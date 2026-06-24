# Coleta das fontes web

- **Status:** Em desenvolvimento (Monitora e PANs implementados; SALVE mapeado, script pendente; SEI fora de escopo de automação)
- **Última atualização:** 2026-06-24
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
- ✅ **Mapeamento técnico concluído** em 2026-06-24 — ver detalhamento completo em [`coleta_salve_detalhado.md`](coleta_salve_detalhado.md). Script de coleta ainda não implementado.
- O front-end de todos os módulos é uma SPA/app Vue.js, mas **isso não impediu a coleta**: inspecionando os arquivos JS servidos (sem precisar de navegador/Playwright) foi possível localizar a API REST real por trás do portal público — `https://salve.icmbio.gov.br/salve-api/public/` —, que inclusive **se autodocumenta** (`GET /salve-api/public/` lista todos os endpoints e parâmetros).
- **O SALVE tem três módulos/URLs distintos**, cada um com finalidade diferente:
  - `salve.icmbio.gov.br/` — portal principal/público. **Fonte principal da coleta**: `/salve-api/public/search?grupoIds=1266,1257` (Répteis, Anfíbios) lista as fichas (2086 no total para a herpetofauna), e `/salve-api/public/fichaHtml?idFicha=<id>&section=<secao>` traz o conteúdo de cada ficha já dividido em 11 seções (header, taxonomia, distribuição, conservação, ameaças, referências bibliográficas, etc.).
  - `salve.icmbio.gov.br/salve-consulta/` — módulo de **consulta pública/participativa**; visualização pública (sem login), mas contribuir exige login. API própria (Grails, `POST ficha/consultaAmpla`) lista as espécies em consulta aberta no momento — secundário, não traz a categoria de risco consolidada.
  - `salve.icmbio.gov.br/salve/` — módulo de **gestão interna**; exige login institucional via SICA-e. Não investigado, fora de escopo (mesma lógica do SEI/ICMBio).
- **Relevância para o RAN:** é a fonte ideal para responder "qual a categoria de risco de extinção da espécie X?" e "quais fichas/documentos técnicos existem para essa espécie?" — dados estruturados por espécie (categoria atual, distribuição, conservação, ameaças, referências), sem necessidade de autenticação para a herpetofauna.

### SEI/ICMBio
- Sistema eletrônico de gestão de **processos administrativos** institucionais (versão 2.0.18 identificada publicamente na tela de login), com autenticação em dois fatores — não é uma base de conhecimento científico, e sim o sistema de tramitação documental do órgão.
- Acesso restrito a usuários autorizados — sem scraping previsto (ver seção de dados sensíveis abaixo). Diferente das outras três fontes, o SEI não deve ser raspado mesmo que fosse tecnicamente possível, pois guarda processos que podem conter decisões internas, dados pessoais ou informações administrativas restritas.

## Passo a passo

- Monitora e PANs: ver passo a passo em [`coleta_monitora_detalhado.md`](coleta_monitora_detalhado.md) e [`coleta_pans_detalhado.md`](coleta_pans_detalhado.md).
- SALVE: mapeamento técnico concluído (ver [`coleta_salve_detalhado.md`](coleta_salve_detalhado.md)); script de coleta ainda a implementar.
- SEI: sem coleta automatizada prevista.

## Frequência de execução

Atualização semestral da base de conhecimento, conforme decisão geral do projeto.

## Observações sobre dados sensíveis

O acesso ao SEI/ICMBio é restrito a usuários autorizados. Documentos do SEI só entram no projeto após exportação manual, avaliação e classificação — nunca por coleta automatizada direta do sistema.
