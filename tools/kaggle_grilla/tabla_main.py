# Principal genérico de tablas de eventos (edgelab/research/tablas.py): eventos + rasgos + desenlaces de TODAS las ejecuciones
# declaradas por el módulo, para UNA fuente y UNA ventana. Sólo tabla: ninguna selección con desenlaces dentro del kernel (K19).
# Variables: MODULO (ruta de import), FUENTE (NQ | ES | DK:USATECHIDXUSD | ... | SINT), DESDE, HASTA (YYYYMMDD).
# SELLADO=1 (sólo una apertura registrada del holdout): lee los ticks sellados de la fuente con el acta de ACTA_JSON.
# Salida: TABLA_<NOMBRE>_<fuente>_<desde>_<hasta>.csv.gz y .json (procedencia: código y módulos).
import glob
import importlib
import json
import os
import time


def main():
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, tablas as TB
    mod = importlib.import_module(os.environ["MODULO"]); fuente = os.environ.get("FUENTE", "NQ")
    d0, d1 = int(os.environ.get("DESDE", 20250805)), int(os.environ.get("HASTA", 20260331)); ent = os.environ.get("ENTRADA", "/kaggle/input")
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    if fuente == "SINT":                                                   # prueba local del kernel (preflight)
        bl, tick = list(TB.bloques_sinteticos(mod, 20, 5)), getattr(mod, "PREFLIGHT_PRECIO", (None, 0.25))[1]
    elif os.environ.get("SELLADO") == "1":
        acta = os.path.abspath("ACTA_HOLDOUT.json"); json.dump(json.loads(os.environ["ACTA_JSON"]), open(acta, "w"))
        d0 = max(d0, F.HOLDOUT_PRIMERA_SESION_INT)
        if fuente.startswith("DK:"):                                      # spot sellado (carpeta del dataset, un parquet por símbolo)
            sym = fuente[3:]; tick = F.REDONDEO_SPOT[sym]
            raiz = os.path.dirname(sorted(glob.glob(ent + f"/**/{sym}_ticks.parquet", recursive=True))[0])
            bl = F.bloques_spot_sellado(sym, d0, d1, raiz)
        else:
            tick = F.TICK_FUTURO[fuente]; rs = sorted(glob.glob(ent + f"/**/{fuente}_*ticks.parquet", recursive=True))
            bl = F.bloques_nq_sellado(d0, d1, rs, acta, tick)
    else:
        lector, tick = F.resolver(fuente); bl = lector(d0, d1, ent)
    ctx = GG.contexto_m1(bl, tick); log(f"{fuente}: {len(ctx['c'])} velas, {len(ctx['tpx'])} ticks")
    T = TB.generar(mod, ctx); log(f"{len(T)} eventos")
    nom = f"TABLA_{mod.NOMBRE}_{fuente.replace('DK:', '')}_{d0}_{d1}"
    T.to_csv(nom + ".csv.gz", index=False)
    defs = [c for c in getattr(mod, "DEFINICIONES", []) if c in T]
    res = dict(modulo=mod.__name__, nombre=mod.NOMBRE, fuente=fuente, ventana=[d0, d1], sellado=os.environ.get("SELLADO") == "1",
               codigo=CODIGO_SHA, modulos=MODULOS_SHA, tick=tick, velas=int(len(ctx["c"])), sesiones=int(len(set(ctx["ses"].tolist()))),
               eventos=int(len(T)), por_definicion={c: int(T[c].sum()) for c in defs}, segundos=round(time.time() - t0))
    json.dump(res, open(nom + ".json", "w"), indent=1); log(json.dumps({k: res[k] for k in ("eventos", "sesiones", "segundos")}))


main()
