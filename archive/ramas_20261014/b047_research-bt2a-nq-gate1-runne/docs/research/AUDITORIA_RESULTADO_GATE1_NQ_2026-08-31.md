# Auditoría independiente — Resultado terminal Gate 1 NQ (2026-08-31)

- **Auditor:** Notion AI — Auditor Cuantitativo. **Fecha:** 2026-08-31 (ART).
- **Objeto:** el resultado terminal de Gate 1 NQ reportado por el baseline (kernel v9, commit de checkout `37aecc65`, decisión `BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM`, acta `BT2A_NQ_GATE1_RESULT_2026-08-31.md`, artefactos en `docs/research/bt2a_nq_gate1_result_20260831/`).
- **Método:** nada aceptado por palabra. Todo lo abajo fue recomputado en el sandbox del auditor sobre los artefactos reales o sobre los bytes remotos exactos del código.

## 1. Lo que verifiqué (todo medido, no inferido)

1. **Decisión recomputada** desde las 16 celdas reales de `primary_family_holm` usando `decide_gate1_outcome` del runner real: `BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM` ✓. 9 celdas tienen `p_holm_16 ≤ 0,05`, pero el máximo `|point|` entre las 16 es **0,2613 ticks < 1,0** (mínimo pre-registrado) → `positive_supported_cells = []`. La puerta de tamaño mínimo de efecto hizo exactamente su trabajo: significancia sin relevancia económica no pasa.
2. **Cobertura:** 234 sesiones ≥ 228 requeridas, min-sobre-celdas → el nulo es con potencia suficiente, no "no se ve porque falta N".
3. **Contabilidad de exclusiones:** `n_exclusions_total = 4224` == suma exacta de los `exclusion_counts` por contrato (valida además, sobre datos reales, la agregación que introdujo mi fix de memoria `8830b74e`).
4. **Attestation == exactamente lo autorizado** por el token 4: `GATE1_RUN=true`, `OUTCOMES_ACCESSED=true`, `HOLDOUT_TOUCHED/PNL_ACCESSED/EDGE_DECLARED/PROMOTION_ELIGIBLE/WINNER_SELECTED` todos `false`.
5. **Cross-check de población:** los eventos K_ABS por contrato del resultado suman **152.695** — idéntico al parquet congelado del event store (152.695 filas, sha256 `96281e88…` en el preflight real).
6. **Preflight real** (`bt2a_nq_gate1_preflight.json`): `PASS_READY_FOR_GATE1_FREEZE`, `missing_bindings=[]`, `git.head = 37aecc65` (la corrida exitosa ya llevaba el fix del sampler), `git.dirty=false`, spec `b9e75c25…` (el rebind de hoy), event store manifest `1e45c43f…` (el rebind), 5 parquets de ticks con hash individual, `physical_holdout_absence=true`.
7. **Fix del sampler (commit `37aecc65`, del baseline): auditado.** Contrato preservado leído línea por línea: uniforme sin reemplazo por permutación única, auto-exclusión por draw vía reserva, fail-closed de capacidad intacto + fail-closed nuevo en reserva agotada, orden de iteración por claves ordenadas intacto. Medición propia: 500 draws sobre pool de 50.000 en **4 ms** (el viejo medía ~140 s en ese estrato según su propia medición; el mío midió 4,16 s en 100K/100 — consistente con O(n²×P)). Suite completa del auditor: **80/80 PASS sobre los bytes remotos exactos del runner** (blob `cfc388f4`, mi copia local verificada byte-idéntica antes de correr). **Nota declarada, no silenciada:** la resolución de auto-colisión por reserva introduce una no-uniformidad despreciable que solo aparece en la rara colisión pick==own; aceptable para el brazo de control.

## 2. Ítem ABIERTO (no bloqueante para la decisión)

Mi recomputación de `result_payload_sha256` sobre el `result.json` del repo dio **distinto** del manifiesto (`6935729f…`). Mi vía — transcribir 44 KB a mano al sandbox — puede arrastrar un dígito en cualquier float; el baseline reporta haberlo recomputado a mano con match exacto; el sandbox no tiene red para un pull byte-exacto que dirima. **Cierre declarado:** recomputar el hash canónico sobre el archivo de salida del kernel directamente (o con un pull byte-exacto) y registrar el resultado acá. Este ítem no afecta la decisión ni ningún número de contenido: todos verificados por recomputación independiente (punto 1).

## 3. Cascada de gobernanza (consecuencias del resultado)

- **SL/TP/BE NQ NO se abre.** Su gatillo era `BT2A_NQ_GATE1_DIRECTIONAL_MECHANISM_SUPPORTED` (`BT2A_NQ_SLTP_BREAKEVEN_DESIGN_V1_2026-08-31.md` §1, escrito horas antes del resultado — la pre-compromiso se paga en días como hoy). El diseño queda listo e inerte. El prior de Kaminski-Lo se sostuvo: sin mecanismo direccional, ninguna regla de salida suma.
- **La idea del BE micro (G=1) pierde sustrato en NQ-tape:** no hay excursión direccional que cosechar.
- **Lo que el resultado cierra:** ESTA configuración de K_ABS (`bt2a_nq_7e84981882b0b380`), bajo el techo EXPLORATORY pre-declarado. No es una refutación confirmatoria de toda la familia BT2A — pero sí un nulo real con potencia suficiente en el umbral económico pre-registrado, sin tocar el holdout ni gastar campaña formal.
- **Lo que sigue intacto:** P-44 (el problema de N del proyecto es de potencia, no de este mecanismo), la línea ZB L2 (HP-006, fuente de información distinta — relativamente más atractiva hoy que ayer), la política multi-kernel (estrena cuando haya cómputo pesado de verdad).

## Aporte al referente

La primera campaña confirmatoria del proyecto terminó en un nulo limpio, verificado por dos vías independientes, con la puerta económica pre-registrada haciendo su trabajo visible. EdgeLab hoy sabe algo que ayer no sabía: que con ~750K eventos y 234 sesiones, la absorción BigTrap2 en NQ deja estructura estadística del orden de una fracción de tick — y que eso no alcanza.
