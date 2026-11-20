"""Prueba integral (end-to-end) del paquete Python `fundedsyncstack_traducido` sobre datos M1
pre-holdout (< 2026-10-01) de `NQ_M1_dukas-M1-.csv`.

Verifica:
1. Carga causal y guardia anti-holdout (`< 2026-10-01`).
2. Construccion de las 10 series (`bip1..bip10`) y los 4 indicadores NT8 (`SMA`, `EMA`, `ATR`, `ADX`).
3. Ejecucion sin errores de los 15 modulos (`A1`, `A20`, `F`, `S`, `P`, `C`, `V`, `O`, `W`, `N`, `T`, `R`, `Z`, `E`, `Q`)
   y validacion estricta del contrato de 16 columnas (`TRADE_COLUMNS`).
4. Verificacion explicita de `VaultBreak` (`V`) con `daily_atr_length=252` (default) y `daily_atr_length=60`,
   y de `Overnight` (`O`) con `qty=1` (override de margen cuando NQ > 25,000) vs default.
5. Simulacion consolidada de cartera (`simular_cartera`) comparando el Libro Mayor Virtual vs Netting en Broker.
"""
from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from edgelab.research.fundedsyncstack import (
        MODULOS, SENALES, TRADE_COLUMNS, VaultConfig, build_multi_series, correr_modulo, correr_todos, load_m1_data, simular_cartera
    )
except ImportError:
    from python import (  # noqa: E402
    MODULOS,
    SENALES,
    TRADE_COLUMNS,
    VaultConfig,
    build_multi_series,
    correr_modulo,
    correr_todos,
    load_m1_data,
    simular_cartera,
)

CSV_PATH = Path(r"C:\StrategyQuantX145\user\mcp-work\edgelab_m1\NQ_M1_dukas-M1-.csv")


def main() -> int:
    t0 = time.perf_counter()
    print("=== 1. Verificando guardia anti-holdout (debe rechazar rutas con 'sellado') ===")
    try:
        load_m1_data(r"C:\EdgeLab\sellado\NQ_20261029_ticks.parquet")
        raise AssertionError("Debio lanzar ValueError ante una ruta con 'sellado'")
    except ValueError as e:
        print(f"  [PASS] Guardia anti-holdout activa: {e}")

    print("\n=== 2. Cargando datos M1 pre-holdout (2025-06-01 .. 2026-09-30 < 2026-10-01) ===")
    assert CSV_PATH.exists(), f"No existe {CSV_PATH}"
    df_m1 = load_m1_data(CSV_PATH, start="2025-06-01", end="2026-10-01", tz_input="UTC")
    max_ts = pd.to_datetime(df_m1["ts_ns"].max(), unit="ns", utc=True)
    min_ts = pd.to_datetime(df_m1["ts_ns"].min(), unit="ns", utc=True)
    print(f"  [PASS] Barras M1 cargadas: {len(df_m1):,} | Rango UTC: {min_ts} -> {max_ts}")
    assert max_ts < pd.Timestamp("2026-10-01 00:00:00", tz="UTC"), "Violacion de frontera pre-holdout!"

    print("\n=== 3. Construyendo MultiSeriesContext (bip1..bip10) ===")
    t_ms = time.perf_counter()
    ms = build_multi_series(df_m1, tz_input="UTC")
    print(
        f"  [PASS] MultiSeriesContext construido en {time.perf_counter() - t_ms:.2f}s: "
        f"bip1={len(ms.bip1.close):,}, bip2={len(ms.bip2.close):,}, bip3={len(ms.bip3.close):,}, "
        f"bip4={len(ms.bip4.close):,}, bip5={len(ms.bip5.close):,}, bip6={len(ms.bip6.close):,}, "
        f"bip7={len(ms.bip7.close):,}, bip8={len(ms.bip8.close):,}, bip9={len(ms.bip9.close):,}, bip10={len(ms.bip10.close):,}"
    )

    print("\n=== 4. Ejecutando los 15 sub-modulos y verificando contrato de 16 columnas ===")
    res = correr_todos(ms, incluir_cartera=True)
    resumen_df = res["resumen_df"]
    print(resumen_df.to_string(index=False))

    for tag in MODULOS:
        df_mod = res["por_modulo"][tag]
        assert list(df_mod.columns) == TRADE_COLUMNS, f"Columnas invalidas en {tag}: {list(df_mod.columns)}"
        if len(df_mod) > 0:
            assert (df_mod["exit_time_utc"] >= df_mod["entry_time_utc"]).all(), f"Orden temporal invalido en {tag}"
            assert np.isfinite(df_mod["pnl_usd"]).all(), f"NaN en pnl_usd de {tag}"

    print("\n=== 5. Verificando VaultBreak (V) con V_DailyAtrLength=60 y Overnight (O) con qty=1 ===")
    df_v60 = correr_modulo("V", ms, daily_atr_length=60)
    df_o1 = correr_modulo("O", ms, qty=1)
    print(f"  [PASS] VaultBreak (V, atr=60): {len(df_v60)} trades | Net USD: {df_v60['pnl_usd'].sum():,.2f}")
    print(f"  [PASS] Overnight (O, qty=1 override): {len(df_o1)} trades | Net USD: {df_o1['pnl_usd'].sum():,.2f}")
    assert len(df_v60) > 0, "VaultBreak con daily_atr_length=60 debe generar trades en 16 meses"
    assert len(df_o1) > 0, "Overnight con qty=1 debe generar trades en 16 meses"

    print("\n=== 6. Verificando Cartera Consolidada (Virtual Ledger vs Broker Netting) ===")
    cartera = res["cartera"]
    assert cartera is not None
    comp = cartera["comparison"]
    for k, v in comp.items():
        print(f"  {k}: {v}")
    assert abs(comp["gross_pnl_diff_usd"]) < 1e-6, f"Diferencia de PnL bruto excesiva: {comp['gross_pnl_diff_usd']}"

    elapsed = time.perf_counter() - t0
    print(f"\nALL END-TO-END TRANSLATION TESTS PASSED IN {elapsed:.2f}s!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

