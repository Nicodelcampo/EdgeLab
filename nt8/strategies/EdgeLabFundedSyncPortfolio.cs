#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Diagnostics;
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
        private sealed class PendingExecMeta
        {
            public long SubmitTimestamp;
            public DateTime SubmitUtc;
            public DateTime BarCloseUtc;
            public double BarDelayMs;
            public string OrderName;
            public int Side;
            public int QtyReq;
            public double SignalPx;
            public double BidAtSignal;
            public double AskAtSignal;
            public double TickSize;
            public double PointValue;
            public string InstrumentName;
            public string SessionWindow;
            public double AckMs = double.NaN;
            public int LoggedFilled;
            public bool TerminalLogged;
        }

        private readonly Strategy _strat;
        private readonly PortfolioCoordinator _coord;
        private readonly string _label;
        private readonly bool _hasSecondaryMnq;
        private TimeZoneInfo _chartTz;
        private TimeZoneInfo _nyTz;
        private TimeZoneInfo _ctTz;

        private readonly bool _enableExecAuditLog;
        private readonly string _execAuditPath;
        private bool _execAuditHeaderWritten;
        private readonly object _auditLock = new object();
        private readonly Dictionary<string, PendingExecMeta> _orderById = new Dictionary<string, PendingExecMeta>();
        private readonly Dictionary<string, Queue<PendingExecMeta>> _pendingByName = new Dictionary<string, Queue<PendingExecMeta>>();
        private static readonly double TickMs = 1000.0 / Stopwatch.Frequency;

        private DateTime _lastBarCloseUtc = DateTime.MinValue;
        private double _lastBarDelayMs = double.NaN;

        public FundedSyncNt8Adapter(
            Strategy strat,
            PortfolioCoordinator coord,
            string label,
            bool hasSecondaryMnq,
            bool enableCsvLog,
            string csvFileName,
            bool enableExecAuditLog = true,
            string execAuditFileName = "")
        {
            _strat = strat;
            _coord = coord;
            _label = label;
            _hasSecondaryMnq = hasSecondaryMnq;
            _enableExecAuditLog = enableExecAuditLog;

            _nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time");
            _ctTz = FundedSyncMath.ResolveTz("Central Standard Time");
            // In NT8, Time[0] is always in Core.Globals.GeneralOptions.TimeZoneInfo (user/display timezone),
            // never in Bars.TradingHours.TimeZoneInfo (exchange market timezone, e.g. Central Time).
            _chartTz = Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;

            double tick = (strat.Instrument != null && strat.Instrument.MasterInstrument != null && strat.Instrument.MasterInstrument.TickSize > 0)
                ? strat.Instrument.MasterInstrument.TickSize
                : 0.25;
            _coord.TickSize = tick;
            _coord.EnableCsvLog = enableCsvLog;
            string fname = string.IsNullOrWhiteSpace(csvFileName) ? "EdgeLab_FundedSync_ParityTrades.csv" : csvFileName.Trim();
            _coord.CsvLogPath = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, fname);

            string auditDir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "exec_audit");
            string acctName = strat.Account != null ? SanitizeToken(strat.Account.Name) : "UnknownAcct";
            string instName = strat.Instrument != null ? SanitizeToken(strat.Instrument.FullName) : "UnknownInst";
            string defaultAudit = string.Format(CultureInfo.InvariantCulture,
                "EdgeLab_LiveExecution_Audit_{0}_{1}_{2:yyyyMMdd}.csv", acctName, instName, DateTime.Now);
            string auditFile = string.IsNullOrWhiteSpace(execAuditFileName) ? defaultAudit : execAuditFileName.Trim();
            _execAuditPath = Path.IsPathRooted(auditFile) ? auditFile : Path.Combine(auditDir, auditFile);
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
            double[] weightOverrides,
            double rOscMult = 3.0, int rEndEt = 660, double rSlAtr = 0.50,
            int zBucketMin = 15, int zEmaPeriod = 20, double zMinEffPct = 40.0, double zSlAtr = 0.50,
            double tStopOrbMult = 1.0, double tBeTrigR = 1.5,
            double vNoiseMult = 0.25, double vSlAtr = 0.30,
            double wSlAtr = 0.25, int nDays = 5, double nSlAtr = 0.25,
            double tStopMinPts = 2.0, double tStopMaxPts = 100.0,
            double vTpPts = 0.0, bool wUseSlopeFilter = true, double nAcceptBufPts = 4.0,
            bool enableExecAuditLog = true, string execAuditFileName = "")
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
            double maxOpenREff = maxOpenR;
            double microPv = 2.0;
            double fricMini = 1.545;

            if (preset == FundedSyncPortfolioPreset.Core5_R25)
            {
                rSlAtr = 0.25;
            }
            else if (preset == FundedSyncPortfolioPreset.SpeedEval_TOnly)
            {
                maxOpenREff = Math.Min(maxOpenREff, 1.5);
            }
            else if (preset == FundedSyncPortfolioPreset.ES_Core_US500)
            {
                rOscMult = 2.0; rEndEt = 660; rSlAtr = 0.50;
                zBucketMin = 15; zEmaPeriod = 20; zMinEffPct = 35.0; zSlAtr = 0.50;
                tStopOrbMult = 1.0; tBeTrigR = 0.0; tStopMinPts = 0.6; tStopMaxPts = 29.0;
                vNoiseMult = 0.30; vSlAtr = 0.35; vTpPts = 15.7;
                wSlAtr = 0.35; wUseSlopeFilter = false; enableWTrail = false;
                nDays = 5; nSlAtr = 0.25; nAcceptBufPts = 0.9;
                maxOpenREff = Math.Min(maxOpenREff, 1.5);
                microPv = 5.0;
                fricMini = 0.55;
            }

            if (propProfile == FundedSyncPropProfile.LucidFlex_25K_Rescate)
                maxOpenREff = Math.Min(maxOpenREff, 1.0);

            double resolvedEvalRisk = useProfile ? prof.EvalRisk1R : evalRisk1R;
            double resolvedFundedRisk = useProfile ? prof.FundedRisk1R : fundedRisk1R;
            if (propProfile == FundedSyncPropProfile.LucidFlex_25K_Rescate && preset == FundedSyncPortfolioPreset.ES_Core_US500)
            {
                resolvedEvalRisk = prof.EvalRisk1R * 6.0;
                resolvedFundedRisk = prof.FundedRisk1R * 6.0;
            }

            var coord = new PortfolioCoordinator(
                weights, flags, enableWTrail: enableWTrail,
                rOscMult: rOscMult, rEndEt: rEndEt, rSlAtr: rSlAtr,
                zBucketMin: zBucketMin, zEmaPeriod: zEmaPeriod, zMinEffPct: zMinEffPct, zSlAtr: zSlAtr,
                tStopOrbMult: tStopOrbMult, tBeTrigR: tBeTrigR,
                vNoiseMult: vNoiseMult, vSlAtr: vSlAtr,
                wSlAtr: wSlAtr, nDays: nDays, nSlAtr: nSlAtr,
                tStopMinPts: tStopMinPts, tStopMaxPts: tStopMaxPts,
                vTpPts: vTpPts, wUseSlopeFilter: wUseSlopeFilter, nAcceptBufPts: nAcceptBufPts)
            {
                MicroPointValue = microPv,
                FrictionMiniPts = fricMini,
                AccountMode = mode,
                EvalRisk1R_USD = resolvedEvalRisk,
                FundedRisk1R_USD = resolvedFundedRisk,
                MaxOpenR = maxOpenREff,
                MaxMicroContracts = useProfile ? prof.MaxMicros : maxMicros,
                CollisionPolicy = useProfile ? prof.CollisionPolicy : collisionPolicy,
                HardFlattenHHMM_ET = useProfile ? prof.HardFlattenHHMM_ET : hardFlattenHhmmEt,
                EnforceEvalDailyCap = useProfile ? prof.EnforceEvalDailyCap : enforceEvalCap,
                EvalDailyCapUSD = useProfile ? prof.EvalDailyCapUsd : evalCapUsd,
                DailyLossLimitUSD = useProfile ? prof.DailyLossLimitUsd : dailyLossUsd
            };

            bool hasSec = !string.IsNullOrWhiteSpace(secondaryMnqSymbol);
            return new FundedSyncNt8Adapter(strat, coord, label, hasSec, enableCsvLog, csvFileName, enableExecAuditLog, execAuditFileName);
        }

        public void OnBarUpdate()
        {
            if (_strat.BarsInProgress != 0 || _strat.CurrentBar < 1)
                return;

            DateTime chartLocal = DateTime.SpecifyKind(_strat.Time[0], DateTimeKind.Unspecified);
            DateTime closeUtc = _chartTz.Id == TimeZoneInfo.Utc.Id
                ? DateTime.SpecifyKind(chartLocal, DateTimeKind.Utc)
                : TimeZoneInfo.ConvertTimeToUtc(chartLocal, _chartTz);
            _lastBarCloseUtc = closeUtc;
            _lastBarDelayMs = _strat.State == State.Realtime ? (DateTime.UtcNow - closeUtc).TotalMilliseconds : double.NaN;

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
                DispatchManagedOrder(bip, tagPrefix + "_FL", -1, curQty, () => _strat.ExitLong(bip, curQty, tagPrefix + "_FL", tagPrefix + "_L"));
                if (targetSignedQty < 0)
                    DispatchManagedOrder(bip, tagPrefix + "_S", -1, Math.Abs(targetSignedQty), () => _strat.EnterShort(bip, Math.Abs(targetSignedQty), tagPrefix + "_S"));
            }
            else if (curQty < 0 && targetSignedQty >= 0)
            {
                DispatchManagedOrder(bip, tagPrefix + "_FL", +1, Math.Abs(curQty), () => _strat.ExitShort(bip, Math.Abs(curQty), tagPrefix + "_FL", tagPrefix + "_S"));
                if (targetSignedQty > 0)
                    DispatchManagedOrder(bip, tagPrefix + "_L", +1, targetSignedQty, () => _strat.EnterLong(bip, targetSignedQty, tagPrefix + "_L"));
            }
            else if (delta > 0)
            {
                if (curQty >= 0)
                    DispatchManagedOrder(bip, tagPrefix + "_L", +1, delta, () => _strat.EnterLong(bip, delta, tagPrefix + "_L"));
                else
                    DispatchManagedOrder(bip, tagPrefix + "_TR", +1, delta, () => _strat.ExitShort(bip, delta, tagPrefix + "_TR", tagPrefix + "_S"));
            }
            else if (delta < 0)
            {
                if (curQty <= 0)
                    DispatchManagedOrder(bip, tagPrefix + "_S", -1, Math.Abs(delta), () => _strat.EnterShort(bip, Math.Abs(delta), tagPrefix + "_S"));
                else
                    DispatchManagedOrder(bip, tagPrefix + "_TR", -1, Math.Abs(delta), () => _strat.ExitLong(bip, Math.Abs(delta), tagPrefix + "_TR", tagPrefix + "_L"));
            }
        }

        private void DispatchManagedOrder(int bip, string orderName, int side, int qtyReq, Func<Order> submitCall)
        {
            if (_strat.State != State.Realtime || !_enableExecAuditLog)
            {
                submitCall();
                return;
            }

            PendingExecMeta meta = CreateSignalMeta(bip, orderName, side, qtyReq);
            lock (_auditLock)
            {
                Queue<PendingExecMeta> q;
                if (!_pendingByName.TryGetValue(orderName, out q))
                {
                    q = new Queue<PendingExecMeta>();
                    _pendingByName[orderName] = q;
                }
                q.Enqueue(meta);
            }

            Order ord = submitCall();
            if (ord != null && !string.IsNullOrEmpty(ord.OrderId))
            {
                lock (_auditLock)
                    _orderById[ord.OrderId] = meta;
            }
        }

        private PendingExecMeta CreateSignalMeta(int bip, string orderName, int side, int qtyReq)
        {
            double sigPx = double.NaN;
            try
            {
                sigPx = (_strat.Closes != null && bip < _strat.Closes.Length && _strat.Closes[bip].Count > 0)
                    ? _strat.Closes[bip][0]
                    : _strat.Close[0];
            }
            catch { sigPx = double.NaN; }

            double bid = double.NaN, ask = double.NaN;
            try { bid = _strat.GetCurrentBid(bip); if (bid <= 0) bid = double.NaN; } catch { bid = double.NaN; }
            try { ask = _strat.GetCurrentAsk(bip); if (ask <= 0) ask = double.NaN; } catch { ask = double.NaN; }

            Instrument inst = null;
            try
            {
                inst = (_strat.BarsArray != null && bip < _strat.BarsArray.Length && _strat.BarsArray[bip] != null)
                    ? _strat.BarsArray[bip].Instrument
                    : _strat.Instrument;
            }
            catch { inst = _strat.Instrument; }

            double tick = (inst != null && inst.MasterInstrument != null && inst.MasterInstrument.TickSize > 0) ? inst.MasterInstrument.TickSize : _coord.TickSize;
            double pv = (inst != null && inst.MasterInstrument != null && inst.MasterInstrument.PointValue > 0) ? inst.MasterInstrument.PointValue : _coord.MicroPointValue;
            string instName = inst != null ? inst.FullName : "UNKNOWN";

            DateTime refUtc = _lastBarCloseUtc != DateTime.MinValue ? _lastBarCloseUtc : DateTime.UtcNow;
            DateTime refNy = TimeZoneInfo.ConvertTimeFromUtc(refUtc, _nyTz);
            int hhmm = refNy.Hour * 100 + refNy.Minute;
            string win = (hhmm >= 930 && hhmm < 1000) ? "OPEN_0930_1000"
                : (hhmm >= 1000 && hhmm < 1600) ? "RTH_1000_1600"
                : (hhmm >= 1600 && hhmm < 1645) ? "CLOSE_1600_1645"
                : "ETH_OVERNIGHT";

            return new PendingExecMeta
            {
                SubmitTimestamp = Stopwatch.GetTimestamp(),
                SubmitUtc = DateTime.UtcNow,
                BarCloseUtc = _lastBarCloseUtc,
                BarDelayMs = _lastBarDelayMs,
                OrderName = orderName ?? "",
                Side = side,
                QtyReq = qtyReq,
                SignalPx = sigPx,
                BidAtSignal = bid,
                AskAtSignal = ask,
                TickSize = tick,
                PointValue = pv,
                InstrumentName = instName,
                SessionWindow = win
            };
        }

        private PendingExecMeta ResolveMetaForOrder(Order order)
        {
            if (order == null) return null;
            lock (_auditLock)
            {
                PendingExecMeta meta;
                if (!string.IsNullOrEmpty(order.OrderId) && _orderById.TryGetValue(order.OrderId, out meta))
                    return meta;

                string name = order.Name ?? "";
                Queue<PendingExecMeta> q;
                if (_pendingByName.TryGetValue(name, out q) && q.Count > 0)
                {
                    meta = q.Dequeue();
                    if (!string.IsNullOrEmpty(order.OrderId))
                        _orderById[order.OrderId] = meta;
                    return meta;
                }
            }
            return null;
        }

        public void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
            double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            if (_strat.State != State.Realtime || !_enableExecAuditLog || order == null)
                return;

            PendingExecMeta meta = ResolveMetaForOrder(order);
            if (meta == null)
                return;

            double elapsedMs = (Stopwatch.GetTimestamp() - meta.SubmitTimestamp) * TickMs;
            if ((orderState == OrderState.Submitted || orderState == OrderState.Accepted || orderState == OrderState.Working) && double.IsNaN(meta.AckMs))
                meta.AckMs = elapsedMs;

            bool isReject = orderState == OrderState.Rejected || error != ErrorCode.NoError;
            bool isCancel = orderState == OrderState.Cancelled && filled == 0;
            if ((isReject || isCancel) && !meta.TerminalLogged)
            {
                meta.TerminalLogged = true;
                string kind = orderState == OrderState.Rejected ? "REJECTED" : (isCancel ? "CANCELLED" : "ORDER_ERROR");
                WriteExecAuditRow(meta, kind, order, filled, averageFillPrice, elapsedMs, double.NaN, error.ToString(), comment ?? "");
                if (!string.IsNullOrEmpty(order.OrderId))
                {
                    lock (_auditLock) { _orderById.Remove(order.OrderId); }
                }
            }
        }

        public void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (_strat.State != State.Realtime || !_enableExecAuditLog || execution == null || execution.Order == null)
                return;

            Order ord = execution.Order;
            PendingExecMeta meta = ResolveMetaForOrder(ord);
            if (meta == null)
            {
                int sideGuess = (ord.OrderAction == OrderAction.Buy || ord.OrderAction == OrderAction.BuyToCover) ? +1 : -1;
                meta = CreateSignalMeta(0, ord.Name ?? "", sideGuess, ord.Quantity);
                meta.SignalPx = double.NaN;
                meta.SubmitTimestamp = 0;
            }

            double fillMs = meta.SubmitTimestamp > 0 ? (Stopwatch.GetTimestamp() - meta.SubmitTimestamp) * TickMs : double.NaN;
            meta.LoggedFilled += quantity;
            string kind = ord.OrderState == OrderState.PartFilled || meta.LoggedFilled < ord.Quantity ? "PART_FILL" : "FILL";
            double comm = execution.Commission + execution.Fee;
            WriteExecAuditRow(meta, kind, ord, quantity, price, fillMs, comm, ErrorCode.NoError.ToString(), executionId ?? "");

            if (kind == "FILL" && !string.IsNullOrEmpty(ord.OrderId))
            {
                lock (_auditLock) { _orderById.Remove(ord.OrderId); }
            }
        }

        private void WriteExecAuditRow(PendingExecMeta meta, string eventKind, Order ord, int qtyFilled,
            double fillPx, double fillMs, double commissionUsd, string errorCode, string comment)
        {
            try
            {
                var ci = CultureInfo.InvariantCulture;
                string acct = _strat.Account != null ? _strat.Account.Name : "";
                string conn = (_strat.Account != null && _strat.Account.Connection != null && _strat.Account.Connection.Options != null)
                    ? _strat.Account.Connection.Options.Name : "";

                double tick = meta.TickSize > 0 ? meta.TickSize : 0.25;
                double spreadPts = (!double.IsNaN(meta.BidAtSignal) && !double.IsNaN(meta.AskAtSignal))
                    ? (meta.AskAtSignal - meta.BidAtSignal) : double.NaN;
                double spreadTicks = !double.IsNaN(spreadPts) ? spreadPts / tick : double.NaN;
                double expectedTouch = meta.Side > 0 ? meta.AskAtSignal : meta.BidAtSignal;

                double slipClosePts = (!double.IsNaN(fillPx) && !double.IsNaN(meta.SignalPx))
                    ? (fillPx - meta.SignalPx) * meta.Side : double.NaN;
                double slipTouchPts = (!double.IsNaN(fillPx) && !double.IsNaN(expectedTouch))
                    ? (fillPx - expectedTouch) * meta.Side : double.NaN;
                double slipCloseTicks = !double.IsNaN(slipClosePts) ? slipClosePts / tick : double.NaN;
                double slipTouchTicks = !double.IsNaN(slipTouchPts) ? slipTouchPts / tick : double.NaN;

                string line = string.Join(",", new[]
                {
                    CsvSafe(DateTime.UtcNow.ToString("o", ci)),
                    CsvSafe(_strat.Name ?? "EdgeLabFundedSync"),
                    CsvSafe(acct),
                    CsvSafe(conn),
                    CsvSafe(meta.InstrumentName),
                    tick.ToString("G", ci),
                    meta.PointValue.ToString("G", ci),
                    CsvSafe(meta.SessionWindow),
                    CsvSafe(eventKind),
                    CsvSafe(ord != null ? ord.Name : meta.OrderName),
                    CsvSafe(ord != null ? ord.OrderId : ""),
                    meta.Side.ToString(ci),
                    meta.QtyReq.ToString(ci),
                    qtyFilled.ToString(ci),
                    CsvSafe(ord != null ? ord.OrderType.ToString() : ""),
                    CsvSafe(ord != null ? ord.OrderState.ToString() : ""),
                    CsvSafe(meta.BarCloseUtc != DateTime.MinValue ? meta.BarCloseUtc.ToString("o", ci) : ""),
                    FmtNum(meta.BarDelayMs, "F2", ci),
                    FmtNum(meta.AckMs, "F2", ci),
                    FmtNum(eventKind == "FILL" || eventKind == "PART_FILL" ? fillMs : double.NaN, "F2", ci),
                    FmtNum(meta.SignalPx, "F4", ci),
                    FmtNum(meta.BidAtSignal, "F4", ci),
                    FmtNum(meta.AskAtSignal, "F4", ci),
                    FmtNum(spreadPts, "F4", ci),
                    FmtNum(spreadTicks, "F2", ci),
                    FmtNum(expectedTouch, "F4", ci),
                    FmtNum(fillPx, "F4", ci),
                    FmtNum(slipClosePts, "F4", ci),
                    FmtNum(slipTouchPts, "F4", ci),
                    FmtNum(slipCloseTicks, "F2", ci),
                    FmtNum(slipTouchTicks, "F2", ci),
                    FmtNum(commissionUsd, "F4", ci),
                    CsvSafe(errorCode),
                    CsvSafe(comment)
                });

                lock (_auditLock)
                {
                    if (!_execAuditHeaderWritten)
                    {
                        string dir = Path.GetDirectoryName(_execAuditPath);
                        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                        if (!File.Exists(_execAuditPath) || new FileInfo(_execAuditPath).Length == 0)
                        {
                            File.WriteAllText(_execAuditPath,
                                "utc_iso,strategy,account,connection,instrument,tick_size,point_value,session_window,event_kind,order_name,order_id,side,qty_req,qty_filled,order_type,order_state,bar_close_utc,bar_delay_ms,submit_to_ack_ms,submit_to_fill_ms,signal_px,bid_at_signal,ask_at_signal,spread_pts,spread_ticks,expected_touch_px,fill_px,slip_vs_close_pts,slip_vs_touch_pts,slip_vs_close_ticks,slip_vs_touch_ticks,commission_usd,error_code,comment" + Environment.NewLine,
                                Encoding.UTF8);
                        }
                        _execAuditHeaderWritten = true;
                    }
                    File.AppendAllText(_execAuditPath, line + Environment.NewLine, Encoding.UTF8);
                }
            }
            catch { }
        }

        private static string FmtNum(double val, string fmt, CultureInfo ci)
        {
            return (double.IsNaN(val) || double.IsInfinity(val)) ? "" : val.ToString(fmt, ci);
        }

        private static string CsvSafe(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace(",", ";").Replace("\r", " ").Replace("\n", " ");
        }

        private static string SanitizeToken(string s)
        {
            if (string.IsNullOrWhiteSpace(s)) return "UNK";
            var sb = new StringBuilder(s.Length);
            foreach (char c in s)
                sb.Append(char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_');
            return sb.ToString().Trim('_');
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
                RSlAtrK = 0.50;

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
                EnableExecAuditLog = true;
                ExecAuditFileName = "";
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
                    customW,
                    rSlAtr: RSlAtrK,
                    enableExecAuditLog: EnableExecAuditLog,
                    execAuditFileName: ExecAuditFileName);
                Print("EdgeLabFundedSyncPortfolio initialized. Preset=" + Preset + " Profile=" + PropProfile + " (>= 500 trading days M1 ETH required).");
            }
        }

        protected override void OnBarUpdate()
        {
            if (_adapter != null)
                _adapter.OnBarUpdate();
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
            double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            if (_adapter != null)
                _adapter.OnOrderUpdate(order, limitPrice, stopPrice, quantity, filled, averageFillPrice, orderState, time, error, comment);
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (_adapter != null)
                _adapter.OnExecutionUpdate(execution, executionId, price, quantity, marketPosition, orderId, time);
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
        [Range(20.0, 2500.0)]
        [Display(Name = "Eval Risk 1R USD (Custom)", Order = 4, GroupName = "01. Prop Account")]
        public double EvalRisk1R_USD { get; set; }

        [NinjaScriptProperty]
        [Range(20.0, 2500.0)]
        [Display(Name = "Funded Risk 1R USD (Custom)", Order = 5, GroupName = "01. Prop Account")]
        public double FundedRisk1R_USD { get; set; }

        [NinjaScriptProperty]
        [Range(0.15, 10.0)]
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

        [NinjaScriptProperty]
        [Range(0.05, 2.0)]
        [Display(Name = "R SL ATR K (0.25=R25, 0.50=Base)", Order = 15, GroupName = "02. Compliance")]
        public double RSlAtrK { get; set; }

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

        [NinjaScriptProperty]
        [Display(Name = "Enable Exec Audit CSV", Order = 50, GroupName = "05. Execution Audit")]
        public bool EnableExecAuditLog { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Exec Audit CSV File (Optional)", Order = 51, GroupName = "05. Execution Audit")]
        public string ExecAuditFileName { get; set; }
        #endregion
    }
}
