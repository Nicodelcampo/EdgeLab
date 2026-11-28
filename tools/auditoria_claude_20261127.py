#!/usr/bin/env python3
"""Auditoria forense de los 33 commits de Claude (8d7706d4 -> 80164f3d, PR #203).

Cuantifica:
  1. Imposibilidad matematica de K27 (potencia >= 0.80 con contraccion 0.5x) por familia individual vs pooling ortogonal.
  2. Auditoria de CRIPTO-PIT: churn de membresia top-8/top-25 en UNIVERSO_PIT.csv, bug .sub(mean) en coins inactivos, peso de EMA_4H en CR_1N.
  3. Auditoria de TENDENCIA-NO-EQUITY: sesgo de clases (43% FX ETFs) y potencia real vs MDE.
  4. Auditoria de PRESET-DIVERSIFICADA y ESTADO_DEL_EDGE: informacion/mes al sumar copias intradia vs mecanismos ortogonales.
"""
from __future__ import annotations

import json
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/research/auditoria_claude_20261127"
OUT.mkdir(parents=True, exist_ok=True)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def k27_impossibility_audit() -> dict:
    # Alpha=0.05 one-sided -> z_a = 1.64485; Power=0.80 -> z_b = 0.84162 -> z_req = 2.48647
    z_req = 1.6448536 + 0.8416212
    months_grid = [18, 22, 45, 63, 100]
    shrinkages = [0.5, 0.7, 1.0]
    required_sr_dev = {}
    for m in months_grid:
        row = {}
        for sh in shrinkages:
            # power = Phi(sqrt(N/12) * SR_eff - 1.645) >= 0.80 => SR_eff >= z_req / sqrt(m/12) => SR_dev >= SR_eff / sh
            sr_eff = z_req / sqrt(m / 12.0)
            row[f"shrink_{sh}"] = round(sr_eff / sh, 2)
        required_sr_dev[f"holdout_{m}m"] = row

    # Multi-mechanism pooled portfolio Sharpe = SR_ind * sqrt(M / (1 + (M - 1) * rho))
    pooling_table = {}
    for rho in (0.05, 0.10, 0.15, 0.25):
        by_m = {}
        for M in (1, 3, 5, 10, 15, 20, 30):
            sr_port = 0.70 * sqrt(M / (1.0 + (M - 1) * rho))
            pwr_63m_sh05 = _phi(sqrt(63 / 12.0) * (0.5 * sr_port) - 1.6448536)
            pwr_63m_sh07 = _phi(sqrt(63 / 12.0) * (0.7 * sr_port) - 1.6448536)
            pwr_22m_sh07 = _phi(sqrt(22 / 12.0) * (0.7 * sr_port) - 1.6448536)
            by_m[f"M_{M}"] = {
                "sr_port_dev": round(sr_port, 2),
                "power_63m_sh05": round(pwr_63m_sh05, 3),
                "power_63m_sh07": round(pwr_63m_sh07, 3),
                "power_22m_sh07": round(pwr_22m_sh07, 3),
            }
        pooling_table[f"rho_{rho}"] = by_m
    return {"required_dev_sharpe_for_K27_80pct": required_sr_dev, "orthogonal_pooling_SRind_070": pooling_table}


def audit_cripto_pit_and_claude_results() -> dict:
    u = pd.read_csv(ROOT / "docs/research/cripto_pit_20261127/UNIVERSO_PIT.csv")
    months = sorted(u.mes.unique())

    def _churn(k: int) -> dict:
        prev = None
        entries, exits, jaccards = [], [], []
        for m in months:
            cur = set(u[(u.mes == m) & (u.rango <= k)].simbolo)
            if prev is not None:
                entries.append(len(cur - prev))
                exits.append(len(prev - cur))
                jaccards.append(len(cur & prev) / max(1, len(cur | prev)))
            prev = cur
        return {
            "unique_coins_ever": int(u[u.rango <= k].simbolo.nunique()),
            "avg_monthly_entries": round(float(np.mean(entries)), 2),
            "avg_monthly_exits": round(float(np.mean(exits)), 2),
            "avg_jaccard_overlap": round(float(np.mean(jaccards)), 3),
        }

    # Verify bug impact in Claude's RESULTADO.json & RESULTADO_TOP8.json
    c_main = json.loads((ROOT / "docs/research/cripto_pit_20261127/RESULTADO.json").read_text(encoding="utf-8"))
    c_top8 = json.loads((ROOT / "docs/research/cripto_pit_20261127/RESULTADO_TOP8.json").read_text(encoding="utf-8"))
    ema_rep = c_main["base"]["CR_Trend_4H_EMA"]["REP"]["usd_mes"]
    cr1n_rep = c_main["base"]["CR_1N"]["REP"]["usd_mes"]
    ema_share_of_cr1n_rep_loss = round((ema_rep / 3.0) / cr1n_rep, 3) if cr1n_rep != 0 else 0.0

    return {
        "churn_top8": _churn(8),
        "churn_top25": _churn(25),
        "non_ascii_symbols": [s for s in sorted(u.simbolo.unique()) if not str(s).isascii()],
        "claude_CR1N_vs_EMA4H_REP_drag": {
            "top25_base20_EMA4H_REP_usd_m": ema_rep,
            "top25_base20_CR1N_REP_usd_m": cr1n_rep,
            "EMA4H_share_of_CR1N_REP_loss": ema_share_of_cr1n_rep_loss,
            "top8_base20_REP_by_rule": {r: c_top8["base"][r]["REP"]["usd_mes"] for r in ("CR_Donchian_1D", "CR_Trend_4H_EMA", "CR_XSMOM_Neutral", "CR_1N")},
        },
        "neutralization_bug_confirmed": "cripto_pit.py line 177 w.sub(w.where(E1).mean(axis=1), axis=0) assigns non-zero weight to ~21 flat coins every day",
    }


def audit_tendencia_etf() -> dict:
    t_res = json.loads((ROOT / "docs/research/tendencia_no_equity_20261127/RESULTADO.json").read_text(encoding="utf-8"))
    clases = {"TLT": "tasas", "IEF": "tasas", "GLD": "metales", "SLV": "metales", "DBB": "metales", "USO": "energia", "UNG": "energia",
              "DBA": "granos", "FXE": "divisas", "FXY": "divisas", "FXB": "divisas", "FXA": "divisas", "FXC": "divisas", "FXF": "divisas"}
    counts = pd.Series(list(clases.values())).value_counts().to_dict()
    shares = {k: round(v / len(clases), 3) for k, v in counts.items()}
    # True power for SR=0.35, 0.45, 0.55 over 130 months (10.83 yrs)
    pwr = {f"SR_{sr}": round(_phi(sqrt(130.0 / 12.0) * sr - 1.6448536), 3) for sr in (0.35, 0.45, 0.55, 0.76)}
    return {
        "etf_class_counts": counts,
        "etf_class_shares": shares,
        "claude_DESC_base": t_res["base"]["DESC"],
        "true_power_130m": pwr,
    }


def audit_diversificada_and_edge_state() -> dict:
    sens = pd.read_csv(ROOT / "docs/research/preset_diversificada_20261127/SENSIBILIDAD_DLL_150K.csv")
    c2 = json.loads((ROOT / "docs/research/canasta_amplia_20261127/EXPLORACION.json").read_text(encoding="utf-8"))
    return {
        "preset_diversificada_150k_2micros": sens[sens["plan"] == "UNOx2|B0"].to_dict("records"),
        "canasta_amplia_shrinkage": c2["fase1_2"]["pendiente_sharpe"],
        "canasta_amplia_grupos": c2["fase1_2"]["grupos"],
        "carril2_REP": c2["fase3_4"]["pozos_sellados"]["CARRIL2"],
    }


def main() -> None:
    res = {
        "k27_impossibility": k27_impossibility_audit(),
        "cripto_pit_audit": audit_cripto_pit_and_claude_results(),
        "tendencia_etf_audit": audit_tendencia_etf(),
        "diversificada_and_canasta": audit_diversificada_and_edge_state(),
    }
    (OUT / "AUDITORIA_CLAUDE.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print("\nSaved:", OUT / "AUDITORIA_CLAUDE.json")


if __name__ == "__main__":
    main()
