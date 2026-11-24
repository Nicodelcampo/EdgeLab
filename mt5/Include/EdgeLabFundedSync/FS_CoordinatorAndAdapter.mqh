//+------------------------------------------------------------------+
//|                                    FS_CoordinatorAndAdapter.mqh  |
//| EdgeLab FUNDEDSYNC MQL5 Coordinator + StrategyTester/LiveAdapter |
//+------------------------------------------------------------------+
#ifndef FS_COORDINATOR_AND_ADAPTER_MQH
#define FS_COORDINATOR_AND_ADAPTER_MQH

#property strict

#include <Trade\Trade.mqh>
#include "FS_ModuleEngines.mqh"

class CFundedSyncCoordinator : public IFsSignalHost
{
private:
   FsVirtualSleeve      m_sleeves[7];
   CFsModuleEngineBase *m_engines[7];
   double               m_sesAtrQueue[];
   FsCompletedTrade     m_completedTrades[];

   int                  m_newsMinutesEt[];
   int                  m_curEthDate;
   double               m_curSesHi, m_curSesLo, m_curSesClose;
   bool                 m_hadTickStopEval;
   bool                 m_csvHeaderWritten;
   int                  m_csvHandle;

   void EnsureSessionTransition(const FsBarContext &bar)
   {
      for(int i = 0; i < 7; i++) m_engines[i].tickSize = signalTickSize;

      if(bar.ethTradeDate != m_curEthDate)
      {
         int prevD = m_curEthDate;
         double prevH = m_curSesHi, prevL = m_curSesLo, prevC = m_curSesClose;
         if(prevD > 0 && prevH >= prevL)
         {
            double rng = prevH - prevL;
            int n = ArraySize(m_sesAtrQueue);
            if(n < 20)
            {
               ArrayResize(m_sesAtrQueue, n + 1);
               m_sesAtrQueue[n] = rng;
            }
            else
            {
               for(int i = 1; i < 20; i++) m_sesAtrQueue[i - 1] = m_sesAtrQueue[i];
               m_sesAtrQueue[19] = rng;
            }
            if(ArraySize(m_sesAtrQueue) >= 20)
            {
               double s = 0.0;
               for(int i = 0; i < 20; i++) s += m_sesAtrQueue[i];
               atr20Session = s / 20.0;
            }
            else atr20Session = EMPTY_VALUE;
         }
         for(int i = 0; i < 7; i++)
            m_engines[i].OnNewEthSession(prevD, prevH, prevL, prevC, bar.ethTradeDate);
         m_curEthDate = bar.ethTradeDate;
         m_curSesHi = -1e18; m_curSesLo = 1e18; m_curSesClose = EMPTY_VALUE;
         hardFlattenedToday = false; dailyCapTriggeredToday = false; dailyLossTriggeredToday = false;
         realizedSessionUsd = 0.0;
      }

      if(bar.high > m_curSesHi) m_curSesHi = bar.high;
      if(bar.low  < m_curSesLo) m_curSesLo = bar.low;
      m_curSesClose = bar.close;
   }

   bool IsInNewsBlackout(int minEt)
   {
      if(!enableNewsGuard || newsBlackoutMin <= 0) return false;
      int n = ArraySize(m_newsMinutesEt);
      for(int i = 0; i < n; i++)
         if(MathAbs(minEt - m_newsMinutesEt[i]) <= newsBlackoutMin) return true;
      return false;
   }

   void RunComplianceAndEngines(const FsBarContext &bar, double exitBid, double exitAsk)
   {
      openPnlUsd = ComputeOpenPnlUsd(bar.close);
      bool inPreBreakFlatten = (hardFlattenHHMM_ET > 0 && hardFlattenHHMM_ET < 1730 &&
                                bar.closeHhmmEt >= hardFlattenHHMM_ET && bar.closeHhmmEt < 1730);
      if(inPreBreakFlatten && !hardFlattenedToday)
      {
         hardFlattenedToday = true;
         FlattenAllImmediate(exitBid, exitAsk, bar.closeNy, "HARD_FLATTEN");
      }

      double netDay = realizedSessionUsd + ComputeOpenPnlUsd(bar.close);
      if(accountMode == FS_MODE_EVALUATION && enforceEvalDailyCap && evalDailyCapUsd > 0.0 &&
         netDay >= evalDailyCapUsd && !dailyCapTriggeredToday)
      {
         dailyCapTriggeredToday = true;
         FlattenAllImmediate(exitBid, exitAsk, bar.closeNy, "EVAL_DAILY_CAP");
      }
      if(dailyLossLimitUsd > 0.0 && netDay <= -dailyLossLimitUsd && !dailyLossTriggeredToday)
      {
         dailyLossTriggeredToday = true;
         FlattenAllImmediate(exitBid, exitAsk, bar.closeNy, "DAILY_LOSS_LIMIT");
      }

      newsBlockedNow = IsInNewsBlackout(bar.closeMinEt);
      entriesAllowedNow = (!hardFlattenedToday && !dailyCapTriggeredToday && !dailyLossTriggeredToday &&
                           !inPreBreakFlatten && !newsBlockedNow);

      for(int i = 0; i < 7; i++)
      {
         if(m_sleeves[i].enabled)
            m_engines[i].ProcessBar(bar, atr20Session, m_sleeves[i], GetPointer(this));
      }
   }

   double NormalizeLots(double raw)
   {
      double st = (lotStep > 0.0) ? lotStep : 0.01;
      double sgn = (raw < 0.0) ? -1.0 : 1.0;
      double absR = MathAbs(raw);
      double norm = MathRound(absR / st) * st;
      return sgn * NormalizeDouble(norm, 6);
   }

   void OpenSleeveNow(FsVirtualSleeve &sl, int side, double fillPx, double riskPts, double relMarker, double tgtPx, datetime barNy)
   {
      if(!entriesAllowedNow || sl.isOpen) return;
      if(collisionPolicy == FS_COL_VETO_OPPOSITE)
      {
         double curNet = TargetNetLots();
         if(curNet * side < -1e-9) return;
      }
      double remR = MathMax(0.0, maxOpenR - CurrentOpenRUsed());
      double wEff = MathMin(sl.weightW5, remR);
      if(wEff <= 1e-6) return;

      double tgtUsd = CurrentRisk1RUsd() * wEff;
      double r1PerLot = MathMax(riskPts * usdPerPointPerLot, 1e-9);
      double rawLots = tgtUsd / r1PerLot;
      double lots = MathAbs(NormalizeLots(rawLots));
      if(lots < minLots && rawLots >= 0.55 * minLots)
         lots = minLots;
      if(maxLotsPerSleeve > 0.0 && lots > maxLotsPerSleeve)
         lots = MathAbs(NormalizeLots(maxLotsPerSleeve));
      if(lots < minLots) return;

      sl.isOpen            = true;
      sl.side              = side;
      sl.lots              = lots;
      sl.appliedW          = wEff;
      sl.entryPrice        = fillPx;
      sl.riskPts           = riskPts;
      sl.initialStopPrice  = fillPx - side * riskPts;
      sl.stopPrice         = sl.initialStopPrice;
      sl.targetPrice       = (relMarker != EMPTY_VALUE && MathIsValidNumber(relMarker)) ? (fillPx + side * relMarker) : tgtPx;
      sl.maxFavPts         = 0.0;
      sl.overlayBeActivated= false;
      sl.entryNy           = barNy;
      sl.entrySessionDate  = m_curEthDate;
   }

   void WriteCsvRow(const FsCompletedTrade &r)
   {
      if(!enableCsvLog || StringLen(csvFileName) == 0) return;
      if(m_csvHandle == INVALID_HANDLE)
      {
         m_csvHandle = FileOpen(csvFileName, FILE_WRITE | FILE_TXT | FILE_ANSI);
         if(m_csvHandle == INVALID_HANDLE) return;
         FileWriteString(m_csvHandle, "fecha_int,a5,modulo,w_w5,side,lots,en_ny,ex_ny,entry_price,stop_price,exit_price,riesgo_pts,pnl_pts,R_bruto,R_neto,exit_name\r\n");
         m_csvHeaderWritten = true;
      }
      string line = StringFormat("%d,LIVE,%s,%.6f,%d,%.4f,%s,%s,%.2f,%.4f,%.4f,%.4f,%.2f,%.6f,%.6f,%s\r\n",
         r.sessionDate, r.moduleId, r.weightW5, r.side, r.lots,
         TimeToString(r.entryNy, TIME_DATE | TIME_SECONDS),
         TimeToString(r.exitNy, TIME_DATE | TIME_SECONDS),
         r.entryPrice, r.initialStopPrice, r.exitPrice, r.riskPts, r.pnlPts,
         r.rBruto, r.rNetoMini, r.exitName);
      FileWriteString(m_csvHandle, line);
   }

   void CloseSleeve(FsVirtualSleeve &sl, double exitPx, datetime barNy, string reason)
   {
      if(!sl.isOpen) return;
      double pnlPts = sl.side * (exitPx - sl.entryPrice);
      double rBruto = pnlPts / MathMax(sl.riskPts, 1e-6);
      double rNetMini = (pnlPts - frictionPts) / MathMax(sl.riskPts, 1e-6);
      realizedSessionUsd += (pnlPts - frictionPts) * sl.lots * usdPerPointPerLot;

      if(!warmupOnly)
      {
         int sz = ArraySize(m_completedTrades);
         ArrayResize(m_completedTrades, sz + 1);
         m_completedTrades[sz].sessionDate      = sl.entrySessionDate;
         m_completedTrades[sz].moduleId         = sl.moduleId;
         m_completedTrades[sz].weightW5         = sl.weightW5;
         m_completedTrades[sz].side             = sl.side;
         m_completedTrades[sz].lots             = sl.lots;
         m_completedTrades[sz].entryNy          = sl.entryNy;
         m_completedTrades[sz].exitNy           = barNy;
         m_completedTrades[sz].entryPrice       = sl.entryPrice;
         m_completedTrades[sz].initialStopPrice = sl.initialStopPrice;
         m_completedTrades[sz].exitPrice        = exitPx;
         m_completedTrades[sz].riskPts          = sl.riskPts;
         m_completedTrades[sz].pnlPts           = pnlPts;
         m_completedTrades[sz].rBruto           = rBruto;
         m_completedTrades[sz].rNetoMini        = rNetMini;
         m_completedTrades[sz].exitName         = reason;
         WriteCsvRow(m_completedTrades[sz]);
      }

      sl.isOpen      = false;
      sl.lots        = 0.0;
      sl.appliedW    = 0.0;
      sl.targetPrice = EMPTY_VALUE;
      sl.stopPrice   = EMPTY_VALUE;
   }

   void FlattenAllImmediate(double bidPx, double askPx, datetime barNy, string reason)
   {
      for(int i = 0; i < 7; i++)
      {
         m_sleeves[i].hasPendingEntry = false;
         m_sleeves[i].pendingEntryIsStopOrder = false;
         if(m_sleeves[i].isOpen)
         {
            double exPx = (m_sleeves[i].side > 0) ? bidPx : askPx;
            CloseSleeve(m_sleeves[i], exPx, barNy, reason);
         }
      }
   }

   void ProcessPendingFillsAtBarOpen(const FsBarContext &bar, double bidFill, double askFill, datetime fillNy, bool fillMarketEntries)
   {
      for(int i = 0; i < 7; i++)
      {
         if(StringLen(m_sleeves[i].pendingExitReason) > 0 && m_sleeves[i].isOpen)
         {
            string rsn = m_sleeves[i].pendingExitReason;
            m_sleeves[i].pendingExitReason = "";
            double exPx = (m_sleeves[i].side > 0) ? bidFill : askFill;
            CloseSleeve(m_sleeves[i], exPx, fillNy, rsn);
         }
         else if(m_sleeves[i].hasPendingEntry && !m_sleeves[i].isOpen)
         {
            if(!m_sleeves[i].pendingEntryIsStopOrder && !fillMarketEntries) continue;
            bool trigger = true;
            double fillPx = (m_sleeves[i].pendingEntrySide > 0) ? askFill : bidFill;
            if(m_sleeves[i].pendingEntryIsStopOrder)
            {
               if(bar.high >= m_sleeves[i].pendingEntryStopPrice)
                  fillPx = MathMax(bar.open, m_sleeves[i].pendingEntryStopPrice);
               else
                  trigger = false;
            }
            if(trigger)
            {
               int side = m_sleeves[i].pendingEntrySide;
               double riskPts = m_sleeves[i].pendingStopPts;
               double marker = m_sleeves[i].pendingFixedStopMarker;
               double tgtPx = m_sleeves[i].pendingTargetPrice;
               m_sleeves[i].hasPendingEntry = false;
               m_sleeves[i].pendingEntryIsStopOrder = false;
               OpenSleeveNow(m_sleeves[i], side, fillPx, riskPts, marker, tgtPx, fillNy);
            }
         }
      }
   }

   void ProcessIntrabarStopsAndTargets(const FsBarContext &bar)
   {
      for(int i = 0; i < 7; i++)
      {
         if(!m_sleeves[i].isOpen) continue;
         bool hasStop = (m_sleeves[i].stopPrice != EMPTY_VALUE && MathIsValidNumber(m_sleeves[i].stopPrice));
         bool hasTgt  = (m_sleeves[i].targetPrice != EMPTY_VALUE && MathIsValidNumber(m_sleeves[i].targetPrice));

         if(m_sleeves[i].side > 0)
         {
            if(hasStop && bar.low <= m_sleeves[i].stopPrice)
            {
               CloseSleeve(m_sleeves[i], MathMin(bar.open, m_sleeves[i].stopPrice), bar.closeNy,
                           m_sleeves[i].overlayBeActivated ? "BE_STOP" : "STOP");
               continue;
            }
            if(hasTgt && bar.high >= m_sleeves[i].targetPrice)
            {
               CloseSleeve(m_sleeves[i], MathMax(bar.open, m_sleeves[i].targetPrice), bar.closeNy, "TARGET");
               continue;
            }
            double fav = bar.high - m_sleeves[i].entryPrice;
            if(fav > m_sleeves[i].maxFavPts) m_sleeves[i].maxFavPts = fav;
         }
         else
         {
            if(hasStop && bar.high >= m_sleeves[i].stopPrice)
            {
               CloseSleeve(m_sleeves[i], MathMax(bar.open, m_sleeves[i].stopPrice), bar.closeNy,
                           m_sleeves[i].overlayBeActivated ? "BE_STOP" : "STOP");
               continue;
            }
            if(hasTgt && bar.low <= m_sleeves[i].targetPrice)
            {
               CloseSleeve(m_sleeves[i], MathMin(bar.open, m_sleeves[i].targetPrice), bar.closeNy, "TARGET");
               continue;
            }
            double fav = m_sleeves[i].entryPrice - bar.low;
            if(fav > m_sleeves[i].maxFavPts) m_sleeves[i].maxFavPts = fav;
         }
      }
   }

   double ComputeOpenPnlUsd(double px)
   {
      double tot = 0.0;
      for(int i = 0; i < 7; i++)
         if(m_sleeves[i].isOpen)
            tot += m_sleeves[i].side * (px - m_sleeves[i].entryPrice) * m_sleeves[i].lots * usdPerPointPerLot;
      return tot;
   }

public:
   double                    signalTickSize;
   double                    usdPerPointPerLot;
   double                    lotStep;
   double                    minLots;
   double                    maxLotsPerSleeve;
   double                    maxTotalNetLots;
   double                    frictionPts;

   ENUM_FS_ACCOUNT_MODE      accountMode;
   ENUM_FS_RISK_SIZING_MODE  sizingMode;
   double                    initialBalanceUsd;
   double                    currentBalanceUsd;
   double                    highWaterBalanceUsd;
   double                    evalRiskPct;
   double                    fundedRiskPct;
   double                    evalRisk1R_USD;
   double                    fundedRisk1R_USD;
   double                    maxOpenR;
   ENUM_FS_COLLISION_POLICY  collisionPolicy;

   int                       hardFlattenHHMM_ET;
   bool                      enforceEvalDailyCap;
   double                    evalDailyCapUsd;
   double                    dailyLossLimitUsd;

   bool                      enableFundedDdBrake;
   double                    fundedDdBrakeThresholdPct;
   double                    fundedDdBrakeScale;

   bool                      enableNewsGuard;
   int                       newsBlackoutMin;

   bool                      warmupOnly;
   bool                      enableCsvLog;
   string                    csvFileName;

   bool                      entriesAllowedNow;
   double                    realizedSessionUsd;
   double                    openPnlUsd;
   double                    atr20Session;
   bool                      hardFlattenedToday;
   bool                      dailyCapTriggeredToday;
   bool                      dailyLossTriggeredToday;
   bool                      newsBlockedNow;

   CFundedSyncCoordinator(
      const double &weights[],
      const bool   &enabledFlags[],
      bool enableWTrail = false,
      double rOscMult = 3.0, int rEndEt = 660, double rSlAtr = 0.50,
      int zBucketMin = 15, int zEmaPeriod = 20, double zMinEffPct = 40.0, double zSlAtr = 0.50,
      double tStopOrbMult = 1.0, double tBeTrigR = 1.5,
      double vNoiseMult = 0.25, double vSlAtr = 0.30,
      double wSlAtr = 0.25, int nDays = 5, double nSlAtr = 0.25)
      : signalTickSize(0.25), usdPerPointPerLot(1.0), lotStep(0.01), minLots(0.01),
        maxLotsPerSleeve(50.0), maxTotalNetLots(100.0), frictionPts(1.50),
        accountMode(FS_MODE_EVALUATION), sizingMode(FS_SIZE_PCT_INITIAL),
        initialBalanceUsd(100000.0), currentBalanceUsd(100000.0), highWaterBalanceUsd(100000.0),
        evalRiskPct(0.75), fundedRiskPct(0.75), evalRisk1R_USD(750.0), fundedRisk1R_USD(750.0),
        maxOpenR(3.0), collisionPolicy(FS_COL_NETTING),
        hardFlattenHHMM_ET(1640), enforceEvalDailyCap(false), evalDailyCapUsd(0.0), dailyLossLimitUsd(3800.0),
        enableFundedDdBrake(false), fundedDdBrakeThresholdPct(5.0), fundedDdBrakeScale(0.50),
        enableNewsGuard(false), newsBlackoutMin(2),
        warmupOnly(false), enableCsvLog(false), csvFileName(""),
        entriesAllowedNow(true), realizedSessionUsd(0.0), openPnlUsd(0.0), atr20Session(EMPTY_VALUE),
        hardFlattenedToday(false), dailyCapTriggeredToday(false), dailyLossTriggeredToday(false), newsBlockedNow(false),
        m_curEthDate(-1), m_curSesHi(-1e18), m_curSesLo(1e18), m_curSesClose(EMPTY_VALUE),
        m_hadTickStopEval(false), m_csvHeaderWritten(false), m_csvHandle(INVALID_HANDLE)
   {
      m_engines[0] = new CAtrPhaseEngine(rOscMult, rEndEt, rSlAtr);
      m_engines[1] = new CZetaEngine(zBucketMin, zEmaPeriod, zMinEffPct, zSlAtr);
      m_engines[2] = new CFtmOrbEngine(tStopOrbMult, tBeTrigR);
      m_engines[3] = new CVaultBreakEngine(vNoiseMult, vSlAtr);
      m_engines[4] = new CVwapCrossEngine(wSlAtr, enableWTrail);
      m_engines[5] = new CNDayLongEngine(nDays, nSlAtr);
      m_engines[6] = new CSessionOpenMomentumEngine();

      for(int i = 0; i < 7; i++)
      {
         m_sleeves[i].idx                    = i;
         m_sleeves[i].moduleId               = FsModuleName(i);
         m_sleeves[i].weightW5               = weights[i];
         m_sleeves[i].enabled                = enabledFlags[i] && weights[i] > 1e-6;
         m_sleeves[i].isOpen                 = false;
         m_sleeves[i].side                   = 0;
         m_sleeves[i].lots                   = 0.0;
         m_sleeves[i].appliedW               = 0.0;
         m_sleeves[i].entryPrice             = 0.0;
         m_sleeves[i].initialStopPrice       = 0.0;
         m_sleeves[i].stopPrice              = EMPTY_VALUE;
         m_sleeves[i].targetPrice            = EMPTY_VALUE;
         m_sleeves[i].riskPts                = 0.0;
         m_sleeves[i].maxFavPts              = 0.0;
         m_sleeves[i].overlayBeActivated     = false;
         m_sleeves[i].entryNy                = 0;
         m_sleeves[i].entrySessionDate       = 0;
         m_sleeves[i].hasPendingEntry        = false;
         m_sleeves[i].pendingEntrySide       = 0;
         m_sleeves[i].pendingStopPts         = 0.0;
         m_sleeves[i].pendingFixedStopMarker = EMPTY_VALUE;
         m_sleeves[i].pendingTargetPrice     = EMPTY_VALUE;
         m_sleeves[i].pendingEntryIsStopOrder= false;
         m_sleeves[i].pendingEntryStopPrice  = 0.0;
         m_sleeves[i].pendingExitReason      = "";
      }
   }

   ~CFundedSyncCoordinator()
   {
      if(m_csvHandle != INVALID_HANDLE)
      {
         FileClose(m_csvHandle);
         m_csvHandle = INVALID_HANDLE;
      }
      for(int i = 0; i < 7; i++)
      {
         if(CheckPointer(m_engines[i]) == POINTER_DYNAMIC)
            delete m_engines[i];
      }
   }

   void SetNewsBlackoutCsv(string csv) { FsParseBlackoutMinutesCsv(csv, m_newsMinutesEt); }

   double CurrentRisk1RUsd()
   {
      double baseUsd = 0.0;
      if(sizingMode == FS_SIZE_FIXED_USD)
         baseUsd = (accountMode == FS_MODE_EVALUATION) ? evalRisk1R_USD : fundedRisk1R_USD;
      else
      {
         double bal = (sizingMode == FS_SIZE_PCT_INITIAL) ? MathMax(initialBalanceUsd, 1.0) : MathMax(currentBalanceUsd, 1.0);
         double pct = (accountMode == FS_MODE_EVALUATION) ? evalRiskPct : fundedRiskPct;
         baseUsd = bal * (pct / 100.0);
      }

      if(accountMode == FS_MODE_FUNDED && enableFundedDdBrake && highWaterBalanceUsd > 0.0)
      {
         double ddPct = 100.0 * MathMax(0.0, highWaterBalanceUsd - currentBalanceUsd) / highWaterBalanceUsd;
         if(ddPct >= fundedDdBrakeThresholdPct && fundedDdBrakeScale > 0.0 && fundedDdBrakeScale < 1.0)
            baseUsd *= fundedDdBrakeScale;
      }
      return MathMax(baseUsd, 0.0);
   }

   int KnnTrainRowsCount()
   {
      CFtmOrbEngine *t = dynamic_cast<CFtmOrbEngine *>(m_engines[2]);
      return (t != NULL) ? t.KnnTrainRowsCount() : 0;
   }

   int VaultDaysCount()
   {
      CVaultBreakEngine *v = dynamic_cast<CVaultBreakEngine *>(m_engines[3]);
      return (v != NULL) ? v.RthRangesCount() : 0;
   }

   double TargetNetLots()
   {
      if(hardFlattenedToday || dailyCapTriggeredToday || dailyLossTriggeredToday) return 0.0;
      double net = 0.0;
      for(int i = 0; i < 7; i++)
         if(m_sleeves[i].isOpen) net += m_sleeves[i].side * m_sleeves[i].lots;
      if(maxTotalNetLots > 0.0)
      {
         if(net > maxTotalNetLots) net = maxTotalNetLots;
         else if(net < -maxTotalNetLots) net = -maxTotalNetLots;
      }
      return (MathAbs(net) < 0.5 * minLots) ? 0.0 : NormalizeLots(net);
   }

   double CurrentOpenRUsed()
   {
      double u = 0.0;
      for(int i = 0; i < 7; i++)
         if(m_sleeves[i].isOpen) u += m_sleeves[i].appliedW;
      return u;
   }

   double GetProtectiveNetStopPrice()
   {
      double tgt = TargetNetLots();
      int netSide = (tgt > 1e-9) ? 1 : ((tgt < -1e-9) ? -1 : 0);
      if(netSide == 0) return EMPTY_VALUE;

      double bestStop = EMPTY_VALUE;
      for(int i = 0; i < 7; i++)
      {
         if(!m_sleeves[i].isOpen || m_sleeves[i].side != netSide) continue;
         if(m_sleeves[i].stopPrice == EMPTY_VALUE || !MathIsValidNumber(m_sleeves[i].stopPrice)) continue;
         if(bestStop == EMPTY_VALUE) bestStop = m_sleeves[i].stopPrice;
         else if(netSide > 0) bestStop = MathMin(bestStop, m_sleeves[i].stopPrice);
         else bestStop = MathMax(bestStop, m_sleeves[i].stopPrice);
      }
      return bestStop;
   }

   void FlattenAllVirtualAtEndOfWarmup()
   {
      for(int i = 0; i < 7; i++)
      {
         m_sleeves[i].hasPendingEntry = false;
         m_sleeves[i].pendingEntryIsStopOrder = false;
         m_sleeves[i].pendingExitReason = "";
         m_sleeves[i].isOpen = false;
         m_sleeves[i].lots = 0.0;
         m_sleeves[i].appliedW = 0.0;
         m_sleeves[i].stopPrice = EMPTY_VALUE;
         m_sleeves[i].targetPrice = EMPTY_VALUE;
      }
      realizedSessionUsd = 0.0;
      openPnlUsd = 0.0;
      ArrayResize(m_completedTrades, 0);
      m_hadTickStopEval = false;
   }

   void FeedHistoricalBar(const FsBarContext &bar)
   {
      EnsureSessionTransition(bar);
      ProcessPendingFillsAtBarOpen(bar, bar.open, bar.open, bar.closeNy, true);
      ProcessIntrabarStopsAndTargets(bar);

      for(int i = 0; i < 7; i++)
         if(m_sleeves[i].isOpen) m_engines[i].UpdateM1OverlayProtectionsOnClose(m_sleeves[i], bar);

      RunComplianceAndEngines(bar, bar.close, bar.close);
      m_hadTickStopEval = false;
   }

   void FeedClosedBarAndFillAtNextOpen(
      const FsBarContext &closedBar,
      double nextOpenBid,
      double nextOpenAsk,
      datetime nextOpenNy)
   {
      EnsureSessionTransition(closedBar);

      if(!m_hadTickStopEval)
      {
         ProcessPendingFillsAtBarOpen(closedBar, closedBar.open, closedBar.open, closedBar.closeNy, true);
         ProcessIntrabarStopsAndTargets(closedBar);
      }
      else
      {
         ProcessPendingFillsAtBarOpen(closedBar, closedBar.open, closedBar.open, closedBar.closeNy, false);
      }
      m_hadTickStopEval = false;

      for(int i = 0; i < 7; i++)
         if(m_sleeves[i].isOpen) m_engines[i].UpdateM1OverlayProtectionsOnClose(m_sleeves[i], closedBar);

      RunComplianceAndEngines(closedBar, nextOpenBid, nextOpenAsk);
      ProcessPendingFillsAtBarOpen(closedBar, nextOpenBid, nextOpenAsk, nextOpenNy, true);
      openPnlUsd = ComputeOpenPnlUsd((nextOpenBid + nextOpenAsk) * 0.5);
   }

   bool EvaluateTick(double bid, double ask, datetime utcNow)
   {
      m_hadTickStopEval = true;
      int etOff = FsIsUsDstUtc(utcNow) ? (-4 * 3600) : (-5 * 3600);
      datetime nyNow = utcNow + etOff;
      bool changed = false;

      for(int i = 0; i < 7; i++)
      {
         if(m_sleeves[i].hasPendingEntry && m_sleeves[i].pendingEntryIsStopOrder && !m_sleeves[i].isOpen && entriesAllowedNow)
         {
            if(ask >= m_sleeves[i].pendingEntryStopPrice)
            {
               int side = m_sleeves[i].pendingEntrySide;
               double riskPts = m_sleeves[i].pendingStopPts;
               double marker = m_sleeves[i].pendingFixedStopMarker;
               double tgtPx = m_sleeves[i].pendingTargetPrice;
               m_sleeves[i].hasPendingEntry = false;
               m_sleeves[i].pendingEntryIsStopOrder = false;
               OpenSleeveNow(m_sleeves[i], side, ask, riskPts, marker, tgtPx, nyNow);
               changed = true;
            }
            continue;
         }

         if(!m_sleeves[i].isOpen) continue;
         bool hasStop = (m_sleeves[i].stopPrice != EMPTY_VALUE && MathIsValidNumber(m_sleeves[i].stopPrice));
         bool hasTgt  = (m_sleeves[i].targetPrice != EMPTY_VALUE && MathIsValidNumber(m_sleeves[i].targetPrice));

         if(m_sleeves[i].side > 0)
         {
            if(hasStop && bid <= m_sleeves[i].stopPrice)
            {
               CloseSleeve(m_sleeves[i], bid, nyNow, m_sleeves[i].overlayBeActivated ? "BE_STOP" : "STOP");
               changed = true; continue;
            }
            if(hasTgt && bid >= m_sleeves[i].targetPrice)
            {
               CloseSleeve(m_sleeves[i], bid, nyNow, "TARGET");
               changed = true; continue;
            }
            double fav = bid - m_sleeves[i].entryPrice;
            if(fav > m_sleeves[i].maxFavPts) m_sleeves[i].maxFavPts = fav;
         }
         else
         {
            if(hasStop && ask >= m_sleeves[i].stopPrice)
            {
               CloseSleeve(m_sleeves[i], ask, nyNow, m_sleeves[i].overlayBeActivated ? "BE_STOP" : "STOP");
               changed = true; continue;
            }
            if(hasTgt && ask <= m_sleeves[i].targetPrice)
            {
               CloseSleeve(m_sleeves[i], ask, nyNow, "TARGET");
               changed = true; continue;
            }
            double fav = m_sleeves[i].entryPrice - ask;
            if(fav > m_sleeves[i].maxFavPts) m_sleeves[i].maxFavPts = fav;
         }
      }

      if(dailyLossLimitUsd > 0.0 && !dailyLossTriggeredToday)
      {
         double mid = (bid + ask) * 0.5;
         double netDay = realizedSessionUsd + ComputeOpenPnlUsd(mid);
         if(netDay <= -dailyLossLimitUsd)
         {
            dailyLossTriggeredToday = true;
            FlattenAllImmediate(bid, ask, nyNow, "DAILY_LOSS_LIMIT");
            entriesAllowedNow = false;
            changed = true;
         }
      }

      return changed;
   }

   virtual bool QueueMarketEntry(FsVirtualSleeve &sl, int side, double riskPts, double fixedTargetPx, double targetDistPts) override
   {
      if(!sl.enabled || !entriesAllowedNow || sl.isOpen || sl.hasPendingEntry || !(riskPts > 0.0)) return false;
      sl.hasPendingEntry          = true;
      sl.pendingEntryIsStopOrder  = false;
      sl.pendingEntrySide         = side;
      sl.pendingStopPts           = riskPts;
      sl.pendingFixedStopMarker   = (targetDistPts != EMPTY_VALUE && MathIsValidNumber(targetDistPts)) ? targetDistPts : EMPTY_VALUE;
      sl.pendingTargetPrice       = (targetDistPts != EMPTY_VALUE && MathIsValidNumber(targetDistPts)) ? (side * targetDistPts) : fixedTargetPx;
      return true;
   }

   virtual bool QueueStopEntry(FsVirtualSleeve &sl, int side, double triggerStopPx, double riskPts) override
   {
      if(!sl.enabled || !entriesAllowedNow || sl.isOpen || sl.hasPendingEntry || !(riskPts > 0.0)) return false;
      sl.hasPendingEntry          = true;
      sl.pendingEntryIsStopOrder  = true;
      sl.pendingEntryStopPrice    = triggerStopPx;
      sl.pendingEntrySide         = side;
      sl.pendingStopPts           = riskPts;
      sl.pendingFixedStopMarker   = EMPTY_VALUE;
      sl.pendingTargetPrice       = EMPTY_VALUE;
      return true;
   }

   virtual void QueueMarketExit(FsVirtualSleeve &sl, string reason) override
   {
      if(sl.isOpen && StringLen(sl.pendingExitReason) == 0)
         sl.pendingExitReason = reason;
   }

   string BuildHudText(string label)
   {
      double atrShow = (atr20Session != EMPTY_VALUE && MathIsValidNumber(atr20Session)) ? atr20Session : 0.0;
      return StringFormat("%s | %s 1R=$%.0f | Net=%.2f lots | OpenR=%.2f/%.1f | DayUSD=$%+.0f | ATR20=%.1f%s",
         label,
         (accountMode == FS_MODE_EVALUATION) ? "EVAL" : "FUND",
         CurrentRisk1RUsd(),
         TargetNetLots(),
         CurrentOpenRUsed(),
         maxOpenR,
         realizedSessionUsd + openPnlUsd,
         atrShow,
         newsBlockedNow ? " | NEWS_HOLD" : "");
   }
};

// ---------------------------------------------------------------------------
// MT5 Adapter (History Warmup, Hedging/Netting Reconciler, Emergency SL, OnTester)
// ---------------------------------------------------------------------------
class CFundedSyncMt5Adapter
{
private:
   CTrade                 m_trade;
   CFundedSyncCoordinator *m_coord;
   string                 m_label;
   ulong                  m_magic;
   ENUM_FS_TZ_MODE        m_tzMode;
   double                 m_fixedUtcOffsetHours;
   bool                   m_checkStopsOnTick;
   bool                   m_useBrokerProtectiveStop;
   datetime               m_lastFedBarOpenSec;
   datetime               m_lastBar0Sec;
   bool                   m_initialized;

   void ConfigureTradeFilling()
   {
      m_trade.SetExpertMagicNumber(m_magic);
      m_trade.SetDeviationInPoints(50);
      long filling = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
      if((filling & SYMBOL_FILLING_FOK) != 0)
         m_trade.SetTypeFilling(ORDER_FILLING_FOK);
      else if((filling & SYMBOL_FILLING_IOC) != 0)
         m_trade.SetTypeFilling(ORDER_FILLING_IOC);
      else
         m_trade.SetTypeFilling(ORDER_FILLING_RETURN);
   }

   double ResolveUsdPerPointPerLot(double overrideVal)
   {
      if(overrideVal > 0.0) return overrideVal;
      double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      if(tickVal <= 0.0) tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tickSize > 0.0 && tickVal > 0.0)
         return tickVal / tickSize;
      double cSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
      return (cSize > 0.0) ? cSize : 1.0;
   }

   double NormalizeVolumeLots(double vol)
   {
      double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      if(step <= 0.0) step = 0.01;
      if(minLot <= 0.0) minLot = 0.01;
      if(maxLot <= 0.0) maxLot = 100.0;
      double norm = MathRound(vol / step) * step;
      if(norm < minLot) return 0.0;
      if(norm > maxLot) norm = maxLot;
      return NormalizeDouble(norm, 2);
   }

   void ClosePositionsOnSide(ENUM_POSITION_TYPE targetSide, double volToClose)
   {
      double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if(minLot <= 0.0) minLot = 0.01;
      if(step <= 0.0) step = 0.01;
      double rem = volToClose;

      for(int i = PositionsTotal() - 1; i >= 0 && rem >= minLot * 0.5; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if((ulong)PositionGetInteger(POSITION_MAGIC) != m_magic) continue;
         if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) != targetSide) continue;

         double pVol = PositionGetDouble(POSITION_VOLUME);
         if(rem >= pVol - minLot * 0.5)
         {
            m_trade.PositionClose(ticket);
            rem -= pVol;
         }
         else
         {
            double part = MathFloor(rem / step) * step;
            part = NormalizeDouble(part, 2);
            if(part >= minLot)
            {
               if(pVol - part < minLot) m_trade.PositionClose(ticket);
               else m_trade.PositionClosePartial(ticket, part);
            }
            rem = 0.0;
         }
      }
   }

   void ReconcileNetPosition()
   {
      double targetNet = (m_coord.hardFlattenedToday || m_coord.dailyCapTriggeredToday || m_coord.dailyLossTriggeredToday)
         ? 0.0 : m_coord.TargetNetLots();
      double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if(minLot <= 0.0) minLot = 0.01;
      if(step <= 0.0) step = 0.01;

      if(MathAbs(targetNet) < minLot * 0.5) targetNet = 0.0;
      else targetNet = (targetNet >= 0.0) ? NormalizeVolumeLots(targetNet) : -NormalizeVolumeLots(-targetNet);

      double buyLots = 0.0, sellLots = 0.0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if((ulong)PositionGetInteger(POSITION_MAGIC) != m_magic) continue;
         ENUM_POSITION_TYPE pType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double pVol = PositionGetDouble(POSITION_VOLUME);
         if(pType == POSITION_TYPE_BUY) buyLots += pVol;
         else if(pType == POSITION_TYPE_SELL) sellLots += pVol;
      }

      if(targetNet <= 0.0 && buyLots > 0.0)
      {
         ClosePositionsOnSide(POSITION_TYPE_BUY, buyLots);
         buyLots = 0.0;
      }
      if(targetNet >= 0.0 && sellLots > 0.0)
      {
         ClosePositionsOnSide(POSITION_TYPE_SELL, sellLots);
         sellLots = 0.0;
      }

      double curNet = buyLots - sellLots;
      double delta = targetNet - curNet;

      if(MathAbs(delta) >= MathMin(step, minLot) * 0.5)
      {
         if(targetNet == 0.0)
         {
            if(buyLots > 0.0) ClosePositionsOnSide(POSITION_TYPE_BUY, buyLots);
            if(sellLots > 0.0) ClosePositionsOnSide(POSITION_TYPE_SELL, sellLots);
         }
         else if(delta > 0.0)
         {
            if(sellLots > 0.0)
            {
               ClosePositionsOnSide(POSITION_TYPE_SELL, MathMin(sellLots, delta));
            }
            else
            {
               double addL = NormalizeVolumeLots(delta);
               if(addL >= minLot)
                  m_trade.Buy(addL, _Symbol, 0.0, 0.0, 0.0, m_label);
            }
         }
         else
         {
            if(buyLots > 0.0)
            {
               ClosePositionsOnSide(POSITION_TYPE_BUY, MathMin(buyLots, -delta));
            }
            else
            {
               double addL = NormalizeVolumeLots(-delta);
               if(addL >= minLot)
                  m_trade.Sell(addL, _Symbol, 0.0, 0.0, 0.0, m_label);
            }
         }
      }

      if(m_useBrokerProtectiveStop && MathAbs(targetNet) >= minLot)
         SyncBrokerProtectiveStop();
   }

   void SyncBrokerProtectiveStop()
   {
      double rawStop = m_coord.GetProtectiveNetStopPrice();
      if(rawStop == EMPTY_VALUE || !MathIsValidNumber(rawStop)) return;

      double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double tickSz = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tickSz <= 0.0) tickSz = pt;
      double slPx = NormalizeDouble(FsRoundTick(rawStop, tickSz), _Digits);
      long stopLvlPts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
      double minDist = (double)stopLvlPts * pt + 2.0 * tickSz;

      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if((ulong)PositionGetInteger(POSITION_MAGIC) != m_magic) continue;
         ENUM_POSITION_TYPE pType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double curSL = PositionGetDouble(POSITION_SL);
         double curTP = PositionGetDouble(POSITION_TP);
         bool distOk = (pType == POSITION_TYPE_BUY) ? (bid - slPx > minDist) : (slPx - ask > minDist);
         if(!distOk) continue;
         if(curSL == 0.0 || MathAbs(curSL - slPx) > tickSz * 2.0)
            m_trade.PositionModify(ticket, slPx, curTP);
      }
   }

   void ProcessClosedBars()
   {
      datetime bar1Time = iTime(_Symbol, PERIOD_M1, 1);
      if(bar1Time <= 0 || bar1Time <= m_lastFedBarOpenSec) return;

      m_coord.currentBalanceUsd = AccountInfoDouble(ACCOUNT_BALANCE);
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(eq > m_coord.highWaterBalanceUsd) m_coord.highWaterBalanceUsd = eq;

      int totalAvail = iBars(_Symbol, PERIOD_M1);
      if(totalAvail < 2) return;

      // Find up to 2000 latest bars starting after m_lastFedBarOpenSec
      int fetchCnt = (m_lastFedBarOpenSec == 0) ? totalAvail : (int)MathMin((double)totalAvail, 2000.0);
      MqlRates rates[];
      ArraySetAsSeries(rates, false);
      int copied = CopyRates(_Symbol, PERIOD_M1, 0, fetchCnt, rates);
      if(copied < 2) return;

      bool anyFed = false;
      int limit = copied - 1; // index copied-1 is currently forming bar 0
      for(int i = 0; i < limit; i++)
      {
         if(rates[i].time <= m_lastFedBarOpenSec) continue;

         datetime openUtc  = FsServerTimeToUtc(rates[i].time, m_tzMode, m_fixedUtcOffsetHours);
         datetime closeUtc = openUtc + 60;
         double vol = (rates[i].real_volume > 0) ? (double)rates[i].real_volume
                                                 : ((rates[i].tick_volume > 0) ? (double)rates[i].tick_volume : 1.0);
         FsBarContext ctx;
         FsBuildBarContext(closeUtc, rates[i].open, rates[i].high, rates[i].low, rates[i].close, vol, ctx);

         bool isNewestClosed = (i == limit - 1);
         double nextBid = isNewestClosed ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : rates[i + 1].open;
         double nextAsk = isNewestClosed ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : rates[i + 1].open;
         datetime nextOpenUtc = FsServerTimeToUtc(rates[i + 1].time, m_tzMode, m_fixedUtcOffsetHours);
         int nextEtOff = FsIsUsDstUtc(nextOpenUtc) ? (-4 * 3600) : (-5 * 3600);
         datetime nextOpenNy = nextOpenUtc + nextEtOff;

         m_coord.FeedClosedBarAndFillAtNextOpen(ctx, nextBid, nextAsk, nextOpenNy);
         m_lastFedBarOpenSec = rates[i].time;
         anyFed = true;
      }

      if(anyFed)
      {
         ReconcileNetPosition();
         RenderHud();
      }
   }

   void RenderHud()
   {
      if(MQLInfoInteger(MQL_OPTIMIZATION)) return;
      Comment(m_coord.BuildHudText(m_label));
   }

public:
   CFundedSyncMt5Adapter() : m_coord(NULL), m_magic(910001), m_tzMode(FS_TZ_NY_PLUS_7_ALL_YEAR),
      m_fixedUtcOffsetHours(2.0), m_checkStopsOnTick(true), m_useBrokerProtectiveStop(true),
      m_lastFedBarOpenSec(0), m_lastBar0Sec(0), m_initialized(false) {}

   ~CFundedSyncMt5Adapter()
   {
      if(CheckPointer(m_coord) == POINTER_DYNAMIC)
      {
         delete m_coord;
         m_coord = NULL;
      }
   }

   int InitFromPreset(
      string label,
      ulong magic,
      ENUM_FS_PORTFOLIO_PRESET preset,
      ENUM_FS_PROP_PROFILE propProfile,
      ENUM_FS_ACCOUNT_MODE accountMode,
      ENUM_FS_RISK_SIZING_MODE customSizingMode,
      double evalRiskPct,
      double fundedRiskPct,
      double evalRiskUsd,
      double fundedRiskUsd,
      double maxOpenR,
      double maxLotsPerSleeve,
      double maxTotalNetLots,
      ENUM_FS_COLLISION_POLICY collisionPolicy,
      int hardFlattenHhmmEt,
      bool enforceEvalDailyCap,
      double evalDailyCapPct,
      double dailyLossLimitPct,
      bool enableFundedDdBrake,
      double fundedDdBrakeThresholdPct,
      double fundedDdBrakeScale,
      bool enableNewsGuard,
      int newsBlackoutMinutes,
      string newsHoursEtCsv,
      ENUM_FS_TZ_MODE tzMode,
      double fixedUtcOffsetHours,
      double overrideUsdPerPtPerLot,
      double frictionPts,
      double signalTickSize,
      bool checkStopsOnTick,
      bool useBrokerProtectiveStop,
      int warmupTargetBars,
      bool allowMidSessionSyncOnStart,
      bool enableWTrail,
      bool enableCsvLog,
      string csvFileName,
      const bool &enableOverrides[],
      const double &weightOverrides[],
      bool useOverrides,
      double rOscMult = 3.0, int rEndEt = 660, double rSlAtr = 0.50,
      int zBucketMin = 15, int zEmaPeriod = 20, double zMinEffPct = 40.0, double zSlAtr = 0.50,
      double tStopOrbMult = 1.0, double tBeTrigR = 1.5,
      double vNoiseMult = 0.25, double vSlAtr = 0.30,
      double wSlAtr = 0.25, int nDays = 5, double nSlAtr = 0.25)
   {
      m_label                   = label;
      m_magic                   = magic;
      m_tzMode                  = tzMode;
      m_fixedUtcOffsetHours     = fixedUtcOffsetHours;
      m_checkStopsOnTick        = checkStopsOnTick;
      m_useBrokerProtectiveStop = useBrokerProtectiveStop;

      if(_Period != PERIOD_M1)
         PrintFormat("[%s] Chart TF is %s; reading PERIOD_M1 series directly.", label, EnumToString(_Period));

      ConfigureTradeFilling();

      double w[];
      bool flags[7];
      if(preset == FS_PRESET_CUSTOM_WEIGHTS)
      {
         ArrayResize(w, 7);
         for(int i = 0; i < 7; i++)
         {
            w[i] = useOverrides ? weightOverrides[i] : 0.0;
            bool en = !useOverrides || enableOverrides[i];
            flags[i] = en && w[i] > 1e-6;
         }
      }
      else
      {
         FsGetPresetWeights(preset, w);
         for(int i = 0; i < 7; i++)
         {
            bool en = !useOverrides || enableOverrides[i];
            flags[i] = en && w[i] > 1e-6;
         }
      }

      FsPropDefaults prof;
      FsGetPropProfileDefaults(propProfile, prof);
      bool useProf = (propProfile != FS_PROP_PERSONAL_CUSTOM);

      double initBal = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), 1.0);
      double maxOpenREff  = useProf ? prof.maxOpenR : maxOpenR;
      double dlPctEff     = useProf ? prof.dailyLossLimitPct : dailyLossLimitPct;
      double evCapPctEff  = useProf ? prof.evalDailyCapPct : evalDailyCapPct;
      bool   enfCapEff    = useProf ? prof.enforceEvalDailyCap : enforceEvalDailyCap;

      m_coord = new CFundedSyncCoordinator(
         w, flags, enableWTrail,
         rOscMult, rEndEt, rSlAtr,
         zBucketMin, zEmaPeriod, zMinEffPct, zSlAtr,
         tStopOrbMult, tBeTrigR,
         vNoiseMult, vSlAtr,
         wSlAtr, nDays, nSlAtr);

      m_coord.signalTickSize            = (signalTickSize > 0.0) ? signalTickSize : 0.25;
      m_coord.usdPerPointPerLot         = ResolveUsdPerPointPerLot(overrideUsdPerPtPerLot);
      m_coord.lotStep                   = (SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP) > 0.0) ? SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP) : 0.01;
      m_coord.minLots                   = (SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) > 0.0)  ? SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)  : 0.01;
      double symMaxLot                  = (SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX) > 0.0)  ? SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX)  : 100.0;
      m_coord.maxLotsPerSleeve          = (maxLotsPerSleeve > 0.0) ? MathMin(maxLotsPerSleeve, symMaxLot) : symMaxLot;
      m_coord.maxTotalNetLots           = (maxTotalNetLots > 0.0)  ? MathMin(maxTotalNetLots, symMaxLot)  : symMaxLot;
      m_coord.frictionPts               = (frictionPts >= 0.0) ? frictionPts : 1.50;

      m_coord.accountMode               = accountMode;
      m_coord.sizingMode                = useProf ? prof.sizingMode : customSizingMode;
      m_coord.initialBalanceUsd         = initBal;
      m_coord.currentBalanceUsd         = initBal;
      m_coord.highWaterBalanceUsd       = initBal;
      m_coord.evalRiskPct               = useProf ? prof.evalRiskPct : evalRiskPct;
      m_coord.fundedRiskPct             = useProf ? prof.fundedRiskPct : fundedRiskPct;
      m_coord.evalRisk1R_USD            = useProf ? prof.evalRiskUsd : evalRiskUsd;
      m_coord.fundedRisk1R_USD          = useProf ? prof.fundedRiskUsd : fundedRiskUsd;
      m_coord.maxOpenR                  = maxOpenREff;
      m_coord.collisionPolicy           = useProf ? prof.collisionPolicy : collisionPolicy;

      m_coord.hardFlattenHHMM_ET        = useProf ? prof.hardFlattenHHMM_ET : hardFlattenHhmmEt;
      m_coord.enforceEvalDailyCap       = enfCapEff;
      m_coord.evalDailyCapUsd           = (enfCapEff && evCapPctEff > 0.0) ? initBal * (evCapPctEff / 100.0) : 0.0;
      m_coord.dailyLossLimitUsd         = (dlPctEff > 0.0) ? initBal * (dlPctEff / 100.0) : 0.0;

      m_coord.enableFundedDdBrake       = useProf ? prof.enableFundedDdBrake : enableFundedDdBrake;
      m_coord.fundedDdBrakeThresholdPct = useProf ? prof.fundedDdBrakeThreshPct : fundedDdBrakeThresholdPct;
      m_coord.fundedDdBrakeScale        = useProf ? prof.fundedDdBrakeScale : fundedDdBrakeScale;

      m_coord.enableNewsGuard           = useProf ? prof.enableNewsGuard : enableNewsGuard;
      m_coord.newsBlackoutMin           = useProf ? prof.newsBlackoutMin : newsBlackoutMinutes;
      m_coord.SetNewsBlackoutCsv(newsHoursEtCsv);

      m_coord.enableCsvLog              = enableCsvLog && !MQLInfoInteger(MQL_OPTIMIZATION);
      m_coord.csvFileName               = csvFileName;

      // Historical M1 warmup
      m_coord.warmupOnly = true;
      int availClosed = MathMax(0, iBars(_Symbol, PERIOD_M1) - 1);
      int req = (warmupTargetBars > 0) ? (int)MathMin((double)warmupTargetBars, (double)availClosed) : availClosed;
      int fed = 0;
      if(req > 0)
      {
         MqlRates hist[];
         ArraySetAsSeries(hist, false);
         int copied = CopyRates(_Symbol, PERIOD_M1, 1, req, hist);
         if(copied > 0)
         {
            for(int i = 0; i < copied; i++)
            {
               datetime openUtc  = FsServerTimeToUtc(hist[i].time, m_tzMode, m_fixedUtcOffsetHours);
               datetime closeUtc = openUtc + 60;
               double vol = (hist[i].real_volume > 0) ? (double)hist[i].real_volume
                                                      : ((hist[i].tick_volume > 0) ? (double)hist[i].tick_volume : 1.0);
               FsBarContext ctx;
               FsBuildBarContext(closeUtc, hist[i].open, hist[i].high, hist[i].low, hist[i].close, vol, ctx);
               m_coord.FeedHistoricalBar(ctx);
               m_lastFedBarOpenSec = hist[i].time;
               fed++;
            }
         }
      }
      m_coord.warmupOnly = false;

      if(!allowMidSessionSyncOnStart && fed > 0)
         m_coord.FlattenAllVirtualAtEndOfWarmup();

      m_lastBar0Sec = iTime(_Symbol, PERIOD_M1, 0);
      m_initialized = true;

      PrintFormat("[%s] Warmup done: M1Bars=%d (Avail=%d), ATR20=%.1f, T_KnnRows=%d, V_Days=%d, UsdPerPtPerLot=%.4f",
         m_label, fed, availClosed,
         (m_coord.atr20Session != EMPTY_VALUE && MathIsValidNumber(m_coord.atr20Session)) ? m_coord.atr20Session : 0.0,
         m_coord.KnnTrainRowsCount(), m_coord.VaultDaysCount(), m_coord.usdPerPointPerLot);

      return INIT_SUCCEEDED;
   }

   void OnTick()
   {
      if(!m_initialized || m_coord == NULL) return;

      datetime bar0 = iTime(_Symbol, PERIOD_M1, 0);
      datetime bar1 = iTime(_Symbol, PERIOD_M1, 1);
      if(bar0 != m_lastBar0Sec || (bar1 > 0 && bar1 > m_lastFedBarOpenSec))
      {
         m_lastBar0Sec = bar0;
         ProcessClosedBars();
      }

      if(m_checkStopsOnTick)
      {
         datetime srvNow = TimeCurrent();
         datetime utcNow = FsServerTimeToUtc(srvNow, m_tzMode, m_fixedUtcOffsetHours);
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(m_coord.EvaluateTick(bid, ask, utcNow))
         {
            ReconcileNetPosition();
            RenderHud();
         }
      }
   }

   double OnTesterScore()
   {
      double prof   = TesterStatistics(STAT_PROFIT);
      double dd     = TesterStatistics(STAT_EQUITY_DD);
      double trades = TesterStatistics(STAT_TRADES);
      if(trades < 10.0) return -1e9;
      double oneR = (m_coord != NULL) ? MathMax(m_coord.CurrentRisk1RUsd(), 1.0) : 500.0;
      return prof / MathMax(dd, oneR);
   }
};

#endif
//+------------------------------------------------------------------+
