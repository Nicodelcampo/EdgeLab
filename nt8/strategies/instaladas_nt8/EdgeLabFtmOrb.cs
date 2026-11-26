#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeLabFtmOrb (version=1.0, 2026-11-20) — módulo T (FtmOrb / FtmEngine, NQ).
// Uso exclusivo de validación de paridad y prueba de comisiones en NinjaTrader 8. No es un edge promovido.
//
// Especificación: edgelab/research/fundedsyncstack/modulos_w_n_t.py (FtmConfig, run_t).
//   Gráfico de 1 minuto de NQ o MNQ, plantilla ETH. Calculate = OnBarClose.
//   Requiere histórico suficiente para calentar el KNN trimestral (desde 2010/2012 con KnnMinTrainingRows=100 por defecto;
//   las fechas/mínimos son configurables en propiedades para pruebas en ventanas más cortas).
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabFtmOrb : Strategy
    {
        private const string SigL = "T_L";
        private const string SigS = "T_S";
        private const double TwoPi = 6.2831853071795862;

        private static readonly HashSet<int> RollExclusions = new HashSet<int>
        {
            20200311, 20200610, 20200909, 20210609, 20210908, 20220608, 20220907, 20260611
        };

        private static readonly HashSet<int> DegradedExclusions = new HashSet<int>
        {
            20200227, 20200228, 20200630, 20200701, 20200702, 20211206, 20220103, 20240918,
            20240919, 20250917, 20250918, 20250924, 20250925, 20251128, 20260316, 20260317,
            20260410, 20260525, 20260730, 20260731
        };

        private class TrainingRow
        {
            public int SessionKey;
            public double[] Features;
            public bool FlipWins;
            public int Sequence;
        }

        private class QuarterModel
        {
            public double[][] TrainXStd;
            public bool[] TrainFlip;
            public int[] TrainSeq;
            public double[] Means;
            public double[] Scales;
        }

        private class ShadowTrade
        {
            public int Side;
            public double Entry;
            public double ActiveStop;
            public double Target;
            public double RiskPoints;
            public double ManagedTriggerR;
            public double ManagedLockR;
            public bool Complete;
            public bool PendingConditionalExit;
            public double ExitPrice;
        }

        private class ShadowPair
        {
            public int SessionKey;
            public DateTime ExpectedFillOpenUtc;
            public int BaselineSide;
            public double[] Features;
            public bool PriorTrendAvail;
            public double PriorTrendBps;
            public bool Initialized;
            public bool Invalid;
            public bool LabelRecorded;
            public ShadowTrade Breakout;
            public ShadowTrade Fade;
        }

        private class PendingDecision
        {
            public DateTime ExpectedObsOpenUtc;
            public int DirectionSide;
            public int RequiredObsBars;
            public bool SubmitActualOrder;
            public string Branch;
            public string DirectionSource;
            public int BaselineSide;
            public double[] Features;
            public double SignalClose;
            public int ObservedBars;
            public double FirstObsOpen;
        }

        private class PendingFinalDecision
        {
            public DateTime ExpectedObsOpenUtc;
            public int RefinedSide;
            public int RequiredObsBars;
            public bool SubmitActualOrder;
            public string Branch;
            public string DirectionSource;
            public string RefinementPath;
            public int ObservedBars;
            public double FirstObsOpen;
        }

        private TimeZoneInfo ct, et;

        // Estado persistente inter-sesión
        private readonly List<double> eligibleOrbHistoryBps = new List<double>();
        private readonly List<double> eligibleRthCloseHistory = new List<double>();
        private readonly List<double> eligibleSessionRetBps = new List<double>();
        private readonly List<TrainingRow> trainingRows = new List<TrainingRow>();
        private int trainingSequence;
        private int activeQuarterKey;
        private QuarterModel activeQuarterModel;

        // Estado diario
        private int currentCashDate = -1, prevDayOfCash = -1;
        private bool sessionDateEligible, refOpenCaptured, dayBlocked = true, orbFinalized, breakoutConsumed;
        private bool cashExitTriggered, cashWindowIntegrity, orbHistoryRecorded, rthCloseHistoryRecorded;
        private double refSessionOpen;
        private int orbBarCount, expectedNextOrbOpenMin;
        private double orbHigh, orbLow, orbOpen, orbClose;
        private double currentOrbBps, currentPriorOrbQ75Bps, currentPriorTrendBps;
        private bool currentPriorOrbQ75Avail, currentPriorTrendAvail;

        private readonly List<double> currentRthMinuteCloses = new List<double>();
        private double currentRthTypVolSum, currentRthVolSum;
        private DateTime lastCashBarCloseUtc = DateTime.MinValue;

        // Gestión activa
        private int activeStopTicks, activeTargetTicks;
        private double activeTriggerR, activeLockR, activeStopDist, activeTargetDist;
        private double liveStopPx = double.NaN, liveTargetPx = double.NaN;
        private bool managedStopActivated, conditionalExitRequested;
        private bool pendingSubmit;
        private int pendingSubmitSide;

        private ShadowPair activeShadowPair;
        private PendingDecision pendingDecision;
        private PendingFinalDecision pendingFinalDecision;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabFtmOrb";
                Description = "T (FtmOrb / FtmEngine): ORB 09:30-09:45 ET + KNN trimestral + refino 2 etapas. Paridad y comisiones NT8.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 20;

                Cantidad = 1;
                UseExclusionCalendars = true;
                ShadowMinSessionDate = 20100101;
                KnnMinSessionDate = 20120101;
                PortfolioStartCashDate = 20120101;
                KnnMinTrainingRows = 100;
                KnnK = 15;
                KnnFlipProbThreshold = 0.65;
            }
            else if (State == State.DataLoaded)
            {
                ct = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
            }
        }

        private double RoundTick(double px) { return Math.Round(px / TickSize) * TickSize; }
        private static double SafeRetBps(double num, double den) { return den == 0.0 ? 0.0 : (num / den - 1.0) * 10000.0; }

        private static double LagRetBps(List<double> vals, int periods)
        {
            if (vals.Count <= periods) return 0.0;
            double den = vals[vals.Count - 1 - periods];
            return den == 0.0 ? 0.0 : SafeRetBps(vals[vals.Count - 1], den);
        }

        private static double LinearPercentile(List<double> vals, double q)
        {
            double[] arr = vals.ToArray();
            Array.Sort(arr);
            double pos = (arr.Length - 1) * q;
            int lo = (int)Math.Floor(pos);
            int hi = (int)Math.Ceiling(pos);
            if (lo == hi) return arr[lo];
            return arr[lo] + (arr[hi] - arr[lo]) * (pos - lo);
        }

        private int RoundPriceOffsetTicks(double points, bool priceBelowEntry)
        {
            double ticks = points / TickSize;
            return priceBelowEntry ? (int)Math.Ceiling(ticks - 0.5) : (int)Math.Floor(ticks + 0.5);
        }

        private static int DateToKey(DateTime d) { return d.Year * 10000 + d.Month * 100 + d.Day; }
        private static DateTime KeyToDate(int key) { return new DateTime(key / 10000, (key / 100) % 100, key % 100); }

        private void InvalidatePending()
        {
            pendingDecision = null;
            pendingFinalDecision = null;
            activeShadowPair = null;
        }

        private void BlockCashDate()
        {
            cashWindowIntegrity = false;
            dayBlocked = true;
            breakoutConsumed = true;
        }

        private void RequestAdminExit(string reason)
        {
            pendingSubmit = false;
            if (Position.MarketPosition == MarketPosition.Long) ExitLong(0, reason, SigL);
            else if (Position.MarketPosition == MarketPosition.Short) ExitShort(0, reason, SigS);
        }

        private void BeginCashDate(int cashKey)
        {
            bool hasExposure = (Position.MarketPosition != MarketPosition.Flat) || pendingSubmit;
            InvalidatePending();

            currentCashDate = cashKey;
            DateTime dCash = KeyToDate(cashKey);
            prevDayOfCash = DateToKey(dCash.AddDays(-1));

            sessionDateEligible = true;
            refOpenCaptured = false;
            refSessionOpen = 0.0;
            dayBlocked = hasExposure;
            orbFinalized = false;
            breakoutConsumed = hasExposure;
            cashExitTriggered = false;
            cashWindowIntegrity = false;
            orbHistoryRecorded = false;
            rthCloseHistoryRecorded = false;

            activeStopTicks = 0; activeTargetTicks = 0;
            managedStopActivated = false; conditionalExitRequested = false;
            orbBarCount = 0; expectedNextOrbOpenMin = 570;
            orbHigh = double.NegativeInfinity; orbLow = double.PositiveInfinity;
            orbOpen = 0.0; orbClose = 0.0;
            currentOrbBps = 0.0; currentPriorOrbQ75Bps = 0.0; currentPriorOrbQ75Avail = false;

            if (eligibleRthCloseHistory.Count >= 21)
            {
                double oldest = eligibleRthCloseHistory[0];
                double newest = eligibleRthCloseHistory[eligibleRthCloseHistory.Count - 1];
                if (oldest > 0.0 && newest > 0.0)
                {
                    currentPriorTrendBps = SafeRetBps(newest, oldest);
                    currentPriorTrendAvail = true;
                }
                else { currentPriorTrendBps = 0.0; currentPriorTrendAvail = false; }
            }
            else { currentPriorTrendBps = 0.0; currentPriorTrendAvail = false; }

            currentRthMinuteCloses.Clear();
            currentRthTypVolSum = 0.0;
            currentRthVolSum = 0.0;
            lastCashBarCloseUtc = DateTime.MinValue;
            activeTriggerR = 0.0; activeLockR = 0.0;

            if (hasExposure) { RequestAdminExit("OvernightExposure"); return; }

            if (dCash.DayOfWeek == DayOfWeek.Saturday || dCash.DayOfWeek == DayOfWeek.Sunday)
            {
                sessionDateEligible = false; dayBlocked = true; return;
            }
            if (UseExclusionCalendars && (DegradedExclusions.Contains(cashKey) || RollExclusions.Contains(cashKey)))
            {
                sessionDateEligible = false; dayBlocked = true; return;
            }

            cashWindowIntegrity = true;
        }

        private void SelectManagementPlan(int side, bool priorTrendAvail, double priorTrendBps,
            bool priorOrbQ75Avail, double curOrbBps, double priorOrbQ75Bps,
            out double targetR, out double triggerR, out double lockR)
        {
            bool highOrb = priorOrbQ75Avail && (curOrbBps > priorOrbQ75Bps);
            bool countertrend = priorTrendAvail && ((side * priorTrendBps) < 0.0);
            if (highOrb) { targetR = 1.25; triggerR = 1.25; lockR = 0.0; return; }
            if (countertrend) { targetR = 3.0; triggerR = 0.75; lockR = 0.10; return; }
            targetR = 3.0; triggerR = 1.25; lockR = 0.0;
        }

        private ShadowTrade CreateShadowTrade(int side, double parentFillOpen, bool priorTrendAvail, double priorTrendBps)
        {
            double entryPx = parentFillOpen + side * TickSize;
            double rawDist = Math.Max(2.0, Math.Min(100.0, (orbHigh - orbLow) * 1.25));
            double stopPx = RoundTick(entryPx - side * rawDist);
            double riskPts = side * (entryPx - stopPx);
            double tR, trigR, lockR;
            SelectManagementPlan(side, priorTrendAvail, priorTrendBps, currentPriorOrbQ75Avail, currentOrbBps, currentPriorOrbQ75Bps,
                out tR, out trigR, out lockR);
            double targetPx = RoundTick(entryPx + side * rawDist * tR);
            ShadowTrade st = new ShadowTrade
            {
                Side = side, Entry = entryPx, ActiveStop = stopPx, Target = targetPx,
                RiskPoints = riskPts, ManagedTriggerR = trigR, ManagedLockR = lockR
            };
            if (!(riskPts > 0.0)) { st.Complete = true; st.ExitPrice = entryPx; }
            return st;
        }

        private void ProcessShadowBar(ShadowTrade st, int closeMin)
        {
            if (st.Complete) return;
            double op = Open[0], hi = High[0], lo = Low[0], cl = Close[0];

            if (st.PendingConditionalExit)
            {
                st.ExitPrice = op - st.Side * TickSize;
                st.Complete = true;
                st.PendingConditionalExit = false;
                return;
            }

            bool stopHit = st.Side == 1 ? (lo <= st.ActiveStop) : (hi >= st.ActiveStop);
            bool tgtHit = st.Side == 1 ? (hi >= st.Target) : (lo <= st.Target);

            if (stopHit)
            {
                double fillStop = st.Side == 1 ? Math.Min(st.ActiveStop, op) : Math.Max(st.ActiveStop, op);
                st.ExitPrice = fillStop - st.Side * TickSize;
                st.Complete = true; st.PendingConditionalExit = false; return;
            }
            if (tgtHit)
            {
                double fillTgt = st.Side == 1 ? Math.Max(st.Target, op) : Math.Min(st.Target, op);
                st.ExitPrice = fillTgt;
                st.Complete = true; st.PendingConditionalExit = false; return;
            }

            if (closeMin < 960 && (closeMin % 15) == 0)
            {
                double closeR = st.Side * (cl - st.Entry) / st.RiskPoints;
                if (closeR >= st.ManagedTriggerR)
                {
                    double newStop = RoundTick(st.Entry + st.Side * st.RiskPoints * st.ManagedLockR);
                    st.ActiveStop = st.Side == 1 ? Math.Max(st.ActiveStop, newStop) : Math.Min(st.ActiveStop, newStop);
                }
                if (closeMin == 930 && (closeR < 0.0 || closeR >= 1.0))
                    st.PendingConditionalExit = true;
            }
        }

        private void TryRecordShadowLabel()
        {
            ShadowPair sp = activeShadowPair;
            if (sp == null || sp.Invalid || sp.LabelRecorded || !sp.Initialized || sp.Breakout == null || sp.Fade == null) return;
            if (!sp.Breakout.Complete || !sp.Fade.Complete) return;

            double brkNet = sp.Breakout.Side * (sp.Breakout.ExitPrice - sp.Breakout.Entry) * 20.0 - 2.5;
            double fadeNet = sp.Fade.Side * (sp.Fade.ExitPrice - sp.Fade.Entry) * 20.0 - 2.5;
            bool flipWins = fadeNet > 0.0;
            bool exclusive = (brkNet > 0.0) != flipWins;
            if (exclusive)
            {
                trainingRows.Add(new TrainingRow
                {
                    SessionKey = sp.SessionKey,
                    Features = (double[])sp.Features.Clone(),
                    FlipWins = flipWins,
                    Sequence = trainingSequence++
                });
            }
            sp.LabelRecorded = true;
            activeShadowPair = null;
        }

        private QuarterModel FitQuarterModel(int cutoffKey)
        {
            List<TrainingRow> elig = new List<TrainingRow>();
            foreach (TrainingRow r in trainingRows)
                if (r.SessionKey >= ShadowMinSessionDate && r.SessionKey <= cutoffKey) elig.Add(r);

            int minRows = Math.Max(KnnMinTrainingRows, KnnK);
            if (elig.Count < minRows) return null;

            int m = elig.Count;
            double[] means = new double[14];
            for (int r = 0; r < m; r++)
                for (int f = 0; f < 14; f++) means[f] += elig[r].Features[f];
            for (int f = 0; f < 14; f++) means[f] /= m;

            double[] scales = new double[14];
            for (int r = 0; r < m; r++)
                for (int f = 0; f < 14; f++)
                {
                    double d = elig[r].Features[f] - means[f];
                    scales[f] += d * d;
                }
            for (int f = 0; f < 14; f++)
            {
                double sd = Math.Sqrt(scales[f] / m);
                scales[f] = sd > 0.0 ? sd : 1.0;
            }

            double[][] xStd = new double[m][];
            bool[] flips = new bool[m];
            int[] seqs = new int[m];
            for (int r = 0; r < m; r++)
            {
                double[] row = new double[14];
                for (int f = 0; f < 14; f++) row[f] = (elig[r].Features[f] - means[f]) / scales[f];
                xStd[r] = row;
                flips[r] = elig[r].FlipWins;
                seqs[r] = elig[r].Sequence;
            }

            return new QuarterModel { TrainXStd = xStd, TrainFlip = flips, TrainSeq = seqs, Means = means, Scales = scales };
        }

        private bool PredictKnn(QuarterModel model, double[] features, out double flipProb)
        {
            flipProb = 0.0;
            if (model == null) return false;

            double[] fz = new double[14];
            for (int f = 0; f < 14; f++) fz[f] = (features[f] - model.Means[f]) / model.Scales[f];

            int m = model.TrainXStd.Length;
            int[] order = new int[m];
            double[] dists = new double[m];
            for (int r = 0; r < m; r++)
            {
                order[r] = r;
                double s2 = 0.0;
                double[] tr = model.TrainXStd[r];
                for (int f = 0; f < 14; f++) { double d = tr[f] - fz[f]; s2 += d * d; }
                dists[r] = Math.Sqrt(s2);
            }

            Array.Sort(order, (a, b) =>
            {
                int c = dists[a].CompareTo(dists[b]);
                return c != 0 ? c : model.TrainSeq[a].CompareTo(model.TrainSeq[b]);
            });

            int flipNeighbors = 0;
            for (int k = 0; k < KnnK; k++)
                if (model.TrainFlip[order[k]]) flipNeighbors++;

            flipProb = (flipNeighbors + 2.0) / (KnnK + 4.0);
            return true;
        }

        private void SubmitActualEntry(int side, string dirSrc, string refPath)
        {
            if (Position.MarketPosition != MarketPosition.Flat || pendingSubmit) return;
            bool isLong = (side == 1);
            double rawDist = Math.Max(2.0, Math.Min(100.0, (orbHigh - orbLow) * 1.25));
            int stopTicks = RoundPriceOffsetTicks(rawDist, isLong);
            double targetR, trigR, lockR;
            SelectManagementPlan(side, currentPriorTrendAvail, currentPriorTrendBps, currentPriorOrbQ75Avail, currentOrbBps, currentPriorOrbQ75Bps,
                out targetR, out trigR, out lockR);
            int targetTicks = RoundPriceOffsetTicks(rawDist * targetR, !isLong);

            activeStopTicks = stopTicks;
            activeTargetTicks = targetTicks;
            activeTriggerR = trigR;
            activeLockR = lockR;
            activeStopDist = stopTicks * TickSize;
            activeTargetDist = targetTicks * TickSize;
            managedStopActivated = false;
            conditionalExitRequested = false;
            pendingSubmit = true;
            pendingSubmitSide = side;

            Print(string.Format("T;SENAL;{0};{1};orb={2:F2};sl_t={3};tp_t={4};{5}|{6}",
                currentCashDate, side, orbHigh - orbLow, stopTicks, targetTicks, dirSrc, refPath));
            if (isLong) EnterLong(0, Cantidad, SigL);
            else EnterShort(0, Cantidad, SigS);
        }

        private void ApplyFinalRefinementOrSubmit(int refinedSide, DateTime refFillOpenUtc, string dirSrc,
            string refPath, bool submitActual, int baselineSide, double[] features, double sigClose)
        {
            double orbRange = orbHigh - orbLow;
            if (!(orbRange > 0.0) || features.Length != 14) { dayBlocked = true; return; }

            double signFlip = refinedSide * baselineSide;
            double alignedPrior = signFlip * features[1];
            double alignedRet30 = signFlip * features[5];
            double orbBody = refinedSide * (orbClose - orbOpen) / orbRange;
            double breakoutEdge = refinedSide == 1 ? orbHigh : orbLow;
            double sigExt = refinedSide * (sigClose - breakoutEdge) / orbRange;

            bool priorDisagree = (alignedPrior > 100.0) && !(orbBody > 0.0);
            bool intradayCont = (alignedRet30 > 25.0) && !(sigExt > 0.25);

            string branch;
            int reqBars;
            if (priorDisagree) { branch = "prior_session_disagreement"; reqBars = 2; }
            else if (intradayCont) { branch = "intraday_continuation"; reqBars = 1; }
            else
            {
                if (submitActual) SubmitActualEntry(refinedSide, dirSrc, refPath + "->entry_condition_not_met");
                return;
            }

            pendingFinalDecision = new PendingFinalDecision
            {
                ExpectedObsOpenUtc = refFillOpenUtc,
                RefinedSide = refinedSide,
                RequiredObsBars = reqBars,
                SubmitActualOrder = submitActual,
                Branch = branch,
                DirectionSource = dirSrc,
                RefinementPath = refPath
            };
        }

        private void EvaluateAdmissionAndDirection(int baselineSide, DateTime cUtc, int cMinEt)
        {
            if (CurrentBar < 14) { breakoutConsumed = true; BlockCashDate(); InvalidatePending(); return; }

            double sigOpen = Open[14];
            double sigHigh = double.NegativeInfinity, sigLow = double.PositiveInfinity;
            for (int k = 0; k < 15; k++)
            {
                DateTime tCloseK = TimeZoneInfo.ConvertTime(Times[0][k], Core.Globals.GeneralOptions.TimeZoneInfo, TimeZoneInfo.Utc);
                if (tCloseK != cUtc.AddMinutes(-k)) { breakoutConsumed = true; BlockCashDate(); InvalidatePending(); return; }
                sigHigh = Math.Max(sigHigh, High[k]);
                sigLow = Math.Min(sigLow, Low[k]);
            }
            if (!(sigHigh > sigLow)) { breakoutConsumed = true; BlockCashDate(); InvalidatePending(); return; }
            double sigClose = Close[0];

            double sigRange = sigHigh - sigLow;
            double body = baselineSide * (sigClose - sigOpen) / sigRange;
            double closeLoc = baselineSide == 1 ? (sigClose - sigLow) / sigRange : (sigHigh - sigClose) / sigRange;
            if (body < 0.15 || closeLoc < 0.60) return;

            double confLevel = baselineSide == 1 ? (orbHigh + TickSize) : (orbLow - TickSize);
            int admTouches = 0;
            for (int k = 0; k < 15; k++)
            {
                if (baselineSide == 1) { if (High[k] >= confLevel) admTouches++; }
                else { if (Low[k] <= confLevel) admTouches++; }
            }
            if (admTouches < 3) { breakoutConsumed = true; return; }

            if (!(orbOpen > 0.0 && orbClose > 0.0 && currentRthVolSum > 0.0) || currentRthMinuteCloses.Count == 0)
            {
                breakoutConsumed = true; BlockCashDate(); InvalidatePending(); return;
            }

            double prevRthClose = eligibleRthCloseHistory.Count > 0 ? eligibleRthCloseHistory[eligibleRthCloseHistory.Count - 1] : orbOpen;
            double priorSessBps = eligibleSessionRetBps.Count > 0 ? eligibleSessionRetBps[eligibleSessionRetBps.Count - 1] : 0.0;
            double priorRet5Bps = LagRetBps(eligibleRthCloseHistory, 5);
            double priorRet20Bps = LagRetBps(eligibleRthCloseHistory, 20);
            double rthVwap = currentRthTypVolSum / currentRthVolSum;
            double close30mAgo = currentRthMinuteCloses.Count <= 30 ? orbClose : currentRthMinuteCloses[currentRthMinuteCloses.Count - 31];

            double gapBps = SafeRetBps(orbOpen, prevRthClose);
            double vwapDistBps = SafeRetBps(sigClose, rthVwap);
            double ret30mBps = SafeRetBps(sigClose, close30mAgo);
            double elapsed15m = (cMinEt - 585) / 15.0;

            DateTime dCash = KeyToDate(currentCashDate);
            int wkIdx = ((int)dCash.DayOfWeek + 6) % 7;
            int month = dCash.Month;

            double[] features = new double[]
            {
                baselineSide * gapBps,
                baselineSide * priorSessBps,
                baselineSide * priorRet5Bps,
                baselineSide * priorRet20Bps,
                baselineSide * vwapDistBps,
                baselineSide * ret30mBps,
                baselineSide,
                elapsed15m,
                currentOrbBps,
                admTouches,
                Math.Sin(TwoPi * wkIdx / 5.0),
                Math.Cos(TwoPi * wkIdx / 5.0),
                Math.Sin(TwoPi * (month - 1) / 12.0),
                Math.Cos(TwoPi * (month - 1) / 12.0)
            };
            for (int f = 0; f < 14; f++)
                if (double.IsNaN(features[f]) || double.IsInfinity(features[f])) { breakoutConsumed = true; BlockCashDate(); InvalidatePending(); return; }

            breakoutConsumed = true;
            bool priorOverride = (baselineSide * priorSessBps) < -300.0;
            bool knnOverride = false;
            if (currentCashDate >= KnnMinSessionDate)
            {
                int y = currentCashDate / 10000;
                int m = (currentCashDate / 100) % 100;
                int q = (m - 1) / 3 + 1;
                int qKey = y * 10 + q;
                if (activeQuarterKey != qKey)
                {
                    DateTime cutoff = new DateTime(y, (q - 1) * 3 + 1, 1).AddDays(-1);
                    activeQuarterModel = FitQuarterModel(DateToKey(cutoff));
                    activeQuarterKey = qKey;
                }
                double flipProb;
                if (PredictKnn(activeQuarterModel, features, out flipProb))
                    knnOverride = flipProb > KnnFlipProbThreshold;
            }

            int dirSide = (priorOverride || knnOverride) ? -baselineSide : baselineSide;
            string dirSrc = (priorOverride && knnOverride) ? "prior_session_and_quarterly_knn"
                          : (priorOverride ? "prior_session" : (knnOverride ? "quarterly_knn" : "breakout"));

            if (currentCashDate >= ShadowMinSessionDate)
            {
                if (activeShadowPair != null) { InvalidatePending(); dayBlocked = true; }
                else activeShadowPair = new ShadowPair
                {
                    SessionKey = currentCashDate, ExpectedFillOpenUtc = cUtc, BaselineSide = baselineSide,
                    Features = (double[])features.Clone(), PriorTrendAvail = currentPriorTrendAvail, PriorTrendBps = currentPriorTrendBps
                };
            }

            if (dayBlocked) return;

            bool contextReady = currentPriorOrbQ75Avail && currentPriorTrendAvail;
            bool submitActual = (currentCashDate >= PortfolioStartCashDate) && contextReady;

            if (features[7] == 1.0 && !(features[4] > 20.0))
            {
                if (submitActual) SubmitActualEntry(baselineSide, "rc1_breakout_shadow", "direct_first_signal_near_vwap");
                return;
            }

            bool weakSignal = !((dirSide * (sigClose - sigOpen) / sigRange) > 0.20);
            bool highVol = currentPriorOrbQ75Avail && (currentOrbBps > currentPriorOrbQ75Bps);
            double dirConfLevel = dirSide == 1 ? (orbHigh + TickSize) : (orbLow - TickSize);
            int dirTouches = 0;
            for (int k = 0; k < 15; k++)
            {
                if (dirSide == 1) { if (High[k] >= dirConfLevel) dirTouches++; }
                else { if (Low[k] <= dirConfLevel) dirTouches++; }
            }
            bool highVolTouchVote = highVol && !(dirTouches > 3);

            if (weakSignal || highVolTouchVote)
            {
                pendingDecision = new PendingDecision
                {
                    ExpectedObsOpenUtc = cUtc,
                    DirectionSide = dirSide,
                    RequiredObsBars = weakSignal ? 1 : 3,
                    SubmitActualOrder = submitActual,
                    Branch = weakSignal ? "weak_signal_delay_keep" : "high_vol_touch_vote",
                    DirectionSource = dirSrc,
                    BaselineSide = baselineSide,
                    Features = (double[])features.Clone(),
                    SignalClose = sigClose
                };
            }
            else
            {
                ApplyFinalRefinementOrSubmit(dirSide, cUtc, dirSrc, "condition_not_met", submitActual, baselineSide, features, sigClose);
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 15) return;

            DateTime barCloseUtc = TimeZoneInfo.ConvertTime(Times[0][0], Core.Globals.GeneralOptions.TimeZoneInfo, TimeZoneInfo.Utc);
            DateTime barOpenUtc = barCloseUtc.AddMinutes(-1);
            DateTime openCt = TimeZoneInfo.ConvertTimeFromUtc(barOpenUtc, ct);
            int cashDate = DateToKey(openCt.AddHours(7).Date);

            if (cashDate != currentCashDate) BeginCashDate(cashDate);

            bool exactMinute = (barCloseUtc.Second == 0 && barCloseUtc.Millisecond == 0);
            if (sessionDateEligible && !refOpenCaptured
                && DateToKey(barOpenUtc) == prevDayOfCash
                && barOpenUtc.Hour == 23 && barOpenUtc.Minute == 0)
            {
                if (!exactMinute || !(Open[0] > 0.0)) BlockCashDate();
                else { refSessionOpen = Open[0]; refOpenCaptured = true; }
            }

            DateTime openEt = TimeZoneInfo.ConvertTimeFromUtc(barOpenUtc, et);
            DateTime closeEt = TimeZoneInfo.ConvertTimeFromUtc(barCloseUtc, et);
            int oDateEt = DateToKey(openEt), cDateEt = DateToKey(closeEt);
            int oMinEt = openEt.Hour * 60 + openEt.Minute;
            int cMinEt = closeEt.Hour * 60 + closeEt.Minute;

            bool inCashWin = (oDateEt == currentCashDate && cDateEt == currentCashDate && oMinEt >= 570 && cMinEt <= 960);

            if (inCashWin && !exactMinute)
            {
                BlockCashDate(); InvalidatePending(); RequestAdminExit("CashTimeAlignment"); return;
            }
            if (inCashWin)
            {
                if (lastCashBarCloseUtc != DateTime.MinValue && barOpenUtc != lastCashBarCloseUtc)
                {
                    BlockCashDate(); InvalidatePending(); RequestAdminExit("CashDataGap"); return;
                }
                lastCashBarCloseUtc = barCloseUtc;
                if (!dayBlocked)
                {
                    currentRthMinuteCloses.Add(Close[0]);
                    currentRthTypVolSum += ((High[0] + Low[0] + Close[0]) / 3.0) * Volume[0];
                    currentRthVolSum += Volume[0];
                }
            }

            if (inCashWin && activeShadowPair != null)
            {
                ShadowPair sp = activeShadowPair;
                if (!sp.Invalid && !sp.LabelRecorded)
                {
                    if (!sp.Initialized)
                    {
                        if (barOpenUtc >= sp.ExpectedFillOpenUtc)
                        {
                            if (barOpenUtc != sp.ExpectedFillOpenUtc) sp.Invalid = true;
                            else
                            {
                                sp.Breakout = CreateShadowTrade(sp.BaselineSide, Open[0], sp.PriorTrendAvail, sp.PriorTrendBps);
                                sp.Fade = CreateShadowTrade(-sp.BaselineSide, Open[0], sp.PriorTrendAvail, sp.PriorTrendBps);
                                sp.Initialized = true;
                            }
                        }
                    }
                    if (sp.Initialized && !sp.Invalid)
                    {
                        ProcessShadowBar(sp.Breakout, cMinEt);
                        ProcessShadowBar(sp.Fade, cMinEt);
                        TryRecordShadowLabel();
                    }
                }
            }

            if (inCashWin && pendingDecision != null && !dayBlocked)
            {
                PendingDecision pd = pendingDecision;
                if (barOpenUtc >= pd.ExpectedObsOpenUtc)
                {
                    if (barOpenUtc != pd.ExpectedObsOpenUtc || (barCloseUtc - barOpenUtc).TotalMinutes != 1.0)
                    {
                        pendingDecision = null; dayBlocked = true;
                    }
                    else
                    {
                        if (pd.ObservedBars == 0) pd.FirstObsOpen = Open[0];
                        pd.ObservedBars++;
                        pd.ExpectedObsOpenUtc = barCloseUtc;
                        if (pd.ObservedBars >= pd.RequiredObsBars)
                        {
                            int rSide = pd.DirectionSide;
                            string rPath = pd.Branch;
                            if (pd.Branch == "high_vol_touch_vote")
                            {
                                double mv = rSide * (Close[0] - pd.FirstObsOpen);
                                double orbR = orbHigh - orbLow;
                                double frac = orbR > 0.0 ? mv / orbR : 0.0;
                                if (!(frac > 0.0)) { rSide = -rSide; rPath = "high_vol_vote_flip"; }
                                else rPath = "high_vol_vote_keep";
                            }
                            pendingDecision = null;
                            ApplyFinalRefinementOrSubmit(rSide, barCloseUtc, pd.DirectionSource, rPath,
                                pd.SubmitActualOrder, pd.BaselineSide, pd.Features, pd.SignalClose);
                        }
                    }
                }
            }

            if (inCashWin && pendingFinalDecision != null && !dayBlocked)
            {
                PendingFinalDecision pfd = pendingFinalDecision;
                if (barOpenUtc >= pfd.ExpectedObsOpenUtc)
                {
                    if (barOpenUtc != pfd.ExpectedObsOpenUtc || (barCloseUtc - barOpenUtc).TotalMinutes != 1.0)
                    {
                        pendingFinalDecision = null; dayBlocked = true;
                    }
                    else
                    {
                        if (pfd.ObservedBars == 0) pfd.FirstObsOpen = Open[0];
                        pfd.ObservedBars++;
                        pfd.ExpectedObsOpenUtc = barCloseUtc;
                        if (pfd.ObservedBars >= pfd.RequiredObsBars)
                        {
                            double obsMv = pfd.RefinedSide * (Close[0] - pfd.FirstObsOpen);
                            int fSide;
                            string actLbl;
                            if (pfd.Branch == "prior_session_disagreement") { fSide = -pfd.RefinedSide; actLbl = "prior_session_disagreement_reverse"; }
                            else if (obsMv > 0.0) { fSide = -pfd.RefinedSide; actLbl = "intraday_continuation_reverse"; }
                            else { fSide = pfd.RefinedSide; actLbl = "intraday_continuation_keep"; }

                            string dSrc = pfd.DirectionSource + "+" + pfd.Branch;
                            string rPath = pfd.RefinementPath + "->" + actLbl;
                            bool subAct = pfd.SubmitActualOrder;
                            pendingFinalDecision = null;
                            if (subAct) SubmitActualEntry(fSide, dSrc, rPath);
                        }
                    }
                }
            }

            if (inCashWin && cMinEt >= 960)
            {
                if (activeShadowPair != null)
                {
                    ShadowPair sp = activeShadowPair;
                    if (sp.Invalid || !sp.Initialized) activeShadowPair = null;
                    else
                    {
                        if (!sp.Breakout.Complete) { sp.Breakout.ExitPrice = Close[0] - sp.Breakout.Side * TickSize; sp.Breakout.Complete = true; }
                        if (!sp.Fade.Complete) { sp.Fade.ExitPrice = Close[0] - sp.Fade.Side * TickSize; sp.Fade.Complete = true; }
                        TryRecordShadowLabel();
                    }
                }
                if (!rthCloseHistoryRecorded && sessionDateEligible && cashWindowIntegrity && orbFinalized && refOpenCaptured)
                {
                    if (!orbHistoryRecorded)
                    {
                        eligibleOrbHistoryBps.Add(currentOrbBps);
                        while (eligibleOrbHistoryBps.Count > 120) eligibleOrbHistoryBps.RemoveAt(0);
                        orbHistoryRecorded = true;
                    }
                    if (Close[0] > 0.0)
                    {
                        double sessRetBps = SafeRetBps(Close[0], refSessionOpen);
                        eligibleRthCloseHistory.Add(Close[0]);
                        while (eligibleRthCloseHistory.Count > 21) eligibleRthCloseHistory.RemoveAt(0);
                        eligibleSessionRetBps.Add(sessRetBps);
                        while (eligibleSessionRetBps.Count > 1) eligibleSessionRetBps.RemoveAt(0);
                        rthCloseHistoryRecorded = true;
                    }
                }
                cashExitTriggered = true;
                dayBlocked = true;
                RequestAdminExit("CashClose1600ET");
                return;
            }

            if (cashExitTriggered) { RequestAdminExit("CashExitFollowup"); return; }

            bool isQuarterHour = inCashWin && cMinEt >= 600 && cMinEt < 960 && (cMinEt % 15) == 0;

            if (Position.MarketPosition != MarketPosition.Flat)
            {
                int posSide = Position.MarketPosition == MarketPosition.Long ? 1 : -1;
                double entryPx = Position.AveragePrice;
                if (isQuarterHour && !managedStopActivated && activeStopTicks >= 1 && entryPx > 0.0)
                {
                    double riskPts = activeStopTicks * TickSize;
                    double closeR = posSide * (Close[0] - entryPx) / riskPts;
                    if (closeR >= activeTriggerR)
                    {
                        liveStopPx = RoundTick(entryPx + posSide * riskPts * activeLockR);
                        managedStopActivated = true;
                        if (posSide == 1) ExitLongStopMarket(0, true, Position.Quantity, liveStopPx, "T_stop", SigL);
                        else ExitShortStopMarket(0, true, Position.Quantity, liveStopPx, "T_stop", SigS);
                    }
                }
                if (inCashWin && cMinEt == 930 && !conditionalExitRequested && activeStopTicks >= 1 && entryPx > 0.0)
                {
                    double riskPts = activeStopTicks * TickSize;
                    double closeR = posSide * (Close[0] - entryPx) / riskPts;
                    if (closeR < 0.0 || closeR >= 1.0)
                    {
                        conditionalExitRequested = true;
                        RequestAdminExit("Conditional1530ET");
                    }
                }
                return;
            }

            DateTime dc = KeyToDate(currentCashDate);
            if (dayBlocked || dc.DayOfWeek == DayOfWeek.Saturday || dc.DayOfWeek == DayOfWeek.Sunday) return;

            if (!orbFinalized)
            {
                if (oDateEt == currentCashDate && cDateEt == currentCashDate && oMinEt >= 570 && oMinEt < 585)
                {
                    if (oMinEt != expectedNextOrbOpenMin || cMinEt != oMinEt + 1) { BlockCashDate(); return; }
                    if (orbBarCount == 0) orbOpen = Open[0];
                    orbHigh = orbBarCount == 0 ? High[0] : Math.Max(orbHigh, High[0]);
                    orbLow = orbBarCount == 0 ? Low[0] : Math.Min(orbLow, Low[0]);
                    orbClose = Close[0];
                    orbBarCount++;
                    expectedNextOrbOpenMin++;
                    if (cMinEt == 585)
                    {
                        if (orbBarCount != 15 || !(orbHigh >= orbLow)) { BlockCashDate(); return; }
                        orbFinalized = true;
                        double mid = 0.5 * (orbHigh + orbLow);
                        currentOrbBps = mid > 0.0 ? ((orbHigh - orbLow) / mid) * 10000.0 : 0.0;
                        currentPriorOrbQ75Avail = (eligibleOrbHistoryBps.Count == 120);
                        if (currentPriorOrbQ75Avail) currentPriorOrbQ75Bps = LinearPercentile(eligibleOrbHistoryBps, 0.75);
                    }
                }
                else if (oDateEt == currentCashDate && cDateEt == currentCashDate && cMinEt > 585)
                {
                    BlockCashDate(); return;
                }
            }

            if (dayBlocked || !orbFinalized || breakoutConsumed || !isQuarterHour) return;

            bool longBreak = Close[0] >= RoundTick(orbHigh + TickSize);
            bool shortBreak = Close[0] <= RoundTick(orbLow - TickSize);
            if (!longBreak && !shortBreak) return;

            EvaluateAdmissionAndDirection(longBreak ? 1 : -1, barCloseUtc, cMinEt);
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            string n = execution.Order.Name;
            if (n != SigL && n != SigS) return;

            pendingSubmit = false;
            double fillPx = execution.Order.AverageFillPrice;
            int q = execution.Order.Filled;
            bool isLong = (n == SigL);

            liveStopPx = RoundTick(fillPx - (isLong ? 1 : -1) * activeStopDist);
            liveTargetPx = RoundTick(fillPx + (isLong ? 1 : -1) * activeTargetDist);
            if (isLong)
            {
                ExitLongStopMarket(0, true, q, liveStopPx, "T_stop", SigL);
                ExitLongLimit(0, true, q, liveTargetPx, "T_obj", SigL);
            }
            else
            {
                ExitShortStopMarket(0, true, q, liveStopPx, "T_stop", SigS);
                ExitShortLimit(0, true, q, liveTargetPx, "T_obj", SigS);
            }
        }

        #region Properties
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Cantidad contratos", Order = 1, GroupName = "T (FtmOrb)")]
        public int Cantidad { get; set; }
        [NinjaScriptProperty, Display(Name = "UseExclusionCalendars (true)", Order = 2, GroupName = "T (FtmOrb)")]
        public bool UseExclusionCalendars { get; set; }
        [NinjaScriptProperty, Display(Name = "ShadowMinSessionDate (20100101)", Order = 3, GroupName = "T (FtmOrb)")]
        public int ShadowMinSessionDate { get; set; }
        [NinjaScriptProperty, Display(Name = "KnnMinSessionDate (20120101)", Order = 4, GroupName = "T (FtmOrb)")]
        public int KnnMinSessionDate { get; set; }
        [NinjaScriptProperty, Display(Name = "PortfolioStartCashDate (20120101)", Order = 5, GroupName = "T (FtmOrb)")]
        public int PortfolioStartCashDate { get; set; }
        [NinjaScriptProperty, Range(15, 500), Display(Name = "KnnMinTrainingRows (100)", Order = 6, GroupName = "T (FtmOrb)")]
        public int KnnMinTrainingRows { get; set; }
        [NinjaScriptProperty, Range(3, 50), Display(Name = "KnnK (15)", Order = 7, GroupName = "T (FtmOrb)")]
        public int KnnK { get; set; }
        [NinjaScriptProperty, Range(0.5, 1.0), Display(Name = "KnnFlipProbThreshold (0.65)", Order = 8, GroupName = "T (FtmOrb)")]
        public double KnnFlipProbThreshold { get; set; }
        #endregion
    }
}

