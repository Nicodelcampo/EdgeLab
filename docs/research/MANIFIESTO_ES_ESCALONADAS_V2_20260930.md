# Manifiesto ES-ESCALONADAS v2: stops amplios, V-shape (barrido y recuperación) y filtro de tendencia — PRE-REGISTRO (2026-09-30)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8` · Antecedente: `RESULTADO_ES_ESCALONADAS_202602_20260930.md`
(32/32 con R bruto negativo; stops de 3–5 ticks se comen ≈ 0,3 R en spread; control mal emparejado).
**Estado:** PRE-REGISTRO; se corre con OK de Nico. Detectores sin cambios (snapshot `d31fbd8`), confirmación por precio (2 ticks).

## Por qué cambia el mes
Febrero ya se usó para ajustar los detectores **y** para elegir qué mirar ahora (stops más amplios, sólo confirmación por
precio): volver a descubrir en febrero sería data snooping. **Descubrimiento: enero-2026** (ES 03-26, mismos ticks NT8;
enero no se usó para ajustar estas dos familias). **Réplica única: marzo-2026 hasta el roll**, sólo celdas que sobrevivan.
Febrero queda como descriptivo. Holdout desde el 1-oct y abr–sep intactos.

## Hipótesis
- **H-A (continuación con stop amplio):** tras la detección, operar en la dirección de la escalera con stop más allá de
  TODA la zona gana más que la misma mecánica al azar. Justificación: el spread pesa menos con riesgo mayor y la
  invalidación real de la absorción escalonada es la zona completa, no el último pico.
- **H-B (V-shape):** si el precio **barre** los picos de la zona (supera su extremo en ≥ 2 ticks) y en ≤ 20 velas **se
  recupera** (vuelve a 1 tick del lado interno del extremo), operar en la dirección original de la escalera gana más que
  el azar. Justificación: barrido de stops sobre una defensa visible y reabsorción (trampa).
- **Refutación:** ninguna celda supera al control tras max-T, o el R neto ≤ 0.

## Celdas — número efectivo de hipótesis = 140 (enmienda de Nico antes de correr: «más SL y TP, sobre todo TP largos»)
- **A:** familia (planas/empinadas) × stop (**extremo de la zona conocida al detectar + 2 ticks** / **fijo 10** / **fijo 16
  ticks**) × objetivo (**1R, 2R, 3R, 5R, 8R**) = 30.
- **B:** familia (2) × stop (**extremo del barrido + 2** / **+ 6 ticks**) × objetivo (1R, 2R, 3R, 5R, 8R) = 20; entrada stop al
  recuperar.
- **Break even (enmienda 2 de Nico, antes de ver resultados; la primera corrida se detuvo sin producir salida):** para
  objetivos ≥ 2R, variante con stop movido al precio de entrada cuando el precio opera a +1R a favor (sin BE / BE a 1R);
  con objetivo 1R el BE no aplica. A: 30 + 12 con BE; B: 20 + 8 con BE → 70.
- **Filtro de tendencia** sobre las 70: **todas** / **sólo a favor de tendencia** → **140. max-T sobre las 140.**
  Tendencia al momento de la entrada: cierre 25t vs EMA de 200 velas, y pendiente de esa EMA en 50 velas; «a favor» =
  dirección de la operación igual al signo compartido (si no coinciden, no hay tendencia → la operación sólo cuenta en «todas»).
- Horizonte 150 velas o fin de sesión. Una operación a la vez por celda y dirección.

## Métrica, control e inferencia
- R neto (comisión 0,40 ticks; bid/ask del replay tick a tick; stop y entrada stop al peor lado; objetivo límite con 1 tick
  de penetración).
- **Control con la MISMA mecánica** (corrige la falla de v1): 3 por evento, velas al azar de otras sesiones del mes,
  misma franja ±30 min, mismo tercil de volatilidad, misma dirección y mismo estado de tendencia si el filtro está activo;
  desde el cierre de esa vela se coloca la **misma orden stop a 2 ticks** en la dirección de la operación (A y B) con el mismo riesgo y objetivo en ticks; si no se llena en 20 velas, se re-sortea.
- Bootstrap por sesión con pesos comunes, **max-T sobre 140**, celda evaluable con ≥ 30 operaciones y ≥ 8 sesiones, MDE.
- Descriptivos: R bruto, tasa de objetivo, MFE/MAE; en B, cuántas zonas se barren y cuántas se recuperan.

## Riesgos
Enero con menos sesiones del contrato 03-26 al comienzo (liquidez previa al roll de diciembre); V-shape es una población
chica; el filtro de tendencia duplica celdas; el control con orden stop puede no llenarse en regímenes quietos (se reporta
la tasa de re-sorteo). Si nada sobrevive, **la familia se cierra en ES** con su alcance: estas geometrías, estas salidas.
