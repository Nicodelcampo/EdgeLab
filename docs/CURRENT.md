# CURRENT — empezar acá

> Estado operativo remoto al **2026-08-28 05:04 UTC**.  
> Punto de entrada: `AUDITOR_START_HERE.md`.

**Base de integración vigente:** `foundation/f0b-compatibility-probe@8ebda7840bc3f0a7e39f3561db75a2c9090fd55f`  
**Baseline histórico:** `main@cde6d93a75240f550db1fc3b96ca90605ca967c8`  
**Registro de ramas:** `docs/BRANCH_REGISTRY_2026-08-28.md`  
**Mapa de campañas:** `docs/PROJECT_STATE_2026-08-28.md`

## Vector operativo

```text
REMOTE_BRANCHES                         = 44
PROTECTED_BRANCHES                      = 0
OPEN_PULL_REQUESTS                      = 12
HOLDOUT_2026_07_01_TO_2026_12_31       = CLOSED_FOR_DESIGN
GLOBAL_OUTCOME_EXPOSURE                 = YES, PREEXISTING
MAIN_IS_CURRENT_INTEGRATION             = false
FOUNDATION_IS_INTEGRATION_BASE          = true
BRANCH_DELETION_AUTHORIZED              = false
MERGE_AUTHORIZED_BY_THIS_DOCUMENT       = false
```

## Líneas activas

### BT2A

- PR #15: contrato P2-A congelable, base de la cadena posterior.
- PR #16: resultado completo P2-A V1-R1; outcomes ya abiertos; no confirmatorio.
- PR #18: protocolo económico P2-B, draft y separado de la ejecución.
- PR #20: heterogeneidad horaria post-selección de GC, draft.

Estado de PR #20 al corte:

```text
HEAD                    = 56717b0d5bcb8691fbfe30f8d2478ec91cb859fc
CONTRACT_CHECK          = PASS
PYTEST_CHECKS           = FAIL / FAIL
READY_TO_FREEZE         = NO
READY_TO_EXECUTE        = NO
```

Bloqueador de integridad: la política Camino B valida schema, número de filas y conteos globales del Parquet, pero todavía no prueba que sus filas sean lógicamente idénticas a las de los 234 checkpoints.

### AVolClusterPOI

- PR #19: protocolo fail-closed de localización/compresión y dirección condicionada con BigTrap.
- Rama `research/avolcluster-nq-microticks-v1-20260828`:
  - NQ, 234 sesiones pre-holdout;
  - sweep target-free de 378 configuraciones;
  - primera configuración: `tick_120_W5_M20_C4_P950`;
  - 5.876 zonas OFF_PRICE, 25,11 por sesión, 1,09 por hora, cobertura 99,6%;
  - no ejecutó expansión, first passage, MFE/MAE, P&L ni Gate 1.

`120 ticks` es resolución de barra. Con `window_bars=5`, el bloque nominal agrega 600 ticks. No llamar “resolución ideal” sin separar efecto de barra y tamaño total del bloque.

### Infraestructura

- PR #17: coordinate store target-free de cuatro indicadores.
- `research/event-store-pit`: módulo PIT aislado.
- `research/gate-regime-context`: cimiento ejecutable, no evidencia operativa.

## Estado epistemológico obligatorio

```text
TARGET_FREE_SELECTION_IS_OUTCOME_EVIDENCE = false
PARITY_IS_EDGE                            = false
BACKTEST_IS_EDGE                          = false
P2A_CONFIRMATORY_ELIGIBLE                 = false
P2A_PROMOTION_ELIGIBLE                    = false
PNL_ACCESSED_IN_CLOCK_FAMILY              = false
HOLDOUT_TOUCHED_BY_CURRENT_FAMILIES       = false
```

La exposición histórica documentada sigue vigente. No escribir `OUTCOMES_NOT_OPENED` como afirmación global.

## Próximas acciones seguras

1. Corregir PR #20 para ligar Parquet ↔ checkpoints fila por fila o por payload canónico; agregar tests positivos y negativos end-to-end.
2. Diagnosticar las dos fallas generales de CI de PR #20 sin relajar contratos.
3. Para AVolClusterPOI NQ-120t, congelar primero configuración, lifecycle, primer toque y reloj causal; no abrir outcomes sin STOP.
4. Mantener cada familia en su rama; integrar sólo mediante PR revisada.
5. Actualizar este archivo y el registro de ramas cuando cambie un tip, estado de PR o firewall.

## No hacer desde este documento

- no ejecutar outcomes;
- no emitir tokens de freeze/ejecución;
- no tocar holdout;
- no borrar ramas;
- no cerrar PR históricas;
- no mover documentación ya citada;
- no reinterpretar un sweep target-free como Gate 1.

## Aporte al referente

CURRENT consolida el estado remoto real del 28-ago, hace visibles las dependencias entre PR y separa explícitamente configuración, medición, resultado y promoción.
