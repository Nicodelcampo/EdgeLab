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

// LiqPoolZones v2.0 -- zonas EQH/EQL. Espejo de edgelab/bridge/indicators/liqpool.py
//
// PORTADO del consenso de las implementaciones de referencia. Comparacion:
// docs/research/H-LIQPOOL_FUENTES_COMPARADAS_2026-09-03.md
//   PyIndicators (equal_hl) -- pivotes consecutivos dentro de tolerancia, y TRES
//     estados: activa / barrida por mecha / rota por cierre.
//   LuxAlgo EQH/EQL -- umbral de igualdad RELATIVO, fusion de zonas vecinas, y el
//     sweep definido en el BORDE LEJANO del cluster.
//   SMC-Liquidity-Hunter -- score por TOQUES + RECENCIA, que coincide con lo que
//     mide arXiv 2101.07410: mas toques previos => mas rebote, con decaimiento.
//
// LAS TRES CORRECCIONES QUE TRAJO EL PORTE, y que explican cuatro intentos fallidos:
//   1. LA TOLERANCIA ES RELATIVA, no fija en ticks. Todas las referencias usan
//      porcentaje del precio (0,1 %) o ATR. En ZB a 108 eso son ~3,5 ticks, no 1.
//   2. EL SWEEP SE DEFINE EN EL BORDE LEJANO, y separa MECHA de CIERRE. Mecha a
//      traves = cascada de stops sin aceptacion. Cierre a traves = el nivel dejo
//      de existir. Es la distincion que pide Osler (2003/2005); mezclarlas en un
//      solo estado pierde el mecanismo.
//   3. LOS PUNTOS SON PIVOTES CORTOS, con longitudes izquierda y derecha
//      separadas. El `>=` a la izquierda deja pasar las mesetas y el `>` a la
//      derecha pone el pivote en la ULTIMA barra de la meseta -- la defensa mas
//      reciente del nivel. Con `>` a los dos lados, como ta.pivothigh de Pine,
//      una meseta no produce NINGUN pivote, y en ZB las mesetas son constantes.
//
// LO QUE NUNCA SE FILTRA: una zona barrida o rota NO se borra. Cambia de estado y
// sigue dibujada y en el CSV. Borrarla deja en pantalla solo las que
// "funcionaron", que es sesgo de supervivencia y no es evidencia admisible.
//
// Aritmetica entera. La tolerancia relativa se resuelve a ticks por zona y se
// registra en el CSV. Contrato: PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md

namespace NinjaTrader.NinjaScript.Indicators
{
	public class LiqPoolZones : Indicator
	{
		private class Pivot { public int Bar; public int Idx; public long Tick; }
		private class Zone
		{
			public bool IsHigh;
			public long FarEdge, NearEdge;      // borde lejano = donde se define el sweep
			public long BandLo, BandHi;
			public int Tol;
			public int NPivots;
			public List<int> PivotBars = new List<int>();
			public List<long> PivotLevels = new List<long>();
			public int FirstBar, CreatedBar, SpanBars;
			public long RoundConfluence;
			public string State = "ACTIVE";     // ACTIVE / SWEPT / BROKEN / EXPIRED
			public int SweptBar = -1, BrokenBar = -1, ExpiredBar = -1;
			public int Touches, FirstTouchBar = -1, AgeAtSweep = -1;
			public bool Dentro;                 // para no contar el mismo toque dos veces
			public bool Logged;
		}

		private List<long> _hi, _lo, _cl;
		private List<Pivot> _grpHi, _grpLo;     // cluster EN CURSO
		private List<Zone> _zones;
		private int _sessionIndex = -1;
		private long _zoneSeq;
		private StreamWriter _log;
		private bool _logFailed;
		private SharpDX.Direct2D1.Brush _dxHi, _dxLo, _dxBand, _dxSwept, _dxBroken;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "LiqPoolZones";
				Description = "Zonas EQH/EQL con tolerancia relativa y tres estados";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				PivotLeft = 2;
				PivotRight = 2;
				EqTolerancePct = 0.10;      // LuxAlgo y SMC-Liquidity-Hunter
				EqToleranceTicks = 0;       // > 0 pisa al porcentaje, solo para contrastar
				MinPivots = 2;
				MaxSpanBars = 500;
				MergeNeighbours = true;
				MaxAgeBars = 0;
				RoundTicks = 32;            // ZB: 32 ticks de 1/32 = 1 punto
				LiquidityBandTicks = 2;

				ShowLiquidityBand = false;
				HideBroken = true;          // solo en pantalla; el CSV nunca se recorta
				ExtendBars = 60;
				MaxZonesRendered = 2000;
				LineWidthPixels = 2f;
				PivotMarkPixels = 7f;
				LevelHighColor = Brushes.IndianRed;
				LevelLowColor = Brushes.MediumSeaGreen;
				BandColor = Brushes.Goldenrod;
				SweptColor = Brushes.Orange;
				BrokenColor = Brushes.Gray;
				ZoneOpacity = 60;
				EventLogPath = "";
			}
			else if (State == State.DataLoaded)
			{
				_hi = new List<long>(); _lo = new List<long>(); _cl = new List<long>();
				_grpHi = new List<Pivot>(); _grpLo = new List<Pivot>();
				_zones = new List<Zone>();
				_zoneSeq = 0;
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (_log != null) { try { _log.Flush(); _log.Close(); } catch { } _log = null; }
				DisposeDxBrushes();
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
				_log.WriteLine("# meta,indicator=LiqPoolZones,version=2.0,model=eqh_eql_reference"
					+ ",instrument=" + Instrument.FullName
					+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
					+ ",pivot_left=" + PivotLeft + ",pivot_right=" + PivotRight
					+ ",eq_tolerance_pct=" + EqTolerancePct.ToString(CultureInfo.InvariantCulture)
					+ ",eq_tolerance_ticks=" + EqToleranceTicks
					+ ",min_pivots=" + MinPivots + ",max_span_bars=" + MaxSpanBars
					+ ",merge_neighbours=" + MergeNeighbours
					+ ",max_age_bars=" + MaxAgeBars + ",round_ticks=" + RoundTicks
					+ ",liquidity_band_ticks=" + LiquidityBandTicks
					+ ",zones_deleted_on_sweep=false,write_mode=overwrite");
				_log.WriteLine("zone_seq,created_bar,bar_close_time_utc,session_index,side,"
					+ "far_edge_tick,near_edge_tick,band_lo,band_hi,tolerance_ticks,n_pivots,"
					+ "first_pivot_bar,span_bars,round_confluence_ticks,pivot_bars,pivot_levels");
			}
			catch { _log = null; _logFailed = true; }
		}

		private long PriceToTick(double price)
		{
			return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
		}

		// Tolerancia RELATIVA resuelta a ticks enteros. Es la correccion principal
		// del porte: todas las referencias usan % del precio o ATR, no ticks fijos.
		private int Tolerancia(long levelTick)
		{
			if (EqToleranceTicks > 0) return EqToleranceTicks;
			int t = (int)Math.Round(Math.Abs(levelTick) * EqTolerancePct / 100.0,
				MidpointRounding.AwayFromZero);
			return Math.Max(1, t);
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 0) return;

			if (Bars.IsFirstBarOfSession)
			{
				// el cluster no cruza sesiones sin una decision explicita
				_sessionIndex++;
				_hi.Clear(); _lo.Clear(); _cl.Clear();
				_grpHi.Clear(); _grpLo.Clear();
			}

			_hi.Add(PriceToTick(High[0]));
			_lo.Add(PriceToTick(Low[0]));
			_cl.Add(PriceToTick(Close[0]));
			int n = _hi.Count;

			// --- pivote confirmado PivotRight barras atras: nunca mira futuro ---
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
				int gBar = CurrentBar - PivotRight;
				if (esHi) Agregar(new Pivot { Bar = gBar, Idx = c, Tick = _hi[c] }, true);
				if (esLo) Agregar(new Pivot { Bar = gBar, Idx = c, Tick = _lo[c] }, false);
			}

			Actualizar();
		}

		private void Agregar(Pivot p, bool isHigh)
		{
			List<Pivot> g = isHigh ? _grpHi : _grpLo;
			if (g.Count == 0) { g.Add(p); return; }
			int tol = Tolerancia(g[g.Count - 1].Tick);
			bool sigue = Math.Abs(p.Tick - g[g.Count - 1].Tick) <= tol
				&& p.Bar - g[0].Bar <= MaxSpanBars;
			if (!sigue) { g.Clear(); g.Add(p); return; }
			g.Add(p);
			if (g.Count >= MinPivots) CrearOActualizar(g, isHigh);
		}

		private void CrearOActualizar(List<Pivot> g, bool isHigh)
		{
			long far = g[0].Tick, near = g[0].Tick;
			for (int i = 1; i < g.Count; i++)
			{
				far = isHigh ? Math.Max(far, g[i].Tick) : Math.Min(far, g[i].Tick);
				near = isHigh ? Math.Min(near, g[i].Tick) : Math.Max(near, g[i].Tick);
			}

			Zone z = null;
			for (int i = _zones.Count - 1; i >= 0; i--)
				if (_zones[i].IsHigh == isHigh && _zones[i].FirstBar == g[0].Bar) { z = _zones[i]; break; }
			// fusion de vecinas: si hay una zona activa del mismo lado dentro de la
			// tolerancia, se le suman los pivotes en vez de crear una nueva ("2x EQH")
			if (z == null && MergeNeighbours)
			{
				int tol0 = Tolerancia(far);
				for (int i = _zones.Count - 1; i >= 0 && i >= _zones.Count - 8; i--)
					if (_zones[i].IsHigh == isHigh && _zones[i].State == "ACTIVE"
						&& Math.Abs(_zones[i].FarEdge - far) <= tol0) { z = _zones[i]; break; }
			}
			bool nueva = z == null;
			if (nueva) { z = new Zone(); _zoneSeq++; }

			z.IsHigh = isHigh;
			z.FarEdge = nueva ? far : (isHigh ? Math.Max(z.FarEdge, far) : Math.Min(z.FarEdge, far));
			z.NearEdge = near;
			z.Tol = Tolerancia(z.FarEdge);
			z.NPivots = g.Count;
			z.PivotBars.Clear(); z.PivotLevels.Clear();
			for (int i = 0; i < g.Count; i++) { z.PivotBars.Add(g[i].Bar); z.PivotLevels.Add(g[i].Tick); }
			z.FirstBar = g[0].Bar;
			z.CreatedBar = g[g.Count - 1].Bar;
			z.SpanBars = z.CreatedBar - z.FirstBar;
			// la banda de stops va MAS ALLA del borde lejano (Osler)
			z.BandLo = isHigh ? z.FarEdge + 1 : z.FarEdge - LiquidityBandTicks;
			z.BandHi = isHigh ? z.FarEdge + LiquidityBandTicks : z.FarEdge - 1;
			long m = RoundTicks > 0 ? ((z.FarEdge % RoundTicks) + RoundTicks) % RoundTicks : 0;
			z.RoundConfluence = RoundTicks > 0 ? Math.Min(m, RoundTicks - m) : 0;

			if (nueva)
			{
				_zones.Add(z);
				if (MaxZonesRendered > 0 && _zones.Count > MaxZonesRendered)
					_zones.RemoveRange(0, _zones.Count - MaxZonesRendered);
			}
			Escribir(z);
		}

		// TRES ESTADOS. Mecha a traves del borde lejano = SWEPT. Cierre a traves =
		// BROKEN. Nada se borra: la zona cambia de estado y sigue en el censo.
		private void Actualizar()
		{
			int i0 = CurrentBar;
			int loc = _hi.Count - 1;
			long h = _hi[loc], l = _lo[loc], cl = _cl[loc];
			for (int i = 0; i < _zones.Count; i++)
			{
				Zone z = _zones[i];
				if (z.State == "BROKEN" || z.State == "EXPIRED") continue;
				if (i0 <= z.CreatedBar) continue;
				if (MaxAgeBars > 0 && (i0 - z.CreatedBar) > MaxAgeBars)
				{ z.State = "EXPIRED"; z.ExpiredBar = i0; continue; }

				bool toca, mecha, cierre;
				if (z.IsHigh)
				{
					toca = h >= z.FarEdge - z.Tol;
					mecha = h > z.FarEdge;
					cierre = cl > z.FarEdge;
				}
				else
				{
					toca = l <= z.FarEdge + z.Tol;
					mecha = l < z.FarEdge;
					cierre = cl < z.FarEdge;
				}

				if (toca && !z.Dentro)
				{
					z.Touches++;
					z.Dentro = true;
					if (z.FirstTouchBar < 0) z.FirstTouchBar = i0;
				}
				else if (!toca) z.Dentro = false;

				if (cierre)
				{
					z.State = "BROKEN"; z.BrokenBar = i0;
					if (z.SweptBar < 0) z.SweptBar = i0;
					z.AgeAtSweep = i0 - z.CreatedBar;
				}
				else if (mecha && z.SweptBar < 0)
				{
					z.SweptBar = i0; z.State = "SWEPT";
					z.AgeAtSweep = i0 - z.CreatedBar;
				}
			}
		}

		private void Escribir(Zone z)
		{
			if (_log == null || _logFailed) return;
			try
			{
				StringBuilder pb = new StringBuilder(), pl = new StringBuilder();
				for (int i = 0; i < z.PivotBars.Count; i++)
				{
					if (i > 0) { pb.Append('|'); pl.Append('|'); }
					pb.Append(z.PivotBars[i]); pl.Append(z.PivotLevels[i]);
				}
				_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}",
					_zoneSeq, z.CreatedBar,
					Time[0].ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					_sessionIndex, z.IsHigh ? "H" : "L",
					z.FarEdge, z.NearEdge, z.BandLo, z.BandHi, z.Tol, z.NPivots,
					z.FirstBar, z.SpanBars, z.RoundConfluence,
					pb.ToString(), pl.ToString()));
			}
			catch (Exception ex) { _logFailed = true; Print(Name + " ERROR [event_log]: " + ex.Message); }
		}

		#region Render
		private void DisposeDxBrushes()
		{
			if (_dxHi != null) { _dxHi.Dispose(); _dxHi = null; }
			if (_dxLo != null) { _dxLo.Dispose(); _dxLo = null; }
			if (_dxBand != null) { _dxBand.Dispose(); _dxBand = null; }
			if (_dxSwept != null) { _dxSwept.Dispose(); _dxSwept = null; }
			if (_dxBroken != null) { _dxBroken.Dispose(); _dxBroken = null; }
		}

		public override void OnRenderTargetChanged()
		{
			DisposeDxBrushes();
			if (RenderTarget == null) return;
			try
			{
				float op = ZoneOpacity / 100f;
				_dxHi = LevelHighColor.ToDxBrush(RenderTarget);
				_dxLo = LevelLowColor.ToDxBrush(RenderTarget);
				_dxBand = BandColor.ToDxBrush(RenderTarget);
				_dxSwept = SweptColor.ToDxBrush(RenderTarget);
				_dxBroken = BrokenColor.ToDxBrush(RenderTarget);
				_dxHi.Opacity = op; _dxLo.Opacity = op;
				_dxSwept.Opacity = op; _dxBand.Opacity = op * 0.6f;
				_dxBroken.Opacity = op * 0.4f;
			}
			catch { DisposeDxBrushes(); }
		}

		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (Bars == null || ChartBars == null || RenderTarget == null) return;
			if (_zones == null || _zones.Count == 0) return;
			if (_dxHi == null) OnRenderTargetChanged();
			if (_dxHi == null) return;

			int from = ChartBars.FromIndex, to = ChartBars.ToIndex;
			float half = (float)chartControl.Properties.BarDistance / 2f;
			SharpDX.Direct2D1.AntialiasMode prev = RenderTarget.AntialiasMode;
			RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.Aliased;
			try
			{
				for (int i = 0; i < _zones.Count; i++)
				{
					Zone z = _zones[i];
					if (HideBroken && z.State == "BROKEN") continue;   // solo en pantalla
					int end = z.CreatedBar + ExtendBars;
					if (z.SweptBar >= 0) end = Math.Min(end, z.SweptBar);
					if (end < from || z.FirstBar > to) continue;

					int a = Math.Max(z.FirstBar, from), b = Math.Min(end, to);
					float x1 = chartControl.GetXByBarIndex(ChartBars, a);
					float x2 = chartControl.GetXByBarIndex(ChartBars, b);
					float w = Math.Max(1f, x2 - x1);
					SharpDX.Direct2D1.Brush br = z.State == "BROKEN" ? _dxBroken
						: z.State == "SWEPT" ? _dxSwept : (z.IsHigh ? _dxHi : _dxLo);

					// linea EN EL BORDE LEJANO, que es donde se define el sweep
					float y = chartScale.GetYByValue(z.FarEdge * TickSize);
					RenderTarget.FillRectangle(
						new SharpDX.RectangleF(x1, y - LineWidthPixels / 2f, w, LineWidthPixels), br);

					// marca en cada pivote que forma la zona
					for (int k = 0; k < z.PivotBars.Count; k++)
					{
						int pbar = z.PivotBars[k];
						if (pbar < from || pbar > to) continue;
						float px = chartControl.GetXByBarIndex(ChartBars, pbar);
						float py = chartScale.GetYByValue(z.PivotLevels[k] * TickSize);
						RenderTarget.FillRectangle(new SharpDX.RectangleF(
							px - half, py - PivotMarkPixels / 2f, half * 2f, PivotMarkPixels), br);
					}

					if (ShowLiquidityBand && LiquidityBandTicks > 0)
					{
						long blo = Math.Min(z.BandLo, z.BandHi), bhi = Math.Max(z.BandLo, z.BandHi);
						float yTop = chartScale.GetYByValue((bhi + 0.5) * TickSize);
						float yBot = chartScale.GetYByValue((blo - 0.5) * TickSize);
						RenderTarget.FillRectangle(
							new SharpDX.RectangleF(x1, yTop, w, Math.Max(1f, yBot - yTop)), _dxBand);
					}
				}
			}
			finally { RenderTarget.AntialiasMode = prev; }
		}
		#endregion

		#region Properties
		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "PivotLeft", Order = 1, GroupName = "1. Deteccion",
			Description = "Barras a la izquierda que el extremo debe dominar, con >=. "
				+ "El >= deja pasar las mesetas, que en ZB son constantes.")]
		public int PivotLeft { get; set; }

		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "PivotRight", Order = 2, GroupName = "1. Deteccion",
			Description = "Barras a la derecha, con >. Pone el pivote en la ULTIMA barra "
				+ "de la meseta y es el retardo de confirmacion.")]
		public int PivotRight { get; set; }

		[NinjaScriptProperty] [Range(0.001, 10.0)]
		[Display(Name = "EqTolerancePct", Order = 3, GroupName = "1. Deteccion",
			Description = "Umbral de igualdad como PORCENTAJE del precio. 0,10 es lo que "
				+ "usan LuxAlgo y SMC-Liquidity-Hunter; en ZB a 108 son ~3,5 ticks.")]
		public double EqTolerancePct { get; set; }

		[NinjaScriptProperty] [Range(0, 10000)]
		[Display(Name = "EqToleranceTicks (0 = usar %)", Order = 4, GroupName = "1. Deteccion",
			Description = "Si es > 0 PISA al porcentaje. Existe solo para contrastar.")]
		public int EqToleranceTicks { get; set; }

		[NinjaScriptProperty] [Range(2, 100)]
		[Display(Name = "MinPivots", Order = 5, GroupName = "1. Deteccion",
			Description = "2 = EQH/EQL clasico. 3+ exige acumulacion; la literatura mide "
				+ "que mas toques previos implican mas rebote.")]
		public int MinPivots { get; set; }

		[NinjaScriptProperty] [Range(1, 100000)]
		[Display(Name = "MaxSpanBars", Order = 6, GroupName = "1. Deteccion")]
		public int MaxSpanBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MergeNeighbours", Order = 7, GroupName = "1. Deteccion",
			Description = "Funde zonas vecinas del mismo lado dentro de la tolerancia "
				+ "(el 2x EQH de LuxAlgo).")]
		public bool MergeNeighbours { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MaxAgeBars (0 = sin expiracion)", Order = 8, GroupName = "2. Ciclo de vida",
			Description = "La literatura mide que la probabilidad de rebote DECAE con el tiempo.")]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "RoundTicks (ZB: 32 = 1 punto)", Order = 9, GroupName = "2. Ciclo de vida",
			Description = "Se registra la distancia al numero redondo: ahi es donde Osler "
				+ "documenta concentracion de ordenes.")]
		public int RoundTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "LiquidityBandTicks", Order = 10, GroupName = "2. Ciclo de vida",
			Description = "Banda de stops MAS ALLA del borde lejano.")]
		public int LiquidityBandTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "ShowLiquidityBand", Order = 20, GroupName = "3. Visual")]
		public bool ShowLiquidityBand { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "HideBroken", Order = 21, GroupName = "3. Visual",
			Description = "Oculta EN PANTALLA las zonas rotas. Siguen en el CSV: borrarlas "
				+ "del censo seria sesgo de supervivencia.")]
		public bool HideBroken { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "ExtendBars", Order = 22, GroupName = "3. Visual")]
		public int ExtendBars { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MaxZonesRendered", Order = 23, GroupName = "3. Visual")]
		public int MaxZonesRendered { get; set; }

		[NinjaScriptProperty] [Range(1, 20)]
		[Display(Name = "LineWidthPixels", Order = 24, GroupName = "3. Visual")]
		public float LineWidthPixels { get; set; }

		[NinjaScriptProperty] [Range(1, 40)]
		[Display(Name = "PivotMarkPixels", Order = 25, GroupName = "3. Visual")]
		public float PivotMarkPixels { get; set; }

		[XmlIgnore] [Display(Name = "LevelHighColor", Order = 26, GroupName = "3. Visual")]
		public Brush LevelHighColor { get; set; }
		[Browsable(false)]
		public string LevelHighColorSerialize
		{
			get { return Serialize.BrushToString(LevelHighColor); }
			set { LevelHighColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "LevelLowColor", Order = 27, GroupName = "3. Visual")]
		public Brush LevelLowColor { get; set; }
		[Browsable(false)]
		public string LevelLowColorSerialize
		{
			get { return Serialize.BrushToString(LevelLowColor); }
			set { LevelLowColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "BandColor", Order = 28, GroupName = "3. Visual")]
		public Brush BandColor { get; set; }
		[Browsable(false)]
		public string BandColorSerialize
		{
			get { return Serialize.BrushToString(BandColor); }
			set { BandColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "SweptColor (mecha a traves)", Order = 29, GroupName = "3. Visual")]
		public Brush SweptColor { get; set; }
		[Browsable(false)]
		public string SweptColorSerialize
		{
			get { return Serialize.BrushToString(SweptColor); }
			set { SweptColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "BrokenColor (cierre a traves)", Order = 30, GroupName = "3. Visual")]
		public Brush BrokenColor { get; set; }
		[Browsable(false)]
		public string BrokenColorSerialize
		{
			get { return Serialize.BrushToString(BrokenColor); }
			set { BrokenColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "ZoneOpacity", Order = 31, GroupName = "3. Visual")]
		public int ZoneOpacity { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EventLogPath (vacio = off)", Order = 40, GroupName = "4. Auditoria",
			Description = "CSV con una fila por zona, incluidas las nunca tocadas.")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
