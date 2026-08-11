# -*- coding: utf-8 -*-
"""Las desviaciones declaradas de `bigtrap2.py` frente al `.cs` v2.2 se MIDEN.

El kernel Python declara en su docstring que no implementa el secuenciador
causal ni la politica de rotura del `.cs` v2.2 porque no tiene el defecto que
esas dos piezas corrigen. Eso es un **argumento**, y un argumento no sostiene
una declaracion de version: `meta_line()` dice `version=2.2` y un consumidor
del export va a leer eso como equivalencia semantica.

Estos tests convierten el argumento en una medicion. El `.cs` v2.2 evalua dos
condiciones para decidir si rompe la sesion:

  1. el bloque de eventos tiene exactamente K y su volumen cierra con la barra;
  2. el OHLC del bloque coincide con el OHLC de la barra (auto-verificacion).

Si las dos valen SIEMPRE en Python, `sesionNoConfiable` nunca se activaria y la
politica es codigo muerto. Si alguna falla, la desviacion **deja de ser no-op**
y hay algo que portar — y se entera la suite, no una auditoria seis meses
despues.

Ventana REAL y pre-holdout a proposito: sobre sinteticos la identidad se
cumple por construccion del generador y el test no probaria nada.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone

import numpy as np
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge.indicators import bigtrap2
from edgelab.bridge.ticks import load_canonical_parquet

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CS = os.path.join(REPO, "nt8", "BigTrap2.cs")
PARQUET = os.path.join(REPO, "data", "nt8", "6E", "6E_09-26_ticks.parquet")

# sha256 canonico del `.cs` v2.2, declarado en
# docs/parity_coverage/PEDIDOS_NT8_2026-07-27.md
#
# NO MOVER este pin para hacer pasar el test sin evidencia. El .cs avanzo a
# v2.5.1 (commits v2.3-v2.5.1, atribucion causal de eventos a barra, camino
# SOLO tick) sin que nadie re-corriera el gate semantico P1/P2 contra un
# oraculo fresco -- ver la adjudicacion completa, diff por diff, en
# docs/P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md. Esos dos tests SIGUEN
# EN ROJO A PROPOSITO: confirman que el pin sigue sin actualizarse, no que
# algo se rompio hoy. El veredicto de esa adjudicacion es WARN, no FAIL: el
# mecanismo que v2.3-v2.5.1 corrige (buffer+ancla incremental) no tiene
# analogo en bars.py, que asigna por indice de array (tick_bar_idx) desde
# siempre -- ver test_tick_bars_count.
SHA256_CS_CANONICO = "75910484b7d87510d8b4e015251106177a41cb8d7f4ee9b7240dc6ebf914c431"

# Ventana pre-holdout (holdout sellado: 2026-07-01 -> 2026-12-31). Dos dias
# alcanzan para cruzar una frontera de sesion, que es donde vive el caso dificil.
VENTANA = ("2026-06-15T00:00:00", "2026-06-17T00:00:00")
RESOLUCIONES = (10, 25)

_RE_VER = re.compile(r"indicator=BigTrap2,version=([0-9]+(?:\.[0-9]+)*)")


def _ns(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp() * 1e9)


@pytest.fixture(scope="module")
def ticks_reales():
    if not os.path.exists(PARQUET):
        pytest.skip("parquet canonico F2 no disponible en este entorno")
    return load_canonical_parquet(PARQUET, contract="6E 09-26",
                                  start_utc_ns=_ns(VENTANA[0]),
                                  end_utc_ns=_ns(VENTANA[1]))


# --------------------------------------------------- la desviacion es no-op
@pytest.mark.parametrize("k", RESOLUCIONES)
def test_el_volumen_del_footprint_cierra_con_la_barra(ticks_reales, k):
    """Condicion 1 del `.cs` v2.2. Es la metrica de FOOTPRINT_MISMATCH v2.1."""
    barras = B.build_tick_bars(ticks_reales, ticks_per_bar=k)
    fps = B.build_footprints(ticks_reales, barras)
    malas = B.footprint_volume_mismatches(barras, fps)
    assert not malas, (
        "%d barra(s) con footprint que no cierra a tick:%d — la politica de "
        "rotura DEJA de ser no-op: %r" % (len(malas), k, malas[:3]))


@pytest.mark.parametrize("k", RESOLUCIONES)
def test_el_ohlc_del_slice_de_ticks_es_el_de_la_barra(ticks_reales, k):
    """Condicion 2 del `.cs` v2.2: la auto-verificacion del secuenciador.

    Se reconstruye el OHLC desde los ticks agrupados por `tick_bar_idx` —el
    mismo criterio de pertenencia que usa el footprint— y se exige identidad
    EXACTA en ticks enteros contra el OHLC que publico el bar builder. Es la
    comparacion que en NT8 fallaba y disparaba la rotura.
    """
    barras = B.build_tick_bars(ticks_reales, ticks_per_bar=k)
    idx = np.asarray(barras.tick_bar_idx)
    px = np.asarray(ticks_reales.price_ticks)
    fallas = []
    for b in range(len(barras)):
        sel = px[idx == b]
        if sel.size == 0:
            fallas.append((b, "barra sin ticks asignados"))
            continue
        if not (sel[0] == barras.open_t[b] and sel[-1] == barras.close_t[b]
                and sel.max() == barras.high_t[b] and sel.min() == barras.low_t[b]):
            fallas.append((b, "OHLC slice=(%d,%d,%d,%d) barra=(%d,%d,%d,%d)"
                           % (sel[0], sel.max(), sel.min(), sel[-1],
                              barras.open_t[b], barras.high_t[b],
                              barras.low_t[b], barras.close_t[b])))
    assert not fallas, (
        "%d barra(s) donde el slice de ticks no reproduce el OHLC a tick:%d — "
        "la auto-verificacion del `.cs` habria roto la sesion: %r"
        % (len(fallas), k, fallas[:3]))


@pytest.mark.parametrize("k", RESOLUCIONES)
def test_el_kernel_no_emite_footprint_mismatch_sobre_datos_reales(ticks_reales, k):
    """Cierre de las dos condiciones por el camino publico del kernel."""
    barras = B.build_tick_bars(ticks_reales, ticks_per_bar=k)
    fps = B.build_footprints(ticks_reales, barras)
    res = bigtrap2.run(ticks_reales, barras, fps)
    mism = [e for e in res["events"] if e["type"] == "FOOTPRINT_MISMATCH"]
    assert not mism, "tick:%d emitio %d FOOTPRINT_MISMATCH" % (k, len(mism))


# ------------------------------------------------------------- procedencia
# Los dos tests que siguen son xfail ESTRICTO a proposito -- NO ocultan el
# drift, lo hacen imposible de ignorar en silencio: si algun dia vuelven a
# pasar (alguien actualizo el pin sin querer, o sin la adjudicacion formal)
# pytest los reporta como XPASS y la suite FALLA. Ver la adjudicacion
# completa en docs/P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md antes de
# tocar el pin o remover estos marcadores.
@pytest.mark.xfail(
    strict=True,
    reason="drift real, adjudicado WARN en P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md "
           "-- .cs avanzo a v2.5.1 sin re-validar el pin v2.2; NO mover sin leer esa adjudicacion")
def test_el_cs_canonico_es_el_declarado():
    """Si el `.cs` cambia sin actualizar el pin, la version declarada miente."""
    if not os.path.exists(CS):
        pytest.skip("nt8/BigTrap2.cs no disponible")
    with open(CS, "rb") as fh:
        got = hashlib.sha256(fh.read()).hexdigest()
    assert got == SHA256_CS_CANONICO, (
        "nt8/BigTrap2.cs cambio (sha256 %s != %s pineado). Adjudicado en "
        "docs/P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md: WARN, no FAIL "
        "-- v2.3-v2.5.1 son atribucion causal SOLO-tick, sin analogo en "
        "bars.py. Revisar esa adjudicacion (no solo el docstring) ANTES de "
        "mover este pin." % (got, SHA256_CS_CANONICO))


@pytest.mark.xfail(
    strict=True,
    reason="drift real, adjudicado WARN en P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md "
           "-- kernel declara 2.2, .cs canonico es 2.5.1; paridad semantica v2.5.1 PENDING")
def test_la_version_del_kernel_coincide_con_la_del_cs():
    """El bug que este test existe para que no vuelva: el kernel declaraba
    `version=2.0` mientras el `.cs` canonico estaba en v2.2. Un export con la
    version equivocada contamina la procedencia de todo lo que se genere."""
    if not os.path.exists(CS):
        pytest.skip("nt8/BigTrap2.cs no disponible")
    with open(CS, encoding="utf-8", errors="replace") as fh:
        cs_ver = _RE_VER.search(fh.read())
    assert cs_ver, "no se encontro `indicator=BigTrap2,version=` en el .cs"
    py_ver = _RE_VER.search(bigtrap2.meta_line(dict(bigtrap2.DEFAULTS), "6E", 5e-05))
    assert py_ver, "no se encontro la version en `meta_line()`"
    assert py_ver.group(1) == cs_ver.group(1), (
        "el kernel Python declara version=%s y el .cs canonico version=%s -- "
        "drift adjudicado en docs/P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md "
        "(WARN: no afecta time:1 ni el corpus F0.2-F1.1xregimen, arquitectura "
        "de bars.py inmune por construccion al mecanismo que cambio)"
        % (py_ver.group(1), cs_ver.group(1)))
