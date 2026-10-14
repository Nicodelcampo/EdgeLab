# Calibración del protocolo de descubrimiento sobre GC (2026-10-04)

Rejilla d1 (`config/discovery/spec_d1.json`, hash `78422948bd1d349a36cf25861c4944bd6df9b82d91a36f70aa86c025b260eb49`): 96 franjas × 4 holdings × 256 condiciones (ninguna, 39 simples, 216 pares) = **98.304 celdas**. Datos de GC previos al holdout, 225 sesiones. Esta calibración no barre ni informa resultados reales: usa los datos solo como estructura de ruido (signos sorteados) o con un efecto plantado conocido.

## Falsos positivos (señal inexistente)
Se sortea el signo de cada sesión de los datos reales y se cuenta con qué frecuencia el protocolo rechaza con α = 0,05.

| Corrida | Repeticiones | Sorteos del nulo | Rechazos | Tasa |
|---|---:|---:|---:|---:|
| Primera (en `calibracion_GC_d1.json`) | 30 | 500 | 4 | 13,3 % |
| Repetición | 300 | 500 | 16 | **5,3 %** |
| Repetición | 300 | 2.000 | 15 | **5,0 %** |

El 13 % de la primera corrida era ruido de una muestra de 30 (error estándar ≈ 4 puntos). Con 300 repeticiones la tasa coincide con el 5 % nominal: el nulo está calibrado.

## Potencia (efecto plantado)
Se suma a una celda al azar un efecto conocido por operación, en desvíos de esa celda, y se cuenta cuántas veces el protocolo lo detecta con `p_max ≤ 0,05` (15 repeticiones por tamaño; error de ± 10 puntos o más).

| Efecto por operación (en desvíos) | Detección |
|---:|---:|
| 0,1 | 0 % |
| 0,2 | 0 % |
| 0,3 | 13 % |
| 0,5 | 80 % |

**Lectura.** Con 225 sesiones y 98.304 celdas solo se detectan de forma fiable efectos de ~0,5 desvíos por operación o más. La celda de GC encontrada en la etapa A (1.152 celdas) tiene un efecto de unos **0,31 desvíos por operación** (21,3 ticks sobre un desvío de 67,6): en esta rejilla tendría ≈ 13 % de probabilidad de ser detectada. Una rejilla más grande no encuentra más: exige más evidencia. Los caminos para ganar potencia son agrupar activos con lógica común (fijado de antemano), más sesiones, o rejillas más pequeñas y mejor motivadas por familia.

## Infraestructura
- CPU: 4 núcleos, sin GPU. Paridad CPU por bloques frente a sin bloques (3 tamaños, hasta 100.000 celdas): diferencia máxima 0,0 (`artifacts/discovery/parity_cpu_only_20261004.json`, estado `CPU_ONLY_PASS_GPU_PENDING`: no cuenta como paridad GPU).
- GPU: pendiente de acceso a `api.kaggle.com`; el kernel (`tools/kaggle_discovery_gpu.py`) exige paridad PASS antes de usar su resultado.
