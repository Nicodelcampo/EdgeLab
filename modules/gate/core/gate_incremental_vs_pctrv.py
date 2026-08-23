#!/usr/bin/env python3
"""
GATE Paso 4 — Valor incremental de GATE vs baseline pct_rv.

Pregunta (Biddle/Seow/Siegel): ¿GATE aporta información *más allá* de pct_rv,
no solo si “gana” en ranking relativo?

Métodos (nested / value-added):
  1) Modelo reducido:  y ~ pct_rv_cell
  2) Modelo completo:  y ~ pct_rv_cell + gate_cell
  3) Test de coeficientes de gate = 0  (LR / Wald / partial-F análogo)
  4) Métricas de ajuste: R² / loglik / ΔAIC

En el lab real, y = estimando de sesión (delta ticks_por_ancho o AbsMagnitude).
Aquí: demo con y sintético controlado para verificar el pipeline.

Anclas:
  - Incremental vs relative information content (Biddle et al.)
  - LR test nested models; partial F / ΔR²
  - Encompassing / Clark-West para pronósticos anidados (referencia)
  - H0 de no mejora ≡ coef de Y|X = 0 en el modelo de riesgo (Pepe et al. style)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260823)


def _ols(y: np.ndarray, X: np.ndarray) -> dict[str, Any]:
    """OLS con intercepto; X sin columna de unos."""
    n = len(y)
    Xd = np.column_stack([np.ones(n), X])
    # ridge leve si singular
    xtx = Xd.T @ Xd
    try:
        beta = np.linalg.solve(xtx, Xd.T @ y)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(Xd, y, rcond=None)[0]
    yhat = Xd @ beta
    resid = y - yhat
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    k = Xd.shape[1]
    # loglik gaussiana
    sigma2 = ss_res / max(n, 1)
    ll = -0.5 * n * (np.log(2 * np.pi) + np.log(max(sigma2, 1e-18)) + 1.0)
    aic = 2 * k - 2 * ll
    return {
        "beta": beta,
        "r2": r2,
        "ss_res": ss_res,
        "loglik": ll,
        "aic": aic,
        "n": n,
        "k": k,
        "resid": resid,
    }


def partial_f_test(y: np.ndarray, X_reduced: np.ndarray, X_full: np.ndarray) -> dict[str, Any]:
    """
    Partial / incremental F:
      F = ((SS_red - SS_full) / q) / (SS_full / (n - k_full))
    q = k_full - k_red
    """
    m_r = _ols(y, X_reduced)
    m_f = _ols(y, X_full)
    n = m_f["n"]
    q = m_f["k"] - m_r["k"]
    df_den = n - m_f["k"]
    if q <= 0 or df_den <= 0:
        return {"status": "INVALID", "m_reduced": m_r, "m_full": m_f}
    num = (m_r["ss_res"] - m_f["ss_res"]) / q
    den = m_f["ss_res"] / df_den
    F = num / den if den > 0 else float("inf")
    # p-value approx via survival de F (Wilson-Hilferty / scipy-free)
    p = _f_sf(F, q, df_den)
    lr = 2 * (m_f["loglik"] - m_r["loglik"])
    return {
        "status": "OK",
        "delta_r2": m_f["r2"] - m_r["r2"],
        "r2_reduced": m_r["r2"],
        "r2_full": m_f["r2"],
        "partial_F": float(F),
        "df": (int(q), int(df_den)),
        "p_value_F": float(p),
        "LR_stat": float(lr),
        "p_value_LR_chi2": float(_chi2_sf(lr, q)),
        "delta_AIC": m_f["aic"] - m_r["aic"],
        "beta_full": m_f["beta"].tolist(),
        "verdict": _verdict(p, m_f["r2"] - m_r["r2"]),
    }


def _f_sf(F: float, d1: float, d2: float) -> float:
    """Survival P(F_d1,d2 > F) aproximación regularizada incompleta beta."""
    if F <= 0 or not np.isfinite(F):
        return 1.0
    x = d2 / (d2 + d1 * F)
    # I_x(d2/2, d1/2) ≈ sf
    return float(_betainc_reg(d2 / 2.0, d1 / 2.0, x))


def _chi2_sf(x: float, df: float) -> float:
    if x <= 0 or not np.isfinite(x):
        return 1.0
    # chi2 sf = gammainc_upper(df/2, x/2)
    return float(_gammainc_upper(df / 2.0, x / 2.0))


def _betainc_reg(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a,b) — continued fraction (Lentz)."""
    x = min(max(x, 0.0), 1.0)
    if x == 0:
        return 0.0
    if x == 1:
        return 1.0
    # use relation with continued fraction
    from math import lgamma, exp, log

    def _betacf(a, b, x, max_iter=200, eps=1e-10):
        am, bm = 1.0, 1.0
        az = 1.0
        qab = a + b
        qap = a + 1
        qam = a - 1
        bz = 1.0 - qab * x / qap
        for m in range(1, max_iter + 1):
            em = float(m)
            tem = em + em
            d = em * (b - em) * x / ((qam + tem) * (a + tem))
            ap = az + d * am
            bp = bz + d * bm
            d = -(a + em) * (qab + em) * x / ((a + tem) * (qap + tem))
            app = ap + d * az
            bpp = bp + d * bz
            am, bm, az, bz = ap / bpp, bp / bpp, app / bpp, 1.0
            if abs(app - ap) < eps * abs(app):
                return az
        return az

    lbeta = lgamma(a) + lgamma(b) - lgamma(a + b)
    front = exp(a * log(x) + b * log(1 - x) - lbeta) / a
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x)
    return 1.0 - (exp(b * log(1 - x) + a * log(x) - lbeta) / b) * _betacf(b, a, 1 - x)


def _gammainc_upper(s: float, x: float) -> float:
    """Q(s,x) = gamma(s,x)/Gamma(s) upper incomplete regularized — serie/continúa simple."""
    from math import lgamma, exp, log

    if x <= 0:
        return 1.0
    # series for lower P then 1-P when x < s+1
    if x < s + 1:
        term = exp(-x + s * log(x) - lgamma(s)) / s
        sm = term
        for n in range(1, 200):
            term *= x / (s + n)
            sm += term
            if abs(term) < 1e-12 * abs(sm):
                break
        return max(0.0, 1.0 - sm)
    # continued fraction for Q
    b0 = x + 1 - s
    c = 1e30
    d = 1.0 / b0
    h = d
    for i in range(1, 200):
        an = -i * (i - s)
        b = b0 + 2 * i
        d = 1.0 / (an * d + b)
        c = b + an / c
        term = c * d
        h *= term
        if abs(term - 1) < 1e-10:
            break
    return exp(-x + s * log(x) - lgamma(s)) * h


def _verdict(p: float, delta_r2: float) -> str:
    if p < 0.05 and delta_r2 > 0.01:
        return "INCREMENTAL_YES"
    if p < 0.05 and delta_r2 <= 0.01:
        return "INCREMENTAL_WEAK"
    return "INCREMENTAL_NO"


def build_design(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    pct_rv_cell: dummies tercil (drop first)
    gate_cell: dummies G-operable / G-estres (drop one)
    """
    # pct terciles already as 0,1,2
    pct = pd.get_dummies(df["pct_rv_cell"], prefix="pct", drop_first=True).to_numpy(dtype=float)
    gate = pd.get_dummies(df["gate_cell"], prefix="gate", drop_first=True).to_numpy(dtype=float)
    y = df["y_session"].to_numpy(dtype=float)
    return y, pct, gate


def incremental_report(df: pd.DataFrame) -> dict[str, Any]:
    y, X_pct, X_gate = build_design(df)
    X_full = np.column_stack([X_pct, X_gate]) if X_gate.size else X_pct
    result = partial_f_test(y, X_pct, X_full)
    result["n_sessions"] = int(len(df))
    result["question"] = (
        "Incremental: does GATE cell add fit beyond pct_rv cell? "
        "(not relative ranking of GATE vs pct_rv alone)"
    )
    result["method"] = "nested OLS partial-F + LR; H0: gate coefs = 0 | pct_rv"
    return result


def make_synthetic_sessions(n_sess: int = 60) -> pd.DataFrame:
    """
    Tres escenarios para validar el pipeline:
      A) GATE no aporta (y solo depende de pct_rv)
      B) GATE aporta de verdad
      C) solo ruido
    Devuelve escenario B como principal + meta de A/C en el JSON.
    """
    rows = []
    for i in range(n_sess):
        pct = int(RNG.integers(0, 3))  # 0 bajo 1 medio 2 alto
        gate = int(RNG.integers(0, 2))  # 0 estres 1 operable
        # B: y depende de ambos
        y = 0.5 * pct + 1.2 * gate + RNG.normal(0, 1.0)
        rows.append({"session_id": f"S{i}", "pct_rv_cell": pct, "gate_cell": gate, "y_session": y})
    return pd.DataFrame(rows)


def scenario_A(n: int = 60) -> pd.DataFrame:
    rows = []
    for i in range(n):
        pct = int(RNG.integers(0, 3))
        gate = int(RNG.integers(0, 2))
        y = 0.8 * pct + RNG.normal(0, 1.0)  # sin gate
        rows.append({"session_id": f"A{i}", "pct_rv_cell": pct, "gate_cell": gate, "y_session": y})
    return pd.DataFrame(rows)


def scenario_C(n: int = 60) -> pd.DataFrame:
    rows = []
    for i in range(n):
        pct = int(RNG.integers(0, 3))
        gate = int(RNG.integers(0, 2))
        y = RNG.normal(0, 1.0)
        rows.append({"session_id": f"C{i}", "pct_rv_cell": pct, "gate_cell": gate, "y_session": y})
    return pd.DataFrame(rows)


def main():
    print("=== GATE Paso 4 — incremental vs pct_rv ===\n")
    df_b = make_synthetic_sessions(60)
    rep_b = incremental_report(df_b)
    rep_a = incremental_report(scenario_A(60))
    rep_c = incremental_report(scenario_C(60))

    out = {
        "schema": "gate_incremental_v1",
        "outcomes_accessed": False,
        "note": "Demo sintética. En lab real y_session = estimando de la familia por sesión.",
        "scenario_B_gate_matters": rep_b,
        "scenario_A_only_pctrv": rep_a,
        "scenario_C_noise": rep_c,
        "interpretation": {
            "INCREMENTAL_YES": "GATE aporta fit más allá de pct_rv (p<0.05 y ΔR²>0.01)",
            "INCREMENTAL_WEAK": "Significativo pero ΔR² pequeño — cautela práctica",
            "INCREMENTAL_NO": "No se rechaza H0: coefs GATE = 0 | pct_rv",
        },
        "literature": {
            "incremental_vs_relative": "Biddle, Seow, Siegel (1995)",
            "nested_LR_partial_F": "standard nested model comparison",
            "H0_no_improvement": "equivalent to coef(Y|X)=0 in risk model (Pepe et al.)",
            "forecast_encompassing": "Clark-McCracken / Clark-West (reference for nested forecasts)",
        },
    }
    print("Scenario B (GATE matters):", rep_b["verdict"], "ΔR²=", round(rep_b.get("delta_r2", 0), 4), "pF=", round(rep_b.get("p_value_F", 1), 4))
    print("Scenario A (only pct_rv):  ", rep_a["verdict"], "ΔR²=", round(rep_a.get("delta_r2", 0), 4), "pF=", round(rep_a.get("p_value_F", 1), 4))
    print("Scenario C (noise):        ", rep_c["verdict"], "ΔR²=", round(rep_c.get("delta_r2", 0), 4), "pF=", round(rep_c.get("p_value_F", 1), 4))

    path = Path(__file__).resolve().parent / "gate_paso4_incremental_report.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {path}")

    # roadmap
    p = Path(__file__).resolve().parent / "GATE_ROADMAP.md"
    if p.exists():
        lines = p.read_text(encoding="utf-8").splitlines()
        out_l = []
        i = 0
        while i < len(lines):
            out_l.append(lines[i])
            if lines[i].startswith("## Paso 4") and i + 1 < len(lines) and "PENDIENTE" in lines[i + 1]:
                out_l.append("**Estado: HECHO (demo sintética)**")
                i += 2
                continue
            i += 1
        p.write_text("\n".join(out_l) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
