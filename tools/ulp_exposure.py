#!/usr/bin/env python3
"""AUDIT-002 — exposición MEDIDA a la familia de bugs de 1 ULP.

Por qué existe: `AUDIT-001` se hizo **leyendo código** y falló. Marcó como riesgo
NULO las comparaciones de borde de zona de HFTZones2 razonando que "ambos
operandos son precios de grilla construidos igual en los dos lados" — y esa
resultó ser la causa raíz de sus 82 `FEATURE_DIFF`. Leer código tiene ese modo de
falla; **medir no lo tiene**.

Qué mide: NT8 construye los precios desde el `double` que manda el feed (un
decimal parseado) y el kernel Python desde `price_ticks × tick_size`. Los dos
representan el mismo precio pero **no son el mismo `double`**. Este script cuenta,
sobre el rango real del instrumento, cuántas decisiones de umbral **cambian de
lado** según cuál de las dos representaciones se use.

Una decisión está EXPUESTA si el umbral puede coincidir **exactamente** con un
precio negociable. Si el borde vive a medio tick de la grilla, el empate es
imposible y la exposición es cero por construcción.

Uso:  python tools/ulp_exposure.py [--tick-size 5e-05] [--lo 20000] [--hi 25000]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def feed(x_ticks, ts, decimals):
    """El `double` que ve NT8: el precio decimal del feed, parseado."""
    return float(("%." + str(decimals) + "f") % (x_ticks * ts))


def _to_tick(price, ts):
    """Espejo de PriceToTick / snap_to_tick: round AwayFromZero, nunca floor."""
    import math
    x = price / ts
    return int(math.floor(x + 0.5)) if x >= 0 else int(math.ceil(x - 0.5))


def recon(x_ticks, ts):
    """El `double` que ve el kernel Python: price_ticks * tick_size."""
    return x_ticks * ts


# --- umbrales declarados por kernel -----------------------------------------
# CADA umbral se modela con la MISMA secuencia de operaciones en coma flotante
# que ejecuta el kernel. No alcanza con el offset neto: `(x - ts) - ts` y
# `x - 2*ts` son distintos en double, y modelarlo mal fue el primer error de
# esta herramienta (dio 0% donde los datos reales muestran 9%).
#
#   thr(edge, ts)  -> construye el umbral desde el precio del borde
#   offset_ticks   -> dónde cae el precio que empata (para saber si es alcanzable)
KERNELS = {
    "Gaps2": [
        # top/bottom son precios negociados: comparación directa, sin aritmética
        ("inside (bottom < price)", 0, "gt", lambda e, ts: e),
        ("back (price >= top)", 0, "ge", lambda e, ts: e),
        # gaps2.py:158 -> `g["bottom"] - rct * tick_size`, UNA resta con rct=2
        # (reversal_confirm_ticks=2 es el default Y el valor del config de CAMP-001).
        # Solo se evalua con state==FULLFILLED, que exige rct != 0.
        ("inverse (price <= bottom - 2*ts)", -2, "le", lambda e, ts: e - 2 * ts),
        ("inverse (price >= top + 2*ts)", 2, "ge", lambda e, ts: e + 2 * ts),
    ],
    # v2.2: bordes y umbral en ENTEROS de tick. El "umbral" ya no se construye
    # con aritmetica de double, asi que se modela con la reconstruccion exacta
    # desde la grilla: es lo que hace `PriceToTick`/`snap_to_tick` en los dos
    # lados. La exposicion cae a 0 por construccion, no por suerte.
    # DOMINIO ENTERO ("tick"): la comparacion NO se hace entre precios sino entre
    # indices de tick, en los dos lados. La exposicion es 0 si -y solo si- las dos
    # representaciones colapsan al MISMO entero; eso se VERIFICA aca, no se asume.
    "HFTZones2 (v2.3, ciclo de vida COMPLETO en enteros)": [
        ("inside (priceTick >= lowerTick)", -1, "ge", "tick"),
        ("inside (priceTick <= upperTick)", 0, "le", "tick"),
        ("close_through (priceTick <= lowerTick - pen)", -2, "le", "tick"),
        ("close_through (priceTick >= upperTick + pen)", 1, "ge", "tick"),
    ],
    "HFTZones2 (v2.1, ANTES del fix — referencia historica)": [
        ("inside (price >= lower)", -1, "ge", lambda e, ts: e - 1 * ts),
        ("inside (price <= upper)", 0, "le", lambda e, ts: e),
        ("close_through (price <= lower - pen*ts)", -2, "le",
         lambda e, ts: (e - 1 * ts) - 1 * ts),
        ("close_through (price >= upper + pen*ts)", 1, "ge", lambda e, ts: e + 1 * ts),
    ],
    "BigTrap2": [
        ("touch (hi >= zone_lo)", None, "ge", lambda e, ts: e - ts / 2.0),
        ("touch (lo <= zone_hi)", None, "le", lambda e, ts: e + ts / 2.0),
        ("adverse_close (close > zone_hi)", None, "gt", lambda e, ts: e + ts / 2.0),
    ],
    "VolTicksPOC2 (price_mark_ticks=1, default)": [
        ("close > upper", None, "gt", lambda e, ts: e + 1 * ts / 2.0),
        ("close < lower", None, "lt", lambda e, ts: e - 1 * ts / 2.0),
    ],
    "VolTicksPOC2 (price_mark_ticks=2, PAR)": [
        ("close > upper", 1, "gt", lambda e, ts: e + 2 * ts / 2.0),
        ("close < lower", -1, "lt", lambda e, ts: e - 2 * ts / 2.0),
    ],
    "aVolCellPOI2": [
        ("touch (hi >= lower)", None, "ge", lambda e, ts: (e / ts - 0.5) * ts),
        ("close > upper", None, "gt", lambda e, ts: (e / ts + 0.5) * ts),
    ],
    # Probe de captura: clasifica el agresor comparando el precio negociado
    # contra bid/ask del snapshot. El umbral ES un precio de grilla llevado SIN
    # aritmetica, y el empate (trade exactamente al ask) no es un caso raro sino
    # el caso NORMAL de un buy agresivo -> offset_ticks=0, no None. Por eso se
    # mide en vez de declararlo inmune: es el escenario decisivo, no uno de borde.
    "CaptureEventProbeV2 (clasificacion de agresor)": [
        ("aggressor buy (price >= ask)", 0, "ge", lambda e, ts: e),
        ("aggressor sell (price <= bid)", 0, "le", lambda e, ts: e),
    ],
}

OPS = {"gt": lambda a, b: a > b, "lt": lambda a, b: a < b,
       "ge": lambda a, b: a >= b, "le": lambda a, b: a <= b}


def exposure(offset_ticks, op, thr, ts, lo, hi, decimals):
    """% de niveles donde la decisión CAMBIA entre representación feed y recon.

    Se evalúa en el caso decisivo: el precio cae **exactamente** sobre el umbral.
    `offset_ticks=None` ⇒ el umbral vive a medio tick y ningún precio negociable
    puede caer ahí: exposición 0 por construcción.
    """
    if offset_ticks is None:
        return None, 0, 0
    k = int(offset_ticks)
    f = OPS[op]
    flips = total = 0
    for edge in range(lo, hi + 1):
        p = edge + k                 # precio exactamente sobre el umbral
        if p < lo:
            continue
        total += 1
        if thr == "tick":
            # v2.2: los dos lados convierten a entero ANTES de comparar. Se
            # verifica que feed y reconstruido colapsen al mismo indice.
            d_py = f(_to_tick(recon(p, ts), ts), edge + k)
            d_nt = f(_to_tick(feed(p, ts, decimals), ts), edge + k)
        else:
            d_py = f(recon(p, ts), thr(recon(edge, ts), ts))
            d_nt = f(feed(p, ts, decimals), thr(feed(edge, ts, decimals), ts))
        if d_py != d_nt:
            flips += 1
    return (100.0 * flips / total if total else 0.0), flips, total


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exposición medida a la familia ULP")
    ap.add_argument("--tick-size", type=float, default=5e-05)
    ap.add_argument("--decimals", type=int, default=5, help="decimales del feed")
    ap.add_argument("--lo", type=int, default=20000)
    ap.add_argument("--hi", type=int, default=25000)
    ap.add_argument("--out", default=os.path.join(
        REPO, "runs", "nt8_bridge", "audit002_ulp_exposure.json"))
    a = ap.parse_args(argv)

    print("=" * 84)
    print("AUDIT-002 — exposicion MEDIDA a la familia de 1 ULP")
    print("=" * 84)
    print("instrumento: tick=%g, %d decimales, niveles %d..%d (%d precios)"
          % (a.tick_size, a.decimals, a.lo, a.hi, a.hi - a.lo + 1))
    print("\nmetodo: se evalua cada umbral en el caso decisivo (precio EXACTAMENTE")
    print("sobre el umbral) con las dos representaciones y se cuenta cuantas veces")
    print("la decision cambia de lado.\n")

    res = {}
    for kernel, thresholds in KERNELS.items():
        print("-" * 84)
        print(kernel)
        rows = []
        for name, off, op, thr in thresholds:
            pct, flips, total = exposure(off, op, thr, a.tick_size, a.lo, a.hi,
                                         a.decimals)
            if pct is None:
                print("    %-42s  borde a MEDIO TICK -> empate imposible, 0%%" % name)
                rows.append(dict(threshold=name, op=op, exposure_pct=0.0,
                                 reason="medio tick: el precio nunca cae en el umbral"))
            else:
                flag = "  <== EXPUESTO" if flips else ""
                print("    %-42s  %6.2f%%  (%d de %d niveles)%s"
                      % (name, pct, flips, total, flag))
                rows.append(dict(threshold=name, op=op, offset_ticks=off,
                                 exposure_pct=round(pct, 3), flips=flips,
                                 levels=total))
        res[kernel] = rows

    print("-" * 84)
    print("\nRESUMEN — kernels con al menos un umbral expuesto:")
    for k, rows in res.items():
        exp = [r for r in rows if r.get("flips")]
        if exp:
            peor = max(exp, key=lambda r: r["exposure_pct"])
            print("   %-44s max %.2f%%  (%s)" % (k, peor["exposure_pct"],
                                                 peor["threshold"]))
    limpios = [k for k, rows in res.items() if not any(r.get("flips") for r in rows)]
    print("\nkernels SIN exposicion (borde a medio tick por construccion):")
    for k in limpios:
        print("   %s" % k)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nartefacto: %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
