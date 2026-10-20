"""Tela de acesso do HerpIA: login e primeiro acesso (definição de senha
com código de convite).

Porta `design-system/ui_kits/herpia-assistente/LoginScreen.jsx`: assinatura
do RAN, aviso de acesso restrito e cartão com usuário institucional, senha e
"Entrar". O "Primeiro acesso" não existe no kit — segue a mesma composição.
Não há autocadastro nem recuperação de senha por e-mail: as contas e os
códigos de convite saem de `scripts/infra/gerenciar_usuarios.py` (ver
docs/processos/autenticacao.md).

A sessão fica em `st.session_state.sessao` (token, usuário e nome). Ela vive
só enquanto a aba do navegador está aberta: recarregar a página pede o login
de novo, mesma limitação já documentada para o histórico da conversa.
"""

import streamlit as st
import tema
from cliente_api import ErroAPI, entrar, primeiro_acesso

_ABAS = ["Entrar", "Primeiro acesso"]
TAMANHO_MINIMO_SENHA = 10  # mesmo valor de backend/services/auth.py, só para a dica do campo


def sessao_atual() -> dict | None:
    return st.session_state.get("sessao")


def token_atual() -> str | None:
    sessao = sessao_atual()
    return sessao["token"] if sessao else None


def encerrar_sessao_local(aviso: str | None = None) -> None:
    """Esquece a sessão e a conversa neste navegador — a conversa de uma
    pessoa não pode continuar na tela para a próxima que entrar."""
    st.session_state.sessao = None
    st.session_state.historico = []
    st.session_state.aviso_acesso = aviso


def _abrir_sessao(resposta_login: dict) -> None:
    st.session_state.sessao = {
        "token": resposta_login["token"],
        "usuario": resposta_login["usuario"]["usuario"],
        "nome": resposta_login["usuario"]["nome"],
    }
    st.session_state.historico = []
    st.session_state.mostrar_acesso = False
    st.session_state.aviso_acesso = None


def _formulario_entrar() -> None:
    with st.form("form-entrar"):
        usuario = st.text_input("Usuário institucional", placeholder="nome.sobrenome", autocomplete="username")
        senha = st.text_input("Senha", type="password", autocomplete="current-password")
        enviado = st.form_submit_button("Entrar", type="primary", width="stretch")
    if enviado:
        if not usuario.strip() or not senha:
            st.error("Informe o usuário e a senha.")
        else:
            try:
                _abrir_sessao(entrar(usuario, senha))
            except ErroAPI as exc:
                st.error(str(exc))
            else:
                st.rerun()
    # Depois do erro, não antes dele nem só no caminho sem erro: é quando a
    # senha foi recusada que a pessoa precisa saber o que fazer.
    st.caption("Senha esquecida: solicite um novo código de convite à administração do HerpIA.")


def _formulario_primeiro_acesso() -> None:
    with st.form("form-primeiro-acesso"):
        usuario = st.text_input("Usuário institucional", placeholder="nome.sobrenome", autocomplete="username")
        codigo = st.text_input("Código de convite", help="Fornecido pela administração do HerpIA. Uso único.")
        senha = st.text_input(
            "Nova senha",
            type="password",
            autocomplete="new-password",
            help=f"Mínimo de {TAMANHO_MINIMO_SENHA} caracteres.",
        )
        confirmacao = st.text_input("Confirmar a nova senha", type="password", autocomplete="new-password")
        enviado = st.form_submit_button("Definir senha e entrar", type="primary", width="stretch")
    if enviado:
        if not usuario.strip() or not codigo.strip() or not senha:
            st.error("Preencha o usuário, o código de convite e a nova senha.")
            return
        if senha != confirmacao:
            st.error("A confirmação não coincide com a nova senha.")
            return
        try:
            primeiro_acesso(usuario, codigo, senha)
            _abrir_sessao(entrar(usuario, senha))
        except ErroAPI as exc:
            st.error(str(exc))
            return
        st.rerun()


def renderizar(pode_voltar: bool) -> None:
    """Desenha a tela de acesso. `pode_voltar`: quando o login não é
    obrigatório para consultar (AUTH_EXIGIR=feedback), oferece a volta à
    consulta sem entrar."""
    tema.marca_acesso()

    aviso = st.session_state.get("aviso_acesso")
    if aviso:
        st.warning(aviso)

    aba = st.segmented_control("Tipo de acesso", _ABAS, default=_ABAS[0], label_visibility="collapsed")
    if aba == _ABAS[1]:
        _formulario_primeiro_acesso()
    else:
        _formulario_entrar()

    st.caption(
        "As perguntas e as avaliações ficam registradas e associadas ao usuário, "
        "para aprimoramento do HerpIA."
    )
    if pode_voltar and st.button("Voltar à consulta"):
        st.session_state.mostrar_acesso = False
        st.rerun()
