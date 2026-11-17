#!/usr/bin/env python3
"""Cosecha del pozo de pistas vivas (pre-registro docs/research/cosecha_pozo_20261117/PREREGISTRO.md, 2026-11-17).

Universo: las pistas de réplica de las campañas PISTAS_VIVAS de 20 familias con holdout libre que ejecutan en un futuro
(INVESTIGACION_ORIGEN_CARTERA_V2_20261117.md §5). Operaciones de DESARROLLO (inicio del DESC → 2026-09-30, nunca el holdout) con
`tools/equity_pistas.py` (etapa ANALIZAR_REGLA, mismo motor que eligió las celdas); selección con la regla de la cartera
(`tools/cartera_nov_analisis.py`: contracción James-Stein, ≤ 2 por familia, correlación ≤ 0,5, hasta 10) sin E5 (octubre: el holdout
de estas familias no se miró).

  python tools/cosecha_pozo.py universo
  python tools/cosecha_pozo.py lanzar         # una corrida por campaña (equity_pistas.lanzar)
  python tools/cosecha_pozo.py traer
  python tools/cosecha_pozo.py seleccion      # -> BATERIA.json, SELECCION.json (commitear ANTES de cualquier dato del holdout)
"""
import glob, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/cosecha_pozo_20261117"; DEV = DIR / "dev"
FAMILIAS = ("COMEX_CIERRE_ORO_GC", "CONFLUENCIA_CVGAP_RACIMOS_CFD_ES", "CONFLUENCIA_CVGAP_RACIMOS_NQ", "CVGAP2_CFD_ES", "CVGAP2_GC",
            "CVGAP2_NQ", "HFT_GC_P10", "IF_HACIA_RACIMOS_NQ", "INTENTO_FALLIDO_LUX_CFD_NQ", "INTENTO_FALLIDO_LUX_NQ",
            "INTENTO_FALLIDO_RACIMOS_NQ", "KALMAN_FADE_NQ", "MODELO_ASIA_NQ", "ORO_ALMUERZO_RUPTURA_CFD", "ORO_ALMUERZO_RUPTURA_GC",
            "OVERNIGHT_INVENTARIO_NQ", "TAU_TENDENCIA_NQ", "TORI_TREND_TOQUE3_CFD_NQ", "TORI_TREND_TOQUE3_GC", "U1_ZONAS_GRILLA_YM")
FUTUROS = {"NQ", "ES", "YM", "GC"}
MIN_OPS, MAX_FRIC, MIN_MESES_POS, MAX_REGLAS = 40, 0.08, 0.55, 10


def universo() -> list:
    out = []
    for f in sorted(glob.glob(str(ROOT / "docs/research/*/embudo/*/estado.json"))):
        st = json.loads(Path(f).read_text(encoding="utf-8")); sp = st["spec"]
        if sp.get("familia") in FAMILIAS and st.get("fase") == "PISTAS_VIVAS" and (sp.get("ejecucion") or sp["sensor"]) in FUTUROS:
            out.append(dict(cid=sp["cid"], familia=sp["familia"], spec=sp, st=st))
    return out


def _equity():
    import equity_pistas as EQ
    EQ.SALIDA = DEV; return EQ


def metricas(u: dict, ops: dict) -> list:
    """Una fila por pista: DESC y REP (ventana de réplica de la campaña), fricción en R, sin las 5 mejores, meses positivos."""
    from cartera_nov_analisis import _sesion, _boot_ic, _t_ses
    from edgelab.research.embudo_runners import friccion
    EQ = _equity(); sp, st = u["spec"], u["st"]; cs = EQ.celdas(st); o = ops.get("operaciones") or {}
    if not o: return []
    cel = np.asarray(o["celda"], int); ses = np.asarray(o["ses"], int); neto = np.asarray(o["neto"], float)
    rg = np.array([np.nan if x is None else x for x in o["riesgo"]], float)
    d0, d1 = int(sp["desc"][0]), int(sp["desc"][1]); r0, r1 = [int(x) for x in st["pistas_replica"]["ventana"]]
    fr_pts = friccion(sp.get("ejecucion") or sp["sensor"])[0]; filas = []
    for i, c in enumerate(cs):
        m = (cel == i) & np.isfinite(neto) & np.isfinite(rg) & (rg > 0) & (((ses >= d0) & (ses <= d1)) | ((ses >= r0) & (ses <= r1)))
        R = neto[m] if sp.get("estadistico") == "R" else neto[m] / rg[m]; s = ses[m]; riesgo = rg[m]
        de, rp = s <= d1, s >= r0
        def tr(k): return dict(n=int(k.sum()), R_op=float(R[k].mean()) if k.any() else None, t_ses=_t_ses(s[k], R[k]), ic90=_boot_ic(s[k], R[k]))
        mes = s // 100; meses = {mm: R[mes == mm].sum() for mm in np.unique(mes)}; srt = np.sort(R)
        n_meses = (int(str(s.max())[:4]) * 12 + int(str(s.max())[4:6]) - int(str(s.min())[:4]) * 12 - int(str(s.min())[4:6]) + 1) if len(s) else 1
        u_, x_ = _sesion(s, R)
        filas.append(dict(regla=f"{u['cid']}#{i}", cid=u["cid"], indice=i, celda=list(c), familia=u["familia"], sensor=sp["sensor"],
                          ejecucion=sp.get("ejecucion") or sp["sensor"], futuro=True, estadistico_campana=sp.get("estadistico") or "puntos",
                          desc=tr(de), rep=tr(rp), dev=tr(np.ones(len(R), bool)),
                          friccion_R=float(np.nanmean(fr_pts / riesgo)) if len(riesgo) else None,
                          sin_top5=float(srt[:-5].sum()) if len(srt) > 5 else None,
                          meses_pos=float(np.mean([v > 0 for v in meses.values()])) if meses else 0.0,
                          ops_mes=float(len(R) / max(n_meses, 1)), _dev_diario=dict(zip(u_.tolist(), x_.tolist()))))
    return filas


def elegibles(B):
    for b in B:
        e = dict(E1=b["dev"]["n"] >= MIN_OPS and (b["desc"]["R_op"] or 0) > 0 and (b["rep"]["R_op"] or 0) > 0,
                 E2=b["friccion_R"] is not None and b["friccion_R"] <= MAX_FRIC, E3=(b["sin_top5"] or 0) > 0,
                 E4=b["meses_pos"] >= MIN_MESES_POS, E6=b["futuro"])
        b["criterios"] = e; b["elegible"] = all(e.values())
    return B


def armar(B):
    from cartera_nov_analisis import _corr
    cand = sorted([b for b in B if b["elegible"]], key=lambda b: -b["R_contraido"]); sel = []
    for b in cand:
        if len(sel) >= MAX_REGLAS: break
        if sum(s["familia"] == b["familia"] for s in sel) >= 2: b["descarte"] = "ya hay 2 de su familia"; continue
        c = max([_corr(b["_dev_diario"], s["_dev_diario"]) for s in sel], default=0.0)
        if c > 0.5: b["descarte"] = f"correlación {c:.2f} con una elegida"; continue
        sel.append(b)
    return [s["regla"] for s in sel]


def seleccion():
    from cartera_nov_analisis import contraer
    B, falta = [], []
    for u in universo():
        f = DEV / f"{u['cid']}.json"
        if not f.exists(): falta.append(u["cid"]); continue
        B += [b for b in metricas(u, json.loads(f.read_text())) if b["dev"]["n"] >= 2]
    if falta: raise SystemExit(f"faltan operaciones de desarrollo de {falta}: la selección se hace con el universo completo")
    tau2 = contraer(B); elegibles(B); sel = armar(B)
    S = dict(regla="PREREGISTRO.md §3", n_pistas=len(B), n_elegibles=sum(b["elegible"] for b in B), tau2=tau2, seleccion=sel,
             por_criterio={k: int(sum(b["criterios"][k] for b in B)) for k in ("E1", "E2", "E3", "E4", "E6")})
    (DIR / "BATERIA.json").write_text(json.dumps(dict(reglas=[{k: v for k, v in b.items() if not k.startswith("_")} for b in B], tau2=tau2),
                                                 indent=1, default=float))
    (DIR / "SELECCION.json").write_text(json.dumps(S, indent=1)); print(json.dumps(S, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "universo"
    if cmd == "universo":
        U = universo(); EQ = _equity()
        for u in U: print(u["cid"], u["familia"], u["spec"]["sensor"], u["spec"].get("ejecucion"), len(EQ.celdas(u["st"])))
        print(len(U), "campañas", sum(len(EQ.celdas(u["st"])) for u in U), "pistas", len({u["familia"] for u in U}), "familias")
    elif cmd == "lanzar": DEV.mkdir(parents=True, exist_ok=True); _equity().lanzar([u["cid"] for u in universo()])
    elif cmd == "traer": _equity().traer()
    elif cmd == "seleccion": seleccion()
