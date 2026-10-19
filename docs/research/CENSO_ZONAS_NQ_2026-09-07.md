# Censo target-free de zonas HFT sobre NQ — primera medición

> **Target-free.** Geometría y ciclo de vida. No mira retornos, no hay P&L, no hay
> dirección esperada. No requiere el STOP del proyecto.
> Reproducción: `tools/censo_zonas_nq.py`. Salida: `data/nt8_oracles/censo_zonas_nq.json`.
> Motor: `edgelab/bridge/indicators/hftzones_nq.py` (13 tests).
> **Alcance: 3 sesiones de `NQ 06-26`, mayo 2026.** No se generaliza a otros contratos
> ni a otros meses. Holdout (desde 2026-07-01) no tocado; el script lo rechaza por
> construcción.

---

## 1. Qué se corrió

| Sesión | ticks | candidatos | zonas (defaults) | segundos |
| :-- | --: | --: | --: | --: |
| 2026-05-12 | 499.739 | 97.160 | 480 | 1,2 |
| 2026-05-13 | 529.605 | 100.076 | 741 | 1,4 |
| 2026-05-14 | 659.522 | 130.779 | 608 | 1,7 |

Una pasada por tick produce el censo completo de **candidatos**; los diez umbrales de
aceptación se aplican después por aritmética. Los barridos de abajo salieron de esas
tres pasadas, no de re-correr nada.

## 2. Las zonas reales son mucho más grandes que sus umbrales

| | mediana |
| :-- | --: |
| altura | **12–18 ticks** (umbral: 4) |
| pasos válidos | **49** (umbral: 8) |
| volumen total | **64–66** (umbral: 50) |
| ms promedio entre ticks | **1,7–2,6 ms** |

Los parámetros que dan nombre al indicador —`min_pasos`, `min_sweep_ticks`— están muy
por debajo de la distribución que efectivamente sale, así que **no filtran nada**.

## 3. Un solo parámetro gobierna la población

Zonas por sesión, barriendo un umbral a la vez desde los defaults:

| `min_total_volume` | 05-12 | 05-13 | 05-14 |
| --: | --: | --: | --: |
| 0 | 10.401 | 11.793 | 13.663 |
| 25 | 1.798 | 2.212 | 2.229 |
| **50 (default)** | **480** | **741** | **608** |
| 100 | 79 | 142 | 100 |
| 200 | 6 | 12 | 5 |

Contra eso, los demás apenas se mueven:

| parámetro | recorrido barrido | efecto sobre el conteo |
| :-- | :-- | :-- |
| `min_sweep_ticks` | 1 → 16 | **3 zonas** (478 → 481) |
| `min_pasos` | 4 → 40 | −20 % recién en el extremo |
| `min_volume_rate` | 0 → 100 | **ninguno**; muerde recién en 200 |
| `max_avg_ms` | 25 → 5 | −23 % |
| `detect_absorb` | on → off | −11 % |

**`min_total_volume` mueve la población tres órdenes de magnitud; el resto la mueve un
dígito.** Dicho de otro modo: *cuántas zonas HFT existen en NQ* no es un hecho medido,
es una elección de un umbral de volumen.

Coherente con eso, la causa de muerte dominante entre los ~100.000 candidatos por
sesión es `pasos` (~85 %), y la segunda es `volumen_total` (~10 %). Las compuertas
temporales matan menos del 1 %.

## 4. Por qué esto importa para definir un cluster

Es el punto que cambia el orden del trabajo.

Un cluster se define por **densidad de zonas** en un rango de precio. La densidad es
función directa de cuántas zonas hay. Y el punto 3 muestra que cuántas zonas hay lo
decide `min_total_volume`. Entonces:

**El umbral de aceptación de la zona y el umbral de densidad del cluster no son
parámetros independientes.** Con `min_total_volume = 0` hay ~20× más zonas y cualquier
umbral de densidad razonable convierte el gráfico entero en un cluster; con `200` no
hay material para formar ninguno.

Consecuencia práctica para el embudo: **el barrido tiene que ser conjunto**, sobre el
par (umbral de zona, umbral de densidad), no anidado. Barrer la densidad con la zona
fija reportaría una sensibilidad que es un artefacto de haber congelado el otro eje.

Y una advertencia sobre multiplicidad, para tenerla escrita antes y no después: un
barrido conjunto de dos ejes con seis valores cada uno son 36 configuraciones **por cada
definición de cluster que se pruebe**. Eso hay que declararlo como presupuesto de
hipótesis antes de mirar nada que se parezca a un retorno.

## 5. Composición por bucket

| | 05-12 | 05-13 | 05-14 |
| :-- | --: | --: | --: |
| Predator (≤5 ms) | 328 | 519 | 424 |
| Ultra (≤15 ms) | 100 | 142 | 131 |
| Absorb | 52 | 79 | 50 |
| Fast | 0 | 1 | 3 |

La población es abrumadoramente **Predator**: la mediana de `avg_ms` es 1,7–2,6 ms, muy
por debajo del corte de 5 ms. La clasificación por velocidad, tal como está calibrada,
casi no discrimina — separa 2 ms de 2 ms.

## 6. Lo que este censo NO dice

- Nada sobre si los clusters atraen al precio. No se midió ninguna relación con el
  precio posterior.
- Nada sobre otros contratos, otros meses, u otros instrumentos.
- Nada sobre si los defaults del `.cs` son buenos. Sólo muestra cuáles muerden.
- La ventana de sesión usa el offset fijo CDT de mayo-junio 2026, declarado en el
  script. Un calendario DST-aware es trabajo aparte.

---

**Aporte al referente:** primera medición real del objeto sobre el que se quiere buscar
un edge. Muestra que el tamaño de la población de zonas es esencialmente un parámetro
libre, y que por lo tanto la definición de cluster no puede calibrarse con la de zona
congelada — lo que evita un barrido cuyo resultado habría sido un artefacto del eje que
se dejó fijo.
