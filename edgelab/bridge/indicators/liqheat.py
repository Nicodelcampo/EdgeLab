"""LiqHeat — mapa de intensidad de zonas por nivel de precio.

Espejo Python de `nt8/LiqHeatMap.cs`. **Target-free: no mira retornos.**

## La idea

En vez de dibujar cada zona por separado —que satura la pantalla— se **acumulan
por nivel de precio**. Cada nivel recibe la suma de los pesos de las zonas que lo
cubren, y se dibuja como una franja horizontal de ancho completo cuya **opacidad**
es esa intensidad.

Lo que se mira entonces no son las zonas: son los **huecos**. Un nivel con poca
acumulación es un tramo por el que el precio pasa sin resistencia.

## Cómo mueren las zonas — y cómo NO

**No mueren por distancia.** Es una decisión explícita: una zona lejos del precio
sigue siendo inventario en el libro; que el precio esté lejos no la consume.
Mueren **lenta y progresivamente** por dos vías:

- **tiempo** — decaimiento exponencial con `half_life_bars`. La literatura lo
  respalda: arXiv 2101.07410 mide que la probabilidad de rebote **decae con el
  tiempo**;
- **toques** — cada visita consume parte del inventario. `touch_decay` es el
  factor que queda después de cada toque.

    peso(zona) = peso_base · 2^(−edad / half_life) · touch_decay^toques

Una zona `BROKEN` —el precio cerró a través— aporta `broken_weight` del peso, por
defecto 0: dejó de existir.

## La calibración, resuelta por construcción

El problema de «sale demasiado claro o demasiado opaco» no se arregla adivinando
un número absoluto: la intensidad depende de cuántas zonas haya, y eso varía por
instrumento, resolución y momento. Se **normaliza contra un percentil** de las
intensidades vivas (`normalize_pct`, por defecto 95), así el mapa se autoescala.
`max_intensity` fuerza una escala fija si hace falta comparar entre corridas.

## Para qué sirve en EdgeLab

La hipótesis que habilita —*el precio atraviesa más rápido los niveles de baja
intensidad*— es **geométrica y target-free**: se mide con velocidad de cruce, no
con P&L. `crossing_speed` da esa medición directamente.

## Cómo podría refutarse

Si la velocidad de cruce no depende de la intensidad, el mapa es decoración: está
mostrando dónde hubo zonas, no dónde el precio encuentra resistencia.
"""
from __future__ import annotations

import math

NAME = "LiqHeat"
VERSION = "1.0"

RESEARCH_DEFAULTS = dict(
    half_life_bars=500,      # decaimiento por tiempo; 0 = sin decaimiento
    touch_decay=0.70,        # factor que queda tras cada toque
    broken_weight=0.0,       # peso de una zona rota (cierre a través)
    swept_weight=0.5,        # peso de una zona barrida (mecha a través)
    weight_by_pivots=True,   # una zona de 4 pivotes pesa el doble que una de 2
    normalize_pct=95,        # percentil de intensidad que mapea a opacidad máxima
    max_intensity=0.0,       # > 0 fuerza escala fija en vez del percentil
)


def _params(overrides=None):
    p = dict(RESEARCH_DEFAULTS)
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


def zone_weight(zone, at_bar, params=None):
    """Peso de una zona en la barra `at_bar`. Decae por tiempo y por toques.

    **Nunca decae por distancia al precio**: una zona lejana sigue siendo
    inventario en el libro, y que el precio esté lejos no la consume.
    """
    p = _params(params)
    edad = int(at_bar) - int(zone["created_bar"])
    if edad < 0:
        return 0.0
    w = float(zone.get("n_pivots", 1)) if p["weight_by_pivots"] else 1.0
    hl = float(p["half_life_bars"])
    if hl > 0:
        w *= math.pow(0.5, edad / hl)
    w *= math.pow(float(p["touch_decay"]), int(zone.get("touches", 0)))
    estado = zone.get("state", "ACTIVE")
    if estado == "BROKEN":
        w *= float(p["broken_weight"])
    elif estado == "SWEPT":
        w *= float(p["swept_weight"])
    return w


def zone_span(zone):
    """Rango de ticks que la zona ocupa: el nivel más su banda de liquidez."""
    bordes = [zone["far_edge_tick"], zone.get("near_edge_tick", zone["far_edge_tick"])]
    if zone.get("band_lo") is not None:
        bordes += [zone["band_lo"], zone["band_hi"]]
    return int(min(bordes)), int(max(bordes))


def intensity_map(zones, at_bar, params=None):
    """Intensidad por tick en la barra `at_bar`. Devuelve `{tick: intensidad}`.

    Sólo entran las zonas ya creadas. El mapa es el **estado actual**: por eso las
    franjas ocupan todo el ancho de la pantalla en vez de arrancar donde nació
    cada zona.
    """
    p = _params(params)
    mapa = {}
    for z in zones:
        if z["created_bar"] > at_bar:
            continue
        w = zone_weight(z, at_bar, p)
        if w <= 0:
            continue
        lo, hi = zone_span(z)
        for t in range(lo, hi + 1):
            mapa[t] = mapa.get(t, 0.0) + w
    return mapa


def normalize(mapa, params=None):
    """Escala la intensidad a 0..1 contra un percentil, no contra un absoluto.

    Es la respuesta al problema de calibración: el número de zonas vivas cambia
    con el instrumento, la resolución y el momento, así que una escala fija sale
    siempre demasiado clara o demasiado opaca. El percentil hace que el mapa se
    autoescale. `max_intensity > 0` fuerza la escala fija cuando hace falta
    comparar dos corridas entre sí.
    """
    p = _params(params)
    if not mapa:
        return {}
    if float(p["max_intensity"]) > 0:
        tope = float(p["max_intensity"])
    else:
        vals = sorted(mapa.values())
        idx = min(len(vals) - 1, int(len(vals) * float(p["normalize_pct"]) / 100.0))
        tope = vals[idx]
    if tope <= 0:
        return {t: 0.0 for t in mapa}
    return {t: min(1.0, v / tope) for t, v in mapa.items()}


def crossing_speed(high_ticks, low_ticks, zones, params=None, sample_every=25):
    """Velocidad de cruce por nivel de intensidad. **Target-free.**

    Es la medición que la idea habilita: *«el precio atraviesa fácil los huecos»*.
    Por cada barra muestreada, se mira cuántas barras tarda el precio en recorrer
    cada tick que atraviesa, y se agrupa por la intensidad de ese tick.

    No usa retornos ni P&L: cuenta barras por tick recorrido. Si la velocidad no
    depende de la intensidad, el mapa no informa.
    """
    p = _params(params)
    n = len(high_ticks)
    acumulado = {}          # decil de intensidad -> [ticks recorridos, barras]
    for b in range(sample_every, n - sample_every, sample_every):
        mapa = normalize(intensity_map(zones, b, p), p)
        if not mapa:
            continue
        lo = min(low_ticks[b:b + sample_every])
        hi = max(high_ticks[b:b + sample_every])
        for t in range(int(lo), int(hi) + 1):
            d = min(9, int(mapa.get(t, 0.0) * 10))
            e = acumulado.setdefault(d, [0, 0])
            e[0] += 1
            e[1] += sample_every
    return {str(d): dict(ticks=v[0], barras=v[1],
                         barras_por_tick=round(v[1] / v[0], 3) if v[0] else None)
            for d, v in sorted(acumulado.items())}
