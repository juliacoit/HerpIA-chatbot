"""Administração das contas de acesso ao HerpIA (ver docs/processos/autenticacao.md).

Não existe autocadastro nem tela de administração: as contas são criadas por
aqui, por quem tem acesso ao servidor e ao .env. A conta nasce sem senha; o
script imprime um código de convite de uso único, que a pessoa usa na tela
"Primeiro acesso" para definir a própria senha. O código aparece só uma
vez — o banco guarda apenas o hash dele.

Uso:
    python scripts/infra/gerenciar_usuarios.py criar nome.sobrenome "Nome Completo"
    python scripts/infra/gerenciar_usuarios.py novo-convite nome.sobrenome   # senha esquecida
    python scripts/infra/gerenciar_usuarios.py desativar nome.sobrenome
    python scripts/infra/gerenciar_usuarios.py reativar nome.sobrenome
    python scripts/infra/gerenciar_usuarios.py listar

Requer o PostgreSQL acessível (DATABASE_URL do .env; ver SETUP_PROJETO.md).
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from backend.config import Settings  # noqa: E402
from backend.db import abrir_pool, fechar_pool  # noqa: E402
from backend.services import auth  # noqa: E402


def _imprimir_convite(usuario: str, codigo: str, dias: int) -> None:
    print(f"Usuário: {auth.normalizar_usuario(usuario)}")
    print(f"Código de convite (uso único, válido por {dias} dias): {codigo}")
    print("Entregue o código à pessoa por um canal seguro; ele não será mostrado de novo.")


def _data(valor) -> str:
    return valor.astimezone().strftime("%Y-%m-%d %H:%M") if valor else "—"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    comandos = parser.add_subparsers(dest="comando", required=True)
    criar = comandos.add_parser("criar", help="cria a conta e gera o código de convite")
    criar.add_argument("usuario")
    criar.add_argument("nome")
    for nome, ajuda in (
        ("novo-convite", "apaga a senha, encerra as sessões e gera novo código de convite"),
        ("desativar", "bloqueia o acesso e encerra as sessões"),
        ("reativar", "libera o acesso de uma conta desativada"),
    ):
        comandos.add_parser(nome, help=ajuda).add_argument("usuario")
    comandos.add_parser("listar", help="lista as contas")
    args = parser.parse_args()

    settings = Settings()
    pool = abrir_pool(settings)
    if pool is None:
        raise SystemExit("PostgreSQL indisponível — ver docker-compose.yml / túnel SSH (SETUP_PROJETO.md).")

    dias = settings.auth_convite_dias
    try:
        if args.comando == "criar":
            codigo = auth.criar_usuario(pool, args.usuario, args.nome, dias)
            _imprimir_convite(args.usuario, codigo, dias)
        elif args.comando == "novo-convite":
            codigo = auth.gerar_novo_convite(pool, args.usuario, dias)
            _imprimir_convite(args.usuario, codigo, dias)
        elif args.comando in ("desativar", "reativar"):
            auth.definir_ativo(pool, args.usuario, ativo=args.comando == "reativar")
            print(f"Conta '{auth.normalizar_usuario(args.usuario)}': {args.comando} concluído.")
        else:
            usuarios = auth.listar_usuarios(pool)
            if not usuarios:
                print("Nenhuma conta cadastrada.")
            for u in usuarios:
                if not u["ativo"]:
                    situacao = "desativada"
                elif u["senha_definida"]:
                    situacao = "ativa"
                else:
                    situacao = f"aguardando primeiro acesso (convite até {_data(u['convite_expira_em'])})"
                print(f"{u['usuario']:<28} {u['nome']:<32} {situacao} | último login: {_data(u['ultimo_login_em'])}")
    except auth.ErroAutenticacao as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        fechar_pool(pool)


if __name__ == "__main__":
    main()
