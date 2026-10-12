# IDM-1 — resultado (borrador `docs/research/autopilot/drafts/IDM-1.md`, 10 pruebas, Holm 10)

Lanzada y analizada por el autopilot (nivel familiar 0,0238; 97 s). Datos crudos: `IDM1_RESULTADOS.json`.

## Veredicto del pre-registro: 1 hallazgo (hit) en 10 pruebas, y NO está en la pista de origen
| Prueba | n | corr(resto del día, última media hora) | p | Holm 10 |
|---|---:|---:|---:|---:|
| **GC (futuro, 2025-07→2026-09)** | 274 | **+0,309** | 0,0009 | **0,009** |
| ES futuro / NQ / YM / ZB / 6E | 241 a 284 | −0,04 a +0,003 | 0,49 a 0,71 | 1,0 |
| 6J | 258 | −0,150 | 0,99 | 1,0 |
| **ES spot (2018-2025)** | 2.317 | +0,053 | 0,25 | 1,0 |
| Gamma bajo − alto (ES spot) | 489 / 1.828 | +0,106 | 0,175 | 1,0 |
| GC spot (2022-07→2025-06) | 931 | +0,050 | 0,135 | 1,0 |

## Qué dice y qué no
- **La pista de origen falla.** El puente «momentum intradía de la literatura + gamma» (GEX_I2D_ROD_LH) se midió en ES spot y en la diferencia por gamma: ninguna pasa (p 0,25 y 0,175, aunque el signo es el esperado). Pasa a `FAILED_REPLICATION` en la evidencia viva.
- **Hallazgo nuevo e inesperado: GC futuro.** Correlación +0,31 (Holm 0,009). Sensibilidad posterior (descriptiva, solo con 126 sesiones de GC de la caché local, 2025-11→2026-05): Pearson 0,315, Spearman 0,250, con winsorización 5/95 % 0,318, sin los 5 días de mayor movimiento 0,276; positiva en 5 de 6 meses (−0,03 en mayo). No parece depender de unos pocos días.
- **Por qué no es edge:** (1) es una sola de 10 pruebas, en un solo activo, sin mecanismo propio (GC no es un índice con cobertura de gamma); (2) el hermano spot 2022-2025 da +0,05 (n.s.), así que puede ser específico del régimen de 2025-26 (oro con tendencia fuerte, coherente con el sesgo vendedor de 2026 de H1/H2 que no existía antes); (3) la ventana 14:30-15:00 CT en GC cae después del cierre de la sesión regular de los metales; (4) no se midió costo ni ejecución.
- **Siguiente paso honesto:** abre la pista `idm-1:idm/GC` (`WEAK_LEAD`, muestra independiente = datos posteriores al 2026-09-30, es decir, holdout cerrado). El generador la deja como `WAIT-…` (bloqueada, decisión humana). No se vuelve a probar con datos ya usados.

## Costo de multiplicidad y estado de aprendizaje
10 pruebas contadas antes de lanzar. Riqueza de alfa 0,0756 (+0,05 por el hallazgo). Corrección de sistema: el primer criterio marcó la pista de origen como replicada por un hallazgo ajeno a ella; ahora cada pista se evalúa solo con sus propias pruebas y un hallazgo fuera de ellas abre una pista nueva (el registro original se conserva y la corrección se anexó, con `correction_of`).
