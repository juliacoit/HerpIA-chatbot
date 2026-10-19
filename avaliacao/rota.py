"""Checagens determinísticas de rota da avaliação (sem LLM, sem custo).

A rota escolhida por `buscar_chunks_priorizados` não aparece na resposta do
/perguntar. Por isso a avaliação a verifica de dois jeitos:

- **Decisão:** recalcula `detectar_fonte_prioritaria(pergunta)`, a mesma
  função pura que a produção usa, e compara com `rota_esperada` ("salve" ou
  "nenhuma"; omitido = indiferente). Isso pega regressões no regex do gate.
  Não pega erro de especificação, porque testa a mesma função.
- **Efeito:** confere a `fonte` dos contextos devolvidos em modo de
  avaliação.
  - Com `rota_esperada == "salve"`, a checagem é estrita: o **primeiro**
    contexto precisa ser da `fonte_esperada`, porque os prioritários vêm
    primeiro (roteamento.py).
  - Nos demais casos, basta a `fonte_esperada` aparecer no top-k, e a fração
    de contextos dessa fonte fica registrada.

Um caso com `falha_conhecida` que falha recebe o status `falha_conhecida`, e
não `divergente`. Se passar, `falha_conhecida_passou` fica True, para o
relatório avisar que a falha pode ter sido corrigida.
"""

from dataclasses import dataclass

from backend.services.roteamento import detectar_fonte_prioritaria

# Status por checagem: "ok", "divergente", "falha_conhecida" ou "nao_checada".


@dataclass
class ResultadoRota:
    rota_obtida: str              # "salve" ou "nenhuma"
    decisao: str
    efeito: str
    fracao_fonte_esperada: float | None
    falha_conhecida_passou: bool

    @property
    def status(self) -> str:
        """Status agregado do caso, o pior das duas checagens."""
        for s in ("divergente", "falha_conhecida", "ok"):
            if s in (self.decisao, self.efeito):
                return s
        return "nao_checada"


def checar_rota(caso: dict, fontes_contextos: list[str]) -> ResultadoRota:
    """`caso` vem de avaliacao.casos.carregar_casos. `fontes_contextos` é a
    `fonte` de cada item de `avaliacao.contextos`, na ordem devolvida."""
    rota_obtida = detectar_fonte_prioritaria(caso["user_input"]) or "nenhuma"

    rota_esperada = caso.get("rota_esperada")
    if rota_esperada is None:
        decisao_ok = None
    else:
        decisao_ok = rota_obtida == rota_esperada

    fonte = caso.get("fonte_esperada")
    fracao = None
    if fonte is None:
        efeito_ok = None
    else:
        fracao = (fontes_contextos.count(fonte) / len(fontes_contextos)) if fontes_contextos else 0.0
        if rota_esperada == "salve":
            efeito_ok = bool(fontes_contextos) and fontes_contextos[0] == fonte
        else:
            efeito_ok = fonte in fontes_contextos

    conhecida = bool(caso.get("falha_conhecida"))

    def status(ok: bool | None) -> str:
        if ok is None:
            return "nao_checada"
        if ok:
            return "ok"
        return "falha_conhecida" if conhecida else "divergente"

    checadas = [ok for ok in (decisao_ok, efeito_ok) if ok is not None]
    passou = conhecida and bool(checadas) and all(checadas)

    return ResultadoRota(
        rota_obtida=rota_obtida,
        decisao=status(decisao_ok),
        efeito=status(efeito_ok),
        fracao_fonte_esperada=fracao,
        falha_conhecida_passou=passou,
    )
