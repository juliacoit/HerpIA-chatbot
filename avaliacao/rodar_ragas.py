"""Avaliação offline do HerpIA com RAGAS e juiz Claude (ADR 0007).

Para cada caso de avaliacao/casos.jsonl:

1. chama POST /perguntar com `incluir_contextos=true` (o backend precisa estar
   rodando com PERMITIR_MODO_AVALIACAO=true; sem isso a resposta é 403 e a
   execução para);
2. roda as checagens de rota (avaliacao/rota.py, sem custo);
3. **bloqueio por sensibilidade, falhando fechado:** se qualquer contexto
   tiver `nivel_sensibilidade` diferente de "autorizado" (inclusive None ou
   campo ausente), o caso inteiro fica `bloqueado_sensibilidade` e nada dele
   é enviado à API;
4. avalia com RAGAS: Faithfulness e AnswerRelevancy sempre;
   ContextPrecisionWithReference e ContextRecall só com gabarito do RAN
   (`tem_referencia`).

O texto avaliado é o que o LLM local gerou: `resposta` nas saídas `gerada` e
`abstencao`, e `resposta_original` na `retida_groundedness`, para permitir
comparar o juiz interno com o RAGAS. As saídas sem texto do LLM (`sem_chunks`,
`sei_nao_indexado`, `contexto_excedido`) não são avaliadas.

Só vão à API a pergunta, o texto gerado, os trechos recuperados (nunca
documentos inteiros) e, quando houver, o gabarito. As métricas multimodais
do ragas não são usadas em hipótese alguma (CVE-2026-6587, ver ADR 0007).

Uso:
    python avaliacao/rodar_ragas.py --dry-run
    python avaliacao/rodar_ragas.py --casos A1 --metricas faithfulness   # smoke test
    python avaliacao/rodar_ragas.py --juiz claude-haiku-5-5 --max-casos 5

    Sem --dry-run há custo: o script mostra o plano (casos e chamadas
    estimadas ao juiz) e pede confirmação, a menos que receba --sim. A
    credencial vem de ANTHROPIC_API_KEY no ambiente ou, se ausente, só dessa
    variável no .env local (fora do versionamento); nunca do repositório.

Saída: um .md e um .json em diagnosticos/ragas/, nomeados com data/hora e
juiz, com metadados (juiz, versões, top_k, commit), notas por caso e por
categoria e os tokens gastos pelo juiz (lidos do `usage` de cada resposta da
API, por caso e no total, com o custo estimado).
"""

import os

# Antes de qualquer import do ragas: a telemetria é lida uma vez e fica em cache.
os.environ["RAGAS_DO_NOT_TRACK"] = "true"

import argparse  # noqa: E402
import asyncio  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from dataclasses import asdict, dataclass, field  # noqa: E402
from datetime import datetime  # noqa: E402
from importlib import metadata  # noqa: E402
from pathlib import Path  # noqa: E402

import httpx  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from avaliacao.casos import carregar_casos  # noqa: E402
from avaliacao.rota import checar_rota  # noqa: E402

DIR_RESULTADOS = RAIZ / "diagnosticos" / "ragas"
URL_PADRAO = "http://localhost:8000"
JUIZ_PADRAO = "claude-sonnet-5-5"
TOP_K_PADRAO = 5          # o mesmo do frontend (diagnosticos/ragas_fase0.md, "Decisões", item 2)
ESFORCO_PADRAO = "low"    # proposta da seção 8.2, a validar no smoke test
MAX_TOKENS_JUIZ = 8192    # o pensamento adaptativo consome max_tokens; o padrão do ragas (1024) é baixo
STRICTNESS_RELEVANCIA = 3  # padrão do AnswerRelevancy: perguntas geradas por chamada
MODELO_EMBEDDING = "BAAI/bge-m3"  # o mesmo do backend (backend/services/retrieval.py), local
NIVEL_PERMITIDO = "autorizado"
ARQUIVO_ENV = RAIZ / ".env"
# US$ por milhão de tokens (entrada, saída), referência da Claude API de
# 2026-10-06; o Haiku vale para prompts de até 100k tokens. Só estimativa:
# a fatura do Console é a fonte oficial. A saída inclui o pensamento.
PRECOS_POR_MTOK = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}

# Só estas quatro. Nunca acrescentar MultiModalFaithfulness/MultiModalRelevance.
METRICAS_SEM_REFERENCIA = ("faithfulness", "answer_relevancy")
METRICAS_COM_REFERENCIA = ("context_precision_with_reference", "context_recall")
METRICAS = METRICAS_SEM_REFERENCIA + METRICAS_COM_REFERENCIA

TIPOS_SEM_TEXTO_DO_LLM = {"sem_chunks", "sei_nao_indexado", "contexto_excedido"}


class ModoAvaliacaoDesabilitado(RuntimeError):
    """O backend respondeu 403: PERMITIR_MODO_AVALIACAO não está ligado."""


@dataclass
class UsoJuiz:
    """Tokens gastos pelo juiz, somados do `usage` de cada resposta da API."""

    requisicoes: int = 0       # respostas 200 de /v1/messages (inclui retries do instructor)
    respostas_erro: int = 0    # respostas não 200 (não cobradas, mas indicam problema)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def somar(self, usage: dict) -> None:
        self.requisicoes += 1
        for campo in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            setattr(self, campo, getattr(self, campo) + (usage.get(campo) or 0))

    def desde(self, antes: "UsoJuiz") -> "UsoJuiz":
        return UsoJuiz(**{k: v - getattr(antes, k) for k, v in asdict(self).items()})


def custo_estimado(uso: UsoJuiz, modelo: str) -> float | None:
    """Em US$, só entrada e saída (o juiz não usa cache). None se o modelo
    não estiver em PRECOS_POR_MTOK."""
    if modelo not in PRECOS_POR_MTOK:
        return None
    entrada, saida = PRECOS_POR_MTOK[modelo]
    return (uso.input_tokens * entrada + uso.output_tokens * saida) / 1_000_000


@dataclass
class ResultadoCaso:
    id: str
    categoria: str
    user_input: str
    tem_referencia: bool
    # Status da avaliação: "avaliado", "planejado" (dry-run),
    # "bloqueado_sensibilidade", "sem_texto_llm" ou "erro_coleta".
    status: str = "erro_coleta"
    erro_coleta: str | None = None
    tipo_saida: str | None = None
    origem_retencao: str | None = None
    resposta_fundamentada: bool | None = None
    texto_avaliado: str | None = None
    origem_texto: str | None = None   # "resposta" ou "resposta_original"
    contextos: list[dict] = field(default_factory=list)  # metadados, sem o texto
    niveis_bloqueados: list[str | None] = field(default_factory=list)
    rota: dict | None = None
    metricas_planejadas: list[str] = field(default_factory=list)
    chamadas_estimadas: int = 0
    caracteres_enviados: int = 0
    notas: dict[str, float | None] = field(default_factory=dict)
    erros_metricas: dict[str, str] = field(default_factory=dict)
    uso_juiz: dict | None = None   # UsoJuiz do caso; None no dry-run


# ---------------------------------------------------------------------------
# Coleta (backend local, sem custo)
# ---------------------------------------------------------------------------

async def coletar(client: httpx.AsyncClient, caso: dict, top_k: int, timeout: float) -> dict:
    """Chama /perguntar em modo de avaliação e devolve o corpo da resposta."""
    corpo = {
        "pergunta": caso["user_input"],
        "top_k": caso["top_k"] or top_k,
        "incluir_contextos": True,
    }
    if caso["fontes"]:
        corpo["fontes"] = caso["fontes"]
    resp = await client.post("/perguntar", json=corpo, timeout=timeout)
    if resp.status_code == 403:
        raise ModoAvaliacaoDesabilitado(resp.text[:300])
    resp.raise_for_status()
    return resp.json()


def niveis_nao_autorizados(contextos: list[dict]) -> list[str | None]:
    """Níveis de sensibilidade que bloqueiam o caso. Falha fechado: campo
    ausente ou None também bloqueia."""
    return [c.get("nivel_sensibilidade") for c in contextos if c.get("nivel_sensibilidade") != NIVEL_PERMITIDO]


def escolher_texto(corpo: dict) -> tuple[str | None, str | None]:
    """Texto gerado pelo LLM local e de qual campo ele veio."""
    avaliacao = corpo["avaliacao"]
    tipo = avaliacao["tipo_saida"]
    if tipo in TIPOS_SEM_TEXTO_DO_LLM:
        return None, None
    if tipo == "retida_groundedness":
        original = avaliacao.get("resposta_original")
        return (original, "resposta_original") if original else (None, None)
    return corpo["resposta"], "resposta"


def metricas_do_caso(caso: dict, selecionadas: tuple[str, ...]) -> list[str]:
    nomes = [m for m in METRICAS_SEM_REFERENCIA if m in selecionadas]
    if caso["tem_referencia"]:
        nomes += [m for m in METRICAS_COM_REFERENCIA if m in selecionadas]
    return nomes


def argumentos_metrica(nome: str, caso: dict, texto: str, contextos: list[str]) -> dict:
    """Argumentos de `ascore` de cada métrica (ragas.metrics.collections 0.4.3)."""
    if nome == "faithfulness":
        return {"user_input": caso["user_input"], "response": texto, "retrieved_contexts": contextos}
    if nome == "answer_relevancy":
        return {"user_input": caso["user_input"], "response": texto}
    if nome in METRICAS_COM_REFERENCIA:
        return {"user_input": caso["user_input"], "reference": caso["reference"], "retrieved_contexts": contextos}
    raise ValueError(f"métrica desconhecida: {nome}")


def estimar_chamadas(nome: str, n_contextos: int) -> int:
    """Chamadas ao juiz por métrica, sem contar retries do instructor."""
    return {
        "faithfulness": 2,                       # afirmações + vereditos
        "answer_relevancy": STRICTNESS_RELEVANCIA,
        "context_precision_with_reference": n_contextos,  # uma por contexto
        "context_recall": 1,
    }[nome]


# ---------------------------------------------------------------------------
# Avaliação de um caso
# ---------------------------------------------------------------------------

async def avaliar_caso(
    caso: dict,
    corpo: dict,
    metricas: dict | None,
    selecionadas: tuple[str, ...] = METRICAS,
) -> ResultadoCaso:
    """`corpo` é a resposta de /perguntar. `metricas` mapeia nome -> objeto
    com `ascore(**kwargs)`; None = dry-run (planeja, mas não chama)."""
    r = ResultadoCaso(
        id=caso["id"], categoria=caso["categoria"], user_input=caso["user_input"],
        tem_referencia=caso["tem_referencia"],
    )
    avaliacao = corpo.get("avaliacao")
    if not avaliacao:
        r.erro_coleta = "resposta sem o campo `avaliacao` (modo de avaliação não aplicado?)"
        return r

    contextos = avaliacao.get("contextos") or []
    r.tipo_saida = avaliacao.get("tipo_saida")
    r.origem_retencao = avaliacao.get("origem_retencao")
    r.resposta_fundamentada = corpo.get("resposta_fundamentada")
    r.contextos = [
        {k: c.get(k) for k in ("fonte", "documento", "secao", "pagina_inicio", "score", "nivel_sensibilidade")}
        for c in contextos
    ]
    rota = checar_rota(caso, [c.get("fonte") for c in contextos])
    r.rota = {**asdict(rota), "status": rota.status}

    # O bloqueio vem antes de tudo o que depende do texto: nem a pergunta nem
    # a resposta de um caso bloqueado vão à API.
    r.niveis_bloqueados = niveis_nao_autorizados(contextos)
    if r.niveis_bloqueados:
        r.status = "bloqueado_sensibilidade"
        return r

    texto, origem = escolher_texto(corpo)
    if not texto or not contextos:
        r.status = "sem_texto_llm"
        return r
    r.texto_avaliado, r.origem_texto = texto, origem

    textos_contextos = [c["texto"] for c in contextos]
    r.metricas_planejadas = metricas_do_caso(caso, selecionadas)
    for nome in r.metricas_planejadas:
        args = argumentos_metrica(nome, caso, texto, textos_contextos)
        r.chamadas_estimadas += estimar_chamadas(nome, len(contextos))
        r.caracteres_enviados += sum(len(v) if isinstance(v, str) else sum(map(len, v)) for v in args.values())

    if metricas is None:
        r.status = "planejado"
        return r

    for nome in r.metricas_planejadas:
        args = argumentos_metrica(nome, caso, texto, textos_contextos)
        try:
            resultado = await metricas[nome].ascore(**args)
            valor = float(resultado.value)
            r.notas[nome] = None if math.isnan(valor) else valor
        except Exception as exc:  # um erro numa métrica não derruba as outras
            r.erros_metricas[nome] = f"{type(exc).__name__}: {exc}"[:500]
    r.status = "avaliado"
    return r


# ---------------------------------------------------------------------------
# Juiz (única parte com custo)
# ---------------------------------------------------------------------------

def ajustar_args_juiz(model_args: dict) -> dict:
    """Contornos da seção 8.2 do diagnóstico para o claude-*-5-5: sem
    temperature/top_p (valores fora do padrão dão 400). O tool_choice auto
    vem do llm_factory."""
    return {k: v for k, v in model_args.items() if k not in ("temperature", "top_p")}


def obter_chave_anthropic(arquivo_env: Path = ARQUIVO_ENV) -> str | None:
    """ANTHROPIC_API_KEY do ambiente ou, se ausente, só essa variável do
    .env local. Nenhuma outra variável do .env é carregada. None deixa o SDK
    resolver a credencial por conta própria (ex.: perfil do `ant auth login`)."""
    chave = os.environ.get("ANTHROPIC_API_KEY")
    if chave:
        return chave
    if not arquivo_env.is_file():
        return None
    from dotenv import dotenv_values

    return dotenv_values(arquivo_env).get("ANTHROPIC_API_KEY") or None


def criar_metricas(
    modelo: str,
    esforco: str,
    selecionadas: tuple[str, ...],
    uso: UsoJuiz | None = None,
    api_key: str | None = None,
) -> dict:
    """Monta as métricas do ragas com o juiz Claude. Imports locais: o
    dry-run e os testes não dependem de ragas/anthropic instalados. Com
    `uso`, soma os tokens de cada resposta da API, sem chamada extra."""
    from anthropic import AsyncAnthropic, DefaultAsyncHttpxClient
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecisionWithReference,
        ContextRecall,
        Faithfulness,
    )

    async def registrar_uso(response) -> None:
        if uso is None or not response.request.url.path.endswith("/messages"):
            return
        if response.status_code != 200:
            uso.respostas_erro += 1
            return
        await response.aread()  # o corpo fica em cache; o SDK o lê depois normalmente
        uso.somar(response.json().get("usage") or {})

    cliente = AsyncAnthropic(
        api_key=api_key,
        http_client=DefaultAsyncHttpxClient(event_hooks={"response": [registrar_uso]}),
    )
    llm = llm_factory(
        modelo,
        provider="anthropic",  # o padrão "openai" trataria o cliente como OpenAI
        client=cliente,
        # Forçar a ferramenta (o padrão do instructor) dá 400 nesses modelos.
        # Sem disable_parallel_tool_use, duas chamadas da ferramenta fariam o
        # parser do instructor rejeitar a resposta (exige exatamente uma).
        tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        max_tokens=MAX_TOKENS_JUIZ,
        output_config={"effort": esforco},
    )
    llm.model_args = ajustar_args_juiz(llm.model_args)

    construtores = {
        "faithfulness": lambda: Faithfulness(llm=llm),
        "answer_relevancy": lambda: AnswerRelevancy(llm=llm, embeddings=_embeddings_locais()),
        "context_precision_with_reference": lambda: ContextPrecisionWithReference(llm=llm),
        "context_recall": lambda: ContextRecall(llm=llm),
    }
    return {nome: construtores[nome]() for nome in selecionadas}


def _embeddings_locais():
    # AnswerRelevancy compara perguntas por embedding; usa o BGE-M3 local, não API.
    from ragas.embeddings.huggingface_provider import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model=MODELO_EMBEDDING)


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

def _versao(pacote: str) -> str:
    try:
        return metadata.version(pacote)
    except metadata.PackageNotFoundError:
        return "não instalado"


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return "?"


def obter_metadados(args: argparse.Namespace, n_casos: int) -> dict:
    meta = {
        "timestamp_iso": datetime.now().isoformat(timespec="seconds"),
        "dry_run": args.dry_run,
        "juiz": args.juiz,
        "esforco_juiz": args.esforco,
        "max_tokens_juiz": MAX_TOKENS_JUIZ,
        "embeddings_answer_relevancy": MODELO_EMBEDDING,
        "metricas": list(args.metricas),
        "top_k": args.top_k,
        "n_casos": n_casos,
        "versao_ragas": _versao("ragas"),
        "versao_instructor": _versao("instructor"),
        "versao_anthropic": _versao("anthropic"),
        "git_commit": _git("rev-parse", "--short", "HEAD") or "?",
        "git_sujo": bool(_git("status", "--porcelain")),
        "url_base": args.url,
    }
    try:
        llm = httpx.get(f"{args.url}/saude", timeout=10.0).json()["llm"]
        meta["backend_llm_modelo"] = llm["modelo"]
        meta["backend_groundedness_verificar"] = llm["groundedness_verificar"]
    except (httpx.HTTPError, KeyError, ValueError):
        meta["backend_llm_modelo"] = "? (GET /saude falhou)"
    return meta


def media(valores: list[float | None]) -> float | None:
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else None


def agregar_por_categoria(resultados: list[ResultadoCaso]) -> dict[str, dict]:
    """Média de cada métrica por categoria, só sobre as notas obtidas (sem
    NaN, sem erro), com o número de notas `n_<métrica>`."""
    categorias: dict[str, dict] = {}
    for cat in sorted({r.categoria for r in resultados}):
        do_cat = [r for r in resultados if r.categoria == cat]
        linha: dict = {"casos": len(do_cat), "avaliados": sum(r.status == "avaliado" for r in do_cat)}
        for m in METRICAS:
            notas = [r.notas.get(m) for r in do_cat if m in r.notas]
            linha[m] = media(notas)
            linha[f"n_{m}"] = sum(v is not None for v in notas)
        categorias[cat] = linha
    return categorias


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f}"


def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


ABREV = {
    "faithfulness": "Faith.",
    "answer_relevancy": "Relev.",
    "context_precision_with_reference": "CtxPrec.",
    "context_recall": "CtxRec.",
}


def gerar_relatorio(resultados: list[ResultadoCaso], meta: dict) -> str:
    titulo = "Avaliação RAGAS — HerpIA" + (" (DRY-RUN, sem chamadas ao juiz)" if meta["dry_run"] else "")
    partes = [f"# {titulo}", "", f"_Gerado em {meta['timestamp_iso']} por `avaliacao/rodar_ragas.py`._", "", "## Metadados", ""]
    partes += [f"- **{k}:** `{v}`" for k, v in meta.items() if k != "timestamp_iso"]

    contagem: dict[str, int] = {}
    for r in resultados:
        contagem[r.status] = contagem.get(r.status, 0) + 1
    partes += ["", "## Resumo", ""]
    partes += [f"- {status}: {n}" for status, n in sorted(contagem.items())]
    partes.append(f"- chamadas ao juiz estimadas (sem retries): {sum(r.chamadas_estimadas for r in resultados)}")
    partes.append("- caracteres de entrada das métricas (pergunta, resposta, trechos, gabarito): "
                  f"{_milhar(sum(r.caracteres_enviados for r in resultados))}")
    uso = meta.get("uso_juiz")
    if uso:
        partes.append(f"- juiz: {uso['requisicoes']} requisição(ões), {_milhar(uso['input_tokens'])} tokens de entrada, "
                      f"{_milhar(uso['output_tokens'])} de saída (inclui pensamento)"
                      + (f", respostas com erro: {uso['respostas_erro']}" if uso["respostas_erro"] else ""))
        if meta.get("custo_estimado_usd") is not None:
            partes.append(f"- custo estimado: US$ {meta['custo_estimado_usd']:.4f} (preços em `PRECOS_POR_MTOK`; "
                          "a fatura do Console é a fonte oficial)")
    rotas: dict[str, int] = {}
    for r in resultados:
        if r.rota:
            rotas[r.rota["status"]] = rotas.get(r.rota["status"], 0) + 1
    partes.append("- checagens de rota: " + ", ".join(f"{s}={n}" for s, n in sorted(rotas.items())))
    passaram = [r.id for r in resultados if r.rota and r.rota["falha_conhecida_passou"]]
    if passaram:
        partes.append(f"- **atenção:** falha conhecida passou em {', '.join(passaram)} (pode ter sido corrigida)")

    partes += ["", "## Por categoria", "", "| Cat. | Casos | Avaliados | " + " | ".join(ABREV[m] for m in METRICAS) + " |",
               "|---|---:|---:|" + "---:|" * len(METRICAS)]
    for cat, linha in agregar_por_categoria(resultados).items():
        celulas = [f"{_fmt(linha[m])} (n={linha[f'n_{m}']})" for m in METRICAS]
        partes.append(f"| {cat} | {linha['casos']} | {linha['avaliados']} | " + " | ".join(celulas) + " |")

    partes += ["", "## Por caso", "",
               "| Caso | Status | Saída | Retenção | Rota | Contextos | Chamadas | Tokens (ent./saída) | "
               + " | ".join(ABREV[m] for m in METRICAS) + " |",
               "|---|---|---|---|---|---|---:|---:|" + "---:|" * len(METRICAS)]
    for r in resultados:
        fontes = ",".join(c["fonte"] or "?" for c in r.contextos) or "—"
        rota = r.rota["status"] if r.rota else "—"
        tokens = f"{r.uso_juiz['input_tokens']}/{r.uso_juiz['output_tokens']}" if r.uso_juiz else "—"
        notas = [_fmt(r.notas.get(m)) if m in r.notas else ("erro" if m in r.erros_metricas else "—") for m in METRICAS]
        partes.append(
            f"| {r.id} | {r.status} | {r.tipo_saida or '—'} | {r.origem_retencao or '—'} | {rota} | "
            f"{fontes} | {r.chamadas_estimadas} | {tokens} | " + " | ".join(notas) + " |"
        )

    problemas = [r for r in resultados if r.erro_coleta or r.erros_metricas or r.niveis_bloqueados]
    if problemas:
        partes += ["", "## Erros e bloqueios", ""]
        for r in problemas:
            if r.erro_coleta:
                partes.append(f"- **{r.id}** (coleta): {r.erro_coleta}")
            if r.niveis_bloqueados:
                partes.append(f"- **{r.id}** bloqueado: níveis {sorted(map(str, set(r.niveis_bloqueados)))}")
            for m, e in r.erros_metricas.items():
                partes.append(f"- **{r.id}** ({m}): {e}")
    partes.append("")
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def selecionar_casos(casos: list[dict], ids: str | None, max_casos: int | None) -> list[dict]:
    if ids:
        pedidos = [i.strip() for i in ids.split(",") if i.strip()]
        desconhecidos = set(pedidos) - {c["id"] for c in casos}
        if desconhecidos:
            raise SystemExit(f"Casos inexistentes em casos.jsonl: {sorted(desconhecidos)}")
        casos = [c for c in casos if c["id"] in pedidos]
    return casos[:max_casos] if max_casos else casos


async def coletar_todos(args: argparse.Namespace, casos: list[dict]) -> list[dict | str]:
    """Coleta todos os casos antes de qualquer chamada paga. Cada item é o
    corpo da resposta de /perguntar ou o texto do erro de coleta."""
    coletas: list[dict | str] = []
    async with httpx.AsyncClient(base_url=args.url) as client:
        for i, caso in enumerate(casos, start=1):
            print(f"[{i}/{len(casos)}] {caso['id']}: coletando...", flush=True)
            try:
                coletas.append(await coletar(client, caso, args.top_k, args.timeout))
            except httpx.HTTPError as exc:
                coletas.append(f"{type(exc).__name__}: {exc}"[:500])
                print(f"    erro de coleta: {coletas[-1]}")
    return coletas


async def avaliar_todos(
    casos: list[dict],
    coletas: list[dict | str],
    metricas: dict | None,
    selecionadas: tuple[str, ...],
    uso: UsoJuiz | None = None,
) -> list[ResultadoCaso]:
    resultados = []
    for caso, coleta in zip(casos, coletas):
        if isinstance(coleta, str):
            resultados.append(ResultadoCaso(
                id=caso["id"], categoria=caso["categoria"], user_input=caso["user_input"],
                tem_referencia=caso["tem_referencia"], erro_coleta=coleta,
            ))
            continue
        antes = UsoJuiz(**asdict(uso)) if uso else None
        r = await avaliar_caso(caso, coleta, metricas, selecionadas)
        if uso and r.status == "avaliado":
            r.uso_juiz = asdict(uso.desde(antes))
        resultados.append(r)
        notas = ", ".join(f"{ABREV[m]}={_fmt(v)}" for m, v in r.notas.items())
        tokens = f" | tokens={r.uso_juiz['input_tokens']}/{r.uso_juiz['output_tokens']}" if r.uso_juiz else ""
        print(f"{r.id}: {r.status} | saída={r.tipo_saida} | rota={r.rota['status'] if r.rota else '—'}"
              f" | chamadas={r.chamadas_estimadas}" + (f" | {notas}" if notas else "") + tokens)
    return resultados


def gravar(resultados: list[ResultadoCaso], meta: dict, destino: Path) -> tuple[Path, Path]:
    destino.mkdir(parents=True, exist_ok=True)
    sufixo = "_dry-run" if meta["dry_run"] else ""
    base = f"{datetime.now().strftime('%Y-%m-%d_%Hh%M')}_{meta['juiz']}{sufixo}"
    md, js = destino / f"{base}.md", destino / f"{base}.json"
    md.write_text(gerar_relatorio(resultados, meta), encoding="utf-8")
    js.write_text(json.dumps({
        "metadados": meta,
        "por_categoria": agregar_por_categoria(resultados),
        "casos": [asdict(r) for r in resultados],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return md, js


def _lista_metricas(valor: str) -> tuple[str, ...]:
    nomes = tuple(m.strip() for m in valor.split(",") if m.strip())
    invalidas = set(nomes) - set(METRICAS)
    if invalidas:
        raise argparse.ArgumentTypeError(f"métricas fora de {list(METRICAS)}: {sorted(invalidas)}")
    return nomes


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Avaliação offline do HerpIA com RAGAS (ADR 0007).")
    p.add_argument("--url", default=URL_PADRAO, help="backend FastAPI")
    p.add_argument("--juiz", default=JUIZ_PADRAO, help=f"modelo do juiz (padrão: {JUIZ_PADRAO})")
    p.add_argument("--esforco", default=ESFORCO_PADRAO, choices=["low", "medium", "high", "xhigh", "max"],
                   help="output_config.effort do juiz")
    p.add_argument("--top-k", type=int, default=TOP_K_PADRAO)
    p.add_argument("--metricas", type=_lista_metricas, default=METRICAS,
                   help="subconjunto separado por vírgula (ex.: faithfulness)")
    p.add_argument("--casos", help="ids separados por vírgula (ex.: A1,C2)")
    p.add_argument("--max-casos", type=int)
    p.add_argument("--dry-run", action="store_true", help="faz tudo, menos as chamadas pagas ao juiz")
    p.add_argument("--sim", action="store_true", help="não pedir confirmação antes das chamadas pagas")
    p.add_argument("--timeout", type=float, default=600.0, help="timeout de cada /perguntar, em segundos")
    p.add_argument("--saida", type=Path, default=DIR_RESULTADOS)
    args = p.parse_args(argv)

    casos = selecionar_casos(carregar_casos(), args.casos, args.max_casos)
    meta = obter_metadados(args, len(casos))

    try:
        coletas = asyncio.run(coletar_todos(args, casos))
    except ModoAvaliacaoDesabilitado as exc:
        print(f"O backend recusou o modo de avaliação (403): {exc}\n"
              "Suba o backend com PERMITIR_MODO_AVALIACAO=true (só no PC de desenvolvimento).")
        return 2

    # Plano (sem custo): status, bloqueios e chamadas estimadas de cada caso.
    resultados = asyncio.run(avaliar_todos(casos, coletas, None, args.metricas))

    if not args.dry_run:
        chamadas = sum(r.chamadas_estimadas for r in resultados)
        a_avaliar = sum(r.status == "planejado" for r in resultados)
        print(f"\nExecução PAGA: juiz {args.juiz} (esforço {args.esforco}), {a_avaliar} caso(s) a avaliar, "
              f"~{chamadas} chamada(s) ao juiz sem contar retries, métricas {list(args.metricas)}.")
        if not args.sim and input("Confirmar? [s/N] ").strip().lower() != "s":
            print("Cancelado: nenhuma chamada paga foi feita.")
            return 1
        uso = UsoJuiz()
        metricas = criar_metricas(args.juiz, args.esforco, args.metricas, uso=uso, api_key=obter_chave_anthropic())
        resultados = asyncio.run(avaliar_todos(casos, coletas, metricas, args.metricas, uso))
        meta["uso_juiz"] = asdict(uso)
        custo = custo_estimado(uso, args.juiz)
        meta["custo_estimado_usd"] = None if custo is None else round(custo, 4)
        print(f"\nJuiz: {uso.requisicoes} requisição(ões), {uso.input_tokens} tokens de entrada, "
              f"{uso.output_tokens} de saída" + (f", ~US$ {custo:.4f}" if custo is not None else ""))

    md, js = gravar(resultados, meta, args.saida)
    print(f"\nRelatório: {md.relative_to(RAIZ) if md.is_relative_to(RAIZ) else md}")
    print(f"Dados:     {js.relative_to(RAIZ) if js.is_relative_to(RAIZ) else js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
