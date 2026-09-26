"""Detectores PROVISIONALES de iceberg/spoofing sobre secuencias sinteticas de eventos L2 (sin datos reales).

Todo el tiempo es en MICROSEGUNDOS enteros (`*_ts_us`), igual que la version corregida del modulo. 1_000_000 = 1s.
"""
import numpy as np
import pytest

from edgelab.research.l2_manipulation_heuristics import (
    ASK, BID, IcebergTracker, SpoofTracker, large_size_thresholds)

US = 1_000_000        # 1 segundo, en microsegundos


def test_umbral_grande_ignora_las_bajas_y_es_por_lado():
    side = np.array([ASK, ASK, ASK, BID, BID, ASK])
    op = np.array([0, 1, 2, 0, 1, 1])       # la baja (op=2) no debe contar
    size = np.array([10.0, 100.0, 999.0, 5.0, 50.0, 20.0])
    thr = large_size_thresholds(side, op, size, pctl=50.0)
    assert thr[ASK] == np.percentile([10.0, 100.0, 20.0], 50.0)
    assert thr[BID] == np.percentile([5.0, 50.0], 50.0)


# ---------------------------------------------------------------------------------------------------------- ICEBERG

def test_iceberg_se_marca_tras_min_refills_consumo_seguido_de_relleno():
    t = IcebergTracker(trade_window_us=2 * US, refill_window_us=5 * US, refill_min_ratio=0.7, min_refills=3)
    tick = 1000
    t.on_l2_event(BID, 0, tick, 50, ts_us=0)             # nace la orden
    for k in range(3):
        base = 10 * US * k
        t.on_trade(tick, ts_us=base + US, size=45, aggressor=-1)   # venta agresiva la consume (golpea el BID)
        t.on_l2_event(BID, 1, tick, 5, ts_us=base + US)    # el tamano baja fuerte
        t.on_l2_event(BID, 1, tick, 48, ts_us=base + 3 * US)   # y se rellena a un tamano parecido al original
    cands = t.candidates()
    assert len(cands) == 1
    c = cands[0]
    assert c["side"] == BID and c["tick"] == tick and c["refill_count"] == 3
    assert c["status"] == "HEURISTIC_UNVALIDATED" and c["neutral_policy"] == "abstain"
    assert c["candidate_id"].startswith("ICE_") and len(c["candidate_id"]) == len("ICE_") + 16
    assert c["attributed_trade_volume"] == pytest.approx(3 * 45)
    assert c["ambiguous_trade_volume"] == 0.0


def test_iceberg_candidate_id_es_determinista_y_distingue_niveles():
    def one_candidate(tick):
        t = IcebergTracker(trade_window_us=2 * US, refill_window_us=5 * US, refill_min_ratio=0.7, min_refills=1)
        t.on_l2_event(BID, 0, tick, 50, ts_us=0)
        t.on_trade(tick, ts_us=US, size=45, aggressor=-1)
        t.on_l2_event(BID, 1, tick, 5, ts_us=US)
        t.on_l2_event(BID, 1, tick, 48, ts_us=2 * US)
        return t.candidates()[0]["candidate_id"]
    id_a1, id_a2, id_b = one_candidate(1000), one_candidate(1000), one_candidate(2000)
    assert id_a1 == id_a2                     # misma secuencia -> mismo id
    assert id_a1 != id_b                      # precio distinto -> id distinto


def test_iceberg_no_se_marca_si_el_relleno_llega_sin_trade_previo():
    t = IcebergTracker(min_refills=1)
    tick = 2000
    t.on_l2_event(ASK, 0, tick, 50, ts_us=0)
    t.on_l2_event(ASK, 1, tick, 5, ts_us=US)     # baja SIN que haya habido un trade en ese precio antes
    t.on_l2_event(ASK, 1, tick, 48, ts_us=3 * US)
    assert t.candidates() == []


def test_iceberg_no_se_marca_si_el_relleno_es_muy_chico_o_muy_tarde():
    t = IcebergTracker(trade_window_us=2 * US, refill_window_us=5 * US, refill_min_ratio=0.7, min_refills=1)
    tick = 3000
    t.on_l2_event(BID, 0, tick, 100, ts_us=0)
    t.on_trade(tick, ts_us=US, size=90, aggressor=-1)
    t.on_l2_event(BID, 1, tick, 10, ts_us=US)
    t.on_l2_event(BID, 1, tick, 50, ts_us=2 * US)     # relleno insuficiente (< 70% de 100)
    t.on_l2_event(BID, 0, tick, 100, ts_us=10 * US)
    t.on_trade(tick, ts_us=11 * US, size=90, aggressor=-1)
    t.on_l2_event(BID, 1, tick, 5, ts_us=11 * US)
    t.on_l2_event(BID, 1, tick, 95, ts_us=20 * US)    # relleno bueno pero fuera de la ventana de 5s
    assert t.candidates() == []


def test_iceberg_min_avg_size_filtra_por_lado():
    t = IcebergTracker(trade_window_us=2 * US, refill_window_us=5 * US, refill_min_ratio=0.7, min_refills=1,
                       min_avg_size={ASK: 100.0, BID: 5.0})
    for side, tick in ((ASK, 1000), (BID, 2000)):
        t.on_l2_event(side, 0, tick, 10, ts_us=0)
        t.on_trade(tick, ts_us=US, size=9, aggressor=(1 if side == ASK else -1))
        t.on_l2_event(side, 1, tick, 1, ts_us=US)
        t.on_l2_event(side, 1, tick, 9, ts_us=2 * US)
    cands = t.candidates()
    assert len(cands) == 1 and cands[0]["side"] == BID          # el ASK queda afuera: 10 < 100


def test_iceberg_delete_cierra_el_ciclo_no_cuenta_delete_mas_add_como_relleno():
    """Bug corregido en la auditoria: un DELETE dejaba `_pending` vivo; un ADD posterior (orden NUEVA) se leia
    como el relleno de la orden vieja que en realidad ya no existia."""
    t = IcebergTracker(trade_window_us=2 * US, refill_window_us=50 * US, refill_min_ratio=0.7, min_refills=1)
    tick = 4000
    t.on_l2_event(BID, 0, tick, 100, ts_us=0)
    t.on_trade(tick, ts_us=US, size=90, aggressor=-1)
    t.on_l2_event(BID, 1, tick, 10, ts_us=US)          # consumo parcial: pending queda abierto
    t.on_l2_event(BID, 2, tick, 0, ts_us=2 * US)       # DELETE explicito: cierra el nivel de verdad
    t.on_l2_event(BID, 0, tick, 95, ts_us=3 * US)      # ADD nuevo, mismo precio: es una orden DISTINTA
    assert t.candidates() == []                        # no debe leerse como relleno del pending viejo


def test_iceberg_dos_refills_del_mismo_consumo_no_se_cuentan_dos_veces():
    """Dos ADD/CHANGE sucesivos ambos por encima del ratio de relleno, sin un consumo nuevo en el medio: solo el
    PRIMERO cierra el ciclo pendiente (`_pending` se limpia); el segundo no encuentra pending y no suma refill."""
    t = IcebergTracker(trade_window_us=2 * US, refill_window_us=10 * US, refill_min_ratio=0.7, min_refills=1)
    tick = 5000
    t.on_l2_event(BID, 0, tick, 100, ts_us=0)
    t.on_trade(tick, ts_us=US, size=90, aggressor=-1)
    t.on_l2_event(BID, 1, tick, 10, ts_us=US)
    t.on_l2_event(BID, 1, tick, 95, ts_us=2 * US)      # relleno #1: cierra el pending
    t.on_l2_event(BID, 1, tick, 96, ts_us=3 * US)      # otro update grande, pero SIN un consumo nuevo antes
    assert len(t.candidates()) == 0 or t.candidates()[0]["refill_count"] == 1


def test_politica_abstain_no_atribuye_neutral_y_por_eso_no_hay_candidato():
    """Sin un trade ATRIBUIDO que explique la baja, "abstain" no abre el ciclo de consumo: no se inventa una
    causa para la baja de tamano. Es la lectura correcta de "no reparar silenciosamente"."""
    t = IcebergTracker(trade_window_us=2 * US, refill_window_us=5 * US, refill_min_ratio=0.7, min_refills=1,
                       neutral_policy="abstain")
    tick = 6000
    t.on_l2_event(BID, 0, tick, 50, ts_us=0)
    t.on_trade(tick, ts_us=US, size=45, aggressor=0)    # trade NEUTRAL (no resolvio agresor)
    t.on_l2_event(BID, 1, tick, 5, ts_us=US)
    t.on_l2_event(BID, 1, tick, 48, ts_us=2 * US)
    assert t.candidates() == []


def test_politica_distribute_y_credit_both_demuestran_el_doble_conteo_que_abstain_evita():
    """El bug real (auditoria 2026-09-21): con "credit_both_exploratory" la MISMA ejecucion neutral se acredita
    entera a los DOS lados que la estan vigilando a la vez, como si fueran dos consumos distintos. "distribute"
    reparte la misma ejecucion a la mitad en cada lado -- declarado, sin duplicar el volumen total."""
    def attributed_both_sides(policy):
        t = IcebergTracker(trade_window_us=2 * US, refill_window_us=5 * US, refill_min_ratio=0.7, min_refills=1,
                           neutral_policy=policy)
        for side in (ASK, BID):
            t.on_l2_event(side, 0, 6000, 50, ts_us=0)
        t.on_trade(6000, ts_us=US, size=45, aggressor=0)     # UNA sola ejecucion neutral, un solo precio
        for side in (ASK, BID):
            t.on_l2_event(side, 1, 6000, 5, ts_us=US)
            t.on_l2_event(side, 1, 6000, 48, ts_us=2 * US)
        cands = {c["side"]: c for c in t.candidates()}
        return cands[ASK]["attributed_trade_volume"], cands[BID]["attributed_trade_volume"]

    ask_d, bid_d = attributed_both_sides("distribute")
    assert ask_d == pytest.approx(22.5) and bid_d == pytest.approx(22.5)          # 45 repartido, no duplicado
    assert ask_d + bid_d == pytest.approx(45.0)

    ask_c, bid_c = attributed_both_sides("credit_both_exploratory")
    assert ask_c == pytest.approx(45.0) and bid_c == pytest.approx(45.0)          # la MISMA ejecucion, dos veces
    assert ask_c + bid_c == pytest.approx(90.0)                                   # doble conteo, ahora declarado


def test_neutral_policy_invalida_falla_cerrado():
    with pytest.raises(ValueError):
        IcebergTracker(neutral_policy="algo_raro")
    with pytest.raises(ValueError):
        SpoofTracker(thresholds={}, neutral_policy="algo_raro")


def test_iceberg_ventana_de_consumo_respeta_el_borde_en_microsegundos():
    """justo antes / en / justo despues del limite de trade_window_us."""
    def refill_cuenta(delta_trade_us):
        t = IcebergTracker(trade_window_us=2 * US, refill_window_us=10 * US, refill_min_ratio=0.7, min_refills=1)
        tick = 7000
        t.on_l2_event(BID, 0, tick, 100, ts_us=0)
        t.on_trade(tick, ts_us=delta_trade_us, size=90, aggressor=-1)
        t.on_l2_event(BID, 1, tick, 10, ts_us=2 * US)      # la baja ocurre siempre en ts=2*US
        t.on_l2_event(BID, 1, tick, 95, ts_us=3 * US)
        return len(t.candidates()) == 1
    assert refill_cuenta(2 * US - 1) is True          # trade justo antes del limite (dentro de la ventana)
    assert refill_cuenta(0) is True                   # trade en el limite exacto (ventana de 2s hacia atras)
    assert refill_cuenta(-1) is False                 # trade "despues" del evento de baja: temporalmente invalido


# ------------------------------------------------------------------------------------------------------------ SPOOF

def test_spoof_se_marca_si_desaparece_rapido_sin_llenarse():
    s = SpoofTracker(thresholds={ASK: 100.0, BID: 100.0}, max_lifetime_us=20 * US, max_fill_ratio=0.2)
    tick = 5000
    s.on_l2_event(ASK, 0, tick, 200, ts_us=0)     # aparece grande
    s.on_trade(tick, ts_us=3 * US, size=10, aggressor=1)   # se llena muy poco
    s.on_l2_event(ASK, 2, tick, 0, ts_us=5 * US)       # se borra rapido
    cands = s.candidates()
    assert len(cands) == 1
    c = cands[0]
    assert c["side"] == ASK and c["tick"] == tick and c["peak_visible_size"] == 200
    assert round(c["fill_ratio"], 3) == 0.05
    assert c["status"] == "HEURISTIC_UNVALIDATED"
    assert c["lifetime_us"] == 5 * US
    assert c["candidate_id"].startswith("SPOOF_")


def test_spoof_no_se_marca_si_se_llena_o_vive_mucho_o_nunca_llega_al_umbral():
    s = SpoofTracker(thresholds={ASK: 100.0, BID: 100.0}, max_lifetime_us=20 * US, max_fill_ratio=0.2)
    # se llena de verdad: no es spoof
    s.on_l2_event(BID, 0, 100, 200, ts_us=0)
    s.on_trade(100, ts_us=3 * US, size=180, aggressor=-1)
    s.on_l2_event(BID, 2, 100, 0, ts_us=5 * US)
    # vive demasiado (persiste, no es "aparece y se va rapido")
    s.on_l2_event(BID, 0, 200, 200, ts_us=0)
    s.on_l2_event(BID, 2, 200, 0, ts_us=30 * US)
    # nunca llega al umbral de "grande"
    s.on_l2_event(BID, 0, 300, 50, ts_us=0)
    s.on_l2_event(BID, 2, 300, 0, ts_us=US)
    assert s.candidates() == []


def test_spoof_sigue_vivo_al_cierre_de_sesion_no_se_emite():
    s = SpoofTracker(thresholds={ASK: 100.0, BID: 100.0})
    s.on_l2_event(ASK, 0, 700, 500, ts_us=0)   # nunca se cierra (no hay op=2 ni caida bajo umbral)
    assert s.candidates() == []


def test_spoof_politica_abstain_no_acredita_neutral():
    s = SpoofTracker(thresholds={ASK: 100.0}, max_lifetime_us=20 * US, max_fill_ratio=1.0, neutral_policy="abstain")
    s.on_l2_event(ASK, 0, 800, 200, ts_us=0)
    s.on_trade(800, ts_us=US, size=10, aggressor=0)
    s.on_l2_event(ASK, 2, 800, 0, ts_us=2 * US)
    c = s.candidates()[0]
    assert c["attributed_fill"] == 0.0 and c["ambiguous_fill"] == pytest.approx(10.0)


def test_spoof_distribute_y_credit_both_demuestran_el_doble_conteo_que_abstain_evita():
    def attributed_both_sides(policy):
        s = SpoofTracker(thresholds={ASK: 100.0, BID: 100.0}, max_lifetime_us=20 * US, max_fill_ratio=1.0,
                         neutral_policy=policy)
        for side in (ASK, BID):
            s.on_l2_event(side, 0, 800, 200, ts_us=0)
        s.on_trade(800, ts_us=US, size=10, aggressor=0)      # UNA sola ejecucion neutral
        for side in (ASK, BID):
            s.on_l2_event(side, 2, 800, 0, ts_us=2 * US)
        cands = {c["side"]: c for c in s.candidates()}
        return cands[ASK]["attributed_fill"], cands[BID]["attributed_fill"]

    ask_d, bid_d = attributed_both_sides("distribute")
    assert ask_d == pytest.approx(5.0) and bid_d == pytest.approx(5.0)
    assert ask_d + bid_d == pytest.approx(10.0)

    ask_c, bid_c = attributed_both_sides("credit_both_exploratory")
    assert ask_c == pytest.approx(10.0) and bid_c == pytest.approx(10.0)          # la MISMA ejecucion, dos veces
    assert ask_c + bid_c == pytest.approx(20.0)


def test_spoof_ventana_de_vida_respeta_el_borde_en_microsegundos():
    def vive(muerte_ts_us):
        s = SpoofTracker(thresholds={ASK: 100.0}, max_lifetime_us=5 * US, max_fill_ratio=1.0)
        s.on_l2_event(ASK, 0, 900, 200, ts_us=0)
        s.on_l2_event(ASK, 2, 900, 0, ts_us=muerte_ts_us)
        return len(s.candidates()) == 1
    assert vive(5 * US - 1) is True      # justo antes del limite
    assert vive(5 * US) is True          # en el limite exacto (inclusive, <=)
    assert vive(5 * US + 1) is False     # justo despues del limite


def test_spoof_no_nace_de_primer_change_grande():
 s=SpoofTracker(thresholds={ASK:100.0},max_fill_ratio=1.0);s.on_l2_event(ASK,1,1,200,0);s.on_l2_event(ASK,2,1,0,1);assert s.candidates()==[]

def test_spoof_cruce_observado_publica_birth_reason():
 s=SpoofTracker(thresholds={ASK:100.0},max_fill_ratio=1.0);s.on_l2_event(ASK,1,1,20,0);s.on_l2_event(ASK,1,1,200,1);s.on_l2_event(ASK,2,1,0,2);assert s.candidates()[0]["birth_reason"]=="THRESHOLD_CROSS"


def test_iceberg_suma_todos_los_trades_y_poda_ambiguos_viejos():
    t=IcebergTracker(trade_window_us=2*US,refill_window_us=5*US,refill_min_ratio=.7,min_refills=1)
    tick=4321;t.on_l2_event(BID,0,tick,100,0);t.on_trade(tick,US,10,0)
    t.on_trade(tick,3*US,20,-1);t.on_trade(tick,4*US,30,-1)
    t.on_l2_event(BID,1,tick,10,5*US);t.on_l2_event(BID,1,tick,90,6*US)
    c=t.candidates()[0];assert c["attributed_trade_volume"]==pytest.approx(50)
    assert c["attributed_trade_count"]==2 and c["ambiguous_trade_volume"]==0

def test_iceberg_no_reutiliza_el_mismo_trade_en_dos_descensos():
    t=IcebergTracker(trade_window_us=10*US,refill_window_us=10*US,refill_min_ratio=.7,min_refills=1)
    t.on_l2_event(BID,0,9,100,0);t.on_trade(9,US,20,-1);t.on_l2_event(BID,1,9,70,2*US)
    t.on_l2_event(BID,1,9,60,3*US);t.on_l2_event(BID,1,9,95,4*US)
    c=t.candidates()[0];assert c["attributed_trade_count"]==1 and c["attributed_trade_volume"]==20
