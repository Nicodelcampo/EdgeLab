# -*- coding: utf-8 -*-
"""Estimando diario canónico de EXPLORE-001 (Diseño B). **La unidad es el DÍA.**

Este módulo implementa el estadístico observado descrito en §1.3 de
ESPEC_TEST_EXPLORE-001.md:

    p_dia(d) = sum_objetivo(d) / n_eventos(d)
    p_global = mean_d p_dia(d)   sobre días con n_eventos(d) > 0

Representado sobre el calendario COMPLETO como un ratio de sumas:

    activo_d = 1[n_eventos(d) > 0]
    u_d      = activo_d * p_dia(d)
    v_d      = activo_d
    p_global = sum_d u_d / sum_d v_d

## Dominio del outcome

`p_dia(d)` es una **proporción**, pero tanto el numerador como el denominador
son **conteos enteros**:

  - `n_eventos` es entero >= 0;
  - `sum_objetivo` es entero >= 0 y <= `n_eventos`;
  - `sum_objetivo` es la cantidad de eventos cuyo outcome fue OBJETIVO, no una
    suma ponderada ni un outcome fraccional;
  - si `n_eventos == 0` entonces `sum_objetivo == 0`.

Si algún día requiriera un outcome continuo (ticks, MFE, probabilidades, etc.)
el estimando sería distinto: este módulo NO lo soporta y debe fallar ruidoso si
se le pasa algo que no es un conteo entero de objetivos.

## Una sola muestra por ejecución

`RegistroDiario` recibe UNA muestra de eventos por ejecución: la observada real
o una realización concreta de la MCPT. Nunca ambas a la vez, y nunca el pool
completo de anclas placebo.

La construcción de la distribución nula (MCPT) vive FUERA de este módulo: éste
sólo expone la primitiva `construir_registro` + `serie_uv` + `theta_de_uv` que
un remuestreo puede invocar sobre cada realización.

## Días sin eventos

Los días sin eventos **no aportan al estimador** (`u=0`, `v=0`), pero
**permanecen en la secuencia calendario**. Al remuestrear bloques se
remuestrean **registros diarios completos**: un bloque de `b` días calendario
contiene un número VARIABLE de días activos. Comprimir la serie primero —tirar
los días cero y armar bloques después— cambia qué días quedan contiguos y por
lo tanto distorsiona la estructura de dependencia temporal.

`serie_uv` devuelve la serie completa y `theta_de_uv` recompute el ratio desde
las sumas de la muestra: **nunca desde una lista precomprimida de días activos**.

Un día sin eventos no recibe "efecto cero": eso lo metería al denominador y
sesgaría `p_global` hacia cero en proporción a cuántos días el feature no
dispara. `v_d = 0` dice "este día no opina", que es distinto de "este día opina
cero".

## Calendario y zona horaria

Las fechas son fechas de sesión en `America/Chicago`. El módulo no rellena días
ausentes salvo que se le pase el calendario canónico de
`cargar_dias_de_estudio`; saber qué día es elegible (mantenimiento, feriados,
domingos) es competencia de la puerta única del universo, no de este módulo.

`tipo_de_dia` puede ser `None` para callers que no dispongan del calendario
oficial, pero los callers de producción siempre deben proveer el valor que
devuelve `cargar_dias_de_estudio` (`COMPLETO`, `CIERRE_SEMANAL`, etc.).

## Lo que este módulo NO hace

No estima largo de bloque, no remuestrea, no calcula intervalos, no toca costos,
no genera realizaciones nulas, no compara real contra nulo. Recibe conteos y
sumas ya agregados por día y devuelve el registro validado más el ratio. El
bootstrap, la MCPT y el resto de la inferencia van aparte y consumen
`serie_uv` + `theta_de_uv`.

## Degradación silenciosa: prohibida

Una muestra sin días activos NO devuelve 0, NaN ni inf: levanta
`SinDiasActivosError`. Un `0/0` convertido en `nan` que viaja por un bootstrap
es un intervalo inventado con cara de resultado. `SinDiasActivosError` es una
subclase propia para que quien remuestrea pueda distinguir un bloque
degenerado (caso legítimo) de una violación del contrato de los datos.
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
    """Un día calendario elegible. Existe aunque no tenga eventos.

    `tipo_de_dia` es el estado calendario del día (`COMPLETO`,
    `CIERRE_SEMANAL`, …), tal como lo trae el manifiesto del censo a través de
    `cargar_dias_de_estudio`. Puede ser `None` para callers sin calendario
    canónico, aunque en producción siempre debe venir poblado.

    `n_eventos` y `sum_objetivo` son conteos enteros: `sum_objetivo` es la
    cantidad de eventos cuyo outcome fue OBJETIVO, no una suma ponderada ni un
    outcome fraccional. `p_dia(d)` es float porque la división de dos enteros en
    Python devuelve float, pero ambos campos de entrada son enteros.
    """

    fecha: str
    tipo_de_dia: str | None
    n_eventos: int
    sum_objetivo: int

    @property
    def activo(self) -> int:
        """1 si el día aporta al estimador. `activo = 1[n_eventos > 0]`."""
        return 1 if self.n_eventos > 0 else 0

    @property
    def v(self) -> float:
        """Peso del día en el denominador. Igual para todo día activo."""
        return float(self.activo)

    @property
    def u(self) -> float:
        """Efecto del día, ya multiplicado por `activo`.

        En un día inactivo devuelve 0.0 **sin evaluar** `sum/n_eventos`: no es
        que el efecto valga cero, es que no entra a ningún lado (`v = 0`).
        Calcularlo sería un `0/0`.
        """
        if not self.activo:
            return 0.0
        return self.sum_objetivo / self.n_eventos


def _entero(valor, campo, fecha):
    """Conteo entero no negativo, con validación ordenada:

      1. rechazar bool;
      2. rechazar NaN / +inf / -inf;
      3. rechazar no entero;
      4. rechazar negativo.
    """
    if isinstance(valor, bool):
        raise EstimandoDiarioError(
            "%s: `%s` no acepta bool, vino %r" % (fecha, campo, valor))
    s = float(valor)
    if not np.isfinite(s):
        raise EstimandoDiarioError(
            "%s: `%s` no es finito, vino %r" % (fecha, campo, valor))
    n = int(s)
    if n != s:
        raise EstimandoDiarioError(
            "%s: `%s` debe ser entero, vino %r" % (fecha, campo, valor))
    if n < 0:
        raise EstimandoDiarioError(
            "%s: `%s` debe ser >= 0, vino %r" % (fecha, campo, valor))
    return n


def _suma_objetivo(valor, campo, fecha, n_eventos):
    """Conteo entero de outcomes OBJETIVO, con validación ordenada:

      1. rechazar bool;
      2. rechazar NaN / +inf / -inf;
      3. rechazar no entero;
      4. rechazar negativo;
      5. rechazar sum_objetivo > n_eventos;
      6. si n_eventos == 0, exigir sum_objetivo == 0.
    """
    s = _entero(valor, campo, fecha)
    if s > n_eventos:
        raise EstimandoDiarioError(
            "%s: `%s` = %d excede n_eventos = %d"
            % (fecha, campo, s, n_eventos))
    if n_eventos == 0 and s != 0:
        raise EstimandoDiarioError(
            "%s: `%s` debe ser 0 cuando n_eventos == 0, vino %d"
            % (fecha, campo, s))
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

    `dias`: iterable de mappings con `fecha`, `n_eventos`, `sum_objetivo` y
        opcionalmente `tipo_de_dia`. Son agregados POR DÍA: este módulo no ve
        eventos sueltos. Representan UNA muestra de eventos por ejecución
        (observada real o una realización MCPT), nunca el pool completo de
        anclas junto con los eventos reales.
    `calendario`: opcional, iterable de mappings con `fecha` (+ `tipo_de_dia`),
        que es exactamente lo que devuelve
        `edgelab.research.universo_estudio.cargar_dias_de_estudio`. Si se pasa,
        los días del calendario que no aparecen en `dias` se agregan como días
        CERO (`n_eventos = 0`), y un día con eventos que NO está en el
        calendario **falla ruidoso** en vez de usarse fuera del universo
        declarado.

    Sin `calendario` no se completa ningún día ausente: rellenar exigiría saber
    qué días son elegibles —mantenimiento, feriados, domingos— y eso lo sabe la
    puerta única del universo, no este módulo. Sin él, la secuencia recibida ES
    el calendario, y el que llama se hace cargo.
    """
    dias = list(dias)
    _fechas_en_orden(dias, "dias")

    crudos = {}
    for d in dias:
        f = d["fecha"]
        n_eventos = _entero(d["n_eventos"], "n_eventos", f)
        sum_objetivo = _suma_objetivo(d["sum_objetivo"], "sum_objetivo", f,
                                      n_eventos)
        crudos[f] = (d.get("tipo_de_dia"), n_eventos, sum_objetivo)

    if calendario is None:
        return [RegistroDiario(f, *crudos[f]) for f in (d["fecha"] for d in dias)]

    calendario = list(calendario)
    _fechas_en_orden(calendario, "calendario")
    elegibles = {c["fecha"]: c.get("tipo_de_dia") for c in calendario}
    fuera = sorted(f for f in crudos if f not in elegibles)
    if fuera:
        raise EstimandoDiarioError(
            "hay dias con datos fuera del calendario elegible: %s. El estudio y "
            "su nulo tienen que cubrir EXACTAMENTE los mismos dias; usar un dia "
            "que el calendario no autoriza es compararlo contra el universo "
            "equivocado"
            % ", ".join(fuera[:5]))

    out = []
    for f, tipo in elegibles.items():
        if f in crudos:
            tipo_obs, n_eventos, sum_objetivo = crudos[f]
            out.append(RegistroDiario(f, tipo_obs if tipo is None else tipo,
                                      n_eventos, sum_objetivo))
        else:
            # Día CERO explícito, autorizado por el calendario canónico. No es
            # una imputación: es un día elegible en el que el feature no disparó.
            out.append(RegistroDiario(f, tipo, 0, 0))
    return out


# ---------------------------------------------------------------- estimación
def serie_uv(registros):
    """`(u, v)` alineadas con el calendario COMPLETO, días cero incluidos.

    Devolver la serie entera —y no sólo los días activos— es lo que permite que
    el remuestreo por bloques opere sobre días calendario contiguos, y que un
    prefijo recursivo [1, t] conserve el calendario.
    """
    u = np.array([r.u for r in registros], dtype=np.float64)
    v = np.array([r.v for r in registros], dtype=np.float64)
    return u, v


def theta_de_uv(u, v):
    """`sum(u) / sum(v)` sobre la muestra que se le pase.

    Es el ÚNICO camino al estimador:

      - una réplica de bootstrap estacionario indexa `u` y `v` por bloques de
        días calendario y vuelve a llamar acá;
      - un estimador fixed-b sobre el bloque [j, j+l-1] pasa el slice y recalcula
        el ratio desde sus propias sumas;
      - un estimador recursivo / self-normalizado sobre el prefijo [1, t] pasa
        el prefijo y recalcula el ratio desde sus propias sumas.

    Nunca se promedian efectos diarios ya calculados sobre una lista
    precomprimida de días activos.
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
        n_eventos=sum(r.n_eventos for r in registros),
        sum_objetivo=sum(r.sum_objetivo for r in registros),
        fecha_min=registros[0].fecha,
        fecha_max=registros[-1].fecha)
