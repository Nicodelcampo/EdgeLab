#!/usr/bin/env python3
"""ESTABILIDAD-CARTERA (2026-11-26): caída del final de las carteras INTRADIA8/INTERDIA3, mitigaciones declaradas (inverso de
volatilidad, freno por curva, poda por t de 12 meses; walk-forward mensual) y tamiz de estrategias descartadas o en revisión por lo que
aportan de estabilidad. Pre-registro: docs/research/estabilidad_cartera_20261126/PREREGISTRO.md. Todo en USD por día con 1 micro.

  python tools/estabilidad_cartera.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/estabilidad_cartera_20261126"
INTRA8 = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
INTER3 = ["SOMSF_NQ", "C2VZ_NQ", "C2VZ_ES"]
# micro de cada instrumento: valor del punto y fricción canónica del micro en puntos (edgelab/costos.py; M2K sin costo canónico:
# se usa el de RTY, declarado)
MICRO = {"NQ": (2.0, 1.9775), "ES": (5.0, 1.155), "YM": (0.5, 7.49), "RTY": (5.0, 0.4436), "GC": (10.0, 0.692)}
FULL_FR = {"NQ": 1.5455, "ES": 0.8877, "YM": 5.052, "RTY": 0.4436, "GC": 0.605}
DESDE, HASTA = "2019-07-01", "2026-09-30"
CAIDA_DESDE = "2026-05-01"


def _diario(pts_gross: pd.Series, fechas, inst: str, idx) -> pd.Series:
    pv, fr = MICRO[inst]
    s = ((pts_gross.to_numpy() - fr) * pv)
    return pd.Series(s, index=pd.to_datetime(pd.Series(fechas).astype(str)).dt.normalize().to_numpy()).groupby(level=0).sum().reindex(idx, fill_value=0.0)


def series() -> tuple[pd.DataFrame, dict]:
    M = pd.read_csv(ROOT / "docs/research/cartera_nt8_20261125/MATRIZ_DIARIA_1MICRO.csv.gz", parse_dates=["dia"]).set_index("dia")
    M = M[(M.index >= DESDE) & (M.index <= HASTA)]; idx = M.index
    S = {c: M[c] for c in M.columns}; cobertura = {c: HASTA for c in M.columns}
    F = pd.read_csv(ROOT / "docs/research/remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz")
    for mod, g in F.groupby("modulo"):
        k = f"FS_{mod}_NQ"
        if mod in ("T", "R", "Z", "V"): continue                       # ya están en la matriz (misma regla)
        S[k] = _diario(g.neto + FULL_FR["NQ"], g.dia, "NQ", idx); cobertura[k] = HASTA
    D = ROOT / "docs/research/m1_largo_20261117"
    for inst in ("ES", "YM", "RTY"):
        o = pd.read_csv(D / f"SOM_OPS_{inst}.csv.gz"); o = o[o.celda == "sin_finde"]
        S[f"SOMSF_{inst}"] = _diario(o.bruto, o.dia, inst, idx); cobertura[f"SOMSF_{inst}"] = HASTA
    for inst in ("ES", "YM", "RTY"):
        f = D / f"FRANKLIN_OPS_{inst}.csv.gz"
        if f.exists() and f"FR_{inst}" not in S:
            o = pd.read_csv(f); S[f"FR_{inst}"] = _diario(o.bruto, o.dia, inst, idx); cobertura[f"FR_{inst}"] = HASTA
    en = "P_obj_s0.45_tp2_stop_s0.45_tp2_fin"
    R = ROOT / "docs/research/rq5_regimen_20261119"
    o = pd.read_csv(R / "OPS_DESC_REP.csv.gz"); o = o[o["L60_m1_c689"].astype(bool) & o[f"r_{en}"].notna() & (o[f"k_{en}"] > 0)]
    h = pd.read_csv(R / "HOLDOUT_OPS.csv.gz")
    for inst in ("YM", "RTY"):
        k = f"RQ5_{inst}"
        if k in S: continue
        a = o[o.inst == inst]; b = h[h.inst == inst]
        g = pd.concat([pd.DataFrame(dict(ses=a.ses, pts=a[f"r_{en}"] * a[f"k_{en}"])),
                       pd.DataFrame(dict(ses=b.ses, pts=b[f"r_{en}"] * b[f"k_{en}"]))])
        S[k] = _diario(g.pts, g.ses, inst, idx); cobertura[k] = HASTA
    C = ROOT / "docs/research/candidatas_nt8_20261125/corridas_nt8_nuevas"
    for inst in ("NQ", "ES"):
        d = pd.read_csv(C / f"NT8_C2_EVRP_{inst}.csv", encoding="utf-8-sig")
        S[f"C2EVRP_{inst}"] = _diario(d.pnl_pts, pd.to_datetime(d.ex_ny).dt.strftime("%Y-%m-%d"), inst, idx); cobertura[f"C2EVRP_{inst}"] = HASTA
    for f in ("OPS.csv.gz", "OPS_LOTE2.csv.gz"):                       # resto de Carril 2: sólo hasta 2025-07
        o = pd.read_csv(ROOT / "docs/research/carril2_20261119" / f)
        for (dfn, inst), g in o.groupby(["definicion", "inst"]):
            k = f"{dfn}_{inst}"
            if dfn in ("C2_VZ", "C2_EVRP") or k in S or inst not in MICRO: continue
            s = _diario(g.lado * (g.salida_px - g.entrada), g.fecha_salida, inst, idx)
            s[s.index > "2025-07-31"] = np.nan; S[k] = s; cobertura[k] = "2025-07-31"
    return pd.DataFrame(S), cobertura


def _mes(x): return x.groupby(x.index.to_period("M")).sum(min_count=1).dropna()


def _st(x: pd.Series) -> dict:
    x = x.dropna(); m = _mes(x); eq = x.cumsum(); a = x.groupby(x.index.year).sum()
    return dict(usd_mes=float(m.mean()), t_mes=float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))) if len(m) > 2 and m.std() > 0 else 0.0,
                sharpe_anual=float(m.mean() / m.std(ddof=1) * np.sqrt(12)) if m.std() > 0 else 0.0, pct_meses_pos=float((m > 0).mean()),
                pct_anios_pos=float((a > 0).mean()), caida_max=float((eq - eq.cummax()).min()), peor_mes=float(m.min()))


def caidas(x: pd.Series) -> pd.DataFrame:
    """Episodios de caída (de un máximo a su recuperación o al final): profundidad y duración en días."""
    eq = x.cumsum(); pico = eq.cummax(); dd = eq - pico; out = []; ini = None
    for t, v in dd.items():
        if v < 0 and ini is None: ini = t
        if v == 0 and ini is not None:
            out.append(dict(ini=ini, fin=t, prof=float(dd[ini:t].min()))); ini = None
    if ini is not None: out.append(dict(ini=ini, fin=dd.index[-1], prof=float(dd[ini:].min()), abierta=True))
    return pd.DataFrame(out)


def parte_a(X: pd.DataFrame) -> dict:
    res = {}
    for c in INTRA8 + INTER3:
        x = X[c]; e = caidas(x); eq = x.cumsum()
        tramo = eq[eq.index >= CAIDA_DESDE]; pico = tramo.cummax().iloc[-1]; final = float(tramo.iloc[-1] - tramo.max())
        hist = e.prof.to_numpy() if len(e) else np.array([0.0])
        res[c] = dict(caida_final=final, percentil=float((hist >= final).mean() * 100) if final < 0 else 0.0,
                      caida_max_hist=float(hist.min()), usd_tramo=float(x[x.index >= CAIDA_DESDE].sum()))
    for nombre, cols in (("INTRADIA8", INTRA8), ("INTERDIA3", INTER3)):
        x = X[cols].sum(axis=1); e = caidas(x); eq = x.cumsum(); tramo = eq[eq.index >= CAIDA_DESDE]
        final = float(tramo.iloc[-1] - tramo.max()); hist = e.prof.to_numpy()
        res[nombre] = dict(caida_final=final, percentil=float((hist >= final).mean() * 100) if final < 0 else 0.0,
                           caida_max_hist=float(hist.min()), usd_tramo=float(x[x.index >= CAIDA_DESDE].sum()))
    t = X[INTRA8][X.index >= CAIDA_DESDE]; r = X[INTRA8][X.index < CAIDA_DESDE]
    cm = lambda d: float(np.nanmean(d.corr().to_numpy()[np.triu_indices(len(d.columns), 1)]))
    res["corr_media_intra8_tramo"] = cm(t); res["corr_media_intra8_resto"] = cm(r)
    from m1_largo import cargar
    from datos import ruta
    c = cargar("NQ", ruta("M1NT8")).c.resample("D").last().dropna()
    c = c[(c.index >= "2019-07-01") & (c.index <= HASTA)]; rd = c.pct_change().dropna()
    res["nq_tramo"] = dict(retorno=float(c[c.index >= CAIDA_DESDE].iloc[-1] / c[c.index >= CAIDA_DESDE].iloc[0] - 1),
                           vol_anual_tramo=float(rd[rd.index >= CAIDA_DESDE].std() * np.sqrt(252)),
                           vol_anual_resto=float(rd[rd.index < CAIDA_DESDE].std() * np.sqrt(252)))
    return res


def parte_b(X: pd.DataFrame, cols: list) -> dict:
    D = X[cols].fillna(0.0); meses = D.index.to_period("M"); um = sorted(set(meses)); res = {}
    eval_desde = pd.Period("2020-07", "M")
    def correr(pesos_fn):
        out = []
        for p in um:
            if p < eval_desde: continue
            hist = D[meses < p]; w = pesos_fn(hist)
            out.append((D[meses == p] * w).sum(axis=1))
        return pd.concat(out)
    m0 = correr(lambda h: pd.Series(1.0, index=cols))
    def m1(h):
        sd = h.tail(63).std().replace(0, np.nan); w = (1 / sd).fillna(0)
        base = h.tail(63).sum(axis=1).std(); cand = (h.tail(63) * w).sum(axis=1).std()
        return w * (base / cand if cand > 0 else 0)
    def m2(h):
        ult = h[h.index >= h.index.max() - pd.DateOffset(months=3)].sum(); return (ult >= 0).astype(float)
    def m3(h):
        mm = h[h.index >= h.index.max() - pd.DateOffset(months=12)].groupby(h[h.index >= h.index.max() - pd.DateOffset(months=12)].index.to_period("M")).sum()
        t = mm.mean() / (mm.std(ddof=1) / np.sqrt(len(mm))).replace(0, np.nan); return (t.fillna(0) >= 0).astype(float)
    for nombre, fn in (("M0_iguales", None), ("M1_inv_vol", m1), ("M2_freno_curva_3m", m2), ("M3_poda_t12m", m3)):
        s = m0 if fn is None else correr(fn)
        res[nombre] = _st(s) | dict(usd_tramo_final=float(s[s.index >= CAIDA_DESDE].sum()))
    return res


def parte_c(X: pd.DataFrame, base_cols: list) -> dict:
    base = X[base_cols].sum(axis=1); bst = _st(base); out = {}
    for c in X.columns:
        if c in base_cols: continue
        x = X[c]; ok = x.notna(); b = base[ok]; xs = x[ok]
        mb, mx = _mes(b), _mes(xs); j = pd.concat([mb, mx], axis=1).dropna()
        sb, sc = _st(b), _st(b + xs); sx = _st(xs)
        out[c] = sx | dict(corr_base=float(j.iloc[:, 0].corr(j.iloc[:, 1])), d_sharpe=sc["sharpe_anual"] - sb["sharpe_anual"],
                           d_caida=sc["caida_max"] - sb["caida_max"], hasta=str(xs.index.max().date()))
        o = out[c]
        o["aporta"] = bool(o["t_mes"] >= 2 and o["pct_anios_pos"] >= 0.7 and o["corr_base"] <= 0.3 and o["d_caida"] >= 0)
    return dict(base=bst, candidatas=out)


def main():
    from registro_global import exigir_contada
    exigir_contada(DIR / "PREREGISTRO.md")
    X, cob = series(); X.to_csv(DIR / "SERIES_DIARIAS.csv.gz")
    res = dict(cobertura=cob, A=parte_a(X), B_intradia=parte_b(X, INTRA8), B_interdia=parte_b(X, INTER3),
               C_sobre_intradia=parte_c(X, INTRA8), C_sobre_interdia=parte_c(X, INTER3))
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    print(json.dumps({k: res["A"][k] for k in ("INTRADIA8", "INTERDIA3", "corr_media_intra8_tramo", "corr_media_intra8_resto", "nq_tramo")}, indent=1))


if __name__ == "__main__":
    main()
