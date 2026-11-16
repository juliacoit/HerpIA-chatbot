# Acesso externo pelo Tailscale Funnel

**Status:** ✅ Publicado em 2026-11-16 em `https://herpia.taileacc36.ts.net`, com `AUTH_EXIGIR=tudo` e cinco contas criadas. Conferido da própria máquina: página 200, WebSocket do Streamlit aceito (101) e backend inacessível pelo endereço público. Falta o teste de fora (rede móvel).

## O que é

Na validação, cada servidor do RAN usa o HerpIA na própria máquina. A Júlia decidiu (2026-11-16) publicar a interface pelo **Tailscale Funnel**: um endereço HTTPS público, do tipo `https://<maquina>.<rede>.ts.net`, que leva até o Streamlit rodando no computador do HerpIA. Não depende da rede interna do RAN nem da TI do ICMBio, e os servidores não instalam nada.

Alternativas descartadas: nuvem (custo, hardware para o LLM local e documentos internos em terceiro), rede privada Tailscale (exige instalar um programa em cada máquina) e Cloudflare Tunnel (a Cloudflare decifra o tráfego no caminho e exige domínio próprio).

## O que fica exposto

- **Só a interface** (Streamlit, porta 8501). Backend, PostgreSQL, Qdrant e Ollama continuam em `127.0.0.1`.
- O endereço fica aberto para **qualquer pessoa na internet**. O login do HerpIA é a única barreira.
- O HTTPS termina no computador do HerpIA; o Tailscale só repassa o tráfego cifrado.
- O sistema só fica no ar com o computador ligado, o backend e a interface rodando.

## Reforços feitos para a exposição pública

- `scripts/infra/publicar_funnel.sh` **se recusa a publicar** se o backend não exigir login para tudo: confere `auth.exigir` em `/saude`, confere que uma pergunta sem sessão recebe 401 e que a interface escuta só em `127.0.0.1`.
- `.streamlit/config.toml`: o Streamlit escuta só em `127.0.0.1` (o padrão é todas as interfaces), não envia telemetria de uso e não mostra traceback nem menu de desenvolvimento no navegador.
- **Limite global de falhas** de login e de convite: 20 por minuto, somando todas as contas; acima disso o backend responde 429 sem calcular hash. Complementa o bloqueio por conta (5 falhas, 15 minutos), que não cobre tentativas com usuários inexistentes.
- O cookie de sessão já sai com `Secure` quando a página está em HTTPS.

## Limitações conhecidas

- **Bloqueio de conta por terceiros:** quem souber o usuário de alguém consegue bloqueá-lo por 15 minutos errando a senha 5 vezes. Na internet isso pesa mais do que em uso interno. Mitigação: nomes de usuário que não sejam óbvios e o limite global acima.
- **Sem limite por endereço IP:** o backend só enxerga o Streamlit, e a documentação do Funnel não cita cabeçalho com o IP de origem no modo HTTPS.
- **Funnel em beta**, com limite de banda não divulgado e portas restritas a 443, 8443 e 10000.
- **O nome da máquina fica público:** o certificado é emitido pela Let's Encrypt, que registra os nomes em logs públicos de certificados (inferência; a documentação do Tailscale não trata disso). Escolher um nome de máquina neutro.
- **WebSocket:** a documentação do Funnel não o menciona, mas o handshake do Streamlit foi aceito pelo endereço público em 2026-11-16.
- **Rede do instituto:** com o computador ligado dentro do RAN, o túnel passa por fora do firewall do ICMBio. A coordenação do RAN deve estar ciente.

## Passo a passo

1. **Instalar o Tailscale** — feito em 2026-11-16, **no Windows** (recomendação da documentação para WSL 2; não instalar também dentro do WSL). O script chama o `tailscale.exe` de dentro do WSL, e o Windows alcança a porta do Streamlit por `127.0.0.1`.
2. **Dar um nome neutro à máquina** no painel do Tailscale (Machines).
3. **Ligar o login:** `AUTH_EXIGIR=tudo` no `.env` e reiniciar o backend.
4. **Criar as contas** com `scripts/infra/gerenciar_usuarios.py criar` e entregar os códigos de convite por um canal privado.
5. **Subir backend e interface** como de costume.
6. **Publicar:** `scripts/infra/publicar_funnel.sh`. Na primeira vez o Tailscale mostra um link para aprovar o Funnel na conta (ele liga o MagicDNS, os certificados HTTPS e o atributo `funnel`). O endereço público pode levar até uns 10 minutos para propagar.
7. **Testar de fora** (celular na rede móvel): abrir o endereço, ver a tela de acesso, entrar, perguntar, recarregar a página.
8. **Tirar do ar** quando não estiver em uso: `scripts/infra/publicar_funnel.sh parar`. Com `--bg`, o Funnel volta sozinho depois de reiniciar a máquina; por isso, parar é sempre explícito.

## Antes de incluir o SEI

O SEI é conteúdo interno. Enquanto o HerpIA estiver publicado na internet, a inclusão do SEI na base deve ser decidida pela equipe do RAN sabendo disso.
