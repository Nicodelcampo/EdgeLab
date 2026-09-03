# CURRENT — estado vivo

**Corte:** 2026-09-02  
**Rama viva:** `foundation/f0b-compatibility-probe`  
**HEAD:** resolver remoto al iniciar; el branch avanzó durante este mismo corte  
**Referente:** `docs/NORTH_STAR.md` · sha256 del cuerpo `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Línea primaria

**Certificación del régimen contractual NQ y saneamiento de la cadena aVolClusterPOI NQ.**

El scan v2 terminó técnicamente sobre 119.153.201 filas y abstuvo científicamente porque no existe evidencia aprobada de completitud. No hubo acceso a outcomes ni holdout.

## Vector de estado

```text
REMOTE_BRANCHES                         = 60
OPEN_PULL_REQUESTS                      = 17
PROTECTED_BRANCHES                      = 0
NQ_MANIFEST_V1                          = PROVISIONAL_INVALID_CALENDAR
NQ_SCAN_V2                              = ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED
NQ_CERTIFIED_ROLLS                      = 0
NQ_PROVISIONAL_ROLLS                    = 4
ROLL_SENSITIVITY_P68                    = IDENTICAL_DATES_CONTRACTS_RATIOS_6DP
NQ09_MAINTENANCE_ROOT_CAUSE             = UNRESOLVED
CME_CALENDAR                            = SOURCE_ACCESS_BLOCKED_NOT_DECISION_BLOCKED
SOURCE_CAPTURE_COMPLETENESS             = NOT_APPROVED
AVOLCLUSTERPOI_NQ_PARITY                = FAIL
EF0                                     = BLOCKED
CAMPAIGN_OUTCOMES_OPENED                = false
PREEXISTING_OUTCOME_EXPOSURE            = YES
```

## Medido: P-68

El volumen del scan v2 ya excluye la ventana de mantenimiento. No hace falta una normalización adicional de NQ 09-26 para calcular los rolls.

Sensibilidad sobre la implementación real:

| Variante | Días | Rolls |
|---|---:|---|
| weekdays | 237 | 2025-09-17, 2025-12-16, 2026-03-17, 2026-06-16 |
| weekdays menos 9 feriados | 229 | las mismas cuatro fechas |

Contratos y ratios `leader_over_current` fueron idénticos a 6 decimales: 3,396162; 1,260126; 1,125767; 2,286790.

**No medido/certificado:** completitud de fuente. La sensibilidad asume `complete_session=True` para aislar el efecto del calendario. Por eso no certifica el manifiesto.

## Bloqueos actuales

1. ~~Obtener las horas oficiales CME.~~ **RESUELTO 2026-09-02 (`4f365bf`)**: el WAF bloquea `curl` y el fetcher, pero el endpoint JSON oficial que la propia página consume (`/services/trading-hours-by-product`) responde 200 desde el origen y **sirve fechas históricas**, así que 2025 también quedó cubierto. Calendario con evidencia hasheada en `docs/research/cme_equity_index_calendar_20260902/`, valida contra el gate. Corrobora el patrón de 1140 min = early close 12:00 CT (7 de 8 early-close dentro de 0-6 min). **Pendiente**: Juneteenth 2026-06-19 (fuente ambigua vs 115.146 ticks observados), por eso corta el 18-jun.
2. Construir cobertura de fuente separada del calendario.
3. Producir evidencia de completitud aprobable.
4. Reconstruir el manifiesto y verificar formalmente los cuatro rolls.
5. Reconstruir los traces por intervalo contractual con reset total.
6. Resolver paridad/lifecycle aVolClusterPOI: 19 `GEOMETRY_DIFF`, 57 `MISSING_IN_NT8`, 48 `MISSING_IN_PYTHON`; primero corregir alineación de borde de ~3 ticks.

## NQ 09-26

Medido: 363.601 ticks y volumen 398.066 en 16:00–17:00 CT, nueve días hábiles del 17 al 30-jun. `ts_local_ns == ts_utc_ns` en todas las 6.235.464 filas. El re-corte no introdujo el fenómeno.

Inferido: plantilla NT8 distinta. Sigue sin confirmación directa y el artefacto conserva `root_cause_status=UNRESOLVED`.

Consecuencia: no afecta la señal causal del roll del 16-jun, que usa D-1. Sí afecta comparaciones crudas de volumen del 17–30 si no se excluye mantenimiento; el scan v2 ya lo excluye.

## Ramas

- `foundation/f0b-compatibility-probe`: integración.
- `audit/notion-ai-sltp-p2b-provenance-20260830`: congelada, no mergear ni borrar.
- 17 PR abiertas; varias tienen bases encadenadas o antiguas.
- Ninguna rama está protegida.
- Registro: `docs/BRANCH_REGISTRY_2026-09-02.md`.
- `research/avolcluster-nq-parity-oracle-20260901`: **mergeada a `foundation` el 2026-09-03.**
  Paridad de aVolClusterPOI v0.5 sobre NQ 06-26 120t. Los tres números miden
  poblaciones distintas y hay que citarlos con su estimand:
  - `KERNEL_PARITY_ON_EQUAL_INPUT = EXACT`: 23.339/23.339 bloques (100,00 %) —
    valida clustering/percentil/geometría **sobre input igual**, no el footprint.
  - Replay en ventana: 203/203 zonas (100,00 %); end-to-end 201/203 (99,01 %) —
    sobre **203 zonas**, ~2 % de los bloques.
  - **Partición de barras: 89,81 %** sobre las 233.601 barras del BARPROFILE
    (auditado 2026-09-03, `docs/research/avolcluster_partition_audit_20260903/`).
    El error crece monótono en la sesión: decil 0 97,27 % → decil 9 73,07 %.
  - Índice y reservas abiertas: `docs/research/PARIDAD_AVOLCLUSTERPOI_INDICE.md` (P-71).
  - Outcomes: `CAMPAIGN_OUTCOMES_OPENED = false`.
- `research/gate-regime-context`: `FOUNDATION_EXECUTABLE`, `CHECKPOINT_PENDING_REAL_DATA`, `NOT_YET_OPERATIONAL`.
- `work/crypto-context-foundation-20260824`: PR #14 draft; CI roja; no mergear.

## No tocar sin decisión explícita

- outcomes, P&L, MAE/MFE, EF0 o holdout;
- reglas de completitud o tolerancias;
- specs/splits congelados;
- ramas G2 rivales;
- borrado/cierre/merge de ramas;
- parquets, artefactos o cuarentenas publicados.

## Índices canónicos

- `PROJECT_INDEX.md`
- `AUDITOR_START_HERE.md`
- `docs/PROJECT_CHRONOLOGY_2026-09-02.md`
- `docs/BRANCH_REGISTRY_2026-09-02.md`
- `docs/OPEN_IDEAS_INDEX_2026-09-02.md`
- `PENDIENTE.md`

## Aporte al referente

CURRENT describe el bloqueo real: los rolls parecen estables, pero la certificación depende todavía de fuente oficial, cobertura y completitud aprobada.