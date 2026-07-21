#!/usr/bin/env python3
"""
Piloto: Processamento de imagens em PDFs com CLIP + Claude Haiku

Pipeline:
1. Extrai imagens de um PDF com PyMuPDF
2. Classifica cada imagem com CLIP (é relevante? gráfico/mapa/diagrama/tabela)
3. Descreve as imagens relevantes com Claude Haiku
4. Salva resultados em JSON com custos

Uso:
    python processar_imagens_piloto.py <caminho_pdf> [--output <dir_saida>] [--threshold 0.5]

Exemplo:
    python processar_imagens_piloto.py "../../02_publicacoes_cientificas_ran/exemplo.pdf"
"""

import argparse
import json
import logging
import os
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
    from anthropic import Anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False
    print("⚠️  Anthropic SDK não instalado. Instale: pip install anthropic")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ImageClassification:
    """Resultado da classificação de uma imagem."""
    image_id: int
    page: int
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
    page: int
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


class ClaudeDescriber:
    """Descritor de imagens com Claude Haiku."""

    MODEL = "claude-3-5-haiku-20241022"

    # Custos por token (Haiku)
    COST_INPUT_PER_K = 0.80 / 1000  # $0.80 por 1M input tokens
    COST_OUTPUT_PER_K = 0.40 / 1000  # $0.40 por 1M output tokens

    def __init__(self):
        """Inicializa o cliente Claude."""
        if not HAS_CLAUDE:
            raise RuntimeError("Anthropic SDK não instalado")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY não está definida em .env")

        self.client = Anthropic(api_key=api_key)
        logger.info(f"Cliente Claude inicializado (modelo: {self.MODEL})")

    def describe(self, image_pil: Image.Image, classification: str) -> tuple[str, int, int, float]:
        """
        Descreve uma imagem com Claude Haiku.

        Retorna: (descrição, tokens_input, tokens_output, custo_usd)
        """
        # Converte PIL para base64
        buffered = BytesIO()
        image_pil.save(buffered, format="PNG")
        import base64
        image_base64 = base64.standard_b64encode(buffered.getvalue()).decode("utf-8")

        prompt = f"""Você está analisando um {classification} de um documento científico sobre herpetofauna brasileira.

Forneça uma descrição estruturada:
1. **Tipo**: Confirme o tipo de visualização
2. **Achado Principal**: Qual é o dado ou padrão mais importante?
3. **Eixos/Categorias**: O que está sendo medido?
4. **Valores Chave**: Números, porcentagens, ranges importantes
5. **Implicações**: O que isto nos diz sobre a espécie ou conservação?

Seja conciso, objetivo e inclua legendas ou anotações visíveis.
Máximo 150 palavras."""

        message = self.client.messages.create(
            model=self.MODEL,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        description = message.content[0].text
        tokens_input = message.usage.input_tokens
        tokens_output = message.usage.output_tokens

        cost = (tokens_input * self.COST_INPUT_PER_K) + (tokens_output * self.COST_OUTPUT_PER_K)

        return description, tokens_input, tokens_output, cost


def extract_images_from_pdf(pdf_path: str) -> list[tuple[Image.Image, int]]:
    """
    Extrai todas as imagens de um PDF.

    Retorna: lista de (imagem_PIL, número_página)
    """
    logger.info(f"Abrindo PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix_list = page.get_images()

        for img_index, xref in enumerate(pix_list):
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_pil = Image.open(BytesIO(image_bytes))

                # Pula imagens muito pequenas (provavelmente logos/ícones)
                if image_pil.width < 100 or image_pil.height < 100:
                    logger.debug(f"Página {page_num+1}: imagem pequena descartada ({image_pil.width}x{image_pil.height})")
                    continue

                images.append((image_pil, page_num + 1))
                logger.info(f"Página {page_num+1}: extraída imagem {img_index+1} ({image_pil.width}x{image_pil.height})")
            except Exception as e:
                logger.warning(f"Erro ao extrair imagem na página {page_num+1}: {e}")

    logger.info(f"Total de imagens extraídas: {len(images)}")
    return images


def classify_images(
    images: list[tuple[Image.Image, int]],
    threshold: float = 0.5
) -> tuple[list[ImageClassification], list[int]]:
    """
    Classifica imagens com CLIP.

    Retorna: (classificações, índices_das_relevantes)
    """
    classifier = ClipClassifier()
    classifications = []
    relevant_indices = []

    for idx, (image_pil, page) in enumerate(images):
        class_name, confidence, reason = classifier.classify(image_pil)

        is_relevant = confidence >= threshold and class_name in ["gráfico", "mapa", "diagrama", "tabela"]

        classifications.append(ImageClassification(
            image_id=idx,
            page=page,
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
    images: list[tuple[Image.Image, int]],
    classifications: list[ImageClassification],
    relevant_indices: list[int]
) -> list[ImageDescription]:
    """
    Descreve imagens relevantes com Claude Haiku.
    """
    describer = ClaudeDescriber()
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
            page=classification.page,
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
    print(f"\nCusto total (Claude Haiku): ${result['custo_total_usd']:.2f}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Piloto: processar imagens em PDFs com CLIP + Claude Haiku"
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
        help="Só classifica, não descreve com Claude (útil para teste rápido)"
    )

    args = parser.parse_args()

    # Validação
    if not Path(args.pdf_path).exists():
        logger.error(f"PDF não encontrado: {args.pdf_path}")
        sys.exit(1)

    if not HAS_CLIP:
        logger.error("CLIP não disponível. Instale: pip install torch transformers pillow")
        sys.exit(1)

    if not args.skip_description and not HAS_CLAUDE:
        logger.error("Anthropic SDK não disponível. Instale: pip install anthropic")
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
