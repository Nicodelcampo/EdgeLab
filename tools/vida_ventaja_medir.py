#!/usr/bin/env python3
"""Paso 1 de docs/research/urgencia_vs_evidencia_20261117/PROPUESTA.md: vida de una ventaja (edgelab/research/vida_ventaja.py) sobre la
población NO elegida del catálogo SQX (las 68 reglas × instrumento, variante original, 2004/2012 → 2026-09-29; nada del holdout).
Pre-registro: docs/research/urgencia_vs_evidencia_20261117/PREREGISTRO_PASO1.md.

  python tools/vida_ventaja_medir.py potencia     # SÓLO operaciones por mes (sin R): qué τ se detecta con esta estructura
  python tools/vida_ventaja_medir.py medir        # ajuste por familia y conjunto + nulo paramétrico (τ = 0) + BH -> RESULTADO_PASO1.json
  python tools/vida_ventaja_medir.py m1_potencia | m1   # paso 1b (grilla M1 intradía; PREREGISTRO_PASO1B.md): potencia sin R, después ajuste
  python tools/vida_ventaja_medir.py diagnostico  # enmienda 1: grilla de ρ extendida, R BRUTO (¿régimen o fricción?), residuos
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OPS = ROOT / "docs/research/sqx_catalogo_20261117/ops"; OUT = ROOT / "docs/research/urgencia_vs_evidencia_20261117"
FAMILIAS = {"tendencia": ("TURTLE_55_20", "TURTLE_20_10", "ADX_TRAIL"), "reversion": ("MR_A", "MR_B", "BUY_DIPS", "PRICE_DIP", "DOUBLE7"),
            "ruptura_corta": ("RANGE_1300", "INSIDE_BAR"), "cot": ("COT1_CROWDING", "COT2_SPREAD", "COT3_TREND"), "volumen": ("VP_POC_USDJPY",)}
B_NULO, SEMILLA, FIN = 500, 20261117, pd.Period("2026-09", "M")


def series(con_R: bool, col: str = "R"):
    """{familia: [(nombre, suma, n)]}. Sin R (potencia): suma = 0. Cada serie va de su primer mes con operaciones a 2026-09."""
    from edgelab.research.vida_ventaja import mensual
    out = {f: [] for f in FAMILIAS}
    for f in sorted(OPS.glob("*_original.csv.gz")):
        nom = f.name.replace("_original.csv.gz", ""); est = nom.rsplit("_", 1)[0]
        fam = next((k for k, v in FAMILIAS.items() if est in v), None)
        if fam is None: continue
        g = pd.read_csv(f, usecols=["dia", col] if con_R else ["dia"]); p = pd.to_datetime(g.dia).dt.to_period("M")
        if not len(g): continue
        ini = p.min(); m = np.asarray((p - ini).apply(lambda x: x.n)); T = (FIN - ini).n + 1
        if con_R: s, n = mensual(g[col].to_numpy(float), m, T)
        else: n = np.bincount(m, minlength=T).astype(float); s = np.zeros(T)
        out[fam].append((nom, s, n))
    return out


def potencia():
    from edgelab.research import vida_ventaja as V
    S = series(con_R=False); res = {}
    grupos = dict(S, conjunto=[x for v in S.values() for x in v])
    for g, lst in grupos.items():
        estr = [n for _, _, n in lst]
        crit = np.quantile([V.ajustar(V.generar_series(estr, 0.9, 0.0, seed=SEMILLA + b))["lr_tau0"] for b in range(100)], 0.95)
        fila = dict(series=len(lst), ops=int(sum(n.sum() for n in estr)), lr_critico_95=float(crit))
        for tau in (0.03, 0.05, 0.1):
            for rho in (0.8, 0.95):
                det = [V.ajustar(V.generar_series(estr, rho, tau, seed=SEMILLA + 1000 + b))["lr_tau0"] > crit for b in range(50)]
                fila[f"tau{tau}_rho{rho}"] = float(np.mean(det))
        res[g] = fila; print(g, fila, flush=True)
    (OUT / "POTENCIA_PASO1.json").write_text(json.dumps(res, indent=1)); return res


def medir():
    from edgelab.research import vida_ventaja as V
    from fundedsync_tanda2 import _bh
    S = series(con_R=True); res = dict(preregistro="docs/research/urgencia_vs_evidencia_20261117/PREREGISTRO_PASO1.md", grupos={})
    grupos = dict(S, conjunto=[x for v in S.values() for x in v])
    for g, lst in grupos.items():
        sr = [(s, n) for _, s, n in lst]; a = V.ajustar(sr)
        nulo = [V.ajustar(V.generar_series([n for _, n in sr], 0.9, 0.0, seed=SEMILLA + b))["lr_tau0"] for b in range(B_NULO)]
        a["p_tau0"] = float((1 + sum(x >= a["lr_tau0"] for x in nulo)) / (B_NULO + 1)); a["series"] = [nom for nom, _, _ in lst]
        res["grupos"][g] = a; print(g, {k: a[k] for k in ("rho", "tau", "lr_tau0", "p_tau0", "vida_media_meses", "ic_rho", "ic_tau")}, flush=True)
    ks = list(res["grupos"]); bh = _bh([res["grupos"][k]["p_tau0"] for k in ks])
    for k, b in zip(ks, bh):
        g = res["grupos"][k]; g["regimen_detectado"] = bool(b and g["tau"] > 0)
    (OUT / "RESULTADO_PASO1.json").write_text(json.dumps(res, indent=1, default=float))


def diagnostico():
    """Enmienda 1 (después de ver ρ en el borde de la grilla, 0,99): no cambia la decisión del pre-registro; precisa L y prueba si el
    régimen es de mercado o de fricción (la fricción fija pesa más en R cuando la volatilidad baja y el stop se achica: K2)."""
    from edgelab.research import vida_ventaja as V
    rho_ext = V.GRILLA_RHO + (0.993, 0.995, 0.997, 0.998, 0.999); res = {}
    for col in ("R", "Rb"):
        S = series(con_R=True, col=col); grupos = dict(ruptura_corta=S["ruptura_corta"], conjunto=[x for v in S.values() for x in v])
        for g, lst in grupos.items():
            sr = [(s, n) for _, s, n in lst]; a = V.ajustar(sr, grilla_rho=rho_ext)
            nulo = [V.ajustar(V.generar_series([n for _, n in sr], 0.9, 0.0, seed=SEMILLA + b), grilla_rho=rho_ext)["lr_tau0"] for b in range(300)]
            a["p_tau0"] = float((1 + sum(x >= a["lr_tau0"] for x in nulo)) / 301)
            z = np.concatenate([V.innovaciones(s, n, a["rho"], a["tau"]) for s, n in sr])
            a["innovaciones"] = dict(n=int(len(z)), media=float(z.mean()), sd=float(z.std()), p01=float(np.quantile(z, 0.01)), p99=float(np.quantile(z, 0.99)),
                                     frac_abs_mayor_3=float((np.abs(z) > 3).mean()))
            res[f"{g}|{col}"] = a
            print(g, col, {k: a[k] for k in ("rho", "tau", "lr_tau0", "p_tau0", "vida_media_meses", "ic_rho", "ic_tau")}, a["innovaciones"], flush=True)
    (OUT / "DIAGNOSTICO_PASO1.json").write_text(json.dumps(res, indent=1, default=float))


# ---------------------------------------------------------------- paso 1b: grilla M1 intradía (PREREGISTRO_PASO1B.md)
IDX8 = ("SP_M1_dukas", "NQ_M1_dukas", "DJ_M1_dukas", "USSC2000IDXUSD", "DEUIDXEUR", "JPNIDXJPY", "GBRIDXGBP", "EUSIDXEUR")
CANONICA = {"ORB": "ORB|{s}|30|BRK|OPUESTO|0", "PRERANGO": "PRERANGO|{s}", "VWAPB": "VWAPB|{s}|3|REV|VWAP|K+1"}     # declaradas por nombre


def series_m1(col="neto", con_R=True):
    """{clave: (suma_z, n)} desde M1_VIDA.json: σ de cada serie con sus sumas totales (R recortado en el kernel)."""
    d = json.loads((OUT / "M1_VIDA.json").read_text())["series"]; out = {}
    for k, v in d.items():
        meses = pd.PeriodIndex(v["mes"], freq="M"); ini = meses.min(); T = (FIN - ini).n + 1; pos = np.asarray([(m - ini).n for m in meses])
        n = np.zeros(T); n[pos] = v["n"]; s = np.zeros(T)
        if con_R:
            N, S, Q = sum(v["n"]), sum(v["s_" + col]), sum(v["q_" + col]); sd = np.sqrt(max((Q - S * S / N) / max(N - 1, 1), 1e-12))
            s[pos] = np.asarray(v["s_" + col]) / sd
        out[k] = (s, n)
    return out


def grupos_m1(S):
    can = {f: [CANONICA[f].format(s=x) for x in IDX8 if CANONICA[f].format(s=x) in S] for f in CANONICA}
    g = {f"canonica_{f}": v for f, v in can.items()}
    g["dominio_cartera"] = [k for f in can.values() for k in f if k.split("|")[1] in ("NQ_M1_dukas", "SP_M1_dukas", "DJ_M1_dukas")]
    g["canonica_conjunto"] = [k for f in can.values() for k in f]
    desc = {f"todas_{f}": [k for k in S if k.startswith(f + "|")] for f in CANONICA}
    return g, desc


def m1_potencia():
    from edgelab.research import vida_ventaja as V
    S = series_m1(con_R=False); g, _ = grupos_m1(S); res = {}
    for nom, ks in g.items():
        estr = [S[k][1] for k in ks]
        crit = np.quantile([V.ajustar(V.generar_series(estr, 0.9, 0.0, seed=SEMILLA + b))["lr_tau0"] for b in range(100)], 0.95)
        fila = dict(series=len(ks), ops=int(sum(n.sum() for n in estr)), lr_critico_95=float(crit))
        for tau in (0.03, 0.05, 0.1):
            fila[f"tau{tau}_rho0.95"] = float(np.mean([V.ajustar(V.generar_series(estr, 0.95, tau, seed=SEMILLA + 1000 + b))["lr_tau0"] > crit for b in range(50)]))
        res[nom] = fila; print(nom, fila, flush=True)
    (OUT / "POTENCIA_PASO1B.json").write_text(json.dumps(res, indent=1)); return res


def m1():
    from edgelab.research import vida_ventaja as V
    from fundedsync_tanda2 import _bh
    pot = json.loads((OUT / "POTENCIA_PASO1B.json").read_text()); rho_ext = V.GRILLA_RHO + (0.993, 0.995, 0.997, 0.998, 0.999)
    res = dict(preregistro="docs/research/urgencia_vs_evidencia_20261117/PREREGISTRO_PASO1B.md", grupos={})
    for col in ("neto", "bruto"):
        S = series_m1(col); g, desc = grupos_m1(S)
        for nom, ks in list(g.items()) + list(desc.items()):
            sr = [S[k] for k in ks]; a = V.ajustar(sr, grilla_rho=rho_ext)
            B = 300 if nom in g else 100
            nulo = [V.ajustar(V.generar_series([n for _, n in sr], 0.9, 0.0, seed=SEMILLA + b), grilla_rho=rho_ext)["lr_tau0"] for b in range(B)]
            a["p_tau0"] = float((1 + sum(x >= a["lr_tau0"] for x in nulo)) / (B + 1)); a["series"] = ks
            a["decide"] = bool(nom in g and pot.get(nom, {}).get("tau0.05_rho0.95", 0) >= 0.5)
            z = np.concatenate([V.innovaciones(s, n, a["rho"], a["tau"]) for s, n in sr]); a["innov_sd"] = float(z.std())
            res["grupos"][f"{nom}|{col}"] = a
            print(nom, col, {k: a[k] for k in ("rho", "tau", "lr_tau0", "p_tau0", "vida_media_meses", "ic_rho", "ic_tau", "decide", "innov_sd")}, flush=True)
    dec = [k for k, a in res["grupos"].items() if a["decide"] and k.endswith("|neto")]
    for k, b in zip(dec, _bh([res["grupos"][k]["p_tau0"] for k in dec]) if dec else []):
        a = res["grupos"][k]; br = res["grupos"][k.replace("|neto", "|bruto")]
        a["regimen_neto"] = bool(b and a["tau"] > 0); a["regimen_de_mercado"] = bool(a["regimen_neto"] and br["p_tau0"] < 0.05 and br["tau"] > 0)
    (OUT / "RESULTADO_PASO1B.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    {"potencia": potencia, "medir": medir, "diagnostico": diagnostico, "m1_potencia": m1_potencia, "m1": m1}[sys.argv[1]]()
