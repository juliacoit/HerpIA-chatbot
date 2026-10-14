"""Fixtures dos testes do backend.

Nada aqui carrega o BGE-M3, abre o Qdrant, chama o Ollama ou conecta ao
PostgreSQL: o TestClient é usado sem `with`, então o lifespan de
backend/main.py não roda, e todas as dependências de /perguntar são
substituídas por versões falsas. Isso também evita disputar a trava do Qdrant
em modo arquivo local com um backend que esteja rodando.
"""

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, obter_settings
from backend.dependencies import obter_db_pool, obter_llm, obter_modelo_embedding, obter_qdrant
from backend.main import app
from backend.routers import perguntar as router_perguntar
from backend.schemas import ChunkRecuperado
from backend.services.llm import LLMClient


class LLMFalso(LLMClient):
    """Devolve as respostas da lista, na ordem (geração e, se ligado, juiz),
    e guarda os prompts recebidos. Uma exceção na lista é levantada."""

    def __init__(self, respostas: list):
        self._respostas = list(respostas)
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        resposta = self._respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def criar_chunks() -> list[ChunkRecuperado]:
    # Duas seções do mesmo documento/página: montar_citacoes deduplica, os
    # contextos da avaliação não podem deduplicar.
    return [
        ChunkRecuperado(
            score=0.81, fonte="salve", documento="Ficha Bothrops marmoratus",
            secao="Ameaças", pagina_inicio=None, pagina_fim=None,
            texto="A principal ameaça à espécie é a perda de habitat no Cerrado.",
            nivel_sensibilidade="autorizado",
        ),
        ChunkRecuperado(
            score=0.77, fonte="salve", documento="Ficha Bothrops marmoratus",
            secao="Categoria", pagina_inicio=None, pagina_fim=None,
            texto="Categoria de risco: Quase Ameaçada (NT).",
            nivel_sensibilidade="autorizado",
        ),
        ChunkRecuperado(
            score=0.70, fonte="pans", documento="PAN Herpetofauna do Cerrado",
            secao=None, pagina_inicio=12, pagina_fim=13,
            texto="O plano prevê ações de manejo do fogo em áreas de ocorrência.",
            nivel_sensibilidade="autorizado",
        ),
    ]


@pytest.fixture
def chunks() -> list[ChunkRecuperado]:
    return criar_chunks()


@pytest.fixture
def cliente_api(monkeypatch):
    """Monta o app com dependências falsas. Devolve uma função que recebe a
    configuração do teste e devolve (TestClient, estado), onde `estado`
    guarda as chamadas a buscar_chunks_priorizados e registrar_interacao."""

    def montar(
        respostas_llm: list,
        chunks: list[ChunkRecuperado] | None = None,
        permitir_modo_avaliacao: bool = False,
        groundedness_verificar: bool = True,
    ):
        estado = {"buscas": 0, "registros": [], "llm": LLMFalso(respostas_llm)}
        settings = Settings(
            _env_file=None,
            permitir_modo_avaliacao=permitir_modo_avaliacao,
            groundedness_verificar=groundedness_verificar,
        )
        lista_chunks = criar_chunks() if chunks is None else chunks

        def buscar_falso(*args, **kwargs):
            estado["buscas"] += 1
            return lista_chunks

        def registrar_falso(db_pool, **kwargs):
            estado["registros"].append(kwargs)
            return 42

        monkeypatch.setattr(router_perguntar, "buscar_chunks_priorizados", buscar_falso)
        monkeypatch.setattr(router_perguntar, "registrar_interacao", registrar_falso)
        app.dependency_overrides[obter_settings] = lambda: settings
        app.dependency_overrides[obter_llm] = lambda: estado["llm"]
        app.dependency_overrides[obter_qdrant] = lambda: None
        app.dependency_overrides[obter_modelo_embedding] = lambda: None
        app.dependency_overrides[obter_db_pool] = lambda: None
        return TestClient(app), estado

    yield montar
    app.dependency_overrides.clear()
