# REGIMEN-FORWARD, enmienda: Z-banda como serie separada de la vigilancia forward (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de cualquier lectura forward (no hay sesiones forward todavía: el dataset sellado sigue en la v7 del
2026-11-16). No cambia la canasta T+R ni sus reglas de decisión.
- **Pedido de Nico:** «pre-registrá Z-banda como serie separada en la vigilancia forward».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF5 (forward).** **Familia:** `FUNDEDSYNC`.
- **Herramienta:** el kernel forward (`tools/kaggle_grilla/fundedsync_main.py::operaciones_zbanda`, activado por `FW_ZBANDA=1` en
  `tools/fundedsync_cadena.py forward`) y `tools/regimen_forward.py` (serie `Z_BANDA`). La cartera B excluye los módulos `ZB_*`.

Antecedentes: Z-PICO y `z_pico_20261119/RESULTADO_RAPIDA_Y_SEVERIDAD.md` (dosis-respuesta de severidad en NQ/ES/RTY; banda de 9 configuraciones
equivalentes; NQ 2018+ +0,32 R/op promedio por mes, p < 0,001; correlación diaria ≈ 0 con T y R).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia del forward, K40, K49, K51, K55/K56).

Diagnóstico de mecanismo: la banda son las 9 configuraciones de severidad moderada (cubeta/EMA 10/30, 15/20 y 30/10 × eficiencia 35/45/55),
≈ 230 operaciones cada una en NQ desde 2018 (ninguna celda casi vacía), elegidas porque producen el mismo número de operaciones y el mismo R;
no se elige una variante: la serie es su promedio diario.

Potencia previa: zbanda_dias.csv: 2.5 ops/mes, R/op +0.262, sd 1.15, n para decidir 120, 48.8 meses → OK (desarrollo NQ 2018-01 → 2026-09, días con
operación de la banda).

## Justificación económica
- Después de un día de tendencia limpio (ninguna cubeta de la sesión toca la EMA de cubetas y el día es eficiente), el día siguiente
  continúa: flujo que persigue la tendencia y cobertura de opciones que la refuerza. Sin correlación diaria con T ni con R: diversifica.

## Regla congelada
- Cada configuración de la banda corre Z de fábrica salvo cubeta/EMA/eficiencia; NQ (en forward: USATECH sellado con costos de NQ).
- R de cada operación = (resultado con stop de catástrofe 0,25 × ATR20 − fricción) / (0,25 × ATR20), con **ATR20 = media de los rangos de las
  20 sesiones CME previas** (`atr20_ses`, igual a `tools/m1_largo.py::atr20`). Serie diaria = promedio de las configuraciones que operaron.

## Vigilancia (e-procesos, válidos mirando cuando sea; datos desde la sesión del 2026-11-14)
| Serie | Edge (H0 E ≤ 0): EDGE si e ≥ 20 | Futilidad: SUSPENDER si e ≥ 10 con mu0 | Corte por drawdown | Cotas |
|---|---|---|---|---|
| Z_BANDA (por día con operación) | EProceso(0) | 0,13 (la mitad del desarrollo) | −13 (≈ 2 × el peor del desarrollo, −6,5) | [−3; +8] |
- **Decisión:** EDGE con ≥ 30 días → candidata a sumarse a la canasta (versión nueva, pre-registro aparte). Futilidad o drawdown → SUSPENDER.
- **Cómo podría refutarse:** futilidad o drawdown antes de EDGE.
- **Contador:** 1 prueba en `FUNDEDSYNC`.

## Corrección de implementación (no cambia ninguna regla)
- El kernel forward calculaba `atr20` con el rango RTH (09:30–16:00), herencia de PREREGISTRO_TANDA2 L2. R y Z se validaron con el ATR20 de la
  sesión CME completa (más grande). Se agregó `atr20_ses` y `regimen_forward.py` lo usa para R y Z_BANDA (frena si falta); el `atr20` RTH queda
  para la cartera B, que se pre-registró así. Sin sesiones forward leídas, nada se midió con el ATR equivocado.
