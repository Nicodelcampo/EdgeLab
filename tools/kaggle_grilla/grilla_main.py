# Principal GENÉRICO de kernels de grilla (lo envuelve tools/kaggle_grilla/construir_kernel.py con los módulos embebidos).
# Corre cualquier experimento con la interfaz de edgelab/research/grilla_generica.py.
# Entorno: EXPERIMENTO = módulo (p. ej. edgelab.research.u1_indaga) · FUENTE = NQ | USATECH · MODO = E0 | DESC | REP ·
#          DESDE/HASTA = YYYYMMDD · CORTES = JSON {variable: [cortes]} (REP: congelados) · CELDAS = JSON [[...]] (REP).
import importlib
import json
import os
import time


def main():
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG
    exp = importlib.import_module(os.environ["EXPERIMENTO"])
    fuente, modo = os.environ.get("FUENTE", "NQ"), os.environ.get("MODO", "E0")
    desde, hasta = int(os.environ["DESDE"]), int(os.environ["HASTA"])
    lector, tick, friccion, extra = F.FUENTES[fuente]
    cortes = json.loads(os.environ["CORTES"]) if os.environ.get("CORTES") else None
    celdas = json.loads(os.environ["CELDAS"]) if os.environ.get("CELDAS") else None
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    ctx = GG.contexto_m1(lector(desde, hasta, os.environ.get("ENTRADA", "/kaggle/input")), tick); log(f"M1 {len(ctx['c'])} velas")
    res, cx = GG.correr(exp, ctx, modo=modo, friccion=friccion, extra_adverso=extra, cortes=cortes, celdas=celdas, log=log)
    res.update(fuente=fuente, desde=desde, hasta=hasta, friccion_pts=friccion, codigo=CODIGO_SHA, modulos=MODULOS_SHA, n_celdas=GG.n_celdas(exp, res["E0"]["cortes"]))
    nombre = f"{exp.NOMBRE}_{fuente}_{modo}".replace("/", "_")
    json.dump(res, open(f"{nombre}.json", "w"), indent=1, default=float)
    json.dump(dict(res, **GG.para_autopilot(res, fuente)), open("STUDY_RESULTS.json", "w"), indent=1, default=float)
    (cx if modo == "E0" else exp.disparos(ctx)).to_parquet(f"{nombre}_disparos.parquet")          # target-free: disparos y variables
    if modo == "REP": GG.operaciones_de(cx, celdas).to_parquet(f"{nombre}_operaciones.parquet")       # serie por operación (seguimiento secuencial)
    log("listo")


main()
