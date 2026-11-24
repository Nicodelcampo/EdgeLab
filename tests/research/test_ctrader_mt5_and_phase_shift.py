"""Tests for cTrader C# bots, MT5 MQL5 EAs, CFD C# core logic, tick phase resampling, and deliverables."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))

import fundedsync_bar_phase_shift as BPS
import sync_ctrader_mt5_bots as SYNC

CSC_EXE = SYNC.CSC_EXE
CALGO_API_DLL = SYNC.CALGO_API_DLL
CALGO_ROBOTS_DIR = SYNC.CALGO_ROBOTS
MT5_TERMINALS = [mql5_root for _, mql5_root, _ in SYNC.MT5_TERMINALS]
BOT_NAMES = list(SYNC.BOT_NAMES)


def test_ctrader_sources_synced_and_compile(tmp_path: Path) -> None:
    """All 5 cTrader bots exist in repo & cAlgo Robots dir and compile with 0 errors/warnings."""
    assert CSC_EXE.exists(), f"Missing csc.exe at {CSC_EXE}"
    assert CALGO_API_DLL.exists(), f"Missing cAlgo.API.dll at {CALGO_API_DLL}"

    shared_core = REPO / "ctrader" / "Shared" / "EdgeLabFundedSyncCfdCore.cs"
    shared_adapter = REPO / "ctrader" / "Shared" / "FundedSyncCTraderAdapter.cs"
    assert shared_core.exists() and shared_adapter.exists()

    for bot in BOT_NAMES:
        repo_bot_cs = REPO / "ctrader" / bot / bot / f"{bot}.cs"
        installed_bot_cs = CALGO_ROBOTS_DIR / bot / bot / f"{bot}.cs"
        installed_core = CALGO_ROBOTS_DIR / bot / bot / "EdgeLabFundedSyncCfdCore.cs"
        installed_adapter = CALGO_ROBOTS_DIR / bot / bot / "FundedSyncCTraderAdapter.cs"
        assert repo_bot_cs.exists(), f"Missing repo cBot: {repo_bot_cs}"
        assert installed_bot_cs.exists(), f"Missing synced cBot: {installed_bot_cs}"
        assert installed_core.exists() and installed_adapter.exists()

        out_dll = tmp_path / f"{bot}.dll"
        cmd = [
            str(CSC_EXE),
            "/nologo",
            "/target:library",
            "/warnaserror",
            "/nowarn:1685",
            f"/r:{CALGO_API_DLL}",
            f"/out:{out_dll}",
            str(installed_bot_cs),
            str(installed_adapter),
            str(installed_core),
        ]
        res = subprocess.run(cmd, capture_output=True)
        out_txt = (res.stdout + res.stderr).decode("cp850", errors="replace")
        assert res.returncode == 0, f"cBot compile failed ({bot}):\n{out_txt}"
        assert out_dll.exists() and out_dll.stat().st_size > 10_000


def test_cfd_core_sizing_news_and_dd_brake_smoke(tmp_path: Path) -> None:
    """Compile standalone C# test exercising PercentOfInitialBalance, FundedDdBrake, NewsGuard, and Tick/Bar feed."""
    shared_core = REPO / "ctrader" / "Shared" / "EdgeLabFundedSyncCfdCore.cs"
    harness = tmp_path / "SmokeCfdCore.cs"
    harness_exe = tmp_path / "SmokeCfdCore.exe"

    harness.write_text(
        r'''
using System;
using EdgeLabFundedSyncCfd;

public static class SmokeCfdCore
{
    public static int Main()
    {
        TimeZoneInfo nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time");
        TimeZoneInfo ctTz = FundedSyncMath.ResolveTz("Central Standard Time");
        var weights = FundedSyncMath.GetPresetWeights(FundedSyncPortfolioPreset.Core5_AltaConv);
        var flags = new bool[] { true, true, true, true, true, true, true };
        var coord = new PortfolioCoordinator(weights, flags)
        {
            SizingMode = FundedSyncRiskSizingMode.PercentOfInitialBalance,
            AccountMode = FundedSyncAccountMode.Evaluation,
            InitialBalanceUsd = 100000.0,
            CurrentBalanceUsd = 100000.0,
            HighWaterBalanceUsd = 100000.0,
            EvalRiskPct = 0.75,
            FundedRiskPct = 0.50,
            EnableFundedDdBrake = true,
            FundedDdBrakeThresholdPct = 5.0,
            FundedDdBrakeScale = 0.50,
            EnableNewsGuard = true,
            NewsBlackoutMinutes = 2,
            WarmupOnly = false
        };

        // 1. PercentOfInitialBalance sizing
        if (Math.Abs(coord.CurrentRisk1RUsd - 750.0) > 1e-6) return 11;

        // 2. Funded DD brake triggers when DD >= 5% in Funded mode
        coord.AccountMode = FundedSyncAccountMode.Funded;
        coord.CurrentBalanceUsd = 94500.0; // -5.5% from 100k HWM
        if (Math.Abs(coord.CurrentRisk1RUsd - 250.0) > 1e-6) return 12;

        // 3. Feed historical + live closed bar + tick without error
        DateTime c1 = new DateTime(2026, 10, 1, 13, 31, 0, DateTimeKind.Utc); // 09:31 NY
        var b1 = FundedSyncMath.BuildBarTimeContext(c1, 30500.0, 30510.0, 30495.0, 30505.0, 1200.0, nyTz, ctTz);
        coord.FeedHistoricalBar(b1);

        // 4. NewsGuard window at 10:00 ET (14:00 UTC in EDT -> 600 min ET)
        DateTime cNews = new DateTime(2026, 10, 1, 14, 0, 0, DateTimeKind.Utc);
        var bNews = FundedSyncMath.BuildBarTimeContext(cNews, 30505.0, 30508.0, 30501.0, 30502.0, 900.0, nyTz, ctTz);
        coord.FeedClosedBarAndFillAtNextOpen(bNews, 30502.0, 30503.0, bNews.CloseNy);
        if (!coord.NewsBlockedNow) return 13;

        // 5. EvaluateTick and off-news closed bar clear NewsBlockedNow
        DateTime offNewsUtc = new DateTime(2026, 10, 1, 14, 5, 10, DateTimeKind.Utc);
        coord.EvaluateTick(30505.0, 30506.0, offNewsUtc, nyTz);
        DateTime cOffNews = new DateTime(2026, 10, 1, 14, 5, 0, DateTimeKind.Utc);
        var bOff = FundedSyncMath.BuildBarTimeContext(cOffNews, 30505.0, 30507.0, 30503.0, 30506.0, 800.0, nyTz, ctTz);
        coord.FeedClosedBarAndFillAtNextOpen(bOff, 30506.0, 30507.0, bOff.CloseNy);
        if (coord.NewsBlockedNow) return 14;

        // 6. Directional short stop-entry does NOT fill prematurely when price stays above trigger
        var slTest = coord.Sleeves["V_nm25_noCap_mae30"];
        slTest.Enabled = true;
        slTest.WeightW5 = 1.0;
        coord.QueueStopEntry(slTest, -1, 30480.0, 20.0);
        coord.EvaluateTick(30500.0, 30501.0, new DateTime(2026, 10, 1, 14, 5, 20, DateTimeKind.Utc), nyTz);
        if (slTest.IsOpen || !slTest.HasPendingEntry) return 15;
        coord.EvaluateTick(30479.5, 30480.5, new DateTime(2026, 10, 1, 14, 5, 30, DateTimeKind.Utc), nyTz);
        if (!slTest.IsOpen || slTest.Side != -1) return 16;

        // 7. Roadmap CFD profile defaults (0.45% FTMO, 0.40% The5ers HS, FundedDdBrake @ 4.5%) & new presets
        var ftmo = CfdPropProfileDefaults.For(FundedSyncCfdPropProfile.FTMO_Swing_100K);
        if (Math.Abs(ftmo.EvalRiskPct - 0.45) > 1e-9 || !ftmo.EnableFundedDdBrake || Math.Abs(ftmo.FundedDdBrakeThresholdPct - 4.5) > 1e-9) return 17;
        var hs = CfdPropProfileDefaults.For(FundedSyncCfdPropProfile.The5ers_HighStakes_100K);
        if (Math.Abs(hs.EvalRiskPct - 0.40) > 1e-9 || !hs.EnableFundedDdBrake || Math.Abs(hs.FundedDdBrakeThresholdPct - 4.5) > 1e-9) return 18;
        var wC5R25 = FundedSyncMath.GetPresetWeights(FundedSyncPortfolioPreset.Core5_R25);
        if (Math.Abs(wC5R25["R_osc30_end660_ATR50"] - 1.802134) > 1e-6) return 19;
        var wSp = FundedSyncMath.GetPresetWeights(FundedSyncPortfolioPreset.SpeedEval_TOnly);
        if (Math.Abs(wSp["T_stop100_BE15R_calFalse"] - 1.0) > 1e-9 || wSp["R_osc30_end660_ATR50"] > 1e-9) return 20;
        var wEs = FundedSyncMath.GetPresetWeights(FundedSyncPortfolioPreset.ES_Core_US500);
        if (Math.Abs(wEs["N_d5_fbTrue_ATR25"] - (1.0 / 6.0)) > 1e-6 || wEs["SOMEOD_ext_NQ"] > 1e-9) return 21;

        Console.WriteLine("SMOKE_OK");
        return 0;
    }
}
''',
        encoding="utf-8",
    )

    comp = subprocess.run(
        [str(CSC_EXE), "/nologo", "/warnaserror", "/nowarn:1685", f"/out:{harness_exe}", str(harness), str(shared_core)],
        capture_output=True,
    )
    assert comp.returncode == 0, comp.stdout.decode("cp850", errors="replace") + comp.stderr.decode("cp850", errors="replace")

    run = subprocess.run([str(harness_exe)], capture_output=True, text=True)
    assert run.returncode == 0, f"Smoke exe rc={run.returncode} stdout={run.stdout} stderr={run.stderr}"
    assert "SMOKE_OK" in run.stdout


def test_mt5_sources_headers_and_compiled_ex5_present() -> None:
    """All 6 MQL5 EAs, 3 shared headers, and compiled .ex5 binaries exist across discovered terminals."""
    headers = ["FS_TypesAndTime.mqh", "FS_ModuleEngines.mqh", "FS_CoordinatorAndAdapter.mqh"]
    for h in headers:
        assert (REPO / "mt5" / "Include" / "EdgeLabFundedSync" / h).exists(), f"Missing repo header {h}"
    for bot in BOT_NAMES:
        assert (REPO / "mt5" / "Experts" / "EdgeLabFundedSync" / f"{bot}.mq5").exists(), f"Missing repo EA {bot}"

    assert len(MT5_TERMINALS) >= 1, "Expected at least one discovered MT5 terminal MQL5 directory"
    for term_mql5 in MT5_TERMINALS:
        for h in headers:
            assert (term_mql5 / "Include" / "EdgeLabFundedSync" / h).exists(), f"Missing synced header {h} in {term_mql5}"
        for bot in BOT_NAMES:
            mq5 = term_mql5 / "Experts" / "EdgeLabFundedSync" / f"{bot}.mq5"
            ex5 = term_mql5 / "Experts" / "EdgeLabFundedSync" / f"{bot}.ex5"
            assert mq5.exists(), f"Missing {mq5}"
            assert ex5.exists() and ex5.stat().st_size > 20_000, f"Missing/tiny compiled {ex5}"


def test_tick_phase_shift_resampler_and_chunk_continuity() -> None:
    """Verify exact shifted 1m OHLCV buckets and zero discrepancy across arbitrary RG/chunk boundaries."""
    base_ns = int(np.datetime64("2026-10-01T13:30:00", "ns").astype("int64"))
    s = 1_000_000_000
    # Synthetic ticks spanning :30:05, :30:20, :30:40, :31:10, :31:25, :31:50
    ts = np.array(
        [
            base_ns + 5 * s,
            base_ns + 20 * s,
            base_ns + 40 * s,
            base_ns + 70 * s,
            base_ns + 85 * s,
            base_ns + 110 * s,
        ],
        dtype=np.int64,
    )
    px = np.array([100.0, 102.0, 99.0, 101.0, 105.0, 98.0], dtype=np.float64)
    vol = np.array([10.0, 15.0, 5.0, 20.0, 10.0, 25.0], dtype=np.float64)

    res_full = BPS.resample_ticks_to_shifted_m1(ts, px, vol, deltas_s=(0, 15, 30), chunk_size=None)
    # Chunk splits right across buckets!
    for cs in (1, 2, 3):
        res_chunk = BPS.resample_ticks_to_shifted_m1(ts, px, vol, deltas_s=(0, 15, 30), chunk_size=cs)
        for d in (0, 15, 30):
            assert res_full[d].equals(res_chunk[d]), f"Chunk continuity failed for delta={d}, chunk_size={cs}"

    # Verify delta=15s exact OHLCV grouping:
    # bucket 0 [13:30:15 .. 13:31:15): ticks at +20(102,15), +40(99,5), +70(101,20) -> O=102,H=102,L=99,C=101,V=40
    # Wait: tick at +5s falls in prior shifted bucket [13:29:15 .. 13:30:15)!
    df15 = res_full[15]
    assert len(df15) == 3
    assert df15.iloc[0]["o"] == 100.0 and df15.iloc[0]["v"] == 10.0
    assert df15.iloc[1]["o"] == 102.0 and df15.iloc[1]["h"] == 102.0 and df15.iloc[1]["l"] == 99.0
    assert df15.iloc[1]["c"] == 101.0 and df15.iloc[1]["v"] == 40.0
    assert df15.iloc[2]["o"] == 105.0 and df15.iloc[2]["c"] == 98.0 and df15.iloc[2]["v"] == 35.0


def test_research_deliverables_present_and_nonempty() -> None:
    """Generated reports, CSVs, and dark charts from phase-shift & satellite suites exist cleanly."""
    ps_dir = REPO / "docs" / "research" / "fundedsync_bar_phase_shift_20261123"
    sat_dir = REPO / "docs" / "research" / "fundedsync_satelites_prop_20261123"

    expected_ps = [
        "RESULTADO.md",
        "subminute_phase_summary.csv",
        "subminute_phase_by_module.csv",
        "multiminute_shift_summary.csv",
        "htf_phase_someod.csv",
        "cfd_usatech_spread_and_comparison.csv",
        "bar_phase_shift_subminute_0_55s.png",
        "bar_phase_shift_multiminute_htf.png",
    ]
    for f in expected_ps:
        p = ps_dir / f
        assert p.exists() and p.stat().st_size > 100, f"Missing/empty phase shift file: {p}"

    expected_sat = [
        "RESULTADO.md",
        "correlacion_satelites.csv",
        "mc_arquitecturas_satelites.csv",
        "personal_blend_resumen.csv",
        "satelites_monetizacion_prop.png",
    ]
    for f in expected_sat:
        p = sat_dir / f
        assert p.exists() and p.stat().st_size > 100, f"Missing/empty satellites file: {p}"

    rm_dir = REPO / "docs" / "research" / "fundedsync_roadmap_ecosistema_20261123"
    expected_rm = [
        "RESULTADO.md",
        "ROADMAP_OPERATIVO_MULTIFRENTE.md",
        "etapa1_overnight_y_swaps_2026.csv",
        "etapa2_frecuencia_estructural_anti_overfit.csv",
        "etapa3_validacion_cruzada_ciclo_vida.csv",
        "etapa4_ecosistema_multifrente_mc.csv",
        "frecuencia_estructural_y_overnight_2026.png",
        "ecosistema_paralelo_roadmap_frontera.png",
    ]
    for f in expected_rm:
        p = rm_dir / f
        assert p.exists() and p.stat().st_size > 100, f"Missing/empty roadmap file: {p}"

    hft_dir = REPO / "docs" / "research" / "auditoria_bots_hftcode_20261124"
    for f in [
        "RESULTADO.md",
        "resumen_particiones_hftcode.csv",
        "defectos_codigo_auditoria.csv",
        "auditoria_bots_hftcode_curvas.png",
    ]:
        p = hft_dir / f
        assert p.exists() and p.stat().st_size > 100, f"Missing/empty HFTCode audit file: {p}"

    # Verify MQL5 EMPTY_VALUE (DBL_MAX) guard exists in FS_TypesAndTime.mqh
    types_mqh = (REPO / "mt5" / "Include" / "EdgeLabFundedSync" / "FS_TypesAndTime.mqh").read_text(encoding="utf-8")
    assert "FsIsValidPos" in types_mqh and "EMPTY_VALUE" in types_mqh
