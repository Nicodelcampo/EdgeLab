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

// EdgeLabZetaBand (version=1.0, 2026-11-20) — Z-banda (ZetaTrendDay) con stop de catástrofe 0,25 × ATR20 de sesión CME.
// Uso exclusivo de validación de paridad y prueba de comisiones en NinjaTrader 8. No es un edge promovido.
//
// Especificación: edgelab/research/fundedsyncstack/modulos_r_z_e_q.py (run_z, _ZetaEngine) + PREREGISTRO_ZBANDA.md.
//   Gráfico de 1 minuto de NQ o MNQ, plantilla ETH. Calculate = OnBarClose.
//   La banda de 9 configuraciones equivale a:
//     (BucketMinutes, EmaPeriod) in {(10, 30), (15, 20), (30, 10)} x MinEfficiencyPct in {35, 45, 55}.
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabZetaBand : Strategy
    {
        private const int SessionStartMinCt = 510;  // 08:30 CT (09:30 ET)
        private const int SessionEndMinCt = 900;    // 15:00 CT (16:00 ET) -> 390 min
        private const int MinDateKey = 20100101;
        private const int MaxDateKey = 20270902;
        private const string SigL = "Z_L";
        private const string SigS = "Z_S";

        private static readonly HashSet<int> NonFullNyse = new HashSet<int>
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

        private TimeZoneInfo ct, et;

        // ATR20 de sesión CME (serie 1m, idéntico a EdgeLabAtrPhaseStop)
        private DateTime sesionActual = DateTime.MinValue;
        private double sesHi = double.MinValue, sesLo = double.MaxValue;
        private readonly Queue<double> rangos = new Queue<double>();
        private double atr20 = double.NaN;

        // Estado _ZetaEngine
        private double emaAlpha;
        private double[] emaSeed;
        private int emaSeedCount;
        private bool emaReady;
        private double emaValue;

        private bool bucketActive, bucketValid;
        private int bucketIndex, bucketCount;
        private double bucketHigh, bucketLow, bucketClose;

        private bool sessionActive, sessionValid, sessionEmaObservable, sessionTouchFree;
        private int sessionDateKey, sessionBucketCount, sessionMinuteCount;
        private double sessionOpen, sessionHigh, sessionLow, sessionClose;

        private bool pendingEntry;
        private int pendingEntryDirection, pendingEntrySessionKey;
        private double pendingEntryTarget;

        private bool pendingQualified, pendingSummaryAvailable;
        private int pendingSessionDateKey;

        // Gestión activa de stop/target
        private double activeTargetPx = double.NaN;
        private double activeStopDist = double.NaN;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabZetaBand";
                Description = "Z-banda (ZetaTrendDay) con stop de catástrofe 0,25 × ATR20 CME. Validación de paridad y comisiones NT8.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 2;

                BucketMinutes = 15;
                EmaPeriod = 20;
                MinEfficiencyPct = 45.0;
                Cantidad = 1;
                MultiploStopAtr20 = 0.25;
            }
            else if (State == State.DataLoaded)
            {
                ct = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                emaAlpha = 2.0 / (EmaPeriod + 1.0);
                emaSeed = new double[EmaPeriod];
                ResetState();
            }
        }

        private void ResetState()
        {
            ResetEma();
            ResetBucket();
            sessionActive = false;
            sessionDateKey = 0;
            sessionValid = false;
            sessionBucketCount = 0;
            sessionMinuteCount = 0;
            sessionOpen = sessionHigh = sessionLow = sessionClose = 0.0;
            sessionEmaObservable = false;
            sessionTouchFree = false;
            pendingEntry = false;
            pendingEntryDirection = 0;
            pendingEntryTarget = 0.0;
            pendingEntrySessionKey = 0;
            pendingQualified = false;
            pendingSummaryAvailable = false;
            pendingSessionDateKey = 0;
        }

        private void ResetEma()
        {
            emaSeedCount = 0;
            emaReady = false;
            emaValue = 0.0;
        }

        private void ResetBucket()
        {
            bucketActive = false;
            bucketIndex = -1;
            bucketCount = 0;
            bucketValid = true;
            bucketHigh = bucketLow = bucketClose = 0.0;
        }

        private void UpdateEma(double closePx)
        {
            if (!(closePx > 0.0)) return;
            if (!emaReady)
            {
                if (emaSeedCount < EmaPeriod)
                {
                    emaSeed[emaSeedCount] = closePx;
                    emaSeedCount++;
                }
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

        private static bool IsFullZetaSession(int key)
        {
            DateTime dt;
            if (!TryDateFromKey(key, out dt)) return false;
            if (dt.DayOfWeek == DayOfWeek.Saturday || dt.DayOfWeek == DayOfWeek.Sunday) return false;
            if (key >= MinDateKey && key <= MaxDateKey) return !NonFullNyse.Contains(key);
            return true;
        }

        private static int NextFullZetaSession(int key)
        {
            DateTime dt;
            if (!TryDateFromKey(key, out dt)) return 0;
            for (int step = 0; step < 20; step++)
            {
                dt = dt.AddDays(1);
                int k = dt.Year * 10000 + dt.Month * 100 + dt.Day;
                if (IsFullZetaSession(k)) return k;
            }
            return 0;
        }

        private static bool TryDateFromKey(int key, out DateTime dt)
        {
            int y = key / 10000;
            int m = (key / 100) % 100;
            int d = key % 100;
            try
            {
                dt = new DateTime(y, m, d);
                return true;
            }
            catch
            {
                dt = DateTime.MinValue;
                return false;
            }
        }

        private double RoundZetaTarget(int side, double price)
        {
            if (side <= 0) return Math.Floor(price / TickSize) * TickSize;
            return Math.Ceiling(price / TickSize) * TickSize;
        }

        private void StartSession(int key, double op, double hi, double lo, double cl)
        {
            sessionActive = true;
            sessionDateKey = key;
            sessionValid = true;
            sessionBucketCount = 0;
            sessionMinuteCount = 0;
            sessionOpen = op;
            sessionHigh = hi;
            sessionLow = lo;
            sessionClose = cl;
            sessionEmaObservable = true;
            sessionTouchFree = true;
            ResetBucket();
        }

        private void FinalizeSession()
        {
            if (!sessionActive) return;
            if (bucketActive)
            {
                sessionValid = false;
                ResetBucket();
                ResetEma();
            }

            int expectedMinutes = SessionEndMinCt - SessionStartMinCt; // 390
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
                sessionValid = false;
                ResetBucket();
                ResetEma();
            }

            if (!bucketActive)
            {
                bucketActive = true;
                bucketIndex = bIdx;
                bucketCount = 0;
                bucketValid = (bMin == 0) && (bIdx == sessionBucketCount);
                bucketHigh = hi;
                bucketLow = lo;
                bucketClose = cl;
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
                sessionValid = false;
                ResetEma();
                ResetBucket();
                return false;
            }

            if (!emaReady)
                sessionEmaObservable = false;
            else if (bucketLow <= emaValue && emaValue <= bucketHigh)
                sessionTouchFree = false;

            UpdateEma(bucketClose);
            sessionBucketCount++;
            ResetBucket();
            return true;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0) return;

            // ATR20 CME (session 18:00 ET -> next day)
            DateTime barCloseLocal = Times[0][0];
            DateTime barOpenEt = TimeZoneInfo.ConvertTime(barCloseLocal.AddMinutes(-1), Core.Globals.GeneralOptions.TimeZoneInfo, et);
            DateTime cmeSes = barOpenEt.AddHours(6).Date;
            if (cmeSes != sesionActual)
            {
                if (sesionActual != DateTime.MinValue && sesHi > sesLo)
                {
                    rangos.Enqueue(sesHi - sesLo);
                    while (rangos.Count > 20) rangos.Dequeue();
                }
                atr20 = rangos.Count == 20 ? rangos.Average() : double.NaN;
                sesionActual = cmeSes;
                sesHi = double.MinValue;
                sesLo = double.MaxValue;
            }
            sesHi = Math.Max(sesHi, High[0]);
            sesLo = Math.Min(sesLo, Low[0]);

            if (CurrentBar < 1) return;

            DateTime openCt = TimeZoneInfo.ConvertTime(barCloseLocal.AddMinutes(-1), Core.Globals.GeneralOptions.TimeZoneInfo, ct);
            int key = openCt.Year * 10000 + openCt.Month * 100 + openCt.Day;
            int minCt = openCt.Hour * 60 + openCt.Minute;

            if (minCt < SessionStartMinCt || minCt >= SessionEndMinCt || !IsFullZetaSession(key))
                return;

            if (!sessionActive || sessionDateKey != key)
            {
                if (sessionActive) FinalizeSession();

                if (pendingSummaryAvailable)
                {
                    int nxt = NextFullZetaSession(pendingSessionDateKey);
                    if (nxt != key)
                    {
                        ResetEma();
                        pendingQualified = false;
                        pendingSummaryAvailable = false;
                    }
                }

                bool qualifiedFromPrev = pendingSummaryAvailable && pendingQualified;
                pendingQualified = false;
                pendingSummaryAvailable = false;

                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("SESSION_SAFETY", SigL);
                    else ExitShort("SESSION_SAFETY", SigS);
                }

                StartSession(key, Open[0], High[0], Low[0], Close[0]);

                if (minCt == SessionStartMinCt && qualifiedFromPrev && emaReady)
                {
                    int dir = Open[0] > emaValue ? -1 : (Open[0] < emaValue ? 1 : 0);
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
            sessionHigh = Math.Max(sessionHigh, High[0]);
            sessionLow = Math.Min(sessionLow, Low[0]);
            sessionClose = Close[0];

            bool bucketClosed = UpdateBucket(minuteOffset, High[0], Low[0], Close[0]);

            if (pendingEntry && minCt == SessionStartMinCt)
            {
                if (pendingEntryDirection <= 0)
                {
                    if (!(Low[0] > pendingEntryTarget)) pendingEntry = false;
                }
                else
                {
                    if (!(High[0] < pendingEntryTarget)) pendingEntry = false;
                }
            }

            if (pendingEntry && minCt == SessionStartMinCt && key == pendingEntrySessionKey)
            {
                bool stillValid = pendingEntryDirection <= 0 ? (Close[0] > pendingEntryTarget) : (Close[0] < pendingEntryTarget);
                if (stillValid && Position.MarketPosition == MarketPosition.Flat)
                {
                    if (MultiploStopAtr20 > 0 && (double.IsNaN(atr20) || atr20 <= 0))
                    {
                        Print(string.Format("Z;OMITIDA;{0};sin ATR20", key));
                    }
                    else
                    {
                        activeTargetPx = RoundZetaTarget(pendingEntryDirection, pendingEntryTarget);
                        activeStopDist = MultiploStopAtr20 > 0 ? Math.Max(TickSize, Math.Round((MultiploStopAtr20 * atr20) / TickSize) * TickSize) : double.NaN;
                        Print(string.Format("Z;SENAL;{0};{1};tgt={2:F2};ema={3:F2};atr20={4:F2}",
                            key, pendingEntryDirection, activeTargetPx, emaValue, atr20));
                        if (pendingEntryDirection > 0) EnterLong(0, Cantidad, SigL);
                        else EnterShort(0, Cantidad, SigS);
                    }
                }
                pendingEntry = false;
            }
            else if (pendingEntry && minCt != SessionStartMinCt)
            {
                pendingEntry = false;
            }

            if (bucketClosed && Position.MarketPosition != MarketPosition.Flat && emaReady)
            {
                int sideNow = Position.MarketPosition == MarketPosition.Long ? 1 : -1;
                activeTargetPx = RoundZetaTarget(sideNow, emaValue);
                if (sideNow > 0)
                    ExitLongLimit(0, true, Position.Quantity, activeTargetPx, "Z_tgt", SigL);
                else
                    ExitShortLimit(0, true, Position.Quantity, activeTargetPx, "Z_tgt", SigS);
            }

            int lastMinute = SessionEndMinCt - 1; // 899 -> 14:59 CT close
            if (minCt >= lastMinute && Position.MarketPosition != MarketPosition.Flat)
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("EOD", SigL);
                else ExitShort("EOD", SigS);
            }
            if (minCt == lastMinute) FinalizeSession();
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            string n = execution.Order.Name;
            if (n != SigL && n != SigS) return;

            double fillPx = execution.Order.AverageFillPrice;
            int q = execution.Order.Filled;
            bool isLong = (n == SigL);

            if (!double.IsNaN(activeStopDist) && activeStopDist > 0)
            {
                double stopPx = isLong ? fillPx - activeStopDist : fillPx + activeStopDist;
                if (isLong) ExitLongStopMarket(0, true, q, stopPx, "Z_stop", SigL);
                else ExitShortStopMarket(0, true, q, stopPx, "Z_stop", SigS);
            }

            if (!double.IsNaN(activeTargetPx))
            {
                bool passedTarget = isLong ? (fillPx >= activeTargetPx) : (fillPx <= activeTargetPx);
                if (passedTarget)
                {
                    if (isLong) ExitLong("Z_tgt_fill_passed", SigL);
                    else ExitShort("Z_tgt_fill_passed", SigS);
                    return;
                }
                if (isLong) ExitLongLimit(0, true, q, activeTargetPx, "Z_tgt", SigL);
                else ExitShortLimit(0, true, q, activeTargetPx, "Z_tgt", SigS);
            }
        }

        #region Properties
        [NinjaScriptProperty, Range(5, 60), Display(Name = "BucketMinutes (10/15/30)", Order = 1, GroupName = "Z-Banda")]
        public int BucketMinutes { get; set; }
        [NinjaScriptProperty, Range(5, 60), Display(Name = "EmaPeriod (30/20/10)", Order = 2, GroupName = "Z-Banda")]
        public int EmaPeriod { get; set; }
        [NinjaScriptProperty, Range(5, 95), Display(Name = "MinEfficiencyPct (35/45/55)", Order = 3, GroupName = "Z-Banda")]
        public double MinEfficiencyPct { get; set; }
        [NinjaScriptProperty, Range(0, 5), Display(Name = "Múltiplo stop ATR20 (0 = sin stop)", Order = 4, GroupName = "Z-Banda")]
        public double MultiploStopAtr20 { get; set; }
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Cantidad contratos", Order = 5, GroupName = "Z-Banda")]
        public int Cantidad { get; set; }
        #endregion
    }
}

