// # meta indicator=HFTClusterZonesNQ,version=1.1.0
// HFTClusterZonesNQ.cs - Detector HFT NQ/MNQ con CLUSTERS POR HALO DE PROXIMIDAD (KDE)
// y CONSUMO DINÁMICO DE LIQUIDEZ (DESGASTE PROGRESIVO POR CONTRATO NEGOCIADO).
//
// Innovaciones de Arquitectura de Microestructura:
// 1. HALO GRAVITACIONAL CONTINUO (KDE): En lugar de solapamiento discreto binario, cada sweep
//    emite un kernel gaussiano de influencia espacial (sigma en ticks). Sweeps cercanos combinan
//    sus campos y generan clusters de alta atracción sin necesidad de solapamiento estricto.
// 2. CONSUMO PROGRESIVO DE LIQUIDEZ: Cada contrato negociado dentro del rango [Lower, Upper]
//    desgasta la capacidad del cluster. La opacidad y fuerza visual decaen en tiempo real con el flujo.
// 3. MÁQUINA DE ESTADOS FINITOS: Active -> TouchedPOC -> Depleted (absorbido) | Invalidated | Expired.
// 4. SESGO DE COLOR POR DELTA: El cluster se tiñe según la dominancia neta (Bull, Bear o Absorción).
// 5. RENDIMIENTO NT8 DE ALTA FRECUENCIA: Actualizaciones visuales optimizadas por delta de volumen
//    para garantizar 60 FPS sin bloqueos en sub-series de 1-tick.

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

// El enum va en el namespace GLOBAL, no dentro de NinjaTrader.NinjaScript.Indicators.
// Motivo: NT8 genera wrappers de este indicador en los namespaces Strategies y
// MarketAnalyzerColumns, y las firmas generadas incluyen el tipo de cada
// NinjaScriptProperty. Desde esos namespaces un tipo declarado en Indicators no se
// resuelve y la compilacion falla con CS0246. Es el mismo patron que usa BigTrap2.cs
// para sus cuatro enums.
//
// Los otros enums del archivo (HFTClusterState, HFTZoneBucket) SI pueden vivir adentro:
// nunca son el tipo de una propiedad expuesta, asi que no aparecen en el codigo generado.

/// <summary>Como pesa cada zona en el campo gravitacional del cluster.</summary>
public enum HFTPesoZona
{
    Conteo,      // 1 por zona: reproduce el comportamiento original
    Volumen,     // proporcional al volumen, normalizado por la mediana del pool
    LogVolumen   // logaritmico: una zona de 10x el volumen pesa ~2x, no 10x
}

namespace NinjaTrader.NinjaScript.Indicators
{
    public enum HFTClusterState
    {
        Active,
        TouchedPOC,
        Depleted,
        Invalidated,
        Expired
    }

    public enum HFTZoneBucket
    {
        Predator,
        Ultra,
        Fast,
        Absorb
    }

    public class HFTClusterZonesNQ : Indicator
    {
        public sealed class Zone
        {
            public int          StartBar, EndBar;
            public int          DrawnBar, VisualEndBar;
            public DateTime     StartTime, EndTime;
            public double       Upper, Lower;
            public int          Direction;
            public HFTZoneBucket Bucket;
            public double       AvgMs, TotalMs, VolRate;
            public int          Pasos, ValidSteps;
            public double       TotalVol;
            public double       MaxRetro;
            public double       MaxTickVol;
            public double       Cvd, BuyVol, SellVol;
            public double       DeltaSlope, DeltaFirst, DeltaSecond;
            public int          NoMoveTicks, MaxLevelTicks;
            public double       NoMoveVol;
            public double       HeightTicks;
            public string       TagRect, TagText;
            public bool         Drawn;
            public Brush        ColorZ;
            public string       Reporte;
        }

        public sealed class Cluster
        {
            public int              Id;
            public string           Tag;
            public double           Lower;
            public double           Upper;
            public double           PocPrice;
            public int              StartBar;
            public int              EndBar;
            public DateTime         StartTime;
            public DateTime         EndTime;
            public double           PeakDensity;
            public double           SeedVolume;
            public double           SeedCvd;
            public double           CapacityVolume;
            public double           VolumeInside;
            public double           DeltaInside;
            public bool             TouchedPoc;
            public HFTClusterState  State;
            public int              ContributingZonesCount;
            public Brush            FillBrush;
            public Brush            BorderBrush;
            public double           LastDrawnVolume;
            public int              LastDrawnOpacity;
            public bool             Drawn;
        }

        // ===================== MOTOR SWEEPS HFT =====================
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

        // ===================== FLOW STREAM =====================
        private long   flowBucket = long.MinValue;
        private long   flowStartMs;
        private double fO, fH, fL, fC, fVol, fBuy, fSell;
        private int    fTicks;

        // ===================== COLECCIONES ACTIVAS =====================
        private readonly List<Zone> zones = new List<Zone>();
        public IReadOnlyList<Zone> PublicZones { get { return zones; } }

        private int clusterCounter = 0;
        private readonly List<Cluster> clusters = new List<Cluster>();
        private readonly List<string> activeDrawTags = new List<string>();

        // ===================== PERSISTENCIA (SQLITE & CSV) =====================
        private SQLiteConnection dbConn;
        private SQLiteCommand    flowCmd, zoneCmd, clusterCmd;
        private bool             dbReady = false;
        private readonly List<object[]> zoneBuf    = new List<object[]>();
        private readonly List<object[]> flowBuf    = new List<object[]>();
        private readonly List<object[]> clusterBuf = new List<object[]>();
        private long   lastFlushMs = 0;
        private const int BatchSize = 300;
        private const int FlushMs   = 2000;
        private const int MaxBuf    = 150000;

        private StreamWriter csvWriter;
        private bool         csvReady = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description              = "Detector HFT NQ con Clusters Gravitacionales por Kernel de Proximidad y Consumo Progresivo de Liquidez.";
                Name                     = "HFTClusterZonesNQ";
                Calculate                = Calculate.OnBarClose;
                IsOverlay                = true;
                DisplayInDataBox         = true;
                DrawOnPricePanel         = true;
                PaintPriceMarkers        = true;
                IsSuspendedWhileInactive = true;

                // 0. Sub-serie
                TickResolution           = 1;

                // A. Estructura Sweeps
                MinPasos                 = 8;
                MaxRangoTickPorVela      = 1;
                FallosTolerados          = 1;
                FiltroDireccionEstricto  = true;
                MinSweepTicks            = 4;
                MaxRetrocesoTicks        = 2;
                RetrocesoPctHeight       = 50;

                // B. Filtros temporales
                MaxAvgMs                 = 25;
                MaxTotalMs               = 500;
                MaxPausaMs               = 100;

                // C. Filtros volumen
                MinVolumeRate            = 100;
                // VUELTO A 50 el 2026-09-07, despues de probarlo en el chart.
                //
                // Con 10 nacen ~7.000 zonas por sesion en vez de ~480, y eso rompe el
                // indicador de dos maneras a la vez: satura el arbol de objetos de dibujo
                // de NinjaTrader al cargar, y hace que los clusters se fusionen hasta
                // quedar enormes -- ancho mediano de 70 ticks contra 22 con umbral 50.
                //
                // La configuracion de investigacion (umbral 10, peso por volumen) sigue
                // siendo la elegida por el test de estabilidad, pero vive en Python
                // (hftzones_nq.CAMPAIGN_FROZEN), donde 7.000 zonas no cuestan nada y no
                // hay nada que dibujar. El chart es para MIRAR el objeto; la medicion no
                // pasa por aca. Son dos usos distintos y no tienen por que compartir
                // defaults.
                MinTotalVolume           = 50;

                // D. Buckets
                PredatorAvgMs            = 5;
                UltraAvgMs               = 15;
                MostrarAbsorb            = true;
                MinAbsorbPasos           = 6;

                // E. Visual Zonas Individuales
                DibujarZonasIndividuales = false; // Por defecto dejamos chart limpio enfocado en clusters
                ExtensionDibujo          = 400;
                OpacidadZonas            = 20;
                MostrarTextoZonas        = false;
                ColorPredator            = Brushes.Gold;
                ColorUltra               = Brushes.Silver;
                ColorBull                = Brushes.DodgerBlue;
                ColorBear                = Brushes.OrangeRed;
                ColorAbsorb              = Brushes.MediumPurple;
                ColorTexto               = Brushes.Silver;

                // H. Clusters: Kernel de Proximidad & Halo
                MostrarClusters          = true;
                // Configuracion congelada por el test de estabilidad target-free
                // (turnover 0.6% contra un contrato de 5%; ~55 clusters por sesion
                // cubriendo ~5% del rango). Provisional: una sesion, validacion de
                // tres en curso al momento de escribir esto.
                // Conteo, no Volumen: es lo que la paridad certifica y lo que el chart
                // necesita para ser legible. El peso continuo se barre en Python.
                PesoZona                 = HFTPesoZona.Conteo;
                MinContributingZones     = 3;
                SoloLogEnVivo            = true;
                HaloSigmaTicks           = 3.0;   // Ancho de banda del kernel gaussiano en ticks
                MinClusterDensity        = 3.0;   // Umbral de densidad de confluencia continua
                ClusterLookbackZones     = 120;   // Cantidad de zonas recientes evaluadas en halo
                MaxClusterAgeBars        = 800;   // Barras antes de que un cluster inactivo expire

                // I. Consumo y Desgaste Dinámico
                ActivarConsumoVolumen    = true;
                MinCapacityVolume        = 1200;  // Piso de contratos necesarios para agotar un cluster
                CapacityMultiplier       = 2.5;   // Multiplicador sobre el volumen semilla original
                InvalidationTicks        = 14;    // Perforación en ticks para invalidación violenta
                RedrawVolumeThreshold    = 50;    // Redibujar en sub-serie cada N contratos consumidos

                // J. Visual Clusters
                OpacidadCluster          = 60;
                OpacidadMinima           = 8;
                ProyectarAlFuturo         = true;
                MostrarTextoCluster      = true;
                DibujarPocCluster        = true;
                OcultarAgotados          = false; // Si false, se mantienen en opacidad mínima como zonas absorbidas
                OcultarInvalidados       = true;

                ColorClusterNeutral      = Brushes.Gold;
                ColorClusterBull         = Brushes.DeepSkyBlue;
                ColorClusterBear         = Brushes.Crimson;
                ColorBordeCluster        = Brushes.DarkOrange;

                // K. Logging
                EnableDbLogging          = true;
                DbPath                   = @"C:\LoggerHFT\data\hft_logger_v4.sqlite";
                EnableEventCsv           = true;
                EventLogPath             = @"C:\LoggerHFT\data\hft_cluster_events.csv";
                EnableFlowLog            = true;
                FlowBucketSeconds        = 1;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, TickResolution);
            }
            else if (State == State.DataLoaded)
            {
                ResetState();
                zones.Clear();
                clusters.Clear();
                activeDrawTags.Clear();
                idCounter      = 0;
                clusterCounter = 0;
                lastSide       = 0;
                flowBucket     = long.MinValue;
                fTicks         = 0;

                if (EnableDbLogging) SetupDb();
                if (EnableEventCsv)  SetupCsv();
            }
            else if (State == State.Terminated)
            {
                CloseCsv();
                CloseDb();
                LimpiarDibujos();
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

                if (ActivarConsumoVolumen && clusters.Count > 0)
                {
                    ActualizarConsumoTick(Closes[1][0], Volumes[1][0], lastSide);
                }
                return;
            }

            if (BarsInProgress != 0) return;
            if (CurrentBars[0] < 2) return;

            // En cierre de barra primaria: chequear expiración temporal y refrescar visuales
            VerificarExpiracionClusters();
            DibujarTodo(false);
        }

        // ===================== DETECTOR DE SWEEPS HFT =====================
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
                FinalizarSweep();
                dir = 0;
                return;
            }

            if (dir == 0)
            {
                if (isDown)    { dir = -1; IniciarSweep(ms, vol, cl, signedVol); }
                else if (isUp) { dir =  1; IniciarSweep(ms, vol, cl, signedVol); }
            }
            else if (dir == -1)
            {
                if (isDown) { ContinuarSweep(ms, vol, cl, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    double currentRetracement = (cl - extremo) / TickSize;
                    double sweepHeight = (swH - swL) / TickSize;
                    double maxAllowedRetracement = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepHeight);

                    if (currentRetracement <= maxAllowedRetracement)
                    {
                        ContinuarSweep(ms, vol, cl, signedVol, false);
                    }
                    else
                    {
                        FinalizarSweep();
                        if (isUp) { dir = 1; IniciarSweep(ms, vol, cl, signedVol); }
                        else        dir = 0;
                    }
                }
            }
            else
            {
                if (isUp) { ContinuarSweep(ms, vol, cl, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    double currentRetracement = (extremo - cl) / TickSize;
                    double sweepHeight = (swH - swL) / TickSize;
                    double maxAllowedRetracement = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepHeight);

                    if (currentRetracement <= maxAllowedRetracement)
                    {
                        ContinuarSweep(ms, vol, cl, signedVol, false);
                    }
                    else
                    {
                        FinalizarSweep();
                        if (isDown) { dir = -1; IniciarSweep(ms, vol, cl, signedVol); }
                        else          dir = 0;
                    }
                }
            }
        }

        private void IniciarSweep(double ms, double vol, double cl, double signedVol)
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

        private void ContinuarSweep(double ms, double vol, double cl, double signedVol, bool valid)
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

        private void FinalizarSweep()
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
                    HFTZoneBucket bucket; Brush col; string bucketTxt;
                    if (isAbsorb)
                    {
                        bucket = HFTZoneBucket.Absorb; col = ColorAbsorb; bucketTxt = "ABSORB";
                    }
                    else
                    {
                        bucket = avgMs <= PredatorAvgMs ? HFTZoneBucket.Predator
                               : avgMs <= UltraAvgMs    ? HFTZoneBucket.Ultra : HFTZoneBucket.Fast;
                        col = bucket == HFTZoneBucket.Predator ? ColorPredator
                            : bucket == HFTZoneBucket.Ultra    ? ColorUltra
                            : (dir == 1 ? ColorBull : ColorBear);
                        bucketTxt = bucket == HFTZoneBucket.Predator ? "PRED"
                                  : bucket == HFTZoneBucket.Ultra    ? "ULTRA"
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
                    string tag = "HFTZN_" + idCounter;

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

                    if (MostrarClusters)
                    {
                        EvaluarHaloClusters(zones.Count - 1);
                    }
                }
            }
            ResetState();
        }

        // ===================== MOTOR DE HALO CONTINUO (KDE) =====================
        private void EvaluarHaloClusters(int newIdx)
        {
            if (newIdx < 0 || newIdx >= zones.Count) return;
            Zone newZ = zones[newIdx];

            // 1. Filtrar zonas activas recientes dentro de la ventana de lookback
            List<Zone> pool = new List<Zone>();
            int searchStart = Math.Max(0, zones.Count - Math.Max(10, ClusterLookbackZones));
            for (int i = searchStart; i < zones.Count; i++)
            {
                Zone z = zones[i];
                if (CurrentBars[0] - z.StartBar > MaxClusterAgeBars) continue;
                pool.Add(z);
            }

            if (pool.Count < 2) return;

            // 2. Determinar envolvente global de precios de las zonas activas
            double minP = double.MaxValue;
            double maxP = double.MinValue;
            for (int i = 0; i < pool.Count; i++)
            {
                if (pool[i].Lower < minP) minP = pool[i].Lower;
                if (pool[i].Upper > maxP) maxP = pool[i].Upper;
            }

            // Margen de 3 sigmas a los extremos
            double sigmaPrice = HaloSigmaTicks * TickSize;
            minP -= (3.0 * sigmaPrice);
            maxP += (3.0 * sigmaPrice);

            long minTk = (long)Math.Floor(minP / TickSize);
            long maxTk = (long)Math.Ceiling(maxP / TickSize);
            if (maxTk - minTk > 2500) return; // Protección contra rangos anómalos

            // 3b. PESO DE CADA ZONA (agregado 2026-09-07 tras el test de estabilidad).
            //
            // El indicador usaba kernel suave para la DISTANCIA y conteo binario para la
            // PERTENENCIA: cada zona que sobrevivia al umbral aportaba 1, y las que no,
            // 0. Medido con el contrato del repo (volumen +-1 en dos tercios de los
            // ticks), el turnover de clusters daba 53% con umbral 25 y densidad 8.
            // Ponderando por volumen baja a 24%, y con umbral 10 baja de 5.8% a 1.0%.
            //
            // El peso se normaliza por la MEDIANA de volumen del pool para que
            // MinClusterDensity siga significando aproximadamente "cuantas zonas" y las
            // dos variantes sean comparables sin recalibrar el umbral.
            double[] pesoZona = new double[pool.Count];
            if (PesoZona == HFTPesoZona.Conteo)
            {
                for (int i = 0; i < pool.Count; i++) pesoZona[i] = 1.0;
            }
            else
            {
                List<double> vols = new List<double>();
                for (int i = 0; i < pool.Count; i++)
                    if (pool[i].TotalVol > 0) vols.Add(pool[i].TotalVol);
                vols.Sort();
                double refVol = vols.Count > 0 ? vols[vols.Count / 2] : 1.0;
                if (refVol <= 0) refVol = 1.0;
                for (int i = 0; i < pool.Count; i++)
                {
                    double r = pool[i].TotalVol / refVol;
                    pesoZona[i] = PesoZona == HFTPesoZona.Volumen
                        ? r
                        : Math.Log(1.0 + r) / Math.Log(2.0);   // log comprime la cola
                }
            }

            // 3. CAMPO GAUSSIANO — dispersion por zona, no barrido por tick.
            //
            // POR QUE CAMBIO (2026-09-07). La version anterior recorria CADA tick de la
            // envolvente (hasta 2.500) y para cada uno evaluaba TODAS las zonas del pool
            // (hasta 120), llamando Math.Exp cada vez: ~300.000 exponenciales por
            // llamada. Con MinTotalVolume=10 nacen ~7.000 zonas por sesion y esto corre
            // en cada nacimiento: ~2.000 millones de exponenciales por sesion. Eso
            // congelaba NinjaTrader al cargar el chart.
            //
            // Ahora cada zona DISPERSA su aporte solo sobre los ticks de su propio radio
            // (3.5 sigma, ~11 ticks con sigma=3), y la exponencial sale de una tabla
            // precomputada indexada por distancia entera en ticks. Costo: 120 zonas x 22
            // ticks = ~2.600 sumas, sin una sola exponencial. Dos ordenes de magnitud.
            //
            // EL RESULTADO ES BIT A BIT IDENTICO. La acumulacion de cada tick recorre las
            // zonas en el MISMO orden del pool que el barrido anterior, asi que la suma
            // en punto flotante se hace en el mismo orden y da el mismo double. Esto no
            // es un detalle: si el orden cambiara, dos corridas podrian caer de lados
            // distintos de MinClusterDensity en un empate.
            //
            // La distancia en ticks es ENTERA por construccion: bordes de zona y precios
            // de grilla son ambos multiplos de TickSize.
            int radioTicks = (int)Math.Floor(3.5 * HaloSigmaTicks);
            double twoSigmaSq = 2.0 * HaloSigmaTicks * HaloSigmaTicks;

            double[] expLookup = new double[radioTicks + 1];
            for (int d = 0; d <= radioTicks; d++)
                expLookup[d] = Math.Exp(-((double)d * d) / twoSigmaSq);

            Dictionary<long, double> densityMap   = new Dictionary<long, double>();
            Dictionary<long, double> volWeightMap = new Dictionary<long, double>();
            Dictionary<long, double> acumD = new Dictionary<long, double>();
            Dictionary<long, double> acumV = new Dictionary<long, double>();

            for (int i = 0; i < pool.Count; i++)
            {
                Zone z = pool[i];
                long zLoTk = (long)Math.Round(Math.Min(z.Lower, z.Upper) / TickSize);
                long zHiTk = (long)Math.Round(Math.Max(z.Lower, z.Upper) / TickSize);

                long desde = Math.Max(minTk, zLoTk - radioTicks);
                long hasta = Math.Min(maxTk, zHiTk + radioTicks);

                for (long tk = desde; tk <= hasta; tk++)
                {
                    int d = tk < zLoTk ? (int)(zLoTk - tk)
                          : tk > zHiTk ? (int)(tk - zHiTk)
                          : 0;
                    if (d > radioTicks) continue;

                    double weight = pesoZona[i] * expLookup[d];
                    double dPrev, vPrev;
                    acumD[tk] = (acumD.TryGetValue(tk, out dPrev) ? dPrev : 0.0) + weight;
                    acumV[tk] = (acumV.TryGetValue(tk, out vPrev) ? vPrev : 0.0)
                                + (weight * z.TotalVol);
                }
            }

            foreach (KeyValuePair<long, double> kv in acumD)
            {
                if (kv.Value >= MinClusterDensity)
                {
                    densityMap[kv.Key]   = kv.Value;
                    volWeightMap[kv.Key] = acumV[kv.Key];
                }
            }

            if (densityMap.Count == 0) return;

            // 4. Segmentar ticks calificados en islas continuas (tolerancia de 1 tick de separación)
            List<long> qTicks = densityMap.Keys.ToList();
            qTicks.Sort();

            List<List<long>> islands = new List<List<long>>();
            List<long> currentIsland = new List<long>();

            for (int i = 0; i < qTicks.Count; i++)
            {
                if (currentIsland.Count == 0)
                {
                    currentIsland.Add(qTicks[i]);
                    continue;
                }

                if (qTicks[i] - currentIsland[currentIsland.Count - 1] <= 1)
                {
                    currentIsland.Add(qTicks[i]);
                }
                else
                {
                    islands.Add(currentIsland);
                    currentIsland = new List<long> { qTicks[i] };
                }
            }
            if (currentIsland.Count > 0) islands.Add(currentIsland);

            // 5. Procesar o actualizar cada isla como Cluster
            for (int c = 0; c < islands.Count; c++)
            {
                List<long> island = islands[c];
                double cLower = island.Min() * TickSize - (TickSize * 0.5);
                double cUpper = island.Max() * TickSize + (TickSize * 0.5);

                // Encontrar POC de máxima densidad gravitacional
                long pocTk = island[0];
                double peakDensity = 0.0;
                double maxVolW = 0.0;

                for (int t = 0; t < island.Count; t++)
                {
                    long tk = island[t];
                    double den = densityMap[tk];
                    double vw  = volWeightMap[tk];
                    if (den > peakDensity || (Math.Abs(den - peakDensity) < 1e-4 && vw > maxVolW))
                    {
                        peakDensity = den;
                        maxVolW     = vw;
                        pocTk       = tk;
                    }
                }
                double pocPrice = pocTk * TickSize;

                // Calcular zonas contribuyentes, volumen semilla y CVD neto
                double seedVol = 0;
                double seedCvd = 0;
                int zCount = 0;
                int clusterStartBar = CurrentBars[0];

                for (int i = 0; i < pool.Count; i++)
                {
                    Zone z = pool[i];
                    double dLower = Math.Max(0.0, (cLower - z.Upper) / TickSize);
                    double dUpper = Math.Max(0.0, (z.Lower - cUpper) / TickSize);
                    double minDistance = Math.Max(dLower, dUpper);

                    if (minDistance <= (2.0 * HaloSigmaTicks))
                    {
                        seedVol += z.TotalVol;
                        seedCvd += z.Cvd;
                        zCount++;
                        clusterStartBar = Math.Min(clusterStartBar, z.StartBar);
                    }
                }

                // CONFLUENCIA REAL. Con peso continuo, MinClusterDensity deja de
                // significar "cuantas zonas": una zona con volumen >= MinClusterDensity
                // veces la mediana cruza el umbral ELLA SOLA, en los ticks de su propio
                // interior donde el gaussiano vale 1. Medido sobre una sesion de NQ: en
                // modo Conteo el 0% de los clusters tiene una sola zona; en Volumen, 8,7%.
                // Un cluster de una sola zona es trivialmente estable, asi que sin esta
                // compuerta la robustez medida podria ser degeneracion disfrazada.
                if (zCount < MinContributingZones) continue;

                double capacityVol = Math.Max(MinCapacityVolume, seedVol * CapacityMultiplier);

                // Determinar paleta según sesgo de flujo
                Brush fillCol, borderCol;
                if (seedCvd > (0.25 * seedVol))
                {
                    fillCol   = ColorClusterBull;
                    borderCol = ColorClusterBull;
                }
                else if (seedCvd < (-0.25 * seedVol))
                {
                    fillCol   = ColorClusterBear;
                    borderCol = ColorClusterBear;
                }
                else
                {
                    fillCol   = ColorClusterNeutral;
                    borderCol = ColorBordeCluster;
                }

                // Buscar si ya existe un cluster activo solapando este rango para expandirlo sin perder su historial
                Cluster matching = null;
                for (int ex = clusters.Count - 1; ex >= 0; ex--)
                {
                    Cluster prev = clusters[ex];
                    if (prev.State == HFTClusterState.Depleted || prev.State == HFTClusterState.Invalidated)
                        continue;

                    double ovLo = Math.Max(cLower, prev.Lower);
                    double ovHi = Math.Min(cUpper, prev.Upper);
                    if (ovHi >= ovLo)
                    {
                        matching = prev;
                        break;
                    }
                }

                if (matching != null)
                {
                    // Expansión / Re-evaluación de Cluster existente
                    matching.Lower                  = Math.Min(matching.Lower, cLower);
                    matching.Upper                  = Math.Max(matching.Upper, cUpper);
                    matching.PocPrice               = pocPrice;
                    matching.PeakDensity            = Math.Max(matching.PeakDensity, peakDensity);
                    matching.SeedVolume             = Math.Max(matching.SeedVolume, seedVol);
                    matching.CapacityVolume         = Math.Max(matching.CapacityVolume, capacityVol);
                    matching.ContributingZonesCount = Math.Max(matching.ContributingZonesCount, zCount);
                    matching.FillBrush              = fillCol;
                    matching.BorderBrush            = borderCol;
                    matching.EndBar                 = CurrentBars[0];
                    matching.EndTime                = Times[0][0];

                    LogClusterEvent("CLUSTER_EXPANDED", matching);
                }
                else
                {
                    // Creación de Nuevo Cluster
                    clusterCounter++;
                    string tag = "HFTCLUST_" + clusterCounter;

                    Cluster nc = new Cluster
                    {
                        Id                     = clusterCounter,
                        Tag                    = tag,
                        Lower                  = cLower,
                        Upper                  = cUpper,
                        PocPrice               = pocPrice,
                        StartBar               = clusterStartBar,
                        EndBar                 = CurrentBars[0],
                        StartTime              = Times[0][0],
                        EndTime                = Times[0][0],
                        PeakDensity            = peakDensity,
                        SeedVolume             = seedVol,
                        SeedCvd                = seedCvd,
                        CapacityVolume         = capacityVol,
                        VolumeInside           = 0,
                        DeltaInside            = 0,
                        TouchedPoc             = false,
                        State                  = HFTClusterState.Active,
                        ContributingZonesCount = zCount,
                        FillBrush              = fillCol,
                        BorderBrush            = borderCol,
                        LastDrawnVolume        = 0,
                        LastDrawnOpacity       = OpacidadCluster,
                        Drawn                  = false
                    };

                    clusters.Add(nc);
                    activeDrawTags.Add(tag);
                    activeDrawTags.Add(tag + "_POC");
                    activeDrawTags.Add(tag + "_T");

                    LogClusterEvent("CLUSTER_CREATED", nc);

                    if (clusters.Count > 300) clusters.RemoveAt(0);
                }
            }
        }

        // ===================== CONSUMO DE VOLUMEN Y MÁQUINA DE ESTADOS =====================
        private void ActualizarConsumoTick(double price, double vol, int side)
        {
            double invalMargin = InvalidationTicks * TickSize;

            for (int i = 0; i < clusters.Count; i++)
            {
                Cluster c = clusters[i];
                if (c.State == HFTClusterState.Depleted || c.State == HFTClusterState.Invalidated || c.State == HFTClusterState.Expired)
                    continue;

                // 1. Detección de Violación / Perforación violenta
                if (price > (c.Upper + invalMargin) || price < (c.Lower - invalMargin))
                {
                    // Si el precio atravesó violentamente sin haber agotado la capacidad
                    if (c.VolumeInside < (c.CapacityVolume * 0.8))
                    {
                        c.State = HFTClusterState.Invalidated;
                        LogClusterEvent("CLUSTER_INVALIDATED", c);
                        DibujarCluster(c);
                        continue;
                    }
                }

                // 2. Consumo Activo: el precio está cotizando dentro del cluster
                if (price >= c.Lower && price <= c.Upper)
                {
                    c.VolumeInside += vol;
                    c.DeltaInside  += (side * vol);

                    // Touch al POC
                    if (!c.TouchedPoc && Math.Abs(price - c.PocPrice) < (TickSize * 0.6))
                    {
                        c.TouchedPoc = true;
                        if (c.State == HFTClusterState.Active) c.State = HFTClusterState.TouchedPOC;
                        LogClusterEvent("CLUSTER_TOUCHED_POC", c);
                    }

                    // Chequeo de Agotamiento de Capacidad
                    double remainingRatio = Math.Max(0.0, 1.0 - (c.VolumeInside / c.CapacityVolume));

                    if (remainingRatio <= 0.0)
                    {
                        c.State = HFTClusterState.Depleted;
                        LogClusterEvent("CLUSTER_DEPLETED", c);
                        DibujarCluster(c);
                        continue;
                    }

                    // Refresco dinamico por delta de contratos.
                    //
                    // ESTE es el redibujo caro: se dispara cada RedrawVolumeThreshold
                    // contratos operados dentro del cluster, o sea muchas veces por
                    // cluster y por sesion. Durante el historico no aporta nada -- el
                    // desvanecimiento progresivo sólo se percibe en vivo -- y el estado
                    // final igual queda bien porque cada cambio de estado (agotado,
                    // invalidado, expirado) redibuja por su cuenta.
                    //
                    // Los dibujos de creacion, expansion y muerte NO se saltean: hacerlo
                    // dejaba el chart con un solo cluster, porque al diferirlos hasta
                    // tiempo real los clusters viejos exigen un barsAgo de miles de
                    // barras y el dibujo falla.
                    if (State == State.Realtime
                        && Math.Abs(c.VolumeInside - c.LastDrawnVolume) >= RedrawVolumeThreshold)
                    {
                        DibujarCluster(c);
                    }
                }
            }
        }

        private void VerificarExpiracionClusters()
        {
            int currentBar = CurrentBars[0];
            for (int i = 0; i < clusters.Count; i++)
            {
                Cluster c = clusters[i];
                if (c.State == HFTClusterState.Active || c.State == HFTClusterState.TouchedPOC)
                {
                    if (currentBar - c.StartBar > MaxClusterAgeBars)
                    {
                        c.State = HFTClusterState.Expired;
                        LogClusterEvent("CLUSTER_EXPIRED", c);
                        DibujarCluster(c);
                    }
                }
            }
        }

        // ===================== DIBUJO Y RENDERIZADO VISUAL =====================
        private void DibujarTodo(bool forceRedraw)
        {
            // Zonas individuales (si están habilitadas)
            if (DibujarZonasIndividuales)
            {
                for (int i = 0; i < zones.Count; i++)
                {
                    Zone z = zones[i];
                    if (z.Drawn && !forceRedraw) continue;
                    int barsAgoStart = CurrentBars[0] - z.StartBar;
                    int barsAgoEnd   = CurrentBars[0] - z.EndBar;
                    if (barsAgoStart < 0) continue;

                    Draw.Rectangle(this, z.TagRect, false,
                        barsAgoStart, z.Upper, -ExtensionDibujo, z.Lower,
                        Brushes.Transparent, z.ColorZ, OpacidadZonas);

                    if (MostrarTextoZonas)
                    {
                        double tY = z.Direction == 1 ? z.Lower - (TickSize * 4) : z.Upper + (TickSize * 4);
                        Draw.Text(this, z.TagText, z.Reporte, Math.Max(0, barsAgoEnd), tY, ColorTexto);
                    }
                    z.Drawn = true;
                }
            }

            // Clusters
            if (MostrarClusters)
            {
                for (int i = 0; i < clusters.Count; i++)
                {
                    DibujarCluster(clusters[i]);
                }
            }
        }

        private void DibujarCluster(Cluster c)
        {
            if (!MostrarClusters) return;

            // Manejo de Ocultamiento según estado
            if (c.State == HFTClusterState.Invalidated && OcultarInvalidados)
            {
                RemoverTagsCluster(c);
                return;
            }
            if (c.State == HFTClusterState.Depleted && OcultarAgotados)
            {
                RemoverTagsCluster(c);
                return;
            }

            int currentBar = CurrentBars[0];
            int startAgo = currentBar - c.StartBar;
            if (startAgo < 0) startAgo = 0;

            int endAgo = ProyectarAlFuturo ? -ExtensionDibujo : (currentBar - c.EndBar);

            // Calcular Opacidad en base a la Capacidad Remanente
            double remainingRatio = Math.Max(0.0, 1.0 - (c.VolumeInside / c.CapacityVolume));
            int effectiveOpacity;

            if (c.State == HFTClusterState.Depleted)
            {
                effectiveOpacity = Math.Min(6, OpacidadMinima);
            }
            else if (c.State == HFTClusterState.Invalidated)
            {
                effectiveOpacity = Math.Min(5, OpacidadMinima);
            }
            else
            {
                effectiveOpacity = (int)Math.Max(OpacidadMinima, OpacidadCluster * remainingRatio);
            }

            // Rectángulo principal del Cluster
            Draw.Rectangle(this, c.Tag, false,
                startAgo, c.Upper, endAgo, c.Lower,
                c.BorderBrush, c.FillBrush, effectiveOpacity);

            // Línea central de máxima atracción (POC)
            if (DibujarPocCluster)
            {
                Draw.Line(this, c.Tag + "_POC", false,
                    startAgo, c.PocPrice, endAgo, c.PocPrice,
                    c.BorderBrush, DashStyleHelper.Dash, 2);
            }

            // Etiqueta de Telemetría Dinámica
            if (MostrarTextoCluster)
            {
                string stateTxt;
                switch (c.State)
                {
                    case HFTClusterState.Depleted:    stateTxt = "DEPLETED (ABSORBIDO)"; break;
                    case HFTClusterState.Invalidated: stateTxt = "INVALIDATED"; break;
                    case HFTClusterState.TouchedPOC:  stateTxt = "TESTING POC"; break;
                    case HFTClusterState.Expired:     stateTxt = "EXPIRED"; break;
                    default:                          stateTxt = "ACTIVE"; break;
                }

                string txt = string.Format("★ CLUSTER [{0}] {1:F1}x | Cap:{2:P0} ({3:F0}/{4:F0}V) POC:{5:F2}",
                    stateTxt, c.PeakDensity, remainingRatio, c.VolumeInside, c.CapacityVolume, c.PocPrice);

                int textBar = Math.Max(0, startAgo);
                Draw.Text(this, c.Tag + "_T", txt, textBar, c.Upper + (TickSize * 3), c.BorderBrush);
            }

            c.LastDrawnVolume  = c.VolumeInside;
            c.LastDrawnOpacity = effectiveOpacity;
            c.Drawn            = true;
        }

        private void RemoverTagsCluster(Cluster c)
        {
            try { RemoveDrawObject(c.Tag); } catch { }
            try { RemoveDrawObject(c.Tag + "_POC"); } catch { }
            try { RemoveDrawObject(c.Tag + "_T"); } catch { }
        }

        private void LimpiarDibujos()
        {
            for (int i = 0; i < activeDrawTags.Count; i++)
            {
                try { RemoveDrawObject(activeDrawTags[i]); }
                catch { }
            }
            activeDrawTags.Clear();
        }

        // ===================== FLOW STREAM ACCUMULATOR =====================
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

        // ===================== LOGGING: EVENT STREAM (CSV) & SQLITE =====================
        private void SetupCsv()
        {
            try
            {
                string dir = Path.GetDirectoryName(EventLogPath);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                    Directory.CreateDirectory(dir);

                bool fileExists = File.Exists(EventLogPath);
                csvWriter = new StreamWriter(new FileStream(EventLogPath, FileMode.Append, FileAccess.Write, FileShare.ReadWrite));
                csvWriter.AutoFlush = true;

                // PROCEDENCIA: las lineas "#" se escriben SIEMPRE, no solo al crear el
                // archivo. El FileStream es Append y EventLogPath tiene un default fijo,
                // asi que una corrida nueva anexaba sus filas debajo del encabezado de
                // la corrida anterior -- con otra version y otros parametros, y sin
                // ninguna marca que permitiera separarlas. El archivo quedaba internamente
                // coherente y con procedencia falsa, que es la peor combinacion.
                // Empiezan con "#": un parser que saltea comentarios las tolera en el medio.
                csvWriter.WriteLine("# meta indicator=HFTClusterZonesNQ,version=1.1.0");
                csvWriter.WriteLine(string.Format("# params sigma={0},minDensity={1},capMult={2},invalTicks={3},peso={4},minTotalVol={5},maxAgeBars={6},lookback={7},minContrib={8},instrument={9}",
                    HaloSigmaTicks, MinClusterDensity, CapacityMultiplier, InvalidationTicks,
                    PesoZona, MinTotalVolume, MaxClusterAgeBars, ClusterLookbackZones,
                    MinContributingZones, Instrument.FullName));
                if (!fileExists)
                    csvWriter.WriteLine("timestamp,event,cluster_id,start_ts,end_ts,lower,upper,poc,peak_density,seed_vol,seed_cvd,cap_vol,vol_inside,delta_inside,remaining_cap_pct,state");
                csvReady = true;
            }
            catch (Exception ex)
            {
                csvReady = false;
                Print("[HFTCluster] SetupCsv: " + ex.Message);
            }
        }

        private void LogClusterEvent(string eventName, Cluster c)
        {
            // Durante el historico se procesan cientos de miles de ticks viejos; escribir
            // cada evento a disco ahi multiplica el tiempo de carga sin aportar nada que
            // no se pueda reproducir desde los parquets. En vivo se registra todo.
            if (SoloLogEnVivo && State != State.Realtime) return;
            double remCap = Math.Max(0.0, 1.0 - (c.VolumeInside / c.CapacityVolume));
            long nowTs = UnixMs(Times[0][0]);

            if (csvReady && csvWriter != null)
            {
                try
                {
                    csvWriter.WriteLine(string.Format("{0},{1},{2},{3},{4},{5:F2},{6:F2},{7:F2},{8:F2},{9:F0},{10:F0},{11:F0},{12:F0},{13:F0},{14:F3},{15}",
                        nowTs, eventName, c.Id, UnixMs(c.StartTime), UnixMs(c.EndTime),
                        c.Lower, c.Upper, c.PocPrice, c.PeakDensity,
                        c.SeedVolume, c.SeedCvd, c.CapacityVolume,
                        c.VolumeInside, c.DeltaInside, remCap, c.State));
                }
                catch { }
            }

            if (dbReady)
            {
                clusterBuf.Add(new object[] {
                    c.Id, Instrument.FullName, UnixMs(c.StartTime), UnixMs(c.EndTime),
                    c.Lower, c.Upper, c.PocPrice, c.PeakDensity,
                    c.SeedVolume, c.SeedCvd, c.CapacityVolume,
                    c.VolumeInside, c.DeltaInside, remCap, c.State.ToString(), eventName, nowTs
                });
                if (clusterBuf.Count >= BatchSize) FlushAll();
            }
        }

        private void CloseCsv()
        {
            try
            {
                if (csvWriter != null)
                {
                    csvWriter.Flush();
                    csvWriter.Close();
                    csvWriter.Dispose();
                    csvWriter = null;
                }
            }
            catch { }
            csvReady = false;
        }

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
                      CREATE INDEX IF NOT EXISTS idx_hf_ts ON hft_flow(instrument, bar_ts);

                      CREATE TABLE IF NOT EXISTS hft_clusters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, cluster_id INTEGER, instrument TEXT, start_ts INTEGER, end_ts INTEGER,
                        lower REAL, upper REAL, poc REAL, initial_density REAL, seed_volume REAL, seed_cvd REAL,
                        capacity_volume REAL, volume_inside REAL, delta_inside REAL, remaining_cap_pct REAL, state TEXT,
                        event TEXT, update_ts INTEGER);
                      CREATE INDEX IF NOT EXISTS idx_hc_ts ON hft_clusters(instrument, update_ts);", dbConn))
                    cmd.ExecuteNonQuery();

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

                clusterCmd = new SQLiteCommand(
                    @"INSERT INTO hft_clusters
                      (cluster_id,instrument,start_ts,end_ts,lower,upper,poc,initial_density,seed_volume,seed_cvd,capacity_volume,
                       volume_inside,delta_inside,remaining_cap_pct,state,event,update_ts)
                      VALUES (@cid,@inst,@s,@e,@lo,@up,@poc,@den,@sv,@sc,@cap,@vi,@di,@rem,@st,@ev,@up_ts)", dbConn);
                foreach (string p in new[]{"@cid","@inst","@s","@e","@lo","@up","@poc","@den","@sv","@sc","@cap","@vi","@di","@rem","@st","@ev","@up_ts"})
                    clusterCmd.Parameters.Add(new SQLiteParameter(p));
                clusterCmd.Prepare();

                dbReady = true;
                lastFlushMs = 0;
            }
            catch (Exception ex)
            {
                dbReady = false;
                Print("[HFTCluster] SetupDb: " + ex.Message);
            }
        }

        private void PersistZone(Zone z)
        {
            if (!dbReady) return;
            if (SoloLogEnVivo && State != State.Realtime) return;
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
            if (zoneBuf.Count == 0 && flowBuf.Count == 0 && clusterBuf.Count == 0) return;
            SQLiteTransaction tx = null;
            try
            {
                tx = dbConn.BeginTransaction();
                if (zoneCmd != null && zoneBuf.Count > 0)
                {
                    zoneCmd.Transaction = tx;
                    foreach (var r in zoneBuf)
                    {
                        for (int i = 0; i < r.Length; i++) zoneCmd.Parameters[i].Value = r[i];
                        zoneCmd.ExecuteNonQuery();
                    }
                }
                if (flowCmd != null && flowBuf.Count > 0)
                {
                    flowCmd.Transaction = tx;
                    foreach (var r in flowBuf)
                    {
                        for (int i = 0; i < r.Length; i++) flowCmd.Parameters[i].Value = r[i];
                        flowCmd.ExecuteNonQuery();
                    }
                }
                if (clusterCmd != null && clusterBuf.Count > 0)
                {
                    clusterCmd.Transaction = tx;
                    foreach (var r in clusterBuf)
                    {
                        for (int i = 0; i < r.Length; i++) clusterCmd.Parameters[i].Value = r[i];
                        clusterCmd.ExecuteNonQuery();
                    }
                }
                tx.Commit();
                zoneBuf.Clear(); flowBuf.Clear(); clusterBuf.Clear();
                lastFlushMs = flowStartMs;
            }
            catch (Exception ex)
            {
                try { if (tx != null) tx.Rollback(); } catch { }
                Print("[HFTCluster] FlushAll: " + ex.Message);
                if (zoneBuf.Count + flowBuf.Count + clusterBuf.Count > MaxBuf)
                {
                    zoneBuf.Clear(); flowBuf.Clear(); clusterBuf.Clear();
                }
            }
        }

        private void CloseDb()
        {
            try
            {
                if (EnableFlowLog && fTicks > 0) BufferFlow();
                FlushAll();
                if (clusterCmd != null) { clusterCmd.Dispose(); clusterCmd = null; }
                if (flowCmd != null)    { flowCmd.Dispose();    flowCmd = null; }
                if (zoneCmd != null)    { zoneCmd.Dispose();    zoneCmd = null; }
                if (dbConn != null)     { dbConn.Close();       dbConn.Dispose(); dbConn = null; }
            }
            catch (Exception ex) { Print("[HFTCluster] CloseDb: " + ex.Message); }
            dbReady = false;
        }

        private static long UnixMs(DateTime dt)
        {
            return new DateTimeOffset(dt.ToUniversalTime()).ToUnixTimeMilliseconds();
        }

        #region Properties
        // 0. Sub-serie
        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Tick Resolution (sub-serie)", Order=1, GroupName="0. Sub-serie", Description="NQ: 1.")]
        public int TickResolution { get; set; }

        // A. Estructura Sweeps
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

        // B. Filtros temporales
        [NinjaScriptProperty][Range(1, 2000)]
        [Display(Name="Max avgMs (entre ticks)", Order=1, GroupName="B. Filtros temporales", Description="NQ: 20-40ms.")]
        public int MaxAvgMs { get; set; }

        [NinjaScriptProperty][Range(50, 10000)]
        [Display(Name="Max totalMs (duracion total)", Order=2, GroupName="B. Filtros temporales", Description="NQ: 300-800ms.")]
        public int MaxTotalMs { get; set; }

        [NinjaScriptProperty][Range(10, 5000)]
        [Display(Name="Max pausa entre ticks (ms)", Order=3, GroupName="B. Filtros temporales", Description="NQ: 80-150ms.")]
        public int MaxPausaMs { get; set; }

        // C. Filtros volumen
        [NinjaScriptProperty][Range(0, 50000)]
        [Display(Name="Min velocidad volumen (contratos/seg)", Order=1, GroupName="C. Filtros volumen", Description="NQ: 50-200.")]
        public int MinVolumeRate { get; set; }

        [NinjaScriptProperty][Range(0, 100000)]
        [Display(Name="Min volumen total (contratos)", Order=2, GroupName="C. Filtros volumen", Description="NQ: 30-100.")]
        public int MinTotalVolume { get; set; }

        // D. Buckets
        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Bucket PREDATOR avgMs <=", Order=1, GroupName="D. Buckets")]
        public int PredatorAvgMs { get; set; }

        [NinjaScriptProperty][Range(1, 200)]
        [Display(Name="Bucket ULTRA avgMs <=", Order=2, GroupName="D. Buckets")]
        public int UltraAvgMs { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar zonas ABSORB", Order=3, GroupName="D. Buckets")]
        public bool MostrarAbsorb { get; set; }

        [NinjaScriptProperty][Range(2, 100)]
        [Display(Name="Min pasos ABSORB", Order=4, GroupName="D. Buckets", Description="NQ: 6.")]
        public int MinAbsorbPasos { get; set; }

        // E. Visual Zonas Individuales
        [NinjaScriptProperty]
        [Display(Name="Dibujar Zonas Individuales", Order=1, GroupName="E. Visual Zonas", Description="Si es false, oculta rectángulos individuales para mantener chart limpio enfocado en clusters.")]
        public bool DibujarZonasIndividuales { get; set; }

        [NinjaScriptProperty][Range(1, 5000)]
        [Display(Name="Extension dibujo zonas (barras)", Order=2, GroupName="E. Visual Zonas")]
        public int ExtensionDibujo { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Opacidad zonas individuales", Order=3, GroupName="E. Visual Zonas")]
        public int OpacidadZonas { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar texto en zonas", Order=4, GroupName="E. Visual Zonas")]
        public bool MostrarTextoZonas { get; set; }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color PREDATOR", Order=5, GroupName="E. Visual Zonas")]
        public Brush ColorPredator { get; set; }
        [Browsable(false)] public string ColorPredatorSerializable
        { get { return Serialize.BrushToString(ColorPredator); } set { ColorPredator = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ULTRA", Order=6, GroupName="E. Visual Zonas")]
        public Brush ColorUltra { get; set; }
        [Browsable(false)] public string ColorUltraSerializable
        { get { return Serialize.BrushToString(ColorUltra); } set { ColorUltra = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color bull (Fast)", Order=7, GroupName="E. Visual Zonas")]
        public Brush ColorBull { get; set; }
        [Browsable(false)] public string ColorBullSerializable
        { get { return Serialize.BrushToString(ColorBull); } set { ColorBull = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color bear (Fast)", Order=8, GroupName="E. Visual Zonas")]
        public Brush ColorBear { get; set; }
        [Browsable(false)] public string ColorBearSerializable
        { get { return Serialize.BrushToString(ColorBear); } set { ColorBear = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ABSORB", Order=9, GroupName="E. Visual Zonas")]
        public Brush ColorAbsorb { get; set; }
        [Browsable(false)] public string ColorAbsorbSerializable
        { get { return Serialize.BrushToString(ColorAbsorb); } set { ColorAbsorb = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color texto zonas", Order=10, GroupName="E. Visual Zonas")]
        public Brush ColorTexto { get; set; }
        [Browsable(false)] public string ColorTextoSerializable
        { get { return Serialize.BrushToString(ColorTexto); } set { ColorTexto = Serialize.StringToBrush(value); } }

        // H. Clusters: Kernel de Proximidad & Halo
        [NinjaScriptProperty]
        [Display(Name="Mostrar Clusters Gravitacionales", Order=1, GroupName="H. Clusters Gravitacionales")]
        public bool MostrarClusters { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Peso de zona en el campo", Order=1, GroupName="H. Clusters Gravitacionales",
            Description="Conteo = original (cada zona vale 1). Volumen = pondera por volumen: mucho mas estable ante ruido. Ver docs/research/PREREGISTRO_H-CLUSTER-NQ.")]
        public HFTPesoZona PesoZona { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Loguear solo en vivo", Order=3, GroupName="K. Database & Logs",
            Description="Saltea la escritura a SQLite y CSV mientras se procesan barras historicas. Reduce mucho el tiempo de carga del chart.")]
        public bool SoloLogEnVivo { get; set; }

        [NinjaScriptProperty][Range(1, 50)]
        [Display(Name="Min zonas contribuyentes", Order=2, GroupName="H. Clusters Gravitacionales",
            Description="Confluencia minima real. Con peso por volumen, una sola zona grande puede cruzar el umbral de densidad; esto lo impide.")]
        public int MinContributingZones { get; set; }

        [NinjaScriptProperty][Range(0.5, 20.0)]
        [Display(Name="Halo Sigma (ticks)", Order=2, GroupName="H. Clusters Gravitacionales", Description="Ancho de banda del kernel gaussiano de influencia continua. Default 3.0.")]
        public double HaloSigmaTicks { get; set; }

        [NinjaScriptProperty][Range(1.0, 20.0)]
        [Display(Name="Densidad minima de cluster", Order=3, GroupName="H. Clusters Gravitacionales", Description="Densidad acumulada de halo requerida para disparar un cluster. Default 3.0.")]
        public double MinClusterDensity { get; set; }

        [NinjaScriptProperty][Range(10, 500)]
        [Display(Name="Lookback zonas para halo", Order=4, GroupName="H. Clusters Gravitacionales", Description="Cantidad de zonas HFT recientes evaluadas en el campo gravitacional.")]
        public int ClusterLookbackZones { get; set; }

        [NinjaScriptProperty][Range(50, 5000)]
        [Display(Name="Edad maxima cluster (barras)", Order=5, GroupName="H. Clusters Gravitacionales", Description="Barras máximas antes de que un cluster inactivo pase a estado Expired.")]
        public int MaxClusterAgeBars { get; set; }

        // I. Consumo y Desgaste Dinámico
        [NinjaScriptProperty]
        [Display(Name="Activar Consumo por Volumen", Order=1, GroupName="I. Consumo y Desgaste", Description="El cluster pierde opacidad progresivamente con cada contrato negociado en su interior.")]
        public bool ActivarConsumoVolumen { get; set; }

        [NinjaScriptProperty][Range(100, 100000)]
        [Display(Name="Capacidad minima (contratos)", Order=2, GroupName="I. Consumo y Desgaste", Description="Volumen base necesario dentro del cluster para agotarlo por completo. Default 1200.")]
        public double MinCapacityVolume { get; set; }

        [NinjaScriptProperty][Range(0.5, 10.0)]
        [Display(Name="Multiplicador de Capacidad", Order=3, GroupName="I. Consumo y Desgaste", Description="Multiplicador sobre el volumen semilla original. Default 2.5.")]
        public double CapacityMultiplier { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Ticks de Invalidacion (Perforacion)", Order=4, GroupName="I. Consumo y Desgaste", Description="Excursión adversa violenta más allá del cluster que lo marca como Invalidated.")]
        public int InvalidationTicks { get; set; }

        [NinjaScriptProperty][Range(10, 1000)]
        [Display(Name="Umbral Redibujo Volumen (contratos)", Order=5, GroupName="I. Consumo y Desgaste", Description="Redibuja el fading en tiempo real cada N contratos consumidos para optimizar CPU.")]
        public int RedrawVolumeThreshold { get; set; }

        // J. Visual Clusters
        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Opacidad inicial cluster", Order=1, GroupName="J. Visual Clusters")]
        public int OpacidadCluster { get; set; }

        [NinjaScriptProperty][Range(1, 50)]
        [Display(Name="Opacidad minima (remanente)", Order=2, GroupName="J. Visual Clusters")]
        public int OpacidadMinima { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Proyectar al futuro", Order=3, GroupName="J. Visual Clusters", Description="Extiende el rectángulo hacia adelante para facilitar visualización de niveles.")]
        public bool ProyectarAlFuturo { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar texto telemetria", Order=4, GroupName="J. Visual Clusters")]
        public bool MostrarTextoCluster { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Dibujar linea central POC", Order=5, GroupName="J. Visual Clusters")]
        public bool DibujarPocCluster { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Ocultar clusters agotados", Order=6, GroupName="J. Visual Clusters", Description="Si es false, permanecen como huella grisácea sutil al 8% de opacidad.")]
        public bool OcultarAgotados { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Ocultar clusters invalidados", Order=7, GroupName="J. Visual Clusters")]
        public bool OcultarInvalidados { get; set; }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color cluster Neutral (Absorb/Mix)", Order=8, GroupName="J. Visual Clusters")]
        public Brush ColorClusterNeutral { get; set; }
        [Browsable(false)] public string ColorClusterNeutralSerializable
        { get { return Serialize.BrushToString(ColorClusterNeutral); } set { ColorClusterNeutral = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color cluster Bull", Order=9, GroupName="J. Visual Clusters")]
        public Brush ColorClusterBull { get; set; }
        [Browsable(false)] public string ColorClusterBullSerializable
        { get { return Serialize.BrushToString(ColorClusterBull); } set { ColorClusterBull = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color cluster Bear", Order=10, GroupName="J. Visual Clusters")]
        public Brush ColorClusterBear { get; set; }
        [Browsable(false)] public string ColorClusterBearSerializable
        { get { return Serialize.BrushToString(ColorClusterBear); } set { ColorClusterBear = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color borde cluster", Order=11, GroupName="J. Visual Clusters")]
        public Brush ColorBordeCluster { get; set; }
        [Browsable(false)] public string ColorBordeClusterSerializable
        { get { return Serialize.BrushToString(ColorBordeCluster); } set { ColorBordeCluster = Serialize.StringToBrush(value); } }

        // K. Logging
        [NinjaScriptProperty]
        [Display(Name="Enable DB Logging", Order=1, GroupName="K. Database & Logs")]
        public bool EnableDbLogging { get; set; }

        [NinjaScriptProperty]
        [Display(Name="DB Path (SQLite)", Order=2, GroupName="K. Database & Logs")]
        public string DbPath { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Enable Event CSV Log", Order=3, GroupName="K. Database & Logs")]
        public bool EnableEventCsv { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Event CSV Path", Order=4, GroupName="K. Database & Logs")]
        public string EventLogPath { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Enable Flow Log", Order=5, GroupName="K. Database & Logs")]
        public bool EnableFlowLog { get; set; }

        [NinjaScriptProperty][Range(1, 60)]
        [Display(Name="Flow Bucket Seconds", Order=6, GroupName="K. Database & Logs")]
        public int FlowBucketSeconds { get; set; }
        #endregion
    }
}
