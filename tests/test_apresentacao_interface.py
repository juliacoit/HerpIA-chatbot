"""Regras de apresentação da interface (interface/apresentacao.py), sem
Streamlit: estado da faixa e agrupamento das citações por documento.
Casos tirados das interações da sessão RAN de 26/10/2026."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "interface"))

import apresentacao  # noqa: E402

from backend.schemas import ChunkRecuperado  # noqa: E402
from backend.services.geracao import montar_citacoes  # noqa: E402


def _item(**campos):
    base = {"evidencia_suficiente": True, "resposta_fundamentada": True, "tipo_saida": "gerada"}
    base.update(campos)
    return base


# --- estado ------------------------------------------------------------------


def test_abstencao_pura_vira_sem_evidencia_796_799_801():
    assert apresentacao.estado_resposta(_item(tipo_saida="abstencao")) == "sem_evidencia"


def test_retida_794():
    item = _item(resposta_fundamentada=False, tipo_saida="retida_groundedness")
    assert apresentacao.estado_resposta(item) == "retida"


def test_gerada_792_continua_fundamentada():
    assert apresentacao.estado_resposta(_item()) == "fundamentada"


def test_recusa_fora_do_padrao_continua_fundamentada_795():
    # Limitação conhecida: o juiz aprovou e tipo_saida é "gerada".
    assert apresentacao.estado_resposta(_item(tipo_saida="gerada")) == "fundamentada"


def test_sem_chunks_e_sei_continuam_sem_evidencia():
    sem_chunks = _item(evidencia_suficiente=False, resposta_fundamentada=False, tipo_saida="sem_chunks")
    sei = _item(evidencia_suficiente=False, resposta_fundamentada=False, tipo_saida="sei_nao_indexado")
    assert apresentacao.estado_resposta(sem_chunks) == "sem_evidencia"
    assert apresentacao.estado_resposta(sei) == "sem_evidencia"


def test_contexto_excedido_continua_retida():
    item = _item(resposta_fundamentada=False, tipo_saida="contexto_excedido")
    assert apresentacao.estado_resposta(item) == "retida"


def test_retida_tem_precedencia_sobre_abstencao():
    # Combinação que o backend não produz hoje; garante a precedência pedida.
    item = _item(resposta_fundamentada=False, tipo_saida="abstencao")
    assert apresentacao.estado_resposta(item) == "retida"


def test_item_antigo_sem_tipo_saida():
    item = {"evidencia_suficiente": True, "resposta_fundamentada": True}
    assert apresentacao.estado_resposta(item) == "fundamentada"


def test_titulos_dos_trechos():
    assert apresentacao.titulo_trechos("retida") == "Trechos recuperados (não verificados)"
    assert apresentacao.titulo_trechos("sem_evidencia") == "Trechos recuperados"
    assert apresentacao.titulo_trechos("fundamentada") is None


# --- agrupamento ---------------------------------------------------------------


def _salve(doc, secao, parte, score):
    return ChunkRecuperado(score=score, fonte="salve", documento=doc, secao=secao, parte=parte,
                           texto=f"{doc} {secao} {parte}", url_origem=f"https://salve/{doc}")


def test_797_um_cartao_com_todas_as_secoes():
    doc = "Rhinella diptycha (Cope, 1862)"
    secoes = ["visao_geral", "conservacao", "distribuicao", "populacao", "referencias"]
    citacoes = [c.model_dump() for c in montar_citacoes([_salve(doc, s, 1, 0.7) for s in secoes])]
    grupos = apresentacao.agrupar_citacoes(citacoes)
    assert len(grupos) == 1
    assert grupos[0]["documento"] == doc
    assert apresentacao.rotulos_trechos(grupos[0]) == [
        "Visão geral", "Conservação", "Distribuição", "População", "Referências"
    ]
    assert apresentacao.resumo_citacoes(grupos) == "1 documento, 5 trechos"


def test_787_partes_da_conservacao_rotuladas():
    doc = "Chelonoidis denticulatus (Linnaeus, 1766)"
    chunks = [_salve(doc, "visao_geral", 2, 0.64), _salve(doc, "pesquisa", 1, 0.63),
              _salve(doc, "conservacao", 1, 0.62), _salve(doc, "conservacao", 2, 0.61),
              _salve(doc, "conservacao", 4, 0.60)]
    grupos = apresentacao.agrupar_citacoes([c.model_dump() for c in montar_citacoes(chunks)])
    assert apresentacao.rotulos_trechos(grupos[0]) == [
        "Visão geral", "Pesquisa", "Conservação · parte 1", "Conservação · parte 2", "Conservação · parte 4"
    ]


def test_ordem_dos_documentos_pelo_melhor_chunk():
    chunks = [
        ChunkRecuperado(score=0.58, fonte="monitora", documento="Bernardes.pdf", pagina_inicio=14,
                        pagina_fim=15, texto="a", secao="materiais-de-apoio"),
        _salve("Trachycephalus", "conservacao", 1, 0.56),
        ChunkRecuperado(score=0.55, fonte="monitora", documento="Bernardes.pdf", pagina_inicio=30,
                        pagina_fim=30, texto="b", secao="materiais-de-apoio"),
        _salve("Trachemys", "conservacao", 1, 0.54),
    ]
    grupos = apresentacao.agrupar_citacoes([c.model_dump() for c in montar_citacoes(chunks)])
    assert [g["documento"] for g in grupos] == ["Bernardes.pdf", "Trachycephalus", "Trachemys"]
    assert apresentacao.rotulos_trechos(grupos[0]) == ["p. 14–15", "p. 30"]
    assert apresentacao.resumo_citacoes(grupos) == "3 documentos, 4 trechos"


def test_nome_categoria_do_pdf_para_leitura():
    assert apresentacao.nome_categoria("materiais-de-apoio") == "Materiais de apoio"
    assert apresentacao.nome_categoria("normativas") == "Normativas"
    assert apresentacao.nome_categoria("sumario_executivo") == "Sumario executivo"
