using System;
using System.Collections.Generic;
using System.Globalization;
using cAlgo.API;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    using EdgeLabFundedSyncCfd;

    /// <summary>
    /// Shared cTrader Automate runtime adapter connecting PortfolioCoordinator
    /// to cTrader M1 Bars warmup, zero-lag bar-close execution, tick SL/TP monitoring,
    /// Hedged/Netted position reconciliation, and chart HUD rendering.
    /// Compatible with C# 5.0 (csc.exe /warnaserror) and cTrader .NET 6.
    /// </summary>
    internal sealed class FundedSyncCTraderAdapter
    {
        private readonly Robot _robot;
        private readonly PortfolioCoordinator _coord;
        private readonly string _botLabel;
        private readonly bool _showHudInBacktest;
        private readonly bool _checkStopsOnTick;
        private readonly bool _useBrokerProtectiveStop;
        private readonly bool _allowMidSessionSyncOnStart;

        private Bars _m1Bars;
        private TimeZoneInfo _nyTz;
        private TimeZoneInfo _ctTz;
        private DateTime _lastFedOpenUtc = DateTime.MinValue;
        private double _lastBrokerNetUnits = 0.0;
        private bool _initialized;

        private FundedSyncCTraderAdapter(
            Robot robot,
            PortfolioCoordinator coord,
            string botLabel,
            bool showHudInBacktest,
            bool checkStopsOnTick,
            bool useBrokerProtectiveStop,
            bool allowMidSessionSyncOnStart)
        {
            _robot = robot;
            _coord = coord;
            _botLabel = botLabel;
            _showHudInBacktest = showHudInBacktest;
            _checkStopsOnTick = checkStopsOnTick;
            _useBrokerProtectiveStop = useBrokerProtectiveStop;
            _allowMidSessionSyncOnStart = allowMidSessionSyncOnStart;
        }

        public static FundedSyncCTraderAdapter CreateFromPreset(
            Robot robot,
            string botLabel,
            FundedSyncPortfolioPreset preset,
            FundedSyncCfdPropProfile propProfile,
            FundedSyncAccountMode accountMode,
            FundedSyncRiskSizingMode customSizingMode,
            double evalRiskPct,
            double fundedRiskPct,
            double evalRiskUsd,
            double fundedRiskUsd,
            double maxOpenR,
            double maxLotsPerSleeve,
            double maxTotalNetLots,
            FundedSyncCollisionPolicy collisionPolicy,
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
            double overrideUsdPerPtPerLot,
            double frictionPts,
            double signalTickSize,
            bool checkStopsOnTick,
            bool useBrokerProtectiveStop,
            int warmupTargetBars,
            bool autoLoadWarmupHistory,
            bool allowMidSessionSyncOnStart,
            bool enableWTrail,
            bool showHudInBacktest,
            bool enableParityLog,
            bool[] enableOverrides,
            double[] weightOverrides,
            double rOscMult = 3.0, int rEndEt = 660, double rSlAtr = 0.50,
            int zBucketMin = 15, int zEmaPeriod = 20, double zMinEffPct = 40.0, double zSlAtr = 0.50,
            double tStopOrbMult = 1.0, double tBeTrigR = 1.5,
            double vNoiseMult = 0.25, double vSlAtr = 0.30,
            double wSlAtr = 0.25, int nDays = 5, double nSlAtr = 0.25)
        {
            Dictionary<string, double> weights;
            bool[] flags = new bool[FundedSyncMath.ModuleOrder.Length];
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

            CfdPropProfileDefaults prof = CfdPropProfileDefaults.For(propProfile);
            bool useProf = propProfile != FundedSyncCfdPropProfile.Personal_Custom;

            double initBal = Math.Max(robot.Account.Balance, 1.0);
            Symbol sym = robot.Symbol;

            double unitsPerLot = sym.QuantityToVolumeInUnits(1.0);
            if (unitsPerLot <= 0.0) unitsPerLot = 1.0;

            double tickVal = sym.TickValue;
            double tickSz = sym.TickSize;
            double usdPerPtPerUnit = (tickVal > 0.0 && tickSz > 0.0) ? (tickVal / tickSz) : 1.0;
            if (overrideUsdPerPtPerLot > 0.0)
                usdPerPtPerUnit = overrideUsdPerPtPerLot / unitsPerLot;

            double maxOpenREff = useProf ? prof.MaxOpenR : maxOpenR;
            double dlPctEff = useProf ? prof.DailyLossLimitPct : dailyLossLimitPct;
            double evCapPctEff = useProf ? prof.EvalDailyCapPct : evalDailyCapPct;
            bool enfCapEff = useProf ? prof.EnforceEvalDailyCap : enforceEvalDailyCap;

            var coord = new PortfolioCoordinator(
                weights, flags, enableWTrail: enableWTrail,
                rOscMult: rOscMult, rEndEt: rEndEt, rSlAtr: rSlAtr,
                zBucketMin: zBucketMin, zEmaPeriod: zEmaPeriod, zMinEffPct: zMinEffPct, zSlAtr: zSlAtr,
                tStopOrbMult: tStopOrbMult, tBeTrigR: tBeTrigR,
                vNoiseMult: vNoiseMult, vSlAtr: vSlAtr,
                wSlAtr: wSlAtr, nDays: nDays, nSlAtr: nSlAtr)
            {
                SignalTickSize = signalTickSize > 0.0 ? signalTickSize : 0.25,
                UsdPerPointPerUnit = usdPerPtPerUnit,
                VolumeStep = sym.VolumeInUnitsStep > 0.0 ? sym.VolumeInUnitsStep : 0.01,
                MinVolumeUnits = sym.VolumeInUnitsMin > 0.0 ? sym.VolumeInUnitsMin : 0.01,
                MaxVolumeUnitsPerSleeve = maxLotsPerSleeve > 0.0 ? sym.QuantityToVolumeInUnits(maxLotsPerSleeve) : sym.VolumeInUnitsMax,
                MaxTotalNetVolumeUnits = maxTotalNetLots > 0.0 ? sym.QuantityToVolumeInUnits(maxTotalNetLots) : sym.VolumeInUnitsMax,
                FrictionPts = frictionPts >= 0.0 ? frictionPts : 1.5,

                AccountMode = accountMode,
                SizingMode = useProf ? prof.SizingMode : customSizingMode,
                InitialBalanceUsd = initBal,
                CurrentBalanceUsd = initBal,
                HighWaterBalanceUsd = initBal,
                EvalRiskPct = useProf ? prof.EvalRiskPct : evalRiskPct,
                FundedRiskPct = useProf ? prof.FundedRiskPct : fundedRiskPct,
                EvalRisk1R_USD = useProf ? prof.EvalRiskUsd : evalRiskUsd,
                FundedRisk1R_USD = useProf ? prof.FundedRiskUsd : fundedRiskUsd,
                MaxOpenR = maxOpenREff,
                CollisionPolicy = useProf ? prof.CollisionPolicy : collisionPolicy,

                HardFlattenHHMM_ET = useProf ? prof.HardFlattenHHMM_ET : hardFlattenHhmmEt,
                EnforceEvalDailyCap = enfCapEff,
                EvalDailyCapUSD = (enfCapEff && evCapPctEff > 0.0) ? initBal * (evCapPctEff / 100.0) : 0.0,
                DailyLossLimitUSD = dlPctEff > 0.0 ? initBal * (dlPctEff / 100.0) : 0.0,

                EnableFundedDdBrake = useProf ? prof.EnableFundedDdBrake : enableFundedDdBrake,
                FundedDdBrakeThresholdPct = useProf ? prof.FundedDdBrakeThresholdPct : fundedDdBrakeThresholdPct,
                FundedDdBrakeScale = useProf ? prof.FundedDdBrakeScale : fundedDdBrakeScale,

                EnableNewsGuard = useProf ? prof.EnableNewsGuard : enableNewsGuard,
                NewsBlackoutMinutes = useProf ? prof.NewsBlackoutMinutes : newsBlackoutMinutes,
                NewsMinutesEt = FundedSyncMath.ParseBlackoutMinutesCsv(newsHoursEtCsv),

                EmitTradeLogs = enableParityLog,
                LogCallback = delegate(string msg) { robot.Print(msg); }
            };

            var adapter = new FundedSyncCTraderAdapter(
                robot, coord, botLabel, showHudInBacktest, checkStopsOnTick, useBrokerProtectiveStop, allowMidSessionSyncOnStart);
            adapter.InitializeAndWarmup(warmupTargetBars, autoLoadWarmupHistory);
            return adapter;
        }

        private void InitializeAndWarmup(int warmupTargetBars, bool autoLoadWarmupHistory)
        {
            _nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time");
            _ctTz = FundedSyncMath.ResolveTz("Central Standard Time");

            if (_robot.TimeFrame != TimeFrame.Minute)
            {
                _robot.Print("WARNING: Chart timeframe is {0}. Bot reads M1 series directly; attach to M1 recommended.",
                    _robot.TimeFrame.Name);
            }

            _m1Bars = _robot.TimeFrame == TimeFrame.Minute
                ? _robot.Bars
                : _robot.MarketData.GetBars(TimeFrame.Minute);

            if (autoLoadWarmupHistory && warmupTargetBars > 0 && _m1Bars.Count < warmupTargetBars)
            {
                int guard = 0;
                while (_m1Bars.Count < warmupTargetBars && guard < 300)
                {
                    int loaded = _m1Bars.LoadMoreHistory();
                    guard++;
                    if (loaded <= 0) break;
                }
            }

            _coord.WarmupOnly = true;
            int closedCount = Math.Max(0, _m1Bars.Count - 1);
            for (int i = 0; i < closedCount; i++)
            {
                DateTime openUtc = DateTime.SpecifyKind(_m1Bars.OpenTimes[i], DateTimeKind.Utc);
                DateTime closeUtc = openUtc.AddMinutes(1);
                double vol = _m1Bars.TickVolumes[i];
                BarTimeContext ctx = FundedSyncMath.BuildBarTimeContext(
                    closeUtc,
                    _m1Bars.OpenPrices[i],
                    _m1Bars.HighPrices[i],
                    _m1Bars.LowPrices[i],
                    _m1Bars.ClosePrices[i],
                    vol > 0.0 ? vol : 1.0,
                    _nyTz,
                    _ctTz);
                _coord.FeedHistoricalBar(ctx);
                _lastFedOpenUtc = openUtc;
            }
            _coord.WarmupOnly = false;

            if (!_allowMidSessionSyncOnStart && closedCount > 0)
            {
                DateTime refNy = TimeZoneInfo.ConvertTimeFromUtc(DateTime.SpecifyKind(_robot.TimeInUtc, DateTimeKind.Utc), _nyTz);
                _coord.FlattenAllVirtualAtEndOfWarmup(_m1Bars.ClosePrices[closedCount - 1], refNy);
            }

            _lastBrokerNetUnits = GetCurrentBrokerNetUnits();
            _m1Bars.BarOpened += OnM1BarOpened;
            _initialized = true;

            _robot.Print("{0} warmed up: M1Bars={1}, ATR20={2:F1}, T_KnnRows={3}, V_Days={4}, UsdPerPtPerLot={5:F4}, UnitPerLot={6:F2}",
                _botLabel,
                closedCount,
                double.IsNaN(_coord.Atr20Session) ? 0.0 : _coord.Atr20Session,
                _coord.KnnTrainRowsCount,
                _coord.VaultDaysCount,
                _coord.UsdPerPointPerUnit * _robot.Symbol.QuantityToVolumeInUnits(1.0),
                _robot.Symbol.QuantityToVolumeInUnits(1.0));
        }

        private void OnM1BarOpened(BarOpenedEventArgs args)
        {
            ProcessClosedBars();
        }

        public void OnBar()
        {
            ProcessClosedBars();
        }

        public void OnTick()
        {
            if (!_initialized) return;

            if (_m1Bars.Count >= 2)
            {
                DateTime latestClosedOpenUtc = DateTime.SpecifyKind(_m1Bars.OpenTimes[_m1Bars.Count - 2], DateTimeKind.Utc);
                if (latestClosedOpenUtc > _lastFedOpenUtc)
                    ProcessClosedBars();
            }

            if (_checkStopsOnTick && _coord.EvaluateTick(_robot.Symbol.Bid, _robot.Symbol.Ask, _robot.TimeInUtc, _nyTz))
            {
                ReconcileNetPosition();
                RenderHud();
            }
        }

        public void OnStop()
        {
            if (_m1Bars != null)
                _m1Bars.BarOpened -= OnM1BarOpened;
        }

        private void ProcessClosedBars()
        {
            if (!_initialized || _m1Bars == null || _m1Bars.Count < 2) return;

            UpdateAccountMetrics();

            int limitIdx = _m1Bars.Count - 1;
            int firstIdx = FindFirstUnfedBarIndex(limitIdx);
            if (firstIdx < 0) return;

            bool anyFed = false;
            for (int i = firstIdx; i < limitIdx; i++)
            {
                DateTime openUtc = DateTime.SpecifyKind(_m1Bars.OpenTimes[i], DateTimeKind.Utc);
                if (openUtc <= _lastFedOpenUtc) continue;

                DateTime closeUtc = openUtc.AddMinutes(1);
                double vol = _m1Bars.TickVolumes[i];
                BarTimeContext ctx = FundedSyncMath.BuildBarTimeContext(
                    closeUtc,
                    _m1Bars.OpenPrices[i],
                    _m1Bars.HighPrices[i],
                    _m1Bars.LowPrices[i],
                    _m1Bars.ClosePrices[i],
                    vol > 0.0 ? vol : 1.0,
                    _nyTz,
                    _ctTz);

                bool isNewestClosed = (i == limitIdx - 1);
                double nextBid = isNewestClosed ? _robot.Symbol.Bid : _m1Bars.OpenPrices[i + 1];
                double nextAsk = isNewestClosed ? _robot.Symbol.Ask : _m1Bars.OpenPrices[i + 1];
                DateTime nextOpenUtc = DateTime.SpecifyKind(_m1Bars.OpenTimes[i + 1], DateTimeKind.Utc);
                DateTime nextOpenNy = TimeZoneInfo.ConvertTimeFromUtc(nextOpenUtc, _nyTz);

                _coord.FeedClosedBarAndFillAtNextOpen(ctx, nextBid, nextAsk, nextOpenNy);
                _lastFedOpenUtc = openUtc;
                anyFed = true;
            }

            if (anyFed)
            {
                ReconcileNetPosition();
                RenderHud();
            }
        }

        private int FindFirstUnfedBarIndex(int limitIdx)
        {
            if (limitIdx <= 0) return -1;
            if (_lastFedOpenUtc == DateTime.MinValue) return 0;
            for (int i = limitIdx - 1; i >= 0; i--)
            {
                DateTime t = DateTime.SpecifyKind(_m1Bars.OpenTimes[i], DateTimeKind.Utc);
                if (t <= _lastFedOpenUtc)
                    return (i + 1 < limitIdx) ? (i + 1) : -1;
            }
            return 0;
        }

        private void UpdateAccountMetrics()
        {
            double bal = _robot.Account.Balance;
            double eq = _robot.Account.Equity;
            _coord.CurrentBalanceUsd = bal;
            if (eq > _coord.HighWaterBalanceUsd)
                _coord.HighWaterBalanceUsd = eq;
        }

        private double GetCurrentBrokerNetUnits()
        {
            Position[] list = _robot.Positions.FindAll(_botLabel, _robot.SymbolName);
            double net = 0.0;
            for (int i = 0; i < list.Length; i++)
                net += list[i].TradeType == TradeType.Buy ? list[i].VolumeInUnits : -list[i].VolumeInUnits;
            return net;
        }

        private void ReconcileNetPosition()
        {
            double targetNet = (_coord.HardFlattenedToday || _coord.DailyCapTriggeredToday || _coord.DailyLossTriggeredToday)
                ? 0.0
                : _coord.TargetNetVolumeUnits;

            targetNet = NormalizeSignedVolume(targetNet);

            Position[] positions = _robot.Positions.FindAll(_botLabel, _robot.SymbolName);
            double curBuy = 0.0, curSell = 0.0;
            for (int i = 0; i < positions.Length; i++)
            {
                if (positions[i].TradeType == TradeType.Buy) curBuy += positions[i].VolumeInUnits;
                else curSell += positions[i].VolumeInUnits;
            }
            double curNet = curBuy - curSell;

            // Close opposite positions first
            if (targetNet <= 0.0 && curBuy > 0.0)
            {
                ClosePositionsBySide(positions, TradeType.Buy, curBuy);
                curBuy = 0.0;
            }
            else if (targetNet >= 0.0 && curSell > 0.0)
            {
                ClosePositionsBySide(positions, TradeType.Sell, curSell);
                curSell = 0.0;
            }

            curNet = curBuy - curSell;
            double delta = targetNet - curNet;
            double step = _robot.Symbol.VolumeInUnitsStep > 0.0 ? _robot.Symbol.VolumeInUnitsStep : 0.01;
            double minU = _robot.Symbol.VolumeInUnitsMin > 0.0 ? _robot.Symbol.VolumeInUnitsMin : 0.01;

            if (Math.Abs(delta) >= Math.Min(step, minU) * 0.5)
            {
                if (targetNet == 0.0)
                {
                    if (curBuy > 0.0) ClosePositionsBySide(positions, TradeType.Buy, curBuy);
                    if (curSell > 0.0) ClosePositionsBySide(positions, TradeType.Sell, curSell);
                }
                else if (delta > 0.0)
                {
                    if (curSell > 0.0)
                    {
                        double toClose = Math.Min(curSell, delta);
                        ClosePositionsBySide(positions, TradeType.Sell, toClose);
                    }
                    else
                    {
                        double addU = _robot.Symbol.NormalizeVolumeInUnits(delta, RoundingMode.ToNearest);
                        if (addU >= minU)
                            _robot.ExecuteMarketOrder(TradeType.Buy, _robot.SymbolName, addU, _botLabel);
                    }
                }
                else
                {
                    if (curBuy > 0.0)
                    {
                        double toClose = Math.Min(curBuy, -delta);
                        ClosePositionsBySide(positions, TradeType.Buy, toClose);
                    }
                    else
                    {
                        double addU = _robot.Symbol.NormalizeVolumeInUnits(-delta, RoundingMode.ToNearest);
                        if (addU >= minU)
                            _robot.ExecuteMarketOrder(TradeType.Sell, _robot.SymbolName, addU, _botLabel);
                    }
                }
            }

            if (_useBrokerProtectiveStop && Math.Abs(targetNet) >= minU)
                SyncBrokerProtectiveStop();

            _lastBrokerNetUnits = GetCurrentBrokerNetUnits();
        }

        private void ClosePositionsBySide(Position[] positions, TradeType side, double volumeToClose)
        {
            double rem = volumeToClose;
            double minU = _robot.Symbol.VolumeInUnitsMin > 0.0 ? _robot.Symbol.VolumeInUnitsMin : 0.01;
            for (int i = 0; i < positions.Length && rem >= minU * 0.5; i++)
            {
                Position pos = positions[i];
                if (pos.TradeType != side) continue;
                if (rem >= pos.VolumeInUnits - minU * 0.5)
                {
                    _robot.ClosePosition(pos);
                    rem -= pos.VolumeInUnits;
                }
                else
                {
                    double part = _robot.Symbol.NormalizeVolumeInUnits(rem, RoundingMode.Down);
                    if (part >= minU)
                    {
                        if (pos.VolumeInUnits - part < minU)
                            _robot.ClosePosition(pos);
                        else
                            _robot.ClosePosition(pos, part);
                    }
                    rem = 0.0;
                }
            }
        }

        private void SyncBrokerProtectiveStop()
        {
            double rawStop = _coord.GetProtectiveNetStopPrice();
            if (double.IsNaN(rawStop)) return;

            double slPx = Math.Round(rawStop, _robot.Symbol.Digits);
            double minDist = _robot.Symbol.MinStopLossDistance;
            Position[] active = _robot.Positions.FindAll(_botLabel, _robot.SymbolName);
            for (int i = 0; i < active.Length; i++)
            {
                Position p = active[i];
                bool distOk = p.TradeType == TradeType.Buy
                    ? (_robot.Symbol.Bid - slPx > minDist + _robot.Symbol.TickSize)
                    : (slPx - _robot.Symbol.Ask > minDist + _robot.Symbol.TickSize);
                if (!distOk) continue;
                if (!p.StopLoss.HasValue || Math.Abs(p.StopLoss.Value - slPx) > _robot.Symbol.TickSize * 2.0)
                    _robot.ModifyPosition(p, slPx, p.TakeProfit);
            }
        }

        private double NormalizeSignedVolume(double signedVol)
        {
            double minU = _robot.Symbol.VolumeInUnitsMin > 0.0 ? _robot.Symbol.VolumeInUnitsMin : 0.01;
            if (Math.Abs(signedVol) < minU * 0.5) return 0.0;
            double absNorm = _robot.Symbol.NormalizeVolumeInUnits(Math.Abs(signedVol), RoundingMode.ToNearest);
            if (absNorm < minU) return 0.0;
            return signedVol < 0.0 ? -absNorm : absNorm;
        }

        private void RenderHud()
        {
            if (_robot.IsBacktesting && !_showHudInBacktest) return;
            try
            {
                string hud = _coord.BuildHudText(_botLabel);
                _robot.Chart.DrawStaticText("EdgeLabFundedSyncHud", hud, VerticalAlignment.Bottom, HorizontalAlignment.Left, Color.Cyan);
            }
            catch
            {
            }
        }
    }
}
