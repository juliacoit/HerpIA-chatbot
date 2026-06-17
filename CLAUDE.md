# CLAUDE.md

## Visão geral do projeto

Este é o repositório do **chatbot interno do RAN/ICMBio** (Centro Nacional de Pesquisa e Conservação de Répteis e Anfíbios), desenvolvido em parceria com o CNPq e intermediação do CIEE. O sistema é baseado em **RAG (Retrieval-Augmented Generation)**: consulta uma base de conhecimento previamente organizada, recupera trechos relevantes e gera respostas fundamentadas nesses trechos, sempre citando as fontes utilizadas (documento, página, link, seção ou base consultada). O foco temático é a herpetofauna brasileira (répteis e anfíbios).

## Objetivo

Facilitar o acesso de técnicos e gestores do RAN/ICMBio a informações ambientais, científicas e institucionais relacionadas a répteis e anfíbios, por meio de respostas objetivas, verificáveis e sempre acompanhadas das fontes que as fundamentam.

## Público-alvo

- Técnicos do RAN/ICMBio
- Gestores do RAN/ICMBio
- Pesquisadores vinculados ao RAN

## Fontes de dados

1. **Programa Monitora do ICMBio** — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento
2. **PANs (Planos de Ação Nacional para Conservação de Espécies Ameaçadas de Extinção)** — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan
3. **SALVE** — https://salve.icmbio.gov.br/#/
4. **SEI/ICMBio** — https://sei.icmbio.gov.br/sip/login.php?sigla_orgao_sistema=ICMBio&sigla_sistema=SEI&infra_url=L3NlaS8= (acesso restrito a usuários autorizados; usar apenas documentos previamente exportados, autorizados e classificados)
5. **Publicações científicas dos pesquisadores vinculados ao RAN** — base local de PDFs (artigos científicos, estudos técnicos, relatórios, capítulos e materiais institucionais)

Ver também `01_fontes_web/urls_fontes.md` para detalhes e observações sobre cada fonte.

## Regras sobre dados sensíveis

- O projeto manipula dados potencialmente sensíveis (ex.: localizações precisas de espécies ameaçadas, informações administrativas restritas, dados pessoais). Esses dados ainda precisam ser avaliados caso a caso.
- Nenhum documento deve ser indexado na base de conhecimento sem avaliação, autorização e classificação prévias de sensibilidade.
- Documentos classificados como sensíveis ficam em `05_documentos_sensiveis_nao_indexar/` e **não devem ser indexados nem enviados a nenhuma API externa**.
- O sistema pode usar API externa de LLM, mas **nunca deve enviar documentos completos** — apenas os trechos (chunks) já recuperados, filtrados e autorizados.
- Dados pessoais, informações administrativas restritas (ex.: processos SEI) e localizações sensíveis de espécies devem receber tratamento cuidadoso e, quando aplicável, anonimização ou generalização antes de qualquer indexação.
- Como agente, nunca exponha, copie, resuma ou inclua em commits o conteúdo de documentos sensíveis ou pendentes de avaliação. Nunca adicione chaves de API, tokens, senhas ou credenciais ao repositório. Se encontrar arquivos `.env`, chaves ou tokens, não os modifique — apenas confirme que permanecem fora do versionamento (já cobertos pelo `.gitignore`).

## Arquitetura planejada

```
Fontes de dados → Extração e limpeza → Classificação de sensibilidade → Chunking →
Embeddings → Banco vetorial → Recuperação → Filtro de acesso → Modelo de linguagem → Resposta com fontes
```

## Tecnologias planejadas

- Python (linguagem principal)
- LlamaIndex ou LangChain (orquestração do RAG)
- Qdrant (banco vetorial)
- PostgreSQL (dados estruturados, metadados, usuários, logs e feedback)
- FastAPI (backend)
- Streamlit (protótipo inicial de interface)
- PyMuPDF (extração de texto de PDFs)
- Tesseract OCR (PDFs escaneados, quando necessário)
- Docker (implantação)
- API externa de LLM (ex.: OpenAI API), respeitando as regras de segurança de dados
- Embeddings para busca semântica
- Busca híbrida (semântica + palavras-chave), quando aplicável

## Estrutura de diretórios

```
chatbot-ran-icmbio/
├── 01_fontes_web/                       # Fontes web previstas (Monitora, PANs, SALVE, SEI) e metadados de coleta
│   ├── monitora/
│   ├── pans/
│   ├── salve/
│   └── sei/
├── 02_publicacoes_cientificas_ran/      # Publicações científicas dos pesquisadores do RAN, organizadas por tema
│   ├── anfibios/
│   ├── repteis/
│   ├── conservacao/
│   ├── monitoramento/
│   └── outros/
├── 03_documentos_autorizados/           # Documentos já avaliados e autorizados para indexação
├── 04_documentos_pendentes_avaliacao/   # Documentos ainda não avaliados quanto à sensibilidade
├── 05_documentos_sensiveis_nao_indexar/ # Documentos sensíveis — NUNCA indexar nem enviar a API externa
├── 06_inventario/                       # Planilhas/inventário das fontes e documentos catalogados
└── 07_processados/                      # Saídas dos pipelines de processamento
    ├── textos_extraidos/
    ├── chunks/
    └── metadados/
```

- `01_fontes_web/` contém `urls_fontes.md` com as URLs e observações de cada fonte web.
- `06_inventario/` contém `inventario_fontes.xlsx`, o inventário consolidado das fontes/documentos.

## Convenções de desenvolvimento

- Escrever código em Python com clareza, priorizando legibilidade sobre abstrações prematuras.
- Separar claramente as responsabilidades: ingestão, processamento/extração, pipeline de RAG, interface (Streamlit/FastAPI) e configuração.
- Manter scripts documentados de forma objetiva (o que fazem e por quê, quando não for óbvio pelo código).
- Usar nomes de variáveis, funções e arquivos descritivos.
- Não misturar dados brutos (`01_*`, `02_*`) com dados processados (`07_processados/`).
- Manter, para cada trecho indexado, metadados de fonte, página, URL, caminho local, data de coleta/atualização e nível de sensibilidade.
- Nunca commitar PDFs sensíveis, dados pessoais ou exportações do SEI sem autorização explícita.

## Regras para respostas do chatbot

- Responder apenas com base nos documentos/trechos efetivamente recuperados da base de conhecimento.
- Citar sempre as fontes utilizadas (documento, página, link, seção ou base).
- Indicar claramente quando não houver evidência suficiente na base para responder, em vez de inventar uma resposta.
- Evitar alucinações — nunca complementar respostas com conhecimento não verificado pelas fontes recuperadas.
- Priorizar respostas objetivas, verificáveis e rastreáveis até a fonte original.

## Próximas etapas recomendadas

1. Consolidar o inventário das fontes (`06_inventario/inventario_fontes.xlsx`).
2. Cadastrar e organizar as publicações científicas em `02_publicacoes_cientificas_ran/`.
3. Classificar a sensibilidade dos documentos pendentes em `04_documentos_pendentes_avaliacao/`.
4. Criar o pipeline de extração de PDFs (PyMuPDF, com fallback de OCR via Tesseract).
5. Criar o pipeline de scraping/coleta das fontes web (Monitora, PANs, SALVE, SEI).
6. Gerar chunks e embeddings a partir dos textos extraídos.
7. Configurar o banco vetorial Qdrant.
8. Criar o protótipo de interface em Streamlit.
9. Implementar a geração de respostas com citação de fontes.
10. Validar o protótipo com técnicos e gestores do RAN/ICMBio.

## Infraestrutura

O protótipo está sendo desenvolvido e executado na **máquina local da desenvolvedora** (via Docker Compose). A migração para um servidor local dedicado na infraestrutura do RAN/ICMBio é a evolução desejável — melhora organização, segurança e escalabilidade — mas **não é prioridade imediata**. Deve ocorrer após o fluxo básico de RAG estar funcionando e validado localmente.

Ver detalhes em [`docs/infraestrutura-local.md`](docs/infraestrutura-local.md) e ADR [0003](docs/decisoes/0003-infraestrutura-prototipo-local-antes-de-servidor-dedicado.md).

## Observações para sessões futuras do Claude Code

- Este projeto está em fase inicial — a maior parte das pastas existe como estrutura preparada, ainda sem conteúdo processado.
- O foco atual é implementar o protótipo RAG localmente. Não sugerir nem iniciar migração para servidor dedicado antes da validação do protótipo.
- Nunca mover, apagar ou sobrescrever documentos, PDFs ou planilhas sem autorização explícita do usuário.
- Nunca expor, copiar ou resumir o conteúdo de documentos sensíveis ou pendentes de avaliação.
- O projeto tem prazo de até um ano para desenvolvimento; a atualização da base de conhecimento será semestral.
