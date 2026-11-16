"""Prepara os chunks dos documentos do SEI — SEM liberar para indexação.

Os documentos do SEI ainda não passaram pela avaliação humana de sensibilidade
(ADR 0002 e ADR 0010). Este script só deixa o chunking pronto, para que a
indexação possa ser feita por etapas depois da avaliação. Por isso:

  - a saída vai para 07_processados/chunks_pendentes/sei/chunks.jsonl, fora de
    07_processados/chunks/, que é onde indexar_chunks.py procura;
  - todo chunk leva "nivel_sensibilidade": "pendente_avaliacao";
  - "sei" continua fora da lista de fontes de gerar_chunks.py e da indexação.

Entrada: 07_processados/textos_extraidos/sei/ (extrair_texto_sei.py), já sem
CPF, RG, e-mail e telefone. Coordenadas e localizações de espécies ficam
(decisão da Júlia de 2026-11-11). Nomes de pessoas NÃO são removidos.

Estratégias:
  - Texto corrido (PDF, HTML do SEI, Word, PPTX, imagem): janela deslizante
    por página com sobreposição, a mesma de Monitora/PANs.
  - Planilha (xlsx, xls, xlsm, ods): chunks por aba, em linhas inteiras e sem
    sobreposição; a primeira linha da aba (o cabeçalho das colunas) é repetida
    em cada chunk, para a linha solta não perder o significado.
  - ZIP: cada arquivo interno é tratado conforme o próprio tipo.

Cada chunk começa com um cabeçalho de contexto (processo, documento, número
SEI) e registra em "sinais_triagem" os padrões de regras_pii.py encontrados no
documento inteiro — isso permite indexar primeiro os documentos sem sinal.

Documentos idênticos (mesmo sha256) em mais de um processo viram chunks uma vez
só; os demais ficam em "tambem_em". Documentos sem texto útil são pulados.

O terminal mostra só contagens.

Uso:
    python scripts/processamento/gerar_chunks_sei.py [--raiz-dados CAMINHO]

    --raiz-dados  Raiz onde estão 01_fontes_web/ e 07_processados/ (padrão: a
                  raiz deste repositório). Serve para rodar a partir de um
                  worktree, em que as pastas de dados não existem.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts" / "classificacao"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gerar_chunks import (  # noqa: E402
    SOBREPOSICAO,
    TAMANHO_ALVO,
    agrupar_em_chunks,
    dividir_bruto,
    unidades_de_texto,
)
from regras_pii import FLAGS  # noqa: E402

FORMATOS_PLANILHA = {"xlsx", "xlsm", "xls", "ods"}
MIN_CHARS_DOCUMENTO = 50
LIMITE_CABECALHO_COLUNAS = 600
LIMITE_TITULO = 200


def _abreviar(texto: str, limite: int) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def carregar_catalogo(raiz_dados: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Devolve (título por número SEI, tipo por número de processo).

    No catálogo o título termina com o número SEI, entre parênteses ou solto;
    o número é tirado do título, que passa a trazer só o tipo e a numeração
    própria do documento.
    """
    caminho = raiz_dados / "01_fontes_web" / "sei" / "documentos_por_processo.json"
    titulos, tipos = {}, {}
    if not caminho.exists():
        return titulos, tipos
    for processo in json.loads(caminho.read_text(encoding="utf-8"))["processos"]:
        tipos[processo["numero"]] = processo.get("tipo") or ""
        for documento in processo.get("documentos") or []:
            achado = re.search(r"\s*\(?(\d{6,})\)?\s*$", documento.get("titulo") or "")
            if achado:
                titulos[achado.group(1)] = documento["titulo"][: achado.start()].strip()
    return titulos, tipos


def sinais_triagem(texto: str) -> list[str]:
    """Chaves de regras_pii.py presentes no texto (marcas de redação não contam)."""
    achados = []
    for chave, regex, *_ in FLAGS:
        if any(texto[m.end(): m.end() + 10] != " removido]" for m in regex.finditer(texto)):
            achados.append(chave)
    return achados


def formato_do_arquivo_interno(nome: str) -> str:
    return Path(nome).suffix.lower().lstrip(".")


def segmentos(dados: dict) -> list[dict]:
    """Agrupa as páginas em segmentos: o documento inteiro ou, num ZIP, cada
    arquivo interno. Cada segmento é {"formato", "arquivo_interno", "paginas"}."""
    if dados.get("formato") != "zip":
        return [{"formato": dados.get("formato"), "arquivo_interno": None, "paginas": dados.get("paginas") or []}]
    grupos: dict[str, dict] = {}
    for pagina in dados.get("paginas") or []:
        nome = pagina.get("arquivo_interno") or ""
        grupos.setdefault(nome, {"formato": formato_do_arquivo_interno(nome), "arquivo_interno": nome, "paginas": []})
        grupos[nome]["paginas"].append(pagina)
    return list(grupos.values())


def janelas_de_texto(paginas: list[dict]) -> list[dict]:
    """Janela deslizante sobre o texto corrido, registrando as páginas de cada chunk."""
    unidades: list[tuple[str, int]] = []
    for pagina in paginas:
        for unidade in unidades_de_texto(pagina.get("texto") or ""):
            unidades.append((unidade, pagina["pagina"]))
    return [
        {"pagina_inicio": unidades[i][1], "pagina_fim": unidades[j][1], "aba": None, "texto": texto}
        for i, j, texto in agrupar_em_chunks([u for u, _ in unidades], TAMANHO_ALVO, SOBREPOSICAO)
    ]


def janelas_de_planilha(paginas: list[dict]) -> list[dict]:
    """Chunks por aba, em linhas inteiras, repetindo a linha de cabeçalho das colunas."""
    janelas = []
    for pagina in paginas:
        linhas = [linha for linha in (pagina.get("texto") or "").split("\n") if linha.strip()]
        if not linhas:
            continue
        colunas = _abreviar(linhas[0], LIMITE_CABECALHO_COLUNAS)
        corpo = linhas[1:] or linhas  # aba de uma linha só: a linha é o próprio conteúdo
        prefixo = f"Colunas: {colunas}\n" if len(linhas) > 1 else ""

        # Linha maior que o alvo (célula com texto longo) é cortada por tamanho.
        pedacos = []
        for linha in corpo:
            pedacos.extend(dividir_bruto(linha, TAMANHO_ALVO) if len(linha) > TAMANHO_ALVO else [linha])

        atual, tamanho = [], 0
        for pedaco in pedacos:
            if atual and tamanho + len(pedaco) > TAMANHO_ALVO:
                janelas.append((pagina, prefixo + "\n".join(atual)))
                atual, tamanho = [], 0
            atual.append(pedaco)
            tamanho += len(pedaco) + 1
        if atual:
            janelas.append((pagina, prefixo + "\n".join(atual)))
    return [
        {"pagina_inicio": pagina["pagina"], "pagina_fim": pagina["pagina"], "aba": pagina.get("aba"), "texto": texto}
        for pagina, texto in janelas
    ]


def cabecalho(dados: dict, titulo: str | None, tipo_processo: str | None, segmento: dict, janela: dict) -> str:
    linha_processo = f"Processo SEI nº {dados.get('processo')}"
    if tipo_processo:
        linha_processo += f" — {_abreviar(tipo_processo, LIMITE_TITULO)}"
    linha_documento = f"Documento nº SEI {dados.get('numero_sei')}"
    if titulo:
        linha_documento = f"Documento: {_abreviar(titulo, LIMITE_TITULO)} (nº SEI {dados.get('numero_sei')})"
    linhas = [linha_processo, linha_documento]
    if segmento["arquivo_interno"]:
        linhas.append(f"Arquivo interno: {_abreviar(segmento['arquivo_interno'], LIMITE_TITULO)}")
    if janela.get("aba"):
        linhas.append(f"Aba: {_abreviar(str(janela['aba']), LIMITE_TITULO)}")
    return "\n".join(linhas)


def chunkar_documento_sei(
    dados: dict, caminho_relativo: str, titulo: str | None = None, tipo_processo: str | None = None
) -> list[dict]:
    texto_documento = "\n".join(p.get("texto") or "" for p in dados.get("paginas") or [])
    sinais = sinais_triagem(texto_documento)

    partes = []
    for segmento in segmentos(dados):
        planilha = segmento["formato"] in FORMATOS_PLANILHA
        janelas = janelas_de_planilha(segmento["paginas"]) if planilha else janelas_de_texto(segmento["paginas"])
        for janela in janelas:
            partes.append((segmento, janela, "planilha" if planilha else "texto"))

    chunks = []
    for idx, (segmento, janela, tipo_conteudo) in enumerate(partes, start=1):
        chunks.append({
            "fonte": "sei",
            "documento": dados.get("nome_arquivo"),
            "categoria": tipo_processo or None,
            "processo": dados.get("processo"),
            "numero_sei": dados.get("numero_sei"),
            "titulo": titulo,
            "tipo_conteudo": tipo_conteudo,
            "formato": segmento["formato"],
            "arquivo_interno": segmento["arquivo_interno"],
            "aba": janela["aba"],
            "parte": idx,
            "n_partes": len(partes),
            "pagina_inicio": janela["pagina_inicio"],
            "pagina_fim": janela["pagina_fim"],
            "url_origem": None,
            "caminho_local": caminho_relativo,
            "caminho_original": dados.get("caminho_original"),
            "data_coleta": dados.get("data_download") or dados.get("data_extracao"),
            "metodo_extracao": dados.get("metodo_extracao"),
            "nivel_sensibilidade": "pendente_avaliacao",
            "acesso": "interno",
            "sinais_triagem": sinais,
            "tambem_em": [],
            "texto": f"{cabecalho(dados, titulo, tipo_processo, segmento, janela)}\n\n{janela['texto']}",
        })
    return chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz-dados", type=Path, default=RAIZ,
                        help="Raiz com 01_fontes_web/ e 07_processados/ (padrão: este repositório)")
    args = parser.parse_args()
    raiz_dados = args.raiz_dados.resolve()

    textos_dir = raiz_dados / "07_processados" / "textos_extraidos" / "sei"
    saida = raiz_dados / "07_processados" / "chunks_pendentes" / "sei" / "chunks.jsonl"
    relatorio_json = raiz_dados / "07_processados" / "metadados" / "chunks_sei_relatorio.json"

    titulos, tipos_processo = carregar_catalogo(raiz_dados)
    arquivos = sorted(textos_dir.rglob("*.json"))
    if not arquivos:
        print(f"Nenhum texto extraído em {textos_dir} — rode extrair_texto_sei.py antes.")
        return

    # Primeira passada: documentos idênticos (mesmo sha256) ficam com o primeiro.
    primeiro_por_sha: dict[str, str] = {}
    repetidos: dict[str, list[dict]] = {}
    documentos = []
    contagem = Counter()
    for arquivo in arquivos:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        if sum(len(p.get("texto") or "") for p in dados.get("paginas") or []) < MIN_CHARS_DOCUMENTO:
            contagem["sem_texto"] += 1
            continue
        sha = dados.get("sha256")
        if sha and sha in primeiro_por_sha:
            repetidos.setdefault(primeiro_por_sha[sha], []).append(
                {"processo": dados.get("processo"), "numero_sei": dados.get("numero_sei")}
            )
            contagem["duplicado"] += 1
            continue
        if sha:
            primeiro_por_sha[sha] = dados["numero_sei"]
        documentos.append((arquivo, dados))

    por_tipo, por_formato, por_sinal = Counter(), Counter(), Counter()
    documentos_sem_sinal = chunks_sem_sinal = total_chunks = 0
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8") as f_out:
        for arquivo, dados in documentos:
            caminho_relativo = str(arquivo.relative_to(textos_dir))
            chunks = chunkar_documento_sei(
                dados, caminho_relativo, titulos.get(dados["numero_sei"]), tipos_processo.get(dados.get("processo"))
            )
            contagem["com_chunks" if chunks else "sem_chunks"] += 1
            for indice, chunk in enumerate(chunks):
                chunk["tambem_em"] = repetidos.get(dados["numero_sei"], [])
                chunk["chunk_id"] = f"sei:{caminho_relativo}:{indice}"
                f_out.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                por_tipo[chunk["tipo_conteudo"]] += 1
                por_formato[chunk["formato"]] += 1
            total_chunks += len(chunks)
            if chunks:
                sinais = chunks[0]["sinais_triagem"]
                por_sinal.update(sinais)
                if not sinais:
                    documentos_sem_sinal += 1
                    chunks_sem_sinal += len(chunks)

    relatorio = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "nivel_sensibilidade": "pendente_avaliacao",
        "documentos_lidos": len(arquivos),
        "documentos": dict(contagem),
        "chunks": total_chunks,
        "chunks_por_tipo_conteudo": dict(por_tipo),
        "chunks_por_formato": dict(por_formato),
        "documentos_por_sinal_triagem": dict(por_sinal),
        "documentos_sem_sinal": documentos_sem_sinal,
        "chunks_de_documentos_sem_sinal": chunks_sem_sinal,
    }
    relatorio_json.parent.mkdir(parents=True, exist_ok=True)
    relatorio_json.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(arquivos)} documento(s) lido(s) → {total_chunks} chunks (pendentes de avaliação, NÃO indexados).")
    print(f"  documentos: {dict(contagem)}")
    print(f"  chunks por tipo de conteúdo: {dict(por_tipo)}")
    print(f"  documentos sem nenhum sinal de triagem: {documentos_sem_sinal} ({chunks_sem_sinal} chunks)")
    print(f"  Saída:     {saida}")
    print(f"  Relatório: {relatorio_json}")


if __name__ == "__main__":
    main()
