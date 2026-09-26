# Pre-registro de la campaña Kaggle — borrador v0.1 (2026-08-14)

**Estado**: BORRADOR. No congelado. Escrito **antes** de tocar un solo outcome y antes de que exista un dataset que pase la Fase 0.
**Requisito de congelamiento**: cotejo con las secciones del Contrato Kaggle v2 que aún no fueron auditadas línea por línea (24 tests adversariales y plan de trabajo de 25 ítems) + ratificación de la enmienda v2.1 + un dataset `research` que pase los gates G1–G4.
**Regla de oro**: nada de lo que sigue puede cambiarse después de mirar resultados fuera de muestra. Si algo cambia, se registra el cambio, la fecha y el motivo, y la corrida anterior queda como evidencia, no como borrador descartado.

---

## 1. Pregunta

¿Existe, en el universo de 11 activos de CME, alguna combinación de frame y especificación que produzca un desplazamiento local medible y estable fuera de muestra, después de corregir por la cantidad de especificaciones probadas?

La hipótesis nula por defecto es que **no**. El resultado esperado a priori es `REFUTED` o `UNSTABLE`. `PROMOTE_RESTRICTED` requiere superar todos los gates declarados abajo.

---

## 2. Datos y firewall

- **Ventana de investigación**: trade dates ≤ 2026-06-30 (sesión CME, America/Chicago).
- **Holdout**: 2026-07-01 → 2026-12-31. No se abre. Su apertura exige el token `M8_HOLDOUT_OPENED_ONCE`, una sola vez, con la regla de decisión ya congelada.
- **Sello**: `edgelab/kaggle/seal.py`. Todo reporte publica filas cortadas por trade date.
- **Roll**: volumen diario, desempate por open interest, fallback a fechas oficiales de CME (cláusula 5 de la enmienda v2.1). `roll_rule_id` declarado y hasheado.
- **Cuarentena**: sesiones con cobertura de minutos activos anómala se listan en `quarantine` y se excluyen del universo con motivo escrito. No se borran silenciosamente.

---

## 3. Unidad de análisis y estimand

- **Unidad**: ventana con cutoff, identificada por `session_key = instrument|contract|session_date` y `cutoff_ns`.
- **Grilla de cutoffs**: 60 s → 1.380 ventanas por sesión. Declarada como `cutoff_policy_id = grid_60s_v1_PREREGISTERED`. Las grillas de 30 s y 10 s quedan explícitamente fuera de este pre-registro (554.760 y 1.664.280 ventanas en 201 sesiones: no entran en el presupuesto).
- **Estimand primario**: triple barrera con horizonte fijo simétrico, medido como MFE/MAE dentro del horizonte. Idéntico para el caso real y su contrafactual.
- **Invariantes de causalidad, chequeados como gate y no como comentario**: `available_at_ns ≤ cutoff_ns`, `bar_end_ns ≤ cutoff_ns`, `target_start_ns > cutoff_ns`, `label_horizon_ns = target_end_ns − target_start_ns`.

---

## 4. Normalización

- **Estacionalidad intradiaria**: Flexible Fourier Form (Andersen–Bollerslev) sobre el reloj de negocio de la sesión, ajustada **sólo con datos de entrenamiento de cada fold**.
- **Escala**: $W = P \cdot V \cdot \sigma$ como referencia de invarianza entre activos (Kyle–Obizhaeva), para que ES y MBT no se comparen en unidades incomparables.
- **Prohibido**: cualquier estadístico de normalización calculado sobre el conjunto completo, incluido el tramo de test de un fold. Es la vía más común de leak en competencias de series financieras y se chequea explícitamente.

---

## 5. Validación

- **Externa**: walk-forward, 5 folds, 20 sesiones de test cada uno, con purga y embargo. Roles por fila: `train, test, purged, embargoed, excluded`.
- **Interna**: 3 folds expanding dentro de cada train externo. Toda selección de especificación ocurre **sólo** con folds internos.
- **Agrupación**: por `market_session_key = instrument_root|session_date`. Ninguna sesión calendaria puede estar simultáneamente en train y test de un mismo fold, ni siquiera vía otro contrato del mismo subyacente.
- **Integridad de folds**: `fold_integrity_report.json` con solapamientos verificados a nivel de fila, no de fecha.

---

## 6. Múltiples pruebas

La grilla completa de la Iteración 3 tiene **9.216 celdas** (`sd_ref` × `K` × `caliper` × `ventana_min` × `pooling` × `estimador` × `ponderación`). No se corre completa: se corre el punto central, un factor por vez, y una **muestra pre-registrada de ~500 celdas** con semilla declarada.

Corrección obligatoria, en este orden:

1. **CPCV apilada** para obtener la distribución de performance fuera de muestra.
2. **PBO** (probability of backtest overfitting, CSCV) sobre esa distribución.
3. **DSR** (deflated Sharpe ratio) usando el **N efectivo** de pruebas, no el N nominal.
4. **Romano–Wolf** con bootstrap por bloques para el familywise error de los contrastes reportados.

Anclaje de costo medido (F2.1 smoke: 1 archivo, 13 sesiones, 987 zonas, 7.790 comparaciones en 3,79 s): ~500 celdas ≈ 8 h en 1 core / ≈ 2 h en 4 cores; la grilla completa ≈ 154 h / 38 h. Los 4 cores de Kaggle y el techo de 12 h por sesión son la restricción dura que justifica la muestra.

---

## 7. Regla de decisión (congelada antes de ver outcomes)

| Veredicto | Condición |
|---|---|
| `PROMOTE_RESTRICTED` | efecto estable en los 5 folds externos, PBO bajo el umbral declarado, DSR positivo con N efectivo, y Romano–Wolf sobrevive |
| `REFUTED` | el efecto no aparece o cambia de signo entre folds |
| `UNSTABLE` | aparece pero no sobrevive la corrección por múltiples pruebas |
| `DATA_INSUFFICIENT` | el universo sellado no alcanza el mínimo de sesiones declarado |
| `ABSTAIN_CAPACITY` | algún presupuesto técnico se excede |

Los umbrales numéricos concretos de PBO y DSR se fijan en el congelamiento, no ahora, y quedan escritos antes de la primera corrida formal.

---

## 8. Artefactos obligatorios por corrida

`contract_validation_report.json`, `resource_usage_report.json`, `calendar_and_roll_report.json`, `fold_integrity_report.json`, `oof_predictions.parquet`, `metrics_by_session.parquet`, `metrics_by_fold.parquet`, `candidate_ledger.parquet`, `run_manifest.json`.

Cada uno con su hash en el manifiesto, y el manifiesto con `manifest_sha256` propio.

---

## 9. Decisión de costo pendiente: Gaps2 sobre el universo completo

`Gaps2` sobre 1.078.414.656 ticks es del orden de **168 h single-core**. Tres caminos, ninguno elegido todavía:

1. **Shard + resume** por contrato con checkpoints (no reduce el costo total; lo hace factible en sesiones de 12 h).
2. **Numba**, con **re-certificación de paridad byte a byte contra el oráculo NT8** antes de usar un solo resultado. Sin re-certificación, no se usa.
3. **Submuestra estratificada pre-registrada** de contratos y sesiones, declarada antes de correr.

La decisión entra a este documento antes de congelarlo.

---

## 10. Qué falta para congelar

1. Cotejar con los **24 tests adversariales** y el **plan de trabajo de 25 ítems** del contrato (secciones aún no auditadas línea por línea).
2. Ratificar la enmienda v2.1.
3. Tener un dataset `research` que pase G1–G4 del notebook 00.
4. Fijar umbrales numéricos de PBO y DSR.
5. Elegir el camino de Gaps2.
6. Correr `02_capacity_benchmark` y **medir** RAM, runtime y tamaños en vez de estimarlos.
