#!/usr/bin/env python3
"""REGIMEN-FORWARD: vigilancia de la canasta T+R y de los regímenes de SOM y Franklin sobre los forwards que ya se producen
(pre-registro docs/research/regimen_forward_20261119/PREREGISTRO.md).

Lee, sin kernels propios: `fundedsyncstack_20261115/cadena/forward/OPS_<HASTA>.csv` (T y R, de `fundedsync_cadena.py traer_forward`),
`quantlab_mt5_eas_20261116/seguimiento/fw<HASTA>/SOM_OPS.csv` (`som_seguimiento.py`) y `reels_20261116/seguimiento/fw<HASTA>/FRANKLIN_OPS.csv`
(`franklin_seguimiento.py`). E-procesos de `edgelab/funnel/secuencial.py`.

  python tools/regimen_forward.py <HASTA AAAAMMDD>     # → docs/research/regimen_forward_20261119/FORWARD_<HASTA>.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/regimen_forward_20261119"; PRE = "docs/research/regimen_forward_20261119/PREREGISTRO.md"
DESDE = 20261114; FR_NQ = 1.5455
REGLAS = {"T": dict(mu=0.075, dd=-20.0, cotas=(-4.0, 3.5)), "R": dict(mu=0.10, dd=-15.0, cotas=(-2.0, 12.0)),
          "CANASTA_TR": dict(mu=0.13, dd=-26.0, cotas=(-6.0, 16.0)), "SOM": dict(mu=0.027, dd=-40.0, cotas=(-4.0, 8.0)),
          "FRANKLIN": dict(mu=0.04, dd=-44.0, cotas=(-3.0, 18.0)),
          "Z_BANDA": dict(mu=0.13, dd=-13.0, cotas=(-3.0, 8.0))}                  # PREREGISTRO_ZBANDA.md (serie separada, no entra en la canasta)


def vigilar(serie, mu, dd, cotas):
    """Edge (e ≥ 20), futilidad (e ≥ 10 con mu0 = mu) y corte por drawdown sobre una serie ordenada de R."""
    from edgelab.funnel.secuencial import EProceso
    lo, hi = cotas; E, Fu = EProceso(0.0, lo, hi, "mayor"), EProceso(mu, lo, hi, "menor"); x = np.asarray(serie, float)
    for v in x:
        if not lo <= v <= hi: return dict(n=int(len(x)), estado="LIMITE_VIOLADO", valor=float(v))
        E.agregar(float(v)); Fu.agregar(float(v))
    c = np.cumsum(x) if len(x) else np.zeros(1); ddm = float((c - np.maximum.accumulate(np.r_[0.0, c])[1:]).min()) if len(x) else 0.0
    est = "EDGE" if E.e_valor >= 20 else ("SUSPENDER_FUTILIDAD" if Fu.e_valor >= 10 else ("SUSPENDER_DRAWDOWN" if ddm <= dd else "SIN_DECIDIR"))
    return dict(n=int(len(x)), R_total=float(x.sum()), R_medio=float(x.mean()) if len(x) else None, e_edge=float(E.e_valor),
                e_futilidad=float(Fu.e_valor), drawdown=ddm, estado=est)


def series(hasta):
    out = {}
    f = ROOT / f"docs/research/fundedsyncstack_20261115/cadena/forward/OPS_{hasta}.csv"
    if f.exists():
        o = pd.read_csv(f, parse_dates=["dia"]); o = o[o.dia >= pd.Timestamp(str(DESDE))]
        t = o[o.modulo == "T"].sort_values("t")
        if len(t) and (t.riesgo < 2).any(): raise SystemExit("riesgo de T < 2: no es el riesgo inicial clip(ORB15·1,25, 2, 100) (auditoría 2026-11-16)")
        t = t.assign(R=t.neto / t.riesgo)
        if "atr20_ses" not in o: raise SystemExit("el forward no trae atr20_ses (ATR20 de sesión CME, el validado): relanzar con el kernel vigente")
        r = o[o.modulo == "R"].sort_values("t").copy(); s = 0.25 * r.atr20_ses; bruto = r.neto + FR_NQ
        r["R"] = (np.where(r.mae_pts >= s, -s, bruto) - FR_NQ) / s
        out["T"], out["R"] = t.R.tolist(), r.R.tolist()
        d = pd.concat([t[["dia", "R"]], r[["dia", "R"]]]).groupby("dia").R.sum().sort_index(); out["CANASTA_TR"] = d.tolist()
        zb = o[o.modulo.astype(str).str.startswith("ZB_")].copy()
        if len(zb):
            s2 = 0.25 * zb.atr20_ses; zb["R"] = (np.where(zb.mae_pts >= s2, -s2, zb.neto + FR_NQ) - FR_NQ) / s2
            out["Z_BANDA"] = zb.groupby("dia").R.mean().sort_index().tolist()      # promedio de las 9 configuraciones por día con operación
    s = ROOT / f"docs/research/quantlab_mt5_eas_20261116/seguimiento/fw{hasta}/SOM_OPS.csv"
    if s.exists():
        S = pd.read_csv(s); out["SOM"] = S.sort_values("entry_time_utc").R.tolist() if "entry_time_utc" in S else S.R.tolist()
    fr = ROOT / f"docs/research/reels_20261116/seguimiento/fw{hasta}/FRANKLIN_OPS.csv"
    if fr.exists():
        F = pd.read_csv(fr); out["FRANKLIN"] = F.sort_values([c for c in ("fecha", "inst") if c in F]).R.tolist()
    return out


def main(hasta):
    from registro_global import exigir_contada
    exigir_contada(PRE)
    S = series(hasta); res = {k: vigilar(S[k], **REGLAS[k]) for k in REGLAS if k in S}
    res = dict(hasta=int(hasta), desde=DESDE, faltan=[k for k in REGLAS if k not in S], resultado=res)
    DIR.mkdir(parents=True, exist_ok=True); (DIR / f"FORWARD_{hasta}.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1])
