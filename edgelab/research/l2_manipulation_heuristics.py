"""Detectores PROVISIONALES de spoofing e iceberg sobre el libro L2 reconstruido.

**Target-free.** No miran retornos ni P&L: solo la secuencia de eventos del libro (`tools/build_l2_viewer_bundle.py`)
y las ejecuciones del mismo feed. Son heurísticas de trabajo, **NO verificadas contra ground truth** — no existe:
el feed es MBP (Market By Price, por nivel), **no MBO** (no hay ID de orden ni prioridad), así que "una orden" es
una inferencia sobre la serie de tamaños a un (lado, precio), que puede mezclar varias órdenes reales de distintos
participantes. Cada candidato queda marcado `status="HEURISTIC_UNVALIDATED"`: sirve para ubicar casos a revisar a
mano, nunca para afirmar manipulación. Auditoría 2026-09-21 (ver `docs/CURRENT.md`): corrige el uso de segundos
truncados (ahora todo el tiempo es en MICROSEGUNDOS enteros, `*_ts_us`), agrega `candidate_id` determinista,
separa volumen ATRIBUIDO (a un lado con agresor definido) de AMBIGUO (trades neutrales cerca del nivel, que antes
se acreditaban silenciosamente a los dos lados a la vez), y corrige un caso de doble conteo (delete+add que podía
leerse como relleno de un iceberg ya borrado).

ICEBERG (candidato). A un (lado, precio) el tamaño visible baja porque un trade lo consume (hay una ejecución
ATRIBUIDA a ese lado, en ese precio, en los `trade_window_us` microsegundos previos), y en los siguientes
`refill_window_us` microsegundos el tamaño vuelve a un nivel parecido (`>= refill_min_ratio` del que tenía antes
de consumirse). Si eso se repite `min_refills` veces o más en la sesión, se marca como candidato. Un DELETE
explícito del nivel cierra el ciclo de consumo pendiente (una reaparición posterior es una orden NUEVA, no un
relleno) — antes no se limpiaba y un delete+add podía contar como relleno.

SPOOFING (candidato). Aparece un tamaño grande (percentil `large_size_pctl` del lado, sobre los tamaños no nulos
de la sesión) a un (lado, precio), y desaparece (baja del umbral, o se borra) en menos de `max_lifetime_us`
microsegundos habiendo sido ejecutado (por trades ATRIBUIDOS en ese precio) menos del `max_fill_ratio` de su
tamaño pico. Es decir: se fue sin haberse llenado. Solo se emiten vidas COMPLETAS (que nacieron y murieron dentro
de la sesión); una orden grande que sigue viva al cierre, o que ya estaba viva al empezar la sesión (el primer
evento la encuentra por encima del umbral sin haber visto su nacimiento), NO se cuenta — no se observó el ciclo
completo.

POLÍTICA DE TRADES NEUTRALES (`neutral_policy`, obligatoria y testeada, ver `D` en la auditoría). La regla de
cotización + tick-test puede dejar un trade sin lado de agresor resuelto (NEUTRAL). Atribuirlo a los dos lados a
la vez —como hacía la versión anterior— cuenta la misma ejecución como si fueran dos consumos observados, sin
declararlo. Tres políticas explícitas:
  - `"abstain"` (default): el volumen neutral no se acredita a ningún lado; queda contado aparte como AMBIGUO.
  - `"distribute"`: se reparte 50/50 entre ambos lados (declarado, no oculto).
  - `"credit_both_exploratory"`: comportamiento anterior (doble acreditación), SOLO para modo exploratorio.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

ASK, BID = 0, 1
NEUTRAL_POLICIES = ("abstain", "distribute", "credit_both_exploratory")


def large_size_thresholds(side: np.ndarray, op: np.ndarray, size: np.ndarray, pctl: float = 95.0) -> dict:
    """Umbral de "tamaño grande" por lado: percentil `pctl` de los tamaños de alta/cambio (se excluyen las bajas,
    que no llevan tamaño significativo)."""
    mask = op != 2
    out = {}
    for s in (ASK, BID):
        vals = size[mask & (side == s)]
        out[s] = float(np.percentile(vals, pctl)) if len(vals) else float("inf")
    return out


def _candidate_id(prefix: str, *parts) -> str:
    """Determinista: mismo (prefijo, side, tick, primer timestamp) siempre produce el mismo id."""
    raw = prefix + "|" + "|".join(str(p) for p in parts)
    return prefix + "_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _neutral_targets(policy: str) -> tuple:
    if policy == "abstain":
        return ()
    if policy in ("distribute", "credit_both_exploratory"):
        return (ASK, BID)
    raise ValueError(f"neutral_policy desconocida: {policy!r} (usar una de {NEUTRAL_POLICIES})")


def _neutral_share(policy: str, size: float) -> float:
    """Cuanto de `size` se acredita a CADA lado en `_neutral_targets`. distribute reparte a la mitad; el modo
    exploratorio, que existia antes por default, acredita el total a los dos lados (doble conteo, declarado)."""
    return size / 2.0 if policy == "distribute" else size


@dataclass
class IcebergTracker:
    trade_window_us: float = 2_000_000.0
    refill_window_us: float = 5_000_000.0
    refill_min_ratio: float = 0.7
    min_refills: int = 3
    min_avg_size: dict = field(default_factory=dict)          # {side: minimo}; descarta niveles chicos (rutina)
    near_ticks: float | None = None                          # solo abre vigilancia cerca del touch (ver `depth`)
    neutral_policy: str = "abstain"
    _last_size: dict = field(default_factory=dict)        # (side,tick) -> tamaño vigente
    _last_trade_ts: dict = field(default_factory=dict)     # (side,tick) -> (ts_us, size) del ultimo trade atribuido
    _ambiguous_near: dict = field(default_factory=dict)     # (side,tick) -> volumen neutral reciente sin atribuir
    _pending: dict = field(default_factory=dict)            # (side,tick) -> dict(ts, prev_size, attributed, ambiguous)
    _stats: dict = field(default_factory=dict)              # (side,tick) -> lista de refills observados

    def __post_init__(self):
        if self.neutral_policy not in NEUTRAL_POLICIES:
            raise ValueError(f"neutral_policy desconocida: {self.neutral_policy!r}")

    def on_trade(self, tick: int, ts_us: int, size: float, aggressor: int) -> None:
        if aggressor > 0:
            self._last_trade_ts[(ASK, tick)] = (ts_us, size)
        elif aggressor < 0:
            self._last_trade_ts[(BID, tick)] = (ts_us, size)
        else:
            for side in _neutral_targets(self.neutral_policy):
                self._last_trade_ts[(side, tick)] = (ts_us, _neutral_share(self.neutral_policy, size))
            # el volumen neutral queda registrado como AMBIGUO para los dos lados aunque no se acredite
            # (policy="abstain"): permite auditar cuanto se descarto sin inflar el conteo de refills.
            for side in (ASK, BID):
                self._ambiguous_near[(side, tick)] = (ts_us, self._ambiguous_near.get((side, tick), (0, 0.0))[1] + size)

    def on_l2_event(self, side: int, op: int, tick: int, size: float, ts_us: int, depth: float | None = None) -> None:
        """`depth`: distancia en ticks al mejor precio DE ESE LADO en el momento del evento (0 = toque). Sin ella,
        no se filtra por cercania (compatibilidad hacia atras / tests)."""
        key = (side, tick)
        prev = self._last_size.get(key)
        if op in (0, 1) and prev is not None and size < prev:
            lt = self._last_trade_ts.get(key)
            near = self.near_ticks is None or depth is None or depth <= self.near_ticks
            if lt is not None and near and 0 <= ts_us - lt[0] <= self.trade_window_us:
                amb = self._ambiguous_near.get(key, (0, 0.0))
                ambiguous_vol = amb[1] if amb[0] and 0 <= ts_us - amb[0] <= self.trade_window_us else 0.0
                self._pending[key] = dict(ts=ts_us, prev_size=prev, attributed=lt[1], ambiguous=ambiguous_vol)
        elif op in (0, 1) and size > 0:
            pend = self._pending.get(key)
            if pend is not None and 0 <= ts_us - pend["ts"] <= self.refill_window_us and size >= self.refill_min_ratio * pend["prev_size"]:
                self._stats.setdefault(key, []).append(dict(
                    first_ts=pend["ts"], last_ts=ts_us, visible_size_before=pend["prev_size"],
                    visible_size_after=size, attributed_trade_volume=pend["attributed"],
                    ambiguous_trade_volume=pend["ambiguous"]))
                self._pending.pop(key, None)
        if op == 2:
            self._last_size.pop(key, None)
            self._pending.pop(key, None)     # un delete cierra el ciclo: una reaparicion despues es una orden NUEVA
        else:
            self._last_size[key] = size

    def candidates(self) -> list[dict]:
        out = []
        for (side, tick), refills in self._stats.items():
            avg = sum(r["visible_size_before"] for r in refills) / len(refills)
            if len(refills) >= self.min_refills and avg >= self.min_avg_size.get(side, 0.0):
                out.append(dict(
                    candidate_id=_candidate_id("ICE", side, tick, refills[0]["first_ts"]),
                    side=side, tick=tick,
                    first_observed_ts_us=refills[0]["first_ts"], last_observed_ts_us=refills[-1]["last_ts"],
                    refill_count=len(refills),
                    visible_size_before=refills[-1]["visible_size_before"], visible_size_after=refills[-1]["visible_size_after"],
                    attributed_trade_volume=sum(r["attributed_trade_volume"] for r in refills),
                    ambiguous_trade_volume=sum(r["ambiguous_trade_volume"] for r in refills),
                    avg_size=avg,
                    confidence_components=dict(refill_count=len(refills), min_refills=self.min_refills,
                                               refill_min_ratio=self.refill_min_ratio, avg_size_over_threshold=avg / max(1e-9, self.min_avg_size.get(side, 0.0)) if self.min_avg_size.get(side) else None),
                    provenance="edgelab.research.l2_manipulation_heuristics.IcebergTracker",
                    neutral_policy=self.neutral_policy, status="HEURISTIC_UNVALIDATED"))
        return out


@dataclass
class SpoofTracker:
    thresholds: dict
    max_lifetime_us: float = 5_000_000.0
    max_fill_ratio: float = 0.2
    near_ticks: float | None = None                          # solo abre vigilancia cerca del touch (ver `depth`)
    neutral_policy: str = "abstain"
    _watch: dict = field(default_factory=dict)   # sólo ciclos con nacimiento observado
    _last_size: dict = field(default_factory=dict)
    _out: list = field(default_factory=list)

    def __post_init__(self):
        if self.neutral_policy not in NEUTRAL_POLICIES:
            raise ValueError(f"neutral_policy desconocida: {self.neutral_policy!r}")

    def on_trade(self, tick: int, ts_us: int, size: float, aggressor: int) -> None:
        if aggressor > 0:
            targets, share = (ASK,), size
        elif aggressor < 0:
            targets, share = (BID,), size
        else:
            targets, share = _neutral_targets(self.neutral_policy), _neutral_share(self.neutral_policy, size)
        for side in targets:
            w = self._watch.get((side, tick))
            if w is not None:
                w["attributed"] += share
        if aggressor == 0:                      # ambiguo: se registra en ambos lados aunque no se acredite (abstain)
            for side in (ASK, BID):
                w = self._watch.get((side, tick))
                if w is not None:
                    w["ambiguous"] += size

    def on_l2_event(self, side: int, op: int, tick: int, size: float, ts_us: int, depth: float | None = None) -> None:
        """`depth`: distancia en ticks al mejor precio DE ESE LADO en el momento del evento (0 = toque)."""
        key = (side, tick)
        w = self._watch.get(key); prev = self._last_size.get(key)
        thr = self.thresholds.get(side, float("inf"))
        if op in (0, 1) and size >= thr:
            if w is None:
                reason = "OBSERVED_ADD" if op == 0 else ("THRESHOLD_CROSS" if prev is not None and prev < thr else None)
                near = self.near_ticks is None or depth is None or depth <= self.near_ticks
                if reason and near:
                    self._watch[key] = dict(born_ts=ts_us, peak_size=size, attributed=0.0, ambiguous=0.0,
                                            distance_to_touch=depth, birth_reason=reason)
            else: w["peak_size"] = max(w["peak_size"], size)
        elif w is not None: self._close(key, w, ts_us)
        if op == 2: self._last_size.pop(key, None)
        else: self._last_size[key] = size

    def _close(self, key: tuple, w: dict, ts_us: int) -> None:
        side, tick = key
        lifetime = ts_us - w["born_ts"]
        fill_ratio = (w["attributed"] / w["peak_size"]) if w["peak_size"] else 1.0
        if lifetime <= self.max_lifetime_us and fill_ratio <= self.max_fill_ratio:
            self._out.append(dict(
                candidate_id=_candidate_id("SPOOF", side, tick, w["born_ts"]),
                side=side, tick=tick, born_ts_us=w["born_ts"], death_ts_us=ts_us, lifetime_us=lifetime,
                peak_visible_size=w["peak_size"], attributed_fill=w["attributed"], ambiguous_fill=w["ambiguous"],
                fill_ratio=fill_ratio, distance_to_touch=w["distance_to_touch"],
                threshold_provenance=dict(threshold=self.thresholds.get(side), side=side),
                birth_reason=w["birth_reason"], lifecycle_complete=True,
                provenance="edgelab.research.l2_manipulation_heuristics.SpoofTracker",
                neutral_policy=self.neutral_policy, status="HEURISTIC_UNVALIDATED"))
        self._watch.pop(key, None)

    def candidates(self) -> list[dict]:
        return list(self._out)
