"""Triagem automática de copyright — publicações científicas (apoio à Fase 3 do roadmap).

Este script NÃO decide o copyright/termos de uso de nenhuma publicação — essa
decisão é humana e da equipe do RAN (ver docs/processos/classificacao_sensibilidade.md).
Diferente da triagem de Monitora/PANs (scripts/classificacao/triagem_sensibilidade.py),
aqui não há texto extraído para varrer (Fase 2.3 do roadmap está pendente, condicionada
a esta própria avaliação) — a classificação usa só os metadados bibliográficos já
levantados em 06_inventario/catalogo_publicacoes_ran.json (pasta de origem, tipologia,
autor, fonte/veículo, DOI).

As regras vêm da avaliação preliminar por grupo já registrada em
docs/processos/catalogacao_publicacoes.md (seção "Observações sobre dados sensíveis"):
boletins/matérias institucionais do próprio RAN/ICMBio têm risco baixo; artigos, resumos,
livros/capítulos e teses publicados em veículo externo têm risco médio (copyright de
editora/revista/evento — precisa checar política de autoarquivamento); os anais completos
dos Congressos Brasileiros de Herpetologia têm risco alto (conteúdo majoritariamente de
terceiros, copyright da Sociedade Brasileira de Herpetologia).

Cada linha da planilha de saída tem colunas em branco (decisao, revisado_por,
data_revisao, observacoes) para a equipe do RAN preencher durante a revisão.

Uso:
    python scripts/classificacao/triagem_copyright_publicacoes.py

Saída:
    06_inventario/triagem_copyright_publicacoes.xlsx
"""

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO = RAIZ / "06_inventario" / "catalogo_publicacoes_ran.json"
SAIDA = RAIZ / "06_inventario" / "triagem_copyright_publicacoes.xlsx"

PASTAS_INSTITUCIONAIS_RAN = {"Boletins_RAN-2015 a 2018", "Matérias_ICMBio-em-Foco_Outros Meios"}

ORDEM_PRIORIDADE = {"ALTO": 0, "MEDIO": 1, "BAIXO": 2, "N/A": 3}
COR_PRIORIDADE = {
    "ALTO": "F8CBAD",
    "MEDIO": "FFE699",
    "BAIXO": "C6E0B4",
    "N/A": "D9D9D9",
}

MOTIVO_CBH = (
    "Anais completos do Congresso Brasileiro de Herpetologia — conteúdo majoritariamente "
    "de terceiros (autores não vinculados ao RAN), copyright da Sociedade Brasileira de "
    "Herpetologia. Recomendação registrada: não indexar o volume inteiro; se houver "
    "interesse, extrair manualmente só os resumos de autoria de pesquisadores do RAN."
)
MOTIVO_INSTITUCIONAL = "Publicação institucional do próprio RAN/ICMBio, sem conteúdo de terceiros."
MOTIVO_OUTROS_ORGAOS = "Publicação de outro órgão público (não é do RAN) — provavelmente aberta, mas confirmar."
MOTIVO_VEICULO_EXTERNO = (
    "Copyright de veículo externo (revista/editora/evento científico) — verificar política "
    "de autoarquivamento antes de indexar o texto completo; considerar usar só resumo/DOI."
)
MOTIVO_PLACEHOLDER = "Marcador de lacuna conhecida ('Faltam') deixado pela equipe — não é um documento real."


def registros(entrada: dict) -> list[dict]:
    m = entrada.get("metadados")
    if not m:
        return []
    return m if isinstance(m, list) else [m]


def classificar_risco(entrada: dict) -> tuple[str, str]:
    if entrada["status"] == "placeholder_faltante":
        return "N/A", MOTIVO_PLACEHOLDER

    caminho = entrada["caminho"]
    nome = Path(caminho).name

    if "/Resumos_CBH_2004-2015/" in caminho:
        return "ALTO", MOTIVO_CBH
    if entrada["pasta_origem"] in PASTAS_INSTITUCIONAIS_RAN or "herpetopan" in nome.lower():
        return "BAIXO", MOTIVO_INSTITUCIONAL
    if entrada["pasta_origem"] == "Outras Publicações Técnicas":
        return "MEDIO", MOTIVO_OUTROS_ORGAOS
    return "MEDIO", MOTIVO_VEICULO_EXTERNO


def resumir_entrada(entrada: dict, entradas_por_caminho: dict) -> dict:
    base = entrada
    motivo_extra = ""
    if entrada["status"] == "duplicata_exata" and entrada.get("duplicata_de"):
        canonico = entradas_por_caminho.get(entrada["duplicata_de"])
        if canonico:
            base = canonico
            motivo_extra = f" [cópia exata de: {entrada['duplicata_de']}]"

    risco, motivo = classificar_risco(base)
    motivo += motivo_extra

    regs = registros(entrada)
    titulo = regs[0].get("titulo") if regs else None
    autor = regs[0].get("autor") if regs else None
    ano = regs[0].get("ano") if regs else entrada.get("ano_extraido_nome")
    fonte_bib = regs[0].get("fonte") if regs else None
    doi = regs[0].get("doi") if regs else None
    tipologia = regs[0].get("tipologia") if regs else None
    if len(regs) > 1:
        titulo = f"{titulo} [+{len(regs) - 1} registro(s)]" if titulo else f"[{len(regs)} registros]"

    return {
        "caminho": entrada["caminho"],
        "pasta_origem": entrada["pasta_origem"],
        "tipologia": tipologia,
        "autor": autor,
        "ano": ano,
        "titulo": titulo,
        "fonte_bibliografica": fonte_bib,
        "doi": doi,
        "status_catalogo": entrada["status"],
        "risco_copyright": risco,
        "motivo_automatico": motivo,
        "decisao": "",
        "revisado_por": "",
        "data_revisao": "",
        "observacoes": "",
    }


COLUNAS = [
    ("caminho", 55),
    ("pasta_origem", 28),
    ("tipologia", 20),
    ("autor", 30),
    ("ano", 8),
    ("titulo", 45),
    ("fonte_bibliografica", 40),
    ("doi", 22),
    ("status_catalogo", 22),
    ("risco_copyright", 14),
    ("motivo_automatico", 60),
    ("decisao", 16),
    ("revisado_por", 16),
    ("data_revisao", 14),
    ("observacoes", 30),
]


def sanitizar(valor):
    """Remove caracteres de controle que o Excel/openpyxl rejeita (comuns em PDFs)."""
    if isinstance(valor, str):
        return ILLEGAL_CHARACTERS_RE.sub("", valor)
    return valor


def gerar_planilha(linhas: list[dict], saida: Path):
    linhas_ordenadas = sorted(
        linhas,
        key=lambda r: (ORDEM_PRIORIDADE[r["risco_copyright"]], r["pasta_origem"] or "", r["titulo"] or ""),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Triagem"

    for col_idx, (nome, largura) in enumerate(COLUNAS, start=1):
        cel = ws.cell(row=1, column=col_idx, value=nome)
        cel.font = Font(bold=True)
        ws.column_dimensions[get_column_letter(col_idx)].width = largura
    ws.freeze_panes = "A2"

    col_risco = next(i for i, (nome, _) in enumerate(COLUNAS, start=1) if nome == "risco_copyright")

    for row_idx, linha in enumerate(linhas_ordenadas, start=2):
        for col_idx, (nome, _largura) in enumerate(COLUNAS, start=1):
            cel = ws.cell(row=row_idx, column=col_idx, value=sanitizar(linha.get(nome)))
            cel.alignment = Alignment(vertical="top", wrap_text=nome in ("motivo_automatico", "fonte_bibliografica", "titulo"))
        cor = COR_PRIORIDADE.get(linha["risco_copyright"])
        if cor:
            ws.cell(row=row_idx, column=col_risco).fill = PatternFill("solid", fgColor=cor)

    # Aba de resumo
    ws2 = wb.create_sheet("Resumo")
    contagem = {"ALTO": 0, "MEDIO": 0, "BAIXO": 0, "N/A": 0}
    for linha in linhas_ordenadas:
        contagem[linha["risco_copyright"]] += 1
    ws2.append(["Risco", "Publicações", "Observação"])
    for col in (1, 2, 3):
        ws2.cell(row=1, column=col).font = Font(bold=True)
    ws2.append(["ALTO", contagem["ALTO"], "Revisar primeiro — conteúdo majoritariamente de terceiros"])
    ws2.append(["MEDIO", contagem["MEDIO"], "Revisar em seguida — copyright de veículo externo, checar política"])
    ws2.append(["BAIXO", contagem["BAIXO"], "Institucional do RAN/ICMBio — recomenda-se amostragem, não pular"])
    ws2.append(["N/A", contagem["N/A"], "Marcador de lacuna ('Faltam') — não é documento real, não entra na revisão"])
    ws2.append(["TOTAL", len(linhas_ordenadas), ""])
    for col, largura in [("A", 14), ("B", 14), ("C", 70)]:
        ws2.column_dimensions[col].width = largura

    saida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(saida)


def main():
    if not CATALOGO.exists():
        print(f"{CATALOGO} não encontrado — rode scripts/coleta/catalogar_publicacoes_ran.py antes.")
        return

    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    entradas = catalogo["arquivos"]
    entradas_por_caminho = {e["caminho"]: e for e in entradas}

    linhas = [resumir_entrada(e, entradas_por_caminho) for e in entradas]

    gerar_planilha(linhas, SAIDA)

    contagem = {"ALTO": 0, "MEDIO": 0, "BAIXO": 0, "N/A": 0}
    for linha in linhas:
        contagem[linha["risco_copyright"]] += 1

    print(f"Triagem concluída — {len(linhas)} publicações analisadas.")
    print(f"  ALTO risco:  {contagem['ALTO']}")
    print(f"  MEDIO risco: {contagem['MEDIO']}")
    print(f"  BAIXO risco: {contagem['BAIXO']}")
    print(f"  N/A:         {contagem['N/A']}")
    print(f"\nPlanilha salva em {SAIDA.relative_to(RAIZ)}")
    print("\nLembrete: este script só classifica por regras de metadados — a decisão final")
    print("de copyright/termos de uso é humana da equipe do RAN, coluna 'decisao'.")


if __name__ == "__main__":
    main()
