"""Cruce ES×NQ CAUSAL (cierre honesto de la pregunta intermercado de EXP-042).

Pregunta: ¿el "aval macro" del ES (lado del VWAP de sesion RTH, evaluado con el
minuto CERRADO m-1) condiciona el resultado de los trades del NQ?

Metodo: sobre los trades de Noise Area NQ (la unica estrategia causal con
entradas intradia disponibles), split acuerdo vs desacuerdo:
  acuerdo = sign(ES_close[d, m-1] - ES_vwap[d, m-1]) == direccion del trade NQ
Null: permutacion de la etiqueta acuerdo/desacuerdo entre trades del MISMO mes
(10.000 perms) -> p-value de la diferencia de medias.

NOTA pre-registrada: si la estrategia base NQ esta muerta, este resultado es
DIAGNOSTICO (¿hay informacion condicional?) — no resucita nada por si solo.

Ejecutar:  python -m strategies.cross_check
"""
import sys
import numpy as np
import pandas as pd

from edgelab.config import ES_M1
from edgelab.sessions import rth_matrices
from strategies.noise_area import run as run_noise_area

RTH_MIN = 390


def es_vwap_state():
    """Matrices ES: close y VWAP de sesion por (dia ET, minuto RTH)."""
    df = pd.read_parquet(ES_M1)
    m = rth_matrices(df)
    O, H, L, C, V = m["O"], m["H"], m["L"], m["C"], m["V"]
    hlc3 = (H + L + C) / 3.0
    pv = np.where(np.isnan(hlc3 * V), 0.0, hlc3 * V)
    vv = np.where(np.isnan(V), 0.0, V)
    cum_pv = np.cumsum(pv, axis=1)
    cum_v = np.cumsum(vv, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        vwap = np.where(cum_v > 0, cum_pv / cum_v, np.nan)
    return m["days"], C, vwap


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Corriendo Noise Area NQ (base para el cruce)...")
    nq = run_noise_area("NQ", n_perm=500)

    es_days, es_C, es_vwap = es_vwap_state()
    es_day_pos = pd.Series(np.arange(len(es_days)), index=es_days)

    td, tdir, tpnl, tem = nq["day"], nq["dir"], nq["pnl"], nq["entry_m"]
    nq_days = nq["days"]

    agree = np.full(len(tpnl), -1, np.int8)   # 1 acuerdo, 0 desacuerdo, -1 sin dato
    for k in range(len(tpnl)):
        day = nq_days[td[k]]
        if day not in es_day_pos.index:
            continue
        di = es_day_pos.loc[day]
        m = tem[k] - 1                        # minuto CERRADO previo a la entrada
        if m < 0 or m >= RTH_MIN or np.isnan(es_C[di, m]) or np.isnan(es_vwap[di, m]):
            continue
        side = 1 if es_C[di, m] > es_vwap[di, m] else -1
        agree[k] = 1 if side == tdir[k] else 0

    ok = agree >= 0
    x = tpnl[ok]; a = agree[ok].astype(bool)
    tms = nq["times"][ok]
    print(f"\ntrades NQ con estado ES disponible: {ok.sum()}/{len(tpnl)}")
    print(f"ACUERDO   : n={a.sum():4d}  exp={x[a].mean():+.2f}t")
    print(f"DESACUERDO: n={(~a).sum():4d}  exp={x[~a].mean():+.2f}t")
    diff = x[a].mean() - x[~a].mean()
    print(f"diferencia acuerdo-desacuerdo: {diff:+.2f}t")

    # null: permutar etiquetas dentro del mismo mes
    months = pd.to_datetime(tms, unit="ms").to_period("M")
    rng = np.random.RandomState(7)
    n_perm = 10000
    cnt = 0
    codes = months.factorize()[0] if hasattr(months, "factorize") else pd.factorize(months)[0]
    codes = pd.factorize(months)[0]
    for _ in range(n_perm):
        ap = a.copy()
        for g in np.unique(codes):
            mask = codes == g
            ap[mask] = rng.permutation(ap[mask])
        if ap.sum() and (~ap).sum():
            d = x[ap].mean() - x[~ap].mean()
            if abs(d) >= abs(diff):
                cnt += 1
    p = (1 + cnt) / (1 + n_perm)
    print(f"p (permutacion por mes, 2 colas): {p:.4f}")
    verdict = "SIN informacion condicional" if p > 0.05 else "informacion condicional DETECTADA (diagnostico)"
    print(f"VEREDICTO cruce ES->NQ: {verdict}")


if __name__ == "__main__":
    main()
