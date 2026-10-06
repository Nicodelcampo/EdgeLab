#!/usr/bin/env python3
"""VTD-DIR etapa 1, análisis (propuesta docs/research/VTD_DIR_PROPUESTA_20261006.md + enmienda 1).
Resultado sin escala: asim_H = (U − D)/(U + D) desde el close de la marca VTD (150t). Acierto = signo(pred) × asim.
Descubrimiento: MNQ 09-25, 12-25, 03-26. Confirmación: 06-26, 09-26, 12-26 (sólo lo que pasa descubrimiento, sin cambios).
P1 EMA: 10 EMAs × 5 condiciones × 2 H = 100 celdas, max-T por sorteo de signo por sesión (2.000). P2–P6: Holm sobre 10.
RTH. Controles (barras al azar) y régimen de amplitud: descriptivos."""
import glob
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

IN = [Path(p) for p in sys.argv[1:]] or [Path("/kaggle/input")]
OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(os.environ.get("AVCL_OUT", "."))
DISC = ("MNQ_09-25", "MNQ_12-25", "MNQ_03-26")
CONF = ("MNQ_06-26", "MNQ_09-26", "MNQ_12-26")
EMAS = ["ema_b%d" % p for p in (20, 50, 100, 200, 500)] + ["ema_m%d" % m for m in (15, 30, 60, 120, 240)]
CONDS = ("cerca<0.5", "cerca<1", "cerca<2", "sin_limite", "lejos>2_contra")
HS = (10, 50)
NPERM, SEED = 2000, 20261006


def files(suffix):
    out = []
    for r in IN:
        out += glob.glob(str(r / "**" / ("*" + suffix)), recursive=True)
    return sorted(set(out))


def load():
    parts = [pd.read_parquet(f) for f in files("_dir150.parquet")]
    d = pd.concat(parts, ignore_index=True)
    for H in HS:
        tot = d["U%d" % H] + d["D%d" % H]
        d["asim%d" % H] = np.where(tot > 0, (d["U%d" % H] - d["D%d" % H]) / tot, np.nan)
        big, small = np.maximum(d["U%d" % H], d["D%d" % H]), np.minimum(d["U%d" % H], d["D%d" % H])
        d["r3_%d" % H] = (big / np.maximum(small, 1) >= 3)
        d["upbig%d" % H] = d["U%d" % H] > d["D%d" % H]
    return d


def preds(d):
    P = {}
    atr = d.atr.to_numpy()
    for e in EMAS:
        diff = d.close.to_numpy() - d[e].to_numpy()
        s = np.sign(diff); dist = np.abs(diff) / np.maximum(atr, 1e-9)
        P[("P1", e, "cerca<0.5")] = np.where(dist < 0.5, s, 0)
        P[("P1", e, "cerca<1")] = np.where(dist < 1, s, 0)
        P[("P1", e, "cerca<2")] = np.where(dist < 2, s, 0)
        P[("P1", e, "sin_limite")] = s
        P[("P1", e, "lejos>2_contra")] = np.where(dist > 2, -s, 0)
    P[("P2", "vwap", "")] = np.sign(d.close - d.vwap).to_numpy()
    P[("P3", "imb20", "")] = np.sign(d.imb20.fillna(0)).to_numpy()
    P[("P4", "vela", "")] = np.sign(d.close - d.open).to_numpy()
    P[("P5", "mom50", "")] = np.sign(d.mom50.fillna(0)).to_numpy()
    nh = (d.sess_hi - d.close) < 0.5 * d.atr; nl = (d.close - d.sess_lo) < 0.5 * d.atr
    P[("P6", "extremos", "")] = np.where(nh & ~nl, -1, np.where(nl & ~nh, 1, 0))
    return P


def session_sums(d, p, H):
    y = p * d["asim%d" % H].to_numpy()
    ok = np.isfinite(y) & (p != 0)
    g = pd.DataFrame(dict(s=d.session.to_numpy()[ok], y=y[ok]))
    return g.groupby("s").y.agg(["sum", "count"])


def stat_and_se(ss):
    m = ss["sum"].sum() / max(ss["count"].sum(), 1)
    G = len(ss)
    u = ss["sum"] - m * ss["count"]
    se = np.sqrt((u ** 2).sum() * G / max(G - 1, 1)) / max(ss["count"].sum(), 1)
    return float(m), float(se), int(ss["count"].sum())


def run_block(d, P, keys, rng):
    """Estadístico por clave y max-T (signo sorteado por sesión, el mismo sorteo para todas las celdas)."""
    sess = np.unique(d.session.to_numpy())
    W = rng.choice([-1.0, 1.0], size=(NPERM, len(sess)))
    pos = {s: i for i, s in enumerate(sess)}
    obs, nulls, info = [], [], []
    for k in keys:
        pk, H = k[:-1], k[-1]
        ss = session_sums(d, P[pk], H)
        m, se, n = stat_and_se(ss)
        vec_s = np.zeros(len(sess)); vec_c = np.zeros(len(sess))
        ix = np.array([pos[s] for s in ss.index], dtype=int)
        vec_s[ix] = ss["sum"].to_numpy(); vec_c[ix] = ss["count"].to_numpy()
        nul = (W @ vec_s) / max(vec_c.sum(), 1)
        obs.append(m); nulls.append(nul); info.append((m, se, n))
    obs = np.array(obs); N = np.abs(np.vstack(nulls))
    mx = N.max(0)
    res = []
    for i, k in enumerate(keys):
        m, se, n = info[i]
        p_single = float((1 + (N[i] >= abs(obs[i])).sum()) / (1 + NPERM))
        p_max = float((1 + (mx >= abs(obs[i])).sum()) / (1 + NPERM))
        res.append(dict(pred=k[0], var=k[1], cond=k[2], H=k[3], media_signo_asim=m, se=se, n=n,
                        p_perm=p_single, p_maxT=p_max, mde=2.8 * se))
    return res


def holm(rs, key="p_perm"):
    ps = [r[key] for r in rs]; order = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(order):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); rs[i]["p_holm"] = mx
    return rs


def main():
    t0 = time.time()
    d = load()
    print("filas", len(d), "marcas", int(d.vtd.sum()), "contratos", sorted(d.contract.unique()), flush=True)
    rng = np.random.default_rng(SEED)
    E = d[d.vtd & d.rth].reset_index(drop=True)
    C = d[~d.vtd & d.rth].reset_index(drop=True)
    PE, PC = preds(E), preds(C)
    ema_keys = [("P1", e, c, H) for e in EMAS for c in CONDS for H in HS]
    fix_keys = [(p, v, "", H) for (p, v) in (("P2", "vwap"), ("P3", "imb20"), ("P4", "vela"), ("P5", "mom50"), ("P6", "extremos")) for H in HS]
    D_ = E.contract.isin(DISC).to_numpy(); C_ = E.contract.isin(CONF).to_numpy()
    Ed, Ec = E[D_].reset_index(drop=True), E[C_].reset_index(drop=True)
    PEd = {k: v[D_] for k, v in PE.items()}; PEc = {k: v[C_] for k, v in PE.items()}
    # ---- descubrimiento
    disc_ema = run_block(Ed, PEd, ema_keys, rng)
    disc_fix = holm(run_block(Ed, PEd, fix_keys, rng))
    pass_ema = [r for r in disc_ema if r["p_maxT"] <= 0.05]
    pass_fix = [r for r in disc_fix if r["p_holm"] <= 0.05]
    print("descubrimiento: EMA pasan", len(pass_ema), "| fijos pasan", len(pass_fix), flush=True)
    # ---- confirmación (sólo lo que pasó, sin cambios)
    conf_keys = [(r["pred"], r["var"], r["cond"], r["H"]) for r in pass_ema + pass_fix]
    conf = holm(run_block(Ec, PEc, conf_keys, rng)) if conf_keys else []
    # ---- descriptivos: misma métrica en barras al azar (controles) y por régimen de amplitud (todo el período)
    desc = []
    for k in fix_keys + [("P1", "ema_b200", "sin_limite", 10), ("P1", "ema_m60", "sin_limite", 10)]:
        pk, H = k[:-1], k[-1]
        me, see, ne = stat_and_se(session_sums(E, PE[pk], H)); mc, sec, nc = stat_and_se(session_sums(C, PC[pk], H))
        row = dict(pred=k[0], var=k[1], cond=k[2], H=H, marcas=me, se_marcas=see, n_marcas=ne, controles=mc, se_controles=sec, n_controles=nc)
        tr = pd.qcut(E.amp_rel.rank(method="first"), 3, labels=["comprimido", "medio", "expandido"]) if E.amp_rel.notna().sum() > 30 else None
        if tr is not None:
            for lab in ("comprimido", "medio", "expandido"):
                m_ = (tr == lab).to_numpy()
                mm, ss_, nn = stat_and_se(session_sums(E[m_], PE[pk][m_], H))
                row["reg_" + lab] = mm; row["reg_" + lab + "_se"] = ss_
        desc.append(row)
    perf = dict(asim_media_marcas={H: float(E["asim%d" % H].mean()) for H in HS},
                p_ratio3_marcas={H: float(E["r3_%d" % H].mean()) for H in HS},
                p_ratio3_controles={H: float(C["r3_%d" % H].mean()) for H in HS},
                big_media_marcas={H: float(np.maximum(E["U%d" % H], E["D%d" % H]).mean()) for H in HS},
                big_media_controles={H: float(np.maximum(C["U%d" % H], C["D%d" % H]).mean()) for H in HS})
    for r in sorted(disc_ema, key=lambda x: x["p_maxT"])[:15] + disc_fix + conf:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    for r in desc:
        print("DESC", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    print("PERFIL", json.dumps(perf), flush=True)
    res = dict(campaign="VTD-DIR etapa 1", propuesta="docs/research/VTD_DIR_PROPUESTA_20261006.md", descubrimiento=DISC,
               confirmacion=CONF, disc_ema=disc_ema, disc_fijos=disc_fix, confirmacion_res=conf, descriptivo=desc,
               perfil=perf, seconds=round(time.time() - t0))
    (OUT / "VTD_DIR_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
