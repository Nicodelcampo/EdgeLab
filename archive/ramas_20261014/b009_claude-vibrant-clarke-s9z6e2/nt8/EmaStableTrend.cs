// EmaStableTrend.cs v3.3 (defaults 'largas y permisivas', Preset 0 = manual; sin validar en historia al momento de escribirlo, ver docs/research/ema_trend/) — zonas de tendencia "tipo trendline" a partir de una EMA (NinjaTrader 8).
//
// IDEA: una trendline por picos/toques es dificil de detectar; una EMA es mas permisiva y permite programar las interacciones.
// ZONA = periodo en el que, medido sobre ventanas moviles (todo en cocientes o en unidades de ATR, sin ticks fijos):
//   (1) la EMA conserva direccion:   |EMA[t]-EMA[t-K]| / suma|dEMA| >= MinEmaEfficiency     y   |EMA[t]-EMA[t-K]| >= MinEmaDriftAtr * ATR * sqrt(K)
//   (2) el precio vive del lado de la tendencia: fraccion de las ultimas M barras con close del lado >= MinSideFraction
//   (3) DISTANCIA CONSTANTE (definicion del usuario): el promedio de los puntos en que el precio MAS SE ALEJA de la EMA y el de los puntos en que MAS SE ACERCA son relativamente constantes
//       (coeficiente de variacion de cada serie de extremos <= MaxFarCv / MaxNearCv; se evalua sobre la zona, ver EnvelopeOk). Ademas |media(close-EMA)| >= MinGapAtr * ATR.
//   Se mantiene HoldBars barras tras dejar de cumplirse (evita que una zona se parta por una barra).
// LINEA DE TENDENCIA (v3): la linea azul es una TANGENTE como la dibuja un humano, no la EMA desplazada: en baja une maximos y el precio queda por DEBAJO; en suba une minimos
//   y el precio queda por ENCIMA (desde uno de los 2 pivotes mas extremos del primer tramo de la zona; el precio puede cruzarla en <= ViolFraction de las barras). Debe tocar >= MinTouches pivotes
//   (|dist| <= TouchTolAtr*ATR). Se recalcula cada RefitBars barras y la zona TERMINA cuando el cierre rompe la linea mas de BreakAtr*ATR. La zona solo se confirma si hay una tangente valida.
//   Referencia: edgelab/research/ema_zones.py::fit_trendline (verificada contra UNA linea trazada a mano por el usuario: misma pendiente; el precio no la cruza).
// LONGITUD DE LA ZONA (lo que importa para operar): la zona solo se CONFIRMA (State = +1/-1) cuando lleva MinZoneBars barras seguidas
//   y (si MinMovePoints > 0) el precio recorrio al menos esos puntos desde el inicio de la zona. Antes de eso State = 0.
// ATRIBUTOS por zona (plots): Length (barras desde el inicio), MovePts (puntos recorridos), SlopeAtr (pendiente de la EMA en ATR por barra, con signo),
//   Peaks (= numero de toques de la tangente).
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
		private double runStartClose;
		private bool   lineValid, broken;
		private int    fitStart;               // CurrentBar absoluto del inicio de la ventana de ajuste (runStart - ExtendBars)
		private int    lineI, lastFitBar;      // lineI: indice del ancla relativo al inicio de la zona
		private double lineSlope, lineH0;      // pendiente por barra y valor en el ancla (en el espacio h: High en baja, -Low en suba)

		// parametros efectivos (despues de aplicar el preset)
		private int    pM, pK, pHold;
		private double pF, pEr, pCv, pDriftAtr, pDminAtr, pFarCv, pNearCv;

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
				Preset           = 0;
				MinZoneBars      = 150;
				MinMovePoints    = 0;
				PivotBars        = 5;
				TouchTolAtr      = 0.3;
				ViolFraction     = 0.05;
				ExtendBars       = 150;
				MinExtentAtr     = 10;
				MaxMeanDistAtr   = 4;
				MaxDistAtr       = 10;
				MinTouches       = 3;
				BreakAtr         = 1.0;
				RefitBars        = 10;

				WindowBars       = 150;
				SlopeBars        = 100;
				MinEmaEfficiency = 0.6;
				MinEmaDriftAtr   = 0.5;
				MinSideFraction  = 0.9;
				MaxGapCV         = 0.0;
				MaxFarCv         = 0.6;
				MaxNearCv        = 0.7;
				EnvPivotBars     = 10;
				MinGapAtr        = 2.0;
				HoldBars         = 100;

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
			pM = WindowBars; pK = SlopeBars; pHold = HoldBars; pF = MinSideFraction; pEr = MinEmaEfficiency; pCv = MaxGapCV; pDriftAtr = MinEmaDriftAtr; pDminAtr = MinGapAtr; pFarCv = MaxFarCv; pNearCv = MaxNearCv;
			if (Preset == 1)      { pM = 200; pK = 150; pF = 0.95; pEr = 0.7; pCv = 0; pFarCv = 0.3; pNearCv = 0.4; pDriftAtr = 0.8; pDminAtr = 2.0; pHold = 66; }
			else if (Preset == 2) { pM = 200; pK = 150; pF = 0.95; pEr = 0.7; pCv = 0; pFarCv = 0.4; pNearCv = 0.5; pDriftAtr = 0.8; pDminAtr = 2.0; pHold = 66; }
			else if (Preset == 3) { pM = 150; pK = 100; pF = 0.90; pEr = 0.7; pCv = 0; pFarCv = 0.6; pNearCv = 0.7; pDriftAtr = 0.5; pDminAtr = 2.0; pHold = 50; }
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
				fitStart = Math.Max(0, runStart - ExtendBars);                      // se busca el ancla tambien ANTES de la zona detectada: asi se marca todo el recorrido
				segCounter++; curTag = "EST_" + segCounter.ToString(CultureInfo.InvariantCulture);
				confirmed = false; peaks = 0; lineValid = false; broken = false; lastFitBar = -1000000;
			}
			rawDir = rawNow;
			if (rawNow == 0) { confirmed = false; return; }

			int length = CurrentBar - runStart + 1;
			double move = Math.Abs(Close[0] - runStartClose);                               // puntos de precio
			if (broken) return;
			int nfit = CurrentBar - fitStart + 1;
			if (length >= MinZoneBars && (CurrentBar - lastFitBar >= RefitBars || !lineValid))
			{
				lastFitBar = CurrentBar;
				lineValid = FitTrendline(rawNow, nfit) && EnvelopeOk(rawNow, nfit - lineI);                // la distancia constante se mide desde el ancla
			}
			if (lineValid && BrokenLine(rawNow, nfit)) { broken = true; confirmed = false; return; }

			if (!confirmed && lineValid && length >= MinZoneBars && (MinMovePoints <= 0 || move >= MinMovePoints))
				confirmed = true;
			if (!lineValid) confirmed = false;

			if (confirmed)
			{
				Values[0][0] = rawNow;
				Values[1][0] = CurrentBar - (fitStart + lineI) + 1;                // largo desde el ancla (todo el recorrido marcado)
				Values[2][0] = move;
				double atr = rangeAvg[0];
				Values[3][0] = atr > 0 ? (ema[0] - ema[Math.Min(pK, CurrentBar)]) / pK / atr : 0;
				Values[4][0] = peaks;
				DrawSegment(rawNow, nfit);
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

		// h[k] (k=0 inicio de la zona): High en baja, -Low en suba. Tangente por envolvente convexa desde pivotes extremos del primer tramo.
		private double H(int dir, int k, int n)
		{
			int ago = n - 1 - k;
			return dir < 0 ? High[ago] : -Low[ago];
		}

		private bool FitTrendline(int dir, int n)
		{
			int p = PivotBars;
			double atr = rangeAvg[0];
			double tol = TouchTolAtr * atr;
			if (n < 30 || atr <= 0) return false;
			double[] h = new double[n];
			for (int k = 0; k < n; k++) h[k] = H(dir, k, n);

			System.Collections.Generic.List<int> pv = new System.Collections.Generic.List<int>();
			for (int i = 0; i < n - p; i++)
			{
				int lo = Math.Max(0, i - p), hi = i + p;
				double mx = h[lo]; int cnt = 0;
				for (int k = lo; k <= hi; k++) { if (h[k] > mx) mx = h[k]; }
				for (int k = lo; k <= hi; k++) { if (h[k] == h[i]) cnt++; }
				if (h[i] == mx && cnt == 1) pv.Add(i);
			}
			// anclas: los 12 pivotes mas altos dentro del primer 50% de la zona
			System.Collections.Generic.List<int> cand = new System.Collections.Generic.List<int>();
			foreach (int k in pv) if (k <= 0.5 * n) cand.Add(k);
			cand.Sort((a, b) => h[b].CompareTo(h[a]));
			if (cand.Count > 12) cand.RemoveRange(12, cand.Count - 12);

			bool found = false; int bi = 0; double bsl = 0; int bestTouches = 0;
			foreach (int i in cand)                                                // anclas por extremidad: la primera que tenga una recta valida gana
			{
				int bestSpan = -1; int bt = 0; int bj = -1; double bs = 0;
				foreach (int j in pv)
				{
					if (j < i + 10) continue;
					double sl = (h[j] - h[i]) / (j - i);
					if (sl >= 0) continue;                                         // la tangente de una resistencia bajista debe bajar
					int viol = 0;
					for (int k = i; k < n; k++)
						if (h[k] > h[i] + sl * (k - i) + tol) viol++;
					if (viol > ViolFraction * (n - i)) continue;                   // el precio solo puede cruzarla ocasionalmente
					int touches = 0, last = i;
					foreach (int k in pv)
						if (k >= i && Math.Abs(h[i] + sl * (k - i) - h[k]) <= tol) { touches++; if (k > last) last = k; }
					if (touches < MinTouches) continue;
					double extent = Math.Abs(sl) * (n - 1 - i);                          // desplazamiento de la linea en ATR: descarta lineas cortas/planas
					if (extent < MinExtentAtr * atr) continue;
					double sumDist = 0, maxDist = 0;
					for (int k = i; k < n; k++)
					{
						double dk = h[i] + sl * (k - i) - h[k];                          // >0: precio del lado correcto
						sumDist += Math.Abs(dk);
						if (dk > maxDist) maxDist = dk;
					}
					if (sumDist / (n - i) > MaxMeanDistAtr * atr) continue;              // linea floja: el precio anda lejos de ella
					if (maxDist > MaxDistAtr * atr) continue;                            // tendencia deforme: en algun tramo el precio se aleja demasiado
					int span = last - i;
					if (touches > bt || (touches == bt && span > bestSpan)) { bt = touches; bestSpan = span; bj = j; bs = sl; }
				}
				if (bj >= 0) { found = true; bi = i; bsl = bs; bestTouches = bt; break; }
			}
			if (!found) return false;
			lineI = bi; lineSlope = bsl; lineH0 = h[bi]; peaks = bestTouches;
			return true;
		}

		// distancia constante: extremos de g = distancia a favor de la tendencia (EMA-close en baja, close-EMA en suba) en la zona
		private bool EnvelopeOk(int dir, int n)
		{
			if (pFarCv <= 0 && pNearCv <= 0) return true;
			int q = EnvPivotBars;
			double[] g = new double[n];
			for (int k = 0; k < n; k++)
			{
				int ago = n - 1 - k;
				g[k] = dir < 0 ? ema[ago] - Close[ago] : Close[ago] - ema[ago];
			}
			double fs = 0, fss = 0, ns = 0, nss = 0; int fn = 0, nn = 0;
			for (int i = 0; i < n - q; i++)
			{
				int lo = Math.Max(0, i - q), hi = i + q;
				double mx = g[lo], mn = g[lo]; int cmx = 0, cmn = 0;
				for (int k = lo; k <= hi; k++) { if (g[k] > mx) mx = g[k]; if (g[k] < mn) mn = g[k]; }
				for (int k = lo; k <= hi; k++) { if (g[k] == g[i]) { cmx++; cmn++; } }
				if (g[i] == mx && cmx == 1) { fs += g[i]; fss += g[i] * g[i]; fn++; }
				if (g[i] == mn && cmn == 1) { ns += g[i]; nss += g[i] * g[i]; nn++; }
			}
			if (fn < 2 || nn < 2) return false;
			double fm = fs / fn, nm = ns / nn;
			if (fm <= 0 || nm <= 0) return false;
			double fcv = Math.Sqrt(Math.Max(fss / fn - fm * fm, 0)) / fm;
			double ncv = Math.Sqrt(Math.Max(nss / nn - nm * nm, 0)) / nm;
			if (pFarCv > 0 && fcv > pFarCv) return false;
			if (pNearCv > 0 && ncv > pNearCv) return false;
			return true;
		}

		private double LineH(int n)                                                   // valor de la tangente (espacio h) en la barra actual
		{
			return lineH0 + lineSlope * ((n - 1) - lineI);
		}

		private bool BrokenLine(int dir, int n)
		{
			double atr = rangeAvg[0];
			double l = LineH(n);
			if (dir < 0) return Close[0] > l + BreakAtr * atr || (l - Close[0]) > MaxDistAtr * atr;        // baja: rompe por arriba o el precio se aleja demasiado por debajo
			return Close[0] < -l - BreakAtr * atr || (Close[0] + l) > MaxDistAtr * atr;                      // suba: rompe por abajo o se aleja demasiado por arriba
		}

		private void DrawSegment(int dir, int n)
		{
			if (curTag == null || !lineValid) return;
			int startAgo = CurrentBar - (fitStart + lineI);
			if (startAgo < 0 || startAgo > CurrentBar) return;
			double y0 = dir < 0 ? lineH0 : -lineH0;
			double l  = LineH(n);
			double y1 = dir < 0 ? l : -l;
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

		[NinjaScriptProperty] [Range(2, 50)]
		[Display(Name = "Pivot Bars", Order = 3, GroupName = "2. Longitud de la zona", Description = "Un pivote es un maximo/minimo local en +-N barras.")]
		public int PivotBars { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Touch Tolerance (ATR)", Order = 4, GroupName = "2. Longitud de la zona", Description = "Un pivote 'toca' la linea si esta a menos de esta distancia (en ATR).")]
		public double TouchTolAtr { get; set; }

		[NinjaScriptProperty] [Range(0, 5000)]
		[Display(Name = "Extend Bars (busqueda hacia atras)", Order = 12, GroupName = "2. Longitud de la zona", Description = "Barras antes del inicio detectado donde se busca el verdadero extremo de arranque de la linea (para marcar todo el recorrido).")]
		public int ExtendBars { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1000.0)]
		[Display(Name = "Min Extent (ATR)", Order = 9, GroupName = "2. Longitud de la zona", Description = "Desplazamiento minimo de la linea en ATR. Descarta lineas cortas o casi planas (capturas del usuario: buenas >= 12, malas <= 7).")]
		public double MinExtentAtr { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1000.0)]
		[Display(Name = "Max Mean Distance (ATR)", Order = 10, GroupName = "2. Longitud de la zona", Description = "Distancia media maxima entre el precio y la linea (descarta lineas flojas).")]
		public double MaxMeanDistAtr { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1000.0)]
		[Display(Name = "Max Distance (ATR)", Order = 11, GroupName = "2. Longitud de la zona", Description = "Distancia maxima precio-linea en cualquier punto; si se supera la tendencia es 'deforme' y la zona termina.")]
		public double MaxDistAtr { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Max Violation Fraction", Order = 8, GroupName = "2. Longitud de la zona", Description = "Fraccion maxima de barras que pueden cruzar la linea (mas que la tolerancia).")]
		public double ViolFraction { get; set; }

		[NinjaScriptProperty] [Range(2, 20)]
		[Display(Name = "Min Touches", Order = 5, GroupName = "2. Longitud de la zona", Description = "Toques minimos de la tangente (incluye el ancla).")]
		public int MinTouches { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Break (ATR)", Order = 6, GroupName = "2. Longitud de la zona", Description = "La zona termina cuando el cierre rompe la linea mas que esto.")]
		public double BreakAtr { get; set; }

		[NinjaScriptProperty] [Range(1, 500)]
		[Display(Name = "Refit Bars", Order = 7, GroupName = "2. Longitud de la zona", Description = "Cada cuantas barras se recalcula la tangente.")]
		public int RefitBars { get; set; }

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

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Max Far CV (0 = off)", Order = 9, GroupName = "3. Detector manual (Preset 0)", Description = "Variacion maxima (desvio/media) de las distancias a la EMA en los puntos en que el precio mas se aleja.")]
		public double MaxFarCv { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Max Near CV (0 = off)", Order = 10, GroupName = "3. Detector manual (Preset 0)", Description = "Idem para los puntos en que el precio mas se acerca a la EMA.")]
		public double MaxNearCv { get; set; }

		[NinjaScriptProperty] [Range(2, 100)]
		[Display(Name = "Envelope Pivot Bars", Order = 11, GroupName = "3. Detector manual (Preset 0)", Description = "Un extremo de distancia es el maximo/minimo local en +-N barras.")]
		public int EnvPivotBars { get; set; }

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
