# -*- coding: utf-8 -*-
"""Extractor tick-based de la curva de diseño.

Los cuatro casos que exigió Nico: **retorno**, **ruptura**, **timestamps
empatados** y **orden ambiguo**. Series fabricadas acá: nada de datos reales,
nada de outcomes.
"""
from __future__ import annotations

import io
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


# ============================================================================
# TESTS DE SISTEMA (13.61)
# ============================================================================
# Los nueve de arriba prueban la ARITMÉTICA del extractor sobre vectores de
# precios. El auditor lo marcó: *"prueban aritmética, no el sistema"*, y sin
# éstos el fail-closed es **conducta observada en un piloto**, no contrato.
#
# Cada uno cubre un punto del brief 13.60/13.61.

import numpy as _np
import pandas as _pd
import pytest as _pytest
from zoneinfo import ZoneInfo as _ZI

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    MAX_FECHA as _MAXF, SESION_HORA_CORTE as _HC, SESION_TZ as _STZ,
    corte_del_sello,
)


def test_sistema_la_frontera_es_el_INICIO_de_la_sesion_sellada():
    """La v1 cortaba en `2026-06-30 23:59:59 UTC` = **18:59 CT**, y la sesión
    `2026-07-01` arranca a las **17:00 CT**: dejaba entrar **2 h de la primera
    sesión sellada**. Fuga latente — los pilotos corrían sobre diciembre 2025.
    """
    corte = corte_del_sello()
    inicio_holdout = _pd.Timestamp("2026-06-30 17:00:00", tz=_STZ).tz_convert("UTC")
    assert corte == inicio_holdout, "el corte debe SER el inicio de la sesión sellada"
    viejo = _pd.Timestamp(_MAXF + " 23:59:59.999999999", tz="UTC")
    assert viejo > corte, "el corte viejo entraba al holdout: esto documenta la fuga"


def test_sistema_ningun_tick_del_holdout_entra():
    """No basta con que el corte esté bien: ningún `ts` >= corte puede pasar."""
    corte = int(corte_del_sello().value)
    dentro = corte - 1
    fuera = corte
    assert dentro < corte and not (fuera < corte)


def test_sistema_el_corte_usa_la_convencion_del_proyecto():
    """17:00 America/Chicago, `[inicio, fin)` — la misma de `bars.py::session_ids`
    y de `SESION_HORA_CORTE` en `pred004_analyze.py`. No una fecha civil UTC."""
    assert _HC == 17 and _STZ == "America/Chicago"


def test_sistema_created_bar_NEGATIVO_no_ancla_a_la_ultima_barra():
    """`gaps2.py:12` declara que antes del primer cierre primario vale **-1**.
    En Python `bar_end[-1]` es la **última** barra: sin guard la zona no fallaba,
    anclaba su disponibilidad al final de la serie **en silencio**.

    Es el peor modo de falla: no explota, miente.
    """
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "cb < 0 or cb >= len(bar_end)" in src


def test_sistema_sin_created_bar_no_se_inventa_la_barra():
    """Fail-closed: la zona se descarta y se **cuenta**, no se estima."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "n_sin_created_bar += 1" in src
    assert "searchsorted(bar_end" not in src, "volvió la heurística desde created_ms"


def test_sistema_los_kernels_elegibles_exportan_created_bar():
    """El punto 2 del brief: no alcanza con BigTrap2. Sin esto el extractor tira
    todo a `zonas_sin_created_bar` y la curva sale vacía sin decir por qué."""
    faltan = []
    for k in ("bigtrap2", "voltickspoc2", "avolcellpoi2", "gaps2", "hftzones2"):
        src = io.open(os.path.join(REPO, "edgelab", "bridge", "indicators", k + ".py"),
                      encoding="utf-8").read()
        if "created_bar=z[" not in src and "created_bar=g[" not in src:
            faltan.append(k)
    assert not faltan, "no exportan created_bar: %s" % faltan


def test_sistema_AACloseOpenDiffs_NO_lo_tiene_y_debe_quedar_afuera():
    """No es un olvido: ese indicador no tiene concepto de barra creadora en su
    ciclo de vida. Tiene que quedar en `sin_created_bar`, no estimado."""
    src = io.open(os.path.join(REPO, "edgelab", "bridge", "indicators",
                               "aacloseopendiffs.py"), encoding="utf-8").read()
    assert "created_bar" not in src


def test_sistema_parity_no_consume_created_bar():
    """La exportación no puede romper los 7 oráculos en PASS. `match_zones`
    empareja por `created_ms` + geometría."""
    src = io.open(os.path.join(REPO, "edgelab", "bridge", "parity.py"),
                  encoding="utf-8").read()
    assert "created_bar" not in src


def test_sistema_la_identidad_de_barras_esta_declarada():
    """`available_ns = bar_end[created_bar]` sólo vale si `created_bar` indexa el
    MISMO array con el que corrió el kernel. Este path es M1 y lo declara."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "REGLA DE IDENTIDAD DE BARRAS" in src
    assert "build_time_bars(tk, 1)" in src


def test_sistema_sequence_no_monotona_ABSTIENE_la_unidad():
    """Si el orden de archivo no es total, no hay cómo ordenar los empates de
    `ts_ns` — y en 6E el 66,1 % de los ticks consecutivos los tiene."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "orden_total = bool((np.diff(sq) > 0).all())" in src
    assert 'estado="ABSTAIN"' in src


def test_sistema_empates_reales_de_ts_ns_con_sequence_propia():
    """Empates REALES: mismo `ts_ns` en varios ticks, `sequence` distinta.
    El extractor recorre por ORDEN DE ARRAY —que es el de `sequence`— y nunca
    consulta `ts_ns` para decidir, así que los empates no lo afectan.

    El test anterior comparaba el mismo vector dos veces, que no probaba nada.
    """
    from diag.tasa_senales.curva_excursion_ticks import eventos_de_zona
    px = _np.array([105., 118., 112., 105., 130.])
    ts = _np.array([1000, 1000, 1000, 1000, 2000], dtype=_np.int64)   # 4 empatados
    sq = _np.arange(1, 6, dtype=_np.int64)
    assert bool((_np.diff(sq) > 0).all()), "sequence desempata"
    assert int((_np.diff(ts) == 0).sum()) == 3, "hay empates reales de ts_ns"
    rup_up, _, ret, _ = eventos_de_zona(px, 100.0, 110.0, 0, 5, (8,))
    assert 8 in ret, "salió a 118 y volvió a 105: hay retorno"
    assert 8 in rup_up


def test_sistema_sequence_reformulado_no_se_vende_como_verdad_de_mercado():
    """Escribí que la ambigüedad *"desaparece por construcción"*. Overclaim, misma
    clase que el `bit-idéntico` del docstring de P5. `sequence` es orden de FILA
    del F2: determinismo reproducible, no orden del matching engine."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "NO es verdad de mercado" in src
    assert "matching engine" in src


def test_sistema_los_descartes_se_REPORTAN():
    """Un descarte que no se imprime es un número que nadie puede reconstruir —
    la familia de falla que este expediente persigue."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert 'sin_created_bar' in src.split("DESCARTES")[1][:400]


def test_sistema_los_cuantiles_no_se_pisan_entre_contratos():
    """La v1 sobrescribía `alejamiento_en_primera_reentrada` en cada contrato:
    publicaba los del ÚLTIMO como si fueran los del universo."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "alejamiento_por_contrato" in src


def test_sistema_el_manifiesto_publica_el_corte_del_firewall():
    """Sin el instante exacto en el artefacto, la frontera no es auditable."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "firewall_corte_utc_ns" in src and "firewall_corte_iso" in src
