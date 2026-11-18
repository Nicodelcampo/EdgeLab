#!/usr/bin/env python3
"""FundedSync: mecanismos, contextos y combinaciones (pre-registro docs/research/fundedsyncstack_20261115/PREREGISTRO_MECANISMOS.md).

  python tools/fundedsync_mecanismos.py <NQ_M1_dukas-M1-.csv>    # -> docs/research/fundedsyncstack_20261115/mecanismos/MECANISMOS.json
Reusa m1_intradia.leer_m1 (M1 de Dukascopy a hora de NY) y las operaciones de la cadena (cadena/FUNDEDSYNC_OPS.csv.gz).
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import m1_intradia as M  # noqa: E402

DIR = ROOT / "docs/research/fundedsyncstack_20261115"; OUT = DIR / "mecanismos"; FR = 1.5455
A, B = ("2020-01-01", "2023-12-31"), ("2024-01-01", "2026-09-29")
NB = 2000


def _tercil(x: pd.Series) -> pd.Series:
    r = x.rolling(251, min_periods=120).apply(lambda a: (a[:-1] < a[-1]).mean() if np.isfinite(a[-1]) else np.nan, raw=True)
    return pd.cut(r, [-0.01, 1 / 3, 2 / 3, 1.01], labels=["bajo", "medio", "alto"]).astype(object)


def contexto(path) -> pd.DataFrame:
    """Variables diarias causales (conocidas antes de la entrada del día)."""
    D = path if isinstance(path, pd.DataFrame) else M.leer_m1(path); D = D[D.index >= "2010-01-01"]          # DataFrame: kernel de Franklin
    m = D.index.hour * 60 + D.index.minute
    R = D[(m >= 570) & (m < 960)]; d = R.index.normalize()
    day = pd.DataFrame(dict(o=R.o.groupby(d).first(), h=R.h.groupby(d).max(), l=R.l.groupby(d).min(), c=R.c.groupby(d).last()))
    O15 = D[(m >= 570) & (m < 585)]; d15 = O15.index.normalize()
    day["orb15"] = (O15.h.groupby(d15).max() - O15.l.groupby(d15).min()).reindex(day.index)
    rango = day.h - day.l; atr = rango.rolling(20).mean().shift(1)
    ses = (D.index + pd.Timedelta(hours=6)).normalize(); noc = (m >= 18 * 60) | (m < 570)
    N = D[noc]; sn = ses[noc]
    noche = ((N.h.groupby(sn).max() - N.l.groupby(sn).min()).reindex(day.index)) / day.c.shift(1)
    V = pd.DataFrame(index=day.index)
    V["vol20"] = _tercil(rango.rolling(20).mean().shift(1))
    V["tend60"] = np.where(day.c.shift(1) > day.c.shift(61), "sube", "baja")
    V["noche"] = _tercil(noche)
    V["gap"] = _tercil((day.o - day.c.shift(1)).abs() / atr)
    V["orb15"] = _tercil(day.orb15 / atr)
    V["dia_tendencia"] = ((day.c - day.o).abs() >= 0.8 * rango).map({True: "si", False: "no"})   # EX POST: sólo descriptivo
    return V


def _hora(t):
    h = pd.to_datetime(t, unit="s", utc=True).dt.tz_convert("America/New_York"); mm = h.dt.hour * 60 + h.dt.minute
    return pd.Series(np.select([(mm >= 570) & (mm < 630), (mm >= 630) & (mm < 720), (mm >= 720) & (mm < 840), (mm >= 840) & (mm < 975)],
                               ["09:30-10:30", "10:30-12:00", "12:00-14:00", "14:00-16:15"], "fuera_rueda"), index=t.index), mm


def operaciones(V) -> pd.DataFrame:
    o = pd.read_csv(DIR / "cadena/FUNDEDSYNC_OPS.csv.gz", parse_dates=["dia"])
    o["salida"] = o.salida.astype(str).str.replace(r"_\d+$", "", regex=True)       # C_STOP_1032 -> C_STOP
    o["hora"], mm = _hora(o.t); o["lado"] = np.where(o.side > 0, "L", "S"); o["dow"] = o.dia.dt.day_name().str[:3]
    o = o.join(V, on="dia")
    o.loc[mm.values < 585, "orb15"] = np.nan                                   # ORB15 sólo se conoce desde las 09:45
    return o


EJES = ("lado", "hora", "dow", "vol20", "tend60", "noche", "gap", "orb15")
# K48 (2026-11-18): hora (desde las 18:00 NY de la sesión) en que se conoce cada eje. `noche` (18:00→09:30), `gap` (apertura 09:30) y
# `orb15` (09:30–09:45) NO son causales para módulos que entran antes (A1, A20, E, S y O operan de noche; Z, W y N antes de las 09:45).
# El atlas del 2026-11-15 los usó con todos: las «elegidas» en A de A1/A20/E por noche/gap/orb15 eran esa fuga (ninguna replicó en B).
CONOCIDA_EJE = {"lado": 0.0, "hora": 0.0, "dow": 0.0, "vol20": 0.0, "tend60": 0.0, "noche": 15.5, "gap": 15.5, "orb15": 15.75}


def _boot(x_cel, d_cel, x_res, d_res, seed):
    """Diferencia de medias (celda − resto) y media de la celda, con bootstrap por sesión."""
    dias = np.unique(np.r_[d_cel, d_res]); pos = {d: i for i, d in enumerate(dias)}
    sc, nc, sr, nr = (np.zeros(len(dias)) for _ in range(4))
    np.add.at(sc, [pos[d] for d in d_cel], x_cel); np.add.at(nc, [pos[d] for d in d_cel], 1)
    np.add.at(sr, [pos[d] for d in d_res], x_res); np.add.at(nr, [pos[d] for d in d_res], 1)
    i = np.random.default_rng(seed).integers(0, len(dias), (NB, len(dias)))
    mc = sc[i].sum(1) / np.maximum(nc[i].sum(1), 1); mr = sr[i].sum(1) / np.maximum(nr[i].sum(1), 1); dif = mc - mr
    d0 = x_cel.mean() - x_res.mean()
    return dict(dif=float(d0), t_dif=float(d0 / dif.std(ddof=1)) if dif.std(ddof=1) > 0 else 0.0, p_dif=float((1 + (dif <= 0).sum()) / (NB + 1)),
                p_media=float((1 + (mc <= 0).sum()) / (NB + 1)))


def _bh(ps, q=0.10):
    ps = np.asarray(ps); o = np.argsort(ps); k = 0
    for j, idx in enumerate(o, 1):
        if ps[idx] <= q * j / len(ps): k = j
    nom = np.zeros(len(ps), bool); nom[o[:k]] = True; return nom


def celdas(o):
    a = o[(o.dia >= A[0]) & (o.dia <= A[1])]; b = o[(o.dia >= B[0]) & (o.dia <= B[1])]; filas = []
    from edgelab.research.papel_regimen import horas_de_sesion
    for k, g in a.groupby("modulo"):
        gb = b[b.modulo == k]; h = horas_de_sesion(pd.to_numeric(g.t, errors="coerce").to_numpy(float))
        for eje in EJES:
            if (h < CONOCIDA_EJE[eje]).any():
                filas.append(dict(modulo=k, eje=eje, nivel="NO_CAUSAL", elegida=False)); continue
            for nivel in sorted(g[eje].dropna().unique()):
                c = g[g[eje] == nivel]; r = g[g[eje] != nivel]
                fila = dict(modulo=k, eje=eje, nivel=str(nivel), nA=int(len(c)), netoA=float(c.neto.mean()) if len(c) else None, netoA_modulo=float(g.neto.mean()))
                if len(c) >= 30 and len(r) >= 10:
                    s = _boot(c.neto.values, c.dia.values, r.neto.values, r.dia.values, hash((k, eje, str(nivel))) % 2**32)
                    fila.update({f"{x}A": y for x, y in s.items()}); fila["elegida"] = bool(fila["netoA"] > 0 and s["t_dif"] >= 2)
                else: fila["elegida"] = False
                if fila["elegida"]:
                    cb = gb[gb[eje] == nivel]; rb = gb[gb[eje] != nivel]
                    fila.update(nB=int(len(cb)), netoB=float(cb.neto.mean()) if len(cb) else None, netoB_modulo=float(gb.neto.mean()) if len(gb) else None)
                    if len(cb) >= 5 and len(rb) >= 5:
                        fila.update({f"{x}B": y for x, y in _boot(cb.neto.values, cb.dia.values, rb.neto.values, rb.dia.values, 7).items()})
                filas.append(fila)
    sel = [f for f in filas if f["elegida"] and "p_difB" in f]
    if sel:
        n1, n2 = _bh([f["p_difB"] for f in sel]), _bh([f["p_mediaB"] for f in sel])
        for f, x, y in zip(sel, n1, n2): f.update(bh_dif=bool(x), bh_media=bool(y), pasa=bool(x and y))
    return filas


def descriptivo(o):
    d = o[o.dia >= A[0]]; out = {}
    for k, g in d.groupby("modulo"):
        out[k] = dict(n=int(len(g)), neto=float(g.neto.mean()), bruto=float(g.neto.mean() + FR), friccion_sobre_bruto=float(FR / (g.neto.mean() + FR)) if g.neto.mean() + FR > 0 else None,
                      por_salida={s: dict(n=int(len(x)), neto=round(float(x.neto.mean()), 2)) for s, x in g.groupby("salida")},
                      por_lado={s: dict(n=int(len(x)), neto=round(float(x.neto.mean()), 2)) for s, x in g.groupby("lado")},
                      dia_tendencia={s: dict(n=int(len(x)), neto=round(float(x.neto.mean()), 2)) for s, x in g.groupby("dia_tendencia")})
    a = o[(o.dia >= A[0]) & (o.dia <= A[1])]
    P = a.pivot_table(index="dia", columns="modulo", values="neto", aggfunc="sum").fillna(0.0)
    corr = P.corr().round(2).to_dict()
    canasta = {}
    for nom, (x, y) in (("A", A), ("B", B)):
        s = o[(o.dia >= x) & (o.dia <= y) & o.modulo.isin(["T", "Z", "R"])].groupby("dia").neto.sum()
        canasta[nom] = dict(dias=int(len(s)), media_dia=float(s.mean()), t=float(s.mean() / s.std(ddof=1) * np.sqrt(len(s))), peor_dia=float(s.min()))
    return dict(modulos=out, correlacion_diaria_A=corr, canasta_TZR=canasta)


def main(path):
    OUT.mkdir(parents=True, exist_ok=True)
    V = contexto(path); o = operaciones(V)
    res = dict(preregistro="PREREGISTRO_MECANISMOS.md", celdas=celdas(o), descriptivo=descriptivo(o))
    (OUT / "MECANISMOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    sel = [c for c in res["celdas"] if c["elegida"]]
    print("elegidas en A:", len(sel), " pasan en B:", sum(c.get("pasa", False) for c in sel))
    for c in sel: print(c["modulo"], c["eje"], c["nivel"], "A", c["nA"], round(c["netoA"], 1), "vs", round(c["netoA_modulo"], 1), "t", round(c["t_difA"], 2),
                        "| B", c.get("nB"), None if c.get("netoB") is None else round(c["netoB"], 1), "vs", None if c.get("netoB_modulo") is None else round(c["netoB_modulo"], 1),
                        "pasa" if c.get("pasa") else "")


if __name__ == "__main__":
    main(sys.argv[1])
