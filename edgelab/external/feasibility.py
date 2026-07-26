# -*- coding: utf-8 -*-
"""Costo de cómputo del precomputado, ANTES de gastarlo. Target-free.

Un feature que no se puede computar sobre el rango de backtest no es un feature,
es una idea. Este módulo contesta eso en un segundo en vez de descubrirlo a las
seis horas de un precomputado que no termina.

El caso que motiva: 2 años de MNQ de 1 minuto ≈ 700k barras. A 30 caminos Monte
Carlo y ~2 s por llamada, correrlo bar-a-bar son **~16 días de cómputo**. La
conclusión no es "no se puede" sino "no se puede *así*" — y las tres salidas
(cadencia, muestreo por evento, resolución más gruesa) tienen costos muy
distintos que conviene comparar con números y no con intuición.
"""
from __future__ import annotations

SEG_POR_DIA = 86400.0


def estimar(n_bars, *, s_por_llamada, cadencia_bars=1, n_eventos=None,
            paralelismo=1):
    """Costo del precomputado bajo una política de muestreo.

    `cadencia_bars`  predecir cada N barras (1 = todas).
    `n_eventos`      si se da, ignora la cadencia: predecir sólo en esos N
                     instantes (p.ej. cuando nace una zona). Es la política más
                     barata y la más alineada con el proyecto — las zonas ya son
                     el evento de interés.
    `paralelismo`    llamadas concurrentes (batch en GPU, procesos en CPU).
    """
    if n_eventos is not None:
        llamadas = int(n_eventos)
        politica = "por evento (n=%d)" % n_eventos
    else:
        llamadas = max(1, int(n_bars // max(1, cadencia_bars)))
        politica = ("todas las barras" if cadencia_bars == 1
                    else "cada %d barras" % cadencia_bars)
    seg = llamadas * float(s_por_llamada) / max(1, int(paralelismo))
    return dict(politica=politica, llamadas=llamadas, segundos=seg,
                horas=seg / 3600.0, dias=seg / SEG_POR_DIA,
                viable_en_una_noche=seg <= 8 * 3600.0)


def comparar(n_bars, s_por_llamada, *, cadencias=(1, 5, 15, 60),
             n_eventos=None, paralelismo=1):
    """Tabla de políticas, de la más cara a la más barata."""
    filas = [estimar(n_bars, s_por_llamada=s_por_llamada, cadencia_bars=c,
                     paralelismo=paralelismo) for c in cadencias]
    if n_eventos is not None:
        filas.append(estimar(n_bars, s_por_llamada=s_por_llamada,
                             n_eventos=n_eventos, paralelismo=paralelismo))
    return sorted(filas, key=lambda r: -r["segundos"])


def formatear(filas, titulo=""):
    L = []
    if titulo:
        L.append(titulo)
    L.append("%-26s %12s %10s %8s  %s" % ("politica", "llamadas", "horas",
                                          "dias", "una noche?"))
    for r in filas:
        L.append("%-26s %12d %10.2f %8.2f  %s"
                 % (r["politica"], r["llamadas"], r["horas"], r["dias"],
                    "si" if r["viable_en_una_noche"] else "NO"))
    return "\n".join(L)


def staleness_de_cadencia(cadencia_bars, bar_ns):
    """Cuán vieja llega a estar la predicción con una cadencia dada.

    Es el número que hay que pasarle a `PITFeatureStore.series(max_staleness_ns=…)`.
    Predecir cada 15 barras y después tratar el valor como fresco durante 15
    barras es una decisión, y conviene que sea explícita: en régimen cambiante,
    una `sigma_pred` de hace 15 minutos puede describir otro mundo.
    """
    return int(cadencia_bars) * int(bar_ns)


def presupuesto_inverso(horas_disponibles, s_por_llamada, paralelismo=1):
    """Cuántas llamadas entran en el tiempo que hay. La pregunta al revés.

    Útil para decidir la cadencia a partir del presupuesto real en vez de
    elegir una cadencia y descubrir que no entra.
    """
    return int(horas_disponibles * 3600.0 * max(1, paralelismo)
               / max(1e-9, float(s_por_llamada)))
