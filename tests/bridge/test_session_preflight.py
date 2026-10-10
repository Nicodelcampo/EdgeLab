"""Synthetic calendar preflight cases ported from foundation.
Real-oracle cases remain in foundation; not copied, skipped or executed here.
"""
import pytest
from edgelab.bridge import sessions as S
from edgelab.bridge.session_preflight import CalendarMismatch, nt8_boundaries, preflight, python_boundaries

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
