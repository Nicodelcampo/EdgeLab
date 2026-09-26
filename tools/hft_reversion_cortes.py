#!/usr/bin/env python3
r"""HFT-REV-EXP, enmienda 1: cortes por contexto de la reversión en el primer retorno (D = 20; R = 40 y 80).

Pre-registro: docs/research/HFT_REVERSION_EXPLORATORIA_MNQ_20260926.md (enmienda 1, escrita antes de medir).
Descubrimiento en un contrato: fija los terciles y aplica BH-FDR. Replicación en otros: reusa los límites
(`--limites`) sin elegir nada.

    python tools/hft_reversion_cortes.py --parquet .../MNQ_09-25_ticks.parquet --contract "MNQ 09-25" --out DIR
    python tools/hft_reversion_cortes.py --parquet .../MNQ_12-25_ticks.parquet --contract "MNQ 12-25" \
        --limites DIR/limites.json --out DIR2
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hft_reversion_explore as H  # noqa: E402

D = 20
RS = (40, 80)
TERCILES = ("vol", "avg_ms", "W", "edad", "alejamiento", "tend15", "tend60")
CATEG = ("bucket", "confluencia", "hora", "color")
NS = H.NS


def _hora(ts_ns):
    t = pd.Timestamp(int(ts_ns), tz="UTC").tz_convert("America/New_York")
    m = t.hour * 60 + t.minute
    if 570 <= m < 660:
        return "apertura"
    if 660 <= m < 840:
        return "mediodia"
    if 840 <= m < 960:
        return "cierre"
    return "ETH"


def features(ts, px, rows, zones, real_zones):
    """Agrega variables a cada evento tocado. `zones` = las zonas de estos eventos (reales o de control);
    `real_zones` = las zonas reales de la sesión (para la confluencia)."""
    lo = np.array([z["bot"] for z in real_zones]); hi = np.array([z["top"] for z in real_zones])
    av = np.array([z["i_avail"] for z in real_zones])
    for r, z in zip(rows, zones):
        if r["estado"] != H.TOUCHED:
            continue
        it = r["i_toque"]; pol = z["pol"]
        near = z["top"] if pol > 0 else z["bot"]
        seg = px[z["i_avail"]:it + 1]
        r["alejamiento"] = float(pol * (seg.max() if pol > 0 else seg.min()) - pol * near) if len(seg) else 0.0
        for k, sec in (("tend15", 900), ("tend60", 3600)):
            j = int(np.searchsorted(ts, ts[it] - sec * NS))
            r[k] = float(pol * (px[it] - px[j]))
        r["edad"] = r["t_toque_s"]
        cov = (av < it) & (lo <= near + 2) & (hi >= near - 2)
        n = int(cov.sum()) - int(z.get("zid", "").count("~") == 0)      # sin contarse a sí misma
        r["confluencia"] = "0" if n <= 0 else ("1" if n == 1 else "2+")
        r["hora"] = _hora(ts[it])
        r["color"] = "verde" if pol > 0 else "roja"
        for k in ("vol", "avg_ms", "bucket"):
            r[k] = z.get(k)
    return rows


def collect(parquet, instrument, contract, max_sessions=None):
    rng = np.random.default_rng(20260926)
    out = {R: dict(real=[], nivel=[]) for R in RS}
    for td, ts, px, zones in H.load_zones(parquet, instrument, contract, max_sessions):
        nulls = H.level_nulls(ts, px, zones, rng)
        for R in RS:
            for tag, zz in (("real", zones), ("nivel", nulls)):
                rows = features(ts, px, H.run_zones(ts, px, zz, D, R), zz, zones)
                for r in rows:
                    if r["estado"] == H.TOUCHED and r["desenlace"] != H.OUT_CENS:
                        r["sesion"] = td
                        out[R][tag].append({k: v for k, v in r.items() if k not in ("mfe", "mae")})
        print(f"{td}: {len(zones)} zonas", flush=True)
    return out


def limites(real_rows):
    return {k: [float(np.nanpercentile([r[k] for r in real_rows], q)) for q in (33.333, 66.667)] for k in TERCILES}


def etiqueta(r, k, lim):
    if k in CATEG:
        return str(r.get(k))
    a, b = lim[k]
    v = r[k]
    return "T1" if v <= a else ("T2" if v <= b else "T3")


def bh(ps, q=0.10):
    p = np.asarray(ps, float); n = len(p); o = np.argsort(p)
    ok = np.zeros(n, bool)
    th = q * (np.arange(1, n + 1)) / n
    passed = np.where(p[o] <= th)[0]
    if len(passed):
        ok[o[: passed.max() + 1]] = True
    return ok


def cortes(data, lim):
    filas = []
    for R, d in data.items():
        for k in TERCILES + CATEG:
            niveles = sorted({etiqueta(r, k, lim) for r in d["real"]})
            for lv in niveles:
                a = [r for r in d["real"] if etiqueta(r, k, lim) == lv]
                b = [r for r in d["nivel"] if etiqueta(r, k, lim) == lv]
                if len(a) < 30 or len(b) < 30:
                    continue
                pt, lo, hi = H.boot_diff(a, b, "sesion")
                se = (hi - lo) / (2 * 1.96) if hi > lo else float("nan")
                p = 2 * (1 - 0.5 * (1 + math.erf(abs(pt / se) / math.sqrt(2)))) if se and se == se and se > 0 else 1.0
                ra = np.mean([r["desenlace"] == H.OUT_REV for r in a]); rb = np.mean([r["desenlace"] == H.OUT_REV for r in b])
                rw = np.mean([r["rw"] for r in a])
                filas.append(dict(R=R, variable=k, nivel=lv, n_real=len(a), n_ctrl=len(b), real=float(ra), ctrl=float(rb),
                                  caminata=float(rw), dif=pt, ic=[lo, hi], p=p))
    ok = bh([f["p"] for f in filas])
    for f, o in zip(filas, ok):
        f["fdr"] = bool(o)
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True); ap.add_argument("--instrument", default="MNQ")
    ap.add_argument("--contract", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--limites"); ap.add_argument("--max-sessions", type=int)
    a = ap.parse_args(argv)
    data = collect(a.parquet, a.instrument, a.contract, a.max_sessions)
    lim = json.loads(Path(a.limites).read_text()) if a.limites else limites(data[RS[0]]["real"])
    filas = cortes(data, lim)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "limites.json").write_text(json.dumps(lim, indent=1))
    (out / "cortes.json").write_text(json.dumps(dict(contrato=a.contract, D=D, limites=lim, filas=filas), indent=1,
                                                ensure_ascii=False))
    L = [f"# Cortes HFT-REV-EXP — {a.contract} (D = {D})", "",
         "| R | variable | nivel | n | real | control | caminata | real − control [IC 95 %] | FDR |", "|---|---|---|---|---|---|---|---|---|"]
    for f in filas:
        L.append(f"| {f['R']} | {f['variable']} | {f['nivel']} | {f['n_real']} | {f['real']:.3f} | {f['ctrl']:.3f} | "
                 f"{f['caminata']:.3f} | {100 * f['dif']:+.1f} pp [{100 * f['ic'][0]:+.1f}, {100 * f['ic'][1]:+.1f}] | "
                 f"{'sí' if f['fdr'] else ''} |")
    (out / "cortes.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
