// # meta indicator=HFTZonesNQPureV4,version=4.1.0
// HFTZonesNQPureV4.cs - Detector HFT NQ/MNQ - VARIANTE "impulso completo" (hermano de V2).
//
// Mismo motor y mismo logger que HFTZonesNQPureV2, con DOS cambios de deteccion para
// capturar los movimientos LARGOS que V2 fragmentaba/descartaba:
//   - LIMPIEZA RELATIVA: el retroceso permitido es proporcional a la altura del sweep
//     (allowed = max(MaxRetrocesoTicks, RetrocesoPctHeight% * altura)), NO un tope absoluto.
//     Asi un impulso largo y limpio que retrocede varios ticks ya no se rechaza, y el chop
//     (retroceso ~ altura) se sigue filtrando.
//   - RESEED NO-FRAGMENTANTE: la racha sigue viva mientras el rebote desde el extremo este
//     dentro de esa banda; solo corta y re-arranca en reversiones REALES (no en cada pullback).
//   => V2 sigue intacto para los cortos; V3 corre en paralelo (tags y base de datos separados).
//
// Logger identico (delta tick-rule, absorcion, flow) pero a base separada:
//   C:\LoggerHFT\data\hft_logger_v3.sqlite (no mezcla con los datos de V2).
//
// Calibracion NQ: MinPasos=8, MinSweepTicks=4, MaxRetrocesoTicks=2 (piso), RetrocesoPctHeight=50%,
// MaxAvgMs=25, MaxTotalMs=500, MaxPausaMs=100, MinVolumeRate=100, MinTotalVolume=50, PRED<=5ms, ULTRA<=15ms.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Data.SQLite;
using System.IO;
using System.Linq;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.Core.FloatingPoint;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class HFTZonesNQPureV4_V2 : Indicator
    {
        public enum HFTBucket { Predator, Ultra, Fast, Absorb }

        public sealed class Zone
        {
            public int    StartBar, EndBar;
            public int    DrawnBar, VisualEndBar;
            public DateTime StartTime, EndTime;
            public double Upper, Lower;
            public int    Direction;
            public HFTBucket Bucket;
            public double AvgMs, TotalMs, VolRate;
            public int    Pasos, ValidSteps;
            public double TotalVol;
            public double MaxRetro;
            public double MaxTickVol;
            public double Cvd, BuyVol, SellVol;
            public double DeltaSlope, DeltaFirst, DeltaSecond;
            public int    NoMoveTicks, MaxLevelTicks;
            public double NoMoveVol;
            public double HeightTicks;
            public string TagRect, TagText;
            public bool   Drawn;
            public Brush  ColorZ;
            public string Reporte;
            public string TerminationReason;
        }

        public sealed class ClusterZone
        {
            public double Lower;
            public double Upper;
            public int    StartBar;
            public int    EndBar;
            public int    ZoneCount;
            public string Tag;
            public double PocPrice;
        }

        
        // ===== V2 Rigorous Parity & Lineage Fields =====
        public bool EnableTickLog { get; set; }

        private long currentTickSeq = 0;
        private int  currentZoneSeq = 0;
        private long zoneStartTickSeq = 0;
        private long zoneEndTickSeq = 0;
        private string currentSessionId = "";
        private string contractStr = "";

        // Precision disclosure: .NET DateTime resolution is 100-nanosecond ticks (1 tick = 100 ns).
        // Timestamps recorded as nanoseconds multiply .NET ticks by 100 from Unix epoch (1970-01-01T00:00:00Z).
        private const string SOURCE_SHA256 = "841cdbcccbe54ca525e20456d38d1ece0beec5fdd7b820de980bbb01acebeb63";
        private const string PARAMETER_MANIFEST_SHA256 = "0fa994533b03d47a0fb615c3fd4478e91de8c05958eb33bb4004308faaba78a1";

        private SQLiteCommand tickCmd;
        private readonly List<object[]> tickBuf = new List<object[]>();

        private int      streak, validSteps, dir, fails;
        private double   swH, swL;
        private double   extremo, maxRetroceso;
        private readonly List<double> msList    = new List<double>();
        private readonly List<double> priceList = new List<double>();
        private readonly List<double> volList   = new List<double>();
        private readonly List<double> signList  = new List<double>();
        private double   totalVol;
        private DateTime tStart, tLast;
        private int      idCounter;
        private int      lastSide = 0;

        private long   flowBucket = long.MinValue;
        private long   flowStartMs;
        private double fO, fH, fL, fC, fVol, fBuy, fSell;
        private int    fTicks;

        private SQLiteConnection dbConn;
        private SQLiteCommand    flowCmd, zoneCmd;
        private bool   dbReady = false;
        private bool   hasLoggedFlushError = false;
        private readonly List<object[]> zoneBuf = new List<object[]>();
        private readonly List<object[]> flowBuf = new List<object[]>();
        private long   lastFlushMs = 0;
        private const int BatchSize = 400;
        private const int FlushMs   = 2000;
        private const int MaxBuf    = 200000;

        private readonly List<Zone> zones = new List<Zone>();
        public IReadOnlyList<Zone> PublicZones { get { return zones; } }

        public bool EnableFlowLog     { get; set; }
        public int  FlowBucketSeconds { get; set; }

        // ===== Vacios / expansiones (integrado) =====
        private int voidRecomputeCounter;
        private int voidCounter;
        private readonly List<string> voidTags = new List<string>();

        // ===== Clusters (solapamiento visual de 3+ rectangulos) =====
        private int clusterCounter;
        private readonly List<ClusterZone> activeClusters = new List<ClusterZone>();
        private readonly List<string> clusterTags = new List<string>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description              = "Detector HFT NQ/MNQ V2: Paridad estricta, monotonic zone_seq, nanosegundos (100ns .NET ticks), sin INSERT OR IGNORE, session_id determinista y tabla hft_ticks_v2 compartida.";
                Name                     = "HFTZonesNQPureV4_V2";
                Calculate                = Calculate.OnBarClose;
                IsOverlay                = true;
                DisplayInDataBox         = true;
                DrawOnPricePanel         = true;
                PaintPriceMarkers        = true;
                IsSuspendedWhileInactive = true;

                TickResolution           = 1;
                MinPasos                 = 8;
                MaxRangoTickPorVela      = 1;
                FallosTolerados          = 1;
                FiltroDireccionEstricto  = true;
                MinSweepTicks            = 4;
                MaxRetrocesoTicks        = 2;
                RetrocesoPctHeight       = 50;
                MaxAvgMs                 = 25;
                MaxTotalMs               = 500;
                MaxPausaMs               = 100;
                MinVolumeRate            = 100;
                MinTotalVolume           = 50;
                PredatorAvgMs            = 5;
                UltraAvgMs               = 15;
                MostrarAbsorb            = true;
                MinAbsorbPasos           = 6;
                ColorAbsorb              = Brushes.MediumPurple;
                ExtensionDibujo          = 600;
                Opacidad                 = 30;
                MostrarTexto             = true;
                ColorPredator            = Brushes.Gold;
                ColorUltra               = Brushes.Silver;
                ColorBull                = Brushes.DodgerBlue;
                ColorBear                = Brushes.OrangeRed;
                ColorTexto               = Brushes.Silver;
                EnableDbLogging          = true;
                EnableTickLog            = true;
                DbPath                   = @"E:\EdgeLab\data\nt8_oracles\hft_zones_nq_v2_native_termination_fresh.sqlite";
                EnableFlowLog            = true;
                FlowBucketSeconds        = 1;
                // Safe default for oracle generation: no WPF drawing.
                ModoExportacionPuro      = true;

                MostrarVacios     = true;
                VoidBinTicks      = 2;
                VoidMinAltoTicks  = 6;
                VoidMinAnchoBars  = 10;
                VoidLookbackBars  = 1200;
                VoidRecomputeBars = 20;
                VoidExtensionBars = 0;
                VoidExigirTouch   = true;
                VoidOpacidad      = 25;
                ColorVoid         = Brushes.DodgerBlue;
                VoidMax           = 200;
                VoidDebug         = false;

                MostrarClusters                = true;
                MinOverlapRectangulos          = 4;
                ColorCluster                   = Brushes.Gold;
                ColorBordeCluster              = Brushes.DarkOrange;
                OpacidadCluster                = 55;
                ExtenderClusterHastaZonaActual = false;
                MostrarTextoCluster            = true;
                DibujarPocCluster              = true;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, TickResolution);
            }
            else if (State == State.DataLoaded)
            {
                ResetState();
                zones.Clear();
                contractStr = (Instrument != null && Instrument.MasterInstrument != null)
                    ? (Instrument.MasterInstrument.Name + " " + Instrument.Expiry.ToString("MM-yy"))
                    : "NQ JUN26";
                currentSessionId = "";
                currentTickSeq = 0;
                currentZoneSeq = 0;
                zoneStartTickSeq = 0;
                zoneEndTickSeq = 0;
                tickBuf.Clear();
                idCounter = 0;
                lastSide  = 0;
                flowBucket = long.MinValue;
                fTicks = 0;
                voidRecomputeCounter = 0;
                voidCounter = 0;
                voidTags.Clear();
                clusterCounter = 0;
                clusterTags.Clear();
                activeClusters.Clear();
                hasLoggedFlushError = false;
                if (EnableDbLogging) SetupDb();
            }
            else if (State == State.Terminated)
            {
                if (dir != 0 && streak > 0)
                {
                    Finalizar("CENSORED_END_OF_INPUT");
                }
                CloseDb();
                LimpiarClusters();
            }
        }

        
        private static long UnixNs(DateTime dt)
        {
            // .NET DateTime.Ticks returns 100-ns intervals since 0001-01-01.
            // Converting to Unix epoch (1970-01-01T00:00:00Z) in nanoseconds:
            DateTime epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            return (dt.ToUniversalTime().Ticks - epoch.Ticks) * 100;
        }

        private static readonly TimeZoneInfo ChicagoTz = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");

        private static string GetCmeSessionId(DateTime tickTime)
        {
            DateTime utcTime = tickTime.ToUniversalTime();
            DateTime ctTime = TimeZoneInfo.ConvertTimeFromUtc(utcTime, ChicagoTz);
            DateTime tradeDate = ctTime.Date;
            DayOfWeek dow = ctTime.DayOfWeek;

            if (ctTime.Hour < 17)
            {
                if (dow == DayOfWeek.Sunday)
                    tradeDate = tradeDate.AddDays(1);
                else if (dow == DayOfWeek.Saturday)
                    tradeDate = tradeDate.AddDays(2);
            }
            else
            {
                if (dow == DayOfWeek.Friday)
                    tradeDate = tradeDate.AddDays(3);
                else if (dow == DayOfWeek.Saturday)
                    tradeDate = tradeDate.AddDays(2);
                else
                    tradeDate = tradeDate.AddDays(1);
            }

            return tradeDate.ToString("yyyyMMdd");
        }

        private void CheckSessionBoundary(DateTime tickTime)
        {
            string sessId = GetCmeSessionId(tickTime);
            if (sessId != currentSessionId)
            {
                if (dir != 0 && streak > 0)
                {
                    Finalizar("END_OF_SESSION");
                }
                currentSessionId = sessId;
                currentTickSeq = 0;
                currentZoneSeq = 0;
                hasLoggedFlushError = false;
                ResetState();
            }
        }

        private void ResetState()
        {
            streak = 0; validSteps = 0; dir = 0; fails = 0;
            msList.Clear(); priceList.Clear(); volList.Clear(); signList.Clear();
            totalVol = 0;
            extremo = 0; maxRetroceso = 0;
            zoneStartTickSeq = 0;
            zoneEndTickSeq = 0;
            lastSide = 0;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress == 1)
            {
                if (CurrentBars[1] < 5) return;
                ProcesarSweeps();
                if (!ModoExportacionPuro) DibujarPendientes();
                return;
            }
            if (BarsInProgress != 0) return;
            if (ModoExportacionPuro) return;
            if (CurrentBars[0] < 2) return;
            DibujarPendientes();
            if (!MostrarClusters && clusterTags.Count > 0)
            {
                LimpiarClusters();
            }

            if (MostrarVacios)
            {
                voidRecomputeCounter++;
                if (voidRecomputeCounter >= Math.Max(1, VoidRecomputeBars))
                {
                    voidRecomputeCounter = 0;
                    DetectarVacios();
                }
            }
        }

        // ===================== STATE MACHINE + FLOW =====================
        private void ProcesarSweeps()
        {
            int ds = 1;
            if (CurrentBars[ds] < 1) return;

            string curContract = (Instrument != null && Instrument.MasterInstrument != null)
                ? (Instrument.MasterInstrument.Name + " " + Instrument.Expiry.ToString("MM-yy"))
                : "NQ JUN26";
            if (!string.IsNullOrEmpty(contractStr) && curContract != contractStr)
            {
                if (dir != 0 && streak > 0)
                {
                    Finalizar("END_OF_SESSION");
                }
                contractStr = curContract;
                currentSessionId = "";
                currentTickSeq = 0;
                currentZoneSeq = 0;
                hasLoggedFlushError = false;
                ResetState();
            }

            DateTime tickTime = Times[ds][0];
            CheckSessionBoundary(tickTime);
            currentTickSeq++;

            if (EnableTickLog && dbReady)
            {
                long tsNs = UnixNs(tickTime);
                long pTicks = (long)Math.Round(Closes[ds][0] / TickSize);
                double curBid = 0, curAsk = 0;
                try { curBid = GetCurrentBid(ds); } catch { }
                try { curAsk = GetCurrentAsk(ds); } catch { }
                long bTicks = curBid > 0 ? (long)Math.Round(curBid / TickSize) : 0;
                long aTicks = curAsk > 0 ? (long)Math.Round(curAsk / TickSize) : 0;
                tickBuf.Add(new object[] {
                    Instrument.FullName, contractStr, currentSessionId, currentTickSeq,
                    tsNs, pTicks, Volumes[ds][0], bTicks, aTicks
                });
                if (tickBuf.Count >= 2000)
                    FlushAll();
            }

            double rng = (Highs[ds][0] - Lows[ds][0]) / TickSize;
            bool small = rng <= MaxRangoTickPorVela;
            double ms  = Times[ds][0].Subtract(Times[ds][1]).TotalMilliseconds;
            double vol = Volumes[ds][0];

            double op  = Opens[ds][0];
            double cl  = Closes[ds][0];
            double clP = Closes[ds][1];

            int side = cl > clP ? 1 : (cl < clP ? -1 : lastSide);
            if (side == 0) side = 1;
            lastSide = side;
            double signedVol = side * vol;

            if (EnableFlowLog) AccumFlow(Times[ds][0], cl, vol, side);

            bool isDown, isUp;
            if (FiltroDireccionEstricto)
            {
                isDown = small && cl <= clP && cl <= op;
                isUp   = small && cl >= clP && cl >= op;
            }
            else
            {
                isDown = small && cl <= clP;
                isUp   = small && cl >= clP;
            }

            if (dir != 0 && ms > MaxPausaMs)
            {
                Finalizar("MAX_PAUSE");
                dir = 0;
                return;
            }

            if (dir == 0)
            {
                if (isDown)    { dir = -1; Iniciar(ms, vol, cl, signedVol); }
                else if (isUp) { dir =  1; Iniciar(ms, vol, cl, signedVol); }
            }
            else if (dir == -1)
            {
                if (isDown) { Continuar(ms, vol, cl, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    double currentRetracement = (cl - extremo) / TickSize;
                    double sweepHeight = (swH - swL) / TickSize;
                    double maxAllowedRetracement = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepHeight);
                    
                    if (currentRetracement <= maxAllowedRetracement)
                    {
                        Continuar(ms, vol, cl, signedVol, false);
                    }
                    else
                    {
                        // Reversion real
                        Finalizar("REVERSAL");
                        if (isUp) { dir = 1; Iniciar(ms, vol, cl, signedVol); }
                        else        dir = 0;
                    }
                }
            }
            else
            {
                if (isUp) { Continuar(ms, vol, cl, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    double currentRetracement = (extremo - cl) / TickSize;
                    double sweepHeight = (swH - swL) / TickSize;
                    double maxAllowedRetracement = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepHeight);
                    
                    if (currentRetracement <= maxAllowedRetracement)
                    {
                        Continuar(ms, vol, cl, signedVol, false);
                    }
                    else
                    {
                        Finalizar("REVERSAL");
                        if (isDown) { dir = -1; Iniciar(ms, vol, cl, signedVol); }
                        else          dir = 0;
                    }
                }
            }
        }

        private void Iniciar(double ms, double vol, double cl, double signedVol)
        {
            int ds = 1;
            streak = 1; validSteps = 1; fails = 0;
            swH = Highs[ds][0]; swL = Lows[ds][0];
            extremo = Closes[ds][0];
            maxRetroceso = 0;
            msList.Clear();
            priceList.Clear(); volList.Clear(); signList.Clear();
            priceList.Add(cl); volList.Add(vol); signList.Add(signedVol);
            totalVol = vol;
            tStart = Times[ds][0];
            tLast  = Times[ds][0];
            zoneStartTickSeq = currentTickSeq;
            zoneEndTickSeq   = currentTickSeq;
        }

        private void Continuar(double ms, double vol, double cl, double signedVol, bool valid)
        {
            int ds = 1;
            streak++;
            if (valid) validSteps++;
            swH = Math.Max(swH, Highs[ds][0]);
            swL = Math.Min(swL, Lows[ds][0]);

            double clC = Closes[ds][0];
            if (dir == 1)
            {
                if (clC > extremo) extremo = clC;
                double adv = (extremo - clC) / TickSize;
                if (adv > maxRetroceso) maxRetroceso = adv;
            }
            else
            {
                if (clC < extremo) extremo = clC;
                double adv = (clC - extremo) / TickSize;
                if (adv > maxRetroceso) maxRetroceso = adv;
            }

            msList.Add(ms);
            priceList.Add(cl); volList.Add(vol); signList.Add(signedVol);
            totalVol += vol;
            tLast = Times[ds][0];
            zoneEndTickSeq = currentTickSeq;
        }

        private void Finalizar(string reason = "REVERSAL")
        {
            double sweepTicks = (swH - swL) / TickSize;
            bool isSweep  = sweepTicks >= MinSweepTicks;
            bool isAbsorb = !isSweep && MostrarAbsorb;
            int minPasosReq = isSweep ? MinPasos : MinAbsorbPasos;

            if (validSteps >= minPasosReq && (isSweep || isAbsorb))
            {
                double total = msList.Sum();
                int    nIntervals = msList.Count;
                double avgMs = total / Math.Max(1, nIntervals);
                double durationSec = Math.Max(total, 1.0) / 1000.0;
                double volRate = totalVol / durationSec;

                bool veloOk    = avgMs <= MaxAvgMs;
                bool durOk     = total <= MaxTotalMs;
                bool volOk     = volRate >= MinVolumeRate;
                bool volTotOk  = totalVol >= MinTotalVolume;
                
                double maxAllowedRetroceso = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepTicks);
                bool limpioOk  = isAbsorb || (maxRetroceso <= maxAllowedRetroceso);

                if (veloOk && durOk && volOk && volTotOk && limpioOk)
                {
                    HFTBucket bucket; Brush col; string bucketTxt;
                    if (isAbsorb)
                    {
                        bucket = HFTBucket.Absorb; col = ColorAbsorb; bucketTxt = "ABSORB";
                    }
                    else
                    {
                        bucket = avgMs <= PredatorAvgMs ? HFTBucket.Predator
                               : avgMs <= UltraAvgMs    ? HFTBucket.Ultra : HFTBucket.Fast;
                        col = bucket == HFTBucket.Predator ? ColorPredator
                            : bucket == HFTBucket.Ultra    ? ColorUltra
                            : (dir == 1 ? ColorBull : ColorBear);
                        bucketTxt = bucket == HFTBucket.Predator ? "PRED"
                                  : bucket == HFTBucket.Ultra    ? "ULTRA"
                                  : (dir == 1 ? "BULL" : "BEAR");
                    }

                    double cvd = 0, buy = 0, sell = 0, maxTickVol = 0;
                    for (int i = 0; i < signList.Count; i++)
                    {
                        double sv = signList[i];
                        cvd += sv;
                        if (sv >= 0) buy += volList[i]; else sell += volList[i];
                        if (volList[i] > maxTickVol) maxTickVol = volList[i];
                    }

                    double slope = 0, dFirst = 0, dSecond = 0;
                    int nS = signList.Count;
                    if (nS >= 2)
                    {
                        double sumX = 0, sumY = 0, sumXY = 0, sumXX = 0, cum = 0;
                        for (int i = 0; i < nS; i++)
                        {
                            cum += signList[i];
                            sumX += i; sumY += cum; sumXY += i * cum; sumXX += (double)i * i;
                        }
                        double den = nS * sumXX - sumX * sumX;
                        if (Math.Abs(den) > 1e-9) slope = (nS * sumXY - sumX * sumY) / den;
                        int half = nS / 2;
                        for (int i = 0; i < nS; i++)
                        {
                            if (i < half) dFirst += signList[i]; else dSecond += signList[i];
                        }
                    }

                    int noMoveTicks = 0; double noMoveVol = 0;
                    var freq = new Dictionary<long, int>();
                    long prevTk = long.MinValue;
                    for (int i = 0; i < priceList.Count; i++)
                    {
                        long tk = (long)Math.Round(priceList[i] / TickSize);
                        if (i > 0 && tk == prevTk) { noMoveTicks++; noMoveVol += volList[i]; }
                        prevTk = tk;
                        int c; freq.TryGetValue(tk, out c); freq[tk] = c + 1;
                    }
                    int maxLevelTicks = 0;
                    foreach (var kv in freq) if (kv.Value > maxLevelTicks) maxLevelTicks = kv.Value;

                    int prim_start = BarsArray[0].GetBar(tStart);
                    int prim_end   = BarsArray[0].GetBar(tLast);
                    if (prim_start < 0) prim_start = Math.Max(0, CurrentBars[0] - streak);
                    if (prim_end < 0)   prim_end   = CurrentBars[0] - 1;
                    if (prim_end < prim_start) prim_end = prim_start;

                    string pasosTxt = (streak == validSteps)
                        ? validSteps.ToString()
                        : string.Format("{0}+{1}f", validSteps, streak - validSteps);

                    string txt = string.Format("[{0}] {1}p {2:F1}ms tot{3:F0}ms vR{4:F0} V{5:F0} h{6:F0}t r{7:F0}t d{8:F0}",
                        bucketTxt, pasosTxt, avgMs, total, volRate, totalVol, sweepTicks, maxRetroceso, cvd);

                    idCounter++;
                    string tag = "HFTNQV4_" + idCounter;

                    var z = new Zone
                    {
                        StartBar = prim_start, EndBar = prim_end,
                        StartTime = tStart, EndTime = tLast,
                        Upper = swH, Lower = swL, Direction = dir, Bucket = bucket,
                        AvgMs = avgMs, TotalMs = total, VolRate = volRate,
                        Pasos = streak, ValidSteps = validSteps, TotalVol = totalVol,
                        MaxRetro = maxRetroceso,
                        MaxTickVol = maxTickVol, Cvd = cvd, BuyVol = buy, SellVol = sell,
                        DeltaSlope = slope, DeltaFirst = dFirst, DeltaSecond = dSecond,
                        NoMoveTicks = noMoveTicks, NoMoveVol = noMoveVol, MaxLevelTicks = maxLevelTicks,
                        HeightTicks = sweepTicks,
                        TagRect = tag + "_R", TagText = tag + "_T", Drawn = false,
                        ColorZ = col, Reporte = txt,
                        TerminationReason = reason
                    };
                    zones.Add(z);
                    if (EnableDbLogging) PersistZone(z);
                }
            }
            ResetState();
        }

        // ===================== DIBUJO =====================
        private void DibujarPendientes()
        {
            if (ModoExportacionPuro) return;
            for (int i = 0; i < zones.Count; i++)
            {
                Zone z = zones[i];
                if (z.Drawn) continue;
                int barsAgoStart = CurrentBars[0] - z.StartBar;
                int barsAgoEnd   = CurrentBars[0] - z.EndBar;
                if (barsAgoStart < 0) continue;
                Draw.Rectangle(this, z.TagRect, false,
                    barsAgoStart, z.Upper, -ExtensionDibujo, z.Lower,
                    Brushes.Transparent, z.ColorZ, Opacidad);
                if (MostrarTexto)
                {
                    double tY = z.Direction == 1 ? z.Lower - (TickSize * 4) : z.Upper + (TickSize * 4);
                    int textBar = Math.Max(0, barsAgoEnd);
                    Draw.Text(this, z.TagText, z.Reporte, textBar, tY, ColorTexto);
                }
                z.Drawn = true;
                z.DrawnBar = CurrentBars[0];
                z.VisualEndBar = CurrentBars[0] + ExtensionDibujo;

                if (MostrarClusters)
                {
                    DetectarSolapamientoCluster(i);
                }
            }
        }

        // ===================== CLUSTERS (HISTOGRAMA DE DENSIDAD DE CONFLUENCIA 4+) =====================
        private void DetectarSolapamientoCluster(int newIdx)
        {
            if (ModoExportacionPuro) return;
            if (newIdx < 0 || newIdx >= zones.Count) return;
            Zone newZ = zones[newIdx];
            int currentBar = CurrentBars[0];

            // 1. Filtrar zonas activas que coexisten temporalmente o recientemente
            List<Zone> candidatos = new List<Zone>();
            int searchStart = Math.Max(0, newIdx - 150);
            for (int i = searchStart; i <= newIdx; i++)
            {
                Zone z = zones[i];
                if (z.VisualEndBar <= newZ.StartBar) continue; // expiro antes del inicio de la nueva zona
                candidatos.Add(z);
            }

            if (candidatos.Count < MinOverlapRectangulos) return;

            // 2. Construir Histograma de Densidad por Ticks
            Dictionary<long, int> tickDensity = new Dictionary<long, int>();
            Dictionary<long, double> tickVolume = new Dictionary<long, double>();

            for (int i = 0; i < candidatos.Count; i++)
            {
                Zone z = candidatos[i];
                double zLo = Math.Min(z.Lower, z.Upper);
                double zHi = Math.Max(z.Lower, z.Upper);
                long loTk = (long)Math.Round(zLo / TickSize);
                long hiTk = (long)Math.Round(zHi / TickSize);

                for (long tk = loTk; tk <= hiTk; tk++)
                {
                    tickDensity[tk] = tickDensity.ContainsKey(tk) ? tickDensity[tk] + 1 : 1;
                    tickVolume[tk]  = tickVolume.ContainsKey(tk) ? tickVolume[tk] + z.TotalVol : z.TotalVol;
                }
            }

            // 3. Extraer ticks que alcanzan el umbral de 4+ zonas (MinOverlapRectangulos)
            List<long> qualifyingTicks = new List<long>();
            foreach (KeyValuePair<long, int> kv in tickDensity)
            {
                if (kv.Value >= MinOverlapRectangulos)
                    qualifyingTicks.Add(kv.Key);
            }

            if (qualifyingTicks.Count == 0) return;
            qualifyingTicks.Sort();

            // 4. Agrupar en segmentos contiguos (tolerancia de 1 tick de gap)
            List<List<long>> clusters = new List<List<long>>();
            List<long> currentCluster = new List<long>();

            for (int i = 0; i < qualifyingTicks.Count; i++)
            {
                if (currentCluster.Count == 0)
                {
                    currentCluster.Add(qualifyingTicks[i]);
                    continue;
                }

                if (qualifyingTicks[i] - currentCluster[currentCluster.Count - 1] <= 1)
                {
                    currentCluster.Add(qualifyingTicks[i]);
                }
                else
                {
                    clusters.Add(currentCluster);
                    currentCluster = new List<long> { qualifyingTicks[i] };
                }
            }
            if (currentCluster.Count > 0)
                clusters.Add(currentCluster);

            // 5. Duracion del cluster: misma longitud que el resto de rectangulos (ExtensionDibujo)
            int clusterEndBar = currentBar + ExtensionDibujo;
            int endAgo = -ExtensionDibujo;

            // 6. Procesar y dibujar cada cluster detectado
            for (int c = 0; c < clusters.Count; c++)
            {
                List<long> cTicks = clusters[c];
                double cLower = cTicks.Min() * TickSize - (TickSize * 0.5);
                double cUpper = cTicks.Max() * TickSize + (TickSize * 0.5);

                // Encontrar el tick POC (maxima confluencia de zonas y volumen)
                long pocTk = cTicks[0];
                int maxCount = 0;
                double maxVol = 0;
                for (int t = 0; t < cTicks.Count; t++)
                {
                    long tk = cTicks[t];
                    int cnt = tickDensity[tk];
                    double vol = tickVolume.ContainsKey(tk) ? tickVolume[tk] : 0;
                    if (cnt > maxCount || (cnt == maxCount && vol > maxVol))
                    {
                        maxCount = cnt;
                        maxVol = vol;
                        pocTk = tk;
                    }
                }
                double pocPrice = pocTk * TickSize;

                // Identificar zonas contribuyentes para determinar la barra de inicio
                int clusterStartBar = newZ.StartBar;
                for (int i = 0; i < candidatos.Count; i++)
                {
                    Zone z = candidatos[i];
                    double zLo = Math.Min(z.Lower, z.Upper);
                    double zHi = Math.Max(z.Lower, z.Upper);
                    if (zHi >= cLower && zLo <= cUpper)
                    {
                        clusterStartBar = Math.Min(clusterStartBar, z.StartBar);
                    }
                }

                int startAgo = currentBar - clusterStartBar;

                // Buscar si ya existe un cluster activo en este nivel para actualizarlo sin duplicar
                ClusterZone matchingExisting = null;
                for (int ex = activeClusters.Count - 1; ex >= 0; ex--)
                {
                    ClusterZone prevC = activeClusters[ex];
                    double ovLo = Math.Max(cLower, prevC.Lower);
                    double ovHi = Math.Min(cUpper, prevC.Upper);
                    if (ovHi > ovLo && clusterStartBar <= prevC.EndBar) // Se intersectan en precio y sigue activo
                    {
                        matchingExisting = prevC;
                        break;
                    }
                }

                if (matchingExisting != null)
                {
                    matchingExisting.Lower = Math.Min(matchingExisting.Lower, cLower);
                    matchingExisting.Upper = Math.Max(matchingExisting.Upper, cUpper);
                    matchingExisting.ZoneCount = Math.Max(matchingExisting.ZoneCount, maxCount);
                    matchingExisting.StartBar = Math.Min(matchingExisting.StartBar, clusterStartBar);
                    matchingExisting.EndBar = clusterEndBar;
                    matchingExisting.PocPrice = pocPrice;

                    int exStartAgo = currentBar - matchingExisting.StartBar;

                    Draw.Rectangle(this, matchingExisting.Tag, false,
                        exStartAgo, matchingExisting.Upper, endAgo, matchingExisting.Lower,
                        ColorBordeCluster, ColorCluster, OpacidadCluster);

                    if (DibujarPocCluster)
                    {
                        Draw.Line(this, matchingExisting.Tag + "_POC", false,
                            exStartAgo, matchingExisting.PocPrice, endAgo, matchingExisting.PocPrice,
                            ColorBordeCluster, DashStyleHelper.Dash, 2);
                    }

                    if (MostrarTextoCluster)
                    {
                        string txt = string.Format("★ CLUSTER {0}x (POC: {1:F2})", matchingExisting.ZoneCount, matchingExisting.PocPrice);
                        int textBar = Math.Max(0, exStartAgo);
                        Draw.Text(this, matchingExisting.Tag + "_T", txt, textBar, matchingExisting.Upper + (TickSize * 3), ColorBordeCluster);
                    }
                }
                else
                {
                    clusterCounter++;
                    string tag = "HFTCLUST_" + clusterCounter;
                    ClusterZone cz = new ClusterZone
                    {
                        Lower = cLower,
                        Upper = cUpper,
                        StartBar = clusterStartBar,
                        EndBar = clusterEndBar,
                        ZoneCount = maxCount,
                        Tag = tag,
                        PocPrice = pocPrice
                    };
                    clusterTags.Add(tag);
                    clusterTags.Add(tag + "_POC");

                    Draw.Rectangle(this, tag, false,
                        startAgo, cz.Upper, endAgo, cz.Lower,
                        ColorBordeCluster, ColorCluster, OpacidadCluster);

                    if (DibujarPocCluster)
                    {
                        Draw.Line(this, tag + "_POC", false,
                            startAgo, cz.PocPrice, endAgo, cz.PocPrice,
                            ColorBordeCluster, DashStyleHelper.Dash, 2);
                    }

                    if (MostrarTextoCluster)
                    {
                        string txt = string.Format("★ CLUSTER {0}x (POC: {1:F2})", cz.ZoneCount, cz.PocPrice);
                        string textTag = tag + "_T";
                        clusterTags.Add(textTag);
                        int textBar = Math.Max(0, startAgo);
                        Draw.Text(this, textTag, txt, textBar, cz.Upper + (TickSize * 3), ColorBordeCluster);
                    }

                    activeClusters.Add(cz);
                    if (activeClusters.Count > 500) activeClusters.RemoveAt(0);
                }
            }
        }

        private void LimpiarClusters()
        {
            for (int i = 0; i < clusterTags.Count; i++)
            {
                try { RemoveDrawObject(clusterTags[i]); }
                catch { }
            }
            clusterTags.Clear();
            activeClusters.Clear();
        }

        // ===================== VACIOS / EXPANSIONES =====================
        // Marca EXPANSIONES: regiones (tiempo x precio) por donde el precio PASO pero que ninguna
        // zona HFT cubre. Cada zona cuenta con su extension hacia adelante (ExtensionDibujo): si una
        // zona se proyecta y atraviesa la expansion, esta deja de marcarse. Las celdas vacias se
        // agrupan en regiones conexas y se dibuja un rectangulo (bounding box) por expansion.
        private void DetectarVacios()
        {
            if (ModoExportacionPuro) return;
            double binSize = Math.Max(1, VoidBinTicks) * TickSize;
            if (binSize <= 0) return;

            int b1 = CurrentBars[0];
            int b0 = Math.Max(0, b1 - Math.Max(10, VoidLookbackBars));
            int nBars = b1 - b0 + 1;
            if (nBars < Math.Max(2, VoidMinAnchoBars)) return;

            double lo = double.MaxValue, hi = double.MinValue;
            for (int b = b0; b <= b1; b++)
            {
                double L = Lows[0].GetValueAt(b);
                double H = Highs[0].GetValueAt(b);
                if (L < lo) lo = L;
                if (H > hi) hi = H;
            }
            if (hi <= lo) return;

            int nBins = (int)Math.Ceiling((hi - lo) / binSize) + 1;
            if (nBins < 2) return;
            // Rango de precio muy grande: agrandar el bin para no exceder la grilla (en vez de no dibujar nada).
            while (nBins > 2000 && binSize > 0)
            {
                binSize *= 2;
                nBins = (int)Math.Ceiling((hi - lo) / binSize) + 1;
            }

            bool[,] touched = new bool[nBars, nBins];
            bool[,] covered = new bool[nBars, nBins];

            // 1) Mascara "el precio estuvo aca" (recorrido high-low por vela)
            for (int c = 0; c < nBars; c++)
            {
                int abs = b0 + c;
                double L = Lows[0].GetValueAt(abs);
                double H = Highs[0].GetValueAt(abs);
                int kFrom = (int)Math.Floor((L - lo) / binSize);
                int kTo   = (int)Math.Floor((H - lo) / binSize);
                if (kFrom < 0) kFrom = 0;
                if (kTo > nBins - 1) kTo = nBins - 1;
                for (int k = kFrom; k <= kTo; k++) touched[c, k] = true;
            }

            // 2) Mascara "hay zona aca". La zona ocupa su nivel de precio hacia ADELANTE segun la
            //    extension configurada (igual que el rectangulo dibujado): de StartBar hasta
            //    EndBar + ExtensionDibujo (+ margen extra opcional). Asi el vacio no pisa la zona.
            int zc = 0;
            for (int i = 0; i < zones.Count; i++)
            {
                Zone z = zones[i];
                int sBar = Math.Max(b0, z.StartBar);
                int eBar = Math.Min(b1, z.EndBar + Math.Max(0, ExtensionDibujo) + Math.Max(0, VoidExtensionBars));
                if (eBar < sBar) continue;

                double pHi = Math.Max(z.Upper, z.Lower);
                double pLo = Math.Min(z.Upper, z.Lower);
                int kLo = (int)Math.Floor((pLo - lo) / binSize);
                int kHi = (int)Math.Floor((pHi - lo) / binSize);
                if (kHi < 0 || kLo > nBins - 1) continue;
                if (kLo < 0) kLo = 0;
                if (kHi > nBins - 1) kHi = nBins - 1;

                for (int c = sBar - b0; c <= eBar - b0; c++)
                {
                    if (c < 0 || c > nBars - 1) continue;
                    for (int k = kLo; k <= kHi; k++) covered[c, k] = true;
                }
                zc++;
            }

            // 3) Celdas de expansion: el precio PASO ahi (touched) y NINGUNA zona la cubre.
            double binTicksActual = binSize / TickSize;
            int minBins = Math.Max(1, (int)Math.Round(Math.Max(1, VoidMinAltoTicks) / Math.Max(1.0, binTicksActual)));
            int minW    = Math.Max(1, VoidMinAnchoBars);

            bool[,] isVoid = new bool[nBars, nBins];
            int voidCells = 0;
            for (int c = 0; c < nBars; c++)
                for (int k = 0; k < nBins; k++)
                {
                    bool v = (!covered[c, k]) && (!VoidExigirTouch || touched[c, k]);
                    isVoid[c, k] = v;
                    if (v) voidCells++;
                }

            // Agrupar en regiones conexas (flood fill, 4-vecinos) -> bounding box por expansion.
            bool[,] seen = new bool[nBars, nBins];
            List<int[]> nuevos = new List<int[]>();
            Stack<int> stack = new Stack<int>();
            int regionsTotal = 0, bestW = 0, bestH = 0;   // diagnostico: mejor region ANTES de filtrar

            for (int cc0 = 0; cc0 < nBars; cc0++)
            {
                for (int kk0 = 0; kk0 < nBins; kk0++)
                {
                    if (!isVoid[cc0, kk0] || seen[cc0, kk0]) continue;

                    int cMin = cc0, cMax = cc0, kMin = kk0, kMax = kk0;
                    seen[cc0, kk0] = true;
                    stack.Push(cc0 * nBins + kk0);
                    while (stack.Count > 0)
                    {
                        int idx = stack.Pop();
                        int cc = idx / nBins;
                        int kk = idx % nBins;
                        if (cc < cMin) cMin = cc; if (cc > cMax) cMax = cc;
                        if (kk < kMin) kMin = kk; if (kk > kMax) kMax = kk;

                        if (cc > 0        && isVoid[cc - 1, kk] && !seen[cc - 1, kk]) { seen[cc - 1, kk] = true; stack.Push((cc - 1) * nBins + kk); }
                        if (cc < nBars - 1 && isVoid[cc + 1, kk] && !seen[cc + 1, kk]) { seen[cc + 1, kk] = true; stack.Push((cc + 1) * nBins + kk); }
                        if (kk > 0        && isVoid[cc, kk - 1] && !seen[cc, kk - 1]) { seen[cc, kk - 1] = true; stack.Push(cc * nBins + (kk - 1)); }
                        if (kk < nBins - 1 && isVoid[cc, kk + 1] && !seen[cc, kk + 1]) { seen[cc, kk + 1] = true; stack.Push(cc * nBins + (kk + 1)); }
                    }

                    int rw = cMax - cMin + 1;
                    int rh = kMax - kMin + 1;
                    regionsTotal++;
                    if (rw > bestW) bestW = rw;
                    if (rh > bestH) bestH = rh;

                    if (rw >= minW && rh >= minBins)
                    {
                        nuevos.Add(new int[] { cMin, cMax, kMin, kMax });
                        if (nuevos.Count >= Math.Max(1, VoidMax)) { cc0 = nBars; break; }
                    }
                }
            }

            // 4) Redibujar cada expansion en su rango real de barras y precio.
            LimpiarVacios();
            int op = Math.Max(1, Math.Min(100, VoidOpacidad));
            for (int i = 0; i < nuevos.Count; i++)
            {
                int cS  = nuevos[i][0];
                int cE  = nuevos[i][1];
                int kLo2 = nuevos[i][2];
                int kHi2 = nuevos[i][3];
                int barsAgo0 = CurrentBars[0] - (b0 + cS);
                int barsAgo1 = CurrentBars[0] - (b0 + cE);
                double bottom = lo + kLo2 * binSize;
                double top    = lo + (kHi2 + 1) * binSize;
                string tag = "HFTVOID4_" + (voidCounter++);
                Draw.Rectangle(this, tag, false, barsAgo0, top, barsAgo1, bottom, ColorVoid, ColorVoid, op);
                voidTags.Add(tag);
            }
            if (VoidDebug) Print("[Vacios] zonas=" + zc + " celdasVacias=" + voidCells + " regiones=" + regionsTotal + " mejorWxH=" + bestW + "x" + bestH + " marcadas=" + nuevos.Count + " | nBars=" + nBars + " nBins=" + nBins + " minW=" + minW + " minBins=" + minBins + " (alto en ticks: bin=" + binTicksActual.ToString("F1") + ")");
        }

        private void LimpiarVacios()
        {
            for (int i = 0; i < voidTags.Count; i++)
            {
                try { RemoveDrawObject(voidTags[i]); }
                catch { }
            }
            voidTags.Clear();
        }

        // ===================== FLOW STREAM =====================
        private void AccumFlow(DateTime t, double price, double vol, int side)
        {
            long ms = UnixMs(t);
            int  secs = Math.Max(1, FlowBucketSeconds);
            long bucket = (ms / 1000L) / secs;
            if (bucket != flowBucket)
            {
                if (flowBucket != long.MinValue && fTicks > 0) BufferFlow();
                flowBucket  = bucket;
                flowStartMs = bucket * secs * 1000L;
                fO = fH = fL = fC = price;
                fVol = 0; fBuy = 0; fSell = 0; fTicks = 0;
            }
            fC = price;
            if (price > fH) fH = price;
            if (price < fL) fL = price;
            fVol += vol;
            if (side > 0) fBuy += vol; else fSell += vol;
            fTicks++;
        }

        private void BufferFlow()
        {
            if (!dbReady) return;
            flowBuf.Add(new object[] { Instrument.FullName, flowStartMs, fO, fH, fL, fC,
                                       fVol, fBuy, fSell, fBuy - fSell, fTicks });
            if (flowBuf.Count >= BatchSize || (flowStartMs - lastFlushMs) >= FlushMs)
                FlushAll();
        }

        // ===================== SQLITE (buffered, concurrency-safe) =====================
        private void SetupDb()
        {
            try
            {
                string dir = Path.GetDirectoryName(DbPath);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                    Directory.CreateDirectory(dir);

                dbConn = new SQLiteConnection("Data Source=" + DbPath + ";Version=3;");
                dbConn.Open();
                using (var c = new SQLiteCommand(
                    "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;", dbConn))
                    c.ExecuteNonQuery();

                // Verificación fail-closed: la base para una certificación debe nacer vacía
                using (var checkCmd = new SQLiteCommand(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('hft_ticks_v2', 'hft_zones_v2');", dbConn))
                {
                    long tableCount = Convert.ToInt64(checkCmd.ExecuteScalar());
                    if (tableCount > 0)
                    {
                        using (var countCmd = new SQLiteCommand(
                            "SELECT (SELECT COUNT(*) FROM hft_ticks_v2) + (SELECT COUNT(*) FROM hft_zones_v2);", dbConn))
                        {
                            long rowCount = Convert.ToInt64(countCmd.ExecuteScalar());
                            if (rowCount > 0)
                            {
                                throw new InvalidOperationException("La base de datos SQLite '" + DbPath + "' ya contiene " + rowCount + " filas. Se prohíbe reutilizar bases de datos para la certificación: debe ser una base completamente limpia y vacía.");
                            }
                        }
                    }
                }

                using (var cmd = new SQLiteCommand(
                    @"CREATE TABLE IF NOT EXISTS hft_ticks_v2 (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        instrument TEXT NOT NULL,
                        contract TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        tick_seq INTEGER NOT NULL,
                        timestamp_ns INTEGER NOT NULL,
                        price_ticks INTEGER NOT NULL,
                        volume REAL NOT NULL,
                        bid_ticks INTEGER NOT NULL,
                        ask_ticks INTEGER NOT NULL,
                        CONSTRAINT ux_tick_v2 UNIQUE (instrument, contract, session_id, tick_seq)
                      );
                      CREATE INDEX IF NOT EXISTS idx_ht_session_seq ON hft_ticks_v2(session_id, tick_seq);
                      CREATE INDEX IF NOT EXISTS idx_ht_ts ON hft_ticks_v2(timestamp_ns);

                      CREATE TABLE IF NOT EXISTS hft_zones_v2 (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        instrument TEXT NOT NULL,
                        contract TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        zone_seq INTEGER NOT NULL,
                        start_tick_seq INTEGER NOT NULL,
                        end_tick_seq INTEGER NOT NULL,
                        start_ts_ns INTEGER NOT NULL,
                        end_ts_ns INTEGER NOT NULL,
                        available_ts_ns INTEGER NOT NULL,
                        direction INTEGER NOT NULL,
                        lo_ticks INTEGER NOT NULL,
                        hi_ticks INTEGER NOT NULL,
                        pasos INTEGER NOT NULL,
                        vol REAL NOT NULL,
                        avg_ms REAL NOT NULL,
                        total_ms REAL NOT NULL,
                        volume_rate REAL NOT NULL,
                        parameter_manifest_sha256 TEXT NOT NULL,
                        indicator_source_sha256 TEXT NOT NULL,
                        valid_steps INTEGER NOT NULL,
                        max_retro REAL NOT NULL,
                        cvd_sweep REAL NOT NULL,
                        buy_vol REAL NOT NULL,
                        sell_vol REAL NOT NULL,
                        delta_slope REAL NOT NULL,
                        delta_first REAL NOT NULL,
                        delta_second REAL NOT NULL,
                        max_tick_vol REAL NOT NULL,
                        no_move_ticks INTEGER NOT NULL,
                        no_move_vol REAL NOT NULL,
                        max_level_ticks INTEGER NOT NULL,
                        bucket TEXT NOT NULL,
                        price_upper REAL NOT NULL,
                        price_lower REAL NOT NULL,
                        price_mid REAL NOT NULL,
                        height_ticks REAL NOT NULL,
                        tick_res INTEGER NOT NULL,
                        termination_reason TEXT NOT NULL,
                        CONSTRAINT ux_zone_v2 UNIQUE (instrument, contract, session_id, zone_seq)
                      );
                      CREATE INDEX IF NOT EXISTS idx_hz_v2_session ON hft_zones_v2(session_id, zone_seq);
                      CREATE INDEX IF NOT EXISTS idx_hz_v2_start ON hft_zones_v2(start_ts_ns);

                      CREATE TABLE IF NOT EXISTS hft_flow (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, instrument TEXT, bar_ts INTEGER, open REAL, high REAL,
                        low REAL, close REAL, volume REAL, buy_vol REAL, sell_vol REAL, delta REAL, n_ticks INTEGER);
                      CREATE INDEX IF NOT EXISTS idx_hf_ts ON hft_flow(instrument, bar_ts);", dbConn))
                    cmd.ExecuteNonQuery();

                zoneCmd = new SQLiteCommand(
                    @"INSERT INTO hft_zones_v2
                      (instrument,contract,session_id,zone_seq,start_tick_seq,end_tick_seq,start_ts_ns,end_ts_ns,
                       available_ts_ns,direction,lo_ticks,hi_ticks,pasos,vol,avg_ms,total_ms,volume_rate,
                       parameter_manifest_sha256,indicator_source_sha256,valid_steps,max_retro,cvd_sweep,
                       buy_vol,sell_vol,delta_slope,delta_first,delta_second,max_tick_vol,no_move_ticks,
                       no_move_vol,max_level_ticks,bucket,price_upper,price_lower,price_mid,height_ticks,tick_res,termination_reason)
                      VALUES (@inst,@ct,@sess,@zseq,@stk,@etk,@s_ns,@e_ns,@avail_ns,@dir,@lo_tk,@hi_tk,@p,@v,
                              @am,@tm,@vr,@param_sha,@src_sha,@vs,@mr,@cvd,@buy,@sell,@dsl,@d1,@d2,@mtv,
                              @nmt,@nmv,@mlt,@b,@pu,@pl,@pm,@ht,@tr,@term_reason)", dbConn);
                foreach (string p in new[]{"@inst","@ct","@sess","@zseq","@stk","@etk","@s_ns","@e_ns","@avail_ns","@dir",
                    "@lo_tk","@hi_tk","@p","@v","@am","@tm","@vr","@param_sha","@src_sha","@vs","@mr","@cvd",
                    "@buy","@sell","@dsl","@d1","@d2","@mtv","@nmt","@nmv","@mlt","@b","@pu","@pl","@pm","@ht","@tr","@term_reason"})
                    zoneCmd.Parameters.Add(new SQLiteParameter(p));

                tickCmd = new SQLiteCommand(
                    @"INSERT INTO hft_ticks_v2
                      (instrument,contract,session_id,tick_seq,timestamp_ns,price_ticks,volume,bid_ticks,ask_ticks)
                      VALUES (@inst,@ct,@sess,@tseq,@ts_ns,@ptk,@vol,@btk,@atk)", dbConn);
                foreach (string p in new[]{"@inst","@ct","@sess","@tseq","@ts_ns","@ptk","@vol","@btk","@atk"})
                    tickCmd.Parameters.Add(new SQLiteParameter(p));
                tickCmd.Prepare();
                zoneCmd.Prepare();

                flowCmd = new SQLiteCommand(
                    @"INSERT INTO hft_flow
                      (instrument,bar_ts,open,high,low,close,volume,buy_vol,sell_vol,delta,n_ticks)
                      VALUES (@inst,@ts,@o,@h,@l,@c,@v,@bv,@sv,@d,@nt)", dbConn);
                foreach (string p in new[]{"@inst","@ts","@o","@h","@l","@c","@v","@bv","@sv","@d","@nt"})
                    flowCmd.Parameters.Add(new SQLiteParameter(p));
                flowCmd.Prepare();

                dbReady = true;
                lastFlushMs = 0;
            }
            catch (Exception ex)
            {
                dbReady = false;
                Print("[HFTLogger-NQ] SetupDb: " + ex.Message);
            }
        }

        private void PersistZone(Zone z)
        {
            if (!dbReady) return;
            currentZoneSeq++;

            long startNs = UnixNs(z.StartTime);
            long endNs = UnixNs(z.EndTime);
            long availNs = UnixNs(Times[1][0]); // Available at completion of sweep (end tick)

            long loTicks = (long)Math.Round(z.Lower / TickSize);
            long hiTicks = (long)Math.Round(z.Upper / TickSize);

            zoneBuf.Add(new object[] {
                Instrument.FullName, contractStr, currentSessionId, currentZoneSeq,
                zoneStartTickSeq, zoneEndTickSeq, startNs, endNs, availNs, z.Direction,
                loTicks, hiTicks, z.Pasos, z.TotalVol, z.AvgMs, z.TotalMs, z.VolRate,
                PARAMETER_MANIFEST_SHA256, SOURCE_SHA256,
                z.ValidSteps, z.MaxRetro, z.Cvd, z.BuyVol, z.SellVol, z.DeltaSlope,
                z.DeltaFirst, z.DeltaSecond, z.MaxTickVol, z.NoMoveTicks, z.NoMoveVol,
                z.MaxLevelTicks, z.Bucket.ToString(), z.Upper, z.Lower, (z.Upper + z.Lower) / 2.0,
                z.HeightTicks, TickResolution, z.TerminationReason
            });
            FlushAll();
        }

        private void FlushAll()
        {
            if (!dbReady) return;
            if (zoneBuf.Count == 0 && flowBuf.Count == 0 && tickBuf.Count == 0) return;
            SQLiteTransaction tx = null;
            try
            {
                tx = dbConn.BeginTransaction();
                if (tickCmd != null && tickBuf.Count > 0)
                {
                    tickCmd.Transaction = tx;
                    foreach (var r in tickBuf)
                    {
                        tickCmd.Reset();
                        for (int i = 0; i < r.Length; i++) tickCmd.Parameters[i].Value = r[i];
                        tickCmd.ExecuteNonQuery();
                    }
                    tickCmd.Reset();
                }
                if (zoneCmd != null && zoneBuf.Count > 0)
                {
                    zoneCmd.Transaction = tx;
                    foreach (var r in zoneBuf)
                    {
                        zoneCmd.Reset();
                        for (int i = 0; i < r.Length; i++) zoneCmd.Parameters[i].Value = r[i];
                        zoneCmd.ExecuteNonQuery();
                    }
                    zoneCmd.Reset();
                }
                if (flowCmd != null && flowBuf.Count > 0)
                {
                    flowCmd.Transaction = tx;
                    foreach (var r in flowBuf)
                    {
                        flowCmd.Reset();
                        for (int i = 0; i < r.Length; i++) flowCmd.Parameters[i].Value = r[i];
                        flowCmd.ExecuteNonQuery();
                    }
                    flowCmd.Reset();
                }
                tx.Commit();
                zoneBuf.Clear(); flowBuf.Clear(); tickBuf.Clear();
                lastFlushMs = flowStartMs;
            }
            catch (Exception ex)
            {
                try { if (tx != null) tx.Rollback(); } catch { }
                try { if (tickCmd != null) tickCmd.Reset(); } catch { }
                try { if (zoneCmd != null) zoneCmd.Reset(); } catch { }
                try { if (flowCmd != null) flowCmd.Reset(); } catch { }
                zoneBuf.Clear(); flowBuf.Clear(); tickBuf.Clear();
                dbReady = false;
                if (!hasLoggedFlushError)
                {
                    hasLoggedFlushError = true;
                    Print("[HFTLogger-NQ] CRITICAL DATABASE FLUSH ERROR: " + ex.Message);
                }
                throw;
            }
        }

        private void CloseDb()
        {
            try
            {
                if (EnableFlowLog && fTicks > 0) BufferFlow();
                FlushAll();
                if (flowCmd != null) { flowCmd.Dispose(); flowCmd = null; }
                if (zoneCmd != null) { zoneCmd.Dispose(); zoneCmd = null; }
                if (tickCmd != null) { tickCmd.Dispose(); tickCmd = null; }
                if (dbConn  != null) { dbConn.Close(); dbConn.Dispose(); dbConn = null; }
            }
            catch (Exception ex) { Print("[HFTLogger-NQ] CloseDb: " + ex.Message); }
            dbReady = false;
        }

        private static long UnixMs(DateTime dt)
        {
            return new DateTimeOffset(dt.ToUniversalTime()).ToUnixTimeMilliseconds();
        }

        #region Properties
        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Tick Resolution (sub-serie)", Order=1, GroupName="0. Sub-serie", Description="NQ: 1.")]
        public int TickResolution { get; set; }

        [NinjaScriptProperty][Range(2, 100)]
        [Display(Name="Min pasos del sweep", Order=1, GroupName="A. Estructura", Description="NQ: 6-10. Default 8.")]
        public int MinPasos { get; set; }

        [NinjaScriptProperty][Range(1, 20)]
        [Display(Name="Max rango tick por vela", Order=2, GroupName="A. Estructura", Description="NQ 1-tick: 1.")]
        public int MaxRangoTickPorVela { get; set; }

        [NinjaScriptProperty][Range(0, 10)]
        [Display(Name="Fallos tolerados", Order=3, GroupName="A. Estructura", Description="NQ: 1.")]
        public int FallosTolerados { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Filtro direccion estricto (cuerpo real)", Order=4, GroupName="A. Estructura")]
        public bool FiltroDireccionEstricto { get; set; }

        [NinjaScriptProperty][Range(0, 100)]
        [Display(Name="Min altura del sweep (ticks)", Order=5, GroupName="A. Estructura", Description="Por debajo = ABSORB. NQ: 3-6.")]
        public int MinSweepTicks { get; set; }

        [NinjaScriptProperty][Range(0, 100)]
        [Display(Name="Max retroceso del sweep (ticks)", Order=6, GroupName="A. Estructura",
            Description="Maxima excursion adversa permitida DENTRO del sweep. NQ: 2-4. Solo aplica a SWEEP.")]
        public int MaxRetrocesoTicks { get; set; }

        [NinjaScriptProperty][Range(0, 100)]
        [Display(Name="Retroceso % de la Altura", Order=7, GroupName="A. Estructura",
            Description="Retroceso permitido como % de la altura del sweep. NQ: 30-50.")]
        public int RetrocesoPctHeight { get; set; }

        [NinjaScriptProperty][Range(1, 2000)]
        [Display(Name="Max avgMs (entre ticks)", Order=1, GroupName="B. Filtros temporales", Description="NQ: 20-40ms.")]
        public int MaxAvgMs { get; set; }

        [NinjaScriptProperty][Range(50, 10000)]
        [Display(Name="Max totalMs (duracion total)", Order=2, GroupName="B. Filtros temporales", Description="NQ: 300-800ms.")]
        public int MaxTotalMs { get; set; }

        [NinjaScriptProperty][Range(10, 5000)]
        [Display(Name="Max pausa entre ticks (ms)", Order=3, GroupName="B. Filtros temporales", Description="NQ: 80-150ms.")]
        public int MaxPausaMs { get; set; }

        [NinjaScriptProperty][Range(0, 50000)]
        [Display(Name="Min velocidad volumen (contratos/seg)", Order=1, GroupName="C. Filtros volumen", Description="NQ: 50-200.")]
        public int MinVolumeRate { get; set; }

        [NinjaScriptProperty][Range(0, 100000)]
        [Display(Name="Min volumen total (contratos)", Order=2, GroupName="C. Filtros volumen", Description="NQ: 30-100.")]
        public int MinTotalVolume { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Bucket PREDATOR avgMs <=", Order=1, GroupName="D. Buckets")]
        public int PredatorAvgMs { get; set; }

        [NinjaScriptProperty][Range(1, 200)]
        [Display(Name="Bucket ULTRA avgMs <=", Order=2, GroupName="D. Buckets")]
        public int UltraAvgMs { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar zonas ABSORB", Order=1, GroupName="DA. Absorcion")]
        public bool MostrarAbsorb { get; set; }

        [NinjaScriptProperty][Range(2, 100)]
        [Display(Name="Min pasos ABSORB", Order=2, GroupName="DA. Absorcion", Description="NQ: 6.")]
        public int MinAbsorbPasos { get; set; }

        [NinjaScriptProperty][Range(1, 5000)]
        [Display(Name="Extension dibujo (barras)", Order=1, GroupName="E. Visual")]
        public int ExtensionDibujo { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Opacidad", Order=2, GroupName="E. Visual")]
        public int Opacidad { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar etiqueta", Order=3, GroupName="E. Visual")]
        public bool MostrarTexto { get; set; }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color PREDATOR", Order=4, GroupName="E. Visual")]
        public Brush ColorPredator { get; set; }
        [Browsable(false)] public string ColorPredatorSerializable
        { get { return Serialize.BrushToString(ColorPredator); } set { ColorPredator = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ULTRA", Order=5, GroupName="E. Visual")]
        public Brush ColorUltra { get; set; }
        [Browsable(false)] public string ColorUltraSerializable
        { get { return Serialize.BrushToString(ColorUltra); } set { ColorUltra = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color bull (Fast)", Order=6, GroupName="E. Visual")]
        public Brush ColorBull { get; set; }
        [Browsable(false)] public string ColorBullSerializable
        { get { return Serialize.BrushToString(ColorBull); } set { ColorBull = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color bear (Fast)", Order=7, GroupName="E. Visual")]
        public Brush ColorBear { get; set; }
        [Browsable(false)] public string ColorBearSerializable
        { get { return Serialize.BrushToString(ColorBear); } set { ColorBear = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ABSORB", Order=8, GroupName="E. Visual")]
        public Brush ColorAbsorb { get; set; }
        [Browsable(false)] public string ColorAbsorbSerializable
        { get { return Serialize.BrushToString(ColorAbsorb); } set { ColorAbsorb = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color texto", Order=9, GroupName="E. Visual")]
        public Brush ColorTexto { get; set; }
        [Browsable(false)] public string ColorTextoSerializable
        { get { return Serialize.BrushToString(ColorTexto); } set { ColorTexto = Serialize.StringToBrush(value); } }

        [Display(Name="Modo Exportacion Puro (sin render)", Order=0, GroupName="F. Database", Description="Desactiva rectangulos, etiquetas, clusters y vacios durante la exportacion.")]
        public bool ModoExportacionPuro { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Enable DB Logging", Order=1, GroupName="F. Database")]
        public bool EnableDbLogging { get; set; }

        [NinjaScriptProperty]
        [Display(Name="DB Path", Order=2, GroupName="F. Database")]
        public string DbPath { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar vacios/expansiones", Order=1, GroupName="G. Vacios")]
        public bool MostrarVacios { get; set; }

        [NinjaScriptProperty][Range(1, 1000)]
        [Display(Name="Vacio: Bin (ticks)", Order=2, GroupName="G. Vacios", Description="Granularidad vertical del escaneo de vacios, en ticks.")]
        public int VoidBinTicks { get; set; }

        [NinjaScriptProperty][Range(1, 100000)]
        [Display(Name="Vacio: Alto minimo (ticks)", Order=3, GroupName="G. Vacios", Description="Alto minimo del rectangulo vacio. Calibrar al rectangulo de referencia.")]
        public int VoidMinAltoTicks { get; set; }

        [NinjaScriptProperty][Range(1, 100000)]
        [Display(Name="Vacio: Ancho minimo (barras)", Order=4, GroupName="G. Vacios", Description="Ancho minimo del rectangulo vacio, en barras.")]
        public int VoidMinAnchoBars { get; set; }

        [NinjaScriptProperty][Range(10, 100000)]
        [Display(Name="Vacio: Lookback (barras)", Order=5, GroupName="G. Vacios", Description="Cuantas barras hacia atras se escanean y dibujan los vacios.")]
        public int VoidLookbackBars { get; set; }

        [NinjaScriptProperty][Range(1, 100000)]
        [Display(Name="Vacio: Recalcular cada (barras)", Order=6, GroupName="G. Vacios")]
        public int VoidRecomputeBars { get; set; }

        [NinjaScriptProperty][Range(0, 100000)]
        [Display(Name="Vacio: Extension extra de zona (barras)", Order=7, GroupName="G. Vacios", Description="Margen extra a la derecha del fin real de cada zona. 0 = footprint real.")]
        public int VoidExtensionBars { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Vacio: Exigir que el precio haya pasado", Order=8, GroupName="G. Vacios", Description="Si esta activo, solo marca vacios en niveles de precio recorridos en la ventana.")]
        public bool VoidExigirTouch { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Vacio: Opacidad", Order=9, GroupName="G. Vacios")]
        public int VoidOpacidad { get; set; }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Vacio: Color", Order=10, GroupName="G. Vacios")]
        public Brush ColorVoid { get; set; }
        [Browsable(false)] public string ColorVoidSerializable
        { get { return Serialize.BrushToString(ColorVoid); } set { ColorVoid = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][Range(1, 100000)]
        [Display(Name="Vacio: Maximo de vacios", Order=11, GroupName="G. Vacios")]
        public int VoidMax { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Vacio: Debug", Order=12, GroupName="G. Vacios")]
        public bool VoidDebug { get; set; }
        #endregion

        #region H. Clusters (densidad de confluencia 4+)
        [Display(Name="Mostrar clusters (4+ zonas)", Order=1, GroupName="H. Clusters", Description="Destaca con otro color el rectangulo donde confluyen 4 o mas zonas visuales.")]
        public bool MostrarClusters { get; set; }

        [Range(2, 20)]
        [Display(Name="Minimo rectangulos solapados", Order=2, GroupName="H. Clusters", Description="Cantidad minima de rectangulos solapados simultaneamente (por defecto 4).")]
        public int MinOverlapRectangulos { get; set; }

        [XmlIgnore]
        [Display(Name="Color relleno cluster", Order=3, GroupName="H. Clusters", Description="Color de relleno para el area exacta de solapamiento.")]
        public Brush ColorCluster { get; set; }
        [Browsable(false)] public string ColorClusterSerializable
        { get { return Serialize.BrushToString(ColorCluster); } set { ColorCluster = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color borde cluster", Order=4, GroupName="H. Clusters", Description="Color del contorno del area de solapamiento.")]
        public Brush ColorBordeCluster { get; set; }
        [Browsable(false)] public string ColorBordeClusterSerializable
        { get { return Serialize.BrushToString(ColorBordeCluster); } set { ColorBordeCluster = Serialize.StringToBrush(value); } }

        [Range(1, 100)]
        [Display(Name="Opacidad cluster", Order=5, GroupName="H. Clusters", Description="Opacidad del relleno del cluster (1 a 100).")]
        public int OpacidadCluster { get; set; }

        [Display(Name="Extender hasta fin de zona actual", Order=6, GroupName="H. Clusters", Description="Si esta activo, extiende el cluster hasta el fin de la zona actual. Si esta inactivo (default), cubre solo el solapamiento visual literal.")]
        public bool ExtenderClusterHastaZonaActual { get; set; }

        [Display(Name="Mostrar etiqueta cluster", Order=7, GroupName="H. Clusters", Description="Muestra una etiqueta indicando la cantidad de zonas solapadas.")]
        public bool MostrarTextoCluster { get; set; }

        [Display(Name="Dibujar linea central POC", Order=8, GroupName="H. Clusters", Description="Dibuja la linea discontinua del punto de maxima confluencia gravitacional dentro del cluster.")]
        public bool DibujarPocCluster { get; set; }
        #endregion
    }
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private HFTZonesNQPureV4_V2[] cacheHFTZonesNQPureV4_V2;
		public HFTZonesNQPureV4_V2 HFTZonesNQPureV4_V2(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return HFTZonesNQPureV4_V2(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}

		public HFTZonesNQPureV4_V2 HFTZonesNQPureV4_V2(ISeries<double> input, int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			if (cacheHFTZonesNQPureV4_V2 != null)
				for (int idx = 0; idx < cacheHFTZonesNQPureV4_V2.Length; idx++)
					if (cacheHFTZonesNQPureV4_V2[idx] != null && cacheHFTZonesNQPureV4_V2[idx].TickResolution == tickResolution && cacheHFTZonesNQPureV4_V2[idx].MinPasos == minPasos && cacheHFTZonesNQPureV4_V2[idx].MaxRangoTickPorVela == maxRangoTickPorVela && cacheHFTZonesNQPureV4_V2[idx].FallosTolerados == fallosTolerados && cacheHFTZonesNQPureV4_V2[idx].FiltroDireccionEstricto == filtroDireccionEstricto && cacheHFTZonesNQPureV4_V2[idx].MinSweepTicks == minSweepTicks && cacheHFTZonesNQPureV4_V2[idx].MaxRetrocesoTicks == maxRetrocesoTicks && cacheHFTZonesNQPureV4_V2[idx].RetrocesoPctHeight == retrocesoPctHeight && cacheHFTZonesNQPureV4_V2[idx].MaxAvgMs == maxAvgMs && cacheHFTZonesNQPureV4_V2[idx].MaxTotalMs == maxTotalMs && cacheHFTZonesNQPureV4_V2[idx].MaxPausaMs == maxPausaMs && cacheHFTZonesNQPureV4_V2[idx].MinVolumeRate == minVolumeRate && cacheHFTZonesNQPureV4_V2[idx].MinTotalVolume == minTotalVolume && cacheHFTZonesNQPureV4_V2[idx].PredatorAvgMs == predatorAvgMs && cacheHFTZonesNQPureV4_V2[idx].UltraAvgMs == ultraAvgMs && cacheHFTZonesNQPureV4_V2[idx].MostrarAbsorb == mostrarAbsorb && cacheHFTZonesNQPureV4_V2[idx].MinAbsorbPasos == minAbsorbPasos && cacheHFTZonesNQPureV4_V2[idx].ExtensionDibujo == extensionDibujo && cacheHFTZonesNQPureV4_V2[idx].Opacidad == opacidad && cacheHFTZonesNQPureV4_V2[idx].MostrarTexto == mostrarTexto && cacheHFTZonesNQPureV4_V2[idx].ColorPredator == colorPredator && cacheHFTZonesNQPureV4_V2[idx].ColorUltra == colorUltra && cacheHFTZonesNQPureV4_V2[idx].ColorBull == colorBull && cacheHFTZonesNQPureV4_V2[idx].ColorBear == colorBear && cacheHFTZonesNQPureV4_V2[idx].ColorAbsorb == colorAbsorb && cacheHFTZonesNQPureV4_V2[idx].ColorTexto == colorTexto && cacheHFTZonesNQPureV4_V2[idx].EnableDbLogging == enableDbLogging && cacheHFTZonesNQPureV4_V2[idx].DbPath == dbPath && cacheHFTZonesNQPureV4_V2[idx].MostrarVacios == mostrarVacios && cacheHFTZonesNQPureV4_V2[idx].VoidBinTicks == voidBinTicks && cacheHFTZonesNQPureV4_V2[idx].VoidMinAltoTicks == voidMinAltoTicks && cacheHFTZonesNQPureV4_V2[idx].VoidMinAnchoBars == voidMinAnchoBars && cacheHFTZonesNQPureV4_V2[idx].VoidLookbackBars == voidLookbackBars && cacheHFTZonesNQPureV4_V2[idx].VoidRecomputeBars == voidRecomputeBars && cacheHFTZonesNQPureV4_V2[idx].VoidExtensionBars == voidExtensionBars && cacheHFTZonesNQPureV4_V2[idx].VoidExigirTouch == voidExigirTouch && cacheHFTZonesNQPureV4_V2[idx].VoidOpacidad == voidOpacidad && cacheHFTZonesNQPureV4_V2[idx].ColorVoid == colorVoid && cacheHFTZonesNQPureV4_V2[idx].VoidMax == voidMax && cacheHFTZonesNQPureV4_V2[idx].VoidDebug == voidDebug && cacheHFTZonesNQPureV4_V2[idx].EqualsInput(input))
						return cacheHFTZonesNQPureV4_V2[idx];
			return CacheIndicator<HFTZonesNQPureV4_V2>(new HFTZonesNQPureV4_V2(){ TickResolution = tickResolution, MinPasos = minPasos, MaxRangoTickPorVela = maxRangoTickPorVela, FallosTolerados = fallosTolerados, FiltroDireccionEstricto = filtroDireccionEstricto, MinSweepTicks = minSweepTicks, MaxRetrocesoTicks = maxRetrocesoTicks, RetrocesoPctHeight = retrocesoPctHeight, MaxAvgMs = maxAvgMs, MaxTotalMs = maxTotalMs, MaxPausaMs = maxPausaMs, MinVolumeRate = minVolumeRate, MinTotalVolume = minTotalVolume, PredatorAvgMs = predatorAvgMs, UltraAvgMs = ultraAvgMs, MostrarAbsorb = mostrarAbsorb, MinAbsorbPasos = minAbsorbPasos, ExtensionDibujo = extensionDibujo, Opacidad = opacidad, MostrarTexto = mostrarTexto, ColorPredator = colorPredator, ColorUltra = colorUltra, ColorBull = colorBull, ColorBear = colorBear, ColorAbsorb = colorAbsorb, ColorTexto = colorTexto, EnableDbLogging = enableDbLogging, DbPath = dbPath, MostrarVacios = mostrarVacios, VoidBinTicks = voidBinTicks, VoidMinAltoTicks = voidMinAltoTicks, VoidMinAnchoBars = voidMinAnchoBars, VoidLookbackBars = voidLookbackBars, VoidRecomputeBars = voidRecomputeBars, VoidExtensionBars = voidExtensionBars, VoidExigirTouch = voidExigirTouch, VoidOpacidad = voidOpacidad, ColorVoid = colorVoid, VoidMax = voidMax, VoidDebug = voidDebug }, input, ref cacheHFTZonesNQPureV4_V2);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.HFTZonesNQPureV4_V2 HFTZonesNQPureV4_V2(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4_V2(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}

		public Indicators.HFTZonesNQPureV4_V2 HFTZonesNQPureV4_V2(ISeries<double> input , int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4_V2(input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.HFTZonesNQPureV4_V2 HFTZonesNQPureV4_V2(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4_V2(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}

		public Indicators.HFTZonesNQPureV4_V2 HFTZonesNQPureV4_V2(ISeries<double> input , int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4_V2(input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}
	}
}

#endregion
