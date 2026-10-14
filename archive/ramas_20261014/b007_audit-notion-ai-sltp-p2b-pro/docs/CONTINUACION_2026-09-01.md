# CONTINUACIÓN — cambio de máquina (2026-09-01)

**Motivo:** Nico cambia de computadora; el historial local de Claude no migra. Este
archivo resume el punto de reentrada. Si contradice otro documento, mandan git, blobs y
artefactos medidos.

## Orden de lectura

1. `CLAUDE.md` y `AGENTS.md`.
2. `docs/DECISIONES_NICO_2026-08-30.md`.
3. `docs/audits/PENDIENTE_RECONCILIACION_2026-09-01.md`.
4. Board canónico: `research/avolcluster-nq-parity-oracle-20260901:PENDIENTE.md`,
   blob `252215c11b89252400919d16464454bcff7306bb`.
5. Canales del auditor 013 en adelante.

## Incidente PENDIENTE.md — corrección definitiva

La afirmación anterior de que `bca71898` había restaurado íntegramente el board era
falsa. Ese commit escribió una versión condensada de 15.003 B (`f924a60d`); el board
preexistente verificable era el linaje largo `e2e0cf40` → `252215c1` (108.777 →
112.595 B). Esta rama conserva ahora sólo un puntero y el acta de reconciliación.

Numeración corregida: las tres palancas son **P-60** (no P-58) y ML/LightGBM es
**P-61** (no P-59). Las P-56…P-59 del board largo conservan sus números.

## Gate 1 NQ

Secuencia: consolidación de ramas por auditor → token
`APPROVE_FREEZE_BT2A_NQ_GATE1_V1` → autorización de implementar CLI → autorización de
corrida. Power inputs ya congelados: MDE 2,90; SD 11,528529; 228/234 sesiones;
N_RAND capacity OK.

## Paridad aVolClusterPOI NQ

El gate sigue **FAIL**. La investigación posterior reportada por Claude descarta dos
hipótesis de bug: el offset de ~3 ticks sería un artefacto de frontera del diagnóstico,
y el clustering Python sería línea-por-línea equivalente al `.cs`. Los 57
`MISSING_IN_NT8` se concentran cerca del umbral (81% con ratio ≤1,15), pero cuatro
outliers >1,30 siguen abiertos. El outlier de 8 ticks requiere exportar `blockCells`
crudos desde NT8 para cierre completo.

El commit local reportado por Claude es `bda443e`, con los documentos
`AVOLCLUSTERPOI_PARITY_NQ0626_TASKS123_FINDINGS_2026-09-01.md` y
`AVOLCLUSTERPOI_PARITY_NQ0626_GEOMETRY_DIFF_ROOTCAUSE_2026-09-01.md`. **Debe pushearse
y auditarse contra los artefactos antes de adoptar el diagnóstico como veredicto del
repo.** No se justifica reejecutar el gate sin cambio de código/datos.

## Otras líneas

- SL/TP+breakeven GC: freeze bloqueado por suite de verdad conocida Romano-Wolf + MCS,
  artefacto P2B y auditoría del store.
- Infraestructura: palancas P-60; ML/LightGBM P-61, pendiente de decisión de Nico.
- Upload de `nt8/HFTZonesNQImpulseV2_5.cs` a `main`: pendiente.

*Corregido por el auditor el 2026-09-01 tras reconciliar contenido y linaje.*
