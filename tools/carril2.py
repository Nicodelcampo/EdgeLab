#!/usr/bin/env python3
"""CARRIL2-LOTE1: IBS+VIX, Double Seven, Turnaround Tuesday y cambio de mes sobre el motor de barras calibrado
(pre-registro docs/research/carril2_20261119/PREREGISTRO_LOTE1.md).

Reusa `sqx_catalogo.simular` (calibración K28 registrada en config/simuladores_baseline.json) con el camino M1 (`indices_m1`), las barras
`barras_desde_m1(D, "D1")`, los indicadores causales de `sqx_catalogo` (`sma`, `atr`, `roll_min`, `roll_max`), `m1_largo.cargar`, el VIX de
`cboe_volatility_daily.parquet`, `holdout.a5_bloque`, `a5.diferencia`, `a5.bh`, `a5.plan_lectura`, `libro_lord` y la fricción canónica.

  python tools/carril2.py correr     # operaciones de las 8 definiciones (4 reglas + 4 controles) → OPS.csv.gz (sólo DESC/REP, salidas fuera de HOLDOUT)
  python tools/carril2.py desc       # 8 pruebas en DESC, BH q 0,10 → DESC.json (commitear antes de rep)
  python tools/carril2.py rep        # nominadas con potencia en días ≥ 0,8 (K49), una vez con LORD++ → REP.json
  python tools/carril2.py correr|desc|rep 2   # LOTE 2 (PREREGISTRO_LOTE2.md): régimen de volatilidad, Dynamic Breakout II, rotación ES/GC
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/carril2_20261119"; PRE = "docs/research/carril2_20261119/PREREGISTRO_LOTE1.md"
FAM = "CARRIL2_A5"; FIN = 20250731; LOTE2 = False   # LOTE2: fuerza el lote 2 cuando PRE es de otra corrida (carril2_extension)
INST = {"C2_IBS": ("ES", "NQ", "YM", "RTY"), "C2_D7": ("ES", "NQ", "YM", "RTY", "GC"), "C2_TT": ("ES", "NQ", "YM", "RTY"), "C2_TOM": ("ES", "NQ", "YM", "RTY")}
REGLAS = ("C2_IBS", "C2_D7", "C2_TT", "C2_TOM")
LOTE = dict(pre=PRE, ops="OPS.csv.gz", desc="DESC.json", rep="REP.json", etiqueta="REP_CARRIL2_LOTE1")
INST2 = {"C2_VBB": ("ES", "NQ", "YM"), "C2_P80": ("ES", "NQ", "YM"), "C2_EVRP": ("ES", "NQ"), "C2_VZ": ("ES", "NQ"), "C2_DBO": ("GC", "ES", "NQ"),
         "C2_ROT": ("ES", "GC")}


def _lote2():
    global PRE, INST, REGLAS
    PRE = "docs/research/carril2_20261119/PREREGISTRO_LOTE2.md"; INST = INST2; REGLAS = tuple(INST2)
    LOTE.update(pre=PRE, ops="OPS_LOTE2.csv.gz", desc="DESC_LOTE2.json", rep="REP_LOTE2.json", etiqueta="REP_CARRIL2_LOTE2")


def _vol(V, B, col):
    x = V[col].copy(); x.index = pd.to_datetime(x.index).normalize()
    x = x.reindex(x.index.union(pd.to_datetime(B.fecha.astype(str)))).ffill()     # último cierre CBOE conocido (sesiones CME sin CBOE)
    return x.reindex(pd.to_datetime(B.fecha.astype(str))).to_numpy(float)          # cierre CBOE del día t (16:15 NY < cierre de la barra 17:00)


def _dbo_lookback(c, fijo=None):
    n = len(c); sd = pd.Series(c).rolling(30).std().to_numpy(); lb = np.full(n, 20, int)
    if fijo: return np.full(n, fijo, int)
    for i in range(1, n):
        lb[i] = lb[i - 1]
        if np.isfinite(sd[i]) and np.isfinite(sd[i - 1]) and sd[i - 1] > 0:
            lb[i] = int(np.clip(round(lb[i - 1] * (1 + (sd[i] - sd[i - 1]) / sd[i - 1])), 20, 60))
    return lb


def _dbo(B, fijo=None):
    from edgelab.research import sqx_catalogo as Q
    h, l, c = (B[k].to_numpy(float) for k in "hlc"); n = len(c); a20 = Q.atr(h, l, c, 20); lb = _dbo_lookback(c, fijo)
    lado = np.zeros(n, int); media = np.full(n, np.nan)
    for i in range(61, n):
        k = lb[i]; w = c[i - k + 1:i + 1]; m, s = w.mean(), w.std(ddof=0); media[i] = m
        if c[i] > m + 2 * s and c[i] > h[i - k:i].max(): lado[i] = 1
        elif c[i] < m - 2 * s and c[i] < l[i - k:i].min(): lado[i] = -1
    return dict(lado=lado, tipo="mkt", sl=1.50 * a20, tp=np.nan, salida=lambda i, ld: (c[i] < media[i]) if ld == 1 else (c[i] > media[i]))


def _senales2(B, inst, V, mens):
    """Lote 2 (largos salvo DBO). VIX para ES/YM, VXN para NQ (pre-registro §1)."""
    from edgelab.research import sqx_catalogo as Q
    h, l, c = (B[k].to_numpy(float) for k in "hlc"); a20 = Q.atr(h, l, c, 20); n = len(c); f = B.fecha.to_numpy()
    iv = _vol(V, B, "vxn_close" if inst == "NQ" else "vix_close"); v9 = _vol(V, B, "vix9d_close"); vx = _vol(V, B, "vix_close")
    S = pd.Series(iv); m20, s20 = S.rolling(20).mean().to_numpy(), S.rolling(20).std().to_numpy()
    p80, p10 = S.rolling(504).quantile(0.80).to_numpy(), S.rolling(504).quantile(0.10).to_numpy()
    rv10 = pd.Series(np.log(c)).diff().rolling(10).std().to_numpy() * np.sqrt(252) * 100; evrp = iv - rv10; cont = v9 / vx
    z = lambda x: ((pd.Series(x) - pd.Series(x).rolling(6).mean()) / pd.Series(x).rolling(6).std()).to_numpy()
    cz = (z(iv) + z(v9)) / 2
    with np.errstate(invalid="ignore"):
        dos_alzas = lambda i, ld: c[i] > c[i - 1] > c[i - 2]
        out = {
            "C2_VBB": dict(lado=(iv > m20 + 2 * s20).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=dos_alzas, tope=10),
            "C2_VBBN": dict(lado=(iv < m20 - 1 * s20).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=dos_alzas, tope=10),
            "C2_P80": dict(lado=(iv > p80).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=lambda i, ld: not iv[i] > p80[i], tope=10),
            "C2_P80N": dict(lado=(iv < p10).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=lambda i, ld: not iv[i] < p10[i], tope=10),
            "C2_EVRP": dict(lado=((evrp > 0) & (cont < 1)).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan,
                            salida=lambda i, ld: not (evrp[i] > 0 and cont[i] < 1), tope=20),
            "C2_EVRPN": dict(lado=((evrp > 0) & (cont >= 1)).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan,
                             salida=lambda i, ld: not (evrp[i] > 0 and cont[i] >= 1), tope=20),
            "C2_VZ": dict(lado=(cz < -1).astype(int), tipo="mkt", sl=1.25 * a20, tp=np.nan, salida=lambda i, ld: not cz[i] < -1, tope=10),
            "C2_VZN": dict(lado=(cz > 1).astype(int), tipo="mkt", sl=1.25 * a20, tp=np.nan, salida=lambda i, ld: not cz[i] > 1, tope=10),
            "C2_DBO": _dbo(B), "C2_DBON": _dbo(B, fijo=20),
        }
    mes = f // 100; ultimo = np.r_[mes[1:] != mes[:-1], True]           # última barra del mes (calendario conocido de antemano)
    r = mens.reindex(mes).to_numpy(float)                                 # razón ES/GC y su SMA de 20 meses, al cierre de ese mes
    es_arriba = r > mens.attrs["sma"].reindex(mes).to_numpy(float)
    quiere = es_arriba if inst == "ES" else ~es_arriba; ok = np.isfinite(r) & np.isfinite(mens.attrs["sma"].reindex(mes).to_numpy(float))
    sal_mes = lambda i, ld: bool(ultimo[i])
    out["C2_ROT"] = dict(lado=(ultimo & ok & quiere).astype(int), tipo="mkt", sl=3.0 * a20, tp=np.nan, salida=sal_mes, tope=30)
    out["C2_ROTN"] = dict(lado=(ultimo & ok & ~quiere).astype(int), tipo="mkt", sl=3.0 * a20, tp=np.nan, salida=sal_mes, tope=30)
    return out


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
    lote2 = PRE.endswith("LOTE2.md") or LOTE2; bars, mens = {}, None
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); vc = V.vix_close.copy(); vc.index = pd.to_datetime(vc.index).normalize()
    vix_reg = (vc > vc.rolling(100).mean()).shift(1)                    # VIX(t−1) > SMA100(t−1)
    partes = []
    if lote2:                                        # razón mensual ES/GC (último cierre del mes de cada uno) y su SMA de 20 meses
        cm = {k: Q.barras_desde_m1(cargar(k, ruta("M1NT8")), "D1").assign(mes=lambda b: b.fecha // 100).groupby("mes").c.last() for k in ("ES", "GC")}
        mens = (cm["ES"] / cm["GC"]).dropna(); mens.attrs["sma"] = mens.rolling(20).mean()
    for inst in sorted({i for v in INST.values() for i in v}):
        D = cargar(inst, ruta("M1NT8")); B = Q.barras_desde_m1(D, "D1"); m1 = Q.indices_m1(B, D, "D1")
        vix_ok = vix_reg.reindex(pd.to_datetime(B.fecha.astype(str))).fillna(False).to_numpy(bool)
        S = _senales2(B, inst, V, mens) if lote2 else _senales(B, vix_ok); fr = float(friccion(inst)[0]); f = B.fecha.to_numpy()
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
    vacias = [d for r in REGLAS for d in (r, r + "N") if not (T.definicion == d).any()]
    if vacias: raise SystemExit(f"K53: definiciones sin disparos {vacias}")
    T.to_csv(DIR / LOTE["ops"], index=False); print(T.groupby(["definicion", "bloque"]).size().unstack().to_string())


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
    T = pd.read_csv(DIR / LOTE["ops"]); res = _pruebas(T, "DESC"); k = list(res); rech = bh([res[x]["p"] for x in k], 0.10)
    for x, b in zip(k, rech): res[x]["bh"] = bool(b)
    nom = [x for x in k if res[x]["bh"] and ("-" in x or (res[x]["R"] > 0 and res[x]["fricR_med"] <= 0.08))]
    (DIR / LOTE["desc"]).write_text(json.dumps(dict(preregistro=PRE, resultados=res, nominadas=nom), indent=1, default=float))
    for x in k: print(x, {y: round(v, 3) if isinstance(v, float) else v for y, v in res[x].items()})
    print("nominadas", nom)


def rep():
    from a5_campana import _commiteado
    from edgelab.research import a5 as A5
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / LOTE["desc"]): raise SystemExit(f"{LOTE['desc']} sin commitear")
    T = pd.read_csv(DIR / LOTE["ops"]); nom = json.loads((DIR / LOTE["desc"]).read_text())["nominadas"]; planes = {}
    for x in nom:
        r = x.split("-")[0]; g = T[(T.definicion == r) & (T.bloque == "DESC")]
        n_rep = int(T[(T.definicion == r) & (T.bloque == "REP")].fecha.nunique())              # sólo cuenta sesiones
        planes[x] = A5.plan_lectura(FAM, g.fecha.to_numpy(), g.R.to_numpy(float), n_rep)
    con = [x for x in nom if (planes[x].get("potencia") or 0) >= A5.POTENCIA_LECTURA_MIN]
    out = {x: dict(plan=planes[x], estado="SIN_POTENCIA_PREVIA") for x in nom if x not in con}
    if con:
        res = _pruebas(T, "REP"); dec = LibroLord().probar(FAM, LOTE["etiqueta"], [(x, res[x]["p"]) for x in con])
        for x in con: out[x] = dict(plan=planes[x], rep=res[x], confirmada=x in (dec.get("confirmadas") or []))
        out["lord"] = dec
    (DIR / LOTE["rep"]).write_text(json.dumps(out, indent=1, default=float))
    for x, v in out.items():
        if x != "lord": print(x, v.get("estado", ""), "potencia", round(v["plan"].get("potencia") or 0, 3), v.get("confirmada"))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "2": _lote2()
    {"correr": correr, "desc": desc, "rep": rep}[sys.argv[1]]()
