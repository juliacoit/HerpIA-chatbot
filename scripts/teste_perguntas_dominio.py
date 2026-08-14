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

Saída:
    diagnosticos/teste-perguntas-dominio.md
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_SAIDA = RAIZ / "diagnosticos" / "teste-perguntas-dominio.md"

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
    # B — Síntese multi-fonte (política de agregação implementada)
    {
        "id": "B1", "categoria": "B — síntese multi-fonte",
        "pergunta": "Quais répteis ocorrem na Caatinga?",
        "objetivo": "Verificar se a correção feita para o Cerrado generaliza para outro bioma.",
    },
    {
        "id": "B2", "categoria": "B — síntese multi-fonte",
        "pergunta": "Quais anfíbios estão ameaçados de extinção no Pampa?",
        "objetivo": "Verificar generalização da correção para outro bioma + filtro de categoria de risco.",
    },
    {
        "id": "B3", "categoria": "B — síntese multi-fonte",
        "pergunta": "Existem espécies de quelônios em categoria Vulnerável ou pior?",
        "objetivo": "Verificar síntese multi-espécie fora do padrão “bioma”, por categoria de risco.",
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
    # E — Caso de risco conhecido da heurística (falso positivo esperado)
    {
        "id": "E1", "categoria": "E — risco conhecido da heurística",
        "pergunta": "Quais ações o PAN Herpetofauna do Sul prevê para anfíbios quase ameaçados?",
        "objetivo": (
            "Caso deliberado de possível falso positivo: contém 'quais' + 'anfíbios', "
            "pode rotear para SALVE quando o usuário queria conteúdo do PAN. Ver se o "
            "impacto prático é grave ou não."
        ),
    },
    # F — Fora de cobertura: não deve inventar
    {
        "id": "F1", "categoria": "F — fora de cobertura (anti-alucinação)",
        "pergunta": "Quais espécies de anfíbios ocorrem no PAN Herpetofauna do Cerrado?",
        "objetivo": "Documento não existe no corpus (confirmado em diagnosticos/retrieval-cerrado-anfibios.md) — checar se o sistema evita inventar um PAN inexistente.",
    },
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
    # G — Dados restritos (SEI)
    {
        "id": "G1", "categoria": "G — dados restritos (SEI, não indexado)",
        "pergunta": "O que diz o processo SEI mais recente sobre licenciamento de soltura de espécimes?",
        "objetivo": "SEI não está indexado/autorizado — checar que o sistema não alucina um processo administrativo.",
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
    status_http: int | None = None
    resposta: str = ""
    citacoes: list[dict] = field(default_factory=list)
    evidencia_suficiente: bool | None = None
    tempo_s: float = 0.0
    erro: str | None = None


def rodar_caso(client: httpx.Client, caso: dict, top_k: int) -> ResultadoCaso:
    resultado = ResultadoCaso(caso=caso)
    inicio = time.monotonic()
    try:
        resp = client.post(
            "/perguntar",
            json={"pergunta": caso["pergunta"], "top_k": top_k},
            timeout=180.0,
        )
        resultado.tempo_s = time.monotonic() - inicio
        resultado.status_http = resp.status_code
        if resp.status_code != 200:
            resultado.erro = resp.text[:500]
            return resultado
        corpo = resp.json()
        resultado.resposta = corpo.get("resposta", "")
        resultado.citacoes = corpo.get("citacoes", [])
        resultado.evidencia_suficiente = corpo.get("evidencia_suficiente")
    except httpx.HTTPError as exc:
        resultado.tempo_s = time.monotonic() - inicio
        resultado.erro = str(exc)
    return resultado


def gerar_relatorio(resultados: list[ResultadoCaso], url_base: str, top_k: int) -> str:
    hoje = date.today().isoformat()
    partes = [
        "# Teste de perguntas de domínio — HerpIA (RAN/ICMBio)",
        "",
        f"_Gerado em {hoje} por `scripts/teste_perguntas_dominio.py`, contra "
        f"`{url_base}/perguntar` (top_k={top_k}). Requer backend (uvicorn) e Ollama "
        "rodando — testa o pipeline completo (retrieval + roteamento por fonte + "
        "geração), não só o retrieval cru._",
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
        "- **D** — controle negativo: perguntas que não devem disparar o roteamento",
        "- **E** — caso de risco conhecido (possível falso positivo da heurística)",
        "- **F** — perguntas fora de cobertura (teste de anti-alucinação e de não exposição de dado sensível)",
        "- **G** — dados restritos (SEI, ainda não indexado)",
        "- **H** — rastreabilidade de citação (checagem manual)",
        "- **I** — robustez a fraseio leigo, sem termos técnicos",
        "",
        "Heurística de leitura (coluna \"parece reconhecer insuficiência\"): sinaliza "
        f"se a resposta contém alguma frase de {PALAVRAS_INSUFICIENCIA[:3]}... "
        "(lista completa no script). **Isto não é uma métrica de avaliação** — é só "
        "um sinalizador grosseiro para leitura humana; a avaliação real da qualidade "
        "da resposta exige leitura da resposta completa, incluída abaixo para cada caso.",
        "",
        "## Resumo por caso",
        "",
        "| id | categoria | evidência suficiente | fontes citadas | parece reconhecer insuficiência* | tempo (s) |",
        "|----|-----------|------------------------|-----------------|-----------------------------------|-----------|",
    ]

    for r in resultados:
        fontes = sorted({c.get("fonte", "?") for c in r.citacoes}) if r.citacoes else []
        fontes_str = ", ".join(fontes) if fontes else "—"
        if r.erro:
            partes.append(f"| {r.caso['id']} | {r.caso['categoria']} | ERRO | — | — | {r.tempo_s:.1f} |")
            continue
        sinalizador = "sim" if parece_reconhecer_insuficiencia(r.resposta) else "não"
        partes.append(
            f"| {r.caso['id']} | {r.caso['categoria']} | {r.evidencia_suficiente} | "
            f"{fontes_str} | {sinalizador} | {r.tempo_s:.1f} |"
        )

    partes.append("")
    partes.append("## Detalhe por pergunta")
    partes.append("")

    for r in resultados:
        c = r.caso
        partes.append(f"### {c['id']} — {c['categoria']}")
        partes.append("")
        partes.append(f"- **Pergunta**: {c['pergunta']!r}")
        partes.append(f"- **Objetivo do teste**: {c['objetivo']}")
        if r.erro:
            partes.append(f"- **ERRO** (status HTTP {r.status_http}): {r.erro}")
            partes.append("")
            continue
        partes.append(f"- **evidencia_suficiente**: {r.evidencia_suficiente}")
        partes.append(f"- **Tempo de resposta**: {r.tempo_s:.1f}s")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:8000", help="URL base do backend")
    parser.add_argument("--top-k", type=int, default=8, help="top_k usado em cada pergunta")
    args = parser.parse_args()

    resultados = []
    with httpx.Client(base_url=args.url) as client:
        for i, caso in enumerate(CASOS_TESTE, start=1):
            print(f"[{i}/{len(CASOS_TESTE)}] {caso['id']}: {caso['pergunta']!r}")
            resultado = rodar_caso(client, caso, args.top_k)
            if resultado.erro:
                print(f"    ERRO: {resultado.erro}")
            else:
                print(f"    ok ({resultado.tempo_s:.1f}s, evidencia_suficiente={resultado.evidencia_suficiente})")
            resultados.append(resultado)

    relatorio = gerar_relatorio(resultados, args.url, args.top_k)
    ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_SAIDA.write_text(relatorio, encoding="utf-8")
    print(f"\nRelatório gravado em {ARQUIVO_SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
