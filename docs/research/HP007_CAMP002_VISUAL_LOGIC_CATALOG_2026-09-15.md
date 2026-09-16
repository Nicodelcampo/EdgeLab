# Catálogo de Diseño Lógico Visual y Espacio de Configuraciones — HP007-CAMP-002
## Fase de Diseño Visual Target-Free (Visual Logic Design)

- **Campaña:** `HP007-CAMP-002`
- **Fecha:** `2026-09-15` / `2026-09-16`
- **Rama Canónica:** `work/hp007-rejection-revisit-campaign-v2-canonical-20260915`
- **Ancla Contractual:** Commit [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491)
- **Documento Rector:** [`docs/research/HP007_CAMP002_VISUAL_LOGIC_DESIGN_HOLD_2026-09-15.md`](HP007_CAMP002_VISUAL_LOGIC_DESIGN_HOLD_2026-09-15.md)
- **Estado Oficial:**
  - `PHASE = VISUAL_LOGIC_DESIGN`
  - `REVISIT_HYPOTHESIS_MEASUREMENT = ON_HOLD_BY_OWNER`
  - `REVISIT_EVENT_SEMANTICS = OWNER_DECISION_PENDING`
  - `SMOKE_CENSUS = SOFTWARE_VALIDATION_ONLY`
  - `OUTCOME_BASED_SELECTION = PROHIBITED`
  - `HOLDOUT = SEALED`

---

## 1. Principio Rector de la Fase Visual

Conforme a la directiva expresa del propietario de la investigación:
> **Queda prohibida toda medición, estimación de traversa, cálculo de P&L o inferencia de edge.**  
> El objetivo exclusivo de esta fase es proporcionar al investigador un catálogo neutral de configuraciones de zonas y modelos de campo, renderizables sobre gráficos, para que **el propietario defina visualmente la semántica de los eventos** antes de redactar cualquier nuevo preregistro.

---

## 2. Catálogo Target-Free de Configuraciones BigTrap2Absorption

Las variantes se construyen variando dimensiones individuales sobre el `PARAM_SPEC` oficial de [`nt8/BigTrap2Absorption.cs`](../../nt8/BigTrap2Absorption.cs) y [`edgelab/bridge/indicators/bigtrap2absorption.py`](../../edgelab/bridge/indicators/bigtrap2absorption.py), sin considerar comportamiento futuro del precio:

| ID Configuración | Parámetro Modificado | Valor | Valor Base | Efecto Microestructural Neutro |
|---|---|---|---|---|
| `BT2A_CFG_01` | *(Base)* | — | — | Ventana de cinta de 25 ticks, absorción percentil 90%, desbalance 2.0x, trampa min 15%. |
| `BT2A_CFG_02` | `TapeWindowTicks` | `15` | `25` | Ventana más estrecha; captura eventos de absorción locales de muy corta duración. |
| `BT2A_CFG_03` | `TapeWindowTicks` | `40` | `25` | Ventana más amplia; suaviza micro-ruido y consolida zonas de mayor persistencia. |
| `BT2A_CFG_04` | `AbsorptionPct` | `95.0` | `90.0` | Umbral más restrictivo; genera menos zonas, restringidas a colas extremas de volumen/desplazamiento. |
| `BT2A_CFG_05` | `AbsorptionPct` | `85.0` | `90.0` | Umbral más permisivo; mayor densidad de zonas y menor separación promedio entre paredes. |
| `BT2A_CFG_06` | `ImbalanceRatio` | `3.0` | `2.0` | Exige asimetría agresiva 3:1 entre bid/ask; selecciona absorciones con fuerte dominancia direccional. |
| `BT2A_CFG_07` | `ImbalanceRatio` | `1.5` | `2.0` | Asimetría moderada 1.5:1; incluye absorciones con presión pasiva menos unilateral. |
| `BT2A_CFG_08` | `MinStackedRows` | `2` | `1` | Requiere que al menos 2 niveles contiguos de precio cumplan absorción simultáneamente (zonas más gruesas). |
| `BT2A_CFG_09` | `ScoreMode` | `AbsDirectional` | `AbsMagnitude` | Pondera la dirección del desplazamiento dentro de la barra en lugar de la magnitud absoluta neta. |

---

## 3. Catálogo de Modelos de Ponderación de Campo y Ablaciones

El campo de resistencia se construye mediante la acumulación causal de zonas as-of:
$$\mathcal{F}(p, t) = 1 - \exp\left( -\sum_{z \in \mathcal{Z}_t} w(z, t) \cdot \mathcal{K}(p, z) \right)$$

### 3.1. Transformaciones de Fuerza ($w_{\text{vol}}$)
- `TRANS_COUNT`: Ponderación unitaria ($w=1.0$), presencia binaria de zona independiente del volumen.
- `TRANS_POWER_025` *(Base)*: $w = (V / V_{\text{ref}})^{0.25}$, compresión sub-lineal fuerte (amortigua outliers de volumen institucional).
- `TRANS_POWER_050`: $w = (V / V_{\text{ref}})^{0.50}$, raíz cuadrada estándar.
- `TRANS_LOG`: $w = \log_2(1 + V / V_{\text{ref}})$, crecimiento logarítmico cóncavo.
- `TRANS_WINSORIZED`: $w = \min(V / V_{\text{ref}}, 3.0)^{0.25}$, tope rígido en 3x el volumen de referencia.

### 3.2. Kernels Espaciales ($\mathcal{K}$)
- `KERNEL_BOX` ($\sigma = 0$): Función escalón estricta; la zona solo proyecta resistencia dentro de su $[b, t]$.
- `KERNEL_GAUSS_NARROW` ($\sigma = 0.75$ ticks): Dispersión estrecha; decae a menos del 1% a 2 ticks de la frontera.
- `KERNEL_GAUSS_BASE` ($\sigma = 1.2$ ticks): Dispersión estándar; suaviza la frontera de la zona permitiendo gradientes en el vacío.
- `KERNEL_GAUSS_BROAD` ($\sigma = 3.0$ ticks): Dispersión amplia; genera campos solapados y desdibuja vacíos estrechos.

### 3.3. Ablaciones de Componente Único (Mecanísticas)
- `FULL`: Modelo completo con maduración bimodal ($t < 1\text{ h}$), decaimiento temporal lento ($t > 4\text{ h}$, $t_{1/2} = 12\text{ h}$) y desgaste por toques as-of ($f = (1 + 0.5 \cdot \text{toques})^{-0.6}$).
- `NO_MATURATION`: Desactiva la maduración ($f_{\text{mat}} = 1.0$ desde $t=0$). Evalúa si una zona recién creada ya actúa con máxima resistencia.
- `NO_TIME_DECAY`: Desactiva el decaimiento temporal ($f_{\text{decay}} = 1.0$ permanente). Evalúa si la antigüedad degrada la resistencia.
- `NO_WEAR`: Desactiva el desgaste por toques ($f_{\text{wear}} = 1.0$). Evalúa si las interacciones físicas consumen la orden pasiva.

---

## 4. Reporte de Deduplicación Causal de Flujos

Para evitar multiplicidad espuria entre configuraciones que produzcan idéntico resultado geométrico:
1. **Deduplicación Nivel 1 (`zone_stream_sha256`)**:
   Se computa el hash SHA-256 del flujo de eventos de zonas generadas `[(z_id, top, bottom, t0, t1, kind)]`. Si dos configuraciones de parámetros producen la misma secuencia exacta de coordenadas, solo una avanza al visor.
2. **Deduplicación Nivel 2 (`field_stream_sha256`)**:
   Se computa el hash del tensor de densidad discretizado $\mathcal{F}(p, t)$ sobre los niveles evaluados. Si dos combinaciones de kernel/fuerza producen vectores equivalentes con tolerancia $< 10^{-4}$, se agrupan bajo un único representante.

---

## 5. Instrucciones de Uso del Visor Gráfico Interactivo

El visor web oficial se encuentra alojado en [`viewer/nt8_bridge/`](../../viewer/nt8_bridge/) y servido localmente en:
`http://localhost:8088/index.html?asset=6E_CONT` (o vía `store_viewer.html`).

### Elementos Visualizados Estrictamente As-Of:
1. **Velas y Ticks:** Gráfico principal con escala de precios exacta.
2. **Zonas Causalmente Disponibles:** Rectángulos coloreados que inician estrictamente en `created_ns / available_ns` y terminan en su invalidación o roll.
3. **Marcadores de Roll / Reset:** Líneas verticales rojas indicando `state_reset_flag == True` donde todo estado previo es purgado.
4. **Campo de Resistencia Lateral:** Curva de densidad agregada proyectada a la derecha de la acción del precio.
5. **Vacíos Visibles:** Franjas intermedias de baja densidad entre zonas activas.
6. **Watermark Mandatorio:** `"PARITY_ABSTAIN: REAL NT8 ORACLE PENDING"` presente en pantalla.

---

## 6. Índice de Muestreo Visual de Sesiones Representativas

Para la inspección visual manual del propietario, se seleccionan 5 sesiones CME representativas bajo criterios deterministas target-free:

| ID Sesión | Fecha CME | Criterio de Selección | Objetivo de la Inspección Visual |
|---|---|---|---|
| `SESS_01` | `2026-01-05` | Primera sesión regular completa del año | Evaluar formación inicial de zonas y arranque en frío del campo. |
| `SESS_02` | `2026-02-18` | Sesión de actividad mediana pre-holdout | Inspeccionar geometría típica de vacíos entre absorciones estándar. |
| `SESS_03` | `2026-03-12` | Sesión contigua al vencimiento/roll contractual | Validar visualmente el corte por roll y reseteo de geometrías activas. |
| `SESS_04` | `2026-04-14` | Sesión de alta volatilidad / alto número de toques | Inspeccionar efecto visual del desgaste por toques (`NO_WEAR` vs `FULL`). |
| `SESS_05` | `2026-05-20` | Sesión de compresión / bajo rango | Observar canibalización de vacíos estrechos ($W < 5$ ticks) bajo distintos kernels. |

---

## 7. Modos de Falla y Abstenciones Formales

1. **Abstención por Falta de Oráculo Real (`ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN`)**:
   Documentada en [`HP007_CAMP002_BT2A_PARITY_AUDIT_2026-09-15.md`](HP007_CAMP002_BT2A_PARITY_AUDIT_2026-09-15.md). No se dispone de oráculos reales exportados de NT8 para `ES`, `MES`, `NQ` o `YM` en la versión actual de BigTrap2Absorption v1.1.1.
2. **Riesgo de Fuga Temporal en Consultas As-Of**:
   Cualquier extracción de zonas debe usar `z.created_ns <= t_now` de manera estricta punto por punto, sin agrupar por sesiones globales completas.
3. **Riesgo de Inmortalidad / Sesgo de Supervivencia**:
   Queda documentado que acondicionar sobre la duración del alejamiento introduce sesgo temporal; cualquier categorización posterior deberá formularse como variable dependiente del tiempo en riesgo.

---

## 8. Decisiones Pendientes Reservadas al Propietario (Checklist)

Antes de redactar un nuevo preregistro o reactivar cualquier runner, el propietario de la investigación inspeccionará los gráficos y definirá:

- [ ] **Definición de Vacío:** ¿Distancia mínima entre bordes de absorción, o umbral de densidad $\mathcal{F} < \theta$?
- [ ] **Fronteras de Entrada y Salida:** ¿Se mide siempre la frontera cercana como entrada y la lejana como cruce?
- [ ] **Primer Acercamiento:** ¿Tolerancia en ticks ({0, 1, 2}) antes de considerar que el precio "tocó" la frontera?
- [ ] **Rechazo Válido:** ¿Cuántos ticks de excursión contraria ({4, 6, 8, 10}) constituyen un rechazo genuino y no mero ruido?
- [ ] **Criterio de Alejamiento:** ¿Se exige tiempo transcurrido (segundos), volumen comerciado fuera, o número de transacciones?
- [ ] **Revisitación:** ¿Qué constituye un segundo acercamiento válido y qué intervalo de tiempo máximo se tolera?
- [ ] **Evolución de Geometría:** ¿La frontera del vacío se congela en el primer toque, o se actualiza si aparecen nuevas zonas intermedias?
- [ ] **Clasificación de Desenlace:** Criterio exacto para distinguir cruce completo, segundo rechazo y censura administrativa.

---

### Aporte al Referente

Se publica el catálogo neutral de diseño lógico visual target-free en `docs/research/HP007_CAMP002_VISUAL_LOGIC_CATALOG_2026-09-15.md`. Queda formalizado el anclaje contractual a `29cad93`, la abstención de paridad en oráculos ausentes, el censo sintético aislado de software y el congelamiento absoluto de mediciones empíricas hasta que el propietario defina visualmente la semántica de los eventos sobre los gráficos.
