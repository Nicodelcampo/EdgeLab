"""Detectores PROVISIONALES de spoofing e iceberg sobre el libro L2 reconstruido.

**Target-free.** No miran retornos ni P&L: solo la secuencia de eventos del libro (`tools/build_l2_viewer_bundle.py`)
y las ejecuciones del mismo feed. Son heurísticas de trabajo, **NO verificadas contra ground truth** — no existe:
el feed es MBP (Market By Price, por nivel), sin ID de orden, así que "una orden" es una inferencia sobre la serie
de tamaños a un (lado, precio), que puede mezclar varias órdenes reales de distintos participantes. Sirven para
ubicar candidatos que revisar a mano, no para afirmar manipulación.

ICEBERG (candidato). A un (lado, precio) el tamaño baja porque un trade lo consume (hay una ejecución en ese precio
en los `trade_window_s` segundos previos), y en los siguientes `refill_window_s` segundos el tamaño vuelve a un
nivel parecido (`>= refill_min_ratio` del que tenía antes de consumirse). Si eso se repite `min_refills` veces o
más en la sesión, se marca como candidato. El trade que consume se asigna al lado que golpeó según el agresor
clasificado (compra agresiva -> consume el ASK; venta agresiva -> consume el BID; neutral -> se acredita a ambos).

SPOOFING (candidato). Aparece un tamaño grande (percentil `large_size_pctl` del lado, sobre los tamaños no nulos
de la sesión) a un (lado, precio), y desaparece (baja del umbral, o se borra) en menos de `max_lifetime_s`
segundos habiendo sido ejecutado (por trades en ese precio, acreditados igual que en el iceberg) menos del
`max_fill_ratio` de su tamaño pico. Es decir: se fue sin haberse llenado. Solo se emiten vidas COMPLETAS (que
nacieron y murieron dentro de la sesión); una orden grande que sigue viva al cierre no se cuenta.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

ASK, BID = 0, 1


def large_size_thresholds(side: np.ndarray, op: np.ndarray, size: np.ndarray, pctl: float = 95.0) -> dict:
    """Umbral de "tamaño grande" por lado: percentil `pctl` de los tamaños de alta/cambio (se excluyen las bajas,
    que no llevan tamaño significativo)."""
    mask = op != 2
    out = {}
    for s in (ASK, BID):
        vals = size[mask & (side == s)]
        out[s] = float(np.percentile(vals, pctl)) if len(vals) else float("inf")
    return out


@dataclass
class IcebergTracker:
    trade_window_s: float = 2.0
    refill_window_s: float = 5.0
    refill_min_ratio: float = 0.7
    min_refills: int = 3
    min_avg_size: dict = field(default_factory=dict)          # {side: minimo}; descarta niveles chicos (rutina)
    near_ticks: float | None = None                          # solo abre vigilancia cerca del touch (ver `depth`)
    _last_size: dict = field(default_factory=dict)        # (side,tick) -> tamaño vigente
    _last_trade_ts: dict = field(default_factory=dict)     # (side,tick) -> ts del ultimo trade que lo pudo consumir
    _pending: dict = field(default_factory=dict)            # (side,tick) -> (ts_consumo, tamano_previo)
    _stats: dict = field(default_factory=dict)              # (side,tick) -> {refills, first_ts, last_ts, sizes}

    def on_trade(self, tick: int, ts: int, aggressor: int) -> None:
        if aggressor > 0:
            self._last_trade_ts[(ASK, tick)] = ts
        elif aggressor < 0:
            self._last_trade_ts[(BID, tick)] = ts
        else:
            self._last_trade_ts[(ASK, tick)] = ts
            self._last_trade_ts[(BID, tick)] = ts

    def on_l2_event(self, side: int, op: int, tick: int, size: float, ts: int, depth: float | None = None) -> None:
        """`depth`: distancia en ticks al mejor precio DE ESE LADO en el momento del evento (0 = toque). Sin ella,
        no se filtra por cercania (compatibilidad hacia atras / tests)."""
        key = (side, tick)
        prev = self._last_size.get(key)
        if op in (0, 1) and prev is not None and size < prev:
            lt = self._last_trade_ts.get(key)
            near = self.near_ticks is None or depth is None or depth <= self.near_ticks
            if lt is not None and near and 0 <= ts - lt <= self.trade_window_s:
                self._pending[key] = (ts, prev)
        elif op in (0, 1) and size > 0:
            pend = self._pending.get(key)
            if pend is not None:
                consumed_ts, consumed_prev = pend
                if 0 <= ts - consumed_ts <= self.refill_window_s and size >= self.refill_min_ratio * consumed_prev:
                    rec = self._stats.setdefault(key, {"refills": 0, "first_ts": ts, "last_ts": ts, "sizes": []})
                    rec["refills"] += 1
                    rec["last_ts"] = ts
                    rec["sizes"].append(consumed_prev)
                    del self._pending[key]
        if op == 2:
            self._last_size.pop(key, None)
        else:
            self._last_size[key] = size

    def candidates(self) -> list[dict]:
        out = []
        for (side, tick), rec in self._stats.items():
            avg = sum(rec["sizes"]) / len(rec["sizes"])
            if rec["refills"] >= self.min_refills and avg >= self.min_avg_size.get(side, 0.0):
                out.append(dict(side=side, tick=tick, first_ts=rec["first_ts"], last_ts=rec["last_ts"],
                                refills=rec["refills"], avg_size=avg))
        return out


@dataclass
class SpoofTracker:
    thresholds: dict
    max_lifetime_s: float = 20.0
    max_fill_ratio: float = 0.2
    near_ticks: float | None = None                          # solo abre vigilancia cerca del touch (ver `depth`)
    _watch: dict = field(default_factory=dict)   # (side,tick) -> {born_ts, peak_size, filled}
    _out: list = field(default_factory=list)

    def on_trade(self, tick: int, ts: int, size: float, aggressor: int) -> None:
        targets = (ASK,) if aggressor > 0 else (BID,) if aggressor < 0 else (ASK, BID)
        for side in targets:
            w = self._watch.get((side, tick))
            if w is not None:
                w["filled"] += size

    def on_l2_event(self, side: int, op: int, tick: int, size: float, ts: int, depth: float | None = None) -> None:
        """`depth`: distancia en ticks al mejor precio DE ESE LADO en el momento del evento (0 = toque)."""
        key = (side, tick)
        w = self._watch.get(key)
        thr = self.thresholds.get(side, float("inf"))
        if op in (0, 1) and size >= thr:
            if w is None:
                near = self.near_ticks is None or depth is None or depth <= self.near_ticks
                if near:
                    self._watch[key] = {"born_ts": ts, "peak_size": size, "filled": 0.0}
            else:
                w["peak_size"] = max(w["peak_size"], size)
        elif w is not None:                       # cayo por debajo del umbral (op 0/1) o se borro (op 2): cierra
            self._close(key, w, ts)

    def _close(self, key: tuple, w: dict, ts: int) -> None:
        side, tick = key
        lifetime = ts - w["born_ts"]
        fill_ratio = (w["filled"] / w["peak_size"]) if w["peak_size"] else 1.0
        if lifetime <= self.max_lifetime_s and fill_ratio <= self.max_fill_ratio:
            self._out.append(dict(side=side, tick=tick, born_ts=w["born_ts"], death_ts=ts,
                                  peak_size=w["peak_size"], filled_ratio=fill_ratio))
        self._watch.pop(key, None)

    def candidates(self) -> list[dict]:
        return list(self._out)
