"""Chunking das publicações científicas do RAN (scripts/processamento/gerar_chunks.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "processamento"))
import gerar_chunks  # noqa: E402


@pytest.fixture(autouse=True)
def contadores_limpos():
    gerar_chunks._contagem_redacoes.clear()
    gerar_chunks._documentos_com_redacao.clear()


def publicacao(**campos) -> dict:
    dados = {
        "fonte": "publicacoes",
        "pasta_origem": "Artigo, Nota, Comunicação Científica",
        "nome_arquivo": "1- Fulano et al, 2003.pdf",
        "caminho_original": "02_publicacoes_cientificas_ran/Artigo/1- Fulano et al, 2003.pdf",
        "autor": "Fulano, A.; Beltrano, B.",
        "titulo": "Dieta de um lagarto fictício",
        "ano": "2003",
        "fonte_bibliografica": "Rev. Fictícia, v.1, p.1-9, 2003.",
        "doi": None,
        "tipologia": "Artigo",
        "metodo_extracao": "texto",
        "data_extracao": "2026-11-06",
        "paginas": [
            {"pagina": 1, "texto": "Primeira frase do resumo. " * 60},
            {"pagina": 2, "texto": ""},
            {"pagina": 3, "texto": "Frase da discussão. " * 60},
        ],
    }
    dados.update(campos)
    return dados


def test_chunk_leva_cabecalho_metadados_e_paginas():
    chunks = gerar_chunks.chunkar_publicacao(publicacao(), "Artigo/1- Fulano et al, 2003.json")

    assert len(chunks) > 1
    assert [c["parte"] for c in chunks] == list(range(1, len(chunks) + 1))
    assert chunks[0]["pagina_inicio"] == 1
    assert chunks[-1]["pagina_fim"] == 3

    for chunk in chunks:
        assert chunk["texto"].startswith(
            "Publicação: Dieta de um lagarto fictício\n"
            "Autoria: Fulano, A.; Beltrano, B. (2003)\n"
            "Tipo: Artigo\n\n"
        )
        assert chunk["fonte"] == "publicacoes"
        assert chunk["titulo"] == "Dieta de um lagarto fictício"
        assert chunk["ano"] == "2003"
        assert chunk["categoria"] == "Artigo, Nota, Comunicação Científica"
        assert chunk["n_partes"] == len(chunks)
        assert chunk["nivel_sensibilidade"] == "autorizado"
        assert chunk["acesso"] == "interno"


def test_ano_em_formato_de_data_vira_so_o_ano():
    chunks = gerar_chunks.chunkar_publicacao(
        publicacao(ano="2019-08-02 00:00:00", autor=None), "x.json"
    )
    assert chunks[0]["ano"] == "2019"
    assert "Ano: 2019" in chunks[0]["texto"]
    assert "Autoria" not in chunks[0]["texto"]


@pytest.mark.parametrize("titulo", [None, "Trabalho A | Trabalho B"])
def test_sem_titulo_unico_o_cabecalho_usa_o_nome_do_arquivo(titulo):
    chunks = gerar_chunks.chunkar_publicacao(publicacao(titulo=titulo), "x.json")
    assert chunks[0]["texto"].startswith("Publicação (arquivo): 1- Fulano et al, 2003\n\n")
    assert chunks[0]["titulo"] == titulo  # o payload guarda o que veio do catálogo


def test_titulo_longo_e_abreviado_so_no_cabecalho():
    titulo = "T" * 1000
    chunks = gerar_chunks.chunkar_publicacao(publicacao(titulo=titulo), "x.json")
    primeira_linha = chunks[0]["texto"].split("\n")[0]
    assert len(primeira_linha) == len("Publicação: ") + gerar_chunks.LIMITE_TITULO_CABECALHO
    assert primeira_linha.endswith("…")
    assert chunks[0]["titulo"] == titulo


def test_email_e_redigido_e_contado_so_em_publicacoes():
    paginas = [{"pagina": 1, "texto": "Contato: fulano@exemplo.org. " + "Texto do artigo. " * 30}]
    chunks = gerar_chunks.chunkar_publicacao(publicacao(paginas=paginas), "x.json")

    assert "fulano@exemplo.org" not in chunks[0]["texto"]
    assert gerar_chunks._documentos_com_redacao["publicacoes"] == {"publicacoes/x.json"}
    assert not gerar_chunks._contagem_redacoes["monitora"]


def test_publicacao_sem_texto_nao_gera_chunk():
    assert gerar_chunks.chunkar_publicacao(publicacao(paginas=[{"pagina": 1, "texto": " "}]), "x.json") == []
