//+------------------------------------------------------------------+
//| Reconstrucción limpia de SessionOpenMomentum.ex5 (v2.2)          |
//| Framework: QuantLab / QuantLabRisk.mqh                           |
//+------------------------------------------------------------------+
#property strict
#include <Trade\Trade.mqh>

enum ENUM_QL_RISK_MODE {
   RISK_PERCENT = 0, // risk as % of account balance per trade
   RISK_MONEY   = 1, // fixed amount in account currency per trade
   RISK_FIXED   = 2  // fixed lot size
};

input group "=== Strategy ==="
input string            InpOpenNY          = "16:30"; // New York open in broker server time (HH:MM)
input int               InpFastEma         = 12;      // Signal EMA period (entry)
input int               InpTrailEma        = 120;     // Trailing EMA period (stop follows this EMA)
input double            InpTrailStartR     = 0.5;     // Start trailing at X R profit (1 R = first stop distance)

input group "=== Risk ==="
input ENUM_QL_RISK_MODE InpRiskMode        = RISK_PERCENT; // Risk mode
input double            InpRiskPercent     = 1.0;     // Risk per trade in % of balance
input double            InpRiskMoney       = 0.0;     // Risk per trade in account currency
input double            InpFixedLot        = 0.1;     // Lot size (mode: fixed lot)

input group "=== Adaptive Risk ==="
input bool              InpUseAdaptiveRisk = true;    // Scale risk with volatility (on/off)
input double            InpVolRiskFloor    = 0.5;     // Minimum risk factor (quiet market)
input double            InpVolRiskCap      = 2.0;     // Maximum risk factor (volatile market)

input group "=== Prop Firm Safety - on prop firms the Randomizer MUST be ON ==="
input bool              InpRandomizer      = false;   // Randomizer (jitters entry/SL/lots)
input bool              InpCloseEod        = false;   // Close open position at EOD
input string            InpEodTime         = "22:55"; // End-of-day close time (HH:MM)
input double            InpMaxEquityDDPct  = 0.0;     // Max equity drawdown % - close all & stop
input double            InpCloseAtEquity   = 0.0;     // Equity take-profit target (0 = off)
input double            InpStopAtEquity    = 0.0;     // Equity stop-out floor (0 = off)

CTrade   g_trade;
int      g_hFastEma  = INVALID_HANDLE;
int      g_hTrailEma = INVALID_HANDLE;
int      g_hAtrM5    = INVALID_HANDLE;
datetime g_lastBarM5 = 0;
int      g_lastOpenDay = -1;
datetime g_lastTrailMod = 0;
double   g_peakEquity = 0.0;
double   g_initR = 0.0;
bool     g_halted = false;
ulong    g_magic = 900100;

int ParseHHMM(string hhmm) {
   string p[];
   if(StringSplit(hhmm, ':', p) != 2) return 0;
   return (int)StringToInteger(p[0]) * 60 + (int)StringToInteger(p[1]);
}

double CalcAdaptiveFactor() {
   if(!InpUseAdaptiveRisk) return 1.0;
   // [INFERIDO] Ratio de volatilidad ATR corto vs línea base larga en M5 (acotado [Floor..Cap])
   double atrBuf[];
   ArraySetAsSeries(atrBuf, true);
   if(CopyBuffer(g_hAtrM5, 0, 1, 200, atrBuf) < 200) return 1.0;
   double sum = 0.0;
   for(int i = 0; i < 200; i++) sum += atrBuf[i];
   double ratio = atrBuf[0] / MathMax(sum / 200.0, _Point);
   return MathMax(InpVolRiskFloor, MathMin(InpVolRiskCap, ratio));
}

double CalcLots(double slDist) {
   double mult = CalcAdaptiveFactor();
   if(InpRiskMode == RISK_FIXED) return NormalizeDouble(InpFixedLot, 2);
   double riskCash = (InpRiskMode == RISK_PERCENT)
                     ? AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPercent / 100.0) * mult
                     : InpRiskMoney * mult;
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double raw      = riskCash / MathMax((slDist / tickSize) * tickVal, 1e-9);
   double lots     = MathFloor(raw / step) * step;
   return MathMax(minLot, MathMin(maxLot, NormalizeDouble(lots, 2)));
}

int OnInit() {
   if(_Period != PERIOD_M5)
      PrintFormat("[Momentum] Chart is %s but signals run on PERIOD_M5 (as configured).", EnumToString(_Period));
   g_hFastEma  = iMA(_Symbol, PERIOD_M5, InpFastEma, 0, MODE_EMA, PRICE_CLOSE);
   g_hTrailEma = iMA(_Symbol, PERIOD_M5, InpTrailEma, 0, MODE_EMA, PRICE_CLOSE);
   g_hAtrM5    = iATR(_Symbol, PERIOD_M5, 14); // MQL5 iATR = SMA de TR sobre 14 barras
   g_trade.SetExpertMagicNumber(g_magic);
   g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("[Momentum] Started - waiting for the next New York session.");
   return (g_hFastEma == INVALID_HANDLE || g_hTrailEma == INVALID_HANDLE || g_hAtrM5 == INVALID_HANDLE)
          ? INIT_FAILED : INIT_SUCCEEDED;
}

void OnTick() {
   if(g_halted) return;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peakEquity = MathMax(g_peakEquity, eq);
   if((InpCloseAtEquity > 0 && eq >= InpCloseAtEquity) ||
      (InpStopAtEquity  > 0 && eq <= InpStopAtEquity) ||
      (InpMaxEquityDDPct > 0 && (g_peakEquity - eq) / g_peakEquity * 100.0 >= InpMaxEquityDDPct)) {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
         if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == (long)g_magic)
            g_trade.PositionClose(PositionGetInteger(POSITION_TICKET));
      g_halted = true;
      return;
   }

   MqlDateTime dt;
   TimeCurrent(dt);
   int nowMin = dt.hour * 60 + dt.min;
   int openMin = ParseHHMM(InpOpenNY);
   int eodMin  = ParseHHMM(InpEodTime);

   bool hasPos = false;
   ulong posTicket = 0;
   for(int i = 0; i < PositionsTotal(); i++) {
      if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == (long)g_magic) {
         hasPos = true;
         posTicket = PositionGetInteger(POSITION_TICKET);
         break;
      }
   }

   // Cierre EOD opcional
   if(hasPos && InpCloseEod && nowMin >= eodMin) {
      g_trade.PositionClose(posTicket);
      return;
   }

   // Trailing Stop sobre EMA(120) M5 tras alcanzar +InpTrailStartR * R, cada <= 300s
   if(hasPos && PositionSelectByTicket(posTicket)) {
      long   ptype   = PositionGetInteger(POSITION_TYPE);
      double openPx  = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL   = PositionGetDouble(POSITION_SL);
      double ema120[];
      ArraySetAsSeries(ema120, true);
      if(CopyBuffer(g_hTrailEma, 0, 1, 1, ema120) == 1) {
         double slInitR = (g_initR > 0.0) ? g_initR : MathAbs(openPx - curSL);
         double curPx   = (ptype == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double prof    = (ptype == POSITION_TYPE_BUY) ? (curPx - openPx) : (openPx - curPx);
         if(prof >= InpTrailStartR * slInitR && TimeCurrent() - g_lastTrailMod >= 300) {
            double newSL = NormalizeDouble(ema120[0], _Digits);
            bool valid = (ptype == POSITION_TYPE_BUY)  ? (newSL > curSL + _Point && newSL < curPx) :
                         (ptype == POSITION_TYPE_SELL) ? ((curSL == 0.0 || newSL < curSL - _Point) && newSL > curPx) : false;
            if(valid && g_trade.PositionModify(posTicket, newSL, 0.0))
               g_lastTrailMod = TimeCurrent();
         }
      }
   }

   // Chequeo exacto al minuto InpOpenNY ("still open") y disparo tras cierre de la 1a vela M5 (+5 min)
   int todayKey = dt.year * 1000 + dt.day_of_year;
   datetime m5Time = iTime(_Symbol, PERIOD_M5, 0);
   if(m5Time == g_lastBarM5) return;
   g_lastBarM5 = m5Time;

   if(hasPos && nowMin == openMin && g_lastOpenDay != todayKey) {
      g_lastOpenDay = todayKey;
      Print("[Momentum] A Momentum position is still open at the NY open - no new trade today. Only one Momentum trade at a time.");
      return;
   }

   // Disparo al abrir la vela 16:35:00 (= cierra la barra M5 de las 16:30)
   if(!hasPos && nowMin == openMin + 5 && g_lastOpenDay != todayKey) {
      double c1 = iClose(_Symbol, PERIOD_M5, 1);
      double e12[1], atr[1];
      if(CopyBuffer(g_hFastEma, 0, 1, 1, e12) == 1 && CopyBuffer(g_hAtrM5, 0, 1, 1, atr) == 1) {
         double slDist = 8.0 * atr[0]; // Verificado: exactamente 8.0 x iATR(M5, 14)[1]
         double lots = CalcLots(slDist);
         if(c1 > e12[0]) {
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            if(g_trade.Buy(lots, _Symbol, ask, NormalizeDouble(ask - slDist, _Digits), 0.0))
               g_initR = slDist;
            g_lastOpenDay = todayKey;
         } else if(c1 < e12[0]) {
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            if(g_trade.Sell(lots, _Symbol, bid, NormalizeDouble(bid + slDist, _Digits), 0.0))
               g_initR = slDist;
            g_lastOpenDay = todayKey;
         }
      }
   }
}
