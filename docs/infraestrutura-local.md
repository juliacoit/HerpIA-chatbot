# Infraestrutura local

## Situação atual

O protótipo está sendo desenvolvido e executado na máquina local da desenvolvedora. Todos os serviços (banco vetorial, banco relacional, interface, backend) rodam via Docker Compose no mesmo ambiente de desenvolvimento.

Isso é adequado para a fase atual — construir e validar o fluxo básico de RAG — mas não é a configuração de longo prazo.

## Evolução planejada: servidor local dedicado

Após o fluxo básico de RAG estar funcionando, o sistema deverá ser migrado para um **servidor local dedicado**, hospedado na infraestrutura do RAN/ICMBio. Essa migração é a evolução desejável porque:

- **Organização**: separa o ambiente de desenvolvimento do ambiente de uso real.
- **Segurança**: os dados (incluindo documentos sensíveis, embeddings e metadados) ficam em infraestrutura controlada pelo RAN/ICMBio, sem depender de máquina pessoal.
- **Escalabilidade**: um servidor dedicado suporta múltiplos usuários simultâneos, indexação de maior volume de documentos e futura expansão da base.
- **Continuidade**: o serviço não fica sujeito a disponibilidade da máquina da desenvolvedora.

## O que precisará estar no servidor

| Componente | Tecnologia | Observação |
|---|---|---|
| Banco vetorial | Qdrant | Armazena embeddings dos chunks |
| Banco relacional | PostgreSQL | Metadados, usuários, logs, feedback |
| Backend | FastAPI + Docker | API do chatbot |
| Interface | Streamlit (protótipo) | Substituível por interface web dedicada |
| Orquestração | Docker Compose | Gestão dos contêineres |

## Quando migrar

A migração para servidor dedicado **não é prioridade imediata**. Deve ocorrer após:

1. O pipeline de ingestão (extração de PDFs, chunking, embeddings) estar funcionando.
2. O fluxo de recuperação e geração de respostas com citação de fontes estar validado localmente.
3. Pelo menos um ciclo de validação com técnicos do RAN/ICMBio ter sido realizado no protótipo local.

## Decisão registrada

Ver ADR [0003 — Infraestrutura: protótipo local antes de servidor dedicado](decisoes/0003-infraestrutura-prototipo-local-antes-de-servidor-dedicado.md).
