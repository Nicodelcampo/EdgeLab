# -*- coding: utf-8 -*-
"""Reconstruccion del MDE de EXPLORE-001 -- REPRODUCE. Y la version anterior no.

## Correccion de un resultado que publique mal

La version anterior de este archivo concluia **NO REPRODUCIBLE**: decia que el
MDE de 1,14 ticks a f=1 daba 2,41 con los insumos documentados, un factor 2,11
sin explicar, y listaba tres hipotesis sin elegir ninguna.

**El numero publicado esta bien. El que estaba mal era este script.**

### Que hice mal, exactamente

Calcule el error estandar como `SD / sqrt(N_eff)` con `SD = 8,77 ticks/trade`,
la mediana de las 40 geometrias. Pero el MDE no usa esa SD: usa un **`SE`
medido por bootstrap**, que el propio expediente publica.

    SD/sqrt(N_eff) = 8,77 / sqrt(9.707) = 0,0890 ticks/ancla   <- lo que use
    SE medida por bootstrap             = 0,0420 ticks/ancla   <- lo correcto

    0,0890 / 0,0420 = 2,12

**Ese cociente ES el factor 2,11 que reporte como inexplicado.** No era un
misterio: era mi insumo.

Y no son la misma cantidad. `SD = 8,77` es dispersion **por trade** entre
geometrias; `SE = 0,0420` es el error estandar **por ancla** del estimando, con
la dependencia entre dias ya adentro. Dividir la primera por `sqrt(n)` supone
independencia y supone que el estimando es la media de esa variable. Ninguna de
las dos cosas es cierta acá.

### Como lo encontre, que es la parte que importa

La version anterior afirmaba: «**Ningun script del repo lo calcula**», y lo
verificaba con `grep` de `norm.ppf`, `z_beta`, `potencia` y `0.8416` sobre todo
`diag/`.

Eso era **cierto y completamente irrelevante**. La derivacion no esta en un
script: esta en `docs/spike_in/MDE_EXPLORE-001.md` -- un documento de 25 KB
**cuyo nombre es exactamente el numero que yo estaba tratando de reconstruir**.
Nunca busque en `docs/`.

Busque donde esperaba que estuviera la respuesta, no la encontre, y **publique
la ausencia como hallazgo**. Es el mismo modo de falla que este expediente
persigue en los demas, con la carga invertida.

Aparecio recien cuando `tools/reportes.py` listo los 103 documentos de `docs/`
por carpeta. No lo encontre razonando: lo encontre porque un indice lo puso
adelante.

## La reconstruccion, ahora

Insumos, todos de `docs/spike_in/MDE_EXPLORE-001.md`:

    SE placebo medida (bootstrap de bloques de dia) = 0,0420 ticks/ancla
    N_eff placebo                                   = 9.707
    M_eff (Li-Ji sobre autovalores)                 = 21,2
    potencia 80%, alfa 0,05 bilateral

    MDE(f) = [z(alfa/M_eff) + z_beta] . SE . sqrt(N_eff_placebo / N_eff(f))

Los cuatro renglones publicados reproducen a la precision con que estan escritos.

## Lo que SIGUE abierto, y no lo cierra esto

`N_eff(f)` esta tabulado -197, 574, 1.733, 4.102- y **no reconstruido**: sale de
un bootstrap que este script no vuelve a correr. Que el MDE reproduzca dado ese
insumo no valida el insumo.

Y el `197` de `f=1` son los **dias de research de entonces**. El universo hoy
tiene **201 sesiones**, asi que el MDE a f=1 se mueve por `sqrt(197/201)`: menos
de 1%, pero el numero publicado es de un universo que ya no es el vigente.

Reproducible: `python diag/multiplicidad/reconstruir_mde.py`
"""
from __future__ import annotations

import sys
from pathlib import Path
from statistics import NormalDist

REPO = Path(__file__).resolve().parents[2]
N = NormalDist()

FUENTE = "docs/spike_in/MDE_EXPLORE-001.md"
SE_PLACEBO = 0.0420      # ticks/ancla, MEDIDA por bootstrap -- no SD/sqrt(n)
N_EFF_PLACEBO = 9707
M_EFF = 21.2
POTENCIA = 0.80
ALFA = 0.05

#: `f` -> (N_eff tabulado, MDE publicado). El `N_eff` NO se reconstruye: sale de
#: un bootstrap que este script no vuelve a correr.
PUBLICADO = {1: (197, 1.14), 3: (574, 0.67), 10: (1733, 0.39), 30: (4102, 0.25)}

#: El error de la version anterior, para que la correccion sea verificable y no
#: haya que creerme.
SD_POR_TRADE_QUE_USE_MAL = 8.77
DIAS_UNIVERSO_HOY = 201


def z(m, alpha=ALFA):
    return N.inv_cdf(1 - (alpha / m) / 2)


def main():
    doc = REPO / FUENTE
    if not doc.exists():
        print("falta %s -- es la fuente de los insumos" % FUENTE)
        return 2

    k = z(M_EFF) + N.inv_cdf(POTENCIA)
    mde_p = k * SE_PLACEBO
    print("fuente     %s" % FUENTE)
    print("insumos    SE=%.4f t/ancla (MEDIDA)  N_eff_placebo=%d  M_eff=%.1f"
          % (SE_PLACEBO, N_EFF_PLACEBO, M_EFF))
    print("           z(%.1f)=%.4f  z_beta=%.4f  k=%.4f"
          % (M_EFF, z(M_EFF), N.inv_cdf(POTENCIA), k))
    print("           MDE_placebo = k*SE = %.5f" % mde_p)

    print("\n%-4s %9s %10s %11s %10s %8s" % ("f", "N_eff", "deflacion",
                                             "calculado", "publicado", "dif"))
    peor = 0.0
    for f, (neff, pub) in sorted(PUBLICADO.items()):
        defl = (N_EFF_PLACEBO / neff) ** 0.5
        calc = mde_p * defl
        peor = max(peor, abs(calc - pub))
        print("%-4d %9d %10.3f %11.4f %10.2f %8.4f"
              % (f, neff, defl, calc, pub, calc - pub))

    ok = peor <= 0.005
    print("\n%s: la diferencia maxima es %.4f ticks -- dentro del redondeo con "
          "que estan\npublicados (2 decimales)." % ("REPRODUCE" if ok else "NO CIERRA", peor))

    # Contraste explicito con el error anterior: que sea verificable, no creible.
    se_mal = SD_POR_TRADE_QUE_USE_MAL / N_EFF_PLACEBO ** 0.5
    print("\ncontrol del error anterior")
    print("  SD/sqrt(N_eff) = %.4f/sqrt(%d) = %.4f t/ancla   <- lo que usaba"
          % (SD_POR_TRADE_QUE_USE_MAL, N_EFF_PLACEBO, se_mal))
    print("  SE medida                      = %.4f t/ancla   <- lo correcto"
          % SE_PLACEBO)
    print("  cociente = %.2f  == el factor '2,11 inexplicado' que reporte"
          % (se_mal / SE_PLACEBO))

    print("\nsigue abierto")
    print("  - N_eff(f) esta TABULADO, no reconstruido: sale de un bootstrap que")
    print("    este script no vuelve a correr. Reproducir dado el insumo no")
    print("    valida el insumo.")
    print("  - el 197 de f=1 son los dias de research de entonces; el universo")
    print("    hoy tiene %d. El MDE se mueve por sqrt(197/%d) = %.4f (%.1f%%)."
          % (DIAS_UNIVERSO_HOY, DIAS_UNIVERSO_HOY,
             (197 / DIAS_UNIVERSO_HOY) ** 0.5,
             100 * (1 - (197 / DIAS_UNIVERSO_HOY) ** 0.5)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
