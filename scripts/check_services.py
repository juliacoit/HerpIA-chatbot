#!/usr/bin/env python3
"""
scripts/check_services.py
─────────────────────────
Verifica se os serviços de infraestrutura (PostgreSQL e Qdrant) estão
acessíveis a partir desta máquina.

Uso:
    python scripts/check_services.py

Pré-requisitos:
    pip install python-dotenv requests psycopg[binary]

Se estiver no PC de desenvolvimento, certifique-se de que o túnel SSH
está ativo antes de rodar este script:

    ssh -N -L 5432:localhost:5432 -L 6333:localhost:6333 usuario@IP_DO_SERVIDOR
"""

import sys
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[✓] python-dotenv carregado — variáveis do .env aplicadas.")
except ImportError:
    print("[!] python-dotenv não instalado. Usando variáveis de ambiente do sistema.")
    print("    Para instalar: pip install python-dotenv\n")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ran_user:change_me@localhost:5432/ran_chatbot"
)

print()
print("=" * 55)
print("  Chatbot RAN/ICMBio — Verificação de serviços")
print("=" * 55)
print(f"  Qdrant URL   : {QDRANT_URL}")
print(f"  Database URL : {DATABASE_URL}")
print("=" * 55)
print()

errors = []

print("[1/2] Testando conexão com Qdrant...")
try:
    import requests
    resp = requests.get(f"{QDRANT_URL}/healthz", timeout=5)
    if resp.status_code == 200:
        print(f"      ✅ Qdrant acessível em {QDRANT_URL}")
    else:
        msg = f"Qdrant respondeu com status inesperado: {resp.status_code}"
        print(f"      ⚠️  {msg}")
        errors.append(msg)
except requests.exceptions.ConnectionError:
    msg = (
        f"Não foi possível conectar ao Qdrant em {QDRANT_URL}.\n"
        "      Verifique se o Docker está rodando no servidor e se o túnel SSH está ativo."
    )
    print(f"      ❌ {msg}")
    errors.append(msg)
except ImportError:
    msg = "Biblioteca 'requests' não instalada. Execute: pip install requests"
    print(f"      ⚠️  {msg}")
    errors.append(msg)

print()

print("[2/2] Testando conexão com PostgreSQL...")
try:
    import psycopg
    conn = psycopg.connect(DATABASE_URL, connect_timeout=5)
    conn.close()
    print(f"      ✅ PostgreSQL acessível — conexão estabelecida com sucesso.")
except psycopg.OperationalError as e:
    msg = (
        f"Não foi possível conectar ao PostgreSQL.\n"
        f"      Erro: {e}\n"
        "      Verifique se o Docker está rodando e se o túnel SSH está ativo."
    )
    print(f"      ❌ {msg}")
    errors.append(msg)
except ImportError:
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        conn.close()
        print(f"      ✅ PostgreSQL acessível (via psycopg2).")
    except psycopg2.OperationalError as e:
        msg = (
            f"Não foi possível conectar ao PostgreSQL.\n"
            f"      Erro: {e}\n"
            "      Verifique se o Docker está rodando e se o túnel SSH está ativo."
        )
        print(f"      ❌ {msg}")
        errors.append(msg)
    except ImportError:
        msg = (
            "Nenhum driver PostgreSQL encontrado.\n"
            "      Instale com: pip install psycopg[binary]"
        )
        print(f"      ⚠️  {msg}")
        errors.append(msg)

print()
print("=" * 55)
if not errors:
    print("  ✅ Todos os serviços estão acessíveis!")
    print()
    print("  Próximos passos:")
    print("  - Rode os pipelines de ingestão")
    print("  - Acesse o Qdrant em: " + QDRANT_URL + "/dashboard")
    sys.exit(0)
else:
    print(f"  ❌ {len(errors)} problema(s) encontrado(s).")
    print()
    print("  Dicas de solução:")
    print("  1. No PC servidor: docker compose up -d")
    print("  2. No PC desenvolvimento: abra o túnel SSH antes de rodar este script")
    print("     ssh -N -L 5432:localhost:5432 -L 6333:localhost:6333 usuario@IP_SERVIDOR")
    print("  3. Instale as dependências: pip install python-dotenv requests psycopg[binary]")
    sys.exit(1)
print("=" * 55)
