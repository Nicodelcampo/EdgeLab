#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KRONOS — PASO 2 de CAMP-002. **TARGET-FREE. No evalua P&L.**

## La pregunta, y por que es la mas barata de toda la campana

R5 del pre-registro: **¿`sigma_pred` de Kronos es distinta de una volatilidad
realizada rezagada trivial?**

Si la correlacion supera 0,95, Kronos no aporta nada sobre `std(returns)` de la
ventana previa — y entonces no hay nada que discutir: no hace falta un
transformer de 102M de parametros, ni 2,5 GB de dependencias, ni un entorno
sidecar. La linea se cierra por una hora de computo.

**No toca P&L**, asi que no cae bajo el STOP. Tampoco toca zonas reales: los
puntos de muestreo son instantes reproducibles sobre dias APTOS, la misma
disciplina del atlas nulo.

## Aislamiento

Corre en el venv sidecar (`sidecar/kronos_env`), fuera del lock principal. El
repo principal nunca importa torch: lee el JSON de salida y nada mas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(AQUI, "Kronos"))

CT = "America/Chicago"
SEED = 20260727
BAR_MIN = 5            # resolucion de las velas que ve el modelo
LOOKBACK = int(__import__('os').environ.get('KRONOS_LOOKBACK', 400))         # recomendado por los autores; entra en el contexto de 512
PRED_LEN = 12          # 1 hora hacia adelante con velas de 5 min
N_PATHS = int(__import__('os').environ.get('KRONOS_PATHS', 30))           # muestreo Monte Carlo de la demo oficial
VOL_LOOKBACK = 60      # barras para la vol realizada rezagada (baseline trivial)


def log(m):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), m), flush=True)


def cargar_barras(archivo, fechas, bar_min=BAR_MIN):
    """Velas de `bar_min` minutos sobre los dias APTOS indicados."""
    import duckdb
    p = os.path.join(REPO, "data", "nt8", "6E", archivo).replace("\\", "/")
    con = duckdb.connect()
    df = con.execute(
        "select ts_utc_ns, price_ticks, volume from read_parquet('%s') "
        "order by ts_utc_ns" % p).df()
    idx = pd.to_datetime(df.ts_utc_ns.values, unit="ns", utc=True).tz_convert(CT)
    df["fecha"] = idx.strftime("%Y-%m-%d")
    df = df[df.fecha.isin(fechas)]
    if df.empty:
        return None
    idx = pd.to_datetime(df.ts_utc_ns.values, unit="ns", utc=True).tz_convert(CT)
    g = pd.DataFrame({"px": df.price_ticks.values, "vol": df.volume.values},
                     index=idx).resample("%dmin" % bar_min)
    k = pd.DataFrame({
        "open": g.px.first(), "high": g.px.max(), "low": g.px.min(),
        "close": g.px.last(), "volume": g.vol.sum()}).dropna()
    k["amount"] = k.close * k.volume
    return k


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", default=os.path.join(REPO, "runs", "censo",
                                                         "manifiesto_universo.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "kronos"))
    ap.add_argument("--n-muestras", type=int, default=200)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--minutos-max", type=int, default=120)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    import torch
    torch.set_num_threads(a.threads)      # no competir con los workers del atlas
    log("torch %s  threads=%d  cuda=%s" % (torch.__version__, a.threads,
                                           torch.cuda.is_available()))

    man = json.load(open(a.manifiesto, encoding="utf-8"))
    por_arch = {}
    for d in man["dias"]:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    # se usa el contrato con mas dias aptos: mas muestras de la MISMA pregunta
    archivo = max(por_arch, key=lambda k: len(por_arch[k]))
    fechas = set(por_arch[archivo])
    log("universo: %s con %d dias aptos" % (archivo, len(fechas)))

    k = cargar_barras(archivo, fechas)
    if k is None or len(k) < LOOKBACK + VOL_LOOKBACK + PRED_LEN + 10:
        log("SKIP: barras insuficientes")
        return 2
    log("velas de %d min: %d" % (BAR_MIN, len(k)))

    from model import Kronos, KronosTokenizer, KronosPredictor
    tk = KronosTokenizer.from_pretrained(os.path.join(AQUI, "pesos", "Kronos-Tokenizer-base"))
    mdl = Kronos.from_pretrained(os.path.join(AQUI, "pesos", "Kronos-small"))
    pred = KronosPredictor(mdl, tk, device="cpu", max_context=512)
    log("modelo cargado")

    rng = np.random.default_rng(SEED)
    lo = LOOKBACK + VOL_LOOKBACK
    hi = len(k) - PRED_LEN - 1
    puntos = sorted(rng.choice(np.arange(lo, hi), size=min(a.n_muestras, hi - lo),
                               replace=False))

    filas, t0 = [], time.time()
    for n, i in enumerate(puntos):
        if (time.time() - t0) / 60.0 > a.minutos_max:
            log("presupuesto de tiempo agotado en la muestra %d" % n)
            break
        ctx = k.iloc[i - LOOKBACK:i]
        xts = pd.Series(ctx.index)
        yts = pd.Series(pd.date_range(ctx.index[-1], periods=PRED_LEN + 1,
                                      freq="%dmin" % BAR_MIN, tz=ctx.index.tz)[1:])
        try:
            out = pred.predict(df=ctx[["open", "high", "low", "close", "volume", "amount"]],
                               x_timestamp=xts, y_timestamp=yts, pred_len=PRED_LEN,
                               T=1.0, top_p=0.9, sample_count=N_PATHS, verbose=False)
        except Exception as e:
            log("muestra %d fallo: %s" % (n, e))
            continue
        c = out["close"].to_numpy(dtype=float)
        r = np.diff(c) / c[:-1]
        sigma_pred = float(np.std(r)) if len(r) > 1 else 0.0

        # BASELINE TRIVIAL: volatilidad realizada REZAGADA (sin mirar el futuro)
        prev = k["close"].to_numpy(dtype=float)[i - VOL_LOOKBACK:i]
        rp = np.diff(prev) / prev[:-1]
        vol_rez = float(np.std(rp))
        # ATR rezagado, la otra forma trivial
        hh = k["high"].to_numpy(dtype=float)[i - VOL_LOOKBACK:i]
        ll = k["low"].to_numpy(dtype=float)[i - VOL_LOOKBACK:i]
        atr_rez = float(np.mean(hh - ll) / prev[-1])

        filas.append(dict(i=int(i), ts=str(k.index[i]), sigma_pred=sigma_pred,
                          vol_rezagada=vol_rez, atr_rezagado=atr_rez))
        if (n + 1) % 20 == 0:
            log("  %d muestras  (%.1f s/muestra)" % (n + 1, (time.time() - t0) / (n + 1)))

    if len(filas) < 30:
        log("SKIP: solo %d muestras utiles" % len(filas))
        json.dump(dict(estado="SKIP", n=len(filas)),
                  open(os.path.join(a.out, "kronos_paso2.json"), "w", encoding="utf-8"),
                  indent=1)
        return 2

    sp = np.array([f["sigma_pred"] for f in filas])
    vr = np.array([f["vol_rezagada"] for f in filas])
    ar = np.array([f["atr_rezagado"] for f in filas])

    def corr(x, y):
        if np.std(x) == 0 or np.std(y) == 0:
            return float("nan")
        return float(np.corrcoef(x, y)[0, 1])

    def spearman(x, y):
        rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
        return corr(rx.astype(float), ry.astype(float))

    res = dict(
        etiqueta="TARGET-FREE — no evalua P&L; R5 del pre-registro CAMP-002",
        modelo="Kronos-small", n_muestras=len(filas), bar_min=BAR_MIN,
        lookback=LOOKBACK, pred_len=PRED_LEN, n_paths=N_PATHS, seed=SEED,
        archivo=archivo, n_dias_aptos=len(fechas),
        segundos=round(time.time() - t0, 1),
        corr_pearson_vs_vol_rezagada=corr(sp, vr),
        corr_spearman_vs_vol_rezagada=spearman(sp, vr),
        corr_pearson_vs_atr_rezagado=corr(sp, ar),
        umbral_refutacion=0.95,
        generado_utc=datetime.now(timezone.utc).isoformat(),
        filas=filas[:50])
    c = res["corr_pearson_vs_vol_rezagada"]
    res["veredicto"] = ("CIERRA_LA_LINEA: sigma_pred no se distingue de la vol "
                        "trivial rezagada" if (c == c and abs(c) > 0.95)
                        else "SOBREVIVE_R5: sigma_pred aporta variacion propia; "
                             "queda pendiente si esa variacion PAGA (baseline "
                             "trivial en el paso b)")
    json.dump(res, open(os.path.join(a.out, "kronos_paso2.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    log("n=%d  corr(sigma_pred, vol_rezagada)=%.4f  spearman=%.4f  atr=%.4f"
        % (len(filas), res["corr_pearson_vs_vol_rezagada"],
           res["corr_spearman_vs_vol_rezagada"],
           res["corr_pearson_vs_atr_rezagado"]))
    log(res["veredicto"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
