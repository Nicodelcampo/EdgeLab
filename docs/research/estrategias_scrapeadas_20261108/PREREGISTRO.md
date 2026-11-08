# Pre-registro — ESTRATEGIAS-SCRAPEADAS (Italian Founder, AlphaZone, FlexingJoe)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-11-08.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa del embudo: **EF2/EF3**. Origen: reels que juntó Nico (2026-11-08). Kemet va aparte (`../gap_continuacion_20261108/`).
Código: `edgelab/research/estrategias_scrapeadas.py`, `tools/kaggle_grilla/estrategias_scrapeadas_main.py`, tests
`tests/research/test_estrategias_scrapeadas.py`. Un kernel por familia (cuenta `nicobuttaro`, datasets compartidos).

## 1. Familias y grillas (reglas tal como se ven; lo que el reel no dice se declara acá)
| Familia | Regla | Grilla | Fuentes (CFD Dukascopy → futuro) | Pruebas |
|---|---|---|---|---|
| ORO_RANGO | Rango 03:00–09:00 Bucharest, OCO en máx/mín desde 09:00, salida 21:00 | stop {rango, medio rango} × salida {21:00, +4 h} | XAUUSD→GC | 4×1×2 = 8 |
| MARTES_DEBIL | Martes RTH cierra < apertura y < SMA40 → compra al cierre; stop 1 ATR diario | salida {miércoles, viernes} | USA500→ES | 2×1×2 = 4 |
| EMA_VWAP | 3 min RTH, mecha cruza VWAP y cierra del otro lado → contra el cruce a la apertura siguiente; sale al cerrar del otro lado de la EMA9 | stop {mecha, 1 ATR, 2 ATR} × horario {RTH, primeras 2 h} | USATECH→NQ, USA500→ES, USA30→YM | 6×3×2 = 36 |
| ORB_EMA20 | OR 09:30–10:00; primera vela 10 min que cierra fuera → dirección; primer toque de EMA20 en 2 min → entrada límite; entradas hasta 15:00 | stop {extremo opuesto, mitad del OR} × objetivo {1R, 2R, cierre} | USATECH→NQ, USA500→ES | 6×2×2 = 24 |

Total **72 pruebas** (canales total 2023-01 → 2026-03 y reciente ≥ 2025-07-01; canal de desarrollo en futuros jul-2025 → mar-2026,
descriptivo). USDJPY (estrategia 4 de Italian Founder) **no se mide**: 6J no tiene spread medido en `edgelab/costos.py`.

## 2. Población
Cada familia mide un evento por día (ORO, ORB, MARTES) o por señal sin solapamiento (EMA_VWAP). Alternativas no medidas: ORB con
entrada directa a la ruptura (ya refutada como familia ORB el 2026-11-08), martes con salida al primer cierre arriba, VWAP con volumen
real de futuros (el CFD sólo tiene volumen de ticks).

## 3. Estadístico y decisión
R por operación = (bruto − fricción canónica) / riesgo. Bootstrap de sesiones (20.000), p unilateral, IC90, MDE; < 30 ops no
evaluable. Tamiz FDR q 0,10 **por familia**. Réplica única abr–sep 2026 en futuros (nominadas o pistas IC90 inf > 0), LORD++.
Simulación por velas con stop antes que objetivo dentro de la vela (conservadora).

## 4. Justificación económica
ORO: la apertura de Londres trae el flujo que rompe el rango asiático. MARTES: reversión de corto plazo bajo tendencia bajista
(sobreventa). EMA_VWAP: el VWAP es referencia de ejecución institucional; un rechazo en la mecha marca falta de aceptación. ORB_EMA20:
continuación del impulso de apertura comprando el primer retroceso.

## 5. Cómo podría refutarse
Sin nominadas con MDE < 0,1 R; nominadas sólo en CFD y negativas en futuros; media R ≤ 0 en réplica; o efecto sólo en 2023–2024.

## 6. Multiplicidad y linaje
Registro global `estrategias_scrapeadas/<familia>/desc`. Linajes: ORO_RANGO, MARTES_DEBIL, EMA_VWAP, ORB_EMA20 ← sin padre medido
(ORB_EMA20 ← ORB_NQ, refutada hoy, n heredado bruto).
