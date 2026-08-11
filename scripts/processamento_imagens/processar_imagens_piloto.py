#!/usr/bin/env python3
"""
Piloto: Processamento de imagens em PDFs com CLIP + VLM local (100% local, sem API paga)

Pipeline:
1. Extrai imagens de um PDF com PyMuPDF
2. Classifica cada imagem com CLIP (é relevante? gráfico/mapa/diagrama/tabela)
3. Descreve as imagens relevantes com um VLM local (Qwen2-VL-2B-Instruct)
4. Salva resultados em JSON

Sem custo de API — decisão de 2026-07-21 (falta de verba), ver
docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md. A etapa de descrição
usava Claude Haiku antes dessa decisão; hoje usa um VLM local.

Uso:
    python processar_imagens_piloto.py <caminho_pdf> [--output <dir_saida>] [--threshold 0.5]

Exemplo:
    python processar_imagens_piloto.py "../../02_publicacoes_cientificas_ran/exemplo.pdf"
"""

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from io import BytesIO

# Dependências opcionais com fallback
try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False
    print("⚠️  CLIP não instalado. Instale: pip install torch transformers pillow")

try:
    from transformers import AutoModelForImageTextToText, AutoProcessor
    HAS_LOCAL_VLM = True
except ImportError:
    HAS_LOCAL_VLM = False
    print("⚠️  Suporte a VLM local não disponível. Instale: pip install transformers accelerate bitsandbytes")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Abaixo disso, imagens costumam ser logos/ícones institucionais — validação
# (docs/processos/VALIDACAO_PILOTO_IMAGENS.md) achou logos de ~120px sendo
# classificados como "tabela" com 100px de mínimo.
MIN_IMAGE_SIZE = 150


@dataclass
class ImageClassification:
    """Resultado da classificação de uma imagem."""
    image_id: int
    pages: list[int]  # todas as páginas onde essa imagem aparece (pode repetir no PDF)
    width: int
    height: int
    is_relevant: bool
    classification: str  # "gráfico", "mapa", "tabela", "diagrama", "outro"
    confidence: float
    reason: Optional[str] = None


@dataclass
class ImageDescription:
    """Descrição de uma imagem relevante."""
    image_id: int
    pages: list[int]
    classification: str
    description: str
    tokens_input: int
    tokens_output: int
    cost_usd: float


class ClipClassifier:
    """Classificador de imagens com CLIP."""

    CLASSES = [
        "um gráfico de barras ou linhas com dados científicos",
        "um mapa geográfico ou de distribuição de espécies",
        "um diagrama ou esquema científico",
        "uma tabela de dados ou números",
        "uma fotografia de um animal",
        "uma ilustração decorativa ou figura",
    ]

    RELEVANT_CLASSES = {0, 1, 2, 3}  # índices das classes relevantes

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """Inicializa o CLIP."""
        if not HAS_CLIP:
            raise RuntimeError("CLIP não instalado")

        logger.info(f"Carregando modelo CLIP: {model_name}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Usando device: {self.device}")

        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

    def classify(self, image_pil: Image.Image) -> tuple[str, float, str]:
        """
        Classifica uma imagem.

        Retorna: (classe_nome, confiança, razão)
        """
        with torch.no_grad():
            inputs = self.processor(
                text=self.CLASSES,
                images=image_pil,
                return_tensors="pt",
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)[0].cpu().numpy()

        best_idx = np.argmax(probs)
        best_prob = float(probs[best_idx])
        best_class = self.CLASSES[best_idx]

        # Simplifica o rótulo
        class_names = [
            "gráfico", "mapa", "diagrama", "tabela",
            "fotografia", "ilustração"
        ]

        is_relevant = best_idx in self.RELEVANT_CLASSES

        return (
            class_names[best_idx],
            best_prob,
            f"Classe: {best_class} ({best_prob:.2%})"
        )


class LocalVLMDescriber:
    """Descritor de imagens com um VLM local (Qwen2-VL-2B-Instruct) — sem custo de API.

    Substitui o ClaudeDescriber (descontinuado em 2026-07-21 por falta de
    verba — ver docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md). Tenta
    carregar em 4-bit na GPU (a RTX 2050 da máquina de dev só tem 4 GB de
    VRAM, compartilhados com a indexação de embeddings); se a GPU não tiver
    memória livre ou bitsandbytes não estiver instalado, cai para CPU.
    """

    MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
    MAX_NEW_TOKENS = 400

    def __init__(self, device: Optional[str] = None):
        """Carrega o VLM local, com fallback automático GPU (4-bit) -> CPU."""
        if not HAS_LOCAL_VLM:
            raise RuntimeError("transformers não instalado com suporte a VLM local")

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Carregando VLM local: {self.MODEL_NAME} (tentando device={self.device})")

        try:
            self.model, self.device = self._carregar_modelo(self.device)
        except Exception as e:
            if self.device == "cuda":
                logger.warning(f"Falha ao carregar na GPU ({e}) — tentando CPU")
                self.model, self.device = self._carregar_modelo("cpu")
            else:
                raise

        self.processor = AutoProcessor.from_pretrained(self.MODEL_NAME)
        self.model.eval()
        logger.info(f"VLM local carregado (device final: {self.device})")

    def _carregar_modelo(self, device: str):
        kwargs = {"dtype": "auto"}
        if device == "cuda":
            try:
                from transformers import BitsAndBytesConfig
                kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
                kwargs["device_map"] = "auto"
            except ImportError:
                logger.warning(
                    "bitsandbytes não instalado — carregando sem quantização "
                    "(pode não caber em GPUs de 4 GB como a RTX 2050)"
                )
                kwargs["device_map"] = "auto"
            model = AutoModelForImageTextToText.from_pretrained(self.MODEL_NAME, **kwargs)
        else:
            model = AutoModelForImageTextToText.from_pretrained(self.MODEL_NAME, **kwargs).to("cpu")
        return model, device

    def describe(self, image_pil: Image.Image, classification: str) -> tuple[str, int, int, float]:
        """
        Descreve uma imagem com o VLM local.

        Retorna: (descrição, tokens_input, tokens_output, custo_usd) — custo
        sempre 0.0 (100% local), tokens mantidos só para fins informativos.
        """
        prompt = f"""Você está analisando um {classification} de um documento científico sobre herpetofauna brasileira.

Forneça uma descrição estruturada:
1. **Tipo**: Confirme o tipo de visualização
2. **Achado Principal**: Qual é o dado ou padrão mais importante?
3. **Eixos/Categorias**: O que está sendo medido?
4. **Valores Chave**: Números, porcentagens, ranges importantes
5. **Implicações**: O que isto nos diz sobre a espécie ou conservação?

Seja conciso, objetivo e inclua legendas ou anotações visíveis.
Máximo 150 palavras."""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        texto_chat = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(
            text=[texto_chat], images=[image_pil], return_tensors="pt", padding=True
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=self.MAX_NEW_TOKENS)
        generated_ids_novos = [
            saida[len(entrada):] for entrada, saida in zip(inputs["input_ids"], generated_ids)
        ]
        description = self.processor.batch_decode(
            generated_ids_novos, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        tokens_input = int(inputs["input_ids"].shape[1])
        tokens_output = int(generated_ids_novos[0].shape[0])

        return description, tokens_input, tokens_output, 0.0


def extract_images_from_pdf(pdf_path: str) -> list[tuple[Image.Image, list[int]]]:
    """
    Extrai todas as imagens de um PDF, deduplicadas por conteúdo.

    A mesma imagem pode estar embutida em mais de uma página do PDF (ex.:
    figura repetida em anexo/resumo — visto na validação em
    docs/processos/VALIDACAO_PILOTO_IMAGENS.md). Deduplicar aqui evita
    descrever a mesma imagem duas vezes na etapa cara do VLM.

    Retorna: lista de (imagem_PIL, páginas_onde_aparece)
    """
    logger.info(f"Abrindo PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    imagens_por_hash: dict[str, tuple[Image.Image, list[int]]] = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix_list = page.get_images()

        for img_index, img_info in enumerate(pix_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_pil = Image.open(BytesIO(image_bytes))

                # Pula imagens muito pequenas (provavelmente logos/ícones)
                if image_pil.width < MIN_IMAGE_SIZE or image_pil.height < MIN_IMAGE_SIZE:
                    logger.debug(f"Página {page_num+1}: imagem pequena descartada ({image_pil.width}x{image_pil.height})")
                    continue

                image_hash = hashlib.md5(image_bytes).hexdigest()
                if image_hash in imagens_por_hash:
                    imagens_por_hash[image_hash][1].append(page_num + 1)
                    logger.debug(f"Página {page_num+1}: imagem duplicada (já extraída na página {imagens_por_hash[image_hash][1][0]})")
                else:
                    imagens_por_hash[image_hash] = (image_pil, [page_num + 1])
                    logger.info(f"Página {page_num+1}: extraída imagem {img_index+1} ({image_pil.width}x{image_pil.height})")
            except Exception as e:
                logger.warning(f"Erro ao extrair imagem na página {page_num+1}: {e}")

    images = list(imagens_por_hash.values())
    duplicatas = sum(len(paginas) - 1 for _, paginas in images)
    logger.info(
        f"Total de imagens únicas extraídas: {len(images)}"
        + (f" ({duplicatas} duplicata(s) descartada(s))" if duplicatas else "")
    )
    return images


def classify_images(
    images: list[tuple[Image.Image, list[int]]],
    threshold: float = 0.5
) -> tuple[list[ImageClassification], list[int]]:
    """
    Classifica imagens com CLIP.

    Retorna: (classificações, índices_das_relevantes)
    """
    classifier = ClipClassifier()
    classifications = []
    relevant_indices = []

    for idx, (image_pil, pages) in enumerate(images):
        class_name, confidence, reason = classifier.classify(image_pil)

        is_relevant = confidence >= threshold and class_name in ["gráfico", "mapa", "diagrama", "tabela"]

        classifications.append(ImageClassification(
            image_id=idx,
            pages=pages,
            width=image_pil.width,
            height=image_pil.height,
            is_relevant=is_relevant,
            classification=class_name,
            confidence=confidence,
            reason=reason
        ))

        if is_relevant:
            relevant_indices.append(idx)

        status = "✓ RELEVANTE" if is_relevant else "✗ descartada"
        logger.info(f"Imagem {idx+1}: {class_name} ({confidence:.2%}) {status}")

    logger.info(f"Imagens relevantes: {len(relevant_indices)} de {len(images)}")
    return classifications, relevant_indices


def describe_images(
    images: list[tuple[Image.Image, list[int]]],
    classifications: list[ImageClassification],
    relevant_indices: list[int]
) -> list[ImageDescription]:
    """
    Descreve imagens relevantes com o VLM local (Qwen2-VL-2B-Instruct).
    """
    describer = LocalVLMDescriber()
    descriptions = []
    total_cost = 0.0

    for idx in relevant_indices:
        image_pil, _ = images[idx]
        classification = classifications[idx]

        logger.info(f"Descrevendo imagem {idx+1}...")
        description, tokens_in, tokens_out, cost = describer.describe(
            image_pil,
            classification.classification
        )

        descriptions.append(ImageDescription(
            image_id=idx,
            pages=classification.pages,
            classification=classification.classification,
            description=description,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=cost
        ))

        total_cost += cost
        logger.info(f"  Tokens: {tokens_in} input + {tokens_out} output | Custo: ${cost:.4f}")

    logger.info(f"Custo total: ${total_cost:.2f}")
    return descriptions


def save_results(
    pdf_path: str,
    classifications: list[ImageClassification],
    descriptions: list[ImageDescription],
    output_dir: str
) -> str:
    """Salva resultados em JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_name = Path(pdf_path).stem
    timestamp = datetime.now().isoformat()

    result = {
        "pdf": str(pdf_path),
        "timestamp": timestamp,
        "imagens_totais": len(classifications),
        "imagens_relevantes": len(descriptions),
        "classificacoes": [asdict(c) for c in classifications],
        "descricoes": [asdict(d) for d in descriptions],
        "custo_total_usd": sum(d.cost_usd for d in descriptions),
        "resumo": {
            "gráficos": sum(1 for c in classifications if c.classification == "gráfico"),
            "mapas": sum(1 for c in classifications if c.classification == "mapa"),
            "diagramas": sum(1 for c in classifications if c.classification == "diagrama"),
            "tabelas": sum(1 for c in classifications if c.classification == "tabela"),
            "fotografias": sum(1 for c in classifications if c.classification == "fotografia"),
            "ilustrações": sum(1 for c in classifications if c.classification == "ilustração"),
        }
    }

    output_file = output_path / f"resultado_{pdf_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Resultados salvos em: {output_file}")
    return str(output_file)


def print_summary(result: dict):
    """Imprime resumo dos resultados."""
    print("\n" + "="*60)
    print("RESUMO DO PROCESSAMENTO")
    print("="*60)
    print(f"PDF: {Path(result['pdf']).name}")
    print(f"Imagens extraídas: {result['imagens_totais']}")
    print(f"Imagens relevantes: {result['imagens_relevantes']}")
    print(f"Taxa de relevância: {result['imagens_relevantes']/result['imagens_totais']*100:.1f}%")
    print("\nDistribuição de tipos:")
    for tipo, count in result['resumo'].items():
        print(f"  - {tipo.capitalize()}: {count}")
    print(f"\nCusto total: ${result['custo_total_usd']:.2f} (VLM local — sempre $0)")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Piloto: processar imagens em PDFs com CLIP + VLM local (100% local, sem API paga)"
    )
    parser.add_argument("pdf_path", help="Caminho do PDF a processar")
    parser.add_argument(
        "--output",
        default=".",
        help="Diretório de saída (padrão: atual)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Threshold de confiança para classificação (0-1, padrão: 0.5)"
    )
    parser.add_argument(
        "--skip-description",
        action="store_true",
        help="Só classifica, não descreve com o VLM local (útil para teste rápido)"
    )

    args = parser.parse_args()

    # Validação
    if not Path(args.pdf_path).exists():
        logger.error(f"PDF não encontrado: {args.pdf_path}")
        sys.exit(1)

    if not HAS_CLIP:
        logger.error("CLIP não disponível. Instale: pip install torch transformers pillow")
        sys.exit(1)

    if not args.skip_description and not HAS_LOCAL_VLM:
        logger.error("Suporte a VLM local não disponível. Instale: pip install transformers accelerate bitsandbytes")
        sys.exit(1)

    # Pipeline
    logger.info("="*60)
    logger.info("COMEÇANDO PROCESSAMENTO DE IMAGENS")
    logger.info("="*60)

    images = extract_images_from_pdf(args.pdf_path)

    if not images:
        logger.warning("Nenhuma imagem encontrada no PDF")
        sys.exit(0)

    classifications, relevant_indices = classify_images(images, args.threshold)

    descriptions = []
    if not args.skip_description and relevant_indices:
        descriptions = describe_images(images, classifications, relevant_indices)
    elif args.skip_description:
        logger.info("Pulando descrição (--skip-description ativado)")

    result = {
        "pdf": args.pdf_path,
        "timestamp": datetime.now().isoformat(),
        "imagens_totais": len(classifications),
        "imagens_relevantes": len(descriptions),
        "classificacoes": [asdict(c) for c in classifications],
        "descricoes": [asdict(d) for d in descriptions],
        "custo_total_usd": sum(d.cost_usd for d in descriptions),
        "resumo": {
            "gráficos": sum(1 for c in classifications if c.classification == "gráfico"),
            "mapas": sum(1 for c in classifications if c.classification == "mapa"),
            "diagramas": sum(1 for c in classifications if c.classification == "diagrama"),
            "tabelas": sum(1 for c in classifications if c.classification == "tabela"),
            "fotografias": sum(1 for c in classifications if c.classification == "fotografia"),
            "ilustrações": sum(1 for c in classifications if c.classification == "ilustração"),
        }
    }

    output_file = save_results(args.pdf_path, classifications, descriptions, args.output)
    print_summary(result)

    logger.info(f"Piloto concluído com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
