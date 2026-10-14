# Implementación de hardening — Puerta 2 y Puerta L2

**Corte:** 2026-08-26  
**Rama activa:** `work/bt2a-gate2-l2-hardening-20260826`  
**Base documental:** `work/bt2a-gate2-l2-audit-20260826@5ddc5eb718f60bc925aae493203589ce5520e3fd`

## Alcance implementado

### Event Store canónico

`tools/build_bt2a_gate1_event_store.py` reconstruye la población exacta de Gate 1 desde el registro all5 de 234 sesiones. Aplica fill estricto, sesión CME dura y la misma elegibilidad de horizonte de Gate 1. Falla si los conteos difieren de `K_ABS=16.940` o `K_BT2=5.262`.

Una prueba real sobre `GC 08-26 / 20260630` produjo `K_ABS=65`, `K_BT2=13`, cero fills excluidos y un evento excluido por horizonte incompleto. La reconstrucción completa de 234 checkpoints sigue pendiente en la computadora con los cinco Parquet.

### Puerta 2 — P2-A first-passage

`edgelab/research/bt2a_gate2_first_passage.py` implementa first-passage causal en ticks enteros:

- `TP_FIRST`, `SL_FIRST`, `TIMEOUT`;
- barreras desde el fill;
- long/short;
- sesión dura y horizontes por ticks o reloj;
- implementación escalar y acelerada equivalentes;
- bootstrap/wild cluster por sesión y Holm.

`tools/run_bt2a_gate2_p2a.py` consume exclusivamente el Event Store reconciliado, genera las 16 celdas primary y 12 celdas clock secondary, materializa controles aleatorios/shuffle, checkpoints e inferencia. Requiere spec congelado y token explícito. No se ejecutó sobre outcomes.

### Puerta 2 — P2-B ejecución

`edgelab/research/bt2a_execution.py` reemplaza la adaptación insegura del simulador legado de 6E con un motor específico para el stream canónico:

- coordenadas nanosegundo + `source_row`;
- entrada estrictamente posterior a la señal;
- long al ask y short al bid;
- slippage adverso en entrada y salida;
- target, stop, time-stop, cierre de sesión y borde de datos;
- una posición simultánea y `first executable signal wins`;
- rechazo explícito de señales durante una posición;
- identidad exacta `net_ticks = gross_ticks - spread_ticks - slippage_ticks`;
- P&L por trade y por señal elegible;
- escenarios `ideal`, `base`, `adverso`, `severo`.

`tools/run_bt2a_gate2_p2b.py` ejecuta P2-B por sesión y finaliza por clusters de sesión. La comisión por lado, su fuente y el valor del tick son inputs obligatorios: el valor 6E no se reutiliza ni se inventa para GC. También requiere spec congelado y el token `AUTHORIZE_BT2A_P2B_POST_OUTCOME_DIAGNOSTIC`.

### Puerta L2

`edgelab/research/bt2a_gate_l2.py` implementa:

- validación física y de cobertura de labels target-free;
- estados `calm/normal/volatile/toxic` y grupos congelados;
- join estricto `available_source_row < event_source_row`, sin fallback temporal;
- chequeo de correlación contexto/ancho de zona;
- interacción directa `((K_ABS-N_RAND)|G-operable)-((K_ABS-N_RAND)|G-stress)`;
- bootstrap por sesiones y abstención por baja potencia;
- identidad manifest/model/report y rechazo de runs dirty.

`tools/validate_bt2a_gate_l2_package.py` valida inventario, hashes, commits, dirty flags, modelo, cobertura, mapping, join y mínimo de sesiones antes de permitir cualquier apertura de outcomes. Los rows marcados explícitamente `context_as_of_ok=false` pueden conservar labels nulos; no cuentan para mapping, estados ni cobertura efectiva.

## Verificaciones ejecutadas

```text
P2A_CELL_PASS
FAST_EQUALS_SCALAR_PASS
GATE_L2_DIRECT_ASSERTIONS_PASS
L2_PHYSICAL_ORDER_FAIL_CLOSED_PASS
L2_NULL_LABELS_PASS
P2B_DIRECT_ASSERTIONS_PASS
P2B_COST_MONOTONIC_PASS
python -m py_compile = PASS
```

`pytest` no está instalado en el sandbox; los tests pytest quedaron versionados para CI.

## Estado honesto

```text
P2-A = IMPLEMENTED_NOT_RUN
P2-B = IMPLEMENTED_NOT_RUN
GATE2_SPEC = PROPOSED_NOT_FROZEN
GATE_L2_VALIDATION = IMPLEMENTED
GATE_L2_EXTRACTION_EVIDENCE = PENDING_LOCAL_AUDIT
GATE_L2_SAMPLE_POWER = NOT_READY
NEW_P2_OR_L2_OUTCOMES_OPENED = false
EDGE_DECLARED = false
```

No llamar “cerrada” a Puerta 2 hasta congelar el contrato, confirmar costos GC, reconstruir 234 checkpoints y recibir autorización explícita. No llamar “cerrada” a Puerta L2 hasta validar procedencia/hashes del run local, disponer captura común L1/L2/eventos y alcanzar al menos 40 sesiones efectivas por grupo primary.

## Próximo orden de ejecución

1. Incorporar `LOCAL_AUDIT_RESULT.json/.md` de Claude Code.
2. Reconciliar/reconstruir el Event Store canónico de 234 sesiones.
3. Confirmar por fuente auditable comisión por lado y valor de tick de GC.
4. Revisar y congelar el spec; no inferir el freeze del código.
5. Sólo con autorización, ejecutar P2-A y P2-B en checkpoints separados.
6. Validar el paquete L2 con el validador fail-closed.
7. Abrir la interacción L2 únicamente si procedencia, cobertura, ancho de zona y potencia pasan.

No usar `--resume` sobre el sweep nocturno hasta adjudicar `partials.code_commit`. No se abrió PR.
