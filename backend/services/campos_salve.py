"""Resposta direta, sem LLM, para perguntas sobre dois campos estruturados das
fichas SALVE: a justificativa da avaliação (seção Visão geral) e o histórico
de avaliação de risco (seção Conservação).

Motivo (interação 1415, 2026-11-17): perguntado pela justificativa da
categoria LC de Acanthochelys radiolata, com o campo "Justificativa da
avaliação:" pronto no primeiro trecho, o qwen2.5:3b reescreveu a resposta
misturando a justificativa com o histórico de avaliações e afirmou que a
espécie era LC "desde 2007" nos estados, quando as estaduais de 2005-2008
foram DD. Em quatro gerações do mesmo prompt, só uma resumiu a justificativa
sem erro. Quando o texto pedido já existe pronto num campo da ficha, copiá-lo
é mais fiel que pedir ao modelo para reescrevê-lo.

Só responde quando tudo é inequívoco; em qualquer dúvida devolve None e a
pergunta segue o caminho normal (LLM + verificação de fundamentação):
- a pergunta pede exatamente um dos dois campos;
- exatamente uma ficha SALVE entre os trechos recuperados tem o nome
  científico (gênero + epíteto) ou um nome comum de duas ou mais palavras
  citado na pergunta;
- o trecho com o campo dessa ficha está entre os recuperados (numa medição
  com 8 espécies e 24 perguntas, esteve em todas) e o campo está completo
  nele. Medido sobre todas as fichas em 2026-11-17: a justificativa é
  extraível em 1.790 de 1.816 e o histórico em 1.623 de 1.731; nos outros
  casos o campo pode continuar na parte seguinte da seção e a pergunta vai
  para o LLM.

A ficha é identificada só entre os trechos recuperados. Quando a pergunta
cita a espécie pelo nome comum, quem garante que a ficha venha na busca é o
roteamento por espécie (`especies_salve.py`).
"""

import re
from dataclasses import dataclass
from typing import Literal

from backend.schemas import ChunkRecuperado
from backend.services.especies_salve import nomes_da_especie
from backend.services.normalizacao import normalizar
from backend.services.roteamento import detectar_categorias_risco

CampoSalve = Literal["justificativa", "historico"]

_PADRAO_PEDE_JUSTIFICATIVA = re.compile(
    r"\bjustificativ\w*"
    r"|\bpor\s*qu[eê]\b.{0,80}?\b(?:classificad|avaliad|categori|considerad|listad|enquadrad)"
    r"|\b(?:motivos?|raz[ãa]o|raz[õo]es)\b.{0,40}?\b(?:classifica|avalia|categori|enquadra)",
    re.IGNORECASE,
)
_PADRAO_PEDE_HISTORICO = re.compile(
    r"\bhist[óo]rico\b.{0,40}?\b(?:avalia|categori|risco|classifica)"
    r"|\bavalia[çc][õo]es\s+(?:anteriores|passadas|ao\s+longo)"
    r"|\bcategorias?\s+anteriores",
    re.IGNORECASE,
)

_ROTULO_JUSTIFICATIVA = "Justificativa da avaliação:"
_ROTULO_HISTORICO = "Histórico de avaliação de risco:"
# Rótulos que vêm logo depois da justificativa na seção Visão geral.
_FIM_JUSTIFICATIVA = re.compile(r"\n\s*\n(?:Autoria|Citação recomendada):")
_PADRAO_CATEGORIA = re.compile(r"^Categoria de risco:\s*(.+)$", re.MULTILINE)
_PADRAO_CODIGO_CATEGORIA = re.compile(r"\(([A-Z]{2,5})\)\s*$")


@dataclass
class RespostaCampo:
    campo: CampoSalve
    texto: str
    chunk: ChunkRecuperado


def detectar_campo_pedido(pergunta: str) -> CampoSalve | None:
    pede_justificativa = _PADRAO_PEDE_JUSTIFICATIVA.search(pergunta) is not None
    pede_historico = _PADRAO_PEDE_HISTORICO.search(pergunta) is not None
    if pede_justificativa == pede_historico:
        return None  # nenhum, ou os dois (deixa o LLM combinar)
    return "justificativa" if pede_justificativa else "historico"


def _nome_comum_do_cabecalho(chunk: ChunkRecuperado) -> str | None:
    """Nomes comuns do cabeçalho do trecho ("Espécie: <documento> (nome 1,
    nome 2, ...)"), no mesmo formato do campo `nome_comum` do payload."""
    primeira_linha = chunk.texto.split("\n", 1)[0]
    prefixo = f"Espécie: {chunk.documento}"
    if primeira_linha.startswith(prefixo):
        resto = primeira_linha[len(prefixo):].strip()
        if resto.startswith("(") and resto.endswith(")"):
            return resto[1:-1]
    return None


def identificar_ficha(pergunta: str, chunks: list[ChunkRecuperado]) -> str | None:
    """Documento da única ficha SALVE recuperada cujo nome (mesmas regras do
    catálogo, `especies_salve.nomes_da_especie`) aparece na pergunta; None se
    nenhuma ou mais de uma."""
    pergunta_normalizada = f" {normalizar(pergunta)} "
    encontradas = {
        c.documento
        for c in chunks
        if c.fonte == "salve"
        and any(
            f" {nome} " in pergunta_normalizada
            for nome in nomes_da_especie(c.documento, _nome_comum_do_cabecalho(c))
        )
    }
    return encontradas.pop() if len(encontradas) == 1 else None


def extrair_justificativa(texto: str) -> str | None:
    """Texto do campo, só se terminar dentro do trecho (seguido de Autoria ou
    Citação recomendada); senão pode continuar na parte seguinte da seção."""
    inicio = texto.find(_ROTULO_JUSTIFICATIVA)
    if inicio < 0:
        return None
    corpo = texto[inicio + len(_ROTULO_JUSTIFICATIVA):]
    fim = _FIM_JUSTIFICATIVA.search(corpo)
    if fim is None:
        return None
    justificativa = corpo[: fim.start()].strip()
    return justificativa or None


def extrair_historico(texto: str, ultima_parte: bool = False) -> list[str] | None:
    """Itens "- ..." logo abaixo do rótulo, só se a lista terminar dentro do
    trecho: numa linha em branco ou, se o trecho for a última parte da seção
    (`ultima_parte`), no fim do texto. Senão pode continuar na parte
    seguinte."""
    inicio = texto.find(_ROTULO_HISTORICO)
    if inicio < 0:
        return None
    linhas = texto[inicio + len(_ROTULO_HISTORICO):].lstrip("\n").rstrip().split("\n")
    itens = []
    for linha in linhas:
        if not linha.startswith("- "):
            return itens if itens and not linha.strip() else None
        itens.append(linha[2:].strip())
    return itens if itens and ultima_parte else None


def _categoria(chunk: ChunkRecuperado) -> str | None:
    m = _PADRAO_CATEGORIA.search(chunk.texto)
    return m.group(1).strip() if m else None


def _observacao_categoria(pergunta: str, categoria: str | None) -> str:
    """Aviso quando a pergunta cita uma categoria diferente da registrada na
    ficha (ex.: "por que X é VU?" para uma espécie LC)."""
    if not categoria:
        return ""
    codigo = _PADRAO_CODIGO_CATEGORIA.search(categoria)
    citadas = detectar_categorias_risco(pergunta)
    if not codigo or not citadas or codigo.group(1) in citadas:
        return ""
    return (
        f"Observação: a pergunta menciona {', '.join(citadas)}, mas a categoria "
        f"registrada na ficha é {categoria}.\n\n"
    )


def responder_campo_salve(pergunta: str, chunks: list[ChunkRecuperado]) -> RespostaCampo | None:
    campo = detectar_campo_pedido(pergunta)
    if campo is None:
        return None
    documento = identificar_ficha(pergunta, chunks)
    if documento is None:
        return None

    da_ficha = [c for c in chunks if c.fonte == "salve" and c.documento == documento]
    if campo == "justificativa":
        for chunk in da_ficha:
            justificativa = extrair_justificativa(chunk.texto)
            if justificativa:
                categoria = _categoria(chunk)
                classificada = f" foi avaliada como {categoria}" if categoria else ""
                texto = (
                    _observacao_categoria(pergunta, categoria)
                    + f"Segundo a ficha do SALVE, {documento}{classificada}. "
                    "Justificativa da avaliação, transcrita da ficha:\n\n"
                    + "\n".join(f"> {linha}" if linha else ">" for linha in justificativa.split("\n"))
                )
                return RespostaCampo(campo, texto, chunk)
    else:
        for chunk in da_ficha:
            ultima_parte = chunk.parte is not None and chunk.parte == chunk.n_partes
            itens = extrair_historico(chunk.texto, ultima_parte)
            if itens:
                categoria = _categoria(chunk)
                atual = f"\n\nCategoria atual registrada na ficha: {categoria}." if categoria else ""
                texto = (
                    _observacao_categoria(pergunta, categoria)
                    + f"Histórico de avaliação de risco de {documento}, transcrito da ficha do SALVE:\n\n"
                    + "\n".join(f"- {item}" for item in itens)
                    + atual
                )
                return RespostaCampo(campo, texto, chunk)
    return None
