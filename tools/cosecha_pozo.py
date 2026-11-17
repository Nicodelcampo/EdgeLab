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


PREREG = "docs/research/cosecha_pozo_20261117/PREREGISTRO.md"; SELLADO = "nicolasbuttaro/edgelab-holdout-sellado"; HOLD = DIR / "hold"
HEREDA_AREAS = ("INTENTO_FALLIDO_LUX_NQ", "INTENTO_FALLIDO_LUX_CFD_NQ", "U1_ZONAS_GRILLA_YM", "INTENTO_FALLIDO_RACIMOS_NQ", "IF_HACIA_RACIMOS_NQ")
CONSUMIDA_AREAS = 20261022          # AREAS_EXP_1_CRUZADO consumió el holdout hasta acá (HOLDOUT_VENTANAS.jsonl): sensibilidad por linaje


def _elegidas() -> dict:
    """{cid: [índices de celda]} de SELECCION.json; exige que esté commiteada y sin cambios (PREREGISTRO §3)."""
    from cartera_nov_analisis import _commiteado
    if not _commiteado(DIR / "SELECCION.json"): raise SystemExit("SELECCION.json no está commiteada (o tiene cambios): §3 lo exige antes del holdout")
    out = {}
    for r in json.loads((DIR / "SELECCION.json").read_text())["seleccion"]:
        c, i = r.split("#"); out.setdefault(c, []).append(int(i))
    return out


def aperturas():
    """Una apertura por familia de las reglas elegidas, con el plan e-proceso de PLAN_POTENCIA.json (K27). Idempotente."""
    from edgelab.research import holdout_ventanas as HV
    from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT
    U = {u["cid"]: u for u in universo()}; plan = json.loads((DIR / "PLAN_POTENCIA.json").read_text())["plan_por_operacion"]
    for fam in sorted({U[c]["familia"] for c in _elegidas()}):
        if (mal := HV.problemas(fam, HOLDOUT_PRIMERA_SESION_INT, f"COSECHA-{fam}")): raise SystemExit("; ".join(mal))
        print("apertura", fam, HV.registrar_apertura(fam, f"COSECHA-{fam}", HOLDOUT_PRIMERA_SESION_INT, 0, plan=plan) or "ya estaba")


def lanzar_hold(commit: str, hasta: int):
    from edgelab.research.embudo_runners import KaggleRunner
    from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT
    run = KaggleRunner(dataset_sellado=SELLADO, raiz=None); U = {u["cid"]: u for u in universo()}; EQ = _equity()
    HOLD.mkdir(parents=True, exist_ok=True); hf = HOLD / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for cid, idx in _elegidas().items():
        if cid in hs: continue
        u = U[cid]; cs = EQ.celdas(u["st"]); sp = dict(u["spec"], cid=f"CPH-{cid}"[:30], cuenta_kaggle="nicolasbuttaro")
        params = dict(cortes=u["st"]["cortes"], celdas=[cs[i] for i in idx], operaciones=True,
                      acta=dict(tipo="holdout_cosecha_20261117", acta=PREREG, commit=commit, cid=cid, familia=u["familia"]))
        h = run.lanzar(sp, "ANALIZAR_REGLA", params, [HOLDOUT_PRIMERA_SESION_INT, int(hasta)])
        hs[cid] = dict(handle=h, indices=idx, periodo=[HOLDOUT_PRIMERA_SESION_INT, int(hasta)], ts=__import__("time").time())
        hf.write_text(json.dumps(hs, indent=1)); print("lanzada", cid, h, flush=True)


def traer_hold():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado=SELLADO, raiz=None); hs = json.loads((HOLD / "handles.json").read_text()); falta = []
    for cid, h in hs.items():
        f = HOLD / f"{cid}.json"
        if f.exists(): continue
        e = run.estado(h["handle"])
        if e != "complete": falta.append((cid, e)); continue
        f.write_text(json.dumps(run.traer(h["handle"]), indent=1, default=float)); print("traída", cid)
    print("faltan", falta); return falta


def holdout():
    """PREREGISTRO §4: e-proceso de la canasta (R por sesión = suma de las reglas, cotas [−15, 40]) y por regla ([−6, 30]); descriptivo
    del holdout sellado y sensibilidad sin las sesiones <= 2026-10-22 para las familias que heredan de AREAS_EXP_1_CRUZADO."""
    from edgelab.funnel.secuencial import EProceso
    from edgelab.holdout import sesion_excluida
    U = {u["cid"]: u for u in universo()}; hs = json.loads((HOLD / "handles.json").read_text()); filas = []
    for cid, h in hs.items():
        u = U[cid]; sp = u["spec"]; o = json.loads((HOLD / f"{cid}.json").read_text()).get("operaciones") or {}
        insts = {x[3:] if x.startswith("DK:") else x for x in (sp["sensor"], sp.get("ejecucion") or sp["sensor"])}
        for c, s, n, rg in zip(o.get("celda", []), o.get("ses", []), o.get("neto", []), o.get("riesgo", [])):
            if rg is None or not rg > 0 or any(sesion_excluida(i, int(s)) for i in insts): continue
            filas.append((f"{cid}#{h['indices'][int(c)]}", u["familia"], int(s), float(n) if sp.get("estadistico") == "R" else float(n) / float(rg)))
    def canasta(fs):
        por = {}
        for _, _, s, r in fs: por[s] = por.get(s, 0.0) + r
        x = np.array([por[s] for s in sorted(por)]); E = EProceso(mu0=0.0, piso=-15.0, techo=40.0); viol = False
        for v in x:
            if not -15.0 <= v <= 40.0: viol = True; break
            E.agregar(float(v))
        return dict(sesiones=len(x), ops=len(fs), R_total=float(x.sum()), R_sesion=float(x.mean()) if len(x) else None,
                    t=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else None,
                    e=float(E.e_valor), limite_violado=viol, EDGE=bool(E.e_valor >= 10 and not viol))
    por_regla = {}
    for reg in sorted({f[0] for f in filas} | {f"{c}#{i}" for c, h in hs.items() for i in h["indices"]}):
        x = [r for g, _, s, r in sorted(filas, key=lambda z: z[2]) if g == reg]; E = EProceso(mu0=0.0, piso=-6.0, techo=30.0); viol = False
        for v in x:
            if not -6.0 <= v <= 30.0: viol = True; break
            E.agregar(float(v))
        por_regla[reg] = dict(ops=len(x), R_total=float(sum(x)), R_op=float(np.mean(x)) if x else None, e=float(E.e_valor), limite_violado=viol)
    sens = [f for f in filas if not (f[1] in HEREDA_AREAS and f[2] <= CONSUMIDA_AREAS)]
    out = dict(preregistro=PREREG, periodo=next(iter(hs.values()))["periodo"], canasta=canasta(filas), por_regla=por_regla,
               sensibilidad_linaje_areas=canasta(sens), lectura="EDGE si e >= 10; si no SIN_DECIDIR (sigue en forward); futilidad a 60 sesiones con R <= 0")
    (DIR / "HOLDOUT.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps({k: out[k] for k in ("canasta", "sensibilidad_linaje_areas")}, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "universo"
    if cmd == "aperturas": aperturas()
    elif cmd == "lanzar_hold": lanzar_hold(sys.argv[2], int(sys.argv[3]))
    elif cmd == "traer_hold": traer_hold()
    elif cmd == "holdout": holdout()
    elif cmd == "universo":
        U = universo(); EQ = _equity()
        for u in U: print(u["cid"], u["familia"], u["spec"]["sensor"], u["spec"].get("ejecucion"), len(EQ.celdas(u["st"])))
        print(len(U), "campañas", sum(len(EQ.celdas(u["st"])) for u in U), "pistas", len({u["familia"] for u in U}), "familias")
    elif cmd == "lanzar": DEV.mkdir(parents=True, exist_ok=True); _equity().lanzar([u["cid"] for u in universo()])
    elif cmd == "traer": _equity().traer()
    elif cmd == "seleccion": seleccion()
