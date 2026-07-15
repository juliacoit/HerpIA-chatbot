"""Extrai texto dos PDFs de publicações científicas do RAN já autorizados.

Lê 06_inventario/triagem_copyright_publicacoes.xlsx e processa apenas as
linhas com decisao == "autorizado" (decisão humana registrada — ver ADR 0002:
toda movimentação para 03_documentos_autorizados/ pressupõe avaliação prévia).
Metadados bibliográficos (autor, título, ano, fonte, DOI) vêm de
06_inventario/catalogo_publicacoes_ran.json, casados pelo campo "caminho".

Para cada PDF autorizado, gera um JSON em
07_processados/textos_extraidos/publicacoes/<pasta_origem>/<nome>.json
com o texto por página e metadados de extração — mesmo formato usado por
extrair_texto_pdfs.py (monitora/pans), para compatibilidade com gerar_chunks.py.

Método principal: PyMuPDF (fitz) — extração direta da camada de texto.
Fallback OCR:     pytesseract + Tesseract, ativado por --ocr quando o texto
                  extraído de uma página for muito escasso (< MIN_CHARS_PAGINA).
                  Requer: sudo apt install tesseract-ocr tesseract-ocr-por

Uso:
    python extrair_texto_publicacoes.py [--ocr] [--reprocessar]

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
import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
TRIAGEM_XLSX = RAIZ / "06_inventario" / "triagem_copyright_publicacoes.xlsx"
CATALOGO_JSON = RAIZ / "06_inventario" / "catalogo_publicacoes_ran.json"
OUTPUT_DIR = RAIZ / "07_processados" / "textos_extraidos" / "publicacoes"

# Páginas com menos que este número de caracteres são consideradas sem texto útil.
MIN_CHARS_PAGINA = 50

# Mínimo de páginas sem texto para classificar o PDF como "escaneado".
LIMIAR_ESCANEADO = 0.5  # fração de páginas sem texto


def limpar_texto(texto: str) -> str:
    texto = re.sub(r"\s*\f\s*", "\n\n", texto)  # form feed → separador de página
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


def carregar_autorizados() -> list[dict]:
    """Lê a planilha de triagem e retorna as linhas com decisao == 'autorizado'."""
    wb = openpyxl.load_workbook(TRIAGEM_XLSX, data_only=True)
    ws = wb["Triagem"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    idx = {h: i for i, h in enumerate(header)}
    return [
        {h: r[idx[h]] for h in header}
        for r in rows[1:]
        if r[idx["decisao"]] == "autorizado"
    ]


def carregar_metadados_catalogo() -> dict[str, dict]:
    """Cria dicionário caminho → metadados bibliográficos do catálogo."""
    if not CATALOGO_JSON.exists():
        return {}
    dados = json.loads(CATALOGO_JSON.read_text(encoding="utf-8"))
    return {a["caminho"]: (a.get("metadados") or {}) for a in dados.get("arquivos", [])}


def processar_pdf(caminho_pdf: Path, linha_triagem: dict, metadados_catalogo: dict, usar_ocr: bool) -> dict:
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
        "fonte": "publicacoes",
        "pasta_origem": linha_triagem["pasta_origem"],
        "nome_arquivo": caminho_pdf.name,
        "caminho_original": linha_triagem["caminho"],
        "autor": metadados_catalogo.get("autor"),
        "titulo": metadados_catalogo.get("titulo"),
        "ano": metadados_catalogo.get("ano"),
        "fonte_bibliografica": metadados_catalogo.get("fonte"),
        "doi": metadados_catalogo.get("doi"),
        "tipologia": metadados_catalogo.get("tipologia"),
        "risco_copyright": linha_triagem["risco_copyright"],
        "decisao_copyright": linha_triagem["decisao"],
        "revisado_por": linha_triagem["revisado_por"],
        "data_revisao_copyright": str(linha_triagem["data_revisao"]),
        "num_paginas": num_paginas,
        "paginas_sem_texto": paginas_sem_texto,
        "provavelmente_escaneado": provavelmente_escaneado,
        "metodo_extracao": metodo,
        "data_extracao": date.today().isoformat(),
        "paginas": paginas,
        "texto_completo": texto_completo,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ocr", action="store_true",
                        help="Usar OCR como fallback para páginas sem texto (requer Tesseract)")
    parser.add_argument("--reprocessar", action="store_true",
                        help="Reprocessar arquivos que já têm JSON de saída")
    args = parser.parse_args()

    autorizados = carregar_autorizados()
    metadados_catalogo = carregar_metadados_catalogo()

    print(f"{len(autorizados)} publicações autorizadas (decisao == 'autorizado') na triagem de copyright.\n")

    relatorio = {"processados": 0, "pulados": 0, "erros": 0, "escaneados": 0, "nao_encontrados": 0}

    for linha in autorizados:
        caminho_pdf = RAIZ / linha["caminho"]
        if not caminho_pdf.exists():
            print(f"  ✗ não encontrado: {linha['caminho']}", file=sys.stderr)
            relatorio["nao_encontrados"] += 1
            continue

        output_subdir = OUTPUT_DIR / linha["pasta_origem"]
        output_subdir.mkdir(parents=True, exist_ok=True)
        output_json = output_subdir / (caminho_pdf.stem + ".json")

        if output_json.exists() and not args.reprocessar:
            relatorio["pulados"] += 1
            continue

        try:
            resultado = processar_pdf(caminho_pdf, linha, metadados_catalogo.get(linha["caminho"], {}), args.ocr)
            output_json.write_text(
                json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            flag_scan = " [ESCANEADO]" if resultado["provavelmente_escaneado"] else ""
            print(f"  ✓ {caminho_pdf.name} — {resultado['num_paginas']} pág., "
                  f"{resultado['metodo_extracao']}{flag_scan}")

            relatorio["processados"] += 1
            if resultado["provavelmente_escaneado"]:
                relatorio["escaneados"] += 1

        except Exception as e:
            print(f"  ✗ {caminho_pdf.name} — ERRO: {e}", file=sys.stderr)
            relatorio["erros"] += 1

    print(f"\n{'='*50}")
    print("CONCLUÍDO")
    print(f"  Processados:      {relatorio['processados']}")
    print(f"  Pulados:          {relatorio['pulados']} (já existiam)")
    print(f"  Escaneados:       {relatorio['escaneados']} (sem texto, OCR {'aplicado' if args.ocr else 'não aplicado'})")
    print(f"  Não encontrados:  {relatorio['nao_encontrados']}")
    print(f"  Erros:            {relatorio['erros']}")
    print(f"  Saída:            {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
