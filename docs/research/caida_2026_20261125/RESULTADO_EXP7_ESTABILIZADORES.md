# EXP-7: estabilizadoras de la canasta de la mañana y entrada en retroceso — resultado

Estado: RESULTADO (EF3; pre-registro `PREREGISTRO_EXP7_ESTABILIZADORES.md`, 12 pruebas contadas)  
Fecha: 2026-11-25  
Herramienta: `tools/exp7_estabilizadores.py`. Corrida que cuenta: **2** (`exp7/EXP7_corrida2.json`, `exp7/SERIES_MENSUALES_corrida2.csv`).
Corrida 1 (`exp7/EXP7_corrida1.json`) publicada; corrección entre ambas abajo.
Diagnóstico de grilla: no aplica (reglas congeladas; 2 niveles de retroceso); llenado, R por operación y MDE por prueba en el JSON.

## Auditoría (iteración pedida por Nico)
1. **Corregido**: en la variante de retroceso las salidas `BE_STOP` salían en la entrada ORIGINAL (regalaba k·riesgo a la
   variante); en la corrida 2 salen en la entrada de la variante.
2. Aproximación declarada, sin cambio: salidas por `TARGET` al mismo precio (nivel efectivamente tocado).
3. Verificado sin hallazgos: búsqueda del retroceso desde la vela siguiente a la entrada (sin look-ahead), 0 horas ambiguas
   por cambio de horario, fricción canónica en todas las series NT8 (las de grilla ya la traen), meses por bloque A5:
   DESC 42, REP 12, HOLDOUT 18 (sólo descriptivo), 2026: 9 (sólo descriptivo).

## Canasta de la mañana (T_NQ, RQ5_NQ, RQ5_ES, ES5N_ES, Franklin_NQ)
R/mes medio: DESC +1,19 (17 de 42 meses malos), REP +0,48 (7 de 12), 2026 +0,33 (7 de 9 malos).

## Estabilizadoras (R medio del mes en los meses malos de la canasta; BH sobre 6 en DESC)
| Prueba | DESC: R malos / buenos, corr | p (MDE) | REP: R malos / buenos, corr | 2026 (desc.): malos / buenos, corr | Veredicto |
|---|---|---|---|---|---|
| C2VZ_NQ | +0,26 / +0,19, −0,24 | 0,050 (0,38) | +0,36 / +0,41, +0,10 | +0,51 / +0,28, −0,30 | Signo correcto en DESC y 2026; no pasa BH ni estabiliza en REP: SIN_POTENCIA |
| C2VZ_ES | +0,20 / +0,06, −0,17 | 0,104 (0,37) | +0,33 / +0,55, +0,24 | +0,45 / +0,09, −0,50 | Ídem: SIN_POTENCIA |
| OVN_NQ | +0,39 / +0,34, +0,04 | 0,26 (1,46) | −0,19 / −0,88, −0,34 | +0,88 / +0,88, +0,31 | No estabiliza (independiente), SIN_POTENCIA |
| SOMSF_NQ | −0,79 / +1,99, +0,30 | 0,76 (2,68) | +0,31 / +0,30, +0,05 | +1,48 / +5,08, +0,64 | **No es estabilizadora**: pierde en los meses malos (comparte el riesgo de la mañana) |
| OVN_ES | −0,43 / −0,68, −0,09 | 0,78 (1,33) | −0,16 / +0,51 | −0,34 / −0,27 | Negativa: REFUTADA como estabilizadora |
| KAL_NQ | −2,09 / −4,10, −0,00 | 0,87 (4,39) | −2,95 / −4,96, −0,36 | +2,89 / −1,71 | Negativa en DESC y REP: REFUTADA |

## Entrada en retroceso (diferencia mensual variante − original; BH sobre 6 en DESC)
| Prueba | Llenado | R/op llenadas (original de esas) | DESC dif/mes (p) | REP dif/mes | Veredicto |
|---|---|---|---|---|---|
| T_NQ k 0,25 | 63 % | +0,11 (−0,15) | −1,88 (1,00) | −0,94 | REFUTADA |
| T_NQ k 0,50 | 38 % | +0,04 (−0,46) | −2,34 (0,99) | −2,20 | REFUTADA |
| RQ5_NQ k 0,25 | 48 % | +0,02 (−0,23) | −0,80 (0,97) | −0,45 | REFUTADA |
| RQ5_NQ k 0,50 | 21 % | +0,03 (−0,48) | −0,84 (0,94) | −1,03 | REFUTADA |
| RQ5_ES k 0,25 | 46 % | +0,01 (−0,24) | −0,86 (0,93) | +0,11 | REFUTADA |
| RQ5_ES k 0,50 | 20 % | +0,02 (−0,49) | −0,60 (0,81) | −1,40 | REFUTADA |

**Selección adversa**: el retroceso se llena sobre todo en las operaciones que iban a perder (su R original es −0,15 a
−0,49) y deja afuera a las ganadoras que siguen sin retroceder. Mejora las que se llenan, pero pierde más por las que no.

## Lectura
- Ninguna estabilizadora pasa: la única con el signo buscado (gana más en los meses malos y correlación negativa) es
  **C2_VZ** (NQ y ES) en DESC y en 2026, pero no se sostiene en REP (12 meses, MDE ≈ 0,8–1,0) y no alcanza BH.
- SOM sin_finde no diversifica la canasta de la mañana: pierde justo en sus meses malos (corr +0,30).
- La entrada en retroceso queda refutada para T y RQ5 por selección adversa.
