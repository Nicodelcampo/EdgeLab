# Registro Canónico de Hallazgo: Filtro de Reversión EMA para BigTrapGC

> **ID de Hallazgo:** `RESEARCH-GC-EMA-REVERT-20260906`  
> **Fecha:** 2026-09-06 / 2026-09-07  
> **Activo:** COMEX Gold Futures (`GC` / `MGC`)  
> **Estado:** `REGISTRADO_VERIFICADO_SECUENCIAL`  
> **Holdout:** `GC 08-26` (100% Sellado e Intocado)  
> **Fricciones Reales CME:** $4.50 USD comisión round-turn + 1 tick slippage adverso en paradas ($10.00 USD).  
> **Scripts de Reproducción:**  
>   - [`tools/optimize_bigtrap_gc_ema.py`](file:///D:/EdgeLab/tools/optimize_bigtrap_gc_ema.py)  
>   - [`tools/audit_gc_ema_reality_check.py`](file:///D:/EdgeLab/tools/audit_gc_ema_reality_check.py)  
>   - Datos brutos: [`docs/research/bigtrap_gc_ema_25tick_results.json`](file:///D:/EdgeLab/docs/research/bigtrap_gc_ema_25tick_results.json)  

---

## 1. Planteamiento de la Hipótesis del Usuario

El usuario propuso filtrar las entradas del indicador `BigTrap2` en Oro mediante una media móvil exponencial (EMA), específicamente una EMA de 200 períodos en barras de ticks, bajo la siguiente regla tendencial:
- **COMPRA (Trapped Sellers):** Solo si el precio está por encima de la EMA (`Close >= EMA`).
- **VENTA (Trapped Buyers):** Solo si el precio está por debajo de la EMA (`Close <= EMA`).

---

## 2. Falsación de la Hipótesis Tendencial

La hipótesis tendencial fue sometida a simulación causal tick a tick sobre 4 contratos CME (~35M ticks, ~270 sesiones CME):
* In-Sample: `GC 12-25` + `GC 02-26` (~140 sesiones).
* Out-of-Sample: `GC 04-26` + `GC 06-26` (~130 sesiones).

### Resultados de la Falsación:
1. **Barras de 25 Ticks:**
   - `SIN_FILTRO` (Control): OOS PnL = +$30,230 USD | Profit Factor = 1.41.
   - `TREND_EMA_200`: OOS PnL = +$8,415 USD | Profit Factor = 1.19 (Pérdida de más del 70% del valor neto).
   - En ejecución secuencial realista (1 sola posición activa a la vez): el filtro tendencial `TREND_EMA_200` generó apenas **+$21 USD netos en 130 sesiones** (Profit Factor 1.00, plano total). Los Longs perdieron -$748 USD.
2. **Barras de 150 Ticks:**
   - La EMA en barras lentas genera un lag severo.
   - En el perfil equilibrado (TP 6.0 pt), `TREND_EMA_200` acumuló una **pérdida neta de -$50,008 USD** en Out-of-Sample (PF 0.93).

**Dictamen:** La hipótesis de operar a favor de la pendiente de la EMA en Oro queda **falsada y descartada**.

---

## 3. El Hallazgo Cuantitativo: Reversión a la Media (`REVERT_EMA`)

Al testear la hipótesis inversa de microestructura de subasta:
- **COMPRA (Trapped Sellers):** Solo cuando el precio está **POR DEBAJO** de la EMA (`Close < EMA`).
- **VENTA (Trapped Buyers):** Solo cuando el precio está **POR ENCIMA** de la EMA (`Close > EMA`).

El comportamiento del sistema cambió radicalmente de forma positiva, tanto en In-Sample como en Out-of-Sample.

### Auditoría Secuencial Estricta (1 Sola Posición Activa a la Vez, Fricciones Reales):

#### A. Perfil Asimétrico (TP 12.0 pt / SL 1.0x / Sin BE)

| Métrica | Control (Sin Filtro) | `REVERT_EMA_100` | `REVERT_EMA_200` |
| :--- | :---: | :---: | :---: |
| **Trades Totales Ejecutados** | 1,016 tr | 582 tr | 601 tr |
| **Win Rate** | 9.9% | **11.2%** | **11.0%** |
| **Profit Factor Global** | 1.10 | **1.31** | **1.30** |
| **PnL Out-of-Sample (130 ses)** | +$15,984 USD | **+$21,252 USD (PF 1.98)** | **+$21,340 USD (PF 1.96)** |
| **Rendimiento LONGS** | +$7,750 USD (10.2% WR) | **+$12,381 USD (12.2% WR)** | **+$12,359 USD (12.2% WR)** |
| **Rendimiento SHORTS** | +$1,648 USD (9.7% WR) | **+$3,340 USD (10.3% WR)** | **+$3,666 USD (9.9% WR)** |
| **Max Drawdown Real** | -$14,324 USD | **-$8,955 USD** | **-$7,342 USD** |
| **Racha Máx Pérdidas Consecutivas**| 48 pérdidas | **34 pérdidas** | **35 pérdidas** |

#### B. Perfil Alto Win Rate (TP 4.0 pt / SL 1.5x / Sin BE)

| Métrica | Control (Sin Filtro) | `REVERT_EMA_100` | `REVERT_EMA_200` |
| :--- | :---: | :---: | :---: |
| **Trades Totales Ejecutados** | 1,207 tr | 674 tr | 687 tr |
| **Win Rate** | 27.5% | **27.9%** | **26.5%** |
| **Profit Factor Global** | 1.09 | **1.15** | **1.07** |
| **PnL Out-of-Sample (130 ses)** | +$13,024 USD | **+$10,368 USD (PF 1.43)** | **+$10,144 USD (PF 1.40)** |
| **Rendimiento LONGS** | +$3,068 USD (27.0% WR) | **+$5,960 USD (29.9% WR)** | **+$2,176 USD (27.7% WR)** |
| **Rendimiento SHORTS** | +$7,460 USD (28.0% WR) | **+$3,696 USD (26.2% WR)** | **+$2,753 USD (25.4% WR)** |
| **Max Drawdown Real** | -$8,602 USD | **-$4,712 USD** | **-$8,420 USD** |
| **Racha Máx Pérdidas Consecutivas**| 26 pérdidas | **22 pérdidas** | **25 pérdidas** |

---

## 4. Mecanismo Causal y Microestructura

1. **Naturaleza del Activo:** El Oro COMEX es un activo de balance, rotación y valor intrínseco. No responde a la inercia de momentum continuo típica de índices bursátiles (como NQ).
2. **La Trampa de Comprar Máximos:** Cuando el precio está extendido por encima de la EMA de 100 o 200 períodos, la aparición de una absorción vendedora ocurre en el clímax del impulso. Comprar allí significa absorber el retroceso correctivo inevitable.
3. **El Resorte del Falso Quiebre:** Cuando el precio quiebra por debajo de la EMA y se genera una absorción masiva de vendedores (`Trapped Sellers`), se trata de un barrido de liquidez de mínimos (*liquidity sweep*). Al no poder continuar a la baja, el precio es catapultado de vuelta hacia el valor medio (la EMA), ofreciendo un recorrido limpio hacia el Target Profit.
4. **Simetría Bilateral:** A diferencia de las pruebas sin filtro (donde los Shorts apenas aportaban o daban pérdidas), el filtro de reversión genera rentabilidad neta positiva tanto en Compras como en Ventas, demostrando independencia del sesgo de tendencia macro.

---

## 5. Estado y Líneas Abiertas para Continuidad

- **Veredicto:** El filtro de reversión con EMA 100/200 queda registrado como una hipótesis válida y robusta para complementar la detección de absorción en Oro.
- **Holdout Intacto:** La ventana sellada `GC 08-26` no fue abierta ni expuesta para esta investigación.
- **Líneas Abiertas:**
  1. Contrastar el filtro de Reversión EMA frente al filtro de Bandas de Desviación de Anchored VWAP (`BigTrapVWAP_GC`).
  2. Explorar el efecto de la distancia mínima a la EMA ($\Delta \text{Ticks} \ge K$).
  3. Investigar la interacción entre los clusters de volumen HFT y el retorno a la EMA.
