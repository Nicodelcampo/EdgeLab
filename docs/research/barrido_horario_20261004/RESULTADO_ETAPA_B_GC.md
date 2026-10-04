# Barrido horario, etapa B — GC (2026-10-04)

Pre-registro: `PREREGISTRO_ETAPA_B_GC.md` (anterior al cálculo). Resultados en `etapaB_GC.json`; código en `tools/barrido_horario_etapa_b_gc.py`. Mismos datos que la etapa A (parciales, previos al holdout): **exploratorio**.

## Validación del simulador
La celda base (04:15 CT, tras subida, corto, 15 min, ejecución de libro, comisión 0,45 ticks) reproduce la etapa A: **128 operaciones, +21,32 ticks netos**. (El script imprimió «0 / nan» en la comparación por un error de índice en la propia validación; no afecta al simulador.)

## B0 — Auditoría de datos: sin marca
- 225 sesiones elegibles, repartidas en los 5 contratos (GC_12-25 a GC_08-26).
- En la ventana de la celda base: mediana de 4.633 ticks (P10 3.021, P90 8.438); **0 %** de sesiones con menos de 100 ticks; salto máximo entre ticks consecutivos: 60 ticks (< 100).
- Spread de libro mediano: **3 ticks en la ventana y 3 ticks en todo el día** (el costo de cruzar el libro ya está incluido en los netos).

## B1 — Robustez de la celda base: cumple R1 a R4
| Regla | Resultado |
|---|---|
| R1: neto > 0 con 2 ticks extra de deslizamiento en el 70 % y en el 30 % | +19,8 (89 op.) y +18,2 (39 op.) ✓ |
| R2: sin las 5 mejores sesiones | +13,3 ✓ |
| R3: ≥ 6 de 8 vecinas con el mismo signo | 8 de 8 (z entre 0,35 y 2,66) ✓ |
| R4: mayoría de contratos con ≥ 15 operaciones positivos | 5 de 5 ✓ (+9,1 / +21,9 / +43,1 / +26,7 / +19,0) |

- Por mes: positivo en 10 de 11 (octubre de 2025: −9,5). Febrero de 2026 aporta +94,2 con 11 operaciones. Sesiones con neto positivo: 65 %.
- **Descomposición.** «Corto sin condición» a las 04:15 (225 operaciones): **+11,9 ticks**; con la condición «tras subida»: **+21,3**; espejo «largo tras bajada» (95 op.): **−4,5**. Es decir, una parte importante del efecto es un corto horario sin filtro, y la condición añade ≈ 9 ticks.
- La predicción registrada (que la celda base fallaría al menos una regla) **no se cumplió**.

## B2 — Barrido de entradas y salidas (2.100 variantes, tick a tick)
- Mejor `z` de dirección sobre la rejilla completa: **4,59** (corto, 04:15, 15 min, objetivo 50, sin stop; +14,0 ticks) frente a q95 del nulo de 3,39: **p_max = 0,0003**.
- 279 de 2.100 variantes tienen z > 2 y el 42 % tiene neto medio positivo. Todas las mejores variantes son la misma franja 04:15 con condición mínima (≥ 1 tick) y holdings 15 a 45; no hay una variante que destaque sobre las demás.
- **Selección en el 70 % y réplica en el 30 %:** elegida 04:15, ≥ 1 tick, 45 min, stop 50, objetivo 50 (z IS 4,18). En el 30 % reservado: z = 1,47, **p = 0,079**, neto medio +7,9 ticks (39 op.). No cumple el criterio.
- **Decisión pre-registrada:** *ninguna variante se distingue de la celda base*. La celda base sigue siendo el único candidato; los stops y objetivos no mejoran de forma comprobable.

## Lo que hay que tener en cuenta
1. **No es evidencia independiente de la etapa A.** La celda base se eligió en la etapa A (de 1.059 celdas) con estos mismos datos, y el 30 % reservado de B1 es el mismo de la réplica de la etapa A. El `p_max` de B2 es condicional a esa selección. El único p honesto sobre «hay algo en GC» sigue siendo el de la etapa A (0,016, y 0,031 en la réplica) y no resiste Bonferroni entre los 4 activos.
2. **Muestra reservada pequeña.** 39 operaciones fuera de muestra en la última ventana.
3. **Hipótesis post hoc, sin probar.** La ventana de la celda base (entrada 04:17 CT, salida 04:32 CT) equivale a 10:17–10:32 hora de Londres tanto en invierno como en verano, es decir, **abarca el inicio de la subasta LBMA de oro de la mañana (10:30)**. Las vecinas que cruzan ese momento (04:15 con 30 y 60 minutos) tienen z más altos que las que no (04:00 con 15 minutos: z = 0,35). Es una explicación económica plausible, pero se formuló después de ver los datos.
4. **Datos parciales.** Los datasets de GC son «partial contract-month slices»; EF0 los marca no elegibles. Auditoría B0 sin marca, pero eso no certifica la serie.

## Lectura
Con estos datos, la celda GC 04:15 CT «corto tras subida» es robusta a los controles que se pre-registraron y no mejora con stops, objetivos ni otras franjas. Sigue siendo exploratoria: la única forma de convertirla en evidencia es probarla con datos que no se usaron para elegirla (etapa C).
