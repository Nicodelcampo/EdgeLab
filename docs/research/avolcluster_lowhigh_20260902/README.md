# aVolClusterPOI — FASE 3: el filtro Low/High no es la causa; hay un off-by-one

Fecha: 2026-09-02 · commit pineado `706c4fe2` · CSV NT8 sha256 `81f32a97…f9da`
Kernel: `notebooks/kaggle/avolcluster_lowhigh/lowhigh_entry.py` (Kaggle, 75 s)
Estado: `DIAGNOSTIC_NO_CODE_CHANGED` — no se tocó el `.cs` ni el kernel Python.

## Qué se probó

Sobre los 22.507 bloques NT8 ya alineados (FASE 2: offset 0 al 99,98 %, Δt mediano
0 ns), cinco construcciones del footprint contra las **mismas** barras:

| variante | bloques con celdas exactas | Σ\|diff\| | sólo NT8 |
|---|---:|---:|---:|
| A sin filtro (kernel actual) | 16 (0,07 %) | 271.675 | 1.098 |
| B filtro `Low[0]/High[0]` replicado | 16 | 271.675 | 1.098 |
| C filtro con rango del bloque | 16 | 271.675 | 1.098 |
| D tick → barra anterior | 3 | 321.327 | 2.047 |
| **E tick → barra siguiente** | **2.118 (9,4 %)** | **227.237** | **627** |

## Resultado 1 — el filtro Low/High queda REFUTADO

`ticks_discarded_by_bar_filter = 0`. El rango `[Low[0], High[0]]` de una barra,
derivado de los mismos ticks que la componen, contiene por construcción a todos
sus ticks. A, B y C son idénticos hasta el último decimal. **Bajo barras
alineadas ese filtro no puede explicar nada**, y era la hipótesis principal que
dejó abierta la FASE 2. Se cierra sin necesidad de más datos.

Alcance de la muerte: el filtro queda refutado *como causa de la divergencia de
celdas bajo la partición actual*. No se afirma nada sobre su efecto si la
partición de barras cambia.

## Resultado 2 — hay un off-by-one real, y tiene signo

Correr la asignación un tick **hacia adelante** multiplica por 132 los bloques
con celdas exactas y baja el residuo 16 %; hacia atrás lo empeora. El desvío
tiene dirección: la partición de Python empieza la barra **un tick antes** que
NT8, o equivalentemente NT8 arranca a contar en un tick posterior.

Pero E es un **re-etiquetado**, no una re-partición: mueve ticks de barra sin
conservar las 120 por barra, así que 9,4 % es un piso, no el techo. La versión
correcta es una **fase** en el conteo dentro de cada sesión — FASE 4.

## Por qué esto no contradice la FASE 2

La FASE 2 midió coincidencia de *timestamps de cierre*, y dio 0 ns de diferencia.
El 51 % de los ticks de NQ comparte timestamp con el anterior (es el mismo hecho
que rompe `HFTZonesNQImpulseV2_5`): una barra desfasada por pocos ticks **cierra
en el mismo nanosegundo**. Los timestamps no tenían resolución para ver esto.

## Dirección del volumen

`nt8_menos_volumen` 14.509 · `nt8_mas_volumen` 4.850 · `igual` 3.148. NT8 ve
*más* volumen que Python en 21,5 % de los bloques, así que ninguna hipótesis que
sólo *quite* ticks puede cerrar el caso completo. Un desfasaje sí explica las dos
direcciones a la vez.

## Cómo podría refutarse la FASE 4

Si ninguna fase `k` mejora a `k=0` de forma clara y monótona, el off-by-one de E
es un artefacto del re-etiquetado y la causa vuelve a estar abierta: quedaría
como principal sospechoso que NT8 y el parquet no ven el mismo conjunto de ticks
(fuente de datos, no kernel).

## Justificación económica

Sin paridad, todo barrido de parámetros sobre aVolClusterPOI mide un indicador
que no es el que corre en el chart, y ningún resultado sobre esa familia es
promovible. Es el bloqueo que hoy separa a la segunda familia viva de poder
entrar al embudo.
