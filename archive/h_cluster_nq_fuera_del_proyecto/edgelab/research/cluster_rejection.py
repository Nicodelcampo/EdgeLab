"""Rechazo en el borde de un cluster — el canal direccional (H2). Target-free.

**No mira P&L.** Mide si el precio se da vuelta al llegar a un nivel, y compara el
borde de un cluster contra un nivel cualquiera al que el precio llegó igual. No hay
entrada, salida, sizing ni costo: sólo la geometría del recorrido posterior.

## La hipótesis

Nico: *«el precio rechaza los extremos de un cluster»*. Es el complemento direccional de
H1 (atracción). Se miden juntas porque un efecto que empuja en las dos direcciones
promedia cero si sólo se mira un canal.

## El control, que es lo que hace medible la pregunta

La trampa acá es la misma de siempre: los niveles que el precio toca no son una muestra
al azar de los niveles posibles, y los bordes de cluster están donde ya hubo actividad.
Comparar "rechazos en bordes de cluster" contra nada da un número sin referencia.

El control es **el mismo evento en un nivel sin cluster**: se enumeran todos los
contactos de primera vez con un nivel de precio en la sesión —haya cluster o no— y se
contrasta la tasa de rechazo entre los que caen sobre un borde vivo y los que no,
**estratificando por distancia de aproximación y por volatilidad local**. Sin
estratificar, el contraste mediría que el precio llega a los bordes de cluster con otra
velocidad, no que reaccione distinto.

## Definiciones, elegidas antes de mirar resultados

- **Contacto**: barra que toca el nivel `L` sin haberlo tocado en las `ventana_previa`
  barras anteriores, viniendo desde al menos `dist_min` ticks de distancia.
- **Rechazo**: dentro de `horizonte`, el precio vuelve a `retro_ticks` del lado por el
  que vino, **sin** haber llegado a `penetracion_ticks` del otro lado.
- **Atraviesa**: llega a `penetracion_ticks` del otro lado.
- Los que no hacen ninguna de las dos quedan como **indefinido** y se cuentan aparte;
  meterlos en el denominador de "rechazo" inflaría o desinflaría la tasa según el
  horizonte, que es un parámetro nuestro y no del mercado.
"""
from __future__ import annotations

import math

NAME = "ClusterRejection"
VERSION = "1.1"

# Escalon 5 del embudo: condicionamiento por intensidad y construccion hold-out.
#
# El cluster nace donde hubo actividad y la actividad ocurre donde estuvo el precio, asi
# que medir "el precio reacciona al cluster" condiciona sobre una variable
# co-determinada por el precio. Dos correcciones, que se miden por separado:
#
#   INTENSIDAD  cuantas zonas nacieron en las ultimas `ventana_intensidad` barras. Si el
#               contraste desaparece al estratificar por esto, lo que se medía era el
#               regimen de actividad, no el objeto.
#
#   HOLD-OUT    solo se usan clusters cuya ultima actualizacion ocurrio hace al menos
#               `lag_holdout` barras. Asi ningun tramo de precio que entra en la
#               definicion del objeto entra tambien en la ventana de resultado.
DEFAULTS = dict(
    ventana_previa=30,        # barras sin tocar el nivel para que cuente como contacto
    dist_min_ticks=4,         # de que tan lejos tiene que venir
    horizonte=20,             # barras para resolver el desenlace
    retro_ticks=4,            # cuanto tiene que volver para contar como rechazo
    penetracion_ticks=4,      # cuanto tiene que pasar de largo para contar como cruce
    bordes_distancia=(4, 8, 16, 32, 1000),
    bordes_sigma=(0.0, 2.0, 4.0, 1e9),
    ventana_intensidad=100,
    bordes_intensidad=(5, 15, 40, 10**9),
    lag_holdout=30,
)


def _p(over=None):
    d = dict(DEFAULTS)
    if over:
        d.update({k: v for k, v in over.items() if v is not None})
    return d


def contactos(barras, i, p):
    """Niveles que la barra `i` toca por primera vez en `ventana_previa` barras.

    Devuelve `[(nivel, lado)]`, con `lado` = +1 si el precio subió hasta el nivel y −1
    si bajó. Un nivel tocado hace dos barras no es un contacto: sería contar la misma
    aproximación muchas veces y multiplicar N sin agregar información.
    """
    if i == 0:
        return []
    b = barras[i]
    prev_close = barras[i - 1]["close"]
    j0 = max(0, i - p["ventana_previa"])
    tocados_antes = set()
    for k in range(j0, i):
        for tk in range(barras[k]["lo"], barras[k]["hi"] + 1):
            tocados_antes.add(tk)

    out = []
    for tk in range(b["lo"], b["hi"] + 1):
        if tk in tocados_antes:
            continue
        d = tk - prev_close
        if abs(d) < p["dist_min_ticks"]:
            continue
        out.append((tk, 1 if d > 0 else -1))
    return out


def desenlace(barras, i, nivel, lado, p):
    """Qué pasa después del contacto: rechazo, cruce, o indefinido.

    `lado` = +1 si el precio venía subiendo. Rechazo es volver hacia abajo; cruce es
    seguir hacia arriba. Se resuelve por **lo que ocurre primero**, no por dónde está
    el precio al final del horizonte — eso último dependería del horizonte y no del
    mercado.
    """
    fin = min(len(barras), i + 1 + p["horizonte"])
    if fin <= i + 1:
        return None
    retro = p["retro_ticks"]
    pene = p["penetracion_ticks"]
    for k in range(i + 1, fin):
        b = barras[k]
        if lado > 0:
            if b["hi"] >= nivel + pene:
                return "cruza"
            if b["lo"] <= nivel - retro:
                return "rechaza"
        else:
            if b["lo"] <= nivel - pene:
                return "cruza"
            if b["hi"] >= nivel + retro:
                return "rechaza"
    return "indefinido"


def es_borde_de_cluster(nivel, clusters, tolerancia=1):
    """¿El nivel cae sobre el borde de algún cluster vivo?

    Borde y no interior: la hipótesis de Nico es sobre los **extremos**. Un nivel en el
    medio del rango es otro objeto y se marca aparte.
    """
    for c in clusters:
        if abs(nivel - c["lower_tk"]) <= tolerancia:
            return True
        if abs(nivel - c["upper_tk"]) <= tolerancia:
            return True
    return False


def borde_de(nivel, clusters, tolerancia=1):
    """Devuelve el cluster cuyo borde toca el nivel, o `None`.

    Hace falta para el escalon 5: sin saber CUAL cluster es, no se puede medir hace
    cuanto que no se actualiza, que es lo que permite construirlo hold-out.
    """
    for c in clusters:
        if (abs(nivel - c["lower_tk"]) <= tolerancia
                or abs(nivel - c["upper_tk"]) <= tolerancia):
            return c
    return None


def esta_dentro(nivel, clusters):
    for c in clusters:
        if c["lower_tk"] <= nivel <= c["upper_tk"]:
            return True
    return False


def _bin(valor, bordes):
    for k, b in enumerate(bordes):
        if valor < b:
            return k
    return len(bordes)


def categoria(nivel, clusters, tolerancia=1):
    """`borde`, `dentro` o `libre`. Los tres son objetos distintos.

    Esto **corrige una contaminación del control**: en la primera corrida el grupo de
    comparación era "todo lo que no es borde", que incluye los niveles del INTERIOR de
    un cluster. Si el interior se comporta distinto de un nivel libre —y no hay razón
    para suponer que no—, el control estaba mezclado y el contraste medía otra cosa.
    El control correcto es el nivel **sin cluster ninguno**.
    """
    if es_borde_de_cluster(nivel, clusters, tolerancia):
        return "borde"
    if esta_dentro(nivel, clusters):
        return "dentro"
    return "libre"


def tabla(muestras, p, minimo=30):
    """Tasa de rechazo por estrato, con y sin cluster.

    Estratifica por distancia de aproximación y volatilidad local: sin eso, el
    contraste mediría que el precio llega a los bordes de cluster de otra manera, no
    que reaccione distinto una vez que llegó.

    Los `indefinido` quedan **fuera** del denominador y se reportan aparte.
    """
    celdas = {}
    for m in muestras:
        if m["desenlace"] == "indefinido":
            clave = (_bin(abs(m["distancia"]), p["bordes_distancia"]),
                     _bin(m["sigma"], p["bordes_sigma"]), m.get("categoria", m["borde"]))
            c = celdas.setdefault(clave, dict(n=0, rechazos=0, indefinidos=0))
            c["indefinidos"] += 1
            continue
        clave = (_bin(abs(m["distancia"]), p["bordes_distancia"]),
                 _bin(m["sigma"], p["bordes_sigma"]), m.get("categoria", m["borde"]))
        c = celdas.setdefault(clave, dict(n=0, rechazos=0, indefinidos=0))
        c["n"] += 1
        c["rechazos"] += 1 if m["desenlace"] == "rechaza" else 0

    out = []
    vistos = {(d, s) for d, s, _ in celdas}
    for d, s in sorted(vistos):
        con = celdas.get((d, s, "borde"), celdas.get((d, s, True),
                         dict(n=0, rechazos=0, indefinidos=0)))
        # control = nivel LIBRE. El interior del cluster es otro objeto y va aparte.
        sin = celdas.get((d, s, "libre"), celdas.get((d, s, False),
                         dict(n=0, rechazos=0, indefinidos=0)))
        adentro = celdas.get((d, s, "dentro"), dict(n=0, rechazos=0, indefinidos=0))
        p_con = con["rechazos"] / con["n"] if con["n"] else None
        p_sin = sin["rechazos"] / sin["n"] if sin["n"] else None
        out.append(dict(
            bin_distancia=d, bin_sigma=s,
            n_borde=con["n"], n_sin_borde=sin["n"],
            indefinidos_borde=con["indefinidos"], indefinidos_sin=sin["indefinidos"],
            n_dentro=adentro["n"],
            rechazo_dentro=(adentro["rechazos"] / adentro["n"]) if adentro["n"] else None,
            rechazo_borde=p_con, rechazo_sin_borde=p_sin,
            contraste=(p_con - p_sin) if (p_con is not None and p_sin is not None) else None,
            suficiente=con["n"] >= minimo and sin["n"] >= minimo,
        ))
    return out


def tabla_por(muestras, campo, bordes, minimo=30):
    """Contraste borde-vs-libre estratificado por un campo cualquiera.

    Se usa para el escalon 5: si el contraste se sostiene dentro de cada estrato de
    intensidad, no es el regimen de actividad el que lo produce.
    """
    celdas = {}
    for m in muestras:
        if m["desenlace"] == "indefinido":
            continue
        cat = m.get("categoria", m["borde"])
        if cat not in ("borde", "libre", True, False):
            continue
        clave = (_bin(m[campo], bordes), cat in ("borde", True))
        c = celdas.setdefault(clave, dict(n=0, rechazos=0))
        c["n"] += 1
        c["rechazos"] += 1 if m["desenlace"] == "rechaza" else 0
    out = []
    for b in sorted({k for k, _ in celdas}):
        con = celdas.get((b, True), dict(n=0, rechazos=0))
        sin = celdas.get((b, False), dict(n=0, rechazos=0))
        p_con = con["rechazos"] / con["n"] if con["n"] else None
        p_sin = sin["rechazos"] / sin["n"] if sin["n"] else None
        out.append(dict(bin=b, n_borde=con["n"], n_libre=sin["n"],
                        rechazo_borde=p_con, rechazo_libre=p_sin,
                        contraste=(p_con - p_sin) if (p_con is not None and p_sin is not None) else None,
                        suficiente=con["n"] >= minimo and sin["n"] >= minimo))
    return out


def agregado(muestras):
    """Resumen sin estratificar. Se publica junto a la tabla, nunca en su lugar.

    Un agregado sin estratos puede invertir el signo del contraste estratificado — es
    la paradoja de Simpson, y con datos donde la exposición al cluster depende de la
    distancia es un riesgo real, no teórico.
    """
    out = {}
    for borde in (True, False):
        sel = [m for m in muestras if m["borde"] == borde
               and m["desenlace"] != "indefinido"]
        n = len(sel)
        out["borde" if borde else "sin_borde"] = dict(
            n=n,
            rechazo=(sum(1 for m in sel if m["desenlace"] == "rechaza") / n) if n else None,
            indefinidos=sum(1 for m in muestras if m["borde"] == borde
                            and m["desenlace"] == "indefinido"),
        )
    a, b = out["borde"]["rechazo"], out["sin_borde"]["rechazo"]
    out["contraste"] = (a - b) if (a is not None and b is not None) else None
    return out


def agregado_limpio(muestras):
    """Agregado con el control **limpio**: borde contra nivel LIBRE, sin el interior.

    `agregado` parte por el booleano `borde`, asi que su grupo "sin borde" mezcla los
    niveles libres con el **interior** de los clusters, que es otro objeto y tiene otra
    tasa. Esa contaminacion ya se habia encontrado y corregido en la tabla estratificada
    (`RECHAZO_CLUSTERS_NQ_2026-09-07.md`, punto 3) y vuelve a entrar por el agregado
    cada vez que se lo lee como si su control fuera "libre".

    Se agrega aparte en vez de cambiar `agregado`: la semantica de un estadistico ya
    publicado no se toca en silencio.
    """
    out = {}
    for cat in ("borde", "libre", "dentro"):
        sel = [m for m in muestras
               if m.get("categoria") == cat and m["desenlace"] != "indefinido"]
        n = len(sel)
        out[cat] = dict(
            n=n,
            rechazo=(sum(1 for m in sel if m["desenlace"] == "rechaza") / n) if n else None,
        )
    a, b = out["borde"]["rechazo"], out["libre"]["rechazo"]
    out["contraste"] = (a - b) if (a is not None and b is not None) else None
    return out


def _prop(sel):
    n = len(sel)
    return n, (sum(1 for m in sel if m["desenlace"] == "rechaza") / n) if n else None


def _z_dos_proporciones(n1, p1, n2, p2, deff=1.0):
    """z y p bilateral para la diferencia de dos proporciones, inflando por `deff`.

    `deff` es el mismo factor de diseno que usa el MDE: las observaciones estan
    agrupadas por sesion y tratarlas como independientes angosta el error de forma
    ficticia.
    """
    if not n1 or not n2 or p1 is None or p2 is None:
        return None, None, None
    se = math.sqrt(deff * (p1 * (1.0 - p1) / n1 + p2 * (1.0 - p2) / n2))
    if se <= 0.0:
        return None, None, None
    z = (p1 - p2) / se
    return se, z, math.erfc(abs(z) / math.sqrt(2.0))


def contraste_lag(muestras, lag, deff=5.0):
    """Descompone el brazo `borde` en cluster **fresco** y cluster **rancio**.

    El escalon 5b como estaba escrito compara *solo* el subconjunto rancio contra libre
    y publica un unico numero. Eso no distingue "el efecto desaparece al aislar el
    objeto" de "el subconjunto rancio no tiene potencia": son lecturas opuestas y el
    mismo numero es compatible con las dos.

    Aca se publican las tres cantidades que hacen falta para decidir: fresco vs libre,
    rancio vs libre, y **la diferencia fresco menos rancio**, que es la que dice si la
    frescura del objeto es lo que produce el contraste.

    Advertencia que no resuelve este estimador: la rancidez no es aleatoria. Un cluster
    lleva 30 barras sin actualizarse porque el precio estuvo lejos, y el rechazo cae con
    la distancia de aproximacion. La particion hay que leerla **estratificada** —por eso
    el runner publica ademas `cr.tabla` sobre cada mitad.
    """
    libre = [m for m in muestras
             if m.get("categoria") == "libre" and m["desenlace"] != "indefinido"]
    bordes = [m for m in muestras
              if m.get("categoria") == "borde" and m["desenlace"] != "indefinido"
              and m.get("lag") is not None]
    frescos = [m for m in bordes if m["lag"] < lag]
    rancios = [m for m in bordes if m["lag"] >= lag]

    n_l, p_l = _prop(libre)
    n_f, p_f = _prop(frescos)
    n_r, p_r = _prop(rancios)

    se_fl, z_fl, pv_fl = _z_dos_proporciones(n_f, p_f, n_l, p_l, deff)
    se_rl, z_rl, pv_rl = _z_dos_proporciones(n_r, p_r, n_l, p_l, deff)
    se_fr, z_fr, pv_fr = _z_dos_proporciones(n_f, p_f, n_r, p_r, deff)

    return dict(
        lag=lag, deff=deff,
        libre=dict(n=n_l, rechazo=p_l),
        fresco=dict(n=n_f, rechazo=p_f,
                    contraste=(p_f - p_l) if (p_f is not None and p_l is not None) else None,
                    se=se_fl, z=z_fl, p_valor=pv_fl),
        rancio=dict(n=n_r, rechazo=p_r,
                    contraste=(p_r - p_l) if (p_r is not None and p_l is not None) else None,
                    se=se_rl, z=z_rl, p_valor=pv_rl),
        diferencia=dict(valor=(p_f - p_r) if (p_f is not None and p_r is not None) else None,
                        se=se_fr, z=z_fr, p_valor=pv_fr),
    )
