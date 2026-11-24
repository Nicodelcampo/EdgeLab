using System;
using cAlgo.API;
using EdgeLabFundedSyncCfd;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class EdgeLabFundedSyncPortfolio : Robot
    {
        [Parameter("Portfolio Preset", Group = "01. Prop Account", DefaultValue = FundedSyncPortfolioPreset.P_OPT_SF_v2)]
        public FundedSyncPortfolioPreset Preset { get; set; }

        [Parameter("Prop Firm Profile", Group = "01. Prop Account", DefaultValue = FundedSyncCfdPropProfile.FTMO_Swing_100K)]
        public FundedSyncCfdPropProfile PropProfile { get; set; }

        [Parameter("Account Mode", Group = "01. Prop Account", DefaultValue = FundedSyncAccountMode.Evaluation)]
        public FundedSyncAccountMode AccountMode { get; set; }

        [Parameter("Custom Sizing Mode", Group = "01. Prop Account", DefaultValue = FundedSyncRiskSizingMode.PercentOfInitialBalance)]
        public FundedSyncRiskSizingMode CustomSizingMode { get; set; }

        [Parameter("Custom Eval Risk 1R (%)", Group = "01. Prop Account", DefaultValue = 0.75, MinValue = 0.05, MaxValue = 5.0)]
        public double EvalRiskPct { get; set; }

        [Parameter("Custom Funded Risk 1R (%)", Group = "01. Prop Account", DefaultValue = 0.75, MinValue = 0.05, MaxValue = 5.0)]
        public double FundedRiskPct { get; set; }

        [Parameter("Custom Eval Risk 1R (USD)", Group = "01. Prop Account", DefaultValue = 750.0, MinValue = 10.0, MaxValue = 25000.0)]
        public double EvalRisk1R_USD { get; set; }

        [Parameter("Custom Funded Risk 1R (USD)", Group = "01. Prop Account", DefaultValue = 750.0, MinValue = 10.0, MaxValue = 25000.0)]
        public double FundedRisk1R_USD { get; set; }

        [Parameter("Custom Max Open R", Group = "01. Prop Account", DefaultValue = 3.0, MinValue = 0.5, MaxValue = 15.0)]
        public double MaxOpenR { get; set; }

        [Parameter("Max Lots Per Sleeve (0=Unlim)", Group = "01. Prop Account", DefaultValue = 50.0, MinValue = 0.0, MaxValue = 1000.0)]
        public double MaxLotsPerSleeve { get; set; }

        [Parameter("Max Total Net Lots (0=Unlim)", Group = "01. Prop Account", DefaultValue = 100.0, MinValue = 0.0, MaxValue = 2000.0)]
        public double MaxTotalNetLots { get; set; }

        [Parameter("Custom Collision Policy", Group = "01. Prop Account", DefaultValue = FundedSyncCollisionPolicy.Netting)]
        public FundedSyncCollisionPolicy CollisionPolicy { get; set; }

        [Parameter("Custom Hard Flatten HHMM ET", Group = "02. Compliance", DefaultValue = 1640, MinValue = 1500, MaxValue = 2400)]
        public int HardFlattenHHMM_ET { get; set; }

        [Parameter("Custom Enforce Eval Daily Cap", Group = "02. Compliance", DefaultValue = false)]
        public bool EnforceEvalDailyCap { get; set; }

        [Parameter("Custom Eval Daily Cap (%)", Group = "02. Compliance", DefaultValue = 0.0, MinValue = 0.0, MaxValue = 20.0)]
        public double EvalDailyCapPct { get; set; }

        [Parameter("Custom Daily Loss Limit (%)", Group = "02. Compliance", DefaultValue = 3.80, MinValue = 0.0, MaxValue = 20.0)]
        public double DailyLossLimitPct { get; set; }

        [Parameter("Enable Funded DD Brake", Group = "02. Compliance", DefaultValue = false)]
        public bool EnableFundedDdBrake { get; set; }

        [Parameter("Funded DD Brake Threshold (%)", Group = "02. Compliance", DefaultValue = 5.0, MinValue = 0.5, MaxValue = 20.0)]
        public double FundedDdBrakeThresholdPct { get; set; }

        [Parameter("Funded DD Brake Scale", Group = "02. Compliance", DefaultValue = 0.50, MinValue = 0.10, MaxValue = 1.0)]
        public double FundedDdBrakeScale { get; set; }

        [Parameter("Custom Enable News Guard", Group = "02. Compliance", DefaultValue = false)]
        public bool EnableNewsGuard { get; set; }

        [Parameter("Custom News Blackout (Min)", Group = "02. Compliance", DefaultValue = 2, MinValue = 0, MaxValue = 30)]
        public int NewsBlackoutMinutes { get; set; }

        [Parameter("News Times ET (HHMM CSV)", Group = "02. Compliance", DefaultValue = "0830,1000,1400")]
        public string NewsHoursEtCsv { get; set; }

        [Parameter("Enable W Trailing (default false)", Group = "02. Compliance", DefaultValue = false)]
        public bool EnableWTrail { get; set; }

        [Parameter("Enable R", Group = "03. Modules & Weights", DefaultValue = true)] public bool EnableR { get; set; }
        [Parameter("Enable Z", Group = "03. Modules & Weights", DefaultValue = true)] public bool EnableZ { get; set; }
        [Parameter("Enable T", Group = "03. Modules & Weights", DefaultValue = true)] public bool EnableT { get; set; }
        [Parameter("Enable V", Group = "03. Modules & Weights", DefaultValue = true)] public bool EnableV { get; set; }
        [Parameter("Enable W", Group = "03. Modules & Weights", DefaultValue = true)] public bool EnableW { get; set; }
        [Parameter("Enable N", Group = "03. Modules & Weights", DefaultValue = true)] public bool EnableN { get; set; }
        [Parameter("Enable SOMEOD", Group = "03. Modules & Weights", DefaultValue = true)] public bool EnableSOMEOD { get; set; }

        [Parameter("Weight R (Custom)", Group = "03. Modules & Weights", DefaultValue = 1.653354)] public double WeightR { get; set; }
        [Parameter("Weight Z (Custom)", Group = "03. Modules & Weights", DefaultValue = 1.965598)] public double WeightZ { get; set; }
        [Parameter("Weight T (Custom)", Group = "03. Modules & Weights", DefaultValue = 0.768284)] public double WeightT { get; set; }
        [Parameter("Weight V (Custom)", Group = "03. Modules & Weights", DefaultValue = 1.019769)] public double WeightV { get; set; }
        [Parameter("Weight W (Custom)", Group = "03. Modules & Weights", DefaultValue = 0.915674)] public double WeightW { get; set; }
        [Parameter("Weight N (Custom)", Group = "03. Modules & Weights", DefaultValue = 1.252428)] public double WeightN { get; set; }
        [Parameter("Weight SOMEOD (Custom)", Group = "03. Modules & Weights", DefaultValue = 0.911410)] public double WeightSOMEOD { get; set; }

        [Parameter("USD/Pt per 1 Lot (0=Auto)", Group = "04. Execution & Warmup", DefaultValue = 0.0, MinValue = 0.0, MaxValue = 1000.0)]
        public double OverrideUsdPerPtPerLot { get; set; }

        [Parameter("Assumed Spread+Slippage (Pts)", Group = "04. Execution & Warmup", DefaultValue = 1.50, MinValue = 0.0, MaxValue = 20.0)]
        public double FrictionPts { get; set; }

        [Parameter("Logical Signal Tick (0.25 NQ)", Group = "04. Execution & Warmup", DefaultValue = 0.25, MinValue = 0.01, MaxValue = 1.0)]
        public double SignalTickSize { get; set; }

        [Parameter("Check Stops/Targets OnTick", Group = "04. Execution & Warmup", DefaultValue = true)]
        public bool CheckStopsOnTick { get; set; }

        [Parameter("Sync Broker Protective SL", Group = "04. Execution & Warmup", DefaultValue = true)]
        public bool UseBrokerProtectiveStop { get; set; }

        [Parameter("Warmup Target M1 Bars", Group = "04. Execution & Warmup", DefaultValue = 350000, MinValue = 1000, MaxValue = 1000000)]
        public int WarmupTargetBars { get; set; }

        [Parameter("Auto Load More History", Group = "04. Execution & Warmup", DefaultValue = true)]
        public bool AutoLoadWarmupHistory { get; set; }

        [Parameter("Allow Mid-Session Sync OnStart", Group = "04. Execution & Warmup", DefaultValue = false)]
        public bool AllowMidSessionSyncOnStart { get; set; }

        [Parameter("Show Chart HUD in Backtest", Group = "04. Execution & Warmup", DefaultValue = false)]
        public bool ShowHudInBacktest { get; set; }

        [Parameter("Emit Parity Trade Logs", Group = "04. Execution & Warmup", DefaultValue = false)]
        public bool EnableParityLog { get; set; }

        private FundedSyncCTraderAdapter _adapter;

        protected override void OnStart()
        {
            bool[] enables = { EnableR, EnableZ, EnableT, EnableV, EnableW, EnableN, EnableSOMEOD };
            double[] weights = { WeightR, WeightZ, WeightT, WeightV, WeightW, WeightN, WeightSOMEOD };
            _adapter = FundedSyncCTraderAdapter.CreateFromPreset(
                this, "FS_Port_" + Preset, Preset, PropProfile, AccountMode, CustomSizingMode,
                EvalRiskPct, FundedRiskPct, EvalRisk1R_USD, FundedRisk1R_USD, MaxOpenR,
                MaxLotsPerSleeve, MaxTotalNetLots, CollisionPolicy, HardFlattenHHMM_ET,
                EnforceEvalDailyCap, EvalDailyCapPct, DailyLossLimitPct,
                EnableFundedDdBrake, FundedDdBrakeThresholdPct, FundedDdBrakeScale,
                EnableNewsGuard, NewsBlackoutMinutes, NewsHoursEtCsv,
                OverrideUsdPerPtPerLot, FrictionPts, SignalTickSize,
                CheckStopsOnTick, UseBrokerProtectiveStop,
                WarmupTargetBars, AutoLoadWarmupHistory, AllowMidSessionSyncOnStart,
                EnableWTrail, ShowHudInBacktest, EnableParityLog,
                enables, weights);
        }

        protected override void OnBar()
        {
            if (_adapter != null) _adapter.OnBar();
        }

        protected override void OnTick()
        {
            if (_adapter != null) _adapter.OnTick();
        }

        protected override void OnStop()
        {
            if (_adapter != null) _adapter.OnStop();
        }
    }
}
