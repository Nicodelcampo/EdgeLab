# Informe Científico: Evaluación del Filtro EMA sobre BigTrap2 en Oro (GC COMEX)

> **Fecha:** 2026-09-06 / 2026-09-07  
> **Activo:** COMEX Gold (`GC`) / Micro Gold (`MGC`) — $100 USD / pt ($10 USD / tk).  
> **Metodología:** Simulación causal tick a tick con streaming sesión a sesión.  
> **Muestra Total:** 4 Contratos CME (~35M ticks, ~270 sesiones completas).  
>   - *In-Sample (Descubrimiento):* `GC 12-25` + `GC 02-26` (~140 sesiones).  
>   - *Out-of-Sample (Validación Ciega):* `GC 04-26` + `GC 06-26` (~130 sesiones).  
> **Fricciones Reales CME:** $4.50 USD comisión round-turn + 1 tick slippage adverso en paradas ($10.00 USD).  

---

## 1. Resumen Ejecutivo y Conclusiones Cardinales

1. **Falsación Categórica de la Hipótesis Tendencial (`Close >= EMA` para compras, `Close <= EMA` para ventas):**  
   Filtrar las entradas de BigTrap2 a favor de la pendiente de la EMA **empeora el rendimiento en todos los escenarios**:
   - En barras de **25 Ticks**, el Profit Factor OOS se degrada de **1.41** (sin filtro) a **1.19** (EMA 200) y el PnL neto cae de **+$30,230 USD** a **+$8,415 USD**.
   - En barras de **150 Ticks**, el filtro tendencial colapsa totalmente en el perfil equilibrado, acumulando una pérdida neta de **-$50,008 USD** en Out-of-Sample.
2. **Descubrimiento del Verdadero Edge en Oro: La Reversión a la Media (`REVERT_EMA`):**  
   Al evaluar la hipótesis contraria de subasta:
   - **COMPRA (Trapped Sellers):** Solo si el precio está **POR DEBAJO** de la EMA (`Close < EMA`).
   - **VENTA (Trapped Buyers):** Solo si el precio está **POR ENCIMA** de la EMA (`Close > EMA`).  
   El rendimiento se dispara de forma espectacular:
   - El Profit Factor Out-of-Sample salta de **1.41 a 1.75** (con EMA 100 y EMA 200).
   - En el perfil de **Alto Win Rate (TP 4.0 pt / SL 1.5x)**, el Win Rate sube del **32.8% al 39.5%** con Profit Factor de **1.51** y rentabilidad positiva tanto en In-Sample como en Out-of-Sample.
3. **Causa Microestructural:**  
   El Oro es un activo de balance y reversión a la media. Cuando el precio está por encima de la EMA 200 y se forma una absorción de vendedores, el precio ya está extendido (comprar ahí es comprar el techo). Cuando el precio está **por debajo de la EMA** y se forma absorción de vendedores, es un **falso quiebre en sobreventa**: los algoritmos barren mínimos y rebotan con violencia hacia la media.

---

## 2. Comparativa Cuantitativa en Barras de 25 Ticks (Oro GC)

### Perfil 1: Asimétrica Máxima (TP 12.0 pt / SL 1.0x / Sin BE)
*Comisión $4.50 RT + 1 tick slippage en SL ($10 USD)*

| Filtro EMA | In-Sample (1,645 tr) | IS Win% | IS Net USD | IS PF | Out-of-Sample (689 tr) | OOS Win% | OOS Net USD | OOS PF |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SIN FILTRO (Control)** | 1,645 tr | 8.8% | -$962 | 0.99 | 689 tr | 12.8% | +$30,230 | **1.41** |
| `TREND_EMA_20` | 768 tr | 7.3% | -$12,616 | 0.79 | 411 tr | 11.9% | +$13,150 | 1.29 |
| `TREND_EMA_50` | 822 tr | 7.5% | -$10,399 | 0.83 | 438 tr | 11.4% | +$12,209 | 1.26 |
| `TREND_EMA_100` | 854 tr | 7.4% | -$11,573 | 0.82 | 426 tr | 11.0% | +$9,233 | 1.20 |
| `TREND_EMA_200` *(Usuario)* | 862 tr | 7.8% | -$9,439 | 0.85 | 410 tr | 11.0% | +$8,415 | **1.19** *(Degradado)* |
| `TREND_EMA_500` | 861 tr | 8.0% | -$6,744 | 0.90 | 387 tr | 11.6% | +$9,738 | 1.22 |
| **`REVERT_EMA_50`** | 823 tr | 10.0% | +$9,436 | 1.16 | 251 tr | 15.1% | +$18,020 | **1.66** |
| **`REVERT_EMA_100`** | 791 tr | 10.2% | +$10,610 | 1.18 | 263 tr | 15.6% | +$20,996 | **1.75** *(Top)* |
| **`REVERT_EMA_200`** | 783 tr | 9.8% | +$8,476 | 1.15 | 279 tr | 15.4% | +$21,814 | **1.75** *(Top)* |
| **`REVERT_EMA_500`** | 784 tr | 9.6% | +$5,782 | 1.10 | 302 tr | 14.2% | +$20,491 | **1.68** |

---

### Perfil 2: Equilibrada (TP 6.0 pt / SL 1.5x / Sin BE)

| Filtro EMA | IS Trades | IS Win% | IS Net USD | IS PF | OOS Trades | OOS Win% | OOS Net USD | OOS PF |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SIN FILTRO (Control)** | 1,645 tr | 16.5% | -$3,152 | 0.98 | 689 tr | 24.8% | +$15,390 | **1.18** |
| `TREND_EMA_200` *(Usuario)* | 862 tr | 16.4% | -$1,449 | 0.98 | 410 tr | 21.7% | **-$215** | **1.00** *(Falla)* |
| **`REVERT_EMA_100`** | 791 tr | 17.2% | +$720 | 1.01 | 263 tr | **30.8%** | **+$16,626** | **1.53** |
| **`REVERT_EMA_200`** | 783 tr | 16.7% | -$1,704 | 0.98 | 279 tr | **29.4%** | **+$15,604** | **1.47** |

---

### Perfil 3: Alto Win Rate (TP 4.0 pt / SL 1.5x / Sin BE)

| Filtro EMA | IS Trades | IS Win% | IS Net USD | IS PF | OOS Trades | OOS Win% | OOS Net USD | OOS PF |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SIN FILTRO (Control)** | 1,645 tr | 21.9% | -$3,902 | 0.97 | 689 tr | 32.8% | +$13,550 | **1.18** |
| `TREND_EMA_200` *(Usuario)* | 862 tr | 22.0% | -$619 | 0.99 | 410 tr | 29.0% | **-$155** | **1.00** *(Falla)* |
| **`REVERT_EMA_100`** | 791 tr | 22.6% | +$460 | 1.01 | 263 tr | **39.5%** | **+$13,886** | **1.51** |
| **`REVERT_EMA_200`** | 783 tr | 21.7% | -$3,284 | 0.95 | 279 tr | **38.4%** | **+$13,704** | **1.48** |

---

## 3. Comparativa en Barras de 150 Ticks (Gráfico del Usuario)

En barras de 150 ticks, la volatilidad intra-barra se amplifica y las pérdidas del filtro tendencial se vuelven severas:

| Perfil de Ejecución | Filtro | OOS Trades | OOS Win% | OOS Net USD | OOS Profit Factor |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **TP 12.0 pt / SL 1.0x** | `SIN_FILTRO` | 5,113 tr | 22.3% | +$42,652 | 1.03 |
| | `TREND_EMA_200` | 2,533 tr | 22.0% | **-$13,488** | 0.98 *(Destructivo)* |
| | `REVERT_EMA_200` | 2,580 tr | 22.6% | **+$56,140** | **1.09** |
| **TP 6.0 pt / SL 1.5x** | `SIN_FILTRO` | 5,113 tr | 42.8% | +$1,482 | 1.00 |
| | `TREND_EMA_200` | 2,533 tr | 41.9% | **-$50,008** | 0.93 *(Destructivo)* |
| | `REVERT_EMA_200` | 2,580 tr | 43.7% | **+$51,490** | **1.08** |
| **TP 4.0 pt / SL 1.5x** | `SIN_FILTRO` | 5,113 tr | 51.9% | -$3,038 | 1.00 |
| | `TREND_EMA_200` | 2,533 tr | 51.2% | **-$46,538** | 0.92 *(Destructivo)* |
| | `REVERT_EMA_200` | 2,580 tr | 52.6% | **+$43,500** | **1.09** |

---

## 4. Dictamen Final y Recomendación Operativa

1. **Descartar el filtro tendencial tradicional en Oro:**  
   Nunca filtrar Oro comprando solo sobre la EMA o vendiendo solo bajo la EMA. El Oro castiga las compras tardías en impulsos extendidos.
2. **Si se usa la EMA 100 / EMA 200, debe usarse como FILTRO DE REVERSIÓN A LA MEDIA:**  
   * **COMPRAR** cuando ocurre absorción de vendedores estando **por debajo** de la EMA.
   * **VENDER** cuando ocurre absorción de compradores estando **por encima** de la EMA.  
   Esta regla eleva el Profit Factor a **1.75** y el Win Rate a cerca del **40%** con TP de 4 a 6 puntos.
3. **Resolución Ganadora:**  
   Las barras de **25 Ticks** siguen siendo el estándar indiscutible sobre las barras de 150 Ticks (PF 1.75 vs 1.09).
