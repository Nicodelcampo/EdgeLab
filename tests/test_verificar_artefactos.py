# -*- coding: utf-8 -*-
"""`tools/verificar_artefactos.py::clasificar_hash` -- las tres clases que
importan: canonico, legacy (otra convencion de serializacion valida) y
mismatch real. Agregado 2026-08-11 a pedido del auditor, que encontro que la
v1 devolvia un `OK` indiferenciado sin decir que convencion habia hecho
match."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.verificar_artefactos import calcular_hash, clasificar_hash  # noqa: E402

# string con caracteres no-ASCII: sin esto, ensure_ascii=True/False producen
# el mismo texto y el test no distinguiria nada.
PAYLOAD = {"mensaje": "atracción, no resistencia — sesión de precisión", "n": 201}


def test_canonico_ensure_ascii_false():
    declarado = calcular_hash(PAYLOAD, ensure_ascii=False)
    clasif, serial, recalc = clasificar_hash(dict(PAYLOAD), declarado)
    assert clasif == "OK"
    assert serial == "json_sort_keys_ensure_ascii_false"
    assert recalc == declarado


def test_legacy_ensure_ascii_true():
    declarado = calcular_hash(PAYLOAD, ensure_ascii=True)
    clasif, serial, _recalc = clasificar_hash(dict(PAYLOAD), declarado)
    assert clasif == "OK_LEGACY"
    assert serial == "json_sort_keys_ensure_ascii_true"


def test_mismatch_real():
    clasif, serial, recalc = clasificar_hash(dict(PAYLOAD), "0" * 64)
    assert clasif == "MISMATCH"
    assert serial is None
    assert recalc == calcular_hash(PAYLOAD, ensure_ascii=False)


def test_sin_payload_sha256():
    clasif, serial, _recalc = clasificar_hash(dict(PAYLOAD), None)
    assert clasif == "SIN_PAYLOAD_SHA256"
    assert serial is None


def test_ascii_puro_no_distingue_las_dos_convenciones_a_proposito():
    """Si el payload no tiene caracteres no-ASCII, ensure_ascii=True/False dan
    el MISMO hash -- coincide con OK (canonico), no con OK_LEGACY, porque
    `clasificar_hash` prueba canonico primero. Documentado para que nadie lea
    esto como que la deteccion de legacy esta rota."""
    payload_ascii = {"n": 1, "ok": True}
    declarado = calcular_hash(payload_ascii, ensure_ascii=True)
    clasif, _serial, _recalc = clasificar_hash(dict(payload_ascii), declarado)
    assert clasif == "OK"
