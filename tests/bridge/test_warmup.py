# -*- coding: utf-8 -*-
"""Warm-up: fija el criterio de frontera con evidencia dura, no con opinión.

`docs/nt8_indicator_parity_contract.md` mide, sobre BigTrap2 v2.2 real:

    2026-07-12 -> 07-17: primera sesion 667 mismatch/0 zonas, posteriores 0/404
    2026-06-14 -> 06-16: primera sesion 484 mismatch/0 zonas, posteriores 1/78

y PRED-003_tickbar_fifo.json, campo P2, sobre tick:10:

    primera_sesion_del_chart: mismatches 3280, zonas_creadas 0
    sesiones_posteriores:     mismatches 0,    zonas_creadas 70

El corte es binario: CERO zonas creadas antes de la frontera, en las tres
mediciones. Estos tests fijan que `primera_frontera_ns` encuentra esa MISMA
frontera sobre datos reales, y que el filtro deja pasar exactamente lo que la
evidencia dice que es comparable.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge.ticks import TickSeries, load_canonical_parquet
from edgelab.bridge.warmup import (SinFronteraDeSesionError,
                                   excluir_zonas_de_warmup,
                                   primera_frontera_ns)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET = os.path.join(REPO, "data", "nt8", "6E", "6E_09-26_ticks.parquet")


def _ns(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp() * 1e9)


@pytest.fixture(scope="module")
def ticks_reales():
    if not os.path.exists(PARQUET):
        pytest.skip("parquet canonico F2 no disponible en este entorno")
    return load_canonical_parquet(
        PARQUET, contract="6E 09-26",
        start_utc_ns=_ns("2026-06-15T00:00:00"), end_utc_ns=_ns("2026-06-17T00:00:00"))


# ------------------------------------------------------------------ sintético
def _serie_dos_sesiones():
    """Dos sesiones separadas por una pausa nocturna real (>= 17h), timestamps
    ya en UTC. La frontera esperada es el primer tick de la sesión 2."""
    t0 = _ns("2026-06-15T14:00:00")   # 09:00 CT, sesion 1 en curso
    t1 = _ns("2026-06-16T14:00:00")   # 09:00 CT del dia siguiente, sesion 2
    ts = np.array([t0, t0 + 1_000_000_000, t1, t1 + 1_000_000_000], dtype=np.int64)
    return TickSeries(ts, np.array([100, 101, 102, 103], np.int64),
                      np.ones(4, np.float64), None, None,
                      np.arange(4, dtype=np.int64), 0.25, "SYN", "SYN", "test")


def test_frontera_es_el_primer_tick_de_la_segunda_sesion():
    tk = _serie_dos_sesiones()
    frontera = primera_frontera_ns(tk.ts_ns)
    assert frontera == int(tk.ts_ns[2])


def test_una_sola_sesion_no_tiene_frontera():
    """Si la ventana entera es una sesión, TODO es warm-up: error explícito,
    no un corte arbitrario ni una lista vacía silenciosa."""
    ts = np.array([_ns("2026-06-15T14:00:00"), _ns("2026-06-15T15:00:00")], np.int64)
    with pytest.raises(SinFronteraDeSesionError):
        primera_frontera_ns(ts)


def test_ventana_vacia_falla_explicito():
    with pytest.raises(SinFronteraDeSesionError):
        primera_frontera_ns(np.array([], dtype=np.int64))


def test_excluir_zonas_de_warmup_filtra_por_created_ms():
    frontera_ns = _ns("2026-06-16T00:00:00")
    frontera_ms = frontera_ns // 1_000_000
    zonas = [
        dict(id="antes", created_ms=frontera_ms - 1),
        dict(id="justo_en_el_limite", created_ms=frontera_ms),
        dict(id="despues", created_ms=frontera_ms + 1),
        dict(id="sin_fecha", created_ms=None),
    ]
    vivas = {z["id"] for z in excluir_zonas_de_warmup(zonas, frontera_ns)}
    assert vivas == {"justo_en_el_limite", "despues"}


# --------------------------------------------------------------------- real
def test_frontera_sobre_ticks_reales_cae_en_un_cambio_de_sesion(ticks_reales):
    """La frontera calculada tiene que SER un cambio de sesion real de
    `bars.session_ids` — no una aproximacion ni un redondeo a medianoche."""
    frontera = primera_frontera_ns(ticks_reales.ts_ns)
    ses = B.session_ids(ticks_reales.ts_ns)
    idx = int(np.searchsorted(ticks_reales.ts_ns, frontera))
    assert idx > 0 and ses[idx] != ses[idx - 1], (
        "la frontera calculada no coincide con un cambio real de session_ids")


def test_excluir_warmup_deja_fuera_toda_la_primera_sesion(ticks_reales):
    """Ninguna zona 'creada' en la primera sesion sobrevive al filtro,
    coincidiendo con el 0 zonas_creadas medido en la evidencia real."""
    frontera_ns = primera_frontera_ns(ticks_reales.ts_ns)
    primer_tick_ms = int(ticks_reales.ts_ns[0]) // 1_000_000
    zona_de_warmup = dict(id="z0", created_ms=primer_tick_ms)
    assert excluir_zonas_de_warmup([zona_de_warmup], frontera_ns) == []
