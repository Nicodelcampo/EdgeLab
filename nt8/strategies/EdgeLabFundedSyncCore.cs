using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

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

    public enum FundedSyncPortfolioPreset
    {
        P_OPT_SF_v2 = 0,
        P_OPT_Core6 = 1,
        P_OPT_SF_SinW = 2,
        Core5_AltaConv = 3,
        Tier1_Snipers_RZ = 4,
        Tier23_Flow_TVNS = 5,
        CustomWeights = 6,
        Core5_R25 = 7,
        SpeedEval_TOnly = 8,
        ES_Core_US500 = 9
    }

    public enum FundedSyncPropProfile
    {
        LucidFlex_150K_Equilibrado = 0,
        LucidFlex_150K_MaxFlujo = 1,
        LucidFlex_50K_Conservador = 2,
        Tradeify_SelectFlex_150K = 3,
        Topstep_NoAct_50K = 4,
        FundedNext_Flex_150K = 5,
        Personal_Custom = 6,
        Tradeify_SelectFlex_50K = 7,
        FundedNext_Flex_50K = 8,
        LucidFlex_25K_Rescate = 9
    }

    public enum FundedSyncModuleId
    {
        R_osc30_end660_ATR50 = 0,
        Z_b15_e20_eff40_ATR50 = 1,
        T_stop100_BE15R_calFalse = 2,
        V_nm25_noCap_mae30 = 3,
        W_slope_allowReFalse_ATR25 = 4,
        N_d5_fbTrue_ATR25 = 5,
        SOMEOD_ext_NQ = 6
    }
}

namespace NinjaTrader.NinjaScript.Strategies.EdgeLabFundedSync
{
    using Strategies;

    public sealed class CompletedTradeRecord
    {
        public int SessionDate;
        public string ModuleId;
        public double WeightW5;
        public int Side;
        public int Contracts;
        public DateTime EntryNy;
        public DateTime ExitNy;
        public double EntryPrice;
        public double InitialStopPrice;
        public double ExitPrice;
        public double RiskPts;
        public double PnlPts;
        public double RBruto;
        public double RNetoMini;
        public string ExitName;
    }

    public sealed class PropProfileDefaults
    {
        public double EvalRisk1R;
        public double FundedRisk1R;
        public int MaxMicros;
        public double EvalDailyCapUsd;
        public double DailyLossLimitUsd;
        public bool EnforceEvalDailyCap;
        public int HardFlattenHHMM_ET;
        public FundedSyncCollisionPolicy CollisionPolicy;

        public static PropProfileDefaults For(FundedSyncPropProfile profile)
        {
            switch (profile)
            {
                case FundedSyncPropProfile.LucidFlex_50K_Conservador:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 200.0, FundedRisk1R = 200.0, MaxMicros = 40,
                        EvalDailyCapUsd = 1140.0, DailyLossLimitUsd = 1200.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.LucidFlex_150K_MaxFlujo:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 650.0, FundedRisk1R = 450.0, MaxMicros = 100,
                        EvalDailyCapUsd = 3420.0, DailyLossLimitUsd = 2700.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.Tradeify_SelectFlex_150K:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 650.0, FundedRisk1R = 450.0, MaxMicros = 120,
                        EvalDailyCapUsd = 3420.0, DailyLossLimitUsd = 0.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.Topstep_NoAct_50K:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 300.0, FundedRisk1R = 200.0, MaxMicros = 50,
                        EvalDailyCapUsd = 1567.0, DailyLossLimitUsd = 0.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1605, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.FundedNext_Flex_150K:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 600.0, FundedRisk1R = 400.0, MaxMicros = 80,
                        EvalDailyCapUsd = 3040.0, DailyLossLimitUsd = 0.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.Tradeify_SelectFlex_50K:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 300.0, FundedRisk1R = 200.0, MaxMicros = 40,
                        EvalDailyCapUsd = 1140.0, DailyLossLimitUsd = 0.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.FundedNext_Flex_50K:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 250.0, FundedRisk1R = 175.0, MaxMicros = 30,
                        EvalDailyCapUsd = 950.0, DailyLossLimitUsd = 0.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.Personal_Custom:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 450.0, FundedRisk1R = 450.0, MaxMicros = 100,
                        EvalDailyCapUsd = 0.0, DailyLossLimitUsd = 0.0, EnforceEvalDailyCap = false,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.LucidFlex_25K_Rescate:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 60.0, FundedRisk1R = 60.0, MaxMicros = 1,
                        EvalDailyCapUsd = 470.0, DailyLossLimitUsd = 120.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1635, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
                case FundedSyncPropProfile.LucidFlex_150K_Equilibrado:
                default:
                    return new PropProfileDefaults
                    {
                        EvalRisk1R = 450.0, FundedRisk1R = 450.0, MaxMicros = 100,
                        EvalDailyCapUsd = 3420.0, DailyLossLimitUsd = 2700.0, EnforceEvalDailyCap = true,
                        HardFlattenHHMM_ET = 1640, CollisionPolicy = FundedSyncCollisionPolicy.Netting
                    };
            }
        }
    }

    internal static class FundedSyncMath
    {
        public static readonly string[] ModuleOrder =
        {
            "R_osc30_end660_ATR50",
            "Z_b15_e20_eff40_ATR50",
            "T_stop100_BE15R_calFalse",
            "V_nm25_noCap_mae30",
            "W_slope_allowReFalse_ATR25",
            "N_d5_fbTrue_ATR25",
            "SOMEOD_ext_NQ"
        };

        public static Dictionary<string, double> GetPresetWeights(FundedSyncPortfolioPreset preset)
        {
            var d = new Dictionary<string, double>();
            foreach (string id in ModuleOrder) d[id] = 0.0;

            switch (preset)
            {
                case FundedSyncPortfolioPreset.P_OPT_Core6:
                    d["R_osc30_end660_ATR50"] = 1.733376;
                    d["Z_b15_e20_eff40_ATR50"] = 2.060732;
                    d["T_stop100_BE15R_calFalse"] = 0.747167;
                    d["V_nm25_noCap_mae30"] = 1.002927;
                    d["W_slope_allowReFalse_ATR25"] = 0.899909;
                    d["N_d5_fbTrue_ATR25"] = 1.215438;
                    break;
                case FundedSyncPortfolioPreset.P_OPT_SF_SinW:
                    d["R_osc30_end660_ATR50"] = 1.747109;
                    d["Z_b15_e20_eff40_ATR50"] = 2.077058;
                    d["T_stop100_BE15R_calFalse"] = 0.719343;
                    d["V_nm25_noCap_mae30"] = 1.003434;
                    d["N_d5_fbTrue_ATR25"] = 1.256155;
                    d["SOMEOD_ext_NQ"] = 0.875168;
                    break;
                case FundedSyncPortfolioPreset.Core5_AltaConv:
                case FundedSyncPortfolioPreset.Core5_R25:
                    d["R_osc30_end660_ATR50"] = 1.802134;
                    d["Z_b15_e20_eff40_ATR50"] = 2.277168;
                    d["T_stop100_BE15R_calFalse"] = 0.709531;
                    d["N_d5_fbTrue_ATR25"] = 1.261968;
                    d["SOMEOD_ext_NQ"] = 0.848629;
                    break;
                case FundedSyncPortfolioPreset.SpeedEval_TOnly:
                    d["T_stop100_BE15R_calFalse"] = 1.0;
                    break;
                case FundedSyncPortfolioPreset.ES_Core_US500:
                    d["R_osc30_end660_ATR50"] = 1.0 / 6.0;
                    d["Z_b15_e20_eff40_ATR50"] = 1.0 / 6.0;
                    d["T_stop100_BE15R_calFalse"] = 1.0 / 6.0;
                    d["V_nm25_noCap_mae30"] = 1.0 / 6.0;
                    d["W_slope_allowReFalse_ATR25"] = 1.0 / 6.0;
                    d["N_d5_fbTrue_ATR25"] = 1.0 / 6.0;
                    break;
                case FundedSyncPortfolioPreset.Tier1_Snipers_RZ:
                    d["R_osc30_end660_ATR50"] = 0.732985;
                    d["Z_b15_e20_eff40_ATR50"] = 1.613336;
                    break;
                case FundedSyncPortfolioPreset.Tier23_Flow_TVNS:
                    d["T_stop100_BE15R_calFalse"] = 0.774228;
                    d["V_nm25_noCap_mae30"] = 1.078114;
                    d["N_d5_fbTrue_ATR25"] = 1.326865;
                    d["SOMEOD_ext_NQ"] = 0.984898;
                    break;
                case FundedSyncPortfolioPreset.P_OPT_SF_v2:
                default:
                    d["R_osc30_end660_ATR50"] = 1.653354;
                    d["Z_b15_e20_eff40_ATR50"] = 1.965598;
                    d["T_stop100_BE15R_calFalse"] = 0.768284;
                    d["V_nm25_noCap_mae30"] = 1.019769;
                    d["W_slope_allowReFalse_ATR25"] = 0.915674;
                    d["N_d5_fbTrue_ATR25"] = 1.252428;
                    d["SOMEOD_ext_NQ"] = 0.911410;
                    break;
            }
            return d;
        }

        public static double RoundTick(double price, double tickSize)
        {
            if (double.IsNaN(price) || tickSize <= 0.0) return price;
            return Math.Round(price / tickSize, MidpointRounding.AwayFromZero) * tickSize;
        }

        public static double RoundZetaTarget(int side, double price, double tickSize)
        {
            if (double.IsNaN(price) || tickSize <= 0.0) return price;
            return side <= 0 ? Math.Floor(price / tickSize) * tickSize : Math.Ceiling(price / tickSize) * tickSize;
        }

        public static int DateKey(DateTime dt) { return dt.Year * 10000 + dt.Month * 100 + dt.Day; }
        public static int Hhmmss(DateTime dt) { return dt.Hour * 10000 + dt.Minute * 100 + dt.Second; }
        public static int Hhmm(DateTime dt) { return dt.Hour * 100 + dt.Minute; }
        public static int MinOfDay(DateTime dt) { return dt.Hour * 60 + dt.Minute; }
        public static int WeekdayMon0(DateTime dt) { return ((int)dt.DayOfWeek + 6) % 7; }

        public static TimeZoneInfo ResolveTz(string winId)
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById(winId); }
            catch { return TimeZoneInfo.Utc; }
        }

        public static BarTimeContext BuildBarTimeContext(
            DateTime closeUtc, double open, double high, double low, double close, double volume,
            TimeZoneInfo nyTz, TimeZoneInfo ctTz)
        {
            DateTime cUtc = DateTime.SpecifyKind(closeUtc, DateTimeKind.Utc);
            DateTime oUtc = cUtc.AddMinutes(-1);
            DateTime cNy = TimeZoneInfo.ConvertTimeFromUtc(cUtc, nyTz);
            DateTime oNy = TimeZoneInfo.ConvertTimeFromUtc(oUtc, nyTz);
            DateTime cCt = TimeZoneInfo.ConvertTimeFromUtc(cUtc, ctTz);
            DateTime oCt = TimeZoneInfo.ConvertTimeFromUtc(oUtc, ctTz);

            return new BarTimeContext
            {
                CloseUtc = cUtc,
                OpenUtc = oUtc,
                CloseNy = cNy,
                OpenNy = oNy,
                CloseCt = cCt,
                OpenCt = oCt,
                OpenDateUtc = DateKey(oUtc),
                OpenHhmmUtc = Hhmm(oUtc),
                OpenDateEt = DateKey(oNy),
                CloseDateEt = DateKey(cNy),
                OpenMinEt = MinOfDay(oNy),
                CloseMinEt = MinOfDay(cNy),
                CloseHhmmEt = Hhmm(cNy),
                OpenDateCt = DateKey(oCt),
                CloseDateCt = DateKey(cCt),
                OpenMinCt = MinOfDay(oCt),
                CloseHhmmssCt = Hhmmss(cCt),
                NextMinHhmmssCt = Hhmmss(cCt.AddMinutes(1)),
                DowCtMon0 = WeekdayMon0(cCt),
                EthTradeDate = DateKey(oNy.AddHours(6).Date),
                ExactMinute = (cUtc.Second == 0 && cUtc.Millisecond == 0),
                Open = open,
                High = high,
                Low = low,
                Close = close,
                Volume = volume
            };
        }

        private static DateTime EasterSundayUtc(int year)
        {
            int a = year % 19;
            int b = year / 100;
            int c = year % 100;
            int d = b / 4;
            int e = b % 4;
            int f = (b + 8) / 25;
            int g = (b - f + 1) / 3;
            int h = (19 * a + b - d - g + 15) % 30;
            int i = c / 4;
            int k = c % 4;
            int l = (32 + 2 * e + 2 * i - h - k) % 7;
            int m = (a + 11 * h + 22 * l) / 451;
            int month = (h + l - 7 * m + 114) / 31;
            int day = ((h + l - 7 * m + 114) % 31) + 1;
            return new DateTime(year, month, day);
        }

        public static bool IsFullNyseTradingDay(DateTime dtCash)
        {
            DayOfWeek dow = dtCash.DayOfWeek;
            if (dow == DayOfWeek.Saturday || dow == DayOfWeek.Sunday) return false;

            int y = dtCash.Year;
            int m = dtCash.Month;
            int d = dtCash.Day;
            int ymd = y * 10000 + m * 100 + d;

            // One-off US equity market closures (Hurricane Sandy, National Days of Mourning)
            if (ymd == 20121029 || ymd == 20121030 || ymd == 20181205 || ymd == 20250109) return false;

            // New Year's Day (Jan 1, or Mon Jan 2 when Jan 1 is Sun)
            if (m == 1 && (d == 1 || (d == 2 && dow == DayOfWeek.Monday))) return false;
            // MLK Day (3rd Monday in January, >= 1998)
            if (m == 1 && y >= 1998 && dow == DayOfWeek.Monday && d >= 15 && d <= 21) return false;
            // Presidents' Day (3rd Monday in February)
            if (m == 2 && dow == DayOfWeek.Monday && d >= 15 && d <= 21) return false;
            // Good Friday
            if (dtCash.Date == EasterSundayUtc(y).AddDays(-2)) return false;
            // Memorial Day (last Monday in May)
            if (m == 5 && dow == DayOfWeek.Monday && d >= 25) return false;
            // Juneteenth (>= 2022, observed)
            if (m == 6 && y >= 2022 && (d == 19 || (d == 18 && dow == DayOfWeek.Friday) || (d == 20 && dow == DayOfWeek.Monday))) return false;
            // Independence Day (Jul 4 observed + Jul 3 Mon-Thu 13:00 ET early close)
            if (m == 7 && (d == 4 || (d == 5 && dow == DayOfWeek.Monday) || (d == 3 && dow >= DayOfWeek.Monday && dow <= DayOfWeek.Thursday))) return false;
            // Labor Day (1st Monday in September)
            if (m == 9 && dow == DayOfWeek.Monday && d <= 7) return false;
            // Thanksgiving (4th Thu Nov) & Day After Thanksgiving (4th Fri Nov early close)
            if (m == 11 && ((dow == DayOfWeek.Thursday && d >= 22 && d <= 28) || (dow == DayOfWeek.Friday && d >= 23 && d <= 29))) return false;
            // Christmas Day (Dec 25 observed + Dec 24 Mon-Thu 13:00 ET early close)
            if (m == 12 && (d == 25 || (d == 26 && dow == DayOfWeek.Monday) || (d == 24 && dow >= DayOfWeek.Monday && dow <= DayOfWeek.Thursday))) return false;

            return true;
        }
    }

    public sealed class BarTimeContext
    {
        public DateTime CloseUtc;
        public DateTime OpenUtc;
        public DateTime CloseNy;
        public DateTime OpenNy;
        public DateTime CloseCt;
        public DateTime OpenCt;
        public int OpenDateUtc;
        public int OpenHhmmUtc;
        public int OpenDateEt;
        public int CloseDateEt;
        public int OpenMinEt;
        public int CloseMinEt;
        public int CloseHhmmEt;
        public int OpenDateCt;
        public int CloseDateCt;
        public int OpenMinCt;
        public int CloseHhmmssCt;
        public int NextMinHhmmssCt;
        public int DowCtMon0;
        public int EthTradeDate;
        public bool ExactMinute;
        public double Open;
        public double High;
        public double Low;
        public double Close;
        public double Volume;
    }

    public sealed class VirtualSleeve
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
        public double TargetPrice = double.NaN;
        public double RiskPts;
        public double MaxFavPts;
        public bool OverlayBeActivated;
        public DateTime EntryNy;
        public int EntrySessionDate;

        // Pending signal at OnBarClose -> executes next M1 bar open
        public bool HasPendingEntry;
        public int PendingEntrySide;
        public double PendingStopPts;
        public double PendingFixedStopPrice = double.NaN;
        public double PendingTargetPrice = double.NaN;
        public bool PendingEntryIsStopOrder;
        public double PendingEntryStopPrice;

        public string PendingExitReason;
    }

    internal abstract class ModuleEngineBase
    {
        public readonly string ModuleId;
        public double TickSize = 0.25;
        protected ModuleEngineBase(string id) { ModuleId = id; }

        public virtual void UpdateM1OverlayProtectionsOnClose(VirtualSleeve sl, BarTimeContext bar) { }

        public abstract void OnNewEthSession(int completedEthDate, double completedHigh, double completedLow, double completedClose, int newEthDate);
        public abstract void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host);
    }

    // -------------------------------------------------------------------------
    // Module R: AtrPhase (10m ETH resampled from M1)
    // -------------------------------------------------------------------------
    internal sealed class AtrPhaseEngine : ModuleEngineBase
    {
        private static readonly HashSet<int> BlockedSessions = new HashSet<int>
        {
            20220803, 20220830, 20230405, 20240704, 20241224, 20250120, 20250703, 20250829
        };

        private readonly double _oscAtrMult;
        private readonly int _entryEndMinEt;
        private readonly double _slAtrK;
        private readonly double _emaAlpha = 2.0 / 22.0;

        private bool _hasBucket;
        private int _bucketDateEt;
        private int _bucketOpenMin10;
        private double _bO, _bH, _bL, _bC, _bV;
        private int _bStartOpenMinEt;
        private int _bOpenDateUtc, _bOpenHhmmUtc;

        private bool _emaReady, _prevCloseReady, _atrReady, _oscReady;
        private int _trCount;
        private double _trSum, _ema21, _prevDecClose, _atr14, _osc;
        private int _shadowSide, _pendingRevSide;
        private int _vwapDate = -1;
        private double _vwapVol, _vwapPv;

        public AtrPhaseEngine(double oscAtrMult = 3.0, int entryEndMinEt = 660, double slAtrK = 0.50)
            : base("R_osc30_end660_ATR50")
        {
            _oscAtrMult = oscAtrMult;
            _entryEndMinEt = entryEndMinEt;
            _slAtrK = slAtrK;
        }

        private void ResetState()
        {
            _prevCloseReady = false; _oscReady = false; _atrReady = false; _emaReady = false;
            _trSum = 0; _trCount = 0; _prevDecClose = 0; _osc = 0; _atr14 = 0; _ema21 = 0;
            _pendingRevSide = 0; _shadowSide = 0; _vwapDate = -1; _vwapVol = 0; _vwapPv = 0;
        }

        public override void OnNewEthSession(int d0, double h, double l, double c, int d1) { }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            if (_pendingRevSide != 0 && !sl.IsOpen && !sl.HasPendingEntry)
            {
                int rSide = _pendingRevSide;
                _pendingRevSide = 0;
                if (!double.IsNaN(atr20Session) && atr20Session > 0)
                    host.QueueMarketEntry(sl, rSide, _slAtrK * atr20Session);
            }

            int bMin10 = (bar.OpenMinEt / 10) * 10;
            if (_hasBucket && (_bucketDateEt != bar.OpenDateEt || _bucketOpenMin10 != bMin10))
                Flush10mBucket(atr20Session, sl, host, _bucketOpenMin10 + 10);

            if (!_hasBucket)
            {
                _hasBucket = true;
                _bucketDateEt = bar.OpenDateEt;
                _bucketOpenMin10 = bMin10;
                _bO = bar.Open; _bH = bar.High; _bL = bar.Low; _bC = bar.Close; _bV = bar.Volume;
                _bStartOpenMinEt = bar.OpenMinEt;
                _bOpenDateUtc = bar.OpenDateUtc;
                _bOpenHhmmUtc = bar.OpenHhmmUtc;
            }
            else
            {
                _bH = Math.Max(_bH, bar.High);
                _bL = Math.Min(_bL, bar.Low);
                _bC = bar.Close;
                _bV += bar.Volume;
            }

            if (bar.CloseMinEt == _bucketOpenMin10 + 10)
                Flush10mBucket(atr20Session, sl, host, bar.CloseMinEt);
        }

        private void Flush10mBucket(double atr20Session, VirtualSleeve sl, PortfolioCoordinator host, int closeMinEt)
        {
            _hasBucket = false;
            int sessDate = _bucketDateEt;
            if (BlockedSessions.Contains(sessDate))
            {
                _shadowSide = 0; _pendingRevSide = 0;
                if (sl.IsOpen) host.QueueMarketExit(sl, "INCOMPLETE_SESSION");
                return;
            }

            if (_bOpenHhmmUtc == 0 && _prevCloseReady && Math.Abs(_bO - _prevDecClose) > 400.0 * TickSize)
            {
                bool had = _shadowSide != 0;
                ResetState();
                if (had && sl.IsOpen) host.QueueMarketExit(sl, "ROLL_RESET");
            }

            double prevOsc = _osc;
            bool prevOscReady = _oscReady;
            bool oscNow = UpdateIndicator(_bH, _bL, _bC);

            bool vwapOk = false;
            if (_bStartOpenMinEt >= 570 && _bStartOpenMinEt < 960)
            {
                if (_vwapDate != sessDate) { _vwapDate = sessDate; _vwapVol = 0; _vwapPv = 0; }
                double typ = (_bH + _bL + _bC) / 3.0;
                _vwapPv += typ * _bV;
                _vwapVol += _bV;
                if (_vwapVol > 0 && _atrReady)
                {
                    double vw = _vwapPv / _vwapVol;
                    vwapOk = Math.Abs(_bC - vw) < 2.5 * _atr14;
                }
            }

            if (closeMinEt == 960)
            {
                _shadowSide = 0; _pendingRevSide = 0;
                if (sl.IsOpen) host.QueueMarketExit(sl, "CASH_CLOSE");
                return;
            }

            if (!prevOscReady || !oscNow) return;

            bool bullCross = prevOsc <= 100.0 && _osc > 100.0;
            bool bearCross = prevOsc >= -100.0 && _osc < -100.0;
            if (!bullCross && !bearCross) return;

            int newSide = bullCross ? 1 : -1;
            if (_shadowSide == newSide) return;

            bool inWin = closeMinEt >= 570 && closeMinEt < _entryEndMinEt;
            if (_shadowSide == 0)
            {
                if (!inWin) return;
                _shadowSide = newSide;
                if (vwapOk && !sl.IsOpen && !double.IsNaN(atr20Session) && atr20Session > 0)
                    host.QueueMarketEntry(sl, newSide, _slAtrK * atr20Session);
                return;
            }

            if (!inWin)
            {
                _shadowSide = 0; _pendingRevSide = 0;
                if (sl.IsOpen) host.QueueMarketExit(sl, "OPPOSITE");
                return;
            }

            _shadowSide = newSide;
            if (sl.IsOpen)
            {
                _pendingRevSide = vwapOk ? newSide : 0;
                host.QueueMarketExit(sl, "REVERSAL");
                return;
            }
            if (vwapOk && !double.IsNaN(atr20Session) && atr20Session > 0)
                host.QueueMarketEntry(sl, newSide, _slAtrK * atr20Session);
        }

        private bool UpdateIndicator(double hi, double lo, double cl)
        {
            _ema21 = !_emaReady ? cl : _emaAlpha * cl + (1.0 - _emaAlpha) * _ema21;
            _emaReady = true;

            double tr = !_prevCloseReady ? (hi - lo)
                : Math.Max(hi - lo, Math.Max(Math.Abs(hi - _prevDecClose), Math.Abs(lo - _prevDecClose)));
            _prevDecClose = cl;
            _prevCloseReady = true;

            if (!_atrReady)
            {
                _trCount++; _trSum += tr;
                if (_trCount == 14) { _atr14 = _trSum / 14.0; _atrReady = true; }
            }
            else
            {
                _atr14 = (13.0 * _atr14 + tr) / 14.0;
            }

            if (!_atrReady || _atr14 <= 0 || double.IsNaN(_atr14)) return false;

            double raw = 100.0 * (cl - _ema21) / (_oscAtrMult * _atr14);
            _osc = !_oscReady ? raw : 0.5 * raw + 0.5 * _osc;
            _oscReady = true;
            return true;
        }
    }

    // -------------------------------------------------------------------------
    // Module Z: ZetaTrendDay (1m ETH -> 15m RTH buckets + whole-session eff%)
    // -------------------------------------------------------------------------
    internal sealed class ZetaEngine : ModuleEngineBase
    {
        private static readonly HashSet<int> NonFullNyse = new HashSet<int>
        {
            20100101, 20100118, 20100215, 20100402, 20100531, 20100705, 20100906, 20101125, 20101126, 20101224,
            20110117, 20110221, 20110422, 20110530, 20110704, 20110905, 20111124, 20111125, 20111226,
            20120102, 20120116, 20120220, 20120406, 20120528, 20120703, 20120704, 20120903, 20121029, 20121030, 20121122, 20121123, 20121224, 20121225,
            20130101, 20130121, 20130218, 20130329, 20130527, 20130703, 20130704, 20130902, 20131128, 20131129, 20131224, 20131225,
            20140101, 20140120, 20140217, 20140418, 20140526, 20140703, 20140704, 20140901, 20141127, 20141128, 20141224, 20141225,
            20150101, 20150119, 20150216, 20150403, 20150525, 20150703, 20150907, 20151126, 20151127, 20151224, 20151225,
            20160101, 20160118, 20160215, 20160325, 20160530, 20160704, 20160905, 20161124, 20161125, 20161226,
            20170102, 20170116, 20170220, 20170414, 20170529, 20170703, 20170704, 20170904, 20171123, 20171124, 20171225,
            20180101, 20180115, 20180219, 20180330, 20180528, 20180703, 20180704, 20180903, 20181122, 20181123, 20181205, 20181224, 20181225,
            20190101, 20190121, 20190218, 20190419, 20190527, 20190703, 20190704, 20190902, 20191128, 20191129, 20191224, 20191225,
            20200101, 20200120, 20200217, 20200410, 20200525, 20200703, 20200907, 20201126, 20201127, 20201224, 20201225,
            20210101, 20210118, 20210215, 20210402, 20210531, 20210705, 20210906, 20211125, 20211126, 20211224,
            20220117, 20220221, 20220415, 20220530, 20220620, 20220704, 20220905, 20221124, 20221125, 20221226,
            20230102, 20230116, 20230220, 20230407, 20230529, 20230619, 20230703, 20230704, 20230904, 20231123, 20231124, 20231225,
            20240101, 20240115, 20240219, 20240329, 20240527, 20240619, 20240703, 20240704, 20240902, 20241128, 20241129, 20241224, 20241225,
            20250101, 20250109, 20250120, 20250217, 20250418, 20250526, 20250619, 20250703, 20250704, 20250901, 20251127, 20251128, 20251224, 20251225,
            20260101, 20260119, 20260216, 20260403, 20260525, 20260619, 20260703, 20260907, 20261126, 20261127, 20261224, 20261225,
            20270101, 20270118, 20270215, 20270326, 20270531, 20270618, 20270705
        };

        private readonly int _bucketMin;
        private readonly int _emaPeriod;
        private readonly double _minEffPct;
        private readonly double _slAtrK;
        private readonly double _emaAlpha;
        private readonly double[] _emaSeed;

        private double _emaValue;
        private bool _emaReady;
        private int _emaSeedCount;

        private bool _bActive, _bValid;
        private int _bIdx, _bCount;
        private double _bH, _bL, _bC;

        private bool _sesActive, _sesValid, _sesEmaObs, _sesTouchFree;
        private int _sesDateKey, _sesBucketCount, _sesMinCount;
        private double _sesO, _sesH, _sesL, _sesC;

        private bool _pendSummaryAvail, _pendQualified;
        private int _pendSesKey;
        private bool _pendEntry;
        private int _pendEntryDir, _pendEntrySesKey;
        private double _pendEntryTarget;

        public ZetaEngine(int bucketMinutes = 15, int emaPeriod = 20, double minEffPct = 40.0, double slAtrK = 0.50)
            : base("Z_b15_e20_eff40_ATR50")
        {
            _bucketMin = bucketMinutes;
            _emaPeriod = emaPeriod;
            _minEffPct = minEffPct;
            _slAtrK = slAtrK;
            _emaAlpha = 2.0 / (emaPeriod + 1.0);
            _emaSeed = new double[emaPeriod];
        }

        private static bool IsFullNyseSession(int key)
        {
            try
            {
                var dt = new DateTime(key / 10000, (key / 100) % 100, key % 100);
                if (dt.DayOfWeek == DayOfWeek.Saturday || dt.DayOfWeek == DayOfWeek.Sunday) return false;
                if (key >= 20100101 && key <= 20270902) return !NonFullNyse.Contains(key);
                return true;
            }
            catch { return false; }
        }

        private static int NextFullNyseSession(int key)
        {
            try
            {
                var dt = new DateTime(key / 10000, (key / 100) % 100, key % 100).AddDays(1);
                for (int i = 0; i < 20; i++)
                {
                    int k = dt.Year * 10000 + dt.Month * 100 + dt.Day;
                    if (IsFullNyseSession(k)) return k;
                    dt = dt.AddDays(1);
                }
            }
            catch { }
            return 0;
        }

        private void ResetBucket() { _bActive = false; _bIdx = -1; _bCount = 0; _bValid = true; _bH = 0; _bL = 0; _bC = 0; }
        private void ResetEma() { _emaValue = 0; _emaReady = false; _emaSeedCount = 0; Array.Clear(_emaSeed, 0, _emaSeed.Length); }

        private void UpdateEma(double c)
        {
            if (!(c > 0)) return;
            if (!_emaReady)
            {
                if (_emaSeedCount < _emaPeriod) _emaSeed[_emaSeedCount++] = c;
                if (_emaSeedCount == _emaPeriod)
                {
                    double s = 0; for (int i = 0; i < _emaPeriod; i++) s += _emaSeed[i];
                    _emaValue = s / _emaPeriod;
                    _emaReady = true;
                }
                return;
            }
            _emaValue += _emaAlpha * (c - _emaValue);
        }

        public override void OnNewEthSession(int d0, double h, double l, double c, int d1) { }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            int key = bar.OpenDateCt;
            int minCt = bar.OpenMinCt;
            if (minCt < 510 || minCt >= 900 || !IsFullNyseSession(key))
                return;

            if (!_sesActive || _sesDateKey != key)
            {
                if (_sesActive) FinalizeSession();

                if (_pendSummaryAvail && NextFullNyseSession(_pendSesKey) != key)
                {
                    ResetEma();
                    _pendQualified = false;
                    _pendSummaryAvail = false;
                }

                bool qualPrev = _pendSummaryAvail && _pendQualified;
                _pendQualified = false;
                _pendSummaryAvail = false;

                if (sl.IsOpen) host.QueueMarketExit(sl, "SESSION_SAFETY");

                _sesActive = true; _sesDateKey = key; _sesValid = true;
                _sesBucketCount = 0; _sesMinCount = 0;
                _sesO = bar.Open; _sesH = bar.High; _sesL = bar.Low; _sesC = bar.Close;
                _sesEmaObs = true; _sesTouchFree = true;
                ResetBucket();

                if (minCt == 510 && qualPrev && _emaReady)
                {
                    int dir = bar.Open > _emaValue ? -1 : (bar.Open < _emaValue ? 1 : 0);
                    if (dir != 0)
                    {
                        _pendEntry = true;
                        _pendEntryDir = dir;
                        _pendEntryTarget = _emaValue;
                        _pendEntrySesKey = key;
                    }
                }
            }

            int minOff = minCt - 510;
            if (minOff != _sesMinCount) _sesValid = false;
            _sesMinCount++;
            _sesH = Math.Max(_sesH, bar.High);
            _sesL = Math.Min(_sesL, bar.Low);
            _sesC = bar.Close;

            bool bucketClosed = UpdateBucket(minOff, bar.High, bar.Low, bar.Close);

            if (_pendEntry && minCt == 510)
            {
                if (_pendEntryDir <= 0 && !(bar.Low > _pendEntryTarget)) _pendEntry = false;
                if (_pendEntryDir > 0 && !(bar.High < _pendEntryTarget)) _pendEntry = false;
            }

            if (_pendEntry && minCt == 510 && key == _pendEntrySesKey)
            {
                bool stillValid = _pendEntryDir <= 0 ? (bar.Close > _pendEntryTarget) : (bar.Close < _pendEntryTarget);
                if (stillValid && !sl.IsOpen && !double.IsNaN(atr20Session) && atr20Session > 0)
                {
                    double tgt = FundedSyncMath.RoundZetaTarget(_pendEntryDir, _pendEntryTarget, TickSize);
                    host.QueueMarketEntry(sl, _pendEntryDir, _slAtrK * atr20Session, tgt);
                }
                _pendEntry = false;
            }
            else if (_pendEntry && minCt != 510)
            {
                _pendEntry = false;
            }

            if (bucketClosed && sl.IsOpen)
            {
                double newTgt = FundedSyncMath.RoundZetaTarget(sl.Side, _emaValue, TickSize);
                if (!double.IsNaN(newTgt)) sl.TargetPrice = newTgt;
            }

            if (minCt >= 899 && sl.IsOpen) host.QueueMarketExit(sl, "EOD");
            if (minCt == 899) FinalizeSession();
        }

        private bool UpdateBucket(int minOff, double hi, double lo, double cl)
        {
            int bIdx = minOff / _bucketMin;
            int bMin = minOff % _bucketMin;

            if (_bActive && _bIdx != bIdx) { _sesValid = false; ResetBucket(); ResetEma(); }
            if (!_bActive)
            {
                _bActive = true; _bIdx = bIdx; _bCount = 0;
                _bValid = (bMin == 0) && (bIdx == _sesBucketCount);
                _bH = hi; _bL = lo; _bC = cl;
            }
            else { _bH = Math.Max(_bH, hi); _bL = Math.Min(_bL, lo); _bC = cl; }

            if (bMin != _bCount) _bValid = false;
            _bCount++;
            if (bMin != _bucketMin - 1) return false;

            if (!_bValid || _bCount != _bucketMin) { _sesValid = false; ResetEma(); ResetBucket(); return false; }

            if (!_emaReady) _sesEmaObs = false;
            else if (_bL <= _emaValue && _emaValue <= _bH) _sesTouchFree = false;

            UpdateEma(_bC);
            _sesBucketCount++;
            ResetBucket();
            return true;
        }

        private void FinalizeSession()
        {
            if (!_sesActive) return;
            if (_bActive) { _sesValid = false; ResetBucket(); ResetEma(); }

            int expMin = 390;
            int expBuckets = expMin / _bucketMin;
            bool allValid = _sesValid && _sesMinCount == expMin && _sesBucketCount == expBuckets;
            double sesRange = _sesH - _sesL;
            double eff = sesRange <= 0 ? 0.0 : (100.0 * Math.Abs(_sesC - _sesO) / sesRange);

            _pendSummaryAvail = true;
            _pendQualified = allValid && _sesEmaObs && sesRange > 0 && _sesTouchFree && eff >= _minEffPct;
            _pendSesKey = _sesDateKey;
            if (!allValid) ResetEma();
            _sesActive = false;
            ResetBucket();
        }
    }

    // -------------------------------------------------------------------------
    // Module T: FtmOrb (15m ORB 09:30-09:45 ET + Quarterly KNN + +1.5R M1 BE)
    // -------------------------------------------------------------------------
    internal sealed class FtmOrbEngine : ModuleEngineBase
    {
        private sealed class DirectionRow
        {
            public int SessionKey;
            public double[] Features;
            public bool FlipWins;
            public int Sequence;
        }

        private sealed class ShadowTrade
        {
            public int Side;
            public double Entry;
            public double ActiveStop;
            public double Target;
            public double RiskPts;
            public double ManagedTrigR;
            public double ManagedLockR;
            public bool Complete;
            public bool PendCondExit;
            public double ExitPrice;
        }

        private sealed class ShadowPair
        {
            public int SessionKey;
            public DateTime ExpParentFillCloseUtc;
            public int BaselineSide;
            public double[] Features;
            public bool PriorTrendAvail;
            public double PriorTrendBps;
            public bool Initialized;
            public bool Invalid;
            public bool LabelRecorded;
            public ShadowTrade Breakout;
            public ShadowTrade Fade;
        }

        private sealed class PendingDecision
        {
            public DateTime ExpObsOpenUtc;
            public int Side;
            public int ReqBars;
            public int ObservedBars;
            public double FirstObsOpen;
            public string Branch;
            public double[] Features;
            public int BaselineSide;
            public double SignalClose;
            public bool IsFinalStage;
            public bool SubmitActual;
        }

        private readonly double _beTriggerR;
        private readonly double _stopOrbMult;
        private readonly double _stopMinPts;
        private readonly double _stopMaxPts;
        private readonly List<double> _eligOrbHistBps = new List<double>();
        private readonly List<double> _eligRthCloseHist = new List<double>();
        private readonly List<double> _eligSesRetHistBps = new List<double>();
        private readonly List<DirectionRow> _trainRows = new List<DirectionRow>();
        private readonly List<BarTimeContext> _m1Buf = new List<BarTimeContext>();

        private int _trainSeq;
        private int _activeQuarterKey;
        private double[,] _knnTrainX;
        private bool[] _knnTrainFlip;
        private int[] _knnTrainSeq;
        private double[] _knnMean = new double[14];
        private double[] _knnScale = new double[14];
        private int _knnRowsCount;

        private int _curCashDate = -1, _prevDayOfCash = -1;
        private bool _sesElig, _refOpenCap, _dayBlocked = true, _orbFinalized, _boConsumed, _cashExitTrig, _cashWinInt, _orbHistRec, _rthCloseRec;
        private double _refSesOpen;
        private int _orbBarCount, _expNextOrbOpenMin = 570;
        private double _orbHigh, _orbLow, _orbOpen, _orbClose, _curOrbBps, _curOrbQ75Bps, _curPriorTrendBps;
        private bool _curOrbQ75Avail, _curPriorTrendAvail;
        private readonly List<double> _rthMinCloses = new List<double>();
        private double _rthTypVolSum, _rthVolSum;
        private DateTime _lastCashCloseUtc;

        private ShadowPair _activeShadow;
        private PendingDecision _pendDec1;
        private PendingDecision _pendDec2;

        // Live T trade IL quarter-hour lock state (in addition to M1 +1.5R BE overlay)
        private double _liveTrigR, _liveLockR, _liveIlRiskPts;
        private bool _liveIlActivated, _condExitReq;

        public FtmOrbEngine(double stopOrbMult = 1.0, double beTriggerR = 1.5, double stopMinPts = 2.0, double stopMaxPts = 100.0) : base("T_stop100_BE15R_calFalse")
        {
            _stopOrbMult = stopOrbMult;
            _beTriggerR = beTriggerR;
            _stopMinPts = stopMinPts;
            _stopMaxPts = stopMaxPts;
        }

        public override void OnNewEthSession(int d0, double h, double l, double c, int d1) { }

        public override void UpdateM1OverlayProtectionsOnClose(VirtualSleeve sl, BarTimeContext bar)
        {
            if (_beTriggerR > 0 && sl.IsOpen && !sl.OverlayBeActivated)
            {
                if (sl.MaxFavPts >= _beTriggerR * Math.Max(sl.RiskPts, 1e-6))
                {
                    if ((sl.Side > 0 && sl.EntryPrice > sl.StopPrice) || (sl.Side < 0 && sl.EntryPrice < sl.StopPrice))
                        sl.StopPrice = sl.EntryPrice;
                    sl.OverlayBeActivated = true;
                }
            }
        }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            _m1Buf.Add(bar);
            if (_m1Buf.Count > 32) _m1Buf.RemoveAt(0);
            if (_m1Buf.Count < 16) return;

            int cashDate = bar.EthTradeDate;
            if (cashDate != _curCashDate)
            {
                BeginCashDate(cashDate, sl, host);
                if (bar.CloseMinEt < 570) _cashWinInt = true; // will verify ref open & full window dynamically
            }

            if (_sesElig && !_refOpenCap && bar.OpenHhmmUtc == 2300 && bar.OpenDateUtc == _prevDayOfCash)
            {
                if (!bar.ExactMinute || !(bar.Open > 0)) _dayBlocked = true;
                else { _refSesOpen = bar.Open; _refOpenCap = true; }
            }

            bool sameEt = (bar.OpenDateEt == _curCashDate && bar.CloseDateEt == _curCashDate);
            bool inCash = sameEt && bar.OpenMinEt >= 570 && bar.CloseMinEt <= 960;
            if (inCash && !bar.ExactMinute)
            {
                _dayBlocked = true; _boConsumed = true; InvalidatePending();
                if (sl.IsOpen) host.QueueMarketExit(sl, "CashTimeAlignment");
                return;
            }

            if (inCash)
            {
                if (_lastCashCloseUtc != DateTime.MinValue && bar.OpenUtc != _lastCashCloseUtc)
                {
                    _cashWinInt = false; _dayBlocked = true; _boConsumed = true; InvalidatePending();
                    if (sl.IsOpen) host.QueueMarketExit(sl, "CashDataGap");
                    return;
                }
                _lastCashCloseUtc = bar.CloseUtc;
                if (!_dayBlocked)
                {
                    _rthMinCloses.Add(bar.Close);
                    _rthTypVolSum += ((bar.High + bar.Low + bar.Close) / 3.0) * bar.Volume;
                    _rthVolSum += bar.Volume;
                }
            }

            // Shadow Pair advancement
            if (sameEt && _activeShadow != null && !_activeShadow.Invalid && !_activeShadow.LabelRecorded)
            {
                if (!_activeShadow.Initialized)
                {
                    if (bar.OpenUtc >= _activeShadow.ExpParentFillCloseUtc)
                    {
                        if (bar.OpenUtc != _activeShadow.ExpParentFillCloseUtc) _activeShadow.Invalid = true;
                        else
                        {
                            _activeShadow.Breakout = CreateShadowTrade(_activeShadow.BaselineSide, bar.Open, _activeShadow.PriorTrendAvail, _activeShadow.PriorTrendBps);
                            _activeShadow.Fade = CreateShadowTrade(-_activeShadow.BaselineSide, bar.Open, _activeShadow.PriorTrendAvail, _activeShadow.PriorTrendBps);
                            _activeShadow.Initialized = true;
                        }
                    }
                }
                if (_activeShadow.Initialized && !_activeShadow.Invalid)
                {
                    StepShadowTrade(_activeShadow.Breakout, bar);
                    StepShadowTrade(_activeShadow.Fade, bar);
                    TryRecordLabel();
                }
            }

            // Pending Stage 1 Decision
            if (sameEt && _pendDec1 != null && !_dayBlocked && bar.OpenUtc >= _pendDec1.ExpObsOpenUtc)
            {
                if (bar.OpenUtc != _pendDec1.ExpObsOpenUtc || !bar.ExactMinute) { _pendDec1 = null; _dayBlocked = true; }
                else
                {
                    if (_pendDec1.ObservedBars == 0) _pendDec1.FirstObsOpen = bar.Open;
                    _pendDec1.ObservedBars++;
                    _pendDec1.ExpObsOpenUtc = bar.CloseUtc;
                    if (_pendDec1.ObservedBars >= _pendDec1.ReqBars)
                    {
                        int rSide = _pendDec1.Side;
                        if (_pendDec1.Branch == "high_vol_touch_vote")
                        {
                            double mv = rSide * (bar.Close - _pendDec1.FirstObsOpen);
                            if (!(mv > 0.0)) rSide = -rSide;
                        }
                        var dec = _pendDec1; _pendDec1 = null;
                        ApplyFinalRefinementOrSubmit(rSide, bar.CloseUtc, dec.SubmitActual, dec.BaselineSide, dec.Features, dec.SignalClose, sl, host);
                    }
                }
            }

            // Pending Stage 2 Decision
            if (sameEt && _pendDec2 != null && !_dayBlocked && bar.OpenUtc >= _pendDec2.ExpObsOpenUtc)
            {
                if (bar.OpenUtc != _pendDec2.ExpObsOpenUtc || !bar.ExactMinute) { _pendDec2 = null; _dayBlocked = true; }
                else
                {
                    if (_pendDec2.ObservedBars == 0) _pendDec2.FirstObsOpen = bar.Open;
                    _pendDec2.ObservedBars++;
                    _pendDec2.ExpObsOpenUtc = bar.CloseUtc;
                    if (_pendDec2.ObservedBars >= _pendDec2.ReqBars)
                    {
                        double obsMv = _pendDec2.Side * (bar.Close - _pendDec2.FirstObsOpen);
                        int fSide = (_pendDec2.Branch == "prior_session_disagreement" || obsMv > 0.0) ? -_pendDec2.Side : _pendDec2.Side;
                        bool sub = _pendDec2.SubmitActual;
                        _pendDec2 = null;
                        if (sub) SubmitLiveEntry(fSide, sl, host);
                    }
                }
            }

            // CashClose 16:00 ET
            if (sameEt && bar.CloseMinEt >= 960)
            {
                if (_activeShadow != null)
                {
                    if (_activeShadow.Invalid || !_activeShadow.Initialized) _activeShadow = null;
                    else
                    {
                        if (!_activeShadow.Breakout.Complete) { _activeShadow.Breakout.ExitPrice = bar.Close - _activeShadow.Breakout.Side * TickSize; _activeShadow.Breakout.Complete = true; }
                        if (!_activeShadow.Fade.Complete) { _activeShadow.Fade.ExitPrice = bar.Close - _activeShadow.Fade.Side * TickSize; _activeShadow.Fade.Complete = true; }
                        TryRecordLabel();
                    }
                }
                if (!_rthCloseRec && _sesElig && _cashWinInt && _orbFinalized && _refOpenCap)
                {
                    if (!_orbHistRec)
                    {
                        _eligOrbHistBps.Add(_curOrbBps);
                        if (_eligOrbHistBps.Count > 120) _eligOrbHistBps.RemoveAt(0);
                        _orbHistRec = true;
                    }
                    if (bar.Close > 0)
                    {
                        double sRet = SafeRetBps(bar.Close, _refSesOpen);
                        _eligRthCloseHist.Add(bar.Close);
                        if (_eligRthCloseHist.Count > 21) _eligRthCloseHist.RemoveAt(0);
                        _eligSesRetHistBps.Clear();
                        _eligSesRetHistBps.Add(sRet);
                        _rthCloseRec = true;
                    }
                }
                _cashExitTrig = true; _dayBlocked = true;
                if (sl.IsOpen) host.QueueMarketExit(sl, "CashClose1600ET");
                return;
            }

            if (_cashExitTrig)
            {
                if (sl.IsOpen) host.QueueMarketExit(sl, "CashExitFollowup");
                return;
            }

            bool isQtr = inCash && bar.CloseMinEt >= 600 && bar.CloseMinEt < 960 && (bar.CloseMinEt % 15 == 0);
            if (sl.IsOpen)
            {
                if (isQtr && !_liveIlActivated && _liveIlRiskPts > 0)
                {
                    double closeR = sl.Side * (bar.Close - sl.EntryPrice) / _liveIlRiskPts;
                    if (closeR >= _liveTrigR)
                    {
                        double newS = FundedSyncMath.RoundTick(sl.EntryPrice + sl.Side * _liveIlRiskPts * _liveLockR, TickSize);
                        if ((sl.Side > 0 && newS > sl.StopPrice) || (sl.Side < 0 && newS < sl.StopPrice))
                            sl.StopPrice = newS;
                        _liveIlActivated = true;
                    }
                }
                if (inCash && bar.CloseMinEt == 930 && !_condExitReq && _liveIlRiskPts > 0)
                {
                    double closeR = sl.Side * (bar.Close - sl.EntryPrice) / _liveIlRiskPts;
                    if (closeR < 0.0 || closeR >= 1.0)
                    {
                        _condExitReq = true;
                        host.QueueMarketExit(sl, "Conditional1530ET");
                    }
                }
                return;
            }

            int dow = FundedSyncMath.WeekdayMon0(new DateTime(_curCashDate / 10000, (_curCashDate / 100) % 100, _curCashDate % 100));
            if (_dayBlocked || dow >= 5) return;

            if (!_orbFinalized)
            {
                if (sameEt && bar.OpenMinEt >= 570 && bar.OpenMinEt < 585)
                {
                    if (bar.OpenMinEt != _expNextOrbOpenMin || bar.CloseMinEt != bar.OpenMinEt + 1) { _dayBlocked = true; return; }
                    if (_orbBarCount == 0) _orbOpen = bar.Open;
                    _orbHigh = _orbBarCount == 0 ? bar.High : Math.Max(_orbHigh, bar.High);
                    _orbLow = _orbBarCount == 0 ? bar.Low : Math.Min(_orbLow, bar.Low);
                    _orbClose = bar.Close;
                    _orbBarCount++; _expNextOrbOpenMin++;
                    if (bar.CloseMinEt == 585)
                    {
                        if (_orbBarCount != 15 || !(_orbHigh >= _orbLow)) { _dayBlocked = true; return; }
                        _orbFinalized = true;
                        double mid = (_orbHigh + _orbLow) * 0.5;
                        _curOrbBps = mid > 0 ? ((_orbHigh - _orbLow) / mid) * 10000.0 : 0.0;
                        _curOrbQ75Avail = _eligOrbHistBps.Count == 120;
                        if (_curOrbQ75Avail) _curOrbQ75Bps = LinearPercentile(_eligOrbHistBps, 0.75);
                    }
                }
                else if (sameEt && bar.CloseMinEt > 585) { _dayBlocked = true; return; }
            }

            if (_dayBlocked || !_orbFinalized || _boConsumed || !isQtr) return;

            double lTrig = FundedSyncMath.RoundTick(_orbHigh + TickSize, TickSize);
            double sTrig = FundedSyncMath.RoundTick(_orbLow - TickSize, TickSize);
            if (bar.Close < lTrig && bar.Close > sTrig) return;

            int baseSide = bar.Close >= lTrig ? 1 : -1;
            EvaluateAdmissionAndDirection(bar, baseSide, sl, host);
        }

        private void BeginCashDate(int cashKey, VirtualSleeve sl, PortfolioCoordinator host)
        {
            bool hasExp = sl.IsOpen || sl.HasPendingEntry;
            InvalidatePending();
            _curCashDate = cashKey;
            var dt = new DateTime(cashKey / 10000, (cashKey / 100) % 100, cashKey % 100);
            _prevDayOfCash = FundedSyncMath.DateKey(dt.AddDays(-1));

            _sesElig = true; _refOpenCap = false; _refSesOpen = 0;
            _dayBlocked = hasExp; _orbFinalized = false; _boConsumed = hasExp;
            _cashExitTrig = false; _cashWinInt = true; _orbHistRec = false; _rthCloseRec = false;
            _liveIlActivated = false; _condExitReq = false;
            _orbBarCount = 0; _expNextOrbOpenMin = 570;
            _orbHigh = double.MinValue; _orbLow = double.MaxValue;
            _orbOpen = 0; _orbClose = 0; _curOrbBps = 0; _curOrbQ75Bps = 0; _curOrbQ75Avail = false;

            if (_eligRthCloseHist.Count >= 21 && _eligRthCloseHist[0] > 0)
            {
                _curPriorTrendBps = SafeRetBps(_eligRthCloseHist[_eligRthCloseHist.Count - 1], _eligRthCloseHist[0]);
                _curPriorTrendAvail = true;
            }
            else { _curPriorTrendBps = 0; _curPriorTrendAvail = false; }

            _rthMinCloses.Clear(); _rthTypVolSum = 0; _rthVolSum = 0; _lastCashCloseUtc = DateTime.MinValue;
            if (hasExp && sl.IsOpen) host.QueueMarketExit(sl, "OvernightExposureOrEntry");
            if (!FundedSyncMath.IsFullNyseTradingDay(dt)) { _sesElig = false; _dayBlocked = true; }
        }

        private void InvalidatePending() { _pendDec1 = null; _pendDec2 = null; _activeShadow = null; }

        private void EvaluateAdmissionAndDirection(BarTimeContext bar, int baseSide, VirtualSleeve sl, PortfolioCoordinator host)
        {
            int idx = _m1Buf.Count - 1;
            double sigOpen = _m1Buf[idx - 14].Open;
            double sigHi = double.MinValue, sigLo = double.MaxValue;
            DateTime cUtc = bar.CloseUtc;
            for (int k = 0; k < 15; k++)
            {
                var b = _m1Buf[idx - k];
                if (b.CloseUtc != cUtc.AddMinutes(-k)) { _boConsumed = true; _dayBlocked = true; return; }
                if (b.High > sigHi) sigHi = b.High;
                if (b.Low < sigLo) sigLo = b.Low;
            }
            if (!(sigHi > sigLo)) { _boConsumed = true; _dayBlocked = true; return; }
            double sigClose = bar.Close, sigRng = sigHi - sigLo;
            double body = baseSide * (sigClose - sigOpen) / sigRng;
            double closeLoc = baseSide == 1 ? (sigClose - sigLo) / sigRng : (sigHi - sigClose) / sigRng;
            if (body < 0.15 || closeLoc < 0.60) return;

            double confLvl = baseSide == 1 ? _orbHigh + TickSize : _orbLow - TickSize;
            int touches = 0;
            for (int k = 0; k < 15; k++)
            {
                if (baseSide == 1) { if (_m1Buf[idx - k].High >= confLvl) touches++; }
                else { if (_m1Buf[idx - k].Low <= confLvl) touches++; }
            }
            if (touches < 3) { _boConsumed = true; return; }

            if (!(_orbOpen > 0 && _orbClose > 0 && _rthVolSum > 0) || _rthMinCloses.Count == 0)
            {
                _boConsumed = true; _dayBlocked = true; return;
            }

            double prevRthC = _eligRthCloseHist.Count > 0 ? _eligRthCloseHist[_eligRthCloseHist.Count - 1] : _orbOpen;
            double priorSesBps = _eligSesRetHistBps.Count > 0 ? _eligSesRetHistBps[_eligSesRetHistBps.Count - 1] : 0.0;
            double priorRet5 = LagRetBps(_eligRthCloseHist, 5);
            double priorRet20 = LagRetBps(_eligRthCloseHist, 20);
            double vwap = _rthTypVolSum / _rthVolSum;
            double c30Ago = _rthMinCloses.Count <= 30 ? _orbClose : _rthMinCloses[_rthMinCloses.Count - 31];
            double gapBps = SafeRetBps(_orbOpen, prevRthC);
            double vwapDist = SafeRetBps(sigClose, vwap);
            double ret30m = SafeRetBps(sigClose, c30Ago);
            double elapsed15m = (bar.CloseMinEt - 585) / 15.0;

            var dtCash = new DateTime(_curCashDate / 10000, (_curCashDate / 100) % 100, _curCashDate % 100);
            int wk = FundedSyncMath.WeekdayMon0(dtCash);
            int mo = dtCash.Month;
            double twoPi = 6.2831853071795862;
            var feat = new double[]
            {
                baseSide * gapBps, baseSide * priorSesBps, baseSide * priorRet5, baseSide * priorRet20,
                baseSide * vwapDist, baseSide * ret30m, baseSide, elapsed15m, _curOrbBps, touches,
                Math.Sin(twoPi * wk / 5.0), Math.Cos(twoPi * wk / 5.0),
                Math.Sin(twoPi * (mo - 1) / 12.0), Math.Cos(twoPi * (mo - 1) / 12.0)
            };
            for (int f = 0; f < 14; f++) if (double.IsNaN(feat[f]) || double.IsInfinity(feat[f])) { _boConsumed = true; _dayBlocked = true; return; }

            _boConsumed = true;
            bool priorOverride = (baseSide * priorSesBps) < -300.0;
            bool knnOverride = false;
            if (_curCashDate >= 20120101)
            {
                int qKey = dtCash.Year * 10 + ((dtCash.Month - 1) / 3 + 1);
                if (_activeQuarterKey != qKey)
                {
                    FitQuarterKnn(dtCash);
                    _activeQuarterKey = qKey;
                }
                knnOverride = PredictKnnFlipProb(feat) > 0.65;
            }
            int dirSide = (priorOverride || knnOverride) ? -baseSide : baseSide;

            if (_activeShadow != null) { InvalidatePending(); _dayBlocked = true; return; }
            _activeShadow = new ShadowPair
            {
                SessionKey = _curCashDate,
                ExpParentFillCloseUtc = bar.CloseUtc,
                BaselineSide = baseSide,
                Features = feat,
                PriorTrendAvail = _curPriorTrendAvail,
                PriorTrendBps = _curPriorTrendBps
            };

            bool ctxReady = _curOrbQ75Avail && _curPriorTrendAvail;
            bool submitActual = (_curCashDate >= 20120101) && ctxReady && _sesElig;

            if (Math.Abs(elapsed15m - 1.0) < 1e-6 && !(feat[4] > 20.0))
            {
                if (submitActual) SubmitLiveEntry(baseSide, sl, host);
                return;
            }

            bool weakSig = !(dirSide * (sigClose - sigOpen) / sigRng > 0.20);
            bool hiVol = _curOrbQ75Avail && _curOrbBps > _curOrbQ75Bps;
            double dLvl = dirSide == 1 ? _orbHigh + TickSize : _orbLow - TickSize;
            int dTouch = 0;
            for (int k = 0; k < 15; k++)
            {
                if (dirSide == 1) { if (_m1Buf[idx - k].High >= dLvl) dTouch++; }
                else { if (_m1Buf[idx - k].Low <= dLvl) dTouch++; }
            }
            bool hiVolVote = hiVol && !(dTouch > 3);

            if (weakSig || hiVolVote)
            {
                _pendDec1 = new PendingDecision
                {
                    ExpObsOpenUtc = bar.CloseUtc, Side = dirSide, ReqBars = weakSig ? 1 : 3,
                    Branch = weakSig ? "weak_signal_delay_keep" : "high_vol_touch_vote",
                    Features = feat, BaselineSide = baseSide, SignalClose = sigClose, SubmitActual = submitActual
                };
            }
            else
            {
                ApplyFinalRefinementOrSubmit(dirSide, bar.CloseUtc, submitActual, baseSide, feat, sigClose, sl, host);
            }
        }

        private void ApplyFinalRefinementOrSubmit(int refSide, DateTime fillUtc, bool submitActual, int baseSide, double[] feat, double sigClose, VirtualSleeve sl, PortfolioCoordinator host)
        {
            double orbR = _orbHigh - _orbLow;
            if (!(orbR > 0)) { _dayBlocked = true; return; }
            double sFlip = refSide * baseSide;
            double alPrior = sFlip * feat[1];
            double alRet30 = sFlip * feat[5];
            double orbBody = refSide * (_orbClose - _orbOpen) / orbR;
            double edge = refSide == 1 ? _orbHigh : _orbLow;
            double sigExt = refSide * (sigClose - edge) / orbR;

            if (alPrior > 100.0 && !(orbBody > 0))
            {
                _pendDec2 = new PendingDecision { ExpObsOpenUtc = fillUtc, Side = refSide, ReqBars = 2, Branch = "prior_session_disagreement", IsFinalStage = true, SubmitActual = submitActual };
            }
            else if (alRet30 > 25.0 && !(sigExt > 0.25))
            {
                _pendDec2 = new PendingDecision { ExpObsOpenUtc = fillUtc, Side = refSide, ReqBars = 1, Branch = "intraday_continuation", IsFinalStage = true, SubmitActual = submitActual };
            }
            else if (submitActual)
            {
                SubmitLiveEntry(refSide, sl, host);
            }
        }

        private void SubmitLiveEntry(int side, VirtualSleeve sl, PortfolioCoordinator host)
        {
            if (sl.IsOpen || sl.HasPendingEntry) return;
            double orbRng = _orbHigh - _orbLow;
            double stopPts = Math.Max(_stopMinPts, Math.Min(_stopMaxPts, _stopOrbMult * orbRng));
            double ilRiskPts = Math.Max(_stopMinPts, Math.Min(_stopMaxPts, 1.25 * orbRng));
            double tgtR, trigR, lockR;
            SelectPlan(side, _curPriorTrendAvail, _curPriorTrendBps, out tgtR, out trigR, out lockR);
            int tgtTicks = RoundOffsetTicks(ilRiskPts * tgtR, side > 0);
            _liveIlRiskPts = ilRiskPts; _liveTrigR = trigR; _liveLockR = lockR; _liveIlActivated = false; _condExitReq = false;
            host.QueueMarketEntry(sl, side, stopPts, double.NaN, tgtTicks * TickSize);
        }

        private void SelectPlan(int side, bool priorAvail, double priorBps, out double tgtR, out double trigR, out double lockR)
        {
            if (_curOrbQ75Avail && _curOrbBps > _curOrbQ75Bps) { tgtR = 1.25; trigR = 1.25; lockR = 0.0; return; }
            if (priorAvail && (side * priorBps) < 0.0) { tgtR = 3.0; trigR = 0.75; lockR = 0.10; return; }
            tgtR = 3.0; trigR = 1.25; lockR = 0.0;
        }

        private ShadowTrade CreateShadowTrade(int side, double parentOpen, bool ptAvail, double ptBps)
        {
            double epx = parentOpen + side * TickSize;
            double rawD = Math.Max(_stopMinPts, Math.Min(_stopMaxPts, (_orbHigh - _orbLow) * 1.25));
            double stopP = FundedSyncMath.RoundTick(epx - side * rawD, TickSize);
            double rPts = side * (epx - stopP);
            double tgtR, trigR, lockR;
            SelectPlan(side, ptAvail, ptBps, out tgtR, out trigR, out lockR);
            double tgtP = FundedSyncMath.RoundTick(epx + side * rawD * tgtR, TickSize);
            var st = new ShadowTrade { Side = side, Entry = epx, ActiveStop = stopP, Target = tgtP, RiskPts = rPts, ManagedTrigR = trigR, ManagedLockR = lockR };
            if (!(rPts > 0)) { st.Complete = true; st.ExitPrice = epx; }
            return st;
        }

        private void StepShadowTrade(ShadowTrade st, BarTimeContext bar)
        {
            if (st.Complete) return;
            if (st.PendCondExit) { st.ExitPrice = bar.Open - st.Side * TickSize; st.Complete = true; st.PendCondExit = false; return; }
            bool hitSl = st.Side == 1 ? (bar.Low <= st.ActiveStop) : (bar.High >= st.ActiveStop);
            bool hitTp = st.Side == 1 ? (bar.High >= st.Target) : (bar.Low <= st.Target);
            if (hitSl)
            {
                double fill = st.Side == 1 ? Math.Min(st.ActiveStop, bar.Open) : Math.Max(st.ActiveStop, bar.Open);
                st.ExitPrice = fill - st.Side * TickSize; st.Complete = true; return;
            }
            if (hitTp)
            {
                st.ExitPrice = st.Side == 1 ? Math.Max(st.Target, bar.Open) : Math.Min(st.Target, bar.Open);
                st.Complete = true; return;
            }
            if (bar.CloseMinEt < 960 && bar.CloseMinEt % 15 == 0)
            {
                double cr = st.Side * (bar.Close - st.Entry) / st.RiskPts;
                if (cr >= st.ManagedTrigR)
                {
                    double ns = FundedSyncMath.RoundTick(st.Entry + st.Side * st.RiskPts * st.ManagedLockR, TickSize);
                    st.ActiveStop = st.Side == 1 ? Math.Max(st.ActiveStop, ns) : Math.Min(st.ActiveStop, ns);
                }
                if (bar.CloseMinEt == 930 && (cr < 0.0 || cr >= 1.0)) st.PendCondExit = true;
            }
        }

        private void TryRecordLabel()
        {
            var sp = _activeShadow;
            if (sp == null || sp.Invalid || sp.LabelRecorded || !sp.Initialized) return;
            if (!sp.Breakout.Complete || !sp.Fade.Complete) return;
            double boNet = sp.Breakout.Side * (sp.Breakout.ExitPrice - sp.Breakout.Entry) * 20.0 - 2.5;
            double faNet = sp.Fade.Side * (sp.Fade.ExitPrice - sp.Fade.Entry) * 20.0 - 2.5;
            bool flipWins = faNet > 0.0;
            if ((boNet > 0.0) != flipWins)
                _trainRows.Add(new DirectionRow { SessionKey = sp.SessionKey, Features = sp.Features, FlipWins = flipWins, Sequence = _trainSeq++ });
            sp.LabelRecorded = true;
            _activeShadow = null;
        }

        private void FitQuarterKnn(DateTime dtCash)
        {
            int qStartMo = ((dtCash.Month - 1) / 3) * 3 + 1;
            int cutoff = FundedSyncMath.DateKey(new DateTime(dtCash.Year, qStartMo, 1).AddDays(-1));
            var elig = new List<DirectionRow>(_trainRows.Count);
            foreach (var r in _trainRows) if (r.SessionKey <= cutoff) elig.Add(r);
            _knnRowsCount = elig.Count;
            if (_knnRowsCount < 100) return;

            for (int f = 0; f < 14; f++)
            {
                double s = 0; for (int i = 0; i < _knnRowsCount; i++) s += elig[i].Features[f];
                double mu = s / _knnRowsCount;
                double v = 0; for (int i = 0; i < _knnRowsCount; i++) { double d = elig[i].Features[f] - mu; v += d * d; }
                _knnMean[f] = mu;
                double sc = Math.Sqrt(v / _knnRowsCount);
                _knnScale[f] = sc > 0 ? sc : 1.0;
            }

            _knnTrainX = new double[_knnRowsCount, 14];
            _knnTrainFlip = new bool[_knnRowsCount];
            _knnTrainSeq = new int[_knnRowsCount];
            for (int i = 0; i < _knnRowsCount; i++)
            {
                for (int f = 0; f < 14; f++) _knnTrainX[i, f] = (elig[i].Features[f] - _knnMean[f]) / _knnScale[f];
                _knnTrainFlip[i] = elig[i].FlipWins;
                _knnTrainSeq[i] = elig[i].Sequence;
            }
        }

        private double PredictKnnFlipProb(double[] feat)
        {
            if (_knnRowsCount < 100 || _knnTrainX == null) return 0.0;
            var fz = new double[14];
            for (int f = 0; f < 14; f++) fz[f] = (feat[f] - _knnMean[f]) / _knnScale[f];
            var list = new List<Tuple<double, int, bool>>(_knnRowsCount);
            for (int i = 0; i < _knnRowsCount; i++)
            {
                double d2 = 0;
                for (int f = 0; f < 14; f++) { double df = _knnTrainX[i, f] - fz[f]; d2 += df * df; }
                list.Add(Tuple.Create(Math.Sqrt(d2), _knnTrainSeq[i], _knnTrainFlip[i]));
            }
            list.Sort((a, b) => { int c = a.Item1.CompareTo(b.Item1); return c != 0 ? c : a.Item2.CompareTo(b.Item2); });
            int flips = 0;
            for (int k = 0; k < 15; k++) if (list[k].Item3) flips++;
            return (flips + 2.0) / (15.0 + 4.0);
        }

        private static double SafeRetBps(double num, double den) { return den == 0 ? 0.0 : (num / den - 1.0) * 10000.0; }
        private static double LagRetBps(List<double> v, int p) { return v.Count <= p ? 0.0 : SafeRetBps(v[v.Count - 1], v[v.Count - 1 - p]); }
        private int RoundOffsetTicks(double pts, bool ceil)
        {
            double t = pts / TickSize;
            return ceil ? (int)Math.Ceiling(t - 0.5) : (int)Math.Floor(t + 0.5);
        }
        private static double LinearPercentile(List<double> vals, double q)
        {
            var arr = vals.ToArray(); Array.Sort(arr);
            double pos = (arr.Length - 1) * q;
            int lo = (int)Math.Floor(pos), hi = (int)Math.Ceiling(pos);
            return lo == hi ? arr[lo] : arr[lo] + (arr[hi] - arr[lo]) * (pos - lo);
        }
    }

    // -------------------------------------------------------------------------
    // Module V: VaultBreak (5m RTH 08:30-15:15 CT, Long-only, 252d range)
    // -------------------------------------------------------------------------
    internal sealed class VaultBreakEngine : ModuleEngineBase
    {
        private readonly double _noiseMult;
        private readonly double _slAtrK;
        private readonly double _tpPts;
        private readonly Queue<double> _rthRanges252 = new Queue<double>();
        private double _rthSum, _dailyAtr, _sesOpen, _sesHi, _sesLo, _noiseUp, _cumVol, _cumPv, _sesVwap;
        private int _curRthDateCt = -1, _tradesToday, _belowVwap;
        private bool _hasSes;
        private bool _hasB5;
        private int _b5Bucket = -1, _b5DateCt = -1;
        private double _b5O, _b5H, _b5L, _b5C, _b5V;

        public VaultBreakEngine(double noiseMult = 0.25, double slAtrK = 0.30, double tpPts = 0.0) : base("V_nm25_noCap_mae30")
        {
            _noiseMult = noiseMult;
            _slAtrK = slAtrK;
            _tpPts = tpPts;
        }

        public override void OnNewEthSession(int d0, double h, double l, double c, int d1) { }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            int ctMin = bar.OpenMinCt;
            if (ctMin < 510 || ctMin >= 915)
            {
                if (_hasB5) Flush5mBar(bar, atr20Session, sl, host);
                return;
            }

            int bId = (ctMin - 510) / 5;
            if (_hasB5 && (_b5DateCt != bar.OpenDateCt || _b5Bucket != bId))
                Flush5mBar(bar, atr20Session, sl, host);

            if (!_hasB5)
            {
                _hasB5 = true; _b5DateCt = bar.OpenDateCt; _b5Bucket = bId;
                _b5O = bar.Open; _b5H = bar.High; _b5L = bar.Low; _b5C = bar.Close; _b5V = bar.Volume;
            }
            else
            {
                _b5H = Math.Max(_b5H, bar.High); _b5L = Math.Min(_b5L, bar.Low); _b5C = bar.Close; _b5V += bar.Volume;
            }

            if ((bar.CloseMinEt % 5) == 0)
                Flush5mBar(bar, atr20Session, sl, host);
        }

        private void Flush5mBar(BarTimeContext curM1, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            _hasB5 = false;
            if (_b5DateCt != _curRthDateCt)
            {
                if (_hasSes)
                {
                    double pr = _sesHi - _sesLo;
                    if (pr > 0)
                    {
                        _rthRanges252.Enqueue(pr); _rthSum += pr;
                        if (_rthRanges252.Count > 252) _rthSum -= _rthRanges252.Dequeue();
                    }
                }
                _dailyAtr = _rthRanges252.Count < 252 ? 0.0 : _rthSum / _rthRanges252.Count;
                _curRthDateCt = _b5DateCt;
                _sesOpen = _b5O; _sesHi = _b5H; _sesLo = _b5L;
                _noiseUp = _dailyAtr <= 0 ? 0.0 : _sesOpen + _noiseMult * _dailyAtr;
                _cumVol = 0; _cumPv = 0; _sesVwap = _b5C;
                _tradesToday = 0; _belowVwap = 0; _hasSes = true;
            }
            if (!_hasSes) return;

            if (_b5H > _sesHi) _sesHi = _b5H;
            if (_b5L < _sesLo) _sesLo = _b5L;
            if (_b5V > 0) { _cumPv += ((_b5H + _b5L + _b5C) / 3.0) * _b5V; _cumVol += _b5V; }
            _sesVwap = _cumVol <= 0 ? _b5C : (_cumPv / _cumVol);
            _belowVwap = _b5C < _sesVwap ? _belowVwap + 1 : 0;

            int hhmmEt = curM1.CloseHhmmEt;
            if (sl.IsOpen)
            {
                if (hhmmEt >= 1550) { host.QueueMarketExit(sl, "V_X_TIME"); return; }
                if (_belowVwap >= 2) { host.QueueMarketExit(sl, "V_X_VWAP"); return; }
                return;
            }

            if (_dailyAtr <= 0 || _tradesToday >= 3) return;
            if (curM1.CloseCt.Hour == 9) return;
            if (hhmmEt < 945 || hhmmEt > 1500) return;
            if (_b5C <= _noiseUp || _b5C <= _sesVwap) return;
            if (double.IsNaN(atr20Session) || atr20Session <= 0) return;

            bool enteredV = _tpPts > 0.0
                ? host.QueueMarketEntry(sl, 1, _slAtrK * atr20Session, double.NaN, _tpPts)
                : host.QueueMarketEntry(sl, 1, _slAtrK * atr20Session);
            if (enteredV)
                _tradesToday++;
        }
    }

    // -------------------------------------------------------------------------
    // Module W: VwapCross (1m ETH, Long-only, exit_on_vwap_cross=false)
    // -------------------------------------------------------------------------
    internal sealed class VwapCrossEngine : ModuleEngineBase
    {
        private readonly double _slAtrK;
        private readonly bool _enableTrail;
        private readonly bool _useSlopeFilter;
        private readonly List<double> _vwapHist = new List<double>();
        private double _cumPv, _cumVol, _sesVwap;
        private int _sigSide;

        public VwapCrossEngine(double slAtrK = 0.25, bool enableTrail = false, bool useSlopeFilter = true) : base("W_slope_allowReFalse_ATR25")
        {
            _slAtrK = slAtrK;
            _enableTrail = enableTrail;
            _useSlopeFilter = useSlopeFilter;
        }

        public override void OnNewEthSession(int d0, double h, double l, double c, int d1) { }

        public override void UpdateM1OverlayProtectionsOnClose(VirtualSleeve sl, BarTimeContext bar)
        {
            if (_enableTrail && sl.IsOpen && sl.RiskPts > 0)
            {
                double[,] tiers = { { 1.5, 0.5 }, { 2.5, 1.5 } };
                for (int t = 0; t < 2; t++)
                {
                    if (sl.MaxFavPts >= tiers[t, 0] * sl.RiskPts)
                    {
                        double cand = sl.EntryPrice + tiers[t, 1] * sl.RiskPts;
                        if (cand > sl.StopPrice) sl.StopPrice = cand;
                    }
                }
            }
        }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            int t1 = bar.CloseHhmmssCt;
            int t2 = bar.NextMinHhmmssCt;
            bool inWin = t1 >= 83000 && t1 < 150000;
            if (inWin)
            {
                if (t1 == 83000) { _cumPv = 0; _cumVol = 0; }
                if (bar.Volume > 0)
                {
                    _cumPv += ((bar.High + bar.Low + bar.Close) / 3.0) * bar.Volume;
                    _cumVol += bar.Volume;
                }
                _sesVwap = _cumVol > 0 ? (_cumPv / _cumVol) : bar.Close;
            }
            _vwapHist.Add(_sesVwap);
            if (_vwapHist.Count > 260) _vwapHist.RemoveAt(0);

            if (t2 >= 150000)
            {
                if (sl.IsOpen) host.QueueMarketExit(sl, "EOD");
                _sigSide = 0;
                return;
            }
            if (!inWin || _cumVol <= 0) return;

            bool above = bar.Close > _sesVwap;
            bool below = bar.Close < _sesVwap;
            if (!sl.IsOpen && !sl.HasPendingEntry && t2 == 83100)
            {
                if (above)
                {
                    _sigSide = 1;
                    bool slopeOk = !_useSlopeFilter || (_vwapHist.Count > 20 && (_sesVwap - _vwapHist[_vwapHist.Count - 21]) >= 0.0);
                    if (slopeOk && !double.IsNaN(atr20Session) && atr20Session > 0)
                        host.QueueMarketEntry(sl, 1, _slAtrK * atr20Session);
                }
                else if (below) _sigSide = 2;
                return;
            }
            if (_sigSide == 1 && below) _sigSide = 2;
            else if (_sigSide == 2 && above) _sigSide = 1;
        }
    }

    // -------------------------------------------------------------------------
    // Module N: NDayLong (1m ETH + completed ETH daily highs/range)
    // -------------------------------------------------------------------------
    internal sealed class NDayLongEngine : ModuleEngineBase
    {
        private readonly int _numDays;
        private readonly double _slAtrK;
        private readonly double _acceptBufPts;
        private readonly Queue<double> _dHighs = new Queue<double>();
        private double _priorRange = double.NaN;
        private double _dayHi = double.NaN;
        private readonly List<double> _rthVwapHist = new List<double>();
        private double _cumPv, _cumVol;
        private int _acceptCloses, _closesBelowDayHi;
        private bool _wasLong;
        private double _lastBreakoutLvl;

        public NDayLongEngine(int numDays = 5, double slAtrK = 0.25, double acceptBufPts = 4.0) : base("N_d5_fbTrue_ATR25")
        {
            _numDays = numDays;
            _slAtrK = slAtrK;
            _acceptBufPts = acceptBufPts;
        }

        public override void OnNewEthSession(int d0, double h, double l, double c, int d1)
        {
            if (d0 > 0 && h > l)
            {
                _priorRange = h - l;
                _dHighs.Enqueue(h);
                if (_dHighs.Count > _numDays) _dHighs.Dequeue();
                if (_dHighs.Count == _numDays)
                {
                    double m = double.MinValue;
                    foreach (double v in _dHighs) if (v > m) m = v;
                    _dayHi = m;
                }
            }
        }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            int ct = bar.CloseHhmmssCt;
            int t2 = bar.NextMinHhmmssCt;
            if (ct == 83000) { _cumPv = 0; _cumVol = 0; }
            double vVal;
            if (ct >= 83000 && ct < 160000)
            {
                _cumPv += ((bar.High + bar.Low + bar.Close) / 3.0) * bar.Volume;
                _cumVol += bar.Volume;
                vVal = _cumVol > 0 ? (_cumPv / _cumVol) : bar.Close;
            }
            else vVal = _rthVwapHist.Count == 0 ? bar.Close : _rthVwapHist[_rthVwapHist.Count - 1];
            _rthVwapHist.Add(vVal);
            if (_rthVwapHist.Count > 60) _rthVwapHist.RemoveAt(0);

            bool maintBlocked = bar.DowCtMon0 == 5 || (bar.DowCtMon0 == 4 && ct >= 154400)
                || (bar.DowCtMon0 == 6 && ct < 170100) || (ct >= 154400 && ct < 170100);
            if (maintBlocked)
            {
                sl.HasPendingEntry = false;
                sl.PendingEntryIsStopOrder = false;
                if (sl.IsOpen) { host.QueueMarketExit(sl, "DAILY_FUTURES_CLOSE"); return; }
            }

            if (t2 >= 160000)
            {
                sl.HasPendingEntry = false;
                sl.PendingEntryIsStopOrder = false;
                if (sl.IsOpen) host.QueueMarketExit(sl, "EOD");
                return;
            }

            if (double.IsNaN(_dayHi) || double.IsNaN(_priorRange) || _priorRange <= 0) return;

            if (sl.IsOpen)
            {
                if (bar.Close <= sl.EntryPrice - _priorRange) { host.QueueMarketExit(sl, "VOLLOSS"); return; }
                if (!_wasLong) { _wasLong = true; _closesBelowDayHi = 0; }
                if (bar.Close < _lastBreakoutLvl) _closesBelowDayHi++; else _closesBelowDayHi = 0;
                if (_closesBelowDayHi >= 6) { host.QueueMarketExit(sl, "FAILED"); return; }
                return;
            }

            _wasLong = false; _closesBelowDayHi = 0;
            if (sl.PendingEntryIsStopOrder)
            {
                if (ct >= 154500) sl.PendingEntryIsStopOrder = false;
                return;
            }
            if (maintBlocked || sl.HasPendingEntry || ct >= 154500) return;

            if (ct < 83000 || ct >= 160000 || _rthVwapHist.Count < 16) return;
            double vPrev = _rthVwapHist[_rthVwapHist.Count - 16];
            if (!(bar.Close > vVal && vVal > vPrev)) return;

            if (bar.Close > _dayHi + _acceptBufPts) _acceptCloses++; else _acceptCloses = 0;
            if (_acceptCloses < 2) return;

            if (double.IsNaN(atr20Session) || atr20Session <= 0) return;
            _lastBreakoutLvl = _dayHi;
            if (_dayHi <= bar.Close)
            {
                host.QueueMarketEntry(sl, 1, _slAtrK * atr20Session);
            }
            else
            {
                host.QueueStopEntry(sl, 1, FundedSyncMath.RoundTick(_dayHi, TickSize), _slAtrK * atr20Session);
            }
        }
    }

    // -------------------------------------------------------------------------
    // Module SOMEOD: SessionOpenMomentum EOD (M5 NY+7h clock, MQL5 SMA ATR14)
    // -------------------------------------------------------------------------
    internal sealed class SessionOpenMomentumEngine : ModuleEngineBase
    {
        private bool _hasB5;
        private long _curBucketId = -1;
        private DateTime _b5OpenNy;
        private double _b5O, _b5H, _b5L, _b5C;
        private int _barsM5Count;
        private double _ema12 = double.NaN, _ema120 = double.NaN, _prevClose = double.NaN, _atr14 = double.NaN;
        private readonly Queue<double> _trWin = new Queue<double>();
        private int _blockedDay = -1;

        public SessionOpenMomentumEngine() : base("SOMEOD_ext_NQ") { }

        public override void OnNewEthSession(int d0, double h, double l, double c, int d1) { }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            DateTime srvOpenNy = bar.OpenNy.AddHours(7);
            long bId = srvOpenNy.Ticks / (TimeSpan.TicksPerMinute * 5L);
            if (_hasB5 && _curBucketId != bId)
                FlushM5Bar(sl, host);

            if (!_hasB5)
            {
                _hasB5 = true; _curBucketId = bId; _b5OpenNy = bar.OpenNy;
                _b5O = bar.Open; _b5H = bar.High; _b5L = bar.Low; _b5C = bar.Close;
            }
            else
            {
                _b5H = Math.Max(_b5H, bar.High); _b5L = Math.Min(_b5L, bar.Low); _b5C = bar.Close;
            }

            if ((bar.CloseNy.Ticks % (TimeSpan.TicksPerMinute * 5L)) == 0)
                FlushM5Bar(sl, host);
        }

        private void FlushM5Bar(VirtualSleeve sl, PortfolioCoordinator host)
        {
            _hasB5 = false;
            double cl = _b5C;
            double tr = double.IsNaN(_prevClose) ? (_b5H - _b5L)
                : Math.Max(_b5H - _b5L, Math.Max(Math.Abs(_b5H - _prevClose), Math.Abs(_b5L - _prevClose)));
            _prevClose = cl;
            _barsM5Count++;

            _ema12 = double.IsNaN(_ema12) ? cl : (2.0 / 13.0) * cl + (1.0 - 2.0 / 13.0) * _ema12;
            _ema120 = double.IsNaN(_ema120) ? cl : (2.0 / 121.0) * cl + (1.0 - 2.0 / 121.0) * _ema120;

            // Exact MQL5 iATR parity: SMA of True Range over 14 M5 bars
            _trWin.Enqueue(tr);
            if (_trWin.Count > 14) _trWin.Dequeue();
            if (_trWin.Count == 14)
            {
                double s = 0; foreach (double x in _trWin) s += x;
                _atr14 = s / 14.0;
            }

            DateTime closedOpenNy = _b5OpenNy;
            DateTime closedCloseNy = closedOpenNy.AddMinutes(5);
            DateTime srvClose = closedCloseNy.AddHours(7);
            int curSrvDay = srvClose.Year * 1000 + srvClose.DayOfYear;
            int closeMinNy = closedCloseNy.Hour * 60 + closedCloseNy.Minute;

            if (sl.IsOpen)
            {
                if (closeMinNy >= 955) // 15:55 NY EOD close
                {
                    host.QueueMarketExit(sl, "EOD_CLOSE");
                    return;
                }
                if (!double.IsNaN(_ema120) && sl.MaxFavPts >= 0.5 * sl.RiskPts)
                {
                    double cand = FundedSyncMath.RoundTick(_ema120, TickSize);
                    if (sl.Side > 0 && cand > sl.StopPrice + 0.01 && cand < cl)
                        sl.StopPrice = cand;
                    else if (sl.Side < 0 && cand < sl.StopPrice - 0.01 && cand > cl)
                        sl.StopPrice = cand;
                }
                return;
            }

            if (_barsM5Count < 122 || double.IsNaN(_atr14) || _atr14 <= 0 || double.IsNaN(_ema12)) return;
            // Closed 09:30-09:35 NY bar -> entry fills on next open at 09:35 NY
            if (closedOpenNy.Hour == 9 && closedOpenNy.Minute == 30 && _blockedDay != curSrvDay)
            {
                int side = cl > _ema12 ? 1 : (cl < _ema12 ? -1 : 0);
                if (side != 0)
                {
                    _blockedDay = curSrvDay;
                    host.QueueMarketEntry(sl, side, FundedSyncMath.RoundTick(8.0 * _atr14, TickSize));
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Coordinator: Virtual Sleeves, MaxOpenR, CollisionPolicy, Compliance, CSV
    // -------------------------------------------------------------------------
    // News veto (EdgeLab, 2026-11-25). Same rule as edgelab/veto_noticias.py: window [event - before, event + after]
    // (closed) for every tier1 event of config/noticias/calendario_usd_tier1.csv; FOMC_* events use the FOMC window.
    // Inside a window: no new entries and every open position is closed. Fail-closed: if the file is missing or the
    // calendar does not cover the bar date, BlocksAt returns true (no trading) and Status says why.
    public sealed class NewsVetoCalendar
    {
        private readonly List<long> _ini = new List<long>();
        private readonly List<long> _fin = new List<long>();
        private DateTime _lastEventUtc = DateTime.MinValue;
        private DateTime _firstEventUtc = DateTime.MaxValue;
        public string Status { get; private set; }
        public int EventCount { get; private set; }

        public NewsVetoCalendar(string csvPath, double beforeMin, double afterMin, double fomcBeforeMin, double fomcAfterMin)
        {
            var raw = new List<KeyValuePair<long, long>>();
            if (string.IsNullOrEmpty(csvPath) || !File.Exists(csvPath))
            {
                Status = "NEWS_CALENDAR_MISSING " + csvPath;
                return;
            }
            string[] lines = File.ReadAllLines(csvPath);
            for (int i = 1; i < lines.Length; i++)
            {
                string[] c = lines[i].Split(',');
                if (c.Length < 4 || c[3].Trim() != "tier1") continue;
                DateTime t;
                if (!DateTime.TryParseExact(c[0].Trim(), "yyyy-MM-ddTHH:mmZ", CultureInfo.InvariantCulture,
                        DateTimeStyles.AdjustToUniversal | DateTimeStyles.AssumeUniversal, out t)) continue;
                bool fomc = c[1].StartsWith("FOMC_");
                double b = fomc ? fomcBeforeMin : beforeMin, a = fomc ? fomcAfterMin : afterMin;
                raw.Add(new KeyValuePair<long, long>(t.AddMinutes(-b).Ticks, t.AddMinutes(a).Ticks));
                if (t > _lastEventUtc) _lastEventUtc = t;
                if (t < _firstEventUtc) _firstEventUtc = t;
            }
            raw.Sort((x, y) => x.Key.CompareTo(y.Key));
            foreach (var kv in raw)
            {
                int n = _ini.Count;
                if (n > 0 && kv.Key <= _fin[n - 1]) { if (kv.Value > _fin[n - 1]) _fin[n - 1] = kv.Value; }
                else { _ini.Add(kv.Key); _fin.Add(kv.Value); }
            }
            EventCount = raw.Count;
            Status = raw.Count > 0 ? "OK " + raw.Count + " events " + _firstEventUtc.ToString("yyyy-MM-dd") + ".." + _lastEventUtc.ToString("yyyy-MM-dd")
                                   : "NEWS_CALENDAR_EMPTY " + csvPath;
        }

        public bool Covers(DateTime utc) { return EventCount > 0 && utc >= _firstEventUtc.Date && utc <= _lastEventUtc.Date.AddDays(1); }

        public bool InWindow(DateTime utc)
        {
            long t = utc.Ticks;
            int lo = 0, hi = _ini.Count - 1, k = -1;
            while (lo <= hi) { int m = (lo + hi) / 2; if (_ini[m] <= t) { k = m; lo = m + 1; } else hi = m - 1; }
            return k >= 0 && t <= _fin[k];
        }

        public bool BlocksAt(DateTime utc) { return !Covers(utc) || InWindow(utc); }
    }

    public sealed class PortfolioCoordinator
    {
        public readonly Dictionary<string, VirtualSleeve> Sleeves = new Dictionary<string, VirtualSleeve>();
        private readonly List<ModuleEngineBase> _engines = new List<ModuleEngineBase>();
        private readonly Queue<double> _sesAtrQueue = new Queue<double>();
        public readonly List<CompletedTradeRecord> CompletedTrades = new List<CompletedTradeRecord>();

        public double TickSize = 0.25;
        public double MicroPointValue = 2.0;
        public double FrictionMiniPts = 1.545;
        public FundedSyncAccountMode AccountMode = FundedSyncAccountMode.Evaluation;
        public double EvalRisk1R_USD = 450.0;
        public double FundedRisk1R_USD = 450.0;
        public double MaxOpenR = 3.0;
        public int MaxMicroContracts = 100;
        public FundedSyncCollisionPolicy CollisionPolicy = FundedSyncCollisionPolicy.Netting;
        public int HardFlattenHHMM_ET = 1640;
        public bool EnforceEvalDailyCap = true;
        public double EvalDailyCapUSD = 3420.0;
        public double DailyLossLimitUSD = 2700.0;
        public bool EntriesAllowedNow { get; private set; }
        public double RealizedSessionUsd { get; private set; }
        public double OpenPnlUsd { get; private set; }
        public double Atr20Session { get; private set; }
        public bool HardFlattenedToday { get; private set; }
        public bool DailyCapTriggeredToday { get; private set; }
        public bool DailyLossTriggeredToday { get; private set; }
        public NewsVetoCalendar NewsVeto;              // null = veto off
        public bool NewsVetoActiveNow { get; private set; }

        public string CsvLogPath;
        public bool EnableCsvLog;
        private bool _csvHeaderWritten;

        private int _curEthDate = -1;
        private double _curSesHi = double.MinValue, _curSesLo = double.MaxValue, _curSesClose = double.NaN;

        public PortfolioCoordinator(
            Dictionary<string, double> weights,
            bool[] enabledFlags,
            bool enableWTrail = false,
            double rOscMult = 3.0, int rEndEt = 660, double rSlAtr = 0.50,
            int zBucketMin = 15, int zEmaPeriod = 20, double zMinEffPct = 40.0, double zSlAtr = 0.50,
            double tStopOrbMult = 1.0, double tBeTrigR = 1.5,
            double vNoiseMult = 0.25, double vSlAtr = 0.30,
            double wSlAtr = 0.25, int nDays = 5, double nSlAtr = 0.25,
            double tStopMinPts = 2.0, double tStopMaxPts = 100.0,
            double vTpPts = 0.0, bool wUseSlopeFilter = true, double nAcceptBufPts = 4.0)
        {
            Atr20Session = double.NaN;
            _engines.Add(new AtrPhaseEngine(rOscMult, rEndEt, rSlAtr));
            _engines.Add(new ZetaEngine(zBucketMin, zEmaPeriod, zMinEffPct, zSlAtr));
            _engines.Add(new FtmOrbEngine(tStopOrbMult, tBeTrigR, tStopMinPts, tStopMaxPts));
            _engines.Add(new VaultBreakEngine(vNoiseMult, vSlAtr, vTpPts));
            _engines.Add(new VwapCrossEngine(wSlAtr, enableWTrail, wUseSlopeFilter));
            _engines.Add(new NDayLongEngine(nDays, nSlAtr, nAcceptBufPts));
            _engines.Add(new SessionOpenMomentumEngine());

            for (int i = 0; i < FundedSyncMath.ModuleOrder.Length; i++)
            {
                string id = FundedSyncMath.ModuleOrder[i];
                double w = weights != null && weights.ContainsKey(id) ? weights[id] : 0.0;
                bool en = (enabledFlags == null || i >= enabledFlags.Length || enabledFlags[i]) && w > 1e-6;
                Sleeves[id] = new VirtualSleeve { ModuleId = id, WeightW5 = w, Enabled = en };
            }
        }

        public double CurrentRisk1RUsd { get { return AccountMode == FundedSyncAccountMode.Evaluation ? EvalRisk1R_USD : FundedRisk1R_USD; } }

        public int TargetNetMicros
        {
            get
            {
                if (HardFlattenedToday || DailyCapTriggeredToday || DailyLossTriggeredToday) return 0;
                int net = 0;
                foreach (string id in FundedSyncMath.ModuleOrder)
                {
                    var sl = Sleeves[id];
                    if (sl.IsOpen) net += sl.Side * sl.Contracts;
                }
                return net;
            }
        }

        public double CurrentOpenRUsed
        {
            get
            {
                double u = 0;
                foreach (string id in FundedSyncMath.ModuleOrder)
                {
                    var sl = Sleeves[id];
                    if (sl.IsOpen) u += sl.AppliedW;
                }
                return u;
            }
        }

        public void FeedBar(BarTimeContext bar)
        {
            foreach (var eng in _engines) eng.TickSize = TickSize;

            if (bar.EthTradeDate != _curEthDate)
            {
                int prevD = _curEthDate;
                double prevH = _curSesHi, prevL = _curSesLo, prevC = _curSesClose;
                if (prevD > 0 && prevH >= prevL)
                {
                    _sesAtrQueue.Enqueue(prevH - prevL);
                    if (_sesAtrQueue.Count > 20) _sesAtrQueue.Dequeue();
                    double s = 0; foreach (double x in _sesAtrQueue) s += x;
                    Atr20Session = _sesAtrQueue.Count >= 20 ? (s / 20.0) : double.NaN;
                }
                foreach (var eng in _engines) eng.OnNewEthSession(prevD, prevH, prevL, prevC, bar.EthTradeDate);
                _curEthDate = bar.EthTradeDate;
                _curSesHi = double.MinValue; _curSesLo = double.MaxValue; _curSesClose = double.NaN;
                HardFlattenedToday = false; DailyCapTriggeredToday = false; DailyLossTriggeredToday = false;
                RealizedSessionUsd = 0.0;
            }

            if (bar.High > _curSesHi) _curSesHi = bar.High;
            if (bar.Low < _curSesLo) _curSesLo = bar.Low;
            _curSesClose = bar.Close;

            // 1. Fill pending Market/Stop entries and Market exits at Open[i]
            ProcessPendingFillsAtBarOpen(bar);

            // 2. Evaluate intrabar STOP (prioritized) & TARGET on [Low[i], High[i]]
            ProcessIntrabarStopsAndTargets(bar);

            // 3. Causal M1-close protection promotion for NEXT bar i+1
            for (int i = 0; i < _engines.Count; i++)
            {
                var sl = Sleeves[_engines[i].ModuleId];
                if (sl.IsOpen) _engines[i].UpdateM1OverlayProtectionsOnClose(sl, bar);
            }

            // 4. Compliance checks before new bar-close signals
            OpenPnlUsd = ComputeOpenPnlUsd(bar.Close);
            bool inPreBreakFlattenWindow = HardFlattenHHMM_ET > 0 && HardFlattenHHMM_ET < 1730
                && bar.CloseHhmmEt >= HardFlattenHHMM_ET && bar.CloseHhmmEt < 1730;
            if (inPreBreakFlattenWindow && !HardFlattenedToday)
            {
                HardFlattenedToday = true;
                FlattenAllImmediate(bar.Close, bar.CloseNy, "HARD_FLATTEN_1640ET");
            }
            double netDay = RealizedSessionUsd + ComputeOpenPnlUsd(bar.Close);
            if (AccountMode == FundedSyncAccountMode.Evaluation && EnforceEvalDailyCap && EvalDailyCapUSD > 0 && netDay >= EvalDailyCapUSD && !DailyCapTriggeredToday)
            {
                DailyCapTriggeredToday = true;
                FlattenAllImmediate(bar.Close, bar.CloseNy, "EVAL_DAILY_CAP");
            }
            if (DailyLossLimitUSD > 0 && netDay <= -DailyLossLimitUSD && !DailyLossTriggeredToday)
            {
                DailyLossTriggeredToday = true;
                FlattenAllImmediate(bar.Close, bar.CloseNy, "DAILY_LOSS_LIMIT");
            }

            bool newsVeto = NewsVeto != null && NewsVeto.BlocksAt(bar.CloseUtc);
            if (newsVeto) FlattenAllImmediate(bar.Close, bar.CloseNy, "NEWS_VETO");
            NewsVetoActiveNow = newsVeto;

            EntriesAllowedNow = !HardFlattenedToday && !DailyCapTriggeredToday && !DailyLossTriggeredToday && !inPreBreakFlattenWindow && !newsVeto;

            // 5. Run all 7 module signal engines on bar close
            for (int i = 0; i < _engines.Count; i++)
            {
                var sl = Sleeves[_engines[i].ModuleId];
                if (sl.Enabled) _engines[i].ProcessBar(bar, Atr20Session, sl, this);
            }
        }

        private void ProcessPendingFillsAtBarOpen(BarTimeContext bar)
        {
            foreach (string id in FundedSyncMath.ModuleOrder)
            {
                var sl = Sleeves[id];
                if (sl.PendingExitReason != null && sl.IsOpen)
                {
                    string rsn = sl.PendingExitReason; sl.PendingExitReason = null;
                    CloseSleeve(sl, bar.Open, bar.CloseNy, rsn);
                }
                else if (sl.HasPendingEntry && !sl.IsOpen)
                {
                    bool trigger = true;
                    double fillPx = bar.Open;
                    if (sl.PendingEntryIsStopOrder)
                    {
                        if (sl.PendingEntrySide > 0)
                        {
                            if (bar.High >= sl.PendingEntryStopPrice)
                                fillPx = Math.Max(bar.Open, sl.PendingEntryStopPrice);
                            else
                                trigger = false;
                        }
                        else
                        {
                            if (bar.Low <= sl.PendingEntryStopPrice)
                                fillPx = Math.Min(bar.Open, sl.PendingEntryStopPrice);
                            else
                                trigger = false;
                        }
                    }
                    if (trigger)
                    {
                        int side = sl.PendingEntrySide;
                        double riskPts = sl.PendingStopPts;
                        double fixStop = sl.PendingFixedStopPrice;
                        double tgtPx = sl.PendingTargetPrice;
                        sl.HasPendingEntry = false;
                        sl.PendingEntryIsStopOrder = false;
                        OpenSleeveNow(sl, side, fillPx, riskPts, fixStop, tgtPx, bar.CloseNy);
                    }
                }
            }
        }

        private void ProcessIntrabarStopsAndTargets(BarTimeContext bar)
        {
            foreach (string id in FundedSyncMath.ModuleOrder)
            {
                var sl = Sleeves[id];
                if (!sl.IsOpen) continue;

                double op = bar.Open, hi = bar.High, lo = bar.Low;
                bool hasStop = !double.IsNaN(sl.StopPrice);
                bool hasTgt = !double.IsNaN(sl.TargetPrice);

                if (sl.Side > 0)
                {
                    if (hasStop && lo <= sl.StopPrice)
                    {
                        CloseSleeve(sl, Math.Min(op, sl.StopPrice), bar.CloseNy, sl.OverlayBeActivated ? "BE_STOP" : "STOP");
                        continue;
                    }
                    if (hasTgt && hi >= sl.TargetPrice)
                    {
                        CloseSleeve(sl, Math.Max(op, sl.TargetPrice), bar.CloseNy, "TARGET");
                        continue;
                    }
                    double fav = hi - sl.EntryPrice;
                    if (fav > sl.MaxFavPts) sl.MaxFavPts = fav;
                }
                else
                {
                    if (hasStop && hi >= sl.StopPrice)
                    {
                        CloseSleeve(sl, Math.Max(op, sl.StopPrice), bar.CloseNy, sl.OverlayBeActivated ? "BE_STOP" : "STOP");
                        continue;
                    }
                    if (hasTgt && lo <= sl.TargetPrice)
                    {
                        CloseSleeve(sl, Math.Min(op, sl.TargetPrice), bar.CloseNy, "TARGET");
                        continue;
                    }
                    double fav = sl.EntryPrice - lo;
                    if (fav > sl.MaxFavPts) sl.MaxFavPts = fav;
                }
            }
        }

        internal bool QueueMarketEntry(VirtualSleeve sl, int side, double riskPts, double fixedTargetPx = double.NaN, double targetDistPts = double.NaN)
        {
            if (!sl.Enabled || !EntriesAllowedNow || sl.IsOpen || sl.HasPendingEntry || !(riskPts > 0)) return false;
            sl.HasPendingEntry = true;
            sl.PendingEntryIsStopOrder = false;
            sl.PendingEntrySide = side;
            sl.PendingStopPts = riskPts;
            sl.PendingFixedStopPrice = double.NaN;
            sl.PendingTargetPrice = !double.IsNaN(targetDistPts) ? (side * targetDistPts) : fixedTargetPx;
            if (!double.IsNaN(targetDistPts)) sl.PendingFixedStopPrice = targetDistPts; // mark relative distance
            return true;
        }

        internal bool QueueStopEntry(VirtualSleeve sl, int side, double triggerStopPx, double riskPts)
        {
            if (!sl.Enabled || !EntriesAllowedNow || sl.IsOpen || sl.HasPendingEntry || !(riskPts > 0)) return false;
            sl.HasPendingEntry = true;
            sl.PendingEntryIsStopOrder = true;
            sl.PendingEntryStopPrice = triggerStopPx;
            sl.PendingEntrySide = side;
            sl.PendingStopPts = riskPts;
            sl.PendingFixedStopPrice = double.NaN;
            sl.PendingTargetPrice = double.NaN;
            return true;
        }

        internal void QueueMarketExit(VirtualSleeve sl, string reason)
        {
            if (sl.IsOpen && sl.PendingExitReason == null) sl.PendingExitReason = reason;
        }

        private void OpenSleeveNow(VirtualSleeve sl, int side, double fillPx, double riskPts, double relTgtMarker, double tgtPx, DateTime barNy)
        {
            if (!EntriesAllowedNow || sl.IsOpen) return;
            if (CollisionPolicy == FundedSyncCollisionPolicy.VetoOpposite)
            {
                int curNet = TargetNetMicros;
                if (curNet * side < 0) return;
            }
            double remR = Math.Max(0.0, MaxOpenR - CurrentOpenRUsed);
            double wEff = Math.Min(sl.WeightW5, remR);
            if (wEff <= 1e-6) return;

            double tgtUsd = CurrentRisk1RUsd * wEff;
            double r1Mic = Math.Max(riskPts * MicroPointValue, 1e-6);
            int qty = (int)Math.Min(MaxMicroContracts, Math.Max(0, Math.Round(tgtUsd / r1Mic)));
            if (qty == 0 && tgtUsd >= 0.55 * r1Mic) qty = 1;
            if (qty <= 0) return;

            sl.IsOpen = true;
            sl.Side = side;
            sl.Contracts = qty;
            sl.AppliedW = wEff;
            sl.EntryPrice = fillPx;
            sl.RiskPts = riskPts;
            sl.InitialStopPrice = fillPx - side * riskPts;
            sl.StopPrice = sl.InitialStopPrice;
            sl.TargetPrice = !double.IsNaN(relTgtMarker) ? (fillPx + side * relTgtMarker) : tgtPx;
            sl.MaxFavPts = 0;
            sl.OverlayBeActivated = false;
            sl.EntryNy = barNy;
            sl.EntrySessionDate = _curEthDate;
        }

        private void CloseSleeve(VirtualSleeve sl, double exitPx, DateTime barNy, string reason)
        {
            if (!sl.IsOpen) return;
            double pnlPts = sl.Side * (exitPx - sl.EntryPrice);
            double rBruto = pnlPts / Math.Max(sl.RiskPts, 1e-6);
            double rNetMini = (pnlPts - FrictionMiniPts) / Math.Max(sl.RiskPts, 1e-6);
            RealizedSessionUsd += (pnlPts - 0.90) * sl.Contracts * MicroPointValue;

            var rec = new CompletedTradeRecord
            {
                SessionDate = sl.EntrySessionDate,
                ModuleId = sl.ModuleId,
                WeightW5 = sl.WeightW5,
                Side = sl.Side,
                Contracts = sl.Contracts,
                EntryNy = sl.EntryNy,
                ExitNy = barNy,
                EntryPrice = sl.EntryPrice,
                InitialStopPrice = sl.InitialStopPrice,
                ExitPrice = exitPx,
                RiskPts = sl.RiskPts,
                PnlPts = pnlPts,
                RBruto = rBruto,
                RNetoMini = rNetMini,
                ExitName = reason
            };
            CompletedTrades.Add(rec);
            if (EnableCsvLog && !string.IsNullOrEmpty(CsvLogPath)) WriteCsvRow(rec);

            sl.IsOpen = false;
            sl.Contracts = 0;
            sl.AppliedW = 0;
            sl.TargetPrice = double.NaN;
            sl.StopPrice = double.NaN;
        }

        private void FlattenAllImmediate(double price, DateTime barNy, string reason)
        {
            foreach (string id in FundedSyncMath.ModuleOrder)
            {
                var sl = Sleeves[id];
                sl.HasPendingEntry = false;
                sl.PendingEntryIsStopOrder = false;
                if (sl.IsOpen) CloseSleeve(sl, price, barNy, reason);
            }
        }

        private double ComputeOpenPnlUsd(double px)
        {
            double tot = 0;
            foreach (string id in FundedSyncMath.ModuleOrder)
            {
                var sl = Sleeves[id];
                if (sl.IsOpen) tot += sl.Side * (px - sl.EntryPrice) * sl.Contracts * MicroPointValue;
            }
            return tot;
        }

        private void WriteCsvRow(CompletedTradeRecord r)
        {
            try
            {
                if (!_csvHeaderWritten)
                {
                    if (!File.Exists(CsvLogPath) || new FileInfo(CsvLogPath).Length == 0)
                        File.WriteAllText(CsvLogPath, "fecha_int,a5,modulo,w_w5,side,en_ny,ex_ny,entry_price,stop_price,exit_price,riesgo_pts,pnl_pts,R_bruto,R_neto_mini,exit_name" + Environment.NewLine, Encoding.UTF8);
                    _csvHeaderWritten = true;
                }
                string line = string.Format(CultureInfo.InvariantCulture,
                    "{0},LIVE,{1},{2:F6},{3},{4},{5},{6:F2},{7:F4},{8:F4},{9:F4},{10:F2},{11:F6},{12:F6},{13}",
                    r.SessionDate, r.ModuleId, r.WeightW5, r.Side,
                    r.EntryNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    r.ExitNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    r.EntryPrice, r.InitialStopPrice, r.ExitPrice, r.RiskPts, r.PnlPts, r.RBruto, r.RNetoMini, r.ExitName);
                File.AppendAllText(CsvLogPath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }

        public string BuildHudText(string stratLabel)
        {
            int net = TargetNetMicros;
            return string.Format(CultureInfo.InvariantCulture,
                "{0} | {1} 1R=${2:F0} | Net={3} MNQ | OpenR={4:F2}/{5:F1} | DayUSD=${6:+0;-0;0} | ATR20={7:F1}",
                stratLabel, AccountMode, CurrentRisk1RUsd, net, CurrentOpenRUsed, MaxOpenR,
                RealizedSessionUsd + OpenPnlUsd, double.IsNaN(Atr20Session) ? 0.0 : Atr20Session);
        }
    }
}
