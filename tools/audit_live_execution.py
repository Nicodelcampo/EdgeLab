#!/usr/bin/env python3
"""Audit live/demo NT8 execution quality CSVs emitted by EdgeLabFundedSyncPortfolio & EdgeLabExecutionProbe."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_AUDIT_DIR = Path.home() / "Documents" / "NinjaTrader 8" / "EdgeLab" / "exec_audit"

CANONICAL_RT_PTS = {
    "MNQ": 1.5455,
    "NQ": 1.5455,
    "MES": 0.8877,
    "ES": 0.8877,
    "MGC": 0.6050,
    "GC": 0.6050,
    "MYM": 7.4900,
    "YM": 5.0520,
}

DEFAULT_COMM_RT_USD = {
    "MNQ": 1.24,
    "NQ": 4.28,
    "MES": 1.24,
    "ES": 4.28,
    "MGC": 1.24,
    "GC": 4.28,
}


def _symbol_root(inst: str) -> str:
    s = str(inst or "").strip().upper()
    return s.split()[0] if s else ""


def _stats(series: pd.Series) -> dict[str, float]:
    s = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)),
        "mean": float(np.mean(s)),
        "med": float(np.median(s)),
        "p90": float(np.percentile(s, 90)),
        "p95": float(np.percentile(s, 95)),
        "max": float(np.max(s)),
    }


def _fmt_ms(st: dict[str, float]) -> str:
    if not st or st.get("n", 0) == 0:
        return "n=0"
    return (
        f"n={st['n']} | mean={st['mean']:.1f} | med={st['med']:.1f} | "
        f"p90={st['p90']:.1f} | p95={st['p95']:.1f} | max={st['max']:.1f} ms"
    )


def _fmt_pts(st: dict[str, float], unit: str = "pts") -> str:
    if not st or st.get("n", 0) == 0:
        return "n=0"
    return (
        f"n={st['n']} | mean={st['mean']:+.4f} | med={st['med']:+.4f} | "
        f"p90={st['p90']:+.4f} {unit}"
    )


def load_audit_csvs(path: Path, account: str | None = None, instrument: str | None = None) -> pd.DataFrame:
    files = sorted(path.glob("*.csv")) if path.is_dir() else [path]
    files = [f for f in files if f.exists() and f.is_file()]
    if not files:
        raise FileNotFoundError(f"No CSV files found under {path}")
    frames = [pd.read_csv(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    if account:
        df = df[df["account"].astype(str).str.contains(account, case=False, na=False)]
    if instrument:
        df = df[df["instrument"].astype(str).str.contains(instrument, case=False, na=False)]
    return df.reset_index(drop=True)


def evaluate_execution_df(df: pd.DataFrame, comm_rt_usd_override: float | None = None) -> dict:
    if df.empty:
        return {"empty": True}

    accts = sorted(df["account"].dropna().astype(str).unique().tolist())
    local_sim = [a for a in accts if a.lower() in ("sim101", "playback101")]

    hb = df[df["event_kind"] == "BAR_HEARTBEAT"]
    fills = df[df["event_kind"].isin(["FILL", "PART_FILL"])]
    full_fills = df[df["event_kind"] == "FILL"]
    rejects = df[df["event_kind"] == "REJECTED"]
    partials = df[df["event_kind"] == "PART_FILL"]
    cancels = df[df["event_kind"] == "CANCELLED"]

    bar_delay_all = _stats(df["bar_delay_ms"])
    bar_delay_fills = _stats(fills["bar_delay_ms"])
    ack_lat = _stats(fills["submit_to_ack_ms"])
    fill_lat = _stats(full_fills["submit_to_fill_ms"])
    spread_pts = _stats(df["spread_pts"])
    spread_ticks = _stats(df["spread_ticks"])

    slip_close = _stats(fills["slip_vs_close_pts"])
    slip_touch = _stats(fills["slip_vs_touch_pts"])
    slip_buy = _stats(fills.loc[pd.to_numeric(fills["side"], errors="coerce") > 0, "slip_vs_close_pts"])
    slip_sell = _stats(fills.loc[pd.to_numeric(fills["side"], errors="coerce") < 0, "slip_vs_close_pts"])

    is_exit_mask = fills["order_name"].astype(str).str.startswith(("X_", "FS_FL", "FS_TR")) | fills["order_name"].astype(str).str.contains("_FL|_TR")
    slip_entry = _stats(fills.loc[~is_exit_mask, "slip_vs_close_pts"])
    slip_exit = _stats(fills.loc[is_exit_mask, "slip_vs_close_pts"])

    inst_summaries = []
    for inst_name, g in df.groupby("instrument", dropna=True):
        root = _symbol_root(str(inst_name))
        pv_vals = pd.to_numeric(g["point_value"], errors="coerce").dropna()
        pv = float(pv_vals.iloc[0]) if len(pv_vals) else (2.0 if "MNQ" in root else 5.0)
        gf = g[g["event_kind"].isin(["FILL", "PART_FILL"])]
        qty_vals = pd.to_numeric(gf["qty_filled"], errors="coerce").fillna(1.0).clip(lower=1.0)
        comm_vals = pd.to_numeric(gf["commission_usd"], errors="coerce").dropna()
        if comm_rt_usd_override is not None:
            comm_rt_usd = float(comm_rt_usd_override)
            comm_src = "CLI override"
        elif len(comm_vals) > 0 and float(comm_vals.sum()) > 0.0:
            per_contract_one_side = float((comm_vals / qty_vals.loc[comm_vals.index]).mean())
            comm_rt_usd = 2.0 * per_contract_one_side
            comm_src = "NT8 CSV"
        else:
            comm_rt_usd = DEFAULT_COMM_RT_USD.get(root, 1.24)
            comm_src = "default proxy (check Tradovate statement!)"

        comm_rt_pts = comm_rt_usd / pv
        mean_slip_close = float(pd.to_numeric(gf["slip_vs_close_pts"], errors="coerce").dropna().mean()) if len(gf) else float("nan")
        implied_rt_pts = (2.0 * mean_slip_close + comm_rt_pts) if not np.isnan(mean_slip_close) else float("nan")
        canon_rt = CANONICAL_RT_PTS.get(root, float("nan"))
        ratio = (implied_rt_pts / canon_rt) if (not np.isnan(implied_rt_pts) and canon_rt > 0) else float("nan")

        inst_summaries.append({
            "instrument": str(inst_name),
            "root": root,
            "fills": int(len(gf)),
            "pv": pv,
            "mean_slip_close_pts": mean_slip_close,
            "comm_rt_usd": comm_rt_usd,
            "comm_rt_pts": comm_rt_pts,
            "comm_src": comm_src,
            "implied_rt_pts": implied_rt_pts,
            "canon_rt_pts": canon_rt,
            "ratio_vs_canon": ratio,
        })

    win_rows = []
    if "session_window" in df.columns:
        for win, gw in df.groupby("session_window", dropna=True):
            gwf = gw[gw["event_kind"].isin(["FILL", "PART_FILL"])]
            win_rows.append({
                "window": str(win),
                "bars": int((gw["event_kind"] == "BAR_HEARTBEAT").sum()),
                "fills": int(len(gwf)),
                "bar_delay_med": _stats(gw["bar_delay_ms"]).get("med", float("nan")),
                "fill_lat_med": _stats(gwf["submit_to_fill_ms"]).get("med", float("nan")),
                "spread_tks_mean": _stats(gw["spread_ticks"]).get("mean", float("nan")),
                "slip_close_mean": _stats(gwf["slip_vs_close_pts"]).get("mean", float("nan")),
            })

    verdicts = []
    if local_sim and len(local_sim) == len(accts):
        verdicts.append("LOCAL_SIM_ONLY (Sim101/Playback101 simulate locally; run on DEMO2xy4tfNV / Tradovate)")
    else:
        if rejects.shape[0] > 0:
            verdicts.append(f"HAS_REJECTS (n={len(rejects)})")
        if bar_delay_all.get("p90", 0) > 500:
            verdicts.append("CHECK_PC_CLOCK_OR_CPU (bar_delay_p90 > 500 ms)")
        if fill_lat.get("p90", 0) > 600:
            verdicts.append("CONSIDER_VPS_CHICAGO (fill_lat_p90 > 600 ms)")
        for ins in inst_summaries:
            if not np.isnan(ins["ratio_vs_canon"]) and ins["ratio_vs_canon"] > 1.30:
                verdicts.append(f"FRICTION_EXCEEDS_BACKTEST_{ins['root']} ({ins['implied_rt_pts']:.3f} vs {ins['canon_rt_pts']:.3f} pts)")
        if not verdicts:
            verdicts.append("LOCAL_PC_PASS (latency & friction within EdgeLab assumptions)")

    return {
        "empty": False,
        "accounts": accts,
        "local_sim_accounts": local_sim,
        "n_rows": int(len(df)),
        "n_heartbeats": int(len(hb)),
        "n_fills": int(len(fills)),
        "n_partials": int(len(partials)),
        "n_rejects": int(len(rejects)),
        "n_cancels": int(len(cancels)),
        "bar_delay_all": bar_delay_all,
        "bar_delay_fills": bar_delay_fills,
        "ack_lat": ack_lat,
        "fill_lat": fill_lat,
        "spread_pts": spread_pts,
        "spread_ticks": spread_ticks,
        "slip_close": slip_close,
        "slip_touch": slip_touch,
        "slip_buy": slip_buy,
        "slip_sell": slip_sell,
        "slip_entry": slip_entry,
        "slip_exit": slip_exit,
        "instruments": inst_summaries,
        "windows": win_rows,
        "verdicts": verdicts,
    }


def format_report(res: dict) -> str:
    if res.get("empty"):
        return "No telemetry rows matched."
    lines = []
    if res["local_sim_accounts"]:
        lines.append(f"[WARNING] Local simulation account(s) detected: {res['local_sim_accounts']} — latency/slippage are NOT real broker metrics!")
    lines.append(f"Accounts: {', '.join(res['accounts'])} | Rows={res['n_rows']} (Heartbeats={res['n_heartbeats']}, Fills={res['n_fills']}, Partials={res['n_partials']}, Cancels={res['n_cancels']}, Rejects={res['n_rejects']})")
    lines.append("")
    lines.append("=== LATENCY & BAR TIMING ===")
    lines.append(f"  Bar Delay (all)  : {_fmt_ms(res['bar_delay_all'])}")
    lines.append(f"  Bar Delay (fills): {_fmt_ms(res['bar_delay_fills'])}")
    lines.append(f"  Submit -> Ack    : {_fmt_ms(res['ack_lat'])}")
    lines.append(f"  Submit -> Fill   : {_fmt_ms(res['fill_lat'])}")
    lines.append("")
    lines.append("=== SPREAD & SLIPPAGE (+ = ADVERSE vs BACKTEST) ===")
    lines.append(f"  Spread (pts)     : {_fmt_pts(res['spread_pts'], 'pts')}")
    lines.append(f"  Spread (ticks)   : {_fmt_pts(res['spread_ticks'], 'ticks')}")
    lines.append(f"  Slip vs Close[0] : {_fmt_pts(res['slip_close'], 'pts')}")
    lines.append(f"  Slip vs Touch L1 : {_fmt_pts(res['slip_touch'], 'pts')}")
    lines.append(f"  Slip Buy / Sell  : BUY {_fmt_pts(res['slip_buy'])} || SELL {_fmt_pts(res['slip_sell'])}")
    lines.append(f"  Slip Entry/Exit  : ENT {_fmt_pts(res['slip_entry'])} || EXT {_fmt_pts(res['slip_exit'])}")
    lines.append("")
    lines.append("=== IMPLIED ROUND-TRIP FRICTION vs EDGELAB CANONICAL ===")
    for ins in res["instruments"]:
        lines.append(
            f"  {ins['instrument']:12s} (fills={ins['fills']}) | 2*Slip={2*ins['mean_slip_close_pts'] if not np.isnan(ins['mean_slip_close_pts']) else float('nan'):+.4f} pts + "
            f"CommRT=${ins['comm_rt_usd']:.2f} ({ins['comm_rt_pts']:.4f} pts [{ins['comm_src']}]) "
            f"=> ImpliedRT={ins['implied_rt_pts']:.4f} pts vs Canon={ins['canon_rt_pts']:.4f} pts "
            f"({ins['ratio_vs_canon']*100:.1f}%)"
        )
    if res["windows"]:
        lines.append("")
        lines.append("=== BY SESSION WINDOW (NY ET) ===")
        for w in res["windows"]:
            lines.append(
                f"  {w['window']:16s} | bars={w['bars']:4d} fills={w['fills']:3d} | "
                f"barMed={w['bar_delay_med']:.1f}ms fillMed={w['fill_lat_med']:.1f}ms | "
                f"spr={w['spread_tks_mean']:.2f} tks slip={w['slip_close_mean']:+.4f} pts"
            )
    lines.append("")
    lines.append("VERDICT: " + " | ".join(res["verdicts"]))
    return "\n".join(lines)


def run_self_test() -> None:
    rows = [
        {
            "utc_iso": "2026-11-25T14:33:00.120Z", "strategy": "EdgeLabExecutionProbe", "account": "DEMO2xy4tfNV",
            "connection": "NinjaTrader", "instrument": "MNQ 12-26", "tick_size": 0.25, "point_value": 2.0,
            "session_window": "OPEN_0930_1000", "event_kind": "BAR_HEARTBEAT", "order_name": "", "order_id": "",
            "side": "", "qty_req": "", "qty_filled": "", "order_type": "", "order_state": "",
            "bar_close_utc": "2026-11-25T14:33:00.000Z", "bar_delay_ms": 120.0, "submit_to_ack_ms": "", "submit_to_fill_ms": "",
            "signal_px": 26000.0, "bid_at_signal": 25999.75, "ask_at_signal": 26000.25, "spread_pts": 0.50, "spread_ticks": 2.0,
            "expected_touch_px": "", "fill_px": "", "slip_vs_close_pts": "", "slip_vs_touch_pts": "",
            "slip_vs_close_ticks": "", "slip_vs_touch_ticks": "", "commission_usd": "", "error_code": "", "comment": "",
        },
        {
            "utc_iso": "2026-11-25T14:33:00.310Z", "strategy": "EdgeLabExecutionProbe", "account": "DEMO2xy4tfNV",
            "connection": "NinjaTrader", "instrument": "MNQ 12-26", "tick_size": 0.25, "point_value": 2.0,
            "session_window": "OPEN_0930_1000", "event_kind": "FILL", "order_name": "PROBE_1_L", "order_id": "O1",
            "side": 1, "qty_req": 1, "qty_filled": 1, "order_type": "Market", "order_state": "Filled",
            "bar_close_utc": "2026-11-25T14:33:00.000Z", "bar_delay_ms": 120.0, "submit_to_ack_ms": 65.0, "submit_to_fill_ms": 190.0,
            "signal_px": 26000.0, "bid_at_signal": 25999.75, "ask_at_signal": 26000.25, "spread_pts": 0.50, "spread_ticks": 2.0,
            "expected_touch_px": 26000.25, "fill_px": 26000.50, "slip_vs_close_pts": 0.50, "slip_vs_touch_pts": 0.25,
            "slip_vs_close_ticks": 2.0, "slip_vs_touch_ticks": 1.0, "commission_usd": 0.62, "error_code": "NoError", "comment": "E1",
        },
        {
            "utc_iso": "2026-11-25T14:34:00.340Z", "strategy": "EdgeLabExecutionProbe", "account": "DEMO2xy4tfNV",
            "connection": "NinjaTrader", "instrument": "MNQ 12-26", "tick_size": 0.25, "point_value": 2.0,
            "session_window": "OPEN_0930_1000", "event_kind": "FILL", "order_name": "X_PROBE_1_L", "order_id": "O2",
            "side": -1, "qty_req": 1, "qty_filled": 1, "order_type": "Market", "order_state": "Filled",
            "bar_close_utc": "2026-11-25T14:34:00.000Z", "bar_delay_ms": 140.0, "submit_to_ack_ms": 70.0, "submit_to_fill_ms": 200.0,
            "signal_px": 26005.0, "bid_at_signal": 26004.75, "ask_at_signal": 26005.25, "spread_pts": 0.50, "spread_ticks": 2.0,
            "expected_touch_px": 26004.75, "fill_px": 26004.75, "slip_vs_close_pts": 0.25, "slip_vs_touch_pts": 0.0,
            "slip_vs_close_ticks": 1.0, "slip_vs_touch_ticks": 0.0, "commission_usd": 0.62, "error_code": "NoError", "comment": "E2",
        },
        {
            "utc_iso": "2026-11-25T14:35:00.250Z", "strategy": "EdgeLabExecutionProbe", "account": "DEMO2xy4tfNV",
            "connection": "NinjaTrader", "instrument": "MNQ 12-26", "tick_size": 0.25, "point_value": 2.0,
            "session_window": "RTH_1000_1600", "event_kind": "REJECTED", "order_name": "PROBE_2_S", "order_id": "O3",
            "side": -1, "qty_req": 1, "qty_filled": 0, "order_type": "Market", "order_state": "Rejected",
            "bar_close_utc": "2026-11-25T14:35:00.000Z", "bar_delay_ms": 110.0, "submit_to_ack_ms": 50.0, "submit_to_fill_ms": "",
            "signal_px": 26001.0, "bid_at_signal": 26000.75, "ask_at_signal": 26001.25, "spread_pts": 0.50, "spread_ticks": 2.0,
            "expected_touch_px": 26000.75, "fill_px": "", "slip_vs_close_pts": "", "slip_vs_touch_pts": "",
            "slip_vs_close_ticks": "", "slip_vs_touch_ticks": "", "commission_usd": "", "error_code": "UnableToSubmitOrder", "comment": "test reject",
        },
    ]
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "test_audit.csv"
        pd.DataFrame(rows).to_csv(p, index=False)
        df = load_audit_csvs(p)
        res = evaluate_execution_df(df)
        assert res["n_rows"] == 4
        assert res["n_fills"] == 2
        assert res["n_rejects"] == 1
        assert abs(res["slip_close"]["mean"] - 0.375) < 1e-9
        ins = res["instruments"][0]
        # 2*0.375 + 1.24/2.0 = 0.75 + 0.62 = 1.37 pts (< canon 1.5455 pts)
        assert abs(ins["implied_rt_pts"] - 1.37) < 1e-6
        assert any("HAS_REJECTS" in v for v in res["verdicts"])
        # Clean case without rejects -> LOCAL_PC_PASS
        res_clean = evaluate_execution_df(df[df["event_kind"] != "REJECTED"])
        assert res_clean["verdicts"] == ["LOCAL_PC_PASS (latency & friction within EdgeLab assumptions)"]
        print("SELF-TEST PASSED:")
        print(format_report(res_clean))


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit NT8 live execution telemetry CSVs")
    ap.add_argument("--path", type=Path, default=DEFAULT_AUDIT_DIR, help="CSV file or exec_audit directory")
    ap.add_argument("--account", default=None, help="Filter substring for Account name")
    ap.add_argument("--instrument", default=None, help="Filter substring for Instrument")
    ap.add_argument("--comm-rt-usd", type=float, default=None, help="Override round-trip commission USD per contract")
    ap.add_argument("--out-md", type=Path, default=None, help="Optional output markdown report path")
    ap.add_argument("--self-test", action="store_true", help="Run built-in unit self-test and exit")
    args = ap.parse_args()

    if args.self_test:
        run_self_test()
        return 0

    df = load_audit_csvs(args.path, account=args.account, instrument=args.instrument)
    res = evaluate_execution_df(df, comm_rt_usd_override=args.comm_rt_usd)
    report = format_report(res)
    print(report)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text("```text\n" + report + "\n```\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
