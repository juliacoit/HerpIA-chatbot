"""Regras de apresentação da resposta, sem Streamlit — testáveis isoladas
(tests/test_apresentacao_interface.py). `app.py` só desenha o que estas
funções decidem.
"""

ESTADO_RETIDA = "retida"
ESTADO_SEM_EVIDENCIA = "sem_evidencia"
ESTADO_FUNDAMENTADA = "fundamentada"


def estado_resposta(item: dict) -> str:
    """Estado da faixa abaixo da resposta. Precedência: retida > sem
    evidência > fundamentada.

    - retida: a verificação de fundamentação reteve a resposta (ou o prompt
      não coube no contexto) — `resposta_fundamentada` False com chunks
      recuperados;
    - sem evidência: nenhum chunk, bloqueio do SEI (`evidencia_suficiente`
      False) ou abstenção pura aprovada pela camada 0 do verificador
      (`tipo_saida == "abstencao"`);
    - fundamentada: o resto.

    O bloqueio do SEI também vem com `resposta_fundamentada` False, mas não
    é uma retenção: continua "sem evidência", como antes.
    """
    sem_chunks_ou_sei = item.get("evidencia_suficiente") is False
    if item.get("resposta_fundamentada") is False and not sem_chunks_ou_sei:
        return ESTADO_RETIDA
    if sem_chunks_ou_sei or item.get("tipo_saida") == "abstencao":
        return ESTADO_SEM_EVIDENCIA
    return ESTADO_FUNDAMENTADA


def titulo_trechos(estado: str) -> str | None:
    """Título da seção de trechos quando eles não sustentam uma resposta
    (exibida recolhida). None = trechos são citações da resposta (título
    com contagem, sempre aberto)."""
    if estado == ESTADO_RETIDA:
        return "Trechos recuperados (não verificados)"
    if estado == ESTADO_SEM_EVIDENCIA:
        return "Trechos recuperados"
    return None


def agrupar_citacoes(citacoes: list[dict]) -> list[dict]:
    """Um grupo por (fonte, documento), na ordem da primeira citação de cada
    um — que é a ordem do melhor chunk do documento, porque o backend
    devolve as citações na ordem de relevância. Cada grupo:
    {"fonte", "documento", "url_origem", "trechos": [citação, ...]}."""
    grupos: dict[tuple, dict] = {}
    for c in citacoes:
        chave = (c.get("fonte"), c.get("documento"))
        if chave not in grupos:
            grupos[chave] = {
                "fonte": c.get("fonte"),
                "documento": c.get("documento"),
                "url_origem": c.get("url_origem"),
                "trechos": [],
            }
        grupos[chave]["trechos"].append(c)
    return list(grupos.values())


def rotulos_trechos(grupo: dict) -> list[str]:
    """Rótulo do expansor de cada trecho do grupo: páginas (PDF) ou nome da
    seção (ficha SALVE). A parte só aparece quando a mesma seção tem mais de
    um trecho no grupo ("Conservação · parte 1", "Conservação · parte 2")."""
    trechos = grupo["trechos"]
    contagem_secao: dict[str, int] = {}
    for c in trechos:
        if not c.get("pagina_inicio"):
            contagem_secao[c.get("secao") or ""] = contagem_secao.get(c.get("secao") or "", 0) + 1
    rotulos = []
    for c in trechos:
        inicio = c.get("pagina_inicio")
        if inicio:
            fim = c.get("pagina_fim")
            rotulos.append(f"p. {inicio}–{fim}" if fim and fim != inicio else f"p. {inicio}")
            continue
        chave = c.get("secao") or ""
        nome = NOMES_SECOES_SALVE.get(chave, chave or "Trecho")
        parte = c.get("parte")
        rotulos.append(f"{nome} · parte {parte}" if parte and contagem_secao[chave] > 1 else nome)
    return rotulos


# Mesmos nomes de exibição de scripts/processamento/gerar_chunks.py (NOMES_SECOES).
NOMES_SECOES_SALVE = {
    "visao_geral": "Visão geral",
    "taxonomia": "Taxonomia",
    "distribuicao": "Distribuição",
    "historia_natural": "História natural",
    "populacao": "População",
    "ameacas": "Ameaças",
    "uso": "Uso",
    "conservacao": "Conservação",
    "pesquisa": "Pesquisa",
    "referencias": "Referências",
}


def nome_categoria(secao: str) -> str:
    """Categoria de coleta de um PDF, vinda como identificador
    ("materiais-de-apoio"), escrita para leitura ("Materiais de apoio")."""
    texto = secao.replace("-", " ").replace("_", " ").strip()
    return texto[:1].upper() + texto[1:]


def resumo_citacoes(grupos: list[dict]) -> str:
    n_docs = len(grupos)
    n_trechos = sum(len(g["trechos"]) for g in grupos)
    docs = "1 documento" if n_docs == 1 else f"{n_docs} documentos"
    trechos = "1 trecho" if n_trechos == 1 else f"{n_trechos} trechos"
    return f"{docs}, {trechos}"


# Motivos do feedback negativo: código gravado no banco -> rótulo exibido.
# Os códigos são os de MotivoFeedback, em backend/schemas.py
# (tests/test_feedback.py confere que as duas listas não divergem).
MOTIVOS_FEEDBACK = {
    "informacao_incorreta": "Informação incorreta",
    "fonte_errada": "Fonte ou citação errada",
    "incompleta": "Resposta incompleta",
    "nao_respondeu": "Não respondeu, e a base tem a informação",
    "nao_entendeu": "Não entendeu a pergunta",
    "outro": "Outro motivo",
}


def resumo_feedback(avaliacao: int, comentario: str | None) -> str:
    """Aviso que substitui os botões depois do envio."""
    rotulo = "positivo" if avaliacao == 1 else "negativo"
    complemento = ", com comentário" if comentario else ""
    return f"Feedback enviado: {rotulo}{complemento}. Obrigado!"
