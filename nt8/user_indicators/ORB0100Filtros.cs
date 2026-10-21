// ORB0100Filtros — rango de 01:00-01:15 (hora de Nueva York) en velas de 5 minutos, ruptura por cierre de cuerpo,
// SL en el otro lado del rango, TP a 0,5 R, y 5 filtros de regimen comparados en un tablero (estrategia de Instagram,
// adaptada a NT8 como indicador de simulacion; no envia ordenes).
//
// Reglas:
// - Rango: maximo y minimo de las velas cuyo CIERRE cae en (01:00, 01:15] ET (3 velas de 5 min).
// - Entrada: la PRIMERA vela posterior cuyo cuerpo cierra fuera del rango (Close > alto => largo; Close < bajo => corto),
//   al precio de cierre de esa vela. Una operacion por dia.
// - SL: el otro lado del rango. TP: entrada +/- TargetR x riesgo. Se evalua desde la vela siguiente; si una vela toca
//   SL y TP, cuenta SL (conservador). Cierre forzado a la hora de fin (16:00 ET por defecto) al cierre de esa vela.
// - Costos: slippage en ticks (entrada y salida a mercado) y comision por operacion (USD).
// - Filtros: tamano del rango (ticks), lado del VWAP de la sesion (reinicia 18:00 ET), tendencia EMA, rango <= % del ADR,
//   dia de la semana. El tablero muestra: Base, cada filtro solo, y "Seleccion" (los filtros activados juntos).
//   Lo dibujado en el grafico corresponde a "Seleccion".
// Uso: grafico de 5 minutos de MNQ (o el contrato que quieras), Calculate = OnBarClose.
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Text;
using System.Windows.Media;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class ORB0100Filtros : Indicator
    {
        private class Stats { public int N, W, L, T; public double Pts, Usd, Peak, MaxDD, Eq; }
        private const int NV = 7;                       // 0 Base, 1 Rango, 2 VWAP, 3 EMA, 4 ADR, 5 Dia, 6 Seleccion
        private static readonly string[] Names = { "Base", "Tam. rango", "Lado VWAP", "Tend. EMA", "Filtro ADR", "Dia semana", "SELECCION" };
        private Stats[] st;
        private TimeZoneInfo et;
        private EMA ema;

        private DateTime curDay = DateTime.MinValue;    // dia ET del rango
        private double rHi, rLo; private bool rHas, rDone, traded;
        private double vwapPV, vwapV; private DateTime vwapSession = DateTime.MinValue;
        private Dictionary<DateTime, double[]> dayHL = new Dictionary<DateTime, double[]>();
        private List<double> adrHist = new List<double>();

        private bool inPos; private DateTime entryDay; private int dir; private double entry, sl, tp; private int entryBar; private bool[] take = new bool[NV];
        private int tradeId;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "ORB0100Filtros"; Description = "ORB 01:00-01:15 NY en 5 min, ruptura por cuerpo, SL rango, TP 0,5R, 5 filtros y tablero";
                Calculate = Calculate.OnBarClose; IsOverlay = true; DisplayInDataBox = false; PaintPriceMarkers = false;
                RangeStartHHMM = 100; RangeEndHHMM = 115; ExitHHMM = 1600; TargetR = 0.5;
                SlippageTicks = 1; CommissionUsd = 1.24;
                UseRangeSize = false; MinRangeTicks = 20; MaxRangeTicks = 200;
                UseVwap = false; UseEma = false; EmaPeriod = 50;
                UseAdr = false; AdrDays = 14; MaxRangePctAdr = 25;
                UseDow = false; Mon = true; Tue = true; Wed = true; Thu = true; Fri = true;
                DrawTrades = true;
            }
            else if (State == State.DataLoaded)
            {
                st = new Stats[NV]; for (int i = 0; i < NV; i++) st[i] = new Stats();
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                ema = EMA(Close, EmaPeriod);
            }
        }

        private DateTime ToEt(DateTime t) { return TimeZoneInfo.ConvertTime(t, Core.Globals.GeneralOptions.TimeZoneInfo, et); }
        private static int Hhmm(DateTime t) { return t.Hour * 100 + t.Minute; }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 2) return;
            if (CurrentBar == 2) Dashboard();
            DateTime e = ToEt(Time[0]);
            int hm = Hhmm(e);

            // VWAP de sesion CME (reinicia 18:00 ET)
            DateTime ses = hm >= 1800 ? e.Date.AddDays(1) : e.Date;
            if (ses != vwapSession) { vwapSession = ses; vwapPV = 0; vwapV = 0; }
            double tpx = (High[0] + Low[0] + Close[0]) / 3.0; vwapPV += tpx * Volume[0]; vwapV += Volume[0];
            double vwap = vwapV > 0 ? vwapPV / vwapV : Close[0];

            // rangos diarios (dia calendario ET) para el ADR
            double[] hl;
            if (!dayHL.TryGetValue(e.Date, out hl)) { dayHL[e.Date] = new double[] { High[0], Low[0] }; if (dayHL.Count > 1) RollAdr(e.Date); }
            else { hl[0] = Math.Max(hl[0], High[0]); hl[1] = Math.Min(hl[1], Low[0]); }

            // nuevo dia de rango
            if (e.Date != curDay) { curDay = e.Date; rHas = false; rDone = false; traded = false; }

            // posicion abierta: resolver con esta vela (empieza en la vela siguiente a la entrada)
            if (inPos && CurrentBar > entryBar)
            {
                bool hitSl = dir > 0 ? Low[0] <= sl : High[0] >= sl;
                bool hitTp = dir > 0 ? High[0] >= tp : Low[0] <= tp;
                bool timeExit = hm >= ExitHHMM || e.Date != entryDay;          // hora de salida o cambio de dia ET
                if (hitSl) Close_(sl, false, "SL");
                else if (hitTp) Close_(tp, true, "TP");
                else if (timeExit) Close_(Close[0], Close[0] * dir > entry * dir, "T");
            }

            // construir el rango: velas que CIERRAN en (inicio, fin]
            if (hm > RangeStartHHMM && hm <= RangeEndHHMM)
            {
                if (!rHas) { rHi = High[0]; rLo = Low[0]; rHas = true; } else { rHi = Math.Max(rHi, High[0]); rLo = Math.Min(rLo, Low[0]); }
                if (hm == RangeEndHHMM) rDone = true;
                return;
            }
            if (hm > RangeEndHHMM && rHas) rDone = true;

            // senal: primera ruptura por cierre de cuerpo, antes de la hora de salida
            if (!rDone || traded || inPos || hm >= ExitHHMM || hm <= RangeEndHHMM) return;
            int d = Close[0] > rHi ? 1 : (Close[0] < rLo ? -1 : 0);
            if (d == 0) return;
            traded = true;
            double risk = d > 0 ? Close[0] - rLo : rHi - Close[0];
            if (risk <= 0) return;
            double rangeTicks = (rHi - rLo) / TickSize;
            double adr = adrHist.Count >= AdrDays ? Avg(adrHist, AdrDays) : double.NaN;
            bool fR = rangeTicks >= MinRangeTicks && rangeTicks <= MaxRangeTicks;
            bool fV = d > 0 ? Close[0] > vwap : Close[0] < vwap;
            bool fE = d > 0 ? Close[0] > ema[0] : Close[0] < ema[0];
            bool fA = !double.IsNaN(adr) && (rHi - rLo) <= MaxRangePctAdr / 100.0 * adr;
            bool fD = DowOk(e.DayOfWeek);
            take[0] = true; take[1] = fR; take[2] = fV; take[3] = fE; take[4] = fA; take[5] = fD;
            take[6] = (!UseRangeSize || fR) && (!UseVwap || fV) && (!UseEma || fE) && (!UseAdr || fA) && (!UseDow || fD);
            inPos = true; dir = d; entry = Close[0]; sl = d > 0 ? rLo : rHi; tp = entry + d * TargetR * risk; entryBar = CurrentBar; entryDay = e.Date; tradeId++;
            if (DrawTrades && take[6])
            {
                if (d > 0) Draw.ArrowUp(this, "orb_in" + tradeId, false, 0, Low[0] - 2 * TickSize, Brushes.DodgerBlue);
                else Draw.ArrowDown(this, "orb_in" + tradeId, false, 0, High[0] + 2 * TickSize, Brushes.OrangeRed);
            }
            if (DrawTrades && take[6])
            {
                Draw.Line(this, "orb_rh" + tradeId, false, CurrentBar - FirstRangeBar(), rHi, 0, rHi, Brushes.Gray, DashStyleHelper.Dash, 1);
                Draw.Line(this, "orb_rl" + tradeId, false, CurrentBar - FirstRangeBar(), rLo, 0, rLo, Brushes.Gray, DashStyleHelper.Dash, 1);
            }
        }

        private int FirstRangeBar() { return Math.Max(0, entryBar - 6); }

        private void Close_(double px, bool win, string why)
        {
            double slip = SlippageTicks * TickSize;
            double exitPx = why == "TP" ? px : px - dir * slip;                // TP limite; SL y tiempo a mercado
            double pts = dir * (exitPx - entry) - slip;                         // slippage de entrada
            double usd = pts * Instrument.MasterInstrument.PointValue - CommissionUsd;
            for (int i = 0; i < NV; i++)
            {
                if (!take[i]) continue;
                Stats s = st[i]; s.N++; if (why == "TP") s.W++; else if (why == "SL") s.L++; else s.T++;
                s.Pts += pts; s.Usd += usd; s.Eq += usd; s.Peak = Math.Max(s.Peak, s.Eq); s.MaxDD = Math.Max(s.MaxDD, s.Peak - s.Eq);
            }
            if (DrawTrades && take[6])
            {
                int ago = CurrentBar - entryBar;
                Draw.Rectangle(this, "orb_tp" + tradeId, false, ago, entry, 0, tp, Brushes.Transparent, Brushes.LimeGreen, 15);
                Draw.Rectangle(this, "orb_sl" + tradeId, false, ago, entry, 0, sl, Brushes.Transparent, Brushes.Red, 15);
                Draw.Text(this, "orb_res" + tradeId, why, 0, why == "SL" ? sl : (why == "TP" ? tp : px), why == "TP" ? Brushes.LimeGreen : (why == "SL" ? Brushes.Red : Brushes.Gray));
            }
            inPos = false;
            Dashboard();
        }

        private void RollAdr(DateTime today)
        {
            DateTime prev = DateTime.MinValue;
            foreach (DateTime k in dayHL.Keys) if (k < today && k > prev) prev = k;
            if (prev == DateTime.MinValue) return;
            double[] hl = dayHL[prev];
            if (prev.DayOfWeek != DayOfWeek.Saturday && prev.DayOfWeek != DayOfWeek.Sunday) adrHist.Add(hl[0] - hl[1]);
            if (adrHist.Count > 500) adrHist.RemoveAt(0);
        }

        private static double Avg(List<double> v, int n) { double s = 0; for (int i = v.Count - n; i < v.Count; i++) s += v[i]; return s / n; }

        private bool DowOk(DayOfWeek d)
        {
            switch (d) { case DayOfWeek.Monday: return Mon; case DayOfWeek.Tuesday: return Tue; case DayOfWeek.Wednesday: return Wed;
                case DayOfWeek.Thursday: return Thu; case DayOfWeek.Friday: return Fri; default: return false; }
        }

        private void Dashboard()
        {
            CultureInfo ic = CultureInfo.InvariantCulture; StringBuilder sb = new StringBuilder();
            sb.AppendLine(string.Format(ic, "ORB 01:00-01:15 NY · TP {0}R · slip {1}t · com ${2}", TargetR, SlippageTicks, CommissionUsd));
            sb.AppendLine("Variante      Ops  Acierto  Neto USD   USD/op  MaxDD");
            for (int i = 0; i < NV; i++)
            {
                Stats s = st[i]; int c = s.W + s.L + s.T;
                sb.AppendLine(string.Format(ic, "{0,-12} {1,4}  {2,6:0.0}%  {3,8:0}  {4,7:0.0}  {5,6:0}", Names[i], s.N,
                    c > 0 ? 100.0 * s.W / c : 0, s.Usd, s.N > 0 ? s.Usd / s.N : 0, s.MaxDD));
            }
            sb.Append("Equilibrio con TP 0,5R: ~66,7% de acierto (sin costos)");
            Draw.TextFixed(this, "orb_dash", sb.ToString(), TextPosition.TopRight, Brushes.White, new SimpleFont("Consolas", 12),
                Brushes.Transparent, Brushes.Black, 70);
        }

        #region Properties
        [NinjaScriptProperty, Range(0, 2359), Display(Name = "Inicio rango (HHMM ET)", Order = 1, GroupName = "1. Rango")] public int RangeStartHHMM { get; set; }
        [NinjaScriptProperty, Range(0, 2359), Display(Name = "Fin rango (HHMM ET)", Order = 2, GroupName = "1. Rango")] public int RangeEndHHMM { get; set; }
        [NinjaScriptProperty, Range(0, 2359), Display(Name = "Cierre forzado (HHMM ET)", Order = 3, GroupName = "1. Rango")] public int ExitHHMM { get; set; }
        [NinjaScriptProperty, Range(0.1, 10), Display(Name = "TP en R", Order = 4, GroupName = "1. Rango")] public double TargetR { get; set; }
        [NinjaScriptProperty, Range(0, 20), Display(Name = "Slippage (ticks)", Order = 1, GroupName = "2. Costos")] public int SlippageTicks { get; set; }
        [NinjaScriptProperty, Range(0, 100), Display(Name = "Comision por operacion (USD)", Order = 2, GroupName = "2. Costos")] public double CommissionUsd { get; set; }
        [NinjaScriptProperty, Display(Name = "Usar filtro tamano de rango", Order = 1, GroupName = "3. Filtros")] public bool UseRangeSize { get; set; }
        [NinjaScriptProperty, Range(0, 100000), Display(Name = "Rango minimo (ticks)", Order = 2, GroupName = "3. Filtros")] public int MinRangeTicks { get; set; }
        [NinjaScriptProperty, Range(0, 100000), Display(Name = "Rango maximo (ticks)", Order = 3, GroupName = "3. Filtros")] public int MaxRangeTicks { get; set; }
        [NinjaScriptProperty, Display(Name = "Usar filtro lado VWAP", Order = 4, GroupName = "3. Filtros")] public bool UseVwap { get; set; }
        [NinjaScriptProperty, Display(Name = "Usar filtro EMA", Order = 5, GroupName = "3. Filtros")] public bool UseEma { get; set; }
        [NinjaScriptProperty, Range(2, 1000), Display(Name = "Periodo EMA", Order = 6, GroupName = "3. Filtros")] public int EmaPeriod { get; set; }
        [NinjaScriptProperty, Display(Name = "Usar filtro ADR", Order = 7, GroupName = "3. Filtros")] public bool UseAdr { get; set; }
        [NinjaScriptProperty, Range(1, 100), Display(Name = "Dias ADR", Order = 8, GroupName = "3. Filtros")] public int AdrDays { get; set; }
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Rango maximo (% del ADR)", Order = 9, GroupName = "3. Filtros")] public double MaxRangePctAdr { get; set; }
        [NinjaScriptProperty, Display(Name = "Usar filtro dia de la semana", Order = 10, GroupName = "3. Filtros")] public bool UseDow { get; set; }
        [NinjaScriptProperty, Display(Name = "Lunes", Order = 11, GroupName = "3. Filtros")] public bool Mon { get; set; }
        [NinjaScriptProperty, Display(Name = "Martes", Order = 12, GroupName = "3. Filtros")] public bool Tue { get; set; }
        [NinjaScriptProperty, Display(Name = "Miercoles", Order = 13, GroupName = "3. Filtros")] public bool Wed { get; set; }
        [NinjaScriptProperty, Display(Name = "Jueves", Order = 14, GroupName = "3. Filtros")] public bool Thu { get; set; }
        [NinjaScriptProperty, Display(Name = "Viernes", Order = 15, GroupName = "3. Filtros")] public bool Fri { get; set; }
        [Display(Name = "Dibujar operaciones (Seleccion)", Order = 1, GroupName = "4. Grafico")] public bool DrawTrades { get; set; }
        #endregion
    }
}
