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
- Página HTML tradicional (gov.br), sem necessidade de renderização JS.
- Conteúdo organizado por **tipo de recurso** (Materiais de Apoio, Artigos Monitora, Estrutura do Programa, Relatórios, Dados, Legislação) e por **subprograma** (Terrestre, Aquático Continental, Marinho/Costeiro) — não por espécie.
- Há painéis interativos em **Power BI** embutidos (painel de dados gerenciais e painel do relatório florestal) — esses painéis não são HTML simples; dados neles exigem ou exportação manual, ou descobrir se o Power BI expõe uma API/dataset público.
- **Ferramenta sugerida:** requests + BeautifulSoup para a página e seus links internos; investigar separadamente os painéis Power BI antes de tentar automatizar.

### PANs
- Página HTML tradicional (gov.br), sem necessidade de renderização JS.
- Lista de PANs organizada **alfabeticamente por espécie/ecossistema**, dividida em "PANs em Execução" (40) e "PANs Finalizados".
- Cada PAN é um link para uma subpágina própria (ex.: `/pan-albatrozes-e-petreis`); os documentos/PDFs de cada plano provavelmente estão dentro dessas subpáginas, não na página principal.
- Existe uma seção "Saiba mais sobre os PANs" com links adicionais (Dados dos PANs, GATs, Documentos e Downloads) que precisam ser explorados individualmente.
- **Ferramenta sugerida:** requests + BeautifulSoup, com um crawler que primeiro lista as ~40+ subpáginas de PANs e depois visita cada uma para extrair os documentos.

### SALVE
- É uma **SPA (Single Page Application)** em JavaScript — o HTML inicial (`https://salve.icmbio.gov.br/#/`) não contém conteúdo, apenas o título da página. Um scraper tradicional (requests/BeautifulSoup) não funciona aqui.
- Para mapear a navegação real (filtros, busca de espécies, fichas de avaliação de risco), é necessário:
  1. Abrir o site num navegador com as ferramentas de desenvolvedor (aba **Network**) e identificar os endpoints de API REST que o front-end consome ao navegar/filtrar.
  2. Avaliar se esses endpoints são públicos e estáveis o suficiente para uso direto (mais eficiente), ou se será preciso renderizar a página com **Selenium/Playwright** simulando cliques nos botões e filtros.
- Essa investigação ainda não foi feita e é um bloqueador para decidir a abordagem de coleta do SALVE.
- **Ferramenta sugerida (a confirmar):** Playwright (preferível a Selenium por suporte nativo a esperar requisições de rede), ou chamada direta à API interna do SALVE, se identificada e estável.

### SEI/ICMBio
- Sistema autenticado, acesso restrito a usuários autorizados — sem scraping previsto (ver seção de dados sensíveis abaixo).

## Passo a passo

A definir, após a investigação técnica do SALVE (item pendente acima) e da estrutura de subpáginas dos PANs.

## Frequência de execução

Atualização semestral da base de conhecimento, conforme decisão geral do projeto.

## Observações sobre dados sensíveis

O acesso ao SEI/ICMBio é restrito a usuários autorizados. Documentos do SEI só entram no projeto após exportação manual, avaliação e classificação — nunca por coleta automatizada direta do sistema.
