#!/usr/bin/env python3
"""
Teste rápido: Classificação de imagens com CLIP (sem custos de API)

Extrai imagens de um PDF e classifica com CLIP para validar que o filtro
está funcionando corretamente antes de gastar dinheiro em descrições com Claude.

Uso:
    python testar_classificacao.py <caminho_pdf> [--threshold 0.5] [--save-images]

Exemplo:
    python testar_classificacao.py "../../02_publicacoes_cientificas_ran/exemplo.pdf" --save-images
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False
    print("⚠️  CLIP não instalado. Instale: pip install torch transformers pillow")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ClipTester:
    """Testa classificação com CLIP."""

    CLASSES = [
        "um gráfico de barras ou linhas com dados científicos",
        "um mapa geográfico ou de distribuição de espécies",
        "um diagrama ou esquema científico",
        "uma tabela de dados ou números",
        "uma fotografia de um animal",
        "uma ilustração decorativa ou figura",
    ]

    RELEVANT_CLASSES = {0, 1, 2, 3}  # gráfico, mapa, diagrama, tabela

    def __init__(self):
        if not HAS_CLIP:
            raise RuntimeError("CLIP não instalado")

        logger.info("Carregando CLIP...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Usando device: {self.device}")

        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.model.to(self.device)
        self.model.eval()

    def classify(self, image_pil: Image.Image) -> tuple[str, float, list[tuple[str, float]]]:
        """Classifica e retorna distribuição de probabilidades."""
        with torch.no_grad():
            inputs = self.processor(
                text=self.CLASSES,
                images=image_pil,
                return_tensors="pt",
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            outputs = self.model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)[0].cpu().numpy()

        best_idx = np.argmax(probs)
        class_names = ["gráfico", "mapa", "diagrama", "tabela", "fotografia", "ilustração"]

        # Distribuição completa para debug
        distribution = [(class_names[i], float(probs[i])) for i in range(len(probs))]

        return class_names[best_idx], float(probs[best_idx]), distribution


def extract_images(pdf_path: str) -> list[tuple[Image.Image, int]]:
    """Extrai imagens do PDF."""
    logger.info(f"Abrindo: {pdf_path}")
    doc = fitz.open(pdf_path)
    images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        for img_xref in page.get_images():
            try:
                base_image = doc.extract_image(img_xref)
                image_bytes = base_image["image"]
                image_pil = Image.open(BytesIO(image_bytes))

                if image_pil.width >= 100 and image_pil.height >= 100:
                    images.append((image_pil, page_num + 1))
            except Exception as e:
                logger.warning(f"Erro na página {page_num+1}: {e}")

    logger.info(f"Extraídas {len(images)} imagens")
    return images


def test_classification(pdf_path: str, threshold: float = 0.5, save_images: bool = False, output_dir: str = "."):
    """Testa classificação e salva relatório."""
    if not HAS_CLIP:
        logger.error("CLIP não disponível")
        sys.exit(1)

    images = extract_images(pdf_path)
    if not images:
        logger.warning("Nenhuma imagem encontrada")
        return

    tester = ClipTester()
    results = []
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for idx, (image_pil, page) in enumerate(images):
        class_name, confidence, distribution = tester.classify(image_pil)

        is_relevant = confidence >= threshold and class_name in ["gráfico", "mapa", "diagrama", "tabela"]
        status = "✓ RELEVANTE" if is_relevant else "✗ descartada"

        print(f"[{idx+1}] Página {page} ({image_pil.width}x{image_pil.height}): {class_name} ({confidence:.1%}) {status}")
        print(f"     Distribuição: {', '.join(f'{c[0]}: {c[1]:.1%}' for c in distribution)}")

        result = {
            "id": idx,
            "page": page,
            "size": f"{image_pil.width}x{image_pil.height}",
            "classification": class_name,
            "confidence": confidence,
            "is_relevant": is_relevant,
            "distribution": distribution,
        }
        results.append(result)

        # Salvar imagem se pedido
        if save_images:
            img_path = output_path / f"img_{idx:04d}_p{page}_{class_name[:8]}.png"
            image_pil.save(img_path)

    # Estatísticas
    relevant_count = sum(1 for r in results if r["is_relevant"])
    total_count = len(results)

    print("\n" + "="*60)
    print(f"RESUMO: {relevant_count}/{total_count} relevantes ({relevant_count/total_count*100:.1f}%)")
    print("="*60)

    by_type = {}
    for r in results:
        c = r["classification"]
        by_type[c] = by_type.get(c, 0) + 1
    for ctype, count in sorted(by_type.items()):
        print(f"  {ctype.capitalize()}: {count}")

    # Salvar relatório
    report = {
        "pdf": pdf_path,
        "timestamp": datetime.now().isoformat(),
        "threshold": threshold,
        "total_imagens": total_count,
        "imagens_relevantes": relevant_count,
        "taxa_relevancia": relevant_count / total_count if total_count > 0 else 0,
        "resultados": results,
        "resumo": by_type,
    }

    report_file = output_path / f"teste_classificacao_{Path(pdf_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Relatório salvo em: {report_file}")
    if save_images:
        logger.info(f"Imagens salvas em: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Teste rápido de classificação com CLIP")
    parser.add_argument("pdf_path", help="Caminho do PDF")
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold de confiança")
    parser.add_argument("--save-images", action="store_true", help="Salvar imagens classificadas")
    parser.add_argument("--output", default=".", help="Diretório de saída")

    args = parser.parse_args()

    if not Path(args.pdf_path).exists():
        logger.error(f"PDF não encontrado: {args.pdf_path}")
        sys.exit(1)

    test_classification(args.pdf_path, args.threshold, args.save_images, args.output)


if __name__ == "__main__":
    main()
