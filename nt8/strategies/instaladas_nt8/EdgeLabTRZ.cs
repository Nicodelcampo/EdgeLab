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

// EdgeLabTRZ (version=1.0, 2026-11-20) — Canasta unificada T (FtmOrb) + R (AtrPhaseStop) + Z-banda (ZetaTrendDay).
// Combina los 3 módulos de FundedSync validados por EdgeLab en UNA sola estrategia NinjaTrader 8 con:
//   - seguimiento virtual independiente por módulo/celda (evita que señales opuestas entre T, R y Z se cancelen entre sí);
//   - sincronización neta de la posición en mercado (cumple regla no-hedging de CME/propfirms y permite backtest conjunto en Strategy Analyzer);
//   - soporte para Z fábrica (15/20/45) o Z-banda completa de 9 configuraciones ({10/30, 15/20, 30/10} x {35, 45, 55}%, Plan A de LUCID-PLAN);
//   - guarda de cuenta opcional para Realtime/Lucid (DLL, Piso de cuenta y Plano a hora fija ET, igual que EdgeLabCanasta).
//
// Uso exclusivo local en NinjaTrader 8 (paper/backtest/forward; no subir la reimplementación de T/Z al repo público por licencia FundedSync).
// Gráfico de 1 minuto de MNQ o NQ, plantilla CME US Index Futures ETH. Calculate = OnBarClose.
// Nota: T requiere ~6 meses (120 sesiones) para estadísticas previas y KnnMinTrainingRows sesiones para KNN (entrenamiento completo desde 2012+).
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabTRZ : Strategy
    {
        private const string SigNetLong = "TRZ_L";
        private const string SigNetShort = "TRZ_S";
        private const double TwoPi = 6.2831853071795862;

        #region Shared Helpers & Calendars

        private static readonly HashSet<int> RollExclusionsT = new HashSet<int>
        {
            20200311, 20200610, 20200909, 20210609, 20210908, 20220608, 20220907, 20260611
        };

        private static readonly HashSet<int> DegradedExclusionsT = new HashSet<int>
        {
            20200227, 20200228, 20200630, 20200701, 20200702, 20211206, 20220103, 20240918,
            20240919, 20250917, 20250918, 20250924, 20250925, 20251128, 20260316, 20260317,
            20260410, 20260525, 20260730, 20260731
        };

        private static readonly HashSet<int> FechasVendedorR = new HashSet<int>
        {
            20220803, 20220830, 20230405, 20240704, 20241224, 20250120, 20250703, 20250829
        };

        private static readonly HashSet<int> NonFullNyseZ = new HashSet<int>
        {
            20100101, 20100118, 20100215, 20100402, 20100531, 20100705, 20100906, 20101125,
            20101126, 20101224, 20110117, 20110221, 20110422, 20110530, 20110704, 20110905,
            20111124, 20111125, 20111226, 20120102, 20120116, 20120220, 20120406, 20120528,
            20120703, 20120704, 20120903, 20121029, 20121030, 20121122, 20121123, 20121224,
            20121225, 20130101, 20130121, 20130218, 20130329, 20130527, 20130703, 20130704,
            20130902, 20131128, 20131129, 20131224, 20131225, 20140101, 20140120, 20140217,
            20140418, 20140526, 20140703, 20140704, 20140901, 20141127, 20141128, 20141224,
            20141225, 20150101, 20150119, 20150216, 20150403, 20150525, 20150703, 20150907,
            20151126, 20151127, 20151224, 20151225, 20160101, 20160118, 20160215, 20160325,
            20160530, 20160704, 20160905, 20161124, 20161125, 20161226, 20170102, 20170116,
            20170220, 20170414, 20170529, 20170703, 20170704, 20170904, 20171123, 20171124,
            20171225, 20180101, 20180115, 20180219, 20180330, 20180528, 20180703, 20180704,
            20180903, 20181122, 20181123, 20181205, 20181224, 20181225, 20190101, 20190121,
            20190218, 20190419, 20190527, 20190703, 20190704, 20190902, 20191128, 20191129,
            20191224, 20191225, 20200101, 20200120, 20200217, 20200410, 20200525, 20200703,
            20200907, 20201126, 20201127, 20201224, 20201225, 20210101, 20210118, 20210215,
            20210402, 20210531, 20210705, 20210906, 20211125, 20211126, 20211224, 20220117,
            20220221, 20220415, 20220530, 20220620, 20220704, 20220905, 20221124, 20221125,
            20221226, 20230102, 20230116, 20230220, 20230407, 20230529, 20230619, 20230703,
            20230704, 20230904, 20231123, 20231124, 20231225, 20240101, 20240115, 20240219,
            20240329, 20240527, 20240619, 20240703, 20240704, 20240902, 20241128, 20241129,
            20241224, 20241225, 20250101, 20250109, 20250120, 20250217, 20250418, 20250526,
            20250619, 20250703, 20250704, 20250901, 20251127, 20251128, 20251224, 20251225,
            20260101, 20260119, 20260216, 20260403, 20260525, 20260619, 20260703, 20260907,
            20261126, 20261127, 20261224, 20261225, 20270101, 20270118, 20270215, 20270326,
            20270531, 20270618, 20270705
        };

        private static int DateToKey(DateTime d) { return d.Year * 10000 + d.Month * 100 + d.Day; }
        private static DateTime KeyToDate(int key) { return new DateTime(key / 10000, (key / 100) % 100, key % 100); }
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

        private double RoundZetaTarget(int side, double price)
        {
            if (side <= 0) return Math.Floor(price / TickSize) * TickSize;
            return Math.Ceiling(price / TickSize) * TickSize;
        }

        #endregion

        #region Virtual Position Container

        private class VirtualLeg
        {
            public string Name;
            public int Side;          // +1, -1, or 0
            public int Qty;
            public double EntryPx;
            public double StopPx = double.NaN;
            public double TargetPx = double.NaN;

            public int PendingSide;
            public int PendingQty;
            public double PendingStopDist = double.NaN;
            public double PendingTargetDist = double.NaN;
            public double PendingTargetPx = double.NaN;
            public bool PendingCheckPassedTarget;

            public int NetDesired()
            {
                if (PendingSide != 0) return PendingSide * PendingQty;
                return Side * Qty;
            }

            public bool HasExposure()
            {
                return Side != 0 || PendingSide != 0;
            }

            public void Clear()
            {
                Side = 0; Qty = 0; EntryPx = 0.0;
                StopPx = double.NaN; TargetPx = double.NaN;
                PendingSide = 0; PendingQty = 0;
                PendingStopDist = double.NaN; PendingTargetDist = double.NaN;
                PendingTargetPx = double.NaN; PendingCheckPassedTarget = false;
            }
        }

        private void LogMsg(string msg)
        {
            if (LogSenales) Print(msg);
        }

        /// <summary>
        /// Convierte la entrada pendiente en posición abierta usando Open[0] y verifica stop/target intrabar conservadoramente (stop antes que target).
        /// </summary>
        private bool ResolveVirtualBar(VirtualLeg leg, double op, double hi, double lo, Func<double, double> roundTick, out string exitReason, out double exitPx)
        {
            exitReason = null;
            exitPx = double.NaN;

            if (leg.PendingSide != 0)
            {
                leg.Side = leg.PendingSide;
                leg.Qty = leg.PendingQty;
                leg.EntryPx = op;
                leg.StopPx = !double.IsNaN(leg.PendingStopDist) && leg.PendingStopDist > 0
                    ? roundTick(op - leg.Side * leg.PendingStopDist)
                    : double.NaN;

                if (!double.IsNaN(leg.PendingTargetPx))
                {
                    leg.TargetPx = leg.PendingTargetPx;
                    if (leg.PendingCheckPassedTarget && (leg.Side > 0 ? op >= leg.TargetPx : op <= leg.TargetPx))
                    {
                        exitReason = leg.Name + "_tgt_fill_passed";
                        exitPx = op;
                        leg.Clear();
                        return true;
                    }
                }
                else if (!double.IsNaN(leg.PendingTargetDist) && leg.PendingTargetDist > 0)
                {
                    leg.TargetPx = roundTick(op + leg.Side * leg.PendingTargetDist);
                }
                else
                {
                    leg.TargetPx = double.NaN;
                }

                leg.PendingSide = 0;
                leg.PendingQty = 0;
                leg.PendingStopDist = double.NaN;
                leg.PendingTargetDist = double.NaN;
                leg.PendingTargetPx = double.NaN;
                leg.PendingCheckPassedTarget = false;
            }

            if (leg.Side == 0) return false;

            bool stopHit = !double.IsNaN(leg.StopPx) && (leg.Side == 1 ? (lo <= leg.StopPx) : (hi >= leg.StopPx));
            if (stopHit)
            {
                exitPx = leg.Side == 1 ? Math.Min(leg.StopPx, op) : Math.Max(leg.StopPx, op);
                exitReason = leg.Name + "_stop";
                leg.Clear();
                return true;
            }

            bool tgtHit = !double.IsNaN(leg.TargetPx) && (leg.Side == 1 ? (hi >= leg.TargetPx) : (lo <= leg.TargetPx));
            if (tgtHit)
            {
                exitPx = leg.Side == 1 ? Math.Max(leg.TargetPx, op) : Math.Min(leg.TargetPx, op);
                exitReason = leg.Name + "_obj";
                leg.Clear();
                return true;
            }

            return false;
        }

        private void CloseVirtualAtBarClose(VirtualLeg leg, string reason, double cl, DateTime tEt)
        {
            if (!leg.HasExposure()) return;
            if (leg.Side != 0)
            {
                double pts = leg.Side * (cl - leg.EntryPx);
                LogMsg(string.Format("TRZ;{0};SALIDA;{1:yyyy-MM-dd HH:mm};{2};qty={3};pts={4:F2}", leg.Name, tEt, reason, leg.Qty, pts));
            }
            leg.Clear();
        }

        #endregion

        #region Shared Timezones, CME ATR20 & Account Guard

        private TimeZoneInfo ct, et;
        private DateTime sesionCmeActual = DateTime.MinValue;
        private double sesCmeHi = double.MinValue, sesCmeLo = double.MaxValue;
        private readonly Queue<double> rangosCme = new Queue<double>();
        private double atr20Cme = double.NaN;

        private DateTime diaGuarda = DateTime.MinValue;
        private double realizadoBaseGuarda;
        private bool bloqueoDiaGuarda, bloqueoTotalGuarda;
        private Order activeSyncOrder;

        private void UpdateCmeAtr20(DateTime barOpenEt, double hi, double lo)
        {
            DateTime ses = barOpenEt.AddHours(6).Date;
            if (ses != sesionCmeActual)
            {
                if (sesionCmeActual != DateTime.MinValue && sesCmeHi > sesCmeLo)
                {
                    rangosCme.Enqueue(sesCmeHi - sesCmeLo);
                    while (rangosCme.Count > 20) rangosCme.Dequeue();
                }
                atr20Cme = rangosCme.Count == 20 ? rangosCme.Average() : double.NaN;
                sesionCmeActual = ses;
                sesCmeHi = double.MinValue;
                sesCmeLo = double.MaxValue;
            }
            sesCmeHi = Math.Max(sesCmeHi, hi);
            sesCmeLo = Math.Min(sesCmeLo, lo);
        }

        private double PnlDiaCuenta()
        {
            double abierto = 0;
            lock (Account.Positions)
                foreach (Position p in Account.Positions)
                    if (p.MarketPosition != MarketPosition.Flat) abierto += p.GetUnrealizedProfitLoss(PerformanceUnit.Currency);
            return Account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar) - realizadoBaseGuarda + abierto;
        }

        private void AplanarCuentaCompleta(string motivo)
        {
            var ins = new List<Instrument>();
            lock (Account.Positions)
                foreach (Position p in Account.Positions)
                    if (p.MarketPosition != MarketPosition.Flat) ins.Add(p.Instrument);
            if (ins.Count == 0) return;
            LogMsg(string.Format("TRZ;GUARDA;APLANAR;{0};{1}", motivo, string.Join(",", ins.Select(i => i.FullName))));
            Account.Flatten(ins);
        }

        private void ClearAllVirtualExposures()
        {
            tLeg.Clear();
            tPendingSubmit = false;
            rLeg.Clear();
            rShadowSide = 0;
            rPendingReversal = 0;
            foreach (ZetaSlot z in zSlots) z.Leg.Clear();
        }

        private bool CheckRealtimeGuard(DateTime tCloseEt)
        {
            if (State != State.Realtime) return false;

            DateTime diaCme = tCloseEt.Hour >= 18 ? tCloseEt.Date.AddDays(1) : tCloseEt.Date;
            if (diaCme != diaGuarda)
            {
                diaGuarda = diaCme;
                bloqueoDiaGuarda = false;
                realizadoBaseGuarda = Account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
            }
            if (PerdidaDiariaUSD > 0 && PnlDiaCuenta() <= -PerdidaDiariaUSD)
            {
                bloqueoDiaGuarda = true;
                ClearAllVirtualExposures();
                AplanarCuentaCompleta("DLL");
            }
            else if (bloqueoDiaGuarda)
            {
                ClearAllVirtualExposures();
                AplanarCuentaCompleta("DLL_REAPERTURA");
            }

            if (PisoCuentaUSD > 0 && Account.Get(AccountItem.NetLiquidation, Currency.UsDollar) <= PisoCuentaUSD + MargenPisoUSD)
            {
                bloqueoTotalGuarda = true;
                ClearAllVirtualExposures();
                AplanarCuentaCompleta("PISO");
            }

            int hp = (HoraPlanoET / 100) * 60 + HoraPlanoET % 100;
            int m = tCloseEt.Hour * 60 + tCloseEt.Minute;
            bool enPlano = HoraPlanoET > 0 && m >= hp && m < 18 * 60;
            if (enPlano)
            {
                ClearAllVirtualExposures();
                AplanarCuentaCompleta("PLANO_" + HoraPlanoET);
            }
            return bloqueoDiaGuarda || bloqueoTotalGuarda || enPlano;
        }

        #endregion

        #region Module T (FtmOrb)

        private class TrainingRowT
        {
            public int SessionKey;
            public double[] Features;
            public bool FlipWins;
            public int Sequence;
        }

        private class QuarterModelT
        {
            public double[][] TrainXStd;
            public bool[] TrainFlip;
            public int[] TrainSeq;
            public double[] Means;
            public double[] Scales;
        }

        private class ShadowTradeT
        {
            public int Side;
            public double Entry, ActiveStop, Target, RiskPoints, ManagedTriggerR, ManagedLockR, ExitPrice;
            public bool Complete, PendingConditionalExit;
        }

        private class ShadowPairT
        {
            public int SessionKey;
            public DateTime ExpectedFillOpenUtc;
            public int BaselineSide;
            public double[] Features;
            public bool PriorTrendAvail, Initialized, Invalid, LabelRecorded;
            public double PriorTrendBps;
            public ShadowTradeT Breakout, Fade;
        }

        private class PendingDecisionT
        {
            public DateTime ExpectedObsOpenUtc;
            public int DirectionSide, RequiredObsBars, BaselineSide, ObservedBars;
            public bool SubmitActualOrder;
            public string Branch, DirectionSource;
            public double[] Features;
            public double SignalClose, FirstObsOpen;
        }

        private class PendingFinalDecisionT
        {
            public DateTime ExpectedObsOpenUtc;
            public int RefinedSide, RequiredObsBars, ObservedBars;
            public bool SubmitActualOrder;
            public string Branch, DirectionSource, RefinementPath;
            public double FirstObsOpen;
        }

        private readonly VirtualLeg tLeg = new VirtualLeg { Name = "T" };
        private readonly List<double> tEligibleOrbHistoryBps = new List<double>();
        private readonly List<double> tEligibleRthCloseHistory = new List<double>();
        private readonly List<double> tEligibleSessionRetBps = new List<double>();
        private readonly List<TrainingRowT> tTrainingRows = new List<TrainingRowT>();
        private int tTrainingSeq, tActiveQuarterKey;
        private QuarterModelT tActiveQuarterModel;

        private int tCurrentCashDate = -1, tPrevDayOfCash = -1;
        private bool tSessionEligible, tRefOpenCaptured, tDayBlocked = true, tOrbFinalized, tBreakoutConsumed;
        private bool tCashExitTriggered, tCashWindowIntegrity, tOrbHistoryRecorded, tRthCloseHistoryRecorded;
        private double tRefSessionOpen;
        private int tOrbBarCount, tExpectedNextOrbOpenMin;
        private double tOrbHigh, tOrbLow, tOrbOpen, tOrbClose;
        private double tCurOrbBps, tCurPriorOrbQ75Bps, tCurPriorTrendBps;
        private bool tCurPriorOrbQ75Avail, tCurPriorTrendAvail;

        private readonly List<double> tCurRthMinCloses = new List<double>();
        private double tCurRthTypVolSum, tCurRthVolSum;
        private DateTime tLastCashBarCloseUtc = DateTime.MinValue;

        private int tActiveStopTicks;
        private double tActiveTriggerR, tActiveLockR, tActiveStopDist, tActiveTargetDist;
        private bool tManagedStopActivated, tConditionalExitRequested, tPendingSubmit;

        private ShadowPairT tActiveShadowPair;
        private PendingDecisionT tPendingDecision;
        private PendingFinalDecisionT tPendingFinalDecision;

        private void TInvalidatePending()
        {
            tPendingDecision = null;
            tPendingFinalDecision = null;
            tActiveShadowPair = null;
        }

        private void TBlockCashDate()
        {
            tCashWindowIntegrity = false;
            tDayBlocked = true;
            tBreakoutConsumed = true;
        }

        private void TBeginCashDate(int cashKey, DateTime tEt)
        {
            bool hasExposure = tLeg.HasExposure() || tPendingSubmit;
            TInvalidatePending();

            tCurrentCashDate = cashKey;
            DateTime dCash = KeyToDate(cashKey);
            tPrevDayOfCash = DateToKey(dCash.AddDays(-1));

            tSessionEligible = true;
            tRefOpenCaptured = false;
            tRefSessionOpen = 0.0;
            tDayBlocked = hasExposure;
            tOrbFinalized = false;
            tBreakoutConsumed = hasExposure;
            tCashExitTriggered = false;
            tCashWindowIntegrity = false;
            tOrbHistoryRecorded = false;
            tRthCloseHistoryRecorded = false;

            tActiveStopTicks = 0;
            tManagedStopActivated = false;
            tConditionalExitRequested = false;
            tOrbBarCount = 0;
            tExpectedNextOrbOpenMin = 570;
            tOrbHigh = double.NegativeInfinity;
            tOrbLow = double.PositiveInfinity;
            tOrbOpen = 0.0;
            tOrbClose = 0.0;
            tCurOrbBps = 0.0;
            tCurPriorOrbQ75Bps = 0.0;
            tCurPriorOrbQ75Avail = false;

            if (tEligibleRthCloseHistory.Count >= 21)
            {
                double oldest = tEligibleRthCloseHistory[0];
                double newest = tEligibleRthCloseHistory[tEligibleRthCloseHistory.Count - 1];
                if (oldest > 0.0 && newest > 0.0)
                {
                    tCurPriorTrendBps = SafeRetBps(newest, oldest);
                    tCurPriorTrendAvail = true;
                }
                else { tCurPriorTrendBps = 0.0; tCurPriorTrendAvail = false; }
            }
            else { tCurPriorTrendBps = 0.0; tCurPriorTrendAvail = false; }

            tCurRthMinCloses.Clear();
            tCurRthTypVolSum = 0.0;
            tCurRthVolSum = 0.0;
            tLastCashBarCloseUtc = DateTime.MinValue;
            tActiveTriggerR = 0.0;
            tActiveLockR = 0.0;

            if (hasExposure)
            {
                tPendingSubmit = false;
                CloseVirtualAtBarClose(tLeg, "OvernightExposure", Close[0], tEt);
                return;
            }
            if (dCash.DayOfWeek == DayOfWeek.Saturday || dCash.DayOfWeek == DayOfWeek.Sunday)
            {
                tSessionEligible = false; tDayBlocked = true; return;
            }
            if (UseExclusionCalendars && (DegradedExclusionsT.Contains(cashKey) || RollExclusionsT.Contains(cashKey)))
            {
                tSessionEligible = false; tDayBlocked = true; return;
            }
            tCashWindowIntegrity = true;
        }

        private void TSelectManagementPlan(int side, bool priorTrendAvail, double priorTrendBps,
            bool priorOrbQ75Avail, double curOrbBps, double priorOrbQ75Bps,
            out double targetR, out double triggerR, out double lockR)
        {
            bool highOrb = priorOrbQ75Avail && (curOrbBps > priorOrbQ75Bps);
            bool countertrend = priorTrendAvail && ((side * priorTrendBps) < 0.0);
            if (highOrb) { targetR = 1.25; triggerR = 1.25; lockR = 0.0; return; }
            if (countertrend) { targetR = 3.0; triggerR = 0.75; lockR = 0.10; return; }
            targetR = 3.0; triggerR = 1.25; lockR = 0.0;
        }

        private ShadowTradeT TCreateShadowTrade(int side, double parentFillOpen, bool priorTrendAvail, double priorTrendBps)
        {
            double entryPx = parentFillOpen + side * TickSize;
            double rawDist = Math.Max(2.0, Math.Min(100.0, (tOrbHigh - tOrbLow) * 1.25));
            double stopPx = RoundTick(entryPx - side * rawDist);
            double riskPts = side * (entryPx - stopPx);
            double tR, trigR, lockR;
            TSelectManagementPlan(side, priorTrendAvail, priorTrendBps, tCurPriorOrbQ75Avail, tCurOrbBps, tCurPriorOrbQ75Bps,
                out tR, out trigR, out lockR);
            double targetPx = RoundTick(entryPx + side * rawDist * tR);
            ShadowTradeT st = new ShadowTradeT
            {
                Side = side, Entry = entryPx, ActiveStop = stopPx, Target = targetPx,
                RiskPoints = riskPts, ManagedTriggerR = trigR, ManagedLockR = lockR
            };
            if (!(riskPts > 0.0)) { st.Complete = true; st.ExitPrice = entryPx; }
            return st;
        }

        private void TProcessShadowBar(ShadowTradeT st, int closeMin)
        {
            if (st.Complete) return;
            double op = Open[0], hi = High[0], lo = Low[0], cl = Close[0];

            if (st.PendingConditionalExit)
            {
                st.ExitPrice = op - st.Side * TickSize;
                st.Complete = true; st.PendingConditionalExit = false; return;
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

        private void TTryRecordShadowLabel()
        {
            ShadowPairT sp = tActiveShadowPair;
            if (sp == null || sp.Invalid || sp.LabelRecorded || !sp.Initialized || sp.Breakout == null || sp.Fade == null) return;
            if (!sp.Breakout.Complete || !sp.Fade.Complete) return;

            double brkNet = sp.Breakout.Side * (sp.Breakout.ExitPrice - sp.Breakout.Entry) * 20.0 - 2.5;
            double fadeNet = sp.Fade.Side * (sp.Fade.ExitPrice - sp.Fade.Entry) * 20.0 - 2.5;
            bool flipWins = fadeNet > 0.0;
            if ((brkNet > 0.0) != flipWins)
            {
                tTrainingRows.Add(new TrainingRowT
                {
                    SessionKey = sp.SessionKey,
                    Features = (double[])sp.Features.Clone(),
                    FlipWins = flipWins,
                    Sequence = tTrainingSeq++
                });
            }
            sp.LabelRecorded = true;
            tActiveShadowPair = null;
        }

        private QuarterModelT TFitQuarterModel(int cutoffKey)
        {
            List<TrainingRowT> elig = new List<TrainingRowT>();
            foreach (TrainingRowT r in tTrainingRows)
                if (r.SessionKey >= ShadowMinSessionDate && r.SessionKey <= cutoffKey) elig.Add(r);

            if (elig.Count < Math.Max(KnnMinTrainingRows, KnnK)) return null;

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
            return new QuarterModelT { TrainXStd = xStd, TrainFlip = flips, TrainSeq = seqs, Means = means, Scales = scales };
        }

        private bool TPredictKnn(QuarterModelT model, double[] features, out double flipProb)
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

        private void TSubmitActualEntry(int side, string dirSrc, string refPath)
        {
            if (ContratosT <= 0 || tLeg.HasExposure() || tPendingSubmit) return;
            bool isLong = (side == 1);
            double rawDist = Math.Max(2.0, Math.Min(100.0, (tOrbHigh - tOrbLow) * 1.25));
            int stopTicks = RoundPriceOffsetTicks(rawDist, isLong);
            double targetR, trigR, lockR;
            TSelectManagementPlan(side, tCurPriorTrendAvail, tCurPriorTrendBps, tCurPriorOrbQ75Avail, tCurOrbBps, tCurPriorOrbQ75Bps,
                out targetR, out trigR, out lockR);
            int targetTicks = RoundPriceOffsetTicks(rawDist * targetR, !isLong);

            tActiveStopTicks = stopTicks;
            tActiveTriggerR = trigR;
            tActiveLockR = lockR;
            tActiveStopDist = stopTicks * TickSize;
            tActiveTargetDist = targetTicks * TickSize;
            tManagedStopActivated = false;
            tConditionalExitRequested = false;

            tLeg.PendingSide = side;
            tLeg.PendingQty = ContratosT;
            tLeg.PendingStopDist = tActiveStopDist;
            tLeg.PendingTargetDist = tActiveTargetDist;
            tLeg.PendingTargetPx = double.NaN;
            tLeg.PendingCheckPassedTarget = false;

            LogMsg(string.Format("TRZ;T;SENAL;{0};{1};qty={2};orb={3:F2};sl_t={4};tp_t={5};{6}|{7}",
                tCurrentCashDate, side, ContratosT, tOrbHigh - tOrbLow, stopTicks, targetTicks, dirSrc, refPath));
        }

        private void TApplyFinalRefinementOrSubmit(int refinedSide, DateTime refFillOpenUtc, string dirSrc,
            string refPath, bool submitActual, int baselineSide, double[] features, double sigClose)
        {
            double orbRange = tOrbHigh - tOrbLow;
            if (!(orbRange > 0.0) || features.Length != 14) { tDayBlocked = true; return; }

            double signFlip = refinedSide * baselineSide;
            double alignedPrior = signFlip * features[1];
            double alignedRet30 = signFlip * features[5];
            double orbBody = refinedSide * (tOrbClose - tOrbOpen) / orbRange;
            double breakoutEdge = refinedSide == 1 ? tOrbHigh : tOrbLow;
            double sigExt = refinedSide * (sigClose - breakoutEdge) / orbRange;

            bool priorDisagree = (alignedPrior > 100.0) && !(orbBody > 0.0);
            bool intradayCont = (alignedRet30 > 25.0) && !(sigExt > 0.25);

            string branch;
            int reqBars;
            if (priorDisagree) { branch = "prior_session_disagreement"; reqBars = 2; }
            else if (intradayCont) { branch = "intraday_continuation"; reqBars = 1; }
            else
            {
                if (submitActual) TSubmitActualEntry(refinedSide, dirSrc, refPath + "->entry_condition_not_met");
                return;
            }

            tPendingFinalDecision = new PendingFinalDecisionT
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

        private void TEvaluateAdmissionAndDirection(int baselineSide, DateTime cUtc, int cMinEt)
        {
            if (CurrentBar < 14) { tBreakoutConsumed = true; TBlockCashDate(); TInvalidatePending(); return; }

            double sigOpen = Open[14];
            double sigHigh = double.NegativeInfinity, sigLow = double.PositiveInfinity;
            for (int k = 0; k < 15; k++)
            {
                DateTime tCloseK = TimeZoneInfo.ConvertTime(Times[0][k], Core.Globals.GeneralOptions.TimeZoneInfo, TimeZoneInfo.Utc);
                if (tCloseK != cUtc.AddMinutes(-k)) { tBreakoutConsumed = true; TBlockCashDate(); TInvalidatePending(); return; }
                sigHigh = Math.Max(sigHigh, High[k]);
                sigLow = Math.Min(sigLow, Low[k]);
            }
            if (!(sigHigh > sigLow)) { tBreakoutConsumed = true; TBlockCashDate(); TInvalidatePending(); return; }
            double sigClose = Close[0];

            double sigRange = sigHigh - sigLow;
            double body = baselineSide * (sigClose - sigOpen) / sigRange;
            double closeLoc = baselineSide == 1 ? (sigClose - sigLow) / sigRange : (sigHigh - sigClose) / sigRange;
            if (body < 0.15 || closeLoc < 0.60) return;

            double confLevel = baselineSide == 1 ? (tOrbHigh + TickSize) : (tOrbLow - TickSize);
            int admTouches = 0;
            for (int k = 0; k < 15; k++)
            {
                if (baselineSide == 1) { if (High[k] >= confLevel) admTouches++; }
                else { if (Low[k] <= confLevel) admTouches++; }
            }
            if (admTouches < 3) { tBreakoutConsumed = true; return; }

            if (!(tOrbOpen > 0.0 && tOrbClose > 0.0 && tCurRthVolSum > 0.0) || tCurRthMinCloses.Count == 0)
            {
                tBreakoutConsumed = true; TBlockCashDate(); TInvalidatePending(); return;
            }

            double prevRthClose = tEligibleRthCloseHistory.Count > 0 ? tEligibleRthCloseHistory[tEligibleRthCloseHistory.Count - 1] : tOrbOpen;
            double priorSessBps = tEligibleSessionRetBps.Count > 0 ? tEligibleSessionRetBps[tEligibleSessionRetBps.Count - 1] : 0.0;
            double priorRet5Bps = LagRetBps(tEligibleRthCloseHistory, 5);
            double priorRet20Bps = LagRetBps(tEligibleRthCloseHistory, 20);
            double rthVwap = tCurRthTypVolSum / tCurRthVolSum;
            double close30mAgo = tCurRthMinCloses.Count <= 30 ? tOrbClose : tCurRthMinCloses[tCurRthMinCloses.Count - 31];

            double gapBps = SafeRetBps(tOrbOpen, prevRthClose);
            double vwapDistBps = SafeRetBps(sigClose, rthVwap);
            double ret30mBps = SafeRetBps(sigClose, close30mAgo);
            double elapsed15m = (cMinEt - 585) / 15.0;

            DateTime dCash = KeyToDate(tCurrentCashDate);
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
                tCurOrbBps,
                admTouches,
                Math.Sin(TwoPi * wkIdx / 5.0),
                Math.Cos(TwoPi * wkIdx / 5.0),
                Math.Sin(TwoPi * (month - 1) / 12.0),
                Math.Cos(TwoPi * (month - 1) / 12.0)
            };
            for (int f = 0; f < 14; f++)
                if (double.IsNaN(features[f]) || double.IsInfinity(features[f])) { tBreakoutConsumed = true; TBlockCashDate(); TInvalidatePending(); return; }

            tBreakoutConsumed = true;
            bool priorOverride = (baselineSide * priorSessBps) < -300.0;
            bool knnOverride = false;
            if (tCurrentCashDate >= KnnMinSessionDate)
            {
                int y = tCurrentCashDate / 10000;
                int m = (tCurrentCashDate / 100) % 100;
                int q = (m - 1) / 3 + 1;
                int qKey = y * 10 + q;
                if (tActiveQuarterKey != qKey)
                {
                    DateTime cutoff = new DateTime(y, (q - 1) * 3 + 1, 1).AddDays(-1);
                    tActiveQuarterModel = TFitQuarterModel(DateToKey(cutoff));
                    tActiveQuarterKey = qKey;
                }
                double flipProb;
                if (TPredictKnn(tActiveQuarterModel, features, out flipProb))
                    knnOverride = flipProb > KnnFlipProbThreshold;
            }

            int dirSide = (priorOverride || knnOverride) ? -baselineSide : baselineSide;
            string dirSrc = (priorOverride && knnOverride) ? "prior_session_and_quarterly_knn"
                          : (priorOverride ? "prior_session" : (knnOverride ? "quarterly_knn" : "breakout"));

            if (tCurrentCashDate >= ShadowMinSessionDate)
            {
                if (tActiveShadowPair != null) { TInvalidatePending(); tDayBlocked = true; }
                else tActiveShadowPair = new ShadowPairT
                {
                    SessionKey = tCurrentCashDate, ExpectedFillOpenUtc = cUtc, BaselineSide = baselineSide,
                    Features = (double[])features.Clone(), PriorTrendAvail = tCurPriorTrendAvail, PriorTrendBps = tCurPriorTrendBps
                };
            }

            if (tDayBlocked) return;

            bool contextReady = tCurPriorOrbQ75Avail && tCurPriorTrendAvail;
            bool submitActual = (tCurrentCashDate >= PortfolioStartCashDate) && contextReady;

            if (features[7] == 1.0 && !(features[4] > 20.0))
            {
                if (submitActual) TSubmitActualEntry(baselineSide, "rc1_breakout_shadow", "direct_first_signal_near_vwap");
                return;
            }

            bool weakSignal = !((dirSide * (sigClose - sigOpen) / sigRange) > 0.20);
            bool highVol = tCurPriorOrbQ75Avail && (tCurOrbBps > tCurPriorOrbQ75Bps);
            double dirConfLevel = dirSide == 1 ? (tOrbHigh + TickSize) : (tOrbLow - TickSize);
            int dirTouches = 0;
            for (int k = 0; k < 15; k++)
            {
                if (dirSide == 1) { if (High[k] >= dirConfLevel) dirTouches++; }
                else { if (Low[k] <= dirConfLevel) dirTouches++; }
            }
            bool highVolTouchVote = highVol && !(dirTouches > 3);

            if (weakSignal || highVolTouchVote)
            {
                tPendingDecision = new PendingDecisionT
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
                TApplyFinalRefinementOrSubmit(dirSide, cUtc, dirSrc, "condition_not_met", submitActual, baselineSide, features, sigClose);
            }
        }

        private void StepModuleT(DateTime barOpenUtc, DateTime barCloseUtc, DateTime openCt, DateTime openEt, DateTime closeEt)
        {
            if (CurrentBar < 15) return;

            int cashDate = DateToKey(openCt.AddHours(7).Date);
            if (cashDate != tCurrentCashDate) TBeginCashDate(cashDate, closeEt);

            bool exactMinute = (barCloseUtc.Second == 0 && barCloseUtc.Millisecond == 0);
            if (tSessionEligible && !tRefOpenCaptured
                && DateToKey(barOpenUtc) == tPrevDayOfCash
                && barOpenUtc.Hour == 23 && barOpenUtc.Minute == 0)
            {
                if (!exactMinute || !(Open[0] > 0.0)) TBlockCashDate();
                else { tRefSessionOpen = Open[0]; tRefOpenCaptured = true; }
            }

            int oDateEt = DateToKey(openEt), cDateEt = DateToKey(closeEt);
            int oMinEt = openEt.Hour * 60 + openEt.Minute;
            int cMinEt = closeEt.Hour * 60 + closeEt.Minute;

            bool inCashWin = (oDateEt == tCurrentCashDate && cDateEt == tCurrentCashDate && oMinEt >= 570 && cMinEt <= 960);

            if (inCashWin && !exactMinute)
            {
                TBlockCashDate(); TInvalidatePending(); CloseVirtualAtBarClose(tLeg, "CashTimeAlignment", Close[0], closeEt); return;
            }
            if (inCashWin)
            {
                if (tLastCashBarCloseUtc != DateTime.MinValue && barOpenUtc != tLastCashBarCloseUtc)
                {
                    TBlockCashDate(); TInvalidatePending(); CloseVirtualAtBarClose(tLeg, "CashDataGap", Close[0], closeEt); return;
                }
                tLastCashBarCloseUtc = barCloseUtc;
                if (!tDayBlocked)
                {
                    tCurRthMinCloses.Add(Close[0]);
                    tCurRthTypVolSum += ((High[0] + Low[0] + Close[0]) / 3.0) * Volume[0];
                    tCurRthVolSum += Volume[0];
                }
            }

            if (inCashWin && tActiveShadowPair != null)
            {
                ShadowPairT sp = tActiveShadowPair;
                if (!sp.Invalid && !sp.LabelRecorded)
                {
                    if (!sp.Initialized)
                    {
                        if (barOpenUtc >= sp.ExpectedFillOpenUtc)
                        {
                            if (barOpenUtc != sp.ExpectedFillOpenUtc) sp.Invalid = true;
                            else
                            {
                                sp.Breakout = TCreateShadowTrade(sp.BaselineSide, Open[0], sp.PriorTrendAvail, sp.PriorTrendBps);
                                sp.Fade = TCreateShadowTrade(-sp.BaselineSide, Open[0], sp.PriorTrendAvail, sp.PriorTrendBps);
                                sp.Initialized = true;
                            }
                        }
                    }
                    if (sp.Initialized && !sp.Invalid)
                    {
                        TProcessShadowBar(sp.Breakout, cMinEt);
                        TProcessShadowBar(sp.Fade, cMinEt);
                        TTryRecordShadowLabel();
                    }
                }
            }

            if (inCashWin && tPendingDecision != null && !tDayBlocked)
            {
                PendingDecisionT pd = tPendingDecision;
                if (barOpenUtc >= pd.ExpectedObsOpenUtc)
                {
                    if (barOpenUtc != pd.ExpectedObsOpenUtc || (barCloseUtc - barOpenUtc).TotalMinutes != 1.0)
                    {
                        tPendingDecision = null; tDayBlocked = true;
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
                                double orbR = tOrbHigh - tOrbLow;
                                double frac = orbR > 0.0 ? mv / orbR : 0.0;
                                if (!(frac > 0.0)) { rSide = -rSide; rPath = "high_vol_vote_flip"; }
                                else rPath = "high_vol_vote_keep";
                            }
                            tPendingDecision = null;
                            TApplyFinalRefinementOrSubmit(rSide, barCloseUtc, pd.DirectionSource, rPath,
                                pd.SubmitActualOrder, pd.BaselineSide, pd.Features, pd.SignalClose);
                        }
                    }
                }
            }

            if (inCashWin && tPendingFinalDecision != null && !tDayBlocked)
            {
                PendingFinalDecisionT pfd = tPendingFinalDecision;
                if (barOpenUtc >= pfd.ExpectedObsOpenUtc)
                {
                    if (barOpenUtc != pfd.ExpectedObsOpenUtc || (barCloseUtc - barOpenUtc).TotalMinutes != 1.0)
                    {
                        tPendingFinalDecision = null; tDayBlocked = true;
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
                            tPendingFinalDecision = null;
                            if (subAct) TSubmitActualEntry(fSide, dSrc, rPath);
                        }
                    }
                }
            }

            if (inCashWin && cMinEt >= 960)
            {
                if (tActiveShadowPair != null)
                {
                    ShadowPairT sp = tActiveShadowPair;
                    if (sp.Invalid || !sp.Initialized) tActiveShadowPair = null;
                    else
                    {
                        if (!sp.Breakout.Complete) { sp.Breakout.ExitPrice = Close[0] - sp.Breakout.Side * TickSize; sp.Breakout.Complete = true; }
                        if (!sp.Fade.Complete) { sp.Fade.ExitPrice = Close[0] - sp.Fade.Side * TickSize; sp.Fade.Complete = true; }
                        TTryRecordShadowLabel();
                    }
                }
                if (!tRthCloseHistoryRecorded && tSessionEligible && tCashWindowIntegrity && tOrbFinalized && tRefOpenCaptured)
                {
                    if (!tOrbHistoryRecorded)
                    {
                        tEligibleOrbHistoryBps.Add(tCurOrbBps);
                        while (tEligibleOrbHistoryBps.Count > 120) tEligibleOrbHistoryBps.RemoveAt(0);
                        tOrbHistoryRecorded = true;
                    }
                    if (Close[0] > 0.0)
                    {
                        double sessRetBps = SafeRetBps(Close[0], tRefSessionOpen);
                        tEligibleRthCloseHistory.Add(Close[0]);
                        while (tEligibleRthCloseHistory.Count > 21) tEligibleRthCloseHistory.RemoveAt(0);
                        tEligibleSessionRetBps.Add(sessRetBps);
                        while (tEligibleSessionRetBps.Count > 1) tEligibleSessionRetBps.RemoveAt(0);
                        tRthCloseHistoryRecorded = true;
                    }
                }
                tCashExitTriggered = true;
                tDayBlocked = true;
                CloseVirtualAtBarClose(tLeg, "CashClose1600ET", Close[0], closeEt);
                return;
            }

            if (tCashExitTriggered)
            {
                CloseVirtualAtBarClose(tLeg, "CashExitFollowup", Close[0], closeEt);
                return;
            }

            bool isQuarterHour = inCashWin && cMinEt >= 600 && cMinEt < 960 && (cMinEt % 15) == 0;

            if (tLeg.Side != 0)
            {
                int posSide = tLeg.Side;
                double entryPx = tLeg.EntryPx;
                if (isQuarterHour && !tManagedStopActivated && tActiveStopTicks >= 1 && entryPx > 0.0)
                {
                    double riskPts = tActiveStopTicks * TickSize;
                    double closeR = posSide * (Close[0] - entryPx) / riskPts;
                    if (closeR >= tActiveTriggerR)
                    {
                        tLeg.StopPx = RoundTick(entryPx + posSide * riskPts * tActiveLockR);
                        tManagedStopActivated = true;
                    }
                }
                if (inCashWin && cMinEt == 930 && !tConditionalExitRequested && tActiveStopTicks >= 1 && entryPx > 0.0)
                {
                    double riskPts = tActiveStopTicks * TickSize;
                    double closeR = posSide * (Close[0] - entryPx) / riskPts;
                    if (closeR < 0.0 || closeR >= 1.0)
                    {
                        tConditionalExitRequested = true;
                        CloseVirtualAtBarClose(tLeg, "Conditional1530ET", Close[0], closeEt);
                    }
                }
                return;
            }

            DateTime dc = KeyToDate(tCurrentCashDate);
            if (tDayBlocked || dc.DayOfWeek == DayOfWeek.Saturday || dc.DayOfWeek == DayOfWeek.Sunday) return;

            if (!tOrbFinalized)
            {
                if (oDateEt == tCurrentCashDate && cDateEt == tCurrentCashDate && oMinEt >= 570 && oMinEt < 585)
                {
                    if (oMinEt != tExpectedNextOrbOpenMin || cMinEt != oMinEt + 1) { TBlockCashDate(); return; }
                    if (tOrbBarCount == 0) tOrbOpen = Open[0];
                    tOrbHigh = tOrbBarCount == 0 ? High[0] : Math.Max(tOrbHigh, High[0]);
                    tOrbLow = tOrbBarCount == 0 ? Low[0] : Math.Min(tOrbLow, Low[0]);
                    tOrbClose = Close[0];
                    tOrbBarCount++;
                    tExpectedNextOrbOpenMin++;
                    if (cMinEt == 585)
                    {
                        if (tOrbBarCount != 15 || !(tOrbHigh >= tOrbLow)) { TBlockCashDate(); return; }
                        tOrbFinalized = true;
                        double mid = 0.5 * (tOrbHigh + tOrbLow);
                        tCurOrbBps = mid > 0.0 ? ((tOrbHigh - tOrbLow) / mid) * 10000.0 : 0.0;
                        tCurPriorOrbQ75Avail = (tEligibleOrbHistoryBps.Count == 120);
                        if (tCurPriorOrbQ75Avail) tCurPriorOrbQ75Bps = LinearPercentile(tEligibleOrbHistoryBps, 0.75);
                    }
                }
                else if (oDateEt == tCurrentCashDate && cDateEt == tCurrentCashDate && cMinEt > 585)
                {
                    TBlockCashDate(); return;
                }
            }

            if (tDayBlocked || !tOrbFinalized || tBreakoutConsumed || !isQuarterHour) return;

            bool longBreak = Close[0] >= RoundTick(tOrbHigh + TickSize);
            bool shortBreak = Close[0] <= RoundTick(tOrbLow - TickSize);
            if (!longBreak && !shortBreak) return;

            TEvaluateAdmissionAndDirection(longBreak ? 1 : -1, barCloseUtc, cMinEt);
        }

        #endregion

        #region Module R (AtrPhaseStop) — 10-min Aggregator Inside 1m Series

        private readonly VirtualLeg rLeg = new VirtualLeg { Name = "R" };
        private bool rPrevCloseReady, rOscReady, rAtrReady, rEmaReady;
        private double rTrSeedSum, rPrevDecisionClose, rOsc, rAtr14, rEma21;
        private int rTrSeedCount, rShadowSide, rPendingReversal;
        private DateTime rVwapDate = DateTime.MinValue;
        private double rVwapVol, rVwapPv;

        // Agregador causal de velas de 10 min desde la serie de 1 min (evita race conditions entre BarsInProgress)
        private bool b10Active;
        private DateTime b10DateEt = DateTime.MinValue;
        private int b10BucketIdx = -1;
        private DateTime b10EndEt, b10AbreEt, b10AbreUtc;
        private double b10Op, b10Hi, b10Lo, b10Cl, b10Vol;

        private void RResetState()
        {
            rPrevCloseReady = rOscReady = rAtrReady = rEmaReady = false;
            rTrSeedSum = rPrevDecisionClose = rOsc = rAtr14 = rEma21 = 0;
            rTrSeedCount = 0;
            rShadowSide = 0;
            rPendingReversal = 0;
            rVwapDate = DateTime.MinValue;
            rVwapVol = rVwapPv = 0;
        }

        private bool RUpdateIndicator(double hi, double lo, double cl)
        {
            double alpha = 2.0 / (21 + 1.0);
            if (!rEmaReady) { rEma21 = cl; rEmaReady = true; }
            else rEma21 = alpha * cl + (1.0 - alpha) * rEma21;

            double tr = !rPrevCloseReady
                ? hi - lo
                : Math.Max(hi - lo, Math.Max(Math.Abs(hi - rPrevDecisionClose), Math.Abs(lo - rPrevDecisionClose)));
            rPrevDecisionClose = cl;
            rPrevCloseReady = true;

            if (!rAtrReady)
            {
                rTrSeedCount++;
                rTrSeedSum += tr;
                if (rTrSeedCount == 14) { rAtr14 = rTrSeedSum / 14.0; rAtrReady = true; }
            }
            else
            {
                rAtr14 = (13.0 * rAtr14 + tr) / 14.0;
            }
            if (!rAtrReady || rAtr14 <= 0 || double.IsNaN(rAtr14)) return false;

            double raw = 100.0 * (cl - rEma21) / (3.0 * rAtr14);
            if (!rOscReady) { rOsc = raw; rOscReady = true; }
            else rOsc = 0.5 * raw + 0.5 * rOsc;
            return true;
        }

        private void REntrar(int lado, DateTime tEt)
        {
            if (ContratosR <= 0 || double.IsNaN(atr20Cme) || atr20Cme <= 0) return;
            int ticks = Math.Max(1, (int)Math.Round(MultiploStopR * atr20Cme / TickSize));
            rLeg.PendingSide = lado;
            rLeg.PendingQty = ContratosR;
            rLeg.PendingStopDist = ticks * TickSize;
            rLeg.PendingTargetDist = double.NaN;
            rLeg.PendingTargetPx = double.NaN;
            rLeg.PendingCheckPassedTarget = false;
            LogMsg(string.Format("TRZ;R;SENAL;{0:yyyy-MM-dd HH:mm};{1};qty={2};sl_t={3}", tEt, lado, ContratosR, ticks));
        }

        private void Process10mBarR(DateTime abreEt, DateTime cierreEt, DateTime abreUtc, double op, double hi, double lo, double cl, double vol)
        {
            int fechaSes = abreEt.Year * 10000 + abreEt.Month * 100 + abreEt.Day;
            if (UsarFechasVendedorR && FechasVendedorR.Contains(fechaSes))
            {
                rShadowSide = 0; rPendingReversal = 0;
                CloseVirtualAtBarClose(rLeg, "INCOMPLETE_SESSION", cl, cierreEt);
                return;
            }

            if (abreUtc.Hour == 0 && abreUtc.Minute == 0 && rPrevCloseReady && Math.Abs(op - rPrevDecisionClose) > 400 * TickSize)
            {
                bool habia = rShadowSide != 0;
                RResetState();
                if (habia) CloseVirtualAtBarClose(rLeg, "ROLL_RESET", cl, cierreEt);
            }

            double prevOsc = rOsc;
            bool prevReady = rOscReady;
            bool ready = RUpdateIndicator(hi, lo, cl);

            bool vwapOk = false;
            int abreMin = abreEt.Hour * 60 + abreEt.Minute;
            if (abreMin >= 570 && abreMin < 960)
            {
                if (rVwapDate != abreEt.Date) { rVwapDate = abreEt.Date; rVwapVol = 0; rVwapPv = 0; }
                rVwapPv += (hi + lo + cl) / 3.0 * vol;
                rVwapVol += vol;
                if (rVwapVol > 0 && rAtrReady) vwapOk = Math.Abs(cl - rVwapPv / rVwapVol) < 2.5 * rAtr14;
            }

            int cierreMin = cierreEt.Hour * 60 + cierreEt.Minute;
            if (cierreMin == 960)
            {
                rShadowSide = 0; rPendingReversal = 0;
                CloseVirtualAtBarClose(rLeg, "CASH_CLOSE", cl, cierreEt);
                return;
            }
            if (!prevReady || !ready) return;

            bool alcista = !double.IsNaN(prevOsc) && prevOsc <= 100.0 && rOsc > 100.0;
            bool bajista = !double.IsNaN(prevOsc) && prevOsc >= -100.0 && rOsc < -100.0;
            if (!alcista && !bajista) return;

            int nuevo = alcista ? 1 : -1;
            if (rShadowSide == nuevo) return;

            bool enVentana = cierreMin >= 570 && cierreMin < 660;
            bool plano = !rLeg.HasExposure();

            if (rShadowSide == 0)
            {
                if (!enVentana) return;
                rShadowSide = nuevo;
                if (vwapOk && plano && CurrentBar >= BarsRequiredToTrade) REntrar(nuevo, cierreEt);
                return;
            }
            if (!enVentana)
            {
                rShadowSide = 0; rPendingReversal = 0;
                CloseVirtualAtBarClose(rLeg, "OPPOSITE", cl, cierreEt);
                return;
            }
            rShadowSide = nuevo;
            if (!plano)
            {
                rPendingReversal = vwapOk ? nuevo : 0;
                CloseVirtualAtBarClose(rLeg, "REVERSAL", cl, cierreEt);
                return;
            }
            if (vwapOk && CurrentBar >= BarsRequiredToTrade) REntrar(nuevo, cierreEt);
        }

        private void StepModuleR(DateTime openEt, DateTime closeEt, DateTime barOpenUtc)
        {
            if (rPendingReversal != 0 && !rLeg.HasExposure() && CurrentBar >= BarsRequiredToTrade)
            {
                int lado = rPendingReversal;
                rPendingReversal = 0;
                REntrar(lado, closeEt);
            }

            int bIdx = (openEt.Hour * 60 + openEt.Minute) / 10;
            if (b10Active && (openEt.Date != b10DateEt || bIdx != b10BucketIdx))
            {
                Process10mBarR(b10AbreEt, b10EndEt, b10AbreUtc, b10Op, b10Hi, b10Lo, b10Cl, b10Vol);
                b10Active = false;
            }

            if (!b10Active)
            {
                b10Active = true;
                b10DateEt = openEt.Date;
                b10BucketIdx = bIdx;
                b10AbreEt = openEt.Date.AddMinutes(bIdx * 10);
                b10EndEt = openEt.Date.AddMinutes((bIdx + 1) * 10);
                TimeSpan diffEtToUtc = barOpenUtc - openEt;
                b10AbreUtc = b10AbreEt + diffEtToUtc;
                b10Op = Open[0];
                b10Hi = High[0];
                b10Lo = Low[0];
                b10Cl = Close[0];
                b10Vol = Volume[0];
            }
            else
            {
                b10Hi = Math.Max(b10Hi, High[0]);
                b10Lo = Math.Min(b10Lo, Low[0]);
                b10Cl = Close[0];
                b10Vol += Volume[0];
            }

            if (closeEt == b10EndEt)
            {
                Process10mBarR(b10AbreEt, b10EndEt, b10AbreUtc, b10Op, b10Hi, b10Lo, b10Cl, b10Vol);
                b10Active = false;
            }
        }

        #endregion

        #region Module Z (Z-Banda: 1 celda o 9 celdas)

        private class ZetaSlot
        {
            public readonly int BucketMinutes;
            public readonly int EmaPeriod;
            public readonly double MinEfficiencyPct;
            public readonly int Qty;
            public readonly VirtualLeg Leg;

            private readonly double emaAlpha;
            private readonly double[] emaSeed;
            private int emaSeedCount;
            private bool emaReady;
            private double emaValue;

            private bool bucketActive, bucketValid;
            private int bucketIndex, bucketCount;
            private double bucketHigh, bucketLow, bucketClose;

            private bool sessionActive, sessionValid, sessionEmaObservable, sessionTouchFree;
            private int sessionDateKey, sessionBucketCount, sessionMinuteCount;
            private double sessionOpen, sessionHigh, sessionLow, sessionClose;

            private bool pendingEntry, pendingQualified, pendingSummaryAvailable;
            private int pendingEntryDirection, pendingEntrySessionKey, pendingSessionDateKey;
            private double pendingEntryTarget;

            private const int SessionStartMinCt = 510;
            private const int SessionEndMinCt = 900;
            private const int MinDateKey = 20100101;
            private const int MaxDateKey = 20270902;

            public ZetaSlot(string name, int bucketMin, int emaPer, double minEff, int qty)
            {
                BucketMinutes = bucketMin;
                EmaPeriod = emaPer;
                MinEfficiencyPct = minEff;
                Qty = qty;
                Leg = new VirtualLeg { Name = name };
                emaAlpha = 2.0 / (emaPer + 1.0);
                emaSeed = new double[emaPer];
            }

            private void ResetEma() { emaSeedCount = 0; emaReady = false; emaValue = 0.0; }
            private void ResetBucket()
            {
                bucketActive = false; bucketIndex = -1; bucketCount = 0;
                bucketValid = true; bucketHigh = bucketLow = bucketClose = 0.0;
            }

            private void UpdateEma(double closePx)
            {
                if (!(closePx > 0.0)) return;
                if (!emaReady)
                {
                    if (emaSeedCount < EmaPeriod) { emaSeed[emaSeedCount++] = closePx; }
                    if (emaSeedCount == EmaPeriod)
                    {
                        double sum = 0.0;
                        for (int k = 0; k < EmaPeriod; k++) sum += emaSeed[k];
                        emaValue = sum / EmaPeriod;
                        emaReady = true;
                    }
                    return;
                }
                emaValue = emaValue + emaAlpha * (closePx - emaValue);
            }

            private static bool IsFullSession(int key)
            {
                DateTime dt;
                try { dt = KeyToDate(key); } catch { return false; }
                if (dt.DayOfWeek == DayOfWeek.Saturday || dt.DayOfWeek == DayOfWeek.Sunday) return false;
                if (key >= MinDateKey && key <= MaxDateKey) return !NonFullNyseZ.Contains(key);
                return true;
            }

            private static int NextFullSession(int key)
            {
                DateTime dt;
                try { dt = KeyToDate(key); } catch { return 0; }
                for (int step = 0; step < 20; step++)
                {
                    dt = dt.AddDays(1);
                    int k = DateToKey(dt);
                    if (IsFullSession(k)) return k;
                }
                return 0;
            }

            private void StartSession(int key, double op, double hi, double lo, double cl)
            {
                sessionActive = true; sessionDateKey = key; sessionValid = true;
                sessionBucketCount = 0; sessionMinuteCount = 0;
                sessionOpen = op; sessionHigh = hi; sessionLow = lo; sessionClose = cl;
                sessionEmaObservable = true; sessionTouchFree = true;
                ResetBucket();
            }

            private void FinalizeSession()
            {
                if (!sessionActive) return;
                if (bucketActive) { sessionValid = false; ResetBucket(); ResetEma(); }

                int expectedMinutes = SessionEndMinCt - SessionStartMinCt;
                int expectedBuckets = expectedMinutes / BucketMinutes;
                bool allBarsValid = sessionValid && sessionMinuteCount == expectedMinutes && sessionBucketCount == expectedBuckets;
                double sessionRange = sessionHigh - sessionLow;
                double efficiency = sessionRange <= 0.0 ? 0.0 : (100.0 * Math.Abs(sessionClose - sessionOpen) / sessionRange);

                pendingSummaryAvailable = true;
                pendingQualified = allBarsValid
                    && sessionEmaObservable
                    && sessionRange > 0.0
                    && sessionTouchFree
                    && efficiency >= MinEfficiencyPct;
                pendingSessionDateKey = sessionDateKey;

                if (!allBarsValid) ResetEma();
                sessionActive = false;
                ResetBucket();
            }

            private bool UpdateBucket(int minuteOffset, double hi, double lo, double cl)
            {
                int bSize = BucketMinutes;
                int bIdx = minuteOffset / bSize;
                int bMin = minuteOffset % bSize;

                if (bucketActive && bucketIndex != bIdx)
                {
                    sessionValid = false; ResetBucket(); ResetEma();
                }
                if (!bucketActive)
                {
                    bucketActive = true; bucketIndex = bIdx; bucketCount = 0;
                    bucketValid = (bMin == 0) && (bIdx == sessionBucketCount);
                    bucketHigh = hi; bucketLow = lo; bucketClose = cl;
                }
                else
                {
                    bucketHigh = Math.Max(bucketHigh, hi);
                    bucketLow = Math.Min(bucketLow, lo);
                    bucketClose = cl;
                }

                if (bMin != bucketCount) bucketValid = false;
                bucketCount++;
                if (bMin != bSize - 1) return false;

                if (!bucketValid || bucketCount != bSize)
                {
                    sessionValid = false; ResetEma(); ResetBucket(); return false;
                }
                if (!emaReady) sessionEmaObservable = false;
                else if (bucketLow <= emaValue && emaValue <= bucketHigh) sessionTouchFree = false;

                UpdateEma(bucketClose);
                sessionBucketCount++;
                ResetBucket();
                return true;
            }

            public void StepBar(EdgeLabTRZ host, DateTime openCt, double op, double hi, double lo, double cl, DateTime closeEt)
            {
                if (Qty <= 0) return;

                int key = DateToKey(openCt);
                int minCt = openCt.Hour * 60 + openCt.Minute;
                if (minCt < SessionStartMinCt || minCt >= SessionEndMinCt || !IsFullSession(key))
                    return;

                if (!sessionActive || sessionDateKey != key)
                {
                    if (sessionActive) FinalizeSession();

                    if (pendingSummaryAvailable)
                    {
                        int nxt = NextFullSession(pendingSessionDateKey);
                        if (nxt != key) { ResetEma(); pendingQualified = false; pendingSummaryAvailable = false; }
                    }
                    bool qualifiedFromPrev = pendingSummaryAvailable && pendingQualified;
                    pendingQualified = false;
                    pendingSummaryAvailable = false;

                    if (Leg.HasExposure()) host.CloseVirtualAtBarClose(Leg, "SESSION_SAFETY", cl, closeEt);

                    StartSession(key, op, hi, lo, cl);

                    if (minCt == SessionStartMinCt && qualifiedFromPrev && emaReady)
                    {
                        int dir = op > emaValue ? -1 : (op < emaValue ? 1 : 0);
                        if (dir != 0)
                        {
                            pendingEntry = true;
                            pendingEntryDirection = dir;
                            pendingEntryTarget = emaValue;
                            pendingEntrySessionKey = key;
                        }
                    }
                }

                int minuteOffset = minCt - SessionStartMinCt;
                if (minuteOffset != sessionMinuteCount) sessionValid = false;
                sessionMinuteCount++;
                sessionHigh = Math.Max(sessionHigh, hi);
                sessionLow = Math.Min(sessionLow, lo);
                sessionClose = cl;

                bool bucketClosed = UpdateBucket(minuteOffset, hi, lo, cl);

                if (pendingEntry && minCt == SessionStartMinCt)
                {
                    if (pendingEntryDirection <= 0) { if (!(lo > pendingEntryTarget)) pendingEntry = false; }
                    else { if (!(hi < pendingEntryTarget)) pendingEntry = false; }
                }

                if (pendingEntry && minCt == SessionStartMinCt && key == pendingEntrySessionKey)
                {
                    bool stillValid = pendingEntryDirection <= 0 ? (cl > pendingEntryTarget) : (cl < pendingEntryTarget);
                    if (stillValid && !Leg.HasExposure())
                    {
                        if (host.MultiploStopZ > 0 && (double.IsNaN(host.atr20Cme) || host.atr20Cme <= 0))
                        {
                            host.LogMsg(string.Format("TRZ;{0};OMITIDA;{1};sin ATR20", Leg.Name, key));
                        }
                        else
                        {
                            double tgtPx = host.RoundZetaTarget(pendingEntryDirection, pendingEntryTarget);
                            double stopDist = host.MultiploStopZ > 0
                                ? Math.Max(host.TickSize, Math.Round((host.MultiploStopZ * host.atr20Cme) / host.TickSize) * host.TickSize)
                                : double.NaN;
                            Leg.PendingSide = pendingEntryDirection;
                            Leg.PendingQty = Qty;
                            Leg.PendingStopDist = stopDist;
                            Leg.PendingTargetDist = double.NaN;
                            Leg.PendingTargetPx = tgtPx;
                            Leg.PendingCheckPassedTarget = true;
                            host.LogMsg(string.Format("TRZ;{0};SENAL;{1};{2};qty={3};tgt={4:F2};ema={5:F2};atr20={6:F2}",
                                Leg.Name, key, pendingEntryDirection, Qty, tgtPx, emaValue, host.atr20Cme));
                        }
                    }
                    pendingEntry = false;
                }
                else if (pendingEntry && minCt != SessionStartMinCt)
                {
                    pendingEntry = false;
                }

                if (bucketClosed && Leg.Side != 0 && emaReady)
                {
                    Leg.TargetPx = host.RoundZetaTarget(Leg.Side, emaValue);
                }

                int lastMinute = SessionEndMinCt - 1;
                if (minCt >= lastMinute && Leg.HasExposure())
                {
                    host.CloseVirtualAtBarClose(Leg, "EOD", cl, closeEt);
                }
                if (minCt == lastMinute) FinalizeSession();
            }
        }

        private readonly List<ZetaSlot> zSlots = new List<ZetaSlot>();

        #endregion

        #region NinjaScript Lifecycle & Net Sync

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabTRZ";
                Description = "Canasta unificada T (FtmOrb) + R (AtrPhaseStop) + Z-banda con seguimiento virtual y posición neta.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 30;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 20;

                ContratosT = 5;
                ContratosR = 5;
                ContratosZ = 1;
                UsarZBandaCompleta9 = false;
                LogSenales = false;

                UseExclusionCalendars = true;
                ShadowMinSessionDate = 20100101;
                KnnMinSessionDate = 20120101;
                PortfolioStartCashDate = 20120101;
                KnnMinTrainingRows = 100;
                KnnK = 15;
                KnnFlipProbThreshold = 0.65;

                MultiploStopR = 0.25;
                UsarFechasVendedorR = false;

                ZBucketMinutes = 15;
                ZEmaPeriod = 20;
                ZMinEfficiencyPct = 45.0;
                MultiploStopZ = 0.25;

                PerdidaDiariaUSD = 0;
                PisoCuentaUSD = 0;
                MargenPisoUSD = 100;
                HoraPlanoET = 1645;
            }
            else if (State == State.DataLoaded)
            {
                ct = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

                zSlots.Clear();
                if (ContratosZ > 0)
                {
                    if (UsarZBandaCompleta9)
                    {
                        int[] buckets = { 10, 15, 30 };
                        int[] emas = { 30, 20, 10 };
                        double[] effs = { 35.0, 45.0, 55.0 };
                        for (int i = 0; i < 3; i++)
                            foreach (double e in effs)
                            {
                                string nm = string.Format("Z_{0}_{1}_{2}", buckets[i], emas[i], (int)e);
                                zSlots.Add(new ZetaSlot(nm, buckets[i], emas[i], e, ContratosZ));
                            }
                    }
                    else
                    {
                        zSlots.Add(new ZetaSlot("Z", ZBucketMinutes, ZEmaPeriod, ZMinEfficiencyPct, ContratosZ));
                    }
                }
            }
        }

        private void ResolveAllVirtualLegs(DateTime tEt)
        {
            string reason; double exitPx;
            if (ResolveVirtualBar(tLeg, Open[0], High[0], Low[0], RoundTick, out reason, out exitPx))
                LogMsg(string.Format("TRZ;T;CIERRE;{0:yyyy-MM-dd HH:mm};{1};px={2:F2}", tEt, reason, exitPx));

            if (ResolveVirtualBar(rLeg, Open[0], High[0], Low[0], RoundTick, out reason, out exitPx))
                LogMsg(string.Format("TRZ;R;CIERRE;{0:yyyy-MM-dd HH:mm};{1};px={2:F2}", tEt, reason, exitPx));

            foreach (ZetaSlot slot in zSlots)
            {
                if (ResolveVirtualBar(slot.Leg, Open[0], High[0], Low[0], RoundTick, out reason, out exitPx))
                    LogMsg(string.Format("TRZ;{0};CIERRE;{1:yyyy-MM-dd HH:mm};{2};px={3:F2}", slot.Leg.Name, tEt, reason, exitPx));
            }
        }

        private int ComputeDesiredNet()
        {
            int net = tLeg.NetDesired() + rLeg.NetDesired();
            foreach (ZetaSlot slot in zSlots) net += slot.Leg.NetDesired();
            return net;
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
            double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string nativeError)
        {
            if (order == activeSyncOrder && (orderState == OrderState.Filled || orderState == OrderState.Cancelled
                || orderState == OrderState.Rejected || orderState == OrderState.Unknown))
            {
                activeSyncOrder = null;
            }
        }

        private void SyncNetPosition(int desiredNet)
        {
            if (State == State.Realtime && activeSyncOrder != null
                && (activeSyncOrder.OrderState == OrderState.Working
                    || activeSyncOrder.OrderState == OrderState.Accepted
                    || activeSyncOrder.OrderState == OrderState.Submitted))
                return;

            int curNet = Position.MarketPosition == MarketPosition.Long ? Position.Quantity
                       : (Position.MarketPosition == MarketPosition.Short ? -Position.Quantity : 0);
            if (curNet == desiredNet) return;

            if (desiredNet == 0)
            {
                if (curNet > 0) activeSyncOrder = ExitLong(0, curNet, "TRZ_FLAT", "");
                else if (curNet < 0) activeSyncOrder = ExitShort(0, -curNet, "TRZ_FLAT", "");
                return;
            }

            if (curNet == 0)
            {
                activeSyncOrder = desiredNet > 0
                    ? EnterLong(0, desiredNet, SigNetLong)
                    : EnterShort(0, -desiredNet, SigNetShort);
                return;
            }

            bool sameDir = (curNet > 0 && desiredNet > 0) || (curNet < 0 && desiredNet < 0);
            if (sameDir)
            {
                int absCur = Math.Abs(curNet);
                int absDes = Math.Abs(desiredNet);
                if (absDes > absCur)
                {
                    activeSyncOrder = desiredNet > 0
                        ? EnterLong(0, absDes - absCur, SigNetLong)
                        : EnterShort(0, absDes - absCur, SigNetShort);
                }
                else
                {
                    int reduce = absCur - absDes;
                    activeSyncOrder = curNet > 0
                        ? ExitLong(0, reduce, "TRZ_RED", "")
                        : ExitShort(0, reduce, "TRZ_RED", "");
                }
                return;
            }

            // Cambio de signo neto: en Managed Mode EnterLong/EnterShort revierte la posición opuesta al tamaño destino.
            activeSyncOrder = desiredNet > 0
                ? EnterLong(0, desiredNet, SigNetLong)
                : EnterShort(0, -desiredNet, SigNetShort);
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0) return;

            DateTime barCloseLocal = Times[0][0];
            DateTime barCloseUtc = TimeZoneInfo.ConvertTime(barCloseLocal, Core.Globals.GeneralOptions.TimeZoneInfo, TimeZoneInfo.Utc);
            DateTime barOpenUtc = barCloseUtc.AddMinutes(-1);
            DateTime openEt = TimeZoneInfo.ConvertTimeFromUtc(barOpenUtc, et);
            DateTime closeEt = TimeZoneInfo.ConvertTimeFromUtc(barCloseUtc, et);
            DateTime openCt = TimeZoneInfo.ConvertTimeFromUtc(barOpenUtc, ct);

            UpdateCmeAtr20(openEt, High[0], Low[0]);

            if (CurrentBar < 2) return;

            ResolveAllVirtualLegs(closeEt);

            bool guardActive = CheckRealtimeGuard(closeEt);

            // Actualizar siempre los motores para mantener continuos EMA, ATR, KNN e historiales de sesión.
            StepModuleT(barOpenUtc, barCloseUtc, openCt, openEt, closeEt);
            StepModuleR(openEt, closeEt, barOpenUtc);
            foreach (ZetaSlot slot in zSlots)
                slot.StepBar(this, openCt, Open[0], High[0], Low[0], Close[0], closeEt);

            if (guardActive)
            {
                ClearAllVirtualExposures();
                if (CurrentBar >= BarsRequiredToTrade) SyncNetPosition(0);
                return;
            }

            int desiredNet = ComputeDesiredNet();
            if (CurrentBar >= BarsRequiredToTrade) SyncNetPosition(desiredNet);
        }

        #endregion

        #region Properties

        [NinjaScriptProperty, Range(0, 1000), Display(Name = "Contratos T (0 = desactivado)", Order = 1, GroupName = "1. Canasta (T + R + Z)")]
        public int ContratosT { get; set; }
        [NinjaScriptProperty, Range(0, 1000), Display(Name = "Contratos R (0 = desactivado)", Order = 2, GroupName = "1. Canasta (T + R + Z)")]
        public int ContratosR { get; set; }
        [NinjaScriptProperty, Range(0, 1000), Display(Name = "Contratos Z (por celda si banda=true)", Order = 3, GroupName = "1. Canasta (T + R + Z)")]
        public int ContratosZ { get; set; }
        [NinjaScriptProperty, Display(Name = "Usar Z-Banda completa (9 celdas)", Order = 4, GroupName = "1. Canasta (T + R + Z)")]
        public bool UsarZBandaCompleta9 { get; set; }
        [NinjaScriptProperty, Display(Name = "Log de señales virtuales en Output", Order = 5, GroupName = "1. Canasta (T + R + Z)")]
        public bool LogSenales { get; set; }

        [NinjaScriptProperty, Display(Name = "UseExclusionCalendars (true)", Order = 1, GroupName = "2. T (FtmOrb)")]
        public bool UseExclusionCalendars { get; set; }
        [NinjaScriptProperty, Display(Name = "ShadowMinSessionDate (20100101)", Order = 2, GroupName = "2. T (FtmOrb)")]
        public int ShadowMinSessionDate { get; set; }
        [NinjaScriptProperty, Display(Name = "KnnMinSessionDate (20120101)", Order = 3, GroupName = "2. T (FtmOrb)")]
        public int KnnMinSessionDate { get; set; }
        [NinjaScriptProperty, Display(Name = "PortfolioStartCashDate (20120101)", Order = 4, GroupName = "2. T (FtmOrb)")]
        public int PortfolioStartCashDate { get; set; }
        [NinjaScriptProperty, Range(15, 500), Display(Name = "KnnMinTrainingRows (100)", Order = 5, GroupName = "2. T (FtmOrb)")]
        public int KnnMinTrainingRows { get; set; }
        [NinjaScriptProperty, Range(3, 50), Display(Name = "KnnK (15)", Order = 6, GroupName = "2. T (FtmOrb)")]
        public int KnnK { get; set; }
        [NinjaScriptProperty, Range(0.5, 1.0), Display(Name = "KnnFlipProbThreshold (0.65)", Order = 7, GroupName = "2. T (FtmOrb)")]
        public double KnnFlipProbThreshold { get; set; }

        [NinjaScriptProperty, Range(0.05, 5.0), Display(Name = "Stop R (x ATR20 de sesión)", Order = 1, GroupName = "3. R (AtrPhaseStop)")]
        public double MultiploStopR { get; set; }
        [NinjaScriptProperty, Display(Name = "Usar fechas bloqueadas del vendedor (R)", Order = 2, GroupName = "3. R (AtrPhaseStop)")]
        public bool UsarFechasVendedorR { get; set; }

        [NinjaScriptProperty, Range(5, 60), Display(Name = "Z BucketMinutes (si banda=false)", Order = 1, GroupName = "4. Z (ZetaBand)")]
        public int ZBucketMinutes { get; set; }
        [NinjaScriptProperty, Range(5, 60), Display(Name = "Z EmaPeriod (si banda=false)", Order = 2, GroupName = "4. Z (ZetaBand)")]
        public int ZEmaPeriod { get; set; }
        [NinjaScriptProperty, Range(5, 95), Display(Name = "Z MinEfficiencyPct (si banda=false)", Order = 3, GroupName = "4. Z (ZetaBand)")]
        public double ZMinEfficiencyPct { get; set; }
        [NinjaScriptProperty, Range(0, 5), Display(Name = "Stop Z (x ATR20 de sesión, 0=sin)", Order = 4, GroupName = "4. Z (ZetaBand)")]
        public double MultiploStopZ { get; set; }

        [NinjaScriptProperty, Range(0, 100000), Display(Name = "DLL diaria USD (0 = sin DLL; ej. 1200/2700)", Order = 1, GroupName = "5. Guarda Lucid (Realtime)")]
        public double PerdidaDiariaUSD { get; set; }
        [NinjaScriptProperty, Range(0, 10000000), Display(Name = "Piso de cuenta USD (0 = sin piso)", Order = 2, GroupName = "5. Guarda Lucid (Realtime)")]
        public double PisoCuentaUSD { get; set; }
        [NinjaScriptProperty, Range(0, 100000), Display(Name = "Margen sobre el piso USD", Order = 3, GroupName = "5. Guarda Lucid (Realtime)")]
        public double MargenPisoUSD { get; set; }
        [NinjaScriptProperty, Display(Name = "Hora plano obligatorio ET (HHMM; 0=no)", Order = 4, GroupName = "5. Guarda Lucid (Realtime)")]
        public int HoraPlanoET { get; set; }

        #endregion
    }
}
