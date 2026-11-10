# Propuesta Iterada y Paquete de Auditoría: `U1-HFT-CLUSTERS-GRILLA` y `U1-HFT-CRUZADO`

- **Fecha:** 2026-11-10
- **Estado:** Pre-registro iterado listo para auditoría adversarial (`abogado_del_diablo` / `revisor` / `juez`)
- **Instrumento primario:** `NQ` (extensible a `ES`, `YM`, `GC` vía `almacen_clusters_hft_grilla`)
- **Código de soporte:**
  - Indicador NT8 Causal: [`nt8/user_indicators/HFTZonesNQRangosPctV2.cs`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/nt8/user_indicators/HFTZonesNQRangosPctV2.cs)
  - Espejo Python + Numba: [`edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py)
  - Suite de paridad y causalidad: [`tests/bridge/test_hftzones_nq_rangos_pct_v2.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/tests/bridge/test_hftzones_nq_rangos_pct_v2.py)
  - Antecedentes directos: [`edgelab/research/u1_racimos_grilla.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/u1_racimos_grilla.py), [`edgelab/research/u1_cruzado.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/u1_cruzado.py), [`edgelab/research/u1_indaga.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/u1_indaga.py), [`docs/research/GUIA_GRILLA_MASIVA.md`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/GUIA_GRILLA_MASIVA.md)

---

## 1. Diagnóstico Crítico de la Iteración: ¿Qué falló en `U1-RACIMOS-GRILLA` y qué corrige esta versión?

Antes de proponer una nueva grilla, diagnosticamos tres cuellos de botella estructurales detectados al cruzar [`edgelab/research/u1_racimos_grilla.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/u1_racimos_grilla.py), [`docs/research/relanzamiento_R_20261102/embudo/U1-RACIMOS-GRILLA-NQ-R/MEDIDO.md`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/relanzamiento_R_20261102/embudo/U1-RACIMOS-GRILLA-NQ-R/MEDIDO.md) y el comportamiento real en gráfico de `HFTZonesNQRangosPctV2`:

### 1.1. El problema del «Doble Racimo» (`_racimo` $\to$ `AX.eventos(ns=(3, 5))`)
En [`edgelab/research/u1_racimos_grilla.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/u1_racimos_grilla.py#L94-L140):
1. Primero `_racimo(df, n_min=3..5, ...)` agrupa $k$ zonas individuales en un «racimo» y lo emite como una fila sintética en la tabla de zonas.
2. Luego `correr_celda` le pasa esa tabla de racimos a `AX.eventos(df_z, b1, ns=(3, 5))` ([`edgelab/research/u1_zonas.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/u1_zonas.py#L72-L108)), que exige **3 o 5 racimos distintos que se solapen entre sí** para recién formar un `Área` operable por `U1`.
3. **Consecuencia matemática:** exigir 3 a 5 racimos solapados de 3 a 5 zonas cada uno equivale a exigir entre **9 y 25 zonas en el mismo nivel**, desplomando el $N$ muestral (en `U1-RACIMOS-GRILLA-NQ-R`, la mejor celda `V2_n3_g10_v60_p1` apenas juntó $N=71$ trades en IS y colapsó a $N=31$ en OOS con `t = -1.21`).
4. **Corrección en esta propuesta:** Un **Cluster HFT causal** (`EvaluarClusterCausal` con $K \in \{3, 4, 5\}$ zonas solapadas) **YA ES un Área consolidada** con límites propios `[lo, hi]`, centro de gravedad ponderado por volumen (`POC`), densidad de empaquetamiento (`packing`) y `detect_bar` causal. Por lo tanto, el motor debe alimentar a `U1` **directamente con cada Cluster HFT como Área (`modo_area = "DIRECTA"`)**, y usar el encadenamiento `AX.eventos` sólo como eje de contraste explícito (`N_area = 1` vs `N_area = 2`).

### 1.2. El sesgo de altura bruta contra zonas altas muy solapadas
En la primera versión del detector de clusters, medir la compresión como `spanTicks / escalaVolTicks` penalizaba apilamientos densos de 5 a 8 zonas HFT cuando cada zona individual medía entre 16 y 24 ticks (4 a 6 puntos de NQ). Una pila de 6 zonas de 20 ticks que se solapan en un rango total de 48 ticks tiene:
$$\text{Packing} = \frac{\sum_{j=1}^{m} H_j}{\max(\text{ Hi}_j) - \min(\text{Lo}_j)} = \frac{120}{48} = 2.50$$
es decir, un promedio de **2,5 zonas HFT superpuestas en cada tick del rango**, aunque el alto bruto sea de 12 puntos.
- **Corrección incorporada en `HFTZonesNQRangosPctV2` (C# y Python/Numba):** La compresión del cluster se mide por **densidad real de solapamiento (`packing`)** y **paso medio normalizado por la altura propia de las zonas (`pasoNorm = (span / m) / avgZoneHeight`)**, permitiendo detectar tanto micro-clusters angostos como trincheras institucionales de 4–6 puntos con alto solapamiento.

### 1.3. Desacople en 2 Etapas para Viabilidad Computacional en Kaggle / Local
Correr el motor de estados 1-tick ($10^8$ ticks por trimestre) dentro del bucle de la grilla es inviable. Siguiendo [`edgelab/bridge/indicators/hftzones_nq.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/bridge/indicators/hftzones_nq.py) y [`docs/research/GUIA_GRILLA_MASIVA.md`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/GUIA_GRILLA_MASIVA.md):
- **Etapa 0 (1 sola vez por trimestre):** `detectar_candidatos_nb` recorre el stream 1-tick en Numba y guarda el censo de candidatos con sus estadísticos suficientes.
- **Etapa 1 ($O(N_{\text{cand}})$, microsegundos por definición):** `filtrar_zonas_nb` genera las poblaciones de zonas HFT bajo cada definición de `GRILLA_ZONA_HFT`.
- **Etapa 2 ($O(N_{\text{zonas}})$, milisegundos por definición):** `evaluar_clusters_causales_nb` y `evaluar_expansiones_causales_nb` construyen el almacén causal de Clusters HFT y Expansiones sin HFT para cada definición de `GRILLA_CLUSTER_HFT`.

---

## 2. Hipótesis Económica y Mecanismo Microestructural

1. **Trinchera de Liquidez (`Cluster HFT`):** Una zona HFT aislada (`Sweep` o `Absorb`) puede ser producto de una barrida oportunista transitoria. En cambio, cuando $K \ge 3$ zonas HFT independientes se confirman dentro de una ventana temporal acotada y se apilan con alta densidad de solapamiento vertical ($\text{packing} \ge 0.85$), revelan un nivel de precio donde algoritmos de ejecución institucional están **defendiendo o recargando inventario repetidamente**.
2. **Asimetría de Reacción y Resolución (`U1` sobre Clusters HFT):**
   - **Hipótesis de Defensa / Rebote (`modo = "rebote"`):** Al re-testear el borde o el `POC` ponderado por volumen de un Cluster HFT vigente tras haberse alejado $\ge d_{\text{sep}}$ puntos, la orden límite (`toque`) o confirmación (`cierre`) captura la defensa del inventario acumulado, con invalidación estructural inmediata al cruzar el extremo opuesto del cluster.
   - **Hipótesis de Absorción Agotada / Ruptura (`modo = "ruptura"`):** Si el precio atraviesa y cierra más allá del rango completo de un Cluster HFT de alto `packing` (especialmente cuando la ruptura deja detrás una **Expansión libre de HFT** causal), quienes defendían la trinchera quedan atrapados y fuerzan una cascada de liquidación.
3. **Hipótesis Cruzada (`U1-HFT-CRUZADO`):** El mismo motor `HFTZonesNQRangosPctV2` produce los dos objetos complementarios del libro de órdenes:
   - **Cluster HFT** = zona de alta fricción / memoria de liquidez (análogo microestructural de `Área` en `U1-CRUZADO`).
   - **Expansión sin HFT** = corredor direccional limpio donde el precio desplazó $\ge 24$ ticks con alta eficiencia sin encontrar respuesta HFT (análogo microestructural de `Vacío` / `AVZ`).
   - Esto permite cruzar **en el mismo reloj causal** el origen de la señal (en Cluster HFT vs en Expansión libre de HFT) con la ubicación del `SL` y `TP` (en la frontera del Cluster HFT o al otro lado de la Expansión libre de HFT).

---

## 3. Parametrización Ortogonal de la Grilla

### 3.1. Nivel 1 — Definición de Zona HFT Base (`GRILLA_ZONA_HFT`: 12 configuraciones post-hoc)
Aplicada sobre el censo único de `detectar_candidatos_nb` (con parámetros estructurales fijos `tick_resolution = 1`, `max_pausa_ms = 100.0`, `retro_floor = 2.0`, `retro_pct = 50.0`):

| Eje | Parámetro | Valores | Justificación microestructural |
| :--- | :--- | :--- | :--- |
| **Cadencia** | `max_avg_ms` | `{15.0, 25.0}` | `15 ms` aísla ráfagas `Predator` + `Ultra`; `25 ms` incluye `Fast` estándar. |
| **Masa crítica** | `min_total_volume` | `{10, 30, 50}` | `10` = congelado E0 (`CAMPAIGN_FROZEN`); `30` = intermedio; `50` = default certificado NT8. |
| **Composición** | `detect_absorb` | `{True, False}` | `True` = barridos ($\ge 4\text{t}$, $\ge 8$ pasos) + absorciones ($<4\text{t}$, $\ge 6$ pasos); `False` = sólo barridos direccionales. |

$$\text{Total Nivel 1} = 2 \times 3 \times 2 = 12 \text{ poblaciones de Zonas HFT}$$

### 3.2. Nivel 2 — Definición Causal de Cluster HFT (`GRILLA_CLUSTER_HFT`: 3 Familias)
Para evitar depender de una única fórmula arbitraria de agrupación, parametrizamos tres familias causales implementadas en [`evaluar_clusters_causales_nb`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py#L483-L735):

#### Familia P — Compresión Estructural por Solapamiento (`MODO_PACKING_PURO`)
No depende del warm-up de historia de sesión; acepta todo apilamiento contiguo de zonas vivas que cumpla las compuertas geométricas:
- `min_zonas_cluster` ($K$): `{3, 4, 5}` zonas HFT vigentes.
- `min_packing` ($\sum H_j / \text{span}$): `{0.85, 1.25}` (`0.85` permite zonas casi adyacentes con gap $\le 0.35 \bar{H}$; `1.25` exige solapamiento real de al menos 25% de altura extra apilada).
- `extension_dibujo` ($W_{\text{viva}}$): `{150, 400}` barras primarias de vigencia de cada zona individual.
- Subtotal Familia P: $3 \times 2 \times 2 = 12$ definiciones.

#### Familia H — Compresión Híbrida V2 (`MODO_V2_HIBRIDO`)
Replica exactamente la regla del indicador visual `HFTZonesNQRangosPctV2.cs` (confirmación inmediata por `altaConfluenciaDirecta` cuando `packing >= 1.35` con $K+1$ zonas o `packing >= 1.65` con $K$ zonas, más filtro adaptativo por frecuencia objetivo `ClustersPorSesion = 1.5` y percentil causal `PctAngosto`):
- `min_zonas_cluster` ($K$): `{3, 4, 5}`.
- `pct_angosto`: `{10, 20}`.
- Subtotal Familia H: $3 \times 2 = 6$ definiciones.

#### Familia D — Polaridad Direccional del Cluster (Variante opcional para el Auditor)
Sobre el subconjunto ganador de Familia P/H, evalúa si la dirección neta del volumen de las zonas que componen el cluster (`polaridad = |sum(dir_j * vol_j)| / sum(vol_j)`) filtra falsos rebotes:
- `polaridad_min`: `{0.0, 0.40}` (`0.0` = agnóstico / simétrico; `0.40` = cluster con sesgo direccional marcado).

### 3.3. Nivel 3 — Gramática de Ejecución `U1` Directa y `U1-HFT-CRUZADO`

#### A. Adaptador Directo (Eliminación del Doble Racimo)
Cada fila del almacén de clusters (`[t_ns, detect_bar, visual_end_bar, lo, hi, poc, n_zonas, width_ticks, packing, net_dir]`) se inyecta directamente como un `Área` operable en `b1` a partir del bar de1m cuyo cierre es $\ge \text{t\_ns}$:
- **Referencia de entrada (`ancla_entrada`):**
  1. `BORDE`: igual que `U1` clásico (`hi` en largos de ruptura / cortos de rebote, `lo` en cortos de ruptura / largos de rebote).
  2. `POC`: entrada anclada en `poc_price` (centro de gravedad ponderado por volumen de las zonas del cluster), probando si el `POC` mejora el ratio recompensa/riesgo al reducir la distancia al `SL` estructural.
- **Parámetros `U1` barridos:**
  - `modo`: `("rebote", "ruptura")`
  - `entrada`: `("toque", "cierre")`
  - `ancla_entrada`: `("borde", "poc")`
  - `sep_pts`: `(3.0, 5.0)` puntos en `NQ` (excursión previa requerida antes del re-testeo)
  - `timeout`: `(15, 30)` barras de 1m
  - `rr` / salida: `(0, 1.5, 2.5)` donde `0` es salida pura por tiempo (`hold`) y `1.5`, `2.5` son múltiplos de `R` sobre el ancho estructural del cluster.

#### B. Variante `U1-HFT-CRUZADO` (Interacción Cluster HFT $\leftrightarrow$ Expansión sin HFT)
Extiende la matriz de 8 celdas de [`edgelab/research/u1_cruzado.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/u1_cruzado.py) reemplazando `Áreas (AX)` por **Clusters HFT causales (`CLUS`)** y `Vacíos (AVZ)` por **Expansiones sin HFT causales (`EXP`)**:

| Código | Señal en | Modo | SL estructural en | TP estructural en | Hipótesis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HC1** | `CLUS` | Rebote | Borde opuesto del `CLUS` | Frontera lejana de `EXP` previa | Rebote en trinchera HFT que rellena el corredor vacío dejado por el impulso. |
| **HC2** | `CLUS` | Ruptura | `POC` / Borde opuesto del `CLUS` | Borde del próximo `CLUS` vigente | Ruptura de trinchera HFT viajando libremente hasta el siguiente cluster activo. |
| **HC3** | `EXP` | Rebote (Mitigación 50%) | Extremo de inicio de la `EXP` (`lo`/`hi`) | `POC` del `CLUS` que frenó el impulso | Pullback al 50% (`MidPrice`) de una expansión limpia sin HFT, apuntando a la zona de absorción. |
| **HC4** | `EXP` | Confluencia `EXP + CLUS` | Borde opuesto del `CLUS` | $2.0\,\text{R}$ / fin de `EXP` | Entrada sólo cuando una `EXP` termina directamente contra un `CLUS` recién confirmado. |

---

## 4. Protocolo de Validación, `E0` Target-Free y Controles Anti-Fuga

1. **Etapa `E0` Target-Free (Antes de tocar retornos):**
   - Medir para cada par `(def_zona, def_cluster)` en los 4 trimestres de `NQ`:
     - **Frecuencia por sesión ($\mu_{\text{ses}}$, $\text{CV}_{\text{trimestral}}$):** descartar combinaciones con $< 0.3$ clusters/sesión (muestra insuficiente, mismo fallo de `U1-RACIMOS-GRILLA`) o $> 8.0$ clusters/sesión (deja de ser evento infrecuente).
     - **Ancho mediano en ticks y estabilidad entre contratos:** descartar definiciones cuyo ancho mediano supere `80 ticks` (20 puntos de NQ) o cuyo turnover entre trimestres supere el umbral de estabilidad.
2. **Alineamiento Temporal Causal Estricto (`ts_avail` / `detect_bar`):**
   - Ningún cluster ni expansión existe antes del `ts_avail` del tick que confirmó la $K$-ésima zona HFT (`clus_int[:, 2] = z_detect_ts[idx]`).
   - En barras de 1 minuto (`b1`), un cluster confirmado en `t_ns` sólo puede habilitar señales en barras cuyo timestamp de cierre sea estrictamente posterior a `t_ns`.
3. **Tres Controles Falsables Obligatorios (`GUIA_GRILLA_MASIVA.md`):**
   - **Control Negativo (`ruido_sintetico`):** permutar los signos de los retornos de 1m manteniendo la geometría de clusters intacta; el percentil 99 de `t_R` fija el piso de selección.
   - **Control de Geometría Trasladada (`placebo_desplazado`):** conservar los `t_ns`, `width_ticks` y `packing` reales de cada cluster pero desplazar `[lo, hi, poc]` por un offset aleatorio $\pm \Delta P$ fuera del nivel real. Si la ventaja de `U1` proviene de la microestructura real del cluster y no sólo del filtro de volatilidad/horario, la celda real debe superar significativamente al placebo desplazado.
   - **Control Positivo (`efecto_plantado`):** inyectar una deriva sintética de $+0.25\,\text{R}$ post-toque en una definición conocida para certificar que el motor recupera la celda plantada en el top 1%.

---

## 5. Guía de Auditoría para el Agente Revisor / Abogado del Diablo

> [!IMPORTANT]
> **Instrucciones para el Agente Auditor (`abogado_del_diablo` / `revisor` / `arquitecto`):**
> Tu objetivo es **atacar, refutar o mejorar** este diseño antes de lanzar el barrido masivo. No aceptes las decisiones por defecto: revisa el código en [`edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py) y contrasta contra [`docs/research/GUIA_GRILLA_MASIVA.md`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/GUIA_GRILLA_MASIVA.md) y los documentos núcleo del proyecto (`DIRECTIVAS.md`, `ERRORES_Y_GUARDAS.md`, `MEDIR_EN_R.md`).

### Vector de Ataque 1: Definición de Vigencia y Mitigación del Cluster
- **Estado actual:** En `evaluar_clusters_causales_nb`, cada zona individual vive `extension_dibujo` barras primarias (`{150, 400}` barras de 5 ticks) y el cluster emitido vive `pct_extension_bars = 300` barras primarias (~15 a 45 minutos según actividad). Cuando se adapta a `U1` en barras de 1m, `U1` usa `timeout` en minutos y descarta el área tras el primer trade (`fin_prev`).
- **Pregunta para el Auditor:** ¿Debe la vigencia de las zonas dentro del cluster medirse en **barras de ticks** (reloj de actividad / volumen, que se acelera en apertura y se frena en almuerzo) o en **segundos / minutos de reloj** (`max_ventana_seg` como en `u1_racimos_grilla.py`), o deben probarse ambos relojes como un eje explícito en `E0`? Además, ¿debe un cluster quedar invalidado antes de dar señal si una barra de 1m lo atraviesa de lado a lado sin activar la entrada?

### Vector de Ataque 2: Crecimiento In-Place del Cluster vs Congelamiento en `DetectBar`
- **Estado actual:** En `evaluar_clusters_causales_nb` (líneas 658–685), si una nueva zona $K+1$ cae sobre un cluster ya activo (`activo_idx >= 0`), el indicador visual actualiza `Lower`, `Upper` y `PocPrice` de ese cluster para no apilar rectángulos duplicados en pantalla.
- **Riesgo de Look-Ahead sutil en Backtest Batch:** Si el backtest de `U1` lee la tabla final de clusters (`df_clusters`) una vez terminado el día, leería el `[lo, hi, poc]` **final** (expandido por la zona $K+1$ en $t_2$) pero con el timestamp `t_ns` original ($t_1 < t_2$) de cuando el cluster tenía sólo $K$ zonas!
- **Solución propuesta y decisión requerida del Auditor:**
  1. **Opción A (Inmutabilidad Estricta para Backtest):** Para el almacén de backtest (`almacen_clusters_hft_grilla`), cuando un cluster se confirma en $t_1$ con $K$ zonas, su geometría `[lo, hi, poc]` en $t_1$ queda **inmutable**; si en $t_2 > t_1$ se agrega una zona $K+1$ que expande los bordes, se emite un **nuevo evento de actualización** con `t_ns = t_2` (o se desactiva la mutación retroactiva de `[lo, hi, poc]`).
  2. **Opción B:** Prohibir cualquier mutación de `clus_flt[activo_idx]` después de `detect_bar` cuando se corre en modo almacén (`inmutable_en_detect=True`).
  - *El Auditor debe dictaminar cuál de las dos opciones se fija como guarda obligatoria antes de correr `U1`.*

### Vector de Ataque 3: Definición de `1R` y Piso de Stop Loss en Clusters HFT
- **Problema conocido en `MEDIR_EN_R.md`:** Si un cluster de `Absorb` + `Sweep` resulta muy angosto (por ejemplo, `width_ticks = 8` ticks = 2.0 puntos de NQ), usar `width_ticks` directo como `1R` infla artificialmente los múltiplos de `R` y magnifica el impacto de 1 tick de slippage.
- **Pregunta para el Auditor:** ¿Cuál debe ser el piso mínimo de `1R` en puntos de NQ (`min_stop_pts`, p. ej. $\max(\text{width\_pts} + 2\times\text{buffer}, 4.0\text{ pts})$ o escalado por `ATR_1m` causal) para que la métrica `media_R` y `t_R` cumpla estrictamente con la directiva de medición en `R`?

### Vector de Ataque 4: Cardinalidad y Presupuesto de Grilla (Control de Multiple Testing)
- **Estado actual:**
  - `12 (Zonas) x 18 (Clusters) = 216` definiciones de almacén.
  - Cruzadas contra `2 (modo) x 2 (entrada) x 2 (ancla: borde/poc) x 2 (sep) x 2 (timeout) x 3 (rr) = 96` celdas `U1` $\implies 20.736$ celdas totales.
- **Pregunta para el Auditor:** ¿Conviene podar primero las `216` definiciones de almacén en la etapa **`E0` target-free** (quedándose sólo con las ~24–36 definiciones geométricamente diversas y estables en frecuencia/ancho, usando clustering jerárquico de solapamiento de eventos como en `indaga`), reduciendo el barrido con retornos a ~2.500–3.500 celdas y bajando el umbral crítico de significancia bajo ruido sintético?

### Formato de Salida Solicitado al Agente Auditor
Al auditar este documento y [`edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py), devuelve tu dictamen estructurado en:
1. **Fugas de futuro o sesgos detectados** (especialmente sobre el Vector de Ataque 2: mutación in-place vs evento inmutable en `t_ns`).
2. **Recortes o adiciones a `GRILLA_ZONA_HFT` y `GRILLA_CLUSTER_HFT`** (justificando qué ejes sobran o qué eje estructural falta).
3. **Regla exacta de `1R` y costos de fricción** a aplicar en `NQ`.
4. **Veredicto sobre el filtro `E0` target-free** previo al barrido con retornos.
