"""HARNESS — punto de entrada UNICO para auditar una estrategia tick.

Objetivo de diseño: que el LLM (o humano) que propone una estrategia tenga
responsabilidad MINIMA. Solo implementa la funcion de señal (contrato en
CONTRATO_LLM.md); el harness hace TODO lo demas con codigo compartido ya
verificado, y emite veredictos mecanicos PASS/FAIL con diagnostico exacto:

  ETAPA A — PREFLIGHT anti-bugs (mecanico, sin juicio):
    A1 synthetic : escenarios artificiales con desenlace conocido (signos).
    A2 mirror    : precios espejados -> longs/shorts y |PnL| deben espejarse.
    A3 prefix    : correr sobre un prefijo no cambia los trades del prefijo
                   (anti-lookahead).
    A4 ledger    : re-derivacion independiente de cada trade del combo
                   headline (aritmetica exacta + no-anticipacion de exits).
  ETAPA B — GAUNTLET estadistico (solo si A paso):
    grid de tp/sl con motor compartido, DSR con haircut por multiplicidad,
    PBO/CSCV sobre el grid, null de ANTI-direccion automatico, IS/OOS 70/30,
    corte mensual.

Uso programatico:
    from validation.harness import full_audit
    full_audit(name, signal_fn, times_ms, last, bid, ask,
               tp_grid, sl_grid, headline=(tp, sl))
signal_fn(times_ms, last, bid, ask) -> (idx_decision int64[], dir int64[])
"""
import numpy as np
import pandas as pd

from edgelab.engine import run_ledger, run_grid, FEES_RT
from edgelab.audit import deflated_sharpe, sr0_haircut
from validation.verify import synthetic_check, mirror_check, prefix_check, verify_ledger
from validation.pbo import pbo_cscv
from validation.gauntlet import report


def _adapter(signal_fn, tp, sl, max_hold_ms, tick, fees):
    def run_trades(times_ms, last, bid, ask):
        idx, dirs = signal_fn(times_ms, last, bid, ask)
        return run_ledger(idx, dirs, times_ms, last, bid, ask, tp, sl,
                          max_hold_ms=max_hold_ms, tick=tick, fees=fees)
    return run_trades


def full_audit(name, signal_fn, times_ms, last, bid, ask, tp_grid, sl_grid,
               headline, max_hold_ms=300_000, tick=0.25, fees=FEES_RT,
               tv=12.5, symmetric=True):
    tp_h, sl_h = headline
    rt = _adapter(signal_fn, tp_h, sl_h, max_hold_ms, tick, fees)

    # ---------- ETAPA A: preflight mecanico ----------
    print(f"\n{'#'*74}\n# AUDIT {name} — headline tp{tp_h}/sl{sl_h}, fees {fees}t RT\n{'#'*74}")
    print("\nETAPA A — PREFLIGHT anti-bugs")
    okA1, _ = synthetic_check(rt, tick=tick, cost=fees)
    if symmetric:
        okA2, _ = mirror_check(rt, times_ms, last, bid, ask)
    else:
        okA2 = True
        print("  [mirror_check] SKIP (estrategia declarada asimetrica)")
    okA3, _ = prefix_check(rt, times_ms, last, bid, ask)
    ledger = rt(times_ms, last, bid, ask)
    okA4, _ = verify_ledger(ledger, times_ms, last, tick=tick, cost=fees)
    if not (okA1 and okA2 and okA3 and okA4):
        print("\n=> PREFLIGHT RECHAZADO. El gauntlet NO corre (GIGO). "
              "Arreglar la falla señalada arriba; no interpretar nada mas.")
        return {"preflight": False}
    print("=> PREFLIGHT APROBADO (4/4)")

    # ---------- ETAPA B: gauntlet ----------
    idx, dirs = signal_fn(times_ms, last, bid, ask)
    print(f"\nETAPA B — GAUNTLET | señales: {len(idx)} "
          f"(L {int((dirs==1).sum())} / S {int((dirs==-1).sum())})")
    grid = run_grid(idx, dirs, times_ms, last, bid, ask, tp_grid, sl_grid,
                    max_hold_ms=max_hold_ms, tick=tick, fees=fees)
    sig_t = times_ms[np.clip(np.asarray(idx) + 1, 0, len(times_ms) - 1)]

    # tabla del grid + DSR con haircut por multiplicidad
    rows = []
    for a, tp in enumerate(tp_grid):
        for s, sl in enumerate(sl_grid):
            v = grid[:, a, s]; x = v[~np.isnan(v)]
            if len(x) < 50 or x.std() <= 0:
                continue
            mean, sd = x.mean(), x.std()
            rows.append({"tp": tp, "sl": sl, "n": len(x), "exp": mean,
                         "sharpe": mean / sd,
                         "skew": float(((x-mean)**3).mean()/sd**3),
                         "kurt": float(((x-mean)**4).mean()/sd**4)})
    gdf = pd.DataFrame(rows)
    if len(gdf) > 1:
        sr0 = sr0_haircut(float(np.std(gdf.sharpe, ddof=1)), len(gdf))
        gdf["dsr"] = [deflated_sharpe(r.sharpe, r.n, r.skew, r.kurt, sr0)
                      for r in gdf.itertuples()]
        print(f"grid {len(gdf)} combos: exp>0 en {int((gdf.exp>0).sum())} | "
              f"DSR>.95 en {int((gdf.dsr>0.95).sum())} (sr0={sr0:.3f})")

    # PBO sobre el grid (unidades = trades cronologicos)
    ok_rows = ~np.isnan(grid).all(axis=(1, 2))
    R = grid[ok_rows].reshape(ok_rows.sum(), -1)
    R = np.nan_to_num(R, nan=0.0)
    pbo = pbo_cscv(R, S=10)

    # null automatico de ANTI-direccion (mismas señales, direccion opuesta)
    hv = grid[:, list(tp_grid).index(tp_h), list(sl_grid).index(sl_h)]
    anti = run_grid(idx, -np.asarray(dirs), times_ms, last, bid, ask,
                    np.array([float(tp_h)]), np.array([float(sl_h)]),
                    max_hold_ms=max_hold_ms, tick=tick, fees=fees)[:, 0, 0]
    av = anti[~np.isnan(anti)]
    print(f"ANTI-direccion (headline): exp={av.mean():+.2f}t (n={len(av)}) — "
          f"si no es claramente peor que el real, la direccion no aporta")

    res = report(f"{name} tp{tp_h}/sl{sl_h}", hv[~np.isnan(hv)],
                 sig_t[~np.isnan(hv)], n_trials=len(gdf),
                 sd_sr_family=float(np.std(gdf.sharpe, ddof=1)) if len(gdf) > 1 else 0.0,
                 pbo=pbo["pbo"],
                 extra=f"reasons: {ledger.reason.value_counts().to_dict()} | "
                       f"anti={av.mean():+.2f}t")
    res["preflight"] = True
    res["grid"] = gdf
    res["ledger"] = ledger
    return res
