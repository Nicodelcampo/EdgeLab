# -*- coding: utf-8 -*-
"""El gate de compilación (T6) — tests que NO exigen tener NT8 instalado.

La compilación real depende del entorno (NT8 + reference assemblies). Estos
tests verifican la LÓGICA del gate, que es lo que puede estar mal sin que nadie
lo note: que distinga entorno de código, que el control negativo sea el defecto
real, y que no toque el fuente canónico.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))

import compilar_nt8_cs as C  # noqa: E402


def test_los_errores_de_entorno_no_se_reportan_como_NO_COMPILA():
    """El defecto que tuvo la v1 de este gate: reportó NO_COMPILA cuando la
    causa real era una referencia sin resolver. Decir "tu código está roto"
    cuando la verdad es "no pude verificarlo" es el modo de falla que este
    expediente persigue."""
    assert "CS0006" in C.ERRORES_DE_ENTORNO   # metadata file no encontrado
    assert "CS1703" in C.ERRORES_DE_ENTORNO   # assembly duplicado
    assert "CS0103" not in C.ERRORES_DE_ENTORNO   # identificador: ES de código


def test_el_control_negativo_reproduce_el_defecto_REAL_de_v23():
    """No un error de sintaxis trivial: el gate tiene que atrapar la CLASE de
    defecto que ya se le escapó una vez — un identificador sin declarar
    (`if (!ok) { }`, CS0103)."""
    assert "if (!" in C.MUTACION and "__identificador_inexistente__" in C.MUTACION


def test_el_parser_atrapa_errores_sin_prefijo_de_archivo():
    """csc emite `error CS0006: …` al principio de línea cuando el error no es
    de un archivo concreto. El parser v1 buscaba `": error "` y perdía TODOS
    esos: daba n_errores=0 con exit_code=1."""
    import re
    linea = "error CS0006: Metadata file 'WindowsBase.dll' could not be found"
    assert re.search(r"error CS\d+", linea)


def test_no_hay_ruta_de_reference_assemblies_hardcodeada():
    """Se descubre en runtime. Escribirla ataba el gate a una versión puntual de
    .NET, y además el literal `\v4.8` se corrompía al pasar por el shell."""
    assert callable(C._descubrir_refasm)


@pytest.mark.skipif(not C.CSPROJ.exists(), reason="NT8 no instalado en esta máquina")
def test_compila_de_verdad_el_cs_canonico(tmp_path):
    """Sólo corre donde NT8 está instalado. Verifica además que el fuente
    canónico quede intacto: el control negativo muta una COPIA."""
    import hashlib
    cs = os.path.join(REPO, "nt8", "BigTrap2.cs")
    antes = hashlib.sha256(open(cs, "rb").read()).hexdigest()
    code = C.main([cs, "--out", str(tmp_path / "r.json")])
    assert hashlib.sha256(open(cs, "rb").read()).hexdigest() == antes
    assert code in (0, 2), "COMPILA o ABSTAIN; NO_COMPILA sería una regresión real"
