"""Decaimiento empírico de clusters HFT — estimarlo, no elegirlo.

**Target-free.** No hay P&L, ni dirección esperada, ni selección por resultado. Se mide
si el comportamiento del precio cambia según cuánto se consumió un cluster.

## La idea

Hoy el cluster tiene una muerte dura: al perforarse pasa a `Invalidated` y desaparece.
Medido sobre el log real de NQ, **el 99,4 % de los clusters muere así** y sólo el 0,4 %
llega a agotarse por consumo. O sea que el mecanismo de decaimiento por volumen
prácticamente nunca actúa: el objeto muere de un golpe.

La alternativa no es elegir una curva de decaimiento sino **estimarla**. Para cada
cluster, en cada barra, se conoce la fracción de capacidad consumida `c`. La pregunta es
si el precio se comporta distinto según `c`:

- ¿vuelve a entrar al rango dentro de `h` barras?
- ¿lo cruza de lado a lado?
- ¿cuántas barras pasa adentro?

Si esas cantidades caen monótonamente con `c`, **esa curva es la función de
decaimiento**. No se elige: se lee.

## El control, que es lo que decide si la curva significa algo

`c` está correlacionado con la edad del cluster y con que el precio ya haya operado
cerca. Un cluster muy consumido es, por construcción, uno viejo junto al cual el precio
estuvo. Así que una curva descendente aparecería **aunque el cluster no tuviera nada
adentro**: sería el sesgo de proximidad otra vez.

Por eso cada muestra real se aparea con un **control sin cluster** a la misma distancia,
del mismo ancho, en el mismo instante — construido con `f28.controls`, las mismas
funciones que cerraron la línea de BigTrap2 como imán sobre 6E. El estimando es el
**contraste**, no la curva cruda.

## Qué NO decide este módulo

No dice si conviene operar nada. No elige la mejor configuración de cluster: eso es
optimizar contra retornos y necesita el STOP del proyecto, manifiesto y holdout. Acá
sólo se estima cómo decae el objeto.
"""
from __future__ import annotations

import math

from edgelab.research.f28.controls import eligible_control, same_side_interval

NAME = "ClusterDecay"
VERSION = "1.0"

DEFAULTS = dict(
    horizonte_barras=20,        # h: ventana de resultado despues de cada muestra
    cada_n_barras=5,            # submuestreo: baja la autocorrelacion del panel
    dist_min_ticks=2,           # el precio tiene que estar AFUERA del cluster
    dist_max_ticks=40,          # y no tan lejos que el resultado sea trivialmente no
    ventana_sigma_barras=50,
    bordes_consumo=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0001),
)


def _p(over=None):
    d = dict(DEFAULTS)
    if over:
        d.update({k: v for k, v in over.items() if v is not None})
    return d


def barras_desde_ticks(ts_ns, price_ticks, volume, ticks_por_barra):
    """Agrega el tick stream en barras de N ticks.

    Devuelve `(barras, perfiles)`. Cada barra es `dict(hi, lo, close, i0, i1)` en ticks
    enteros; cada perfil es `{tick: volumen}` de esa barra.

    El perfil por barra es lo que hace viable el módulo: el consumo de un cluster se
    calcula intersecando su rango con los pocos niveles que la barra tocó, en vez de
    recorrer todos los ticks por cada cluster. De O(ticks x clusters) a
    O(barras x clusters x niveles).
    """
    barras, perfiles = [], []
    n = len(price_ticks)
    for i0 in range(0, n, ticks_por_barra):
        i1 = min(i0 + ticks_por_barra, n)
        if i1 - i0 < 2:
            break
        tramo = price_ticks[i0:i1]
        perfil = {}
        for k in range(i0, i1):
            perfil[price_ticks[k]] = perfil.get(price_ticks[k], 0.0) + float(volume[k])
        barras.append(dict(hi=max(tramo), lo=min(tramo), close=tramo[-1], i0=i0, i1=i1))
        perfiles.append(perfil)
    return barras, perfiles


def sigma_local(barras, i, ventana):
    """Volatilidad realizada en ticks sobre las `ventana` barras previas.

    Se usa para aparear el control: sin condicionar por σ, un cluster nacido en régimen
    volátil parecería "atraer" sólo porque con más σ se toca cualquier cosa.
    """
    j0 = max(1, i - ventana)
    if i - j0 < 2:
        return 0.0
    difs = [barras[k]["close"] - barras[k - 1]["close"] for k in range(j0, i)]
    m = sum(difs) / len(difs)
    var = sum((d - m) ** 2 for d in difs) / max(1, len(difs) - 1)
    return math.sqrt(var)


def consumo_por_barra(clusters, perfil):
    """Volumen operado dentro de cada cluster durante una barra.

    `clusters` son dicts con `lower_tk`/`upper_tk` enteros. Devuelve `{id: volumen}`.
    """
    out = {}
    for c in clusters:
        v = 0.0
        for tk, vol in perfil.items():
            if c["lower_tk"] <= tk <= c["upper_tk"]:
                v += vol
        if v:
            out[c["id"]] = v
    return out


def resultados(barras, i, lo_tk, hi_tk, h):
    """Qué hace el precio en las `h` barras siguientes respecto de una banda.

    Tres canales, todos **no direccionales**: entrar, atravesar, y permanecer. Ninguno
    mira signo de retorno ni P&L.

    - `reentra`: tocó la banda al menos una vez;
    - `cruza`: estuvo estrictamente de los dos lados (la atravesó entera);
    - `barras_adentro`: cuántas de las `h` barras solapan la banda.
    """
    fin = min(len(barras), i + 1 + h)
    if fin <= i + 1:
        return None
    toco = False
    arriba = False
    abajo = False
    adentro = 0
    for k in range(i + 1, fin):
        b = barras[k]
        if b["hi"] >= lo_tk and b["lo"] <= hi_tk:
            toco = True
            adentro += 1
        if b["hi"] > hi_tk:
            arriba = True
        if b["lo"] < lo_tk:
            abajo = True
    return dict(reentra=int(toco), cruza=int(arriba and abajo),
                barras_adentro=adentro, horizonte=fin - (i + 1))


def muestra_control(precio_tk, lo_tk, hi_tk, ocupados):
    """Banda-placebo: mismo ancho, misma distancia, mismo lado, sin cluster.

    Usa `f28.controls`, que es el control que refutó a BigTrap2 como imán sobre 6E: si
    el placebo se comporta igual que el cluster, no era la zona — era la geometría.

    Devuelve `None` si el control cae sobre un cluster real o cruza el precio; esos
    casos se descartan en vez de contaminarse.
    """
    ancho = hi_tk - lo_tk + 1
    d = lo_tk - precio_tk if lo_tk > precio_tk else precio_tk - hi_tk
    if d <= 0:
        return None
    # el control va del lado OPUESTO al cluster, a la misma distancia
    hacia_arriba = lo_tk > precio_tk
    clo, chi = same_side_interval(precio_tk, d, ancho, is_bull=not hacia_arriba)
    if not eligible_control(precio_tk, clo, chi, ocupados):
        return None
    return clo, chi


def curva(muestras, campo, bordes, minimo_por_bin=30):
    """Promedio del resultado por bin de consumo, con su n.

    Publica **todos** los bins, incluidos los que no llegan al mínimo — un bin flaco es
    información, y esconderlo haría parecer suave una curva que no lo es.
    """
    out = []
    for a, b in zip(bordes, bordes[1:]):
        sel = [m for m in muestras if a <= m["consumo"] < b]
        n = len(sel)
        real = sum(m["real"][campo] for m in sel) / n if n else None
        ctrl = [m for m in sel if m.get("control")]
        placebo = (sum(m["control"][campo] for m in ctrl) / len(ctrl)) if ctrl else None
        out.append(dict(
            desde=round(a, 3), hasta=round(min(b, 1.0), 3), n=n, n_control=len(ctrl),
            real=real, placebo=placebo,
            contraste=(real - placebo) if (real is not None and placebo is not None) else None,
            suficiente=n >= minimo_por_bin,
        ))
    return out


def mde_proporcion(n, p=0.5, potencia=0.8, alfa=0.05, celdas=1, deff=1.0):
    """Efecto mínimo detectable para una proporción, antes de correr.

    El proyecto obliga a publicarlo con todo resultado nulo: sin MDE, un cero no
    distingue "no hay efecto" de "no había potencia". `celdas` corrige por multiplicidad
    (Bonferroni) y `deff` por el agrupamiento en sesiones.
    """
    if n <= 0:
        return None
    z_a = _z(1.0 - (alfa / celdas) / 2.0)
    z_b = _z(potencia)
    n_ef = n / max(1e-9, deff)
    return (z_a + z_b) * math.sqrt(2.0 * p * (1.0 - p) / n_ef)


def _z(q):
    """Cuantil normal por Acklam; suficiente para un MDE y sin dependencias nuevas."""
    if not 0.0 < q < 1.0:
        raise ValueError("q fuera de (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if q < plow:
        t = math.sqrt(-2 * math.log(q))
        return (((((c[0]*t+c[1])*t+c[2])*t+c[3])*t+c[4])*t+c[5]) / ((((d[0]*t+d[1])*t+d[2])*t+d[3])*t+1)
    if q > phigh:
        t = math.sqrt(-2 * math.log(1 - q))
        return -(((((c[0]*t+c[1])*t+c[2])*t+c[3])*t+c[4])*t+c[5]) / ((((d[0]*t+d[1])*t+d[2])*t+d[3])*t+1)
    t = q - 0.5
    r = t * t
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*t / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
