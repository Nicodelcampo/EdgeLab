#!/usr/bin/env python3
"""BONOS-ROTACION (pre-registro docs/research/bonos_rotacion_20261127/PREREGISTRO.md): la versión swing de la técnica de Gus Lucioni
(«trade un poquito más swing… 2 o 3 días», ratio contra su promedio de 7/15 días, rotación en tandas, nunca todo) con bonos propios
y sin comisión (VetaFLAT), medida como exceso contra mantener 50/50 el par.

  python tools/bonos_rotacion.py correr      # DESC y REP de A5; HOLDOUT sellado

Regla (congelada, de la charla):
- z_t = (ln R_t − media de ln R en las ventanas t−W..t−1) / desvío de esas mismas ventanas; R = GD/AL (cierres en pesos).
- Peso en GD: w_t = 0,5 − 0,3 · clip(z_t / 2, −1, 1)  → 50/50 en el promedio y 80/20 hacia el barato con |z| ≥ 2. Siempre queda un
  20 % en el bono caro («nunca todo») y el paso es gradual («en tandas»).
- Se decide al cierre de t y se ejecuta al cierre de t+1. Gana desde t+1 hasta t+2.
- Exceso diario contra 50/50: (w − 0,5)·(r_GD − r_AL) − |Δw| · (spread_GD + spread_AL)/2 − |Δw| · 2 · 0,01 % (derechos).
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/bonos_rotacion_20261127"; PRE = "docs/research/bonos_rotacion_20261127/PREREGISTRO.md"
DATA = ROOT / "data/bonos_ar"
PARES = {"GD30/AL30": ("GD30", "AL30"), "GD35/AL35": ("GD35", "AL35"), "GD38/AE38": ("GD38", "AE38"), "GD41/AL41": ("GD41", "AL41")}
DERECHOS = 0.0001
ABONO_ARS_MES = {"PRO": 85_000 * 1.21, "ADVANCE": 160_000 * 1.21, "ELITE": 285_000 * 1.21}    # + IVA (vetacap.com.ar/personas, 2026-11)
CUPO = {"PRO": 1.75, "ADVANCE": 2.50, "ELITE": 4.00}


def _spreads() -> dict:
    s = json.loads((DATA / "SPREADS_FOTO.json").read_text())
    return {k: v["spread_pct"] / 100 for k, v in s.items() if not k.startswith("_")}


def _exceso(a: str, b: str, W: int, esc_costo: float = 1.0) -> pd.DataFrame:
    import bonos_ratios as BR
    d = BR._serie(a, b)                                                   # mismos cierres, volumen > 0 y bloques A5 que BONOS-RATIOS
    lr = d.r; mu = lr.shift(1).rolling(W).mean(); sd = lr.shift(1).rolling(W).std()
    z = (lr - mu) / sd; w = (0.5 - 0.3 * (z / 2).clip(-1, 1)).fillna(0.5)
    w_ej = w.shift(1).fillna(0.5)                                         # decidido en t, ejecutado al cierre de t+1
    rg, ra = np.log(d.ga).diff(), np.log(d.gb).diff()
    sp = _spreads(); c_u = esc_costo * ((sp[a] + sp[b]) / 2 + 2 * DERECHOS)
    dw = w_ej.diff().abs().fillna(0.0)
    e = (w_ej.shift(1) - 0.5) * (rg - ra) - dw * c_u                     # la posición ejecutada en t+1 gana desde t+1 → t+2
    sell = (~d.bloque.isin(["DESC", "REP"])).astype(int)
    limpio = (sell.rolling(W + 3).max() == 0)                             # ventana, ejecución y retorno sin meses sellados
    return pd.DataFrame(dict(e=e, dw=dw, w=w_ej, bloque=d.bloque.where(limpio, "SELLADO")))


def _st(x: pd.Series) -> dict:
    from math import erf, sqrt
    m = x.groupby(x.index.to_period("M")).sum(); n = len(m)
    if n < 3 or m.std() == 0: return dict(meses=n)
    t = float(m.mean() / (m.std(ddof=1) / np.sqrt(n)))
    return dict(meses=n, exceso_pct_mes=round(float(m.mean() * 100), 4), t=round(t, 2), p_una_cola=round(0.5 * (1 - erf(t / sqrt(2))), 4),
                sharpe_anual=round(float(m.mean() / m.std(ddof=1) * np.sqrt(12)), 2), pct_meses_pos=round(float((m > 0).mean()), 3))


def correr() -> int:
    from registro_global import exigir_contada
    from edgelab.research.a5 import bh
    exigir_contada(PRE); OUT.mkdir(parents=True, exist_ok=True); res = {"pares": {}}
    canasta = {}
    for W in (15, 7):
        for esc in (1.0, 0.5, 2.0):
            series = {}
            for nom, (a, b) in PARES.items():
                x = _exceso(a, b, W, esc); series[nom] = x
                if esc == 1.0:
                    r = res["pares"].setdefault(nom, {})
                    r[f"W{W}"] = dict(DESC=_st(x.e[x.bloque == "DESC"]), REP=_st(x.e[x.bloque == "REP"]),
                                      rotacion_media_dia=round(float(x.dw[x.bloque.isin(["DESC", "REP"])].mean()), 4),
                                      bruto_DESC=_st((x.e + x.dw * ((_spreads()[a] + _spreads()[b]) / 2 + 2 * DERECHOS))[x.bloque == "DESC"]))
            E = pd.concat({k: v.e.where(v.bloque.isin(["DESC", "REP"])) for k, v in series.items()}, axis=1)
            B = series["GD30/AL30"].bloque
            c = E.mean(axis=1, skipna=True)
            canasta[f"W{W}_costo{esc}"] = dict(DESC=_st(c[B == "DESC"]), REP=_st(c[B == "REP"]))
    res["canasta"] = canasta
    ps = [res["pares"][k]["W15"]["DESC"].get("p_una_cola", 1.0) for k in PARES]
    res["BH_DESC_W15"] = dict(zip(PARES, map(bool, bh(ps, q=0.10))))
    prim = canasta["W15_costo1.0"]
    res["primaria"] = prim
    res["veredicto_DESC"] = "CONFIRMA" if prim["DESC"].get("t", 0) >= 1.645 else ("NO_CONCLUYENTE" if prim["DESC"].get("exceso_pct_mes", 0) > 0 else "EN_CONTRA")
    res["replica_REP"] = bool(prim["REP"].get("t", 0) >= 1.645) if res["veredicto_DESC"] == "CONFIRMA" else None
    # Capital mínimo para pagar el abono (descriptivo): abono / (exceso mensual × cupo de bonos de aire)
    ex = prim["DESC"].get("exceso_pct_mes", 0) / 100
    res["capital_minimo_ARS"] = {p: (round(ABONO_ARS_MES[p] / (ex * CUPO[p])) if ex > 0 else None) for p in ABONO_ARS_MES}
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("primaria", "veredicto_DESC", "replica_REP", "BH_DESC_W15", "capital_minimo_ARS")}, indent=1, default=str))
    for k, v in res["pares"].items(): print(k, v["W15"])
    return 0


if __name__ == "__main__":
    sys.exit({"correr": correr}[sys.argv[1]]())
