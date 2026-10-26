import math

from edgelab.research import embudo as EM, potencia_previa as PP


def test_ventana_y_mde_bajan_con_n():
    a, b = PP.ventana(25, 10.0), PP.ventana(100, 10.0)
    assert math.isclose(a["mde"] / b["mde"], 2.0, rel_tol=1e-9)


def test_informe_previo_meses_necesarios():
    spec = dict(desc=[20240101, 20241231], oos=[20250101, 20250630], holdout=dict(n_fijo=150),
                potencia_previa=dict(ops_mes=10, sd_op=20.0, efecto_util=2.0))
    r = PP.informe_previo(spec, EM._meses)
    assert r["desc"]["n"] == 120 and r["oos"]["n"] == 60 and r["meses_necesarios"] > 12
    assert PP.informe_previo({}, EM._meses) is None


def test_por_candidata_proyecta_al_oos():
    p = dict(celda=[1], n=120, ic90=[1.0, 5.0], media_neta=3.0)
    r = PP.por_candidata(p, 12, 6, 150)
    assert r["oos"]["n"] == 60 and r["holdout"]["potencia"] > r["oos"]["potencia"]


def test_escala_rango_sesion_previa_es_causal():
    import numpy as np
    from edgelab.research.grilla_generica import escala_ops
    ctx = dict(ses=np.array([1, 1, 2, 2, 3]), h=np.array([10., 12, 20, 25, 9]), l=np.array([9., 8, 19, 15, 1]))
    e = escala_ops("rango_sesion_previa", [1, 2, 3, 3], ctx)
    assert np.isnan(e[0]) and e[1] == 4.0 and e[2] == 10.0 and e[3] == 10.0      # la sesión 3 usa el rango de la 2, no el propio
