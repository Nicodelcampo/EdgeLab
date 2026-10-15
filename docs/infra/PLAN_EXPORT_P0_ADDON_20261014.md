# Plan de exportación P0 con el AddOn «EdgeLab Tick History»

Estado: VIGENTE
Fecha: 2026-10-14
Familia / módulo: liquid-release · R0 (datos)

Cubre los 309 tramos P0 de `docs/infra/MISSING_EXPORTS_20261014.md` (son **ticks**, no L2). Campos del formulario del AddOn: *Contratos exactos* (separados por `;`, formato `PRODUCTO MM-AA`), *Desde (inclusive)*, *Hasta (inclusive)* y *Carpeta de salida*.
- **Carpeta de salida:** `E:\DatosNT8	ick_history_P0_20261014` (una carpeta nueva, para no mezclar con exports anteriores y poder auditarla sola).
- **Fechas:** el `Desde` ya está corrido un día antes del `trade_date` faltante (la sesión CME abre la noche anterior, 17:00 CT). Días de más no molestan.
- Usá **Probar** primero (1 día por semana, sin escribir): si NT8 no tiene historia tan atrás (las más viejas son de julio-agosto 2025), el *Probar* lo muestra antes de bajar nada.

## Fase 1 — los 4 grandes (sin ningún dato hoy; 140 de las 309 sesiones)
| Contratos exactos | Desde | Hasta | Sesiones |
|---|---|---|---:|
| `MGC 08-25;MGC 10-25;MGC 12-25` | 2025-07-31 | 2025-10-06 | 46 |
| `MYM 09-25;MYM 12-25` | 2025-07-31 | 2025-09-29 | 41 |
| `RTY 09-25;RTY 12-25` | 2025-07-31 | 2025-10-01 | 43 |
| `YM 09-25` | 2025-07-31 | 2025-08-14 | 10 |
Los contratos de esta fase los deduje por el ciclo de vencimientos (MGC bimestral, MYM/RTY/YM trimestral): si NT8 no ofrece alguno, sacalo de la lista.

## Fase 2 — tandas con contrato explícito y ≥ 4 sesiones
| Contratos exactos | Desde | Hasta | Sesiones |
|---|---|---|---:|
| `MGC 06-26` | 2026-02-04 | 2026-04-02 | 10 |
| `MNQ 09-26` | 2026-06-10 | 2026-07-17 | 9 |
| `YM 06-26` | 2026-01-14 | 2026-02-26 | 8 |
| `MGC 08-26` | 2026-06-08 | 2026-06-24 | 7 |
| `MGC 08-26` | 2026-04-01 | 2026-05-21 | 7 |
| `MYM 12-26` | 2026-08-05 | 2026-09-10 | 6 |
| `YM 09-26` | 2026-04-01 | 2026-04-30 | 5 |
| `6E 12-26` | 2026-08-05 | 2026-09-03 | 5 |
| `MYM 06-26` | 2026-05-21 | 2026-06-05 | 4 |
| `GC 12-26` | 2026-09-15 | 2026-09-24 | 4 |

## Fase 3 — resto (53 tandas, 84 sesiones) y sesiones sin datos de ningún contrato
- Tandas chicas con contrato explícito: `docs/infra/PLAN_EXPORT_P0_ADDON_20261014.csv` (columna `Desde`/`Hasta`; ordenadas por contrato).
- Sesiones donde **ningún** contrato tiene dato (contrato = el vigente en la fecha; exportar los dos más cercanos): 2025-12-25 (6B, 6J, MES, MNQ, RTY, YM), 2026-09-28→30 (6B, 6E, 6J: `12-26`; ES y NQ 2026-09-28: `12-26`), 2026-09-16 y 2026-09-24 (GC `12-26`), 2026-08-20 (MYM `12-26`).

## Después de exportar
Avisame la carpeta: valido tamaños y esquema, las integro a una release v5 (reconstrucción, verificación, auditoría en Kaggle y aprobación con el SHA nuevo) y las subo **una sola vez** junto con lo que aporte el addon.

## Resultado de la primera corrida (2026-10-14, conexión «Simulation»)
- `DESCARGAR MGC 08-25 …` (31 s por día): de 43 días probados, **1 con datos** (2025-08-26, 2 ticks) y 42 `NO_DATA`; se detuvo a mano.
- `PROBAR MGC 08-25;MGC 10-25;MGC 12-25`: `MGC 08-25` y `MGC 12-25` sin datos en los 10 días de muestra; **NT8 no conoce `MGC 10-25`** (error).
- **Lectura:** con la conexión «Simulation» NT8 sólo entrega lo que ya está en su base local; MGC antes del 2025-10-08 (primera sesión de la release) nunca tuvo tick en esta máquina. Esas 46 sesiones **no son recuperables con esta conexión** (hacen falta los datos del proveedor real) y no son un defecto de la release: están fuera de su cobertura.
- **Regla operativa:** correr siempre **Probar** antes de **Descargar** (10 días en ~3 s contra ~31 s por día) y descargar sólo los contratos/rangos que muestren datos. Para historia nueva, conectar el proveedor real con el que se hicieron los exports anteriores.
