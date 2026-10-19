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

## 6. Resultado E1 (26/09; `artifacts/vrev/report_e1.json`, sha `cc24e6443d72`, controles con cobertura ≥ 98 %, auditoría PASS)
**Estados de las 128 celdas:** INFO− 96 · SIN_INFO 32 · INFO+ 0 · SIN_POTENCIA 0. **Ninguna pasa a E2.**

**Qué dice, con alcance preciso:**
- En las 4 activos, 4 confirmaciones, 4 X y 2 stops, entrar hacia el VWAP **en el primer alejamiento ≥ X ATR de vela de 25 ticks** (o hasta 30 velas después, con C1–C3) llega al VWAP **menos** que una barra con el mismo estado, a la misma hora, en otra sesión. La brecha crece con X: ES X6 C0 k1, 14,2 % contra 16,3 %; MYM X6 C0 k2, 22,7 % contra 30,7 %; YM X6 C0 k1, 13,6 % contra 22,0 %.
- La distancia al objetivo está emparejada (real 5,38 contra control 5,35 ATR en ES X6), así que no es un sesgo del control.
- **Lectura:** el momento del **primer** alejamiento lleva **inercia de continuación**. Es coherente con AGOT-EXT (ir contra un extremo recién confirmado rinde peor que el azar). Ninguna de las confirmaciones probadas (C1–C3) la neutraliza.
- **Económico:** el recorrido neto de costo es negativo en 127 de 128 celdas; la única positiva (YM C0 X4 k2, +0,3 t) es INFO−.

**Lo que esto NO descarta (regla §0):**
- **La reversión al VWAP como mecanismo general.** Ni siquiera la variante del mapa información/costo, que tenía timing fino y horizonte corto.
- **Alejamientos grandes en escala diaria:** acá X está en ATR de vela de 25 ticks, así que X = 6 es un alejamiento moderado dentro del día. Faltan X en ATR diario o en σ de bandas de VWAP.
- **Entrar después del agotamiento de la inercia**, no en el primer alejamiento: por ejemplo, tras N velas sin nuevo extremo, tras una divergencia de flujo o tras absorción en el extremo.
- Todo lo del §5 (VWAP anclado, objetivos parciales, confirmaciones de flujo/L2, velas de tiempo, filtros de régimen, otros activos).

**Candidata nueva, no evaluada acá:** la continuación después del primer alejamiento (el signo inverso de INFO−). Es otra hipótesis: requiere registro y manifiesto propios, y no se reinterpreta este resultado como prueba de ella.
