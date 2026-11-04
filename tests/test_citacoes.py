"""`montar_citacoes` (backend/services/geracao.py): uma citação por seção de
ficha SALVE, PDFs deduplicados por página, e cobertura total chunk ↔ citação
(H1 do diagnóstico da sessão RAN de 26/10/2026)."""

from backend.schemas import ChunkRecuperado
from backend.services.geracao import SEPARADOR_TRECHOS, montar_citacoes


def _salve(secao: str, parte: int, texto: str, score: float = 0.6, doc: str = "Rhinella diptycha (Cope, 1862)"):
    return ChunkRecuperado(
        score=score, fonte="salve", documento=doc, secao=secao, parte=parte,
        texto=texto, url_origem="https://salve.icmbio.gov.br/ficha", chunk_id=f"salve:{doc}:{secao}:{parte}",
    )


def _pdf(doc: str, p_ini: int, p_fim: int, texto: str, categoria: str = "materiais-de-apoio", parte: int = 1):
    return ChunkRecuperado(
        score=0.5, fonte="monitora", documento=doc, secao=categoria, pagina_inicio=p_ini,
        pagina_fim=p_fim, texto=texto, parte=parte, chunk_id=f"monitora:{doc}:{parte}",
    )


def _coberto(chunks, citacoes):
    """Todo chunk tem o texto dentro de alguma citação; toda citação tem o
    texto de algum chunk."""
    textos_cit = [c.texto or "" for c in citacoes]
    chunk_coberto = all(any(ch.texto in t for t in textos_cit) for ch in chunks)
    citacao_tem_origem = all(any(ch.texto in t for ch in chunks) for t in textos_cit)
    return chunk_coberto and citacao_tem_origem


def test_salve_uma_citacao_por_secao_como_797():
    # Contexto de #797: 5 chunks da mesma ficha, seções diferentes.
    secoes = ["visao_geral", "conservacao", "distribuicao", "populacao", "referencias"]
    chunks = [_salve(s, 1, f"texto de {s}", score=0.7 - i / 100) for i, s in enumerate(secoes)]
    citacoes = montar_citacoes(chunks)
    assert [c.secao for c in citacoes] == secoes  # ordem de relevância mantida
    assert any("conservacao" in c.texto for c in citacoes)
    assert _coberto(chunks, citacoes)


def test_salve_partes_da_mesma_secao_viram_citacoes_distintas_como_787():
    # Contexto de #787: conservação partes 1, 2 e 4 da mesma ficha.
    chunks = [
        _salve("visao_geral", 2, "A partir destas informações, foi avaliada como EN.", doc="Chelonoidis denticulatus"),
        _salve("conservacao", 1, "Histórico de avaliação de risco: Nacional Brasil 2024: EN", doc="Chelonoidis denticulatus"),
        _salve("conservacao", 2, "Histórico ... Unidades de conservação com registro", doc="Chelonoidis denticulatus"),
        _salve("conservacao", 4, "Ações de conservação", doc="Chelonoidis denticulatus"),
    ]
    citacoes = montar_citacoes(chunks)
    assert [(c.secao, c.parte) for c in citacoes] == [
        ("visao_geral", 2), ("conservacao", 1), ("conservacao", 2), ("conservacao", 4)
    ]
    assert any("Nacional Brasil 2024" in c.texto for c in citacoes)
    assert _coberto(chunks, citacoes)


def test_salve_chunk_repetido_nao_duplica_citacao():
    a = _salve("conservacao", 1, "mesmo texto")
    citacoes = montar_citacoes([a, a.model_copy()])
    assert len(citacoes) == 1
    assert citacoes[0].texto == "mesmo texto"


def test_pdf_mesmo_arquivo_em_duas_categorias_continua_uma_citacao():
    # Caso #799: o mesmo PDF indexado em `livros` e `encontro-dos-saberes`.
    doc = "IPE_MPB___Livro_Encontro_Saberes.pdf"
    chunks = [_pdf(doc, 14, 15, "mesmo texto", "livros"), _pdf(doc, 14, 15, "mesmo texto", "encontro-dos-saberes")]
    citacoes = montar_citacoes(chunks)
    assert len(citacoes) == 1
    assert citacoes[0].texto == "mesmo texto"
    assert citacoes[0].parte is None  # PDF é identificado por página


def test_pdf_partes_diferentes_na_mesma_pagina_juntam_textos():
    # Caso #795: duas partes do mesmo TCC com o mesmo intervalo de páginas.
    doc = "TCC.pdf"
    chunks = [_pdf(doc, 17, 18, "parte 21", parte=21), _pdf(doc, 17, 18, "parte 22", parte=22)]
    citacoes = montar_citacoes(chunks)
    assert len(citacoes) == 1
    assert citacoes[0].texto == f"parte 21{SEPARADOR_TRECHOS}parte 22"
    assert _coberto(chunks, citacoes)


def test_pdf_paginas_diferentes_sao_citacoes_diferentes_na_ordem():
    chunks = [_pdf("A.pdf", 3, 3, "a3"), _pdf("B.pdf", 1, 1, "b1"), _pdf("A.pdf", 9, 10, "a9")]
    citacoes = montar_citacoes(chunks)
    assert [(c.documento, c.pagina_inicio) for c in citacoes] == [("A.pdf", 3), ("B.pdf", 1), ("A.pdf", 9)]
    assert _coberto(chunks, citacoes)


def test_cobertura_em_contexto_misto():
    chunks = [
        _pdf("Bernardes.pdf", 14, 15, "tracajá NT"),
        _salve("conservacao", 1, "ficha 1", doc="Trachycephalus nigromaculatus"),
        _salve("conservacao", 1, "ficha 2", doc="Trachemys adiutrix"),
        _pdf("Bernardes.pdf", 14, 15, "outra parte", parte=2),
        _salve("conservacao", 1, "ficha 1", doc="Trachycephalus nigromaculatus"),
    ]
    citacoes = montar_citacoes(chunks)
    assert _coberto(chunks, citacoes)
    assert len(citacoes) == 3
    assert citacoes[0].documento == "Bernardes.pdf"


def test_sem_chunks_sem_citacoes():
    assert montar_citacoes([]) == []
