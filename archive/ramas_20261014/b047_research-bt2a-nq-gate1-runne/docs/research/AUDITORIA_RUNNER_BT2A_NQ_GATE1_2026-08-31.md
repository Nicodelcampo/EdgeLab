# Auditoría del runner BT2A NQ Gate 1 — veredicto: NOT READY (2026-08-31)

**Auditor:** Notion AI. **Objeto:** rama `research/bt2a-nq-gate1-runner-impl-v1-20260831`,
tip `52cbe45` (implementación `cd33a15` + pin). **Autoría:** Antigravity, bajo token 3.

## Lo verificado que PASA

- Estructura de la rama: `cd33a15` cuelga de `4044e823` (HEAD con el freeze), agrega
  exactamente 4 archivos nuevos, no modifica ningún spec congelado. Hashes de los 3
  specs verificados por Antigravity contra los pins vigentes: correctos.
- Suite reproducida por el auditor en sandbox propio (réplica byte-verificada de la
  rama): **76/76 PASS, 0 fallos** — el número reportado se reproduce.
- Motor de celdas (`bt2a_nq_gate1_outcomes.py`) y primitivas GC reutilizadas sin
  modificación, como mandaba el contrato.

## El bug que bloquea la corrida (demostrado, no inferido)

`decide_gate1_outcome` (edgelab/research/bt2a_nq_gate1_runner.py) lee por celda las
claves `mean_contrast` y `ci_lower`. El pipeline real (`compute_family` →
`compute_cell_contrast` → `wild_cluster_test`) emite `point`, `lower`, `upper`,
`p_two_sided`, `p_holm_16`. Esas claves no existen en la salida real.

Demostración corrida por el auditor (sandbox, 2026-08-31 ~01:25 ART): efecto plantado
de 8 ticks en las 16 celdas, 40 sesiones, ruido 0.5 → `p_holm_16 = 0.0319`,
`point = 7.82`, `lower = 7.61` → `decide_gate1_outcome` devuelve
**BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM**. Con la salida real del pipeline, la regla
de decisión **nunca puede declarar SUPPORTED**: falla cerrada (no declara edges
falsos), pero un Gate 1 con efecto real saldría "sin mecanismo". El test sintético
del caso SUPPORTED pasa solo porque alimenta las claves mock (`mean_contrast`,
`ci_lower`) que el pipeline nunca produce — testea un esquema que no existe.

## Hallazgos secundarios (por lectura de código, archivo citado)

1. `tools/run_bt2a_nq_gate1_outcomes.py`: N_RAND crea anchors con `direction=1`
   fijo. El motor GC evalúa el anchor apareado con la dirección del evento K_ABS que
   reemplaza (`event_dir`). El nulo no queda apareado en dirección.
2. `bt2a_nq_gate1_runner.py::sample_nrand_strata_indices`: el pool incluye las
   posiciones de los propios eventos K_ABS y el muestreo no excluye el anchor
   (no hay equivalente de `_sample_without_own`). La regla pool-1>=n existía justo
   para hacer posible esa exclusión.
3. `verify_input_artifact(spec_path, sha256_file(spec_path), ...)`: chequeo vacuo —
   compara el spec contra su propio hash recién computado, no contra el pin
   `5c5857a5...`. Un spec modificado pasaría.
4. El parseo de K_BT2 lee `configurations → contracts → coordinates` del resultado
   V2; ese archivo contiene filas de resumen bajo `results` (así lo lee el preflight
   del repo), no coordenadas. K_BT2 quedaría vacío en silencio (hay guarda `.empty`)
   y la familia secundaria moriría en `compute_cell_contrast`. Además el propio spec
   declara pendiente el staging físico del artefacto BT2 bajo `--bt2-artifact-dir`.
5. `notebooks/kaggle/bt2a_nq_gate1_16cell_runner.py`: no pasa por el sobre de
   ejecución congelada (`edgelab.kaggle.execution.require_authorized`), nunca corre
   el preflight físico del repo (`preflight_bt2a_nq_gate1.py --preflight-only`), el
   gate del token 4 es una comparación de strings, y `event_store_path` apunta a
   `specs/bt2a_nq_creation_event_store_manifest.json`, que no existe en el repo.
6. Sin chequeo positivo de holdout: la attestation escribe `HOLDOUT_TOUCHED=False`
   pero ningún código verifica `ts_ns < 1782856800000000000`. Escrito, no medido.
7. El paralelismo vive dentro de la herramienta (threads in-process sobre el
   pipeline), no en el lanzador como manda
   `KAGGLE_LAUNCHER_PARALLELISM_POLICY_V1_2026-08-30.md` (thread pool DE
   SUBPROCESOS, en el launcher).
8. Cobertura: `effective_sessions_available` cuenta sesiones con algún stat, no
   sesiones elegibles en ambos brazos por celda.

## Veredicto

Token 3 cumplido en forma (rama limpia, tests verdes, motor reusado). Pero la corrida
bajo token 4 queda **bloqueada** hasta, como mínimo: (a) arreglar el mapeo de claves
de la regla de decisión y agregar un test de integración que alimente
`decide_gate1_outcome` con la salida REAL de `compute_family`; (b) dirección del
anchor N_RAND y exclusión del propio anchor; (c) pin real del spec en el CLI;
(d) staging y parseo real del artefacto K_BT2; (e) la corrida pasa por el sobre de
ejecución congelada + preflight físico, no por un string compare.
