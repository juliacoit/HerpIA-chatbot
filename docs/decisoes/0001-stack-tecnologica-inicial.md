# 0001. Stack tecnológica inicial

- **Status:** Aceita — parcialmente substituída pelo [ADR 0006](0006-escolha-temporaria-llm-geracao.md) no item "API externa de LLM" (geração via LLM local com Ollama)
- **Data:** 2026-06-16
- **Responsável(eis):** Equipe do projeto (RAN/ICMBio, CNPq, CIEE)

## Contexto

O chatbot precisa de um pipeline de RAG (Retrieval-Augmented Generation) completo: extração de texto de documentos (incluindo PDFs escaneados), geração e armazenamento de embeddings, recuperação semântica/híbrida, backend de API, e uma interface para uso pelos técnicos e gestores do RAN/ICMBio. O projeto tem até um ano de prazo e pode usar API externa de LLM, desde que sejam respeitadas regras de segurança sobre dados sensíveis.

## Decisão

Adotar a seguinte stack:

- **Python** como linguagem principal.
- **LlamaIndex ou LangChain** para orquestração do RAG.
- **Qdrant** como banco vetorial.
- **PostgreSQL** para dados estruturados, metadados, usuários, logs e feedback.
- **FastAPI** para o backend.
- **Streamlit** para o protótipo inicial de interface.
- **PyMuPDF** para extração de texto de PDFs.
- **Tesseract OCR** para PDFs escaneados, quando necessário.
- **Docker** para implantação.
- **API externa de LLM** (ex.: OpenAI API), enviando apenas trechos recuperados e autorizados — nunca documentos completos.
- **Embeddings** para busca semântica, com possibilidade de **busca híbrida** (semântica + palavras-chave).

## Consequências

- O item "API externa de LLM" foi substituído, por ora, por LLM local via Ollama — ver [ADR 0006](0006-escolha-temporaria-llm-geracao.md). A busca híbrida continua só como possibilidade: o backend atual usa apenas busca densa (BGE-M3), e a híbrida está pendente no [roadmap](../roadmap.md) (Fase 6), condicionada à busca densa se mostrar insuficiente.
- A escolha entre LlamaIndex e LangChain ainda está aberta e deve ser decidida em um ADR específico antes da implementação do pipeline de RAG.
- O uso de API externa de LLM exige que o filtro de sensibilidade (ver [0002](0002-classificacao-de-sensibilidade-em-pastas.md)) esteja implementado **antes** de qualquer chamada externa.
- Qdrant e PostgreSQL precisarão de infraestrutura própria (local ou em contêiner via Docker) — a ser detalhada em um ADR de infraestrutura/implantação.
