"""Fixtures sintéticos del diseño NQ-CRUCE25-CLIMA v2 (Entrada 067). Sin outcomes reales."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import l2_labels_utc as U  # noqa: E402
import nq_cruce25_clima as R  # noqa: E402

H3 = 3 * 3600 * 1_000_000


def _lab(rows):
    base = dict(instrument="NQ", contract="NQ_09-26", clock_semantics="NT8_WALL_CLOCK_X", data_window_end_us=0,
                feature_eligible=True, context_group="g", context_fail_reason="", context_model_id="m",
                p_calm=0.0, p_normal=0.0, p_volatile=0.0, flow_toxicity_score=0.0)
    df = pd.DataFrame([{**base, **r} for r in rows])
    df["minute_start_us"] = df["minute_start_us"].astype(np.int64)
    df["feature_available_at_us"] = df["minute_start_us"] + 60_000_000
    return df


def test_utc_una_sola_vez_y_enteros():
    art = 1_790_000_000_000_000  # µs de pared ART
    df = _lab([dict(cme_session="20260801", minute_id=1, minute_start_us=art, evaluation_eligible=True, context_state="calm", context_as_of_ok=True)])
    o = U.to_utc(df)
    assert int(o["available_utc_us"].iloc[0]) == art + 60_000_000 + H3
    assert int(o["available_utc_us"].iloc[0]) - H3 == int(df["feature_available_at_us"].iloc[0])  # ida y vuelta
    with pytest.raises(ValueError):
        U.to_utc(o)  # doble conversión


def _cl(rows):
    return R.ClimaLookup(U.to_utc(_lab(rows)))


def test_clima_causal_edad_y_validez():
    t0 = 1_790_000_000_000_000
    CL = _cl([dict(cme_session="s", minute_id=1, minute_start_us=t0, evaluation_eligible=True, context_state="calm", context_as_of_ok=True),
              dict(cme_session="s", minute_id=2, minute_start_us=t0 + 60_000_000, evaluation_eligible=False, context_state=None, context_as_of_ok=False)])
    avail1 = (t0 + 60_000_000 + H3) * 1000  # ns
    assert R.ClimaLookup.at_ns(CL, avail1 - 1) is None           # un ns antes de publicarse: no disponible
    assert CL.at_ns(avail1) == "calm"                             # exacto en la publicación: disponible
    assert CL.at_ns(avail1 + 59_000_000_000) == "calm"
    assert CL.at_ns(avail1 + 60_000_000_000) is None              # la fila siguiente es inelegible: no se salta a la vieja
    CL2 = _cl([dict(cme_session="s", minute_id=1, minute_start_us=t0, evaluation_eligible=True, context_state="calm", context_as_of_ok=True)])
    assert CL2.at_ns(avail1 + 120_000_000_000) == "calm"
    assert CL2.at_ns(avail1 + 120_000_001_000) is None            # edad > 120 s


def test_control_mismo_clima():
    pool = dict(ses=np.array(["a", "b", "b", "c", "c"]), tod=np.array([100, 100, 100, 100, 100]),
                ter=np.array([1, 1, 1, 1, 1]), clima=np.array(["calm", "calm", "toxic", "calm", "toxic"], dtype=object))
    rng = np.random.default_rng(0)
    p = R.pick_controls(pool, "a", 100, 1, "toxic", rng, n=2)
    assert set(pool["clima"][p]) == {"toxic"} and "a" not in set(pool["ses"][p])
    assert R.pick_controls(pool, "a", 100, 1, "toxic", rng, n=3) is None      # sin soporte
    assert R.pick_controls(pool, "a", 100 + 1801, 1, "calm", rng, n=1) is None  # fuera de ±30 min


def test_vol_rms_firmada():
    C = np.array([0, 1] * 20, float)  # alternancia de igual magnitud: std(|Δ|) ≈ 0, RMS = 1
    assert R.vol_prev(C)[25] == pytest.approx(1.0)
    assert R.vol_prev_v1(C)[25] == pytest.approx(0.0)


def test_bootstrap_conjunto_pesos_comunes():
    ev = np.array([1., 0, 1, 0]); ctrl = np.zeros((4, 3)); es = np.array([0, 1, 2, 3]); cs = np.array([[1, 2, 3]] * 4)
    c1 = dict(ev=ev, ctrl=ctrl, ev_ses=es, ctrl_ses=cs)
    c2 = dict(ev=ev.copy(), ctrl=ctrl, ev_ses=es, ctrl_ses=cs)
    obs, se, crit, _ = R.joint_maxT([c1, c2], 4, n_boot=500)
    assert obs[0] == pytest.approx(0.5) and se[0] == pytest.approx(se[1])
    # celdas idénticas con pesos comunes ⇒ el máximo de |T| es el |T| de una celda: crit = cuantil marginal
    obs1, se1, crit1, _ = R.joint_maxT([c1], 4, n_boot=500)
    assert crit == pytest.approx(crit1)
    assert R.cell_stat(ev, ctrl, es, cs, np.ones(4)) == pytest.approx(0.5)


def test_eval_ids_hash_congelado():
    import json
    g = json.loads((Path(__file__).resolve().parents[1] / "artifacts/l2_contexts/NQ/gate_report.json").read_text(encoding="utf-8")) \
        if (Path(__file__).resolve().parents[1] / "artifacts/l2_contexts/NQ/gate_report.json").exists() else None
    if g is None:
        pytest.skip("gate_report local no disponible")
    assert R.eval_ids_sha(map(str, g["plan"]["eval_ids"])) == R.EVAL_IDS_SHA256


def test_holdout_frontera():
    import tbz_e2 as TB
    assert R.HOLDOUT_NS == TB.HOLDOUT_NS == 1_790_805_600_000_000_000


def test_objetivo_desde_el_cierre_de_senal():
    # d=+1, objetivo 10, falla 0, señal en j=1
    H = np.array([5., 11, 9, 12]); L = np.array([4., 5, 6, 8]); C = np.array([5., 10.5, 8, 11])
    assert R.outcome_from_close(H, L, C, 1, 10, 0, 1, 3) is None          # cierre de j ya pasó el objetivo: sin operación
    C2 = np.array([5., 7, 8, 11]); H2 = np.array([5., 11, 9, 12])         # sólo la mecha de j tocó: no cuenta, se mide desde j+1
    assert R.outcome_from_close(H2, L, C2, 1, 10, 0, 1, 2) == 0           # j+1 (máx 9) no llega
    assert R.outcome_from_close(H2, L, C2, 1, 10, 0, 1, 3) == 1           # llega en j+2
