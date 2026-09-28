# Manifiesto ESPEJO-NICO-100T: ¿las vueltas «parecidas» (definición de Nico) completan el espejo más que el azar? — PRE-REGISTRO (2026-09-28)

**North Star:** `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`
**Estado:** PRE-REGISTRO. Mira retornos (llegar o no a A): **STOP** hasta el OK de Nico **y** la auditoría de GPT-6 Sol (entrada 055). Nada corrido.
**Familia:** ESPEJO-IND (registro `REGISTRO_FAMILIA_ESPEJO_IND_20260926.md`). No transporta resultados de ESPEJO-SIM ni ESPEJO-MACRO (sólo sus definiciones de evento y nulo).
**Ledger:** `artifacts/hippocampus/espejo_ind_20260926.jsonl` (partición nueva de descubrimiento).

## 1. Hipótesis, justificación y refutación
- **Hipótesis:** entre las vueltas que ya recorrieron la fracción x del impulso, las **más parecidas** a la ida según la definición validada de Nico completan el espejo (llegan a A antes de un extremo nuevo más allá de B) **más** que las menos parecidas y más que el nulo exacto.
- **Justificación económica (tesis de Nico):** un impulso forzado explora sin aceptación; cuando el empuje afloja, el precio deshace el camino con la misma forma. Una vuelta que reproduce la forma de la ida es la huella de ese mecanismo; una que no la reproduce es otro fenómeno.
- **Cómo podría refutarse:** la tasa de completado del tercil más parecido no supera a la del menos parecido ni al nulo al cierre (f); o sólo lo hace por velocidad (sería momentum, ya visto en ESPEJO-MACRO), cosa que se controla porque la definición congelada pesa sobre todo la forma (DTW).

## 2. Objeto y definición de «parecido» (congelados antes de este manifiesto)
- **Velas 100t** (4 velas de 25t agrupadas dentro de la sesión, exacto). **ES**, contrato canónico por sesión (research-v2, proveedor Lucid).
- **Impulso:** kernel `edgelab/bridge/indicators/espejo_impulsos.py` con `min_w = 34 t`, `max_bars = 20`, `e_min = 0,3`, `retr = 0,3`, sin `e_max`. Estratos: **TBZ** (eficiencia ≥ 0,6) y **otros** (0,3–0,6).
- **Semejanza:** modelo congelado `docs/research/ESPEJO_SEMEJANZA_NICO_CONGELADA_20260928.json` (código `tools/espejo_semejanza_nico.py`, sha `02ac263ba511…`). Validado fuera de muestra: 73 % de pares (IC 62–83 %). Se calcula **con datos hasta la vela del evento** (causal). Variante preregistrada de sensibilidad: DTW solo.
- **Espacio de eventos enumerado** (regla de población): creación del impulso, confirmación en B, cruce de x de la vuelta, completado, fracaso, vencimiento, estado continuo. **Se congela: cruce de x** (primer cierre en que la vuelta pasa x).

## 3. Evento, resultado y nulo
- **Evento:** primer cierre de vela en que la vuelta recorrió x ∈ {0,50; 0,75} del impulso, sin extremo nuevo más allá de B.
- **Resultado:** completa (toca A) antes de un extremo nuevo más allá de B; horizonte 3 × duración de la ida o fin de sesión.
- **Nulo exacto:** sin memoria, desde la fracción f **al cierre** de la vela del evento, P(completar) = f (lección de ESPEJO-SIM: el nulo con el extremo de la vela está sesgado).
  - **RETIRADO 28/09 (auditoría 056 §4, verificado en sintético): f NO es exacto.** Paseo simétrico sintético con velas 100t, toque por mecha, falla = extremo nuevo más allá de B y horizonte 3x: sesgo sobre resueltas de +1 a +5 pp sin censura y hasta +25 pp con censura (`tools/espejo_nulo_sintetico.py`, `artifacts/espejo/nulo_sintetico_20260928.json`). Antes de cualquier outcome: reemplazar por un nulo simulado que preserve barreras, regla de toque, 100t y horizonte, y tratar censura como categoría propia. **Decisión de Nico: SÍ (28/09) → enmienda N1 abajo.**
- **Enmienda N1 — nulo simulado (aprobada por Nico 28/09, antes de mirar cualquier desenlace):**
  - Por evento, `edgelab/research/espejo_nulo.py::simulate_null` (tests `tests/research/test_espejo_nulo.py`) da
    p0(completa), p0(falla), p0(ambigua), p0(censurada) con 2.000 trayectorias sin memoria que remuestrean i.i.d. las
    velas de 25t **anteriores al evento** de la misma sesión (≥ 50; si hay menos, se completan con el final de la sesión
    previa; si aun así no alcanza, el evento se excluye y se cuenta). Ternas (cierre, máximo, mínimo) − apertura, centradas
    para no imponer deriva. Mismas barreras en ticks, mismo toque por mecha, misma agregación a 100t, mismo horizonte
    recortado por fin de sesión. Semilla = hash del id del evento.
  - **Estimand primario nuevo:** exceso = media(completa_i − p0_completa_i) sobre **todos** los eventos (no sólo los
    resueltos: condicionar a resueltos reintroduce el sesgo de censura). La censura se publica aparte: observada vs p0.
  - f queda sólo como descriptivo.
- **Medición sobre el precio de trade y sobre el midquote** (lección del Cerebro `LES-R3-TRADE-PRICE-BOUNCE`); el primario es **midquote**.

## 4. Pruebas (celdas primarias)
Terciles del puntaje de semejanza fijados **sobre el descubrimiento completo sin mirar resultados** (sólo el puntaje).
| # | Contraste primario | Celdas |
|---|---|---|
| P1 | completado − p0 en el tercil **más parecido** | x (2) × estrato (2) = 4 |
| P2 | (completado − p0) tercil más parecido − tercil menos parecido | x (2) × estrato (2) = 4 |
**8 pruebas primarias**, BH q = 0,10. Bootstrap por sesión (1.000). Se publican MDE, n por celda, la distribución completa del exceso y los dos canales (direccional: completa; no direccional: excursión máxima en W). Descriptivos no contados: sensibilidad con DTW solo, trade vs mid.

## 5. Datos y particiones
- **Descubrimiento:** ES jul-2025 → mar-2026 (Lucid). **Replicación (una vez, A3):** abr–sep 2026 sólo para celdas sobrevivientes; ojo: jul–sep es NT8 (Entrada 053), así que la replicación se reporta por proveedor y requiere antes la paridad Lucid ↔ NT8. **Holdout:** oct+ a futuro.
- Las 32 + 31 tandas que juzgó Nico (ene–mar 2026 y oct–dic 2025) usaron eventos de estos meses **sin desenlace**: no contaminan el resultado, pero se reporta el resultado **con y sin** esos 189 impulsos.

## 6. Economía (sólo si P1/P2 sobreviven; pre-registro aparte)
- Fricción ES propia (~2,5 t ida y vuelta con deslizamiento). Con W mediano ≈ 39 t, el exceso sobre p0 necesario para cubrir costos es ≈ **2,5 / 39 ≈ 6,4 puntos** en la geometría «entrada en x, objetivo A, stop más allá de B». Si P1 da un exceso menor, se reporta como información sin viabilidad a esta escala.

## 7. Riesgos declarados
- Potencia: ~290 vueltas llegan al 75 % por trimestre en ES; por tercil y estrato puede quedar SIN_POTENCIA; se publica el MDE.
- La definición de semejanza tiene 73 % de acuerdo con Nico, no 100 %: un nulo puede deberse a la métrica.
- Superposición de eventos (x = 0,50 y 0,75 del mismo impulso): se reportan por separado, bootstrap por sesión.
