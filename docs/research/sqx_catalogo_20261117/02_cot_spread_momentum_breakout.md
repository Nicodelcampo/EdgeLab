# Candidata #02 — COT Hedger–Spec Spread + ROC4 + Ruptura 20 Barras

- **Nombre en catálogo:** Estrategia 26 (*Hedger-Speculator Spread*) + Estrategia 37 (*Absolute Level + Momentum*) + sección *Five Ideas to Prioritize*
- **Origen exacto:** [`COT_SQX_Strategies_Guide_v8.docx`](file:///C:/StrategyQuantX145/COT/COT_SQX_Strategies_Guide_v8.docx) (párrafos 578–593, 725–737, 791–805) y [`COT_Indicators_and_Signals_Reference_Guide_SQX.docx`](file:///C:/StrategyQuantX145/COT/COT_Indicators_and_Signals_Reference_Guide_SQX.docx)
- **Autor / fecha:** Documentación oficial SQX / SpreadCharts (`COT v8`, agosto 2026; derivada de Wang 2001 y Briese Movement Index)
- **Instrumento y timeframe originales:** Materias primas (`CL`, `NG`, `HG`, `GC`, granos `ZC`/`ZS`/`ZW`) y divisas (`6E`, `6B`); **`H4` o `D1`**.

---

## Reglas completas y parámetros por defecto

- **Definiciones COT (escala normalizada `-1.0` a `+1.0`, o `-100` a `+100` en bloque numérico SQX; sin *lookahead* usando fecha de publicación CFTC):**
  - `COTSpread52 = cpihedg_52w - cpispec_52w` (en indicador numérico SQX: `(COT) Hedger-Spec Spread`).
  - `SpreadROC4 = COTSpread52[report_0] - COTSpread52[report_4]` (diferencia respecto a `4` reportes semanales ≈ `1` mes atrás).
- **Largo:**
  1. Nivel de divergencia ya favorable (comerciales mucho más largos en su rango histórico que especuladores): `COTSpread52 > +0.65` *(guía sección prioritaria, párrafos 794–795; variantes `0.40–0.70`)*.
  2. La divergencia sigue fortaleciéndose en las últimas 4 semanas (evita señales rancias ya en decadencia): `SpreadROC4 > +0.15` *(párrafo 795; o `+0.20` en Estrategia 37)*.
  3. Confirmación de ruptura de precio (`Estrategia 17` / *Breakout*): `Close[1] > Highest(High, 20)[2]` *(o cruce sobre máximo de 20 velas anteriores)*.
- **Corto (espejo):**
  1. `COTSpread52 < -0.65`
  2. `SpreadROC4 < -0.15`
  3. `Close[1] < Lowest(Low, 20)[2]`
- **Gestión de salida y riesgo:**
  - `StopLoss = 2.0 * ATR(14)[1]`
  - `ProfitTarget = 4.0 * ATR(14)[1]`
  - **Cierre de viernes (adaptación EdgeLab):** cerrar los viernes `15:55 NY` si se exige `0` exposición de fin de semana.

### Pseudocódigo SQX
```text
VARIABLES:
  SpreadThresh = 0.65      // escala [-1, +1] (equivalente a +65 en bloque -100..+100)
  Roc4Thresh   = 0.15
  BreakoutLen  = 20
  AtrPeriod    = 14
  SlMult = 2.0, TpMult = 4.0

COTSpread_0 = COT_HedgerCPI(52w, rep=0) - COT_SpecCPI(52w, rep=0)
COTSpread_4 = COT_HedgerCPI(52w, rep=4) - COT_SpecCPI(52w, rep=4)
SpreadROC4  = COTSpread_0 - COTSpread_4

IF MarketPositionIsFlat THEN
  IF COTSpread_0 > SpreadThresh AND SpreadROC4 > Roc4Thresh
     AND Close[1] > Highest(High, BreakoutLen)[2]
  THEN EnterAtMarket(Long, SL = 2.0 * ATR(14)[1], TP = 4.0 * ATR(14)[1]);

  IF COTSpread_0 < -SpreadThresh AND SpreadROC4 < -Roc4Thresh
     AND Close[1] < Lowest(Low, BreakoutLen)[2]
  THEN EnterAtMarket(Short, SL = 2.0 * ATR(14)[1], TP = 4.0 * ATR(14)[1]);
```

### Reconstrucción fiel en MQL5
```mql5
#include <Trade/Trade.mqh>
input double InpSpreadThresh = 0.65;
input double InpRoc4Thresh   = 0.15;
input int    InpBreakoutLen  = 20;
input int    InpAtrPeriod    = 14;
input double InpSlAtrMult    = 2.0;
input double InpTpAtrMult    = 4.0;
input double InpLots         = 0.10;
input long   InpMagic        = 91002;

int hAtr = INVALID_HANDLE;
datetime lastBar = 0;
CTrade trade;

int OnInit() {
   trade.SetExpertMagicNumber(InpMagic);
   hAtr = iATR(_Symbol, _Period, InpAtrPeriod);
   return (hAtr != INVALID_HANDLE) ? INIT_SUCCEEDED : INIT_FAILED;
}

void OnTick() {
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == lastBar) return;
   lastBar = t0;
   if(PositionSelect(_Symbol)) return;

   double atrBuf[1], hi[], lo[];
   if(CopyBuffer(hAtr, 0, 1, 1, atrBuf) < 1) return;
   if(CopyHigh(_Symbol, _Period, 2, InpBreakoutLen, hi) < InpBreakoutLen) return;
   if(CopyLow(_Symbol, _Period, 2, InpBreakoutLen, lo) < InpBreakoutLen) return;

   double hi20 = hi[ArrayMaximum(hi)], lo20 = lo[ArrayMinimum(lo)];
   double c1 = iClose(_Symbol, _Period, 1), atr1 = atrBuf[0];
   double sp0 = GetCotCpi(false, 52, 0) - GetCotCpi(true, 52, 0);
   double sp4 = GetCotCpi(false, 52, 4) - GetCotCpi(true, 52, 4);
   double roc4 = sp0 - sp4;
   double open0 = iOpen(_Symbol, _Period, 0);

   if(sp0 > InpSpreadThresh && roc4 > InpRoc4Thresh && c1 > hi20) {
      trade.Buy(InpLots, _Symbol, 0.0,
                NormalizeDouble(open0 - InpSlAtrMult * atr1, _Digits),
                NormalizeDouble(open0 + InpTpAtrMult * atr1, _Digits), "COT_SpreadMom_L");
   } else if(sp0 < -InpSpreadThresh && roc4 < -InpRoc4Thresh && c1 < lo20) {
      trade.Sell(InpLots, _Symbol, 0.0,
                 NormalizeDouble(open0 + InpSlAtrMult * atr1, _Digits),
                 NormalizeDouble(open0 - InpTpAtrMult * atr1, _Digits), "COT_SpreadMom_S");
   }
}
```

| Parámetro | Valor por defecto | Rango guía | Notas |
|---|---|---|---|
| `COTSpread52` umbral | `+/- 0.65` | `0.40–0.80` | `cpihedg_52w - cpispec_52w` |
| `SpreadROC4` (`4` reportes) | `+/- 0.15` | `0.15–0.30` | Descarta señales expiradas |
| Ruptura precio (`BreakoutLen`) | `20` barras | `10–40` | Confirma que el precio acompaña la acumulación |
| `SL` / `TP` | `2.0 * ATR(14)` / `4.0 * ATR(14)` | `2.0x` / `4.0x` | Cumple `>> 12x` costos ida/vuelta |

---

## Backtest de catálogo (NO evidencia para EdgeLab)

- Sin backtest empaquetado en `.sqx`; destacada por el autor en *Five Ideas to Prioritize* (`COT Spread + COT Momentum + price confirmation`, párrafo 805) como la combinación más prometedora tras las pruebas negativas de reglas estáticas simples (`[R13]`). **No constituye evidencia para EdgeLab.**

---

## Mecanismo y cómo podría refutarse

- **Mecanismo:** Combina presión fundamental de cobertura física (*Hedgers* absorbiendo inventario/oferta) y momentum reciente de reposicionamiento a 4 semanas, activando el trade únicamente cuando el mercado valida una ruptura real de `20` barras en esa dirección.
- **Cómo refutarse:** Si en `H4`/`D1` (metales, energía, FX) el filtro `COTSpread52 > 0.65 & ROC4 > 0.15` no aporta incremento estadístico frente a operar el breakout `Highest(20)` / `Lowest(20)` incondicional en la misma muestra pre-holdout, o genera `< 200` operaciones en la cesta objetivo.

## Hueco de diversificación

- **Sesión / Activo / Horizonte / Estilo:** Materias primas y FX, horizonte swing multi-día (`H4`/`D1`), ruptura condicionada a flujo institucional semanal CFTC. Totalmente descorrelacionada de apertura NY NQ/ES.
