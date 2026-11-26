"""Pruebas unitarias e invariantes para despliegue integrado FUNDEDSYNC y Multi-Prop Firm."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import fundedsync_integracion_multiprop as IMP
import sync_ctrader_mt5_bots as SYNC


def test_simular_trade_en_ticks_be_causal_y_duracion():
    # Minuto 0: sube hasta +1.6 R (16 pts vs sl=10); BE (+1.5R) debe activarse recien al cambiar al minuto 1
    base_ns = 1_760_000_000_000_000_000
    t_m0 = (base_ns // 60_000_000_000) * 60_000_000_000
    ts = np.array([
        t_m0 + 1_000_000_000,
        t_m0 + 20_000_000_000,
        t_m0 + 40_000_000_000,       # aun minuto 0: vuelve a +0.2R, NO debe saltar BE todavia
        t_m0 + 65_000_000_000,       # minuto 1: se promueve BE a entry (100.0)
        t_m0 + 75_000_000_000,       # toca 99.75 <= 100.0 -> salida exacta en BE
        t_m0 + 120_000_000_000,
    ], dtype=np.int64)
    px = np.array([100.0, 116.0, 102.0, 101.0, 99.75, 95.0], dtype=np.float64)

    sim = IMP.simular_trade_en_ticks(
        ts, px, t_m0, t_m0 + 180_000_000_000, side=1, sl_pts=10.0, m1_entry_px=100.0, be_trig_r=1.5
    )
    assert sim["ok"] == 1.0
    assert sim["motivo"] == 1.0
    assert abs(sim["pnl_pts"] - (-0.25)) < 1e-6
    assert abs(sim["dur_s"] - 74.0) < 1e-6


def test_colisiones_y_netting_intradia():
    # Dos trades simultaneos opuestos en la misma sesion con cierre+apertura coincidentes
    t0 = 1_760_000_000_000_000_000
    tr_df = pd.DataFrame([
        {
            "stream": "A::NQ", "fecha_int": 20250110, "en_ns": t0, "ex_ns": t0 + 600_000_000_000,
            "side": 1, "riesgo_pts": 50.0, "R_bruto": 1.0, "R_neto_mini": 0.97,
            "mae_pts": 40.0, "mfe_pts": 60.0, "w_eff": 1.0, "R_eff": 0.97,
        },
        {
            "stream": "B::NQ", "fecha_int": 20250110, "en_ns": t0, "ex_ns": t0 + 600_000_000_000,
            "side": -1, "riesgo_pts": 50.0, "R_bruto": 0.2, "R_neto_mini": 0.17,
            "mae_pts": 40.0, "mfe_pts": 30.0, "w_eff": 1.0, "R_eff": 0.17,
        },
    ])
    ses = [20250110]
    audit = IMP.auditar_colisiones_opuestas(tr_df, ses, 450.0, 100, True, 1.545, 0.90)
    assert audit["n_trades_en_colision"] >= 1
    assert audit["pct_dias_colision"] == 100.0
    assert audit["politicas"]["veto_opuesto"]["n_trades"] == 1

    P_ind, LO_ind, _, _ = IMP.construir_serie_intradia_prop_v2(
        tr_df, ses, 450.0, 100, True, 1.545, 0.90, 1.0, politica_colision="independiente"
    )
    P_net, LO_net, _, _ = IMP.construir_serie_intradia_prop_v2(
        tr_df, ses, 450.0, 100, True, 1.545, 0.90, 1.0, politica_colision="netting"
    )
    assert P_net[0] > P_ind[0]
    assert abs(LO_net[0]) < abs(LO_ind[0])


def test_multiprop_intraday_sin_doble_conteo_y_billing_y_cero():
    # Verificar que eval_dd_kind=1 (intraday) NO doble-cuenta bal + hi del mismo dia
    P_ev = np.array([1000.0, 500.0, 0.0], dtype=np.float64)
    LO_ev = np.array([0.0, 0.0, -1100.0], dtype=np.float64)
    HI_ev = np.array([1000.0, 1200.0, 0.0], dtype=np.float64)
    j_seq = np.array([[0, 1, 2]], dtype=np.int64)

    base_cfg = {
        "eval_fee_sim": 100.0, "activation_fee": 0.0, "billing_mode": "one_time",
        "profit_target": 5000.0, "max_loss": 2000.0, "eval_drawdown_kind": "intraday_trailing",
        "funded_drawdown_kind": "eod_trailing", "lock_at_profit": 4000.0,
        "eval_dll": 0.0, "funded_dll": 0.0, "eval_min_days": 1, "eval_consistency": 0.0,
        "eval_cap_cons": False, "funded_consistency": 0.0, "payout_mode": "win_days",
        "payout_min_days": 5, "payout_day_min_profit": 150.0, "payout_min_profit": 1.0,
        "payout_min_amount": 250.0, "payout_buffer_post": 0.0, "payout_lock_buffer": 0.0,
        "payout_fraction": 0.5, "payout_basis": "total", "payout_caps": [3000.0],
        "payout_split": 0.9, "payout_max_count": 5, "close_after_max_payouts": True,
        "max_eval": 1, "max_funded": 1, "max_total": 2, "stagger_days": 1,
    }
    kw = IMP._norm_multiprop_cfg(base_cfg)
    _, c24, _, _, _, _, comp24, _ = IMP._trayectoria_multiprop_numba(
        P_ev, LO_ev, HI_ev, P_ev, LO_ev, HI_ev, j_seq, **kw
    )
    # Dia 0: bal=1000, peak=1000 -> piso=-1000. Dia 1: peak=1000+1200=2200 (NO 1500+1200=2700!) -> piso=+200, bal=1500.
    # Dia 2: bal + LO = 1500 - 1100 = +400 > +200 -> sobrevive! Solo 1 eval comprada.
    assert comp24[0] == 1
    assert c24[0] == -100.0

    # Billing monthly cobra cuota adicional al dia 21 en eval, one_time no
    P_flat = np.full(25, 10.0, dtype=np.float64)
    Z = np.zeros(25, dtype=np.float64)
    j25 = np.arange(25, dtype=np.int64).reshape(1, 25)
    kw_one = IMP._norm_multiprop_cfg({**base_cfg, "billing_mode": "one_time"})
    kw_mon = IMP._norm_multiprop_cfg({**base_cfg, "billing_mode": "monthly"})
    _, c_one, _, _, _, _, _, _ = IMP._trayectoria_multiprop_numba(P_flat, Z, Z, P_flat, Z, Z, j25, **kw_one)
    _, c_mon, _, _, _, _, _, _ = IMP._trayectoria_multiprop_numba(P_flat, Z, Z, P_flat, Z, Z, j25, **kw_mon)
    assert abs((c_one[0] - c_mon[0]) - 100.0) < 1e-6

    # Stagger spacing: stagger=5 limita a 1 compra en primeros 4 dias vs stagger=1 (4 compras)
    j4 = np.arange(4, dtype=np.int64).reshape(1, 4)
    kw_s1 = IMP._norm_multiprop_cfg({**base_cfg, "max_eval": 5, "max_total": 5, "stagger_days": 1})
    kw_s5 = IMP._norm_multiprop_cfg({**base_cfg, "max_eval": 5, "max_total": 5, "stagger_days": 5})
    _, _, _, _, _, _, comp_s1, _ = IMP._trayectoria_multiprop_numba(P_flat[:4], Z[:4], Z[:4], P_flat[:4], Z[:4], Z[:4], j4, **kw_s1)
    _, _, _, _, _, _, comp_s5, _ = IMP._trayectoria_multiprop_numba(P_flat[:4], Z[:4], Z[:4], P_flat[:4], Z[:4], Z[:4], j4, **kw_s5)
    assert comp_s1[0] == 4 and comp_s5[0] == 1

    # Regimen media cero: expectativa negativa con drift cero simetrico en 150K
    rng = np.random.default_rng(123)
    steps = rng.choice([-450.0, 450.0], size=200)
    j_200 = np.tile(np.arange(200, dtype=np.int64), (40, 1))
    kw_zero = IMP._norm_multiprop_cfg({
        **base_cfg, "eval_fee_sim": 250.0, "profit_target": 9000.0, "max_loss": 4500.0,
        "max_eval": 5, "max_funded": 5, "max_total": 10, "stagger_days": 3,
    })
    c12_z, _, _, _, _, _, _, fl_z = IMP._trayectoria_multiprop_numba(
        steps, np.minimum(steps, 0.0), np.maximum(steps, 0.0),
        steps, np.minimum(steps, 0.0), np.maximum(steps, 0.0),
        j_200, **kw_zero
    )
    assert float(np.mean(c12_z)) < 0.0

    # Agregar arquitectura multifirma preserva suma de flujos
    r_stub = {"firm": "F", "account_size": 150000, "retiros_12m": 1.0, "retiros_24m": 2.0, "fee_sim_usd": 200.0}
    arq = IMP.agregar_arquitectura_multifirma("T", "Test", [(r_stub, 1.0, fl_z), (r_stub, 0.5, fl_z)], "REP", "cero_0")
    assert arq["retiros_12m"] == 1.5


def test_someod_m1_paridad_y_cs_nt8_valido(tmp_path):
    import subprocess

    strat_dir = ROOT / "nt8/strategies"
    expected_classes = {
        "EdgeLabFundedSyncCore.cs": "public sealed class PortfolioCoordinator",
        "EdgeLabFundedSyncPortfolio.cs": "public class EdgeLabFundedSyncPortfolio : Strategy",
        "EdgeLabFundedSyncCore6.cs": "public class EdgeLabFundedSyncCore6 : Strategy",
        "EdgeLabFundedSyncCore5AltaConv.cs": "public class EdgeLabFundedSyncCore5AltaConv : Strategy",
        "EdgeLabFundedSyncSnipersRZ.cs": "public class EdgeLabFundedSyncSnipersRZ : Strategy",
        "EdgeLabFundedSyncSingleModule.cs": "public class EdgeLabFundedSyncSingleModule : Strategy",
    }

    cs_paths = []
    for fname, sig in expected_classes.items():
        p = strat_dir / fname
        assert p.exists(), f"Falta archivo NT8: {p}"
        raw_bytes = p.read_bytes()
        assert b"\n" not in raw_bytes.replace(b"\r\n", b""), f"Se requiere formato CRLF estricto en {fname}"
        txt = raw_bytes.decode("ascii")
        assert "#region NinjaScript generated code" not in txt
        assert sig in txt
        assert txt.count("{") == txt.count("}")
        assert txt.count("(") == txt.count(")")
        cs_paths.append(str(p))

    portfolio_txt = (strat_dir / "EdgeLabFundedSyncPortfolio.cs").read_text(encoding="ascii")
    for req in (
        "R_osc30_end660_ATR50", "Z_b15_e20_eff40_ATR50", "T_stop100_BE15R_calFalse",
        "V_nm25_noCap_mae30", "W_slope_allowReFalse_ATR25", "N_d5_fbTrue_ATR25", "SOMEOD_ext_NQ",
        "HardFlattenHHMM_ET", "MaxOpenR", "CollisionPolicy", "EvalDailyCapUSD", "DailyLossLimitUSD",
        "SMA of True Range", "500 trading days",
    ):
        assert req in portfolio_txt

    core_txt = (strat_dir / "EdgeLabFundedSyncCore.cs").read_text(encoding="ascii")
    for preset in (
        "P_OPT_SF_v2", "P_OPT_Core6", "P_OPT_SF_SinW",
        "Core5_AltaConv", "Tier1_Snipers_RZ", "Tier23_Flow_TVNS",
    ):
        assert preset in core_txt

    csc = SYNC.CSC_EXE
    nt_core = SYNC.NT8_CORE_DLL
    nt_gui = SYNC.NT8_GUI_DLL
    nt_cust = SYNC.NT8_CUSTOM_DLL
    wpf_dir = SYNC.WPF_DIR
    if csc.exists() and nt_core.exists() and nt_gui.exists() and nt_cust.exists():
        out_dll = tmp_path / "EdgeLabFundedSyncNt8Test.dll"
        cmd = [
            str(csc),
            "/nologo",
            "/target:library",
            "/warnaserror",
            f"/out:{out_dll}",
            "/r:System.dll",
            "/r:System.Core.dll",
            "/r:System.ComponentModel.DataAnnotations.dll",
            "/r:System.Xml.dll",
            f"/r:{wpf_dir / 'PresentationCore.dll'}",
            f"/r:{wpf_dir / 'PresentationFramework.dll'}",
            f"/r:{wpf_dir / 'WindowsBase.dll'}",
            f"/r:{nt_core}",
            f"/r:{nt_gui}",
            f"/r:{nt_cust}",
            *cs_paths,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert res.returncode == 0, f"csc /warnaserror fallo:\n{res.stdout}\n{res.stderr}"
        assert out_dll.exists()
