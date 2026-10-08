// aVolZonePOI2.cs - EdgeLab 2026-10-07. Versión mejorada de aVolZonePOI.
//
// Mismo núcleo: bloques de N barras -> perfil por precio -> niveles hot (>= mediana x M) -> clusters adyacentes ->
// zona si el score del cluster supera el percentil histórico de su franja horaria.
//
// Mejoras respecto de aVolZonePOI:
//  1. El bloque se reinicia al empezar la sesión (no mezcla el cierre de una sesión con la apertura de la siguiente).
//  2. El umbral usa SÓLO las últimas N sesiones completas (no la sesión en curso, sin cola global que mezcla horas):
//     las zonas no dependen de cuántos días cargaste en el chart, salvo las primeras N sesiones de calentamiento.
//  3. Score opcional por densidad (volumen por nivel), para no favorecer zonas anchas.
//  4. Franjas en hora de Chicago (no se corren con el cambio de horario de EE.UU.).
//  5. Rápido: perfil con claves enteras, umbral ordenado una vez por sesión, y dibujo propio (SharpDX) sólo de las
//     zonas visibles, sin miles de objetos Draw.Rectangle. Sin SQLite. Sin grupos de alerta.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Gui;
using NinjaTrader.Data;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript;
#endregion

// enum en el namespace global: el código que genera NT8 (Strategies, MarketAnalyzer) tiene que verlo
public enum AVolZoneScoreMode { Suma, Densidad }

namespace NinjaTrader.NinjaScript.Indicators
{
    public class aVolZonePOI2 : Indicator
    {
        private class Zone
        {
            public int Bar;
            public int LowTick;
            public int HighTick;
            public double Score;
            // clasificación tipo orderblock (se decide al cerrar la ventana de OB Barras después de la creación)
            public int Seen;            // barras observadas
            public double VolIn, VolAll; // volumen operado dentro de la zona / total, en la ventana
            public int MaxAway;         // alejamiento máximo en ticks desde el borde de la zona
            public int State;           // 0 = en observación, 1 = normal, 2 = orderblock
            public double InsidePct;
            public int RacimoBar = -1;  // barra en que entró a un racimo (-1 = nunca)
        }

        private Dictionary<int, double> barProfile;     // ticks de la barra en formación (clave = precio en ticks)
        private Dictionary<int, double> blockProfile;   // perfil acumulado del bloque
        private int blockCount;
        private Dictionary<int, List<KeyValuePair<int, double>>> hist;   // franja -> (sesión, score)
        private Dictionary<int, List<double>> pending;                   // franja -> scores de la sesión en curso
        private Dictionary<int, double[]> sortedCache;
        private int sessionIndex;
        private List<Zone> zones;
        private TimeZoneInfo ctZone;
        private TimeZoneInfo localZone;
        private System.IO.StreamWriter logw;
        private SharpDX.Direct2D1.Brush dxFill, dxBorder, dxText, dxObFill, dxObBorder;
        private List<Zone> watching;
        private SharpDX.Direct2D1.Brush dxRacFill, dxRacBorder, dxRacLine;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "aVolZonePOI2";
                Description = "Zonas de volumen anómalo (aVolZonePOI mejorado): umbral por sesiones previas, bloque por sesión, render rápido.";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DrawOnPricePanel = true;
                IsSuspendedWhileInactive = true;
                DisplayInDataBox = false;
                PaintPriceMarkers = false;

                WindowBars = 10;
                MedianMultiplier = 2.0;
                MaxGapTicks = 1;
                MinClusterTicks = 2;
                ScoreMode = AVolZoneScoreMode.Suma;
                BucketMinutes = 15;
                DetectionPercentile = 95.0;
                LookbackSessions = 20;
                MinSamplesPerBucket = 20;
                ExtendBars = 250;
                ZoneColor = Brushes.DodgerBlue;
                Opacity = 20;
                ShowScore = true;
                ObBars = 100;
                ObAwayHeights = 3.0;
                ObMinAwayTicks = 8;
                ObMaxInsidePct = 2.0;   // calibrado MNQ 200t sep-2026: 21% de las zonas tiene <1% dentro, despues cae (corte natural)
                ObColor = Brushes.Red;
                RacimoMin = 5;            // "más de 4"
                RacimoBars = 135;
                RacimoAlturaTicks = 18;
                RacimoLineBars = 500;
                RacimoColor = Brushes.MediumPurple;
                LogPath = "";
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, 1);
            }
            else if (State == State.DataLoaded)
            {
                barProfile = new Dictionary<int, double>();
                blockProfile = new Dictionary<int, double>();
                blockCount = 0;
                hist = new Dictionary<int, List<KeyValuePair<int, double>>>();
                pending = new Dictionary<int, List<double>>();
                sortedCache = new Dictionary<int, double[]>();
                sessionIndex = -1;
                zones = new List<Zone>();
                watching = new List<Zone>();
                try { ctZone = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time"); } catch { ctZone = null; }
                localZone = Core.Globals.GeneralOptions.TimeZoneInfo;
                if (!string.IsNullOrWhiteSpace(LogPath))
                {
                    try
                    {
                        logw = new System.IO.StreamWriter(LogPath, false);
                        logw.WriteLine(string.Format(CultureInfo.InvariantCulture,
                            "# meta,indicator=aVolZonePOI2,version=1,instrument={0},bars={1},window={2},mult={3},gap={4},minc={5},mode={6},bucket_min={7},pct={8},lookback={9},min_samples={10}",
                            Instrument != null ? Instrument.FullName : "", BarsPeriod != null ? BarsPeriod.ToString() : "",
                            WindowBars, MedianMultiplier, MaxGapTicks, MinClusterTicks, ScoreMode, BucketMinutes,
                            DetectionPercentile, LookbackSessions, MinSamplesPerBucket));
                        logw.WriteLine("# B,bar,time,levels,best_score,bucket,session | Z,bar,time,low,high,levels,score,thresh,samples");
                    }
                    catch (Exception ex) { Print("aVolZonePOI2 log: " + ex.Message); logw = null; }
                }
            }
            else if (State == State.Terminated)
            {
                if (logw != null) { try { logw.Flush(); logw.Dispose(); } catch { } logw = null; }
                DisposeDx();
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress == 1)
            {
                double v = Volumes[1][0];
                if (v <= 0) return;
                int k = (int)Math.Round(Closes[1][0] / TickSize);
                double cur;
                barProfile[k] = barProfile.TryGetValue(k, out cur) ? cur + v : v;
                return;
            }
            if (BarsInProgress != 0) return;

            if (Bars.IsFirstBarOfSession)
            {
                CommitSession();
                blockProfile.Clear();
                blockCount = 0;
            }

            // cerrar la barra: sólo ticks dentro del rango de la barra
            int lo = (int)Math.Round(Low[0] / TickSize), hi = (int)Math.Round(High[0] / TickSize);
            foreach (var kv in barProfile)
            {
                if (kv.Key < lo || kv.Key > hi) continue;
                double cur;
                blockProfile[kv.Key] = blockProfile.TryGetValue(kv.Key, out cur) ? cur + kv.Value : kv.Value;
            }
            if (watching.Count > 0) UpdateOrderBlocks(lo, hi);
            barProfile.Clear();
            blockCount++;
            if (blockCount < WindowBars) return;
            ProcessBlock();
            blockProfile.Clear();
            blockCount = 0;
        }

        private void CommitSession()
        {
            if (sessionIndex >= 0)
            {
                foreach (var kv in pending)
                {
                    List<KeyValuePair<int, double>> l;
                    if (!hist.TryGetValue(kv.Key, out l)) { l = new List<KeyValuePair<int, double>>(); hist[kv.Key] = l; }
                    foreach (double s in kv.Value) l.Add(new KeyValuePair<int, double>(sessionIndex, s));
                }
                int minS = sessionIndex - LookbackSessions + 1;
                foreach (var l in hist.Values) l.RemoveAll(x => x.Key < minS);
                sortedCache.Clear();
            }
            pending.Clear();
            sessionIndex++;
        }

        private int Bucket()
        {
            DateTime t = Time[0];
            if (ctZone != null && localZone != null)
            {
                try { t = TimeZoneInfo.ConvertTime(t, localZone, ctZone); } catch { }
            }
            return (t.Hour * 60 + t.Minute) / Math.Max(1, BucketMinutes);
        }

        private void ProcessBlock()
        {
            int bucket = Bucket();
            double best = 0;
            int n = blockProfile.Count;
            if (n >= 3)
            {
                var keys = new int[n];
                var vols = new double[n];
                blockProfile.Keys.CopyTo(keys, 0);
                blockProfile.Values.CopyTo(vols, 0);
                Array.Sort(keys, vols);
                var sv = (double[])vols.Clone();
                Array.Sort(sv);
                double hot = sv[n / 2] * MedianMultiplier;

                double[] sorted;
                if (!sortedCache.TryGetValue(bucket, out sorted))
                {
                    List<KeyValuePair<int, double>> l;
                    if (hist.TryGetValue(bucket, out l))
                    {
                        sorted = new double[l.Count];
                        for (int i = 0; i < l.Count; i++) sorted[i] = l[i].Value;
                        Array.Sort(sorted);
                    }
                    else sorted = new double[0];
                    sortedCache[bucket] = sorted;
                }
                double thr = sorted.Length >= MinSamplesPerBucket ? Pct(sorted, DetectionPercentile / 100.0) : -1;

                // niveles hot en orden de precio; el hueco se mide en ticks de precio (como el original)
                var hotIdx = new List<int>();
                for (int i = 0; i < n; i++) if (vols[i] >= hot) hotIdx.Add(i);
                int g = 0;
                while (g < hotIdx.Count)
                {
                    int e = g;
                    while (e + 1 < hotIdx.Count && keys[hotIdx[e + 1]] - keys[hotIdx[e]] - 1 <= MaxGapTicks) e++;
                    int cnt = e - g + 1;
                    if (cnt >= MinClusterTicks)
                    {
                        double sum = 0;
                        for (int j = g; j <= e; j++) sum += vols[hotIdx[j]];
                        int lowK = keys[hotIdx[g]], highK = keys[hotIdx[e]];
                        double sc = ScoreMode == AVolZoneScoreMode.Suma ? sum : sum / (highK - lowK + 1);
                        if (sc > best) best = sc;
                        if (thr > 0 && sc >= thr)
                        {
                            var nz = new Zone { Bar = CurrentBar, LowTick = lowK, HighTick = highK, Score = sc };
                            MarkRacimo(nz);
                            zones.Add(nz);
                            if (ObBars > 0) watching.Add(nz); else nz.State = 1;
                            if (logw != null)
                                logw.WriteLine(string.Format(CultureInfo.InvariantCulture, "Z,{0},{1:yyyy-MM-dd HH:mm:ss.fff},{2},{3},{4},{5},{6},{7}",
                                    CurrentBar, Time[0], lowK * TickSize, highK * TickSize, cnt, sc, thr, sorted.Length));
                        }
                    }
                    g = e + 1;
                }
            }
            List<double> pl;
            if (!pending.TryGetValue(bucket, out pl)) { pl = new List<double>(); pending[bucket] = pl; }
            pl.Add(best);
            if (logw != null)
                logw.WriteLine(string.Format(CultureInfo.InvariantCulture, "B,{0},{1:yyyy-MM-dd HH:mm:ss.fff},{2},{3},{4},{5}",
                    CurrentBar, Time[0], n, best, bucket, sessionIndex));
        }

        // Orderblock: desde la creación, se acumula el volumen operado dentro de la zona y el total. En la PRIMERA barra
        // en que el precio queda a max(ObAwayHeights x altura, ObMinAwayTicks) ticks del borde, se decide:
        // orderblock si el volumen dentro hasta ese momento es <= ObMaxInsidePct %. Si en ObBars barras no se alejó, normal.
        // Calibrado MNQ 200t sep-2026 (815 zonas): 27% tiene <1% dentro al alejarse; entre 1% y 2% sólo 1% -> corte natural.
        private void UpdateOrderBlocks(int lo, int hi)
        {
            double tot = 0;
            foreach (var kv in barProfile) if (kv.Key >= lo && kv.Key <= hi) tot += kv.Value;
            for (int i = watching.Count - 1; i >= 0; i--)
            {
                Zone z = watching[i];
                double inside = 0;
                foreach (var kv in barProfile)
                    if (kv.Key >= lo && kv.Key <= hi && kv.Key >= z.LowTick && kv.Key <= z.HighTick) inside += kv.Value;
                z.VolIn += inside;
                z.VolAll += tot;
                int away = Math.Max(hi - z.HighTick, z.LowTick - lo);
                if (away > z.MaxAway) z.MaxAway = away;
                z.Seen++;
                int height = z.HighTick - z.LowTick + 1;
                double need = Math.Max(ObAwayHeights * height, ObMinAwayTicks);
                double insidePct = z.VolAll > 0 ? 100.0 * z.VolIn / z.VolAll : 0;
                z.InsidePct = insidePct;
                if (z.MaxAway >= need) z.State = insidePct <= ObMaxInsidePct ? 2 : 1;
                else if (z.Seen >= ObBars) z.State = 1;
                else continue;
                if (logw != null)
                    logw.WriteLine(string.Format(CultureInfo.InvariantCulture, "O,{0},{1:yyyy-MM-dd HH:mm:ss.fff},{2},{3},{4},{5:0.###},{6}",
                        CurrentBar, Time[0], z.Bar, z.LowTick * TickSize, z.Seen, insidePct, z.State));
                watching.RemoveAt(i);
            }
        }

        // Racimo: una "caja" de RacimoBars velas de ancho y RacimoAlturaTicks de alto. Al nacer una zona, si dentro de
        // una caja que la contiene nacieron al menos RacimoMin zonas (completas en la caja), todas se pintan violeta.
        // Sólo mira el pasado.
        private void MarkRacimo(Zone nz)
        {
            if (RacimoMin <= 1) return;
            var cand = new List<Zone>();
            for (int i = zones.Count - 1; i >= 0; i--)
            {
                Zone z = zones[i];
                if (nz.Bar - z.Bar > RacimoBars) break;
                cand.Add(z);
            }
            cand.Add(nz);
            // franjas posibles: cada una arranca en el piso de alguna zona y tiene que contener a la nueva
            List<Zone> best = null;
            foreach (var basez in cand)
            {
                int lo = basez.LowTick, hi = lo + RacimoAlturaTicks - 1;
                if (nz.LowTick < lo || nz.HighTick > hi) continue;
                var inside = new List<Zone>();
                foreach (var z in cand) if (z.LowTick >= lo && z.HighTick <= hi) inside.Add(z);
                if (best == null || inside.Count > best.Count) best = inside;
            }
            if (best == null || best.Count < RacimoMin) return;
            foreach (var m in best)
                if (m.RacimoBar < 0)
                {
                    m.RacimoBar = CurrentBar;
                    if (logw != null)
                        logw.WriteLine(string.Format(CultureInfo.InvariantCulture, "R,{0},{1:yyyy-MM-dd HH:mm:ss.fff},{2},{3},{4}", CurrentBar, Time[0], m.Bar, m.LowTick * TickSize, best.Count));
                }
        }

        private static double Pct(double[] s, double p)
        {
            if (s.Length == 0) return 0;
            if (s.Length == 1) return s[0];
            double r = p * (s.Length - 1);
            int lo = (int)Math.Floor(r);
            int hi = Math.Min(lo + 1, s.Length - 1);
            return s[lo] + (r - lo) * (s[hi] - s[lo]);
        }

        #region Render
        private void DisposeDx()
        {
            if (dxFill != null) { dxFill.Dispose(); dxFill = null; }
            if (dxBorder != null) { dxBorder.Dispose(); dxBorder = null; }
            if (dxText != null) { dxText.Dispose(); dxText = null; }
            if (dxObFill != null) { dxObFill.Dispose(); dxObFill = null; }
            if (dxObBorder != null) { dxObBorder.Dispose(); dxObBorder = null; }
            if (dxRacFill != null) { dxRacFill.Dispose(); dxRacFill = null; }
            if (dxRacBorder != null) { dxRacBorder.Dispose(); dxRacBorder = null; }
            if (dxRacLine != null) { dxRacLine.Dispose(); dxRacLine = null; }
        }

        public override void OnRenderTargetChanged()
        {
            DisposeDx();
            if (RenderTarget == null) return;
            try
            {
                dxFill = (ZoneColor ?? Brushes.DodgerBlue).ToDxBrush(RenderTarget);
                dxFill.Opacity = Opacity / 100f;
                dxBorder = (ZoneColor ?? Brushes.DodgerBlue).ToDxBrush(RenderTarget);
                dxBorder.Opacity = Math.Min(1f, Opacity / 100f * 2.2f);
                dxText = (ZoneColor ?? Brushes.DodgerBlue).ToDxBrush(RenderTarget);
                dxObFill = (ObColor ?? Brushes.Red).ToDxBrush(RenderTarget);
                dxObFill.Opacity = Opacity / 100f;
                dxObBorder = (ObColor ?? Brushes.Red).ToDxBrush(RenderTarget);
                dxObBorder.Opacity = Math.Min(1f, Opacity / 100f * 2.2f);
                dxRacFill = (RacimoColor ?? Brushes.MediumPurple).ToDxBrush(RenderTarget);
                dxRacFill.Opacity = Opacity / 100f;
                dxRacBorder = (RacimoColor ?? Brushes.MediumPurple).ToDxBrush(RenderTarget);
                dxRacBorder.Opacity = Math.Min(1f, Opacity / 100f * 2.2f);
                dxRacLine = (RacimoColor ?? Brushes.MediumPurple).ToDxBrush(RenderTarget);
            }
            catch { DisposeDx(); }
        }

        protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
        {
            base.OnRender(chartControl, chartScale);
            if (zones == null || zones.Count == 0 || ChartBars == null || RenderTarget == null) return;
            if (dxFill == null) OnRenderTargetChanged();
            if (dxFill == null) return;
            int from = ChartBars.FromIndex, to = ChartBars.ToIndex;
            float half = (float)chartControl.Properties.BarDistance / 2f;
            SharpDX.DirectWrite.TextFormat tf = null;
            if (ShowScore)
            {
                try { tf = (chartControl.Properties.LabelFont ?? new Gui.Tools.SimpleFont("Arial", 9)).ToDirectWriteTextFormat(); }
                catch { tf = null; }
            }
            var prev = RenderTarget.AntialiasMode;
            RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.Aliased;
            try
            {
                // las zonas están ordenadas por barra: búsqueda binaria de la primera que puede verse
                int lo = 0, hi = zones.Count;
                int minBar = from - Math.Max(ExtendBars, RacimoLineBars);
                while (lo < hi) { int mid = (lo + hi) / 2; if (zones[mid].Bar < minBar) lo = mid + 1; else hi = mid; }
                for (int i = lo; i < zones.Count; i++)
                {
                    Zone z = zones[i];
                    if (z.Bar > to) break;
                    bool racz = z.RacimoBar >= 0 && dxRacBorder != null;
                    if (racz && RacimoLineBars > 0)
                    {
                        // líneas del racimo: borde superior e inferior de la zona, RacimoLineBars velas a la derecha
                        int la = Math.Max(z.Bar, from), lb = Math.Min(z.Bar + RacimoLineBars, to);
                        if (lb >= la)
                        {
                            float lx1 = chartControl.GetXByBarIndex(ChartBars, la) - half;
                            float lx2 = chartControl.GetXByBarIndex(ChartBars, lb) + half;
                            float ly1 = chartScale.GetYByValue((z.HighTick + 0.5) * TickSize);
                            float ly2 = chartScale.GetYByValue((z.LowTick - 0.5) * TickSize);
                            RenderTarget.DrawLine(new SharpDX.Vector2(lx1, ly1), new SharpDX.Vector2(lx2, ly1), dxRacLine, 1.5f);
                            RenderTarget.DrawLine(new SharpDX.Vector2(lx1, ly2), new SharpDX.Vector2(lx2, ly2), dxRacLine, 1.5f);
                        }
                    }
                    int a = Math.Max(z.Bar, from), b = Math.Min(z.Bar + ExtendBars, to);
                    if (b < a) continue;
                    float x1 = chartControl.GetXByBarIndex(ChartBars, a) - half;
                    float x2 = chartControl.GetXByBarIndex(ChartBars, b) + half;
                    float y1 = chartScale.GetYByValue((z.HighTick + 0.5) * TickSize);
                    float y2 = chartScale.GetYByValue((z.LowTick - 0.5) * TickSize);
                    var rect = new SharpDX.RectangleF(Math.Min(x1, x2), Math.Min(y1, y2), Math.Max(1f, Math.Abs(x2 - x1)), Math.Max(1f, Math.Abs(y2 - y1)));
                    // violeta (racimo) tiene prioridad sobre rojo (OB) y azul; se pinta violeta desde el inicio de la zona
                    // (visual: en tiempo real la zona se vuelve violeta recién cuando se completa el racimo; el log guarda esa barra)
                    bool rac = z.RacimoBar >= 0 && dxRacFill != null;
                    bool ob = !rac && z.State == 2 && dxObFill != null;
                    RenderTarget.FillRectangle(rect, rac ? dxRacFill : ob ? dxObFill : dxFill);
                    RenderTarget.DrawRectangle(rect, rac ? dxRacBorder : ob ? dxObBorder : dxBorder, 1f);
                    if (tf != null && z.Bar >= from)
                    {
                        string s = ScoreMode == AVolZoneScoreMode.Suma ? ((int)z.Score).ToString() : z.Score.ToString("0.0", CultureInfo.InvariantCulture);
                        if (z.State == 2) s += "  OB " + z.InsidePct.ToString("0.0", CultureInfo.InvariantCulture) + "%";
                        else if (z.State == 1) s += "  " + z.InsidePct.ToString("0", CultureInfo.InvariantCulture) + "%";
                        using (var layout = new SharpDX.DirectWrite.TextLayout(Core.Globals.DirectWriteFactory, s, tf, 220f, tf.FontSize + 4f))
                            RenderTarget.DrawTextLayout(new SharpDX.Vector2(rect.X + 2f, rect.Y - tf.FontSize - 4f), layout, dxText);
                    }
                }
            }
            finally
            {
                RenderTarget.AntialiasMode = prev;
                if (tf != null) tf.Dispose();
            }
        }
        #endregion

        #region Properties
        [NinjaScriptProperty][Range(2, 200)]
        [Display(Name = "Window Bars", Order = 1, GroupName = "1. Detección", Description = "Barras por bloque. Se reinicia al empezar la sesión.")]
        public int WindowBars { get; set; }

        [NinjaScriptProperty][Range(1.0, 10.0)]
        [Display(Name = "Median Multiplier", Order = 2, GroupName = "1. Detección")]
        public double MedianMultiplier { get; set; }

        [NinjaScriptProperty][Range(0, 10)]
        [Display(Name = "Max Gap Ticks", Order = 3, GroupName = "1. Detección")]
        public int MaxGapTicks { get; set; }

        [NinjaScriptProperty][Range(1, 50)]
        [Display(Name = "Min Cluster Ticks", Order = 4, GroupName = "1. Detección")]
        public int MinClusterTicks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Score", Order = 5, GroupName = "1. Detección", Description = "Suma = volumen total del cluster (como el original). Densidad = volumen por nivel (no favorece zonas anchas).")]
        public AVolZoneScoreMode ScoreMode { get; set; }

        [NinjaScriptProperty][Range(1, 120)]
        [Display(Name = "Franja (minutos, hora Chicago)", Order = 1, GroupName = "2. Umbral")]
        public int BucketMinutes { get; set; }

        [NinjaScriptProperty][Range(50.0, 99.99)]
        [Display(Name = "Percentil", Order = 2, GroupName = "2. Umbral")]
        public double DetectionPercentile { get; set; }

        [NinjaScriptProperty][Range(1, 250)]
        [Display(Name = "Sesiones previas", Order = 3, GroupName = "2. Umbral", Description = "El umbral usa sólo estas sesiones completas anteriores.")]
        public int LookbackSessions { get; set; }

        [NinjaScriptProperty][Range(5, 5000)]
        [Display(Name = "Mín. muestras por franja", Order = 4, GroupName = "2. Umbral", Description = "Sin esta cantidad de bloques previos en la franja, no se marca zona.")]
        public int MinSamplesPerBucket { get; set; }

        [NinjaScriptProperty][Range(1, 50000)]
        [Display(Name = "Extender (barras)", Order = 1, GroupName = "3. Visual")]
        public int ExtendBars { get; set; }

        [XmlIgnore]
        [Display(Name = "Color", Order = 2, GroupName = "3. Visual")]
        public Brush ZoneColor { get; set; }

        [Browsable(false)]
        public string ZoneColorSerializable
        {
            get { return Serialize.BrushToString(ZoneColor); }
            set { ZoneColor = Serialize.StringToBrush(value); }
        }

        [Range(1, 100)]
        [Display(Name = "Opacidad", Order = 3, GroupName = "3. Visual")]
        public int Opacity { get; set; }

        [Display(Name = "Mostrar score", Order = 4, GroupName = "3. Visual")]
        public bool ShowScore { get; set; }

        [Range(0, 5000)]
        [Display(Name = "OB: barras de observación (0 = off)", Order = 1, GroupName = "4. Orderblock", Description = "Máximo de barras que se espera a que el precio se aleje. Si no se aleja, la zona queda normal.")]
        public int ObBars { get; set; }

        [Range(0.0, 100.0)]
        [Display(Name = "OB: alejamiento mínimo (alturas)", Order = 2, GroupName = "4. Orderblock")]
        public double ObAwayHeights { get; set; }

        [Range(0, 10000)]
        [Display(Name = "OB: alejamiento mínimo (ticks)", Order = 3, GroupName = "4. Orderblock", Description = "Piso en ticks para zonas muy finas.")]
        public int ObMinAwayTicks { get; set; }

        [Range(0.0, 100.0)]
        [Display(Name = "OB: volumen máx. dentro (%)", Order = 4, GroupName = "4. Orderblock", Description = "Porcentaje máximo del volumen de la ventana operado dentro de la zona.")]
        public double ObMaxInsidePct { get; set; }

        [XmlIgnore]
        [Display(Name = "OB: color", Order = 5, GroupName = "4. Orderblock")]
        public Brush ObColor { get; set; }

        [Browsable(false)]
        public string ObColorSerializable
        {
            get { return Serialize.BrushToString(ObColor); }
            set { ObColor = Serialize.StringToBrush(value); }
        }

        [Range(0, 50)]
        [Display(Name = "Racimo: mín. zonas (0 = off)", Order = 1, GroupName = "5. Racimo")]
        public int RacimoMin { get; set; }

        [Range(1, 100000)]
        [Display(Name = "Racimo: ventana (velas hacia atrás)", Order = 2, GroupName = "5. Racimo")]
        public int RacimoBars { get; set; }

        [Range(0, 100000)]
        [Display(Name = "Racimo: largo de las líneas (velas)", Order = 5, GroupName = "5. Racimo", Description = "Líneas en el borde superior e inferior de cada zona del racimo, hacia la derecha (0 = sin líneas).")]
        public int RacimoLineBars { get; set; }

        [Range(1, 100000)]
        [Display(Name = "Racimo: altura máx. (ticks)", Order = 3, GroupName = "5. Racimo", Description = "Todas las zonas del racimo tienen que entrar completas en una franja de este alto.")]
        public int RacimoAlturaTicks { get; set; }

        [XmlIgnore]
        [Display(Name = "Racimo: color", Order = 4, GroupName = "5. Racimo")]
        public Brush RacimoColor { get; set; }

        [Browsable(false)]
        public string RacimoColorSerializable
        {
            get { return Serialize.BrushToString(RacimoColor); }
            set { RacimoColor = Serialize.StringToBrush(value); }
        }

        [Display(Name = "Log Path (vacío = off)", Order = 1, GroupName = "9. EdgeLab export")]
        public string LogPath { get; set; }
        #endregion
    }
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private aVolZonePOI2[] cacheaVolZonePOI2;
		public aVolZonePOI2 aVolZonePOI2(int windowBars, double medianMultiplier, int maxGapTicks, int minClusterTicks, AVolZoneScoreMode scoreMode, int bucketMinutes, double detectionPercentile, int lookbackSessions, int minSamplesPerBucket, int extendBars)
		{
			return aVolZonePOI2(Input, windowBars, medianMultiplier, maxGapTicks, minClusterTicks, scoreMode, bucketMinutes, detectionPercentile, lookbackSessions, minSamplesPerBucket, extendBars);
		}

		public aVolZonePOI2 aVolZonePOI2(ISeries<double> input, int windowBars, double medianMultiplier, int maxGapTicks, int minClusterTicks, AVolZoneScoreMode scoreMode, int bucketMinutes, double detectionPercentile, int lookbackSessions, int minSamplesPerBucket, int extendBars)
		{
			if (cacheaVolZonePOI2 != null)
				for (int idx = 0; idx < cacheaVolZonePOI2.Length; idx++)
					if (cacheaVolZonePOI2[idx] != null && cacheaVolZonePOI2[idx].WindowBars == windowBars && cacheaVolZonePOI2[idx].MedianMultiplier == medianMultiplier && cacheaVolZonePOI2[idx].MaxGapTicks == maxGapTicks && cacheaVolZonePOI2[idx].MinClusterTicks == minClusterTicks && cacheaVolZonePOI2[idx].ScoreMode == scoreMode && cacheaVolZonePOI2[idx].BucketMinutes == bucketMinutes && cacheaVolZonePOI2[idx].DetectionPercentile == detectionPercentile && cacheaVolZonePOI2[idx].LookbackSessions == lookbackSessions && cacheaVolZonePOI2[idx].MinSamplesPerBucket == minSamplesPerBucket && cacheaVolZonePOI2[idx].ExtendBars == extendBars && cacheaVolZonePOI2[idx].EqualsInput(input))
						return cacheaVolZonePOI2[idx];
			return CacheIndicator<aVolZonePOI2>(new aVolZonePOI2(){ WindowBars = windowBars, MedianMultiplier = medianMultiplier, MaxGapTicks = maxGapTicks, MinClusterTicks = minClusterTicks, ScoreMode = scoreMode, BucketMinutes = bucketMinutes, DetectionPercentile = detectionPercentile, LookbackSessions = lookbackSessions, MinSamplesPerBucket = minSamplesPerBucket, ExtendBars = extendBars }, input, ref cacheaVolZonePOI2);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.aVolZonePOI2 aVolZonePOI2(int windowBars, double medianMultiplier, int maxGapTicks, int minClusterTicks, AVolZoneScoreMode scoreMode, int bucketMinutes, double detectionPercentile, int lookbackSessions, int minSamplesPerBucket, int extendBars)
		{
			return indicator.aVolZonePOI2(Input, windowBars, medianMultiplier, maxGapTicks, minClusterTicks, scoreMode, bucketMinutes, detectionPercentile, lookbackSessions, minSamplesPerBucket, extendBars);
		}

		public Indicators.aVolZonePOI2 aVolZonePOI2(ISeries<double> input , int windowBars, double medianMultiplier, int maxGapTicks, int minClusterTicks, AVolZoneScoreMode scoreMode, int bucketMinutes, double detectionPercentile, int lookbackSessions, int minSamplesPerBucket, int extendBars)
		{
			return indicator.aVolZonePOI2(input, windowBars, medianMultiplier, maxGapTicks, minClusterTicks, scoreMode, bucketMinutes, detectionPercentile, lookbackSessions, minSamplesPerBucket, extendBars);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.aVolZonePOI2 aVolZonePOI2(int windowBars, double medianMultiplier, int maxGapTicks, int minClusterTicks, AVolZoneScoreMode scoreMode, int bucketMinutes, double detectionPercentile, int lookbackSessions, int minSamplesPerBucket, int extendBars)
		{
			return indicator.aVolZonePOI2(Input, windowBars, medianMultiplier, maxGapTicks, minClusterTicks, scoreMode, bucketMinutes, detectionPercentile, lookbackSessions, minSamplesPerBucket, extendBars);
		}

		public Indicators.aVolZonePOI2 aVolZonePOI2(ISeries<double> input , int windowBars, double medianMultiplier, int maxGapTicks, int minClusterTicks, AVolZoneScoreMode scoreMode, int bucketMinutes, double detectionPercentile, int lookbackSessions, int minSamplesPerBucket, int extendBars)
		{
			return indicator.aVolZonePOI2(input, windowBars, medianMultiplier, maxGapTicks, minClusterTicks, scoreMode, bucketMinutes, detectionPercentile, lookbackSessions, minSamplesPerBucket, extendBars);
		}
	}
}

#endregion
