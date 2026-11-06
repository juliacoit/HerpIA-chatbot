"""Tela de acesso do HerpIA: login e primeiro acesso (definição de senha
com código de convite).

Porta `design-system/ui_kits/herpia-assistente/LoginScreen.jsx`: assinatura
do RAN, aviso de acesso restrito e cartão com usuário institucional, senha e
"Entrar". O "Primeiro acesso" não existe no kit — segue a mesma composição.
Não há autocadastro nem recuperação de senha por e-mail: as contas e os
códigos de convite saem de `scripts/infra/gerenciar_usuarios.py` (ver
docs/processos/autenticacao.md).

A sessão fica em `st.session_state.sessao` (token, usuário e nome) e o token
também num cookie do navegador (`COOKIE_SESSAO`), para a sessão sobreviver ao
recarregar a página. O histórico da conversa continua só na memória da aba.
"""

import json
from datetime import datetime, timezone

import streamlit as st
import tema
from cliente_api import ErroAPI, entrar, primeiro_acesso, usuario_da_sessao

_ABAS = ["Entrar", "Primeiro acesso"]
TAMANHO_MINIMO_SENHA = 10  # mesmo valor de backend/services/auth.py, só para a dica do campo

# Cookie com o token da sessão. O Streamlit lê cookies (st.context.cookies),
# mas não os grava: a gravação é um <script> injetado com st.html. Por isso o
# cookie não pode ser HttpOnly. Mitigações: SameSite=Strict, Secure quando a
# página está em HTTPS, validade igual à da sessão no backend, e o backend
# confere o token a cada carga (um token encerrado ou expirado não volta).
COOKIE_SESSAO = "herpia_sessao"
_VALIDADE_PADRAO_S = 12 * 3600  # AUTH_SESSAO_HORAS padrão, se a resposta não trouxer expira_em


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
    _agendar_cookie(None)


def _segundos_ate(expira_em: str | None) -> int:
    try:
        fim = datetime.fromisoformat(expira_em)
    except (TypeError, ValueError):
        return _VALIDADE_PADRAO_S
    if fim.tzinfo is None:
        fim = fim.replace(tzinfo=timezone.utc)
    return max(0, int((fim - datetime.now(timezone.utc)).total_seconds()))


def _agendar_cookie(token: str | None, segundos: int = 0) -> None:
    """Pede a gravação (token) ou a remoção (None) do cookie na próxima vez
    que `sincronizar_cookie` rodar — a gravação precisa de um elemento na
    página, e quem chama esta função costuma dar st.rerun() logo depois."""
    st.session_state.cookie_pendente = {"token": token, "segundos": segundos}


def sincronizar_cookie() -> None:
    """Grava ou apaga o cookie da sessão, se houver pedido pendente. Chamar
    uma vez por execução, antes de qualquer st.stop()."""
    pendente = st.session_state.pop("cookie_pendente", None)
    if pendente is None:
        return
    nome = json.dumps(COOKIE_SESSAO)
    if pendente["token"] and pendente["segundos"] > 0:
        valor = json.dumps(pendente["token"])
        validade = int(pendente["segundos"])
    else:
        valor, validade = '""', 0
    st.html(
        "<script>(function(){"
        f"var c={nome}+'='+encodeURIComponent({valor})+'; Max-Age={validade}; Path=/; SameSite=Strict';"
        "if(location.protocol==='https:'){c+='; Secure';}"
        "document.cookie=c;})();</script>",
        unsafe_allow_javascript=True,
    )


def restaurar_sessao() -> None:
    """Se a aba ainda não tem sessão, tenta a do cookie, uma vez por carga
    da página. O backend decide se o token ainda vale (/auth/eu): sessão
    encerrada ou expirada apaga o cookie; backend fora do ar não restaura nem
    apaga. `st.context.cookies` é o que o navegador mandou ao abrir a página,
    por isso só é lido uma vez: depois de "Sair" ele ainda traz o token antigo."""
    if sessao_atual() is not None or st.session_state.get("cookie_verificado"):
        return
    st.session_state.cookie_verificado = True
    token = st.context.cookies.get(COOKIE_SESSAO)
    if not token:
        return
    try:
        usuario = usuario_da_sessao(token)
    except ErroAPI:
        return
    if usuario is None:
        _agendar_cookie(None)
        return
    st.session_state.sessao = {"token": token, "usuario": usuario["usuario"], "nome": usuario["nome"]}


def _abrir_sessao(resposta_login: dict) -> None:
    st.session_state.sessao = {
        "token": resposta_login["token"],
        "usuario": resposta_login["usuario"]["usuario"],
        "nome": resposta_login["usuario"]["nome"],
    }
    _agendar_cookie(resposta_login["token"], _segundos_ate(resposta_login.get("expira_em")))
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
