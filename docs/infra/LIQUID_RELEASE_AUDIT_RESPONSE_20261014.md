# Respuesta a la auditoría independiente de la release líquida (2026-10-14)

Auditoría: `docs/infra/LIQUID_RELEASE_INDEPENDENT_AUDIT_20261014.md` (rama `feat/research-ops-supervisor-mvp`, commit `2ae9e23`).
Productor auditado: `705229bc`. Corrección: commit `0f68fe28` (rama `data/liquid-release-20261014`), con 15 pruebas de regresión nuevas
(53 pruebas en `tests/data/test_liquid_release_*.py`).

**Veredicto sobre la v3 publicada: se conserva inmutable como candidata. No se aprueba para research.** Todos los defectos de
código se confirmaron reproduciéndolos con pruebas que fallaban antes del arreglo y pasan después. Se midió su impacto real.

## Estado por hallazgo
| Id | Defecto | Confirmado | Corregido | Impacto medido en la release v3 |
|---|---|---|---|---|
| LRA-01 | La existencia de un contrato en D-1 se decidía con `lo.max()` (datos posteriores a S) | sí | existencia as-of: visto con fecha ≤ D-1 y vencimiento nominal (fin del mes de entrega) no pasado | **0 sesiones o contratos seleccionados cambian** (3.854 sesiones, 14 activos). Cambian etiquetas: 22 `NO_ELIGIBLE` pasan a `UNDETERMINED` (MGC +3, MYM +6, RTY +7, 6B/6E/6J +2 c/u) |
| LRA-02 | Spread desconocido pasaba el filtro de liquidez | sí | desconocido no es elegible salvo `allow_unknown_spread` explícito | **0**: ninguna fila del censo tiene spread vacío |
| LRA-03 | `MISSING` no bloqueaba como `UNKNOWN` (latente) | sí | ambos bloquean | **0** (el productor nunca emite `MISSING`) |
| LRA-04 | El lector sólo protegía `trade_date`, no `ts_utc_ns` | sí | `preflight_footer`: ambos relojes en todos los row groups, antes de leer cualquier payload | Los 14 Parquet publicados **pasan**: ningún row group con `ts_utc_ns ≥ 2026-09-30T22:00Z` ni `trade_date ≥ 20261001` |
| LRA-05 | Integridad no era admisión; `metadata_files` sin validar | sí | `purpose` obligatorio (`audit` / `provisional_research` / `research`); `research` exige `release_approval.json` atado al SHA del manifiesto y sin atajos de hash; `metadata_files` se valida (existencia, tamaño, SHA) | La v3 pasa la validación (14 activos + 16 metadatos, 0 ausentes) |
| LRA-06 | El verificador leía el row group antes de rechazarlo | sí | `preflight_footer` es lo primero que hace `verify_asset` | Antes del arreglo la guarda llegaba tarde; la verificación posterior leyó 1.395 M de filas con **0 filas en holdout** |

Honestidad sobre LRA-04/06: el escritor ya excluía el holdout a nivel de bytes (corte en `20260930 220000` del texto) y la
verificación completa posterior no encontró ninguna fila reservada. El defecto era de **diseño de la guarda**, y la cadena de custodia
no debe depender de que el archivo ya sea limpio.

## Hallazgo adicional propio (no estaba en la auditoría)
La réplica de racimos de AVZP2 (ES, NQ, MNQ, MES) se calculó sobre la v3 candidata, no aprobada para research. Ahora está rotulada
**PROVISIONAL** en su acta y en el registro MEDIDO/NO MEDIDO, y el script declara `purpose="provisional_research"`.

## Calibración de la política (límites del auditor, medido)
`propose_policy` calibraba con toda la muestra pre-holdout. Ahora usa las primeras 80 sesiones de cada activo y es prospectiva después.
Medido: sólo **22 de 3.854 sesiones (0,6 %)** difieren entre ambas calibraciones (19 salen, 3 entran), 16 de ellas en GC.
Las sesiones de la ventana de calibración siguen siendo in-sample y está declarado en `notes`. Sigue siendo una **propuesta sin aprobar**.

## Lo que NO se resolvió (y quién lo resuelve)
- **Calendario**: sigue derivado de los datos (`cls_last` y vecinos posteriores), útil como diagnóstico retrospectivo. Necesita el calendario
  oficial por producto (Nico / CME). Hasta entonces los desconocidos no se rellenan como ceros.
- **Aprobación de política de liquidez y licencia**: pendiente de Nico. Nada de esto autoriza P&L ni promoción.
- **Exports faltantes** (P0/P1): pendiente de los exports de Nico (`docs/infra/MISSING_EXPORTS_20261014.md`).
- **Procedencia del build v3**: el manifiesto v3 declaraba `tree_dirty_at_finalize=true` (commit `1ea3e2a1`). La v4 se construye desde un
  árbol limpio en `0f68fe28` y lo registra.
- **Huso horario / reloj del feed**: la evidencia sigue siendo empírica contra el horario; falta atestación independiente (logs NT8).
- **Auditoría de payload dentro de Kaggle** que el auditor no pudo completar: pendiente. Lo hecho hasta acá es verificación local
  por SHA-256 de los 14 Parquet y control de footers; no sustituye una auditoría independiente de contenido.
- Matriz rectangular contrato × sesión de captura, grilla de quotes y semántica de agresor: sin cambios, siguen como límites declarados.

## Próxima versión
La v4 se reconstruye desde el commit corregido con árbol limpio. Los activos cuyo conjunto seleccionado cambia por la calibración
prospectiva se publican con su hash nuevo; los demás se comparan por SHA contra la v3 (determinismo del escritor). Ver `LIQUID_RELEASE_V4_DELTA_20261014.md`.
