# -*- coding: utf-8 -*-
"""Preflight de calendario (Decisión 2 de Nico, 2026-07-26).

Incluye el test que **ancla contra el oráculo real**: las fronteras que declara
NT8 tienen que coincidir con las de `sessions.py`. Si algún día dejan de
coincidir, este test lo dice antes de que se gaste un oráculo persiguiendo una
zona equivocada.
"""
import csv
import os

import pytest

from edgelab.bridge import sessions as S
from edgelab.bridge.session_preflight import (
    CalendarMismatch, nt8_boundaries, preflight, python_boundaries)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORACULO = os.path.join(REPO, "oracles", "HFTZones2_adaptive_6E_0926_v22.csv")

CT_17 = 17  # las sesiones CME ETH abren 17:00 CT


def _eventos_de_inicio_de_sesion():
    """ts (ns) de los eventos con que NT8 abre cada sesión."""
    with open(ORACULO, encoding="utf-8-sig") as f:
        filas = [l.rstrip("\n") for l in f if not l.startswith("#")]
    return [int(r["unix_ms"]) * 1_000_000 for r in csv.DictReader(filas)
            if r["event_type"] in ("CALIBRATION", "CALIBRATION_PENDING")]


@pytest.mark.skipif(not os.path.exists(ORACULO), reason="sin oráculo HFTZones2")
def test_las_fronteras_de_nt8_coinciden_con_sessions_py():
    """Ancla contra el oráculo REAL: NT8 abre sesión exactamente a las 17:00 CT."""
    ev = _eventos_de_inicio_de_sesion()
    assert len(ev) >= 5, "el oráculo no trae suficientes eventos de sesión"
    for ns in ev:
        b = S.session_begin_ns(ns)
        # El evento cae DENTRO de la sesión que abre, y esa sesión abre 17:00 CT.
        assert 0 <= (ns - b) < 3600 * 1_000_000_000, (
            "el evento de NT8 no cae en el primer tramo de la sesión de Python")
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        loc = datetime.fromtimestamp(b / 1e9, tz=timezone.utc).astimezone(
            ZoneInfo("America/Chicago"))
        assert (loc.hour, loc.minute, loc.second) == (CT_17, 0, 0), loc


@pytest.mark.skipif(not os.path.exists(ORACULO), reason="sin oráculo HFTZones2")
def test_preflight_pasa_contra_el_oraculo_real():
    ev = _eventos_de_inicio_de_sesion()
    nt8 = nt8_boundaries(ev)
    # Python evaluado sobre los mismos instantes: mismo rango, misma cobertura.
    py = python_boundaries(ev)
    rep = preflight(nt8, py, strict=True)
    assert rep["ok"]
    assert rep["n_sesiones_nt8"] == rep["n_sesiones_python"] >= 5


EV4 = [int(1783548000184e6), int(1783634400892e6),      # 07-08, 07-09
       int(1783893600060e6), int(1783980000756e6)]     # 07-12, 07-13


def test_aborta_cuando_falta_una_sesion_EN_EL_MEDIO():
    """El caso que el preflight existe para atrapar.

    Tiene que ser un hueco INTERIOR: una sesión de más pasado el último límite
    de NT8 no es desalineamiento, es que el chart cargó menos historia. Esa
    distinción es justamente lo que hace usable al preflight — si abortara por
    rangos distintos, abortaría siempre.
    """
    nt8 = nt8_boundaries(EV4)
    py = python_boundaries([EV4[0], EV4[2], EV4[3]])    # falta 07-09
    with pytest.raises(CalendarMismatch) as e:
        preflight(nt8, py, strict=True)
    msg = str(e.value)
    # El mensaje tiene que decir QUÉ sesión y QUÉ fecha, no sólo que hay diff.
    assert "SOLO_NT8" in msg, msg
    assert "2026-07-10" in msg, msg            # trade-date de la sesión faltante
    assert "No se comparan zonas" in msg


def test_rango_de_carga_distinto_NO_es_desalineamiento():
    """Que el parquet tenga más historia que el chart es normal, no un fallo."""
    nt8 = nt8_boundaries(EV4[:2])
    py = python_boundaries(EV4)                # Python ve dos sesiones más, después
    rep = preflight(nt8, py, strict=True)
    assert rep["ok"] and rep["diffs"] == []


def test_no_strict_reporta_sin_levantar():
    nt8 = nt8_boundaries(EV4)
    py = python_boundaries([EV4[0], EV4[2], EV4[3]])
    rep = preflight(nt8, py, strict=False)
    assert not rep["ok"]
    assert any(d["tipo"] == "SOLO_NT8" for d in rep["diffs"])


def test_sin_fronteras_no_se_afirma_paridad():
    with pytest.raises(CalendarMismatch):
        preflight([], [("2026-07-13", 1)], strict=True)


def test_el_offset_de_indice_se_declara_no_se_absorbe():
    """NT8 numera desde la primera barra del chart; Python desde el parquet.

    Ese offset es benigno PERO tiene que quedar declarado: si cambia entre
    corridas es que el chart cargó otro rango, y eso invalida la comparación.
    """
    ev = [int(1783548000184e6), int(1783634400892e6), int(1783893600060e6)]
    b = nt8_boundaries(ev)
    rep = preflight(b, b, nt8_index_base=b[1][0], strict=True)
    assert rep["offset_de_indice"] == 1


def test_base_fuera_del_parquet_es_discrepancia():
    ev = [int(1783548000184e6), int(1783634400892e6)]
    b = nt8_boundaries(ev)
    with pytest.raises(CalendarMismatch) as e:
        preflight(b, b, nt8_index_base="1999-01-04", strict=True)
    assert "BASE_NT8_FUERA_DEL_PARQUET" in str(e.value)
