# Diagnóstico de retrieval — "anfíbios no Cerrado"

_Gerado em 2026-08-12 por `scripts/diagnostico_retrieval.py`. Diagnóstico apenas — nenhuma mudança de produção foi feita nesta tarefa._

## Resumo executivo

O problema original é reproduzível: sem filtro de fonte, os 5 resultados do baseline são dominados por parágrafos introdutórios genéricos sobre o bioma Cerrado, vindos de PANs de táxons não relacionados (cactáceas, aves, lepidópteros, pato-mergulhão), com scores concentrados em 0.61–0.66. A informação sobre anfíbios do Cerrado **existe** na base — fichas SALVE de espécies com `Bioma: Cerrado` — mas fica abaixo do corte quando a busca não é filtrada por fonte: isolar `fontes=["salve"]` (caso 4) já traz majoritariamente fichas de anfíbios/répteis relevantes. Não existe, no corpus indexado, nenhum PAN de Herpetofauna do Cerrado — só PANs regionais (Nordeste, Sul, Sudeste, Espinhaço, Insular) — então a pergunta não tem um documento-síntese único para citar. Reformular com termo mais técnico ("anuros Cerrado conservação", caso 6) melhora bastante a precisão do ranking (6/10 resultados sinalizados como possivelmente relevantes, contra 1/5 no baseline), o que indica que parte do problema é ranking/vocabulário, não só ausência de conteúdo. A causa mais provável é a combinação de: ausência de busca léxica que pondere termos exatos, chunks de boilerplate quase-idênticos entre PANs de táxons diferentes inflando scores de trechos genéricos sobre o bioma, e ranking sem filtro de fonte deixando os PANs (mais numerosos em texto corrido) dominarem sobre o SALVE (fichas específicas por espécie).

## Casos de teste

Heurística de leitura (coluna "possivelmente relevante"): marca "sim" quando o texto do chunk ou o nome do documento contém alguma das palavras anfíbio, anfíbios, anuro, anuros, herpetofauna (case-insensitive). **Isto não é uma métrica de avaliação** — é só um sinalizador grosseiro para facilitar a leitura humana da tabela; um "sim" não garante que o trecho responda à pergunta, e um "não" não garante que seja irrelevante.

Total de resultados coletados em todos os casos: 65 (sinalizados como possivelmente relevantes: 14).

### Caso 1-baseline

- **Pergunta**: 'quais anfíbios ocorrem no Cerrado?'
- **top_k**: 5
- **fontes**: todas
- **Por que este caso existe**: Repetição do teste manual original que motivou este diagnóstico — referência para comparar com os demais casos.
- **Resultados retornados**: 5

| # | score | fonte | documento | seção | página | possivelmente relevante* | trecho (~200 car.) |
|---|-------|-------|-----------|-------|--------|--------------------------|---------------------|
| 1 | 0.6557 | pans | pan-herpetofauna-do-nordeste-sumario.pdf | pan-herpetofauna-do-nordeste | 2 | sim | Com uma área de aproximadamente 22% do território nacional, o Cerrado é caracterizado predominantemente por extensas formações savânicas, constituído por diferentes fitofisionomias, desde formações fl… |
| 2 | 0.6362 | pans | pan-cactaceas-livro.pdf | pan-cactaceas | 17 | não | O Cerrado, caracterizado por uma co- bertura contínua de plantas herbáceas com predomínio de Poaceae e Cyperaceae acom- panhadas de um estrato arbustivo-arbóreo de densidade variável, é uma vegetação… |
| 3 | 0.6267 | pans | pan-aves-do-cerrado-pantanal-sumario.pdf | pan-aves-do-cerrado-e-pantanal | 2 | não | Para diversas espécies de aves migratórias, provenientes tanto do Hemisfério Norte quanto do Hemisfério Sul, o Pantanal representa um importante sítio de invernada. Porto Jofre, MT Renato Soares Morei… |
| 4 | 0.6194 | pans | copy_of_GuiadoeducadorPatomergulho.pdf | pan-pato-mergulhao | 9-10 | não | O Cerrado é o segundo maior bioma da América do Sul, ocupando cerca de 24% do território brasileiro e ainda parte dos territórios do Paraguai e Bolívia (Brasil 2010). O seu alto endemismo de plantas e… |
| 5 | 0.6135 | pans | pan-lepidopteros-livro.pdf | pan-lepidopteros | 18 | não | A região dos cerrados inclui apenas um centro de endemismo, conhecido como Ara- guaia (Prance, 1982). Apesar do reconhecimen- to deste centro de endemismo, que é baseado na diferenciação local de raça… |

### Caso 2-top_k_20

- **Pergunta**: 'quais anfíbios ocorrem no Cerrado?'
- **top_k**: 20
- **fontes**: todas
- **Por que este caso existe**: Mesma pergunta, top_k maior — checar se algo relevante aparece mais abaixo no ranking (indício de problema de ranking, não de cobertura).
- **Resultados retornados**: 20

| # | score | fonte | documento | seção | página | possivelmente relevante* | trecho (~200 car.) |
|---|-------|-------|-----------|-------|--------|--------------------------|---------------------|
| 1 | 0.6557 | pans | pan-herpetofauna-do-nordeste-sumario.pdf | pan-herpetofauna-do-nordeste | 2 | sim | Com uma área de aproximadamente 22% do território nacional, o Cerrado é caracterizado predominantemente por extensas formações savânicas, constituído por diferentes fitofisionomias, desde formações fl… |
| 2 | 0.6362 | pans | pan-cactaceas-livro.pdf | pan-cactaceas | 17 | não | O Cerrado, caracterizado por uma co- bertura contínua de plantas herbáceas com predomínio de Poaceae e Cyperaceae acom- panhadas de um estrato arbustivo-arbóreo de densidade variável, é uma vegetação… |
| 3 | 0.6267 | pans | pan-aves-do-cerrado-pantanal-sumario.pdf | pan-aves-do-cerrado-e-pantanal | 2 | não | Para diversas espécies de aves migratórias, provenientes tanto do Hemisfério Norte quanto do Hemisfério Sul, o Pantanal representa um importante sítio de invernada. Porto Jofre, MT Renato Soares Morei… |
| 4 | 0.6194 | pans | copy_of_GuiadoeducadorPatomergulho.pdf | pan-pato-mergulhao | 9-10 | não | O Cerrado é o segundo maior bioma da América do Sul, ocupando cerca de 24% do território brasileiro e ainda parte dos territórios do Paraguai e Bolívia (Brasil 2010). O seu alto endemismo de plantas e… |
| 5 | 0.6135 | pans | pan-lepidopteros-livro.pdf | pan-lepidopteros | 18 | não | A região dos cerrados inclui apenas um centro de endemismo, conhecido como Ara- guaia (Prance, 1982). Apesar do reconhecimen- to deste centro de endemismo, que é baseado na diferenciação local de raça… |
| 6 | 0.6093 | pans | 20251202-pan-cerpan-sumario.pdf | pan-cerpam | 4 | não | O Cerrado é um mosaico de fitofisionomias. xxxxO recorte territorial do CERPAM engloba quatro biomas: Amazônia, Cerrado, Pantanal e Mata Atlântica, esta última apenas na região Centro-Oeste do Brasil.… |
| 7 | 0.6059 | pans | pan-lepidopteros-livro.pdf | pan-lepidopteros | 18 | não | Apesar de ser um bioma ainda bem preservado, a falta de conhecimento e estudos recentes resulta em apenas uma espécie des- te bioma na lista das espécies ameaçadas do Brasil. Estudos adicionais são ne… |
| 8 | 0.5967 | pans | pan-cerpan-sumario.pdf | pan-cerpam | 2 | não | Além disso, o solo do Cerrado funciona também como uma “esponja”, sendo importante para a formação de diversos aquíferos, que são reservatórios de água subterrânea, incluindo o Aquífero Guarani. Por t… |
| 9 | 0.5956 | pans | pan-aves-do-cerrado-pantanal-sumario.pdf | pan-aves-do-cerrado-e-pantanal | 1-2 | não | Sumário Executivo do Plano de Ação Nacional para a Conservação das Aves do Cerrado e Pantanal. O Cerrado constitui a maior e mais rica área de savanas contínuas do planeta, com cerca de 2,1 milhões de… |
| 10 | 0.5945 | pans | pan-aves-de-rapina-livro.pdf | pan-aves-de-rapina | 50-51 | não | Em um trabalho comparativo das unidades de conservação do bioma, Braz (2003) analisou as 837 espécies de aves, copilando as listas da bibliografia disponível e os dados de saídas de campo em quatro UC… |
| 11 | 0.5943 | pans | 20251023-pan-primatas-amazonicos-livro-primatas-mato-grosso-compactado.pdf | pan-primatas-amazonicos | 20 | não | As Florestas de Sinop e Região 20 Na região de Sinop, a Amazônia e o Cerrado se encontram. É o maior ecótono (zona de transição) tropical do planeta, onde há uma mistura de plantas e animais da Amazôn… |
| 12 | 0.5848 | salve | Bothrops marmoratus Silva & Rodrigues, 2008 | historia_natural | — | sim | Espécie: Bothrops marmoratus Silva & Rodrigues, 2008 (Jararaca, Jararaca-Marmorata, Jararaca-Pintada, Marbled lancehead) Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado, Mata Atlântica DOI:… |
| 13 | 0.5842 | monitora | CerradoemFlores.pdf | materiais-de-apoio | 6 | não | APRESENTAÇÃO Conhecer a biodiversidade do Cerrado é o primeiro passo para a conservação desse bioma. Com mais de 12 mil espécies de plantas e considerado a savana mais rica do planeta, o Cerrado abrig… |
| 14 | 0.5841 | pans | pan-lepidopteros-livro.pdf | pan-lepidopteros | 18 | não | Durante o workshop “Ações Prioritárias para a Conservação do Cerrado e Pantanal”, fo- ram detectadas duas províncias e três sub-regiões faunísticas distintas para certos grupos de in- setos, inclusive… |
| 15 | 0.5789 | pans | pan-onca-pintada-livro.pdf | pan-onca-pintada | 59 | não | Tendências populacionais A população de onças-pintadas no Cerrado está provavelmente em declínio, mas ainda há uma grande lacuna de conhecimento para o Bioma. Assim sendo novas áreas devem ser pesquis… |
| 16 | 0.5764 | pans | pan-cervideos-livro.pdf | pan-cervideos | 36 | não | Relevo acidentado, com a formação de paredões e cânions Parque Nacional do Araguaia 557.714 Estado do Tocantins, médio Araguaia, no extremo norte da Ilha do Bananal Transição entre o Cerrado, predomin… |
| 17 | 0.5725 | pans | pan-aves-do-cerrado-pantanal-sumario.pdf | pan-aves-do-cerrado-e-pantanal | 2-3 | não | O baixo endemismo é justificado pela sinergia das espécies advindas de todos os biomas associados, o que o torna extremamente rico e importante para a manutenção da riqueza biológica do Brasil. Consid… |
| 18 | 0.5712 | pans | pan-onca-pintada-livro.pdf | pan-onca-pintada | 60 | não | PLANO DE AÇÃO NACIONAL PARA CONSERVAÇÃO 59 ONÇA-PINTADA ser sugeridas. Com base em perdas conhecidas em alguns lugares, achamos que a população de onças pintadas no Cerrado diminuiu 50% nos últimos 25… |
| 19 | 0.5705 | pans | pan-lepidopteros-livro.pdf | pan-lepidopteros | 18 | não | Dentre as mariposas a taxa de endemis- mo também é baixa, e com cerca de 12% de espécies endêmicas para os Saturniidae (Camar- go & Becker, 1999). Ainda entre os Saturniidae (família melhor estudada),… |
| 20 | 0.5661 | pans | pan-pequenos-mamiferos-areas-abertas-sumario.pdf | pan-pequenos-mamiferos-areas-abertas | 2 | não | Dentre os diferentes ambientes ocupados por esses animais, as áreas abertas como o Cerrado, Caatinga, Pampa e Pantanal, abrigam uma diversidade expressiva de pequenos mamíferos, grande parte deles exc… |

### Caso 3-fonte_monitora

- **Pergunta**: 'quais anfíbios ocorrem no Cerrado?'
- **top_k**: 10
- **fontes**: ['monitora']
- **Por que este caso existe**: Isolar a fonte Monitora para ver cobertura/ranking só dentro dela.
- **Resultados retornados**: 10

| # | score | fonte | documento | seção | página | possivelmente relevante* | trecho (~200 car.) |
|---|-------|-------|-----------|-------|--------|--------------------------|---------------------|
| 1 | 0.5842 | monitora | CerradoemFlores.pdf | materiais-de-apoio | 6 | não | APRESENTAÇÃO Conhecer a biodiversidade do Cerrado é o primeiro passo para a conservação desse bioma. Com mais de 12 mil espécies de plantas e considerado a savana mais rica do planeta, o Cerrado abrig… |
| 2 | 0.5527 | monitora | Guiaparaamostragemdasformasdevida.pdf | materiais-de-apoio | 14-16 | não | Fotografia Marcelo Kuhlmann Guia para amostragem das formas de vida da vegetação e apoio ao Programa de Monitoramento da biodiversidade do ICMBio 14 CACTOS Plantas geralmente suculentas, com caules ve… |
| 3 | 0.5455 | monitora | RelatorioFlorestal20142022.pdf | relatorios | 116 | não | 116 Instituto Chico Mendes de Conservação da Biodiversidade espécie (Cariama cristata – seriema), são típicos de ambientes abertos e praticamente não foram avistados (Figura 5.5). A variação nas propo… |
| 4 | 0.5402 | monitora | verdemasnodoCerrado.pdf | materiais-de-apoio | 7-11 | não | Fotografia Marcelo Kuhlmann É verde, mas não é do Cerrado: espécies exóticas invasoras em Unidades de Conservação do DF 7 Anacardiaceae MANGUEIRA NOME CIENTÍFICO Mangifera indica L. FORMA DE VIDA Árvo… |
| 5 | 0.5335 | monitora | verdemasnodoCerrado.pdf | materiais-de-apoio | 21-26 | não | Fotografia Marcelo Kuhlmann É verde, mas não é do Cerrado: espécies exóticas invasoras em Unidades de Conservação do DF 21 Poaceae CAPIM-DO-TEXAS NOME CIENTÍFICO Cenchrus setaceus (Forssk.) Morrone FO… |
| 6 | 0.5316 | monitora | Guiaparaamostragemdasformasdevida.pdf | materiais-de-apoio | 6-8 | não | Fotografia Marcelo Kuhlmann Guia para amostragem das formas de vida da vegetação e apoio ao Programa de Monitoramento da biodiversidade do ICMBio 6 ERVAS GRAMINOIDES Plantas herbáceas, com caules verd… |
| 7 | 0.5258 | monitora | verdemasnodoCerrado.pdf | materiais-de-apoio | 11-16 | não | Fotografia Marcelo Kuhlmann É verde, mas não é do Cerrado: espécies exóticas invasoras em Unidades de Conservação do DF 11 Euphorbiaceae MAMONA NOME CIENTÍFICO Ricinus communis L. FORMA DE VIDA Arbust… |
| 8 | 0.5252 | monitora | RelatorioFlorestal20142022.pdf | relatorios | 136 | não | Mamíferos de médio e grande porte em fragmentos de Cerrado na Fazenda Experimental do Glória (Uberlândia, MG). Dissertação de Mestrado. Universidade Federal de Uberlândia. Uberlândia, MG. Alves, S. L.… |
| 9 | 0.5222 | monitora | RegimentoInternoPortaria1270de29dedezembrode2022.pdf | legislacao | 60 | não | Ao Centro Nacional de Pesquisa e Conservação da Biodiversidade do Cerrado e Restauração Ecológica - CBC compete: I - coordenar, apoiar e realizar a pesquisa e a divulgação das ações técnico-científica… |
| 10 | 0.5212 | monitora | verdemasnodoCerrado.pdf | materiais-de-apoio | 16-21 | não | Fotografia Marcelo Kuhlmann É verde, mas não é do Cerrado: espécies exóticas invasoras em Unidades de Conservação do DF 16 Myrtaceae JAMELÃO NOME CIENTÍFICO Syzygium cumini (L.) Skeels FORMA DE VIDA Á… |

### Caso 4-fonte_salve

- **Pergunta**: 'quais anfíbios ocorrem no Cerrado?'
- **top_k**: 10
- **fontes**: ['salve']
- **Por que este caso existe**: Isolar a fonte SALVE para ver cobertura/ranking só dentro dela.
- **Resultados retornados**: 10

| # | score | fonte | documento | seção | página | possivelmente relevante* | trecho (~200 car.) |
|---|-------|-------|-----------|-------|--------|--------------------------|---------------------|
| 1 | 0.5848 | salve | Bothrops marmoratus Silva & Rodrigues, 2008 | historia_natural | — | sim | Espécie: Bothrops marmoratus Silva & Rodrigues, 2008 (Jararaca, Jararaca-Marmorata, Jararaca-Pintada, Marbled lancehead) Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado, Mata Atlântica DOI:… |
| 2 | 0.5653 | salve | Aspronema dorsivittatum (Cope, 1862) | referencias | — | não | Espécie: Aspronema dorsivittatum (Cope, 1862) Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado, Mata Atlântica, Pampa DOI: 10.37002/salve.ficha.35643.2 Seção: Referências Instituto de Ciência… |
| 3 | 0.5634 | salve | Dendropsophus microcephalus (Cope, 1886) | referencias | — | sim | Espécie: Dendropsophus microcephalus (Cope, 1886) Categoria de risco: Menos Preocupante (LC) Bioma: Amazônia, Caatinga, Cerrado, Mata Atlântica DOI: 10.37002/salve.ficha.21206 Seção: Referências Revis… |
| 4 | 0.5627 | salve | Proceratophrys vielliardi Martins & Giaretta, 2011 | ameacas | — | não | Espécie: Proceratophrys vielliardi Martins & Giaretta, 2011 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.21464.2 Seção: Ameaças A espécie ocorre em uma região do… |
| 5 | 0.5610 | salve | Phalotris nasutus (Gomes, 1915) | historia_natural | — | não | Espécie: Phalotris nasutus (Gomes, 1915) (Fura-Terra, Fura-Terra-Nariguda) Categoria de risco: Menos Preocupante (LC) Bioma: Amazônia, Cerrado, Mata Atlântica, Pantanal DOI: 10.37002/salve.ficha.27877… |
| 6 | 0.5586 | salve | Leptodactylus troglodytes Lutz, 1926 | referencias | — | sim | Espécie: Leptodactylus troglodytes Lutz, 1926 Categoria de risco: Menos Preocupante (LC) Bioma: Amazônia, Caatinga, Cerrado, Mata Atlântica DOI: 10.37002/salve.ficha.20371.2 Seção: Referências Biotema… |
| 7 | 0.5555 | salve | Adenomera saci Carvalho & Giaretta, 2013 | ameacas | — | não | Espécie: Adenomera saci Carvalho & Giaretta, 2013 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.20309 Seção: Ameaças A perda de hábitat é uma ameaça frequente par… |
| 8 | 0.5540 | salve | Xenodon nattereri (Steindachner, 1867) | ameacas | — | não | Espécie: Xenodon nattereri (Steindachner, 1867) (Achatadeira, Boipeva, Cobra-Nariguda, Cobra-Nariguda-do-Campo, Falsa-Jararaca, Nariguda) Categoria de risco: Dados Insuficientes (DD) Bioma: Amazônia,… |
| 9 | 0.5532 | salve | Micrurus brasiliensis Roze, 1967 | historia_natural | — | não | Espécie: Micrurus brasiliensis Roze, 1967 Categoria de risco: Menos Preocupante (LC) Bioma: Caatinga, Cerrado DOI: 10.37002/salve.ficha.28063.2 Seção: História natural Micrurus brasiliensis ocorre no… |
| 10 | 0.5513 | salve | Stenocercus quinarius Nogueira & Rodrigues, 2006 | historia_natural | — | não | Espécie: Stenocercus quinarius Nogueira & Rodrigues, 2006 (Pequeno-dragão) Categoria de risco: Vulnerável (VU) Bioma: Cerrado DOI: 10.37002/salve.ficha.35759.2 Seção: História natural Stenocercus quin… |

### Caso 5-reformulacao

- **Pergunta**: 'lista de espécies de anfíbios ameaçados no bioma Cerrado'
- **top_k**: 10
- **fontes**: todas
- **Por que este caso existe**: Reformulação da pergunta original — testar sensibilidade da busca semântica à forma como a pergunta é escrita.
- **Resultados retornados**: 10

| # | score | fonte | documento | seção | página | possivelmente relevante* | trecho (~200 car.) |
|---|-------|-------|-----------|-------|--------|--------------------------|---------------------|
| 1 | 0.6302 | pans | pan-lepidopteros-livro.pdf | pan-lepidopteros | 18 | não | Apesar de ser um bioma ainda bem preservado, a falta de conhecimento e estudos recentes resulta em apenas uma espécie des- te bioma na lista das espécies ameaçadas do Brasil. Estudos adicionais são ne… |
| 2 | 0.6053 | salve | Xenodon nattereri (Steindachner, 1867) | ameacas | — | não | Espécie: Xenodon nattereri (Steindachner, 1867) (Achatadeira, Boipeva, Cobra-Nariguda, Cobra-Nariguda-do-Campo, Falsa-Jararaca, Nariguda) Categoria de risco: Dados Insuficientes (DD) Bioma: Amazônia,… |
| 3 | 0.6028 | salve | Scinax goya (Andrade, Santos, Rocha, Pombal & Vaz-Silva, 2018) | referencias | — | sim | Espécie: Scinax goya (Andrade, Santos, Rocha, Pombal & Vaz-Silva, 2018) (Perereca-de-inverno) Categoria de risco: Dados Insuficientes (DD) Bioma: Cerrado DOI: 10.37002/salve.ficha.20211.1 Seção: Refer… |
| 4 | 0.6028 | pans | pan-aves-do-cerrado-pantanal-sumario.pdf | pan-aves-do-cerrado-e-pantanal | 2 | não | Para diversas espécies de aves migratórias, provenientes tanto do Hemisfério Norte quanto do Hemisfério Sul, o Pantanal representa um importante sítio de invernada. Porto Jofre, MT Renato Soares Morei… |
| 5 | 0.6013 | pans | pan-aves-do-cerrado-pantanal-sumario.pdf | pan-aves-do-cerrado-e-pantanal | 2-3 | não | O baixo endemismo é justificado pela sinergia das espécies advindas de todos os biomas associados, o que o torna extremamente rico e importante para a manutenção da riqueza biológica do Brasil. Consid… |
| 6 | 0.5999 | salve | Adenomera saci Carvalho & Giaretta, 2013 | ameacas | — | não | Espécie: Adenomera saci Carvalho & Giaretta, 2013 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.20309 Seção: Ameaças A perda de hábitat é uma ameaça frequente par… |
| 7 | 0.5977 | pans | pan-herpetofauna-do-nordeste-sumario.pdf | pan-herpetofauna-do-nordeste | 2 | sim | Com uma área de aproximadamente 22% do território nacional, o Cerrado é caracterizado predominantemente por extensas formações savânicas, constituído por diferentes fitofisionomias, desde formações fl… |
| 8 | 0.5924 | salve | Adenomera juikitam Carvalho & Giaretta, 2013 | ameacas | — | não | Espécie: Adenomera juikitam Carvalho & Giaretta, 2013 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.21176 Seção: Ameaças A perda de habitat é uma ameaça para as e… |
| 9 | 0.5920 | pans | copy_of_GuiadoeducadorPatomergulho.pdf | pan-pato-mergulhao | 9-10 | não | O Cerrado é o segundo maior bioma da América do Sul, ocupando cerca de 24% do território brasileiro e ainda parte dos territórios do Paraguai e Bolívia (Brasil 2010). O seu alto endemismo de plantas e… |
| 10 | 0.5894 | salve | Proceratophrys vielliardi Martins & Giaretta, 2011 | ameacas | — | não | Espécie: Proceratophrys vielliardi Martins & Giaretta, 2011 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.21464.2 Seção: Ameaças A espécie ocorre em uma região do… |

### Caso 6-termo_especifico

- **Pergunta**: 'anuros Cerrado conservação'
- **top_k**: 10
- **fontes**: todas
- **Por que este caso existe**: Termo mais próximo do vocabulário técnico dos documentos (anuros) e consulta mais curta, testando se isso melhora o ranking.
- **Resultados retornados**: 10

| # | score | fonte | documento | seção | página | possivelmente relevante* | trecho (~200 car.) |
|---|-------|-------|-----------|-------|--------|--------------------------|---------------------|
| 1 | 0.6349 | salve | Dendropsophus microcephalus (Cope, 1886) | referencias | — | sim | Espécie: Dendropsophus microcephalus (Cope, 1886) Categoria de risco: Menos Preocupante (LC) Bioma: Amazônia, Caatinga, Cerrado, Mata Atlântica DOI: 10.37002/salve.ficha.21206 Seção: Referências Revis… |
| 2 | 0.6279 | salve | Odontophrynus cultripes Reinhardt & Lütken, 1862 | referencias | — | sim | Espécie: Odontophrynus cultripes Reinhardt & Lütken, 1862 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado, Mata Atlântica DOI: 10.37002/salve.ficha.21379 Seção: Referências Araujo, C.O.; Cor… |
| 3 | 0.5975 | salve | Dendropsophus cruzi (Pombal & Bastos, 1998) | referencias | — | sim | Espécie: Dendropsophus cruzi (Pombal & Bastos, 1998) Categoria de risco: Menos Preocupante (LC) Bioma: Amazônia, Cerrado, Mata Atlântica DOI: 10.37002/salve.ficha.21203.2 Seção: Referências Bastos, R.… |
| 4 | 0.5811 | salve | Proceratophrys moratoi (Jim & Caramaschi, 1980) | referencias | — | não | Espécie: Proceratophrys moratoi (Jim & Caramaschi, 1980) (Sapo-da-terra) Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado, Mata Atlântica DOI: 10.37002/salve.ficha.20067.2 Seção: Referências… |
| 5 | 0.5787 | salve | Proceratophrys salvatori (Caramaschi, 1996) | referencias | — | sim | Espécie: Proceratophrys salvatori (Caramaschi, 1996) Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.21381.2 Seção: Referências Brandão, R.A. & Batista, C.G. 2000.… |
| 6 | 0.5775 | salve | Oreobates antrum Vaz-Silva, Maciel, Andrade & Amaro, 2018 | conservacao | — | não | Espécie: Oreobates antrum Vaz-Silva, Maciel, Andrade & Amaro, 2018 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.20212.1 Seção: Conservação Não há ações de conser… |
| 7 | 0.5742 | salve | Micrurus decoratus (Jan, 1858) | conservacao | — | não | Espécie: Micrurus decoratus (Jan, 1858) (Cobra Coral Decorada) Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado, Mata Atlântica DOI: 10.37002/salve.ficha.28065.2 Seção: Conservação Não há açã… |
| 8 | 0.5702 | pans | copy_of_GuiadoeducadorPatomergulho.pdf | pan-pato-mergulhao | 9-10 | não | O Cerrado é o segundo maior bioma da América do Sul, ocupando cerca de 24% do território brasileiro e ainda parte dos territórios do Paraguai e Bolívia (Brasil 2010). O seu alto endemismo de plantas e… |
| 9 | 0.5677 | salve | Aplastodiscus lutzorum Berneck, Giaretta, Brandão, Cruz, and Haddad, 2017 | referencias | — | sim | Espécie: Aplastodiscus lutzorum Berneck, Giaretta, Brandão, Cruz, and Haddad, 2017 Categoria de risco: Menos Preocupante (LC) Bioma: Cerrado DOI: 10.37002/salve.ficha.16658 Seção: Referências Bastos,… |
| 10 | 0.5674 | salve | Dendropsophus rubicundulus (Reinhardt & Lütken, 1862) | referencias | — | sim | Espécie: Dendropsophus rubicundulus (Reinhardt & Lütken, 1862) Categoria de risco: Menos Preocupante (LC) Bioma: Caatinga, Cerrado DOI: 10.37002/salve.ficha.21208.2 Seção: Referências Herpetofauna da… |

## Cobertura do corpus

Verificação feita varrendo os metadados já indexados no Qdrant (campos `documento` e `secao`/`categoria` do payload), sem abrir nenhum PDF.

- Pontos verificados: 59085
- Fontes presentes na coleção: monitora, pans, salve
- Documentos distintos por fonte: {'monitora': 108, 'pans': 663, 'salve': 1816}

Documentos cujo nome contém termos de herpetofauna (anfíbio, anfíbios, anuro, anuros, herpetofauna, réptil/reptil):

- 2013-pan-herpetofauna-do-sul-matriz-planejamento-site.pdf
- 2015-pan-herpetofauna-do-nordeste-boletim-1.pdf
- 2016-pan-herpetofauna-do-espinhaco-boletim-1.pdf
- 2016-pan-herpetofauna-insular-boletim-1.pdf
- 2020-pan-herpetofauna-do-espinhaco-mozaico-quadrilatero-ferrifero.pdf
- 2020-pan-herpetofauna-do-espinhaco-mozaico-serra-cipo.pdf
- 2020-pan-herpetofauna-do-sul-bibliografia-ecologia-conservacao-melanophryniscus-admirabilis.pdf
- 2020-pan-herpetofauna-do-sul-bibliografia-efeitos-da-poluicao-sonora-em-anfibios.pdf
- 2020-pan-herpetofauna-do-sul-bibliografia-pesquisa-monitoramento-de-anuros.pdf
- 2020-pan-herpetofauna-do-sul-bibliografia-pesquisas-pithecopus-rusticus-outras-spp-regiao-campos-de-agua-doce.pdf
- 2020-pan-herpetofauna-do-sul-nota-tecnica-uc-em-arambare-rs.pdf
- 2022-pan-herpetofauna-do-espinhaco-areas-estrategicas.pdf
- 2022-pan-herpetofauna-do-sudeste-bibliografia-acao-3-3-1.pdf
- 2022-pan-herpetofauna-do-sudeste-bibliografia-acao-3-5.pdf
- 2022-pan-herpetofauna-do-sudeste-bibliografia-acao-3-9-1.pdf
- 2022-pan-herpetofauna-do-sudeste-jogo-memoria-10-sp-ameacadas-rj.pdf
- 2022-pan-herpetofauna-do-sudeste-livro-parque-estadual-fontes-ipiranga.pdf
- 2024-pan-herpetofauna-do-espinhaco-acao-1-7-fichas-das-especies.pdf
- 2024-pan-herpetofauna-do-espinhaco-acao-4-4-identidade-visual.pdf
- 2024-pan-herpetofauna-do-espinhaco-acao-6-1-incendios-em-ucs.pdf
- 2024-pan-herpetofauna-do-espinhaco-acao-6-3-modelagem-e-mapeamento-conectividade.pdf
- 2024-pan-herpetofauna-do-espinhaco-acao-6-5-cobertura-natural-das-ucs.pdf
- 2024-pan-herpetofauna-do-nordeste-acao-1-2-criacao-corredores-ecologicos.pdf
- 20240924_pan_herpetofauna_sudeste_portaria.pdf
- 20240924_pan_herpetofauna_sudeste_portaria_gat.pdf
- pan-herpetofauna-do-espinhaco-matriz-avaliacao.pdf
- pan-herpetofauna-do-espinhaco-matriz-planejamento-site.pdf
- pan-herpetofauna-do-espinhaco-portaria-aprovacao.pdf
- pan-herpetofauna-do-espinhaco-portaria-gat.pdf
- pan-herpetofauna-do-espinhaco-sumario.pdf
- pan-herpetofauna-do-nordeste-livro.pdf
- pan-herpetofauna-do-nordeste-matriz-planejamento-site.pdf
- pan-herpetofauna-do-nordeste-portaria-aprovacao.pdf
- pan-herpetofauna-do-nordeste-portaria-de-aprovacao-e-gat.pdf
- pan-herpetofauna-do-nordeste-portaria-gat.pdf
- pan-herpetofauna-do-nordeste-sumario.pdf
- pan-herpetofauna-do-sudeste-portaria-aprovacao.pdf
- pan-herpetofauna-do-sudeste-sumario.pdf
- pan-herpetofauna-do-sul-portaria-aprovacao.pdf
- pan-herpetofauna-do-sul-portaria-de-aprovacao-e-gat.pdf
- pan-herpetofauna-do-sul-portaria-gat.pdf
- pan-herpetofauna-do-sul-sumario.pdf
- pan-herpetofauna-insular-livro.pdf
- pan-herpetofauna-insular-sumario.pdf

- PAN de Herpetofauna com 'Cerrado' no nome do documento: NÃO encontrado
- PAN de Herpetofauna com 'Nordeste' no nome do documento: SIM — 2015-pan-herpetofauna-do-nordeste-boletim-1.pdf; 2024-pan-herpetofauna-do-nordeste-acao-1-2-criacao-corredores-ecologicos.pdf; pan-herpetofauna-do-nordeste-livro.pdf; pan-herpetofauna-do-nordeste-matriz-planejamento-site.pdf; pan-herpetofauna-do-nordeste-portaria-aprovacao.pdf; pan-herpetofauna-do-nordeste-portaria-de-aprovacao-e-gat.pdf; pan-herpetofauna-do-nordeste-portaria-gat.pdf; pan-herpetofauna-do-nordeste-sumario.pdf

_Aviso: esta verificação olha só o **nome do documento** e a **seção/categoria** nos metadados já indexados — não abre o conteúdo dos PDFs. Um PAN de Herpetofauna do Cerrado pode existir na base de fontes web (`01_fontes_web/`) sem ter sido indexado, ou pode estar indexado com um nome de documento que não contém nenhum dos termos buscados; nesse segundo caso este script não o detectaria e a checagem exigiria uma revisão manual do inventário (`06_inventario/inventario_fontes.xlsx`)._

**Atualização (checagem manual do inventário, feita ao planejar as ações de melhoria):**
confirmado que a ausência não é uma lacuna de coleta/indexação — é uma ausência real na fonte
primária. A aba dedicada "PANs - Herpetofauna" de `06_inventario/inventario_fontes.xlsx` lista
exatamente 7 PANs relacionados a herpetofauna (Nordeste, Sudeste, Sul, Espinhaço, Insular,
Quelônios, Tartarugas Marinhas) e nenhum deles é do Cerrado. O índice oficial raspado
diretamente da página de PANs do gov.br (`01_fontes_web/pans/_indice_pans.json`, coletado em
2026-06-17, 75 PANs no total) também não lista nenhum PAN de Herpetofauna do Cerrado — "Cerrado"
só aparece associado a outros táxons ("Aves do Cerrado e Pantanal", "Morceguinho-do-cerrado").
Ou seja: **não existe, no catálogo oficial do ICMBio, um PAN de Herpetofauna do Cerrado** —
a pergunta original não tem, e não terá após qualquer reindexação, um documento-síntese único
para citar. Ver decisão de política de resposta para esse caso na Ação 1 do plano de melhorias.

## Hipóteses

1. **Falta de documento consolidado sobre herpetofauna do Cerrado — CONFIRMADO, não é mais hipótese.**
   O ICMBio organiza os PANs de Herpetofauna por *recorte biogeográfico regional*, não por bioma: existem PAN Nordeste, PAN Sul, PAN Sudeste, PAN Espinhaço, PAN Insular (mais Quelônios e Tartarugas Marinhas). Nenhum se chama "PAN Herpetofauna do Cerrado" — confirmado na seção "Cobertura do corpus" abaixo, tanto nos metadados já indexados quanto (na checagem manual feita ao planejar as ações de melhoria) no inventário de fontes e no índice oficial raspado do gov.br. Isso não é uma falha de indexação; é assim que a fonte primária organiza os planos, e continuará assim mesmo após qualquer melhoria de ranking ou reindexação. Quando alguém pergunta "quais anfíbios ocorrem no Cerrado", não existe *um documento* que sintetize essa resposta, como existiria para a região Sul. A informação está lá, mas espalhada: cada espécie tem sua própria ficha no SALVE (base de avaliação de risco de extinção), e o campo `Bioma` de cada ficha pode incluir "Cerrado" junto com outros biomas. É informação dispersa em milhares de fichas atômicas, não um documento-lista pronto.

2. **Boilerplate quase-idêntico entre PANs de táxons diferentes infla o score de trechos genéricos.**
   "Boilerplate" aqui é o texto padronizado que se repete quase sem mudança em documentos diferentes — um parágrafo de abertura que vários PANs usam para apresentar o bioma antes de entrar no assunto específico do plano. No caso 2 (top_k=20), a mesma descrição de "o Cerrado é o segundo maior bioma..." aparece em pelo menos 7 PANs de assuntos totalmente diferentes (cactáceas, aves, lepidópteros, pato-mergulhão, cervídeos, pequenos mamíferos, onça-pintada). Do ponto de vista da busca por similaridade de embeddings, esses parágrafos são quase o mesmo vetor, porque falam do bioma em termos genéricos, não do assunto do plano. Como a pergunta "anfíbios no Cerrado" também menciona o bioma de forma central, o modelo de embeddings encontra alta similaridade com qualquer parágrafo que descreva o Cerrado, independente de ser sobre anfíbio, ave ou planta. É por isso que a faixa de score do baseline (0.61–0.66) é estreita: vários chunks quase-clones competindo pelo mesmo motivo — "falam do Cerrado" — não porque algum deles responda "quais espécies".

3. **Busca puramente vetorial sub-pondera termos exatos.**
   A busca atual (`buscar_chunks` em `backend/services/retrieval.py`) é 100% busca semântica/vetorial: a pergunta e os chunks são transformados em vetores numéricos (embeddings, via BGE-M3) e o Qdrant retorna os vizinhos mais próximos por similaridade de cosseno. Esse tipo de busca é bom para captar sinônimos e parafraseamento (ex.: "bicho que vive na água e na terra" ≈ "anfíbio"), mas é ruim para garantir que uma palavra técnica específica pese o suficiente quando aparece literalmente no texto-alvo. No caso 6, trocar "anfíbios" por "anuros" (termo técnico que aparece literalmente nas fichas do SALVE) mudou drasticamente o ranking — 6 de 10 resultados viraram fichas de espécies reais de anfíbio, contra 1 de 5 no baseline. Isso é sintoma clássico de falta de busca léxica: um mecanismo tipo **BM25** (algoritmo clássico de busca por palavra-chave, usado por motores como Elasticsearch) daria peso extra a documentos que contêm as palavras exatas da pergunta, complementando o que a busca vetorial não capta bem.

4. **Sem filtro de fonte, PANs dominam SALVE no ranking.**
   A coleção tem duas "formas" de conteúdo bem diferentes: os PANs são PDFs longos com texto corrido (parágrafos de várias frases, redação institucional), e o SALVE é uma base estruturada por espécie, com fichas curtas e objetivas (seções como "Referências", "Ameaças", "Conservação", cada uma virando um chunk pequeno). Quando filtramos só por `salve` (caso 4), o próprio SALVE já traz várias espécies corretas com bom score (0.55–0.58). Mas no baseline sem filtro, nenhuma ficha SALVE aparece nos top 5 — só a partir da posição 12 no caso top_k=20. A coleção `pans` tem menos documentos distintos que o `salve` (663 vs 1816), mas parece ter chunks de texto corrido mais longos e mais redundantes entre si sobre o mesmo bioma, o que os deixa em vantagem estrutural pura de similaridade vetorial.

5. **Chunking pode estar amplificando o problema.**
   Hipótese derivada das anteriores, não confirmada diretamente nesta tarefa: se o processo de chunking (`gerar_chunks.py`) corta o parágrafo introdutório do bioma como um chunk isolado — sem juntá-lo ao conteúdo específico do plano que vem na sequência — esse chunk "genérico" vira uma unidade recuperável por si só. Como ele se repete quase igual entre dezenas de PANs de assuntos diferentes, qualquer pergunta que cite o nome do bioma tem chance desproporcional de trazer um desses. Não olhamos o código de chunking nesta tarefa para confirmar isso — é uma hipótese a validar, não um fato observado diretamente nos dados do teste.

## Opções para decisão

Nenhuma das opções abaixo foi implementada nesta tarefa — são caminhos para Júlia avaliar e decidir.

1. **Busca híbrida (BM25/léxica + vetorial), com fusão de score.**
   Ideia: rodar duas buscas em paralelo — a vetorial atual (semântica) e uma léxica por palavra-chave (BM25) — e combinar os dois rankings num score final (técnica comum chamada *Reciprocal Rank Fusion*, ou combinação ponderada de scores). O Qdrant já suporta isso nativamente via *sparse vectors* (vetores esparsos, que representam presença/peso de palavras, ao invés dos vetores densos de embeddings semânticos), então não seria necessário trocar de banco vetorial.
   Prós: ataca diretamente a hipótese 3 — resgata documentos com correspondência exata de termo mesmo quando a similaridade semântica geral é modesta (ganho observado no caso 6); reduz a chance de boilerplate genérico dominar o ranking só por similaridade vetorial.
   Contras: mais peça de infraestrutura para manter (índice léxico esparso, além do denso) e mais um hiperparâmetro para calibrar (o peso relativo entre léxico e semântico) — sem esse ajuste, corre o risco de simplesmente trocar um viés por outro.

2. **Revisão da estratégia de chunking** (separar boilerplate de conteúdo específico, ou reduzir redundância entre PANs).
   Ideia: mudar como o texto é cortado em pedaços antes de gerar embeddings — por exemplo, detectar e marcar parágrafos de "contexto compartilhado" (como a introdução do bioma) separadamente do "conteúdo específico do plano", ou deduplicar chunks quase-idênticos entre documentos diferentes antes de indexar.
   Prós: ataca a causa na raiz (hipóteses 2 e 5) — se o boilerplate parar de competir como resultado autônomo, menos "ruído genérico" aparece no topo do ranking para qualquer pergunta que mencione o bioma.
   Contras: é a opção de maior esforço — envolve reprocessar os ~59 mil chunks já gerados e indexados, e criar uma heurística confiável para diferenciar "boilerplate" de "conteúdo relevante" sem descartar contexto legítimo (às vezes o parágrafo introdutório do bioma *é* relevante, dependendo da pergunta).

3. **Confirmar cobertura do corpus e decidir a política de resposta quando não há documento-síntese — checagem já feita, política já implementada.**
   A checagem manual (`01_fontes_web/pans/_indice_pans.json` e `06_inventario/inventario_fontes.xlsx`) confirmou que não existe PAN de Herpetofauna do Cerrado no catálogo oficial do ICMBio — não é lacuna de coleta/indexação (ver hipótese 1 atualizada). Com isso resolvido, a política de resposta foi implementada: `backend/services/geracao.py::PROMPT_SISTEMA` agora instrui explicitamente o LLM a sintetizar uma resposta agregada quando vários trechos parciais (ex.: várias fichas SALVE) cobrem a pergunta em conjunto, citando cada um, em vez de exigir um único trecho completo.
   Prós: ataca a causa raiz (hipótese 1) diretamente — a resposta do sistema passa a refletir a realidade da fonte ("não há PAN dedicado, mas várias espécies têm Cerrado como bioma, segundo o SALVE") em vez de silenciosamente falhar por falta de um documento único.
   Contras: por si só não resolve o problema de ranking (hipóteses 2 e 4) — a política de síntese só ajuda se os trechos certos (fichas SALVE) chegarem no top-k retornado pela busca; ver Ação 2 (roteamento por fonte) para isso.

4. **Roteamento/priorização de fonte para perguntas do tipo "lista de espécies por bioma" — IMPLEMENTADO.**
   Implementado em `backend/services/roteamento.py`: `detectar_fonte_prioritaria` é uma heurística por palavra-chave que reconhece o padrão "quais/lista de espécies/anfíbios/répteis ... ocorrem/existem em <lugar>"; quando casa (e o cliente não pediu uma fonte explicitamente), `buscar_chunks_priorizados` reserva as vagas do `top_k` para `salve` primeiro, completando com a busca sem filtro só se sobrar vaga. Usado no endpoint `/perguntar` (`backend/routers/perguntar.py`); o endpoint de depuração `/buscar` continua usando `buscar_chunks` puro, sem a heurística, para servir como visão do retrieval "cru".
   Prós: mais barato e rápido de implementar que as opções 1 e 2; o caso 4 do diagnóstico já mostrava que esse filtro sozinho resolve boa parte do problema para esse tipo específico de pergunta.
   Contras: é um "remendo" para um padrão de pergunta específico — perguntas ambíguas (ex.: "o que diz o PAN sobre o Cerrado?") podem ser roteadas errado, e o problema de ranking geral (boilerplate vencendo textos específicos) continua existindo para perguntas fora desse padrão — só a busca híbrida (opção 1, ainda não implementada) ataca isso de forma geral.
