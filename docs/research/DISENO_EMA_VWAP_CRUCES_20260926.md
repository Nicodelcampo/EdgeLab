# Diseño: cruces EMA × VWAP en MYM (familia EVX) — 2026-09-26

**Estado:** DISEÑO VISUAL. Sin mediciones ni resultados. La prueba masiva de configuraciones corre sólo después de este diseño, con registro de familia, manifiesto (event-space, nulos, presupuesto) y OK de Nico (regla STOP).
**Instrumento:** MYM (datos de Lucid, canonizados, no publicables). Exploración ≤ 2026-03-31; abr–jun reservado; holdout intacto.
**Aprendizajes heredados:** los cruces de medias suelen morir con costos y *data snooping* (ver la investigación del 26/09). El control tiene que emparejar actividad y estado (N-REVVOL, TBZX). El estiramiento respecto de las medias no aportó nada propio en TBZX.

## Evento
**Cruce EVX:** la EMA(p) de los cierres de velas de 25 ticks cambia de lado respecto del VWAP de sesión (precio típico, reinicio en la pausa diaria). EMA sobre VWAP → largo; bajo VWAP → corto. Se ignoran las primeras `warmup` velas de cada sesión (el VWAP recién reiniciado es ruido). Todo es causal: se decide al cierre de la vela del cruce.

## Filtros (sobre el tramo previo, entre el cruce anterior y este)
- `minSideBars` / `minSideSecs`: cuánto tiempo estuvo la EMA del otro lado;
- `minMaxDist`: cuánto se alejó la EMA del VWAP en ese tramo (máximo |EMA − VWAP|, en ticks);
- `volMin` / `volMax`: volumen negociado desde el cruce anterior hasta este.

## Modos de entrada
- **M0 al cruce:** entrada al cierre de la vela del cruce.
- **M1 retroceso:** después del cruce, límite en la EMA; se llena si en `pbBars` velas el precio toca la EMA desde el lado nuevo. Si no, no hay entrada.
- **M2 confirmación:** entrada al cierre de la vela `confBars` después del cruce, sólo si la EMA siguió del lado nuevo todo ese tiempo.
- **M3 vuelve al VWAP** (pedido de Nico): después del cruce, límite en el VWAP; se llena si en `pbBars` velas el precio lo toca desde el lado nuevo.

## Stop y objetivo (variantes, sólo como niveles; no se simula la salida en el visor)
- **SL:** `slMode` 0 = ticks fijos desde la entrada · 1 = más allá del VWAP por `slTicks` · 2 = más allá del extremo del tramo previo por `slTicks`. Si queda del lado equivocado, 1 tick.
- **TP:** `tpMode` 0 = múltiplo `tpR` del riesgo · 1 = `tpTicks` fijos.
- `hold`: largo de la caja dibujada (tiempo máximo candidato).
- Pendiente: salida por cruce opuesto, costos MYM propios (no se transportan de ES).

## Justificación económica y cómo podría refutarse
El VWAP de sesión es la referencia de precio de los institucionales; que la EMA lo cruce después de un tramo largo y alejado indicaría un cambio de control del flujo. **Se refuta** si, con costos realistas de MYM, la expectativa neta no supera a la de cruces fantasma emparejados por hora, actividad y estado (N-REVVOL), o si no sobrevive a la corrección por la cantidad de configuraciones probadas.

## En el visor
Parámetros → **✖ Cruces EMA × VWAP (diseño)**. Todos los parámetros de arriba tienen control deslizante. Cruce que pasa los filtros = triángulo de color; filtrado = gris. Entrada según el modo = punto negro con etiqueta. Clic en un cruce → sus valores. Muestra el conteo de cruces por día.
