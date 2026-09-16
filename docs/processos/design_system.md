# Design system (`design-system/`)

- **Status:** Em produção (fonte de verdade visual para `interface/`)
- **Última atualização:** 2026-09-16
- **Responsável(eis):** Júlia Coité

## O que é

`design-system/` (raiz do repo) é um pacote de design system para o HerpIA,
gerado a partir de dois materiais oficiais do RAN/ICMBio fornecidos pela
Júlia em 2026-09-16:

- `design-system/assets/ran-logo.png` / `.svg` — a assinatura oficial do
  RAN (ICMBio/MMA). O PNG é colorido (verde `#4B7936`, azul `#2F7FB7`,
  medidos no próprio arquivo); o SVG é um traçado monocromático que perdeu
  as cores da marca, por isso **não é usado** em nenhum lugar do produto
  (ver `design-system/components/brand/Logo.jsx`) — só o PNG.
- `design-system/assets/icmbio-manual-identidade-visual.pdf` — Manual de
  Identidade Visual do ICMBio (2009): cores institucionais (p. 15), tons
  de cinza (p. 16), tipografia institucional DIN Alternate (p. 14), área
  de reserva do logo (p. 11), moldura sobre fundo sem contraste (p. 12 e
  19), redução mínima (p. 13), usos incorretos (p. 20).

Antes desses dois materiais, o produto usava uma paleta autorada sem
nenhum material oficial disponível (teal/areia — ver histórico em
[`interface_streamlit.md`](interface_streamlit.md)). O design system em
`design-system/` **substitui essa paleta** como fonte de verdade — ver
`design-system/readme.md` para os fundamentos completos (cor, tipografia,
espaçamento, forma, estados, movimento, iconografia) e
`design-system/tokens/*.css` para os valores exatos.

## Proveniência e curadoria

O pacote foi recebido como um `.zip` de ~13MB, extraído e **curado** antes
de entrar no repositório — alguns arquivos internos da ferramenta que o
gerou não fazem parte do sistema em si (não estão no índice de
`design-system/readme.md`) e foram deixados de fora para não versionar
~8MB de binários duplicados:

| Excluído | Motivo |
| --- | --- |
| `uploads/` | Cópia bruta e idêntica (mesmo hash) dos arquivos já em `assets/` — resíduo do upload original |
| `_ds_manifest.json`, `_ds_bundle.js` | Manifesto/bundle internos da ferramenta que gerou o pacote; não referenciados por `readme.md` nem por nenhum componente |
| `_adherence.oxlintrc.json` | Config de lint interna da mesma ferramenta |

Tudo o que está documentado no índice de `design-system/readme.md`
(`tokens/`, `guidelines/`, `components/`, `templates/`, `ui_kits/`,
`assets/`, `handoff/`, mais `readme.md`/`github.md`/`SKILL.md`/
`styles.css`/`thumbnail.html`) foi mantido integralmente, sem edição — é
um artefato recebido, não um documento deste repositório para editar
livremente. Correções e ressalvas ficam **aqui**, não dentro do pacote.

`design-system/SKILL.md` permite instalar este pacote como um Agent Skill
("Use this skill to generate well-branded interfaces and assets for
HerpIA"), útil para gerar mocks/protótipos rápidos e consistentes com a
marca em sessões futuras — não só para a implementação em Streamlit.

## Inconsistências conhecidas no pacote recebido

O pacote foi gerado em duas rodadas (antes e depois do logo/manual
chegarem) e nem todo arquivo foi atualizado na segunda rodada. Quando
houver conflito, **`design-system/readme.md` e `design-system/tokens/*.css`
são a autoridade** — não o texto solto em `.prompt.md` ou `SKILL.md`:

- `design-system/SKILL.md` (linha final) ainda diz "there is no logo (use
  the typographic `Wordmark`)" — desatualizado; o logo oficial existe e é
  o que `interface/tema.py` usa agora.
- `design-system/components/rag/SourceChip.prompt.md` descreve "Monitora
  teal, PANs musgo, SALVE âmbar, SEI cinza, Publicações azul" — são as
  cores da paleta teal/areia **anterior**. O mapeamento atual (e o que
  `interface/tema.py` usa) é o de `design-system/tokens/colors.css`:
  Monitora azul RAN, PANs verde-escuro ICMBio, SALVE verde-claro ICMBio,
  SEI cinza, Publicações amarelo-escuro ICMBio.
- `design-system/handoff/prompt-claude-code.md` é o prompt da rodada
  **anterior** ao logo/manual — tem uma nota no topo (revisão 2)
  explicando que só a seção de forma/espaçamento/estados/movimento
  continua válida; cor/tipografia/marca vêm de `readme.md`/`tokens/`.

## O que foi portado para `interface/`

Streamlit não consome CSS custom properties nem componentes React
diretamente — `interface/tema.py`/`app.py` **reimplementam manualmente**
os tokens e a composição relevantes em Python/HTML injetado. Ver a seção
"Identidade oficial do RAN" em
[`interface_streamlit.md`](interface_streamlit.md#identidade-oficial-do-ran-substitui-a-paleta-tealareia)
para o mapeamento completo (cor, tipografia, marca).

**2026-09-16, segunda rodada — porte estrutural, não só de cor:** a
primeira aplicação do design system (mesma data, mais cedo) só trocou
paleta/tipografia/forma, mantendo o layout antigo (faixa colorida no
cabeçalho, `st.info`/`st.warning` como faixa de estado, citações em
`st.expander`). Comparado contra o protótipo de referência — tanto
`design-system/ui_kits/herpia-assistente/` (`AppShell.jsx`,
`ConsultaScreen.jsx`) quanto o HTML standalone exportado do mesmo protótipo
(`HerpIA - Assistente (offline).html`, fora do repositório) — ficou claro
que a composição também tinha diferenças reais, não só cor. Portado nesta
rodada:

- **Marca só na sidebar** (`tema.marca_sidebar()`, sem faixa colorida) —
  o cabeçalho do conteúdo principal virou um título de tela simples
  (`st.title("Consulta")` + `st.caption(...)`), como em `TopBar` do
  `AppShell.jsx`. A versão anterior desta função envolvia o logo numa
  faixa verde que não existe na referência.
- **Ícones Lucide** (`design-system/readme.md`, seção Iconografia) —
  portados como SVG inline hand-authored em `tema._ICONES`/`tema._icone()`
  (não são os arquivos reais do pacote Lucide, que não foi vendorizado
  como asset de ícone neste projeto; são uma aproximação visual dos
  mesmos traçados). Usados no chip de fonte (`tema.chip_fonte()`, ícone
  por fonte — `activity`/`clipboard-list`/`leaf`/`folder-lock`/
  `book-open`) e na faixa de estado (`tema.faixa_estado()`, ícone
  `shield-check`/`shield-alert`/`search-x`).
- **Faixa de estado como card compacto** (`tema.faixa_estado()`, porta
  `EvidenceBanner.jsx`) abaixo da resposta, não mais `st.info`/`st.warning`
  substituindo o texto — a resposta sempre aparece como texto normal
  (`st.write`), e a faixa (ícone + rótulo fixo, cor por estado) vem depois,
  para os três estados **e** para o caso "fundamentada" (a referência
  mostra a faixa verde mesmo na resposta bem-sucedida — resolve uma
  ambiguidade que o prompt antigo deixava "opcional").
- **Citações em cartão** (`app.py._renderizar_citacao()`, porta
  `CitationCard.jsx`) em vez de `st.expander`: número, chip de fonte com
  ícone, página em mono, título em negrito, seção, link "↗ Abrir fonte" —
  tudo visível sem clicar. **Desvio deliberado da referência**: o
  `CitationCard.jsx` de origem não tem campo para o texto do chunk
  recuperado (a fixture de demonstração do protótipo não inclui esse
  campo); como isso é uma funcionalidade real e valiosa do produto atual
  (conferir a fonte exata sem sair da interface), o texto continua exposto
  aqui, só que dentro de um expander aninhado só para ele ("Ver trecho
  recuperado"), não para o cartão inteiro.
- **Filtro de fontes como checkboxes com chip colorido** (sidebar) em vez
  de `st.multiselect`, com a fonte SEI desabilitada e uma legenda "Não
  indexado — acesso restrito" — porta o padrão
  `Checkbox`+`SourceChip`+fonte desabilitada do `AppShell.jsx`.
  Estatística fixa no rodapé da sidebar ("59.080 trechos indexados",
  "Base atualizada semestralmente") — mesmo número já citado em
  `CLAUDE.md`/outros docs; não há endpoint que devolva essa contagem ao
  vivo, então não é uma chamada de API nova, é o mesmo texto estático de
  antes movido de lugar.
- **Diálogo de comentário no feedback negativo** (`app.py`,
  `st.dialog`) — porta o `Dialog` que `ConsultaScreen.jsx` abre ao clicar
  "não útil". Descoberta no processo: `POST /feedback` já aceita
  `comentario` (`backend/schemas.py`, `interface/cliente_api.py`) e nunca
  era usado pela interface — não era uma lacuna do design system, era uma
  capacidade do backend não exposta na UI. `st.toast()` confirma o envio
  (útil direto, ou depois de enviar o comentário).

**Deliberadamente não portado** (mesmo depois desta rodada):

- **Componentes React** (`design-system/components/`) e **telas**
  (`design-system/ui_kits/herpia-assistente/`, `design-system/templates/`)
  continuam sendo referência de composição/estado/copy, não código
  consumível (Streamlit não roda JSX) — cada decisão visual que fazia
  sentido em Streamlit foi reimplementada a mão.
- **Navegação por telas** ("Consulta"/"Busca nos trechos" no
  `Sidebar` do `AppShell.jsx`) — o produto atual só tem a tela de
  consulta (`POST /perguntar`); não existe uma tela para `POST /buscar`
  na interface hoje, então não há para onde navegar. Um item de nav com
  uma opção só não agregava nada.
- **Avatar customizado do assistente** (círculo verde-escuro + ícone
  `sparkles`, `ChatMessage.jsx`) — `st.chat_message("assistant")` usa o
  avatar padrão do Streamlit; trocar por uma imagem customizada é possível
  mas não foi feito nesta rodada.
- **Botão "Copiar resposta"** (`ConsultaScreen.jsx`) — Streamlit não tem
  um jeito nativo de copiar texto arbitrário para a área de transferência
  sem JavaScript customizado (`unsafe_allow_javascript`); não implementado.
- **Indicador de confiança de 3 níveis** — já não portado desde a revisão
  anterior (o backend só calcula `resposta_fundamentada` booleano).

## Limitação conhecida: "redução mínima" do logo não verificada

`design-system/components/brand/Logo.jsx` referencia a "redução mínima"
do manual (p. 13) mas não cita o valor exato, e o ambiente desta sessão
não tinha `pdftoppm`/`poppler-utils` (nem sudo interativo para instalar)
para renderizar aquela página do PDF. As alturas usadas em
`interface/tema.py` (96px no cabeçalho, 56px na sidebar) são uma escolha
conservadora para manter o texto "ICMBio-MMA" da assinatura legível, não
um valor confirmado contra o manual. Reconferir
`design-system/assets/icmbio-manual-identidade-visual.pdf`, página 13, se
precisão institucional exata (ex.: para material impresso ou slides
oficiais) for necessária.

## Pendências (herdadas do pacote recebido)

Do próprio `design-system/readme.md`, seção "O que foi adotado":

- Arquivos da **DIN Alternate** (fonte licenciada) para eliminar a
  substituição por Archivo.
- Versão vetorial original (AI/EPS) do logo do RAN — hoje só há
  PNG (colorido) e SVG (monocromático, não usado).
- A **assinatura conjunta Governo Federal / MMA / ICMBio** (anexo do
  manual), necessária em publicações e slides oficiais — ainda não
  modelada como componente.

## Observações sobre dados sensíveis

Nenhum arquivo em `design-system/` é sensível: o logo e o manual de
identidade visual são materiais institucionais públicos do RAN/ICMBio, não
dados de espécies, localização ou processos administrativos. Não se
aplicam as regras de `04_documentos_pendentes_avaliacao/`/
`05_documentos_sensiveis_nao_indexar/` (CLAUDE.md) — esta pasta não é uma
fonte de dados do pipeline RAG, é um artefato de marca/design.
