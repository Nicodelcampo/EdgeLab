# 01 — Gate 1 y auditoría de los procesos nocturnos

## 1. Gate 1 vigente

```text
branch = work/bt2a-gate1-all5-20260826
tip = 3e639e150bcd7b4691da3d1ba8049a33f586c217
status = COMPLETE_GATE1_ALL5_POST_OUTCOME_REPLICATION
EDGE_DECLARED = false
confirmatory_eligible = false
promotion_eligible = false
```

Muestra: 234 sesiones (`82 + 44 + 42 + 42 + 24`) de cinco contratos GC.

```text
K_ABS - N_RAND
+4.837606837606837
IC95 [+3.355594159773872, +6.320101319544505]

K_ABS - K_ABS_SHUFFLE
+1.7393162393162394
IC95 [+0.17462476220740109, +3.306348788286751]

K_ABS - K_BT2
+0.10042735042735043
IC95 [-3.9256103028766414, +4.160450226718588]
```

Estimando:

```text
d_hat = mediana(MFE_ticks) - mediana(MAE_ticks)
```

Interpretación vinculante: K_ABS cambia la asimetría del recorrido frente a los dos
nulos especificados; no establece el orden del camino, P&L, costos ni superioridad
frente a BT2.

## 2. Material de Antigravity auditado

Rama:

```text
work/futures-l2-context-foundation-20260825
0a1283f97a0ccee2802bd77617e4c0abbdc3290a
```

Commits:

```text
ced33dd4235da2882f5e334c87c84b7f3249dc7d  extracción L2
070af84357d659e3862446c762497755de301456  Event Store all5
0a1283f97a0ccee2802bd77617e4c0abbdc3290a  progreso sweep 190 parciales
```

Se auditó el código y lo efectivamente versionado. Los directorios `E:\DatosNT8` no
están en Git y requieren la réplica local indicada en `CLAUDE_CODE_LOCAL_AUDIT.md`.

## 3. Proceso 1 — extracción y HMM L2

### Lo que sí está respaldado

- `build_l2_gate_contexts.py` existe y ejecuta la ruta causal L1/L2.
- Verifica los Parquets contra manifests de conversión.
- Reconstruye features, entrena HMM3 sólo con sesiones train y etiqueta evaluación con
  filtrado forward-only.
- Escribe localmente features por sesión, labels, modelo, reporte target-free y
  `run_manifest.json`.
- El proceso nocturno registró exit code 0 antes de generar el reporte.
- La ruta no importa outcomes de Gate 1.

### Lo que no está respaldado por el commit

El commit `ced33dd` sólo agrega un reporte de siete líneas y dos scripts. No versiona:

```text
run_manifest.json
gate_l2_context_model.json
gate_l2_target_free_report.json
gate_l2_context_labels.parquet
hashes de features/labels/modelo
conteos por estado
cobertura, persistencia y flip rate
```

La frase “69,2 millones de eventos procesados” no aparece derivada en el reporte. Puede
ser el total de filas L1/L2 de entrada, pero no es una métrica auditable desde Git.

### Debilidad de procedencia

El master invocó la extracción con:

```text
--allow-dirty
```

Y los propios scripts `run_overnight_master.py` y `build_event_store_all5.py` fueron
commiteados después de esa tarea. Por lo tanto, la corrida se permitió sobre un árbol
sucio. El manifiesto local debería registrar `dirty_start/dirty_end`; hasta leerlo no
corresponde llamarla corrida formal hash-qualified.

### Veredicto

```text
EXECUTION_PLAUSIBLE = true
TARGET_FREE_BY_CODE = true
REAL_EXTRACTION_CLAIMED = true
FORMAL_EVIDENCE_COMPLETE = false
FORMAL_EXTRACTION_VERIFIED = false
```

## 4. Proceso 2 — Event Store all5

### Conteos publicados

```text
K_ABS = 18.679
K_BT2 = 5.870
total = 24.549
```

Gate 1, después de selección de sesiones, fill y elegibilidad de horizonte, contiene:

```text
K_ABS = 16.940
K_BT2 = 5.262
total = 22.202
```

Diferencias:

| Contrato | Event Store K_ABS − Gate 1 | Event Store BT2 − Gate 1 |
|---|---:|---:|
| GC 12-25 | +35 | +12 |
| GC 02-26 | +171 | +64 |
| GC 04-26 | +307 | +124 |
| GC 06-26 | +148 | +64 |
| GC 08-26 | +1.078 | +344 |
| **Total** | **+1.739** | **+608** |

La diferencia no prueba por sí sola un bug: el Event Store procesa el contrato entero,
mientras Gate 1 usa una registry de sesiones y elegibilidad. Sí prueba que no son la
misma población y que el store no puede sustituir los checkpoints de Gate 1 sin una
reconciliación por sesión/evento.

### Hallazgos de código

1. Usa `edgelab.bridge.*`, no el runtime congelado y corregido
   `edgelab/research/all5_runtime/*` de Gate 1.
2. No verifica hashes de inputs, commit de código ni hashes de outputs.
3. Procesa todas las filas de cada contrato, no la registry all5 de 234 sesiones.
4. Asigna fill con `min(idx + 1, n_ticks - 1)`; no rechaza el último tick ni cruces de
   sesión.
5. No aplica la elegibilidad de horizonte de Gate 1.
6. Captura excepciones de HFTZones2/VolTicksPOC2 y aun así puede terminar con exit 0.
7. El reporte final sólo publica BT2A y BT2; no demuestra que los otros dos kernels
   hayan corrido correctamente.
8. La afirmación “0 retrocesos temporales” no está acompañada por una aserción o
   métrica; ordenar el DataFrame al final no verifica la causalidad de origen.
9. No hay `event_id`, control de duplicados ni validación de unicidad.
10. El manifiesto local no se versionó.

### Veredicto

```text
RAW_EVENT_INVENTORY = usable_after_local_audit
CANONICAL_GATE1_EVENT_STORE = false
P2_INPUT_AUTHORIZED = false
```

Debe reconstruirse desde el runtime exacto de Gate 1 o reconciliarse 1:1 contra él.

## 5. Proceso 3 — sweep target-free de 99 configuraciones

### Lo que sí está respaldado por código

- No calcula MFE, MAE, retornos, P&L ni hit-rate.
- Las features PIT usan únicamente datos `<= t0` y verifican
  `feature_available_at_ns <= event_time_ns`.
- Los parciales registran input hash, config id y code commit.
- La finalización exige matriz completa y falla ante mezcla de commits.
- El split sellado no aporta métricas.

La etiqueta target-free es razonable por inspección de código, aunque los 190 archivos
locales todavía deben verificarse.

### Alcance real

El sweep no usa la nueva muestra all5 de 234 sesiones. Su contrato usa:

```text
4 contratos = GC 02-26, GC 04-26, GC 06-26, GC 08-26
universo = 152 sesiones
métricas = 133 sesiones Puerta 1 antigua
GC 12-25 = ausente
inputs = *.Last.txt, no los cinco Parquets canónicos all5
```

Progreso declarado:

```text
GC 02-26 = 99/99
GC 04-26 = 91/99
GC 06-26 = 0/99
GC 08-26 = 0/99
190/396 = 48,0 %
```

### El problema de `--resume`

La tarea comenzó después del commit `070af843...`; los parciales deberían registrar
ese `code_commit`. Después se creó `0a1283f...` para publicar el progreso. El runner
sólo salta un parcial cuando:

```text
partial.code_commit == HEAD actual
```

Por eso ejecutar el comando publicado desde `0a1283f` probablemente recompute los 190
parciales en vez de continuar. Antes de reanudar hay que leer los `code_commit` reales
y elegir una de dos rutas:

1. volver exactamente al commit de los parciales y completar allí; o
2. invalidar/recomputar todo bajo un nuevo commit congelado.

No se deben relajar los chequeos para “salvar” parciales.

### Veredicto

```text
TARGET_FREE_DESIGN = supported
LOCAL_PARTIAL_COUNT = claimed_not_versioned
ALL5_RELEVANCE = indirect_only
RESUME_FROM_CURRENT_TIP = not_authorized
```

## 6. Debilidades del orquestador nocturno

- `git_commit_and_push()` no comprueba los return codes antes de imprimir “Push
  completado con éxito”.
- Stagea todo `docs/`, `specs/` y `tools/`, incluidos cambios no relacionados.
- La tarea L2 permite árbol sucio.
- El mensaje final dice “todos los procesos ejecutados” aunque el sweep haya devuelto
  pausa/error.
- Los reportes resumen no se derivan de los manifests locales ni sellan sus hashes.

Los commits existentes prueban que algo fue publicado, pero el master no constituye un
registro formal de ejecución.

## 7. Cómo refuerza cada gate

### Gate 1

- Conservar el resultado all5 sin reescribirlo.
- Usar el sweep sólo como sensibilidad target-free del detector.
- Reconciliar Event Store contra los 22.202 eventos Gate 1 elegibles.
- Prohibir que el Event Store bruto cambie retrospectivamente la población primaria.

### Puerta 2

- Construir first-passage desde los eventos Gate 1, no desde el store provisional.
- Headline congelado como primary.
- Las 99 configs son sensibilidad; no cruzar `99 × 16` y elegir el máximo.
- Aplicar el shell G2 sólo después de producir ejecución neta.

### Puerta L2

- Recuperar y auditar el paquete local de la extracción.
- Mantener el HMM target-free y forward-only.
- Exigir captura mixta con `source_row` común para el join.
- El piloto de 5 sesiones evaluation no satisface 40 sesiones por celda.
- Contexto primary sólo sobre la configuración headline; el sweep no crea 99 trials
  contextuales.
