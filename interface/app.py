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

# Perguntas de exemplo da tela vazia: casos do gabarito revisado pela equipe
# do RAN (A1/C3, A2, A3), que a base responde com fonte.
PERGUNTAS_EXEMPLO = [
    "Há jacarés ameaçados de extinção no Brasil?",
    "Quais são os objetivos do PAN Herpetofauna do Espinhaço?",
    "O que é o Programa Monitora do ICMBio?",
]

# Avatares do chat: ícones Material, com as cores do RAN pelo CSS de
# tema.aplicar_estilo() (os padrão do Streamlit são vermelho e laranja). A
# assinatura do RAN não serve de avatar: é vertical, e o manual do ICMBio
# proíbe cortar ou distorcer a marca.
AVATAR_USUARIO = ":material/person:"
AVATAR_HERPIA = ":material/smart_toy:"

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
    # A chave `doc-` deixa o CSS de tema.aplicar_estilo() achatar os
    # expanders de trecho dentro do cartão (sem caixa dentro de caixa).
    with st.container(border=True, key=f"doc-{chave}"):
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
                st.caption(apresentacao.nome_categoria(primeiro["secao"]))
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


def _formulario_feedback(item: dict, avaliacao: int) -> None:
    """Corpo dos dois diálogos de feedback: motivos (só no negativo),
    comentário livre e os botões. Reabre com o que já foi enviado."""
    motivos: list[str] = []
    if avaliacao == -1:
        st.caption("Motivos (opcional). Indicam o tipo de falha a medir.")
        marcados = item.get("feedback_motivos") or []
        for codigo, rotulo in apresentacao.MOTIVOS_FEEDBACK.items():
            if st.checkbox(rotulo, value=codigo in marcados, key=f"motivo-{item['id']}-{codigo}"):
                motivos.append(codigo)
    # Rótulo visível acima do campo (antes ficava oculto, com uma frase
    # cinza no lugar); o limite de caracteres o próprio campo mostra.
    comentario = st.text_area(
        "Comentário (opcional)",
        value=item.get("feedback_comentario") or "",
        placeholder="Ex.: a resposta citou o documento errado.",
        max_chars=2000,
        key=f"comentario-{item['id']}-{avaliacao}",
    )
    st.caption("Fica registrado junto da avaliação.")
    col_cancelar, col_enviar = st.columns(2)
    if col_cancelar.button("Cancelar", width="stretch"):
        st.rerun()
    if col_enviar.button("Enviar feedback", type="primary", width="stretch"):
        if _registrar_feedback(item, avaliacao, comentario.strip() or None, motivos):
            st.toast("Feedback registrado. Obrigado.")
            st.rerun()


@st.dialog("O que faltou nesta resposta?")
def _dialogo_feedback_negativo(item: dict) -> None:
    _formulario_feedback(item, -1)


@st.dialog("Comentário sobre a resposta")
def _dialogo_comentario(item: dict) -> None:
    _formulario_feedback(item, item["feedback_enviado"])


def _registrar_feedback(
    item: dict, avaliacao: int, comentario: str | None = None, motivos: list[str] | None = None
) -> bool:
    """Envia e guarda no item o que foi enviado. False = não registrou (o
    erro já foi exibido), para quem chama não confirmar o envio."""
    try:
        enviar_feedback(item["id"], avaliacao, comentario, token=acesso.token_atual(), motivos=motivos)
    except ErroSessao as exc:
        _sessao_expirou(exc)
        return False
    except ErroAPI as exc:
        st.error(str(exc))
        return False
    item["feedback_enviado"] = avaliacao
    item["feedback_comentario"] = comentario
    item["feedback_motivos"] = motivos or []
    return True


def _renderizar_resposta(item: dict, idx: int) -> None:
    tema.rotulo_autor("HerpIA")
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
        comentario = item.get("feedback_comentario")
        with st.container(horizontal=True, vertical_alignment="center"):
            st.caption(apresentacao.resumo_feedback(feedback_enviado, comentario), width="content")
            # Completar a avaliação depois do envio só existe com login: o
            # backend substitui a avaliação do mesmo usuário, e sem usuário
            # o reenvio viraria uma segunda linha (registrar_feedback).
            if acesso.sessao_atual() is not None:
                rotulo = "Editar comentário" if comentario else "Adicionar comentário"
                if st.button(rotulo, key=f"comentar-{idx}", type="tertiary"):
                    _dialogo_comentario(item)
    elif MODO_AUTH == "feedback" and acesso.sessao_atual() is None:
        # Antes: uma frase longa repetida sob cada resposta, mandando o
        # usuário procurar o botão na barra lateral. Agora o próprio botão.
        if st.button("Entrar para avaliar", key=f"entrar-{idx}", type="tertiary"):
            st.session_state.mostrar_acesso = True
            st.rerun()
    else:
        # Par de botões circulares com polegar, lado a lado com o rótulo
        # (design-system/components/rag/FeedbackButtons.jsx). O ícone e o
        # formato vêm do CSS em tema.aplicar_estilo(), que mira as chaves
        # destes botões; o rótulo textual continua sendo o nome acessível.
        with st.container(horizontal=True, vertical_alignment="center"):
            st.caption("Esta resposta foi útil?", width="content")
            if st.button("Útil", key=f"util-{idx}", help="Resposta útil"):
                if _registrar_feedback(item, 1):
                    st.toast("Feedback registrado. Obrigado.")
                    st.rerun()
            if st.button("Não útil", key=f"nao_util-{idx}", help="Resposta não útil"):
                _dialogo_feedback_negativo(item)


with st.sidebar:
    tema.marca_sidebar()

    tema.rotulo_secao("Fontes da base")
    fontes_selecionadas = []
    # O texto do rótulo fica na cor do corpo (o verde-claro do SALVE tinha
    # contraste 3,4:1 sobre o branco); a cor da fonte vai para a caixa de
    # marcação, pelo CSS de tema.aplicar_estilo(), que mira estas chaves.
    for fonte in FONTES_DISPONIVEIS:
        if st.checkbox(tema.rotulo_fonte(fonte), value=True, key=f"fonte-{fonte}"):
            fontes_selecionadas.append(fonte)
    st.checkbox(
        tema.rotulo_fonte("sei"),
        value=False,
        disabled=True,
        key="fonte-sei",
        help="Não indexado: acesso restrito (ver CLAUDE.md).",
    )
    st.caption("SEI não indexado: acesso restrito")

    top_k = st.slider(
        "Trechos por resposta",
        min_value=1,
        max_value=20,
        value=5,
        help="Quantos trechos da base são enviados ao modelo para montar cada resposta (top_k).",
    )
    st.divider()
    sessao = acesso.sessao_atual()
    if sessao is not None:
        tema.rotulo_secao("Sessão")
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
    if st.session_state.historico and st.button("Limpar conversa"):
        st.session_state.historico = []
        st.rerun()
    # Estado do backend: uma linha discreta quando está tudo certo; o alerta
    # vermelho fica só para a falha, que é quando o usuário precisa agir.
    if ESTADO_BACKEND is not None:
        tema.linha_status(f"Base conectada: {TRECHOS_INDEXADOS} trechos, atualizada a cada semestre")
    else:
        st.error("O backend não respondeu. Ver SETUP_PROJETO.md.")

st.title("Consulta")
tema.paragrafo_lead(
    f"Respostas montadas só com os {TRECHOS_INDEXADOS} trechos do Monitora, dos PANs e "
    "do SALVE, sempre com a fonte de cada informação."
)

pergunta_atual = st.chat_input("Pergunte sobre répteis e anfíbios do Brasil")
# Um clique num exemplo grava a pergunta e recarrega; ela entra aqui como se
# tivesse sido digitada.
pergunta_atual = pergunta_atual or st.session_state.pop("pergunta_exemplo", None)

if not st.session_state.historico and not pergunta_atual:
    tema.rotulo_secao("Exemplos de pergunta")
    with st.container(horizontal=True, key="exemplos"):
        for i, exemplo in enumerate(PERGUNTAS_EXEMPLO):
            if st.button(exemplo, key=f"exemplo-{i}"):
                st.session_state.pergunta_exemplo = exemplo
                st.rerun()

for idx, item in enumerate(st.session_state.historico):
    with st.chat_message("user", avatar=AVATAR_USUARIO):
        st.write(item["pergunta"])
    with st.chat_message("assistant", avatar=AVATAR_HERPIA):
        _renderizar_resposta(item, idx)

if pergunta_atual:
    with st.chat_message("user", avatar=AVATAR_USUARIO):
        st.write(pergunta_atual)
    with st.chat_message("assistant", avatar=AVATAR_HERPIA):
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
