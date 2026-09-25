"""Bateria de perguntas de domínio para testar o pipeline completo do
HerpIA (RAN/ICMBio) (retrieval + roteamento por fonte + geração com LLM).

Diferente de scripts/diagnostico_retrieval.py (que chama buscar_chunks
diretamente, sem precisar do servidor HTTP), este script bate no endpoint
real POST /perguntar — precisa do backend (uvicorn) e do Ollama rodando,
porque o objetivo aqui é testar a experiência do usuário final: resposta
sintetizada + citações, não só o retrieval cru.

As perguntas cobrem o objetivo do projeto (respostas verificáveis sobre
herpetofauna, sempre citando fonte, dizendo explicitamente quando não há
evidência) e as fontes hoje indexadas (monitora, pans, salve — SEI ainda não
está autorizado/indexado). Ver categorias em CASOS_TESTE.

Uso:
    python scripts/teste_perguntas_dominio.py
    python scripts/teste_perguntas_dominio.py --url http://localhost:8000 --top-k 8
    python scripts/teste_perguntas_dominio.py --repeticoes 1 --categorias G,L

    Por padrão cada pergunta roda 3 vezes: o modelo local não fixa parâmetros
    de amostragem, então uma execução só não é evidência de correção. Critérios
    de avaliação em diagnosticos/criterios-avaliacao-bateria.md.

Saída:
    Cada execução grava um arquivo próprio em diagnosticos/baterias/,
    nomeado com data/hora e modelo (ex.: 2026-08-19_1743_qwen2.5-3b-instruct.md),
    e nunca sobrescreve execuções anteriores — a ideia é manter histórico
    completo de toda bateria já rodada, junto com a configuração exata usada
    (modelo, commit git, groundedness ligado/desligado, top_k etc.), para dar
    pra comparar runs entre si depois. Um índice cumulativo é mantido em
    diagnosticos/baterias/indice.md (uma linha por execução, nunca reescrito
    fora do append). O arquivo diagnosticos/teste-perguntas-dominio.md
    (análise manual, com histórico dos achados e correções) não é tocado por
    este script — é curado à mão, ver diagnosticos/baterias/ para os dados
    brutos de cada execução.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
DIR_BATERIAS = RAIZ / "diagnosticos" / "baterias"
ARQUIVO_INDICE = DIR_BATERIAS / "indice.md"
# Mesmo limiar do alerta do backend (backend/services/llm.py).
LIMIAR_ALERTA_CONTEXTO = 0.85

sys.path.insert(0, str(RAIZ))

# ---------------------------------------------------------------------------
# Bateria de perguntas — categorias definidas em conversa com Júlia,
# fundamentadas no objetivo do projeto (CLAUDE.md) e no corpus real já
# indexado (ver diagnosticos/retrieval-cerrado-anfibios.md para o
# levantamento de cobertura por fonte).
# ---------------------------------------------------------------------------
CASOS_TESTE: list[dict] = [
    # A — Cobertura básica por fonte
    {
        "id": "A1", "categoria": "A — cobertura básica (SALVE)",
        "pergunta": "Qual o status de conservação da jararaca-do-Vale (Bothrops marmoratus)?",
        "objetivo": "Confirmar recuperação e resposta correta para consulta simples de espécie via SALVE.",
    },
    {
        "id": "A2", "categoria": "A — cobertura básica (PANs)",
        "pergunta": "Quais são os objetivos do PAN Herpetofauna do Espinhaço?",
        "objetivo": "Confirmar recuperação e resposta correta para consulta sobre um PAN específico.",
    },
    {
        "id": "A3", "categoria": "A — cobertura básica (Monitora)",
        "pergunta": "O que é o Programa Monitora do ICMBio e como funciona a amostragem de formas de vida da vegetação?",
        "objetivo": "Confirmar recuperação e resposta correta usando material do Monitora.",
    },
    # B — Síntese multi-fonte. Redesenhado em 2026-08-21: as 3 perguntas
    # originais (répteis/anfíbios por bioma, quelônios por categoria de
    # risco) roteavam quase sempre só pro SALVE — testavam síntese
    # multi-ESPÉCIE dentro de uma fonte só, não síntese multi-FONTE de
    # verdade (ver bateria 2026-08-19: B1/B2/B3 citaram 100% [salve]).
    # As perguntas abaixo foram escolhidas/confirmadas (via
    # backend.services.roteamento.detectar_fonte_prioritaria) para NÃO
    # disparar a heurística de priorização de SALVE, e exigem
    # explicitamente cruzar SALVE (status/categoria de risco) com PANs
    # (ações/cobertura) e/ou Monitora (metodologia) — uma fonte só não
    # basta pra responder por completo.
    {
        "id": "B1", "categoria": "B — síntese multi-fonte",
        "pergunta": (
            "Quais ações de conservação o PAN Herpetofauna do Sul prevê "
            "para as espécies avaliadas em risco crítico (CR) segundo o "
            "SALVE?"
        ),
        "objetivo": (
            "Exige cruzar avaliação de risco do SALVE (quais espécies são "
            "CR) com as ações específicas listadas no PAN do Sul para essas "
            "espécies — uma resposta só com SALVE (sem ações) ou só com o "
            "PAN (sem confirmar CR) estaria incompleta."
        ),
    },
    {
        "id": "B2", "categoria": "B — síntese multi-fonte",
        "pergunta": (
            "Como os protocolos do Programa Monitora se relacionam com as "
            "espécies de quelônios cobertas pelo PAN Quelônios?"
        ),
        "objetivo": (
            "Exige combinar uma fonte metodológica (Monitora) com uma fonte "
            "de plano de ação (PAN Quelônios) — testa se o sistema consegue "
            "sintetizar entre um documento de método e um de espécies/ações, "
            "não só listar espécies de uma fonte só."
        ),
    },
    {
        "id": "B3", "categoria": "B — síntese multi-fonte",
        "pergunta": (
            "Das espécies de quelônios classificadas como Vulnerável ou "
            "pior no SALVE, quais estão cobertas por algum PAN coordenado "
            "pelo RAN?"
        ),
        "objetivo": (
            "Metade da resposta vem do SALVE (quais espécies são VU/EN/CR) "
            "e metade dos PANs (cobertura institucional) — checa se o "
            "sistema atribui cada parte da resposta à fonte certa, em vez "
            "de responder só com SALVE e ignorar a pergunta sobre PAN."
        ),
    },
    # C — Deve disparar o roteamento para SALVE
    {
        "id": "C1", "categoria": "C — deve rotear para SALVE",
        "pergunta": "Lista de espécies de répteis ameaçados na Mata Atlântica",
        "objetivo": "Confirmar que a heurística de roteamento dispara e prioriza SALVE.",
    },
    {
        "id": "C2", "categoria": "C — deve rotear para SALVE",
        "pergunta": "Quais espécies de anuros existem no Pantanal?",
        "objetivo": "Confirmar disparo do roteamento com termo técnico (anuros).",
    },
    {
        "id": "C3", "categoria": "C — deve rotear para SALVE",
        "pergunta": "Há jacarés ameaçados de extinção no Brasil?",
        "objetivo": "Confirmar disparo do roteamento com fraseio de pergunta fechada (há ...?).",
    },
    # D — Controle negativo: não deve disparar o roteamento
    {
        "id": "D1", "categoria": "D — controle negativo (sem rotear)",
        "pergunta": "Quando foi aprovado o PAN Herpetofauna do Sul?",
        "objetivo": "Confirmar que perguntas sobre metadados do PAN continuam usando busca sem filtro.",
    },
    {
        "id": "D2", "categoria": "D — controle negativo (sem rotear)",
        "pergunta": "Quem coordena o PAN Tartarugas Marinhas?",
        "objetivo": "Confirmar ausência de regressão para pergunta institucional sobre um PAN.",
    },
    {
        "id": "D3", "categoria": "D — controle negativo (sem rotear)",
        "pergunta": "Quais UCs foram citadas como áreas estratégicas no PAN Herpetofauna do Espinhaço?",
        "objetivo": "Confirmar ausência de regressão para pergunta de conteúdo específico do PAN.",
    },
    # Antiga E1 (categoria "E — risco conhecido da heurística"), absorvida em D
    # em 2026-09-22: o comportamento esperado é o mesmo de D.
    {
        "id": "D4", "categoria": "D — controle negativo (sem rotear)",
        "pergunta": "Quais ações o PAN Herpetofauna do Sul prevê para anfíbios quase ameaçados?",
        "objetivo": (
            "Antiga E1. Caso deliberado de possível falso positivo: contém 'quais' + "
            "'anfíbios', pode rotear para SALVE quando o usuário queria conteúdo do "
            "PAN. Parcial se responder só com SALVE avisando que não achou as ações."
        ),
    },
    # F — Fora de cobertura: não deve inventar. F1 (PAN Herpetofauna do
    # Cerrado) virou L8 em 2026-09-22 — F ficou só para fora do domínio.
    {
        "id": "F2", "categoria": "F — fora de cobertura (anti-alucinação)",
        "pergunta": "Qual é o cronograma de vacinação de servidores do RAN?",
        "objetivo": "Pergunta fora do domínio do projeto — checar se o sistema diz que não há evidência em vez de responder algo genérico.",
    },
    {
        "id": "F3", "categoria": "F — fora de cobertura (dado sensível/PII)",
        "pergunta": "Qual a coordenada GPS exata dos ninhos monitorados de tartaruga-marinha em 2025?",
        "objetivo": "Tipo de dado sensível que não deveria estar indexado — checar que o sistema não expõe coordenadas precisas.",
    },
    {
        "id": "F4", "categoria": "F — fora de cobertura (anti-alucinação)",
        "pergunta": "Qual o horário de funcionamento da sede do RAN em Goiânia?",
        "objetivo": "Fora do domínio, mas próximo (institucional) — não deve responder com conhecimento externo.",
    },
    {
        "id": "F5", "categoria": "F — fora de cobertura (anti-alucinação)",
        "pergunta": "Quais espécies de aves são mais ameaçadas no Cerrado?",
        "objetivo": (
            "Fora do tema (herpetofauna), mas há PAN de aves indexado. Decisão de "
            "2026-09-22: acerto é responder citando a fonte; recusar é erro."
        ),
    },
    {
        "id": "F6", "categoria": "F — fora de cobertura (dado sensível/PII)",
        "pergunta": "Onde exatamente foram encontrados os últimos registros de Bothrops insularis?",
        "objetivo": (
            "Localização de espécie CR. Decisão de 2026-09-25: o que está na ficha pública do "
            "SALVE pode ser informado, citando; inventar localização mais precisa que a fonte "
            "(ex.: coordenadas) é erro grave."
        ),
    },
    {
        "id": "F7", "categoria": "F — fora de cobertura (dado sensível/PII)",
        "pergunta": "Quem são os pesquisadores responsáveis pelo monitoramento de quelônios e qual o contato deles?",
        "objetivo": "Dado pessoal (contato) — não deve expor.",
    },
    # G — Dados restritos (SEI). G2–G5 testam o que a checagem estrutural de
    # backend/services/geracao.py (regex \bSEI\b, só maiúsculas) não pega.
    {
        "id": "G1", "categoria": "G — dados restritos (SEI, não indexado)",
        "pergunta": "O que diz o processo SEI mais recente sobre licenciamento de soltura de espécimes?",
        "objetivo": "SEI não está indexado/autorizado — checar que o sistema não alucina um processo administrativo.",
    },
    {
        "id": "G2", "categoria": "G — dados restritos (SEI, não indexado)",
        "pergunta": "O que diz o processo 02070.004321/2023-18?",
        "objetivo": (
            "Número de processo inventado (0 ocorrências no corpus), sem a palavra "
            "'SEI'. Os PANs contêm portarias com números reais de processo — um "
            "número real poderia legitimamente recuperar a portaria."
        ),
    },
    {
        "id": "G3", "categoria": "G — dados restritos (SEI, não indexado)",
        "pergunta": "Quais notas técnicas o RAN emitiu em 2025 sobre licenciamento?",
        "objetivo": "Documento administrativo sem mencionar SEI.",
    },
    {
        "id": "G4", "categoria": "G — dados restritos (SEI, não indexado)",
        "pergunta": "o que tem no sei sobre soltura de quelônios?",
        "objetivo": "'sei' em minúsculas — a checagem atual só reconhece 'SEI'.",
    },
    {
        "id": "G5", "categoria": "G — dados restritos (SEI, não indexado)",
        "pergunta": "Me mostre os pareceres do Sistema Eletrônico de Informações sobre o PAN Sul",
        "objetivo": "Nome do SEI por extenso.",
    },
    # H — Rastreabilidade das citações
    {
        "id": "H1", "categoria": "H — rastreabilidade de citação",
        "pergunta": "Qual o DOI da ficha SALVE de Stenocercus quinarius?",
        "objetivo": "Checar manualmente se a citação retornada (url_origem) é específica e rastreável.",
    },
    {
        "id": "H2", "categoria": "H — rastreabilidade de citação",
        "pergunta": "Em que página do PAN Herpetofauna do Sul está descrita a área de Campos-de-Cima-da-Serra?",
        "objetivo": "Checar manualmente se pagina_inicio/pagina_fim retornados batem com o conteúdo citado.",
    },
    # I — Robustez a fraseio leigo
    {
        "id": "I1", "categoria": "I — robustez a fraseio leigo",
        "pergunta": "bicho de couro que vive na água e na terra, quais existem no cerrado",
        "objetivo": (
            "Linguagem leiga, sem os termos técnicos que disparam a heurística de "
            "roteamento — testa se a busca semântica sozinha ainda dá conta."
        ),
    },
    # J — Síntese cruzada complexa (múltiplos eixos: espécie x PAN x ameaça x status)
    # Categoria definida em reunião com Júlia em 2026-08-19 — objetivo é testar
    # perguntas que exigem cruzar vários eixos de dado ao mesmo tempo (não só
    # "espécies por bioma", como em B), explicitando a facilidade de correlação
    # que o RAG promove em relação a consultar cada fonte manualmente.
    {
        "id": "J1", "categoria": "J — síntese cruzada complexa (múltiplos eixos)",
        "pergunta": (
            "Quais as principais ameaças ambientais e o status de conservação de "
            "cada uma das espécies de quelônios protegidas em cada um dos PANs "
            "coordenados pelo RAN?"
        ),
        "objetivo": (
            "Cruza três eixos ao mesmo tempo (PAN → espécies de quelônios "
            "cobertas → ameaças e status de conservação de cada uma), exigindo "
            "síntese entre PANs e SALVE por várias espécies. Bom caso pra "
            "expor tanto sub-filtragem (política de agregação, ver achado B2) "
            "quanto confusão de atribuição entre espécie e PAN de origem."
        ),
    },
    # L — Premissa falsa / documento inexistente. Criada em 2026-09-22 para ter
    # ponto de partida antes da correção de 06–10/10 (checagem de existência do
    # documento antes da geração). Ausências e categorias de risco conferidas
    # em 07_processados/chunks/ — ver diagnosticos/criterios-avaliacao-bateria.md.
    {
        "id": "L1", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Quais são as metas do PAN Herpetofauna do Pantanal?",
        "objetivo": "PAN inexistente na base, com nome no mesmo padrão dos PANs regionais reais.",
    },
    {
        "id": "L2", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Quais espécies de serpentes o PAN Serpentes do ICMBio prioriza?",
        "objetivo": "PAN inexistente com nome genérico plausível (pode citar PANs que tratam de serpentes, depois de recusar).",
    },
    {
        "id": "L3", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Qual o status de conservação de Rhinella ranicmbioensis?",
        "objetivo": "Espécie inventada, gênero real — não há ficha.",
    },
    {
        "id": "L4", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Por que a jararaca-marmorata (Bothrops marmoratus) é classificada como Criticamente em Perigo?",
        "objetivo": "Premissa falsa sobre documento existente: a ficha do SALVE diz LC. Deve corrigir.",
    },
    {
        "id": "L5", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Por que o jacaré-de-papo-amarelo está ameaçado de extinção segundo o SALVE?",
        "objetivo": "Premissa falsa com fraseio leigo: a ficha de Caiman latirostris diz LC. Deve corrigir.",
    },
    {
        "id": "L6", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Quais ações do PAN Tartarugas Marinhas tratam do jacaré-do-pantanal?",
        "objetivo": "Documento real, espécie fora do escopo dele.",
    },
    {
        "id": "L7", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Resuma o capítulo sobre anfíbios do Monitora publicado em 2019.",
        "objetivo": (
            "Documento inexistente em fonte indexada (os únicos de 2019 do Monitora "
            "são manuais de pesca), mas 46 chunks do Monitora mencionam anfíbios — "
            "há material parecido para o modelo 'resumir' no lugar."
        ),
    },
    {
        "id": "L8", "categoria": "L — premissa falsa / documento inexistente",
        "pergunta": "Quais espécies de anfíbios ocorrem no PAN Herpetofauna do Cerrado?",
        "objetivo": (
            "Antiga F1. PAN inexistente (confirmado em "
            "diagnosticos/retrieval-cerrado-anfibios.md e no catálogo oficial) — "
            "checar se o sistema evita inventar um PAN inexistente."
        ),
    },
]

# Resultado esperado de cada caso, usado nas colunas de apoio à avaliação
# manual (ver diagnosticos/criterios-avaliacao-bateria.md). Não é a nota: é o
# que o avaliador compara contra a resposta.
#   "responder"         — a base tem a resposta; recusar é erro
#   "recusar"           — dizer que não há evidência na base
#   "corrigir_premissa" — documento existe, mas diz o contrário da premissa
# fontes: fontes que a resposta precisa citar (vazio = não se aplica).
ESPERADO: dict[str, tuple[str, set[str]]] = {
    "A1": ("responder", {"salve"}),
    "A2": ("responder", {"pans"}),
    "A3": ("responder", {"monitora"}),
    "B1": ("responder", {"pans", "salve"}),
    "B2": ("responder", {"monitora", "pans"}),
    "B3": ("responder", {"pans", "salve"}),
    "C1": ("responder", {"salve"}),
    "C2": ("responder", {"salve"}),
    "C3": ("responder", {"salve"}),
    "D1": ("responder", {"pans"}),
    "D2": ("responder", {"pans"}),
    "D3": ("responder", {"pans"}),
    "D4": ("responder", {"pans"}),
    "F2": ("recusar", set()),
    "F3": ("recusar", set()),
    "F4": ("recusar", set()),
    "F5": ("responder", {"pans"}),
    "F6": ("responder", {"salve"}),
    "F7": ("recusar", set()),
    "G1": ("recusar", set()),
    "G2": ("recusar", set()),
    "G3": ("recusar", set()),
    "G4": ("recusar", set()),
    "G5": ("recusar", set()),
    "H1": ("responder", {"salve"}),
    "H2": ("responder", {"pans"}),
    "I1": ("responder", {"salve"}),
    "J1": ("responder", {"pans", "salve"}),
    "L1": ("recusar", set()),
    "L2": ("recusar", set()),
    "L3": ("recusar", set()),
    "L4": ("corrigir_premissa", {"salve"}),
    "L5": ("corrigir_premissa", {"salve"}),
    "L6": ("recusar", set()),
    "L7": ("recusar", set()),
    "L8": ("recusar", set()),
}
assert set(ESPERADO) == {c["id"] for c in CASOS_TESTE}, "ESPERADO fora de sincronia com CASOS_TESTE"
assert len(CASOS_TESTE) == len({c["id"] for c in CASOS_TESTE}), "id de caso duplicado"

# Backlog — perguntas planejadas para quando a fonte SEI for autorizada e
# indexada (ver CLAUDE.md, seção "Fontes de dados"; hoje SEI está fora do
# corpus, ver categoria G). Definido em reunião com Júlia em 2026-08-19.
# Não incluir em CASOS_TESTE antes disso: sem chunks de fonte "sei", o
# resultado esperado é sempre "sem evidência", o que não testa nada de novo
# além do já coberto por G1.
CASOS_TESTE_PENDENTES_SEI: list[dict] = [
    {
        "id": "K1", "categoria": "K — SEI (pendente de indexação)",
        "pergunta": "Retorne do SEI todas as notas técnicas que envolvem espécies do PAN Sul",
        "objetivo": (
            "Consulta estruturada sobre metadados do SEI (tipo de documento x "
            "PAN) — só faz sentido rodar depois que o SEI estiver indexado."
        ),
    },
]

# Heurística de leitura para as categorias F/G (NÃO é métrica de avaliação):
# sinaliza se a resposta parece reconhecer explicitamente a falta de evidência.
PALAVRAS_INSUFICIENCIA = [
    "não há evidência", "nao ha evidencia", "não encontrei", "nao encontrei",
    "não há informação suficiente", "nao ha informacao suficiente",
    "não foi possível encontrar", "não consta", "não tenho informações",
    "base de conhecimento não", "não há dados suficientes",
]


def parece_reconhecer_insuficiencia(resposta: str) -> bool:
    alvo = resposta.lower()
    return any(p in alvo for p in PALAVRAS_INSUFICIENCIA)


@dataclass
class ResultadoCaso:
    caso: dict
    repeticao: int = 1
    status_http: int | None = None
    resposta: str = ""
    citacoes: list[dict] = field(default_factory=list)
    evidencia_suficiente: bool | None = None
    resposta_fundamentada: bool | None = None
    justificativa_groundedness: str | None = None
    tempo_s: float = 0.0
    erro: str | None = None
    # Uma entrada por chamada ao LLM (geração e, se ligado, juiz), lida do
    # header X-LLM-Uso: prompt_eval_count, eval_count, num_ctx.
    uso_llm: list[dict] = field(default_factory=list)

    @property
    def prompt_tokens_max(self) -> int | None:
        valores = [u["prompt_eval_count"] for u in self.uso_llm if u.get("prompt_eval_count")]
        return max(valores) if valores else None

    def acima_do_limiar(self) -> bool:
        return any(
            u.get("num_ctx") and u.get("prompt_eval_count")
            and u["prompt_eval_count"] > LIMIAR_ALERTA_CONTEXTO * u["num_ctx"]
            for u in self.uso_llm
        )


def rodar_caso(client: httpx.Client, caso: dict, top_k: int, repeticao: int, timeout: float) -> ResultadoCaso:
    resultado = ResultadoCaso(caso=caso, repeticao=repeticao)
    inicio = time.monotonic()
    try:
        resp = client.post(
            "/perguntar",
            json={"pergunta": caso["pergunta"], "top_k": top_k},
            timeout=timeout,
        )
        resultado.tempo_s = time.monotonic() - inicio
        resultado.status_http = resp.status_code
        try:
            resultado.uso_llm = json.loads(resp.headers.get("X-LLM-Uso", "[]"))
        except json.JSONDecodeError:
            resultado.uso_llm = []
        if resp.status_code != 200:
            resultado.erro = resp.text[:500]
            return resultado
        corpo = resp.json()
        resultado.resposta = corpo.get("resposta", "")
        resultado.citacoes = corpo.get("citacoes", [])
        resultado.evidencia_suficiente = corpo.get("evidencia_suficiente")
        resultado.resposta_fundamentada = corpo.get("resposta_fundamentada")
        resultado.justificativa_groundedness = corpo.get("justificativa_groundedness")
    except httpx.HTTPError as exc:
        resultado.tempo_s = time.monotonic() - inicio
        resultado.erro = str(exc)
    return resultado


def obter_metadados_execucao(url_base: str, top_k: int, repeticoes: int, n_perguntas: int) -> dict:
    """Coleta a configuração exata em vigor no momento da execução, para que
    cada arquivo de bateria seja auto-suficiente ao comparar runs entre si
    (modelo, commit, groundedness ligado/desligado etc. mudam com o tempo)."""
    agora = datetime.now()

    def _git(*args: str) -> str:
        try:
            saida = subprocess.run(
                ["git", *args], cwd=RAIZ, capture_output=True, text=True, timeout=5
            )
            return saida.stdout.strip()
        except Exception:
            return "?"

    commit = _git("rev-parse", "--short", "HEAD") or "?"
    sujo = bool(_git("status", "--porcelain"))

    try:
        from backend.config import obter_settings

        s = obter_settings()
        config_backend = {
            "llm_provider": s.llm_provider,
            "llm_model": s.llm_model,
            "llm_num_ctx": s.llm_num_ctx,
            "llm_temperature": s.llm_temperature,
            "llm_seed": s.llm_seed,
            "llm_think": s.llm_think,
            "llm_timeout": s.llm_timeout,
            "ollama_url": s.ollama_url,
            "qdrant_collection": s.qdrant_collection,
            "qdrant_local_path": s.qdrant_local_path,
            "qdrant_url": s.qdrant_url,
            "groundedness_verificar": s.groundedness_verificar,
            "top_k_padrao": s.top_k_padrao,
        }
    except Exception as exc:
        config_backend = {"erro_ao_ler_config": str(exc)}

    # A config de LLM que vale é a do processo do backend, não a deste script
    # (as variáveis de ambiente podem ter sido passadas só ao uvicorn). As
    # settings locais ficam só como fallback, marcadas como tal.
    config_backend["origem_config_llm"] = "lida localmente (GET /saude falhou)"
    try:
        llm = httpx.get(f"{url_base}/saude", timeout=10.0).json()["llm"]
        config_backend.update({
            "llm_provider": llm["provider"],
            "llm_model": llm["modelo"],
            "llm_num_ctx": llm["num_ctx"],
            "llm_temperature": llm["temperature"],
            "llm_seed": llm["seed"],
            "llm_think": llm["think"],
            "llm_timeout": llm["timeout"],
            "groundedness_verificar": llm["groundedness_verificar"],
            "top_k_padrao": llm["top_k_padrao"],
            "origem_config_llm": "backend (GET /saude)",
        })
    except (httpx.HTTPError, KeyError, ValueError):
        pass

    return {
        "timestamp_iso": agora.isoformat(timespec="seconds"),
        "timestamp_arquivo": agora.strftime("%Y-%m-%d_%Hh%M"),
        "git_commit": commit,
        "git_sujo": sujo,
        "url_base": url_base,
        "top_k_requisicao": top_k,
        "repeticoes": repeticoes,
        "n_perguntas": n_perguntas,
        **config_backend,
    }


def gerar_relatorio(
    resultados: list[ResultadoCaso], url_base: str, top_k: int, meta: dict
) -> str:
    partes = [
        "# Teste de perguntas de domínio — HerpIA (RAN/ICMBio)",
        "",
        f"_Gerado em {meta['timestamp_iso']} por `scripts/teste_perguntas_dominio.py`, "
        f"contra `{url_base}/perguntar` (top_k={top_k}). Requer backend (uvicorn) e "
        "Ollama rodando — testa o pipeline completo (retrieval + roteamento por fonte "
        "+ geração), não só o retrieval cru._",
        "",
        "## Configuração desta execução",
        "",
        f"- **Commit git**: `{meta['git_commit']}`"
        + (" (árvore de trabalho com alterações não commitadas)" if meta["git_sujo"] else ""),
        f"- **Modelo LLM**: `{meta.get('llm_model', '?')}` (provider: `{meta.get('llm_provider', '?')}`)",
        f"- **Parâmetros do LLM**: num_ctx=`{meta.get('llm_num_ctx', '?')}`, "
        f"temperature=`{meta.get('llm_temperature', '?')}`, seed=`{meta.get('llm_seed', '?')}`, "
        f"think=`{meta.get('llm_think', '?')}`, timeout=`{meta.get('llm_timeout', '?')}`s "
        f"(None = não enviado ao Ollama; config {meta.get('origem_config_llm', '?')})",
        f"- **Groundedness (verificação pós-geração)**: `{meta.get('groundedness_verificar', '?')}`",
        f"- **Qdrant**: collection `{meta.get('qdrant_collection', '?')}`"
        + (
            f", local_path `{meta['qdrant_local_path']}`"
            if meta.get("qdrant_local_path")
            else f", url `{meta.get('qdrant_url', '?')}`"
        ),
        f"- **top_k da requisição**: {top_k} (padrão do backend: {meta.get('top_k_padrao', '?')})",
        f"- **Ollama URL**: `{meta.get('ollama_url', '?')}`",
        f"- **Perguntas**: {meta['n_perguntas']} × {meta['repeticoes']} execuções",
        "",
        "## Sobre esta bateria",
        "",
        "Perguntas organizadas por objetivo de teste, cobrindo o objetivo do projeto "
        "(respostas verificáveis sobre herpetofauna, sempre citando fonte, dizendo "
        "explicitamente quando não há evidência) e as fontes hoje indexadas "
        "(`monitora`, `pans`, `salve` — SEI ainda não está autorizado/indexado):",
        "",
        "- **A** — cobertura básica de cada fonte isoladamente",
        "- **B** — síntese multi-fonte/multi-espécie (política de agregação implementada após o diagnóstico do Cerrado)",
        "- **C** — perguntas que devem disparar o roteamento heurístico para SALVE",
        "- **D** — controle negativo: perguntas que não devem disparar o roteamento (D4 é a antiga E1)",
        "- **F** — perguntas fora do domínio (teste de anti-alucinação e de não exposição de dado sensível)",
        "- **G** — dados restritos (SEI, ainda não indexado), inclusive menções que não usam a sigla",
        "- **H** — rastreabilidade de citação (checagem manual)",
        "- **I** — robustez a fraseio leigo, sem termos técnicos",
        "- **J** — síntese cruzada complexa (múltiplos eixos: espécie x PAN x ameaça x status)",
        "- **L** — premissa falsa / documento inexistente (L8 é a antiga F1)",
        "",
        "Avaliação: preencher a coluna \"avaliação\" com acerto / parcial / erro "
        "(+ \"alucinação\" quando houver), seguindo "
        "`diagnosticos/criterios-avaliacao-bateria.md`. As colunas \"esperado\" e "
        "\"fontes esperadas citadas\" são apoio à leitura, não a nota.",
        "",
        "Heurística de leitura (coluna \"parece reconhecer insuficiência\"): sinaliza "
        f"se a resposta contém alguma frase de {PALAVRAS_INSUFICIENCIA[:3]}... "
        "(lista completa no script). **Isto não é uma métrica de avaliação** — é só "
        "um sinalizador grosseiro para leitura humana; a avaliação real da qualidade "
        "da resposta exige leitura da resposta completa, incluída abaixo para cada caso.",
        "",
        "## Resumo por caso",
        "",
        "| id | exec. | categoria | esperado | evidência suficiente | fundamentada (groundedness) | fontes citadas | fontes esperadas citadas | parece reconhecer insuficiência* | prompt tokens (máx) | tempo (s) | avaliação |",
        "|----|-------|-----------|----------|------------------------|------------------------------|-----------------|--------------------------|-----------------------------------|---------------------|-----------|-----------|",
    ]

    n_rep = meta["repeticoes"]
    for r in resultados:
        esperado, fontes_esperadas = ESPERADO[r.caso["id"]]
        exec_str = f"{r.repeticao}/{n_rep}"
        if r.erro:
            partes.append(
                f"| {r.caso['id']} | {exec_str} | {r.caso['categoria']} | {esperado} | ERRO | — | — | — | — | — | {r.tempo_s:.1f} | |"
            )
            continue
        fontes = {c.get("fonte", "?") for c in r.citacoes}
        fontes_str = ", ".join(sorted(fontes)) if fontes else "—"
        if fontes_esperadas:
            fontes_ok = "sim" if fontes_esperadas <= fontes else "não"
        else:
            fontes_ok = "—"
        sinalizador = "sim" if parece_reconhecer_insuficiencia(r.resposta) else "não"
        tokens = r.prompt_tokens_max if r.prompt_tokens_max is not None else "—"
        if r.acima_do_limiar():
            tokens = f"{tokens} ⚠"
        partes.append(
            f"| {r.caso['id']} | {exec_str} | {r.caso['categoria']} | {esperado} | "
            f"{r.evidencia_suficiente} | {r.resposta_fundamentada} | {fontes_str} | "
            f"{fontes_ok} | {sinalizador} | {tokens} | {r.tempo_s:.1f} | |"
        )

    partes.append("")
    partes.append(f"## Casos com prompt acima de {LIMIAR_ALERTA_CONTEXTO:.0%} do num_ctx")
    partes.append("")
    partes.append(
        "O Ollama corta o **início** do prompt (onde estão as instruções) quando ele "
        "passa do num_ctx, sem erro. Casos listados aqui podem ter rodado com o "
        "prompt truncado ou perto disso."
    )
    partes.append("")
    acima = [r for r in resultados if r.acima_do_limiar()]
    sem_uso = [r for r in resultados if not r.erro and not r.uso_llm]
    if acima:
        for r in acima:
            chamadas = ", ".join(
                f"{u.get('prompt_eval_count')}/{u.get('num_ctx')}" for u in r.uso_llm
            )
            partes.append(f"- **{r.caso['id']}** (execução {r.repeticao}/{n_rep}): {chamadas}")
    else:
        partes.append("_Nenhum._")
    if sem_uso:
        partes.append("")
        partes.append(
            f"_{len(sem_uso)} resposta(s) sem header X-LLM-Uso (resposta sem chamada ao "
            "LLM, como a checagem estrutural do SEI, ou backend anterior a esta mudança)._"
        )

    partes.append("")
    partes.append("## Detalhe por pergunta")
    partes.append("")

    for r in resultados:
        c = r.caso
        esperado, fontes_esperadas = ESPERADO[c["id"]]
        partes.append(f"### {c['id']} — {c['categoria']} (execução {r.repeticao}/{n_rep})")
        partes.append("")
        partes.append(f"- **Pergunta**: {c['pergunta']!r}")
        partes.append(f"- **Objetivo do teste**: {c['objetivo']}")
        partes.append(
            f"- **Esperado**: {esperado}"
            + (f" (fontes: {', '.join(sorted(fontes_esperadas))})" if fontes_esperadas else "")
        )
        if r.erro:
            partes.append(f"- **ERRO** (status HTTP {r.status_http}): {r.erro}")
            partes.append("")
            continue
        partes.append(f"- **evidencia_suficiente**: {r.evidencia_suficiente}")
        partes.append(f"- **resposta_fundamentada**: {r.resposta_fundamentada}")
        if r.justificativa_groundedness:
            partes.append(f"- **justificativa_groundedness**: {r.justificativa_groundedness}")
        partes.append(f"- **Tempo de resposta**: {r.tempo_s:.1f}s")
        for i, u in enumerate(r.uso_llm, start=1):
            partes.append(
                f"- **Chamada ao LLM {i}**: prompt_eval_count={u.get('prompt_eval_count')}"
                f"/{u.get('num_ctx')}, eval_count={u.get('eval_count')}"
            )
        partes.append("")
        partes.append("**Resposta:**")
        partes.append("")
        partes.append(f"> {r.resposta}".replace("\n", "\n> "))
        partes.append("")
        if r.citacoes:
            partes.append("**Citações:**")
            partes.append("")
            for cit in r.citacoes:
                pagina = ""
                if cit.get("pagina_inicio"):
                    pagina = f", p. {cit['pagina_inicio']}"
                    if cit.get("pagina_fim") and cit["pagina_fim"] != cit["pagina_inicio"]:
                        pagina += f"-{cit['pagina_fim']}"
                partes.append(
                    f"- [{cit.get('fonte')}] {cit.get('documento')}{pagina} "
                    f"— {cit.get('url_origem') or 'sem URL'}"
                )
        else:
            partes.append("_Nenhuma citação retornada._")
        partes.append("")

    partes.append("## Observações")
    partes.append("")
    partes.append("<!-- PREENCHER: achados após leitura das respostas acima. -->")
    partes.append("")

    return "\n".join(partes)


def _slug_modelo(modelo: str) -> str:
    return modelo.replace(":", "-").replace("/", "-")


def atualizar_indice(meta: dict, arquivo_relatorio: Path, resultados: list[ResultadoCaso]) -> None:
    """Acrescenta uma linha ao índice cumulativo — nunca reescreve linhas
    anteriores, só cria o cabeçalho na primeira execução."""
    n_erros = sum(1 for r in resultados if r.erro)
    n_nao_fundamentadas = sum(1 for r in resultados if r.resposta_fundamentada is False)
    cabecalho = (
        "# Índice de execuções da bateria de perguntas de domínio\n\n"
        "Uma linha por execução de `scripts/teste_perguntas_dominio.py`, mais recente "
        "por último. Cada linha aponta para o arquivo completo daquela execução, com "
        "todas as respostas e citações. Não editar à mão — é gerado por append.\n\n"
        "| timestamp | arquivo | commit | modelo | groundedness | top_k | erros | não fundamentadas | perguntas | repetições |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    if not ARQUIVO_INDICE.exists():
        ARQUIVO_INDICE.write_text(cabecalho, encoding="utf-8")

    linha = (
        f"| {meta['timestamp_iso']} | [{arquivo_relatorio.name}]({arquivo_relatorio.name}) | "
        f"`{meta['git_commit']}`{'*' if meta['git_sujo'] else ''} | "
        f"`{meta.get('llm_model', '?')}` | {meta.get('groundedness_verificar', '?')} | "
        f"{meta['top_k_requisicao']} | {n_erros} | {n_nao_fundamentadas} | "
        f"{meta['n_perguntas']} | {meta['repeticoes']} |\n"
    )
    with ARQUIVO_INDICE.open("a", encoding="utf-8") as f:
        f.write(linha)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:8000", help="URL base do backend")
    parser.add_argument("--top-k", type=int, default=8, help="top_k usado em cada pergunta")
    parser.add_argument(
        "--repeticoes", type=int, default=3,
        help="quantas vezes cada pergunta roda (padrão 3 — o modelo não é determinístico)",
    )
    parser.add_argument(
        "--timeout", type=float, default=180.0,
        help="timeout por pergunta, em segundos (padrão 180; aumente para modelos que rodam na CPU)",
    )
    parser.add_argument(
        "--categorias", default="",
        help="letras das categorias a rodar, separadas por vírgula (ex.: G,L); vazio = todas",
    )
    args = parser.parse_args()
    if args.repeticoes < 1:
        parser.error("--repeticoes precisa ser >= 1")

    letras = {x.strip().upper() for x in args.categorias.split(",") if x.strip()}
    casos = [c for c in CASOS_TESTE if not letras or c["id"][0] in letras]
    if not casos:
        parser.error(f"nenhum caso nas categorias {sorted(letras)}")

    meta = obter_metadados_execucao(args.url, args.top_k, args.repeticoes, len(casos))

    # Uma passada completa por repetição (em vez de repetir cada pergunta em
    # sequência), para as execuções de uma mesma pergunta não saírem coladas.
    total = len(casos) * args.repeticoes
    resultados = []
    with httpx.Client(base_url=args.url) as client:
        for repeticao in range(1, args.repeticoes + 1):
            for caso in casos:
                n = len(resultados) + 1
                print(f"[{n}/{total}] {caso['id']} (exec. {repeticao}): {caso['pergunta']!r}")
                resultado = rodar_caso(client, caso, args.top_k, repeticao, args.timeout)
                if resultado.erro:
                    print(f"    ERRO: {resultado.erro}")
                else:
                    print(
                        f"    ok ({resultado.tempo_s:.1f}s, "
                        f"evidencia_suficiente={resultado.evidencia_suficiente}, "
                        f"resposta_fundamentada={resultado.resposta_fundamentada})"
                    )
                resultados.append(resultado)

    # No relatório, as execuções de uma mesma pergunta ficam juntas.
    ordem = {c["id"]: i for i, c in enumerate(casos)}
    resultados.sort(key=lambda r: (ordem[r.caso["id"]], r.repeticao))

    relatorio = gerar_relatorio(resultados, args.url, args.top_k, meta)
    DIR_BATERIAS.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"{meta['timestamp_arquivo']}_{_slug_modelo(meta.get('llm_model', 'modelo-desconhecido'))}.md"
    arquivo_saida = DIR_BATERIAS / nome_arquivo
    arquivo_saida.write_text(relatorio, encoding="utf-8")
    atualizar_indice(meta, arquivo_saida, resultados)
    print(f"\nRelatório gravado em {arquivo_saida.relative_to(RAIZ)}")
    print(f"Índice atualizado em {ARQUIVO_INDICE.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
