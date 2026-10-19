"""Barrido de anidacion en delta: `break` vs `continue`, deterministico y versionado.

POR QUE EXISTE. El 2026-08-18 reporte "135 -> 11" en chat y "135 -> 21" en el commit.
El auditor marco la discrepancia (entrada 027) y tenia razon: los dos numeros salen de
mediciones distintas, y la primera estaba MAL.

La causa: el primer script recorria los dos modelos con el MISMO objeto `rng`, en
serie. El segundo modelo consumia el generador donde lo habia dejado el primero, asi
que **cada modelo vio series distintas**. Comparar 135 contra 11 era comparar dos
poblaciones, no dos tratamientos.

Es la misma falla de fondo que el proyecto viene cazando, en version estadistica: un
numero que se reporta sin que su procedencia se derive. Aca la correccion es trivial
--sembrar de nuevo para cada modelo, mismas series para los dos-- pero el numero solo
vale si el barrido esta en el repo y cualquiera lo puede repetir.

    .venv\Scripts\python diag\tasa_senales\barrido_anidacion.py

Target-free: no toca datos reales, no toca outcomes. Series sinteticas.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
RUNNER = REPO / "diag" / "tasa_senales" / "censo_hz2a_superficie.py"
SEMILLA = 20260818
N_SERIES = 400
# ANCLA UNICA. El patron `i = k + 1` / `continue` aparece TRES veces en
# `censar_zona` (cond 1, cond 2 y la rama de separacion). Un `replace` sobre el
# patron pelado convierte las tres en `break` y construye un control que NO es el
# codigo viejo -- error cometido y detectado el 2026-08-18, que produjo un "0
# violaciones" imposible. El ancla incluye el comentario, que si es unico, y main()
# verifica que la sustitucion ocurra exactamente una vez.
ANCLA = """# que vienen despues.
                                i = k + 1
                                continue"""
REEMPLAZO = """# que vienen despues.
                                break"""


def _cargar(texto, nombre, tmp):
    # El runner resuelve REPO desde su propio __file__ para poder importar `edgelab`.
    # Al cargarlo desde otro directorio esa resolucion falla, asi que el path se
    # asegura aca: la copia es del MISMO texto, solo cambia de donde se ejecuta.
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    ruta = tmp / ("%s.py" % nombre)
    ruta.write_text(texto, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def series(n):
    """MISMAS series para los dos modelos: se siembra de nuevo, no se comparte el rng."""
    rng = np.random.default_rng(SEMILLA)
    for _ in range(n):
        d = (np.abs(np.cumsum(rng.integers(-4, 5, 120))) % 90).astype(np.int64)
        yield d, d == 0


def violaciones(mod, censo_mods):
    """Cuenta pares (serie, celda) donde subir delta BAJA el conteo de near-miss."""
    n = 0
    for d, toca in series(N_SERIES):
        c = mod.censar_zona(d, toca, toca.copy())
        for D in mod.D_FAR:
            for R in mod.R_MIN:
                s = [c[(D, dl, R, "trade")][1] for dl in mod.DELTA_NM]
                n += sum(1 for x, y in zip(s, s[1:]) if y < x)
    return n


def main():
    tmp = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    src = RUNNER.read_text(encoding="utf-8")
    assert src.count(ANCLA) == 1, (
        "el ancla del barrido matchea %d veces, tiene que ser exactamente 1 -- si el "
        "runner cambio, este control deja de ser el codigo viejo" % src.count(ANCLA))
    viejo = src.replace(ANCLA, REEMPLAZO, 1)
    assert viejo.count("i = k + 1") == src.count("i = k + 1") - 1, "sustitucion sucia"
    con_fix = _cargar(src, "anid_fix", tmp)
    con_break = _cargar(viejo, "anid_break", tmp)

    a = violaciones(con_break, None)
    b = violaciones(con_fix, None)
    out = dict(semilla=SEMILLA, n_series=N_SERIES,
               violaciones_con_break=a, violaciones_con_fix=b,
               nota="mismas series para los dos modelos; el rng se siembra de nuevo")
    print(json.dumps(out, indent=2))
    print()
    print("con `break`   : %d pares (serie, celda) donde subir delta BAJA el conteo" % a)
    print("con el fix    : %d" % b)
    print()
    print("Las %d residuales NO son un bug: son la segmentacion golosa (P-45)." % b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
