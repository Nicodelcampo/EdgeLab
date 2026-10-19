# Barrido horario, etapa A — resultados (2026-10-04)

Pre-registro: `PREREGISTRO_ETAPA_A.md` (commit anterior al cálculo). Solo datos previos al holdout; datasets parciales, no elegibles para backtest continuo (EF0), así que el resultado es **exploratorio**. Archivos: `etapaA_{GC,ZB,6J,6E,6E6J}.json`.

## Resultados por activo
Rejilla de 96 franjas × 4 holdings × 3 condiciones (celdas con ≥ 40 oportunidades), `max |z|` en dos colas contra el nulo de signo por sesión (20.000 sorteos).

| Activo | Sesiones | Celdas | max \|z\| real | q95 del nulo | **p_max** | Réplica 70/30: mejor p de Holm (neto real tras comisión) |
|---|---:|---:|---:|---:|---:|---|
| GC | 225 | 1.059 | 3,95 | 3,71 | **0,016** | 0,031 (04:15, 15 min, tras subida, corto; +21,3 ticks) |
| ZB | 211 | 911 | 3,34 | 3,79 | 0,303 | 0,086 |
| 6J | 225 | 1.059 | 3,81 | 3,79 | **0,047** | 0,012 (12:00, 60 min, tras subida, corto; +1,25 ticks) |
| 6E | 228 | 1.059 | 3,34 | 3,82 | 0,332 | 0,474 |
| 6E + 6J (cesta) | 232 | 1.059 | 3,65 | 3,83 | 0,108 | 0,153 |

## Aplicación de la regla pre-registrada
- **GC y 6J cumplen** las tres condiciones: p_max ≤ 0,05, una celda de la réplica con p de Holm ≤ 0,05 en el 30 % reservado y media neta real > 0 tras comisión.
- **ZB y 6E no**: p_max > 0,05, estructura no distinguible del azar. La cesta de divisas tampoco (p_max = 0,108).
- Qué habilita: solo escribir un pre-registro de la etapa B (salidas) para GC y 6J. Ninguna cifra de esta etapa es un edge.

## Lo que hay que tener en cuenta (declarado)
1. **Multiplicidad entre activos.** Se hicieron 4 pruebas independientes más la cesta (5 en total, 5.760 celdas). El pre-registro no especificó corrección entre activos. Con Bonferroni (umbral 0,05 / 4 = 0,0125) no pasaría ninguno, ni GC (0,016) ni 6J (0,047, apenas bajo 0,05). Con 4 pruebas al 5 %, la probabilidad de al menos un falso positivo es ≈ 19 %.
2. **Qué es la «media neta real».** Incluye todas las sesiones, también las usadas para elegir la celda, y no resta la tendencia. En GC (+21,3 ticks por operación sobre 128 operaciones) es muy alta para 15 minutos de tenencia; puede reflejar la subida del oro en la muestra, huecos en las series parciales o liquidez fina de la sesión de Londres. No es una estimación fuera de muestra.
3. **Réplica con una sola ventana.** El 30 % reservado son ≈ 68 sesiones. Las otras 4 celdas de GC tuvieron z OOS entre 0,26 y 0,61 (misma dirección, sin significancia).
4. **Observación post hoc, sin probar:** en ZB, 6J y 6E las celdas de mayor |z| son «tras una subida de los 15 minutos previos, corto» entre las 12:00 y las 13:30 de Chicago (en GC, a las 04:15). Sugiere una reversión de corto plazo común, pero se vio después de mirar los datos; probarla exige su propio pre-registro y no cuenta como evidencia aquí.

## Lectura
No hay base para decir que la estrategia original tenga edge en ZB ni en 6E con estos datos. En GC y 6J aparece una señal que cumple la regla escrita antes pero que no resiste una corrección entre activos; es una pista para una etapa B, no un resultado.
