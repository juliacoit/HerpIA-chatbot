# Conexão PC de desenvolvimento ↔ PC servidor (SMB)

- **Status:** Em desenvolvimento (bloqueado — aguardando confirmação do TI sobre Identity Agent)
- **Última atualização:** 2026-06-19
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

**Status no fim da sessão:** aguardando resposta do TI antes de prosseguir com a instalação do Identity Agent e a montagem efetiva do compartilhamento.
