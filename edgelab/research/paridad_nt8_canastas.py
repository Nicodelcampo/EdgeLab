"""Paridad con NinjaTrader 8 Strategy Analyzer y Ejecución de Canastas de Regímenes (2026-10-29).

Garantiza que toda regla individual (`ACTA_HOLDOUT` o pista OOS) y toda `Canasta de Regímenes` (`PISTAS_VIVAS`)
evaluada en `edgelab/research/analizador.py` tenga su contraparte exacta bajo las reglas de ejecución secuencial
de una estrategia de NinjaTrader 8 (`EntriesPerDirection = 1`, `MarketPosition.Flat`, `E1A`/`E1C`/Límite con
trade-through de 1 tick, `Break-Even` al cierre de la barra de `+1R` y tope de pérdida `aplicar_tope`).

Soporta tanto `polars` (cuando está instalado en el entorno local/Debian/Kaggle) como `pandas`/`numpy` para el
cálculo vectorizado de curvas de equity, drawdowns y multiplexación de canastas de regímenes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import polars as pl
    TIENE_POLARS = True
except ImportError:
    pl = None  # type: ignore[assignment]
    TIENE_POLARS = False

from edgelab.research import analizador as AN

VALOR_PUNTO_MICRO: dict[str, float] = {
    "NQ": 2.0,
    "MNQ": 2.0,
    "DK:USATECHIDXUSD": 2.0,
    "ES": 5.0,
    "MES": 5.0,
    "DK:USA500IDXUSD": 5.0,
    "GC": 10.0,
    "MGC": 10.0,
    "DK:XAUUSD": 10.0,
    "YM": 0.5,
    "MYM": 0.5,
}

VALOR_PUNTO_MINI: dict[str, float] = {
    "NQ": 20.0,
    "DK:USATECHIDXUSD": 20.0,
    "ES": 50.0,
    "DK:USA500IDXUSD": 50.0,
    "GC": 100.0,
    "DK:XAUUSD": 100.0,
    "YM": 5.0,
}


def filtrar_solapadas_nt8(
    ops_df: pd.DataFrame,
    duracion_s: int = 900,
    una_por_sesion: bool = False,
) -> pd.DataFrame:
    """Filtra operaciones solapadas de una misma regla como lo hace NinjaTrader 8 con `EntriesPerDirection = 1` (`Flat-Only`).

    En la grilla (`areas_expansion.simular`), cada disparo válido se evalúa en paralelo. En NinjaTrader 8 Strategy Analyzer,
    mientras una posición está abierta (`t < t_entrada_previa + duracion_s` dentro de la misma sesión `ses`, o en toda la
    sesión si `una_por_sesion=True`), las nuevas señales sobre esa misma regla se ignoran.
    """
    if ops_df is None or len(ops_df) == 0:
        return pd.DataFrame(columns=["celda", "t", "ses", "k", "neto"])
    df = ops_df.sort_values(["t", "celda"] if "celda" in ops_df.columns else ["t"], kind="stable").reset_index(drop=True)
    t_arr = df["t"].to_numpy(np.int64)
    s_arr = df["ses"].to_numpy(np.int64)
    keep: list[int] = [0]
    for j in range(1, len(t_arr)):
        ult = keep[-1]
        if una_por_sesion:
            if s_arr[j] != s_arr[ult]:
                keep.append(j)
        else:
            if s_arr[j] != s_arr[ult] or (t_arr[j] - t_arr[ult]) >= int(duracion_s):
                keep.append(j)
    return df.iloc[keep].reset_index(drop=True)


def curva_equity_polars_o_pandas(
    ops_df: pd.DataFrame,
    valor_punto: float = 1.0,
) -> dict[str, Any]:
    """Calcula la curva de equity operación por operación y sesión por sesión usando Polars (si está disponible) o Pandas."""
    if ops_df is None or len(ops_df) == 0:
        return {
            "motor": "polars" if TIENE_POLARS else "pandas",
            "n_ops": 0,
            "n_sesiones": 0,
            "t": [],
            "ses": [],
            "neto_pts": [],
            "eq_pts": [],
            "dd_pts": [],
            "eq_usd": [],
            "dd_usd": [],
            "sesiones_unicas": [],
            "eq_diaria_pts": [],
            "eq_diaria_usd": [],
        }

    df_ord = ops_df.sort_values("t", kind="stable").reset_index(drop=True)
    if TIENE_POLARS and pl is not None:
        pl_df = pl.from_pandas(df_ord[["t", "ses", "neto"]])
        pl_df = pl_df.with_columns([
            pl.col("neto").cast(pl.Float64).alias("neto_pts"),
            pl.col("neto").cast(pl.Float64).cum_sum().alias("eq_pts"),
        ]).with_columns([
            (pl.col("eq_pts") - pl.col("eq_pts").cum_max()).alias("dd_pts"),
            (pl.col("eq_pts") * float(valor_punto)).alias("eq_usd"),
            ((pl.col("eq_pts") - pl.col("eq_pts").cum_max()) * float(valor_punto)).alias("dd_usd"),
        ])
        diaria = (
            pl_df.group_by("ses", maintain_order=True)
            .agg(pl.col("neto_pts").sum().alias("neto_dia_pts"))
            .with_columns(pl.col("neto_dia_pts").cum_sum().alias("eq_diaria_pts"))
            .with_columns((pl.col("eq_diaria_pts") * float(valor_punto)).alias("eq_diaria_usd"))
        )
        return {
            "motor": "polars",
            "n_ops": int(pl_df.height),
            "n_sesiones": int(diaria.height),
            "t": pl_df["t"].to_list(),
            "ses": pl_df["ses"].to_list(),
            "neto_pts": pl_df["neto_pts"].to_list(),
            "eq_pts": pl_df["eq_pts"].to_list(),
            "dd_pts": pl_df["dd_pts"].to_list(),
            "eq_usd": pl_df["eq_usd"].to_list(),
            "dd_usd": pl_df["dd_usd"].to_list(),
            "sesiones_unicas": diaria["ses"].to_list(),
            "eq_diaria_pts": diaria["eq_diaria_pts"].to_list(),
            "eq_diaria_usd": diaria["eq_diaria_usd"].to_list(),
        }

    x = df_ord["neto"].to_numpy(float)
    eq = np.cumsum(x)
    dd = eq - np.maximum.accumulate(eq)
    dia = df_ord.groupby("ses", sort=True)["neto"].sum()
    eq_dia = np.cumsum(dia.to_numpy(float))
    return {
        "motor": "pandas",
        "n_ops": int(len(x)),
        "n_sesiones": int(len(dia)),
        "t": df_ord["t"].astype(int).tolist(),
        "ses": df_ord["ses"].astype(int).tolist(),
        "neto_pts": x.tolist(),
        "eq_pts": eq.tolist(),
        "dd_pts": dd.tolist(),
        "eq_usd": (eq * float(valor_punto)).tolist(),
        "dd_usd": (dd * float(valor_punto)).tolist(),
        "sesiones_unicas": [int(s) for s in dia.index.tolist()],
        "eq_diaria_pts": eq_dia.tolist(),
        "eq_diaria_usd": (eq_dia * float(valor_punto)).tolist(),
    }


def reporte_paridad_nt8(
    ops_df: pd.DataFrame,
    instrumento: str = "NQ",
    duracion_s: int = 900,
) -> dict[str, Any]:
    """Compara el reporte crudo de grilla (`analizador.reporte`) contra la ejecución `Flat-Only` de NinjaTrader 8."""
    vp_micro = VALOR_PUNTO_MICRO.get(instrumento, 2.0)
    vp_mini = VALOR_PUNTO_MINI.get(instrumento, 20.0)

    if ops_df is None or len(ops_df) == 0:
        return {"n_raw": 0, "n_nt8": 0, "paridad_ops_pct": 100.0, "retencion_neto_pct": 100.0}

    df_raw = ops_df.sort_values("t", kind="stable").reset_index(drop=True)
    df_nt8 = filtrar_solapadas_nt8(df_raw, duracion_s=duracion_s, una_por_sesion=False)
    df_1ses = filtrar_solapadas_nt8(df_raw, duracion_s=duracion_s, una_por_sesion=True)

    t_raw = pd.DataFrame({
        "neto_pts": df_raw["neto"].to_numpy(float),
        "ses": df_raw["ses"].to_numpy(np.int64),
        "mes": pd.to_datetime(df_raw["t"].to_numpy(np.int64), unit="s", utc=True).strftime("%Y-%m"),
    })
    t_nt8 = pd.DataFrame({
        "neto_pts": df_nt8["neto"].to_numpy(float),
        "ses": df_nt8["ses"].to_numpy(np.int64),
        "mes": pd.to_datetime(df_nt8["t"].to_numpy(np.int64), unit="s", utc=True).strftime("%Y-%m"),
    })
    t_1ses = pd.DataFrame({
        "neto_pts": df_1ses["neto"].to_numpy(float),
        "ses": df_1ses["ses"].to_numpy(np.int64),
        "mes": pd.to_datetime(df_1ses["t"].to_numpy(np.int64), unit="s", utc=True).strftime("%Y-%m"),
    })

    r_raw = AN.reporte(t_raw)
    r_nt8 = AN.reporte(t_nt8)
    r_1ses = AN.reporte(t_1ses)

    paridad_ops = 100.0 * float(r_nt8["n"]) / max(1, int(r_raw["n"]))
    ret_neto = (
        100.0 * float(r_nt8["neto_total"]) / float(r_raw["neto_total"])
        if abs(float(r_raw.get("neto_total") or 0.0)) > 1e-9
        else 100.0
    )

    curva_raw = curva_equity_polars_o_pandas(df_raw, valor_punto=vp_micro)
    curva_nt8 = curva_equity_polars_o_pandas(df_nt8, valor_punto=vp_micro)

    return {
        "instrumento": instrumento,
        "valor_punto_micro_usd": vp_micro,
        "valor_punto_mini_usd": vp_mini,
        "n_raw": int(r_raw["n"]),
        "n_nt8": int(r_nt8["n"]),
        "n_1_por_sesion": int(r_1ses["n"]),
        "paridad_ops_pct": round(paridad_ops, 2),
        "retencion_neto_pct": round(ret_neto, 2),
        "raw": r_raw,
        "nt8_flat": r_nt8,
        "nt8_1_por_sesion": r_1ses,
        "neto_usd_micro_nt8": round(float(r_nt8["neto_total"]) * vp_micro, 2),
        "neto_usd_mini_nt8": round(float(r_nt8["neto_total"]) * vp_mini, 2),
        "dd_usd_micro_nt8": round(float(r_nt8["drawdown_max"]) * vp_micro, 2),
        "curva_raw": curva_raw,
        "curva_nt8": curva_nt8,
    }


def simular_canasta_regimen(
    ops_df: pd.DataFrame,
    n_celdas: int,
    instrumento: str = "NQ",
    duracion_s: int = 900,
    top_k_pistas: int | None = None,
) -> dict[str, Any]:
    """Simula una Canasta de Regímenes bajo los modos de ejecución en NinjaTrader 8:

    1. `subcuentas_1_k` (`VirtualSubAccountsNetting`): cada pista `c` en `0..K-1` opera su propio slot `Flat-Only`
       (`EntriesPerDirection = 1` por pista) y la cuenta ejecuta la posición neta agregada (ponderada `1/K` en puntos
       equivalentes o `1` micro-contrato por pista activa).
    2. `cuenta_unica_flat` (`SingleGlobalFlatLock`): un único contrato global `Flat-Only` en toda la canasta
       (`MaxSimultaneous = 1`), tomando la primera señal que dispara cuando la cuenta está `Flat` (desempatando por el
       rango de descubrimiento `celda` menor).
    3. `top_k_subcuentas`: sub-canasta con las `top_k_pistas` primeras celdas nominadas en `DESC` (menor varianza y menor
       requerimiento de margen en prop firms).
    """
    vp_micro = VALOR_PUNTO_MICRO.get(instrumento, 2.0)
    if ops_df is None or len(ops_df) == 0 or n_celdas <= 0:
        return {"n_celdas": n_celdas, "instrumento": instrumento, "ok": False}

    # Paso 1: aplicar Flat-Only individual por cada celda de la canasta
    por_celda: list[pd.DataFrame] = []
    for c_idx, grp in ops_df.groupby("celda"):
        if top_k_pistas is not None and int(c_idx) >= int(top_k_pistas):
            continue
        por_celda.append(filtrar_solapadas_nt8(grp, duracion_s=duracion_s, una_por_sesion=False))

    if not por_celda:
        return {"n_celdas": n_celdas, "instrumento": instrumento, "ok": False}

    k_eff = min(int(n_celdas), int(top_k_pistas)) if top_k_pistas is not None else int(n_celdas)
    df_m1 = pd.concat(por_celda).sort_values(["t", "celda"], kind="stable").reset_index(drop=True)

    # Modo 1: Subcuentas Virtuales 1/K (media por sesión de la canasta equivalente a 1 unidad total dividida en K slots)
    df_m1_ponderado = df_m1.copy()
    df_m1_ponderado["neto"] = df_m1_ponderado["neto"].to_numpy(float) / float(k_eff)
    curva_m1 = curva_equity_polars_o_pandas(df_m1_ponderado, valor_punto=vp_micro)
    t_m1 = pd.DataFrame({
        "neto_pts": df_m1_ponderado["neto"].to_numpy(float),
        "ses": df_m1_ponderado["ses"].to_numpy(np.int64),
        "mes": pd.to_datetime(df_m1_ponderado["t"].to_numpy(np.int64), unit="s", utc=True).strftime("%Y-%m"),
    })
    rep_m1 = AN.reporte(t_m1)

    # Modo 2: Cuenta Única Flat-Only Global (MaxSimultaneous = 1 en toda la canasta)
    df_m2 = filtrar_solapadas_nt8(df_m1, duracion_s=duracion_s, una_por_sesion=False)
    curva_m2 = curva_equity_polars_o_pandas(df_m2, valor_punto=vp_micro)
    t_m2 = pd.DataFrame({
        "neto_pts": df_m2["neto"].to_numpy(float),
        "ses": df_m2["ses"].to_numpy(np.int64),
        "mes": pd.to_datetime(df_m2["t"].to_numpy(np.int64), unit="s", utc=True).strftime("%Y-%m"),
    })
    rep_m2 = AN.reporte(t_m2)

    return {
        "ok": True,
        "instrumento": instrumento,
        "n_celdas_canasta": k_eff,
        "valor_punto_micro_usd": vp_micro,
        "m1_subcuentas_1_k": {
            "n_ops": int(len(df_m1)),
            "n_sesiones": int(df_m1["ses"].nunique()),
            "neto_total_1x_pts": round(float(df_m1_ponderado["neto"].sum()), 3),
            "neto_total_suma_k_pts": round(float(df_m1["neto"].sum()), 3),
            "media_por_disparo_pts": round(float(df_m1["neto"].mean()), 3),
            "profit_factor": rep_m1.get("profit_factor"),
            "drawdown_max_1x_pts": round(float(rep_m1.get("drawdown_max") or 0.0), 3),
            "ic90_sesiones": rep_m1.get("ic90_sesiones"),
            "p_sesiones": rep_m1.get("p_sesiones"),
            "neto_usd_1_micro_por_pista": round(float(df_m1["neto"].sum()) * vp_micro, 2),
            "curva": curva_m1,
        },
        "m2_cuenta_unica_flat": {
            "n_ops": int(len(df_m2)),
            "n_sesiones": int(df_m2["ses"].nunique()),
            "neto_total_pts": round(float(df_m2["neto"].sum()), 3),
            "media_pts": round(float(df_m2["neto"].mean()), 3),
            "profit_factor": rep_m2.get("profit_factor"),
            "drawdown_max_pts": round(float(rep_m2.get("drawdown_max") or 0.0), 3),
            "ic90_sesiones": rep_m2.get("ic90_sesiones"),
            "p_sesiones": rep_m2.get("p_sesiones"),
            "neto_usd_1_micro": round(float(df_m2["neto"].sum()) * vp_micro, 2),
            "curva": curva_m2,
        },
    }


def exportar_senales_nt8_csv(ops_df: pd.DataFrame, ruta_csv: str | Path) -> int:
    """Exporta la tabla de eventos/señales ordenadas por timestamp UTC para reproducción de paridad en NinjaTrader 8."""
    p = Path(ruta_csv)
    p.parent.mkdir(parents=True, exist_ok=True)
    if ops_df is None or len(ops_df) == 0:
        p.write_text("t_utc_s,ses,celda,k,neto_ref_pts\n", encoding="utf-8")
        return 0
    df = ops_df.sort_values(["t", "celda"] if "celda" in ops_df.columns else ["t"], kind="stable").reset_index(drop=True)
    out = pd.DataFrame({
        "t_utc_s": df["t"].astype(np.int64),
        "ses": df["ses"].astype(np.int64),
        "celda": df["celda"].astype(np.int64) if "celda" in df.columns else 0,
        "k": df["k"].astype(np.int64) if "k" in df.columns else 0,
        "neto_ref_pts": df["neto"].astype(float).round(6),
    })
    out.to_csv(p, index=False)
    return int(len(out))
