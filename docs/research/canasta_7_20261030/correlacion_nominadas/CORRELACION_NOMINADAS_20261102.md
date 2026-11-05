# Correlación entre las nominadas al holdout (2026-11-02)

Estado: VIGENTE (descriptivo). Pedido de Nico: «hacé un test para ver cuáles están más y menos correlacionadas». Referente:
`docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. No elige ni descarta reglas: es
información para el tamaño y la diversificación de la cartera.

## Datos y método (`tools/correlacion_nominadas.py`)
- **Reglas:** las 12 nominadas y U1-CRUZADO, con su P&L **causal** de DESC + réplica (2025-08 → 2026-09; YM desde 2024). Sin holdout:
  tiene muy pocas operaciones.
- **Serie por regla:** P&L neto por sesión dividido por su desvío; 0 en las sesiones sin operación.
- **Por par:**
  - Pearson y Spearman sobre las sesiones en que operó alguna de las dos (dentro del período común);
  - IC90 por bootstrap de sesiones;
  - co-ocurrencia: sesiones en que operaron las dos;
  - correlación sólo en esas sesiones.
- **Número efectivo de estrategias independientes:** Li-Ji (`escalera.n_efectivo`) sobre la matriz común de 277 sesiones.

## Resultado
**Casi no hay correlación entre las reglas.**
- 78 pares. Mediana de |r| = 0,06; 59 pares con |r| < 0,1. Máximo +0,16 y mínimo −0,26.
- Número efectivo (Li-Ji): **13,0 de 13**. Para la cartera se comportan como estrategias independientes.
- 18 de 78 IC90 excluyen el 0. Por azar se esperarían ≈ 8: hay algo de estructura, pero chica.

**Más correlacionadas (positivas):**

| Par | r | IC90 | Sesiones con las dos operando |
|---|---|---|---|
| U1-ZONAS-NQ y U1-YM-GRILLA | +0,16 | [+0,05; +0,26] | 37 |
| U1-RACIMOS-GRILLA-ES y U1-CRUZADO | +0,16 | [+0,02; +0,29] | 46 |
| U1-ZONAS-NQ y U1-ZONAS-BT2-ES | +0,15 | [+0,05; +0,25] | 31 |
| CVGAP-NQ y U1-RACIMOS-GRILLA-ES | +0,14 | [+0,00; +0,26] | 45 |
| CVGAP-NQ y U1-ZONAS-BT2-NQ | +0,13 | [+0,01; +0,25] | 47 |
| CVGAP-NQ y CVGAP-CFD-NQ | +0,10 | [+0,02; +0,19] | 72 (r = +0,20 cuando operan las dos) |

**Menos correlacionadas (negativas, sirven de cobertura entre sí):**

| Par | r | IC90 |
|---|---|---|
| U1-RACIMOS-GRILLA-NQ y U1-ZONAS-ES | −0,26 | [−0,46; −0,04] |
| U1-ORO-GRILLA y U1-CRUZADO | −0,16 | [−0,28; −0,03] |
| U1-RACIMOS-GRILLA-NQ y U1-ZONAS-BT2-NQ | −0,15 | [−0,27; −0,02] |
| CVGAP-NQ y U1-RACIMOS-GRILLA-NQ | −0,14 | [−0,27; −0,00] |
| U1-ZONAS-AVCL-NQ y U1-CRUZADO | −0,13 | [−0,31; +0,03] |
| U1-ES-GRILLA y U1-ZONAS-BT2-NQ | −0,12 | [−0,23; −0,01] |

**Cerca de cero:** ORO con BT2-NQ, RACIMOS-ES y YM; ZONAS-NQ con RACIMOS-ES; BT2-NQ con ZONAS-ES.

## Lectura
- **Diversifican bien:** la canasta puede sumar riesgo casi sin que se compense entre reglas en contra, pero tampoco se concentra.
- **Las dos CVGAP** comparten familia y sólo correlacionan +0,10 (+0,20 en los días en que operan las dos): cambiar el sensor cambia
  bastante las operaciones.
- **Lo que no se mide acá:** la correlación en estrés, es decir en las colas o en los peores días. Con unas 270 sesiones y operaciones
  esporádicas, la medición de colas no tiene potencia.

## Cómo podría refutarse
Que en el holdout, con más sesiones, aparezcan pares con |r| > 0,3 sostenido.
