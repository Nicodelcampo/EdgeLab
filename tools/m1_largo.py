#!/usr/bin/env python3
"""M1 real de futuros (NT8, 2006 → frontera) sobre las estrategias externas y prueba de régimen análogo
(pre-registro docs/research/m1_largo_20261117/PREREGISTRO.md).

Reusa, sin copiar: el motor de FundedSync con las funciones del kernel `tools/kaggle_grilla/fundedsync_main.py` (`a_utc`, `_orb_t`,
`operaciones`, tomadas por AST), SOM con `quantlab_mt5_medir.ops_som`, la calibración de `atras_m1.calibrar` y el lector
`m1_intradia.leer_m1nt8` (corta en la frontera del holdout).

  python tools/m1_largo.py correr <carpeta M1 NT8> fs|som|estado <INST>   # -> docs/research/m1_largo_20261117/{FS_OPS,SOM_OPS,ESTADO}_<INST>
  python tools/m1_largo.py analizar                                         # -> RESULTADO.json
"""
import ast, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/m1_largo_20261117"
INST = ("NQ", "ES", "YM")
LIMPIO = (20060106, 20111230)                       # ninguna medición de FundedSync ni de SOM tocó estos años
CALIB = (20120120, 20250731)                        # mismo tramo que la medición sobre el CFD (M1 Dukascopy)
REF_EXT = (20200101, 20250731)                      # donde T, Z, R y SOM se vieron positivos
CONFIRMATORIAS = ("T", "Z", "R", "SOM")


def cargar(inst, datos):
    from edgelab.research.m1_intradia import leer_m1nt8
    return leer_m1nt8(Path(datos) / f"{inst}_M1_nonadj_utc.parquet")


def _kernel_fs(fr):
    """Las funciones del kernel de FundedSync (las mismas que produjeron FUNDEDSYNC_OPS sobre el CFD), sin su carga de datos."""
    from edgelab.research import fundedsyncstack as F
    arbol = ast.parse((ROOT / "tools/kaggle_grilla/fundedsync_main.py").read_text(encoding="utf-8"))
    fns = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in ("a_utc", "_orb_t", "operaciones")]
    ns = dict(F=F, np=np, pd=pd, os=os, FR=float(fr)); exec(compile(ast.Module(body=fns, type_ignores=[]), "fundedsync_main.py", "exec"), ns)
    return ns


def _sesion(idx):
    """Sesión CME (desde las 18:00 de NY es el día siguiente) de un índice en hora de NY."""
    return (idx + pd.Timedelta(hours=6)).normalize()


def atr20(D):
    """Rango diario de la sesión CME, media de 20 sesiones previas (causal): unidad para módulos sin stop y para comparar épocas."""
    ses = _sesion(D.index); r = D.h.groupby(ses).max() - D.l.groupby(ses).min()
    return r.rolling(20).mean().shift(1)


def correr_fs(inst, datos):
    from edgelab.research.embudo_runners import friccion
    D = cargar(inst, datos); ops = _kernel_fs(friccion(inst)[0])["operaciones"](D); a = atr20(D)
    out = pd.concat([v.assign(modulo=k) for k, v in ops.items() if v is not None and len(v)])
    out["atr20"] = a.reindex(_sesion(pd.DatetimeIndex(out.dia))).to_numpy()
    out.to_csv(DIR / f"FS_OPS_{inst}.csv.gz", index=False); print(inst, out.groupby("modulo").size().to_dict(), flush=True)


T_FECHAS = dict(shadow_min_session_date=20060101, knn_min_session_date=20080101, portfolio_start_cash_date=20080101)   # enmienda 1
LIMPIO_T = (20080102, 20111230)


def correr_t2008(inst, datos):
    """Enmienda 1: T con sus fechas de arranque corridas 6 años (sombra desde 2006, KNN y operación desde 2008): mismo calentamiento de 2 años
    que el diseño de fábrica (2010 → 2012). Mismas funciones del kernel; sólo T y con esas tres fechas."""
    from types import SimpleNamespace
    from edgelab.research import fundedsyncstack as F
    from edgelab.research.embudo_runners import friccion
    ns = _kernel_fs(friccion(inst)[0])
    ns["F"] = SimpleNamespace(MODULOS={"T": F.MODULOS["T"]}, build_multi_series=F.build_multi_series, load_m1_data=F.load_m1_data,
                              correr_modulo=lambda k, ms, **kw: F.correr_modulo(k, ms, **{**T_FECHAS, **kw}))
    D = cargar(inst, datos); v = ns["operaciones"](D)["T"]; a = atr20(D)
    v = v.assign(modulo="T", atr20=a.reindex(_sesion(pd.DatetimeIndex(v.dia))).to_numpy())
    v.to_csv(DIR / f"FS_OPS_T2008_{inst}.csv.gz", index=False); print(inst, "T2008", len(v), flush=True)


def correr_som(inst, datos):
    from dataclasses import replace
    from edgelab.research.embudo_runners import friccion
    from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
    from edgelab.research.m1_intradia import SERVIDOR_MENOS_NY
    from quantlab_mt5_medir import ops_som, FUENTES
    D = cargar(inst, datos); srv = (D.index + pd.Timedelta(hours=SERVIDOR_MENOS_NY)).tz_localize("UTC")   # el EA lee la hora del servidor (NY+7)
    df = pd.DataFrame(dict(time=srv, ts_ns=srv.asi8, open=D.o.to_numpy(), high=D.h.to_numpy(), low=D.l.to_numpy(), close=D.c.to_numpy(),
                           volume=D.v.to_numpy()))
    fr = friccion(inst)[0]; partes = []
    for celda, cfg in (("sin_eod", SessionOpenMomentumConfig()), ("eod", replace(SessionOpenMomentumConfig(), close_eod=True)),
                       ("sin_finde", replace(SessionOpenMomentumConfig(), close_weekend=True))):
        partes.append(ops_som(df, cfg, FUENTES[inst][1], fr).assign(celda=celda))
    pd.concat(partes).to_csv(DIR / f"SOM_OPS_{inst}.csv.gz", index=False); print(inst, "SOM", len(partes[-1]), flush=True)


def correr_estado(inst, datos):
    """Variables de estado SIN resultados (PREREGISTRO §2): por mes, mediana del rango diario / cierre (volatilidad) y signo del retorno de
    126 sesiones al empezar el mes (tendencia)."""
    D = cargar(inst, datos); ses = _sesion(D.index)
    d = pd.DataFrame(dict(h=D.h.groupby(ses).max(), l=D.l.groupby(ses).min(), c=D.c.groupby(ses).last()))
    d = d[d.index.dayofweek < 5]; d["rv"] = (d.h - d.l) / d.c; d["ret126"] = d.c / d.c.shift(126) - 1
    m = d.index.to_period("M")
    e = pd.DataFrame(dict(vol=d.rv.groupby(m).median(), tend=np.sign(d.ret126.groupby(m).last().shift(1))))
    e.index = e.index.astype(str); e.to_csv(DIR / f"ESTADO_{inst}.csv"); print(inst, "estado", len(e), flush=True)


# ------------------------------------------------------------------------------------------------------------- análisis (§3–§5)
def _unidades_fs(g):
    """Todos los módulos en neto / ATR20 diario (PREREGISTRO §3): comparable entre épocas (NQ ≈ 1.700 → 21.000 puntos) y entre módulos con y
    sin stop; el riesgo de T en el archivo del CFD es anterior a la corrección de la auditoría del 16-nov (276 operaciones con riesgo 0)."""
    u = g.neto / g.atr20
    return g.assign(u=u, ses=pd.to_datetime(g.dia).dt.strftime("%Y%m%d").astype(int))


def ops_estrategia(nombre, limpio_t=False):
    """[(sesión, instrumento, unidad)] de una estrategia en futuros (las 3 confirmatorias pooled en NQ, ES, YM)."""
    out = []
    for inst in INST:
        if nombre == "SOM":
            g = pd.read_csv(DIR / f"SOM_OPS_{inst}.csv.gz"); g = g[g.celda == "sin_finde"]
            out += [(int(s), inst, float(r)) for s, r in zip(g.fecha, g.R)]
        else:
            arch = DIR / (f"FS_OPS_T2008_{inst}.csv.gz" if nombre == "T" and limpio_t else f"FS_OPS_{inst}.csv.gz")
            g = _unidades_fs(pd.read_csv(arch)); g = g[(g.modulo == nombre) & np.isfinite(g.u)]
            out += [(int(s), inst, float(r)) for s, r in zip(g.ses, g.u)]
    return out


def _resumen(o, a, b):
    from cartera_nov_analisis import _boot_ic
    o = [x for x in o if a <= x[0] <= b]; R = np.array([x[2] for x in o]); S = np.array([x[0] for x in o])
    anios = {int(y): float(R[S // 10000 == y].sum()) for y in np.unique(S // 10000)} if len(S) else {}
    return dict(ops=len(R), u_op=float(R.mean()) if len(R) else None, sd=float(R.std(ddof=1)) if len(R) > 1 else None,
                ic90=_boot_ic(S, R) if len(R) > 2 else None, frac_anios_pos=float(np.mean([v > 0 for v in anios.values()])) if anios else None,
                anios=anios), R


def _veredicto(res, R, efecto_ref, favor="A_FAVOR", contra="EN_CONTRA"):
    from edgelab.research import holdout_ventanas as HV
    pot = HV.plan_potencia("fijo", max(efecto_ref / 2, 1e-9), res["sd"] or 1.0, n=max(res["ops"], 1))["potencia"] if res["ops"] > 1 else 0.0
    ic = res["ic90"] or [None, None]
    if ic[0] is not None and ic[0] > 0 and (res["frac_anios_pos"] or 0) >= 0.6: v = favor
    elif res["u_op"] is not None and res["u_op"] <= 0 and pot >= 0.8: v = contra
    else: v = "NO_CONCLUYENTE"
    return dict(res, potencia_mitad_ref=pot, efecto_ref=efecto_ref, veredicto=v)


def _estado(inst):
    e = pd.read_csv(DIR / f"ESTADO_{inst}.csv", index_col=0)
    base = e[(e.index >= "2006-01") & (e.index <= "2025-07")]; q = base.vol.quantile([1 / 3, 2 / 3]).to_numpy()   # terciles sin resultados
    e["terc"] = np.digitize(e.vol, q); return e


def regimen(nombre, ops, ref, prueba):
    """§4: estado modal (tercil de volatilidad, signo de tendencia) de la ventana de referencia; meses análogos de la ventana de prueba."""
    E = {i: _estado(i) for i in {x[1] for x in ops}}
    clave = lambda s, i: (int(E[i].terc.get(f"{s // 10000}-{s // 100 % 100:02d}", -1)), float(E[i].tend.get(f"{s // 10000}-{s // 100 % 100:02d}", 0)))
    refm = pd.Series([clave(s, i) for s, i, _ in ops if ref[0] <= s <= ref[1]])
    if not len(refm): return dict(veredicto="SIN_DATOS")
    modal = refm.value_counts().index[0]; cobertura = float((refm == modal).mean())
    ref_ef = float(np.mean([r for s, i, r in ops if ref[0] <= s <= ref[1]]))
    an = [(s, i, r) for s, i, r in ops if prueba[0] <= s <= prueba[1] and clave(s, i) == modal]
    no = [(s, i, r) for s, i, r in ops if prueba[0] <= s <= prueba[1] and clave(s, i) != modal]
    ra, Ra = _resumen(an, *prueba); rn, _ = _resumen(no, *prueba)
    v = _veredicto(ra, Ra, ref_ef, favor="REGIMEN_APOYADO", contra="REGIMEN_RECHAZADO")
    return dict(estrategia=nombre, estado_modal=dict(tercil_vol=modal[0], tendencia=modal[1]), cobertura_ref=cobertura, analogos=v, no_analogos=rn)


def analizar():
    import atras_m1 as A
    from edgelab.research.embudo_runners import friccion
    out = dict(preregistro="docs/research/m1_largo_20261117/PREREGISTRO.md", calibracion={}, limpio={}, regimen={}, descriptivo={})
    # §3a calibración (diagnóstico): futuros NT8 contra el CFD en el mismo tramo, NQ
    cfd = pd.read_csv(ROOT / "docs/research/fundedsyncstack_20261115/cadena/FUNDEDSYNC_OPS.csv.gz")
    cfd["ses"] = pd.to_datetime(cfd.dia).dt.strftime("%Y%m%d").astype(int); fut = pd.read_csv(DIR / "FS_OPS_NQ.csv.gz")
    fut["ses"] = pd.to_datetime(fut.dia).dt.strftime("%Y%m%d").astype(int)
    for k in sorted(set(cfd.modulo) | set(fut.modulo)):
        t = cfd[(cfd.modulo == k) & cfd.ses.between(*CALIB)].groupby("ses").neto.sum().to_dict()
        m = fut[(fut.modulo == k) & fut.ses.between(*CALIB)].groupby("ses").neto.sum().to_dict()
        out["calibracion"][k] = A.calibrar(t, m) if len(t) > 2 and len(m) > 2 else dict(calibra=False, motivo="sin operaciones")
    s_cfd = pd.read_csv(ROOT / "docs/research/quantlab_mt5_eas_20261116/SOM_OPS_NQ_sin_finde.csv.gz"); s_fut = pd.read_csv(DIR / "SOM_OPS_NQ.csv.gz")
    s_fut = s_fut[s_fut.celda == "sin_finde"]
    out["calibracion"]["SOM"] = A.calibrar(s_cfd[s_cfd.fecha.between(*CALIB)].groupby("fecha").R.sum().to_dict(),
                                           s_fut[s_fut.fecha.between(*CALIB)].groupby("fecha").R.sum().to_dict())
    # §3b años limpios 2006–2011 (confirmatorio para T, Z, R, SOM; NQ+ES+YM pooled) y descriptivo por módulo e instrumento
    for n in CONFIRMATORIAS:
        o = ops_estrategia(n); ref, _ = _resumen(o, *REF_EXT)
        res, R = _resumen(ops_estrategia(n, limpio_t=True), *LIMPIO_T) if n == "T" else _resumen(o, *LIMPIO)
        out["limpio"][n] = dict(referencia_2020_2025=ref, limpio_2006_2011=_veredicto(res, R, ref["u_op"] or 0.0))
    for inst in INST:
        g = _unidades_fs(pd.read_csv(DIR / f"FS_OPS_{inst}.csv.gz"))
        for k, h in g.groupby("modulo"):
            h = h[np.isfinite(h.u)]
            out["descriptivo"][f"{k}|{inst}"] = {t: _resumen([(int(s), inst, float(r)) for s, r in zip(h.ses, h.u)], a, b)[0]
                                                 for t, (a, b) in (("2006-2011", LIMPIO), ("2012-2019", (20120101, 20191231)), ("2020-2025", REF_EXT))}
    # §4 régimen análogo
    for n in CONFIRMATORIAS:
        out["regimen"][n] = regimen(n, ops_estrategia(n), REF_EXT, (20060106, 20191231))
    for n, (cid, inst, prim, d0) in A.REGLAS.items():
        _, ops = A.ops_m1(n, "atras"); _, cal = A.ops_m1(n, "calibracion")
        o = [(s, inst, r) for s, r in ops] + [(s, inst, r) for s, r in cal]
        out["regimen"][n] = regimen(n, o, A.CALIB, prim)
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))
    for k, v in out["limpio"].items(): print("LIMPIO", k, v["limpio_2006_2011"]["veredicto"], round(v["limpio_2006_2011"]["u_op"] or 0, 3), v["limpio_2006_2011"]["ops"])
    for k, v in out["regimen"].items(): print("REGIMEN", k, v.get("analogos", {}).get("veredicto"), v.get("estado_modal"), round(v.get("cobertura_ref", 0), 2))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "correr": {"fs": correr_fs, "t2008": correr_t2008, "som": correr_som, "estado": correr_estado}[sys.argv[3]](sys.argv[4], sys.argv[2])
    elif c == "analizar": analizar()
