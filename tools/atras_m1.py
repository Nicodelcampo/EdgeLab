#!/usr/bin/env python3
"""«Atrás» de reglas YA CONGELADAS (v2 y v4) sobre M1 real de futuros de NT8 (pre-registro docs/research/atras_m1_20261117/PREREGISTRO.md).

Dos fases, en orden: (1) CALIBRACION: la regla sobre M1 de NT8 en su propio desarrollo (ago-25 → sep-26) contra sus operaciones en
ticks; (2) ATRAS: sólo las que calibran, sobre los años que su linaje no miró. Etapa ANALIZAR_REGLA del embudo (mismo módulo, celda,
cortes y tope), lector `M1NT8:` (corta en la frontera del holdout).

  python tools/atras_m1.py lanzar calibracion|atras
  python tools/atras_m1.py traer
  python tools/atras_m1.py calibracion          # -> CALIBRACION.json (commitear ANTES de lanzar el atrás)
  python tools/atras_m1.py atras                # -> ATRAS.json
"""
import json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/atras_m1_20261117"; RES = DIR / "resultados"; HF = DIR / "handles.json"
CALIB = (20250805, 20260930)
# regla, campaña del embudo, instrumento, ventana primaria del atrás (años que su linaje no miró; el Nasdaq 2023-01 → 2025-07 lo miró
# AREAS_EXP_1_CRUZADO sobre USATECH), inicio del tramo descriptivo
REGLAS = {
    "CVGAP2-GC#11": ("CVGAP2-GC", "GC", (20180102, 20250731), 20080114),
    "COMEX-CIERRE-GC-R#0": ("COMEX-CIERRE-GC-R", "GC", (20180102, 20250731), 20080114),
    "IF-LUX-NQ-R2#1": ("IF-LUX-NQ-R2", "NQ", (20180102, 20221230), 20060106),
    "CVGAP-ES-C": ("CVGAP-ES-C", "ES", (20180102, 20250731), 20060106),
    "PREAPERTURA-NQ": ("PREAPERTURA-NQ", "NQ", (20180102, 20221230), 20060106),
}
MIN_CORR, MIN_SES_COMUNES = 0.5, 30


def _regla(nombre):
    """(spec, celda, cortes, tope) congelados: v4 de la cosecha (estado.json + BATERIA), v2 de su acta (cartera_nov.universo)."""
    cid = REGLAS[nombre][0]
    if "#" in nombre:
        import cosecha_pozo as CP
        u = next(x for x in CP.universo() if x["cid"] == cid); i = int(nombre.split("#")[1])
        return u["spec"], CP._equity().celdas(u["st"])[i], u["st"]["cortes"], None
    from cartera_nov import universo
    r = next(x for x in universo() if x["cid"] == cid)
    return r["spec"], r["celda"], r["cortes"], r["tope"]


def ops_ticks(nombre):
    """Operaciones de desarrollo en ticks (R por operación y sesión) de la regla, para la calibración."""
    if "#" in nombre:
        import cosecha_pozo as CP
        cid, i = nombre.split("#"); u = next(x for x in CP.universo() if x["cid"] == cid)
        b = [x for x in CP.metricas(u, json.loads((CP.DEV / f"{cid}.json").read_text())) if x["indice"] == int(i)][0]
        return {int(k): v for k, v in b["_dev_diario"].items()}
    from cartera_nov_analisis import _ops, _sesion
    d = {}
    for t in ("desc", "rep"):
        o = _ops(nombre, t); u, x = _sesion(o["ses"], o["R"]); d.update({int(a): float(b) for a, b in zip(u, x)})
    return d


def ops_m1(nombre, fase):
    """{sesión: R} de la corrida M1 de la regla (neto en R si la campaña mide en R; si no, neto / riesgo)."""
    sp = _regla(nombre)[0]; o = json.loads((RES / f"{nombre.replace('#', '_')}__{fase}.json").read_text()).get("operaciones") or {}
    d, n = {}, []
    for s, x, rg in zip(o.get("ses", []), o.get("neto", []), o.get("riesgo", [])):
        if rg is None or not rg > 0: continue
        r = float(x) if sp.get("estadistico") == "R" else float(x) / float(rg); d[int(s)] = d.get(int(s), 0.0) + r; n.append((int(s), r))
    return d, n


def lanzar(fase):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); hs = json.loads(HF.read_text()) if HF.exists() else {}; DIR.mkdir(parents=True, exist_ok=True)
    nombres = list(REGLAS)
    if fase == "atras":
        cal = json.loads((DIR / "CALIBRACION.json").read_text())
        from cartera_nov_analisis import _commiteado
        if not _commiteado(DIR / "CALIBRACION.json"): raise SystemExit("CALIBRACION.json sin commitear: el atrás se lanza sólo después")
        nombres = [n for n in nombres if cal["reglas"][n]["calibra"]]
    for k, nombre in enumerate(nombres):
        clave = f"{nombre}__{fase}"
        if clave in hs: continue
        cid, inst, prim, d0 = REGLAS[nombre]; sp, celda, cortes, tope = _regla(nombre)
        sp = dict(sp, sensor=f"M1NT8:{inst}", ejecucion=f"M1NT8:{inst}", datasets_extra=[], cuenta_kaggle="nicolasbuttaro",                # dueña del dataset M1 (privado): las otras cuentas no lo ven
                  cid=f"M1{'C' if fase == 'calibracion' else 'A'}-{nombre.replace('#', '-')}"[:30])
        per = list(CALIB) if fase == "calibracion" else [d0, prim[1]]
        h = run.lanzar(sp, "ANALIZAR_REGLA", dict(cortes=cortes, celdas=[celda], tope=tope, operaciones=True), per)
        hs[clave] = dict(handle=h, periodo=per, ts=time.time()); HF.write_text(json.dumps(hs, indent=1)); print("lanzada", clave, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads(HF.read_text()); RES.mkdir(parents=True, exist_ok=True); falta = []
    for clave, h in hs.items():
        f = RES / f"{clave.replace('#', '_')}.json"
        if f.exists(): continue
        e = run.estado(h["handle"])
        if e != "complete": falta.append((clave, e)); continue
        f.write_text(json.dumps(run.traer(h["handle"]), indent=1, default=float)); print("traída", clave)
    print("faltan", falta); return falta


def calibrar(t: dict, m: dict) -> dict:
    """Criterio de papel_m1_20261115/VALIDACION.md: mismo signo de la media por sesión, diferencia dentro de ~1 error estándar combinado y
    correlación por sesión > 0,5 en las sesiones comunes (>= 30)."""
    ses = sorted(set(t) | set(m)); x = np.array([t.get(s, 0.0) for s in ses]); y = np.array([m.get(s, 0.0) for s in ses])
    com = sorted(set(t) & set(m))
    ee = float(np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))) if len(ses) > 2 else float("nan")
    corr = float(np.corrcoef([t[s] for s in com], [m[s] for s in com])[0, 1]) if len(com) > 2 else float("nan")
    out = dict(sesiones=len(ses), comunes=len(com), ticks_media=float(x.mean()), m1_media=float(y.mean()), ee=ee, corr=corr,
               ops_ticks_ses=len(t), ops_m1_ses=len(m))
    out["calibra"] = bool(len(com) >= MIN_SES_COMUNES and np.sign(x.mean()) == np.sign(y.mean()) and abs(x.mean() - y.mean()) <= ee
                          and corr > MIN_CORR)
    return out


def calibracion():
    out = dict(preregistro="docs/research/atras_m1_20261117/PREREGISTRO.md", periodo=list(CALIB), reglas={})
    for n in REGLAS:
        t = {s: v for s, v in ops_ticks(n).items() if CALIB[0] <= s <= CALIB[1]}; m, _ = ops_m1(n, "calibracion")
        out["reglas"][n] = calibrar(t, m); print(n, out["reglas"][n], flush=True)
    (DIR / "CALIBRACION.json").write_text(json.dumps(out, indent=1, default=float))


def atras():
    """PREREGISTRO §4: por regla y canasta (suma de R por sesión), en la ventana primaria; descriptivo en el tramo viejo."""
    from edgelab.funnel.secuencial import EProceso
    from cartera_nov_analisis import _boot_ic
    cal = json.loads((DIR / "CALIBRACION.json").read_text()); out = dict(preregistro="docs/research/atras_m1_20261117/PREREGISTRO.md", reglas={})
    can = {}
    for n in [x for x in REGLAS if cal["reglas"][x]["calibra"]]:
        _, ops = ops_m1(n, "atras"); prim = REGLAS[n][2]
        for tramo, (a, b) in (("primario", prim), ("descriptivo", (REGLAS[n][3], prim[0] - 1))):
            o = [(s, r) for s, r in ops if a <= s <= b]; R = np.array([r for _, r in o]); S = np.array([s for s, _ in o])
            E = EProceso(mu0=0.0, piso=-6.0, techo=30.0); viol = False
            for r in R:
                if not -6.0 <= r <= 30.0: viol = True; break
                E.agregar(float(r))
            anios = {int(y): float(R[S // 10000 == y].sum()) for y in np.unique(S // 10000)} if len(S) else {}
            out["reglas"].setdefault(n, {})[tramo] = dict(ventana=[a, b], ops=len(R), R_op=float(R.mean()) if len(R) else None,
                R_total=float(R.sum()), ic90=_boot_ic(S, R) if len(R) > 2 else None, e=float(E.e_valor), limite_violado=viol,
                anios=anios, frac_anios_pos=float(np.mean([v > 0 for v in anios.values()])) if anios else None,
                ops_mes=float(len(R) / max(1, (b // 10000 - a // 10000) * 12 + (b // 100 % 100 - a // 100 % 100) + 1)))
            if tramo == "primario":
                for s, r in o: can[s] = can.get(s, 0.0) + r
    x = np.array([can[s] for s in sorted(can)]); S = np.array(sorted(can))
    if len(x) > 2:
        rng = np.random.default_rng(20261117); B = rng.integers(0, len(x), (20000, len(x))); m = x[B].mean(1)
        p = float(((m - m.mean() + 0.0) >= x.mean()).mean())                                  # bootstrap centrado en 0, unilateral
        anios = {int(y): float(x[S // 10000 == y].sum()) for y in np.unique(S // 10000)}
        out["canasta"] = dict(sesiones=len(x), R_total=float(x.sum()), R_sesion=float(x.mean()), p=p, anios=anios,
                              frac_anios_pos=float(np.mean([v > 0 for v in anios.values()])))
    (DIR / "ATRAS.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out.get("canasta"), indent=1))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "lanzar": lanzar(sys.argv[2])
    elif c == "traer": traer()
    elif c == "calibracion": calibracion()
    elif c == "atras": atras()
