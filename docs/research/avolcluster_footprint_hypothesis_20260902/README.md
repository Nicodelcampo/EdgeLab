# Hipótesis de consolidación de trades simultáneos — REFUTADA (2026-09-02)

**`DIAGNOSTIC_NO_CODE_CHANGED`.** Kernel `avolcluster-footprint-hypo-20260902`,
code_commit `2f14636`. No se modificó el `.cs` ni el kernel Python.
`outcomes_accessed=false`, `holdout_accessed=false`.

## La hipótesis

El cruce completo (`avolcluster_parity_full_20260902/`) mostró que más del 75 % del desvío
de paridad es **ruido de valor por celda**, no pérdida de ticks. Se propuso que la causa
fuera la *subserie de 1 tick* de NT8: si NT8 consolida trades con el mismo timestamp en una
sola barra y asigna el volumen sumado a un único precio, mientras Python asigna el volumen
de cada tick a su propio precio, aparecería exactamente ese patrón.

## Resultado: refutada

Se construyeron tres footprints sobre los **mismos** ticks y bloques, y se compararon contra
las celdas reales de NT8:

| variante | bloques idénticos | `sum_abs_diff` | celdas con valor distinto |
|---|---|---|---|
| **A — Python actual** (cada tick a su precio) | **2** | **276.756** | **46.730** |
| B — consolidado al precio del último | 0 | 1.715.442 | 260.590 |
| C — consolidado al precio del primero | 0 | 1.754.264 | 259.979 |

Las dos variantes de consolidación son **6× peores** en diferencia absoluta y **5,6× peores**
en número de celdas divergentes. La regla propuesta no acerca el footprint a NT8: lo aleja.

**No falló por falta de material.** El 51,1 % de los ticks comparte timestamp con el
anterior (14.070.725 de 27.543.603), y hay **3.024.940 grupos multi-tick en los que el
precio efectivamente varía** — o sea, la regla tenía millones de oportunidades de mejorar
algo y empeoró en todas. La hipótesis queda descartada, no "sin evidencia suficiente".

## Defecto del propio test, declarado

Este kernel **no reprodujo el particionado en bloques del indicador**. El indicador real
arma bloques *por sesión* (`bar_indices` de cada sesión, luego grupos de 10 barras); acá se
tomaron grupos de 10 barras corridos desde el índice 0, ignorando los límites de sesión. Por
eso sólo emparejaron **3.948** bloques contra los **22.200** del cruce completo: el resto
quedó desalineado.

Qué invalida y qué no:

- **No invalida la refutación.** Las tres variantes se evaluaron sobre exactamente los
  mismos bloques, así que la comparación relativa A vs B vs C es limpia.
- **Sí invalida los valores absolutos.** El `blocks_identical = 2` de este test **no** es
  comparable con el `16 de 22.200` del cruce completo, que sigue siendo la cifra buena.

## Un dato que sobrevive y apunta a otra parte

En la variante A, sobre los bloques emparejados: **13.316 celdas que Python tiene y NT8 no**,
pero también **9.479 celdas que NT8 tiene y Python no**.

Ese segundo número importa: el filtro `Low[0]/High[0]` sólo puede *quitar* celdas del lado
NT8, nunca agregarlas. Que NT8 tenga miles de celdas ausentes en Python **no se explica con
el mecanismo conocido**, y no estaba aislado hasta ahora.

## Estado

La causa dominante del ruido de valor **sigue sin identificar**. Descartado: consolidación
de trades simultáneos. El gate de paridad sigue en `FAIL`, sin reclasificar, y no se tocó
código de producción.

Próximo paso natural, más barato que este: repetir el cruce respetando el particionado por
sesión y separar las celdas que sólo NT8 tiene, que es la pista que este test dejó servida.
