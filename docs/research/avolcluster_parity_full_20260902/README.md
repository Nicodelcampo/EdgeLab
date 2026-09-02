# Paridad aVolClusterPOI NQ 06-26 — cruce COMPLETO celda por celda (2026-09-02)

**`DIAGNOSTIC_NO_CODE_CHANGED`.** Kernel `avolcluster-parity-full-20260902`,
code_commit `e2199bb`. No se modificó el `.cs` ni el kernel Python.
`outcomes_accessed=false`, `holdout_accessed=false`.

Extiende a **22.200 bloques emparejados** el cruce que
`AVOLCLUSTERPOI_NT8_DIAG_CONFIRMED_2026-09-01.md` había hecho sobre **3 casos**.

## Resultado que corrige la conclusión previa

| | |
|---|---|
| bloques NT8 / Python | 22.507 / 22.934 |
| emparejados | **22.200** (307 NT8 sin par) |
| **bloques con celdas idénticas** | **16** |
| bloques con ticks ausentes en NT8 | 3.387 (15 %) |
| bloques con ticks ausentes en Python | 800 |
| **bloques con sólo ruido de valor** | **18.164 (82 %)** |

Discrepancias efectivas y su causa:

| | total | con ticks ausentes en NT8 | **sólo ruido de valor** | sin diferencia de celdas |
|---|---|---|---|---|
| decisión distinta | 590 | 137 (23 %) | **453 (77 %)** | **0** |
| geometría distinta | 30 | 10 (33 %) | **20 (67 %)** | **0** |

## Las dos conclusiones

**1. No hay causa desconocida.** `sin_diferencia_de_celdas = 0` en ambos tipos de
mismatch: **toda** discrepancia tiene una diferencia de celdas detrás. El algoritmo de
clustering está bien traducido — eso ya se había verificado línea por línea, y ahora se
confirma por exclusión sobre la población completa.

**2. El mecanismo dominante NO es el filtro `Low[0]/High[0]`.** La muestra de 3 casos
sugería que la pérdida de ticks de borde era la causa principal. Sobre los 22.200 bloques
resulta lo contrario: la pérdida de ticks explica sólo el **23 %** de los mismatches de
decisión y el **33 %** de los de geometría. El resto — **más de las tres cuartas partes** —
es **ruido de valor en el volumen por celda**, sin ningún tick ausente.

Y el dato que lo enmarca: **sólo 16 bloques de 22.200 tienen celdas idénticas**. El ruido
de valor no es un caso raro; es la condición normal, presente en el 82 % de los bloques
incluso cuando no cambia ninguna decisión. En los 40 peores casos, la mediana de ticks
compartidos con volumen distinto es **14**, con máximo de 52.

## Consecuencia para el fix

Corregir el `.cs` para reasignar el tick de borde en vez de descartarlo **es correcto pero
insuficiente**: resolvería en torno a un cuarto de las discrepancias de decisión. La causa
dominante está en **cómo se reconstruye el volumen por celda**, no en qué ticks se pierden
en el borde.

Hipótesis a verificar (**no confirmada acá**): el `.cs` acumula sobre una *subserie de 1
tick* de NT8 (`Closes[1][0]`, `Volumes[1][0]`), que no es un tick individual sino una barra
de un tick — puede agregar varios trades simultáneos en una sola entrada, asignando el
volumen total al precio del último. El footprint de Python suma cada tick por separado. Eso
produciría diferencias chicas, sistemáticas y presentes en casi todos los bloques, que es
exactamente el patrón observado. **Verificarlo requiere comparar la subserie de 1 tick de
NT8 contra los ticks crudos, no se hizo.**

## Magnitud, para dimensionar

Sobre los 22.200 bloques emparejados: **2,7 %** cambia de decisión y, entre los 412 bloques
donde ambos crean zona, **7,3 %** difiere en geometría. Es la escala del problema, no una
tolerancia aprobada — el gate sigue en `FAIL` y nadie lo reclasificó.

## Lo que sigue sin decidirse

- Si se toca el `.cs` (cambia el indicador en producción y las zonas dibujadas).
- Qué tolerancia, si alguna, es aceptable.
- Si conviene perseguir paridad exacta o declarar una banda y seguir. El precedente
  `BIGTRAP2_PARIDAD_IMPOSIBLE_2026-08-21.md` existe para el caso en que no se alcance.
