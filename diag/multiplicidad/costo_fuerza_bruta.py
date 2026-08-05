# -*- coding: utf-8 -*-
"""Costo de multiplicidad de una fuerza bruta sobre ruptura de rango horario.

Contesta una sola pregunta: **si se barre el espacio completo de la hipotesis
"que rango, roto con que caracteristicas, con que SL y que TP", cuanto sube el
MDE por la correccion de multiples pruebas?**

Justificacion economica: el orden en que se construyen las piezas del pipeline
depende de cual es el obstaculo REAL. Si la multiplicidad fuera el obstaculo,
la prioridad seria recortar la grilla; si no lo es, la prioridad es otra y
recortar la grilla no compra nada. Esto lo decide un numero, no una intuicion.

Como podria refutarse: si la calibracion contra los dos puntos ya registrados
en `docs/ESPEC_TEST_EXPLORE-001.md` (M_eff=21,2 -> z=3,041 y M_eff=106 ->
z=3,496) no reprodujera esos z, la regla de correccion supuesta aca (Bonferroni
bilateral) no seria la que el expediente usa y toda la tabla quedaria invalida.
La calibracion es un assert, no un comentario.

Sin dependencias fuera de la stdlib (scipy NO esta en el lock base).
"""
import json
import sys
from statistics import NormalDist

N = NormalDist()

# --- puntos de calibracion, tomados de docs/ESPEC_TEST_EXPLORE-001.md ---------
ALPHA = 0.05          # bilateral
POTENCIA = 0.80
MDE_BASE = 1.14       # ticks/trade, a f=1, con M_eff = 21,2
CALIBRACION = ((21.2, 3.041), (106.0, 3.496))
MARGEN_MEDIDO_F10 = 1.60   # 2-ter: "El margen medido a f=10 es 1,60x"

# --- ejes del espacio de busqueda --------------------------------------------
# Cada eje es una decision que HOY NO ESTA TOMADA. La grilla es ilustrativa del
# orden de magnitud, no una propuesta sellada: sellarla exige un manifiesto.
EJES = [
    ("inicio del rango (hora)", 24),
    ("duracion del rango", 6),
    ("caracteristica de la ruptura", 12),   # cierre/mecha, N ticks, volumen, retest
    ("ancho del SL", 8),
    ("ancho del TP", 8),
    ("estatico vs dinamico (ATR)", 2),
    ("indicador como filtro (o ninguno)", 6),
]


def z_bonferroni(m, alpha=ALPHA):
    """z critico bilateral con correccion de Bonferroni sobre `m` hipotesis."""
    return N.inv_cdf(1 - (alpha / m) / 2)


def mde(m):
    """MDE en ticks, escalado desde el punto base. (z_alpha + z_beta) * SE, con
    SE constante: lo unico que cambia entre celdas es el z critico."""
    zb = N.inv_cdf(POTENCIA)
    z0 = z_bonferroni(CALIBRACION[0][0])
    return MDE_BASE * (z_bonferroni(m) + zb) / (z0 + zb)


def main():
    for m, z_esperado in CALIBRACION:
        obtenido = z_bonferroni(m)
        assert abs(obtenido - z_esperado) < 5e-4, (
            "la regla de correccion supuesta no reproduce el expediente: "
            "M_eff=%s daba z=%s y este modelo da z=%.4f" % (m, z_esperado, obtenido))

    m_total = 1
    ejes = []
    for nombre, k in EJES:
        m_total *= k
        ejes.append({"eje": nombre, "valores": k, "acumulado": m_total})

    filas = []
    for m in [CALIBRACION[0][0], CALIBRACION[1][0], 1e3, 1e4, 1e5, m_total]:
        filas.append({
            "M_eff": m,
            "z": round(z_bonferroni(m), 4),
            "mde_ticks": round(mde(m), 4),
            "factor_vs_base": round(mde(m) / MDE_BASE, 4),
        })

    factor = mde(m_total) / MDE_BASE
    res = {
        "ejes": ejes,
        "M_fuerza_bruta": m_total,
        "tabla": filas,
        "factor_fuerza_bruta": round(factor, 4),
        "margen_medido_f10": MARGEN_MEDIDO_F10,
        "entra_en_el_margen": bool(factor <= MARGEN_MEDIDO_F10),
        # La conclusion que importa, y es contraintuitiva:
        "conclusion": (
            "Bonferroni es logaritmico: z ~ sqrt(2 ln M). Un millon de celdas "
            "cuesta +%.0f%% de MDE, no un orden de magnitud. Y M_eff real es "
            "MUCHO menor que M (un SL de 12t y uno de 13t son casi la misma "
            "hipotesis), asi que este numero es COTA SUPERIOR. La multiplicidad "
            "no es el obstaculo de esta familia." % ((factor - 1) * 100)
        ),
    }
    json.dump(res, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
