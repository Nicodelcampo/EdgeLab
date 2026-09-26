#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atlas nulo — grilla ASIMÉTRICA P/N y horizontes finos. **NULL / DESCRIPTIVO.**

## Qué agrega y por qué es la MISMA pregunta

El atlas de anoche midió sólo combinaciones **simétricas** (P = N = L) y
horizontes gruesos. Nico necesita elegir P/N/K con objetivos y stops
**distintos** —13/8, 12/10, …— y con horizontes finos entre 10 y 90 minutos.

Es una **extensión de la misma pregunta**, no una pregunta nueva: mismas anclas
placebo, misma dirección sorteada 50/50 antes de mirar el futuro, misma
separación mínima, mismos estratos, mismo bootstrap por bloques de día. Lo único
que cambia es la **grilla que se evalúa** sobre esas mismas trayectorias.

Se corre aparte y no toca la config congelada del atlas original: aquélla ya
cerró con su `CFG_HASH` y su resultado. Mezclarlas habría sido reescribir una
corrida terminada.

## Por qué un P/N asimétrico no se puede derivar de la tabla simétrica

Con P ≠ N la pregunta deja de ser "¿qué toca primero, +L o −L?" y pasa a ser
"¿toca +P antes que −N?", que depende de la **trayectoria**, no sólo de los
extremos. No hay forma de obtenerla de la tabla simétrica: hay que volver a
recorrer el camino de cada ancla. De ahí que esto sea una pasada nueva.

**PROHIBIDO**: cargar zonas reales, elegir P/N/K por rendimiento, tocar holdout.
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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))

import atlas_excursiones_nulas as A0   # noqa: E402  (anclas y utilidades)

# ---------------------------------------------------------------------------
# CONFIG CONGELADA de la extensión. Hereda todo lo metodológico de A0.
# ---------------------------------------------------------------------------
CFG = dict(
    seed=A0.CFG["seed"],                       # MISMAS anclas que el atlas base
    # GRILLA DE DECISION P/N/K (2026-07-27, tras retirar la propuesta 13/8).
    #
    # Se agregan simetricos suaves y, sobre todo, la asimetria INVERSA
    # (objetivo cerca / stop lejos): el test de razon de varianzas dio VR<1 en
    # los 7 horizontes -- reversion -- y bajo reversion esa es la geometria
    # favorecida. La grilla anterior tenia P>N en los seis pares, sin excepcion:
    # exploraba solo el lado que el proceso desfavorece.
    # GRILLA ANCHA (2026-07-27, tercera iteración). La tabla de decisión mostró
    # que el break-even depende del ANCHO TOTAL de las barreras y no de la
    # señal: marcada a mercado la esperanza nula es 0 en toda geometría, así
    # que hay que mover la tasa `delta = 2,704/(P+N)` puntos absolutos.
    #
    #   P+N = 21  ->  delta = 0,129   (lift 22% sobre una base de 0,57)
    #   P+N = 54  ->  delta = 0,050   (lift  9% sobre la misma base)
    #
    # Con barreras de 10-13 ticks la fricción se come el 21-34% del objetivo.
    # Esta grilla pregunta si la escala pagable está afuera de la que se venía
    # mirando. Sigue siendo NULO DESCRIPTIVO: no gasta hipótesis.
    # Se elige con --grilla. Las dos son CONFIGS CONGELADAS distintas y cada una
    # produce su propio CFG_HASH: no es un parametro que se pueda mover a gusto
    # durante una corrida, es cual de dos preguntas declaradas se contesta.
    **(dict(
        # ANCHA: si la escala pagable esta afuera de la grilla original. La tabla
        # de decision mostro que el break-even depende del ANCHO TOTAL de las
        # barreras y no de la senal -- delta = 2,704/(P+N). P+N=21 pide 12,9
        # puntos de tasa; P+N=54 pide 5,0.
        horizontes_min=[120, 180, 240, 360],
        pares_pn=[(20, 20), (27, 27), (34, 34),
                  (20, 27), (20, 34), (27, 34),
                  (27, 20), (34, 20), (34, 27),
                  (13, 21)],
        sep_min_minutos=360)
       if os.environ.get("ATLAS_GRILLA", "ancha") == "ancha" else
       dict(
        # PNK: la grilla de decision original, para rehacer la tabla sobre el
        # universo reconstruido.
        horizontes_min=[30, 60, 90, 120],
        pares_pn=[(5, 5), (8, 8), (10, 10),
                  (8, 10), (8, 13), (10, 13),
                  (10, 8), (12, 10), (13, 10), (13, 8)],
        sep_min_minutos=120)),
    grilla=os.environ.get("ATLAS_GRILLA", "ancha"),
    anclas_por_dia=A0.CFG["anclas_por_dia"],
    vol_lookback_min=A0.CFG["vol_lookback_min"],
    vol_cortes=A0.CFG["vol_cortes"],
    franjas_horarias=A0.CFG["franjas_horarias"],
    min_n_estrato=A0.CFG["min_n_estrato"],
    bootstrap_reps=A0.CFG["bootstrap_reps"],
    # Los MISMOS candados que el atlas base, heredados para que no puedan
    # divergir: este archivo tampoco filtraba el holdout ni el tipo de dia, y
    # habria consumido los 15 dias sellados igual que el base (ver nota 4 de
    # docs/holdout_access_log.md). Entran al CFG_HASH.
    holdout_desde=A0.CFG["holdout_desde"],
    tipos_de_dia=A0.CFG["tipos_de_dia"],
    conv_margen=0.005,        # convergencia sobre TASAS, no sobre ticks
    conv_rondas=3,
)
CFG_HASH = hashlib.sha256(json.dumps(CFG, sort_keys=True,
                                     default=str).encode()).hexdigest()[:16]

TICK_SIZE_DEFAULT = 5e-05      # 6E


def log(m, f=None):
    s = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), m)
    print(s, flush=True)
    if f:
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(s + "\n")


def procesar_dia(args):
    """Trayectorias de las anclas placebo de un día, evaluadas en la grilla P/N.

    Devuelve, por ancla y por (horizonte, par P/N), qué pasó primero.
    """
    archivo, contrato, fecha, data_dir, ronda = args
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

            fila = dict(vol_prev=vol_prev,
                        hora_ct=int(datetime.fromtimestamp(t0 / 1e9, tz=timezone.utc)
                                    .astimezone(CT).hour))
            for H in CFG["horizontes_min"]:
                e = np.searchsorted(ts, t0 + H * 60 * 10**9, side="right")
                fut = px[i + 1:e]
                if len(fut) == 0:
                    continue
                delta = (fut - p0) * direccion       # a favor = positivo, en TICKS
                fila["mfe_%d" % H] = int(delta.max())
                fila["mae_%d" % H] = int(delta.min())
                for (P, N) in CFG["pares_pn"]:
                    fav = np.flatnonzero(delta >= P)
                    adv = np.flatnonzero(delta <= -N)
                    f0 = int(fav[0]) if len(fav) else -1
                    a0 = int(adv[0]) if len(adv) else -1
                    if f0 < 0 and a0 < 0:
                        v = 0                        # ninguno dentro del horizonte
                    elif a0 < 0 or (f0 >= 0 and f0 < a0):
                        v = 1                        # objetivo primero
                    else:
                        v = -1                       # stop primero
                    fila["r_%d_%d_%d" % (H, P, N)] = v
            filas.append(fila)
        return dict(fecha=fecha, n=len(filas), filas=filas)
    except Exception as e:
        import traceback
        return dict(fecha=fecha, n=0, motivo="error: %s" % e,
                    traceback=traceback.format_exc()[-700:])


def agregar(filas):
    out = dict(n_anclas=len(filas), tasas={}, percentiles={})
    if not filas:
        return out
    for H in CFG["horizontes_min"]:
        m = np.array([f["mfe_%d" % H] for f in filas if ("mfe_%d" % H) in f])
        a = np.array([f["mae_%d" % H] for f in filas if ("mae_%d" % H) in f])
        if len(m):
            out["percentiles"]["H%d" % H] = dict(
                n=int(len(m)),
                mfe=[float(np.percentile(m, q)) for q in (10, 25, 50, 75, 90)],
                mae=[float(np.percentile(a, q)) for q in (10, 25, 50, 75, 90)])
        for (P, N) in CFG["pares_pn"]:
            key = "r_%d_%d_%d" % (H, P, N)
            v = np.array([f[key] for f in filas if key in f])
            if not len(v):
                continue
            gana = float((v == 1).mean())
            pierde = float((v == -1).mean())
            nada = float((v == 0).mean())
            # esperanza en ticks del par, ignorando el caso "ninguno" (se declara aparte)
            out["tasas"]["H%d_P%d_N%d" % (H, P, N)] = dict(
                n=int(len(v)), p_objetivo=gana, p_stop=pierde, p_ninguno=nada,
                # E[R] nulo del par: cuanto deja el azar por operacion, en ticks
                e_ticks=round(gana * P - pierde * N, 4))
    return out


def agregar_por_estrato(filas):
    if not filas:
        return {}
    vols = np.array([f["vol_prev"] for f in filas], dtype=float)
    q1, q2 = (float(np.quantile(vols, CFG["vol_cortes"][0])),
              float(np.quantile(vols, CFG["vol_cortes"][1])))

    def franja(h):
        for x, y in CFG["franjas_horarias"]:
            if x <= h < y or (x > y and (h >= x or h < y)):
                return "%02d-%02d" % (x, y)
        return "otra"

    g = {}
    for f in filas:
        reg = "vol_bajo" if f["vol_prev"] <= q1 else ("vol_medio" if f["vol_prev"] <= q2
                                                      else "vol_alto")
        g.setdefault("%s|%s" % (franja(f["hora_ct"]), reg), []).append(f)
    out = dict(cortes_vol=[q1, q2], estratos={}, ocultos={})
    for k, v in sorted(g.items()):
        if len(v) < CFG["min_n_estrato"]:
            out["ocultos"][k] = len(v)
        else:
            out["estratos"][k] = agregar(v)
    return out


def bootstrap_tasas(por_dia, key, reps=None):
    """IC de la tasa `key` remuestreando DÍAS. Las anclas del mismo día
    comparten régimen: remuestrearlas sueltas daría un IC falsamente angosto."""
    reps = reps or CFG["bootstrap_reps"]
    dias = [d for d, v in por_dia.items() if v]
    if len(dias) < 3:
        return None
    # PRE-AGREGADO POR DIA. El estadistico es una MEDIA de indicadores sobre las
    # filas agrupadas, o sea sum(aciertos)/sum(totales): alcanza con dos numeros
    # por dia y NO hace falta reconstruir las filas en cada replica.
    #
    # La version anterior concatenaba las ~658.000 filas en cada una de las 400
    # replicas, por cada una de las 42 combinaciones (H,P,N): unos 11.000
    # millones de operaciones de Python. Medido: un core al 100 % durante 14 min
    # sin terminar la primera combinacion; la corrida entera daba ~13 h.
    #
    # Esto es EXACTO, no una aproximacion: mismo estimador, misma seed y el mismo
    # patron de consumo del RNG (una llamada a `choice` por replica), asi que el
    # remuestreo de dias es identico al que habria hecho la version lenta.
    S = np.array([sum(1 for x in por_dia[d] if x.get(key) == 1) for d in dias], float)
    T = np.array([sum(1 for x in por_dia[d] if key in x) for d in dias], float)
    r = np.random.default_rng(CFG["seed"])
    vals = []
    for _ in range(reps):
        i = r.choice(len(dias), size=len(dias), replace=True)
        tot = T[i].sum()
        if tot:
            vals.append(float(S[i].sum() / tot))
    if not vals:
        return None
    return dict(media=float(np.mean(vals)),
                ic90=[float(np.percentile(vals, 5)), float(np.percentile(vals, 95))],
                n_bloques=len(dias))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", default=os.path.join(REPO, "runs", "censo",
                                                         "manifiesto_universo.json"))
    ap.add_argument("--data", default=os.path.join(REPO, "data", "nt8", "6E"))
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "atlas_asimetrico"))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--hard-stop", default="05:30")
    ap.add_argument("--solo-archivo", default=None,
                    help="restringe el manifiesto a un parquet (para ES/NQ)")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    LOG = os.path.join(a.out, "atlas_asim.log")
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS"):
        os.environ[v] = "1"

    import collections as _c
    # PUERTA UNICA — ver edgelab/research/universo_estudio.py y el incidente
    # del 2026-07-27. Este archivo tampoco filtraba: heredaba la regla de A0.
    from edgelab.research.universo_estudio import cargar_dias_de_estudio
    dias, info = cargar_dias_de_estudio(a.manifiesto,
                                        tipos_de_dia=CFG["tipos_de_dia"],
                                        caller="atlas_asimetrico")
    if a.solo_archivo:
        dias = [d for d in dias if d["archivo"] == a.solo_archivo]
    if info["descartados_holdout"]:
        log("  FIREWALL: %d dias del holdout descartados por la puerta"
            % info["descartados_holdout"], LOG)

    log("ATLAS ASIMETRICO — NULL/DESCRIPTIVO. %d dias EFECTIVOS %s, cfg=%s, workers=%d"
        % (len(dias), dict(_c.Counter(d["tipo_de_dia"] for d in dias)),
           CFG_HASH, a.workers), LOG)
    if not dias:
        log("  manifiesto vacio para el filtro dado", LOG)
        return 1

    hh, mm = (int(x) for x in a.hard_stop.split(":"))
    ahora = datetime.now()
    stop = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if stop <= ahora:
        stop += timedelta(days=1)
    log("  hard stop: %s" % stop.strftime("%Y-%m-%d %H:%M"), LOG)

    tareas = [(d["archivo"], d.get("contrato") or "?", d["fecha"], a.data) for d in dias]
    import multiprocessing as mp
    por_dia, rondas, hist = {}, [], []
    ronda = 0
    t0 = time.time()
    with mp.Pool(a.workers) as pool:
        while datetime.now() < stop:
            ronda += 1
            lote = [(f, c, fe, dd, ronda) for (f, c, fe, dd) in tareas]
            n_ok = 0
            for r in pool.imap_unordered(procesar_dia, lote, chunksize=1):
                if r.get("n"):
                    por_dia.setdefault(r["fecha"], []).extend(r["filas"])
                    n_ok += r["n"]
                if datetime.now() >= stop:
                    break
            todas = [f for v in por_dia.values() for f in v]
            agg = agregar(todas)
            rondas.append(dict(ronda=ronda, nuevas=n_ok, total=len(todas),
                               ts=datetime.now().isoformat()))
            tmp = os.path.join(a.out, "_ckpt.tmp")
            json.dump(dict(config=CFG, config_hash=CFG_HASH, rondas=rondas,
                           agregado=agg, n_dias=len(por_dia)),
                      open(tmp, "w", encoding="utf-8"), indent=1,
                      ensure_ascii=False, default=str)
            os.replace(tmp, os.path.join(a.out, "checkpoint.json"))

            # convergencia declarada ANTES: las tasas de objetivo se mueven poco
            firma = [agg["tasas"].get("H%d_P%d_N%d" % (H, P, N), {}).get("p_objetivo", 0)
                     for H in CFG["horizontes_min"] for (P, N) in CFG["pares_pn"]]
            hist.append(firma)
            conv = False
            if len(hist) > CFG["conv_rondas"]:
                u = np.array(hist[-(CFG["conv_rondas"] + 1):], dtype=float)
                conv = bool(np.max(np.abs(u - u[-1])) <= CFG["conv_margen"])
            log("ronda %d: +%d (total %d, %d dias)  converge=%s"
                % (ronda, n_ok, len(todas), len(por_dia), conv), LOG)

    todas = [f for v in por_dia.values() for f in v]
    boot = {}
    for H in CFG["horizontes_min"]:
        for (P, N) in CFG["pares_pn"]:
            k = "r_%d_%d_%d" % (H, P, N)
            boot["H%d_P%d_N%d" % (H, P, N)] = bootstrap_tasas(por_dia, k)
    salida = dict(
        etiqueta="NULL / DESCRIPTIVO — no es un edge; extension asimetrica del atlas",
        config=CFG, config_hash=CFG_HASH,
        n_anclas_bruto=len(todas), n_efectivo_dias=len(por_dia),
        nota_n="el N efectivo son los DIAS: las anclas del mismo dia comparten regimen",
        rondas=rondas, agregado=agregar(todas),
        por_estrato=agregar_por_estrato(todas), bootstrap=boot,
        # (aciertos, total) POR DIA para cada combinación. Sin esto, el IC sólo
        # se puede recalcular re-corriendo todo: la salida guardaba el agregado
        # y las filas crudas morían con el proceso.
        #
        # Hace falta porque el bootstrap de bloque FIJO de 1 día subestima la
        # incertidumbre — medido sobre la serie diaria real: b_opt de
        # Politis-White da 13-18 días y el intervalo correcto es un 120-143%
        # más ancho. Con estos dos números por día, el IC estacionario se
        # recalcula sin volver a tocar los datos.
        por_dia_tasas={
            "H%d_P%d_N%d" % (H, P, N): {
                d: [int(sum(1 for x in v if x.get("r_%d_%d_%d" % (H, P, N)) == 1)),
                    int(sum(1 for x in v if ("r_%d_%d_%d" % (H, P, N)) in x))]
                for d, v in por_dia.items()}
            for H in CFG["horizontes_min"] for (P, N) in CFG["pares_pn"]},
        segundos=round(time.time() - t0, 1),
        generado_utc=datetime.now(timezone.utc).isoformat())
    json.dump(salida, open(os.path.join(a.out, "atlas_asimetrico.json"), "w",
                           encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    log("FIN: %d anclas sobre %d dias en %d rondas" % (len(todas), len(por_dia),
                                                       len(rondas)), LOG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
