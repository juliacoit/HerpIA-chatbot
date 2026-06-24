# Mapeamento técnico do SALVE (preparação da coleta)

- **Status:** Em desenvolvimento (mapeamento concluído, script de coleta ainda não implementado)
- **Última atualização:** 2026-06-24
- **Responsável(eis):** Investigação manual via `curl` (sem script ainda)

## Objetivo

Mapear a estrutura técnica real do SALVE (Sistema de Avaliação do Risco de Extinção da Biodiversidade) para viabilizar um script de coleta de **metadados** das fichas de espécies — com foco em herpetofauna (Répteis e Anfíbios) para o RAN —, seguindo o mesmo padrão de saída (JSON por categoria/grupo) usado em `coleta_monitora.py` e `coleta_pans.py`.

Este documento registra o que foi descoberto até agora. O script de coleta (`scripts/coleta/coleta_salve.py`) ainda **não foi escrito** — este é o trabalho de mapeamento que o precede.

## Contexto: por que o SALVE precisou de uma investigação diferente

Diferente do Monitora e dos PANs (páginas HTML tradicionais do gov.br, com `requests` + `BeautifulSoup` bastando), o SALVE é servido por **duas aplicações Vue.js diferentes**, sem conteúdo no HTML inicial. A análise anterior (`coleta_fontes_web.md`, 2026-06-16) tinha identificado isso como bloqueador e citava uma pista de uma URL de API (`/salve/api/pdf/doi/...`). Esta sessão (2026-06-24) destravou o bloqueio: em vez de simular cliques com Playwright/Selenium, foi possível **inspecionar os arquivos JS servidos** (`app.<hash>.js` e os módulos do `salve-consulta`) com `curl` e `grep`, encontrando diretamente as chamadas de API que o front-end faz. A API pública, inclusive, **se autodocumenta**: `GET /salve-api/public/` retorna uma página HTML com a lista de todos os endpoints e parâmetros aceitos.

## Os três módulos do SALVE (confirmado)

| Módulo | URL | Autenticação | Relevância para coleta |
|---|---|---|---|
| **Portal público** | `salve.icmbio.gov.br/` (SPA Vue CLI, `app.<hash>.js`) | Nenhuma | **Principal fonte**: fichas de espécies com categoria de risco, distribuição, conservação etc. |
| **Consulta pública/participativa** | `salve.icmbio.gov.br/salve-consulta/` (Vue 2 + Grails/GSP) | Visualização pública; contribuir exige login SICA-e | Secundário: lista de espécies em "consulta ampla" (período aberto a contribuições da sociedade) |
| **Gestão interna** | `salve.icmbio.gov.br/salve/` | Login institucional (SICA-e) | Fora de escopo — não investigado, não é fonte pública |

## Módulo 1 — Portal público: API REST `salve-api`

**Base URL:** `https://salve.icmbio.gov.br/salve-api/public/`

Descoberta: o bundle `https://salve.icmbio.gov.br/js/app.<hash>.js` define `baseURL:"https://salve.icmbio.gov.br/salve-api/public/"` para a instância do axios. A própria API expõe sua documentação em `GET /salve-api/public/` (HTML simples, sem autenticação) — é a fonte mais confiável de endpoints e parâmetros, mais completa do que o que dá para extrair só lendo o JS minificado.

### Endpoint principal para a coleta: `/search`

```
GET /salve-api/public/search?<parâmetros>
```

Parâmetros relevantes confirmados (testados nesta sessão):

- `q=<termo>` — busca textual por nome científico/comum (ex.: `q=Puma concolor`).
- `grupoIds=<id1>,<id2>` — filtra por grupo taxonômico. **IDs confirmados via `/selectOptions`:**

  | Grupo | id |
  |---|---|
  | Répteis | `1266` |
  | Anfíbios | `1257` |
  | Mamíferos | `1262` |
  | Aves | `1258` |
  | Peixes Continentais | `1264` |
  | Peixes Marinhos (ósseos) | `1265` |
  | Tubarões e Raias | `1856` |
  | Invertebrados Terrestres | `1261` |
  | Invertebrados de Água Doce | `1259` |
  | Invertebrados Marinhos | `1260` |

  → Para o RAN, o filtro de coleta é `grupoIds=1266,1257`.
- `categoriaIds=<id1>,<id2>` — filtra por categoria de risco (IDs também em `/selectOptions`, campo `categories`).
- `publicada=S|N`, `endemicaBrasil=S|N`, `taxonId=`, `regiaoIds=`, `estadoIds=`, `biomaIds=`, `panIds=`, `ucIds=`, `ameacaIds=`, `baciaIds=`, `presencaListaVigente=S` — filtros adicionais (não testados individualmente, mas documentados no próprio endpoint).
- **Paginação:** primeira chamada só com `paginationPageSize=<N>`; chamadas seguintes devem reenviar `paginationPageNumber`, `paginationTotalPages` e `paginationTotalRecords` (valores recebidos na resposta anterior). Confirmado: `grupoIds=1266,1257` retorna **2086 fichas no total** (Répteis + Anfíbios), 418 páginas de 5 registros — ou seja, dá para paginar com tamanho de página maior (ex.: 100) para reduzir o número de requisições.
- `export=row` (planilha, com opção de envio por e-mail via `email=`), `export=pdf`, `export=reg` (registros de ocorrência) — geram um job assíncrono; status/download via `GET /salve-api/public/job/job-xxxxx`. **Não testado** nesta sessão (evitar disparar jobs de exportação em massa sem necessidade).

Cada item retornado pelo `/search` traz, entre outros campos: `nm_cientifico`, `no_comum`, `cd_categoria_final` (sigla IUCN/SALVE: LC, NT, VU, EN, CR, etc.), `de_categoria_final_completa`, `ds_grupo_salve`, `no_bioma`, `de_periodo_avaliacao`, `cd_situacao_ficha`, `ds_doi`, e o campo-chave **`id_ficha`** — um identificador opaco (não é o ID numérico interno; parece ser um token codificado/criptografado pelo backend) usado para buscar o conteúdo completo da ficha.

### Endpoint de conteúdo da ficha: `/fichaHtml`

```
GET /salve-api/public/fichaHtml?idFicha=<id_ficha>&section=<secao>
```

Cada seção retorna um JSON com o HTML/texto daquela parte da ficha. Seções confirmadas (testadas nesta sessão para *Acanthochelys macrocephala*, categoria VU):

| `section` | Conteúdo |
|---|---|
| `header` | Nome científico, categoria final, data da última avaliação, data de publicação, justificativa da categoria |
| `taxonomicClassification` | Árvore taxonômica completa (Reino → Espécie) + nomes antigos/sinônimos |
| `distribution` | Distribuição global e nacional (texto livre) |
| `naturalHistory` | História natural |
| `population` | Dados de população |
| `threats` | Ameaças |
| `uses` | Usos |
| `conservation` | Ações de conservação (testado — retorna texto livre rico, ex.: menção a UCs e RPPNs no Pantanal) |
| `research` | Pesquisas relacionadas |
| `bibliographicReferences` | Referências bibliográficas completas (testado — lista de citações formatadas) |
| `authors` | Autores da ficha |

Essa decomposição em seções é **boa notícia para o chunking do RAG**: cada seção já é uma unidade de conteúdo semanticamente coesa (ex.: "Conservação" e "Ameaças" não se misturam), o que facilita criar um chunk por seção/ficha em vez de ter que segmentar um texto único.

### Outros endpoints úteis documentados em `/salve-api/public/`

- `/selectOptions` — valores para os filtros de busca avançada: `taxonGroups`, `regions`, `categories`, `states`, `biomas`, `groups`, `threats`, `uses`, `hydrographicBasin`. Útil para montar os filtros da coleta (ex.: pegar o id de "Répteis"/"Anfíbios" programaticamente em vez de fixar no código).
- `/searchTaxon?q=<nome>&idLevel=<n>&criteria=startWith` — busca de táxon por nível.
- `/searchPan?q=<termo>` — busca de PANs relacionados (pode ser usado para cruzar SALVE × PANs já coletados).
- `/fichaPdf/<idFicha>` e `/fichaVersaoPdf/<idFicha>` — PDF oficial da ficha (alternativa/complemento ao HTML por seção).
- `/speciePhoto/<id>` e `/speciePhoto/<id>/full` — foto da espécie (não citável como fonte textual, mas pode interessar para a interface).
- `/highlightedSpecies`, `/totalNumbers`, `/graphEvaluatedCategories`, `/graphEvaluatedCategoriesBiome`, `/graphEvaluatedGroups`, `/graphThreatenedGroupsCategories` — dados agregados/gráficos da página inicial. Não são fichas individuais, mas podem servir para responder perguntas gerais ("quantas espécies de répteis estão avaliadas no Brasil?").
- Endpoints adicionais em `/salve-api/api/` (sem o `/public/`): `fichaEspecie?sqFicha=<id>` (parece usar o ID numérico interno, não o token opaco) e `taxon/search/<nome>/<nivel>` — **não testados**; podem exigir autenticação ou ter `sqFicha` não descoberto a partir do `/search` público (que só devolve `id_ficha` opaco). Investigar antes de depender deles.

### Confirmações técnicas

- Todas as chamadas testadas devolveram `Access-Control-Allow-Origin: *` e não exigiram nenhum cookie/sessão — é seguro tratar como **API pública sem autenticação**.
- Resposta padrão: `{"msg": "", "status": 200, "data": ..., "pagination": {...}}`. `status` 404 = endpoint inexistente; `status` 500 = endpoint existe mas faltam parâmetros obrigatórios (ex.: `/search` sem nenhum parâmetro).

## Módulo 2 — `salve-consulta` (consulta ampla)

**Base URL:** `https://salve.icmbio.gov.br/salve-consulta/`

Backend Grails/GSP com Vue 2 incorporado via `<script>` direto (não é SPA pura — o HTML inicial já vem com a estrutura da página, e os dados são carregados depois via POST). Endpoints descobertos no arquivo `assets/inicial-<hash>.js` (variável `baseUrl` definida em `assets/application-<hash>.js` como `<protocolo+host> + '/salve-consulta/'`):

- `POST ficha/consultaAmpla` — lista as fichas atualmente abertas para consulta pública ampla (sem necessidade de login). Testado: retorna 794 fichas (ciclo testado, majoritariamente peixes em 2026), com `sqConsultaFicha`, `noCientifico` (HTML com itálico), `noComum`, `dtFim` (prazo da consulta), `sqGrupo`/`sqSubgrupo`, além de um campo `consultas` com os ciclos de consulta ativos (`sgConsulta`, `cdSistema`).
- `POST ficha/consultaDireta` — fichas em consulta direta (provavelmente vinculadas a um login de colaborador específico) — não relevante para coleta pública.
- `POST ficha/gruposAvaliados` e `POST ficha/subgruposAvaliados` — listas de grupos/subgrupos para os filtros da página.

Esse módulo é **secundário** para o RAN: é uma "fila de espécies aguardando revisão pública", não a fonte de categoria de risco consolidada (essa é o portal público, módulo 1). Pode ser útil só para sinalizar "espécie X está em revisão, categoria pode mudar em breve" — uma nota de cautela na resposta do chatbot, se a espécie aparecer aqui.

## Módulo 3 — `salve/` (gestão interna)

Não investigado — exige login institucional (SICA-e). Fora do escopo de coleta automatizada pública, mesma lógica já aplicada ao SEI/ICMBio (acesso restrito, sem scraping).

## Entradas (para o futuro script)

- IDs de grupo taxonômico fixos (Répteis `1266`, Anfíbios `1257`), ou obtidos dinamicamente via `/selectOptions` a cada execução (mais robusto a mudanças).
- Paginação do `/search?grupoIds=1266,1257&paginationPageSize=<N>` até esgotar `paginationTotalPages`.
- Para cada `id_ficha` retornado, uma chamada a `/fichaHtml` por seção (11 seções listadas acima).

## Saídas (proposta, a confirmar ao implementar)

Seguindo o padrão de `01_fontes_web/monitora/` e `01_fontes_web/pans/`:

```
01_fontes_web/salve/
├── _indice_salve.json                 # resumo: total de fichas por grupo/categoria, data de coleta
└── fichas/
    └── <slug-nome-cientifico>/
        └── metadados.json            # categoria, taxonomia, e o texto de cada seção
```

Cada `metadados.json` deveria registrar, no mínimo: `id_ficha` (token), nome científico, categoria de risco (sigla + descrição), grupo, data da última avaliação/publicação, URL de origem (a própria API), data de coleta, e o conteúdo de cada seção (texto bruto em HTML, a ser limpo na etapa de extração).

**Ainda não decidido:** se as 11 seções de cada ficha entram como 11 chunks separados (aproveitando a divisão natural da API) ou se são concatenadas num único texto por ficha antes do chunking padrão do pipeline. Ponto a discutir na etapa de geração de embeddings/chunks (`07_processados/`), não nesta etapa de mapeamento.

## Ferramentas

- **Python 3.10+**, **requests** — chamadas diretas à API JSON (não é necessário BeautifulSoup nem renderização JS: a API devolve JSON estruturado).
- Não é necessário Playwright/Selenium — a suposição inicial de que o SALVE exigiria renderização JS (`coleta_fontes_web.md`) **não se confirmou** depois de localizar a API REST por trás do front-end.

## Próximos passos

1. Implementar `scripts/coleta/coleta_salve.py`: paginar `/search?grupoIds=1266,1257`, depois buscar as 11 seções de `/fichaHtml` para cada `id_ficha`, salvando em `01_fontes_web/salve/fichas/<slug>/metadados.json`.
2. Decidir um `--atraso` padrão entre requisições (mesmo padrão usado em `coleta_monitora.py`/`coleta_pans.py`) — com 2086 fichas × 11 seções, são ~22.946 requisições só de conteúdo, então isso precisa de um intervalo educado e, possivelmente, execução em lotes/retomável.
3. Avaliar se vale usar `/fichaPdf/<idFicha>` como alternativa/complemento ao `/fichaHtml` por seção (PDF oficial pode ser mais citável como "fonte", mas exige extração de PDF depois).
4. Testar `/selectOptions` -> `categories` para mapear todas as siglas de categoria de risco (LC, NT, VU, EN, CR, etc.) e documentar o significado de cada uma.
5. Confirmar se `id_ficha` é estável entre execuções (reavaliações podem gerar `id_ficha_versao_antiga` — ver campo já presente na resposta do `/search`) para não duplicar fichas históricas indevidamente.
6. Avaliar cruzamento com PANs via `/searchPan` — várias espécies de herpetofauna citadas em PANs já coletados podem ter ficha SALVE correspondente.

## Relacionados

- Análise técnica original (todas as fontes web, antes da investigação do SALVE): [`coleta_fontes_web.md`](coleta_fontes_web.md)
- Padrão de saída equivalente: [`coleta_monitora_detalhado.md`](coleta_monitora_detalhado.md), [`coleta_pans_detalhado.md`](coleta_pans_detalhado.md)

## Observações sobre dados sensíveis

Os dados mapeados (categoria de risco, distribuição, conservação) são informações públicas do portal oficial do SALVE, sem necessidade de login. Não foram investigados nem acessados os módulos de gestão interna (`salve/`) ou qualquer dado que exigisse autenticação — mantendo a mesma cautela já aplicada ao SEI/ICMBio. Distribuição geográfica de espécies ameaçadas, quando em nível nacional/textual (como retornado aqui), é a mesma informação já publicada pelo próprio ICMBio na ficha oficial — não é uma localização precisa de ocorrência (coordenadas), que receberia tratamento mais cauteloso se fosse encontrada.
