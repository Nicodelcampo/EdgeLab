# -*- coding: utf-8 -*-
"""Reconstruccion del MDE de 1,14 -- y por que NO da.

## Que se intenta

`docs/ESPEC_TEST_EXPLORE-001.md` usa **MDE = 1,14 ticks a f=1** y **0,39 a
f=10** como el numero que sostiene toda la discusion de factibilidad: de ahi
sale la banda entre lo detectable y lo operable, el margen de 1,60x que
justifico el barrido de resolucion, y el costo en MDE de ampliar la grilla.

**Ningun script del repo lo calcula.** `unidad4_por_geometria.py` emite
varianzas por geometria pero no un MDE; `unidad2_grilla.py` y
`unidad3_deflacion.py` lo nombran en sus docstrings y no lo computan. Verificado
con `grep` de `norm.ppf`, `z_beta`, `potencia` y `0.8416` sobre todo `diag/`.

## Como deberia salir, con los insumos que SI estan persistidos

De `diag/spike_in/neff.json` (control interno: `anclas/DEFF` reproduce
`N_eff` exacto):

    DEFF = 4,864 · N_eff_placebo = 9.707 · anclas/dia = 255,2 · dias = 185

De `docs/ESPEC_TEST_EXPLORE-001.md` y `p_pasar_prop_firm.py`:

    SD = 8,77 ticks/trade · M_eff = 21,2 · potencia 80% · alfa 0,05 bilateral

Y la formula de deflacion que declara `unidad3_deflacion.py`:

    MDE_real = MDE_placebo · sqrt(N_eff_placebo / N_eff_real)

## El resultado

    z(21,2) = 3,0409   z_beta = 0,8416   k = 3,8826
    MDE_placebo = k · SD / sqrt(9707) = 0,3456

    f       N_eff_real   calculado   ESPEC   ratio
    1              200      2,4077    1,14    2,11
    10           2.000      0,7614    0,39    1,95

**Da entre 1,95x y 2,11x el valor publicado.** La razon se mantiene aprox.
constante entre f=1 y f=10, o sea que el escalado con `n` es correcto y lo que
difiere es un factor global — no un error de exponente.

## Que puede explicar el factor ~2, y por que no lo elijo

Hipotesis que **no** puedo confirmar sin el codigo original:

1. **`SD` no es 8,77 en las unidades del estimando.** Si el estadistico fuera la
   media POR DIA en vez de por trade, la varianza relevante seria otra.
2. **`N_eff_real` no es `f x 200`.** Si a `f=1` tambien se aplicara un DEFF, o
   si el universo fueran mas dias que 200.
3. **`z` sin correccion.** Con `z=1,96` da 1,74 a f=1: mas cerca, pero tampoco
   1,14, y contradiria que el MDE este corregido por multiplicidad.

**No elijo ninguna.** Cualquiera de las tres se puede ajustar hasta dar 1,14, y
elegir la que cuadra es exactamente fabricar acuerdo con un numero cuya
derivacion no tengo. Es el mismo modo de falla que este expediente persigue.

## Por que importa, y no es academico

El MDE **no es un dato de color**: es el que decide si una hipotesis es
detectable. Si el verdadero fuera 2,41 en vez de 1,14 a f=1:

- la banda «detectable pero no operable» se ensancha mucho (el minimo operable
  a f=1 es 1,92, o sea que **2,41 quedaria por ENCIMA**: a f=1 no habria nada
  detectable que ademas sea operable);
- el margen de 1,60x a f=10 quedaria en ~0,8x, y **el barrido de resolucion no
  entraria**;
- el costo en MDE de ampliar la grilla se leeria distinto.

**No estoy afirmando que 1,14 este mal.** Estoy afirmando que **no es
reproducible desde lo documentado y persistido**, y que la diferencia con lo que
sale de esos insumos es un factor 2, no un redondeo.

Reproducible: `python diag/multiplicidad/reconstruir_mde.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import NormalDist

REPO = Path(__file__).resolve().parents[2]
N = NormalDist()
SD_TICKS = 8.77          # mediana de las 40 geometrias, por_geom_nulo.json
M_EFF = 21.2             # registrado en la ESPEC
POTENCIA = 0.80
PUBLICADO = {1: 1.14, 10: 0.39}
DIAS_RESEARCH = 200


def z(m, alpha=0.05):
    return N.inv_cdf(1 - (alpha / m) / 2)


def main():
    p = REPO / "diag" / "spike_in" / "neff.json"
    if not p.exists():
        print("falta %s" % p)
        return 2
    d = json.loads(p.read_text(encoding="utf-8"))
    deff, neff_p = d["deff_mediana"], d["n_eff_mediana"]
    apd, nd = d["anclas_por_dia"], d["n_dias"]

    ctrl = apd * nd / deff
    assert abs(ctrl - neff_p) < 1, "el artefacto no es internamente consistente"
    print("artefacto  DEFF=%.3f  N_eff_placebo=%.0f  anclas/dia=%.1f  dias=%d"
          % (deff, neff_p, apd, nd))
    print("control    anclas/DEFF = %.0f  == N_eff persistido  OK" % ctrl)

    k = z(M_EFF) + N.inv_cdf(POTENCIA)
    mde_p = k * SD_TICKS / neff_p ** 0.5
    print("\nz(%.1f)=%.4f  z_beta=%.4f  k=%.4f" % (M_EFF, z(M_EFF),
                                                   N.inv_cdf(POTENCIA), k))
    print("MDE_placebo = k*SD/sqrt(N_eff) = %.4f" % mde_p)

    print("\n%-4s %12s %12s %10s %8s" % ("f", "N_eff_real", "calculado",
                                         "publicado", "ratio"))
    peor = 0.0
    for f, pub in sorted(PUBLICADO.items()):
        nr = f * DIAS_RESEARCH
        calc = mde_p * (neff_p / nr) ** 0.5
        peor = max(peor, calc / pub)
        print("%-4d %12d %12.4f %10.2f %8.2f" % (f, nr, calc, pub, calc / pub))

    print("\nNO REPRODUCIBLE: el calculo da hasta %.2fx el valor publicado." % peor)
    print("La razon se mantiene entre f=1 y f=10, asi que el escalado con n es")
    print("correcto y lo que difiere es un FACTOR GLOBAL. Ver el docstring para")
    print("las tres hipotesis que podrian explicarlo, y por que no se elige una.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
