# aVolClusterPOI — FASE 4: la fase de partición es real pero chica (9 %)

Fecha: 2026-09-02 · commit pineado `706c4fe2` · CSV NT8 sha256 `81f32a97…f9da`
Kernel: `notebooks/kaggle/avolcluster_phase/phase_entry.py` (Kaggle)
Estado: `DIAGNOSTIC_NO_CODE_CHANGED`.

## Qué se probó

Barrido de la fase `k` del contador de ticks por barra, aplicada **dentro de cada
sesión** (`bucket = (rank_en_sesión − k) // 120`, respetando el reinicio por
sesión de TICKBAR-001). `k=0` es el kernel actual.

| k | bloques exactos | % | Σ\|diff\| |
|---:|---:|---:|---:|
| −3 | 101 | 0,50 % | 229.071 |
| −2 | 313 | 1,50 % | 218.832 |
| **−1** | **1.958** | **9,01 %** | 224.319 |
| 0 | 16 | 0,07 % | 271.675 |
| +1 | 3 | 0,01 % | 313.654 |

(`matched` cae con `|k|` porque el emparejamiento por timestamp se hace contra
barras desplazadas; es un artefacto del matcher, no del resultado.)

## Resultado — hay una fase, y es −1

El pico en `k=−1` es nítido: multiplica por 127 los bloques exactos y es seis
veces mayor que su vecino inmediato. **NT8 empieza a contar la barra un tick
después que el kernel Python**, dentro de cada sesión. Es un hallazgo real y
corregible en el kernel, sin tocar el `.cs`.

## Pero no es la causa principal

9,01 % es prácticamente idéntico al 9,4 % que ya daba el re-etiquetado de la
FASE 3, que era una aproximación grosera. **El off-by-one explica ~9 % de los
bloques y deja el 91 % sin explicar.** Ajustar la fase mejora la paridad, no la
alcanza. Nótese además que `k=−1` no minimiza el residuo total (lo hace `k=−2`):
la fase corrige *qué* bloques quedan exactos, no la masa del error.

## Qué queda vivo

Una sola familia grande: **NT8 y el parquet no ven el mismo conjunto de ticks.**
Es la única compatible con el hecho, ya medido en la FASE 3, de que NT8 tiene
*más* volumen que Python en 21,5 % de los bloques — ninguna hipótesis que sólo
reparta o filtre ticks puede producir exceso.

FASE 5 la decide con un test que cancela por construcción cualquier diferencia
de partición: conservación de volumen a nivel **sesión**.

## Cómo podría refutarse este resultado

Si la FASE 5 muestra totales de sesión idénticos, entonces los ticks sí son los
mismos y el 91 % restante es partición — y este barrido de fase habría explorado
el eje correcto con la parametrización equivocada (por ejemplo, fase que se
reinicia en un evento distinto del primer tick de sesión).

## Justificación económica

Igual que FASE 3: sin paridad no hay barrido de parámetros interpretable sobre
aVolClusterPOI, y la segunda familia viva del proyecto no puede entrar al embudo.
