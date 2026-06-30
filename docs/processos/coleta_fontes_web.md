# Coleta das fontes web

- **Status:** Em desenvolvimento (Monitora e PANs implementados; SALVE com script, execução pendente; SEI com catalogação automatizada implementada)
- **Última atualização:** 2026-06-30
- **Responsável(eis):**

## Objetivo

Coletar/atualizar periodicamente o conteúdo das fontes web previstas para a base de conhecimento: Programa Monitora, PANs, SALVE e SEI/ICMBio (ver `01_fontes_web/urls_fontes.md`).

## Entradas

- URLs listadas em `01_fontes_web/urls_fontes.md`.
- Para o SEI/ICMBio: apenas documentos previamente exportados, autorizados e classificados por um usuário autorizado — não há scraping automatizado previsto para o SEI.

## Saídas

- Conteúdo coletado salvo em `01_fontes_web/<fonte>/` (subpastas `monitora/`, `pans/`, `salve/`, `sei/`).
- Metadados de coleta (URL de origem, data de coleta) a serem definidos.

## Ferramentas

Varia por fonte — ver análise por site abaixo. Provavelmente duas abordagens distintas: scraping HTML simples (Monitora, PANs) e renderização JS (SALVE).

## Análise por site (2026-06-16)

Cada fonte web tem uma estrutura muito diferente, então não dá para usar um único scraper genérico — é preciso um coletor por site.

### Programa Monitora
- ✅ **Implementado** em `scripts/coleta/coleta_monitora.py` — ver detalhamento completo em [`coleta_monitora_detalhado.md`](coleta_monitora_detalhado.md).
- Página HTML tradicional (gov.br), sem necessidade de renderização JS.
- Conteúdo organizado por **tipo de recurso** (Materiais de Apoio, Artigos Monitora, Estrutura do Programa, Relatórios, Dados, Legislação) e por **subprograma** (Terrestre, Aquático Continental, Marinho/Costeiro) — não por espécie.
- Há painéis interativos em **Power BI** embutidos (painel de dados gerenciais e painel do relatório florestal) — esses painéis não são HTML simples; dados neles exigem ou exportação manual, ou descobrir se o Power BI expõe uma API/dataset público.
- **Ferramenta sugerida:** requests + BeautifulSoup para a página e seus links internos; investigar separadamente os painéis Power BI antes de tentar automatizar.

### PANs
- Página HTML tradicional (gov.br), sem necessidade de renderização JS.
- Lista de PANs organizada **alfabeticamente por espécie/ecossistema**, dividida em "PANs em Execução" (40, cobrindo 992+ espécies ameaçadas) e "PANs Finalizados".
- Cada PAN é um link para uma subpágina própria (ex.: `/pan-albatrozes-e-petreis`); os documentos de cada plano estão dentro dessas subpáginas, não na página principal.
- **Exemplo real inspecionado — PAN Albatrozes e Petréis (PLANACAP):** a subpágina traz vigência do ciclo atual (2025-2030, 4º ciclo), 12 espécies-alvo (7 nacionalmente ameaçadas), bioma (Marinho) e instituição responsável (CEMAVE), além de uma seção de Documentos com: Portaria de aprovação (PDF), Matriz de Planejamento/Monitoria/Avaliação (XLSX), Lista de espécies-alvo (XLSX) e material de ciclos anteriores (sumários executivos, livros). Esse padrão de estrutura provavelmente se repete nos demais PANs.
- Existe uma seção "Saiba mais sobre os PANs" com links adicionais (Dados dos PANs, GATs, Documentos e Downloads) que precisam ser explorados individualmente.
- **Ferramenta sugerida:** requests + BeautifulSoup, com um crawler que primeiro lista as ~40+ subpáginas de PANs e depois visita cada uma para extrair Portarias (PDF) e Matrizes (XLSX).
- **Relevância para o RAN:** é provavelmente a fonte web mais rica e estruturada para a herpetofauna — vários PANs tratam diretamente de répteis e anfíbios (ex.: tartarugas marinhas), com documentos oficiais citáveis sobre status de conservação e ações planejadas por espécie.

### SALVE
- ✅ **Mapeamento técnico concluído e script implementado** em 2026-06-24 (`scripts/coleta/coleta_salve.py`) — ver detalhamento completo em [`coleta_salve_detalhado.md`](coleta_salve_detalhado.md). Ainda sem execução completa validada (ver ressalva de volume no documento detalhado).
- O front-end de todos os módulos é uma SPA/app Vue.js, mas **isso não impediu a coleta**: inspecionando os arquivos JS servidos (sem precisar de navegador/Playwright) foi possível localizar a API REST real por trás do portal público — `https://salve.icmbio.gov.br/salve-api/public/` —, que inclusive **se autodocumenta** (`GET /salve-api/public/` lista todos os endpoints e parâmetros).
- **O SALVE tem três módulos/URLs distintos**, cada um com finalidade diferente:
  - `salve.icmbio.gov.br/` — portal principal/público. **Fonte principal da coleta**: `/salve-api/public/search?grupoIds=1266,1257` (Répteis, Anfíbios) lista as fichas (2086 no total para a herpetofauna), e `/salve-api/public/fichaHtml?idFicha=<id>&section=<secao>` traz o conteúdo de cada ficha já dividido em 11 seções (header, taxonomia, distribuição, conservação, ameaças, referências bibliográficas, etc.).
  - `salve.icmbio.gov.br/salve-consulta/` — módulo de **consulta pública/participativa**; visualização pública (sem login), mas contribuir exige login. API própria (Grails, `POST ficha/consultaAmpla`) lista as espécies em consulta aberta no momento — secundário, não traz a categoria de risco consolidada.
  - `salve.icmbio.gov.br/salve/` — módulo de **gestão interna**; exige login institucional via SICA-e. Não investigado, fora de escopo (mesma lógica do SEI/ICMBio).
- **Relevância para o RAN:** é a fonte ideal para responder "qual a categoria de risco de extinção da espécie X?" e "quais fichas/documentos técnicos existem para essa espécie?" — dados estruturados por espécie (categoria atual, distribuição, conservação, ameaças, referências), sem necessidade de autenticação para a herpetofauna.

### SEI/ICMBio
- ✅ **Catalogação automatizada implementada** — ver detalhamento em [`coleta_sei_detalhado.md`](coleta_sei_detalhado.md).
- Sistema eletrônico de gestão de **processos administrativos** institucionais. O acesso requer login institucional (SIP); a automação do login via Python foi implementada e validada em 2026-06-30.
- **O que foi automatizado:** navegação nos blocos internos, listagem de processos e extração de metadados de documentos (título, tipo, ID interno) — sem leitura de conteúdo.
- **O que permanece manual:** exportação e avaliação dos documentos. Nenhum conteúdo de documento é acessado, transmitido ou armazenado pelos scripts.
- **43 blocos internos catalogados**, 16 classificados como prioritários (~464 processos). Catálogo salvo em `01_fontes_web/sei/blocos_internos.json` e `01_fontes_web/sei/documentos_por_processo.json`.

## Passo a passo

- Monitora e PANs: ver passo a passo em [`coleta_monitora_detalhado.md`](coleta_monitora_detalhado.md) e [`coleta_pans_detalhado.md`](coleta_pans_detalhado.md).
- SALVE: mapeamento técnico concluído e script implementado (ver [`coleta_salve_detalhado.md`](coleta_salve_detalhado.md)); execução completa ainda a validar.
- SEI: catalogação automatizada implementada (ver [`coleta_sei_detalhado.md`](coleta_sei_detalhado.md)); exportação e avaliação de documentos são manuais.

## Frequência de execução

Atualização semestral da base de conhecimento, conforme decisão geral do projeto.

## Observações sobre dados sensíveis

O acesso ao SEI/ICMBio é restrito a usuários autorizados. Os scripts de catalogação (`listar_blocos_sei.py`, `listar_documentos_sei.py`) fazem login e navegam o sistema, mas **não leem nem transmitem o conteúdo de nenhum documento** — apenas metadados de navegação (títulos, tipos, IDs internos). Documentos do SEI só entram no projeto após exportação manual, avaliação individual e autorização explícita da equipe do RAN.
