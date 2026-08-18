# Mapa de `docs/`

> Una sesión nueva **no** empieza acá: empieza en `docs/CURRENT.md`. Este archivo
> sólo ordena el resto. Regla de orden del proyecto: **ningún archivo se mueve ni
> se renombra** — las citas son path + blob sha1, y mover un archivo rompe la
> cadena. El orden se hace con índices (este mapa, `CURRENT.md`,
> `notion/CATALOG.md`), no con mudanzas.

## La cadena de entrada

| Capa | Qué es | Archivo |
|---|---|---|
| L0 | Estado vivo, una página, con gate | `CURRENT.md` |
| L1 | Board de decisiones | `../PENDIENTE.md` |
| L1 | Contrato Notion ↔ repo | `TRACEABILITY.md` |
| L2 | Canal y auditorías | `audits/` |
| L2 | Research: hipótesis y mediciones | `research/` |
| L3 | Catálogo Notion ↔ repo | `notion/CATALOG.md` |
| L4 | Notion (el timbre) | fuera del repo |

## Subdirectorios

| Dir | Contenido |
|---|---|
| `audits/` | Canal Opus ↔ Auditor (`CANAL_AUDITOR.md` = índice, entradas 001→023), auditorías |
| `research/` | Hipótesis (H-Z2A v1→v4 + manifiesto), censo, paridades, programas, handoffs |
| `notion/` | `CATALOG.md` + README del catálogo |
| `amendments/` | Enmiendas de contratos (G2-A1 y otras) |
| `bridge/` | Docs del puente NT8 ↔ Python |
| `campaigns/` | Manifiestos de campaña |
| `foundation/` | Etapa fundacional |
| `incidents/` | Incidentes (P0 y otros) |
| `parity_coverage/` | Cobertura de paridad |
| `predictions/` | Predicciones pre-registradas |
| `referencias/` | Material de referencia |
| `spike_in/` | Spike-in y enmiendas |
| `transferencias/` | Transferencias entre máquinas |
| `validation/` | Contratos de validación |

## La raíz de `docs/` (dos eras, sin mezclar)

**Vivos hoy:** los de la cadena de entrada (arriba) más los contratos y referentes
estables que el board cita: `NORTH_STAR.md`, `DECISIONES_2026-08-15.md`,
`PLAN_RUTA_A_UNA_CUENTA_2026-08-18.md`, `edge_validation_contract.md`,
`promotion_registry.md`, `kernel_contract.md`, `nt8_bridge.md`,
`nt8_indicator_parity_contract.md`, `holdout_access_log.md`, y los manifiestos de
datos (`datos_manifiesto.json`, `oraculos_manifiesto.json`).

**Etapa forense (julio → 10-ago), archivo:** los `ESTADO_*`, `REPORTE_*`,
`*_RESULTADO_2026-08-10.md`, `P0.*`, `P2_*`, `SCRATCHPAD_*`, `MIGRACION_*`,
`REVISION_CLON_*`, `HANDOFF_DESKTOP_SYNC_*`, `SESION_2026-08-04_*` y afines. Se
conservan porque la historia es evidencia, pero **no describen el estado vivo** —
si algo de ahí contradice a `CURRENT.md`, manda `CURRENT.md`.

## Huecos conocidos (declarados, no escondidos)

Sin respaldo en el repo: «Handoff · Sesión Claude (al 14-ago)», «Orden de trabajo
15-ago» y los 12 snapshots de texto del zip del 16-ago. Detalle en
`notion/CATALOG.md` § Respaldo.
