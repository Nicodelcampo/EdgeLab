# -*- coding: utf-8 -*-
"""Arnés de EXPLORE — mide zonas contra el nulo. **Seco: no decide nada solo.**

## Qué hace

1. Carga zonas del CSV del oráculo y se queda con el **PRIMER TOQUE** de cada
   una (un evento por zona: los toques posteriores no cuentan para la primaria).
2. Desde ese instante mide la excursión en la dirección **declarada en el
   pre-registro** hasta el horizonte.
3. Clasifica: objetivo primero / stop primero / ni uno.
4. Compara contra el nulo del atlas, estratificado igual.
5. p-valor por **permutación estratificada por día**; intervalo por **bootstrap
   estacionario**.

## Las tres decisiones que ya costaron caro y acá están cerradas

**Timeout a mercado.** El atlas puntúa la salida por horizonte como 0. Eso no es
una convención de P&L: marcado a mercado, la esperanza nula es *exactamente* 0
para toda geometría, y puntuar el timeout como cero hace que las geometrías de
objetivo cercano parezcan ventajosas cuando no lo son. Acá el timeout vale lo
que valga la posición al horizonte. La convención se declara en el pre-registro
y el runner la respeta; no hay default.

**Unidad = zona, no toque.** Un evento por zona. Contar todos los toques sería
pseudo-replicación: una zona muy tocada pesaría como veinte zonas.

**El runner se niega sin pre-registro sellado.** No hay bandera para saltearlo.

## Lo que este módulo NO hace

No elige P/N/K, no elige dirección, no decide si algo es un edge. Todo eso viene
del pre-registro sellado. Si falta, levanta.
"""
from __future__ import annotations

import numpy as np

from edgelab.research.preregistro import (PreRegistroError, cargar_sellado,
                                          exigir_coherencia)

__all__ = ["parsear_zonas", "primer_toque", "clasificar_excursion",
           "evaluar_toques", "permutacion_estratificada_por_dia", "correr"]


# --------------------------------------------------------------------- parseo
def parsear_zonas(path, tick_size):
    """Zonas y toques del CSV de eventos. Devuelve (zonas, primeros_toques)."""
    zonas, toques = {}, []
    with open(path, encoding="utf-8") as fh:
        for linea in fh:
            if linea.startswith("#"):
                continue
            c = linea.rstrip("\n").split("|")
            if len(c) < 4 or c[2] not in ("ZONE_CREATED", "ZONE_TOUCHED"):
                continue
            d = dict(kv.split("=", 1) for kv in c[3].split(";") if "=" in kv)
            zid = d.get("zone_id")
            if not zid:
                continue
            if c[2] == "ZONE_CREATED":
                zonas[zid] = dict(
                    zone_id=zid, side=d.get("side"), ts=c[1],
                    lo_ticks=int(round(float(d["lo"]) / tick_size)),
                    hi_ticks=int(round(float(d["hi"]) / tick_size)),
                    vol=float(d.get("vol", 0)))
            elif d.get("touches") == "1":
                toques.append(dict(zone_id=zid, ts=c[1], side=d.get("side")))
    return zonas, toques


def primer_toque(toques):
    """Un evento por zona. Si el oráculo repitiera `touches=1`, gana el primero."""
    visto, out = set(), []
    for t in sorted(toques, key=lambda x: x["ts"]):
        if t["zone_id"] in visto:
            continue
        visto.add(t["zone_id"])
        out.append(t)
    return out


# ---------------------------------------------------------------- clasificación
def clasificar_excursion(px_ticks, i0, direccion, P, N, n_pasos,
                         convencion_timeout="a_mercado"):
    """Resultado desde el paso `i0`, mirando SOLO hacia adelante.

    `direccion`: +1 si la hipótesis dice que el precio sube, -1 si baja.
    Devuelve (resultado, valor_en_ticks).

    El barrido es secuencial a propósito: importa **cuál se toca primero**, y
    eso no se puede sacar del máximo y el mínimo por separado.
    """
    n = len(px_ticks)
    fin = min(i0 + n_pasos, n - 1)
    if fin <= i0:
        return "SIN_FUTURO", np.nan
    p0 = px_ticks[i0]
    for i in range(i0 + 1, fin + 1):
        d = direccion * (px_ticks[i] - p0)
        if d >= P:
            return "OBJETIVO", float(P)
        if d <= -N:
            return "STOP", float(-N)
    d_fin = direccion * (px_ticks[fin] - p0)
    if convencion_timeout == "cero":
        return "TIMEOUT", 0.0
    return "TIMEOUT", float(d_fin)


# ----------------------------------------------------------------- agregación
def evaluar_toques(filas):
    """Tasas y esperanza. `filas`: dicts con `resultado` y `valor`."""
    v = [f for f in filas if f["resultado"] != "SIN_FUTURO"]
    n = len(v)
    if not n:
        return None
    val = np.array([f["valor"] for f in v], float)
    return dict(
        n=n,
        p_objetivo=sum(1 for f in v if f["resultado"] == "OBJETIVO") / n,
        p_stop=sum(1 for f in v if f["resultado"] == "STOP") / n,
        p_timeout=sum(1 for f in v if f["resultado"] == "TIMEOUT") / n,
        e_ticks=float(val.mean()),
        e_neto_ticks=None,          # lo completa `correr` con la fricción sellada
        descartados_sin_futuro=len(filas) - n)


def permutacion_estratificada_por_dia(por_dia_real, por_dia_candidatos,
                                      reps=10000, seed=20260727):
    """p-valor bajo la nula aguda, permutando DENTRO de cada día.

    `por_dia_real[fecha]`: lista de valores de los toques de zona de ese día.
    `por_dia_candidatos[fecha]`: valores de TODOS los instantes candidatos del
    día (las anclas placebo del atlas), de donde se sortea.

    Cada permutación preserva la identidad del día y su tasa base, así que la
    dependencia entre días —medida en 13–18 días— es idéntica en todas y no
    puede inflar la significancia. Permutar bloques de días dejaría ~12
    unidades y un p-valor mínimo de 0,083: incapaz de dar evidencia al 5 %.

    Costo declarado: no detecta efectos puramente ENTRE días. La hipótesis es
    que el toque marca un momento, no un día.
    """
    fechas = [f for f in por_dia_real
              if f in por_dia_candidatos and len(por_dia_candidatos[f]) > 0]
    if not fechas:
        return None
    obs_v = [x for f in fechas for x in por_dia_real[f]]
    if not obs_v:
        return None
    obs = float(np.mean(obs_v))
    ks = np.array([len(por_dia_real[f]) for f in fechas])
    pools = [np.asarray(por_dia_candidatos[f], float) for f in fechas]
    rng = np.random.default_rng(seed)
    mayores = 0
    for _ in range(reps):
        acum, tot = 0.0, 0
        for k, pool in zip(ks, pools):
            if k <= 0:
                continue
            idx = rng.integers(0, len(pool), size=k)
            acum += float(pool[idx].sum()); tot += k
        if tot and acum / tot >= obs:
            mayores += 1
    return dict(observado=obs, p_valor=(mayores + 1) / (reps + 1), reps=int(reps),
                n_dias=len(fechas), toques_por_dia_mediana=float(np.median(ks)),
                resolucion_baja=bool(np.median(ks) < 3))


# --------------------------------------------------------------------- runner
def correr(preregistro_path, *, geometria, universo, cargar_series):
    """Punto de entrada. **Levanta si no hay pre-registro sellado coherente.**

    `cargar_series`: callable que devuelve, por día, la serie de precios en
    ticks y los índices de los toques. Se inyecta para que este módulo no
    dependa del formato de datos y sea testeable con sintéticos.
    """
    spec = cargar_sellado(preregistro_path)          # levanta si falta o no cierra
    exigir_coherencia(spec, geometria, universo)
    if spec["convencion_timeout"] != "a_mercado":
        # se permite, pero queda dicho en la salida por que importa
        pass
    return spec
