# Piloto de soporte de etiquetas para EXP-REV-GRID — resultados

Estado: MEDIDO (desarrollo; solo camino de precios, sin modelo ni indicador)
Fecha: 2026-10-15
Familia / módulo: EXP-REV-GRID
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)
Autorización: Nico, 2026-10-15 ("si") al piloto de descubrimiento propuesto. Aclaración de Nico: **la pista L2 entrena con los pocos datos disponibles; lo que no es L2 entrena con todo el historial de ticks.**

## Qué se midió
Kernel `nicolasbuttaro/edgelab-grid-support-pilot-v1` (id 138919313, release v4, 41 s). ES, descubrimiento HOLDOUT-A3 (2025-07-18 a 2026-03-31): **178 sesiones**, decisiones cada 60 s en RTH (08:30–15:30 hora de Chicago real), ≈415 por sesión; entrada en el primer tick posterior; R / C / ambiguo / timeout / censurado por fin de sesión; se promedian las dos direcciones. **No hay indicador, expansión ni modelo: esto mide cuánto resuelve una etiqueta, no si se puede predecir.** Código: `tools/grid_support_pilot/support_pilot_kernel.py`; resultados completos: `docs/research/grid_support_pilot_20261015/GRID_SUPPORT_PILOT.json`.

## Resultados (fracción de decisiones; `p_eq` con fricción de ES 3,546 ticks)
| X/Y (ticks) | T (s) | R | C | timeout | censurado | resueltos/sesión | `p_eq` | nulo primer paso |
|---|---|---|---|---|---|---|---|---|
| 24/24 | 300 | 0,156 | 0,156 | 0,687 | 0 | 130 | 0,574 | 0,50 |
| 24/24 | 900 | 0,297 | 0,297 | 0,404 | 0,001 | 247 | 0,574 | 0,50 |
| 24/24 | 1800 | 0,377 | 0,377 | 0,242 | 0,003 | 313 | 0,574 | 0,50 |
| **32/32** | **300** | 0,092 | 0,092 | **0,815** | 0 | 77 | 0,555 | 0,50 |
| 32/32 | 900 | 0,220 | 0,220 | 0,559 | 0,001 | 183 | 0,555 | 0,50 |
| 32/32 | 1800 | 0,306 | 0,306 | 0,383 | 0,004 | 255 | 0,555 | 0,50 |
| 32/32 | 3600 | 0,381 | 0,381 | 0,182 | 0,057 | 316 | 0,555 | 0,50 |
| 48/32 | 300 | 0,032 | 0,094 | 0,874 | 0 | 52 | 0,444 | 0,40 |
| 48/32 | 1800 | 0,178 | 0,334 | 0,484 | 0,004 | 213 | 0,444 | 0,40 |
| 48/48 | 1800 | 0,197 | 0,197 | 0,602 | 0,004 | 164 | 0,537 | 0,50 |
| 48/48 | 3600 | 0,279 | 0,279 | 0,376 | 0,066 | 232 | 0,537 | 0,50 |
| 64/32 | 1800 | 0,109 | 0,344 | 0,542 | 0,004 | 188 | 0,370 | 0,33 |
| 64/64 | 3600 | 0,201 | 0,201 | 0,530 | 0,069 | 167 | 0,528 | 0,50 |
| 96/48 | 3600 | 0,092 | 0,308 | 0,531 | 0,069 | 166 | 0,358 | 0,33 |
Episodios independientes aproximados en las 178 sesiones: ≈ 14.950 a T=300 s, 4.980 a T=900 s, 2.490 a T=1800 s, 1.250 a T=3600 s.

## Lectura
1. **La etiqueta propuesta (32 vs 32 ticks a 300 s) resuelve sólo el 18,5 % de las decisiones; el 81,5 % son timeouts.** La economía de ese diseño estaría dominada por el retorno al vencimiento, no por R/C. Mi reserva 3 sobre la revisión de Gemini queda confirmada con datos.
2. **Resolver ≥ 60 % de las decisiones exige horizontes de ≥ 30 min con barreras de 32** (32/32 a 1800 s: 61,7 %) o barreras de 24 a 600–900 s (24/24 a 900 s: 59,6 %). El costo: cuanto más chico el recorrido, mayor el acierto necesario (24/24 → 57,4 %).
3. **El censurado por fin de sesión crece a 5–7 % a 3600 s** (la sesión RTH termina): conviene un horizonte ≤ 1800 s o una regla explícita de cierre.
4. **Equilibrio con fricción:** 32/32 requiere 55,5 % entre resueltos; 48/48 53,7 %; 64/64 52,8 %. Las asimétricas (48/32, 64/32) exigen sólo 4,4–3,7 puntos sobre su nulo de primer paso, pero resuelven mucho menos hacia la reversión (R=3–18 %).
5. **Candidatos para congelar (decisión de Nico/protocolo, no mía):** primaria **32/32 a 1800 s** (resuelve 61,7 %, ≈ 14 episodios independientes por sesión), secundarias 24/24 a 900 s y 48/32 a 1800 s. No usar T=300 s como primaria.

## Límites
- Es la distribución **incondicional** (todas las decisiones RTH, sin expansión): tras una expansión la resolución puede ser mayor. Hay que repetir el conteo sobre la población de decisión elegida.
- El MDE de la tabla en el JSON corresponde a la tasa incondicional entre resueltos y vale 1–2 pp en las asimétricas; **no** es el MDE de una mejora de un modelo sobre su baseline, que depende de la población y de las particiones (calibración ≈ 12 sesiones, tuning ≈ 11).
- No se aplica fricción ni se marca el timeout a mercado: eso es evaluación económica, no soporte.
- Sólo ES; cada instrumento necesita su propia fricción y su propio piloto.

## Entrenamiento: aclaración de Nico y su costo
La pista **L2** entrena con los datos L2 disponibles (≈ 100 sesiones de ES). La pista **sin L2 (ticks)** entrena con **todo el historial de ticks**. Para que esto sea compatible con HOLDOUT-A3 hay que decidir explícitamente si "todo el historial" incluye abril–septiembre de 2026 (la ventana de replicación) y/o otros instrumentos: usarlas para entrenar **consume la replicación de esta familia**. El holdout (≥ 2026-10-01) sigue sellado. Se anota como pendiente de enmienda formal si Nico quiere esa ventana; el piloto usó sólo descubrimiento.

*Aporte al referente:* mide con datos que la etiqueta de 300 s era inviable por falta de resolución y acota los horizontes y barreras donde el modelo de grilla tiene soporte, antes de gastar cómputo.
