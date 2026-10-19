"""Etapa 0 de VTD-DIR: validación target-free del detector de régimen (edgelab/regimes/state.py).
Para cada N: (1) ocupación de estados real vs nulo; (2) persistencia P(estado en t+N | estado en t) con ventanas
contiguas no superpuestas, real vs nulo; (3) previsibilidad: E en [t, t+N] (siguiente) según estado en t, real vs nulo.
Uso: python tools/regimen_etapa0.py <parquet> <ticks_por_barra> <desde_ns> <hasta_ns>"""
import sys
import json
import dataclasses
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\EdgeLab-gex")
from edgelab.bridge import ticks as T, bars as B  # noqa: E402
from edgelab.regimes import state as S  # noqa: E402

if "MGC" not in T.INSTRUMENT_CATALOG:
    T.INSTRUMENT_CATALOG["MGC"] = T.INSTRUMENT_CATALOG["GC"]
NS = (20, 50, 200)


def session_ends(end):
    from edgelab.bridge.sessions import session_end_ns
    um, inv = np.unique(np.asarray(end, np.int64) // 60_000_000_000, return_inverse=True)
    return np.array([session_end_ns(int(x) * 60_000_000_000 + 1) for x in um], dtype=np.int64)[inv]


def evaluate(close, send, N, q33, q67):
    E = S.efficiency(close, send, N)
    st = S.classify(E, q33, q67)
    n = len(close)
    t = np.arange(N, n - N, N)                       # ventanas contiguas no superpuestas
    Ef = E[np.minimum(t + N, n - 1)]                 # eficiencia de la ventana siguiente [t, t+N]
    ok = np.isfinite(st[t]) & np.isfinite(st[np.minimum(t + N, n - 1)]) & np.isfinite(Ef)
    s0, s1, ef = st[t][ok], st[np.minimum(t + N, n - 1)][ok], Ef[ok]
    occ = {k: float(np.mean(st[np.isfinite(st)] == v)) for k, v in (("rango", -1), ("neutro", 0), ("tendencia", 1))}
    pers = {k: float(np.mean(s1[s0 == v] == v)) if (s0 == v).any() else None for k, v in (("rango", -1), ("neutro", 0), ("tendencia", 1))}
    nxt = {k: float(np.mean(ef[s0 == v])) if (s0 == v).any() else None for k, v in (("rango", -1), ("neutro", 0), ("tendencia", 1))}
    return dict(ocupacion=occ, persistencia=pers, E_siguiente=nxt, n_ventanas=int(ok.sum()))


def main(pq, Nt, a, z):
    tk = T.load_canonical_parquet(pq, start_utc_ns=a, end_utc_ns=z)
    ct = pd.to_datetime(tk.ts_ns, utc=True).tz_convert("America/Chicago")
    keep = np.asarray(~(((ct.hour * 60 + ct.minute) >= 960) & ((ct.hour * 60 + ct.minute) < 1020)))
    tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None)
                                    for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")})
    bars = B.build_tick_bars(tk, Nt)
    close = np.asarray(bars.close_t, float)
    send = session_ends(bars.end_ns)
    rng = np.random.default_rng(20261006)
    out = dict(contrato=tk.contract, ticks_por_barra=Nt, barras=len(close))
    for N in NS:
        q33, q67 = S.null_thresholds(close, send, N, rng)
        real = evaluate(close, send, N, q33, q67)
        nul = evaluate(S.null_close(close, send, rng), send, N, q33, q67)
        out["N%d" % N] = dict(umbrales_nulo=[q33, q67], real=real, nulo=nul)
        print("N", N, "umbrales", round(q33, 3), round(q67, 3))
        for k in ("ocupacion", "persistencia", "E_siguiente"):
            print("  ", k, "real", {a: (round(b, 3) if b is not None else None) for a, b in real[k].items()},
                  "| nulo", {a: (round(b, 3) if b is not None else None) for a, b in nul[k].items()})
    return out


if __name__ == "__main__":
    res = main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    print(json.dumps(res)[:200])
