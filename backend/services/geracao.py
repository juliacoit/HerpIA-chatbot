"""Monta o prompt de geração a partir dos chunks recuperados e formata a
resposta final com citações de fonte.

Regra do projeto (CLAUDE.md): responder só com base nos trechos
recuperados, sempre citando a fonte, e indicar claramente quando não há
evidência suficiente em vez de inventar uma resposta.

`evidencia_suficiente` aqui só reflete se algum chunk foi recuperado — não
há (ainda) verificação de que a resposta do LLM realmente se apoiou nos
trechos; isso é objetivo da validação da Fase 8.
"""

from backend.schemas import ChunkRecuperado, Citacao, PerguntarResponse
from backend.services.llm import LLMClient

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
    "sobre o mesmo assunto geral). "
    "Nem sempre existe um único trecho que responda à pergunta inteira: se "
    "vários trechos parciais (ex.: fichas de espécies diferentes) juntos "
    "cobrem a resposta, sintetize uma resposta agregada combinando as "
    "informações desses trechos, citando cada um deles — não exija um "
    "trecho único e completo antes de responder. Isso é diferente de "
    "especular: síntese combina o que os trechos realmente dizem, "
    "especulação inventa o que eles provavelmente diriam."
)


def montar_prompt(pergunta: str, chunks: list[ChunkRecuperado]) -> str:
    trechos = "\n\n".join(
        f"[Trecho {i + 1} — fonte: {c.fonte}, documento: {c.documento}]\n{c.texto}"
        for i, c in enumerate(chunks)
    )
    return f"{PROMPT_SISTEMA}\n\nTrechos recuperados:\n{trechos}\n\nPergunta: {pergunta}\n\nResposta:"


def montar_citacoes(chunks: list[ChunkRecuperado]) -> list[Citacao]:
    vistas = set()
    citacoes = []
    for c in chunks:
        chave = (c.fonte, c.documento, c.secao, c.pagina_inicio)
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
            )
        )
    return citacoes


async def gerar_resposta(
    llm: LLMClient, pergunta: str, chunks: list[ChunkRecuperado]
) -> PerguntarResponse:
    if not chunks:
        return PerguntarResponse(
            pergunta=pergunta,
            resposta="Não há evidência suficiente na base de conhecimento para responder a essa pergunta.",
            citacoes=[],
            evidencia_suficiente=False,
        )

    prompt = montar_prompt(pergunta, chunks)
    resposta = await llm.generate(prompt)
    return PerguntarResponse(
        pergunta=pergunta,
        resposta=resposta,
        citacoes=montar_citacoes(chunks),
        evidencia_suficiente=True,
    )
