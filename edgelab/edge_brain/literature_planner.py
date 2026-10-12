"""Planificador de contrastes: que hallazgos SSRN vale la pena llevar a una corrida Kaggle de EdgeLab (2026-10-09).

Heuristica determinista y revisable (sin modelos). Para cada hallazgo relevante a la consulta:

1. ``needs``: que datos haria falta para medirlo (regex sobre afirmacion/condiciones/mercado).
2. ``blockers``: lo que EdgeLab NO tiene hoy segun el catalogo de Kaggle (``edgelab-data-catalog``): profundidad L2,
   mensajes de ordenes, tamanos L1, opciones, seccion cruzada de acciones, historia de varios anos.
3. ``transfer``: cercania del mercado del paper a los futuros CME que tenemos (indices > FX/oro/tasas > acciones...).
4. ``model_specific``: hallazgos sobre la precision de un modelo propio del paper (LSTM, RL...) bajan de prioridad:
   reproducirlos exige reimplementar su modelo, no medir un fenomeno.

Tambien bloquean: hallazgos de un evento puntual (SPECIFIC_EVENT), que requieren identificar participantes
(PARTICIPANT_IDS), citas de segunda mano (SECONDARY_CITATION) o mercados que no tenemos (OTHER_MARKETS).

``priority = relevancia * transfer * (1 | 0.15 si hay blockers) * (0.5 si model_specific) * (1.1 si cuantitativo)
* (0.3 si no menciona nada medible con nuestros datos)``.
Es una propuesta para un humano: no aprueba campanas ni corre nada.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .trading_glossary import fold

# Lo que hay hoy en Kaggle (docs del catalogo, 2026-10-05): ticks CME con trade/aggressor y bid/ask en precio,
# 14 instrumentos (ES NQ YM RTY MES MNQ MYM GC MGC 6E 6B 6J ZB MBT), ~2025-07 a 2026-09; spot Dukascopy.
EDGELAB_DATA = frozenset({"TRADES", "AGGRESSOR", "L1_QUOTE_PRICES", "INTRADAY_CLOCK"})
INSTRUMENTS = ("ES", "NQ", "YM", "RTY", "MES", "MNQ", "MYM", "GC", "MGC", "6E", "6B", "6J", "ZB", "MBT")

_NEEDS: tuple[tuple[str, str], ...] = (
    ("L2_DEPTH", r"profundidad|depth|book slope|pendiente del libro|cola|queue|niveles del libro|multi.?level|varios niveles"),
    ("ORDER_MESSAGES", r"cancel|rechaz|mensaje|order.level|submission|llegada de ordenes limite|limit order arrival|limit order flow|flujos? de ordenes limite|hidden|ocult"),
    ("L1_SIZES", r"microprice|micro.?precio|imbalance de cotiz|queue imbalance|tamano en el (bid|ask)|best bid size"),
    ("OPTIONS", r"opcion|option|implied|implicita|vix|varianza implicita|variance risk premium"),
    ("CROSS_SECTION", r"\bacciones\b|stocks|portafolio|portfolio|cartera|cross.?section|\d{2,} (acciones|stocks)|pares de acciones|sectores|sectorial|\bpca\b"),
    ("NON_EMPIRICAL", r"costo computacional|tiempo de (computo|calculo)|horas con el metodo|simulad[oa]s? (por|con) el modelo"),
    ("SPECIFIC_EVENT", r"introduccion de|co.?location|interrupcion|intervencion|evento de|crisis|\b(19|200)\d\b|cambio (de|en) (la )?(regla|regulacion)|post.?entrada|entrada (de )?hft|decimaliz|tick size pilot"),
    ("PARTICIPANT_IDS", r"\bhfts?\b (orientad|tomador|proveedor)|banco lider|bancos|identificad|cuentas|por participante|institucional(es)? (vs|frente)|traders? hft"),
    ("SECONDARY_CITATION", r"citad[oa]s? como|segun (la )?literatura previa|referencia externa"),
    ("OTHER_MARKETS", r"wti|brent|dubai|crudo|crude|commodit|chin|bitcoin|cripto|crypto|jse|ibovespa|asx|india"),
    ("TRADES", r"trade|operacion|volumen|volume|transacc"),
    ("AGGRESSOR", r"agres|compra|venta|buy|sell|signo|order flow|flujo de ordenes|imbalance|desbalance"),
    ("INTRADAY_CLOCK", r"intrad|hora|minuto|apertura|cierre|sesion|open|close"),
)
_MODEL = r"llm|gpt|lstm|red(es)? neuronal|neural|transformer|xgboost|random forest|reinforcement|refuerzo|a2c|dqn|ppo|deep|svm|accuracy del modelo|el modelo (predice|alcanza|logra)"
_MARKET = ((0.35, r"cripto|crypto|bitcoin|china|chinese|india|jse|ibovespa|asx|hyperliquid|brasil|brazil"),
           (1.0, r"e.?mini|\bes\b|\bnq\b|s&p 500 futur|futuros? (de )?indice|index futures|nasdaq.?100 futur|dow futur"),
           (0.85, r"futur"),
           (0.7, r"fx|divisa|euro|forex|oro|gold|bund|bono|bond|treasury|tasas"),
           (0.55, r"us equit|nasdaq|nyse|s&p|acciones (de )?ee\.?uu|equities|stocks|acciones"))


@dataclass(frozen=True)
class TestProposal:
    claim_id: str
    source_id: str
    title: str
    claim: str
    market: str
    magnitude: str
    relevance: float
    transfer: float
    needs: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    model_specific: bool = False
    priority: float = 0.0
    status: str = "AUTHOR_REPORTED_RESULT"
    authority_status: str = "AUTHOR_REPORTED_RESULT"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _field(text: str, name: str) -> str:
    m = re.search(rf"{name}: (.*?)(?: \| \w+: |$)", text)
    return m.group(1).strip() if m else ""


def assess(text: str, title: str = "") -> dict[str, Any]:
    """Requisitos de datos, bloqueos y transferibilidad de un hallazgo (texto 'afirmacion: ... | mercado: ...')."""
    # requisitos: solo afirmacion/condiciones/magnitud (el mercado y el periodo van a `transfer`, no bloquean)
    t = fold(" ".join(_field(text, k) for k in ("afirmacion", "condiciones", "magnitud")) or text)
    needs = [n for n, rx in _NEEDS if re.search(rx, t)]
    blockers = [n for n in needs if n not in EDGELAB_DATA]
    measurable = any(n in EDGELAB_DATA for n in needs)
    market = fold(_field(text, "mercado"))
    transfer = next((w for w, rx in _MARKET if re.search(rx, market)), 0.5)
    model = bool(re.search(_MODEL, fold(_field(text, "afirmacion") + " " + title)))
    quantitative = bool(re.search(r"\d", _field(text, "magnitud")))
    return dict(needs=needs, blockers=blockers, transfer=transfer, model_specific=model, quantitative=quantitative,
                measurable=measurable)


def propose_tests(cortex, queries: Iterable[str] | str, *, limit: int = 10, per_query: int = 15,
                  claim_status=None, include_blocked: bool = False) -> list[TestProposal]:
    """Hallazgos candidatos a contrastar, ordenados por prioridad. ``claim_status(claim_id)`` (del hipocampo)
    excluye los ya contrastados."""
    if isinstance(queries, str):
        queries = [queries]
    best: dict[str, TestProposal] = {}
    for q in queries:
        hits = cortex.search_findings_ranked(q, limit=per_query)
        top = max((h["score"] for h in hits), default=0.0) or 1.0
        for h in hits:
            status = claim_status(h["claim_id"]) if claim_status else "AUTHOR_REPORTED_RESULT"
            if status != "AUTHOR_REPORTED_RESULT":
                continue
            a = assess(h["text"], h["title"])
            if a["blockers"] and not include_blocked:
                continue
            rel = h["score"] / top
            pr = rel * a["transfer"] * (0.15 if a["blockers"] else 1.0) * (0.5 if a["model_specific"] else 1.0) \
                * (1.1 if a["quantitative"] else 1.0) * (1.0 if a["measurable"] else 0.3)
            prop = TestProposal(claim_id=h["claim_id"], source_id=f"SRC-SSRN-{h['doc_id']:04d}", title=h["title"],
                                claim=_field(h["text"], "afirmacion"), market=_field(h["text"], "mercado"),
                                magnitude=_field(h["text"], "magnitud"), relevance=round(rel, 4),
                                transfer=a["transfer"], needs=a["needs"], blockers=a["blockers"],
                                model_specific=a["model_specific"], priority=round(pr, 4), status=status)
            if prop.claim_id not in best or prop.priority > best[prop.claim_id].priority:
                best[prop.claim_id] = prop
    return sorted(best.values(), key=lambda p: (-p.priority, p.claim_id))[: max(1, int(limit))]
