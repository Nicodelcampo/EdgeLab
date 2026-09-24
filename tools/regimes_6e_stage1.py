#!/usr/bin/env python3
r"""Familia 6E-REGIMES, etapa 1 target-free (protocolo: docs/research/FAMILIA_6E_REGIMENES_LIQUIDEZ_20260924.md).

Pasos, en orden:
  declare  particiones en el ledger propio de la familia (antes de medir nada)
  ticks    V3: persistencia de log P1 sobre los ticks pre-holdout (research-v2)
  l2       V1 (validez de P1 contra la profundidad L2) y V2 (puente ticks<->L2, sesiones de junio). Incremental: una
           linea por sesion en artifacts/regimes_6e/l2_sessions.jsonl; si se corta, retoma. Toca el holdout SOLO como
           validacion target-free autorizada por Nico (2026-09-24) y cada corrida queda en docs/holdout_access_log.md.
  report   agrega, aplica los umbrales congelados, escribe el artefacto y registra observaciones en el Brain.

Nada mira retornos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.research.holdout_guard import HOLDOUT_START_ISO, check_holdout  # noqa: E402
from edgelab.research.l2_phase0 import defect_reasons, process_session  # noqa: E402
from edgelab.research.liquidity_regimes import (NS, block_proxy, hour_profile, session_bootstrap_mean,  # noqa: E402
                                                session_date, spearman, truth_blocks, within_session_autocorr)

TICKS = Path(r"E:\EdgeLab\data\nt8_research_v2\6E")
L2_DIRS = [Path(r"E:\l2_parquet\6E_09-26"), Path(r"E:\l2_parquet\6E_12-26")]
OUT = REPO / "artifacts" / "regimes_6e"
LEDGER = REPO / "artifacts" / "hippocampus" / "regimes_6e_20260924.jsonl"
PREREG = "docs/research/FAMILIA_6E_REGIMENES_LIQUIDEZ_20260924.md"
HOLDOUT_YMD = int(HOLDOUT_START_ISO[:10].replace("-", ""))
ART_TO_UTC_US = 3 * 3600 * 1_000_000          # reloj L2 6E = ART guardado como UTC (L2_VISOR_RESOLUCION S1)
BLOCKS = {300: (3, 12, 48), 900: (1, 4, 16), 3600: (1, 4)}   # mismos horizontes de reloj: 15 min, 1 h, 4 h
EXP_END, CONF_START = 20260331, 20260401
AUTH = "autorizacion Nico chat 2026-09-24: L2 6E jul-sep solo para validar el sustituto de profundidad, sin retornos"


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def provenance():
    return dict(code_commit=_git("rev-parse", "HEAD"), tree_dirty=bool(_git("status", "--porcelain", "--", "edgelab", "tools")),
                prereg=PREREG)


# ------------------------------------------------------------------ ticks
def load_ticks() -> pd.DataFrame:
    """Ticks pre-holdout de todos los contratos; por dia de sesion se queda el contrato con mas trades."""
    parts = []
    for f in sorted(TICKS.glob("6E_*_ticks.parquet")):
        t = pq.read_table(f, columns=["ts_utc_ns", "bid_ticks", "ask_ticks", "volume", "source_row"]).to_pandas()
        t["contract"] = f.stem.replace("_ticks", "")
        parts.append(t)
    t = pd.concat(parts, ignore_index=True)
    t["session"] = session_date(t["ts_utc_ns"].to_numpy())
    t = t[t.session < HOLDOUT_YMD]
    front = t.groupby(["session", "contract"]).size().reset_index(name="n").sort_values(["session", "n"]) \
        .groupby("session").tail(1).set_index("session")["contract"]
    t = t[t.contract.to_numpy() == front.reindex(t.session).to_numpy()]
    return t.sort_values(["ts_utc_ns", "source_row"], kind="stable").reset_index(drop=True), front


def tick_blocks(t: pd.DataFrame, block_s: int) -> pd.DataFrame:
    return block_proxy(t.ts_utc_ns.to_numpy(), t.volume.to_numpy(), t.bid_ticks.to_numpy(), t.ask_ticks.to_numpy(),
                       block_s=block_s)


# ------------------------------------------------------------------ L2
def l2_sessions():
    """(fecha, dir) del contrato con mas trades ese dia, entre los dos contratos."""
    best = {}
    for d in L2_DIRS:
        for p in sorted((d / "l1_quotes").glob("*.parquet")):
            n = pq.read_table(p, columns=["side"]).to_pandas().side.eq(2).sum()
            if p.stem not in best or n > best[p.stem][1]:
                best[p.stem] = (d, int(n))
    return {s: d for s, (d, n) in sorted(best.items()) if n > 0}


def l2_proxy_and_truth(base: Path, s: str, block_s: int = 900):
    l1 = pq.read_table(base / "l1_quotes" / f"{s}.parquet", columns=["side", "price_tick", "size", "ts_us", "source_row"]) \
        .to_pandas().sort_values("source_row", kind="stable")
    l2 = pq.read_table(base / "l2_depth" / f"{s}.parquet",
                       columns=["side", "operation", "level", "price_tick", "size", "ts_us", "source_row"]) \
        .to_pandas().sort_values("source_row", kind="stable")
    res = process_session(l2, l1)
    bad = defect_reasons(res.qa)
    # trades con el bid/ask vigente (orden de source_row), reloj pasado a UTC
    side, px, sz, ts = l1.side.to_numpy(), l1.price_tick.to_numpy(), l1["size"].to_numpy(), l1.ts_us.to_numpy()
    bid = ask = None
    tt, tb, ta, tv = [], [], [], []
    for sd, p, z, t in zip(side, px, sz, ts):
        if sd == 0:
            ask = int(p)
        elif sd == 1:
            bid = int(p)
        elif sd == 2 and bid is not None and ask is not None:
            tt.append((int(t) + ART_TO_UTC_US) * 1000); tb.append(bid); ta.append(ask); tv.append(int(z))
    tt = np.asarray(tt, np.int64)
    order = np.argsort(tt, kind="stable")                     # el reloj del archivo no tiene inversiones (manifest)
    prox = block_proxy(tt[order], np.asarray(tv)[order], np.asarray(tb)[order], np.asarray(ta)[order], block_s=block_s)
    sn = res.snaps
    truth = truth_blocks((sn["t"].astype(np.int64) + ART_TO_UTC_US) * 1000, sn["bid_sz"], sn["ask_sz"], block_s=block_s) \
        if len(sn["t"]) else pd.DataFrame(columns=["block", "t1", "t2", "snaps"])
    per_min = pd.Series(1, index=pd.to_datetime(tt, utc=True)).resample("1min").sum()
    return prox, truth, bad, per_min


def xcorr_peak(a: pd.Series, b: pd.Series, max_lag_min: int = 240) -> int:
    idx = a.index.union(b.index)
    a, b = a.reindex(idx, fill_value=0).astype(float), b.reindex(idx, fill_value=0).astype(float)
    best, arg = -2.0, None
    for lag in range(-max_lag_min, max_lag_min + 1):
        c = a.corr(b.shift(lag))
        if np.isfinite(c) and c > best:
            best, arg = c, lag
    return arg


# ------------------------------------------------------------------ pasos
def step_declare():
    from edgelab.edge_brain.episode_logger import measurement_episode
    t, _ = load_ticks()
    sess = sorted(int(x) for x in t.session.unique())
    l2 = l2_sessions()
    val = [s for s in l2 if int(s) < HOLDOUT_YMD]
    hold = [s for s in l2 if int(s) >= HOLDOUT_YMD]
    with measurement_episode(LEDGER, "EP-6E-REG-DECLARE-20260924", goal="6E-REGIMES: declarar particiones",
                             recorded_by="tools/regimes_6e_stage1.py declare", repo=REPO, prereg_ref=PREREG) as ep:
        st = ep.store
        st.record_partition("P-6E-REG-EXP", "EXPLORATION", "6E ticks research-v2, sesiones 2025-07-25..2026-03-31",
                            [f"6E:{s}" for s in sess if s <= EXP_END])
        st.record_partition("P-6E-REG-CONF", "CONFIRMATION_RESERVED", "6E ticks research-v2, sesiones 2026-04-01..2026-06-30",
                            [f"6E:{s}" for s in sess if s >= CONF_START])
        st.record_partition("P-6E-REG-L2VAL", "FUTURE", "L2 6E pre-holdout (junio): solo validacion target-free",
                            [f"6E-L2:{s}" for s in val])
        st.record_partition("P-6E-REG-L2HOLDOUT", "FUTURE", f"L2 6E HOLDOUT jul-sep: {AUTH}", [f"6E-L2:{s}" for s in hold])
    print(json.dumps(dict(exp=sum(s <= EXP_END for s in sess), conf=sum(s >= CONF_START for s in sess),
                          l2_val=len(val), l2_holdout=len(hold))))


def step_ticks():
    OUT.mkdir(parents=True, exist_ok=True)
    t, front = load_ticks()
    res = dict(sessions=int(t.session.nunique()), trades=int(len(t)), front_by_session=front.astype(str).to_dict(),
               by_block={})
    for block_s, lags in BLOCKS.items():
        b = tick_blocks(t, block_s)
        b = b[~b.halt]
        prof = hour_profile(b)
        b["resid"] = b.log_p1 - b.hour_ct.map(prof)
        # sin filtros de sesion no declarados: el minimo de pares por sesion (within_session_autocorr) cubre los dias cortos
        row = dict(blocks=int(len(b)), sessions=int(b.session.nunique()),
                   zero_mid_change_share=float((b.mid_changes == 0).mean()),
                   log_p1_quantiles={f"p{q}": float(np.percentile(b.log_p1, q)) for q in (10, 25, 50, 75, 90)},
                   hour_profile_log_p1={int(k): float(v) for k, v in prof.items()},
                   variance_share_explained_by_hour=float(1 - b.resid.var() / b.log_p1.var()), autocorr={})
        for lag in lags:
            h = f"{lag * block_s // 60}min"
            row["autocorr"][h] = dict(
                deseasonalized=session_bootstrap_mean(within_session_autocorr(b, "resid", lag, block_s)),
                raw=session_bootstrap_mean(within_session_autocorr(b, "log_p1", lag, block_s)))
        res["by_block"][str(block_s)] = row
        print(json.dumps({block_s: row["autocorr"]}), flush=True)
    (OUT / "ticks_v3.json").write_text(json.dumps(dict(provenance=provenance(), **res), indent=1), encoding="utf-8")


def step_l2():
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "l2_sessions.jsonl"
    done = {json.loads(x)["session"] for x in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    sessions = l2_sessions()
    hold = [s for s in sessions if int(s) >= HOLDOUT_YMD]
    if hold:
        check_holdout(f"{hold[0][:4]}-{hold[0][4:6]}-{hold[0][6:]}T00:00:00", f"{hold[-1][:4]}-{hold[-1][4:6]}-{hold[-1][6:]}T23:59:59",
                      purpose="target_free_validation",
                      caller=f"tools/regimes_6e_stage1.py l2 (familia 6E-REGIMES, V1): proxy de profundidad vs L2, sin retornos; {AUTH}")
    ticks = None
    for s, base in sessions.items():
        if s in done:
            continue
        prox, truth, bad, per_min = l2_proxy_and_truth(base, s)
        rec = dict(session=s, contract=base.name, holdout=int(s) >= HOLDOUT_YMD, defects=bad)
        if not bad:
            m = prox[~prox.halt].merge(truth, on="block", how="inner")
            m = m[m.snaps >= 60]                                  # al menos 1 min de libro valido en el bloque
            rec.update(blocks=int(len(m)), rho_t1=spearman(m.log_p1, np.log(m.t1)), rho_t2=spearman(m.log_p1, np.log(m.t2)),
                       blocks_detail=m[["block", "hour_ct", "log_p1", "t1", "t2", "trades"]].to_dict("list"))
            if int(s) < HOLDOUT_YMD:                               # V2: puente con research-v2
                if ticks is None:
                    ticks, _ = load_ticks()
                lo, hi = int(m.block.min()) if len(m) else 0, int(m.block.max()) + 900 * NS if len(m) else 0
                tk = ticks[(ticks.ts_utc_ns >= lo - 86400 * NS) & (ticks.ts_utc_ns <= hi + 86400 * NS)]
                tb = tick_blocks(tk, 900)
                br = m.merge(tb[["block", "log_p1"]], on="block", suffixes=("", "_ticks"))
                tmin = pd.Series(1, index=pd.to_datetime(tk.ts_utc_ns.to_numpy(), utc=True)).resample("1min").sum()
                rec.update(bridge_blocks=int(len(br)), rho_bridge=spearman(br.log_p1, br.log_p1_ticks),
                           clock_xcorr_peak_min=xcorr_peak(per_min, tmin))
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=float) + "\n")
        print(json.dumps({k: v for k, v in rec.items() if k != "blocks_detail"}, default=float), flush=True)


def step_report():
    from edgelab.edge_brain.episode_logger import measurement_episode
    v3 = json.loads((OUT / "ticks_v3.json").read_text(encoding="utf-8"))
    rows = [json.loads(x) for x in (OUT / "l2_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    ok = [r for r in rows if not r["defects"] and r.get("blocks", 0) >= 8]
    # V1b: sin perfil horario, perfil de la propia muestra L2 (target-free)
    det = pd.concat([pd.DataFrame(r["blocks_detail"]).assign(session=r["session"]) for r in ok], ignore_index=True)
    det["lt1"] = np.log(det.t1)
    for c in ("log_p1", "lt1"):
        det[c + "_r"] = det[c] - det.groupby("hour_ct")[c].transform("median")
    rho_b = det.groupby("session").apply(lambda d: spearman(d.log_p1_r, d.lt1_r), include_groups=False)
    rho = np.array([r["rho_t1"] for r in ok], float)
    med = float(np.nanmedian(rho))
    v1 = "VALID" if med >= 0.5 else ("WEAK" if med >= 0.3 else "INVALID")
    bridge = [r for r in ok if "rho_bridge" in r]
    v2 = "PASS" if bridge and all(r["rho_bridge"] >= 0.9 for r in bridge) else "FAIL"
    ac = v3["by_block"]["900"]["autocorr"]["60min"]["deseasonalized"]
    v3v = "REGIME" if ac[1] >= 0.3 else ("NO_REGIME" if ac[2] < 0.1 else "INCONCLUSIVE")
    summary = dict(
        V1=dict(verdict=v1, median_rho_t1=med, sessions=len(ok), share_rho_pos=float(np.mean(rho > 0)),
                rho_t1_quantiles={f"p{q}": float(np.nanpercentile(rho, q)) for q in (10, 25, 50, 75, 90)},
                median_rho_t2=float(np.nanmedian([r["rho_t2"] for r in ok])),
                median_rho_deseasonalized=float(np.nanmedian(rho_b)),
                preholdout=dict(sessions=sum(not r["holdout"] for r in ok),
                                median_rho_t1=float(np.nanmedian([r["rho_t1"] for r in ok if not r["holdout"]] or [np.nan]))),
                holdout=dict(sessions=sum(r["holdout"] for r in ok),
                             median_rho_t1=float(np.nanmedian([r["rho_t1"] for r in ok if r["holdout"]] or [np.nan]))),
                skipped=[dict(session=r["session"], defects=r["defects"], blocks=r.get("blocks")) for r in rows if r not in ok]),
        V2=dict(verdict=v2, per_session=[dict(session=r["session"], rho=r["rho_bridge"], blocks=r["bridge_blocks"],
                                              clock_xcorr_peak_min=r["clock_xcorr_peak_min"]) for r in bridge]),
        V3=dict(verdict=v3v, autocorr_1h_deseasonalized_15min=ac,
                variance_share_explained_by_hour=v3["by_block"]["900"]["variance_share_explained_by_hour"],
                all=({k: v["autocorr"] for k, v in v3["by_block"].items()})))
    body = dict(schema="EDGELAB_6E_REGIMES_STAGE1_V1", provenance=provenance(), thresholds_frozen_in=PREREG,
                summary=summary, ticks_sessions=v3["sessions"])
    raw = json.dumps(body, indent=1, default=float)
    (OUT / "stage1_report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    dep = [f"CODE:liquidity_regimes@{hashlib.sha256((REPO / 'edgelab/research/liquidity_regimes.py').read_bytes()).hexdigest()[:16]}",
           "DATA:nt8_research_v2/6E", "DATA:l2_parquet/6E"]
    with measurement_episode(LEDGER, "EP-6E-REG-STAGE1-20260924", goal="6E-REGIMES etapa 1 target-free: V1 V2 V3",
                             recorded_by="tools/regimes_6e_stage1.py report", repo=REPO, prereg_ref=PREREG) as ep:
        st = ep.store
        st.record_observation("OBS-6E-REG-V1", "log P1 (ticks) vs profundidad L2 en el mejor nivel", "TARGET_FREE",
                              ["P-6E-REG-L2VAL", "P-6E-REG-L2HOLDOUT"],
                              {k: summary["V1"][k] for k in ("verdict", "median_rho_t1", "median_rho_t2", "median_rho_deseasonalized", "share_rho_pos")},
                              {"sessions": len(ok)}, sha, depends_on=dep)
        st.record_observation("OBS-6E-REG-V2", "puente P1 research-v2 vs P1 archivo L2 (junio)", "TARGET_FREE",
                              ["P-6E-REG-L2VAL", "P-6E-REG-CONF"], {"verdict": v2, "per_session": summary["V2"]["per_session"]},
                              {"sessions": len(bridge)}, sha, depends_on=dep)
        st.record_observation("OBS-6E-REG-V3", "persistencia de log P1 sin perfil horario", "TARGET_FREE",
                              ["P-6E-REG-EXP", "P-6E-REG-CONF"],
                              {"verdict": v3v, "ac_1h_deseasonalized": ac,
                               "variance_share_explained_by_hour": summary["V3"]["variance_share_explained_by_hour"]},
                              {"sessions": v3["sessions"]}, sha, depends_on=dep)
    print(json.dumps(dict(V1=v1, V1_median=med, V2=v2, V3=v3v, ac1h=ac, artifact=sha[:12]), default=float))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "ticks", "l2", "report"])
    a = ap.parse_args(argv)
    dict(declare=step_declare, ticks=step_ticks, l2=step_l2, report=step_report)[a.step]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
