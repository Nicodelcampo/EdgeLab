import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

P = Path(__file__).resolve().parents[1] / "tools" / "r3_direccion.py"
sys.path.insert(0, str(P.parent))
spec = importlib.util.spec_from_file_location("r3_direccion", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _tendencia(sign=1.0):
    first = np.arange(390, dtype=float) * sign
    last = first + 0.5 * sign
    net = np.full(390, sign)
    return first, last, net


def test_ventanas_y_signo_en_tendencia_alcista():
    first, last, net = _tendencia(1.0)
    cells = m.session_cells(first, last, net)
    n, s, h = cells[("A", 15, 15)]
    assert n == 25 and h == 25 and s > 0                 # m = 15, 30, ... 375 -> 25 decisiones, todas aciertan
    n, s, h = cells[("B", 60, 60)]
    assert n == 5 and h == 5                              # m = 60..300 (m+H <= 390)


def test_tendencia_bajista_con_signo_correcto_tambien_acierta():
    first, last, net = _tendencia(-1.0)
    n, s, h = m.session_cells(first, last, net)[("A", 30, 30)]
    assert n > 0 and h == n and s > 0


def test_sin_senal_o_sin_datos_se_descarta():
    first = np.full(390, np.nan); last = np.full(390, np.nan); net = np.zeros(390)
    assert all(v[0] == 0 for v in m.session_cells(first, last, net).values())
    first, last, net = _tendencia(1.0)
    net[:] = 0                                            # B sin flujo neto = empate
    assert m.session_cells(first, last, net)[("B", 15, 15)][0] == 0


def test_holm_es_monotono_y_acotado():
    adj = m.holm(np.array([0.001, 0.02, 0.04, 0.5]))
    assert list(np.round(adj, 3)) == [0.004, 0.06, 0.08, 0.5]


def test_analisis_detecta_ventaja_clara_y_no_inventa_ninguna():
    rng = np.random.default_rng(1)
    sessions = []
    for i in range(60):
        cells = {("A", 15, 15): (24, 24 * 6.0 + float(rng.normal(0, 3)), 20)}      # media bruta ~6 ticks
        sessions.append((20250801 + i, cells))
    idx = m.stationary_idx(60, B=300, seed=1)
    r = m.analyze(sessions, 2.0, 3.0, idx)[("A", 15, 15)]
    assert r["net_mean_F_high"] > 2.5 and r["ci95_net_F_high"][0] > 0 and r["p_one_sided"] < 0.01
    sessions = [(20250801 + i, {("A", 15, 15): (24, float(rng.normal(0, 40)), 12)}) for i in range(60)]
    r = m.analyze(sessions, 2.0, 3.0, idx)[("A", 15, 15)]
    assert r["ci95_net_F_high"][0] < 0


def test_replicacion_se_niega_a_repetirse_y_exige_celdas(tmp_path, monkeypatch):
    (tmp_path / "REPLICATION_OPENED.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["x", "--release", str(tmp_path), "--partition", "replication", "--out", str(tmp_path)])
    with pytest.raises(SystemExit, match="ya se abrio"):
        m.main()
    (tmp_path / "REPLICATION_OPENED.json").unlink()
    with pytest.raises(SystemExit, match="exige --cells"):
        m.main()
