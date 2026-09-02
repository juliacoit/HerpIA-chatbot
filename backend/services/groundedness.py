"""Verificação de groundedness pós-geração (adianta trabalho da Fase 8).

`evidencia_suficiente` em `PerguntarResponse` só reflete se chunks foram
recuperados — não se a resposta do LLM realmente se apoiou neles. O teste de
domínio (`diagnosticos/teste-perguntas-dominio.md`, achado 1) encontrou duas
alucinações reais que esse campo não pegou, e mostrou que reforço de prompt
sozinho não elimina o problema de forma confiável (o caso G1 falhou em 3 de
3 execuções mesmo depois do prompt ser reforçado contra especulação).

Este módulo tem três camadas, com papéis diferentes — a divisão não é
arbitrária, é resultado de testar cada peça isoladamente contra casos reais
(ver histórico de commits) e descobrir que nem toda checagem serve pra tudo:

1. `checar_ancoras_parenteses` — heurística barata, sem chamada a LLM, e
   **decide sozinha (hard gate)**. Extrai nomes imediatamente seguidos de
   parênteses (padrão "Genero espécie (Autor, Ano)", o formato consistente
   de citação científica neste corpus) e confere se aparecem nos trechos ou
   na pergunta. Alta precisão nesse domínio — praticamente só dispara em
   nomes de espécie/citação, então um nome que não aparece em lugar nenhum
   é fabricação com bastante confiança (o padrão exato do achado I1, o
   inseto "Arapapás" inventado). Motivo de ser hard gate: testado
   diretamente contra o juiz por LLM (camada 3) informado desse mesmo
   termo suspeito, o juiz ignorou o aviso e aprovou a fabricação em 3 de 3
   execuções — não dá pra confiar só no juiz pra esse tipo de caso.

2. `checar_ancoras_meio_frase` — mesma ideia, mas para palavras capitalizadas
   soltas no meio de uma cláusula (não só nome+parênteses). **Não decide
   sozinha** — só vira uma pista para a camada 3. Testado como hard gate
   primeiro e a taxa de falso positivo foi alta demais para este domínio:
   escrita institucional/administrativa capitaliza termo de categoria o
   tempo todo ("Parques Nacionais", "Menos Preocupante"), e regex não
   distingue isso de um nome realmente inventado — chegou a reter respostas
   corretas por causa da palavra "Vale" (parte do nome popular já citado na
   própria pergunta) e de "Parques"/"Nacionais" (categoria administrativa).

3. `verificar_com_llm` — pede ao próprio LLM para julgar a resposta contra
   os trechos, recebendo os termos suspeitos da camada 2 como pista (não
   veredito). É o único jeito de pegar o padrão do achado G1 (vocabulário
   que *está* nos trechos, mas atribuído ao documento errado — a checagem
   lexical não pega isso, as palavras realmente aparecem). Mas é fraco:
   testes diretos contra texto conhecidamente alucinado mostraram taxa de
   acerto baixa e inconsistente (0 a 1 em 3 execuções, mesmo modelo local
   que gerou a resposta original) — fica como camada complementar, não como
   garantia. O mesmo juiz fraco também erra pro outro lado: em várias
   baterias (H2, F2) rejeitou abstenções honestas ("os trechos não contêm
   informação sobre X") como se fossem não-fundamentadas — abstenção
   correta não é fabricação, então `checar_abstencao_honesta` (camada 0,
   abaixo) intercepta esse padrão antes de chamar o juiz.

0. `checar_abstencao_honesta` — roda só depois do hard gate (camada 1) já
   ter aprovado (sem isso, uma abstenção poderia mascarar uma fabricação de
   entidade escondida no mesmo texto). Se a resposta já é, lexicalmente, uma
   admissão de falta de evidência, não há o que o juiz por LLM possa
   contribuir além de arriscar um falso negativo — decide sozinha (hard
   pass), sem gastar uma chamada extra ao LLM.

Falha fechada por escolha deliberada em toda a cadeia: qualquer veredito
ambíguo do juiz (não começa com "SIM" inequívoco) é tratado como não
fundamentado, e qualquer termo sem apoio na camada 1 já basta pra reter.
Para este projeto, o custo de reter uma resposta boa é menor que o custo de
mostrar uma resposta inventada (ver CLAUDE.md, "Regras para respostas do
chatbot") — mas isso não torna a checagem infalível, só estritamente melhor
que `evidencia_suficiente`, que hoje não pega nenhuma das duas alucinações
documentadas.
"""

import re

from backend.schemas import ChunkRecuperado
from backend.services.llm import LLMClient

MENSAGEM_NAO_FUNDAMENTADA = (
    "Não foi possível confirmar que a resposta gerada está totalmente "
    "apoiada nos trechos recuperados da base de conhecimento, então ela "
    "foi retida para evitar apresentar uma informação não verificada. "
    "Tente reformular a pergunta de forma mais específica ou consulte "
    "diretamente as fontes citadas abaixo."
)

# Nome imediatamente seguido de parênteses — o padrão consistente de nome
# científico no corpus ("Genero espécie (Autor, Ano)", "Nome (Sinônimo)").
_PADRAO_ENTIDADE_PARENTESES = re.compile(
    r"\b([A-ZÀ-Ý][\wà-ÿ]*(?:\s[a-zà-ÿ][\wà-ÿ]*){0,3})\s*\("
)
# "Genero espécie" (ou "Nome epíteto") liderando um item de lista — outra
# posição de alta precisão: é onde o LLM tipicamente introduz o nome da
# entidade sendo discutida no item (espécie, documento...). Foi descoberta
# como lacuna real: uma fabricação (falso gênero "Leptotrombidium
# akarai/cervi", com doença fictícia) passou pelo gate porque usava
# "1. Nome epíteto - descrição" (traço, não parênteses) — o padrão de
# parênteses não pega isso, e a regra de "ignorar a primeira palavra da
# cláusula" do checar_ancoras_meio_frase existe justamente pra ignorar
# posições como essa, então também não pegava.
#
# Exige DUAS palavras (padrão binomial), não uma só: a primeira versão
# aceitava uma única palavra capitalizada isolada, e isso pegava qualquer
# palavra comum do português que abre um item/sub-item de lista — pronome
# ("- Ela está classificada..."), rótulo de campo ("- Biomas: ..."),
# cabeçalho de item ("2. **Representação dos Trechos**: ...") — nenhum
# nome de entidade de verdade, um bug real encontrado no teste (bateria de
# 2026-08-19, achados A3/B2/C1: 3 respostas corretas retidas por causa
# disso). Duas palavras sozinhas ainda não bastam (ver
# `_CONECTIVOS_E_PRONOMES_COMUNS` abaixo) porque frases como "Representação
# dos" ou "Ela está" também têm duas palavras.
_PADRAO_ITEM_LISTA_ENTIDADE = re.compile(
    r"(?:^|\n)\s*(?:\d+[.)]|[-•*])\s*\*{0,2}([A-ZÀ-Ý][a-zà-ÿ]{2,}\s[a-zà-ÿ]{2,})\b",
    re.MULTILINE,
)
# Conectivos, artigos, pronomes e formas verbais comuns que aparecem como
# segunda palavra de uma falsa dupla ("Representação dos", "Ela está",
# "Isso é") — se qualquer palavra do candidato cair aqui, não é um nome de
# entidade no padrão binomial, é só o início comum de uma frase em português.
_CONECTIVOS_E_PRONOMES_COMUNS = {
    "a", "o", "as", "os",
    "de", "da", "do", "dos", "das", "e", "ou", "em", "no", "na", "nos", "nas",
    "com", "para", "por", "entre", "sobre", "segundo", "conforme", "que",
    "ao", "aos", "um", "uma", "uns", "umas",
    "ela", "ele", "elas", "eles", "isso", "isto", "aquilo",
    "esta", "este", "essa", "esse", "estas", "estes", "essas", "esses",
    "aqui", "ali", "lá", "assim",
    "é", "são", "foi", "foram", "está", "estão", "esteve", "estiveram",
    "tem", "têm", "teve", "tiveram", "há",
    "cada", "todo", "toda", "todos", "todas", "qualquer", "quaisquer",
    "algum", "alguma", "alguns", "algumas", "nenhum", "nenhuma",
    "outro", "outra", "outros", "outras", "mesmo", "mesma", "mesmos", "mesmas",
    "tal", "tais", "cujo", "cuja", "cujos", "cujas",
    # Pronomes possessivos — faltavam (achado da revisão de baterias de
    # 2026-08-21: "Seu habitat", "Sua categoria" retidos como falso
    # positivo por começarem item de lista com um possessivo, não um nome).
    "seu", "sua", "seus", "suas", "nosso", "nossa", "nossos", "nossas",
    "meu", "minha", "meus", "minhas", "teu", "tua", "teus", "tuas",
    # Conectivos/advérbios de transição e verbo "existir" — faltavam (achado
    # da bateria `2026-09-02_16h51`, rodada de reteste do fix dos
    # substantivos-gatilho abaixo): "Além disso" (item de lista começando
    # com transição textual) e "Existem indicações" (verbo conjugado de
    # "existir" na 3ª pessoa do plural — mesma função de "há", já coberto,
    # mas "existir" não estava na lista) retidos por engano, mesma
    # assinatura de falso positivo institucional/genérico do achado A2.
    "além", "disso", "como", "existe", "existem", "existia", "existiam",
}
# Verbo no infinitivo liderando item de lista de ação — achado da revisão da
# bateria `2026-08-21_16h55` (caso A2): documentos institucionais (PANs)
# listam ações no infinitivo ("Estabelecer estratégias...", "Realizar
# diagnóstico...", "Implementar protocolo..."), padrão estruturalmente
# idêntico ao de "Nome epíteto" liderando item de lista que
# `_PADRAO_ITEM_LISTA_ENTIDADE` foi desenhado pra pegar — mas não é uma
# entidade fabricada, é uma frase de ação comum em texto burocrático.
# `_tem_suporte` exige a frase de duas palavras inteira e contígua no texto
# disponível, então mesmo com as duas palavras presentes separadamente nos
# trechos (vocabulário comum de PAN), a combinação exata pode não bater —
# falso positivo mesmo sem fabricação nenhuma.
#
# Checagem morfológica (terminação -ar/-er/-ir na primeira palavra) em vez
# de lista fixa de verbos: cobre a classe gramatical inteira em vez de só os
# casos pontuais já encontrados, do mesmo jeito que os pronomes possessivos
# tiveram que ser corrigidos um a um antes. Risco aceito: pega também
# substantivos/adjetivos comuns com a mesma terminação ("Regular",
# "Familiar", "Celular") — tradeoff já aceito em outras camadas deste
# módulo (ver `checar_ancoras_meio_frase`) porque, neste domínio, o custo de
# reter uma resposta boa é menor que o de mostrar uma fabricação (CLAUDE.md).
_PADRAO_VERBO_INFINITIVO = re.compile(r"^[a-zà-ÿ]{3,}(?:ar|er|ir)$")
# Substantivos comuns que abrem uma frase institucional/acadêmica genérica —
# achado da revisão da bateria `2026-08-25_15h45` (casos C3, F1, J1):
# "Evidências indicam" (substantivo + verbo conjugado na 3ª pessoa do
# plural, terminação "-am"/"-em", não infinitivo), "Estudos específicos"/
# "Estudos recentes" (substantivo + adjetivo), "Mudança climática", "Práticas
# pesqueiras" — mesma assinatura do achado A2 (frase comum de escrita
# institucional tratada como nome de entidade só por liderar um item de
# lista ou vir seguida de parênteses), mas a segunda palavra não é mais um
# verbo no infinitivo, então `_PADRAO_VERBO_INFINITIVO` não cobre.
#
# Diferente do infinitivo (uma classe gramatical fechada, checável por
# sufixo), verbo conjugado tem dezenas de terminações possíveis por
# tempo/pessoa e adjetivo não tem terminação que o distinga de substantivo
# em português — não há regra morfológica barata equivalente. Lista de
# gatilhos fixa em vez de regra morfológica, do mesmo jeito que já foi
# feito para conectivos/pronomes (`_CONECTIVOS_E_PRONOMES_COMUNS`), em vez de
# tentar achar uma regra gramatical geral. Checa só a PRIMEIRA palavra do
# candidato (como o infinitivo) porque em todos os casos catalogados até
# agora é o substantivo genérico que abre a frase, não a segunda palavra —
# nenhum nome de espécie/documento real no corpus começa com estas
# palavras (gêneros são nomes próprios em latim; documentos começam com
# "PAN", que não bate no padrão por ser todo maiúsculo).
_SUBSTANTIVOS_GATILHO_COMUNS = {
    "estudo", "estudos", "evidência", "evidências",
    "dado", "dados", "resultado", "resultados",
    "informação", "informações", "análise", "análises",
    "registro", "registros", "levantamento", "levantamentos",
    "pesquisa", "pesquisas", "relatório", "relatórios",
    "observação", "observações", "medida", "medidas",
    "avaliação", "avaliações", "investigação", "investigações",
    "trabalho", "trabalhos", "indicador", "indicadores",
    "estratégia", "estratégias", "diretriz", "diretrizes",
    "norma", "normas", "política", "políticas",
    "prática", "práticas", "mudança", "mudanças",
    "área", "áreas", "categoria", "categorias",
    "população", "populações", "espécie", "espécies",
}
# Palavra capitalizada no meio de uma cláusula (não a primeira da cláusula).
_PALAVRA_CAPITALIZADA = re.compile(r"^[A-ZÀ-Ý][a-zà-ÿ]{2,}$")
# Quebra em qualquer pontuação (vírgula, parênteses, aspas...) — só espaço
# não conta como quebra. Sem isso, "No Cerrado, vivem espécies" perderia a
# vírgula ao extrair só letras e trataria "Cerrado" e "vivem" como
# adjacentes, quando na verdade estão em cláusulas diferentes.
_QUEBRA_PONTUACAO = re.compile(r"[^\sA-Za-zÀ-ÿ]+")
_PADRAO_MARCADOR_LISTA = re.compile(r"^\s*(?:\d+[.)]|[-•*])\s*")

# Frases que o modelo usa de fato, neste corpus, para admitir falta de
# evidência (mesma família de sinalização usada em
# scripts/teste_perguntas_dominio.py:PALAVRAS_INSUFICIENCIA, mas aqui vira
# critério de decisão, não só heurística de leitura). Abstenção honesta não
# é fabricação — mesmo mencionando termos "sem apoio", a resposta não está
# afirmando nada que não esteja nos trechos.
#
# Regex em vez de lista de substrings literais: a revisão das baterias de
# 2026-08-21 (diagnosticos/baterias/*.md, casos F3/H2) achou, com o texto
# original recuperado do log do servidor, duas abstenções honestas reais que
# a lista literal original não pegava — "não contém informaçÕES" (plural,
# a lista só tinha o singular) e "não contém NENHUMA informação" (palavra
# inserida) — e foram incorretamente rejeitadas pelo juiz por LLM por causa
# disso. O padrão flexível abaixo cobre singular/plural e a inserção de
# "nenhum(a)" sem precisar enumerar cada variante à mão. Não cobre resposta
# em outro idioma (achado F2 na mesma revisão: o modelo respondeu em inglês)
# — isso é um problema diferente (idioma da geração, não fraseio), fora do
# escopo desta checagem lexical em português.
_PADRAO_ABSTENCAO = re.compile(
    r"n[ãa]o\s+h[áa]\s+evid[êe]ncia"
    r"|n[ãa]o\s+encontrei"
    r"|n[ãa]o\s+h[áa]\s+informa[çc][ãa]o\s+suficiente"
    r"|n[ãa]o\s+foi\s+poss[íi]vel\s+encontrar"
    r"|n[ãa]o\s+consta\b"
    r"|n[ãa]o\s+tenho\s+informa[çc][õo]es"
    r"|base\s+de\s+conhecimento\s+n[ãa]o"
    r"|n[ãa]o\s+h[áa]\s+dados\s+suficientes"
    r"|n[ãa]o\s+cont[êeé]m\s+(?:nenhum[ao]\s+)?(?:informa[çc][ãa]o|informa[çc][õo]es|refer[êe]ncia)"
    r"|n[ãa]o\s+fornece(?:m)?\s+informa[çc][õo]es"
)


def checar_abstencao_honesta(resposta: str) -> bool:
    """Hard pass: a resposta já admite, em português claro, que os trechos
    não bastam pra responder. Ver docstring do módulo (camada 0) para o
    motivo de isso decidir sozinho em vez de ir pro juiz por LLM."""
    return _PADRAO_ABSTENCAO.search(resposta.lower()) is not None


def _texto_disponivel(chunks: list[ChunkRecuperado], pergunta: str) -> str:
    """Trechos + pergunta, em minúsculas — a pergunta conta como fonte
    válida porque o LLM pode legitimamente citar de volta um termo que o
    próprio usuário já forneceu (ex.: pergunta "jararaca-do-Vale (Bothrops
    marmoratus)?" — "Vale" não precisa aparecer nos trechos pra resposta
    poder repetir o nome popular que já veio na pergunta; isso não é
    fabricação, é eco do que foi perguntado)."""
    return " ".join(c.texto for c in chunks).lower() + " " + pergunta.lower()


def _tem_suporte(candidato: str, texto_disponivel: str) -> bool:
    """Presença por PALAVRA INTEIRA (\\b...\\b), não substring — checagem por
    substring simples deixa passar coisas como "verde" "encontrado" dentro
    de "esverdeada" (cor da água em um trecho sem relação nenhuma com o
    candidato "Verde" de uma resposta), fazendo o gate achar que um nome
    inventado está apoiado quando na verdade só bateu num pedaço de outra
    palavra.
    """
    return re.search(r"\b" + re.escape(candidato.lower()) + r"\b", texto_disponivel) is not None


def _eh_provavel_entidade(candidato: str) -> bool:
    """Descarta candidatos do padrão binomial ("Palavra1 palavra2") cuja
    segunda palavra (ou qualquer palavra do candidato) é um conectivo,
    artigo, pronome ou forma verbal comum, ou cuja primeira palavra é um
    verbo no infinitivo ou um substantivo-gatilho comum (item de lista de
    ação ou frase institucional genérica, não nome de entidade) — sinal de
    que é o início de uma frase qualquer, não um nome de espécie/documento."""
    palavras = candidato.lower().split()
    if any(p in _CONECTIVOS_E_PRONOMES_COMUNS for p in palavras):
        return False
    if _PADRAO_VERBO_INFINITIVO.match(palavras[0]) is not None:
        return False
    return palavras[0] not in _SUBSTANTIVOS_GATILHO_COMUNS


def checar_ancoras_estruturais(
    resposta: str, chunks: list[ChunkRecuperado], pergunta: str = ""
) -> tuple[bool, list[str]]:
    """Hard gate: nomes em posições estruturais de alta precisão — seguidos
    de parênteses, ou liderando um item de lista — que não aparecem em
    nenhum trecho nem na pergunta. Ver docstring do módulo (camada 1) para
    o motivo de essas duas posições serem confiáveis o bastante pra decidir
    sozinhas neste domínio.
    """
    candidatos = {
        m.group(1).strip() for m in _PADRAO_ENTIDADE_PARENTESES.finditer(resposta)
        if _eh_provavel_entidade(m.group(1))
    }
    candidatos.update(
        m.group(1) for m in _PADRAO_ITEM_LISTA_ENTIDADE.finditer(resposta)
        if _eh_provavel_entidade(m.group(1))
    )
    if not candidatos:
        return True, []
    texto_disponivel = _texto_disponivel(chunks, pergunta)
    sem_apoio = sorted(c for c in candidatos if not _tem_suporte(c, texto_disponivel))
    return len(sem_apoio) == 0, sem_apoio


def _candidatos_meio_frase(fragmento: str) -> set[str]:
    """Palavras capitalizadas no meio de uma cláusula (não a primeira,
    maiúscula só por estar no início da cláusula, não por ser nome próprio).

    Checa palavra por palavra, não frase/bigrama: um nome de uma palavra só
    (ex. "Monitora", usado sozinho depois de já apresentado como "Programa
    Monitora") pareado com a palavra seguinte ("Monitora se destaca") criaria
    um bigrama que não aparece literalmente nos trechos mesmo a palavra
    aparecendo — mesmo problema com termos de categoria de duas palavras
    capitalizadas (ex. "Menos Preocupante" seguido de "na avaliação").
    Checar a palavra isolada evita esse tipo de falso positivo.
    """
    candidatos = set()
    for clausula in _QUEBRA_PONTUACAO.split(fragmento):
        palavras = clausula.split()
        candidatos.update(p for p in palavras[1:] if _PALAVRA_CAPITALIZADA.match(p))
    return candidatos


def checar_ancoras_meio_frase(
    resposta: str, chunks: list[ChunkRecuperado], pergunta: str = ""
) -> tuple[bool, list[str]]:
    """Soft signal (ver docstring do módulo, camada 2) — NÃO usar como
    veredito final sozinho, só como pista pro juiz por LLM. Taxa de falso
    positivo alta demais neste domínio pra decidir sozinha.
    """
    candidatos: set[str] = set()
    for fragmento in re.split(r"(?<=[.!?:])\s+|\n", resposta):
        fragmento = _PADRAO_MARCADOR_LISTA.sub("", fragmento)
        candidatos.update(_candidatos_meio_frase(fragmento))
    if not candidatos:
        return True, []
    texto_disponivel = _texto_disponivel(chunks, pergunta)
    sem_apoio = sorted(c for c in candidatos if not _tem_suporte(c, texto_disponivel))
    return len(sem_apoio) == 0, sem_apoio


_PROMPT_JUIZ = (
    "Você é um verificador de fidelidade (groundedness) para um sistema de "
    "perguntas e respostas sobre herpetofauna brasileira. Sua única tarefa "
    "é julgar se a RESPOSTA abaixo está totalmente apoiada pelos TRECHOS "
    "fornecidos — sem inventar nada que não esteja neles, e sem descrever "
    "o conteúdo de um documento como se fosse de outro documento diferente "
    "do que a pergunta pede. Síntese de vários trechos parciais conta como "
    "apoiada, desde que cada afirmação individual esteja em algum trecho. "
    "Termos administrativos/institucionais comuns (nomes de categoria como "
    "\"Área de Proteção Ambiental\", siglas, sinônimos, ou palavras que já "
    "vieram na própria pergunta do usuário) NÃO contam como fabricação — "
    "só conte como fabricação um nome, dado ou afirmação específica que não "
    "tem base em nenhum trecho nem na pergunta. ATENÇÃO: frases como "
    "\"podemos inferir que provavelmente\", \"provavelmente cobriria\", "
    "\"é possível que\" são especulação disfarçada de resposta, mesmo "
    "quando parecem cautelosas — se a resposta descreve o que um documento "
    "\"provavelmente\" diz em vez de citar o que os trechos realmente "
    "dizem sobre ele, isso NÃO está apoiado nos trechos, mesmo que as "
    "palavras individuais apareçam neles.\n\n"
    "TRECHOS:\n{trechos}\n\n"
    "PERGUNTA: {pergunta}\n\n"
    "RESPOSTA A JULGAR:\n{resposta}\n"
    "{aviso_lexico}\n"
    "A resposta está totalmente apoiada nos trechos, sem inventar nada e "
    "sem atribuir a um documento/processo diferente o conteúdo perguntado?\n"
    "Responda EXATAMENTE neste formato, com SIM ou NÃO sozinho na primeira "
    "linha:\n"
    "SIM ou NÃO\n"
    "Justificativa: <uma frase curta explicando por quê>"
)


async def verificar_com_llm(
    llm: LLMClient,
    pergunta: str,
    resposta: str,
    chunks: list[ChunkRecuperado],
    termos_suspeitos: list[str] | None = None,
) -> tuple[bool, str]:
    """Pede ao LLM para julgar a própria geração contra os trechos.

    Falha fechada: qualquer coisa que não seja um "SIM" inequívoco na
    primeira linha do veredito é tratada como não fundamentada.
    """
    trechos = "\n\n".join(
        f"[Trecho {i + 1} — fonte: {c.fonte}, documento: {c.documento}]\n{c.texto}"
        for i, c in enumerate(chunks)
    )
    aviso_lexico = ""
    if termos_suspeitos:
        aviso_lexico = (
            "\nAVISO AUTOMÁTICO (heurística, pode ser falso positivo): os "
            "termos a seguir aparecem na resposta mas não foram encontrados "
            "literalmente nos trechos nem na pergunta: "
            + ", ".join(termos_suspeitos)
            + ". Preste atenção redobrada a esses termos específicos ao "
            "julgar, mas não rejeite automaticamente só por causa deste "
            "aviso — confirme se é mesmo um nome/dado inventado.\n"
        )
    prompt = _PROMPT_JUIZ.format(
        trechos=trechos, pergunta=pergunta, resposta=resposta, aviso_lexico=aviso_lexico
    )
    veredito = await llm.generate(prompt)

    linhas = veredito.strip().splitlines()
    primeira_linha = linhas[0].strip().upper() if linhas else ""
    fundamentada = primeira_linha.startswith("SIM")

    justificativa = veredito.strip()
    if "Justificativa:" in veredito:
        justificativa = veredito.split("Justificativa:", 1)[1].strip()

    return fundamentada, justificativa


async def verificar_groundedness(
    llm: LLMClient, pergunta: str, resposta: str, chunks: list[ChunkRecuperado]
) -> tuple[bool, str | None]:
    """Roda as três camadas na ordem certa: primeiro o hard gate barato
    (nomes em posição estrutural de alta precisão), que já decide se
    falhar; senão, junta a pista da camada 2 (meio de frase) e deixa o
    veredito final com o juiz por LLM.
    """
    ancorada, sem_apoio = checar_ancoras_estruturais(resposta, chunks, pergunta)
    if not ancorada:
        return False, (
            "Verificação lexical (nome em posição estrutural de alta "
            "precisão — seguido de parênteses ou liderando item de lista — "
            "sem apoio em nenhum trecho nem na pergunta): " + "; ".join(sem_apoio)
        )

    if checar_abstencao_honesta(resposta):
        return True, None

    _, termos_suspeitos = checar_ancoras_meio_frase(resposta, chunks, pergunta)
    return await verificar_com_llm(llm, pergunta, resposta, chunks, termos_suspeitos)
