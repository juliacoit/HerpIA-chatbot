# HerpIA — Assistente Inteligente para Consulta de Informações sobre a Herpetofauna Brasileira

**Nome técnico:** Sistema RAG para Consulta Inteligente de Dados sobre a Herpetofauna Brasileira — RAN/ICMBio

Projeto de chatbot interno baseado em RAG para facilitar a consulta a informações sobre a herpetofauna brasileira, apoiando técnicos e gestores do RAN/ICMBio no acesso a dados ambientais, científicos e institucionais.

## Status do projeto

Em desenvolvimento — fase inicial. Estrutura de pastas e fontes de dados definidas; pipelines de ingestão, processamento e RAG ainda não implementados. Prazo previsto de até um ano para conclusão.

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
```

## Observação sobre dados

Este repositório não deve conter PDFs internos, documentos sensíveis, arquivos do SEI, dados pessoais ou informações ambientais restritas.

## Infraestrutura local

O projeto pode ser executado com dois computadores em rede local:

- **PC de desenvolvimento** — onde o código é escrito (VS Code / Claude Code), scripts são executados e versionamento Git é feito.
- **PC servidor local** — onde rodam PostgreSQL e Qdrant via Docker, e onde ficam os dados reais (PDFs, chunks, embeddings, metadados).

O acesso do PC de desenvolvimento ao servidor é feito via **túnel SSH**, sem expor os serviços diretamente na rede. Veja o guia completo em [`docs/infraestrutura-local.md`](./docs/infraestrutura-local.md).

## Para desenvolvedores e sessões de IA

Consulte [`CLAUDE.md`](./CLAUDE.md) para o contexto completo do projeto, arquitetura planejada, regras sobre dados sensíveis e próximas etapas. Decisões técnicas registradas em [`docs/decisoes/`](./docs/decisoes/).
