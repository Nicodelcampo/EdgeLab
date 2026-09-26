# Manifiesto: mapa de información contra costo por horizonte (IVC), ES y NQ, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Escrito antes de medir. **Espera el OK de Nico** (regla STOP: mira retornos futuros).
**Partición:** exploración, sesiones jul-2025 a mar-2026 (las mismas de `P-TBZ-EXP` / `P-TBZX-R3-EXP`).
Descubrimiento = jul–nov 2025; validación = dic 2025–mar 2026. Abr–jun y el holdout (>= 2026-07-01) no se leen.
**Herramientas:** `tools/mapa_info_costo_kaggle.py` (kernel de Kaggle) y `tools/mapa_info_costo_analisis.py`.
**Cerebro:** familia `IVC`, ledger propio `artifacts/hippocampus/ivc_20260926.jsonl`.

## 1. Por qué ahora

El cerebro junta diez familias intradía de horizonte corto con neto negativo: HFTZones, BigTrap2, TBZ-E2, TBZX-R3, MM-QI,
TREND-MICRO, AGOT-EXT, V-RND, la sinergia L2 de NQ y las cinco familias simples de la campaña de ticks. En todas hay
información (QI +39 pp en el próximo tick; TBZ +3 pp; reversión al VWAP con timing en 5/5), pero su tamaño por
operación (~0,1–0,5 t) es menor que la fricción (~1,5 t en ES). La única pista que pasó un nulo serio es de otra
escala: el cierre del gap nocturno (MCPT p <= 0,019 en ES, NQ y YM), sin potencia por tener una observación por día.

La regla del proyecto ordena geometría → **información** → P&L bruto → neto. El paso de información nunca se midió de
forma sistemática por horizonte (la «F4 constitucional»). Este mapa lo mide y contesta **en qué horizonte y con qué
estado la información por apuesta supera el costo**, antes de gastar más pruebas en reglas de entrada.

**Justificación económica:** la fricción es casi fija por operación (spread + comisión), mientras que el movimiento
esperado crece con el horizonte (~√h). Un IC chico puede pagar el costo en horizontes largos y nunca en los cortos.
**Cómo podría refutarse:** que en ningún horizonte, instrumento ni estado el borde bruto por apuesta supere al costo
con IC inferior > 0 en descubrimiento y signo sostenido en validación.

## 2. Espacio de eventos y estados (regla de población)

Enumerado antes de elegir. Candidatos: (a) eventos (toques, creaciones, aperturas), (b) estado continuo muestreado en
una grilla de reloj, (c) grillas en reloj de volumen. **Se elige (b), grilla de 5 minutos ET en toda la sesión CME**,
porque da la mayor potencia (≈ 276 puntos por sesión), no hereda la selección de ningún detector y permite comparar
todos los estados en el mismo soporte. La única variable de evento es el gap, que se mide una vez por día (9:35 ET).
Se refuta la elección si el mapa por grilla contradice a los eventos ya medidos (p. ej. TBZ +3 pp a 3 ticks).

## 3. Variables de estado (todas causales, con información hasta el instante t)

| Variable | Definición | Canal |
|---|---|---|
| `mom5`, `mom15`, `mom60`, `mom240` | cambio del precio medio en h minutos (ticks) | direccional |
| `vwap` | último trade − VWAP de la sesión (ticks) | direccional |
| `ofi5`, `ofi60` | volumen firmado por tick-rule / volumen total, ventana h | direccional |
| `zona` | posición en la última franja TBZX (mb20_mw8) disponible: (precio − medio)/W con signo del impulso; NaN si no hay | direccional |
| `gap` | apertura RTH 9:30 − cierre RTH previo (ticks), sólo en el punto de 9:35 ET | direccional |
| `vol30` | rango de los 30 min previos (ticks) | no direccional |

## 4. Objetivos y costo

- Retorno futuro del medio a h ∈ {1, 5, 15, 60, 240 min, cierre RTH 16:00 ET} (ticks). Sin cruzar el fin de sesión.
- Canal no direccional: |retorno futuro|.
- Costo de ida y vuelta por punto: spread en t + spread en t+h (agresivo, conservador) + comisión (ES 0,2 t/lado;
  NQ 0,45 t/lado). Se reporta además con la corrección pasiva de EXEC-QI (ES +0,12 t/lado; NQ +0,43 t/lado), como
  lectura secundaria.

## 5. Medida

Por instrumento × variable × horizonte × subconjunto (todo / RTH 9:30–16:00 / fuera de RTH):
1. IC de Spearman (estado, retorno futuro) e IC no direccional (estado, |retorno|).
2. **Borde bruto por apuesta** = (media del retorno en el quintil superior − media en el inferior) / 2, con el signo del
   IC. Es lo que ganaría, en promedio, operar los dos extremos a favor.
3. **Margen** = borde bruto − costo mediano de ese horizonte. IC 95 % por bootstrap por sesión (1.000).
4. **Breadth** = apuestas independientes por año (ventanas de h que no se solapan, 40 % en los quintiles extremos).
5. **Nulo**: la misma variable desplazada circularmente entre sesiones a la misma hora del día (200 réplicas). MDE.

## 6. Multiplicidad y decisión (fijas ahora)

- Celdas: 10 variables × 6 horizontes × 3 subconjuntos × 2 instrumentos = **360** (gap: sólo horizonte a cierre).
- BH-FDR q = 0,10 sobre el IC direccional contra el nulo. Celdas con < 20 sesiones en descubrimiento o validación: SIN_POTENCIA (el nulo entre sesiones es degenerado; detectado en la prueba nula).
- **Zona prometedora** = FDR + margen con IC inferior > 0 en descubrimiento + margen > 0 e IC del mismo signo con IC
  inferior > 0 en validación.
- Una zona prometedora **no es un edge**: habilita un pre-registro de regla con su propia campaña, confirmación en
  abr–jun y, al final, el holdout. Se publica el mapa completo (las 360 celdas).

## 7. Riesgos

- Los 5 min de grilla solapan retornos de horizontes largos: se corrige con bootstrap por sesión y breadth honesta.
- El costo agresivo es conservador; puede esconder márgenes que la ejecución pasiva recuperaría (lectura secundaria).
- 9 meses son pocos para el gap (≈ 180 observaciones): puede quedar sin potencia; el MDE lo dirá.
- `sequence` no es secuencia del exchange (P-28): el tick-rule usa sólo el orden por timestamp.
