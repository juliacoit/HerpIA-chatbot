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

## Hipóteses

1. **Falta de documento consolidado sobre herpetofauna do Cerrado.** Confirmado na seção "Cobertura do corpus": não há PAN de Herpetofauna do Cerrado indexado, só PANs regionais (Nordeste, Sul, Sudeste, Espinhaço, Insular). A informação sobre anfíbios do Cerrado existe, mas pulverizada em milhares de fichas SALVE individuais (uma espécie por chunk/seção), não em um documento-lista único.

2. **Boilerplate quase-idêntico entre PANs de táxons diferentes infla o score de trechos genéricos.** O parágrafo introdutório "O Cerrado é..." aparece, com poucas variações, em pelo menos 7 PANs de grupos não relacionados a anfíbios (cactáceas, aves, lepidópteros, pato-mergulhão, cervídeos, pequenos mamíferos, onça-pintada — ver casos 1 e 2). O embedding da pergunta "anfíbios no Cerrado" combina fortemente com a descrição genérica do bioma (rica em "Cerrado", "biodiversidade", "espécies"), o que explica a faixa estreita de scores 0.61–0.66 do baseline: são trechos quase-duplicados competindo entre si por semelhança textual ao bioma, não por relevância à pergunta sobre anfíbios.

3. **Busca puramente vetorial sub-pondera termos exatos.** A palavra "anfíbio"/"anfíbios" isolada não empurra o ranking na direção certa; já o termo mais técnico "anuros" (caso 6) — que aparece literalmente no texto de várias fichas SALVE — muda o ranking de forma acentuada (6/10 sinalizados vs 1/5 no baseline). Isso é consistente com ausência de um componente léxico/BM25 que resgate documentos com correspondência exata de palavra, mesmo quando a similaridade semântica geral é modesta.

4. **Sem filtro de fonte, PANs dominam SALVE no ranking.** O caso 4 (fontes=["salve"]) mostra que, isolado, o SALVE tem bom conteúdo sobre anfíbios do Cerrado (scores 0.55–0.58, várias espécies corretas). Mas no baseline sem filtro, nenhuma ficha SALVE aparece nas top 5 — só a partir da posição 12 no caso top_k=20. A coleção `pans` tem menos documentos distintos que o `salve` (663 vs 1816), mas parece ter chunks de texto corrido mais longos e mais redundantes entre si sobre o mesmo bioma, o que os deixa em vantagem competitiva pura de similaridade vetorial.

5. **Chunking pode estar amplificando o problema.** Se o boilerplate introdutório do bioma é isolado como chunk próprio (hipótese 2) sem diferenciação de "contexto compartilhado" vs. "conteúdo específico do plano", qualquer pergunta que mencione "Cerrado" tem uma probabilidade desproporcional de trazer esse tipo de trecho no top-k, independente do assunto (anfíbios, aves, mamíferos, etc.).

## Opções para decisão

Nenhuma das opções abaixo foi implementada nesta tarefa — são caminhos para Júlia avaliar e decidir.

1. **Busca híbrida (BM25/léxica + vetorial), com fusão de score.**
   Prós: resgata correspondência exata de termos como "anuros", "herpetofauna" que a busca puramente semântica está sub-ponderando (ganho observado no caso 6); reduz a chance de boilerplate genérico dominar o ranking só por similaridade vetorial.
   Contras: mais complexidade de infraestrutura (índice léxico adicional — ex.: sparse vectors do Qdrant ou motor separado) e mais um parâmetro a calibrar (peso da fusão léxico/vetorial).

2. **Revisão da estratégia de chunking** (separar boilerplate de conteúdo específico, ou reduzir redundância entre PANs).
   Prós: ataca a hipótese 2/5 diretamente — menos chunks quase-duplicados de "descrição do bioma" competindo no top-k para qualquer pergunta que mencione o nome do bioma.
   Contras: retrabalho sobre os 59 mil chunks já gerados/indexados; exige uma heurística confiável para distinguir "boilerplate compartilhado" de "conteúdo específico do plano" sem perder contexto legítimo.

3. **Confirmar cobertura do corpus e decidir a política de resposta quando não há documento-síntese.**
   Prós: ataca a causa raiz (hipótese 1) — nenhuma melhora de ranking resolve totalmente uma pergunta para a qual não existe PAN específico; envolve checar `01_fontes_web/pans` e o inventário (`06_inventario/inventario_fontes.xlsx`) para confirmar que de fato não há PAN de Herpetofauna do Cerrado a indexar, e definir se o chatbot deve responder agregando fichas SALVE nesse caso.
   Contras: pode confirmar que a resposta correta é "não há PAN dedicado, mas várias espécies têm Cerrado como bioma" — isso é uma resposta legítima do sistema, não um bug de indexação, e precisa ser tratada na lógica de geração (fora do escopo desta tarefa).

4. **Roteamento/priorização de fonte para perguntas do tipo "lista de espécies por bioma".**
   Prós: o caso 4 mostra que filtrar por `fontes=["salve"]` já resolve boa parte do problema para esse tipo de pergunta, sem tocar em embeddings; uma heurística leve (ou um passo de classificação da pergunta) que priorize SALVE quando a pergunta pede lista de espécies por bioma/táxon poderia ajudar de forma barata.
   Contras: lógica de roteamento heurística pode errar em perguntas ambíguas ou que genuinamente querem contexto de PAN; não resolve o caso geral (perguntas que não se encaixam nesse padrão continuam sujeitas aos mesmos problemas de ranking).
