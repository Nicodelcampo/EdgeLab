"""CAMP-001 — motor de la campaña de descubrimiento sobre Gaps2.

Implementa literalmente el manifiesto **SEALED v1.1** (`docs/campaigns/
CAMP-001_gaps2_discovery.md`, sha256 del cuerpo `46533c0a…`):

- §5   familias F1–F4 y reglas comunes (1 contrato, una posición simultánea,
       señal en el cierre de `t`, ejecución en el **open de `t+1`**).
- §5.1 fórmulas exactas de dirección y stop (enmienda E2).
- §6   grilla sellada: 4 familias × `zone_min_size{2,3,5}` × `stop_pad{2,4}`
       × `target_R{1,2}` × `time_stop{240}` = **48**.
- E4   `close_at_session_end = True`.
- E6   umbrales y reglas de veredicto (§11).

**Prohibido importar kernels** (§4): las zonas se leen del store.

Toda la geometría se resuelve en **índices ENTEROS de tick** (`lower_tick` /
`upper_tick` del store), nunca comparando `double` — es la lección permanente
del contrato de paridad §5.
"""
from __future__ import annotations

import itertools
import json

import numpy as np

from ..bridge import bars as bars_mod
from ..bridge import sessions
from .costs import get_scenario

# ---- grilla SELLADA (§6). Cambiarla exige enmienda aprobada ANTES de correr --
FAMILIES = ("F1", "F2", "F3", "F4")
ZONE_MIN_SIZE = (2, 3, 5)
STOP_PAD = (2, 4)
TARGET_R = (1, 2)
TIME_STOP_BARS = (240,)
N_EFF = 48

# ---- E6.6: umbrales, sin relajar -------------------------------------------
MIN_TRADES_WINNER = 50        # selección dentro de la familia
MIN_TRADES_G1 = 100           # promoción (edge_validation_contract §G1)

CAMPAIGN_CONFIG_ID = "a6c32c0e9dbeb79a"      # E6.7: identidad única
GAPS2_KERNEL_ID = "771429ccc049bb8e"
MANIFEST_SHA256 = "46533c0a4c6ff69ee0ddcb1435e47595a9b5ff86594c63019d5a6c7347b304be"

# ---- folds con la regla de recorte E3 (§3.1), UTC semiabierto [inicio, fin) --
FOLDS = (
    ("6E_09-25", "6E 09-25", "2025-07-25T20:00:00", "2025-09-15T14:13:50"),
    ("6E_12-25", "6E 12-25", "2025-09-15T14:13:49", "2025-12-15T15:11:58"),
    ("6E_03-26", "6E 03-26", "2025-12-15T15:11:57", "2026-03-16T14:16:01"),
    ("6E_06-26", "6E 06-26", "2026-03-16T14:16:00", "2026-06-15T14:13:13"),
)


def expand_grid():
    """Las 48 hipótesis selladas, en orden determinista."""
    return [dict(config_id="%s-z%d-p%d-R%d-t%d" % (f, z, sp, tr, ts),
                 family=f, zone_min_size=z, stop_pad=sp,
                 target_R=tr, time_stop_bars=ts)
            for f, z, sp, tr, ts in itertools.product(
                FAMILIES, ZONE_MIN_SIZE, STOP_PAD, TARGET_R, TIME_STOP_BARS)]


def signal_key(g):
    """Los disparos dependen SOLO de (familia, zone_min_size) — §6.

    `stop_pad` y `target_R` cambian las salidas, no las señales. Permite
    calcular 12 conjuntos de disparos en vez de 48 (mismo resultado, exacto).
    """
    return (g["family"], g["zone_min_size"])


# --------------------------------------------------------------------------- #
# Steps del simulador: una barra m1 = un step, ejecutable en su OPEN
# --------------------------------------------------------------------------- #
def build_steps(ticks, bars):
    """Steps para `sim.simulate`, uno por barra m1.

    `ts` = timestamp del PRIMER tick de la barra (el momento real del open), no
    el borde del minuto: así un `available_at` puesto en el cierre de `t`
    (`end_ns[t]`) selecciona sin ambigüedad el open de `t+1` con el operador
    estrictamente-mayor del simulador (§6.2 de la spec).

    `bid`/`ask` son el quote REAL de ese primer tick. `low`/`high` son el rango
    completo de la barra, así que el stop/target puede dispararse dentro de la
    misma barra de entrada (spec §6.3, con "gana el adverso" en el ambiguo).
    """
    n = len(bars)
    first = np.searchsorted(bars.tick_bar_idx, np.arange(n), side="left")
    ts = ticks.ts_ns[first]
    tick_size = ticks.tick_size
    has_q = ticks.bid_ticks is not None and ticks.ask_ticks is not None
    op = bars.open_t.astype(np.int64)
    bid = ticks.bid_ticks[first].astype(np.int64) if has_q else op
    ask = ticks.ask_ticks[first].astype(np.int64) if has_q else op + 1
    # Quote degradado (cruzado, vacío o más ancho de lo creíble): se cae al
    # libro de 1 tick alrededor del open. Se CUENTA y se reporta, no se oculta.
    bad = (bid <= 0) | (ask <= 0) | (ask <= bid) | ((ask - bid) > 10)
    if bad.any():
        bid = np.where(bad, op, bid)
        ask = np.where(bad, op + 1, ask)
    skeys = [sessions.session_key(int(s)) for s in bars.start_ns]
    steps = [dict(ts=int(ts[i] // 1_000_000),
                  last=float(op[i]) * tick_size,
                  bid=float(bid[i]) * tick_size,
                  ask=float(ask[i]) * tick_size,
                  low=float(bars.low_t[i]) * tick_size,
                  high=float(bars.high_t[i]) * tick_size,
                  session_id=skeys[i]) for i in range(n)]
    return steps, dict(n_steps=n, n_quotes_degraded=int(bad.sum()),
                       has_quotes=bool(has_q))


# --------------------------------------------------------------------------- #
# Disparos por familia (§5) — como máximo UNA señal por zona y familia
# --------------------------------------------------------------------------- #
def triggers_for_zone(z, bars, i0, i1):
    """Devuelve {familia: (bar_disparo, dir)} para una zona.

    `inside` = el rango [low, high] de la barra entra en la zona (enteros).
    Una época de touch = barras consecutivas adentro (mismo criterio que
    `inside_epoch` del kernel, trasladado a barras).
    """
    lo_t, hi_t = int(z["lower_tick"]), int(z["upper_tick"])
    bull = z["kind"] == "bull_gap"
    hi = bars.high_t
    lo = bars.low_t
    cl = bars.close_t
    out = {}
    inside_prev = False
    epoch = 0
    for i in range(i0, i1):
        inside = (hi[i] >= lo_t) and (lo[i] <= hi_t)
        if inside and not inside_prev:
            epoch += 1
            if epoch == 1 and "F1" not in out:
                out["F1"] = (i, 1 if bull else -1)
            elif epoch == 2 and "F4" not in out:
                out["F4"] = (i, 1 if bull else -1)
            # F3: touch + la barra SIGUIENTE cierra fuera, del lado del rebote
            if "F3" not in out and i + 1 < i1:
                if bull and cl[i + 1] > hi_t:
                    out["F3"] = (i + 1, 1)
                elif (not bull) and cl[i + 1] < lo_t:
                    out["F3"] = (i + 1, -1)
        inside_prev = inside
        # F2: el close atraviesa un borde. La dirección la fija la RUPTURA,
        # no el tipo de zona (§5.1, nota de desambiguación).
        if "F2" not in out:
            if cl[i] > hi_t:
                out["F2"] = (i, 1)
            elif cl[i] < lo_t:
                out["F2"] = (i, -1)
    return out


def stop_tick_for(family, dirn, lo_t, hi_t, pad):
    """§5.1: `stop = borde_ref − dir*pad*tick`, en enteros de tick.

    `borde_ref` = **distal** en fade (F1/F3/F4), **proximal** en ruptura (F2).
    """
    if family == "F2":                      # proximal = el borde atravesado
        ref = hi_t if dirn == 1 else lo_t
    else:                                   # distal = el borde adverso
        ref = lo_t if dirn == 1 else hi_t
    return ref - dirn * pad


def build_signals(zones, bars, steps, family, zone_min_size, stop_pad, target_R,
                  time_stop_bars, tick_size, scenario="base"):
    """Señales ejecutables para UNA celda de la grilla.

    El `stop` sellado es un PRECIO absoluto y el riesgo se mide contra el fill
    de entrada, así que hay que resolver el step de entrada para expresarlo como
    distancia (que es lo que consume el simulador). El step de entrada es
    determinista: el primero con `ts > available_at`. La regla de una posición
    simultánea sólo RECHAZA señales, nunca desplaza la entrada de las aceptadas,
    así que precalcularlo es exacto.
    """
    sc = get_scenario(scenario)
    end_ms = (bars.end_ns // 1_000_000).astype(np.int64)
    step_ts = np.array([s["ts"] for s in steps], dtype=np.int64)
    n = len(bars)
    sigs, skipped = [], {"invalid_stop": 0, "no_entry_step": 0}

    for z in zones:
        if (json.loads(z["features"]).get("size_ticks") or 0) < zone_min_size:
            continue
        c0 = int(z["created_ms"])
        c1 = int(z["ended_ms"]) if z["ended_ms"] is not None else int(end_ms[-1]) + 1
        i0 = int(np.searchsorted(end_ms, c0, "left"))
        i1 = min(int(np.searchsorted(end_ms, c1, "left")), n)
        if i1 <= i0:
            continue
        trig = triggers_for_zone(z, bars, i0, i1)
        if family not in trig:
            continue
        bar_t, dirn = trig[family]
        available_at = int(end_ms[bar_t])

        # step de entrada = primer step con ts ESTRICTAMENTE > available_at
        e = int(np.searchsorted(step_ts, available_at, side="right"))
        if e >= len(steps):
            skipped["no_entry_step"] += 1
            continue
        book = steps[e]["ask"] if dirn == 1 else steps[e]["bid"]
        entry_fill = round(book / tick_size) + dirn * sc.slip_entry

        stop_t = stop_tick_for(family, dirn, int(z["lower_tick"]),
                               int(z["upper_tick"]), stop_pad)
        stop_ticks = int(dirn * (entry_fill - stop_t))
        if stop_ticks <= 0:
            # El precio ya abrió más allá del stop: no existe trade con ese
            # stop. No es una decisión discrecional — es imposible ejecutarlo.
            skipped["invalid_stop"] += 1
            continue

        sigs.append(dict(
            signal_id="%s|%s|%d" % (z["zone_id"], family, bar_t),
            available_at=available_at, dir=dirn,
            stop_ticks=stop_ticks, target_ticks=int(target_R * stop_ticks),
            time_stop_ms=int(time_stop_bars) * 60_000,
            zone_id=z["zone_id"], trigger_bar=int(bar_t)))
    sigs.sort(key=lambda s: (s["available_at"], s["signal_id"]))
    return sigs, skipped


def cost_round_turn(scenario="base", tick_value=6.25):
    """Fricción round-turn EXACTA del escenario, resuelta (no aproximada)."""
    sc = get_scenario(scenario)
    slip_ticks = sc.slip_entry + sc.slip_exit          # 2 patas
    com_usd = 2 * sc.commission_per_side_usd
    usd = slip_ticks * tick_value + com_usd
    return dict(scenario=sc.name, slippage_ticks=float(slip_ticks),
                commission_usd=float(com_usd), total_usd=float(usd),
                total_ticks=float(usd / tick_value), tick_value_usd=tick_value)
