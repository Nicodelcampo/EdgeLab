# Principal del kernel U1-ORO (docs/research/u1_oro_20261025/PREREGISTRO_U1_ORO.md): la regla U1-CRUZADO congelada, con la señal
# en el oro spot de Dukascopy (XAUUSD) y la operación en GC. Lo único que se traslada es la escala: W (alto del área, 40 pts) y G
# (separación, 1 pt) se multiplican por r = rango M1 mediano de XAU del trimestre ANTERIOR / rango M1 mediano de USATECH en el
# descubrimiento de U1 (2025-08-05 → 2026-03-31). Todo lo demás (A/H ≥ 8, x = 0,25, N ≥ 3, ejecuciones T1/T3 con stop S3) queda igual.
# Reutiliza u1_cruzado.senales/operar/operar_propio, fuentes_ticks, grilla_generica.contexto_m1 y escalera.resumen_sesiones.
# Entorno: FRICCION (puntos de GC, edgelab.costos). Salida: U1_ORO.json y U1_ORO_operaciones.csv.
import json
import os
import time

import numpy as np
import pandas as pd

REF_US = (20250805, 20260331)
PERIODOS = {"proxy_xau": (20230101, 20250804), "cruzado_gc": (20250805, 20260930)}


def trimestres(d0, d1):
    for a in range(d0 // 10000, d1 // 10000 + 1):
        for q0, q1 in ((101, 331), (401, 630), (701, 930), (1001, 1231)):
            lo, hi = max(a * 10000 + q0, d0), min(a * 10000 + q1, d1)
            if lo <= hi: yield lo, hi


def rango_m1(ctx):
    return float(np.median(ctx["h"] - ctx["l"]))


def main():
    from edgelab.funnel import escalera as ES
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, u1_cruzado as X, u1_indaga as U
    ent = os.environ.get("ENTRADA", "/kaggle/input"); fr = float(os.environ["FRICCION"])
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    W0, G0 = U.W_U1, U.G_U1
    ref = []                                                                     # target-free: escala de USATECH en el descubrimiento
    for lo, hi in trimestres(*REF_US):
        ref.append(rango_m1(GG.contexto_m1(F.bloques_usatech(lo, hi, ent), F.FUENTES["USATECH"][1])))
    r_us = float(np.median(ref)); log(f"rango M1 mediano USATECH (descubrimiento) {r_us:.3f}")
    lx, tx = F.resolver("DK:XAUUSD"); lg, tg = F.resolver("GC"); ops, escala, previo = [], [], None
    for nombre, (d0, d1) in PERIODOS.items():
        for lo, hi in trimestres(d0, d1):
            try: xau = GG.contexto_m1(lx(lo, hi, ent), tx)
            except (ValueError, IndexError): log(f"XAU {lo}-{hi}: sin datos"); continue
            r_q = rango_m1(xau)
            if previo is None: previo = r_q; escala.append(dict(desde=lo, hasta=hi, r_xau_previo=None, nota="primer trimestre: sólo calibra")); continue
            k = previo / r_us; U.W_U1, U.G_U1 = W0 * k, G0 * k; previo = r_q        # escala causal: trimestre anterior
            S = X.senales(xau); escala.append(dict(desde=lo, hasta=hi, factor=k, W=U.W_U1, G=U.G_U1, senales=int(len(S))))
            if not len(S): continue
            P = X.operar_propio(xau, S); P["neto_xau"] = P.bruto - fr; P["periodo"] = nombre
            if nombre == "cruzado_gc":
                del xau["tpx"]
                try: gc = GG.contexto_m1(lg(lo, hi, ent), tg)
                except (ValueError, IndexError): gc = None
                if gc is not None:
                    O = X.operar(xau, gc, S); O["neto"] = O.bruto - fr
                    P = P.merge(O[["k_us", "ejecucion", "base", "motivo", "neto"]], on=["k_us", "ejecucion"], how="left")
            ops.append(P); log(f"{nombre} {lo}-{hi}: factor {k:.3f} W {U.W_U1:.2f}, {len(S)} señales")
    U.W_U1, U.G_U1 = W0, G0
    A = pd.concat(ops, ignore_index=True) if ops else pd.DataFrame()
    res = dict(experimento="U1-ORO", codigo=CODIGO_SHA, modulos=MODULOS_SHA, friccion_pts=fr, rango_m1_usatech=r_us, escala=escala, pruebas={})
    for nombre in PERIODOS:
        g0 = A[A.periodo == nombre] if len(A) else A
        for ej, g in (g0.groupby("ejecucion") if len(g0) else []):
            col = "neto" if nombre == "cruzado_gc" else "neto_xau"
            x = g[col].to_numpy(float); ok = np.isfinite(x)
            r = dict(n=int(ok.sum()))
            if ok.sum() >= 10:
                rs = ES.resumen_sesiones(x[ok], g.ses.to_numpy()[ok], n_boot=20000)
                r.update(media=rs["media"], ic90=rs["ic"], p_unilateral=rs["p_unilateral"], sesiones=rs["n_sesiones"], mde=float(ES.mde(rs["se"])),
                         acierto=float((x[ok] > 0).mean()), peor=float(x[ok].min()), mejor=float(x[ok].max()))
            if nombre == "cruzado_gc":
                xx = g.neto_xau.to_numpy(float); r["mismas_senales_en_xau"] = dict(n=int(np.isfinite(xx).sum()), media=float(np.nanmean(xx)) if np.isfinite(xx).any() else None)
                r["motivos"] = g.motivo.fillna("sin GC").replace("", "operada").value_counts().to_dict()
            res["pruebas"][f"{nombre}/{ej}"] = r
    json.dump(res, open("U1_ORO.json", "w"), indent=1, default=float); A.to_csv("U1_ORO_operaciones.csv", index=False)
    log(json.dumps({k: (v.get("n"), round(v.get("media", float("nan")), 3)) for k, v in res["pruebas"].items()}))


if __name__ == "__main__":
    main()
