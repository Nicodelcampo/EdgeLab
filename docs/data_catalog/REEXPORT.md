# Qué hay que re-exportar o re-subir (generado)

Cada punto sale de una regla verificable sobre el catálogo. Orden de prioridad: contratos faltantes y fuentes en conflicto primero.

## CONTRATO_FALTANTE

- **GC:** Exportar GC_08-25, GC_10-25 (contratos del ciclo estándar que debieron ser líder y no están).
- **MGC:** Exportar MGC_10-25, MGC_10-26 (contratos del ciclo estándar que debieron ser líder y no están).

## FUENTES_EN_CONFLICTO

- **6E:** Contratos con fuentes que difieren de forma material: 6E_09-26. Reexportar de NinjaTrader y comparar contra las dos.
- **ES:** Contratos con fuentes que difieren de forma material: ES_09-26. Reexportar de NinjaTrader y comparar contra las dos.
- **MNQ:** Contratos con fuentes que difieren de forma material: MNQ_09-26, MNQ_12-26. Reexportar de NinjaTrader y comparar contra las dos.
- **NQ:** Contratos con fuentes que difieren de forma material: NQ_06-26, NQ_09-25. Reexportar de NinjaTrader y comparar contra las dos.

## SESIONES_FALTANTES

- **6E:** Faltan sesiones que no son feriados: 2026-09-03. Reexportar esos días.
- **ES:** Faltan sesiones que no son feriados: 2026-08-27. Reexportar esos días.
- **MBT:** Faltan sesiones que no son feriados: 2026-06-01..2026-06-05, 2026-06-08..2026-06-12, 2026-06-15..2026-06-18. Reexportar esos días.
- **MES:** Faltan sesiones que no son feriados: 2026-08-06, 2026-08-13. Reexportar esos días.
- **MGC:** Faltan sesiones que no son feriados: 2026-07-02, 2026-07-09, 2026-07-16, 2026-07-30, 2026-08-28, 2026-09-10..2026-09-11. Reexportar esos días.
- **MNQ:** Faltan sesiones que no son feriados: 2026-03-26, 2026-04-02, 2026-05-21. Reexportar esos días.
- **MYM:** Faltan sesiones que no son feriados: 2026-07-09, 2026-07-16, 2026-07-23, 2026-07-30, 2026-08-20. Reexportar esos días.
- **YM:** Faltan sesiones que no son feriados: 2026-08-20. Reexportar esos días.

## COBERTURA_CORTA

- **GC:** Los datos terminan el 2026-06-30; para julio-septiembre de 2026 hace falta exportar desde 2026-06-30.
- **MBT:** Los datos terminan el 2026-06-30; para julio-septiembre de 2026 hace falta exportar desde 2026-06-30.
- **ZB:** Los datos terminan el 2026-06-30; para julio-septiembre de 2026 hace falta exportar desde 2026-06-30.

## ARCHIVOS_VACIOS_O_DE_RELLENO

Archivos con menos de 1.000 trades (casi vacíos): no se usan y el contrato **debe reexportarse**.

| Dataset | Archivo | Contrato | Trades | Tamaño (bytes) |
|---|---|---|---:|---:|
| `edgelab-mgc-nt8-raw-parquet-20261002` | `MGC_08-25.parquet` | MGC_08-25 | 3 | 3,188 |
| `edgelab-ticks-nt8-canonical` | `MYM/MYM_09-25_ticks_ext.parquet` | MYM_09-25 | 2 | 4,355 |
| `edgelab-ticks-nt8-canonical` | `RTY/RTY_09-25_ticks_ext.parquet` | RTY_09-25 | 1 | 4,268 |

## DUKASCOPY XAU/USD (spot)

- Dataset unificado vigente: 2022-07-01..2026-10-01, 1098 sesiones; días hábiles sin datos sin explicación: ninguno. **No requiere re-subida.**

