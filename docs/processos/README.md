# Documentação de processos

Cada arquivo nesta pasta documenta um processo ou pipeline operacional do projeto: o que ele faz, quais são suas entradas/saídas, ferramentas usadas e como executá-lo.

## Convenção

- Use o `template.md` como ponto de partida para um novo processo.
- Atualize o arquivo do processo sempre que o passo a passo, as ferramentas ou as entradas/saídas mudarem — não crie um novo arquivo para a mesma etapa do pipeline.
- Se um processo ainda não foi implementado, mantenha o arquivo com status **A definir** e preencha o que já estiver decidido (ex.: entradas e saídas esperadas), mesmo sem os passos completos.

## Índice

| Processo | Etapa do pipeline | Status |
|----------|--------------------|--------|
| [Conexão PC de desenvolvimento ↔ PC servidor (SMB)](conexao_pc_dev_servidor.md) | Infraestrutura | 🔶 Em desenvolvimento |
| [Coleta das fontes web](coleta_fontes_web.md) | Fontes de dados → Extração | A definir |
| [**Coleta de PANs (Planos de Ação Nacional)**](coleta_pans_detalhado.md) | Fontes de dados → Extração | ✅ Em produção |
| [**Coleta do Programa Monitora**](coleta_monitora_detalhado.md) | Fontes de dados → Extração | ✅ Em produção |
| [**Coleta do SALVE**](coleta_salve_detalhado.md) | Fontes de dados → Extração | 🔶 Em execução (coleta completa rodando) |
| [**Extração de texto de PDFs (Monitora e PANs)**](extracao_pdfs.md) | Extração e limpeza | ✅ Em produção |
| [**Extração de texto das fichas SALVE**](extracao_texto_salve.md) | Extração e limpeza | ✅ Em produção |
| [Classificação de sensibilidade](classificacao_sensibilidade.md) | Classificação de sensibilidade | A definir |
| [**Seleção de processos do SEI para exportação**](selecao_processos_sei.md) | Fontes de dados → Extração | 🔶 Lista gerada; autorização pendente |
| [**Chunking dos documentos autorizados**](chunking.md) | Chunking | ✅ Em produção (Monitora/PANs/SALVE); 🔶 SEI e publicações pendentes |
| Geração de embeddings | Embeddings → Banco vetorial | A definir |
