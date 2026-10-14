"""Rodada 2: comparação offline de juízes de groundedness.

Cada juiz recebe os mesmos pares (pergunta, trechos, resposta) do conjunto
rotulado (diagnosticos/juizes/conjunto_rotulado.jsonl, ver o README da pasta)
e devolve um veredito: fundamentada ou não. Nenhuma resposta nova é gerada e
a API não muda — todos os adaptadores vivem só neste script.

Juízes:
    J1  autojulgamento: modelo gerador padrão (LLM_MODEL), verificar_com_llm atual
    J2  granite4.1-guardian:8b, critério pré-definido "groundedness", sem thinking
    J3  granite4.1-guardian:8b, critério próprio (BYOC), sem thinking
    J4  bespoke-minicheck, uma chamada por frase da resposta
    J6  gpt-oss:20b, verificar_com_llm atual (think="low", como na rodada 1)

O J5 (qwen3.5:9b, think=false) reteve os 53 itens e saiu da comparação em
2026-10-09; continua definido para reproduzir resultados_J5*.jsonl, mas fora
da lista padrão de --juizes.

J1, J5 e J6 importam e chamam backend.services.groundedness.verificar_com_llm,
com os termos suspeitos da camada 2 (checar_ancoras_meio_frase), sem copiar
nada. J2–J4 usam os templates oficiais embutidos nos modelos do Ollama (ver
TEMPLATE_* abaixo e o relatório da rodada 2).

Configuração comum: temperature=0, seed=42, num_ctx=8192.

Uso:
    # teste de fumaça (imprime, não grava)
    python scripts/avaliar_juizes.py --juizes J2,J3 --itens r1-qwen2.5-3b-D1-e1,r1-qwen2.5-3b-A1-e1

    # execução completa de um juiz (grava diagnosticos/juizes/resultados_<juiz>.jsonl)
    python scripts/avaliar_juizes.py --juizes J4 --repeticoes 2 --gravar

O MiniCheck (J4) tem licença CC BY-NC 4.0 (uso não comercial): usado só
nesta avaliação.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import httpx

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backend.config import Settings  # noqa: E402
from backend.schemas import ChunkRecuperado  # noqa: E402
from backend.services.groundedness import (  # noqa: E402
    checar_ancoras_meio_frase,
    dividir_frases,
    motivo_sem_afirmacao,
    verificar_com_llm,
)
from backend.services.llm import OllamaLLMClient, registrar_uso_llm  # noqa: E402

CONJUNTO = RAIZ / "diagnosticos" / "juizes" / "conjunto_rotulado.jsonl"
PASTA_RESULTADOS = RAIZ / "diagnosticos" / "juizes"

OPCOES_COMUNS = {"temperature": 0, "seed": 42, "num_ctx": 8192}  # num_ctx muda com --num-ctx
TIMEOUT_S = 900.0
# Teto de saída do MiniCheck, que só responde "Yes"/"No" (8 tokens). Sem ele,
# um prompt cortado pelo Ollama faz o modelo sair do formato e gerar texto
# livre até estourar o TIMEOUT_S.
MAX_TOKENS_MINICHECK = 32

MODELO_GUARDIAN = "granite4.1-guardian:8b"
MODELO_MINICHECK = "bespoke-minicheck"

# Critério BYOC do J3. Em inglês, como os critérios nativos do Guardian
# (o template do modelo usa o texto da mensagem "system" como critério quando
# ele não é um dos nomes pré-definidos).
CRITERIO_J3 = (
    "A text is considered ungrounded if it includes any claim, name, number, "
    "classification or attribution that lacks support from, or directly "
    "contradicts, the provided document(s). This includes presenting "
    "information from one document as if it were about a different document, "
    "species or entity, and describing what a document probably or possibly "
    "contains instead of what the documents actually state. The following are "
    "NOT ungrounded: (1) stating that the provided documents do not contain the "
    "information needed to answer the question; (2) correcting a false premise "
    "in the user's question based on what the documents state; (3) combining "
    "information from several documents, as long as each individual claim is "
    "supported by at least one document. The documents, the question and the "
    "text may be written in Portuguese."
)

# Parse oficial do Guardian (model card ibm-granite/granite-guardian-4.1-8b):
# descarta o bloco <think> e lê o conteúdo de <score>.
_PADRAO_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_PADRAO_SCORE = re.compile(r"<score>\s*(.*?)\s*</score>", re.DOTALL)


@dataclass
class Veredito:
    fundamentada: bool | None  # None = falha de parse
    justificativa: str | None
    chamadas: int
    tempo_s: float
    bruto: str  # saída crua do modelo, para auditoria
    detalhes: dict = field(default_factory=dict)  # tokens, frases do J4 etc.


class Juiz(Protocol):
    nome: str

    async def julgar(self, pergunta: str, trechos: list[dict], resposta: str) -> Veredito: ...


def _para_chunks(trechos: list[dict]) -> list[ChunkRecuperado]:
    return [
        ChunkRecuperado(
            score=0.0,
            fonte=t["fonte"],
            documento=t["documento"],
            texto=t["texto"],
            secao=t.get("secao"),
            pagina_inicio=t.get("pagina_inicio"),
            pagina_fim=t.get("pagina_fim"),
        )
        for t in trechos
    ]


def _rotulo_trecho(i: int, t: dict) -> str:
    """Mesmo cabeçalho de trecho usado por geracao.py e verificar_com_llm."""
    return f"Trecho {i + 1} — fonte: {t['fonte']}, documento: {t['documento']}"


# ---------------------------------------------------------------------------
# J1, J5, J6: generalistas com o verificar_com_llm de produção
# ---------------------------------------------------------------------------


class _ClienteGravador(OllamaLLMClient):
    """OllamaLLMClient que guarda a saída crua de cada chamada, porque
    verificar_com_llm só devolve (bool, justificativa)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saidas: list[str] = []

    async def generate(self, prompt: str) -> str:
        saida = await super().generate(prompt)
        self.saidas.append(saida)
        return saida


class JuizGeneralista:
    def __init__(self, nome: str, base_url: str, modelo: str, think: bool | str | None):
        self.nome = nome
        self.modelo = modelo
        self._cliente = _ClienteGravador(
            base_url=base_url, modelo=modelo, opcoes=dict(OPCOES_COMUNS), think=think, timeout=TIMEOUT_S
        )

    async def julgar(self, pergunta: str, trechos: list[dict], resposta: str) -> Veredito:
        chunks = _para_chunks(trechos)
        _, termos_suspeitos = checar_ancoras_meio_frase(resposta, chunks, pergunta)
        self._cliente.saidas.clear()
        inicio = time.perf_counter()
        with registrar_uso_llm() as uso:
            fundamentada, justificativa = await verificar_com_llm(
                self._cliente, pergunta, resposta, chunks, termos_suspeitos
            )
        tempo = time.perf_counter() - inicio
        bruto = self._cliente.saidas[-1] if self._cliente.saidas else ""
        # verificar_com_llm falha fechado (tudo que não começa com SIM vira
        # False). Aqui separamos "NÃO" explícito de saída que não segue o
        # formato, para contar falhas de parse.
        primeira = bruto.strip().splitlines()[0].strip().upper() if bruto.strip() else ""
        if not (primeira.startswith("SIM") or primeira.startswith("NÃO") or primeira.startswith("NAO")):
            fundamentada = None
        return Veredito(
            fundamentada=fundamentada,
            justificativa=justificativa,
            chamadas=len(uso),
            tempo_s=round(tempo, 2),
            bruto=bruto,
            detalhes={"uso": uso, "termos_suspeitos": termos_suspeitos},
        )


# ---------------------------------------------------------------------------
# J2, J3: Granite Guardian 4.1
# ---------------------------------------------------------------------------
#
# Template oficial (ollama.com/library/granite4.1-guardian, template embutido no
# modelo, digest c17246311739): a 1ª mensagem "system" é o critério — um nome
# pré-definido ("groundedness") ou um texto livre (BYOC); mensagens com papel
# "document<título>" viram a lista <documents> do system prompt; o bloco
# <guardian> com o critério é injetado pelo próprio template como última
# mensagem do usuário, e o "Scoring Schema" é escolhido pelo papel da última
# mensagem (assistant → "If the last assistant's text meets the criteria,
# return 'yes'"). Ou seja: yes = critério de risco atendido = NÃO fundamentada.


class JuizGuardian:
    def __init__(self, nome: str, base_url: str, criterio: str):
        self.nome = nome
        self.modelo = MODELO_GUARDIAN
        self._url = base_url.rstrip("/") + "/api/chat"
        self.criterio = criterio

    def montar_mensagens(self, pergunta: str, trechos: list[dict], resposta: str) -> list[dict]:
        mensagens = [{"role": "system", "content": self.criterio}]
        mensagens += [
            {"role": f"document {_rotulo_trecho(i, t)}", "content": t["texto"]} for i, t in enumerate(trechos)
        ]
        mensagens += [
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": resposta},
        ]
        return mensagens

    async def julgar(self, pergunta: str, trechos: list[dict], resposta: str) -> Veredito:
        payload = {
            "model": self.modelo,
            "messages": self.montar_mensagens(pergunta, trechos, resposta),
            "think": False,
            "stream": False,
            "options": dict(OPCOES_COMUNS),
        }
        inicio = time.perf_counter()
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as cliente:
            r = await cliente.post(self._url, json=payload)
            r.raise_for_status()
            corpo = r.json()
        tempo = time.perf_counter() - inicio
        mensagem = corpo.get("message", {})
        bruto = mensagem.get("content", "")
        score = _PADRAO_SCORE.findall(_PADRAO_THINK.sub("", bruto).strip())
        valor = score[0].strip().lower() if score else ""
        fundamentada = {"yes": False, "no": True}.get(valor)
        return Veredito(
            fundamentada=fundamentada,
            justificativa=None,
            chamadas=1,
            tempo_s=round(tempo, 2),
            bruto=bruto,
            detalhes={
                "score": valor or None,
                "thinking": mensagem.get("thinking"),
                "uso": [_uso(corpo)],
            },
        )


# ---------------------------------------------------------------------------
# J4: Bespoke-MiniCheck, uma chamada por frase
# ---------------------------------------------------------------------------
#
# Template oficial (ollama.com/library/bespoke-minicheck): prompt
# "Document: {documento}\nClaim: {afirmação}" em /api/generate; o system prompt
# embutido no modelo (digest 016aea4b585f) pede "Yes" ou "No". O README do
# modelo pede que respostas com várias frases sejam divididas em frases antes.

# A divisão em frases e os padrões de frase pulada vivem em groundedness.py
# (dividir_frases, motivo_sem_afirmacao), que os usa na camada 0.


def motivo_pular(frase: str, regra: str = "v3") -> str | None:
    """Motivo para a frase não ir ao MiniCheck. A regra v3 é a de produção
    (groundedness.motivo_sem_afirmacao); v2 não pula negação sobre os trechos
    e v1 também não pula a abstenção "extra"."""
    motivo = motivo_sem_afirmacao(frase)
    if motivo == "negacao_sobre_trechos" and regra != "v3":
        return None
    if motivo == "abstencao_extra" and regra == "v1":
        return None
    return motivo


class JuizMiniCheck:
    def __init__(self, nome: str, base_url: str, regra_pular: str = "v3"):
        self.nome = nome
        self.modelo = MODELO_MINICHECK
        self._url = base_url.rstrip("/") + "/api/generate"
        self.regra_pular = regra_pular

    @staticmethod
    def montar_documento(trechos: list[dict]) -> str:
        return "\n\n".join(f"[{_rotulo_trecho(i, t)}]\n{t['texto']}" for i, t in enumerate(trechos))

    async def julgar(self, pergunta: str, trechos: list[dict], resposta: str) -> Veredito:
        documento = self.montar_documento(trechos)
        frases = []
        brutos = []
        usos = []
        inicio = time.perf_counter()
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as cliente:
            for frase in dividir_frases(resposta):
                motivo = motivo_pular(frase, self.regra_pular)
                if motivo:
                    frases.append({"frase": frase, "pulada": motivo})
                    continue
                payload = {
                    "model": self.modelo,
                    "prompt": f"Document: {documento}\nClaim: {frase}",
                    "stream": False,
                    "options": {**OPCOES_COMUNS, "num_predict": MAX_TOKENS_MINICHECK},
                }
                r = await cliente.post(self._url, json=payload)
                r.raise_for_status()
                corpo = r.json()
                saida = corpo.get("response", "").strip()
                brutos.append(saida)
                usos.append(_uso(corpo))
                palavra = saida.lower().lstrip("\"'* ")
                suportada = True if palavra.startswith("yes") else False if palavra.startswith("no") else None
                frases.append({"frase": frase, "suportada": suportada, "bruto": saida})
        tempo = time.perf_counter() - inicio

        checadas = [f for f in frases if "pulada" not in f]
        if any(f["suportada"] is False for f in checadas):
            fundamentada = False
        elif any(f["suportada"] is None for f in checadas):
            fundamentada = None
        else:
            fundamentada = True  # inclui resposta só com frases puladas (abstenção pura)
        reprovadas = [f["frase"] for f in checadas if f["suportada"] is False]
        return Veredito(
            fundamentada=fundamentada,
            justificativa=("Frases sem suporte: " + " | ".join(reprovadas)) if reprovadas else None,
            chamadas=len(checadas),
            tempo_s=round(tempo, 2),
            bruto=" | ".join(brutos),
            detalhes={"frases": frases, "uso": usos, "regra_pular": self.regra_pular},
        )


def _uso(corpo: dict) -> dict:
    return {
        "prompt_eval_count": corpo.get("prompt_eval_count"),
        "eval_count": corpo.get("eval_count"),
        "num_ctx": OPCOES_COMUNS["num_ctx"],
    }


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


def criar_juizes(settings: Settings, regra_pular: str) -> dict[str, Juiz]:
    url = settings.ollama_url
    return {
        "J1": JuizGeneralista("J1", url, settings.llm_model, think=False),
        "J2": JuizGuardian("J2", url, "groundedness"),
        "J3": JuizGuardian("J3", url, CRITERIO_J3),
        "J4": JuizMiniCheck("J4", url, regra_pular),
        # Mesmo J4 com a regra de pulo mais estreita (só checar_abstencao_honesta),
        # para medir a troca entre abstenções retidas e alucinações escondidas.
        "J4-v1": JuizMiniCheck("J4-v1", url, "v1"),
        "J5": JuizGeneralista("J5", url, "qwen3.5:9b", think=False),
        "J6": JuizGeneralista("J6", url, "gpt-oss:20b", think="low"),
    }


def carregar_conjunto(ids: list[str] | None, caminho: Path = CONJUNTO) -> list[dict]:
    # split("\n"), não splitlines(): o texto de alguns trechos tem separadores
    # Unicode (ex.: \x1c,  ) que splitlines() trataria como fim de linha.
    linhas = caminho.read_text(encoding="utf-8").split("\n")
    itens = [json.loads(linha) for linha in linhas if linha.strip()]
    if ids:
        por_id = {i["id"]: i for i in itens}
        faltando = [i for i in ids if i not in por_id]
        if faltando:
            raise SystemExit(f"ids inexistentes no conjunto: {faltando}")
        itens = [por_id[i] for i in ids]
    return itens


async def aquecer(juiz: Juiz, item: dict) -> None:
    """Uma chamada fora da medição, para carregar o modelo na memória."""
    if isinstance(juiz, JuizMiniCheck):
        await JuizMiniCheck(juiz.nome, juiz._url.rsplit("/api", 1)[0], juiz.regra_pular).julgar(
            item["pergunta"], item["trechos"][:1], "Teste."
        )
    else:
        await juiz.julgar(item["pergunta"], item["trechos"], item["resposta"])


def _ja_gravados(destino: Path) -> set[tuple[str, int]]:
    """Pares (id, repetição) já presentes no arquivo de resultados."""
    linhas = destino.read_text(encoding="utf-8").split("\n")
    registros = [json.loads(linha) for linha in linhas if linha.strip()]
    return {(r["id"], r["repeticao"]) for r in registros}


async def rodar(
    juizes: list[Juiz],
    itens: list[dict],
    repeticoes: int,
    gravar: bool,
    aquecimento: bool,
    retomar: bool = False,
    sufixo: str = "",
) -> None:
    for juiz in juizes:
        print(f"\n===== {juiz.nome} ({juiz.modelo}) =====", flush=True)
        destino = PASTA_RESULTADOS / f"resultados_{juiz.nome}{sufixo}.jsonl" if gravar else None
        feitos: set[tuple[str, int]] = set()
        if destino and destino.exists():
            if not retomar:
                raise SystemExit(f"{destino} já existe; mova ou apague antes de regravar (ou use --retomar).")
            feitos = _ja_gravados(destino)
            pendentes = sum((i["id"], r) not in feitos for i in itens for r in range(1, repeticoes + 1))
            print(f"retomando: {len(feitos)} já gravados, {pendentes} pendentes", flush=True)
            if not pendentes:
                continue
        if aquecimento:
            await aquecer(juiz, itens[0])
        for repeticao in range(1, repeticoes + 1):
            for item in itens:
                if (item["id"], repeticao) in feitos:
                    continue
                v = await juiz.julgar(item["pergunta"], item["trechos"], item["resposta"])
                registro = {
                    "id": item["id"],
                    "juiz": juiz.nome,
                    "modelo": juiz.modelo,
                    "repeticao": repeticao,
                    "rotulo": item["rotulo"],
                    "num_ctx": OPCOES_COMUNS["num_ctx"],
                    **asdict(v),
                }
                if destino:
                    with destino.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
                _imprimir(registro, detalhado=not gravar)


def _imprimir(r: dict, detalhado: bool) -> None:
    veredito = {True: "fundamentada", False: "NÃO fundamentada", None: "falha de parse"}[r["fundamentada"]]
    tokens = [u.get("prompt_eval_count") for u in r["detalhes"].get("uso", [])]
    print(
        f"[{r['juiz']} rep{r['repeticao']}] {r['id']} (rótulo: {r['rotulo']}) → {veredito} | "
        f"chamadas={r['chamadas']} tempo={r['tempo_s']}s prompt_tokens={tokens}",
        flush=True,
    )
    if detalhado:
        print(f"  bruto: {r['bruto']!r}")
        if r["justificativa"]:
            print(f"  justificativa: {r['justificativa']}")
        for f in r["detalhes"].get("frases", []):
            marca = f"pulada ({f['pulada']})" if "pulada" in f else f"{f['bruto']!r}"
            print(f"    - {marca}: {f['frase'][:140]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--juizes", default="J1,J2,J3,J4,J6", help="lista separada por vírgula")
    parser.add_argument("--conjunto", type=Path, default=CONJUNTO, help="arquivo .jsonl com os itens a julgar")
    parser.add_argument("--itens", help="ids do conjunto, separados por vírgula (padrão: todos)")
    parser.add_argument("--repeticoes", type=int, default=1)
    parser.add_argument("--gravar", action="store_true", help="grava diagnosticos/juizes/resultados_<juiz>.jsonl")
    parser.add_argument(
        "--retomar", action="store_true", help="com --gravar: continua um arquivo interrompido, pulando o já gravado"
    )
    parser.add_argument("--num-ctx", type=int, default=OPCOES_COMUNS["num_ctx"], help="contexto de todos os juízes")
    parser.add_argument("--sufixo", default="", help="com --gravar: grava resultados_<juiz>_<sufixo>.jsonl")
    parser.add_argument("--sem-aquecimento", action="store_true")
    parser.add_argument("--regra-pular", choices=["v1", "v2", "v3"], default="v3", help="frases puladas no J4")
    args = parser.parse_args()

    OPCOES_COMUNS["num_ctx"] = args.num_ctx  # antes de criar os juízes, que copiam as opções
    settings = Settings()
    todos = criar_juizes(settings, args.regra_pular)
    nomes = [n.strip() for n in args.juizes.split(",")]
    juizes = [todos[n] for n in nomes]
    itens = carregar_conjunto(args.itens.split(",") if args.itens else None, args.conjunto)
    sufixo = f"_{args.sufixo}" if args.sufixo else ""
    asyncio.run(rodar(juizes, itens, args.repeticoes, args.gravar, not args.sem_aquecimento, args.retomar, sufixo))


if __name__ == "__main__":
    main()
