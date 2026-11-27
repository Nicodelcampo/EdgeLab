#!/usr/bin/env python3
"""CONFIANZA-SIN-FORWARD (pre-registro docs/research/confianza_sin_forward_20261127/PREREGISTRO.md): subir o bajar la confianza en
Carril 2 sin esperar forward, con datos que nadie miró para estas reglas.

  python tools/confianza_sin_forward.py bajar      # diarios de Yahoo (índices extranjeros, EE. UU. cash, ^VIX) → data/confianza_sf/
  python tools/confianza_sin_forward.py correr     # H1 transferencia a índices extranjeros, H2 EE. UU. 1990–2005, H3 placebo regla − control
  python tools/confianza_sin_forward.py dsr        # Sharpe deflactado y recorte de Harvey-Liu (descriptivo, sin pruebas nuevas)

Reusa sin cambios las reglas de `tools/carril2.py` (`_senales`, `_senales2`), el motor calibrado `sqx_catalogo.simular` (sin M1: peor caso,
stop antes que objetivo) y `canasta_amplia` para la canasta sellada. Nada desde 2026-10-01.
"""
import hashlib, json, sys, urllib.request
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DATA = ROOT / "data/confianza_sf"; OUT = ROOT / "docs/research/confianza_sin_forward_20261127"; PRE = "docs/research/confianza_sin_forward_20261127/PREREGISTRO.md"
CORTE = pd.Timestamp("2026-10-01")
EXTRANJEROS = {"^GDAXI": "DAX", "^FTSE": "FTSE", "^FCHI": "CAC", "^STOXX50E": "EuroStoxx", "^N225": "Nikkei", "^HSI": "HangSeng",
               "^AXJO": "ASX200", "^GSPTSE": "TSX"}
EEUU = {"^GSPC": "SP500", "^NDX": "Nasdaq100", "^DJI": "Dow", "^RUT": "Russell2000"}
REGLAS = ("C2_IBS", "C2_D7", "C2_TT", "C2_TOM", "C2_VBB")          # ROT queda afuera: es la razón ES/GC, propia de esos dos contratos
COSTO_BPS = {"base": 3.0, "estres": 6.0}                           # ida y vuelta, ESTIMADO y declarado (K34): no hay componente canónico


def _yahoo(sym: str) -> tuple[pd.DataFrame, str]:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?period1=631152000"
           f"&period2={int(CORTE.timestamp())}&interval=1d")
    b = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
    j = json.loads(b)["chart"]["result"][0]; q = j["indicators"]["quote"][0]; off = int(j["meta"].get("gmtoffset", 0))
    idx = (pd.to_datetime(j["timestamp"], unit="s") + pd.Timedelta(seconds=off)).normalize()
    D = pd.DataFrame(dict(o=q["open"], h=q["high"], l=q["low"], c=q["close"], v=q.get("volume") or 0), index=idx).dropna(subset=["o", "h", "l", "c"])
    return D[~D.index.duplicated(keep="last") & (D.index < CORTE)], hashlib.sha256(b).hexdigest()


def bajar() -> int:
    DATA.mkdir(parents=True, exist_ok=True); proc = {}
    for s in {**EXTRANJEROS, **EEUU, "^VIX": "VIX"}:
        D, sha = _yahoo(s); nombre = {**EXTRANJEROS, **EEUU, "^VIX": "VIX"}[s]; D.to_parquet(DATA / f"{nombre}.parquet")
        proc[nombre] = dict(simbolo=s, desde=str(D.index[0].date()), hasta=str(D.index[-1].date()), n=len(D), sha256_respuesta=sha)
        print(nombre, proc[nombre], flush=True)
    (DATA / "PROCEDENCIA.json").write_text(json.dumps(dict(fuente="query1.finance.yahoo.com v8 chart (OHLC sin ajustar)", archivos=proc), indent=1))
    return 0


def _barras(nombre: str) -> pd.DataFrame:
    """D1 con calidad mínima: se descartan las barras con rango nulo (h == l, típicas de series viejas de Yahoo) y el índice empieza el
    primer mes desde el que ≥ 95 % de las barras tienen rango (declarado en el pre-registro)."""
    D = pd.read_parquet(DATA / f"{nombre}.parquet"); D = D[(D.h >= D.l) & (D.h >= D.c) & (D.l <= D.c) & (D.c > 0)]
    ok = (D.h > D.l).groupby(D.index.to_period("M")).mean()
    desde = next((p for p in ok.index if ok.loc[p:].min() >= 0.95), None)
    D = D[(D.index.to_period("M") >= desde) & (D.h > D.l)] if desde is not None else D.iloc[0:0]
    B = D[["o", "h", "l", "c", "v"]].copy(); B["fecha"] = np.asarray(B.index.strftime("%Y%m%d"), dtype=np.int64); B["dow"] = B.index.dayofweek
    return B[B.dow < 5]


def _vol_df(B: pd.DataFrame) -> pd.DataFrame:
    """VIX diario de Yahoo con las columnas que piden las reglas (vix_close / vxn_close): VBB usa el de ES/YM (VIX)."""
    V = pd.read_parquet(DATA / "VIX.parquet")[["c"]].rename(columns={"c": "vix_close"}); V["vxn_close"] = V.vix_close; V["vix9d_close"] = V.vix_close
    return V


def _operar(B: pd.DataFrame, regla_set, costo_bps: float) -> pd.DataFrame:
    import carril2 as C2
    from edgelab.research import sqx_catalogo as Q
    V = _vol_df(B); vc = V.vix_close.copy(); vix_reg = (vc > vc.rolling(100).mean()).shift(1)
    vix_ok = vix_reg.reindex(pd.to_datetime(B.fecha.astype(str))).ffill().fillna(False).to_numpy(bool)
    mens = pd.Series(dtype=float); mens.attrs["sma"] = pd.Series(dtype=float)      # ROT no se usa: razón ES/GC vacía
    S = {**C2._senales(B, vix_ok), **{k: v for k, v in C2._senales2(B, "ES", V, mens).items() if k.startswith("C2_VBB")}}
    f = B.fecha.to_numpy(); partes = []
    for d, sig in S.items():
        regla = d[:-1] if d.endswith("N") else d
        if regla not in regla_set: continue
        O = Q.simular(B, sig, viernes=False)
        if not len(O): continue
        rg = (O.entrada - O.stop0).abs(); fr = O.entrada * costo_bps / 1e4
        O["R"] = (O.lado * (O.salida_px - O.entrada) - fr) / rg; O["Rb"] = O.lado * (O.salida_px - O.entrada) / rg; O["fricR"] = fr / rg
        O["definicion"] = d; partes.append(O[O.stop0.notna() & (rg > 0)])
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def _canasta(T: pd.DataFrame, solo_reglas=True) -> pd.Series:
    """R mensual de la canasta: suma de R por serie (regla-índice) y mes, promedio entre las series con datos ese mes."""
    T = T[~T.definicion.str.endswith("N")] if solo_reglas else T
    m = T.assign(mes=pd.to_datetime(T.fecha.astype(str)).dt.to_period("M")).pivot_table(index="mes", columns="serie", values="R", aggfunc="sum")
    return m.fillna(0.0).where(m.notna().cumsum() > 0).mean(axis=1).dropna()


def _t(x: pd.Series) -> dict:
    x = x.dropna(); n = len(x); mu, sd = float(x.mean()), float(x.std(ddof=1))
    from math import erf, sqrt
    t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
    return dict(meses=n, media=round(mu, 4), sharpe_anual=round(mu / sd * np.sqrt(12), 3) if sd > 0 else 0.0, t=round(t, 2),
                p_una_cola=round(0.5 * (1 - erf(t / sqrt(2))), 4), pct_meses_pos=round(float((x > 0).mean()), 3))


def _veredicto(s: dict) -> str:
    return "CONFIRMA" if s["t"] >= 1.645 else ("NO_CONCLUYENTE" if s["media"] > 0 else "EN_CONTRA")


def _universo(nombres: dict, hasta=None) -> dict:
    out = {}
    for esc, bps in COSTO_BPS.items():
        partes = []
        for nombre in nombres.values():
            B = _barras(nombre)
            if hasta is not None: B = B[B.fecha <= hasta]
            if len(B) < 300: continue
            T = _operar(B, REGLAS, bps)
            if len(T): partes.append(T.assign(indice=nombre, serie=lambda d: d.definicion + "_" + nombre))
        out[esc] = pd.concat(partes, ignore_index=True)
    return out


def correr() -> int:
    from registro_global import exigir_contada
    exigir_contada(PRE); OUT.mkdir(parents=True, exist_ok=True); res = {}
    # H1: índices extranjeros, desde el inicio con calidad hasta 2026-09-30
    U1 = _universo(EXTRANJEROS); U1["base"].to_csv(OUT / "OPS_H1_EXTRANJEROS.csv.gz", index=False)
    c1 = _canasta(U1["base"]); res["H1_extranjeros"] = dict(primaria=_t(c1), veredicto=_veredicto(_t(c1)), estres_6bps=_t(_canasta(U1["estres"])),
        antes_2009=_t(c1[c1.index < pd.Period("2009-01", "M")]), desde_2009=_t(c1[c1.index >= pd.Period("2009-01", "M")]),
        desde_2019=_t(c1[c1.index >= pd.Period("2019-01", "M")]),
        por_regla={r: _t(_canasta(U1["base"][U1["base"].definicion == r])) for r in REGLAS},
        por_indice={i: _t(_canasta(U1["base"][U1["base"].indice == i])) for i in sorted(U1["base"].indice.unique())},
        control_N=_t(_canasta(U1["base"][U1["base"].definicion.str.endswith("N")].assign(definicion=lambda d: d.definicion.str[:-1]))),
        operaciones=int((~U1["base"].definicion.str.endswith("N")).sum()), fricR_media=round(float(U1["base"].fricR.mean()), 4))
    # H2: EE. UU. cash 1990 → 2005-12-31 (antes de los datos NT8 que usó EdgeLab)
    U2 = _universo(EEUU, hasta=20051231); U2["base"].to_csv(OUT / "OPS_H2_EEUU_1990_2005.csv.gz", index=False)
    c2 = _canasta(U2["base"]); res["H2_eeuu_1990_2005"] = dict(primaria=_t(c2), veredicto=_veredicto(_t(c2)), estres_6bps=_t(_canasta(U2["estres"])),
        por_regla={r: _t(_canasta(U2["base"][U2["base"].definicion == r])) for r in REGLAS},
        control_N=_t(_canasta(U2["base"][U2["base"].definicion.str.endswith("N")].assign(definicion=lambda d: d.definicion.str[:-1]))),
        operaciones=int((~U2["base"].definicion.str.endswith("N")).sum()))
    # H3: placebo en la canasta sellada (2006 → 2026-09): regla − su control N, mismo instrumento, mismo motor, todos los bloques
    res["H3_placebo_sellada"] = _placebo()
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({k: (v.get("primaria"), v.get("veredicto")) for k, v in res.items()}, indent=1, default=float))
    return 0


def _placebo() -> dict:
    """Diferencia mensual entre la canasta sellada (16, pesos fijos) y la misma canasta con cada regla reemplazada por su control N.
    Lee meses HOLDOUT de CARRIL2_A5, familia cuya única apertura ya se hizo (2026-11-27): diagnóstico declarado, no elige nada."""
    import canasta_amplia as CA, carril2 as C2
    from datos import ruta
    from m1_largo import cargar
    from edgelab.research import sqx_catalogo as Q
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import a5_bloque
    pesos = json.loads((ROOT / "docs/research/canasta_amplia_20261127/PESOS_CARRIL2_SELLADA.json").read_text(encoding="utf-8"))
    pesos = pesos.get("pesos", pesos)
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); vc = V.vix_close.copy(); vc.index = pd.to_datetime(vc.index).normalize()
    vix_reg = (vc > vc.rolling(100).mean()).shift(1)
    cm = {k: Q.barras_desde_m1(cargar(k, ruta("M1NT8")), "D1").assign(mes=lambda b: b.fecha // 100).groupby("mes").c.last() for k in ("ES", "GC")}
    mens = (cm["ES"] / cm["GC"]).dropna(); mens.attrs["sma"] = mens.rolling(20).mean()
    filas = []
    for inst in sorted({k.rsplit("_", 1)[1] for k in pesos}):
        D = cargar(inst, ruta("M1NT8")); B = Q.barras_desde_m1(D, "D1"); m1 = Q.indices_m1(B, D, "D1")
        vix_ok = vix_reg.reindex(pd.to_datetime(B.fecha.astype(str))).fillna(False).to_numpy(bool)
        S = {**C2._senales(B, vix_ok), **C2._senales2(B, inst, V, mens)}; fr = float(friccion(inst)[0]); f = B.fecha.to_numpy()
        for k, w in pesos.items():
            regla, i2 = k.rsplit("_", 1)
            if i2 != inst: continue
            for d in (regla, regla + "N"):
                O = Q.simular(B, S[d], viernes=False, m1=m1)
                rg = (O.entrada - O.stop0).abs(); O = O[O.stop0.notna() & (rg > 0)].copy(); rg = rg.loc[O.index]
                O["R"] = (O.lado * (O.salida_px - O.entrada) - fr) / rg * w; O["fecha_sal"] = f[np.minimum(O.i0 + O.barras - 1, len(f) - 1)]
                O["tipo"] = "regla" if d == regla else "control"; O["serie"] = k; filas.append(O)
    T = pd.concat(filas, ignore_index=True); T = T[(T.fecha_sal < 20261001) & (T.fecha < 20261001)]
    T["bloque"] = [a5_bloque(int(x)) for x in T.fecha]; T = T[T.bloque.isin(["DESC", "REP", "HOLDOUT"])]
    T["mes"] = pd.to_datetime(T.fecha.astype(str)).dt.to_period("M")
    m = T.pivot_table(index="mes", columns="tipo", values="R", aggfunc="sum").fillna(0.0); dif = m["regla"] - m["control"]
    blq = T.groupby("mes").bloque.first()
    T.to_csv(OUT / "OPS_H3_PLACEBO.csv.gz", index=False)
    out = dict(primaria=_t(dif), regla=_t(m["regla"]), control=_t(m["control"]),
               por_bloque={b: dict(diferencia=_t(dif[blq == b]), regla=_t(m["regla"][blq == b]), control=_t(m["control"][blq == b]))
                           for b in ("DESC", "REP", "HOLDOUT")})
    out["veredicto"] = _veredicto(out["primaria"])
    return out


def dsr() -> int:
    """Sharpe deflactado (Bailey y López de Prado 2014) y recorte de Harvey-Liu (Bonferroni) con las pruebas contadas por familia.
    Descriptivo: no agrega pruebas; usa Sharpe mensuales ya publicados."""
    from math import erf, sqrt, log, pi, e
    Phi = lambda z: 0.5 * (1 + erf(z / sqrt(2)))
    reg = [json.loads(l) for l in (ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    n_fam = {}
    for r in reg:
        if "family_id" in r: n_fam[r["family_id"]] = n_fam.get(r["family_id"], 0) + int(r.get("n_trials", 0))
    filas = [  # (estrategia, familia del contador, Sharpe anual medido, meses, fuente, muestra)
        ("Carril 2 sellada (HOLDOUT A5)", "CARRIL2_A5", 1.057, 63, "holdout_a5_nocme_20261127/RESULTADO.md", "sellada"),
        ("Carril 2 sellada (DESC+REP)", "CARRIL2_A5", 0.857, 186, "supercartera_v3_20261127/RESULTADO.md", "vista"),
        ("Macro risk premia (HOLDOUT A5)", "MACRO_RISK_PREMIA", 0.38, 63, "holdout_a5_nocme_20261127/RESULTADO.md", "sellada"),
        ("Cripto v3 (HOLDOUT A5)", "CRIPTO_BINANCE", 0.493, 18, "holdout_a5_nocme_20261127/RESULTADO.md", "sellada"),
        ("Cripto OFI (HOLDOUT A5)", "CRIPTO_ORDERFLOW_PIT", 1.133, 18, "holdout_a5_nocme_20261127/RESULTADO.md", "sellada"),
        ("T+R+Z+V NQ (2021–2026-09)", "FUNDEDSYNC", 2.494, 51, "supercartera_v2_20261127/RESULTADO.md", "vista por el vendedor"),
    ]
    from statistics import NormalDist
    inv = NormalDist().inv_cdf; g = 0.5772156649
    out = []
    for nom, fam, sr, n, fuente, muestra in filas:
        N = max(n_fam.get(fam, 1), 1); sr_m = sr / sqrt(12)                      # Sharpe mensual
        # SR0: máximo esperado de N Sharpe mensuales nulos, con var(SR̂) ≈ 1/(n−1) (retornos normales; Bailey y López de Prado 2014)
        sr0 = sqrt(1 / (n - 1)) * ((1 - g) * inv(1 - 1 / N) + g * inv(1 - 1 / (N * e))) if N > 1 else 0.0
        t = sr_m * sqrt(n); p = 1 - Phi(t); p_bonf = min(1.0, p * N)
        out.append(dict(estrategia=nom, familia=fam, pruebas_familia=N, sharpe_anual=sr, meses=n, muestra=muestra, t=round(t, 2), p=round(p, 5),
                        p_bonferroni_familia=round(p_bonf, 4), sr0_anual=round(sr0 * sqrt(12), 3), dsr=round(Phi((sr_m - sr0) * sqrt(n - 1)), 3),
                        fuente=fuente))
    (OUT / "DSR_HAIRCUT.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for o in out: print(o)
    return 0


if __name__ == "__main__":
    sys.exit({"bajar": bajar, "correr": correr, "dsr": dsr}[sys.argv[1]]())
