#!/usr/bin/env python3
"""LUXIMB-A5 (pre-registro docs/research/luximb_a5_20261118/PREREGISTRO.md): impulsos de LUX-IMB con zonas en el 25 % inicial, primera
campaña con la partición HOLDOUT-A5 sobre M1 real de futuros de NT8 (NQ 2006-01 → 2022-12).

Reusa, sin copiar: la tabla de eventos y desenlaces de `edgelab/research/luximb_hvn.py` (detector, zonas OG/VI y fade a mercado con stop
al tick que lo cruza), el lector `fuentes_ticks.bloques_m1nt8` (corta en la frontera), `holdout.a5_bloque`, `atras_m1.calibrar`,
`embudo_runners.friccion`, `escalera` (BH) y `libro_lord`. Restringe la tabla a lo pre-registrado (detector D3_20, 3 ejecuciones, sin EXT)
fijando los atributos del módulo antes de llamarlo.

  python tools/luximb_a5.py calibrar <carpeta M1 NT8>   # fase 0: M1 contra ticks en el desarrollo ya mirado -> CALIBRACION.json
  python tools/luximb_a5.py correr <carpeta M1 NT8>     # eventos de toda la ventana; desenlaces SÓLO en meses DESC y REP
  python tools/luximb_a5.py desc                        # 21 pruebas en DESC, BH q 0,10 -> DESC.json
  python tools/luximb_a5.py rep                         # nominadas en REP con un paso de LORD++ -> REP.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.research import a5 as A5  # noqa: E402  (capa común de la partición A5, extraída de esta herramienta)
DIR = ROOT / "docs/research/luximb_a5_20261118"
FAMILIA = "LUXIMB_A5_ZONAS25"
VENTANA = (20060106, 20221230)                       # 2023-01 → 2026-09 lo usó el linaje (H-ZONAS en USATECH, desarrollo en ticks)
LIMPIOS = (20060106, 20111230)                       # ninguna familia LUX-IMB miró impulsos en estos años (sensibilidad)
CALIB = ((20250805, 20260331), (20260401, 20260925))  # tablas de ticks de LUXIMB-HVN (desarrollo ya mirado)
EJ = [(0.5, 1.0, 0.0, 0.0), (0.35, 1.0, 0.0, 0.0), (0.2, 1.0, 0.0, 0.0)]
ZONAS = (0, 1, 2, 3)                                 # LG.ZON: 0 control, 1 ≥ 1, 2 ≥ 3 (visor), 3 ≥ 5 zonas en el 25 % inicial
AMP_A5 = ((60.0, 0.0),)                              # K36: percentil causal sin el piso de 60 pts (en 2010 deja 3 marcas por año)
FRIC_R_MAX = 0.08                                    # subconjunto operable declarado (fricción / riesgo inicial)
MIN_FRAC_ANIOS = 0.6


def _hvn():
    from edgelab.research import luximb_hvn as H
    H.DETECTORES = {"D3_20": (3.0, 20)}; H.E0 = list(EJ); H.EXT = []
    return H


def _ctx(datos, d0, d1):
    from edgelab.research.fuentes_ticks import bloques_m1nt8
    from edgelab.research.grilla_generica import contexto_m1
    ctx = contexto_m1(bloques_m1nt8("NQ", int(d0), int(d1), str(datos)), 0.25)
    ctx["m1_sintetico"] = True                                        # enmienda 1: stop dentro de la vela en su nivel, no en el extremo
    return ctx


def _ej(x):
    from edgelab.research.luximb_hvn import nombre_e0
    return nombre_e0(x)


def _por_sesion(T, defn, ej, neto=False, fr=0.0):
    g = T[T[defn].astype(bool) & T[f"r_{ej}"].notna()]
    r = g[f"r_{ej}"] - (fr / g[f"k_{ej}"] if neto else 0.0)
    return {int(s): float(v) for s, v in r.groupby(g.ses.astype(int)).sum().items()}


def calibrar(datos):
    """Fase 0 (K30): misma definición que las tablas de ticks (AMP de LUXIMB-HVN, con piso), M1 de NT8 en el mismo tramo."""
    from atras_m1 import calibrar as crit
    H = _hvn(); out = dict(preregistro="docs/research/luximb_a5_20261118/PREREGISTRO.md", celdas={})
    for d0, d1 in CALIB:
        ctx = _ctx(datos, d0, d1); M = H.desenlaces(H.eventos(ctx), ctx)
        T = pd.read_csv(ROOT / f"docs/research/luximb_hvn_20261111/tablas/LXH_NQ_{d0}_{d1}.csv.gz")
        for z in ZONAS:
            for x in EJ:
                c = f"D3_20_a0_z{z}|{_ej(x)}"; acc = out["celdas"].setdefault(c, dict(t={}, m={}))
                acc["t"].update(_por_sesion(T, f"D3_20_a0_z{z}", _ej(x))); acc["m"].update(_por_sesion(M, f"D3_20_a0_z{z}", _ej(x)))
        print("calibración", d0, d1, len(M), "eventos M1", flush=True)
    for c, acc in out["celdas"].items():
        out["celdas"][c] = crit(acc["t"], acc["m"]); print(c, out["celdas"][c], flush=True)
    out["calibran"] = sum(v["calibra"] for v in out["celdas"].values())
    (DIR / "CALIBRACION.json").write_text(json.dumps(out, indent=1, default=float))


def _bloques(ses):
    return A5.bloques(ses)


def correr(datos):
    """Eventos (sin retornos) de toda la ventana; desenlaces sólo en DESC y REP. HOLDOUT y EMBARGO quedan sin desenlace."""
    from cartera_nov_analisis import _commiteado
    if not _commiteado(DIR / "CALIBRACION.json"): raise SystemExit("CALIBRACION.json sin commitear: la corrida va después")
    cal = json.loads((DIR / "CALIBRACION.json").read_text())
    H = _hvn(); ctx = _ctx(datos, *VENTANA); E = H.eventos(ctx, amp=AMP_A5)
    E["bloque"] = _bloques(E.ses.to_numpy())
    cols = ["k", "d", "i0", "ses", "rg", "velas", "nz", "nini25", "bloque"] + [f"D3_20_a0_z{z}" for z in ZONAS]
    E[cols].to_csv(DIR / "EVENTOS.csv.gz", index=False)
    vis = E[E.bloque.isin(["DESC", "REP"])].reset_index(drop=True)
    T = H.desenlaces(vis, ctx)
    keep = cols + [f"{p}_{_ej(x)}" for x in EJ for p in ("r", "k")]
    T[keep].to_csv(DIR / "OPS_DESC_REP.csv.gz", index=False)
    cnt = {b: {f"z{z}": int(E.loc[E.bloque == b, f"D3_20_a0_z{z}"].sum()) for z in ZONAS} for b in ("DESC", "REP", "HOLDOUT", "EMBARGO")}
    (DIR / "CORRIDA.json").write_text(json.dumps(dict(ventana=VENTANA, velas=int(len(ctx["c"])), eventos=int(len(E)), marcas_por_bloque=cnt,
                                                      calibracion_ok=cal["calibran"]), indent=1))
    print(json.dumps(cnt), flush=True)


_cluster, _dif = (lambda ses, r: A5.cluster(ses, r)), (lambda *a: A5.diferencia(*a))


def _celdas(T, bloque, fr):
    T = T[T.bloque == bloque]; out = {}
    for x in EJ:
        e = _ej(x); base = None
        for z in ZONAS:
            g = T[T[f"D3_20_a0_z{z}"].astype(bool) & T[f"r_{e}"].notna()]
            r = g[f"r_{e}"].to_numpy(float); fric = fr / g[f"k_{e}"].to_numpy(float); ses = g.ses.to_numpy(int)
            m, se, p = _cluster(ses, r); anio = pd.Series(r).groupby(ses // 10000).sum()
            op = fric <= FRIC_R_MAX
            out[f"z{z}|{e}"] = dict(n=int(len(r)), R_bruto=m, se=se, p=p, frac_anios_pos=float((anio > 0).mean()), R_neto=float((r - fric).mean()),
                                   fric_R_media=float(fric.mean()), n_operable=int(op.sum()),
                                   R_neto_operable=float((r - fric)[op].mean()) if op.any() else None,
                                   R_bruto_limpios=float(r[(ses >= LIMPIOS[0]) & (ses <= LIMPIOS[1])].mean()) if ((ses <= LIMPIOS[1]).any()) else None)
            if z == 0: base = (ses, r)
            else:
                d, sd, pd_ = _dif(ses, r, *base); out[f"z{z}-z0|{e}"] = dict(dif_bruto=d, se=sd, p=pd_)
    return out


def desc():
    bh = A5.bh
    from edgelab.research.embudo_runners import friccion
    T = pd.read_csv(DIR / "OPS_DESC_REP.csv.gz"); res = _celdas(T, "DESC", friccion("NQ")[0])
    cal = json.loads((DIR / "CALIBRACION.json").read_text())["celdas"]
    def calibra(k):                                   # un contraste necesita que calibren sus dos celdas (PREREGISTRO §5.0)
        z, e = k.split("|"); return all(cal[f"D3_20_a0_{x}|{e}"]["calibra"] for x in z.split("-"))
    nombres = list(res); ps = [res[k]["p"] for k in nombres]; rech = bh(ps, 0.10)
    for k, rj in zip(nombres, rech):
        v = res[k]; v["bh"] = bool(rj)
        v["calibra"] = calibra(k)
        v["nominada"] = bool(rj and v["calibra"] and (v.get("R_bruto", v.get("dif_bruto")) > 0) and v.get("frac_anios_pos", 1.0) >= MIN_FRAC_ANIOS)
    out = dict(preregistro="docs/research/luximb_a5_20261118/PREREGISTRO.md", pruebas=len(nombres), resultados=res,
               nominadas=[k for k in nombres if res[k]["nominada"]])
    (DIR / "DESC.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out["nominadas"]))


def rep():
    from edgelab.funnel.libro_lord import LibroLord
    from edgelab.research.embudo_runners import friccion
    from cartera_nov_analisis import _commiteado
    if not _commiteado(DIR / "DESC.json"): raise SystemExit("DESC.json sin commitear: la réplica va después")
    nom = json.loads((DIR / "DESC.json").read_text())["nominadas"]
    T = pd.read_csv(DIR / "OPS_DESC_REP.csv.gz"); res = _celdas(T, "REP", friccion("NQ")[0]); res = {k: res[k] for k in nom}
    dec = LibroLord().probar(FAMILIA, "REP_20261118", [(k, res[k]["p"]) for k in nom]) if nom else None
    (DIR / "REP.json").write_text(json.dumps(dict(nominadas=nom, resultados=res, lord=dec), indent=1, default=float)); print(json.dumps(dec))


if __name__ == "__main__":
    c = sys.argv[1]
    {"calibrar": lambda: calibrar(sys.argv[2]), "correr": lambda: correr(sys.argv[2]), "desc": desc, "rep": rep}[c]()
