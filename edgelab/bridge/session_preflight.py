# -*- coding: utf-8 -*-
"""Preflight de calendario: fronteras de sesión antes de comparar zonas.

Decisión de Nico del 2026-07-26: *alinear `sessions.py` a NT8, sin tolerancia*, y
**abortar con diagnóstico** si las fronteras difieren — antes de comparar zonas,
no después. Aplica a `aVolCellPOI2`, `HFTZones2` y a todo indicador futuro que
dependa de sesiones.

Por qué antes: un desalineamiento de calendario produce diffs de zona que
*parecen* diffs de geometría. Se gasta el oráculo persiguiendo la zona equivocada.
El preflight convierte ese modo de falla en un mensaje que dice qué sesión y qué
fecha, y frena ahí.

## Lo que se midió (2026-07-26)

Contra el oráculo real `HFTZones2_adaptive_6E_0926_v22.csv`, las **7 fronteras de
sesión de NT8 coinciden exactamente** con las de `sessions.py` (17:00 CT, DST-aware).
El calendario NO está desalineado.

Lo que sí difiere es el **origen del contador**: NT8 numera desde la primera barra
que cargó el chart y Python desde el inicio del parquet. En 6E 09-26 eso da un
offset constante de 4 (NT8 arranca en 2026-06-12, el parquet en 2026-06-08). Un
`session_index` de NT8 **no es** un índice de Python: hay que traducirlo por
trade-date, nunca por ordinal. Ese fue el verdadero origen del FAIL de
`aVolCellPOI2` que se había diagnosticado como "deriva de calendario".

El offset se **declara**, no se absorbe en silencio: si cambia entre corridas es
que el chart cargó otro rango, y eso invalida la comparación igual que un
desalineamiento real.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import sessions as S

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000

# Tolerancia: CERO en la frontera derivada. NT8 estampa sus eventos de sesión con
# el PRIMER TICK de la sesión, que llega unos cientos de ms después de las 17:00
# CT; por eso lo que se compara es la frontera derivada (`session_begin_ns` del
# instante del evento), no el instante crudo. Comparar el crudo exigiría una
# tolerancia — y las tolerancias no se amplían en este proyecto.


class CalendarMismatch(Exception):
    """El calendario de sesiones de NT8 y el de Python no coinciden."""


def _ct(ns: int) -> datetime:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).astimezone(CT)


def python_boundaries(ts_ns_iter):
    """Fronteras de sesión que produce `sessions.py` sobre una serie de ts.

    Devuelve [(trade_date, begin_ns)] ordenado y sin repetidos.
    """
    out, vistos = [], set()
    for ns in ts_ns_iter:
        ns = int(ns)
        k = S.session_key(ns)
        if k in vistos:
            continue
        vistos.add(k)
        out.append((k, S.session_begin_ns(ns)))
    out.sort(key=lambda x: x[1])
    return out


def nt8_boundaries(event_ts_ns_iter):
    """Fronteras que declara NT8, derivadas de sus eventos de inicio de sesión.

    Se le pasan los ts de los eventos que NT8 emite **al abrir** cada sesión
    (`CALIBRATION` / `CALIBRATION_PENDING` en HFTZones2). Cada uno se lleva a la
    frontera que lo contiene, así el jitter del primer tick no entra en la
    comparación.
    """
    out, vistos = [], set()
    for ns in event_ts_ns_iter:
        ns = int(ns)
        b = S.session_begin_ns(ns)
        if b in vistos:
            continue
        vistos.add(b)
        out.append((S.session_key(ns), b))
    out.sort(key=lambda x: x[1])
    return out


def preflight(nt8_bounds, py_bounds, *, nt8_index_base=None, strict=True):
    """Compara los dos calendarios sobre el rango COMÚN y reporta.

    Se restringe al rango que ambos cubren: que el parquet tenga más historia que
    el chart no es un desalineamiento, es otro rango de carga. Lo que sí lo es:
    una frontera dentro del rango común que uno tiene y el otro no.

    `nt8_index_base` — el trade-date que NT8 numera como session_index 0, si se
    conoce. Se reporta el offset contra la numeración de Python.

    Devuelve un dict-reporte. Con `strict=True` levanta `CalendarMismatch` ante
    la primera discrepancia, con el detalle de qué sesión y qué fecha.
    """
    if not nt8_bounds or not py_bounds:
        raise CalendarMismatch(
            "preflight sin datos: nt8=%d fronteras, python=%d fronteras. "
            "Sin fronteras no se puede afirmar paridad — no se sigue."
            % (len(nt8_bounds), len(py_bounds)))

    lo = max(nt8_bounds[0][1], py_bounds[0][1])
    hi = min(nt8_bounds[-1][1], py_bounds[-1][1])
    n_en_rango = [(k, b) for k, b in nt8_bounds if lo <= b <= hi]
    p_en_rango = [(k, b) for k, b in py_bounds if lo <= b <= hi]

    diffs = []
    sn, sp = {b for _, b in n_en_rango}, {b for _, b in p_en_rango}
    for b in sorted(sn - sp):
        diffs.append(dict(tipo="SOLO_NT8", trade_date=S.session_key(b),
                          inicio_ct=_ct(b).strftime("%a %Y-%m-%d %H:%M:%S %Z")))
    for b in sorted(sp - sn):
        diffs.append(dict(tipo="SOLO_PYTHON", trade_date=S.session_key(b),
                          inicio_ct=_ct(b).strftime("%a %Y-%m-%d %H:%M:%S %Z")))

    # El trade-date tiene que coincidir para la MISMA frontera; si no, alguno de
    # los dos lados está etiquetando la sesión con el día equivocado.
    etiq = {b: k for k, b in n_en_rango}
    for k, b in p_en_rango:
        if b in etiq and etiq[b] != k:
            diffs.append(dict(tipo="ETIQUETA_DISTINTA", trade_date_python=k,
                              trade_date_nt8=etiq[b],
                              inicio_ct=_ct(b).strftime("%a %Y-%m-%d %H:%M:%S %Z")))

    offset = None
    if nt8_index_base is not None:
        todas = [k for k, _ in py_bounds]
        if nt8_index_base in todas:
            offset = todas.index(nt8_index_base)
        else:
            diffs.append(dict(tipo="BASE_NT8_FUERA_DEL_PARQUET",
                              trade_date=nt8_index_base))

    rep = dict(
        ok=not diffs,
        rango_comun=(_ct(lo).strftime("%Y-%m-%d %H:%M"),
                     _ct(hi).strftime("%Y-%m-%d %H:%M")),
        n_sesiones_nt8=len(n_en_rango),
        n_sesiones_python=len(p_en_rango),
        offset_de_indice=offset,
        diffs=diffs,
    )
    if diffs and strict:
        raise CalendarMismatch(formatear(rep))
    return rep


def formatear(rep) -> str:
    L = ["PREFLIGHT DE CALENDARIO — %s" % ("OK" if rep["ok"] else "ABORTA"),
         "  rango comun: %s -> %s" % rep["rango_comun"],
         "  sesiones en rango: NT8=%d  Python=%d"
         % (rep["n_sesiones_nt8"], rep["n_sesiones_python"])]
    if rep["offset_de_indice"] is not None:
        L.append("  offset de indice: %d  (session_index de NT8 + %d = indice de "
                 "Python; NUNCA comparar ordinales, traducir por trade-date)"
                 % (rep["offset_de_indice"], rep["offset_de_indice"]))
    if rep["diffs"]:
        L.append("  DISCREPANCIAS (%d):" % len(rep["diffs"]))
        for d in rep["diffs"]:
            L.append("    - " + ", ".join("%s=%s" % kv for kv in d.items()))
        L.append("  No se comparan zonas: un calendario desalineado produce diffs "
                 "de zona que parecen diffs de geometria.")
    return "\n".join(L)
