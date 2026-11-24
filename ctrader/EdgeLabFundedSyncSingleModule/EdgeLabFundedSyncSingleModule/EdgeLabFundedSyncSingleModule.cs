using System;
using cAlgo.API;
using EdgeLabFundedSyncCfd;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class EdgeLabFundedSyncSingleModule : Robot
    {
        [Parameter("Target Module", Group = "01. Module & Sizing", DefaultValue = FundedSyncModuleId.R_osc30_end660_ATR50)]
        public FundedSyncModuleId TargetModule { get; set; }

        [Parameter("Sizing Mode", Group = "01. Module & Sizing", DefaultValue = FundedSyncRiskSizingMode.PercentOfInitialBalance)]
        public FundedSyncRiskSizingMode SizingMode { get; set; }

        [Parameter("Risk 1R (%)", Group = "01. Module & Sizing", DefaultValue = 0.75, MinValue = 0.05, MaxValue = 5.0)]
        public double Risk1R_Pct { get; set; }

        [Parameter("Risk 1R (USD)", Group = "01. Module & Sizing", DefaultValue = 750.0, MinValue = 10.0, MaxValue = 25000.0)]
        public double Risk1R_USD { get; set; }

        [Parameter("Max Lots Cap (0=Unlim)", Group = "01. Module & Sizing", DefaultValue = 50.0, MinValue = 0.0, MaxValue = 1000.0)]
        public double MaxLots { get; set; }

        [Parameter("Hard Flatten HHMM ET", Group = "01. Module & Sizing", DefaultValue = 1640, MinValue = 1500, MaxValue = 2400)]
        public int HardFlattenHHMM_ET { get; set; }

        [Parameter("R Osc ATR Mult", Group = "02. Module Params", DefaultValue = 3.0, MinValue = 0.5, MaxValue = 10.0)]
        public double ROscAtrMult { get; set; }

        [Parameter("R Entry End Min ET", Group = "02. Module Params", DefaultValue = 660, MinValue = 570, MaxValue = 960)]
        public int REndMinEt { get; set; }

        [Parameter("R SL ATR K", Group = "02. Module Params", DefaultValue = 0.50, MinValue = 0.05, MaxValue = 2.0)]
        public double RSlAtrK { get; set; }

        [Parameter("Z Bucket Minutes", Group = "02. Module Params", DefaultValue = 15, MinValue = 5, MaxValue = 60)]
        public int ZBucketMin { get; set; }

        [Parameter("Z EMA Period", Group = "02. Module Params", DefaultValue = 20, MinValue = 5, MaxValue = 100)]
        public int ZEmaPeriod { get; set; }

        [Parameter("Z Min Efficiency Pct", Group = "02. Module Params", DefaultValue = 40.0, MinValue = 0.0, MaxValue = 100.0)]
        public double ZMinEffPct { get; set; }

        [Parameter("Z SL ATR K", Group = "02. Module Params", DefaultValue = 0.50, MinValue = 0.05, MaxValue = 2.0)]
        public double ZSlAtrK { get; set; }

        [Parameter("T Stop ORB Mult", Group = "02. Module Params", DefaultValue = 1.0, MinValue = 0.25, MaxValue = 3.0)]
        public double TStopOrbMult { get; set; }

        [Parameter("T BE Trigger R", Group = "02. Module Params", DefaultValue = 1.5, MinValue = 0.0, MaxValue = 5.0)]
        public double TBeTriggerR { get; set; }

        [Parameter("V Noise Mult", Group = "02. Module Params", DefaultValue = 0.25, MinValue = 0.05, MaxValue = 2.0)]
        public double VNoiseMult { get; set; }

        [Parameter("V SL ATR K", Group = "02. Module Params", DefaultValue = 0.30, MinValue = 0.05, MaxValue = 2.0)]
        public double VSlAtrK { get; set; }

        [Parameter("W SL ATR K", Group = "02. Module Params", DefaultValue = 0.25, MinValue = 0.05, MaxValue = 2.0)]
        public double WSlAtrK { get; set; }

        [Parameter("W Enable Trail", Group = "02. Module Params", DefaultValue = false)]
        public bool EnableWTrail { get; set; }

        [Parameter("N Lookback Days", Group = "02. Module Params", DefaultValue = 5, MinValue = 1, MaxValue = 30)]
        public int NDays { get; set; }

        [Parameter("N SL ATR K", Group = "02. Module Params", DefaultValue = 0.25, MinValue = 0.05, MaxValue = 2.0)]
        public double NSlAtrK { get; set; }

        [Parameter("USD/Pt per 1 Lot (0=Auto)", Group = "03. Execution & Warmup", DefaultValue = 0.0, MinValue = 0.0, MaxValue = 1000.0)]
        public double OverrideUsdPerPtPerLot { get; set; }

        [Parameter("Assumed Spread+Slippage (Pts)", Group = "03. Execution & Warmup", DefaultValue = 1.50, MinValue = 0.0, MaxValue = 20.0)]
        public double FrictionPts { get; set; }

        [Parameter("Logical Signal Tick (0.25 NQ)", Group = "03. Execution & Warmup", DefaultValue = 0.25, MinValue = 0.01, MaxValue = 1.0)]
        public double SignalTickSize { get; set; }

        [Parameter("Check Stops/Targets OnTick", Group = "03. Execution & Warmup", DefaultValue = true)]
        public bool CheckStopsOnTick { get; set; }

        [Parameter("Sync Broker Protective SL", Group = "03. Execution & Warmup", DefaultValue = true)]
        public bool UseBrokerProtectiveStop { get; set; }

        [Parameter("Warmup Target M1 Bars", Group = "03. Execution & Warmup", DefaultValue = 350000, MinValue = 1000, MaxValue = 1000000)]
        public int WarmupTargetBars { get; set; }

        [Parameter("Auto Load More History", Group = "03. Execution & Warmup", DefaultValue = true)]
        public bool AutoLoadWarmupHistory { get; set; }

        [Parameter("Allow Mid-Session Sync OnStart", Group = "03. Execution & Warmup", DefaultValue = false)]
        public bool AllowMidSessionSyncOnStart { get; set; }

        [Parameter("Show Chart HUD in Backtest", Group = "03. Execution & Warmup", DefaultValue = false)]
        public bool ShowHudInBacktest { get; set; }

        [Parameter("Emit Parity Trade Logs", Group = "03. Execution & Warmup", DefaultValue = true)]
        public bool EnableParityLog { get; set; }

        private FundedSyncCTraderAdapter _adapter;

        protected override void OnStart()
        {
            int idx = (int)TargetModule;
            bool[] enables = new bool[FundedSyncMath.ModuleOrder.Length];
            double[] weights = new double[FundedSyncMath.ModuleOrder.Length];
            for (int i = 0; i < FundedSyncMath.ModuleOrder.Length; i++)
            {
                enables[i] = (i == idx);
                weights[i] = (i == idx) ? 1.0 : 0.0;
            }

            _adapter = FundedSyncCTraderAdapter.CreateFromPreset(
                this, "FS_Single_" + TargetModule, FundedSyncPortfolioPreset.CustomWeights,
                FundedSyncCfdPropProfile.Personal_Custom, FundedSyncAccountMode.Evaluation, SizingMode,
                Risk1R_Pct, Risk1R_Pct, Risk1R_USD, Risk1R_USD, 3.0,
                MaxLots, MaxLots, FundedSyncCollisionPolicy.Independent, HardFlattenHHMM_ET,
                false, 0.0, 0.0,
                false, 5.0, 0.50,
                false, 2, "0830,1000,1400",
                OverrideUsdPerPtPerLot, FrictionPts, SignalTickSize,
                CheckStopsOnTick, UseBrokerProtectiveStop,
                WarmupTargetBars, AutoLoadWarmupHistory, AllowMidSessionSyncOnStart,
                EnableWTrail, ShowHudInBacktest, EnableParityLog,
                enables, weights,
                rOscMult: ROscAtrMult, rEndEt: REndMinEt, rSlAtr: RSlAtrK,
                zBucketMin: ZBucketMin, zEmaPeriod: ZEmaPeriod, zMinEffPct: ZMinEffPct, zSlAtr: ZSlAtrK,
                tStopOrbMult: TStopOrbMult, tBeTrigR: TBeTriggerR,
                vNoiseMult: VNoiseMult, vSlAtr: VSlAtrK,
                wSlAtr: WSlAtrK, nDays: NDays, nSlAtr: NSlAtrK);
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
