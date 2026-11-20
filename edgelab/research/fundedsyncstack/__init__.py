"""Paquete de investigacion y simulacion cuantitativa de las 15 sub-estrategias NQ/MNQ
identificadas en FUNDEDSYNCSTACK (traduccion 1:1 a Python y motor de cartera).

Sub-estrategias incluidas:
- A1  : Absorb 1m (divergencia precio/delta en 1m ETH + filtro ADX + sesion 18:01..15:35 CT)
- A20 : Absorb 20m (divergencia precio/delta en 20m ETH + filtro ADX + EMA + cooldown)
- F   : Flat (fade en rango plano de ADX sobre 5m ETH)
- S   : Sweep (barrido de extremos previos + volumen alto + mecha en 3m ETH)
- P   : NqPullback (ruptura ORB + retesteo de VWAP + pivots estrictos en 1m ETH)
- C   : CapstoneGap (continuacion de gap RTH contenido en el rango previo sobre 1m US STOCK)
- V   : VaultBreak (ruptura de banda de ruido diaria + VWAP en 5m RTH)
- O   : Overnight (tendencia diaria + sizing inverso a volatilidad nocturna 15:00/17:01 -> 08:30 CT)
- W   : VwapCross (cruce Long-only sobre VWAP RTH en 1m ETH)
- N   : NDayLong (ruptura alcista de N dias previos con filtro de aceptacion y eficiencia en 1m ETH)
- T   : FtmOrb (ORB 15m 09:30-09:45 ET + clasificador KNN K=15 14D con shadow pairs y refinamiento en 2 etapas)
- R   : AtrPhase (cambio de fase de ratio ATR corto/largo en 10m ETH)
- Z   : ZetaTrendDay (detector de dia de tendencia intradia en 26 buckets de 15m RTH)
- E   : EmaDivergence (divergencia z-score de volumen/rango/CVD + cruce EMA 9/11/45 en 15m ETH)
- Q   : Rampart5Minute (ruptura de canal 48 barras en 5m ETH con filtro EMA 100/220 y sizing dinamico)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

import pandas as pd

from .base_series import (
    build_multi_series,
    load_m1_data,
    nt_adx,
    nt_atr,
    nt_ema,
    nt_sma,
)
from .contracts import (
    POINT_VALUE_MNQ,
    POINT_VALUE_NQ,
    TICK_SIZE_NQ,
    TRADE_COLUMNS,
    BarSeries,
    MultiSeriesContext,
    TradeRecord,
    round_tick,
    trades_to_df,
)
from .modulos_a1_a20_f_s import (
    Absorb1mConfig,
    Absorb20mConfig,
    FabioConfig,
    SwasConfig,
    run_a1,
    run_a20,
    run_f,
    run_s,
    senales_a1,
    senales_a20,
    senales_f,
    senales_s,
)
A1Config = Absorb1mConfig
A20Config = Absorb20mConfig
FlatConfig = FabioConfig
SweepConfig = SwasConfig
from .modulos_p_c_v_o import (
    CapstoneConfig,
    OvernightConfig,
    PullbackConfig,
    VaultConfig,
    run_c,
    run_o,
    run_p,
    run_v,
    senales_c,
    senales_o,
    senales_p,
    senales_v,
)
from .modulos_r_z_e_q import (
    AtrPhaseConfig,
    EmaDivConfig,
    RampartConfig,
    ZetaConfig,
    run_e,
    run_q,
    run_r,
    run_z,
    senales_e,
    senales_q,
    senales_r,
    senales_z,
)
from .modulos_w_n_t import (
    FTM_CONTRACT_ROLL_EXCLUSION_DATE_KEYS,
    FTM_DEGRADED_DATA_EXCLUSION_DATE_KEYS,
    FTM_MODEL_FEATURE_NAMES,
    FtmConfig,
    NDayConfig,
    VwapCrossConfig,
    run_n,
    run_t,
    run_w,
    senales_n,
    senales_t,
    senales_w,
)
from .motor_cartera import (
    BUNDLE_A_TAGS,
    BUNDLE_B_TAGS,
    HALF_DRAWDOWN_ROTATION_OFFSETS,
    MODULE_SIGNAL_BIP,
    STRATEGY_SELECTION_TAG,
    TAGS_ALL,
    AccountStage,
    BundleSelection,
    EntryTiming,
    EvaluationSizingMode,
    ExecMode,
    ExecutionIntentKind,
    ModuleState,
    PortfolioConfig,
    PortfolioEngine,
    RollingValues,
    SizingProfile,
    StrategySelection,
    simular_cartera,
)

MODULOS: Dict[str, Callable[..., pd.DataFrame]] = {
    "A1": run_a1,
    "A20": run_a20,
    "F": run_f,
    "S": run_s,
    "P": run_p,
    "C": run_c,
    "V": run_v,
    "O": run_o,
    "W": run_w,
    "N": run_n,
    "T": run_t,
    "R": run_r,
    "Z": run_z,
    "E": run_e,
    "Q": run_q,
}

SENALES: Dict[str, Callable[..., pd.DataFrame]] = {
    "A1": senales_a1,
    "A20": senales_a20,
    "F": senales_f,
    "S": senales_s,
    "P": senales_p,
    "C": senales_c,
    "V": senales_v,
    "O": senales_o,
    "W": senales_w,
    "N": senales_n,
    "T": senales_t,
    "R": senales_r,
    "Z": senales_z,
    "E": senales_e,
    "Q": senales_q,
}

CONFIG_CLASSES: Dict[str, Any] = {
    "A1": A1Config,
    "A20": A20Config,
    "F": FlatConfig,
    "S": SweepConfig,
    "P": PullbackConfig,
    "C": CapstoneConfig,
    "V": VaultConfig,
    "O": OvernightConfig,
    "W": VwapCrossConfig,
    "N": NDayConfig,
    "T": FtmConfig,
    "R": AtrPhaseConfig,
    "Z": ZetaConfig,
    "E": EmaDivConfig,
    "Q": RampartConfig,
}


def _ensure_ms(
    data_or_ms: Any,
    *,
    start: Any = None,
    end: Any = "2026-10-01",
    tz_input: str = "UTC",
    allow_sellado: bool = False,
) -> MultiSeriesContext:
    if isinstance(data_or_ms, MultiSeriesContext):
        return data_or_ms
    df = load_m1_data(
        data_or_ms,
        start=start,
        end=end,
        tz_input=tz_input,
        allow_sellado=allow_sellado,
        end_inclusive=False,
    )
    return build_multi_series(df, tz_input="UTC", allow_sellado=allow_sellado)


def correr_modulo(
    tag: str,
    data_or_ms: Any,
    qty: Optional[int] = None,
    cfg: Any = None,
    *,
    start: Any = None,
    end: Any = "2026-10-01",
    tz_input: str = "UTC",
    allow_sellado: bool = False,
    **cfg_overrides: Any,
) -> pd.DataFrame:
    """Ejecuta un modulo individual (`A1`..`Q`) sobre `MultiSeriesContext` o datos M1."""
    key = tag.strip().upper()
    if key not in MODULOS:
        raise ValueError(f"Modulo desconocido '{tag}'. Disponibles: {list(MODULOS.keys())}")
    ms = _ensure_ms(
        data_or_ms, start=start, end=end, tz_input=tz_input, allow_sellado=allow_sellado
    )
    runner = MODULOS[key]
    if cfg is None and cfg_overrides:
        cfg = CONFIG_CLASSES[key](**cfg_overrides)
    if qty is None:
        return runner(ms, cfg=cfg) if cfg is not None else runner(ms)
    return runner(ms, qty=qty, cfg=cfg) if cfg is not None else runner(ms, qty=qty)


def correr_todos(
    data_or_ms: Any,
    *,
    incluir_cartera: bool = True,
    portfolio_config: Optional[PortfolioConfig] = None,
    module_configs: Optional[Mapping[str, Any]] = None,
    start: Any = None,
    end: Any = "2026-10-01",
    tz_input: str = "UTC",
    allow_sellado: bool = False,
) -> Dict[str, Any]:
    """Ejecuta los 15 modulos individualmente y opcionalmente la cartera consolidada."""
    ms = _ensure_ms(
        data_or_ms, start=start, end=end, tz_input=tz_input, allow_sellado=allow_sellado
    )
    por_modulo: Dict[str, pd.DataFrame] = {}
    resumen_rows = []
    for tag, fn in MODULOS.items():
        m_cfg = module_configs.get(tag) if module_configs else None
        df_t = fn(ms, cfg=m_cfg) if m_cfg is not None else fn(ms)
        por_modulo[tag] = df_t
        n_tr = len(df_t)
        net_usd = float(df_t["pnl_usd"].sum()) if n_tr else 0.0
        gp = float(df_t.loc[df_t["pnl_usd"] > 0, "pnl_usd"].sum()) if n_tr else 0.0
        gl = float(-df_t.loc[df_t["pnl_usd"] < 0, "pnl_usd"].sum()) if n_tr else 0.0
        pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
        win_rate = float((df_t["pnl_usd"] > 0).mean() * 100.0) if n_tr else 0.0
        resumen_rows.append(
            {
                "module": tag,
                "trades": n_tr,
                "win_rate_pct": round(win_rate, 2),
                "net_pnl_usd": round(net_usd, 2),
                "gross_profit_usd": round(gp, 2),
                "gross_loss_usd": round(gl, 2),
                "profit_factor": round(pf, 3) if pf != float("inf") else float("inf"),
            }
        )
    resumen_df = pd.DataFrame(resumen_rows)
    all_trades_df = (
        pd.concat([df for df in por_modulo.values() if len(df) > 0], ignore_index=True)
        if any(len(df) > 0 for df in por_modulo.values())
        else trades_to_df([])
    )
    if len(all_trades_df) > 0:
        all_trades_df = all_trades_df.sort_values(
            ["entry_time_utc", "exit_time_utc", "module"], kind="mergesort"
        ).reset_index(drop=True)

    cartera = None
    if incluir_cartera:
        cartera = simular_cartera(ms, por_modulo, config=portfolio_config)

    return {
        "ms": ms,
        "por_modulo": por_modulo,
        "resumen_df": resumen_df,
        "trades_df": all_trades_df,
        "cartera": cartera,
    }


__all__ = [
    "MODULOS",
    "SENALES",
    "CONFIG_CLASSES",
    "correr_modulo",
    "correr_todos",
    "simular_cartera",
    "load_m1_data",
    "build_multi_series",
    "nt_sma",
    "nt_ema",
    "nt_atr",
    "nt_adx",
    "BarSeries",
    "MultiSeriesContext",
    "TradeRecord",
    "TRADE_COLUMNS",
    "TICK_SIZE_NQ",
    "POINT_VALUE_NQ",
    "POINT_VALUE_MNQ",
    "round_tick",
    "trades_to_df",
    "PortfolioConfig",
    "PortfolioEngine",
    "ModuleState",
    "RollingValues",
    "A1Config",
    "A20Config",
    "FlatConfig",
    "SweepConfig",
    "PullbackConfig",
    "CapstoneConfig",
    "VaultConfig",
    "OvernightConfig",
    "VwapCrossConfig",
    "NDayConfig",
    "FtmConfig",
    "AtrPhaseConfig",
    "ZetaConfig",
    "EmaDivConfig",
    "RampartConfig",
    "run_a1",
    "run_a20",
    "run_f",
    "run_s",
    "run_p",
    "run_c",
    "run_v",
    "run_o",
    "run_w",
    "run_n",
    "run_t",
    "run_r",
    "run_z",
    "run_e",
    "run_q",
    "senales_a1",
    "senales_a20",
    "senales_f",
    "senales_s",
    "senales_p",
    "senales_c",
    "senales_v",
    "senales_o",
    "senales_w",
    "senales_n",
    "senales_t",
    "senales_r",
    "senales_z",
    "senales_e",
    "senales_q",
]
