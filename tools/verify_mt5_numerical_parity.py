#!/usr/bin/env python3
"""Runs real MQL5 bytecode in MetaTrader 5 Strategy Tester to verify 100% trade-by-trade parity vs C#."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import sync_ctrader_mt5_bots as SYNC

MT5_TERM_EXE = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
MT5_ME_EXE = Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe")
MT5_MQL5_DIR = Path(r"C:\Users\nicoc\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5")
MT5_COMMON_FILES = Path(r"C:\Users\nicoc\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
SCRATCH = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1\scratch")


def main() -> int:
    print("[1/4] Syncing and compiling cTrader C# + MT5 MQL5 suites...", flush=True)
    SYNC.sync_and_compile_ctrader(install=True, compile_check=True)
    SYNC.sync_and_compile_mt5(install=True, compile_check=True)

    # Re-compile and run C# VerifyCfdCoreParity.exe to make sure reference reflects latest Shared core
    m1_csv = SCRATCH / "nq_m1_2008_2026.csv"
    cs_tr_csv = SCRATCH / "cfd_core_parity_2025_2026.csv"
    cs_dy_csv = SCRATCH / "cfd_core_daily_2025_2026.csv"
    verify_cs_exe = SCRATCH / "VerifyCfdCoreParity.exe"

    comp_cs = subprocess.run(
        [
            str(SYNC.CSC_EXE),
            "/nologo",
            "/warnaserror",
            "/nowarn:1685",
            f"/out:{verify_cs_exe}",
            str(ROOT / "tools" / "VerifyCfdCoreParity.cs"),
            str(ROOT / "ctrader" / "Shared" / "EdgeLabFundedSyncCfdCore.cs"),
        ],
        capture_output=True,
    )
    if comp_cs.returncode != 0:
        raise RuntimeError(comp_cs.stdout.decode("cp850", errors="replace") + comp_cs.stderr.decode("cp850", errors="replace"))

    print("[2/4] Checking C# VerifyCfdCoreParity.exe reference on 2008-2026 M1...", flush=True)
    if not cs_tr_csv.exists() or cs_tr_csv.stat().st_mtime < (ROOT / "ctrader" / "Shared" / "EdgeLabFundedSyncCfdCore.cs").stat().st_mtime:
        t0 = time.perf_counter()
        res_cs = subprocess.run([str(verify_cs_exe), str(m1_csv), "20250101", str(cs_tr_csv), str(cs_dy_csv)], capture_output=True, text=True)
        if res_cs.returncode != 0:
            raise RuntimeError(f"VerifyCfdCoreParity failed: {res_cs.stderr}")
        print(f"  C# parity run completed in {time.perf_counter() - t0:.1f}s -> {cs_tr_csv}", flush=True)
    else:
        print(f"  Reusing up-to-date C# parity reference -> {cs_tr_csv}", flush=True)

    # Prepare FILE_COMMON binary M1 file for ultra-fast MT5 Strategy Tester ingestion (48 bytes/bar)
    par_dir = MT5_COMMON_FILES / "edgelab_parity"
    par_dir.mkdir(parents=True, exist_ok=True)
    common_bin = par_dir / "nq_m1_2008_2026.bin"
    mt5_out_csv = par_dir / "mt5_parity_trades_2025_2026.csv"
    if mt5_out_csv.exists():
        mt5_out_csv.unlink()
    if not common_bin.exists() or common_bin.stat().st_mtime < Path(__file__).stat().st_mtime or common_bin.stat().st_mtime < m1_csv.stat().st_mtime:
        print("  Encoding binary M1 stream nq_m1_2008_2026.bin for MQL5 FileReadArray...", flush=True)
        import pyarrow.csv as pacsv
        tb = pacsv.read_csv(str(m1_csv))
        ts_s = pd.to_datetime(tb["close_utc"].to_numpy(zero_copy_only=False), format="%Y-%m-%dT%H:%M:%S", utc=True).as_unit("s").asi8
        print(f"    ts_s range: {int(ts_s[0])} .. {int(ts_s[-1])} (rows={len(ts_s)})", flush=True)
        dt_bin = np.dtype([("t", "<i8"), ("o", "<f8"), ("h", "<f8"), ("l", "<f8"), ("c", "<f8"), ("v", "<f8")])
        rec = np.empty(len(ts_s), dtype=dt_bin)
        rec["t"] = ts_s
        rec["o"] = tb["o"].to_numpy(zero_copy_only=False).astype(np.float64)
        rec["h"] = tb["h"].to_numpy(zero_copy_only=False).astype(np.float64)
        rec["l"] = tb["l"].to_numpy(zero_copy_only=False).astype(np.float64)
        rec["c"] = tb["c"].to_numpy(zero_copy_only=False).astype(np.float64)
        rec["v"] = tb["v"].to_numpy(zero_copy_only=False).astype(np.float64)
        rec.tofile(str(common_bin))
        del tb, rec, ts_s

    # Compile VerifyMt5ParityTester.mq5 into MT5_MQL5_DIR\Experts\EdgeLabFundedSync\
    dst_mq5 = MT5_MQL5_DIR / "Experts" / "EdgeLabFundedSync" / "VerifyMt5ParityTester.mq5"
    dst_ex5 = MT5_MQL5_DIR / "Experts" / "EdgeLabFundedSync" / "VerifyMt5ParityTester.ex5"
    SYNC.write_crlf_ascii(dst_mq5, (ROOT / "tools" / "VerifyMt5ParityTester.mq5").read_text(encoding="utf-8"))
    if dst_ex5.exists():
        dst_ex5.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        log_p = tmp_p / "compile_verify.log"
        subprocess.run([str(MT5_ME_EXE), f"/compile:{dst_mq5}", f"/log:{log_p}"], check=False)
        log_txt = SYNC._read_metaeditor_log(log_p)
        if "0 errors, 0 warnings" not in log_txt or not dst_ex5.exists():
            raise RuntimeError(f"Failed compiling VerifyMt5ParityTester.mq5:\n{log_txt}")
        print("[3/4] Compiled VerifyMt5ParityTester.ex5 (0 errors, 0 warnings). Running MT5 Strategy Tester...", flush=True)

        ini_p = tmp_p / "mt5_parity_tester.ini"
        ini_txt = (
            "[Tester]\r\n"
            "Expert=EdgeLabFundedSync\\VerifyMt5ParityTester.ex5\r\n"
            "Symbol=USATECH\r\n"
            "Period=M5\r\n"
            "Optimization=0\r\n"
            "Model=3\r\n"
            "FromDate=2023.11.02\r\n"
            "ToDate=2023.11.04\r\n"
            "ForwardMode=0\r\n"
            "Deposit=100000\r\n"
            "Currency=USD\r\n"
            "Leverage=100\r\n"
            "Visual=0\r\n"
            "ShutdownTerminal=1\r\n"
        )
        ini_p.write_bytes(ini_txt.encode("utf-16"))
        t1 = time.perf_counter()
        proc = subprocess.Popen([str(MT5_TERM_EXE), f"/config:{ini_p}"])
        # Wait up to 420s for MT5 tester to finish reading 6.5M M1 rows and writing mt5_out_csv
        deadline = time.perf_counter() + 420.0
        while time.perf_counter() < deadline:
            ret = proc.poll()
            if ret is not None:
                break
            if mt5_out_csv.exists() and mt5_out_csv.stat().st_size > 200_000:
                # Wait until file size stabilizes (FileClose completed)
                sz1 = mt5_out_csv.stat().st_size
                time.sleep(2.0)
                sz2 = mt5_out_csv.stat().st_size
                if sz2 == sz1:
                    time.sleep(1.0)
                    if proc.poll() is None:
                        proc.terminate()
                    break
            time.sleep(1.5)
        if proc.poll() is None:
            proc.kill()
        print(f"  MT5 Tester run elapsed: {time.perf_counter() - t1:.1f}s", flush=True)

    # Clean up temporary tester EA from terminal Experts folder
    for p in (dst_mq5, dst_ex5):
        if p.exists():
            p.unlink()

    if not mt5_out_csv.exists():
        raise RuntimeError(f"MT5 did not produce {mt5_out_csv}; check MT5 Tester logs.")

    shutil.copy2(mt5_out_csv, SCRATCH / "mt5_parity_trades_2025_2026.csv")
    print("[4/4] Comparing MT5 MQL5 trades vs C# cTrader/NT8 reference...", flush=True)
    df_cs = pd.read_csv(cs_tr_csv)
    df_mt = pd.read_csv(mt5_out_csv)

    for port in ("INDEP", "CORE5", "P7"):
        c_sub = df_cs[df_cs["portfolio"] == port].reset_index(drop=True)
        m_sub = df_mt[df_mt["portfolio"] == port].reset_index(drop=True)
        print(f"\n=== Portfolio {port}: C# n={len(c_sub)} vs MT5 n={len(m_sub)} ===")
        if len(c_sub) != len(m_sub):
            print("  COUNT MISMATCH! Per-module counts:")
            print("  C# :", c_sub["modulo"].value_counts().to_dict())
            print("  MT5:", m_sub["modulo"].value_counts().to_dict())
            # Find first mismatch
            merged = c_sub.merge(m_sub, on=["fecha_int", "modulo", "en_ny"], how="outer", indicator=True, suffixes=("_cs", "_mt"))
            diff_rows = merged[merged["_merge"] != "both"]
            print(diff_rows[["fecha_int", "modulo", "en_ny", "_merge"]].head(15).to_string(index=False))
            return 1

        same_mod = (c_sub["modulo"] == m_sub["modulo"]).all()
        same_side = (c_sub["side"] == m_sub["side"]).all()
        same_en = (c_sub["en_ny"] == m_sub["en_ny"]).all()
        same_ex = (c_sub["ex_ny"] == m_sub["ex_ny"]).all()
        max_px_diff = float(np.max(np.abs(c_sub["entry_price"] - m_sub["entry_price"])))
        max_r_diff = float(np.max(np.abs(c_sub["R_neto_mini"] - m_sub["R_neto_mini"])))
        sum_cs = float(c_sub["R_neto_mini"].sum())
        sum_mt = float(m_sub["R_neto_mini"].sum())
        print(
            f"  same_mod={same_mod} same_side={same_side} same_en={same_en} same_ex={same_ex} | "
            f"sumR C#={sum_cs:+.6f} MT5={sum_mt:+.6f} | max_entry_diff={max_px_diff:.6f} max_R_diff={max_r_diff:.6f}"
        )
        if not (same_mod and same_side and same_en and same_ex) or max_r_diff > 1e-4:
            bad = c_sub.index[np.abs(c_sub["R_neto_mini"] - m_sub["R_neto_mini"]) > 1e-4]
            for idx in bad[:10]:
                print("  DIFF C# :", c_sub.iloc[idx].to_dict())
                print("  DIFF MT5:", m_sub.iloc[idx].to_dict())
            return 1

    print("\nALL 3 PORTFOLIOS (INDEP, CORE5, P7) VERIFIED 100% TRADE-BY-TRADE PARITY IN MQL5!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
