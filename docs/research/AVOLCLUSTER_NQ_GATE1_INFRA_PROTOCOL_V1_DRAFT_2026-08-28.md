# aVolClusterPOI NQ-120t — infraestructura de Gate 1 V1 (borrador fail-closed)

**Estado:** `DRAFT_PREAUTHORIZATION_FAIL_CLOSED`  
**Rama:** `research/avolcluster-nq-gate1-infra-v1-20260828`  
**Base:** `research/avolcluster-nq-microticks-v1-20260828@3961b67d80cd62aa6adab101e79739db3bc0005b`  
**Fecha:** 2026-08-28

## Alcance implementado

1. contrato genérico de filas canónicas tipadas;
2. identidad lógica independiente de bytes físicos de Parquet;
3. equivalencia 1:1 checkpoints ↔ Parquet;
4. schema específico `ZONE_CREATED` para NQ-120t;
5. registries congelados de 234 sesiones y cinco inputs con SHA-256;
6. builder determinista de la configuración única seleccionada;
7. checkpoints atómicos por contract-session;
8. snapshot hash-bound de `SessionProfile` y resume de prefijo contiguo;
9. finalización que exige 234 checkpoints, 5.876 eventos y cobertura de 233 sesiones;
10. tests adversariales y workflow contractual dedicado.

La implementación está presente pero permanece inejecutable con datos reales porque la spec sigue en borrador y todos los tokens están desautorizados.

## Configuración target-free vinculada

```text
config_id               = tick_120_W5_M20_C4_P950
instrument              = NQ
tick_size               = 0.25
tick_bar_size           = 120
window_bars             = 5
nominal_ticks_per_block = 600
median_multiplier       = 2.0
max_gap_ticks           = 1
min_cluster_ticks       = 4
lookback_sessions       = 20
detection_percentile    = 95.0
min_samples_per_bucket  = 10
```

Resultado target-free observado:

```text
contract-sessions                = 234
OFF_PRICE zones                  = 5.876
contract-sessions with OFF_PRICE = 233
coverage                         = 99,6%
zones/session                    = 25,11
zones/hour (denominador 23h)     = 1,09
mean width                       = 14,8 ticks
p95 width                        = 26 ticks
```

La selección utilizó densidad, cobertura y ancho. No prueba información predictiva, compresión, dirección ni edge. `120t × 5 barras = 600 ticks` es el bloque nominal; no prueba que 120t sea óptimo aisladamente.

## Inputs vinculados

El builder exige byte-size y SHA-256 exactos del registry versionado:

| Contrato | Filas | SHA-256 |
|---|---:|---|
| NQ 09-25 | 13.624.675 | `b0ea15f34ffd53d6eb35a666e511da3f605a26b653d9e3b3d1b64408544f839c` |
| NQ 12-25 | 34.264.511 | `6e0cea584fbe7d50ddb4cf53a25b29074092b7c62bb1e24749cb96472d65451c` |
| NQ 03-26 | 30.825.016 | `02d4eebcd04aad981f0567e7837fc89e1125aecf14192fecc9275b4beb1e396c` |
| NQ 06-26 | 34.203.535 | `3de249b9b8d810834376fa4c66708b73fdb2b6c1676fbfdc00c0f8373b5358f9` |
| NQ 09-26 | 14.972.883 | `a1abae00913c1fc8d2ba3a25287f3ee1b0fa3f671c667104b2aee132f50bf884` |

## Relojes separados

### A — creación de zona

Implementado. El evento sólo contiene geometría e información disponible al cierre del bloque detector. `availability_ts_utc_ns = created_ts_utc_ns + 1` representa la frontera causal exclusiva; no inventa un tick de mercado. La barra de creación no es elegible como toque.

### B — lifecycle / first touch

No implementado. Requiere una spec separada para persistencia, invalidación, primer toque, un toque por zona, colapso de episodios y clock de decisión.

### C — outcomes

Cerrado. Incluye expansión posterior, MFE, MAE, first passage, retornos y P&L.

## Checkpoints y resume

- un checkpoint JSON por contract-session;
- orden exacto del registry de 234 sesiones;
- sólo se acepta un prefijo contiguo;
- cada checkpoint liga spec payload, source SHA-256, commit, sesión y ordinal;
- `SessionProfile` se persiste después de `commit()` con hash propio;
- cualquier hueco, mutación o cambio de commit aborta;
- la finalización relee y valida los 234 checkpoints antes de escribir Parquet.

## Preflights permitidos

```powershell
python tools/validate_avolcluster_nq_zone_store.py `
  --preflight-only `
  --expected-commit REVIEWED_HEAD_SHA

python tools/build_avolcluster_nq_zone_store.py `
  --preflight-only `
  --expected-commit REVIEWED_HEAD_SHA
```

Mientras la spec sea borrador, deben devolver preparación no ejecutable:

```text
status                            = DRAFT_BUILDER_PREPARED
run_all_authorized                = false
ready_for_first_touch_or_outcomes = false
future_price_path_accessed        = false
pnl_accessed                      = false
holdout_touched                   = false
```

## Comandos futuros — no autorizados bajo esta revisión

Los siguientes modos existen para revisión de código, pero abortan antes de leer datos mientras la spec no esté congelada y los tokens no estén habilitados:

```powershell
python tools/build_avolcluster_nq_zone_store.py --run-all ...
python tools/build_avolcluster_nq_zone_store.py --finalize ...
python tools/validate_avolcluster_nq_zone_store.py --validate-artifacts ...
```

No deben ejecutarse ni completarse los tokens por inferencia.

## Gates pendientes antes de construir artefactos reales

1. auditoría del builder y tests;
2. decidir si el run se clasifica como Python-kernel research o exige paridad NT8 NQ-120t;
3. ceremonia de freeze del Event Store de creación;
4. autorización literal separada para build y finalize;
5. reproducción exacta de las 5.876 zonas;
6. validación Parquet ↔ checkpoints e informe de integridad.

Después se diseña lifecycle/first touch. Gate 1 outcomes sigue cerrado.

## Firewalls

```text
FUTURE_PRICE_PATH_ACCESSED = false
FIRST_TOUCH_ACCESSED        = false
MFE_MAE_ACCESSED            = false
FIRST_PASSAGE_ACCESSED      = false
PNL_ACCESSED                = false
HOLDOUT_TOUCHED             = false
EDGE_DECLARED               = false
PROMOTION_ELIGIBLE          = false
```

## Aporte al referente

La configuración NQ-120t dispone ahora de registries hash-bound, builder reanudable y validación lógica reusable. La construcción real, lifecycle y outcomes continúan separados y fail-closed hasta revisión, freeze y tokens independientes.
