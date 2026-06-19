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

---

## Configuração com dois computadores

Esta seção descreve como configurar o projeto para rodar com um **PC servidor** (bancos de dados, dados reais) e um **PC de desenvolvimento** (código, scripts, VS Code).

```
[PC de desenvolvimento]  ──── túnel SSH ────►  [PC servidor]
   VS Code / scripts                              PostgreSQL (5432)
   Git / GitHub                                  Qdrant (6333 / 6334)
   acesso via localhost                          dados reais / PDFs
```

---

## PC Servidor — configuração inicial

### 1. Instalar Docker e Docker Compose

No Windows, instale o **Docker Desktop** com suporte ao WSL 2:

1. Baixe em: https://www.docker.com/products/docker-desktop/
2. Durante a instalação, mantenha marcada a opção **"Use WSL 2 based engine"**.
3. Após instalar, abra o terminal (PowerShell ou WSL) e verifique:

```bash
docker --version
docker compose version
```

### 2. Clonar o repositório

```bash
git clone https://github.com/<seu-usuario>/chatbot-ran-icmbio.git
cd chatbot-ran-icmbio
```

### 3. Criar o arquivo `.env`

```bash
cp .env.example .env
```

### 4. Editar as variáveis do `.env`

Abra o arquivo `.env` e substitua os valores fictícios pelos reais.

> ⚠️ Nunca versione o `.env` com valores reais. O `.gitignore` já o protege, mas confirme antes de qualquer `git add`.

### 5. Subir os serviços

```bash
docker compose up -d
```

### 6. Verificar os containers

```bash
docker ps
```

### 7. Ver logs

```bash
docker compose logs -f
```

### 8. Parar os serviços

```bash
docker compose down
```

---

## PC de Desenvolvimento — acesso via túnel SSH

### Abrir o túnel SSH

```bash
ssh -N -L 5432:localhost:5432 -L 6333:localhost:6333 -L 6334:localhost:6334 usuario@IP_DO_SERVIDOR
```

Deixe esse terminal aberto enquanto trabalha.

### Configurar o `.env` no PC de desenvolvimento

```env
DATABASE_URL=postgresql://ran_user:change_me@localhost:5432/ran_chatbot
QDRANT_URL=http://localhost:6333
```

### Testar a conexão

```bash
python scripts/check_services.py
```

---

## Notas de segurança

- Nunca versione o arquivo `.env`.
- As portas `5432`, `6333` e `6334` ficam restritas ao `127.0.0.1` — isso é intencional.
- Não exponha as portas diretamente na rede sem revisar as implicações de segurança.
- Dados em `04_documentos_pendentes_avaliacao/` e `05_documentos_sensiveis_nao_indexar/` nunca devem ser processados automaticamente.
