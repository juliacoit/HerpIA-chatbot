"""Protótipo de interface do HerpIA (RAN/ICMBio) — Fase 7 do roadmap.

Chat em Streamlit consumindo o backend FastAPI (backend/main.py): pergunta em
linguagem natural, resposta com citações de fonte, feedback (útil/não útil)
por resposta. Requer o backend rodando (ver SETUP_PROJETO.md).

Layout portado de `design-system/ui_kits/herpia-assistente/ConsultaScreen.jsx`
(ver `docs/processos/design_system.md`): marca só na sidebar (`tema.marca_sidebar`),
cabeçalho de tela simples (`st.title`, sem faixa colorida), faixa de estado
(`tema.faixa_estado`) abaixo da resposta em vez de substituí-la, citações em
cartão numerado com chip de fonte em vez de expander.

Rodar:
    streamlit run interface/app.py
"""

import acesso
import apresentacao
import streamlit as st
import tema
from cliente_api import ErroAPI, ErroSessao, enviar_feedback, estado_backend, perguntar, sair

FONTES_DISPONIVEIS = ["monitora", "pans", "salve"]
TRECHOS_INDEXADOS = "59.085"  # mesmo número citado em CLAUDE.md/docs — atualizar junto se mudar

st.set_page_config(page_title="HerpIA — RAN/ICMBio", page_icon="🦎", layout="centered")
tema.aplicar_estilo()

if "historico" not in st.session_state:
    st.session_state.historico = []

# Autenticação (docs/processos/autenticacao.md). O backend diz, em /saude, o
# que exige sessão (AUTH_EXIGIR): "tudo" bloqueia a consulta inteira atrás do
# login; "feedback" deixa consultar e pede login só para avaliar; "nada" é o
# comportamento anterior, sem tela de acesso. Com o backend fora do ar não dá
# para saber — a tela segue como antes e a sidebar avisa que ele não respondeu.
ESTADO_BACKEND = estado_backend()
MODO_AUTH = ESTADO_BACKEND["auth_exigir"] if ESTADO_BACKEND else "nada"

if MODO_AUTH != "nada":
    acesso.restaurar_sessao()
acesso.sincronizar_cookie()

if (MODO_AUTH == "tudo" and acesso.sessao_atual() is None) or (
    MODO_AUTH != "nada" and st.session_state.get("mostrar_acesso")
):
    acesso.renderizar(pode_voltar=MODO_AUTH == "feedback")
    st.stop()


def _sessao_expirou(exc: ErroSessao) -> None:
    acesso.encerrar_sessao_local(aviso=str(exc))
    st.session_state.mostrar_acesso = True
    st.rerun()


def _renderizar_documento(grupo: dict, indice: int, chave: str) -> None:
    # Cartão numerado por documento (design-system/components/rag/CitationCard.jsx):
    # chip de fonte, título em negrito e link "Abrir fonte" sempre visíveis.
    # Desde 2026-11 o cartão agrupa todos os trechos do documento enviados ao
    # LLM — cada seção da ficha SALVE (ou intervalo de páginas do PDF) num
    # expander próprio. Antes era um cartão por citação, e as seções de uma
    # ficha colapsavam numa só (diagnóstico da sessão RAN de 26/10, H1).
    # O texto do chunk não faz parte do CitationCard de referência, mas
    # continua exposto (ver docs/processos/design_system.md).
    with st.container(border=True):
        col_numero, col_corpo = st.columns([1, 14], gap="small")
        with col_numero:
            st.markdown(
                f'<div style="width:22px; height:22px; border-radius:999px; margin-top:2px;'
                f'background:{tema.CORES["surface_tinted"]}; color:{tema.CORES["ran_verde_800"]};'
                f'display:flex; align-items:center; justify-content:center;'
                f'font-family:\'IBM Plex Mono\',monospace; font-size:11.5px; font-weight:700;">'
                f"{indice}</div>",
                unsafe_allow_html=True,
            )
        with col_corpo:
            st.markdown(tema.chip_fonte(grupo["fonte"]), unsafe_allow_html=True)
            st.markdown(f"**{grupo['documento']}**")
            primeiro = grupo["trechos"][0]
            if primeiro.get("pagina_inicio") and primeiro.get("secao"):
                # PDF: a "seção" é a categoria de coleta (ex.: materiais-de-apoio).
                st.caption(primeiro["secao"])
            if grupo.get("url_origem"):
                # Sem a seta "↗": design-system/readme.md (Iconografia) proíbe
                # caractere unicode como ícone. O external-link do
                # CitationCard.jsx entra pelo CSS de tema.aplicar_estilo(), que
                # mira esta chave — o href vem do backend e não pode ser
                # interpolado em HTML injetado.
                with st.container(key=f"citacao-link-{chave}"):
                    st.markdown(f"[Abrir fonte]({grupo['url_origem']})")
            for rotulo, trecho in zip(apresentacao.rotulos_trechos(grupo), grupo["trechos"]):
                texto = trecho.get("texto")
                if texto:
                    with st.expander(rotulo):
                        st.text(texto)


def _renderizar_citacoes(citacoes: list[dict], estado: str, chave: str) -> None:
    grupos = apresentacao.agrupar_citacoes(citacoes)
    if not grupos:
        return
    titulo = apresentacao.titulo_trechos(estado)
    resumo = apresentacao.resumo_citacoes(grupos)
    if titulo is None:
        st.caption(f"Citações: {resumo}")
        for i, grupo in enumerate(grupos, start=1):
            _renderizar_documento(grupo, i, chave=f"{chave}-{i}")
        return
    # Retida ou sem evidência: os trechos não sustentam uma resposta, então
    # não são "citações" — ficam recolhidos, com título que diz isso.
    with st.expander(f"{titulo} — {resumo}", expanded=False):
        for i, grupo in enumerate(grupos, start=1):
            _renderizar_documento(grupo, i, chave=f"{chave}-{i}")


@st.dialog("O que faltou nesta resposta?")
def _dialogo_feedback_negativo(item: dict) -> None:
    st.caption("O comentário é opcional e fica registrado junto da avaliação.")
    comentario = st.text_area(
        "Comentário",
        placeholder="Ex.: a resposta citou o documento errado.",
        max_chars=2000,
        label_visibility="collapsed",
    )
    st.caption("Máx. 2000 caracteres")
    col_cancelar, col_enviar = st.columns(2)
    if col_cancelar.button("Cancelar", width="stretch"):
        st.rerun()
    if col_enviar.button("Enviar feedback", type="primary", width="stretch"):
        _registrar_feedback(item, -1, comentario or None)
        st.toast("Feedback registrado. Obrigado.")
        st.rerun()


def _registrar_feedback(item: dict, avaliacao: int, comentario: str | None = None) -> None:
    try:
        enviar_feedback(item["id"], avaliacao, comentario, token=acesso.token_atual())
        item["feedback_enviado"] = avaliacao
    except ErroSessao as exc:
        _sessao_expirou(exc)
    except ErroAPI as exc:
        st.error(str(exc))


def _renderizar_resposta(item: dict, idx: int) -> None:
    st.markdown(
        f'<div style="font-family:\'Archivo\',sans-serif; font-weight:600; font-size:18px;'
        f' color:{tema.CORES["text_title"]}; margin-bottom:6px;">HerpIA</div>',
        unsafe_allow_html=True,
    )
    st.write(item["resposta"])

    estado = apresentacao.estado_resposta(item)
    tema.faixa_estado(estado)
    if estado == apresentacao.ESTADO_RETIDA:
        justificativa = item.get("justificativa_groundedness")
        if justificativa:
            st.caption(f"Motivo da retenção: {justificativa}")

    _renderizar_citacoes(item.get("citacoes") or [], estado, chave=str(idx))

    interacao_id = item.get("id")
    feedback_enviado = item.get("feedback_enviado")
    if interacao_id is None:
        st.caption("Feedback indisponível nesta sessão (PostgreSQL não conectado).")
    elif feedback_enviado is not None:
        rotulo = "positivo" if feedback_enviado == 1 else "negativo"
        st.caption(f"Feedback enviado: {rotulo}. Obrigado!")
    elif MODO_AUTH == "feedback" and acesso.sessao_atual() is None:
        st.caption("Para avaliar esta resposta, entre com o usuário institucional (botão Entrar, na barra lateral).")
    else:
        # Par de botões circulares com polegar, lado a lado com o rótulo
        # (design-system/components/rag/FeedbackButtons.jsx). O ícone e o
        # formato vêm do CSS em tema.aplicar_estilo(), que mira as chaves
        # destes botões; o rótulo textual continua sendo o nome acessível.
        with st.container(horizontal=True, vertical_alignment="center"):
            st.caption("Esta resposta foi útil?", width="content")
            if st.button("Útil", key=f"util-{idx}", help="Resposta útil"):
                _registrar_feedback(item, 1)
                st.toast("Feedback registrado. Obrigado.")
                st.rerun()
            if st.button("Não útil", key=f"nao_util-{idx}", help="Resposta não útil"):
                _dialogo_feedback_negativo(item)


with st.sidebar:
    tema.marca_sidebar()

    st.markdown(
        f'<span style="font-size:11.5px; font-weight:600; letter-spacing:0.08em;'
        f' text-transform:uppercase; color:{tema.CORES["text_subtle"]};">Fontes da base</span>',
        unsafe_allow_html=True,
    )
    fontes_selecionadas = []
    for fonte in FONTES_DISPONIVEIS:
        rotulo_chip = tema.rotulo_fonte(fonte)
        cor_chip = tema.CORES_FONTE.get(fonte)
        rotulo_md = f':color[{rotulo_chip}]{{foreground="{cor_chip}"}}' if cor_chip else rotulo_chip
        if st.checkbox(rotulo_md, value=True, key=f"fonte-{fonte}"):
            fontes_selecionadas.append(fonte)
    st.checkbox(
        f':color[{tema.rotulo_fonte("sei")}]{{foreground="{tema.CORES_FONTE["sei"]}"}}',
        value=False,
        disabled=True,
        key="fonte-sei",
        help="Não indexado — acesso restrito (ver CLAUDE.md).",
    )
    st.caption("SEI: não indexado — acesso restrito")

    top_k = st.slider("Trechos recuperados (top_k)", min_value=1, max_value=20, value=5)
    st.divider()
    sessao = acesso.sessao_atual()
    if sessao is not None:
        st.markdown(
            f'<span style="font-size:11.5px; font-weight:600; letter-spacing:0.08em;'
            f' text-transform:uppercase; color:{tema.CORES["text_subtle"]};">Sessão</span>',
            unsafe_allow_html=True,
        )
        # Nome e usuário vêm do backend: st.text, nunca HTML interpolado.
        st.text(sessao["nome"])
        st.caption(sessao["usuario"])
        if st.button("Sair"):
            sair(sessao["token"])
            acesso.encerrar_sessao_local()
            st.rerun()
        st.divider()
    elif MODO_AUTH == "feedback":
        st.caption("Consulta liberada sem login. Para avaliar respostas, é preciso entrar.")
        if st.button("Entrar"):
            st.session_state.mostrar_acesso = True
            st.rerun()
        st.divider()
    if ESTADO_BACKEND is not None:
        st.success("Backend conectado")
    else:
        st.error("Backend não respondeu — ver SETUP_PROJETO.md")
    st.divider()
    if st.button("Limpar conversa"):
        st.session_state.historico = []
        st.rerun()
    st.divider()
    st.caption(f"{TRECHOS_INDEXADOS} trechos indexados")
    st.caption("Base atualizada semestralmente")

st.title("Consulta")
st.caption(
    "Respostas geradas apenas a partir dos trechos recuperados na base de "
    "conhecimento do RAN/ICMBio (Monitora, PANs, SALVE), sempre com as fontes."
)

pergunta_atual = st.chat_input("Pergunte sobre répteis e anfíbios — ex.: quais anfíbios ameaçados ocorrem no Cerrado?")

for idx, item in enumerate(st.session_state.historico):
    with st.chat_message("user"):
        st.write(item["pergunta"])
    with st.chat_message("assistant"):
        _renderizar_resposta(item, idx)

if pergunta_atual:
    with st.chat_message("user"):
        st.write(pergunta_atual)
    with st.chat_message("assistant"):
        with st.spinner("Consultando a base de conhecimento..."):
            try:
                resultado = perguntar(
                    pergunta_atual,
                    top_k=top_k,
                    fontes=fontes_selecionadas or None,
                    token=acesso.token_atual(),
                )
            except ErroSessao as exc:
                _sessao_expirou(exc)
            except ErroAPI as exc:
                st.error(str(exc))
                resultado = None
        if resultado is not None:
            novo_item = {"pergunta": pergunta_atual, "feedback_enviado": None, **resultado}
            st.session_state.historico.append(novo_item)
            _renderizar_resposta(novo_item, len(st.session_state.historico) - 1)
