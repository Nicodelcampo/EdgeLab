# -*- coding: utf-8 -*-
"""Firewall causal para features de modelos externos.

El test que importa es `test_el_detector_atrapa_al_predictor_tramposo`: sin él,
todo lo demás sería un conjunto de aserciones que nunca se vieron fallar.
"""
import pytest

from edgelab.external.causality import (
    CausalityViolation, assert_causal, assert_store_causal, diagnose_join,
    probe_positions)
from edgelab.external.contract import ContractError, PredictionRecord
from edgelab.external.mock import (
    LeakyMockPredictor, MockPredictor, barras_sinteticas, identidad_mock)
from edgelab.external.pit_store import LookAheadError, PITFeatureStore

BAR_NS = 300 * 10**9


def _store_de(pred, bars, latency_ns=0):
    st = PITFeatureStore(pred.identity.model_id)
    for i in range(len(bars)):
        st.add_many(pred.predict_at(bars, i))
    return st.seal()


# --------------------------------------------------------------- el test clave
def test_el_detector_atrapa_al_predictor_tramposo():
    """Un gate que nunca se vio fallar no es un gate.

    `LeakyMockPredictor` reproduce el bug REAL —mirar `bars[i+horizon]`— que es
    lo que pasa al correr `predict()` sobre la serie entera y unir por el índice
    que devuelve el modelo.
    """
    bars = barras_sinteticas(300)
    leaky = LeakyMockPredictor(identidad_mock(horizon_bars=6), bar_ns=BAR_NS)

    def fn(sub):
        return [leaky.predict_at(sub, i)[0].values["p_up"] for i in range(len(sub))]

    with pytest.raises(CausalityViolation) as e:
        assert_causal(fn, bars, nombre="p_up (tramposo)")
    assert "MIRA HACIA ADELANTE" in str(e.value)
    assert "truncado=" in str(e.value)


def test_el_predictor_honesto_pasa():
    bars = barras_sinteticas(300)
    p = MockPredictor(bar_ns=BAR_NS)

    def fn(sub):
        return [p.predict_at(sub, i)[0].values["p_up"] for i in range(len(sub))]

    assert assert_causal(fn, bars, nombre="p_up")


def test_una_funcion_centrada_no_pasa():
    """Un rolling centrado es look-ahead aunque nadie lo llame así."""
    datos = list(range(200))

    def centrada(xs):
        return [sum(xs[max(0, i - 1): i + 2]) / len(xs[max(0, i - 1): i + 2])
                for i in range(len(xs))]

    with pytest.raises(CausalityViolation):
        assert_causal(centrada, datos, nombre="media centrada")


def test_una_funcion_causal_equivalente_si_pasa():
    datos = list(range(200))

    def rezagada(xs):
        return [sum(xs[max(0, i - 2): i + 1]) / len(xs[max(0, i - 2): i + 1])
                for i in range(len(xs))]

    assert assert_causal(rezagada, datos, nombre="media rezagada")


def test_las_sondas_cubren_el_final_de_la_serie():
    """Un leak de pocas barras sólo queda al descubierto cerca del final."""
    pos = probe_positions(1000, n_probes=24)
    assert max(pos) >= 900, pos
    assert len(set(pos)) == len(pos)
    assert probe_positions(1000, 24) == probe_positions(1000, 24)  # determinista


# ------------------------------------------------------ invariantes del record
def test_no_se_puede_construir_una_prediccion_del_pasado():
    with pytest.raises(ContractError) as e:
        PredictionRecord(model_id="m", generated_at_ns=1000,
                         target_ts_ns=1000, available_at_ns=1000, values={})
    assert "no es una predicción" in str(e.value)


def test_no_se_puede_estar_disponible_antes_de_generarse():
    with pytest.raises(ContractError):
        PredictionRecord(model_id="m", generated_at_ns=1000, target_ts_ns=2000,
                         available_at_ns=999, values={})


# ------------------------------------------------------------ store as-of
def test_el_store_nunca_sirve_una_prediccion_futura():
    bars = barras_sinteticas(120)
    st = _store_de(MockPredictor(bar_ns=BAR_NS), bars)
    for b in bars:
        r = st.as_of(int(b["ts_ns"]))
        assert r is None or r.available_at_ns <= int(b["ts_ns"])


def test_la_serie_servida_por_el_store_es_causal():
    bars = barras_sinteticas(200)
    st = _store_de(MockPredictor(bar_ns=BAR_NS), bars)
    idx = [int(b["ts_ns"]) for b in bars]
    assert assert_store_causal(st, idx, "p_up")


def test_la_latencia_de_computo_corre_el_feature():
    """Generar 30 caminos lleva tiempo real; ignorarlo también es look-ahead."""
    bars = barras_sinteticas(50)
    lat = 2 * BAR_NS
    st = _store_de(MockPredictor(bar_ns=BAR_NS, latency_ns=lat), bars)
    idx = [int(b["ts_ns"]) for b in bars]
    con = st.series(idx, "p_up")
    sin = st.series(idx, "p_up")
    assert con == sin
    # Con 2 barras de latencia, las 2 primeras posiciones no tienen nada.
    assert con[0] != con[0]          # NaN
    assert con[1] != con[1]
    assert con[3] == con[3]


def test_no_se_puede_escribir_despues_de_sellar():
    bars = barras_sinteticas(10)
    p = MockPredictor(bar_ns=BAR_NS)
    st = _store_de(p, bars)
    with pytest.raises(LookAheadError):
        st.add(p.predict_at(bars, 5)[0])


def test_staleness_corta_la_propagacion_de_un_valor_viejo():
    """Sin límite, un hueco de cómputo propaga una predicción vieja durante horas."""
    bars = barras_sinteticas(40)
    p = MockPredictor(bar_ns=BAR_NS)
    st = PITFeatureStore(p.identity.model_id)
    for i in (0, 1, 2):                     # después, silencio
        st.add_many(p.predict_at(bars, i))
    st.seal()
    idx = [int(b["ts_ns"]) for b in bars]
    sin_limite = st.series(idx, "p_up")
    con_limite = st.series(idx, "p_up", max_staleness_ns=3 * BAR_NS)
    assert sin_limite[-1] == sin_limite[-1]          # se propagó hasta el final
    assert con_limite[-1] != con_limite[-1]          # NaN: quedó viejo
    assert con_limite[3] == con_limite[3]            # todavía fresco


# --------------------------------------------------------- diagnóstico de join
def test_diagnostica_el_join_por_target_ts():
    """El error de una línea que produce el AUC de 0.9997."""
    gen = [1000 * k for k in range(50)]
    target = [g + 6000 for g in gen]                # índice = target_ts
    d = diagnose_join(target, gen)
    assert not d["ok"] and d["code"] == "INDICE_ES_TARGET_TS"
    assert d["n_adelantadas"] == 50


def test_diagnostica_el_join_correcto():
    gen = [1000 * k for k in range(50)]
    d = diagnose_join(gen, gen)
    assert d["ok"] and d["code"] == "INDICE_ES_GENERATED_AT"


# ---------------------------------------------------------------- auditoría
def test_auditoria_estructural_limpia():
    bars = barras_sinteticas(60)
    st = _store_de(MockPredictor(bar_ns=BAR_NS), bars)
    a = st.audit()
    assert a["ok"], a["problemas"]
    assert a["n"] == 60


def test_auditoria_marca_prediccion_inutilizable():
    """Lista DESPUÉS del instante que describe: no es leak, pero no sirve."""
    st = PITFeatureStore("m")
    st.add(PredictionRecord(model_id="m", generated_at_ns=0, target_ts_ns=100,
                            available_at_ns=200, values=dict(p_up=0.5)))
    a = st.audit()
    assert not a["ok"]
    assert a["problemas"][0]["tipo"] == "LISTA_DESPUES_DEL_TARGET"
