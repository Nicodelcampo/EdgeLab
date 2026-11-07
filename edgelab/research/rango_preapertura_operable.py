"""Lo que de PREAPERTURA-ES y PREAPERTURA-NQ se puede operar sin inventar cortes.

Coordenadas publicadas en series_diarias_regimen_20261106.json. El eje de ancho
es un tercil de cuantiles del E0 y esos cortes no están archivados: no entra
en la orden. El resto de cada coordenada sí está fijo en rango_ruptura.
"""
from __future__ import annotations

COORD_ES = (2, 0, 1, 0, 0, 5)
COORD_NQ = (2, 0, 0, 0, 1, 5)


def especificar(coord: tuple) -> dict:
    if len(coord) != 6:
        raise ValueError("la celda de preapertura tiene 6 ejes")
    cuerpo, volumen, ancho, eficiencia, intento, ejecucion = coord
    if cuerpo != 2 or volumen != 0 or eficiencia != 0 or ejecucion != 5:
        raise ValueError("esta traducción no cubre otra celda de preapertura")
    if intento not in (0, 1) or ancho not in (0, 1):
        raise ValueError("intento o ancho fuera de las dos celdas publicadas")
    return {
        "instrumento": "ES" if coord == COORD_ES else ("NQ" if coord == COORD_NQ else "otro"),
        "cuerpo": "cualquiera",
        "volumen": "cualquiera",
        "eficiencia": "cualquiera",
        "ancho_tercil_publicado": "alto" if ancho == 1 else "bajo",
        "ancho_en_la_orden": False,
        "intento": intento,
        "stop": "OPUESTO",
        "objetivo": "SALIDA",
        "rango_cierre_et": "09:16-09:30",
        "entradas_hasta_et": "11:30",
        "salida_forzada_et": "15:55",
        "min_velas_de_rango": 12,
    }
