// EmaStableTrend.cs — periodos con EMA direccional y distancia precio-EMA ESTABLE (NinjaTrader 8).
//
// QUE DETECTA
//   Ventanas de W barras en las que, a la vez:
//     (1) la EMA conserva direccion:    ER_ema = |EMA[t]-EMA[t-W]| / suma|dEMA|  >= MinEmaEfficiency
//                                        (1 = monotona; ~0 = serrucho)
//     (2) la EMA es tendencia de verdad: |EMA[t]-EMA[t-W]| / (ATR*sqrt(W))       >= MinEmaDrift
//                                        (desplazamiento vs. escala de ruido de un random walk)
//     (3) el precio vive del lado de la tendencia: fraccion de barras con
//         sign(close-EMA) == sign(pendiente EMA)                                  >= MinSideFraction
//     (4) la distancia g = close-EMA es CONSTANTE:
//         - sin deriva:  |pendiente OLS de g| * W / |media(g)|                    <= MaxGapDrift
//           (el gap no se ensancha ni se achica mas de esa fraccion de su media)
//         - sin ruido:   desvio de g alrededor de su recta OLS / |media(g)|       <= MaxGapCV
//         - lejos de la EMA: |media(g)| >= MinGapAtr * ATR  (no es "precio pegado a la EMA")
//     (5) la media del gap tiene el signo de la tendencia (precio debajo en baja, arriba en suba).
//   Todo se mide en unidades de ATR o en cocientes: sin parametros en puntos ni ticks.
//
// CAUSALIDAD
//   Calculate = OnBarClose; la senal en la barra t usa solo datos <= t. El INICIO dibujado del
//   segmento se fija W-1 barras atras de la primera deteccion (es la ventana que lo probo): es
//   una anotacion retroactiva, NO una senal disponible antes de la barra de deteccion. Si se
//   usa como filtro de contexto, usar solo Values[0] (estado), nunca el inicio del segmento.
//   El segmento termina cuando pasan WindowBars/4 barras sin cumplirse (histeresis) y el
//   extremo final se recorta a la ultima barra que si cumplia.
//
// LINEA AZUL: recta de (EMA[inicio]+media(gap)) a (EMA[fin]+media(gap)), paralela a la EMA.
// PLOT 0 "State": +1 tendencia alcista estable, -1 bajista estable, 0 nada.
// Los umbrales son un punto de partida SIN calibrar sobre tus ejemplos marcados: ajustar mirando
// el chart (ver notas en la respuesta). No es evidencia de edge.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class EmaStableTrend : Indicator
	{
		private EMA ema;
		private ATR atr;

		private bool   active;
		private int    segStartBar;      // CurrentBar absoluto del inicio
		private int    lastOkBar;
		private double lastMu;           // media del gap en la ultima barra OK
		private int    segCounter;
		private string curTag;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name        = "EmaStableTrend";
				Description = "Detecta periodos con EMA direccional y distancia precio-EMA estable y constante.";
				Calculate   = Calculate.OnBarClose;
				IsOverlay   = true;
				DisplayInDataBox = false;
				PaintPriceMarkers = false;

				EmaPeriod         = 200;
				WindowBars        = 300;
				AtrPeriod         = 100;

				MinEmaEfficiency  = 0.85;
				MinEmaDrift       = 1.2;
				MinSideFraction   = 0.97;
				MaxGapDrift       = 0.35;
				MaxGapCV          = 0.45;
				MinGapAtr         = 0.5;

				LineWidth         = 2;
				LineBrush         = System.Windows.Media.Brushes.CornflowerBlue;

				AddPlot(new Stroke(System.Windows.Media.Brushes.Transparent, 1), PlotStyle.Line, "State");
			}
			else if (State == State.DataLoaded)
			{
				ema = EMA(EmaPeriod);
				atr = ATR(AtrPeriod);
				active = false; segCounter = 0; curTag = null;
			}
		}

		protected override void OnBarUpdate()
		{
			Values[0][0] = 0;
			int W = WindowBars;
			if (CurrentBar < Math.Max(W, Math.Max(EmaPeriod, AtrPeriod)) + 1)
				return;

			double mu, unit;
			int dir;
			bool ok = WindowOk(W, out mu, out unit, out dir);

			if (ok)
			{
				if (!active)
				{
					active = true;
					segStartBar = CurrentBar - W + 1;   // anotacion retroactiva (ver cabecera)
					segCounter++;
					curTag = "EST_" + segCounter.ToString(CultureInfo.InvariantCulture);
				}
				lastOkBar = CurrentBar;
				lastMu = mu;
				DrawSegment(CurrentBar, mu);
			}
			else if (active)
			{
				if (CurrentBar - lastOkBar > W / 4)
				{
					active = false;
					DrawSegment(lastOkBar, lastMu);   // recorta el extremo a la ultima barra valida
				}
				else
					DrawSegment(CurrentBar, lastMu);
			}

			if (active)
			{
				double slope = ema[0] - ema[Math.Min(W - 1, CurrentBar)];
				Values[0][0] = slope > 0 ? 1 : (slope < 0 ? -1 : 0);
			}
		}

		// Evalua la ventana [CurrentBar-W+1, CurrentBar]. O(W) por barra.
		private bool WindowOk(int W, out double mu, out double unit, out int dir)
		{
			mu = 0; unit = atr[0]; dir = 0;
			if (unit <= 0) return false;

			double e0 = ema[W - 1], e1 = ema[0];
			double disp = e1 - e0;
			dir = disp > 0 ? 1 : (disp < 0 ? -1 : 0);
			if (dir == 0) return false;

			double sumDe = 0, Sg = 0, Sgg = 0, Sxg = 0;
			int sideCount = 0;
			for (int k = 0; k < W; k++)
			{
				int back = W - 1 - k;                    // barras atras del elemento k (k=0 mas viejo)
				double e = ema[back];
				double g = Close[back] - e;
				if (k > 0) sumDe += Math.Abs(e - ema[back + 1]);
				Sg += g; Sgg += g * g; Sxg += k * g;
				if ((g > 0 && dir > 0) || (g < 0 && dir < 0)) sideCount++;
			}
			if (sumDe <= 0) return false;

			double er    = Math.Abs(disp) / sumDe;
			double drift = Math.Abs(disp) / (unit * Math.Sqrt(W));
			double side  = (double)sideCount / W;
			if (er < MinEmaEfficiency || drift < MinEmaDrift || side < MinSideFraction)
				return false;

			double Sx  = W * (W - 1) / 2.0;
			double Sxx = (W - 1.0) * W * (2.0 * W - 1.0) / 6.0;
			double den = W * Sxx - Sx * Sx;
			double slopeG = (W * Sxg - Sx * Sg) / den;
			mu = Sg / W;
			double sse = Sgg - Sg * Sg / W - slopeG * (Sxg - Sx * Sg / W);
			double sig = Math.Sqrt(Math.Max(sse, 0) / Math.Max(1, W - 2));

			double amu = Math.Abs(mu);
			if (amu < MinGapAtr * unit) return false;
			if ((mu > 0) != (dir > 0)) return false;
			if (Math.Abs(slopeG) * W / amu > MaxGapDrift) return false;
			if (sig / amu > MaxGapCV) return false;
			return true;
		}

		private void DrawSegment(int endBar, double mu)
		{
			if (curTag == null) return;
			int startAgo = CurrentBar - segStartBar;
			int endAgo   = CurrentBar - endBar;
			if (startAgo < 0 || startAgo > CurrentBar) return;
			double y0 = ema[startAgo] + mu;
			double y1 = ema[endAgo] + mu;
			Draw.Line(this, curTag, false, startAgo, y0, endAgo, y1, LineBrush, DashStyleHelper.Solid, LineWidth);
		}

		#region Properties

		[NinjaScriptProperty] [Range(2, 5000)]
		[Display(Name = "EMA Period", Order = 1, GroupName = "1. Base")]
		public int EmaPeriod { get; set; }

		[NinjaScriptProperty] [Range(20, 5000)]
		[Display(Name = "Window Bars (W)", Order = 2, GroupName = "1. Base",
			Description = "Largo minimo del periodo estable. Mas grande = segmentos mas largos y menos frecuentes.")]
		public int WindowBars { get; set; }

		[NinjaScriptProperty] [Range(2, 5000)]
		[Display(Name = "ATR Period (unidad)", Order = 3, GroupName = "1. Base")]
		public int AtrPeriod { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min EMA Efficiency", Order = 1, GroupName = "2. Direccion de la EMA",
			Description = "|desplazamiento EMA| / suma|cambios EMA| en la ventana. 1 = monotona.")]
		public double MinEmaEfficiency { get; set; }

		[NinjaScriptProperty] [Range(0.0, 100.0)]
		[Display(Name = "Min EMA Drift (ATR*sqrt(W))", Order = 2, GroupName = "2. Direccion de la EMA",
			Description = "Desplazamiento de la EMA en unidades de ATR*sqrt(W). Filtra EMAs planas.")]
		public double MinEmaDrift { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min Side Fraction", Order = 3, GroupName = "2. Direccion de la EMA",
			Description = "Fraccion de barras con el precio del lado de la tendencia respecto de la EMA.")]
		public double MinSideFraction { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Max Gap Drift", Order = 1, GroupName = "3. Distancia constante",
			Description = "Maxima deriva de la distancia precio-EMA dentro de la ventana, como fraccion de su media.")]
		public double MaxGapDrift { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Max Gap CV", Order = 2, GroupName = "3. Distancia constante",
			Description = "Maximo desvio de la distancia (alrededor de su recta) / media. Menor = mas estricta.")]
		public double MaxGapCV { get; set; }

		[NinjaScriptProperty] [Range(0.0, 100.0)]
		[Display(Name = "Min Gap (ATR)", Order = 3, GroupName = "3. Distancia constante",
			Description = "Distancia media minima a la EMA en ATRs; evita marcar precio pegado a la EMA.")]
		public double MinGapAtr { get; set; }

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
