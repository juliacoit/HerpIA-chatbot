"""Extrai o texto dos documentos do SEI baixados pela exportação automatizada.

Lê 01_fontes_web/sei/exportacao_sei_manifesto.json (gerado por
scripts/coleta/exportar_documentos_sei.py — ADR 0010) e processa os documentos
com status "baixado", que estão em 04_documentos_pendentes_avaliacao/sei/.

A extração NÃO autoriza nenhum documento: ela existe para viabilizar a triagem
de sensibilidade e a avaliação humana (ADR 0002). Os JSONs de saída levam
"sensibilidade": "pendente_avaliacao", e "sei" não está na lista de fontes de
gerar_chunks.py — nada daqui é fragmentado nem indexado.

Para cada documento, gera
07_processados/textos_extraidos/sei/<processo>/<numero_sei>.json
no mesmo formato de extrair_texto_pdfs.py ("paginas" + "texto_completo"). O que
conta como "página" depende do tipo de arquivo:

    pdf            página do PDF (OCR nas páginas sem texto, com --ocr)
    html           documento inteiro (documentos internos do SEI)
    xlsx/xlsm/xls  uma aba da planilha
    ods            uma aba da planilha
    docx           documento inteiro
    pptx           um slide
    png/jpg        a imagem (só com --ocr)
    zip            cada arquivo interno vira uma ou mais páginas

Formatos sem extrator (.doc, .7z) ficam registrados no resumo para tratamento
manual. O resumo vai para 07_processados/metadados/extracao_texto_sei.json.

O terminal mostra só o número SEI, o tipo e contagens — nunca nome de arquivo
interno nem conteúdo.

Uso:
    python scripts/processamento/extrair_texto_sei.py [--ocr] [--reprocessar]
        [--processos N] [--limite N]
"""

import argparse
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

import fitz  # PyMuPDF
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parents[2]
MANIFESTO = RAIZ / "01_fontes_web" / "sei" / "exportacao_sei_manifesto.json"
OUTPUT_DIR = RAIZ / "07_processados" / "textos_extraidos" / "sei"
RESUMO = RAIZ / "07_processados" / "metadados" / "extracao_texto_sei.json"

# Páginas com menos que este número de caracteres são consideradas sem texto útil.
MIN_CHARS_PAGINA = 50
# Teto de páginas com OCR por documento, para um PDF enorme não travar a fila.
MAX_PAGINAS_OCR = 400
# Limites para arquivos compactados (proteção contra "zip bomb").
MAX_MEMBROS_ZIP = 2000
MAX_BYTES_ZIP = 1024**3
MAX_BYTES_MEMBRO = 300 * 1024**2

EXTENSOES_IMAGEM = {"png", "jpg", "jpeg", "tif", "tiff", "bmp"}
EXTENSOES_PLANILHA = {"xlsx", "xlsm"}


class FormatoSemExtrator(Exception):
    """O tipo de arquivo não tem extrator neste script."""


def limpar_texto(texto: str) -> str:
    # O caractere nulo aparece em alguns PDFs e o PostgreSQL recusa textos com ele.
    texto = texto.replace("\x00", "")
    texto = re.sub(r"\s*\f\s*", "\n\n", texto)
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    texto = re.sub(r" ?\n ?", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def ocr_pixmap(pix) -> str:
    import pytesseract
    from PIL import Image

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return limpar_texto(pytesseract.image_to_string(img, lang="por+eng"))


def extrair_pdf(dados: bytes, usar_ocr: bool) -> tuple[list[dict], dict]:
    paginas = []
    paginas_ocr = 0
    ocr_truncado = False
    with fitz.open(stream=dados, filetype="pdf") as doc:
        for i, pagina in enumerate(doc, start=1):
            texto = limpar_texto(pagina.get_text())
            metodo = "texto"
            if usar_ocr and len(texto) < MIN_CHARS_PAGINA:
                if paginas_ocr < MAX_PAGINAS_OCR:
                    pix = pagina.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csRGB, alpha=False)
                    texto_ocr = ocr_pixmap(pix)
                    paginas_ocr += 1
                    if len(texto_ocr) > len(texto):
                        texto, metodo = texto_ocr, "ocr"
                else:
                    ocr_truncado = True
            paginas.append({"pagina": i, "texto": texto, "metodo": metodo})
    return paginas, {"paginas_ocr": paginas_ocr, "ocr_truncado": ocr_truncado}


def extrair_imagem(dados: bytes, extensao: str, usar_ocr: bool) -> tuple[list[dict], dict]:
    if not usar_ocr:
        return [{"pagina": 1, "texto": "", "metodo": "sem_ocr"}], {}
    with fitz.open(stream=dados, filetype=extensao) as doc:
        pix = doc[0].get_pixmap(colorspace=fitz.csRGB, alpha=False)
        texto = ocr_pixmap(pix)
    return [{"pagina": 1, "texto": texto, "metodo": "ocr"}], {"paginas_ocr": 1}


def extrair_html(dados: bytes) -> tuple[list[dict], dict]:
    sopa = BeautifulSoup(dados, "html.parser")
    for tag in sopa(["script", "style", "head"]):
        tag.decompose()
    texto = limpar_texto(sopa.get_text(separator="\n"))
    return [{"pagina": 1, "texto": texto, "metodo": "texto"}], {}


def _celula(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _linhas_para_texto(linhas) -> str:
    saida = []
    for linha in linhas:
        celulas = [_celula(v) for v in linha]
        while celulas and not celulas[-1]:
            celulas.pop()
        if any(celulas):
            saida.append(" | ".join(celulas))
    return limpar_texto("\n".join(saida))


def extrair_xlsx(dados: bytes) -> tuple[list[dict], dict]:
    import warnings

    import openpyxl

    # Avisos sobre recursos de planilha que o openpyxl ignora (validação etc.).
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
    wb =openpyxl.load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    paginas = []
    try:
        for i, ws in enumerate(wb.worksheets, start=1):
            if not hasattr(ws, "iter_rows"):  # aba só com gráfico
                continue
            texto = _linhas_para_texto(ws.iter_rows(values_only=True))
            paginas.append({"pagina": i, "aba": ws.title, "texto": texto, "metodo": "texto"})
    finally:
        wb.close()
    return paginas, {}


def extrair_xls(dados: bytes) -> tuple[list[dict], dict]:
    try:
        import xlrd
    except ImportError as erro:
        raise FormatoSemExtrator("xls (instale xlrd)") from erro

    wb = xlrd.open_workbook(file_contents=dados)
    paginas = []
    for i, ws in enumerate(wb.sheets(), start=1):
        texto = _linhas_para_texto(ws.row_values(r) for r in range(ws.nrows))
        paginas.append({"pagina": i, "aba": ws.name, "texto": texto, "metodo": "texto"})
    return paginas, {}


def _nome_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _texto_xml_por_paragrafo(xml: bytes, tag_paragrafo: str, tags_texto: set[str]) -> str:
    """Junta o texto de um XML de documento Office, um parágrafo por linha."""
    raiz = ElementTree.fromstring(xml)
    linhas = []
    for elemento in raiz.iter():
        if _nome_local(elemento.tag) != tag_paragrafo:
            continue
        partes = []
        for no in elemento.iter():
            nome = _nome_local(no.tag)
            if nome in tags_texto and no.text:
                partes.append(no.text)
            elif nome in ("tab", "br"):
                partes.append(" ")
        if partes:
            linhas.append("".join(partes))
    return limpar_texto("\n".join(linhas))


def extrair_docx(dados: bytes) -> tuple[list[dict], dict]:
    # O .docx é um zip de XMLs; ler direto dispensa dependência extra e pega
    # também o texto dentro de tabelas, cabeçalhos, rodapés e notas.
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        nomes = z.namelist()
        partes = ["word/document.xml"]
        partes += sorted(n for n in nomes if re.fullmatch(r"word/(header|footer)\d*\.xml", n))
        partes += [n for n in ("word/footnotes.xml", "word/endnotes.xml") if n in nomes]
        textos = [_texto_xml_por_paragrafo(z.read(p), "p", {"t"}) for p in partes if p in nomes]
    texto = limpar_texto("\n\n".join(t for t in textos if t))
    return [{"pagina": 1, "texto": texto, "metodo": "texto"}], {}


def extrair_pptx(dados: bytes) -> tuple[list[dict], dict]:
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        slides = sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)),
        )
        paginas = [
            {"pagina": i, "texto": _texto_xml_por_paragrafo(z.read(n), "p", {"t"}), "metodo": "texto"}
            for i, n in enumerate(slides, start=1)
        ]
    return paginas, {}


def extrair_ods(dados: bytes) -> tuple[list[dict], dict]:
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        raiz = ElementTree.fromstring(z.read("content.xml"))
    paginas = []
    tabelas = [e for e in raiz.iter() if _nome_local(e.tag) == "table"]
    for i, tabela in enumerate(tabelas, start=1):
        linhas = []
        for linha in tabela.iter():
            if _nome_local(linha.tag) != "table-row":
                continue
            celulas = [
                " ".join(t.strip() for t in celula.itertext() if t.strip())
                for celula in linha
                if _nome_local(celula.tag) == "table-cell"
            ]
            linhas.append(celulas)
        nome_aba = next((v for k, v in tabela.attrib.items() if _nome_local(k) == "name"), None)
        paginas.append({"pagina": i, "aba": nome_aba, "texto": _linhas_para_texto(linhas), "metodo": "texto"})
    return paginas, {}


def identificar_extensao(dados: bytes, extensao: str) -> str:
    """Confere o tipo pelo início do arquivo quando a extensão não ajuda."""
    conhecidas = {"pdf", "html", "htm", "xlsx", "xlsm", "xls", "ods", "docx", "pptx", "zip", "doc", "7z"}
    if extensao in conhecidas | EXTENSOES_IMAGEM:
        return extensao
    inicio = dados[:8]
    if inicio.startswith(b"%PDF"):
        return "pdf"
    if inicio.startswith(b"\x89PNG"):
        return "png"
    if inicio.startswith(b"\xff\xd8"):
        return "jpg"
    if inicio.startswith(b"PK"):
        return "zip"
    if re.search(rb"<html|<!doctype", dados[:2000], re.IGNORECASE):
        return "html"
    return extensao


def extrair(dados: bytes, extensao: str, usar_ocr: bool) -> tuple[list[dict], dict]:
    extensao = identificar_extensao(dados, extensao)
    if extensao == "pdf":
        return extrair_pdf(dados, usar_ocr)
    if extensao in ("html", "htm"):
        return extrair_html(dados)
    if extensao in EXTENSOES_PLANILHA:
        return extrair_xlsx(dados)
    if extensao == "xls":
        return extrair_xls(dados)
    if extensao == "ods":
        return extrair_ods(dados)
    if extensao == "docx":
        return extrair_docx(dados)
    if extensao == "pptx":
        return extrair_pptx(dados)
    if extensao in EXTENSOES_IMAGEM:
        return extrair_imagem(dados, extensao, usar_ocr)
    raise FormatoSemExtrator(extensao or "sem_extensao")


def extrair_zip(dados: bytes, usar_ocr: bool) -> tuple[list[dict], dict]:
    """Extrai, em memória, cada arquivo interno do zip (sem seguir zips aninhados)."""
    paginas = []
    info = {"membros": 0, "membros_extraidos": 0, "membros_sem_extrator": Counter(), "membros_com_erro": 0,
            "paginas_ocr": 0, "ocr_truncado": False}
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        membros = [m for m in z.infolist() if not m.is_dir()]
        if len(membros) > MAX_MEMBROS_ZIP or sum(m.file_size for m in membros) > MAX_BYTES_ZIP:
            raise ValueError("zip acima do limite de tamanho")
        info["membros"] = len(membros)
        for membro in membros:
            extensao = Path(membro.filename).suffix.lower().lstrip(".")
            if membro.file_size > MAX_BYTES_MEMBRO:
                info["membros_com_erro"] += 1
                continue
            try:
                if extensao == "zip":
                    raise FormatoSemExtrator("zip_aninhado")
                paginas_membro, info_membro = extrair(z.read(membro), extensao, usar_ocr)
            except FormatoSemExtrator as erro:
                info["membros_sem_extrator"][str(erro)] += 1
                continue
            except Exception:
                info["membros_com_erro"] += 1
                continue
            info["membros_extraidos"] += 1
            info["paginas_ocr"] += info_membro.get("paginas_ocr", 0)
            info["ocr_truncado"] = info["ocr_truncado"] or info_membro.get("ocr_truncado", False)
            for p in paginas_membro:
                p["arquivo_interno"] = membro.filename
                p["pagina_no_arquivo"] = p["pagina"]
                p["pagina"] = len(paginas) + 1
                paginas.append(p)
    info["membros_sem_extrator"] = dict(info["membros_sem_extrator"])
    return paginas, info


def processar_documento(numero: str, registro: dict, usar_ocr: bool) -> dict:
    """Extrai um documento e grava o JSON. Devolve só o resumo (sem conteúdo)."""
    caminho = RAIZ / registro["arquivo"]
    extensao = caminho.suffix.lower().lstrip(".")
    resumo = {"numero_sei": numero, "processo": registro["processo"], "extensao": extensao}
    try:
        dados = caminho.read_bytes()
        extensao = identificar_extensao(dados, extensao)
        resumo["extensao"] = extensao
        if extensao == "zip":
            paginas, info = extrair_zip(dados, usar_ocr)
        else:
            paginas, info = extrair(dados, extensao, usar_ocr)
    except FormatoSemExtrator:
        return {**resumo, "status": "formato_sem_extrator"}
    except Exception as erro:
        return {**resumo, "status": "erro", "erro": type(erro).__name__}

    paginas_sem_texto = [p["pagina"] for p in paginas if len(p["texto"]) < MIN_CHARS_PAGINA]
    caracteres = sum(len(p["texto"]) for p in paginas)
    texto_completo = "\n\n".join(f"[Página {p['pagina']}]\n{p['texto']}" for p in paginas if p["texto"])

    saida = {
        "fonte": "sei",
        "sensibilidade": "pendente_avaliacao",
        "numero_sei": numero,
        "processo": registro["processo"],
        "nome_arquivo": caminho.name,
        "caminho_original": registro["arquivo"],
        "sha256": registro.get("sha256"),
        "content_type": registro.get("content_type"),
        "tipo_no_sei": (registro.get("icone") or "").removesuffix(".svg") or None,
        "data_download": registro.get("data"),
        "formato": extensao,
        "num_paginas": len(paginas),
        "paginas_sem_texto": paginas_sem_texto,
        "provavelmente_escaneado": extensao == "pdf" and bool(paginas)
        and sum(1 for p in paginas if p.get("metodo") != "texto" or len(p["texto"]) < MIN_CHARS_PAGINA) / len(paginas) >= 0.5,
        "metodo_extracao": "ocr" if info.get("paginas_ocr") else "texto",
        "detalhes_extracao": info,
        "data_extracao": date.today().isoformat(),
        "paginas": paginas,
        "texto_completo": texto_completo,
    }
    destino = OUTPUT_DIR / caminho.parent.name / f"{numero}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        **resumo,
        "status": "extraido" if caracteres >= MIN_CHARS_PAGINA else "sem_texto",
        "num_paginas": len(paginas),
        "paginas_sem_texto": len(paginas_sem_texto),
        "caracteres": caracteres,
        "paginas_ocr": info.get("paginas_ocr", 0),
        "ocr_truncado": info.get("ocr_truncado", False),
        "membros_sem_extrator": info.get("membros_sem_extrator") or None,
        "membros_com_erro": info.get("membros_com_erro") or None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ocr", action="store_true", help="OCR nas páginas sem texto e nas imagens (requer Tesseract)")
    parser.add_argument("--reprocessar", action="store_true", help="Reprocessa documentos que já têm JSON de saída")
    parser.add_argument("--processos", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                        help="Número de processos em paralelo")
    parser.add_argument("--limite", type=int, default=None, help="Processa só os N primeiros (teste)")
    args = parser.parse_args()

    # Cada processo do Tesseract fica com uma thread: o paralelismo é por documento.
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")

    documentos = json.loads(MANIFESTO.read_text(encoding="utf-8"))["documentos"]
    baixados = {n: d for n, d in documentos.items() if d.get("status") == "baixado"}
    print(f"{len(baixados)} documento(s) baixado(s) no manifesto.")

    resumos_anteriores = {}
    if RESUMO.exists():
        resumos_anteriores = {r["numero_sei"]: r for r in json.loads(RESUMO.read_text(encoding="utf-8"))["documentos"]}

    fila, resumos = [], {}
    for numero, registro in baixados.items():
        destino = OUTPUT_DIR / Path(registro["arquivo"]).parent.name / f"{numero}.json"
        if destino.exists() and not args.reprocessar and numero in resumos_anteriores:
            resumos[numero] = resumos_anteriores[numero]
        else:
            fila.append((numero, registro))
    if args.limite:
        fila = fila[: args.limite]
    print(f"{len(resumos)} já extraído(s); {len(fila)} na fila; {args.processos} processo(s); OCR {'ligado' if args.ocr else 'desligado'}.\n")

    def gravar_resumo():
        RESUMO.parent.mkdir(parents=True, exist_ok=True)
        RESUMO.write_text(json.dumps({
            "atualizado_em": datetime.now().isoformat(timespec="seconds"),
            "ocr": args.ocr,
            "contagem_por_status": dict(Counter(r["status"] for r in resumos.values())),
            "documentos": sorted(resumos.values(), key=lambda r: (r["processo"], r["numero_sei"])),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    with ProcessPoolExecutor(max_workers=args.processos) as pool:
        futuros = {pool.submit(processar_documento, n, r, args.ocr): n for n, r in fila}
        for feitos, futuro in enumerate(as_completed(futuros), start=1):
            numero = futuros[futuro]
            try:
                r = futuro.result()
            except Exception as erro:  # processo filho morreu (ex.: falta de memória)
                r = {"numero_sei": numero, "processo": baixados[numero]["processo"],
                     "extensao": Path(baixados[numero]["arquivo"]).suffix.lower().lstrip("."),
                     "status": "erro", "erro": type(erro).__name__}
            resumos[numero] = r
            detalhe = f"{r.get('num_paginas', 0)} pág., {r.get('caracteres', 0)} car." if "caracteres" in r else r.get("erro", "")
            ocr = f", OCR em {r['paginas_ocr']} pág." if r.get("paginas_ocr") else ""
            saida = sys.stdout if r["status"] in ("extraido", "sem_texto") else sys.stderr
            print(f"  [{feitos}/{len(fila)}] {numero} ({r['extensao']}) — {r['status']} {detalhe}{ocr}", file=saida, flush=True)
            if feitos % 50 == 0:
                gravar_resumo()
    gravar_resumo()

    print(f"\n{'=' * 50}\nCONCLUÍDO")
    for status, total in Counter(r["status"] for r in resumos.values()).most_common():
        print(f"  {status:22} {total}")
    print(f"  Saída:  {OUTPUT_DIR}\n  Resumo: {RESUMO}")


if __name__ == "__main__":
    main()
