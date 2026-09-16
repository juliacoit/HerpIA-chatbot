# Prompt para o Claude Code — aplicar o design system HerpIA no repositório

> **Nota (revisão 2):** este prompt foi escrito antes de eu receber o logo do RAN e o Manual de Identidade Visual do ICMBio. O design system já foi atualizado para a identidade oficial (verde RAN #4B7936, azul RAN #2F7FB7, institucionais #006633/#339966/#669933/#CCCC33, cinzas do manual, Archivo no lugar da DIN Alternate, assinatura oficial no lugar do wordmark). **Use as seções abaixo apenas para forma, espaçamento, estados e movimento; para cor, tipografia e marca, siga `readme.md` e `tokens/` deste design system, não os hex teal citados adiante.**

Copie tudo abaixo da linha e cole no Claude Code aberto em `chatbot-ran-icmbio`.

---

Quero substituir a identidade visual atual da interface (`interface/tema.py`, `.streamlit/config.toml` e o que depender delas) por um design system novo, definido abaixo. **Esses valores passam a ser a fonte de verdade** — substituem a paleta e as fontes que estão hoje em `interface/tema.py` (`CORES`, `_FONTES`) e no tema do Streamlit. Não reinvente cor, fonte ou raio: porte exatamente o que está aqui.

## 1. Paleta (substitui o dict `CORES`)

Base teal institucional (ação e marca):

```
teal_950  #06262E
teal_900  #0A3B47
teal_800  #0F4C5C   <- primária (ação, marca)
teal_700  #166274
teal_600  #1F7D92
teal_400  #4FA9BC
teal_200  #A7D5DF
teal_100  #D3EAF0
teal_50   #EDF6F8
```

Neutros areia quentes (nunca cinza puro):

```
sand_950 #1B1917   sand_900 #2B2825   sand_800 #413C37
sand_600 #6B645C   sand_400 #9B938A   sand_300 #C4BCB1
sand_200 #E1DBD2   sand_100 #F0ECE5   sand_50  #F8F6F2
```

Acentos semânticos (fg/bg em pares):

```
moss_700  #2E6B45   moss_100  #DDEEE3    -> resposta fundamentada / sucesso / feedback positivo
amber_700 #8A5A12   amber_100 #F6EBD5    -> resposta retida (groundedness reprovou) / atenção
clay_700  #8C3A2B   clay_100  #F6E0DA    -> sem evidência / erro / feedback negativo
sky_700   #1C5E8A   sky_100   #DCEBF6    -> informação neutra
```

Aliases obrigatórios:

```
text_title   = teal_950     surface_page    = sand_50
text_body    = sand_900     surface_card    = #FFFFFF
text_muted   = sand_600     surface_sunken  = sand_100
text_subtle  = sand_400     surface_tinted  = teal_50
text_link    = teal_700     surface_inverse = teal_900
border_hairline = sand_200  border_strong = sand_300  border_focus = teal_600
action_primary = teal_800   action_primary_hover = teal_900
```

**Cor fixa por fonte de dados** (a cor é informação, não decoração — não reutilize para outra finalidade):

```
monitora    #1F7D92
pans        #2E6B45
salve       #8A5A12
sei         #6B645C
publicacoes #1C5E8A
```

## 2. Tipografia (substitui `_FONTES`)

Google Fonts, um único link:

```
https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap
```

- **Spectral 600** — títulos (`h1..h4`), nome de documento, wordmark. Fallback `Georgia, serif`. Títulos com `letter-spacing:-0.01em`.
- **Source Sans 3** — corpo, interface, microcópia. Fallback `system-ui, sans-serif`.
- **IBM Plex Mono 400/500** — score, páginas, IDs, nomes de campo da API, `code/pre`, `summary` de expander, textarea do chat input.

Escala: display 40/46 · h1 30/36 · h2 23/30 · h3 18/24 · corpo 16/26 · **texto de resposta 17/28 com medida máxima de 68 caracteres** · small 14/21 · caption 12,5/18 · rótulo de seção 11,5px 600 caixa alta `letter-spacing:0.08em`.

## 3. Forma, sombra, espaçamento, movimento

- Raios: **controles são pill (999px)** — botões, campos, chips, tags, switch. **Cards e blocos: 14px.** Overlays/modais: 20px. Checkbox: 4px (único canto quase reto). *Isto substitui o `border-radius:4px` usado hoje no cabeçalho e no card da sidebar: a faixa institucional passa a 14px.*
- Bordas: 1px `border_hairline`; borda forte só em campo/controle desabilitado ou divisor enfático.
- Sombras (baixíssimas, nunca relevo):
  - card: `0 1px 2px rgba(27,25,23,.04), 0 1px 10px rgba(27,25,23,.04)`
  - elevado/toast: `0 2px 4px rgba(27,25,23,.05), 0 8px 24px rgba(27,25,23,.07)`
  - overlay: `0 12px 40px rgba(6,38,46,.18)`
- Espaçamento base 4px: 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 64 · 80.
- Layout: conteúdo centrado com máximo de 820px; sidebar 268px; gutter 24px.
- Movimento: 140ms para cor/borda/sombra, 220ms para deslocamento, 360ms máximo. Easing `cubic-bezier(0.2,0,0.2,1)` (padrão) e `cubic-bezier(0.16,1,0.3,1)` (saída). **Sem bounce, sem overshoot, sem animação de entrada.** Zerar tudo em `prefers-reduced-motion`.
- Estados: hover escurece a cor (teal 800 → 900) ou aplica fundo tonal (`sand_100` / `teal_50`) — **nunca muda opacidade**; press `scale(0.985)` em 80ms; foco = borda `teal_600` + anel `0 0 0 3px #A7D5DF` (nunca remover foco visível); desabilitado = fundo `sand_200`, texto `sand_400`.
- **Sem gradientes, sem glassmorphism, sem texturas.** Transparência/blur só no scrim de modal: `rgba(6,38,46,0.42)` + `blur(3px)`.

## 4. Marca

- Wordmark tipográfico: **"HerpIA"** em Spectral 600 (`letter-spacing:-0.01em`), seguido do qualificador **"RAN/ICMBIO"** em Source Sans 3 600, caixa alta, `letter-spacing:0.1em`, ~42% do tamanho do wordmark, em `text_muted`.
- Faixa institucional do cabeçalho: fundo `teal_900`, texto `#FFFFFF`/`teal_50`, padding `30px 32px`, raio **14px**, gap 20px; tagline 14,5px, máximo 56 caracteres por linha, em branco a 85%.
- **Decisão a confirmar comigo:** este design system é tipográfico e não define símbolo. O selo atual (`_SELO_SVG`) é do guia antigo. Duas opções — **não escolha sozinho, me pergunte**: (a) manter o selo, recolorido em `cream`→branco/`teal_50` sobre a faixa `teal_900`, com o dot em `teal_600`; (b) remover o selo e deixar só o wordmark. Se eu não responder, mantenha o selo e siga.
- Não crie nenhum outro símbolo, ícone de marca ou ilustração.

## 5. Mapeamento dos estados de resposta (não mudar a lógica, só a cor)

Mantenha exatamente a lógica atual de `_renderizar_resposta` em `interface/app.py`; só troque a aparência:

| Condição da API | Tratamento visual |
| --- | --- |
| `evidencia_suficiente is False` | faixa `clay_100` / texto `clay_700`, ícone/rótulo "Sem evidência suficiente" |
| `resposta_fundamentada is False` | faixa `amber_100` / texto `amber_700`, rótulo "Resposta retida pela verificação de fundamentação" + `justificativa_groundedness` em 12,5px logo abaixo |
| caso normal | resposta em Source Sans 17/28, medida 68ch, sem faixa; opcionalmente faixa `moss_100`/`moss_700` "Resposta fundamentada nos trechos recuperados" |
| backend conectado / erro de backend | `moss_100`/`moss_700` e `clay_100`/`clay_700` |

Citações: cada uma continua em expander colapsado. No título use a **cor fixa da fonte** como chip (borda 1px + texto na cor da fonte, pill, 12,5px 600) antes do nome do documento; página e score em IBM Plex Mono 13px `text_muted`; `url_origem` como link em `text_link`. O texto do chunk (`citacao["texto"]`) continua em `st.text` (mono).

Feedback: mantenha os botões "Útil" / "Não útil" e as mensagens atuais; estilo pill, secundário (branco + borda `sand_300`), e após envio o estado positivo usa `moss_100`/`moss_700`, o negativo `clay_100`/`clay_700`.

## 6. Arquivos a alterar

1. **`interface/tema.py`** — substituir `CORES` e `_FONTES` pelos valores acima; ajustar `aplicar_estilo()` para: fonte de corpo Source Sans 3, títulos Spectral 600, mono IBM Plex Mono nos mesmos seletores de hoje, link em `teal_700`, borda de expander em `sand_200`, fundo do app em `sand_50`, raio 14px nos cards de marca, foco com anel teal. Manter a arquitetura atual (HTML estático autoral, `unsafe_allow_html` só para HTML que **nunca** interpola texto do backend/LLM — essa regra continua valendo integralmente).
2. **`.streamlit/config.toml`** — `primaryColor="#0F4C5C"`, `backgroundColor="#F8F6F2"`, `secondaryBackgroundColor="#FFFFFF"`, `textColor="#2B2825"`, `font="sans serif"`; atualizar o comentário do topo, que hoje diz "Paleta do guia de identidade visual do HerpIA".
3. **`docs/processos/interface_streamlit.md`** — atualizar a seção "Identidade visual": trocar a referência ao artifact "HerpIA — Guia de Identidade Visual" pela nova fonte de verdade (este design system: paleta teal/areia, Spectral + Source Sans 3 + IBM Plex Mono, controles pill, cards 14px), registrando que a paleta forest/amber/cream anterior foi descontinuada e por quê.
4. **`docs/roadmap.md`** — na linha da Fase 7, trocar "identidade visual do guia (interface/tema.py) aplicada" pela menção ao novo design system, com a data da mudança.
5. Não altere `backend/`, `scripts/` nem qualquer regra de dados sensíveis. Nenhuma mudança de comportamento: só aparência e documentação.

## 7. Restrições de conteúdo (mantêm o que o projeto já faz)

- Português do Brasil, tom técnico e sóbrio, frases declarativas curtas, sentence case em títulos e botões.
- Sistema fala de si em 3ª pessoa ("O HerpIA responde apenas com base nos documentos indexados"); nunca "eu"/"nós".
- Honestidade sobre limites é regra: manter as mensagens literais de falta de evidência e de SEI não indexado, sem hedge.
- Números em formato brasileiro: 59.080 trechos, score 0,6214, p. 44–46.
- Siglas com grafia oficial: RAN, ICMBio, SALVE, PANs, SEI, Monitora.
- **Sem emoji na interface.** Se mantiver o `page_icon="🦎"` do `st.set_page_config`, é a única exceção tolerada (favicon) — me avise ao decidir.

## 8. Entrega

Ao final, mostre: o diff de `interface/tema.py` e `.streamlit/config.toml`, um resumo do que mudou na documentação, e rode `streamlit run interface/app.py` descrevendo o que aparece (cabeçalho, sidebar, uma resposta com citações, os três estados de faixa). Pergunte antes de qualquer decisão que não esteja definida acima.
