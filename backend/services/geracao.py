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
from backend.schemas import ChunkRecuperado, Citacao, PerguntarResponse
from backend.services.groundedness import MENSAGEM_NAO_FUNDAMENTADA, verificar_groundedness
from backend.services.llm import LLMClient

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


def montar_citacoes(chunks: list[ChunkRecuperado]) -> list[Citacao]:
    # Dedupe por (fonte, documento, página) — não por seção. `secao` não
    # aparece na citação exibida ao usuário, então dois chunks do mesmo
    # documento/página mas de seções diferentes (ex.: "história natural" e
    # "ameaças" da mesma ficha SALVE) produziam citações visualmente
    # idênticas e repetidas (ver diagnosticos/teste-perguntas-dominio.md,
    # achado 5).
    vistas = set()
    citacoes = []
    for c in chunks:
        chave = (c.fonte, c.documento, c.pagina_inicio, c.pagina_fim)
        if chave in vistas:
            continue
        vistas.add(chave)
        citacoes.append(
            Citacao(
                fonte=c.fonte,
                documento=c.documento,
                secao=c.secao,
                pagina_inicio=c.pagina_inicio,
                pagina_fim=c.pagina_fim,
                url_origem=c.url_origem,
                texto=c.texto,
            )
        )
    return citacoes


async def gerar_resposta(
    llm: LLMClient, pergunta: str, chunks: list[ChunkRecuperado], settings: Settings
) -> PerguntarResponse:
    if not chunks:
        return PerguntarResponse(
            pergunta=pergunta,
            resposta="Não há evidência suficiente na base de conhecimento para responder a essa pergunta.",
            citacoes=[],
            evidencia_suficiente=False,
            resposta_fundamentada=False,
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
        )

    prompt = montar_prompt(pergunta, chunks)
    resposta = await llm.generate(prompt)

    fundamentada = True
    justificativa = None
    if settings.groundedness_verificar:
        fundamentada, justificativa = await verificar_groundedness(llm, pergunta, resposta, chunks)
        if not fundamentada:
            print(f"[groundedness] resposta retida — {justificativa}\nResposta original: {resposta}")
            resposta = MENSAGEM_NAO_FUNDAMENTADA

    return PerguntarResponse(
        pergunta=pergunta,
        resposta=resposta,
        citacoes=montar_citacoes(chunks),
        evidencia_suficiente=True,
        resposta_fundamentada=fundamentada,
        justificativa_groundedness=justificativa if not fundamentada else None,
    )
