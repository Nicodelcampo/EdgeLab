# -*- coding: utf-8 -*-
"""SPIKE-IN end-to-end sobre el atlas de excursiones nulas.

Implementa la especificación de `docs/spike_in_enmiendas_2026-08-01.md`
(commit 17d47a6). Inyecta señal sintética de magnitud conocida en el punto
declarado -- `tools/atlas_asimetrico.py::procesar_dia`, sobre `delta` -- y mide
desde qué tamaño el pipeline la recupera.

NO modifica código de producción. Replica `procesar_dia` línea por línea y le
agrega la inyección, igual que `x4_sensibilidad.py` hizo con
`simular_funcionales`. El control de la Unidad 1 compara MI camino contra el
camino REAL importado del módulo de producción, ancla por ancla.

Alcance declarado: el atlas usa anclas PLACEBO (instantes aleatorios). Esto
valida la agregación y la potencia del test, NO el kernel de detección de
zonas.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

REPO = "E:/EdgeLab"
# La grilla DEBE fijarse antes de importar: define horizontes y pares P/N, y
# entra al CFG_HASH. El atlas sellado (config_hash 3c5e32e2785fc9cd) es "pnk".
os.environ["ATLAS_GRILLA"] = "pnk"
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, REPO)

import atlas_asimetrico as A            # noqa: E402  (código de PRODUCCIÓN)
import atlas_excursiones_nulas as A0    # noqa: E402

CFG = A.CFG
ATLAS_SELLADO = os.path.join(REPO, "runs/atlas_pnk/atlas_asimetrico.json")
DATA_DIR = os.path.join(REPO, "data/nt8/6E")


# ---------------------------------------------------------------- inyección
def _senal_ticks(ts_fut, t0, H, m, signo, forma="rampa"):
    """señal(Δt), discretizada a TICKS ENTEROS con np.trunc.

    forma="rampa"   -> m·(Δt/H). La forma REALISTA y la que usa la grilla:
                       una deriva direccional que se acumula con el tiempo.
    forma="escalon" -> m constante desde el primer tick posterior al ancla.
                       SÓLO para el control de forzado (1B). Ver la nota de
                       `unidad1_control.py`: con una rampa no existe ningún m
                       finito que fuerce el resultado, porque en Δt→0 la señal
                       vale 0 y una caída adversa temprana dispara el stop
                       antes de que la rampa entregue nada. El escalón sí tiene
                       magnitud de forzado bien definida, y ejercita el MISMO
                       camino de inyección.

    `np.trunc` y no `floor`/`round`: es la única simétrica respecto de cero.
    Con `floor`, una señal de -0,5 ticks iría a -1 y una de +0,5 a 0, metiendo
    un sesgo direccional espurio en el experimento que existe para medir
    dirección (importa en la variante B, donde el signo se sortea).

    Devuelve SIEMPRE int64, incluso con m=0, para que `delta` no se promueva a
    float64 y las comparaciones de barrera sigan siendo enteras.
    """
    if forma == "escalon":
        return np.trunc(np.full(len(ts_fut), signo * m, dtype=np.float64)).astype(np.int64)
    frac = (ts_fut - t0) / float(H * 60 * 10**9)      # ∈ (0, 1]
    return np.trunc(signo * m * frac).astype(np.int64)


def procesar_dia_spike(args):
    """`atlas_asimetrico.procesar_dia` + inyección. Mismo flujo, mismo RNG.

    args: (archivo, contrato, fecha, data_dir, ronda, m, variante)
    """
    archivo, contrato, fecha, data_dir, ronda, m, variante = args[:7]
    forma = args[7] if len(args) > 7 else "rampa"
    try:
        import duckdb
        from zoneinfo import ZoneInfo
        CT = ZoneInfo("America/Chicago")

        p = os.path.join(data_dir, archivo).replace("\\", "/")
        d0 = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=CT)
        a = int(d0.timestamp() * 1e9)
        b = int((d0 + timedelta(days=1)).timestamp() * 1e9)
        con = duckdb.connect()
        df = con.execute(
            "select ts_utc_ns, price_ticks from read_parquet('%s') "
            "where ts_utc_ns>=%d and ts_utc_ns<%d order by ts_utc_ns" % (p, a, b)).df()
        if len(df) < 5000:
            return dict(fecha=fecha, n=0, motivo="pocos_ticks")
        ts = df.ts_utc_ns.values.astype(np.int64)
        px = df.price_ticks.values.astype(np.int64)
        del df

        hmax = max(CFG["horizontes_min"])
        sep_ns = CFG["sep_min_minutos"] * 60 * 10**9
        vol_ns = CFG["vol_lookback_min"] * 60 * 10**9

        r = A0._rng(CFG["seed"], contrato, fecha, "anclas", ronda)
        t_lo = int(ts[0]) + vol_ns
        t_hi = int(ts[-1]) - hmax * 60 * 10**9
        if t_hi <= t_lo:
            return dict(fecha=fecha, n=0, motivo="dia_corto")
        cand = np.sort(r.integers(t_lo, t_hi, size=CFG["anclas_por_dia"] * 4))
        anclas, ultimo = [], None
        for t in cand:
            t = int(t)
            if ultimo is None or t - ultimo >= sep_ns:
                anclas.append(t); ultimo = t
            if len(anclas) >= CFG["anclas_por_dia"]:
                break
        if not anclas:
            return dict(fecha=fecha, n=0, motivo="sin_anclas")

        idx = np.searchsorted(ts, anclas, side="right") - 1
        filas = []
        for k, i in enumerate(idx):
            if i < 1:
                continue
            t0, p0 = int(ts[i]), int(px[i])
            j = np.searchsorted(ts, t0 - vol_ns, side="left")
            if i - j < 50:
                continue
            prev = px[j:i + 1]
            vol_prev = float(np.std(np.diff(prev.astype(np.float64)))) if len(prev) > 2 else 0.0
            rd = A0._rng(CFG["seed"], contrato, fecha, ronda, k)
            direccion = 1 if rd.integers(0, 2) == 0 else -1

            # ---- SIGNO DE LA SEÑAL ----------------------------------------
            # A: alineado con `direccion` (delta ya viene orientada) -> mide
            #    MAGNITUD con el signo regalado.
            # B: sorteado por ancla, de un stream PROPIO. El sufijo
            #    "spike_signo" hace que el hash de `_rng` sea distinto del de
            #    `direccion`; si se reusara aquel stream, s_k y direccion
            #    quedarían correlacionados y B degeneraría en A sin avisar.
            if variante == "B":
                rs = A0._rng(CFG["seed"], contrato, fecha, ronda, k, "spike_signo")
                signo = 1 if rs.integers(0, 2) == 0 else -1
            else:
                signo = 1

            fila = dict(vol_prev=vol_prev, signo_spike=int(signo),
                        direccion=int(direccion),
                        hora_ct=int(datetime.fromtimestamp(t0 / 1e9, tz=timezone.utc)
                                    .astimezone(CT).hour))
            for H in CFG["horizontes_min"]:
                e = np.searchsorted(ts, t0 + H * 60 * 10**9, side="right")
                fut = px[i + 1:e]
                if len(fut) == 0:
                    continue
                # ---- PUNTO DE INYECCIÓN (atlas_asimetrico.py:189) ----------
                # Se ejecuta SIEMPRE, para todo m incluido 0. Con m=0 `senal`
                # es un array de ceros int64 y `delta` conserva dtype y valor
                # exactos => bit a bit igual al nulo, habiendo recorrido el
                # mismo camino de código.
                senal = _senal_ticks(ts[i + 1:e], t0, H, m, signo, forma)
                delta = (fut - p0) * direccion + senal
                fila["mfe_%d" % H] = int(delta.max())
                fila["mae_%d" % H] = int(delta.min())
                for (P, N) in CFG["pares_pn"]:
                    fav = np.flatnonzero(delta >= P)
                    adv = np.flatnonzero(delta <= -N)
                    f0 = int(fav[0]) if len(fav) else -1
                    a0 = int(adv[0]) if len(adv) else -1
                    if f0 < 0 and a0 < 0:
                        v = 0
                    elif a0 < 0 or (f0 >= 0 and f0 < a0):
                        v = 1
                    else:
                        v = -1
                    fila["r_%d_%d_%d" % (H, P, N)] = v
            filas.append(fila)
        return dict(fecha=fecha, n=len(filas), filas=filas)
    except Exception as e:
        import traceback
        return dict(fecha=fecha, n=0, motivo="error: %s" % e,
                    traceback=traceback.format_exc()[-700:])


# ------------------------------------------------------------------ utilidades
def dias_del_atlas_sellado():
    """Las 188 fechas exactas del atlas sellado, con su archivo/contrato."""
    A_ = json.load(open(ATLAS_SELLADO, encoding="utf-8"))
    fechas = sorted(A_["por_dia_tasas"][sorted(A_["por_dia_tasas"])[0]])
    man = json.load(open(os.path.join(REPO, "runs/censo/manifiesto_universo.json"),
                         encoding="utf-8"))
    por_fecha = {}
    for d in man["dias"]:
        por_fecha.setdefault(d["fecha"], d)
    salida = []
    for f in fechas:
        d = por_fecha.get(f)
        if d:
            salida.append((d["archivo"], d["contrato"], f))
    return salida, fechas


def geometrias():
    return ["H%d_P%d_N%d" % (H, P, N)
            for H in CFG["horizontes_min"] for (P, N) in CFG["pares_pn"]]


def tasas_por_dia(resultados):
    """S/T por geometría y fecha. S = # de 'objetivo primero', T = # eventos
    resueltos (excluye v=0, que es 'ninguno dentro del horizonte')."""
    out = {}
    for res in resultados:
        if res["n"] == 0:
            continue
        for H in CFG["horizontes_min"]:
            for (P, N) in CFG["pares_pn"]:
                g = "H%d_P%d_N%d" % (H, P, N)
                key = "r_%d_%d_%d" % (H, P, N)
                S = T = 0
                for fila in res["filas"]:
                    v = fila.get(key)
                    if v is None or v == 0:
                        continue
                    T += 1
                    if v == 1:
                        S += 1
                out.setdefault(g, {}).setdefault(res["fecha"], [0, 0])
                out[g][res["fecha"]][0] += S
                out[g][res["fecha"]][1] += T
    return out
