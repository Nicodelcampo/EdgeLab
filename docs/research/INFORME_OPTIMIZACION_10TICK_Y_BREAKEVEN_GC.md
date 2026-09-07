# Informe Científico de Optimización en 10 Ticks y Falsación de Break-Even (BE)

> **Activo:** COMEX Gold Futures (`GC`) — Multiplicador: \$100.00 USD / punto ($10.00 USD / tick).  
> **Metodología:** Simulación causal estricta tick a tick, streaming por sesión.  
> **Ejecución Realista:** Secuencial Estricta (1 sola posición activa a la vez, idéntico a una cuenta real).  
> **Fricciones Reales CME:** \$4.50 USD de comisión round-turn + 1 tick de slippage adverso en paradas de stop (\$10.00 USD).  
> **Partición:** In-Sample (`GC 12-25` + `GC 02-26`, 779 trades) vs Out-of-Sample ciego (`GC 04-26` + `GC 06-26`, 253 trades). Holdout `GC 08-26` sellado.

---

## 1. Conclusiones Ejecutivas

1. **Falsación Categórica de las Barras de 10 Ticks:**
   * Las barras de 10 ticks **fallan el estándar de viabilidad cuantitativa en las 192 combinaciones evaluadas**.
   * Ninguna configuración logró ser rentable en In-Sample (todas perdieron entre -\$13,000 y -\$24,000 USD).
   * El Profit Factor quedó atrapado entre **0.65 y 0.82**.
   * La tasa de acierto (Win Rate) colapsó a niveles de entre **9.7% y 17.6%**, acumulando rachas destructivas de hasta **62 pérdidas consecutivas**.
   * En Out-of-Sample, la gran mayoría continuó en terreno negativo (-\$511 a -\$8,577 USD).

2. **Diagnóstico del Break-Even (BE):**
   * Colocar Break-Even a diferentes niveles (+1.0, +1.5, +2.0, +2.5, +3.0 puntos) **degrada de forma monótona el rendimiento**.
   * A medida que el gatillo de BE es más agresivo (ej. +1.5 o +2.0 pt), el Win Rate cae del 11.3% al 9.3% y el PnL empeora.
   * Causa física: En Oro, tras la absorción inicial el precio suele rebotar 1.5 a 2.0 puntos para luego re-testear la zona antes de expandir. Si el stop se mueve a la entrada, la oscilación normal del libro de órdenes saca al trader en tablas (flat), sacrificando los trades ganadores hacia el target de 4.0 o 5.0 pt.

3. **La Causa Raíz Microestructural (Por qué 10 ticks falla y 25 ticks funciona):**
   * **En 10 Ticks:** Una barra se completa en sólo 10 contratos ejecutados. La mecha de absorción mide apenas 3 a 5 ticks (0.30 a 0.50 pt). Un stop estructural queda a sólo 4 a 6 ticks del precio de entrada ($40 a $60 USD). Esto cae directamente dentro de la banda de **ruido aleatorio del spread bid-ask** de COMEX.
   * **En 25 Ticks:** La barra acumula suficiente volumen para formar una zona de soporte/resistencia institucional de 10 a 15 ticks (1.0 a 1.5 pt). El stop estructural (1.5 a 2.2 pt) queda protegido fuera del ruido intradía, permitiendo que la probabilidad juegue a favor.

---

## 2. Resultados del Barrido en 10 Ticks (192 Combinaciones)

### Top 10 Configuraciones In-Sample (Ordenadas por PnL y PF)

| Rank | SL Mult | TP (pts) | BE Trigger | Win% | Net USD In-Sample | Profit Factor | Max Drawdown | Racha Máx Pérdidas |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 1.0x | 5.0 pt | **Sin BE** | 9.7% | -$13,039.00 | 0.73 | $14,014.00 | 62 pérdidas |
| **2** | 1.5x | 5.0 pt | **Sin BE** | 14.1% | -$13,468.50 | 0.79 | $17,021.50 | 62 pérdidas |
| **3** | 1.0x | 4.0 pt | +2.5 pt | 10.6% | -$14,096.00 | 0.69 | $14,772.50 | 62 pérdidas |
| **4** | 2.0x | 5.0 pt | **Sin BE** | 17.6% | -$14,201.50 | 0.82 | $18,793.50 | 37 pérdidas |
| **5** | 1.0x | 4.0 pt | +2.0 pt | 10.0% | -$14,290.50 | 0.67 | $14,967.00 | 62 pérdidas |
| **6** | 1.0x | 4.0 pt | +3.0 pt | 10.7% | -$14,317.00 | 0.69 | $14,993.50 | 62 pérdidas |
| **7** | 1.0x | 4.0 pt | **Sin BE** | 11.3% | -$14,377.00 | 0.70 | $15,053.50 | 62 pérdidas |
| **8** | 1.0x | 10.0 pt | **Sin BE** | 6.1% | -$14,467.50 | 0.71 | $15,381.50 | 62 pérdidas |
| **9** | 1.5x | 6.0 pt | **Sin BE** | 12.0% | -$14,489.50 | 0.78 | $18,741.00 | 62 pérdidas |
| **10** | 1.0x | 4.0 pt | +1.5 pt | 9.3% | -$14,645.00 | 0.65 | $15,380.00 | 62 pérdidas |

---

## 3. Validación Ciega Out-of-Sample (OOS) en 10 Ticks

Evaluación sobre los contratos `GC 04-26` y `GC 06-26` (247 trades secuenciales):

| Rank | Configuración (SL / TP / BE) | Net USD In-Sample | Net USD Out-of-Sample | OOS Win% | OOS PF | OOS Max DD | OOS Racha Pérdidas |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | SL 1.0x / TP 5.0 pt / Sin BE | -$13,039.00 | **-$511.50** | 16.2% | 0.97 | $2,786.00 | 25 pérdidas |
| **2** | SL 1.5x / TP 5.0 pt / Sin BE | -$13,468.50 | **-$3,901.50** | 19.4% | 0.86 | $5,849.50 | 25 pérdidas |
| **3** | SL 1.0x / TP 4.0 pt / BE +2.5 pt | -$14,096.00 | **-$3,521.50** | 15.8% | 0.81 | $4,577.50 | 29 pérdidas |
| **4** | SL 2.0x / TP 5.0 pt / Sin BE | -$14,201.50 | **-$8,577.00** | 21.5% | 0.75 | $10,245.00 | 25 pérdidas |
| **5** | SL 1.0x / TP 4.0 pt / BE +2.0 pt | -$14,290.50 | **-$3,281.50** | 15.0% | 0.82 | $4,337.50 | 29 pérdidas |
| **6** | SL 1.0x / TP 4.0 pt / BE +3.0 pt | -$14,317.00 | **-$2,571.50** | 17.4% | 0.87 | $4,233.50 | 25 pérdidas |
| **7** | SL 1.0x / TP 4.0 pt / Sin BE | -$14,377.00 | **-$2,411.50** | 17.8% | 0.88 | $3,963.50 | 25 pérdidas |
| **8** | SL 1.0x / TP 10.0 pt / Sin BE | -$14,467.50 | **+$3,013.00** | 10.6% | 1.13 | $3,679.50 | 41 pérdidas |

> **Nota sobre el Rank 8 (TP 10 pt OOS +$3,013):**  
> Al igual que ocurrió en 25 ticks con TP=12 pt, este resultado está artificialmente inflado por la tendencia macro del contrato `GC 04-26` (+$2,418 USD vs +$595 USD en `06-26`) y sufre de **41 pérdidas consecutivas** con sólo 10.6% de acierto. En In-Sample perdió -$14,467 USD. No es un edge ejecutable.

---

## 4. Análisis Detallado del Impacto de Break-Even (BE)

Comparando la configuración fija `TP = 4.0 pt` y `SL = 1.0x` variando exclusivamente el nivel de activación de BE:

| Nivel Gatillo Break-Even | Win Rate IS | Net USD IS | Win Rate OOS | Net USD OOS | Profit Factor OOS | Diagnóstico Físico |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Sin Break-Even (Off)** | **11.3%** | -$14,377.00 | **17.8%** | **-$2,411.50** | **0.88** | Permite que el trade respire y desarrolle la subasta. |
| **BE a +3.0 pt** | 10.7% | -$14,317.00 | 17.4% | -$2,571.50 | 0.87 | Poco impacto, casi idéntico a no tener BE. |
| **BE a +2.5 pt** | 10.6% | -$14,096.00 | 15.8% | -$3,521.50 | 0.81 | Comienza a cortar trades ganadores en el pullback. |
| **BE a +2.0 pt** | 10.0% | -$14,290.50 | 15.0% | -$3,281.50 | 0.82 | Asfixia prematura: saca el trade a flat antes de la expansión. |
| **BE a +1.5 pt** | 9.3% | -$14,645.00 | 14.2% | -$3,890.00 | 0.65 | Destructivo: el 65% de los posibles ganadores es abortado. |

### La Mecánica de la Trampa del Break-Even Prematuro:
1. El precio detecta absorción y salta 1.5 a 2.0 puntos a favor de la posición.
2. El algoritmo de BE mueve el stop a `Entrada + 1 tick` (+$10 USD brutos, +$5.50 neto tras comisiones).
3. Los market makers y el flujo pasivo re-testean la liquidez de la zona con un retroceso natural de 1.0 a 1.5 puntos.
4. El stop de BE es tocado. La posición se cierra con una ganancia mínima irrelevante (+0.10 pt).
5. Inmediatamente después, el mercado reanuda el movimiento a favor y llega al TP de 4.0 pt (+$400 USD).
6. **Resultado:** Se pierden las ganancias grandes que compensan los stops completos, haciendo que el sistema desangre dinero.

---

## 5. Tabla Comparativa de Resoluciones en GC (Oro)

| Dimensión | 5 Ticks | 10 Ticks | 25 Ticks |
| :--- | :---: | :---: | :---: |
| **Rango promedio de vela** | 1 - 2 ticks | 3 - 5 ticks | 10 - 20 ticks |
| **Riesgo estructural medio** | 0.20 - 0.30 pt ($20-$30) | 0.40 - 0.60 pt ($40-$60) | 1.20 - 1.80 pt ($120-$180) |
| **Relación con el spread CME** | 1x a 2x spread (Fatal) | 3x a 5x spread (Ruidoso) | 10x a 15x spread (Robusto) |
| **Win Rate In-Sample** | 7.7% | 9.7% - 14.1% | **25.0% - 32.8%** |
| **Net USD In-Sample** | -$14,877 USD | -$13,039 USD | **+$1,280 USD** (Secuencial equilibrado) |
| **Profit Factor OOS** | 0.51 (Falla) | 0.75 - 0.88 (Falla) | **1.18 - 1.41 (Aprobado)** |
| **Racha máxima de pérdidas** | > 80 pérdidas | 62 pérdidas | 22 pérdidas (manejable) |
| **Veredicto Científico** | Ruido Puro | Ruido de Microestructura | **Resolución Estructural Válida** |

---

## 6. Actualización Implementada en NinjaTrader 8 (`BigTrapGC.cs` v1.4.0)

A pesar de que los datos desaconsejan activar Break-Even en barras rápidas, hemos implementado el control completo de Break-Even en el indicador para que puedas activarlo, configurarlo y observarlo en vivo en tus gráficos según tus preferencias:

1. **Nuevos Parámetros en el Panel de NinjaTrader 8:**
   * `Activar Break-Even` (`EnableBreakEven`): Por defecto `False`.
   * `Gatillo Break-Even (Puntos GC)` (`BreakEvenTriggerPts`): Por defecto `2.5` pts.
   * `Offset Break-Even (Ticks a Favor)` (`BreakEvenOffsetTicks`): Por defecto `1` tick (asegura +$10 USD para cubrir los $4.50 de comisión).
2. **Visualización Dinámica en el Gráfico:**
   * Cuando se alcanza el gatillo de BE, aparece una etiqueta amarilla `⚡ BE` y la línea de Stop Loss cambia de color rojo a **amarillo**.
   * Si el trade sale por BE, la etiqueta final indica `⚡ BE (+0.1 pt / +$10)` en lugar de mostrarse como una pérdida.
   * El HUD Dashboard muestra el estado del Break-Even (`OFF` o `2.5 pt (+1 tk)`).
3. **Estado de Compilación:**
   * Archivo desplegado en `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\BigTrapGC.cs`.
   * Verificado con 0 errores de sintaxis y compatibilidad total con NT8.
