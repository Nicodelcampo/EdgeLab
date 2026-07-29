# -*- coding: utf-8 -*-
"""Exclusión de warm-up para el arnés de paridad. **Condición de comparabilidad
de oráculos, no regla de construcción de barras.**

## Por qué vive acá y no en `bars.py`

`docs/nt8_indicator_parity_contract.md`, sección *"REGLA — la primera sesión de
toda carga de chart es WARM-UP"*: NT8 reinicia su conteo de ticks en cada
frontera de sesión, y un chart que arranca a mitad de sesión no puede alinearse
con esa cuenta hasta la frontera siguiente. Es una propiedad de **cómo NT8
carga un chart para exportar un oráculo**, no una propiedad del stream de ticks
ni de cómo Python construye barras. En producción no hay carga de chart — se
construye desde el parquet completo y todas las sesiones salen bien — así que
esta exclusión sólo tiene sentido **al comparar contra un oráculo**, nunca al
generar. Ponerla en `bars.py` cambiaría la geometría de producción para
absorber un artefacto de NinjaTrader; el warm-up se filtra en el arnés de
paridad, después de generar, nunca antes.

## Qué hace

`primera_frontera_ns` usa el mismo criterio de sesión que `bars.session_ids`
(17:00 CT, DST-aware) — no inventa uno nuevo — para encontrar el primer cambio
de sesión dentro de la ventana de ticks. Todo lo anterior a esa frontera es
warm-up y se excluye de ambos lados (Python y NT8) antes de compararlos.

`excluir_zonas_de_warmup` filtra por `created_ms`: una zona nacida antes de la
frontera no es comparable, sin importar qué le pase después.
"""
from __future__ import annotations

import numpy as np

from . import bars as bars_mod

__all__ = ["SinFronteraDeSesionError", "primera_frontera_ns",
           "excluir_zonas_de_warmup"]


class SinFronteraDeSesionError(ValueError):
    """La ventana no cruza ninguna frontera de sesión: no hay warm-up que
    excluir porque no hay una segunda sesión con la que compararse."""


def primera_frontera_ns(ts_ns) -> int:
    """ns UTC del primer cambio de sesión — fin de la sesión de warm-up.

    Levanta `SinFronteraDeSesionError` si la ventana entera cae en una sola
    sesión: en ese caso TODA la ventana es warm-up y no hay nada comparable,
    lo que hay que reportar explícitamente, no silenciar con un corte a ciegas.
    """
    ts_ns = np.asarray(ts_ns)
    if len(ts_ns) == 0:
        raise SinFronteraDeSesionError("ventana de ticks vacía")
    ses = bars_mod.session_ids(ts_ns)
    cambios = np.flatnonzero(np.diff(ses))
    if not len(cambios):
        raise SinFronteraDeSesionError(
            "la ventana no cruza ninguna frontera de sesión (todo es warm-up "
            "de la primera carga): %d ticks, sesión única" % len(ts_ns))
    return int(ts_ns[cambios[0] + 1])


def excluir_zonas_de_warmup(zonas, frontera_ns, campo="created_ms"):
    """Zonas con `campo` (unix ms) anterior a la frontera quedan afuera.

    Zonas sin el campo (`None`) se excluyen también: no hay forma de saber si
    nacieron en warm-up, y dejarlas entrar de rebote sería el mismo error que
    la regla busca evitar."""
    frontera_ms = frontera_ns // 1_000_000
    return [z for z in zonas
            if z.get(campo) is not None and z[campo] >= frontera_ms]
