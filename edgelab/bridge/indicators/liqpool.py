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
    min_pivots=3,               # escalones mínimos de la cadena
    max_step_ticks=4,           # salto máximo de precio entre escalones consecutivos
    max_step_bars=200,          # separación máxima en barras entre escalones
    allow_equal_steps=True,     # un escalón plano no rompe la cadena
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


def build_chains(high_ticks, low_ticks, params=None):
    """Cadenas escalonadas monótonas de pivotes consecutivos.

    ## Qué es el objeto, corregido

    La primera versión buscaba **picos al mismo precio** (máximos iguales). Está
    mal: lo que Nico marca a mano son **escaleras** — pivotes consecutivos que van
    bajando (o subiendo) escalón por escalón, con tramos planos donde dos picos
    coinciden. Él lo había dicho: *«picos con una consecución creciente o
    decreciente»*; el error fue leer «cercana» como «mismo nivel».

    Una cadena es un run **maximal** de pivotes consecutivos del mismo tipo donde:

    - la dirección no se invierte: en una cadena descendente de máximos, ningún
      pico **supera** al anterior. El pico que lo supera **corta la cadena** — es
      literalmente el criterio que dio Nico;
    - el salto entre escalones no excede `max_step_ticks` (los picos son
      «muy cercanos» en precio);
    - la separación entre escalones no excede `max_step_bars`.

    Un escalón **plano** (mismo precio que el anterior) no rompe la cadena si
    `allow_equal_steps`: es el caso de los máximos iguales, que ahora queda como
    un caso particular de la escalera y no como el objeto entero.

    Es causal: cada pivote se confirma `pivot_strength` barras después, y la
    cadena sólo existe hasta su último escalón confirmado.
    """
    p = _params(params)
    max_step = int(p["max_step_ticks"])
    max_gap = int(p["max_step_bars"])
    minp = int(p["min_pivots"])
    eq = bool(p["allow_equal_steps"])
    todos = find_pivots(high_ticks, low_ticks, p["pivot_strength"])
    cadenas = []
    for tipo in ("H", "L"):
        pivots = [x for x in todos if x[1] == tipo]
        i = 0
        while i < len(pivots):
            cadena = [pivots[i]]
            direccion = 0                 # +1 sube, -1 baja, 0 aún sin definir
            j = i + 1
            while j < len(pivots):
                prev, cur = cadena[-1], pivots[j]
                paso = cur[2] - prev[2]
                if cur[0] - prev[0] > max_gap or abs(paso) > max_step:
                    break
                if paso == 0:
                    if not eq:
                        break
                elif direccion == 0:
                    direccion = 1 if paso > 0 else -1
                elif (paso > 0) != (direccion > 0):
                    break                 # este pico SUPERA al anterior: corta
                cadena.append(cur)
                j += 1
            if len(cadena) >= minp:
                cadenas.append(_cerrar(cadena, tipo, direccion,
                                       high_ticks, low_ticks, p))
            # las cadenas no se solapan: la siguiente arranca donde ésta terminó
            i = max(j, i + 1)
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
