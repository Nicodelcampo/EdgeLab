# ESCALONADAS-M1: la escalera plana de picos en M1 de NQ, ES y YM 2006–2025, con la partición A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «había un indicador de picos de 150t en MNQ, creo que había dado buenos resultados. ¿Te parece hacer una versión en
  M1 para el NQ y MNQ, u otro tipo de variante…, quizás agregándole otros filtros u otras lógicas?».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT. **Familia:** `ESCALONADAS_M1_A5`.
- **Herramientas:** `edgelab/research/escalonadas_m1.py` (contrato de `tablas`; preflight OK: causalidad por disparo y por cortes, motor
  calibrado, kernel SINT) y `tools/a5_campana.py` con `CAMPANA.json`.

Antecedentes: `tools/antecedentes.py "indicador de picos 150 ticks MNQ"` y las actas de ESCALONADAS.
- **MNQ-ESCALONADAS-ESCALAS (`RESULTADO_MNQ_ESCALONADAS_ESCALAS_20260930.md`):** 0/648 celdas sobreviven max-T (ago-25 → ene-26).
  - En 150t las medias quedan cerca de 0 neto.
  - El +0,25 R de febrero fue un caso elegido mirando.
  - Lo único vivo, sin potencia, son las escalas grandes con stop amplio. Con entrada a mercado en la vela siguiente:
    - SL ×2, objetivo 2R: bruto +0,075, control −0,145;
    - SL ×4, objetivo 5R: bruto +0,121, control −0,118, diferencia +0,18 con MDE 0,63 (n 294).
- **ES escalonadas v1/v2 y EURUSD (648 + 450 GC):** sin efecto que sobreviva.
- **Qué agrega esta campaña:** 20 años de M1 y tres índices. Pone a prueba la idea (escalera → ruptura en su dirección) con potencia, en
  lugar de en 6 meses.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v2 — §0–§5.
- §2: el linaje usó 2025-08 → 2026-03 (MNQ/ES ticks) → ventana 2006-01 → 2025-07; calibración contra ticks (K30) antes de correr; K40
  (stop de M1 en su nivel) en el motor.
- §3: todo en R; K36 (detector sin puntos fijos: unidad = rango medio de la vela / 2,5); bruto y neto con fricción en R por época.
- §4: potencia abajo; K38 no aplica (regla propia).

Potencia previa: plan de `holdout_ventanas.plan_potencia` (sin operaciones de desarrollo en M1; efecto de MNQ 150t velas_w2, desarrollo):
- **Sólo NQ** (≈ 5.000 operaciones de holdout, conteo sin retornos en Q1-2010 escalado):
  - con la mitad de +0,075 R (sd 1,4): potencia 0,60;
  - con la mitad de +0,12 R (sd 2,2): 0,61;
  - con la mitad de la diferencia +0,11 (sd 1,6): 0,78.
  - **NO alcanza.**
- **Por eso se agrupan NQ, ES y YM** (≈ 15.000): potencia ≥ 0,95 con la mitad del efecto en las tres lecturas.
- **La regla de apertura** recalcula la potencia con el N real del holdout, contado sin desenlaces, y no abre por debajo de 0,8 (E8).

## 1. Justificación económica
- **El mecanismo:** una serie de picos que no superan al anterior (techo plano o que baja) marca un lado que absorbe: cada intento de
  pasar el nivel fracasa. Cuando el precio se aleja del último pico por la distancia de confirmación, ese lado gana.
- **La operación:** a favor (venta en un techo, compra en un piso). La escala de la vela M1 es mayor que la de 150t, así que la fricción
  pesa menos por R, que es la palanca que dejó viva la campaña de MNQ.

## 2. Espacio de eventos y población
**Espacio** (escalonadas, `escalonadas_det`):
- creación (2.º pico);
- detección (la familia PLANAS cumple sus filtros: es la entrada medida acá);
- toque n-ésimo del nivel;
- ruptura del último pico (fin de la serie);
- vencimiento por hueco;
- estado continuo (hay una escalera activa).

**Elegida:** la detección en tiempo real (confirmación por precio). Ruptura y estado quedan fuera.

**Definiciones:**
- **ESC:** toda serie detectada.
- **ESC4:** detectada con ≥ 4 picos (escalera larga: más intentos fallidos).
- **ESC_VWAP:** del lado del VWAP de la sesión (venta con cierre < VWAP, compra con cierre > VWAP). Hipótesis: la escalera rompe a
  favor del valor de la sesión.

**Controles placebo, causales:**
- **CTRL:** velas elegidas por un hash de su índice, ≈ 1 de cada 250 (la frecuencia de las series), con lado ±1 y la unidad de su
  sesión.
- **CTRL_VWAP:** lo mismo, alineado con el VWAP. Control de ESC_VWAP.
- La primera versión del control (una vela de una sesión pasada por serie) falló la prueba de causalidad y se reemplazó antes de correr.
- La hora no está emparejada: se reporta el reparto horario como descriptivo.

**K36:**
- Los parámetros del detector (ticks de ES 25t) se expresan en u = rango medio de la vela M1 de las 20 sesiones anteriores / 2,5.
- El stop y el objetivo están en múltiplos de ese rango, nunca en puntos.

## 3. Ejecución y medición (motor único `ejecucion.py`)
- **Entrada:** a mercado en el primer tick de la vela siguiente a la detección. ref = cierre + lado·rg, con D ≈ rg = rango medio de la
  vela.
- **Stop y objetivo:** stop sl·D con sl ∈ {1, 2, 4}; objetivo sl·{2, 5}·D. Son 6 ejecuciones, sin BE ni parcial.
- **Tenencia:** 240 velas, o hasta el fin de sesión o un hueco de 30 min.
- **Unidad:** R bruto. El neto resta la fricción canónica del instrumento (NQ, ES, YM) / riesgo.
- **Subconjunto operable declarado:** fricción ≤ 0,08 R.
- **MNQ:** mismo precio que NQ. El neto en MNQ se reporta aparte con su fricción canónica si existe en `costos.py`; si no, queda como
  NO MEDIDO.

## 4. Partición A5, ventana y fases
- **Ventana:** NQ/ES/YM M1 NT8, 2006-01-06 → 2025-07-31. Eventos sin retornos en toda la ventana; desenlaces sólo en DESC y REP.
- **0. Calibración (K30)** en 2025-08-05 → 2026-03-31, ya mirado por el linaje:
  - la misma tabla en ticks reales (Kaggle, `tools/tablas.py lanzar`) contra M1 local;
  - criterio `a5.calibrar_por_sesion` (≥ 30 sesiones comunes, mismo signo, diferencia ≤ 1 EE, corr > 0,5);
  - una celda que no calibra no se nomina; `CALIBRACION.json` se commitea antes de correr.
- **1. DESC:** 36 pruebas agrupando los tres índices: 18 absolutas (3 definiciones × 6 ejecuciones) y 18 contrastes definición − control.
  - R bruto, EE por sesión, BH q 0,10.
  - **Nominada:** BH + media > 0 + ≥ 60 % de años positivos (las absolutas) + calibra.
- **2. REP:** un paso de LORD++ (`ESCALONADAS_M1_A5::REP_escalonadas_m1_20261118`).
- **3. HOLDOUT:** una apertura de la familia con todos los meses HOLDOUT a la vez, sólo con las confirmadas y con N fijo.
  - **Requisitos para abrir:** plan de potencia ≥ 0,8 con la mitad del efecto de DESC; compuerta económica antes (neto operable con
    costos canónicos, escalera); `registrar_apertura` y la reserva LORD hechas.
  - **Confirma si:** p ≤ nivel, media > 0, ≥ 60 % de años positivos y ningún tercil de volatilidad en contra significativo.

## 5. Cómo podría refutarse
- **Mecanismo:** ningún contraste definición − control nominado con potencia en DESC, o en contra en REP.
- **Regla:** el bruto ≤ 0 con potencia en el holdout.
- **Economía:** el neto operable ≤ 0 aunque el bruto confirme. Es lo esperable en 2006–2015 con stops de 1 rango M1 (fricción ≈ 2 R).

## 6. Contador y linaje
- **Contador:** 36 pruebas.
  `tools/registro_global.py preregistrado ESCALONADAS-M1 ESCALONADAS_M1_A5 36 docs/research/escalonadas_m1_20261118/PREREGISTRO.md`.
- **Linaje (`LINAJES.jsonl`):** padres MNQ_ESCALONADAS_ESCALAS, ES_ESCALONADAS y EURUSD_ESCALONADAS (sin entrada propia: anteriores
  al registro de linajes). Heredan el conteo bruto.

## Enmienda 1 (2026-11-18, en la calibración, antes de cualquier desenlace de 2006–2025)
- **Qué pasó:** la calibración v0 (`CALIBRACION_v0.json`) dio 13/18 celdas reales calibradas.
  - Las que fallan son las de stop 1·D: M1 sale más optimista que los ticks por los saltos dentro de la vela (K40). Quedan sin nominar,
    como prevé el protocolo.
  - Los controles daban correlación ≈ 0,05.
- **Causa raíz:** el placebo se elegía con un hash del ÍNDICE de la vela, y el índice difiere entre el contexto armado con ticks y el M1
  de NT8. Cada fuente tomaba minutos distintos.
- **Corrección:** el hash es del minuto (t // 60), sigue siendo causal y elige el mismo minuto en las dos fuentes. Se relanza la
  calibración completa (ticks y M1).
- **Qué no cambia:** la regla, las celdas y la decisión.
