#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TABLA DE DECISIÓN P/N/K — para elegir la geometría ANTES de mirar zonas.

Cruza tres cosas que hasta ahora estaban separadas:

1. **La tasa nula** de tocar el objetivo antes que el stop (placebos del atlas).
2. **La fricción** de 2,7040 ticks round-trip: cuánto tiene que subir esa tasa
   para que la esperanza NETA llegue a cero.
3. **La potencia**: cuál es el corrimiento más chico que los 197 días-bloque
   permiten distinguir del azar.

## Por qué las tres juntas y no la tasa sola

Una geometría puede tener un nulo poco negativo y aun así ser inservible: si
para pagar la fricción hace falta subir la tasa de acierto un 70 %, ninguna
señal basada en niveles llega. Y al revés: una geometría puede ser plausible en
break-even pero tener una tasa base tan baja que el estudio no tenga potencia
para detectar nada.

**El objetivo es descartar geometrías ANTES de gastar el único turno de la cola
de hipótesis**, no después.

## Los dos intervalos

Se reportan los dos a propósito:

- **fijo b=1**: el que usa el arnés hoy. Trata cada día como independiente.
- **estacionario con b de Politis–White**: medido sobre la serie diaria real,
  `b_opt` da **13–18 días** y el intervalo correcto sale **120–143 % más
  ancho**. Los días no son independientes: la volatilidad se agrupa por
  semanas.

El umbral de detección honesto es el del estacionario. Con el fijo, el estudio
**sobre-detectaría**: cruzaría el percentil 95 con corrimientos que son ruido.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.stats.bootstrap_estacionario import (bootstrap_estacionario,  # noqa: E402
                                                  largo_de_bloque_optimo)

# FUENTE UNICA (2026-08-06): antes `2.7040` hardcodeado. Ver costs.py.
from edgelab.research.costs import friccion_rt_ticks  # noqa: E402
FRICCION_RT = friccion_rt_ticks()          # ticks round-trip, 6E
LIFT_IMPLAUSIBLE = 0.30       # umbral declarado ANTES de ver la tabla


def _boot_tasa(por_dia, reps=4000, seed=20260727, estacionario=True):
    """IC de la tasa remuestreando DÍAS. `por_dia`: {fecha: [aciertos, total]}."""
    S = np.array([v[0] for v in por_dia.values()], float)
    T = np.array([v[1] for v in por_dia.values()], float)
    ok = T > 0
    S, T = S[ok], T[ok]
    if len(S) < 3:
        return None
    diaria = S / T                      # serie de tasas diarias, para b_opt
    b = largo_de_bloque_optimo(diaria) if estacionario else 1
    n = len(S)
    rng = np.random.default_rng(seed)
    p = 1.0 / max(b, 1)
    pos = np.arange(n)
    vals = np.empty(reps)
    hecho = 0
    while hecho < reps:
        m = min(2048, reps - hecho)
        inicios = rng.integers(0, n, size=(m, n))
        nuevo = rng.random((m, n)) < p
        nuevo[:, 0] = True
        arr = np.maximum.accumulate(np.where(nuevo, pos[None, :], 0), axis=1)
        idx = (np.take_along_axis(inicios, arr, axis=1) + (pos[None, :] - arr)) % n
        vals[hecho:hecho + m] = S[idx].sum(axis=1) / T[idx].sum(axis=1)
        hecho += m
    return dict(b=int(b), n_bloques=n, p=float(S.sum() / T.sum()),
                ic90=[float(np.percentile(vals, 5)), float(np.percentile(vals, 95))],
                p95=float(np.percentile(vals, 95)))


def break_even(P, N, p_obj, p_stop, friccion=FRICCION_RT):
    """Tasa de objetivo que hace la esperanza NETA = 0, en dos variantes.

    La masa de probabilidad extra tiene que salir de algún lado, y de dónde
    salga cambia el número. Se reportan los dos extremos en vez de elegir uno:

    - `desde_perdida`: p(ninguno) fijo; lo que sube el objetivo se lo saca al
      stop. Es el caso OPTIMISTA — la señal evita pérdidas además de acertar.
    - `desde_timeout`: p(stop) fijo; lo que sube el objetivo sale de los que no
      tocaban nada. Es el PESIMISTA — la señal sólo convierte indecisos.
    """
    p_none = max(0.0, 1.0 - p_obj - p_stop)
    K = p_obj + p_stop
    be_perdida = (friccion + N * K) / (P + N) if (P + N) > 0 else float("nan")
    be_timeout = (friccion + N * p_stop) / P if P > 0 else float("nan")
    return dict(desde_perdida=be_perdida, desde_timeout=be_timeout,
                p_ninguno=p_none,
                factible_perdida=bool(be_perdida <= K + 1e-12),
                factible_timeout=bool(be_timeout <= p_obj + p_none + 1e-12))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", default=os.path.join(REPO, "runs", "atlas_pnk",
                                                    "atlas_asimetrico.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "atlas_pnk",
                                                  "tabla_decision_pnk.json"))
    a = ap.parse_args(argv)

    d = json.load(open(a.atlas, encoding="utf-8"))
    tasas = d["agregado"]["tasas"]
    pordia = d.get("por_dia_tasas") or {}
    if not pordia:
        raise SystemExit("el atlas no guardo `por_dia_tasas`: sin eso no se "
                         "puede recalcular el IC estacionario sin re-correr")

    filas = []
    for clave, t in sorted(tasas.items()):
        _h, _p, _n = clave.split("_")
        H, P, N = int(_h[1:]), int(_p[1:]), int(_n[1:])
        pd_ = pordia.get(clave)
        if not pd_:
            continue
        est = _boot_tasa(pd_, estacionario=True)
        fij = _boot_tasa(pd_, estacionario=False)
        if not est or not fij:
            continue
        be = break_even(P, N, t["p_objetivo"], t["p_stop"])
        # corrimiento minimo detectable: superar el percentil 95 del nulo
        mde_est = est["p95"] - est["p"]
        mde_fij = fij["p95"] - fij["p"]
        lift_be = min(be["desde_perdida"], be["desde_timeout"]) / t["p_objetivo"] - 1
        mde_rel = mde_est / t["p_objetivo"]
        factible = bool(be["factible_perdida"] or be["factible_timeout"])
        # N EFECTIVO: 197 dias no son 197 observaciones independientes. Con
        # dependencia de b_opt dias, el numero de bloques verdaderamente
        # independientes es ~197/b_opt. Es el N que gobierna la potencia.
        n_ef = est["n_bloques"] / max(est["b"], 1)
        # INDETECTABLE: el corrimiento minimo que se distingue del azar es MAYOR
        # que el que haria falta para pagar la friccion. O sea que ni una
        # estrategia exactamente en break-even se podria confirmar: el estudio
        # no puede decir nada util sobre esta geometria.
        indetectable = bool(factible and mde_rel > lift_be)
        motivo = ("IMPOSIBLE (ni con p_obj=1)" if not factible else
                  "lift %.0f%% > %.0f%%" % (100 * lift_be, 100 * LIFT_IMPLAUSIBLE)
                  if lift_be > LIFT_IMPLAUSIBLE else
                  "INDETECTABLE en break-even" if indetectable else "")
        filas.append(dict(
            H=H, P=P, N=N, clave=clave,
            p_obj=t["p_objetivo"], p_stop=t["p_stop"], p_none=t["p_ninguno"],
            e_ticks=t["e_ticks"], neto=t["e_ticks"] - FRICCION_RT,
            friccion_sobre_P=FRICCION_RT / P,
            b_opt=est["b"], n_bloques=est["n_bloques"], n_efectivo=n_ef,
            ic90_estacionario=est["ic90"], ic90_fijo=fij["ic90"],
            mde_abs=mde_est, mde_rel=mde_rel,
            mde_rel_fijo=mde_fij / t["p_objetivo"],
            subestimacion_del_fijo=(mde_est / mde_fij) if mde_fij > 0 else float("nan"),
            be_desde_perdida=be["desde_perdida"], be_desde_timeout=be["desde_timeout"],
            be_factible=factible, lift_minimo_para_pagar=lift_be,
            indetectable=indetectable,
            descartada=bool(motivo), motivo_descarte=motivo))

    filas.sort(key=lambda r: r["mde_rel"])
    json.dump(dict(friccion_rt=FRICCION_RT, umbral_lift_implausible=LIFT_IMPLAUSIBLE,
                   n_dias=d.get("n_efectivo_dias"), config_hash=d.get("config_hash"),
                   filas=filas), open(a.out, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    print("TABLA DE DECISION P/N/K — %s anclas, %s dias-bloque, friccion %.4f ticks RT"
          % (d.get("n_anclas_bruto"), d.get("n_efectivo_dias"), FRICCION_RT))
    print("ordenada por DETECTABILIDAD (corrimiento minimo relativo, menor = mejor)")
    print()
    print("%-4s %-3s %-3s %8s %8s %7s %6s %6s %9s %9s %9s  %s"
          % ("H", "P", "N", "p_obj", "e_bruto", "fric/P", "b_opt", "N_ef",
             "MDE_rel", "lift_BE", "MDE_fijo", "veredicto"))
    for r in filas:
        print("%-4d %-3d %-3d %8.4f %8.3f %6.0f%% %6d %6.1f %8.1f%% %8.1f%% %8.1f%%  %s"
              % (r["H"], r["P"], r["N"], r["p_obj"], r["e_ticks"],
                 100 * r["friccion_sobre_P"], r["b_opt"], r["n_efectivo"],
                 100 * r["mde_rel"], 100 * r["lift_minimo_para_pagar"],
                 100 * r["mde_rel_fijo"],
                 ("DESCARTADA: " + r["motivo_descarte"]) if r["descartada"] else "viable"))
    vivas = [r for r in filas if not r["descartada"]]
    bs = sorted({r["b_opt"] for r in filas})
    print()
    print("b_opt por geometria: min=%d max=%d  (%s)" % (bs[0], bs[-1], bs))
    if bs[-1] > 2 * max(bs[0], 1):
        print("  OJO: b_opt varia mucho entre geometrias -> el N efectivo no es")
        print("  el mismo para todas y la comparacion de potencia no es directa.")
    print()
    print("VIABLES (pagables Y detectables): %d de %d" % (len(vivas), len(filas)))
    if not vivas:
        print()
        print("  INTERSECCION VACIA. Ninguna geometria de 6E en 30-120 min es a la")
        print("  vez pagable con friccion de %.4f ticks RT y detectable con el N" % FRICCION_RT)
        print("  efectivo disponible. Es un RESULTADO, no un fracaso: redirige a")
        print("  objetivos mayores (~27 ticks para que la friccion sea el 10%),")
        print("  horizontes mas largos, o a un instrumento con mejor relacion")
        print("  movimiento/costo. Gastar el turno de la hipotesis aca seria")
        print("  comprar un experimento que no puede responder que si.")
    print("salida: %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
