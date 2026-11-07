"""Candidatos a espejo vistos en velas de 10 ticks.

Un impulso y la vuelta se juzgan en esa resolución, no en el tick. Los dos tienen
que ir sin un retroceso marcado: un cierre que devuelve más de `retro` (0,20) del
tramo ya hecho y después el precio sigue. El dibujo de referencia es una montaña
de un solo trazo contra un serrucho.

El candidato se conoce en el primer cierre que deshizo la mitad del impulso.
Ahí se corta. No se mira si después llega a A: eso lo clasifica quien mira el gráfico.

Los precios entran en ticks. Una fila por sesión, sin cruzar el corte.
"""
from __future__ import annotations

import numpy as np

TICKS_POR_VELA = 10
RETRO_MARCADO = 0.20
MITAD = 0.50
MIN_W = 80.0
MIN_BARRAS_IDA = 8
MIN_BARRAS_VUELTA = 4
MAX_BARRAS_IDA = 400
# Al mostrar el candidato ya se recorrió la mitad. Lo que falta hasta A tiene que
# cubrir varios viajes del escenario severo, si no la fricción se come el tramo.
VIAJES_EN_LO_QUE_FALTA = 40


def ancho_minimo_ticks(instrumento: str, viajes: float = VIAJES_EN_LO_QUE_FALTA) -> int:
    """Ancho mínimo, en ticks, para que la mitad que falta valga `viajes` idas y vueltas severas."""
    from edgelab import costos
    falta = viajes * costos.friccion_rt_ticks(instrumento, "severo")
    return int(np.ceil(2.0 * falta))


def peor_cierre(C, i0: int, i1: int, lado: int) -> float:
    """Peor retroceso del cierre entre i0 e i1, en ticks. Sólo cuenta lo que no es un nuevo extremo."""
    peor = 0.0
    ext = float(C[i0])
    if lado == 1:
        for k in range(i0 + 1, i1 + 1):
            if C[k] >= ext:
                ext = float(C[k])
            else:
                peor = max(peor, ext - float(C[k]))
        return peor
    for k in range(i0 + 1, i1 + 1):
        if C[k] <= ext:
            ext = float(C[k])
        else:
            peor = max(peor, float(C[k]) - ext)
    return peor


def _candidato(C, i0: int, lado: int, retro: float, mitad: float, min_w: float, min_ida: int, min_vuelta: int, max_ida: int):
    """Desde i0, un impulso en `lado`. None si esta salida no es un candidato."""
    n = len(C)
    A = float(C[i0])
    ext = A
    iext = i0
    peor = 0.0
    tope = i0 + max_ida
    for k in range(i0 + 1, n):
        ck = float(C[k])
        nuevo = (lado == 1 and ck > ext) or (lado == -1 and ck < ext)
        if nuevo:
            if k > tope:
                return None
            if iext < k - 1 and (ext - A) * lado >= min_w * 0.5:
                dip = (ext - float(np.min(C[iext + 1:k]))) if lado == 1 else (float(np.max(C[iext + 1:k])) - ext)
                if dip > retro * (ext - A) * lado:
                    return None
                peor = max(peor, dip)
            ext = ck
            iext = k
            continue
        W = (ext - A) * lado
        if W < min_w or iext - i0 + 1 < min_ida:
            if (A - ck) * lado > 0:
                return None
            continue
        avance = (ext - ck) * lado
        if avance < mitad * W:
            if (A - ck) * lado > 0:
                return None
            continue
        if k - iext < min_vuelta:
            return None
        if not _vuelta_limpia(C, iext, k, lado, retro):
            return None
        return dict(i0=i0, iext=iext, k=k, A=A, B=ext, lado=lado, W=W,
                    retro_ida=peor / W, retro_vuelta=0.0)
    return None


def _vuelta_limpia(C, iext: int, k: int, lado: int, retro: float) -> bool:
    """La vuelta, hasta el cierre k, no devolvió más de `retro` de lo que ya había deshecho."""
    piso = float(C[iext])
    if lado == 1:
        for j in range(iext + 1, k + 1):
            cj = float(C[j])
            if cj < piso:
                piso = cj
            elif float(C[iext]) - piso > 0 and cj - piso > retro * (float(C[iext]) - piso):
                return False
        return True
    techo = float(C[iext])
    for j in range(iext + 1, k + 1):
        cj = float(C[j])
        if cj > techo:
            techo = cj
        elif techo - float(C[iext]) > 0 and techo - cj > retro * (techo - float(C[iext])):
            return False
    return True


def detectar(C, ses=None, retro=RETRO_MARCADO, mitad=MITAD, min_w=MIN_W, min_ida=MIN_BARRAS_IDA,
             min_vuelta=MIN_BARRAS_VUELTA, max_ida=MAX_BARRAS_IDA) -> list:
    """Candidatos de una serie de cierres. `ses` parte las sesiones; sin él, es una sola."""
    C = np.asarray(C, float)
    n = len(C)
    if ses is None:
        ses = np.zeros(n, np.int64)
    else:
        ses = np.asarray(ses)
    out = []
    cortes = np.r_[0, np.flatnonzero(ses[1:] != ses[:-1]) + 1, n] if n else np.array([0])
    for a, b in zip(cortes[:-1], cortes[1:]):
        out.extend(_sesion(C[a:b], int(a), retro, mitad, min_w, min_ida, min_vuelta, max_ida))
    return out


def _sesion(C, base: int, retro, mitad, min_w, min_ida, min_vuelta, max_ida) -> list:
    n = len(C)
    out = []
    i = 0
    while i < n - min_ida:
        up = _candidato(C, i, 1, retro, mitad, min_w, min_ida, min_vuelta, max_ida)
        dn = _candidato(C, i, -1, retro, mitad, min_w, min_ida, min_vuelta, max_ida)
        el = up if dn is None else dn if up is None else (up if up["k"] <= dn["k"] else dn)
        if el is None:
            i += 1
            continue
        el = dict(el)
        el["i0"] += base
        el["iext"] += base
        el["k"] += base
        out.append(el)
        i = el["k"] - base + 1
    return out


def velas_de_ticks(precio_ticks: np.ndarray, volumen: np.ndarray, ticks_por_vela: int = TICKS_POR_VELA):
    """Velas de N ticks dentro de una sola sesión. El resto que no completa una vela se tira."""
    px = np.asarray(precio_ticks, float)
    vol = np.asarray(volumen, float)
    n = int(ticks_por_vela)
    m = len(px) // n
    if m == 0:
        z = np.zeros(0, float)
        return z, z, z, z, z
    px = px[:m * n].reshape(m, n)
    vol = vol[:m * n].reshape(m, n)
    return px[:, 0], px.max(1), px.min(1), px[:, -1], vol.sum(1)
