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
    point_mode="bar_extreme",   # "bar_extreme" = cada vela aporta su mecha (default)
                                # "pivot" = sólo extremos que dominan K barras
    pivot_strength=3,           # sólo aplica en point_mode="pivot"
    min_pivots=3,               # escalones mínimos de la cadena
    touch_tolerance_ticks=1,    # cuán cerca del nivel tiene que estar un punto para contar
    max_slope_ticks=1,          # deriva máxima del nivel cada `slope_per_bars` barras
    slope_per_bars=50,          # ...la escalera no puede ser empinada
    max_total_drift_ticks=8,    # deriva total máxima de la cadena entera
    max_step_bars=400,          # barras máximas SIN un toque nuevo antes de cerrar
    max_step_ticks=4,           # (legado) salto máximo entre escalones
    allow_equal_steps=True,     # un escalón plano no rompe la cadena
    only_compressing_chains=True,   # ver build_chains: sólo dos de las cuatro
    level_tolerance_ticks=1,    # (legado) tolerancia de nivel
    liquidity_band_ticks=2,     # ancho de la banda MÁS ALLÁ del nivel (stops)
    zone_height_ticks=1,        # grosor del nivel mismo (take-profit)
    max_age_bars=0,             # 0 = sin expiración
    invalidation_ticks=8,       # cuánto debe atravesar para considerarse barrida.
                                # 4 era demasiado poco: ZB recorre ~26 ticks por
                                # sesión, así que casi toda zona quedaba barrida
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


def points(high_ticks, low_ticks, tipo, params=None):
    """Los **puntos** de la serie: por defecto, la mecha de cada vela.

    Corrección de Nico: *«un punto sería una mecha o el extremo de una vela»*. La
    versión anterior sólo tomaba pivotes que dominaran `pivot_strength` barras a
    cada lado, y con eso tiraba casi todos los puntos y se quedaba con unos pocos
    dispersos — por eso las cadenas no se parecían a las que él traza.

    `point_mode="pivot"` conserva el comportamiento viejo, para poder contrastar.
    """
    p = _params(params)
    if p["point_mode"] == "pivot":
        return [(b, v) for b, tp, v in find_pivots(high_ticks, low_ticks,
                                                   p["pivot_strength"]) if tp == tipo]
    serie = high_ticks if tipo == "H" else low_ticks
    return [(i, int(v)) for i, v in enumerate(serie)]


def build_chains(high_ticks, low_ticks, params=None):
    """Cadenas de puntos sobre un nivel: seguidillas, serruchos y escaleras suaves.

    ## La regla, con las tres correcciones de Nico incorporadas

    1. **Un punto es la mecha de una vela**, no un pivote de K barras.
    2. **Lo que corta la cadena es romper el nivel**, no alejarse de él. En un
       soporte, un mínimo que baja más de `touch_tolerance_ticks` por debajo la
       corta; que el precio se vaya para arriba y vuelva **no corta nada** — es
       exactamente el caso donde una línea une dos grupos de mínimos separados por
       un tramo alto.
    3. **La escalera no puede ser empinada.** El nivel puede derivar, pero como
       máximo `max_slope_ticks` cada `slope_per_bars` barras, y
       `max_total_drift_ticks` en total.

    Con eso, las tres formas son la misma cadena con distinta deriva:

    | forma | deriva |
    |---|---|
    | serrucho / seguidilla | 0 |
    | escalera suave | pequeña, dentro del límite |
    | escalera empinada | excede el límite → **no es zona** |

    Y sólo dos de las cuatro combinaciones cuentan: mínimos que suben o se
    mantienen (soporte) y máximos que bajan o se mantienen (resistencia).
    `only_compressing_chains` descarta las otras dos, que son la tendencia misma.

    Causal: cada punto está disponible al cerrar su vela.
    """
    p = _params(params)
    tol = int(p["touch_tolerance_ticks"])
    max_gap = int(p["max_step_bars"])
    minp = int(p["min_pivots"])
    slope, per = int(p["max_slope_ticks"]), int(p["slope_per_bars"])
    max_drift = int(p["max_total_drift_ticks"])
    solo_comp = bool(p["only_compressing_chains"])
    cadenas = []
    for tipo in ("H", "L"):
        pts = points(high_ticks, low_ticks, tipo, p)
        n = len(pts)
        sig = -1 if tipo == "H" else 1          # dirección que comprime
        i = 0
        while i < n:
            b0, v0 = pts[i]
            nivel = v0
            toques = [(b0, v0)]
            j = i + 1
            while j < n:
                b, v = pts[j]
                if b - toques[-1][0] > max_gap:
                    break
                rompe = (v > nivel + tol) if tipo == "H" else (v < nivel - tol)
                if rompe:
                    break                        # rompe el nivel: cierra la cadena
                cerca = abs(v - nivel) <= tol
                if cerca:
                    # deriva permitida: ni empinada ni acumulada de más
                    d_total = v - v0
                    d_span = b - b0
                    empinada = (abs(d_total) * per > slope * max(d_span, 1)
                                and abs(d_total) > slope)
                    if abs(d_total) > max_drift or empinada:
                        break
                    if solo_comp and d_total != 0 and (d_total > 0) != (sig > 0):
                        break
                    toques.append((b, v))
                    nivel = v                    # el nivel sigue al último toque
                j += 1
            if len(toques) >= minp:
                niveles = [x[1] for x in toques]
                direccion = 0
                if niveles[-1] != niveles[0]:
                    direccion = 1 if niveles[-1] > niveles[0] else -1
                grupo = [(b, tipo, v) for b, v in toques]
                cadenas.append(_cerrar(grupo, tipo, direccion,
                                       high_ticks, low_ticks, p))
                i = toques[-1][0] + 1 if toques[-1][0] > b0 else i + 1
            else:
                i += 1
    cadenas.sort(key=lambda z: (z["created_bar"], z["level_tick"]))
    return cadenas


# alias: el nombre viejo seguía diciendo "zonas", pero el objeto es una cadena
build_zones = build_chains


def _cerrar(grupo, tipo, direccion, high_ticks, low_ticks, p):
    barras = [g[0] for g in grupo]
    niveles = [g[2] for g in grupo]
    a, b = barras[0], barras[-1]
    if b > a:
        exc = int(max(high_ticks[a:b + 1]) - min(low_ticks[a:b + 1]))
    else:
        exc = 0
    # El nivel operativo de la cadena es su ÚLTIMO escalón: es el que sigue
    # vigente. Los anteriores ya fueron superados por la propia escalera.
    nivel = int(niveles[-1])
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
    pasos = [niveles[k + 1] - niveles[k] for k in range(len(niveles) - 1)]
    return dict(
        side=tipo,
        direction=int(direccion),                 # +1 escalera ascendente, -1 descendente
        level_tick=nivel,
        level_lo=int(lvl_lo), level_hi=int(lvl_hi),
        band_lo=int(band_lo), band_hi=int(band_hi),
        n_pivots=len(grupo), pivot_bars=list(barras), pivot_levels=list(niveles),
        step_ticks=pasos,
        total_drop_ticks=int(abs(niveles[-1] - niveles[0])),
        flat_steps=sum(1 for x in pasos if x == 0),
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
                       build_chains(high_ticks, low_ticks, params), params)


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
