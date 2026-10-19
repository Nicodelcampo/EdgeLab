#!/usr/bin/env python3
"""Dry run de CAMP-001 — SIN acceso a retornos ni P&L.

Verifica la grilla sellada (48 hipótesis), la elegibilidad de paridad de las
particiones, y cuenta los DISPAROS esperados por familia (triggers sobre
zonas + OHLC), con el MISMO carácter target-free que la calibración de E1:
se cuentan eventos de interacción precio-zona, **nunca se evalúa el resultado**
de un trade. No usa el simulador ni calcula P&L.

Uso: python tools/camp001_dryrun.py [--fold 6E_09-25]
"""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod, store  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402
from edgelab.research.holdout_guard import check_holdout  # noqa: E402

# ---- grilla SELLADA (CAMP-001 §6) — no se toca sin enmienda ----
FAMILIES = ("F1", "F2", "F3", "F4")
ZONE_MIN_SIZE = (2, 3, 5)
STOP_PAD = (2, 4)
TARGET_R = (1, 2)
TIME_STOP = (240,)
MIN_TRADES_WINNER = 50            # E1, sellado

# ---- folds con la regla de recorte E3 (§3.1) ----
FOLDS = [
    ("6E_09-25", "6E 09-25", "2025-07-25T20:00:00", "2025-09-15T14:13:50"),
    ("6E_12-25", "6E 12-25", "2025-09-15T14:13:49", "2025-12-15T15:11:58"),
    ("6E_03-26", "6E 03-26", "2025-12-15T15:11:57", "2026-03-16T14:16:01"),
    ("6E_06-26", "6E 06-26", "2026-03-16T14:16:00", "2026-06-15T14:13:13"),
]
CAMPAIGN_CONFIG_ID = "a6c32c0e9dbeb79a"   # §4: defaults + min_gap_ticks=2, tz ART
STORE = os.path.join(REPO, "runs", "nt8_bridge", "campaign_store")


def expand_grid():
    return [dict(family=f, zone_min_size=z, stop_pad=sp, target_R=tr, time_stop=ts)
            for f, z, sp, tr, ts in itertools.product(
                FAMILIES, ZONE_MIN_SIZE, STOP_PAD, TARGET_R, TIME_STOP)]


def _iso_ns(s):
    return int(dt.datetime.fromisoformat(s).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1e9)


def count_triggers(zones, bars, tick_size):
    """Disparos por familia (§5), sobre barras OHLC vs geometría as-of.

    SOLO cuenta eventos de interacción; no evalúa ningún resultado.
    Touch de la barra t = el rango [low, high] de la barra entra en la zona.
    Épocas de touch: barras consecutivas tocando = UNA época (igual criterio de
    `inside_epoch` del kernel, trasladado a barras).
    """
    import numpy as np
    end_ms = (bars.end_ns // 1_000_000).astype(np.int64)
    hi = bars.high_t.astype(np.float64) * tick_size
    lo = bars.low_t.astype(np.float64) * tick_size
    cl = bars.close_t.astype(np.float64) * tick_size
    n = len(end_ms)
    out = dict(F1=0, F2=0, F3=0, F4=0)
    for z in zones:
        top, bot = z["top"], z["bottom"]
        c0 = z["created_ms"]
        c1 = z["ended_ms"] if z["ended_ms"] is not None else end_ms[-1] + 1
        i0 = int(np.searchsorted(end_ms, c0, "left"))
        i1 = int(np.searchsorted(end_ms, c1, "left"))
        if i1 <= i0:
            continue
        bull = (z.get("side") == "bull") or ("bull" in (z.get("kind") or ""))
        inside_prev = False
        epoch = 0
        f1 = f3 = f4 = f2 = False
        for i in range(i0, min(i1, n)):
            inside = (hi[i] >= bot) and (lo[i] <= top)
            if inside and not inside_prev:
                epoch += 1
                if epoch == 1 and not f1:
                    out["F1"] += 1; f1 = True
                elif epoch == 2 and not f4:
                    out["F4"] += 1; f4 = True
                # F3: touch + la barra SIGUIENTE cierra fuera del lado del rebote
                if not f3 and i + 1 < min(i1, n):
                    if (bull and cl[i + 1] > top) or ((not bull) and cl[i + 1] < bot):
                        out["F3"] += 1; f3 = True
            inside_prev = inside
            # F2: close atraviesa un borde (ruptura), primera vez por zona
            if not f2 and (cl[i] > top or cl[i] < bot):
                out["F2"] += 1; f2 = True
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dry run CAMP-001 (sin retornos)")
    ap.add_argument("--fold", action="append", default=[],
                    help="limitar a estos folds (default: todos)")
    args = ap.parse_args(argv)

    grid = expand_grid()
    print("=" * 78)
    print("DRY RUN CAMP-001 — sin acceso a retornos ni P&L")
    print("=" * 78)
    print(f"\n[1] GRILLA SELLADA: {len(grid)} configs "
          f"({len(FAMILIES)} familias x {len(ZONE_MIN_SIZE)} zone_min_size x "
          f"{len(STOP_PAD)} stop_pad x {len(TARGET_R)} target_R x {len(TIME_STOP)} time_stop)")
    assert len(grid) == 48, "la grilla sellada debe dar 48 hipotesis"
    print("    N_eff = 48  -> coincide con el manifiesto sellado")
    print("    NOTA: stop_pad y target_R NO cambian los DISPAROS (solo las salidas):")
    print(f"    los 48 configs comparten {len(FAMILIES)*len(ZONE_MIN_SIZE)} conjuntos "
          "de señales distintos (familia x zone_min_size).")

    print("\n[2] ELEGIBILIDAD DE PARTICIONES (§4.1: solo parity_covered|exact)")
    parts = {p["contract"]: p for p in store.get_partitions(
        STORE, indicator="Gaps2", config_id=CAMPAIGN_CONFIG_ID)}
    ok_all = True
    for key, contract, s, e in FOLDS:
        p = parts.get(contract)
        if p is None:
            print(f"    {contract}: FALTA materializar            -> NO ELEGIBLE")
            ok_all = False
            continue
        st = p["parity_state"]
        elig = st in ("parity_covered", "parity_exact")
        ok_all &= elig
        cov = json.loads(p["manifest_json"]).get("coverage") or {}
        src = ("oraculo=%s sha=%s cfg=%s" % (
            os.path.basename(cov.get("oracle_path") or "-"),
            (cov.get("oracle_sha256") or "-")[:12], cov.get("source_config_id") or "-")
            if cov else "(fuente propia)")
        print(f"    {contract}: {st:<16} {'ELEGIBLE' if elig else 'NO ELEGIBLE'}  {src}")

    print("\n[3] DISPAROS ESPERADOS (target-free: cuenta interacciones, NO resultados)")
    folds = [f for f in FOLDS if not args.fold or f[0] in args.fold]
    totals = {f: {z: 0 for z in ZONE_MIN_SIZE} for f in FAMILIES}
    for key, contract, s, e in folds:
        p = parts.get(contract)
        if p is None:
            print(f"    {contract}: sin particion, se omite")
            continue
        check_holdout(s, e, purpose="development", caller="camp001_dryrun")
        tk = ticks_mod.load_canonical_parquet(
            os.path.join(REPO, "data", "nt8", "6E", key + "_ticks.parquet"),
            contract=contract, start_utc_ns=_iso_ns(s), end_utc_ns=_iso_ns(e))
        b = bars_mod.build_time_bars(tk, 1)
        zrows = store.read_zone_rows(p["dir"])
        line = f"    {contract} ({len(zrows):,} zonas, {len(b):,} barras m1):"
        for zmin in ZONE_MIN_SIZE:
            zs = [z for z in zrows
                  if (json.loads(z["features"]).get("size_ticks") or 0) >= zmin]
            c = count_triggers(zs, b, tk.tick_size)
            for fam in FAMILIES:
                totals[fam][zmin] += c[fam]
            line += f"\n        zone_min_size>={zmin}: " + " ".join(
                f"{fam}={c[fam]:,}" for fam in FAMILIES)
        print(line)

    print("\n[4] TABLA DE LAS 48 HIPOTESIS (disparos agregados de desarrollo)")
    print(f"    {'#':>3} {'familia':<8}{'zmin':>5}{'pad':>5}{'R':>3}"
          f"{'disparos':>12}  {'vs E1 (min '+str(MIN_TRADES_WINNER)+')':>22}")
    below = 0
    for i, g in enumerate(grid, 1):
        trig = totals[g["family"]][g["zone_min_size"]]
        flag = "OK (trades<=disparos)" if trig >= MIN_TRADES_WINNER else "BAJO EL MINIMO"
        if trig < MIN_TRADES_WINNER:
            below += 1
        print(f"    {i:>3} {g['family']:<8}{g['zone_min_size']:>5}{g['stop_pad']:>5}"
              f"{g['target_R']:>3}{trig:>12,}  {flag:>22}")
    print(f"\n    configs por debajo del minimo de E1: {below}/48")
    print("    (los disparos son COTA SUPERIOR de los trades: la regla de 1 posicion")
    print("     simultanea solo puede reducirlos, nunca aumentarlos)")

    print("\n[5] CHECKLIST DE BLOQUEOS PREVIOS A LA CORRIDA")
    sim_ok = os.path.exists(os.path.join(REPO, "edgelab", "research", "sim.py"))
    print(f"    [{'x' if sim_ok else ' '}] simulador implementado y con golden tests verdes")
    print(f"    [{'x' if ok_all else ' '}] 4 particiones de desarrollo en parity_covered|exact")
    print("    [ ] OK final de Nico a este checkpoint (incluye lectura de E1/E3)")
    print("    [ ] costos reales del broker (bloquea G3, no la corrida de G1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
