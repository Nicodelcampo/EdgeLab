#!/usr/bin/env python3
"""SELECTIVIDAD (pre-registro docs/research/selectividad_20261119/PREREGISTRO.md): pureza del día de tendencia → continuación al día siguiente,
con una sola perilla (percentil causal de la pureza) y dosis-respuesta en 5 bandas fijas. Motor calibrado sqx_catalogo.simular (K28) sobre barras
RTH de 15 min con camino M1; una corrida con todas las señales y después cada operación se asigna a la banda de su día de señal.

  python tools/selectividad.py correr   # → OPS.csv.gz (sólo DESC/REP)
  python tools/selectividad.py desc     # P1 pendiente, P2 banda 5 → DESC.json (commitear antes de rep)
  python tools/selectividad.py rep      # nominadas con potencia en días ≥ 0,8 (K49), una vez con LORD++ → REP.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/selectividad_20261119"; PRE = "docs/research/selectividad_20261119/PREREGISTRO.md"; FAM = "SELECTIVIDAD_A5"
INST = ("NQ", "ES", "YM", "RTY"); FIN = 20250731; BORDES = [0.0, 0.50, 0.70, 0.85, 0.95, 1.0001]; K_STOP = 0.25


def pureza(D):
    """Por día RTH (09:30–15:59): dirección, pureza = 1 − retroceso máximo contra la dirección / rango, minutos."""
    mm = D.index.hour * 60 + D.index.minute; R = D[(mm >= 570) & (mm < 960)]; filas = {}
    for d, g in R.groupby(R.index.normalize()):
        o, h, l, c = g.o.iloc[0], g.h.to_numpy(), g.l.to_numpy(), g.c.iloc[-1]; rng = h.max() - l.min(); lado = np.sign(c - o)
        if rng <= 0 or lado == 0 or len(g) < 380: filas[d] = (np.nan, 0, len(g)); continue
        retro = (np.maximum.accumulate(h) - l).max() if lado > 0 else (h - np.minimum.accumulate(l)).max()
        filas[d] = (1.0 - retro / rng, int(lado), len(g))
    P = pd.DataFrame.from_dict(filas, orient="index", columns=["pureza", "lado", "minutos"]).sort_index()
    s = P.pureza.to_numpy(); pct = np.full(len(s), np.nan)
    for i in range(len(s)):
        prev = s[max(0, i - 250):i]; prev = prev[np.isfinite(prev)]
        if np.isfinite(s[i]) and len(prev) >= 120: pct[i] = float((prev < s[i]).mean())
    P["pct"] = pct; return P, R


def correr():
    from registro_global import exigir_contada
    from datos import ruta
    from m1_largo import cargar, atr20
    from edgelab.research import sqx_catalogo as Q
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import a5_bloque
    exigir_contada(PRE); partes = []
    for inst in INST:
        D = cargar(inst, ruta("M1NT8")); P, R = pureza(D); A = atr20(D)
        B = Q.barras_desde_m1(R, "M15"); m1 = Q.indices_m1(B, R, "M15"); f = B.fecha.to_numpy(); n = len(B)
        ultimo = np.r_[f[1:] != f[:-1], True]
        fechas = pd.to_datetime(pd.Series(f).astype(str)).to_numpy(); dias = np.unique(fechas)
        sig_dia = {pd.Timestamp(d): (P.lado.get(pd.Timestamp(d), 0), P.pct.get(pd.Timestamp(d), np.nan)) for d in dias}
        nxt = {pd.Timestamp(dias[i]): pd.Timestamp(dias[i + 1]) for i in range(len(dias) - 1)}
        lado = np.zeros(n, int); sl = np.full(n, np.nan)
        for i in np.flatnonzero(ultimo):
            d = pd.Timestamp(fechas[i]); ld, pc = sig_dia[d]
            if d not in nxt or not np.isfinite(pc) or ld == 0: continue
            a = A.get(nxt[d], np.nan)
            if np.isfinite(a) and a > 0: lado[i] = int(ld); sl[i] = K_STOP * a
        sig = dict(lado=lado, tipo="mkt", sl=sl, tp=np.nan, salida=lambda i, ld: bool(ultimo[i]))
        O = Q.simular(B, sig, viernes=False, m1=m1); fr = float(friccion(inst)[0])
        rg = (O.entrada - O.stop0).abs(); O["R"] = (O.lado * (O.salida_px - O.entrada) - fr) / rg; O["Rb"] = O.lado * (O.salida_px - O.entrada) / rg
        O["fricR"] = fr / rg; O["fecha_senal"] = [int(pd.Timestamp(fechas[max(i - 1, 0)]).strftime("%Y%m%d")) for i in O.i0]
        O["pct"] = [sig_dia[pd.Timestamp(str(x))][1] for x in O.fecha_senal]; O["inst"] = inst
        assert (O.barras <= 26).all(), "una operación cruzó de día (no debería: sale en la última vela)"
        partes.append(O[O.stop0.notna() & (rg > 0)]); print(inst, len(O), flush=True)
    T = pd.concat(partes, ignore_index=True); T["banda"] = np.digitize(T.pct, BORDES)
    T["bloque"] = [a5_bloque(int(x)) for x in T.fecha]; T = T[(T.fecha <= FIN) & T.bloque.isin(["DESC", "REP"])]
    T.to_csv(DIR / "OPS.csv.gz", index=False); print(T.groupby(["banda", "bloque"]).size().unstack().to_string())


def _pruebas(T, B=4000, seed=7):
    from carril2 import _media
    ses = T.fecha.to_numpy(); u, inv = np.unique(ses, return_inverse=True); x = T.banda.to_numpy(float); y = T.R.to_numpy(float)
    def pend(ix):
        m = np.isin(inv, ix); xx, yy = x[m], y[m]; return float(np.polyfit(xx, yy, 1)[0]) if len(np.unique(xx)) > 1 else np.nan
    obs = pend(np.arange(len(u))); rng = np.random.default_rng(seed)
    bs = np.array([pend(rng.integers(0, len(u), len(u))) for _ in range(B)]); se = float(np.nanstd(bs, ddof=1))
    from edgelab.research.a5 import sf
    b5 = T[T.banda == 5]; m, se2, p2 = _media(b5.fecha.to_numpy(), b5.R.to_numpy())
    return dict(P1=dict(pendiente=obs, se=se, p=float(sf(obs / se)) if se > 0 else 1.0), P2=dict(R_B5=m, se=se2, p=p2, n=int(len(b5))))


def desc():
    from edgelab.research.a5 import bh
    from edgelab.research.diagnostico_grilla import episodios
    T = pd.read_csv(DIR / "OPS.csv.gz"); D = T[T.bloque == "DESC"]; r = _pruebas(D)
    rech = bh([r["P1"]["p"], r["P2"]["p"]], 0.10); r["P1"]["bh"] = bool(rech[0] and r["P1"]["pendiente"] > 0); r["P2"]["bh"] = bool(rech[1] and r["P2"]["R_B5"] > 0)
    r["por_banda"] = {int(b): dict(n=int(len(g)), R=round(float(g.R.mean()), 4), Rb=round(float(g.Rb.mean()), 4), fricR_med=round(float(g.fricR.median()), 4))
                      for b, g in D.groupby("banda")}
    r["por_inst_banda"] = {f"{i}|{int(b)}": round(float(g.R.mean()), 4) for (i, b), g in D.groupby(["inst", "banda"])}
    r["por_epoca_banda"] = {f"{e}|{int(b)}": round(float(g.R.mean()), 4) for (e, b), g in D.assign(e=pd.cut(D.fecha // 10000, [2005, 2011, 2017, 2026], labels=["06-11", "12-17", "18-25"]).astype(str)).groupby(["e", "banda"])}
    b5 = D[D.banda == 5].assign(mes=lambda x: (x.fecha // 100).astype(str)); r["episodios_B5"] = episodios(b5)["linea"]
    r["nominadas"] = [k for k in ("P1", "P2") if r[k]["bh"]]
    (DIR / "DESC.json").write_text(json.dumps(dict(preregistro=PRE, **r), indent=1, default=float)); print(json.dumps(r, indent=1, default=float)[:5000])


def rep():
    from a5_campana import _commiteado
    from edgelab.research import a5 as A5
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / "DESC.json"): raise SystemExit("DESC.json sin commitear")
    J = json.loads((DIR / "DESC.json").read_text()); T = pd.read_csv(DIR / "OPS.csv.gz"); out = {}
    if not J["nominadas"]: out["estado"] = "SIN_NOMINADAS"
    else:
        D5 = T[(T.bloque == "DESC") & (T.banda == 5)]; n_rep = int(T[(T.bloque == "REP") & (T.banda == 5)].fecha.nunique())
        plan = A5.plan_lectura(FAM, D5.fecha.to_numpy(), D5.R.to_numpy(float), n_rep); out["plan_B5"] = plan
        if (plan.get("potencia") or 0) < A5.POTENCIA_LECTURA_MIN and "P1" not in J["nominadas"]: out["estado"] = "SIN_POTENCIA_PREVIA"
        else:
            r = _pruebas(T[T.bloque == "REP"]); dec = LibroLord().probar(FAM, "REP_SELECTIVIDAD", [(k, r[k]["p"]) for k in J["nominadas"]])
            out.update(rep=r, lord=dec, confirmadas=dec.get("confirmadas"))
    (DIR / "REP.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, default=float)[:2000])


if __name__ == "__main__":
    {"correr": correr, "desc": desc, "rep": rep}[sys.argv[1]]()
