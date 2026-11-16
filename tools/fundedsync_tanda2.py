#!/usr/bin/env python3
"""FundedSync tanda 2 (pre-registro docs/research/fundedsyncstack_20261115/PREREGISTRO_TANDA2.md).

  python tools/fundedsync_tanda2.py salidas  <carpeta M1>   # L1: salida al cierre vs técnica (S, A20, W, N) en S&P, Dow, Russell (+ Nasdaq aparte)
  python tools/fundedsync_tanda2.py tendencia <carpeta M1>  # L3 + L4: días de tendencia (E0) y volatilidad rugosa / Hurst
  python tools/fundedsync_tanda2.py knn <carpeta M1>        # L4bis: capa KNN sombra sobre PREAPERTURA-NQ y CVGAP-ES-C
  python tools/fundedsync_tanda2.py catastrofe <carpeta M1> # L2: Z y R con stop de catástrofe 0,5 × ATR20 (desarrollo, descriptivo)
<carpeta M1>: los CSV de `edgelab-sqx-m1` (NQ_M1_dukas.csv, SP_M1_dukas.csv, DJ_M1_dukas.csv, USSC2000IDXUSD.csv).
Salida: docs/research/fundedsyncstack_20261115/tanda2/*.json. Reusa m1_intradia.leer_m1 y el paquete fundedsyncstack.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import m1_intradia as M  # noqa: E402

OUT = ROOT / "docs/research/fundedsyncstack_20261115/tanda2"
INST = {"NQ_M1_dukas": ("NQ", 1.5455), "SP_M1_dukas": ("ES", 0.8877), "DJ_M1_dukas": ("YM", 5.052), "USSC2000IDXUSD": ("RTY", 0.4436)}
PRUEBA = ("SP_M1_dukas", "DJ_M1_dukas", "USSC2000IDXUSD")
VARIANTES = {"S": dict(exit_on_st_flip=False, use_hard_stop=True), "A20": dict(exit_on_st_flip=False), "W": dict(exit_on_vwap_cross=False),
             "N": dict(use_failed_breakout_exit=False)}
TRAMOS = (("2012-2019", "2012-01-01", "2019-12-31"), ("2020-2023", "2020-01-01", "2023-12-31"), ("2024-2026", "2024-01-01", "2026-09-29"))


def leer(carpeta, sim):
    D = M.leer_m1(Path(carpeta) / f"{sim}.csv"); return D[(D.index >= "2012-01-20") & (D.index < "2026-09-30")]


def a_utc(D):
    t = D.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC"); ok = ~t.isna()
    return pd.DataFrame(dict(t=t[ok], o=D.o.values[ok], h=D.h.values[ok], l=D.l.values[ok], c=D.c.values[ok], v=D.v.values[ok]))


def diario(D):
    m = D.index.hour * 60 + D.index.minute; R = D[(m >= 570) & (m < 960)]; d = R.index.normalize()
    day = pd.DataFrame(dict(o=R.o.groupby(d).first(), h=R.h.groupby(d).max(), l=R.l.groupby(d).min(), c=R.c.groupby(d).last()))
    day["atr20"] = (day.h - day.l).rolling(20).mean().shift(1); return day


def _ops(x, fr):
    if not len(x): return pd.DataFrame(columns=["dia", "neto"])
    tt = pd.to_datetime(x.entry_time_utc, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return pd.DataFrame(dict(dia=tt.dt.normalize(), neto=pd.to_numeric(x.pnl_pts, errors="coerce").values - fr,
                             mae=pd.to_numeric(x.get("mae_usd", np.nan), errors="coerce").values, salida=x.exit_name.astype(str).str.replace(r"_\d+$", "", regex=True).values))


def _boot_media(v, seed=7, B=10000):
    v = np.asarray(v, float); i = np.random.default_rng(seed).integers(0, len(v), (B, len(v))); m = v[i].mean(1)
    return float((1 + (m <= 0).sum()) / (B + 1))


def _bh(ps, q=0.10):
    ps = np.asarray(ps); o = np.argsort(ps); k = 0
    for j, idx in enumerate(o, 1):
        if ps[idx] <= q * j / len(ps): k = j
    nom = np.zeros(len(ps), bool); nom[o[:k]] = True; return nom.tolist()


def salidas(carpeta):
    from edgelab.research import fundedsyncstack as F
    res, dif = {}, {k: [] for k in VARIANTES}
    for sim, (fut, fr) in INST.items():
        D = leer(carpeta, sim); day = diario(D); ms = F.build_multi_series(F.load_m1_data(a_utc(D), end="2026-10-01"), tz_input="UTC"); res[sim] = {}
        for k, kw in VARIANTES.items():
            a = _ops(F.correr_modulo(k, ms), fr); b = _ops(F.correr_modulo(k, ms, **kw), fr)
            sa, sb = a.groupby("dia").neto.sum(), b.groupby("dia").neto.sum(); dias = sa.index.union(sb.index)
            d = (sb.reindex(dias, fill_value=0) - sa.reindex(dias, fill_value=0)) / day.atr20.reindex(dias)
            d = d[np.isfinite(d)]
            if sim in PRUEBA: dif[k].append(d.values)
            res[sim][k] = dict(original=dict(n=len(a), neto=float(a.neto.mean()) if len(a) else None, peor_dia=float(sa.min()) if len(sa) else None),
                               variante=dict(n=len(b), neto=float(b.neto.mean()) if len(b) else None, peor_dia=float(sb.min()) if len(sb) else None),
                               dif_dia_atr=float(d.mean()) if len(d) else None, p_dif=_boot_media(d.values) if len(d) > 5 else None,
                               por_tramo={n: dict(original=float(a[(a.dia >= x) & (a.dia <= y)].neto.sum()), variante=float(b[(b.dia >= x) & (b.dia <= y)].neto.sum())) for n, x, y in TRAMOS},
                               salidas_variante=b.salida.value_counts().to_dict())
            print(sim, k, "orig", round(res[sim][k]["original"]["neto"] or 0, 2), "var", round(res[sim][k]["variante"]["neto"] or 0, 2), "p", res[sim][k]["p_dif"], flush=True)
    pooled = {k: dict(dif_dia_atr=float(np.concatenate(v).mean()), p=_boot_media(np.concatenate(v)), mejor_en=sum(res[s][k]["dif_dia_atr"] > 0 for s in PRUEBA)) for k, v in dif.items()}
    bh = _bh([pooled[k]["p"] for k in VARIANTES])
    for k, b in zip(VARIANTES, bh): pooled[k].update(bh=b, confirmada=bool(b and pooled[k]["mejor_en"] >= 2))
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "L1_SALIDAS.json").write_text(json.dumps(dict(por_indice=res, prueba_SP_DJ_RTY=pooled), indent=1, default=float))
    print(json.dumps(pooled, indent=1))


if __name__ == "__main__":
    globals()[sys.argv[1]](sys.argv[2])
