//+------------------------------------------------------------------+
//| Reconstrucción limpia de QLB_K_XAUUSD_3x_speed_q4_turn.ex5 v1.8  |
//| Framework: QLBATCH Multi-Slot Basket (Hedging obligatorio)       |
//+------------------------------------------------------------------+
#property strict
#include <Trade\Trade.mqh>

input string InpLicenseKey      = "";
input int    InpRiskMode        = 0;     // 0=Percent, 1=Money, 2=FixedLot
input double InpRiskPercent     = 0.75;
input double InpRiskMoney       = 0.0;
input double InpFixedLot        = 0.01;
input bool   InpTradeMinLot     = true;
input long   InpMagicBase       = 871800;
input int    InpSlippage        = 30;
input int    InpTrailSeconds    = 300;
input bool   InpNoHedge         = false;
input double InpCloseAtEquity   = 0.0;
input double InpStopAtEquity    = 0.0;
input int    InpMaxSendsPerDay  = 8;
input double InpMaxDailyLossPct = 4.0;
input bool   InpRandomize       = false;
input int    InpRandomStrength  = 5;

struct SlotState {
   string          name;
   ENUM_TIMEFRAMES tf;
   int             atrHandle;
   datetime        lastBar;
   int             maxHoldBars;
   int             sendsToday;
   long            magic;
};

SlotState g_slots[3];
CTrade    g_trade;
int       g_refDay = -1;
double    g_dayRefEquity = 0.0;

int OnInit() {
   if((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) {
      Print("This basket expert needs a hedging account. Run aborted.");
      return INIT_FAILED;
   }
   g_slots[0].name = "speed_switch_momentum";            g_slots[0].tf = PERIOD_H4; g_slots[0].maxHoldBars = 120;
   g_slots[1].name = "q4_momentum_breakout";             g_slots[1].tf = PERIOD_H1; g_slots[1].maxHoldBars = 40;  // [INFERIDO]
   g_slots[2].name = "turn_of_month_january_momentum_2"; g_slots[2].tf = PERIOD_H1; g_slots[2].maxHoldBars = 40;
   for(int s = 0; s < 3; s++) {
      g_slots[s].magic     = InpMagicBase + s;
      g_slots[s].atrHandle = iATR(_Symbol, g_slots[s].tf, 14);
      g_slots[s].lastBar   = iTime(_Symbol, g_slots[s].tf, 0); // Evita operar barra incompleta inicial
   }
   return INIT_SUCCEEDED;
}

double CalcSlotLots(double slDist) {
   if(InpRiskMode == 2) return NormalizeDouble(InpFixedLot, 2);
   double riskCash = (InpRiskMode == 0) ? AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPercent / 100.0) : InpRiskMoney;
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double raw = riskCash / MathMax((slDist / ts) * tv, 1e-9);
   if(raw < minLot) return InpTradeMinLot ? minLot : 0.0;
   return MathMin(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), MathFloor(raw / step) * step);
}

void ProcessSlot(int s, bool dailyStopped) {
   datetime barTime = iTime(_Symbol, g_slots[s].tf, 0);
   if(barTime == g_slots[s].lastBar) return; // Solo al cierre de vela del timeframe del slot
   g_slots[s].lastBar = barTime;

   // 1) Gestión de salida por tiempo (MaxHoldBars: 120 H4 en Slot 0; 40 H1 en Slot 2)
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == g_slots[s].magic) {
         datetime openT = (datetime)PositionGetInteger(POSITION_TIME);
         int heldBars = iBarShift(_Symbol, g_slots[s].tf, openT, false);
         if(heldBars >= g_slots[s].maxHoldBars)
            g_trade.PositionClose(PositionGetInteger(POSITION_TICKET));
         return; // Máximo 1 posición simultánea por slot
      }
   }

   if(dailyStopped || (InpMaxSendsPerDay > 0 && g_slots[s].sendsToday >= InpMaxSendsPerDay)) return;

   // 2) Evaluación de señal por slot
   MqlDateTime dt; TimeToStruct(barTime, dt);
   int dir = 0; // +1 BUY, -1 SELL
   if(s == 0) {
      // [INFERIDO] speed_switch_momentum (H4 Long/Short: tendencia + filtro de cambio de velocidad ATR)
   } else if(s == 1) {
      if(dt.mon >= 10) { /* [INFERIDO] q4_momentum_breakout (H1, solo Q4) */ }
   } else if(s == 2) {
      // [VERIFICADO] Solo Long; ventana Turn-of-Month (~1eros días del mes) ampliada en enero (<= día 13..14)
      bool seasonOk = (dt.mon == 1 && dt.day <= 14) || (dt.day <= 8);
      if(seasonOk) { /* [INFERIDO] gatillo momentum horario alcista */ }
   }

   if(dir == 0) return;

   // 3) SL = 2.5 * iATR(tf, 14)[1]  |  TP = 5.0 * iATR(tf, 14)[1] (RR = 2.00 verificada 57/57)
   double atr[1];
   if(CopyBuffer(g_slots[s].atrHandle, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;
   double slDist = 2.5 * atr[0];
   double tpDist = 5.0 * atr[0];
   double lots   = CalcSlotLots(slDist);
   if(lots <= 0) return;

   g_trade.SetExpertMagicNumber(g_slots[s].magic);
   g_trade.SetDeviationInPoints(InpSlippage);
   if(dir > 0) {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      g_trade.Buy(lots, _Symbol, ask, NormalizeDouble(ask - slDist, _Digits), NormalizeDouble(ask + tpDist, _Digits));
   } else {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      g_trade.Sell(lots, _Symbol, bid, NormalizeDouble(bid + slDist, _Digits), NormalizeDouble(bid - tpDist, _Digits));
   }
   g_slots[s].sendsToday++;
}

void OnTick() {
   MqlDateTime dt; TimeCurrent(dt);
   if(dt.day_of_year != g_refDay) {
      g_refDay = dt.day_of_year;
      g_dayRefEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      for(int s = 0; s < 3; s++) g_slots[s].sendsToday = 0;
   }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   bool dailyStopped = (InpMaxDailyLossPct > 0 && eq < g_dayRefEquity * (1.0 - InpMaxDailyLossPct / 100.0));
   for(int s = 0; s < 3; s++) ProcessSlot(s, dailyStopped);
}
