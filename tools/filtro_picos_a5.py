#!/usr/bin/env python3
"""FILTRO-PICOS con la partición A5 (pre-registro docs/research/filtro_picos_20261118/PREREGISTRO.md): análisis PAREADO por gatillo.

La calibración y la corrida son las genéricas (`tools/a5_campana.py calibrar_m1|lanzar_ticks|traer_ticks|calibracion|correr`); acá sólo
el análisis, que necesita pares: por cada gatillo de una base, el valor de una configuración es su R si entró (0 si no entró) y se
compara con la entrada inmediata de la regla base (INM) y con el placebo de la misma espera (PL15 / PL60).

  python tools/filtro_picos_a5.py desc     # 80 pruebas (5 bases × 8 configuraciones × 2 contrastes), BH q 0,10 → DESC.json
  python tools/filtro_picos_a5.py rep      # nominadas con un paso de LORD++ → REP.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.research import a5 as A5, filtro_picos as F  # noqa: E402

DIR = ROOT / "docs/research/filtro_picos_20261118"
EJ, EJ_B = "P_obj_stop_fin", "P_obj_stop_b_fin"


def _ops():
    """OPS con trig/base/conf. Si la corrida no los conservó (a5_campana anterior al 2026-11-18), se toman de EVENTOS por posición:
    `correr` escribe OPS con las filas DESC/REP de EVENTOS en el mismo orden por instrumento. Se verifica fila por fila; si algo no
    coincide, no se analiza."""
    O = pd.read_csv(DIR / "OPS_DESC_REP.csv.gz")
    if {"trig", "base", "conf"} <= set(O.columns): return O
    E = pd.read_csv(DIR / "EVENTOS.csv.gz", usecols=["k", "ses", "lado", "inst", "bloque", "trig", "base", "conf"])
    E = E[E.bloque.isin(["DESC", "REP"])].reset_index(drop=True)
    if len(E) != len(O): raise SystemExit(f"EVENTOS ({len(E)}) y OPS ({len(O)}) no alinean: relanzar `correr` con `conservar`")
    for c in ("k", "ses", "lado", "inst", "bloque"):
        if not (E[c].to_numpy() == O[c].to_numpy()).all(): raise SystemExit(f"columna {c} no alinea: relanzar `correr` con `conservar`")
    return O.assign(trig=E.trig.to_numpy(), base=E.base.to_numpy(), conf=E.conf.to_numpy())


def _valores(O, bloque):
    from edgelab.research.embudo_runners import friccion
    O = O[O.bloque == bloque].copy(); fr = {i: float(friccion(i)[0]) for i in O.inst.unique()}
    for e in (EJ, EJ_B):
        ok = O[f"r_{e}"].notna() & (O[f"k_{e}"] > 0)
        O[f"v_{e}"] = np.where(ok, O[f"r_{e}"], 0.0)
        O[f"n_{e}"] = np.where(ok, O[f"r_{e}"] - O.inst.map(fr) / O[f"k_{e}"], 0.0)
        O[f"ok_{e}"] = ok
    return O


def _pares(O, base, conf, contra):
    """Por gatillo de la base: (sesión, valor de conf, valor de contra) con 0 donde no entró."""
    T = O[(O.base == base) & (O.conf == "INM")][["trig", "ses"]].drop_duplicates("trig")
    def col(cf, c):
        g = O[(O.base == base) & (O.conf == cf)].drop_duplicates("trig").set_index("trig")[c]
        return T.trig.map(g).fillna(0.0).to_numpy(float)
    return T.ses.to_numpy(np.int64), col, T


def evaluar(bloque):
    O = _valores(_ops(), bloque); res = {}
    for base in F.BASES:
        for cf in F.CONFIGS:
            conf = F.nombre_conf(cf); pl = f"PL{cf[1]}"
            for contra in ("INM", pl):
                ses, col, T = _pares(O, base, conf, contra)
                if not len(T): continue
                a, b = col(conf, f"v_{EJ}"), col(contra, f"v_{EJ}")
                an, bn = col(conf, f"n_{EJ}"), col(contra, f"n_{EJ}")
                d = a - b; m, se, p = A5.cluster(ses, d)
                llena = O[(O.base == base) & (O.conf == conf) & O[f"ok_{EJ}"]]
                res[f"{base}|{conf}-{contra}"] = dict(
                    gatillos=int(len(T)), dif_bruto=m, se=se, p=p, frac_anios_pos=A5.frac_anios_positivos(ses, d),
                    dif_neto=float((an - bn).mean()), tasa_entrada=float(len(llena) / len(T)),
                    R_bruto_si_entra=float(llena[f"r_{EJ}"].mean()) if len(llena) else None,
                    R_neto_si_entra=float(llena[f"n_{EJ}"].mean()) if len(llena) else None,
                    dif_bruto_stop_b=float((col(conf, f"v_{EJ_B}") - col(contra, f"v_{EJ_B}")).mean()),
                    base_R_bruto=float(b.mean()), base_R_neto=float(bn.mean()))
    return res


def desc():
    cal = json.loads((DIR / "CALIBRACION.json").read_text())["celdas"]
    def calibra(k):
        base, rest = k.split("|"); conf, contra = rest.split("-")
        return all(cal.get(f"{base}__{x}|{EJ}", {}).get("calibra", False) for x in (conf, contra))
    res = evaluar("DESC"); nom = A5.nominar(res, 0.10, calibra)
    (DIR / "DESC.json").write_text(json.dumps(dict(preregistro=str(DIR / "PREREGISTRO.md"), pruebas=len(res), resultados=res, nominadas=nom),
                                              indent=1, default=float))
    print(len(res), "pruebas;", json.dumps(nom))


def rep():
    from edgelab.funnel.libro_lord import LibroLord
    from a5_campana import _commiteado
    if not _commiteado(DIR / "DESC.json"): raise SystemExit("DESC.json sin commitear")
    nom = json.loads((DIR / "DESC.json").read_text())["nominadas"]; res = evaluar("REP"); res = {k: res[k] for k in nom}
    dec = LibroLord().probar("FILTRO_PICOS_A5", "REP_filtro_picos_20261118", [(k, res[k]["p"]) for k in nom]) if nom else None
    (DIR / "REP.json").write_text(json.dumps(dict(nominadas=nom, resultados=res, lord=dec), indent=1, default=float)); print(json.dumps(dec))


if __name__ == "__main__":
    {"desc": desc, "rep": rep}[sys.argv[1]]()
