#!/usr/bin/env python3
r"""TBZX-R3 iteración 4: escenarios macro contra la fricción (manifiesto §10, fijado antes de medir).

Lee los registros por disparo del kernel (ev/<fecha>.parquet), arma escenarios = (dirección, r) × hasta 2 condiciones
macro con cortes por terciles de DESCUBRIMIENTO (jul–nov 2025), selecciona por P&L realista > 0 (IC, fantasma, FDR) y
evalúa UNA vez en VALIDACIÓN (dic 2025–mar 2026).

    python tools/tbzx_r3_macro.py --ev <dir con ev/> --out <dir> [--configs mb10_mw8 ...]
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

GRID = [(mb, mw) for mb in (10, 20, 40) for mw in (8, 12, 17, 24)]
CFG_NAMES = [f"mb{mb}_mw{mw}" for mb, mw in GRID]
SPLIT = "20251130"          # descubrimiento <= SPLIT < validación
MIN_N = 200
N_BOOT = 1000
SEED = 20260926
Q_FDR = 0.10
COMBOS = [(sl, tp) for sl in (3, 6, 10, 20) for tp in (3, 6, 10, 20)]
TOD = [(0, "asia", 18 * 60, 27 * 60), (1, "europa", 3 * 60, 9.5 * 60), (2, "apertura", 9.5 * 60, 10.5 * 60),
       (3, "mediodia", 10.5 * 60, 14 * 60), (4, "cierre", 14 * 60, 17 * 60)]
META = ["si", "td", "cfg", "nul", "ladoB", "D", "ip", "r", "up", "W", "tr15", "tr60", "tr240", "vol30", "vwapd", "tod"]


def tod_bucket(m):
    m = np.asarray(m, float)
    b = np.full(len(m), -1, np.int8)
    b[(m >= 18 * 60) | (m < 3 * 60)] = 0
    b[(m >= 3 * 60) & (m < 9.5 * 60)] = 1
    b[(m >= 9.5 * 60) & (m < 10.5 * 60)] = 2
    b[(m >= 10.5 * 60) & (m < 14 * 60)] = 3
    b[(m >= 14 * 60) & (m < 17 * 60)] = 4
    return b


def bh(p, q):
    p = np.asarray(p, float); m = len(p)
    if m == 0:
        return np.zeros(0, bool)
    o = np.argsort(p); ok = p[o] <= q * np.arange(1, m + 1) / m
    k = np.max(np.nonzero(ok)[0]) + 1 if ok.any() else 0
    r = np.zeros(m, bool); r[o[:k]] = True
    return r


def load(ev_dir: Path, configs):
    files = sorted(glob.glob(str(ev_dir / "ev" / "*.parquet")))
    cols = None
    parts = []
    for f in files:
        if cols is None:
            import pyarrow.parquet as pq
            allc = pq.ParquetFile(f).schema.names
            cols = META + [c for c in allc if c.startswith(("perfecta_mid|", "realista|"))]
        parts.append(pd.read_parquet(f, columns=cols))
    D = pd.concat(parts, ignore_index=True)
    keep = [CFG_NAMES.index(c) for c in configs] if configs else list(range(len(GRID)))
    D = D[D.cfg.isin(keep)]
    # un disparo = un trade: el mismo instante y lado en varias (config, D, p) es la misma operación
    D["tsec"] = np.round(D.tod.astype(float) * 60).astype(np.int64)
    D = D.drop_duplicates(["si", "nul", "tsec", "up", "r"]).reset_index(drop=True)
    return D


def conditions(D, disc):
    """Variables macro por dirección (q = +1 compra, −1 venta) y sus cortes por terciles en descubrimiento."""
    out = {}
    for dn in ("sigue", "rebota"):
        q = np.where(D.up == 1, -1, 1) if dn == "sigue" else np.where(D.up == 1, 1, -1)
        V = pd.DataFrame(index=D.index)
        V["tend60"] = D.tr60 * q
        V["tend240"] = D.tr240 * q
        V["vol30"] = D.vol30
        V["W_vol"] = D.W / D.vol30.replace(0, np.nan)
        V["vwap"] = D.vwapd * q
        L = pd.DataFrame(index=D.index)
        cuts = {}
        for c in V.columns:
            lo, hi = np.nanquantile(V.loc[disc, c], [1 / 3, 2 / 3])
            cuts[c] = (float(lo), float(hi))
            L[c] = np.select([V[c] <= lo, V[c] <= hi, V[c] > hi], [0, 1, 2], -1).astype(np.int8)
            L.loc[V[c].isna(), c] = -1
        L["hora"] = tod_bucket(D.tod)
        L["lado"] = D.ladoB.astype(np.int8)
        out[dn] = (L, cuts)
    return out


def boot_mean(y, si, sessions, W):
    """Media por disparo y su bootstrap por sesión."""
    idx = np.searchsorted(sessions, si)
    s = np.bincount(idx, weights=y, minlength=len(sessions)); n = np.bincount(idx, minlength=len(sessions))
    pt = s.sum() / max(n.sum(), 1)
    bt = (W @ s) / np.maximum(W @ n, 1)
    return pt, bt


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ev", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--configs", nargs="*")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    D = load(Path(a.ev), a.configs)
    disc = (D.td.astype(str) <= SPLIT).to_numpy()
    val = ~disc
    C = conditions(D, disc)
    rng = np.random.default_rng(SEED)
    res = []
    feats = ["tend60", "tend240", "vol30", "W_vol", "vwap", "hora", "lado"]
    for dn in ("sigue", "rebota"):
        L, cuts = C[dn]
        conds = [()] + [((f, lv),) for f in feats for lv in sorted(set(L[f].unique()) - {-1})]
        conds += [((f1, l1), (f2, l2)) for f1, f2 in itertools.combinations(feats, 2)
                  for l1 in sorted(set(L[f1].unique()) - {-1}) for l2 in sorted(set(L[f2].unique()) - {-1})]
        for r in sorted(D.r.unique()):
            base = (D.r == r).to_numpy()
            for cond in conds:
                m = base.copy()
                for f, lv in cond:
                    m &= (L[f] == lv).to_numpy()
                real_d = m & disc & (D.nul == 0).to_numpy()
                if real_d.sum() < MIN_N:
                    continue
                fant_d = m & disc & (D.nul == 1).to_numpy()
                ses_d = np.unique(D.si[real_d])
                Wd = np.stack([np.bincount(rng.integers(0, len(ses_d), len(ses_d)), minlength=len(ses_d))
                               for _ in range(N_BOOT)]).astype(float)
                for sl, tp in COMBOS:
                    col = f"realista|{dn}|SL{sl}|TP{tp}"
                    y = D[col].to_numpy(float)
                    pt, bt = boot_mean(y[real_d], D.si.to_numpy()[real_d], ses_d, Wd)
                    fm = fant_d & np.isin(D.si.to_numpy(), ses_d)
                    pf, bf = boot_mean(y[fm], D.si.to_numpy()[fm], ses_d, Wd) if fm.sum() >= MIN_N else (np.nan, None)
                    mid = D[f"perfecta_mid|{dn}|SL{sl}|TP{tp}"].to_numpy(float)
                    res.append(dict(dir=dn, r=int(r), cond=" & ".join(f"{f}={lv}" for f, lv in cond) or "todo",
                                    SL=sl, TP=tp, n_disc=int(real_d.sum()), pnl_disc=float(pt),
                                    pnl_disc_lo=float(np.quantile(bt, .025)), p_disc=float((bt <= 0).mean()),
                                    pnl_fant_disc=float(pf) if pf == pf else None,
                                    dfant_lo=float(np.quantile(bt - bf, .025)) if bf is not None else None,
                                    mid_disc=float(mid[real_d].mean()), _cond=cond, _col=col))
    R = pd.DataFrame(res)
    R["fdr"] = bh(R.p_disc, Q_FDR)
    R["elegido"] = R.fdr & (R.pnl_disc_lo > 0) & (R.dfant_lo.fillna(-1) > 0)
    # validación, una sola vez
    vs = []
    for i, row in R.iterrows():
        if not row["elegido"]:
            vs.append((np.nan, np.nan, np.nan)); continue
        L = C[row["dir"]][0]
        m = (D.r == row["r"]).to_numpy() & val & (D.nul == 0).to_numpy()
        for f, lv in row["_cond"]:
            m &= (L[f] == lv).to_numpy()
        if m.sum() == 0:
            vs.append((0, np.nan, np.nan)); continue
        y = D[row["_col"]].to_numpy(float)[m]; si = D.si.to_numpy()[m]
        ses = np.unique(si)
        Wv = np.stack([np.bincount(rng.integers(0, len(ses), len(ses)), minlength=len(ses))
                       for _ in range(N_BOOT)]).astype(float)
        pt, bt = boot_mean(y, si, ses, Wv); vs.append((int(m.sum()), float(pt), float(np.quantile(bt, .025))))
    R["n_val"], R["pnl_val"], R["pnl_val_lo"] = zip(*vs)
    R["sostenido"] = R.elegido & (R.pnl_val > 0) & (R.pnl_val_lo > 0)
    R = R.drop(columns=["_cond", "_col"])
    R.to_csv(out / "macro_escenarios.csv.gz", index=False)
    cuts_all = {dn: C[dn][1] for dn in C}
    summ = dict(disparos=int(len(D)), reales=int((D.nul == 0).sum()), sesiones_disc=int(D.si[disc].nunique()),
                sesiones_val=int(D.si[val].nunique()), escenarios_probados=int(len(R)), fdr=int(R.fdr.sum()),
                elegidos=int(R.elegido.sum()), sostenidos=int(R.sostenido.sum()), cortes=cuts_all,
                realista_positivos_disc=int((R.pnl_disc > 0).sum()),
                mejores_disc=R.sort_values("pnl_disc", ascending=False).head(15).to_dict("records"),
                elegidos_lista=R[R.elegido].sort_values("pnl_disc", ascending=False).head(50).to_dict("records"))
    (out / "macro_resumen.json").write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps({k: v for k, v in summ.items() if k not in ("mejores_disc", "elegidos_lista", "cortes")}, indent=1))


if __name__ == "__main__":
    main()
