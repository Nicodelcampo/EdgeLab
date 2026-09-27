"""ESPEJO-MÁS-ALLÁ, Fase 0 (manifiesto `docs/research/MANIFIESTO_ESPEJO_MAS_ALLA_BORRADOR_20260927.md`).

¿Hay más casos que van lejos más allá de A **y** más casos que mueren en A que en un placebo con la misma geometría?
Descriptivo: sin imanes, sin condicionantes, sin entradas ni costos.

Uso:
  python tools/espejo_mas_alla.py spy --csv SPY.csv --out DIR
  python tools/espejo_mas_alla.py fut --inst ES --parquet ... [--modo rth|full] --out DIR
  python tools/espejo_mas_alla.py comb --dirs D1 D2 D3 --spy DIR_SPY --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import espejo_macro as EM  # noqa: E402
import espejo_semejanza as ES  # noqa: E402

CFGS = ((12, 3), (12, 4), (24, 4))
OS = (0.25, 0.5, 1.0, 2.0)
BARRERA = 0.5
SEED = 20260927


def extension(H, L, lvl, W, cont, j0):
    """M (en W) más allá de `lvl` en dirección `cont` desde la vela j0 (incluida) hasta la barrera lvl ∓ 0,5 W o el fin.
    En velas posteriores a j0, la barrera se evalúa antes que la extensión (pesimista). Devuelve (M, censurado)."""
    n = len(H)
    bar = lvl - cont * BARRERA * W
    M = max(0.0, ((lvl - L[j0]) if cont == -1 else (H[j0] - lvl)) / W)
    for q in range(j0 + 1, n):
        if (cont == -1 and H[q] >= bar) or (cont == 1 and L[q] <= bar):
            return M, False
        M = max(M, ((lvl - L[q]) if cont == -1 else (H[q] - lvl)) / W)
    return M, True


def eventos_sesion(t, H, L, C, O, imp, rng, sesion):
    out = []
    n = len(C)
    for row in imp:
        d, a, ext, iext = int(row[0]), row[1], row[2], int(row[4])
        W = abs(ext - a)
        if W <= 0:
            continue
        k_touch = None
        for k in range(iext + 1, n):
            if (d == 1 and H[k] > ext) or (d == -1 and L[k] < ext):
                break
            if (d == 1 and L[k] <= a) or (d == -1 and H[k] >= a):
                k_touch = k
                break
        if k_touch is None:
            continue
        cont = -d                                           # el espejo sigue en contra del impulso
        M, cen = extension(H, L, a, W, cont, k_touch)
        j = int(rng.integers(0, n))
        Mp, cenp = extension(H, L, O[j], W, cont, j)
        # sensibilidad (enmienda F0-1, posterior a ver SPY): placebo en la misma vela del toque de otra sesión al azar
        out.append(dict(sesion=sesion, W=float(W), dir=cont, M=float(M), cens=cen, Mp=float(Mp), censp=cenp,
                        velas_hasta_toque=k_touch - iext, k_touch=k_touch, j0=int(k_touch)))
    return out


def correr(bars, etiqueta):
    H = bars.H.to_numpy(np.float64); L = bars.L.to_numpy(np.float64); C = bars.C.to_numpy(np.float64)
    O = bars.O.to_numpy(np.float64); t = bars.t.to_numpy(np.float64); atr = EM.atr_prev(H, L, C)
    days = bars.day.to_numpy()
    cuts = np.r_[0, np.where(days[1:] != days[:-1])[0] + 1, len(days)]
    data = {}
    for mb, k in CFGS:
        rng = np.random.default_rng(SEED)
        rows = []
        for a, b in zip(cuts[:-1], cuts[1:]):
            if b - a <= mb:
                continue
            imp = EM.detect_var(t[a:b], H[a:b], L[a:b], C[a:b], mb, k * atr[a:b], EM.EFF, EM.RETR)
            rows += eventos_sesion(t[a:b], H[a:b], L[a:b], C[a:b], O[a:b], imp, rng, str(days[a]))
        # placebo emparejado por hora (enmienda F0-1): misma vela del día que el toque, en otra sesión al azar
        largas = [(a_, b_) for a_, b_ in zip(cuts[:-1], cuts[1:])]
        for r in rows:
            for _ in range(20):
                a_, b_ = largas[int(rng.integers(0, len(largas)))]
                if b_ - a_ > r["k_touch"] and str(days[a_]) != r["sesion"]:
                    j = a_ + r["k_touch"]
                    m2, c2 = extension(H[a_:b_], L[a_:b_], O[j], r["W"], r["dir"], r["k_touch"])
                    r.update(Mh=float(m2), censh=c2)
                    break
            else:
                r.update(Mh=float("nan"), censh=True)
        data[f"5m_{mb}_{k}"] = rows
        print(f"{etiqueta} 5m_{mb}_{k}: {len(rows)} toques de A", flush=True)
    return data


def _stat(rows, nombre, pk="Mp"):
    """Diferencia real − placebo. Un censurado cuenta con el M alcanzado (cota inferior), igual en real y placebo."""
    M = np.array([r["M"] for r in rows if r.get(pk) == r.get(pk)]); P = np.array([r[pk] for r in rows if r.get(pk) == r.get(pk)])
    if nombre.startswith("sup_"):
        o = float(nombre[4:])
        return float(np.mean(M >= o) - np.mean(P >= o))
    if nombre == "muere_en_A":
        return float(np.mean(M < 0.1) - np.mean(P < 0.1))
    if nombre == "lejos":
        return float(np.mean(M >= 1) - np.mean(P >= 1))
    raise ValueError(nombre)


PRUEBAS = [f"sup_{o}" for o in OS] + ["muere_en_A", "lejos"]


def analizar(data, nboot=1000, pk="Mp"):
    filas = []
    for cfg, rows in data.items():
        if not rows:
            continue
        ses = sorted({r["sesion"] for r in rows})
        por = {s: [r for r in rows if r["sesion"] == s] for s in ses}
        rng = np.random.default_rng(SEED)
        boots = {p: [] for p in PRUEBAS}
        for _ in range(nboot):
            smp = [x for i in rng.choice(len(ses), len(ses)) for x in por[ses[i]]]
            for p in PRUEBAS:
                boots[p].append(_stat(smp, p, pk))
        M = np.array([r["M"] for r in rows]); P = np.array([r[pk] for r in rows if r.get(pk) == r.get(pk)])
        for p in PRUEBAS:
            b = np.array(boots[p]); est = _stat(rows, p, pk)
            pv = float(min(1.0, 2 * min(np.mean(b <= 0), np.mean(b >= 0))))
            fila = dict(config=cfg, prueba=p, n=len(rows), est=est, ic=[float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
                        p=pv, mde=float(2.8 * b.std()))
            if p.startswith("sup_"):
                o = float(p[4:])
                fila.update(real=float(np.mean(M >= o)), placebo=float(np.mean(P >= o)), teorico=BARRERA / (BARRERA + o))
            filas.append(fila)
        filas.append(dict(config=cfg, prueba="_distribucion", n=len(rows),
                          cuantiles_real=[float(np.percentile(M, q)) for q in (10, 25, 50, 75, 90, 95)],
                          cuantiles_placebo=[float(np.percentile(P, q)) for q in (10, 25, 50, 75, 90, 95)],
                          censurados_real=float(np.mean([r["cens"] for r in rows])),
                          censurados_placebo=float(np.mean([r["censp" if pk == "Mp" else "censh"] for r in rows]))))
    for f in filas:
        f["placebo_tipo"] = "vela al azar de la misma sesión" if pk == "Mp" else "misma vela del día, otra sesión (F0-1)"
    ok = ES.bh([f["p"] for f in filas if "p" in f])
    for f, o in zip([f for f in filas if "p" in f], ok):
        f["fdr"] = bool(o)
    return filas


def svg_superv(data, titulo, pk="Mp", w=640, h=300, pad=40):
    """Supervivencia P(M ≥ o) real vs placebo vs teórica, o de 0 a 3 W, eje y logarítmico."""
    cols = ["#2563eb", "#dc2626", "#16a34a"]
    oo = np.linspace(0, 3, 61)
    ymin = 0.005
    def py(v):
        v = max(v, ymin)
        return h - pad - (np.log10(v) - np.log10(ymin)) / (0 - np.log10(ymin)) * (h - 2 * pad)
    def px(o):
        return pad + o / 3 * (w - 2 * pad)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="sans-serif" font-size="11">',
         f'<rect width="100%" height="100%" fill="#fff"/><text x="{pad}" y="18">{titulo}</text>']
    for v in (1, 0.1, 0.01):
        s.append(f'<line x1="{pad}" x2="{w - pad}" y1="{py(v):.1f}" y2="{py(v):.1f}" stroke="#eee"/>'
                 f'<text x="{pad - 4}" y="{py(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
    for o in (0, 1, 2, 3):
        s.append(f'<text x="{px(o):.1f}" y="{h - pad + 14}" text-anchor="middle">{o} W</text>')
    s.append(f'<polyline fill="none" stroke="#999" stroke-dasharray="4 3" points="'
             + " ".join(f"{px(o):.1f},{py(BARRERA / (BARRERA + o)):.1f}" for o in oo) + '"/>')
    y0 = 34
    for i, (cfg, rows) in enumerate(data.items()):
        if not rows:
            continue
        M = np.array([r["M"] for r in rows]); P = np.array([r[pk] for r in rows if r.get(pk) == r.get(pk)])
        for arr, dash in ((M, ""), (P, ' stroke-dasharray="2 2"')):
            s.append(f'<polyline fill="none" stroke="{cols[i]}"{dash} stroke-width="1.4" points="'
                     + " ".join(f"{px(o):.1f},{py(np.mean(arr >= o)):.1f}" for o in oo) + '"/>')
        s.append(f'<text x="{w - pad}" y="{y0 + 14 * i}" text-anchor="end" fill="{cols[i]}">{cfg} (n={len(rows)}) '
                 f'— continuo: real, punteado: placebo</text>')
    s.append(f'<text x="{w - pad}" y="{y0 + 42}" text-anchor="end" fill="#999">gris: teórico 0,5/(0,5+o)</text></svg>')
    return "".join(s)


def escribir(out, titulo, data, filas, meta):
    out.mkdir(parents=True, exist_ok=True)
    _escribir(out, titulo, data, filas, meta, "")
    _escribir(out, titulo + " — placebo emparejado por hora (F0-1)", data, analizar(data, pk="Mh"), meta, "_hora")


def _escribir(out, titulo, data, filas, meta, suf):
    (out / "eventos.json").write_text(json.dumps(data))
    (out / f"reporte{suf}.json").write_text(json.dumps(dict(meta=meta, filas=filas), indent=1))
    (out / f"supervivencia{suf}.svg").write_text(svg_superv(data, titulo, "Mp" if not suf else "Mh"))
    L = [f"# ESPEJO-MÁS-ALLÁ Fase 0 — {titulo}", "", f"Meta: `{json.dumps(meta, ensure_ascii=False)}`", "",
         "| config | prueba | n | real | placebo | teórico | real − placebo [IC 95 %] | MDE | FDR |", "|---|---|---|---|---|---|---|---|---|"]
    for f in filas:
        if f["prueba"] == "_distribucion":
            continue
        r = lambda k: f"{f[k]:.3f}" if k in f else "—"  # noqa: E731
        L.append(f"| {f['config']} | {f['prueba']} | {f['n']} | {r('real')} | {r('placebo')} | {r('teorico')} | "
                 f"{f['est']:+.3f} [{f['ic'][0]:+.3f}, {f['ic'][1]:+.3f}] | {f['mde']:.3f} | {'sí' if f['fdr'] else 'no'} |")
    L += ["", "Cuantiles de M (10, 25, 50, 75, 90, 95) y censurados:", ""]
    for f in filas:
        if f["prueba"] == "_distribucion":
            L.append(f"- {f['config']}: real {[round(v, 2) for v in f['cuantiles_real']]} (cens {f['censurados_real']:.0%}); "
                     f"placebo {[round(v, 2) for v in f['cuantiles_placebo']]} (cens {f['censurados_placebo']:.0%})")
    (out / f"reporte{suf}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("spy"); s1.add_argument("--csv", required=True); s1.add_argument("--out", required=True)
    s2 = sub.add_parser("fut"); s2.add_argument("--inst", required=True); s2.add_argument("--parquet", nargs="+", required=True)
    s2.add_argument("--modo", choices=("rth", "full"), default="rth"); s2.add_argument("--out", required=True)
    s3 = sub.add_parser("comb"); s3.add_argument("--dirs", nargs="+", required=True); s3.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "spy":
        bars, dups = EM.spy_bars(a.csv, 5)
        data = correr(bars, "SPY")
        escribir(Path(a.out), "SPY 2008–2021 (descubrimiento)", data, analizar(data),
                 dict(fuente="SPY 1 min RTH", dias=int(bars.day.nunique()), filas_duplicadas_eliminadas=int(dups)))
    elif a.cmd == "fut":
        bars = EM.es_bars(a.parquet, 5, modo=a.modo)
        data = correr(bars, a.inst)
        escribir(Path(a.out), f"{a.inst} {a.modo.upper()}", data, analizar(data),
                 dict(fuente=f"{a.inst} {a.modo.upper()} 2025-07..2026-03", dias=int(bars.day.nunique()),
                      parquets=[Path(p).name for p in a.parquet]))
    else:
        data = {}
        for d in a.dirs:
            for k, rows in json.loads((Path(d) / "eventos.json").read_text()).items():
                data.setdefault(k, []).extend(rows)
        escribir(Path(a.out), "Futuros combinados RTH (replicación)", data, analizar(data),
                 dict(fuente=" + ".join(Path(d).name for d in a.dirs), bootstrap="por día calendario"))


if __name__ == "__main__":
    main()
