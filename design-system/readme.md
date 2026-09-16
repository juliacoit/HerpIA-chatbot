# HerpIA — Design System (RAN/ICMBio)

Sistema de design para o **HerpIA — Assistente Inteligente para Consulta de Informações sobre a Herpetofauna Brasileira**, chatbot interno do **RAN/ICMBio** (Centro Nacional de Pesquisa e Conservação de Répteis e Anfíbios), desenvolvido em parceria com o CNPq e intermediação do CIEE. Nome técnico do projeto: *Sistema RAG para Consulta Inteligente de Dados sobre a Herpetofauna Brasileira — RAN/ICMBio*.

## Contexto do produto

O HerpIA é um sistema **RAG** (Retrieval-Augmented Generation): recupera trechos de uma base curada, gera a resposta apenas a partir deles e **sempre cita as fontes**. Público: técnicos, gestores e pesquisadores vinculados ao RAN. Idioma do produto: **português do Brasil**.

Superfícies do produto hoje:

| Superfície | Situação no código-fonte |
| --- | --- |
| API FastAPI (`/buscar`, `/perguntar`, `/feedback`, `/saude`) | Implementada (esqueleto da Fase 6) |
| Interface do assistente (protótipo Streamlit previsto) | **Não implementada** — Fase 8 do roadmap |
| Pipelines de coleta/extração/chunking | Concluídos para Monitora, PANs e SALVE (59.080 trechos) |

Cinco fontes de dados, que aparecem como entidade visual de primeira classe neste sistema: **Monitora**, **PANs**, **SALVE**, **SEI** (acesso restrito, ainda não indexado) e **Publicações científicas do RAN**.

## Fontes deste design system

- Repositório GitHub: **https://github.com/juliacoit/chatbot-ran-icmbio** (branch `main`) — leia `README.md`, `CLAUDE.md`, `backend/` e `docs/roadmap.md` para aprofundar qualquer decisão tomada aqui.
- Documentos institucionais citados pelo repositório: Programa Monitora (gov.br/icmbio), PANs (gov.br/icmbio), SALVE (salve.icmbio.gov.br), SEI/ICMBio (acesso restrito).
- Nenhum Figma, deck, guia de marca, arquivo de fonte, CSS ou front-end foi fornecido.

### Identidade oficial aplicada (atualização)

Depois da primeira versão, foram fornecidos dois materiais oficiais, agora em `assets/`:

- `assets/ran-logo.svg` / `assets/ran-logo.png` — **assinatura oficial do RAN (ICMBio/MMA)**. Cores medidas no próprio arquivo: verde **#4B7936** e azul **#2F7FB7**.
- `assets/icmbio-manual-identidade-visual.pdf` — **Manual de Identidade Visual do ICMBio**: institucionais **#006633, #339966, #669933, #CCCC33** (p. 15), tons de cinza preto 100/80/60/30% (p. 16), tipografia institucional **DIN Alternate** (p. 14), área de reserva (p. 11), moldura branca sobre fundo sem contraste (p. 12 e 19), redução mínima (p. 13) e usos incorretos (p. 20).
- Também existe agora interface real no repositório (`interface/app.py`, `interface/tema.py`): protótipo Streamlit com cabeçalho institucional, sidebar de filtros, citações em expander e feedback útil/não útil.

**O que foi adotado da identidade:** verde RAN como cor primária de ação e marca; azul RAN como acento, link e cor da fonte Monitora; institucionais do ICMBio nos estados de resposta e no mapa de cores por fonte; tons de cinza do manual como neutros de interface; Archivo como substituta da DIN Alternate; a assinatura oficial (componente `Logo`) substituindo a marca tipográfica nos cabeçalhos, com área de reserva e moldura codificadas.

**O que foi mantido do sistema de produto** (o manual é de 2009 e não trata de interface digital): Source Sans 3 para corpo de resposta e IBM Plex Mono para dados; controles pill e cards de 14px; escala de espaçamento, sombras, foco, estados e movimento; o tom clay para erro/negativo, ausente do manual.

**Pendências:** arquivos da **DIN Alternate** (licenciada) para eliminar a substituição; versão vetorial original (AI/EPS) do logo do RAN; e a **assinatura conjunta Governo Federal / MMA / ICMBio** (anexo do manual), necessária em publicações e slides, ainda não modelada como componente.

### Aviso de origem — leia antes de usar

O repositório **não contém nenhum artefato visual**: sem logo, sem CSS, sem componentes, sem fontes, sem telas. Portanto:

1. **A base do sistema (espaçamento, forma, estados, movimento) foi autorada**, ancorada no domínio (conservação de répteis e anfíbios, órgão federal, leitura técnica longa) e no contrato real da API. Ela é uma **proposta**, não uma recriação — trate cor, tipo e forma como decisões revisáveis.
2. **A marca é a oficial do RAN**, fornecida pelo usuário e usada sem alteração (componente `Logo`). Nada foi desenhado ou reconstruído; `Wordmark` fica só para espaços pequenos.
3. **Tipografia substituída:** Archivo (no lugar da DIN Alternate institucional) + Source Sans 3 + IBM Plex Mono.
4. **Ícones substituídos:** Lucide via CDN (não há nenhum asset de ícone no repositório).

---

## FUNDAMENTOS DE CONTEÚDO

Extraídos da linguagem real do projeto (`CLAUDE.md`, `backend/services/geracao.py`, mensagens dos endpoints).

- **Idioma:** português do Brasil, sempre. Termos técnicos do domínio ficam em português (trecho, fonte, ficha de espécie, bioma, táxon); nomes de campos da API ficam como estão no código (`top_k`, `evidencia_suficiente`, `resposta_fundamentada`) e são grafados em mono.
- **Pessoa:** o sistema fala de forma impessoal ou em 3ª pessoa sobre si (“O HerpIA responde apenas com base nos documentos indexados”). Nunca “eu”, nunca “nós”. Ao usuário, trata-se por “você” apenas quando necessário; o padrão é a frase sem sujeito (“Selecione as fontes”).
- **Tom:** técnico, sóbrio, verificável. Frases declarativas curtas. Nada de entusiasmo, exclamações ou marketing.
- **Honestidade sobre limites é a regra central do produto.** Quando falta evidência, o texto diz isso literalmente: *“Não há evidência suficiente na base de conhecimento para responder a essa pergunta.”* Nunca hedge (“provavelmente”, “é possível que”) — o próprio prompt do sistema proíbe.
- **Erros nomeiam causa e ação:** *“LLM local (Ollama) indisponível: … rode 'ollama serve' e baixe o modelo com 'ollama pull …'.”*; *“PostgreSQL indisponível nesta sessão — feedback não pode ser registrado agora.”*; *“Interação 1832 não encontrada.”*
- **Fontes restritas são explicitadas:** *“A base de conhecimento ainda não tem documentos do SEI indexados (fonte de acesso restrito, pendente de exportação e autorização).”*
- **Caixa:** frase capitalizada (sentence case) em títulos, rótulos e botões — *“Buscar na base”*, *“Enviar feedback”*. Caixa alta só em rótulos de seção de 11,5px com tracking. Siglas mantêm a grafia oficial: RAN, ICMBio, SALVE, PANs, SEI, Monitora.
- **Números:** formato brasileiro — 59.080 trechos, score 0,6214, p. 44–46.
- **Emoji: nunca.** Nem em UI, nem em documentação, nem em mensagens de erro. O repositório não usa nenhum.
- **Rótulos de botão** são verbo + objeto curto: “Perguntar”, “Buscar”, “Copiar resposta”, “Enviar feedback”, “Filtrar fontes”.
- **Vibe:** caderno de campo de um órgão de pesquisa — preciso, rastreável, sem ornamento. Cada afirmação tem uma fonte ao lado.

---

## FUNDAMENTOS VISUAIS

### Cor
Primária **verde RAN `#4B7936`**, tirada da assinatura do centro; **azul RAN `#2F7FB7`** como acento, link e cor da fonte Monitora. Estados de resposta usam os institucionais do ICMBio: **`#006633`** (fundamentada/positivo), **`#CCCC33`/`#6E6E1A`** (retida/atenção), **`#8C3A2B`** clay (sem evidência/erro — único tom fora do manual), **azul RAN** (informação). Neutros são os **tons de cinza do manual** (preto 100/80/60/30% mais degraus claros de interface), com fundo de página `#F6F7F4`. Cada fonte de dados tem **cor fixa**, toda ela oficial: Monitora `#2F7FB7`, PANs `#006633`, SALVE `#669933`, SEI `#666666`, Publicações `#6E6E1A` — a cor da fonte é informação, não decoração.
Sem gradientes em nenhum lugar. Máximo de dois fundos por tela (`--surface-page` + `--surface-card`), com `--surface-tinted` (teal 50) para destaque pontual.

### Tipografia
**Archivo** (600) para títulos, rótulos e a marca — substituta livre da **DIN Alternate**, tipografia institucional do ICMBio (manual, p. 14); **Source Sans 3** para interface e corpo de resposta; **IBM Plex Mono** para score, páginas, IDs e nomes de campo. Resposta a 17/28px com medida máxima de 68 caracteres (`--measure-answer`): leitura longa é o caso de uso principal. Títulos com `-0.01em`; rótulos de seção em caixa alta com `+0.08em`.

### Espaçamento e layout
Base 4px (`--space-1` … `--space-20`). Estrutura fixa de app: barra lateral de 268px (navegação + filtro de fontes + contagem da base), conteúdo central com máximo de 820px, gutter de 24px. Campo de pergunta fixo no rodapé da tela de consulta; cabeçalho fixo no topo. Nada de layout centrado “landing page”.

### Fundos e imagens
A única peça gráfica é a **assinatura oficial do RAN**. Não há fotografias, ilustrações, padrões ou texturas — nada foi gerado. Sobre foto ou fundo escuro, a marca recebe **moldura branca** (manual, p. 12 e 19) e nunca transparência (p. 20). Fundos são cor plana. Quando houver material fotográfico real do RAN (fauna em campo), a orientação é imagem documental, natural, sem filtro nem overlay colorido; até então, a ausência é intencional, não uma lacuna a preencher com decoração.

### Forma, borda e sombra
Controles são **pill** (`--radius-pill`): botões, campos, chips, tags, switches. Cards e blocos de conteúdo: **14px**. Overlays: **20px**. Checkbox é o único elemento de canto quase reto (4px), para distinguir de radio. Bordas **hairline areia** de 1px em tudo; sombras baixíssimas — `--shadow-card` para cards em repouso, `--shadow-raised` no hover de card clicável e em toasts, `--shadow-overlay` só em modal/tooltip. Sem sombras internas, sem efeito de relevo.

### Estados
- **Hover:** escurece a cor (primário teal 800 → 900) ou aplica fundo tonal sutil (secundário/ghost → areia 100 / teal 50). Nunca muda opacidade.
- **Press:** `scale(0.985)` em botões, 80ms; cor um passo mais escura.
- **Foco:** borda teal 600 + anel `0 0 0 3px var(--teal-200)`. Nunca remova o foco visível.
- **Desabilitado:** fundo areia 200, texto areia 400, cursor `not-allowed`; não usa opacidade global em botões.
- **Selecionado:** fundo teal cheio em Tag; fundo teal 50 + texto teal 900 em item de navegação e IconButton ativo.

### Movimento
Transições curtas e retas: 140ms (`--duration-fast`) para cor/borda/sombra, 220ms para deslocamentos (thumb do switch), 360ms no máximo. Easing `cubic-bezier(0.2,0,0.2,1)` padrão e `(0.16,1,0.3,1)` para saída. **Sem bounce, sem overshoot, sem animação de entrada de página.** Todas as durações vão a zero em `prefers-reduced-motion`.

### Transparência e blur
Só em uma situação: o scrim do modal (`--overlay-scrim` teal 6% preto-esverdeado a 42% + `blur(3px)`). Não há cards translúcidos, nem glassmorphism, nem gradientes de proteção sobre imagem (não há imagens).

### Aparência de um card
Fundo branco, borda 1px areia 200, raio 14px, padding 20px, sombra quase imperceptível. Título em Spectral 18px; metadado à direita em 12,5px areia 600. Card clicável eleva a sombra e tinge a borda de teal 200 no hover — sem deslocamento vertical.

---

## ICONOGRAFIA

- O repositório **não tem nenhum asset de ícone** (sem SVG, sem sprite, sem fonte de ícone). Adotamos **Lucide 0.454.0 via CDN** — traço de 1,75px, cantos arredondados, peso compatível com o tom sóbrio do produto. **Substituição sinalizada:** se o RAN/ICMBio tiver um conjunto institucional, troque.
- Uso: sempre pelo componente `Icon` (`<Icon name="search" size="md" />`), que herda `currentColor`. Tamanhos 14 / 16 / 20 / 24px.
- Ícone acompanha rótulo na maioria dos casos; ícone sozinho só em `IconButton`, que exige `label` acessível.
- Mapeamento semântico em uso: `search` busca, `arrow-up` enviar pergunta, `sparkles` avatar do assistente, `shield-check` resposta fundamentada, `shield-alert` resposta retida, `search-x` sem evidência, `thumbs-up`/`thumbs-down` feedback, `external-link` abrir fonte, `folder-lock` SEI, `leaf` SALVE, `clipboard-list` PANs, `activity` Monitora, `book-open` publicações, `database` base indexada.
- **Emoji: nunca** na interface. Única exceção existente no produto: `page_icon="🦎"` do Streamlit (favicon). Caracteres unicode como ícone: nunca. Não desenhe ícones novos à mão.
- A marca do RAN **não é ícone** — não a reduza a um glifo, não a recorte e não a use dentro de botões.

---

## ÍNDICE

### Raiz
- `styles.css` — ponto de entrada único (só `@import`s). Consumidores linkam este arquivo.
- `thumbnail.html` — tile do sistema.
- `SKILL.md` — uso como Agent Skill.
- `github.md` — associação com o repositório de origem e último sync.

### `tokens/`
`fonts.css` (webfonts), `colors.css`, `typography.css`, `spacing.css`, `shape.css`, `motion.css`.

### `guidelines/` — cards de especimen (Design System tab)
Cores (teal, neutros, acentos semânticos, cores por fonte, estados de resposta, superfícies), Type (display, corpo, mono, rótulos), Spacing (escala, layout em uso), Shape (raios, sombras, bordas/foco), Motion.

### `components/core/` — primitivas
`Icon`, `Button`, `IconButton`, `Input`, `Textarea`, `Select`, `Checkbox`, `Radio`, `Switch`, `Card`, `Badge`, `Tag`, `Tabs`, `Tooltip`, `Dialog`, `Toast`.

### `components/brand/` — marca
`Logo` (assinatura oficial do RAN, com área de reserva e moldura).

### `components/rag/` — componentes de domínio
`SourceChip`, `CitationCard`, `ChunkResultCard`, `EvidenceBanner`, `FeedbackButtons`, `ChatMessage`, `Wordmark`.

Cada componente tem `.jsx`, `.d.ts` (contrato de props) e `.prompt.md` (quando usar + exemplo).

### `templates/consulta-herpia/` — template
`ConsultaHerpia.dc.html` — página de consulta pronta para copiar em projetos que consomem este sistema (pergunta, resposta, citações, feedback).

### `ui_kits/herpia-assistente/` — telas
`index.html` (Consulta, interativa), `busca.card.html` (Busca nos trechos), `login.card.html` (Acesso), com `AppShell.jsx`, `ConsultaScreen.jsx`, `BuscaScreen.jsx`, `LoginScreen.jsx`. Ver `ui_kits/herpia-assistente/README.md` para o mapeamento tela → código-fonte.

## Adições intencionais

Nenhuma fonte definia um inventário de componentes, então o conjunto de primitivas é o padrão do sistema. As sete adições de domínio (`SourceChip`, `CitationCard`, `ChunkResultCard`, `EvidenceBanner`, `FeedbackButtons`, `ChatMessage`, `Wordmark`) existem porque mapeiam campos concretos da API do HerpIA — sem elas, as regras de citação e de fundamentação do produto não teriam representação visual. `Wordmark` existe especificamente por não haver logo.
