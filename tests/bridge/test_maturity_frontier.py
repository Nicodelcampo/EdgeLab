"""Frontera de madurez del matcher de paridad (A2).

NT8 exporta más rango que la ventana Python; las zonas creadas cerca del final
no completan su ciclo (max_age) dentro de la ventana común. Regla: geometría se
compara SIEMPRE; lifecycle/touches solo para zonas maduras. NO es tolerancia:
una zona MADURA con STATE_ORDER_DIFF sigue siendo WARN/FAIL.
"""
import json
import os

import pytest

from edgelab.bridge import parity


def _py(zid, top, bottom, created_ms, state, touches=0):
    return dict(id=zid, top=top, bottom=bottom, created_ms=created_ms,
                state=state, touches=touches)


def _nt8(zid, top, bottom, created_ms, state, touches=0):
    return dict(id=zid, top=top, bottom=bottom, created_ms=created_ms,
                state=state, touches=touches)


TICK = 0.25
FRONTIER = 10_000       # zonas creadas > 10000 ms son inmaduras (cola)


def test_immature_state_diff_suppressed():
    # zona creada DESPUÉS de la frontera con estado distinto -> no WARN (cola)
    py = [_py("Z1", 100, 99, 15_000, "VIRGIN", touches=0)]
    nt8 = [_nt8("Z1", 100, 99, 15_000, "EXPIRED", touches=3)]
    r = parity.match_zones(py, nt8, TICK, maturity_frontier_ms=FRONTIER)
    assert r["gate"] == "PASS"                     # geometría ok, lifecycle en cola
    assert r["summary"]["counts"].get("STATE_ORDER_DIFF") is None
    assert r["summary"]["counts"].get("FEATURE_DIFF") is None
    assert r["summary"]["immature_tail"] == 1
    assert r["summary"]["counts"].get("MATURITY_TAIL") == 1


def test_mature_state_diff_still_warn():
    # ADVERSARIAL: misma discrepancia pero en zona MADURA (antes de la frontera)
    # -> DEBE seguir siendo WARN.
    py = [_py("Z1", 100, 99, 5_000, "VIRGIN", touches=0)]
    nt8 = [_nt8("Z1", 100, 99, 5_000, "EXPIRED", touches=3)]
    r = parity.match_zones(py, nt8, TICK, maturity_frontier_ms=FRONTIER)
    assert r["gate"] == "WARN"
    assert r["summary"]["counts"].get("STATE_ORDER_DIFF") == 1
    assert r["summary"]["counts"].get("FEATURE_DIFF") == 1
    assert r["summary"]["immature_tail"] == 0


def test_geometry_always_compared_even_immature():
    # geometría distinta en zona inmadura -> SIGUE siendo GEOMETRY_DIFF (FAIL)
    py = [_py("Z1", 100, 99, 15_000, "VIRGIN")]
    nt8 = [_nt8("Z1", 101, 100, 15_000, "VIRGIN")]   # +1 tick arriba/abajo
    r = parity.match_zones(py, nt8, TICK, maturity_frontier_ms=FRONTIER)
    assert r["gate"] == "FAIL"
    assert r["summary"]["counts"].get("GEOMETRY_DIFF") == 1


def test_none_frontier_is_previous_behavior():
    # sin frontera, la discrepancia de estado siempre cuenta (compat)
    py = [_py("Z1", 100, 99, 15_000, "VIRGIN")]
    nt8 = [_nt8("Z1", 100, 99, 15_000, "EXPIRED")]
    r = parity.match_zones(py, nt8, TICK, maturity_frontier_ms=None)
    assert r["gate"] == "WARN"
    assert r["summary"]["immature_tail"] == 0


def test_immature_matched_clean_when_lifecycle_agrees():
    # zona inmadura pero con estado/touches iguales -> MATCHED, sin MATURITY_TAIL
    py = [_py("Z1", 100, 99, 15_000, "VIRGIN", touches=1)]
    nt8 = [_nt8("Z1", 100, 99, 15_000, "VIRGIN", touches=1)]
    r = parity.match_zones(py, nt8, TICK, maturity_frontier_ms=FRONTIER)
    assert r["gate"] == "PASS"
    assert r["summary"]["counts"].get("MATURITY_TAIL") is None
    assert r["summary"]["immature_tail"] == 0


def test_boundary_created_exactly_at_frontier_is_mature():
    # Operador exacto (copiado del código, run_nt8_bridge.py + parity.py):
    #   frontier_ms = end_ns[len(bars)-1-max_age_bars] // 1_000_000
    #   immature = created_ms > frontier_ms   (parity.py línea ~93-95)
    # => MADURA si created_ms <= frontier_ms (comparación NO estricta). Una zona
    # cuyo ciclo termina EXACTAMENTE en la frontera (created_ms == FRONTIER) debe
    # tratarse como MADURA: lifecycle SE compara, un diff sigue dando WARN.
    py = [_py("Z1", 100, 99, FRONTIER, "VIRGIN", touches=0)]
    nt8 = [_nt8("Z1", 100, 99, FRONTIER, "EXPIRED", touches=3)]
    r = parity.match_zones(py, nt8, TICK, maturity_frontier_ms=FRONTIER)
    assert r["gate"] == "WARN"                      # NO suprimido: es madura
    assert r["summary"]["counts"].get("STATE_ORDER_DIFF") == 1
    assert r["summary"]["counts"].get("FEATURE_DIFF") == 1
    assert r["summary"]["counts"].get("MATURITY_TAIL") is None
    assert r["summary"]["immature_tail"] == 0
    # un tick de diferencia (1 ms después de la frontera) sí es inmadura
    py2 = [_py("Z2", 100, 99, FRONTIER + 1, "VIRGIN", touches=0)]
    nt82 = [_nt8("Z2", 100, 99, FRONTIER + 1, "EXPIRED", touches=3)]
    r2 = parity.match_zones(py2, nt82, TICK, maturity_frontier_ms=FRONTIER)
    assert r2["gate"] == "PASS"
    assert r2["summary"]["immature_tail"] == 1


_REAL_ARTIFACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "runs", "nt8_bridge", "parity_gaps2_0926", "parity_report.json")


@pytest.mark.skipif(not os.path.exists(_REAL_ARTIFACT),
                    reason="artefacto runs/nt8_bridge/parity_gaps2_0926/ no disponible "
                    "en este checkout (runs/ está gitignored; ver docs/nt8_bridge.md "
                    "para regenerarlo con el oráculo real de oracles/Gaps2_6E_0926.csv)")
def test_real_gaps2_pass_run_has_zero_mature_lifecycle_diffs():
    """Regresión sobre el run PASS real de Gaps2 (F4C, 6E 09-26, 1316/1316
    zonas). Congela la evidencia registrada en el commit 0555e5d: cero diffs
    de lifecycle/features en zonas MADURAS, y la cola inmadura queda contable
    como MATURITY_TAIL (no oculta, no cuenta como WARN/FAIL)."""
    with open(_REAL_ARTIFACT, encoding="utf-8") as fh:
        report = json.load(fh)
    summary = next(iter(report.values()))["summary"]
    assert summary["gate"] == "PASS"
    assert summary["py_zones"] == summary["nt8_zones"] == summary["matched_pairs"] == 1316
    counts = summary["counts"]
    # (a) cero diffs de lifecycle/features en zonas MADURAS
    mature_lifecycle_diff_count = counts.get("STATE_ORDER_DIFF", 0) + counts.get("FEATURE_DIFF", 0)
    assert mature_lifecycle_diff_count == 0
    assert counts.get("GEOMETRY_DIFF", 0) == 0
    assert counts.get("MISSING_IN_NT8", 0) == 0 and counts.get("MISSING_IN_PYTHON", 0) == 0
    # (c) MATURITY_TAIL presente y contable (cola de ventana, no oculta)
    assert summary["immature_tail"] > 0
    assert counts.get("MATURITY_TAIL") == summary["immature_tail"]
