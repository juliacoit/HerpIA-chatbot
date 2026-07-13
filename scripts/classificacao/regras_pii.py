"""Padrões de dados sensíveis (Monitora/PANs) — fonte única compartilhada.

Usado por dois pontos do pipeline:
  - triagem_sensibilidade.py: só sinaliza ocorrências para revisão humana
    (planilha `06_inventario/triagem_sensibilidade_monitora_pans.xlsx`).
  - gerar_chunks.py (scripts/processamento): redige automaticamente, no
    momento do chunking, os padrões marcados como `redigivel=True`.

Manter as duas etapas na mesma lista evita que detecção (o que a equipe do
RAN vê na planilha) e redação automática (o que efetivamente é indexado)
fiquem dessincronizadas.

Por que só alguns padrões são `redigivel=True`: CPF, e-mail, telefone e
coordenadas são estruturados — o regex tem alta precisão e substituição
automática é seguro. "Palavra de restrição administrativa", "menção a
localização de espécie" e "dado pessoal genérico" são padrões semânticos —
o regex serve só para priorizar a revisão humana; redigir automaticamente
geraria falsos positivos/negativos demais (ex.: apagar a palavra "CPF" de
uma frase sobre exigência documental, sem nenhum CPF real presente).

Cada item é uma tupla:
    (chave, regex, severidade, descricao, redigivel, placeholder)
"""

import re

FLAGS = [
    (
        "cpf",
        re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
        "ALTA",
        "Possível CPF",
        True,
        "[CPF removido]",
    ),
    (
        "email",
        re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
        "ALTA",
        "E-mail pessoal",
        True,
        "[e-mail removido]",
    ),
    (
        "telefone",
        re.compile(r"\(\d{2}\)\s?\d{4,5}-?\d{4}\b"),
        "MEDIA",
        "Telefone",
        True,
        "[telefone removido]",
    ),
    (
        "coordenada_decimal",
        re.compile(r"-?\d{1,2}[.,]\d{4,8}\s*[,;]\s*-?\d{1,3}[.,]\d{4,8}"),
        "ALTA",
        "Par de coordenadas decimais",
        True,
        "[coordenada removida]",
    ),
    (
        "coordenada_dms",
        re.compile(r"\d{1,3}\s*°\s*\d{1,2}\s*['′]\s*\d{0,2}(?:[.,]\d+)?\s*[\"″]?\s*[NSEWOnsewo]\b"),
        "ALTA",
        "Coordenada em graus/min/seg",
        True,
        "[coordenada removida]",
    ),
    (
        "utm",
        re.compile(r"\bUTM\b"),
        "MEDIA",
        "Menção a sistema UTM",
        False,
        None,
    ),
    (
        "palavra_restrito",
        re.compile(
            r"\b(sigilos\w*|confidencial\w*|document\w*\s+restrit\w*|acesso\s+restrit\w*|"
            r"circulaç\w*\s+restrit\w*|não\s+divulgar|uso\s+interno|reservad\w*)\b",
            re.I,
        ),
        "ALTA",
        "Palavra indicando restrição administrativa de acesso",
        False,
        None,
    ),
    (
        "palavra_localizacao",
        re.compile(
            r"\b(ponto\s+de\s+ocorrência|área\s+de\s+soltura|sítio\s+de\s+reproduç\w*|"
            r"localiza\w*\s+exata|coordenadas?\s+geográficas?|georreferenciad\w*)\b",
            re.I,
        ),
        "MEDIA",
        "Menção a localização de espécie",
        False,
        None,
    ),
    (
        "dado_pessoal_generico",
        re.compile(r"\b(CPF|RG|passaporte|data\s+de\s+nascimento)\b"),
        "MEDIA",
        "Menção genérica a dado pessoal (sem padrão numérico confirmado)",
        False,
        None,
    ),
]

FLAGS_REDIGIVEIS = [f for f in FLAGS if f[4]]


def redigir_texto(texto: str) -> tuple[str, dict[str, int]]:
    """Substitui ocorrências dos padrões estruturados (redigivel=True) por um
    placeholder. Retorna o texto redigido e a contagem de substituições por
    flag, para alimentar o relatório de auditoria — esses padrões não passam
    por revisão humana linha a linha, só por amostragem.
    """
    contagens: dict[str, int] = {}
    for chave, regex, _severidade, _descricao, _redigivel, placeholder in FLAGS_REDIGIVEIS:
        texto, n = regex.subn(placeholder, texto)
        if n:
            contagens[chave] = n
    return texto, contagens
