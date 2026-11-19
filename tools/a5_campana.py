#!/usr/bin/env python3
"""Campaña con la partición HOLDOUT-A5 sobre M1 real de futuros (NT8) para un módulo con el contrato de `edgelab/research/tablas.py`.

Generaliza `tools/luximb_a5.py` (primer uso). La campaña se declara en `<carpeta>/CAMPANA.json`:
  {"modulo": "edgelab.research.escalonadas_m1", "familia": "...", "preregistro": "<carpeta>/PREREGISTRO.md",
   "instrumentos": ["NQ", "ES", "YM"], "ventana": [20060106, 20250731], "calibracion": [[20250805, 20260331]],
   "definiciones": [...], "control": {def: control}, "ejecuciones": ["M_sl1.0_tp2.0_N", ...], "limpios": [a, b] (opcional)}

  python tools/a5_campana.py calibrar_m1 <carpeta> <datos M1>   # tablas M1 en la ventana de calibración (ya mirada)
  python tools/a5_campana.py lanzar_ticks <carpeta>             # las mismas tablas en ticks reales (Kaggle, tools/tablas.py lanzar)
  python tools/a5_campana.py traer_ticks <carpeta>
  python tools/a5_campana.py calibracion <carpeta>              # M1 contra ticks por sesión → CALIBRACION.json (commitear antes de correr)
  python tools/a5_campana.py correr <carpeta> <datos M1>        # eventos de toda la ventana; desenlaces SÓLO en DESC y REP
  python tools/a5_campana.py desc <carpeta>                     # BH q 0,10 → DESC.json (commitear antes de rep)
  python tools/a5_campana.py rep <carpeta>                      # nominadas con un paso de LORD++ → REP.json
Los desenlaces de HOLDOUT/EMBARGO no se calculan acá: sólo con la apertura registrada (holdout_ventanas) y su reserva de LORD++.
"""
import importlib, json, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.research import a5 as A5  # noqa: E402


def _cfg(carpeta):
    c = json.loads((Path(carpeta) / "CAMPANA.json").read_text(encoding="utf-8")); c["dir"] = Path(carpeta); return c


def _commiteado(p):
    r = subprocess.run(["git", "status", "--porcelain", str(p)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    h = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(p)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return bool(h) and not r


def _ctx(inst, datos, d0, d1):
    """`datos` None: la copia local verificada de `tools/datos.py` (acceso estándar; una carpeta a mano ya no hace falta)."""
    from edgelab.research.fuentes_ticks import bloques_m1nt8, TICK_FUTURO, TICK_M1NT8_EXTRA
    if datos is None:
        from datos import ruta
        datos = ruta("M1NT8")
    from edgelab.research.grilla_generica import contexto_m1
    return contexto_m1(bloques_m1nt8(inst, int(d0), int(d1), str(datos)), TICK_FUTURO.get(inst) or TICK_M1NT8_EXTRA[inst])


def _tabla(cfg, ctx):
    from edgelab.research import tablas as TB
    return TB.generar(importlib.import_module(cfg["modulo"]), ctx)


def _fric(inst):
    from edgelab.research.embudo_runners import friccion
    return float(friccion(inst)[0])


def calibrar_m1(carpeta, datos):
    cfg = _cfg(carpeta); out = cfg["dir"] / "calibracion_m1"; out.mkdir(exist_ok=True)
    for inst in cfg["instrumentos"]:
        for d0, d1 in cfg["calibracion"]:
            ctx = _ctx(inst, datos, d0, d1); assert ctx.get("m1_sintetico"), "el contexto M1 no quedó marcado (K40)"
            T = _tabla(cfg, ctx); T.to_csv(out / f"M1_{inst}_{d0}_{d1}.csv.gz", index=False); print("M1", inst, d0, d1, len(T), flush=True)


def lanzar_ticks(carpeta):
    cfg = _cfg(carpeta); v = [f"{i}:{a}:{b}" for i in cfg["instrumentos"] for a, b in cfg["calibracion"]]
    subprocess.run([sys.executable, str(ROOT / "tools/tablas.py"), "lanzar", cfg["modulo"], *v], check=True)


def traer_ticks(carpeta):
    subprocess.run([sys.executable, str(ROOT / "tools/tablas.py"), "traer", _cfg(carpeta)["modulo"]], check=True)


def _ticks(cfg, inst, d0, d1):
    from edgelab.research import tablas as TB
    mod = importlib.import_module(cfg["modulo"]); d = Path(getattr(mod, "CARPETA", ROOT / f"docs/research/tablas/{mod.NOMBRE}")) / "tablas"
    f = sorted(d.glob(f"TABLA_{mod.NOMBRE}_{inst}_{d0}_{d1}*.csv.gz"))
    if not f: raise SystemExit(f"falta la tabla de ticks de {inst} {d0}-{d1} en {d} (tools/a5_campana.py traer_ticks)")
    # una tabla de ticks que corrió con OTRO código no calibra nada (2026-11-18: `tablas.py traer` no re-descarga si el archivo ya
    # existe, y la calibración de ESCALONADAS-M1 comparó tablas viejas contra M1 nuevo)
    from edgelab.research.preflight import codigo_vigente
    js = Path(str(f[0]).replace(".csv.gz", ".json"))
    viejo = codigo_vigente(json.loads(js.read_text()), ROOT) if js.exists() else ["sin json de procedencia"]
    if viejo: raise SystemExit(f"tabla de ticks NO VIGENTE ({f[0].name}: {viejo}); moverla y volver a traer")
    return pd.read_csv(f[0])


def _por_sesion(T, d, e):
    g = T[T[d].astype(bool) & T[f"r_{e}"].notna()]
    return {int(s): float(v) for s, v in g.groupby(g.ses.astype(int))[f"r_{e}"].sum().items()}


def insumos_distintos(K: pd.DataFrame, M: pd.DataFrame, defs) -> list:
    """K54 (2026-11-19): columnas de contexto (no desenlaces ni definiciones) que el M1 trae y la tabla de ticks no (p. ej. VIX: el kernel de
    Kaggle no tenía el parquet de CBOE y el módulo cayó en silencio a un respaldo) → ticks y M1 midieron reglas distintas."""
    out = []
    for c in sorted(set(K.columns) & set(M.columns)):
        if c in defs or c.startswith(("r_", "k_")) or not (pd.api.types.is_numeric_dtype(K[c]) and pd.api.types.is_numeric_dtype(M[c])): continue
        if M[c].notna().mean() > 0.5 and K[c].notna().mean() < 0.05: out.append(c)
    return out


def calibracion(carpeta):
    cfg = _cfg(carpeta); res = {}
    defs = list(cfg["definiciones"]) + sorted(set(cfg.get("control", {}).values()))
    for inst in cfg["instrumentos"]:
        for d0, d1 in cfg["calibracion"]:
            M = pd.read_csv(cfg["dir"] / "calibracion_m1" / f"M1_{inst}_{d0}_{d1}.csv.gz"); dif = insumos_distintos(_ticks(cfg, inst, d0, d1), M, defs)
            if dif: raise SystemExit(f"K54: la tabla de ticks de {inst} no tiene {dif} y el M1 sí (insumo externo ausente en Kaggle): no calibra nada")
    pares = {tuple(x) for x in cfg["pares"]} if cfg.get("pares") else None
    ctrl_ej = {c: e for (d, e) in (pares or []) for dd, c in cfg.get("control", {}).items() if dd == d}
    for d in defs:
        for e in cfg["ejecuciones"]:
            if pares and (d, e) not in pares and ctrl_ej.get(d) != e: continue
            t, m = {}, {}
            for inst in cfg["instrumentos"]:
                for d0, d1 in cfg["calibracion"]:
                    M = pd.read_csv(cfg["dir"] / "calibracion_m1" / f"M1_{inst}_{d0}_{d1}.csv.gz"); K = _ticks(cfg, inst, d0, d1)
                    t.update({(inst, s): v for s, v in _por_sesion(K, d, e).items()}); m.update({(inst, s): v for s, v in _por_sesion(M, d, e).items()})
            res[f"{d}|{e}"] = A5.calibrar_por_sesion(t, m)
    sin = [k for k, v in res.items() if not v.get("sesiones")]
    if sin:   # K53 (2026-11-19): una definición que no dispara en toda la ventana de calibración es un posible error de código, no «no calibra»
        raise SystemExit(f"K53: sin disparos en la calibración: {sin}. Revisar el módulo (p. ej. sesiones que cruzan la medianoche) antes de seguir")
    out = dict(preregistro=cfg["preregistro"], celdas=res, calibran=sum(v["calibra"] for v in res.values()), total=len(res))
    (cfg["dir"] / "CALIBRACION.json").write_text(json.dumps(out, indent=1, default=float)); print(out["calibran"], "/", out["total"], "calibran")


def columnas_ops(O, cfg) -> list:
    """Columnas de OPS_DESC_REP, sin repetir. K45 (2026-11-18): se conservan SIEMPRE las columnas de identidad (texto: trig/base/conf
    del filtro de picos se perdían y el análisis pareado no podía emparejar gatillos), más las que CAMPANA.json declare en `conservar`."""
    c = ["k", "ses", "t", "inst", "bloque", "lado", "rg"] + [x for x in O.columns if pd.api.types.is_string_dtype(O[x]) or pd.api.types.is_object_dtype(O[x]) or x in cfg.get("conservar", [])] + \
        [d for d in O.columns if d in cfg["definiciones"] or d in cfg.get("control", {}).values()] + \
        [x for x in O.columns if x.startswith(("r_", "k_")) and x[2:] in cfg["ejecuciones"]]
    return list(dict.fromkeys(x for x in c if x in O.columns))


def correr(carpeta, datos):
    cfg = _cfg(carpeta)
    if not _commiteado(cfg["dir"] / "CALIBRACION.json"): raise SystemExit("CALIBRACION.json sin commitear: la corrida va después")
    mod = importlib.import_module(cfg["modulo"]); ev, ops, cnt = [], [], {}
    for inst in cfg["instrumentos"]:
        ctx = _ctx(inst, datos, *cfg["ventana"]); E = mod.eventos(ctx)
        k = E.k.to_numpy(np.int64); E["ses"] = np.asarray(ctx["ses"])[k]; E["t"] = np.asarray(ctx["t"], float)[k]
        E["bloque"] = A5.bloques(E.ses.to_numpy()); E["inst"] = inst
        ev.append(E.drop(columns=[c for c in E.columns if c.startswith(("r_", "k_"))], errors="ignore"))
        from edgelab.research import ejecucion as X, rasgos_comunes as RC
        vis = E[A5.con_desenlace(E)].reset_index(drop=True)
        ops.append(X.desenlaces(RC.agregar(vis, ctx), ctx, mod.EJECUCIONES))   # agregar/desenlaces conservan filas y columnas
        defs = list(cfg["definiciones"]) + sorted(set(cfg.get("control", {}).values()))
        cnt[inst] = {b: {d: int(E.loc[E.bloque == b, d].astype(bool).sum()) for d in defs} for b in ("DESC", "REP", "HOLDOUT", "EMBARGO")}
        print(inst, json.dumps(cnt[inst]), flush=True)
    pd.concat(ev, ignore_index=True).to_csv(cfg["dir"] / "EVENTOS.csv.gz", index=False)
    O = pd.concat(ops, ignore_index=True)
    keep = columnas_ops(O, cfg)
    O[keep].to_csv(cfg["dir"] / "OPS_DESC_REP.csv.gz", index=False)
    (cfg["dir"] / "CORRIDA.json").write_text(json.dumps(dict(ventana=cfg["ventana"], instrumentos=cfg["instrumentos"], marcas_por_bloque=cnt), indent=1))


def _evaluar(cfg, bloque):
    O = pd.read_csv(cfg["dir"] / "OPS_DESC_REP.csv.gz")
    fr = {i: _fric(i) for i in cfg["instrumentos"]}
    for e in cfg["ejecuciones"]:                                   # fricción en R de cada fila con la de SU instrumento
        O[f"f_{e}"] = O.inst.map(fr) / O[f"k_{e}"]
    pares = {tuple(x) for x in cfg["pares"]} if cfg.get("pares") else None
    res = A5.evaluar(O, bloque, cfg["definiciones"], cfg["ejecuciones"], None, cfg.get("control"), cfg.get("limpios"), pares)
    por_inst = {}
    for inst in cfg["instrumentos"]:
        for e in cfg["ejecuciones"]:
            for d in cfg["definiciones"]:
                if pares and (d, e) not in pares: continue
                g = O[(O.inst == inst) & (O.bloque == bloque) & O[d].astype(bool) & O[f"r_{e}"].notna()]
                por_inst[f"{inst}|{d}|{e}"] = dict(n=int(len(g)), R_bruto=float(g[f"r_{e}"].mean()) if len(g) else None)
    return res, por_inst


def desc(carpeta):
    cfg = _cfg(carpeta); res, pi = _evaluar(cfg, "DESC"); cal = json.loads((cfg["dir"] / "CALIBRACION.json").read_text())["celdas"]
    ctrl = cfg.get("control", {})

    def calibra(k):
        dd, e = k.split("|"); partes = dd.split("-")
        return all(cal.get(f"{x}|{e}", {}).get("calibra", False) for x in partes)
    nom = A5.nominar(res, 0.10, calibra)
    out = dict(preregistro=cfg["preregistro"], pruebas=len(res), resultados=res, por_instrumento=pi, nominadas=nom, control=ctrl)
    (cfg["dir"] / "DESC.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(nom))


def rep(carpeta):
    from edgelab.funnel.libro_lord import LibroLord
    cfg = _cfg(carpeta)
    if not _commiteado(cfg["dir"] / "DESC.json"): raise SystemExit("DESC.json sin commitear: la réplica va después")
    nom = json.loads((cfg["dir"] / "DESC.json").read_text())["nominadas"]
    # K49: potencia en días ANTES de leer REP; las celdas sin potencia no gastan la réplica (quedan SIN_POTENCIA_PREVIA)
    O = pd.read_csv(cfg["dir"] / "OPS_DESC_REP.csv.gz"); planes = {}
    for k in nom:
        dd, e = k.split("|"); d0 = dd.split("-")[0]
        desc = O[(O.bloque == "DESC") & O[d0].astype(bool) & O[f"r_{e}"].notna()]
        n_rep = int(O[(O.bloque == "REP") & O[d0].astype(bool)].ses.nunique())            # sólo cuenta sesiones, no lee desenlaces
        planes[k] = A5.plan_lectura(cfg["familia"], desc.ses.to_numpy(), desc[f"r_{e}"].to_numpy(float), n_rep)
    con = [k for k in nom if planes[k].get("potencia", 0) >= A5.POTENCIA_LECTURA_MIN]
    if nom and not con: raise SystemExit(f"K49: ninguna nominada llega a potencia {A5.POTENCIA_LECTURA_MIN} en REP: {json.dumps({k: planes[k].get('potencia') for k in nom})}")
    res, pi = _evaluar(cfg, "REP"); res = {k: res[k] for k in con}
    dec = LibroLord().probar(cfg["familia"], f"REP_{cfg['dir'].name}", [(k, res[k]["p"]) for k in con]) if con else None
    res.update({k: dict(estado="SIN_POTENCIA_PREVIA", plan=planes[k]) for k in nom if k not in con})
    (cfg["dir"] / "REP.json").write_text(json.dumps(dict(nominadas=nom, resultados=res, por_instrumento=pi, lord=dec), indent=1, default=float))
    print(json.dumps(dec))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"calibrar_m1": lambda: calibrar_m1(a[1], a[2] if len(a) > 2 else None), "lanzar_ticks": lambda: lanzar_ticks(a[1]), "traer_ticks": lambda: traer_ticks(a[1]),
     "calibracion": lambda: calibracion(a[1]), "correr": lambda: correr(a[1], a[2] if len(a) > 2 else None), "desc": lambda: desc(a[1]), "rep": lambda: rep(a[1])}[a[0]]()
