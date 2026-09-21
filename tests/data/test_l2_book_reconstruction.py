"""Reconstruccion del libro L2 por posicion (tools/build_l2_viewer_bundle.py)."""
import importlib.util
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "build_l2", Path(__file__).resolve().parents[2] / "tools" / "build_l2_viewer_bundle.py")
B = importlib.util.module_from_spec(SPEC)
sys.modules["build_l2"] = B
SPEC.loader.exec_module(B)


def test_alta_cambio_y_baja_por_posicion():
    bids = []
    for lvl, tick in enumerate([100, 99, 98]):
        B.apply_l2(None, bids, 0, lvl, tick, 5)            # alta al final
    assert [t for t, _ in bids] == [100, 99, 98]
    B.apply_l2(None, bids, 0, 0, 101, 2)                    # alta en el tope: corre lo de abajo
    assert [t for t, _ in bids] == [101, 100, 99, 98]
    B.apply_l2(None, bids, 1, 1, 100, 9)                    # cambio de tamano
    assert bids[1] == [100, 9]
    B.apply_l2(None, bids, 2, 0, 0, 0)                      # baja del tope: sube lo de abajo
    assert [t for t, _ in bids] == [100, 99, 98]


def test_eventos_fuera_de_rango_no_rompen():
    b = [[10, 1]]
    B.apply_l2(None, b, 2, 5, 0, 0)                         # baja de una posicion inexistente
    B.apply_l2(None, b, 1, 3, 9, 4)                         # cambio fuera de rango: se agrega
    B.apply_l2(None, b, 0, 9, 8, 2)                         # alta mas alla del final: se agrega al final
    assert [t for t, _ in b] == [10, 9, 8]


def test_rechaza_sesiones_desde_el_corte_pre_holdout(tmp_path):
    with pytest.raises(SystemExit):
        B.main(["--base", str(tmp_path), "--date", "20260630", "--instrument", "GC", "--contract", "GC 08-26",
                "--out", str(tmp_path)])
    assert B.CUTOFF_DATE == 20260630
