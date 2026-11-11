# Principal del kernel LUXIMB-HVN (docs/research/luximb_hvn_20261111/PREREGISTRO.md): tabla de eventos (todas las definiciones del
# impulso), rasgos (incluido el nodo de volumen más allá de B) y desenlaces tick a tick de todas las ejecuciones fijadas, para UNA
# fuente y UNA ventana. Sólo tabla: ninguna selección ni resumen con desenlaces dentro del kernel (K19).
# Variables: FUENTE (NQ | DK:USATECHIDXUSD | SINT), DESDE, HASTA (YYYYMMDD). Salida: LXH_<fuente>_<desde>_<hasta>.csv.gz y .json.
import json
import os
import time


def main():
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, luximb_hvn as H
    fuente = os.environ.get("FUENTE", "NQ"); d0, d1 = int(os.environ.get("DESDE", 20250805)), int(os.environ.get("HASTA", 20260331))
    ent = os.environ.get("ENTRADA", "/kaggle/input"); t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    if fuente == "SINT":                                                # sólo prueba local del kernel
        from edgelab.research import sintetico
        bl, tick = sintetico.bloques(dias=12, planta=False, seed=5), 0.25
    else:
        lector, tick = F.resolver(fuente); bl = lector(d0, d1, ent)
    ctx = GG.contexto_m1(bl, tick); log(f"{fuente}: {len(ctx['c'])} velas M1, {len(ctx['tpx'])} ticks")
    E = H.eventos(ctx); log(f"{len(E)} eventos únicos")
    T = H.desenlaces(E, ctx); log("desenlaces listos")
    nom = f"LXH_{fuente.replace('DK:', '')}_{d0}_{d1}"
    T.to_csv(nom + ".csv.gz", index=False)
    defs = [c for c in T.columns if c[:1] == "D" and "_a" in c and "_z" in c]
    res = dict(experimento="LUXIMB-HVN", fuente=fuente, ventana=[d0, d1], codigo=CODIGO_SHA, modulos=MODULOS_SHA, tick=tick,
               velas=int(len(ctx["c"])), sesiones=int(len(set(ctx["ses"].tolist()))), eventos=int(len(T)),
               por_definicion={c: int(T[c].sum()) for c in defs}, columnas=list(T.columns), segundos=round(time.time() - t0))
    json.dump(res, open(nom + ".json", "w"), indent=1); log(json.dumps({k: res[k] for k in ("eventos", "sesiones", "segundos")}))


main()
