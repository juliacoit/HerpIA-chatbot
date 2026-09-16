"""Protótipo de interface do HerpIA (RAN/ICMBio) — Fase 7 do roadmap.

Chat em Streamlit consumindo o backend FastAPI (backend/main.py): pergunta em
linguagem natural, resposta com citações de fonte, feedback (útil/não útil)
por resposta. Requer o backend rodando (ver SETUP_PROJETO.md).

Rodar:
    streamlit run interface/app.py
"""

import streamlit as st
import tema
from cliente_api import ErroAPI, enviar_feedback, perguntar, verificar_saude

FONTES_DISPONIVEIS = ["monitora", "pans", "salve"]

_ROTULO_FONTE = {
    "monitora": "MONITORA",
    "pans": "PANS",
    "salve": "SALVE",
    "sei": "SEI",
    "publicacoes": "PUBLICAÇÕES",
}

st.set_page_config(page_title="HerpIA — RAN/ICMBio", page_icon="🦎", layout="centered")
tema.aplicar_estilo()

tema.cabecalho(
    "Assistente para consulta de informações sobre a herpetofauna brasileira "
    "— RAN/ICMBio. Respostas baseadas exclusivamente na base de conhecimento "
    "indexada (Monitora, PANs, SALVE), sempre com citação de fonte."
)

if "historico" not in st.session_state:
    st.session_state.historico = []


def _chip_fonte(fonte: str) -> str:
    # Cor fixa por fonte de dados (tema.CORES_FONTE) como prefixo colorido
    # do título da citação, para identificar a origem à primeira vista.
    # st.expander só aceita um subconjunto de Markdown (não
    # unsafe_allow_html), então usa a sintaxe nativa de cor custom do
    # Streamlit (":color[...]{foreground=...}") em vez de HTML — sem
    # interpolar HTML do backend, mantendo a invariante de segurança
    # documentada em tema.py.
    cor = tema.CORES_FONTE.get(fonte)
    rotulo = _ROTULO_FONTE.get(fonte, fonte.upper())
    if not cor:
        return f"[{rotulo}]"
    return f'**:color[{rotulo}]{{foreground="{cor}"}}**'


def _titulo_citacao(citacao: dict) -> str:
    partes = [f"{_chip_fonte(citacao['fonte'])} {citacao['documento']}"]
    if citacao.get("secao"):
        partes.append(f"— {citacao['secao']}")
    if citacao.get("pagina_inicio"):
        pagina = str(citacao["pagina_inicio"])
        fim = citacao.get("pagina_fim")
        if fim and fim != citacao["pagina_inicio"]:
            pagina += f"-{fim}"
        partes.append(f", p. {pagina}")
    return " ".join(partes)


def _renderizar_citacao(citacao: dict) -> None:
    # Um expander por citação (em vez de uma lista dentro de um expander só)
    # porque o Streamlit não permite expander aninhado — e assim cada trecho
    # recuperado fica colapsado por padrão, sem poluir a resposta.
    with st.expander(_titulo_citacao(citacao), expanded=False):
        if citacao.get("url_origem"):
            st.markdown(citacao["url_origem"])
        texto = citacao.get("texto")
        if texto:
            st.text(texto)
        else:
            st.caption("Texto do trecho não disponível.")


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
        st.caption(f"Fontes citadas ({len(citacoes)}) — clique para ver o trecho recuperado:")
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
    tema.marca_sidebar()
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
