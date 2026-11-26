#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeLabAbsorb20m (version=1.0, 2026-11-20) — módulo A20 (Absorb 20m, A20_7_2_2.5_1.5, sólo corta por defecto).
// Uso exclusivo de validación de paridad y prueba de comisiones en NinjaTrader 8. No es un edge promovido.
//
// Especificación: edgelab/research/fundedsyncstack/modulos_a1_a20_f_s.py (_run_absorb, Absorb20mConfig, run_a20).
//   Gráfico de 1 minuto de NQ o MNQ, plantilla ETH. Agrega serie secundaria de 20 minutos (BIP 1).
//   Calculate = OnBarClose.
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabAbsorb20m : Strategy
    {
        private const string SigL = "A20_L";
        private const string SigS = "A20_S";

        private TimeZoneInfo ct;
        private ATR atrInd, atrSt;
        private SMA avgVolSma;
        private MAX vpMaxHigh, rng10MaxHigh;
        private MIN vpMinLow, rng10MinLow;

        private double[] volAtPrice;
        private double[] deltaHistory;
        private int deltaIdx;
        private double prevSmoothDelta;

        private readonly bool[] absUpHist = new bool[10];
        private readonly bool[] absDownHist = new bool[10];
        private int absHistIdx;

        private readonly double[] rangeHistory = new double[60];
        private int rangeIdx;

        private double[] atrBaseHist;
        private int atrBaseIdx;

        private double orbHigh = double.NaN, orbLow = double.NaN;
        private bool orbDefined, prevInSess, prevInSessClose;
        private int sessionBarsCount;

        private double cumPv, cumVol;

        private bool stInit;
        private double prevFinalUpper, prevFinalLower, prevClose;
        private int prevTrend = 1;

        private int dailyLosses, lossCooldownRemaining, lastPerfTradeCount;
        private double pendingHardStopPx = double.NaN;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabAbsorb20m";
                Description = "A20 (Absorb 20m, StPeriod=7, StMult=2.0, sólo corta). Validación de paridad y comisiones NT8.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 60;

                Cantidad = 1;
                VpLength = 10;
                VpResolution = 24;
                AbsorbVolMult = 2.5;
                AbsorbPriceThresh = 1.9;
                DeltaLookback = 5;
                UseVwap = true;
                VwapBand = 0.5;
                MaxDailyLosses = 3;
                OrbMinutes = 30;
                UseOrb = true;
                UseRolloverFilter = true;
                RolloverDaysBefore = 10;
                RolloverDaysAfter = 1;
                UseVolatilityFilter = true;
                VolBaselineLookback = 100;
                VolRegimeMultiplier = 2.9;
                UseHardStop = true;
                HardStopAtrMult = 1.5;
                FlattenAtSessionEnd = true;
                SessionStartHour = 5;
                SessionStartMinute = 30;
                SessionEndHour = 15;
                SessionEndMinute = 0;
                AtrPeriod = 14;
                StPeriod = 7;
                StMult = 2.0;
                ExitOnStFlip = true;
                AllowLongs = false;
                AllowShorts = true;
                BlockMondayEntries = true;
                RequireSupertrendEntryAlignment = false;
                LossCooldownBars = 0;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Minute, 20);
            }
            else if (State == State.DataLoaded)
            {
                ct = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
                atrInd = ATR(Closes[1], AtrPeriod);
                atrSt = ATR(Closes[1], StPeriod);
                avgVolSma = SMA(Volumes[1], 20);
                vpMaxHigh = MAX(Highs[1], VpLength);
                vpMinLow = MIN(Lows[1], VpLength);
                rng10MaxHigh = MAX(Highs[1], 10);
                rng10MinLow = MIN(Lows[1], 10);

                volAtPrice = new double[Math.Max(1, VpResolution)];
                deltaHistory = new double[Math.Max(1, DeltaLookback)];
                atrBaseHist = new double[Math.Max(1, VolBaselineLookback)];
            }
        }

        private static DateTime ThirdFriday(int year, int month)
        {
            DateTime first = new DateTime(year, month, 1);
            int offset = ((int)DayOfWeek.Friday - (int)first.DayOfWeek + 7) % 7;
            return first.AddDays(offset + 14);
        }

        private bool IsNearRollover(DateTime d)
        {
            int[] qm = { 3, 6, 9, 12 };
            for (int dy = -1; dy <= 1; dy++)
            {
                int yy = d.Year + dy;
                foreach (int m in qm)
                {
                    DateTime tf = ThirdFriday(yy, m);
                    int diff = (d.Date - tf).Days;
                    if (diff >= -RolloverDaysBefore && diff <= RolloverDaysAfter) return true;
                }
            }
            return false;
        }

        private static bool LookupAbs(bool[] history, int barsBack, int totalCount)
        {
            if (totalCount - barsBack <= 0) return false;
            int idx = (totalCount - 1 - barsBack) % history.Length;
            return history[idx];
        }

        private void ComputeVapBands(double vpHigh, double vpLow, out double vah, out double val)
        {
            int res = Math.Max(1, VpResolution);
            double step = (vpHigh - vpLow) / res;
            if (step <= 0.0) { vah = double.NaN; val = double.NaN; return; }

            for (int b = 0; b < res; b++) volAtPrice[b] = 0.0;
            int kLimit = Math.Min(VpLength, CurrentBars[1] + 1);
            for (int k = 0; k < kLimit; k++)
            {
                int b = (int)Math.Floor((Closes[1][k] - vpLow) / step);
                if (b >= 0 && b < res) volAtPrice[b] += Volumes[1][k];
            }

            double maxBinVol = 0.0, totalVol = 0.0;
            int pocBin = 0;
            for (int b = 0; b < res; b++)
            {
                double bv = volAtPrice[b];
                totalVol += bv;
                if (bv > maxBinVol) { maxBinVol = bv; pocBin = b; }
            }

            double vaTarget = totalVol * 0.7;
            double vaVol = volAtPrice[pocBin];
            int hiBin = pocBin, loBin = pocBin;
            while (vaVol < vaTarget && (hiBin < res - 1 || loBin > 0))
            {
                double upVol = hiBin >= res - 1 ? 0.0 : volAtPrice[hiBin + 1];
                double dnVol = loBin <= 0 ? 0.0 : volAtPrice[loBin - 1];
                if (upVol >= dnVol && hiBin < res - 1) { hiBin++; vaVol += upVol; }
                else if (loBin > 0) { loBin--; vaVol += dnVol; }
            }
            vah = vpLow + hiBin * step + step;
            val = vpLow + loBin * step;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 1) return;
            if (CurrentBars[1] < BarsRequiredToTrade || CurrentBars[0] < 1) return;

            if (lossCooldownRemaining > 0) lossCooldownRemaining--;

            double curAtr = atrInd[0];
            atrBaseHist[atrBaseIdx % atrBaseHist.Length] = curAtr;
            atrBaseIdx++;
            int abCnt = Math.Min(atrBaseIdx, atrBaseHist.Length);
            double abSum = 0.0;
            for (int i = 0; i < abCnt; i++) abSum += atrBaseHist[i];
            double avgAtr = abCnt > 0 ? abSum / abCnt : curAtr;
            bool highVolRegime = avgAtr > 0.0 && curAtr > avgAtr * VolRegimeMultiplier;
            bool volFilterPass = !UseVolatilityFilter || !highVolRegime;

            if (BarsArray[1].IsFirstBarOfSession) { cumPv = 0.0; cumVol = 0.0; }
            double hi = Highs[1][0], lo = Lows[1][0], cl = Closes[1][0], op = Opens[1][0], vol = Volumes[1][0];
            double typical = (hi + lo + cl) / 3.0;
            cumPv += typical * vol; cumVol += vol;
            double vwap = cumVol > 0.0 ? (cumPv / cumVol) : typical;
            double upperVwapBand = vwap + curAtr * VwapBand;
            double lowerVwapBand = vwap - curAtr * VwapBand;

            DateTime tCt = TimeZoneInfo.ConvertTime(Times[1][0], Core.Globals.GeneralOptions.TimeZoneInfo, ct);
            int minuteOfDay = tCt.Hour * 60 + tCt.Minute;
            int sessStart = SessionStartHour * 60 + SessionStartMinute;
            int sessEnd = SessionEndHour * 60 + SessionEndMinute;
            bool inSession = minuteOfDay >= sessStart && minuteOfDay < sessEnd;
            bool enteredSession = inSession && !prevInSess;
            bool exitedSession = !inSession && prevInSessClose;
            prevInSess = inSession;
            prevInSessClose = inSession;

            if (enteredSession)
            {
                dailyLosses = 0;
                orbHigh = double.NaN; orbLow = double.NaN; orbDefined = false;
                sessionBarsCount = -1;
            }

            if (FlattenAtSessionEnd && exitedSession && Position.MarketPosition != MarketPosition.Flat)
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong(0, "SESSION", SigL);
                else ExitShort(0, "SESSION", SigS);
            }

            double vah, val;
            ComputeVapBands(vpMaxHigh[0], vpMinLow[0], out vah, out val);

            double buyVol;
            if (cl > op) buyVol = vol;
            else if (cl == op) buyVol = vol * 0.5;
            else buyVol = vol * ((hi - cl) / ((hi - lo) + 0.0001));
            double barDelta = buyVol - (vol - buyVol);

            deltaHistory[deltaIdx % deltaHistory.Length] = barDelta;
            deltaIdx++;
            int dCnt = Math.Min(deltaIdx, deltaHistory.Length);
            double dSum = 0.0;
            for (int i = 0; i < dCnt; i++) dSum += deltaHistory[i];
            double smoothDelta = dCnt > 0 ? dSum / dCnt : 0.0;
            bool deltaShiftUp = smoothDelta > 0.0 && smoothDelta > prevSmoothDelta;
            bool deltaShiftDown = smoothDelta < 0.0 && smoothDelta < prevSmoothDelta;
            prevSmoothDelta = smoothDelta;

            double avgVol = avgVolSma[0];
            double bodyAtrRatio = Math.Abs(cl - op) / (curAtr > 0.0 ? curAtr : 1.0);
            bool isAbsorption = (vol > avgVol * AbsorbVolMult) && (bodyAtrRatio < AbsorbPriceThresh);
            bool absUp = isAbsorption && cl > op;
            bool absDown = isAbsorption && cl < op;

            int absSlot = absHistIdx % 10;
            absUpHist[absSlot] = absUp;
            absDownHist[absSlot] = absDown;
            absHistIdx++;

            double range10 = rng10MaxHigh[0] - rng10MinLow[0];
            rangeHistory[rangeIdx % 60] = range10;
            rangeIdx++;
            int rCnt = Math.Min(rangeIdx, 60);
            double rSum = 0.0;
            for (int i = 0; i < rCnt; i++) rSum += rangeHistory[i];
            double avgRange10 = rCnt > 0 ? rSum / rCnt : range10;
            bool isTightRange = range10 < avgRange10 * 0.6;
            bool isWideClimax = (range10 > avgRange10 * 1.2) && (vol > avgVol * 1.5);
            bool climaxLong = isWideClimax && cl > op && smoothDelta > 0.0;
            bool climaxShort = isWideClimax && cl < op && smoothDelta < 0.0;

            bool recentAbsUp = LookupAbs(absUpHist, 3, absHistIdx) || LookupAbs(absUpHist, 4, absHistIdx) || LookupAbs(absUpHist, 5, absHistIdx);
            bool recentAbsDown = LookupAbs(absDownHist, 3, absHistIdx) || LookupAbs(absDownHist, 4, absHistIdx) || LookupAbs(absDownHist, 5, absHistIdx);
            bool absClimaxLong = recentAbsUp && isTightRange && climaxLong;
            bool absClimaxShort = recentAbsDown && isTightRange && climaxShort;

            if (inSession)
            {
                sessionBarsCount++;
                int orbBars = Math.Max(1, OrbMinutes / 20);
                if (sessionBarsCount <= orbBars)
                {
                    orbHigh = double.IsNaN(orbHigh) ? hi : Math.Max(orbHigh, hi);
                    orbLow = double.IsNaN(orbLow) ? lo : Math.Min(orbLow, lo);
                    orbDefined = (sessionBarsCount == orbBars);
                }
            }

            double prevCl = CurrentBars[1] > 0 ? Closes[1][1] : cl;
            bool orbLong = UseOrb && orbDefined && (cl > orbHigh) && !(prevCl > orbHigh);
            bool orbShort = UseOrb && orbDefined && (cl < orbLow) && !(prevCl < orbLow);

            bool nearVal = !double.IsNaN(val) && lo <= val * 1.001 && lo >= val * 0.999;
            bool nearVah = !double.IsNaN(vah) && hi >= vah * 0.999 && hi <= vah * 1.001;
            bool vpLong = nearVal && absUp && deltaShiftUp;
            bool vpShort = nearVah && absDown && deltaShiftDown;

            bool rolloverOk = !UseRolloverFilter || !IsNearRollover(tCt.Date);
            bool longSig = (absClimaxLong || orbLong || vpLong) && (!UseVwap || cl > lowerVwapBand);
            bool shortSig = (absClimaxShort || orbShort || vpShort) && (!UseVwap || cl < upperVwapBand);
            bool envOk = rolloverOk && volFilterPass;
            bool dailyLossOk = dailyLosses < MaxDailyLosses;
            bool canTradeCooldown = lossCooldownRemaining <= 0;

            // SuperTrend step
            double hl2 = 0.5 * (hi + lo);
            double basicUpper = hl2 + StMult * atrSt[0];
            double basicLower = hl2 - StMult * atrSt[0];
            double finalUpper, finalLower;
            int trend;
            if (!stInit)
            {
                finalUpper = basicUpper;
                finalLower = basicLower;
                trend = cl < basicLower ? -1 : 1;
                stInit = true;
            }
            else
            {
                finalUpper = (basicUpper < prevFinalUpper || prevClose > prevFinalUpper) ? basicUpper : prevFinalUpper;
                finalLower = (basicLower > prevFinalLower || prevClose < prevFinalLower) ? basicLower : prevFinalLower;
                if (prevTrend == -1 && cl > prevFinalUpper) trend = 1;
                else if (prevTrend == 1 && cl < prevFinalLower) trend = -1;
                else trend = prevTrend;
            }
            bool stFlipUp = (trend == 1 && prevTrend == -1);
            bool stFlipDown = (trend == -1 && prevTrend == 1);
            bool stAlignLong = !RequireSupertrendEntryAlignment || trend == 1;
            bool stAlignShort = !RequireSupertrendEntryAlignment || trend == -1;

            bool mondayOk = !BlockMondayEntries || tCt.DayOfWeek != DayOfWeek.Monday;

            if (ExitOnStFlip && Position.MarketPosition == MarketPosition.Long && stFlipDown)
                ExitLong(0, "ST", SigL);
            else if (ExitOnStFlip && Position.MarketPosition == MarketPosition.Short && stFlipUp)
                ExitShort(0, "ST", SigS);

            if (AllowLongs && longSig && envOk && dailyLossOk && canTradeCooldown && stAlignLong && mondayOk
                && Position.MarketPosition == MarketPosition.Flat)
            {
                pendingHardStopPx = UseHardStop ? Instrument.MasterInstrument.RoundToTickSize(cl - HardStopAtrMult * curAtr) : double.NaN;
                Print(string.Format("A20;SENAL;L;{0:yyyy-MM-dd HH:mm};sl={1:F2}", tCt, pendingHardStopPx));
                EnterLong(0, Cantidad, SigL);
            }
            else if (AllowShorts && shortSig && envOk && dailyLossOk && canTradeCooldown && stAlignShort && mondayOk
                && Position.MarketPosition == MarketPosition.Flat)
            {
                pendingHardStopPx = UseHardStop ? Instrument.MasterInstrument.RoundToTickSize(cl + HardStopAtrMult * curAtr) : double.NaN;
                Print(string.Format("A20;SENAL;S;{0:yyyy-MM-dd HH:mm};sl={1:F2}", tCt, pendingHardStopPx));
                EnterShort(0, Cantidad, SigS);
            }

            prevFinalUpper = finalUpper;
            prevFinalLower = finalLower;
            prevClose = cl;
            prevTrend = trend;
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (SystemPerformance.AllTrades.Count > lastPerfTradeCount)
            {
                for (int i = lastPerfTradeCount; i < SystemPerformance.AllTrades.Count; i++)
                {
                    if (SystemPerformance.AllTrades[i].ProfitCurrency < 0)
                    {
                        dailyLosses++;
                        if (LossCooldownBars > 0) lossCooldownRemaining = LossCooldownBars;
                    }
                }
                lastPerfTradeCount = SystemPerformance.AllTrades.Count;
            }

            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            string n = execution.Order.Name;
            if (n != SigL && n != SigS) return;

            if (!double.IsNaN(pendingHardStopPx))
            {
                double fillPx = execution.Order.AverageFillPrice;
                int q = execution.Order.Filled;
                bool isLong = (n == SigL);
                if (isLong)
                {
                    if (fillPx <= pendingHardStopPx) ExitLong(0, "STOP_OPEN", SigL);
                    else ExitLongStopMarket(0, true, q, pendingHardStopPx, "A20_stop", SigL);
                }
                else
                {
                    if (fillPx >= pendingHardStopPx) ExitShort(0, "STOP_OPEN", SigS);
                    else ExitShortStopMarket(0, true, q, pendingHardStopPx, "A20_stop", SigS);
                }
            }
        }

        #region Properties
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Cantidad contratos", Order = 1, GroupName = "A20")]
        public int Cantidad { get; set; }
        [NinjaScriptProperty, Display(Name = "AllowLongs (false en fábrica A20)", Order = 2, GroupName = "A20")]
        public bool AllowLongs { get; set; }
        [NinjaScriptProperty, Display(Name = "AllowShorts (true en fábrica A20)", Order = 3, GroupName = "A20")]
        public bool AllowShorts { get; set; }
        [NinjaScriptProperty, Range(1, 50), Display(Name = "StPeriod (7)", Order = 4, GroupName = "A20")]
        public int StPeriod { get; set; }
        [NinjaScriptProperty, Range(0.5, 10), Display(Name = "StMult (2.0)", Order = 5, GroupName = "A20")]
        public double StMult { get; set; }
        [NinjaScriptProperty, Range(0.5, 10), Display(Name = "AbsorbVolMult (2.5)", Order = 6, GroupName = "A20")]
        public double AbsorbVolMult { get; set; }
        [NinjaScriptProperty, Range(0.5, 10), Display(Name = "AbsorbPriceThresh (1.9)", Order = 7, GroupName = "A20")]
        public double AbsorbPriceThresh { get; set; }
        [NinjaScriptProperty, Display(Name = "UseHardStop (true)", Order = 8, GroupName = "A20")]
        public bool UseHardStop { get; set; }
        [NinjaScriptProperty, Range(0.1, 10), Display(Name = "HardStopAtrMult (1.5)", Order = 9, GroupName = "A20")]
        public double HardStopAtrMult { get; set; }
        [NinjaScriptProperty, Display(Name = "BlockMondayEntries (true)", Order = 10, GroupName = "A20")]
        public bool BlockMondayEntries { get; set; }
        [NinjaScriptProperty, Display(Name = "ExitOnStFlip (true)", Order = 11, GroupName = "A20")]
        public bool ExitOnStFlip { get; set; }
        [NinjaScriptProperty, Range(1, 20), Display(Name = "MaxDailyLosses (3)", Order = 12, GroupName = "A20")]
        public int MaxDailyLosses { get; set; }
        [NinjaScriptProperty, Display(Name = "UseRolloverFilter (true)", Order = 13, GroupName = "A20")]
        public bool UseRolloverFilter { get; set; }
        [NinjaScriptProperty, Display(Name = "UseVolatilityFilter (true)", Order = 14, GroupName = "A20")]
        public bool UseVolatilityFilter { get; set; }
        [NinjaScriptProperty, Display(Name = "UseOrb (true)", Order = 15, GroupName = "A20")]
        public bool UseOrb { get; set; }
        [NinjaScriptProperty, Display(Name = "UseVwap (true)", Order = 16, GroupName = "A20")]
        public bool UseVwap { get; set; }
        [NinjaScriptProperty, Range(2, 50), Display(Name = "AtrPeriod", Order = 17, GroupName = "A20")]
        public int AtrPeriod { get; set; }
        [NinjaScriptProperty, Range(2, 50), Display(Name = "VpLength", Order = 18, GroupName = "A20")]
        public int VpLength { get; set; }
        [NinjaScriptProperty, Range(4, 100), Display(Name = "VpResolution", Order = 19, GroupName = "A20")]
        public int VpResolution { get; set; }
        [NinjaScriptProperty, Range(1, 50), Display(Name = "DeltaLookback", Order = 20, GroupName = "A20")]
        public int DeltaLookback { get; set; }
        [NinjaScriptProperty, Range(0, 5), Display(Name = "VwapBand", Order = 21, GroupName = "A20")]
        public double VwapBand { get; set; }
        [NinjaScriptProperty, Range(5, 120), Display(Name = "OrbMinutes", Order = 22, GroupName = "A20")]
        public int OrbMinutes { get; set; }
        [NinjaScriptProperty, Range(0, 30), Display(Name = "RolloverDaysBefore", Order = 23, GroupName = "A20")]
        public int RolloverDaysBefore { get; set; }
        [NinjaScriptProperty, Range(0, 30), Display(Name = "RolloverDaysAfter", Order = 24, GroupName = "A20")]
        public int RolloverDaysAfter { get; set; }
        [NinjaScriptProperty, Range(10, 500), Display(Name = "VolBaselineLookback", Order = 25, GroupName = "A20")]
        public int VolBaselineLookback { get; set; }
        [NinjaScriptProperty, Range(0.5, 10), Display(Name = "VolRegimeMultiplier", Order = 26, GroupName = "A20")]
        public double VolRegimeMultiplier { get; set; }
        [NinjaScriptProperty, Display(Name = "FlattenAtSessionEnd", Order = 27, GroupName = "A20")]
        public bool FlattenAtSessionEnd { get; set; }
        [NinjaScriptProperty, Range(0, 23), Display(Name = "SessionStartHour CT", Order = 28, GroupName = "A20")]
        public int SessionStartHour { get; set; }
        [NinjaScriptProperty, Range(0, 59), Display(Name = "SessionStartMinute CT", Order = 29, GroupName = "A20")]
        public int SessionStartMinute { get; set; }
        [NinjaScriptProperty, Range(0, 23), Display(Name = "SessionEndHour CT", Order = 30, GroupName = "A20")]
        public int SessionEndHour { get; set; }
        [NinjaScriptProperty, Range(0, 59), Display(Name = "SessionEndMinute CT", Order = 31, GroupName = "A20")]
        public int SessionEndMinute { get; set; }
        [NinjaScriptProperty, Display(Name = "RequireSupertrendEntryAlignment", Order = 32, GroupName = "A20")]
        public bool RequireSupertrendEntryAlignment { get; set; }
        [NinjaScriptProperty, Range(0, 100), Display(Name = "LossCooldownBars", Order = 33, GroupName = "A20")]
        public int LossCooldownBars { get; set; }
        #endregion
    }
}

