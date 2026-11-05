# E0 sin desenlaces de PRERANGE-ZONAS: censo por conjunto, cortes y poda. No simula operaciones. Ventana fija de DESC.
# Entorno: INSTS (NQ,ES,YM). Salida: E0_PRERANGE_ZONAS.json y RESULTADO.json, reescritos tras cada activo.
import json
import os
import time


def main():
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, prerange_zonas as Z
    ent = os.environ.get("ENTRADA", "/kaggle/input"); d0, d1 = 20250805, 20260331; t0 = time.time()
    res = dict(experimento=Z.NOMBRE, desde=d0, hasta=d1, target_free=True, codigo=CODIGO_SHA, modulos=MODULOS_SHA, activos={})
    for inst in os.environ.get("INSTS", "NQ,ES,YM").split(","):
        lec, tick = F.resolver(inst); ctx = GG.contexto_m1(lec(d0, d1, ent), tick); ctx.update(sensor=inst)
        lc, tc = F.resolver("DK:" + F.DUKASCOPY[inst]); ctx["conf"] = GG.contexto_m1(lc(d0, d1, ent), tc)
        c = Z.censo(ctx, Z.IND_POR_INST[inst]); c["poda"] = Z.podar(c); res["activos"][inst] = c
        for f in ("E0_PRERANGE_ZONAS.json", "RESULTADO.json"): json.dump(res, open(f, "w"), indent=1, default=float)
        print(f"[{time.time() - t0:7.0f}s] {inst}: {c['disparos']} disparos, poda {c['poda']}", flush=True)


main()
