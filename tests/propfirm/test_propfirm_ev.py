"""El simulador de prop firms contra la teoría (Villahermosa 2026, Prop. 1; Hall 2026): fixtures chicos y
deterministas."""
from __future__ import annotations

from dataclasses import replace

from edgelab.propfirm.ev import Strategy, report, simulate
from edgelab.propfirm.requirements import requirement
from edgelab.propfirm.rules import Rules
from edgelab.propfirm.scraper import extract, html_to_text


def _rules(**kw):
    base = dict(firm="T", plan="t", account_size=25000, eval_fee=0.0, profit_target=1250, max_loss=1000,
                drawdown_kind="static", min_trading_days=1, payout_split=0.9, payout_max_count=1)
    base.update(kw)
    return Rules(**base)


def _flip(p=0.5, step=50.0):
    return Strategy(p_win=p, tp=step, sl=step, cost_rt=0.0, trades_per_day=10, contracts=1, mae_win=0.0)


def test_techo_geometrico_piso_fijo_sin_ventaja():
    r = _rules()
    s = simulate(r, _flip(), n_paths=6000, eval_days=400, funded_days=1)
    assert abs(s["p_pass"] - r.geometric_ceiling()) < 0.03       # L/(T+L) = 0,444


def test_trailing_no_supera_al_piso_fijo():
    fijo = simulate(_rules(), _flip(), n_paths=6000, eval_days=400, funded_days=1)["p_pass"]
    trail = simulate(_rules(drawdown_kind="eod_trailing"), _flip(), n_paths=6000, eval_days=400, funded_days=1)["p_pass"]
    intra = simulate(_rules(drawdown_kind="intraday_trailing"), _flip(), n_paths=6000, eval_days=400, funded_days=1)["p_pass"]
    assert trail <= fijo + 0.01 and intra <= trail + 0.01


def test_costos_bajan_el_pase():
    sin = simulate(_rules(), _flip(), n_paths=6000, eval_days=400, funded_days=1)["p_pass"]
    con = simulate(_rules(), replace(_flip(), cost_rt=5.0), n_paths=6000, eval_days=400, funded_days=1)["p_pass"]
    assert con < sin


def test_consistencia_no_ayuda():
    sin = simulate(_rules(), _flip(), n_paths=4000, eval_days=200, funded_days=1)["p_pass"]
    con = simulate(_rules(consistency_cap=0.5), _flip(), n_paths=4000, eval_days=200, funded_days=1)["p_pass"]
    assert con <= sin + 0.01


def test_control_de_ventaja_cero_y_aporte():
    r = _rules(eval_fee=70.0, drawdown_kind="eod_trailing", payout_cap=900, payout_max_count=3)
    s = Strategy(p_win=0.56, tp=50, sl=50, cost_rt=2.0, trades_per_day=4)
    rep = report(r, s, n_paths=3000, eval_days=60, funded_days=60)
    assert rep["ventaja_cero"]["ev"] < 0                          # sin ventaja, la cuota no se recupera
    assert rep["aporte_estrategia"] > 0


def test_requisito_acierto_minimo_supera_al_sin_ventaja():
    r = _rules(eval_fee=70.0, drawdown_kind="eod_trailing", payout_cap=900, payout_max_count=3)
    q = requirement(r, "MES", tp_ticks=40, sl_ticks=40, trades_per_day=2, contracts=1, n_paths=1500,
                    eval_days=60, funded_days=60)
    assert q["acierto_minimo"] > q["acierto_sin_ventaja"]
    assert q["ventaja_neta_min_ticks"] > 0


def test_scraper_extrae_candidatos_con_contexto():
    txt = html_to_text("<p>Profit Target: $3,000</p><script>x=1</script><p>Maximum Loss Limit $2,000 trailing</p>")
    c = extract(txt)
    campos = {x["campo"] for x in c}
    assert "profit_target" in campos and "max_loss" in campos
    assert all(x["numeros"] for x in c)


def test_compuerta_usa_el_ic_inferior():
    from edgelab.propfirm.requirements import gate
    r = _rules(eval_fee=70.0, drawdown_kind="eod_trailing", payout_cap=900, payout_max_count=3)
    g = gate(r, "ES", 20, 20, 2, net_ticks_point=3.0, net_ticks_lo=-1.0, n_paths=1500, eval_days=60, funded_days=60)
    assert not g["pasa"]                                          # sólo paga en el punto: no pasa
    assert g["punto"]["ev"] > g["ic_inferior"]["ev"]
