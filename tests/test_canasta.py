"""Capa de canasta: sólo entra lo CONFIRMADO por el embudo; retiro por futilidad, por drawdown y por cota violada; una regla retirada
no vuelve sin otra confirmación; pesos de riesgo igual con topes por estrategia e instrumento; persistencia en disco."""
import random

import pytest

from edgelab.funnel.canasta import Canasta, Estrategia

OK = dict(fase="CONFIRMADA")


def _e(id_, inst="NQ", sd=10.0, celda=(1,)):
    return Estrategia(id=id_, familia="F", instrumento=inst, regla=dict(celda=list(celda)), acta="acta.json", perdida_max_pts=20.0,
                      ganancia_max_pts=40.0, margen_hueco_pts=5.0, friccion_pts=1.0, mu_util=2.0, sd_desarrollo=sd)


def test_alta_exige_confirmacion(tmp_path):
    c = Canasta(tmp_path / "c.json")
    with pytest.raises(ValueError): c.alta(_e("a"), dict(fase="SIN_POTENCIA"))
    c.alta(_e("a"), OK); assert Canasta(tmp_path / "c.json").estrategias["a"].estado == "ACTIVA"


def test_retiro_por_futilidad_y_no_resucita(tmp_path):
    c = Canasta(tmp_path / "c.json"); c.alta(_e("a"), OK); r = random.Random(0); st = None
    for _ in range(400):
        st = c.operaciones("a", [r.uniform(-12, 10)])                             # media ≈ −1 < mu_util 2
        if st["estado"] == "RETIRADA": break
    assert st["estado"] == "RETIRADA" and "futilidad" in st["motivo"]
    with pytest.raises(ValueError): c.alta(_e("b"), OK)                           # misma regla congelada, otro id
    with pytest.raises(ValueError): c.operaciones("a", [1.0])


def test_retiro_por_drawdown_y_por_cota(tmp_path):
    c = Canasta(tmp_path / "c.json", reglas=dict(dd_max_r=2.0)); c.alta(_e("a"), OK); c.alta(_e("b", celda=(2,)), OK)
    st = c.operaciones("a", [-20.0, -20.0, -20.0])
    assert st["estado"] == "RETIRADA" and "drawdown" in st["motivo"]
    st = c.operaciones("b", [-500.0])
    assert st["estado"] == "RETIRADA" and "cota" in st["motivo"]


def test_pesos_riesgo_igual_con_topes(tmp_path):
    c = Canasta(tmp_path / "c.json", reglas=dict(peso_max=0.6, peso_max_instrumento=0.7))
    c.alta(_e("a", "NQ", sd=5.0, celda=(1,)), OK); c.alta(_e("b", "NQ", sd=5.0, celda=(2,)), OK); c.alta(_e("c", "ES", sd=20.0, celda=(3,)), OK)
    w = c.pesos()
    assert abs(sum(w.values()) - 1) < 1e-9 and w["a"] + w["b"] <= 0.7 + 1e-9 and w["c"] > 0.2
    assert Canasta(tmp_path / "x.json").reporte()["nota"]


def test_una_sola_estrategia_respeta_el_tope_y_el_resto_queda_sin_asignar(tmp_path):
    c = Canasta(tmp_path / "c.json"); c.alta(_e("a"), OK)
    assert c.pesos() == {"a": 0.25}                                             # 75 % sin asignar: no se concentra para «llenar»
