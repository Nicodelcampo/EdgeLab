# -*- coding: utf-8 -*-
"""`docs/NORTH_STAR.md` se autocita: publica al pie el sha256 de su propio
cuerpo (todo lo anterior al marcador `SHA256-BODY-ABOVE`). Ese diseño evita
el problema de un archivo que se hashea a sí mismo incluyendo su propio
hash -- pero sólo funciona si la autocita se refresca cada vez que el cuerpo
cambia. No lo hizo dos veces seguidas (2026-08-01, incidente INC-006 del
holdout y su revert): la cita quedó apuntando a una versión del cuerpo
anterior a esos dos commits, y CLAUDE.md heredó la misma cita stale.

Este test existe para que esa clase de defecto se detecte en la suite, no en
una auditoría manual meses después -- exactamente el patrón de
`test_desviacion_rotura.py::test_la_version_del_kernel_coincide_con_la_del_cs`
para el drift NT8, aplicado acá a NORTH_STAR.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NORTH_STAR = REPO / "docs" / "NORTH_STAR.md"
MARKER = b"<!-- SHA256-BODY-ABOVE -->"
_RE_FOOTER = re.compile(
    r"\*\*sha256 \(cuerpo hasta el marcador\):\*\* `([0-9a-f]{64})`")


def test_hay_exactamente_un_marcador():
    raw = NORTH_STAR.read_bytes()
    assert raw.count(MARKER) == 1, (
        "docs/NORTH_STAR.md debe tener exactamente un marcador %r -- "
        "encontrados: %d" % (MARKER, raw.count(MARKER)))


def test_la_autocita_del_pie_coincide_con_el_cuerpo_actual():
    """Si el cuerpo cambia (como en INC-006) sin refrescar la autocita, esto
    falla. No relajar el test para que pase: refrescar la autocita."""
    raw = NORTH_STAR.read_bytes()
    body = raw.split(MARKER, 1)[0].replace(b"\r\n", b"\n")
    body_sha256 = hashlib.sha256(body).hexdigest()

    text = raw.decode("utf-8")
    m = _RE_FOOTER.search(text)
    assert m, (
        "no se encontro la autocita `**sha256 (cuerpo hasta el marcador):** "
        "`<hex>`` en docs/NORTH_STAR.md")
    declarado = m.group(1)

    assert declarado == body_sha256, (
        "docs/NORTH_STAR.md cambio de cuerpo sin refrescar su autocita.\n"
        "  autocita en el pie: %s\n"
        "  cuerpo actual:      %s\n"
        "Recalcular con: hashlib.sha256(raw.split(MARKER, 1)[0].replace(b'\\r\\n', b'\\n')).hexdigest() "
        "y actualizar la linea del pie -- no relajar este test."
        % (declarado, body_sha256))


def test_el_hash_del_cuerpo_no_es_el_hash_del_archivo_completo():
    """Regresion del error propio: comparar sha256(archivo) contra la
    autocita (que es sha256(cuerpo)) da un falso mismatch aunque la autocita
    este perfectamente al dia. Documentado para que no se repita la
    confusion de dominios."""
    raw = NORTH_STAR.read_bytes().replace(b"\r\n", b"\n")
    body = raw.split(MARKER, 1)[0]
    assert hashlib.sha256(body).hexdigest() != hashlib.sha256(raw).hexdigest(), (
        "el cuerpo y el archivo completo coincidieron -- revisar si el "
        "marcador sigue estando despues de todo el contenido citable")
