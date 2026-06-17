# 0003. Infraestrutura: protótipo local antes de servidor dedicado

- **Status:** Aceita
- **Data:** 2026-06-17
- **Responsável(eis):** Equipe do projeto (RAN/ICMBio, CNPq, CIEE)

## Contexto

O ADR [0001](0001-stack-tecnologica-inicial.md) definiu que Qdrant e PostgreSQL precisarão de infraestrutura própria — local ou em contêiner via Docker — e delegou os detalhes para um ADR específico.

O projeto está em fase inicial e o fluxo básico de RAG (ingestão, chunking, recuperação, geração com citação de fontes) ainda não foi implementado. Há uma opção entre dois caminhos:

1. Configurar desde já um servidor local dedicado na infraestrutura do RAN/ICMBio.
2. Desenvolver o protótipo na máquina local da desenvolvedora e migrar para servidor dedicado depois.

## Decisão

**Desenvolver o protótipo na máquina local** e migrar para um servidor local dedicado somente após o fluxo básico de RAG estar funcionando e validado.

Durante a fase de protótipo, todos os serviços (Qdrant, PostgreSQL, FastAPI, Streamlit) rodarão via Docker Compose na máquina da desenvolvedora.

A migração para servidor dedicado é a **evolução desejável** — melhora organização, segurança e escalabilidade — mas não é prioridade imediata.

## Consequências

- O ambiente de desenvolvimento será a máquina local da desenvolvedora até validação do protótipo.
- A configuração Docker Compose deve ser pensada desde o início para facilitar a portabilidade para o servidor (sem hardcoded paths ou dependências de sistema operacional específico).
- Quando a migração ocorrer, será necessário: provisionar o servidor, transferir dados indexados, configurar acesso de rede e autenticação de usuários.
- Documentação adicional sobre o servidor planejado em [`docs/infraestrutura-local.md`](../infraestrutura-local.md).
