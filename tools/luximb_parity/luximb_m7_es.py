"""M7: "un area cargada de OG/VI frena el precio" — escalonadas en ES, descubrimiento.
Reglas: docs/research/luximb_parity_20261020/MANIFIESTO_M7_ES_AREA_CARGADA_FRENA_20261020.md (no cambiar sin enmienda).
Numpy por contrato (sin bundles JSON). Uso: python tools/luximb_parity/luximb_m7_es.py <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "tools"))
import parity_luximb as P  # noqa: E402
import escalonadas_det as E  # noqa: E402
from luximb_m6 import carrera  # noqa: E402
from luximb_outcomes import COMM as COMM_NQ, REP_START  # noqa: E402

SRC = "D:/edgelab_release_work/release_v4/data/ES_ticks.parquet"
TRAMOS = [("ES 09-25", 20250721, 20250915), ("ES 12-25", 20250916, 20251215), ("ES 03-26", 20251216, 20260316), ("ES 06-26", 20260317, 20260331)]
TICK, K, M25, VIDA_MIN, COMM_ES = 0.25, 350, 14, 500, 0.09
FAM = dict(E.FAMILIA_NQ, max_step=10, min_pull=3, conf=4, nmin=5)
NB = 10000


def cargar(contrato, d0, d1):
    pf = pq.ParquetFile(SRC); md = pf.metadata
    ci = {md.row_group(0).column(i).path_in_schema: i for i in range(md.row_group(0).num_columns)}
    ts, px, vv = [], [], []
    for r in range(md.num_row_groups):
        g = md.row_group(r); td = g.column(ci["trade_date"]).statistics; ct = g.column(ci["contract"]).statistics
        if td.max < d0 or td.min > d1 or str(ct.min) > contrato or str(ct.max) < contrato: continue
        tb = pf.read_row_group(r, columns=["ts_utc_ns", "price_ticks", "volume", "contract", "trade_date"])
        m = (tb["contract"].to_numpy(zero_copy_only=False) == contrato) & (tb["trade_date"].to_numpy() >= d0) & (tb["trade_date"].to_numpy() <= d1)
        ts.append(tb["ts_utc_ns"].to_numpy()[m]); px.append(tb["price_ticks"].to_numpy()[m]); vv.append(tb["volume"].to_numpy()[m])
    ts = np.concatenate(ts); o = np.argsort(ts, kind="stable")
    return ts[o], np.concatenate(px)[o].astype(float) * TICK, np.concatenate(vv)[o].astype(float)


def m1(ts, px):
    key = ts // 60_000_000_000 + 1                       # marca de cierre; tick en :00 abre vela nueva (convencion validada)
    st = np.flatnonzero(np.r_[True, np.diff(key) != 0]); en = np.r_[st[1:], len(ts)]
    return key[st] * 60, px[st], np.maximum.reduceat(px, st), np.minimum.reduceat(px, st), px[en - 1]


def velas_n(t_s, px, n):
    brk = np.r_[True, np.diff(t_s) > 1800 * 10**9]; seg = np.cumsum(brk) - 1
    pos = np.arange(len(t_s)) - np.flatnonzero(brk)[seg]
    st = np.flatnonzero(np.r_[True, (seg[1:] != seg[:-1]) | (pos[1:] // n != pos[:-1] // n)])
    return st, np.maximum.reduceat(px, st), np.minimum.reduceat(px, st), px[np.r_[st[1:], len(px)] - 1]


def eventos_contrato(contrato, d0, d1):
    ts, px, _ = cargar(contrato, d0, d1)
    tcl, o, h, l, c = m1(ts, px)
    Z = P.detect(o, h, l, c)
    zav = np.array([tcl[i] for i, *_ in Z]); zt1 = zav + VIDA_MIN * 60
    ztop = np.array([z[3] for z in Z]); zbot = np.array([z[4] for z in Z])
    s25, h25, l25, c25 = velas_n(ts, px, 25); t25 = (ts[s25] // 10**9).astype(float)
    del ts, px
    seg = np.cumsum(np.r_[True, np.diff(t25) > 1800]) - 1
    pos = np.arange(len(seg)) - np.flatnonzero(np.r_[True, seg[1:] != seg[:-1]])[seg]
    st = np.flatnonzero(np.r_[True, (seg[1:] != seg[:-1]) | (pos[1:] // M25 != pos[:-1] // M25)])
    cd = dict(t=t25[st], h=np.maximum.reduceat(h25, st), l=np.minimum.reduceat(l25, st), c=c25[np.r_[st[1:], len(c25)] - 1])
    E.TICK = TICK
    rows = []
    for z in E.detectar_px(cd, FAM, FAM["conf"]):
        i0, di = z["picos"][0][0], z["det_i"]
        lo, hi = float(cd["l"][i0:di + 1].min()), float(cd["h"][i0:di + 1].max()); td = cd["t"][di]
        n = int(((zav <= td) & (zt1 > td) & (zbot <= hi) & (ztop >= lo)).sum())
        if td >= REP_START: raise SystemExit("evento fuera de descubrimiento")
        i25 = int(st[di + 1]) if di + 1 < len(st) else len(t25)
        if i25 >= len(t25): continue
        ev = dict(kind=z["kind"], det_cierre=float(cd["c"][di]), area_lo=lo, area_hi=hi, det_nivel=z["det_nivel"], i25_post=i25)
        r = carrera(ev, t25, h25, l25, c25, (0, 1, 2))
        for k in list(r):
            if k.startswith("pnl_"): r[k] = r[k] + COMM_NQ - COMM_ES          # costos ES propios
        j = int(np.searchsorted(t25, t25[i25] + 3600, "left"))
        rec = float(h25[i25:j].max() - l25[i25:j].min()) if j > i25 else np.nan
        jp = int(np.searchsorted(t25, t25[i25] - 3600, "left"))          # M7b: volatilidad de los 60 min previos (causal)
        vol_pre = float(h25[jp:i25].max() - l25[jp:i25].min()) if i25 > jp else np.nan
        ny = pd.Timestamp(td, unit="s", tz="UTC").tz_convert("America/New_York")
        rows.append(dict(contrato=contrato, kind=z["kind"], det_t=td, dia=str(ny.date()), cash=bool(9.5 <= ny.hour + ny.minute / 60 < 11),
                         zonas=n, esT=n >= 3, area=hi - lo, recorrido_pts=rec, vol_pre=vol_pre, **r))
    print(contrato, "M1", len(tcl), "zonas", len(Z), "velas350", len(st), "escalonadas", len(rows), flush=True)
    return rows


def boot_fn(df, fn, rng):
    days = df.dia.unique(); idx = {d: np.flatnonzero(df.dia.values == d) for d in days}
    full = fn(df); bs = np.empty(NB)
    for k in range(NB):
        pick = rng.choice(days, len(days)); bs[k] = fn(df.iloc[np.concatenate([idx[d] for d in pick])])
    return full, bs


def resumen(full, bs, lado):
    p = float(np.mean(bs >= 0)) if lado == "menor" else float(np.mean(bs <= 0))
    return dict(est=round(float(full), 4), ic95=[round(float(np.nanpercentile(bs, 2.5)), 4), round(float(np.nanpercentile(bs, 97.5)), 4)],
                p_unilateral=p, se=float(np.nanstd(bs)))


def main():
    out = sys.argv[1]; rows = []
    for c, a, b in TRAMOS:
        rows += eventos_contrato(c, a, b)
    df = pd.DataFrame(rows); df["r"] = (df.res == "ruptura").astype(float)
    terc = np.quantile(df.area, [1 / 3, 2 / 3]); df["estrato"] = np.digitize(df.area, terc).astype(str) + df.cash.map({True: "c", False: "r"})
    rng = np.random.default_rng(20261024)
    dif = lambda col: (lambda d: d.loc[d.esT, col].mean() - d.loc[~d.esT, col].mean())

    def emparejado(d):
        tot, acc = 0, 0.0
        for s_, g in d.groupby("estrato"):
            nt = int(g.esT.sum())
            if nt and (~g.esT).any(): acc += nt * (g.loc[g.esT, "r"].mean() - g.loc[~g.esT, "r"].mean()); tot += nt
        return acc / tot if tot else np.nan
    H = {"H1_Pruptura_T_menos_C": resumen(*boot_fn(df, dif("r"), rng), "menor"),
         "H2_recorrido60_pts_T_menos_C": resumen(*boot_fn(df, dif("recorrido_pts"), rng), "menor"),
         "H3_Pruptura_emparejado": resumen(*boot_fn(df, emparejado, rng), "menor"),
         "H4_pnl_rechazo_T_1tick": resumen(*boot_fn(df[df.esT], lambda d: d.pnl_rec_1.mean(), rng), "mayor")}
    fam = {k: v["p_unilateral"] for k, v in H.items()}
    order = sorted(fam, key=fam.get); holm = {}; run = 0.0
    for k, n in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * fam[n])); holm[n] = round(run, 4)
    desc = {g: dict(n=len(x), dias=x.dia.nunique(), P_ruptura=round(x.r.mean(), 4), P_rechazo=round((x.res == "rechazo").mean(), 4),
                    recorrido60_pts_p50=float(x.recorrido_pts.median()), recorrido60_pts_media=round(x.recorrido_pts.mean(), 3), area_p50=float(x.area.median()),
                    **{f"pnl_rup_{s}": round(x[f"pnl_rup_{s}"].mean(), 3) for s in (0, 1, 2)}, **{f"pnl_rec_{s}": round(x[f"pnl_rec_{s}"].mean(), 3) for s in (0, 1, 2)})
            for g, x in df.groupby(df.esT.map({True: "T", False: "C"}))}
    sens = {f">={k}": round(float(df.loc[df.zonas >= k, "r"].mean() - df.loc[df.zonas < k, "r"].mean()), 4) for k in (2, 3, 5)}
    pc = df.groupby(["contrato", "esT"]).agg(n=("r", "size"), P_ruptura=("r", "mean"), recorrido=("recorrido_pts", "mean")).round(3).reset_index().to_dict("records")
    res = dict(manifiesto="MANIFIESTO_M7_ES_AREA_CARGADA_FRENA_20261020.md", K=K, familia=FAM, descriptivo=desc, hipotesis=H, p_holm=holm,
               MDE80_H1_pp=round(2.8 * H["H1_Pruptura_T_menos_C"]["se"] * 100, 1), MDE80_H2_pts=round(2.8 * H["H2_recorrido60_pts_T_menos_C"]["se"], 2),
               sensibilidad_umbral_zonas_dif_Pruptura=sens, por_contrato=pc)
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    df.to_csv(out.replace(".json", "_eventos.csv"), index=False)
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
