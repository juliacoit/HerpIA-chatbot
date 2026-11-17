"""Monta o prompt de geração a partir dos chunks recuperados e formata a
resposta final com citações de fonte.

Regra do projeto (CLAUDE.md): responder só com base nos trechos
recuperados, sempre citando a fonte, e indicar claramente quando não há
evidência suficiente em vez de inventar uma resposta.

`evidencia_suficiente` só reflete se algum chunk foi recuperado — não se a
resposta do LLM realmente se apoiou neles. Quem verifica isso de fato é
`resposta_fundamentada`, calculado por `backend.services.groundedness`
depois da geração (ver docstring daquele módulo para o motivo de precisar
das duas camadas de checagem).
"""

import re

from backend.config import Settings
from backend.schemas import (
    ChunkRecuperado,
    Citacao,
    ContextoAvaliacao,
    DadosAvaliacao,
    OrigemRetencao,
    PerguntarResponse,
    TipoSaida,
)
from backend.services.campos_salve import responder_campo_salve
from backend.services.groundedness import verificar_groundedness_detalhado
from backend.services.llm import ContextoExcedidoError, LLMClient

# SEI nunca está indexado (ver CLAUDE.md, "Fontes de dados" — acesso restrito,
# só documentos previamente exportados/autorizados entram na base), então
# nenhum chunk tem fonte == "sei" hoje. Perguntas que nomeiam SEI explicitamente
# ainda recuperam chunks de outras fontes (pans, salve...) por similaridade
# semântica frouxa, e o achado G1 (diagnosticos/teste-perguntas-dominio.md)
# mostrou o LLM especulando sobre "o processo SEI mais recente" a partir
# desses chunks não relacionados — reforço de prompt sozinho não elimina isso
# de forma confiável (falhou em 3 de 3 reexecuções). Checagem estrutural:
# comparar o fonte dos chunks recuperados contra o tipo de documento nomeado
# na pergunta pega esse padrão de forma determinística, sem depender do juízo
# do LLM de 3B. Só cobre SEI (único caso hoje com fonte inteira ausente do
# corpus) — não generaliza para "documento nomeado que não existe dentro de
# uma fonte já indexada" (padrão do achado F1), que exigiria um catálogo de
# documentos indexados pra comparar contra, não implementado.
_PADRAO_MENCAO_SEI = re.compile(r"\bSEI\b")


def _pergunta_pede_sei_nao_indexado(pergunta: str, chunks: list[ChunkRecuperado]) -> bool:
    return bool(_PADRAO_MENCAO_SEI.search(pergunta)) and not any(
        c.fonte == "sei" for c in chunks
    )


# Mensagem exibida no lugar de uma resposta retida pela verificação. Até
# 2026-11 era `groundedness.MENSAGEM_NAO_FUNDAMENTADA`, que manda o usuário
# "consultar diretamente as fontes citadas abaixo" — mas abaixo de uma
# retida só há trechos recuperados, não verificados, muitas vezes sem
# relação com a pergunta (#794, diagnóstico da sessão RAN de 26/10). O texto
# fica aqui, e não em groundedness.py, porque quem troca a resposta pela
# mensagem é este módulo; o verificador não muda.
MENSAGEM_RETENCAO = (
    "Não foi possível confirmar que a resposta gerada está totalmente "
    "apoiada nos trechos recuperados da base de conhecimento, então ela "
    "foi retida para evitar apresentar uma informação não verificada. "
    "Tente reformular a pergunta de forma mais específica."
)

MENSAGEM_CONTEXTO_EXCEDIDO = (
    "Não foi possível gerar a resposta: os trechos recuperados para esta "
    "pergunta são longos demais para o modelo de linguagem. Tente uma "
    "pergunta mais específica."
)

PROMPT_SISTEMA = (
    "Você é um assistente do RAN/ICMBio especializado em répteis e anfíbios "
    "(herpetofauna). Responda à pergunta do usuário usando SOMENTE as "
    "informações nos trechos abaixo. Nunca use conhecimento externo aos "
    "trechos — isso inclui definições, classificações taxonômicas ou fatos "
    "gerais que pareçam óbvios ou de conhecimento comum, mas que não estejam "
    "escritos explicitamente nos trechos. "
    "Trechos sobre temas parecidos ou vagamente relacionados à pergunta, mas "
    "que não a respondem diretamente, contam como evidência insuficiente — "
    "nunca escreva respostas especulativas ou hedgeadas (ex.: "
    "'provavelmente', 'possivelmente', 'pode ser que', 'é possível que "
    "cubra') como forma de contornar essa falta de evidência. Se os trechos "
    "não tiverem informação suficiente para responder, diga isso "
    "explicitamente em vez de inventar ou especular uma resposta. "
    "Preste atenção especial quando a pergunta nomear um documento, "
    "processo ou fonte específica (ex.: um número de processo SEI, uma "
    "norma, um plano nomeado): se nenhum trecho for de fato sobre esse "
    "documento/processo específico, diga que não há evidência sobre ele — "
    "nunca descreva o conteúdo de um trecho sobre um documento diferente "
    "como se fosse o conteúdo do documento perguntado, mesmo que os temas "
    "sejam parecidos (ex.: outro processo de licenciamento, outra norma "
    "sobre o mesmo assunto geral). Nesse caso, diga explicitamente que não "
    "encontrou esse documento/processo específico na base — não trate a "
    "pergunta como se o documento existisse e apenas faltassem detalhes "
    "sobre ele. "
    "Nem sempre existe um único trecho que responda à pergunta inteira: se "
    "vários trechos parciais (ex.: fichas de espécies diferentes) juntos "
    "cobrem a resposta, sintetize uma resposta agregada combinando as "
    "informações desses trechos, citando cada um deles — não exija um "
    "trecho único e completo antes de responder. Isso é diferente de "
    "especular: síntese combina o que os trechos realmente dizem, "
    "especulação inventa o que eles provavelmente diriam. "
    "Revise TODOS os trechos fornecidos antes de responder, não só os "
    "primeiros — um trecho mais adiante na lista pode conter a evidência "
    "mais direta (ex.: uma seção 'População' descrevendo ocorrência real "
    "numa área específica é mais confiável que uma lista de referências "
    "bibliográficas). Quando a pergunta pedir espécies de um bioma "
    "específico e os trechos forem fichas de espécie no formato 'Espécie: "
    "... Bioma: ...', o campo 'Bioma:' é a fonte confiável para decidir se "
    "a espécie ocorre ali — use exatamente essa lista, não infira do resto "
    "do texto. Inclua só espécies cujo campo 'Bioma:' contenha o bioma "
    "perguntado, mesmo que outra parte do trecho (ex.: uma referência "
    "bibliográfica) mencione esse bioma em outro contexto; e não inclua "
    "uma espécie de bioma diferente só porque ela apareceu entre os "
    "trechos recuperados."
)


def montar_prompt(pergunta: str, chunks: list[ChunkRecuperado]) -> str:
    trechos = "\n\n".join(
        f"[Trecho {i + 1} — fonte: {c.fonte}, documento: {c.documento}]\n{c.texto}"
        for i, c in enumerate(chunks)
    )
    return f"{PROMPT_SISTEMA}\n\nTrechos recuperados:\n{trechos}\n\nPergunta: {pergunta}\n\nResposta:"


def _chave_citacao(c: ChunkRecuperado) -> tuple:
    """Chave de agrupamento de chunks em citações.

    PDFs (Monitora/PANs) são identificados pelas páginas: chunks do mesmo
    documento com o mesmo intervalo de páginas viram uma citação só (o
    mesmo PDF indexado em duas categorias, por exemplo). Fichas SALVE não
    têm página: até 2026-11 a chave era a mesma dos PDFs, e todas as seções
    de uma ficha colapsavam numa citação com o texto do primeiro chunk —
    18,9% dos chunks enviados ao LLM nunca apareciam na tela
    (diagnosticos/2026-11-04_sessao_supervisionada_ran.md, H1). Sem página,
    a chave passa a ser a seção e a parte da seção.
    """
    if c.pagina_inicio is None and c.pagina_fim is None:
        return (c.fonte, c.documento, "secao", c.secao, c.parte)
    return (c.fonte, c.documento, "paginas", c.pagina_inicio, c.pagina_fim)


SEPARADOR_TRECHOS = "\n\n[…]\n\n"


def montar_citacoes(chunks: list[ChunkRecuperado]) -> list[Citacao]:
    """Uma citação por chave de `_chave_citacao`, na ordem do primeiro chunk
    de cada uma (a ordem de relevância do retrieval).

    Garantia de cobertura: toda citação vem de pelo menos um chunk do
    prompt, e o texto de todo chunk do prompt está no `texto` de alguma
    citação. Quando dois chunks de PDF diferentes caem na mesma chave
    (partes vizinhas no mesmo intervalo de páginas), os textos distintos
    são concatenados com `SEPARADOR_TRECHOS`, em vez de o segundo sumir.
    """
    por_chave: dict[tuple, Citacao] = {}
    textos: dict[tuple, list[str]] = {}
    for c in chunks:
        chave = _chave_citacao(c)
        if chave not in por_chave:
            por_chave[chave] = Citacao(
                fonte=c.fonte,
                documento=c.documento,
                secao=c.secao,
                parte=c.parte if chave[2] == "secao" else None,
                pagina_inicio=c.pagina_inicio,
                pagina_fim=c.pagina_fim,
                url_origem=c.url_origem,
            )
            textos[chave] = []
        if c.texto and c.texto not in textos[chave]:
            textos[chave].append(c.texto)
    for chave, citacao in por_chave.items():
        citacao.texto = SEPARADOR_TRECHOS.join(textos[chave]) or None
    return list(por_chave.values())


def _dados_avaliacao(
    tipo_saida: TipoSaida,
    chunks_no_prompt: list[ChunkRecuperado],
    resposta_original: str | None = None,
    origem_retencao: OrigemRetencao | None = None,
) -> DadosAvaliacao:
    # texto = chunk.texto exatamente como entra em montar_prompt (sem o
    # cabeçalho do trecho), para os contextos da avaliação serem o que o LLM leu.
    return DadosAvaliacao(
        tipo_saida=tipo_saida,
        origem_retencao=origem_retencao,
        contextos=[
            ContextoAvaliacao(
                fonte=c.fonte,
                documento=c.documento,
                secao=c.secao,
                pagina_inicio=c.pagina_inicio,
                pagina_fim=c.pagina_fim,
                score=c.score,
                nivel_sensibilidade=c.nivel_sensibilidade,
                texto=c.texto,
            )
            for c in chunks_no_prompt
        ],
        resposta_original=resposta_original,
    )


async def gerar_resposta(
    llm: LLMClient,
    pergunta: str,
    chunks: list[ChunkRecuperado],
    settings: Settings,
    incluir_avaliacao: bool = False,
) -> PerguntarResponse:
    """`incluir_avaliacao` preenche `avaliacao` em todos os caminhos de
    retorno (modo de avaliação offline, ver backend/routers/perguntar.py).
    Sem ele, a resposta é a mesma de sempre, com `avaliacao=None`."""
    if not chunks:
        return PerguntarResponse(
            pergunta=pergunta,
            resposta="Não há evidência suficiente na base de conhecimento para responder a essa pergunta.",
            citacoes=[],
            evidencia_suficiente=False,
            resposta_fundamentada=False,
            tipo_saida="sem_chunks",
            avaliacao=_dados_avaliacao("sem_chunks", []) if incluir_avaliacao else None,
        )

    if _pergunta_pede_sei_nao_indexado(pergunta, chunks):
        return PerguntarResponse(
            pergunta=pergunta,
            resposta=(
                "A base de conhecimento ainda não tem documentos do SEI "
                "indexados (fonte de acesso restrito, pendente de exportação "
                "e autorização — ver CLAUDE.md). Não é possível responder "
                "com base em processos, notas técnicas ou outros documentos "
                "do SEI."
            ),
            citacoes=[],
            evidencia_suficiente=False,
            resposta_fundamentada=False,
            justificativa_groundedness=(
                "Verificação estrutural: a pergunta menciona SEI, mas nenhum "
                "chunk recuperado é da fonte 'sei' (ainda não indexada)."
            ),
            tipo_saida="sei_nao_indexado",
            # Os chunks foram recuperados, mas não chegaram a ir para um prompt.
            avaliacao=_dados_avaliacao("sei_nao_indexado", []) if incluir_avaliacao else None,
        )

    campo = responder_campo_salve(pergunta, chunks) if settings.extracao_campos_salve else None
    if campo is not None:
        # Texto transcrito da ficha: não passa pelo LLM nem pela verificação
        # de fundamentação, e cita só o trecho de onde veio.
        return PerguntarResponse(
            pergunta=pergunta,
            resposta=campo.texto,
            citacoes=montar_citacoes([campo.chunk]),
            evidencia_suficiente=True,
            resposta_fundamentada=True,
            tipo_saida="extraida_salve",
            avaliacao=_dados_avaliacao("extraida_salve", [campo.chunk]) if incluir_avaliacao else None,
        )

    prompt = montar_prompt(pergunta, chunks)
    try:
        resposta = await llm.generate(prompt)
    except ContextoExcedidoError as exc:
        # Antes o Ollama cortava o início do prompt (instruções e primeiros
        # trechos) e o modelo respondia mesmo assim.
        return PerguntarResponse(
            pergunta=pergunta,
            resposta=MENSAGEM_CONTEXTO_EXCEDIDO,
            citacoes=montar_citacoes(chunks),
            evidencia_suficiente=True,
            resposta_fundamentada=False,
            justificativa_groundedness=f"Resposta não gerada: {exc}.",
            tipo_saida="contexto_excedido",
            avaliacao=_dados_avaliacao("contexto_excedido", chunks) if incluir_avaliacao else None,
        )

    fundamentada = True
    justificativa = None
    origem = None
    resposta_original = None
    if settings.groundedness_verificar:
        fundamentada, justificativa, origem = await verificar_groundedness_detalhado(
            llm, pergunta, resposta, chunks
        )
        if not fundamentada:
            print(f"[groundedness] resposta retida — {justificativa}\nResposta original: {resposta}")
            resposta_original = resposta
            resposta = MENSAGEM_RETENCAO

    # Mesma regra de antes (que só valia no modo de avaliação), agora
    # calculada sempre: a interface precisa de `abstencao` para o estado
    # "sem evidência", e o log grava o caminho de toda interação.
    if not fundamentada:
        tipo_saida: TipoSaida = "retida_groundedness"
    elif origem == "abstencao":
        tipo_saida = "abstencao"
    else:
        tipo_saida = "gerada"
    origem_retencao = origem if not fundamentada else None

    avaliacao = None
    if incluir_avaliacao:
        avaliacao = _dados_avaliacao(tipo_saida, chunks, resposta_original, origem_retencao)

    resultado = PerguntarResponse(
        pergunta=pergunta,
        resposta=resposta,
        citacoes=montar_citacoes(chunks),
        evidencia_suficiente=True,
        resposta_fundamentada=fundamentada,
        justificativa_groundedness=justificativa if not fundamentada else None,
        tipo_saida=tipo_saida,
        avaliacao=avaliacao,
    )
    resultado._origem_retencao = origem_retencao
    resultado._resposta_original = resposta_original
    return resultado
