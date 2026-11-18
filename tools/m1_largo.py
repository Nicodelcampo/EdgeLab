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
        partes.append(ops_som(df, cfg, FUENTES.get(inst, (None, "USA500"))[1], fr).assign(celda=celda))   # RTY/EMD: preset de redondeo del S&P (no cambia R)
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


def correr_franklin(inst, datos):
    """Franklin (celda llevada al holdout, `reels_20261116/FRANKLIN_MEJORAS.json`) con su motor (`estrategias_scrapeadas.franklin_variantes`)
    sobre futuros; R con la fricción canónica (`reels_20261116._en_r`)."""
    from edgelab.research import estrategias_scrapeadas as X
    from edgelab.research.embudo_runners import friccion
    from reels_20261116 import _en_r
    celda = json.loads((ROOT / "docs/research/reels_20261116/FRANKLIN_MEJORAS.json").read_text())["al_holdout"].split("|")
    R = X.franklin_variantes(X.ctx_de_m1(cargar(inst, datos)), celdas=[celda])
    g = _en_r(R, friccion(inst)[0]).drop(columns=["celda"], errors="ignore"); g.to_csv(DIR / f"FRANKLIN_OPS_{inst}.csv.gz", index=False)
    print(inst, "Franklin", len(g), flush=True)


def analizar_franklin():
    """PREREGISTRO_FRANKLIN.md: años limpios 2006–2011 (NQ + ES) confirmatorio en neto; bruto y neto por período (descriptivo)."""
    out = dict(preregistro="docs/research/m1_largo_20261117/PREREGISTRO_FRANKLIN.md", periodos={})
    g = pd.concat([pd.read_csv(DIR / f"FRANKLIN_OPS_{i}.csv.gz").assign(inst=i) for i in ("NQ", "ES")])
    o = [(int(s), i, float(r)) for s, i, r in zip(g.fecha, g.inst, g.R)]; ob = [(int(s), i, float(r)) for s, i, r in zip(g.fecha, g.inst, g.Rb)]
    ref, _ = _resumen(ob, *REF_EXT); res, R = _resumen(ob, *LIMPIO)                 # §2: la prueba principal es el BRUTO
    out["limpio_2006_2011"] = _veredicto(res, R, ref["u_op"] or 0.0); out["referencia_2020_2025_bruto"] = ref
    for nom, (a, b) in (("2006-2011", LIMPIO), ("2012-2019", (20120101, 20191231)), ("2020-2025", REF_EXT)):
        out["periodos"][nom] = dict(neto=_resumen(o, a, b)[0], bruto=_resumen(ob, a, b)[0],
                                    friccion_R=float(g[g.fecha.between(a, b)].fricR.mean()))
    (DIR / "RESULTADO_FRANKLIN.json").write_text(json.dumps(out, indent=1, default=float))
    v = out["limpio_2006_2011"]; print("FRANKLIN limpio", v["veredicto"], v["ops"], v["u_op"], v["ic90"], v["frac_anios_pos"], v["potencia_mitad_ref"])
    for k, x in out["periodos"].items(): print(k, "neto", round(x["neto"]["u_op"] or 0, 3), x["neto"]["ic90"], "bruto", round(x["bruto"]["u_op"] or 0, 3), x["bruto"]["ic90"], "fricR", round(x["friccion_R"], 3))


FRANKLIN_NUEVOS = {"YM": (20060106, 20250731), "EMD": (20060109, 20250731), "RTY": (20170710, 20250731), "GC": (20080102, 20250731)}
PRE_FR_NUEVOS = "docs/research/franklin_confirmacion_20261118/PREREGISTRO.md"


def analizar_franklin_nuevos():
    """franklin_confirmacion_20261118/PREREGISTRO.md: R BRUTO de Franklin en YM, EMD, RTY y GC (nunca medidos), una vez, LORD++."""
    from edgelab.research import a5 as A5
    from edgelab.funnel.libro_lord import LibroLord
    from edgelab.research.embudo_runners import friccion
    from edgelab import costos as C
    partes = []
    for inst, (a, b) in FRANKLIN_NUEVOS.items():
        g = pd.read_csv(DIR / f"FRANKLIN_OPS_{inst}.csv.gz"); g = g[(g.fecha >= a) & (g.fecha <= b) & (g.riesgo > 0)].assign(inst=inst)
        partes.append(g)
    G = pd.concat(partes, ignore_index=True); ses = G.fecha.to_numpy(np.int64); rb = G.Rb.to_numpy(float)
    m, se, p = A5.cluster(ses, rb)
    res = LibroLord().reservar("FRANKLIN", "CONF_NUEVOS_20261118", "Franklin bruto en YM/EMD/RTY/GC")
    dec = LibroLord().resolver("FRANKLIN", "CONF_NUEVOS_20261118", [("franklin_nuevos", p)])
    G["anio"] = G.fecha // 10000; ia = G.groupby(["inst", "anio"]).Rb.mean(); frac = float((ia > 0).mean())
    if dec.get("rechazo") and m > 0 and frac >= 0.6: ver = "CONFIRMADA"
    elif m <= 0 or m + 1.645 * se < 0.04: ver = "REFUTADA"
    else: ver = "NO_CONFIRMADA"
    micro = {"YM": "MYM", "GC": "MGC"}; por = {}
    with C.estimados_permitidos(PRE_FR_NUEVOS):
        for inst, g in G.groupby("inst"):
            fr_mi = friccion(micro[inst])[0] if inst in micro else None
            mi, si, pi = A5.cluster(g.fecha.to_numpy(np.int64), g.Rb.to_numpy(float))
            por[inst] = dict(n=int(len(g)), R_bruto=mi, se=si, p=pi, R_neto_mini=float(g.R.mean()),
                             R_neto_micro=float((g.Rb - fr_mi / g.riesgo).mean()) if fr_mi else None, fric_R_mediana=float(g.fricR.median()),
                             epocas={e: dict(n=int(len(x)), bruto=float(x.Rb.mean()), neto=float(x.R.mean()), fricR=float(x.fricR.mean()))
                                     for e, (x0, x1) in (("2006-2011", (20060101, 20111231)), ("2012-2019", (20120101, 20191231)), ("2020-2025", (20200101, 20251231)))
                                     for x in [g[g.fecha.between(x0, x1)]] if len(x)},
                             operable=dict(n=int((g.fricR <= 0.08).sum()), neto=float(g[g.fricR <= 0.08].R.mean()) if (g.fricR <= 0.08).any() else None))
    out = dict(preregistro=PRE_FR_NUEVOS, n=int(len(G)), R_bruto=m, se=se, p=p, reserva=res, lord=dec, frac_inst_anio_pos=frac, veredicto=ver, por_instrumento=por)
    (ROOT / "docs/research/franklin_confirmacion_20261118/RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("n", "R_bruto", "se", "p", "frac_inst_anio_pos", "veredicto")}, default=float))


NUEVOS = {"EMD": (20060109, 20250731), "RTY": (20170710, 20250731)}       # PREREGISTRO_INDICES.md
SOM_RTY_LIMPIO = (20170710, 20190228)                                         # SOM ya miró el Russell (CFD) desde 2019-03 (som_transfer)


def _con_costos(inst, fn, *a):
    """EMD tiene spread ESTIMADO (costos_canonicos.json): sólo se usa dentro del permiso declarado (K33)."""
    from edgelab import costos as C
    if inst == "EMD":                                                     # el permiso es del pre-registro de la corrida (M1LARGO_PREREG)
        with C.estimados_permitidos(os.environ.get("M1LARGO_PREREG", "docs/research/m1_largo_20261117/PREREGISTRO_INDICES.md")): return fn(*a)
    return fn(*a)


def analizar_indices():
    """PREREGISTRO_INDICES.md: SOM (R) y R AtrPhase (ATR) en EMD y RTY, BRUTO, ventana limpia de cada uno; descriptivo neto y por período."""
    from edgelab.research.embudo_runners import friccion
    out = dict(preregistro="docs/research/m1_largo_20261117/PREREGISTRO_INDICES.md", pruebas={}, descriptivo={})
    o_som, o_r, d_som, d_r = [], [], [], []
    for inst, (a, b) in NUEVOS.items():
        s = pd.read_csv(DIR / f"SOM_OPS_{inst}.csv.gz"); s = s[s.celda == "sin_finde"]
        lim = SOM_RTY_LIMPIO if inst == "RTY" else (a, b)
        o_som += [(int(f), inst, float(r)) for f, r in zip(s.fecha, s.Rb) if lim[0] <= f <= lim[1]]
        d_som += [(int(f), inst, float(r), float(rn)) for f, r, rn in zip(s.fecha, s.Rb, s.R)]
        fr = _con_costos(inst, lambda: friccion(inst)[0])
        g = pd.read_csv(DIR / f"FS_OPS_{inst}.csv.gz"); g = g[(g.modulo == "R") & np.isfinite(g.atr20)]
        ses = pd.to_datetime(g.dia).dt.strftime("%Y%m%d").astype(int); bruto = (g.neto + fr) / g.atr20; neto = g.neto / g.atr20
        o_r += [(int(x), inst, float(u)) for x, u in zip(ses, bruto) if a <= x <= b]; d_r += [(int(x), inst, float(u), float(n)) for x, u, n in zip(ses, bruto, neto)]
    for nom, o, ref in (("SOM", o_som, 0.064), ("R", o_r, 0.097)):           # efecto de referencia: bruto de los años limpios de NQ/ES/YM
        res, R = _resumen(o, 20060101, 20250731); out["pruebas"][nom] = _veredicto(res, R, ref)
    for nom, d in (("SOM", d_som), ("R", d_r)):
        for inst in NUEVOS:
            for per, (x, y) in (("2006-2011", (20060101, 20111231)), ("2012-2019", (20120101, 20191231)), ("2020-2025", REF_EXT)):
                b = [(s, i, u) for s, i, u, n in d if i == inst]; n_ = [(s, i, n) for s, i, u, n in d if i == inst]
                out["descriptivo"][f"{nom}|{inst}|{per}"] = dict(bruto=_resumen(b, x, y)[0], neto=_resumen(n_, x, y)[0])
    (DIR / "RESULTADO_INDICES.json").write_text(json.dumps(out, indent=1, default=float))
    for k, v in out["pruebas"].items(): print("PRUEBA", k, v["veredicto"], v["ops"], v["u_op"], v["ic90"], v["frac_anios_pos"], v["potencia_mitad_ref"])
    for k, v in out["descriptivo"].items(): print(k, "bruto", v["bruto"]["u_op"] and round(v["bruto"]["u_op"], 3), v["bruto"]["ops"], "neto", v["neto"]["u_op"] and round(v["neto"]["u_op"], 3))


def viejas_edgereplica(datos):
    """PREREGISTRO_VIEJAS.md §1: las 60 reglas con el motor de tools/edgereplica_usatech.py (`run`) sobre NQ futuros M1 (sin bid/ask:
    entrada y salida a la apertura de la vela), fricción canónica de NQ y puntos / ATR20 diario."""
    import edgereplica_usatech as E
    from edgelab.research.embudo_runners import friccion
    D = cargar("NQ", datos); a = atr20(D)
    t_close = (D.index + pd.Timedelta(minutes=1)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert(E.CT)
    ok = ~t_close.isna()
    b = pd.DataFrame(dict(open=D.o.to_numpy()[ok], close=D.c.to_numpy()[ok], bo=D.o.to_numpy()[ok], ao=D.o.to_numpy()[ok]), index=t_close[ok])
    b = b[~b.index.duplicated()].sort_index()
    t, sk = E.run(b, 0.0); fr = friccion("NQ")[0]
    t["ses_d"] = pd.to_datetime(t.ses); t["atr20"] = a.reindex(t.ses_d).to_numpy()
    t["bruto_atr"] = t.pts / t.atr20; t["neto_atr"] = (t.pts - fr) / t.atr20
    t[["rule", "dir", "ses", "pts", "atr20", "bruto_atr", "neto_atr"]].to_csv(DIR / "EDGEREPLICA_NQ.csv.gz", index=False); print("EdgeReplica", len(t), sk, flush=True)


def viejas_oro415(datos):
    """PREREGISTRO_VIEJAS.md §2: corto al cierre de la vela de las 04:15 CT, salida 15 minutos después (aperturas de las velas siguientes);
    H1 = sólo si los 15 minutos previos subieron. GC futuros, sesiones hasta 2022-06-30."""
    D = cargar("GC", datos); a = atr20(D)
    ct = pd.DatetimeIndex(D.index).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("America/Chicago")
    S = pd.DataFrame(dict(o=D.o.to_numpy(), c=D.c.to_numpy()), index=ct); S = S[~S.index.isna()]; S = S[~S.index.duplicated()]
    filas = []
    for dia, g in S.groupby(S.index.date):
        g = g.set_index(g.index.strftime("%H:%M"))
        if not {"04:14", "03:59", "04:15", "04:30"} <= set(g.index): continue          # vela que cierra 04:15 = abre 04:14
        ent, sal = g.at["04:15", "o"], g.at["04:30", "o"]; previo = g.at["04:14", "c"] - g.at["03:59", "c"]
        filas.append(dict(dia=pd.Timestamp(dia), bruto_ticks=(ent - sal) / 0.1, subida=bool(previo > 0)))
    t = pd.DataFrame(filas); t["atr20"] = a.reindex(t.dia + pd.Timedelta(0)).to_numpy()
    t.to_csv(DIR / "ORO415_GC.csv.gz", index=False); print("oro 04:15", len(t), flush=True)


# ------------------------------------------------------------------------------------------------- capa 2 (PREREGISTRO_CAPA2.md)
def _ms(D):
    from edgelab.research import fundedsyncstack as F
    return F.build_multi_series(F.load_m1_data(_kernel_fs(0.0)["a_utc"](D), end="2026-10-01"), tz_input="UTC")


def correr_variantes(inst, datos):
    """Variantes de salida de la tanda 2 (`fundedsync_tanda2.VARIANTES`: S, A20, W, N) contra el original, mismo motor, en futuros; y el ATR20
    de la sesión regular (`fundedsync_tanda2.diario`) para el stop de catástrofe de Z y R (0,5 × ATR20 sobre la MAE)."""
    from edgelab.research import fundedsyncstack as F
    from edgelab.research.embudo_runners import friccion
    from fundedsync_tanda2 import VARIANTES, _ops, diario
    D = cargar(inst, datos); ms = _ms(D); fr = friccion(inst)[0]; partes = []
    for k, kw in VARIANTES.items():
        partes += [_ops(F.correr_modulo(k, ms), fr).assign(modulo=k, version="original"),
                   _ops(F.correr_modulo(k, ms, **kw), fr).assign(modulo=k, version="variante")]
    pd.concat(partes).to_csv(DIR / f"FS_VAR_{inst}.csv.gz", index=False)
    diario(D)[["atr20"]].to_csv(DIR / f"ATR_RTH_{inst}.csv"); print(inst, "variantes", flush=True)


PERFILES = {"Lucid50K_fabrica": 3, "Lucid25K": 2}


def correr_cartera(inst, datos):
    """Cartera completa con el motor del vendedor (`motor_cartera.simular_cartera`): netting, tamaño por perfil, rotación, enfriamiento y
    cierre diario; filtro de noticias APAGADO (el calendario del vendedor no está: con el valor por defecto bloquearía todo). Sólo NQ (la
    estrategia exige NQ en 1 minuto). T con las fechas de la enmienda 1 (opera desde 2008)."""
    from edgelab.research import fundedsyncstack as F
    from edgelab.research.fundedsyncstack.motor_cartera import PortfolioConfig, simular_cartera
    D = cargar(inst, datos); ms = _ms(D); runners = {}
    for k in F.MODULOS:
        runners[k] = F.correr_modulo(k, ms, **(T_FECHAS if k == "T" else {}))
    for nom, perfil in PERFILES.items():
        cfg = PortfolioConfig(FundedSyncStackBlockRestrictedNewsDays=False, SizingProfile=perfil)
        r = simular_cartera(ms, runners, cfg); t = r["trades_df"]
        t.to_csv(DIR / f"CARTERA_{nom}_{inst}.csv.gz", index=False)
        print(inst, nom, len(t), "operaciones", {k: r.get(k) for k in ("virtual_net_pnl_usd", "broker_net_pnl_usd", "virtual_max_closed_dd_usd")}, flush=True)


def analizar_capa2():
    from cartera_nov_analisis import _boot_ic
    from edgelab.research.embudo_runners import friccion
    out = dict(preregistro="docs/research/m1_largo_20261117/PREREGISTRO_CAPA2.md", variantes={}, catastrofe={}, cartera={})
    tramos = (("2006-2011", 20060106, 20111230), ("2012-2019", 20120101, 20191231), ("2020-2025", 20200101, 20250731))
    # §2 variantes de salida: diferencia por día (variante − original) / ATR20 RTH; confirmatorio en años limpios, 3 índices juntos
    for k in ("S", "A20", "W", "N"):
        S_, Dl = [], []
        for inst in INST:
            v = pd.read_csv(DIR / f"FS_VAR_{inst}.csv.gz"); a = pd.read_csv(DIR / f"ATR_RTH_{inst}.csv", index_col=0).atr20
            a.index = pd.to_datetime(a.index); v["dia"] = pd.to_datetime(v.dia); v = v[v.modulo == k]
            sa = v[v.version == "original"].groupby("dia").neto.sum(); sb = v[v.version == "variante"].groupby("dia").neto.sum()
            dias = sa.index.union(sb.index); d = (sb.reindex(dias, fill_value=0) - sa.reindex(dias, fill_value=0)) / a.reindex(dias)
            d = d[np.isfinite(d)]; S_ += list(d.index.strftime("%Y%m%d").astype(int)); Dl += list(d.values)
        S_, Dl = np.array(S_), np.array(Dl); res = {}
        for nom, x, y in tramos:
            m = (S_ >= x) & (S_ <= y); res[nom] = dict(dias=int(m.sum()), dif_atr=float(Dl[m].mean()) if m.any() else None,
                                                       ic90=_boot_ic(S_[m], Dl[m]) if m.sum() > 2 else None)
        ic = res["2006-2011"]["ic90"] or [None, None]
        res["veredicto_limpio"] = ("CONFIRMA_MEJORA" if ic[0] is not None and ic[0] > 0 else ("EN_CONTRA" if ic[1] is not None and ic[1] < 0 else "NO_CONCLUYENTE"))
        out["variantes"][k] = res
    # §3 catástrofe de Z y R (descriptivo): stop 0,5 × ATR20 RTH sobre la MAE en puntos
    for k in ("Z", "R"):
        for inst in INST:
            g = pd.read_csv(DIR / f"FS_OPS_{inst}.csv.gz"); g = g[g.modulo == k].copy(); fr = friccion(inst)[0]
            a = pd.read_csv(DIR / f"ATR_RTH_{inst}.csv", index_col=0).atr20; a.index = pd.to_datetime(a.index)
            g["dia"] = pd.to_datetime(g.dia); g["stop"] = 0.5 * a.reindex(g.dia).to_numpy()
            g["neto_cat"] = np.where(pd.to_numeric(g.mae_pts, errors="coerce").abs() >= g.stop, -g.stop - fr, g.neto)
            s = g.dia.dt.strftime("%Y%m%d").astype(int)
            out["catastrofe"][f"{k}|{inst}"] = {nom: dict(n=int(((s >= x) & (s <= y)).sum()),
                                                          neto_atr=float((g.neto / g.stop * 0.5)[(s >= x) & (s <= y)].mean()),
                                                          neto_cat_atr=float((g.neto_cat / g.stop * 0.5)[(s >= x) & (s <= y)].mean()),
                                                          peor_pts=float(g.neto[(s >= x) & (s <= y)].min()), peor_cat_pts=float(g.neto_cat[(s >= x) & (s <= y)].min()))
                                                for nom, x, y in tramos}
    # §4 cartera completa (descriptivo): USD por año con la fricción canónica sobre el bruto (puntos × contratos × 20)
    fr = friccion("MNQ")[0]                                   # el motor ejecuta en MNQ por defecto (ExecMode.MNQ): qty = micros, 2 USD/pt
    for nom in PERFILES:
        t = pd.read_csv(DIR / f"CARTERA_{nom}_NQ.csv.gz"); t["anio"] = pd.to_datetime(t.entry_time_utc, unit="ns").dt.year
        t["usd_canon"] = (t.pnl_pts - fr) * t.qty * 2.0
        por = t.groupby("anio").usd_canon.sum(); eq = t.sort_values("exit_time_utc").usd_canon.cumsum()
        out["cartera"][nom] = dict(operaciones=int(len(t)), usd_por_anio={int(k): float(v) for k, v in por.items()},
                                   anios_pos=float((por > 0).mean()), usd_total=float(t.usd_canon.sum()),
                                   max_dd_usd=float((eq - eq.cummax()).min()), por_modulo={m: float(v) for m, v in t.groupby("module").usd_canon.sum().items()},
                                   contratos_max=int(t.qty.max()))
    (DIR / "RESULTADO_CAPA2.json").write_text(json.dumps(out, indent=1, default=float))
    for k, v in out["variantes"].items(): print("VAR", k, v["veredicto_limpio"], {n: v[n]["dif_atr"] for n in ("2006-2011", "2012-2019", "2020-2025")})
    for k, v in out["cartera"].items(): print("CARTERA", k, v["usd_total"], v["anios_pos"], v["max_dd_usd"])


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
    if c == "correr": _con_costos(sys.argv[4], {"fs": correr_fs, "t2008": correr_t2008, "som": correr_som, "estado": correr_estado, "variantes": correr_variantes, "cartera": correr_cartera, "franklin": correr_franklin}[sys.argv[3]], sys.argv[4], sys.argv[2])
    elif c == "analizar": analizar()
    elif c == "analizar_capa2": analizar_capa2()
    elif c == "analizar_franklin": analizar_franklin()
    elif c == "analizar_indices": analizar_indices()
    elif c == "analizar_franklin_nuevos": analizar_franklin_nuevos()
    elif c == "viejas": (viejas_edgereplica(sys.argv[2]), viejas_oro415(sys.argv[2]))
