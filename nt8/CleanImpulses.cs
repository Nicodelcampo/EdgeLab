// CleanImpulses.cs - clon de HFTZonesNQPureV4 (detector intacto) + impulsos limpios.
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

// =====================================================================
// CleanImpulses -- CLON LITERAL de HFTZonesNQPureV4 + una funcion agregada.
//
// POR QUE UN CLON Y NO UN PORT. La version anterior porteaba a mano solo la
// maquina de estados de deteccion. Compilaba, corria, y daba CERO zonas donde el
// original daba muchas. Reescribir un detector "equivalente" introduce
// divergencias que no se ven hasta que el conteo no coincide. Un clon no puede
// divergir: es el mismo codigo.
//
// LO UNICO AGREGADO es la seccion "IMPULSOS LIMPIOS" y su grupo de parametros:
//   1. parte la serie en tramos, de un pivote a su pivote OPUESTO;
//   2. se queda con el TopPct % mas largo, con corte CAUSAL (solo tramos ya
//      cerrados: usar el percentil de todo el chart seria mirar el futuro);
//   3. de esos, marca los que NO tienen NINGUNA zona nacida adentro.
//
// Solo cuenta DONDE NACIO la zona (StartBar). Ni hasta donde se extiende, ni en
// que nivel de precio esta: la regla es temporal.
//
// La ventana de nacimiento es [inicio del tramo, fin + gracia], con gracia =
// PivotRight por defecto. Ese es el retardo exacto con que se confirma un
// pivote, asi que la zona que el propio impulso genera al cerrarse cuenta como
// nacida adentro, sin mirada al futuro.
//
// NADA del detector fue tocado. Si se cambia HFTZonesNQPureV4, este archivo NO
// se entera: son dos copias.
// =====================================================================
namespace NinjaTrader.NinjaScript.Indicators
{
    public class CleanImpulses : Indicator
    {
        public enum HFTBucket { Predator, Ultra, Fast, Absorb }

        public sealed class Zone
        {
            public int    StartBar, EndBar;
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

        // ===================== IMPULSOS LIMPIOS: estado =====================
        // La version viaja en el cartel del chart, no en un string muerto: si se
        // toca la logica y no se sube, se ve en pantalla.
        private const string VERSION = "1.0.0";

        private int    ciSegIni = -1, ciSegHiBar, ciSegLoBar;
        private double ciSegHi, ciSegLo;
        // Diagnostico: "no marca nada" es ambiguo entre no haber tramos largos y
        // que todos los largos tengan una zona nacida adentro. Son dos cosas
        // distintas con arreglos distintos.
        private int ciMarcados, ciTramos, ciCortos;
        private int ciMinZonas = int.MaxValue;   // el minimo alcanzable de verdad

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

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description              = "CLON de HFTZonesNQPureV4 + impulsos limpios. Detector HFT EXCLUSIVO para NQ/MNQ con modo ABSORB + logger enriquecido (delta tick-rule, absorcion, flow). Escritura concurrente segura.";
                Name                     = "CleanImpulses";
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
                EnableDbLogging          = false;  // CLON: no duplicar filas en la base del original
                DbPath                   = @"C:\LoggerHFT\data\hft_logger_v4.sqlite";
                EnableFlowLog            = false;  // idem: el original ya lo escribe
                FlowBucketSeconds        = 1;

                MarcarImpulsos    = true;
                PivotLeft         = 3;
                PivotRight        = 3;
                TopPct            = 3;
                WindowLegs        = 200;
                MinLegTicks       = 6;
                ReversalTicks     = 3;
                GraceBars         = -1;
                MaxZonasAdentro   = 0;
                ExigirSolapePrecio = true;
                MargenPrecioTicks  = 0;
                CILogPath          = "";
                GrosorImpulso     = 3;
                ColorImpulsoUp    = Brushes.LimeGreen;
                ColorImpulsoDown  = Brushes.OrangeRed;

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
                if (EnableDbLogging) SetupDb();

            }
            else if (State == State.Terminated)
            {
                CloseDb();

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

            if (MarcarImpulsos)
            {
                ActualizarImpulsos();
                Draw.TextFixed(this, "ci_diag",
                    "CleanImpulses version=" + VERSION + ": " + ciMarcados
                    + " impulsos marcados  |  tramos="
                    + ciTramos + " lapsos sin zonas"
                    + "  de menos de " + MinLegTicks + " ticks=" + ciCortos
                    + "  zonas=" + zones.Count,
                    TextPosition.TopLeft);
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
            }
        }

        // ===================== VACIOS / EXPANSIONES =====================
        // Marca EXPANSIONES: regiones (tiempo x precio) por donde el precio PASO pero que ninguna
        // zona HFT cubre. Cada zona cuenta con su extension hacia adelante (ExtensionDibujo): si una
        // zona se proyecta y atraviesa la expansion, esta deja de marcarse. Las celdas vacias se
        // agrupan en regiones conexas y se dibuja un rectangulo (bounding box) por expansion.
        // ===================== IMPULSOS LIMPIOS =====================
        // La forma del impulso NO importa: puede ser escalera, serrucho, recta o
        // cualquier cosa. Importan dos cosas y nada mas:
        //   1. la ALTURA que alcanzo el precio;
        //   2. que en el lapso en que se formo esa altura NO haya nacido ninguna zona.
        //
        // Por eso los tramos no se construyen con pivotes ni con retrocesos: los
        // delimitan los propios NACIMIENTOS de zona. Cada nacimiento cierra el
        // tramo en curso y abre el siguiente. Lo que queda entre dos nacimientos
        // es, por definicion, un lapso sin zonas nacidas adentro; solo resta
        // medir cuanto se movio el precio ahi.
        //
        // Altura = maximo alto menos minimo bajo del lapso. La linea se dibuja del
        // extremo que ocurrio primero al que ocurrio despues, asi muestra la
        // direccion real del recorrido.
        private void ActualizarImpulsos()
        {
            int b = CurrentBars[0];

            if (ciSegIni < 0) { AbrirSegmento(b); return; }

            // ¿nacio alguna zona en esta barra?
            bool nacio = false;
            for (int i = zones.Count - 1; i >= 0; i--)
            {
                if (zones[i].StartBar < b) break;      // la lista viene en orden
                if (zones[i].StartBar == b) { nacio = true; break; }
            }

            if (!nacio)
            {
                double hi = Highs[0][0], lo = Lows[0][0];
                if (hi > ciSegHi) { ciSegHi = hi; ciSegHiBar = b; }
                if (lo < ciSegLo) { ciSegLo = lo; ciSegLoBar = b; }
                return;
            }

            CerrarSegmento(b - 1);
            AbrirSegmento(b + 1);
        }

        private void AbrirSegmento(int b)
        {
            ciSegIni = b;
            ciSegHi = double.MinValue; ciSegLo = double.MaxValue;
            ciSegHiBar = b; ciSegLoBar = b;
        }

        private void CerrarSegmento(int fin)
        {
            if (ciSegIni < 0 || fin < ciSegIni) return;
            if (ciSegHi == double.MinValue) return;

            ciTramos++;
            double altura = (ciSegHi - ciSegLo) / TickSize;
            if (altura < MinLegTicks) { ciCortos++; return; }

            ciMarcados++;
            // del extremo que ocurrio primero al que ocurrio despues
            int b0 = Math.Min(ciSegHiBar, ciSegLoBar);
            int b1 = Math.Max(ciSegHiBar, ciSegLoBar);
            double p0 = b0 == ciSegHiBar ? ciSegHi : ciSegLo;
            double p1 = b1 == ciSegHiBar ? ciSegHi : ciSegLo;

            int ba0 = CurrentBars[0] - b0;
            int ba1 = CurrentBars[0] - b1;
            if (ba0 < 0 || ba1 < 0) return;
            Draw.Line(this, "ci_" + b0 + "_" + b1, false, ba0, p0, ba1, p1,
                      p1 > p0 ? ColorImpulsoUp : ColorImpulsoDown,
                      DashStyleHelper.Solid, GrosorImpulso);
        }

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
        [NinjaScriptProperty]
        [Display(Name = "MarcarImpulsos", Order = 1, GroupName = "9. Impulsos limpios")]
        public bool MarcarImpulsos { get; set; }

        [NinjaScriptProperty] [Range(1, 100)]
        [Display(Name = "PivotLeft", Order = 2, GroupName = "9. Impulsos limpios")]
        public int PivotLeft { get; set; }

        [NinjaScriptProperty] [Range(1, 100)]
        [Display(Name = "PivotRight", Order = 3, GroupName = "9. Impulsos limpios")]
        public int PivotRight { get; set; }

        [NinjaScriptProperty] [Range(0.1, 100)]
        [Display(Name = "TopPct (% mas largo)", Order = 4, GroupName = "9. Impulsos limpios")]
        public double TopPct { get; set; }

        [NinjaScriptProperty] [Range(20, 100000)]
        [Display(Name = "WindowLegs", Order = 5, GroupName = "9. Impulsos limpios")]
        public int WindowLegs { get; set; }

        [NinjaScriptProperty] [Range(0, 1000000)]
        [Display(Name = "MinLegTicks", Order = 6, GroupName = "9. Impulsos limpios")]
        public int MinLegTicks { get; set; }

        [NinjaScriptProperty] [Range(-1, 1000)]
        [Display(Name = "GraceBars (-1 = PivotRight)", Order = 7, GroupName = "9. Impulsos limpios")]
        public int GraceBars { get; set; }

        [NinjaScriptProperty] [Range(1, 1000)]
        [Display(Name = "ReversalTicks (corta el tramo)", Order = 79, GroupName = "9. Impulsos limpios")]
        public int ReversalTicks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "CILogPath (vacio = off)", Order = 78, GroupName = "9. Impulsos limpios")]
        public string CILogPath { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "ExigirSolapePrecio", Order = 76, GroupName = "9. Impulsos limpios")]
        public bool ExigirSolapePrecio { get; set; }

        [NinjaScriptProperty] [Range(0, 1000)]
        [Display(Name = "MargenPrecioTicks", Order = 77, GroupName = "9. Impulsos limpios")]
        public int MargenPrecioTicks { get; set; }

        // 0 = la regla original (ninguna zona nacida adentro). Subirlo relaja la
        // regla de forma explicita y medible, en vez de esconderla en TopPct.
        [NinjaScriptProperty] [Range(0, 1000)]
        [Display(Name = "MaxZonasAdentro (0 = ninguna)", Order = 75, GroupName = "9. Impulsos limpios")]
        public int MaxZonasAdentro { get; set; }

        [NinjaScriptProperty] [Range(1, 20)]
        [Display(Name = "GrosorImpulso", Order = 8, GroupName = "9. Impulsos limpios")]
        public int GrosorImpulso { get; set; }

        [XmlIgnore]
        [Display(Name = "ColorImpulsoUp", Order = 9, GroupName = "9. Impulsos limpios")]
        public Brush ColorImpulsoUp { get; set; }
        [Browsable(false)]
        public string ColorImpulsoUpSerialize
        { get { return Serialize.BrushToString(ColorImpulsoUp); } set { ColorImpulsoUp = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name = "ColorImpulsoDown", Order = 10, GroupName = "9. Impulsos limpios")]
        public Brush ColorImpulsoDown { get; set; }
        [Browsable(false)]
        public string ColorImpulsoDownSerialize
        { get { return Serialize.BrushToString(ColorImpulsoDown); } set { ColorImpulsoDown = Serialize.StringToBrush(value); } }


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
    }
}
