"""Catálogo de nomes das fichas SALVE: identifica as espécies citadas numa
pergunta pelo nome científico ou por um nome comum.

Motivo (2026-11-17): "por que o cágado-amarelo foi classificado como menos
preocupante?" trazia, na busca semântica, trechos de PANs de peixe-boi. O
BGE-M3 não associa o nome comum à ficha de Acanthochelys radiolata, embora
"Cágado-amarelo" esteja no cabeçalho de todos os chunks dela. Com o nome
identificado na pergunta, `roteamento.buscar_chunks_priorizados` filtra a
busca pela ficha (campo `documento` do payload).

O catálogo é montado uma vez no startup a partir do próprio índice
(`carregar_catalogo`), então acompanha a reindexação sem arquivo extra.
"""

import logging
import re

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from backend.config import Settings
from backend.services.normalizacao import normalizar
from backend.services.retrieval import FILTRO_ACESSO

log = logging.getLogger(__name__)

# Mais que isso, a pergunta não é sobre espécies específicas (ou o nome é
# genérico demais) e o roteamento por espécie não se aplica.
MAX_ESPECIES = 3


def nomes_da_especie(documento: str, nome_comum: str | None) -> list[str]:
    """Nomes normalizados pelos quais uma ficha pode ser citada: gênero +
    epíteto do documento (e o trinômio, se houver subespécie) e os nomes
    comuns separados por vírgula. Nomes comuns de uma palavra só ("sapo",
    "perereca", "jararaca") ficam de fora: são genéricos demais."""
    palavras = documento.split()
    nomes = [normalizar(" ".join(palavras[:2]))]
    if len(palavras) > 2 and re.fullmatch(r"[a-zà-ÿ-]+", palavras[2]):
        nomes.append(normalizar(" ".join(palavras[:3])))
    for nome in (nome_comum or "").split(","):
        normalizado = normalizar(nome)
        if len(normalizado.split()) >= 2:
            nomes.append(normalizado)
    return [n for n in nomes if n]


class CatalogoEspecies:
    def __init__(self, fichas: dict[str, str | None]):
        """`fichas`: documento -> nome comum (como no payload)."""
        self._documentos_por_nome: dict[str, set[str]] = {}
        for documento, nome_comum in fichas.items():
            for nome in nomes_da_especie(documento, nome_comum):
                self._documentos_por_nome.setdefault(nome, set()).add(documento)
        self._max_palavras = max((len(n.split()) for n in self._documentos_por_nome), default=0)

    def __len__(self) -> int:
        return len(self._documentos_por_nome)

    def detectar(self, pergunta: str) -> list[str]:
        """Documentos das fichas citadas na pergunta, ou [] se nenhuma ou mais
        de MAX_ESPECIES. Quando um nome citado está dentro de outro mais longo
        também citado ("bothrops jararaca" dentro de um trinômio), vale só o
        mais longo."""
        palavras = normalizar(pergunta).split()
        achados: list[tuple[int, int, set[str]]] = []
        for inicio in range(len(palavras)):
            for fim in range(min(len(palavras), inicio + self._max_palavras), inicio, -1):
                documentos = self._documentos_por_nome.get(" ".join(palavras[inicio:fim]))
                if documentos:
                    achados.append((inicio, fim, documentos))
        documentos: set[str] = set()
        for inicio, fim, docs in achados:
            dentro_de_outro = any(
                i <= inicio and fim <= f and (i, f) != (inicio, fim) for i, f, _ in achados
            )
            if not dentro_de_outro:
                documentos |= docs
        if len(documentos) > MAX_ESPECIES:
            return []
        return sorted(documentos)


def carregar_catalogo(client: QdrantClient, settings: Settings) -> CatalogoEspecies | None:
    """Lê documento e nome comum da primeira parte da Visão geral de cada
    ficha SALVE autorizada. None se a leitura falhar: o backend sobe sem o
    roteamento por espécie, como antes."""
    filtro = Filter(must=[
        *FILTRO_ACESSO,
        FieldCondition(key="fonte", match=MatchValue(value="salve")),
        FieldCondition(key="secao", match=MatchValue(value="visao_geral")),
        FieldCondition(key="parte", match=MatchValue(value=1)),
    ])
    fichas: dict[str, str | None] = {}
    try:
        deslocamento = None
        while True:
            pontos, deslocamento = client.scroll(
                collection_name=settings.qdrant_collection,
                scroll_filter=filtro,
                limit=1000,
                offset=deslocamento,
                with_payload=["documento", "nome_comum"],
                with_vectors=False,
            )
            for p in pontos:
                if p.payload and p.payload.get("documento"):
                    fichas[p.payload["documento"]] = p.payload.get("nome_comum")
            if deslocamento is None:
                break
    except Exception as exc:  # noqa: BLE001 — o catálogo é opcional
        log.warning("Catálogo de espécies SALVE não carregado: %s", exc)
        return None
    return CatalogoEspecies(fichas)
