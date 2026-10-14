# MNQ retroceso EMA20 — ampliación43 y combinado197

## Veredicto

**SIN EDGE DEMOSTRADO.** La ampliación no refuerza la hipótesis: el filtro cambia de +4,36USD/trade en154 sesiones originales a −2,84USD/trade en43 anteriores. El combinado conserva media positiva, pero ambos endpoints tienen intervalos que incluyen cero y alpha medio contra controles negativo. No habilita promoción ni live.

## Población y protocolo

Sólo MNQ, un minuto, BASE y SEP, salida30min.43 sesiones elegibles04/08–06/10/2025;154 originales07/10/2025–30/06/2026;197combinadas. Se preservan las154 sin nuevo replay. Mismo detector, costos, filtro y controles, sin recalibración. Fechas nuevas en esta campaña, no certificadas ciegas en todo EdgeLab. Sin L2; holdout julio2026+ cerrado.

## Resultado económico

| Bloque | Variante | Trades | Trades/sesión | USD/trade | USD/trade stress2ticks/leg | Alpha medioU | Soporte pareado |
|---|---|---:|---:|---:|---:|---:|---:|
| ORIGINAL154 | BASE | 878 | 5.70 | +3.89 | ver acta original | ver acta original | ver acta original |
| ORIGINAL154 | SEP | 791 | 5.14 | +4.36 | ver acta original | ver acta original | ver acta original |
| EXTRA43 | BASE | 249 | 5.79 | +0.92 | -0.08 | -0.0491 | 225/249 (90.4%) |
| EXTRA43 | SEP | 227 | 5.28 | -2.84 | -3.84 | -0.2361 | 204/227 (89.9%) |
| COMBINED197 | BASE | 1127 | 5.72 | +3.24 | +2.24 | -0.0836 | 1022/1127 (90.7%) |
| COMBINED197 | SEP | 1018 | 5.17 | +2.76 | +1.76 | -0.1943 | 922/1018 (90.6%) |

USD para un contrato MNQ. Spread pagado en bidask; comisión supuesta0,60USD/lado y deslizamiento1tick/lado base,2/3stress. No fees del usuario ni fills certificados. U es rango verdadero medio de20barras estrictamente previas, en ticks; normalización por trade, no conversión del intervalo a USD.

## Inferencia y gates

| Bloque | Variante | NetoU, IC95% diagnóstico | AlphaU, IC95% diagnóstico |
|---|---|---|---|
| EXTRA43 | BASE | [-0.402, +0.493] | [-0.383, +0.277] |
| EXTRA43 | SEP | [-0.518, +0.346] | [-0.648, +0.162] |
| COMBINED197 | BASE | [-0.176, +0.266] | [-0.262, +0.098] |
| COMBINED197 | SEP | [-0.176, +0.244] | [-0.408, +0.019] |

Bootstrap nativo estacionario por sesiones, incluyendo cero trades;20.000 réplicas diagnósticas.43sesiones: bootstrap-t bloqueado por mínimo160.197sesiones:10.000réplicas studentizadas disponibles, intervalos ajustados a familia local20 también incluyen cero. Familia12 anterior+8nuevos;142 sólo escenario de presupuesto parcial, no historial completo/N_eff certificado.

G1 EXTRA43 BASE falla sin mejores5 y concentración; SEP falla además media positiva. COMBINED197 BASE pasa G1 diagnóstico; SEP falla al retirar las mejores5 operaciones. Las cuatro pantallas ajustadas fallan. Ningún endpoint positivo permite ignorar fullPBO/DSR/selectionWF/vecinos pendientes.

## Variación por mes

| Mes | BASE combinado, trades | BASE USD/trade | SEP USD/trade |
|---|---:|---:|---:|
| 202508 | 116 | -1.23 | -5.72 |
| 202509 | 110 | -4.79 | -6.16 |
| 202510 | 125 | +14.48 | +17.81 |
| 202511 | 104 | +14.33 | +11.77 |
| 202512 | 101 | -10.54 | -14.65 |
| 202601 | 109 | +9.92 | +13.56 |
| 202602 | 111 | +12.10 | +8.41 |
| 202603 | 74 | +3.28 | +1.08 |
| 202604 | 101 | -2.97 | -1.59 |
| 202605 | 93 | -13.31 | -7.53 |
| 202606 | 83 | +11.45 | +10.19 |

Bloque nuevo BASE: agosto116trades/20sesiones, −1,23USD; septiembre110/19, −4,79USD; sólo los primeros4días elegibles de octubre23trades, +39,06USD. No presentar estos4días como mes completo ni omitirlos para mejorar la estabilidad. CSV conserva bloques y variantes completos.

## Custodia y auditoría

Manifiesto congelado `59b07eca201487a0de40e7a1f818c1882aec08d94430a6b38844146b642ca134`. Runner `13c90af152679c2adda7060a05490d24ef37727fdca76c34bd1aec0bb86cb454`. Adapter estadístico `a068efcb23e62ab31dfd0339c3cb8fa538dfcae783403cdcd5758547ebeae673`. Source Kaggle privadov1 verificado byteporbyte, transporte `e7cc3ee01c46cff8f1ec5f6f8724e1113dd08679267e78a7f1447989418abb18`. Nativebase3913149, extensionbase848e5927, preparación736efd2. Corrida1 kernel136681024 COMPLETE; DONE100,9826s incluyendo descarga, runner `89.8484s`.

Dos fuentes verificadas; nuevo parquet34.508.845filas; distinguir hash original del parquet de manifest y hash ZSTD recomprimido actual. Preflight leído primero, sin outcomes.6prefixchecks y soporte targetfree guardado antes de replay.249intents→249COMPLETE;227SEP;1103controles nuevos. Viejas878/791 intactas;197calendarios conciliados; no unknown ni overlaps.

23tests dirigidos, no suite completa. Auditoría independiente:1129vínculos de controles, costos escalares1/2/3ticks, geometría, calendarios, sumas, medias, pareados y agregación original+nuevo.10quotes exactos del raw (entrada/salida de primeras5señales MNQ09-25), no auditoría raw completa.

Profiler no lee parquet directamente: muestra estructural20.000filas CSV; sin nulos/filasduplicadas; timestamps repetidos permitidos entre prints con secuencia única; columnas constantes corresponden a un contrato/fuente y no son corrupción. Scan completo acotado por productor aporta QA por sesión. Reloj absoluto/quoteage/publicación operable y MAE/MFE siguen sin certificar.

Resultados SHA `158f3112f050f206ed37c7c4f0b337ca2a41c505499c0222e0c41d21cb84c283`; preflight `69ab7ccc75112f6309633692e4c7939c771ae56c1aab7a915afb4553c618f795`. Raw, ledgers, producer privado y URLs firmadas no se publican. No merge ni modificación de visores/IPC/L2.

## Decisión

Archivar esta configuración como resultado de desarrollo sin edge demostrado; no rescatar SEP con más umbrales, ni abrir holdout para revertirlo. BASE sigue siendo una hipótesis descriptiva débil, no una estrategia validada. Más trades dieron una comprobación de fragilidad del filtro, no evidencia de ventaja nueva.

Aporte al referente: la ampliación conserva frecuencia cercana a5–6operaciones por sesión, pero debilita la selección SEP y mantiene abierta la explicación de ruido/benchmark direccional.
