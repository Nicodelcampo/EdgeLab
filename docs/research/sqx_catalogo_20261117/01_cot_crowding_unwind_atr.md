# Candidata #01 — COT Crowding Unwind + Contracción de Volatilidad + SMA20

- **Nombre en catálogo:** Estrategia 2 (*Crowding Unwind*) + Estrategia 33 (*Volatility-Conditioned COT Reversal*) + Arquitectura recomendada de Capas 1–3
- **Origen exacto:** [`COT_SQX_Strategies_Guide_v8.docx`](file:///C:/StrategyQuantX145/COT/COT_SQX_Strategies_Guide_v8.docx) (párrafos 318–330, 671–685, 841–857) y [`COT_Indicators_and_Signals_Reference_Guide_SQX.docx`](file:///C:/StrategyQuantX145/COT/COT_Indicators_and_Signals_Reference_Guide_SQX.docx)
- **Autor / fecha:** Documentación oficial SQX / SpreadCharts (`COT v8`, agosto 2026)
- **Instrumento y timeframe originales:** Futuros físicos (metales `GC`/`HG`/`SI`, energía `CL`/`NG`, granos `ZC`/`ZW`/`ZS`), divisas (`6E`, `6B`, `6J`) y tasas (`ZB`/`ZN`); barras **`H4` o `D1`** con serie semanal COT alineada estrictamente por fecha de publicación (*no-lookahead*).

---

## Reglas completas y parámetros por defecto

### Lógica de capas (sin *lookahead*)
- **Regla causal COT:** Cada barra `H4`/`D1` recibe el último reporte CFTC COT cuya **fecha de publicación pública** (típicamente viernes 15:30 ET, nunca la fecha de corte de martes anterior a su publicación) sea `<= tiempo_barra`. En SQX, los bloques booleanos usan escala `0..1` (equivale a `0..100` en indicadores numéricos).
- **Largo:**
  1. Hubo hacinamiento bajista extremo de grandes especuladores y cobertura alcista comercial: `cpispec_52w[1] < 0.10` (y `cpispec_156w < 0.20`, `cpihedg_52w > 0.75`).
  2. Comienza el desarme (*unwind*): `cpispec_52w > cpispec_52w[1]` (en reportes semanales).
  3. La volatilidad reciente se estabiliza/contrae (evita atrapar cuchillos): `ATR(14) < ATR(14)[5]`.
  4. Gatillo de precio al cierre de barra: `Close[1] crosses above SMA(20)[1]` (o `Close[1] > SMA(20)[1]` cuando `Close[2] <= SMA(20)[2]`).
- **Corto (espejo):**
  1. `cpispec_52w[1] > 0.90`, `cpispec_156w > 0.80`, `cpihedg_52w < 0.25`.
  2. Desarme especulativo: `cpispec_52w < cpispec_52w[1]`.
  3. Estabilización de volatilidad: `ATR(14)[1] < ATR(14)[6]`.
  4. Gatillo de precio: `Close[1] crosses below SMA(20)[1]`.
- **Gestión de salida y riesgo (Capa 3 del catálogo):**
  - `StopLoss = 2.0 * ATR(14)[1]`
  - `ProfitTarget = 4.0 * ATR(14)[1]` *(alternativa del catálogo: trailing stop)*
  - **Cierre de viernes (adaptación EdgeLab):** cerrar posición abierta los viernes a `15:55 NY` (`22:55 EST+07`) y permitir reentrada lunes tras confirmación, o evaluar impacto semanal frente a riesgo de gap.

### Pseudocódigo SQX
```text
VARIABLES:
  SpecExtremeHigh = 0.90, SpecExtremeLow = 0.10
  SpecStructHigh  = 0.80, SpecStructLow  = 0.20
  HedgerExtremeHi = 0.75, HedgerExtremeLo = 0.25
  SmaPeriod = 20, AtrPeriod = 14, AtrLookback = 5
  StopAtrMult = 2.0, TargetAtrMult = 4.0

// Long (evaluated on bar close, market flat)
IF COT_SpecCPI(52w, prev_report) < SpecExtremeLow
   AND COT_SpecCPI(156w, cur_report) < SpecStructLow
   AND COT_HedgerCPI(52w, cur_report) > HedgerExtremeHi
   AND COT_SpecCPI(52w, cur_report) > COT_SpecCPI(52w, prev_report)
   AND ATR(AtrPeriod)[1] < ATR(AtrPeriod)[1 + AtrLookback]
   AND Close[1] > SMA(SmaPeriod)[1] AND Close[2] <= SMA(SmaPeriod)[2]
THEN EnterAtMarket(Long, SL = 2.0 * ATR(14)[1], TP = 4.0 * ATR(14)[1]);

// Short mirror
IF COT_SpecCPI(52w, prev_report) > SpecExtremeHigh
   AND COT_SpecCPI(156w, cur_report) > SpecStructHigh
   AND COT_HedgerCPI(52w, cur_report) < HedgerExtremeLo
   AND COT_SpecCPI(52w, cur_report) < COT_SpecCPI(52w, prev_report)
   AND ATR(AtrPeriod)[1] < ATR(AtrPeriod)[1 + AtrLookback]
   AND Close[1] < SMA(SmaPeriod)[1] AND Close[2] >= SMA(SmaPeriod)[2]
THEN EnterAtMarket(Short, SL = 2.0 * ATR(14)[1], TP = 4.0 * ATR(14)[1]);
```

### Reconstrucción fiel en MQL5
```mql5
#include <Trade/Trade.mqh>
input int    InpSmaPeriod    = 20;
input int    InpAtrPeriod    = 14;
input int    InpAtrCompShift = 5;
input double InpSlAtrMult    = 2.0;
input double InpTpAtrMult    = 4.0;
input double InpLots         = 0.10;
input long   InpMagic        = 91001;

// Proveedor semanal causal (fecha publicación CFTC <= bar_time):
// Debe exponer: GetCotCpi(bool is_spec, int weeks, int report_shift) en escala [0..1]
// report_shift=0 -> último reporte publicado; report_shift=1 -> reporte semanal previo.
int hSma = INVALID_HANDLE, hAtr = INVALID_HANDLE;
datetime lastBarTime = 0;
CTrade trade;

int OnInit() {
   trade.SetExpertMagicNumber(InpMagic);
   hSma = iMA(_Symbol, _Period, InpSmaPeriod, 0, MODE_SMA, PRICE_CLOSE);
   hAtr = iATR(_Symbol, _Period, InpAtrPeriod);
   return (hSma != INVALID_HANDLE && hAtr != INVALID_HANDLE) ? INIT_SUCCEEDED : INIT_FAILED;
}

void OnTick() {
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == lastBarTime) return;
   lastBarTime = t0;
   if(PositionSelect(_Symbol)) return;

   double sma[3], atr[10], c1 = iClose(_Symbol, _Period, 1), c2 = iClose(_Symbol, _Period, 2);
   if(CopyBuffer(hSma, 0, 1, 2, sma) < 2 || CopyBuffer(hAtr, 0, 1, InpAtrCompShift + 2, atr) < InpAtrCompShift + 2) return;
   double atrNow = atr[InpAtrCompShift + 1], atrPrev = atr[1]; // buffer ascendente: [last]=shift 1
   double sma1 = sma[1], sma2 = sma[0];

   double s52_0 = GetCotCpi(true, 52, 0), s52_1 = GetCotCpi(true, 52, 1);
   double s156  = GetCotCpi(true, 156, 0), h52 = GetCotCpi(false, 52, 0);
   bool volContract = (atrNow < atrPrev);
   double open0 = iOpen(_Symbol, _Period, 0);

   if(s52_1 < 0.10 && s156 < 0.20 && h52 > 0.75 && s52_0 > s52_1 && volContract && c1 > sma1 && c2 <= sma2) {
      double sl = NormalizeDouble(open0 - InpSlAtrMult * atrNow, _Digits);
      double tp = NormalizeDouble(open0 + InpTpAtrMult * atrNow, _Digits);
      trade.Buy(InpLots, _Symbol, 0.0, sl, tp, "COT_CrowdingUnwind_L");
   }
   else if(s52_1 > 0.90 && s156 > 0.80 && h52 < 0.25 && s52_0 < s52_1 && volContract && c1 < sma1 && c2 >= sma2) {
      double sl = NormalizeDouble(open0 + InpSlAtrMult * atrNow, _Digits);
      double tp = NormalizeDouble(open0 - InpTpAtrMult * atrNow, _Digits);
      trade.Sell(InpLots, _Symbol, 0.0, sl, tp, "COT_CrowdingUnwind_S");
   }
}
```

| Parámetro | Valor por defecto | Rango guía SQX | Notas |
|---|---|---|---|
| Ventana rápida / estructural COT | `52` sem / `156` sem | `52` / `156` | Mínimo `3` años de historial CFTC de calentamiento |
| Umbrales hacinamiento `cpispec` | `< 0.10` / `> 0.90` (156w: `0.20`/`0.80`) | `0.05–0.20` / `0.80–0.95` | Requiere acuerdo 52w + 156w |
| Umbrales `cpihedg_52w` | `> 0.75` / `< 0.25` | `0.70–0.90` / `0.10–0.30` | Cobertura comercial opuesta |
| Contracción ATR / Cruce | `ATR(14) < ATR(14)[5]` + `SMA(20)` | `ATR(14)`, `SMA(10–50)` | Evita entrar en medio de liquidación violenta |
| SL / TP | `2.0 * ATR(14)` / `4.0 * ATR(14)` | `2.0x` / `4.0x` ATR | Stop grande (`>> 12x` costos ida/vuelta en futuros líquidos) |

---

## Backtest de catálogo (NO evidencia para EdgeLab)

- La guía `COT v8` es un catálogo de diseño y **no trae tabla de PF/DD por estrategia individual**.
- En la sección empírica interna de SQX (`[R13]`, agosto 2026), los **filtros simples COT aislados** y la variante **Full-Cycle (#39)** evaluados sobre `45` mercados **no** superaron al benchmark aleatorio (`27/45` mejoras vs ~`22` esperadas por azar). Ninguno de estos resultados sirve como evidencia positiva ni negativa definitiva para la versión condicionada (#2 + #33) en futuros individuales de EdgeLab.

---

## Mecanismo y cómo podría refutarse

- **Por qué podría funcionar (mecanismo económico):** Cuando fondos especulativos alcanzan saturación máxima en un lado mientras los coberturistas comerciales cubren agresivamente el lado opuesto, la capacidad marginal de nueva compra/venta especulativa se agota. Esperar a que `cpispec` empiece a caer, a que el `ATR` se enfríe y a que el precio recupere su media de `20` barras evita faders prematuros y captura el desarme forzado del posicionamiento abarrotado.
- **Cómo podría refutarse en EdgeLab:** Si al medirla en `GC`, `CL`, `HG`, `ZN` y `6E` con fechas CFTC reales (publicación viernes post-cierre) en `H4`/`D1`: (1) produce `< 200` trades agregados o por activo en 10+ años; (2) no supera en expectancy R neto a un control aleatorio/misma regla de precio `ATR + SMA(20)` **sin** condición COT (ablación obligatoria del filtro COT).

## Hueco de diversificación

- **Sesión / Activo / Horizonte / Estilo:** Fuera completamente de NY-open NQ/ES. Ataca **materias primas, tasas y FX mayores**, horizonte **multi-día/swing (`H4`/`D1`)**, estilo **reversión institucional guiada por posicionamiento CFTC + volatilidad**. El stop de `2.0 * ATR(14)` en `H4`/`D1` supera holgadamente el requisito de `>= 12x` costo de futuros.
