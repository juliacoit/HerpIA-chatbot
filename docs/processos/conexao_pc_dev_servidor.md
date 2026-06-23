# Conexão PC de desenvolvimento ↔ PC servidor (SMB)

- **Status:** Em desenvolvimento (bloqueado — sem rota de rede até o servidor; aguardando TI ajustar configuração de rede, sem necessidade de VPN)
- **Última atualização:** 2026-06-23
- **Responsável(eis):** Julia (desenvolvedora)

## Objetivo

Permitir que o PC de desenvolvimento acesse, via rede local, os documentos armazenados no PC servidor (`RAN_AvalFauna_FHF9703`, IP `10.62.62.191`) através de um compartilhamento SMB, para rodar os scripts de coleta/processamento (ex.: download dos PDFs dos PANs) sem precisar copiar arquivos manualmente entre as máquinas.

Essa conexão é importante porque:

- **Separação entre desenvolvimento e dados reais**: o código é escrito no PC de desenvolvimento, mas os dados do projeto (documentos, PDFs dos PANs, banco vetorial, banco de dados) ficam centralizados no PC servidor.
- **Segurança e organização dos dados**: manter os dados centralizados no servidor evita cópias duplicadas e descontroladas de documentos potencialmente sensíveis (ver regras de dados sensíveis no `CLAUDE.md`).
- **Preparação para uso real**: o chatbot, quando pronto, vai consultar essa base centralizada — validar essa conexão agora é testar a arquitetura cliente-servidor que será usada na prática.
- **Continuidade**: se outras pessoas ou um futuro servidor de produção precisarem acessar os mesmos dados, ter essa estrutura já validada evita retrabalho.

## Entradas

- Compartilhamento SMB `pans_dados` exposto pelo PC servidor (`//10.62.62.191/pans_dados`, caminho local no servidor `C:\compartilhado\pans_dados`).

## Saídas

- Montagem local em `/mnt/pans_dados` (WSL do PC de desenvolvimento), com symlink em `~/pans_dados`.
- Acesso de leitura/escrita usado pelos scripts em `scripts/coleta/` (ex.: `download_documentos_pans.py`).

## Ferramentas

- `cifs-utils` (driver CIFS/SMB para Linux/WSL).
- Scripts do repositório: `setup_wsl_mount.sh`, documentação em `SETUP_WSL_CONEXAO_SERVIDOR.md`.

## Passo a passo

1. Instalar dependência no PC de desenvolvimento (WSL): `sudo apt update && sudo apt install -y cifs-utils`.
2. Confirmar que o servidor está online e a porta SMB (445) está acessível: `ping 10.62.62.191` e `nc -zv 10.62.62.191 445`.
3. Montar o compartilhamento: `bash setup_wsl_mount.sh`, ou manualmente:
   ```bash
   sudo mount -t cifs //10.62.62.191/pans_dados /mnt/pans_dados \
     -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777,vers=2.1,nomultichannel
   ```
4. Validar o conteúdo montado: `ls -la /mnt/pans_dados` (deve conter `01_fontes_web`, `03_documentos_autorizados`, `07_processados`).
5. Rodar os scripts de coleta apontando para o caminho montado, ex.: `python scripts/coleta/download_documentos_pans.py --servidor /mnt/pans_dados --dry-run`.

## Frequência de execução

Sob demanda — a montagem é temporária (desfeita ao reiniciar o WSL); precisa ser refeita a cada nova sessão de trabalho, ou configurada via `/etc/fstab` para persistir (ver `SETUP_WSL_CONEXAO_SERVIDOR.md`).

## Observações sobre dados sensíveis

O compartilhamento dá acesso a pastas de documentos do projeto. Os diretórios `04_documentos_pendentes_avaliacao/` e `05_documentos_sensiveis_nao_indexar/` nunca devem ser processados automaticamente pelos scripts, independentemente do meio de acesso (local ou montagem remota).

## Histórico de troubleshooting (2026-06-19)

Na primeira tentativa de configurar essa conexão, foram encontrados três obstáculos em sequência, documentados aqui para referência futura:

1. **`sudo: A terminal is required to authenticate`** ao rodar `setup_wsl_mount.sh` via automação (Claude Code): comandos que pedem senha de `sudo` precisam ser executados em um terminal interativo real, não via ferramentas de automação sem TTY.
2. **`mount error(115): could not connect... Unable to find suitable address`**: erro comum do CIFS/SMB3 quando o servidor anuncia múltiplas interfaces de rede (recurso *multichannel* do SMB3) e o cliente tenta usar um endereço inalcançável, mesmo com a porta 445 acessível. Resolvido adicionando as opções de mount `vers=2.1,nomultichannel` (alternativa: `vers=3.0,nomultichannel`).
3. **Portal cativo de firewall (NAC)**: ao tentar acessar a rede onde está o servidor, o firewall institucional redirecionou automaticamente para uma página de autenticação e, após o login, ofereceu o download de um "Identity Agent" (comum em soluções de Network Access Control, ex.: FortiClient, Cisco ISE, Aruba ClearPass). Por se tratar de software com acesso à rede/identidade instalado na máquina de desenvolvimento — que lida com dados potencialmente sensíveis do projeto — a instalação foi pausada até confirmação do time de TI/infraestrutura do ICMBio sobre:
   - Se o agente é parte oficial da infraestrutura de rede do ICMBio.
   - Se é obrigatório instalá-lo para acesso contínuo, ou se a autenticação no portal já é suficiente para a sessão atual.

**Status no fim da sessão (2026-06-19):** aguardando resposta do TI antes de prosseguir com a instalação do Identity Agent e a montagem efetiva do compartilhamento.

## Atualização (2026-06-22) — autenticação no Identity Agent e indicação de VPN

1. **Autenticação concluída**: foi possível conectar à rede usando usuário e senha institucionais no portal/Identity Agent (sem precisar instalar nada adicional no PC de desenvolvimento).
2. **Teste de conectividade até o servidor (com Identity Agent ativo, sem VPN)**:
   ```bash
   ping -c 3 10.62.62.191      # 100% de perda de pacotes
   nc -zv 10.62.62.191 445     # sem resposta (timeout silencioso)
   ```
   Resultado: **sem rota até o servidor**, mesmo autenticado na rede via Identity Agent.
3. **Interpretação**: a falha indica segmentação de rede (VLANs) — o Identity Agent libera acesso a um segmento de rede, mas esse segmento aparentemente não tem rota até a VLAN onde o servidor (`10.62.62.191`) está. Não é um problema de porta bloqueada por host, e sim de roteamento/firewall entre segmentos, controlado pela infraestrutura do TI.
4. **Gerente de TI indicou configurar uma VPN** para viabilizar o acesso. Avaliada também a alternativa de instalar o Identity Agent no PC servidor — descartada por dois motivos:
   - Tecnicamente, o agente autentica o *dispositivo cliente* na rede; ele não cria rotas entre VLANs, então não resolveria o problema de roteamento identificado no teste acima.
   - O PC servidor armazena os dados reais do projeto (PDFs, banco vetorial, PostgreSQL — potencialmente sensíveis); instalar ali um software adicional de NAC com acesso à rede/identidade aumenta a superfície de risco e não deveria ser feito sem confirmação explícita do TI, na mesma linha de cautela já registrada para o PC de desenvolvimento.
5. **Próximo passo**: solicitar ao TI (a) o cliente VPN a ser usado, (b) o perfil/certificado de configuração, e (c) confirmação de que a VPN oferece rota até `10.62.62.191` especificamente (não apenas acesso geral à rede institucional). Repetir o teste de conectividade (`ping` + `nc -zv ... 445`) após conectar a VPN, antes de tentar o `mount` SMB.

**Status no fim da sessão (2026-06-22):** autenticação na rede via Identity Agent funcionando; sem rota até o servidor confirmada por teste; aguardando TI fornecer configuração de VPN.

## Atualização (2026-06-23) — conversa com técnico de redes: VPN não é necessária

1. **Conversa com o técnico de redes do ICMBio**: ao relatar o resultado dos testes de conectividade (sem rota até `10.62.62.191`, ver atualização de 2026-06-22), o técnico informou que, em princípio, **não há necessidade de VPN** — a rede cabeada (onde está o servidor) se comunica normalmente com a rede wifi (usada pelo PC de desenvolvimento). Segundo ele, o problema é **apenas uma questão de configuração** de rede a ser ajustada do lado da infraestrutura, não uma limitação estrutural de segmentação que exigisse VPN.
2. **Recomendação adicional do técnico**: instalar **Linux no PC servidor** (em vez de manter o sistema atual). Motivo específico não detalhado nesta conversa — registrar para confirmar com o técnico antes de agir, já que essa mudança no PC servidor teria impacto maior (reinstalação de SO, dados/configuração já existentes no servidor).
3. **Implicação para o plano anterior**: a indicação de VPN do gerente de TI (2026-06-22) parece ter sido substituída pela orientação do técnico de redes (ajuste de configuração, sem VPN). Ainda não há detalhes de qual configuração específica precisa ser ajustada nem por quem (TI ou desenvolvedora) — a confirmar.

**Próximos passos:**
- Confirmar com o técnico de redes **qual configuração** precisa ser ajustada (ex.: rota estática, regra de firewall entre VLANs/segmentos, configuração de switch) e quem é responsável por aplicá-la.
- Perguntar o motivo específico da recomendação de instalar Linux no PC servidor antes de decidir se/quando migrar o SO — **não realizar essa migração sem autorização explícita e confirmação dos detalhes**, dado que o servidor já tem dados e configuração em uso.
- Repetir o teste de conectividade (`ping` + `nc -zv ... 445`) assim que a configuração de rede for ajustada, antes de tentar o `mount` SMB.

**Status no fim da sessão (2026-06-23):** técnico de redes indicou que VPN não é necessária e que o bloqueio é uma questão de configuração; recomendou instalar Linux no PC servidor (motivo a confirmar); aguardando detalhamento da configuração necessária.

## Atualização (2026-06-23, mesma sessão) — reteste após reinício local

Repetido o teste de conectividade após reiniciar apenas o PC de desenvolvimento (WSL), sem nenhuma mudança de configuração por parte do TI:

```bash
ping -c 3 10.62.62.191      # 100% de perda de pacotes
nc -zv 10.62.62.191 445     # timeout
```

Resultado: mesmo bloqueio de antes — sem rota até o servidor. Confirma que o problema é de configuração de rede do lado da infraestrutura (ainda não ajustada), e não algo resolvível por reinício local. Continua aguardando o técnico de redes detalhar e aplicar o ajuste necessário.
