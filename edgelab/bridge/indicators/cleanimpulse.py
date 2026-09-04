"""CleanImpulse — impulsos largos SIN zonas creadas adentro.

Espejo Python de `nt8/CleanImpulses.cs`. **Target-free: no mira retornos.**

## Qué marca

1. Parte la serie en **tramos** (legs): de un pivote a su pivote opuesto. Un tramo
   alcista va de un mínimo a un máximo, uno bajista al revés. Largo = |ticks|.
2. Se queda con el **3 % más largo** de los tramos.
3. De ésos, marca sólo los que **no tienen NINGUNA zona creada adentro**. Una sola
   zona creada durante el impulso lo descalifica, **en cualquier nivel de precio**:
   la regla es temporal, no espacial.

Es la definición literal del pedido, sin agregados.

## Por qué el percentil es causal

El corte del 5 % se calcula sobre los **últimos `window_legs` tramos ya cerrados**,
no sobre la serie entera. Usar el percentil de todo el chart sería mirar el futuro:
un tramo de hoy quedaría clasificado con información de mañana. Eso invalidaría
cualquier medición posterior sin que se note.

## Qué NO decide este módulo

No dice si un impulso limpio es bueno o malo. Sólo enumera la población. Medir si
tiene valor exige manifiesto y el STOP del proyecto.
"""
from __future__ import annotations

NAME = "CleanImpulse"
VERSION = "1.0"

RESEARCH_DEFAULTS = dict(
    pivot_left=3,
    pivot_right=3,
    top_pct=3.0,          # el 3 % más largo
    window_legs=200,      # sobre cuántos tramos previos se calcula el corte
    min_leg_ticks=0,      # piso absoluto opcional
    grace_bars=None,      # barras de gracia tras el fin del tramo; None = pivot_right
    require_price_overlap=False,  # regla de Nico: NINGUNA zona creada dentro del
                                  # impulso, sin importar en qué nivel caiga
)


def _params(overrides=None):
    p = dict(RESEARCH_DEFAULTS)
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


def find_swings(high_ticks, low_ticks, params=None):
    """Pivotes alternados: máximo, mínimo, máximo… Devuelve `[(bar, tipo, tick)]`.

    Alterna a propósito: dos máximos seguidos no delimitan un tramo. Si aparece un
    segundo máximo sin un mínimo en medio, **reemplaza** al anterior si es más
    alto; si no, se descarta. Así cada tramo va de un extremo al extremo opuesto.
    """
    p = _params(params)
    L, R = int(p["pivot_left"]), int(p["pivot_right"])
    n = len(high_ticks)
    out = []
    for i in range(L, n - R):
        esH = (all(high_ticks[i] >= high_ticks[i - d] for d in range(1, L + 1))
               and all(high_ticks[i] > high_ticks[i + d] for d in range(1, R + 1)))
        esL = (all(low_ticks[i] <= low_ticks[i - d] for d in range(1, L + 1))
               and all(low_ticks[i] < low_ticks[i + d] for d in range(1, R + 1)))
        for tipo, ok, v in (("H", esH, high_ticks[i]), ("L", esL, low_ticks[i])):
            if not ok:
                continue
            if out and out[-1][1] == tipo:
                mejor = v > out[-1][2] if tipo == "H" else v < out[-1][2]
                if mejor:
                    out[-1] = (i, tipo, int(v))
                continue
            out.append((i, tipo, int(v)))
    return out


def build_legs(high_ticks, low_ticks, params=None):
    """Tramos entre pivotes opuestos consecutivos."""
    sw = find_swings(high_ticks, low_ticks, params)
    legs = []
    for a, b in zip(sw, sw[1:]):
        legs.append(dict(start_bar=a[0], end_bar=b[0],
                         start_tick=a[2], end_tick=b[2],
                         direction=1 if b[2] > a[2] else -1,
                         length_ticks=abs(b[2] - a[2]),
                         bars=b[0] - a[0]))
    return legs


def _corte(largos, top_pct):
    """Umbral del `top_pct` % superior, sobre los largos ya vistos."""
    if not largos:
        return None
    v = sorted(largos)
    idx = int(len(v) * (1.0 - float(top_pct) / 100.0))
    return v[min(idx, len(v) - 1)]


def zones_inside(leg, zones, params=None):
    """Zonas que el tramo **contiene**: en tiempo y en precio.

    ## Las dos correcciones

    La primera versión sólo miraba el **rango de barras**, y fallaba por dos vías
    a la vez:

    **El tramo terminaba en el pivote exacto.** La zona que el impulso genera se
    registra al cerrarse el movimiento, una o dos barras después del pivote, así
    que caía fuera de la ventana y el impulso quedaba marcado como limpio teniendo
    zonas propias adentro.

    La regla es **temporal**: cualquier zona creada durante el impulso lo
    descalifica, **en cualquier nivel de precio**. `require_price_overlap` existe
    para contrastar contra la variante espacial, y viene apagado.

    La gracia por defecto es `pivot_right`, que es **exactamente** el retardo con
    el que se confirma el pivote: no introduce mirada al futuro, porque en el
    momento en que el tramo queda cerrado esa zona ya se conocía.
    """
    p = _params(params)
    gracia = p["grace_bars"]
    if gracia is None:
        gracia = int(p["pivot_right"])
    b0, b1 = leg["start_bar"], leg["end_bar"] + int(gracia)
    lo_leg = min(leg["start_tick"], leg["end_tick"])
    hi_leg = max(leg["start_tick"], leg["end_tick"])
    out = []
    for z in zones:
        sb = int(z["start_bar"])
        if not (b0 <= sb <= b1):
            continue
        if p["require_price_overlap"] and ("lower_tick" in z or "upper_tick" in z):
            zlo = int(z.get("lower_tick", z.get("upper_tick")))
            zhi = int(z.get("upper_tick", z.get("lower_tick")))
            if zhi < lo_leg or zlo > hi_leg:
                continue                 # la zona no cae dentro del recorrido
        out.append(z)
    return out


def detect(high_ticks, low_ticks, zones, params=None):
    """Tramos del `top_pct` % más largo y **sin zonas creadas adentro**.

    Devuelve todos los tramos evaluados con su clasificación, no sólo los
    marcados: el censo completo es lo que permite medir después sin quedar
    seleccionado por resultado.
    """
    p = _params(params)
    legs = build_legs(high_ticks, low_ticks, p)
    win = int(p["window_legs"])
    piso = int(p["min_leg_ticks"])
    vistos = []
    for leg in legs:
        # percentil CAUSAL: sólo con los tramos ya cerrados antes de éste
        corte = _corte(vistos[-win:], p["top_pct"])
        leg["cut_ticks"] = corte
        leg["is_long"] = (corte is not None and leg["length_ticks"] >= corte
                          and leg["length_ticks"] >= piso)
        dentro = zones_inside(leg, zones, p)
        leg["zones_inside"] = len(dentro)
        leg["is_clean"] = leg["is_long"] and len(dentro) == 0
        vistos.append(leg["length_ticks"])
    return legs


def census(legs):
    if not legs:
        return dict(n=0)
    largos = [l for l in legs if l["is_long"]]
    limpios = [l for l in legs if l["is_clean"]]
    med = lambda v: sorted(v)[len(v) // 2] if v else None
    return dict(
        n=len(legs), largos=len(largos), limpios=len(limpios),
        pct_limpios_entre_largos=(round(len(limpios) / len(largos), 4)
                                  if largos else None),
        largo_mediano=med([l["length_ticks"] for l in legs]),
        largo_mediano_de_los_largos=med([l["length_ticks"] for l in largos]),
        zonas_dentro_mediana_de_los_largos=med([l["zones_inside"] for l in largos]),
    )
