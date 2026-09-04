"""Protótipo de interface do HerpIA (RAN/ICMBio) — Fase 7 do roadmap.

Chat em Streamlit consumindo o backend FastAPI (backend/main.py): pergunta em
linguagem natural, resposta com citações de fonte, feedback (útil/não útil)
por resposta. Requer o backend rodando (ver SETUP_PROJETO.md).

Rodar:
    streamlit run interface/app.py
"""

import streamlit as st
from cliente_api import ErroAPI, enviar_feedback, perguntar, verificar_saude

FONTES_DISPONIVEIS = ["monitora", "pans", "salve"]

st.set_page_config(page_title="HerpIA — RAN/ICMBio", layout="centered")

st.title("HerpIA")
st.caption(
    "Assistente para consulta de informações sobre a herpetofauna brasileira "
    "— RAN/ICMBio. Respostas baseadas exclusivamente na base de conhecimento "
    "indexada (Monitora, PANs, SALVE), sempre com citação de fonte."
)

if "historico" not in st.session_state:
    st.session_state.historico = []


def _renderizar_citacao(citacao: dict) -> None:
    partes = [f"**[{citacao['fonte']}]** {citacao['documento']}"]
    if citacao.get("secao"):
        partes.append(f"— {citacao['secao']}")
    if citacao.get("pagina_inicio"):
        pagina = str(citacao["pagina_inicio"])
        fim = citacao.get("pagina_fim")
        if fim and fim != citacao["pagina_inicio"]:
            pagina += f"-{fim}"
        partes.append(f", p. {pagina}")
    linha = " ".join(partes)
    if citacao.get("url_origem"):
        linha += f"  \n{citacao['url_origem']}"
    st.markdown(linha)


def _registrar_feedback(item: dict, avaliacao: int) -> None:
    try:
        enviar_feedback(item["id"], avaliacao)
        item["feedback_enviado"] = avaliacao
    except ErroAPI as exc:
        st.error(str(exc))


def _renderizar_resposta(item: dict, idx: int) -> None:
    if item.get("evidencia_suficiente") is False:
        st.info(item["resposta"])
    elif item.get("resposta_fundamentada") is False:
        st.warning(item["resposta"])
        justificativa = item.get("justificativa_groundedness")
        if justificativa:
            st.caption(f"Motivo da retenção: {justificativa}")
    else:
        st.write(item["resposta"])

    citacoes = item.get("citacoes") or []
    if citacoes:
        with st.expander(f"Fontes citadas ({len(citacoes)})"):
            for citacao in citacoes:
                _renderizar_citacao(citacao)

    interacao_id = item.get("id")
    feedback_enviado = item.get("feedback_enviado")
    if interacao_id is None:
        st.caption("Feedback indisponível nesta sessão (PostgreSQL não conectado).")
    elif feedback_enviado is not None:
        rotulo = "positivo" if feedback_enviado == 1 else "negativo"
        st.caption(f"Feedback enviado: {rotulo}. Obrigado!")
    else:
        col_util, col_nao_util, _ = st.columns([1, 1, 4])
        if col_util.button("Útil", key=f"util-{idx}"):
            _registrar_feedback(item, 1)
            st.rerun()
        if col_nao_util.button("Não útil", key=f"nao_util-{idx}"):
            _registrar_feedback(item, -1)
            st.rerun()


with st.sidebar:
    st.subheader("Filtros")
    fontes_selecionadas = st.multiselect(
        "Restringir a fontes",
        FONTES_DISPONIVEIS,
        default=[],
        help="Vazio = busca em todas as fontes indexadas.",
    )
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

pergunta_atual = st.chat_input("Faça uma pergunta sobre répteis e anfíbios brasileiros...")

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
