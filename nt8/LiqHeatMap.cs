#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Text;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.Tools;
#endregion

// LiqHeatMap v1.0 -- mapa de intensidad de zonas por NIVEL DE PRECIO.
// Espejo de edgelab/bridge/indicators/liqheat.py
//
// LA IDEA
//   En vez de dibujar cada zona por separado --que satura la pantalla-- se
//   ACUMULAN POR NIVEL DE PRECIO. Cada nivel recibe la suma de los pesos de las
//   zonas que lo cubren y se pinta como una franja horizontal de ANCHO COMPLETO
//   cuya OPACIDAD es esa intensidad.
//   CADA ZONA APORTA UN KERNEL TRIANGULAR, no una caja plana. La primera version
//   sumaba cajas: con muchas zonas sobre los ~20 niveles que ZB muestra en
//   pantalla, todos los ticks cubiertos quedaban con intensidad casi identica y el
//   mapa salia BINARIO -- un bloque saturado y huecos blancos, sin gradacion. El
//   kernel hace que dos zonas cercanas den dos picos con un valle en el medio.
//
//   Lo que se mira entonces no son las zonas: son los HUECOS. Un nivel con poca
//   acumulacion es un tramo por el que el precio pasa sin resistencia.
//
// COMO MUEREN LAS ZONAS -- Y COMO NO
//   NO MUEREN POR DISTANCIA. Es una decision explicita: una zona lejos del precio
//   sigue siendo inventario en el libro, y que el precio este lejos no la consume.
//   Mueren lenta y progresivamente por dos vias:
//     TIEMPO  -- decaimiento exponencial con HalfLifeBars. La literatura lo
//                respalda: arXiv 2101.07410 mide que la probabilidad de rebote
//                DECAE con el tiempo.
//     TOQUES  -- cada visita consume inventario. TouchDecay es el factor que
//                queda despues de cada toque.
//   peso = peso_base * 2^(-edad/HalfLife) * TouchDecay^toques
//   Una zona rota --cierre a traves-- aporta BrokenWeight, por defecto 0.
//
// LA CALIBRACION, RESUELTA POR CONSTRUCCION
//   "Sale demasiado claro o demasiado opaco" no se arregla adivinando un numero
//   absoluto: la intensidad depende de cuantas zonas haya, y eso cambia con el
//   instrumento, la resolucion y el momento. Se NORMALIZA contra un PERCENTIL de
//   las intensidades vivas (NormalizePct), asi el mapa se autoescala.
//   MaxIntensity > 0 fuerza escala fija, para comparar dos corridas entre si.
//
// El mapa es el ESTADO ACTUAL, por eso las franjas ocupan todo el ancho en vez de
// arrancar donde nacio cada zona.

namespace NinjaTrader.NinjaScript.Indicators
{
	public class LiqHeatMap : Indicator
	{
		private class Pivot { public int Bar; public long Tick; }
		private class Zone
		{
			public bool IsHigh;
			public long Lo, Hi;              // rango de ticks que ocupa
			public int CreatedBar;
			public int NPivots;
			public int Touches;
			public string State = "ACTIVE";  // ACTIVE / SWEPT / BROKEN
			public long FarEdge;
			public int Tol;
			public bool Dentro;
		}

		private List<long> _hi, _lo, _cl;
		private List<Pivot> _grpHi, _grpLo;
		private List<Zone> _zones;
		private int _sessionIndex = -1;
		private StreamWriter _log;
		private bool _logFailed;
		private SharpDX.Direct2D1.Brush _dxHeat;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "LiqHeatMap";
				Description = "Intensidad acumulada de zonas por nivel de precio; los huecos son lo informativo";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				// --- deteccion de zonas (mismo modelo que LiqPoolZones) ---
				PivotLeft = 2;
				PivotRight = 2;
				EqTolerancePct = 0.10;
				MinPivots = 2;
				MaxSpanBars = 500;
				LiquidityBandTicks = 2;

				// --- decaimiento ---
				HalfLifeBars = 500;
				TouchDecay = 0.70;
				SweptWeight = 0.5;
				BrokenWeight = 0.0;
				WeightByPivots = true;
				MaxZonesTracked = 4000;
				KernelWidthTicks = 6;
				UseKernel = true;

				// --- escala y dibujo ---
				NormalizePct = 95;
				MaxIntensity = 0;
				MinOpacity = 2;
				MaxOpacity = 55;
				Gamma = 1.0;
				HeatColor = Brushes.MediumPurple;
				EventLogPath = "";
			}
			else if (State == State.DataLoaded)
			{
				_hi = new List<long>(); _lo = new List<long>(); _cl = new List<long>();
				_grpHi = new List<Pivot>(); _grpLo = new List<Pivot>();
				_zones = new List<Zone>();
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (_log != null) { try { _log.Flush(); _log.Close(); } catch { } _log = null; }
				if (_dxHeat != null) { _dxHeat.Dispose(); _dxHeat = null; }
			}
		}

		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				string dir = Path.GetDirectoryName(EventLogPath);
				if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
				_log = new StreamWriter(EventLogPath, false, new UTF8Encoding(false));
				_log.AutoFlush = true;
				_log.WriteLine("# meta,indicator=LiqHeatMap,version=1.0"
					+ ",instrument=" + Instrument.FullName
					+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
					+ ",pivot_left=" + PivotLeft + ",pivot_right=" + PivotRight
					+ ",eq_tolerance_pct=" + EqTolerancePct.ToString(CultureInfo.InvariantCulture)
					+ ",min_pivots=" + MinPivots
					+ ",half_life_bars=" + HalfLifeBars
					+ ",touch_decay=" + TouchDecay.ToString(CultureInfo.InvariantCulture)
					+ ",swept_weight=" + SweptWeight.ToString(CultureInfo.InvariantCulture)
					+ ",broken_weight=" + BrokenWeight.ToString(CultureInfo.InvariantCulture)
					+ ",kernel_width_ticks=" + KernelWidthTicks
					+ ",use_kernel=" + UseKernel
					+ ",dies_by_distance=false,write_mode=overwrite");
				_log.WriteLine("bar_index,bar_close_time_utc,session_index,tick,intensity");
			}
			catch { _log = null; _logFailed = true; }
		}

		private long PriceToTick(double p)
		{
			return (long)Math.Round(p / TickSize, MidpointRounding.AwayFromZero);
		}

		private int Tolerancia(long lvl)
		{
			int t = (int)Math.Round(Math.Abs(lvl) * EqTolerancePct / 100.0,
				MidpointRounding.AwayFromZero);
			return Math.Max(1, t);
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 0) return;
			if (Bars.IsFirstBarOfSession)
			{
				_sessionIndex++;
				_hi.Clear(); _lo.Clear(); _cl.Clear();
				_grpHi.Clear(); _grpLo.Clear();
				// las zonas NO se limpian: sobreviven a la sesion, porque el
				// inventario del libro no se borra al cerrar el mercado
			}
			_hi.Add(PriceToTick(High[0]));
			_lo.Add(PriceToTick(Low[0]));
			_cl.Add(PriceToTick(Close[0]));
			int n = _hi.Count;

			int c = n - 1 - PivotRight;
			if (c >= PivotLeft)
			{
				bool esHi = true, esLo = true;
				for (int d = 1; d <= PivotLeft; d++)
				{
					if (!(_hi[c] >= _hi[c - d])) esHi = false;
					if (!(_lo[c] <= _lo[c - d])) esLo = false;
				}
				for (int d = 1; d <= PivotRight; d++)
				{
					if (!(_hi[c] > _hi[c + d])) esHi = false;
					if (!(_lo[c] < _lo[c + d])) esLo = false;
				}
				int gb = CurrentBar - PivotRight;
				if (esHi) Agregar(new Pivot { Bar = gb, Tick = _hi[c] }, true);
				if (esLo) Agregar(new Pivot { Bar = gb, Tick = _lo[c] }, false);
			}
			Actualizar();
		}

		private void Agregar(Pivot p, bool isHigh)
		{
			List<Pivot> g = isHigh ? _grpHi : _grpLo;
			if (g.Count == 0) { g.Add(p); return; }
			int tol = Tolerancia(g[g.Count - 1].Tick);
			if (Math.Abs(p.Tick - g[g.Count - 1].Tick) > tol || p.Bar - g[0].Bar > MaxSpanBars)
			{ g.Clear(); g.Add(p); return; }
			g.Add(p);
			if (g.Count < MinPivots) return;

			long far = g[0].Tick, near = g[0].Tick;
			for (int i = 1; i < g.Count; i++)
			{
				far = isHigh ? Math.Max(far, g[i].Tick) : Math.Min(far, g[i].Tick);
				near = isHigh ? Math.Min(near, g[i].Tick) : Math.Max(near, g[i].Tick);
			}
			long blo = isHigh ? far + 1 : far - LiquidityBandTicks;
			long bhi = isHigh ? far + LiquidityBandTicks : far - 1;

			Zone z = null;
			for (int i = _zones.Count - 1; i >= 0 && i >= _zones.Count - 4; i--)
				if (_zones[i].IsHigh == isHigh && _zones[i].CreatedBar >= g[0].Bar) { z = _zones[i]; break; }
			bool nueva = z == null;
			if (nueva) z = new Zone();
			z.IsHigh = isHigh;
			z.FarEdge = far;
			z.Tol = Tolerancia(far);
			z.Lo = Math.Min(Math.Min(far, near), Math.Min(blo, bhi));
			z.Hi = Math.Max(Math.Max(far, near), Math.Max(blo, bhi));
			z.CreatedBar = g[g.Count - 1].Bar;
			z.NPivots = g.Count;
			if (nueva)
			{
				_zones.Add(z);
				if (MaxZonesTracked > 0 && _zones.Count > MaxZonesTracked)
					_zones.RemoveRange(0, _zones.Count - MaxZonesTracked);
			}
		}

		private void Actualizar()
		{
			int i0 = CurrentBar, loc = _hi.Count - 1;
			long h = _hi[loc], l = _lo[loc], cl = _cl[loc];
			for (int i = 0; i < _zones.Count; i++)
			{
				Zone z = _zones[i];
				if (z.State == "BROKEN" || i0 <= z.CreatedBar) continue;
				bool toca, mecha, cierre;
				if (z.IsHigh)
				{ toca = h >= z.FarEdge - z.Tol; mecha = h > z.FarEdge; cierre = cl > z.FarEdge; }
				else
				{ toca = l <= z.FarEdge + z.Tol; mecha = l < z.FarEdge; cierre = cl < z.FarEdge; }
				if (toca && !z.Dentro) { z.Touches++; z.Dentro = true; }
				else if (!toca) z.Dentro = false;
				if (cierre) z.State = "BROKEN";
				else if (mecha && z.State == "ACTIVE") z.State = "SWEPT";
			}
		}

		// peso = base * 2^(-edad/HalfLife) * TouchDecay^toques * factor(estado)
		// NO hay termino de distancia al precio, y es deliberado.
		private double Peso(Zone z, int atBar)
		{
			int edad = atBar - z.CreatedBar;
			if (edad < 0) return 0.0;
			double w = WeightByPivots ? z.NPivots : 1.0;
			if (HalfLifeBars > 0) w *= Math.Pow(0.5, (double)edad / HalfLifeBars);
			w *= Math.Pow(TouchDecay, z.Touches);
			if (z.State == "BROKEN") w *= BrokenWeight;
			else if (z.State == "SWEPT") w *= SweptWeight;
			return w;
		}

		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (Bars == null || ChartBars == null || RenderTarget == null) return;
			if (_zones == null || _zones.Count == 0) return;
			if (_dxHeat == null) _dxHeat = HeatColor.ToDxBrush(RenderTarget);
			if (_dxHeat == null) return;

			// rango de precio visible, en ticks
			long tLo = PriceToTick(chartScale.MinValue);
			long tHi = PriceToTick(chartScale.MaxValue);
			if (tHi <= tLo || tHi - tLo > 20000) return;
			int span = (int)(tHi - tLo) + 1;
			double[] inten = new double[span];

			int atBar = ChartBars.ToIndex;
			for (int i = 0; i < _zones.Count; i++)
			{
				Zone z = _zones[i];
				if (z.CreatedBar > atBar) continue;
				double w = Peso(z, atBar);
				if (w <= 0) continue;
				if (!UseKernel)
				{
					long a0 = Math.Max(z.Lo, tLo), b0 = Math.Min(z.Hi, tHi);
					for (long t = a0; t <= b0; t++) inten[(int)(t - tLo)] += w;
					continue;
				}
				// kernel triangular: el aporte cae linealmente con la distancia AL
				// RANGO de la zona y se extingue en KernelWidthTicks
				int kw = Math.Max(1, KernelWidthTicks);
				long a = Math.Max(z.Lo - kw, tLo), b = Math.Min(z.Hi + kw, tHi);
				for (long t = a; t <= b; t++)
				{
					long d = t < z.Lo ? z.Lo - t : (t > z.Hi ? t - z.Hi : 0);
					if (d >= kw) continue;
					inten[(int)(t - tLo)] += w * (1.0 - (double)d / kw);
				}
			}

			// --- normalizacion por PERCENTIL: el mapa se autoescala ---
			double tope;
			if (MaxIntensity > 0) tope = MaxIntensity;
			else
			{
				double[] orden = (double[])inten.Clone();
				Array.Sort(orden);
				int idx = Math.Min(span - 1, (int)(span * NormalizePct / 100.0));
				tope = orden[idx];
				// con pocos niveles visibles el percentil 95 coincide con el maximo
				// y todo satura; ahi la referencia honesta es el maximo real
				if (span < 40) tope = orden[span - 1];
			}
			if (tope <= 0) return;

			float x0 = ChartPanel.X, wpx = ChartPanel.W;
			SharpDX.Direct2D1.AntialiasMode prev = RenderTarget.AntialiasMode;
			RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.Aliased;
			try
			{
				for (int k = 0; k < span; k++)
				{
					double u = inten[k] / tope;
					if (u <= 0) continue;
					if (u > 1) u = 1;
					if (Gamma > 0 && Gamma != 1.0) u = Math.Pow(u, Gamma);
					float op = (float)((MinOpacity + (MaxOpacity - MinOpacity) * u) / 100.0);
					if (op <= 0.002f) continue;
					long t = tLo + k;
					float yTop = chartScale.GetYByValue((t + 0.5) * TickSize);
					float yBot = chartScale.GetYByValue((t - 0.5) * TickSize);
					_dxHeat.Opacity = op;
					RenderTarget.FillRectangle(
						new SharpDX.RectangleF(x0, yTop, wpx, Math.Max(1f, yBot - yTop)), _dxHeat);
				}
			}
			finally
			{
				RenderTarget.AntialiasMode = prev;
				_dxHeat.Opacity = 1f;
			}
		}

		public override void OnRenderTargetChanged()
		{
			if (_dxHeat != null) { _dxHeat.Dispose(); _dxHeat = null; }
			if (RenderTarget != null)
			{
				try { _dxHeat = HeatColor.ToDxBrush(RenderTarget); }
				catch { _dxHeat = null; }
			}
		}

		#region Properties
		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "PivotLeft", Order = 1, GroupName = "1. Zonas")]
		public int PivotLeft { get; set; }

		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "PivotRight", Order = 2, GroupName = "1. Zonas")]
		public int PivotRight { get; set; }

		[NinjaScriptProperty] [Range(0.001, 10.0)]
		[Display(Name = "EqTolerancePct", Order = 3, GroupName = "1. Zonas",
			Description = "Umbral de igualdad como porcentaje del precio. 0,10 es el de "
				+ "LuxAlgo y SMC-Liquidity-Hunter.")]
		public double EqTolerancePct { get; set; }

		[NinjaScriptProperty] [Range(2, 100)]
		[Display(Name = "MinPivots", Order = 4, GroupName = "1. Zonas")]
		public int MinPivots { get; set; }

		[NinjaScriptProperty] [Range(1, 100000)]
		[Display(Name = "MaxSpanBars", Order = 5, GroupName = "1. Zonas")]
		public int MaxSpanBars { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "LiquidityBandTicks", Order = 6, GroupName = "1. Zonas")]
		public int LiquidityBandTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 1000000)]
		[Display(Name = "HalfLifeBars (0 = sin decaer)", Order = 10, GroupName = "2. Decaimiento",
			Description = "Vida media en barras. Las zonas NO mueren por distancia al "
				+ "precio: sólo por tiempo y por toques.")]
		public int HalfLifeBars { get; set; }

		[NinjaScriptProperty] [Range(0.01, 1.0)]
		[Display(Name = "TouchDecay", Order = 11, GroupName = "2. Decaimiento",
			Description = "Factor que queda tras cada toque. 0,70 = cada visita consume "
				+ "el 30 % del inventario.")]
		public double TouchDecay { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "SweptWeight (mecha a traves)", Order = 12, GroupName = "2. Decaimiento")]
		public double SweptWeight { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "BrokenWeight (cierre a traves)", Order = 13, GroupName = "2. Decaimiento",
			Description = "0 = una zona rota deja de aportar. Es lo razonable: el precio "
				+ "cerro del otro lado.")]
		public double BrokenWeight { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "WeightByPivots", Order = 14, GroupName = "2. Decaimiento",
			Description = "Una zona de 4 pivotes pesa el doble que una de 2.")]
		public bool WeightByPivots { get; set; }

		[NinjaScriptProperty] [Range(100, 100000)]
		[Display(Name = "MaxZonesTracked", Order = 15, GroupName = "2. Decaimiento")]
		public int MaxZonesTracked { get; set; }

		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "KernelWidthTicks", Order = 16, GroupName = "2. Decaimiento",
			Description = "A cuantos ticks del rango de la zona se extingue su aporte. "
				+ "Sin kernel el mapa sale binario: un bloque saturado y huecos blancos.")]
		public int KernelWidthTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "UseKernel", Order = 17, GroupName = "2. Decaimiento",
			Description = "OFF vuelve a la caja plana de la primera version, para contrastar.")]
		public bool UseKernel { get; set; }

		[NinjaScriptProperty] [Range(50, 100)]
		[Display(Name = "NormalizePct", Order = 20, GroupName = "3. Escala",
			Description = "Percentil de intensidad que mapea a la opacidad maxima. Es lo "
				+ "que hace que el mapa se autoescale en vez de salir siempre demasiado "
				+ "claro o demasiado opaco.")]
		public int NormalizePct { get; set; }

		[NinjaScriptProperty] [Range(0, 1000000)]
		[Display(Name = "MaxIntensity (0 = usar percentil)", Order = 21, GroupName = "3. Escala",
			Description = "> 0 fuerza escala FIJA. Sirve para comparar dos corridas entre si.")]
		public double MaxIntensity { get; set; }

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "MinOpacity %", Order = 22, GroupName = "3. Escala")]
		public int MinOpacity { get; set; }

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "MaxOpacity %", Order = 23, GroupName = "3. Escala")]
		public int MaxOpacity { get; set; }

		[NinjaScriptProperty] [Range(0.1, 5.0)]
		[Display(Name = "Gamma", Order = 24, GroupName = "3. Escala",
			Description = "Curva de la opacidad. > 1 apaga los niveles debiles y resalta "
				+ "los fuertes; < 1 hace lo contrario. Es la perilla fina de calibracion.")]
		public double Gamma { get; set; }

		[XmlIgnore] [Display(Name = "HeatColor", Order = 25, GroupName = "3. Escala")]
		public Brush HeatColor { get; set; }
		[Browsable(false)]
		public string HeatColorSerialize
		{
			get { return Serialize.BrushToString(HeatColor); }
			set { HeatColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty]
		[Display(Name = "EventLogPath (vacio = off)", Order = 30, GroupName = "4. Auditoria")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
