"""Chunking dos documentos do SEI (scripts/processamento/gerar_chunks_sei.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "processamento"))
import gerar_chunks_sei  # noqa: E402


def documento(formato: str, paginas: list[dict], **campos) -> dict:
    dados = {
        "fonte": "sei",
        "processo": "02000.000001/2020-01",
        "numero_sei": "1234567",
        "nome_arquivo": f"1234567.{formato}",
        "caminho_original": f"04_documentos_pendentes_avaliacao/sei/02000.000001-2020-01/1234567.{formato}",
        "formato": formato,
        "data_download": "2026-11-10T16:20:00",
        "metodo_extracao": "texto",
        "paginas": paginas,
    }
    dados.update(campos)
    return dados


def chunkar(dados, **kwargs):
    return gerar_chunks_sei.chunkar_documento_sei(dados, "02000.000001-2020-01/1234567.json", **kwargs)


def test_chunk_de_texto_fica_pendente_e_leva_cabecalho():
    dados = documento("pdf", [{"pagina": 1, "texto": "Parecer sobre a soltura de quelônios. " * 20}])

    chunks = chunkar(dados, titulo="Parecer Técnico 12", tipo_processo="Fauna: Manejo")

    assert chunks
    chunk = chunks[0]
    assert chunk["fonte"] == "sei"
    assert chunk["nivel_sensibilidade"] == "pendente_avaliacao"
    assert chunk["tipo_conteudo"] == "texto"
    assert chunk["texto"].startswith(
        "Processo SEI nº 02000.000001/2020-01 — Fauna: Manejo\n"
        "Documento: Parecer Técnico 12 (nº SEI 1234567)\n\n"
    )


def test_sem_titulo_no_catalogo_o_cabecalho_usa_so_o_numero():
    dados = documento("html", [{"pagina": 1, "texto": "Despacho de encaminhamento. " * 10}])

    chunk = chunkar(dados)[0]

    assert chunk["texto"].startswith("Processo SEI nº 02000.000001/2020-01\nDocumento nº SEI 1234567\n\n")


def test_texto_longo_registra_paginas_de_inicio_e_fim():
    paginas = [{"pagina": n, "texto": f"Parágrafo da página {n}. " * 60} for n in (1, 2, 3)]

    chunks = chunkar(documento("pdf", paginas))

    assert len(chunks) > 1
    assert chunks[0]["pagina_inicio"] == 1
    assert chunks[-1]["pagina_fim"] == 3
    assert [c["parte"] for c in chunks] == list(range(1, len(chunks) + 1))
    assert {c["n_partes"] for c in chunks} == {len(chunks)}


def test_planilha_repete_o_cabecalho_das_colunas_em_cada_chunk():
    linhas = ["Espécie | Município | Ano"] + [f"Especie ficticia {n} | Goiânia | 2020" for n in range(200)]
    dados = documento("xlsx", [{"pagina": 1, "aba": "Registros", "texto": "\n".join(linhas)}])

    chunks = chunkar(dados)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["tipo_conteudo"] == "planilha"
        assert chunk["aba"] == "Registros"
        assert "Aba: Registros" in chunk["texto"]
        assert "Colunas: Espécie | Município | Ano" in chunk["texto"]
    # Nenhuma linha se perde nem se repete entre os chunks.
    corpo = [linha for c in chunks for linha in c["texto"].split("\n") if linha.startswith("Especie ficticia")]
    assert corpo == linhas[1:]


def test_planilha_com_uma_linha_so_nao_perde_o_conteudo():
    dados = documento("xls", [{"pagina": 1, "aba": "Plan1", "texto": "Observação única da aba"}])

    chunks = chunkar(dados)

    assert len(chunks) == 1
    assert "Observação única da aba" in chunks[0]["texto"]
    assert "Colunas:" not in chunks[0]["texto"]


def test_zip_trata_cada_arquivo_interno_pelo_proprio_tipo():
    paginas = [
        {"pagina": 1, "arquivo_interno": "relatorio.pdf", "texto": "Relatório de campo. " * 10},
        {"pagina": 2, "arquivo_interno": "dados.xlsx", "aba": "A", "texto": "Coluna 1 | Coluna 2\nvalor a | valor b"},
    ]

    chunks = chunkar(documento("zip", paginas))

    por_arquivo = {c["arquivo_interno"]: c for c in chunks}
    assert por_arquivo["relatorio.pdf"]["tipo_conteudo"] == "texto"
    assert por_arquivo["dados.xlsx"]["tipo_conteudo"] == "planilha"
    assert "Arquivo interno: dados.xlsx" in por_arquivo["dados.xlsx"]["texto"]


def test_sinais_de_triagem_ignoram_marcas_de_redacao():
    texto = "Contato: [e-mail removido], [telefone removido], [CPF removido]. " * 5

    assert gerar_chunks_sei.sinais_triagem(texto) == []
    assert gerar_chunks_sei.sinais_triagem("Documento de acesso restrito, ver coordenadas geográficas.") == [
        "palavra_restrito",
        "palavra_localizacao",
    ]


def test_sinais_do_documento_inteiro_vao_para_todos_os_chunks():
    paginas = [
        {"pagina": 1, "texto": "Texto comum sobre anfíbios. " * 100},
        {"pagina": 2, "texto": "Este documento é sigiloso. " * 5},
    ]

    chunks = chunkar(documento("pdf", paginas))

    assert len(chunks) > 1
    assert all(c["sinais_triagem"] == ["palavra_restrito"] for c in chunks)
