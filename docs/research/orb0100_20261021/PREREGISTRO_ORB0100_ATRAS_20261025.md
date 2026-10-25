# Pre-registro — ORB0100 «hacia atrás»: la celda congelada sobre USATECH 2023-01 → 2025-08

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `ORB0100`. Etapa del embudo: **EF4** (confirmación de una celda congelada en datos que la familia no usó).
Origen: `docs/research/RELANZAMIENTO_ANALISIS_VIEJOS_20261025.md`.

## 1. Por qué
La celda congelada fue positiva en los tres tramos de NQ (IS 2025 +5,5; OOS 2026T1 +15,4; réplica abr–sep +6,85 pts/op con costos
MNQ), ninguno significativo solo: la réplica dio NO_CONCLUYENTE (IC 95 % [−6,7; +20,7], n 92). Con la escalera de hoy eso es
SIN_POTENCIA, no muerte. USATECH de Dukascopy del 2023-01-03 al 2025-08-04 es anterior a todo lo que ORB0100 miró (su IS empieza el
2025-08-05): es un fuera de muestra hacia atrás, sin tocar la réplica (ya consumida) ni el holdout.

## 2. Regla (congelada, `tools/orb0100/orb0100_v2.py::senales` y `::operar`, sin cambios)
Rango 01:00–01:15 ET; primera vela de 5 min que cierra fuera (hasta las 16:00); sólo a favor del VWAP de la sesión (reinicio 18:00 ET);
entrada al cierre de esa vela; SL en el otro lado del rango; TP 1,5 R; cierre forzado 16:00 ET; resolución con M1 (SL antes que TP en
la misma vela). Diferencias declaradas: (a) el VWAP del CFD se pondera con el volumen de cotizaciones de Dukascopy, no con volumen de
operaciones; (b) `operar` corre con tick 0 y comisión 0, y se resta la **fricción canónica de NQ** (`edgelab/costos.py`: 1,5455 pts
por viaje; adversa 2,0455), más dura que la usada en la réplica (0,62 + 2 ticks ≈ 1,12 pts).

## 3. Datos
USATECH (Dukascopy, mid bid/ask), sesiones 2023-01-03 → 2025-08-04, `edgelab/research/fuentes_ticks.py`, kernel en Kaggle
(`tools/kaggle_grilla/orb0100_atras_main.py`). Nada del holdout.

## 4. Estadístico y decisión (una sola prueba)
- Media neta por operación, bootstrap de sesiones (20.000), p unilateral (H1: media > 0), IC90, MDE.
- Paso de LORD++ de la familia ORB0100 **reservado antes de correr**: t = 1, nivel **0,010937** (`docs/research/LIBRO_LORD.json`,
  reserva `ORB0100::ORB0100-ATRAS`).
- **A FAVOR** si p ≤ 0,010937 y media adversa > 0. **EN CONTRA** si media ≤ 0 y MDE ≤ 5 pts (la mitad del efecto medio de NQ).
  Si no, **NO_CONCLUYENTE** con el MDE. Por año se reporta descriptivo; no se elige subperíodo.
- A FAVOR no es edge: la familia sigue al holdout a N fijo por el protocolo de apertura. EN CONTRA mata la celda en este período y
  este instrumento, no el horario.

## 5. Justificación económica
01:00 ET es la apertura de Europa: flujo nuevo después de la calma asiática. Si la ruptura del primer rango europeo a favor del VWAP
tiene continuación, TP 1,5R se cumple lo suficiente para pagar los SL.

## 6. Cómo podría refutarse
Media neta ≤ 0 con potencia en 2023–2025; o positiva sólo por un año.

## 7. Riesgos y multiplicidad
- Registro global `orb0100_20261021/atras_usatech` (1 prueba) antes de correr. Multiplicidad de la selección de la celda: la absorbe
  el paso de LORD++ (es la misma celda congelada de la réplica, no una nueva elección).
- El NQ de 2023 cotizaba a 11.000–16.000: los puntos valen menos que en 2025–2026; se reporta también el R bruto medio.
- El CFD no es el futuro (nocturno de Dukascopy con spread más ancho; el costo canónico es el del futuro).
- sha256: `tools/kaggle_grilla/orb0100_atras_main.py` `fc80c2ccc66bce88a7ebc0cff8076044709cb485ddb88e840faa90735e20ac26` ·
  `tools/orb0100/orb0100_v2.py` `657a891a72298bebbe5bf9cf35876467ef29c9ae3febe31eb8e1501e3a0d3f63`.

## Resultado (2026-10-25, kernel `nicolasbuttaro/orb0100-atras`, código `2624a5d9…`; JSON `ORB0100_ATRAS.json`)
| n (sesiones) | media neta pts/op | IC90 | p | MDE | media adversa | bruto pts/op | R bruto | acierto |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 447 | **−1,01** | [−3,25; +1,22] | 0,77 | 3,36 | −1,51 | +0,54 | +0,11 | 44,5 % |

Por año: 2023 −0,49 (n 178) · 2024 +0,67 (176) · 2025 hasta ago −5,16 (93). Largos −1,25, cortos −0,67.
Paso de LORD++ resuelto (`ORB0100::ORB0100-ATRAS`, nivel 0,010937, p de Simes 0,77): no rechaza.
**Veredicto pre-registrado: EN CONTRA** (media ≤ 0 con MDE 3,36 ≤ 5). La celda congelada no tuvo ventaja neta en USATECH
2023-01 → 2025-08. Lectura con alcance: el R bruto es +0,11 (positivo), pero en esos años el NQ cotizaba más bajo y el rango de
01:00–01:15 era más chico en puntos, así que la fricción canónica (1,5455 pts, fija en puntos) pesa más por operación. Mata la celda en
este período e instrumento; no mata el horario ni la regla escalada por volatilidad (NO MEDIDO). Junto con la escalera del 2026-10-22
(SIN_POTENCIA y concentración en 5 operaciones), ORB0100 queda **sin candidato**: no se abre su holdout.
