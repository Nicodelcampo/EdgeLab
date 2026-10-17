"""ORB-CFD censo 0A (TARGET-FREE: no calcula retornos ni nada posterior al cierre del rango de 15 min).
Mide, por instrumento CFD de Dukascopy (USA500/USATECH/USA30) y por ano: dias, cobertura de cotizaciones en 09:30-10:30 ET,
huecos, ancho del rango de 15 min, spread y spread/ancho. Sirve para fijar guardas de integridad ANTES de medir extensiones.
Precio = mid (bid+ask)/2. Solo ventana 09:25-16:00 ET de lunes a viernes.
"""
import glob, json, math, os, time
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DATASETS = {"USA500": "edgelab-dukascopy-es-usa500", "USATECH": "edgelab-dukascopy-nq-usatech", "USA30": "edgelab-dukascopy-ym-usa30"}
NS = 1_000_000_000
HOLDOUT_UTC = pd.Timestamp("2026-10-01", tz="UTC").value


def locate(slug):
    c = glob.glob("/kaggle/input/**/*_ticks.parquet", recursive=True)
    c = [p for p in c if slug in p or slug.replace("edgelab-dukascopy-", "") in p]
    if not c:
        c = [p for p in glob.glob("/kaggle/input/**/*_ticks.parquet", recursive=True)]
    return c


def rth_rows(path):
    pf = pq.ParquetFile(path)
    T, M, S = [], [], []
    for b in pf.iter_batches(batch_size=4_000_000, columns=["time_utc_ns", "bid", "ask"]):
        t = b.column(0).to_numpy()
        bid = b.column(1).to_numpy()
        ask = b.column(2).to_numpy()
        keep0 = t < HOLDOUT_UTC
        et = pd.DatetimeIndex(t, tz="UTC").tz_convert("America/New_York")
        mins = et.hour.values * 60 + et.minute.values
        m = keep0 & (et.dayofweek.values < 5) & (mins >= 565) & (mins < 960)
        if m.any():
            T.append(np.stack([t[m], (et.year.values[m] * 10000 + et.month.values[m] * 100 + et.day.values[m]).astype(np.int64)]))
            M.append(((bid[m] + ask[m]) / 2.0))
            S.append((ask[m] - bid[m]))
    ts = np.concatenate([x[0] for x in T])
    day = np.concatenate([x[1] for x in T])
    return ts, day, np.concatenate(M), np.concatenate(S)


def open_ns(td):
    d = pd.Timestamp(year=td // 10000, month=(td // 100) % 100, day=td % 100)
    return d.tz_localize("America/New_York").replace(hour=9, minute=30).value if False else \
        pd.Timestamp(d.year, d.month, d.day, 9, 30, tz="America/New_York").tz_convert("UTC").value


def census(inst, path):
    ts, day, mid, spr = rth_rows(path)
    udays, starts = np.unique(day, return_index=True)
    ends = np.append(starts[1:], len(day))
    rows = []
    for td, a, b in zip(udays, starts, ends):
        o = open_ns(int(td))
        t, m, s = ts[a:b], mid[a:b], spr[a:b]
        w1 = (t >= o) & (t < o + 60 * 60 * NS)
        w15 = (t >= o) & (t < o + 15 * 60 * NS)
        r = {"td": int(td), "n_rth": int(b - a), "n_0930_1030": int(w1.sum()), "n_or15": int(w15.sum())}
        pre = t[t < o]
        r["secs_since_last_pre_quote"] = float((o - pre[-1]) / NS) if len(pre) else None
        if w1.sum() >= 2:
            tt = t[w1]
            r["first_quote_delay_s"] = float((tt[0] - o) / NS)
            r["max_gap_0930_1030_s"] = float(np.diff(tt).max() / NS)
        else:
            r["first_quote_delay_s"] = None
            r["max_gap_0930_1030_s"] = None
        if w15.sum() >= 5:
            hi, lo = float(m[w15].max()), float(m[w15].min())
            r["or15_width"] = hi - lo
            r["or15_median_spread"] = float(np.median(s[w15]))
        late = (t >= o + 330 * 60 * NS) & (t < o + 375 * 60 * NS)
        r["n_1500_1545"] = int(late.sum())
        rows.append(r)
    df = pd.DataFrame(rows)
    df["year"] = df["td"] // 10000
    out = {"n_rth_days": int(len(df)), "first_day": int(df.td.min()), "last_day": int(df.td.max()), "per_year": {}, "per_day": rows}
    for y, g in df.groupby("year"):
        ok_first = g["first_quote_delay_s"].notna() & (g["first_quote_delay_s"] <= 300)
        gp = g["max_gap_0930_1030_s"]
        wd = g["or15_width"]
        out["per_year"][int(y)] = {
            "days": int(len(g)),
            "median_quotes_0930_1030": float(g["n_0930_1030"].median()),
            "median_quotes_or15": float(g["n_or15"].median()),
            "days_first_quote_le_300s": int(ok_first.sum()),
            "days_gap_gt_60s": int((gp > 60).sum()), "days_gap_gt_120s": int((gp > 120).sum()), "days_gap_gt_300s": int((gp > 300).sum()),
            "days_n_or15_lt_20": int((g["n_or15"] < 20).sum()),
            "days_n_1500_1545_lt_100": int((g["n_1500_1545"] < 100).sum()),
            "median_or15_width": float(wd.median()) if wd.notna().any() else None,
            "median_or15_spread": float(g["or15_median_spread"].median()) if g["or15_median_spread"].notna().any() else None,
            "median_spread_over_width": float((g["or15_median_spread"] / g["or15_width"]).replace([np.inf], np.nan).median()),
            "median_secs_since_last_pre_quote": float(g["secs_since_last_pre_quote"].median()) if g["secs_since_last_pre_quote"].notna().any() else None,
        }
    return out


def main():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    allp = sorted(glob.glob("/kaggle/input/**/*_ticks.parquet", recursive=True))
    print("parquets:", allp, flush=True)
    res = {"spec_id": "EXP-ORB-CFD-0A-CENSUS", "target_free": True, "holdout_touched": False, "price": "mid=(bid+ask)/2"}
    for inst in DATASETS:
        t0 = time.time()
        p = [x for x in allp if inst in os.path.basename(x)]
        if not p:
            res[inst] = {"ERROR": "parquet no encontrado"}
            continue
        try:
            res[inst] = census(inst, p[0])
            res[inst]["elapsed_s"] = round(time.time() - t0, 1)
            print("OK", inst, res[inst]["n_rth_days"], flush=True)
        except Exception as e:
            res[inst] = {"ERROR": repr(e)[:500]}
            print("ERR", inst, repr(e)[:500], flush=True)
    txt = json.dumps(res, default=float)
    (out_dir / "EXP_ORB_CFD_0A_CENSUS.json").write_text(txt, encoding="utf-8")
    slim = {k: ({kk: vv for kk, vv in v.items() if kk != "per_day"} if isinstance(v, dict) else v) for k, v in res.items()}
    print("=== CENSUS_START ===\n" + json.dumps(slim, indent=1, default=float)[:60000] + "\n=== CENSUS_END ===", flush=True)


if __name__ == "__main__":
    main()
