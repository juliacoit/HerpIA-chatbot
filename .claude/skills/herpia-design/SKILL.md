---
name: herpia-design
description: Use ao criar, implementar ou revisar qualquer interface, tela, mock ou material visual do HerpIA (RAN/ICMBio) — cor, tipografia, marca, componentes, espaçamento, estados de resposta, cor por fonte de dados ou copy de interface. Envolve o design system em `design-system/` e corrige as instruções desatualizadas do pacote.
---

# HerpIA — Design System (wrapper)

Esta skill **não contém** o design system. Ela aponta para o pacote que já está
no repositório, em `design-system/`, e registra as correções que não podem ser
feitas dentro dele.

Todos os caminhos abaixo são relativos à **raiz do repositório**
(`chatbot-ran-icmbio/`), não a este arquivo.

## Regra primeira: `design-system/` é imutável

É um artefato recebido (gerado no Claude Design a partir do contexto deste
repositório, 2026-09-16), curado e versionado como veio. **Nunca edite, mova,
renomeie ou "corrija" nada lá dentro** — nem os textos desatualizados listados
mais abaixo. Correções, ressalvas e decisões de porte ficam fora do pacote:
nesta skill e em `docs/processos/design_system.md`.

## Por onde começar

| Preciso de… | Leia |
| --- | --- |
| Regras de uso, fundamentos visuais e de conteúdo | `design-system/readme.md` — **minúsculo**, não `README.md` (o sistema de arquivos é case-sensitive) |
| Valores de token (cor, tipo, espaço, forma, movimento) | `design-system/tokens/*.css` |
| Ponto de entrada CSS | `design-system/styles.css` (só `@import`s dos 6 arquivos de token) |
| Contrato de props de um componente | `design-system/components/<grupo>/<Nome>.d.ts` |
| Quando/como usar um componente | `design-system/components/<grupo>/<Nome>.prompt.md` (ver ressalvas) |
| Especímenes visuais (cor, tipo, espaço, forma, movimento) | `design-system/guidelines/*.card.html` — 16 cards HTML autônomos |
| Composição de tela de referência | `design-system/ui_kits/herpia-assistente/` (`AppShell.jsx`, `ConsultaScreen.jsx`, `BuscaScreen.jsx`, `LoginScreen.jsx`, `README.md`) |
| Marca oficial | `design-system/assets/ran-logo.png` (colorido, é o que se usa) e `icmbio-manual-identidade-visual.pdf` |
| O que já foi portado para a aplicação, e por quê | `docs/processos/design_system.md` |
| O porte em si | `interface/tema.py`, `interface/app.py`, `.streamlit/config.toml` |

## Ordem de autoridade

Quando dois arquivos do pacote se contradizerem:

1. **`design-system/tokens/*.css`** — fonte de verdade dos valores. Nenhum hex,
   raio, duração ou degrau de tipografia deve ser inventado ou copiado de outro
   lugar.
2. **`design-system/readme.md`** — autoridade das regras de uso (quando aplicar
   cada token, proibições, fundamentos de conteúdo).
3. Todo o resto (`.prompt.md`, `.d.ts`, `handoff/`, `SKILL.md` do pacote).

## Correções ao pacote — leia antes de seguir qualquer texto dele

O pacote foi gerado em duas rodadas (antes e depois de o logo e o manual de
identidade chegarem) e nem todo arquivo foi atualizado na segunda. Sabe-se que
está desatualizado:

- **O logo oficial existe e é o que se usa.** `design-system/SKILL.md` (última
  linha) ainda diz *"there is no logo (use the typographic `Wordmark`)"* —
  **ignore**. A assinatura oficial do RAN está em
  `design-system/assets/ran-logo.png` e é modelada por
  `design-system/components/brand/Logo.jsx` (`.d.ts` para as props), com as
  regras do Manual de Identidade Visual do ICMBio codificadas: área de reserva
  (p. 11), moldura branca sobre fundo de baixo contraste (p. 12 e 19), nunca
  transparência nem recolorir (p. 20). `Wordmark` fica só para espaços pequenos
  demais para a assinatura.
- **Cor por fonte de dados:** `components/rag/SourceChip.prompt.md` descreve a
  paleta teal/areia **anterior**. O mapa atual está em `tokens/colors.css`:
  Monitora azul RAN `#2F7FB7`, PANs `#006633`, SALVE `#669933`, SEI `#666666`,
  Publicações `#6E6E1A`.
- **Tipografia:** `components/core/Card.d.ts` e `readme.md` (seção "Aparência de
  um card") citam **Spectral**, fonte da rodada anterior que não existe mais em
  `tokens/typography.css`. As famílias atuais são Archivo (títulos/rótulos/marca),
  Source Sans 3 (corpo) e IBM Plex Mono (dados).
- **`design-system/handoff/prompt-claude-code.md`** é o prompt da rodada anterior;
  só a seção de forma/espaçamento/estados/movimento continua válida.
- **Aliases de compatibilidade:** o bloco `--teal-*`/`--sand-*`/`--moss-*`/
  `--amber-*`/`--sky-*` no fim de `tokens/colors.css` **não é legado morto** — 12
  dos 24 componentes ainda o consomem. Não o remova ao portar.

## A aplicação é Streamlit, não React

Os `.jsx` em `design-system/components/` e `design-system/ui_kits/` são
**referência de composição, estado e copy — não código consumível**. A interface
do produto é Streamlit (`interface/app.py`), que não renderiza JSX. Também não
são consumíveis `design-system/templates/consulta-herpia/support.js` e
`ds-base.js` (runtime da ferramenta geradora).

Não porte JSX literalmente, e não proponha adicionar React, npm ou build de
front-end para reaproveitá-lo. O que atravessa para Streamlit é:

1. **Valores de token** — `tokens/*.css`, portados em `interface/tema.py`.
2. **CSS global** via `st.html()` (não `st.markdown(unsafe_allow_html=True)`:
   no Streamlit 1.63 o `<style>` vaza como texto), mirando `data-testid`.
3. **HTML estático autoral** para os componentes de domínio.
4. **Widget nativo re-skinado** — `st.dialog`, `st.toast`, `st.expander`,
   `st.checkbox` no lugar de `Dialog`, `Toast`, `Card`, `Checkbox`.

**Invariante de segurança, não negociável:** o HTML injetado **nunca** interpola
texto vindo do backend ou do LLM (resposta, citação, justificativa, pergunta do
usuário). Esses passam por `st.write`/`st.markdown`/`st.caption` sem
`unsafe_allow_html`. Ver os docstrings de `interface/tema.py`.

## Ao implementar ou verificar uma interface

1. Leia `design-system/readme.md` inteiro antes da primeira decisão visual.
2. Pegue valores de `tokens/*.css` — nunca invente nem arredonde.
3. Confira o componente em `components/<grupo>/<Nome>.d.ts` (props) e
   `.prompt.md` (uso), aplicando as ressalvas acima.
4. Confira a composição contra `ui_kits/herpia-assistente/` — que tela mostra o
   quê, em que ordem.
5. Confira o resultado contra os especímenes em `guidelines/*.card.html`.
6. Respeite as proibições do `readme.md`: sem gradiente, sem imagem decorativa,
   sem emoji na interface (exceção única já existente: `page_icon="🦎"`), sem
   glassmorphism, sem animação de entrada de página, foco visível sempre.
7. Copy em **pt-BR**, 3ª pessoa impessoal, sem hedge, sentence case, siglas com
   grafia oficial (RAN, ICMBio, SALVE, PANs, SEI, Monitora) — `readme.md`, seção
   "FUNDAMENTOS DE CONTEÚDO".
8. Registre o que portou, e o que deliberadamente não portou, em
   `docs/processos/design_system.md`.

Para mocks e protótipos descartáveis: copie os assets para fora e gere HTML
estático que linke `design-system/styles.css`. Continua valendo a regra de não
editar nada dentro de `design-system/`.
