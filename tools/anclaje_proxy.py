#!/usr/bin/env python3
"""Proxy de gamma desde 2006 y el filtro de exclusión en T + Franklin + SOM (pre-registro docs/research/anclaje_proxy_20261118/PREREGISTRO.md).

Reusa `gex_tendencia.gamma` (GEX), `gex_tendencia._canasta_dia`-equivalente por fecha, `a5.diferencia`, `a5.plan_lectura` /
`exigir_potencia` (K49), `libro_lord`, `m1_intradia.leer_m1nt8` y la copia verificada de `tools/datos.py`.

  python tools/anclaje_proxy.py fase0   # candidatos sin retornos de estrategia; el de mayor |Spearman| con GEX -> FASE0.json
  python tools/anclaje_proxy.py fase1   # efecto en DESC 2011+ (ya mirado) y potencia de la lectura 2006–2011 -> FASE1.json
  python tools/anclaje_proxy.py fase2   # UNA lectura en 2006-01 → 2011-10, sólo si K49 lo permite -> FASE2.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/anclaje_proxy_20261118"
FAMILIA, RESERVA = "ANCLAJE_PROXY", "CONF_20261118"
LECTURA = (20060101, 20111031)
CALIB = (20111101, 20250731)


def candidatos() -> pd.DataFrame:
    """Por día d, del cierre de d−1: vix_ivp, vix_z20, vr20 y ac20 (NQ RTH)."""
    from datos import ruta
    from edgelab.research.m1_intradia import leer_m1nt8
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); V.index = pd.to_datetime(V.index)
    X = pd.DataFrame(index=V.index)
    X["vix_ivp"] = V.vix_ivp_252_prev_close                                     # ya es del cierre previo
    vc = V.vix_close; X["vix_z20"] = ((vc - vc.rolling(20).mean()) / vc.rolling(20).std()).shift(1)
    D = leer_m1nt8(Path(ruta("M1NT8")) / "NQ_M1_nonadj_utc.parquet"); m = D.index.hour * 60 + D.index.minute
    R = D[(m >= 570) & (m < 960)]; dia = R.index.normalize()
    r1 = np.log(R.c).groupby(dia).diff()
    R30 = R[(m[(m >= 570) & (m < 960)] - 570) % 30 == 29]; r30 = np.log(R30.c).groupby(R30.index.normalize()).diff()
    R5 = R[(m[(m >= 570) & (m < 960)] - 570) % 5 == 4]; r5 = np.log(R5.c).groupby(R5.index.normalize()).diff()
    v1 = (r1 ** 2).groupby(r1.index.normalize()).agg(["sum", "count"]); v30 = (r30 ** 2).groupby(r30.index.normalize()).agg(["sum", "count"])
    vr = (v30["sum"].rolling(20).sum() / v30["count"].rolling(20).sum()) / (30 * v1["sum"].rolling(20).sum() / v1["count"].rolling(20).sum())
    a = pd.DataFrame(dict(x=r5, y=r5.groupby(r5.index.normalize()).shift(1))).dropna(); a["d"] = a.index.normalize()
    s = a.groupby("d").apply(lambda g: pd.Series(dict(xy=(g.x * g.y).sum(), xx=(g.x ** 2).sum())))
    ac = s.xy.rolling(20).sum() / s.xx.rolling(20).sum()
    X = X.join(pd.DataFrame(dict(vr20=vr.shift(1), ac20=ac.shift(1))), how="outer")
    X.index = X.index.strftime("%Y%m%d").astype(int); return X


def fase0():
    from gex_tendencia import gamma
    X = candidatos(); g = gamma(); g.index = g.index.strftime("%Y%m%d").astype(int)
    J = X.join(g[["g_rank250"]], how="inner"); J = J[(J.index >= CALIB[0]) & (J.index <= CALIB[1])]
    rho = {c: float(J[[c, "g_rank250"]].dropna().rank().corr().iloc[0, 1]) for c in ("vix_ivp", "vix_z20", "vr20", "ac20")}
    mejor = max(rho, key=lambda c: abs(rho[c])); signo = 1 if rho[mejor] > 0 else -1           # lado que acompaña a gamma alta
    y = signo * X[mejor]; corte = float(y[(y.index >= CALIB[0]) & (y.index <= CALIB[1])].quantile(2 / 3))
    out = dict(spearman_con_gex=rho, elegido=mejor, signo=signo, corte_alto=corte, pasa=bool(abs(rho[mejor]) >= 0.3))
    DIR.mkdir(parents=True, exist_ok=True); (DIR / "FASE0.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))


def _canasta():
    D = ROOT / "docs/research/m1_largo_20261117"
    T = pd.concat([pd.read_csv(D / f"FS_OPS_T2008_{i}.csv.gz") for i in ("NQ", "ES", "YM")]); T = T[T.riesgo > 0]
    T["R"] = T.neto / T.riesgo; T["fecha"] = pd.to_datetime(T.dia).dt.strftime("%Y%m%d").astype(int)
    F = pd.concat([pd.read_csv(D / f"FRANKLIN_OPS_{i}.csv.gz") for i in ("NQ", "ES")]); F = F[F.riesgo > 0]
    S = pd.concat([pd.read_csv(D / f"SOM_OPS_{i}.csv.gz") for i in ("NQ", "ES", "YM")]); S = S[(S.celda == "sin_finde") & (S.riesgo > 0)]
    return pd.concat([T[["fecha", "R"]], F[["fecha", "R"]], S[["fecha", "R"]]]).groupby("fecha").R.sum()


def _marca(fechas):
    f0 = json.loads((DIR / "FASE0.json").read_text()); X = candidatos()
    y = f0["signo"] * pd.Series(fechas).map(X[f0["elegido"]]).to_numpy(float)
    return np.where(np.isfinite(y), y >= f0["corte_alto"], np.nan)


def fase1():
    from edgelab.holdout import a5_bloque
    from edgelab.research import a5 as A5
    if not json.loads((DIR / "FASE0.json").read_text())["pasa"]: raise SystemExit("fase 0: ningún proxy ≥ 0,3; se termina sin mirar retornos")
    c = _canasta(); f = c.index.values
    desc = c[[(CALIB[0] <= x <= CALIB[1]) and a5_bloque(int(x)) == "DESC" for x in f]]
    a = _marca(desc.index.values); ok = np.isfinite(a); a = a[ok].astype(bool); r = desc.values[ok]; fd = desc.index.values[ok]
    d, se, p = A5.diferencia(fd[a], r[a], fd[~a], r[~a])
    n_lect = int(((f >= LECTURA[0]) & (f <= LECTURA[1])).sum())                  # sólo cuenta días de la lectura
    # K49 en días: contraste de dos grupos (fracción q en «alto»): sd equivalente por día = sqrt(var_alto/q + var_resto/(1−q))
    from edgelab.research import holdout_ventanas as HV
    from edgelab.funnel.libro_lord import LibroLord
    q = a.mean(); sd = float(np.sqrt(r[a].var(ddof=1) / q + r[~a].var(ddof=1) / (1 - q)))
    plan = dict(HV.plan_potencia("fijo", 0.5 * max(-d, 0.0) or 1e-9, sd, n=n_lect, alfa=LibroLord().nivel(FAMILIA),
                                 fuente_efecto="mitad del contraste de DESC 2011+ (K49)"), sd_dia=sd, n_dias=n_lect)
    out = dict(desc_contraste=d, se=se, p=p, n_desc=int(len(r)), n_alto=int(a.sum()), n_dias_lectura=n_lect, plan=plan)
    (DIR / "FASE1.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps({k: out[k] for k in ("desc_contraste", "se", "p", "n_dias_lectura")}), "potencia", plan.get("potencia"))


def fase2():
    from a5_campana import _commiteado
    from edgelab.research import a5 as A5
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / "FASE1.json"): raise SystemExit("FASE1.json sin commitear")
    A5.exigir_potencia(json.loads((DIR / "FASE1.json").read_text())["plan"], "lectura 2006–2011 del proxy de anclaje")   # K49
    c = _canasta(); c = c[(c.index >= LECTURA[0]) & (c.index <= LECTURA[1])]
    a = _marca(c.index.values); ok = np.isfinite(a); a = a[ok].astype(bool); r = c.values[ok]; fd = c.index.values[ok]
    d, se, p = A5.diferencia(fd[a], r[a], fd[~a], r[~a]); p = 1 - p                 # H1: alto − resto < 0
    res = LibroLord().reservar(FAMILIA, RESERVA, "anclaje alto − resto, 2006–2011"); dec = LibroLord().resolver(FAMILIA, RESERVA, [("anclaje", p)])
    yy = pd.DataFrame(dict(y=fd // 10000, r=r, a=a)).groupby("y").apply(lambda x: x[x.a].r.mean() - x[~x.a].r.mean()).dropna()
    frac = float((yy < 0).mean())
    ver = "CONFIRMADA" if (dec.get("rechazo") and d < 0 and frac >= 0.6) else ("REFUTADA" if (d >= 0 or d - 1.645 * se > -0.1) else "NO_CONFIRMADA")
    sin = r[~a]; out = dict(contraste=d, se=se, p=p, lord=dec, frac_anios=frac, anios=int(len(yy)), veredicto=ver, n=int(len(r)), n_alto=int(a.sum()),
                            media_alto=float(r[a].mean()), media_resto=float(sin.mean()), canasta_todos=float(r.mean()), por_anio=yy.to_dict())
    (DIR / "FASE2.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps({k: out[k] for k in ("contraste", "se", "p", "frac_anios", "veredicto", "media_alto", "media_resto", "canasta_todos")}, default=float))


if __name__ == "__main__":
    {"fase0": fase0, "fase1": fase1, "fase2": fase2}[sys.argv[1]]()
