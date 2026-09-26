"""Tests de propiedad del simulador (además de los golden).

Invariantes que deben valer para CUALQUIER entrada, no solo los casos de la
spec: causalidad, identidad aditiva de costos, determinismo, firewall del
holdout y el cierre de sesión sellado en CAMP-001 E4.
"""
import pytest

from edgelab.research.holdout_guard import HoldoutViolation
from edgelab.research.sim import simulate

TICK, TV = 0.00005, 6.25


def _steps(n=40, t0=1_000_000, dt=1000, session_every=None, base=23000):
    """Stream determinista (zig-zag suave), sin aleatoriedad."""
    out = []
    for i in range(n):
        px = base + (i % 7) - 3
        sess = "A" if not session_every else "S%d" % (i // session_every)
        out.append(dict(ts=t0 + i * dt, last=px * TICK, bid=px * TICK,
                        ask=(px + 1) * TICK, low=px * TICK, high=px * TICK,
                        session_id=sess))
    return out


def _sigs(steps, k=6, tstop=0):
    return [dict(signal_id="S%d" % i, available_at=steps[i * 3]["ts"],
                 dir=1 if i % 2 == 0 else -1, target_ticks=4, stop_ticks=3,
                 time_stop_ms=tstop) for i in range(k)]


def _run(steps, sigs, **kw):
    kw.setdefault("close_at_session_end", True)
    return simulate(sigs, steps, scenario="base", tick_size=TICK, tick_value=TV,
                    check_guard=False, **kw)


# --------------------------- causalidad ------------------------------------ #
def test_entrada_siempre_estrictamente_posterior_a_available_at():
    steps = _steps()
    sigs = _sigs(steps)
    r = _run(steps, sigs)
    by_id = {s["signal_id"]: s for s in sigs}
    assert r.trades, "el fixture debe producir trades"
    for t in r.trades:
        assert t["entry_ts"] > by_id[t["signal_id"]]["available_at"]


def test_ningun_step_con_ts_igual_a_available_at_es_elegible():
    # un step EXACTAMENTE en available_at no puede ser el de entrada
    steps = _steps(n=5)
    av = steps[2]["ts"]
    r = _run(steps, [dict(signal_id="X", available_at=av, dir=1,
                          target_ticks=4, stop_ticks=3, time_stop_ms=0)])
    assert r.trades and r.trades[0]["entry_ts"] > av
    assert r.trades[0]["entry_ts"] == steps[3]["ts"]


def test_salida_nunca_anterior_a_la_entrada():
    steps = _steps()
    r = _run(steps, _sigs(steps))
    for t in r.trades:
        assert t["exit_ts"] >= t["entry_ts"] and t["bars_held"] >= 0


def test_una_sola_posicion_simultanea():
    steps = _steps(n=60)
    # señales muy juntas: varias deben rechazarse por position_open
    sigs = [dict(signal_id="S%d" % i, available_at=steps[i]["ts"], dir=1,
                 target_ticks=50, stop_ticks=50, time_stop_ms=0) for i in range(10)]
    r = _run(steps, sigs)
    # los intervalos [entry, exit] de los trades no se solapan
    iv = sorted((t["entry_ts"], t["exit_ts"]) for t in r.trades)
    for a, b in zip(iv, iv[1:]):
        assert b[0] >= a[1]
    assert any(x["reason"] == "position_open" for x in r.rejected)


# --------------------------- costos ---------------------------------------- #
@pytest.mark.parametrize("scenario", ["ideal", "base", "adverso", "severo"])
def test_identidad_aditiva_de_costos_por_trade(scenario):
    steps = _steps()
    r = simulate(_sigs(steps), steps, scenario=scenario, tick_size=TICK,
                 tick_value=TV, check_guard=False)
    assert r.trades
    for t in r.trades:
        # neto == bruto - spread - slippage (exacto)
        assert abs(t["neto_ticks"] - (t["bruto_ticks"] - t["spread_ticks"]
                                      - t["slippage_ticks"])) < 1e-9
        # neto_usd == neto_ticks * tick_value - comision
        assert abs(t["neto_usd"] - (t["neto_ticks"] * TV - t["comision_usd"])) < 1e-9


def test_escenario_ideal_no_cobra_nada():
    steps = _steps()
    r = simulate(_sigs(steps), steps, scenario="ideal", tick_size=TICK,
                 tick_value=TV, check_guard=False)
    for t in r.trades:
        assert t["slippage_ticks"] == 0 and t["comision_usd"] == 0


def test_escenarios_mas_adversos_nunca_mejoran_el_neto():
    steps = _steps()
    sigs = _sigs(steps)
    nets = {}
    for sc in ("ideal", "base", "adverso", "severo"):
        r = simulate(sigs, steps, scenario=sc, tick_size=TICK, tick_value=TV,
                     check_guard=False)
        nets[sc] = r.summary["net_usd"]
    assert nets["ideal"] >= nets["base"] >= nets["adverso"] >= nets["severo"]


# --------------------------- determinismo ---------------------------------- #
def test_mismo_input_mismo_digest():
    steps = _steps()
    sigs = _sigs(steps)
    a = _run(steps, sigs)
    b = _run(steps, sigs)
    assert a.digest == b.digest and a.digest
    assert a.trades == b.trades


def test_digest_cambia_si_cambia_el_resultado():
    steps = _steps()
    sigs = _sigs(steps)
    a = _run(steps, sigs)
    b = simulate(sigs, steps, scenario="severo", tick_size=TICK, tick_value=TV,
                 check_guard=False)
    assert a.digest != b.digest


# --------------------------- sesión (E4) ----------------------------------- #
def test_close_at_session_end_true_cierra_en_fin_de_sesion():
    steps = _steps(n=30, session_every=10)
    sigs = [dict(signal_id="X", available_at=steps[1]["ts"], dir=1,
                 target_ticks=999, stop_ticks=999, time_stop_ms=0)]
    r = _run(steps, sigs, close_at_session_end=True)
    assert r.trades[0]["exit_reason"] == "session_close"
    assert r.trades[0]["exit_ts"] == steps[9]["ts"]      # último step de la sesión S0


def test_close_at_session_end_false_no_cierra_por_sesion():
    steps = _steps(n=30, session_every=10)
    sigs = [dict(signal_id="X", available_at=steps[1]["ts"], dir=1,
                 target_ticks=999, stop_ticks=999, time_stop_ms=0)]
    r = _run(steps, sigs, close_at_session_end=False)
    assert r.trades[0]["exit_reason"] == "data_edge"


# --------------------------- firewall del holdout -------------------------- #
def test_guard_rechaza_datos_del_holdout_en_development(tmp_path):
    import datetime as dt
    t0 = int(dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
    steps = _steps(n=5, t0=t0)
    with pytest.raises(HoldoutViolation):
        simulate([], steps, scenario="base", tick_size=TICK, tick_value=TV,
                 check_guard=True, guard_log_path=str(tmp_path / "log.md"))


def test_guard_acepta_datos_pre_holdout(tmp_path):
    import datetime as dt
    t0 = int(dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
    steps = _steps(n=5, t0=t0)
    r = simulate([], steps, scenario="base", tick_size=TICK, tick_value=TV,
                 check_guard=True, guard_log_path=str(tmp_path / "log.md"))
    assert r.trades == []
