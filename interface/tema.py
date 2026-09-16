"""Identidade visual do HerpIA aplicada à interface Streamlit.

Aplica só o que dá para fazer dentro das restrições do Streamlit — paleta,
tipografia (Google Fonts) e o selo/wordmark — a partir do guia de
identidade visual (fonte de verdade dos hex e do conceito; não reinventar
cor ou fonte aqui, só portar). Streamlit não dá controle de layout amplo
como um site estático, então isto não tenta recriar o guia inteiro: sem
componente de "indicador de confiança" de 3 níveis (o backend só tem
`resposta_fundamentada` booleano, ver `backend/schemas.py` — inventar 3
níveis na interface seria a UI afirmando uma granularidade que o sistema
não tem) e sem card de citação em CSV (o formato real é documento/página/
URL, já é o que `app.py` exibe).

Todo HTML aqui é estático, autoral — nunca interpola texto vindo do
backend/LLM/chunks. `unsafe_allow_html=True` só é seguro enquanto isso
continuar valendo (texto de resposta, citação e pergunta do usuário
continuam passando por `st.write`/`st.markdown` sem essa flag, em app.py).
"""

import textwrap

import streamlit as st

# Mesmos hex do guia de identidade — fonte de verdade dos tokens de marca.
CORES = {
    "forest": "#1F4A3D",
    "forest_dark": "#14332A",
    "amber": "#B8862F",
    "teal": "#2C6E8E",
    "cream": "#EDE6D3",
    "ink": "#23292A",
    "border": "#D9D1B8",
}

_FONTES = (
    "https://fonts.googleapis.com/css2?"
    "family=Newsreader:ital,wght@0,400;0,500;0,600;1,400;1,500"
    "&family=IBM+Plex+Sans:wght@400;500;600;700"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&display=swap"
)

# Selo do guia de identidade — mesmo símbolo (ficha de campo + lagartixa),
# só o essencial para o tamanho pequeno usado aqui.
_SELO_SVG = """
<svg viewBox="0 0 200 200" width="{tamanho}" height="{tamanho}" style="color:{cor};flex:none">
  <circle cx="100" cy="100" r="90" fill="none" stroke="currentColor" stroke-width="2.5"/>
  <circle cx="100" cy="100" r="82" fill="none" stroke="currentColor" stroke-width="1"/>
  <path fill="currentColor" d="M30,100 L38,90 L55,94 L75,86 L100,83 L122,88 L140,94 L160,97 L185,100 L160,103 L140,106 L122,112 L100,117 L75,114 L55,106 L38,110 Z"/>
  <g stroke="currentColor" stroke-width="4" stroke-linecap="round" fill="none">
    <path d="M70,88 L58,74 L54,68"/><path d="M70,113 L60,126 L57,132"/>
    <path d="M118,89 L128,76 L132,70"/><path d="M118,111 L128,124 L132,130"/>
  </g>
  <circle cx="40" cy="93" r="2.8" fill="#2C6E8E"/>
</svg>
"""


def _selo(tamanho: int, cor: str) -> str:
    return _SELO_SVG.format(tamanho=tamanho, cor=cor).strip()


def aplicar_estilo() -> None:
    """CSS global — fontes e re-skin dos elementos padrão do Streamlit que
    dão para mirar com segurança (containers/testids estáveis). Não tenta
    recolorir tudo; onde a seletor não bate em alguma versão do Streamlit,
    o pior caso é a fonte não trocar, não quebra layout.
    """
    st.markdown(
        textwrap.dedent(
            f"""
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="{_FONTES}" rel="stylesheet">
            <style>
              .stApp {{ font-family: 'IBM Plex Sans', sans-serif; }}
              h1, h2, h3, h4,
              [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
                font-family: 'Newsreader', Georgia, serif !important;
                font-weight: 500 !important;
              }}
              code, pre,
              [data-testid="stExpander"] summary,
              [data-testid="stChatInput"] textarea {{
                font-family: 'IBM Plex Mono', monospace !important;
              }}
              a {{ color: {CORES["teal"]}; }}
              [data-testid="stExpander"] {{
                border-color: {CORES["border"]} !important;
              }}
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def cabecalho(tagline: str) -> None:
    """Substitui st.title + st.caption — faixa institucional com selo,
    wordmark e a mesma frase de propósito já usada no resto do projeto
    (README.md/CLAUDE.md), não um slogan novo.
    """
    # Dedenta o esqueleto ANTES de inserir o selo (SVG multilinha, sem
    # indentação própria) — dedentar depois da interpolação não funciona:
    # as linhas do SVG (indentação 0) reduziriam a zero a indentação comum
    # calculada pelo textwrap.dedent, deixando as linhas do <div> externo
    # com espaços de sobra (>=4), o que o Markdown do Streamlit interpreta
    # como bloco de código em vez de HTML cru.
    template = textwrap.dedent(
        """
        <div style="background:{forest_dark}; color:{cream};
                    padding:30px 32px; border-radius:4px; margin-bottom:1.6rem;
                    display:flex; align-items:center; gap:20px;">
          {selo}
          <div>
            <div style="font-family:'Newsreader',serif; font-weight:500; font-size:32px; line-height:1.1;">
              Herp<span style="color:{teal}">IA</span>
            </div>
            <p style="margin:8px 0 0; font-size:14.5px; max-width:56ch; color:rgba(237,230,211,0.85);">
              {tagline}
            </p>
          </div>
        </div>
        """
    )
    st.markdown(
        template.format(
            forest_dark=CORES["forest_dark"],
            cream=CORES["cream"],
            teal=CORES["teal"],
            selo=_selo(56, CORES["cream"]),
            tagline=tagline,
        ),
        unsafe_allow_html=True,
    )


def marca_sidebar() -> None:
    """Bloco de marca no topo da sidebar — contido (não recolore a
    sidebar inteira, só este card), então os widgets abaixo continuam com
    o contraste padrão do tema claro do Streamlit."""
    # Ver comentário em cabecalho() sobre a ordem dedent → interpolação.
    template = textwrap.dedent(
        """
        <div style="background:{forest_dark}; color:{cream};
                    padding:14px 16px; border-radius:4px; margin-bottom:1rem;
                    display:flex; align-items:center; gap:10px;">
          {selo}
          <span style="font-family:'Newsreader',serif; font-size:17px;">
            Herp<span style="color:{teal}">IA</span>
          </span>
        </div>
        """
    )
    st.markdown(
        template.format(
            forest_dark=CORES["forest_dark"],
            cream=CORES["cream"],
            teal=CORES["teal"],
            selo=_selo(30, CORES["cream"]),
        ),
        unsafe_allow_html=True,
    )
