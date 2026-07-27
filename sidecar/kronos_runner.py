#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arnés a prueba de crashes para el paso 2 de Kronos.

## Por qué hace falta

`kronos_paso2.py` funciona con pocas muestras y **muere** con muchas, siempre en
el mismo lugar: `Fatal Python error: PyEval_SaveThread` dentro de la atención del
modelo. Se descartaron dos causas midiendo — no es la cantidad de hilos (falla
igual con 1) ni la versión de torch (2.13 y 2.5.1 fallan idéntico). Lo que sí
cambia el resultado es **qué contextos** toca: con `n=2` pasa, con `n=120` muere.
O sea que hay ventanas concretas que revientan el modelo.

Es un error **fatal**, no una excepción: `try/except` no lo atrapa, se lleva el
proceso entero. La única forma de que una ventana mala no cueste toda la corrida
es que cada lote viva en su **propio proceso**.

Este arnés lanza hijos de `--lote` muestras, cada uno escribiendo sus filas a un
JSONL compartido. Si un hijo muere, se pierde su lote y se sigue con el
siguiente. Al final el padre agrega y calcula la correlación.

**No cambia nada de la metodología**: mismos puntos de muestreo (misma seed),
mismo baseline, mismo criterio de refutación. Sólo cambia quién ejecuta qué.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
PY = os.path.join(AQUI, "kronos_env", "Scripts", "python.exe")


def log(m):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), m), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=120)
    ap.add_argument("--lote", type=int, default=5)
    ap.add_argument("--lookback", type=int, default=128)
    ap.add_argument("--paths", type=int, default=30)
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "kronos"))
    ap.add_argument("--minutos-max", type=int, default=100)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    jsonl = os.path.join(a.out, "filas.jsonl")
    open(jsonl, "w").close()

    env = dict(os.environ, KRONOS_LOOKBACK=str(a.lookback),
               KRONOS_PATHS=str(a.paths), KRONOS_JSONL=jsonl)
    t0 = datetime.now()
    hechos = muertos = 0
    for off in range(0, a.total, a.lote):
        if (datetime.now() - t0).total_seconds() / 60 > a.minutos_max:
            log("presupuesto agotado en offset %d" % off)
            break
        env["KRONOS_OFFSET"] = str(off)
        env["KRONOS_N"] = str(a.lote)
        r = subprocess.run([PY, "-u", os.path.join(AQUI, "kronos_paso2.py"),
                            "--n-muestras", str(a.total), "--threads", "2",
                            "--minutos-max", "20", "--solo-lote"],
                           cwd=AQUI, env=env, capture_output=True, text=True,
                           timeout=1800)
        n = sum(1 for _ in open(jsonl, encoding="utf-8"))
        if r.returncode != 0:
            muertos += 1
            log("lote %d-%d MURIO (rc=%s) — se sigue; acumuladas %d filas"
                % (off, off + a.lote, r.returncode, n))
        else:
            log("lote %d-%d ok — acumuladas %d filas" % (off, off + a.lote, n))
        hechos += 1

    filas = [json.loads(l) for l in open(jsonl, encoding="utf-8") if l.strip()]
    log("lotes: %d (%d murieron) — filas utiles: %d" % (hechos, muertos, len(filas)))
    if len(filas) < 30:
        json.dump(dict(estado="SKIP", n=len(filas), lotes=hechos, lotes_muertos=muertos,
                       motivo="menos de 30 muestras utiles"),
                  open(os.path.join(a.out, "kronos_paso2.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        return 2

    sp = np.array([f["sigma_pred"] for f in filas])
    vr = np.array([f["vol_rezagada"] for f in filas])
    ar = np.array([f["atr_rezagado"] for f in filas])

    def corr(x, y):
        if np.std(x) == 0 or np.std(y) == 0:
            return float("nan")
        return float(np.corrcoef(x, y)[0, 1])

    def spearman(x, y):
        return corr(np.argsort(np.argsort(x)).astype(float),
                    np.argsort(np.argsort(y)).astype(float))

    c = corr(sp, vr)
    res = dict(
        etiqueta="TARGET-FREE — R5 del pre-registro CAMP-002; no evalua P&L",
        modelo="Kronos-small", n_muestras=len(filas),
        lookback=a.lookback, n_paths=a.paths, bar_min=5, pred_len=12,
        lotes=hechos, lotes_muertos=muertos,
        desviacion_declarada=("lookback 128 en vez de los 400 recomendados: con "
                              "400 el modelo crashea en CPU (PyEval_SaveThread). "
                              "Se verifico que 320 y 256 tambien crashean con 30 "
                              "caminos; 128 es el mayor que sostiene el muestreo "
                              "Monte Carlo completo."),
        corr_pearson_vs_vol_rezagada=c,
        corr_spearman_vs_vol_rezagada=spearman(sp, vr),
        corr_pearson_vs_atr_rezagado=corr(sp, ar),
        umbral_refutacion=0.95,
        veredicto=("CIERRA_LA_LINEA: sigma_pred no se distingue de la vol trivial "
                   "rezagada" if (c == c and abs(c) > 0.95) else
                   "SOBREVIVE_R5: sigma_pred aporta variacion propia; queda "
                   "pendiente si esa variacion PAGA (baseline trivial, paso b)"),
        generado_utc=datetime.now(timezone.utc).isoformat())
    json.dump(res, open(os.path.join(a.out, "kronos_paso2.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    log("n=%d  corr(sigma_pred, vol_rezagada)=%.4f  spearman=%.4f  atr=%.4f"
        % (len(filas), c, res["corr_spearman_vs_vol_rezagada"],
           res["corr_pearson_vs_atr_rezagado"]))
    log(res["veredicto"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
