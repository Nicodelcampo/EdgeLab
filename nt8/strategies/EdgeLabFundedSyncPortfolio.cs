#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Text;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Core;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public enum FundedSyncAccountMode
    {
        Evaluation = 0,
        Funded = 1
    }

    public enum FundedSyncCollisionPolicy
    {
        Netting = 0,
        VetoOpposite = 1,
        Independent = 2
    }

    /// <summary>
    /// Unified NinjaTrader 8 portfolio executor for P_OPT_SF_v2 FUNDEDSYNC (NQ / MNQ).
    /// Encodes all 7 uncorrelated causal modules (R, Z, T, V, W, N, SOMEOD) with W5 weights,
    /// causal MaxOpenR = 3.0 cap, Virtual Sleeve + Net Position Synchronizer, Hybrid NQ/MNQ split,
    /// Hard Flatten 16:40 ET, Eval Consistency Daily Cap, Daily Loss Limit, and CSV parity logger.
    ///
    /// IMPORTANT DATA REQUIREMENT:
    /// Attach to NQ or MNQ 1-Minute ETH chart with AT LEAST 500 trading days (~2 years) loaded
    /// so T quarterly KNN accumulates >= 100 exclusive shadow rows and V accumulates 252 RTH ranges.
    /// Verified 2026-11-22: W_slope_allowReFalse_ATR25 without trail (EnableWTrail = false default).
    /// </summary>
    public class EdgeLabFundedSyncPortfolio : Strategy
    {
        private sealed class VirtualSleeve
        {
            public string ModuleId;
            public double WeightW5;
            public bool Enabled;
            public bool IsOpen;
            public int Side;
            public int Contracts;
            public double AppliedW;
            public double EntryPrice;
            public double InitialStopPrice;
            public double StopPrice;
            public double TargetPrice;
            public double RiskPts;
            public double MaxFavPts;
            public bool BeActivated;
            public double BeLockTriggerR;
            public double IlLockTriggerR;
            public double IlLockLevelR;
            public DateTime EntryNyTime;
            public int EntrySessionDate;
        }

        private sealed class ShadowObs
        {
            public int QuarterKey;
            public double[] Features;
            public double ReturnR;
        }

        private static readonly string[] CsvHeaderCols =
        {
            "fecha_int", "a5", "modulo", "w_w5", "side", "en_ny", "ex_ny",
            "entry_price", "stop_price", "exit_price", "riesgo_pts", "pnl_pts",
            "R_bruto", "R_neto_mini", "exit_name"
        };

        #region State & Aggregators
        private TimeZoneInfo _chartTz;
        private TimeZoneInfo _nyTz;
        private TimeZoneInfo _ctTz;

        private bool _hasSecondaryMnq;
        private bool _csvHeaderWritten;
        private string _resolvedCsvPath;
        private bool _hardFlattenedToday;
        private bool _dailyCapTriggeredToday;
        private bool _dailyLossTriggeredToday;
        private int _currentSessionDate;
        private int _currentCalDateNy;
        private double _realizedSessionUsd;

        // Session OHLC & ATR20_session (causal over completed CME 18:00 ET sessions)
        private double _sesHigh = double.MinValue;
        private double _sesLow = double.MaxValue;
        private double _sesOpen = double.NaN;
        private double _sesClose = double.NaN;
        private readonly Queue<double> _completedSesRanges = new Queue<double>();
        private readonly Queue<double> _completedSesHighs = new Queue<double>();
        private readonly Queue<double> _completedSesCloses = new Queue<double>();
        private double _atr20Session = double.NaN;
        private double _priorSesRange = double.NaN;
        private double _priorSesClose = double.NaN;
        private double _prior5DayHigh = double.NaN;
        private double _priorSesRetBps;
        private double _priorRet5Bps;
        private double _priorRet20Bps;

        // RTH stats for V (252d RTH range) & ORB 09:30-09:45 ET for T
        private double _rthDayHigh = double.MinValue;
        private double _rthDayLow = double.MaxValue;
        private double _rthSessionOpen = double.NaN;
        private bool _rthActive;
        private readonly Queue<double> _rth252Ranges = new Queue<double>();
        private double _vDailyAtr252 = double.NaN;
        private int _vTradesToday;

        // RTH VWAP & 1m closes for W / V / T / R
        private double _vwapCumPv;
        private double _vwapCumVol;
        private double _rthVwap = double.NaN;
        private readonly List<double> _m1VwapHist = new List<double>();
        private readonly List<double> _m1CloseHist = new List<double>();
        private bool _wTradedToday;

        // Module T (ORB + completed 15m breakout + 14-feature KNN + shadow bank)
        private double _orbHigh = double.MinValue;
        private double _orbLow = double.MaxValue;
        private int _orbBarsCount;
        private long _t15CurBucket = -1;
        private double _t15O, _t15H, _t15L, _t15C;
        private bool _tTakenToday;
        private int _tTouchCount;
        private double _tPriorSesOpenGapBps;
        private int _tPendingDelayBars;
        private int _tPendingSide;
        private bool _tPendingShadowActive;
        private double _tPendingShadowEntry;
        private double _tPendingShadowStopPts;
        private double _tPendingShadowTargetR;
        private double[] _tPendingFeatures;
        private readonly List<ShadowObs> _tShadowBank = new List<ShadowObs>();
        private readonly List<ShadowObs> _tActiveModelRows = new List<ShadowObs>();
        private double[] _tFeatMean = new double[14];
        private double[] _tFeatStd = new double[14];
        private int _tLastRefitQuarter = -1;

        // Module R (10m ETH oscillator)
        private long _rCurBucket = -1;
        private double _rCurO, _rCurH, _rCurL, _rCurC;
        private int _rBarCount;
        private double _rEma21 = double.NaN;
        private double _rPrevEmaClose = double.NaN;
        private double _rAtr14 = double.NaN;
        private readonly List<double> _rTrSeed = new List<double>();
        private double _rPrevOsc = double.NaN;
        private double _rOsc = double.NaN;

        // Module Z (15m RTH EMA20 + touch-free + efficiency >= 40%) & N (15m RTH VWAP slope + 5d high)
        private long _rth15CurBucket = -1;
        private double _rth15O, _rth15H, _rth15L, _rth15C;
        private double _rth15VwapPrev = double.NaN;
        private double _rth15VwapCur = double.NaN;
        private readonly List<double> _zCloseSeed = new List<double>();
        private double _zEma20 = double.NaN;
        private double _zPrevSesEndEma20 = double.NaN;
        private bool _zPrevSesTouchFree;
        private bool _zCurSesTouchFree = true;
        private int _zCurSesBucketCount;
        private double _zTradeTargetEma = double.NaN;
        private bool _zTakenToday;
        private int _nClosesAbove5dHi;
        private int _nClosesBelowDayHi;
        private bool _nTakenToday;
        private int _nConsecBelowVwap;
        private int _vConsecBelowVwap;

        // Module V (5m RTH bar closes)
        private long _v5CurBucket = -1;
        private double _v5O, _v5H, _v5L, _v5C;

        // Module SOMEOD (5m NY+7h MQL5 EMA12, EMA120, SMA-ATR14)
        private long _som5CurBucket = -1;
        private double _som5O, _som5H, _som5L, _som5C;
        private DateTime _som5StartNy;
        private int _som5BarCount;
        private double _somEma12 = double.NaN;
        private double _somEma120 = double.NaN;
        private double _somPrevClose = double.NaN;
        private readonly Queue<double> _somTrWindow = new Queue<double>();
        private double _somAtr14 = double.NaN;
        private bool _somTradedToday;

        // 7 virtual sleeves
        private readonly Dictionary<string, VirtualSleeve> _sleeves = new Dictionary<string, VirtualSleeve>();
        private readonly string[] _moduleOrder =
        {
            "R_osc30_end660_ATR50",
            "Z_b15_e20_eff40_ATR50",
            "T_stop100_BE15R_calFalse",
            "V_nm25_noCap_mae30",
            "W_slope_allowReFalse_ATR25",
            "N_d5_fbTrue_ATR25",
            "SOMEOD_ext_NQ"
        };
        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "P_OPT_SF_v2 FUNDEDSYNC Portfolio (7 causal modules, W5 weights, MaxOpenR=3, Prop compliance).";
                Name = "EdgeLabFundedSyncPortfolio";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 2;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 1;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                IsInstantiatedOnEachOptimizationIteration = true;

                // Prop Account & Risk Sizing
                AccountMode = FundedSyncAccountMode.Evaluation;
                EvalRisk1R_USD = 650.0;
                FundedRisk1R_USD = 450.0;
                MaxOpenR = 3.0;
                MaxMicroContracts = 100;
                CollisionPolicy = FundedSyncCollisionPolicy.Netting;
                SecondaryMnqSymbol = string.Empty;

                // Compliance Protections
                HardFlattenHHMM_ET = 1640;
                EnforceEvalDailyCap = true;
                EvalDailyCapUSD = 3420.0;
                DailyLossLimitUSD = 2700.0;
                EnableWTrail = false;

                // Parity & Module Toggles
                EnableR = true;
                EnableZ = true;
                EnableT = true;
                EnableV = true;
                EnableW = true;
                EnableN = true;
                EnableSOMEOD = true;

                // Learned Causal W5 Weights (DESC 2020-2026-09)
                WeightR = 1.653354;
                WeightZ = 1.965598;
                WeightT = 0.768284;
                WeightV = 1.019769;
                WeightW = 0.915674;
                WeightN = 1.252428;
                WeightSOMEOD = 0.911410;

                EnableParityCsvLog = false;
                ParityCsvFileName = "EdgeLab_FundedSync_ParityTrades.csv";
            }
            else if (State == State.Configure)
            {
                if (!string.IsNullOrWhiteSpace(SecondaryMnqSymbol))
                {
                    AddDataSeries(SecondaryMnqSymbol.Trim(), BarsPeriodType.Minute, 1);
                    _hasSecondaryMnq = true;
                }
            }
            else if (State == State.DataLoaded)
            {
                _nyTz = ResolveTz("Eastern Standard Time");
                _ctTz = ResolveTz("Central Standard Time");
                _chartTz = (Bars != null && Bars.TradingHours != null && Bars.TradingHours.TimeZoneInfo != null)
                    ? Bars.TradingHours.TimeZoneInfo
                    : (Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local);

                InitSleeves();
                _resolvedCsvPath = Path.Combine(NinjaTrader.Core.Globals.UserDataDir,
                    string.IsNullOrWhiteSpace(ParityCsvFileName) ? "EdgeLab_FundedSync_ParityTrades.csv" : ParityCsvFileName.Trim());
                Print("EdgeLabFundedSyncPortfolio initialized. Note: load >= 500 trading days (~2y M1) for full T-KNN & V-ATR252 warmup.");
            }
        }

        private static TimeZoneInfo ResolveTz(string winId)
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById(winId); }
            catch { return TimeZoneInfo.Local; }
        }

        private void InitSleeves()
        {
            _sleeves.Clear();
            RegisterSleeve("R_osc30_end660_ATR50", WeightR, EnableR);
            RegisterSleeve("Z_b15_e20_eff40_ATR50", WeightZ, EnableZ);
            RegisterSleeve("T_stop100_BE15R_calFalse", WeightT, EnableT);
            RegisterSleeve("V_nm25_noCap_mae30", WeightV, EnableV);
            RegisterSleeve("W_slope_allowReFalse_ATR25", WeightW, EnableW);
            RegisterSleeve("N_d5_fbTrue_ATR25", WeightN, EnableN);
            RegisterSleeve("SOMEOD_ext_NQ", WeightSOMEOD, EnableSOMEOD);
        }

        private void RegisterSleeve(string id, double weight, bool enabled)
        {
            _sleeves[id] = new VirtualSleeve
            {
                ModuleId = id,
                WeightW5 = weight,
                Enabled = enabled
            };
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 1)
                return;

            DateTime barNy = TimeZoneInfo.ConvertTime(Time[0], _chartTz, _nyTz);
            DateTime barCt = TimeZoneInfo.ConvertTime(Time[0], _chartTz, _ctTz);
            int nyHHMM = barNy.Hour * 100 + barNy.Minute;
            int ctHHMM = barCt.Hour * 100 + barCt.Minute;
            int nyMin = barNy.Hour * 60 + barNy.Minute;
            int ctMin = barCt.Hour * 60 + barCt.Minute;

            int calDateNy = barNy.Year * 10000 + barNy.Month * 100 + barNy.Day;
            DateTime cmeSesDt = barNy.AddHours(6).Date;
            int sesDate = cmeSesDt.Year * 10000 + cmeSesDt.Month * 100 + cmeSesDt.Day;

            if (sesDate != _currentSessionDate)
                OnNewCmeSession(sesDate);

            if (calDateNy != _currentCalDateNy)
            {
                _currentCalDateNy = calDateNy;
                ResetDailyNyState(barNy);
            }

            // Track CME session OHLC strictly
            if (double.IsNaN(_sesOpen))
                _sesOpen = Open[0];
            _sesHigh = Math.Max(_sesHigh, High[0]);
            _sesLow = Math.Min(_sesLow, Low[0]);
            _sesClose = Close[0];

            // Track RTH session (09:30-16:00 ET / 08:30-15:00 CT) & ORB (09:30-09:45 ET)
            UpdateRthAndOrb(nyMin, barNy);
            UpdateM1History(Close[0]);

            // Manage active stops, BE, trailing, and timed exits on already open sleeves before signals
            ManageOpenSleeves(barNy, nyHHMM, ctHHMM);

            // Check compliance locks (Hard flatten 16:40 ET, Eval Daily Cap, Daily Loss Limit)
            CheckComplianceLocks(barNy, nyHHMM);

            // Process sub-timeframe bars and generate signals if trading is permitted today
            bool entriesAllowed = !_hardFlattenedToday && !_dailyCapTriggeredToday && !_dailyLossTriggeredToday
                                  && nyHHMM < HardFlattenHHMM_ET;

            ProcessModuleR_10m(barNy, nyMin, entriesAllowed);
            ProcessModuleZandN_15m(barNy, barCt, ctMin, nyHHMM, ctHHMM, entriesAllowed);
            ProcessModuleV_5m(barNy, barCt, nyMin, ctMin, nyHHMM, entriesAllowed);
            ProcessModuleW_1m(barNy, ctHHMM, entriesAllowed);
            ProcessModuleT_Orb(barNy, nyMin, entriesAllowed);
            ProcessModuleSOMEOD_5m(barNy, entriesAllowed);

            // Synchronize aggregate virtual net position to NinjaTrader Orders
            SynchronizeNetPosition(barNy);
        }

        private void OnNewCmeSession(int newSesDate)
        {
            if (_currentSessionDate > 0 && _sesHigh > _sesLow && _sesHigh > -1e12 && _sesLow < 1e12)
            {
                double rng = _sesHigh - _sesLow;
                double prevC = _sesClose;
                _priorSesRange = rng;

                _completedSesRanges.Enqueue(rng);
                if (_completedSesRanges.Count > 20)
                    _completedSesRanges.Dequeue();
                double sumR = 0.0;
                foreach (double r in _completedSesRanges) sumR += r;
                if (_completedSesRanges.Count >= 5)
                    _atr20Session = sumR / _completedSesRanges.Count;

                _completedSesHighs.Enqueue(_sesHigh);
                if (_completedSesHighs.Count > 5)
                    _completedSesHighs.Dequeue();
                double hi5 = double.MinValue;
                foreach (double h in _completedSesHighs) hi5 = Math.Max(hi5, h);
                if (_completedSesHighs.Count >= 5)
                    _prior5DayHigh = hi5;

                if (!double.IsNaN(_priorSesClose) && _priorSesClose > 0.0)
                    _priorSesRetBps = 10000.0 * (prevC - _priorSesClose) / _priorSesClose;

                _completedSesCloses.Enqueue(prevC);
                if (_completedSesCloses.Count > 21)
                    _completedSesCloses.Dequeue();
                double[] clsArr = _completedSesCloses.ToArray();
                int nC = clsArr.Length;
                _priorRet5Bps = (nC >= 6 && clsArr[nC - 6] > 0) ? 10000.0 * (prevC - clsArr[nC - 6]) / clsArr[nC - 6] : 0.0;
                _priorRet20Bps = (nC >= 21 && clsArr[nC - 21] > 0) ? 10000.0 * (prevC - clsArr[nC - 21]) / clsArr[nC - 21] : 0.0;
                _priorSesClose = prevC;
            }

            _currentSessionDate = newSesDate;
            _sesHigh = double.MinValue;
            _sesLow = double.MaxValue;
            _sesOpen = double.NaN;
            _hardFlattenedToday = false;
            _dailyCapTriggeredToday = false;
            _dailyLossTriggeredToday = false;
            _realizedSessionUsd = 0.0;

            if (_rthActive && _rthDayHigh > _rthDayLow && _rthDayHigh > -1e12)
            {
                _rth252Ranges.Enqueue(_rthDayHigh - _rthDayLow);
                if (_rth252Ranges.Count > 252)
                    _rth252Ranges.Dequeue();
                double sV = 0.0;
                foreach (double v in _rth252Ranges) sV += v;
                if (_rth252Ranges.Count >= 20)
                    _vDailyAtr252 = sV / _rth252Ranges.Count;
            }

            // Reset Z & N session trackers
            if (_zCurSesBucketCount >= 10 && !double.IsNaN(_zEma20))
            {
                _zPrevSesTouchFree = _zCurSesTouchFree;
                _zPrevSesEndEma20 = _zEma20;
            }
            _zCurSesTouchFree = true;
            _zCurSesBucketCount = 0;
            _rthDayHigh = double.MinValue;
            _rthDayLow = double.MaxValue;
            _rthSessionOpen = double.NaN;
            _rthActive = false;
            _vwapCumPv = 0.0;
            _vwapCumVol = 0.0;
            _rthVwap = double.NaN;
            _m1VwapHist.Clear();
            _rth15VwapPrev = double.NaN;
            _rth15VwapCur = double.NaN;
        }

        private void ResetDailyNyState(DateTime barNy)
        {
            _orbHigh = double.MinValue;
            _orbLow = double.MaxValue;
            _orbBarsCount = 0;
            _t15CurBucket = -1;
            _tTakenToday = false;
            _tTouchCount = 0;
            _tPendingDelayBars = 0;
            _vTradesToday = 0;
            _vConsecBelowVwap = 0;
            _wTradedToday = false;
            _zTakenToday = false;
            _nTakenToday = false;
            _nClosesAbove5dHi = 0;
            _nClosesBelowDayHi = 0;
            _somTradedToday = false;
        }

        private void UpdateRthAndOrb(int nyMin, DateTime barNy)
        {
            // RTH [09:30..16:00] ET
            if (nyMin >= 570 && nyMin < 960)
            {
                if (!_rthActive)
                {
                    _rthActive = true;
                    _rthSessionOpen = Open[0];
                    _vwapCumPv = 0.0;
                    _vwapCumVol = 0.0;
                    if (!double.IsNaN(_priorSesClose) && _priorSesClose > 0)
                        _tPriorSesOpenGapBps = 10000.0 * (Open[0] - _priorSesClose) / _priorSesClose;
                }
                _rthDayHigh = Math.Max(_rthDayHigh, High[0]);
                _rthDayLow = Math.Min(_rthDayLow, Low[0]);

                double typ = (High[0] + Low[0] + Close[0]) / 3.0;
                double vol = Math.Max(Volume[0], 1.0);
                _vwapCumPv += typ * vol;
                _vwapCumVol += vol;
                _rthVwap = _vwapCumPv / _vwapCumVol;
                _m1VwapHist.Add(_rthVwap);
                if (_m1VwapHist.Count > 60)
                    _m1VwapHist.RemoveAt(0);
            }

            // ORB [09:30..09:45] ET = 15 x 1m bars
            if (nyMin >= 570 && nyMin < 585)
            {
                _orbHigh = Math.Max(_orbHigh, High[0]);
                _orbLow = Math.Min(_orbLow, Low[0]);
                _orbBarsCount++;
            }
            else if (nyMin >= 585 && nyMin < 945 && _orbHigh > _orbLow)
            {
                if (Low[0] <= _orbHigh + 0.25 && High[0] >= _orbLow - 0.25)
                    _tTouchCount++;
            }
        }

        private void UpdateM1History(double c)
        {
            _m1CloseHist.Add(c);
            if (_m1CloseHist.Count > 120)
                _m1CloseHist.RemoveAt(0);
        }

        private double GetVwapSlope20()
        {
            int cnt = _m1VwapHist.Count;
            if (cnt < 21) return 0.0;
            return _m1VwapHist[cnt - 1] - _m1VwapHist[cnt - 21];
        }

        private void ManageOpenSleeves(DateTime barNy, int nyHHMM, int ctHHMM)
        {
            foreach (string id in _moduleOrder)
            {
                VirtualSleeve sl = _sleeves[id];
                if (!sl.IsOpen)
                    continue;

                double risk = Math.Max(sl.RiskPts, 0.25);
                double barFav = sl.Side > 0 ? (High[0] - sl.EntryPrice) : (sl.EntryPrice - Low[0]);
                sl.MaxFavPts = Math.Max(sl.MaxFavPts, barFav);

                // Stop hit check (causal intrabar check using existing StopPrice BEFORE updating M1-close BE/trail)
                bool stopHit = (sl.Side > 0 && Low[0] <= sl.StopPrice) || (sl.Side < 0 && High[0] >= sl.StopPrice);
                if (stopHit)
                {
                    CloseVirtualSleeve(sl, sl.StopPrice, barNy, sl.BeActivated ? "BE_STOP" : "STOP");
                    continue;
                }

                // Target check (T / Z)
                if (!double.IsNaN(sl.TargetPrice) && sl.TargetPrice > 0)
                {
                    bool tgtHit = (sl.Side > 0 && High[0] >= sl.TargetPrice) || (sl.Side < 0 && Low[0] <= sl.TargetPrice);
                    if (tgtHit)
                    {
                        CloseVirtualSleeve(sl, sl.TargetPrice, barNy, "TARGET");
                        continue;
                    }
                }

                // End-of-day module exits
                if (id == "SOMEOD_ext_NQ" && nyHHMM >= 1555)
                {
                    CloseVirtualSleeve(sl, Close[0], barNy, "EOD_CLOSE");
                    continue;
                }
                if (id == "R_osc30_end660_ATR50" && nyHHMM >= 1600)
                {
                    CloseVirtualSleeve(sl, Close[0], barNy, "CASH_CLOSE");
                    continue;
                }
                if (id == "Z_b15_e20_eff40_ATR50" && ctHHMM >= 1459)
                {
                    CloseVirtualSleeve(sl, Close[0], barNy, "EOD");
                    continue;
                }
                if (id == "V_nm25_noCap_mae30" && nyHHMM >= 1550)
                {
                    CloseVirtualSleeve(sl, Close[0], barNy, "V_X_TIME");
                    continue;
                }
                if (id == "W_slope_allowReFalse_ATR25" && ctHHMM >= 1500)
                {
                    CloseVirtualSleeve(sl, Close[0], barNy, "EOD");
                    continue;
                }
                if (id == "N_d5_fbTrue_ATR25" && ctHHMM >= 1600)
                {
                    CloseVirtualSleeve(sl, Close[0], barNy, "EOD");
                    continue;
                }
                if (id == "T_stop100_BE15R_calFalse")
                {
                    if (nyHHMM >= 1600)
                    {
                        CloseVirtualSleeve(sl, Close[0], barNy, "CashClose1600ET");
                        continue;
                    }
                    if (nyHHMM == 1530)
                    {
                        double closeR = sl.Side * (Close[0] - sl.EntryPrice) / risk;
                        if (closeR < 0.0 || closeR >= 1.0)
                        {
                            CloseVirtualSleeve(sl, Close[0], barNy, "Conditional1530ET");
                            continue;
                        }
                    }
                }

                // Causal M1-bar-close promotion of BE & IL lock for NEXT bar (matches _evaluar_overlay_m1_numba)
                if (sl.BeLockTriggerR > 0 && sl.MaxFavPts >= sl.BeLockTriggerR * risk && !sl.BeActivated)
                {
                    if (sl.Side > 0 && sl.EntryPrice > sl.StopPrice)
                        sl.StopPrice = sl.EntryPrice;
                    else if (sl.Side < 0 && sl.EntryPrice < sl.StopPrice)
                        sl.StopPrice = sl.EntryPrice;
                    sl.BeActivated = true;
                }

                if (sl.IlLockTriggerR > 0 && sl.MaxFavPts >= sl.IlLockTriggerR * risk)
                {
                    double lockPx = sl.EntryPrice + sl.Side * sl.IlLockLevelR * risk;
                    if ((sl.Side > 0 && lockPx > sl.StopPrice) || (sl.Side < 0 && lockPx < sl.StopPrice))
                        sl.StopPrice = lockPx;
                }

                // Optional W trailing tiers (only when EnableWTrail = true; false by default)
                if (id == "W_slope_allowReFalse_ATR25" && EnableWTrail)
                {
                    double[,] tiers = { { 1.5, 0.5 }, { 2.5, 1.5 } };
                    for (int t = 0; t < 2; t++)
                    {
                        if (sl.MaxFavPts >= tiers[t, 0] * risk)
                        {
                            double cand = sl.EntryPrice + sl.Side * tiers[t, 1] * risk;
                            if ((sl.Side > 0 && cand > sl.StopPrice) || (sl.Side < 0 && cand < sl.StopPrice))
                                sl.StopPrice = cand;
                        }
                    }
                }
            }
        }

        private void CheckComplianceLocks(DateTime barNy, int nyHHMM)
        {
            if (nyHHMM >= HardFlattenHHMM_ET && !_hardFlattenedToday)
            {
                _hardFlattenedToday = true;
                FlattenAllSleeves(Close[0], barNy, "HARD_FLATTEN_1640ET");
                return;
            }

            double openUsd = ComputeOpenPnlUsd(Close[0]);
            double netDayUsd = _realizedSessionUsd + openUsd;

            if (AccountMode == FundedSyncAccountMode.Evaluation && EnforceEvalDailyCap && EvalDailyCapUSD > 0.0)
            {
                if (netDayUsd >= EvalDailyCapUSD && !_dailyCapTriggeredToday)
                {
                    _dailyCapTriggeredToday = true;
                    FlattenAllSleeves(Close[0], barNy, "EVAL_DAILY_CAP");
                }
            }

            if (DailyLossLimitUSD > 0.0 && netDayUsd <= -DailyLossLimitUSD && !_dailyLossTriggeredToday)
            {
                _dailyLossTriggeredToday = true;
                FlattenAllSleeves(Close[0], barNy, "DAILY_LOSS_LIMIT");
            }
        }

        private void FlattenAllSleeves(double price, DateTime barNy, string reason)
        {
            foreach (string id in _moduleOrder)
            {
                VirtualSleeve sl = _sleeves[id];
                if (sl.IsOpen)
                    CloseVirtualSleeve(sl, price, barNy, reason);
            }
        }

        private double ComputeOpenPnlUsd(double markPx)
        {
            double tot = 0.0;
            foreach (string id in _moduleOrder)
            {
                VirtualSleeve sl = _sleeves[id];
                if (sl.IsOpen)
                    tot += sl.Side * (markPx - sl.EntryPrice) * sl.Contracts * 2.0;
            }
            return tot;
        }

        private double CurrentOpenRUsed()
        {
            double u = 0.0;
            foreach (string id in _moduleOrder)
            {
                VirtualSleeve sl = _sleeves[id];
                if (sl.IsOpen)
                    u += sl.AppliedW;
            }
            return u;
        }

        private int CurrentVirtualNetMicros()
        {
            int net = 0;
            foreach (string id in _moduleOrder)
            {
                VirtualSleeve sl = _sleeves[id];
                if (sl.IsOpen)
                    net += sl.Side * sl.Contracts;
            }
            return net;
        }

        private double CurrentRisk1RUsd()
        {
            return AccountMode == FundedSyncAccountMode.Evaluation ? EvalRisk1R_USD : FundedRisk1R_USD;
        }

        private bool TryOpenVirtualSleeve(
            string moduleId, int side, double entryPx, double stopPts, DateTime barNy,
            double targetPx = double.NaN, double beTrigR = -1.0, double ilTrigR = -1.0, double ilLvlR = 0.0)
        {
            VirtualSleeve sl = _sleeves[moduleId];
            if (!sl.Enabled || sl.IsOpen || stopPts < 1.0)
                return false;

            if (CollisionPolicy == FundedSyncCollisionPolicy.VetoOpposite)
            {
                int netOpen = CurrentVirtualNetMicros();
                if (netOpen * side < 0)
                    return false;
            }

            double remR = Math.Max(0.0, MaxOpenR - CurrentOpenRUsed());
            double wEff = Math.Min(sl.WeightW5, remR);
            if (wEff <= 1e-6)
                return false;

            double tgtUsd = CurrentRisk1RUsd() * wEff;
            double risk1Micro = stopPts * 2.0;
            int qty = (int)Math.Min(MaxMicroContracts, Math.Max(0, Math.Round(tgtUsd / Math.Max(risk1Micro, 1e-6))));
            if (qty == 0 && tgtUsd >= 0.55 * risk1Micro)
                qty = 1;
            if (qty <= 0)
                return false;

            sl.IsOpen = true;
            sl.Side = side;
            sl.Contracts = qty;
            sl.AppliedW = wEff;
            sl.EntryPrice = entryPx;
            sl.RiskPts = stopPts;
            sl.InitialStopPrice = entryPx - side * stopPts;
            sl.StopPrice = sl.InitialStopPrice;
            sl.TargetPrice = targetPx;
            sl.MaxFavPts = 0.0;
            sl.BeActivated = false;
            sl.BeLockTriggerR = beTrigR;
            sl.IlLockTriggerR = ilTrigR;
            sl.IlLockLevelR = ilLvlR;
            sl.EntryNyTime = barNy;
            sl.EntrySessionDate = _currentSessionDate;
            return true;
        }

        private void CloseVirtualSleeve(VirtualSleeve sl, double exitPx, DateTime barNy, string exitName)
        {
            if (!sl.IsOpen)
                return;

            double pnlPts = sl.Side * (exitPx - sl.EntryPrice);
            double rBruto = pnlPts / Math.Max(sl.RiskPts, 1e-6);
            double rNetMini = (pnlPts - 1.545) / Math.Max(sl.RiskPts, 1e-6);
            _realizedSessionUsd += (pnlPts - 0.90) * sl.Contracts * 2.0;

            if (EnableParityCsvLog)
                AppendParityCsvRow(sl, exitPx, barNy, pnlPts, rBruto, rNetMini, exitName);

            sl.IsOpen = false;
            sl.Contracts = 0;
            sl.AppliedW = 0.0;
        }

        private void AppendParityCsvRow(
            VirtualSleeve sl, double exitPx, DateTime exNy, double pnlPts, double rBruto, double rNetMini, string exitName)
        {
            try
            {
                if (!_csvHeaderWritten)
                {
                    if (!File.Exists(_resolvedCsvPath) || new FileInfo(_resolvedCsvPath).Length == 0)
                        File.WriteAllText(_resolvedCsvPath, string.Join(",", CsvHeaderCols) + Environment.NewLine, Encoding.UTF8);
                    _csvHeaderWritten = true;
                }
                string line = string.Format(CultureInfo.InvariantCulture,
                    "{0},LIVE,{1},{2:F6},{3},{4},{5},{6:F2},{7:F4},{8:F4},{9:F4},{10:F2},{11:F6},{12:F6},{13}",
                    sl.EntrySessionDate, sl.ModuleId, sl.WeightW5, sl.Side,
                    sl.EntryNyTime.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    exNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    sl.EntryPrice, sl.InitialStopPrice, exitPx, sl.RiskPts, pnlPts, rBruto, rNetMini, exitName);
                File.AppendAllText(_resolvedCsvPath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { /* Protect execution from filesystem lock during Strategy Analyzer backtest */ }
        }

        #region Module 1: R_osc30_end660_ATR50 (10m ETH)
        private void ProcessModuleR_10m(DateTime barNy, int nyMin, bool entriesAllowed)
        {
            long bucket = ((long)_currentCalDateNy * 1440L + nyMin) / 10L;
            if (_rCurBucket < 0)
            {
                _rCurBucket = bucket;
                _rCurO = Open[0]; _rCurH = High[0]; _rCurL = Low[0]; _rCurC = Close[0];
                return;
            }
            if (bucket == _rCurBucket)
            {
                _rCurH = Math.Max(_rCurH, High[0]);
                _rCurL = Math.Min(_rCurL, Low[0]);
                _rCurC = Close[0];
                return;
            }

            // Finalize completed 10m bar
            double cl = _rCurC;
            double tr = double.IsNaN(_rPrevEmaClose) ? (_rCurH - _rCurL)
                : Math.Max(_rCurH - _rCurL, Math.Max(Math.Abs(_rCurH - _rPrevEmaClose), Math.Abs(_rCurL - _rPrevEmaClose)));
            _rPrevEmaClose = cl;
            _rBarCount++;

            if (double.IsNaN(_rEma21))
                _rEma21 = cl;
            else
                _rEma21 = (2.0 / 22.0) * cl + (1.0 - 2.0 / 22.0) * _rEma21;

            if (double.IsNaN(_rAtr14))
            {
                _rTrSeed.Add(tr);
                if (_rTrSeed.Count == 14)
                {
                    double s = 0; foreach (double x in _rTrSeed) s += x;
                    _rAtr14 = s / 14.0;
                }
            }
            else
            {
                _rAtr14 = (_rAtr14 * 13.0 + tr) / 14.0;
            }

            if (!double.IsNaN(_rAtr14) && _rAtr14 > 0)
            {
                double raw = 100.0 * (cl - _rEma21) / (3.0 * _rAtr14);
                _rPrevOsc = _rOsc;
                _rOsc = double.IsNaN(_rPrevOsc) ? raw : 0.5 * raw + 0.5 * _rPrevOsc;
            }

            // Start new 10m bar
            _rCurBucket = bucket;
            _rCurO = Open[0]; _rCurH = High[0]; _rCurL = Low[0]; _rCurC = Close[0];

            if (double.IsNaN(_rOsc) || double.IsNaN(_rPrevOsc) || double.IsNaN(_rthVwap) || double.IsNaN(_atr20Session))
                return;

            bool crossUp = _rPrevOsc <= 100.0 && _rOsc > 100.0;
            bool crossDn = _rPrevOsc >= -100.0 && _rOsc < -100.0;
            if (!crossUp && !crossDn)
                return;

            VirtualSleeve rSl = _sleeves["R_osc30_end660_ATR50"];
            bool inWindow = nyMin >= 570 && nyMin < 660;
            if (!inWindow)
            {
                if (rSl.IsOpen && ((rSl.Side > 0 && crossDn) || (rSl.Side < 0 && crossUp)))
                    CloseVirtualSleeve(rSl, Close[0], barNy, "OPP_CROSS");
                return;
            }

            if (!entriesAllowed || Math.Abs(cl - _rthVwap) >= 2.5 * _rAtr14)
                return;

            int sigSide = crossUp ? 1 : -1;
            if (rSl.IsOpen && rSl.Side != sigSide)
                CloseVirtualSleeve(rSl, Close[0], barNy, "REVERSAL");

            if (!rSl.IsOpen)
                TryOpenVirtualSleeve("R_osc30_end660_ATR50", sigSide, Close[0], 0.50 * _atr20Session, barNy);
        }
        #endregion

        #region Module 2 & 6: Z_b15_e20_eff40_ATR50 & N_d5_fbTrue_ATR25 (15m RTH)
        private void ProcessModuleZandN_15m(
            DateTime barNy, DateTime barCt, int ctMin, int nyHHMM, int ctHHMM, bool entriesAllowed)
        {
            if (ctMin < 510 || ctMin >= 900)
            {
                if (ctMin >= 900 && _rth15CurBucket >= 0)
                {
                    Finalize15mBucket(barNy, entriesAllowed);
                    _rth15CurBucket = -1;
                }
                return;
            }

            long bId = (long)(barCt.Year * 10000 + barCt.Month * 100 + barCt.Day) * 32L + ((ctMin - 510) / 15L);
            if (_rth15CurBucket < 0)
            {
                _rth15CurBucket = bId;
                _rth15O = Open[0]; _rth15H = High[0]; _rth15L = Low[0]; _rth15C = Close[0];
            }
            else if (bId == _rth15CurBucket)
            {
                _rth15H = Math.Max(_rth15H, High[0]);
                _rth15L = Math.Min(_rth15L, Low[0]);
                _rth15C = Close[0];
            }
            else
            {
                // Finalize completed 15m RTH bucket
                Finalize15mBucket(barNy, entriesAllowed);
                _rth15CurBucket = bId;
                _rth15O = Open[0]; _rth15H = High[0]; _rth15L = Low[0]; _rth15C = Close[0];
            }

            // Z open entry on first 1m bar of NYSE session [08:30 CT / 09:30 ET]
            if (entriesAllowed && !_zTakenToday && ctHHMM >= 830 && ctHHMM < 835 && _zPrevSesTouchFree
                && !double.IsNaN(_zPrevSesEndEma20) && !double.IsNaN(_atr20Session))
            {
                double dist = Open[0] - _zPrevSesEndEma20;
                if (Math.Abs(dist) >= 2.0)
                {
                    int side = dist > 0 ? -1 : 1; // Fade toward prior EMA20
                    _zTradeTargetEma = _zPrevSesEndEma20;
                    if (TryOpenVirtualSleeve("Z_b15_e20_eff40_ATR50", side, Close[0], 0.50 * _atr20Session, barNy, _zTradeTargetEma))
                        _zTakenToday = true;
                }
            }
        }

        private void Finalize15mBucket(DateTime barNy, bool entriesAllowed)
        {
            double o = _rth15O, h = _rth15H, l = _rth15L, c = _rth15C;
            double rng = Math.Max(h - l, 1e-6);
            double effPct = 100.0 * Math.Abs(c - o) / rng;

            if (double.IsNaN(_zEma20))
            {
                _zCloseSeed.Add(c);
                if (_zCloseSeed.Count == 20)
                {
                    double s = 0; foreach (double x in _zCloseSeed) s += x;
                    _zEma20 = s / 20.0;
                }
            }
            else
            {
                _zEma20 = (2.0 / 21.0) * c + (1.0 - 2.0 / 21.0) * _zEma20;
            }

            if (!double.IsNaN(_zEma20))
            {
                _zCurSesBucketCount++;
                if (l <= _zEma20 && h >= _zEma20)
                    _zCurSesTouchFree = false;
                if (effPct < 40.0)
                    _zCurSesTouchFree = false;

                VirtualSleeve zSl = _sleeves["Z_b15_e20_eff40_ATR50"];
                if (zSl.IsOpen)
                    zSl.TargetPrice = _zEma20; // Update trailing limit/target each 15m bucket
            }

            _rth15VwapPrev = _rth15VwapCur;
            _rth15VwapCur = _rthVwap;

            // Module N signal evaluation (5-day high breakout, long-only)
            VirtualSleeve nSl = _sleeves["N_d5_fbTrue_ATR25"];
            if (!double.IsNaN(_prior5DayHigh) && !double.IsNaN(_rth15VwapPrev) && !double.IsNaN(_atr20Session))
            {
                bool vwapAccept = !double.IsNaN(_rthVwap) && _rth15VwapCur > _rth15VwapPrev && c > _rthVwap;
                if (c > _prior5DayHigh + 4.0)
                    _nClosesAbove5dHi++;
                else
                    _nClosesAbove5dHi = 0;

                if (entriesAllowed && !_nTakenToday && !nSl.IsOpen && _nClosesAbove5dHi >= 2 && vwapAccept)
                {
                    if (TryOpenVirtualSleeve("N_d5_fbTrue_ATR25", 1, Close[0], 0.25 * _atr20Session, barNy))
                        _nTakenToday = true;
                }

                if (nSl.IsOpen)
                {
                    if (c < _rthDayHigh) _nClosesBelowDayHi++;
                    else _nClosesBelowDayHi = 0;

                    if (_nClosesBelowDayHi >= 6)
                        CloseVirtualSleeve(nSl, Close[0], barNy, "FAILED_BREAKOUT");
                    else if (!double.IsNaN(_priorSesRange) && Close[0] <= nSl.EntryPrice - _priorSesRange)
                        CloseVirtualSleeve(nSl, Close[0], barNy, "VOLLOSS");
                }
            }
        }
        #endregion

        #region Module 4: V_nm25_noCap_mae30 (5m RTH Long-Only)
        private void ProcessModuleV_5m(
            DateTime barNy, DateTime barCt, int nyMin, int ctMin, int nyHHMM, bool entriesAllowed)
        {
            if (ctMin < 510 || ctMin >= 915)
            {
                if (ctMin >= 915 && _v5CurBucket >= 0)
                    _v5CurBucket = -1;
                return;
            }

            long bId = (long)(barCt.Year * 10000 + barCt.Month * 100 + barCt.Day) * 100L + ((ctMin - 510) / 5L);
            if (_v5CurBucket < 0)
            {
                _v5CurBucket = bId;
                _v5O = Open[0]; _v5H = High[0]; _v5L = Low[0]; _v5C = Close[0];
                return;
            }
            if (bId == _v5CurBucket)
            {
                _v5H = Math.Max(_v5H, High[0]);
                _v5L = Math.Min(_v5L, Low[0]);
                _v5C = Close[0];
                return;
            }

            double c5 = _v5C;
            _v5CurBucket = bId;
            _v5O = Open[0]; _v5H = High[0]; _v5L = Low[0]; _v5C = Close[0];

            VirtualSleeve vSl = _sleeves["V_nm25_noCap_mae30"];
            if (double.IsNaN(_rthVwap) || double.IsNaN(_vDailyAtr252) || double.IsNaN(_rthSessionOpen) || double.IsNaN(_atr20Session))
                return;

            if (vSl.IsOpen)
            {
                if (c5 < _rthVwap) _vConsecBelowVwap++;
                else _vConsecBelowVwap = 0;
                if (_vConsecBelowVwap >= 2)
                {
                    CloseVirtualSleeve(vSl, Close[0], barNy, "V_X_VWAP");
                    return;
                }
            }

            // Entry window 09:45-15:00 ET excluding CT hour 9 (09:00-09:59 CT = 10:00-10:59 ET)
            bool inWindow = nyMin >= 585 && nyMin <= 900 && barCt.Hour != 9;
            if (entriesAllowed && !vSl.IsOpen && inWindow && _vTradesToday < 3)
            {
                if (c5 > _rthSessionOpen + 0.25 * _vDailyAtr252 && c5 > _rthVwap)
                {
                    if (TryOpenVirtualSleeve("V_nm25_noCap_mae30", 1, Close[0], 0.30 * _atr20Session, barNy))
                    {
                        _vTradesToday++;
                        _vConsecBelowVwap = 0;
                    }
                }
            }
        }
        #endregion

        #region Module 5: W_slope_allowReFalse_ATR25 (1m ETH Long-Only)
        private void ProcessModuleW_1m(DateTime barNy, int ctHHMM, bool entriesAllowed)
        {
            if (!entriesAllowed || _wTradedToday || _sleeves["W_slope_allowReFalse_ATR25"].IsOpen)
                return;
            if (ctHHMM < 831 || ctHHMM > 1400)
                return;
            if (double.IsNaN(_rthVwap) || double.IsNaN(_atr20Session))
                return;

            if (Close[0] > _rthVwap && GetVwapSlope20() >= 0.0)
            {
                if (TryOpenVirtualSleeve("W_slope_allowReFalse_ATR25", 1, Close[0], 0.25 * _atr20Session, barNy))
                    _wTradedToday = true;
            }
        }
        #endregion

        #region Module 3: T_stop100_BE15R_calFalse (15m ORB + 14-Feature Quarterly KNN + +1.5R BE)
        private void ProcessModuleT_Orb(DateTime barNy, int nyMin, bool entriesAllowed)
        {
            // Advance pending shadow evaluation on current 1m bar
            if (_tPendingShadowActive)
            {
                double stopPx = _tPendingShadowEntry - _tPendingSide * _tPendingShadowStopPts;
                double tgtPx = _tPendingShadowEntry + _tPendingSide * _tPendingShadowTargetR * _tPendingShadowStopPts;
                bool hitSl = (_tPendingSide > 0 && Low[0] <= stopPx) || (_tPendingSide < 0 && High[0] >= stopPx);
                bool hitTp = (_tPendingSide > 0 && High[0] >= tgtPx) || (_tPendingSide < 0 && Low[0] <= tgtPx);
                if (hitSl || hitTp || nyMin >= 960)
                {
                    double resR = hitSl ? -1.0 : (hitTp ? _tPendingShadowTargetR : _tPendingSide * (Close[0] - _tPendingShadowEntry) / _tPendingShadowStopPts);
                    int qKey = barNy.Year * 4 + ((barNy.Month - 1) / 3);
                    _tShadowBank.Add(new ShadowObs { QuarterKey = qKey, Features = _tPendingFeatures, ReturnR = resR });
                    _tPendingShadowActive = false;
                }
            }

            if (_orbBarsCount < 5 || _orbHigh <= _orbLow || nyMin < 585 || nyMin >= 945)
                return;

            double orbPts = _orbHigh - _orbLow;
            double stopPts = Math.Max(2.0, Math.Min(100.0, 1.0 * orbPts)); // Exactly 1.0x ORB clamped [2, 100]

            if (_tPendingDelayBars > 0)
            {
                _tPendingDelayBars--;
                if (_tPendingDelayBars == 0 && entriesAllowed && !_tTakenToday && !_sleeves["T_stop100_BE15R_calFalse"].IsOpen)
                {
                    LaunchModuleTOrder(_tPendingSide, stopPts, barNy);
                    _tTakenToday = true;
                }
            }

            // Build 15m completed bar starting after ORB closes at 09:45 ET (nyMin >= 585)
            long bId = ((long)_currentCalDateNy * 1440L + nyMin) / 15L;
            if (_t15CurBucket < 0)
            {
                _t15CurBucket = bId;
                _t15O = Open[0]; _t15H = High[0]; _t15L = Low[0]; _t15C = Close[0];
                return;
            }
            if (bId == _t15CurBucket)
            {
                _t15H = Math.Max(_t15H, High[0]);
                _t15L = Math.Min(_t15L, Low[0]);
                _t15C = Close[0];
                return;
            }

            // Finalize completed 15m bar before starting the next quarter-hour bar
            double qO = _t15O, qH = _t15H, qL = _t15L, qC = _t15C;
            _t15CurBucket = bId;
            _t15O = Open[0]; _t15H = High[0]; _t15L = Low[0]; _t15C = Close[0];

            if (nyMin < 600)
                return;

            double br = Math.Max(qH - qL, 1e-6);
            double bodyRatio = Math.Abs(qC - qO) / br;
            double closeLoc = (qC - qL) / br;

            int sigSide = 0;
            if (qC > _orbHigh + 0.25 && closeLoc >= 0.60 && bodyRatio >= 0.15 && _tTouchCount >= 3)
                sigSide = 1;
            else if (qC < _orbLow - 0.25 && (1.0 - closeLoc) >= 0.60 && bodyRatio >= 0.15 && _tTouchCount >= 3)
                sigSide = -1;

            if (sigSide == 0)
                return;

            double[] feat = BuildModuleTFeatures(barNy, nyMin, sigSide, orbPts);
            int curQ = barNy.Year * 4 + ((barNy.Month - 1) / 3);
            MaybeRefitModuleTKnn(curQ);

            // Causal KNN flip & refinement vote
            int finalSide = sigSide;
            if (_priorSesRetBps < -300.0 && sigSide > 0)
                finalSide = -1;
            else if (_tActiveModelRows.Count >= 100 && PredictFlipProbKnn(feat) > 0.65)
                finalSide = -sigSide;

            // Start shadow observation if not taken as live yet
            double tgtR = GetModuleTTargetR(finalSide, orbPts);
            if (!_tPendingShadowActive)
            {
                _tPendingShadowActive = true;
                _tPendingShadowEntry = Close[0];
                _tPendingShadowStopPts = stopPts;
                _tPendingShadowTargetR = tgtR;
                _tPendingFeatures = feat;
            }

            if (!entriesAllowed || _tTakenToday || _sleeves["T_stop100_BE15R_calFalse"].IsOpen)
                return;

            double elapsed15m = (nyMin - 585) / 15.0;
            double vwapDistBps = !double.IsNaN(_rthVwap) ? finalSide * 10000.0 * (Close[0] - _rthVwap) / Close[0] : 999.0;
            if (Math.Abs(elapsed15m - 1.0) < 0.01 && Math.Abs(vwapDistBps) <= 20.0)
            {
                LaunchModuleTOrder(finalSide, stopPts, barNy);
                _tTakenToday = true;
            }
            else if (bodyRatio <= 0.20)
            {
                _tPendingDelayBars = 1;
                _tPendingSide = finalSide;
            }
            else
            {
                LaunchModuleTOrder(finalSide, stopPts, barNy);
                _tTakenToday = true;
            }
        }

        private void LaunchModuleTOrder(int side, double stopPts, DateTime barNy)
        {
            double orbPts = _orbHigh - _orbLow;
            double tgtR = GetModuleTTargetR(side, orbPts);
            bool isCounter = (side * _priorSesRetBps) < 0.0;
            double ilTrig = isCounter ? 0.75 : 1.25;
            double ilLvl = isCounter ? 0.10 : 0.0;
            double targetPx = Close[0] + side * tgtR * stopPts;
            TryOpenVirtualSleeve("T_stop100_BE15R_calFalse", side, Close[0], stopPts, barNy, targetPx, 1.5, ilTrig, ilLvl);
        }

        private double GetModuleTTargetR(int side, double orbPts)
        {
            double orbBps = Close[0] > 0 ? 10000.0 * orbPts / Close[0] : 0.0;
            if (orbBps > 45.0) return 1.25;
            return 3.0;
        }

        private double[] BuildModuleTFeatures(DateTime barNy, int nyMin, int side, double orbPts)
        {
            double c = Math.Max(Close[0], 1.0);
            double vwapBps = !double.IsNaN(_rthVwap) ? 10000.0 * (c - _rthVwap) / c : 0.0;
            int nM = _m1CloseHist.Count;
            double ret30m = (nM >= 31 && _m1CloseHist[nM - 31] > 0) ? 10000.0 * (c - _m1CloseHist[nM - 31]) / _m1CloseHist[nM - 31] : 0.0;
            double wkAng = 2.0 * Math.PI * ((int)barNy.DayOfWeek) / 5.0;
            double moAng = 2.0 * Math.PI * (barNy.Month - 1) / 12.0;

            return new[]
            {
                _tPriorSesOpenGapBps, _priorSesRetBps, _priorRet5Bps, _priorRet20Bps,
                vwapBps, ret30m, (double)side, (nyMin - 585) / 15.0,
                10000.0 * orbPts / c, (double)_tTouchCount,
                Math.Sin(wkAng), Math.Cos(wkAng), Math.Sin(moAng), Math.Cos(moAng)
            };
        }

        private void MaybeRefitModuleTKnn(int curQuarter)
        {
            if (curQuarter == _tLastRefitQuarter)
                return;
            _tLastRefitQuarter = curQuarter;
            _tActiveModelRows.Clear();
            foreach (ShadowObs obs in _tShadowBank)
            {
                if (obs.QuarterKey < curQuarter)
                    _tActiveModelRows.Add(obs);
            }
            if (_tActiveModelRows.Count < 100)
                return;

            for (int f = 0; f < 14; f++)
            {
                double sum = 0.0;
                foreach (ShadowObs r in _tActiveModelRows) sum += r.Features[f];
                double mu = sum / _tActiveModelRows.Count;
                double var = 0.0;
                foreach (ShadowObs r in _tActiveModelRows) var += Math.Pow(r.Features[f] - mu, 2);
                _tFeatMean[f] = mu;
                _tFeatStd[f] = Math.Max(Math.Sqrt(var / _tActiveModelRows.Count), 1e-6);
            }
        }

        private double PredictFlipProbKnn(double[] feat)
        {
            var dists = new List<Tuple<double, double>>(_tActiveModelRows.Count);
            foreach (ShadowObs obs in _tActiveModelRows)
            {
                double d2 = 0.0;
                for (int f = 0; f < 14; f++)
                {
                    double dz = (feat[f] - _tFeatMean[f]) / _tFeatStd[f] - (obs.Features[f] - _tFeatMean[f]) / _tFeatStd[f];
                    d2 += dz * dz;
                }
                dists.Add(Tuple.Create(Math.Sqrt(d2), obs.ReturnR));
            }
            dists.Sort((a, b) => a.Item1.CompareTo(b.Item1));
            int k = Math.Min(15, dists.Count);
            double wTot = 0.0, wFlip = 0.0;
            for (int i = 0; i < k; i++)
            {
                double w = 1.0 / (1.0 + 2.0 * dists[i].Item1);
                wTot += w;
                if (dists[i].Item2 < 0.0)
                    wFlip += w;
            }
            return wTot > 0 ? wFlip / wTot : 0.0;
        }
        #endregion

        #region Module 7: SOMEOD_ext_NQ (M5 NY+7h MQL5 EMA12/120 & SMA-ATR14)
        private void ProcessModuleSOMEOD_5m(DateTime barNy, bool entriesAllowed)
        {
            DateTime srvTime = barNy.AddHours(7);
            long bId = ((long)srvTime.Ticks) / (TimeSpan.TicksPerMinute * 5L);
            if (_som5CurBucket < 0)
            {
                _som5CurBucket = bId;
                _som5StartNy = barNy;
                _som5O = Open[0]; _som5H = High[0]; _som5L = Low[0]; _som5C = Close[0];
                return;
            }
            if (bId == _som5CurBucket)
            {
                _som5H = Math.Max(_som5H, High[0]);
                _som5L = Math.Min(_som5L, Low[0]);
                _som5C = Close[0];
                return;
            }

            // Finalize completed M5 bar
            double cl = _som5C;
            double tr = double.IsNaN(_somPrevClose) ? (_som5H - _som5L)
                : Math.Max(_som5H - _som5L, Math.Max(Math.Abs(_som5H - _somPrevClose), Math.Abs(_som5L - _somPrevClose)));
            _somPrevClose = cl;
            _som5BarCount++;

            _somEma12 = double.IsNaN(_somEma12) ? cl : (2.0 / 13.0) * cl + (1.0 - 2.0 / 13.0) * _somEma12;
            _somEma120 = double.IsNaN(_somEma120) ? cl : (2.0 / 121.0) * cl + (1.0 - 2.0 / 121.0) * _somEma120;

            // Exact MQL5 iATR parity: SMA of True Range over 14 bars (NOT Wilder RMA!)
            _somTrWindow.Enqueue(tr);
            if (_somTrWindow.Count > 14)
                _somTrWindow.Dequeue();
            if (_somTrWindow.Count == 14)
            {
                double s = 0; foreach (double x in _somTrWindow) s += x;
                _somAtr14 = s / 14.0;
            }

            DateTime closedStartNy = _som5StartNy;
            _som5CurBucket = bId;
            _som5StartNy = barNy;
            _som5O = Open[0]; _som5H = High[0]; _som5L = Low[0]; _som5C = Close[0];

            VirtualSleeve somSl = _sleeves["SOMEOD_ext_NQ"];
            // Trail update on closed M5 bar using EMA120 after +0.5 R MFE
            if (somSl.IsOpen && !double.IsNaN(_somEma120))
            {
                if (somSl.MaxFavPts >= 0.5 * somSl.RiskPts)
                {
                    if (somSl.Side > 0 && _somEma120 < cl && _somEma120 > somSl.StopPrice + 0.25)
                        somSl.StopPrice = _somEma120;
                    else if (somSl.Side < 0 && _somEma120 > cl && _somEma120 < somSl.StopPrice - 0.25)
                        somSl.StopPrice = _somEma120;
                }
            }

            // Signal check on closed 09:30 NY M5 bar (closes at 09:35 NY)
            bool isOpenSignalBar = closedStartNy.Hour == 9 && closedStartNy.Minute >= 30 && closedStartNy.Minute < 35;
            if (entriesAllowed && !_somTradedToday && !somSl.IsOpen && isOpenSignalBar && !double.IsNaN(_somAtr14) && _somAtr14 > 0)
            {
                int side = cl > _somEma12 ? 1 : (cl < _somEma12 ? -1 : 0);
                if (side != 0)
                {
                    if (TryOpenVirtualSleeve("SOMEOD_ext_NQ", side, Close[0], 8.0 * _somAtr14, barNy))
                        _somTradedToday = true;
                }
            }
        }
        #endregion

        #region Single Net Position Synchronizer & Hybrid NQ/MNQ Split
        private void SynchronizeNetPosition(DateTime barNy)
        {
            int targetMicros = _hardFlattenedToday || _dailyCapTriggeredToday || _dailyLossTriggeredToday
                ? 0
                : CurrentVirtualNetMicros();

            double pvPrimary = Instrument.MasterInstrument.PointValue;
            if (_hasSecondaryMnq && pvPrimary >= 15.0)
            {
                // Hybrid NQ (BIP 0) + MNQ (BIP 1) Split: exact floor(|net|/10) NQ + |net|%10 MNQ
                int sgn = Math.Sign(targetMicros);
                int absM = Math.Abs(targetMicros);
                int tgtNq = sgn * (absM / 10);
                int tgtMnq = sgn * (absM % 10);
                ReconcileBipPosition(0, tgtNq, "FS_NQ");
                ReconcileBipPosition(1, tgtMnq, "FS_MNQ");
            }
            else if (pvPrimary >= 15.0)
            {
                // Single NQ chart without secondary MNQ feed: round net micros / 10 to nearest mini
                int tgtMini = (int)Math.Round(targetMicros / 10.0, MidpointRounding.AwayFromZero);
                ReconcileBipPosition(0, tgtMini, "FS_NQ");
            }
            else
            {
                // Single MNQ chart: 1-to-1 micro execution
                ReconcileBipPosition(0, targetMicros, "FS_MNQ");
            }
        }

        private void ReconcileBipPosition(int bip, int targetSignedQty, string tagPrefix)
        {
            Position pos = Positions[bip];
            int curQty = pos.MarketPosition == MarketPosition.Long ? pos.Quantity
                : (pos.MarketPosition == MarketPosition.Short ? -pos.Quantity : 0);

            if (curQty == targetSignedQty)
                return;

            int delta = targetSignedQty - curQty;
            if (curQty > 0 && targetSignedQty <= 0)
            {
                ExitLong(bip, curQty, tagPrefix + "_FL", tagPrefix + "_L");
                if (targetSignedQty < 0)
                    EnterShort(bip, Math.Abs(targetSignedQty), tagPrefix + "_S");
            }
            else if (curQty < 0 && targetSignedQty >= 0)
            {
                ExitShort(bip, Math.Abs(curQty), tagPrefix + "_FL", tagPrefix + "_S");
                if (targetSignedQty > 0)
                    EnterLong(bip, targetSignedQty, tagPrefix + "_L");
            }
            else if (delta > 0)
            {
                if (curQty >= 0) EnterLong(bip, delta, tagPrefix + "_L");
                else ExitShort(bip, delta, tagPrefix + "_TR", tagPrefix + "_S");
            }
            else if (delta < 0)
            {
                if (curQty <= 0) EnterShort(bip, Math.Abs(delta), tagPrefix + "_S");
                else ExitLong(bip, Math.Abs(delta), tagPrefix + "_TR", tagPrefix + "_L");
            }
        }
        #endregion

        #region NinjaScript Properties
        [NinjaScriptProperty]
        [Display(Name = "Account Mode", Order = 1, GroupName = "01. Prop Account")]
        public FundedSyncAccountMode AccountMode { get; set; }

        [NinjaScriptProperty]
        [Range(50.0, 2500.0)]
        [Display(Name = "Eval Risk 1R (USD)", Order = 2, GroupName = "01. Prop Account")]
        public double EvalRisk1R_USD { get; set; }

        [NinjaScriptProperty]
        [Range(50.0, 2500.0)]
        [Display(Name = "Funded Risk 1R (USD)", Order = 3, GroupName = "01. Prop Account")]
        public double FundedRisk1R_USD { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Max Concurrent Open R", Order = 4, GroupName = "01. Prop Account")]
        public double MaxOpenR { get; set; }

        [NinjaScriptProperty]
        [Range(1, 200)]
        [Display(Name = "Max Micros Cap", Order = 5, GroupName = "01. Prop Account")]
        public int MaxMicroContracts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Collision Policy", Order = 6, GroupName = "01. Prop Account")]
        public FundedSyncCollisionPolicy CollisionPolicy { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Secondary MNQ Symbol (optional Hybrid)", Order = 7, GroupName = "01. Prop Account")]
        public string SecondaryMnqSymbol { get; set; }

        [NinjaScriptProperty]
        [Range(1500, 1700)]
        [Display(Name = "Hard Flatten HHMM ET", Order = 10, GroupName = "02. Compliance")]
        public int HardFlattenHHMM_ET { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enforce Eval Daily Cap", Order = 11, GroupName = "02. Compliance")]
        public bool EnforceEvalDailyCap { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 50000.0)]
        [Display(Name = "Eval Daily Cap USD", Order = 12, GroupName = "02. Compliance")]
        public double EvalDailyCapUSD { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 50000.0)]
        [Display(Name = "Daily Loss Limit USD", Order = 13, GroupName = "02. Compliance")]
        public double DailyLossLimitUSD { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable W Trailing (default false)", Order = 14, GroupName = "02. Compliance")]
        public bool EnableWTrail { get; set; }

        [NinjaScriptProperty] [Display(Name = "Enable R", Order = 20, GroupName = "03. Modules & W5 Weights")] public bool EnableR { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable Z", Order = 21, GroupName = "03. Modules & W5 Weights")] public bool EnableZ { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable T", Order = 22, GroupName = "03. Modules & W5 Weights")] public bool EnableT { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable V", Order = 23, GroupName = "03. Modules & W5 Weights")] public bool EnableV { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable W", Order = 24, GroupName = "03. Modules & W5 Weights")] public bool EnableW { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable N", Order = 25, GroupName = "03. Modules & W5 Weights")] public bool EnableN { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable SOMEOD", Order = 26, GroupName = "03. Modules & W5 Weights")] public bool EnableSOMEOD { get; set; }

        [NinjaScriptProperty] [Display(Name = "Weight R (W5)", Order = 30, GroupName = "03. Modules & W5 Weights")] public double WeightR { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight Z (W5)", Order = 31, GroupName = "03. Modules & W5 Weights")] public double WeightZ { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight T (W5)", Order = 32, GroupName = "03. Modules & W5 Weights")] public double WeightT { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight V (W5)", Order = 33, GroupName = "03. Modules & W5 Weights")] public double WeightV { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight W (W5)", Order = 34, GroupName = "03. Modules & W5 Weights")] public double WeightW { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight N (W5)", Order = 35, GroupName = "03. Modules & W5 Weights")] public double WeightN { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight SOMEOD (W5)", Order = 36, GroupName = "03. Modules & W5 Weights")] public double WeightSOMEOD { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable Parity CSV Log", Order = 40, GroupName = "04. Parity Logger")]
        public bool EnableParityCsvLog { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Parity CSV File Name", Order = 41, GroupName = "04. Parity Logger")]
        public string ParityCsvFileName { get; set; }
        #endregion
    }
}
