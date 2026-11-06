# 0010. Exportação automatizada dos documentos técnicos do SEI

- **Status:** Aceita
- **Data:** 2026-11-06
- **Responsável(eis):** Julia Coite (titular da credencial do SEI usada)

## Contexto

O [ADR 0004](0004-criterios-selecao-documentos-sei.md) definiu que os scripts do projeto
acessam o SEI só para ler metadados de navegação (títulos e IDs) e nunca o conteúdo dos
documentos. A exportação ficaria manual, pela interface do SEI.

Em 2026-11-06 a equipe do RAN validou a seleção: 173 processos e 1.197 documentos
técnicos autorizados para exportação. À mão, a estimativa era de 9 a 15 horas (3 a 5
minutos por processo, sem medição real).

Alternativas consideradas:

1. **Exportação manual pela interface do SEI.** Não muda regra nenhuma, mas toma horas de
   trabalho repetitivo.
2. **Webservices oficiais do SEI.** Exigem cadastro do sistema pela TI do ICMBio, o que a
   equipe do RAN descartou (quer independência da TI).
3. **Script com a credencial da Júlia**, reaproveitando o login e a navegação que já
   existiam em `scripts/coleta/listar_documentos_sei.py`.

## Decisão

Adotar a alternativa 3. A Júlia autorizou, em 2026-11-06, o uso da sua credencial do SEI
para baixar automaticamente os documentos técnicos dos processos autorizados.

É uma **exceção** à regra do ADR 0004: o script de exportação lê e salva o conteúdo dos
documentos. A regra continua valendo para os outros scripts do SEI.

O script `scripts/coleta/exportar_documentos_sei.py` funciona com estas travas:

- **Só leitura.** Requisições só às ações de leitura de uma lista fechada
  (`protocolo_pesquisa_rapida`, `procedimento_trabalhar`, `procedimento_visualizar`,
  `arvore_visualizar`, `documento_download_anexo`, `documento_visualizar`). A página de
  um documento no SEI também traz ações que alteram o processo (assinar, excluir, enviar
  e-mail, dar ciência); qualquer URL fora da lista é recusada antes da requisição.
- **Só os documentos autorizados.** Cada processo é aberto pelo número na pesquisa rápida;
  da árvore, só são baixados os documentos de `processos_docs.csv`, identificados pelo
  número SEI que aparece entre parênteses no título.
- **Restritos e sigilosos ficam de fora.** Um documento cujo nó na árvore mencione
  "restrito" ou "sigiloso" é pulado e registrado. A decisão sobre documentos de acesso
  restrito continua em aberto (ADR 0004). Documentos cancelados no SEI também são pulados.
- **Ritmo de uso humano.** Pausa de 1,5 s entre requisições e uma sessão por execução.
- **Nada do conteúdo no terminal.** O script imprime só números, contagens, tipos e
  tamanhos. Isso importa porque a saída do terminal pode ser lida por um assistente de IA
  com API externa, e os documentos ainda não passaram pela avaliação de sensibilidade.
- **Destino de pendentes.** Os arquivos vão para
  `04_documentos_pendentes_avaliacao/sei/<processo>/`, fora do git, e só chegam a
  `03_documentos_autorizados/sei/` depois da avaliação de sensibilidade do ADR 0002.
- **Rastreável e retomável.** O manifesto `01_fontes_web/sei/exportacao_sei_manifesto.json`
  (fora do git) registra, por documento, o status, o arquivo, o tamanho e o SHA-256. Uma
  nova execução pula o que já foi baixado.

## Piloto (2026-11-06)

Rodado nos 10 processos do piloto (49 documentos técnicos), escolhidos por
`scripts/coleta/montar_piloto_exportacao_sei.py`:

- 46 baixados, 2 cancelados no SEI, 1 não encontrado na árvore atual do processo;
- 19 PDF (todos válidos), 9 documentos do editor do SEI em HTML, 13 planilhas Excel,
  2 Word, 3 compactados (2 ZIP e 1 7z);
- cerca de 7,5 minutos no total, 133 MB.

Achados no caminho:

- O SEI do ICMBio mudou de endereço: `sei.icmbio.gov.br` redireciona (301) para
  `icmbio.sei.gov.br`. O redirecionamento transforma o POST do login em GET e o login
  falhava sem mensagem; os scripts passaram a usar o endereço novo.
- Os IDs internos dos documentos mudaram em relação ao catálogo de julho (o SEI parece ter
  sido migrado). O número SEI do documento, que aparece no título, continua o mesmo; por
  isso a correspondência é feita por ele.
- Arquivos que o navegador não exibe (ZIP, tipo não identificado) não têm o link de
  download na propriedade `src` do nó da árvore, e sim dentro do HTML do nó.

## Consequências

- A exportação dos 1.197 documentos leva poucas horas de execução sem acompanhamento, em
  vez de 9 a 15 horas de trabalho manual.
- Os acessos ficam registrados no SEI em nome da Júlia. O volume é o de um usuário
  abrindo documentos em sequência, sem paralelismo, mas o risco de a conta ser
  questionada ou bloqueada por uso automatizado é dela, e foi aceito por ela.
- A extração de texto precisa tratar formatos que o pipeline de PDFs não cobre: HTML do
  editor do SEI, planilhas, Word e arquivos compactados.
- A avaliação de sensibilidade documento a documento continua obrigatória antes de
  qualquer indexação.
- Se o SEI mudar a estrutura da árvore, o script deixa de encontrar os documentos e
  registra `nao_encontrado_na_arvore` ou `sem_url_de_download`, sem baixar nada errado.
