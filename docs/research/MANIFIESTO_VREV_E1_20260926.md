# Manifiesto VREV (reversión al VWAP desde un alejamiento X, con confirmaciones) — registro y E1, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Aprobación:** Nico en chat, 26/09 («OK»), con una instrucción de método explícita: **no descartar mecanismos generales cuando sólo se descartó una variante particular.**
**Herramienta:** `tools/vrev.py`. Ledger: `artifacts/hippocampus/vrev_20260926.jsonl`. Infraestructura heredada de EVX (velas de 25 ticks, contrato canónico, control de mismo estado); no hereda resultados ni presupuesto.

## 0. Regla de alcance (primera regla de esta familia)
- Toda conclusión se enuncia **por celda**: (activo, X, confirmación, stop k, horizonte). Nunca «la reversión al VWAP no funciona».
- Cada celda termina en uno de cuatro estados:
  - **INFO+**: supera al control con FDR;
  - **INFO−**: rinde peor que el control con FDR;
  - **SIN_INFO**: IC que incluye 0 y **MDE ≤ 0,1** en acierto; se descarta sólo esa variante, y sólo por encima de su MDE;
  - **SIN_POTENCIA**: MDE > 0,1 o n < 100. **No se descarta nada.**
- El reporte publica la **lista de lo no medido** (§5). La familia sólo se podría cerrar con evidencia sobre esa lista, no por extrapolación.
- Antecedente que motiva la familia: el mapa información/costo encontró información en la reversión al VWAP con timing (5/5), pero con tamaño menor que la fricción. **Esta familia no la refuta ni la confirma**: prueba otra variante (alejamiento grande con confirmación) cuyo objetivo es que el recorrido supere al costo.

## 1. Evento, dirección y confirmaciones
- **Alejamiento:** la primera vela en que |cierre − VWAP| ≥ X·ATR, con X ∈ {2, 3, 4, 6}. Se rearma cuando el precio vuelve a menos de X/2 ATR. Fuera de las primeras 50 velas de la sesión. Dirección: hacia el VWAP.
- **Confirmación** (dentro de W = 30 velas desde el alejamiento; si no ocurre, no hay entrada):
  - **C0** ninguna: entrada en la vela del alejamiento;
  - **C1** cruce de EMA(9) y EMA(21) hacia el VWAP;
  - **C2** cierre que cruza la EMA(21) hacia el VWAP;
  - **C3** primer retroceso: cierre a ≤ (X − 0,5) ATR del VWAP.
- **Entrada:** cierre de la vela de confirmación (en velas de tick, la apertura siguiente queda a ±1 tick).

## 2. Resultado (E1 con economía incluida)
- **Objetivo:** el VWAP **fijado en la vela de entrada**. **Stop:** entrada − dir · k·ATR, con k ∈ {1, 2}. Horizonte: 200 velas o fin de sesión.
- **Medida primaria:** acierto (toca el objetivo antes del stop; si toca los dos en la misma vela, cuenta como stop).
- **Secundarias:**
  - R bruto por evento (salida en objetivo, stop o tiempo);
  - recorrido esperado en ticks **menos el costo del activo**;
  - retorno direccional a 20, 60 y 200 velas.
- **Costo provisional por activo** (ida y vuelta, en ticks; propio de cada instrumento, no transportado): ES 1,4 · NQ 2,0 · YM 2,0 · MYM 3,0. Incluye spread y comisión, más 1 tick de slippage en el stop. Es provisional: se estima con datos en E3.

## 3. Controles
- **Mismo estado:** 3 barras de otras sesiones, a la misma hora (± 1 h), con la misma distancia firmada al VWAP en ATR, la misma pendiente de la EMA(21) y la misma actividad previa (±50 % o ±0,15 ATR). Misma dirección (hacia su propio VWAP), mismo k, objetivo en su VWAP.
- **Geométrico:** N1 = s / (s + r + 1). Descriptivo.
- **Dos canales:** acierto (direccional) y |retorno| (no direccional).

## 4. Prueba y multiplicidad
- 4 X × 4 confirmaciones × 2 k × 4 activos = **128 celdas** en la medida primaria (acierto real − control, pareado, bootstrap por sesión, BH q = 0,10).
- **Pasa a E2** la celda INFO+ con R bruto real > R bruto del control, recorrido neto de costo > 0 y el mismo signo en las dos mitades del período.

## 5. Lo que NO se mide aquí (queda abierto, no descartado)
Otras distancias (X < 2 o X en σ de bandas de VWAP); VWAP anclado (semanal, desde eventos, desde el máximo o mínimo del día); objetivo parcial (50 % del camino) o por bandas; entradas límite o escalonadas; confirmaciones de flujo (delta, absorción, L2, icebergs); velas de tiempo (1 o 5 min); otros horizontes o salidas; otros activos (6E, GC, ZB); filtros de régimen (tendencia del día, gap, tipo de día); la variante del mapa de costos (timing fino, horizonte corto).
