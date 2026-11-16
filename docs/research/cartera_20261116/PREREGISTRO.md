# Cartera con el período nuevo: continuación del holdout, validación y selección (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado ANTES de lanzar y antes de que exista ningún resultado de noviembre. Pedido de Nico (2026-11-16,
esfuerzo alto): aprovechar al máximo el período nuevo, validar calidad/potencia/estabilidad/rentabilidad por otras vías, ver qué se puede
mejorar (frecuencia, fricción, rentabilidad) y armar hoy la cartera más fiable posible.
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5 (confirmación) para la cartera;
descriptiva por regla. Herramienta: `tools/cartera_nov.py` (reusa el KaggleRunner sellado y ANALIZAR_REGLA de `tools/holdout_en_r.py`).

## 1. Universo (fijo): las 27 reglas con acta de holdout VIGENTE desde 2026-10-01
Todo `ACTA_HOLDOUT.json` no anulado (`python tools/cartera_nov.py universo`): CVGAP-NQ, CVGAP-CFD-NQ, CVGAP2-CFD-NQ, CVGAP-ES-C,
CVGAP-CFD-ES-C, U1-ZONAS-NQ, U1-ZONAS-ES, U1-ZONAS-BT2-NQ, U1-ZONAS-BT2-ES, U1-ZONAS-AVCL-NQ, U1-ZONAS-AVCL-ES-C, U1-RACIMOS-GRILLA-NQ,
U1-RACIMOS-GRILLA-ES, U1-ES-GRILLA, U1-YM-GRILLA, U1-ORO-GRILLA, TORI-NQ-R, CONF-CVR-CFD-NQ-R, DRC-NQ-R, DRC-YM-R, DRC-GC-R,
DRC-USATECH-R, DRC-USA500-R, DRC-XAU-R, DRC-EURUSD-R, PREAPERTURA-ES, PREAPERTURA-NQ.
**Fuera, a propósito:** ASIA-NQ, OTR930, RANGO0100 y PRERANGE-ZONAS (sus ventanas son forward desde el 2-nov con revisiones fijas y
prohíben mirar entre revisiones), CANASTA-GLOBAL (no pasó su holdout: «no se reintenta») y las familias que ya usaron su única apertura
(DELTASWEEP_NQ, M1_INTRADIA, LUXIMB_AMARILLA). ABSORCION-NQ-3R y COMPRESION-NR-GC no tienen regla reproducible congelada (auditoría del 7-nov).

## 2. Datos
- **Holdout sellado** `nicolasbuttaro/edgelab-holdout-sellado`, sesiones 2026-10-01 → 2026-11-13, menos `SESIONES_EXCLUIDAS_HOLDOUT`.
  Noviembre (2 → 13, 10 sesiones) existe sólo para **futuros NQ, ES, YM**. El spot de Dukascopy (USATECH, USA500, USA30, XAU, EURUSD) y GC
  llegan hasta el 29/30-oct: las reglas con esos sensores sólo aportan octubre hasta que se sellen sus noviembres.
- **Desarrollo** DESC y REP (réplica) de cada campaña: el ya medido en R con código causal (`canasta_7_20261030/desarrollo_en_r`) o, si
  falta, re-corrido ahora con la misma celda, cortes y tope.
- **Qué ya se miró:** octubre, para todas (apertura conjunta, `holdout_en_r`, PREAPERTURA, DRC/TORI/CONF en el tablero). **Noviembre 2 → 13
  no lo miró nadie para ninguna regla:** es la prueba limpia de esta cartera.
- Limitación declarada: las reglas U1 de zonas leen el almacén de zonas de desarrollo (`edgelab-zonas-u1`) como calentamiento; las zonas
  nuevas del holdout no están en el almacén, igual que en octubre.

## 3. R por operación
R = neto (con la fricción canónica de `edgelab/costos.py` ya descontada por el motor) / riesgo inicial (entrada real a stop).
Fricción en R = fricción canónica en puntos del instrumento de ejecución / riesgo.

## 4. Batería de validación (por regla; con desarrollo y octubre; noviembre se agrega después, aparte)
R/op con IC90 bootstrap por sesión (DESC, REP, OCT); t por sesión; meses con R > 0; R total sin las 5 mejores; drawdown máximo en R; racha
perdedora más larga; fricción en R y **estrés de costos** (R con fricción ×1,5 y ×2); operaciones por mes; **contracción empírico-bayesiana**
(R de desarrollo encogido hacia 0 con la varianza entre reglas: James-Stein), que descuenta la maldición del ganador; MDE80 del holdout con
su N fijo; correlación diaria entre reglas. Estas medidas describen: la selección usa sólo las de §5.

## 5. Regla de selección de la cartera (FIJA; se calcula sólo con sesiones ≤ 2026-10-30)
Elegible si cumple todo:
- **E1** ≥ 40 operaciones de desarrollo y R/op > 0 en DESC **y** en REP.
- **E2** fricción media en R ≤ 0,08.
- **E3** R total de desarrollo sin las 5 mejores operaciones > 0.
- **E4** ≥ 55 % de los meses de desarrollo con operaciones tienen R total > 0.
- **E5** octubre no en contra con evidencia: t por sesión de octubre ≥ −1,64 (con < 3 operaciones, pasa).
- **E6** se ejecuta en un futuro (NQ, ES, YM, GC o sus micros): es la cartera para prop de futuros. Las elegibles que se ejecutan en CFD
  forman una **cartera CFD** aparte con la misma regla.
Orden: R de desarrollo contraído (§4) de mayor a menor. Se agrega una regla si su correlación diaria de desarrollo con cada elegida es
≤ 0,5 y si no hay ya 2 de la misma familia de mecanismo (prefijo: CVGAP, U1-ZONAS, U1-RACIMOS, DRC, TORI, CONF, PREAPERTURA). Máximo 10.
Pesos: **1 R por operación para todas** (mismo riesgo en dólares), sin optimizar pesos.
La selección se escribe en `SELECCION.json` y se **commitea antes** de calcular nada de noviembre.

## 6. Prueba de la cartera en noviembre (la única inferencia de este documento)
- Serie: por sesión de noviembre (2 → 13, válidas), suma de R de las reglas elegidas (0 si no operan).
- **H: media > 0.** p de una cola por inversión de signo por sesión (B = 20.000) y t. Se informa además el holdout completo (oct + nov).
- Sin potencia previsible: con 10 sesiones y ≈ 1–3 operaciones por sesión en la cartera, el error estándar será ≈ 0,4–0,8 R por sesión.
  Se lee como dirección. Contador global: 1 prueba (familia `CARTERA_20261116`).
- **Lectura fijada antes:** VERDE si la media de noviembre > 0 y la del holdout completo > 0; AMARILLO si una de las dos ≤ 0; ROJO si el t
  del holdout completo < −1,64. Ninguna habilita dinero: operar en real lo decide Nico (CLAUDE.md). VERDE sólo respalda empezar una
  evaluación de prop con micros y el riesgo por operación de §8.
- Por regla, noviembre actualiza su e-proceso (`edgelab/funnel/secuencial.py`, válido mirando siempre) y su acta sigue hasta su N fijo.
  Nada de noviembre cambia reglas, cortes, topes ni la selección.

## 7. Mejoras (sólo con desarrollo; nada se elige con el holdout)
Frecuencia: la misma regla congelada en otros instrumentos ya medidos en desarrollo (versiones -ES/-YM/-GC de cada campaña) y la cuenta de
operaciones por mes de la cartera. Fricción: qué reglas tienen fricción en R alta y qué palanca la baja (stop más grande, entrada límite,
micros para redondear el tamaño). Rentabilidad: R por mes de la cartera, contribución por regla y concentración. Toda mejora propuesta
es una hipótesis nueva con su propio pre-registro: no entra en la cartera de hoy.

## 8. Tamaño para prop (descriptivo)
Con la serie diaria de desarrollo + octubre de la cartera: simulación por bloques de la evaluación de 50K (objetivo 3.000 USD, pérdida
máxima 2.000 USD con trailing de fin de día, `canasta_7_20261030/estimar_propfirm.py`) para riesgos de 50, 100 y 150 USD por R, con la
media de desarrollo contraída y con media 0 (el azar), en micros enteros.

## Justificación económica / cómo podría refutarse
Varias reglas con ventaja chica, de mecanismos e instrumentos distintos y poco correlacionadas suman su esperanza y diluyen el ruido; la
contracción y el estrés de costos descuentan selección y fricción. Refutación: media de la cartera ≤ 0 en noviembre y en el holdout
completo, o t del holdout completo < −1,64.
