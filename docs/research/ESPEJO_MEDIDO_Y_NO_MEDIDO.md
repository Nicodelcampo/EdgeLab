# Familia ESPEJO — qué está medido y qué NO (registro vivo, desde 2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`

## 0. Para qué sirve este registro (pedido explícito de Nico, 2026-09-26)

Los estudios de espejo que se corrieron hasta ahora son un **tamiz**: contestan «¿vale la pena seguir investigando la
idea del espejo?», no «¿el espejo existe?».

- **Un SÍ del tamiz** autoriza experimentos más detallados, rigurosos y abarcativos, con más variantes.
- **Un NO del tamiz no cierra la familia.** Sólo invalida exactamente lo que dice la columna «Medido» de §2. Para
  cerrar la idea del espejo hace falta haber cubierto los ejes de §3 (regla de §4), algo que hoy está lejos de pasar.
- **Regla permanente del proyecto que se aplica acá:** toda muerte tiene alcance preciso. Ampliarla a toda la familia
  exige evidencia propia.

## 1. Veredicto del tamiz hasta hoy: **SÍ, seguir** (provisional, faltan las replicaciones)

- La semejanza de la vuelta con el impulso tiene el mismo signo en MNQ 25 t (2025) y en SPY 5 y 15 min (2008–2021).
- En SPY, la vuelta que ya recorrió el 75 % completa el espejo más que el azar en todas las configuraciones con
  muestra; al 40 % completa menos.
- Pendiente: replicación en MNQ 12-25 y 03-26 (25 t) y en ES (5 y 15 min).

## 2. MEDIDO (exactamente esto, y nada más)

| Estudio | Mercado / período | Velas | Impulso | Evento | Semejanza | Resultado medido | Nulo | Qué dio |
|---|---|---|---|---|---|---|---|---|
| TBZX-ESPEJO (25/09) | ES y NQ, jul-25 a mar-26 | 25 ticks | TBZX: **eficiencia ≥ 0,6**, fin al retroceso 0,3; 12 configuraciones | salida y reingreso a la franja A–B | no | llega a A, penetración, excursión, tiempo afuera | fantasma a la misma hora, N-VOL, N-REV | ES +5 pp sobre N-VOL; NQ desaparece contra N-REV |
| ESPEJO-SIM (26/09) | MNQ 09-25 (descubrimiento); 12-25 y 03-26 pendientes | 25 ticks | TBZX (eficiencia ≥ 0,6); grilla 3 × 5, W de 17 a 68 t | primer cierre en que la vuelta pasa x ∈ {0,4; 0,5; 0,75} | vel, efi, forma, ondas → S | espejo completo (A antes que un extremo nuevo), 200 velas | exacto f (al cierre; el del extremo está sesgado) | parecidas − poco parecidas: +1,5 a +4,9 pp con W = 17 t; resto ruido |
| ESPEJO-MACRO (26/09; `artifacts/research/espejo_macro/SPY/`) | SPY RTH 2008–2021, 3.347 días (descubrimiento); ES RTH jul-25 a mar-26 pendiente | 5 y 15 min, tiempo | TBZX (eficiencia ≥ 0,6), W ≥ k·ATR14, k ∈ {3, 4, 6}; 18 configuraciones | igual que ESPEJO-SIM | igual | igual, dentro de la sesión RTH | exacto f al cierre | parecidas − poco parecidas: +3 a +11 pp en 5 min; al 75 %: +6 a +16 pp sobre f; al 40 %: −2 a −12 pp |

**Reglas de lectura (declaradas después de ver SPY; no cambian ningún número):** no se interpreta ninguna celda con
n < 30 por tercil. Con 3–15 eventos, el bootstrap por sesión colapsa y produce «significativos» de ±30–40 pp que son
artefactos.


### Actualización 2026-09-26 (noche) — replicación ES de ESPEJO-MACRO

- **Sin potencia:** 198 días RTH; MDE ≈ 30 pp en la prueba principal, contra un efecto en SPY de 4–11 pp. Ninguna
  prueba sostiene y E2 no se calcula.
- **Concordancia de signo con SPY:** 10 de 10 en la prueba principal, 11 de 15 en el exceso general. Es descriptiva.
- **Tamiz: sigue en SÍ.** Lo que falta es muestra, no una idea distinta.
- **Nuevo ítem NO MEDIDO:** ES con muestra suficiente (más historia, sesión completa, NQ o YM macro).


### Actualización 2026-09-26 (madrugada) — NQ, YM y ES sesión completa (enmienda 2 de ESPEJO-MACRO)

- **Semejanza (T3 − T1):** no replica en la combinada RTH de futuros. En ES sesión completa es positiva en todas las
  celdas (descriptiva). Queda **sin confirmar, no muerta**.
- **Exceso al 75 %:** replica en futuros. En 5m_12_4: combinada +9,4 pp [+2,2, +16,1], con signo + en ES, NQ e YM.
- **E2 en ES:** G positivo, de +1,5 a +2,6 t en sesión completa, con IC que cruza el cero. Sin candidato robusto.
- **Tamiz: SÍ.** Siguiente paso sugerido: mapa de MAE/MFE de los eventos del 75 % para mejorar la entrada y el stop
  (análisis micro dentro de la ventaja macro).


### Actualización 2026-09-26 — replicación de ESPEJO-SIM en MNQ (25 ticks)

- **La semejanza (T3 − T1) SOSTIENE en MNQ** en 09-25, 12-25 y 03-26 con `minW` 17 y 24: de +2 a +5 pp, con IC > 0
  en las tres. Son 43 de 52 pruebas candidatas.
- **Es la primera evidencia replicada de la familia.** A esta escala no paga (costo/W ≈ 10–14 pp). Sirve como
  **filtro micro** dentro de la ventaja macro.

## 3. NO MEDIDO (por eso un NO de hoy no alcanza para descartar la idea)

### 3.1 La definición del impulso — **el hueco más grande**
- **Impulsos ineficientes.** La tesis de Nico es que el impulso explora el rango «de manera ineficiente y forzada».
  **Todo lo medido usa el detector TBZX, que exige eficiencia ≥ 0,6: impulsos eficientes.** La población que describe
  la tesis no se midió todavía.
- Impulsos definidos por volumen: poco volumen por tick (empuje sin participación), delta agresor, desbalance.
- Otros detectores: zigzag, swings por ATR, pivotes, rango de sesión, ruptura de rango previo.
- Otros tamaños: por debajo de 17 t (sin sentido económico) y por encima de 6 ATR (poca muestra en SPY).
- Retroceso de fin de impulso distinto de 0,3; duración máxima fuera de la grilla.

### 3.2 El «afloja» (agotamiento)
- Ningún estudio mide el punto de agotamiento: caída de velocidad, caída del volumen agresivo, absorción, divergencia
  de delta. El evento se definió por cuánto recorrió la vuelta, no por señales de que el empujador se retiró.

### 3.3 La semejanza
- Sólo cuatro medidas: velocidad, eficiencia, RMSE de forma con 20 puntos, cantidad de ondas con zigzag de 0,1 W.
- **No medidas:**
  - DTW;
  - correlación de retornos vela a vela;
  - simetría de duración (la vuelta tarda lo mismo que el impulso);
  - simetría de volumen;
  - amplitud de las ondas internas;
  - semejanza del delta;
  - semejanza ponderada al tramo más reciente;
  - aprendizaje de la semejanza (sólo como exploración).
- El tramo espejo se compara contra el final del impulso invertido. No se probó contra el impulso completo reescalado
  ni contra su inicio.

### 3.4 El evento y el resultado
- **Estado continuo** (cada vela de la vuelta) en vez del primer cruce de x.
- Otros x: 0,2–0,3 (antes del fin de impulso), 0,6, 0,9.
- Otros resultados:
  - espejo parcial (llegar a 0,9 o a 1,2 W);
  - sobrepaso de A;
  - **tiempo hasta A comparado con la duración del impulso**;
  - excursión máxima con stop parcial.
- Horizontes: overnight y varios días. ESPEJO-MACRO resuelve dentro de la sesión RTH, y eso censura justo los
  impulsos de la tarde.

### 3.5 Mercados, períodos y velas
- Instrumentos no medidos: NQ y YM a escala macro, CL, GC, 6E, ZB, cripto, acciones individuales.
- SPY después de 2021 y antes de 2008; ES antes de jul-2025; confirmación abr–jun.
- ES en sesión completa (sólo RTH es principal); ETH aislada (Asia y Europa).
- Velas de volumen, de rango, Renko, 1 min, 1 h, diario.

### 3.6 Contexto y regímenes
- Volatilidad (VIX o ATR relativo), tendencia de fondo, hora del día, noticias, apertura y cierre, días de vencimiento.
- **Asimetría alcista y bajista:** los resultados están agregados sobre las dos direcciones.
- Secuencias: espejos anidados, dobles espejos, espejo de un espejo.

### 3.7 Ejecución y economía
- La parte económica (E2) sólo está diseñada para ES, con costo de 2,4 t, 1 t de deslizamiento en el stop, entrada al
  cierre y ejecución a nivel de vela.
- **No medidos:**
  - entradas límite en x;
  - stop parcial o dinámico;
  - objetivo parcial;
  - salida por tiempo;
  - sizing;
  - otros costos: micro contra mini, prop firm;
  - fill real con ticks.

## 4. Regla para cerrar la familia ESPEJO (fijada ahora)

La idea del espejo se da por descartada **sólo si** da NO, con potencia publicada (MDE menor que el costo/W relevante),
en **todo** esto:

1. impulsos eficientes **e** ineficientes (§3.1);
2. al menos una definición de agotamiento (§3.2);
3. al menos dos familias de semejanza más allá de las cuatro actuales, incluida la simetría de duración (§3.3);
4. estado continuo además del evento (§3.4);
5. al menos dos instrumentos con escala macro, con horizonte más allá de la sesión (§3.4 y §3.5);
6. las dos direcciones por separado (§3.6).

Si no se cumple, el estado es **«NO PROBADO»**, nunca «muerto».

## 5. Próximo experimento sugerido si el tamiz sigue en SÍ

- **ESPEJO-INEF:** el hueco de §3.1.
  - El mismo evento y el mismo nulo sobre impulsos **ineficientes** (eficiencia < 0,6) y de poco volumen por tick.
  - Agrega la simetría de duración como medida de semejanza.
  - Estado continuo como población paralela.
  - En ES y NQ macro, con horizonte hasta el cierre del día siguiente.
- Va con pre-registro propio. Es la prueba más cercana a la tesis literal de Nico.

## 6. Cómo mantener este registro

Cada resultado nuevo de la familia se agrega en §2 **en el mismo commit** que el resultado, y se tacha lo
correspondiente de §3.
