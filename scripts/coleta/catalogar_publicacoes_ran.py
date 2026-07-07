"""Cataloga os arquivos de 02_publicacoes_cientificas_ran/ cruzando com a
planilha de controle mantida pela equipe do RAN.

Lê a planilha mais recente de publicações e normaliza cada aba (Artigo, Boletim,
Livro/Capítulo, Resumo de Evento, Dissertação/Tese, Monografia/TCC, Outras
publicações) em registros bibliográficos. Cruza cada arquivo físico (PDF/DOCX)
com o(s) registro(s) correspondente(s) pelo número no início do nome do arquivo
(ex.: "12 - Alves Junior et al, 2012.pdf" -> Nº 12 na aba), incluindo faixas de
números quando um único arquivo cobre várias linhas da planilha (ex.: um livro
inteiro com vários capítulos, "5 a 16 - Balestra et al, 2016.pdf" -> Nº 5 a 16).

Também identifica, por hash de conteúdo, arquivos que são cópias exatas de
outro já presente no acervo (comum entre "Boletins_RAN-2015 a 2018" e
"Matérias_ICMBio-em-Foco_Outros Meios"), e arquivos-placeholder que a própria
equipe deixou marcados como "Faltam" (documento ainda não obtido, não é uma
publicação real).

Não move nem copia nenhum arquivo, nem lê o conteúdo além do necessário para o
hash — apenas gera um catálogo (Fase 1.4 do roadmap) para apoiar a decisão de
quais publicações entram no acervo (03_documentos_autorizados/) e quais
precisam de avaliação de sensibilidade (04_documentos_pendentes_avaliacao/).

Saída: 06_inventario/catalogo_publicacoes_ran.json

Uso:
    python scripts/coleta/catalogar_publicacoes_ran.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
SRC_DIR = RAIZ / "02_publicacoes_cientificas_ran"
PLANILHA = (
    SRC_DIR
    / "bkup planilhas antigas"
    / "Publicacoes_RAN_Herpetofauna_2023_2025_ATUALIZAÇÃO_15_11_2025.xlsx"
)
OUTPUT = RAIZ / "06_inventario" / "catalogo_publicacoes_ran.json"

# pasta em Publicacoes_Cientificas_Divulgacoes/ -> aba correspondente na planilha
# (None implícito = pasta sem aba mapeada, ex.: sem numeração nos arquivos)
MAPA_PASTA_ABA = {
    "Artigo, Nota, Comunicação Científica": "Artigo,Nota,Comun. Cient.",
    # As duas pastas de boletim/matérias se cruzam com a mesma aba: a planilha
    # não distingue "Boletim RAN" (edição própria) de "ICMBio em Foco"
    # (matéria em veículo de terceiros) em pastas separadas.
    "Boletins_RAN-2015 a 2018": "Boletim",
    "Matérias_ICMBio-em-Foco_Outros Meios": "Boletim",
    "Livro, Capítulo Livro, Cartilha, Revista, Manual": "Liv,Cap.Liv,Cart,Mat.Rev.,Man.",
    "Monografias_TCC": "Monografia_TCC",
    "Outras Publicações Técnicas": "Outras publicações",
    "Resumos_Eventos Científicos": "Resumo_Evento Científico",
    "Teses e Dissertações": "Dissertação, Tese",
}

# pastas que contêm as próprias planilhas de controle, não documentos-fonte
PASTAS_IGNORADAS = {"Planilhas publicações bkup", "bkup planilhas antigas"}

RE_FAIXA = re.compile(r"^(\d+)\s*[ae]\s*(\d+)[\s_-]+")
RE_NUMERO = re.compile(r"^(\d+)[\s_-]+")
RE_ANO = re.compile(r"(19|20)\d{2}")
RE_FALTAM = re.compile(r"faltam", re.IGNORECASE)


def normalizar_linha(sheet_name, header, row):
    d = {header[i]: row[i] for i in range(len(header)) if header[i]}
    numero = d.get("Nº") or d.get("N°")
    if numero is None:
        return None
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        return None

    def campo(*chaves):
        for chave in chaves:
            v = d.get(chave)
            if v is not None:
                return v.strip() if isinstance(v, str) else v
        return None

    return {
        "aba": sheet_name,
        "numero": numero,
        "tipologia": campo("Tipologia"),
        "autor": campo("Autor", "Autor/es ", "Autores"),
        "ano": str(campo("Ano")) if campo("Ano") is not None else None,
        "titulo": campo("Título", "Título "),
        "fonte": campo(
            "Periódico",
            "Revista/Livro/Jornal/Outros",
            "Editora",
            "Entidade/Curso/Evento",
            "Instituição",
        ),
        "doi": campo("DOI"),
    }


def carregar_planilha():
    wb = openpyxl.load_workbook(PLANILHA, data_only=True)
    registros_por_aba = {}
    for ws in wb.worksheets:
        linhas = list(ws.iter_rows(values_only=True))
        if not linhas:
            continue
        header = [h.strip() if isinstance(h, str) else h for h in linhas[0]]
        registros = {}
        for row in linhas[1:]:
            rec = normalizar_linha(ws.title.strip(), header, row)
            if rec:
                registros.setdefault(rec["numero"], []).append(rec)
        registros_por_aba[ws.title.strip()] = registros
    return registros_por_aba


def extrair_numeracao(nome_arquivo):
    """Retorna a lista de números de referência que o nome do arquivo indica.

    Aceita tanto um número único ("12 - ...") quanto uma faixa ("5 a 16 - ...",
    que cobre as linhas 5 a 16 da planilha — comum quando um único PDF reúne
    vários capítulos ou vários resumos de evento).
    """
    m = RE_FAIXA.match(nome_arquivo)
    if m:
        inicio, fim = int(m.group(1)), int(m.group(2))
        if fim >= inicio:
            return list(range(inicio, fim + 1))
    m = RE_NUMERO.match(nome_arquivo)
    if m:
        return [int(m.group(1))]
    return []


def extrair_ano(nome_arquivo):
    m = RE_ANO.search(nome_arquivo)
    return m.group(0) if m else None


def calcular_hash(caminho):
    h = hashlib.md5()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


STATUS_CASADO = {"casado", "casado_faixa"}


def status_preliminar(numeracao, registros, aba):
    if not aba:
        return "sem_pasta_mapeada", None
    if not numeracao:
        return "sem_numero_no_nome", None
    if len(numeracao) == 1:
        candidatos = registros.get(numeracao[0], [])
        if not candidatos:
            return "numero_nao_encontrado_na_planilha", None
        if len(candidatos) > 1:
            return "numero_ambiguo_na_planilha", None
        return "casado", candidatos[0]
    encontrados = [
        registros[n][0] for n in numeracao if len(registros.get(n, [])) == 1
    ]
    if encontrados:
        return "casado_faixa", encontrados
    return "faixa_nao_encontrada_na_planilha", None


def catalogar():
    registros_por_aba = carregar_planilha()

    arquivos_por_pasta = {}
    for pasta in sorted(p.name for p in SRC_DIR.iterdir() if p.is_dir()):
        if pasta in PASTAS_IGNORADAS:
            continue
        arquivos_por_pasta[pasta] = [
            a
            for a in sorted((SRC_DIR / pasta).rglob("*"))
            if a.is_file() and not a.name.startswith(".")
        ]

    # hash de todo o acervo, para detectar cópias exatas entre pastas
    # (ex.: mesmo PDF presente em Boletins_RAN-2015 a 2018 e em Matérias_ICMBio-em-Foco)
    caminhos_por_hash = {}
    for arquivos in arquivos_por_pasta.values():
        for arquivo in arquivos:
            caminhos_por_hash.setdefault(calcular_hash(arquivo), []).append(arquivo)

    entradas = {}
    for pasta, arquivos in arquivos_por_pasta.items():
        aba = MAPA_PASTA_ABA.get(pasta)
        registros = registros_por_aba.get(aba, {}) if aba else {}
        for arquivo in arquivos:
            nome = arquivo.name
            numeracao = extrair_numeracao(nome)
            if RE_FALTAM.search(nome):
                status, metadados = "placeholder_faltante", None
            else:
                status, metadados = status_preliminar(numeracao, registros, aba)
            entradas[str(arquivo)] = {
                "caminho": str(arquivo.relative_to(RAIZ)),
                "pasta_origem": pasta,
                "extensao": arquivo.suffix.lower(),
                "numeracao_extraida": numeracao,
                "ano_extraido_nome": extrair_ano(nome),
                "aba_planilha": aba,
                "status": status,
                "metadados": metadados,
                "duplicata_de": None,
            }

    # entre cópias exatas (mesmo hash), a canônica é a que já casou por número;
    # as demais viram "duplicata_exata" e herdam os metadados da canônica
    for grupo in caminhos_por_hash.values():
        if len(grupo) < 2:
            continue
        canonico = next(
            (p for p in grupo if entradas[str(p)]["status"] in STATUS_CASADO),
            min(grupo, key=str),
        )
        for arquivo in grupo:
            if arquivo == canonico:
                continue
            entrada = entradas[str(arquivo)]
            if entrada["status"] not in STATUS_CASADO:
                entrada["status"] = "duplicata_exata"
                entrada["metadados"] = entradas[str(canonico)]["metadados"]
            entrada["duplicata_de"] = str(canonico.relative_to(RAIZ))

    catalogo = []
    stats = {}
    for pasta, arquivos in arquivos_por_pasta.items():
        aba = MAPA_PASTA_ABA.get(pasta)
        registros = registros_por_aba.get(aba, {}) if aba else {}
        numeros_usados = set()
        casados = 0
        for arquivo in arquivos:
            entrada = entradas[str(arquivo)]
            catalogo.append(entrada)
            if entrada["status"] in STATUS_CASADO:
                casados += 1
                for n in entrada["numeracao_extraida"]:
                    if len(registros.get(n, [])) == 1:
                        numeros_usados.add(n)

        numeros_sem_arquivo = sorted(set(registros.keys()) - numeros_usados) if aba else []
        stats[pasta] = {
            "total_arquivos": len(arquivos),
            "casados_por_numero": casados,
            "aba_planilha": aba,
            "registros_na_aba": len(registros),
            "numeros_na_aba_sem_arquivo_correspondente": numeros_sem_arquivo,
        }

    abas_sem_pasta = sorted(set(registros_por_aba) - set(MAPA_PASTA_ABA.values()))
    return catalogo, stats, abas_sem_pasta


def main():
    if not PLANILHA.exists():
        print(f"Planilha não encontrada: {PLANILHA}", file=sys.stderr)
        sys.exit(1)

    catalogo, stats, abas_sem_pasta = catalogar()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "gerado_de": str(PLANILHA.relative_to(RAIZ)),
                "arquivos": catalogo,
                "estatisticas": stats,
                "abas_sem_pasta_correspondente": abas_sem_pasta,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Catálogo salvo em {OUTPUT.relative_to(RAIZ)} ({len(catalogo)} arquivos)\n")
    for pasta, s in stats.items():
        linha = f"{pasta}: {s['casados_por_numero']}/{s['total_arquivos']} casados por número"
        if s["aba_planilha"]:
            linha += f" | aba: {s['aba_planilha']}"
            faltantes = len(s["numeros_na_aba_sem_arquivo_correspondente"])
            if faltantes:
                linha += f" | {faltantes} nº da planilha sem arquivo"
        else:
            linha += " | sem aba mapeada"
        print(linha)

    if abas_sem_pasta:
        print(f"\nAbas da planilha sem pasta de arquivos correspondente: {abas_sem_pasta}")


if __name__ == "__main__":
    main()
