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
    public class HFTZonesNQPureV4 : Indicator
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
                Description              = "Detector HFT EXCLUSIVO para NQ/MNQ con modo ABSORB + logger enriquecido (delta tick-rule, absorcion, flow). Escritura concurrente segura.";
                Name                     = "HFTZonesNQPureV4";
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
                DbPath                   = @"C:\LoggerHFT\data\hft_logger_v4.sqlite";
                EnableFlowLog            = true;
                FlowBucketSeconds        = 1;

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
                if (EnableDbLogging) SetupDb();
            }
            else if (State == State.Terminated)
            {
                CloseDb();
                LimpiarClusters();
            }
        }

        private void ResetState()
        {
            streak = 0; validSteps = 0; dir = 0; fails = 0;
            msList.Clear(); priceList.Clear(); volList.Clear(); signList.Clear();
            totalVol = 0;
            extremo = 0; maxRetroceso = 0;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress == 1)
            {
                if (CurrentBars[1] < 5) return;
                ProcesarSweeps();
                DibujarPendientes();
                return;
            }
            if (BarsInProgress != 0) return;
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
                Finalizar();
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
                        Finalizar();
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
                        Finalizar();
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
        }

        private void Finalizar()
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
                        ColorZ = col, Reporte = txt
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

            // 5. Duracion del cluster: el doble que el resto de rectangulos (2 * ExtensionDibujo)
            int clusterEndBar = currentBar + (ExtensionDibujo * 2);
            int endAgo = -(ExtensionDibujo * 2);

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
                    if (ovHi > ovLo) // Se intersectan en precio
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

                using (var cmd = new SQLiteCommand(
                    @"CREATE TABLE IF NOT EXISTS hft_zones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, instrument TEXT, start_ts INTEGER, end_ts INTEGER,
                        bucket TEXT, dir INTEGER, price_upper REAL, price_lower REAL, price_mid REAL, height_ticks REAL,
                        pasos INTEGER, valid_steps INTEGER, avg_ms REAL, total_ms REAL, vol_rate REAL, total_vol REAL,
                        max_tick_vol REAL, cvd_sweep REAL, buy_vol REAL, sell_vol REAL, delta_slope REAL, delta_first REAL,
                        delta_second REAL, no_move_ticks INTEGER, no_move_vol REAL, max_level_ticks INTEGER, tick_res INTEGER,
                        max_retro REAL);
                      CREATE INDEX IF NOT EXISTS idx_hz_ts ON hft_zones(start_ts);
                      CREATE INDEX IF NOT EXISTS idx_hz_inst ON hft_zones(instrument);
                      CREATE TABLE IF NOT EXISTS hft_flow (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, instrument TEXT, bar_ts INTEGER, open REAL, high REAL,
                        low REAL, close REAL, volume REAL, buy_vol REAL, sell_vol REAL, delta REAL, n_ticks INTEGER);
                      CREATE INDEX IF NOT EXISTS idx_hf_ts ON hft_flow(instrument, bar_ts);", dbConn))
                    cmd.ExecuteNonQuery();

                // Migracion suave: si la tabla ya existia sin max_retro (data previa), la agrega.
                try { using (var mig = new SQLiteCommand("ALTER TABLE hft_zones ADD COLUMN max_retro REAL;", dbConn)) mig.ExecuteNonQuery(); }
                catch { /* la columna ya existe */ }

                EnsureUnique("hft_zones", "ux_hz", "instrument, start_ts");
                EnsureUnique("hft_flow",  "ux_hf", "instrument, bar_ts");

                zoneCmd = new SQLiteCommand(
                    @"INSERT OR IGNORE INTO hft_zones
                      (instrument,start_ts,end_ts,bucket,dir,price_upper,price_lower,price_mid,height_ticks,pasos,valid_steps,
                       avg_ms,total_ms,vol_rate,total_vol,max_tick_vol,cvd_sweep,buy_vol,sell_vol,delta_slope,delta_first,
                       delta_second,no_move_ticks,no_move_vol,max_level_ticks,tick_res,max_retro)
                      VALUES (@inst,@s,@e,@b,@dir,@pu,@pl,@pm,@ht,@p,@vs,@am,@tm,@vr,@tv,@mtv,@cvd,@buy,@sell,@dsl,@d1,@d2,@nmt,@nmv,@mlt,@tr,@mr)", dbConn);
                foreach (string p in new[]{"@inst","@s","@e","@b","@dir","@pu","@pl","@pm","@ht","@p","@vs","@am","@tm","@vr","@tv",
                    "@mtv","@cvd","@buy","@sell","@dsl","@d1","@d2","@nmt","@nmv","@mlt","@tr","@mr"})
                    zoneCmd.Parameters.Add(new SQLiteParameter(p));
                zoneCmd.Prepare();

                flowCmd = new SQLiteCommand(
                    @"INSERT OR IGNORE INTO hft_flow
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

        private void EnsureUnique(string table, string idx, string cols)
        {
            try
            {
                using (var c = new SQLiteCommand("CREATE UNIQUE INDEX IF NOT EXISTS " + idx + " ON " + table + "(" + cols + ");", dbConn))
                    c.ExecuteNonQuery();
            }
            catch
            {
                try
                {
                    using (var c = new SQLiteCommand(
                        "DELETE FROM " + table + " WHERE id NOT IN (SELECT MIN(id) FROM " + table + " GROUP BY " + cols + ");" +
                        "CREATE UNIQUE INDEX IF NOT EXISTS " + idx + " ON " + table + "(" + cols + ");", dbConn))
                        c.ExecuteNonQuery();
                }
                catch (Exception ex) { Print("[HFTLogger] EnsureUnique " + table + ": " + ex.Message); }
            }
        }

        private void PersistZone(Zone z)
        {
            if (!dbReady) return;
            zoneBuf.Add(new object[] {
                Instrument.FullName, UnixMs(z.StartTime), UnixMs(z.EndTime), z.Bucket.ToString(), z.Direction,
                z.Upper, z.Lower, (z.Upper + z.Lower) / 2.0, z.HeightTicks, z.Pasos, z.ValidSteps,
                z.AvgMs, z.TotalMs, z.VolRate, z.TotalVol, z.MaxTickVol, z.Cvd, z.BuyVol, z.SellVol,
                z.DeltaSlope, z.DeltaFirst, z.DeltaSecond, z.NoMoveTicks, z.NoMoveVol, z.MaxLevelTicks,
                TickResolution, z.MaxRetro });
            FlushAll();
        }

        private void FlushAll()
        {
            if (!dbReady) return;
            if (zoneBuf.Count == 0 && flowBuf.Count == 0) return;
            SQLiteTransaction tx = null;
            try
            {
                tx = dbConn.BeginTransaction();
                if (zoneCmd != null)
                {
                    zoneCmd.Transaction = tx;
                    foreach (var r in zoneBuf)
                    {
                        for (int i = 0; i < r.Length; i++) zoneCmd.Parameters[i].Value = r[i];
                        zoneCmd.ExecuteNonQuery();
                    }
                }
                if (flowCmd != null)
                {
                    flowCmd.Transaction = tx;
                    foreach (var r in flowBuf)
                    {
                        for (int i = 0; i < r.Length; i++) flowCmd.Parameters[i].Value = r[i];
                        flowCmd.ExecuteNonQuery();
                    }
                }
                tx.Commit();
                zoneBuf.Clear(); flowBuf.Clear();
                lastFlushMs = flowStartMs;
            }
            catch (Exception ex)
            {
                try { if (tx != null) tx.Rollback(); } catch { }
                Print("[HFTLogger-NQ] flush: " + ex.Message);
                if (zoneBuf.Count + flowBuf.Count > MaxBuf) { zoneBuf.Clear(); flowBuf.Clear(); }
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
		private HFTZonesNQPureV4[] cacheHFTZonesNQPureV4;
		public HFTZonesNQPureV4 HFTZonesNQPureV4(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return HFTZonesNQPureV4(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}

		public HFTZonesNQPureV4 HFTZonesNQPureV4(ISeries<double> input, int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			if (cacheHFTZonesNQPureV4 != null)
				for (int idx = 0; idx < cacheHFTZonesNQPureV4.Length; idx++)
					if (cacheHFTZonesNQPureV4[idx] != null && cacheHFTZonesNQPureV4[idx].TickResolution == tickResolution && cacheHFTZonesNQPureV4[idx].MinPasos == minPasos && cacheHFTZonesNQPureV4[idx].MaxRangoTickPorVela == maxRangoTickPorVela && cacheHFTZonesNQPureV4[idx].FallosTolerados == fallosTolerados && cacheHFTZonesNQPureV4[idx].FiltroDireccionEstricto == filtroDireccionEstricto && cacheHFTZonesNQPureV4[idx].MinSweepTicks == minSweepTicks && cacheHFTZonesNQPureV4[idx].MaxRetrocesoTicks == maxRetrocesoTicks && cacheHFTZonesNQPureV4[idx].RetrocesoPctHeight == retrocesoPctHeight && cacheHFTZonesNQPureV4[idx].MaxAvgMs == maxAvgMs && cacheHFTZonesNQPureV4[idx].MaxTotalMs == maxTotalMs && cacheHFTZonesNQPureV4[idx].MaxPausaMs == maxPausaMs && cacheHFTZonesNQPureV4[idx].MinVolumeRate == minVolumeRate && cacheHFTZonesNQPureV4[idx].MinTotalVolume == minTotalVolume && cacheHFTZonesNQPureV4[idx].PredatorAvgMs == predatorAvgMs && cacheHFTZonesNQPureV4[idx].UltraAvgMs == ultraAvgMs && cacheHFTZonesNQPureV4[idx].MostrarAbsorb == mostrarAbsorb && cacheHFTZonesNQPureV4[idx].MinAbsorbPasos == minAbsorbPasos && cacheHFTZonesNQPureV4[idx].ExtensionDibujo == extensionDibujo && cacheHFTZonesNQPureV4[idx].Opacidad == opacidad && cacheHFTZonesNQPureV4[idx].MostrarTexto == mostrarTexto && cacheHFTZonesNQPureV4[idx].ColorPredator == colorPredator && cacheHFTZonesNQPureV4[idx].ColorUltra == colorUltra && cacheHFTZonesNQPureV4[idx].ColorBull == colorBull && cacheHFTZonesNQPureV4[idx].ColorBear == colorBear && cacheHFTZonesNQPureV4[idx].ColorAbsorb == colorAbsorb && cacheHFTZonesNQPureV4[idx].ColorTexto == colorTexto && cacheHFTZonesNQPureV4[idx].EnableDbLogging == enableDbLogging && cacheHFTZonesNQPureV4[idx].DbPath == dbPath && cacheHFTZonesNQPureV4[idx].MostrarVacios == mostrarVacios && cacheHFTZonesNQPureV4[idx].VoidBinTicks == voidBinTicks && cacheHFTZonesNQPureV4[idx].VoidMinAltoTicks == voidMinAltoTicks && cacheHFTZonesNQPureV4[idx].VoidMinAnchoBars == voidMinAnchoBars && cacheHFTZonesNQPureV4[idx].VoidLookbackBars == voidLookbackBars && cacheHFTZonesNQPureV4[idx].VoidRecomputeBars == voidRecomputeBars && cacheHFTZonesNQPureV4[idx].VoidExtensionBars == voidExtensionBars && cacheHFTZonesNQPureV4[idx].VoidExigirTouch == voidExigirTouch && cacheHFTZonesNQPureV4[idx].VoidOpacidad == voidOpacidad && cacheHFTZonesNQPureV4[idx].ColorVoid == colorVoid && cacheHFTZonesNQPureV4[idx].VoidMax == voidMax && cacheHFTZonesNQPureV4[idx].VoidDebug == voidDebug && cacheHFTZonesNQPureV4[idx].EqualsInput(input))
						return cacheHFTZonesNQPureV4[idx];
			return CacheIndicator<HFTZonesNQPureV4>(new HFTZonesNQPureV4(){ TickResolution = tickResolution, MinPasos = minPasos, MaxRangoTickPorVela = maxRangoTickPorVela, FallosTolerados = fallosTolerados, FiltroDireccionEstricto = filtroDireccionEstricto, MinSweepTicks = minSweepTicks, MaxRetrocesoTicks = maxRetrocesoTicks, RetrocesoPctHeight = retrocesoPctHeight, MaxAvgMs = maxAvgMs, MaxTotalMs = maxTotalMs, MaxPausaMs = maxPausaMs, MinVolumeRate = minVolumeRate, MinTotalVolume = minTotalVolume, PredatorAvgMs = predatorAvgMs, UltraAvgMs = ultraAvgMs, MostrarAbsorb = mostrarAbsorb, MinAbsorbPasos = minAbsorbPasos, ExtensionDibujo = extensionDibujo, Opacidad = opacidad, MostrarTexto = mostrarTexto, ColorPredator = colorPredator, ColorUltra = colorUltra, ColorBull = colorBull, ColorBear = colorBear, ColorAbsorb = colorAbsorb, ColorTexto = colorTexto, EnableDbLogging = enableDbLogging, DbPath = dbPath, MostrarVacios = mostrarVacios, VoidBinTicks = voidBinTicks, VoidMinAltoTicks = voidMinAltoTicks, VoidMinAnchoBars = voidMinAnchoBars, VoidLookbackBars = voidLookbackBars, VoidRecomputeBars = voidRecomputeBars, VoidExtensionBars = voidExtensionBars, VoidExigirTouch = voidExigirTouch, VoidOpacidad = voidOpacidad, ColorVoid = colorVoid, VoidMax = voidMax, VoidDebug = voidDebug }, input, ref cacheHFTZonesNQPureV4);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.HFTZonesNQPureV4 HFTZonesNQPureV4(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}

		public Indicators.HFTZonesNQPureV4 HFTZonesNQPureV4(ISeries<double> input , int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4(input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.HFTZonesNQPureV4 HFTZonesNQPureV4(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}

		public Indicators.HFTZonesNQPureV4 HFTZonesNQPureV4(ISeries<double> input , int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxRetrocesoTicks, int retrocesoPctHeight, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorTexto, bool enableDbLogging, string dbPath, bool mostrarVacios, int voidBinTicks, int voidMinAltoTicks, int voidMinAnchoBars, int voidLookbackBars, int voidRecomputeBars, int voidExtensionBars, bool voidExigirTouch, int voidOpacidad, Brush colorVoid, int voidMax, bool voidDebug)
		{
			return indicator.HFTZonesNQPureV4(input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxRetrocesoTicks, retrocesoPctHeight, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorTexto, enableDbLogging, dbPath, mostrarVacios, voidBinTicks, voidMinAltoTicks, voidMinAnchoBars, voidLookbackBars, voidRecomputeBars, voidExtensionBars, voidExigirTouch, voidOpacidad, colorVoid, voidMax, voidDebug);
		}
	}
}

#endregion
