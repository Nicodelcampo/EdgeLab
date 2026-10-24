"""Chequeo final de las correcciones de falsos negativos (2026-10-24) sobre los artefactos COMMITTEADOS de AREAS-EXP-1 v1.4:
¿las celdas de U1 llegan a la réplica y las confirma el paso de LORD++ por lote? (con la lógica de selección de hoy, sin correr
nada nuevo). Informe: docs/research/revision_20261024/FALSOS_NEGATIVOS_EMBUDO_20261024.md, sección 9."""
import json
from pathlib import Path

import pytest

from edgelab.funnel import escalera as E
from edgelab.research import embudo as EM

V14 = Path(__file__).resolve().parents[2] / "docs/research/areas_expansion_20261022/v14"
U1 = [[2, 2, 10, 3, 2, 3, 1], [2, 2, 11, 3, 1, 3, 1], [2, 2, 11, 3, 2, 3, 2], [2, 2, 58, 3, 3, 3, 1], [2, 2, 59, 3, 3, 3, 2]]


def recheck(fuente="USATECH", k=E.K_PISTAS_REPLICA, nivel=None):
    """Selección de pistas con la regla de hoy sobre el DESC v1.4 de `fuente` + paso único de LORD++ con los p de la réplica v1.4."""
    desc = json.loads((V14 / f"AREAS_{fuente}_DESC_v14.json").read_text(encoding="utf-8"))
    rep = json.loads((V14 / "REP_EVALUACION_LORDPP_v14.json").read_text(encoding="utf-8"))
    congel = json.loads((V14 / "REP_CONGELADO_v14.json").read_text(encoding="utf-8"))[fuente]["celdas"]
    filas = [f for f in rep["filas"] if f["fuente"] == fuente]
    p_rep = {tuple(c): f for c, f in zip(congel, filas)}                         # mismo orden que se congeló en v1.4
    pistas = [p for c in desc["canales"].values() for p in c["pistas"]]
    sel = EM.DEFECTOS["seleccion"]
    elegidas = E.elegir_pistas_replica(pistas, k, min_dif=sel["min_dif"], min_sesiones=sel["min_sesiones"], ratio_mov_friccion=sel["ratio_mov_friccion"])
    pruebas = [(str(p["celda"]), p_rep[tuple(p["celda"])]["p_rep"] if p_rep[tuple(p["celda"])]["p_rep"] is not None else 1.0) for p in elegidas]
    L = E.LordPP()
    nv = nivel if nivel is not None else L.nivel()
    d = E.decidir_lote(nv, pruebas)
    filas_r = [dict(media_neta=p_rep[tuple(p["celda"])]["media_rep"]) for p in elegidas]
    ok = E.decidir_pistas(d, filas_r, [n for n, _ in pruebas])
    return dict(elegidas=[p["celda"] for p in elegidas], decision=d, confirmadas=[elegidas[i]["celda"] for i in ok],
                u1_elegidas=[c for c in U1 if c in [p["celda"] for p in elegidas]],
                meseta_u1=[next((p["meseta"] for p in pistas if p["celda"] == c), None) for c in U1])


@pytest.mark.skipif(not (V14 / "REP_EVALUACION_LORDPP_v14.json").exists(), reason="artefactos v1.4 no presentes")
def test_u1_llega_a_replica_y_la_confirma_el_lote():
    r = recheck()
    assert r["meseta_u1"].count(False) == 4                                      # la meseta como compuerta mataba 4 de las 5
    assert len(r["u1_elegidas"]) >= 2                                            # entran por cota inferior entre las top-20
    assert r["decision"]["rechazo"] and set(map(tuple, r["confirmadas"])) <= set(map(tuple, U1)) and r["confirmadas"]
    uno_a_uno = json.loads((V14 / "REP_EVALUACION_LORDPP_v14.json").read_text(encoding="utf-8"))["lordpp"]
    assert uno_a_uno["rechazos"] == [] and uno_a_uno["t"] == 80                  # LORD++ de a una: 0 de 80 (lo que pasó)


@pytest.mark.skipif(not (V14 / "REP_EVALUACION_LORDPP_v14.json").exists(), reason="artefactos v1.4 no presentes")
def test_u1_depende_del_paso_lo_que_se_informa():
    """Honestidad: al nivel del SEGUNDO paso (si el lote de NQ hubiera ido primero) el lote de USATECH no rechaza."""
    nv2 = E.LordPP(t=1).nivel()
    assert not recheck(nivel=nv2)["decision"]["rechazo"]
    assert not recheck("NQ")["decision"]["rechazo"]
