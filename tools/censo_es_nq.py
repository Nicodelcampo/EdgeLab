#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CENSO DE INTEGRIDAD para `es_full_ticks` y `nq_ticks_clean`.

Archivo aparte de `censo_integridad.py` **a propósito**: aquél consume el schema
canónico de F2 (`ts_utc_ns`, `price_ticks` enteros, `contract`) y estos dos
parquets **no lo cumplen**. Meterlos ahí obligaría a ensuciar el camino que hoy
alimenta el universo de 6E, que está validado. La batería de `universe.py` sí se
reusa entera y sin tocar sus reglas.

## Lo que se midió antes de escribir esto (no se asumió nada)

| propiedad | `es_full_ticks` | `nq_ticks_clean` |
|---|---|---|
| columnas | `datetime, price, bid, ask, volume` | `ts_ns, last, bid, ask, vol` |
| filas | 127.911.524 | 95.326.877 |
| zona horaria | **UTC** (medida) | **UTC** (medida) |
| grilla de precios | 0.25, 0 % fuera | **0.125**, 0 % fuera; **55 % fuera de 0.25** |

La zona horaria se **midió** en vez de suponerse: se ubicó el hueco diario de
mantenimiento y se preguntó en qué hora cae bajo cada interpretación. Leyendo los
timestamps como UTC, el hueco de 60 min arranca 15:59 CT en los dos archivos, y
los huecos de fin de semana duran 2940 min = 49 h (vie 16:00 → dom 17:00 CT). Es
la misma estructura de 6E, así que `VENTANA_CERRADA=(16,17)` aplica tal cual.

## El hallazgo estructural: son series CONTINUAS ARMADAS, no exports crudos

`nq_ticks_clean` tiene el 55 % de sus precios fuera de la grilla de 0.25 — media
tick. No es ruido: el desplazamiento cambia de régimen exactamente **dos veces**,
2025-12-14 y 2026-06-14, los dos domingos de apertura después de un roll
trimestral. Y dentro del tramo desplazado los precios caen, sobre 52,5 M de
ticks y **sin una sola excepción**, en la misma grilla de 0.25 corrida +0.125.

Eso identifica el producto: **back-adjustment**. Se le restó a la historia el
escalón del roll para pegarla continua, y en NQ ese escalón no fue múltiplo
entero de tick.

`es_full_ticks` no muestra el síntoma (0 % fuera de grilla) porque sus ajustes sí
cayeron en múltiplos de tick — pero tiene la **misma firma** en el salto: +206.25
puntos el 2026-06-14, contra +227.625 de NQ el mismo día. Un spread de calendario
ES Jun→Sep es de decenas de puntos y **negativo**; 206 puntos positivos es el
escalón acumulado del ajuste, no un spread.

Conclusión operativa, y es la que condiciona todo lo que sigue:

1. Los **niveles absolutos de precio no son precios reales** fuera del tramo
   crudo. Una zona guardada a 25758.125 no es un nivel al que se pueda mandar una
   orden: ese precio no existe en NQ.
2. Las **diferencias dentro de un tramo sí son exactas** en ticks — el
   desplazamiento se cancela al restar. Estadística de excursiones: válida.
3. Las **fronteras de tramo son cortes duros**. Ninguna ventana de estudio puede
   cruzarlas.

Por eso la salida separa `apto_para_excursiones` de `apto_para_niveles`: son dos
preguntas distintas y meterlas en un solo APTO/DEFECTUOSO perdería justamente lo
que este censo encontró.

## Duplicación

Mismo detector de hash rodante que el censo de 6E — es el que atrapó la copia de
13:00–14:00 dentro de la ventana de mantenimiento. Acá se hashea el precio en
**unidades de la grilla cruda** (0.125 en NQ, 0.25 en ES), donde todos los
precios son enteros exactos. Así el detector es inmune al desplazamiento de los
tramos y no depende de haberlos resuelto bien.

Se busca **cualquier** copia, no sólo el corrimiento de +3 h de 6E.

Uso:  .venv/Scripts/python tools/censo_es_nq.py [--solo es|nq] [--out runs/censo_es_nq]
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
from tools.censo_integridad import hash_rodante, W_DUP  # noqa: E402

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000
HOLDOUT_DESDE = "2026-07-01"

# Roll trimestral CME de índices: el jueves 8 días antes del 3er viernes.
# Se listan los que caen en el rango de estos archivos. NO se usan para excluir
# nada: se usan para MEDIR el salto de precio y clasificar el tramo.
ROLLS = ["2025-09-11", "2025-12-11", "2026-03-12", "2026-06-11"]

# Ventanas que Nico marcó como envenenadas para ES. Se excluyen por orden suya y
# ADEMAS se reporta qué dice el censo por su cuenta sobre ellas — si la regla
# general las agarra sola, la lista negra sobra; si no, la lista es información.
VENTANAS_ENVENENADAS_ES = [("2026-03-15", "2026-03-21"), ("2026-06-11", "2026-06-16")]

ARCHIVOS = {
    "es": dict(
        path="data/es_full_ticks.parquet", instrumento="ES (E-mini S&P 500)",
        col_ts="datetime", ts_en_ns=False, col_px="price", col_vol="volume",
        tick=0.25, grilla=0.25,
        envenenadas=VENTANAS_ENVENENADAS_ES),
    "nq": dict(
        path="data/nq_ticks_clean.parquet", instrumento="NQ (E-mini Nasdaq-100)",
        col_ts="ts_ns", ts_en_ns=True, col_px="last", col_vol="vol",
        tick=0.25, grilla=0.125,
        envenenadas=[]),
}


def _log(m):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), m), flush=True)


def _expr_ts(spec):
    """Expresión SQL que devuelve un TIMESTAMP naive en UTC.

    `to_timestamp` devuelve TIMESTAMPTZ y arrastra `pytz`, que no está en el lock
    — y no hace falta: ya se midió que los timestamps de los dos archivos son
    UTC, así que un timestamp naive es la representación correcta y la conversión
    a CT la hace pandas del lado de Python, con `zoneinfo`.
    """
    if not spec["ts_en_ns"]:
        return spec["col_ts"]
    return "make_timestamp(cast(%s/1000 as bigint))" % spec["col_ts"]


# --------------------------------------------------------------------------
# Identidad del archivo: tramos, rolls, grilla
# --------------------------------------------------------------------------
def identidad(con, spec):
    """Establece qué ES el archivo. Fail-closed: lo que no se puede medir, SKIP."""
    p = spec["path"].replace("\\", "/")
    t = _expr_ts(spec)
    px, tick, grilla = spec["col_px"], spec["tick"], spec["grilla"]

    n, t0, t1, pmin, pmax = con.execute(
        "select count(*), min(%s), max(%s), min(%s), max(%s) from read_parquet('%s')"
        % (t, t, px, px, p)).fetchone()

    # --- grilla: fracción fuera de la grilla de TICK y de la grilla CRUDA
    fuera_tick, fuera_grilla = con.execute(
        "select sum(case when abs({px}/{tk} - round({px}/{tk}))>1e-9 then 1 else 0 end),"
        "       sum(case when abs({px}/{gr} - round({px}/{gr}))>1e-9 then 1 else 0 end)"
        " from read_parquet('{p}')".format(px=px, tk=tick, gr=grilla, p=p)).fetchone()

    # --- tramos por desplazamiento respecto de la grilla de tick, por día
    dd = con.execute(
        "select cast(%s as date) d, count(*) n,"
        " avg(case when abs(%s/%s - round(%s/%s))>1e-9 then 1.0 else 0.0 end) frac_off"
        " from read_parquet('%s') group by 1 order by 1" % (t, px, tick, px, tick, p)).df()
    dd["reg"] = (dd.frac_off > 0.5).astype(int)
    dd["ds"] = dd.d.astype(str).str.slice(0, 10)
    cortes = set(dd.index[dd.reg.diff().fillna(0) != 0].tolist())
    # los rolls entran como corte aunque el desplazamiento no cambie: un cambio
    # de contrato crudo NO mueve la grilla si el spread es multiplo de tick, asi
    # que la deteccion por desplazamiento sola dejaria pasar ese caso.
    for r in ROLLS:
        idx = dd.index[dd.ds >= r]
        if len(idx):
            cortes.add(int(idx[0]))

    tramos, ini = [], 0
    for c in sorted(cortes) + [len(dd)]:
        if c <= ini:
            continue
        tramos.append(dict(desde=dd.ds.iloc[ini], hasta=dd.ds.iloc[c - 1],
                           n_dias=int(c - ini), n_ticks=int(dd.n.iloc[ini:c].sum()),
                           desplazado=bool(dd.reg.iloc[ini])))
        ini = c

    # --- salto de precio en cada roll, CONTRA LA DISTRIBUCION DE FINES DE SEMANA
    #
    # Medir sólo el salto no alcanza: el hueco mayor de la semana del roll es el
    # fin de semana, y un fin de semana normal de NQ salta ±50 puntos. Un umbral
    # fijo confundiría un gap corriente con un cambio de contrato. Se compara
    # contra la distribución empírica de TODOS los fines de semana del archivo:
    # un cambio de contrato crudo aparece como outlier extremo, un gap normal no.
    gaps = con.execute(
        "select %s tt, %s pp from read_parquet('%s') where date_part('hour', %s) "
        "between 20 and 23 or date_part('hour', %s) between 0 and 1" % (t, px, p, t, t)).df()
    fines = []
    if len(gaps) > 2:
        gt = gaps.tt.values.astype("datetime64[ns]").astype("int64")
        gp = gaps.pp.values
        gd = np.diff(gt)
        # fin de semana = hueco de mas de 24 h
        for k in np.flatnonzero(gd > 24 * 3600 * NS):
            fines.append((int(gt[k]), float(gp[k + 1] - gp[k])))
    mags = np.abs([x[1] for x in fines]) if fines else np.array([0.0])
    mediana = float(np.median(mags))
    mad = float(np.median(np.abs(mags - mediana))) or 1e-9

    rolls = []
    for r in ROLLS:
        r_ns = int(np.datetime64(r, "ns").astype("int64"))
        cerca = [x for x in fines if 0 <= x[0] - r_ns < 7 * 24 * 3600 * NS]
        if not cerca:
            rolls.append(dict(roll=r, estado="SIN_FIN_DE_SEMANA_EN_LA_VENTANA",
                              corte_duro=True))
            continue
        salto = max(cerca, key=lambda x: abs(x[1]))[1]
        z = (abs(salto) - mediana) / (1.4826 * mad)
        rolls.append(dict(
            roll=r, salto_puntos=round(salto, 4), salto_ticks=round(salto / tick, 4),
            entero_en_ticks=bool(abs(salto / tick - round(salto / tick)) < 1e-6),
            z_robusto_vs_fines_de_semana=round(float(z), 2),
            mediana_fin_de_semana=round(mediana, 4),
            # NO se clasifica: con ~48 fines de semana en el archivo no hay poder
            # para separar un cambio de contrato de un gap grande, y sin una
            # referencia externa del spread de calendario la pregunta no se puede
            # cerrar con los datos que hay. Se declara CORTE DURO igual — es
            # fail-closed: ninguna ventana de estudio cruza un roll, tenga o no
            # cambio de contrato. El salto queda como evidencia, no como criterio.
            corte_duro=True,
            nota="salto medido; clasificacion NO establecida (ver docstring)"))

    crudos = [x for x in tramos if not x["desplazado"]]
    return dict(
        instrumento=spec["instrumento"], n_ticks=int(n),
        rango=[str(t0), str(t1)], precio=[float(pmin), float(pmax)],
        tick_declarado=tick, grilla_cruda_medida=grilla,
        pct_fuera_de_grilla_de_tick=round(100.0 * fuera_tick / n, 6),
        pct_fuera_de_grilla_cruda=round(100.0 * fuera_grilla / n, 6),
        tramos=tramos, rolls=rolls,
        contrato=dict(
            estado="SKIP_NO_ESTABLECIDO",
            motivo=("el archivo es una serie continua armada, no el export de un "
                    "contrato unico: no tiene columna de contrato y los niveles de "
                    "precio estan ajustados. El front month por volumen -- el "
                    "criterio medido que se uso en 6E -- no se puede aplicar porque "
                    "no hay dos contratos que comparar dentro del archivo."),
            tramo_crudo_inferido=(crudos[-1] if crudos else None),
            evidencia_del_tramo_crudo=("ultimo tramo sin desplazamiento y posterior "
                                       "al salto discontinuo del roll 2026-06-11")))


# --------------------------------------------------------------------------
# Duplicación sobre el archivo entero, por trozos, sin reventar la RAM
# --------------------------------------------------------------------------
def duplicacion(con, spec, filas_por_trozo=16_000_000):
    """Hash rodante sobre TODO el archivo, acumulando sólo el array de hashes.

    El hash rodante pide `key` y `acc` simultáneos; sobre 128 M de ticks son
    ~2 GB más temporarios, y hay un atlas corriendo. Se procesa por trozos con
    solape de W-1 — el solape exacto para que ninguna ventana quede sin hashear —
    y se conserva **el array global de hashes**, así una copia entre trozos
    distintos igual aparece al ordenar. No hay tope silencioso: la cobertura es
    el archivo entero.

    El troceo es POSICIONAL, sin `order by`: se verificó que los dos archivos
    están guardados en orden temporal exacto (0 desórdenes sobre 128 M y 95 M
    filas), así que la posición de fila **es** el orden cronológico.

    Confirmación: se agrupa por valor de hash y sólo se comparan las posiciones
    **dentro del mismo grupo**. Comparar todas contra todas sería O(n²) sobre los
    candidatos y no termina; y como el criterio final es la igualdad exacta de la
    secuencia, agrupar no pierde ninguna duplicación real.
    """
    p = spec["path"].replace("\\", "/")
    px, vol, gr = spec["col_px"], spec["col_vol"], spec["grilla"]
    n = con.execute("select count(*) from read_parquet('%s')" % p).fetchone()[0]
    solape = W_DUP - 1

    def leer(off, lim):
        """Clave (precio_en_grilla_cruda, volumen) de `lim` filas desde `off`."""
        d = con.execute(
            "select cast(round(%s/%s) as bigint) u, cast(%s as bigint) v"
            " from read_parquet('%s') limit %d offset %d" % (px, gr, vol, p, lim, off)).df()
        return (d.u.values.astype(np.uint64) * np.uint64(100000)
                + np.minimum(d.v.values, 99999).astype(np.uint64))

    # --- pasada 1: hashes
    partes, off = [], 0
    while off < n:
        lim = min(filas_por_trozo + solape, n - off)
        h = hash_rodante(leer(off, lim), W_DUP)
        partes.append(h[:filas_por_trozo].copy())
        del h
        off += filas_por_trozo
    H = np.concatenate(partes) if partes else np.empty(0, np.uint64)
    del partes
    _log("    hashes: %d posiciones" % len(H))
    if not len(H):
        return [], n

    hs = np.sort(H)
    rep = np.unique(hs[1:][hs[1:] == hs[:-1]])
    del hs
    _log("    valores de hash repetidos: %d" % len(rep))
    if not len(rep):
        return [], n

    pos = np.flatnonzero(np.isin(H, rep))
    hv = H[pos]
    del H
    _log("    posiciones candidatas: %d" % len(pos))

    # --- grupos por valor de hash
    o = np.argsort(hv, kind="stable")
    pos, hv = pos[o], hv[o]
    cortes = np.flatnonzero(hv[1:] != hv[:-1]) + 1
    grupos = np.split(pos, cortes)

    # --- pasada 2: ventanas de las posiciones candidatas, en streaming
    necesarias = sorted({int(i) for g in grupos for i in g})
    ventanas = {}
    if necesarias:
        i, off = 0, 0
        while off < n and i < len(necesarias):
            lim = min(filas_por_trozo + solape, n - off)
            k = leer(off, lim)
            while i < len(necesarias) and necesarias[i] + W_DUP <= off + lim:
                a = necesarias[i]
                ventanas[a] = k[a - off:a - off + W_DUP].copy()
                i += 1
            del k
            off += filas_por_trozo

    pares, vistos = [], set()
    for g in grupos:
        gg = sorted(int(x) for x in g)
        for ai in range(len(gg)):
            for bi in range(ai + 1, len(gg)):
                a, b = gg[ai], gg[bi]
                if b - a < W_DUP:
                    continue                     # solape trivial consigo mismo
                va, vb = ventanas.get(a), ventanas.get(b)
                if va is None or vb is None or not np.array_equal(va, vb):
                    continue                     # colision de hash, no duplicacion
                clave = (a // W_DUP, b - a)      # colapsa el corrimiento de 1 tick
                if clave in vistos:
                    continue
                vistos.add(clave)
                # GUARDIA CONTRA EL FALSO POSITIVO DEGENERADO: 256 ticks seguidos
                # al mismo precio y el mismo volumen coinciden con CUALQUIER otra
                # racha igual. Eso es un mercado clavado, no una copia. Contar la
                # coincidencia como duplicacion inflaria el censo con ruido y
                # tiraria dias limpios.
                nd = int(len(np.unique(va)))
                pares.append(dict(origen_idx=a, copia_idx=b, n_ticks=W_DUP,
                                  separacion_ticks=b - a, n_valores_distintos=nd,
                                  degenerado=bool(nd <= 2)))
                if len(pares) >= 200:
                    return pares, n
    return pares, n


# --------------------------------------------------------------------------
def censar(con, clave, spec, out):
    p = spec["path"].replace("\\", "/")
    t, px, vol = _expr_ts(spec), spec["col_px"], spec["col_vol"]
    _log("=" * 70)
    _log("%s — %s" % (clave.upper(), spec["instrumento"]))

    t0 = time.time()
    ident = identidad(con, spec)
    _log("  identidad: %d ticks, %s -> %s" % (ident["n_ticks"], *ident["rango"]))
    _log("  fuera de grilla de tick: %.4f%%   de grilla cruda (%s): %.6f%%"
         % (ident["pct_fuera_de_grilla_de_tick"], spec["grilla"],
            ident["pct_fuera_de_grilla_cruda"]))
    for tr in ident["tramos"]:
        _log("    tramo %s -> %s  (%d dias, %d ticks)  desplazado=%s"
             % (tr["desde"], tr["hasta"], tr["n_dias"], tr["n_ticks"], tr["desplazado"]))
    for r in ident["rolls"]:
        _log("    roll %s: %s  corte_duro=%s"
             % (r["roll"],
                ("salto=%+9.3f pts (%+.0f ticks, z=%.1f)"
                 % (r["salto_puntos"], r["salto_ticks"], r["z_robusto_vs_fines_de_semana"])
                 if "salto_puntos" in r else r.get("estado", "?")),
                r.get("corte_duro")))

    # --- batería por día
    # Una consulta POR DIA serían ~240 escaneos completos del parquet. Se lee la
    # columna de tiempo una sola vez y se corta con numpy, igual que el censo de
    # 6E. La fecha se arma en entero: `strftime` sobre 10^8 valores es un bucle
    # de Python adentro de pandas y domina el censo entero.
    _log("  bateria por dia...")
    import pandas as pd
    # el volumen diario se agrega en duckdb: traer 10^8 volumenes a memoria para
    # despues sumarlos por dia cuesta 1 GB y no aporta nada al veredicto.
    volday = {str(r.d)[:10]: int(r.v) for _, r in con.execute(
        "select cast(%s as date) d, sum(%s) v from read_parquet('%s') group by 1"
        % (t, vol, p)).df().iterrows()}
    tsdf = con.execute("select %s as tt from read_parquet('%s')" % (t, p)).df()
    # CASTEO EXPLICITO A datetime64[ns]. duckdb entrega TIMESTAMP como
    # datetime64[**us**]; tomar ese `.astype(int64)` como si fuesen nanosegundos
    # comprime 322 dias en 7 horas y la bateria ve UN solo dia. Paso silencioso:
    # no falla, da un veredicto sobre un dia que no existe.
    ts = tsdf.tt.values.astype("datetime64[ns]").astype(np.int64)
    del tsdf
    ct = pd.to_datetime(ts, unit="ns", utc=True).tz_convert(CT)
    # dtypes chicos a proposito: sobre 128 M de filas cada int64 de mas es 1 GB
    fechas = (ct.year.to_numpy().astype(np.int32) * 10000
              + ct.month.to_numpy().astype(np.int32) * 100
              + ct.day.to_numpy().astype(np.int32))
    horas = ct.hour.to_numpy().astype(np.int8)
    dows = ct.dayofweek.to_numpy().astype(np.int8)
    del ct

    bordes = np.flatnonzero(fechas[1:] != fechas[:-1]) + 1
    ini = np.concatenate(([0], bordes))
    fin = np.concatenate((bordes, [len(ts)]))
    dias = []
    for a, b in zip(ini, fin):
        f = "%04d-%02d-%02d" % (fechas[a] // 10000, fechas[a] // 100 % 100, fechas[a] % 100)
        rep = U.evaluar_dia("__continuo__", f, ts[a:b], price_ticks=None,
                            horas=horas[a:b], dow=int(dows[a]))
        # `front_month` no aplica a una serie continua armada: no hay contrato que
        # comparar. El veredicto de identidad ocupa su lugar, a nivel de archivo.
        rep["motivos"] = [m for m in rep["motivos"] if m["chequeo"] != "front_month"]
        rep.pop("detalle", None)
        rep["estado"] = "APTO" if not rep["motivos"] else "DEFECTUOSO"
        rep["volumen"] = volday.get(f, 0)
        rep["tramo"] = next((i for i, tr in enumerate(ident["tramos"])
                             if tr["desde"] <= f <= tr["hasta"]), None)
        rep["pre_holdout"] = f < HOLDOUT_DESDE
        rep["envenenado"] = any(x <= f <= y for x, y in spec["envenenadas"])
        dias.append(rep)
    del ts, fechas, horas, dows
    _log("  %d dias  APTO=%d  DEF=%d" % (
        len(dias), sum(1 for x in dias if x["estado"] == "APTO"),
        sum(1 for x in dias if x["estado"] == "DEFECTUOSO")))

    # --- duplicación
    _log("  duplicacion (hash rodante, archivo entero)...")
    dups, ntot = duplicacion(con, spec)
    reales = [d for d in dups if not d["degenerado"]]
    _log("  coincidencias exactas: %d   de las cuales DEGENERADAS: %d   REALES: %d"
         % (len(dups), len(dups) - len(reales), len(reales)))

    # fecha/hora de cada duplicación real, y propagación al veredicto diario
    for d in reales:
        for k, col in (("origen_idx", "origen_ct"), ("copia_idx", "copia_ct")):
            r = con.execute("select %s from read_parquet('%s') limit 1 offset %d"
                            % (t, p, d[k])).fetchone()
            d[col] = (datetime.fromisoformat(str(r[0])).replace(tzinfo=timezone.utc)
                      .astimezone(CT).strftime("%Y-%m-%d %H:%M:%S")) if r else ""
    afectadas = {}
    for d in reales:
        for col in ("origen_ct", "copia_ct"):
            afectadas[d[col][:10]] = afectadas.get(d[col][:10], 0) + 1
    for rep in dias:
        k = afectadas.get(rep["fecha"])
        if k:
            rep["motivos"].append(dict(chequeo="duplicacion_de_bloque", ok=False,
                                       code="BLOQUE_DUPLICADO", n_bloques=k))
            rep["estado"] = "DEFECTUOSO"
    if afectadas:
        _log("  dias tocados por duplicacion real: %d  -> %s"
             % (len(afectadas), sorted(afectadas)[:8]))

    res = dict(archivo=os.path.basename(spec["path"]), clave=clave,
               identidad=ident, n_dias=len(dias),
               n_aptos=sum(1 for x in dias if x["estado"] == "APTO"),
               n_defectuosos=sum(1 for x in dias if x["estado"] == "DEFECTUOSO"),
               n_coincidencias_exactas=len(dups),
               n_degeneradas=len(dups) - len(reales),
               duplicaciones_de_bloque=reales,
               bug_6e_presente=bool(reales),
               dias_con_duplicacion=sorted(afectadas),
               segundos=round(time.time() - t0, 1), dias=dias)
    json.dump(res, open(os.path.join(out, "censo_%s.json" % clave), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default=None, choices=["es", "nq"])
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "censo_es_nq"))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    import duckdb
    con = duckdb.connect()
    con.execute("set enable_progress_bar=false")
    con.execute("set memory_limit='3GB'")       # el atlas corre en paralelo

    claves = [a.solo] if a.solo else ["es", "nq"]
    res = [censar(con, k, ARCHIVOS[k], a.out) for k in claves]

    # manifiesto: qué días pueden consumirse, y PARA QUÉ
    universo = []
    for r in res:
        crudo = r["identidad"]["contrato"]["tramo_crudo_inferido"]
        for d in r["dias"]:
            if d["estado"] != "APTO" or not d["pre_holdout"] or d["envenenado"]:
                continue
            en_crudo = bool(crudo and crudo["desde"] <= d["fecha"] <= crudo["hasta"])
            universo.append(dict(
                archivo=r["archivo"], fecha=d["fecha"], n_ticks=d["n_ticks"],
                tramo=d["tramo"],
                apto_para_excursiones=True,      # diffs exactas dentro del tramo
                apto_para_niveles=en_crudo))     # precios reales solo en el crudo
    json.dump(dict(generado_utc=datetime.now(timezone.utc).isoformat(),
                   holdout_desde=HOLDOUT_DESDE, n=len(universo), dias=universo),
              open(os.path.join(a.out, "manifiesto_es_nq.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)

    _log("=" * 70)
    for r in res:
        _log("%-24s dias=%-4d APTO=%-4d DEF=%-4d  dup_bloque=%d  bug_6E=%s"
             % (r["archivo"], r["n_dias"], r["n_aptos"], r["n_defectuosos"],
                len(r["duplicaciones_de_bloque"]),
                "SI" if r["bug_6e_presente"] else "NO"))
    ne = sum(1 for u in universo if u["apto_para_excursiones"])
    nn = sum(1 for u in universo if u["apto_para_niveles"])
    _log("universo consumible pre-holdout: %d dias  (excursiones=%d, niveles=%d)"
         % (len(universo), ne, nn))
    _log("salida: %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
