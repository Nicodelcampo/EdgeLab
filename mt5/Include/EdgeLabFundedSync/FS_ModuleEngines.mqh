//+------------------------------------------------------------------+
//|                                             FS_ModuleEngines.mqh |
//|   Exact 1:1 Causal Implementations of All 7 FUNDEDSYNC Modules   |
//+------------------------------------------------------------------+
#ifndef FS_MODULE_ENGINES_MQH
#define FS_MODULE_ENGINES_MQH

#property strict

#include "FS_TypesAndTime.mqh"

interface IFsSignalHost
{
   bool QueueMarketEntry(FsVirtualSleeve &sl, int side, double riskPts, double fixedTargetPx, double targetDistPts);
   bool QueueStopEntry(FsVirtualSleeve &sl, int side, double triggerStopPx, double riskPts);
   void QueueMarketExit(FsVirtualSleeve &sl, string reason);
};

class CFsModuleEngineBase
{
public:
   string moduleId;
   double tickSize;

   CFsModuleEngineBase(string id) : moduleId(id), tickSize(0.25) {}
   virtual ~CFsModuleEngineBase() {}

   virtual void UpdateM1OverlayProtectionsOnClose(FsVirtualSleeve &sl, const FsBarContext &bar) {}
   virtual void OnNewEthSession(int completedEthDate, double completedHigh, double completedLow, double completedClose, int newEthDate) {}
   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) = 0;
};

// ---------------------------------------------------------------------------
// Module R: AtrPhase (10m ETH resampled from M1)
// ---------------------------------------------------------------------------
class CAtrPhaseEngine : public CFsModuleEngineBase
{
private:
   double m_oscAtrMult;
   int    m_entryEndMinEt;
   double m_slAtrK;
   double m_emaAlpha;

   bool   m_hasBucket;
   int    m_bucketDateEt;
   int    m_bucketOpenMin10;
   double m_bO, m_bH, m_bL, m_bC, m_bV;
   int    m_bStartOpenMinEt;
   int    m_bOpenDateUtc, m_bOpenHhmmUtc;

   bool   m_emaReady, m_prevCloseReady, m_atrReady, m_oscReady;
   int    m_trCount;
   double m_trSum, m_ema21, m_prevDecClose, m_atr14, m_osc;
   int    m_shadowSide, m_pendingRevSide;
   int    m_vwapDate;
   double m_vwapVol, m_vwapPv;

   bool IsBlockedSession(int ymd)
   {
      return (ymd == 20220803 || ymd == 20220830 || ymd == 20230405 || ymd == 20240704 ||
              ymd == 20241224 || ymd == 20250120 || ymd == 20250703 || ymd == 20250829);
   }

   void ResetState()
   {
      m_prevCloseReady = false; m_oscReady = false; m_atrReady = false; m_emaReady = false;
      m_trSum = 0.0; m_trCount = 0; m_prevDecClose = 0.0; m_osc = 0.0; m_atr14 = 0.0; m_ema21 = 0.0;
      m_pendingRevSide = 0; m_shadowSide = 0; m_vwapDate = -1; m_vwapVol = 0.0; m_vwapPv = 0.0;
   }

   bool UpdateIndicator(double hi, double lo, double cl)
   {
      m_ema21 = (!m_emaReady) ? cl : (m_emaAlpha * cl + (1.0 - m_emaAlpha) * m_ema21);
      m_emaReady = true;

      double tr = (!m_prevCloseReady) ? (hi - lo)
         : MathMax(hi - lo, MathMax(MathAbs(hi - m_prevDecClose), MathAbs(lo - m_prevDecClose)));
      m_prevDecClose = cl;
      m_prevCloseReady = true;

      if(!m_atrReady)
      {
         m_trCount++;
         m_trSum += tr;
         if(m_trCount == 14) { m_atr14 = m_trSum / 14.0; m_atrReady = true; }
      }
      else
      {
         m_atr14 = (13.0 * m_atr14 + tr) / 14.0;
      }

      if(!m_atrReady || m_atr14 <= 0.0 || !MathIsValidNumber(m_atr14)) return false;

      double raw = 100.0 * (cl - m_ema21) / (m_oscAtrMult * m_atr14);
      m_osc = (!m_oscReady) ? raw : (0.5 * raw + 0.5 * m_osc);
      m_oscReady = true;
      return true;
   }

   void Flush10mBucket(double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host, int closeMinEt)
   {
      m_hasBucket = false;
      int sessDate = m_bucketDateEt;
      if(IsBlockedSession(sessDate))
      {
         m_shadowSide = 0; m_pendingRevSide = 0;
         if(sl.isOpen) host.QueueMarketExit(sl, "INCOMPLETE_SESSION");
         return;
      }

      if(m_bOpenHhmmUtc == 0 && m_prevCloseReady && MathAbs(m_bO - m_prevDecClose) > 400.0 * tickSize)
      {
         bool had = (m_shadowSide != 0);
         ResetState();
         if(had && sl.isOpen) host.QueueMarketExit(sl, "ROLL_RESET");
      }

      double prevOsc = m_osc;
      bool prevOscReady = m_oscReady;
      bool oscNow = UpdateIndicator(m_bH, m_bL, m_bC);

      bool vwapOk = false;
      if(m_bStartOpenMinEt >= 570 && m_bStartOpenMinEt < 960)
      {
         if(m_vwapDate != sessDate) { m_vwapDate = sessDate; m_vwapVol = 0.0; m_vwapPv = 0.0; }
         double typ = (m_bH + m_bL + m_bC) / 3.0;
         m_vwapPv += typ * m_bV;
         m_vwapVol += m_bV;
         if(m_vwapVol > 0.0 && m_atrReady)
         {
            double vw = m_vwapPv / m_vwapVol;
            vwapOk = MathAbs(m_bC - vw) < 2.5 * m_atr14;
         }
      }

      if(closeMinEt == 960)
      {
         m_shadowSide = 0; m_pendingRevSide = 0;
         if(sl.isOpen) host.QueueMarketExit(sl, "CASH_CLOSE");
         return;
      }

      if(!prevOscReady || !oscNow) return;

      bool bullCross = (prevOsc <= 100.0 && m_osc > 100.0);
      bool bearCross = (prevOsc >= -100.0 && m_osc < -100.0);
      if(!bullCross && !bearCross) return;

      int newSide = bullCross ? 1 : -1;
      if(m_shadowSide == newSide) return;

      bool inWin = (closeMinEt >= 570 && closeMinEt < m_entryEndMinEt);
      if(m_shadowSide == 0)
      {
         if(!inWin) return;
         m_shadowSide = newSide;
         if(vwapOk && !sl.isOpen && MathIsValidNumber(atr20Session) && atr20Session > 0.0)
            host.QueueMarketEntry(sl, newSide, m_slAtrK * atr20Session, EMPTY_VALUE, EMPTY_VALUE);
         return;
      }

      if(!inWin)
      {
         m_shadowSide = 0; m_pendingRevSide = 0;
         if(sl.isOpen) host.QueueMarketExit(sl, "OPPOSITE");
         return;
      }

      m_shadowSide = newSide;
      if(sl.isOpen)
      {
         m_pendingRevSide = vwapOk ? newSide : 0;
         host.QueueMarketExit(sl, "REVERSAL");
         return;
      }
      if(vwapOk && MathIsValidNumber(atr20Session) && atr20Session > 0.0)
         host.QueueMarketEntry(sl, newSide, m_slAtrK * atr20Session, EMPTY_VALUE, EMPTY_VALUE);
   }

public:
   CAtrPhaseEngine(double oscAtrMult = 3.0, int entryEndMinEt = 660, double slAtrK = 0.50)
      : CFsModuleEngineBase("R_osc30_end660_ATR50"),
        m_oscAtrMult(oscAtrMult), m_entryEndMinEt(entryEndMinEt), m_slAtrK(slAtrK),
        m_emaAlpha(2.0 / 22.0), m_hasBucket(false), m_bucketDateEt(0), m_bucketOpenMin10(0),
        m_bO(0.0), m_bH(0.0), m_bL(0.0), m_bC(0.0), m_bV(0.0),
        m_bStartOpenMinEt(0), m_bOpenDateUtc(0), m_bOpenHhmmUtc(0),
        m_emaReady(false), m_prevCloseReady(false), m_atrReady(false), m_oscReady(false),
        m_trCount(0), m_trSum(0.0), m_ema21(0.0), m_prevDecClose(0.0), m_atr14(0.0), m_osc(0.0),
        m_shadowSide(0), m_pendingRevSide(0), m_vwapDate(-1), m_vwapVol(0.0), m_vwapPv(0.0) {}

   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) override
   {
      if(m_pendingRevSide != 0 && !sl.isOpen && !sl.hasPendingEntry)
      {
         int rSide = m_pendingRevSide;
         m_pendingRevSide = 0;
         if(MathIsValidNumber(atr20Session) && atr20Session > 0.0)
            host.QueueMarketEntry(sl, rSide, m_slAtrK * atr20Session, EMPTY_VALUE, EMPTY_VALUE);
      }

      int bMin10 = (bar.openMinEt / 10) * 10;
      if(m_hasBucket && (m_bucketDateEt != bar.openDateEt || m_bucketOpenMin10 != bMin10))
         Flush10mBucket(atr20Session, sl, host, m_bucketOpenMin10 + 10);

      if(!m_hasBucket)
      {
         m_hasBucket = true;
         m_bucketDateEt = bar.openDateEt;
         m_bucketOpenMin10 = bMin10;
         m_bO = bar.open; m_bH = bar.high; m_bL = bar.low; m_bC = bar.close; m_bV = bar.volume;
         m_bStartOpenMinEt = bar.openMinEt;
         m_bOpenDateUtc = bar.openDateUtc;
         m_bOpenHhmmUtc = bar.openHhmmUtc;
      }
      else
      {
         m_bH = MathMax(m_bH, bar.high);
         m_bL = MathMin(m_bL, bar.low);
         m_bC = bar.close;
         m_bV += bar.volume;
      }

      if(bar.closeMinEt == m_bucketOpenMin10 + 10)
         Flush10mBucket(atr20Session, sl, host, bar.closeMinEt);
   }
};

// ---------------------------------------------------------------------------
// Module Z: ZetaTrendDay (1m ETH -> 15m RTH buckets + whole-session eff%)
// ---------------------------------------------------------------------------
class CZetaEngine : public CFsModuleEngineBase
{
private:
   int    m_bucketMin;
   int    m_emaPeriod;
   double m_minEffPct;
   double m_slAtrK;
   double m_emaAlpha;
   double m_emaSeed[];

   double m_emaValue;
   bool   m_emaReady;
   int    m_emaSeedCount;

   bool   m_bActive, m_bValid;
   int    m_bIdx, m_bCount;
   double m_bH, m_bL, m_bC;

   bool   m_sesActive, m_sesValid, m_sesEmaObs, m_sesTouchFree;
   int    m_sesDateKey, m_sesBucketCount, m_sesMinCount;
   double m_sesO, m_sesH, m_sesL, m_sesC;

   bool   m_pendSummaryAvail, m_pendQualified;
   int    m_pendSesKey;
   bool   m_pendEntry;
   int    m_pendEntryDir, m_pendEntrySesKey;
   double m_pendEntryTarget;

   int NextFullNyseSession(int key)
   {
      int cur = key;
      for(int i = 0; i < 20; i++)
      {
         cur = FsAddDaysYmd(cur, 1);
         if(FsIsZetaFullNyseSession(cur)) return cur;
      }
      return 0;
   }

   void ResetBucket() { m_bActive = false; m_bIdx = -1; m_bCount = 0; m_bValid = true; m_bH = 0.0; m_bL = 0.0; m_bC = 0.0; }
   void ResetEma()    { m_emaValue = 0.0; m_emaReady = false; m_emaSeedCount = 0; ArrayInitialize(m_emaSeed, 0.0); }

   void UpdateEma(double c)
   {
      if(!(c > 0.0)) return;
      if(!m_emaReady)
      {
         if(m_emaSeedCount < m_emaPeriod) m_emaSeed[m_emaSeedCount++] = c;
         if(m_emaSeedCount == m_emaPeriod)
         {
            double s = 0.0;
            for(int i = 0; i < m_emaPeriod; i++) s += m_emaSeed[i];
            m_emaValue = s / m_emaPeriod;
            m_emaReady = true;
         }
         return;
      }
      m_emaValue += m_emaAlpha * (c - m_emaValue);
   }

   bool UpdateBucket(int minOff, double hi, double lo, double cl)
   {
      int bIdx = minOff / m_bucketMin;
      int bMin = minOff % m_bucketMin;

      if(m_bActive && m_bIdx != bIdx) { m_sesValid = false; ResetBucket(); ResetEma(); }
      if(!m_bActive)
      {
         m_bActive = true; m_bIdx = bIdx; m_bCount = 0;
         m_bValid = (bMin == 0) && (bIdx == m_sesBucketCount);
         m_bH = hi; m_bL = lo; m_bC = cl;
      }
      else
      {
         m_bH = MathMax(m_bH, hi); m_bL = MathMin(m_bL, lo); m_bC = cl;
      }

      if(bMin != m_bCount) m_bValid = false;
      m_bCount++;
      if(bMin != m_bucketMin - 1) return false;

      if(!m_bValid || m_bCount != m_bucketMin) { m_sesValid = false; ResetEma(); ResetBucket(); return false; }

      if(!m_emaReady) m_sesEmaObs = false;
      else if(m_bL <= m_emaValue && m_emaValue <= m_bH) m_sesTouchFree = false;

      UpdateEma(m_bC);
      m_sesBucketCount++;
      ResetBucket();
      return true;
   }

   void FinalizeSession()
   {
      if(!m_sesActive) return;
      if(m_bActive) { m_sesValid = false; ResetBucket(); ResetEma(); }

      int expMin = 390;
      int expBuckets = expMin / m_bucketMin;
      bool allValid = m_sesValid && m_sesMinCount == expMin && m_sesBucketCount == expBuckets;
      double sesRange = m_sesH - m_sesL;
      double eff = (sesRange <= 0.0) ? 0.0 : (100.0 * MathAbs(m_sesC - m_sesO) / sesRange);

      m_pendSummaryAvail = true;
      m_pendQualified = allValid && m_sesEmaObs && sesRange > 0.0 && m_sesTouchFree && eff >= m_minEffPct;
      m_pendSesKey = m_sesDateKey;
      if(!allValid) ResetEma();
      m_sesActive = false;
      ResetBucket();
   }

public:
   CZetaEngine(int bucketMinutes = 15, int emaPeriod = 20, double minEffPct = 40.0, double slAtrK = 0.50)
      : CFsModuleEngineBase("Z_b15_e20_eff40_ATR50"),
        m_bucketMin(bucketMinutes), m_emaPeriod(emaPeriod), m_minEffPct(minEffPct), m_slAtrK(slAtrK),
        m_emaAlpha(2.0 / (emaPeriod + 1.0)), m_emaValue(0.0), m_emaReady(false), m_emaSeedCount(0),
        m_bActive(false), m_bValid(true), m_bIdx(-1), m_bCount(0), m_bH(0.0), m_bL(0.0), m_bC(0.0),
        m_sesActive(false), m_sesValid(false), m_sesEmaObs(false), m_sesTouchFree(false),
        m_sesDateKey(0), m_sesBucketCount(0), m_sesMinCount(0), m_sesO(0.0), m_sesH(0.0), m_sesL(0.0), m_sesC(0.0),
        m_pendSummaryAvail(false), m_pendQualified(false), m_pendSesKey(0),
        m_pendEntry(false), m_pendEntryDir(0), m_pendEntrySesKey(0), m_pendEntryTarget(0.0)
   {
      ArrayResize(m_emaSeed, m_emaPeriod);
      ArrayInitialize(m_emaSeed, 0.0);
   }

   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) override
   {
      int key = bar.openDateCt;
      int minCt = bar.openMinCt;
      if(minCt < 510 || minCt >= 900 || !FsIsZetaFullNyseSession(key))
         return;

      if(!m_sesActive || m_sesDateKey != key)
      {
         if(m_sesActive) FinalizeSession();

         if(m_pendSummaryAvail && NextFullNyseSession(m_pendSesKey) != key)
         {
            ResetEma();
            m_pendQualified = false;
            m_pendSummaryAvail = false;
         }

         bool qualPrev = m_pendSummaryAvail && m_pendQualified;
         m_pendQualified = false;
         m_pendSummaryAvail = false;

         if(sl.isOpen) host.QueueMarketExit(sl, "SESSION_SAFETY");

         m_sesActive = true; m_sesDateKey = key; m_sesValid = true;
         m_sesBucketCount = 0; m_sesMinCount = 0;
         m_sesO = bar.open; m_sesH = bar.high; m_sesL = bar.low; m_sesC = bar.close;
         m_sesEmaObs = true; m_sesTouchFree = true;
         ResetBucket();

         if(minCt == 510 && qualPrev && m_emaReady)
         {
            int dir = (bar.open > m_emaValue) ? -1 : ((bar.open < m_emaValue) ? 1 : 0);
            if(dir != 0)
            {
               m_pendEntry = true;
               m_pendEntryDir = dir;
               m_pendEntryTarget = m_emaValue;
               m_pendEntrySesKey = key;
            }
         }
      }

      int minOff = minCt - 510;
      if(minOff != m_sesMinCount) m_sesValid = false;
      m_sesMinCount++;
      m_sesH = MathMax(m_sesH, bar.high);
      m_sesL = MathMin(m_sesL, bar.low);
      m_sesC = bar.close;

      bool bucketClosed = UpdateBucket(minOff, bar.high, bar.low, bar.close);

      if(m_pendEntry && minCt == 510)
      {
         if(m_pendEntryDir <= 0 && !(bar.low > m_pendEntryTarget)) m_pendEntry = false;
         if(m_pendEntryDir > 0 && !(bar.high < m_pendEntryTarget)) m_pendEntry = false;
      }

      if(m_pendEntry && minCt == 510 && key == m_pendEntrySesKey)
      {
         bool stillValid = (m_pendEntryDir <= 0) ? (bar.close > m_pendEntryTarget) : (bar.close < m_pendEntryTarget);
         if(stillValid && !sl.isOpen && MathIsValidNumber(atr20Session) && atr20Session > 0.0)
         {
            double tgt = FsRoundZetaTarget(m_pendEntryDir, m_pendEntryTarget, tickSize);
            host.QueueMarketEntry(sl, m_pendEntryDir, m_slAtrK * atr20Session, tgt, EMPTY_VALUE);
         }
         m_pendEntry = false;
      }
      else if(m_pendEntry && minCt != 510)
      {
         m_pendEntry = false;
      }

      if(bucketClosed && sl.isOpen)
      {
         double newTgt = FsRoundZetaTarget(sl.side, m_emaValue, tickSize);
         if(MathIsValidNumber(newTgt)) sl.targetPrice = newTgt;
      }

      if(minCt >= 899 && sl.isOpen) host.QueueMarketExit(sl, "EOD");
      if(minCt == 899) FinalizeSession();
   }
};

// ---------------------------------------------------------------------------
// Module T: FtmOrb (15m ORB 09:30-09:45 ET + Quarterly KNN + +1.5R M1 BE)
// ---------------------------------------------------------------------------
struct FsTDirRow
{
   int    sessionKey;
   double features[14];
   bool   flipWins;
   int    seq;
};

struct FsTShadowTrade
{
   int    side;
   double entry;
   double activeStop;
   double target;
   double riskPts;
   double managedTrigR;
   double managedLockR;
   bool   complete;
   bool   pendCondExit;
   double exitPrice;
};

struct FsTShadowPair
{
   bool   active;
   int    sessionKey;
   datetime expParentFillCloseUtc;
   int    baselineSide;
   double features[14];
   bool   priorTrendAvail;
   double priorTrendBps;
   bool   initialized;
   bool   invalid;
   bool   labelRecorded;
   FsTShadowTrade breakout;
   FsTShadowTrade fade;
};

struct FsTPendingDec
{
   bool     active;
   datetime expObsOpenUtc;
   int      side;
   int      reqBars;
   int      observedBars;
   double   firstObsOpen;
   string   branch;
   double   features[14];
   int      baselineSide;
   double   signalClose;
   bool     submitActual;
};

class CFtmOrbEngine : public CFsModuleEngineBase
{
private:
   double m_beTriggerR;
   double m_stopOrbMult;

   double m_eligOrbHistBps[];
   double m_eligRthCloseHist[];
   double m_eligSesRetHistBps[];
   FsTDirRow m_trainRows[];
   FsBarContext m_m1Buf[32];
   int    m_m1BufCount;

   int    m_trainSeq;
   int    m_activeQuarterKey;
   double m_knnTrainX[]; // flat rows * 14
   bool   m_knnTrainFlip[];
   int    m_knnTrainSeq[];
   double m_knnMean[14];
   double m_knnScale[14];
   int    m_knnRowsCount;

   int    m_curCashDate, m_prevDayOfCash;
   bool   m_sesElig, m_refOpenCap, m_dayBlocked, m_orbFinalized, m_boConsumed, m_cashExitTrig, m_cashWinInt, m_orbHistRec, m_rthCloseRec;
   double m_refSesOpen;
   int    m_orbBarCount, m_expNextOrbOpenMin;
   double m_orbHigh, m_orbLow, m_orbOpen, m_orbClose, m_curOrbBps, m_curOrbQ75Bps, m_curPriorTrendBps;
   bool   m_curOrbQ75Avail, m_curPriorTrendAvail;

   double m_rthMinCloses[];
   double m_rthTypVolSum, m_rthVolSum;
   datetime m_lastCashCloseUtc;

   FsTShadowPair m_activeShadow;
   FsTPendingDec m_pendDec1;
   FsTPendingDec m_pendDec2;

   double m_liveTrigR, m_liveLockR, m_liveIlRiskPts;
   bool   m_liveIlActivated, m_condExitReq;

   void PushRingDouble(double &arr[], double val, int maxLen)
   {
      int n = ArraySize(arr);
      if(n < maxLen)
      {
         ArrayResize(arr, n + 1);
         arr[n] = val;
      }
      else
      {
         for(int i = 1; i < n; i++) arr[i - 1] = arr[i];
         arr[n - 1] = val;
      }
   }

   double SafeRetBps(double num, double den) { return (den == 0.0) ? 0.0 : (num / den - 1.0) * 10000.0; }
   double LagRetBps(const double &v[], int p)
   {
      int n = ArraySize(v);
      return (n <= p) ? 0.0 : SafeRetBps(v[n - 1], v[n - 1 - p]);
   }

   int RoundOffsetTicks(double pts, bool ceilMode)
   {
      double t = pts / tickSize;
      return ceilMode ? (int)MathCeil(t - 0.5) : (int)MathFloor(t + 0.5);
   }

   double LinearPercentile(const double &vals[], double q)
   {
      int n = ArraySize(vals);
      double tmp[];
      ArrayCopy(tmp, vals);
      ArraySort(tmp);
      double pos = (n - 1) * q;
      int lo = (int)MathFloor(pos), hi = (int)MathCeil(pos);
      if(lo == hi) return tmp[lo];
      return tmp[lo] + (tmp[hi] - tmp[lo]) * (pos - lo);
   }

   void InvalidatePending()
   {
      m_pendDec1.active = false;
      m_pendDec2.active = false;
      m_activeShadow.active = false;
   }

   void BeginCashDate(int cashKey, FsVirtualSleeve &sl, IFsSignalHost *host)
   {
      bool hasExp = sl.isOpen || sl.hasPendingEntry;
      InvalidatePending();
      m_curCashDate = cashKey;
      m_prevDayOfCash = FsAddDaysYmd(cashKey, -1);

      m_sesElig = true; m_refOpenCap = false; m_refSesOpen = 0.0;
      m_dayBlocked = hasExp; m_orbFinalized = false; m_boConsumed = hasExp;
      m_cashExitTrig = false; m_cashWinInt = true; m_orbHistRec = false; m_rthCloseRec = false;
      m_liveIlActivated = false; m_condExitReq = false;
      m_orbBarCount = 0; m_expNextOrbOpenMin = 570;
      m_orbHigh = -1e18; m_orbLow = 1e18;
      m_orbOpen = 0.0; m_orbClose = 0.0; m_curOrbBps = 0.0; m_curOrbQ75Bps = 0.0; m_curOrbQ75Avail = false;

      int nHist = ArraySize(m_eligRthCloseHist);
      if(nHist >= 21 && m_eligRthCloseHist[0] > 0.0)
      {
         m_curPriorTrendBps = SafeRetBps(m_eligRthCloseHist[nHist - 1], m_eligRthCloseHist[0]);
         m_curPriorTrendAvail = true;
      }
      else
      {
         m_curPriorTrendBps = 0.0;
         m_curPriorTrendAvail = false;
      }

      ArrayResize(m_rthMinCloses, 0);
      m_rthTypVolSum = 0.0; m_rthVolSum = 0.0; m_lastCashCloseUtc = 0;
      if(hasExp && sl.isOpen) host.QueueMarketExit(sl, "OvernightExposureOrEntry");
      if(!FsIsFullNyseTradingDay(cashKey)) { m_sesElig = false; m_dayBlocked = true; }
   }

   void SelectPlan(int side, bool priorAvail, double priorBps, double &tgtR, double &trigR, double &lockR)
   {
      if(m_curOrbQ75Avail && m_curOrbBps > m_curOrbQ75Bps) { tgtR = 1.25; trigR = 1.25; lockR = 0.0; return; }
      if(priorAvail && (side * priorBps) < 0.0) { tgtR = 3.0; trigR = 0.75; lockR = 0.10; return; }
      tgtR = 3.0; trigR = 1.25; lockR = 0.0;
   }

   void CreateShadowTrade(int side, double parentOpen, bool ptAvail, double ptBps, FsTShadowTrade &st)
   {
      double epx = parentOpen + side * tickSize;
      double rawD = MathMax(2.0, MathMin(100.0, (m_orbHigh - m_orbLow) * 1.25));
      double stopP = FsRoundTick(epx - side * rawD, tickSize);
      double rPts = side * (epx - stopP);
      double tgtR, trigR, lockR;
      SelectPlan(side, ptAvail, ptBps, tgtR, trigR, lockR);
      double tgtP = FsRoundTick(epx + side * rawD * tgtR, tickSize);

      st.side = side; st.entry = epx; st.activeStop = stopP; st.target = tgtP;
      st.riskPts = rPts; st.managedTrigR = trigR; st.managedLockR = lockR;
      st.complete = false; st.pendCondExit = false; st.exitPrice = epx;
      if(!(rPts > 0.0)) st.complete = true;
   }

   void StepShadowTrade(FsTShadowTrade &st, const FsBarContext &bar)
   {
      if(st.complete) return;
      if(st.pendCondExit) { st.exitPrice = bar.open - st.side * tickSize; st.complete = true; st.pendCondExit = false; return; }
      bool hitSl = (st.side == 1) ? (bar.low <= st.activeStop) : (bar.high >= st.activeStop);
      bool hitTp = (st.side == 1) ? (bar.high >= st.target) : (bar.low <= st.target);
      if(hitSl)
      {
         double fill = (st.side == 1) ? MathMin(st.activeStop, bar.open) : MathMax(st.activeStop, bar.open);
         st.exitPrice = fill - st.side * tickSize; st.complete = true; return;
      }
      if(hitTp)
      {
         st.exitPrice = (st.side == 1) ? MathMax(st.target, bar.open) : MathMin(st.target, bar.open);
         st.complete = true; return;
      }
      if(bar.closeMinEt < 960 && bar.closeMinEt % 15 == 0)
      {
         double cr = st.side * (bar.close - st.entry) / st.riskPts;
         if(cr >= st.managedTrigR)
         {
            double ns = FsRoundTick(st.entry + st.side * st.riskPts * st.managedLockR, tickSize);
            st.activeStop = (st.side == 1) ? MathMax(st.activeStop, ns) : MathMin(st.activeStop, ns);
         }
         if(bar.closeMinEt == 930 && (cr < 0.0 || cr >= 1.0)) st.pendCondExit = true;
      }
   }

   void TryRecordLabel()
   {
      if(!m_activeShadow.active || m_activeShadow.invalid || m_activeShadow.labelRecorded || !m_activeShadow.initialized) return;
      if(!m_activeShadow.breakout.complete || !m_activeShadow.fade.complete) return;
      double boNet = m_activeShadow.breakout.side * (m_activeShadow.breakout.exitPrice - m_activeShadow.breakout.entry) * 20.0 - 2.5;
      double faNet = m_activeShadow.fade.side * (m_activeShadow.fade.exitPrice - m_activeShadow.fade.entry) * 20.0 - 2.5;
      bool flipWins = (faNet > 0.0);
      if((boNet > 0.0) != flipWins)
      {
         int sz = ArraySize(m_trainRows);
         ArrayResize(m_trainRows, sz + 1);
         m_trainRows[sz].sessionKey = m_activeShadow.sessionKey;
         for(int f = 0; f < 14; f++) m_trainRows[sz].features[f] = m_activeShadow.features[f];
         m_trainRows[sz].flipWins = flipWins;
         m_trainRows[sz].seq = m_trainSeq++;
      }
      m_activeShadow.labelRecorded = true;
      m_activeShadow.active = false;
   }

   void FitQuarterKnn(int cashKey)
   {
      int y = cashKey / 10000;
      int mon = (cashKey / 100) % 100;
      int qStartMo = ((mon - 1) / 3) * 3 + 1;
      int cutoff = FsAddDaysYmd(y * 10000 + qStartMo * 100 + 1, -1);

      int eligIdx[];
      int total = ArraySize(m_trainRows);
      for(int i = 0; i < total; i++)
      {
         if(m_trainRows[i].sessionKey <= cutoff)
         {
            int c = ArraySize(eligIdx);
            ArrayResize(eligIdx, c + 1);
            eligIdx[c] = i;
         }
      }
      m_knnRowsCount = ArraySize(eligIdx);
      if(m_knnRowsCount < 100) return;

      for(int f = 0; f < 14; f++)
      {
         double s = 0.0;
         for(int i = 0; i < m_knnRowsCount; i++) s += m_trainRows[eligIdx[i]].features[f];
         double mu = s / m_knnRowsCount;
         double v = 0.0;
         for(int i = 0; i < m_knnRowsCount; i++) { double d = m_trainRows[eligIdx[i]].features[f] - mu; v += d * d; }
         m_knnMean[f] = mu;
         double sc = MathSqrt(v / m_knnRowsCount);
         m_knnScale[f] = (sc > 0.0) ? sc : 1.0;
      }

      ArrayResize(m_knnTrainX, m_knnRowsCount * 14);
      ArrayResize(m_knnTrainFlip, m_knnRowsCount);
      ArrayResize(m_knnTrainSeq, m_knnRowsCount);
      for(int i = 0; i < m_knnRowsCount; i++)
      {
         int src = eligIdx[i];
         for(int f = 0; f < 14; f++)
            m_knnTrainX[i * 14 + f] = (m_trainRows[src].features[f] - m_knnMean[f]) / m_knnScale[f];
         m_knnTrainFlip[i] = m_trainRows[src].flipWins;
         m_knnTrainSeq[i]  = m_trainRows[src].seq;
      }
   }

   double PredictKnnFlipProb(const double &feat[])
   {
      if(m_knnRowsCount < 100) return 0.0;
      double fz[14];
      for(int f = 0; f < 14; f++) fz[f] = (feat[f] - m_knnMean[f]) / m_knnScale[f];

      double dists[];
      bool used[];
      ArrayResize(dists, m_knnRowsCount);
      ArrayResize(used, m_knnRowsCount);
      ArrayInitialize(used, false);

      for(int i = 0; i < m_knnRowsCount; i++)
      {
         double d2 = 0.0;
         int off = i * 14;
         for(int f = 0; f < 14; f++) { double df = m_knnTrainX[off + f] - fz[f]; d2 += df * df; }
         dists[i] = MathSqrt(d2);
      }

      int flips = 0;
      for(int k = 0; k < 15; k++)
      {
         int bestIdx = -1;
         for(int i = 0; i < m_knnRowsCount; i++)
         {
            if(used[i]) continue;
            if(bestIdx < 0 || dists[i] < dists[bestIdx] ||
               (dists[i] == dists[bestIdx] && m_knnTrainSeq[i] < m_knnTrainSeq[bestIdx]))
               bestIdx = i;
         }
         if(bestIdx < 0) break;
         used[bestIdx] = true;
         if(m_knnTrainFlip[bestIdx]) flips++;
      }
      return (flips + 2.0) / (15.0 + 4.0);
   }

   void SubmitLiveEntry(int side, FsVirtualSleeve &sl, IFsSignalHost *host)
   {
      if(sl.isOpen || sl.hasPendingEntry) return;
      double orbRng = m_orbHigh - m_orbLow;
      double stopPts = MathMax(2.0, MathMin(100.0, m_stopOrbMult * orbRng));
      double ilRiskPts = MathMax(2.0, MathMin(100.0, 1.25 * orbRng));
      double tgtR, trigR, lockR;
      SelectPlan(side, m_curPriorTrendAvail, m_curPriorTrendBps, tgtR, trigR, lockR);
      int tgtTicks = RoundOffsetTicks(ilRiskPts * tgtR, side > 0);
      m_liveIlRiskPts = ilRiskPts; m_liveTrigR = trigR; m_liveLockR = lockR; m_liveIlActivated = false; m_condExitReq = false;
      host.QueueMarketEntry(sl, side, stopPts, EMPTY_VALUE, tgtTicks * tickSize);
   }

   void ApplyFinalRefinementOrSubmit(int refSide, datetime fillUtc, bool submitActual, int baseSide, const double &feat[], double sigClose, FsVirtualSleeve &sl, IFsSignalHost *host)
   {
      double orbR = m_orbHigh - m_orbLow;
      if(!(orbR > 0.0)) { m_dayBlocked = true; return; }
      double sFlip = refSide * baseSide;
      double alPrior = sFlip * feat[1];
      double alRet30 = sFlip * feat[5];
      double orbBody = refSide * (m_orbClose - m_orbOpen) / orbR;
      double edge = (refSide == 1) ? m_orbHigh : m_orbLow;
      double sigExt = refSide * (sigClose - edge) / orbR;

      if(alPrior > 100.0 && !(orbBody > 0.0))
      {
         m_pendDec2.active = true; m_pendDec2.expObsOpenUtc = fillUtc; m_pendDec2.side = refSide;
         m_pendDec2.reqBars = 2; m_pendDec2.observedBars = 0; m_pendDec2.firstObsOpen = 0.0;
         m_pendDec2.branch = "prior_session_disagreement"; m_pendDec2.submitActual = submitActual;
      }
      else if(alRet30 > 25.0 && !(sigExt > 0.25))
      {
         m_pendDec2.active = true; m_pendDec2.expObsOpenUtc = fillUtc; m_pendDec2.side = refSide;
         m_pendDec2.reqBars = 1; m_pendDec2.observedBars = 0; m_pendDec2.firstObsOpen = 0.0;
         m_pendDec2.branch = "intraday_continuation"; m_pendDec2.submitActual = submitActual;
      }
      else if(submitActual)
      {
         SubmitLiveEntry(refSide, sl, host);
      }
   }

   void EvaluateAdmissionAndDirection(const FsBarContext &bar, int baseSide, FsVirtualSleeve &sl, IFsSignalHost *host)
   {
      int idx = m_m1BufCount - 1;
      double sigOpen = m_m1Buf[idx - 14].open;
      double sigHi = -1e18, sigLo = 1e18;
      datetime cUtc = bar.closeUtc;
      for(int k = 0; k < 15; k++)
      {
         datetime expUtc = cUtc - k * 60;
         if(m_m1Buf[idx - k].closeUtc != expUtc) { m_boConsumed = true; m_dayBlocked = true; return; }
         if(m_m1Buf[idx - k].high > sigHi) sigHi = m_m1Buf[idx - k].high;
         if(m_m1Buf[idx - k].low < sigLo) sigLo = m_m1Buf[idx - k].low;
      }
      if(!(sigHi > sigLo)) { m_boConsumed = true; m_dayBlocked = true; return; }
      double sigClose = bar.close, sigRng = sigHi - sigLo;
      double body = baseSide * (sigClose - sigOpen) / sigRng;
      double closeLoc = (baseSide == 1) ? ((sigClose - sigLo) / sigRng) : ((sigHi - sigClose) / sigRng);
      if(body < 0.15 || closeLoc < 0.60) return;

      double confLvl = (baseSide == 1) ? (m_orbHigh + tickSize) : (m_orbLow - tickSize);
      int touches = 0;
      for(int k = 0; k < 15; k++)
      {
         if(baseSide == 1) { if(m_m1Buf[idx - k].high >= confLvl) touches++; }
         else { if(m_m1Buf[idx - k].low <= confLvl) touches++; }
      }
      if(touches < 3) { m_boConsumed = true; return; }

      int nCloses = ArraySize(m_rthMinCloses);
      if(!(m_orbOpen > 0.0 && m_orbClose > 0.0 && m_rthVolSum > 0.0) || nCloses == 0)
      {
         m_boConsumed = true; m_dayBlocked = true; return;
      }

      int nHistRth = ArraySize(m_eligRthCloseHist);
      double prevRthC = (nHistRth > 0) ? m_eligRthCloseHist[nHistRth - 1] : m_orbOpen;
      int nSesRet = ArraySize(m_eligSesRetHistBps);
      double priorSesBps = (nSesRet > 0) ? m_eligSesRetHistBps[nSesRet - 1] : 0.0;
      double priorRet5 = LagRetBps(m_eligRthCloseHist, 5);
      double priorRet20 = LagRetBps(m_eligRthCloseHist, 20);
      double vwap = m_rthTypVolSum / m_rthVolSum;
      double c30Ago = (nCloses <= 30) ? m_orbClose : m_rthMinCloses[nCloses - 31];
      double gapBps = SafeRetBps(m_orbOpen, prevRthC);
      double vwapDist = SafeRetBps(sigClose, vwap);
      double ret30m = SafeRetBps(sigClose, c30Ago);
      double elapsed15m = (bar.closeMinEt - 585) / 15.0;

      int yr = m_curCashDate / 10000, mo = (m_curCashDate / 100) % 100, dy = m_curCashDate % 100;
      int wk = (FsDowFromYmd(yr, mo, dy) + 6) % 7;
      double twoPi = 6.2831853071795862;
      double feat[14];
      feat[0] = baseSide * gapBps; feat[1] = baseSide * priorSesBps; feat[2] = baseSide * priorRet5; feat[3] = baseSide * priorRet20;
      feat[4] = baseSide * vwapDist; feat[5] = baseSide * ret30m; feat[6] = baseSide; feat[7] = elapsed15m; feat[8] = m_curOrbBps; feat[9] = touches;
      feat[10] = MathSin(twoPi * wk / 5.0); feat[11] = MathCos(twoPi * wk / 5.0);
      feat[12] = MathSin(twoPi * (mo - 1) / 12.0); feat[13] = MathCos(twoPi * (mo - 1) / 12.0);
      for(int f = 0; f < 14; f++) if(!MathIsValidNumber(feat[f])) { m_boConsumed = true; m_dayBlocked = true; return; }

      m_boConsumed = true;
      bool priorOverride = (baseSide * priorSesBps) < -300.0;
      bool knnOverride = false;
      if(m_curCashDate >= 20120101)
      {
         int qKey = yr * 10 + ((mo - 1) / 3 + 1);
         if(m_activeQuarterKey != qKey)
         {
            FitQuarterKnn(m_curCashDate);
            m_activeQuarterKey = qKey;
         }
         knnOverride = PredictKnnFlipProb(feat) > 0.65;
      }
      int dirSide = (priorOverride || knnOverride) ? -baseSide : baseSide;

      if(m_activeShadow.active) { InvalidatePending(); m_dayBlocked = true; return; }
      m_activeShadow.active = true;
      m_activeShadow.sessionKey = m_curCashDate;
      m_activeShadow.expParentFillCloseUtc = bar.closeUtc;
      m_activeShadow.baselineSide = baseSide;
      for(int f = 0; f < 14; f++) m_activeShadow.features[f] = feat[f];
      m_activeShadow.priorTrendAvail = m_curPriorTrendAvail;
      m_activeShadow.priorTrendBps = m_curPriorTrendBps;
      m_activeShadow.initialized = false; m_activeShadow.invalid = false; m_activeShadow.labelRecorded = false;

      bool ctxReady = m_curOrbQ75Avail && m_curPriorTrendAvail;
      bool submitActual = (m_curCashDate >= 20120101) && ctxReady && m_sesElig;

      if(MathAbs(elapsed15m - 1.0) < 1e-6 && !(feat[4] > 20.0))
      {
         if(submitActual) SubmitLiveEntry(baseSide, sl, host);
         return;
      }

      bool weakSig = !(dirSide * (sigClose - sigOpen) / sigRng > 0.20);
      bool hiVol = m_curOrbQ75Avail && (m_curOrbBps > m_curOrbQ75Bps);
      double dLvl = (dirSide == 1) ? (m_orbHigh + tickSize) : (m_orbLow - tickSize);
      int dTouch = 0;
      for(int k = 0; k < 15; k++)
      {
         if(dirSide == 1) { if(m_m1Buf[idx - k].high >= dLvl) dTouch++; }
         else { if(m_m1Buf[idx - k].low <= dLvl) dTouch++; }
      }
      bool hiVolVote = hiVol && !(dTouch > 3);

      if(weakSig || hiVolVote)
      {
         m_pendDec1.active = true;
         m_pendDec1.expObsOpenUtc = bar.closeUtc;
         m_pendDec1.side = dirSide;
         m_pendDec1.reqBars = weakSig ? 1 : 3;
         m_pendDec1.observedBars = 0;
         m_pendDec1.firstObsOpen = 0.0;
         m_pendDec1.branch = weakSig ? "weak_signal_delay_keep" : "high_vol_touch_vote";
         for(int f = 0; f < 14; f++) m_pendDec1.features[f] = feat[f];
         m_pendDec1.baselineSide = baseSide;
         m_pendDec1.signalClose = sigClose;
         m_pendDec1.submitActual = submitActual;
      }
      else
      {
         ApplyFinalRefinementOrSubmit(dirSide, bar.closeUtc, submitActual, baseSide, feat, sigClose, sl, host);
      }
   }

public:
   CFtmOrbEngine(double stopOrbMult = 1.0, double beTriggerR = 1.5)
      : CFsModuleEngineBase("T_stop100_BE15R_calFalse"),
        m_beTriggerR(beTriggerR), m_stopOrbMult(stopOrbMult), m_m1BufCount(0),
        m_trainSeq(0), m_activeQuarterKey(0), m_knnRowsCount(0),
        m_curCashDate(-1), m_prevDayOfCash(-1),
        m_sesElig(false), m_refOpenCap(false), m_dayBlocked(true), m_orbFinalized(false),
        m_boConsumed(false), m_cashExitTrig(false), m_cashWinInt(false), m_orbHistRec(false), m_rthCloseRec(false),
        m_refSesOpen(0.0), m_orbBarCount(0), m_expNextOrbOpenMin(570),
        m_orbHigh(-1e18), m_orbLow(1e18), m_orbOpen(0.0), m_orbClose(0.0),
        m_curOrbBps(0.0), m_curOrbQ75Bps(0.0), m_curPriorTrendBps(0.0),
        m_curOrbQ75Avail(false), m_curPriorTrendAvail(false),
        m_rthTypVolSum(0.0), m_rthVolSum(0.0), m_lastCashCloseUtc(0),
        m_liveTrigR(0.0), m_liveLockR(0.0), m_liveIlRiskPts(0.0), m_liveIlActivated(false), m_condExitReq(false)
   {
      m_activeShadow.active = false;
      m_pendDec1.active = false;
      m_pendDec2.active = false;
   }

   int KnnTrainRowsCount() { return ArraySize(m_trainRows); }

   virtual void UpdateM1OverlayProtectionsOnClose(FsVirtualSleeve &sl, const FsBarContext &bar) override
   {
      if(m_beTriggerR > 0.0 && sl.isOpen && !sl.overlayBeActivated)
      {
         if(sl.maxFavPts >= m_beTriggerR * MathMax(sl.riskPts, 1e-6))
         {
            if((sl.side > 0 && sl.entryPrice > sl.stopPrice) || (sl.side < 0 && sl.entryPrice < sl.stopPrice))
               sl.stopPrice = sl.entryPrice;
            sl.overlayBeActivated = true;
         }
      }
   }

   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) override
   {
      if(m_m1BufCount < 32) m_m1Buf[m_m1BufCount++] = bar;
      else
      {
         for(int i = 1; i < 32; i++) m_m1Buf[i - 1] = m_m1Buf[i];
         m_m1Buf[31] = bar;
      }
      if(m_m1BufCount < 16) return;

      int cashDate = bar.ethTradeDate;
      if(cashDate != m_curCashDate)
      {
         BeginCashDate(cashDate, sl, host);
         if(bar.closeMinEt < 570) m_cashWinInt = true;
      }

      if(m_sesElig && !m_refOpenCap && bar.openHhmmUtc == 2300 && bar.openDateUtc == m_prevDayOfCash)
      {
         if(!bar.exactMinute || !(bar.open > 0.0)) m_dayBlocked = true;
         else { m_refSesOpen = bar.open; m_refOpenCap = true; }
      }

      bool sameEt = (bar.openDateEt == m_curCashDate && bar.closeDateEt == m_curCashDate);
      bool inCash = sameEt && bar.openMinEt >= 570 && bar.closeMinEt <= 960;
      if(inCash && !bar.exactMinute)
      {
         m_dayBlocked = true; m_boConsumed = true; InvalidatePending();
         if(sl.isOpen) host.QueueMarketExit(sl, "CashTimeAlignment");
         return;
      }

      if(inCash)
      {
         if(m_lastCashCloseUtc != 0 && bar.openUtc != m_lastCashCloseUtc)
         {
            m_cashWinInt = false; m_dayBlocked = true; m_boConsumed = true; InvalidatePending();
            if(sl.isOpen) host.QueueMarketExit(sl, "CashDataGap");
            return;
         }
         m_lastCashCloseUtc = bar.closeUtc;
         if(!m_dayBlocked)
         {
            int n = ArraySize(m_rthMinCloses);
            ArrayResize(m_rthMinCloses, n + 1);
            m_rthMinCloses[n] = bar.close;
            m_rthTypVolSum += ((bar.high + bar.low + bar.close) / 3.0) * bar.volume;
            m_rthVolSum += bar.volume;
         }
      }

      if(sameEt && m_activeShadow.active && !m_activeShadow.invalid && !m_activeShadow.labelRecorded)
      {
         if(!m_activeShadow.initialized)
         {
            if(bar.openUtc >= m_activeShadow.expParentFillCloseUtc)
            {
               if(bar.openUtc != m_activeShadow.expParentFillCloseUtc) m_activeShadow.invalid = true;
               else
               {
                  CreateShadowTrade(m_activeShadow.baselineSide, bar.open, m_activeShadow.priorTrendAvail, m_activeShadow.priorTrendBps, m_activeShadow.breakout);
                  CreateShadowTrade(-m_activeShadow.baselineSide, bar.open, m_activeShadow.priorTrendAvail, m_activeShadow.priorTrendBps, m_activeShadow.fade);
                  m_activeShadow.initialized = true;
               }
            }
         }
         if(m_activeShadow.initialized && !m_activeShadow.invalid)
         {
            StepShadowTrade(m_activeShadow.breakout, bar);
            StepShadowTrade(m_activeShadow.fade, bar);
            TryRecordLabel();
         }
      }

      if(sameEt && m_pendDec1.active && !m_dayBlocked && bar.openUtc >= m_pendDec1.expObsOpenUtc)
      {
         if(bar.openUtc != m_pendDec1.expObsOpenUtc || !bar.exactMinute) { m_pendDec1.active = false; m_dayBlocked = true; }
         else
         {
            if(m_pendDec1.observedBars == 0) m_pendDec1.firstObsOpen = bar.open;
            m_pendDec1.observedBars++;
            m_pendDec1.expObsOpenUtc = bar.closeUtc;
            if(m_pendDec1.observedBars >= m_pendDec1.reqBars)
            {
               int rSide = m_pendDec1.side;
               if(m_pendDec1.branch == "high_vol_touch_vote")
               {
                  double mv = rSide * (bar.close - m_pendDec1.firstObsOpen);
                  if(!(mv > 0.0)) rSide = -rSide;
               }
               FsTPendingDec dec = m_pendDec1;
               m_pendDec1.active = false;
               ApplyFinalRefinementOrSubmit(rSide, bar.closeUtc, dec.submitActual, dec.baselineSide, dec.features, dec.signalClose, sl, host);
            }
         }
      }

      if(sameEt && m_pendDec2.active && !m_dayBlocked && bar.openUtc >= m_pendDec2.expObsOpenUtc)
      {
         if(bar.openUtc != m_pendDec2.expObsOpenUtc || !bar.exactMinute) { m_pendDec2.active = false; m_dayBlocked = true; }
         else
         {
            if(m_pendDec2.observedBars == 0) m_pendDec2.firstObsOpen = bar.open;
            m_pendDec2.observedBars++;
            m_pendDec2.expObsOpenUtc = bar.closeUtc;
            if(m_pendDec2.observedBars >= m_pendDec2.reqBars)
            {
               double obsMv = m_pendDec2.side * (bar.close - m_pendDec2.firstObsOpen);
               int fSide = (m_pendDec2.branch == "prior_session_disagreement" || obsMv > 0.0) ? -m_pendDec2.side : m_pendDec2.side;
               bool sub = m_pendDec2.submitActual;
               m_pendDec2.active = false;
               if(sub) SubmitLiveEntry(fSide, sl, host);
            }
         }
      }

      if(sameEt && bar.closeMinEt >= 960)
      {
         if(m_activeShadow.active)
         {
            if(m_activeShadow.invalid || !m_activeShadow.initialized) m_activeShadow.active = false;
            else
            {
               if(!m_activeShadow.breakout.complete) { m_activeShadow.breakout.exitPrice = bar.close - m_activeShadow.breakout.side * tickSize; m_activeShadow.breakout.complete = true; }
               if(!m_activeShadow.fade.complete) { m_activeShadow.fade.exitPrice = bar.close - m_activeShadow.fade.side * tickSize; m_activeShadow.fade.complete = true; }
               TryRecordLabel();
            }
         }
         if(!m_rthCloseRec && m_sesElig && m_cashWinInt && m_orbFinalized && m_refOpenCap)
         {
            if(!m_orbHistRec)
            {
               PushRingDouble(m_eligOrbHistBps, m_curOrbBps, 120);
               m_orbHistRec = true;
            }
            if(bar.close > 0.0)
            {
               double sRet = SafeRetBps(bar.close, m_refSesOpen);
               PushRingDouble(m_eligRthCloseHist, bar.close, 21);
               ArrayResize(m_eligSesRetHistBps, 1);
               m_eligSesRetHistBps[0] = sRet;
               m_rthCloseRec = true;
            }
         }
         m_cashExitTrig = true; m_dayBlocked = true;
         if(sl.isOpen) host.QueueMarketExit(sl, "CashClose1600ET");
         return;
      }

      if(m_cashExitTrig)
      {
         if(sl.isOpen) host.QueueMarketExit(sl, "CashExitFollowup");
         return;
      }

      bool isQtr = inCash && bar.closeMinEt >= 600 && bar.closeMinEt < 960 && (bar.closeMinEt % 15 == 0);
      if(sl.isOpen)
      {
         if(isQtr && !m_liveIlActivated && m_liveIlRiskPts > 0.0)
         {
            double closeR = sl.side * (bar.close - sl.entryPrice) / m_liveIlRiskPts;
            if(closeR >= m_liveTrigR)
            {
               double newS = FsRoundTick(sl.entryPrice + sl.side * m_liveIlRiskPts * m_liveLockR, tickSize);
               if((sl.side > 0 && newS > sl.stopPrice) || (sl.side < 0 && newS < sl.stopPrice))
                  sl.stopPrice = newS;
               m_liveIlActivated = true;
            }
         }
         if(inCash && bar.closeMinEt == 930 && !m_condExitReq && m_liveIlRiskPts > 0.0)
         {
            double closeR = sl.side * (bar.close - sl.entryPrice) / m_liveIlRiskPts;
            if(closeR < 0.0 || closeR >= 1.0)
            {
               m_condExitReq = true;
               host.QueueMarketExit(sl, "Conditional1530ET");
            }
         }
         return;
      }

      int dow = (FsDowFromYmd(m_curCashDate / 10000, (m_curCashDate / 100) % 100, m_curCashDate % 100) + 6) % 7;
      if(m_dayBlocked || dow >= 5) return;

      if(!m_orbFinalized)
      {
         if(sameEt && bar.openMinEt >= 570 && bar.openMinEt < 585)
         {
            if(bar.openMinEt != m_expNextOrbOpenMin || bar.closeMinEt != bar.openMinEt + 1) { m_dayBlocked = true; return; }
            if(m_orbBarCount == 0) m_orbOpen = bar.open;
            m_orbHigh = (m_orbBarCount == 0) ? bar.high : MathMax(m_orbHigh, bar.high);
            m_orbLow = (m_orbBarCount == 0) ? bar.low : MathMin(m_orbLow, bar.low);
            m_orbClose = bar.close;
            m_orbBarCount++; m_expNextOrbOpenMin++;
            if(bar.closeMinEt == 585)
            {
               if(m_orbBarCount != 15 || !(m_orbHigh >= m_orbLow)) { m_dayBlocked = true; return; }
               m_orbFinalized = true;
               double mid = (m_orbHigh + m_orbLow) * 0.5;
               m_curOrbBps = (mid > 0.0) ? ((m_orbHigh - m_orbLow) / mid) * 10000.0 : 0.0;
               m_curOrbQ75Avail = (ArraySize(m_eligOrbHistBps) == 120);
               if(m_curOrbQ75Avail) m_curOrbQ75Bps = LinearPercentile(m_eligOrbHistBps, 0.75);
            }
         }
         else if(sameEt && bar.closeMinEt > 585) { m_dayBlocked = true; return; }
      }

      if(m_dayBlocked || !m_orbFinalized || m_boConsumed || !isQtr) return;

      double lTrig = FsRoundTick(m_orbHigh + tickSize, tickSize);
      double sTrig = FsRoundTick(m_orbLow - tickSize, tickSize);
      if(bar.close < lTrig && bar.close > sTrig) return;

      int baseSide = (bar.close >= lTrig) ? 1 : -1;
      EvaluateAdmissionAndDirection(bar, baseSide, sl, host);
   }
};

// ---------------------------------------------------------------------------
// Module V: VaultBreak (5m RTH 08:30-15:15 CT, Long-only, 252d range)
// ---------------------------------------------------------------------------
class CVaultBreakEngine : public CFsModuleEngineBase
{
private:
   double m_noiseMult;
   double m_slAtrK;
   double m_rthRanges252[];
   double m_rthSum, m_dailyAtr, m_sesOpen, m_sesHi, m_sesLo, m_noiseUp, m_cumVol, m_cumPv, m_sesVwap;
   int    m_curRthDateCt, m_tradesToday, m_belowVwap;
   bool   m_hasSes, m_hasB5;
   int    m_b5Bucket, m_b5DateCt;
   double m_b5O, m_b5H, m_b5L, m_b5C, m_b5V;

   void Flush5mBar(const FsBarContext &curM1, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host)
   {
      m_hasB5 = false;
      if(m_b5DateCt != m_curRthDateCt)
      {
         if(m_hasSes)
         {
            double pr = m_sesHi - m_sesLo;
            if(pr > 0.0)
            {
               int n = ArraySize(m_rthRanges252);
               if(n < 252)
               {
                  ArrayResize(m_rthRanges252, n + 1);
                  m_rthRanges252[n] = pr;
                  m_rthSum += pr;
               }
               else
               {
                  m_rthSum -= m_rthRanges252[0];
                  for(int i = 1; i < 252; i++) m_rthRanges252[i - 1] = m_rthRanges252[i];
                  m_rthRanges252[251] = pr;
                  m_rthSum += pr;
               }
            }
         }
         int cnt = ArraySize(m_rthRanges252);
         m_dailyAtr = (cnt < 252) ? 0.0 : (m_rthSum / cnt);
         m_curRthDateCt = m_b5DateCt;
         m_sesOpen = m_b5O; m_sesHi = m_b5H; m_sesLo = m_b5L;
         m_noiseUp = (m_dailyAtr <= 0.0) ? 0.0 : (m_sesOpen + m_noiseMult * m_dailyAtr);
         m_cumVol = 0.0; m_cumPv = 0.0; m_sesVwap = m_b5C;
         m_tradesToday = 0; m_belowVwap = 0; m_hasSes = true;
      }
      if(!m_hasSes) return;

      if(m_b5H > m_sesHi) m_sesHi = m_b5H;
      if(m_b5L < m_sesLo) m_sesLo = m_b5L;
      if(m_b5V > 0.0) { m_cumPv += ((m_b5H + m_b5L + m_b5C) / 3.0) * m_b5V; m_cumVol += m_b5V; }
      m_sesVwap = (m_cumVol <= 0.0) ? m_b5C : (m_cumPv / m_cumVol);
      m_belowVwap = (m_b5C < m_sesVwap) ? (m_belowVwap + 1) : 0;

      int hhmmEt = curM1.closeHhmmEt;
      if(sl.isOpen)
      {
         if(hhmmEt >= 1550) { host.QueueMarketExit(sl, "V_X_TIME"); return; }
         if(m_belowVwap >= 2) { host.QueueMarketExit(sl, "V_X_VWAP"); return; }
         return;
      }

      if(m_dailyAtr <= 0.0 || m_tradesToday >= 3) return;
      MqlDateTime mCt;
      TimeToStruct(curM1.closeCt, mCt);
      if(mCt.hour == 9) return;
      if(hhmmEt < 945 || hhmmEt > 1500) return;
      if(m_b5C <= m_noiseUp || m_b5C <= m_sesVwap) return;
      if(!MathIsValidNumber(atr20Session) || atr20Session <= 0.0) return;

      if(host.QueueMarketEntry(sl, 1, m_slAtrK * atr20Session, EMPTY_VALUE, EMPTY_VALUE))
         m_tradesToday++;
   }

public:
   CVaultBreakEngine(double noiseMult = 0.25, double slAtrK = 0.30)
      : CFsModuleEngineBase("V_nm25_noCap_mae30"),
        m_noiseMult(noiseMult), m_slAtrK(slAtrK),
        m_rthSum(0.0), m_dailyAtr(0.0), m_sesOpen(0.0), m_sesHi(0.0), m_sesLo(0.0), m_noiseUp(0.0),
        m_cumVol(0.0), m_cumPv(0.0), m_sesVwap(0.0),
        m_curRthDateCt(-1), m_tradesToday(0), m_belowVwap(0),
        m_hasSes(false), m_hasB5(false), m_b5Bucket(-1), m_b5DateCt(-1),
        m_b5O(0.0), m_b5H(0.0), m_b5L(0.0), m_b5C(0.0), m_b5V(0.0) {}

   int RthRangesCount() { return ArraySize(m_rthRanges252); }

   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) override
   {
      int ctMin = bar.openMinCt;
      if(ctMin < 510 || ctMin >= 915)
      {
         if(m_hasB5) Flush5mBar(bar, atr20Session, sl, host);
         return;
      }

      int bId = (ctMin - 510) / 5;
      if(m_hasB5 && (m_b5DateCt != bar.openDateCt || m_b5Bucket != bId))
         Flush5mBar(bar, atr20Session, sl, host);

      if(!m_hasB5)
      {
         m_hasB5 = true; m_b5DateCt = bar.openDateCt; m_b5Bucket = bId;
         m_b5O = bar.open; m_b5H = bar.high; m_b5L = bar.low; m_b5C = bar.close; m_b5V = bar.volume;
      }
      else
      {
         m_b5H = MathMax(m_b5H, bar.high); m_b5L = MathMin(m_b5L, bar.low); m_b5C = bar.close; m_b5V += bar.volume;
      }

      if((bar.closeMinEt % 5) == 0)
         Flush5mBar(bar, atr20Session, sl, host);
   }
};

// ---------------------------------------------------------------------------
// Module W: VwapCross (1m ETH, Long-only, exit_on_vwap_cross=false)
// ---------------------------------------------------------------------------
class CVwapCrossEngine : public CFsModuleEngineBase
{
private:
   double m_slAtrK;
   bool   m_enableTrail;
   double m_vwapHist[];
   double m_cumPv, m_cumVol, m_sesVwap;
   int    m_sigSide;

public:
   CVwapCrossEngine(double slAtrK = 0.25, bool enableTrail = false)
      : CFsModuleEngineBase("W_slope_allowReFalse_ATR25"),
        m_slAtrK(slAtrK), m_enableTrail(enableTrail),
        m_cumPv(0.0), m_cumVol(0.0), m_sesVwap(0.0), m_sigSide(0) {}

   virtual void UpdateM1OverlayProtectionsOnClose(FsVirtualSleeve &sl, const FsBarContext &bar) override
   {
      if(m_enableTrail && sl.isOpen && sl.riskPts > 0.0)
      {
         double trigs[2] = { 1.5, 2.5 };
         double locks[2] = { 0.5, 1.5 };
         for(int t = 0; t < 2; t++)
         {
            if(sl.maxFavPts >= trigs[t] * sl.riskPts)
            {
               double cand = sl.entryPrice + locks[t] * sl.riskPts;
               if(cand > sl.stopPrice) sl.stopPrice = cand;
            }
         }
      }
   }

   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) override
   {
      int t1 = bar.closeHhmmssCt;
      int t2 = bar.nextMinHhmmssCt;
      bool inWin = (t1 >= 83000 && t1 < 150000);
      if(inWin)
      {
         if(t1 == 83000) { m_cumPv = 0.0; m_cumVol = 0.0; }
         if(bar.volume > 0.0)
         {
            m_cumPv += ((bar.high + bar.low + bar.close) / 3.0) * bar.volume;
            m_cumVol += bar.volume;
         }
         m_sesVwap = (m_cumVol > 0.0) ? (m_cumPv / m_cumVol) : bar.close;
      }

      int n = ArraySize(m_vwapHist);
      if(n < 260) { ArrayResize(m_vwapHist, n + 1); m_vwapHist[n] = m_sesVwap; }
      else { for(int i = 1; i < 260; i++) m_vwapHist[i - 1] = m_vwapHist[i]; m_vwapHist[259] = m_sesVwap; }

      if(t2 >= 150000)
      {
         if(sl.isOpen) host.QueueMarketExit(sl, "EOD");
         m_sigSide = 0;
         return;
      }
      if(!inWin || m_cumVol <= 0.0) return;

      bool above = (bar.close > m_sesVwap);
      bool below = (bar.close < m_sesVwap);
      if(!sl.isOpen && !sl.hasPendingEntry && t2 == 83100)
      {
         if(above)
         {
            m_sigSide = 1;
            int vn = ArraySize(m_vwapHist);
            bool slopeOk = (vn > 20 && (m_sesVwap - m_vwapHist[vn - 21]) >= 0.0);
            if(slopeOk && MathIsValidNumber(atr20Session) && atr20Session > 0.0)
               host.QueueMarketEntry(sl, 1, m_slAtrK * atr20Session, EMPTY_VALUE, EMPTY_VALUE);
         }
         else if(below) m_sigSide = 2;
         return;
      }
      if(m_sigSide == 1 && below) m_sigSide = 2;
      else if(m_sigSide == 2 && above) m_sigSide = 1;
   }
};

// ---------------------------------------------------------------------------
// Module N: NDayLong (1m ETH + completed ETH daily highs/range)
// ---------------------------------------------------------------------------
class CNDayLongEngine : public CFsModuleEngineBase
{
private:
   int    m_numDays;
   double m_slAtrK;
   double m_dHighs[];
   double m_priorRange, m_dayHi;
   double m_rthVwapHist[];
   double m_cumPv, m_cumVol;
   int    m_acceptCloses, m_closesBelowDayHi;
   bool   m_wasLong;
   double m_lastBreakoutLvl;

public:
   CNDayLongEngine(int numDays = 5, double slAtrK = 0.25)
      : CFsModuleEngineBase("N_d5_fbTrue_ATR25"),
        m_numDays(numDays), m_slAtrK(slAtrK),
        m_priorRange(EMPTY_VALUE), m_dayHi(EMPTY_VALUE),
        m_cumPv(0.0), m_cumVol(0.0), m_acceptCloses(0), m_closesBelowDayHi(0),
        m_wasLong(false), m_lastBreakoutLvl(0.0) {}

   virtual void OnNewEthSession(int d0, double h, double l, double c, int d1) override
   {
      if(d0 > 0 && h > l)
      {
         m_priorRange = h - l;
         int n = ArraySize(m_dHighs);
         if(n < m_numDays)
         {
            ArrayResize(m_dHighs, n + 1);
            m_dHighs[n] = h;
         }
         else
         {
            for(int i = 1; i < n; i++) m_dHighs[i - 1] = m_dHighs[i];
            m_dHighs[n - 1] = h;
         }
         if(ArraySize(m_dHighs) == m_numDays)
         {
            double mx = -1e18;
            for(int i = 0; i < m_numDays; i++) if(m_dHighs[i] > mx) mx = m_dHighs[i];
            m_dayHi = mx;
         }
      }
   }

   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) override
   {
      int ct = bar.closeHhmmssCt;
      int t2 = bar.nextMinHhmmssCt;
      if(ct == 83000) { m_cumPv = 0.0; m_cumVol = 0.0; }
      double vVal;
      if(ct >= 83000 && ct < 160000)
      {
         m_cumPv += ((bar.high + bar.low + bar.close) / 3.0) * bar.volume;
         m_cumVol += bar.volume;
         vVal = (m_cumVol > 0.0) ? (m_cumPv / m_cumVol) : bar.close;
      }
      else
      {
         int nvh = ArraySize(m_rthVwapHist);
         vVal = (nvh == 0) ? bar.close : m_rthVwapHist[nvh - 1];
      }

      int n = ArraySize(m_rthVwapHist);
      if(n < 60) { ArrayResize(m_rthVwapHist, n + 1); m_rthVwapHist[n] = vVal; }
      else { for(int i = 1; i < 60; i++) m_rthVwapHist[i - 1] = m_rthVwapHist[i]; m_rthVwapHist[59] = vVal; }

      bool maintBlocked = (bar.dowCtMon0 == 5) || (bar.dowCtMon0 == 4 && ct >= 154400)
          || (bar.dowCtMon0 == 6 && ct < 170100) || (ct >= 154400 && ct < 170100);
      if(maintBlocked)
      {
         sl.hasPendingEntry = false;
         sl.pendingEntryIsStopOrder = false;
         if(sl.isOpen) { host.QueueMarketExit(sl, "DAILY_FUTURES_CLOSE"); return; }
      }

      if(t2 >= 160000)
      {
         sl.hasPendingEntry = false;
         sl.pendingEntryIsStopOrder = false;
         if(sl.isOpen) host.QueueMarketExit(sl, "EOD");
         return;
      }

      if(m_dayHi == EMPTY_VALUE || !MathIsValidNumber(m_dayHi) || m_priorRange == EMPTY_VALUE || !(m_priorRange > 0.0)) return;

      if(sl.isOpen)
      {
         if(bar.close <= sl.entryPrice - m_priorRange) { host.QueueMarketExit(sl, "VOLLOSS"); return; }
         if(!m_wasLong) { m_wasLong = true; m_closesBelowDayHi = 0; }
         if(bar.close < m_lastBreakoutLvl) m_closesBelowDayHi++; else m_closesBelowDayHi = 0;
         if(m_closesBelowDayHi >= 6) { host.QueueMarketExit(sl, "FAILED"); return; }
         return;
      }

      m_wasLong = false; m_closesBelowDayHi = 0;
      if(sl.pendingEntryIsStopOrder)
      {
         if(ct >= 154500) sl.pendingEntryIsStopOrder = false;
         return;
      }
      if(maintBlocked || sl.hasPendingEntry || ct >= 154500) return;

      int vn = ArraySize(m_rthVwapHist);
      if(ct < 83000 || ct >= 160000 || vn < 16) return;
      double vPrev = m_rthVwapHist[vn - 16];
      if(!(bar.close > vVal && vVal > vPrev)) return;

      if(bar.close > m_dayHi + 4.0) m_acceptCloses++; else m_acceptCloses = 0;
      if(m_acceptCloses < 2) return;

      if(!MathIsValidNumber(atr20Session) || atr20Session <= 0.0) return;
      m_lastBreakoutLvl = m_dayHi;
      if(m_dayHi <= bar.close)
         host.QueueMarketEntry(sl, 1, m_slAtrK * atr20Session, EMPTY_VALUE, EMPTY_VALUE);
      else
         host.QueueStopEntry(sl, 1, FsRoundTick(m_dayHi, tickSize), m_slAtrK * atr20Session);
   }
};

// ---------------------------------------------------------------------------
// Module SOMEOD: SessionOpenMomentum EOD (M5 NY+7h clock, MQL5 SMA ATR14)
// ---------------------------------------------------------------------------
class CSessionOpenMomentumEngine : public CFsModuleEngineBase
{
private:
   bool     m_hasB5;
   long     m_curBucketId;
   datetime m_b5OpenNy;
   double   m_b5H, m_b5L, m_b5C;
   int      m_barsM5Count;
   double   m_ema12, m_ema120, m_prevClose, m_atr14;
   double   m_trWin[];
   int      m_blockedDay;

   void FlushM5Bar(FsVirtualSleeve &sl, IFsSignalHost *host)
   {
      m_hasB5 = false;
      double cl = m_b5C;
      double tr = (m_prevClose == EMPTY_VALUE) ? (m_b5H - m_b5L)
         : MathMax(m_b5H - m_b5L, MathMax(MathAbs(m_b5H - m_prevClose), MathAbs(m_b5L - m_prevClose)));
      m_prevClose = cl;
      m_barsM5Count++;

      m_ema12  = (m_ema12  == EMPTY_VALUE) ? cl : ((2.0 / 13.0)  * cl + (1.0 - 2.0 / 13.0)  * m_ema12);
      m_ema120 = (m_ema120 == EMPTY_VALUE) ? cl : ((2.0 / 121.0) * cl + (1.0 - 2.0 / 121.0) * m_ema120);

      int n = ArraySize(m_trWin);
      if(n < 14) { ArrayResize(m_trWin, n + 1); m_trWin[n] = tr; }
      else { for(int i = 1; i < 14; i++) m_trWin[i - 1] = m_trWin[i]; m_trWin[13] = tr; }
      if(ArraySize(m_trWin) == 14)
      {
         double s = 0.0;
         for(int i = 0; i < 14; i++) s += m_trWin[i];
         m_atr14 = s / 14.0;
      }

      datetime closedOpenNy  = m_b5OpenNy;
      datetime closedCloseNy = closedOpenNy + 300;
      datetime srvClose      = closedCloseNy + 7 * 3600;

      MqlDateTime mOpenNy, mCloseNy, mSrv;
      TimeToStruct(closedOpenNy, mOpenNy);
      TimeToStruct(closedCloseNy, mCloseNy);
      TimeToStruct(srvClose, mSrv);

      int curSrvDay = mSrv.year * 1000 + mSrv.day_of_year;
      int closeMinNy = mCloseNy.hour * 60 + mCloseNy.min;

      if(sl.isOpen)
      {
         if(closeMinNy >= 955) { host.QueueMarketExit(sl, "EOD_CLOSE"); return; }
         if(m_ema120 != EMPTY_VALUE && sl.maxFavPts >= 0.5 * sl.riskPts)
         {
            double cand = FsRoundTick(m_ema120, tickSize);
            if(sl.side > 0 && cand > sl.stopPrice + 0.01 && cand < cl)
               sl.stopPrice = cand;
            else if(sl.side < 0 && cand < sl.stopPrice - 0.01 && cand > cl)
               sl.stopPrice = cand;
         }
         return;
      }

      if(m_barsM5Count < 122 || m_atr14 == EMPTY_VALUE || !(m_atr14 > 0.0) || m_ema12 == EMPTY_VALUE) return;
      if(mOpenNy.hour == 9 && mOpenNy.min == 30 && m_blockedDay != curSrvDay)
      {
         int side = (cl > m_ema12) ? 1 : ((cl < m_ema12) ? -1 : 0);
         if(side != 0)
         {
            m_blockedDay = curSrvDay;
            host.QueueMarketEntry(sl, side, FsRoundTick(8.0 * m_atr14, tickSize), EMPTY_VALUE, EMPTY_VALUE);
         }
      }
   }

public:
   CSessionOpenMomentumEngine()
      : CFsModuleEngineBase("SOMEOD_ext_NQ"),
        m_hasB5(false), m_curBucketId(-1), m_b5OpenNy(0), m_b5H(0.0), m_b5L(0.0), m_b5C(0.0),
        m_barsM5Count(0), m_ema12(EMPTY_VALUE), m_ema120(EMPTY_VALUE), m_prevClose(EMPTY_VALUE),
        m_atr14(EMPTY_VALUE), m_blockedDay(-1) {}

   virtual void ProcessBar(const FsBarContext &bar, double atr20Session, FsVirtualSleeve &sl, IFsSignalHost *host) override
   {
      datetime srvOpenNy = bar.openNy + 7 * 3600;
      long bId = (long)srvOpenNy / 300;
      if(m_hasB5 && m_curBucketId != bId)
         FlushM5Bar(sl, host);

      if(!m_hasB5)
      {
         m_hasB5 = true; m_curBucketId = bId; m_b5OpenNy = bar.openNy;
         m_b5H = bar.high; m_b5L = bar.low; m_b5C = bar.close;
      }
      else
      {
         m_b5H = MathMax(m_b5H, bar.high); m_b5L = MathMin(m_b5L, bar.low); m_b5C = bar.close;
      }

      if(((long)bar.closeNy % 300) == 0)
         FlushM5Bar(sl, host);
   }
};

#endif
//+------------------------------------------------------------------+
