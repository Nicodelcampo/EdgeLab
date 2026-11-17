# Candidata #03 — COT Speculator Trend Following + Pullback RSI/SMA

- **Nombre en catálogo:** Estrategia 12 (*Moderate Speculator Trend Following*) + Estrategia 18 (*COT Pullback*)
- **Origen exacto:** [`COT_SQX_Strategies_Guide_v8.docx`](file:///C:/StrategyQuantX145/COT/COT_SQX_Strategies_Guide_v8.docx) (párrafos 455–460, 495–500) y [`COT_Indicators_and_Signals_Reference_Guide_SQX.docx`](file:///C:/StrategyQuantX145/COT/COT_Indicators_and_Signals_Reference_Guide_SQX.docx)
- **Autor / fecha:** Documentación oficial SQX / SpreadCharts (`COT v8`, agosto 2026; basada en Wang 2001/2004 y Moskowitz et al. 2012)
- **Instrumento y timeframe originales:** FX mayores (`6E`, `6B`, `6J`, `6A`), metales y energía; **`H4` o `D1`**.

---

## Reglas completas y parámetros por defecto

A diferencia de las estrategias contrarian (#1 y #2), ésta prueba la hipótesis **pro-tendencia**: los grandes especuladores suelen acompañar tendencias reales durante meses mientras su posicionamiento no esté saturado (`> 0.90`).

- **Largo:**
  1. Tendencia estructural alcista en precio: `Close[1] > SMA(200)[1]` *(Estrategia 18)*.
  2. Régimen especulativo sano (alcista, subiendo en el último mes, pero **sin** extremo abarrotado `>= 0.85`): `0.60 < cpispec_52w[rep_0] < 0.85` y `cpispec_52w[rep_0] > cpispec_52w[rep_4]` (y estructural `cpispec_156w > 0.55`).
  3. Retroceso táctico de corto plazo (*pullback*): en las últimas velas hubo `RSI(14) < 40` o `Close < SMA(20)`, seguido de giro al alza en cierre actual (`Close[1] > Close[2]` y `Close[1] > SMA(20)[1]` o `RSI(14)[1] > RSI(14)[2]`).
- **Corto (espejo):**
  1. `Close[1] < SMA(200)[1]`.
  2. `0.15 < cpispec_52w[rep_0] < 0.40`, `cpispec_52w[rep_0] < cpispec_52w[rep_4]`, `cpispec_156w < 0.45`.
  3. Hubo rebote sobrecomprado (`RSI(14)[2] > 60` o `Close[2] > SMA(20)[2]`) seguido de giro bajista (`Close[1] < SMA(20)[1]` y `Close[1] < Close[2]`).
- **Gestión de salida y riesgo:**
  - `StopLoss = 2.0 * ATR(14)[1]`
  - `ProfitTarget = 4.0 * ATR(14)[1]` (o *trailing stop* por `ATR` / cierre los viernes `15:55 NY`).

### Pseudocódigo SQX
```text
VARIABLES:
  S52Min = 0.60, S52Max = 0.85, S156Min = 0.55
  SmaLong = 200, SmaPull = 20, RsiPeriod = 14, AtrPeriod = 14
  SlMult = 2.0, TpMult = 4.0

IF MarketPositionIsFlat THEN
  // Long
  IF Close[1] > SMA(SmaLong)[1]
     AND COT_SpecCPI(52w, rep=0) > S52Min AND COT_SpecCPI(52w, rep=0) < S52Max
     AND COT_SpecCPI(156w, rep=0) > S156Min
     AND COT_SpecCPI(52w, rep=0) > COT_SpecCPI(52w, rep=4)
     AND (RSI(RsiPeriod)[2] < 40 OR Close[2] < SMA(SmaPull)[2])
     AND Close[1] > SMA(SmaPull)[1] AND Close[1] > Close[2]
  THEN EnterAtMarket(Long, SL = 2.0 * ATR(14)[1], TP = 4.0 * ATR(14)[1]);

  // Short mirror
  IF Close[1] < SMA(SmaLong)[1]
     AND COT_SpecCPI(52w, rep=0) < (1.0 - S52Min) AND COT_SpecCPI(52w, rep=0) > (1.0 - S52Max)
     AND COT_SpecCPI(156w, rep=0) < (1.0 - S156Min)
     AND COT_SpecCPI(52w, rep=0) < COT_SpecCPI(52w, rep=4)
     AND (RSI(RsiPeriod)[2] > 60 OR Close[2] > SMA(SmaPull)[2])
     AND Close[1] < SMA(SmaPull)[1] AND Close[1] < Close[2]
  THEN EnterAtMarket(Short, SL = 2.0 * ATR(14)[1], TP = 4.0 * ATR(14)[1]);
```

### Reconstrucción fiel en MQL5
```mql5
#include <Trade/Trade.mqh>
input int    InpSmaLong  = 200;
input int    InpSmaPull  = 20;
input int    InpRsiPer   = 14;
input int    InpAtrPer   = 14;
input double InpSlMult   = 2.0;
input double InpTpMult   = 4.0;
input double InpLots     = 0.10;
input long   InpMagic    = 91003;

int hSmaL, hSmaP, hRsi, hAtr;
datetime lastBar = 0;
CTrade trade;

int OnInit() {
   trade.SetExpertMagicNumber(InpMagic);
   hSmaL = iMA(_Symbol, _Period, InpSmaLong, 0, MODE_SMA, PRICE_CLOSE);
   hSmaP = iMA(_Symbol, _Period, InpSmaPull, 0, MODE_SMA, PRICE_CLOSE);
   hRsi  = iRSI(_Symbol, _Period, InpRsiPer, PRICE_CLOSE);
   hAtr  = iATR(_Symbol, _Period, InpAtrPer);
   return (hSmaL!=INVALID_HANDLE && hSmaP!=INVALID_HANDLE && hRsi!=INVALID_HANDLE && hAtr!=INVALID_HANDLE) ? INIT_SUCCEEDED : INIT_FAILED;
}

void OnTick() {
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == lastBar) return;
   lastBar = t0;
   if(PositionSelect(_Symbol)) return;

   double slv[1], spv[2], rsv[1], atv[1];
   if(CopyBuffer(hSmaL,0,1,1,slv)<1 || CopyBuffer(hSmaP,0,1,2,spv)<2 ||
      CopyBuffer(hRsi,0,2,1,rsv)<1  || CopyBuffer(hAtr,0,1,1,atv)<1) return;

   double c1 = iClose(_Symbol,_Period,1), c2 = iClose(_Symbol,_Period,2);
   double s52_0 = GetCotCpi(true, 52, 0), s52_4 = GetCotCpi(true, 52, 4), s156 = GetCotCpi(true, 156, 0);
   double open0 = iOpen(_Symbol,_Period,0), atr1 = atv[0];

   bool bullCot = (s52_0 > 0.60 && s52_0 < 0.85 && s156 > 0.55 && s52_0 > s52_4);
   bool bearCot = (s52_0 < 0.40 && s52_0 > 0.15 && s156 < 0.45 && s52_0 < s52_4);

   if(c1 > slv[0] && bullCot && (rsv[0] < 40.0 || c2 < spv[0]) && c1 > spv[1] && c1 > c2)
      trade.Buy(InpLots, _Symbol, 0.0, NormalizeDouble(open0 - InpSlMult*atr1, _Digits), NormalizeDouble(open0 + InpTpMult*atr1, _Digits), "COT_TrendPull_L");
   else if(c1 < slv[0] && bearCot && (rsv[0] > 60.0 || c2 > spv[0]) && c1 < spv[1] && c1 < c2)
      trade.Sell(InpLots, _Symbol, 0.0, NormalizeDouble(open0 + InpSlMult*atr1, _Digits), NormalizeDouble(open0 - InpTpMult*atr1, _Digits), "COT_TrendPull_S");
}
```

| Parámetro | Valor por defecto | Rango guía | Notas |
|---|---|---|---|
| Banda `cpispec_52w` | `(0.60, 0.85)` / `(0.15, 0.40)` | `0.55–0.90` | Participación tendencial sin sobre-hacinamiento |
| Confirmación `cpispec_156w` | `> 0.55` / `< 0.45` | `> 0.50` / `< 0.50` | Régimen multi-anual alineado |
| Tendencia / Pullback | `SMA(200)` / `RSI(14)<40` o `SMA(20)` | estándar | Mejor precio de entrada dentro de la tendencia |
| `SL` / `TP` | `2.0 * ATR(14)` / `4.0 * ATR(14)` | `2.0x` / `4.0x` | Stop amplio frente a fricción de futuros |

---

## Backtest de catálogo (NO evidencia para EdgeLab)

- Sin backtest tabular propio en `.sqx`; motivada en la guía por estudios académicos de continuación con sentimiento de grandes especuladores (`Wang 2001/2004`) y *time-series momentum* (`Moskowitz et al. 2012`). **No constituye evidencia para EdgeLab.**

---

## Mecanismo y cómo podría refutarse

- **Mecanismo:** Cuando los fondos sistemáticos y macro construyen posición neta moderada y creciente en la misma dirección que la tendencia de `200` velas, los retrocesos cortos contra la tendencia encuentran demanda institucional real en lugar de desarme pánico.
- **Cómo refutarse:** Si `RSI/SMA` pullback sobre `SMA(200)` **sin** banda COT rinde igual o mejor que con la banda `0.60–0.85`, o si la reducción de frecuencia deja `< 200` operaciones en `10+` años.

## Hueco de diversificación

- **Sesión / Activo / Horizonte / Estilo:** FX mayores (`6E`, `6B`, `6J`), energía/metales, horizonte swing intermedio (`H4`/`D1`), estilo **tendencial por retroceso** (complemento natural de #1 contrarian).
