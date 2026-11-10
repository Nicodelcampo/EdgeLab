# Principal del kernel HFT-CLUSTERS-INFO (docs/research/hft_clusters_u1_20261110/PREREGISTRO_E0_E_INFORMACION.md).
# MODO=e0: sin retornos. Clusters por sesión, ancho, zonas y packing de 2 zonas x 4 clusters en NQ, ES, YM y GC (DESC), y la definición
#          elegida por activo con la regla mecánica (hft_clusters_info.elegir_definicion).
# MODO=info / MODO=rep: UNA hipótesis. Carrera a ±X tras el toque del borde, real contra placebo desplazado, con la definición de DEFS
#          (la que eligió el E0), en DESC o en la réplica abr → sep. Reutiliza fuentes_ticks.bloques_futuro y el espejo Numba del indicador.
# Salida: HFTC_<MODO>.json y HFTC_<MODO>.csv.
import json
import os
import time
from statistics import NormalDist

import pandas as pd

MODO = "e0"                                                   # lo fija tools/hft_clusters_info.py al construir
DEFS = {}                                                     # {inst: [zona, cluster]}, congelado tras el E0
INSTRUMENTOS = ("NQ", "ES", "YM", "GC")
DESC, REP = (20250701, 20260331), (20260401, 20260930)
FRICCION = {"NQ": 1.5455, "ES": 0.8877, "YM": 5.052, "GC": 0.605}   # edgelab/costos.py, puntos por viaje (2026-11-10)


def main():
    from edgelab.research import fuentes_ticks as F, hft_clusters_info as H
    ent = os.environ.get("ENTRADA", "/kaggle/input"); t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    d0, d1 = REP if MODO == "rep" else DESC
    res = dict(experimento="HFT-CLUSTERS-INFO", modo=MODO, ventana=[d0, d1], codigo=CODIGO_SHA, modulos=MODULOS_SHA, friccion_pts=FRICCION,
               barrera_pts={i: H.barrera(FRICCION[i], F.TICK_FUTURO[i]) for i in INSTRUMENTOS}, zonas=H.ZONAS, clusters=H.CLUSTERS)
    filas = []
    ZN, CL = (H.ZONAS, H.CLUSTERS) if MODO != "e0b" else ({"Z_CERT": H.ZONAS["Z_CERT"]}, H.CLUSTERS_B)
    for inst in (INSTRUMENTOS if MODO in ("e0", "e0b") else [i for i in INSTRUMENTOS if i in DEFS]):
        tk = F.TICK_FUTURO[inst]; n = 0
        try: bloques = list(F.bloques_futuro(inst, d0, d1, ent))             # generador: la falta de archivo salta al iterar
        except (IndexError, ValueError): log(f"{inst}: sin datos"); continue
        for B in bloques:
            if len(B) < 1000: continue
            fecha = int(B.sesion.iloc[0]); ts, px = B.ts_ns.to_numpy(), B.px.to_numpy()
            D = H.clusters_del_dia(ts, px, B.vol.to_numpy(), B.sesion.to_numpy(), tk, ZN, CL, H.barrera(FRICCION[inst], tk)); n += 1
            if MODO in ("e0", "e0b"):
                for zk in ZN:
                    for ck in CL: filas.append(H.e0_fila(inst, fecha, zk, ck, D.get((zk, ck)), tk, FRICCION[inst]))
            else:
                C = D.get(tuple(DEFS[inst]))
                if C is not None:
                    filas += [dict(f, prueba="rebote") for f in H.info_del_dia(inst, fecha, ts, px, C, tk, FRICCION[inst])]
                    filas += [dict(f, prueba="iman") for f in H.iman_del_dia(inst, fecha, ts, px, C, tk, FRICCION[inst])]
        log(f"{inst}: {n} sesiones, {len(filas)} filas acumuladas")
    T = pd.DataFrame(filas); T.to_csv(f"HFTC_{MODO}.csv", index=False)
    if MODO == "e0b" and len(T):
        res["equilibrio"] = H.elegir_equilibrio(T, FRICCION)
    elif MODO == "e0" and len(T):
        g = T.groupby(["inst", "zona", "cluster"])
        res["definiciones"] = [dict(inst=k[0], zona=k[1], cluster=k[2], sesiones=int(len(h)), clusters_por_sesion=float(h.n.mean()),
                                    ancho_pts_mediano=float(h.ancho_pts_med.median()) if "ancho_pts_med" in h else None,
                                    frac_ancho_menor_X=float(h.frac_ancho_menor_X.mean()) if "frac_ancho_menor_X" in h else None,
                                    friccion_r_stop_ancho=float(h.friccion_r_stop_ancho.median()) if "friccion_r_stop_ancho" in h else None,
                                    por_mes={str(m): float(v) for m, v in h.assign(mes=h.fecha // 100).groupby("mes").n.mean().items()}) for k, h in g]
        res["eleccion"] = H.elegir_definicion(T)
    elif len(T):
        for prueba, Tp in T.groupby("prueba"):                             # dos hipótesis separadas: rebote (tras el toque) e imán (antes del toque)
            r = dict(por_activo={i: H.contraste(h) for i, h in Tp.groupby("inst")}, conjunto=H.contraste(Tp))
            ps = [c["p_unilateral"] for c in r["por_activo"].values() if "p_unilateral" in c]
            if ps:
                z = sum(NormalDist().inv_cdf(min(max(1 - p, 1e-6), 1 - 1e-6)) for p in ps) / len(ps) ** 0.5
                r["stouffer"] = dict(z=float(z), p=float(1 - NormalDist().cdf(z)), activos=len(ps))
            res[prueba] = r
    json.dump(res, open(f"HFTC_{MODO}.json", "w"), indent=1, default=float); log(json.dumps({i: (v["elegida"] or {}) for i, v in res["equilibrio"].items()} if "equilibrio" in res else res.get("eleccion") or {k: res[k].get("stouffer") for k in ("rebote", "iman") if k in res}))


if __name__ == "__main__":
    main()
