# Control nulo repetido de la criba maxT: UNA simulación de DESC y N sorteos de `neutralizar` sobre el MISMO P&L, por el camino real
# (neutralizar -> tensor -> estadisticas -> criba_maxt). Compara con una nula de control sobre la matriz sesión x celda.
# Además sortea MATRIZ_N signos con default_rng(s) sobre la matriz: la tasa de t_max > q90 distingue azar de defecto con mucha más potencia.
# Entorno: EXPERIMENTO, SENSOR, EJECUCION, DESDE, HASTA (<= 20260331), FRICCION, EXTRA, SEMILLAS (N), SEMILLA_DESDE, MATRIZ_N, B_POOL, TOPE_S. Salida: RESULTADO.json.
import importlib
import json
import os
import time

import numpy as np


class _Alto(Exception):
    pass


def main():
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, grilla_masiva as GM
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    exp = importlib.import_module(os.environ["EXPERIMENTO"]); sensor = os.environ["SENSOR"]
    d0, d1 = int(os.environ["DESDE"]), int(os.environ["HASTA"])
    if d1 >= 20260401: raise ValueError("el control nulo no toca OOS")
    N, BP, tope = int(os.environ.get("SEMILLAS", 40)), int(os.environ.get("B_POOL", 2000)), float(os.environ.get("TOPE_S", 30000))
    lec, tk = F.resolver(sensor); ctx = GG.contexto_m1(lec(d0, d1, os.environ.get("ENTRADA", "/kaggle/input")), tk); ctx.update(sensor=sensor, desde_eval=d0)
    cap = {}
    def _cap(e, cx, **k): cap["cx"] = cx; raise _Alto
    GG.canales = _cap
    try: GG.correr(exp, ctx, modo="DESC", friccion=float(os.environ["FRICCION"]), extra_adverso=float(os.environ["EXTRA"]), log=log)
    except _Alto: pass
    cx = cap["cx"]; P, idx, net, ses = cx["perillas"], cx["indices"], cx["net"], cx["ses"]; ei = idx[-1]
    st0 = cx["st"]; ev = st0["evaluable"].ravel(); n_ev = int(ev.sum()); us, inv = np.unique(ses, return_inverse=True)
    res = dict(experimento=exp.NOMBRE, desde=d0, hasta=d1, evaluables=n_ev, sesiones=len(us), B=GG.B_RW, alfa=GG.ALFA_RW, corridas=[], codigo=CODIGO_SHA)
    guarda = lambda: json.dump(res, open("RESULTADO.json", "w"), indent=1, default=float)
    cent = GG.neutralizar(net, ei, ses, 0) * np.random.default_rng(0).choice((-1.0, 1.0), size=len(us))[inv]   # P&L centrado sin signos
    bs = GM._Bootstrap(P, idx, cent, inv, len(us), ev, np.ones((1, len(us)))); M = bs._sumas(0, n_ev)[0]; d = np.sqrt((M ** 2).sum(0)); ok = d > 0
    M, d = M[:, ok], d[ok]; log(f"matriz {M.shape}, sesiones con operaciones {int((M != 0).any(1).sum())}")
    sv = np.linalg.svd(M / d, full_matrices=False, compute_uv=False); res["espectro"] = dict(sv2_top=(sv[:5] ** 2 / (sv ** 2).sum()).tolist())
    r = np.random.default_rng(999); pool = []
    for a in range(0, BP, 200):
        S = r.choice((-1.0, 1.0), size=(200, len(us))); pool.append(((S @ M) / d).max(1))
    pool = np.sort(np.concatenate(pool)); res["pool"] = dict(n=len(pool), q50=float(np.quantile(pool, .5)), q90=float(np.quantile(pool, .9)), q99=float(np.quantile(pool, .99)), max=float(pool[-1])); log(str(res["pool"])); guarda()
    MN = int(os.environ.get("MATRIZ_N", 20000)); tms = np.empty(MN)
    for a in range(0, MN, 200):
        S = np.stack([np.random.default_rng(s + 1).choice((-1.0, 1.0), size=len(us)) for s in range(a, min(MN, a + 200))]); tms[a:a + 200] = ((S @ M) / d).max(1)
    res["matriz_semillas"] = dict(n=MN, q90_pool=res["pool"]["q90"], tasa_sobre_q90=float((tms > res["pool"]["q90"]).mean()), q50=float(np.quantile(tms, .5)), q90=float(np.quantile(tms, .9)), q99=float(np.quantile(tms, .99)),
                                  tasa_primeras_40=float((tms[:40] > res["pool"]["q90"]).mean())); log(str(res["matriz_semillas"])); guarda()
    d0s = int(os.environ.get("SEMILLA_DESDE", 41))
    for s in range(d0s, d0s + N):
        if time.time() - t0 > tope: log("tope de tiempo"); break
        x = GG.neutralizar(net, ei, ses, s); st = GM.estadisticas(*GM.tensor(P, idx, x)); mt = GM.criba_maxt(P, idx, x, ses, st, B=GG.B_RW, alfa=GG.ALFA_RW)
        sg = np.random.default_rng(s).choice((-1.0, 1.0), size=len(us)); tm = float(((sg @ M) / d).max())
        fila = dict(semilla=s, n_nominadas=mt["n_nominadas"], p=mt["p_del_maximo"], t_max=mt["t_max"], umbral=mt["umbral"], t_max_matriz=tm, ev=int(st["evaluable"].sum()), p_pool=float((1 + (pool >= mt["t_max"]).sum()) / (len(pool) + 1)))
        res["corridas"].append(fila); guarda(); log(str(fila))
    log("listo")


main()
