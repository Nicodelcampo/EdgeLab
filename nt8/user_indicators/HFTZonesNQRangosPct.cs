// # meta indicator=HFTZonesNQRangosPctV2,version=2.0.0
// HFTZonesNQRangosPctV2.cs (2026-11-09, pedido de Nico)
// Rediseño 100% CAUSAL (sin look-ahead), con renderizado nativo SharpDX (OnRender) en todo el histórico:
//   1. SIN LOOK-AHEAD:
//      - Cada zona HFT se empieza a dibujar en z.DetectBar (la barra primaria exacta donde Finalizar() confirmó el sweep),
//        nunca en StartBar antes de que terminara el impulso.
//      - Cada CLUSTER HFT y cada EXPANSION SIN HFT nace en su DetectBar (el punto exacto de detección causal) y se proyecta
//        hacia adelante. Si una expansión sigue creciendo en barras posteriores, escalona desde la barra nueva sin alterar el pasado.
//   2. DETECCIÓN MEJORADA DE EVENTOS INFRECUENTES (normalizada por volatilidad + frecuencia objetivo por sesión):
//      - Clusters HFT: evalúa compacidad normalizada por escala de volatilidad causal, empaquetamiento real (solapamiento),
//        cantidad de zonas y volumen ponderado (con línea POC interna), desduplicando eventos sobre el mismo cluster activo.
//      - Expansiones sin HFT: rastrea impulsos direccionales causales y mide el mayor corredor libre de zonas HFT activas,
//        ponderado por eficiencia direccional (desplazamiento neto / recorrido bruto) y normalizado por volatilidad.
//   3. SCROLLBACK COMPLETO EN TODO EL GRÁFICO:
//      - Renderizado por SharpDX (OnRender) sobre la ventana visible [ChartBars.FromIndex, ChartBars.ToIndex]: al ir hacia atrás
//        en cualquier timeframe (incluso 5 ticks con decenas de miles de barras), todas las zonas HFT, clusters y expansiones
//        se siguen dibujando instantáneamente sin degradar el rendimiento.
//   4. ESTÉTICA LIMPIA Y NO MOLESTA:
//      - Rellenos translúcidos suaves, marcador vertical nítido en el punto exacto de detección (DetectBar), bordes finos de 1px,
//        línea punteada de POC en clusters y de 50% en expansiones, y etiquetas compactas DirectWrite opcionales.

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
    public class HFTZonesNQRangosPct : Indicator
    {
        public enum HFTBucket { Predator, Ultra, Fast, Absorb }

        public sealed class Zone
        {
            public int       StartBar, EndBar, DetectBar, VisualEndBar;
            public DateTime  StartTime, EndTime, DetectTime;
            public double    Upper, Lower;
            public int       Direction;
            public HFTBucket Bucket;
            public double    AvgMs, TotalMs, VolRate;
            public int       Pasos, ValidSteps;
            public double    TotalVol;
            public double    MaxRetro;
            public double    MaxTickVol;
            public double    Cvd, BuyVol, SellVol;
            public double    DeltaSlope, DeltaFirst, DeltaSecond;
            public int       NoMoveTicks, MaxLevelTicks;
            public double    NoMoveVol;
            public double    HeightTicks;
            public string    Reporte;
            public string    TerminationReason;
        }

        public sealed class CausalCluster
        {
            public double Lower;
            public double Upper;
            public double PocPrice;
            public int    DetectBar;
            public int    VisualEndBar;
            public int    ZoneCount;
            public double WidthTicks;
            public double Score;
            public string Label;
        }

        public sealed class CausalExpansion
        {
            public double Lower;
            public double Upper;
            public double MidPrice;
            public int    DetectBar;
            public int    VisualEndBar;
            public int    Direction;
            public double HeightTicks;
            public double Efficiency;
            public int    LegId;
            public string Label;
        }

        // ===== Sincronización OnBarUpdate <-> OnRender =====
        private readonly object syncRoot = new object();

        // ===== V2 Rigorous Parity & Lineage Fields =====
        public bool EnableTickLog { get; set; }

        private long   currentTickSeq = 0;
        private int    currentZoneSeq = 0;
        private long   zoneStartTickSeq = 0;
        private long   zoneEndTickSeq = 0;
        private string currentSessionId = "";
        private DateTime currentSessionDate = DateTime.MinValue;
        private string contractStr = "";

        private const string SOURCE_SHA256 = "841cdbcccbe54ca525e20456d38d1ece0beec5fdd7b820de980bbb01acebeb63";
        private const string PARAMETER_MANIFEST_SHA256 = "0fa994533b03d47a0fb615c3fd4478e91de8c05958eb33bb4004308faaba78a1";

        private SQLiteCommand tickCmd;
        private readonly List<object[]> tickBuf = new List<object[]>();

        private int      streak, validSteps, dir, fails;
        private int      startPrimBar, lastPrimBar;
        private double   swH, swL;
        private double   extremo, maxRetroceso;
        private double   totalMs;
        private int      msCount;
        private readonly List<double> priceList = new List<double>();
        private readonly List<double> volList   = new List<double>();
        private readonly List<double> signList  = new List<double>();
        private double   totalVol;
        private DateTime tStart, tLast;
        private DateTime prevTickTime = DateTime.MinValue;
        private double   prevTickClose = 0;
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

        private readonly List<Zone>            zones         = new List<Zone>();
        private readonly List<CausalCluster>   clustersPct   = new List<CausalCluster>();
        private readonly List<CausalExpansion> expansionsPct = new List<CausalExpansion>();

        public IReadOnlyList<Zone> PublicZones { get { return zones; } }

        public bool EnableFlowLog     { get; set; }
        public int  FlowBucketSeconds { get; set; }

        // ===== Estado causal de volatilidad, clusters y expansiones =====
        private int      primeraSinEvaluar;
        private int      sesionesVistas;
        private DateTime ultimaFechaSesion = DateTime.MinValue;
        private double   escalaVolTicks = 12.0;
        private double   escalaVolZonaMean = 40.0;

        private const int MaxHistoriaEventos = 600;
        private readonly List<double> histScoreCluster = new List<double>(MaxHistoriaEventos + 4);
        private readonly List<double> histScoreExp     = new List<double>(MaxHistoriaEventos + 4);
        private readonly List<double> sortScratch      = new List<double>(MaxHistoriaEventos + 4);
        private readonly List<Zone>   vivasBuf         = new List<Zone>(64);
        private double cachedUmbralExp = double.MaxValue;
        private bool   umbralExpDirty  = true;

        // Seguimiento causal de piernas (impulsos) para Expansiones sin HFT
        private int    impDir;
        private int    impStartBar, impExtBar, impLegId;
        private double impStartPrice, impExtPrice, impSumRange;
        private double impBestScoreRegistrado;
        private double impLastTriggeredHeightTicks;
        private CausalExpansion impActiveExpansion;

        // ===== Recursos SharpDX para OnRender =====
        private SharpDX.Direct2D1.Brush dxBullFill, dxBearFill, dxPredFill, dxUltraFill, dxAbsorbFill;
        private SharpDX.Direct2D1.Brush dxBullEdge, dxBearEdge, dxPredEdge, dxUltraEdge, dxAbsorbEdge;
        private SharpDX.Direct2D1.Brush dxClusterFill, dxClusterBorder, dxClusterAccent, dxClusterText;
        private SharpDX.Direct2D1.Brush dxExpFill, dxExpBorder, dxExpAccent, dxExpText;
        private SharpDX.Direct2D1.Brush dxLabelBg;
        private SharpDX.Direct2D1.StrokeStyle dxDashStyle;
        private SharpDX.DirectWrite.TextFormat dwFontSmall;
        private bool dxReady = false;

        public override string DisplayName
        {
            get { return Name; }
        }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description              = "Detector HFT NQ/MNQ V2 Causal (sin look-ahead): zonas, clusters HFT y expansiones sin HFT dibujadas desde su punto exacto de detección con SharpDX en todo el histórico.";
                Name                     = "HFTZonesNQRangosPct";
                Calculate                = Calculate.OnBarClose;
                IsOverlay                = true;
                DisplayInDataBox         = false;
                DrawOnPricePanel         = true;
                PaintPriceMarkers        = false;
                IsSuspendedWhileInactive = true;

                // Parámetros de eventos infrecuentes (Clusters y Expansiones)
                MostrarRangosPct   = true;
                MostrarZonasBase   = true;
                MinZonasCluster    = 4;
                PctAngosto         = 10;
                ClustersPorSesion  = 1.5;
                PctAmplio          = 5;
                ExpPorSesion       = 1.2;
                MinExpTicks        = 24;
                ZigZagTicks        = 40;
                PctMinHistoria     = 25;
                PctExtensionBars   = 300;
                OpacidadPct        = 22;
                ColorClusterPct    = Brushes.DarkOrange;
                ColorVacioPct      = Brushes.DeepSkyBlue;
                MostrarTextoPct    = true;

                // Parámetros del motor HFT
                TickResolution          = 1;
                MinPasos                = 8;
                MaxRangoTickPorVela     = 1;
                FallosTolerados         = 1;
                FiltroDireccionEstricto = true;
                MinSweepTicks           = 4;
                MaxRetrocesoTicks       = 2;
                RetrocesoPctHeight      = 50;
                MaxAvgMs                = 25;
                MaxTotalMs              = 500;
                MaxPausaMs              = 100;
                MinVolumeRate           = 100;
                MinTotalVolume          = 50;
                PredatorAvgMs           = 5;
                UltraAvgMs              = 15;
                MostrarAbsorb           = true;
                MinAbsorbPasos          = 6;
                ColorAbsorb             = Brushes.MediumPurple;
                ExtensionDibujo         = 400;
                Opacidad                = 12;
                MostrarTexto            = false;
                VelasDibujoHistorico    = 500000;
                ColorPredator           = Brushes.Gold;
                ColorUltra              = Brushes.Silver;
                ColorBull               = Brushes.DodgerBlue;
                ColorBear               = Brushes.Tomato;
                ColorTexto              = Brushes.Silver;

                EnableDbLogging         = false;
                EnableTickLog           = false;
                DbPath                  = @"E:\EdgeLab\data\nt8_oracles\hft_zones_nq_v2.sqlite";
                EnableFlowLog           = false;
                FlowBucketSeconds       = 1;
                ModoExportacionPuro     = false;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, TickResolution);
            }
            else if (State == State.DataLoaded)
            {
                lock (syncRoot)
                {
                    ResetState();
                    zones.Clear();
                    clustersPct.Clear();
                    expansionsPct.Clear();
                    histScoreCluster.Clear();
                    histScoreExp.Clear();
                }
                contractStr = (Instrument != null && Instrument.MasterInstrument != null)
                    ? (Instrument.MasterInstrument.Name + " " + Instrument.Expiry.ToString("MM-yy"))
                    : "NQ DEC26";
                currentSessionId = "";
                currentSessionDate = DateTime.MinValue;
                currentTickSeq = 0;
                currentZoneSeq = 0;
                zoneStartTickSeq = 0;
                zoneEndTickSeq = 0;
                tickBuf.Clear();
                prevTickTime = DateTime.MinValue;
                prevTickClose = 0;
                lastSide = 0;
                flowBucket = long.MinValue;
                fTicks = 0;
                primeraSinEvaluar = 0;
                sesionesVistas = 0;
                ultimaFechaSesion = DateTime.MinValue;
                escalaVolTicks = 24.0;
                escalaVolZonaMean = 40.0;
                cachedUmbralExp = double.MaxValue;
                umbralExpDirty = true;

                impDir = 0;
                impStartBar = 0;
                impExtBar = 0;
                impLegId = 0;
                impStartPrice = 0;
                impExtPrice = 0;
                impSumRange = 0;
                impBestScoreRegistrado = 0;
                impLastTriggeredHeightTicks = 0;
                impActiveExpansion = null;

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
                DisposeDxResources();
            }
        }

        private static long UnixNs(DateTime dt)
        {
            DateTime epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            return (dt.ToUniversalTime().Ticks - epoch.Ticks) * 100;
        }

        private void CheckSessionBoundary(DateTime tickTime)
        {
            DateTime d = tickTime.Date;
            if (d != currentSessionDate)
            {
                if (dir != 0 && streak > 0)
                {
                    Finalizar("END_OF_SESSION");
                }
                currentSessionDate = d;
                currentSessionId = EnableDbLogging ? d.ToString("yyyyMMdd") : "";
                currentTickSeq = 0;
                currentZoneSeq = 0;
                hasLoggedFlushError = false;
                ResetState();
            }
        }

        private void ResetState()
        {
            streak = 0; validSteps = 0; dir = 0; fails = 0;
            totalMs = 0; msCount = 0;
            if (EnableDbLogging)
            {
                priceList.Clear(); volList.Clear(); signList.Clear();
            }
            totalVol = 0;
            extremo = 0; maxRetroceso = 0;
            zoneStartTickSeq = 0;
            zoneEndTickSeq = 0;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress == 1)
            {
                if (CurrentBars[1] < 5) return;
                ProcesarSweeps();
                return;
            }
            if (BarsInProgress != 0) return;
            if (CurrentBars[0] < 2) return;

            // Actualizar escala de volatilidad causal con el rango de la vela primaria
            double barRangeTicks = (Highs[0][0] - Lows[0][0]) / TickSize;
            if (barRangeTicks > 0)
            {
                // Escala equivalente a un impulso corto (~4 velas), piso de 16 ticks (4 puntos NQ)
                double targetScale = Math.Max(16.0, barRangeTicks * 2.5);
                escalaVolTicks = 0.98 * escalaVolTicks + 0.02 * targetScale;
            }

            if (Times[0][0].Date != ultimaFechaSesion)
            {
                RegistrarPiernaEnHistoria();
                ultimaFechaSesion = Times[0][0].Date;
                sesionesVistas++;
                impDir = 0;
                impStartBar = CurrentBars[0];
                impExtBar = CurrentBars[0];
                impStartPrice = Closes[0][0];
                impExtPrice = Closes[0][0];
                impSumRange = 0;
                impBestScoreRegistrado = 0;
                impLastTriggeredHeightTicks = 0;
                impActiveExpansion = null;
            }

            if (MostrarRangosPct)
            {
                // 1) Evaluar cada zona HFT recién detectada como posible Cluster HFT causal
                //    y cortar el impulso libre de HFT si una zona nueva aparece en la frontera del movimiento
                while (primeraSinEvaluar < zones.Count)
                {
                    Zone z = zones[primeraSinEvaluar];
                    // Asegurar que la zona nunca tenga DetectBar posterior a la barra actual primaria
                    if (z.DetectBar > CurrentBars[0]) break;
                    primeraSinEvaluar++;
                    escalaVolZonaMean = 0.96 * escalaVolZonaMean + 0.04 * Math.Max(20.0, z.TotalVol);
                    EvaluarClusterCausal(primeraSinEvaluar - 1);
                    NotificarZonaNuevaEnImpulso(z);
                }

                // 2) Evaluar en tiempo real el impulso actual para detectar Expansiones sin HFT en el punto exacto
                ActualizarImpulsoYExpansionCausal();
            }
        }

        // ===================== MOTOR DE DETECCIÓN DE ZONAS HFT (1-TICK) =====================
        private void ProcesarSweeps()
        {
            const int ds = 1;
            DateTime tickTime = Times[ds][0];
            double cl  = Closes[ds][0];
            double vol = Volumes[ds][0];

            if (prevTickTime == DateTime.MinValue)
            {
                prevTickTime = tickTime;
                prevTickClose = cl;
                currentSessionDate = tickTime.Date;
                if (EnableDbLogging) currentSessionId = currentSessionDate.ToString("yyyyMMdd");
                return;
            }

            if (tickTime.Date != currentSessionDate)
            {
                CheckSessionBoundary(tickTime);
            }
            currentTickSeq++;

            if (EnableTickLog && dbReady)
            {
                long tsNs = UnixNs(tickTime);
                long pTicks = (long)Math.Round(cl / TickSize);
                double curBid = 0, curAsk = 0;
                try { curBid = GetCurrentBid(ds); } catch { }
                try { curAsk = GetCurrentAsk(ds); } catch { }
                long bTicks = curBid > 0 ? (long)Math.Round(curBid / TickSize) : 0;
                long aTicks = curAsk > 0 ? (long)Math.Round(curAsk / TickSize) : 0;
                tickBuf.Add(new object[] {
                    Instrument.FullName, contractStr, currentSessionId, currentTickSeq,
                    tsNs, pTicks, vol, bTicks, aTicks
                });
                if (tickBuf.Count >= 2000)
                    FlushAll();
            }

            double ms  = (tickTime.Ticks - prevTickTime.Ticks) * 0.0001;
            double clP = prevTickClose;
            prevTickTime  = tickTime;
            prevTickClose = cl;

            double hi, lo, op;
            bool small;
            if (TickResolution <= 1)
            {
                hi = cl; lo = cl; op = cl;
                small = true;
            }
            else
            {
                hi = Highs[ds][0];
                lo = Lows[ds][0];
                op = Opens[ds][0];
                small = (hi - lo) <= MaxRangoTickPorVela * TickSize;
            }

            int side = cl > clP ? 1 : (cl < clP ? -1 : lastSide);
            if (side == 0) side = 1;
            lastSide = side;
            double signedVol = side * vol;

            if (EnableFlowLog) AccumFlow(tickTime, cl, vol, side);

            bool isDown, isUp;
            if (TickResolution <= 1 || !FiltroDireccionEstricto)
            {
                isDown = small && cl <= clP;
                isUp   = small && cl >= clP;
            }
            else
            {
                isDown = small && cl <= clP && cl <= op;
                isUp   = small && cl >= clP && cl >= op;
            }

            if (dir != 0 && ms > MaxPausaMs)
            {
                Finalizar("MAX_PAUSE", tickTime);
                dir = 0;
                return;
            }

            if (dir == 0)
            {
                if (isDown)    { dir = -1; Iniciar(tickTime, hi, lo, cl, vol, signedVol); }
                else if (isUp) { dir =  1; Iniciar(tickTime, hi, lo, cl, vol, signedVol); }
            }
            else if (dir == -1)
            {
                if (isDown) { Continuar(tickTime, hi, lo, cl, ms, vol, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    double currentRetracement = (cl - extremo) / TickSize;
                    double sweepHeight = (swH - swL) / TickSize;
                    double maxAllowedRetracement = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepHeight);

                    if (currentRetracement <= maxAllowedRetracement)
                    {
                        Continuar(tickTime, hi, lo, cl, ms, vol, signedVol, false);
                    }
                    else
                    {
                        Finalizar("REVERSAL", tickTime);
                        if (isUp) { dir = 1; Iniciar(tickTime, hi, lo, cl, vol, signedVol); }
                        else        dir = 0;
                    }
                }
            }
            else
            {
                if (isUp) { Continuar(tickTime, hi, lo, cl, ms, vol, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    double currentRetracement = (extremo - cl) / TickSize;
                    double sweepHeight = (swH - swL) / TickSize;
                    double maxAllowedRetracement = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepHeight);

                    if (currentRetracement <= maxAllowedRetracement)
                    {
                        Continuar(tickTime, hi, lo, cl, ms, vol, signedVol, false);
                    }
                    else
                    {
                        Finalizar("REVERSAL", tickTime);
                        if (isDown) { dir = -1; Iniciar(tickTime, hi, lo, cl, vol, signedVol); }
                        else          dir = 0;
                    }
                }
            }
        }

        private void Iniciar(DateTime tickTime, double hi, double lo, double cl, double vol, double signedVol)
        {
            streak = 1; validSteps = 1; fails = 0;
            swH = hi; swL = lo;
            extremo = cl;
            maxRetroceso = 0;
            totalMs = 0;
            msCount = 0;
            if (EnableDbLogging)
            {
                priceList.Clear(); volList.Clear(); signList.Clear();
                priceList.Add(cl); volList.Add(vol); signList.Add(signedVol);
            }
            totalVol = vol;
            tStart = tickTime;
            tLast  = tickTime;
            int pBar = CurrentBars[0] >= 0 ? CurrentBars[0] : 0;
            startPrimBar = pBar;
            lastPrimBar  = pBar;
            zoneStartTickSeq = currentTickSeq;
            zoneEndTickSeq   = currentTickSeq;
        }

        private void Continuar(DateTime tickTime, double hi, double lo, double clC, double ms, double vol, double signedVol, bool valid)
        {
            streak++;
            if (valid) validSteps++;
            if (hi > swH) swH = hi;
            if (lo < swL) swL = lo;

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

            totalMs += ms;
            msCount++;
            if (EnableDbLogging)
            {
                priceList.Add(clC); volList.Add(vol); signList.Add(signedVol);
            }
            totalVol += vol;
            tLast = tickTime;
            if (CurrentBars[0] >= 0) lastPrimBar = CurrentBars[0];
            zoneEndTickSeq = currentTickSeq;
        }

        private void Finalizar(string reason = "REVERSAL", DateTime detectTickTime = default(DateTime))
        {
            double sweepTicks = (swH - swL) / TickSize;
            bool isSweep  = sweepTicks >= MinSweepTicks;
            bool isAbsorb = !isSweep && MostrarAbsorb;
            int minPasosReq = isSweep ? MinPasos : MinAbsorbPasos;

            if (validSteps >= minPasosReq && (isSweep || isAbsorb))
            {
                double total = totalMs;
                int    nIntervals = msCount;
                double avgMs = total / Math.Max(1, nIntervals);
                double durationSec = Math.Max(total, 1.0) / 1000.0;
                double volRate = totalVol / durationSec;

                bool veloOk   = avgMs <= MaxAvgMs;
                bool durOk    = total <= MaxTotalMs;
                bool volOk    = volRate >= MinVolumeRate;
                bool volTotOk = totalVol >= MinTotalVolume;

                double maxAllowedRetroceso = Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepTicks);
                bool limpioOk = isAbsorb || (maxRetroceso <= maxAllowedRetroceso);

                if (veloOk && durOk && volOk && volTotOk && limpioOk)
                {
                    HFTBucket bucket; string bucketTxt;
                    if (isAbsorb)
                    {
                        bucket = HFTBucket.Absorb; bucketTxt = "ABS";
                    }
                    else
                    {
                        bucket = avgMs <= PredatorAvgMs ? HFTBucket.Predator
                               : avgMs <= UltraAvgMs    ? HFTBucket.Ultra : HFTBucket.Fast;
                        bucketTxt = bucket == HFTBucket.Predator ? "PRED"
                                  : bucket == HFTBucket.Ultra    ? "ULT"
                                  : (dir == 1 ? "BULL" : "BEAR");
                    }

                    double cvd = 0, buy = 0, sell = 0, maxTickVol = 0;
                    double slope = 0, dFirst = 0, dSecond = 0;
                    int noMoveTicks = 0, maxLevelTicks = 0;
                    double noMoveVol = 0;

                    if (EnableDbLogging)
                    {
                        for (int i = 0; i < signList.Count; i++)
                        {
                            double sv = signList[i];
                            cvd += sv;
                            if (sv >= 0) buy += volList[i]; else sell += volList[i];
                            if (volList[i] > maxTickVol) maxTickVol = volList[i];
                        }

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

                        var freq = new Dictionary<long, int>();
                        long prevTk = long.MinValue;
                        for (int i = 0; i < priceList.Count; i++)
                        {
                            long tk = (long)Math.Round(priceList[i] / TickSize);
                            if (i > 0 && tk == prevTk) { noMoveTicks++; noMoveVol += volList[i]; }
                            prevTk = tk;
                            int c; freq.TryGetValue(tk, out c); freq[tk] = c + 1;
                        }
                        foreach (var kv in freq) if (kv.Value > maxLevelTicks) maxLevelTicks = kv.Value;
                    }

                    DateTime tDetect = detectTickTime != default(DateTime) ? detectTickTime : tLast;
                    int curPrim = CurrentBars[0] >= 0 ? CurrentBars[0] : 0;
                    int prim_start  = startPrimBar;
                    int prim_end    = Math.Max(prim_start, lastPrimBar);
                    int prim_detect = Math.Max(prim_end, curPrim);

                    string txt = (MostrarTexto || EnableDbLogging)
                        ? string.Format("{0} {1:F0}t · V{2:F0}", bucketTxt, sweepTicks, totalVol)
                        : bucketTxt;

                    var z = new Zone
                    {
                        StartBar = prim_start,
                        EndBar = prim_end,
                        DetectBar = prim_detect,
                        VisualEndBar = prim_detect + Math.Max(1, ExtensionDibujo),
                        StartTime = tStart,
                        EndTime = tLast,
                        DetectTime = tDetect,
                        Upper = swH,
                        Lower = swL,
                        Direction = dir,
                        Bucket = bucket,
                        AvgMs = avgMs,
                        TotalMs = total,
                        VolRate = volRate,
                        Pasos = streak,
                        ValidSteps = validSteps,
                        TotalVol = totalVol,
                        MaxRetro = maxRetroceso,
                        MaxTickVol = maxTickVol,
                        Cvd = cvd,
                        BuyVol = buy,
                        SellVol = sell,
                        DeltaSlope = slope,
                        DeltaFirst = dFirst,
                        DeltaSecond = dSecond,
                        NoMoveTicks = noMoveTicks,
                        NoMoveVol = noMoveVol,
                        MaxLevelTicks = maxLevelTicks,
                        HeightTicks = sweepTicks,
                        Reporte = txt,
                        TerminationReason = reason
                    };
                    lock (syncRoot)
                    {
                        zones.Add(z);
                    }
                    if (EnableDbLogging) PersistZone(z);
                }
            }
            ResetState();
        }

        // ===================== DETECCIÓN CAUSAL DE EVENTOS INFRECUENTES =====================
        private static void AgregarHistoriaAcotada(List<double> hist, double val)
        {
            hist.Add(val);
            if (hist.Count > MaxHistoriaEventos)
                hist.RemoveAt(0);
        }

        private double Percentil(List<double> v, double p)
        {
            int n = v.Count;
            if (n == 0) return 0;
            sortScratch.Clear();
            for (int i = 0; i < n; i++) sortScratch.Add(v[i]);
            sortScratch.Sort();
            double pos = Math.Max(0.0, Math.Min(100.0, p)) / 100.0 * (n - 1);
            int k = (int)Math.Floor(pos);
            double frac = pos - k;
            if (k + 1 < n)
                return sortScratch[k] * (1.0 - frac) + sortScratch[k + 1] * frac;
            return sortScratch[k];
        }

        private static int CompareZonesByMid(Zone a, Zone b)
        {
            return (a.Upper + a.Lower).CompareTo(b.Upper + b.Lower);
        }

        // 1) CLUSTERS HFT CAUSALES:
        // Se evalúa en el instante en que la zona idx es detectada (detectBar = z.DetectBar).
        // Sólo considera zonas que YA fueron detectadas (w.DetectBar <= detectBar) y siguen vigentes (w.VisualEndBar >= detectBar).
        // Evalúa la DENSIDAD DE SOLAPAMIENTO (packing y gap libre entre zonas) normalizada por la altura propia de las zonas,
        // de modo que apilamientos de zonas de 3-6 puntos (40-60 ticks de alto total con alto solapamiento) se detecten igual de bien
        // que micro-zonas angostas. El rectángulo del cluster comienza estrictamente en detectBar (sin look-ahead hacia atrás).
        private void EvaluarClusterCausal(int idx)
        {
            Zone z = zones[idx];
            if (!MostrarAbsorb && z.Bucket == HFTBucket.Absorb) return;
            int detectBar = z.DetectBar;
            int K = Math.Max(2, MinZonasCluster);
            int ext = Math.Max(1, ExtensionDibujo);
            int minDetectBarViva = detectBar - ext;

            vivasBuf.Clear();
            for (int j = idx; j >= 0; j--)
            {
                Zone w = zones[j];
                if (w.DetectBar < minDetectBarViva) break;
                if (!MostrarAbsorb && w.Bucket == HFTBucket.Absorb) continue;
                if (w.DetectBar <= detectBar && w.VisualEndBar >= detectBar)
                    vivasBuf.Add(w);
            }
            if (vivasBuf.Count < K) return;

            vivasBuf.Sort(CompareZonesByMid);
            int pos = vivasBuf.IndexOf(z);
            if (pos < 0) return;

            double mejorScore = double.MaxValue;
            double bestLo = 0, bestHi = 0, bestPoc = 0, bestPacking = 0;
            int bestCount = 0;
            int nVivas = vivasBuf.Count;
            double maxAllowedSpanPrice = Math.Max(88.0, escalaVolTicks * 3.2) * TickSize;

            for (int startIdx = Math.Max(0, pos - K + 1); startIdx <= pos && startIdx + K <= nVivas; startIdx++)
            {
                int i0 = startIdx;
                int i1 = startIdx + K - 1;
                double lo = double.MaxValue, hi = double.MinValue;
                double sumH = 0, totalBandVol = 0, totalWeightedMid = 0;

                for (int j = i0; j <= i1; j++)
                {
                    Zone w = vivasBuf[j];
                    double wLo = Math.Min(w.Lower, w.Upper);
                    double wHi = Math.Max(w.Lower, w.Upper);
                    if (wLo < lo) lo = wLo;
                    if (wHi > hi) hi = wHi;
                    double hZ = Math.Max(TickSize * 2.0, wHi - wLo);
                    sumH += hZ;
                    double v = Math.Max(1.0, w.TotalVol);
                    totalBandVol += v;
                    totalWeightedMid += ((wLo + wHi) * 0.5) * v;
                }

                double avgZoneHeight = sumH / K;
                double maxJoinGap = Math.Max(TickSize * 4.0, avgZoneHeight * 0.35);

                // Expandir la pila contigua en O(1) amortizado sobre la lista ya ordenada por precio medio
                bool expanded = true;
                while (expanded)
                {
                    expanded = false;
                    if (i0 > 0)
                    {
                        Zone prev = vivasBuf[i0 - 1];
                        double pLo = Math.Min(prev.Lower, prev.Upper);
                        double pHi = Math.Max(prev.Lower, prev.Upper);
                        double newLo = Math.Min(lo, pLo);
                        double newHi = Math.Max(hi, pHi);
                        if (pHi >= lo - maxJoinGap && (newHi - newLo) <= maxAllowedSpanPrice)
                        {
                            lo = newLo;
                            hi = newHi;
                            i0--;
                            sumH += Math.Max(TickSize * 2.0, pHi - pLo);
                            double v = Math.Max(1.0, prev.TotalVol);
                            totalBandVol += v;
                            totalWeightedMid += ((pLo + pHi) * 0.5) * v;
                            expanded = true;
                        }
                    }
                    if (i1 + 1 < nVivas)
                    {
                        Zone next = vivasBuf[i1 + 1];
                        double nLo = Math.Min(next.Lower, next.Upper);
                        double nHi = Math.Max(next.Lower, next.Upper);
                        double newLo = Math.Min(lo, nLo);
                        double newHi = Math.Max(hi, nHi);
                        if (nLo <= hi + maxJoinGap && (newHi - newLo) <= maxAllowedSpanPrice)
                        {
                            lo = newLo;
                            hi = newHi;
                            i1++;
                            sumH += Math.Max(TickSize * 2.0, nHi - nLo);
                            double v = Math.Max(1.0, next.TotalVol);
                            totalBandVol += v;
                            totalWeightedMid += ((nLo + nHi) * 0.5) * v;
                            expanded = true;
                        }
                    }
                }

                int mTotal = i1 - i0 + 1;
                double spanPrice = Math.Max(TickSize * 2.0, hi - lo);
                if (spanPrice > maxAllowedSpanPrice) continue;

                // Densidad real de solapamiento (packing = suma de alturas individuales / altura total de la pila)
                double packing = sumH / spanPrice;
                if (packing < 0.70) continue;

                double spanTicks = spanPrice / TickSize;
                double avgZoneTicks = Math.Max(6.0, (sumH / mTotal) / TickSize);
                double pasoNorm = (spanTicks / mTotal) / avgZoneTicks;
                double gapLibreTicks = Math.Max(0.0, spanPrice - sumH * 0.75) / TickSize;
                double gapNorm = (gapLibreTicks / mTotal) / avgZoneTicks;

                double bonusZonas = Math.Pow((double)mTotal / K, 0.80);
                double bonusPack = Math.Sqrt(Math.Max(0.6, packing));
                double volRatio = (totalBandVol / mTotal) / Math.Max(10.0, escalaVolZonaMean);
                double bonusVol = 1.0 + 0.15 * Math.Min(3.0, volRatio);
                double score = (pasoNorm + 0.65 * gapNorm) / (bonusZonas * bonusPack * bonusVol);

                if (score < mejorScore)
                {
                    mejorScore = score;
                    bestLo = lo;
                    bestHi = hi;
                    bestCount = mTotal;
                    bestPacking = packing;
                    bestPoc = totalBandVol > 0 ? (totalWeightedMid / totalBandVol) : ((lo + hi) * 0.5);
                }
            }

            if (mejorScore == double.MaxValue) return;
            double bestWidthTicks = (bestHi - bestLo) / TickSize;
            int extPct = Math.Max(10, PctExtensionBars);

            // Verificar si ya hay un cluster activo en este rango de precio en detectBar
            CausalCluster activoSolapado = null;
            for (int i = clustersPct.Count - 1; i >= 0; i--)
            {
                CausalCluster cc = clustersPct[i];
                if (cc.DetectBar < detectBar - extPct * 3) break;
                if (cc.VisualEndBar < detectBar) continue;
                if (cc.Lower <= bestHi + TickSize * 2 && bestLo - TickSize * 2 <= cc.Upper)
                {
                    activoSolapado = cc;
                    break;
                }
            }

            if (activoSolapado != null)
            {
                if (bestCount > activoSolapado.ZoneCount || mejorScore < activoSolapado.Score || bestLo < activoSolapado.Lower || bestHi > activoSolapado.Upper)
                {
                    activoSolapado.Lower = Math.Min(activoSolapado.Lower, bestLo);
                    activoSolapado.Upper = Math.Max(activoSolapado.Upper, bestHi);
                    activoSolapado.PocPrice = bestPoc;
                    activoSolapado.WidthTicks = (activoSolapado.Upper - activoSolapado.Lower) / TickSize;
                    activoSolapado.VisualEndBar = Math.Max(activoSolapado.VisualEndBar, detectBar + extPct);
                    activoSolapado.ZoneCount = Math.Max(activoSolapado.ZoneCount, bestCount);
                    activoSolapado.Score = Math.Min(activoSolapado.Score, mejorScore);
                    activoSolapado.Label = string.Format("CLUS {0}z · {1:F0}t", activoSolapado.ZoneCount, activoSolapado.WidthTicks);
                }
                return;
            }

            // Registrar en la historia sólo candidatos de formaciones distintas
            AgregarHistoriaAcotada(histScoreCluster, mejorScore);

            int nHist = histScoreCluster.Count;
            bool altaConfluenciaDirecta = (bestCount >= K + 1 && bestPacking >= 1.35) || (bestCount >= K && bestPacking >= 1.65);

            if (!altaConfluenciaDirecta)
            {
                if (nHist < Math.Max(6, PctMinHistoria / 2)) return;
                double fracSesion = Math.Max(0.5, ClustersPorSesion) * Math.Max(1, sesionesVistas) / Math.Max(1, nHist);
                double pctEfectivo = Math.Max((double)PctAngosto, Math.Min(35.0, 100.0 * fracSesion));
                double umbral = Percentil(histScoreCluster, Math.Max(5.0, pctEfectivo));
                if (mejorScore > umbral) return;
            }

            // Confirmado en detectBar: nace en detectBar y se proyecta hacia adelante
            var nuevoCluster = new CausalCluster
            {
                Lower        = bestLo,
                Upper        = bestHi,
                PocPrice     = bestPoc,
                DetectBar    = detectBar,
                VisualEndBar = detectBar + extPct,
                ZoneCount    = bestCount,
                WidthTicks   = bestWidthTicks,
                Score        = mejorScore,
                Label        = string.Format("CLUS {0}z · {1:F0}t", bestCount, bestWidthTicks)
            };
            lock (syncRoot)
            {
                clustersPct.Add(nuevoCluster);
            }
        }

        // 2) EXPANSIONES SIN HFT CAUSALES (SIN DESFASE Y SIN SUPERPOSICIÓN):
        private void RegistrarPiernaEnHistoria()
        {
            if (impBestScoreRegistrado > 0.15)
            {
                AgregarHistoriaAcotada(histScoreExp, impBestScoreRegistrado);
                umbralExpDirty = true;
            }
            impBestScoreRegistrado = 0;
            impLastTriggeredHeightTicks = 0;
            impActiveExpansion = null;
        }

        private void RecortarExpansionesSolapadas(CausalExpansion actual)
        {
            if (actual == null) return;
            int minBar = actual.DetectBar - Math.Max(10, PctExtensionBars) * 3;
            for (int i = expansionsPct.Count - 1; i >= 0; i--)
            {
                CausalExpansion prev = expansionsPct[i];
                if (prev.DetectBar < minBar) break;
                if (ReferenceEquals(prev, actual)) continue;
                if (prev.VisualEndBar <= actual.DetectBar) continue;
                double ov = Math.Min(prev.Upper, actual.Upper) - Math.Max(prev.Lower, actual.Lower);
                if (ov >= -TickSize)
                {
                    prev.VisualEndBar = Math.Min(prev.VisualEndBar, actual.DetectBar);
                }
            }
        }

        private void NotificarZonaNuevaEnImpulso(Zone z)
        {
            if (z == null || impDir == 0) return;
            if (!MostrarAbsorb && z.Bucket == HFTBucket.Absorb) return;

            int b = CurrentBars[0];
            double zl = Math.Min(z.Lower, z.Upper);
            double zh = Math.Max(z.Lower, z.Upper);

            if (impDir == 1)
            {
                if (zh >= impStartPrice && zl <= impExtPrice + TickSize * 2)
                {
                    if (impActiveExpansion != null && impActiveExpansion.LegId == impLegId && zl > impActiveExpansion.Lower + TickSize * 4)
                    {
                        impActiveExpansion.Upper = Math.Max(impActiveExpansion.Upper, zl);
                        impActiveExpansion.MidPrice = (impActiveExpansion.Lower + impActiveExpansion.Upper) * 0.5;
                        impActiveExpansion.HeightTicks = (impActiveExpansion.Upper - impActiveExpansion.Lower) / TickSize;
                        impActiveExpansion.Label = string.Format("EXP {0:F0}t", impActiveExpansion.HeightTicks);
                        RecortarExpansionesSolapadas(impActiveExpansion);
                    }
                    RegistrarPiernaEnHistoria();
                    impStartPrice = zh;
                    impExtPrice = Math.Max(zh, Highs[0][0]);
                    impStartBar = b;
                    impExtBar = b;
                    impSumRange = Math.Max(TickSize, Highs[0][0] - Lows[0][0]);
                    impLegId++;
                }
            }
            else if (impDir == -1)
            {
                if (zl <= impStartPrice && zh >= impExtPrice - TickSize * 2)
                {
                    if (impActiveExpansion != null && impActiveExpansion.LegId == impLegId && zh < impActiveExpansion.Upper - TickSize * 4)
                    {
                        impActiveExpansion.Lower = Math.Min(impActiveExpansion.Lower, zh);
                        impActiveExpansion.MidPrice = (impActiveExpansion.Lower + impActiveExpansion.Upper) * 0.5;
                        impActiveExpansion.HeightTicks = (impActiveExpansion.Upper - impActiveExpansion.Lower) / TickSize;
                        impActiveExpansion.Label = string.Format("EXP {0:F0}t", impActiveExpansion.HeightTicks);
                        RecortarExpansionesSolapadas(impActiveExpansion);
                    }
                    RegistrarPiernaEnHistoria();
                    impStartPrice = zl;
                    impExtPrice = Math.Min(zl, Lows[0][0]);
                    impStartBar = b;
                    impExtBar = b;
                    impSumRange = Math.Max(TickSize, Highs[0][0] - Lows[0][0]);
                    impLegId++;
                }
            }
        }

        private void ActualizarImpulsoYExpansionCausal()
        {
            int b = CurrentBars[0];
            double H = Highs[0][0];
            double L = Lows[0][0];
            double barRng = Math.Max(TickSize, H - L);
            int extPct = Math.Max(10, PctExtensionBars);
            int minBarActiva = b - extPct * 3;

            // 1) Mitigar expansiones previas selladas si el precio ya rellenó >= 75% de su rango
            for (int i = expansionsPct.Count - 1; i >= 0; i--)
            {
                CausalExpansion prev = expansionsPct[i];
                if (prev.DetectBar < minBarActiva) break;
                if (ReferenceEquals(prev, impActiveExpansion)) continue;
                if (prev.VisualEndBar <= b) continue;
                double span = prev.Upper - prev.Lower;
                if (span <= TickSize) continue;
                if (prev.Direction == -1 && H >= prev.Lower + 0.75 * span)
                {
                    prev.VisualEndBar = b;
                }
                else if (prev.Direction == 1 && L <= prev.Upper - 0.75 * span)
                {
                    prev.VisualEndBar = b;
                }
            }

            // Giro local adaptativo (sin escalar por 0.38 * legHeight, que desfasaba los giros hasta 80 puntos)
            double giroTicks = Math.Max(12.0, Math.Min((double)Math.Max(12, ZigZagTicks), escalaVolTicks * 2.2));
            double giroReq = giroTicks * TickSize;

            if (impDir == 0)
            {
                if (impStartPrice == 0)
                {
                    impStartPrice = Closes[0][0];
                    impExtPrice = impStartPrice;
                    impStartBar = b;
                    impExtBar = b;
                    return;
                }
                impSumRange += barRng;
                if (H - impStartPrice >= giroReq)
                {
                    impDir = 1;
                    impExtPrice = H;
                    impExtBar = b;
                    impLegId++;
                }
                else if (impStartPrice - L >= giroReq)
                {
                    impDir = -1;
                    impExtPrice = L;
                    impExtBar = b;
                    impLegId++;
                }
                return;
            }

            bool nuevoExtremo = false;
            if (impDir == 1)
            {
                if (H >= impExtPrice)
                {
                    impExtPrice = H;
                    impExtBar = b;
                    impSumRange += barRng;
                    nuevoExtremo = true;
                }
                else if (impExtPrice - L >= giroReq)
                {
                    RegistrarPiernaEnHistoria();
                    impStartPrice = impExtPrice;
                    impStartBar = impExtBar;
                    impDir = -1;
                    impExtPrice = L;
                    impExtBar = b;
                    impSumRange = barRng;
                    impLegId++;
                    nuevoExtremo = true;
                }
                else
                {
                    impSumRange += barRng;
                }
            }
            else
            {
                if (L <= impExtPrice)
                {
                    impExtPrice = L;
                    impExtBar = b;
                    impSumRange += barRng;
                    nuevoExtremo = true;
                }
                else if (H - impExtPrice >= giroReq)
                {
                    RegistrarPiernaEnHistoria();
                    impStartPrice = impExtPrice;
                    impStartBar = impExtBar;
                    impDir = 1;
                    impExtPrice = H;
                    impExtBar = b;
                    impSumRange = barRng;
                    impLegId++;
                    nuevoExtremo = true;
                }
                else
                {
                    impSumRange += barRng;
                }
            }

            if (!nuevoExtremo) return;

            double lo = Math.Min(impStartPrice, impExtPrice);
            double hi = Math.Max(impStartPrice, impExtPrice);
            double dispTicks = (hi - lo) / TickSize;
            if (dispTicks < 6.0) return;

            // Determinar el corredor libre de zonas HFT en la FRONTERA LÍDER del impulso actual [impStartBar .. b]
            double gLo = lo;
            double gHi = hi;
            for (int j = primeraSinEvaluar - 1; j >= 0; j--)
            {
                Zone z = zones[j];
                if (z.DetectBar < impStartBar - 15) break;
                if (z.DetectBar > b) continue;
                if (!MostrarAbsorb && z.Bucket == HFTBucket.Absorb) continue;
                double zl = Math.Min(z.Lower, z.Upper);
                double zh = Math.Max(z.Lower, z.Upper);
                if (zh < lo || zl > hi) continue;

                if (impDir == 1)
                {
                    if (zl <= hi && zh >= hi - TickSize) return;
                    if (zh > gLo && zh < hi) gLo = zh;
                }
                else
                {
                    if (zh >= lo && zl <= lo + TickSize) return;
                    if (zl < gHi && zl > lo) gHi = zl;
                }
            }

            // Si la expansión ya estaba activa en esta pierna, mantener su ancla de inicio fija y sólo expandir la frontera líder
            if (impActiveExpansion != null && impActiveExpansion.LegId == impLegId)
            {
                if (impDir == 1)
                {
                    gLo = impActiveExpansion.Lower;
                    gHi = Math.Max(impActiveExpansion.Upper, gHi);
                }
                else
                {
                    gHi = impActiveExpansion.Upper;
                    gLo = Math.Min(impActiveExpansion.Lower, gLo);
                }
            }

            double mejorGap = gHi - gLo;
            double gapTicks = mejorGap / TickSize;
            if (gapTicks < 6.0) return;

            // Eficiencia direccional y puntaje normalizado por volatilidad
            double netMove = Math.Abs(impExtPrice - impStartPrice);
            double eficiencia = Math.Min(1.0, netMove / Math.Max(netMove, impSumRange * 0.45));
            double altoNorm = gapTicks / Math.Max(6.0, escalaVolTicks);
            double scoreExp = altoNorm * (0.55 + 0.45 * eficiencia);

            if (scoreExp > impBestScoreRegistrado)
                impBestScoreRegistrado = scoreExp;

            if (gapTicks < Math.Max(8, MinExpTicks)) return;

            // Si ya se activó la expansión en esta pierna, actualizar in-place su frontera líder (manteniendo DetectBar fijo!)
            if (impActiveExpansion != null && impActiveExpansion.LegId == impLegId)
            {
                impActiveExpansion.Lower = gLo;
                impActiveExpansion.Upper = gHi;
                impActiveExpansion.MidPrice = (gLo + gHi) * 0.5;
                impActiveExpansion.HeightTicks = gapTicks;
                impActiveExpansion.Efficiency = eficiencia;
                impActiveExpansion.VisualEndBar = Math.Max(impActiveExpansion.VisualEndBar, b + extPct);
                impActiveExpansion.Label = string.Format("EXP {0:F0}t", gapTicks);
                impLastTriggeredHeightTicks = gapTicks;
                RecortarExpansionesSolapadas(impActiveExpansion);
                return;
            }

            int nHist = histScoreExp.Count;
            if (nHist < Math.Max(10, PctMinHistoria)) return;

            if (umbralExpDirty)
            {
                double frac = Math.Min(PctAmplio / 100.0, Math.Max(0.1, ExpPorSesion) * Math.Max(1, sesionesVistas) / nHist);
                cachedUmbralExp = Percentil(histScoreExp, 100.0 * (1.0 - frac));
                umbralExpDirty = false;
            }
            if (scoreExp < cachedUmbralExp) return;

            // Evitar abrir una expansión redundante contenida dentro de una expansión activa de sentido opuesto
            for (int i = expansionsPct.Count - 1; i >= 0; i--)
            {
                CausalExpansion prev = expansionsPct[i];
                if (prev.DetectBar < b - 45) break;
                if (prev.VisualEndBar <= b) continue;
                double inter = Math.Min(prev.Upper, gHi) - Math.Max(prev.Lower, gLo);
                if (inter > 0 && inter >= 0.70 * mejorGap && b - prev.DetectBar < 40)
                {
                    prev.VisualEndBar = b;
                    return;
                }
            }

            impLastTriggeredHeightTicks = gapTicks;
            var nuevaExp = new CausalExpansion
            {
                Lower        = gLo,
                Upper        = gHi,
                MidPrice     = (gLo + gHi) * 0.5,
                DetectBar    = b,
                VisualEndBar = b + extPct,
                Direction    = impDir,
                HeightTicks  = gapTicks,
                Efficiency   = eficiencia,
                LegId        = impLegId,
                Label        = string.Format("EXP {0:F0}t", gapTicks)
            };
            impActiveExpansion = nuevaExp;
            RecortarExpansionesSolapadas(nuevaExp);
            lock (syncRoot)
            {
                expansionsPct.Add(nuevaExp);
            }
        }

        // ===================== RENDERIZADO SHARPDX (ESTÉTICO, SIN LOOK-AHEAD, CON SCROLLBACK TOTAL) =====================
        private void DisposeDxResources()
        {
            dxReady = false;
            if (dxBullFill      != null) { dxBullFill.Dispose();      dxBullFill = null; }
            if (dxBearFill      != null) { dxBearFill.Dispose();      dxBearFill = null; }
            if (dxPredFill      != null) { dxPredFill.Dispose();      dxPredFill = null; }
            if (dxUltraFill     != null) { dxUltraFill.Dispose();     dxUltraFill = null; }
            if (dxAbsorbFill    != null) { dxAbsorbFill.Dispose();    dxAbsorbFill = null; }
            if (dxBullEdge      != null) { dxBullEdge.Dispose();      dxBullEdge = null; }
            if (dxBearEdge      != null) { dxBearEdge.Dispose();      dxBearEdge = null; }
            if (dxPredEdge      != null) { dxPredEdge.Dispose();      dxPredEdge = null; }
            if (dxUltraEdge     != null) { dxUltraEdge.Dispose();     dxUltraEdge = null; }
            if (dxAbsorbEdge    != null) { dxAbsorbEdge.Dispose();    dxAbsorbEdge = null; }
            if (dxClusterFill   != null) { dxClusterFill.Dispose();   dxClusterFill = null; }
            if (dxClusterBorder != null) { dxClusterBorder.Dispose(); dxClusterBorder = null; }
            if (dxClusterAccent != null) { dxClusterAccent.Dispose(); dxClusterAccent = null; }
            if (dxClusterText   != null) { dxClusterText.Dispose();   dxClusterText = null; }
            if (dxExpFill       != null) { dxExpFill.Dispose();       dxExpFill = null; }
            if (dxExpBorder     != null) { dxExpBorder.Dispose();     dxExpBorder = null; }
            if (dxExpAccent     != null) { dxExpAccent.Dispose();     dxExpAccent = null; }
            if (dxExpText       != null) { dxExpText.Dispose();       dxExpText = null; }
            if (dxLabelBg       != null) { dxLabelBg.Dispose();       dxLabelBg = null; }
            if (dxDashStyle     != null) { dxDashStyle.Dispose();     dxDashStyle = null; }
            if (dwFontSmall     != null) { dwFontSmall.Dispose();     dwFontSmall = null; }
        }

        public override void OnRenderTargetChanged()
        {
            DisposeDxResources();
            if (RenderTarget == null) return;
            try
            {
                float opBase = Math.Max(0.02f, Math.Min(0.85f, Opacidad / 100f));
                float opEdge = Math.Min(0.90f, opBase * 3.2f);
                float opPct  = Math.Max(0.04f, Math.Min(0.85f, OpacidadPct / 100f));

                dxBullFill   = (ColorBull     ?? Brushes.DodgerBlue).ToDxBrush(RenderTarget);   dxBullFill.Opacity   = opBase;
                dxBearFill   = (ColorBear     ?? Brushes.Tomato).ToDxBrush(RenderTarget);       dxBearFill.Opacity   = opBase;
                dxPredFill   = (ColorPredator ?? Brushes.Gold).ToDxBrush(RenderTarget);         dxPredFill.Opacity   = Math.Min(0.85f, opBase * 1.35f);
                dxUltraFill  = (ColorUltra    ?? Brushes.Silver).ToDxBrush(RenderTarget);       dxUltraFill.Opacity  = opBase;
                dxAbsorbFill = (ColorAbsorb   ?? Brushes.MediumPurple).ToDxBrush(RenderTarget); dxAbsorbFill.Opacity = opBase;

                dxBullEdge   = (ColorBull     ?? Brushes.DodgerBlue).ToDxBrush(RenderTarget);   dxBullEdge.Opacity   = opEdge;
                dxBearEdge   = (ColorBear     ?? Brushes.Tomato).ToDxBrush(RenderTarget);       dxBearEdge.Opacity   = opEdge;
                dxPredEdge   = (ColorPredator ?? Brushes.Gold).ToDxBrush(RenderTarget);         dxPredEdge.Opacity   = Math.Min(0.95f, opEdge * 1.2f);
                dxUltraEdge  = (ColorUltra    ?? Brushes.Silver).ToDxBrush(RenderTarget);       dxUltraEdge.Opacity  = opEdge;
                dxAbsorbEdge = (ColorAbsorb   ?? Brushes.MediumPurple).ToDxBrush(RenderTarget); dxAbsorbEdge.Opacity = opEdge;

                Brush cClust = ColorClusterPct ?? Brushes.DarkOrange;
                Brush cClustEdge = (cClust == Brushes.Gold) ? Brushes.DarkOrange : cClust;
                dxClusterFill   = cClust.ToDxBrush(RenderTarget);     dxClusterFill.Opacity   = opPct;
                dxClusterBorder = cClustEdge.ToDxBrush(RenderTarget); dxClusterBorder.Opacity = Math.Min(0.95f, opPct * 3.4f);
                dxClusterAccent = cClustEdge.ToDxBrush(RenderTarget); dxClusterAccent.Opacity = 0.95f;
                dxClusterText   = cClustEdge.ToDxBrush(RenderTarget); dxClusterText.Opacity   = 0.98f;

                Brush cExp = ColorVacioPct ?? Brushes.DeepSkyBlue;
                dxExpFill   = cExp.ToDxBrush(RenderTarget); dxExpFill.Opacity   = Math.Max(0.03f, opPct * 0.85f);
                dxExpBorder = cExp.ToDxBrush(RenderTarget); dxExpBorder.Opacity = Math.Min(0.88f, opPct * 2.6f);
                dxExpAccent = cExp.ToDxBrush(RenderTarget); dxExpAccent.Opacity = 0.90f;
                dxExpText   = cExp.ToDxBrush(RenderTarget); dxExpText.Opacity   = 0.95f;

                dxLabelBg = new SharpDX.Direct2D1.SolidColorBrush(RenderTarget, new SharpDX.Color4(0.06f, 0.08f, 0.12f, 0.78f));

                var sp = new SharpDX.Direct2D1.StrokeStyleProperties
                {
                    DashStyle = SharpDX.Direct2D1.DashStyle.Dash,
                    DashCap   = SharpDX.Direct2D1.CapStyle.Flat
                };
                dxDashStyle = new SharpDX.Direct2D1.StrokeStyle(RenderTarget.Factory, sp);
                dwFontSmall = new SharpDX.DirectWrite.TextFormat(NinjaTrader.Core.Globals.DirectWriteFactory, "Segoe UI",
                    SharpDX.DirectWrite.FontWeight.SemiBold, SharpDX.DirectWrite.FontStyle.Normal, 10f);

                dxReady = true;
            }
            catch
            {
                DisposeDxResources();
            }
        }

        private int BuscarPrimeraZona(int minDetectBar)
        {
            int lo = 0, hi = zones.Count - 1;
            while (lo <= hi)
            {
                int mid = (lo + hi) >> 1;
                if (zones[mid].DetectBar < minDetectBar) lo = mid + 1;
                else hi = mid - 1;
            }
            return lo;
        }

        private int BuscarPrimeraExp(int minDetectBar)
        {
            int lo = 0, hi = expansionsPct.Count - 1;
            while (lo <= hi)
            {
                int mid = (lo + hi) >> 1;
                if (expansionsPct[mid].DetectBar < minDetectBar) lo = mid + 1;
                else hi = mid - 1;
            }
            return lo;
        }

        private int BuscarPrimerCluster(int minDetectBar)
        {
            int lo = 0, hi = clustersPct.Count - 1;
            while (lo <= hi)
            {
                int mid = (lo + hi) >> 1;
                if (clustersPct[mid].DetectBar < minDetectBar) lo = mid + 1;
                else hi = mid - 1;
            }
            return lo;
        }

        protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
        {
            base.OnRender(chartControl, chartScale);
            if (ModoExportacionPuro || Bars == null || ChartBars == null || RenderTarget == null) return;
            if (!dxReady) OnRenderTargetChanged();
            if (!dxReady) return;

            int fromBar = ChartBars.FromIndex;
            int toBar   = ChartBars.ToIndex;
            if (toBar < fromBar) return;

            int extBase = Math.Max(1, ExtensionDibujo);
            int extPct  = Math.Max(10, PctExtensionBars) * 3;
            float halfBar = Math.Max(1f, (float)chartControl.Properties.BarDistance * 0.45f);
            SharpDX.Direct2D1.AntialiasMode prevMode = RenderTarget.AntialiasMode;
            RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.Aliased;

            try
            {
                lock (syncRoot)
                {
                    // 1. CAPA BASE: Zonas HFT individuales (búsqueda binaria O(log N) + corte inmediato en toBar)
                    if (MostrarZonasBase && zones.Count > 0)
                    {
                        int iStart = BuscarPrimeraZona(fromBar - extBase);
                        for (int i = iStart; i < zones.Count; i++)
                        {
                            Zone z = zones[i];
                            if (z.DetectBar > toBar) break;
                            if (z.VisualEndBar < fromBar) continue;

                            int bStart = Math.Max(fromBar, z.DetectBar);
                            int bEnd   = Math.Min(toBar, z.VisualEndBar);
                            float x1 = chartControl.GetXByBarIndex(ChartBars, bStart);
                            float x2 = chartControl.GetXByBarIndex(ChartBars, bEnd) + halfBar;
                            if (x2 <= x1) x2 = x1 + 2f;

                            float yTop = chartScale.GetYByValue(Math.Max(z.Upper, z.Lower));
                            float yBot = chartScale.GetYByValue(Math.Min(z.Upper, z.Lower));
                            float h = yBot - yTop;
                            if (h < 1.5f) { yTop -= 0.75f; h = 1.5f; }

                            SharpDX.Direct2D1.Brush fillBrush, edgeBrush;
                            switch (z.Bucket)
                            {
                                case HFTBucket.Predator: fillBrush = dxPredFill;   edgeBrush = dxPredEdge;   break;
                                case HFTBucket.Ultra:    fillBrush = dxUltraFill;  edgeBrush = dxUltraEdge;  break;
                                case HFTBucket.Absorb:   fillBrush = dxAbsorbFill; edgeBrush = dxAbsorbEdge; break;
                                default:
                                    fillBrush = z.Direction == 1 ? dxBullFill : dxBearFill;
                                    edgeBrush = z.Direction == 1 ? dxBullEdge : dxBearEdge;
                                    break;
                            }

                            var rect = new SharpDX.RectangleF(x1, yTop, x2 - x1, h);
                            RenderTarget.FillRectangle(rect, fillBrush);

                            // Marcador nítido de 2px en la barra exacta de detección (z.DetectBar)
                            if (z.DetectBar >= fromBar && z.DetectBar <= toBar)
                            {
                                var detectBarRect = new SharpDX.RectangleF(x1, yTop, Math.Min(2.5f, x2 - x1), h);
                                RenderTarget.FillRectangle(detectBarRect, edgeBrush);
                            }

                            if (MostrarTexto && z.DetectBar >= fromBar && z.DetectBar <= toBar)
                            {
                                DibujarEtiquetaCompacta(z.Reporte, x1 + 4f, yTop - 13f, edgeBrush);
                            }
                        }
                    }

                    // 2. CAPA INFRECUENTE A: Expansiones sin HFT (búsqueda binaria O(log N) + corte en toBar)
                    if (MostrarRangosPct && expansionsPct.Count > 0)
                    {
                        int iStart = BuscarPrimeraExp(fromBar - extPct);
                        for (int i = iStart; i < expansionsPct.Count; i++)
                        {
                            CausalExpansion ex = expansionsPct[i];
                            if (ex.DetectBar > toBar) break;
                            if (ex.VisualEndBar < fromBar) continue;

                            int bStart = Math.Max(fromBar, ex.DetectBar);
                            int bEnd   = Math.Min(toBar, ex.VisualEndBar);
                            float x1 = chartControl.GetXByBarIndex(ChartBars, bStart);
                            float x2 = chartControl.GetXByBarIndex(ChartBars, bEnd) + halfBar;
                            if (x2 <= x1) x2 = x1 + 3f;

                            float yTop = chartScale.GetYByValue(ex.Upper);
                            float yBot = chartScale.GetYByValue(ex.Lower);
                            float yMid = chartScale.GetYByValue(ex.MidPrice);
                            float h = yBot - yTop;
                            if (h < 2f) h = 2f;

                            var rect = new SharpDX.RectangleF(x1, yTop, x2 - x1, h);
                            RenderTarget.FillRectangle(rect, dxExpFill);

                            // Bordes horizontales superior e inferior finos + línea 50% punteada
                            RenderTarget.DrawLine(new SharpDX.Vector2(x1, yTop), new SharpDX.Vector2(x2, yTop), dxExpBorder, 1.2f);
                            RenderTarget.DrawLine(new SharpDX.Vector2(x1, yBot), new SharpDX.Vector2(x2, yBot), dxExpBorder, 1.2f);
                            if (h >= 8f && dxDashStyle != null)
                            {
                                RenderTarget.DrawLine(new SharpDX.Vector2(x1, yMid), new SharpDX.Vector2(x2, yMid), dxExpBorder, 1.0f, dxDashStyle);
                            }

                            // Barra vertical de anclaje en el punto exacto de detección (ex.DetectBar)
                            if (ex.DetectBar >= fromBar && ex.DetectBar <= toBar)
                            {
                                RenderTarget.FillRectangle(new SharpDX.RectangleF(x1, yTop, 3f, h), dxExpAccent);
                                if (MostrarTextoPct && (x2 - x1) >= 28f)
                                {
                                    DibujarEtiquetaCompacta(ex.Label, x1 + 5f, yTop + 2f, dxExpText);
                                }
                            }
                        }
                    }

                    // 3. CAPA INFRECUENTE B: Clusters HFT (búsqueda binaria O(log N) + corte en toBar)
                    if (MostrarRangosPct && clustersPct.Count > 0)
                    {
                        int iStart = BuscarPrimerCluster(fromBar - extPct);
                        for (int i = iStart; i < clustersPct.Count; i++)
                        {
                            CausalCluster cc = clustersPct[i];
                            if (cc.DetectBar > toBar) break;
                            if (cc.VisualEndBar < fromBar) continue;

                            int bStart = Math.Max(fromBar, cc.DetectBar);
                            int bEnd   = Math.Min(toBar, cc.VisualEndBar);
                            float x1 = chartControl.GetXByBarIndex(ChartBars, bStart);
                            float x2 = chartControl.GetXByBarIndex(ChartBars, bEnd) + halfBar;
                            if (x2 <= x1) x2 = x1 + 3f;

                            float yTop = chartScale.GetYByValue(cc.Upper);
                            float yBot = chartScale.GetYByValue(cc.Lower);
                            float yPoc = chartScale.GetYByValue(cc.PocPrice);
                            float h = yBot - yTop;
                            if (h < 2f) { yTop -= 1f; h = 2f; }

                            var rect = new SharpDX.RectangleF(x1, yTop, x2 - x1, h);
                            RenderTarget.FillRectangle(rect, dxClusterFill);

                            // Contorno superior/inferior + línea POC punteada
                            RenderTarget.DrawLine(new SharpDX.Vector2(x1, yTop), new SharpDX.Vector2(x2, yTop), dxClusterBorder, 1.5f);
                            RenderTarget.DrawLine(new SharpDX.Vector2(x1, yBot), new SharpDX.Vector2(x2, yBot), dxClusterBorder, 1.5f);
                            if (h >= 6f && dxDashStyle != null)
                            {
                                RenderTarget.DrawLine(new SharpDX.Vector2(x1, yPoc), new SharpDX.Vector2(x2, yPoc), dxClusterAccent, 1.2f, dxDashStyle);
                            }

                            // Barra vertical de anclaje en el punto exacto de detección (cc.DetectBar)
                            if (cc.DetectBar >= fromBar && cc.DetectBar <= toBar)
                            {
                                RenderTarget.FillRectangle(new SharpDX.RectangleF(x1, yTop, 3.5f, h), dxClusterAccent);
                                if (MostrarTextoPct && (x2 - x1) >= 28f)
                                {
                                    DibujarEtiquetaCompacta(cc.Label, x1 + 5f, yTop - 15f, dxClusterText);
                                }
                            }
                        }
                    }
                }
            }
            finally
            {
                RenderTarget.AntialiasMode = prevMode;
            }
        }

        private void DibujarEtiquetaCompacta(string text, float x, float y, SharpDX.Direct2D1.Brush textBrush)
        {
            if (string.IsNullOrEmpty(text) || dwFontSmall == null || textBrush == null) return;
            float tw = text.Length * 5.8f + 6f;
            float th = 14f;
            if (dxLabelBg != null)
            {
                RenderTarget.FillRectangle(new SharpDX.RectangleF(x - 2f, y - 1f, tw, th), dxLabelBg);
            }
            RenderTarget.DrawText(text, dwFontSmall, new SharpDX.RectangleF(x, y - 1f, tw + 20f, th + 2f), textBrush);
        }

        // ===================== FLOW STREAM & SQLITE =====================
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

        private void SetupDb()
        {
            try
            {
                string dirPath = Path.GetDirectoryName(DbPath);
                if (!string.IsNullOrEmpty(dirPath) && !Directory.Exists(dirPath))
                    Directory.CreateDirectory(dirPath);

                dbConn = new SQLiteConnection("Data Source=" + DbPath + ";Version=3;");
                dbConn.Open();
                using (var c = new SQLiteCommand(
                    "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;", dbConn))
                    c.ExecuteNonQuery();

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
                foreach (string p in new[]{"@inst","@ct","@sess","@tseq","@ts_ns","@ptk","@vol,@btk","@atk"})
                {
                    // Handled explicitly below
                }
                tickCmd.Parameters.Clear();
                foreach (string p in new[]{"@inst","@ct","@sess","@tseq","@ts_ns","@ptk","@vol","@btk","@atk"})
                    tickCmd.Parameters.Add(new SQLiteParameter(p));
                tickCmd.Prepare();
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

        private void PersistZone(Zone z)
        {
            if (!dbReady) return;
            currentZoneSeq++;

            long startNs = UnixNs(z.StartTime);
            long endNs   = UnixNs(z.EndTime);
            long availNs = UnixNs(z.DetectTime);

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
                if (!hasLoggedFlushError)
                {
                    hasLoggedFlushError = true;
                    Print("[HFTLogger-NQ] FlushAll error: " + ex.Message);
                }
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

        #region P. Rangos por percentil (Causal V2)
        [Display(Name="Mostrar clusters y expansiones", Order=1, GroupName="P. Rangos por percentil")]
        public bool MostrarRangosPct { get; set; }

        [Display(Name="Mostrar zonas HFT base", Order=2, GroupName="P. Rangos por percentil")]
        public bool MostrarZonasBase { get; set; }

        [Range(2, 50)][Display(Name="Min zonas por cluster", Order=3, GroupName="P. Rangos por percentil")]
        public int MinZonasCluster { get; set; }

        [Range(1, 100)][Display(Name="% clusters mas densos (top %)", Order=4, GroupName="P. Rangos por percentil")]
        public int PctAngosto { get; set; }

        [Range(0.1, 50)][Display(Name="Clusters por sesion (promedio)", Order=5, GroupName="P. Rangos por percentil")]
        public double ClustersPorSesion { get; set; }

        [Range(1, 100)][Display(Name="% expansiones mas amplias (top %)", Order=6, GroupName="P. Rangos por percentil")]
        public int PctAmplio { get; set; }

        [Range(0.1, 50)][Display(Name="Expansiones por sesion (promedio)", Order=7, GroupName="P. Rangos por percentil")]
        public double ExpPorSesion { get; set; }

        [Range(4, 2000)][Display(Name="Alto minimo expansion (ticks)", Order=8, GroupName="P. Rangos por percentil")]
        public int MinExpTicks { get; set; }

        [Range(4, 10000)][Display(Name="Giro minimo impulso (ticks)", Order=9, GroupName="P. Rangos por percentil")]
        public int ZigZagTicks { get; set; }

        [Range(10, 100000)][Display(Name="Historia minima (casos)", Order=10, GroupName="P. Rangos por percentil")]
        public int PctMinHistoria { get; set; }

        [Range(10, 5000)][Display(Name="Extension derecha (velas)", Order=11, GroupName="P. Rangos por percentil")]
        public int PctExtensionBars { get; set; }

        [Range(1, 100)][Display(Name="Opacidad clusters/expansiones", Order=12, GroupName="P. Rangos por percentil")]
        public int OpacidadPct { get; set; }

        [XmlIgnore][Display(Name="Color clusters HFT", Order=13, GroupName="P. Rangos por percentil")]
        public Brush ColorClusterPct { get; set; }
        [Browsable(false)] public string ColorClusterPctSerializable { get { return Serialize.BrushToString(ColorClusterPct); } set { ColorClusterPct = Serialize.StringToBrush(value); } }

        [XmlIgnore][Display(Name="Color expansiones sin HFT", Order=14, GroupName="P. Rangos por percentil")]
        public Brush ColorVacioPct { get; set; }
        [Browsable(false)] public string ColorVacioPctSerializable { get { return Serialize.BrushToString(ColorVacioPct); } set { ColorVacioPct = Serialize.StringToBrush(value); } }

        [Display(Name="Mostrar etiquetas compactas", Order=15, GroupName="P. Rangos por percentil")]
        public bool MostrarTextoPct { get; set; }

        [Range(100, 1000000)][Browsable(false)]
        public int VelasDibujoHistorico { get; set; }
        #endregion

        #region Properties
        [Range(1, 100)]
        [Display(Name="Tick Resolution (sub-serie)", Order=1, GroupName="0. Sub-serie")]
        public int TickResolution { get; set; }

        [Range(2, 100)]
        [Display(Name="Min pasos del sweep", Order=1, GroupName="A. Estructura")]
        public int MinPasos { get; set; }

        [Range(1, 20)]
        [Display(Name="Max rango tick por vela", Order=2, GroupName="A. Estructura")]
        public int MaxRangoTickPorVela { get; set; }

        [Range(0, 10)]
        [Display(Name="Fallos tolerados", Order=3, GroupName="A. Estructura")]
        public int FallosTolerados { get; set; }

        [Display(Name="Filtro direccion estricto (cuerpo real)", Order=4, GroupName="A. Estructura")]
        public bool FiltroDireccionEstricto { get; set; }

        [Range(0, 100)]
        [Display(Name="Min altura del sweep (ticks)", Order=5, GroupName="A. Estructura")]
        public int MinSweepTicks { get; set; }

        [Range(0, 100)]
        [Display(Name="Max retroceso del sweep (ticks)", Order=6, GroupName="A. Estructura")]
        public int MaxRetrocesoTicks { get; set; }

        [Range(0, 100)]
        [Display(Name="Retroceso % de la Altura", Order=7, GroupName="A. Estructura")]
        public int RetrocesoPctHeight { get; set; }

        [Range(1, 2000)]
        [Display(Name="Max avgMs (entre ticks)", Order=1, GroupName="B. Filtros temporales")]
        public int MaxAvgMs { get; set; }

        [Range(50, 10000)]
        [Display(Name="Max totalMs (duracion total)", Order=2, GroupName="B. Filtros temporales")]
        public int MaxTotalMs { get; set; }

        [Range(10, 5000)]
        [Display(Name="Max pausa entre ticks (ms)", Order=3, GroupName="B. Filtros temporales")]
        public int MaxPausaMs { get; set; }

        [Range(0, 50000)]
        [Display(Name="Min velocidad volumen (contratos/seg)", Order=1, GroupName="C. Filtros volumen")]
        public int MinVolumeRate { get; set; }

        [Range(0, 100000)]
        [Display(Name="Min volumen total (contratos)", Order=2, GroupName="C. Filtros volumen")]
        public int MinTotalVolume { get; set; }

        [Range(1, 100)]
        [Display(Name="Bucket PREDATOR avgMs <=", Order=1, GroupName="D. Buckets")]
        public int PredatorAvgMs { get; set; }

        [Range(1, 200)]
        [Display(Name="Bucket ULTRA avgMs <=", Order=2, GroupName="D. Buckets")]
        public int UltraAvgMs { get; set; }

        [Display(Name="Mostrar zonas ABSORB", Order=1, GroupName="DA. Absorcion")]
        public bool MostrarAbsorb { get; set; }

        [Range(2, 100)]
        [Display(Name="Min pasos ABSORB", Order=2, GroupName="DA. Absorcion")]
        public int MinAbsorbPasos { get; set; }

        [Range(1, 5000)]
        [Display(Name="Extension dibujo zonas HFT (barras)", Order=1, GroupName="E. Visual")]
        public int ExtensionDibujo { get; set; }

        [Range(1, 100)]
        [Display(Name="Opacidad zonas HFT", Order=2, GroupName="E. Visual")]
        public int Opacidad { get; set; }

        [Display(Name="Mostrar etiqueta de zona HFT", Order=3, GroupName="E. Visual")]
        public bool MostrarTexto { get; set; }

        [XmlIgnore]
        [Display(Name="Color PREDATOR", Order=4, GroupName="E. Visual")]
        public Brush ColorPredator { get; set; }
        [Browsable(false)] public string ColorPredatorSerializable
        { get { return Serialize.BrushToString(ColorPredator); } set { ColorPredator = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color ULTRA", Order=5, GroupName="E. Visual")]
        public Brush ColorUltra { get; set; }
        [Browsable(false)] public string ColorUltraSerializable
        { get { return Serialize.BrushToString(ColorUltra); } set { ColorUltra = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color bull (Fast)", Order=6, GroupName="E. Visual")]
        public Brush ColorBull { get; set; }
        [Browsable(false)] public string ColorBullSerializable
        { get { return Serialize.BrushToString(ColorBull); } set { ColorBull = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color bear (Fast)", Order=7, GroupName="E. Visual")]
        public Brush ColorBear { get; set; }
        [Browsable(false)] public string ColorBearSerializable
        { get { return Serialize.BrushToString(ColorBear); } set { ColorBear = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color ABSORB", Order=8, GroupName="E. Visual")]
        public Brush ColorAbsorb { get; set; }
        [Browsable(false)] public string ColorAbsorbSerializable
        { get { return Serialize.BrushToString(ColorAbsorb); } set { ColorAbsorb = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color texto", Order=9, GroupName="E. Visual")]
        public Brush ColorTexto { get; set; }
        [Browsable(false)] public string ColorTextoSerializable
        { get { return Serialize.BrushToString(ColorTexto); } set { ColorTexto = Serialize.StringToBrush(value); } }

        [Display(Name="Modo Exportacion Puro (sin render)", Order=0, GroupName="F. Database")]
        public bool ModoExportacionPuro { get; set; }

        [Display(Name="Enable DB Logging", Order=1, GroupName="F. Database")]
        public bool EnableDbLogging { get; set; }

        [Display(Name="DB Path", Order=2, GroupName="F. Database")]
        public string DbPath { get; set; }
        #endregion

        #region Compatibilidad con plantillas previas
        [Browsable(false)] public int ExpVentanaBars { get; set; }
        [Browsable(false)] public int PctRecomputeBars { get; set; }
        [Browsable(false)] public bool MostrarVacios { get; set; }
        [Browsable(false)] public int VoidBinTicks { get; set; }
        [Browsable(false)] public int VoidMinAltoTicks { get; set; }
        [Browsable(false)] public int VoidMinAnchoBars { get; set; }
        [Browsable(false)] public int VoidLookbackBars { get; set; }
        [Browsable(false)] public int VoidRecomputeBars { get; set; }
        [Browsable(false)] public int VoidExtensionBars { get; set; }
        [Browsable(false)] public bool VoidExigirTouch { get; set; }
        [Browsable(false)] public int VoidOpacidad { get; set; }
        [XmlIgnore][Browsable(false)] public Brush ColorVoid { get; set; }
        [Browsable(false)] public string ColorVoidSerializable { get { return Serialize.BrushToString(ColorVoid); } set { ColorVoid = Serialize.StringToBrush(value); } }
        [Browsable(false)] public int VoidMax { get; set; }
        [Browsable(false)] public bool VoidDebug { get; set; }
        [Browsable(false)] public bool MostrarClusters { get; set; }
        [Browsable(false)] public int MinOverlapRectangulos { get; set; }
        [XmlIgnore][Browsable(false)] public Brush ColorCluster { get; set; }
        [Browsable(false)] public string ColorClusterSerializable { get { return Serialize.BrushToString(ColorCluster); } set { ColorCluster = Serialize.StringToBrush(value); } }
        [XmlIgnore][Browsable(false)] public Brush ColorBordeCluster { get; set; }
        [Browsable(false)] public string ColorBordeClusterSerializable { get { return Serialize.BrushToString(ColorBordeCluster); } set { ColorBordeCluster = Serialize.StringToBrush(value); } }
        [Browsable(false)] public int OpacidadCluster { get; set; }
        [Browsable(false)] public bool ExtenderClusterHastaZonaActual { get; set; }
        [Browsable(false)] public bool MostrarTextoCluster { get; set; }
        [Browsable(false)] public bool DibujarPocCluster { get; set; }
        #endregion
    }
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private HFTZonesNQRangosPct[] cacheHFTZonesNQRangosPct;
		public HFTZonesNQRangosPct HFTZonesNQRangosPct()
		{
			return HFTZonesNQRangosPct(Input);
		}

		public HFTZonesNQRangosPct HFTZonesNQRangosPct(ISeries<double> input)
		{
			if (cacheHFTZonesNQRangosPct != null)
				for (int idx = 0; idx < cacheHFTZonesNQRangosPct.Length; idx++)
					if (cacheHFTZonesNQRangosPct[idx] != null &&  cacheHFTZonesNQRangosPct[idx].EqualsInput(input))
						return cacheHFTZonesNQRangosPct[idx];
			return CacheIndicator<HFTZonesNQRangosPct>(new HFTZonesNQRangosPct(), input, ref cacheHFTZonesNQRangosPct);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.HFTZonesNQRangosPct HFTZonesNQRangosPct()
		{
			return indicator.HFTZonesNQRangosPct(Input);
		}

		public Indicators.HFTZonesNQRangosPct HFTZonesNQRangosPct(ISeries<double> input )
		{
			return indicator.HFTZonesNQRangosPct(input);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.HFTZonesNQRangosPct HFTZonesNQRangosPct()
		{
			return indicator.HFTZonesNQRangosPct(Input);
		}

		public Indicators.HFTZonesNQRangosPct HFTZonesNQRangosPct(ISeries<double> input )
		{
			return indicator.HFTZonesNQRangosPct(input);
		}
	}
}

#endregion
