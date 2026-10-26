# Principal ÚNICO del embudo de grilla en Kaggle (lo empaqueta edgelab/research/embudo_runners.py con el experimento).
# Entorno: CONFIRMADOR (opcional, segundo instrumento para variables), EXPERIMENTO (ruta de import), ETAPA (E0|DESC|INDAGA|REP|INTEGRIDAD|TOPES), SENSOR (p. ej. NQ o DK:USATECHIDXUSD),
#          EJECUCION (vacío = misma que SENSOR), DESDE/HASTA (YYYYMMDD), FRICCION/EXTRA (de edgelab.costos, los pone el lanzador),
#          PARAMS (JSON: celdas, cortes, bases, topes, tope). Salida: RESULTADO.json (+ STUDY_RESULTS.json para el ciclo autónomo).
import importlib
import json
import os
import time


def main():
    from edgelab.research import etapas as ET, fuentes_ticks as F, grilla_generica as GG
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    exp = importlib.import_module(os.environ["EXPERIMENTO"]); etapa = os.environ["ETAPA"]
    sensor, ejec = os.environ["SENSOR"], os.environ.get("EJECUCION") or ""
    desde, hasta = int(os.environ["DESDE"]), int(os.environ["HASTA"]); ent = os.environ.get("ENTRADA", "/kaggle/input")
    params = json.loads(os.environ.get("PARAMS") or "{}")
    if os.environ.get("SELLADO") == "1":                                  # holdout: datos del dataset sellado; exige el acta en PARAMS
        import glob
        acta = os.path.abspath("ACTA_HOLDOUT.json"); json.dump(params["acta"], open(acta, "w"), default=float)
        raiz = os.path.dirname(glob.glob(ent + "/**/SELLADO.txt", recursive=True)[0])
        def resolver(n):
            if n.startswith("DK:"): return (lambda d0, d1, e=None: F.bloques_spot_sellado(n[3:], d0, d1, os.path.join(raiz, "dukascopy"))), F.REDONDEO_SPOT[n[3:]]
            return (lambda d0, d1, e=None: F.bloques_nq_sellado(d0, d1, glob.glob(raiz + f"/**/{n}_*ticks.parquet", recursive=True)[0], acta)), F.TICK_FUTURO[n]
    else:
        resolver = F.resolver
    lec_s, tk_s = resolver(sensor); ctx = GG.contexto_m1(lec_s(desde, hasta, ent), tk_s); log(f"señal {sensor}: {len(ctx['c'])} velas")
    if (conf := os.environ.get("CONFIRMADOR")):                          # 2026-10-26: segundo instrumento sólo para variables (U1-CONFIRMA)
        lec_c, tk_c = resolver(conf); ctx["conf"] = GG.contexto_m1(lec_c(desde, hasta, ent), tk_c); log(f"confirmador {conf}: {len(ctx['conf']['c'])} velas")
    cx_ej = alin = None
    if ejec and ejec != sensor:
        lec_e, tk_e = resolver(ejec); cx_ej = GG.contexto_m1(lec_e(desde, hasta, ent), tk_e); log(f"ejecución {ejec}: {len(cx_ej['c'])} velas")
        if etapa == "INTEGRIDAD": alin = (lec_s(desde, hasta, ent), lec_e(desde, hasta, ent))
    res = ET.ejecutar(etapa, exp, ctx, friccion=float(os.environ["FRICCION"]), extra_adverso=float(os.environ["EXTRA"]), cx_ej=cx_ej,
                      params=params, bloques_alineacion=alin, log=log)
    res.update(experimento_modulo=os.environ["EXPERIMENTO"], etapa=etapa, sensor=sensor, ejecucion=ejec or sensor, desde=desde, hasta=hasta,
               codigo=CODIGO_SHA, modulos=MODULOS_SHA)
    json.dump(res, open("RESULTADO.json", "w"), indent=1, default=float)
    json.dump(dict(res, **GG.para_autopilot(res, sensor)), open("STUDY_RESULTS.json", "w"), indent=1, default=float)
    log("listo")


main()
