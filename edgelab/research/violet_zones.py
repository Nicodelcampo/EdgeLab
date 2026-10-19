"""Lógica de las zonas VIOLETA de nt8/aVolClusterPOI_violet_v05.cs (líneas 686-775, 701-775 y el ciclo por barra de OnBarUpdate), portada a Python y aplicada a ZONAS CUALQUIERA
(en particular las de `edgelab.bridge.indicators.avolzonepoi2`, con paridad NT8 verificada). Una zona es violeta si el precio SE ALEJÓ RÁPIDO Y LEJOS de ella con POCO volumen operado adentro:
  - dirección = signo del cierre de la barra de creación respecto de la zona (+1 por encima, −1 por debajo; 0 = adentro → no aplica, como AT_PRICE);
  - alejamiento = máxima separación (ticks) respecto del borde lejano de su lado ≥ max(min_away_ticks, ceil(away_width_mult × ancho)) dentro de `quick_bars` barras desde la creación;
  - poco volumen = (volumen operado DENTRO de la zona desde su creación hasta ese momento) / score ≤ umbral ADAPTATIVO y CAUSAL: cuantil q de los ratios de las zonas ya alejadas, con
    q = (target_pct/100) / (zonas alejadas / zonas resueltas) acotado a [0,02; 1]; con menos de 20 alejadas o 20 resueltas se usa `warmup_max_ratio`;
  - la decisión se fija una vez; una zona invalidada (cierre de barra del lado equivocado: CloseThrough) o que no se alejó a tiempo queda no violeta.
Orden por barra (idéntico al .cs): acumular volumen de la barra → evaluar alejamiento → ciclo de vida (invalidación) → las zonas creadas en la barra recién entran en la siguiente."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DEFAULTS = dict(min_away_ticks=40, away_width_mult=2.0, quick_bars=30, target_pct=20.0, warmup_max_ratio=0.35)


@dataclass
class Violet:
    direction: np.ndarray      # +1 / −1 / 0 por zona
    decided: np.ndarray        # bool
    departed: np.ndarray       # bool: se alejó a tiempo
    purple: np.ndarray         # bool
    decision_bar: np.ndarray   # barra de la decisión (−1 si ninguna)
    ratio: np.ndarray          # traded/score al alejarse (NaN si no se alejó)
    traded: np.ndarray


def zone_directions(zones, close_t) -> np.ndarray:
    return np.array([1 if close_t[z["bar"]] > z["high_tick"] else (-1 if close_t[z["bar"]] < z["low_tick"] else 0) for z in zones], dtype=np.int8)


def violet(zones: list, bars, fps, params: dict | None = None) -> Violet:
    p = {**DEFAULTS, **(params or {})}
    nz = len(zones); hi, lo, cl = (np.asarray(x, dtype=np.int64) for x in (bars.high_t, bars.low_t, bars.close_t)); n = len(cl)
    direction = zone_directions(zones, cl); cbar = np.array([z["bar"] for z in zones], dtype=np.int64); order = np.argsort(cbar, kind="stable")
    L = np.array([z["low_tick"] for z in zones], dtype=np.int64); U = np.array([z["high_tick"] for z in zones], dtype=np.int64); score = np.array([float(z["score"]) for z in zones])
    traded = np.zeros(nz); maxaway = np.zeros(nz, dtype=np.int64); decided = np.zeros(nz, bool); departed = np.zeros(nz, bool); purple = np.zeros(nz, bool)
    dbar = np.full(nz, -1, dtype=np.int64); ratio_z = np.full(nz, np.nan)
    ratios: list = []; resolved = 0; ndeparted = 0
    off, ft, fv = fps.offsets, fps.ticks, fps.vols

    def threshold():
        if len(ratios) < 20 or resolved < 20: return p["warmup_max_ratio"]
        share = ndeparted / max(1, resolved); q = (p["target_pct"] / 100.0) / share if share > 0 else 1.0
        q = min(1.0, max(0.02, q)); s = sorted(ratios); k = min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1)); return s[k]

    def decide(i, is_purple, b):
        nonlocal resolved
        decided[i] = True; purple[i] = is_purple; dbar[i] = b; resolved += 1

    live: list = []; ptr = 0; b = int(cbar[order[0]]) + 1 if nz else n
    while b < n:
        while ptr < nz and cbar[order[ptr]] < b:                       # elegibles: creadas en barras ANTERIORES
            i = int(order[ptr]); ptr += 1
            if direction[i] != 0: live.append(i)
        if not live:
            if ptr >= nz: break
            b = int(cbar[order[ptr]]) + 1; continue
        t, v = ft[off[b]:off[b + 1]], fv[off[b]:off[b + 1]]
        for i in live: traded[i] += float(v[(t >= L[i]) & (t <= U[i])].sum())             # 1) volumen operado dentro
        for i in live:                                                                      # 2) alejamiento
            if decided[i]: continue
            away = int(hi[b] - U[i]) if direction[i] > 0 else int(L[i] - lo[b]); maxaway[i] = max(maxaway[i], away); age = b - int(cbar[i])
            need = max(p["min_away_ticks"], math.ceil(p["away_width_mult"] * int(U[i] - L[i] + 1)))
            if maxaway[i] >= need and age <= p["quick_bars"]:
                r = traded[i] / max(1.0, score[i]); is_p = r <= threshold(); ratios.append(r)
                if len(ratios) > 1000: ratios.pop(0)
                ndeparted += 1; departed[i] = True; ratio_z[i] = r; decide(i, bool(is_p), b)
            elif age >= p["quick_bars"]:
                decide(i, False, b)
        for i in live:                                                                      # 3) invalidación CloseThrough
            if decided[i]: continue
            if (direction[i] > 0 and cl[b] < L[i]) or (direction[i] < 0 and cl[b] > U[i]): decide(i, False, b)
        live = [i for i in live if not decided[i]]
        b += 1
    return Violet(direction=direction, decided=decided, departed=departed, purple=purple, decision_bar=dbar, ratio=ratio_z, traded=traded)


# ----------------------------------------------------------------------------------------------------------------------------------------------------
# Eventos: «el precio, después de alejarse, vuelve a una distancia D de la zona»; resultado a nivel de TICK con barreras (TP hacia la zona a ticks, SL alejándose b ticks)
# ----------------------------------------------------------------------------------------------------------------------------------------------------
def death_bar(zone, direction, cl, start, end):
    """Primera barra en [start, end) con cierre del lado equivocado (CloseThrough); `end` si no hay."""
    seg = cl[start:end]
    bad = np.flatnonzero(seg < zone["low_tick"]) if direction > 0 else np.flatnonzero(seg > zone["high_tick"])
    return start + int(bad[0]) if len(bad) else end


def zone_events(zone, direction, dec_bar, price_t, bar_start_tick, bar_end_by_session, cl, Ds, configs):
    """Devuelve filas (D, a, b, resultado, pnl_ticks, ticks_hasta_la_entrada) para una zona ya alejada. dist = ticks de separación desde el borde cercano (>0 = afuera). `configs(D)` → [(a, b)]."""
    n = len(cl); end_bar = int(bar_end_by_session[dec_bar]); end_bar = min(end_bar, n - 1)
    dth = death_bar(zone, direction, cl, dec_bar + 1, end_bar + 1)                          # ventana: hasta la invalidación o el fin de sesión
    t0, t1 = int(bar_start_tick[dec_bar + 1]), int(bar_start_tick[min(dth, n - 1) + 1] if dth <= end_bar else bar_start_tick[end_bar + 1])
    if t1 - t0 < 2: return []
    px = price_t[t0 - 1:t1]                                                                 # incluye el último tick de la barra de decisión
    dist = (px - zone["high_tick"]) if direction > 0 else (zone["low_tick"] - px)
    rows = []
    for D in Ds:
        far = np.flatnonzero(dist > D)                                                      # «se alejó»: DESPUÉS de la decisión el precio está más allá de D
        if not len(far): continue
        hit = np.flatnonzero(dist[far[0] + 1:] <= D)                                        # y luego vuelve a D (entrada con orden límite en D)
        if not len(hit): continue
        j = int(far[0] + 1 + hit[0]); sub = dist[j + 1:]
        if len(sub) == 0: continue
        dmin = np.minimum.accumulate(sub); dmax = np.maximum.accumulate(sub)
        for a, bb in configs(D):
            tp = int(np.searchsorted(-dmin, -(D - a), side="left")); sl = int(np.searchsorted(dmax, D + bb, side="left"))   # primer índice con dist ≤ D−a / ≥ D+b
            if tp == len(sub) and sl == len(sub): rows.append((D, a, bb, 0, float(D - sub[-1]), j)); continue                  # sin barrera: salida al fin de la ventana
            rows.append((D, a, bb, 1, float(a), j) if tp < sl else (D, a, bb, -1, float(-bb), j))                             # empate en el mismo tick imposible (un tick no está en ambos lados)
    return rows
