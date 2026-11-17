# Candidata #05 — Turtles Breakout 55/20 + Régimen Volatilidad (Donchian Clásico)

- **Nombre en catálogo:** *Turtles Breakout Trading Strategy* (`Turtle_longterm-1.sqx` y `Turtle_shortterm-1.sqx`)
- **Origen exacto:** Marketplace / Shared Hub oficial de StrategyQuant X — [`https://strategyquant.com/shared/turtles-breakout-trading-strategy/`](https://strategyquant.com/shared/turtles-breakout-trading-strategy/)
- **Autor / fecha:** Tomas Vanek & Tomas Matejka / StrategyQuant (`2025-09-29`)
- **Instrumento y timeframe originales:** `[[Nasdaq 100]]` + `QQQ.D` (`Turtle_longterm-1.sqx`, engine Stockpicker) y `[QQQ.D]` (`Turtle_shortterm-1.sqx`, engine AlgoCloud Single-asset), **`D1`** *(portable directamente a futuros multi-activo: `GC`, `CL`, `6E`, `6J`, `FDAX`, `ZN` en `D1` o `H4` para ampliar frecuencia y evitar NQ/ES NY-open)*

---

## Reglas completas y parámetros por defecto

### Dos variantes oficiales publicadas en el `.sqx`
1. **Variante Largo Plazo (`Turtle_longterm-1.sqx` — Sistema 2 clásico modificado):**
   - **Entrada Larga (al cierre de barra `OnBarClose`):**
     - `Close[0] > Highest(High, 55)[1]` *(ruptura de canal Donchian 55 días)*
     - `EMA(Subchart1, Close, 20)[1] > EMA(Subchart1, Close, 350)[1]` *(filtro tendencial de largo plazo)*
     - `ATR(10)[1] < ATR(200)[1]` *(filtro anti-expansión excesiva: evita entrar tras picos de volatilidad)*
   - **Stop inicial y salida:**
     - `StopLoss = 2 * ATR(20)`
     - **Salida por canal opuesto:** `Close[0] < Lowest(Low, 20)[1]`
     - **Ranking de cartera (si multi-activo):** `Momentum(Close, 10)[1]`, máx. `10` posiciones, `10%` por posición.
2. **Variante Corto Plazo (`Turtle_shortterm-1.sqx` — Sistema 1 clásico modificado):**
   - **Entrada Larga (al cierre `OnBarClose`):**
     - `Close[0] > Highest(High, 20)[1]`
     - `EMA(Close, 20)[1] > EMA(Close, 350)[1]`
   - **Stop inicial y salida:**
     - `StopLoss = 2 * ATR(20)`
     - **Salida por canal opuesto:** `Close[0] < Lowest(Low, 10)[1]`
   - **Nota de adaptación a EdgeLab:** En futuros líquidos no bursátiles (`GC`, `CL`, `6E`, `6J`, `FDAX`, `ZN`), el modelo puede hacerse bidireccional (cortos simétricos con `EMA(20) < EMA(350)` y `Close < Lowest(Low, 55/20)[1]`) y operarse tanto en `D1` (evaluando impacto del cierre de viernes) como en `H4` cerrado el viernes `15:55 NY` para acumular `>= 200` trades con cero riesgo de fin de semana.

### Pseudocódigo oficial (generado por SQX Build 145)
```text
//--------------------------------------------------------------------
// 1) Turtle_longterm-1.sqx (AlgoCloud Stockpicker, D1)
//--------------------------------------------------------------------
Main chart = Current Symbol / Current TF;
Subchart1  = QQQ.D / D1;

Entry Condition (On Bar Close):
   Close(Main chart)[0] > MAX(Main chart, PRICE_HIGH, 55)[1]
   AND EMA(Subchart1, D1, PRICE_CLOSE, 20)[1] > EMA(Subchart1, D1, PRICE_CLOSE, 350)[1]
   AND ATR(Main chart, 10)[1] < ATR(Main chart, 200)[1]
Order: Open Long order at Market;
   Stop Loss = 2 * ATR(20);
Exit Condition (On Bar Close):
   Close(Main chart)[0] < MIN(Main chart, PRICE_LOW, 20)[1]
Position Score = Momentum(Main chart, PRICE_CLOSE, 10)[1]; Max positions: 10; Risk 10% of account

//--------------------------------------------------------------------
// 2) Turtle_shortterm-1.sqx (AlgoCloud Single-asset, D1)
//--------------------------------------------------------------------
Entry Condition (On Bar Close):
   Close(Main chart)[0] > MAX(Main chart, PRICE_HIGH, 20)[1]
   AND EMA(Main chart, PRICE_CLOSE, 20)[1] > EMA(Main chart, PRICE_CLOSE, 350)[1]
Order: Open Long order at Market;
   Stop Loss = 2 * ATR(20);
Exit Condition (On Bar Close):
   Close(Main chart)[0] < MIN(Main chart, PRICE_LOW, 10)[1]
Risk 10% of account
```

### Código MQL5
> **Nota técnica de SQX Build 145:** Al invocar `get_strategy_source(format="Expert Advisor for MetaTrader5 (*.MQ5)")` sobre `Turtle_longterm-1.sqx` y `Turtle_shortterm-1.sqx`, SQX informó: *"Stockpicker strategies are not supported for this platform... supported only in algocloud.com"*. Por ello abajo se incluye la **implementación MQL5 directa equivalente** para MetaTrader 5 basada exactamente en sus reglas (con opción simétrica de cortos para futuros/FX).

```mql5
#include <Trade/Trade.mqh>
input int    InpEntryChannel = 55;     // 55 (longterm) o 20 (shortterm)
input int    InpExitChannel  = 20;     // 20 (longterm) o 10 (shortterm)
input int    InpEmaFast      = 20;
input int    InpEmaSlow      = 350;
input int    InpAtrStopPer   = 20;
input double InpSlAtrMult    = 2.0;
input bool   InpUseVolFilter = true;   // ATR(10) < ATR(200)
input bool   InpAllowShort   = true;   // Simétrico para FX/commodities
input double InpLots         = 0.10;
input long   InpMagic        = 92005;

int hEmaF, hEmaS, hAtr20, hAtr10, hAtr200;
datetime lastBar = 0;
CTrade trade;

int OnInit() {
   trade.SetExpertMagicNumber(InpMagic);
   hEmaF   = iMA(_Symbol, _Period, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaS   = iMA(_Symbol, _Period, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hAtr20  = iATR(_Symbol, _Period, InpAtrStopPer);
   hAtr10  = iATR(_Symbol, _Period, 10);
   hAtr200 = iATR(_Symbol, _Period, 200);
   return (hEmaF!=INVALID_HANDLE && hEmaS!=INVALID_HANDLE && hAtr20!=INVALID_HANDLE) ? INIT_SUCCEEDED : INIT_FAILED;
}

void OnTick() {
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == lastBar) return;
   lastBar = t0;

   double ef[1], es[1], a20[1], a10[1], a200[1], hi[], lo[], hiEx[], loEx[];
   if(CopyBuffer(hEmaF,0,1,1,ef)<1 || CopyBuffer(hEmaS,0,1,1,es)<1 || CopyBuffer(hAtr20,0,1,1,a20)<1) return;
   if(InpUseVolFilter && (CopyBuffer(hAtr10,0,1,1,a10)<1 || CopyBuffer(hAtr200,0,1,1,a200)<1)) return;
   if(CopyHigh(_Symbol,_Period,2,InpEntryChannel,hi)<InpEntryChannel || CopyLow(_Symbol,_Period,2,InpEntryChannel,lo)<InpEntryChannel) return;
   if(CopyHigh(_Symbol,_Period,2,InpExitChannel,hiEx)<InpExitChannel || CopyLow(_Symbol,_Period,2,InpExitChannel,loEx)<InpExitChannel) return;

   double c1 = iClose(_Symbol, _Period, 1);
   double maxEntry = hi[ArrayMaximum(hi)], minEntry = lo[ArrayMinimum(lo)];
   double minExit  = loEx[ArrayMinimum(loEx)], maxExit = hiEx[ArrayMaximum(hiEx)];

   if(PositionSelect(_Symbol)) {
      long ptype = PositionGetInteger(POSITION_TYPE);
      if(ptype == POSITION_TYPE_BUY && c1 < minExit) trade.PositionClose(_Symbol);
      else if(ptype == POSITION_TYPE_SELL && c1 > maxExit) trade.PositionClose(_Symbol);
      return;
   }

   bool volOk = (!InpUseVolFilter || a10[0] < a200[0]);
   double open0 = iOpen(_Symbol, _Period, 0);
   if(c1 > maxEntry && ef[0] > es[0] && volOk) {
      trade.Buy(InpLots, _Symbol, 0.0, NormalizeDouble(open0 - InpSlAtrMult*a20[0], _Digits), 0.0, "Turtle_L");
   } else if(InpAllowShort && c1 < minEntry && ef[0] < es[0] && volOk) {
      trade.Sell(InpLots, _Symbol, 0.0, NormalizeDouble(open0 + InpSlAtrMult*a20[0], _Digits), 0.0, "Turtle_S");
   }
}
```

| Parámetro | `Turtle_longterm` | `Turtle_shortterm` | Notas |
|---|---|---|---|
| Canal entrada / salida | `55` / `20` barras (`High/Low`) | `20` / `10` barras (`High/Low`) | Ruptura clásica Donchian |
| Filtro régimen | `EMA(20) > EMA(350)` + `ATR(10) < ATR(200)` | `EMA(20) > EMA(350)` | Evita largos en bear secular o clímax volátil |
| Stop inicial | `2 * ATR(20)` | `2 * ATR(20)` | Tamaño amplio `>> 12x` fricción |
| Profit Target | Ninguno (salida por canal opuesto) | Ninguno | Captura colas tendenciales derechas |

---

## Backtest de catálogo (NO evidencia para EdgeLab)

- Ambos `.sqx` almacenan backtests en `AlgoCloud`:
  - `Turtle_longterm-1.sqx`: `[[Nasdaq 100]]`, `D1`, `1993.10.01 – 2025.09.05`.
  - `Turtle_shortterm-1.sqx`: `[QQQ.D]`, `D1`, `1999.03.10 – 2025.09.05`.
- Métricas agregadas en binario interno `SQStats`; la página web no lista tabla numérica pública. **No constituye evidencia para EdgeLab** (y probarla en `Nasdaq/QQQ` violaría la prioridad de diversificar fuera de índices US; debe trasladarse a commodities/FX/DAX/tasas).

---

## Mecanismo y cómo podría refutarse

- **Mecanismo:** Seguimiento puro de tendencias macro (*trend following* con sesgo positivo por asimetría de colas). El filtro `ATR(10) < ATR(200)` mejora el clásico sistema Turtle impidiendo comprar rupturas tardías que ocurren tras expansiones extremas de rango, mientras `EMA(20)/EMA(350)` evita rupturas falsas contracorriente.
- **Cómo refutarse en EdgeLab:** Si al correrlo en futuros no-NQ/ES (`GC`, `CL`, `6E`, `6J`, `FDAX`, `ZN` en `H4` y `D1` pre-holdout con cierre viernes y sin él): (1) la ganancia se destruye al obligar a cerrar posiciones cada viernes `15:55 NY`; (2) el PF neto tras deslizamiento real en `H4`/`D1` cae por debajo de `1.10` durante regímenes laterales prolongados (ej. FX 2015–2019).

## Hueco de diversificación

- **Sesión / Activo / Horizonte / Estilo:** Independiente de la apertura NY de NQ/ES si se aplica en **metales (`GC`), energía (`CL`), tasas (`ZN`) y FX (`6E`/`6J`)** o **`FDAX`**; horizonte **swing multi-día**; estilo **ruptura de canal Donchian con trailing implícito (`Lowest 20/10`) sin TP fijo**. El stop `2 * ATR(20)` cumple sobradamente `>= 12x` costos ida/vuelta.
