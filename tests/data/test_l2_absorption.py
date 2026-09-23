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
