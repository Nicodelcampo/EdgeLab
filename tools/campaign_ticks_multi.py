#!/usr/bin/env python3
r"""Campaña multi-instrumento sobre ticks (5 familias x 4 variantes x 5 instrumentos = 100 pruebas).

Implementa `docs/research/PREREG_CAMPANA_TICKS_MULTIINSTRUMENTO_20260923.md` + enmienda A1 (commit 60154b9),
aprobada por Nico. Cualquier desvio respecto de ese texto es un bug. Registra campañas y pruebas en el Edge Brain
(`artifacts/hippocampus/campaign_ticks_multi_20260923.jsonl`): 5 campañas de 20 pruebas; la 101 no puede existir.

    .venv\Scripts\python tools\campaign_ticks_multi.py --stage bars      # ticks -> barras 5 min (cache)
    .venv\Scripts\python tools\campaign_ticks_multi.py --stage run       # simulacion + estadistica + Brain
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from edgelab.research.holdout_guard import HOLDOUT_START_ISO  # noqa: E402

DATA = Path(r"E:\EdgeLab\data\nt8_research_v2")
DIRS = {"GC": "GC_parquet", "ES": "ES_parquet", "NQ": "NQ_parquet", "YM": "YM_parquet", "6E": "6E"}
OUT = REPO / "artifacts" / "campaign_ticks_multi"
LEDGER = REPO / "artifacts" / "hippocampus" / "campaign_ticks_multi_20260923.jsonl"
PREREG = "docs/research/PREREG_CAMPANA_TICKS_MULTIINSTRUMENTO_20260923.md@60154b9"
BAR_S = 300
START_DAY = "2025-08-01"
DISC_END = "2026-02-28"          # descubrimiento: ago-2025..feb-2026 ; validacion: mar..jun-2026
HOLDOUT_DAY = HOLDOUT_START_ISO[:10]
RTH = {"ES": (570, 960), "NQ": (570, 960), "YM": (570, 960), "GC": (500, 810), "6E": (480, 900)}   # min ET (A1.2)
COMM_TICKS = {"ES": 0.36, "NQ": 0.9, "YM": 0.9, "GC": 0.45, "6E": 0.72}                            # A1.5
SEED = 20260923
N_PERM = 1000
N_BOOT = 10000
FAMILIES = {
    "F1": [dict(L=6, H=6), dict(L=6, H=12), dict(L=12, H=6), dict(L=12, H=12)],
    "F2": [dict(k=1.5, H=6), dict(k=1.5, H=12), dict(k=2.5, H=6), dict(k=2.5, H=12)],
    "F3": [dict(R=15, X="12"), dict(R=15, X="EOD"), dict(R=30, X="12"), dict(R=30, X="EOD")],
    "F4": [dict(g=0.3, X="12"), dict(g=0.3, X="EOD"), dict(g=0.6, X="12"), dict(g=0.6, X="EOD")],
    "F5": [dict(m=2, H=6), dict(m=2, H=12), dict(m=3, H=6), dict(m=3, H=12)],
}


# ------------------------------------------------------------------ etapa 1: barras

def build_bars(inst: str) -> pd.DataFrame:
    files = sorted((DATA / DIRS[inst]).glob("*.parquet"))
    parts = []
    for f in files:
        q = f"""
        SELECT contract, CAST((ts_utc_ns // 1000000000 + 7200) // 86400 AS BIGINT) AS tday,
               ts_utc_ns // {BAR_S * 1_000_000_000} AS bucket,
               arg_min(price_ticks, ts_utc_ns) AS o, max(price_ticks) AS h, min(price_ticks) AS l,
               arg_max(price_ticks, ts_utc_ns) AS c, sum(volume) AS v, count(*) AS n,
               median(CASE WHEN ask_ticks > bid_ticks THEN ask_ticks - bid_ticks END) AS spread
        FROM read_parquet('{f.as_posix()}')
        WHERE price_ticks IS NOT NULL
        GROUP BY 1, 2, 3"""
        parts.append(duckdb.sql(q).df())
    b = pd.concat(parts, ignore_index=True)
    b["date"] = pd.to_datetime(b["tday"], unit="D").dt.strftime("%Y-%m-%d")
    b = b[(b["date"] >= START_DAY) & (b["date"] < HOLDOUT_DAY)]
    vol = b.groupby(["date", "contract"])["v"].sum().reset_index()
    front = vol.sort_values("v").groupby("date").tail(1).set_index("date")["contract"].sort_index()
    roll = front.ne(front.shift()) & front.shift().notna()                      # A1.4: dia de roll excluido
    keep = front[~roll]
    b = b[b.apply(lambda r: keep.get(r["date"]) == r["contract"], axis=1)] if len(b) < 50_000 else \
        b.merge(keep.rename("front"), left_on="date", right_index=True).query("contract == front").drop(columns="front")
    b = b.sort_values("bucket").reset_index(drop=True)
    et = pd.to_datetime(b["bucket"] * BAR_S, unit="s", utc=True).dt.tz_convert("America/New_York")
    b["et_min"] = et.dt.hour * 60 + et.dt.minute
    b["et_hour"] = et.dt.hour
    return b[["date", "contract", "bucket", "et_min", "et_hour", "o", "h", "l", "c", "v", "n", "spread"]]


# ------------------------------------------------------------------ etapa 2: reglas

def _prep(b: pd.DataFrame):
    tr = np.maximum(b.h, b.c.shift()) - np.minimum(b.l, b.c.shift())
    tr = tr.fillna(b.h - b.l)
    b = b.assign(atr14=tr.rolling(14, min_periods=14).mean(),
                 atr20_prev=tr.rolling(20, min_periods=20).mean().shift(1))
    tp = (b.h + b.l + b.c) / 3.0
    b = b.assign(vwap=(tp * b.v).groupby(b.date).cumsum() / b.v.groupby(b.date).cumsum())
    return b


def _rth_daily(b, inst):
    o0, o1 = RTH[inst]
    r = b[(b.et_min >= o0) & (b.et_min < o1)]
    d = r.groupby("date").agg(rth_open=("o", "first"), rth_close=("c", "last"), rh=("h", "max"), rl=("l", "min"))
    d["range"] = d.rh - d.rl
    d["atr_d"] = d["range"].rolling(14, min_periods=14).mean().shift(1)          # A1.2: previos 14
    d["prev_close"] = d["rth_close"].shift(1)
    return d


def simulate(b: pd.DataFrame, inst: str, fam: str, p: dict) -> list[tuple]:
    """Trades: (date, i_entry, i_exit, dir, entry_px, exit_px, et_hour_entry). Indices globales de barra."""
    trades = []
    o0, o1 = RTH[inst]
    daily = _rth_daily(b, inst) if fam == "F4" else None
    for date, g in b.groupby("date", sort=True):
        idx = g.index.to_numpy()
        O, H_, L_, C = g.o.to_numpy(float), g.h.to_numpy(float), g.l.to_numpy(float), g.c.to_numpy(float)
        et = g.et_min.to_numpy(); n = len(idx)
        if n < 3:
            continue
        pos_until = -1
        if fam in ("F1", "F2", "F5"):
            atr, vw, a20 = g.atr14.to_numpy(), g.vwap.to_numpy(), g.atr20_prev.to_numpy()
            for i in range(n - 1):                                             # nunca se entra en la ultima barra
                if i <= pos_until:
                    continue
                d = 0
                if fam == "F1" and i >= p["L"]:
                    d = int(np.sign(C[i] - C[i - p["L"]]))
                elif fam == "F2" and np.isfinite(atr[i]) and abs(C[i] - vw[i]) > p["k"] * atr[i]:
                    d = -int(np.sign(C[i] - vw[i]))
                elif fam == "F5" and np.isfinite(a20[i]) and (H_[i] - L_[i]) > p["m"] * a20[i]:
                    d = int(np.sign(C[i] - O[i]))
                if d == 0:
                    continue
                e = i + 1
                x = min(e + p["H"] - 1, n - 1)
                if fam == "F2":                                                 # sale al cruzar el VWAP (cierre)
                    for j in range(e, x + 1):
                        if (C[j] - vw[j]) * (-d) <= 0 and j > e - 1:
                            if np.sign(C[j] - vw[j]) != -d:
                                x = j; break
                trades.append((date, idx[e], idx[x], d, O[e], C[x], int(g.et_hour.iloc[e])))
                pos_until = x
        elif fam == "F3":
            start = np.where(et >= o0)[0]
            if not len(start):
                continue
            s0 = start[0]; rng_end = np.where(et >= o0 + p["R"])[0]
            if not len(rng_end):
                continue
            r0 = rng_end[0]
            hi, lo = H_[s0:r0].max() if r0 > s0 else np.nan, L_[s0:r0].min() if r0 > s0 else np.nan
            rth_last = np.where(et < o1)[0]; rth_last = rth_last[-1] if len(rth_last) else n - 1
            for i in range(r0, min(rth_last, n - 1)):
                d = 1 if C[i] > hi else (-1 if C[i] < lo else 0)
                if d:
                    e = i + 1
                    x = min(e + 11, n - 1) if p["X"] == "12" else max(e, min(rth_last, n - 1))
                    trades.append((date, idx[e], idx[x], d, O[e], C[x], int(g.et_hour.iloc[e])))
                    break
        elif fam == "F4":
            if date not in daily.index:
                continue
            row = daily.loc[date]
            if not (np.isfinite(row.atr_d) and np.isfinite(row.prev_close)):
                continue
            start = np.where(et >= o0)[0]
            if not len(start):
                continue
            e = start[0]; gap = O[e] - row.prev_close
            if abs(gap) <= p["g"] * row.atr_d or e >= n - 1:
                continue
            d = -int(np.sign(gap))
            rth_last = np.where(et < o1)[0]; rth_last = rth_last[-1] if len(rth_last) else n - 1
            x = min(e + 11, n - 1) if p["X"] == "12" else max(e, min(rth_last, n - 1))
            exit_px = C[x]
            for j in range(e, x + 1):                                           # toca el cierre previo -> sale ahi
                if L_[j] <= row.prev_close <= H_[j]:
                    x, exit_px = j, float(row.prev_close); break
            trades.append((date, idx[e], idx[x], d, O[e], exit_px, int(g.et_hour.iloc[e])))
    return trades


# ------------------------------------------------------------------ estadistica

def trade_net(trades, cost_by_hour, mult=1.0):
    return np.array([d * (xp - ep) - mult * cost_by_hour.get(h, np.nanmedian(list(cost_by_hour.values())))
                     for (_, _, _, d, ep, xp, h) in trades], dtype=float)


def mcpt_family(b, var_trades, cost_by_hour, disc_days, rng):
    """A1.6: entradas aleatorias en la misma sesion, misma duracion/direccion/cantidad; max sobre variantes."""
    O, C = b.o.to_numpy(float), b.c.to_numpy(float)
    day_of = b.date.to_numpy()
    starts = b.groupby("date").apply(lambda g: (g.index.min(), g.index.max())).to_dict()
    hour = b.et_hour.to_numpy()
    obs, specs = [], []
    for tr in var_trades:
        t = [x for x in tr if x[0] in disc_days]
        net = trade_net(t, cost_by_hour)
        obs.append(net.mean() if len(net) else -np.inf)
        specs.append([(starts[x[0]], x[2] - x[1] + 1, x[3]) for x in t])
    stat = max(obs)
    cost_arr = np.array([cost_by_hour.get(h, np.nan) for h in range(24)])
    cost_arr = np.where(np.isnan(cost_arr), np.nanmedian(cost_arr), cost_arr)
    null = np.empty(N_PERM)
    for k in range(N_PERM):
        best = -np.inf
        for sp in specs:
            if not sp:
                continue
            lo = np.array([s[0][0] for s in sp]); hi = np.array([s[0][1] for s in sp])
            ln = np.array([s[1] for s in sp]); dr = np.array([s[2] for s in sp])
            top = np.maximum(hi - ln + 1, lo)
            st = lo + (rng.random(len(sp)) * (top - lo + 1)).astype(int)
            en = np.minimum(st + ln - 1, hi)
            v = dr * (C[en] - O[st]) - cost_arr[hour[st]]
            best = max(best, v.mean())
        null[k] = best
    p = (1 + np.sum(null >= stat)) / (1 + N_PERM)
    return float(stat), float(p), obs


def session_ci_and_dsr(trades, days, cost_by_hour, mult):
    from edgelab.research.g2 import deflated_sharpe
    from edgelab.stats.cluster_estimand import (SessionAggregate, percentile_interval,
                                                resample_stationary_session_clusters)
    net = trade_net(trades, cost_by_hour, mult)
    per = {}
    for (t, v) in zip(trades, net):
        s = per.setdefault(t[0], [0.0, 0]); s[0] += v; s[1] += 1
    rows = [SessionAggregate(d, float(per.get(d, [0.0, 0])[0]), int(per.get(d, [0.0, 0])[1])) for d in sorted(days)]
    ntr = sum(r.n_trades for r in rows)
    if ntr < 2:
        return dict(n_trades=ntr, expectancy=None, ci=None, dsr=None, ci_pass=False, dsr_pass=False)
    res = resample_stationary_session_clusters(rows, n_replicates=N_BOOT, seed=SEED)
    lo, hi = percentile_interval(res, 0.95)
    pnl = np.array([r.pnl_net for r in rows])
    sd = pnl.std(ddof=1)
    sr = float(pnl.mean() / sd) if sd > 0 else 0.0
    z = (pnl - pnl.mean()) / sd if sd > 0 else pnl * 0
    dsr = float(deflated_sharpe(sr, len(pnl), 100, float((z ** 3).mean()), float((z ** 4).mean())))
    return dict(n_trades=ntr, expectancy=float(res.observed), ci=[float(lo), float(hi)], dsr=dsr,
                ci_pass=bool(lo > 0), dsr_pass=bool(dsr > 0.95))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("bars", "run"), required=True)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.stage == "bars":
        for inst in DIRS:
            b = build_bars(inst)
            b.to_parquet(OUT / f"bars_{inst}.parquet", index=False)
            print(json.dumps(dict(inst=inst, bars=len(b), days=int(b.date.nunique()), first=b.date.min(),
                                  last=b.date.max())), flush=True)
        return 0

    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    rng = np.random.default_rng(SEED)
    rows = []
    with measurement_episode(LEDGER, "EP-CAMPAIGN-TICKS-MULTI-20260923", goal="Campaña multi-instrumento sobre ticks",
                             recorded_by="tools/campaign_ticks_multi.py", prereg_ref=PREREG, repo=REPO,
                             inputs={f"bars_{i}": OUT / f"bars_{i}.parquet" for i in DIRS}) as ep:
        store = DurableHippocampus(LEDGER)
        for fam in FAMILIES:
            store.record_campaign(f"C-TICKS-{fam}", fam, "human:Nico", "agent:claude-code", 20, PREREG,
                                  "research-v2 ticks GC/ES/NQ/YM/6E 2025-08..2026-06 pre-holdout, 5-min bars")
        for inst in DIRS:
            b = _prep(pd.read_parquet(OUT / f"bars_{inst}.parquet"))
            disc_days = set(b.date[b.date <= DISC_END]); val_days = set(b.date[b.date > DISC_END])
            spr = b[b.date <= DISC_END].groupby("et_hour")["spread"].median()
            cost = {int(h): float(v) + COMM_TICKS[inst] for h, v in spr.items() if np.isfinite(v)}
            for fam, variants in FAMILIES.items():
                vt = [simulate(b, inst, fam, p) for p in variants]
                stat, pval, obs = mcpt_family(b, vt, cost, disc_days, rng)
                for vi, (p, tr) in enumerate(zip(variants, vt)):
                    val = [t for t in tr if t[0] in val_days]
                    base = session_ci_and_dsr(val, val_days, cost, 1.0)
                    stress = session_ci_and_dsr(val, val_days, cost, 1.5)
                    survives_1_3 = bool(pval < 0.05 and base["ci_pass"] and stress["ci_pass"] and base["dsr_pass"])
                    row = dict(inst=inst, family=fam, variant=vi, params=p, disc_trades=int(sum(1 for t in tr if t[0] in disc_days)),
                               disc_expectancy=None if not np.isfinite(obs[vi]) else float(obs[vi]),
                               family_mcpt_stat=stat, family_mcpt_p=pval, val_base=base, val_stress=stress,
                               survives_1_3=survives_1_3)
                    rows.append(row)
                    store.record_trial(f"C-TICKS-{fam}", f"T-{fam}-{inst}-v{vi}", f"{fam} {p}", inst,
                                       "net ticks/trade (val, base)",
                                       json.dumps(dict(mcpt_p=round(pval, 4), exp=base["expectancy"], ci=base["ci"],
                                                       dsr=base["dsr"], s13=survives_1_3)))
                print(json.dumps(dict(inst=inst, fam=fam, mcpt_p=round(pval, 4),
                                      val=[None if r["val_base"]["expectancy"] is None else round(r["val_base"]["expectancy"], 3)
                                           for r in rows[-4:]])), flush=True)
        land = pd.DataFrame(rows)
        rep = land[land.survives_1_3].groupby(["family", "variant"]).inst.nunique()
        survivors = [dict(family=f, variant=int(v), n_instruments=int(n)) for (f, v), n in rep.items() if n >= 2]
        ep.note("trials", str(len(rows)))
        ep.note("survivors_1_3", str(int(land.survives_1_3.sum())))
        ep.note("survivors_replicated", json.dumps(survivors))
        land.to_json(OUT / "landscape.json", orient="records", indent=1, default_handler=str)
        (OUT / "summary.json").write_text(json.dumps(dict(prereg=PREREG, trials=len(rows),
                                                          survives_1_3=int(land.survives_1_3.sum()),
                                                          survivors_replicated=survivors,
                                                          trials_by_family=store.trials_by_family()), indent=1),
                                          encoding="utf-8")
        print(json.dumps(dict(trials=len(rows), survives_1_3=int(land.survives_1_3.sum()), replicated=survivors)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
