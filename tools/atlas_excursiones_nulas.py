#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATLAS DE EXCURSIONES NULAS — **NULL / DESCRIPTIVO. NO ES UN EDGE.**

## Qué es y qué NO es

Mide qué le pasa al precio después de un instante **elegido al azar**. Nada más.
No hay indicador, no hay zona, no hay señal: son **anclas placebo**.

Sirve para una sola cosa: que mañana se puedan elegir P (objetivo), N (stop) y
K (horizonte) sabiendo **qué ocurre por puro azar** con esa combinación. Sin este
piso, cualquier "el 62 % de las zonas reaccionó" es un número sin denominador —
si el azar da 61 %, la zona no aporta nada, y hoy no hay forma de saberlo.

**PROHIBIDO** (y el código lo respeta por construcción: nunca importa un módulo
de indicador ni lee el store):
- cargar o consultar zonas o resultados de indicadores reales;
- elegir P/N/K por rendimiento de zonas;
- optimizar estrategias; tocar el holdout; presentar esto como edge.

## Decisiones metodológicas, todas tomadas ANTES de correr

**Dirección 50/50 por seed, asignada antes de mirar el futuro.** Si se eligiera
"la dirección que después funcionó", el nulo dejaría de ser nulo. El sorteo es
reproducible desde `(seed, instrumento, fecha, índice del ancla)`.

**Solapamiento controlado y declarado.** Dos anclas separadas por menos que el
horizonte comparten futuro: no son observaciones independientes. Se impone una
separación mínima **igual al horizonte máximo**, y aun así el N efectivo se
estima por bootstrap de bloques por día — nunca se venden las anclas como
independientes.

**Estratos a priori**, con **información sólo hasta el ancla**: instrumento ×
franja horaria de sesión × régimen de volatilidad **rezagado** (la vol realizada
de la ventana previa al ancla, jamás la posterior).

**Precio de referencia en ticks enteros.** Toda la excursión se mide en ticks;
no se degrada a float. Misma disciplina que el resto del proyecto.

**Congelado metodológico**: una vez lanzado, la config no cambia por resultados
parciales. Si un error mecánico obliga a relanzar, se relanza con la MISMA config
o el cambio se documenta como corrección de bug, no de metodología.

Uso:
  .venv/Scripts/python tools/atlas_excursiones_nulas.py \
      --manifiesto runs/censo/manifiesto_universo.json --out runs/atlas \
      --workers 5 --hard-stop "07:10"
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

# ---------------------------------------------------------------------------
# CONFIG CONGELADA. No se toca durante la corrida.
# ---------------------------------------------------------------------------
CFG = dict(
    seed=20260727,
    # horizontes en MINUTOS de reloj (no barras: el atlas es agnóstico de bar_spec)
    horizontes_min=[5, 15, 30, 60, 120],
    # grilla de objetivos y stops en TICKS, escala geométrica (no optimizada:
    # cubre de "ruido de spread" a "movimiento de sesión")
    grilla_ticks=[2, 3, 5, 8, 13, 21, 34],
    anclas_por_dia=120,               # antes de aplicar la separación mínima
    # separación mínima = horizonte máximo, para que dos anclas no compartan futuro
    sep_min_minutos=120,
    # régimen de vol: se mide sobre la ventana PREVIA al ancla, nunca la posterior
    vol_lookback_min=60,
    vol_cortes=[0.33, 0.66],          # terciles → bajo / medio / alto
    franjas_horarias=[(17, 24), (0, 7), (7, 12), (12, 16)],   # hora CT
    min_n_estrato=200,                # por debajo, el estrato se oculta
    bootstrap_reps=400,
    # ── FIREWALL DEL HOLDOUT, EN LA CONFIG CONGELADA ────────────────────────
    # Estaba SOLO en el docstring, y la corrida del 2026-07-27 uso 10 dias del
    # holdout (2026-07-06 .. 07-21) entre sus 163. El atlas mide MFE/MAE sobre
    # horizontes futuros: eso es RETORNO, no es target-free, y la regla sellada
    # dice que ningun placebo pisa el holdout. Ahora es un candado de codigo.
    holdout_desde="2026-07-01",
    # ── ALCANCE POR TIPO DE DIA (decision 2026-07-27) ───────────────────────
    # Entra lunes-a-viernes. Se EXCLUYE el domingo (APERTURA_SEMANAL): son 7 h
    # de sesion contra 23, con 7.544 ticks de mediana contra 62.857-77.775 --
    # entre 8 y 10 veces mas fino. Dos razones, y las dos son estructurales:
    #   1. el bootstrap resamplea POR DIA como bloque, y un fragmento de 7 h no
    #      es intercambiable con un dia de 23 h: subestimaria la varianza;
    #      pero (2) tiene un ancla: el spread y el slippage de una sesion tan
    #   2. fina son otro regimen de EJECUCION (jerarquia #4 del referente), asi
    #      que mezclarlo en la franja (17,24) haria un nulo de dos regimenes.
    # Es una DECISION DECLARADA, no una exclusion accidental como la de los
    # viernes que esto mismo vino a corregir. Entra al hash de la config, y el
    # arnes de EXPLORE debe NEGARSE a evaluar una zona cuyo tipo de dia no este
    # en este alcance -- si aparecen zonas de domingo, que falle ruidoso en vez
    # de compararlas contra el nulo equivocado.
    tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"],
    # convergencia declarada ANTES: los percentiles centrales de MFE deben
    # moverse menos que este margen (en ticks) durante N rondas seguidas
    conv_margen_ticks=0.25,
    conv_rondas=3,
)
CFG_HASH = hashlib.sha256(json.dumps(CFG, sort_keys=True).encode()).hexdigest()[:16]


def _log(msg, f=None):
    s = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    print(s, flush=True)
    if f:
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(s + "\n")


def _rng(*partes):
    """PRNG reproducible desde una tupla de identidad. Sin estado global."""
    h = hashlib.sha256(("|".join(str(p) for p in partes)).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


# ---------------------------------------------------------------------------
# Unidad de trabajo: un instrumento-día
# ---------------------------------------------------------------------------
def procesar_dia(args):
    """Devuelve las excursiones de las anclas placebo de UN día.

    Se ejecuta en un worker. Carga sólo su día: la RAM por worker queda acotada.
    """
    archivo, contrato, fecha, data_dir, ronda = args
    try:
        import duckdb
        import pandas as pd
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
            return dict(fecha=fecha, contrato=contrato, n=0, motivo="pocos_ticks")

        ts = df.ts_utc_ns.values.astype(np.int64)
        px = df.price_ticks.values.astype(np.int64)   # ENTEROS de tick, sin float
        del df

        hmax = max(CFG["horizontes_min"])
        sep_ns = CFG["sep_min_minutos"] * 60 * 10**9
        vol_ns = CFG["vol_lookback_min"] * 60 * 10**9

        # --- anclas placebo: uniformes en el tiempo, con separación mínima
        # la RONDA entra en la seed: cada ronda sortea anclas placebo nuevas.
        # Sin esto todas las rondas repetirian exactamente las mismas anclas y
        # acumular rondas no agregaria un solo dato. Es mas N de la MISMA
        # pregunta -- misma metodologia, otro sorteo -- nunca una pregunta nueva.
        r = _rng(CFG["seed"], contrato, fecha, "anclas", ronda)
        t_lo = ts[0] + vol_ns                       # deja lugar para la vol rezagada
        t_hi = ts[-1] - hmax * 60 * 10**9           # y para el horizonte completo
        if t_hi <= t_lo:
            return dict(fecha=fecha, contrato=contrato, n=0, motivo="dia_corto")
        cand = np.sort(r.integers(t_lo, t_hi, size=CFG["anclas_por_dia"] * 4))
        anclas = []
        ultimo = None                       # centinela: None, no un entero gigante.
        for t in cand:                      # -10**19 desborda int64 al restarlo de un
            t = int(t)                      # np.int64 y tumbaba el dia entero.
            if ultimo is None or t - ultimo >= sep_ns:
                anclas.append(t); ultimo = t
            if len(anclas) >= CFG["anclas_por_dia"]:
                break
        if not anclas:
            return dict(fecha=fecha, contrato=contrato, n=0, motivo="sin_anclas")

        idx = np.searchsorted(ts, anclas, side="right") - 1
        filas = []
        for k, i in enumerate(idx):
            if i < 1:
                continue
            t0, p0 = int(ts[i]), int(px[i])

            # --- régimen de vol REZAGADO: sólo información anterior al ancla
            j = np.searchsorted(ts, t0 - vol_ns, side="left")
            if i - j < 50:
                continue
            prev = px[j:i + 1]
            vol_prev = float(np.std(np.diff(prev.astype(np.float64)))) if len(prev) > 2 else 0.0

            # --- dirección 50/50 por seed, ANTES de mirar el futuro
            rd = _rng(CFG["seed"], contrato, fecha, ronda, k)
            direccion = 1 if rd.integers(0, 2) == 0 else -1

            fila = dict(t0=t0, p0=p0, dir=direccion, vol_prev=vol_prev,
                        hora_ct=int(datetime.fromtimestamp(t0 / 1e9, tz=timezone.utc)
                                    .astimezone(CT).hour))
            # --- excursiones por horizonte, en TICKS
            for H in CFG["horizontes_min"]:
                e = np.searchsorted(ts, t0 + H * 60 * 10**9, side="right")
                fut = px[i + 1:e]
                if len(fut) == 0:
                    fila["mfe_%d" % H] = None; fila["mae_%d" % H] = None
                    fila["first_%d" % H] = None
                    continue
                delta = (fut - p0) * direccion          # a favor = positivo
                mfe = int(delta.max()); mae = int(delta.min())
                fila["mfe_%d" % H] = mfe
                fila["mae_%d" % H] = mae
                # primer toque favorable vs adverso, por nivel de la grilla
                for L in CFG["grilla_ticks"]:
                    fav = np.flatnonzero(delta >= L)
                    adv = np.flatnonzero(delta <= -L)
                    f0 = int(fav[0]) if len(fav) else -1
                    a0 = int(adv[0]) if len(adv) else -1
                    if f0 < 0 and a0 < 0:
                        v = 0                      # ninguno
                    elif a0 < 0 or (f0 >= 0 and f0 < a0):
                        v = 1                      # favorable primero
                    else:
                        v = -1                     # adverso primero
                    fila["fa_%d_%d" % (H, L)] = v
            filas.append(fila)
        return dict(fecha=fecha, contrato=contrato, n=len(filas), filas=filas)
    except Exception as e:                          # un día roto no tumba la ronda
        import traceback
        return dict(fecha=fecha, contrato=contrato, n=0,
                    motivo="error: %s" % e, traceback=traceback.format_exc()[-900:])


# ---------------------------------------------------------------------------
def agregar(filas):
    """Tablas NULL: percentiles de MFE/MAE y tasas de primer toque."""
    out = dict(n_anclas=len(filas))
    if not filas:
        return out
    perc = {}
    for H in CFG["horizontes_min"]:
        mfe = np.array([f["mfe_%d" % H] for f in filas if f.get("mfe_%d" % H) is not None])
        mae = np.array([f["mae_%d" % H] for f in filas if f.get("mae_%d" % H) is not None])
        if not len(mfe):
            continue
        perc["H%d" % H] = dict(
            n=int(len(mfe)),
            mfe=[float(np.percentile(mfe, q)) for q in (10, 25, 50, 75, 90)],
            mae=[float(np.percentile(mae, q)) for q in (10, 25, 50, 75, 90)],
            mfe_media=float(mfe.mean()), mae_media=float(mae.mean()))
    out["percentiles"] = perc

    tasas = {}
    for H in CFG["horizontes_min"]:
        for L in CFG["grilla_ticks"]:
            v = np.array([f.get("fa_%d_%d" % (H, L)) for f in filas
                          if f.get("fa_%d_%d" % (H, L)) is not None])
            if not len(v):
                continue
            tasas["H%d_L%d" % (H, L)] = dict(
                n=int(len(v)),
                p_favorable=float((v == 1).mean()),
                p_adverso=float((v == -1).mean()),
                p_ninguno=float((v == 0).mean()))
    out["tasas_primer_toque"] = tasas
    return out


def agregar_por_estrato(filas):
    """Tablas NULL por estrato: franja horaria x regimen de vol REZAGADO.

    Los cortes de vol son terciles calculados sobre las anclas acumuladas: es una
    descripcion del propio nulo, no una eleccion con consecuencias. Los estratos
    con N por debajo de `min_n_estrato` se OCULTAN -- publicar un percentil sobre
    40 observaciones invita a leerlo como si significara algo.
    """
    if not filas:
        return {}
    vols = np.array([f["vol_prev"] for f in filas], dtype=float)
    q1, q2 = (float(np.quantile(vols, CFG["vol_cortes"][0])),
              float(np.quantile(vols, CFG["vol_cortes"][1])))

    def franja(h):
        for a, b in CFG["franjas_horarias"]:
            if a <= h < b or (a > b and (h >= a or h < b)):
                return "%02d-%02d" % (a, b)
        return "otra"

    def regimen(v):
        return "vol_bajo" if v <= q1 else ("vol_medio" if v <= q2 else "vol_alto")

    grupos = {}
    for f in filas:
        k = "%s|%s" % (franja(f["hora_ct"]), regimen(f["vol_prev"]))
        grupos.setdefault(k, []).append(f)

    out = dict(cortes_vol=[q1, q2], estratos={}, ocultos={})
    for k, g in sorted(grupos.items()):
        if len(g) < CFG["min_n_estrato"]:
            out["ocultos"][k] = len(g)      # se declara que existe, no su contenido
            continue
        out["estratos"][k] = agregar(g)
    return out


def bootstrap_por_dia(filas_por_dia, clave, reps=None):
    """Intervalo por bootstrap de BLOQUES = días.

    Remuestrear anclas sueltas daría intervalos falsamente angostos: las anclas
    del mismo día comparten régimen. El bloque natural es el día.
    """
    reps = reps or CFG["bootstrap_reps"]
    dias = list(filas_por_dia)
    if len(dias) < 3:
        return None
    r = np.random.default_rng(CFG["seed"])
    vals = []
    for _ in range(reps):
        pick = r.choice(len(dias), size=len(dias), replace=True)
        acc = []
        for i in pick:
            acc.extend(x for x in filas_por_dia[dias[i]] if x is not None)
        if acc:
            vals.append(float(np.mean(acc)))
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
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "atlas"))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--hard-stop", default="07:10")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    LOG = os.path.join(a.out, "atlas.log")

    # 1 hilo BLAS por worker: 5 workers x N hilos satura y ralentiza todo
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS"):
        os.environ[v] = "1"

    man = json.load(open(a.manifiesto, encoding="utf-8"))
    dias = man["dias"]
    _log("ATLAS NULL — manifiesto: %d dias aptos" % len(dias), LOG)

    # ── candados, en este orden y ruidosos ─────────────────────────────────
    en_holdout = [d for d in dias if d["fecha"] >= CFG["holdout_desde"]]
    if en_holdout:
        _log("  FIREWALL: se descartan %d dias del holdout (>= %s): %s"
             % (len(en_holdout), CFG["holdout_desde"],
                sorted({d["fecha"] for d in en_holdout})), LOG)
    dias = [d for d in dias if d["fecha"] < CFG["holdout_desde"]]

    sin_tipo = [d for d in dias if not d.get("tipo_de_dia")]
    if sin_tipo:
        # fail-closed: un manifiesto viejo sin `tipo_de_dia` no se puede filtrar
        # por alcance, y correr sin filtrar seria meter domingos sin declararlo.
        raise SystemExit(
            "manifiesto sin `tipo_de_dia` en %d dias: regenerar el censo "
            "(tools/censo_integridad.py) antes de correr el atlas" % len(sin_tipo))
    fuera = [d for d in dias if d["tipo_de_dia"] not in CFG["tipos_de_dia"]]
    if fuera:
        import collections as _c
        _log("  ALCANCE: se descartan %d dias fuera de %s -> %s"
             % (len(fuera), CFG["tipos_de_dia"],
                dict(_c.Counter(d["tipo_de_dia"] for d in fuera))), LOG)
    dias = [d for d in dias if d["tipo_de_dia"] in CFG["tipos_de_dia"]]

    import collections as _c
    _log("ATLAS NULL — %d dias EFECTIVOS %s, cfg=%s, workers=%d"
         % (len(dias), dict(_c.Counter(d["tipo_de_dia"] for d in dias)),
            CFG_HASH, a.workers), LOG)
    _log("  ESTO ES UN NULO DESCRIPTIVO. No es un edge ni una estrategia.", LOG)

    hh, mm = (int(x) for x in a.hard_stop.split(":"))
    ahora = datetime.now()
    stop = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if stop <= ahora:
        stop += timedelta(days=1)
    _log("  hard stop: %s" % stop.strftime("%Y-%m-%d %H:%M"), LOG)

    tareas = [(d["archivo"], d.get("contrato") or "?", d["fecha"], a.data) for d in dias]
    if not tareas:
        _log("  manifiesto vacio: nada que hacer", LOG)
        return 1

    import multiprocessing as mp
    filas_por_dia, rondas, hist = {}, [], []
    ronda = 0
    t_ini = time.time()

    with mp.Pool(a.workers) as pool:
        while datetime.now() < stop:
            ronda += 1
            # cada ronda recorre TODOS los días con otra semilla de ancla:
            # más N de la MISMA pregunta, jamás preguntas nuevas
            lote = [(f, c, fe, dd, ronda) for (f, c, fe, dd) in tareas]
            res = []
            for r in pool.imap_unordered(procesar_dia, lote, chunksize=1):
                res.append(r)
                if datetime.now() >= stop:
                    _log("  hard stop alcanzado durante la ronda %d" % ronda, LOG)
                    break
            n_ok = 0
            for r in res:
                if r.get("n"):
                    filas_por_dia.setdefault(r["fecha"], []).extend(r["filas"])
                    n_ok += r["n"]
            todas = [f for v in filas_por_dia.values() for f in v]
            agg = agregar(todas)
            agg_estr = agregar_por_estrato(todas)
            rondas.append(dict(ronda=ronda, anclas_nuevas=n_ok,
                               anclas_total=len(todas),
                               n_dias=len(filas_por_dia),
                               ts=datetime.now().isoformat()))
            # checkpoint ATOMICO por ronda
            tmp = os.path.join(a.out, "_ckpt.tmp")
            json.dump(dict(config=CFG, config_hash=CFG_HASH, rondas=rondas,
                           agregado=agg, por_estrato=agg_estr,
                           n_dias=len(filas_por_dia)),
                      open(tmp, "w", encoding="utf-8"),
                      indent=1, ensure_ascii=False)
            os.replace(tmp, os.path.join(a.out, "checkpoint.json"))

            # convergencia declarada ANTES de correr
            med = [agg.get("percentiles", {}).get("H%d" % H, {}).get("mfe", [0]*5)[2]
                   for H in CFG["horizontes_min"]]
            hist.append(med)
            conv = False
            if len(hist) > CFG["conv_rondas"]:
                ult = np.array(hist[-(CFG["conv_rondas"] + 1):], dtype=float)
                conv = bool(np.max(np.abs(ult - ult[-1])) <= CFG["conv_margen_ticks"])
            _log("ronda %d: +%d anclas (total %d)  mediana MFE=%s  converge=%s"
                 % (ronda, n_ok, len(todas), [round(x, 2) for x in med], conv), LOG)
            if conv:
                _log("  criterio de convergencia alcanzado; se sigue acumulando N "
                     "de la MISMA pregunta hasta el hard stop", LOG)

    # cierre ordenado
    todas = [f for v in filas_por_dia.values() for f in v]
    agg = agregar(todas)
    boot = {}
    for H in CFG["horizontes_min"]:
        col = {d: [f.get("mfe_%d" % H) for f in v] for d, v in filas_por_dia.items()}
        boot["mfe_H%d" % H] = bootstrap_por_dia(col, "mfe")
    # N EFECTIVO: el bootstrap remuestrea DIAS, asi que la unidad independiente es
    # el dia, no el ancla. Reportar solo el N bruto seria vender como independientes
    # anclas que comparten regimen intradiario.
    n_efectivo = len(filas_por_dia)
    salida = dict(
        etiqueta="NULL / DESCRIPTIVO — no es un edge",
        n_anclas_bruto=len(todas), n_efectivo_dias=n_efectivo,
        nota_n=("el N efectivo es el numero de DIAS: las anclas del mismo dia "
                "comparten regimen y el bootstrap remuestrea por bloques de dia"),
        config=CFG, config_hash=CFG_HASH,
        generado_utc=datetime.now(timezone.utc).isoformat(),
        segundos=round(time.time() - t_ini, 1),
        n_dias=len(filas_por_dia), rondas=rondas,
        agregado=agg, por_estrato=agregar_por_estrato(todas),
        bootstrap_por_dia=boot)
    json.dump(salida, open(os.path.join(a.out, "atlas_null.json"), "w",
                           encoding="utf-8"), indent=1, ensure_ascii=False)
    _log("FIN: %d anclas sobre %d dias en %d rondas" % (len(todas), len(filas_por_dia),
                                                        len(rondas)), LOG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
