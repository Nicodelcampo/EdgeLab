#!/usr/bin/env python3
"""GEX a fondo (pre-registro docs/research/gex_tendencia_20261118/PREREGISTRO.md): variantes de gamma, desenlaces continuos y momentum
intradía condicionado a gamma (Baltussen et al. 2021). Fase 1 SÓLO en meses DESC de A5; el holdout se abre una vez, aparte.

Reusa `dia_tendencia._dia` (día RTH, ATR20, E1/E3, p1000) y `_rank`, `fundedsync_tanda2._auc`, `a5.diferencia`, `holdout.a5_bloque`.

  python tools/gex_tendencia.py tabla     # DESC: filas (instrumento, día) con gamma y desenlaces -> TABLA_DESC.csv.gz
  python tools/gex_tendencia.py explorar  # 54 medidas exploratorias -> EXPLORACION.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/gex_tendencia_20261118"
INST = ("NQ", "ES", "YM", "RTY")
PRED = ("g_rank250", "g_rank60", "g_neg", "g_z20", "g_chg", "g_esc", "dix_rank250")
SIGNO_ECON = {"g_rank250": -1, "g_rank60": -1, "g_neg": 1, "g_z20": -1, "g_chg": -1, "g_esc": -1, "dix_rank250": 0}   # menos gamma -> más tendencia


def gamma(bloques=("DESC",)) -> pd.DataFrame:
    """Variantes de gamma del cierre de d−1, indexadas por el día d."""
    from dia_tendencia import _rank
    G = pd.read_csv(ROOT / "data/DIX_squeezemetrics_20261108.csv", parse_dates=["date"]).set_index("date").sort_index()
    X = pd.DataFrame(index=G.index)
    X["g_rank250"] = _rank(G.gex, 250); X["g_rank60"] = _rank(G.gex, 60); X["g_neg"] = (G.gex < 0).astype(float)
    X["g_z20"] = (G.gex - G.gex.rolling(20).mean()) / G.gex.rolling(20).std()
    X["g_chg"] = X.g_rank250.diff(); X["g_esc"] = _rank(G.gex / G.price ** 2, 250); X["dix_rank250"] = _rank(G.dix, 250)
    return X.shift(1)                                                             # el dato de d−1 para el día d


def _dia_ext(inst):
    from datos import ruta
    from edgelab.research.m1_intradia import leer_m1nt8
    from dia_tendencia import _dia
    day = _dia(inst)
    D = leer_m1nt8(Path(ruta("M1NT8")) / f"{inst}_M1_nonadj_utc.parquet"); m = D.index.hour * 60 + D.index.minute
    q = D[m == 929]; day["p1530"] = q.c.groupby(q.index.normalize()).last().reindex(day.index)
    a = day.atr20
    day["Y1"] = (day.c - day.o).abs() / a; day["Y2"] = (day.h - day.l) / a
    day["Y4"] = np.sign(day.p1530 - day.o) * (day.c - day.p1530) / a
    day["Y5"] = np.sign(day.p1000 - day.o) * (day.c - day.p1000) / a
    day["vol20_t"] = pd.qcut(a.rank(method="first"), 3, labels=False)
    day["gap_t"] = pd.qcut(((day.o - day.c.shift(1)).abs() / a).rank(method="first"), 3, labels=False)
    return day


def tabla():
    from edgelab.holdout import a5_bloque
    g = gamma(); partes = []
    for inst in INST:
        d = _dia_ext(inst).join(g, how="left"); d["inst"] = inst; partes.append(d); print(inst, len(d), flush=True)
    T = pd.concat(partes); T["fecha"] = T.index.strftime("%Y%m%d").astype(int)
    T["bloque"] = [a5_bloque(int(f)) for f in T.fecha]
    T = T[(T.bloque == "DESC") & (T.fecha <= 20250731) & T.g_rank250.notna()]   # SÓLO DESC (REP consumido, HOLDOUT sellado)
    cols = ["fecha", "inst", "bloque", "E1", "E3", "Y1", "Y2", "Y4", "Y5", "vol20_t", "gap_t"] + list(PRED)
    DIR.mkdir(parents=True, exist_ok=True); T[cols].to_csv(DIR / "TABLA_DESC.csv.gz", index=False); print("DESC", len(T), T.fecha.nunique(), "días")


def _boot_dif(T, mask_a, mask_b, y, B=2000, seed=7):
    from edgelab.research.a5 import diferencia
    a, b = T[mask_a], T[mask_b]
    return diferencia(a.fecha.to_numpy(np.int64), a[y].to_numpy(float), b.fecha.to_numpy(np.int64), b[y].to_numpy(float), B=B, seed=seed)


def explorar():
    from fundedsync_tanda2 import _auc
    T = pd.read_csv(DIR / "TABLA_DESC.csv.gz"); out = {}
    for p in PRED:
        t = T.dropna(subset=[p]); s = SIGNO_ECON[p] or 1
        for y in ("Y1", "Y2"):
            r = t[[p, y]].rank().corr().iloc[0, 1] * s
            por = {i: float(g[[p, y]].rank().corr().iloc[0, 1] * s) for i, g in t.groupby("inst")}
            out[f"{p}|{y}"] = dict(spearman_signo_econ=float(r), por_inst=por)
        for y in ("E1", "E3"):
            out[f"{p}|{y}"] = dict(auc_signo_econ=_auc(s * t[p].values, t[y].values.astype(bool)),
                                  por_inst={i: _auc(s * g[p].values, g[y].values.astype(bool)) for i, g in t.groupby("inst")})
        for y in ("Y4", "Y5"):                                                    # bajo gamma (tercil "más tendencia") − alto
            q = pd.qcut((s * t[p]).rank(method="first"), 3, labels=False)
            d, se, pv = _boot_dif(t, q.values == 2, q.values == 0, y)
            out[f"{p}|{y}"] = dict(media_tercil=[float(t[y][q.values == k].mean()) for k in (0, 1, 2)], dif_mas_menos=d, se=se, p=pv,
                                  por_inst={i: float(g[y][(q[g.index] == 2).values].mean() - g[y][(q[g.index] == 0).values].mean()) for i, g in t.groupby("inst")})
    for z in ("vol20_t", "gap_t"):                                                # interacciones de g_rank250 con vol20 y gap
        for k in (0, 1, 2):
            t = T[T[z] == k].dropna(subset=["g_rank250"])
            out[f"g_rank250@{z}={k}|Y1"] = dict(spearman_signo_econ=float(-t[["g_rank250", "Y1"]].rank().corr().iloc[0, 1]))
            out[f"g_rank250@{z}={k}|E1"] = dict(auc_signo_econ=_auc(-t.g_rank250.values, t.E1.values.astype(bool)))
    (DIR / "EXPLORACION.json").write_text(json.dumps(dict(nota="EF2 exploratorio en DESC: no confirmatorio", medidas=len(out), resultados=out), indent=1, default=float))
    for k, v in out.items(): print(k, {a: (round(b, 4) if isinstance(b, float) else (None if b is None else (b if not isinstance(b, (list, dict)) else "…"))) for a, b in v.items() if a != "por_inst"})



# ------------------------------------------------------------------------------- fase 2: confirmación del filtro (apéndice 1)
RESERVA = "GEX_FILTRO_CONF_20261118"; FAMILIA = "DIA_TENDENCIA_A5"; CID = f"{FAMILIA}::{RESERVA}"


def _canasta_dia(bloques):
    from edgelab.holdout import a5_bloque
    D = ROOT / "docs/research/m1_largo_20261117"
    T = pd.concat([pd.read_csv(D / f"FS_OPS_T2008_{i}.csv.gz").assign(inst=i) for i in ("NQ", "ES", "YM")]); T = T[T.riesgo > 0]
    T["R"] = T.neto / T.riesgo; T["fecha"] = pd.to_datetime(T.dia).dt.strftime("%Y%m%d").astype(int)
    F = pd.concat([pd.read_csv(D / f"FRANKLIN_OPS_{i}.csv.gz").assign(inst=i) for i in ("NQ", "ES")]); F = F[F.riesgo > 0]
    S = pd.concat([pd.read_csv(D / f"SOM_OPS_{i}.csv.gz").assign(inst=i) for i in ("NQ", "ES", "YM")]); S = S[(S.celda == "sin_finde") & (S.riesgo > 0)]
    X = pd.concat([T[["fecha", "R", "inst"]].assign(regla="T"), F[["fecha", "R", "inst"]].assign(regla="FR"), S[["fecha", "R", "inst"]].assign(regla="SOM")])
    X = X[X.fecha <= 20250731]; X["bloque"] = [a5_bloque(int(f)) for f in X.fecha]; X = X[X.bloque.isin(bloques)]
    g = gamma(); g.index = g.index.strftime("%Y%m%d").astype(int); X["g"] = X.fecha.map(g["g_rank250"]); X = X.dropna(subset=["g"])
    c = json.loads((DIR / "CORTES_DESC.json").read_text())["cortes_g_rank250"]
    X["t"] = np.where(X.g < c[0], "bajo", np.where(X.g < c[1], "medio", "alto"))
    return X, X.groupby(["fecha", "t"]).R.sum().reset_index()


def abrir():
    from a5_campana import _commiteado
    from edgelab.funnel.libro_lord import LibroLord
    from edgelab.research import holdout_ventanas as HV
    if not _commiteado(DIR / "PREREGISTRO.md"): raise SystemExit("pre-registro sin commitear")
    _, dd = _canasta_dia(("DESC",)); lo, hi = dd[dd.t == "bajo"].R, dd[dd.t == "alto"].R
    efecto = float(lo.mean() - hi.mean()); sd = float(np.sqrt((lo.var() + hi.var()) / 2) * np.sqrt(2))
    _, dc = _canasta_dia(("REP", "HOLDOUT")); n = int(dc.fecha.nunique() // 3)               # sólo CUENTA días (sin desenlaces)
    res = LibroLord().reservar(FAMILIA, RESERVA, "filtro de gamma en T+Franklin+SOM, REP+HOLDOUT")
    plan = HV.plan_potencia("fijo", efecto, sd, n=n, alfa=res["nivel"], fuente_efecto="contraste DESC completo (decisión de Nico, apéndice 1)")
    fila = HV.registrar_apertura(FAMILIA, CID, 20111101, n, plan=plan)
    (DIR / "APERTURA_FILTRO.json").write_text(json.dumps(dict(reserva=res, plan=plan, apertura=fila), indent=1, default=float))
    print(json.dumps(dict(nivel=res["nivel"], potencia=plan["potencia"], efecto=efecto, n=n)))


def confirmar():
    from a5_campana import _commiteado
    from edgelab.funnel.libro_lord import LibroLord
    from edgelab.research.a5 import diferencia, cluster
    if not _commiteado(DIR / "APERTURA_FILTRO.json"): raise SystemExit("apertura sin commitear")
    X, dc = _canasta_dia(("REP", "HOLDOUT"))
    lo, hi = dc[dc.t == "bajo"], dc[dc.t == "alto"]
    d, se, p = diferencia(lo.fecha.values, lo.R.values, hi.fecha.values, hi.R.values)
    dec = LibroLord().resolver(FAMILIA, RESERVA, [("gex_filtro", p)])
    dc["anio"] = dc.fecha // 10000
    yy = dc.groupby("anio").apply(lambda x: x[x.t == "bajo"].R.mean() - x[x.t == "alto"].R.mean()).dropna(); frac = float((yy > 0).mean())
    ver = "CONFIRMADA" if (dec.get("rechazo") and d > 0 and frac >= 0.6) else ("REFUTADA" if (d <= 0 or d + 1.645 * se < 0.25) else "NO_CONFIRMADA")
    sin_alto = dc[dc.t != "alto"]; m, s2, p2 = cluster(sin_alto.fecha.values, sin_alto.R.values)
    por_regla = {r: {t: float(g[g.t == t].R.mean()) for t in ("bajo", "medio", "alto")} for r, g in X.groupby("regla")}
    out = dict(contraste=d, se=se, p=p, lord=dec, frac_anios=frac, anios=int(len(yy)), veredicto=ver,
               canasta_por_tercil={t: float(dc[dc.t == t].R.mean()) for t in ("bajo", "medio", "alto")},
               dias_por_tercil={t: int((dc.t == t).sum()) for t in ("bajo", "medio", "alto")},
               canasta_todos=float(dc.R.mean()), canasta_sin_alto=dict(R_dia=m, se=s2, p=p2), por_regla=por_regla)
    (DIR / "CONFIRMACION_FILTRO.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("contraste", "se", "p", "frac_anios", "veredicto", "canasta_por_tercil", "canasta_todos", "canasta_sin_alto")}, default=float))


# ------------------------------------------------------------------------------- apéndice 2: tres pruebas del mecanismo
def _alto(fechas):
    g = gamma(); g.index = g.index.strftime("%Y%m%d").astype(int); c = json.loads((DIR / "CORTES_DESC.json").read_text())["cortes_g_rank250"]
    v = pd.Series(fechas).map(g["g_rank250"]).to_numpy(float)
    return np.where(np.isfinite(v), v >= c[1], np.nan)


def _contraste(fechas, r, signo):
    """(alto − resto, EE, p unilateral en la dirección `signo`, fracción de años con ese signo); bootstrap por día."""
    from edgelab.research.a5 import diferencia
    a = _alto(fechas); ok = np.isfinite(a) & np.isfinite(r); f, r, a = np.asarray(fechas)[ok].astype(np.int64), np.asarray(r, float)[ok], a[ok].astype(bool)
    d, se, p = diferencia(f[a], r[a], f[~a], r[~a]); p = p if signo > 0 else 1 - p
    yy = pd.DataFrame(dict(y=f // 10000, r=r, a=a)).groupby("y").apply(lambda x: x[x.a].r.mean() - x[~x.a].r.mean()).dropna()
    return dict(contraste=d, se=se, p=p, n=int(ok.sum()), n_alto=int(a.sum()), frac_anios_signo=float((np.sign(yy) == signo).mean()), anios=int(len(yy)),
                media_alto=float(r[a].mean()), media_resto=float(r[~a].mean()))


def mecanismo():
    from edgelab.funnel.libro_lord import LibroLord
    D = ROOT / "docs/research/m1_largo_20261117"; R = {}
    # P1: canasta T + Franklin + SOM en EMD y RTY (R neto por día)
    partes = []
    for i in ("EMD", "RTY"):
        t = pd.read_csv(D / f"FS_OPS_{i}.csv.gz"); t = t[(t.modulo == "T") & (t.riesgo > 0)]; t["R"] = t.neto / t.riesgo
        t["fecha"] = pd.to_datetime(t.dia).dt.strftime("%Y%m%d").astype(int); partes.append(t[["fecha", "R"]])
        f = pd.read_csv(D / f"FRANKLIN_OPS_{i}.csv.gz"); partes.append(f[f.riesgo > 0][["fecha", "R"]])
        s = pd.read_csv(D / f"SOM_OPS_{i}.csv.gz"); partes.append(s[(s.celda == "sin_finde") & (s.riesgo > 0)][["fecha", "R"]])
    X = pd.concat(partes); X = X[(X.fecha <= 20250731) & (X.fecha >= 20111101)]; dia = X.groupby("fecha").R.sum()
    R["P1_exclusion_EMD_RTY"] = _contraste(dia.index.values, dia.values, -1)
    # P2: fade LUX-IMB (predicción opuesta)
    L = pd.read_csv(ROOT / "docs/research/luximb_ejecucion_20261118/OPS_DESC_REP.csv.gz", usecols=["ses", "z0", "r_M_sl0.5_tp1.0_N"])
    L = L[L.z0.astype(bool) & L["r_M_sl0.5_tp1.0_N"].notna() & (L.ses >= 20111101)]
    R["P2_fade_luximb"] = _contraste(L.ses.values, L["r_M_sl0.5_tp1.0_N"].values, +1)
    # P3: ORB O1 (operaciones de confirmación)
    O = pd.read_csv(ROOT / "docs/research/orb_a5_20261118/OPS_CONFIRMACION_O1.csv.gz"); O = O[O["r_P_obj_stop_fin"].notna() & (O["k_P_obj_stop_fin"] > 0)]
    R["P3_orb_o1"] = _contraste(O.ses.values, O["r_P_obj_stop_fin"].values, -1)
    dec = LibroLord().probar(FAMILIA, "GEX_MECANISMO_20261118", [(k, v["p"]) for k, v in R.items()])
    conf = {c["test"] for c in dec.get("confirmadas", [])}
    for k, v in R.items(): v["confirmada"] = bool(k in conf and v["frac_anios_signo"] >= 0.6)
    mec = bool((R["P1_exclusion_EMD_RTY"]["confirmada"] or R["P3_orb_o1"]["confirmada"]) and R["P2_fade_luximb"]["confirmada"])
    out = dict(preregistro="docs/research/gex_tendencia_20261118/PREREGISTRO.md (apéndice 2)", pruebas=R, lord=dec, mecanismo_confirmado=mec)
    (DIR / "MECANISMO.json").write_text(json.dumps(out, indent=1, default=float))
    for k, v in R.items(): print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()})
    print("nivel", dec.get("nivel"), "mecanismo confirmado:", mec)


if __name__ == "__main__":
    {"tabla": tabla, "explorar": explorar, "abrir": abrir, "confirmar": confirmar, "mecanismo": mecanismo}[sys.argv[1]]()
