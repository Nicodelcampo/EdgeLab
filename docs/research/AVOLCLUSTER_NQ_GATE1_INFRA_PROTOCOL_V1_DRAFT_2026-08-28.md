# aVolClusterPOI NQ-120t — infraestructura de Gate 1 V1 (borrador fail-closed)

**Estado:** `DRAFT_PREAUTHORIZATION_FAIL_CLOSED`  
**Rama:** `research/avolcluster-nq-gate1-infra-v1-20260828`  
**Base:** `research/avolcluster-nq-microticks-v1-20260828@3961b67d80cd62aa6adab101e79739db3bc0005b`  
**Fecha:** 2026-08-28

## Alcance de este avance

Este cambio crea la primera capa reutilizable para la corrida AVolClusterPOI:

1. contrato genérico de filas canónicas tipadas;
2. identidad lógica independiente de los bytes físicos de Parquet;
3. equivalencia 1:1 entre checkpoints y Parquet;
4. schema específico de creación de zonas NQ-120t;
5. validaciones geométricas, causales, de holdout y de procedencia;
6. preflight que permanece cerrado mientras la spec sea borrador;
7. tests adversariales y workflow contractual dedicado.

No construye todavía el Event Store real y no abre trayectorias posteriores a la creación de una zona.

## Configuración target-free vinculada

```text
config_id              = tick_120_W5_M20_C4_P950
instrument             = NQ
tick_size              = 0.25
tick_bar_size          = 120
window_bars            = 5
nominal_ticks_per_block = 600
median_multiplier      = 2.0
max_gap_ticks          = 1
min_cluster_ticks      = 4
lookback_sessions      = 20
detection_percentile   = 95.0
min_samples_per_bucket = 10
```

Resultado target-free observado:

```text
contract-sessions                 = 234
OFF_PRICE zones                   = 5,876
contract-sessions with OFF_PRICE  = 233
coverage                          = 99.6%
zones/session                     = 25.11
zones/hour (23h denominator)      = 1.09
mean width                        = 14.8 ticks
p95 width                         = 26 ticks
```

Es una selección por densidad, cobertura y ancho. No prueba información predictiva, compresión, dirección ni edge. `120t × 5 barras = 600 ticks` es el bloque nominal; no demuestra que 120t sea óptimo aisladamente.

## Separación de relojes

### Reloj A — creación, implementado en esta infraestructura

El evento `ZONE_CREATED` contiene únicamente información disponible al cierre del bloque detector. La disponibilidad se fija estrictamente después de ese cierre. La barra de creación nunca puede ser barra de toque.

### Reloj B — lifecycle/first touch, no implementado

Requiere una spec separada para:

- persistencia de zona;
- `ZONE_INVALIDATED`;
- primer tick/bar elegible de toque;
- un primer toque por zona;
- colapso de episodios simultáneos;
- clock causal de decisión.

### Reloj C — outcomes, cerrado

Incluye expansión posterior, MFE, MAE, first passage, retornos o P&L. No está autorizado por este cambio.

## Identidad lógica

Para cada fila:

1. se exigen columnas exactas y tipos finitos;
2. `event_id` se deriva de la clave natural de creación;
3. `identity_sha256` cubre todo el contenido científico de la fila;
4. las filas se ordenan por claves canónicas;
5. `event_id` e `identity_sha256` deben ser únicos;
6. el payload agregado tiene hash SHA-256 canónico;
7. el Parquet debe reconstruir exactamente las mismas filas que los checkpoints.

Diferencias de codec, metadata o row groups pueden cambiar el hash físico del Parquet sin cambiar su identidad lógica. Una mutación de una sola fila es bloqueante.

## Preflight permitido

```powershell
python tools/validate_avolcluster_nq_zone_store.py `
  --preflight-only `
  --expected-commit <REVIEWED_HEAD> `
  --output-json runs/avolcluster_nq_zone_store/preflight.json
```

El resultado esperado bajo esta revisión es:

```text
status                              = DRAFT_PREPARATION_READY
ready_for_zone_store_validation     = false
ready_for_first_touch_or_outcomes   = false
future_price_path_accessed          = false
pnl_accessed                        = false
holdout_touched                     = false
```

No existe en este borrador ningún comando autorizado para producir o validar artefactos reales.

## Próximo bloque de implementación

1. manifest SHA-256 de los cinco Parquet NQ locales;
2. builder de la configuración única seleccionada;
3. checkpoint atómico por contract-session;
4. snapshot/rehidratación de `SessionProfile` para resume determinista;
5. reproducción exacta del conteo target-free de 5.876 zonas;
6. Parquet agregado validado contra checkpoints;
7. informe de paridad NQ-120t o clasificación explícita como investigación Python-only;
8. revisión humana y ceremonia de freeze del Event Store de creación.

Sólo después se diseña y congela lifecycle/first touch. Gate 1 outcomes continúa cerrado.

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

La selección NQ-120t deja de ser sólo un ranking target-free y adquiere un contrato auditable de creación de zonas. El lifecycle y los outcomes siguen separados y bloqueados hasta tener manifest, builder, reproducción exacta, freeze y autorización independientes.
