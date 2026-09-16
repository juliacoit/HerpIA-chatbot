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

import streamlit as st
import tema
from cliente_api import ErroAPI, enviar_feedback, perguntar, verificar_saude

FONTES_DISPONIVEIS = ["monitora", "pans", "salve"]
TRECHOS_INDEXADOS = "59.080"  # mesmo número citado em CLAUDE.md/docs — atualizar junto se mudar

st.set_page_config(page_title="HerpIA — RAN/ICMBio", page_icon="🦎", layout="centered")
tema.aplicar_estilo()

if "historico" not in st.session_state:
    st.session_state.historico = []


def _pagina_str(citacao: dict) -> str | None:
    inicio = citacao.get("pagina_inicio")
    if not inicio:
        return None
    fim = citacao.get("pagina_fim")
    if fim and fim != inicio:
        return f"p. {inicio}–{fim}"
    return f"p. {inicio}"


def _renderizar_citacao(citacao: dict, indice: int) -> None:
    # Cartão numerado (design-system/components/rag/CitationCard.jsx) em vez
    # de expander: metadado (chip de fonte, página) sempre visível, título
    # em negrito, link "Abrir fonte". O texto do chunk (citacao["texto"])
    # não faz parte do CitationCard de referência, mas continua exposto
    # aqui — é o que permite conferir a fonte exata sem sair da interface
    # (ver docs/processos/interface_streamlit.md) — dentro de um expander
    # aninhado só para esse trecho, não para o cartão inteiro.
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
            linha_meta = tema.chip_fonte(citacao["fonte"])
            pagina = _pagina_str(citacao)
            if pagina:
                linha_meta += (
                    f'<span style="font-family:\'IBM Plex Mono\',monospace; font-size:13px;'
                    f' color:{tema.CORES["text_muted"]}; margin-left:8px;">{pagina}</span>'
                )
            st.markdown(linha_meta, unsafe_allow_html=True)
            st.markdown(f"**{citacao['documento']}**")
            if citacao.get("secao"):
                st.caption(citacao["secao"])
            if citacao.get("url_origem"):
                st.markdown(f"[↗ Abrir fonte]({citacao['url_origem']})")
            texto = citacao.get("texto")
            if texto:
                with st.expander("Ver trecho recuperado"):
                    st.text(texto)


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
        enviar_feedback(item["id"], avaliacao, comentario)
        item["feedback_enviado"] = avaliacao
    except ErroAPI as exc:
        st.error(str(exc))


def _renderizar_resposta(item: dict, idx: int) -> None:
    st.markdown(
        f'<div style="font-family:\'Archivo\',sans-serif; font-weight:600; font-size:18px;'
        f' color:{tema.CORES["text_title"]}; margin-bottom:6px;">HerpIA</div>',
        unsafe_allow_html=True,
    )
    st.write(item["resposta"])

    if item.get("evidencia_suficiente") is False:
        tema.faixa_estado("sem_evidencia")
    elif item.get("resposta_fundamentada") is False:
        tema.faixa_estado("retida")
        justificativa = item.get("justificativa_groundedness")
        if justificativa:
            st.caption(f"Motivo da retenção: {justificativa}")
    else:
        tema.faixa_estado("fundamentada")

    citacoes = item.get("citacoes") or []
    if citacoes:
        st.caption(f"Citações ({len(citacoes)})")
        for i, citacao in enumerate(citacoes, start=1):
            _renderizar_citacao(citacao, i)

    interacao_id = item.get("id")
    feedback_enviado = item.get("feedback_enviado")
    if interacao_id is None:
        st.caption("Feedback indisponível nesta sessão (PostgreSQL não conectado).")
    elif feedback_enviado is not None:
        rotulo = "positivo" if feedback_enviado == 1 else "negativo"
        st.caption(f"Feedback enviado: {rotulo}. Obrigado!")
    else:
        col_legenda, col_util, col_nao_util, _ = st.columns([3, 1, 1, 3])
        col_legenda.caption("Esta resposta foi útil?")
        if col_util.button("Útil", key=f"util-{idx}"):
            _registrar_feedback(item, 1)
            st.toast("Feedback registrado. Obrigado.")
            st.rerun()
        if col_nao_util.button("Não útil", key=f"nao_util-{idx}"):
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
    if verificar_saude():
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
                resultado = perguntar(pergunta_atual, top_k=top_k, fontes=fontes_selecionadas or None)
            except ErroAPI as exc:
                st.error(str(exc))
                resultado = None
        if resultado is not None:
            novo_item = {"pergunta": pergunta_atual, "feedback_enviado": None, **resultado}
            st.session_state.historico.append(novo_item)
            _renderizar_resposta(novo_item, len(st.session_state.historico) - 1)
