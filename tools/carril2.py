#!/usr/bin/env python3
"""CARRIL2-LOTE1: IBS+VIX, Double Seven, Turnaround Tuesday y cambio de mes sobre el motor de barras calibrado
(pre-registro docs/research/carril2_20261119/PREREGISTRO_LOTE1.md).

Reusa `sqx_catalogo.simular` (calibración K28 registrada en config/simuladores_baseline.json) con el camino M1 (`indices_m1`), las barras
`barras_desde_m1(D, "D1")`, los indicadores causales de `sqx_catalogo` (`sma`, `atr`, `roll_min`, `roll_max`), `m1_largo.cargar`, el VIX de
`cboe_volatility_daily.parquet`, `holdout.a5_bloque`, `a5.diferencia`, `a5.bh`, `a5.plan_lectura`, `libro_lord` y la fricción canónica.

  python tools/carril2.py correr     # operaciones de las 8 definiciones (4 reglas + 4 controles) → OPS.csv.gz (sólo DESC/REP, salidas fuera de HOLDOUT)
  python tools/carril2.py desc       # 8 pruebas en DESC, BH q 0,10 → DESC.json (commitear antes de rep)
  python tools/carril2.py rep        # nominadas con potencia en días ≥ 0,8 (K49), una vez con LORD++ → REP.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/carril2_20261119"; PRE = "docs/research/carril2_20261119/PREREGISTRO_LOTE1.md"
FAM = "CARRIL2_A5"; FIN = 20250731
INST = {"C2_IBS": ("ES", "NQ", "YM", "RTY"), "C2_D7": ("ES", "NQ", "YM", "RTY", "GC"), "C2_TT": ("ES", "NQ", "YM", "RTY"), "C2_TOM": ("ES", "NQ", "YM", "RTY")}
REGLAS = ("C2_IBS", "C2_D7", "C2_TT", "C2_TOM")


def _senales(B, vix_ok):
    from edgelab.research import sqx_catalogo as Q
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a20 = Q.atr(h, l, c, 20); n = len(c)
    ibs = (c - l) / np.maximum(h - l, 1e-9); hprev = Q.sh(h); cprev = Q.sh(c)
    s200 = Q.sma(c, 200); mn7, mx7 = Q.roll_min(c, 7), Q.roll_max(c, 7); dow = B.dow.to_numpy(); f = B.fecha.to_numpy()
    mes = f // 100; pos_desde_fin = np.zeros(n, int); pos_desde_ini = np.zeros(n, int)
    for m in np.unique(mes):                       # calendario hábil del mes (feriados conocidos de antemano)
        ix = np.flatnonzero(mes == m); pos_desde_ini[ix] = np.arange(1, len(ix) + 1); pos_desde_fin[ix] = np.arange(len(ix), 0, -1)
    sal_ibs = lambda i, lado: (ibs[i] > 0.80) or (c[i] > h[i - 1])
    sal_tt = lambda i, lado: c[i] > h[i - 1]
    sal_d7 = lambda i, lado: c[i] >= mx7[i]
    lado = lambda m: m.astype(int)
    return {
        "C2_IBS": dict(lado=lado((ibs < 0.20) & vix_ok), tipo="mkt", sl=1.50 * a20, tp=np.nan, salida=sal_ibs, tope=10),
        "C2_IBSN": dict(lado=lado((ibs > 0.80) & vix_ok), tipo="mkt", sl=1.50 * a20, tp=np.nan, salida=sal_ibs, tope=10),
        "C2_D7": dict(lado=lado((c > s200) & (c <= mn7)), tipo="mkt", sl=1.75 * a20, tp=np.nan, salida=sal_d7),
        "C2_D7N": dict(lado=lado((c < s200) & (c <= mn7)), tipo="mkt", sl=1.75 * a20, tp=np.nan, salida=sal_d7),
        "C2_TT": dict(lado=lado((dow == 0) & (c < cprev) & (ibs < 0.50)), tipo="mkt", sl=1.50 * a20, tp=np.nan, salida=sal_tt, tope=4),
        "C2_TTN": dict(lado=lado((dow == 0) & (ibs > 0.80)), tipo="mkt", sl=1.50 * a20, tp=np.nan, salida=sal_tt, tope=4),
        "C2_TOM": dict(lado=lado(pos_desde_fin == 5), tipo="mkt", sl=2.00 * a20, tp=np.nan, tope=8),
        "C2_TOMN": dict(lado=lado(pos_desde_ini == 4), tipo="mkt", sl=2.00 * a20, tp=np.nan, tope=8),
    }


def correr():
    from registro_global import exigir_contada
    from datos import ruta
    from m1_largo import cargar
    from edgelab.research import sqx_catalogo as Q
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import a5_bloque
    exigir_contada(PRE)
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); vc = V.vix_close.copy(); vc.index = pd.to_datetime(vc.index).normalize()
    vix_reg = (vc > vc.rolling(100).mean()).shift(1)                    # VIX(t−1) > SMA100(t−1)
    partes = []
    for inst in sorted({i for v in INST.values() for i in v}):
        D = cargar(inst, ruta("M1NT8")); B = Q.barras_desde_m1(D, "D1"); m1 = Q.indices_m1(B, D, "D1")
        vix_ok = vix_reg.reindex(pd.to_datetime(B.fecha.astype(str))).fillna(False).to_numpy(bool)
        S = _senales(B, vix_ok); fr = float(friccion(inst)[0]); f = B.fecha.to_numpy()
        for d, sig in S.items():
            regla = d[:-1] if d.endswith("N") and d[:-1] in REGLAS else d
            if inst not in INST[regla]: continue
            O = Q.simular(B, sig, viernes=False, m1=m1)
            if not len(O): continue
            rg = (O.entrada - O.stop0).abs(); O["R"] = (O.lado * (O.salida_px - O.entrada) - fr) / rg; O["Rb"] = O.lado * (O.salida_px - O.entrada) / rg
            O["fricR"] = fr / rg; O["fecha_salida"] = f[np.minimum(O.i0 + O.barras - 1, len(f) - 1)]
            O["definicion"], O["inst"] = d, inst; partes.append(O[O.stop0.notna() & (rg > 0)])
        print(inst, flush=True)
    T = pd.concat(partes, ignore_index=True)
    bl = {int(x): a5_bloque(int(x)) for x in pd.unique(np.r_[T.fecha.to_numpy(), T.fecha_salida.to_numpy()])}
    T["bloque"] = T.fecha.map(bl); T["bloque_salida"] = T.fecha_salida.map(bl)
    T = T[(T.fecha_salida <= FIN) & T.bloque.isin(["DESC", "REP"]) & ~T.bloque_salida.isin(["HOLDOUT", "EMBARGO"])]
    assert not T.bloque_salida.isin(["HOLDOUT", "EMBARGO"]).any()        # ninguna operación evaluada lee precios sellados
    T.to_csv(DIR / "OPS.csv.gz", index=False); print(T.groupby(["definicion", "bloque"]).size().unstack().to_string())


def _media(f, r, B=2000, seed=7):
    """R medio y p unilateral (> 0) con bootstrap por sesión."""
    from edgelab.research.a5 import sf
    s = pd.DataFrame(dict(f=f, r=r)).groupby("f").r.agg(["sum", "count"]).to_numpy(float); rng = np.random.default_rng(seed)
    bs = np.array([(lambda x: x[:, 0].sum() / x[:, 1].sum())(s[rng.integers(0, len(s), len(s))]) for _ in range(B)])
    m = s[:, 0].sum() / s[:, 1].sum(); se = float(bs.std(ddof=1)); return float(m), se, float(sf(m / se)) if se > 0 else 1.0


def _pruebas(T, bloque):
    from edgelab.research import a5 as A5
    res = {}
    for r in REGLAS:
        g = T[(T.definicion == r) & (T.bloque == bloque)]; gc = T[(T.definicion == r + "N") & (T.bloque == bloque)]
        m, se, p = _media(g.fecha.to_numpy(), g.R.to_numpy()); res[r] = dict(n=int(len(g)), R=m, se=se, p=p, Rb=float(g.Rb.mean()), fricR_med=float(g.fricR.median()),
                                                                             ops_mes=float(len(g) / max(g.fecha.floordiv(100).nunique(), 1)))
        d, se2, p2 = A5.diferencia(g.fecha.to_numpy(), g.R.to_numpy(), gc.fecha.to_numpy(), gc.R.to_numpy())
        res[f"{r}-{r}N"] = dict(dif=d, se=se2, p=p2, R_control=float(gc.R.mean()), n_control=int(len(gc)))
    return res


def desc():
    from edgelab.research.a5 import bh
    T = pd.read_csv(DIR / "OPS.csv.gz"); res = _pruebas(T, "DESC"); k = list(res); rech = bh([res[x]["p"] for x in k], 0.10)
    for x, b in zip(k, rech): res[x]["bh"] = bool(b)
    nom = [x for x in k if res[x]["bh"] and ("-" in x or (res[x]["R"] > 0 and res[x]["fricR_med"] <= 0.08))]
    (DIR / "DESC.json").write_text(json.dumps(dict(preregistro=PRE, resultados=res, nominadas=nom), indent=1, default=float))
    for x in k: print(x, {y: round(v, 3) if isinstance(v, float) else v for y, v in res[x].items()})
    print("nominadas", nom)


def rep():
    from a5_campana import _commiteado
    from edgelab.research import a5 as A5
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / "DESC.json"): raise SystemExit("DESC.json sin commitear")
    T = pd.read_csv(DIR / "OPS.csv.gz"); nom = json.loads((DIR / "DESC.json").read_text())["nominadas"]; planes = {}
    for x in nom:
        r = x.split("-")[0]; g = T[(T.definicion == r) & (T.bloque == "DESC")]
        n_rep = int(T[(T.definicion == r) & (T.bloque == "REP")].fecha.nunique())              # sólo cuenta sesiones
        planes[x] = A5.plan_lectura(FAM, g.fecha.to_numpy(), g.R.to_numpy(float), n_rep)
    con = [x for x in nom if (planes[x].get("potencia") or 0) >= A5.POTENCIA_LECTURA_MIN]
    out = {x: dict(plan=planes[x], estado="SIN_POTENCIA_PREVIA") for x in nom if x not in con}
    if con:
        res = _pruebas(T, "REP"); dec = LibroLord().probar(FAM, "REP_CARRIL2_LOTE1", [(x, res[x]["p"]) for x in con])
        for x in con: out[x] = dict(plan=planes[x], rep=res[x], confirmada=x in (dec.get("confirmadas") or []))
        out["lord"] = dec
    (DIR / "REP.json").write_text(json.dumps(out, indent=1, default=float))
    for x, v in out.items():
        if x != "lord": print(x, v.get("estado", ""), "potencia", round(v["plan"].get("potencia") or 0, 3), v.get("confirmada"))


if __name__ == "__main__":
    {"correr": correr, "desc": desc, "rep": rep}[sys.argv[1]]()
