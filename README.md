# HerpIA — Assistente Inteligente para Consulta de Informações sobre a Herpetofauna Brasileira

**Nome técnico:** Sistema RAG para Consulta Inteligente de Dados sobre a Herpetofauna Brasileira — RAN/ICMBio

Projeto de chatbot interno baseado em RAG para facilitar a consulta a informações sobre a herpetofauna brasileira, apoiando técnicos e gestores do RAN/ICMBio no acesso a dados ambientais, científicos e institucionais.

## Status do projeto

Em desenvolvimento. Coleta, extração de texto e chunking concluídos para Monitora, PANs e SALVE (**59.080 trechos**, indexados no Qdrant com embeddings BGE-M3). O backend FastAPI responde de ponta a ponta (`/buscar`, `/perguntar`, `/feedback`, `/saude`), com geração via LLM local (Ollama) e registro de feedback em PostgreSQL. O protótipo de interface em Streamlit está funcional, com a identidade oficial do RAN/ICMBio aplicada.

Pendentes: classificação de sensibilidade individual formal, exportação do SEI (depende de autorização da equipe do RAN), busca híbrida, autenticação e validação com usuários. Status detalhado por fase em [`docs/roadmap.md`](./docs/roadmap.md). Prazo previsto de até um ano para conclusão.

## Público-alvo

- Técnicos do RAN/ICMBio
- Gestores do RAN/ICMBio
- Pesquisadores vinculados ao RAN

## Fontes previstas

- Programa Monitora do ICMBio
- PANs
- SALVE
- SEI/ICMBio
- Publicações científicas dos pesquisadores vinculados ao RAN

## Estrutura de pastas

```
01_fontes_web/                       # Fontes web (Monitora, PANs, SALVE, SEI)
02_publicacoes_cientificas_ran/      # Publicações científicas do RAN, por tema
03_documentos_autorizados/           # Documentos avaliados e autorizados para indexação
04_documentos_pendentes_avaliacao/   # Documentos ainda não avaliados
05_documentos_sensiveis_nao_indexar/ # Documentos sensíveis — não indexar
06_inventario/                       # Inventário das fontes e documentos
07_processados/                      # Textos extraídos, chunks e metadados

backend/                             # API FastAPI (busca, geração, feedback)
interface/                           # Protótipo de interface em Streamlit
design-system/                       # Design system do HerpIA (somente leitura)
scripts/                             # Pipelines de coleta, extração e indexação
docs/                                # Processos, decisões (ADRs) e roadmap
```

## Observação sobre dados

Este repositório não deve conter PDFs internos, documentos sensíveis, arquivos do SEI, dados pessoais ou informações ambientais restritas.

## Infraestrutura local

O projeto pode ser executado com dois computadores em rede local:

- **PC de desenvolvimento** — onde o código é escrito (VS Code / Claude Code), scripts são executados e versionamento Git é feito.
- **PC servidor local** — onde rodam PostgreSQL e Qdrant via Docker, e onde ficam os dados reais (PDFs, chunks, embeddings, metadados).

O acesso do PC de desenvolvimento ao servidor é feito via **túnel SSH**, sem expor os serviços diretamente na rede. Veja o guia completo em [`docs/infraestrutura-local.md`](./docs/infraestrutura-local.md).

## Identidade visual

O design system do HerpIA fica em [`design-system/`](./design-system/) — tokens de cor, tipografia, forma e movimento, componentes de referência, guidelines e o kit de telas. É um **artefato recebido e imutável**: correções e ressalvas ficam em [`docs/processos/design_system.md`](./docs/processos/design_system.md), nunca dentro do pacote.

A aplicação do sistema à interface Streamlit vive em `interface/tema.py` (tokens portados, CSS global, componentes de domínio) e `.streamlit/config.toml`. Sessões de IA devem usar a skill de projeto `herpia-design` (`.claude/skills/herpia-design/`), que aponta para os arquivos certos e registra as instruções desatualizadas do pacote.

## Para desenvolvedores e sessões de IA

Consulte [`CLAUDE.md`](./CLAUDE.md) para o contexto completo do projeto, arquitetura planejada, regras sobre dados sensíveis e próximas etapas. Decisões técnicas registradas em [`docs/decisoes/`](./docs/decisoes/).
