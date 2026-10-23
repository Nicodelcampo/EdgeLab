# Pre-registro — integridad de U1-CRUZADO y prueba fuera de muestra en USATECH 2023–2025 (2026-10-23)

Estado: VIGENTE — registrado antes de correr. OK de Nico en el chat (2026-10-23) para los pasos 1 y 2 de
`REVISION_ERRORES_Y_PLAN_U1_CRUZADO.md`.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Regla U1-CRUZADO congelada: `MANIFIESTO_U1_CRUZADO.md`. Kernel `tools/kaggle_grilla/kernel_u1_cruzado.py`, modos `INTEGRIDAD` y `OOS_US`.

## Paso 1 — Integridad
Sobre los meses de desarrollo (2025-08 → 2026-03 y 2026-04 → 09), sin P&L nuevo de la regla.

| control | qué se mide | pasa si | si no pasa |
|---|---|---|---|
| Alineación al segundo | correlación de retornos por segundo CFD↔NQ, desfasajes de −20 a +20 s (30 días por tramo) | pico en ≤ 0 s (NQ lidera o empate) | **STOP**: posible look-ahead; no se abre nada |
| Placebo | 5 semillas: momentos al azar de la misma sesión (≥ 30 min de la señal), dirección al azar, misma geometría en NQ | media del placebo ≤ +2 pts/op y al menos 15 pts debajo de la regla | **STOP**: el resultado viene de la geometría o del simulador |
| Latencia | entrar 1, 2 y 5 min tarde con los mismos niveles | con 1 min la media sigue > 0 | no frena; se informa como fragilidad (la operación en vivo necesita latencia baja) |

## Paso 2 — Fuera de muestra: USATECH 2023-01-01 → 2025-07-31 (nunca usado en la familia)
- **Qué se corre:** la regla tal cual (T1 y T3), P&L neto en el CFD con la fricción de NQ. Ya se verificó que el P&L en NQ es ≈ el del CFD.
  - Dos tramos por memoria: 2023-01 → 2024-03 y 2024-04 → 2025-07. Se analizan juntos.
- **Decisión:** lote de 2 (T1, T3) = **un paso de LORD++ de la familia**, el paso 3.
  - Los pasos anteriores, sin rechazo: el lote de v1.4 y U1-B. El α del paso 3 es ≈ 0,00189.
  - Se aplica Simes del lote y, si rechaza, BH adentro (`escalera.probar_lote`). El p es el unilateral por sesiones (`resumen_sesiones`).
- **Lectura por el principio de edges actuales:**
  - **Confirma:** evidencia fuerte antes del holdout.
  - **No confirma con media > 0:** consistente pero sin potencia.
  - **Media ≤ 0:** la idea no funcionaba en 2023–2025. No la mata, porque buscamos edges actuales, pero baja la prioridad y se informa.
- **Riesgo:** drawdown máximo, peor día, peor racha y percentil 1 por ejecución, para el diseño de tope del paso 3.
- **Pruebas:** 2 (`u1_cruzado/oos_us`). La integridad no selecciona nada; se reporta completa.

## Resultado (2026-10-23) — archivos en `u1/integridad_oos/`

### Paso 1 — Integridad: PASA en los dos tramos
| control | 2025-08 → 2026-03 | 2026-04 → 09 | regla |
|---|---|---|---|
| Alineación (pico) | 0 s (corr 0,71) | 0 s (corr 0,72) | ≤ 0 s ✔ |
| Placebo (media de 5 semillas) | T1 −12,7 · T3 −10,6 | T1 −1,4 · T3 +1,2 | ≤ +2 y ≥ 15 debajo de la regla ✔ |
| Latencia: 0 / 1 / 2 / 5 min, T1 | +16,8 / +16,2 / +16,4 / +18,7 | +21,1 / +24,1 / +23,6 / +27,2 | 1 min > 0 ✔ |

Sin look-ahead entre feeds; el resultado no viene de la geometría ni de la latencia.

### Paso 2 — Fuera de muestra USATECH 2023-01 → 2025-07: NO CONFIRMA
| ejecución | ops | media neta | IC90 | p | acierto | peor | drawdown máx | peor día |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| T1 | 156 | +0,06 | [−9,0, +8,3] | 0,51 | 78 % | −318,7 | −744,5 | −549,4 |
| T3 | 157 | −4,55 | [−15,6, +6,3] | 0,76 | 74 % | −393,0 | −1.465,8 | −500,3 |

- **LORD++ paso 3** (α = 0,00189): Simes 0,76, sin rechazo. El estado queda en `oos_eval.json`.
- **Por año (T1):** 2023 −2,0 (24 ops) · 2024 −10,3 (50) · 2025 enero–julio +7,0 (82). 18 de 26 meses positivos.
- **Lectura por el principio de edges actuales:** en 2023–2024 no funcionaba; desde 2025 y en todo el desarrollo
  (2025-08 → 2026-09, +17 a +28) sí.
  - **Dos explicaciones posibles:** un régimen actual, o que U1 se eligió en datos recientes (selección).
  - Sin datos nuevos no se pueden separar: **la única prueba que las distingue es el forward.**
- **Frecuencia:** 5 señales por mes en 2023 → 2025-07, contra ≈ 20 por mes en el desarrollo. Falta verificar, sin mirar P&L, si
  cambió la densidad del feed de Dukascopy (ticks por día y velas M1 con huecos) o la volatilidad: es parte del riesgo de feed.
- **Cola:** una sola operación pierde hasta −393 pts. Antes de cualquier holdout hace falta el tope de stop (paso 3 del plan).
