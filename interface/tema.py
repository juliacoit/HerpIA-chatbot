"""Design system do HerpIA aplicado à interface Streamlit — identidade
oficial do RAN/ICMBio.

Fonte de verdade dos tokens (`CORES`, `CORES_FONTE`, `_FONTES`): o design
system em `design-system/` (raiz do repo), decisão de 2026-09-16, gerado a
partir de dois materiais oficiais do RAN/ICMBio (`design-system/assets/`):
a assinatura do centro (`ran-logo.png` — verde #4B7936 e azul #2F7FB7) e o
Manual de Identidade Visual do ICMBio (`icmbio-manual-identidade-visual.pdf`
— institucionais #006633/#339966/#669933/#CCCC33, cinzas p. 16). Ver
`design-system/readme.md` (fundamentos completos) e
`docs/processos/design_system.md` (o que foi portado para cá e por quê).
Substitui a paleta teal/areia autorada (revisão anterior, sem material
oficial disponível — ver histórico em `docs/processos/interface_streamlit.md`).
Não reinventar cor, fonte ou raio aqui — só portar os tokens de
`design-system/tokens/`.

Aplica só o que dá para fazer dentro das restrições do Streamlit — paleta,
tipografia (Google Fonts), forma (raio/sombra), a marca oficial (logo) e a
cor dos estados de resposta. Streamlit não dá controle de layout amplo como
um site estático, então isto não tenta recriar o design system inteiro: sem
componente de "indicador de confiança" de 3 níveis (o backend só tem
`resposta_fundamentada` booleano, ver `backend/schemas.py`) e sem os ícones
Lucide do design system (exigiriam um pacote de ícones novo; os estados de
resposta seguem só com faixa de cor + rótulo textual, como antes).

Todo HTML aqui é estático, autoral — nunca interpola texto vindo do
backend/LLM. `unsafe_allow_html=True` só é seguro enquanto isso continuar
valendo (texto de resposta, citação e pergunta do usuário continuam
passando por `st.write`/`st.markdown` sem essa flag, em app.py; o chip de
cor por fonte na citação usa a sintaxe nativa `:color[...]` do Markdown do
Streamlit em vez de HTML, pelo mesmo motivo — ver `_titulo_citacao` em
app.py).
"""

import base64
import textwrap
from pathlib import Path

import streamlit as st

# Paleta oficial (design-system/tokens/colors.css é a fonte de verdade —
# só portada para Python aqui). RAN = cor medida na assinatura do centro;
# ICMBio = institucionais do manual de identidade visual (p. 15); cinzas =
# tons de cinza do manual (p. 16); clay = único tom fora do manual (o
# manual não define vermelho/erro), mantido do sistema de produto anterior.
CORES = {
    "ran_verde_900": "#2E4C22",
    "ran_verde_800": "#3C612B",
    "ran_verde": "#4B7936",
    "ran_verde_400": "#83A671",
    "ran_verde_200": "#C7DBBC",
    "ran_verde_100": "#E6EEE1",
    "ran_verde_50": "#F2F7EF",
    "ran_azul_900": "#1B4E71",
    "ran_azul_800": "#256793",
    "ran_azul": "#2F7FB7",
    "ran_azul_400": "#7FB2D6",
    "ran_azul_200": "#BCD8EC",
    "ran_azul_100": "#E4EFF7",
    "icmbio_verde_escuro": "#006633",
    "icmbio_verde": "#339966",
    "icmbio_verde_claro": "#669933",
    "icmbio_amarelo": "#CCCC33",
    "icmbio_amarelo_escuro": "#6E6E1A",
    "preto": "#000000",
    "cinza_80": "#666666",
    "cinza_60": "#999999",
    "cinza_30": "#CCCCCC",
    "cinza_15": "#E6E6E4",
    "cinza_8": "#F0F1EE",
    "cinza_4": "#F6F7F4",
    "white": "#FFFFFF",
    "ink": "#23292A",
    "clay_700": "#8C3A2B",
    "clay_500": "#B85541",
    "clay_100": "#F6E0DA",
}
CORES.update(
    {
        "text_title": CORES["ran_verde_900"],
        "text_body": CORES["ink"],
        "text_muted": CORES["cinza_80"],
        "text_subtle": CORES["cinza_60"],
        "text_link": CORES["ran_azul_800"],
        "text_link_hover": CORES["ran_azul_900"],
        "surface_page": CORES["cinza_4"],
        "surface_card": CORES["white"],
        "surface_sunken": CORES["cinza_8"],
        "surface_tinted": CORES["ran_verde_100"],
        "surface_inverse": CORES["icmbio_verde_escuro"],
        "border_hairline": CORES["cinza_15"],
        "border_strong": CORES["cinza_30"],
        "border_focus": CORES["ran_verde_800"],
        "action_primary": CORES["ran_verde"],
        "action_primary_hover": CORES["ran_verde_800"],
    }
)

# Cor fixa por fonte de dados — é informação (identifica a origem do
# trecho citado), não decoração: não reutilizar para outra finalidade.
# Todas tiradas da identidade oficial (design-system/tokens/colors.css).
CORES_FONTE = {
    "monitora": CORES["ran_azul"],
    "pans": CORES["icmbio_verde_escuro"],
    "salve": CORES["icmbio_verde_claro"],
    "sei": CORES["cinza_80"],
    "publicacoes": CORES["icmbio_amarelo_escuro"],
}

# Estados de resposta do RAG (design-system/tokens/colors.css) — cores
# institucionais do ICMBio, exceto sem_evidencia (clay, fora do manual).
CORES_ESTADO = {
    "fundamentada": {"fg": CORES["icmbio_verde_escuro"], "bg": "#E1EFE6"},
    "retida": {"fg": CORES["icmbio_amarelo_escuro"], "bg": "#F6F6DE"},
    "sem_evidencia": {"fg": CORES["clay_700"], "bg": CORES["clay_100"]},
    "info": {"fg": CORES["ran_azul_900"], "bg": CORES["ran_azul_100"]},
}

# DIN Alternate (tipografia institucional do ICMBio, manual p. 14) é
# licenciada e não está disponível — substituída por Archivo (Google
# Fonts), grotesca geométrica de proporções próximas. Source Sans 3 e IBM
# Plex Mono mantidos do sistema de produto (o manual é de 2009 e não
# cobre interface digital).
_FONTES = (
    "https://fonts.googleapis.com/css2?"
    "family=Archivo:wght@400;500;600;700"
    "&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&display=swap"
)

_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "ran-logo.png"


def _logo_base64() -> str:
    """Assinatura oficial do RAN, embutida como data URI. Usa o PNG
    colorido (`design-system/assets/ran-logo.png`, verde #4B7936 e azul
    #2F7FB7) — o SVG irmão é um traçado monocromático que perdeu as cores
    da marca (ver `design-system/components/brand/Logo.jsx`), por isso não
    é usado aqui. Data URI em vez de caminho de arquivo porque o HTML
    injetado via `st.html()` é servido para o navegador, não para o
    processo Python — um `<img src="caminho/local">` não resolveria."""
    return base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")


def _logo_html(altura: int, moldura: bool = True, reserva: bool = True) -> str:
    """Porta `design-system/components/brand/Logo.jsx` para HTML estático.
    Regras do Manual de Identidade Visual do ICMBio: área de reserva ao
    redor da marca (p. 11, aproximada aqui por padding proporcional —
    `--marca-reserva: 0.9em` do design system, desligável com
    `reserva=False` quando o container que envolve o logo já dá espaço de
    sobra — mesma opção de `Logo.jsx`, usada por
    `design-system/ui_kits/herpia-assistente/AppShell.jsx` na sidebar);
    moldura branca quando o fundo não contrasta com a marca (p. 12 e 19) —
    usada no cabeçalho porque o "RAN" do logo é verde sobre fundo também
    verde; nunca recolorir, distorcer ou aplicar transparência (p. 20).

    Não foi possível confirmar a "redução mínima" exata do manual (p. 13)
    nesta sessão — sem ferramenta de leitura de PDF por página disponível
    no ambiente (ver `docs/processos/design_system.md`). As alturas usadas
    neste módulo são uma escolha conservadora para manter "ICMBio-MMA" (o
    texto menor da assinatura) legível; revisar contra o manual se precisão
    institucional exata for necessária.
    """
    b64 = _logo_base64()
    padding_moldura = round(altura * 0.08)
    img = (
        f'<img src="data:image/png;base64,{b64}" alt="RAN — ICMBio/MMA" '
        f'style="height:{altura}px; width:auto; display:block;">'
    )
    if moldura:
        img = (
            f'<span style="display:inline-flex; background:{CORES["white"]}; '
            f'padding:{padding_moldura}px; border-radius:2px;">{img}</span>'
        )
    if reserva:
        img = f'<span style="display:inline-flex; padding:0.9em;">{img}</span>'
    return img


# Ícones do design system (design-system/readme.md, seção "Iconografia"):
# Lucide via CDN no design system original; aqui portados como SVG inline
# hand-authored (aproximação dos traçados reais do Lucide — não copiados
# byte a byte do pacote, que não foi vendorizado como asset de ícone neste
# projeto). Trocar pelos SVGs reais do Lucide (ou por um conjunto oficial
# do RAN/ICMBio, se vier a existir) é seguro a qualquer momento: só afeta
# `_ICONES`. Sempre `fill="none"`/`stroke="currentColor"`, 1,75px de
# traço, cantos arredondados — mesmos parâmetros de `components/core/Icon.jsx`.
_ICONES = {
    "shield-check": (
        '<path d="M20 13c0 5-3.5 7.5-7.35 8.95a1 1 0 0 1-1.3 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1'
        'c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "shield-alert": (
        '<path d="M20 13c0 5-3.5 7.5-7.35 8.95a1 1 0 0 1-1.3 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1'
        'c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
        '<path d="M12 8v4"/><path d="M12 16h.01"/>'
    ),
    "search-x": (
        '<circle cx="10" cy="10" r="7"/><path d="m8 8 4 4"/><path d="m12 8-4 4"/>'
        '<path d="m21 21-4.35-4.35"/>'
    ),
    "external-link": (
        '<path d="M15 3h6v6"/><path d="M10 14 21 3"/>'
        '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    ),
    "activity": (
        '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0'
        ' 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>'
    ),
    "clipboard-list": (
        '<rect x="8" y="2" width="8" height="4" rx="1"/>'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>'
    ),
    "leaf": (
        '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>'
        '<path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>'
    ),
    "folder-lock": (
        '<path d="M10 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9'
        'H20a2 2 0 0 1 2 2v3"/><rect width="8" height="5" x="14" y="17" rx="1"/>'
        '<path d="M18 17v-2a2 2 0 1 0-4 0v2"/>'
    ),
    "book-open": (
        '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 '
        '4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>'
    ),
}


def _icone(nome: str, tamanho: int = 16, cor: str = "currentColor") -> str:
    caminhos = _ICONES.get(nome, "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{tamanho}" height="{tamanho}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{cor}" stroke-width="1.75" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex:none;display:inline-block;vertical-align:middle">{caminhos}</svg>'
    )


# Nome de exibição + ícone por fonte de dados (design-system/components/rag/SourceChip.jsx).
_FONTE_META = {
    "monitora": {"label": "MONITORA", "icon": "activity"},
    "pans": {"label": "PANS", "icon": "clipboard-list"},
    "salve": {"label": "SALVE", "icon": "leaf"},
    "sei": {"label": "SEI", "icon": "folder-lock"},
    "publicacoes": {"label": "PUBLICAÇÕES", "icon": "book-open"},
}


def rotulo_fonte(fonte: str) -> str:
    """Nome de exibição de uma fonte de dados (ex.: "monitora" -> "MONITORA")."""
    return _FONTE_META.get(fonte, {"label": fonte.upper()})["label"]


def chip_fonte(fonte: str, pequeno: bool = True) -> str:
    """Porta `design-system/components/rag/SourceChip.jsx`: pill com borda
    e ícone na cor fixa da fonte de dados (`CORES_FONTE`) — identifica a
    origem de um trecho/citação à primeira vista. Retorna HTML (string);
    quem chama decide como embutir (`st.markdown(..., unsafe_allow_html=True)`
    ou concatenado dentro de outro bloco). Só usa `fonte` como chave de
    dicionário (nunca concatena a string da fonte no HTML), então é seguro
    mesmo que o valor vier do backend — sem risco de injeção.
    """
    cor = CORES_FONTE.get(fonte)
    meta = _FONTE_META.get(fonte, {"label": fonte.upper(), "icon": "file-text"})
    if not cor:
        return meta["label"]
    altura = 20 if pequeno else 24
    padding_h = 8 if pequeno else 10
    fonte_px = "11.5px" if pequeno else "12.5px"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;height:{altura}px;'
        f'padding:0 {padding_h}px;border-radius:999px;background:{CORES["white"]};'
        f'border:1px solid {cor};color:{cor};font-family:\'Source Sans 3\',sans-serif;'
        f'font-size:{fonte_px};font-weight:600;letter-spacing:0.01em;white-space:nowrap;">'
        f'{_icone(meta["icon"], 14, cor)}{meta["label"]}</span>'
    )


# Ícone + título fixo por estado de resposta (design-system/components/rag/EvidenceBanner.jsx).
_ESTADO_META = {
    "fundamentada": {"icon": "shield-check", "titulo": "Resposta fundamentada nos trechos recuperados"},
    "retida": {"icon": "shield-alert", "titulo": "Resposta retida pela verificação de fundamentação"},
    "sem_evidencia": {"icon": "search-x", "titulo": "Não há evidência suficiente na base de conhecimento"},
}


def faixa_estado(estado: str) -> None:
    """Porta `design-system/components/rag/EvidenceBanner.jsx`: faixa
    compacta com ícone + rótulo fixo, cor por estado (`CORES_ESTADO`).
    Só interpola texto autoral fixo (`_ESTADO_META`) — a `justificativa`
    (texto livre do backend, `justificativa_groundedness`) NUNCA entra
    aqui; continua renderizada à parte via `st.caption` em `app.py`, que já
    escapa/trata o texto com segurança (mesma invariante do resto deste
    módulo: HTML aqui nunca interpola texto do backend/LLM).
    """
    meta = _ESTADO_META[estado]
    cores = CORES_ESTADO[estado]
    st.markdown(
        f'<div style="display:flex;gap:12px;padding:16px;background:{cores["bg"]};border-radius:14px;">'
        f'<span style="color:{cores["fg"]};flex:none;padding-top:1px;">'
        f'{_icone(meta["icon"], 20, cores["fg"])}</span>'
        f'<div style="min-width:0;font-size:14px;font-weight:600;color:{cores["fg"]};">'
        f'{meta["titulo"]}</div></div>',
        unsafe_allow_html=True,
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
                font-family: 'Archivo', 'Helvetica Neue', Arial, sans-serif !important;
                font-weight: 600 !important;
                letter-spacing: -0.015em;
                color: {CORES["text_title"]} !important;
              }}

              code, pre,
              [data-testid="stExpander"] summary,
              [data-testid="stChatInput"] textarea {{
                font-family: 'IBM Plex Mono', monospace !important;
              }}

              a {{ color: {CORES["text_link"]}; transition: color 140ms var(--herpia-ease); }}
              a:hover {{ color: {CORES["text_link_hover"]}; }}

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

              /* Foco: nunca remover — anel verde RAN, sem exceção */
              [data-testid^="stBaseButton"]:focus-visible,
              [data-testid="stChatInputTextArea"]:focus-visible,
              a:focus-visible {{
                outline: none !important;
                border-color: {CORES["border_focus"]} !important;
                box-shadow: 0 0 0 3px {CORES["ran_verde_200"]} !important;
              }}

              /* Status do backend na sidebar (st.success/st.error, único uso
                 restante de alerta nativo — os três estados de resposta do
                 RAG usam tema.faixa_estado(), não st.info/st.warning). */
              [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {{
                background: {CORES_ESTADO["fundamentada"]["bg"]} !important;
                color: {CORES_ESTADO["fundamentada"]["fg"]} !important;
              }}
              [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{
                background: {CORES_ESTADO["sem_evidencia"]["bg"]} !important;
                color: {CORES_ESTADO["sem_evidencia"]["fg"]} !important;
              }}
              [data-testid="stAlertContainer"] svg {{ fill: currentColor !important; }}

              @media (prefers-reduced-motion: reduce) {{
                * {{ transition: none !important; animation: none !important; }}
              }}
            </style>
            """
        )
    )


def marca_sidebar() -> None:
    """Bloco de marca no topo da sidebar: a assinatura oficial do RAN (sem
    faixa colorida nem moldura — o fundo da sidebar já é branco, contraste
    suficiente com o "RAN" verde do logo) mais o nome do produto.

    Porta `design-system/ui_kits/herpia-assistente/AppShell.jsx`
    (`<Logo altura={{84}} reserva={{false}} />` no topo da sidebar): a marca
    institucional (RAN) fica só aqui, não repetida como banner no topo do
    conteúdo principal — o cabeçalho de tela em `app.py` (`st.title`) é só
    o nome da tela ("Consulta"), sem repetir a marca. Substitui a versão
    anterior desta função, que envolvia o logo numa faixa verde — não é o
    que o protótipo de referência (`design-system/ui_kits/herpia-assistente/`,
    também exportado como HTML standalone) faz; ver
    `docs/processos/design_system.md`.
    """
    template = textwrap.dedent(
        """
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:1.2rem;">
          {logo}
          <span style="font-family:'Archivo',sans-serif; font-weight:600; font-size:19px;
                       color:{cor_texto};">
            Herp<span style="color:{verde_acao}">IA</span>
          </span>
        </div>
        """
    )
    st.markdown(
        template.format(
            logo=_logo_html(56, moldura=False, reserva=False),
            cor_texto=CORES["text_title"],
            verde_acao=CORES["action_primary"],
        ),
        unsafe_allow_html=True,
    )
