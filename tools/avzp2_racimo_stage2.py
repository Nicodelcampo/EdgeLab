#!/usr/bin/env python3
"""AVZP2-RACIMO análisis (manifiesto docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md).
5 pruebas formales (Holm): O1 continuación, O2 seguimiento, O3b rebote en retest, O4 duración, O5 expansión.
Real vs pseudo apareado por ocupación, FE contrato×franja + decil de ocupación + tercil de amplitud, SE por sesión.
Descriptivos para diseño. Confirmación (09-26, 12-26) sólo para lo que pase."""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avzp2_rebote_stage2 import absorb  # noqa: E402
from scipy.stats import norm  # noqa: E402

IN = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else IN
CONF = ("MNQ_09-26", "MNQ_12-26")


def beta(d, y, extra=()):
    """extra: columnas adicionales de FE (p. ej. deciles de magnitud de tendencia, auditoría de O1)."""
    ok = np.isfinite(y)
    d, y = d[ok], y[ok]
    f = (d.kind == "real").to_numpy()
    Z = absorb(np.column_stack([f.astype(float), y]),
               [(d.contract + "|" + d.clock.astype(str)).to_numpy(), d.occD.to_numpy(), d.ampT.to_numpy()]
               + [d[c].to_numpy() for c in extra])
    e, Y = Z[:, 0], Z[:, 1]
    ee = e @ e; b = (e @ Y) / ee; U = Y - e * b
    sid = pd.factorize(d.session.to_numpy())[0]; G = sid.max() + 1
    S = np.bincount(sid, weights=e * U, minlength=G)
    se = float(np.sqrt((S ** 2).sum() * G / (G - 1)) / ee)
    return dict(beta=float(b), se=se, z=float(b / se), p=float(2 * (1 - norm.cdf(abs(b / se)))), mde=2.8 * se,
                media_real=float(y[f].mean()), media_pseudo=float(y[~f].mean()), n_real=int(f.sum()), n_pseudo=int((~f).sum()),
                n_sesiones=int(G))


def prep(t):
    t = t.copy()
    t["occD"] = pd.qcut(t.occ.rank(method="first"), 10, labels=False)
    t["ampT"] = pd.qcut(t.amp.fillna(t.amp.median()).rank(method="first"), 3, labels=False)
    out = t.te >= 0
    t["y_O1"] = np.where(out & (t.trend != 0), (t.dir == t.trend).astype(float), np.nan)
    t["y_O2"] = np.where(t.o2 >= 0, (t.o2 == 1).astype(float), np.nan)
    t["y_O3a"] = np.where(out, t.o3a.astype(float), np.nan)
    t["y_O3b"] = np.where(t.o3b >= 0, (t.o3b == 1).astype(float), np.nan)
    t["y_O4"] = t.o4
    t["y_O5"] = t.o5
    if "trend_h" in t:                       # auditoría de O1: magnitud de la tendencia (signo ya está en O1)
        t["trD"] = pd.qcut(t.trend_h.abs().rank(method="first"), 10, labels=False)
        t["moD"] = pd.qcut((t.mom100_h * np.sign(t.trend_h).replace(0, 1)).rank(method="first"), 10, labels=False)
    return t


def descr(t):
    r = t[t.kind == "real"]
    o = r[r.te >= 0]
    q = lambda s: {str(k): round(float(v), 3) for k, v in s.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).items()}
    return dict(
        racimos=int(len(r)), sesiones=int(r.session.nunique()), racimos_por_sesion=round(len(r) / max(1, r.session.nunique()), 2),
        altura_ticks=q(r.h), ocupacion_previa=q(r.occ),
        posicion_en_t0={"dentro": float((r.pos == 0).mean()), "arriba": float((r.pos == 1).mean()), "abajo": float((r.pos == -1).mean())},
        sale_en_la_sesion=float((r.te >= 0).mean()),
        velas_hasta_salir=q(np.exp(o.o4)),
        salida_a_favor_de_tendencia=float((o.dir == o.trend)[o.trend != 0].mean()),
        salida_arriba=float((o.dir == 1).mean()),
        excursion_tras_salida_en_alturas=q(o.mx_h),
        seguimiento_1_altura=float((o.o2 == 1)[o.o2 >= 0].mean()),
        retest=float(o.o3a.mean()), rebote_en_retest=float((o.o3b == 1)[o.o3b >= 0].mean()),
        expansion_log=q(o.o5.dropna()),
    )


def main():
    t = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(IN / "**" / "*_avzp2rac.parquet"), recursive=True))], ignore_index=True)
    print("contratos", sorted(t.contract.unique()), "filas", len(t))
    D = prep(t[~t.contract.isin(CONF)])
    out = {"descubrimiento": {}, "descriptivo_O3a": None}
    for k in ("O1", "O2", "O3b", "O4", "O5"):
        out["descubrimiento"][k] = beta(D, D["y_" + k].to_numpy(float))
    out["descriptivo_O3a"] = beta(D, D["y_O3a"].to_numpy(float))
    ps = sorted(out["descubrimiento"], key=lambda k: out["descubrimiento"][k]["p"]); mx = 0.0
    for r, k in enumerate(ps):
        mx = max(mx, min(1.0, (len(ps) - r) * out["descubrimiento"][k]["p"])); out["descubrimiento"][k]["p_holm"] = mx
    out["descriptivos_diseno_real"] = descr(D)
    out["descriptivos_diseno_pseudo"] = descr(D.assign(kind=np.where(D.kind == "pseudo", "real", "x")))
    out["por_posicion_en_t0"] = {str(p): beta(D[D.pos == p], D[D.pos == p]["y_O1"].to_numpy(float)) for p in (0,) if (D.pos == p).sum() > 50}
    pasan = [k for k, v in out["descubrimiento"].items() if v["p_holm"] <= 0.05]
    out["pasan"] = pasan
    if pasan and t.contract.isin(CONF).any():
        C = prep(t[t.contract.isin(CONF)])
        res = {k: beta(C, C["y_" + k].to_numpy(float)) for k in pasan}
        ps = sorted(res, key=lambda k: res[k]["p"]); mx = 0.0
        for r, k in enumerate(ps):
            mx = max(mx, min(1.0, (len(ps) - r) * res[k]["p"])); res[k]["p_holm"] = mx
            res[k]["confirma"] = bool(mx <= 0.05 and np.sign(res[k]["beta"]) == np.sign(out["descubrimiento"][k]["beta"]))
        out["confirmacion"] = res
    (OUT / "AVZP2_RACIMO_RESULTADOS.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for k, v in out["descubrimiento"].items():
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()})
    print("O3a", {a: (round(b, 4) if isinstance(b, float) else b) for a, b in out["descriptivo_O3a"].items()})
    for k, v in out.get("confirmacion", {}).items():
        print("CONF", k, v)
    print(json.dumps(out["descriptivos_diseno_real"], indent=0))


if __name__ == "__main__":
    main()
