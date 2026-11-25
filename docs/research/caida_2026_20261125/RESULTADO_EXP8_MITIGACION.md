# EXP-8: mitigar la caída final sin sobreajuste — resultado

Estado: RESULTADO (Parte A EF3, 24 pruebas contadas; Parte B EF2 descriptiva). Pre-registro `PREREGISTRO_EXP8_MITIGACION.md`.  
Fecha: 2026-11-25  
Herramienta: `tools/exp8_mitigacion.py`. Corrida que cuenta: **2** (`exp8/EXP8_corrida2.json`, `exp8/CARTERAS_MENSUALES_corrida2.csv`); corrida 1 publicada.  
Diagnóstico de grilla: no aplica (sin perillas: un umbral fijo, la mediana expansiva; pesos por regla fija).

## Auditoría (iteración pedida por Nico)
1. **Corregido — unidad de la prueba**: la corrida 1 comparaba operaciones; V tiene ≈ 1,5 operaciones por día y las del mismo día
   no son independientes (p demasiado chico). Corrida 2: R sumado por sesión. Sólo cambia V (las demás operan una vez por día).
2. **Corregido — arranque de los pesos inverso-volatilidad**: en la corrida 1 los 12 primeros meses (2020) quedaban a peso 1, o sea
   igual a la cartera sin pesos, justo en el drawdown de 2020. Corrida 2: la volatilidad se estima con los meses de 2019 de cada
   corrida NT8, y los meses anteriores a la primera operación de cada estrategia son historia faltante (no ceros).
3. Verificado sin hallazgos: el estado de la sesión t usa sólo sesiones anteriores (`merge_asof` estricto) y la mediana se calcula
   sobre esa misma serie hasta t−1; fricción canónica; bloques A5; 2026 y HOLDOUT sólo descriptivos.

## Parte A — Filtro por estado de la apertura (20 sesiones previas): 0/24 en BH, ninguna confirma
p mínimo en DESC: RQ5_NQ × `ac5_manana` 0,0045 (umbral BH del primero: 0,0042) y **en REP da al revés** (−0,20 R/op, p 0,92).
Las otras diferencias en DESC son chicas frente a su MDE (0,16–0,47 R/op). En REP aparecen dos positivas (RQ5_ES y ES5N_ES ×
`frac_noche`, p 0,01) que no estaban en DESC: no se pueden usar (sería elegir mirando la réplica).
**Lectura**: un estado de 20 sesiones del mercado no anticipa cuándo pagan estas reglas. La caída no se puede apagar con un
interruptor de régimen de este tipo sin sobreajustar. Tabla completa (R/op encendido, apagado, MDE, por bloque) en el JSON.

## Parte B — Armado de cartera (descriptivo; 11 estrategias, R mensual, 1 R por operación)
| Esquema | 2020–2025: R/mes | sd | meses < 0 | DD máx | peor semestre | R/mes ÷ DD | 2026: R/mes | DD máx | peor semestre |
|---|---|---|---|---|---|---|---|---|---|
| IGUAL_MANANA (5) | 5,54 | 11,2 | 28/72 | −26,1 | −20,5 | 0,21 | 1,65 | −28,2 | −22,0 |
| IGUAL_TODAS (11) | 8,88 | 14,7 | 21/72 | −45,5 | −22,6 | 0,20 | 5,63 | −17,7 | −3,9 |
| **INV_VOL_TODAS (11)** | 5,39 | 8,6 | 19/72 | **−22,1** | **−9,6** | **0,24** | 4,29 | **−6,7** | **+5,5** |
| MANANA_MAS_C2VZ (7) | 5,90 | 11,0 | 23/72 | −27,2 | −18,5 | 0,22 | 2,48 | −25,5 | −16,3 |

- **Inverso-volatilidad** (peso ∝ 1/sd del R mensual de los 12 meses previos, recortado a [0,25; 2]) es la única vía que reduce la
  caída sin elegir reglas. Llevado a la misma media que IGUAL_TODAS (×1,65), el drawdown 2020–2025 queda en ≈ −36 R contra −45,5 y
  el peor semestre en ≈ −16 R contra −22,6. En 2026 la mejora es mayor (DD −6,7 contra −17,7; descriptivo, el tramo inspiró la pregunta).
- Lo que hace en la práctica: baja el peso de las estrategias frecuentes y volátiles en R mensual (pesos a 2026-09: T 0,25, RQ5 ≈ 0,4,
  ES5N 0,41, V 0,57, SOM 0,57, Franklin 0,71, R 1,2, Z 1,44, C2_VZ 2,0 en NQ y ES). No mira la media de nadie.
- Sumar C2_VZ a la canasta de la mañana mejora poco (DD −27,2 contra −26,1 con más R; 2026 −25,5 contra −28,2).
- La canasta de la mañana sola es la peor en 2026: su caída es la caída que se ve en las curvas.

## Qué se puede usar hoy
- No hay filtro de régimen que apague la caída: las reglas se dejan como están.
- Para la cartera: repartir el riesgo por inverso de la volatilidad mensual de cada estrategia (regla fija, sin parámetros ajustados
  a resultados). Es una regla de tamaño, no de señal; su efecto es en drawdown, no en la media.
