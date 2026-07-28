# -*- coding: utf-8 -*-
"""Estimando diario de EXPLORE-001 — probado SOLO con conteos sintéticos.

Ningún resultado de zona real entra acá, ni directa ni indirectamente: todos los
`sum_real` / `sum_nulo` son números elegidos a mano para que la respuesta se
sepa de antemano. Si el estimador no da 0,5 donde tiene que dar 0,5, el problema
es el estimador y cualquier medición posterior no significaría nada.
"""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.stats.estimando_diario import (EstimandoDiarioError,
                                            SinDiasActivosError,
                                            construir_registro, estimar,
                                            serie_uv, theta_de_uv)


def dia(fecha, n_real=0, sum_real=0.0, n_nulo=None, sum_nulo=0.0,
        tipo_de_dia="COMPLETO"):
    """Un día ya agregado. Por defecto empareja uno-a-uno."""
    return dict(fecha=fecha, tipo_de_dia=tipo_de_dia,
                n_real=n_real, sum_real=sum_real,
                n_nulo=n_real if n_nulo is None else n_nulo, sum_nulo=sum_nulo)


# --------------------------------------------------------- 1 · igual peso por día
def test_igual_peso_por_dia_no_pooling_por_evento():
    """Día de 1 zona con efecto 1,0 y día de 9 zonas con efecto 0,0.

    Equal-weight por día -> 0,5. El pooling por evento daría 0,1: el día de 9
    zonas se llevaría nueve décimos del estadístico por producir más zonas, que
    es una propiedad del feature y no del efecto.
    """
    reg = construir_registro([
        dia("2026-01-05", n_real=1, sum_real=1.0, sum_nulo=0.0),   # x = 1,0
        dia("2026-01-06", n_real=9, sum_real=9.0, sum_nulo=9.0),   # x = 0,0
    ])
    r = estimar(reg)
    assert r["theta"] == pytest.approx(0.5)
    assert r["theta"] != pytest.approx(0.1)

    # el pooling por evento, explícito, para dejar ver la diferencia
    pooled = (1.0 + 9.0) / 10 - (0.0 + 9.0) / 10
    assert pooled == pytest.approx(0.1)


# ------------------------------------------------------- 2 · día cero conservado
def test_dia_cero_queda_en_la_cronologia_y_no_diluye():
    """El día sin zonas mantiene su lugar en la secuencia pero no opina."""
    reg = construir_registro([
        dia("2026-01-05", n_real=1, sum_real=1.0, sum_nulo=0.0),   # x = 1,0
        dia("2026-01-06"),                                          # sin zonas
        dia("2026-01-07", n_real=2, sum_real=4.0, sum_nulo=4.0),   # x = 0,0
    ])
    assert len(reg) == 3
    assert [r.activo for r in reg] == [1, 0, 1]

    r = estimar(reg)
    assert r["theta"] == pytest.approx(0.5)          # no 1/3: el cero no diluye
    assert r["n_dias_calendario"] == 3
    assert r["n_dias_activos"] == 2

    u, v = serie_uv(reg)
    assert v.tolist() == [1.0, 0.0, 1.0]
    assert u.tolist() == [1.0, 0.0, 0.0]             # el día cero aporta 0, no NaN


def test_el_calendario_canonico_materializa_los_dias_sin_zonas():
    """Con calendario, un día elegible sin zonas entra como día CERO explícito.

    El calendario tiene la forma que devuelve `cargar_dias_de_estudio`.
    """
    calendario = [dict(fecha="2026-01-05", tipo_de_dia="COMPLETO"),
                  dict(fecha="2026-01-06", tipo_de_dia="COMPLETO"),
                  dict(fecha="2026-01-09", tipo_de_dia="CIERRE_SEMANAL")]
    reg = construir_registro(
        [dia("2026-01-05", n_real=1, sum_real=1.0, sum_nulo=0.0),
         dia("2026-01-09", n_real=3, sum_real=3.0, sum_nulo=3.0)],
        calendario=calendario)
    assert [r.fecha for r in reg] == ["2026-01-05", "2026-01-06", "2026-01-09"]
    assert [r.activo for r in reg] == [1, 0, 1]
    assert reg[1].tipo_de_dia == "COMPLETO" and reg[2].tipo_de_dia == "CIERRE_SEMANAL"
    assert estimar(reg)["n_dias_calendario"] == 3


def test_sin_calendario_no_se_rellena_nada():
    """Sin la función canónica de calendario no se inventan días ausentes."""
    reg = construir_registro([dia("2026-01-05", n_real=1, sum_real=1.0),
                              dia("2026-01-09", n_real=1, sum_real=1.0)])
    assert [r.fecha for r in reg] == ["2026-01-05", "2026-01-09"]


def test_zona_fuera_del_calendario_falla_ruidoso():
    """Un día con zonas que el nulo no cubre no se compara: falla."""
    with pytest.raises(EstimandoDiarioError, match="fuera del calendario"):
        construir_registro(
            [dia("2026-01-04", n_real=1, sum_real=1.0)],
            calendario=[dict(fecha="2026-01-05", tipo_de_dia="COMPLETO")])


# ----------------------------------------------------- 3 · todos los días cero
def test_sin_ningun_dia_activo_falla_explicito():
    reg = construir_registro([dia("2026-01-05"), dia("2026-01-06"),
                              dia("2026-01-07")])
    assert len(reg) == 3
    with pytest.raises(SinDiasActivosError, match="ningun dia activo"):
        estimar(reg)


# ------------------------------------------------ 4 · bloque sin días activos
def test_bloque_remuestreado_sin_dias_activos_falla_explicito():
    """Ni 0, ni NaN, ni inf: un 0/0 que sigue viajando es un intervalo inventado."""
    reg = construir_registro([dia("2026-01-05", n_real=1, sum_real=1.0),
                              dia("2026-01-06"),
                              dia("2026-01-07")])
    u, v = serie_uv(reg)
    bloque = [1, 2]                                   # dos días cero contiguos
    with pytest.raises(SinDiasActivosError):
        theta_de_uv(u[bloque], v[bloque])

    # el 0/0 que se evita: sin el gate esto viajaría como NaN hasta el intervalo
    with np.errstate(invalid="ignore"):
        degradado = np.divide(u[bloque].sum(), v[bloque].sum())
    assert np.isnan(degradado)


# --------------------------------------------------- 5 · desbalance real/nulo
def test_dia_activo_con_n_real_distinto_de_n_nulo_falla():
    with pytest.raises(EstimandoDiarioError, match="emparejamiento uno-a-uno"):
        construir_registro([dia("2026-01-05", n_real=3, sum_real=3.0,
                                n_nulo=120, sum_nulo=0.0)])


def test_dia_activo_sin_lado_nulo_falla():
    with pytest.raises(EstimandoDiarioError, match="emparejamiento uno-a-uno"):
        construir_registro([dia("2026-01-05", n_real=2, sum_real=2.0, n_nulo=0)])


def test_dia_inactivo_no_exige_emparejamiento():
    """En un día sin zonas el lado nulo no se usa: no se le impone nada."""
    reg = construir_registro([dia("2026-01-05", n_real=0, n_nulo=120, sum_nulo=7.0),
                              dia("2026-01-06", n_real=1, sum_real=1.0)])
    assert reg[0].activo == 0 and reg[0].u == 0.0 and reg[0].v == 0.0
    assert estimar(reg)["theta"] == pytest.approx(1.0)


def test_dia_sin_eventos_con_suma_falla():
    with pytest.raises(EstimandoDiarioError, match="no puede tener suma"):
        construir_registro([dia("2026-01-05", n_real=0, sum_real=3.0)])


# ------------------------------------------------------------ 6 · recomputación
def _registro_de_seis_dias():
    """activo(1,0) · cero · cero · activo(0,0) · cero · activo(1,0)."""
    return construir_registro([
        dia("2026-01-05", n_real=1, sum_real=1.0, sum_nulo=0.0),   # x = 1,0
        dia("2026-01-06"),
        dia("2026-01-07"),
        dia("2026-01-08", n_real=2, sum_real=6.0, sum_nulo=6.0),   # x = 0,0
        dia("2026-01-09"),
        dia("2026-01-12", n_real=4, sum_real=8.0, sum_nulo=4.0),   # x = 1,0
    ])


def test_la_muestra_de_bloques_recomputa_el_ratio_desde_las_sumas():
    """Bloques de DÍAS CALENDARIO completos, ratio recalculado desde sum(u)/sum(v)."""
    u, v = serie_uv(_registro_de_seis_dias())
    assert u.tolist() == [1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    assert v.tolist() == [1.0, 0.0, 0.0, 1.0, 0.0, 1.0]

    muestra = [0, 1, 2, 3, 4, 5, 0, 1, 2]             # bloques de 3 días calendario
    esperado = float(u[muestra].sum()) / float(v[muestra].sum())    # 3,0 / 4,0
    assert theta_de_uv(u[muestra], v[muestra]) == pytest.approx(esperado)
    assert theta_de_uv(u[muestra], v[muestra]) == pytest.approx(0.75)


def test_comprimir_primero_los_dias_cero_cambia_los_bloques():
    """Por qué la serie NO se comprime antes de bloquear.

    El mismo bloque —3 posiciones desde el inicio— vale 1,0 sobre la serie
    calendario (un solo día activo adentro) y 2/3 sobre la serie ya comprimida
    (tres días activos adentro). Los días cero no cambian el estimador global,
    cambian QUÉ días quedan contiguos, que es justo lo que el bloque preserva.
    """
    reg = _registro_de_seis_dias()
    u, v = serie_uv(reg)
    bloque = [0, 1, 2]
    assert theta_de_uv(u[bloque], v[bloque]) == pytest.approx(1.0)

    activos = [r for r in reg if r.activo]            # la compresión prohibida
    uc, vc = serie_uv(activos)
    assert theta_de_uv(uc[bloque], vc[bloque]) == pytest.approx(2.0 / 3.0)

    # el estimador GLOBAL sí coincide: la compresión no se nota sin bloques,
    # y por eso el error sería invisible si no se lo testea acá.
    assert theta_de_uv(u, v) == pytest.approx(theta_de_uv(uc, vc))


def test_dia_inactivo_con_efecto_es_incoherente():
    """Blinda contra una serie armada a mano donde un día cero trae efecto."""
    with pytest.raises(EstimandoDiarioError, match="no puede aportar efecto"):
        theta_de_uv([1.0, 0.5], [1.0, 0.0])


# -------------------------------------------------------------- 7 · orden temporal
def test_fechas_duplicadas_fallan():
    with pytest.raises(EstimandoDiarioError, match="duplicadas o fuera de orden"):
        construir_registro([dia("2026-01-05", n_real=1, sum_real=1.0),
                            dia("2026-01-05", n_real=1, sum_real=1.0)])


def test_fechas_fuera_de_orden_fallan():
    with pytest.raises(EstimandoDiarioError, match="duplicadas o fuera de orden"):
        construir_registro([dia("2026-01-06", n_real=1, sum_real=1.0),
                            dia("2026-01-05", n_real=1, sum_real=1.0)])


def test_calendario_fuera_de_orden_falla():
    with pytest.raises(EstimandoDiarioError, match="duplicadas o fuera de orden"):
        construir_registro(
            [dia("2026-01-05", n_real=1, sum_real=1.0)],
            calendario=[dict(fecha="2026-01-06", tipo_de_dia="COMPLETO"),
                        dict(fecha="2026-01-05", tipo_de_dia="COMPLETO")])


# ------------------------------------------------------------------- conteos
def test_los_conteos_acompanan_al_estimador():
    r = estimar(_registro_de_seis_dias())
    assert r["n_dias_calendario"] == 6
    assert r["n_dias_activos"] == 3
    assert r["n_eventos_reales"] == 7
    assert r["n_eventos_nulos"] == 7
    assert r["fecha_min"] == "2026-01-05" and r["fecha_max"] == "2026-01-12"
    assert r["theta"] == pytest.approx(2.0 / 3.0)
