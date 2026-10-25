"""D5 en el embudo: holdout.estadistico = e_proceso habilita el reuso autorizado de sesiones miradas sólo con cotas estructurales,
decide en cada conteo (Ville) e informa también sin las sesiones vistas."""
import json

import numpy as np

from edgelab.research import embudo as EM, holdout_ventanas as HV

COTAS = dict(perdida_max_pts=20.0, ganancia_max_pts=20.0, margen_hueco_pts=5.0, mu_util=1.0)


def _em(tmp_path, ventanas):
    return EM.Embudo(tmp_path / "estado", {}, registro=None, libro=None, ahora=lambda: 1_793_000_000, log=lambda s: None, ventanas=ventanas)


def _spec(**h):
    return dict(cid="T-E", familia="FAM", experimento="x", sensor="NQ", ejecucion="NQ", holdout=dict(desde=20261001, n_fijo=60, conteo_cada_s=0, **h))


def _st(spec):
    return dict(etapa="ACTA", fase="PENDIENTE", historial=[], spec=spec, regla=dict(celda=[0], tope=["pts", 20.0]), cortes={}, reglas={})


def _ventanas(tmp_path, reuso=True):
    f = tmp_path / "v.jsonl"
    filas = [dict(tipo="consumida", familia="FAM", desde=20261001, hasta=20261022, relacionadas=[])]
    if reuso: filas.append(dict(tipo="reuso_autorizado", familia="FAM", desde=20261001, condicion="e_proceso"))
    f.write_text("".join(json.dumps(r) + "\n" for r in filas), encoding="utf-8"); return f


def test_acta_bloquea_e_proceso_sin_cotas_y_n_fijo_que_reusa(tmp_path):
    v = _ventanas(tmp_path); em = _em(tmp_path, v)
    sp = _spec(estadistico="e_proceso"); (tmp_path / "estado" / "T-E").mkdir(parents=True)
    assert "sin cotas" in em._acta(sp, _st(sp))["motivo"]
    sp = _spec(); assert em._acta(sp, _st(sp))["fase"] == "BLOQUEADA"                  # n_fijo no puede reusar lo mirado


def test_acta_con_e_proceso_y_reuso_registra_cotas_y_vistas(tmp_path):
    v = _ventanas(tmp_path); em = _em(tmp_path, v); sp = _spec(estadistico="e_proceso", **COTAS)
    (tmp_path / "estado" / "T-E").mkdir(parents=True)
    st = em._acta(sp, _st(sp))
    assert st["etapa"] == "CONTEO" and st["acta"]["estadistico"] == "e_proceso" and st["acta"]["vistas_hasta"] == 20261022
    assert any(r.get("tipo") == "apertura" for r in HV.leer(v))


def _acta_st(sp):
    st = _st(sp); st.update(etapa="HOLDOUT", acta=dict(n_fijo=60, alfa=0.05, cotas=COTAS, estadistico="e_proceso", vistas_hasta=20261022))
    return st


def _ops(x, ses):
    return dict(t=list(range(len(x))), neto=list(map(float, x)), ses=list(map(int, ses)))


def test_e_proceso_confirma_edge_claro_e_informa_sin_las_vistas(tmp_path):
    em = _em(tmp_path, _ventanas(tmp_path)); sp = _spec(estadistico="e_proceso", **COTAS); (tmp_path / "estado" / "T-E").mkdir(parents=True)
    rng = np.random.default_rng(1); x = np.clip(rng.normal(6, 4, 50), -20, 14); ses = [20261005] * 10 + [20261027] * 40
    st = em._fin_holdout_e(sp, _acta_st(sp), _ops(x, ses), 60)
    assert st["fase"] == "CONFIRMADA" and st["holdout"]["sin_sesiones_vistas"]["n"] == 40


def test_e_proceso_sin_decidir_sigue_contando_y_limite_violado_bloquea(tmp_path):
    em = _em(tmp_path, _ventanas(tmp_path)); sp = _spec(estadistico="e_proceso", **COTAS); (tmp_path / "estado" / "T-E").mkdir(parents=True)
    st = em._fin_holdout_e(sp, _acta_st(sp), _ops([0.5, -0.3, 0.2], [20261027] * 3), 60)
    assert st["etapa"] == "CONTEO" and st["n_holdout_decidido"] == 3
    st = em._fin_holdout_e(sp, _acta_st(sp), _ops([1.0, -80.0], [20261027] * 2), 60)
    assert st["fase"] == "BLOQUEADA" and "LIMITE_VIOLADO" in st["motivo"]
