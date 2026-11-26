#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    using EdgeLabFundedSync;

    public enum CarteraPreset { Intradia = 0, Interdia = 1, Rescate25K = 2, Personalizada = 3 }

    /// <summary>
    /// EdgeLabCartera (2026-11-25): UNA estrategia NT8 con varias estrategias EdgeLab en uno o mas instrumentos.
    /// Cada estrategia tiene sus ordenes reales (entrada, stop y objetivo OCO, salida a mercado) y la cuenta queda con la
    /// posicion neta. Presets:
    ///   Intradia   : MNQ T,R,Z,V,RQ5,Franklin + MES RQ5,ES5N (1 micro c/u), plano 16:40 ET y 20 min antes del fin de sesion.
    ///   Interdia   : MNQ SOM sin_finde, C2_VZ + MES C2_VZ (1 micro c/u), mantiene de noche (cuentas que lo permiten).
    ///   Rescate25K : MNQ T (1 micro): perdida maxima por dia ~$200 < colchon de la 25K; registro de ejecucion completo.
    ///                (docs/research/cartera_nt8_20261125/RESULTADO.md: el freno diario y mas estrategias BAJAN la probabilidad)
    /// Composicion editable: "MNQ:T=1,R=1;MES:RQ5=1" (codigos: T R Z V W N SOMEOD SOM RQ5 FR FRV ES5N C2VZ C2EVRP).
    /// Historico de una corrida en vivo: simulacion virtual (sin ordenes) y arranque plano en tiempo real. Strategy
    /// Analyzer (cuenta Backtest): ordenes reales de NT8 desde la primera vela.
    /// </summary>
    public class EdgeLabCartera : Strategy, ICarteraGateway
    {
        private readonly List<CarteraBook> _books = new List<CarteraBook>();
        private readonly Dictionary<int, CarteraBook> _byBip = new Dictionary<int, CarteraBook>();
        private readonly Dictionary<string, Order> _orders = new Dictionary<string, Order>();
        private readonly Dictionary<string, AuditMeta> _audit = new Dictionary<string, AuditMeta>();
        private readonly Dictionary<int, SessionIterator> _sessIt = new Dictionary<int, SessionIterator>();
        private List<KeyValuePair<string, List<KeyValuePair<string, int>>>> _comp;
        private TimeZoneInfo _chartTz, _nyTz, _ctTz;
        private NewsVetoCalendar _newsCal;
        private bool _blocked, _haltedTotal, _brokerHist;
        private double _realizedTotalUsd;
        private int _dayKey = -1;
        private bool _dayBlocked;
        private string _auditPath, _dir;
        // diagnostico (2026-11-25): contadores por mes para encontrar el consumo de memoria/tiempo en el Strategy Analyzer
        private long _nBars, _nSub, _nChg, _nCan, _nFill, _nRej, _nUpd;
        private int _mesDiag = -1, _descuadres;
        private static bool Coord_Broker(CarteraBook bk) { return bk.Coord.BrokerDriven; }

        private sealed class AuditMeta { public DateTime SubmitUtc; public double RefPx; public int Side; public string Book, Sleeve, Role; public double Tick, Pv; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabCartera";
                Description = "EdgeLab: varias estrategias en una, ordenes reales por estrategia (entrada, stop/objetivo OCO), veto de noticias y guardas de cuenta.";
                Calculate = Calculate.OnBarClose;
                IsUnmanaged = true;
                IgnoreOverfill = true;
                IsExitOnSessionCloseStrategy = false;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.IgnoreAllErrors;   // los rechazos los maneja CarteraBook
                TimeInForce = TimeInForce.Gtc;
                BarsRequiredToTrade = 1;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                Slippage = 0;
                Preset = CarteraPreset.Intradia;
                Composicion = "";
                InstrumentosSecundarios = "";
                PerdidaDiariaMaxUSD = 0.0;
                PerdidaTotalMaxUSD = 0.0;
                ObjetivoDiarioUSD = 0.0;
                HardFlattenHHMM_ET = 1640;
                MinAntesFinSesion = 20;
                EnableNewsVeto = true;
                NewsBeforeMin = 2.0; NewsAfterMin = 2.0; FomcBeforeMin = 5.0; FomcAfterMin = 5.0;
                VolCsvPath = "";
                EnableCsvLog = true;
                EnableExecAudit = true;
                Diagnostico = true;
            }
            else if (State == State.Configure)
            {
                _comp = ParseComposicion(string.IsNullOrWhiteSpace(Composicion) ? DefaultComposicion(Preset) : Composicion);
                var sec = ParseSecundarios(InstrumentosSecundarios);
                for (int i = 1; i < _comp.Count; i++)
                {
                    string root = _comp[i].Key;
                    string name;
                    if (!sec.TryGetValue(root, out name))
                        name = root + " " + (Instrument != null ? Instrument.Expiry.ToString("MM-yy", CultureInfo.InvariantCulture) : "");
                    AddDataSeries(name, BarsPeriodType.Minute, 1);
                }
            }
            else if (State == State.DataLoaded)
            {
                _nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time");
                _ctTz = FundedSyncMath.ResolveTz("Central Standard Time");
                _chartTz = Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
                string master = (Instrument != null && Instrument.MasterInstrument != null) ? Instrument.MasterInstrument.Name : "";
                if (_comp.Count == 0 || !string.Equals(master, _comp[0].Key, StringComparison.OrdinalIgnoreCase))
                {
                    _blocked = true;
                    Print("EdgeLabCartera BLOQUEADA: el grafico es " + master + " y la composicion empieza por " + (_comp.Count > 0 ? _comp[0].Key : "(vacia)") + ".");
                    return;
                }
                _brokerHist = Account != null && (Account.Name ?? "").StartsWith("Backtest", StringComparison.OrdinalIgnoreCase);
                _dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "cartera");
                Directory.CreateDirectory(_dir);
                _auditPath = Path.Combine(_dir, "exec_audit_" + Preset + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss", CultureInfo.InvariantCulture) + ".csv");
                if (EnableNewsVeto)
                {
                    _newsCal = new NewsVetoCalendar(Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "noticias", "calendario_usd_tier1.csv"),
                        NewsBeforeMin, NewsAfterMin, FomcBeforeMin, FomcAfterMin);
                    Print("EdgeLabCartera veto de noticias: " + _newsCal.Status);
                }
                string volPath = string.IsNullOrWhiteSpace(VolCsvPath)
                    ? Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "datos", "cboe_vol_diario.csv") : VolCsvPath.Trim();
                bool interdia = Preset == CarteraPreset.Interdia;
                for (int i = 0; i < _comp.Count; i++)
                {
                    string root = _comp[i].Key;
                    FundedSyncActivo act;
                    if (!Enum.TryParse(root, true, out act)) { _blocked = true; Print("EdgeLabCartera BLOQUEADA: activo desconocido " + root); return; }
                    FundedSyncAssetSpec spec = FundedSyncAssets.Get(act);
                    var coord = BuildCoordinator(act, spec, _comp[i].Value, volPath, interdia);
                    if (coord == null) { _blocked = true; return; }
                    if (EnableCsvLog)
                    {
                        coord.EnableCsvLog = true;
                        coord.CsvLogPath = Path.Combine(_dir, Preset + "_" + spec.Root + ".csv");
                        if (File.Exists(coord.CsvLogPath)) File.Delete(coord.CsvLogPath);
                    }
                    double tick = BarsArray[i].Instrument.MasterInstrument.TickSize;
                    var book = new CarteraBook(i, spec.Root, coord, tick, this, _brokerHist);
                    _books.Add(book); _byBip[i] = book;
                    Print("EdgeLabCartera libro " + i + ": " + BarsArray[i].Instrument.FullName + " -> "
                          + string.Join(", ", _comp[i].Value.Select(kv => kv.Key + "x" + kv.Value)) + (interdia ? " (mantiene de noche)" : ""));
                }
                Print("EdgeLabCartera " + Preset + " | historico " + (_brokerHist ? "con ordenes reales (Backtest)" : "virtual, arranque plano en tiempo real")
                      + " | perdida diaria max $" + PerdidaDiariaMaxUSD + " | perdida total max $" + PerdidaTotalMaxUSD);
            }
            else if (State == State.Transition)
            {
                if (!_brokerHist) foreach (var b in _books) b.ResetToFlatBrokerMode();
            }
        }

        // ---------------------------------------------------------------------------------------------------------------
        public static string DefaultComposicion(CarteraPreset p)
        {
            switch (p)
            {
                case CarteraPreset.Interdia: return "MNQ:SOM=1,C2VZ=1;MES:C2VZ=1";
                case CarteraPreset.Rescate25K: return "MNQ:T=1";
                default: return "MNQ:T=1,R=1,Z=1,V=1,RQ5=1,FR=1;MES:RQ5=1,ES5N=1";
            }
        }

        private static List<KeyValuePair<string, List<KeyValuePair<string, int>>>> ParseComposicion(string s)
        {
            var res = new List<KeyValuePair<string, List<KeyValuePair<string, int>>>>();
            foreach (string blk in (s ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string[] p = blk.Split(':');
                if (p.Length != 2) continue;
                var items = new List<KeyValuePair<string, int>>();
                foreach (string it in p[1].Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries))
                {
                    string[] kv = it.Split('=');
                    int q = 1;
                    if (kv.Length == 2) int.TryParse(kv[1].Trim(), out q);
                    if (q > 0) items.Add(new KeyValuePair<string, int>(kv[0].Trim().ToUpperInvariant(), q));
                }
                res.Add(new KeyValuePair<string, List<KeyValuePair<string, int>>>(p[0].Trim().ToUpperInvariant(), items));
            }
            return res;
        }

        private static Dictionary<string, string> ParseSecundarios(string s)
        {
            var d = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (string it in (s ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string[] kv = it.Split('=');
                if (kv.Length == 2) d[kv[0].Trim()] = kv[1].Trim();
            }
            return d;
        }

        private static readonly Dictionary<string, string> FsIds = new Dictionary<string, string>
        {
            { "R", "R_osc30_end660_ATR50" }, { "Z", "Z_b15_e20_eff40_ATR50" }, { "T", "T_stop100_BE15R_calFalse" },
            { "V", "V_nm25_noCap_mae30" }, { "W", "W_slope_allowReFalse_ATR25" }, { "N", "N_d5_fbTrue_ATR25" },
            { "SOMEOD", "SOMEOD_ext_NQ" }, { "SOM", "SOM_sin_finde" }
        };

        private PortfolioCoordinator BuildCoordinator(FundedSyncActivo act, FundedSyncAssetSpec spec, List<KeyValuePair<string, int>> items, string volPath, bool interdia)
        {
            var weights = new Dictionary<string, double>();
            bool[] flags = new bool[FundedSyncMath.ModuleOrder.Length];
            for (int i = 0; i < FundedSyncMath.ModuleOrder.Length; i++) weights[FundedSyncMath.ModuleOrder[i]] = 0.0;
            foreach (var kv in items)
            {
                string fid;
                if (FsIds.TryGetValue(kv.Key, out fid)) { weights[fid] = 1.0; flags[Array.IndexOf(FundedSyncMath.ModuleOrder, fid)] = true; }
            }
            bool es = act == FundedSyncActivo.ES || act == FundedSyncActivo.MES;
            PortfolioCoordinator c = es
                ? new PortfolioCoordinator(weights, flags, enableWTrail: false,
                    rOscMult: 2.0, rEndEt: 660, rSlAtr: 0.50, zBucketMin: 15, zEmaPeriod: 20, zMinEffPct: 35.0, zSlAtr: 0.50,
                    tStopOrbMult: 1.0, tBeTrigR: 0.0, vNoiseMult: 0.30, vSlAtr: 0.35, wSlAtr: 0.35, nDays: 5, nSlAtr: 0.25,
                    tStopMinPts: 0.6, tStopMaxPts: 29.0, vTpPts: 15.7, wUseSlopeFilter: false, nAcceptBufPts: 0.9)
                : new PortfolioCoordinator(weights, flags);
            foreach (var kv in items)
            {
                string fid;
                if (FsIds.TryGetValue(kv.Key, out fid)) { c.SetSleeveFixedContracts(fid, kv.Value); continue; }
                switch (kv.Key)
                {
                    case "RQ5": c.AddEngine(new RQ5Engine("RQ5", 60, 1.0, 1130, 0.45, 2.0, spec.FrictionPts, 0.08), 1.0, kv.Value); break;
                    case "FR": c.AddEngine(new FranklinEngine("FRANKLIN", false), 1.0, kv.Value); break;
                    case "FRV": c.AddEngine(new FranklinEngine("FRANKLIN_VETOPREAP", true), 1.0, kv.Value); break;
                    case "ES5N": c.AddEngine(new ES5NEngine("ES5N"), 1.0, kv.Value); break;
                    case "C2VZ":
                    case "C2EVRP":
                        {
                            bool nq = act == FundedSyncActivo.NQ || act == FundedSyncActivo.MNQ;
                            var eng = new Carril2Engine(kv.Key == "C2VZ" ? "C2_VZ" : "C2_EVRP", kv.Key == "C2VZ", nq, volPath);
                            if (!eng.Loaded) { Print("EdgeLabCartera BLOQUEADA: falta el CSV CBOE " + volPath + " (tools/exportar_vix_nt8.py)"); return null; }
                            c.AddEngine(eng, 1.0, kv.Value);
                            break;
                        }
                    default:
                        Print("EdgeLabCartera BLOQUEADA: codigo de estrategia desconocido " + kv.Key); return null;
                }
            }
            c.MicroPointValue = spec.PointValue;
            c.FrictionMiniPts = spec.FrictionPts;
            c.AccountMode = FundedSyncAccountMode.Evaluation;
            c.EvalRisk1R_USD = 1.0; c.FundedRisk1R_USD = 1.0;          // sin sizing por riesgo: contratos fijos por estrategia
            c.MaxOpenR = 1000.0;
            c.MaxMicroContracts = 1000;
            c.MaxNetContracts = 0;
            c.FixedContracts = 0;
            c.CollisionPolicy = FundedSyncCollisionPolicy.Independent;
            c.HardFlattenHHMM_ET = interdia ? 0 : HardFlattenHHMM_ET;
            c.EnforceEvalDailyCap = false; c.EvalDailyCapUSD = 0.0; c.DailyLossLimitUSD = 0.0;
            c.NewsVeto = _newsCal;
            return c;
        }

        // ---------------------------------------------------------------------------------------------------------------
        protected override void OnBarUpdate()
        {
            if (_blocked) return;
            int b = BarsInProgress;
            CarteraBook book;
            if (!_byBip.TryGetValue(b, out book) || CurrentBars[b] < 1) return;
            if (BarsArray[b].BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsArray[b].BarsPeriod.Value != 1) return;

            DateTime chartLocal = DateTime.SpecifyKind(Times[b][0], DateTimeKind.Unspecified);
            DateTime closeUtc = _chartTz.Id == TimeZoneInfo.Utc.Id ? DateTime.SpecifyKind(chartLocal, DateTimeKind.Utc) : TimeZoneInfo.ConvertTimeToUtc(chartLocal, _chartTz);
            BarTimeContext ctx = FundedSyncMath.BuildBarTimeContext(closeUtc, Opens[b][0], Highs[b][0], Lows[b][0], Closes[b][0], Volumes[b][0], _nyTz, _ctTz);
            ctx.IsLastBarOfSession = BarsArray[b].IsLastBarOfSession;

            // guardas de cuenta (todas las estrategias y libros)
            int dk = ctx.EthTradeDate;
            if (dk != _dayKey) { _dayKey = dk; _dayBlocked = false; }
            double day = 0, open = 0;
            foreach (var bk in _books) { day += bk.Coord.RealizedSessionUsd; open += double.IsNaN(bk.LastClose) ? 0 : bk.Coord.OpenPnlUsdAt(bk.LastClose); }
            string guard = null;
            if (!_haltedTotal && PerdidaTotalMaxUSD > 0 && _realizedTotalUsd + open <= -PerdidaTotalMaxUSD) { _haltedTotal = true; guard = "PERDIDA_TOTAL_MAX"; }
            if (!_dayBlocked && PerdidaDiariaMaxUSD > 0 && day + open <= -PerdidaDiariaMaxUSD) { _dayBlocked = true; guard = "PERDIDA_DIARIA_MAX"; }
            if (!_dayBlocked && ObjetivoDiarioUSD > 0 && day + open >= ObjetivoDiarioUSD) { _dayBlocked = true; guard = "OBJETIVO_DIARIO"; }

            // fin de sesion (intradia): 20 min antes del cierre real de la sesion, tambien en cierres tempranos de feriado
            bool finSesion = false;
            if (Preset != CarteraPreset.Interdia && MinAntesFinSesion > 0)
            {
                SessionIterator it;
                if (!_sessIt.TryGetValue(b, out it)) { it = new SessionIterator(BarsArray[b]); _sessIt[b] = it; }
                if (BarsArray[b].IsFirstBarOfSession || it.ActualSessionEnd <= Times[b][0]) it.GetNextSession(Times[b][0], true);
                finSesion = (it.ActualSessionEnd - Times[b][0]).TotalMinutes <= MinAntesFinSesion;
            }

            book.Coord.ExternalBlock = _haltedTotal || _dayBlocked || finSesion;
            book.OnBar(ctx);
            // control: posicion real de NT8 = suma de las estrategias del libro (sin ordenes de entrada/salida en vuelo)
            if (Coord_Broker(book) && !book.AnyMarketInFlight)
            {
                int real = PositionQty(b), esperado = book.ExpectedNet;
                if (real != esperado && ++_descuadres <= 50)
                    Print("EdgeLabCartera DESCUADRE " + book.Root + " " + ctx.CloseNy.ToString("yyyy-MM-dd HH:mm") + " NT8 " + real + " libro " + esperado);
            }
            if (guard != null) { Print("EdgeLabCartera GUARDA " + guard + " " + ctx.CloseNy.ToString("yyyy-MM-dd HH:mm")); foreach (var bk in _books) bk.FlattenAll(guard); }
            else if (finSesion) book.FlattenAll("FIN_SESION");
            else if (_haltedTotal || _dayBlocked) book.FlattenAll(_haltedTotal ? "PERDIDA_TOTAL_MAX" : "BLOQUEO_DIARIO");

            _nBars++;
            if (Diagnostico && b == 0)
            {
                int mes = ctx.CloseNy.Year * 100 + ctx.CloseNy.Month;
                if (mes != _mesDiag)
                {
                    if (_mesDiag > 0)
                        Print(string.Format(CultureInfo.InvariantCulture,
                            "EdgeLabCartera DIAG {0}: velas {1} | ordenes enviadas {2} cambios {3} cancel {4} fills {5} rechazos {6} eventos {7} | ordenes en mapa {8} | destrabes {9} | descuadres {10} | memoria {11:F0} MB",
                            _mesDiag, _nBars, _nSub, _nChg, _nCan, _nFill, _nRej, _nUpd, _orders.Count, _books.Sum(x => x.Destrabes), _descuadres, GC.GetTotalMemory(false) / 1048576.0));
                    _mesDiag = mes;
                }
            }
            if (b == 0) DrawHud();
        }

        private void DrawHud()
        {
            if (State != State.Realtime) return;
            var sb = new StringBuilder();
            sb.Append("EdgeLabCartera " + Preset + (_haltedTotal ? " | DETENIDA (perdida total)" : (_dayBlocked ? " | bloqueada hoy" : "")));
            foreach (var bk in _books)
                sb.Append("\n" + bk.Root + ": neto esperado " + bk.ExpectedNet + " | real " + PositionQty(bk.Index)
                          + " | dia $" + (bk.Coord.RealizedSessionUsd + (double.IsNaN(bk.LastClose) ? 0 : bk.Coord.OpenPnlUsdAt(bk.LastClose))).ToString("F0", CultureInfo.InvariantCulture));
            Draw.TextFixed(this, "edgelab_cartera_hud", sb.ToString(), TextPosition.TopLeft);
        }

        private int PositionQty(int bip)
        {
            Position p = Positions[bip];
            return p.MarketPosition == MarketPosition.Long ? p.Quantity : (p.MarketPosition == MarketPosition.Short ? -p.Quantity : 0);
        }

        // ---------------------------------------------------------------------------------------------------------------
        // ICarteraGateway: ordenes unmanaged
        public void Submit(CarteraBook book, string tag, CarteraRole role, string sleeveId, int side, int qty, CarteraOrderType type, double price, string oco)
        {
            _nSub++;
            OrderAction act;
            int cur = PositionQty(book.Index);
            if (side > 0) act = cur < 0 && qty <= -cur ? OrderAction.BuyToCover : OrderAction.Buy;
            else act = cur > 0 && qty <= cur ? OrderAction.Sell : OrderAction.SellShort;
            OrderType ot = type == CarteraOrderType.Market ? OrderType.Market : (type == CarteraOrderType.Stop ? OrderType.StopMarket : OrderType.Limit);
            double lim = type == CarteraOrderType.Limit ? price : 0, stp = type == CarteraOrderType.Stop ? price : 0;
            if (EnableExecAudit && State == State.Realtime)
                _audit[tag] = new AuditMeta { SubmitUtc = DateTime.UtcNow, RefPx = type == CarteraOrderType.Market ? book.LastClose : price, Side = side,
                                              Book = book.Root, Sleeve = sleeveId, Role = role.ToString(), Tick = book.TickSize,
                                              Pv = BarsArray[book.Index].Instrument.MasterInstrument.PointValue };
            Audit(tag, "SUBMIT", qty, double.NaN);
            Order o = SubmitOrderUnmanaged(book.Index, act, ot, qty, lim, stp, oco ?? "", tag);
            if (o != null && !_orders.ContainsKey(tag) && !Order.IsTerminalState(o.OrderState)) _orders[tag] = o;
        }

        public void Change(CarteraBook book, string tag, int qty, double price)
        {
            Order o;
            if (!_orders.TryGetValue(tag, out o) || o == null || Order.IsTerminalState(o.OrderState)) return;
            _nChg++;
            if (o.OrderType == OrderType.StopMarket) ChangeOrder(o, qty, 0, price); else ChangeOrder(o, qty, price, 0);
            AuditMeta m; if (_audit.TryGetValue(tag, out m)) m.RefPx = price;
            Audit(tag, "CHANGE", qty, price);
        }

        public void Cancel(CarteraBook book, string tag)
        {
            Order o;
            if (_orders.TryGetValue(tag, out o) && o != null && !Order.IsTerminalState(o.OrderState)) { _nCan++; CancelOrder(o); }
        }

        public void Log(string msg) { Print("EdgeLabCartera " + msg); }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled, double averageFillPrice,
                                              OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            if (_blocked || order == null || string.IsNullOrEmpty(order.Name)) return;
            _nUpd++;
            if (orderState == OrderState.Filled) _nFill++;
            if (orderState == OrderState.Rejected) _nRej++;
            string tag = order.Name;
            CarteraBook book = null;
            foreach (var bk in _books) if (bk.Owns(tag)) { book = bk; break; }
            if (book == null)
            {
                if (Order.IsTerminalState(orderState)) _orders.Remove(tag);
                return;
            }
            _orders[tag] = order;
            if (orderState == OrderState.Filled)
            {
                DateTime ny = ToNy(time);
                Audit(tag, "FILLED", filled, averageFillPrice);
                book.OnFilled(tag, averageFillPrice, filled, ny);
                _orders.Remove(tag);
                RecalcRealizedTotal();
            }
            else if (orderState == OrderState.Cancelled || orderState == OrderState.Rejected)
            {
                Audit(tag, orderState == OrderState.Rejected ? "REJECTED " + error + " " + comment : "CANCELLED", quantity, double.NaN);
                _orders.Remove(tag);
                book.OnTerminal(tag, orderState == OrderState.Rejected);
            }
            else if (orderState == OrderState.Accepted || orderState == OrderState.Working)
            {
                Audit(tag, orderState.ToString().ToUpperInvariant(), quantity, double.NaN);
            }
        }

        private void RecalcRealizedTotal()
        {
            double t = 0;
            foreach (var bk in _books) foreach (var r in bk.Coord.CompletedTrades) t += (r.PnlPts - bk.Coord.FrictionMiniPts) * r.Contracts * r.PointValue;
            _realizedTotalUsd = t;
        }

        private DateTime ToNy(DateTime chartTime)
        {
            DateTime local = DateTime.SpecifyKind(chartTime, DateTimeKind.Unspecified);
            DateTime utc = _chartTz.Id == TimeZoneInfo.Utc.Id ? DateTime.SpecifyKind(local, DateTimeKind.Utc) : TimeZoneInfo.ConvertTimeToUtc(local, _chartTz);
            return TimeZoneInfo.ConvertTimeFromUtc(utc, _nyTz);
        }

        // registro de ejecucion: latencia (ms desde el envio) y deslizamiento en ticks (positivo = en contra) en tiempo real
        private void Audit(string tag, string ev, int qty, double px)
        {
            if (!EnableExecAudit || State != State.Realtime) return;
            AuditMeta m;
            if (!_audit.TryGetValue(tag, out m)) return;
            try
            {
                double ms = (DateTime.UtcNow - m.SubmitUtc).TotalMilliseconds;
                double slipT = (!double.IsNaN(px) && !double.IsNaN(m.RefPx) && ev == "FILLED") ? m.Side * (px - m.RefPx) / m.Tick : double.NaN;
                if (!File.Exists(_auditPath))
                    File.WriteAllText(_auditPath, "utc,evento,libro,estrategia,rol,orden,lado,cantidad,precio_ref,precio,ms_desde_envio,desliz_ticks,desliz_usd" + Environment.NewLine, Encoding.UTF8);
                string line = string.Format(CultureInfo.InvariantCulture, "{0:yyyy-MM-dd HH:mm:ss.fff},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10:F0},{11:F2},{12:F2}",
                    DateTime.UtcNow, ev.Replace(',', ';'), m.Book, m.Sleeve, m.Role, tag, m.Side, qty, m.RefPx, px, ms, slipT,
                    double.IsNaN(slipT) ? double.NaN : slipT * m.Tick * m.Pv * qty);
                File.AppendAllText(_auditPath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }

        #region Properties
        [NinjaScriptProperty] [Display(Name = "Preset", Order = 1, GroupName = "01. Cartera")] public CarteraPreset Preset { get; set; }
        [NinjaScriptProperty] [Display(Name = "Composicion (vacio = preset)", Order = 2, GroupName = "01. Cartera",
            Description = "MNQ:T=1,R=1;MES:RQ5=1 - el primer instrumento es el del grafico")] public string Composicion { get; set; }
        [NinjaScriptProperty] [Display(Name = "Instrumentos secundarios (vacio = mismo vencimiento)", Order = 3, GroupName = "01. Cartera",
            Description = "MES=MES 12-26;MGC=MGC 02-27")] public string InstrumentosSecundarios { get; set; }
        [NinjaScriptProperty] [Range(0, 100000)] [Display(Name = "Perdida diaria max USD (0 = no)", Order = 1, GroupName = "02. Guardas de cuenta")] public double PerdidaDiariaMaxUSD { get; set; }
        [NinjaScriptProperty] [Range(0, 1000000)] [Display(Name = "Perdida total max USD (0 = no)", Order = 2, GroupName = "02. Guardas de cuenta")] public double PerdidaTotalMaxUSD { get; set; }
        [NinjaScriptProperty] [Range(0, 100000)] [Display(Name = "Objetivo diario USD (0 = no)", Order = 3, GroupName = "02. Guardas de cuenta")] public double ObjetivoDiarioUSD { get; set; }
        [NinjaScriptProperty] [Range(0, 2400)] [Display(Name = "Plano forzado HHMM ET (intradia)", Order = 4, GroupName = "02. Guardas de cuenta")] public int HardFlattenHHMM_ET { get; set; }
        [NinjaScriptProperty] [Range(0, 120)] [Display(Name = "Minutos antes del fin de sesion (intradia)", Order = 5, GroupName = "02. Guardas de cuenta")] public int MinAntesFinSesion { get; set; }
        [NinjaScriptProperty] [Display(Name = "Veto de noticias", Order = 1, GroupName = "03. Noticias")] public bool EnableNewsVeto { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes", Order = 2, GroupName = "03. Noticias")] public double NewsBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues", Order = 3, GroupName = "03. Noticias")] public double NewsAfterMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes FOMC", Order = 4, GroupName = "03. Noticias")] public double FomcBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues FOMC", Order = 5, GroupName = "03. Noticias")] public double FomcAfterMin { get; set; }
        [NinjaScriptProperty] [Display(Name = "CSV CBOE (vacio = defecto)", Order = 1, GroupName = "04. Datos y registro")] public string VolCsvPath { get; set; }
        [NinjaScriptProperty] [Display(Name = "CSV de operaciones por libro", Order = 2, GroupName = "04. Datos y registro")] public bool EnableCsvLog { get; set; }
        [NinjaScriptProperty] [Display(Name = "Registro de ejecucion (tiempo real)", Order = 3, GroupName = "04. Datos y registro")] public bool EnableExecAudit { get; set; }
        [NinjaScriptProperty] [Display(Name = "Diagnostico mensual (Output)", Order = 4, GroupName = "04. Datos y registro")] public bool Diagnostico { get; set; }
        #endregion
    }
}
