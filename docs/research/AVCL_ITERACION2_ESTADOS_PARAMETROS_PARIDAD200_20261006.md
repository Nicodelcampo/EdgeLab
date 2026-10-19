# Iteración 2 — correcciones a la propuesta de estados, huecos de medición de AVCL, parámetros del indicador y paridad a 200t — 2026-10-06

Soporte/resistencia: **fuera de alcance** por decisión de Nico.

## 1. Errores en la propuesta de estados (`ESTADOS_MERCADO_LITERATURA_Y_DISENO_20261006.md`) y su corrección
| # | error | por qué importa | corrección |
|---|---|---|---|
| E1 | Los umbrales en **terciles móviles** hacen los estados equiprobables por construcción. | Cualquier serie, incluso ruido, da 1/3 de cada estado: el mapa no informa nada. | Umbral de eficiencia contra un **nulo de random walk**: VR(q) y E_N simulados con los incrementos permutados dentro de la sesión. Terciles sólo para amplitud, declarados como convención. |
| E2 | La duración de los estados se iba a reportar como si fuera evidencia. | Con ventanas superpuestas de N barras, el estado dura unas N barras **mecánicamente**. | Comparar duraciones y matriz de transición contra el **mismo detector corrido sobre la serie permutada** (bloques de sesión). Sólo cuenta el exceso sobre ese nulo. |
| E3 | La suma de \|Δclose\| sobre barras de 50t incluye el **rebote bid/ask** y la discreción de 1 tick. | E_N queda sesgado hacia abajo a N chico: "agitación" falsa. | Piso de ruido (descontar 1 tick por cada cambio de signo) o VR con corrección tipo Roll. Reportar E_10 con y sin corrección. |
| E4 | La amplitud se normalizaba "a la misma hora en 20 sesiones" **por barra**. | En barras de ticks, la cantidad de barras por hora varía mucho (RTH contra ETH). | Normalizar **por tiempo** (ticks de rango por minuto) y además por barra. Fijar cuál es la primaria antes de mirar. |
| E5 | Las ventanas podían cruzar sesión, pausa CME o roll. | Saltos de apertura que se leen como "desplazamiento". | Cortar ventanas en el límite de sesión y usar sólo el contrato líder, como el runner AVCL. |
| E6 | No estaba definido cómo combinar las 3 escalas (10/50/200). | Tres estados que pueden contradecirse. | Reportar las tres por separado. Si hace falta una sola etiqueta, jerarquía fija decidida ahora: 200 = "régimen", 10 = "fase". |
| E7 | La "validación" se quedaba en la estabilidad. | Un estado estable que no anticipa nada no sirve como contexto. | Agregar **previsibilidad target-free**: ¿el estado en t anticipa la amplitud y la eficiencia en t+h mejor que el nulo? Mira el precio futuro, pero no es P&L ni dirección. |
| E8 | No había nada sobre la **compresión** posterior a la zona. | VOL-1/2 la vieron (`y_rv` < 0 a H50/200), pero nunca se testeó, porque la prueba era unilateral. | Incluirla como pregunta explícita (§2, H-c), y en el cruce estado × zona. |

## 2. Qué falta medir en AVCL (para que no quede nada afuera)
Ya medido: expansión a 10/50/200 (VOL-1); contra el volumen (VOL-2 A); curva (VOL-2 B); dirección y toque inmediato
(SR-DIR).

| id | medición faltante | tipo | costo con cache |
|---|---|---|---|
| H-a | **Dosis-respuesta**: ¿más anomalía (score/threshold, `anomaly_ratio`, `cluster_share`, densidad, ancho) da más expansión? Es la prueba mecanística más fuerte de que el efecto es de la zona. | información | minutos |
| H-b | **Estabilidad temporal**: efecto por contrato/trimestre y por franja (apertura, mediodía, cierre). | robustez | minutos |
| H-c | **Compresión posterior**, bilateral y pre-registrada (H50/H200). | información | minutos |
| H-d | **ETH formal** (hasta ahora sólo descriptivo). | información | minutos |
| H-e | **Agrupamiento de eventos**: zonas en ráfaga (`burst_count`) contra aisladas; dependencia entre eventos cercanos (¿alcanza el SE por sesión?). | robustez / inferencia | minutos |
| H-f | **AT contra OFF**: por qué difieren (en AT el precio está dentro del cluster). | información | minutos |
| H-g | **Sensibilidad a parámetros** (§3): ¿el efecto existe en toda la grilla o sólo en p95/W10? | robustez | recalcula el indicador: unos 30 min por tanda de 4 celdas |
| H-h | **Bar spec**: 200t contra 50t (requiere paridad a 200t, §4). | robustez | recalcula |
| H-i | **Otros instrumentos**: MES/ES, NQ, YM, RTY. Exploratorio, sin paridad propia. | replicación | recalcula |
| H-j | **Delta de la zona**: el cache no guarda bid/ask. Hay que extender la etapa 1 con footprint bid/ask. | información | recalcula una vez |
| H-k | **Estado previo** (detector de §1) como contexto: ¿una zona en consolidación expande más que en agitación? | contexto pre-registrado | minutos, cuando exista el detector |
| H-l | **Magnitud contra costo**: exceso de rango en ticks por estado y por intensidad, comparado con el costo de ida y vuelta (unos 5,8 ticks en MNQ). | economía (no P&L) | minutos |

Orden propuesto:
1. H-a, H-b, H-c, H-d, H-e, H-f, H-l: un solo kernel sobre el cache, con un manifiesto.
2. H-j y H-g/H-h: recalculan el indicador.
3. H-k cuando exista el detector.

## 3. Parámetros de aVolClusterPOI (v0.5, 39 en NT8)
**Detección** (cambian **qué zonas nacen**):
| NT8 | Python | qué hace | usado | defecto |
|---|---|---|---|---|
| Window Bars (bloque) | `window_bars` | Barras por bloque, sin superposición. Al cerrar cada bloque se busca un cluster en su footprint acumulado. | 10 | 10 |
| Median Multiplier | `median_multiplier` | Una celda (precio) es "caliente" si su volumen > k × mediana de las celdas del bloque. | 2,0 | 2,0 |
| Selección robusta (top-K) / Hot Fraction | `use_topk_hot_cells` / `hot_fraction` | Alternativa: las celdas calientes son el top 17 % del bloque. | off | off / 0,17 |
| Max Gap Ticks | `max_gap_ticks` | Huecos tolerados dentro de un cluster. | 1 | 1 |
| Min Cluster Ticks | `min_cluster_ticks` | Ancho mínimo del cluster. | 2 | 2 |
| Session Relative Buckets / Time Bucket | `use_session_buckets` / `time_bucket_minutes` | Umbral separado por franja horaria (relativa a la sesión). | sí / 30 | sí / 30 |
| Lookback Sessions | `lookback_sessions` | Sesiones de historia para el umbral. | 20 | 20 |
| **Detection Percentile** | `detection_percentile` | Score del cluster ≥ percentil p de los scores históricos de su franja. | **95** | **98** |
| Min Samples Per Bucket | `min_samples_per_bucket` | Historia mínima para emitir umbral (calentamiento). | 20 | 20 |

**Filtro y ranking** (descartan o puntúan zonas ya detectadas):
- `enable_predictive_filter` (off).
- `min_quality_score` (0).
- `max_distance_from_zone_ticks` (80; sólo actúa con el filtro).
- `rejection_full_score_ticks` (12).
- `burst_min_zones` / `burst_window_bars` / `burst_range_ticks` (3/200/40), que entran en el puntaje de calidad.

**Ciclo de vida** (no cambian la creación; cambian vida, toques e invalidación):
- `invalidation_mode` (usado None; defecto CloseThrough).
- `max_age_bars` (500).
- `max_touches` (0).

**Sólo etiquetas** (no afectan zonas): `reaction_horizon_bars` / `target` / `stop` (50/12/8). Son el resultado
TARGET/STOP que dibuja el indicador. **No usarlos como evidencia.**

**Visuales:** opacidad, colores, dashboard, etc. Ojo con **Remove Invalidated Zones**: si está activo, el chart oculta
las zonas invalidadas, y por la regla de supervivencia del render, lo que se ve en pantalla deja de ser evidencia
admisible. Hay que recordarlo cuando se retome soporte/resistencia.

**Eje distinto (regla `ticks_per_row` / `bar_spec`):** el tamaño de barra (50t, 200t) **no es un parámetro del
indicador**. Cambia el bloque efectivo: W=10 barras de 50t son 500 trades; de 200t, 2.000.

### Grilla de sensibilidad propuesta (H-g)
Target-free respecto del P&L. Se publica el landscape completo y **no se elige celda**.
- Ejes: `detection_percentile` {90, 95, 98} × `window_bars` {5, 10, 20} × `median_multiplier` {1,5, 2, 3} ×
  `min_cluster_ticks` {2, 4} × bar_spec {50t, 200t}. Son 108 celdas: demasiadas para recalcular el indicador en todas.
- Diseño fraccional:
  - ejes de a uno alrededor del punto base (p95/W10/k2/m2/50t): 9 celdas;
  - más las 4 esquinas percentil × ventana: **13 celdas**.
- Cada celda corre el kernel de la etapa 1, en paralelo.
- La pregunta de robustez es **"¿el signo y el orden de magnitud de AT·y_rg A2 se mantienen?"**, no "¿cuál celda es
  mejor?". El landscape es descriptivo; la única prueba formal sigue siendo la del punto base.

## 4. Paridad a 200t (propuesta de Nico)
Por qué: si el efecto se replica en 200t, es más barato operarlo (menos ruido de microestructura) y descarta que sea un
artefacto de 50t. La paridad a 50t no se transporta.

Pasos (Nico en NT8):
1. Chart **MNQ 12-26, 200 Tick**, Merge policy **Do not merge**, tz ART. Cargar desde **2026-07-15** hasta la última
   sesión **anterior al 2026-10-01**.
2. aVolClusterPOI con los **mismos** parámetros que en 50t: percentil 95, invalidación None, MaxAge 500, resto por defecto.
3. Activar los tres exports:
   - Event Log Path: `E:\EdgeLab\data\nt8_oracles\avolcluster_v05_MNQ1226_200t_20260715_20260930.csv`
   - Diag Block Export: enabled, path `..._200t_DIAG.csv`
   - Bar Profile Log Path: `..._200t_BARPROFILE.csv`
4. Avisar cuando estén los tres archivos.

Lado Python:
`tools/paridad_oraculo.py --indicador avolclusterpoi --barras tick:200 --excluir-pausa-cme --footprint-nt8-subserie
--chart-tz America/Argentina/Buenos_Aires --param max_age_bars=500 --param detection_percentile=95.0` más la ventana
del oráculo (`--desde-ns` = 2026-07-14 19:00 ART, `--hasta-ns` = último cierre + 1 ms).

Criterio: igual que en 50t (creación al ms, geometría 0 ticks, estado y fin). Causa raíz de toda diferencia, sin
ampliar tolerancias. Con PASS se habilitan H-h y las celdas de 200t de la grilla.
