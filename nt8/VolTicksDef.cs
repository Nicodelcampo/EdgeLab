// VolTicksDef.cs - Marca velas con volumen excepcionalmente alto (top 0.5% por defecto)

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Media;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class VolTicksDef : Indicator
    {
        private const int ColorSteps = 9;

        private sealed class P2Quantile
        {
            private readonly double q;
            private readonly List<double> init = new List<double>(5);

            private bool initialized;
            private int count;

            private readonly double[] h = new double[5];
            private readonly double[] n = new double[5];
            private readonly double[] np = new double[5];
            private readonly double[] dn = new double[5];

            public P2Quantile(double quantile)
            {
                q = Math.Max(0.0001, Math.Min(0.9999, quantile));

                dn[0] = 0;
                dn[1] = q / 2.0;
                dn[2] = q;
                dn[3] = (1.0 + q) / 2.0;
                dn[4] = 1.0;
            }

            public void Reset()
            {
                init.Clear();
                initialized = false;
                count = 0;
                Array.Clear(h, 0, h.Length);
                Array.Clear(n, 0, n.Length);
                Array.Clear(np, 0, np.Length);
            }

            public void Add(double x)
            {
                if (!initialized)
                {
                    init.Add(x);
                    count++;
                    if (init.Count == 5)
                    {
                        init.Sort();
                        for (int i = 0; i < 5; i++)
                        {
                            h[i] = init[i];
                            n[i] = i + 1;
                        }

                        np[0] = 1;
                        np[1] = 1 + 2 * q;
                        np[2] = 1 + 4 * q;
                        np[3] = 3 + 2 * q;
                        np[4] = 5;

                        initialized = true;
                    }
                    return;
                }

                count++;

                int k;
                if (x < h[0])
                {
                    h[0] = x;
                    k = 0;
                }
                else if (x < h[1]) k = 0;
                else if (x < h[2]) k = 1;
                else if (x < h[3]) k = 2;
                else if (x <= h[4]) k = 3;
                else
                {
                    h[4] = x;
                    k = 3;
                }

                for (int i = k + 1; i < 5; i++)
                    n[i]++;

                for (int i = 0; i < 5; i++)
                    np[i] += dn[i];

                for (int i = 1; i <= 3; i++)
                {
                    double d = np[i] - n[i];
                    if ((d >= 1 && (n[i + 1] - n[i]) > 1) || (d <= -1 && (n[i - 1] - n[i]) < -1))
                    {
                        int s = Math.Sign(d);

                        double hp = Parabolic(i, s);
                        if (hp > h[i - 1] && hp < h[i + 1])
                            h[i] = hp;
                        else
                            h[i] = Linear(i, s);

                        n[i] += s;
                    }
                }
            }

            public bool IsReady => initialized;

            public int Count => count;

            public double Value => initialized ? h[2] : double.NaN;

            private double Parabolic(int i, int d)
            {
                double n0 = n[i - 1];
                double n1 = n[i];
                double n2 = n[i + 1];

                double h0 = h[i - 1];
                double h1 = h[i];
                double h2 = h[i + 1];

                double a = (n1 - n0 + d) * (h2 - h1) / (n2 - n1);
                double b = (n2 - n1 - d) * (h1 - h0) / (n1 - n0);

                return h1 + (d / (n2 - n0)) * (a + b);
            }

            private double Linear(int i, int d)
            {
                return h[i] + d * (h[i + d] - h[i]) / (n[i + d] - n[i]);
            }
        }

        private P2Quantile quantileGlobal;
        private P2Quantile quantileSession;
        private double maxRatioSeen;
        private double rollingVolumeSum;
        private int rollingVolumeSumPeriod;

        private readonly Queue<string> rectTags = new Queue<string>();
        private StreamWriter logw;   // EdgeLab: export para paridad (vacío = off)

        private static readonly Dictionary<int, Brush[]> brushCacheByOpacity = new Dictionary<int, Brush[]>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "VolTicksDef";
                Description = "Marca velas con volumen excepcionalmente alto vs promedio (umbral por percentil).";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                IsSuspendedWhileInactive = true;

                AvgPeriod = 200;
                // Top 0,25% (muy exigente)
                DetectionPercentile = 99.75;
                ExtendBars = 3000;
                MaxRectangles = 250;
                Opacity = 20;

                ResetThresholdEachSession = true;
                MinSessionSamples = 30;
                LogPath = "";
            }
            else if (State == State.DataLoaded)
            {
                quantileGlobal = new P2Quantile(DetectionPercentile / 100.0);
                quantileSession = new P2Quantile(DetectionPercentile / 100.0);
                maxRatioSeen = 0;
                rectTags.Clear();

                rollingVolumeSum = 0;
                rollingVolumeSumPeriod = 0;

                if (!string.IsNullOrWhiteSpace(LogPath))
                {
                    try
                    {
                        logw = new StreamWriter(LogPath, false);
                        logw.WriteLine(string.Format(CultureInfo.InvariantCulture,
                            "# meta,indicator=VolTicksDef,version=log1,instrument={0},bars={1},avg_period={2},percentile={3},reset_session={4},min_session_samples={5}",
                            Instrument != null ? Instrument.FullName : "", BarsPeriod != null ? BarsPeriod.ToString() : "",
                            AvgPeriod, DetectionPercentile, ResetThresholdEachSession, MinSessionSamples));
                        logw.WriteLine("bar_index,bar_close_time,first_bar_of_session,volume,avg,ratio,thr_session,n_session,thr_global,n_global,thr_used,flagged,high,low");
                    }
                    catch (Exception ex) { Print("VolTicksDef log: " + ex.Message); logw = null; }
                }
            }
            else if (State == State.Terminated)
            {
                if (logw != null) { try { logw.Flush(); logw.Dispose(); } catch { } logw = null; }
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(5, AvgPeriod))
                return;

            if (ResetThresholdEachSession && Bars != null && Bars.IsFirstBarOfSession)
            {
                quantileSession.Reset();
                maxRatioSeen = 0;
            }

            // Mantener suma móvil del volumen para evitar bucles por barra
            if (rollingVolumeSumPeriod != AvgPeriod)
            {
                rollingVolumeSum = 0;
                int initBars = Math.Min(CurrentBar + 1, AvgPeriod);
                for (int i = 0; i < initBars; i++)
                    rollingVolumeSum += Volume[i];
                rollingVolumeSumPeriod = AvgPeriod;
            }
            else
            {
                rollingVolumeSum += Volume[0];
                rollingVolumeSum -= Volume[AvgPeriod];
            }

            double avg = rollingVolumeSum / AvgPeriod;
            if (avg <= 0)
                return;

            double ratio = Volume[0] / avg;

            // Actualizar estimadores (global + sesión)
            quantileGlobal.Add(ratio);
            quantileSession.Add(ratio);

            double threshold = GetActiveThreshold();

            if (logw != null)
            {
                logw.WriteLine(string.Format(CultureInfo.InvariantCulture,
                    "{0},{1:yyyy-MM-ddTHH:mm:ss.fff},{2},{3},{4:R},{5:R},{6:R},{7},{8:R},{9},{10:R},{11},{12:R},{13:R}",
                    CurrentBar, Time[0], Bars.IsFirstBarOfSession ? 1 : 0, Volume[0], avg, ratio,
                    quantileSession.Value, quantileSession.Count, quantileGlobal.Value, quantileGlobal.Count, threshold,
                    (threshold > 0 && ratio >= threshold) ? 1 : 0, High[0], Low[0]));
            }
            if (!(threshold > 0))
                return;

            // Actualizar escala de color (máximo con decaimiento suave)
            maxRatioSeen = Math.Max(ratio, maxRatioSeen * 0.9995);
            if (maxRatioSeen < threshold)
                maxRatioSeen = threshold;

            if (ratio < threshold)
                return;

            double denom = Math.Max(1e-9, (maxRatioSeen - threshold));
            double t = Math.Max(0, Math.Min(1, (ratio - threshold) / denom));

            int opacityScaled = GetOpacityScaled(t);
            Brush fill = GetHeatBrushDiscrete(t, opacityScaled);
            Brush outline = Brushes.Transparent;

            int endBarsAgo = -Math.Abs(ExtendBars);

            string tag = "VTD_" + CurrentBar;
            Draw.Rectangle(this, tag, false,
                0, High[0],
                endBarsAgo, Low[0],
                outline, fill, opacityScaled);

            rectTags.Enqueue(tag);
            while (rectTags.Count > Math.Max(10, MaxRectangles))
            {
                string old = rectTags.Dequeue();
                RemoveDrawObject(old);
            }
        }

        private double GetActiveThreshold()
        {
            // Preferir sesión si está lista y tiene muestras suficientes
            if (ResetThresholdEachSession && quantileSession.IsReady && quantileSession.Count >= Math.Max(5, MinSessionSamples))
                return quantileSession.Value;

            if (quantileGlobal.IsReady)
                return quantileGlobal.Value;

            return double.NaN;
        }

        private int GetOpacityScaled(double t)
        {
            // Cuanto más volumen relativo (t), más opacidad.
            // Se mantiene Opacity como el máximo configurado.
            int maxOpacity = Math.Max(1, Math.Min(100, Opacity));
            int minOpacity = Math.Max(1, (int)Math.Round(maxOpacity * 0.25));
            int scaled = (int)Math.Round(minOpacity + (maxOpacity - minOpacity) * Math.Max(0, Math.Min(1, t)));
            if (scaled < 1) scaled = 1;
            if (scaled > 100) scaled = 100;
            return scaled;
        }

        private Brush GetHeatBrushDiscrete(double t, int opacity)
        {
            // 9 niveles discretos:
            //  0-2: verdes (más verde -> más amarillo)
            //  3-5: amarillos (amarillo -> naranja)
            //  6-8: rojos (naranja-rojo -> rojo)
            int areaOpacity = Math.Max(1, Math.Min(100, opacity));
            if (!brushCacheByOpacity.TryGetValue(areaOpacity, out Brush[] brushes) || brushes == null || brushes.Length != ColorSteps)
            {
                brushes = BuildBrushSteps(areaOpacity);
                brushCacheByOpacity[areaOpacity] = brushes;
            }

            int idx = (int)Math.Floor(t * ColorSteps);
            if (idx < 0) idx = 0;
            if (idx >= ColorSteps) idx = ColorSteps - 1;
            return brushes[idx];
        }

        private Brush[] BuildBrushSteps(int areaOpacity)
        {
            // Ojo: el alpha real lo controla el parámetro areaOpacity en Draw.Rectangle.
            // Acá dejamos alpha 255 para no “doble-opacar”.
            // 3 verdes
            var colors = new[]
            {
                Color.FromArgb(255, 0,   200, 0),   // verde fuerte
                Color.FromArgb(255, 80,  220, 0),   // verde amarillento
                Color.FromArgb(255, 150, 240, 0),   // lima

                // 3 amarillos
                Color.FromArgb(255, 230, 230, 0),   // amarillo
                Color.FromArgb(255, 255, 200, 0),   // amarillo cálido
                Color.FromArgb(255, 255, 150, 0),   // ámbar/naranja claro

                // 3 rojos
                Color.FromArgb(255, 255, 90,  0),   // naranja-rojo
                Color.FromArgb(255, 255, 40,  0),   // rojo fuerte
                Color.FromArgb(255, 220, 0,   0),   // rojo profundo
            };

            var brushes = new Brush[ColorSteps];
            for (int i = 0; i < ColorSteps; i++)
            {
                var b = new SolidColorBrush(colors[i]);
                b.Freeze();
                brushes[i] = b;
            }
            return brushes;
        }

        #region Properties

        [NinjaScriptProperty]
        [Range(20, 2000)]
        [Display(Name = "Avg Period", Order = 1, GroupName = "Parámetros")]
        public int AvgPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(90.0, 99.99)]
        [Display(Name = "Detection Percentile", Order = 2, GroupName = "Parámetros")]
        public double DetectionPercentile { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Reset Threshold Each Session", Order = 6, GroupName = "OrderFlow / Delta")]
        public bool ResetThresholdEachSession { get; set; }

        [NinjaScriptProperty]
        [Range(5, 500)]
        [Display(Name = "Min Session Samples", Order = 7, GroupName = "OrderFlow / Delta")]
        public int MinSessionSamples { get; set; }

        [NinjaScriptProperty]
        [Range(100, 10000)]
        [Display(Name = "Extend Bars", Order = 3, GroupName = "Parámetros")]
        public int ExtendBars { get; set; }

        [NinjaScriptProperty]
        [Range(10, 2000)]
        [Display(Name = "Max Rectangles", Order = 4, GroupName = "Parámetros")]
        public int MaxRectangles { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Opacity", Order = 5, GroupName = "Parámetros")]
        public int Opacity { get; set; }

        [Display(Name = "Log Path (vacio = off)", Order = 1, GroupName = "9. EdgeLab export")]
        public string LogPath { get; set; }

        #endregion
    }
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private VolTicksDef[] cacheVolTicksDef;
		public VolTicksDef VolTicksDef(int avgPeriod, double detectionPercentile, bool resetThresholdEachSession, int minSessionSamples, int extendBars, int maxRectangles, int opacity)
		{
			return VolTicksDef(Input, avgPeriod, detectionPercentile, resetThresholdEachSession, minSessionSamples, extendBars, maxRectangles, opacity);
		}

		public VolTicksDef VolTicksDef(ISeries<double> input, int avgPeriod, double detectionPercentile, bool resetThresholdEachSession, int minSessionSamples, int extendBars, int maxRectangles, int opacity)
		{
			if (cacheVolTicksDef != null)
				for (int idx = 0; idx < cacheVolTicksDef.Length; idx++)
					if (cacheVolTicksDef[idx] != null && cacheVolTicksDef[idx].AvgPeriod == avgPeriod && cacheVolTicksDef[idx].DetectionPercentile == detectionPercentile && cacheVolTicksDef[idx].ResetThresholdEachSession == resetThresholdEachSession && cacheVolTicksDef[idx].MinSessionSamples == minSessionSamples && cacheVolTicksDef[idx].ExtendBars == extendBars && cacheVolTicksDef[idx].MaxRectangles == maxRectangles && cacheVolTicksDef[idx].Opacity == opacity && cacheVolTicksDef[idx].EqualsInput(input))
						return cacheVolTicksDef[idx];
			return CacheIndicator<VolTicksDef>(new VolTicksDef(){ AvgPeriod = avgPeriod, DetectionPercentile = detectionPercentile, ResetThresholdEachSession = resetThresholdEachSession, MinSessionSamples = minSessionSamples, ExtendBars = extendBars, MaxRectangles = maxRectangles, Opacity = opacity }, input, ref cacheVolTicksDef);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.VolTicksDef VolTicksDef(int avgPeriod, double detectionPercentile, bool resetThresholdEachSession, int minSessionSamples, int extendBars, int maxRectangles, int opacity)
		{
			return indicator.VolTicksDef(Input, avgPeriod, detectionPercentile, resetThresholdEachSession, minSessionSamples, extendBars, maxRectangles, opacity);
		}

		public Indicators.VolTicksDef VolTicksDef(ISeries<double> input , int avgPeriod, double detectionPercentile, bool resetThresholdEachSession, int minSessionSamples, int extendBars, int maxRectangles, int opacity)
		{
			return indicator.VolTicksDef(input, avgPeriod, detectionPercentile, resetThresholdEachSession, minSessionSamples, extendBars, maxRectangles, opacity);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.VolTicksDef VolTicksDef(int avgPeriod, double detectionPercentile, bool resetThresholdEachSession, int minSessionSamples, int extendBars, int maxRectangles, int opacity)
		{
			return indicator.VolTicksDef(Input, avgPeriod, detectionPercentile, resetThresholdEachSession, minSessionSamples, extendBars, maxRectangles, opacity);
		}

		public Indicators.VolTicksDef VolTicksDef(ISeries<double> input , int avgPeriod, double detectionPercentile, bool resetThresholdEachSession, int minSessionSamples, int extendBars, int maxRectangles, int opacity)
		{
			return indicator.VolTicksDef(input, avgPeriod, detectionPercentile, resetThresholdEachSession, minSessionSamples, extendBars, maxRectangles, opacity);
		}
	}
}

#endregion
