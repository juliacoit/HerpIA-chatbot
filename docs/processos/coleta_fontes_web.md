# Coleta das fontes web

- **Status:** A definir
- **Última atualização:** 2026-06-16
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
- É uma **SPA (Single Page Application)** em JavaScript em todos os módulos identificados — nenhum HTML inicial traz conteúdo renderizado. Um scraper tradicional (requests/BeautifulSoup) não funciona em nenhum deles.
- **O SALVE tem pelo menos três módulos/URLs distintos**, cada um com finalidade diferente:
  - `salve.icmbio.gov.br/#/` — portal principal/público.
  - `salve.icmbio.gov.br/salve/` — módulo de **gestão interna** do processo de avaliação de risco; exige login institucional via SICA-e. Aqui ficam manuais do usuário, instruções normativas de avaliação de risco e diretrizes de revisão de fichas.
  - `salve.icmbio.gov.br/salve-consulta/` — módulo de **consulta pública/participativa**; visualização é pública (sem login), mas contribuir com avaliações exige login. Tem filtros por nível taxonômico, nome científico/comum, e seções como "Espécie(s) em consulta ampla".
- **Pista valiosa encontrada via busca:** identificamos uma URL real de API por trás do sistema — `salve.icmbio.gov.br/salve/api/pdf/doi/...` — confirmando que existe uma **API REST** (`/salve/api/...`) servindo os dados em JSON/PDF, em vez de o conteúdo ser só renderizado em tela.
- Próximo passo recomendado para destravar essa fonte:
  1. Abrir o site num navegador com as ferramentas de desenvolvedor (aba **Network**), navegar pela busca de espécies em `salve-consulta/` e capturar as chamadas a `/salve/api/...` que retornam dados estruturados.
  2. Avaliar se esses endpoints são públicos e estáveis o suficiente para uso direto (mais eficiente que renderizar a página), ou se será necessário **Playwright/Selenium** simulando cliques nos filtros.
- Essa investigação (mapear os endpoints reais) ainda não foi feita e é o bloqueador técnico atual para decidir a abordagem de coleta do SALVE.
- **Relevância para o RAN:** é a fonte ideal para responder "qual a categoria de risco de extinção da espécie X?" e "quais fichas/documentos técnicos existem para essa espécie?" — dados estruturados por espécie (categoria atual, histórico de avaliações, registros de ocorrência), com quase 15 mil espécies da fauna brasileira avaliadas.

### SEI/ICMBio
- Sistema eletrônico de gestão de **processos administrativos** institucionais (versão 2.0.18 identificada publicamente na tela de login), com autenticação em dois fatores — não é uma base de conhecimento científico, e sim o sistema de tramitação documental do órgão.
- Acesso restrito a usuários autorizados — sem scraping previsto (ver seção de dados sensíveis abaixo). Diferente das outras três fontes, o SEI não deve ser raspado mesmo que fosse tecnicamente possível, pois guarda processos que podem conter decisões internas, dados pessoais ou informações administrativas restritas.

## Passo a passo

A definir, após a investigação técnica do SALVE (item pendente acima) e da estrutura de subpáginas dos PANs.

## Frequência de execução

Atualização semestral da base de conhecimento, conforme decisão geral do projeto.

## Observações sobre dados sensíveis

O acesso ao SEI/ICMBio é restrito a usuários autorizados. Documentos do SEI só entram no projeto após exportação manual, avaliação e classificação — nunca por coleta automatizada direta do sistema.
