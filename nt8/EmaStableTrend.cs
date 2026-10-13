// EmaStableTrend.cs v2 — zonas de tendencia "tipo trendline" a partir de una EMA (NinjaTrader 8).
//
// IDEA: una trendline por picos/toques es dificil de detectar; una EMA es mas permisiva y permite programar las interacciones.
// ZONA = periodo en el que, medido sobre ventanas moviles (todo en cocientes o en unidades de ATR, sin ticks fijos):
//   (1) la EMA conserva direccion:   |EMA[t]-EMA[t-K]| / suma|dEMA| >= MinEmaEfficiency     y   |EMA[t]-EMA[t-K]| >= MinEmaDriftAtr * ATR * sqrt(K)
//   (2) el precio vive del lado de la tendencia: fraccion de las ultimas M barras con close del lado >= MinSideFraction
//   (3) la distancia precio-EMA es estable: desvio(g)/|media(g)| <= MaxGapCV, y |media(g)| >= MinGapAtr * ATR   (g = close-EMA)
//   Se mantiene HoldBars barras tras dejar de cumplirse (evita que una zona se parta por una barra).
// LONGITUD DE LA ZONA (lo que importa para operar): la zona solo se CONFIRMA (State = +1/-1) cuando lleva MinZoneBars barras seguidas
//   y (si MinMovePoints > 0) el precio recorrio al menos esos puntos desde el inicio de la zona. Antes de eso State = 0.
// ATRIBUTOS por zona (plots): Length (barras desde el inicio), MovePts (puntos recorridos), SlopeAtr (pendiente de la EMA en ATR por barra, con signo),
//   Peaks (picos aproximados: veces que el precio retrocede >= 35% de la distancia media a la EMA y vuelve a hacer un nuevo extremo a favor).
//   Sirven para clasificar tipos: mas/menos empinadas (SlopeAtr), con mas/menos picos (Peaks), cortas/largas (Length).
// CAUSALIDAD: Calculate=OnBarClose; el estado en la barra t usa solo datos <= t. La linea azul se dibuja desde el inicio retroactivo de la zona
//   (anotacion, NO disponible antes de la confirmacion). Para usarlo como filtro, usar solo el plot State.
// PRESETS (calibrados sobre la historia de NQ 25 ticks, EMA 200; ver docs/research/ema_trend/): 1 Pocas (~6% de las barras), 2 Normal (~16%), 3 Muchas (~28%). 0 = parametros manuales.
// ATR aqui = media simple de (High-Low) en AtrPeriod barras (la misma que se uso al calibrar). NO es evidencia de edge: solo detecta regimenes.

#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Xml.Serialization;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class EmaStableTrend : Indicator
	{
		private EMA ema;
		private SMA rangeAvg;

		private int    rawDir;          // direccion cruda (con hold) en la barra anterior
		private int    runStart;        // CurrentBar del inicio de la zona cruda
		private int    lastCondBar;     // ultima barra en que se cumplieron las condiciones
		private int    lastCondDir;
		private int    segCounter;
		private string curTag;
		private bool   confirmed;
		private double lastMu;
		private int    peaks;
		private double extreme, trough;
		private bool   retraced;
		private double runStartClose;

		// parametros efectivos (despues de aplicar el preset)
		private int    pM, pK, pHold;
		private double pF, pEr, pCv, pDriftAtr, pDminAtr;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name        = "EmaStableTrend";
				Description = "Zonas de tendencia estable respecto de una EMA (tipo trendline), con longitud minima y atributos.";
				Calculate   = Calculate.OnBarClose;
				IsOverlay   = true;
				DisplayInDataBox = false;
				PaintPriceMarkers = false;

				EmaPeriod        = 200;
				AtrPeriod        = 100;
				Preset           = 2;
				MinZoneBars      = 120;
				MinMovePoints    = 0;

				WindowBars       = 200;
				SlopeBars        = 150;
				MinEmaEfficiency = 0.7;
				MinEmaDriftAtr   = 0.8;
				MinSideFraction  = 0.95;
				MaxGapCV         = 0.5;
				MinGapAtr        = 2.0;
				HoldBars         = 66;

				LineWidth        = 2;
				LineBrush        = System.Windows.Media.Brushes.CornflowerBlue;

				AddPlot(new Stroke(System.Windows.Media.Brushes.Transparent, 1), PlotStyle.Line, "State");
				AddPlot(new Stroke(System.Windows.Media.Brushes.Transparent, 1), PlotStyle.Line, "Length");
				AddPlot(new Stroke(System.Windows.Media.Brushes.Transparent, 1), PlotStyle.Line, "MovePts");
				AddPlot(new Stroke(System.Windows.Media.Brushes.Transparent, 1), PlotStyle.Line, "SlopeAtr");
				AddPlot(new Stroke(System.Windows.Media.Brushes.Transparent, 1), PlotStyle.Line, "Peaks");
			}
			else if (State == State.DataLoaded)
			{
				ema      = EMA(EmaPeriod);
				rangeAvg = SMA(Range(), AtrPeriod);
				rawDir = 0; segCounter = 0; curTag = null; confirmed = false; lastCondBar = -1000000; lastCondDir = 0;
				ApplyPreset();
			}
		}

		private void ApplyPreset()
		{
			pM = WindowBars; pK = SlopeBars; pHold = HoldBars; pF = MinSideFraction; pEr = MinEmaEfficiency; pCv = MaxGapCV; pDriftAtr = MinEmaDriftAtr; pDminAtr = MinGapAtr;
			if (Preset == 1)      { pM = 200; pK = 150; pF = 0.95; pEr = 0.7; pCv = 0.3; pDriftAtr = 0.8; pDminAtr = 2.0; pHold = 66; }
			else if (Preset == 2) { pM = 200; pK = 150; pF = 0.95; pEr = 0.7; pCv = 0.5; pDriftAtr = 0.8; pDminAtr = 2.0; pHold = 66; }
			else if (Preset == 3) { pM = 150; pK = 100; pF = 0.90; pEr = 0.7; pCv = 0.5; pDriftAtr = 0.5; pDminAtr = 2.0; pHold = 50; }
		}

		protected override void OnBarUpdate()
		{
			for (int i = 0; i < 5; i++) Values[i][0] = 0;
			int need = Math.Max(Math.Max(pM, pK), Math.Max(EmaPeriod, AtrPeriod)) + 2;
			if (CurrentBar < need) return;

			double mu; int dir;
			bool ok = ConditionsOk(out mu, out dir);
			if (ok) { lastCondBar = CurrentBar; lastCondDir = dir; lastMu = mu; }

			int rawNow = (CurrentBar - lastCondBar <= pHold) ? lastCondDir : 0;      // hold: sigue activa HoldBars barras tras la ultima vez que se cumplio

			if (rawNow != 0 && rawNow != rawDir)                                     // zona nueva (o cambio de direccion)
			{
				runStart = CurrentBar - pM + 1;                                     // inicio retroactivo: la ventana que la probo
				runStartClose = Close[Math.Min(pM - 1, CurrentBar)];
				segCounter++; curTag = "EST_" + segCounter.ToString(CultureInfo.InvariantCulture);
				confirmed = false; peaks = 0; extreme = 0; trough = 0; retraced = false;
			}
			rawDir = rawNow;
			if (rawNow == 0) { confirmed = false; return; }

			int length = CurrentBar - runStart + 1;
			double move = Math.Abs(Close[0] - runStartClose);                               // puntos de precio
			UpdatePeaks(rawNow);

			if (!confirmed && length >= MinZoneBars && (MinMovePoints <= 0 || move >= MinMovePoints))
				confirmed = true;

			if (confirmed)
			{
				Values[0][0] = rawNow;
				Values[1][0] = length;
				Values[2][0] = move;
				double atr = rangeAvg[0];
				Values[3][0] = atr > 0 ? (ema[0] - ema[Math.Min(pK, CurrentBar)]) / pK / atr : 0;
				Values[4][0] = peaks;
				DrawSegment();
			}
		}

		// Condiciones sobre la ventana [t-M+1, t]; replica 'state' de edgelab/research/ema_zones.py
		private bool ConditionsOk(out double mu, out int dir)
		{
			mu = 0; dir = 0;
			double atr = rangeAvg[0];
			if (atr <= 0) return false;

			double disp = ema[0] - ema[pK];
			dir = disp > 0 ? 1 : (disp < 0 ? -1 : 0);
			if (dir == 0) return false;

			double sumDe = 0;
			for (int i = 0; i < pK; i++) sumDe += Math.Abs(ema[i] - ema[i + 1]);
			if (sumDe <= 0) return false;
			if (Math.Abs(disp) / sumDe < pEr) return false;
			if (Math.Abs(disp) < pDriftAtr * atr * Math.Sqrt(pK)) return false;

			double sg = 0, sgg = 0; int up = 0, dn = 0;
			for (int i = 0; i < pM; i++)
			{
				double g = Close[i] - ema[i];
				sg += g; sgg += g * g;
				if (g > 0) up++; else if (g < 0) dn++;
			}
			mu = sg / pM;
			if (Math.Abs(mu) < pDminAtr * atr) return false;
			double sd = Math.Sqrt(Math.Max(sgg / pM - mu * mu, 0));
			if (pCv > 0 && sd / Math.Max(Math.Abs(mu), 1e-9) > pCv) return false;
			if (dir > 0) return mu > 0 && (double)up / pM >= pF;
			return mu < 0 && (double)dn / pM >= pF;
		}

		// picos aproximados: retroceso >= 35% de la distancia media y nuevo extremo a favor
		private void UpdatePeaks(int dir)
		{
			double gd = dir * (Close[0] - ema[0]);                      // distancia a favor de la tendencia
			double thr = 0.35 * Math.Abs(lastMu);
			if (extreme == 0 && trough == 0) { extreme = gd; trough = gd; return; }
			if (gd > extreme) { if (retraced) { peaks++; retraced = false; } extreme = gd; trough = gd; }
			else
			{
				if (gd < trough) trough = gd;
				if (extreme - trough >= thr) retraced = true;
			}
		}

		private void DrawSegment()
		{
			if (curTag == null) return;
			int startAgo = CurrentBar - runStart;
			if (startAgo < 0 || startAgo > CurrentBar) return;
			double y0 = ema[startAgo] + lastMu;
			double y1 = ema[0] + lastMu;
			Draw.Line(this, curTag, false, startAgo, y0, 0, y1, LineBrush, DashStyleHelper.Solid, LineWidth);
		}

		#region Properties
		[NinjaScriptProperty] [Range(2, 5000)]
		[Display(Name = "EMA Period", Order = 1, GroupName = "1. Base")]
		public int EmaPeriod { get; set; }

		[NinjaScriptProperty] [Range(2, 5000)]
		[Display(Name = "ATR Period (media de High-Low)", Order = 2, GroupName = "1. Base")]
		public int AtrPeriod { get; set; }

		[NinjaScriptProperty] [Range(0, 3)]
		[Display(Name = "Preset (0 manual, 1 Pocas, 2 Normal, 3 Muchas)", Order = 3, GroupName = "1. Base",
			Description = "Cantidad de zonas. Los presets reemplazan los parametros de los grupos 3 y 4.")]
		public int Preset { get; set; }

		[NinjaScriptProperty] [Range(1, 5000)]
		[Display(Name = "Min Zone Bars (longitud minima)", Order = 1, GroupName = "2. Longitud de la zona",
			Description = "La zona se confirma (State != 0) cuando lleva al menos estas barras.")]
		public int MinZoneBars { get; set; }

		[NinjaScriptProperty] [Range(0.0, 100000.0)]
		[Display(Name = "Min Move Points (0 = off)", Order = 2, GroupName = "2. Longitud de la zona",
			Description = "Recorrido minimo del precio (puntos) desde el inicio de la zona para confirmarla.")]
		public double MinMovePoints { get; set; }

		[NinjaScriptProperty] [Range(10, 5000)]
		[Display(Name = "Window Bars (M)", Order = 1, GroupName = "3. Detector manual (Preset 0)")]
		public int WindowBars { get; set; }

		[NinjaScriptProperty] [Range(5, 5000)]
		[Display(Name = "Slope Bars (K)", Order = 2, GroupName = "3. Detector manual (Preset 0)")]
		public int SlopeBars { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min EMA Efficiency", Order = 3, GroupName = "3. Detector manual (Preset 0)")]
		public double MinEmaEfficiency { get; set; }

		[NinjaScriptProperty] [Range(0.0, 100.0)]
		[Display(Name = "Min EMA Drift (ATR*sqrt(K))", Order = 4, GroupName = "3. Detector manual (Preset 0)")]
		public double MinEmaDriftAtr { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min Side Fraction", Order = 5, GroupName = "3. Detector manual (Preset 0)")]
		public double MinSideFraction { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Max Gap CV (0 = off)", Order = 6, GroupName = "3. Detector manual (Preset 0)")]
		public double MaxGapCV { get; set; }

		[NinjaScriptProperty] [Range(0.0, 100.0)]
		[Display(Name = "Min Gap (ATR)", Order = 7, GroupName = "3. Detector manual (Preset 0)")]
		public double MinGapAtr { get; set; }

		[NinjaScriptProperty] [Range(0, 5000)]
		[Display(Name = "Hold Bars", Order = 8, GroupName = "3. Detector manual (Preset 0)")]
		public int HoldBars { get; set; }

		[NinjaScriptProperty] [Range(1, 10)]
		[Display(Name = "Line Width", Order = 1, GroupName = "4. Visual")]
		public int LineWidth { get; set; }

		[XmlIgnore]
		[Display(Name = "Line Color", Order = 2, GroupName = "4. Visual")]
		public System.Windows.Media.Brush LineBrush { get; set; }
		[Browsable(false)]
		public string LineBrushSerialize
		{
			get { return Serialize.BrushToString(LineBrush); }
			set { LineBrush = Serialize.StringToBrush(value); }
		}
		#endregion
	}
}
