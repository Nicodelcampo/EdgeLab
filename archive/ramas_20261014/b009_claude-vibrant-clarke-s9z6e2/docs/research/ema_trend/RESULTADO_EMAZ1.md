# EMAZ-1 — calibración descriptiva de zonas EMA-estables (NQ 25T, EMA 200)

**No es una prueba de hipótesis ni evidencia de edge.** Describe cuántas zonas marca cada configuración en la historia de NQ de edgelab (sesiones aprobadas 2025-07-01..2026-09-30, 6 contratos, 25 ticks) para elegir presets razonables. Las capturas del usuario son posteriores al holdout: se usaron solo para entender la lógica (escala ≈ 1 px = 1 barra, ajustada con la EMA dibujada; zonas de 165 a 540 barras) y no para ajustar umbrales.

## Qué se encontró
- El detector original (ventana 300, side 0,97, drift 1,2) marca ~6 % de las barras (≈4–7 zonas por sesión): coincide con «marca pocas zonas» en el gráfico.
- La calibración sobre las capturas solas daba 35–70 % de barras marcadas en la historia (demasiado ruidoso), así que se descartó: los umbrales se eligieron con la historia, buscando una cantidad razonable de zonas largas.
- Grilla de 144 configuraciones (M 100–200, K 100–150, drift 0,5–1,2 ATR, side 0,9–0,95, eficiencia 0,5–0,7, CV 0,3–0,5). El factor que más controla la cantidad es la exigencia de **desplazamiento de la EMA (drift)**.

## Presets (en `nt8/EmaStableTrend.cs`)
| Preset | Parámetros | Barras marcadas | Zonas/sesión | Largas (≥150 barras)/sesión | Duración mediana | Recorrido mediano |
|---|---|---:|---:|---:|---:|---:|
| 1 Pocas | M200 K150 f0,95 er0,7 cv0,3 drift0,8 | 6,5 % | 8,8 | 3,1 | 122 barras | 12 pts |
| **2 Normal** | M200 K150 f0,95 er0,7 cv0,5 drift0,8 | 15,9 % | 18,0 | 8,7 | 146 barras | 14 pts |
| 3 Muchas | M150 K100 f0,9 er0,7 cv0,5 drift0,5 | 28,1 % | 34,5 | 14,1 | 130 barras | 13 pts |
| (original) | W300 f0,97 er0,85 drift1,2 | 6,5 % | 6,6 | 3,8 | 162 barras | 15 pts |

(Zonas por sesión cuenta tramos continuos, incluso los cortos; con `MinZoneBars` = 120 solo se confirman los que llegan a esa longitud. Zonas arriba/abajo: aprox. 55 % / 45 %.)

## Longitud de la zona (lo que pidió el usuario)
Nuevo parámetro `MinZoneBars` (por defecto 120): la zona se confirma, y `State` pasa a ±1, recién cuando lleva esas barras; opcional `MinMovePoints`. Con ello la zona útil dura ≥ 120 barras (mediana de las confirmadas ~150–200) y recorre del orden de 12–40 puntos de NQ. Costo: la confirmación llega 120 barras después del inicio; la línea azul se dibuja retroactiva desde el inicio.

## Lo que NO se sabe
- Si operar estas zonas tiene ventaja. Deriva posterior media a favor de la tendencia dentro de las zonas (ticks de 0,25 pt por 100 barras): Normal +0,57, Pocas +0,51, Muchas −0,09, original −1,52; una regla trivial (solo pendiente de la EMA) da −0,4 a −0,5. Diferencias de décimas de tick, barras solapadas, sin costos: es descripción, no una prueba. La pregunta del usuario (¿al darse vuelta el precio atraviesa/continúa más de lo que rebota?) necesita una medición pre-registrada aparte, como VIO-1.
- Que el indicador compile en NT8 (no hay compilador acá; la lógica es la de `edgelab/research/ema_zones.py`, probada en Python con `tests/test_ema_zones.py`).
- El «ATR» del indicador es la media simple de (High−Low) en 100 barras, no el ATR de Wilder de NT8, porque así se calibró.


## Corrección (2026-10-13, tras la observación del usuario)
- Las 4 líneas azules del montaje inicial **no eran del usuario**: eran las del indicador anterior (la EMA desplazada), y se había dicho por error que eran trazadas a mano. La **única** línea hecha a mano es la de la última captura (NQ 12-26, 13/10/2026, 15:59), la más empinada.
- Esa línea es una **tangente**: el precio queda por debajo (resistencia bajista) y casi nunca la cruza. El indicador anterior dibujaba la EMA desplazada por la distancia media, que atraviesa el precio por cualquier lado.
- Por eso el indicador v3 dibuja una tangente (`fit_trendline`). Verificación real: sobre esa captura (digitalizada) el ajuste da pendiente 0,878 vs 0,877 de la línea del usuario, con 0 cruces, anclada en el máximo del inicio y con 3 toques. Parámetros estrictos: tolerancia de toque 0,2 ATR y ≤ 2 % de barras cruzando. Los parámetros más laxos (10 % de cruces) que se habían elegido usando las líneas del indicador viejo como si fueran del usuario quedaron **descartados**.
- Validación: 1 línea, 1 captura. No se calibró nada más contra capturas.

## EMAZ-3 — indicador v3 completo (tangente estricta + distancia constante) en la historia de NQ
Réplica del indicador (`simulate_zones`) sobre NQ 25T, EMA 200, sesiones aprobadas 2025-07-01..2026-09-30 (6 contratos). Descriptivo, sin P&L. Tangente: toque 0,2 ATR, ≤ 2 % de barras cruzando, ≥ 3 toques; distancia constante: variación de los extremos de alejamiento/acercamiento ≤ umbral del preset. 68 minutos de cómputo (luego optimizado ~5×).

| Preset (alejamiento/acercamiento máx.) | Tramos EMA | **Zonas confirmadas** | Por sesión | Largo mediano (p10–p90) | Recorrido mediano (pts) | Demora de confirmación mediana |
|---|---:|---:|---:|---|---:|---:|
| 1 Pocas (0,3 / 0,4) | 5.483 | 104 | 0,37 | 258 (228–368) barras | 31 | 199 barras |
| 2 Normal (0,4 / 0,5) | 5.483 | 276 | 0,99 | 290 (228–480) | 47 | 217 |
| 3 Muchas (0,6 / 0,7) | 11.477 | 987 | 3,55 | 292 (182–514) | 44 | 230 |

- La mitad aprox. son alcistas y la mitad bajistas; todas tocan la tangente 3–4 veces (el mínimo exigido es 3).
- **Advertencia importante — demora:** la zona se confirma ~200 barras después de su inicio (lo que tarda la ventana de detección). Del largo mediano (~260–290 barras) solo quedan ~60–90 barras *después* de confirmada. El inicio de la línea es retroactivo; como área de trading en tiempo real, la parte utilizable es la posterior a la confirmación.
- 64–76 % de las zonas terminan por ruptura de la tangente (cierre a > 0,5 ATR), el resto cuando termina el tramo de la EMA.
- **Deriva posterior a la confirmación** (ticks de 0,25 pt, a favor de la tendencia, media por zona; solapada y sin costos): Pocas +0,0/+0,9/+3,2 (50/100/200 barras), Normal −1,8/−3,0/−8,0, Muchas −0,3/−0,0/+2,8. Sin signo consistente: no hay evidencia de continuación; la pregunta del usuario requiere una medición pre-registrada específica.
- Archivo: `EMAZ3_RESULTADOS.json`.

## EMAZ-5 — con los filtros de utilidad del usuario (desplazamiento ≥ 10 ATR, distancia media ≤ 4, máxima ≤ 8,5)
| Preset | Zonas confirmadas | Por sesión | Largo mediano | Recorrido mediano | Demora de confirmación | Terminan por ruptura/alejamiento |
|---|---:|---:|---:|---:|---:|---:|
| 1 Pocas | 55 | 0,20 | 234 barras | 32 pts | 199 | 93 % |
| 2 Normal | 100 | 0,36 | 236 | 44 pts | 199 | 95 % |
| 3 Muchas | 267 | 0,96 | 230 | 37 pts | 205 | 94 % |
- Los filtros bajan las zonas a un tercio (987 → 267 en «Muchas»): se eliminan las cortas, planas y deformes.
- **Problema abierto:** la zona se confirma ~200 barras después de su inicio y su largo mediano es ~235: quedan ~35 barras *después* de confirmada hasta que termina. Como área operable en tiempo real casi no sobra recorrido. Se prueba EMA 100 (confirmación más temprana) y la condición de EMA recta (R²) en EMAZ-6.
- Deriva posterior a la confirmación sin signo consistente (Pocas +2,8/+5,5/+12,8 ticks a 50/100/200 barras con n = 55; Normal y Muchas negativas): no hay evidencia de continuación.

## EMAZ-6 — EMA 100 vs 200 y condición de EMA recta (R²)
Mismos filtros de utilidad que EMAZ-5; umbrales de distancia constante «Normal» (0,4/0,5). EMA 100 usa M=100, K=75.

| Variante | Zonas | Por sesión | Largo mediano | Demora de confirmación | Restante tras confirmar |
|---|---:|---:|---:|---:|---:|
| EMA 200 sin R² | 100 | 0,36 | 236 | 199 | ~37 barras |
| EMA 200 + R² ≥ 0,98 | 109 | 0,39 | 238 | 200 | ~38 |
| EMA 100 sin R² | 166 | 0,60 | 162 | 131 | ~31 |
| EMA 100 + R² ≥ 0,98 | 202 | 0,73 | 160 | 132 | ~28 |
| EMA 100 + R² ≥ 0,99 | 293 | 1,05 | 153 | 130 | ~23 |

- EMA 100 confirma antes (131 vs 199 barras) pero las zonas también son más cortas: **sobra lo mismo (~25–35 barras)**. La condición de EMA recta casi no cambia el resultado: con estos umbrales no es selectiva (la EMA ya es lisa) y, al cambiar la estructura de los tramos, hasta suma zonas.
- Conclusión: el cuello de botella no es la elección de la EMA sino el diseño: la zona se reconoce con una ventana de 100-200 barras y se confirma recién al completarla. Para que sea operable en tiempo real hay que **detectarla por la propia tangente** (confirmar al tercer toque con desplazamiento suficiente), usando la EMA solo como contexto de dirección y rectitud con ventanas cortas. Pendiente de implementar.

## EMAZ-8/9 — extensión hacia atrás (todo el recorrido) y número de anclas
La línea ahora busca su ancla hasta `ExtendBars` (100) barras antes del inicio detectado, y la distancia constante se mide desde el ancla. Con pocas anclas candidatas (2–4) la extensión hacía desaparecer casi todas las zonas (EMAZ-7: 11; EMAZ-8: 89 de 766): los extremos previos ganaban el ranking y no pasaban los filtros. Con **12 anclas** (se prueba cada pivote extremo por orden hasta hallar una línea válida) se recupera:

| Variante (filtros de utilidad del usuario, distancia constante 0,4/0,5) | Zonas | Por sesión | Largo desde el ancla (p10 / mediana / p90) | Recorrido mediano | Deriva a 100 / 200 barras (ticks; n solapado) |
|---|---:|---:|---|---:|---|
| EMA 200, sin extensión | 1.126 | 4,05 | 132 / 182 / 257 | 41 pts | +2,3 / +1,5 |
| **EMA 200, extensión 100** | **630** | **2,27** | **171 / 215 / 284** | 44 pts | +2,7 / +3,4 |
| EMA 100, extensión 100 | 549 | 1,97 | 130 / 162 / 221 | 45 pts | +1,8 / +0,2 |

- La extensión alarga la zona marcada (mediana 182 → 215 barras, p10 132 → 171) y descarta casi la mitad de las zonas (las que no tienen un extremo claro de arranque).
- Indicador v3.2: Preset 2 por defecto = «EMA 200, extensión 100, 12 anclas» (~2,3 zonas por sesión). La deriva posterior a la confirmación es de décimas de punto, sin significancia (barras solapadas, sin costos): no hay evidencia de continuación.
- Corridas: emaz-1..9 (Kaggle `edgelab-emaz-*`); resultados en `EMAZ*_RESULTADOS.json`.
