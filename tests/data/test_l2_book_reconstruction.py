"""Reconstruccion FAIL-CLOSED del libro L2 por posicion (tools/build_l2_viewer_bundle.py).

Auditoria 2026-09-21: `apply_l2` ya NO repara en silencio un `level` fuera de rango (recortarlo a la posicion
valida mas cercana inventaba una posicion que el feed no dijo). Ahora devuelve `None` si el evento era valido, o
un codigo `ABSTAIN_*` si no — y el libro NO se modifica cuando el evento es invalido.
"""
import importlib.util
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "build_l2", Path(__file__).resolve().parents[2] / "tools" / "build_l2_viewer_bundle.py")
B = importlib.util.module_from_spec(SPEC)
sys.modules["build_l2"] = B
SPEC.loader.exec_module(B)


def test_alta_cambio_y_baja_por_posicion_devuelven_none_si_son_validos():
    bids = []
    for lvl, tk in enumerate([100, 99, 98]):
        assert B.apply_l2(bids, 0, lvl, tk, 5) is None            # alta al final
    assert [t for t, _ in bids] == [100, 99, 98]
    assert B.apply_l2(bids, 0, 0, 101, 2) is None                 # alta en el tope: corre lo de abajo
    assert [t for t, _ in bids] == [101, 100, 99, 98]
    assert B.apply_l2(bids, 1, 1, 100, 9) is None                 # cambio de tamano
    assert bids[1] == [100, 9]
    assert B.apply_l2(bids, 2, 0, 0, 0) is None                   # baja del tope: sube lo de abajo
    assert [t for t, _ in bids] == [100, 99, 98]


def test_nivel_fuera_de_rango_devuelve_abstain_y_NO_modifica_el_libro():
    b = [[10, 1]]
    snapshot = [list(x) for x in b]

    assert B.apply_l2(b, 2, 5, 0, 0) == B.ABSTAIN_INVALID_LEVEL      # baja de una posicion inexistente
    assert b == snapshot                                            # el libro queda intacto, no se repara

    assert B.apply_l2(b, 1, 3, 9, 4) == B.ABSTAIN_INVALID_LEVEL      # cambio fuera de rango
    assert b == snapshot

    assert B.apply_l2(b, 0, 9, 8, 2) == B.ABSTAIN_INVALID_LEVEL      # alta mas alla de len(book)+1
    assert b == snapshot


def test_alta_justo_en_el_borde_es_valida_alta_mas_alla_no():
    b = [[10, 1], [9, 1]]
    assert B.apply_l2(b, 0, 2, 8, 1) is None            # alta en lvl == len(book): valida, va al final
    assert [t for t, _ in b] == [10, 9, 8]
    assert B.apply_l2(b, 0, 10, 7, 1) == B.ABSTAIN_INVALID_LEVEL   # alta con lvl > len(book): invalida


def test_rechaza_sesiones_desde_el_corte_pre_holdout(tmp_path):
    try:
        B.main(["--base", str(tmp_path), "--date", "20260630", "--instrument", "GC", "--contract", "GC 08-26",
                "--out", str(tmp_path)])
        assert False, "debia abortar"
    except SystemExit:
        pass
    assert B.CUTOFF_DATE == 20260630
