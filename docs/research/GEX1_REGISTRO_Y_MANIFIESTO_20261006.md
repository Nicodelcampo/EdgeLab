# GEX-1 — registro de familia y manifiesto de campaña (2026-10-06) — **PENDIENTE DE OK DE NICO (regla STOP)**

NORTH_STAR: `docs/NORTH_STAR.md`, sha256 del cuerpo `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Contexto y fuentes: `docs/research/GEX_FUENTES_Y_EVIDENCIA_20261006.md` (rama `claude/vibrant-clarke-s9z6e2`).

## 1. Registro de familia
- **Familia:** GEX-1 — gamma neto de dealers del SPX como **estado diario ex-ante**. Independiente: no transporta
  resultados, poblaciones, costos ni presupuesto de multiplicidad de otras familias.
- **Variable:** `gex_t-1` = GEX neto de SqueezeMetrics (`DIX.csv`, columna `gex`) de la sesión anterior a la evaluada.
  Se publica después del cierre: para la sesión t sólo se usa el valor de t-1. Derivados congelados: signo
  (`gex_t-1 < 0`) y percentil móvil de 252 sesiones calculado sólo con el pasado.
- **Por qué este estado y no otros (regla de población):** espacio enumerado —
  (a) estado diario del GEX neto [ELEGIDO: única serie larga, causal y gratis; respaldo académico directo];
  (b) estado continuo intradía, distancia a flip/walls [DESCARTADO por ahora: no hay niveles históricos causales free;
  SquawkFlow empieza 2026-07-28];
  (c) eventos de toque/ruptura de walls [DESCARTADO por la misma razón; queda para cuando haya historia propia];
  (d) cruce del flip intradía [DESCARTADO: FirmTape no permite bajarlo y es ex-post].
- **Justificación económica:** con gamma neto negativo, los dealers cubren en la dirección del movimiento (venden en
  caídas, compran en subas) y amplifican; con gamma positivo, cubren contra el movimiento y amortiguan. Baltussen et
  al. (JFE 2021) y Barbon-Buraschi lo documentan como momentum intradía con gamma negativo y reversión con positivo.

## 2. Hipótesis (target-free → información; sin P&L en esta campaña)
Unidad de inferencia: **sesión** (RTH 08:30-15:00 CT). Comparación: sesiones con `gex_t-1 < 0` vs `>= 0`.
- **I1 (amplitud):** rango RTH / volatilidad realizada previa (20 sesiones) mayor con gex<0.
- **I2 (continuación de cierre, Baltussen):** pendiente de la regresión retorno(últimos 30 min) ~ retorno(cierre
  previo → 14:30 CT) mayor con gex<0.
- **I3 (autocorrelación intradía, Barbon-Buraschi):** autocorrelación de retornos de 5 min dentro de RTH más alta con
  gex<0 (momentum) y más baja/negativa con gex>=0 (reversión).
Canales: I2 e I3 se miden en el canal direccional (pendiente/autocorrelación con signo) **y** en el no direccional
(|retorno| de los últimos 30 min, varianza). Se publica la distribución completa por grupo, no sólo medias.

**Cómo podría refutarse:** cada diferencia (gex<0 menos gex>=0) dentro del IC del nulo; o desaparece al controlar por
volatilidad realizada previa (confusor principal: gex<0 coincide con volatilidad alta), comparando dentro de
quintiles de volatilidad previa.

## 3. Datos, ventana y holdout
- ES/MES: ticks NT8 vía `edgelab_data` (sólo sesiones aprobadas), 2025-07 → 2026-09-30.
- Potencia adicional: spot USA500 Dukascopy 2023-01 → 2025-06 (sólo I1-I3, que son de información; sus
  limitaciones aplican: precio CFD, horario igual en RTH).
- SqueezeMetrics `gex` 2011 → 2026 (sólo se usa el tramo con precio intradía disponible).
- **Holdout desde 2026-10-01: no se toca.**

## 4. Nulos, multiplicidad y potencia
- Nulo: permutación de la etiqueta gex<0 entre sesiones **por bloques de 20 sesiones** (conserva la persistencia del
  régimen); 20.000 permutaciones; semilla 20261006.
- Número efectivo de pruebas: 3 hipótesis × 2 canales × 2 fuentes (futuro, spot) = **12**; Holm sobre las 12.
  Se registran en `TRIAL_REGISTRY_GLOBAL.jsonl` al correr.
- MDE: se publica por hipótesis con N sesiones de cada grupo antes de mirar la diferencia.
- Riesgos: GEX naive (signo supuesto); OI de cierre no ve 0DTE; fracción gex<0 puede ser chica en 2025-2026
  (se informa N por grupo antes de correr; si un grupo < 40 sesiones en futuros, I2-I3 se reportan sólo con spot).

## 5. Qué NO hace esta campaña
No busca reglas de entrada/salida ni P&L. Si alguna I pasa con Holm y sobrevive al control de volatilidad, el paso
siguiente (P&L bruto de una regla única pre-registrada, p. ej. continuación de la última media hora sólo con gex<0)
requiere otro manifiesto y otro OK.
