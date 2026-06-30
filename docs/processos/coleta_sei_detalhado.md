# Catalogação do SEI/ICMBio — detalhamento técnico

- **Status:** Implementado e validado (catalogação); exportação de documentos pendente (manual)
- **Última atualização:** 2026-06-30

## O que é o SEI e o que são blocos internos

O **SEI (Sistema Eletrônico de Informações)** é o sistema do governo federal para gestão de processos administrativos. Toda tramitação burocrática do ICMBio — contratos, licenças, portarias, relatórios técnicos, atas, planos de ação — vira um processo SEI com número único (ex.: `02071.000061/2022-82`).

Um **bloco interno** é uma pasta de organização pessoal dentro do SEI, visível apenas para a unidade criadora. Serve para agrupar processos relacionados tematicamente sem alterar os processos em si. Os blocos do RAN/ICMBio refletem a organização temática da própria equipe — o que os torna um bom ponto de partida para identificar processos relevantes para o chatbot.

## O que foi implementado

### Script 1 — `listar_blocos_sei.py`

Lista todos os blocos internos da unidade e os processos em cada bloco.

**Saída:** `01_fontes_web/sei/blocos_internos.json`

```
{
  "data_coleta": "2026-06-30",
  "total_blocos": 43,
  "blocos": [
    {
      "numero": "201455",
      "descricao": "Comitê Científico do RAN",
      "atribuicao": "",
      "estado": "Gerado",
      "geradora": "RAN Goiânia-GO",
      "grupo": "Comitê Científico do RAN",
      "url_processos": "...",
      "processos": [
        {
          "Seq.": "1",
          "Processo": "02071.000061/2022-82",
          "Tipo": "COMITÊ",
          "Anotações": "Criação de Comitê Consultivo do RAN.",
          "Ações": ""
        }
      ]
    }
  ]
}
```

**Uso:**
```bash
source venv/bin/activate
set -a && source .env && set +a
python scripts/coleta/listar_blocos_sei.py

# Só listar blocos, sem buscar processos de cada um:
python scripts/coleta/listar_blocos_sei.py --sem-processos
```

**Credenciais necessárias no `.env`:**
```
SEI_LOGIN=seu_login_sei
SEI_SENHA=sua_senha_sei
```

---

### Script 2 — `listar_documentos_sei.py`

Para cada processo nos 16 blocos prioritários, navega até a página do processo no SEI e extrai a lista de documentos internos (título, ID, URL relativa) sem ler o conteúdo.

**Saída:** `01_fontes_web/sei/documentos_por_processo.json`

```json
{
  "data_coleta": "2026-06-30",
  "processos": [
    {
      "numero": "02071.000061/2022-82",
      "bloco": "Comitê Científico do RAN",
      "tipo": "COMITÊ",
      "anotacao": "Criação de Comitê Consultivo do RAN.",
      "documentos": [
        {
          "id": "12697418",
          "titulo": "Informação Técnica 6",
          "url_relativa": "controlador.php?acao=arvore_visualizar&..."
        }
      ],
      "total_documentos": 91,
      "erro": null
    }
  ]
}
```

**Uso:**
```bash
source venv/bin/activate
set -a && source .env && set +a

# Rodar completo (todos os 16 blocos prioritários):
python scripts/coleta/listar_documentos_sei.py

# Testar com um bloco específico:
python scripts/coleta/listar_documentos_sei.py --bloco "Comitê Científico do RAN"

# Retomar execução interrompida (pula processos já catalogados):
python scripts/coleta/listar_documentos_sei.py --retomar
```

**Tempo estimado:** ~20–30 min para todos os blocos prioritários (delay de 1,2s entre requisições).

---

## Como funciona tecnicamente

### Login no SIP

O SEI/ICMBio usa autenticação via SIP (sistema de login gov.br). O login é feito por POST com os campos:

| Campo | Valor |
|---|---|
| `txtUsuario` | login institucional |
| `pwdSenha` | senha |
| `hdnAcao` | `2` (reproduz o `onsubmit="acaoLogin(2)"` do botão ACESSAR) |
| `selOrgao` | `0` (ICMBio, pré-selecionado) |

O campo `hdnAcao=2` é crítico: sem ele, o login falha silenciosamente e a página retorna ao formulário sem mensagem de erro.

### infra_hash — por que não dá para acessar URLs diretamente

Todas as páginas internas do SEI incluem um parâmetro `infra_hash` único por sessão na URL. Tentar acessar uma URL interna sem o hash correto retorna "Link sem assinatura." O hash é gerado pelo servidor a cada ação e não pode ser previsto. Por isso, os scripts sempre navegam a partir da página principal (que já tem hashes válidos) ao invés de construir URLs manualmente.

### Estrutura da página de processo (iframes)

A página de um processo SEI usa dois iframes:
- **`ifrArvore`** → carrega `procedimento_visualizar`, que contém a árvore de documentos como JavaScript
- **`ifrVisualizacao`** → painel de visualização do documento selecionado (não é acessado pelos scripts)

### Extração da lista de documentos

A árvore de documentos é gerada como JavaScript dentro do `ifrArvore`. Cada documento aparece como:

```javascript
Nos[N] = new infraArvoreNo(
  "DOCUMENTO",    // tipo
  "17618270",     // id interno
  "PASTA5",       // pasta pai
  "controlador.php?acao=arvore_visualizar&...",  // url relativa
  "ifrVisualizacao",  // frame destino
  "Informação Técnica 6"  // título
);
```

Os scripts extraem esses dados via regex sem executar JavaScript. O título do documento é o 6º argumento do construtor.

### Pastas e ação ABRIR_PASTAS

Processos com muitos documentos são divididos em pastas (Pasta 1, Pasta 2, ...). Por padrão, apenas a última pasta está carregada. O script usa a ação `ABRIR_PASTAS` (quando disponível), que retorna a árvore completa com todas as pastas expandidas em uma única requisição.

## Blocos prioritários definidos

Os 16 blocos foram selecionados por relevância temática para o chatbot (herpetofauna, conservação, PANs, Monitora). Ver lista completa e justificativas em [`docs/decisoes/0004-criterios-selecao-documentos-sei.md`](../decisoes/0004-criterios-selecao-documentos-sei.md).

## Limitações

- O catálogo lista **títulos** de documentos, não seu conteúdo. Um processo com 90 documentos pode ter 80 ofícios e convites e apenas 10 documentos técnicos reais — é preciso análise humana para distinguir.
- Os títulos são os nomes dados pelos servidores ao salvar o documento no SEI. Qualidade dos títulos varia muito (alguns são genéricos como "Ofício 42", outros são descritivos como "Relatório de Campo - Quelônios RDS Mamirauá 2023").
- O login pode expirar em sessões longas. O script não tem reconexão automática — se houver erro de sessão no meio da execução, usar `--retomar` para continuar de onde parou.
- Processos restritos (com sigilo) retornam erro de acesso — são registrados com `"erro": "..."` no JSON de saída e não interrompem a execução.

## Próximas etapas

1. Analisar `documentos_por_processo.json` para identificar processos com documentos técnicos relevantes
2. Apresentar listagem à equipe do RAN para definir autorização de exportação por processo
3. Exportar documentos aprovados manualmente pelo SEI e salvar em `04_documentos_pendentes_avaliacao/sei/`
4. Avaliar sensibilidade (ver ADR 0002) e mover aprovados para `03_documentos_autorizados/sei/`
5. Extrair texto com o pipeline de PDFs existente (`scripts/processamento/extrair_texto_pdfs.py`)
