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
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public enum EdgeLabProbeMode
    {
        MarketOnBarClose = 0,
        PassiveLimitThenCross = 1,
        MonitorOnlyNoOrders = 2
    }

    /// <summary>
    /// Dedicated benchmark strategy to measure real-world broker execution quality on Demo/Eval:
    /// bar-close processing delay, order ack &amp; fill latency, live spread, signed slippage vs signal Close[0]
    /// and vs live Bid/Ask touch, implied round-trip friction vs EdgeLab canonical, commissions, and rejects.
    ///
    /// Uses Calculate.OnBarClose on a 1-minute chart so it mirrors EdgeLabFundedSyncPortfolio execution mechanics,
    /// while subscribing to L1 bid/ask via OnMarketData for touch spread and Limit-then-Cross timeout handling.
    /// </summary>
    public class EdgeLabExecutionProbe : Strategy
    {
        private sealed class OrderMeta
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
            public string SessionWindow;
            public double AckMs = double.NaN;
            public int LoggedFilled;
            public bool TerminalLogged;
            public bool IsEntry;
        }

        private enum ProbePhase
        {
            Idle = 0,
            EnteringMarket = 1,
            EnteringLimit = 2,
            CancelingLimitToCross = 3,
            Holding = 4,
            Exiting = 5,
            Stopped = 6
        }

        private static readonly double TickMs = 1000.0 / Stopwatch.Frequency;

        private TimeZoneInfo _chartTz;
        private TimeZoneInfo _nyTz;
        private string _auditPath;
        private bool _headerWritten;
        private readonly object _auditLock = new object();

        private double _liveBid = double.NaN;
        private double _liveAsk = double.NaN;
        private DateTime _lastQuoteUtc = DateTime.MinValue;

        private DateTime _lastBarCloseUtc = DateTime.MinValue;
        private double _lastBarDelayMs = double.NaN;
        private double _lastSignalPx = double.NaN;
        private string _lastSessionWin = "ETH_OVERNIGHT";

        private ProbePhase _phase = ProbePhase.Idle;
        private int _barCounter;
        private int _barsHeld;
        private int _roundTripsDone;
        private int _nextSide = 1;
        private int _activeSide = 1;
        private int _seqId;
        private string _activeSignal = "";
        private Order _activeOrder;
        private DateTime _limitDeadlineUtc = DateTime.MaxValue;
        private bool _crossPendingOnCancel;
        private bool _stopped;
        private string _stopReason = "";

        private double _realizedUsd;
        private double _entryFillPx = double.NaN;
        private int _rejectCount;
        private int _partFillCount;
        private double _totalCommUsd;

        private readonly Dictionary<string, OrderMeta> _metaById = new Dictionary<string, OrderMeta>();
        private readonly Dictionary<string, Queue<OrderMeta>> _pendingByName = new Dictionary<string, Queue<OrderMeta>>();

        private readonly List<double> _barDelays = new List<double>();
        private readonly List<double> _ackLats = new List<double>();
        private readonly List<double> _fillLats = new List<double>();
        private readonly List<double> _spreadTicks = new List<double>();
        private readonly List<double> _slipClosePts = new List<double>();
        private readonly List<double> _slipTouchPts = new List<double>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabExecutionProbe";
                Description = "Benchmark dedicado de latencia, bar delay, spread, slippage y friccion real (Demo/Eval).";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 60;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                IsInstantiatedOnEachOptimizationIteration = true;

                Mode = EdgeLabProbeMode.MarketOnBarClose;
                IntervalBars = 3;
                HoldBars = 1;
                LimitTimeoutSec = 15;
                AlternateSides = true;
                InitialSide = 1;

                LogBarHeartbeats = true;
                ExecAuditFileName = "";
                ShowHud = true;

                Quantity = 1;
                MaxRoundTrips = 15;
                MaxLossUsd = 60.0;
                AllowLiveAccount = false;
                OnlyRthWindow = false;
                AvoidCmeBreak = true;
            }
            else if (State == State.DataLoaded)
            {
                _nyTz = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                _chartTz = Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
                _nextSide = InitialSide >= 0 ? 1 : -1;

                string dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "exec_audit");
                string acctName = Account != null ? SanitizeToken(Account.Name) : "UnknownAcct";
                string instName = Instrument != null ? SanitizeToken(Instrument.FullName) : "UnknownInst";
                string defName = string.Format(CultureInfo.InvariantCulture,
                    "EdgeLab_LiveExecution_Audit_{0}_{1}_{2:yyyyMMdd}.csv", acctName, instName, DateTime.Now);
                string f = string.IsNullOrWhiteSpace(ExecAuditFileName) ? defName : ExecAuditFileName.Trim();
                _auditPath = Path.IsPathRooted(f) ? f : Path.Combine(dir, f);
            }
            else if (State == State.Realtime)
            {
                string acct = Account != null ? Account.Name : "";
                bool isDemoOrSim = IsAutoAllowedAccount(acct);
                if (!isDemoOrSim && !AllowLiveAccount)
                {
                    _stopped = true;
                    _phase = ProbePhase.Stopped;
                    _stopReason = "BLOCKED_LIVE_ACCT";
                    Print("EdgeLabExecutionProbe: cuenta '" + acct + "' no es Sim/Demo y AllowLiveAccount=false. Detenido.");
                }
                else
                {
                    Print("EdgeLabExecutionProbe activo en cuenta=" + acct + " modo=" + Mode + " inst=" + Instrument.FullName + " csv=" + _auditPath);
                }
            }
            else if (State == State.Terminated)
            {
                try
                {
                    if (_activeOrder != null && (_activeOrder.OrderState == OrderState.Working || _activeOrder.OrderState == OrderState.Accepted))
                        CancelOrder(_activeOrder);
                }
                catch { }
                Print(BuildSummaryLine());
            }
        }

        protected override void OnMarketData(MarketDataEventArgs e)
        {
            if (e.MarketDataType == MarketDataType.Bid)
            {
                _liveBid = e.Price;
                _lastQuoteUtc = DateTime.UtcNow;
            }
            else if (e.MarketDataType == MarketDataType.Ask)
            {
                _liveAsk = e.Price;
                _lastQuoteUtc = DateTime.UtcNow;
            }

            if (State != State.Realtime || _stopped)
                return;

            if (_phase == ProbePhase.EnteringLimit && _activeOrder != null && DateTime.UtcNow >= _limitDeadlineUtc)
            {
                _phase = ProbePhase.CancelingLimitToCross;
                _crossPendingOnCancel = true;
                CancelOrder(_activeOrder);
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 1)
                return;

            if (State != State.Realtime)
                return;

            DateTime chartLocal = DateTime.SpecifyKind(Time[0], DateTimeKind.Unspecified);
            DateTime barCloseUtc = _chartTz.Id == TimeZoneInfo.Utc.Id
                ? DateTime.SpecifyKind(chartLocal, DateTimeKind.Utc)
                : TimeZoneInfo.ConvertTimeToUtc(chartLocal, _chartTz);
            DateTime nowUtc = DateTime.UtcNow;
            double barDelayMs = (nowUtc - barCloseUtc).TotalMilliseconds;

            _lastBarCloseUtc = barCloseUtc;
            _lastBarDelayMs = barDelayMs;
            _lastSignalPx = Close[0];

            DateTime barNy = TimeZoneInfo.ConvertTimeFromUtc(barCloseUtc, _nyTz);
            int hhmm = barNy.Hour * 100 + barNy.Minute;
            _lastSessionWin = ClassifySession(hhmm);
            _barDelays.Add(barDelayMs);

            double bid = ValidQuote(_liveBid) ? _liveBid : SafeGetBid();
            double ask = ValidQuote(_liveAsk) ? _liveAsk : SafeGetAsk();
            if (ValidQuote(bid) && ValidQuote(ask) && ask >= bid && TickSize > 0)
                _spreadTicks.Add((ask - bid) / TickSize);

            if (LogBarHeartbeats)
                WriteHeartbeatRow(barCloseUtc, barDelayMs, Close[0], bid, ask, _lastSessionWin);

            // Check limit timeout on bar close too in case OnMarketData is quiet
            if (!_stopped && _phase == ProbePhase.EnteringLimit && _activeOrder != null && nowUtc >= _limitDeadlineUtc)
            {
                _phase = ProbePhase.CancelingLimitToCross;
                _crossPendingOnCancel = true;
                CancelOrder(_activeOrder);
            }

            // Risk stop check
            double openPnl = 0.0;
            if (Position.MarketPosition != MarketPosition.Flat)
                openPnl = Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);

            if (!_stopped && (_realizedUsd + openPnl) <= -MaxLossUsd)
            {
                _stopped = true;
                _stopReason = "MAX_LOSS_HIT";
                ForceFlatten();
                RenderHud(openPnl);
                return;
            }

            if (!_stopped && Mode != EdgeLabProbeMode.MonitorOnlyNoOrders)
            {
                // Safe CME break window 16:50..18:05 ET
                bool cmeBreak = AvoidCmeBreak && (hhmm >= 1650 && hhmm < 1805);
                bool outsideRth = OnlyRthWindow && (hhmm < 930 || hhmm >= 1600);

                if (_phase == ProbePhase.Holding)
                {
                    _barsHeld++;
                    if (_barsHeld >= HoldBars || cmeBreak || outsideRth)
                        SubmitExit();
                }
                else if (_phase == ProbePhase.Idle)
                {
                    if (_roundTripsDone >= MaxRoundTrips)
                    {
                        _stopped = true;
                        _stopReason = "MAX_ROUNDTRIPS_DONE";
                    }
                    else if (!cmeBreak && !outsideRth && Position.MarketPosition == MarketPosition.Flat)
                    {
                        _barCounter++;
                        if (_barCounter >= IntervalBars)
                        {
                            _barCounter = 0;
                            SubmitEntry(bid, ask);
                        }
                    }
                }
            }

            if (ShowHud)
                RenderHud(openPnl);
        }

        private void SubmitEntry(double bid, double ask)
        {
            _seqId++;
            _activeSide = _nextSide;
            if (AlternateSides)
                _nextSide = -_nextSide;
            _activeSignal = string.Format(CultureInfo.InvariantCulture, "PROBE_{0}_{1}", _seqId, _activeSide > 0 ? "L" : "S");
            _barsHeld = 0;

            bool useLimit = Mode == EdgeLabProbeMode.PassiveLimitThenCross && ValidQuote(bid) && ValidQuote(ask) && ask >= bid;
            if (useLimit)
            {
                double limitPx = Instrument.MasterInstrument.RoundToTickSize(_activeSide > 0 ? bid : ask);
                _phase = ProbePhase.EnteringLimit;
                _limitDeadlineUtc = DateTime.UtcNow.AddSeconds(LimitTimeoutSec);
                _crossPendingOnCancel = false;
                OrderMeta meta = BuildMeta(_activeSignal, _activeSide, Quantity, Close[0], bid, ask, true);
                EnqueueMeta(_activeSignal, meta);
                _activeOrder = _activeSide > 0
                    ? EnterLongLimit(0, true, Quantity, limitPx, _activeSignal)
                    : EnterShortLimit(0, true, Quantity, limitPx, _activeSignal);
                BindOrderId(_activeOrder, meta);
            }
            else
            {
                _phase = ProbePhase.EnteringMarket;
                OrderMeta meta = BuildMeta(_activeSignal, _activeSide, Quantity, Close[0], bid, ask, true);
                EnqueueMeta(_activeSignal, meta);
                _activeOrder = _activeSide > 0
                    ? EnterLong(Quantity, _activeSignal)
                    : EnterShort(Quantity, _activeSignal);
                BindOrderId(_activeOrder, meta);
            }
        }

        private void SubmitExit()
        {
            if (Position.MarketPosition == MarketPosition.Flat)
            {
                _phase = ProbePhase.Idle;
                return;
            }
            string exitSig = "X_" + _activeSignal;
            int exitSide = Position.MarketPosition == MarketPosition.Long ? -1 : 1;
            int qty = Math.Max(1, Position.Quantity);
            double bid = ValidQuote(_liveBid) ? _liveBid : SafeGetBid();
            double ask = ValidQuote(_liveAsk) ? _liveAsk : SafeGetAsk();

            _phase = ProbePhase.Exiting;
            OrderMeta meta = BuildMeta(exitSig, exitSide, qty, Close[0], bid, ask, false);
            EnqueueMeta(exitSig, meta);
            _activeOrder = Position.MarketPosition == MarketPosition.Long
                ? ExitLong(exitSig, _activeSignal)
                : ExitShort(exitSig, _activeSignal);
            BindOrderId(_activeOrder, meta);
        }

        private void ForceFlatten()
        {
            try
            {
                if (_activeOrder != null && (_activeOrder.OrderState == OrderState.Working || _activeOrder.OrderState == OrderState.Accepted))
                    CancelOrder(_activeOrder);
                if (Position.MarketPosition == MarketPosition.Long)
                    ExitLong("X_MAXLOSS", _activeSignal);
                else if (Position.MarketPosition == MarketPosition.Short)
                    ExitShort("X_MAXLOSS", _activeSignal);
            }
            catch { }
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
            double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            if (State != State.Realtime || order == null)
                return;

            OrderMeta meta = ResolveMeta(order);
            if (meta != null)
            {
                double elapsedMs = (Stopwatch.GetTimestamp() - meta.SubmitTimestamp) * TickMs;
                if ((orderState == OrderState.Submitted || orderState == OrderState.Accepted || orderState == OrderState.Working) && double.IsNaN(meta.AckMs))
                {
                    meta.AckMs = elapsedMs;
                    _ackLats.Add(elapsedMs);
                }

                if (orderState == OrderState.Rejected || error != ErrorCode.NoError)
                {
                    _rejectCount++;
                    if (!meta.TerminalLogged)
                    {
                        meta.TerminalLogged = true;
                        WriteExecRow(meta, "REJECTED", order, filled, averageFillPrice, elapsedMs, double.NaN, error.ToString(), comment ?? "");
                    }
                    if (order == _activeOrder)
                    {
                        _activeOrder = null;
                        _phase = Position.MarketPosition == MarketPosition.Flat ? (_stopped ? ProbePhase.Stopped : ProbePhase.Idle) : ProbePhase.Holding;
                    }
                    CleanupOrderId(order);
                    return;
                }

                if (orderState == OrderState.Cancelled && filled == 0)
                {
                    if (!meta.TerminalLogged)
                    {
                        meta.TerminalLogged = true;
                        WriteExecRow(meta, "CANCELLED", order, 0, double.NaN, elapsedMs, double.NaN, error.ToString(), comment ?? "");
                    }
                    CleanupOrderId(order);

                    if (_phase == ProbePhase.CancelingLimitToCross && _crossPendingOnCancel)
                    {
                        _crossPendingOnCancel = false;
                        _phase = ProbePhase.EnteringMarket;
                        double bid = ValidQuote(_liveBid) ? _liveBid : SafeGetBid();
                        double ask = ValidQuote(_liveAsk) ? _liveAsk : SafeGetAsk();
                        OrderMeta crossMeta = BuildMeta(_activeSignal, _activeSide, Quantity, Close[0], bid, ask, true);
                        EnqueueMeta(_activeSignal, crossMeta);
                        _activeOrder = _activeSide > 0
                            ? EnterLong(Quantity, _activeSignal)
                            : EnterShort(Quantity, _activeSignal);
                        BindOrderId(_activeOrder, crossMeta);
                    }
                    else if (order == _activeOrder)
                    {
                        _activeOrder = null;
                        if (!_stopped)
                            _phase = Position.MarketPosition == MarketPosition.Flat ? ProbePhase.Idle : ProbePhase.Holding;
                    }
                }
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (State != State.Realtime || execution == null || execution.Order == null)
                return;

            Order ord = execution.Order;
            OrderMeta meta = ResolveMeta(ord);
            if (meta == null)
            {
                int guessSide = (ord.OrderAction == OrderAction.Buy || ord.OrderAction == OrderAction.BuyToCover) ? 1 : -1;
                double b = ValidQuote(_liveBid) ? _liveBid : SafeGetBid();
                double a = ValidQuote(_liveAsk) ? _liveAsk : SafeGetAsk();
                meta = BuildMeta(ord.Name ?? "", guessSide, ord.Quantity, Close[0], b, a, _phase != ProbePhase.Exiting);
                meta.SubmitTimestamp = 0;
            }

            double fillMs = meta.SubmitTimestamp > 0 ? (Stopwatch.GetTimestamp() - meta.SubmitTimestamp) * TickMs : double.NaN;
            meta.LoggedFilled += quantity;
            bool isPartial = ord.OrderState == OrderState.PartFilled || meta.LoggedFilled < ord.Quantity;
            string kind = isPartial ? "PART_FILL" : "FILL";
            if (isPartial) _partFillCount++;

            double comm = execution.Commission + execution.Fee;
            _totalCommUsd += comm;

            if (!double.IsNaN(fillMs) && !isPartial)
                _fillLats.Add(fillMs);
            if (!double.IsNaN(meta.SignalPx))
                _slipClosePts.Add((price - meta.SignalPx) * meta.Side);
            double touch = meta.Side > 0 ? meta.AskAtSignal : meta.BidAtSignal;
            if (!double.IsNaN(touch))
                _slipTouchPts.Add((price - touch) * meta.Side);

            WriteExecRow(meta, kind, ord, quantity, price, fillMs, comm, ErrorCode.NoError.ToString(), executionId ?? "");

            if (!isPartial)
            {
                CleanupOrderId(ord);
                if (meta.IsEntry)
                {
                    _entryFillPx = price;
                    _phase = _stopped ? ProbePhase.Stopped : ProbePhase.Holding;
                    _barsHeld = 0;
                    _activeOrder = null;
                }
                else
                {
                    if (!double.IsNaN(_entryFillPx) && Instrument != null && Instrument.MasterInstrument != null)
                        _realizedUsd += (_activeSide * (price - _entryFillPx) * Instrument.MasterInstrument.PointValue * quantity) - comm;
                    _entryFillPx = double.NaN;
                    _roundTripsDone++;
                    _activeOrder = null;
                    _phase = _stopped ? ProbePhase.Stopped : ProbePhase.Idle;
                    if (_roundTripsDone >= MaxRoundTrips)
                    {
                        _stopped = true;
                        _stopReason = "MAX_ROUNDTRIPS_DONE";
                        _phase = ProbePhase.Stopped;
                    }
                }
            }

            if (ShowHud)
                RenderHud(0.0);
        }

        private OrderMeta BuildMeta(string name, int side, int qty, double signalPx, double bid, double ask, bool isEntry)
        {
            return new OrderMeta
            {
                SubmitTimestamp = Stopwatch.GetTimestamp(),
                SubmitUtc = DateTime.UtcNow,
                BarCloseUtc = _lastBarCloseUtc,
                BarDelayMs = _lastBarDelayMs,
                OrderName = name ?? "",
                Side = side,
                QtyReq = qty,
                SignalPx = signalPx,
                BidAtSignal = bid,
                AskAtSignal = ask,
                SessionWindow = _lastSessionWin,
                IsEntry = isEntry
            };
        }

        private void EnqueueMeta(string orderName, OrderMeta meta)
        {
            lock (_auditLock)
            {
                Queue<OrderMeta> q;
                if (!_pendingByName.TryGetValue(orderName, out q))
                {
                    q = new Queue<OrderMeta>();
                    _pendingByName[orderName] = q;
                }
                q.Enqueue(meta);
            }
        }

        private void BindOrderId(Order ord, OrderMeta meta)
        {
            if (ord != null && !string.IsNullOrEmpty(ord.OrderId))
            {
                lock (_auditLock)
                    _metaById[ord.OrderId] = meta;
            }
        }

        private OrderMeta ResolveMeta(Order ord)
        {
            if (ord == null) return null;
            lock (_auditLock)
            {
                OrderMeta m;
                if (!string.IsNullOrEmpty(ord.OrderId) && _metaById.TryGetValue(ord.OrderId, out m))
                    return m;

                string name = ord.Name ?? "";
                Queue<OrderMeta> q;
                if (_pendingByName.TryGetValue(name, out q) && q.Count > 0)
                {
                    m = q.Dequeue();
                    if (!string.IsNullOrEmpty(ord.OrderId))
                        _metaById[ord.OrderId] = m;
                    return m;
                }
            }
            return null;
        }

        private void CleanupOrderId(Order ord)
        {
            if (ord != null && !string.IsNullOrEmpty(ord.OrderId))
            {
                lock (_auditLock)
                    _metaById.Remove(ord.OrderId);
            }
        }

        private void WriteHeartbeatRow(DateTime barCloseUtc, double barDelayMs, double closePx, double bid, double ask, string sessionWin)
        {
            var meta = new OrderMeta
            {
                BarCloseUtc = barCloseUtc,
                BarDelayMs = barDelayMs,
                SignalPx = closePx,
                BidAtSignal = bid,
                AskAtSignal = ask,
                SessionWindow = sessionWin
            };
            WriteExecRow(meta, "BAR_HEARTBEAT", null, 0, double.NaN, double.NaN, double.NaN, "", "");
        }

        private void WriteExecRow(OrderMeta meta, string eventKind, Order ord, int qtyFilled, double fillPx,
            double fillMs, double commissionUsd, string errorCode, string comment)
        {
            try
            {
                var ci = CultureInfo.InvariantCulture;
                string acct = Account != null ? Account.Name : "";
                string conn = (Account != null && Account.Connection != null && Account.Connection.Options != null)
                    ? Account.Connection.Options.Name : "";
                string inst = Instrument != null ? Instrument.FullName : "";
                double tick = (Instrument != null && Instrument.MasterInstrument != null && Instrument.MasterInstrument.TickSize > 0)
                    ? Instrument.MasterInstrument.TickSize : 0.25;
                double pv = (Instrument != null && Instrument.MasterInstrument != null && Instrument.MasterInstrument.PointValue > 0)
                    ? Instrument.MasterInstrument.PointValue : 2.0;

                double spreadPts = (ValidQuote(meta.BidAtSignal) && ValidQuote(meta.AskAtSignal)) ? (meta.AskAtSignal - meta.BidAtSignal) : double.NaN;
                double spreadTicks = !double.IsNaN(spreadPts) ? spreadPts / tick : double.NaN;
                double expectedTouch = meta.Side > 0 ? meta.AskAtSignal : meta.BidAtSignal;

                double slipClosePts = (!double.IsNaN(fillPx) && !double.IsNaN(meta.SignalPx) && meta.Side != 0)
                    ? (fillPx - meta.SignalPx) * meta.Side : double.NaN;
                double slipTouchPts = (!double.IsNaN(fillPx) && !double.IsNaN(expectedTouch) && meta.Side != 0)
                    ? (fillPx - expectedTouch) * meta.Side : double.NaN;
                double slipCloseTicks = !double.IsNaN(slipClosePts) ? slipClosePts / tick : double.NaN;
                double slipTouchTicks = !double.IsNaN(slipTouchPts) ? slipTouchPts / tick : double.NaN;

                string line = string.Join(",", new[]
                {
                    CsvSafe(DateTime.UtcNow.ToString("o", ci)),
                    CsvSafe("EdgeLabExecutionProbe"),
                    CsvSafe(acct),
                    CsvSafe(conn),
                    CsvSafe(inst),
                    tick.ToString("G", ci),
                    pv.ToString("G", ci),
                    CsvSafe(meta.SessionWindow),
                    CsvSafe(eventKind),
                    CsvSafe(ord != null ? ord.Name : meta.OrderName),
                    CsvSafe(ord != null ? ord.OrderId : ""),
                    meta.Side != 0 ? meta.Side.ToString(ci) : "",
                    meta.QtyReq > 0 ? meta.QtyReq.ToString(ci) : "",
                    qtyFilled > 0 ? qtyFilled.ToString(ci) : "",
                    CsvSafe(ord != null ? ord.OrderType.ToString() : ""),
                    CsvSafe(ord != null ? ord.OrderState.ToString() : ""),
                    CsvSafe(meta.BarCloseUtc != DateTime.MinValue ? meta.BarCloseUtc.ToString("o", ci) : ""),
                    FmtNum(meta.BarDelayMs, "F2", ci),
                    FmtNum(meta.AckMs, "F2", ci),
                    FmtNum((eventKind == "FILL" || eventKind == "PART_FILL") ? fillMs : double.NaN, "F2", ci),
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
                    if (!_headerWritten)
                    {
                        string dir = Path.GetDirectoryName(_auditPath);
                        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                        if (!File.Exists(_auditPath) || new FileInfo(_auditPath).Length == 0)
                        {
                            File.WriteAllText(_auditPath,
                                "utc_iso,strategy,account,connection,instrument,tick_size,point_value,session_window,event_kind,order_name,order_id,side,qty_req,qty_filled,order_type,order_state,bar_close_utc,bar_delay_ms,submit_to_ack_ms,submit_to_fill_ms,signal_px,bid_at_signal,ask_at_signal,spread_pts,spread_ticks,expected_touch_px,fill_px,slip_vs_close_pts,slip_vs_touch_pts,slip_vs_close_ticks,slip_vs_touch_ticks,commission_usd,error_code,comment" + Environment.NewLine,
                                Encoding.UTF8);
                        }
                        _headerWritten = true;
                    }
                    File.AppendAllText(_auditPath, line + Environment.NewLine, Encoding.UTF8);
                }
            }
            catch { }
        }

        private void RenderHud(double openPnl)
        {
            try
            {
                var ci = CultureInfo.InvariantCulture;
                string acct = Account != null ? Account.Name : "";
                string acctType = IsLocalSim(acct) ? "LOCAL_SIM_WARN"
                    : (acct.IndexOf("demo", StringComparison.OrdinalIgnoreCase) >= 0 ? "BROKER_DEMO" : "LIVE_EVAL");

                double barMed = Percentile(_barDelays, 0.50);
                double barP90 = Percentile(_barDelays, 0.90);
                double fillMed = Percentile(_fillLats, 0.50);
                double fillP90 = Percentile(_fillLats, 0.90);
                double sprMean = Mean(_spreadTicks);
                double slipMean = Mean(_slipClosePts);
                double pv = (Instrument != null && Instrument.MasterInstrument != null && Instrument.MasterInstrument.PointValue > 0)
                    ? Instrument.MasterInstrument.PointValue : 2.0;
                int fillsCount = _fillLats.Count;
                double meanCommPts = (fillsCount > 0 && _totalCommUsd > 0) ? ((_totalCommUsd / fillsCount) / (pv * Math.Max(1, Quantity))) : 0.0;
                double impliedRtPts = !double.IsNaN(slipMean) ? (2.0 * slipMean + 2.0 * meanCommPts) : double.NaN;
                double canonRtPts = CanonicalRtPts();

                string badge = "OK";
                if (IsLocalSim(acct)) badge = "WARN_LOCAL_SIM";
                else if (_rejectCount > 0 || (!double.IsNaN(barP90) && barP90 > 500) || (!double.IsNaN(fillP90) && fillP90 > 600))
                    badge = "WARN_LATENCY";
                else if (!double.IsNaN(impliedRtPts) && canonRtPts > 0 && impliedRtPts > 1.30 * canonRtPts)
                    badge = "HIGH_FRICTION";

                string txt = string.Format(ci,
                    "EdgeLabExecProbe [{0}] | {1} ({2}) | RT={3}/{4} | PnL=${5:+0.0;-0.0;0.0} | Status={6}\n" +
                    "BarDelay med/p90={7}/{8} ms | FillLat med/p90={9}/{10} ms | Rej={11} Part={12}\n" +
                    "Spread={13} tks | SlipClose={14} pts | ImpliedRT={15} pts (Canon={16} pts){17}",
                    Mode, acct, acctType, _roundTripsDone, MaxRoundTrips, _realizedUsd + openPnl, badge,
                    FmtOrDash(barMed, "F0"), FmtOrDash(barP90, "F0"),
                    FmtOrDash(fillMed, "F0"), FmtOrDash(fillP90, "F0"),
                    _rejectCount, _partFillCount,
                    FmtOrDash(sprMean, "F2"), FmtOrDash(slipMean, "F3"),
                    FmtOrDash(impliedRtPts, "F3"), canonRtPts.ToString("F3", ci),
                    _stopped ? " | STOP=" + _stopReason : "");

                Draw.TextFixed(this, "EdgeLabExecutionProbeHud", txt, TextPosition.BottomLeft);
            }
            catch { }
        }

        private string BuildSummaryLine()
        {
            var ci = CultureInfo.InvariantCulture;
            return string.Format(ci,
                "EdgeLabExecutionProbe SUMMARY: Mode={0} Acct={1} Inst={2} RTs={3} Fills={4} Rejects={5} PartFills={6} BarDelayMed={7}ms FillLatMed={8}ms SpreadTicks={9} SlipClosePts={10} PnL=${11:F2}",
                Mode,
                Account != null ? Account.Name : "",
                Instrument != null ? Instrument.FullName : "",
                _roundTripsDone,
                _fillLats.Count,
                _rejectCount,
                _partFillCount,
                FmtOrDash(Percentile(_barDelays, 0.50), "F1"),
                FmtOrDash(Percentile(_fillLats, 0.50), "F1"),
                FmtOrDash(Mean(_spreadTicks), "F2"),
                FmtOrDash(Mean(_slipClosePts), "F4"),
                _realizedUsd);
        }

        private double CanonicalRtPts()
        {
            string master = (Instrument != null && Instrument.MasterInstrument != null) ? Instrument.MasterInstrument.Name.ToUpperInvariant() : "";
            if (master == "MNQ" || master == "NQ") return 1.5455;
            if (master == "MES" || master == "ES") return 0.8877;
            if (master == "MGC" || master == "GC") return 0.6050;
            return 1.00;
        }

        private double SafeGetBid()
        {
            try { double b = GetCurrentBid(); return b > 0 ? b : double.NaN; } catch { return double.NaN; }
        }

        private double SafeGetAsk()
        {
            try { double a = GetCurrentAsk(); return a > 0 ? a : double.NaN; } catch { return double.NaN; }
        }

        private static bool ValidQuote(double px) { return !double.IsNaN(px) && !double.IsInfinity(px) && px > 0.0; }

        private static bool IsLocalSim(string acct)
        {
            if (string.IsNullOrEmpty(acct)) return false;
            return acct.Equals("Sim101", StringComparison.OrdinalIgnoreCase) || acct.Equals("Playback101", StringComparison.OrdinalIgnoreCase);
        }

        private static bool IsAutoAllowedAccount(string acct)
        {
            if (string.IsNullOrEmpty(acct)) return false;
            return acct.StartsWith("Sim", StringComparison.OrdinalIgnoreCase)
                || acct.StartsWith("Playback", StringComparison.OrdinalIgnoreCase)
                || acct.StartsWith("DEMO", StringComparison.OrdinalIgnoreCase);
        }

        private static string ClassifySession(int hhmm)
        {
            if (hhmm >= 930 && hhmm < 1000) return "OPEN_0930_1000";
            if (hhmm >= 1000 && hhmm < 1600) return "RTH_1000_1600";
            if (hhmm >= 1600 && hhmm < 1645) return "CLOSE_1600_1645";
            return "ETH_OVERNIGHT";
        }

        private static double Mean(List<double> xs)
        {
            if (xs == null || xs.Count == 0) return double.NaN;
            double s = 0.0;
            for (int i = 0; i < xs.Count; i++) s += xs[i];
            return s / xs.Count;
        }

        private static double Percentile(List<double> xs, double q)
        {
            if (xs == null || xs.Count == 0) return double.NaN;
            var arr = new List<double>(xs);
            arr.Sort();
            double idx = Math.Max(0.0, Math.Min(arr.Count - 1, q * (arr.Count - 1)));
            int lo = (int)Math.Floor(idx);
            int hi = (int)Math.Ceiling(idx);
            if (lo == hi) return arr[lo];
            double frac = idx - lo;
            return arr[lo] * (1.0 - frac) + arr[hi] * frac;
        }

        private static string FmtOrDash(double v, string fmt)
        {
            return (double.IsNaN(v) || double.IsInfinity(v)) ? "-" : v.ToString(fmt, CultureInfo.InvariantCulture);
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

        #region NinjaScript Properties
        [NinjaScriptProperty]
        [Display(Name = "Probe Mode", Order = 1, GroupName = "01. Benchmark Mode")]
        public EdgeLabProbeMode Mode { get; set; }

        [NinjaScriptProperty, Range(1, 240)]
        [Display(Name = "Interval Bars (M1)", Order = 2, GroupName = "01. Benchmark Mode")]
        public int IntervalBars { get; set; }

        [NinjaScriptProperty, Range(1, 120)]
        [Display(Name = "Hold Bars (M1)", Order = 3, GroupName = "01. Benchmark Mode")]
        public int HoldBars { get; set; }

        [NinjaScriptProperty, Range(1, 120)]
        [Display(Name = "Limit Timeout Sec", Order = 4, GroupName = "01. Benchmark Mode")]
        public int LimitTimeoutSec { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Alternate Long/Short", Order = 5, GroupName = "01. Benchmark Mode")]
        public bool AlternateSides { get; set; }

        [NinjaScriptProperty, Range(-1, 1)]
        [Display(Name = "Initial Side (+1 Long, -1 Short)", Order = 6, GroupName = "01. Benchmark Mode")]
        public int InitialSide { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Log M1 Bar Heartbeats", Order = 10, GroupName = "02. Telemetry")]
        public bool LogBarHeartbeats { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Exec Audit CSV File (Optional)", Order = 11, GroupName = "02. Telemetry")]
        public string ExecAuditFileName { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Show On-Chart HUD", Order = 12, GroupName = "02. Telemetry")]
        public bool ShowHud { get; set; }

        [NinjaScriptProperty, Range(1, 5)]
        [Display(Name = "Contracts Quantity", Order = 20, GroupName = "03. Safety Guardrails")]
        public int Quantity { get; set; }

        [NinjaScriptProperty, Range(1, 200)]
        [Display(Name = "Max RoundTrips", Order = 21, GroupName = "03. Safety Guardrails")]
        public int MaxRoundTrips { get; set; }

        [NinjaScriptProperty, Range(5.0, 500.0)]
        [Display(Name = "Max Loss USD", Order = 22, GroupName = "03. Safety Guardrails")]
        public double MaxLossUsd { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Non-Sim/Demo Account", Order = 23, GroupName = "03. Safety Guardrails")]
        public bool AllowLiveAccount { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Only RTH 09:30-16:00 ET", Order = 24, GroupName = "03. Safety Guardrails")]
        public bool OnlyRthWindow { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Avoid CME Break 16:50-18:05 ET", Order = 25, GroupName = "03. Safety Guardrails")]
        public bool AvoidCmeBreak { get; set; }
        #endregion
    }
}
