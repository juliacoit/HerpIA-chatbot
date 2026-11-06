"""Monta a lista de conferência do piloto de exportação manual do SEI.

Escolhe 10 dos 173 processos autorizados (01_fontes_web/sei/processos_para_exportacao.json)
e gera uma planilha para quem vai exportar pela interface do SEI, com uma linha por
processo (onde anotar tempo gasto, formato e problemas) e uma linha por documento técnico
a exportar (de processos_docs.csv).

Critério de escolha — determinístico, para o piloto ser reproduzível:
  - 10 blocos internos diferentes: os 10 com mais processos autorizados;
  - em cada bloco, o processo cujo número de documentos técnicos fica mais perto de um
    tamanho-alvo. Os alvos variam de 1 a 16 (a mediana do conjunto é 3 e o percentil 90
    é 16) para o piloto medir o tempo em processos pequenos e grandes; blocos maiores
    recebem alvos maiores. Empate: menos documentos no processo, depois o número.

A planilha fica em 01_fontes_web/sei/, fora do git: os títulos dos documentos do SEI
trazem nomes de pessoas. O script não acessa o SEI, só lê os dois arquivos acima.

Uso:
    python scripts/coleta/montar_piloto_exportacao_sei.py
"""

import csv
import json
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

RAIZ = Path(__file__).resolve().parents[2]
PROCESSOS_JSON = RAIZ / "01_fontes_web" / "sei" / "processos_para_exportacao.json"
DOCS_CSV = RAIZ / "01_fontes_web" / "sei" / "processos_docs.csv"
SAIDA_XLSX = RAIZ / "01_fontes_web" / "sei" / "piloto_exportacao_sei.xlsx"
DESTINO_BASE = "04_documentos_pendentes_avaliacao/sei"

# Tamanho-alvo (documentos técnicos) para cada bloco, do maior bloco para o menor.
ALVOS_POR_POSICAO = [16, 10, 7, 5, 3, 3, 2, 1, 3, 1]

INSTRUCOES = [
    "Piloto de exportação manual do SEI — HerpIA (RAN/ICMBio)",
    "",
    "Objetivo: medir quanto tempo a exportação leva e como os arquivos saem, antes de decidir como exportar os 173 processos.",
    "",
    "Para cada processo da aba Processos:",
    "1. Abra o processo no SEI pelo número.",
    "2. Gere um PDF do processo marcando SÓ os documentos listados para ele na aba Documentos (no SEI 4: ícone 'Gerar Arquivo PDF do Processo'). Se preferir, exporte documento por documento.",
    "3. Salve o arquivo na pasta indicada em 'pasta_destino', no computador da Júlia (ou entregue os arquivos a ela).",
    "4. Preencha as colunas em amarelo: quem exportou, data, minutos gastos, formato, se o PDF tem texto selecionável e observações.",
    "5. Na aba Documentos, marque 'exportado' (sim/não) e anote quando um documento não abrir, tiver nível de acesso restrito ou não existir mais.",
    "",
    "Cuidados:",
    "- Não envie os arquivos exportados por e-mail, Google Drive ou outro serviço externo: eles ainda não passaram pela avaliação de sensibilidade.",
    "- Documentos com nível de acesso restrito: não exporte; anote na observação. A decisão sobre eles ainda está em aberto (ADR 0004).",
    "- 'PDF tem texto': abra o PDF e tente selecionar uma frase. Se não der, é imagem e vai precisar de OCR.",
    "",
    "Depois do piloto: os arquivos passam por extração de texto, triagem automática de dados pessoais e avaliação humana de sensibilidade, e só então vão para 03_documentos_autorizados/sei/.",
]

COLUNAS_PROCESSOS = [
    ("ordem", 7), ("numero_processo", 24), ("bloco", 40), ("tipo", 20), ("anotacao", 50),
    ("total_documentos", 10), ("docs_a_exportar", 10), ("tamanho_alvo", 9), ("pasta_destino", 52),
    ("exportado_por", 18), ("data_exportacao", 14), ("minutos_gastos", 10), ("formato", 18),
    ("pdf_tem_texto", 12), ("observacoes", 50),
]
COLUNAS_DOCUMENTOS = [
    ("ordem_processo", 8), ("numero_processo", 24), ("numero_documento_sei", 14),
    ("titulo_documento", 70), ("exportado", 10), ("observacoes", 50),
]
A_PREENCHER = {"exportado_por", "data_exportacao", "minutos_gastos", "formato", "pdf_tem_texto",
               "observacoes", "exportado"}


def escolher_processos(processos: list[dict]) -> list[dict]:
    autorizados = [p for p in processos if p.get("status_exportacao") == "autorizado"]
    contagem = Counter(p["bloco"] for p in autorizados)
    blocos = sorted(contagem, key=lambda b: (-contagem[b], b))[: len(ALVOS_POR_POSICAO)]

    escolhidos = []
    for posicao, bloco in enumerate(blocos):
        alvo = ALVOS_POR_POSICAO[posicao]
        candidatos = [p for p in autorizados if p["bloco"] == bloco]
        melhor = min(candidatos, key=lambda p: (abs(p["n_docs_tecnicos"] - alvo),
                                                 p["total_documentos"], p["numero"]))
        escolhidos.append({**melhor, "tamanho_alvo": alvo})
    return escolhidos


def pasta_destino(numero: str) -> str:
    return f"{DESTINO_BASE}/{numero.replace('/', '-')}/"


def formatar_aba(ws, colunas: list[tuple[str, int]]) -> None:
    amarelo = PatternFill("solid", fgColor="FFF4C2")
    for i, (nome, largura) in enumerate(colunas, start=1):
        celula = ws.cell(row=1, column=i)
        celula.font = Font(bold=True)
        celula.alignment = Alignment(wrap_text=True, vertical="top")
        if nome in A_PREENCHER:
            celula.fill = amarelo
        ws.column_dimensions[celula.column_letter].width = largura
    ws.freeze_panes = "C2"
    for linha in ws.iter_rows(min_row=2):
        for celula in linha:
            celula.alignment = Alignment(wrap_text=True, vertical="top")


def lista_suspensa(ws, coluna: str, opcoes: list[str], n_linhas: int) -> None:
    validacao = DataValidation(type="list", formula1='"' + ",".join(opcoes) + '"', allow_blank=True)
    ws.add_data_validation(validacao)
    validacao.add(f"{coluna}2:{coluna}{n_linhas + 1}")


def main() -> None:
    processos = json.loads(PROCESSOS_JSON.read_text(encoding="utf-8"))["processos"]
    with DOCS_CSV.open(encoding="utf-8", newline="") as f:
        documentos = list(csv.DictReader(f))

    escolhidos = escolher_processos(processos)

    wb = Workbook()
    ws_inst = wb.active
    ws_inst.title = "Instruções"
    for linha in INSTRUCOES:
        ws_inst.append([linha])
    ws_inst["A1"].font = Font(bold=True, size=13)
    ws_inst.column_dimensions["A"].width = 130
    for linha in ws_inst.iter_rows():
        linha[0].alignment = Alignment(wrap_text=True, vertical="top")

    ws_proc = wb.create_sheet("Processos")
    ws_proc.append([nome for nome, _ in COLUNAS_PROCESSOS])
    ws_docs = wb.create_sheet("Documentos")
    ws_docs.append([nome for nome, _ in COLUNAS_DOCUMENTOS])

    total_docs = 0
    for ordem, p in enumerate(escolhidos, start=1):
        docs_do_processo = [d for d in documentos if d["numero_processo"] == p["numero"]]
        assert len(docs_do_processo) == p["n_docs_tecnicos"], p["numero"]
        total_docs += len(docs_do_processo)
        ws_proc.append([ordem, p["numero"], p["bloco"], p["tipo"], p.get("anotacao") or "",
                        p["total_documentos"], p["n_docs_tecnicos"], p["tamanho_alvo"],
                        pasta_destino(p["numero"]), "", "", None, "", "", ""])
        for d in docs_do_processo:
            ws_docs.append([ordem, p["numero"], d["numero_documento_sei"], d["doc_tecnico"], "", ""])

    formatar_aba(ws_proc, COLUNAS_PROCESSOS)
    formatar_aba(ws_docs, COLUNAS_DOCUMENTOS)
    lista_suspensa(ws_proc, "M", ["PDF do processo", "PDF por documento", "ZIP", "outro"], len(escolhidos))
    lista_suspensa(ws_proc, "N", ["sim", "não", "parcial"], len(escolhidos))
    lista_suspensa(ws_docs, "E", ["sim", "não"], total_docs)

    wb.save(SAIDA_XLSX)

    print(f"Piloto: {len(escolhidos)} processos, {total_docs} documentos técnicos "
          f"({total_docs / sum(p['n_docs_tecnicos'] for p in processos):.1%} do total).")
    for ordem, p in enumerate(escolhidos, start=1):
        print(f"  {ordem:2}. {p['n_docs_tecnicos']:3} docs (alvo {p['tamanho_alvo']:2}) | {p['tipo'][:22]:22} | bloco #{ordem}")
    print(f"Planilha: {SAIDA_XLSX.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
