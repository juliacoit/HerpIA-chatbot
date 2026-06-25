"""Extrai texto dos PDFs coletados do Programa Monitora e dos PANs.

Para cada PDF em 01_fontes_web/{monitora,pans}/*/documentos/, gera um JSON em
07_processados/textos_extraidos/{monitora,pans}/<categoria_ou_slug>/<nome>.json
com o texto por página e metadados de extração.

Método principal: PyMuPDF (fitz) — extração direta da camada de texto.
Fallback OCR:     pytesseract + Tesseract, ativado por --ocr quando o texto
                  extraído de uma página for muito escasso (< MIN_CHARS_PAGINA).
                  Requer: sudo apt install tesseract-ocr tesseract-ocr-por

Uso:
    python extrair_texto_pdfs.py [--fonte monitora|pans] [--ocr] [--reprocessar]

    --fonte       Processa apenas a fonte indicada (padrão: ambas)
    --ocr         Ativa fallback OCR para páginas sem texto (requer Tesseract)
    --reprocessar Reprocessa arquivos que já têm JSON de saída (padrão: pula)
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

RAIZ = Path(__file__).resolve().parents[2]
FONTES_DIR = RAIZ / "01_fontes_web"
OUTPUT_DIR = RAIZ / "07_processados" / "textos_extraidos"

# Páginas com menos que este número de caracteres são consideradas sem texto útil.
MIN_CHARS_PAGINA = 50

# Mínimo de páginas sem texto para classificar o PDF como "escaneado".
LIMIAR_ESCANEADO = 0.5  # fração de páginas sem texto


def limpar_texto(texto: str) -> str:
    texto = re.sub(r"\s*\f\s*", "\n\n", texto)   # form feed → separador de página
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_com_pymupdf(caminho_pdf: Path) -> list[dict]:
    """Retorna lista de {pagina, texto} para cada página do PDF."""
    paginas = []
    with fitz.open(str(caminho_pdf)) as doc:
        for i, pagina in enumerate(doc, start=1):
            texto = limpar_texto(pagina.get_text())
            paginas.append({"pagina": i, "texto": texto})
    return paginas


def extrair_com_ocr(caminho_pdf: Path) -> list[dict]:
    """Fallback OCR via pytesseract. Só chamado se --ocr foi passado."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print("  [OCR] pytesseract/Pillow não instalados — pule com --ocr ou instale.", file=sys.stderr)
        return []

    paginas = []
    with fitz.open(str(caminho_pdf)) as doc:
        for i, pagina in enumerate(doc, start=1):
            mat = fitz.Matrix(2, 2)  # resolução 2×
            pix = pagina.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texto = limpar_texto(pytesseract.image_to_string(img, lang="por+eng"))
            paginas.append({"pagina": i, "texto": texto})
    return paginas


def processar_pdf(
    caminho_pdf: Path,
    metadados_doc: dict,
    fonte: str,
    subdir: str,
    usar_ocr: bool,
) -> dict:
    paginas = extrair_com_pymupdf(caminho_pdf)
    num_paginas = len(paginas)
    paginas_sem_texto = [p["pagina"] for p in paginas if len(p["texto"]) < MIN_CHARS_PAGINA]
    fracao_sem_texto = len(paginas_sem_texto) / num_paginas if num_paginas else 0
    provavelmente_escaneado = fracao_sem_texto >= LIMIAR_ESCANEADO

    metodo = "texto"
    if provavelmente_escaneado and usar_ocr:
        print(f"    → {fracao_sem_texto:.0%} páginas sem texto, aplicando OCR...")
        paginas = extrair_com_ocr(caminho_pdf)
        metodo = "ocr"
        paginas_sem_texto = [p["pagina"] for p in paginas if len(p["texto"]) < MIN_CHARS_PAGINA]

    texto_completo = "\n\n".join(
        f"[Página {p['pagina']}]\n{p['texto']}" for p in paginas if p["texto"]
    )

    return {
        "fonte": fonte,
        "subdir": subdir,
        "nome_arquivo": caminho_pdf.name,
        "url_origem": metadados_doc.get("url", ""),
        "contexto": metadados_doc.get("contexto", ""),
        "ciclo": metadados_doc.get("ciclo"),
        "num_paginas": num_paginas,
        "paginas_sem_texto": paginas_sem_texto,
        "provavelmente_escaneado": provavelmente_escaneado,
        "metodo_extracao": metodo,
        "data_extracao": date.today().isoformat(),
        "paginas": paginas,
        "texto_completo": texto_completo,
    }


def carregar_mapa_urls(metadados_json: Path) -> dict[str, dict]:
    """Cria dicionário nome_arquivo → metadados do documento."""
    if not metadados_json.exists():
        return {}
    dados = json.loads(metadados_json.read_text(encoding="utf-8"))
    documentos = dados if isinstance(dados, list) else dados.get("documentos", [])
    return {d["nome_arquivo"]: d for d in documentos if d.get("nome_arquivo")}


def processar_fonte(fonte: str, usar_ocr: bool, reprocessar: bool) -> dict:
    fonte_dir = FONTES_DIR / fonte
    if not fonte_dir.exists():
        print(f"Diretório {fonte_dir} não encontrado.")
        return {}

    relatorio = {"processados": 0, "pulados": 0, "erros": 0, "escaneados": 0, "sem_pdf": 0}

    subdirs = [d for d in sorted(fonte_dir.iterdir()) if d.is_dir()]
    for subdir in subdirs:
        docs_dir = subdir / "documentos"
        if not docs_dir.exists():
            continue

        mapa_urls = carregar_mapa_urls(subdir / "metadados.json")
        pdfs = sorted(docs_dir.rglob("*.pdf"))

        if not pdfs:
            relatorio["sem_pdf"] += 1
            continue

        output_subdir = OUTPUT_DIR / fonte / subdir.name
        output_subdir.mkdir(parents=True, exist_ok=True)

        print(f"\n  [{fonte}/{subdir.name}] {len(pdfs)} PDFs")

        for pdf in pdfs:
            # Preserva subdiretórios dentro de documentos/ (ex: ciclo-1/, ciclo-2/)
            relativo = pdf.relative_to(docs_dir)
            output_json = output_subdir / relativo.parent / (pdf.stem + ".json")
            output_json.parent.mkdir(parents=True, exist_ok=True)

            if output_json.exists() and not reprocessar:
                relatorio["pulados"] += 1
                continue

            metadados_doc = mapa_urls.get(pdf.name, {})
            try:
                resultado = processar_pdf(pdf, metadados_doc, fonte, subdir.name, usar_ocr)
                output_json.write_text(
                    json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
                )

                flag_scan = " [ESCANEADO]" if resultado["provavelmente_escaneado"] else ""
                print(f"    ✓ {pdf.name} — {resultado['num_paginas']} pág., "
                      f"{resultado['metodo_extracao']}{flag_scan}")

                relatorio["processados"] += 1
                if resultado["provavelmente_escaneado"]:
                    relatorio["escaneados"] += 1

            except Exception as e:
                print(f"    ✗ {pdf.name} — ERRO: {e}", file=sys.stderr)
                relatorio["erros"] += 1

    return relatorio


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fonte", choices=["monitora", "pans"], default=None,
                        help="Processar apenas esta fonte (padrão: ambas)")
    parser.add_argument("--ocr", action="store_true",
                        help="Usar OCR como fallback para páginas sem texto (requer Tesseract)")
    parser.add_argument("--reprocessar", action="store_true",
                        help="Reprocessar arquivos que já têm JSON de saída")
    args = parser.parse_args()

    fontes = [args.fonte] if args.fonte else ["monitora", "pans"]

    total = {"processados": 0, "pulados": 0, "erros": 0, "escaneados": 0, "sem_pdf": 0}
    for fonte in fontes:
        print(f"\n{'='*50}")
        print(f"Processando: {fonte.upper()}")
        print(f"{'='*50}")
        rel = processar_fonte(fonte, args.ocr, args.reprocessar)
        for k in total:
            total[k] += rel.get(k, 0)

    print(f"\n{'='*50}")
    print(f"CONCLUÍDO")
    print(f"  Processados:  {total['processados']}")
    print(f"  Pulados:      {total['pulados']} (já existiam)")
    print(f"  Escaneados:   {total['escaneados']} (sem texto, OCR {'aplicado' if args.ocr else 'não aplicado'})")
    print(f"  Erros:        {total['erros']}")
    print(f"  Saída:        {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
