# Enmienda P1 — H1 y H2 sobre la muestra nueva de oro spot (2022-07-01 a 2025-07-31)

Reglas: `docs/research/REVISION_EMBUDO_DISCOVERY_Y_PLAN_ORO_20261004.md` §3.2 y §4 (enmienda P1), escritas antes de cargar estos datos. Herramienta: `tools/barrido_horario_p1_h1h2.py`; salida cruda `etapaP1_H1H2.json`. Una sola corrida, nulo de dirección por sesión (20.000 sorteos, semilla 20261011, unilateral), Holm sobre H1 y H2. No se leyó el 1 de octubre ni nada posterior. La muestra es anterior a los datos con que se eligió la celda (GC 2025-08 a 2026-06): todo fuera de muestra.

**Integridad (condición previa de la enmienda):** `calidad.json` del dataset unificado, 1.323 días, 0 ticks desordenados, 0 bid > ask y 0 precios ≤ 0; el escaneo propio de las 258.524.416 filas da lo mismo. Los cuatro días que debían volver a bajarse (2022-07-06, 07-12, 07-14 y 07-15) pasan los controles. Ninguna sesión se excluyó.

## Veredicto: **ni H1 ni H2 replican**
796 sesiones elegibles (ninguna descartada); spread mediano USD 0,357 (≈ 3,6 ticks de GC), más bajo que el de 2026 (USD 0,57).

| | Operaciones | Neto medio (ticks de GC) | Desvío | Aciertos | z | p (unilateral) | p Holm | Decisión |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **H1** celda congelada (corto tras subida de 15 min) | 419 | **−3,1** | 18,9 | 40,8 % | 1,34 | 0,088 | 0,088 | **No replica** |
| **H2** corto sin condición | 796 | **−2,5** | 18,2 | 41,5 % | 2,82 | 0,0022 | 0,0044 | **No replica** (neto ≤ 0) |

Regla: replica si Holm ≤ 0,05 **y** neto > 0.

## Lectura
1. **H2 tiene una señal direccional bruta pequeña pero no explotable.** El estadístico del nulo (que cancela el costo) da z = 2,82 con Holm 0,0044: en 2022-2025 hay un sesgo vendedor bruto de ≈ **+1,8 ticks por operación** a las 04:15 CT. El costo (spread de ≈ 3,6 ticks más 0,45 de comisión) lo supera, y el neto es negativo (−2,5). El largo sin condición pierde 6,2.
2. **H1 no se distingue del azar** (p = 0,088) y es negativa neta en los cuatro años (2022: −3,4; 2023: −4,0; 2024: −1,7; 2025 hasta julio: −3,9).
3. **El efecto de 2026 no existe en esos cuatro años.** En la ventana del 1 de julio al 30 de septiembre de 2026 el corto sin condición dio +24,1 ticks netos (z = 4,98) y la celda +25,6. En 2022-2025 el sesgo bruto es unas veinte veces menor (≈ 1,8 contra ≈ 30 ticks brutos). Medido en desvíos por operación: 2026 ≈ 0,6; 2022-2025 ≈ 0,1.
4. Por estación de EE.UU. (H2): invierno −3,2 (264 operaciones), verano −2,2 (532). Sin diferencia que sugiera que la franja LBMA mueva el resultado.
5. **Sensibilidad (descriptiva, posterior):** una sola sesión (2025-03-03) tuvo la salida a 1.532 s del instante previsto; excluirla no cambia nada (H2: −2,45; z = 2,90).

## Qué se concluye
- La celda no tiene evidencia fuera de muestra **de largo plazo** (2022-2025): lo que se observa en agosto de 2025 a septiembre de 2026 (selección en GC y réplica en spot) **no se extiende hacia atrás**. Es compatible con un cambio de régimen reciente o con una racha que la selección y la réplica comparten; esta corrida no puede distinguirlo.
- **No se puede afirmar un edge.** Para operar haría falta, como mínimo, entender por qué solo aparece desde mediados de 2025 y confirmarlo en futuros con datos nuevos (octubre en adelante, holdout formal).
- Contador global de pruebas: +2 (campaña `ETAPA-P1-H1H2-spot-2022-2025`).
