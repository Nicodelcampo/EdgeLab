#!/usr/bin/env python3
"""CARRIL2-CRASH (pre-registro docs/research/carril2_20261119/PREREGISTRO_CRASH.md): IBS, Double Seven y pico de VIX con el filtro «no comprar con
la curva de VIX invertida (VIX9D/VIX ≥ 1)». Lee operaciones ya calculadas (lote 1 y 2) y el VIX de CBOE; sin motor nuevo.

  python tools/carril2_crash.py desc   # T1 en DESC 2011–2017 → CRASH_DESC.json (commitear antes de rep)
  python tools/carril2_crash.py rep    # T2 en REP con K49 y LORD++ → CRASH_REP.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/carril2_20261119"; PRE = "docs/research/carril2_20261119/PREREGISTRO_CRASH.md"; FAM = "CARRIL2_A5"


def operaciones():
    from datos import ruta
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); V.index = pd.to_datetime(V.index).normalize()
    ts = (V.vix9d_close / V.vix_close).dropna()
    A = pd.read_csv(DIR / "OPS.csv.gz"); B = pd.read_csv(DIR / "OPS_LOTE2.csv.gz")
    O = pd.concat([A[A.definicion.isin(["C2_IBS", "C2_D7"])], B[B.definicion == "C2_VBB"]], ignore_index=True)
    d = pd.to_datetime(O.fecha.astype(str))
    pos = np.searchsorted(ts.index.values, d.values, side="left") - 1                # último cierre CBOE ANTERIOR a la sesión de entrada (causal)
    O["vix_ts"] = np.where(pos >= 0, ts.to_numpy()[np.clip(pos, 0, None)], np.nan)
    O = O[np.isfinite(O.vix_ts) & (O.fecha >= 20110101)].copy(); O["invertida"] = O.vix_ts >= 1.0
    O["mes"] = (O.fecha // 100).astype(str); return O


def _contraste(O):
    from carril2 import _media
    from edgelab.research import a5 as A5
    n, i = O[~O.invertida], O[O.invertida]
    d, se, p = A5.diferencia(n.fecha.to_numpy(), n.R.to_numpy(), i.fecha.to_numpy(), i.R.to_numpy())
    m, se2, p2 = _media(n.fecha.to_numpy(), n.R.to_numpy())
    return dict(dif=d, se=se, p=p, R_normal=float(n.R.mean()), R_invertida=float(i.R.mean()), n_normal=int(len(n)), n_invertida=int(len(i)),
                R_filtrada=m, p_filtrada=p2, por_regla={r: dict(normal=float(g[~g.invertida].R.mean()), invertida=float(g[g.invertida].R.mean()) if g.invertida.any() else None,
                                                                 n_inv=int(g.invertida.sum()), n=int(len(g))) for r, g in O.groupby("definicion")})


def desc():
    from registro_global import exigir_contada
    from edgelab.research.diagnostico_grilla import episodios
    exigir_contada(PRE)
    O = operaciones(); O.to_csv(DIR / "OPS_CRASH.csv.gz", index=False)
    T1 = O[(O.bloque == "DESC") & (O.fecha <= 20171231)]; r = _contraste(T1); r["nominada"] = bool(r["dif"] > 0 and r["p"] < 0.05)
    r["episodios_invertida"] = episodios(T1[T1.invertida])["linea"] if T1.invertida.sum() >= 3 else None
    r["episodios_normal"] = episodios(T1[~T1.invertida])["linea"]
    D18 = O[(O.bloque == "DESC") & (O.fecha >= 20180101)]; r["descriptivo_DESC_2018"] = {k: v for k, v in _contraste(D18).items() if k != "por_regla"}
    (DIR / "CRASH_DESC.json").write_text(json.dumps(dict(preregistro=PRE, T1=r), indent=1, default=float)); print(json.dumps(r, indent=1, default=float)[:3000])


def rep():
    from a5_campana import _commiteado
    from edgelab.research import a5 as A5
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / "CRASH_DESC.json"): raise SystemExit("CRASH_DESC.json sin commitear")
    J = json.loads((DIR / "CRASH_DESC.json").read_text())["T1"]; O = pd.read_csv(DIR / "OPS_CRASH.csv.gz"); out = {}
    if not J["nominada"]: out["estado"] = "SIN_NOMINADA"
    else:
        T1 = O[(O.bloque == "DESC") & (O.fecha <= 20171231)]; R = O[O.bloque == "REP"]
        dif = np.where(T1.invertida, -1.0, 1.0) * T1.R.to_numpy()                   # aproximación del contraste por día para el plan
        plan = A5.plan_lectura(FAM, T1.fecha.to_numpy(), dif, int(R.fecha.nunique())); out["plan"] = plan
        if (plan.get("potencia") or 0) < A5.POTENCIA_LECTURA_MIN: out["estado"] = "SIN_POTENCIA_PREVIA"
        else:
            r = _contraste(R); dec = LibroLord().probar(FAM, "REP_CARRIL2_CRASH", [("T2", r["p"])]); out.update(rep=r, lord=dec, confirmada="T2" in (dec.get("confirmadas") or []))
    (DIR / "CRASH_REP.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, default=float)[:2000])


if __name__ == "__main__":
    {"desc": desc, "rep": rep}[sys.argv[1]]()
