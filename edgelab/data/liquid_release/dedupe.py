"""Detección de bloques duplicados con corrimiento horario dentro de una misma fuente (causa raíz de la cuarentena NQ_09-26).

Evidencia (2026-10-13): en el export nativo `NQ 09-26.Last.txt`, el bloque de la hora 18 UTC del 17-jun (86.342 trades) aparece
copiado fila por fila con +3 h exactas en la hora 21 UTC (pausa CME). Las huellas por hora (n, volumen y sumas exactas de
sello-dentro-de-la-hora, precio, bid y ask) de un bloque copiado con corrimiento entero de horas son IDÉNTICAS a las del
original, y un mercado real nunca repite una hora entera: por eso esta coincidencia exacta es evidencia de copia.

Regla de adjudicación (conservadora): de los dos bloques idénticos, la copia es el que cae fuera del horario regular; si
ambos caen dentro, es ambiguo y no se descarta nada (la sesión se marca para adjudicar con otra fuente).
"""
from __future__ import annotations

import pandas as pd

FP = ["n", "vol", "fp_ts", "fp_px", "fp_bid", "fp_ask"]


def find_shifted_duplicates(bins: pd.DataFrame, *, min_n: int = 20, max_shift_h: int = 24) -> pd.DataFrame:
    """bins: UNA fuente/grupo, con raw_date, raw_hour y las huellas FP. Devuelve pares (original, copia) idénticos."""
    b = bins[bins["n"] >= min_n].copy()
    b["t"] = pd.to_datetime(b["raw_date"].astype(str), format="%Y%m%d") + pd.to_timedelta(b["raw_hour"], unit="h")
    b = b.sort_values("t")
    out = []
    for _, g in b.groupby(FP, sort=False):
        if len(g) < 2:
            continue
        rows = g.to_dict("records")
        first = rows[0]
        for later in rows[1:]:
            shift = int((later["t"] - first["t"]).total_seconds() // 3600)
            if 0 < shift <= max_shift_h:
                out.append(dict(orig_date=first["raw_date"], orig_hour=first["raw_hour"], copy_date=later["raw_date"],
                                copy_hour=later["raw_hour"], shift_h=shift, n=int(first["n"])))
    return pd.DataFrame(out, columns=["orig_date", "orig_hour", "copy_date", "copy_hour", "shift_h", "n"])


def adjudicate(dups: pd.DataFrame, in_break: dict) -> pd.DataFrame:
    """in_break: {(raw_date, raw_hour): bool}. Marca cuál bloque es la copia. 'AMBIGUOUS' si ambos son horario regular."""
    rows = []
    for r in dups.itertuples():
        o_out = bool(in_break.get((r.orig_date, r.orig_hour), False))
        c_out = bool(in_break.get((r.copy_date, r.copy_hour), False))
        if c_out and not o_out:
            verdict, drop = "COPY_IS_LATER_OUTSIDE_REGULAR", (r.copy_date, r.copy_hour)
        elif o_out and not c_out:
            verdict, drop = "COPY_IS_EARLIER_OUTSIDE_REGULAR", (r.orig_date, r.orig_hour)
        else:
            verdict, drop = "AMBIGUOUS", None
        rows.append(dict(**r._asdict(), verdict=verdict, drop_date=None if drop is None else drop[0],
                         drop_hour=None if drop is None else drop[1]))
    return pd.DataFrame(rows).drop(columns=["Index"], errors="ignore")
