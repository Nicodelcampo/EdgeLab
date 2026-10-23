# Pre-registro — tope de stop de U1-CRUZADO y densidad del feed (2026-10-23)

Estado: VIGENTE — registrado antes de correr. OK de Nico en el chat («Si») a los dos pasos que quedaban antes del holdout
(`REVISION_ERRORES_Y_PLAN_U1_CRUZADO.md`; el resultado del fuera de muestra está en `PREREGISTRO_INTEGRIDAD_Y_OOS_U1_CRUZADO.md`).

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Kernel `tools/kaggle_grilla/kernel_u1_cruzado.py`, modos `TOPES` y `DENSIDAD`. Tope: `u1_cruzado.aplicar_tope`.

## A. Densidad del feed (target-free, sin P&L)
- **Qué se mide** (USATECH 2023-01 → 2026-09):
  - por día: ticks, minutos con datos, velas M1 con hueco (OG/VI) y rango del día;
  - por trimestre: señales U1.
- **Pregunta:** el salto de ≈ 5 a ≈ 20 señales por mes, ¿acompaña a la volatilidad (mercado) o a la densidad del feed (ticks o
  minutos por día, sin cambio de rango)?
- **Lectura fijada:**
  - si las señales por mes siguen al rango del día y no a los ticks por día, es mercado;
  - si siguen a los ticks y no al rango, es feed: riesgo de que U1 dependa de cómo cotiza Dukascopy, y la paridad con el feed en
    vivo pasa a ser bloqueante.

## B. Tope de stop (sólo con datos ya usados)
- **Variantes** (`u1_cruzado.TOPES`): sin tope; tope en puntos 50 / 75 / 100 / 150; tope en múltiplos de la distancia al objetivo
  2× / 3× / 4×. Cada una con T1 y T3: 14 pruebas nuevas, `u1_cruzado/topes`.
- **Datos:**
  - **Para elegir:** NQ con la señal del CFD, desarrollo 2025-08 → 2026-03 (P1) y 2026-04 → 09 (P2).
  - **Sólo informativo:** USATECH 2023-01 → 2025-07, ya visto, con los mismos topes. No se usa para elegir.
- **Regla de elección (fijada ahora):**
  1. **Elegibles:** variantes con media neta > 0 en P1 y en P2, y en cada período al menos el 50 % de la media sin tope de esa
     misma ejecución.
  2. **Orden:** por P&L total de P1 + P2 dividido por |drawdown máximo| de P1 + P2 (retorno sobre drawdown).
  3. **Desempate:** el tope más amplio (menos ajuste), y T1 antes que T3.
  4. **Resultado:** UNA regla congelada (ejecución y tope) para el holdout. Si ninguna es elegible, no hay holdout: se informa.
- **Lo que no se hace:** elegir con 2023–2025, ni cambiar la grilla de topes al ver resultados.

## Resultado B — tope de stop (2026-10-23), archivos en `u1/topes/`
Medias netas en NQ, por período (P1 / P2), en pts por operación:

| tope | T1 | T3 | peor operación T3 | peor día T3 | elegible (T1 / T3) |
|---|---|---|---:|---:|---|
| sin tope | 16,8 / 21,1 | 21,5 / 28,4 | −218 | −264 | (referencia) |
| 50 pts | 5,5 / 2,4 | 11,1 / 0,6 | −54 | −153 | no / no |
| 75 pts | 1,3 / 9,7 | 4,6 / 8,8 | −79 | −228 | no / no |
| 100 pts | 0,5 / 17,0 | 4,5 / 20,1 | −102 | −257 | no / no |
| 150 pts | 3,8 / 19,9 | 8,5 / 24,3 | −152 | −220 | no / no |
| 2× distancia al objetivo | 0,7 / 19,2 | 16,9 / 19,5 | −192 | −141 | no / sí |
| 3× distancia al objetivo | 17,1 / 17,5 | **21,3 / 27,3** | −218 | −188 | sí / **sí (elegida)** |
| 4× distancia al objetivo | 16,9 / 21,6 | 22,0 / 28,9 | −218 | −232 | sí / sí |

- **Por la regla, la elegida es `E1A/T3` con tope de 3× la distancia al objetivo:** mayor retorno sobre drawdown (8,17).
- **Pero no cumple el propósito del tope.** La peor operación sigue en −218 pts, porque el tope es relativo y en expansiones
  grandes la distancia al objetivo también lo es.
- **Todo tope fijo en puntos (50 a 150) borra el resultado en P1.** El edge depende del stop amplio: gana seguido y pierde poco y
  grande. No hay un tope en puntos que conserve el edge y acote la pérdida.
- **Consecuencias:**
  - no hay pérdida máxima estructural en puntos, así que el holdout no puede usar seguimiento secuencial: sólo prueba única a N fijo;
  - el riesgo por operación se controla con el TAMAÑO (MNQ: la peor operación de −218 pts son ≈ 436 USD por contrato) y con un
    límite diario de la cuenta, no con el stop.
- **Fuera de muestra 2023–2025 con topes (informativo, no elige):** todos ≈ 0 o negativos en el segundo tramo. Igual que sin tope.
