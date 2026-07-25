"""Golden tests del simulador — `docs/execution_simulator_spec.md` §9.

La spec está SELLADA: estos números son CONTRATO. Si un golden no sale, se
frena y se reporta — está PROHIBIDO ajustar el golden para que pase.

6E: tick = 0.00005, tick_value = $6.25, comisión $2.20/pata (RT $4.40).
Escenario `base` (slippage 1 tick/pata). Precios expresados en TICKS enteros.
"""
import pytest

from edgelab.research.sim import simulate

TICK = 0.00005
TV = 6.25


def _s(ts, last, bid, ask, session="A", low=None, high=None):
    """Step de tick (low=high=last) salvo que se den low/high (step de barra)."""
    return dict(ts=ts, last=last * TICK, bid=bid * TICK, ask=ask * TICK,
                low=(low if low is not None else last) * TICK,
                high=(high if high is not None else last) * TICK,
                session_id=session)


def _sig(av, tgt=10, stp=5, tstop=0, sid="S1", d=1):
    return dict(signal_id=sid, available_at=av, dir=d,
                target_ticks=tgt, stop_ticks=stp, time_stop_ms=tstop)


def _run(signals, steps, **kw):
    kw.setdefault("close_at_session_end", True)   # CAMP-001 E4
    return simulate(signals, steps, scenario="base", tick_size=TICK,
                    tick_value=TV, check_guard=False, **kw)


def _approx(a, b):
    return abs(a - b) < 1e-9


# --------------------------------------------------------------------------- #
def test_G1_entrada_mas_target():
    steps = [_s(1000, 23000, 23000, 23001), _s(1100, 23000, 23000, 23001),
             _s(1200, 23010, 23009, 23010), _s(1300, 23013, 23012, 23013)]
    r = _run([_sig(1000)], steps)
    assert len(r.trades) == 1
    t = r.trades[0]
    assert t["entry_ts"] == 1100                       # primer step ts > 1000
    assert _approx(t["entry_px"], 23002 * TICK)        # ask 23001 + 1 slip
    assert t["exit_reason"] == "target"
    assert _approx(t["exit_px"], 23011 * TICK)         # 23012 - 1 slip
    assert _approx(t["bruto_ticks"], 11.5)
    assert _approx(t["spread_ticks"], 0.5)
    assert _approx(t["slippage_ticks"], 2.0)
    assert _approx(t["comision_usd"], 4.40)
    assert _approx(t["neto_ticks"], 9.0)
    assert _approx(t["neto_usd"], 51.85)


def test_G2_entrada_mas_stop():
    steps = [_s(1000, 23000, 23000, 23001), _s(1100, 23000, 23000, 23001),
             _s(1200, 22996, 22996, 22997)]
    r = _run([_sig(1000)], steps)
    t = r.trades[0]
    assert t["exit_reason"] == "stop"
    assert _approx(t["entry_px"], 23002 * TICK)
    assert _approx(t["exit_px"], 22996 * TICK)         # 22997 - 1 slip
    assert _approx(t["bruto_ticks"], -3.5)
    assert _approx(t["spread_ticks"], 0.5)
    assert _approx(t["slippage_ticks"], 2.0)
    assert _approx(t["neto_ticks"], -6.0)
    assert _approx(t["neto_usd"], -41.90)


def test_G3_ambiguo_gana_el_adverso():
    # s2 es step de BARRA: low/high abarcan target (23012) Y stop (22997)
    steps = [_s(1000, 23000, 23000, 23001), _s(1100, 23000, 23000, 23001),
             _s(1200, 23015, 23014, 23015, low=22990, high=23020)]
    r = _run([_sig(1000)], steps)
    t = r.trades[0]
    assert t["exit_reason"] == "stop_ambiguous"        # GANA EL ADVERSO
    assert _approx(t["exit_px"], 22996 * TICK)
    assert _approx(t["neto_ticks"], -6.0)
    assert _approx(t["neto_usd"], -41.90)


def test_G4_time_stop():
    steps = [_s(1000, 23000, 23000, 23001), _s(1100, 23000, 23000, 23001),
             _s(1200, 23005, 23004, 23005), _s(1300, 23006, 23005, 23006)]
    r = _run([_sig(1000, tstop=200)], steps)           # deadline = 1100+200 = 1300
    t = r.trades[0]
    assert t["exit_reason"] == "time_stop"
    assert t["exit_ts"] == 1300
    assert _approx(t["exit_px"], 23004 * TICK)         # bid 23005 - 1 slip
    assert _approx(t["bruto_ticks"], 5.0)              # mid->mid
    assert _approx(t["spread_ticks"], 1.0)             # 2 patas cruzan el book
    assert _approx(t["slippage_ticks"], 2.0)
    assert _approx(t["neto_ticks"], 2.0)
    assert _approx(t["neto_usd"], 8.10)


def test_G5_senal_en_el_ultimo_step_no_ejecuta():
    steps = [_s(1000, 23000, 23000, 23001), _s(1100, 23000, 23000, 23001)]
    r = _run([_sig(1100)], steps)                      # no hay step con ts > 1100
    assert r.trades == []
    assert r.rejected == [dict(signal_id="S1", reason="no_execution_step")]


def test_G6_sesion_sin_steps_posteriores_expira():
    steps = [_s(1000, 23000, 23000, 23001, session="A"),
             _s(1100, 23000, 23000, 23001, session="A"),
             _s(9000, 23000, 23000, 23001, session="B")]
    r = _run([_sig(1100)], steps)
    assert r.trades == []
    assert r.rejected == [dict(signal_id="S1", reason="session_boundary_no_fill")]


def test_G7_posicion_abierta_al_borde_de_datos():
    steps = [_s(1000, 23000, 23000, 23001), _s(1100, 23000, 23000, 23001),
             _s(1200, 23004, 23003, 23004)]
    r = _run([_sig(1000)], steps)                      # ni stop ni target ni time stop
    t = r.trades[0]
    assert t["exit_reason"] == "data_edge"
    assert _approx(t["exit_px"], 23002 * TICK)         # bid 23003 - 1 slip
    assert _approx(t["bruto_ticks"], 3.0)
    assert _approx(t["spread_ticks"], 1.0)
    assert _approx(t["slippage_ticks"], 2.0)
    assert _approx(t["neto_ticks"], 0.0)               # plano en bruto...
    assert _approx(t["neto_usd"], -4.40)               # ...pierde exactamente la comisión
