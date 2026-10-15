# Resultados de la fase D (desarrollo) — filtros sobre `HA` (F1A, 100T, ES, 299 sesiones)

Fecha: 2026-10-15 · Estado: **DESARROLLO sobre ES (datos ya quemados para confirmar, HOLDOUT-A3 regla 1 y 4)**. No es evidencia confirmatoria. NQ, YM y holdout (≥ 2026-10-01) **no se abrieron**.
Autorización: Nico, "sí a las 4" (Adenda D §12). Manifiesto: `MANIFIESTO_PASADA3_CONFIRMATORIA_CORREDOR_20261015.md` (+ §13) y `ADENDA_D_DESARROLLO_FILTROS_CORREDOR_20261015.md` (+ §13).
Procedencia: kernel Kaggle `edgelab-es-corridor-dev-events-v1` (id 138900273, v1, sin GPU ni internet); script generado por `tools/corridor_pass2/build_dev_script.py` (Pasada 2 sha256 `10e8fa9f22693b9269754e73b8fafe18b7694ccc70702f9a843ebea7b584c0ec` + adenda + `DET_NT8`); análisis local `tools/corridor_pass2/dev_filters_analysis.py`. Tabla de eventos: `data/corridor_dev/ES_CORRIDOR_DEV_EVENTS.csv` (local, gitignorada).

## 1. Integridad
- **Regresión contra Pasada 2 (DET_PY, 100T, preset 1, F1A, purgado):** ALL N=1.793, acierto 54,10 % — **idéntico** a Pasada 2. STEEP N=847 / 55,49 % vs 852 / 55,40 % de Pasada 2: la diferencia se debe a que Pasada 2 calculó la mediana de pendiente sobre todos los eventos (todas las familias) y acá sobre F1A; documentado.
- **Paridad de detector:** `DET_NT8` (ATR = SMA del rango, como `EmaCorridorTrend.cs`) vs `DET_PY` (EMA del true range): zonas 8.617 vs 8.604 (preset 1), resultados casi iguales (54,37 % vs 54,10 % ALL). **La diferencia de ATR no cambia las conclusiones.** El port sigue sin prueba de paridad zona a zona contra NT8.
- Datos: 299 sesiones, 305.388.908 ticks, volumen real por tick disponible; el parquet también trae `aggressor`, `bid_ticks`, `ask_ticks` (no usados: política de agresor pendiente, D13).
- 0 errores de extracción de features. Prueba de prefijo vs streaming de las features: **pendiente** (recomendada por el auditor externo).

## 2. Línea base sin filtro (RTH 08:30–15:30 hora de Chicago real, purga `no_overlap`, P&L con timeouts marcados a mercado, fricción ES 3,546 ticks)
| Detector / preset / estrato | N | sesiones | acierto (resueltos) | % timeouts | bruto | **neto** [IC95 por sesiones] |
|---|---|---|---|---|---|---|
| NT8 P1 ALL | 3.456 | 289 | 53,7 % | 55 % | +1,10 | **−2,45** [−3,54; −1,40] |
| **NT8 P1 STEEP (= HA)** | 1.728 | 247 | 54,8 % | 61 % | +1,54 [−0,26; +3,32] | **−2,01** [−3,81; −0,21] |
| NT8 P2 ALL / STEEP | 4.171 / 2.089 | 290 / 262 | 51,6 % / 53,3 % | 51 % / 57 % | +0,28 / +0,49 | −3,27 / −3,06 |
| NT8 P3 ALL / STEEP | 4.888 / 2.444 | 291 / 268 | 51,5 % / 52,8 % | 44 % / 51 % | +0,66 / +0,92 | −2,89 / −2,63 |
| PY P1 / P2 / P3 STEEP | 1.728 / 2.090 / 2.445 | 247 / 262 / 268 | 54,8 / 53,3 / 53,0 % | 61 / 57 / 51 % | +1,52 / +0,46 / +1,00 | −2,03 / −3,09 / −2,55 |
Umbral de pendiente (congelable): mediana de `slope_ticks` en NT8 P1 RTH = **0,362 ticks/barra**.
- Hay un **efecto bruto pequeño y positivo** (+0,3 a +1,5 ticks por operación), pero para HA exacta **su IC95 incluye 0** y es menor que la fricción por un factor de 2–10. El **neto es negativo en todas las variantes** y para HA el IC95 excluye 0 por debajo.
- **Más de la mitad de los eventos son timeouts** (55–61 %): el "acierto sobre resueltos" de Pasada 2 describe sólo ~40 % de las operaciones.
- Las dos mitades cronológicas dan netos parecidos (−2,75/−2,15 en P1 ALL): sin decaimiento claro, tampoco señal.

## 3. Herramientas T1–T5 (población P1 ALL RTH, N = 3.456; walk-forward 5 pliegues con purga y embargo; selección interna por bloques de sesión)
| Herramienta | ΔE (neto, vs sin filtro del mismo test) | retención | pliegues con ΔE>0 |
|---|---|---|---|
| T1 variable simple | −0,40 | 34 % | 0/5 |
| T2 elastic net | +0,16 | 68 % | 2/5 |
| T3 árbol prof. 3 | +0,80 | 32 % | 3/5 |
| T4 LightGBM | 0,00 | 39 % | 2/5 |
| T5 abstención calibrada | **+0,94** | 35 % | 5/5 |
| Baseline continuo (hora, volatilidad, trayectoria, intensidad) — mejor | +0,24 | 75 % | — |
- **Ninguna herramienta lleva el neto a positivo:** el mejor `E_sel` es −1,28 ticks (T5) contra −2,45 sin filtro.
- T5 es el único con signo positivo en los 5 pliegues, pero **decae**: +6,43 (n=40), +1,23 (n=95), −0,91, −2,24, −2,78 (n=193 en el último). Es el patrón típico de selección sobre poco soporte que no se sostiene.
- El baseline continuo hace +0,24 como mucho: **el indicador no agrega información sobre un modelo simple de hora/volatilidad/trayectoria** en esta medición.
- Nulo del pipeline (300 repeticiones): ver §5, **p = 0,239**.

## 4. HB (F2D, 500T, preset 2, ES, RTH, purgado)
NT8 STEEP: N=388 eventos, **sólo 72 resueltos (81 % timeouts)**, acierto 59,7 %, bruto +3,04 [−3,1; +8,9], neto −0,50 [−6,7; +5,4]. Sin potencia; el "N=73" de Pasada 2 era el conteo de resueltos. No se optimiza.

## 5. Nulo del pipeline
300 repeticiones (desplazamiento circular de etiquetas por la serie ordenada de eventos, pipeline completo T1–T5 en cada una; semilla 20261015). Estadístico: la mayor mejora ΔE entre herramientas.
- Observado: **+0,94 ticks** (T5).
- Nulo: media **0,68**, mediana 0,64, p90 1,33, p95 1,64, máximo 2,45.
- **p_pipeline = 0,239**: el pipeline encuentra una "mejora" igual o mayor en ~24 % de los casos sin información en las variables. **No hay evidencia de que algún filtro mejore `HA`** (corte de Adenda D: p < 0,05).
- Salida de la fase (Adenda D §9, caso 3): no se congela filtro; `HA` no tiene mejora demostrada ni siquiera en desarrollo.

## 6. Lectura (alcance preciso)
1. `HA` tal como está definida **no es rentable neta de fricción en ES** y, con timeouts, su efecto bruto ni siquiera es distinguible de cero. Esto vale para el detector, la población, la etiqueta (barrera 1,0H, horizonte 400 barras, entrada al cierre) y la fricción declarados.
2. **Ningún filtro de los probados multiplica el efecto bruto** hasta hacerlo positivo neto. La mejora máxima observada (+0,94 ticks, T5) es 2–3 veces menor que la brecha y no se sostiene en los últimos pliegues.
3. El indicador no aporta sobre el baseline continuo en esta medición.
4. Lo que **no** se cierra: otras etiquetas (objetivo estructural `orig_px`, horizontes distintos), población alternativa de eventos (P1 creación, P3 toques), entradas con menor fricción (límite con trade-through), uso del agresor/bid-ask, y la CNN multiescala de la propuesta del modelo de reversión. Cada una requiere su propio manifiesto.
5. No hay base para abrir NQ/YM con `HA`: confirmar en ellos lo que en ES ya es negativo neto no cambia la decisión económica; sí podría usarse sólo para estimar el efecto bruto si Nico lo pide.

*Aporte al referente:* mide con rigor (timeouts, fricción, purga, validación anidada) que el efecto bruto de `HA` es del orden de +1 tick y no se multiplica con filtros, lo que evita gastar la confirmación en NQ/YM y redirige la búsqueda hacia etiquetas y entradas con otra relación recorrido/fricción.
