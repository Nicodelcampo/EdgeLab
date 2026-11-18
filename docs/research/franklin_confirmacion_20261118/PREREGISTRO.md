# Franklin en instrumentos nunca medidos: YM, MidCap (EMD), Russell (RTY) y oro (GC) (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea y se cuenta antes de correr.
- **Pedido de Nico:** «vamos a hacer los 4, uno por vez, explorando e indagando a fondo». Es el punto 1: la canasta T + Franklin (+ SOM).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. **Etapa EF5** (confirmación en datos no
  usados). **Familia:** `FRANKLIN`.
- **Herramienta:** `tools/m1_largo.py correr … franklin <INST>` (sin cambios) y `analizar_franklin_nuevos`.

Antecedentes: `docs/research/m1_largo_20261117/RESULTADO_FRANKLIN_E_INDICES.md`.
- **Lo medido:** Franklin bruto +0,195 R en 2006–2011 (NQ + ES, la prueba), +0,063 en 2012–2019 y +0,125 en 2020–2025. Holdout
  terminal (desde oct-2026) con 28 operaciones, +0,27 R, NO_CONCLUYENTE.
- **Hallazgo de la exploración de hoy:**
  - las mediciones de M1 largo de T, Franklin y SOM usaron años completos 2006–2025, así que **el holdout A5 de esas tres familias
    ya está mirado** y no sirve para confirmar;
  - para Franklin quedan instrumentos nunca medidos (YM, EMD, RTY y GC); T y SOM ya se midieron en los cinco índices.
- **Auditoría del código** (`estrategias_scrapeadas.franklin_variantes` y `_sesgo_franklin`):
  - causal: Londres 03:00–09:30 conocido desde las 09:30, VWAP hasta la vela de decisión, decisión al cierre de la vela de las 09:59
    (K48 OK);
  - riesgo inicial = extremo 09:30–10:00;
  - stop en su nivel salvo hueco (K40 OK);
  - ATR sólo de días previos.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6.
- §2: datos con `tools/datos.py`; M1 de futuros (calibración de Franklin en NQ/ES con el mismo motor).
- §3: R bruto con el riesgo inicial; neto con mini y micro; costos de `costos.py` (EMD estimado dentro del permiso K33 de este
  pre-registro).
- §4: potencia al nivel LORD; K38 (regla de un tercero en instrumentos que su autor no usó).
- §6: K45–K48.

Potencia previa: `holdout_ventanas.plan_potencia("fijo", 0,06, 1,38, n≈7.000, alfa=0,0109)` → potencia 0,91 (n necesarias 5.197).
- **Efecto:** conservador, la mitad del bruto de todos los períodos. Con la mitad del de los años limpios (0,0975), la potencia es
  1,00.
- **Desvío:** el del R bruto de Franklin en NQ (1,38).
- **N:** ≈ 8,8 operaciones por mes por instrumento.

## 1. Justificación económica
- **El sesgo:** a las 10:00 de NY, un precio arriba del máximo de Londres y del VWAP de la sesión indica que el flujo de la apertura
  de EE. UU. confirma la dirección que Londres no pudo sostener; abajo del mínimo y del VWAP, lo contrario.
- **Por qué debería transferir:** si el mecanismo es la transferencia de flujo entre sesiones y no una particularidad del Nasdaq, tiene
  que aparecer en otros índices de EE. UU. y en el oro, cuyo mercado principal es Londres.

## 2. Datos (nunca usados para Franklin)
- **YM:** 2006-01-06 → 2025-07-31. **EMD:** 2006-01-09 → 2025-07-31. **RTY:** 2017-07-10 → 2025-07-31. **GC:** 2008-01-02 →
  2025-07-31.
- **Fuente:** M1 real de futuros de NT8 (copia verificada de `tools/datos.py`, lector que corta en la frontera). Ningún dato posterior
  al 2025-07-31.
- **Regla:** la celda que fue al holdout, «1000|rango|ninguno» (`reels_20261116/FRANKLIN_MEJORAS.json`), sin cambios.

## 3. Prueba (una vez)
- **Estadístico:** R BRUTO medio por operación, juntando los cuatro instrumentos, con EE agrupado por fecha (`a5.cluster`). P
  unilateral.
- **α:** nivel LORD++ reservado para `FRANKLIN::CONF_NUEVOS_20261118` antes de calcular.

**Veredicto:**
- **CONFIRMADA:** p ≤ nivel, media > 0 y ≥ 60 % de los instrumento-año con media positiva. Se cuenta por instrumento-año para que
  el nivel distinto de cada instrumento no se mezcle en el año (lección de ASIA del mismo día).
- **REFUTADA:** media ≤ 0, o cota superior unilateral al 95 % < 0,04 R (menor que la fricción típica en R de NQ 2020–2025).
- **NO_CONFIRMADA:** cualquier otro caso.

**Descriptivo** (no decide): por instrumento y época; neto con mini y micro (YM→MYM, GC→MGC; RTY y EMD sin micro en la tabla);
subconjunto con fricción ≤ 0,08 R.

## 4. Cómo podría refutarse
- **Media bruta ≤ 0 o menor que lo útil, con potencia:** Franklin es una particularidad de NQ/ES; la canasta se queda con T y SOM.
- **Confirma en bruto pero el neto es negativo en todos:** el mecanismo es real, pero sólo es operable en NQ (fricción baja).

## 5. Contador y linaje
- **Contador:** 1 prueba.
  `tools/registro_global.py preregistrado FRANKLIN-NUEVOS FRANKLIN 1 docs/research/franklin_confirmacion_20261118/PREREGISTRO.md`,
  más el commit del registro antes de correr.
- **Linaje:** `FRANKLIN` (ya registrada).
