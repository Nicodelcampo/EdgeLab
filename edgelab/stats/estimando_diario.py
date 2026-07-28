# -*- coding: utf-8 -*-
"""Estimando diario canónico de EXPLORE-001. **La unidad es el DÍA, no el evento.**

## Qué se estima y por qué así

Por cada día calendario elegible `d` hay UN registro, tenga zonas o no. Si el
día tiene al menos un evento real (día ACTIVO), su efecto es la diferencia de
medias del día contra su propio nulo:

    x_d = sum_real_d / n_real_d  -  sum_nulo_d / n_nulo_d

y el estimando primario es el promedio de esos efectos con **igual peso por día
activo**:

    u_d = activo_d * x_d          v_d = activo_d
    theta = sum_d u_d / sum_d v_d

**Por qué equal-weight por día y no por evento** (§1.3 de la espec): el pooling
por evento (`Σ aciertos / Σ eventos`) le da a un día con 20 zonas veinte veces
el peso de un día con 1. Los eventos del mismo día comparten régimen
—volatilidad, tendencia, noticias—, así que ese peso extra **no es información
extra**: es la misma observación contada veinte veces. Además haría que el
estadístico dependa de cuántas zonas produce el indicador cada día, que es una
propiedad del feature y no del efecto que se quiere medir.

Consecuencia declarada: un efecto que sólo exista en días de muchas zonas **no**
lo detecta este estimando. Es otra hipótesis, con su propio turno.

## Por qué los días CERO se guardan aunque no entren al denominador

Los días sin zonas **no aportan efecto** (`u=0`, `v=0`) pero **siguen en la
cronología**. Esa distinción no es cosmética: al remuestrear bloques se
remuestrean **registros diarios completos**, y un bloque de `b` días calendario
contiene un número VARIABLE de días activos. Comprimir la serie primero
—tirando los días cero y recién después armando bloques— cambia qué días quedan
contiguos y por lo tanto cambia la estructura de dependencia que el bloque
existe para preservar. Por eso `serie_uv` devuelve la serie completa y
`theta_de_uv` recomputa el ratio desde las sumas de la muestra: **nunca desde
una lista precomprimida de días activos.**

Un día sin zonas tampoco recibe "efecto cero": eso lo metería al denominador y
sesgaría `theta` hacia cero en proporción a cuántos días el feature no dispara.
`v_d = 0` dice "este día no opina", que es distinto de "este día opina cero".

## Lo que este módulo NO hace

No estima largo de bloque, no remuestrea, no calcula intervalos, no toca costos
ni datos reales. Recibe conteos y sumas ya agregados por día y devuelve el
registro validado más el ratio. El bootstrap y el resto de la inferencia van
aparte y consumen `serie_uv` + `theta_de_uv`.

## Degradación silenciosa: prohibida

Una muestra sin días activos NO devuelve 0, NaN ni inf: levanta
`SinDiasActivosError`. Un `0/0` que se convierte en `nan` y sigue viajando por
un bootstrap es un intervalo inventado con cara de resultado.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["EstimandoDiarioError", "SinDiasActivosError", "RegistroDiario",
           "construir_registro", "serie_uv", "theta_de_uv", "estimar"]


class EstimandoDiarioError(RuntimeError):
    """El registro diario viola su contrato. Falla ruidoso, no se degrada."""


class SinDiasActivosError(EstimandoDiarioError):
    """No hay ningún día activo: el efecto condicional no existe en esa muestra.

    Tipo propio —y no el genérico— porque un remuestreo de bloques puede caer
    legítimamente en una ventana sin días activos, y quien remuestrea necesita
    distinguir ese caso de una violación del contrato de los datos.
    """


# ------------------------------------------------------------------- registro
@dataclass(frozen=True)
class RegistroDiario:
    """Un día calendario elegible. Existe aunque no tenga zonas.

    `tipo_de_dia` es el estado calendario del día (`COMPLETO`,
    `CIERRE_SEMANAL`, …), tal como lo trae el manifiesto del censo a través de
    `cargar_dias_de_estudio`.
    """

    fecha: str
    tipo_de_dia: str | None
    n_real: int
    sum_real: float
    n_nulo: int
    sum_nulo: float

    @property
    def activo(self) -> int:
        """1 si el día aporta al efecto condicional. `activo = 1[n_real > 0]`."""
        return 1 if self.n_real > 0 else 0

    @property
    def v(self) -> float:
        """Peso del día en el denominador. Igual para todo día activo."""
        return float(self.activo)

    @property
    def u(self) -> float:
        """Efecto del día, ya multiplicado por `activo`.

        En un día inactivo devuelve 0.0 **sin evaluar** `sum/n`: no es que el
        efecto valga cero, es que no entra a ningún lado (`v = 0`). Calcularlo
        sería un `0/0`.
        """
        if not self.activo:
            return 0.0
        return self.sum_real / self.n_real - self.sum_nulo / self.n_nulo


def _cuenta(valor, campo, fecha):
    n = int(valor)
    if n != valor or n < 0:
        raise EstimandoDiarioError(
            "%s: `%s` debe ser entero >= 0, vino %r" % (fecha, campo, valor))
    return n


def _suma(valor, campo, fecha):
    s = float(valor)
    if not np.isfinite(s):
        raise EstimandoDiarioError(
            "%s: `%s` no es finito (%r)" % (fecha, campo, valor))
    return s


def _fechas_en_orden(items, que):
    """Fechas estrictamente crecientes. Duplicado o desorden = FALLA."""
    previa = None
    for it in items:
        f = it.get("fecha")
        if not f:
            raise EstimandoDiarioError("%s: hay una entrada sin `fecha`" % que)
        if previa is not None and f <= previa:
            raise EstimandoDiarioError(
                "%s: fechas duplicadas o fuera de orden (%s despues de %s). No "
                "se reordena ni se deduplica en silencio: un registro diario "
                "desordenado rompe la contiguidad que los bloques preservan"
                % (que, f, previa))
        previa = f


def construir_registro(dias, *, calendario=None):
    """Registro diario validado, uno por día calendario elegible.

    `dias`: iterable de mappings con `fecha`, `n_real`, `sum_real`, `n_nulo`,
        `sum_nulo` y opcionalmente `tipo_de_dia`. Son agregados POR DÍA: este
        módulo no ve eventos sueltos.
    `calendario`: opcional, iterable de mappings con `fecha` (+ `tipo_de_dia`),
        que es exactamente lo que devuelve
        `edgelab.research.universo_estudio.cargar_dias_de_estudio`. Si se pasa,
        los días del calendario que no aparecen en `dias` se agregan como días
        CERO (`n_real = 0`), y un día con zonas que NO está en el calendario
        **falla ruidoso** en vez de compararse contra un nulo que no lo cubre.

    Sin `calendario` no se completa ningún día ausente: rellenar exigiría saber
    qué días son elegibles —mantenimiento, feriados, domingos— y eso lo sabe la
    puerta única del universo, no este módulo. Sin él, la secuencia recibida
    ES el calendario, y el que llama se hace cargo.
    """
    dias = list(dias)
    _fechas_en_orden(dias, "dias")

    crudos = {}
    for d in dias:
        f = d["fecha"]
        n_real = _cuenta(d["n_real"], "n_real", f)
        n_nulo = _cuenta(d["n_nulo"], "n_nulo", f)
        sum_real = _suma(d["sum_real"], "sum_real", f)
        sum_nulo = _suma(d["sum_nulo"], "sum_nulo", f)
        if n_real == 0 and sum_real != 0.0:
            raise EstimandoDiarioError(
                "%s: n_real = 0 pero sum_real = %r. Un dia sin eventos no puede "
                "tener suma" % (f, sum_real))
        # Emparejamiento uno-a-uno, SOLO exigible en dias activos: es el dia
        # activo el que compara real contra nulo. En un dia inactivo el lado
        # nulo no se usa (u = v = 0) y no se le impone nada.
        if n_real > 0 and n_real != n_nulo:
            raise EstimandoDiarioError(
                "%s: dia activo sin emparejamiento uno-a-uno (n_real = %d, "
                "n_nulo = %d). Medias sobre conteos distintos no son la misma "
                "comparacion: el lado con mas observaciones entra con menos "
                "ruido y la diferencia deja de ser el efecto del dia"
                % (f, n_real, n_nulo))
        crudos[f] = (d.get("tipo_de_dia"), n_real, sum_real, n_nulo, sum_nulo)

    if calendario is None:
        return [RegistroDiario(f, *crudos[f]) for f in (d["fecha"] for d in dias)]

    calendario = list(calendario)
    _fechas_en_orden(calendario, "calendario")
    elegibles = {c["fecha"]: c.get("tipo_de_dia") for c in calendario}
    fuera = sorted(f for f in crudos if f not in elegibles)
    if fuera:
        raise EstimandoDiarioError(
            "hay dias con datos fuera del calendario elegible: %s. El estudio y "
            "su nulo tienen que cubrir EXACTAMENTE los mismos dias; comparar un "
            "dia que el nulo no cubre es compararlo contra el nulo equivocado"
            % ", ".join(fuera[:5]))

    out = []
    for f, tipo in elegibles.items():
        if f in crudos:
            tipo_obs, n_real, sum_real, n_nulo, sum_nulo = crudos[f]
            out.append(RegistroDiario(f, tipo_obs if tipo is None else tipo,
                                      n_real, sum_real, n_nulo, sum_nulo))
        else:
            # Dia CERO explicito, autorizado por el calendario canonico. No es
            # una imputacion: es un dia elegible en el que el feature no disparo.
            out.append(RegistroDiario(f, tipo, 0, 0.0, 0, 0.0))
    return out


# ---------------------------------------------------------------- estimación
def serie_uv(registros):
    """`(u, v)` alineadas con el calendario COMPLETO, días cero incluidos.

    Devolver la serie entera —y no sólo los días activos— es lo que permite que
    el remuestreo por bloques opere sobre días calendario contiguos.
    """
    u = np.array([r.u for r in registros], dtype=np.float64)
    v = np.array([r.v for r in registros], dtype=np.float64)
    return u, v


def theta_de_uv(u, v):
    """`sum(u) / sum(v)` sobre la muestra que se le pase.

    Es el ÚNICO camino al estimador: una réplica de bootstrap indexa `u` y `v`
    por sus bloques de días calendario y vuelve a llamar acá. Nunca se
    promedian efectos diarios ya calculados sobre una lista precomprimida de
    días activos.
    """
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    if u.shape != v.shape or u.ndim != 1:
        raise EstimandoDiarioError(
            "u y v tienen que ser 1-D y de la misma longitud (%s vs %s)"
            % (u.shape, v.shape))
    if not np.all(np.isfinite(u)) or not np.all(np.isfinite(v)):
        raise EstimandoDiarioError("u o v traen valores no finitos")
    if np.any(v < 0):
        raise EstimandoDiarioError("v tiene pesos negativos")
    fantasma = (v == 0) & (u != 0)
    if np.any(fantasma):
        raise EstimandoDiarioError(
            "%d dia(s) con v = 0 y u != 0: un dia inactivo no puede aportar "
            "efecto" % int(fantasma.sum()))
    den = float(v.sum())
    if den <= 0:
        raise SinDiasActivosError(
            "la muestra no tiene ningun dia activo (%d dias calendario, 0 "
            "activos): el efecto condicional no esta definido. No se devuelve "
            "0 ni NaN" % u.size)
    return float(u.sum()) / den


def estimar(registros):
    """Estimador primario y los conteos que hacen falta para leerlo.

    `n_dias_calendario` y `n_dias_activos` van juntos a propósito: `theta` sin
    saber sobre cuántos días activos se calculó, y sobre cuántos días calendario
    se los buscó, no se puede interpretar.
    """
    registros = list(registros)
    if not registros:
        raise EstimandoDiarioError("registro diario vacio")
    u, v = serie_uv(registros)
    return dict(
        theta=theta_de_uv(u, v),
        n_dias_calendario=len(registros),
        n_dias_activos=int(v.sum()),
        n_eventos_reales=int(sum(r.n_real for r in registros)),
        n_eventos_nulos=int(sum(r.n_nulo for r in registros if r.activo)),
        fecha_min=registros[0].fecha,
        fecha_max=registros[-1].fecha)
