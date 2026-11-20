#!/usr/bin/env python3
"""Confirmación de ORB-A5 O1 (ORB de 5 min) en una sola lectura: holdout A5 de NQ/ES/YM + MidCap (EMD) y Russell (RTY) completos.
Pre-registro: docs/research/orb_a5_20261118/PREREGISTRO_CONFIRMACION_O1.md (la apertura y la reserva de α se registran ANTES de correr).

  python tools/orb_confirmacion_o1.py abrir                  # exige el pre-registro commiteado; reserva LORD++ y registra la apertura
  python tools/orb_confirmacion_o1.py correr [datos M1 NT8]  # desenlaces SÓLO de lo declarado (O1 en HOLDOUT de NQ/ES/YM; EMD y RTY completos)
  python tools/orb_confirmacion_o1.py analizar               # decisión pre-registrada → CONFIRMACION_O1.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.research import a5 as A5  # noqa: E402

DIR = ROOT / "docs/research/orb_a5_20261118"; PRE = DIR / "PREREGISTRO_CONFIRMACION_O1.md"
FAMILIA, RESERVA, CID = "ORB_A5", "CONF_O1_20261118", "ORB_A5::CONF_O1_20261118"
FUENTES = {"NQ": (20060106, 20250731, "HOLDOUT"), "ES": (20060106, 20250731, "HOLDOUT"), "YM": (20060106, 20250731, "HOLDOUT"),
           "EMD": (20060109, 20250731, "TODO"), "RTY": (20170710, 20250731, "TODO")}
N_FIJO, EFECTO, SD = 10089, 0.090, 2.56
EJ = "P_obj_stop_fin"


def abrir():
    from a5_campana import _commiteado
    from edgelab.funnel.libro_lord import LibroLord
    from edgelab.research import holdout_ventanas as HV
    if not _commiteado(PRE): raise SystemExit("el pre-registro no está commiteado")
    res = LibroLord().reservar(FAMILIA, RESERVA, "confirmación O1 (holdout A5 NQ/ES/YM + EMD + RTY)")
    plan = HV.plan_potencia("fijo", EFECTO, SD, n=N_FIJO, alfa=res["nivel"], fuente_efecto="REP de ORB-A5 (+0,090, no usado para elegir)")
    fila = HV.registrar_apertura(FAMILIA, CID, 20060106, N_FIJO, plan=plan)
    (DIR / "APERTURA_CONF_O1.json").write_text(json.dumps(dict(reserva=res, plan=plan, apertura=fila), indent=1, default=float))
    print(json.dumps(dict(nivel=res["nivel"], potencia=plan["potencia"])))


def correr(datos):
    from a5_campana import _ctx, _commiteado
    from edgelab.research import orb_a5 as M, ejecucion as X, rasgos_comunes as RC
    if not (DIR / "APERTURA_CONF_O1.json").exists() or not _commiteado(DIR / "APERTURA_CONF_O1.json"):
        raise SystemExit("la apertura no está registrada y commiteada")
    partes = []
    for inst, (a, b, que) in FUENTES.items():
        ctx = _ctx(inst, datos, a, b); E = M.eventos(ctx); E = E[E.O1.astype(bool)].reset_index(drop=True)
        k = E.k.to_numpy(np.int64); E["ses"] = np.asarray(ctx["ses"])[k]; E["t"] = np.asarray(ctx["t"], float)[k]
        E["bloque"] = A5.bloques(E.ses.to_numpy())
        if que == "HOLDOUT": E = E[E.bloque == "HOLDOUT"].reset_index(drop=True)
        T = X.desenlaces(RC.agregar(E, ctx), ctx, M.EJECUCIONES); T["inst"] = inst
        # tercil de volatilidad: ATR20 RTH causal de la sesión, en terciles dentro del instrumento (descriptivo de la condición)
        mo = M.minuto_ny(ctx["t"]); h, l, ses = np.asarray(ctx["h"]), np.asarray(ctx["l"]), np.asarray(ctx["ses"])
        rth = (mo >= 570) & (mo < 960); rr = pd.Series(h[rth] - 0).groupby(ses[rth]).max() - pd.Series(l[rth]).groupby(ses[rth]).min()
        atr = rr.rolling(20).mean().shift(1); T["atr20"] = T.ses.map(atr).to_numpy(float)
        partes.append(T); print(inst, que, len(T), flush=True)
    O = pd.concat(partes, ignore_index=True)
    cols = ["k", "ses", "t", "inst", "bloque", "lado", "obj", "stop", "atr20", f"r_{EJ}", f"k_{EJ}"]
    O[cols].to_csv(DIR / "OPS_CONFIRMACION_O1.csv.gz", index=False)


def analizar():
    from edgelab.funnel.libro_lord import LibroLord
    from edgelab.research.embudo_runners import friccion
    from edgelab import costos as C
    O = pd.read_csv(DIR / "OPS_CONFIRMACION_O1.csv.gz"); O = O[O[f"r_{EJ}"].notna() & (O[f"k_{EJ}"] > 0)].copy()
    r = O[f"r_{EJ}"].to_numpy(float); ses = O.ses.to_numpy(np.int64)
    m, se, p = A5.cluster(ses, r)
    dec = LibroLord().resolver(FAMILIA, RESERVA, [("O1", p)])
    anios = A5.frac_anios_positivos(ses, r)
    O["ter"] = O.groupby("inst").atr20.transform(lambda x: pd.qcut(x.rank(method="first"), 3, labels=False) if x.notna().sum() >= 3 else np.nan)
    ter = {}
    for tq in (0, 1, 2):
        g = O[O.ter == tq]; mm, ss, pp = A5.cluster(g.ses.to_numpy(np.int64), g[f"r_{EJ}"].to_numpy(float)) if len(g) else (np.nan, np.nan, 1.0)
        ter[int(tq)] = dict(n=int(len(g)), R=mm, p_contra=(1 - pp) if len(g) else None)
    contra = any(v["R"] == v["R"] and v["R"] < 0 and v["p_contra"] < 0.05 for v in ter.values())
    conf = bool(dec.get("rechazo") and m > 0 and anios >= 0.6 and not contra)
    veredicto = "CONFIRMADA" if conf else ("REFUTADA" if m <= 0 else "NO_CONFIRMADA_SIN_POTENCIA")
    # descriptivo: por instrumento, fuente, época y neto (mini y micro; EMD con costo estimado dentro del permiso K33 de este pre-registro)
    micro = {"NQ": "MNQ", "ES": "MES", "YM": "MYM", "EMD": "EMD", "RTY": "RTY"}
    with C.estimados_permitidos(str(PRE.relative_to(ROOT))):
        fr_mini = {i: float(friccion(i)[0]) for i in FUENTES}; fr_micro = {i: float(friccion(micro[i])[0]) for i in FUENTES}
    O["n_mini"] = r - O.inst.map(fr_mini) / O[f"k_{EJ}"]; O["n_micro"] = r - O.inst.map(fr_micro) / O[f"k_{EJ}"]
    O["fR_mini"] = O.inst.map(fr_mini) / O[f"k_{EJ}"]; O["anio"] = O.ses // 10000
    por = {}
    for inst, g in O.groupby("inst"):
        mi, si, pi = A5.cluster(g.ses.to_numpy(np.int64), g[f"r_{EJ}"].to_numpy(float))
        por[inst] = dict(n=int(len(g)), R_bruto=mi, se=si, p=pi, neto_mini=float(g.n_mini.mean()), neto_micro=float(g.n_micro.mean()))
    epoca = {}
    for nom, (a, b) in {"2006-11": (2006, 2011), "2012-19": (2012, 2019), "2020-25": (2020, 2025)}.items():
        g = O[(O.anio >= a) & (O.anio <= b)]; op = g[g.fR_mini <= 0.08]
        epoca[nom] = dict(n=int(len(g)), R_bruto=float(g[f"r_{EJ}"].mean()), neto_mini=float(g.n_mini.mean()), neto_micro=float(g.n_micro.mean()),
                          operable_n=int(len(op)), operable_neto_mini=float(op.n_mini.mean()) if len(op) else None)
    fuente = {k: dict(n=int(len(g)), R_bruto=float(g[f"r_{EJ}"].mean())) for k, g in
              (("holdout_A5_NQ_ES_YM", O[O.inst.isin(["NQ", "ES", "YM"])]), ("indices_nuevos_EMD_RTY", O[O.inst.isin(["EMD", "RTY"])]))}
    out = dict(preregistro=str(PRE.relative_to(ROOT)), n=int(len(O)), R_bruto=m, se=se, p=p, lord=dec, frac_anios_pos=anios, terciles=ter,
               tercil_en_contra=contra, veredicto=veredicto, por_instrumento=por, por_fuente=fuente, por_epoca=epoca,
               mde80=float(2.49 * se) if se == se else None)
    (DIR / "CONFIRMACION_O1.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps({k: out[k] for k in ("n", "R_bruto", "se", "p", "veredicto")}, default=float))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"abrir": abrir, "correr": lambda: correr(a[1] if len(a) > 1 else None), "analizar": analizar}[a[0]]()
