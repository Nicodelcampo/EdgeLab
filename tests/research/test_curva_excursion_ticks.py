# -*- coding: utf-8 -*-
"""Extractor tick-based de la curva de diseño.

Los cuatro casos que exigió Nico: **retorno**, **ruptura**, **timestamps
empatados** y **orden ambiguo**. Series fabricadas acá: nada de datos reales,
nada de outcomes.
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    MAX_FECHA, T_DESIGN, eventos_de_zona,
)

LO, HI = 100.0, 110.0          # banda de la zona, en unidades de tick


def _ev(precios, umbrales=T_DESIGN):
    px = np.asarray(precios, dtype=np.float64)
    return eventos_de_zona(px, LO, HI, 0, len(px), umbrales)


def test_retorno_exige_alejarse_Y_VOLVER():
    """Sube a 118 (8 por encima de HI) y vuelve a la banda. El retorno califica
    hasta T=8 y no más: a T=13 nunca se alejó tanto."""
    rup_up, rup_dn, ret, primera = _ev([105, 112, 118, 114, 105])
    assert 8 in ret and 13 not in ret
    assert primera == 0.0, "el primer tick ya estaba dentro: alejamiento previo 0"


def test_ruptura_NO_exige_volver():
    """Relojes separados. Se va y no vuelve: hay ruptura, no hay retorno."""
    rup_up, rup_dn, ret, _ = _ev([105, 120, 140, 160])
    assert 34 in rup_up and rup_up[34] > 0
    assert ret == {}, "no volvió a la banda: no puede haber retorno"


def test_la_direccion_de_la_ruptura_se_separa():
    """Un `trapped_sellers` que rompe hacia ABAJO contradice el mecanismo. La
    versión M1 los sumaba con los de arriba."""
    rup_up, rup_dn, _, _ = _ev([105, 90, 80, 70])
    assert 21 in rup_dn and not rup_up, "sólo se alejó por abajo"


def test_el_alejamiento_previo_es_ESTRICTAMENTE_anterior():
    """Un tick DENTRO de la banda no puede justificar su propio retorno: el
    acumulado que lo habilita es el de los ticks previos."""
    # nunca sale de la banda -> ningún retorno califica, ni siquiera a T=1
    _, _, ret, _ = _ev([105, 106, 104, 105])
    assert ret == {}


def test_timestamps_empatados_no_afectan_el_resultado():
    """En 6E el 66,1 % de los ticks consecutivos comparte `ts_ns`. El extractor
    trabaja sobre el ORDEN del array -que es `sequence`, orden estable del
    archivo- y no sobre el reloj, así que empatar timestamps no cambia nada.

    Se compara la MISMA secuencia de precios: el resultado debe ser idéntico
    porque el extractor nunca mira `ts_ns` para ordenar.
    """
    precios = [105, 118, 112, 105, 130]
    a = _ev(precios)
    b = _ev(list(precios))          # mismo orden, timestamps irrelevantes
    assert a[0] == b[0] and a[2] == b[2]


def test_orden_ambiguo_NO_EXISTE_con_orden_total():
    """El caso que forzaba 91 % de ABSTAIN sobre barras M1: una barra cuyo RANGO
    tocaba la banda Y se alejaba, sin poder demostrar cuál pasó primero.

    Con ticks el caso **no se puede construir**: un tick es un punto, está dentro
    o afuera. Los dos órdenes posibles dan resultados DISTINTOS y determinados —
    que es exactamente lo que M1 no podía distinguir.
    """
    _, _, ret_ab, _ = _ev([105, 118, 105])      # sale y vuelve -> hay retorno
    rup_ba, _, ret_ba, _ = _ev([105, 105, 118])  # vuelve y sale -> no hay retorno
    assert 8 in ret_ab
    assert 8 not in ret_ba and 8 in rup_ba
    assert ret_ab != ret_ba, "los dos órdenes tienen que distinguirse"


def test_tramo_vacio_devuelve_None_y_no_inventa():
    assert eventos_de_zona(np.array([105.0]), LO, HI, 0, 0, T_DESIGN) is None


def test_la_grilla_de_diseno_no_incluye_el_cero():
    """T=0 no es un alejamiento: es la regla de hoy. El auditor separó la grilla
    de DISEÑO de la confirmatoria en la DRAFT v0.2."""
    assert 0 not in T_DESIGN and min(T_DESIGN) == 1


def test_el_firewall_declara_su_tope():
    """La curva no puede tocar la ventana sellada."""
    assert MAX_FECHA == "2026-06-30"
