"""Detectores PROVISIONALES de iceberg/spoofing sobre secuencias sinteticas de eventos L2 (sin datos reales)."""
import numpy as np

from edgelab.research.l2_manipulation_heuristics import ASK, BID, IcebergTracker, SpoofTracker, large_size_thresholds


def test_umbral_grande_ignora_las_bajas_y_es_por_lado():
    side = np.array([ASK, ASK, ASK, BID, BID, ASK])
    op = np.array([0, 1, 2, 0, 1, 1])       # la baja (op=2) no debe contar
    size = np.array([10.0, 100.0, 999.0, 5.0, 50.0, 20.0])
    thr = large_size_thresholds(side, op, size, pctl=50.0)
    assert thr[ASK] == np.percentile([10.0, 100.0, 20.0], 50.0)
    assert thr[BID] == np.percentile([5.0, 50.0], 50.0)


def test_iceberg_se_marca_tras_min_refills_consumo_seguido_de_relleno():
    t = IcebergTracker(trade_window_s=2, refill_window_s=5, refill_min_ratio=0.7, min_refills=3)
    tick = 1000
    t.on_l2_event(BID, 0, tick, 50, ts=0)             # nace la orden
    for k in range(3):
        base = 10 * k
        t.on_trade(tick, ts=base + 1, aggressor=-1)   # venta agresiva la consume (golpea el BID)
        t.on_l2_event(BID, 1, tick, 5, ts=base + 1)    # el tamano baja fuerte
        t.on_l2_event(BID, 1, tick, 48, ts=base + 3)   # y se rellena a un tamano parecido al original
    cands = t.candidates()
    assert len(cands) == 1 and cands[0]["side"] == BID and cands[0]["tick"] == tick and cands[0]["refills"] == 3


def test_iceberg_no_se_marca_si_el_relleno_llega_sin_trade_previo():
    t = IcebergTracker(min_refills=1)
    tick = 2000
    t.on_l2_event(ASK, 0, tick, 50, ts=0)
    t.on_l2_event(ASK, 1, tick, 5, ts=1)     # baja SIN que haya habido un trade en ese precio antes
    t.on_l2_event(ASK, 1, tick, 48, ts=3)
    assert t.candidates() == []


def test_iceberg_no_se_marca_si_el_relleno_es_muy_chico_o_muy_tarde():
    t = IcebergTracker(trade_window_s=2, refill_window_s=5, refill_min_ratio=0.7, min_refills=1)
    tick = 3000
    t.on_l2_event(BID, 0, tick, 100, ts=0)
    t.on_trade(tick, ts=1, aggressor=-1)
    t.on_l2_event(BID, 1, tick, 10, ts=1)
    t.on_l2_event(BID, 1, tick, 50, ts=2)     # relleno insuficiente (< 70% de 100)
    t.on_l2_event(BID, 0, tick, 100, ts=10)
    t.on_trade(tick, ts=11, aggressor=-1)
    t.on_l2_event(BID, 1, tick, 5, ts=11)
    t.on_l2_event(BID, 1, tick, 95, ts=20)    # relleno bueno pero fuera de la ventana de 5s
    assert t.candidates() == []


def test_spoof_se_marca_si_desaparece_rapido_sin_llenarse():
    s = SpoofTracker(thresholds={ASK: 100.0, BID: 100.0}, max_lifetime_s=20, max_fill_ratio=0.2)
    tick = 5000
    s.on_l2_event(ASK, 0, tick, 200, ts=0)     # aparece grande
    s.on_trade(tick, ts=3, size=10, aggressor=1)   # se llena muy poco
    s.on_l2_event(ASK, 2, tick, 0, ts=5)       # se borra rapido
    cands = s.candidates()
    assert len(cands) == 1
    c = cands[0]
    assert c["side"] == ASK and c["tick"] == tick and c["peak_size"] == 200 and round(c["filled_ratio"], 3) == 0.05


def test_spoof_no_se_marca_si_se_llena_o_vive_mucho_o_nunca_llega_al_umbral():
    s = SpoofTracker(thresholds={ASK: 100.0, BID: 100.0}, max_lifetime_s=20, max_fill_ratio=0.2)
    # se llena de verdad: no es spoof
    s.on_l2_event(BID, 0, 100, 200, ts=0)
    s.on_trade(100, ts=3, size=180, aggressor=-1)
    s.on_l2_event(BID, 2, 100, 0, ts=5)
    # vive demasiado (persiste, no es "aparece y se va rapido")
    s.on_l2_event(BID, 0, 200, 200, ts=0)
    s.on_l2_event(BID, 2, 200, 0, ts=30)
    # nunca llega al umbral de "grande"
    s.on_l2_event(BID, 0, 300, 50, ts=0)
    s.on_l2_event(BID, 2, 300, 0, ts=1)
    assert s.candidates() == []


def test_spoof_sigue_vivo_al_cierre_de_sesion_no_se_emite():
    s = SpoofTracker(thresholds={ASK: 100.0, BID: 100.0})
    s.on_l2_event(ASK, 0, 700, 500, ts=0)   # nunca se cierra (no hay op=2 ni caida bajo umbral)
    assert s.candidates() == []


def test_iceberg_min_avg_size_filtra_por_lado():
    t = IcebergTracker(trade_window_s=2, refill_window_s=5, refill_min_ratio=0.7, min_refills=1,
                       min_avg_size={ASK: 100.0, BID: 5.0})
    for side, tick in ((ASK, 1000), (BID, 2000)):
        t.on_l2_event(side, 0, tick, 10, ts=0)
        t.on_trade(tick, ts=1, aggressor=(1 if side == ASK else -1))
        t.on_l2_event(side, 1, tick, 1, ts=1)
        t.on_l2_event(side, 1, tick, 9, ts=2)
    cands = t.candidates()
    assert len(cands) == 1 and cands[0]["side"] == BID          # el ASK queda afuera: 10 < 100
