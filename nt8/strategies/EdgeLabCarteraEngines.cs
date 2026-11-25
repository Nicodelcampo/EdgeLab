// EdgeLabCarteraEngines (2026-11-25): RQ5, Franklin, ES5N y Carril2 (C2_VZ / C2_EVRP) como motores del coordinador
// (ModuleEngineBase) para correr varias estrategias en UNA estrategia NT8 (EdgeLabCartera). La logica de senal es la de
// EdgeLabRQ5.cs, EdgeLabCandidataFranklin.cs, EdgeLabCandidataES5N.cs y EdgeLabCandidataCarril2.cs, sin cambios: aca solo
// cambia quien ejecuta (el coordinador / el broker por estrategia). Codigo C# puro (sin tipos de NinjaTrader): se compila
// tambien en el arnes de paridad tools/nt8_cartera_harness (Python + csc) contra las corridas NT8 individuales.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;

namespace NinjaTrader.NinjaScript.Strategies.EdgeLabFundedSync
{
    // ---------------------------------------------------------------------------------------------------------------
    // RQ5: banda de ruido intradia (fabrica RQ5-REGIMEN). Decision al cierre de las velas 10:00, 10:30, 11:00, 11:30, 12:00
    // ET (hasta el corte); stop = cierre -/+ d, d = max(s * ATR diario RTH, 0,5 * banda); objetivo tp * d; cierre 16:00.
    // ---------------------------------------------------------------------------------------------------------------
    internal sealed class RQ5Engine : ModuleEngineBase
    {
        private static readonly int[] Slots = { 600, 630, 660, 690, 720 };
        private readonly int _l, _corteMin; private readonly double _m, _s, _tp, _fricPts, _fricMaxR;
        private DateTime _rthFecha = DateTime.MinValue;
        private bool _hayDia, _hayPrevio, _senalHoy;
        private double _ab, _hi, _lo, _cl, _sumTp, _atrDia = double.NaN, _prevCierre = double.NaN, _prevHi, _prevLo;
        private int _nTp;
        private readonly Queue<double> _trs = new Queue<double>();
        private readonly Dictionary<int, List<double>> _hist = new Dictionary<int, List<double>>();

        public RQ5Engine(string id, int l, double m, int corteHhmm, double s, double tp, double fricPts, double fricMaxR) : base(id)
        {
            _l = l; _m = m; _s = s; _tp = tp; _fricPts = fricPts; _fricMaxR = fricMaxR;
            _corteMin = (corteHhmm / 100) * 60 + corteHhmm % 100;
            foreach (int x in Slots) _hist[x] = new List<double>();
        }

        public override void OnNewEthSession(int completedEthDate, double completedHigh, double completedLow, double completedClose, int newEthDate) { }

        private void CerrarDia()
        {
            if (!_hayDia) return;
            double tr = _hayPrevio ? Math.Max(_hi - _lo, Math.Max(Math.Abs(_hi - _prevCierre), Math.Abs(_lo - _prevCierre))) : _hi - _lo;
            _trs.Enqueue(tr); while (_trs.Count > 20) _trs.Dequeue();
            _prevCierre = _cl; _prevHi = _hi; _prevLo = _lo; _hayPrevio = true; _hayDia = false;
        }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            DateTime t = bar.CloseNy;
            int minCierre = t.Hour * 60 + t.Minute;
            bool rth = minCierre >= 571 && minCierre <= 960;
            if (sl.IsOpen && sl.PendingExitReason == null)
            {
                if (minCierre == 960 || bar.IsLastBarOfSession || (_rthFecha != DateTime.MinValue && t.Date != _rthFecha && minCierre > 960))
                    host.QueueMarketExit(sl, "EOD_CLOSE");
            }
            if (!rth) return;
            if (t.Date != _rthFecha)
            {
                CerrarDia();
                _rthFecha = t.Date; _hayDia = true; _senalHoy = false;
                _ab = bar.Open; _hi = bar.High; _lo = bar.Low; _sumTp = 0; _nTp = 0;
                _atrDia = _trs.Count >= 3 ? _trs.Average() : (_hayPrevio ? _prevHi - _prevLo : double.NaN);
            }
            _hi = Math.Max(_hi, bar.High); _lo = Math.Min(_lo, bar.Low); _cl = bar.Close;
            _sumTp += (bar.High + bar.Low + bar.Close) / 3.0; _nTp++;
            double vwap = _sumTp / _nTp;
            List<double> h;
            if (!_hist.TryGetValue(minCierre, out h)) return;
            double ck = bar.Close, mv = Math.Abs(ck - _ab);
            if (!host.NewsVetoActiveNow && !_senalHoy && minCierre <= _corteMin && h.Count >= 10 && !double.IsNaN(_atrDia) && _atrDia > 0
                && !sl.IsOpen && !sl.HasPendingEntry)
            {
                double banda = h.Skip(Math.Max(0, h.Count - _l)).Average();
                int ld = ck > _ab ? 1 : -1;
                bool vwOk = (ld == 1 && ck >= vwap) || (ld == -1 && ck <= vwap);
                if (banda > 0 && mv >= _m * banda && vwOk)
                {
                    _senalHoy = true;
                    double d = Math.Max(_s * _atrDia, 0.5 * banda);
                    if (!(_fricPts > 0 && _fricPts / d > _fricMaxR))
                        host.QueueMarketEntryAbs(sl, ld, ck - ld * d, _tp > 0 ? ck + ld * _tp * d : double.NaN);
                }
            }
            h.Add(mv); if (h.Count > 90) h.RemoveAt(0);
        }
    }

    // ---------------------------------------------------------------------------------------------------------------
    // Franklin: a las 10:00 NY, cierre arriba del maximo de Londres (03:00-09:30) y del VWAP de sesion -> compra (abajo de
    // ambos -> venta); stop en el extremo opuesto de 09:30-10:00; salida al cierre 16:00. Veto PREAPERTURA opcional.
    // ---------------------------------------------------------------------------------------------------------------
    internal sealed class FranklinEngine : ModuleEngineBase
    {
        private readonly bool _vetoPreap;
        private DateTime _sesDate = DateTime.MinValue, _rthDate = DateTime.MinValue;
        private double _cumPv, _cumVol, _lonHi = double.NaN, _lonLo = double.NaN, _nightHi = double.NaN, _nightLo = double.NaN;
        private double _orHi = double.NaN, _orLo = double.NaN, _prevRthClose = double.NaN, _curRthClose = double.NaN;
        private bool _nightEvaluated, _nightHighToday, _tradedToday;
        private readonly Queue<double> _nightHist = new Queue<double>();

        public FranklinEngine(string id, bool vetoPreapertura) : base(id) { _vetoPreap = vetoPreapertura; }
        public override void OnNewEthSession(int completedEthDate, double completedHigh, double completedLow, double completedClose, int newEthDate) { }

        private void EvalPreap()
        {
            if (_nightEvaluated) return;
            _nightEvaluated = true; _nightHighToday = false;
            if (double.IsNaN(_nightHi) || double.IsNaN(_nightLo) || double.IsNaN(_prevRthClose) || _prevRthClose <= 0) return;
            double val = (_nightHi - _nightLo) / _prevRthClose;
            if (_nightHist.Count >= 120)
            {
                int below = 0; foreach (double x in _nightHist) if (x < val) below++;
                if ((double)below / _nightHist.Count > 2.0 / 3.0) _nightHighToday = true;
            }
            _nightHist.Enqueue(val); if (_nightHist.Count > 250) _nightHist.Dequeue();
        }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            DateTime openNy = bar.OpenNy;
            int openMin = openNy.Hour * 60 + openNy.Minute;
            DateTime ses = openNy.AddHours(6).Date;
            if (ses != _sesDate)
            {
                _sesDate = ses; _cumPv = 0; _cumVol = 0;
                _lonHi = _lonLo = _nightHi = _nightLo = double.NaN;
                _nightEvaluated = false; _nightHighToday = false;
            }
            double tp = (bar.High + bar.Low + bar.Close) / 3.0, vol = Math.Max(bar.Volume, 1e-9);
            _cumPv += tp * vol; _cumVol += vol;
            double vwap = _cumVol > 0 ? _cumPv / _cumVol : bar.Close;
            if (openMin >= 1080 || openMin < 570)
            {
                _nightHi = double.IsNaN(_nightHi) ? bar.High : Math.Max(_nightHi, bar.High);
                _nightLo = double.IsNaN(_nightLo) ? bar.Low : Math.Min(_nightLo, bar.Low);
            }
            if (openMin >= 180 && openMin < 570)
            {
                _lonHi = double.IsNaN(_lonHi) ? bar.High : Math.Max(_lonHi, bar.High);
                _lonLo = double.IsNaN(_lonLo) ? bar.Low : Math.Min(_lonLo, bar.Low);
            }
            if (sl.IsOpen && sl.PendingExitReason == null
                && (openMin >= 959 || bar.IsLastBarOfSession || (openNy.Date != _rthDate && _rthDate != DateTime.MinValue)))
            {
                host.QueueMarketExit(sl, "EOD_CLOSE");
                return;
            }
            if (!(openMin >= 570 && openMin < 960)) return;
            if (openNy.Date != _rthDate)
            {
                if (!double.IsNaN(_curRthClose)) _prevRthClose = _curRthClose;
                _rthDate = openNy.Date; _orHi = double.NaN; _orLo = double.NaN; _tradedToday = false;
                EvalPreap();
            }
            _curRthClose = bar.Close;
            if (openMin < 600)
            {
                _orHi = double.IsNaN(_orHi) ? bar.High : Math.Max(_orHi, bar.High);
                _orLo = double.IsNaN(_orLo) ? bar.Low : Math.Min(_orLo, bar.Low);
            }
            if (openMin == 599 && !_tradedToday && !sl.IsOpen && !sl.HasPendingEntry)
            {
                _tradedToday = true;
                if (host.NewsVetoActiveNow) return;
                if (_vetoPreap && _nightHighToday) return;
                if (double.IsNaN(_lonHi) || double.IsNaN(_lonLo) || double.IsNaN(_orHi) || double.IsNaN(_orLo)) return;
                double p = bar.Close;
                int d = (p > _lonHi && p > vwap) ? 1 : ((p < _lonLo && p < vwap) ? -1 : 0);
                if (d == 0) return;
                double st = d == 1 ? _orLo : _orHi;
                if (!(d * (p - st) > 0)) return;
                host.QueueMarketEntryAbs(sl, d, st, double.NaN);
            }
        }
    }

    // ---------------------------------------------------------------------------------------------------------------
    // ES5N: a las 10:00 NY, retorno de la primera media hora >= 0,12 ATR20 diario RTH con RSI(10) diario entre 40 y 60 ->
    // a favor; stop 0,45 ATR desde la entrada; salida 16:00.
    // ---------------------------------------------------------------------------------------------------------------
    internal sealed class ES5NEngine : ModuleEngineBase
    {
        private DateTime _rthDate = DateTime.MinValue;
        private bool _hasRthDay, _tradedToday;
        private double _rthOpen, _rthHi, _rthLo, _rthCl, _prevRthClose = double.NaN;
        private readonly Queue<double> _atr20 = new Queue<double>();
        private double _avgG = double.NaN, _avgL = double.NaN, _rsi10 = 50.0, _dayAtr = double.NaN, _dayRsi10 = 50.0;

        public ES5NEngine(string id) : base(id) { }
        public override void OnNewEthSession(int completedEthDate, double completedHigh, double completedLow, double completedClose, int newEthDate) { }

        private void ClosePrevRthDay()
        {
            if (!_hasRthDay) return;
            double tr = !double.IsNaN(_prevRthClose)
                ? Math.Max(_rthHi - _rthLo, Math.Max(Math.Abs(_rthHi - _prevRthClose), Math.Abs(_rthLo - _prevRthClose))) : (_rthHi - _rthLo);
            _atr20.Enqueue(tr); if (_atr20.Count > 20) _atr20.Dequeue();
            if (!double.IsNaN(_prevRthClose))
            {
                double d = _rthCl - _prevRthClose, g = d > 0 ? d : 0, l = d < 0 ? -d : 0;
                if (double.IsNaN(_avgG)) { _avgG = g; _avgL = l; }
                else { const double a = 0.1; _avgG = (1 - a) * _avgG + a * g; _avgL = (1 - a) * _avgL + a * l; }
                double tot = _avgG + _avgL;
                _rsi10 = tot > 1e-12 ? 100.0 * _avgG / tot : 50.0;
            }
            _prevRthClose = _rthCl; _hasRthDay = false;
        }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            DateTime openNy = bar.OpenNy;
            int openMin = openNy.Hour * 60 + openNy.Minute;
            if (sl.IsOpen && sl.PendingExitReason == null
                && (openMin >= 959 || bar.IsLastBarOfSession || (openNy.Date != _rthDate && _rthDate != DateTime.MinValue)))
            {
                host.QueueMarketExit(sl, "EOD_CLOSE");
                return;
            }
            if (openMin < 570 || openMin >= 960) return;
            if (openNy.Date != _rthDate)
            {
                ClosePrevRthDay();
                _rthDate = openNy.Date; _hasRthDay = true;
                _rthOpen = bar.Open; _rthHi = bar.High; _rthLo = bar.Low; _rthCl = bar.Close; _tradedToday = false;
                _dayAtr = _atr20.Count >= 4 ? _atr20.Average() : double.NaN;
                _dayRsi10 = _rsi10;
            }
            _rthHi = Math.Max(_rthHi, bar.High); _rthLo = Math.Min(_rthLo, bar.Low); _rthCl = bar.Close;
            if (openMin == 599 && !_tradedToday && !sl.IsOpen && !sl.HasPendingEntry)
            {
                _tradedToday = true;
                if (host.NewsVetoActiveNow || double.IsNaN(_dayAtr) || !(_dayAtr > 0) || double.IsNaN(_prevRthClose)) return;
                double ret30m = bar.Close - _rthOpen;
                if (Math.Abs(ret30m) < 0.12 * _dayAtr) return;
                if (_dayRsi10 < 40.0 || _dayRsi10 > 60.0) return;
                host.QueueMarketEntry(sl, ret30m > 0 ? 1 : -1, 0.45 * _dayAtr);
            }
        }
    }

    // ---------------------------------------------------------------------------------------------------------------
    // Carril2 (C2_VZ / C2_EVRP): swing largo en barras diarias CME (18:00 -> 17:00 NY) con datos CBOE diarios
    // (Documents\NinjaTrader 8\EdgeLab\datos\cboe_vol_diario.csv: fecha,vix,vxn,vix9d). Entrada al cierre diario,
    // stop = entrada - k * ATR20 diario, salida al cierre diario cuando la condicion se apaga o al tope de barras.
    // ---------------------------------------------------------------------------------------------------------------
    internal sealed class Carril2Engine : ModuleEngineBase
    {
        private struct VolRow { public double Vix, Vxn, Vix9d; }
        private readonly bool _vz, _isNq;
        private readonly List<DateTime> _volDates = new List<DateTime>();
        private readonly List<VolRow> _volRows = new List<VolRow>();
        public bool Loaded { get { return _volDates.Count > 0; } }
        private DateTime _curDay = DateTime.MinValue, _lastClosedDay = DateTime.MinValue;
        private double _dHi = double.NaN, _dLo = double.NaN, _dCl = double.NaN, _prevDailyClose = double.NaN;
        private readonly Queue<double> _tr20 = new Queue<double>(), _logRets10 = new Queue<double>(), _iv6 = new Queue<double>(), _v9_6 = new Queue<double>();
        private int _barsHeld;

        public Carril2Engine(string id, bool vz, bool isNq, string cboeCsvPath) : base(id)
        {
            _vz = vz; _isNq = isNq;
            if (!File.Exists(cboeCsvPath)) return;
            string[] lines = File.ReadAllLines(cboeCsvPath);
            for (int i = 1; i < lines.Length; i++)
            {
                string[] c = lines[i].Split(',');
                if (c.Length < 4) continue;
                DateTime dt;
                if (!DateTime.TryParseExact(c[0].Trim(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out dt)) continue;
                _volDates.Add(dt);
                _volRows.Add(new VolRow { Vix = P(c[1]), Vxn = P(c[2]), Vix9d = P(c[3]) });
            }
        }

        private static double P(string s) { double v; return double.TryParse(s.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : double.NaN; }

        private bool Lookup(DateTime d, out VolRow row)
        {
            row = default(VolRow);
            int idx = _volDates.BinarySearch(d);
            if (idx < 0) idx = (~idx) - 1;
            if (idx < 0) return false;
            row = _volRows[idx]; return true;
        }

        private static double Z6(Queue<double> q)
        {
            if (q.Count < 6) return double.NaN;
            double sum = 0; foreach (double x in q) { if (double.IsNaN(x)) return double.NaN; sum += x; }
            double mean = sum / q.Count, ss = 0, last = 0;
            foreach (double x in q) { ss += (x - mean) * (x - mean); last = x; }
            double sd = Math.Sqrt(ss / (q.Count - 1));
            return sd > 1e-12 ? (last - mean) / sd : double.NaN;
        }

        public override void OnNewEthSession(int completedEthDate, double completedHigh, double completedLow, double completedClose, int newEthDate) { }

        private void OnDailyClosed(DateTime day, VirtualSleeve sl, PortfolioCoordinator host)
        {
            if (day == DateTime.MinValue || day == _lastClosedDay || double.IsNaN(_dCl)) return;
            _lastClosedDay = day;
            double tr = !double.IsNaN(_prevDailyClose) ? Math.Max(_dHi - _dLo, Math.Max(Math.Abs(_dHi - _prevDailyClose), Math.Abs(_dLo - _prevDailyClose))) : (_dHi - _dLo);
            _tr20.Enqueue(tr); if (_tr20.Count > 20) _tr20.Dequeue();
            if (!double.IsNaN(_prevDailyClose) && _prevDailyClose > 0 && _dCl > 0)
            {
                _logRets10.Enqueue(Math.Log(_dCl / _prevDailyClose)); if (_logRets10.Count > 10) _logRets10.Dequeue();
            }
            _prevDailyClose = _dCl;
            VolRow vr;
            if (!Lookup(day, out vr)) return;
            double iv = _isNq ? vr.Vxn : vr.Vix;
            _iv6.Enqueue(iv); if (_iv6.Count > 6) _iv6.Dequeue();
            _v9_6.Enqueue(vr.Vix9d); if (_v9_6.Count > 6) _v9_6.Dequeue();
            if (_tr20.Count < 20) return;
            double atr20 = _tr20.Average();
            if (!(atr20 > 0)) return;
            bool cond; double slMult; int tope;
            if (_vz)
            {
                double zIv = Z6(_iv6), zV9 = Z6(_v9_6);
                if (double.IsNaN(zIv) || double.IsNaN(zV9)) return;
                cond = 0.5 * (zIv + zV9) < -1.0; slMult = 1.25; tope = 10;
            }
            else
            {
                if (_logRets10.Count < 10 || double.IsNaN(iv) || double.IsNaN(vr.Vix) || double.IsNaN(vr.Vix9d) || vr.Vix <= 0) return;
                double m = _logRets10.Average(), ss = 0; foreach (double r in _logRets10) ss += (r - m) * (r - m);
                double rv10 = Math.Sqrt(ss / (_logRets10.Count - 1)) * Math.Sqrt(252.0) * 100.0;
                cond = (iv - rv10 > 0.0) && (vr.Vix9d / vr.Vix < 1.0); slMult = 2.0; tope = 20;
            }
            if (sl.IsOpen)
            {
                _barsHeld++;
                if ((!cond || _barsHeld >= tope) && sl.PendingExitReason == null) host.QueueMarketExit(sl, !cond ? "SALIDA_COND" : "SALIDA_TOPE");
                return;
            }
            if (cond && !host.NewsVetoActiveNow && !sl.HasPendingEntry)
            {
                _barsHeld = 0;
                host.QueueMarketEntry(sl, 1, slMult * atr20);
            }
        }

        public override void ProcessBar(BarTimeContext bar, double atr20Session, VirtualSleeve sl, PortfolioCoordinator host)
        {
            DateTime closeNy = bar.CloseNy, openNy = bar.OpenNy;
            DateTime td = openNy.AddHours(6).Date;
            if (td.DayOfWeek == DayOfWeek.Saturday || td.DayOfWeek == DayOfWeek.Sunday) return;
            if (!sl.IsOpen) { } // el conteo de barras se reinicia al entrar
            if (_curDay != DateTime.MinValue && td != _curDay) { OnDailyClosed(_curDay, sl, host); _curDay = DateTime.MinValue; }
            if (_curDay != td) { _curDay = td; _dHi = bar.High; _dLo = bar.Low; _dCl = bar.Close; }
            else { _dHi = Math.Max(_dHi, bar.High); _dLo = Math.Min(_dLo, bar.Low); _dCl = bar.Close; }
            int closeMin = closeNy.Hour * 60 + closeNy.Minute;
            if ((closeMin == 1020 && closeNy.Date == _curDay) || bar.IsLastBarOfSession) OnDailyClosed(_curDay, sl, host);
        }
    }
}
