"""H-GC-BT2-1 — carrera de barreras sobre TICKS CRUDOS tras cada TRAP de BigTrap2.

Pre-registro: docs/research/H-GC-BT2-1_PREREGISTRO.md (congelado ANTES de correr).

CRUZA EL STOP: mide outcomes. Autorizado por Nico. CONSUME HOLDOUT: los datos son
2026-08-11 -> 2026-08-21, dentro de la ventana sellada. Gasto deliberado, no descuido.

POR QUE TICKS Y NO VELAS
========================
Dos razones, y las dos son de Nico:
1. El edge puede ser INTRAVELA. Medir el cierre de la vela siguiente lo destruiria.
2. En un grafico de 25 ticks el eje temporal NO es uniforme: en la captura que trajo, 15
   barras caen en 7 segundos y otras tres abarcan un minuto cada una. "N velas despues"
   no es un horizonte.

Por eso el outcome es una carrera de barreras sobre el flujo de ticks, con el horizonte
declarado en TICKS y en RELOJ, nunca en velas.

EL ESTIMANDO ES ECONOMICO, NO ESTADISTICO
=========================================
GC: 1 tick = 10 USD. Friccion ida y vuelta declarada 1,5 ticks. Para una carrera simetrica
de +-B el punto de equilibrio es p* = (B+F)/(2B):

    B= 5 -> 65,0%      B= 9 -> 58,3%      B=18 -> 54,2%      B=30 -> 52,5%

"Distinto de 50%" NO alcanza. Hay que superar p*, y con barreras chicas p* es altisimo.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA_VERSION = "h_gc_bt2_barreras_v1"
ORACULO = pathlib.Path(r"E:\l2_parquet__Tick1.csv")
TICKS = pathlib.Path(r"E:\l2_parquet\GC 12-26.Last.txt")
CANONICAL_OUT = REPO / "docs" / "research" / "h_gc_bt2_barreras.json"
TICK_SIZE = 0.10
OFFSET_H = 3

# --- CONGELADOS EN EL PRE-REGISTRO -------------------------------------------
BARRERAS = (5, 9, 18, 30)                  # ticks; 9 = rango mediano de la barra
HOR_TICKS = (25, 50, 100, 250)             # ~1, 2, 4, 10 barras
HOR_SEG = (5, 30, 120)
FRICCION_TICKS = 1.5
B_BOOT = 10_000
SEED = 20260821
MAX_SEP_MS = 30 * 60 * 1000
TOL_RANGO = 1                              # +-1 tick para emparejar la barra de control
BUCKET_MIN = 15
FASES = [("asia", 18, 3), ("europa", 3, 8), ("premarket", 8, 9.5),
         ("rth_am", 9.5, 12), ("rth_pm", 12, 16), ("cierre", 16, 18)]


def p_equilibrio(b, f=FRICCION_TICKS):
    """Tasa de acierto que deja la expectativa en cero: p*(B-F) = (1-p)*(B+F)."""
    return (b + f) / (2.0 * b)


def fase_de(h):
    for nombre, ini, fin in FASES:
        if ini <= fin:
            if ini <= h < fin:
                return nombre
        elif h >= ini or h < fin:
            return nombre
    return "otro"


class PercentilExpansivo:
    def __init__(self, minimo=20):
        self.hist, self.minimo = {}, minimo

    def pct(self, bucket, valor):
        h = self.hist.setdefault(bucket, [])
        p = None if len(h) < self.minimo else float(np.mean(np.asarray(h) <= valor))
        h.append(valor)
        return None if p is None else round(p, 4)


def leer_oraculo(path):
    barras, traps = {}, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for linea in f:
            p = linea.split("|")
            if len(p) < 4:
                continue
            tipo = p[2].strip()
            kv = dict(x.split("=", 1) for x in p[3].strip().split(";") if "=" in x)
            try:
                t = (dt.datetime.fromisoformat(p[1][:26]).replace(tzinfo=dt.timezone.utc)
                     + dt.timedelta(hours=OFFSET_H))
                ts_ns = int(t.timestamp() * 1e9)
            except Exception:
                continue
            if tipo == "BARRA_PROCESADA":
                barras[int(kv["bar"])] = (int(kv["largo"]), ts_ns)
            elif tipo == "TRAP":
                traps.append((int(kv["bar"]), ts_ns, kv))
    return barras, traps


def leer_ticks(path):
    ts, px = [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for linea in f:
            p = linea.rstrip("\n").split(";")
            if len(p) < 5:
                continue
            try:
                a, b, c = p[0].split(" ")
                e = int(dt.datetime(int(a[:4]), int(a[4:6]), int(a[6:8]), int(b[:2]),
                                    int(b[2:4]), int(b[4:6]),
                                    tzinfo=dt.timezone.utc).timestamp())
                ts.append(e * 1_000_000_000 + int(c) * 100)
                px.append(float(p[1]))
            except Exception:
                pass
    return np.array(ts, dtype=np.int64), np.array(px)


def carrera(pt, ts, j, direccion, b, hor_ticks=None, hor_seg=None):
    """Toca +b antes que -b, en `direccion`, desde el tick j+1.

    Devuelve 1 (gana), 0 (pierde) o None (sin resolver dentro del horizonte).
    `pt` en TICKS ENTEROS. El horizonte se aplica en ticks o en reloj, no en barras.
    """
    n = len(pt)
    i0 = j + 1
    if i0 >= n:
        return None
    fin = n
    if hor_ticks is not None:
        fin = min(fin, i0 + hor_ticks)
    if hor_seg is not None:
        fin = min(fin, int(np.searchsorted(ts, ts[j] + hor_seg * 1_000_000_000)))
    if fin <= i0:
        return None
    seg = pt[i0:fin]
    p0 = pt[j]
    arriba = np.flatnonzero(seg >= p0 + b)
    abajo = np.flatnonzero(seg <= p0 - b)
    ia = arriba[0] if len(arriba) else None
    ib = abajo[0] if len(abajo) else None
    if ia is None and ib is None:
        return None
    if direccion > 0:                       # largo: gana si toca +b primero
        if ia is None:
            return 0
        if ib is None:
            return 1
        return 1 if ia < ib else 0
    if ib is None:
        return 0
    if ia is None:
        return 1
    return 1 if ib < ia else 0


def boot_tasa(por_sesion, b=B_BOOT, seed=SEED, alpha=0.05):
    """Tasa de acierto con bootstrap de SESIONES completas, zona-ponderada."""
    claves = [k for k, v in por_sesion.items() if len(v)]
    if not claves:
        return {}
    todos = np.concatenate([por_sesion[k] for k in claves])
    punto = float(np.mean(todos))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(claves), size=(b, len(claves)))
    reps = np.empty(b)
    for i in range(b):
        reps[i] = np.mean(np.concatenate([por_sesion[claves[j]] for j in idx[i]]))
    lo = float(np.percentile(reps, 100 * alpha / 2))
    hi = float(np.percentile(reps, 100 * (1 - alpha / 2)))
    se = (hi - lo) / (2 * 1.959964)
    return dict(n=int(len(todos)), n_sesiones=len(claves), tasa=round(punto, 4),
                ci95=[round(lo, 4), round(hi, 4)],
                mde=round((1.959964 + 0.841621) * se, 4), B=b, seed=seed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    a = ap.parse_args()

    print("H-GC-BT2-1  -  %s" % SCHEMA_VERSION)
    barras, traps = leer_oraculo(ORACULO)
    ts, px = leer_ticks(TICKS)
    pt = np.round(px / TICK_SIZE).astype(np.int64)
    print("  oraculo %s barras / %s TRAPs   ticks %s"
          % (f"{len(barras):,}", f"{len(traps):,}", f"{len(ts):,}"))

    # --- anclar cada barra del oraculo a su indice de tick --------------------
    idx_bar = {}
    for bar, (largo, tclose) in barras.items():
        j = int(np.searchsorted(ts, tclose, side="right")) - 1
        if j >= 0 and ts[j] == tclose:
            idx_bar[bar] = (j, largo)
    print("  barras ancladas: %s de %s" % (f"{len(idx_bar):,}", f"{len(barras):,}"))

    con_trap = {b for b, _, _ in traps}
    pctv = PercentilExpansivo()

    def contexto(j, largo, tclose):
        i0 = max(j - largo + 1, 0)
        k0 = int(np.searchsorted(ts, tclose - 300 * 1_000_000_000))
        pr = pt[k0:i0]
        if len(pr) < 2:
            return None
        rv = float(np.sqrt((np.diff(pr.astype(float)) ** 2).sum()))
        d = dt.datetime.fromtimestamp(tclose / 1e9, dt.timezone.utc)
        h = d.hour + d.minute / 60.0
        return dict(fase=fase_de(h), bucket=int(h * 60 // BUCKET_MIN), rv=rv,
                    rango=int(pt[i0:j + 1].max() - pt[i0:j + 1].min()),
                    dia=d.strftime("%Y%m%d"))

    # --- eventos TRAP ---------------------------------------------------------
    ev = []
    for bar, ts_ns, kv in sorted(traps, key=lambda x: x[1]):
        if bar not in idx_bar:
            continue
        j, largo = idx_bar[bar]
        c = contexto(j, largo, barras[bar][1])
        if c is None:
            continue
        c["pct_rv"] = pctv.pct(c["bucket"], c["rv"])
        ev.append(dict(bar=bar, j=j, dir=-1 if kv["side"] == "trapped_buyers" else 1,
                       side=kv["side"], vol=float(kv["vol"]),
                       max_ratio=float(kv["max_ratio"]), **c))
    print("  TRAPs con contexto: %s" % f"{len(ev):,}")

    # --- control: barras SIN trap, emparejadas por fase y rango --------------
    pool = collections.defaultdict(list)
    for bar, (j, largo) in idx_bar.items():
        if bar in con_trap:
            continue
        c = contexto(j, largo, barras[bar][1])
        if c is None:
            continue
        pool[(c["dia"], c["fase"], c["rango"])].append((barras[bar][1], j, c))
    rng = np.random.default_rng(SEED)
    usadas = set()
    ctrl = []
    for e in ev:
        mejor = None
        for dr in range(-TOL_RANGO, TOL_RANGO + 1):
            for k, (tc, j, c) in enumerate(pool.get((e["dia"], e["fase"],
                                                     e["rango"] + dr), [])):
                if (e["dia"], e["fase"], e["rango"] + dr, k) in usadas:
                    continue
                d = abs(tc - barras[e["bar"]][1])
                if mejor is None or d < mejor[0]:
                    mejor = (d, (e["dia"], e["fase"], e["rango"] + dr, k), j, c)
        if mejor is None or mejor[0] > MAX_SEP_MS * 1_000_000:
            continue
        usadas.add(mejor[1])
        ctrl.append(dict(j=mejor[2], dir=int(rng.choice([-1, 1])), **mejor[3]))
    print("  controles emparejados: %s (%.4f)" % (f"{len(ctrl):,}",
                                                  len(ctrl) / max(len(ev), 1)))

    # --- medicion -------------------------------------------------------------
    def medir(pobl, b, ht=None, hs=None, filtro=None):
        por = collections.defaultdict(list)
        sinres = 0
        for e in pobl:
            if filtro and not filtro(e):
                continue
            r = carrera(pt, ts, e["j"], e["dir"], b, ht, hs)
            if r is None:
                sinres += 1
                continue
            por[e["dia"]].append(r)
        return {k: np.array(v, dtype=float) for k, v in por.items()}, sinres

    res = {}
    for b in BARRERAS:
        pstar = p_equilibrio(b)
        for ht in HOR_TICKS:
            pt_, sr = medir(ev, b, ht=ht)
            ct_, _ = medir(ctrl, b, ht=ht)
            rt = boot_tasa(pt_)
            rc = boot_tasa(ct_)
            if not rt:
                continue
            res["B%d_T%d" % (b, ht)] = dict(
                barrera=b, horizonte_ticks=ht, p_equilibrio=round(pstar, 4),
                trap=rt, control=rc, sin_resolver=sr,
                frac_sin_resolver=round(sr / max(len(ev), 1), 4),
                supera_equilibrio=bool(rt["ci95"][0] > pstar),
                margen_vs_equilibrio=round(rt["tasa"] - pstar, 4))
    for b in BARRERAS:
        for hs in HOR_SEG:
            pt_, sr = medir(ev, b, hs=hs)
            rt = boot_tasa(pt_)
            if rt:
                res["B%d_S%d" % (b, hs)] = dict(
                    barrera=b, horizonte_seg=hs, p_equilibrio=round(p_equilibrio(b), 4),
                    trap=rt, secundario=True,
                    supera_equilibrio=bool(rt["ci95"][0] > p_equilibrio(b)))

    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                   text=True).strip()
    out = dict(
        schema_version=SCHEMA_VERSION,
        preregistro="docs/research/H-GC-BT2-1_PREREGISTRO.md",
        outcomes_accessed=True, pnl_accessed=False, holdout_included=True,
        advertencia=("CONSUME HOLDOUT: datos 2026-08-11 a 2026-08-21. Gasto deliberado, "
                     "autorizado por Nico."),
        instrumento="GC 12-26", bar_spec="25 tick", tick_size=TICK_SIZE,
        parametros=dict(barreras=list(BARRERAS), horizontes_ticks=list(HOR_TICKS),
                        horizontes_seg=list(HOR_SEG), friccion_ticks=FRICCION_TICKS,
                        B=B_BOOT, seed=SEED,
                        p_equilibrio={str(b): round(p_equilibrio(b), 4)
                                      for b in BARRERAS}),
        conteos=dict(n_traps=len(traps), n_con_contexto=len(ev), n_control=len(ctrl),
                     n_barras=len(barras), n_ancladas=len(idx_bar)),
        resultado=res,
        procedencia=dict(head_commit=head, comando=" ".join(sys.argv)))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")

    print("\n  B  hor_ticks   p*      TRAP   IC95            MDE     control  supera?")
    for b in BARRERAS:
        for ht in HOR_TICKS:
            k = "B%d_T%d" % (b, ht)
            if k not in res:
                continue
            r = res[k]
            t, c = r["trap"], r["control"]
            print(" %2d %8d  %.3f   %.4f [%.4f,%.4f] %.4f  %.4f   %s"
                  % (b, ht, r["p_equilibrio"], t["tasa"], t["ci95"][0], t["ci95"][1],
                     t["mde"], c.get("tasa", float("nan")),
                     "SI" if r["supera_equilibrio"] else "no"))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
