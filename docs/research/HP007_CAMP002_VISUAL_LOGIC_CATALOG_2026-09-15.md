# Catálogo de Diseño Lógico Visual y Espacio de Configuraciones — HP007-CAMP-002
## Fase de Diseño Visual Target-Free (Visual Logic Design)

- **Campaña:** `HP007-CAMP-002`
- **Fecha:** `2026-09-15` / `2026-09-16`
- **Rama Canónica:** `work/hp007-rejection-revisit-campaign-v2-canonical-20260915`
- **Ancla Contractual:** Commit [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491)
- **Documento Rector:** [`docs/research/HP007_CAMP002_VISUAL_LOGIC_DESIGN_HOLD_2026-09-15.md`](HP007_CAMP002_VISUAL_LOGIC_DESIGN_HOLD_2026-09-15.md)
- **Estado de la Fase:**
  - `PHASE = VISUAL_LOGIC_DESIGN`
  - `VISUAL_CONFIGURATION_CATALOG_SPECIFIED = YES`
  - `VISUAL_INSPECTION_PACKAGE_COMPLETED = YES`
  - `READY_FOR_OWNER_VISUAL_REVIEW = YES`
  - `REVISIT_HYPOTHESIS_MEASUREMENT = ON_HOLD_BY_OWNER`
  - `REVISIT_EVENT_SEMANTICS = OWNER_DECISION_PENDING`
  - `OUTCOME_BASED_SELECTION = PROHIBITED`
  - `HOLDOUT = SEALED`

---

## 1. Principio Rector de la Fase Visual

Conforme a la directiva expresa y vinculante del propietario de la investigación:
> **Queda prohibida toda medición empírica, estimación de probabilidad de traversa, cálculo de P&L o inferencia de edge direccional.**  
> El objetivo exclusivo de esta fase es proporcionar al investigador un catálogo neutral de configuraciones de zonas y modelos continuos de intensidad de campo, renderizables sobre gráficos de activos contractualmente habilitados, para que **el propietario defina visualmente la semántica de los eventos** antes de redactar cualquier nuevo preregistro o reactivar mediciones.

---

## 2. Catálogo Target-Free de Configuraciones BigTrap2Absorption

Las 9 configuraciones se construyen variando dimensiones individuales sobre el `PARAM_SPEC` oficial de [`nt8/BigTrap2Absorption.cs`](../../nt8/BigTrap2Absorption.cs) (SHA-256: `18d16312...`) y [`edgelab/bridge/indicators/bigtrap2absorption.py`](../../edgelab/bridge/indicators/bigtrap2absorption.py) (SHA-256: `d5913b13...`), sin condicionar sobre comportamiento futuro del precio ni outcomes. Cada configuración está completamente especificada en formato machine-readable en [`docs/research/HP007_CAMP002_BT2A_CONFIG_CATALOG_2026-09-15.json`](HP007_CAMP002_BT2A_CONFIG_CATALOG_2026-09-15.json).

| ID Configuración | Parámetro Modificado | Valor | Valor Base | Efecto Microestructural Neutro |
|---|---|---|---|---|
| `BT2A_CFG_01` | *(Base)* | — | — | Ventana de cinta de 25 ticks, absorción percentil 90%, desbalance 2.0x, trampa min 15%. |
| `BT2A_CFG_02` | `TapeWindowTicks` | `15` | `25` | Ventana más estrecha; captura eventos de absorción locales de muy corta duración. |
| `BT2A_CFG_03` | `TapeWindowTicks` | `40` | `25` | Ventana más amplia; suaviza micro-ruido y consolida zonas de mayor persistencia temporal. |
| `BT2A_CFG_04` | `AbsorptionPct` | `95.0` | `90.0` | Umbral más restrictivo; genera menor densidad de zonas, restringidas a colas extremas de volumen/desplazamiento. |
| `BT2A_CFG_05` | `AbsorptionPct` | `85.0` | `90.0` | Umbral más permisivo; mayor densidad de zonas y menor separación promedio entre zonas contiguas. |
| `BT2A_CFG_06` | `ImbalanceRatio` | `3.0` | `2.0` | Exige asimetría 3:1 entre bid/ask; selecciona absorciones con mayor dominancia unidireccional. |
| `BT2A_CFG_07` | `ImbalanceRatio` | `1.5` | `2.0` | Asimetría moderada 1.5:1; incluye absorciones con presión pasiva bilateral. |
| `BT2A_CFG_08` | `MinStackedRows` | `2` | `1` | Requiere que al menos 2 niveles contiguos de precio cumplan absorción simultáneamente (zonas de mayor espesor). |
| `BT2A_CFG_09` | `ScoreMode` | `AbsDirectional` | `AbsMagnitude` | Pondera la dirección del desplazamiento dentro de la barra en lugar de la magnitud absoluta neta. |

---

## 3. Definición Matemática Rigurosa de Modelos de Campo e Intensidad Continua

El perfil continuo de intensidad espacial (`aggregate zone intensity field`) describe la densidad microestructural acumulada por zonas activas as-of. Se prohíben términos interpretativos ("paredes", "resistencia", "obstáculo"). La nomenclatura se restringe a: `zone intensity`, `aggregate field`, `high-density region`, `low-density interval`, `zone contribution`.

### 3.1. Acumulación Causal del Campo
Dado un precio $p$ en el tiempo $t$, la intensidad agregada adimensional $\mathcal{F}(p, t) \in [0, 1)$ se define como:
$$\mathcal{F}(p, t) = 1 - \exp\left( -\sum_{z \in \mathcal{Z}_t} w(z, t) \cdot \mathcal{K}(d(p, z)) \right)$$

donde:
- $\mathcal{Z}_t = \{ z : t_{\text{created}}(z) \le t < t_{\text{invalidated}}(z) \}$ es el conjunto de zonas estrictamente activas as-of en el instante $t$.
- $d(p, z)$ es la distancia ortogonal en ticks desde el precio $p$ hasta el intervalo de la zona $[z_{\text{lower}}, z_{\text{upper}}]$:
  $$d(p, z) = \max(0, z_{\text{lower}} - p, p - z_{\text{upper}})$$
- $w(z, t) = w_{\text{vol}}(z) \cdot f_{\text{mat}}(t - t_z) \cdot f_{\text{decay}}(t - t_z) \cdot f_{\text{wear}}(n_z(t))$ es el peso dinámico compuesto de la zona.

### 3.2. Kernels Espaciales ($\mathcal{K}$) y Truncamiento
La función kernel $\mathcal{K}(d)$ proyecta la contribución de la zona en función de la distancia $d$:

1. **`KERNEL_BOX` ($\sigma = 0$ ticks)**:
   $$\mathcal{K}_{\text{box}}(d) = \begin{cases} 1.0 & \text{si } d = 0 \text{ (precio dentro del intervalo de la zona } [z_{\text{lower}}, z_{\text{upper}}]\text{)} \\ 0.0 & \text{si } d > 0 \end{cases}$$

2. **`KERNEL_GAUSS` (Dispersión gaussiana con truncamiento en $3\sigma$)**:
   $$\mathcal{K}_{\text{gauss}}(d; \sigma) = \begin{cases} \exp\left(-\frac{d^2}{2\sigma^2}\right) & \text{si } 0 \le d \le 3\sigma \\ 0.0 & \text{si } d > 3\sigma \end{cases}$$
   - **`KERNEL_GAUSS_NARROW` ($\sigma = 0.75$ ticks)**:
     - En $d = 0$ ticks: $\mathcal{K}(0) = 1.000000$ (100.00%).
     - En $d = 1$ tick: $\mathcal{K}(1) = \exp\left(-\frac{1}{2 \times 0.75^2}\right) = \exp(-0.888889) \approx 0.411112$ (41.11%).
     - En $d = 2$ ticks: $\mathcal{K}(2) = \exp\left(-\frac{4}{2 \times 0.5625}\right) = \exp(-3.555556) \approx 0.028566$ (**2.86%**).
     - Radio de corte ($3\sigma$): $2.25$ ticks. Para todo $d > 2.25$ ticks, $\mathcal{K}(d) = 0.0$.
   - **`KERNEL_GAUSS_BASE` ($\sigma = 1.20$ ticks)**:
     - En $d = 0$ ticks: $\mathcal{K}(0) = 1.000000$.
     - En $d = 2$ ticks: $\mathcal{K}(2) = \exp\left(-\frac{4}{2 \times 1.44}\right) = \exp(-1.388889) \approx 0.249352$ (24.94%).
     - Radio de corte ($3\sigma$): $3.60$ ticks.
   - **`KERNEL_GAUSS_BROAD` ($\sigma = 3.00$ ticks)**:
     - Radio de corte ($3\sigma$): $9.00$ ticks. Suaviza fuertemente el espacio entre zonas adyacentes.

### 3.3. Factor de Normalización Causal de Volumen ($V_{\text{ref}}$)
Para evitar fugar información agregada de la sesión o del dataset:
- $V_{\text{ref}}(t)$ se calcula como la mediana móvil estrictamente causal del volumen absorbido registrado en las últimas 500 zonas consolidadas antes de $t$.
- Durante el arranque en frío (primeras 100 zonas del contrato), se adopta el prior fijo $V_0 = 100.0$ contratos.
- Si una zona registra volumen cero o nulo, se le asigna peso base unitario $w_{\text{vol}} = 1.0$.
- Transformaciones evaluadas:
  - `TRANS_COUNT`: $w_{\text{vol}} = 1.0$.
  - `TRANS_POWER_025` *(Base)*: $w_{\text{vol}} = (V_z / V_{\text{ref}})^{0.25}$.
  - `TRANS_POWER_050`: $w_{\text{vol}} = (V_z / V_{\text{ref}})^{0.50}$.
  - `TRANS_LOG`: $w_{\text{vol}} = \log_2(1 + V_z / V_{\text{ref}})$.
  - `TRANS_WINSORIZED`: $w_{\text{vol}} = \min(V_z / V_{\text{ref}}, 3.0)^{0.25}$.

### 3.4. Ablaciones Mecanísticas de Componente Único
- **`FULL`**: Modelo completo con maduración sigmoidal ($f_{\text{mat}} = \frac{1}{1 + \exp(-(t - 1800)/600)}$ para $t$ en segundos), decaimiento temporal exponencial lento ($f_{\text{decay}} = \exp(-\ln(2) \cdot \max(0, t - 14400) / 43200)$ con vida media de 12 horas), y atenuación por toques ($f_{\text{wear}} = (1 + 0.5 \cdot n_z)^{-0.6}$).
- **`NO_MATURATION`**: $f_{\text{mat}} = 1.0$ idénticamente para todo $t$. Evalúa el efecto de proyectar intensidad plena desde el tick de creación.
- **`NO_TIME_DECAY`**: $f_{\text{decay}} = 1.0$ idénticamente para todo $t$. Evalúa la persistencia indefinida de zonas no invalidadas.
- **`NO_WEAR`**: $f_{\text{wear}} = 1.0$ idénticamente. Evalúa el comportamiento sin degradación por interacción física del precio.

### 3.5. Discretización y Precisión
- Discretización de precios: Grilla evaluada en múltiplos exactos de $\text{tick\_size} = 0.25$ pts en NQ.
- Precisión numérica: Todos los valores de campo $\mathcal{F}(p, t)$ se redondean a 6 decimales (`round(val, 6)`) previo a serialización y cómputo de hashes.

---

## 4. Resultados de Deduplicación Causal de Flujos y Clases de Equivalencia

Se ejecutaron las 9 configuraciones sobre las 4 sesiones únicas representativas de `NQ 06-26` (1.873.468 ticks procesados) bajo el runner [`tools/run_visual_configurations.py`](../../tools/run_visual_configurations.py). Los resultados consolidados se registran en [`docs/research/HP007_CAMP002_DEDUPLICATION_REPORT_2026-09-15.json`](HP007_CAMP002_DEDUPLICATION_REPORT_2026-09-15.json):

### 4.1. Deduplicación Nivel 1 (Geometría de Zonas — `zone_stream_sha256`)
Las 9 configuraciones generaron flujos geométricos estrictamente distintos (cero colapso de equivalencia, 9 clases únicas):

| ID Configuración | Zonas Totales Generadas | Hash del Flujo de Zonas (`zone_stream_sha256`) | Clase de Equivalencia |
|---|---|---|---|
| `BT2A_CFG_01` | 3.710 | `aea22487966d1a9fdba13faa80ab5fd98c8492e298cdaea308b1cfb7949c9b3a` | `ZONE_CLASS_01` |
| `BT2A_CFG_02` | 5.214 | `8cd38b14f54a35edf6c5f1ec87403e721a873f7cae2230e47a0e63a65ed02ebf` | `ZONE_CLASS_02` |
| `BT2A_CFG_03` | 2.291 | `a71baca61ae9bd288c318c71acca3520b9847189850ba79824f8dd9764201e72` | `ZONE_CLASS_03` |
| `BT2A_CFG_04` | 1.982 | `7577bd58e61f76bba12919180361a8008d492dec40dc6f47d7f7c5dc5966ed47` | `ZONE_CLASS_04` |
| `BT2A_CFG_05` | 5.137 | `84422399237ad4152c6f1d3f2ac375011a5de691ad9c7888aba1ab13e7533653` | `ZONE_CLASS_05` |
| `BT2A_CFG_06` | 3.062 | `24eefbeabd83dc4e83c74ee0f339cf39943bf1e033783a45c0f64c679b88cf1e` | `ZONE_CLASS_06` |
| `BT2A_CFG_07` | 3.785 | `28ead7f3d02bbf812c75a40a831e5f8fdf178f7e2ce71fe25852f50bf8f9c10f` | `ZONE_CLASS_07` |
| `BT2A_CFG_08` | 2.414 | `da0a1a0cf71a4ad857b28fa526017b35520e5ff3baae3dfec4f09d84e56598c8` | `ZONE_CLASS_08` |
| `BT2A_CFG_09` | 5.154 | `9d080ab709894cf5e9c0c80b5e5a5a1f681a2f643e2e8e3d09a06db9566d8e8b` | `ZONE_CLASS_09` |

### 4.2. Deduplicación Nivel 2 (Tensores de Intensidad Continua — `field_stream_sha256`)
Evaluados sobre la grilla espaciotemporal discretizada de la sesión mediana (`2026-04-01`):
- **Equivalencias Idénticas:** `FIELD_TRANS_WINSORIZED` y `FIELD_ABL_NO_TIME_DECAY` colapsaron al mismo hash que `FIELD_GAUSS_BASE` (`13d713064c030066...`), ya que las zonas intradiarias se invalidan antes de la cota de 4 horas de decaimiento y los volúmenes relativos en esta muestra no superaron el límite de corte $3.0\times V_{\text{ref}}$.
- **Efecto de Maduración:** `FIELD_ABL_NO_MATURATION` presentó un incremento de $14,4\times$ en la intensidad media del campo ($0,0230$ vs $0,0016$), confirmando empíricamente que la maduración suprime fuertemente la intensidad de zonas recién nacidas.
- **Efecto de Desgaste:** `FIELD_ABL_NO_WEAR` aumentó la intensidad media un $56\%$ ($0,0025$ vs $0,0016$), evidenciando la degradación de intensidad por toques sucesivos.
- **Diferenciación Espacial:** `FIELD_BOX` mostró una correlación moderada ($r = 0,65$ a $0,66$) con los kernels gaussianos, confirmando que la función escalón produce intervalos de densidad radicalmente más discontinuos.

---

## 5. Instrucciones de Visualización y Watermarks Mandatorios

### Activos y Advertencias Contractuales
Bajo el ancla contractual [`29cad93`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491):
- **Activos Canónicamente Habilitados:** `ES`, `MES`, `NQ`, `YM` (`PARTIAL_MULTI_ASSET_CERTIFICATION`).
- **Activos en Abstención:** `6E`, `6B`, `6J`, `GC`, `ZB`, `MBT` (`CONTRACT_REGIME = ABSTAIN`).
- El paquete visual canónico se genera primariamente sobre **`NQ 06-26`** (Tick size: 0.25).
- Si se inspecciona `6E_CONT` con fines de diagnóstico del visor, rigen dos advertencias obligatorias:
  1. `CONTRACT_REGIME = ABSTAIN` (la serie continua de 6E no posee certificación de calendario CME).
  2. `INDICATOR_PARITY = ABSTAIN` (no existe oráculo real exportado de NT8).

### Watermarks en Pantalla
Todo gráfico estático o vista web debe presentar de forma visible e inamovible el watermark:
- **Para NQ / ES:** `PARITY_ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY`
- **Para 6E:** `CONTRACT_REGIME = ABSTAIN | INDICATOR_PARITY = ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY`

### Componentes Gráficos As-Of:
1. **Velas de Precio:** Escala OHLC exacta por barra tick (120t).
2. **Zonas Activas:** Rectángulos horizontales delimitados estrictamente entre $t_{\text{created}}$ y $t_{\text{invalidated}}$. Color e intensidad determinados por la contribución de la zona.
3. **Frontera de Rollover / Reset:** Línea vertical roja en ticks donde `state_reset_flag == True`, marcando purga total de memoria.
4. **Perfil Lateral de Intensidad Agregada (`aggregate field`):** Curva continua de densidad a la derecha de la acción del precio.
5. **Intervalos de Baja Densidad:** Franjas de precio donde $\mathcal{F}(p, t) < \theta$, visualmente distinguibles.
6. **Prohibición Absoluta de Outcomes:** Cero marcadores de trades futuros, cero cálculo de P&L, cero flechas de compra/venta, cero etiquetas de éxito/fracaso de cruce.

---

## 6. Selección Reproducible de Sesiones Representativas

Para evitar sesgo de selección visual oportunista, las sesiones se eligen mediante un algoritmo determinista (`tools/select_canonical_visual_sessions.py`) sobre el universo pre-holdout de NQ:

| ID Sesión | Fecha CME | Día | Criterio de Selección Formal | Métrica Evaluada | Ticks | Rango (pts) | Objetivo de la Inspección Visual |
|---|---|---|---|---|---|---|---|
| `SESS_01` | `2026-03-17` | Martes | Primera sesión activa regular pre-holdout | `min(trade_date)` elegible | 331.822 | 388,75 pts (1.555t) | Evaluar formación inicial de zonas y arranque en frío del campo. |
| `SESS_02` | `2026-04-01` | Miércoles | Mediana de actividad | Percentil 50 de ticks (exacto p50) | 517.143 | 468,25 pts (1.873t) | Inspeccionar geometría típica de vacíos entre absorciones estándar. |
| `SESS_03` | `2026-03-17` | Martes | Frontera de rollover contractual NQ 03-26 $\rightarrow$ NQ 06-26 | `state_reset_flag == True` en apertura | 331.822 | 388,75 pts (1.555t) | Validar visualmente el corte por roll y reseteo de zonas activas. |
| `SESS_04` | `2026-04-08` | Miércoles | Alta volatilidad / dispersión | Percentil 90 de rango (3.608t vs p90 3.563t) | 572.626 | 902,00 pts (3.608t) | Inspeccionar efecto visual de la atenuación por toques (`NO_WEAR` vs `FULL`). |
| `SESS_05` | `2026-05-22` | Viernes | Rango estrecho / compresión | Percentil 10 de rango (1.252t vs p10 1.255t) | 451.877 | 313,00 pts (1.252t) | Observar comportamiento de vacíos estrechos bajo distintos anchos de kernel. |

El manifiesto completo de procedencia con fechas exactas, cuantiles y SHA-256 del script se publica en [`docs/research/HP007_CAMP002_SESSION_SELECTION_MANIFEST_2026-09-15.json`](HP007_CAMP002_SESSION_SELECTION_MANIFEST_2026-09-15.json).

---

## 7. Checklist de Decisiones Reservadas al Propietario

El trabajo técnico concluye entregando las alternativas visuales comparables y neutrales. El propietario inspeccionará las imágenes y definirá:

- [ ] **Definición de Vacío:** ¿Distancia mínima en ticks entre zonas de absorción contiguas, o umbral de intensidad $\mathcal{F} < \theta$?
- [ ] **Fronteras del Evento:** ¿Se mide siempre la frontera cercana como primer toque y la opuesta como cruce completo?
- [ ] **Tolerancia de Primer Acercamiento:** ¿Tolerancia en ticks ({0, 1, 2}) para declarar inicio de aproximación?
- [ ] **Definición de Rechazo Válido:** ¿Magnitud de excursión contraria en ticks ({4, 6, 8, 10}) requerida para validar rechazo sin ruido?
- [ ] **Calificación de Alejamiento:** ¿Criterio de permanencia fuera (tiempo en segundos, volumen comerciado o conteo de ticks)?
- [ ] **Revisitación:** ¿Qué define un segundo acercamiento calificado y cuál es la ventana máxima permitida?
- [ ] **Dinámica de Fronteras:** ¿La geometría del vacío se congela en el primer toque o muta si nacen nuevas zonas intermedias?
- [ ] **Taxonomía de Desenlaces:** Criterios formales para distinguir traversa completa, segundo rechazo y censura administrativa/roll.

---

### Aporte al Referente

Se publica la especificación neutral y formal del catálogo visual y espacio de configuraciones en `docs/research/HP007_CAMP002_VISUAL_LOGIC_CATALOG_2026-09-15.md`. Se eliminan supuestos preconcebidos de resistencia, se establecen las fórmulas exactas del kernel gaussiano truncado y de normalización causal, se estipulan los watermarks mandatorios y se circunscribe la inspección a activos contractualmente certificados (`NQ 06-26` bajo `29cad93`).
