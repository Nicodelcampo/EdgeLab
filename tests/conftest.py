"""Configuración común de la suite.

Caché de numba aislado por corrida (2026-10-22). Varias pruebas cargan herramientas de `tools/` con
`importlib.util.spec_from_file_location` y un nombre de módulo propio; las funciones `@njit(cache=True)` de esos archivos
guardan el índice del caché en `tools/__pycache__` con el nombre de módulo con que se compilaron. Si el mismo archivo se
cargó antes con otro nombre (otra prueba, o un script corrido a mano), numba intenta reabrir el índice viejo y falla con
`ModuleNotFoundError: No module named '<dynamic>'`. Con un directorio de caché nuevo por sesión de pytest el resultado no
depende de lo que haya quedado en el árbol de trabajo. Tiene que fijarse ANTES de que se importe numba.
"""
import os
import tempfile

os.environ.setdefault("NUMBA_CACHE_DIR", tempfile.mkdtemp(prefix="edgelab_numba_cache_"))

import sys

try:                                                   # el autopilot (Debian) usa fcntl; en Windows se emula con msvcrt (bloqueo real)
    import fcntl  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    import _fcntl_windows
    sys.modules["fcntl"] = _fcntl_windows

import pytest

_SOLO_POSIX = ("research_ops",)                        # O_NOFOLLOW, descriptores de directorio, symlinks, mkfifo: diseño para el Debian


def pytest_collection_modifyitems(config, items):
    """En Windows se saltean las pruebas de módulos que exigen POSIX por diseño (fallan cerrado a propósito);
    corren en el CI de Ubuntu (.github/workflows/ci.yml y research-ops.yml). No se debilita la protección."""
    if os.name == "posix":
        return
    marca = pytest.mark.skip(reason="requiere POSIX por diseño (corre en el CI de Ubuntu y en el Debian)")
    for it in items:
        if any(f"{os.sep}{d}{os.sep}" in str(it.fspath) for d in _SOLO_POSIX):
            it.add_marker(marca)
