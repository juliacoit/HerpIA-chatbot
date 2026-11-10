"""Gera chunks a partir dos documentos já autorizados para indexação.

Lê exclusivamente de 03_documentos_autorizados/{monitora,pans,salve,publicacoes}/ — nunca de
04_documentos_pendentes_avaliacao/ ou 05_documentos_sensiveis_nao_indexar/
(ver ADR 0002). Os arquivos nessa pasta já são o JSON de texto extraído
(mesmo formato gerado por extrair_texto_pdfs.py / extrair_texto_salve.py /
extrair_texto_publicacoes.py).

Estratégias (ver docs/roadmap.md, Fase 4):
  - SALVE: um chunk por seção da ficha; seções longas divididas em sub-chunks
    por parágrafo/sentença, com sobreposição. Cada chunk leva um cabeçalho
    com metadados da espécie (nome, categoria de risco, bioma, DOI).
  - Monitora/PANs: janela deslizante sobre o texto por página, com
    sobreposição, respeitando limites de parágrafo/sentença. Cada chunk
    registra página inicial/final.
  - Publicações científicas do RAN: mesma janela por página de Monitora/PANs,
    com um cabeçalho bibliográfico (título, autoria, ano, tipo) em cada chunk
    e os metadados do catálogo no payload. Os chunks levam `acesso: "interno"`:
    as publicações foram liberadas para uso interno do RAN (decisão de
    2026-11-06), então não devem ser indexadas antes de o login existir.

Tamanho alvo: ~2000 caracteres (~500 tokens). Sobreposição: ~200 caracteres
(~50 tokens). Aproximação por caracteres — o projeto não usa tokenizador.

Saída: 07_processados/chunks/<fonte>/chunks.jsonl (um JSON por linha).

Uso:
    python gerar_chunks.py [--fonte monitora|pans|salve|publicacoes]
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
AUTORIZADOS_DIR = RAIZ / "03_documentos_autorizados"
OUTPUT_DIR = RAIZ / "07_processados" / "chunks"
RELATORIO_ANONIMIZACAO = RAIZ / "06_inventario" / "relatorio_anonimizacao_chunks.json"
RELATORIO_ANONIMIZACAO_PUBLICACOES = (
    RAIZ / "06_inventario" / "relatorio_anonimizacao_chunks_publicacoes.json"
)
FONTES = ["monitora", "pans", "salve", "publicacoes"]

sys.path.insert(0, str(RAIZ / "scripts" / "classificacao"))
from regras_pii import redigir_texto  # noqa: E402

# Contadores globais de redação, por fonte, preenchidos durante o chunking e
# salvos ao final — ver função main(). Monitora/PANs vão para
# RELATORIO_ANONIMIZACAO; publicações, para um arquivo próprio, para que gerar
# os chunks de uma fonte não apague a auditoria da outra.
# Só cobrem os padrões estruturados (redigivel=True em regras_pii.py); os
# padrões semânticos (localização de espécie, palavra de restrição) não são
# redigidos automaticamente e continuam dependendo da revisão humana via
# triagem_sensibilidade.py.
_contagem_redacoes: dict[str, Counter] = defaultdict(Counter)
_documentos_com_redacao: dict[str, set[str]] = defaultdict(set)

TAMANHO_ALVO = 2000
SOBREPOSICAO = 200

NOMES_SECOES = {
    "visao_geral": "Visão geral",
    "taxonomia": "Taxonomia",
    "distribuicao": "Distribuição",
    "historia_natural": "História natural",
    "populacao": "População",
    "ameacas": "Ameaças",
    "uso": "Uso",
    "conservacao": "Conservação",
    "pesquisa": "Pesquisa",
    "referencias": "Referências",
}


def dividir_paragrafos(texto: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]


def dividir_sentencas(paragrafo: str) -> list[str]:
    sentencas = re.split(r"(?<=[.!?])\s+", paragrafo)
    return [s.strip() for s in sentencas if s.strip()]


def dividir_bruto(texto: str, limite: int) -> list[str]:
    """Corte por tamanho fixo (no espaço mais próximo) para texto sem pontuação
    de frase — ex.: tabelas/listas de dados extraídas como um único bloco."""
    partes = []
    while len(texto) > limite:
        corte = texto.rfind(" ", 0, limite)
        if corte <= 0:
            corte = limite
        partes.append(texto[:corte].strip())
        texto = texto[corte:].strip()
    if texto:
        partes.append(texto)
    return partes


def unidades_de_texto(texto: str, limite_unidade: int = TAMANHO_ALVO) -> list[str]:
    """Quebra o texto em parágrafos; parágrafos maiores que o limite viram sentenças
    (e sentenças que ainda excedam 2x o limite são cortadas por tamanho fixo)."""
    unidades = []
    for p in dividir_paragrafos(texto):
        if len(p) <= limite_unidade:
            unidades.append(p)
            continue
        for s in dividir_sentencas(p):
            if len(s) <= limite_unidade * 2:
                unidades.append(s)
            else:
                unidades.extend(dividir_bruto(s, limite_unidade))
    return unidades


def agrupar_em_chunks(
    unidades: list[str],
    tamanho_alvo: int = TAMANHO_ALVO,
    sobreposicao: int = SOBREPOSICAO,
    tamanho_minimo: int = 300,
) -> list[tuple[int, int, str]]:
    """Agrupa unidades em chunks (janela deslizante com overlap).

    Parágrafos muito curtos (ex.: "Art. 45.", isolado por quebra de página)
    continuam sendo agregados ao próximo mesmo que isso ultrapasse
    tamanho_alvo, até o chunk atingir tamanho_minimo — evita chunks de poucas
    palavras sem contexto suficiente para recuperação.

    Retorna lista de (indice_unidade_inicial, indice_unidade_final, texto_chunk).
    """
    chunks = []
    n = len(unidades)
    i = 0
    while i < n:
        atual = []
        tamanho = 0
        j = i
        while j < n:
            cabe = tamanho == 0 or tamanho + len(unidades[j]) <= tamanho_alvo
            ainda_pequeno = tamanho < tamanho_minimo
            if not cabe and not ainda_pequeno:
                break
            atual.append(unidades[j])
            tamanho += len(unidades[j]) + 2
            j += 1
        chunks.append((i, j - 1, "\n\n".join(atual)))

        if j >= n:
            break

        # Recua a partir do fim do chunk atual para gerar sobreposição no próximo.
        k = j - 1
        acumulado = 0
        while k > i and acumulado < sobreposicao:
            acumulado += len(unidades[k]) + 2
            k -= 1
        i = max(k + 1, i + 1)  # garante progresso mesmo se uma unidade for enorme

    return chunks


# --------------------------------------------------------------------------
# SALVE
# --------------------------------------------------------------------------

def normalizar_lista_csv(valor_bruto: str | None) -> list[str]:
    """"Amazônia, Cerrado, Pantanal" -> ["Amazônia", "Cerrado", "Pantanal"].

    Usado para todo campo de ficha SALVE que vem como string separada por
    vírgula mas precisa virar filtro de payload no Qdrant
    (backend/services/retrieval.py, FieldCondition com MatchAny) — hoje
    `bioma` e `estados`. Lista, não string, porque o MatchAny do Qdrant casa
    "algum elemento da lista é igual a X"; contra a string original
    ("Amazônia, Cerrado, Pantanal") nunca bateria, porque nenhum valor
    sozinho é igual à string inteira.
    """
    return [v.strip() for v in (valor_bruto or "").split(",") if v.strip()]


def chunkar_ficha_salve(dados: dict, caminho_relativo: str) -> list[dict]:
    cabecalho = (
        f"Espécie: {dados.get('nome_cientifico', '')}"
        + (f" ({dados.get('nome_comum')})" if dados.get("nome_comum") else "")
        + f"\nGrupo: {dados.get('grupo', '')}"
        + f"\nCategoria de risco: {dados.get('categoria_risco_completa', '')}"
        + f"\nBioma: {dados.get('bioma', '')}"
        + f"\nEstados: {dados.get('estados', '')}"
        + f"\nDOI: {dados.get('doi', '')}"
    )

    chunks = []
    secoes = dados.get("secoes") or {}
    for chave_secao, texto_secao in secoes.items():
        if not texto_secao or not texto_secao.strip():
            continue

        nome_secao = NOMES_SECOES.get(chave_secao, chave_secao)
        unidades = unidades_de_texto(texto_secao)
        agrupados = agrupar_em_chunks(unidades)

        for parte, (_, _, texto_chunk) in enumerate(agrupados, start=1):
            texto_final = f"{cabecalho}\nSeção: {nome_secao}\n\n{texto_chunk}"
            chunks.append({
                "fonte": "salve",
                "documento": dados.get("nome_cientifico"),
                "secao": chave_secao,
                "parte": parte,
                "n_partes": len(agrupados),
                "nome_comum": dados.get("nome_comum"),
                "grupo": dados.get("grupo"),
                "categoria_risco": dados.get("categoria_risco"),
                "bioma": normalizar_lista_csv(dados.get("bioma")),
                "estados": normalizar_lista_csv(dados.get("estados")),
                "doi": dados.get("doi"),
                "url_origem": dados.get("url_origem"),
                "caminho_local": caminho_relativo,
                "data_coleta": dados.get("data_coleta"),
                "nivel_sensibilidade": "autorizado",
                "texto": texto_final,
            })
    return chunks


# --------------------------------------------------------------------------
# Monitora / PANs (PDFs por página)
# --------------------------------------------------------------------------

def janelas_por_pagina(dados: dict, fonte: str, identificador_doc: str) -> list[tuple[int, int, str]]:
    """Redige os padrões estruturados de cada página e agrupa o texto em janelas.

    Retorna lista de (pagina_inicio, pagina_fim, texto), na ordem do documento.
    """
    # Lista de (unidade_texto, pagina) preservando a ordem das páginas.
    unidades_com_pagina: list[tuple[str, int]] = []
    for pagina in dados.get("paginas") or []:
        texto_pagina = pagina.get("texto", "")
        if not texto_pagina.strip():
            continue
        texto_pagina, contagens = redigir_texto(texto_pagina)
        if contagens:
            _documentos_com_redacao[fonte].add(identificador_doc)
            _contagem_redacoes[fonte].update(contagens)
        for unidade in unidades_de_texto(texto_pagina):
            unidades_com_pagina.append((unidade, pagina["pagina"]))

    agrupados = agrupar_em_chunks([u for u, _ in unidades_com_pagina])
    return [
        (unidades_com_pagina[i][1], unidades_com_pagina[j][1], texto)
        for i, j, texto in agrupados
    ]


def chunkar_documento_pdf(dados: dict, fonte: str, caminho_relativo: str) -> list[dict]:
    # Monitora/PANs vêm de fontes públicas, mas o PDF pode conter e-mail/telefone/CPF
    # de pesquisadores ou coordenadas de ocorrência de espécie embutidos no meio do
    # texto — isso é diferente de "o documento inteiro é sensível" (ver
    # docs/processos/triagem_pendente_sensibilidade_copyright.md). Por isso a
    # redação acontece aqui, no chunking, e não como um filtro de documento inteiro.
    identificador_doc = f"{fonte}/{caminho_relativo}"

    janelas = janelas_por_pagina(dados, fonte, identificador_doc)

    chunks = []
    for idx, (pagina_inicio, pagina_fim, texto_chunk) in enumerate(janelas, start=1):
        chunks.append({
            "fonte": fonte,
            "documento": dados.get("nome_arquivo"),
            "categoria": dados.get("subdir"),
            "contexto": dados.get("contexto"),
            "parte": idx,
            "n_partes": len(janelas),
            "pagina_inicio": pagina_inicio,
            "pagina_fim": pagina_fim,
            "url_origem": dados.get("url_origem"),
            "caminho_local": caminho_relativo,
            "data_coleta": dados.get("data_extracao"),
            "nivel_sensibilidade": "autorizado",
            "texto": texto_chunk,
        })
    return chunks


# --------------------------------------------------------------------------
# Publicações científicas do RAN (PDFs por página + metadados do catálogo)
# --------------------------------------------------------------------------

LIMITE_TITULO_CABECALHO = 300
LIMITE_AUTORIA_CABECALHO = 200


def _abreviar(texto: str, limite: int) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def extrair_ano(valor) -> str | None:
    """O catálogo traz o ano como "2003" ou como data ("2019-08-02 00:00:00")."""
    achado = re.search(r"\b(1[89]|20)\d{2}\b", str(valor or ""))
    return achado.group(0) if achado else None


def cabecalho_publicacao(dados: dict) -> str:
    """Cabeçalho bibliográfico repetido em cada chunk da publicação.

    Um trecho solto de artigo raramente diz de que trabalho veio; o cabeçalho
    dá esse contexto à busca e à citação. Arquivo que reúne várias publicações
    (metadados mesclados com " | " por extrair_texto_publicacoes.py) ou sem
    título no catálogo é identificado só pelo nome do arquivo: não dá para
    saber a qual dos trabalhos o trecho pertence.
    """
    titulo = dados.get("titulo")
    if not titulo or " | " in str(titulo):
        return f"Publicação (arquivo): {Path(dados.get('nome_arquivo') or '').stem}"

    linhas = [f"Publicação: {_abreviar(str(titulo), LIMITE_TITULO_CABECALHO)}"]
    autor = dados.get("autor")
    ano = extrair_ano(dados.get("ano"))
    if autor:
        autoria = _abreviar(str(autor), LIMITE_AUTORIA_CABECALHO)
        linhas.append(f"Autoria: {autoria}" + (f" ({ano})" if ano else ""))
    elif ano:
        linhas.append(f"Ano: {ano}")
    if dados.get("tipologia"):
        linhas.append(f"Tipo: {dados['tipologia']}")
    return "\n".join(linhas)


def chunkar_publicacao(dados: dict, caminho_relativo: str) -> list[dict]:
    # A redação de CPF/e-mail/telefone/coordenada segue a mesma regra de
    # Monitora/PANs (regras_pii.py).
    janelas = janelas_por_pagina(dados, "publicacoes", f"publicacoes/{caminho_relativo}")
    cabecalho = cabecalho_publicacao(dados)

    chunks = []
    for idx, (pagina_inicio, pagina_fim, texto_chunk) in enumerate(janelas, start=1):
        chunks.append({
            "fonte": "publicacoes",
            "documento": dados.get("nome_arquivo"),
            "categoria": dados.get("pasta_origem"),
            "titulo": dados.get("titulo"),
            "autor": dados.get("autor"),
            "ano": extrair_ano(dados.get("ano")),
            "fonte_bibliografica": dados.get("fonte_bibliografica"),
            "doi": dados.get("doi"),
            "tipologia": dados.get("tipologia"),
            "parte": idx,
            "n_partes": len(janelas),
            "pagina_inicio": pagina_inicio,
            "pagina_fim": pagina_fim,
            "url_origem": None,
            "caminho_local": caminho_relativo,
            "caminho_original": dados.get("caminho_original"),
            "data_coleta": dados.get("data_extracao"),
            "metodo_extracao": dados.get("metodo_extracao"),
            "nivel_sensibilidade": "autorizado",
            "acesso": "interno",
            "texto": f"{cabecalho}\n\n{texto_chunk}",
        })
    return chunks


# --------------------------------------------------------------------------
# Orquestração
# --------------------------------------------------------------------------

def processar_fonte(fonte: str) -> dict:
    fonte_dir = AUTORIZADOS_DIR / fonte
    if not fonte_dir.exists():
        print(f"Diretório {fonte_dir} não encontrado.")
        return {"documentos": 0, "chunks": 0, "erros": 0}

    arquivos = sorted(fonte_dir.rglob("*.json"))
    relatorio = {"documentos": 0, "chunks": 0, "erros": 0}

    output_dir = OUTPUT_DIR / fonte
    output_dir.mkdir(parents=True, exist_ok=True)
    saida = output_dir / "chunks.jsonl"

    with saida.open("w", encoding="utf-8") as f_out:
        for arquivo in arquivos:
            caminho_relativo = str(arquivo.relative_to(fonte_dir))
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
                if fonte == "salve":
                    chunks = chunkar_ficha_salve(dados, caminho_relativo)
                elif fonte == "publicacoes":
                    chunks = chunkar_publicacao(dados, caminho_relativo)
                else:
                    chunks = chunkar_documento_pdf(dados, fonte, caminho_relativo)

                for indice, chunk in enumerate(chunks):
                    chunk["chunk_id"] = f"{fonte}:{caminho_relativo}:{indice}"
                    f_out.write(json.dumps(chunk, ensure_ascii=False) + "\n")

                relatorio["documentos"] += 1
                relatorio["chunks"] += len(chunks)

            except Exception as e:
                print(f"  ✗ {caminho_relativo} — ERRO: {e}", file=sys.stderr)
                relatorio["erros"] += 1

    print(f"  [{fonte}] {relatorio['documentos']} documentos → {relatorio['chunks']} chunks "
          f"({relatorio['erros']} erros) — {saida.relative_to(RAIZ)}")
    return relatorio


def salvar_relatorio_anonimizacao(rotulo: str, fontes: tuple[str, ...], destino: Path) -> bool:
    """Grava a auditoria das redações das fontes dadas. Não grava (nem apaga o
    relatório anterior) se nenhuma delas teve redação nesta execução."""
    contagem: Counter = Counter()
    documentos: set[str] = set()
    for fonte in fontes:
        contagem.update(_contagem_redacoes[fonte])
        documentos |= _documentos_com_redacao[fonte]
    if not contagem:
        return False

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(
            {
                "total_documentos_com_redacao": len(documentos),
                "total_substituicoes_por_flag": dict(contagem),
                "documentos_afetados": sorted(documentos),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"\nAnonimização automática ({rotulo}): {len(documentos)} documentos "
        f"tiveram ao menos 1 trecho redigido (CPF/e-mail/telefone/coordenada). "
        f"Relatório de auditoria: {destino.relative_to(RAIZ)}"
    )
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fonte", choices=FONTES, default=None,
                        help="Processar apenas esta fonte (padrão: todas)")
    args = parser.parse_args()

    fontes = [args.fonte] if args.fonte else FONTES

    total = {"documentos": 0, "chunks": 0, "erros": 0}
    print("Gerando chunks a partir de 03_documentos_autorizados/ ...\n")
    for fonte in fontes:
        rel = processar_fonte(fonte)
        for k in total:
            total[k] += rel.get(k, 0)

    print(f"\nCONCLUÍDO — {total['documentos']} documentos, {total['chunks']} chunks, "
          f"{total['erros']} erros no total.")

    salvou = False
    for rotulo, fontes_relatorio, destino in (
        ("Monitora/PANs", ("monitora", "pans"), RELATORIO_ANONIMIZACAO),
        ("publicações", ("publicacoes",), RELATORIO_ANONIMIZACAO_PUBLICACOES),
    ):
        salvou = salvar_relatorio_anonimizacao(rotulo, fontes_relatorio, destino) or salvou
    if salvou:
        print(
            "Lembrete: só os padrões estruturados são redigidos automaticamente — menções "
            "semânticas (localização de espécie, palavra de restrição) continuam dependendo "
            "da revisão humana em triagem_sensibilidade.py."
        )

if __name__ == "__main__":
    main()
