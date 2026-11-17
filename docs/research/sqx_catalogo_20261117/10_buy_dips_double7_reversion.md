# Candidata #10 — Reversión Tendencial D1 (`buy_dips.sqx` / `PriceDip_SP500.sqx` / *Double 7*)

- **Nombre en catálogo:** *Buy Dips* (`buy_dips.sqx`) + *Buy The Dip for S&P500* (`PriceDip_SP500.sqx`) + *Larry Connor's Double 7* (`Larry_Connors-SPY.sqx`)
- **Origen exacto:**
  1. Instalación local oficial SQX — `C:\StrategyQuantX145\internal\web\AlgoWizard\examples\buy_dips.sqx`
  2. Marketplace / Shared Hub oficial — [`https://strategyquant.com/shared/buy-the-dip-for-sp500/`](https://strategyquant.com/shared/buy-the-dip-for-sp500/) (`PriceDip_SP500.sqx`, `2026-07-07`) y [`https://strategyquant.com/shared/larry-connors-double-7-for-spy/`](https://strategyquant.com/shared/larry-connors-double-7-for-spy/) (`Larry_Connors-SPY.sqx`, `2026-09-16`)
- **Autor / fecha:** Ellie Souckova / StrategyQuant (`2026-07-07` y `2026-09-16`)
- **Instrumento y timeframe originales:** `[[S&P 500]]` / `[SPY.D]`, **`D1`**. **Nota de diversificación EdgeLab:** Se coloca en puesto #10 porque sus activos originales son renta variable EE. UU. (`SP500`/`SPY`), pero el mecanismo es **reversión multi-día en `D1`** (completamente opuesto al momentum NY-open de `SOM`/`Franklin`); debe probarse prioritariamente en **`FDAX`**, **`GC`**, **`ZN`** y compararse contra `ES` sólo fuera de redundancia.

---

## Reglas completas y parámetros por defecto

### Tres implementaciones oficiales convergentes del catálogo SQX
1. **Variante Principal — `buy_dips.sqx` (AlgoWizard Example, límite ATR + EMA7):**
   - **Entrada Larga (`Buy Limit`, válida `2` barras):**
     - `Open > SMA(250)` AND `RSI(5) < 30` AND `Close[1] > 10` AND `Volume[1] > 250000`
     - Orden: `Buy Limit` a `Close - 0.5 * ATR(14)[1]`.
   - **Salida:** `Open > EMA(Open, 7)` *(al abrir encima de su EMA rápida de aperturas)* o `ExitAfterBars = 20`.
2. **Variante B — `PriceDip_SP500.sqx` (Shared Hub / Stockpicker):**
   - **Entrada:** `Close < Close[3] * 0.95` *(caída ≥ 5% en 3 días)* AND `Close > SMA(200)[1]` AND `Subchart(SPY) > SMA(200)[1]`. `Open Long at Market`.
   - **Salida:** `Close > High[1]` *(cierra encima del máximo previo)* o `ExitAfterBars = 10`. Ranking `Close / Close[3]`, máx. `10` posiciones.
3. **Variante C — `Larry_Connors-SPY.sqx` (*Double 7*, Shared Hub / Single-asset):**
   - **Entrada:** `Close[1] > SMA(200)[1]` AND `Close[1] <= MIN(Close, 7)[1]`. `Open Long at Market`.
   - **Salida:** `Close[1] >= MAX(Close, 7)[1]`. *(Sin SL/TP fijo en el original; en EdgeLab exige añadir `StopLoss` ATR amplio ≥ `12x` costos, ej. `3.0 * ATR(14)`).*

### Pseudocódigo oficial (generado por SQX Build 145)
```text
//--------------------------------------------------------------------
// 1) buy_dips.sqx (AlgoWizard Example, D1)
//--------------------------------------------------------------------
Entry Condition:
   Open(Main chart)[0] > SMA(Main chart, PRICE_CLOSE, 250)[0]
   AND RSI(Main chart, PRICE_CLOSE, 5)[0] < 30
   AND Close(Main chart)[1] > 10
   AND Volume(Main chart)[1] > 250000
Order: Open Long order at (Close(Main chart)[0] - (0.5 * ATR(Main chart, 14)[1])) Limit;
   Order valid for 2 bars; Exit After 20 bars;
Exit Condition: Open(Main chart)[0] > EMA(Main chart, PRICE_OPEN, 7)[0]

//--------------------------------------------------------------------
// 2) PriceDip_SP500.sqx (Marketplace Shared Hub, D1)
//--------------------------------------------------------------------
Main chart = Current Symbol / Current TF; Subchart1 = SPY.D / D1;
Entry Condition:
   Close[0] < (Close[3] * 0.95)
   AND Close[0] > SMA(PRICE_CLOSE, 200)[1]
   AND Close(Subchart1, D1)[0] > SMA(Subchart1, D1, PRICE_CLOSE, 200)[1]
Order: Open Long order at Market; Exit After 10 bars;
Exit Condition: Close[0] > High[1]

//--------------------------------------------------------------------
// 3) Larry_Connors-SPY.sqx (Marketplace Double 7, D1)
//--------------------------------------------------------------------
Entry Condition (On Bar Close):
   Close[1] > SMA(PRICE_CLOSE, 200)[1]
   AND Close[1] <= MIN(PRICE_CLOSE, 7)[1]
Order: Open Long order at Market; Duplicate trades = disabled;
Exit Condition (On Bar Close):
   Close[1] >= MAX(PRICE_CLOSE, 7)[1]
```

### Código MQL5
> **Nota técnica de SQX Build 145:** Las tres variantes pertenecen al motor *AlgoCloud / Stockpicker*, por lo que `get_strategy_source` de SQX Build 145 no exporta directamente a `.mq5`. Se incluye la **traducción MQL5 equivalente** configurable entre modo `buy_dips` (`RSI(5)<30` + `BuyLimit -0.5*ATR(14)`) y modo `Double7` (`MIN/MAX Close 7`) con `StopLoss` de seguridad en ATR.

```mql5
#include <Trade/Trade.mqh>
input bool   InpUseDouble7   = false; // false = buy_dips (RSI5 + Limit ATR), true = Double 7
input int    InpSmaTrend     = 250;   // 250 (buy_dips) / 200 (Double 7)
input int    InpRsiPeriod    = 5;
input double InpRsiLevel     = 30.0;
input int    InpEmaExit      = 7;
input int    InpAtrPeriod    = 14;
input double InpLimitAtr     = 0.5;
input double InpStopAtrMult  = 3.0;   // Stop protector amplio para futuros
input int    InpMaxHoldBars  = 20;
input double InpLots         = 0.10;
input long   InpMagic        = 92010;

int hSma, hRsi, hEma, hAtr;
datetime lastBar = 0;
ulong pendingTicket = 0;
int pendingAge = 0;
CTrade trade;

int OnInit() {
   trade.SetExpertMagicNumber(InpMagic);
   hSma = iMA(_Symbol, _Period, InpSmaTrend, 0, MODE_SMA, PRICE_CLOSE);
   hRsi = iRSI(_Symbol, _Period, InpRsiPeriod, PRICE_CLOSE);
   hEma = iMA(_Symbol, _Period, InpEmaExit, 0, MODE_EMA, PRICE_OPEN);
   hAtr = iATR(_Symbol, _Period, InpAtrPeriod);
   return (hSma!=INVALID_HANDLE && hRsi!=INVALID_HANDLE && hEma!=INVALID_HANDLE && hAtr!=INVALID_HANDLE)
          ? INIT_SUCCEEDED : INIT_FAILED;
}

void OnTick() {
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == lastBar) return;
   lastBar = t0;

   if(pendingTicket > 0 && OrderSelect(pendingTicket)) {
      pendingAge++;
      if(pendingAge >= 2) { trade.OrderDelete(pendingTicket); pendingTicket = 0; pendingAge = 0; }
   }

   double sma[1], rsi[1], ema[1], atr[1], cl7[];
   if(CopyBuffer(hSma,0,1,1,sma)<1 || CopyBuffer(hRsi,0,1,1,rsi)<1 || CopyBuffer(hEma,0,1,1,ema)<1 || CopyBuffer(hAtr,0,1,1,atr)<1) return;
   if(CopyClose(_Symbol,_Period,1,7,cl7)<7) return;
   double c1 = iClose(_Symbol,_Period,1), o0 = iOpen(_Symbol,_Period,0);

   if(PositionSelect(_Symbol)) {
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int held = iBarShift(_Symbol,_Period,openTime);
      double max7 = cl7[ArrayMaximum(cl7)];
      if(InpUseDouble7) {
         if(c1 >= max7) trade.PositionClose(_Symbol);
      } else {
         if(o0 > ema[0] || held >= InpMaxHoldBars) trade.PositionClose(_Symbol);
      }
      return;
   }

   if(InpUseDouble7) {
      double min7 = cl7[ArrayMinimum(cl7)];
      if(c1 > sma[0] && c1 <= min7) {
         trade.Buy(InpLots, _Symbol, 0.0, NormalizeDouble(o0 - InpStopAtrMult*atr[0], _Digits), 0.0, "Double7_L");
      }
   } else if(o0 > sma[0] && rsi[0] < InpRsiLevel) {
      double limitPx = NormalizeDouble(c1 - InpLimitAtr * atr[0], _Digits);
      double sl = NormalizeDouble(limitPx - InpStopAtrMult * atr[0], _Digits);
      if(trade.BuyLimit(InpLots, limitPx, _Symbol, sl, 0.0, ORDER_TIME_GTC, 0, "BuyDips_L")) {
         pendingTicket = trade.ResultOrder(); pendingAge = 0;
      }
   }
}
```

| Parámetro | `buy_dips.sqx` | `Larry_Connors-SPY.sqx` | Notas |
|---|---|---|---|
| Filtro tendencia | `Open > SMA(250)` | `Close > SMA(200)` | Sólo compra debilidad dentro de tendencia primaria alcista |
| Gatillo sobreventa | `RSI(5) < 30` | `Close <= MIN(Close, 7)` | Contrarian corto plazo (`5–7` días) |
| Entrada | `BuyLimit = Close - 0.5*ATR(14)` (`2` días) | `Market` al cierre | `ATR Limit` reduce exposición a caídas suaves |
| Salida | `Open > EMA(Open, 7)` o `20` velas | `Close >= MAX(Close, 7)` | Captura rebote hacia la media rápida |

---

## Backtest de catálogo (NO evidencia para EdgeLab)

- **Para `Larry_Connors-SPY.sqx` (publicado literalmente en el catálogo `strategyquant.com/shared/`):**
  - Instrumento / Período: **`SPY`, `D1`, `1993.01 – 2026.09`** (`100%` capital por operación sobre `$10,000` iniciales, investigación sin gestión monetaria realista).
  - Resultados reportados en el sitio: **`333` trades**, Net Profit `~$143,000`, **Profit Factor `2.35`**, Sharpe `0.85`, **Max Drawdown `~12.5%`**, exposición `~28%`.
  - El propio artículo advierte explícitamente que en **bonos del Tesoro de larga duración** funcionó mal porque los bonos responden a expectativas de tasas más que a sobreventa por pánico bursátil.
- **Advertencia obligatoria EdgeLab:** Este backtest **NO constituye evidencia para nosotros**: primero, `SPY` cubre `1993–2026.09` sin nuestros costos ni formato `R` y con tamaño del `100%`; segundo, carece de `StopLoss` duro (sufre riesgo de cola en shocks tipo `2008`/`2020`).

---

## Mecanismo y cómo podría refutarse

- **Mecanismo:** Captura rebotes tras liquidaciones rápidas de corto plazo en mercados alcistas seculares (`> SMA 200/250`), actuando como proveedor pasivo de liquidez ante ventas emocionales o rebalanceos forzados (*forced de-risking*).
- **Cómo refutarse en EdgeLab:**
  1. Al exigir un **`StopLoss` en `R`** (`>= 12x` costos, ej. `2.5–3.0 ATR`) y cerrar o no sostener posiciones de forma ilimitada en caídas macro, si el PF cae debajo de `1.15`.
  2. Si en **`FDAX`**, **`GC`** o divisas (`6E`) el patrón no genera ventaja fuera de la prima estructural alcista de renta variable estadounidense (`ES`/`NQ`), quedando redundante respecto a la exposición beta a índices EE. UU. ya presente en `v2`.

## Hueco de diversificación

- **Sesión / Activo / Horizonte / Estilo:** Independiente de la microestructura intradía de apertura NY; horizonte **multi-día (`3–15` días)**; estilo **reversión rápida con filtro secular lento (`SMA 200/250`)**, priorizando validación en **`FDAX`**, **`GC`** y **`ZN`** (con chequeo estricto contra `SMA 200` y stop duro) antes que en `NQ/ES`.
