# E0 target-free de PRERANGE-HFT: disparos, S y evaluables por activo, ANTES de DESC. No simula operaciones.
# Entorno: INSTS (ES,NQ,YM), DESDE, HASTA (<= 20260331 para el E0 de DESC). Salida: E0_PRERANGE_HFT.json.
import json
import os


def main():
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, prerange_hft as X
    ent = os.environ.get("ENTRADA", "/kaggle/input"); d0, d1 = int(os.environ.get("DESDE", 20250805)), int(os.environ.get("HASTA", 20260331))
    if d1 > 20260930: raise ValueError("el E0 no toca el holdout")
    res = dict(experimento=X.NOMBRE, desde=d0, hasta=d1, codigo=CODIGO_SHA, modulos=MODULOS_SHA, activos={})
    for inst in os.environ.get("INSTS", "ES,NQ,YM").split(","):
        lec, tick = F.resolver(inst)
        ctx = GG.contexto_m1(lec(d0, d1, ent), tick); ctx.update(sensor=inst)
        D = X.disparos(ctx); D["ses"] = ctx["ses"][D.k.to_numpy().astype(int)]
        cortes = GG.cortes_e0(D, X.VARIABLES)
        res["activos"][inst] = dict(GG.resumen_e0(D, X.VARIABLES, cortes), diagnostico=X.diagnostico_e0(D, cortes))
        print(inst, json.dumps(res["activos"][inst]["diagnostico"]["por_fuente"]), flush=True)
    json.dump(res, open("E0_PRERANGE_HFT.json", "w"), indent=1, default=float)


main()
