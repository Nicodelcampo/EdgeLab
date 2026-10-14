# Auditoria local BT2A / Gate1 L2 / event store / sweep overnight — 2026-08-26

Rama de auditoria: `work/bt2a-gate2-l2-audit-20260826`, worktree
`E:/EdgeLab_worktrees/bt2a-gate2-l2-audit-20260826`. Este documento CONSOLIDA
tres auditorias ya corridas (A: gate_l2_ctx4, B: event_store_gc_all5, C:
sweep_partials). No se recalculo ni recorrio nada nuevo para este documento.

**FALTA declarada por adelantado** (para no enterrarlo): en gate_l2_ctx4 no
existe ningun archivo de eventos crudos L1/L2, asi que el cruce
`available_source_row` vs `event_source_row` pedido en el criterio de
aceptacion **no se pudo hacer** — ver seccion A, punto 5.

## Resumen ejecutivo

- **Gate 1 L2 (contexto de mercado, GC 06-26, 13 sesiones)**: los 4 archivos
  requeridos + 13 parquets diarios estan, hasheados, y el cruce independiente
  contra `gate_l2_target_free_report.json` da EXACTO en todos los campos
  recalculables. Pero `clock_reference_resolved=false` (reloj sin resolver) y
  la exclusion de la sesion 20260618 no tiene motivo declarado en el manifest.
- **Event store GC all5 (insumo para Gate1 BT2/Absorption)**: NO hay
  equivalencia 1:1 con los CSV de Gate1 — 71 de 234 filas de sesion difieren,
  siempre con el store por ENCIMA del CSV (+78 BigTrap2Absorption, +15
  BigTrap2), y la causa raiz no se pudo aislar desde el store solo. Ademas el
  parquet de GC 08-26 tiene 1286 filas dentro de la ventana de holdout
  (2026-07-01 en adelante) — el archivo crudo no esta recortado, aunque el
  filtro de las 234 sesiones de Gate1 si respeta la frontera.
- **Sweep overnight bt2a (99 configs x 4 contratos)**: 190/396 pares
  presentes, faltan 206 (los 99x2 de GC_06-26/GC_08-26 completos + 8 pares
  sueltos de GC_04-26). El `code_commit` de los 190 partials
  (`ced33dd4235d...`) NO es HEAD de `foundation` ni del worktree de auditoria
  — vive solo en una rama remota sin mergear un commit por delante de
  `foundation`. Por regla de procedencia, **--resume ahora mismo recomputaria
  los 190**, no los reutiliza.

## Tabla de veredictos

| Veredicto | Valor | Fuente |
|---|---|---|
| `FORMAL_EXTRACTION_VERIFIED_L2` | **true** | A: `archivos_esperados_faltantes=[]` (17/17 presentes) Y `cruce_vs_target_free_report` = coincide exacto en todos los campos recalculados |
| `CANONICAL_GATE1_EVENT_STORE` | **false** | B: `equivalencia_1a1_con_gate1=false` (71/234 filas de sesion difieren, store siempre >= csv) |
| `RESUME_SAFE_SWEEP` | **false** | C: `resume_safe=false` (code_commit de los partials no es ancestro/HEAD de foundation actual) |
| `ANY_FORBIDDEN_OUTCOME_KEY_FOUND` | **false** | C: `claves_prohibidas_encontradas=[]` (busqueda recursiva de mfe/mae/pnl/return/hit_rate/target_first/stop_first: 0 coincidencias en 190 archivos) |

## Detalle A — gate_l2_ctx4 (GC 06-26, HMM3 contexto de mercado)

**Checks (pass/fail):**

| Check | Veredicto |
|---|---|
| Archivos requeridos presentes (4 raiz + 13 features/) | PASS |
| Cruce independiente vs `gate_l2_target_free_report.json` | PASS (exacto) |
| `clock_reference_resolved` | FAIL (`false` literal en `run_manifest.json`, y columna `clock_semantics`='NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED' en las 14970 filas) |
| Outcomes cerrados / target-free | WARN — `CAMPAIGN_OUTCOMES_OPENED=false`, `EDGE_DECLARED=false`, `outcomes_accessed=false`, `outcomes_computed=false` (13/13 session_reports) estan todos en orden, pero `PREEXISTING_OUTCOME_EXPOSURE='YES'` (string literal) no tiene ninguna explicacion en el propio artefacto — no se puede cerrar este check sin causa raiz |
| Motivo declarado de `excluded_sessions` (20260618) | FAIL — no existe campo `excluded_reason` ni similar en `run_manifest.json` |
| Cruce `available_source_row` vs `event_source_row` | **NO_DERIVADO_EN_REPO / FALTA** — no hay ningun archivo de eventos crudos L1/L2 en `gate_ctx4/`, ni columna `event_source_row` en ningun parquet |
| "69,2 millones de eventos" citado literal en algun artefacto | FAIL — la cifra no aparece escrita en ningun JSON (grep negativo); SI es derivable sumando `source_rows_total` de los 13 `session_reports` = 69.229.635, que coincide exacto con `l1_rows`(17.401.308)+`l2_rows`(51.828.327) |

**Cifras exactas:**

- 17 archivos totales (`run_manifest.json` 12259B, `gate_l2_context_model.json` 5728B, `gate_l2_target_free_report.json` 2694B, `gate_l2_context_labels.parquet` 2143105B, + 13 `features/*.parquet`), todos con sha256 (campo `archivos` del JSON).
- `code_commit_start = code_commit_end = 9d1cd64f2f1847872c839b7c47ae12ed3635d35c`; `dirty_start = dirty_end = true` (arbol sucio en todo el run).
- `model_id = gate_gc_l2_hmm3_toxic_forward_v1:46bb10afdccc7fad` — coincide en `context_model_id` de las 14970 filas del parquet y en `gate_l2_context_model.json`.
- `train_sessions` (8): 20260609,20260610,20260611,20260612,20260614,20260615,20260616,20260617. `evaluation_sessions` (5): 20260619,20260621,20260622,20260623,20260624. `excluded_sessions` (1): 20260618.
- `n_labels = 14970` filas, 66 columnas. `coverage = 0.8008016032064128` (=11988/14970), identico entre `context_as_of_ok`, `feature_eligible` y `coverage` del reporte.
- Estados por minuto: calm=5377, normal=2833, toxic=2669, volatile=1109. Sesiones con ese estado presente: calm=13, normal=12 (falta en 20260619), toxic=13, volatile=13.
- `evaluation_eligible=True` en 4667 filas, 100% dentro de las 5 evaluation_sessions declaradas, 0 fuga desde train. `training_rows=7321` coincide exacto.
- Persistencia y flip rate recalculados de forma independiente: 717 rachas, media=16.719665271966527 min, mediana=6.0 min, 704 flips/11975 transiciones — coincide EXACTO con el reporte. OJO: `minute_id` tiene huecos (hasta 415 minutos), asi que ese `flip_rate=0.05878914405010439` es una fraccion de transiciones sobre la secuencia YA FILTRADA, no una tasa horaria real. La tasa horaria real recalculada con timestamps: **2.753764912966116 cambios/hora** (704 flips / 255.65 horas reales acumuladas entre minutos etiquetados).

## Detalle B — event_store_gc_all5 (insumo BT2/Absorption, 5 contratos GC)

**FALTA/OJO declarado primero:** el event store bruto de GC 08-26 tiene 22
sesiones dentro del holdout (2026-07-01 en adelante) sin recortar.

- 5 parquets + 1 manifest + spec + 5 CSV de Gate1, todos hasheados. `total_events_across_contracts=24549` — coincide exacto con la suma de filas leidas por pyarrow en los 5 archivos (9262+5671+3792+2731+3093=24549).
- Esquema identico en los 5 parquets: `ts_utc_ns, source_row, contract, session_id, indicator, direction, price_ticks, fill_ts_utc_ns, fill_source_row, fill_price_ticks, metadata_json`. `direction` en dominio {-1,1} (no strings). `indicator` en {BigTrap2Absorption, BigTrap2}, sin tercer valor.
- Duplicados: 0 en los 5 archivos (fila completa y clave `ts_utc_ns+source_row+indicator+direction`).
- Fill posterior a origen: 100% de las 24549 filas cumple `(fill_ts,fill_source_row) > (ts,source_row)` — 0 violaciones.
- Orden dentro de sesion: 972 empates (392+145+255+80+100 por contrato), 0 inversiones. Los 15 casos inspeccionados a mano son pares BigTrap2Absorption+BigTrap2 sobre el mismo tick de origen, no error de escritura.
- Cruce de sesion en fill: metrica ingenua da 223 filas fuera del rango propio, pero 0 caen dentro de la ventana de OTRA sesion — no es cruce real, es hueco posterior al ultimo evento de origen visible.
- Fills en el ultimo tick de origen disponible: 165/24549 (0.67%).
- Poblacion bruta: 85/79/78/73/64 sesiones por contrato (mucho mas que las 82/44/42/42/24 de Gate1). Filtro reconstruido da EXACTO 234/234 esperadas presentes.
- **HOLDOUT**: `GC_08-26_event_store.parquet` tiene 22 session_id >= 20260701 (20260701-20260729 y 20260817) = 1286/3093 filas (41.6%), con 970 BigTrap2Absorption + 316 BigTrap2. El filtro de las 234 sesiones de Gate1 SI respeta la frontera (window_end GC 08-26 = 20260630) — no es violacion de firewall (no hubo P&L ni seleccion), pero es riesgo operativo: el parquet crudo no esta recortado al holdout.
- **NO equivalencia 1:1 con Gate1**: 71/234 filas de sesion difieren (30.3%), siempre `event_store >= csv` (nunca al reves). Excedente agregado: +78 BigTrap2Absorption (17018 vs 16940 filtrado), +15 BigTrap2 (5277 vs 5262). Causa raiz **NO aislable** desde este store de solo lectura — `metadata_json` no trae flags de elegibilidad/dedup, solo `score/absorption_vol/trap_vol` o `kind/trap_vol` en placeholder 0.0.
- Por esto: `canonical_gate1_input = false`.

## Detalle C — sweep_partials (bt2a_sweep_overnight_20260826)

**FALTA/OJO declarado primero:** `resume_safe = false` — reanudar ahora
recomputaria los 190 partials existentes, no los reutiliza.

- `n_archivos = 190` en `partials/`: 99 GC_02-26 (completo, 99 config_id unicos) + 91 GC_04-26. **GC_06-26 y GC_08-26 estan AUSENTES por completo** (0 archivos).
- Matriz maxima 99 configs x 4 contratos = 396 pares. Presentes = 190. **Faltan 206**: 198 = 99 configs x 2 contratos ausentes (GC_06-26+GC_08-26) + 8 pares sueltos de GC_04-26 (config_id: `0667634c938874ea, 0e5acfd3481e0e4e, 395709e8d8b1c19d, 555d48039f5ebd4a, 5d08e75f7326d2ec, 69c33e40605f6a20, 9b788847b39c0ae0, c60e6a9c4e6224b8`).
- `code_commit`: un unico valor en los 190 partials → `ced33dd4235da2882f5e334c87c84b7f3249dc7d` (190/190).
- `input_sha256`: 2 valores (esperado, uno por contrato) — `53cac568a2e6...` (99 GC_02-26), `32dcde3db246...` (91 GC_04-26).
- `target_free=True` en 190/190. `outcomes_opened=False` en 190/190.
- Busqueda recursiva de `mfe/mae/pnl/return/hit_rate/target_first/stop_first` en los 190 JSON: **0 coincidencias**. `claves_prohibidas_encontradas = []`.
- Registros `event_pit` (287.555 en total): 0 violaciones de `feature_available_at_ns <= event_time_ns` — PIT-safe, con igualdad (no adelanto) en la muestra inspeccionada.
- `violaciones_pit_ordering = 0`.
- **Procedencia**: HEAD del worktree de auditoria = `5ddc5eb718f60bc925aae493203589ce5520e3fd` (rama `work/bt2a-gate2-l2-audit-20260826`, arbol limpio). HEAD de `foundation/f0b-compatibility-probe` en `E:/EdgeLab` = `7e8526e0eab0ac96af4f36dce6e20890fcf69287` (arbol limpio). El commit real de los partials (`ced33dd4235d...`) es descendiente directo de `7e8526e` (un commit encima, `feat(context): complete real 13-session GATE L2 extraction and HMM3 model`) pero vive **solo** en la rama remota `origin/work/futures-l2-context-foundation-20260825`, no mergeado a `foundation`. `ced33dd` y `5ddc5eb` son hermanos divergentes de `7e8526e`; ninguno es ancestro del otro.
- **Conclusion de resume**: dado que la regla es mismatch de `code_commit` → recompute, y `ced33dd` != HEAD de `foundation` (`7e8526e`), los 190 partials quedan con procedencia no verificada contra ese HEAD. **`--resume` ahora mismo recomputaria los 190** (`n_recomputarian_si_resume_ahora = 190`).
- Nota aparte: el spec `specs/bt2_absorption_gate1_all5_sessions_2026-08-26.json` (5 contratos, 234 sesiones) es el REGISTRO DE SESIONES de Gate1 — un objeto distinto del universo 4 contratos x 99 configs de este sweep. No confundirlos por el nombre parecido.
