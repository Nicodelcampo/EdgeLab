#!/usr/bin/env python3
"""
GATE Paso 2 — Métricas target-free del régimen (sin outcomes / sin P&L).

Reporta:
  - minutos (o conteo) por estado
  - persistencia media (duración de rachas)
  - flip-flop rate
  - matriz de transición empírica
  - cobertura por sesión (≥40 sesiones/celda = flag EdgeLab CTX-2)
  - corr régimen↔ancho_ticks (Pearson sobre códigos; point-biserial por estado vs resto)
  - veredicto de contaminación tipo CTX-2 (corr alta con ancho → riesgo)

Anclas:
  - duración ≈ 1/(1-p_stay); persistencia de estados en Markov
  - point-biserial / Pearson para categórico vs continuo (confundidor)
  - IDA/EDA: explorar estructura sin asociar al estimando de la hipótesis
  - umbral orientativo ≥40 sesiones/celda (criterio ya usado en H-ES-CTX-2)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REGIME_NAMES = {0: "calmo", 1: "normal", 2: "volatil", 3: "toxico"}
# Umbral de alarma alineado a CTX-2: fase sesión tenía |corr|≈0.255 con ancho → rechazada
CORR_ANCHO_WARN = 0.20
CORR_ANCHO_REJECT = 0.25
MIN_SESSIONS_CELL = 40


def persistence_mean(regime: np.ndarray) -> float:
    durs = []
    run = 1
    for i in range(1, len(regime)):
        if regime[i] == regime[i - 1]:
            run += 1
        else:
            durs.append(run)
            run = 1
    durs.append(run)
    return float(np.mean(durs)) if durs else float("nan")


def flip_flop_rate(regime: np.ndarray) -> float:
    if len(regime) < 2:
        return float("nan")
    return float(np.mean(regime[1:] != regime[:-1]))


def transition_matrix(regime: np.ndarray, K: int = 4) -> np.ndarray:
    C = np.zeros((K, K), dtype=float)
    for a, b in zip(regime[:-1], regime[1:]):
        if 0 <= a < K and 0 <= b < K:
            C[int(a), int(b)] += 1
    row = C.sum(axis=1, keepdims=True)
    row[row == 0] = 1
    return C / row


def minutes_by_regime(regime: np.ndarray) -> dict[str, int]:
    return {REGIME_NAMES[k]: int((regime == k).sum()) for k in range(4)}


def session_coverage(
    labels: pd.DataFrame,
    session_col: str = "session_id",
    regime_col: str = "regime",
) -> dict[str, Any]:
    """Sesiones distintas por celda de régimen (eventos etiquetados)."""
    df = labels[labels.get("as_of_ok", True) == True] if "as_of_ok" in labels.columns else labels
    out = {}
    for k, name in REGIME_NAMES.items():
        sub = df[df[regime_col] == k]
        n_sess = int(sub[session_col].nunique()) if len(sub) else 0
        out[name] = {
            "n_events": int(len(sub)),
            "n_sessions": n_sess,
            "ok_min_sessions": n_sess >= MIN_SESSIONS_CELL,
        }
    return out


def corr_regime_ancho(
    labels: pd.DataFrame,
    ancho_col: str = "ancho_ticks",
    regime_col: str = "regime",
) -> dict[str, Any]:
    """
    Correlación régimen (código 0..3) vs ancho continuo.
    + point-biserial por estado (1 vs resto) — detecta si un estado concentra anchos.
    """
    df = labels.dropna(subset=[ancho_col, regime_col]).copy()
    if "as_of_ok" in df.columns:
        df = df[df["as_of_ok"] == True]
    if len(df) < 10:
        return {"status": "INSUFFICIENT", "n": len(df)}

    r = df[regime_col].astype(float).to_numpy()
    w = df[ancho_col].astype(float).to_numpy()
    # Pearson (equivalente a tratar régimen como numérico ordinal de vol)
    if r.std() < 1e-12 or w.std() < 1e-12:
        pearson = float("nan")
    else:
        pearson = float(np.corrcoef(r, w)[0, 1])

    pb = {}
    for k, name in REGIME_NAMES.items():
        binary = (r == k).astype(float)
        if binary.std() < 1e-12:
            pb[name] = float("nan")
        else:
            pb[name] = float(np.corrcoef(binary, w)[0, 1])

    abs_p = abs(pearson) if pearson == pearson else 0.0
    if abs_p >= CORR_ANCHO_REJECT:
        verdict = "REJECT_LIKE_CTX2"
    elif abs_p >= CORR_ANCHO_WARN:
        verdict = "WARN"
    else:
        verdict = "OK_LOW_CORR"

    return {
        "status": "OK",
        "n": int(len(df)),
        "pearson_regime_code_vs_ancho": round(pearson, 4) if pearson == pearson else None,
        "point_biserial_one_vs_rest": {k: (round(v, 4) if v == v else None) for k, v in pb.items()},
        "verdict": verdict,
        "thresholds": {"warn": CORR_ANCHO_WARN, "reject": CORR_ANCHO_REJECT},
        "note": (
            "CTX-2 rechazó fase sesión con corr≈-0.255 vs ancho. "
            "GATE debe publicar esta corr target-free antes de outcomes."
        ),
    }


def target_free_report(
    regime_path: np.ndarray | None = None,
    labels: pd.DataFrame | None = None,
    *,
    bar_minutes: bool = True,
) -> dict[str, Any]:
    """
    Si se pasa regime_path (serie temporal de barras): persistencia/flip/transición/minutos.
    Si se pasa labels (eventos etiquetados): cobertura por sesión + corr con ancho.
    """
    report: dict[str, Any] = {"schema": "gate_target_free_v1", "outcomes_accessed": False}

    if regime_path is not None:
        rp = np.asarray(regime_path).astype(int)
        pers = persistence_mean(rp)
        ff = flip_flop_rate(rp)
        P = transition_matrix(rp)
        # duración esperada por estado ≈ 1/(1-p_ii)
        exp_dur = {}
        for k in range(4):
            p_stay = P[k, k]
            exp_dur[REGIME_NAMES[k]] = round(1.0 / (1.0 - p_stay), 2) if p_stay < 1 else None
        report["bar_path"] = {
            "n_bars": int(len(rp)),
            "minutes_by_regime": minutes_by_regime(rp),
            "persistencia_media": round(pers, 2),
            "flip_flop_rate": round(ff, 4),
            "transition_matrix": P.round(3).tolist(),
            "expected_duration_from_p_stay": exp_dur,
            "unit": "bars(=minutes si 1m)" if bar_minutes else "bars",
        }

    if labels is not None:
        report["event_labels"] = {
            "n_events": int(len(labels)),
            "n_as_of_ok": int(labels["as_of_ok"].sum())
            if "as_of_ok" in labels.columns
            else int(len(labels)),
            "session_coverage": session_coverage(labels),
            "corr_with_ancho": corr_regime_ancho(labels)
            if "ancho_ticks" in labels.columns
            else {"status": "NO_ANCHO_COLUMN"},
        }

    return report


def demo() -> dict[str, Any]:
    """Demo target-free sobre generador v2 + labels del adapter."""
    from gate_generator_transformer import gen_latent_v2_target_budget
    from gate_recreate import generate_prices, BARS_PER_DAY
    from gate_five_proposals import enrich_features
    from gate_adapter import label_events_at_t0

    latent = gen_latent_v2_target_budget(BARS_PER_DAY)
    df = generate_prices(latent)
    df = enrich_features(df)
    df["regime"] = latent
    age = np.zeros(len(df), dtype=int)
    for i in range(1, len(df)):
        age[i] = age[i - 1] + 1 if latent[i] == latent[i - 1] else 0
    df["sticky_age_bars"] = age
    df["post_calmo"] = (latent == 0).astype(float)
    df["post_normal"] = (latent == 1).astype(float)
    df["post_volatil"] = (latent == 2).astype(float)

    # multi-sesión sintética para cobertura
    events = []
    for sess in range(50):
        offset = (sess * 7) % max(len(df) - 5, 1)
        for j in range(5):
            i = min(offset + j * 3 + 10, len(df) - 1)
            events.append(
                {
                    "event_id": f"s{sess}_e{j}",
                    "t0": df["time"].iloc[i],
                    "session_id": f"2026-03-{12 + (sess % 28):02d}",
                    "ancho_ticks": float(3 + (latent[i] % 3) + (sess % 4) * 0.1),
                }
            )
    events_df = pd.DataFrame(events)
    labels = label_events_at_t0(events_df, df, seed=20260312, commit="paso2-demo")

    report = target_free_report(regime_path=latent, labels=labels)
    return report


def main():
    print("=== GATE Paso 2 — target-free ===\n")
    report = demo()
    print(json.dumps(report, indent=2, default=str))
    path = Path(__file__).resolve().parent / "gate_paso2_target_free_report.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {path}")

    # update roadmap status line
    rd = Path(__file__).resolve().parent / "GATE_ROADMAP.md"
    if rd.exists():
        txt = rd.read_text(encoding="utf-8")
        txt = txt.replace(
            "## Paso 2 — Métricas target-free del régimen\n**Estado: PENDIENTE**",
            "## Paso 2 — Métricas target-free del régimen\n**Estado: HECHO (demo sintética)**",
        )
        txt = txt.replace(
            "## Paso 1 — Schema + adaptador causal + proveniencia\n**Estado: EN CURSO**",
            "## Paso 1 — Schema + adaptador causal + proveniencia\n**Estado: HECHO (smoke)**",
        )
        rd.write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main()
