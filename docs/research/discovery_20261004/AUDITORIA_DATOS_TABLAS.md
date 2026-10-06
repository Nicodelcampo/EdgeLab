# Auditoría de datos: tablas generadas

Generado por `tools/discovery_audit_report.py` desde `artifacts/discovery/audit/`. Descriptivo: no se excluyó ninguna sesión ni tick.

## Resumen por activo

| Activo | Rango | Fechas con datos | Sesiones usadas (elegibles) | No elegibles por volumen | Días hábiles sin datos sin motivo conocido | Costo de libro entrada+salida p50 / p99 / máx (ticks) |
|---|---|---:|---:|---:|---:|---|
| 6E | 2025-07-25 a 2026-06-30 | 263 | 228 | 35 | 0 | 2 / 3 / 6 |
| 6J | 2025-08-01 a 2026-06-30 | 260 | 225 | 35 | 0 | 2 / 3 / 4 |
| ES | 2025-07-18 a 2026-06-30 | 280 | 234 | 46 | 0 | 2 / 3 / 17 |
| GC | 2025-08-01 a 2026-06-30 | 258 | 225 | 32 | 0 | 6 / 23 / 51 |
| NQ | 2025-08-01 a 2026-06-30 | 265 | 220 | 44 | 0 | 5 / 15 / 38 |
| YM | 2025-08-15 a 2026-06-30 | 246 | 209 | 36 | 0 | 3 / 8 / 61 |
| ZB | 2025-08-18 a 2026-06-30 | 250 | 211 | 39 | 0 | 2 / 2 / 4 |

## 6E

### Contratos (trades de la ventana previa al corte)

| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 6E_09-25 | 2,539,857 | 0 | 25 | 0 | 0 | 0 | 60 | 1 / 3 / 64 | 0 | 31 | 43 | 10 | 0 |
| 6E_12-25 | 4,512,656 | 0 | 55 | 0 | 0 | 0 | 41 | 1 / 3 / 117 | 63 | 37 | 82 | 16 | 0 |
| 6E_03-26 | 5,064,128 | 0 | 55 | 0 | 0 | 0 | 24 | 1 / 3 / 510 | 1 | 37 | 76 | 14 | 1 |
| 6E_06-26 | 5,554,201 | 0 | 58 | 0 | 0 | 0 | 26 | 1 / 3 / 49 | 0 | 46 | 71 | 5 | 1 |
| 6E_09-26 | 1,084,345 | 0 | 12 | 0 | 0 | 0 | 0 | 1 / 3 / 37 | 0 | 17 | 17 | 3 | 1 |

Spreads ≥ 100 ticks (valores más frecuentes y horas CT con más casos):

- 6E_12-25: 63 ticks; valores 115 (15), 106 (8), 117 (7); horas CT 13h (63)
- 6E_03-26: 1 ticks; valores 510 (1); horas CT 9h (1)

Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):

- pocos_ticks(<25% de la mediana): 39 / 0
- termina_antes_de_15:55_CT: 29 / 1
- hueco ≥ 5 min en 08:30-15:00 CT: 24 / 2

Días hábiles sin datos: 2025-12-25 (feriado federal de EE.UU.), 2026-01-01 (feriado federal de EE.UU.)

Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):

- 6E_09-25 → 6E_12-25 desde 2025-09-13: volumen previo 18,960 → 106,697; diferencia 118
- 6E_12-25 → 6E_03-26 desde 2025-12-14: volumen previo 16,725 → 130,182; diferencia 105
- 6E_03-26 → 6E_06-26 desde 2026-03-16: volumen previo 26,890 → 211,629; diferencia 97
- 6E_06-26 → 6E_09-26 desde 2026-06-15: volumen previo 20,678 → 149,745; diferencia 85

## 6J

### Contratos (trades de la ventana previa al corte)

| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 6J_09-25 | 1,474,871 | 0 | 12 | 0 | 0 | 0 | 22 | 1 / 2 / 43 | 0 | 17 | 38 | 10 | 1 |
| 6J_12-25 | 3,795,837 | 0 | 31 | 0 | 0 | 0 | 44 | 1 / 2 / 43 | 0 | 27 | 83 | 19 | 0 |
| 6J_03-26 | 4,670,101 | 0 | 43 | 0 | 0 | 0 | 43 | 1 / 3 / 61 | 0 | 60 | 75 | 13 | 2 |
| 6J_06-26 | 4,012,219 | 0 | 35 | 0 | 0 | 0 | 11 | 1 / 3 / 26 | 0 | 22 | 71 | 7 | 2 |
| 6J_09-26 | 674,550 | 0 | 7 | 0 | 0 | 0 | 1 | 1 / 2 / 22 | 0 | 16 | 18 | 5 | 2 |

Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):

- pocos_ticks(<25% de la mediana): 41 / 0
- termina_antes_de_15:55_CT: 24 / 2
- hueco ≥ 5 min en 08:30-15:00 CT: 23 / 5

Días hábiles sin datos: 2025-12-25 (feriado federal de EE.UU.), 2026-01-01 (feriado federal de EE.UU.)

Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):

- 6J_09-25 → 6J_12-25 desde 2025-09-14: volumen previo 8,581 → 91,413; diferencia 127
- 6J_12-25 → 6J_03-26 desde 2025-12-15: volumen previo 10,828 → 93,247; diferencia 106
- 6J_03-26 → 6J_06-26 desde 2026-03-16: volumen previo 18,643 → 130,925; diferencia 101
- 6J_06-26 → 6J_09-26 desde 2026-06-15: volumen previo 13,826 → 128,118; diferencia 91

## ES

### Contratos (trades de la ventana previa al corte)

| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| ES_09-25 | 35,045,149 | 0 | 59 | 0 | 0 | 0 | 42 | 1 / 3 / 71 | 0 | 41 | 56 | 14 | 0 |
| ES_12-25 | 73,446,975 | 0 | 409 | 0 | 0 | 0 | 63 | 1 / 3 / 75 | 0 | 43 | 88 | 23 | 0 |
| ES_03-26 | 68,302,992 | 0 | 94 | 0 | 0 | 0 | 160 | 1 / 3 / 88 | 0 | 52 | 79 | 18 | 0 |
| ES_06-26 | 73,268,494 | 0 | 101 | 0 | 0 | 0 | 130 | 1 / 4 / 82 | 0 | 137 | 72 | 9 | 1 |
| ES_09-26 | 12,743,000 | 0 | 17 | 0 | 0 | 0 | 0 | 1 / 4 / 72 | 0 | 71 | 18 | 7 | 1 |

Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):

- pocos_ticks(<25% de la mediana): 67 / 0
- termina_antes_de_15:55_CT: 39 / 0
- hueco ≥ 5 min en 08:30-15:00 CT: 19 / 2

Días hábiles sin datos: 2026-01-01 (feriado federal de EE.UU.)

Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):

- ES_09-25 → ES_12-25 desde 2025-09-16: volumen previo 433,348 → 698,739; diferencia 230
- ES_12-25 → ES_03-26 desde 2025-12-15: volumen previo 2 → 88; diferencia 239
- ES_03-26 → ES_06-26 desde 2026-03-17: volumen previo 798,836 → 1,055,293; diferencia 202
- ES_06-26 → ES_09-26 desde 2026-06-16: volumen previo 579,431 → 923,610; diferencia 261

## GC

### Contratos (trades de la ventana previa al corte)

| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| GC_12-25 | 16,206,084 | 0 | 124 | 0 | 0 | 0 | 186 | 2 / 12 / 510 | 161 | 234 | 124 | 43 | 1 |
| GC_02-26 | 7,699,219 | 0 | 112 | 0 | 0 | 0 | 91 | 3 / 13 / 510 | 94 | 781 | 77 | 35 | 2 |
| GC_04-26 | 6,827,667 | 0 | 257 | 0 | 0 | 0 | 103 | 6 / 35 / 325 | 1300 | 841 | 72 | 27 | 1 |
| GC_06-26 | 4,617,492 | 0 | 60 | 0 | 0 | 0 | 24 | 4 / 25 / 255 | 364 | 218 | 68 | 22 | 0 |
| GC_08-26 | 2,804,464 | 0 | 27 | 0 | 0 | 0 | 0 | 4 / 15 / 241 | 234 | 145 | 27 | 4 | 3 |

Spreads ≥ 100 ticks (valores más frecuentes y horas CT con más casos):

- GC_12-25: 161 ticks; valores 110 (23), 101 (19), 106 (15); horas CT 17h (48), 7h (32), 19h (25)
- GC_02-26: 94 ticks; valores 255 (16), 136 (6), 109 (5); horas CT 23h (55), 9h (17), 14h (5)
- GC_04-26: 1300 ticks; valores 100 (98), 101 (74), 104 (73); horas CT 17h (287), 9h (249), 7h (149)
- GC_06-26: 364 ticks; valores 131 (17), 100 (12), 125 (12); horas CT 17h (269), 7h (77), 2h (9)
- GC_08-26: 234 ticks; valores 134 (15), 104 (11), 101 (10); horas CT 7h (190), 17h (44)

Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):

- pocos_ticks(<25% de la mediana): 120 / 0
- termina_antes_de_15:55_CT: 103 / 4
- hueco ≥ 5 min en 08:30-15:00 CT: 91 / 3

Días hábiles sin datos: 2025-12-25 (feriado federal de EE.UU.), 2026-01-01 (feriado federal de EE.UU.), 2026-04-03 (Viernes Santo)

Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):

- GC_12-25 → GC_02-26 desde 2025-11-26: volumen previo 58,146 → 151,863; diferencia 389
- GC_02-26 → GC_04-26 desde 2026-01-29: volumen previo 49,676 → 335,444; diferencia 368
- GC_04-26 → GC_06-26 desde 2026-03-30: volumen previo 21,187 → 149,438; diferencia 308
- GC_06-26 → GC_08-26 desde 2026-05-28: volumen previo 26,328 → 147,467; diferencia 336

## NQ

### Contratos (trades de la ventana previa al corte)

| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| NQ_09-25 | 13,624,675 | 0 | 37 | 0 | 0 | 0 | 91 | 2 / 11 / 255 | 847 | 114 | 42 | 12 | 0 |
| NQ_12-25 | 34,264,511 | 0 | 79 | 0 | 0 | 0 | 206 | 2 / 15 / 255 | 1120 | 471 | 86 | 22 | 0 |
| NQ_03-26 | 30,825,016 | 0 | 100 | 0 | 0 | 0 | 196 | 3 / 16 / 255 | 1515 | 376 | 79 | 18 | 0 |
| NQ_06-26 | 34,203,535 | 0 | 96 | 0 | 0 | 0 | 83 | 3 / 19 / 307 | 1904 | 413 | 72 | 8 | 0 |
| NQ_09-26 | 6,235,464 | 0 | 21 | 0 | 0 | 0 | 1 | 4 / 24 / 255 | 537 | 2978 | 19 | 8 | 0 |

Spreads ≥ 100 ticks (valores más frecuentes y horas CT con más casos):

- NQ_09-25: 847 ticks; valores 137 (23), 100 (22), 122 (22); horas CT 7h (371), 9h (247), 15h (222)
- NQ_12-25: 1120 ticks; valores 255 (80), 100 (42), 111 (34); horas CT 7h (352), 15h (277), 8h (170)
- NQ_03-26: 1515 ticks; valores 100 (58), 101 (54), 102 (54); horas CT 7h (714), 17h (286), 9h (220)
- NQ_06-26: 1904 ticks; valores 101 (116), 100 (90), 102 (85); horas CT 7h (406), 17h (347), 8h (241)
- NQ_09-26: 537 ticks; valores 103 (27), 100 (24), 109 (24); horas CT 17h (150), 8h (88), 11h (73)

Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):

- pocos_ticks(<25% de la mediana): 64 / 0
- termina_antes_de_15:55_CT: 40 / 0
- hueco ≥ 5 min en 08:30-15:00 CT: 8 / 0

Días hábiles sin datos: 2026-01-01 (feriado federal de EE.UU.)

Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):

- NQ_09-25 → NQ_12-25 desde 2025-09-17: volumen previo 94,421 → 320,669; diferencia 951
- NQ_12-25 → NQ_03-26 desde 2025-12-16: volumen previo 241,994 → 304,943; diferencia 989
- NQ_03-26 → NQ_06-26 desde 2026-03-17: volumen previo 249,343 → 280,702; diferencia 870
- NQ_06-26 → NQ_09-26 desde 2026-06-16: volumen previo 147,791 → 337,967; diferencia 1208

## YM

### Contratos (trades de la ventana previa al corte)

| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| YM_09-25 | 1,551,901 | 0 | 10 | 0 | 0 | 0 | 14 | 1 / 7 / 94 | 0 | 83 | 29 | 8 | 0 |
| YM_12-25 | 5,798,136 | 0 | 37 | 0 | 0 | 0 | 80 | 2 / 7 / 310 | 31 | 180 | 85 | 21 | 0 |
| YM_03-26 | 6,460,091 | 0 | 34 | 0 | 0 | 0 | 97 | 2 / 7 / 200 | 31 | 94 | 75 | 15 | 1 |
| YM_06-26 | 6,213,697 | 0 | 37 | 0 | 0 | 0 | 77 | 2 / 10 / 243 | 83 | 133 | 72 | 9 | 0 |
| YM_09-26 | 1,027,629 | 0 | 6 | 0 | 0 | 0 | 1 | 2 / 10 / 255 | 39 | 161 | 17 | 5 | 0 |

Spreads ≥ 100 ticks (valores más frecuentes y horas CT con más casos):

- YM_12-25: 31 ticks; valores 101 (6), 126 (3), 310 (3); horas CT 7h (17), 8h (6), 17h (4)
- YM_03-26: 31 ticks; valores 123 (9), 164 (5), 100 (4); horas CT 7h (20), 14h (7), 17h (3)
- YM_06-26: 83 ticks; valores 102 (11), 101 (4), 121 (4); horas CT 7h (67), 17h (7), 13h (5)
- YM_09-26: 39 ticks; valores 255 (5), 117 (3), 112 (2); horas CT 13h (26), 7h (7), 17h (6)

Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):

- pocos_ticks(<25% de la mediana): 54 / 0
- termina_antes_de_15:55_CT: 32 / 0
- hueco ≥ 5 min en 08:30-15:00 CT: 11 / 1

Días hábiles sin datos: 2025-12-25 (feriado federal de EE.UU.), 2026-01-01 (feriado federal de EE.UU.)

Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):

- YM_09-25 → YM_12-25 desde 2025-09-16: volumen previo 28,996 → 52,887; diferencia 340
- YM_12-25 → YM_03-26 desde 2025-12-16: volumen previo 31,071 → 59,037; diferencia 372
- YM_03-26 → YM_06-26 desde 2026-03-17: volumen previo 33,434 → 103,631; diferencia 293
- YM_06-26 → YM_09-26 desde 2026-06-15: volumen previo 50,108 → 64,657; diferencia 371

## ZB

### Contratos (trades de la ventana previa al corte)

| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| ZB_09-25 | 610,102 | 0 | 16 | 0 | 0 | 0 | 412 | 1 / 1 / 11 | 0 | 4 | 28 | 20 | 0 |
| ZB_12-25 | 7,370,765 | 0 | 189 | 0 | 0 | 0 | 4474 | 1 / 1 / 42 | 0 | 11 | 102 | 38 | 1 |
| ZB_03-26 | 7,624,585 | 0 | 170 | 0 | 0 | 0 | 4358 | 1 / 1 / 18 | 0 | 14 | 98 | 38 | 3 |
| ZB_06-26 | 9,029,661 | 0 | 96 | 0 | 0 | 0 | 5931 | 1 / 1 / 32 | 0 | 19 | 84 | 19 | 0 |
| ZB_09-26 | 2,569,580 | 0 | 80 | 0 | 0 | 0 | 1918 | 1 / 1 / 7 | 0 | 9 | 27 | 2 | 0 |

Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):

- pocos_ticks(<25% de la mediana): 98 / 0
- termina_antes_de_15:55_CT: 92 / 1
- hueco ≥ 5 min en 08:30-15:00 CT: 80 / 4

Días hábiles sin datos: 2026-01-01 (feriado federal de EE.UU.)

Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):

- ZB_09-25 → ZB_12-25 desde 2025-08-25: volumen previo 5 → 10; diferencia -12
- ZB_12-25 → ZB_03-26 desde 2025-11-24: volumen previo 1 → 9; diferencia -11
- ZB_03-26 → ZB_06-26 desde 2026-02-26: volumen previo 108,133 → 220,266; diferencia -14
- ZB_06-26 → ZB_09-26 desde 2026-05-28: volumen previo 108,468 → 321,512; diferencia -16
