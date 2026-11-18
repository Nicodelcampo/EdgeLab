# Día de tendencia: predictores causales nuevos (gamma de dealers, calendario, Europa, estructura previa, open drive, amplitud), E0 sin retornos (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea, se cuenta y se commitea el registro antes de construir la tabla.
- **Pedido de Nico:** punto 4 de «vamos a hacer los 4 […] y todo lo que propongas vos también probalo».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF2 en DESC (sólo elige el signo de cada predictor) y EF4 en REP (prueba). **Familia:** `DIA_TENDENCIA_A5`.
- **Herramienta:** `tools/dia_tendencia.py` (reutiliza `fundedsync_tanda2.tabla_dia`, `_auc` y `_logit`; `m1_intradia.leer_m1nt8`;
  `macro_literatura.leer`; `holdout.a5_bloque`).

Antecedentes: F-DIA-TENDENCIA-NO-ANTICIPABLE, F-RUPTURA-VIVE-DEL-DIA-DE-TENDENCIA, GEX1/GEX1b (`GEX1_Y_GEX1B_COMPLETO_20261005.md`).
- **Ya probado y nulo, que no se repite:** rango y eficiencia de la primera hora, volumen relativo, gap alineado, noche, vol20 y
  pronósticos HAR/rugoso. AUC 0,45–0,55 en 4 índices 2012–2026.
- **GEX:** en 757 sesiones del S&P spot, menos gamma dio más amplitud (Holm 0,004–0,02), pero sin señal en la continuación. En MES no
  hubo potencia.
- **Lo nuevo de esta campaña:** clases de predictores que nunca se probaron contra la etiqueta de día de tendencia, en 15–20 años de
  futuros.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6.
- §2: A5 (HOLDOUT y EMBARGO fuera de la tabla, sin etiquetas ni predictores); datos con `tools/datos.py`.
- §4: BH; potencia.
- §6: **K48**, la hora de conocimiento de cada predictor declarada abajo y anterior a la etiqueta.

Potencia previa: REP ≈ 2.700 filas (instrumento × día), ≈ 15 % de días E1.
- **EE del AUC:** ≈ 0,016 (bootstrap por fecha).
- **Potencia:** para detectar AUC 0,55 a un nivel BH ≈ 0,005, ≈ 0,85.
- **Mínimo útil:** AUC ≥ 0,55 (por debajo, un filtro no cambia el resultado de una regla de ruptura).

## 1. Justificación económica (por clase)
- **Gamma de los dealers (GEX, cierre del día previo):** con gamma negativa los dealers cubren en la dirección del movimiento y lo
  amplifican; con gamma alta lo frenan (anclaje). Es el mecanismo canónico del día de tendencia.
- **DIX** (proporción de volumen oscuro de compras): presión institucional acumulada.
- **Calendario conocido de antemano:**
  - vencimiento mensual de opciones (tercer viernes): anclaje al strike, menos tendencia;
  - vuelta de mes: flujos de rebalanceo direccionales.
- **Europa (eficiencia de DAX de 03:00 a 09:00 NY):** un flujo global ya ordenado antes de la apertura persiste.
- **Estructura previa:** NR7 y día interior (contracción → expansión, Crabel), cierre previo en un extremo (urgencia no resuelta) y día
  de tendencia previo (persistencia).
- **A las 10:00:** open drive (Dalton: de 09:35 a 10:00 el precio no vuelve a la apertura) y amplitud (acuerdo de NQ/ES/YM/RTY en la
  dirección 09:30–10:00).

## 2. Etiquetas, predictores y horas de conocimiento (K48)
**Etiquetas** (desenlace de mercado, no de una estrategia):
- **E1:** |cierre − apertura RTH| ≥ 0,8·rango RTH.
- **E3:** desde las 10:00, el precio sigue en la dirección de 09:30–10:00 y la continuación es ≥ 0,6·rango de 10:00 a 16:00.

**Predictores antes de las 09:30** (para E1 y E3):

| Predictor | Definición | Se conoce |
|---|---|---|
| `gex` | percentil del GEX del cierre de d−1 contra sus 250 previos | cierre de d−1 |
| `dix` | ídem DIX | cierre de d−1 |
| `opex` | tercer viernes | calendario |
| `fin_mes` | último o primer día hábil del mes | calendario |
| `nr7` | rango RTH de d−1 = mínimo de 7 | cierre de d−1 |
| `interior` | día interior en d−1 | cierre de d−1 |
| `ubic_prev` | ubicación del cierre de d−1 en su rango, en valor absoluto | cierre de d−1 |
| `tend_prev` | E1 de d−1 | cierre de d−1 |
| `europa_ef` | eficiencia del DAX H1 de 03:00 a 09:00 NY | 09:00 |

**Predictores de las 10:00** (sólo para E3): `open_drive` y `amplitud`.

**Instrumentos:** NQ, ES, YM (2006 → 2025-07) y RTY (2017-07 → 2025-07), M1 real de futuros. GEX y DIX desde 2011-05.

## 3. Prueba (una vez)
- **21 pruebas:** E1 × 9 predictores; E3 × 11 predictores; E3 con un modelo combinado (logística ajustada en DESC).
- **Signo:** se elige en DESC (AUC ≥ 0,5 o su inverso).
- **REP:** AUC con ese signo, juntando los instrumentos, con p unilateral (AUC > 0,5) por bootstrap de fechas.
- **«Sirve»:** BH q 0,10, AUC en REP ≥ 0,55 y el mismo signo en ≥ 3 de 4 índices.
- **Descriptivo:** AUC por instrumento, AUC en DESC y tasa de E1/E3.

**Si algo sirve:** se pre-registra aparte como filtro de T, ORB y Franklin (desenlaces en R, contra las mismas reglas sin filtro).

## 4. Cómo podría refutarse
- **Ninguno sirve con potencia:** el día de tendencia tampoco se anticipa con gamma, calendario, Europa ni estructura previa. La
  palanca sigue siendo perder poco los días sin tendencia.
- **Sirve en DESC y no en REP:** era selección.

## 5. Contador y linaje
- **Contador:** 21 pruebas.
  `tools/registro_global.py preregistrado DIA-TENDENCIA DIA_TENDENCIA_A5 21 docs/research/dia_tendencia_20261118/PREREGISTRO.md`,
  y el commit del registro antes de construir la tabla.
- **Linaje:** `DIA_TENDENCIA_A5` ← `FUNDEDSYNC` (L3 de tanda 2) y `GEX`.
