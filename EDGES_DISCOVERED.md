# Edge Record: Asian Range Breakout (ARB) + SMA 200

## 1. Ficha Técnica
* **Activo:** EURUSD (Spot y Futuros 6E)
* **Timeframe:** 15 Minutos (M15)
* **Estilo:** Momentum / Breakout Intradiario
* **Frecuencia:** ~1.3 trades por día (combinando ventanas)
* **Validación:** Completada en VectorBT y JForex4 (Tick-Data Real)
* **Walk-Forward:** Positivo (Sharpe > 0.7 en Train y Test)

## 2. Lógica del Sistema
El edge explota la ruptura del rango de consolidación que se forma durante la sesión asiática (baja liquidez), buscando atrapar el flujo de capital institucional que entra con la apertura de Londres y el pre-market de Nueva York, filtrando falsos rompimientos a favor de la tendencia a corto plazo.

### 2.1 Variables Core
* **Asian Range:** Máximo y mínimo formados entre las `00:00 UTC` y las `08:00 UTC`.
* **Filtro de Tendencia:** SMA 200 aplicada en gráficos de M15 (representa la tendencia de los últimos ~2.5 días).

### 2.2 Condiciones de Entrada
Se evalúa la ruptura exclusivamente al **cierre** de 4 ventanas horarias clave: `08:45, 09:00, 11:00 y 12:00 UTC`.

* **LONG:** El precio de cierre rompe por encima del *Asian High* Y el precio está por encima de la *SMA 200*.
* **SHORT:** El precio de cierre rompe por debajo del *Asian Low* Y el precio está por debajo de la *SMA 200*.

*Nota: Solo se permite 1 trade por ventana por día, con un máximo teórico de 4 trades simultáneos.*

### 2.3 Gestión de Riesgo (Salidas)
* **Take Profit:** 20 pips (40 ticks en 6E)
* **Stop Loss:** 50 pips (100 ticks en 6E)
* **Time-Stop:** Cierre incondicional de todas las posiciones a las `16:00 UTC` (fin de la sesión líquida, evita el overnight y reduce el drawdown drásticamente).

## 3. Estadísticas Consolidadas (JForex 18 Meses)
* **Capital Inicial:** $50,000 (1 Lote Estándar por señal / $10 el pip)
* **Net Profit:** +$9,802.71 (+19.6%)
* **Total Trades:** 473
* **Frecuencia Mensual:** ~25.5 trades / mes
* **Resultado Auditoría de Bugs:** Limpio (Sin look-ahead bias, indexación correcta de OHLC, no-repainting).

## 4. Archivos de Implementación
* **VectorBT (Python):** `validation/vectorbt_eurusd_portfolio.py`
* **JForex4 (Java):** Implementado en el entorno local (AsianRangeBreakout.java)
* **NinjaTrader 8 (C#):** `AsianRangeBreakout6E.cs` (Soporta contratos de futuros con conversiones DST dinámicas a Central Time).

## 5. Observaciones Finales
La diversificación con otras estrategias en este mismo activo (Mean Reversion, Friday Fade) demostró ser subóptima (Sharpes negativos). El Edge en el EURUSD es fuertemente de Momentum intradiario, y este sistema captura eficientemente ese fenómeno.

---
*Documento autogenerado tras validación exitosa del modelo. Fecha: Julio 2026.*
