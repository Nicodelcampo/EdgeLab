"""ORB-HORARIOS: barrido de 44 ventanas x 2 reglas x 8 activos + embudo de confirmacion.
Reglas: docs/research/orb0100_20261021/MANIFIESTO_ORB_HORARIOS_20261021.md (no cambiar sin enmienda).
Uso: python tools/orb0100/orb_horarios.py <out.json>"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orb0100_v2 as V  # noqa: E402

VENTANAS = list(range(0, 1291, 30))          # minutos desde las 18:00 ET (18:00 .. 15:30)
TOPE = 1375                                  # 16:55 ET
REGLAS = {"R0": (0.5, False), "R1": (1.5, True)}
NB = 2000


def hhmm(m0):
    t = (1080 + m0) % 1440; return f"{t // 60:02d}:{t % 60:02d}"


def senales_ses(d, m0):
    out = []; sm = d.sm.values; b5 = d.b5.values; c = d.close.values; h = d.high.values; l = d.low.values
    fin_m = min(m0 + 15 + 360, TOPE)
    for ses, idx in d.groupby("sesion").indices.items():
        smi = sm[idx]
        r = idx[(smi >= m0) & (smi < m0 + 15)]
        if len(r) < 9: continue
        hi, lo = h[r].max(), l[r].min()
        post = idx[(smi >= m0 + 15) & (smi < fin_m)]
        if len(post) < 5 or hi <= lo: continue
        pb = b5[post]; ends = np.flatnonzero(np.r_[pb[1:] != pb[:-1], True])          # ultima M1 de cada vela de 5 min
        for e in ends:
            k = post[e]; dirn = 1 if c[k] > hi else (-1 if c[k] < lo else 0)
            if dirn:
                out.append(dict(fecha=str(ses), hi=hi, lo=lo, dir=dirn, k=int(k), c=c[k], vwap=d.vwap.values[k], ema=0.0, fin=int(post[-1]))); break
    return out


def opera_dir(h, l, c, k, fin, E, dirn, risk, tp_r, tick, comm):
    sl = E - dirn * risk; tp = E + dirn * tp_r * risk
    for j in range(k + 1, fin + 1):
        if (l[j] <= sl) if dirn > 0 else (h[j] >= sl): return (dirn * (sl - dirn * tick - E) - comm) / risk
        if (h[j] >= tp) if dirn > 0 else (l[j] <= tp): return (dirn * (tp - E) - comm) / risk
    return (dirn * (c[fin] - dirn * tick - E) - comm) / risk


def main():
    rng = np.random.default_rng(20261021); celdas = []; detalle = {}
    for inst, (tick, usd_pt, comm) in V.ACT.items():
        d = V.cargar(inst); cp = comm / usd_pt
        d["sm"] = ((d.et.dt.hour * 60 + d.et.dt.minute) - 1080) % 1440
        h, l, c = d.high.values, d.low.values, d.close.values
        for m0 in VENTANAS:
            S = senales_ses(d, m0)
            for rn, (tp_r, use_vwap) in REGLAS.items():
                R, R2, Rf, F = [], [], [], []
                for s in S:
                    if use_vwap and not ((s["c"] > s["vwap"]) if s["dir"] > 0 else (s["c"] < s["vwap"])): continue
                    E = s["c"] + s["dir"] * tick; risk = s["dir"] * (E - (s["lo"] if s["dir"] > 0 else s["hi"]))
                    if risk <= 0: continue
                    R.append(opera_dir(h, l, c, s["k"], s["fin"], E, s["dir"], risk, tp_r, tick, cp))
                    E2 = s["c"] + s["dir"] * 2 * tick; risk2 = s["dir"] * (E2 - (s["lo"] if s["dir"] > 0 else s["hi"]))
                    R2.append(opera_dir(h, l, c, s["k"], s["fin"], E2, s["dir"], risk2, tp_r, 2 * tick, cp) if risk2 > 0 else -1.0)
                    Ef = s["c"] - s["dir"] * tick                                          # direccion contraria, mismo riesgo
                    Rf.append(opera_dir(h, l, c, s["k"], s["fin"], Ef, -s["dir"], risk, tp_r, tick, cp))
                    F.append(s["fecha"])
                if len(R) < 20: continue
                R, R2, Rf, F = map(np.array, (R, R2, Rf, F))
                is_ = F < "2026"; bs = np.array([rng.choice(R, len(R)).mean() for _ in range(NB)])
                rec = dict(inst=inst, ventana=hhmm(m0), m0=m0, regla=rn, n=len(R), R_op=round(float(R.mean()), 4),
                           R_IS=round(float(R[is_].mean()), 4) if is_.any() else None, R_OOS=round(float(R[~is_].mean()), 4) if (~is_).any() else None,
                           p=float(np.mean(bs <= 0)), contaminada=bool(inst == "NQ" and m0 == 420))
                celdas.append(rec); detalle[(inst, m0, rn)] = (R, R2, Rf)
        print(inst, flush=True)
    # 1) cribado con BH 10 %
    ps = np.array([x["p"] for x in celdas]); order = np.argsort(ps); m = len(ps); thr = 0.0
    for rank, i in enumerate(order, 1):
        if ps[i] <= 0.10 * rank / m: thr = ps[i]
    buenas = []
    for x in celdas:
        x["pasa_BH"] = bool(x["p"] <= thr and thr > 0)
        x["cribado"] = bool(x["pasa_BH"] and x["n"] >= 60 and (x["R_IS"] or -1) > 0 and (x["R_OOS"] or -1) > 0)
        if x["cribado"]: buenas.append(x)
    # 2) confirmacion
    idx = {(x["inst"], x["m0"], x["regla"]): x for x in celdas}
    for x in buenas:
        R, R2, Rf = detalle[(x["inst"], x["m0"], x["regla"])]
        a = float(R2.mean()) > 0
        vec = [idx.get((x["inst"], x["m0"] + dm, x["regla"])) for dm in (-30, 30)]; b = any(v and v["R_op"] > 0 for v in vec)
        null = np.array([np.where(rng.random(len(R)) < 0.5, R, Rf).mean() for _ in range(2000)]); pn = float(np.mean(null >= R.mean())); cc = pn < 0.05
        k = max(1, int(round(0.05 * len(R)))); dd = float(np.sort(R)[:-k].mean()) > 0
        x["confirmacion"] = dict(costo_extra_R=round(float(R2.mean()), 4), costo_ok=a, vecinas=[v and v["R_op"] for v in vec], vecindad_ok=b,
                                 p_nulo_direccion=round(pn, 4), nulo_ok=cc, sin_top5pct_R=round(float(np.sort(R)[:-k].mean()), 4), robustez_ok=dd,
                                 pasa_todo=bool(a and b and cc and dd))
    out = dict(manifiesto="MANIFIESTO_ORB_HORARIOS_20261021.md", umbral_BH=thr, n_celdas=len(celdas), n_cribado=len(buenas),
               confirmadas=[x for x in buenas if x["confirmacion"]["pasa_todo"]], cribadas=buenas, celdas=celdas)
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str)
    print("celdas", len(celdas), "umbral BH", thr, "cribadas", len(buenas), "confirmadas", len(out["confirmadas"]))
    for x in buenas: print(x["inst"], x["ventana"], x["regla"], x["n"], x["R_op"], x["R_IS"], x["R_OOS"], x["confirmacion"])


if __name__ == "__main__":
    main()
