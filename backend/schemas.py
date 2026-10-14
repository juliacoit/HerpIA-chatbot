"""Modelos Pydantic compartilhados entre os routers do backend."""

from typing import Literal

from pydantic import BaseModel, Field


class ChunkRecuperado(BaseModel):
    """Um chunk retornado pela busca semântica, com metadados de rastreabilidade."""

    score: float
    fonte: str
    documento: str
    texto: str
    secao: str | None = None
    pagina_inicio: int | None = None
    pagina_fim: int | None = None
    url_origem: str | None = None
    caminho_local: str | None = None
    nivel_sensibilidade: str | None = None


class BuscaRequest(BaseModel):
    pergunta: str = Field(min_length=1, description="Pergunta em linguagem natural")
    top_k: int = Field(default=5, ge=1, le=20)
    fontes: list[str] | None = Field(
        default=None, description="Filtrar por fonte(s): monitora, pans, salve"
    )


class BuscaResponse(BaseModel):
    pergunta: str
    resultados: list[ChunkRecuperado]


class PerguntarRequest(BuscaRequest):
    incluir_contextos: bool = Field(
        default=False,
        description=(
            "Modo de avaliação offline (avaliacao/rodar_ragas.py): devolve em "
            "`avaliacao` os trechos enviados ao prompt e, se houve retenção, a "
            "resposta original. Só aceito com PERMITIR_MODO_AVALIACAO=true "
            "(403 caso contrário); a interação não é registrada no PostgreSQL."
        ),
    )


class Citacao(BaseModel):
    fonte: str
    documento: str
    secao: str | None = None
    pagina_inicio: int | None = None
    pagina_fim: int | None = None
    url_origem: str | None = None
    texto: str | None = Field(
        default=None,
        description=(
            "Texto do chunk recuperado que originou esta citação (o mesmo "
            "trecho enviado ao LLM em backend/services/geracao.py, não o "
            "documento completo — ver CLAUDE.md, regras sobre dados "
            "sensíveis). Permite ao usuário conferir a fonte exata sem "
            "precisar abrir o documento original."
        ),
    )


class ContextoAvaliacao(BaseModel):
    fonte: str
    documento: str
    secao: str | None = None
    pagina_inicio: int | None = None
    pagina_fim: int | None = None
    score: float
    nivel_sensibilidade: str | None = None
    texto: str = Field(
        description=(
            "Exatamente o `chunk.texto` enviado ao prompt de geração, sem o "
            "cabeçalho '[Trecho i — fonte, documento]' que montar_prompt põe antes."
        )
    )


TipoSaida = Literal[
    "gerada",               # texto do LLM aprovado pelo juiz (ou groundedness desligado)
    "abstencao",            # abstenção pura, aprovada pela camada 0 sem chamar o juiz
    "retida_groundedness",  # texto do LLM substituído por MENSAGEM_NAO_FUNDAMENTADA
    "sem_chunks",
    "sei_nao_indexado",
    "contexto_excedido",
]

OrigemRetencao = Literal[
    "lexical",             # camada 1 (hard gate), sem chamada ao LLM
    "juiz_llm",            # veredito diferente de "SIM"
    "juiz_nao_realizado",  # prompt do juiz não coube no contexto: retida sem julgamento
]


class DadosAvaliacao(BaseModel):
    """Só preenchido no modo de avaliação. `resposta_original` pode conter uma
    resposta retida por não ser fundamentada — nunca deve chegar a um usuário
    real, por isso a trava PERMITIR_MODO_AVALIACAO."""

    tipo_saida: TipoSaida
    origem_retencao: OrigemRetencao | None = None
    contextos: list[ContextoAvaliacao] = Field(
        description="Chunks enviados ao prompt de geração, na mesma ordem; vazio quando não houve prompt."
    )
    resposta_original: str | None = Field(
        default=None, description="Resposta do LLM antes de uma retenção por groundedness."
    )


class PerguntarResponse(BaseModel):
    id: int | None = Field(
        default=None,
        description=(
            "ID da interação registrada no PostgreSQL (tabela `interacoes`), "
            "para enviar de volta em POST /feedback. None quando o "
            "PostgreSQL está indisponível nesta sessão (ver backend/db.py) "
            "— nesse caso não é possível dar feedback desta resposta."
        ),
    )
    pergunta: str
    resposta: str
    citacoes: list[Citacao]
    evidencia_suficiente: bool
    resposta_fundamentada: bool = Field(
        description=(
            "Resultado da verificação de groundedness pós-geração (ver "
            "backend/services/groundedness.py) — diferente de "
            "evidencia_suficiente, que só reflete se chunks foram "
            "recuperados. False quando a resposta original não passou na "
            "checagem e foi substituída por uma mensagem de retenção."
        )
    )
    justificativa_groundedness: str | None = Field(
        default=None,
        description="Motivo da retenção quando resposta_fundamentada é False.",
    )
    avaliacao: DadosAvaliacao | None = Field(
        default=None,
        description="Só no modo de avaliação (incluir_contextos=true); None nas requisições normais.",
    )


class FeedbackRequest(BaseModel):
    interacao_id: int = Field(description="Valor de `id` recebido em PerguntarResponse.")
    avaliacao: Literal[-1, 1] = Field(description="1 = positivo (thumbs up), -1 = negativo (thumbs down)")
    comentario: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    ok: bool = True
