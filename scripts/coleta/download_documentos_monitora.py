"""
Download dos documentos listados nos metadados do Programa Monitora.

Lê todos os arquivos metadados.json em 01_fontes_web/monitora/*/
e baixa cada documento para 01_fontes_web/monitora/<categoria>/documentos/.

Uso:
    python download_documentos_monitora.py
    python download_documentos_monitora.py --categoria materiais-de-apoio
    python download_documentos_monitora.py --dry-run
    python download_documentos_monitora.py --servidor 10.62.62.191
"""

import argparse
import json
import logging
import time
from pathlib import Path

import requests


def _get_monitora_dir(servidor=None):
    """Retorna o caminho para a pasta do Monitora.

    Se servidor for fornecido, retorna um caminho UNC remoto.
    Caso contrário, retorna o caminho local do projeto.
    """
    if servidor:
        return Path(f"\\\\{servidor}\\monitora_dados\\01_fontes_web\\monitora")
    return Path(__file__).resolve().parents[2] / "01_fontes_web" / "monitora"


MONITORA_DIR = None  # Será definido em main() após parsing dos argumentos
HEADERS = {"User-Agent": "Mozilla/5.0 (coleta RAN/ICMBio chatbot; uso interno)"}
PAUSA_ENTRE_REQUISICOES = 1.0  # segundos
MAX_TENTATIVAS = 3
TIMEOUT = 30  # segundos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def carregar_metadados(categoria=None):
    padrao = f"{categoria}/metadados.json" if categoria else "*/metadados.json"
    metas = []
    for caminho in sorted(MONITORA_DIR.glob(padrao)):
        with open(caminho, encoding="utf-8") as f:
            meta = json.load(f)
        metas.append((caminho.parent, meta))
    return metas


def deduplicar_por_url(documentos):
    vistos = set()
    unicos = []
    for doc in documentos:
        url = doc.get("url", "").strip()
        if url and url not in vistos:
            vistos.add(url)
            unicos.append(doc)
    return unicos


def baixar_arquivo(url, destino, sessao):
    """Tenta baixar um arquivo com retentativas. Retorna (sucesso, codigo_http)."""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resp = sessao.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
            if resp.status_code == 200:
                destino.parent.mkdir(parents=True, exist_ok=True)
                with open(destino, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True, 200
            if resp.status_code == 404:
                return False, 404
            log.warning(f"HTTP {resp.status_code} — {url} (tentativa {tentativa})")
        except requests.RequestException as e:
            log.warning(f"Erro de conexão — {url} (tentativa {tentativa}): {e}")
        if tentativa < MAX_TENTATIVAS:
            time.sleep(2 ** tentativa)
    return False, -1


def main():
    global MONITORA_DIR
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Lista arquivos sem baixar")
    parser.add_argument("--categoria", metavar="SLUG", help="Baixa apenas a categoria especificada (ex: materiais-de-apoio)")
    parser.add_argument(
        "--servidor",
        metavar="IP",
        help="IP ou hostname do servidor para download remoto (ex: 10.62.62.191 ou RAN_AvalFauna_FHF9703)"
    )
    args = parser.parse_args()

    MONITORA_DIR = _get_monitora_dir(args.servidor)

    if not MONITORA_DIR.exists():
        log.error(f"Caminho não acessível: {MONITORA_DIR}")
        if args.servidor:
            log.error("Verifique se:")
            log.error(f"  1. O servidor {args.servidor} está online e acessível")
            log.error(f"  2. O compartilhamento 'monitora_dados' foi criado")
            log.error(f"  3. Há conexão de rede entre os computadores")
        return

    modo = "REMOTO" if args.servidor else "LOCAL"
    log.info(f"Modo de download: {modo}")
    log.info(f"Destino: {MONITORA_DIR}")

    todos_metadados = carregar_metadados(args.categoria)
    if not todos_metadados:
        log.error("Nenhum metadados.json encontrado.")
        return

    sessao = requests.Session()
    resultados = []
    total_baixados = total_pulados = total_falhas = 0

    for categoria_dir, meta in todos_metadados:
        slug = meta["slug"]
        documentos = deduplicar_por_url(meta.get("documentos", []))
        dir_destino = categoria_dir / "documentos"

        log.info(f"{'─'*60}")
        log.info(f"Categoria: {meta['nome']}  ({len(documentos)} arquivo(s) únicos)")

        for doc in documentos:
            url = doc["url"]
            nome_arquivo = doc["nome_arquivo"]
            destino = dir_destino / nome_arquivo

            if destino.exists():
                log.info(f"  SKIP  {nome_arquivo}")
                resultados.append({"slug": slug, "arquivo": nome_arquivo, "status": "skip"})
                total_pulados += 1
                continue

            if args.dry_run:
                log.info(f"  DRY   {destino.relative_to(MONITORA_DIR)}")
                log.info(f"        {url}")
                resultados.append({"slug": slug, "arquivo": str(destino.relative_to(MONITORA_DIR)), "status": "dry-run", "url": url})
                continue

            log.info(f"  GET   {nome_arquivo}")
            ok, codigo = baixar_arquivo(url, destino, sessao)

            if ok:
                tamanho_kb = destino.stat().st_size // 1024
                log.info(f"        OK  {tamanho_kb} KB")
                resultados.append({"slug": slug, "arquivo": nome_arquivo, "status": "ok", "kb": tamanho_kb})
                total_baixados += 1
            else:
                log.warning(f"        FALHA  HTTP {codigo}  {url}")
                resultados.append({"slug": slug, "arquivo": nome_arquivo, "status": f"falha_{codigo}", "url": url})
                total_falhas += 1

            time.sleep(PAUSA_ENTRE_REQUISICOES)

    log.info(f"{'─'*60}")
    log.info(f"Concluído — {total_baixados} baixados | {total_pulados} já existiam | {total_falhas} falhas")

    relatorio = MONITORA_DIR / "relatorio_download.json"
    with open(relatorio, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    log.info(f"Relatório salvo em {relatorio}")


if __name__ == "__main__":
    main()
