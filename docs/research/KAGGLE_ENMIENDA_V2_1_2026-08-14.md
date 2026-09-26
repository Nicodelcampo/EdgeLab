# Enmienda v2.1 al Contrato Kaggle v2 (2026-08-14)

**Origen**: auditoría externa del intento de ejecución de la Fase 0 del contrato sobre el dataset `edgelab-cme-futures-universe` v1.
**Estado del contrato base**: `DRAFT_NON_EXECUTABLE`. Esta enmienda no lo declara ejecutable; corrige y hace ejecutables siete puntos que hoy son ambiguos o violables sin detección.
**Naturaleza**: propuesta. Cada cláusula requiere ratificación explícita de Nico para pasar a norma.

---

## Cláusula 1 — El sello del holdout es por trade date de Chicago, nunca por timestamp UTC

**Texto propuesto**: toda exclusión de holdout se computa como `trade_date(t) ≤ 2026-06-30`, donde `trade_date` es la sesión CME en `America/Chicago` con apertura a las 17:00 CT del día anterior. Está prohibido implementar el firewall como comparación contra un instante UTC.

**Motivo**: medido, no argumentado. En `6E_09-26` (1.131.047 ticks) el corte UTC conserva **871 filas** del trade date 2026-07-01. Ver P-17.

**Implementación de referencia**: `edgelab/kaggle/sessions_cme.py` + `edgelab/kaggle/seal.py`.

**Verificación exigida**: todo reporte formal publica `rows_cut_holdout`, `cut_rows_by_trade_date` y `rows_leaked_by_naive_utc_cut`. Si el último es > 0, el reporte debe explicitar que un corte UTC habría filtrado.

---

## Cláusula 2 — Separación entre custodia y análisis

**Texto propuesto**: se distinguen dos clases de dataset.

| Clase | Contenido | Puede adjuntarse a un notebook formal |
|---|---|---|
| `raw_custody` | ticks crudos completos, incluido el tramo de holdout | **no** |
| `research` | derivadas con sello aplicado, holdout físicamente ausente | sí |

Un dataset `raw_custody` no satisface el requisito de "holdout físicamente ausente" y por lo tanto no habilita análisis, aunque el código aplique el sello. La v1 actual se reclasifica como `raw_custody`.

**Motivo**: el contrato ya exige ausencia física; faltaba el mecanismo que impide usar por error el archivo que la viola.

---

## Cláusula 3 — `ABSTAIN_CAPACITY` es un veredicto, no un obstáculo a sortear

**Texto propuesto**: si el input excede 10 GB, los archivos top-level exceden 20, el peak RSS excede 20 GB o el runtime excede 6 h, la corrida emite `ABSTAIN_CAPACITY` y termina. Está prohibido resolver un exceso de presupuesto partiendo la corrida en más sesiones hasta que entre.

**Implementación de referencia**: `inventory.budget_gates`, gate `G2` del notebook 00.

**Nota de plataforma**: la documentación de Kaggle indica un máximo de 50 archivos de nivel superior por dataset y 200 GB por dataset. La v1 existe con 57 archivos top-level. Se registra la discrepancia observada; no se afirma cuál es la regla vigente ni se construye sobre esa ambigüedad.

---

## Cláusula 4 — La identidad del código se verifica por git-blob, no por declaración

**Texto propuesto**: todo `run_manifest.json` incluye, por cada módulo `edgelab` efectivamente importado, su `git_blob_sha1`, su `sha256` y su tamaño. El paquete se distribuye a Kaggle como **code dataset** y su blob queda registrado en el manifiesto de cada corrida.

**Motivo**: el contrato ya advierte que "la mera presencia del campo no alcanza". El git-blob sha1 es directamente comparable con `git ls-files -s` del repo, así que la identidad del código que corrió en Kaggle es verificable contra la rama sin necesidad de git dentro del notebook. Es el mismo mecanismo con el que se cerró la identidad de los kernels en P-16 y P-08.

**Implementación de referencia**: `identity.code_identity` + `identity.imported_module_paths`.

---

## Cláusula 5 — Regla de roll declarada antes de tocar outcomes

**Texto propuesto**: el contrato activo de cada `instrument_root` en cada sesión se determina por **volumen diario**, con desempate por **open interest** y, si ninguno está disponible, por las **fechas oficiales de roll de CME** como fallback. La regla recibe un `roll_rule_id` y su hash entra en `roll_schedule_sha256`. Está prohibido construir series continuas concatenando contratos sin declarar la regla.

**Evidencia que lo motiva**: en `6E_09-26`, sobre 66 trade dates medidos, sólo **11** alcanzan cobertura de sesión completa; 28 son parciales y 27 escasas (todas entre el 2026-04-01 y el 2026-05-25). No es un defecto de datos: es el back month que casi no negocia. Analizar ese tramo como si fuera front month mezcla dos regímenes de liquidez distintos.

**Corolario**: el chequeo "0 minutos faltantes en horario activo" (P-14 / P-15) se aplica al contrato activo, no a todo contrato.

---

## Cláusula 6 — Reproducibilidad de la sesión de Kaggle

**Texto propuesto**: un artefacto sólo es formal si se produjo con `Save Version → Save & Run All (Commit)`, con internet OFF, semilla declarada y `environment_manifest_sha256` publicado. Las salidas de una sesión interactiva no son artefactos formales.

**Motivo**: en Kaggle sólo el commit persiste las salidas de forma reproducible; una ejecución interactiva no deja evidencia de haber corrido el notebook completo de arriba a abajo.

**Nota sobre P-05**: el contrato considera que un `Save & Run All` cumple la función de CI para los notebooks. Eso no cierra P-05 (CI del repo en Actions), y por eso los scripts que dependen de rutas de sandbox (`/data/p16`) viven en `tools/sandbox/` y no en `tests/`.

---

## Cláusula 7 — Toda validación por batches debe tener un test de paridad contra el cálculo en memoria

**Texto propuesto**: cuando el presupuesto de RAM obligue a procesar por batches, el acumulador streaming debe tener un test que compare clave por clave contra el cálculo en memoria sobre un archivo de referencia, en al menos tres tamaños de batch distintos. Sin ese test, los números del streaming no son auditables.

**Implementación de referencia**: `tools/sandbox/kaggle_streaming_parity.py`. Resultado medido: 28 claves de integridad, 594 claves de actividad, 66 trade dates y el sello completo idénticos en batches de 7.919 / 100.000 / 500.000 / 1.131.047 filas (143 / 12 / 3 / 1 batches).

---

## Ratificación

| Cláusula | Ratificada | Fecha | Nota |
|---|---|---|---|
| 1 · sello por trade date | pendiente | | ya implementada en código |
| 2 · custodia vs análisis | pendiente | | implica reclasificar la v1 |
| 3 · ABSTAIN_CAPACITY | pendiente | | ya implementada en código |
| 4 · identidad por git-blob | pendiente | | ya implementada en código |
| 5 · regla de roll | pendiente | | requiere fuente de volumen/OI |
| 6 · Save & Run All | pendiente | | |
| 7 · paridad streaming↔batch | pendiente | | ya implementada y verificada |
