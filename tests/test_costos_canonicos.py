import pytest
from edgelab import costos
from edgelab.autopilot import friccion

LEGACY = {"ES": 3.55, "MES": 4.62, "6E": 4.16, "NQ": 6.18, "GC": 6.05, "MNQ": 7.91}   # REFERENCIA_COSTOS §4, tabla literal previa de friccion.py


def test_reproduce_la_tabla_documentada_y_no_cambia_el_autopilot():
    assert friccion.FRICCION_RT_TICKS == LEGACY
    for k, v in LEGACY.items():
        assert costos.friccion_rt_ticks(k) == pytest.approx(v, abs=0.006)


def test_escenarios_y_unidades():
    b = costos.friccion_rt_ticks("NQ")
    assert costos.friccion_rt_ticks("NQ", "adverso") == pytest.approx(b + 2)
    assert costos.friccion_rt_ticks("NQ", "severo") == pytest.approx(b + 4)
    assert costos.friccion_rt_ticks("NQ", "ideal") == 0.0
    assert costos.friccion_rt_ticks("NQ", incluye_spread=False) == pytest.approx(b - 3.03)
    assert costos.friccion_rt_puntos("NQ") == pytest.approx(b * 0.25)
    assert costos.friccion_rt_usd("ES") == pytest.approx(costos.friccion_rt_ticks("ES") * 12.5)
    assert costos.friccion_rt_ticks("ES", criterio="min") < costos.friccion_rt_ticks("ES")


def test_no_transporta_costos_entre_instrumentos():
    with pytest.raises(costos.CostoNoMedido):
        costos.friccion_rt_ticks("ZB")          # spread sin medir
    with pytest.raises(costos.CostoNoMedido):
        costos.friccion_rt_ticks("EURUSD")      # spot: no está en la tabla
    assert costos.desglose("6J")["friccion_rt_ticks"] is None
