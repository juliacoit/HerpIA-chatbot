# Autenticação de usuários

**Status:** 🔶 Implementado e testado em banco de teste (2026-10-07). Escopo definido pela equipe do RAN (ver "Decisões da equipe do RAN"): login obrigatório para todo o sistema. No código o padrão continua `AUTH_EXIGIR=nada`; para valer a decisão, o `.env` do ambiente de validação precisa de `AUTH_EXIGIR=tudo`. Falta a conferência visual da tela no navegador e criar as contas.

## O que é

Login para o HerpIA, para restringir o acesso à equipe e associar cada pergunta e cada avaliação (feedback) a quem a fez. Antes disto, a API não tinha nenhuma autenticação e o feedback era anônimo.

## Modelo de acesso

Contas locais por convite, sem autocadastro:

1. A administração cria a conta com `scripts/infra/gerenciar_usuarios.py criar`. A conta nasce sem senha e o script imprime um **código de convite** de uso único (válido por `AUTH_CONVITE_DIAS`, padrão 7 dias).
2. A pessoa abre a interface, escolhe **Primeiro acesso**, informa usuário, código e a senha que quiser (mínimo de 10 caracteres) e já entra.
3. Nos acessos seguintes, usa **Entrar** com usuário e senha.
4. Senha esquecida: a administração roda `novo-convite`, que apaga a senha, encerra as sessões abertas e gera outro código. Não há recuperação por e-mail (o projeto não tem servidor de e-mail).

O modelo não depende de terceiros, e isso é intencional: a equipe do RAN pediu independência da TI do ICMBio (ver "Decisões da equipe do RAN"), então o login institucional (SSO) está descartado e as contas locais são o modelo definitivo do protótipo, não um passo provisório.

## O que exige login: `AUTH_EXIGIR`

| Valor | Efeito na API | Efeito na interface |
|---|---|---|
| `nada` (padrão) | Tudo aberto, como antes | Sem tela de acesso |
| `feedback` | Só `POST /feedback` exige sessão | Consulta liberada; botão "Entrar" na barra lateral; avaliar pede login |
| `tudo` | `/buscar`, `/perguntar` e `/feedback` exigem sessão | Tela de acesso antes de qualquer coisa |

O padrão é `nada` para não quebrar a bateria (`scripts/teste_perguntas_dominio.py`) nem os demais scripts, que chamam a API sem sessão. Em qualquer modo, uma sessão válida enviada na requisição fica associada à interação e ao feedback.

A interface descobre o modo em `GET /saude` (campo `auth.exigir`). A proteção está na API, não só na tela: sem sessão válida, os endpoints cobertos respondem 401.

## Endpoints

| Método e rota | Função |
|---|---|
| `POST /auth/primeiro-acesso` | Troca o código de convite pela senha escolhida |
| `POST /auth/login` | Confere usuário e senha; devolve o token da sessão e sua validade |
| `GET /auth/eu` | Usuário da sessão atual |
| `POST /auth/sair` | Encerra a sessão |

As demais rotas recebem a sessão em `Authorization: Bearer <token>`.

## Banco de dados

Criado automaticamente na inicialização do backend (`backend/db.py`), de forma aditiva:

- **`usuarios`**: usuário (único, em minúsculas), nome, hash da senha, situação (ativa ou não), hash e validade do convite, contagem de tentativas e bloqueio, último login.
- **`sessoes`**: hash do token, usuário e validade (`AUTH_SESSAO_HORAS`, padrão 12 horas).
- **`interacoes.usuario_id`** e **`feedback.usuario_id`**: quem perguntou e quem avaliou. `NULL` nos registros anônimos, inclusive todos os anteriores ao login.

Na primeira vez que o backend desta versão subir contra o PostgreSQL real, ele cria as duas tabelas e acrescenta as duas colunas. Nenhum dado existente é alterado.

## Segurança

- **Senha:** nunca gravada em claro. Hash scrypt (biblioteca padrão do Python, sem dependência nova), com sal aleatório por usuário.
- **Token de sessão e código de convite:** aleatórios; o banco guarda só o SHA-256. Quem ler as tabelas não consegue se passar por ninguém.
- **Falha de login:** a mesma mensagem para usuário inexistente, conta desativada e senha errada, para não revelar quais usuários existem.
- **Bloqueio:** 5 tentativas erradas seguidas bloqueiam a conta por 15 minutos. Efeito colateral aceito para uso interno: alguém que saiba o usuário de outra pessoa consegue bloqueá-la temporariamente.
- **Feedback alheio:** uma interação feita por um usuário logado só pode ser avaliada por ele (os ids são sequenciais; sem isso, qualquer pessoa avaliaria a resposta de outra).
- **Desativar conta** encerra as sessões abertas na hora.
- **Transporte:** o token trafega no cabeçalho HTTP. Fora da própria máquina, o acesso precisa passar pelo túnel SSH ou por HTTPS; expor o backend em HTTP na rede deixaria senha e token legíveis.
- **Dados pessoais:** com login, o log de perguntas passa a ser associado a pessoas identificadas. A tela de acesso avisa disso. Quem pode ler a tabela `interacoes` deve ser o mínimo necessário.

## Interface

- `interface/acesso.py`: tela de acesso (Entrar e Primeiro acesso), portada de `design-system/ui_kits/herpia-assistente/LoginScreen.jsx`.
- `interface/app.py`: mostra a tela de acesso conforme o modo; na barra lateral, nome e usuário de quem entrou e o botão "Sair". Sair apaga a conversa da tela.
- `interface/cliente_api.py`: envia o token e trata a sessão expirada (volta à tela de acesso com aviso).

Limitação: a sessão vive só enquanto a aba está aberta. Recarregar a página pede o login de novo, mesma limitação do histórico da conversa.

## Como usar

```bash
# criar a conta e obter o código de convite
python scripts/infra/gerenciar_usuarios.py criar nome.sobrenome "Nome Completo"

# senha esquecida
python scripts/infra/gerenciar_usuarios.py novo-convite nome.sobrenome

# bloquear, liberar e listar
python scripts/infra/gerenciar_usuarios.py desativar nome.sobrenome
python scripts/infra/gerenciar_usuarios.py reativar nome.sobrenome
python scripts/infra/gerenciar_usuarios.py listar
```

Para ligar o login, defina `AUTH_EXIGIR=tudo` (ou `feedback`) no `.env` e reinicie o backend. Com `tudo`, a bateria de perguntas precisa de uma conta própria: crie-a com o script e defina `HERPIA_USUARIO` e `HERPIA_SENHA` no ambiente antes de rodar.

## Como foi testado

- **API:** 35 verificações contra um banco PostgreSQL de teste separado (criado e removido no teste), com as rotas reais e sem carregar embeddings, Qdrant nem LLM: os três modos, primeiro acesso, convite de uso único, mensagem única de falha, bloqueio, desativação, redefinição, expiração de sessão, feedback em interação alheia e funcionamento sem PostgreSQL.
- **Interface:** fluxo completo com `streamlit.testing.v1.AppTest` contra um backend de teste: tela inicial, erro de login, primeiro acesso, pergunta e feedback autenticados, sair e novo login.
- **Aparência no navegador:** conferida em 2026-10-09 com Chromium, contra um backend mínimo de teste (sem banco).
- **Não testado:** o fluxo contra o backend completo com o banco real.

Os testes foram scripts descartáveis, feitos antes de o repositório ganhar a suíte `tests/` (pytest); ainda não há testes de autenticação nela.

## Decisões da equipe do RAN (2026-10-07)

Respostas às quatro perguntas enviadas pela desenvolvedora:

| Pergunta | Decisão |
|---|---|
| Quem participa da validação | Grupo pequeno: quatro servidores do RAN |
| Login para tudo ou só para avaliar | Para tudo, acesso restrito (`AUTH_EXIGIR=tudo`) |
| Avaliações identificadas ou com pseudônimo | Identificadas: pode registrar quem avaliou |
| Login institucional pela TI do ICMBio | Descartado. O acesso institucional é muito restrito por critérios de segurança e governança, e a equipe quer independência: criar uma demanda ou um vínculo formal com o instituto traria cobranças em vários aspectos |

Consequências:

- O sistema de contas próprio (por convite) é o modelo adotado, sem integração com sistemas do ICMBio.
- Com quatro contas, o script de administração basta; uma tela de administração não é prioridade.
- Como a avaliação é identificada, o aviso de registro na tela de acesso permanece.

## Pendências técnicas

- [ ] Definir `AUTH_EXIGIR=tudo` no `.env` do ambiente de validação e criar as quatro contas.
- [x] Conferir a tela de acesso no navegador contra o kit do design system (2026-10-09, ver `docs/processos/design_system.md`, "Tela de acesso").
- [ ] Manter a sessão ao recarregar a página.
- [ ] Tela de administração e painel de feedbacks por usuário (hoje, script e consulta direta ao banco).
- [x] Sessão para a bateria de perguntas: com `HERPIA_USUARIO` e `HERPIA_SENHA` no ambiente, `scripts/teste_perguntas_dominio.py` faz login antes de rodar (não testado contra um backend real com login ligado).
