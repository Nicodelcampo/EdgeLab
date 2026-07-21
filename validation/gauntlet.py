"""Gauntlet — el juicio completo de una estrategia candidata, con umbrales
PRE-REGISTRADOS (del informe compass + disciplina propia del ledger):

  MUERTE si: MCPT p > 0.05 | PBO > 0.50 (si hay grilla) | expectancy neta <= 0
  con costos pre-registrados | OOS de signo contrario a IS | corte mensual con
  concentracion extrema (todo el PnL en 1 mes).
  Ademas: checklist de causalidad (regla 7 del cerebro) es previa al codigo,
  no un numero: toda decision usa datos hasta la barra previa.

report() imprime el veredicto integrado. Cada estrategia arma las piezas que
aplican (una config unica no tiene PBO; una familia si).
"""
import numpy as np
import pandas as pd

from edgelab.audit import deflated_sharpe, sr0_haircut, trade_stats

MCPT_MAX_P = 0.05
PBO_MAX = 0.50


def monthly_cut(pnl, times_ms):
    t = pd.to_datetime(np.asarray(times_ms), unit="ms")
    s = pd.Series(np.asarray(pnl), index=t)
    by = s.groupby(s.index.to_period("M")).agg(["sum", "count", "mean"])
    return by


def is_oos(pnl, times_ms, q=0.70):
    tms = np.asarray(times_ms, dtype=np.float64)
    split = np.quantile(tms, q)
    x = np.asarray(pnl)
    return x[tms < split], x[tms >= split]


def report(name, pnl_net, times_ms, n_trials=1, sd_sr_family=0.0,
           mcpt_p=None, pbo=None, spa_p=None, extra=""):
    """pnl_net: PnL neto por trade (ticks, costos YA descontados)."""
    x = np.asarray(pnl_net, dtype=np.float64)
    x = x[~np.isnan(x)]
    st = trade_stats(x)
    sr0 = sr0_haircut(sd_sr_family, n_trials) if n_trials > 1 else 0.0
    dsr = deflated_sharpe(st["sharpe"], st["n"], st["skew"], st["kurt"], sr0) \
        if st["n"] >= 2 and not np.isnan(st["sharpe"]) else np.nan
    isx, oosx = is_oos(x, times_ms)
    mc = monthly_cut(x, times_ms)
    pos_months = int((mc["sum"] > 0).sum())

    print(f"\n{'='*74}\nGAUNTLET — {name}\n{'='*74}")
    print(f"n={st['n']}  exp_neta={st['exp']:+.2f}t  win={st.get('win', np.nan)*100:.0f}%  "
          f"sharpe/trade={st['sharpe']:.3f}  DSR(sr0={sr0:.2f})={dsr:.2f}")
    print(f"IS={isx.mean():+.2f}t (n={len(isx)})  OOS={oosx.mean():+.2f}t (n={len(oosx)})")
    print(f"meses: {pos_months}/{len(mc)} positivos | "
          + " ".join(f"{p}:{r['sum']:+.0f}t" for p, r in mc.iterrows()))
    if mcpt_p is not None:
        print(f"MCPT p={mcpt_p:.4f} (umbral {MCPT_MAX_P})")
    if pbo is not None:
        print(f"PBO={pbo:.2f} (umbral {PBO_MAX})")
    if spa_p is not None:
        print(f"SPA p={spa_p:.4f}")
    if extra:
        print(extra)

    kills = []
    if st["exp"] <= 0:
        kills.append("expectancy neta <= 0")
    if len(isx) > 10 and len(oosx) > 10 and isx.mean() > 0 and oosx.mean() < 0:
        kills.append("OOS de signo contrario")
    if mcpt_p is not None and mcpt_p > MCPT_MAX_P:
        kills.append(f"MCPT p={mcpt_p:.3f} > {MCPT_MAX_P}")
    if pbo is not None and not np.isnan(pbo) and pbo > PBO_MAX:
        kills.append(f"PBO={pbo:.2f} > {PBO_MAX}")
    if len(mc) >= 4 and (mc["sum"].max() > 0) and \
       (mc["sum"].sum() - mc["sum"].max()) <= 0 < mc["sum"].sum():
        kills.append("todo el PnL concentrado en 1 mes")

    verdict = "MUERTA: " + "; ".join(kills) if kills else "SOBREVIVE esta tanda (no es prueba final)"
    print(f"\nVEREDICTO: {verdict}")
    return {"stats": st, "dsr": dsr, "is": isx.mean() if len(isx) else np.nan,
            "oos": oosx.mean() if len(oosx) else np.nan, "monthly": mc,
            "kills": kills, "alive": not kills}
