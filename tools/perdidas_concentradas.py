#!/usr/bin/env python3
"""Dónde se concentran las pérdidas: stop corto relativo (pre-registro docs/research/cartera_20261116/PREREGISTRO_PERDIDAS_CONCENTRADAS.md).

  python tools/perdidas_concentradas.py analizar     # C1, C2, C3, H1–H3, descriptivo -> PERDIDAS_CONCENTRADAS.json
Reusa los lectores de tools/cartera_nov_analisis.py (R neto por operación, sesiones válidas del holdout) y la fricción canónica.
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from cartera_nov import DIR, universo  # noqa: E402
from cartera_nov_analisis import _ops, _validas_hold, CORTE_OCT, NOV0  # noqa: E402

GENERADORAS = {"U1-CRUZADO", "CVGAP-NQ", "U1-ZONAS-NQ", "U1-ZONAS-AVCL-NQ"}
VENTANA, MINIMO = 60, 20


def _op_t(cid, tramo):
    """Operaciones con su hora (t) además de R y riesgo, en orden cronológico."""
    o = _ops(cid, tramo)
    if o is None: return None
    from cartera_nov_analisis import DEV_PREVIO, OPS
    f = (DEV_PREVIO / f"{cid}__{tramo}.json") if tramo != "hold" and (DEV_PREVIO / f"{cid}__{tramo}.json").exists() else OPS / f"{cid}__{tramo}.json"
    raw = json.loads(f.read_text()).get("operaciones") or {}
    neto = np.array(raw.get("neto", []), float); rg = np.array([np.nan if x is None else x for x in raw.get("riesgo", [np.nan] * len(neto))], float)
    ok = np.isfinite(neto) & np.isfinite(rg) & (rg > 0); t = np.array(raw.get("t", [0] * len(neto)), float)[ok]
    k = np.lexsort((t, o["ses"])); return {**{a: b[k] for a, b in o.items()}, "t": t[k]}


def clasificar(cid, sp):
    """Por operación: tramo, sesión, hora, R neto, R bruto y si su riesgo está en el tercil bajo de las 60 previas (causal)."""
    from edgelab.research.embudo_runners import friccion
    fr = friccion(sp.get("ejecucion") or sp["sensor"])[0]; ok = _validas_hold(sp); filas, hist = [], []
    for tramo in ("desc", "rep", "hold"):
        o = _op_t(cid, tramo)
        if o is None: return None
        for s, x, rg, t in zip(o["ses"], o["R"], o["riesgo"], o["t"]):
            prev = hist[-VENTANA:]; bajo = None
            if len(prev) >= MINIMO: bajo = bool(np.mean(np.array(prev) < rg) < 1 / 3)
            hist.append(rg)
            if tramo == "hold" and not ok(s): continue
            filas.append(dict(tramo=tramo, ses=int(s), t=float(t), R=float(x), Rb=float(x + fr / rg), bajo=bajo, riesgo=float(rg)))
    return filas


def delta(por_regla, campo="R", B=10000, seed=20261116):
    """Δ estratificado por regla y p de una cola (Δ < 0) por bootstrap de sesiones sobre el conjunto entero."""
    def est(F):
        num = den = 0.0; signos = []
        for f in F.values():
            b = np.array([x[campo] for x in f if x["bajo"]]); r = np.array([x[campo] for x in f if x["bajo"] is False])
            if len(b) < 3 or len(r) < 3: continue
            w = len(b) * len(r) / (len(b) + len(r)); d = b.mean() - r.mean(); num += w * d; den += w; signos.append(d < 0)
        return (num / den if den else np.nan), signos
    F = {c: [x for x in f if x["bajo"] is not None] for c, f in por_regla.items()}
    d0, signos = est(F)
    ses = sorted({(c, x["ses"]) for c, f in F.items() for x in f}); dias = sorted({s for _, s in ses})
    por_dia = {}
    for c, f in F.items():
        for x in f: por_dia.setdefault(x["ses"], []).append((c, x))
    rng = np.random.default_rng(seed); bs = []
    for _ in range(B if len(dias) > 5 else 0):
        G = {}
        for d in rng.choice(dias, len(dias)):
            for c, x in por_dia[d]: G.setdefault(c, []).append(x)
        bs.append(est(G)[0])
    bs = np.array(bs); bs = bs[np.isfinite(bs)]
    nb = sum(1 for f in F.values() for x in f if x["bajo"]); nr = sum(1 for f in F.values() for x in f if x["bajo"] is False)
    sd = float(bs.std(ddof=1)) if len(bs) > 2 else None
    return dict(delta=float(d0), p_una_cola=float((1 + (bs >= 0).sum()) / (1 + len(bs))) if len(bs) else None, ee=sd,
                mde80=float(2.49 * sd) if sd else None, reglas_con_delta_neg=f"{sum(signos)}/{len(signos)}", n_bajo=nb, n_resto=nr,
                R_total_bajo=float(sum(x[campo] for f in F.values() for x in f if x["bajo"])),
                R_op_todo=float(np.mean([x[campo] for f in F.values() for x in f])) if nb + nr else None,
                R_op_sin_bajo=float(np.mean([x[campo] for f in F.values() for x in f if x["bajo"] is False])) if nr else None)


def _bh(ps, q=0.10):
    o = np.argsort(ps); k = 0
    for i, j in enumerate(o, 1):
        if ps[j] <= q * i / len(ps): k = i
    return [bool(r < k) for r in np.argsort(o)]


def descriptivo(por_regla):
    import datetime as dt
    from zoneinfo import ZoneInfo
    ny = ZoneInfo("America/New_York"); H = {}; W = {}
    for f in por_regla.values():
        for x in f:
            if not x["t"]: continue
            h = dt.datetime.fromtimestamp(x["t"], ny); m = h.hour * 60 + h.minute
            b = "09:30-10:30" if 570 <= m < 630 else "10:30-14:00" if 630 <= m < 840 else "14:00-16:15" if 840 <= m < 975 else "resto"
            H.setdefault(b, []).append(x["R"]); W.setdefault(h.strftime("%a"), []).append(x["R"])
    tot_neg = sum(-r for v in H.values() for r in v if r < 0)
    f = lambda D: {k: dict(n=len(v), R_op=float(np.mean(v)), R_total=float(np.sum(v)), parte_de_perdidas=float(sum(-r for r in v if r < 0) / tot_neg) if tot_neg else None)
                   for k, v in sorted(D.items())}
    return dict(hora_ny=f(H), dia=f(W))


def tamano(por_regla):
    out = {}
    for nom, g in (("riesgo_fijo_R", lambda x: x["R"]), ("contrato_fijo_pts", lambda x: x["R"] * x["riesgo"]), ("raiz", lambda x: x["R"] * np.sqrt(x["riesgo"]))):
        ts = []
        for f in por_regla.values():
            v = np.array([g(x) for x in f])
            if len(v) > 2 and v.std(ddof=1) > 0: ts.append(v.mean() / v.std(ddof=1) * np.sqrt(len(v)))
        out[nom] = dict(t_medio_por_regla=float(np.mean(ts)) if ts else None, reglas_t_pos=f"{sum(t > 0 for t in ts)}/{len(ts)}")
    return out


def analizar():
    U = universo(); todas = {}
    for r in U:
        f = clasificar(r["cid"], r["spec"])
        if f: todas[r["cid"]] = f
    C1 = {c: [x for x in f if x["tramo"] in ("desc", "rep")] for c, f in todas.items() if c not in GENERADORAS}
    C2 = {c: [x for x in f if x["tramo"] == "hold" and x["ses"] >= NOV0] for c, f in todas.items()}
    C2 = {c: f for c, f in C2.items() if f}
    C3 = {c: [x for x in f if x["tramo"] == "hold"] for c, f in todas.items()}
    H = {"H1": delta(C1, "R"), "H2": delta(C1, "Rb")}
    H["H3"] = dict(R_total_bajo=H["H1"]["R_total_bajo"], p_una_cola=None)
    # H3: suma de R del tercil bajo < 0; p por bootstrap de sesiones de la suma
    rng = np.random.default_rng(7); xb = {}
    for f in C1.values():
        for x in f:
            if x["bajo"]: xb.setdefault(x["ses"], 0.0); xb[x["ses"]] += x["R"]
    dias = sorted({x["ses"] for f in C1.values() for x in f if x["bajo"] is not None}); v = np.array([xb.get(d, 0.0) for d in dias])
    bs = np.array([v[rng.integers(0, len(v), len(v))].sum() for _ in range(10000)]); H["H3"]["p_una_cola"] = float((1 + (bs >= 0).sum()) / 10001)
    ps = [H[k]["p_una_cola"] for k in ("H1", "H2", "H3")]; bh = _bh(ps)
    for k, b in zip(("H1", "H2", "H3"), bh): H[k]["nominada_BH"] = b
    c2 = delta(C2, "R", B=2000); c3 = delta(C3, "R", B=2000)
    lect = ("CONFIRMADA" if H["H1"]["nominada_BH"] and c2["delta"] < 0 and H["H2"]["nominada_BH"] else
            "SOLO_FRICCION" if H["H1"]["nominada_BH"] and not H["H2"]["nominada_BH"] else
            "REFUTADA" if H["H1"]["delta"] >= 0 and (H["H1"]["mde80"] or 9) <= 0.10 else "NO_CONCLUYENTE")
    por_regla = {c: dict(n=len([x for x in f if x["bajo"] is not None]), **{k: v for k, v in delta({c: f}, "R", B=0).items() if k in ("delta", "n_bajo", "R_total_bajo")}) for c, f in C1.items()}
    out = dict(preregistro="PREREGISTRO_PERDIDAS_CONCENTRADAS.md", reglas_C1=sorted(C1), reglas_C2=sorted(C2), hipotesis=H, C2_noviembre=c2, C3_holdout=c3,
               lectura=lect, por_regla_C1=por_regla, descriptivo_C1=descriptivo(C1), tamano=dict(C1=tamano(C1), C2=tamano(C2)))
    (DIR / "PERDIDAS_CONCENTRADAS.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps({k: out[k] for k in ("hipotesis", "C2_noviembre", "lectura")}, indent=1, default=float))


if __name__ == "__main__":
    analizar() if sys.argv[1:] == ["analizar"] else print(__doc__)
