"""Modelos Pydantic compartilhados entre os routers do backend."""

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
    pass


class Citacao(BaseModel):
    fonte: str
    documento: str
    secao: str | None = None
    pagina_inicio: int | None = None
    pagina_fim: int | None = None
    url_origem: str | None = None


class PerguntarResponse(BaseModel):
    pergunta: str
    resposta: str
    citacoes: list[Citacao]
    evidencia_suficiente: bool
