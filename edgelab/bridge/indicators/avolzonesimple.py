"""AVolZoneSimple — zonas de volumen, definición simple y estable.

Reemplaza la maquinaria de aVolClusterPOI (mediana × multiplicador → celdas hot →
clustering por gap → percentil histórico por franja horaria) por **una sola
definición geométrica**:

    la zona es el rango de precios MÁS ANGOSTO que concentra S % del volumen
    del bloque, y se publica sólo si su concentración supera un umbral.

## Por qué

Medido sobre los 22.507 bloques reales de NQ 06-26 120t
(`docs/research/avolcluster_decision_rule_20260903/`):

- la regla vieja tenía, en el **89,60 %** de los bloques, una celda a **un
  contrato** del umbral `mediana × 2`. Un contrato de diferencia entre NT8 y el
  parquet cambiaba la zona;
- su turnover bajo ruido de ±1 contrato era **30,87 %**, y ninguna variante de la
  regla de selección bajaba del 22 %;
- esta definición da **4,97 %** con los defaults de abajo, cumpliendo el
  `PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md`, y conserva la altura mediana
  de zona (9 ticks contra 9 de la regla vieja).

La razón es estructural: un umbral sobre celdas individuales tiene un borde que
un contrato cruza; una **suma sobre muchas celdas** no lo tiene.

## Qué se eliminó, y qué se gana

- **La mediana y el multiplicador**: no hay umbral por celda.
- **El clustering por gap**: la zona es un intervalo contiguo por construcción,
  así que no puede fusionarse ni partirse por una celda marginal.
- **El percentil histórico por franja horaria y sesión**: era estado acumulado
  entre bloques y sesiones — la causa de que el indicador marcara muchas zonas en
  un momento y ninguna en otro, sin que el mercado cambiara. Lo reemplaza un
  umbral **fijo y declarado** de concentración.

Sin estado histórico, cada bloque se decide solo. Eso hace el indicador
reproducible barra a barra, comparable entre instrumentos y **barrible**: cuatro
parámetros, todos enteros y monótonos.

## Aritmética

Todo entero, sin floats en la decisión (regla 1 del contrato de paridad):

    necesario   = techo(volumen_bloque * share_pct / 100)
    concentracion = volumen_zona * ancho_bloque * 1000 / (volumen_bloque * ancho_zona)

`concentracion == 1000` significa «tan concentrada como el reparto uniforme del
bloque»; 2000, el doble. Es adimensional, así que el mismo umbral significa lo
mismo en NQ, ES o GC — pero **eso no autoriza a transportar costos ni resultados
entre instrumentos**, sólo hace comparable la escala del parámetro.

## Justificación económica

Una zona de volumen es una hipótesis sobre dónde quedó inventario que puede
reaccionar. Si la zona se mueve porque un contrato cruzó un umbral, no se está
midiendo el mercado sino el ruido del feed, y ningún barrido sobre esa familia
produce un resultado promovible.

## Cómo podría refutarse

Si al barrer `area_share_pct` × `max_zone_ticks` × `min_concentration` el
landscape resulta plano —todas las celdas dan lo mismo— la definición no
discrimina y la zona no aporta información sobre la ubicación del precio. Y si
las zonas que publica no coinciden en absoluto con las de `aVolClusterPOI` sobre
el mismo chart, la premisa «misma funcionalidad, más estable» es falsa.
"""
from __future__ import annotations

NAME = "AVolZoneSimple"
VERSION = "1.0"

RESEARCH_DEFAULTS = dict(
    bars_per_block=10,        # barras que forman un bloque
    area_share_pct=30,        # % del volumen del bloque que define la zona
    max_zone_ticks=12,        # ancho máximo admitido, en ticks
    min_concentration=1500,   # 1000 = uniforme; 1500 = 1,5x
)


def _params(overrides=None):
    p = dict(RESEARCH_DEFAULTS)
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


def narrowest_area(cells, area_share_pct, max_zone_ticks):
    """Rango contiguo más angosto que concentra `area_share_pct`% del volumen.

    Empates de ancho se rompen por MAYOR volumen, y si también empatan, por
    precio ascendente — determinista, sin depender del orden del diccionario.
    Devuelve `(lower, upper, vol_zona, vol_bloque, ancho_bloque)` o None.
    """
    if not cells:
        return None
    ticks = sorted(cells)
    vols = [int(cells[t]) for t in ticks]
    total = sum(vols)
    if total <= 0:
        return None
    need = -(-total * int(area_share_pct) // 100)     # techo entero
    n = len(ticks)
    pre = [0] * (n + 1)
    for i, v in enumerate(vols):
        pre[i + 1] = pre[i] + v

    best = None            # (ancho, -volumen, lower, upper)
    j = 0
    for i in range(n):
        if j < i:
            j = i
        while j < n and pre[j + 1] - pre[i] < need:
            j += 1
        if j >= n:
            break
        width = ticks[j] - ticks[i] + 1
        if width > int(max_zone_ticks):
            continue
        cand = (width, -(pre[j + 1] - pre[i]), ticks[i], ticks[j])
        if best is None or cand < best:
            best = cand
    if best is None:
        return None
    _w, negv, lo, hi = best
    return lo, hi, -negv, total, ticks[-1] - ticks[0] + 1


def concentration(zone_vol, block_vol, zone_ticks, block_ticks):
    """1000 = tan concentrada como el reparto uniforme del bloque. División entera."""
    if block_vol <= 0 or zone_ticks <= 0:
        return 0
    return (int(zone_vol) * int(block_ticks) * 1000) // (int(block_vol) * int(zone_ticks))


def detect_block(cells, params=None, close_tick=None):
    """Decide un bloque. Sin estado, sin historia: mismo input, mismo output.

    Devuelve siempre un registro con la decisión y todo lo que la produjo, para
    que el bloque sea auditable aunque no se publique zona.
    """
    p = _params(params)
    rec = dict(decision="ABSTAIN_NO_CELLS", lower_tick=None, upper_tick=None,
               zone_ticks=None, zone_volume=None, block_volume=None,
               block_ticks=None, concentration=None, side=None, distance_ticks=None,
               params=p)
    if len(cells) < 2:
        return rec
    area = narrowest_area(cells, p["area_share_pct"], p["max_zone_ticks"])
    rec["block_volume"] = int(sum(int(v) for v in cells.values()))
    ordered = sorted(cells)
    rec["block_ticks"] = int(ordered[-1] - ordered[0] + 1)
    if area is None:
        rec["decision"] = "ABSTAIN_TOO_WIDE"
        return rec
    lo, hi, zvol, total, span = area
    zt = hi - lo + 1
    conc = concentration(zvol, total, zt, span)
    rec.update(lower_tick=int(lo), upper_tick=int(hi), zone_ticks=int(zt),
               zone_volume=int(zvol), block_volume=int(total),
               block_ticks=int(span), concentration=int(conc))
    if conc < int(p["min_concentration"]):
        rec["decision"] = "ABSTAIN_LOW_CONCENTRATION"
        return rec
    rec["decision"] = "CREATE"
    if close_tick is not None:
        ct = int(close_tick)
        if ct > hi:
            rec["side"], rec["distance_ticks"] = "SUPPORT", ct - hi
        elif ct < lo:
            rec["side"], rec["distance_ticks"] = "RESISTANCE", lo - ct
        else:
            rec["side"], rec["distance_ticks"] = "AT_PRICE", 0
    return rec


def sweep_grid(cells_by_block, grid, close_ticks=None):
    """Barrido: una pasada por celda de la grilla, sin estado entre celdas.

    `grid` es un iterable de dicts de parámetros. Devuelve, por celda, el conteo
    de decisiones y la altura mediana — el landscape COMPLETO, sin seleccionar.
    """
    out = []
    for params in grid:
        created = 0
        heights = []
        decisions = {}
        for i, cells in enumerate(cells_by_block):
            ct = close_ticks[i] if close_ticks is not None else None
            r = detect_block(cells, params, ct)
            decisions[r["decision"]] = decisions.get(r["decision"], 0) + 1
            if r["decision"] == "CREATE":
                created += 1
                heights.append(r["zone_ticks"])
        heights.sort()
        out.append(dict(params=dict(_params(params)), created=created,
                        n_blocks=len(cells_by_block), decisions=decisions,
                        median_zone_ticks=heights[len(heights) // 2] if heights else None))
    return out
