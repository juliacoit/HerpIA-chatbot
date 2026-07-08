# Escolha do modelo de embeddings

- **Status:** Decisão temporária tomada (BGE-M3, só para testes) — decisão final de produção segue pendente com a equipe (Fase 5.1 do [`docs/roadmap.md`](../roadmap.md))
- **Última atualização:** 2026-07-08
- **Decisão temporária registrada em ADR:** [`docs/decisoes/0005-escolha-temporaria-modelo-embeddings.md`](../decisoes/0005-escolha-temporaria-modelo-embeddings.md) — enquanto a equipe não decide se há orçamento para custear uma API (Opção A/B), o modelo **BGE-M3** (Opção C) está sendo usado para gerar embeddings de teste sobre os chunks já existentes e avaliar a qualidade da recuperação. Essa escolha é descartável e não compromete a decisão final — se a equipe optar por API paga, os vetores de teste são regenerados do zero.

## Objetivo deste documento

Explicar, sem jargão técnico desnecessário, o que são embeddings, por que o
chatbot depende de um modelo para gerá-los, e apresentar as opções concretas
para a equipe do RAN decidir junto qual usar. Não é uma decisão só de
engenharia — envolve custo, dependência de serviços externos e onde os dados
do projeto circulam, então cabe à equipe pesar essas trocas.

---

## O que são embeddings

Um **embedding** é uma forma de transformar um texto (uma frase, um parágrafo,
uma pergunta) em uma lista de números — um vetor. Esse vetor é construído de
um jeito que captura o **significado** do texto, não as palavras exatas.

Um exemplo com dados reais do projeto: as fichas do SALVE têm um trecho como
"tendência populacional em declínio" e outro trecho, em um PAN diferente, diz
"a espécie vem perdendo indivíduos ao longo dos anos". São frases com palavras
completamente diferentes, mas com o mesmo significado. Um embedding bem feito
transforma essas duas frases em vetores **próximos entre si** — mesmo sem
nenhuma palavra em comum. Já uma frase sobre "cronograma de reuniões do
comitê" viraria um vetor **distante** dos outros dois.

É essa propriedade — textos parecidos em significado geram vetores próximos —
que permite buscar por **sentido**, e não só por palavra-chave exata. Uma
busca por palavra-chave tradicional (como `Ctrl+F` ou um `WHERE texto LIKE`)
só encontra "declínio populacional" se o documento usar exatamente essas
palavras. Busca por embeddings encontra o trecho certo mesmo que ele use
outras palavras para dizer a mesma coisa — essencial num acervo com centenas
de documentos escritos por autores diferentes, em anos diferentes, cada um
com seu vocabulário.

## Por que o chatbot precisa disso

O chatbot do RAN é um sistema de **RAG** (Retrieval-Augmented Generation —
geração aumentada por recuperação). Ele funciona em duas etapas, sempre que
alguém faz uma pergunta:

1. **Recuperação (Retrieval):** o sistema busca, entre os milhares de trechos
   (`chunks`) já extraídos do Monitora, PANs e SALVE, os que são mais
   relevantes para a pergunta feita.
2. **Geração (Generation):** só depois de recuperar os trechos certos, o
   sistema monta uma resposta com base **apenas neles**, citando a fonte de
   cada informação.

A etapa 1 é a que depende de embeddings. Sem eles, o sistema teria que
adivinhar quais dos ~59 mil chunks já gerados (Fase 4) são relevantes para
cada pergunta — e faria isso por coincidência de palavras, não de sentido,
o que erraria bastante em perguntas escritas de forma diferente do documento
original.

Na prática, o fluxo com embeddings funciona assim:

```
Pergunta do usuário
   → vira um embedding (mesmo modelo usado nos documentos)
   → comparada com os embeddings de todos os chunks já armazenados no Qdrant
   → os chunks com vetores mais próximos são recuperados
   → só esses chunks (já autorizados) são enviados ao modelo de linguagem para gerar a resposta
```

## Por que precisamos escolher um modelo (e não usar um "padrão")

Não existe um único embedding universal — cada **modelo** de embeddings tem
seu próprio jeito de transformar texto em vetor, treinado sobre um conjunto de
dados diferente. Modelos diferentes:

- Produzem vetores de **tamanhos diferentes** (ex.: 768, 1024, 1536 números
  por vetor) — isso define a configuração do banco vetorial (Qdrant).
- Têm **qualidade diferente** para português e para vocabulário técnico-científico
  (nomes latinos de espécies, termos jurídico-administrativos dos PANs).
- Têm **custo e infraestrutura diferentes** — alguns são pagos por uso via API,
  outros rodam localmente sem custo por token, mas exigem processamento próprio.

Essa escolha também é **cara de reverter**: se trocarmos de modelo depois de
indexado, os vetores de um modelo não são compatíveis com os de outro — seria
necessário gerar os embeddings de todos os ~59 mil chunks de novo. Por isso
faz sentido decidir com calma agora, antes de indexar no Qdrant (Fase 5.2/5.3).

## Sobre o envio de dados a uma API externa

Se a escolha for um modelo via API (OpenAI), o texto de cada chunk é enviado
para o serviço externo gerar o vetor. Isso é compatível com as regras de dados
sensíveis do projeto (ver `CLAUDE.md`) **porque os chunks já vêm exclusivamente
de `03_documentos_autorizados/`** — ou seja, já passaram pelo filtro de
sensibilidade antes de chegar aqui. Nenhum documento de
`04_documentos_pendentes_avaliacao/` ou `05_documentos_sensiveis_nao_indexar/`
entra nesse fluxo. Ainda assim, é uma escolha relevante para a equipe: envolve
decidir se o projeto está confortável em enviar o conteúdo autorizado a um
serviço de terceiros, ou se prefere manter tudo dentro da própria
infraestrutura.

## As opções

| | **A. OpenAI `text-embedding-3-small`** | **B. OpenAI `text-embedding-3-large`** | **C. Modelo open-source local** (ex.: `BAAI/bge-m3` ou `intfloat/multilingual-e5-large` — [comparação detalhada entre os dois](#aprofundando-a-opção-c-comparando-os-dois-modelos-candidatos)) |
|---|---|---|---|
| Onde roda | API da OpenAI (externo) | API da OpenAI (externo) | Na própria máquina/servidor do projeto |
| Dados saem do projeto? | Sim — texto do chunk enviado à API | Sim — texto do chunk enviado à API | Não |
| Tamanho do vetor | ~1536 (ajustável) | ~3072 | ~1024 |
| Qualidade em português | Boa (multilíngue) | Muito boa (multilíngue) | Boa a muito boa, dependendo do modelo (treinados especificamente para busca multilíngue) |
| Custo estimado (indexar os ~59 mil chunks de hoje) | ≈ US$ 0,60 | ≈ US$ 3,90 | R$ 0 (sem custo por token) |
| Custo recorrente (nova pergunta / atualização semestral) | Poucos centavos por vez | Poucos centavos por vez | R$ 0, mas consome processamento local |
| Infraestrutura extra necessária | Nenhuma (só a chave de API já prevista em `.env`) | Nenhuma | Instalar `sentence-transformers`, baixar o modelo (~1–2 GB), processamento em CPU (viável, dado que a atualização da base é semestral, não é preciso ser instantâneo) |
| Facilidade de implementação | Alta | Alta | Média (mais peças para manter) |
| Dependência de terceiros | Sim (API, preço e disponibilidade da OpenAI) | Sim | Não |

## Ponto de partida para a conversa

Uma leitura possível, para começar a discussão (não é a decisão final):

- Se a equipe já aceita usar API externa da OpenAI para gerar as respostas do
  chatbot na Fase 6, usar a mesma API para embeddings (Opção A) simplifica a
  implementação e o custo é baixo o suficiente para não ser um fator decisivo.
- Se a preferência institucional for manter os dados do projeto sempre dentro
  da própria infraestrutura (mesmo sendo dados já autorizados/públicos), a
  Opção C evita qualquer envio externo, ao custo de mais complexidade de
  manutenção.
- A Opção B (modelo "large" da OpenAI) tende a ser qualidade acima do
  necessário para o volume e o domínio deste projeto, com custo maior — só
  faria sentido se a Opção A mostrar limitações na prática.

## Aprofundando a Opção C: comparando os dois modelos candidatos

A Opção C citava dois modelos possíveis sem detalhar as diferenças entre eles.
Esta seção compara `BAAI/bge-m3` e `intfloat/multilingual-e5-large` — os dois
são gratuitos, rodam localmente e suportam português — explicando os termos
técnicos ao longo do caminho, para quem não trabalha com isso no dia a dia.

### Termos usados nesta comparação

- **Token:** a menor unidade de texto que o modelo processa — geralmente um
  pedaço de palavra (não uma palavra inteira). Em português, 1000 tokens
  equivalem a aproximadamente 700–750 palavras.
- **Contexto máximo:** quantos tokens o modelo consegue "ler" de uma vez antes
  de cortar o texto. Se um chunk for maior que esse limite, o restante é
  simplesmente ignorado ao gerar o embedding — sem aviso. Por isso importa que
  o contexto do modelo seja folgado em relação ao tamanho dos chunks já usados
  em produção (~500 tokens / ~2000 caracteres, ver
  [`chunking.md`](chunking.md)).
- **Busca densa (dense retrieval):** o método "padrão" de busca semântica
  descrito nas seções acima — compara o vetor da pergunta com o vetor de cada
  chunk. Encontra bem significado, mas pode falhar em buscas por termos exatos
  (siglas, nomes científicos em latim, números de processo SEI).
- **Busca esparsa (sparse retrieval):** busca por palavras-chave, no estilo do
  BM25 usado por buscadores tradicionais. Boa para termos exatos, mas não
  entende sinônimos ou contexto — o oposto da busca densa.
- **Busca híbrida:** combina busca densa + busca esparsa, somando os pontos
  fortes de cada uma. É o recurso citado como desejável no
  [`docs/roadmap.md`](../roadmap.md) (Fase 6).
- **Multi-vetor (ColBERT):** em vez de um único vetor por chunk, o modelo gera
  um vetor por palavra/token, permitindo comparações mais finas entre pergunta
  e trecho. Mais preciso, porém mais caro computacionalmente — normalmente
  usado só para reordenar (re-ranking) resultados já encontrados, não na busca
  inicial.
- **Benchmarks (MTEB, MIRACL, MKQA, MLDR, Mr. TyDi):** conjuntos de testes
  padronizados que a comunidade de IA usa para comparar modelos de embedding
  em diferentes idiomas e tarefas de busca. Quando um modelo "tem bom
  desempenho no MIRACL", significa que ele foi testado formalmente em buscas
  multilíngues com resultado consistente — não é apenas divulgação do
  fabricante.
- **MRR@10 (Mean Reciprocal Rank):** uma métrica desses benchmarks — mede, em
  média, em que posição do ranking de resultados a resposta certa apareceu
  (quanto mais perto do 1º lugar, melhor). Valores mais altos = melhor.
- **Parâmetros do modelo:** o "tamanho" do modelo (quantos números internos
  ele ajustou durante o treinamento). Modelos maiores tendem a captar mais
  nuance, mas exigem mais processamento (CPU/GPU) e memória para rodar.

### Comparação lado a lado

| Característica | BGE-M3 | multilingual-e5-large |
|---|---|---|
| Desenvolvido por | BAAI (Beijing Academy of Artificial Intelligence) | Microsoft (via intfloat) |
| Modelo-base | XLM-RoBERTa (versão estendida) | XLM-RoBERTa-large |
| Dimensão do embedding | 1024 números por vetor | 1024 números por vetor |
| Contexto máximo | 8192 tokens (~6 mil palavras) | 512 tokens (~360 palavras) |
| Idiomas suportados | Mais de 100 | 100 (herdados do XLM-RoBERTa) |
| Tamanho do modelo | ~560 milhões de parâmetros | ~560 milhões de parâmetros |
| Licença | MIT (uso livre, inclusive comercial) | MIT (uso livre, inclusive comercial) |
| Tipos de busca que o modelo faz sozinho | Densa **+** esparsa **+** multi-vetor, tudo no mesmo modelo | Só densa |
| Forma de usar | Texto direto, sem preparo especial | Exige adicionar o prefixo `"query: "` no texto da pergunta e `"passage: "` no texto de cada chunk antes de gerar o embedding |
| Benchmarks em que foi avaliado | MIRACL, MKQA, MLDR (busca multilíngue e textos longos) | Mr. TyDi (MRR@10 de 70.5 em 11 idiomas) |
| Ano de lançamento | 2024 | 2023 |

### BGE-M3 em mais detalhe

O nome "M3" vem de três capacidades combinadas: **M**ulti-linguagem,
**M**ulti-funcionalidade (densa + esparsa + multi-vetor no mesmo modelo) e
**M**ulti-granularidade (processa desde frases curtas até documentos de até
8192 tokens sem precisar cortar o texto). Na prática, um único modelo já
entrega os ingredientes da busca híbrida, sem precisar manter um segundo
sistema de busca por palavras-chave em paralelo (ex.: um índice BM25 separado
por fora do Qdrant).

### multilingual-e5-large em mais detalhe

Modelo mais estabelecido e testado em produção há mais tempo, mas com duas
limitações relevantes para este projeto:

1. **Contexto de 512 tokens:** qualquer texto além disso é cortado
   silenciosamente — o modelo não avisa, apenas ignora o excedente. Como o
   projeto já planeja chunks de ~500 tokens, o risco na prática é baixo, mas
   sobra pouca margem (ex.: cabeçalhos de metadados adicionados a cada chunk,
   como nome da espécie ou número do processo, "roubam" espaço do limite).
2. **Prefixos obrigatórios (`"query: "` / `"passage: "`):** é preciso lembrar
   de aplicar o prefixo certo em cada lugar do código — um na hora de indexar
   os chunks, outro na hora de embutir a pergunta do usuário. Esquecer isso em
   um dos dois lugares não gera erro visível: a busca continua funcionando,
   só que com qualidade pior, o que torna o bug difícil de perceber depois.

### Leitura para a conversa, especificamente entre os dois modelos

Se a equipe optar pela Opção C (modelo local), a leitura é: **BGE-M3** tende a
ser a escolha mais robusta, por dois motivos concretos —

1. Já entrega busca híbrida nativamente, o que evita ter que montar um
   segundo sistema de busca por palavras-chave separado quando a Fase 6
   quiser esse recurso.
2. Não depende de convenção de prefixo para funcionar corretamente, o que
   reduz uma fonte de erro silencioso no código de indexação/busca.

O trade-off: se a prioridade for manter a Fase 5 o mais simples possível por
enquanto (só busca densa, sem pensar em híbrida agora), o e5-large é uma
opção mais "enxuta" — um modelo que só faz uma coisa, sem a decisão extra de
como armazenar os vetores esparsos no Qdrant. Os dois modelos têm porte e
exigência de hardware equivalentes (~560M parâmetros cada), então a escolha
entre eles não muda os requisitos de CPU/GPU/memória da infraestrutura — a
diferença de custo computacional relevante é entre a Opção C como um todo e
as opções A/B (API paga), não entre os dois modelos locais.

## Próximos passos

A escolha temporária (BGE-M3, para testes) já está registrada em
[ADR 0005](../decisoes/0005-escolha-temporaria-modelo-embeddings.md). Este
documento continua valendo como material de apoio para a **decisão final**
entre as opções A/B/C, que segue pendente com a equipe.

1. Implementar `scripts/indexacao/indexar_chunks.py` usando BGE-M3
   (`sentence-transformers` ou `FlagEmbedding`) — Fase 5.3.
2. Definir a dimensão do vetor (1024, para BGE-M3) e a métrica de
   similaridade da coleção no Qdrant (Fase 5.2).
3. Indexar os chunks já existentes e avaliar a qualidade da recuperação.
4. Levar o resultado do teste + a necessidade de orçamento para API para a
   equipe decidir entre manter BGE-M3 em produção ou migrar para a Opção
   A/B — quando essa decisão final sair, atualizar o ADR 0005 e o
   `requirements.txt` (`sentence-transformers`/`FlagEmbedding` já cobrem a
   Opção C; `openai` seria necessário só se a equipe optar por A/B).
