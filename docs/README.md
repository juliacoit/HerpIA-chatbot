# Documentação do projeto

Esta pasta reúne a documentação de processo do chatbot RAN/ICMBio — tudo que não é dado em si, mas explica **como e por que** o projeto está sendo construído.

Para o contexto geral do projeto (visão geral, arquitetura, regras sobre dados sensíveis), veja [`/CLAUDE.md`](../CLAUDE.md) na raiz do repositório.

## Estrutura

```
docs/
├── decisoes/    # Registro de decisões técnicas (ADRs) — o que foi decidido e por quê
├── processos/   # Documentação de cada processo/pipeline operacional do projeto
└── README.md    # Este arquivo
```

O histórico cronológico de progresso do projeto fica em [`/CHANGELOG.md`](../CHANGELOG.md), na raiz do repositório.

## Quando criar um novo documento

- **Tomou uma decisão técnica relevante** (escolha de ferramenta, formato, política)? Crie um ADR em `decisoes/` a partir do `decisoes/template.md`.
- **Definiu ou alterou um processo operacional** (como rodar a coleta web, como classificar sensibilidade, etc.)? Crie ou atualize um arquivo em `processos/` a partir do `processos/template.md`.
- **Concluiu uma etapa do roadmap ou mudou algo relevante no projeto**? Registre no `CHANGELOG.md`.
