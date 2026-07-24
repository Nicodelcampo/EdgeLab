"""Frontera de madurez del matcher de paridad (A2).

NT8 exporta más rango que la ventana Python; las zonas creadas cerca del final
no completan su ciclo (max_age) dentro de la ventana común. Regla: geometría se
compara SIEMPRE; lifecycle/touches solo para zonas maduras. NO es tolerancia:
una zona MADURA con STATE_ORDER_DIFF sigue siendo WARN/FAIL.
"""
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
