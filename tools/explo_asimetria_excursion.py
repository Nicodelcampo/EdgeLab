"""Exploración (descriptiva, sin decisión): asimetría de la excursión posterior a la creación de zonas.
Hipótesis de Nico (2026-10-06): en las X velas posteriores a la zona, el precio se extiende mucho hacia UN lado y apenas
visita el otro. Métrica sin escala (no depende de ventanas previas): U = máx(high) − close[b], D = close[b] − mín(low)
en [b+1, b+H]; cociente = max(U, D) / max(min(U, D), 1 tick). Eventos (AVCL AT/OFF, VTD) contra controles de la misma
franja de 30 min (reponderados a la distribución horaria de los eventos), misma sesión.
Uso: python tools/explo_asimetria_excursion.py <parquet> <ticks_por_barra> [<desde_ns> <hasta_ns>]"""
import sys
import dataclasses
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\EdgeLab-gex")
from edgelab.bridge import ticks as T, bars as B  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi_fast import run_full_fast  # noqa: E402
from edgelab.bridge.indicators.volticksdef import run as vtd_run  # noqa: E402
from edgelab.bridge.sessions import session_end_ns  # noqa: E402
import dataclasses as _dc  # noqa: E402
if "MGC" not in T.INSTRUMENT_CATALOG:              # sólo para esta exploración: MGC = GC con tick 0,10
    T.INSTRUMENT_CATALOG["MGC"] = T.INSTRUMENT_CATALOG["GC"]

HS = (10, 20, 50, 100)
PARAMS = dict(window_bars=10, median_multiplier=2.0, max_gap_ticks=1, min_cluster_ticks=2, use_session_buckets=True,
              time_bucket_minutes=30, lookback_sessions=20, detection_percentile=95.0, min_samples_per_bucket=20,
              enable_predictive_filter=False, use_topk_hot_cells=False, invalidation_mode="None", max_age_bars=500)


def excursions(hi, lo, cl, send, b, H):
    n = len(cl)
    ok = (b + H < n)
    b = b[ok]
    idx = b[:, None] + np.arange(1, H + 1)[None, :]
    same = (send[idx[:, -1]] == send[b])
    U = hi[idx].max(1) - cl[b]
    D = cl[b] - lo[idx].min(1)
    return b[same], U[same].astype(float), D[same].astype(float)


def stats(U, D, w=None):
    U = np.maximum(U, 0); D = np.maximum(D, 0)
    big, small = np.maximum(U, D), np.minimum(U, D)
    r = big / np.maximum(small, 1.0)
    A = np.abs(U - D) / np.maximum(U + D, 1.0)
    w = np.ones(len(U)) if w is None else w
    w = w / w.sum()
    return dict(n=len(U), A_media=float((A * w).sum()), p_ratio3=float(((r >= 3) * w).sum()), p_ratio5=float(((r >= 5) * w).sum()),
                big_media=float((big * w).sum()), small_media=float((small * w).sum()), total_media=float(((U + D) * w).sum()))


def main(pq, N, a=None, z=None):
    tk = T.load_canonical_parquet(pq, start_utc_ns=a, end_utc_ns=z)
    ct = pd.to_datetime(tk.ts_ns, utc=True).tz_convert("America/Chicago")
    keep = np.asarray(~(((ct.hour * 60 + ct.minute) >= 960) & ((ct.hour * 60 + ct.minute) < 1020)))
    tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None)
                                    for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")})
    bars = B.build_tick_bars(tk, N)
    fp = B.build_total_footprint_csr_nt8(tk, bars)
    r = run_full_fast(tk, bars, fp, PARAMS)
    v = vtd_run(bars)
    hi = np.asarray(bars.high_t, np.int64); lo = np.asarray(bars.low_t, np.int64); cl = np.asarray(bars.close_t, np.int64)
    end = np.asarray(bars.end_ns, np.int64)
    um, inv = np.unique(end // 60_000_000_000, return_inverse=True)
    send = np.array([session_end_ns(int(x) * 60_000_000_000 + 1) for x in um], dtype=np.int64)[inv]
    clock = np.asarray(pd.to_datetime(end, utc=True).tz_convert("America/Chicago").hour * 2
                       + pd.to_datetime(end, utc=True).tz_convert("America/Chicago").minute // 30)
    zn = pd.DataFrame(r["zones"]) if r["zones"] else pd.DataFrame(columns=["kind", "created_bar"])
    evs = {"AVCL AT": zn[zn.kind == "AT_PRICE"].created_bar.to_numpy().astype(np.int64),
           "AVCL OFF": zn[zn.kind == "OFF_PRICE"].created_bar.to_numpy().astype(np.int64),
           "VTD": np.array([x["bar"] for x in v["zones"]], dtype=np.int64)}
    allev = np.unique(np.concatenate(list(evs.values())))
    n = len(cl)
    cand = np.arange(300, n - 101, 7)
    j = np.searchsorted(allev, cand)
    dist = np.minimum(np.abs(cand - allev[np.clip(j, 0, len(allev) - 1)]), np.abs(cand - allev[np.clip(j - 1, 0, len(allev) - 1)]))
    ctrl = cand[dist > 100]
    print("instrumento", tk.contract, "barras", n, "N", N, {k: len(x) for k, x in evs.items()}, "controles", len(ctrl))
    rows = []
    for H in HS:
        cb, cU, cD = excursions(hi, lo, cl, send, ctrl, H)
        cclk = clock[cb]
        for name, eb in evs.items():
            b, U, D = excursions(hi, lo, cl, send, eb, H)
            # reponderar controles a la distribución horaria de los eventos
            pe = pd.Series(clock[b]).value_counts(normalize=True)
            pc = pd.Series(cclk).value_counts(normalize=True)
            w = pd.Series(cclk).map(pe / pc).fillna(0).to_numpy()
            se, sc = stats(U, D), stats(cU, cD, w)
            rows.append(dict(H=H, evento=name, n_ev=se["n"], A_ev=se["A_media"], A_ctrl=sc["A_media"],
                             p3_ev=se["p_ratio3"], p3_ctrl=sc["p_ratio3"], p5_ev=se["p_ratio5"], p5_ctrl=sc["p_ratio5"],
                             big_ev=se["big_media"], big_ctrl=sc["big_media"], small_ev=se["small_media"], small_ctrl=sc["small_media"]))
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))
    return out


if __name__ == "__main__":
    pq, N = sys.argv[1], int(sys.argv[2])
    a = int(sys.argv[3]) if len(sys.argv) > 3 else None
    z = int(sys.argv[4]) if len(sys.argv) > 4 else None
    main(pq, N, a, z)
