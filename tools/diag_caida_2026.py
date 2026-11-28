"""DIAG-CAIDA-2026 (pre-registro `docs/research/caida_2026_20261125/PREREGISTRO_DIAG_CAIDA_2026.md`, contado: 10 pruebas).

Parte A: descomposición sizing vs precio de cada corrida NT8 (1 contrato fijo) por trimestre.
Parte B: rasgos de la apertura de NY por sesión (NQ, ES) y percentil de 2026-04 → 2026-09 contra las ventanas de 6 meses
de 2018–2025.

  python tools/diag_caida_2026.py --out docs/research/caida_2026_20261125

Descriptivo: no elige ni prueba reglas. Nunca lee el holdout terminal (corta en 2026-09-30).
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from edgelab.cartera.regimen import rasgos_diarios  # noqa: E402

NY = "America/New_York"
CAND = ROOT / "docs" / "research" / "candidatas_nt8_20261125"
VENT = ("2026-04-01", "2026-09-30")


def parte_a(r1: float = 200.0) -> pd.DataFrame:
    fs = sorted(glob.glob(str(CAND / "*" / "NT8_*.csv")) + glob.glob(str(CAND / "corridas_nt8_nuevas" / "*.csv")))
    out = []
    for f in fs:
        if "riesgo2000" in f or "MNQ" in f:
            continue
        d = pd.read_csv(f)
        if not {"pnl_pts", "riesgo_pts", "en_ny", "entry_price"} <= set(d.columns):
            continue
        d = d[d.riesgo_pts > 0].copy()
        pv = d.valor_punto if "valor_punto" in d else 20.0
        t = pd.to_datetime(d.en_ny)
        d = d[(t >= "2020-01-01") & (t <= VENT[1])]
        t = pd.to_datetime(d.en_ny)
        d["q"] = t.dt.year.astype(str) + "Q" + t.dt.quarter.astype(str)
        d["R"] = d.pnl_pts / d.riesgo_pts
        d["usd_fijo"] = d.pnl_pts * (pv if np.isscalar(pv) else pv.loc[d.index])
        d["stop_pct"] = 100 * d.riesgo_pts / d.entry_price
        nombre = Path(f).stem.replace("NT8_", "").replace("_fijo1", "")
        g = d.groupby("q").agg(n=("R", "size"), R_op=("R", "mean"), usd_fijo_op=("usd_fijo", "mean"),
                               stop_pts=("riesgo_pts", "median"), stop_pct=("stop_pct", "median"))
        g["usd_riesgo_const_op"] = g.R_op * r1
        g.insert(0, "estrategia", nombre)
        out.append(g.reset_index())
    return pd.concat(out, ignore_index=True)


def sesiones(inst: str) -> pd.DataFrame:
    pq = ROOT / "data" / "m1nt8" / f"{inst}_M1_nonadj_utc.parquet"
    d = pd.read_parquet(pq, columns=["open", "high", "low", "close"],
                        filters=[("datetime", ">=", pd.Timestamp("2017-09-01")), ("datetime", "<", pd.Timestamp("2026-10-01 04:00"))])
    d.index = pd.DatetimeIndex(d.index).tz_localize("UTC").tz_convert(NY)
    d = d[(d.index.hour * 60 + d.index.minute >= 570) & (d.index.hour * 60 + d.index.minute < 960)]   # RTH, vela que abre
    d["fecha"] = d.index.normalize().tz_localize(None)
    d["m"] = d.index.hour * 60 + d.index.minute
    filas = []
    prev_c = np.nan
    for f, g in d.groupby("fecha", sort=True):
        if len(g) < 300 or g.m.iloc[0] != 570:
            prev_c = g.close.iloc[-1] if len(g) else prev_c
            continue
        o = g.open.iloc[0]; c = g.close.iloc[-1]
        orb = g[g.m < 585]; hi, lo = orb.high.max(), orb.low.min()
        resto = g[(g.m >= 585) & (g.m < 660)]
        up = resto.index[resto.high > hi]; dn = resto.index[resto.low < lo]
        lado = 0
        if len(up) and (not len(dn) or up[0] < dn[0]): lado = 1
        elif len(dn): lado = -1
        cont = np.nan if lado == 0 else float((c > hi) if lado == 1 else (c < lo))
        man = g[g.m < 690]
        ef = abs(man.close.iloc[-1] - o) / max(np.abs(np.diff(np.r_[o, man.close.to_numpy()])).sum(), 1e-9)
        noche = abs(o - prev_c) if np.isfinite(prev_c) else np.nan
        fn = noche / (noche + abs(c - o)) if np.isfinite(noche) and (noche + abs(c - o)) > 0 else np.nan
        r5 = man.close.iloc[::5].pct_change().dropna().to_numpy()
        ac = float(np.corrcoef(r5[:-1], r5[1:])[0, 1]) if len(r5) > 5 and r5.std() > 0 else np.nan
        filas.append(dict(fecha=int(f.strftime("%Y%m%d")), h=g.high.max(), l=g.low.min(), c=c,
                          cont_orb=cont, ef_manana=ef, frac_noche=fn, ac5_manana=ac))
        prev_c = c
    s = pd.DataFrame(filas)
    rr = rasgos_diarios(s[["fecha", "h", "l", "c"]])
    s = s.merge(rr[["fecha", "rv_rel"]], on="fecha", how="left") if "rv_rel" in rr else s
    s["dt"] = pd.to_datetime(s.fecha.astype(str))
    return s[s.dt >= "2018-01-01"]


def parte_b(inst: str) -> tuple[dict, pd.DataFrame]:
    s = sesiones(inst)
    rasgos = ["cont_orb", "ef_manana", "frac_noche", "rv_rel", "ac5_manana"]
    mens = s.set_index("dt")[rasgos].resample("MS").mean()
    hist = s[s.dt < "2026-01-01"].set_index("dt")[rasgos]
    w = s[(s.dt >= VENT[0]) & (s.dt <= VENT[1])][rasgos].mean()
    res = {}
    for r in rasgos:
        roll = hist[r].resample("MS").mean().rolling(6).mean().dropna()
        res[r] = dict(ventana=round(float(w[r]), 4), hist_mediana=round(float(roll.median()), 4),
                      hist_p05=round(float(roll.quantile(0.05)), 4), hist_p95=round(float(roll.quantile(0.95)), 4),
                      percentil=round(float((roll < w[r]).mean() * 100), 1))
    return res, mens


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    A = parte_a(); A.to_csv(a.out / "PARTE_A_SIZING_VS_PRECIO.csv", index=False)
    res = {}
    for inst in ("NQ", "ES"):
        r, mens = parte_b(inst); res[inst] = r
        mens.round(4).to_csv(a.out / f"PARTE_B_RASGOS_MENSUALES_{inst}.csv")
    (a.out / "PARTE_B_PERCENTILES.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    pd.set_option("display.width", 220)
    print(json.dumps(res, indent=1))
    piv = A[A.q >= "2025Q1"].pivot_table(index="estrategia", columns="q", values="R_op").round(2)
    print(piv.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
