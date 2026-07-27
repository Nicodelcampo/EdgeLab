#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CENSO DE INTEGRIDAD — todos los días de todos los parquets.

## Por qué el detector de duplicación es lo más importante de acá

La copia de 13:00–14:00 dentro de la ventana de mantenimiento se encontró **por
accidente**: cayó donde no debía haber nada. Una copia idéntica dentro de una
hora ACTIVA habría sido invisible — el precio es continuo, el volumen plausible,
y ninguna regla de sesión la delata. El único modo de saber si hay más es
buscarlas por su firma: una subsecuencia de `(precio, volumen)` que se repite.

Método: **hash rodante** sobre la secuencia `(price_ticks, volume)` con ventana
de W ticks. Dos posiciones con el mismo hash y separadas más de W son candidatas;
se confirman comparando la secuencia **exacta**. Se usa un índice de hashes, no
todos-contra-todos: con 19,7 M de ticks, O(n²) no termina nunca.

Una coincidencia casual de W=256 pares consecutivos es esencialmente imposible en
datos reales, así que el detector no necesita heurísticas de "parecido": o la
secuencia es idéntica o no lo es.

**NO** se repiten los tests de corrimiento +3h: quedaron refutados (la apertura
dominical y el hueco no se desplazan; era duplicación de bloque).

Uso:  .venv/Scripts/python tools/censo_integridad.py [--out runs/censo]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import universe as U  # noqa: E402

CT = ZoneInfo("America/Chicago")
W_DUP = 256          # ventana del hash rodante, en ticks
B_HASH = np.uint64(1000003)
NS = 1_000_000_000


def _log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


# ---------------------------------------------------------------- duplicación
def hash_rodante(key, w=W_DUP):
    """Hash polinomial en CADA posicion, vectorizado.

    Por que no bloques alineados: un bloque duplicado empieza en una posicion
    arbitraria, asi que los bloques alineados del ORIGINAL caen en posiciones no
    alineadas de la COPIA y los hashes nunca coinciden. Esa version dio 0
    duplicaciones sobre un parquet donde hay una de 3577 ticks demostrada: un
    detector con falso negativo conocido no sirve para nada.

    El truco para que sea viable: `w` pasadas VECTORIZADAS sobre todo el array
    (256 operaciones numpy de 5M elementos) en vez de 5M iteraciones de Python.
    Wraparound natural de uint64, igual que el digest de TickBarDiag.
    """
    n = len(key)
    if n < w:
        return np.empty(0, np.uint64)
    k = key.astype(np.uint64)
    m = n - w + 1
    acc = np.zeros(m, np.uint64)
    for j in range(w):
        acc = acc * B_HASH + k[j:j + m]
    return acc


def buscar_duplicados(key, ts, w=W_DUP, max_reportar=40):
    """Bloques cuya secuencia (precio,volumen) se repite. Confirmados EXACTO."""
    h = hash_rodante(key, w)
    if not len(h):
        return []
    orden = np.argsort(h, kind="stable")
    hs = h[orden]
    cand = {}
    for idx in np.flatnonzero(hs[1:] == hs[:-1]):
        a, b = int(orden[idx]), int(orden[idx + 1])
        if a > b:
            a, b = b, a
        if b - a < w:                       # solape trivial consigo mismo
            continue
        if not np.array_equal(key[a:a + w], key[b:b + w]):
            continue                        # colision de hash, no duplicacion
        cand.setdefault((a // w, b - a), (a, b))   # colapsa el corrimiento de 1 tick
    pares = []
    for (a, b) in sorted(cand.values()):
        pares.append(dict(origen_idx=a, copia_idx=b, n_ticks=w,
                          origen_ts=str(_TS[a]) if _TS is not None else "",
                          copia_ts=str(_TS[b]) if _TS is not None else ""))
        if len(pares) >= max_reportar:
            break
    return pares


_TS = None      # indice de fechas ya convertido, para no recalcular por par


def extender_duplicado(key, a, b):
    """Largo REAL del bloque duplicado, extendiendo desde un par confirmado."""
    n = len(key)
    ini = 0
    while a - ini - 1 >= 0 and b - ini - 1 > a and key[a - ini - 1] == key[b - ini - 1]:
        ini += 1
    fin = 0
    while b + W_DUP + fin < n and key[a + W_DUP + fin] == key[b + W_DUP + fin]:
        fin += 1
    return ini + W_DUP + fin


# --------------------------------------------------------------------- censo
def censar_parquet(path, contrato_hint=None):
    import duckdb
    con = duckdb.connect()
    _log("leyendo %s" % os.path.basename(path))
    df = con.execute(
        "select ts_utc_ns, price_ticks, volume, contract from read_parquet('%s') "
        "order by ts_utc_ns" % path.replace("\\", "/")).df()
    ts = df.ts_utc_ns.values.astype(np.int64)
    px = df.price_ticks.values.astype(np.int64)
    vol = df.volume.values.astype(np.int64)
    contratos = sorted(set(df.contract.astype(str)))
    del df

    # clave de secuencia: precio y volumen juntos, sin colisión práctica
    key = (px.astype(np.uint64) * np.uint64(100000)
           + np.minimum(vol, 99999).astype(np.uint64))

    _log("  %d ticks, contratos=%s" % (len(ts), contratos))

    # --- indice de fechas CT, vectorizado y compartido
    import pandas as pd
    global _TS
    _idx = pd.to_datetime(ts, unit="ns", utc=True).tz_convert(CT)
    _TS = _idx

    # --- duplicación generalizada
    t0 = time.time()
    dups = buscar_duplicados(key, ts)
    for d in dups:
        d["n_ticks_reales"] = int(extender_duplicado(key, d["origen_idx"], d["copia_idx"]))
    _log("  duplicados confirmados: %d  (%.1fs)" % (len(dups), time.time() - t0))

    # --- por día
    # strftime sobre 5M valores tarda ~18 s (bucle Python adentro de pandas).
    # Los componentes ya estan vectorizados: la fecha se arma en entero.
    fechas = (_idx.year.to_numpy() * 10000 + _idx.month.to_numpy() * 100
              + _idx.day.to_numpy())
    horas  = _idx.hour.to_numpy()
    dows   = _idx.dayofweek.to_numpy()
    dias, out = [], []
    bordes = np.flatnonzero(fechas[1:] != fechas[:-1]) + 1
    ini = np.concatenate(([0], bordes))
    fin = np.concatenate((bordes, [len(ts)]))
    contrato = contrato_hint or (contratos[0] if len(contratos) == 1 else None)
    for a, b in zip(ini, fin):
        f = "%04d-%02d-%02d" % (fechas[a] // 10000, fechas[a] // 100 % 100,
                                fechas[a] % 100)
        rep = U.evaluar_dia(contrato or "?", f, ts[a:b], price_ticks=None,
                            horas=horas[a:b], dow=int(dows[a]))
        rep["volumen"] = int(vol[a:b].sum())
        rep["primer_tick_ct"] = datetime.fromtimestamp(int(ts[a]) / 1e9, tz=timezone.utc)\
            .astimezone(CT).strftime("%H:%M:%S")
        rep["ultimo_tick_ct"] = datetime.fromtimestamp(int(ts[b - 1]) / 1e9, tz=timezone.utc)\
            .astimezone(CT).strftime("%H:%M:%S")
        rep.pop("detalle", None)
        out.append(rep)
        dias.append(f)

    # --- propagar las duplicaciones al veredicto DIARIO
    # Sin esto el censo encuentra la duplicacion pero el dia sigue siendo APTO:
    # el 2026-06-19 cayo por SIN_HUECO_DE_MANTENIMIENTO, o sea por CASUALIDAD.
    # Una copia enteramente dentro de horario activo, en un dia con hueco normal,
    # habria pasado -- y ese es justo el caso que el censo existe para atrapar.
    por_fecha = {}
    for d in dups:
        for idxk in ("origen_idx", "copia_idx"):
            i = d[idxk]
            fk = "%04d-%02d-%02d" % (fechas[i] // 10000, fechas[i] // 100 % 100,
                                     fechas[i] % 100)
            por_fecha.setdefault(fk, 0)
            por_fecha[fk] += 1
    for rep in out:
        n = por_fecha.get(rep["fecha"])
        if n:
            rep["motivos"].append(dict(chequeo="duplicacion_de_bloque", ok=False,
                                       code="BLOQUE_DUPLICADO", n_bloques=n))
            rep["estado"] = "DEFECTUOSO"

    # --- duplicados exactos de (ts, precio, vol)
    # np.unique(axis=0) sobre 5M x 3 ordena una matriz entera; una clave escalar
    # combinada da lo mismo en una fraccion del tiempo. Los ts vienen ordenados,
    # asi que basta comparar con el vecino tras ordenar la clave.
    trio_key = (ts.astype(np.uint64) * np.uint64(1_000_000_003)
                + key)                     # ts + (precio,volumen) ya combinados
    tk = np.sort(trio_key)
    n_dup_exactos = int(np.count_nonzero(tk[1:] == tk[:-1]))

    h = hashlib.sha256()
    h.update(ts.tobytes()); h.update(px.tobytes()); h.update(vol.tobytes())
    return dict(
        archivo=os.path.basename(path), contratos=contratos, n_ticks=int(len(ts)),
        volumen=int(vol.sum()), digest=h.hexdigest()[:32],
        rango=[str(dias[0]), str(dias[-1])] if dias else [],
        n_dias=len(out),
        n_aptos=sum(1 for d in out if d["estado"] == "APTO"),
        n_defectuosos=sum(1 for d in out if d["estado"] == "DEFECTUOSO"),
        n_indeterminados=sum(1 for d in out if d["estado"] == "INDETERMINADO"),
        grupos_ts_px_vol_repetidos=n_dup_exactos,
        duplicaciones_de_bloque=dups,
        dias=out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(REPO, "data", "nt8", "6E"))
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "censo"))
    ap.add_argument("--skip", default="6E_all_contracts.parquet",
                    help="union de los otros: sus duplicados serian los mismos")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    archivos = [f for f in sorted(os.listdir(a.data))
                if f.endswith(".parquet") and f not in a.skip.split(",")]
    _log("CENSO DE INTEGRIDAD — %d parquets" % len(archivos))
    res, t0 = [], time.time()
    for f in archivos:
        try:
            res.append(censar_parquet(os.path.join(a.data, f)))
        except Exception as e:                       # un parquet ilegible no frena el censo
            _log("  ERROR en %s: %s" % (f, e))
            res.append(dict(archivo=f, error=str(e)))

    cfg = dict(w_dup=W_DUP, bateria=list(U.BATERIA),
               front_month=U.FRONT_MONTH, cierres_tempranos=U.CIERRES_TEMPRANOS)
    cfg_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]

    # manifiesto del universo: lo que ATLAS puede consumir
    universo = []
    for r in res:
        for d in r.get("dias", []):
            if d["estado"] == "APTO":
                universo.append(dict(archivo=r["archivo"], contrato=d.get("contrato"),
                                     fecha=d["fecha"], n_ticks=d["n_ticks"]))
    manifiesto = dict(
        generado_utc=datetime.now(timezone.utc).isoformat(),
        config_hash=cfg_hash, config=cfg,
        n_dias_aptos=len(universo), dias=universo)

    json.dump(res, open(os.path.join(a.out, "censo.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, default=str)
    json.dump(manifiesto, open(os.path.join(a.out, "manifiesto_universo.json"), "w",
                               encoding="utf-8"), indent=1, ensure_ascii=False)

    _log("=" * 70)
    for r in res:
        if "error" in r:
            _log("%-28s ERROR" % r["archivo"]); continue
        _log("%-28s %5d dias  APTO=%-4d DEF=%-4d IND=%-3d  dup_bloque=%d"
             % (r["archivo"], r["n_dias"], r["n_aptos"], r["n_defectuosos"],
                r["n_indeterminados"], len(r["duplicaciones_de_bloque"])))
    _log("universo: %d dias aptos   config_hash=%s   %.0fs"
         % (len(universo), cfg_hash, time.time() - t0))
    _log("salida: %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
