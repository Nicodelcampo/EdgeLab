# -*- coding: utf-8 -*-
"""`docs/CURRENT.md` es una etiqueta escrita a mano.

Nada obliga a que sea cierta. Si nadie la actualiza, queda desactualizada
en silencio y una sesion nueva la lee como verdad. Es la misma clase de
defecto que P-34 (version=), P-35 (WARN = parity_exact), P-39 (gex_dollar
sin dolares) y P-41 (holdout_included escrito a mano).

Ya paso dos veces esta semana: el commit que decia asentar P-41 no lo
asento, y la nota que documentaba esa falla afirmaba una reparacion que
no ocurrio.

Este test no convierte CURRENT en un artefacto computado. Solo hace que
«quedo viejo» sea ruidoso:

1. todo P-NN citado en CURRENT existe como encabezado en PENDIENTE.md;
2. la Fecha declarada no queda mas de un dia atras del HEAD;
3. todo path entre backticks existe en el repo.

No relajar el test para que pase: actualizar CURRENT.md, o asentar el
P-NN en el board. Patron: tests/test_north_star_hash.py.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CURRENT = REPO / "docs" / "CURRENT.md"
PENDIENTE = REPO / "PENDIENTE.md"

_RE_P = re.compile(r"\bP-(\d+)\b")
_RE_HEADER = re.compile(r"^## P-(\d+)", re.MULTILINE)
_RE_FECHA = re.compile(r"\*\*Fecha:\*\*\s*(\d{4}-\d{2}-\d{2})")
_RE_PATH = re.compile(r"`([^`]+)`")

MAX_LAG_DAYS = 1


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_current_existe():
    assert CURRENT.is_file(), "docs/CURRENT.md desaparecio -- es el L0"


def test_todo_p_nn_citado_existe_en_el_board():
    """Un P-NN en CURRENT que no tiene encabezado en PENDIENTE.md es la
    misma mentira que un acta que cierra lo que el board no asienta."""
    current = _text(CURRENT)
    board = _text(PENDIENTE)
    citados = {int(n) for n in _RE_P.findall(current)}
    asentados = {int(n) for n in _RE_HEADER.findall(board)}
    huérfanos = sorted(citados - asentados)
    assert not huérfanos, (
        "docs/CURRENT.md cita P-NN que no tienen encabezado en PENDIENTE.md: "
        "%s. Asentarlos en el board o sacarlos de CURRENT -- no relajar "
        "este test." % huérfanos
    )


def test_la_fecha_declarada_no_queda_atras_del_head():
    """Si CURRENT dice 2026-08-15 y el HEAD es del 17, una sesion nueva
    lee un mapa de anteayer como si fuera hoy."""
    current = _text(CURRENT)
    m = _RE_FECHA.search(current)
    assert m, (
        "docs/CURRENT.md debe declarar **Fecha:** YYYY-MM-DD -- "
        "sin eso el gate no puede medir atraso"
    )
    declarado = dt.date.fromisoformat(m.group(1))
    head = subprocess.check_output(
        ["git", "log", "-1", "--format=%cs"],
        cwd=REPO,
        text=True,
    ).strip()
    head_date = dt.date.fromisoformat(head)
    lag = (head_date - declarado).days
    assert lag <= MAX_LAG_DAYS, (
        "docs/CURRENT.md declara Fecha %s y el HEAD es %s (atraso %d dias, "
        "maximo %d). Actualizar la Fecha y el cuerpo en el mismo commit "
        "que cambia el estado -- no relajar este test."
        % (declarado.isoformat(), head, lag, MAX_LAG_DAYS)
    )
    assert declarado <= head_date, (
        "docs/CURRENT.md declara Fecha %s, posterior al HEAD %s -- "
        "la fecha no se adelanta a un commit que no existe"
        % (declarado.isoformat(), head)
    )


def test_los_paths_entre_backticks_existen():
    """Un path citado que no esta en el arbol es otra etiqueta que no se
    deriva del contenido."""
    current = _text(CURRENT)
    faltan = []
    for raw in _RE_PATH.findall(current):
        token = raw.strip()
        if not token or token.startswith("http") or " " in token:
            continue
        if not any(token.startswith(p) for p in (
            "docs/", "PENDIENTE.md", "CLAUDE.md", "PLAN.md", "tests/",
            "edgelab/", "tools/",
        )):
            continue
        # recortes deliberados tipo docs/audits/ENTRADA_013_...
        if token.endswith("..."):
            continue
        if not (REPO / token).exists():
            faltan.append(token)
    assert not faltan, (
        "docs/CURRENT.md cita paths que no existen: %s. Corregir el path "
        "o crear el archivo -- no relajar este test." % faltan
    )
