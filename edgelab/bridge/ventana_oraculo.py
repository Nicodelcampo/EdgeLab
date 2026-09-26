# -*- coding: utf-8 -*-
"""Ventana de DATOS != ventana de COMPARACIÓN (`nt8_indicator_parity_contract.md`,
sección del mismo nombre, 2026-07-27). **Específico de BigTrap2 con secuenciador
causal — no un warm-up genérico.**

## Por qué esto no es "dale más historia y ya"

La propia regla del contrato lo prohíbe con un contraejemplo real: el oráculo de
`Gaps2` se generó con el chart arrancando **en** la ventana de comparación, y
darle un mes de historia de más hizo que Python dejara de reproducir sus
primeras zonas. **La ventana de datos es una propiedad del oráculo particular,
no una constante del arnés.** Lo que se implementa acá vale para BigTrap2
porque la evidencia YA está medida: la regla de warm-up (`warmup.py`) mide 0
zonas creadas en la primera sesión de cualquier ventana BigTrap2 v2.2 — eso
sólo pasa si el chart cargó **al menos una sesión completa antes** del primer
evento exportado. Para un oráculo cuya evidencia dijera lo contrario (como
`Gaps2`), este módulo no aplicaría.

## Las dos ventanas

- **Datos**: desde el primer tick de la sesión ANTERIOR a la que contiene el
  primer evento del oráculo. Se DERIVA de `bars.session_ids` sobre lo que ya
  esté cargado — nunca una constante de minutos fija (el margen fijo es
  exactamente lo que falló: alcanza un día de semana, no alcanza un domingo de
  reapertura semanal, como quedó medido).
- **Comparación**: recortada a la ventana temporal que el oráculo realmente
  cubre (su primer y último evento). Generar con más datos no autoriza a
  comparar más zonas que las que el oráculo pudo haber visto.
"""
from __future__ import annotations

import numpy as np

from . import bars as bars_mod

__all__ = ["SinSesionAnteriorError", "inicio_de_ventana_de_datos",
           "recortar_a_ventana_de_oraculo"]


class SinSesionAnteriorError(ValueError):
    """La red de ticks cargada para BUSCAR la frontera no alcanza a cubrir la
    sesión anterior a la del primer evento. Hay que cargar con más margen
    hacia atrás antes de poder derivar la ventana de datos -- nunca asumir un
    valor."""


def inicio_de_ventana_de_datos(ts_ns_amplios, primer_evento_ns) -> int:
    """ns UTC del primer tick de la sesión ANTERIOR a la del primer evento.

    "Anterior" es la sesión con `session_id` más alto entre los estrictamente
    MENORES al del primer evento -- no necesariamente `session_id - 1`. Un
    fin de semana o feriado salta valores de `session_id` sin que exista
    ningún tick con esos valores (medido: un cierre de viernes a reapertura
    de domingo salta DOS enteros de `session_id`, no uno). Restar 1 a ciegas
    apunta a una sesión vacía y falla donde no debería.

    `ts_ns_amplios` tiene que cubrir generosamente hacia atrás -- esto
    ENCUENTRA la frontera, no la asume. Si ninguna sesión anterior está
    presente en `ts_ns_amplios`, levanta `SinSesionAnteriorError`: cargar de
    más "por las dudas" silenciosamente sería reintroducir el mismo error
    que un margen fijo en minutos.
    """
    ts_ns_amplios = np.asarray(ts_ns_amplios)
    if len(ts_ns_amplios) == 0:
        raise SinSesionAnteriorError("red de busqueda vacia")
    ses = bars_mod.session_ids(ts_ns_amplios)
    idx_evento = int(np.searchsorted(ts_ns_amplios, primer_evento_ns))
    if idx_evento >= len(ts_ns_amplios):
        raise SinSesionAnteriorError(
            "el primer evento del oraculo cae fuera de la red de busqueda cargada")
    s_evento = ses[idx_evento]
    anteriores = ses[ses < s_evento]
    if not len(anteriores):
        raise SinSesionAnteriorError(
            "la red de busqueda no cubre ninguna sesion anterior a la del primer "
            "evento (session_id=%d); ampliar el rango hacia atras, no asumir" % s_evento)
    s_prev = int(anteriores.max())
    inicio_idx = np.flatnonzero(ses == s_prev)[0]
    return int(ts_ns_amplios[inicio_idx])


def recortar_a_ventana_de_oraculo(zonas, inicio_ms, fin_ms, campo="created_ms"):
    """Sólo zonas con `campo` dentro de `[inicio_ms, fin_ms]` del oráculo.

    Generar sobre una ventana de DATOS más ancha no autoriza a comparar zonas
    que el oráculo nunca tuvo la chance de ver."""
    return [z for z in zonas
            if z.get(campo) is not None and inicio_ms <= z[campo] <= fin_ms]
