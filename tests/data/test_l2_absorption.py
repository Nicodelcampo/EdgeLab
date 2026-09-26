"""AbsorptionTracker: volumen agresivo grande en un precio que el precio no atraviesa dentro de la ventana."""
from edgelab.research.l2_manipulation_heuristics import ASK, BID, AbsorptionTracker

W = 10_000_000


def _noise(t):
    for i in range(200):                                   # fondo: muchas celdas chicas para fijar el percentil
        t.on_trade(1000 + i % 7, i * W + 1, 1.0, 1 if i % 2 else -1)


def test_buy_flow_that_does_not_lift_price_is_absorption():
    t = AbsorptionTracker(pctl=99.0)
    _noise(t)
    base = 500 * W
    for k in range(5):
        t.on_trade(2000, base + k * 1000, 50.0, +1)        # compras agresivas grandes en 2000
    t.on_trade(1999, base + 9000, 1.0, -1)                 # nada por encima de 2000 en la ventana
    c = [x for x in t.candidates() if x["tick"] == 2000]
    assert len(c) == 1 and c[0]["side"] == ASK and c[0]["attributed_volume"] == 250.0
    assert c[0]["available_ts_us"] == base + W and c[0]["status"] == "HEURISTIC_UNVALIDATED"


def test_flow_that_breaks_the_level_is_not_absorption():
    t = AbsorptionTracker(pctl=99.0)
    _noise(t)
    base = 500 * W
    for k in range(5):
        t.on_trade(2000, base + k * 1000, 50.0, +1)
    t.on_trade(2001, base + 9000, 1.0, +1)                 # el precio atravesó 2000 hacia arriba
    assert not [x for x in t.candidates() if x["tick"] == 2000]


def test_sell_side_and_neutral_not_credited():
    t = AbsorptionTracker(pctl=99.0)
    _noise(t)
    base = 600 * W
    for k in range(5):
        t.on_trade(3000, base + k, 50.0, -1)
        t.on_trade(3000, base + k, 500.0, 0)               # neutral enorme: no se acredita
    c = [x for x in t.candidates() if x["tick"] == 3000]
    assert len(c) == 1 and c[0]["side"] == BID and c[0]["attributed_volume"] == 250.0
    assert c[0]["ambiguous_volume"] == 2500.0


def test_causal_threshold_never_uses_future_windows():
    """Volumen grande ANTES de tener historia: no hay umbral, no hay candidato (antes el percentil de la sesion
    completa lo marcaba usando las ventanas futuras)."""
    t = AbsorptionTracker(pctl=99.0)
    for k in range(5):
        t.on_trade(2000, 1 * W + k * 1000, 50.0, +1)      # ventana 1: grande y temprano
    _noise_after = [t.on_trade(1000 + i % 7, (10 + i) * W + 1, 1.0, 1 if i % 2 else -1) for i in range(300)]
    assert not [x for x in t.candidates() if x["tick"] == 2000]
    legacy = AbsorptionTracker(pctl=99.0, causal=False)
    for k in range(5):
        legacy.on_trade(2000, 1 * W + k * 1000, 50.0, +1)
    for i in range(300):
        legacy.on_trade(1000 + i % 7, (10 + i) * W + 1, 1.0, 1 if i % 2 else -1)
    assert [x for x in legacy.candidates() if x["tick"] == 2000]     # el modo viejo si lo marcaba (fuga)


def test_causal_candidate_threshold_comes_from_the_past():
    t = AbsorptionTracker(pctl=99.0)
    _noise(t)
    for k in range(5):
        t.on_trade(2000, 500 * W + k * 1000, 50.0, +1)
    c = [x for x in t.candidates() if x["tick"] == 2000][0]
    assert c["scale_scope"] == "CAUSAL_PRIOR_WINDOWS" and c["volume_threshold"] <= 1.0
