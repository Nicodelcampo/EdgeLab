"""Guardas del 2026-10-27 (docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md, O13): el CONTEO del holdout con 0 disparos
en la ventana devuelve conteo 0 (el embudo sigue mirando) en vez de romper el kernel (U1-YM-GRILLA, U1-ES-GRILLA, U1-ORO-GRILLA)."""
import numpy as np
import pandas as pd

from edgelab.research import etapas as ET, grilla_generica as GG


class _ExpSinDisparos:
    NOMBRE = "SIN-DISPAROS"; VARIABLES = []; EJECUCIONES = [(1, 1.0)]

    @staticmethod
    def disparos(ctx):
        return pd.DataFrame(dict(k=[]))                                  # columna `k` vacía: dtype object, no entera

    @staticmethod
    def niveles(r, ej, ctx):
        raise AssertionError("sin disparos no hay niveles")


def _ctx(n=500):
    c = 20000 + np.cumsum(np.ones(n) * 0.25)
    return dict(t=np.arange(n) * 60.0, c=c, h=c + 0.25, l=c - 0.25, o=c, ses=np.arange(n) // 100, tick=0.25,
                tpx=np.zeros(0), tstart=np.zeros(n + 1, np.int64))


def test_correr_con_cero_disparos_no_rompe():
    res, D = GG.correr(_ExpSinDisparos, _ctx(), modo="REP", friccion=0.0, extra_adverso=0.0, cortes={}, celdas=[[0]])
    assert res["E0"]["disparos"] == 0 and len(D) == 0 and "ses" in D


def test_conteo_del_holdout_con_cero_disparos_da_cero():
    res = ET.ejecutar("HOLDOUT_CONTEO", _ExpSinDisparos, _ctx(), friccion=0.0, extra_adverso=0.0, params=dict(celdas=[[0], [0]], cortes={}))
    assert res["conteo"] == [0, 0]


def test_resumen_e0_con_cero_disparos_sin_columnas():
    """2026-10-27: U1 sin mes previo en el holdout devuelve un DataFrame vacío sin las columnas de las variables (KeyError 'r_vol')."""
    import pandas as pd
    from edgelab.research import grilla_generica as GG
    V = [GG.Variable("r", "r_vol", "grupo"), GG.Variable("z", "zt", "grupo", categoria=3)]
    r = GG.resumen_e0(pd.DataFrame(columns=["k", "ses"]), V, None)
    assert r["disparos"] == 0 and r["variables"]["r"]["faltantes"] == 0 and r["variables"]["z"]["conteo"] == {}


def test_correr_con_cero_disparos_sin_k_ni_columnas():
    """El experimento vacío puede no traer ni `k` ni las columnas de sus variables: correr devuelve E0 con 0 disparos, no rompe."""
    import types
    import pandas as pd
    from edgelab.research import grilla_generica as GG
    exp = types.SimpleNamespace(NOMBRE="X", VARIABLES=[GG.Variable("r", "r_vol", "grupo")], disparos=lambda c: pd.DataFrame(columns=["m"]))
    res, D = GG.correr(exp, {"ses": [1, 2]}, modo="REP", friccion=0.0, extra_adverso=0.0, cortes={}, celdas=[[0]], log=lambda *a: None)
    assert res["E0"]["disparos"] == 0 and len(D) == 0


def test_u1_oro_escala_octubre_holdout_usa_septiembre_causal():
    from edgelab.research import u1_oro as UO
    t0 = int(pd.Timestamp("2026-10-05 14:30", tz="UTC").timestamp())
    ctx = dict(t=np.array([t0, t0 + 60]), h=np.array([10.0, 10.0]), l=np.array([8.0, 8.0]), sensor="NQ")
    _, f = UO.escala_por_mes(ctx, 6.25)
    assert np.isclose(f[202610], UO.RANGO_M1_202609["NQ"] / 6.25)


def test_calentamiento_desde_eval_no_cuenta_disparos_ni_operaciones():
    import types
    cx = _ctx(300); cx["ses"] = np.array([20261001] * 100 + [20261023] * 100 + [20261026] * 100)
    cx["desde_eval"] = 20261023
    exp = types.SimpleNamespace(NOMBRE="CAL", VARIABLES=[], EJECUCIONES=[(1,)],
                                disparos=lambda c: pd.DataFrame(dict(k=[50, 150, 250])),
                                niveles=lambda r, ej, c: (int(r["k"]), 0, 1, float(c["c"][int(r["k"])]), float(c["c"][int(r["k"])]) - 1.0, float(c["c"][int(r["k"])]) + 1.0, 0))
    res = ET.ejecutar("HOLDOUT_CONTEO", exp, cx, friccion=0.0, extra_adverso=0.0, params=dict(celdas=[[0]], cortes={}))
    assert res["conteo"] == [2]


def test_confirmar_en_canasta_regimen_dentro_y_fuera_de_banda():
    from edgelab.funnel.escalera import confirmar_en_canasta_regimen
    # Con mu_esperada=10, sd_op_ref=20 y n=4 -> se_n = 10, banda 90% = [-6.45, +26.45]
    ok = confirmar_en_canasta_regimen([5.0, -2.0, 12.0, 1.0], mu_esperada=10.0, sd_op_ref=20.0, n_min=4)
    assert ok["confirmada_canasta"] is True and ok["dentro_desviacion"] is True and ok["estado"] == "CONFIRMADA_CANASTA"
    mal = confirmar_en_canasta_regimen([-15.0, -20.0, -10.0, -12.0], mu_esperada=10.0, sd_op_ref=20.0)
    assert mal["confirmada_canasta"] is False and mal["dentro_desviacion"] is False and mal["estado"] == "FUERA_DE_BANDA_INFERIOR"
    vacio = confirmar_en_canasta_regimen([], mu_esperada=10.0, sd_op_ref=20.0)
    assert vacio["confirmada_canasta"] is False and vacio["estado"] == "SIN_OPERACIONES_AUN"



def test_canasta_regimen_no_confirma_perdiendo_con_poco_n():
    """2026-10-30: con n chico la banda inferior quedaba < 0 y una media negativa salía CONFIRMADA_CANASTA."""
    from edgelab.funnel.escalera import confirmar_en_canasta_regimen
    r = confirmar_en_canasta_regimen([-50.0, -60.0, -40.0], mu_esperada=19.0, sd_op_ref=100.0)      # cota inferior ≈ −76
    assert r["dentro_desviacion"] is True and r["confirmada_canasta"] is False and r["estado"] == "SIN_EVIDENCIA_AUN"
    pocas = confirmar_en_canasta_regimen([30.0, 20.0], mu_esperada=19.0, sd_op_ref=100.0)              # gana, pero n < n_min
    assert pocas["estado"] == "SIN_EVIDENCIA_AUN"
    bien = confirmar_en_canasta_regimen([30.0, 20.0, 5.0, 40.0, 10.0], mu_esperada=19.0, sd_op_ref=100.0)
    assert bien["estado"] == "CONFIRMADA_CANASTA"
    muy_mal = confirmar_en_canasta_regimen([-200.0] * 10, mu_esperada=19.0, sd_op_ref=100.0)
    assert muy_mal["estado"] == "FUERA_DE_BANDA_INFERIOR"


def test_confirmar_canasta_junta_el_n_de_todas():
    from edgelab.funnel.escalera import confirmar_canasta
    import numpy as np
    rng = np.random.default_rng(7)
    buenas = [dict(cid=f"S{i}", netos=list(rng.normal(30, 100, 4)), sd_op_ref=100.0) for i in range(12)]     # 0,3 sd por operación
    assert confirmar_canasta(buenas)["n"] == 48
    ruido = [dict(cid=f"R{i}", netos=list(rng.normal(0, 100, 4)), sd_op_ref=100.0) for i in range(12)]
    assert confirmar_canasta(ruido)["estado"] != "CANASTA_CONFIRMADA"
    malas = [dict(cid=f"M{i}", netos=list(rng.normal(-40, 100, 4)), sd_op_ref=100.0) for i in range(12)]
    assert confirmar_canasta(malas)["estado"] == "CANASTA_EN_CONTRA"
    assert confirmar_canasta([dict(cid="X", netos=[], sd_op_ref=100.0)])["estado"] == "SIN_OPERACIONES_AUN"
    pesos = confirmar_canasta([dict(cid="A", netos=[10.0, 12.0], sd_op_ref=10.0), dict(cid="B", netos=[100.0, 120.0], sd_op_ref=100.0)])
    assert abs(pesos["por_estrategia"]["A"]["media_std"] - pesos["por_estrategia"]["B"]["media_std"]) < 1e-9, "igual riesgo por estrategia"
