"""LiqPool — zonas EQH/EQL (equal highs / equal lows), modelo de referencia.

Espejo Python de `nt8/LiqPoolZones.cs`. **Detección pura, sin outcomes.**

Portado del consenso de las implementaciones de referencia, comparadas en
`docs/research/H-LIQPOOL_FUENTES_COMPARADAS_2026-09-03.md`:

- **PyIndicators** `internal_external_liquidity_zones` modo `equal_hl` — pivotes
  consecutivos dentro de una tolerancia, y **tres estados** (activa / barrida /
  rota);
- **LuxAlgo EQH/EQL** — umbral de igualdad **relativo**, fusión de zonas vecinas,
  y el sweep definido en el **borde lejano** del cluster;
- **SMC-Liquidity-Hunter** — score por **toques + recencia**, que coincide con lo
  que mide arXiv 2101.07410: más toques previos ⇒ más rebote, con decaimiento.

## Las tres correcciones que trajo el porte

Las cuatro versiones anteriores de este módulo fallaban por lo mismo:

1. **La tolerancia es relativa, no fija en ticks.** Todas las referencias usan
   porcentaje del precio (0,1 %) o ATR. En ZB a 108 eso son ~3,5 ticks, no 1.
2. **El sweep se define en el borde LEJANO del cluster**, y separa **mecha** de
   **cierre**: mecha a través = cascada de stops sin aceptación; cierre a través =
   el nivel dejó de existir. Es la distinción que pide Osler (2003/2005).
3. **Los puntos son pivotes cortos**, no la mecha de cada vela ni pivotes de 3+
   barras a cada lado.

## Lo que NO se filtra nunca

Una zona barrida o rota **no se borra**: cambia de estado y sigue en el censo.
Borrarla deja en pantalla sólo las que «funcionaron», que es sesgo de
supervivencia y CLAUDE.md lo excluye como evidencia.

## Aritmética

Todo entero, en ticks. La tolerancia relativa se resuelve a un entero de ticks
por zona y se registra. Empates de pivote resueltos hacia la barra más temprana.
"""
from __future__ import annotations

NAME = "LiqPool"
VERSION = "2.0"

RESEARCH_DEFAULTS = dict(
    # --- puntos ---
    pivot_left=2,               # barras a la izquierda que el extremo debe dominar
    pivot_right=2,              # ...y a la derecha (confirma con este retardo)
    # --- igualdad ---
    eq_tolerance_pct=0.10,      # % del precio. 0,10 = LuxAlgo y SMC-Liquidity-Hunter
    eq_tolerance_ticks=0,       # si > 0, PISA al porcentaje (para pruebas)
    min_pivots=2,               # 2 = EQH/EQL clásico; 3+ = acumulación
    max_span_bars=500,          # barras máximas entre el primer y el último pivote
    merge_neighbours=True,      # zonas vecinas se fusionan (LuxAlgo)
    # --- ciclo de vida ---
    max_age_bars=0,             # 0 = sin expiración
    # --- contexto ---
    round_ticks=32,             # ZB: 32 ticks de 1/32 = 1 punto entero
    liquidity_band_ticks=2,     # banda de stops MÁS ALLÁ del borde lejano
)


def _params(overrides=None):
    p = dict(RESEARCH_DEFAULTS)
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


def tolerance_ticks(level_tick, params):
    """Tolerancia de igualdad, resuelta a ticks enteros.

    Relativa por defecto, como todas las referencias. Un valor fijo en ticks
    —`eq_tolerance_ticks`— la pisa, y existe sólo para poder contrastar.
    """
    p = _params(params)
    if int(p["eq_tolerance_ticks"]) > 0:
        return int(p["eq_tolerance_ticks"])
    return max(1, int(round(abs(int(level_tick)) * float(p["eq_tolerance_pct"]) / 100.0)))


def find_pivots(high_ticks, low_ticks, params=None):
    """Pivotes con longitudes izquierda y derecha separadas.

    Un máximo domina a `pivot_left` barras a la izquierda (con `>=`) y a
    `pivot_right` a la derecha (con `>`). La asimetría es deliberada: el `>=` a la
    izquierda deja pasar las mesetas, y el `>` a la derecha hace que el pivote
    caiga en la **última** barra de la meseta. Sin esa asimetría —exigiendo `>` a
    los dos lados, como `ta.pivothigh` de Pine— una meseta no produce **ningún**
    pivote, y con el tick grueso de ZB las mesetas son constantes.

    Que el pivote sea la última barra de la meseta también es lo correcto para
    esta familia: es la defensa **más reciente** del nivel.

    Causal: el pivote de la barra `i` se confirma `pivot_right` barras después.
    """
    p = _params(params)
    L, R = int(p["pivot_left"]), int(p["pivot_right"])
    n = len(high_ticks)
    out = []
    for i in range(L, n - R):
        h = high_ticks[i]
        if (all(h >= high_ticks[i - d] for d in range(1, L + 1))
                and all(h > high_ticks[i + d] for d in range(1, R + 1))):
            out.append((i, "H", int(h)))
        lo = low_ticks[i]
        if (all(lo <= low_ticks[i - d] for d in range(1, L + 1))
                and all(lo < low_ticks[i + d] for d in range(1, R + 1))):
            out.append((i, "L", int(lo)))
    return out


def build_zones(high_ticks, low_ticks, params=None):
    """Agrupa pivotes **consecutivos** del mismo tipo en zonas EQH/EQL.

    Consecutivos dentro de la tolerancia relativa, con la separación temporal
    acotada por `max_span_bars`. Si `merge_neighbours`, dos zonas del mismo lado
    cuyos rangos se tocan se funden en una, sumando los pivotes — es el «2x EQH»
    de LuxAlgo.

    El **borde lejano** de la zona es el pivote más extremo del cluster: el más
    alto en una EQH, el más bajo en una EQL. Ahí es donde se define el sweep.
    """
    p = _params(params)
    minp = int(p["min_pivots"])
    max_span = int(p["max_span_bars"])
    zonas = []
    for tipo in ("H", "L"):
        pivots = [x for x in find_pivots(high_ticks, low_ticks, p) if x[1] == tipo]
        i = 0
        while i < len(pivots):
            grupo = [pivots[i]]
            j = i + 1
            while j < len(pivots):
                tol = tolerance_ticks(grupo[-1][2], p)
                if (abs(pivots[j][2] - grupo[-1][2]) > tol
                        or pivots[j][0] - grupo[0][0] > max_span):
                    break
                grupo.append(pivots[j])
                j += 1
            if len(grupo) >= minp:
                zonas.append(_zona(grupo, tipo, p))
            i = j if j > i + 1 else i + 1
    if p["merge_neighbours"]:
        zonas = _fusionar(zonas)
    zonas.sort(key=lambda z: (z["created_bar"], z["far_edge_tick"]))
    return zonas


def _zona(grupo, tipo, p):
    barras = [g[0] for g in grupo]
    niveles = [g[2] for g in grupo]
    far = max(niveles) if tipo == "H" else min(niveles)
    near = min(niveles) if tipo == "H" else max(niveles)
    tol = tolerance_ticks(far, p)
    band = int(p["liquidity_band_ticks"])
    # la banda de stops va MÁS ALLÁ del borde lejano (Osler: los stops de quien
    # está posicionado en contra se apoyan del otro lado del nivel)
    if tipo == "H":
        band_lo, band_hi = far + 1, far + band
    else:
        band_lo, band_hi = far - band, far - 1
    rt = int(p["round_ticks"])
    m = (far % rt + rt) % rt if rt > 0 else 0
    return dict(
        side=tipo,
        far_edge_tick=int(far), near_edge_tick=int(near),
        band_lo=int(min(band_lo, band_hi)), band_hi=int(max(band_lo, band_hi)),
        tolerance_ticks=int(tol),
        n_pivots=len(grupo), pivot_bars=list(barras), pivot_levels=list(niveles),
        first_pivot_bar=int(barras[0]), created_bar=int(barras[-1]),
        span_bars=int(barras[-1] - barras[0]),
        round_confluence_ticks=int(min(m, rt - m)) if rt > 0 else None,
        # --- ciclo de vida y score, se completan en track_zones ---
        state="ACTIVE", swept_bar=None, broken_bar=None, expired_bar=None,
        touches=0, first_touch_bar=None, age_at_sweep=None,
    )


def _fusionar(zonas):
    """Funde zonas del mismo lado cuyos rangos se tocan («2x EQH» de LuxAlgo)."""
    out = []
    for z in sorted(zonas, key=lambda x: (x["side"], x["first_pivot_bar"])):
        anterior = out[-1] if out else None
        if (anterior and anterior["side"] == z["side"]
                and abs(z["far_edge_tick"] - anterior["far_edge_tick"])
                <= max(anterior["tolerance_ticks"], z["tolerance_ticks"])):
            anterior["n_pivots"] += z["n_pivots"]
            anterior["pivot_bars"] += z["pivot_bars"]
            anterior["pivot_levels"] += z["pivot_levels"]
            anterior["created_bar"] = max(anterior["created_bar"], z["created_bar"])
            anterior["span_bars"] = anterior["created_bar"] - anterior["first_pivot_bar"]
            if z["side"] == "H":
                anterior["far_edge_tick"] = max(anterior["far_edge_tick"], z["far_edge_tick"])
            else:
                anterior["far_edge_tick"] = min(anterior["far_edge_tick"], z["far_edge_tick"])
            continue
        out.append(dict(z))
    return out


def track_zones(high_ticks, low_ticks, close_ticks, zones, params=None):
    """Ciclo de vida con los **tres estados** de PyIndicators.

    - `SWEPT` — el precio atravesó el **borde lejano** con la mecha, sin cerrar
      más allá. Es la cascada de stops sin aceptación.
    - `BROKEN` — el precio **cerró** más allá del borde lejano. El nivel dejó de
      existir.
    - `EXPIRED` — venció por `max_age_bars` sin ser tocada.

    `touches` cuenta cuántas veces el precio volvió al nivel después de formarse,
    porque más toques previos ⇒ más probabilidad de rebote (arXiv 2101.07410) y es
    el ingrediente principal del score de SMC-Liquidity-Hunter.

    **Nada se borra.** Una zona barrida o rota cambia de estado y sigue en el censo.
    """
    p = _params(params)
    max_age = int(p["max_age_bars"])
    n = len(high_ticks)
    for z in zones:
        dentro = False
        for i in range(z["created_bar"] + 1, n):
            if max_age and (i - z["created_bar"]) > max_age:
                z["state"], z["expired_bar"] = "EXPIRED", i
                break
            tol = z["tolerance_ticks"]
            if z["side"] == "H":
                toca = high_ticks[i] >= z["far_edge_tick"] - tol
                rompe_mecha = high_ticks[i] > z["far_edge_tick"]
                rompe_cierre = close_ticks[i] > z["far_edge_tick"]
            else:
                toca = low_ticks[i] <= z["far_edge_tick"] + tol
                rompe_mecha = low_ticks[i] < z["far_edge_tick"]
                rompe_cierre = close_ticks[i] < z["far_edge_tick"]
            if toca and not dentro:
                z["touches"] += 1
                dentro = True
                if z["first_touch_bar"] is None:
                    z["first_touch_bar"] = i
            elif not toca:
                dentro = False
            if rompe_cierre:
                z["state"], z["broken_bar"] = "BROKEN", i
                if z["swept_bar"] is None:
                    z["swept_bar"] = i
                z["age_at_sweep"] = i - z["created_bar"]
                break
            if rompe_mecha and z["swept_bar"] is None:
                z["swept_bar"], z["state"] = i, "SWEPT"
                z["age_at_sweep"] = i - z["created_bar"]
    return zones


def detect(high_ticks, low_ticks, close_ticks, params=None):
    """Detección completa: zonas EQH/EQL con su ciclo de vida marcado."""
    return track_zones(high_ticks, low_ticks, close_ticks,
                       build_zones(high_ticks, low_ticks, params), params)


def census(zones):
    """Resumen del censo, **incluidas las que nunca fueron tocadas**."""
    if not zones:
        return dict(n=0)
    est = {}
    for z in zones:
        est[z["state"]] = est.get(z["state"], 0) + 1
    med = lambda v: sorted(v)[len(v) // 2]
    return dict(
        n=len(zones), por_estado=est,
        lado_H=sum(1 for z in zones if z["side"] == "H"),
        lado_L=sum(1 for z in zones if z["side"] == "L"),
        n_pivots_mediana=med([z["n_pivots"] for z in zones]),
        span_bars_mediana=med([z["span_bars"] for z in zones]),
        tolerancia_mediana=med([z["tolerance_ticks"] for z in zones]),
        toques_mediana=med([z["touches"] for z in zones]),
        nunca_tocadas=sum(1 for z in zones if z["first_touch_bar"] is None),
        nunca_barridas=sum(1 for z in zones if z["swept_bar"] is None),
    )
