# Mejoras de la cartera: fricción, horario, tamaño, comisión y riesgo (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado ANTES de calcular ninguna de las mejoras sobre los conjuntos de confirmación. Pedido de Nico: «iterá y
aplicá las mejoras». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3/EF5.
Familia `MEJORAS_CARTERA_20261116` (hija de `CARTERA_20261116` y `PERDIDAS_STOP_CORTO`). Herramienta: `tools/mejoras_cartera.py`.
No cambia la cartera congelada (`SELECCION.json`): define una **versión 2** que sólo incorpora lo que pasa esta prueba.

## Dos clases de mejora
**A. Sin inferencia (hechos de costo y decisiones de riesgo; se aplican siempre):**
- **A1 Comisión mínima.** El R canónico usa la comisión MÁS cara de las firmas que admiten algoritmos (`criterio="max"`). Operando en la
  más barata, el R de cada operación sube en (fricción_max − fricción_min)/riesgo del micro (`edgelab/costos.py`). Es un hecho contable,
  condicionado a operar efectivamente en esa firma.
- **A2 PREAPERTURA-NQ a media ponderación.** DD de desarrollo −18 R y racha de 13 perdedoras: se pesa 0,5. Decisión de riesgo, no de señal.

**B. Hipótesis (salieron del desarrollo de 24 reglas; se prueban en datos no usados para verlas):**
- **M1 Filtro de fricción por operación:** saltear la operación si su fricción canónica en R (costo / riesgo) > **0,08** — el umbral
  vigente del proyecto para reglas (CLAUDE.md, lista K4–K9), no ajustado. H: R de las salteadas < R de las que quedan.
- **M2 Fin de rueda:** saltear entradas entre **14:00 y 16:15 NY**. H: R de las salteadas < R de las demás. Justificación: menos recorrido
  hasta el cierre (salidas por tiempo truncan las ganadoras) y menos liquidez direccional. Sólo esa franja: no se tocan las reglas
  diseñadas para fuera de la rueda (PREAPERTURA, nocturnas).
- **M3 Tamaño por contrato fijo:** micros fijos por regla (los que dan el riesgo objetivo con el riesgo mediano de desarrollo de la regla)
  en vez de riesgo fijo por operación. H: el t por sesión del P&L con contrato fijo > con riesgo fijo, a igual riesgo medio en dólares.

## Conjuntos de confirmación (no mirados para estas preguntas)
- **G:** desarrollo DESC + REP de las 3 reglas generadoras del universo (CVGAP-NQ, U1-ZONAS-NQ, U1-ZONAS-AVCL-NQ), que quedaron FUERA del
  análisis del que salieron M1–M3.
- **H:** holdout 2026-10-01 → 2026-11-13 de las 27 reglas (octubre y noviembre se miraron en total por regla, nunca por fricción, hora ni
  tamaño). Prueba principal: G ∪ H. Se informa cada uno por separado.

## Estadísticos (k = 3, BH q 0,10)
- M1, M2: Δ = R(salteadas) − R(quedan), estratificado por regla (como en `perdidas_concentradas.delta`), p de una cola por bootstrap de
  sesiones (B = 10.000); además R total de las salteadas.
- M3: Δt = t(contrato fijo) − t(riesgo fijo) de la serie por sesión de G ∪ H (todas las reglas sumadas, cada una escalada a 200 USD de
  riesgo medio); p de una cola por bootstrap de sesiones.
- **Incorporación a la v2:** una hipótesis entra si es nominada por BH **y** su Δ va en el sentido declarado en G **y** en H por separado.

## Cartera v2 y su medición (descriptiva)
v2 = las 8 reglas de `SELECCION.json` + A1 + A2 + las M que pasen. Se informa, con la misma simulación de prop (50K, 200 USD por R,
micros enteros): R por sesión de desarrollo y de holdout, probabilidad de pasar y de quemar, contra la v1. Nada de esto vuelve a elegir
reglas: la selección sigue congelada.

## Cómo podría refutarse
M1/M2: las salteadas rinden igual o más que las demás en G ∪ H. M3: el contrato fijo no mejora el t. Si nada pasa, la v2 = v1 + A1 + A2.
Contador global: 3 pruebas (`MEJORAS_CARTERA_20261116`).
