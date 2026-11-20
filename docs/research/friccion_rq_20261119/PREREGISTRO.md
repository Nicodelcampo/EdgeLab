# FRICCION-RQ: ¿se puede bajar la fricción de RQ2, RQ5 y RQ6 sin perder el bruto? Curva bruto–stop y otras palancas (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «Adelante con tu recomendación del bruto. Indagá en otras maneras de reducir la fricción».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3, sólo DESC** (meses DESC de A5, 2006–2025, ES + NQ + YM). REP y holdout no se leen. **Familia:** `ROBOQUANT_A5` (misma
  familia que las reglas: estas celdas suman a su multiplicidad).
- **Herramienta:** `tools/friccion_rq.py` (reusa las señales ya calculadas de `docs/research/roboquant_20261118/EVENTOS.csv.gz`, el motor
  único `ejecucion.desenlaces` con objetivo/stop en precios, la fricción canónica y el cargador rápido verificado de
  `tools/externas_estructurales_a5.py::cargar_ctx_m1nt8_rapido`, que arma el mismo contexto que `a5_campana._ctx` salvo el perfil de
  volumen, que este motor no usa — comprobado 2026-11-19 en NQ ene–feb 2018: o/h/l/c/t/ses/tpx/tstart idénticos).

Antecedentes: «fricción stop grande entrada pasiva una por día roboquant banda de ruido vwap» — F-STOP-GRANDE-FRENTE-A-FRICCION,
F-STOP-CORTO-ES-FRICCION, F-SELECCION-ADVERSA-PASIVA, F-LUXIMB-EJECUCION-TIMING (la curva bruto–stop es la prueba que pide), F-FRECUENCIA-MINIMA.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 R con el riesgo inicial nuevo, K40, K48, K49, K50).

Potencia previa: DESC tiene 1.500–6.700 operaciones por regla (1.000–2.200 sesiones por índice); con sd ≈ 1,2 R el error estándar del R
medio por celda es 0,015–0,03 R. Alcanza para ver si el bruto cae a la par de la fricción (diferencias de ~0,05 R). No habilita REP: si una
celda mejora, su lectura en REP + holdout se planifica después con K49 (potencia en días) y se pre-registra aparte.

## 0. Justificación económica
- RQ5 y RQ6 capturan momentum intradía (continuación a favor del día, Baltussen et al. 2021; banda de ruido de Zarattini) y RQ2 una
  reversión inter-día. Si el desplazamiento que explotan dura más que su objetivo actual, un riesgo y un objetivo más grandes cobran la
  misma ventaja en R pagando la fricción fija sobre una base mayor: el neto sube. Si su ventaja es de timing (se agota en minutos), el
  bruto cae al ensanchar y no hay palanca.
- **Registro de un lanzamiento descartado (2026-11-19):** la primera ejecución de `friccion_rq.py correr` arrancó antes de que este
  pre-registro se contara (la guarda pidió esta sección y la cadena de comandos siguió igual). Se mató a mano después de procesar ES; no
  escribió `OPS.csv.gz` ni `RESULTADO.json` y no se miró ningún desenlace. Se relanza completa después del conteo.

## 1. De qué está hecha la fricción (costos canónicos, viaje redondo)
| | spread | comisión | slippage (supuesto) | total |
|---|---|---|---|---|
| NQ | 3,03 ticks | 1,15 | 2 | 6,18 ticks = 1,55 pts |
| ES | 1,09 | 0,46 | 2 | 3,55 ticks = 0,89 pts |
| YM | 1,90 | 1,15 | 2 | 5,05 ticks = 5,05 pts |
- Pesa en R como fricción / riesgo inicial. Las tres vías para bajarla: **riesgo más grande por operación** (stop/objetivo más amplios o
  salida al cierre), **menos operaciones** (una por día; juntar reglas que coinciden) y **pagar menos por operación** (orden límite).

## 2. Celdas (18, cerradas antes de correr; misma señal, mismo momento de entrada a mercado)
- Para RQ2, RQ5 y RQ6 (las tres con neto operable ≥ 0 en DESC; RQ1 queda fuera: su salida a 8 minutos es timing por construcción):
  - **Escala m ∈ {1; 1,5; 2; 3}:** stop a m × el riesgo original desde el cierre de la vela de señal; objetivo a m × la distancia original
    (misma geometría en R; si el objetivo original es «lejano», queda lejano). m = 1 reproduce la regla.
  - **Salida al cierre, m ∈ {1; 2}:** sin objetivo (cierre RTH o fin de la regla), stop a m × el riesgo original.
- R bruto, fricción en R con el riesgo nuevo y R neto por celda; error estándar agrupado por sesión.

## 3. Decisión y cómo podría refutarse
- **TIMING** (la palanca no sirve): el bruto cae a la par de la fricción y el neto de la mejor m > 1 no supera al de m = 1 por más de un
  error estándar.
- **ESCALABLE:** alguna m > 1 da R neto > 0 con su IC90 inferior > −0,01 y bruto ≥ 50 % del de m = 1. Pasa a pre-registro de lectura
  (REP + holdout con K49), no a operar.
- **Descriptivo (sin decisión ni conteo):** (a) una operación por día y por instrumento (la primera); (b) RQ5 y RQ6 juntas en una sola
  posición cuando coinciden de lado el mismo día; (c) sensibilidad de costo: salir en el objetivo con orden límite no paga medio spread
  ni el slippage de salida (cambiar el modelo canónico es semántica de validación: sólo se reporta, lo decide Nico); (d) entrada con
  orden límite: no se mide acá (F-SELECCION-ADVERSA-PASIVA: ≈ −0,07 R de selección adversa con fill conservador).
- **Contador:** 18 pruebas en `ROBOQUANT_A5`.
