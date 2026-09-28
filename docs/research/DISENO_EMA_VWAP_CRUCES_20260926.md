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

## Salidas (26/09)
Dentro de cada vela, orden conservador: primero el **SL** (se toca) y después el **TP** (hay que atravesarlo por 1 tick). Las salidas por cierre se ejecutan en la apertura de la vela siguiente:
- `xOpp`: **cruce opuesto** EMA × VWAP;
- `xTrail`: cierre del otro lado de la EMA (trailing por la media);
- `beR`: stop a break-even cuando el precio llega a x R;
- `xSession`: cierre al final de la sesión (al último cierre);
- `hold`: tiempo máximo en velas.

`showOut` muestra la salida y el R bruto de cada operación. **Sólo se habilita en bundles de exploración** (última vela ≤ 2026-03-31); el visor lo bloquea en los demás.

## Revisión de las reglas (26/09, antes de medir)
Corregido:
1. **M0 y M2** entraban al cierre de la vela de la señal, que no se puede operar. Ahora entran en la **apertura de la vela siguiente**.
2. **M1 y M3** se llenaban con sólo tocar el nivel. Ahora el precio tiene que **atravesarlo por 1 tick**, la misma convención que en el resto del proyecto.
3. **SL «más allá del VWAP»**: usaba el VWAP de la vela de entrada. Ahora usa el de la **vela anterior**.
4. **SL «más allá del extremo»**: incluía la vela de entrada. Ahora corta en la **vela anterior**.

Conocido y aceptado:

5. La EMA no se reinicia por sesión y el VWAP sí; `warmup` cubre el arranque.
6. El VWAP usa el precio típico de las velas de 25 ticks (H+L+C)/3 como aproximación del precio promedio de cada trade.
7. Límite en velas: sin ticks, el orden dentro de la vela es conservador y la cola de la orden límite no se modela.

## Correr en otros activos
El diseñador ya funciona sobre cualquier bundle del visor (ES, NQ, YM, 6E, GC…). La prueba masiva corre en Python sobre ticks con contrato canónico por activo, con los **costos propios de cada instrumento** (no se transportan). Candidatos: MYM, YM, ES, NQ, 6E, GC. Cada activo es una prueba de la misma familia y cuenta en la multiplicidad.

## Plan de la prueba masiva EVX v1 (26/09) — BORRADOR para OK de Nico, sin ejecutar

### Principio: embudo, no fuerza bruta
Probar todo contra P&L de una vez multiplica la selección espuria y el cómputo. Se usa un **embudo pre-registrado**: cada etapa es barata y descarta lo que no merece la siguiente. El P&L sólo se mira en lo que ya mostró información.

| Etapa | Qué mira | Costo | Mata si |
|---|---|---|---|
| **E0 censo** (target-free) | cruces por día, por activo y período; duración de los tramos; distribución de los filtros | segundos | < 1 cruce por día, o < 300 eventos en la exploración |
| **E1 información** (sin P&L) | retorno direccional a 5, 20, 60 y 200 velas después del cruce, contra el control | minutos | IC que cruza 0 contra el control, o efecto < MDE |
| **E2 P&L bruto** | grilla de entradas × salidas, sólo en las celdas que sobrevivieron E1 | minutos | expectativa bruta ≤ control con las mismas salidas |
| **E3 neto** | costos propios del activo (spread observado + comisión + 1 tick de slippage en stops) | segundos | IC neto ≤ 0 |
| **E4 robustez** | mitades, meses, vecinos en la grilla, PBO (CSCV) y DSR (`edgelab/research/g2.py`) | minutos | PBO > 0,5, DSR < 0,95, o pico aislado (los vecinos no acompañan) |
| **E5 confirmación** | abr–jun, una sola apertura, sólo 1–3 configuraciones | — | según los gates G0–G5 |

### Controles (lo aprendido en TBZX)
1. **Control de evento:** cruce fantasma en **otra sesión, a la misma hora, con la misma actividad previa y el mismo estado** (distancia |EMA − VWAP| y pendiente de la EMA a ±25 %). Corta la trampa «mercado movido + estado».
2. **Control de salidas:** **entradas al azar con las mismas reglas de salida** (misma hora, misma dirección). El trailing por la EMA, el cruce opuesto o el break-even pueden generar resultado sin que el cruce aporte nada. Una celda sólo sobrevive si le gana a **las dos** cosas: al cruce fantasma y a la entrada al azar con sus salidas.
3. **Signo invertido** como diagnóstico: si el lado contrario da parecido, es volatilidad y no dirección.

### Robustez de las lógicas
- **Parámetros portables entre activos:** las distancias (SL, TP fijo, alejamiento, margen) se expresan en **unidades de ATR de sesión**, no en ticks, y los filtros de tiempo y volumen en **cuantiles del propio activo** (terciles). La misma regla significa lo mismo en MYM y en 6E, y la grilla se achica.
- **Dos resoluciones:** velas de 25 ticks (principal) y de 1 minuto (réplica). Una lógica que sólo vive en una resolución es sospechosa.
- **Mesetas, no picos:** en E4 se exige que la celda elegida y sus vecinas inmediatas en la grilla tengan el mismo signo.
- **Contrato canónico** por activo (`contract_regime`), holdout y reserva cerrados.

### Grilla (tamaño controlado)
- **EMA:** 21, 55, 144, 377 (4, espaciado log). **Filtros por terciles:** tiempo del otro lado, alejamiento y volumen, cada uno {sin filtro, ≥ T1, ≥ T2} → 27 combinaciones, pero **en E1 se prueban de a un filtro** (1 + 3×2 = 7).
- **Entradas:** M0, M1, M2 (3 velas), M3; esperas de 10 y 30 velas.
- **SL:** 0,5 · 1 · 2 ATR; VWAP + 0,25 ATR; extremo + 0,25 ATR (5). **TP:** 1 · 2 · 3 R, o ninguno (4).
- **Salidas:** {cruce opuesto} × {trailing EMA sí/no} × {break-even en 1 R sí/no} × fin de sesión siempre, con tiempo máximo de 200 velas (4).
- **E1:** 4 EMA × 7 filtros × 4 horizontes = 112 celdas por activo. **E2**, sólo sobre los sobrevivientes: hasta 5 × 4 × 5 × 4 × 4 = 1.600 variantes de salida por celda.

### Cómputo
- **Precálculo único por sesión:** velas de 25 ticks (ya en caché para ES y NQ; MYM desde los parquets canónicos), EMA de los 4 períodos, VWAP y ATR. Los cruces dependen sólo del período, no de filtros ni salidas: **se detectan una vez**. Los filtros son máscaras sobre la tabla de eventos.
- **Simulación en numba:** un kernel recorre cada evento una sola vez y evalúa **todas las variantes de salida a la vez** (vector de estados por variante), en lugar de una pasada por configuración. Estimado: MYM, 181 sesiones × ~10 cruces por día × 1.600 variantes × ≤ 200 velas ≈ 6·10⁸ pasos, unos minutos por activo en esta PC.
- **Máquina:** máximo 2 procesos pesados, lectura por sesión (nunca archivos enteros). Si crece, al kernel de Kaggle, con el mismo patrón que TBZX-R3.
- **Orden de activos:** MYM (objetivo), YM (mismo subyacente: réplica natural), ES, NQ; después 6E y GC. Cada activo es una prueba más de la familia.

### Multiplicidad y presupuesto
- **E1:** BH q = 0,10 sobre 112 × activos. **E2–E4:** PBO y DSR con el número **real** de variantes evaluadas (se registra en el Cerebro); nunca «la mejor» sola: se publica el paisaje completo.
- **Límite:** a E5 pasan 3 configuraciones como máximo, pre-registradas antes de abrir abr–jun.

### Qué necesito de Nico para lanzar
1. OK a este embudo, la grilla y los activos.
2. Confirmar si SL y TP en ATR (portables) está bien, o si preferís ticks.
3. Registro de la familia EVX (independiente de TBZ y TBZX) y OK de STOP para mirar retornos desde E1.
