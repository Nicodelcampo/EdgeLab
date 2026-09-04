"""LiqPool — zonas de máximos/mínimos repetidos («acumulación de liquidez»).

Espejo Python de `nt8/LiqPoolZones.cs`. Detección pura, sin outcomes.

## Qué marca, y por qué así

Un **pivote** es un extremo que domina estrictamente a `pivot_strength` barras de
cada lado. Varios pivotes del mismo tipo a distancia ≤ `level_tolerance_ticks`
forman una **zona**.

La zona tiene **dos partes**, y la separación viene de la literatura, no del gusto
(`docs/research/H-LIQPOOL-ZB_ESTADO_DEL_ARTE_2026-09-03.md`):

- el **nivel** — donde Osler documenta que se agrupan los *take-profit*, y por lo
  tanto donde el precio tiende a **rebotar**;
- la **banda de liquidez** — `liquidity_band_ticks` **más allá** del nivel, donde
  se apoyan los *stop-loss* de quien está posicionado contra el movimiento, y por
  lo tanto donde el precio tiende a **acelerar** si la atraviesa.

Los dos mecanismos tienen efecto **opuesto**. Un detector que marca una sola línea
los mezcla y después no se pueden separar. Por eso se exportan por separado.

## Lo que se registra y nunca se filtra

- `n_pivots` — la literatura (arXiv 2101.07410) encuentra que **más toques previos
  ⇒ más probabilidad de rebote**, así que el conteo es información, no un umbral.
- `span_bars` y `excursion_ticks` — separan la **microzona** (picos juntos en el
  tiempo, poco recorrido entre ellos) de la **zona separada** (picos lejanos con
  recorrido sustancial). Son los dos ejes que distinguió Nico. **Se registran para
  estratificar, no para filtrar**: filtrar de entrada congela una población sin
  haber visto el landscape.
- `age_bars` al momento de cada evento — el mismo paper mide que el efecto **decae
  con el tiempo**.
- `round_confluence` — distancia al número redondo más cercano, porque ahí es
  donde Osler documenta la concentración de órdenes.

## La regla que evita el sesgo que arruina esto

**Una zona tocada NO se borra.** Se marca `touched`, `swept` o `expired` y sigue
en el censo. Borrarla al ser mitigada produce exactamente el sesgo de
supervivencia que CLAUDE.md prohíbe usar como evidencia: en pantalla sobreviven
sólo las que «funcionaron».

## Aritmética

Todo entero, en ticks. Sin mediana, sin percentil histórico, sin reloj entre
ticks. Empates deterministas por precio ascendente. Cumple
`PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md`.

## Cómo podría refutarse la utilidad del detector

Si al barrer `pivot_strength` × `level_tolerance_ticks` × `min_pivots` el censo no
cambia de tamaño de forma monótona, los parámetros no están controlando lo que
dicen controlar. Y si las zonas detectadas no se distinguen de niveles de control
con la misma geometría, el objeto no aporta — que es exactamente como murió
`BIGTRAP2_MAGNET_LINE_CLOSED`.
"""
from __future__ import annotations

NAME = "LiqPool"
VERSION = "1.0"

RESEARCH_DEFAULTS = dict(
    pivot_strength=3,           # barras a cada lado que el extremo debe dominar
    level_tolerance_ticks=1,    # cuánto pueden diferir dos picos y ser el mismo nivel
    min_pivots=2,               # 2 = par de picos; 3+ = acumulación
    liquidity_band_ticks=2,     # ancho de la banda MÁS ALLÁ del nivel (stops)
    zone_height_ticks=1,        # grosor del nivel mismo (take-profit)
    max_age_bars=0,             # 0 = sin expiración
    invalidation_ticks=4,       # cuánto debe atravesar para considerarse barrida
    round_ticks=32,             # cada cuántos ticks hay un "número redondo" (ZB: 32 = 1 punto)
)


def _params(overrides=None):
    p = dict(RESEARCH_DEFAULTS)
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


def find_pivots(high_ticks, low_ticks, strength):
    """Pivotes estrictos. Devuelve [(bar, tipo, precio)] con tipo 'H' o 'L'.

    Estricto a los dos lados: un extremo empatado con un vecino NO es pivote. Es
    deliberado — con el tick grueso de ZB los empates son frecuentes, y aceptarlos
    haría que un tramo plano genere pivotes en cada barra.
    """
    K = int(strength)
    n = len(high_ticks)
    out = []
    for i in range(K, n - K):
        h = high_ticks[i]
        if all(h > high_ticks[i - d] and h > high_ticks[i + d] for d in range(1, K + 1)):
            out.append((i, "H", int(h)))
        lo = low_ticks[i]
        if all(lo < low_ticks[i - d] and lo < low_ticks[i + d] for d in range(1, K + 1)):
            out.append((i, "L", int(lo)))
    return out


def build_zones(high_ticks, low_ticks, params=None):
    """Agrupa pivotes en zonas. Sin outcomes: sólo detección.

    Una zona se cierra cuando aparece un pivote del mismo tipo fuera de la
    tolerancia. El agrupamiento es **secuencial en el tiempo**, no un clustering
    global: así la zona existe desde su último pivote y no usa información futura.
    """
    p = _params(params)
    tol = int(p["level_tolerance_ticks"])
    zonas = []
    for tipo in ("H", "L"):
        pivots = [x for x in find_pivots(high_ticks, low_ticks, p["pivot_strength"])
                  if x[1] == tipo]
        grupo = []
        for piv in pivots:
            if grupo and abs(piv[2] - grupo[-1][2]) <= tol:
                grupo.append(piv)
                continue
            if len(grupo) >= int(p["min_pivots"]):
                zonas.append(_cerrar(grupo, tipo, high_ticks, low_ticks, p))
            grupo = [piv]
        if len(grupo) >= int(p["min_pivots"]):
            zonas.append(_cerrar(grupo, tipo, high_ticks, low_ticks, p))
    zonas.sort(key=lambda z: (z["created_bar"], z["level_tick"]))
    return zonas


def _cerrar(grupo, tipo, high_ticks, low_ticks, p):
    barras = [g[0] for g in grupo]
    niveles = [g[2] for g in grupo]
    a, b = barras[0], barras[-1]
    # recorrido del precio ENTRE el primer y el último pico: el eje que separa la
    # microzona de la zona separada
    if b > a:
        exc = int(max(high_ticks[a:b + 1]) - min(low_ticks[a:b + 1]))
    else:
        exc = 0
    nivel = max(niveles) if tipo == "H" else min(niveles)
    band = int(p["liquidity_band_ticks"])
    h = int(p["zone_height_ticks"])
    if tipo == "H":
        lvl_lo, lvl_hi = nivel - h, nivel
        band_lo, band_hi = nivel + 1, nivel + band
    else:
        lvl_lo, lvl_hi = nivel, nivel + h
        band_lo, band_hi = nivel - band, nivel - 1
    rt = int(p["round_ticks"])
    dist_redondo = min(nivel % rt, rt - (nivel % rt)) if rt > 0 else None
    return dict(
        side=tipo, level_tick=int(nivel),
        level_lo=int(lvl_lo), level_hi=int(lvl_hi),
        band_lo=int(band_lo), band_hi=int(band_hi),
        n_pivots=len(grupo), pivot_bars=list(barras), pivot_levels=list(niveles),
        first_pivot_bar=int(a), created_bar=int(b),
        span_bars=int(b - a), excursion_ticks=exc,
        round_confluence_ticks=dist_redondo,
        state="ACTIVE", touched_bar=None, swept_bar=None, expired_bar=None,
    )


def track_zones(high_ticks, low_ticks, zones, params=None):
    """Recorre las barras posteriores y marca el ciclo de vida. NO borra nada.

    `touched` = el precio entró en el nivel. `swept` = lo atravesó más allá de
    `invalidation_ticks` (la banda de liquidez quedó consumida). `expired` = venció
    por `max_age_bars` sin ser tocada.

    Las tres se conservan en el censo. Las expiradas son las que el ojo nunca
    registra y las que hacen que el censo no esté seleccionado por resultado.
    """
    p = _params(params)
    inval = int(p["invalidation_ticks"])
    max_age = int(p["max_age_bars"])
    n = len(high_ticks)
    for z in zones:
        for i in range(z["created_bar"] + 1, n):
            if max_age and (i - z["created_bar"]) > max_age:
                z["state"], z["expired_bar"] = "EXPIRED", i
                break
            if z["side"] == "H":
                if z["touched_bar"] is None and high_ticks[i] >= z["level_lo"]:
                    z["touched_bar"], z["state"] = i, "TOUCHED"
                if high_ticks[i] >= z["level_tick"] + inval:
                    z["swept_bar"], z["state"] = i, "SWEPT"
                    break
            else:
                if z["touched_bar"] is None and low_ticks[i] <= z["level_hi"]:
                    z["touched_bar"], z["state"] = i, "TOUCHED"
                if low_ticks[i] <= z["level_tick"] - inval:
                    z["swept_bar"], z["state"] = i, "SWEPT"
                    break
    return zones


def detect(high_ticks, low_ticks, params=None):
    """Detección completa: zonas con su ciclo de vida marcado."""
    return track_zones(high_ticks, low_ticks,
                       build_zones(high_ticks, low_ticks, params), params)


def census(zones):
    """Resumen del censo, incluidas las que nunca fueron tocadas."""
    if not zones:
        return dict(n=0)
    est = {}
    for z in zones:
        est[z["state"]] = est.get(z["state"], 0) + 1
    piv = sorted(z["n_pivots"] for z in zones)
    span = sorted(z["span_bars"] for z in zones)
    exc = sorted(z["excursion_ticks"] for z in zones)
    med = lambda v: v[len(v) // 2]
    return dict(n=len(zones), por_estado=est,
                lado_H=sum(1 for z in zones if z["side"] == "H"),
                lado_L=sum(1 for z in zones if z["side"] == "L"),
                n_pivots_mediana=med(piv), n_pivots_max=piv[-1],
                span_bars_mediana=med(span), excursion_ticks_mediana=med(exc),
                nunca_tocadas=sum(1 for z in zones if z["touched_bar"] is None))
