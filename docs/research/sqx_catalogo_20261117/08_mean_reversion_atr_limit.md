# Candidata #08 — Mean Reversion Panic Limit (`mean_reversion.sqx` + `MeanRev.sqx`)

- **Nombre en catálogo:** *Mean Reversion Strategy* (`MeanRev.sqx`, Shared Hub) + *mean_reversion* (`mean_reversion.sqx`, AlgoWizard Examples)
- **Origen exacto:**
  1. Marketplace / Shared Hub oficial — [`https://strategyquant.com/shared/mean-reversion-strategy/`](https://strategyquant.com/shared/mean-reversion-strategy/) (`MeanRev.sqx`, Tomas Vanek, `2025-10-06`)
  2. Instalación local oficial SQX — `C:\StrategyQuantX145\internal\web\AlgoWizard\examples\mean_reversion.sqx`
- **Autor / fecha:** Tomas Vanek / StrategyQuant (`2025-10-06`)
- **Instrumento y timeframe originales:** `[[Russell 3000]]`, **`D1`** (Stockpicker). Para EdgeLab: portar a futuros **`FDAX`**, **`GC`**, **`ZN`**, **`6E`** (en `H4` o `D1`; evaluar también variante con `SL` ATR protector para cumplir gestión de riesgo por trade).

---

## Reglas completas y parámetros por defecto

### Dos variantes oficiales del catálogo SQX
1. **Variante A — `mean_reversion.sqx` (AlgoWizard Example, Long-Only por caída ATR):**
   - **Entrada Larga (límite, válida `1` barra):**
     - Condición al cierre: `Close > SMA(200)[1]` AND `Close < Open - 1.0 * ATR(5)[1]` *(vela bajista pánica ≥ `1x ATR(5)` dentro de tendencia alcista)* AND `Close[1] > 30` AND `Volume > 1`.
     - **Orden:** `Buy Limit` a `Close - 1.2 * ATR(5)[1]`.
   - **Salida:** `Close > Open` (primera barra verde al cierre), `ProfitTarget = 10%`, o `ExitAfterBars = 4`.
2. **Variante B — `MeanRev.sqx` (Shared Hub / Marketplace, Bidireccional Long + Short):**
   - **Entrada Larga (límite):** `Close < Open * 0.97` AND `Close < MIN(Low, 3)[1]` AND `Close > EMA(200)[1]` AND `Close > 3` → `Buy Limit` en `Close - 0.5 * ATR(5)[1]`. Salida `Close > Open` o `ExitAfterBars = 5`.
   - **Entrada Corta (límite, sobre rally eufórico en régimen alcista/general):** `Close > Open * 1.03` AND `Close > MAX(High, 3)[1]` AND `Close > EMA(200)[1]` → `Sell Limit` en `Close + 0.5 * ATR(5)[1]`. Salida `Close < Open` o `ExitAfterBars = 5`.
   - *Nota EdgeLab:* En futuros/FX (`FDAX`, `GC`, `ZN`, `6E`), el umbral fijo `0.97` (`-3%` diario) de `MeanRev.sqx` es raro por vela; conviene usar la formulación normalizada por volatilidad `1.0 * ATR(5)` de `mean_reversion.sqx` añadiendo un `StopLoss` duro (ej. `2.5–3.0 * ATR(14)`) y cierre viernes `15:55 NY` cuando se opere `H4`.

### Pseudocódigo oficial (generado por SQX Build 145)
```text
//--------------------------------------------------------------------
// A) mean_reversion.sqx (AlgoWizard Example, Stockpicker, D1)
//--------------------------------------------------------------------
Entry Condition (After Bar Close / Before Bar Open):
   Close(Main chart)[0] > SMA(Main chart, PRICE_CLOSE, 200)[1]
   AND Close(Main chart)[0] < (Open(Main chart)[0] - (1 * ATR(Main chart, 5)[1]))
   AND Close(Main chart)[1] > 30
   AND Volume(Main chart)[0] > 1
Order: Open Long order at (Close(Main chart)[0] - (1.2 * ATR(Main chart, 5)[1])) Limit;
   Order valid for 1 bars; Profit target = 10%; Exit After 4 bars;
Exit Condition: (Close(Main chart)[0] > Open(Main chart)[0])
Position Score = Abs(1 - ROC(Close, 5)[0]); Risk $10000 per strategy

//--------------------------------------------------------------------
// B) MeanRev.sqx (Marketplace Shared Hub, Stockpicker, D1)
//--------------------------------------------------------------------
Long Entry Condition:
   Close[0] < (Open[0] * 0.97)
   AND Close[0] < MIN(PRICE_LOW, 3)[1]
   AND Close[0] > EMA(PRICE_CLOSE, 200)[1]
   AND Close[0] > 3
Long Order: Buy Limit at (Close[0] - 0.5 * ATR(5)[1]); Exit After 5 bars;
Long Exit : Close[0] > Open[0]; PosScore = (1 - ROC(20)[1]); MaxPos = 5

Short Entry Condition:
   Close[0] > (Open[0] * 1.03)
   AND Close[0] > MAX(PRICE_HIGH, 3)[1]
   AND Close[0] > EMA(PRICE_CLOSE, 200)[1]
   AND Close[0] > 3
Short Order: Sell Limit at (Close[0] + 0.5 * ATR(5)[1]); Exit After 5 bars;
Short Exit : Close[0] < Open[0]; PosScore = ROC(20)[1]; MaxPos = 5
```

### Código MQL5
> **Nota técnica de SQX Build 145:** Al ejecutar `get_strategy_source(format="Expert Advisor for MetaTrader5 (*.MQ5)")` sobre ambos `.sqx`, SQX Build 145 reportó que los archivos *AlgoCloud Stockpicker* no exportan directamente a MT5. Se incluye abajo la **implementación MQL5 equivalente** usando la regla de pánico `ATR(5)` + orden `BuyLimit` válida `1` barra + stop protector para futuras mediciones en EdgeLab/MT5.

```mql5
#include <Trade/Trade.mqh>
input int    InpSmaTrend    = 200;
input int    InpAtrPeriod   = 5;
input double InpPanicAtr    = 1.0;   // caída mínima Close < Open - 1.0*ATR(5)
input double InpLimitAtr    = 1.2;   // entrada BuyLimit = Close - 1.2*ATR(5)
input double InpStopAtrMult = 3.0;   // stop protector en R (>= 12x costos)
input int    InpMaxHoldBars = 4;
input double InpLots        = 0.10;
input long   InpMagic       = 92008;

int hSma, hAtr;
datetime lastBar = 0;
datetime entryBarTime = 0;
ulong pendingTicket = 0;
CTrade trade;

int OnInit() {
   trade.SetExpertMagicNumber(InpMagic);
   hSma = iMA(_Symbol, _Period, InpSmaTrend, 0, MODE_SMA, PRICE_CLOSE);
   hAtr = iATR(_Symbol, _Period, InpAtrPeriod);
   return (hSma!=INVALID_HANDLE && hAtr!=INVALID_HANDLE) ? INIT_SUCCEEDED : INIT_FAILED;
}

void OnTick() {
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == lastBar) return;
   lastBar = t0;

   if(pendingTicket > 0 && OrderSelect(pendingTicket)) {
      trade.OrderDelete(pendingTicket);
      pendingTicket = 0;
   }

   double o1 = iOpen(_Symbol,_Period,1), c1 = iClose(_Symbol,_Period,1);
   if(PositionSelect(_Symbol)) {
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int held = iBarShift(_Symbol, _Period, openTime);
      if(c1 > o1 || held >= InpMaxHoldBars) trade.PositionClose(_Symbol);
      return;
   }

   double sma[1], atr[2];
   if(CopyBuffer(hSma,0,1,1,sma)<1 || CopyBuffer(hAtr,0,2,1,atr)<1) return;
   double atrPrev = atr[0];
   if(c1 > sma[0] && c1 < o1 - InpPanicAtr * atrPrev) {
      double limitPx = NormalizeDouble(c1 - InpLimitAtr * atrPrev, _Digits);
      double sl = NormalizeDouble(limitPx - InpStopAtrMult * atrPrev, _Digits);
      if(trade.BuyLimit(InpLots, limitPx, _Symbol, sl, 0.0, ORDER_TIME_DAY, 0, "MeanRev_L"))
         pendingTicket = trade.ResultOrder();
   }
}
```

| Parámetro | `mean_reversion.sqx` | `MeanRev.sqx` (Shared) | Notas |
|---|---|---|---|
| Régimen | `Close > SMA(200)` | `Close > EMA(200)` | Sólo largos sobre tendencia mayor |
| Disparador pánico | `Close < Open - 1.0*ATR(5)` | `Close < Open * 0.97 & Close < MIN(Low,3)` | Replicable vía `ATR(5)` en futuros/FX |
| Orden Límite | `Close - 1.2 * ATR(5)` (`1` barra) | `Close - 0.5 * ATR(5)` (`+/-` cortos) | Sólo llena si continúa el pánico intrabarra |
| Salida | `Close > Open` o `4` barras (`TP 10%`) | `Close > Open` o `5` barras | Hold muy corto (`1–4` velas) |

---

## Backtest de catálogo (NO evidencia para EdgeLab)

- `MeanRev.sqx` (`lastSettings.xml`): `[[Russell 3000]]`, `D1`, `1990.07.03 – 2025.09.05`, resultados en binario interno `SQStats` / video tutorial sin tabla impresa en web. **No constituye evidencia para EdgeLab** (y Russell 3000 cash D1 tiene dinámicas y survivorship/fees distintas de futuros de cartera EdgeLab).

---

## Mecanismo y cómo podría refutarse

- **Mecanismo:** Cuando ocurre una vela de liquidación/pánico agudo dentro de una tendencia de largo plazo sana (`> SMA 200`), las órdenes *Buy Limit* escaladas por debajo del cierre (`-0.5` a `-1.2 ATR`) proveen liquidez a ventas forzadas de apertura/continuación de pánico y capturan el rebote técnico inmediato (salida en la primera vela de cierre superior a apertura).
- **Cómo refutarse en EdgeLab:** Si en `FDAX`, `GC`, `ZN` y `6E` (`H4`/`D1`): (1) las órdenes límite sufren *adverse selection* severa (sólo se ejecutan cuando la caída rompe tendencia y salta el stop, ganando únicamente cuando NO se llenan los mejores trades); (2) al imponer `StopLoss` duro (obligatorio por gestión de riesgo en EdgeLab) y cierre de viernes, desaparece el retorno positivo.

## Hueco de diversificación

- **Sesión / Activo / Horizonte / Estilo:** Fuera de NY-open `NQ/ES`; aplicable a **`FDAX`**, **`GC`**, **`ZN`** en `H4`/`D1`, horizonte **ultra-corto (`1–4` velas)**, estilo **reversión pura con orden Limit por pánico de volatilidad ATR** (correlación negativa o cero frente a sistemas breakout/momentum).
