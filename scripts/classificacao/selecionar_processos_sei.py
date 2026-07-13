"""Seleção de processos do SEI para revisão de exportação (versão corrigida).

Reproduz os dois critérios documentados em docs/processos/selecao_processos_sei.md
e no ADR 0004, a partir do catálogo bruto já coletado (nenhum novo acesso ao
SEI é feito aqui):

  Critério 1 — tipo de processo técnico (ver TIPOS_ACEITOS)
  Critério 2 — pelo menos 1 documento com título técnico e não-administrativo

Esta versão corrige falsos positivos encontrados numa análise manual da saída
anterior (2026-07-13), sem tocar em nenhum documento nem processo além do que
já estava no catálogo:

  1. Casamento por substring sem fronteira de palavra: a versão anterior usava
     `chave in titulo.lower()`, então "ata " batia dentro de "Renata"/"Data
     Logger" e "guia" batia dentro do sobrenome "Aguiar". Aqui a checagem usa
     `\\b<termo>\\b`, então só conta como match uma palavra/frase inteira.
  2. TITULOS_TRAMITE não cobria categorias claramente administrativas que
     apareceram em volume alto na saída anterior — a maior de longe é
     "Relatório de Viagem" (prestação de contas de viagem a serviço; sozinha
     era ~21% de todos os "documentos técnicos" identificados antes desta
     correção, só porque a palavra solta "relatório" está na lista técnica).
     Também prestação de contas, lista de presença, certificado de
     participação, orçamento de evento, guia de trâmite externo, currículo
     Lattes e termo de recebimento de bens.

O que esta correção NÃO tenta resolver (fica para revisão humana):
  - "Publicação" é ambíguo — pode ser uma publicação técnica real (ex.: um
    livro) ou só o registro administrativo de publicação de uma portaria no
    Diário Oficial da União. Não há um padrão textual confiável para separar
    os dois casos automaticamente sem risco de esconder publicações reais,
    então nenhum documento é excluído só por causa disso — ver a seção
    "Observações" no relatório de saída.

Entrada:
    01_fontes_web/sei/documentos_por_processo.json (catálogo bruto, já coletado)

Saídas (mesmo formato da versão anterior, para não quebrar o fluxo de trabalho
da equipe — nenhuma decisão humana existente é sobrescrita, pois todas as
linhas de status_exportacao ainda estavam "pendente" quando esta versão foi
gerada):
    01_fontes_web/sei/processos_para_exportacao.json
    01_fontes_web/sei/processos_descartados.json
    01_fontes_web/sei/processos_descartados.csv
    01_fontes_web/sei/processos_docs.csv

Uso:
    python scripts/classificacao/selecionar_processos_sei.py
"""

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA = RAIZ / "01_fontes_web" / "sei" / "documentos_por_processo.json"
SAIDA_SELECIONADOS = RAIZ / "01_fontes_web" / "sei" / "processos_para_exportacao.json"
SAIDA_DESCARTADOS_JSON = RAIZ / "01_fontes_web" / "sei" / "processos_descartados.json"
SAIDA_DESCARTADOS_CSV = RAIZ / "01_fontes_web" / "sei" / "processos_descartados.csv"
SAIDA_DOCS_CSV = RAIZ / "01_fontes_web" / "sei" / "processos_docs.csv"

# Critério 1 — tipos aceitos (ver docs/processos/selecao_processos_sei.md e ADR 0004)
TIPOS_ACEITOS = {
    # Fauna e espécies
    "FAUNA", "ESPÉCIES AMEAÇADAS", "ESPÉCIES EXÓTICAS INVASORAS",
    "CAPTURA DE EXEMPLARES", "MANEJO DE ANIMAIS",
    # Planejamento e conservação
    "PLANO", "PLANO DE MANEJO", "IMPLEMENTAÇÃO DE PAN", "PROJETO",
    "PROJETO DE PESQUISA",
    # Monitoramento e pesquisa
    "MONITORAMENTO", "PESQUISA", "ESTUDO",
    # Documentos normativos
    "INSTRUÇÃO NORMATIVA", "PORTARIA", "PARECER",
    # Publicações e guias
    "PUBLICAÇÃO", "PUBLICAÇÃO BIBLIOGRÁFICA", "GUIA",
    # Cooperação
    "COOPERAÇÃO TÉCNICA", "DADOS GEOESPACIAIS",
    # Atividades institucionais
    "OFICINA", "CURSO DE CAPACITAÇÃO", "GRUPO DE TRABALHO", "COMITÊ",
    "PROPOSTA",
    # Informação/Consultoria
    "INFORMAÇÃO", "CONSULTORIA", "RELATÓRIO", "RELATÓRIO DE ATIVIDADE",
    "MOÇÃO",
}

# Critério 2 — termos que indicam título técnico
TITULOS_TECNICOS = [
    "relatório", "nota técnica", "informação técnica", "it", "ata", "matriz",
    "plano", "estudo", "laudo", "parecer", "portaria", "instrução normativa",
    "publicação", "guia", "manual", "inventário", "diagnóstico", "ficha",
    "resultado", "monitoramento", "expedição", "oficina", "planilha",
    "formulário de campo", "relatório de campo", "relatório final",
    "relatório técnico", "relatório de atividade", "relatório mensal",
    "moção", "termo de referência", "projeto", "protocolo de monitoramento",
    "relatório fotográfico",
]

# Termos que indicam tramitação/administrativo puro — mesmo que um termo
# técnico também apareça no título, a presença de qualquer um destes descarta
# o documento. Lista original (docs/processos/selecao_processos_sei.md) +
# categorias administrativas confirmadas na análise de 2026-07-13 (marcadas
# com comentário).
TITULOS_TRAMITE = [
    "memorando abertura", "despacho", "ofício", "oficio", "e-mail", "convite",
    "encaminhamento", "solicitação", "autorização", "recibo", "nota de empenho",
    "certidão", "declaração", "comunicação interna", "ci", "memorando",
    "protocolo", "minuta", "planilha de custos", "comprovante", "passagem",
    "bilhete", "ordem bancária",
    # --- adicionados em 2026-07-13 (análise de falsos positivos) ---
    "relatório de viagem",       # ~21% de todos os docs "técnicos" antes desta correção
    "pedido de viagem",
    "prestação de contas",
    "lista de presença",
    "certificado participantes", "certificado de participação",
    "orçamento",
    "programação",               # programação/agenda de evento (oficina, curso)
    "guia de trâmite externo",   # termo formal do SEI p/ roteamento externo — não é "guia" de conteúdo
    "currículo lattes",
    "termo de recebimento de bens",
]


def _padrao(termo: str) -> re.Pattern:
    """Cada termo vira um regex com fronteira de palavra nas duas pontas, para
    não casar dentro de outra palavra (ex.: "ata" não deve casar em "Renata"
    nem em "Data"; "guia" não deve casar em "Aguiar")."""
    return re.compile(r"\b" + re.escape(termo) + r"\b", re.IGNORECASE)


PADROES_TECNICOS = [(t, _padrao(t)) for t in TITULOS_TECNICOS]
PADROES_TRAMITE = [(t, _padrao(t)) for t in TITULOS_TRAMITE]


def titulo_e_tecnico(titulo: str) -> tuple[bool, str | None]:
    """Retorna (é_técnico, termo_tramite_que_excluiu -- ou None)."""
    for termo, padrao in PADROES_TRAMITE:
        if padrao.search(titulo):
            return False, termo
    for termo, _padrao_re in PADROES_TECNICOS:
        if _padrao_re.search(titulo):
            return True, None
    return False, None


def extrair_numero_documento(titulo: str, id_interno: str) -> str:
    """Número de documento SEI mencionado no próprio título (entre parênteses
    ou no final), com fallback para o id interno de navegação se o título não
    tiver nenhum número (ex.: título só "Publicação")."""
    m = re.search(r"\((\d{4,})\)\s*$", titulo)
    if m:
        return m.group(1)
    m = re.search(r"(\d{4,})\s*$", titulo)
    if m:
        return m.group(1)
    return id_interno


def classificar(entrada: Path = ENTRADA) -> dict:
    dados = json.loads(entrada.read_text(encoding="utf-8"))
    processos = dados["processos"]

    selecionados = []
    descartados = []

    for proc in processos:
        numero = proc["numero"]
        bloco = proc["bloco"]
        tipo = (proc.get("tipo") or "").strip()
        anotacao = proc.get("anotacao")
        documentos = proc.get("documentos") or []
        total_documentos = proc.get("total_documentos", len(documentos))

        if tipo.upper() not in TIPOS_ACEITOS:
            descartados.append({
                "numero": numero, "bloco": bloco, "tipo": tipo, "anotacao": anotacao,
                "total_documentos": total_documentos,
                "motivo_descarte": "criterio_1_tipo_nao_tecnico",
                "detalhe": f"Tipo de processo '{tipo}' não está na lista de tipos técnicos aceitos.",
            })
            continue

        docs_tecnicos = []
        for doc in documentos:
            titulo = doc.get("titulo") or ""
            eh_tecnico, _termo_exclusao = titulo_e_tecnico(titulo)
            if eh_tecnico:
                docs_tecnicos.append({
                    "titulo": titulo,
                    "numero_documento_sei": extrair_numero_documento(titulo, doc.get("id", "")),
                })

        if not docs_tecnicos:
            descartados.append({
                "numero": numero, "bloco": bloco, "tipo": tipo, "anotacao": anotacao,
                "total_documentos": total_documentos,
                "motivo_descarte": "criterio_2_sem_doc_tecnico",
                "detalhe": "Nenhum título de documento passou no filtro de conteúdo técnico.",
            })
            continue

        selecionados.append({
            "numero": numero, "bloco": bloco, "tipo": tipo, "anotacao": anotacao,
            "total_documentos": total_documentos,
            "docs_tecnicos_identificados": [d["titulo"] for d in docs_tecnicos],
            "docs_tecnicos_detalhado": docs_tecnicos,
            "n_docs_tecnicos": len(docs_tecnicos),
            "status_exportacao": "pendente",
        })

    return {
        "data_coleta_catalogo": dados.get("data_coleta"),
        "total_processos_catalogados": len(processos),
        "selecionados": selecionados,
        "descartados": descartados,
    }


def gerar_saidas(resultado: dict) -> None:
    hoje = date.today().isoformat()

    saida_selecionados = {
        "data_analise": hoje,
        "criterio": "tipo_processo_tecnico + pelo_menos_1_doc_tecnico_no_titulo (v2 — falsos positivos corrigidos em 2026-07-13)",
        "total": len(resultado["selecionados"]),
        "processos": [
            {
                "numero": p["numero"], "bloco": p["bloco"], "tipo": p["tipo"],
                "anotacao": p["anotacao"], "total_documentos": p["total_documentos"],
                "docs_tecnicos_identificados": p["docs_tecnicos_identificados"],
                "n_docs_tecnicos": p["n_docs_tecnicos"],
                "status_exportacao": p["status_exportacao"],
            }
            for p in resultado["selecionados"]
        ],
    }
    SAIDA_SELECIONADOS.write_text(
        json.dumps(saida_selecionados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total_c1 = sum(1 for d in resultado["descartados"] if d["motivo_descarte"] == "criterio_1_tipo_nao_tecnico")
    total_c2 = sum(1 for d in resultado["descartados"] if d["motivo_descarte"] == "criterio_2_sem_doc_tecnico")
    saida_descartados = {
        "data_analise": hoje,
        "descricao": "Processos descartados na triagem automática (não removidos do catálogo — só fora da lista de exportação).",
        "total": len(resultado["descartados"]),
        "total_criterio_1": total_c1,
        "total_criterio_2": total_c2,
        "processos": resultado["descartados"],
    }
    SAIDA_DESCARTADOS_JSON.write_text(
        json.dumps(saida_descartados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with SAIDA_DESCARTADOS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["numero", "bloco", "tipo", "anotacao", "total_documentos", "motivo_descarte", "detalhe"])
        w.writeheader()
        for d in resultado["descartados"]:
            w.writerow(d)

    with SAIDA_DOCS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["numero_processo", "bloco", "tipo", "status_exportacao", "doc_tecnico", "numero_documento_sei"])
        for p in resultado["selecionados"]:
            for doc in p["docs_tecnicos_detalhado"]:
                w.writerow([p["numero"], p["bloco"], p["tipo"], p["status_exportacao"],
                            doc["titulo"], doc["numero_documento_sei"]])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--somente-relatorio", action="store_true",
                         help="Só imprime o resumo, sem sobrescrever os arquivos de saída")
    args = parser.parse_args()

    if not ENTRADA.exists():
        print(f"Catálogo bruto não encontrado: {ENTRADA}", file=sys.stderr)
        sys.exit(1)

    resultado = classificar()
    n_docs_tecnicos = sum(p["n_docs_tecnicos"] for p in resultado["selecionados"])

    print(f"Catálogo bruto: {resultado['total_processos_catalogados']} processos (coleta de {resultado['data_coleta_catalogo']})")
    print(f"Selecionados (Critério 1 + 2): {len(resultado['selecionados'])} processos, {n_docs_tecnicos} documentos técnicos")
    print(f"Descartados: {len(resultado['descartados'])} processos")

    if args.somente_relatorio:
        print("\n--somente-relatorio: nada foi escrito em disco.")
        return

    gerar_saidas(resultado)
    print(f"\nArquivos gerados:")
    print(f"  {SAIDA_SELECIONADOS.relative_to(RAIZ)}")
    print(f"  {SAIDA_DESCARTADOS_JSON.relative_to(RAIZ)}")
    print(f"  {SAIDA_DESCARTADOS_CSV.relative_to(RAIZ)}")
    print(f"  {SAIDA_DOCS_CSV.relative_to(RAIZ)}")
    print("\nLembrete: nenhum documento foi lido nem exportado — isso só refiltra")
    print("títulos já catalogados. A decisão de exportação continua sendo da equipe do RAN.")


if __name__ == "__main__":
    main()
