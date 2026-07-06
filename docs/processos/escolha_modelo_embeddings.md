# Escolha do modelo de embeddings

- **Status:** Em discussão com a equipe — decisão pendente (Fase 5.1 do [`docs/roadmap.md`](../roadmap.md))
- **Última atualização:** 2026-07-06
- **Vira ADR quando decidido:** este documento deve virar `docs/decisoes/0005-escolha-modelo-embeddings.md` assim que a equipe fechar a escolha (ver [`docs/decisoes/template.md`](../decisoes/template.md))

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

| | **A. OpenAI `text-embedding-3-small`** | **B. OpenAI `text-embedding-3-large`** | **C. Modelo open-source local** (ex.: `BAAI/bge-m3` ou `intfloat/multilingual-e5-large`) |
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

## Próximos passos após a decisão

1. Registrar a escolha como ADR (`docs/decisoes/0005-...md`), substituindo este documento.
2. Atualizar `requirements.txt` (`openai` ou `sentence-transformers`, conforme a escolha).
3. Definir a dimensão do vetor e a métrica de similaridade da coleção no Qdrant (Fase 5.2).
4. Implementar `scripts/indexacao/indexar_chunks.py` (Fase 5.3).
