# Chatbot RAN/ICMBio

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

## Para desenvolvedores e sessões de IA

Consulte [`CLAUDE.md`](./CLAUDE.md) para o contexto completo do projeto, arquitetura planejada, regras sobre dados sensíveis e próximas etapas.
