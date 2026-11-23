#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Core;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    using EdgeLabFundedSync;

    /// <summary>
    /// Shared NinjaTrader 8 runtime adapter using pure composition so every FUNDEDSYNC portfolio
    /// variant and single-module auditor delegates bar mapping, net position synchronization,
    /// hybrid NQ/MNQ contract splitting, and chart HUD rendering through one code path.
    /// </summary>
    internal sealed class FundedSyncNt8Adapter
    {
        private readonly Strategy _strat;
        private readonly PortfolioCoordinator _coord;
        private readonly string _label;
        private readonly bool _hasSecondaryMnq;
        private TimeZoneInfo _chartTz;
        private TimeZoneInfo _nyTz;
        private TimeZoneInfo _ctTz;

        public FundedSyncNt8Adapter(
            Strategy strat,
            PortfolioCoordinator coord,
            string label,
            bool hasSecondaryMnq,
            bool enableCsvLog,
            string csvFileName)
        {
            _strat = strat;
            _coord = coord;
            _label = label;
            _hasSecondaryMnq = hasSecondaryMnq;

            _nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time");
            _ctTz = FundedSyncMath.ResolveTz("Central Standard Time");
            _chartTz = (strat.Bars != null && strat.Bars.TradingHours != null && strat.Bars.TradingHours.TimeZoneInfo != null)
                ? strat.Bars.TradingHours.TimeZoneInfo
                : (Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local);

            double tick = (strat.Instrument != null && strat.Instrument.MasterInstrument != null && strat.Instrument.MasterInstrument.TickSize > 0)
                ? strat.Instrument.MasterInstrument.TickSize
                : 0.25;
            _coord.TickSize = tick;
            _coord.EnableCsvLog = enableCsvLog;
            string fname = string.IsNullOrWhiteSpace(csvFileName) ? "EdgeLab_FundedSync_ParityTrades.csv" : csvFileName.Trim();
            _coord.CsvLogPath = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, fname);
        }

        public static FundedSyncNt8Adapter CreateFromPreset(
            Strategy strat,
            string label,
            FundedSyncPortfolioPreset preset,
            FundedSyncPropProfile propProfile,
            FundedSyncAccountMode mode,
            double evalRisk1R,
            double fundedRisk1R,
            double maxOpenR,
            int maxMicros,
            FundedSyncCollisionPolicy collisionPolicy,
            int hardFlattenHhmmEt,
            bool enforceEvalCap,
            double evalCapUsd,
            double dailyLossUsd,
            bool enableWTrail,
            string secondaryMnqSymbol,
            bool enableCsvLog,
            string csvFileName,
            bool[] enableOverrides,
            double[] weightOverrides)
        {
            Dictionary<string, double> weights;
            bool[] flags = new bool[7];
            if (preset == FundedSyncPortfolioPreset.CustomWeights)
            {
                weights = new Dictionary<string, double>();
                for (int i = 0; i < FundedSyncMath.ModuleOrder.Length; i++)
                {
                    string modId = FundedSyncMath.ModuleOrder[i];
                    double w = (weightOverrides != null && i < weightOverrides.Length) ? weightOverrides[i] : 0.0;
                    bool en = enableOverrides == null || i >= enableOverrides.Length || enableOverrides[i];
                    weights[modId] = w;
                    flags[i] = en && w > 1e-6;
                }
            }
            else
            {
                weights = FundedSyncMath.GetPresetWeights(preset);
                for (int i = 0; i < FundedSyncMath.ModuleOrder.Length; i++)
                {
                    string modId = FundedSyncMath.ModuleOrder[i];
                    bool userEn = enableOverrides == null || i >= enableOverrides.Length || enableOverrides[i];
                    flags[i] = userEn && weights.ContainsKey(modId) && weights[modId] > 1e-6;
                }
            }

            PropProfileDefaults prof = PropProfileDefaults.For(propProfile);
            bool useProfile = propProfile != FundedSyncPropProfile.Personal_Custom;

            var coord = new PortfolioCoordinator(weights, flags, enableWTrail: enableWTrail)
            {
                MicroPointValue = 2.0,
                FrictionMiniPts = 1.545,
                AccountMode = mode,
                EvalRisk1R_USD = useProfile ? prof.EvalRisk1R : evalRisk1R,
                FundedRisk1R_USD = useProfile ? prof.FundedRisk1R : fundedRisk1R,
                MaxOpenR = maxOpenR,
                MaxMicroContracts = useProfile ? prof.MaxMicros : maxMicros,
                CollisionPolicy = useProfile ? prof.CollisionPolicy : collisionPolicy,
                HardFlattenHHMM_ET = useProfile ? prof.HardFlattenHHMM_ET : hardFlattenHhmmEt,
                EnforceEvalDailyCap = useProfile ? prof.EnforceEvalDailyCap : enforceEvalCap,
                EvalDailyCapUSD = useProfile ? prof.EvalDailyCapUsd : evalCapUsd,
                DailyLossLimitUSD = useProfile ? prof.DailyLossLimitUsd : dailyLossUsd
            };

            bool hasSec = !string.IsNullOrWhiteSpace(secondaryMnqSymbol);
            return new FundedSyncNt8Adapter(strat, coord, label, hasSec, enableCsvLog, csvFileName);
        }

        public void OnBarUpdate()
        {
            if (_strat.BarsInProgress != 0 || _strat.CurrentBar < 1)
                return;

            DateTime chartLocal = DateTime.SpecifyKind(_strat.Time[0], DateTimeKind.Unspecified);
            DateTime closeUtc = _chartTz.Id == TimeZoneInfo.Utc.Id
                ? DateTime.SpecifyKind(chartLocal, DateTimeKind.Utc)
                : TimeZoneInfo.ConvertTimeToUtc(chartLocal, _chartTz);

            BarTimeContext ctx = FundedSyncMath.BuildBarTimeContext(
                closeUtc,
                _strat.Open[0],
                _strat.High[0],
                _strat.Low[0],
                _strat.Close[0],
                _strat.Volume[0],
                _nyTz,
                _ctTz);

            _coord.FeedBar(ctx);
            SynchronizeNetPosition();
            RenderHud();
        }

        private void SynchronizeNetPosition()
        {
            int targetMicros = (_coord.HardFlattenedToday || _coord.DailyCapTriggeredToday || _coord.DailyLossTriggeredToday)
                ? 0
                : _coord.TargetNetMicros;

            double pvPrimary = (_strat.Instrument != null && _strat.Instrument.MasterInstrument != null)
                ? _strat.Instrument.MasterInstrument.PointValue
                : 2.0;

            if (_hasSecondaryMnq && pvPrimary >= 15.0)
            {
                int sgn = Math.Sign(targetMicros);
                int absM = Math.Abs(targetMicros);
                int tgtNq = sgn * (absM / 10);
                int tgtMnq = sgn * (absM % 10);
                ReconcileBipPosition(0, tgtNq, "FS_NQ");
                ReconcileBipPosition(1, tgtMnq, "FS_MNQ");
            }
            else if (pvPrimary >= 15.0)
            {
                int tgtMini = (int)Math.Round(targetMicros / 10.0, MidpointRounding.AwayFromZero);
                ReconcileBipPosition(0, tgtMini, "FS_NQ");
            }
            else
            {
                ReconcileBipPosition(0, targetMicros, "FS_MNQ");
            }
        }

        private void ReconcileBipPosition(int bip, int targetSignedQty, string tagPrefix)
        {
            if (_strat.Positions == null || bip >= _strat.Positions.Length)
                return;

            Position pos = _strat.Positions[bip];
            int curQty = pos.MarketPosition == MarketPosition.Long ? pos.Quantity
                : (pos.MarketPosition == MarketPosition.Short ? -pos.Quantity : 0);

            if (curQty == targetSignedQty)
                return;

            int delta = targetSignedQty - curQty;
            if (curQty > 0 && targetSignedQty <= 0)
            {
                _strat.ExitLong(bip, curQty, tagPrefix + "_FL", tagPrefix + "_L");
                if (targetSignedQty < 0)
                    _strat.EnterShort(bip, Math.Abs(targetSignedQty), tagPrefix + "_S");
            }
            else if (curQty < 0 && targetSignedQty >= 0)
            {
                _strat.ExitShort(bip, Math.Abs(curQty), tagPrefix + "_FL", tagPrefix + "_S");
                if (targetSignedQty > 0)
                    _strat.EnterLong(bip, targetSignedQty, tagPrefix + "_L");
            }
            else if (delta > 0)
            {
                if (curQty >= 0) _strat.EnterLong(bip, delta, tagPrefix + "_L");
                else _strat.ExitShort(bip, delta, tagPrefix + "_TR", tagPrefix + "_S");
            }
            else if (delta < 0)
            {
                if (curQty <= 0) _strat.EnterShort(bip, Math.Abs(delta), tagPrefix + "_S");
                else _strat.ExitLong(bip, Math.Abs(delta), tagPrefix + "_TR", tagPrefix + "_L");
            }
        }

        private void RenderHud()
        {
            try
            {
                string hud = _coord.BuildHudText(_label);
                Draw.TextFixed(_strat, "EdgeLabFundedSyncHud", hud, TextPosition.BottomLeft);
            }
            catch
            {
            }
        }
    }

    /// <summary>
    /// Unified NinjaTrader 8 portfolio executor for FUNDEDSYNC (NQ / MNQ), defaulting to P_OPT_SF_v2.
    /// Encodes all 7 uncorrelated causal modules:
    /// - R_osc30_end660_ATR50
    /// - Z_b15_e20_eff40_ATR50
    /// - T_stop100_BE15R_calFalse
    /// - V_nm25_noCap_mae30
    /// - W_slope_allowReFalse_ATR25
    /// - N_d5_fbTrue_ATR25
    /// - SOMEOD_ext_NQ (5m NY+7h using SMA of True Range over 14 bars)
    ///
    /// DATA REQUIREMENT:
    /// Attach to an NQ or MNQ 1-Minute ETH chart with at least 500 trading days (~2 years) loaded
    /// so T quarterly KNN accumulates >= 100 exclusive shadow rows and V accumulates 252 RTH ranges.
    /// </summary>
    public class EdgeLabFundedSyncPortfolio : Strategy
    {
        private FundedSyncNt8Adapter _adapter;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "P_OPT_SF_v2 FUNDEDSYNC Unified Portfolio (7 causal modules, W5 weights, MaxOpenR=3, Prop compliance).";
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

                Preset = FundedSyncPortfolioPreset.P_OPT_SF_v2;
                PropProfile = FundedSyncPropProfile.LucidFlex_150K_Equilibrado;
                AccountMode = FundedSyncAccountMode.Evaluation;
                EvalRisk1R_USD = 450.0;
                FundedRisk1R_USD = 450.0;
                MaxOpenR = 3.0;
                MaxMicroContracts = 100;
                CollisionPolicy = FundedSyncCollisionPolicy.Netting;
                SecondaryMnqSymbol = string.Empty;

                HardFlattenHHMM_ET = 1640;
                EnforceEvalDailyCap = true;
                EvalDailyCapUSD = 3420.0;
                DailyLossLimitUSD = 2700.0;
                EnableWTrail = false;

                EnableR = true;
                EnableZ = true;
                EnableT = true;
                EnableV = true;
                EnableW = true;
                EnableN = true;
                EnableSOMEOD = true;

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
                    AddDataSeries(SecondaryMnqSymbol.Trim(), BarsPeriodType.Minute, 1);
            }
            else if (State == State.DataLoaded)
            {
                bool[] enables = new bool[] { EnableR, EnableZ, EnableT, EnableV, EnableW, EnableN, EnableSOMEOD };
                double[] customW = new double[] { WeightR, WeightZ, WeightT, WeightV, WeightW, WeightN, WeightSOMEOD };
                _adapter = FundedSyncNt8Adapter.CreateFromPreset(
                    this,
                    Preset.ToString(),
                    Preset,
                    PropProfile,
                    AccountMode,
                    EvalRisk1R_USD,
                    FundedRisk1R_USD,
                    MaxOpenR,
                    MaxMicroContracts,
                    CollisionPolicy,
                    HardFlattenHHMM_ET,
                    EnforceEvalDailyCap,
                    EvalDailyCapUSD,
                    DailyLossLimitUSD,
                    EnableWTrail,
                    SecondaryMnqSymbol,
                    EnableParityCsvLog,
                    ParityCsvFileName,
                    enables,
                    customW);
                Print("EdgeLabFundedSyncPortfolio initialized. Preset=" + Preset + " Profile=" + PropProfile + " (>= 500 trading days M1 ETH required).");
            }
        }

        protected override void OnBarUpdate()
        {
            if (_adapter != null)
                _adapter.OnBarUpdate();
        }

        #region NinjaScript Properties
        [NinjaScriptProperty]
        [Display(Name = "Portfolio Preset", Order = 1, GroupName = "01. Prop Account")]
        public FundedSyncPortfolioPreset Preset { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prop Firm Profile", Order = 2, GroupName = "01. Prop Account")]
        public FundedSyncPropProfile PropProfile { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Account Mode", Order = 3, GroupName = "01. Prop Account")]
        public FundedSyncAccountMode AccountMode { get; set; }

        [NinjaScriptProperty]
        [Range(50.0, 2500.0)]
        [Display(Name = "Eval Risk 1R USD (Custom)", Order = 4, GroupName = "01. Prop Account")]
        public double EvalRisk1R_USD { get; set; }

        [NinjaScriptProperty]
        [Range(50.0, 2500.0)]
        [Display(Name = "Funded Risk 1R USD (Custom)", Order = 5, GroupName = "01. Prop Account")]
        public double FundedRisk1R_USD { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Max Concurrent Open R", Order = 6, GroupName = "01. Prop Account")]
        public double MaxOpenR { get; set; }

        [NinjaScriptProperty]
        [Range(1, 200)]
        [Display(Name = "Max Micros Cap (Custom)", Order = 7, GroupName = "01. Prop Account")]
        public int MaxMicroContracts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Collision Policy (Custom)", Order = 8, GroupName = "01. Prop Account")]
        public FundedSyncCollisionPolicy CollisionPolicy { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Secondary MNQ Symbol (Hybrid)", Order = 9, GroupName = "01. Prop Account")]
        public string SecondaryMnqSymbol { get; set; }

        [NinjaScriptProperty]
        [Range(1500, 2400)]
        [Display(Name = "Hard Flatten HHMM ET (Custom)", Order = 10, GroupName = "02. Compliance")]
        public int HardFlattenHHMM_ET { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enforce Eval Daily Cap (Custom)", Order = 11, GroupName = "02. Compliance")]
        public bool EnforceEvalDailyCap { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 50000.0)]
        [Display(Name = "Eval Daily Cap USD (Custom)", Order = 12, GroupName = "02. Compliance")]
        public double EvalDailyCapUSD { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 50000.0)]
        [Display(Name = "Daily Loss Limit USD (Custom)", Order = 13, GroupName = "02. Compliance")]
        public double DailyLossLimitUSD { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable W Trailing (default false)", Order = 14, GroupName = "02. Compliance")]
        public bool EnableWTrail { get; set; }

        [NinjaScriptProperty] [Display(Name = "Enable R", Order = 20, GroupName = "03. Modules & Custom Weights")] public bool EnableR { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable Z", Order = 21, GroupName = "03. Modules & Custom Weights")] public bool EnableZ { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable T", Order = 22, GroupName = "03. Modules & Custom Weights")] public bool EnableT { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable V", Order = 23, GroupName = "03. Modules & Custom Weights")] public bool EnableV { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable W", Order = 24, GroupName = "03. Modules & Custom Weights")] public bool EnableW { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable N", Order = 25, GroupName = "03. Modules & Custom Weights")] public bool EnableN { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enable SOMEOD", Order = 26, GroupName = "03. Modules & Custom Weights")] public bool EnableSOMEOD { get; set; }

        [NinjaScriptProperty] [Display(Name = "Weight R (Custom)", Order = 30, GroupName = "03. Modules & Custom Weights")] public double WeightR { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight Z (Custom)", Order = 31, GroupName = "03. Modules & Custom Weights")] public double WeightZ { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight T (Custom)", Order = 32, GroupName = "03. Modules & Custom Weights")] public double WeightT { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight V (Custom)", Order = 33, GroupName = "03. Modules & Custom Weights")] public double WeightV { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight W (Custom)", Order = 34, GroupName = "03. Modules & Custom Weights")] public double WeightW { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight N (Custom)", Order = 35, GroupName = "03. Modules & Custom Weights")] public double WeightN { get; set; }
        [NinjaScriptProperty] [Display(Name = "Weight SOMEOD (Custom)", Order = 36, GroupName = "03. Modules & Custom Weights")] public double WeightSOMEOD { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable Parity CSV Log", Order = 40, GroupName = "04. Parity Logger")]
        public bool EnableParityCsvLog { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Parity CSV File Name", Order = 41, GroupName = "04. Parity Logger")]
        public string ParityCsvFileName { get; set; }
        #endregion
    }
}
