#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.NinjaScript.Indicators;
using System.Data.SQLite;
using System.IO;
using System.Diagnostics;
using System.Linq;
using System.Globalization;
#endregion

// MTF Imbalance Detector
// Basado en el PineScript "Imbalance Detector [LuxAlgo]"
// Se asegura de usar siempre M1 como base para detectar ineficiencias,
// y dibuja las zonas en cualquier gráfico usando coordenadas temporales (DateTime).

namespace NinjaTrader.NinjaScript.Indicators
{
    public class ImbalanceDetectorLuxAlgoMTF : Indicator
    {
        private ATR atr200;
        private bool prevBullOG;
        private bool prevBearOG;

        private class ActiveImbalanceZone
        {
            public double Top;
            public double Bottom;
            public DateTime EndTime;
            public bool IsBull;
            public string SourceType;
        }
        private System.Collections.Generic.List<ActiveImbalanceZone> activeZones = new System.Collections.Generic.List<ActiveImbalanceZone>();

        // Logging variables
        private string DbPath = @"D:\AlgoProject\data\algo_features.sqlite";
        private bool tableReady = false;
        private long lastSnapshotMs = 0;
        private readonly object sync = new object();

        // ===== Export EdgeLab (paridad NT8 -> Python) =====
        // Una fila por zona en el momento de su creacion (cierre de la vela M1 que la genera) y, opcional, una fila por vela M1.
        // No cambia la deteccion ni el dibujo. Archivos nuevos en cada carga del indicador (no se mezclan corridas).
        private StreamWriter expZones;
        private StreamWriter expBars;
        private long expZoneRows, expBarRows;
        private static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        #region Properties

        // --- Logging ---
        [NinjaScriptProperty]
        [Display(Name = "Enable DB Logging", Order = 0, GroupName = "0. Logging")]
        public bool EnableDbLogging { get; set; }

        // --- Export EdgeLab ---
        [Display(Name = "Exportar zonas (CSV)", Order = 1, GroupName = "9. Export EdgeLab",
            Description = "Escribe una fila por zona OG/VI/FVG al cerrar la vela M1 que la crea (as-of), con parametros en el encabezado.")]
        public bool ExportEnabled { get; set; }

        [Display(Name = "Exportar velas M1 (CSV)", Order = 2, GroupName = "9. Export EdgeLab",
            Description = "Escribe cada vela M1 usada por el detector (OHLCV) para validar la paridad de las barras.")]
        public bool ExportM1Bars { get; set; }

        [Display(Name = "Carpeta de export", Order = 3, GroupName = "9. Export EdgeLab")]
        public string ExportFolder { get; set; }

        // --- Fair Value Gaps ---
        [NinjaScriptProperty]
        [Display(Name = "Show Fair Value Gaps (FVG)", Order = 0, GroupName = "1. Fair Value Gaps")]
        public bool ShowFVG { get; set; }

        [XmlIgnore]
        [Display(Name = "Bullish FVG color", Order = 1, GroupName = "1. Fair Value Gaps")]
        public Brush BullFVGBrush { get; set; }
        [Browsable(false)]
        public string BullFVGBrushSerialize { get { return Serialize.BrushToString(BullFVGBrush); } set { BullFVGBrush = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name = "Bearish FVG color", Order = 2, GroupName = "1. Fair Value Gaps")]
        public Brush BearFVGBrush { get; set; }
        [Browsable(false)]
        public string BearFVGBrushSerialize { get { return Serialize.BrushToString(BearFVGBrush); } set { BearFVGBrush = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty]
        [Display(Name = "FVG Min Width enabled", Order = 3, GroupName = "1. Fair Value Gaps")]
        public bool FVGUseWidth { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "FVG Min Width", Order = 4, GroupName = "1. Fair Value Gaps")]
        public double FVGGapWidth { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "FVG Width Method", Order = 5, GroupName = "1. Fair Value Gaps")]
        public ImbalanceWidthMethod FVGMethod { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Extend FVG (minutos)", Order = 6, GroupName = "1. Fair Value Gaps")]
        public int FVGExtend { get; set; }

        // --- Opening Gaps ---
        [NinjaScriptProperty]
        [Display(Name = "Show Opening Gaps (OG)", Order = 0, GroupName = "2. Opening Gaps")]
        public bool ShowOG { get; set; }

        [XmlIgnore]
        [Display(Name = "Bullish OG color", Order = 1, GroupName = "2. Opening Gaps")]
        public Brush BullOGBrush { get; set; }
        [Browsable(false)]
        public string BullOGBrushSerialize { get { return Serialize.BrushToString(BullOGBrush); } set { BullOGBrush = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name = "Bearish OG color", Order = 2, GroupName = "2. Opening Gaps")]
        public Brush BearOGBrush { get; set; }
        [Browsable(false)]
        public string BearOGBrushSerialize { get { return Serialize.BrushToString(BearOGBrush); } set { BearOGBrush = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty]
        [Display(Name = "OG Min Width enabled", Order = 3, GroupName = "2. Opening Gaps")]
        public bool OGUseWidth { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "OG Min Width", Order = 4, GroupName = "2. Opening Gaps")]
        public double OGGapWidth { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "OG Width Method", Order = 5, GroupName = "2. Opening Gaps")]
        public ImbalanceWidthMethod OGMethod { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Extend OG (minutos)", Order = 6, GroupName = "2. Opening Gaps")]
        public int OGExtend { get; set; }

        // --- Volume Imbalance ---
        [NinjaScriptProperty]
        [Display(Name = "Show Volume Imbalances (VI)", Order = 0, GroupName = "3. Volume Imbalance")]
        public bool ShowVI { get; set; }

        [XmlIgnore]
        [Display(Name = "Bullish VI color", Order = 1, GroupName = "3. Volume Imbalance")]
        public Brush BullVIBrush { get; set; }
        [Browsable(false)]
        public string BullVIBrushSerialize { get { return Serialize.BrushToString(BullVIBrush); } set { BullVIBrush = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name = "Bearish VI color", Order = 2, GroupName = "3. Volume Imbalance")]
        public Brush BearVIBrush { get; set; }
        [Browsable(false)]
        public string BearVIBrushSerialize { get { return Serialize.BrushToString(BearVIBrush); } set { BearVIBrush = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty]
        [Display(Name = "VI Min Width enabled", Order = 3, GroupName = "3. Volume Imbalance")]
        public bool VIUseWidth { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "VI Min Width", Order = 4, GroupName = "3. Volume Imbalance")]
        public double VIGapWidth { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "VI Width Method", Order = 5, GroupName = "3. Volume Imbalance")]
        public ImbalanceWidthMethod VIMethod { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Extend VI (minutos)", Order = 6, GroupName = "3. Volume Imbalance")]
        public int VIExtend { get; set; }

        // --- Near-Miss Scanner ---
        [NinjaScriptProperty]
        [Display(Name = "Show Near-Miss Diamonds", Order = 0, GroupName = "4. Escáner Near-Miss")]
        public bool ShowNearMissDiamonds { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Max Distance (Ticks)", Order = 1, GroupName = "4. Escáner Near-Miss", Description = "Distancia máxima a la zona (debe ser > 0 y <= este valor)")]
        public int MaxDistanceTicks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Min Approach (Ticks)", Order = 2, GroupName = "4. Escáner Near-Miss", Description = "Distancia mínima del impulso hacia la zona")]
        public int MinApproachTicks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Min Reaction (Ticks)", Order = 3, GroupName = "4. Escáner Near-Miss", Description = "Tamaño mínimo de la mecha de rechazo")]
        public int MinReactionTicks { get; set; }

        [XmlIgnore]
        [Display(Name = "Bullish Near-Miss Color", Order = 4, GroupName = "4. Escáner Near-Miss")]
        public Brush BullNearMissBrush { get; set; }
        [Browsable(false)]
        public string BullNearMissBrushSerialize { get { return Serialize.BrushToString(BullNearMissBrush); } set { BullNearMissBrush = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name = "Bearish Near-Miss Color", Order = 5, GroupName = "4. Escáner Near-Miss")]
        public Brush BearNearMissBrush { get; set; }
        [Browsable(false)]
        public string BearNearMissBrushSerialize { get { return Serialize.BrushToString(BearNearMissBrush); } set { BearNearMissBrush = Serialize.StringToBrush(value); } }

        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = "Imbalance Detector [LuxAlgo] - Usa motor en M1 pero marca en cualquier grafico";
                Name                                        = "ImbalanceDetectorLuxAlgoMTF";
                Calculate                                   = Calculate.OnBarClose;
                IsOverlay                                   = true;
                DisplayInDataBox                            = false;
                DrawOnPricePanel                            = true;
                DrawHorizontalGridLines                     = true;
                DrawVerticalGridLines                       = true;
                PaintPriceMarkers                           = false;
                ScaleJustification                          = ScaleJustification.Right;
                IsSuspendedWhileInactive                    = true;

                EnableDbLogging = false;

                ShowFVG         = false;
                BullFVGBrush    = MakeBrush(0x21, 0x57, 0xf3);
                BearFVGBrush    = MakeBrush(0xff, 0x11, 0x00);
                FVGUseWidth     = false;
                FVGGapWidth     = 0;
                FVGMethod       = ImbalanceWidthMethod.Points;
                FVGExtend       = 500;

                ShowOG          = true;
                BullOGBrush     = MakeBrush(0x21, 0x57, 0xf3);
                BearOGBrush     = MakeBrush(0xff, 0x11, 0x00);
                OGUseWidth      = false;
                OGGapWidth      = 0;
                OGMethod        = ImbalanceWidthMethod.Points;
                OGExtend        = 500;

                ShowVI          = true;
                BullVIBrush     = MakeBrush(0x21, 0x57, 0xf3);
                BearVIBrush     = MakeBrush(0xff, 0x11, 0x00);
                VIUseWidth      = false;
                VIGapWidth      = 0;
                VIMethod        = ImbalanceWidthMethod.Points;
                VIExtend        = 500;

                ShowNearMissDiamonds = true;
                MaxDistanceTicks     = 2;
                MinApproachTicks     = 10;
                MinReactionTicks     = 5;
                BullNearMissBrush    = Brushes.LimeGreen;
                BearNearMissBrush    = Brushes.Magenta;

                ExportEnabled        = false;
                ExportM1Bars         = true;
                ExportFolder         = @"E:\EdgeLab\data\nt8_oracles\luximb";
            }
            else if (State == State.Configure)
            {
                prevBullOG = false;
                prevBearOG = false;
                activeZones.Clear();
                
                // Siempre agregamos la serie M1 invisible para los calculos
                AddDataSeries(BarsPeriodType.Minute, 1);
            }
            else if (State == State.DataLoaded)
            {
                // Inicializamos el ATR usando la serie M1 (indice 1 o el 0 si el grafico primario es M1)
                if (BarsArray.Length > 1)
                {
                    atr200 = ATR(BarsArray[1], 200);
                }
                else
                {
                    atr200 = ATR(BarsArray[0], 200);
                }

                if (EnableDbLogging)
                {
                    EnsureTable();
                    lastSnapshotMs = 0;
                }

                if (ExportEnabled)
                    OpenExport();
            }
            else if (State == State.Terminated)
            {
                CloseExport();
            }
        }

        private void OpenExport()
        {
            try
            {
                Directory.CreateDirectory(ExportFolder);
                string inst  = Instrument.FullName.Replace(' ', '_').Replace('/', '-');
                string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss", IC);
                string bp    = BarsArray[0].BarsPeriod.ToString().Replace(' ', '_');
                string baseName = Path.Combine(ExportFolder, "luximb_" + inst + "_" + bp + "_" + stamp);
                string hdr = "# indicador=ImbalanceDetectorLuxAlgoMTF\n"
                    + "# instrumento=" + Instrument.FullName + "\n"
                    + "# tick_size=" + Instrument.MasterInstrument.TickSize.ToString("R", IC) + "\n"
                    + "# serie_primaria=" + BarsArray[0].BarsPeriod.ToString() + "\n"
                    + "# serie_deteccion=M1 (AddDataSeries Minute 1), Calculate=" + Calculate + "\n"
                    + "# reloj=Time[0] de NT8 = CIERRE de la vela, zona horaria de NT8; ts_utc_ms = Time[0] convertido a UTC por la PC\n"
                    + "# ShowOG=" + ShowOG + " OGUseWidth=" + OGUseWidth + " OGGapWidth=" + OGGapWidth.ToString("R", IC) + " OGMethod=" + OGMethod + " OGExtend=" + OGExtend + "\n"
                    + "# ShowVI=" + ShowVI + " VIUseWidth=" + VIUseWidth + " VIGapWidth=" + VIGapWidth.ToString("R", IC) + " VIMethod=" + VIMethod + " VIExtend=" + VIExtend + "\n"
                    + "# ShowFVG=" + ShowFVG + " FVGUseWidth=" + FVGUseWidth + " FVGGapWidth=" + FVGGapWidth.ToString("R", IC) + " FVGMethod=" + FVGMethod + " FVGExtend=" + FVGExtend + "\n"
                    + "# las zonas NO se borran por mitigacion: viven hasta end_time (Time + Extend minutos)\n";
                expZones = new StreamWriter(baseName + "_zones.csv", false, new System.Text.UTF8Encoding(false));
                expZones.Write(hdr);
                expZones.WriteLine("m1_bar,bar_time_nt8,ts_utc_ms,state,type,dir,top,bottom,height_ticks,extend_min,end_time_nt8,atr200,"
                    + "o0,h0,l0,c0,o1,h1,l1,c1,o2,h2,l2,c2");
                if (ExportM1Bars)
                {
                    expBars = new StreamWriter(baseName + "_m1bars.csv", false, new System.Text.UTF8Encoding(false));
                    expBars.Write(hdr);
                    expBars.WriteLine("m1_bar,bar_time_nt8,ts_utc_ms,state,open,high,low,close,volume");
                }
                expZoneRows = 0; expBarRows = 0;
                Print("[ImbalanceDetector] Export -> " + baseName + "_*.csv");
            }
            catch (Exception ex) { Print("[ImbalanceDetector] OpenExport: " + ex.Message); expZones = null; expBars = null; }
        }

        private void CloseExport()
        {
            try
            {
                if (expZones != null) { expZones.Flush(); expZones.Dispose(); expZones = null; }
                if (expBars  != null) { expBars.Flush();  expBars.Dispose();  expBars  = null; }
                if (ExportEnabled) Print("[ImbalanceDetector] Export cerrado: zonas=" + expZoneRows + " velas M1=" + expBarRows);
            }
            catch (Exception ex) { Print("[ImbalanceDetector] CloseExport: " + ex.Message); }
        }

        private static long UtcMs(DateTime t)
        {
            return new DateTimeOffset(t.ToUniversalTime()).ToUnixTimeMilliseconds();
        }

        private void ExportZone(string type, bool isBull, double top, double btm, int extendMin)
        {
            if (expZones == null) return;
            double tk = Instrument.MasterInstrument.TickSize;
            string atr = (atr200 != null && atr200.Count > 0) ? atr200[0].ToString("R", IC) : "";
            expZones.WriteLine(string.Join(",", new string[] {
                CurrentBar.ToString(IC), Time[0].ToString("yyyy-MM-dd HH:mm:ss", IC), UtcMs(Time[0]).ToString(IC), State.ToString(),
                type, isBull ? "bull" : "bear", top.ToString("R", IC), btm.ToString("R", IC), Math.Round((top - btm) / tk, 4).ToString("R", IC),
                extendMin.ToString(IC), Time[0].AddMinutes(extendMin).ToString("yyyy-MM-dd HH:mm:ss", IC), atr,
                Open[0].ToString("R", IC), High[0].ToString("R", IC), Low[0].ToString("R", IC), Close[0].ToString("R", IC),
                Open[1].ToString("R", IC), High[1].ToString("R", IC), Low[1].ToString("R", IC), Close[1].ToString("R", IC),
                Open[2].ToString("R", IC), High[2].ToString("R", IC), Low[2].ToString("R", IC), Close[2].ToString("R", IC) }));
            expZoneRows++;
            if (expZoneRows % 2000 == 0) expZones.Flush();
        }

        private static Brush MakeBrush(byte r, byte g, byte b)
        {
            SolidColorBrush br = new SolidColorBrush(Color.FromRgb(r, g, b));
            if (br.CanFreeze) br.Freeze();
            return br;
        }

        private bool CheckWidth(double top, double btm, bool useWidth, ImbalanceWidthMethod method, double width)
        {
            if (!useWidth)
                return true;

            double dist = top - btm;
            switch (method)
            {
                case ImbalanceWidthMethod.Points:  return dist > width;
                case ImbalanceWidthMethod.Percent: return (btm != 0) && (dist / btm * 100.0) > width;
                case ImbalanceWidthMethod.ATR:     return atr200 != null && dist > atr200[0] * width;
            }
            return true;
        }

        protected override void OnBarUpdate()
        {
            int m1Idx = BarsArray.Length > 1 ? 1 : 0;
            
            // ===== PRIMARY CHART (Near-Miss Scanner) =====
            if (BarsInProgress == 0)
            {
                // Logging snapshot every 30s (using chart time for historical support)
                if (EnableDbLogging)
                {
                    long currentMs = new DateTimeOffset(Time[0].ToUniversalTime()).ToUnixTimeMilliseconds();
                    if (currentMs - lastSnapshotMs >= 30000)
                    {
                        lastSnapshotMs = currentMs;
                        PersistSnapshot(Time[0], CurrentBar);
                    }
                }

                if (!ShowNearMissDiamonds || CurrentBar < 5) return;
                
                // Limpiar zonas expiradas
                activeZones.RemoveAll(z => Time[0] >= z.EndTime);

                foreach (var z in activeZones)
                {
                    // ==========================================
                    // 1. Check Support Near-Miss (Approaching z.Top from above)
                    // ==========================================
                    // ----- Caso A: Reacción en la misma vela (Mecha larga) -----
                    double dist0_Sup = Low[0] - z.Top;
                    if (dist0_Sup >= 0 && dist0_Sup <= MaxDistanceTicks * TickSize)
                    {
                        double maxHigh = High[0];
                        for (int i = 1; i <= 4; i++) maxHigh = Math.Max(maxHigh, High[i]);
                        
                        if (maxHigh - Low[0] >= MinApproachTicks * TickSize)
                        {
                            if (Close[0] - Low[0] >= MinReactionTicks * TickSize)
                            {
                                Draw.Diamond(this, "NearMissBull_" + CurrentBar + "_" + z.SourceType, false, 0, Low[0] - 2 * TickSize, BullNearMissBrush);
                            }
                        }
                    }

                    // ----- Caso B: Reacción en la siguiente vela (Vela base + Vela reversión) -----
                    double dist1_Sup = Low[1] - z.Top;
                    if (dist1_Sup >= 0 && dist1_Sup <= MaxDistanceTicks * TickSize && Low[0] > Low[1])
                    {
                        double maxHigh1 = High[1];
                        for (int i = 2; i <= 5; i++) maxHigh1 = Math.Max(maxHigh1, High[i]);

                        if (maxHigh1 - Low[1] >= MinApproachTicks * TickSize)
                        {
                            if (Close[0] - Low[1] >= MinReactionTicks * TickSize)
                            {
                                Draw.Diamond(this, "NearMissBull_" + (CurrentBar - 1) + "_" + z.SourceType, false, 1, Low[1] - 2 * TickSize, BullNearMissBrush);
                            }
                        }
                    }

                    // ==========================================
                    // 2. Check Resistance Near-Miss (Approaching z.Bottom from below)
                    // ==========================================
                    // ----- Caso A: Reacción en la misma vela (Mecha larga) -----
                    double dist0_Res = z.Bottom - High[0];
                    if (dist0_Res >= 0 && dist0_Res <= MaxDistanceTicks * TickSize)
                    {
                        double minLow = Low[0];
                        for (int i = 1; i <= 4; i++) minLow = Math.Min(minLow, Low[i]);

                        if (High[0] - minLow >= MinApproachTicks * TickSize)
                        {
                            if (High[0] - Close[0] >= MinReactionTicks * TickSize)
                            {
                                Draw.Diamond(this, "NearMissBear_" + CurrentBar + "_" + z.SourceType, false, 0, High[0] + 2 * TickSize, BearNearMissBrush);
                            }
                        }
                    }

                    // ----- Caso B: Reacción en la siguiente vela (Vela base + Vela reversión) -----
                    double dist1_Res = z.Bottom - High[1];
                    if (dist1_Res >= 0 && dist1_Res <= MaxDistanceTicks * TickSize && High[0] < High[1])
                    {
                        double minLow1 = Low[1];
                        for (int i = 2; i <= 5; i++) minLow1 = Math.Min(minLow1, Low[i]);

                        if (High[1] - minLow1 >= MinApproachTicks * TickSize)
                        {
                            if (High[1] - Close[0] >= MinReactionTicks * TickSize)
                            {
                                Draw.Diamond(this, "NearMissBear_" + (CurrentBar - 1) + "_" + z.SourceType, false, 1, High[1] + 2 * TickSize, BearNearMissBrush);
                            }
                        }
                    }
                }
            }

            // ===== M1 CHART (Imbalance Detection) =====
            if (BarsInProgress != m1Idx) return;

            if (expBars != null)
            {
                expBars.WriteLine(string.Join(",", new string[] {
                    CurrentBar.ToString(IC), Time[0].ToString("yyyy-MM-dd HH:mm:ss", IC), UtcMs(Time[0]).ToString(IC), State.ToString(),
                    Open[0].ToString("R", IC), High[0].ToString("R", IC), Low[0].ToString("R", IC), Close[0].ToString("R", IC), Volume[0].ToString("R", IC) }));
                expBarRows++;
                if (expBarRows % 20000 == 0) expBars.Flush();
            }
            
            if (CurrentBar < 3) return;

            // Las propiedades Open, High, Low, Close, Time se auto-direccionan 
            // a la serie de M1 gracias al if (BarsInProgress != m1Idx)

            double bullGapTop = Math.Min(Close[0], Open[0]);
            double bullGapBtm = Math.Max(Close[1], Open[1]);

            double bearGapTop = Math.Min(Close[1], Open[1]);
            double bearGapBtm = Math.Max(Close[0], Open[0]);

            // ===== Volume Imbalance =====
            bool bullVICond =
                Open[0]  > Close[1] &&
                High[1]  > Low[0]   &&
                Close[0] > Close[1] &&
                Open[0]  > Open[1]  &&
                High[1]  < bullGapTop;

            bool bearVICond =
                Open[0]  < Close[1] &&
                Low[1]   < High[0]  &&
                Close[0] < Close[1] &&
                Open[0]  < Open[1]  &&
                Low[1]   > bearGapBtm;

            bool bullVI = ShowVI && bullVICond && CheckWidth(bullGapTop, bullGapBtm, VIUseWidth, VIMethod, VIGapWidth);
            bool bearVI = ShowVI && bearVICond && CheckWidth(bearGapTop, bearGapBtm, VIUseWidth, VIMethod, VIGapWidth);

            if (bullVI) activeZones.Add(new ActiveImbalanceZone { Top = bullGapTop, Bottom = bullGapBtm, EndTime = Time[0].AddMinutes(VIExtend), IsBull = true, SourceType = "VI" });
            if (bearVI) activeZones.Add(new ActiveImbalanceZone { Top = bearGapTop, Bottom = bearGapBtm, EndTime = Time[0].AddMinutes(VIExtend), IsBull = false, SourceType = "VI" });

            // ===== Opening Gaps =====
            bool bullOGCond = Low[0]  > High[1];
            bool bearOGCond = High[0] < Low[1];

            bool bullOG = ShowOG && bullOGCond && CheckWidth(bullGapTop, bullGapBtm, OGUseWidth, OGMethod, OGGapWidth);
            bool bearOG = ShowOG && bearOGCond && CheckWidth(bearGapTop, bearGapBtm, OGUseWidth, OGMethod, OGGapWidth);

            if (bullOG) activeZones.Add(new ActiveImbalanceZone { Top = bullGapTop, Bottom = bullGapBtm, EndTime = Time[0].AddMinutes(OGExtend), IsBull = true, SourceType = "OG" });
            if (bearOG) activeZones.Add(new ActiveImbalanceZone { Top = bearGapTop, Bottom = bearGapBtm, EndTime = Time[0].AddMinutes(OGExtend), IsBull = false, SourceType = "OG" });

            // ===== Fair Value Gaps =====
            bool bullFVGCond = Low[0]  > High[2] && Close[1] > High[2] && !(bullOG || prevBullOG);
            bool bearFVGCond = High[0] < Low[2]  && Close[1] < Low[2]  && !(bearOG || prevBearOG);

            bool bullFVG = ShowFVG && bullFVGCond && CheckWidth(Low[0],  High[2], FVGUseWidth, FVGMethod, FVGGapWidth);
            bool bearFVG = ShowFVG && bearFVGCond && CheckWidth(Low[2],  High[0], FVGUseWidth, FVGMethod, FVGGapWidth);

            if (bullFVG) activeZones.Add(new ActiveImbalanceZone { Top = Low[0], Bottom = High[2], EndTime = Time[0].AddMinutes(FVGExtend), IsBull = true, SourceType = "FVG" });
            if (bearFVG) activeZones.Add(new ActiveImbalanceZone { Top = Low[2], Bottom = High[0], EndTime = Time[0].AddMinutes(FVGExtend), IsBull = false, SourceType = "FVG" });

            // ===== Export EdgeLab (as-of: al cierre de esta vela M1) =====
            if (expZones != null)
            {
                if (bullVI)  ExportZone("VI",  true,  bullGapTop, bullGapBtm, VIExtend);
                if (bearVI)  ExportZone("VI",  false, bearGapTop, bearGapBtm, VIExtend);
                if (bullOG)  ExportZone("OG",  true,  bullGapTop, bullGapBtm, OGExtend);
                if (bearOG)  ExportZone("OG",  false, bearGapTop, bearGapBtm, OGExtend);
                if (bullFVG) ExportZone("FVG", true,  Low[0], High[2], FVGExtend);
                if (bearFVG) ExportZone("FVG", false, Low[2], High[0], FVGExtend);
            }

            // ===== Drawing (Using barsAgo on the M1 series, NT8 handles the time projection) =====
            string tagBase = "ImbMTF_" + CurrentBar + "_";
            
            if (bullVI)
                DrawDottedRectangle(tagBase + "VIb", 1, bullGapTop, -VIExtend, bullGapBtm, BullVIBrush);

            if (bearVI)
                DrawDottedRectangle(tagBase + "VIs", 1, bearGapTop, -VIExtend, bearGapBtm, BearVIBrush);

            if (bullOG)
            {
                Draw.Rectangle(this, tagBase + "OGb", false,
                    1, bullGapTop, -OGExtend, bullGapBtm,
                    Brushes.Transparent, BullOGBrush, 50);

                Draw.Text(this, tagBase + "OGb_t", "OG",
                    (1 - OGExtend) / 2, (bullGapTop + bullGapBtm) / 2.0,
                    Brushes.White);
            }
            if (bearOG)
            {
                Draw.Rectangle(this, tagBase + "OGs", false,
                    1, bearGapTop, -OGExtend, bearGapBtm,
                    Brushes.Transparent, BearOGBrush, 50);

                Draw.Text(this, tagBase + "OGs_t", "OG",
                    (1 - OGExtend) / 2, (bearGapTop + bearGapBtm) / 2.0,
                    Brushes.White);
            }

            if (bullFVG)
            {
                double avg = (Low[0] + High[2]) / 2.0;
                Draw.Rectangle(this, tagBase + "FVGb", false,
                    2, Low[0], -FVGExtend, High[2],
                    Brushes.Transparent, BullFVGBrush, 20);
                Draw.Line(this, tagBase + "FVGb_m", false,
                    2, avg, -FVGExtend, avg,
                    BullFVGBrush, DashStyleHelper.Solid, 1);
            }
            if (bearFVG)
            {
                double avg = (Low[2] + High[0]) / 2.0;
                Draw.Rectangle(this, tagBase + "FVGs", false,
                    2, Low[2], -FVGExtend, High[0],
                    Brushes.Transparent, BearFVGBrush, 20);
                Draw.Line(this, tagBase + "FVGs_m", false,
                    2, avg, -FVGExtend, avg,
                    BearFVGBrush, DashStyleHelper.Solid, 1);
            }

            prevBullOG = bullOG;
            prevBearOG = bearOG;
        }

        private void DrawDottedRectangle(string baseTag, int startBarsAgo, double top, int endBarsAgo, double btm, Brush color)
        {
            Draw.Line(this, baseTag + "_t", false, startBarsAgo, top, endBarsAgo,   top, color, DashStyleHelper.Dot, 1);
            Draw.Line(this, baseTag + "_b", false, startBarsAgo, btm, endBarsAgo,   btm, color, DashStyleHelper.Dot, 1);
            Draw.Line(this, baseTag + "_l", false, startBarsAgo, top, startBarsAgo, btm, color, DashStyleHelper.Dot, 1);
            Draw.Line(this, baseTag + "_r", false, endBarsAgo,   top, endBarsAgo,   btm, color, DashStyleHelper.Dot, 1);
        }

        // ===================== SQLITE LOGGING =====================
        private void EnsureTable()
        {
            try
            {
                using (var conn = new SQLiteConnection("Data Source=" + DbPath + ";Version=3;"))
                {
                    conn.Open();
                    using (var cmd = new SQLiteCommand(
                        @"CREATE TABLE IF NOT EXISTS imbalance_zones (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            instrument   TEXT,
                            snapshot_ts  INTEGER,
                            source_type  TEXT,
                            is_bull      INTEGER,
                            price_top    REAL,
                            price_bottom REAL,
                            last_price   REAL,
                            tick_size    REAL
                        );
                        CREATE INDEX IF NOT EXISTS idx_imb_ts ON imbalance_zones(snapshot_ts);", conn))
                        cmd.ExecuteNonQuery();
                }
                tableReady = true;
            }
            catch (Exception ex) { Print("[ImbalanceDetector] EnsureTable: " + ex.Message); }
        }

        private void PersistSnapshot(DateTime now, int curBar)
        {
            if (!tableReady) return;

            long ms = new DateTimeOffset(now.ToUniversalTime()).ToUnixTimeMilliseconds();
            double lastPx = CurrentBars[0] >= 0 ? Closes[0][0] : 0;
            double tickSz = Instrument.MasterInstrument.TickSize;

            var zonesCopy = activeZones.ToList();
            if (zonesCopy.Count == 0) return;

            try
            {
                using (var conn = new SQLiteConnection("Data Source=" + DbPath + ";Version=3;"))
                {
                    conn.Open();
                    using (var tx = conn.BeginTransaction())
                    using (var cmd = new SQLiteCommand(
                        @"INSERT INTO imbalance_zones
                            (instrument,snapshot_ts,source_type,is_bull,price_top,price_bottom,last_price,tick_size)
                          VALUES (@inst,@ts,@st,@ib,@pt,@pb,@lp,@tk);", conn, tx))
                    {
                        foreach (var z in zonesCopy)
                        {
                            cmd.Parameters.Clear();
                            cmd.Parameters.AddWithValue("@inst", Instrument.FullName);
                            cmd.Parameters.AddWithValue("@ts", ms);
                            cmd.Parameters.AddWithValue("@st", z.SourceType);
                            cmd.Parameters.AddWithValue("@ib", z.IsBull ? 1 : 0);
                            cmd.Parameters.AddWithValue("@pt", z.Top);
                            cmd.Parameters.AddWithValue("@pb", z.Bottom);
                            cmd.Parameters.AddWithValue("@lp", lastPx);
                            cmd.Parameters.AddWithValue("@tk", tickSz);
                            cmd.ExecuteNonQuery();
                        }
                        tx.Commit();
                    }
                }
            }
            catch (Exception ex) { Print("[ImbalanceDetector] PersistSnapshot: " + ex.Message); }
        }
    }
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private ImbalanceDetectorLuxAlgoMTF[] cacheImbalanceDetectorLuxAlgoMTF;
		public ImbalanceDetectorLuxAlgoMTF ImbalanceDetectorLuxAlgoMTF(bool enableDbLogging, bool showFVG, bool fVGUseWidth, double fVGGapWidth, ImbalanceWidthMethod fVGMethod, int fVGExtend, bool showOG, bool oGUseWidth, double oGGapWidth, ImbalanceWidthMethod oGMethod, int oGExtend, bool showVI, bool vIUseWidth, double vIGapWidth, ImbalanceWidthMethod vIMethod, int vIExtend, bool showNearMissDiamonds, int maxDistanceTicks, int minApproachTicks, int minReactionTicks)
		{
			return ImbalanceDetectorLuxAlgoMTF(Input, enableDbLogging, showFVG, fVGUseWidth, fVGGapWidth, fVGMethod, fVGExtend, showOG, oGUseWidth, oGGapWidth, oGMethod, oGExtend, showVI, vIUseWidth, vIGapWidth, vIMethod, vIExtend, showNearMissDiamonds, maxDistanceTicks, minApproachTicks, minReactionTicks);
		}

		public ImbalanceDetectorLuxAlgoMTF ImbalanceDetectorLuxAlgoMTF(ISeries<double> input, bool enableDbLogging, bool showFVG, bool fVGUseWidth, double fVGGapWidth, ImbalanceWidthMethod fVGMethod, int fVGExtend, bool showOG, bool oGUseWidth, double oGGapWidth, ImbalanceWidthMethod oGMethod, int oGExtend, bool showVI, bool vIUseWidth, double vIGapWidth, ImbalanceWidthMethod vIMethod, int vIExtend, bool showNearMissDiamonds, int maxDistanceTicks, int minApproachTicks, int minReactionTicks)
		{
			if (cacheImbalanceDetectorLuxAlgoMTF != null)
				for (int idx = 0; idx < cacheImbalanceDetectorLuxAlgoMTF.Length; idx++)
					if (cacheImbalanceDetectorLuxAlgoMTF[idx] != null && cacheImbalanceDetectorLuxAlgoMTF[idx].EnableDbLogging == enableDbLogging && cacheImbalanceDetectorLuxAlgoMTF[idx].ShowFVG == showFVG && cacheImbalanceDetectorLuxAlgoMTF[idx].FVGUseWidth == fVGUseWidth && cacheImbalanceDetectorLuxAlgoMTF[idx].FVGGapWidth == fVGGapWidth && cacheImbalanceDetectorLuxAlgoMTF[idx].FVGMethod == fVGMethod && cacheImbalanceDetectorLuxAlgoMTF[idx].FVGExtend == fVGExtend && cacheImbalanceDetectorLuxAlgoMTF[idx].ShowOG == showOG && cacheImbalanceDetectorLuxAlgoMTF[idx].OGUseWidth == oGUseWidth && cacheImbalanceDetectorLuxAlgoMTF[idx].OGGapWidth == oGGapWidth && cacheImbalanceDetectorLuxAlgoMTF[idx].OGMethod == oGMethod && cacheImbalanceDetectorLuxAlgoMTF[idx].OGExtend == oGExtend && cacheImbalanceDetectorLuxAlgoMTF[idx].ShowVI == showVI && cacheImbalanceDetectorLuxAlgoMTF[idx].VIUseWidth == vIUseWidth && cacheImbalanceDetectorLuxAlgoMTF[idx].VIGapWidth == vIGapWidth && cacheImbalanceDetectorLuxAlgoMTF[idx].VIMethod == vIMethod && cacheImbalanceDetectorLuxAlgoMTF[idx].VIExtend == vIExtend && cacheImbalanceDetectorLuxAlgoMTF[idx].ShowNearMissDiamonds == showNearMissDiamonds && cacheImbalanceDetectorLuxAlgoMTF[idx].MaxDistanceTicks == maxDistanceTicks && cacheImbalanceDetectorLuxAlgoMTF[idx].MinApproachTicks == minApproachTicks && cacheImbalanceDetectorLuxAlgoMTF[idx].MinReactionTicks == minReactionTicks && cacheImbalanceDetectorLuxAlgoMTF[idx].EqualsInput(input))
						return cacheImbalanceDetectorLuxAlgoMTF[idx];
			return CacheIndicator<ImbalanceDetectorLuxAlgoMTF>(new ImbalanceDetectorLuxAlgoMTF(){ EnableDbLogging = enableDbLogging, ShowFVG = showFVG, FVGUseWidth = fVGUseWidth, FVGGapWidth = fVGGapWidth, FVGMethod = fVGMethod, FVGExtend = fVGExtend, ShowOG = showOG, OGUseWidth = oGUseWidth, OGGapWidth = oGGapWidth, OGMethod = oGMethod, OGExtend = oGExtend, ShowVI = showVI, VIUseWidth = vIUseWidth, VIGapWidth = vIGapWidth, VIMethod = vIMethod, VIExtend = vIExtend, ShowNearMissDiamonds = showNearMissDiamonds, MaxDistanceTicks = maxDistanceTicks, MinApproachTicks = minApproachTicks, MinReactionTicks = minReactionTicks }, input, ref cacheImbalanceDetectorLuxAlgoMTF);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.ImbalanceDetectorLuxAlgoMTF ImbalanceDetectorLuxAlgoMTF(bool enableDbLogging, bool showFVG, bool fVGUseWidth, double fVGGapWidth, ImbalanceWidthMethod fVGMethod, int fVGExtend, bool showOG, bool oGUseWidth, double oGGapWidth, ImbalanceWidthMethod oGMethod, int oGExtend, bool showVI, bool vIUseWidth, double vIGapWidth, ImbalanceWidthMethod vIMethod, int vIExtend, bool showNearMissDiamonds, int maxDistanceTicks, int minApproachTicks, int minReactionTicks)
		{
			return indicator.ImbalanceDetectorLuxAlgoMTF(Input, enableDbLogging, showFVG, fVGUseWidth, fVGGapWidth, fVGMethod, fVGExtend, showOG, oGUseWidth, oGGapWidth, oGMethod, oGExtend, showVI, vIUseWidth, vIGapWidth, vIMethod, vIExtend, showNearMissDiamonds, maxDistanceTicks, minApproachTicks, minReactionTicks);
		}

		public Indicators.ImbalanceDetectorLuxAlgoMTF ImbalanceDetectorLuxAlgoMTF(ISeries<double> input , bool enableDbLogging, bool showFVG, bool fVGUseWidth, double fVGGapWidth, ImbalanceWidthMethod fVGMethod, int fVGExtend, bool showOG, bool oGUseWidth, double oGGapWidth, ImbalanceWidthMethod oGMethod, int oGExtend, bool showVI, bool vIUseWidth, double vIGapWidth, ImbalanceWidthMethod vIMethod, int vIExtend, bool showNearMissDiamonds, int maxDistanceTicks, int minApproachTicks, int minReactionTicks)
		{
			return indicator.ImbalanceDetectorLuxAlgoMTF(input, enableDbLogging, showFVG, fVGUseWidth, fVGGapWidth, fVGMethod, fVGExtend, showOG, oGUseWidth, oGGapWidth, oGMethod, oGExtend, showVI, vIUseWidth, vIGapWidth, vIMethod, vIExtend, showNearMissDiamonds, maxDistanceTicks, minApproachTicks, minReactionTicks);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.ImbalanceDetectorLuxAlgoMTF ImbalanceDetectorLuxAlgoMTF(bool enableDbLogging, bool showFVG, bool fVGUseWidth, double fVGGapWidth, ImbalanceWidthMethod fVGMethod, int fVGExtend, bool showOG, bool oGUseWidth, double oGGapWidth, ImbalanceWidthMethod oGMethod, int oGExtend, bool showVI, bool vIUseWidth, double vIGapWidth, ImbalanceWidthMethod vIMethod, int vIExtend, bool showNearMissDiamonds, int maxDistanceTicks, int minApproachTicks, int minReactionTicks)
		{
			return indicator.ImbalanceDetectorLuxAlgoMTF(Input, enableDbLogging, showFVG, fVGUseWidth, fVGGapWidth, fVGMethod, fVGExtend, showOG, oGUseWidth, oGGapWidth, oGMethod, oGExtend, showVI, vIUseWidth, vIGapWidth, vIMethod, vIExtend, showNearMissDiamonds, maxDistanceTicks, minApproachTicks, minReactionTicks);
		}

		public Indicators.ImbalanceDetectorLuxAlgoMTF ImbalanceDetectorLuxAlgoMTF(ISeries<double> input , bool enableDbLogging, bool showFVG, bool fVGUseWidth, double fVGGapWidth, ImbalanceWidthMethod fVGMethod, int fVGExtend, bool showOG, bool oGUseWidth, double oGGapWidth, ImbalanceWidthMethod oGMethod, int oGExtend, bool showVI, bool vIUseWidth, double vIGapWidth, ImbalanceWidthMethod vIMethod, int vIExtend, bool showNearMissDiamonds, int maxDistanceTicks, int minApproachTicks, int minReactionTicks)
		{
			return indicator.ImbalanceDetectorLuxAlgoMTF(input, enableDbLogging, showFVG, fVGUseWidth, fVGGapWidth, fVGMethod, fVGExtend, showOG, oGUseWidth, oGGapWidth, oGMethod, oGExtend, showVI, vIUseWidth, vIGapWidth, vIMethod, vIExtend, showNearMissDiamonds, maxDistanceTicks, minApproachTicks, minReactionTicks);
		}
	}
}

#endregion
