"""Design system do HerpIA aplicado à interface Streamlit (paleta teal/areia).

Fonte de verdade dos tokens (`CORES`, `CORES_FONTE`, `_FONTES`): definidos a
partir do design system aprovado em 2026-09-16 (ver
`docs/processos/interface_streamlit.md`), que substitui o guia de identidade
visual anterior (paleta forest/amber/cream). Não reinventar cor, fonte ou
raio aqui — só portar.

Aplica só o que dá para fazer dentro das restrições do Streamlit — paleta,
tipografia (Google Fonts), forma (raio/sombra) e a cor dos estados de
resposta. Streamlit não dá controle de layout amplo como um site estático,
então isto não tenta recriar o design system inteiro: sem componente de
"indicador de confiança" de 3 níveis (o backend só tem
`resposta_fundamentada` booleano, ver `backend/schemas.py` — inventar 3
níveis na interface seria a UI afirmando uma granularidade que o sistema
não tem).

O design system é tipográfico — não define símbolo/selo (decisão registrada
em `docs/processos/interface_streamlit.md`).

Todo HTML aqui é estático, autoral — nunca interpola texto vindo do
backend/LLM. `unsafe_allow_html=True` só é seguro enquanto isso continuar
valendo (texto de resposta, citação e pergunta do usuário continuam
passando por `st.write`/`st.markdown` sem essa flag, em app.py; o chip de
cor por fonte na citação usa a sintaxe nativa `:color[...]` do Markdown do
Streamlit em vez de HTML, pelo mesmo motivo — ver `_titulo_citacao` em
app.py).
"""

import textwrap

import streamlit as st

# Base teal institucional (ação e marca) + neutros areia quentes (nunca
# cinza puro) + acentos semânticos em pares fg/bg — hex são a fonte de
# verdade do design system, não reinventar.
CORES = {
    "teal_950": "#06262E",
    "teal_900": "#0A3B47",
    "teal_800": "#0F4C5C",
    "teal_700": "#166274",
    "teal_600": "#1F7D92",
    "teal_400": "#4FA9BC",
    "teal_200": "#A7D5DF",
    "teal_100": "#D3EAF0",
    "teal_50": "#EDF6F8",
    "sand_950": "#1B1917",
    "sand_900": "#2B2825",
    "sand_800": "#413C37",
    "sand_600": "#6B645C",
    "sand_400": "#9B938A",
    "sand_300": "#C4BCB1",
    "sand_200": "#E1DBD2",
    "sand_100": "#F0ECE5",
    "sand_50": "#F8F6F2",
    "moss_700": "#2E6B45",
    "moss_100": "#DDEEE3",
    "amber_700": "#8A5A12",
    "amber_100": "#F6EBD5",
    "clay_700": "#8C3A2B",
    "clay_100": "#F6E0DA",
    "sky_700": "#1C5E8A",
    "sky_100": "#DCEBF6",
}
CORES.update(
    {
        "text_title": CORES["teal_950"],
        "text_body": CORES["sand_900"],
        "text_muted": CORES["sand_600"],
        "text_subtle": CORES["sand_400"],
        "text_link": CORES["teal_700"],
        "surface_page": CORES["sand_50"],
        "surface_card": "#FFFFFF",
        "surface_sunken": CORES["sand_100"],
        "surface_tinted": CORES["teal_50"],
        "surface_inverse": CORES["teal_900"],
        "border_hairline": CORES["sand_200"],
        "border_strong": CORES["sand_300"],
        "border_focus": CORES["teal_600"],
        "action_primary": CORES["teal_800"],
        "action_primary_hover": CORES["teal_900"],
    }
)

# Cor fixa por fonte de dados — é informação (identifica a origem do
# trecho citado), não decoração: não reutilizar para outra finalidade.
CORES_FONTE = {
    "monitora": "#1F7D92",
    "pans": "#2E6B45",
    "salve": "#8A5A12",
    "sei": "#6B645C",
    "publicacoes": "#1C5E8A",
}

_FONTES = (
    "https://fonts.googleapis.com/css2?"
    "family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,400"
    "&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&display=swap"
)


def aplicar_estilo() -> None:
    """CSS global — fontes, paleta e re-skin dos elementos padrão do
    Streamlit que dão para mirar com segurança (testids estáveis:
    `stAlertContainer`/`stAlertContent*` para os estados de resposta e do
    backend, `stBaseButton-*` para botões, `stChatMessageContent` para a
    tipografia da resposta, `stExpander` para as citações). Não tenta
    recolorir tudo; onde o seletor não bate em alguma versão do Streamlit,
    o pior caso é o estilo não aplicar, não quebra layout.
    """
    # st.html() em vez de st.markdown(unsafe_allow_html=True): no Streamlit
    # 1.63, o markdown passa a <style> pelo parser de Markdown antes da
    # sanitização HTML, então o conteúdo do bloco de CSS aparecia como
    # texto solto na página em vez de ser aplicado como estilo. st.html()
    # é a API dedicada para HTML/CSS cru (sanitizado via DOMPurify) e não
    # tem esse problema.
    st.html(
        textwrap.dedent(
            f"""
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="{_FONTES}" rel="stylesheet">
            <style>
              :root {{
                --herpia-ease: cubic-bezier(0.2,0,0.2,1);
              }}

              .stApp {{
                font-family: 'Source Sans 3', system-ui, sans-serif;
                background: {CORES["surface_page"]};
                color: {CORES["text_body"]};
              }}

              h1, h2, h3, h4,
              [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
                font-family: 'Spectral', Georgia, serif !important;
                font-weight: 600 !important;
                letter-spacing: -0.01em;
                color: {CORES["text_title"]} !important;
              }}

              code, pre,
              [data-testid="stExpander"] summary,
              [data-testid="stChatInput"] textarea {{
                font-family: 'IBM Plex Mono', monospace !important;
              }}

              a {{ color: {CORES["text_link"]}; transition: color 140ms var(--herpia-ease); }}
              a:hover {{ color: {CORES["surface_inverse"]}; }}

              /* Cards (citações): raio 14px, borda 1px — nunca sombra alta */
              [data-testid="stExpander"] {{
                border: 1px solid {CORES["border_hairline"]} !important;
                border-radius: 14px !important;
                overflow: hidden;
                box-shadow: 0 1px 2px rgba(27,25,23,.04), 0 1px 10px rgba(27,25,23,.04);
              }}

              /* Resposta principal: corpo 17/28, medida máxima 68ch */
              [data-testid="stChatMessageContent"] p {{
                font-size: 17px;
                line-height: 28px;
                max-width: 68ch;
              }}

              /* Controles são pill (999px) — botões e chat input */
              [data-testid^="stBaseButton"] {{
                border-radius: 999px !important;
                transition: background-color 140ms var(--herpia-ease),
                            border-color 140ms var(--herpia-ease),
                            box-shadow 140ms var(--herpia-ease);
              }}
              [data-testid^="stBaseButton"]:active {{ transform: scale(0.985); }}
              [data-testid^="stBaseButton-secondary"] {{
                background: {CORES["surface_card"]} !important;
                border-color: {CORES["border_strong"]} !important;
                color: {CORES["text_body"]} !important;
              }}
              [data-testid^="stBaseButton-secondary"]:hover {{
                background: {CORES["surface_sunken"]} !important;
                border-color: {CORES["text_muted"]} !important;
              }}
              [data-testid="stChatInput"] {{
                border-radius: 999px !important;
              }}

              /* Foco: nunca remover — anel teal, sem exceção */
              [data-testid^="stBaseButton"]:focus-visible,
              [data-testid="stChatInputTextArea"]:focus-visible,
              a:focus-visible {{
                outline: none !important;
                border-color: {CORES["border_focus"]} !important;
                box-shadow: 0 0 0 3px {CORES["teal_200"]} !important;
              }}

              /* Estados de resposta (evidência insuficiente / retida pela
                 verificação de fundamentação / normal) e status do backend:
                 a lógica (qual st.info/warning/success/error é chamado)
                 continua em interface/app.py, só a cor muda aqui. */
              [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {{
                background: {CORES["clay_100"]} !important;
                color: {CORES["clay_700"]} !important;
              }}
              [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {{
                background: {CORES["amber_100"]} !important;
                color: {CORES["amber_700"]} !important;
              }}
              [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {{
                background: {CORES["moss_100"]} !important;
                color: {CORES["moss_700"]} !important;
              }}
              [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{
                background: {CORES["clay_100"]} !important;
                color: {CORES["clay_700"]} !important;
              }}
              [data-testid="stAlertContainer"] svg {{ fill: currentColor !important; }}

              @media (prefers-reduced-motion: reduce) {{
                * {{ transition: none !important; animation: none !important; }}
              }}
            </style>
            """
        )
    )


def cabecalho(tagline: str) -> None:
    """Substitui st.title + st.caption — faixa institucional com wordmark
    e a mesma frase de propósito já usada no resto do projeto
    (README.md/CLAUDE.md), não um slogan novo. Sem selo: o design system
    é tipográfico, não define símbolo.
    """
    template = textwrap.dedent(
        """
        <div style="background:{faixa}; color:#FFFFFF;
                    padding:30px 32px; border-radius:14px; margin-bottom:1.6rem;">
          <div style="font-family:'Spectral',Georgia,serif; font-weight:600; font-size:32px;
                      line-height:1.1; letter-spacing:-0.01em;">
            Herp<span style="color:{teal_claro}">IA</span>
            <span style="font-family:'Source Sans 3',sans-serif; font-weight:600;
                         font-size:13.5px; letter-spacing:0.1em; color:{qualificador};
                         margin-left:10px; vertical-align:middle;">RAN/ICMBIO</span>
          </div>
          <p style="margin:8px 0 0; font-size:14.5px; max-width:56ch; color:{tagline_cor};">
            {tagline}
          </p>
        </div>
        """
    )
    st.markdown(
        template.format(
            faixa=CORES["surface_inverse"],
            teal_claro=CORES["teal_400"],
            qualificador=CORES["teal_100"],
            tagline_cor="rgba(255,255,255,0.85)",
            tagline=tagline,
        ),
        unsafe_allow_html=True,
    )


def marca_sidebar() -> None:
    """Bloco de marca no topo da sidebar — contido (não recolore a
    sidebar inteira, só este card), então os widgets abaixo continuam com
    o contraste padrão do tema claro do Streamlit. Sem selo, ver
    cabecalho()."""
    template = textwrap.dedent(
        """
        <div style="background:{faixa}; color:#FFFFFF;
                    padding:14px 16px; border-radius:14px; margin-bottom:1rem;">
          <span style="font-family:'Spectral',Georgia,serif; font-weight:600; font-size:17px;">
            Herp<span style="color:{teal_claro}">IA</span>
          </span>
        </div>
        """
    )
    st.markdown(
        template.format(
            faixa=CORES["surface_inverse"],
            teal_claro=CORES["teal_400"],
        ),
        unsafe_allow_html=True,
    )
