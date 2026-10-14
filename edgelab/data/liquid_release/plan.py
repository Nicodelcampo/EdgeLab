"""Plan de la release: calendario derivado, política de liquidez propuesta, selección causal por activo y segmentos de escritura.

Todo lo que sale de acá es PROPUESTA hasta que Nico apruebe la política (`approved_by`). Los límites se calibran de forma
descriptiva con las PRIMERAS `CALIBRATION_SESSIONS` sesiones de cada activo (volumen y ticks del líder diario, spread típico)
y se congelan como constantes redondas: las sesiones posteriores a esa ventana se deciden con una política fijada sin
mirarlas (auditoría LRA, 2026-10-14: antes se calibraba con toda la muestra pre-holdout). Las sesiones de la propia ventana de
calibración sí son in-sample, y quedan declaradas en `notes`.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from edgelab.data.liquid_release.calendar_derive import derive_calendar, session_days
from edgelab.data.liquid_release.selection import LiquidityPolicy, OK, select_sessions

EXCLUDED_NO_DATA = "EXCLUDED_SELECTED_CONTRACT_HAS_NO_DATA"
POLICY_VERSION = "liquid_policy_proposal_v1_20261014"
FLOOR_FRACTION = 0.10          # piso = 10 % de la mediana del líder diario (volumen y ticks)
CALIBRATION_SESSIONS = 80      # ventana de calibración: primeras N sesiones de lunes a viernes de cada activo (prospectivo después)
SPREAD_MULT = 3.0              # tope de spread típico = 3 x la mediana de la mediana diaria de spread del líder, mínimo 2 ticks


def _round_nice(x: float) -> float:
    if x <= 0:
        return 0.0
    mag = 10 ** int(np.floor(np.log10(x)))
    return float(np.floor(x / mag) * mag) if x / mag >= 2 else float(np.floor(x / (mag / 2)) * (mag / 2))


def asset_frame(chosen: pd.DataFrame, instrument: str) -> pd.DataFrame:
    c = chosen[(chosen["instrument"] == instrument)].copy()
    c["vol"] = c["vol_reg"].astype(float)
    c["n"] = c["n_reg"].astype(int)
    c["spread_p50"] = c["spread_p50"].astype(float)
    c["coverage"] = OK
    return c[["contract", "trade_date", "vol", "n", "spread_p50", "coverage", "kind", "group", "assurance", "n_min_reg",
              "max_gap_reg_ns", "n_break", "n_dup_copy", "identical", "n_candidates"]]


def propose_policy(chosen: pd.DataFrame, instrument: str, calibration_sessions: int | None = CALIBRATION_SESSIONS) -> LiquidityPolicy:
    c = chosen[(chosen["instrument"] == instrument) & (chosen["n_reg"] > 0)]
    lead = c.sort_values("vol_reg", ascending=False).drop_duplicates("trade_date").sort_values("trade_date")
    wk = lead[pd.to_datetime(lead["trade_date"].astype(str)).dt.dayofweek < 5]
    if calibration_sessions:
        wk = wk.head(int(calibration_sessions))
    vol_floor = _round_nice(FLOOR_FRACTION * float(wk["vol_reg"].median()))
    n_floor = int(_round_nice(FLOOR_FRACTION * float(wk["n_reg"].median())))
    sp = max(2.0, float(np.ceil(SPREAD_MULT * float(wk["spread_p50"].median()))))
    return LiquidityPolicy(POLICY_VERSION, vol_floor, n_floor, sp, approved_by=None,
                           notes=(f"calibrada con las primeras {len(wk)} sesiones de líder diario (hasta {int(wk['trade_date'].max())}); prospectiva después; "
                                f"las sesiones de la ventana son in-sample; PROPUESTA sin aprobar"))


def derive_all_calendars(chosen: pd.DataFrame) -> pd.DataFrame:
    daily = chosen[chosen["n_reg"] > 0].groupby(["instrument", "trade_date"], as_index=False)["vol_reg"].sum()
    daily = daily.rename(columns={"vol_reg": "vol"})
    return derive_calendar(daily)


def plan_asset(chosen: pd.DataFrame, calendars: pd.DataFrame, instrument: str, policy: LiquidityPolicy | None = None):
    pol = policy or propose_policy(chosen, instrument)
    fr = asset_frame(chosen, instrument)
    days = session_days(calendars, instrument)
    dec = select_sessions(fr[["contract", "trade_date", "vol", "n", "spread_p50", "coverage"]], days, pol)
    # El contrato elegido por D-1 debe tener datos en S. Si no los tiene NO se cambia de contrato para rescatar la sesión:
    # se excluye y queda registrada (ni cero inventado ni fallback).
    have = set(zip(fr["contract"], fr["trade_date"]))
    miss = (dec["status"] == "SELECTED") & ~pd.Series([(c, d) in have for c, d in zip(dec["contract"], dec["trade_date"])], index=dec.index)
    dec.loc[miss, "reason"] = "contrato elegido por D-1 sin datos en S: sesión excluida (no se rescata con otro contrato)"
    dec.loc[miss, "status"] = EXCLUDED_NO_DATA
    return pol, fr, dec
