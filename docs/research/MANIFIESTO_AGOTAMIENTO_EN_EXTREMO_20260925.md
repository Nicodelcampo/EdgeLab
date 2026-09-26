# Manifiesto: agotamiento en extremo (familia AGOT-EXT), ES · NQ, 2026-09-25

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** **APROBADO** por Nico el 25/09: "OK manifiesto AGOT-EXT, levanto F9, adelante con todo". **F9 queda levantada sólo para esta familia**; para cualquier otro indicador nuevo sigue pausada.

**Excepción a F9, a decidir en el mismo OK.** F9 (indicadores nuevos) está pausada por decisión sellada. Esta familia **abre un indicador nuevo** (RSI y divergencia de delta). Correrla exige levantar la pausa para esta familia y sólo para ella. El argumento está en §1.

**Ledger:** `artifacts/hippocampus/agot_ext_20260925.jsonl` (familia nueva). No hereda resultados, poblaciones, costos ni presupuesto de TREND-MICRO, TBZ, ABS-CTX ni HP-008.

**P-52:** la definición es nativa (RSI de Wilder, divergencia sobre pivotes propios). No se replica el algoritmo de ninguna plataforma.

## 1. Pregunta y por qué ahora

**Pregunta de Nico (25/09):** ¿las divergencias del RSI, u otros osciladores, funcionan? ¿Vale la pena probarlas?

**Qué es una divergencia, sin folklore.** El precio hace un extremo nuevo (máximo más alto que el máximo previo), pero el impulso con el que llegó es menor que el del extremo anterior. Es una **desaceleración en el extremo**. El RSI sólo transforma precios pasados, así que la pregunta real es si la desaceleración en el extremo anticipa una vuelta **más allá de lo que ya anticipa haber hecho un extremo nuevo**.

**Por qué ahora (evidencia propia, no folklore):**
- TREND-MICRO (25/09): cuando una expansión se continúa en la misma dirección, el precio llega al target **menos** que un camino aleatorio con las mismas distancias. ES −3,4 pts de acierto, IC [−4,5; −2,2], n = 12.003. NQ −6,2 pts, IC [−8,8; −3,6], n = 1.984.
- HP-008: razón de varianzas < 1 en NQ 25t.

Hay un sesgo de **agotamiento después de desplazamientos sostenidos**. La divergencia es una forma clásica de fecharlo; puede afinarlo o ser una versión más ruidosa de lo mismo, y eso es lo que se mide.

**Lo que dice la literatura (la vara es alta):** las reglas técnicas, osciladores incluidos, casi nunca sobreviven a la corrección por pruebas múltiples y a los costos en mercados líquidos (Sullivan, Timmermann y White 1999; Bajgrowicz y Scaillet 2012). En intradía del E-mini no encontraron valor (Marshall, Cahan y Cahan 2008). La divergencia del RSI no tiene tests rigurosos publicados que conozcamos. **Probabilidad previa de éxito: baja a moderada.**

**Justificación económica:**
- Un extremo nuevo alcanzado con menos impulso indica que la demanda (o la oferta) que empujó el tramo anterior se está agotando.
- Los que compran el máximo nuevo son los que llegan tarde. Si el flujo agresivo se debilita en el extremo (divergencia de delta), la pared pasiva del otro lado está absorbiendo, y el precio tiene menos combustible para seguir.

**Cómo podría refutarse:**
- La **sinergia** (§4) es ≤ 0 con un MDE chico: la divergencia no agrega nada a "hizo un extremo nuevo".
- O el R neto no supera a N1 en ninguna celda después de la corrección por pruebas múltiples.
- O supera sólo en exploración y no en la reserva.

## 2. Espacio de eventos (enumerado antes de congelar la población)

| Familia de eventos | ¿Se mide? | Por qué |
|---|---|---|
| **Máximo o mínimo nuevo de un tramo (pivote de zigzag) que supera al pivote previo del mismo lado** | **Sí (base)** | Es la definición clásica de divergencia: compara dos pivotes consecutivos |
| Máximo o mínimo nuevo de la sesión | No | Otro objeto (TREND-MICRO B1 ya lo midió como ruptura) |
| Ruptura de PDH/PDL o de un número redondo | No | Ídem (TREND-MICRO B1/B2) |
| Borde de una franja TBZ | No | Otra familia (TBZ-E2) |
| Divergencia como **estado** continuo (condiciona todas las barras) | No en E1 | Sirve para lo descriptivo; la pregunta es una decisión de entrada |
| Toque n-ésimo del extremo, invalidación, vencimiento, confluencia | No en E1 | Se abren sólo si E1 deja algo |

**Momentos del evento, dos variantes declaradas:**
- **V-RUP (en la ruptura):** primer trade que supera el pivote previo del mismo lado por ≥ 1 tick. La divergencia se evalúa **en ese instante**, comparando el oscilador actual contra el del pivote previo.
- **V-CONF (en la confirmación):** cuando el máximo nuevo queda confirmado como pivote (retroceso ≥ max(2 t, 0,3 · tramo), la misma regla de fin de TBZ), y el oscilador en el pivote nuevo es menor que en el previo.
- Las dos son **causales**: nada usa barras posteriores al instante del evento.

## 3. Definiciones (fijas, sin barrido)

- **Barras:** tiempo, 1 min y 5 min (el RSI se usa clásicamente sobre barras de tiempo), armadas desde los ticks de `research-v2`.
- **Pivotes:** zigzag sobre las barras con retroceso ≥ max(2 t, 0,3 · tramo) y tramo mínimo ≥ 1,5 · ATR(20) causal. El pivote previo del mismo lado tiene que estar dentro de las 60 barras anteriores.
- **Divergencia RSI (D-RSI):** RSI de Wilder de 14. Precio con máximo más alto que el pivote previo y RSI menor que el RSI en el pivote previo (y simétrico en mínimos). Umbral δ = 0. Como sensibilidad descriptiva, RSI 7 y 21.
- **Divergencia de delta (D-DELTA), sólo NQ:** en el tramo que llega al extremo nuevo, la fracción de volumen agresivo a favor del tramo es menor que en el tramo que llegó al pivote previo. El agresor de `research-v2` está validado en NQ (99 %) y **no en ES (80 %, P-93)**; por eso ES sólo lleva D-RSI.
- **Operación** (contra el extremo):
  - entrada agresiva en el primer trade posterior a evento + 250 ms;
  - stop: el extremo nuevo + max(2 t, 0,25 · tramo);
  - targets de 1R y 2R, como límite que se llena sólo si el precio lo atraviesa por 1 tick;
  - tiempo máximo: 30 barras de la resolución;
  - costo: spread observado más comisión por lado (ES 0,2 t y NQ 0,5 t).

## 4. Estimandos, nulos y controles

- **Primario:** R neto por evento (con costo), bootstrap por sesión.
- **Sinergia (el control que decide):** misma resolución, mismo momento, mismos extremos nuevos, **con** contra **sin** divergencia. `S = E[R | extremo ∧ divergencia] − E[R | extremo ∧ sin divergencia]`. Contesta la pregunta de verdad: si la divergencia agrega algo a "hizo un extremo nuevo".
- **N1, ruina del jugador con las convenciones de la simulación:** el acierto tiene que superar lo que da la geometría sola (s/(d + s) desde el último trade, con el target atravesado por 1 tick).
- **Dos canales:**
  - direccional: R y acierto;
  - no direccional: |movimiento| a 30 barras y excursiones a favor y en contra;
  - más la distribución completa, que es la regla del proyecto.
- **Guardia de controles:** el "sin divergencia" es de la **misma** población de eventos, no un instante al azar, así que `CTRL_TIMING_V1` no aplica. Se registra `design = "OTHER"`.

## 5. Datos, particiones y potencia

- Ticks de `research-v2` pre-holdout. Sesiones y contrato del día desde los manifiestos de los bundles, igual que en TREND-MICRO.
- **Particiones nuevas, declaradas antes de medir:**
  - `P-AGOT-ES-EXP` y `P-AGOT-NQ-EXP`: jul-2025 a mar-2026;
  - `P-AGOT-ES-CONF` y `P-AGOT-NQ-CONF`: abr–jun 2026, reservadas.
- Son **las mismas sesiones de exploración** que usaron TREND-MICRO y TBZ-E2. Eso se declara: la exploración se mira varias veces, y por eso la confirmación va sólo a la reserva.
- **Holdout de ticks** (jul–dic 2026): intacto. El 24/09 no aplica (es holdout).
- **Potencia:** se publica el MDE por celda. Las celdas con menos de 200 eventos se reportan como sin potencia.

## 6. Presupuesto de pruebas

**Celdas primarias:**

| Instrumento | Resoluciones | Momentos | Divergencias | Targets | Celdas |
|---|---:|---:|---:|---:|---:|
| ES | 2 | 2 | 1 (D-RSI) | 2 | 8 |
| NQ | 2 | 2 | 2 (D-RSI, D-DELTA) | 2 | 16 |
| **Total** | | | | | **24** |

Cada celda lleva su sinergia. **FDR (BH, q = 0,10)** sobre las 24. RSI 7 y 21 son sensibilidad descriptiva: no entran al presupuesto y no pueden generar sugerencias.

**Otros osciladores (MACD, estocástico, CCI):** **no se prueban**. Son transformaciones casi equivalentes del mismo precio y sólo multiplicarían las pruebas sin sumar información. Si D-RSI deja algo, se compara contra una sola alternativa pre-registrada.

## 7. Regla de sugerencia (fija)

Una celda es SUGERENCIA si cumple todo esto:
- pasa el FDR;
- R neto con IC > 0;
- acierto por encima de N1, con IC;
- **sinergia con IC > 0**;
- positiva en ≥ 55 % de los meses.

A lo sumo **3** pasan a `P-AGOT-*-CONF`, con una spec en revisión ciega y una campaña aprobada.

## 8. Riesgos

- **Mirar el futuro con los pivotes:** un pivote sólo existe cuando se confirma. V-RUP compara contra el pivote **previo** ya confirmado; V-CONF entra recién al confirmarse. Hay un test con un fixture que mueve el precio después del evento y verifica que nada cambia.
- **Solapamiento con el sesgo de reversión de TREND-MICRO B3:** la familia puede estar midiendo lo mismo con otro nombre. Por eso decide la **sinergia**, no el R solo.
- **Agresor de ES inválido (P-93):** en ES no hay D-DELTA.
- **Multiplicidad:** 24 celdas más las sensibilidades. Se controla con FDR, el tope de 3 y la reserva intacta.
- **F9:** abre un indicador. Si Nico no levanta la pausa para esta familia, no se corre.

## 9. Herramienta (reutilizable)

`tools/agotamiento.py` (`declare` → `run` → `report`): recibe el instrumento, las sesiones y la resolución. Reusa el zigzag de `tools/tbz_e2.py`, la simulación con las convenciones de N1 y el esqueleto de reporte de TREND-MICRO. Se escribe **después** del OK.

## 10. Resultado (25/09, madrugada): ninguna sugerencia; la divergencia no anticipa la vuelta

Reporte `artifacts/agot_ext/report.json` (sha `381d3cc81039…`). Ledger `artifacts/hippocampus/agot_ext_20260925.jsonl`. Exploración jul-2025 a mar-2026: NQ en 171 sesiones y ES en ~180. **24 celdas, 0 sugerencias.** Las 24 pasan el FDR, todas por ser **negativas**.

**La pregunta central: ¿la divergencia agrega algo a "hizo un extremo nuevo"? (sinergia, R neto)**

| Momento | Resolución | NQ D-RSI | NQ D-DELTA | ES D-RSI |
|---|---|---|---|---|
| En la ruptura (V-RUP) | 1 min | **−0,13** [−0,16; −0,10] | −0,00 [−0,03; +0,02] | **−0,05** [−0,08; −0,02] |
| En la ruptura (V-RUP) | 5 min | **−0,10** [−0,17; −0,03] | −0,04 [−0,09; +0,01] | −0,02 [−0,10; +0,06] |
| En la confirmación (V-CONF) | 1 min | +0,01 [−0,01; +0,03] | −0,02 [−0,05; +0,00] | **+0,03** [+0,01; +0,06] |
| En la confirmación (V-CONF) | 5 min | −0,02 [−0,07; +0,03] | +0,01 [−0,05; +0,06] | −0,01 [−0,06; +0,04] |

(Target 1R; 2R da lo mismo. Sensibilidad: RSI 7 y 21 dan el mismo signo en la ruptura: NQ −0,17 y −0,11; ES −0,08 y −0,04.)

**Lectura:**
1. **En la ruptura, la divergencia del RSI empeora ir contra el extremo, en los dos instrumentos**, y es robusta al largo del RSI. Es lo contrario de lo que promete el folklore.
2. **En la confirmación no agrega nada**, salvo +0,03 R en ES 1 min. Ese valor es chico y la celda sigue perdiendo: R −0,17.
3. **La divergencia de delta (NQ) tampoco agrega nada** en ningún momento ni resolución.
4. **Hallazgo lateral (ES y NQ): ir contra un extremo nuevo ya confirmado acierta menos que el azar.**
   - ES 1 min: 0,394 contra N1 0,446 a 1R, y 0,207 contra 0,302 a 2R.
   - NQ 1 min: 0,43 contra 0,475.
   - Después de un máximo más alto confirmado (retroceso del 30 %), el precio tiende a volver a buscar el máximo: persistencia a la escala del pivote.
   - Junto con TREND-MICRO B3 (la continuación en el disparo de una expansión también falla más que el azar), dibuja un patrón de "vender el impulso, comprar el retroceso". **Es una pista descriptiva, no una sugerencia**: invertir las operaciones no da automáticamente una esperanza positiva (cambia la geometría y los costos), y necesitaría su propio pre-registro.

**Alcance de la muerte:**
- **Muere:** la divergencia de RSI (7, 14 y 21) o de delta como señal para ir contra un extremo nuevo de pivote, en ruptura o en confirmación, en 1 y 5 min, en ES y NQ, jul-2025 a mar-2026, con estas salidas.
- **No muere:** otros usos de la divergencia (salida de una posición a favor, filtro de otras familias); no se midieron.

**F9:** esta familia la usó y queda cerrada; la pausa sigue para cualquier otro indicador.
