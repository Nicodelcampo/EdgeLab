"""Prototipo sintético para revisión; aún no integrado ni autorizado para datos reales.

Opera una sola señal con ticks last ordenados y una única sesión y segmento.
El calendario debe ser completo y point-in-time; recibe ventanas bloqueadas
preverificadas. No descubre señales ni selecciona filtros.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Operacion:
    fill_ns: int
    exit_ns: int
    entry: float
    exit: float
    stop: float
    riesgo: float
    neto_r: float
    motivo: str


def simular(ts, px, *, senal_ns, cierre_ns, fin_sesion_ns, lado, stop, friccion_pts, bloqueos=()):
    """Sólo para pruebas sintéticas mientras el resto de guardas sigue abierto.

    Para elegibilidad se usa [señal, cierre programado] ANTES de inspeccionar
    el fill o salida: ningún filtrado en función del resultado. Bloqueos son
    intervalos cerrados (inicio_ns, fin_ns). El llamador debe verificar que
    ticks sean de la misma sesión/contrato y que el cierre sea operable.
    `fin_sesion_ns` es un límite exclusivo, certificado externamente: no
    prueba que la captura sea completa ni autoriza aceptar cualquier demora.
    Devuelve None para señal vetada o sin fill válido; falta de datos durante
    una posición abierta es error, nunca se convierte silenciosamente en P&L.
    Fricción se descuenta una vez en puntos antes de dividir por riesgo inicial.
    """
    t=np.asarray(ts,dtype=np.int64); p=np.asarray(px,dtype=float)
    if len(t)!=len(p) or np.any(np.diff(t)<0) or not np.all(np.isfinite(p)) or np.any(p<=0):
        raise ValueError('ticks inválidos o desordenados')
    if lado not in (-1,1) or not np.isfinite(stop) or not np.isfinite(friccion_pts) or friccion_pts<0:
        raise ValueError('dirección, stop o fricción inválidos')
    if not senal_ns < cierre_ns < fin_sesion_ns:
        raise ValueError('señal, cierre o límite de sesión inválido')
    for a,b in bloqueos:
        if a>b: raise ValueError('ventana invertida')
        if a<=cierre_ns and b>=senal_ns: return None
    # La vela termina en señal_ns; el diseño exige un tick estrictamente posterior.
    # Con timestamps empatados no inventamos un orden intrananosegundo.
    i=int(np.searchsorted(t,senal_ns,side='right'))
    if i>=len(t) or t[i]>=cierre_ns: return None
    entrada=float(p[i]); riesgo=lado*(entrada-stop)
    if riesgo<=0: return None
    for j in range(i+1,len(t)):
        if t[j]>=fin_sesion_ns:
            raise ValueError('salida fuera de la sesión certificada')
        if t[j]>=cierre_ns:
            if any(a <= t[j] and b >= cierre_ns for a, b in bloqueos):
                raise ValueError('el tick de salida cruza una ventana de noticias')
            salida=float(p[j]); return Operacion(int(t[i]),int(t[j]),entrada,salida,float(stop),float(riesgo),
                float((lado*(salida-entrada)-friccion_pts)/riesgo),'CIERRE')
        if lado*(p[j]-stop)<=0:
            salida=float(p[j]); return Operacion(int(t[i]),int(t[j]),entrada,salida,float(stop),float(riesgo),
                float((lado*(salida-entrada)-friccion_pts)/riesgo),'STOP')
    raise ValueError('posición sin datos de salida verificable')
