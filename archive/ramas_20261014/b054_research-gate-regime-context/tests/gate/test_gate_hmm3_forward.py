from __future__ import annotations

import json
import numpy as np
import pytest

from modules.gate.core.gate_hmm3_forward import (
    HMM3Checkpoint,
    HMM3Config,
    fit_hmm3,
    forward_filter,
)


def _fixture():
    rng = np.random.default_rng(7)
    rows, sequence_ids = [], []
    for session in range(8):
        state = session % 3
        for _ in range(120):
            if rng.random() < 0.06:
                state = int(rng.integers(0, 3))
            centre = np.array([
                0.4 + state * 1.2,
                1.0 + state * 2.0,
                1.0 + state * 0.5,
                -0.2 + state * 0.2,
                0.75 - state * 0.2,
            ])
            rows.append(centre + rng.normal(0, [0.08, 0.2, 0.05, 0.08, 0.04]))
            sequence_ids.append(f"s{session}")
    return np.asarray(rows), sequence_ids


def test_checkpoint_incluye_pesos_normalizador_datos_config_y_commit():
    x, sessions = _fixture()
    cp = fit_hmm3(x, sessions, code_commit="a" * 40)
    cp.validate()
    assert cp.model_id.startswith("gate_gc_l1_hmm3_forward_v0:")
    assert cp.config_sha256 == HMM3Config().config_sha256
    assert len(cp.training_matrix_sha256) == 64
    assert cp.training_rows == len(x)
    assert cp.training_sequences == 8
    assert cp.code_commit == "a" * 40


def test_forward_es_prefijo_invariante_y_no_mira_el_futuro():
    x, sessions = _fixture()
    cp = fit_hmm3(x, sessions, code_commit="b" * 40)
    short = forward_filter(x[:100], sessions[:100], cp)
    long_prefix = forward_filter(x[:120], sessions[:120], cp)[:100]
    assert np.allclose(short, long_prefix, rtol=0, atol=1e-12)


def test_checkpoint_es_determinista_y_model_id_identifica_los_bytes():
    x, sessions = _fixture()
    a = fit_hmm3(x, sessions, code_commit="c" * 40)
    b = fit_hmm3(x, sessions, code_commit="c" * 40)
    assert a.model_id == b.model_id
    assert a.checkpoint_sha256 == b.checkpoint_sha256


def test_tamper_de_config_o_pesos_falla_cerrado():
    x, sessions = _fixture()
    cp = fit_hmm3(x, sessions, code_commit="d" * 40)
    raw = json.loads(json.dumps(cp.to_dict()))
    raw["config"]["tol"] = 0.5
    with pytest.raises(ValueError, match="config_sha256"):
        HMM3Checkpoint.from_dict(raw)


def test_normalizacion_es_exclusivamente_la_muestra_entregada_a_train():
    x, sessions = _fixture()
    cp = fit_hmm3(x[:600], sessions[:600], code_commit="e" * 40)
    assert np.allclose(cp.normalizer_mean, x[:600].mean(axis=0))
    assert not np.allclose(cp.normalizer_mean, x.mean(axis=0))


def test_sequence_id_repetido_en_bloques_no_contiguos_falla():
    x, _ = _fixture()
    ids = ["a"] * 300 + ["b"] * 300 + ["a"] * (len(x) - 600)
    with pytest.raises(ValueError, match="no contiguo"):
        fit_hmm3(x, ids, code_commit="f" * 40)
