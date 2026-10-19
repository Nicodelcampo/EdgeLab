# Programa de análisis — indicadores fijados, rangos como terceridad, cruzado, GEX/L2

- **Fecha:** 2026-08-15
- **Origen:** instrucción de Nico en el hilo de auditoría (store / Kaggle-tools / rangos / cruzado / GEX+L2).
- **Estado:** `PROGRAM_REGISTERED` — no ejecutado.
- **Board:** P-32.
- **Firewall:** `holdout_included=False`, `outcomes_accessed=False`, `pnl_accessed=False`.
- **Nada de este documento afirma un edge ni autoriza F4.**

---

## 1. Lo que Nico fijó

1. Analizar con los indicadores de paridad medida.
2. Usar herramientas prefabricadas de Kaggle (competencias, datasets, repos) **en local**, sobre tablas ya fijadas. Cero ticks crudos a Kaggle.
3. Análisis exploratorio de **rangos** para usarlos después como **terceridad**: un régimen/contexto independiente contra el que se pregunta si los indicadores pareados u otras features tienen capacidad de predicción.
4. Análisis cruzado multiactivo: divergencias, patrones, coincidencias o discrepancias entre indicadores (y entre indicadores y precio).
5. Sumar GEX y L2 lo antes posible, **después** de sus gates, sin producto cartesiano.
6. Pregunta resuelta en §3: **sí se pueden fijar**. El zone store v2 ya existe.

---

## 2. Corrección de inventario — no son «6 con paridad comprobada»

`CLAUDE.md` habla de una campaña formal sobre **5** indicadores existentes y mantiene F9 pausada. El bridge lista cinco kernels. Encima está `aVolClusterPOI` (segunda familia viva) y `AACloseOpenDiffs` (P-16). **No hay un conjunto de 6 con gate P2 formal en verde.** El board manda sobre el recuerdo.

| Indicador | Qué está medido | Qué no está |
|---|---|---|
| `BigTrap2` | W1: 3.628/3.638 EXACT (99,73 %) en junio; 171/171 EXACT en abril+mayo. Imán **cerrado** (F2.7–F2.10). Queda como detector geométrico. | Oráculos `tick:5`/`tick:10` de la campaña. Cruce con aVol **prohibido**. |
| `aVolClusterPOI` v0.5 | 6E 72/72 creaciones, Δscore = 0. ES 09-26: 100 % pre-11-jun, 98,7 % post (P-15). | Nulo propio. Defecto de datos 11-jun (P-15). |
| `Gaps2` v2.0 | P-16: 11.435/11.442 MATCHED, idéntico al local. P2 histórico 1.316/1.316 en ventana corta. | Esa ventana corta (13–16 jul) está **dentro del holdout** — sirve para paridad target-free, no para promover. El gate estructural estricto etiqueta FAIL por residuos de borde. |
| `AACloseOpenDiffs` v1.2 | P-16: 18.004/18.020 MATCHED, residuos idénticos al local. | Gate estructural FAIL (huérfanas + 4 GEOMETRY_DIFF). Declarar «paridad representativa» es decisión de Nico. |
| `VolTicksPOC2` v2.1 | P-16: 151 MATCHED + 1 FEATURE_DIFF. PASS corto con warmup (23/23) en arnés viejo. | Mismo FAIL estructural. Secuenciador causal **no portado** (expuesto en `tick:N`). |
| `HFTZones2` v2.3 | Integrado, P1A real, PASS 1.599 con warmup en arnés viejo. ULP v2.3 medido. | **No** está en P-16. `nt8_bridge.md` lo sigue marcando pendiente de paridad real. |
| `aVolCellPOI2` v2.0 | Integrado, P1A real, 140 zonas con warmup. | Paridad NT8 formal **pendiente**. Secuenciador causal no portado. |
| `YMPreRangeSweep` | Detector de rangos, no de la familia de kernels. 72,5 % doble barrido medido; nulo browniano 54–76 % → no es edge. | P-19…P-22 bloquean cualquier corrida real del barrido L3. Sin `version=` en el `.cs` (P-31). |

Contar «6 comprobados» mezcla tres cosas distintas: paridad formal P2, réplica P-16 con residuos, y humo sintético/P1A. Hasta que Nico nombre el conjunto, el programa usa **solo** las filas de arriba con medición citada, cada una con su estado, nunca como un bloque homogéneo.

---

## 3. Respuesta: sí se fijan, y la máquina ya está

No hace falta un store nuevo. `docs/nt8_bridge.md` ya define el **zone store v2**:

- Tres tablas por partición: `observations.parquet`, `events.parquet`, `zones.parquet`.
- Identidad content-addressed: `dataset_id` (ticks) × `kernel_id` (código) × `config_id` (params + `bar_spec` + `chart_tz`) × `run_id`.
- Publicación atómica; partición publicada **inmutable**; misma reejecución con los mismos digests = idempotente; digests distintos = `DeterminismError` (no sobrescribe).
- Consumo: `edgelab.bridge.features.get_zones_df` + `materialize_features(..., as-of)` — la fuerza bruta **no importa kernels**.
- Exploratoria exige `integrity_state=api_verified`. Formal exige además `parity_exact` o `parity_covered`. Promover un edge exige `parity_exact` **propio**.

Eso es exactamente «correr una vez y dejarlos guardados». El EDA posterior lee el store, no vuelve a NT8.

### Cómo se fija, en orden

1. Árbol de ticks: `E:/EdgeLab/data/nt8_research_v2`, **después** de `verify_tree.py --maxts --columns` (hoy el «100 % libre de holdout» no está medido en disco).
2. Campaña declarativa (`tools/run_campaign.py`) por indicador × contrato × `bar_spec` congelados. Declara N y costo **antes** de correr.
3. `tools/store_audit.py --all --recompute-sample … --promote` (P3.7).
4. A partir de ahí, el EDA y las herramientas de Kaggle consumen `zones` / features as-of. Recalcular = otra campaña con otro `config_id`.

### Lo que el store no es

- No es un atajo para saltear paridad. Una partición `parity_pending` no entra a formal.
- No autoriza outcomes ni P&L. F4 sigue bajo STOP.
- No convierte a BigTrap2 en imán. El objeto fijado es geométrico.
- No reintroduce `sequence` como secuencia del exchange (P-28).

---

## 4. Rangos como terceridad — qué sí y qué no

«Terceridad» acá = un **régimen o contexto independiente**, no un target que el propio rango ya contiene.

**No sirve como target de predicción** el doble barrido (~70 % en YM/ES/NQ). El nulo browniano de reflexión ya da 54–76 %. Preguntar si un indicador «predice el sweep» es, en gran parte, preguntar si predice un fenómeno que un paseo aleatorio también produce. Eso ya está escrito en `H-SWEEP-1` y en la respuesta al auditor de rangos.

**Sí sirve como terceridad**, si se pre-registra qué es cada cosa:

| Rol | Ejemplos | Uso |
|---|---|---|
| Label de régimen (ex-ante) | ancho del prerange, lado del primer barrido, martes vs viernes, sync YM/ES/NQ ese día | estratificar; no es el evento a predecir |
| Contexto de pregunta | «¿la zona de Gaps2 / aVol predice algo **condicional** a +GEX y a rango estrecho?» | la capacidad se mide *dentro* del régimen |
| Feature de rango | re-ingreso al rango (H-SWEEP-2), no el toque del extremo | otra familia, otro presupuesto de multiplicidad |

P-19…P-22 siguen abiertas: no se corre L3 sobre datos reales hasta el fix (toque por cruce, trade date CME, grilla RTH, una sola ventana con su fuente). El constructor `cross_asset_prerange.py` existe; no se reinterpreta su 72,5 % como edge.

---

## 5. Herramientas de Kaggle, en local

Permitido: traer **código** de competencias / datasets / repos (CV temporal, selección de features, nulos, calibración) y correrlo sobre las tablas fijadas del store, en la máquina gobernada.

Prohibido, vigente (P-07, P-18, F2.10 `NO_UPLOAD`):

- subir ticks, parquets de CQG/CME o zonas derivadas a Kaggle;
- usar la V1 `edgelab-cme-futures-universe` como dataset exploratorio;
- tratar un notebook público como evidencia.

`research-v2` no es publicable: `ABSTAIN_LICENSE` y tres gates de capacidad en rojo. Aprobar la licencia (P-07) **no** produce `PASS` — destapa `ABSTAIN_CAPACITY`.

---

## 6. Cruzado multiactivo

Reloj común: `trade_date` CME (`sessions_cme.py`), no fecha calendario, no `session_index` de NT8 (se traduce por trade-date, nunca por ordinal).

Alineación: materializar cada indicador as-of sobre **la misma** serie de barras del activo. Comparar ES vs NQ vs YM es comparar features en el mismo `trade_date` / misma ventana de sesión, no timestamps crudos.

Limitación ya medida (P-28): `sequence == source_row` en 11/11 archivos. Cualquier claim de microestructura que asuma secuencia del exchange **no está soportado** por estos ticks.

BigTrap2 × aVol sigue prohibido (acta F2.7–F2.10). El cruzado es entre familias **registradas por separado**, cada una con su ledger y su presupuesto de multiplicidad.

---

## 7. GEX y L2 — lo antes posible, no ahora

| Capa | Qué hay | Gate que falta |
|---|---|---|
| GEX diario | Parquets locales 17 años (`D:\\EdgeLab\\data\\gex\\`). Reconstructor y stress test en el repo. | `GEX_FUENTES_Y_GATES` sigue `DRAFT_NON_EXECUTABLE`. El dictamen del 14-ago afirma identidad aritmética contra el boletín #154; eso no sustituye el gate corrido y sellado. Sin M0 no hay pin, ni flip, ni cruce con detectores. |
| L2 | `tools/convert_l2_to_parquet.py` existe. | Sin paridad de libro, sin cruce. Misma regla: no producto cartesiano (ZAMR). |

Cuando entren, entran como **covariable de régimen ex-ante** (el propio dictamen GEX lo dice), no como feature más en un join masivo contra zonas.

---

## 8. Orden de ejecución (no se salta)

1. `verify_tree.py --maxts --columns` sobre `nt8_research_v2` — cierra la prueba física de holdout y P-28.
2. Nico nombra el conjunto de indicadores de este programa (P-32) y, si quiere, declara paridad representativa del trío P-16.
3. Publicar al store las configs congeladas sobre research-v2. P3.7 antes de cualquier EDA.
4. EDA de rangos como régimen (no como target de sweep). Pre-registrar label vs feature.
5. Cruzado multiactivo sobre las features fijadas.
6. Herramientas de Kaggle **locales** sobre esas tablas.
7. GEX-M0 / L2, después. F4 solo con manifiesto y OK explícito.

---

Aporte al referente: el destino de research dejó de ser un recuerdo de chat y pasó a un objeto con inventario honesto; la pregunta del fijado ya tenía respuesta en el store v2 — lo que faltaba era no volver a calcular lo que ya se puede consultar por identidad.
