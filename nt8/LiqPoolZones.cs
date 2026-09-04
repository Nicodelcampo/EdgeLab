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

// LiqPoolZones v1.0 -- zonas de maximos/minimos repetidos, para ZB.
//
// Espejo exacto de edgelab/bridge/indicators/liqpool.py.
// Investigacion que lo fundamenta: docs/research/H-LIQPOOL-ZB_ESTADO_DEL_ARTE_2026-09-03.md
//
// QUE MARCA -- CORREGIDO
//   El objeto NO es "picos al mismo precio". Es una ESCALERA: pivotes
//   CONSECUTIVOS del mismo tipo que bajan (o suben) escalon por escalon.
//   La cadena se corta cuando un pico SUPERA al anterior -- criterio textual de
//   Nico. Un escalon PLANO (mismo precio) no la corta: los maximos iguales son un
//   CASO PARTICULAR de la escalera, no el objeto entero.
//   La primera version buscaba niveles horizontales y por eso casi no coincidia
//   con lo que se marca a mano.
//
//   UN PUNTO ES LA MECHA DE UNA VELA, no un pivote de K barras. La version que
//   exigia dominar PivotStrength barras a cada lado tiraba casi todos los puntos
//   y se quedaba con unos pocos dispersos. Con extremos de vela consecutivos la
//   regla queda simple: una corrida donde el nivel NO SE DEVUELVE.
//     escalera  -- cada punto baja (o sube) un escalon
//     serrucho  -- varios puntos AL MISMO NIVEL; el plano no corta
//   PointModePivot=true recupera el modo viejo, para contrastar.
//
//   LO QUE CORTA LA CADENA ES ROMPER EL NIVEL, NO ALEJARSE DE EL. En un soporte,
//   un minimo que baja mas de TouchToleranceTicks por debajo la corta; que el
//   precio se vaya para arriba y vuelva NO CORTA NADA -- es el caso donde una
//   linea une dos grupos de minimos separados por un tramo alto.
//
//   Y LA ESCALERA NO PUEDE SER EMPINADA: el nivel deriva como maximo
//   MaxSlopeTicks cada SlopePerBars barras, y MaxTotalDriftTicks en total.
//     serrucho / seguidilla -> deriva 0
//     escalera suave        -> deriva dentro del limite
//     escalera empinada     -> NO es zona
//
//   SOLO DOS DE LAS CUATRO COMBINACIONES SON ZONAS:
//     minimos ASCENDENTES  -> soporte escalonado    (valida)
//     maximos DESCENDENTES -> resistencia escalonada (valida)
//     minimos descendentes -> es una bajada, no una zona
//     maximos ascendentes  -> es una subida, no una zona
//   Las dos ultimas son las "invertidas que no cuentan". La version anterior
//   marcaba las cuatro. OnlyCompressingChains las filtra.
//
// LA ZONA TIENE DOS PARTES, y la separacion sale de la literatura, no del gusto:
//   - el NIVEL: donde Osler (J. Finance 2003) documenta que se agrupan los
//     take-profit, y por lo tanto donde el precio tiende a REBOTAR;
//   - la BANDA DE LIQUIDEZ: LiquidityBandTicks MAS ALLA del nivel, donde se
//     apoyan los stop-loss de quien esta posicionado en contra, y por lo tanto
//     donde el precio tiende a ACELERAR si la atraviesa (Osler, JIMF 2005:
//     cascadas de stops).
//   Los dos mecanismos tienen efecto OPUESTO. Un detector que dibuja una sola
//   linea los mezcla y despues no se pueden separar.
//
// LO QUE SE REGISTRA Y NUNCA SE FILTRA
//   n_pivots        -- arXiv 2101.07410 mide que MAS toques previos => MAS
//                      probabilidad de rebote. El conteo es informacion.
//   span_bars       -- barras entre el primer y el ultimo pico.
//   excursion_ticks -- recorrido del precio ENTRE los picos.
//   Esos dos ejes son los que distinguen la MICROZONA (picos juntos, poco
//   recorrido) de la ZONA SEPARADA (picos lejanos, recorrido sustancial). Se
//   registran para estratificar, NO para filtrar: filtrar de entrada congela una
//   poblacion sin haber visto el landscape.
//   round_confluence -- distancia al numero redondo, donde Osler documenta la
//                      concentracion de ordenes. En ZB, 32 ticks = 1 punto.
//
// LA REGLA QUE EVITA EL SESGO QUE ARRUINA ESTO
//   Una zona tocada NO SE BORRA. Se marca TOUCHED / SWEPT / EXPIRED y sigue
//   dibujada y en el CSV. Borrarla al ser mitigada deja en pantalla solo las que
//   "funcionaron", que es sesgo de supervivencia y no es evidencia admisible.
//
// ARITMETICA entera, sin mediana, sin percentil historico, sin reloj entre ticks.
// Empates deterministas. Contrato: PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md

namespace NinjaTrader.NinjaScript.Indicators
{
	public class LiqPoolZones : Indicator
	{
		// Bar = indice GLOBAL de barra (para dibujar y loguear).
		// Idx = indice LOCAL dentro de _hi/_lo, que se limpian por sesion.
		// Mezclarlos dibuja corridas todas las zonas posteriores a la 1a sesion.
		private class Pivot { public int Bar; public int Idx; public bool IsHigh; public long Tick; }
		private class Zone
		{
			public bool IsHigh;
			public long Level;
			public long LevelLo, LevelHi;
			public long BandLo, BandHi;
			public int NPivots;
			public int FirstBar, CreatedBar;
			public int SpanBars;
			public long ExcursionTicks;
			public long RoundConfluence;
			public List<int> PivotBars = new List<int>();     // para dibujar la escalera
			public List<long> PivotLevels = new List<long>();
			public int Direction;          // +1 ascendente, -1 descendente
			public long TotalDropTicks;
			public int FlatSteps;
			public string State;          // ACTIVE / TOUCHED / SWEPT / EXPIRED
			public int TouchedBar = -1, SweptBar = -1, ExpiredBar = -1;
			public bool Logged;
		}

		private List<long> _hi, _lo;
		private List<Pivot> _cadHi, _cadLo;   // cadena EN CURSO, no historial
		private int _dirHi, _dirLo;
		private List<Zone> _zones;
		private int _sessionIndex = -1;
		private long _zoneSeq;
		private StreamWriter _log;
		private bool _logFailed;

		private SharpDX.Direct2D1.Brush _dxLevelHi, _dxLevelLo, _dxBand, _dxSwept;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "LiqPoolZones";
				Description = "Zonas de maximos/minimos repetidos: nivel (take-profit) y banda de liquidez (stops)";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				PivotStrength = 3;
				TouchToleranceTicks = 1;
				MaxSlopeTicks = 1;
				SlopePerBars = 50;
				MaxTotalDriftTicks = 8;
				MaxStepBars = 400;
				MaxStepTicks = 4;
				AllowEqualSteps = true;
				PointModePivot = false;   // por defecto: un punto por vela
				OnlyCompressingChains = true;
				LevelToleranceTicks = 1;
				MinPivots = 3;
				LiquidityBandTicks = 2;
				ZoneHeightTicks = 1;
				MaxAgeBars = 0;
				InvalidationTicks = 8;      // ZB recorre ~26 ticks por sesion: con 4
				                            // casi toda zona se marcaba barrida al instante
				ShowLiquidityBand = false;  // por defecto: solo la linea, sin tapar el chart
				HideSwept = true;           // las barridas siguen en el CSV, no en pantalla
				LineWidthPixels = 2f;
				PivotMarkPixels = 7f;
				RoundTicks = 32;          // ZB: 32 ticks de 1/32 = 1 punto entero
				ExtendBars = 40;
				MaxZonesRendered = 2000;
				KeepTouchedZones = true;

				LevelHighColor = Brushes.IndianRed;
				LevelLowColor = Brushes.MediumSeaGreen;
				BandColor = Brushes.Goldenrod;
				SweptColor = Brushes.Gray;
				ZoneOpacity = 45;
				EventLogPath = "";
			}
			else if (State == State.DataLoaded)
			{
				_hi = new List<long>(); _lo = new List<long>();
				_cadHi = new List<Pivot>(); _cadLo = new List<Pivot>();
				_dirHi = 0; _dirLo = 0;
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
				_log.WriteLine("# meta,indicator=LiqPoolZones,version=1.0"
					+ ",instrument=" + Instrument.FullName
					+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
					+ ",point_mode=" + (PointModePivot ? "pivot" : "bar_extreme")
					+ ",pivot_strength=" + PivotStrength
					+ ",level_tolerance_ticks=" + LevelToleranceTicks
					+ ",min_pivots=" + MinPivots
					+ ",liquidity_band_ticks=" + LiquidityBandTicks
					+ ",zone_height_ticks=" + ZoneHeightTicks
					+ ",max_age_bars=" + MaxAgeBars
					+ ",invalidation_ticks=" + InvalidationTicks
					+ ",touch_tolerance_ticks=" + TouchToleranceTicks
					+ ",max_slope_ticks=" + MaxSlopeTicks
					+ ",slope_per_bars=" + SlopePerBars
					+ ",max_total_drift_ticks=" + MaxTotalDriftTicks
					+ ",max_step_ticks=" + MaxStepTicks
					+ ",max_step_bars=" + MaxStepBars
					+ ",allow_equal_steps=" + AllowEqualSteps
					+ ",only_compressing_chains=" + OnlyCompressingChains
					+ ",round_ticks=" + RoundTicks
					+ ",zones_deleted_on_touch=false,write_mode=overwrite");
				_log.WriteLine("zone_seq,created_bar,bar_close_time_utc,session_index,side,"
					+ "level_tick,level_lo,level_hi,band_lo,band_hi,n_pivots,first_pivot_bar,"
					+ "span_bars,excursion_ticks,round_confluence_ticks,pivot_bars,pivot_levels");
			}
			catch { _log = null; _logFailed = true; }
		}

		private long PriceToTick(double price)
		{
			return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 0) return;

			if (Bars.IsFirstBarOfSession)
			{
				// La zona no cruza sesiones: el pivote de ayer no agrupa con el de hoy
				// sin una decision explicita, y esa decision no esta tomada.
				_sessionIndex++;
				_hi.Clear(); _lo.Clear(); _cadHi.Clear(); _cadLo.Clear();
				_dirHi = 0; _dirLo = 0;
			}

			_hi.Add(PriceToTick(High[0]));
			_lo.Add(PriceToTick(Low[0]));
			int n = _hi.Count;
			int K = PivotStrength;

			if (PointModePivot)
			{
				// modo viejo: solo extremos que dominan K barras a cada lado.
				// El pivote de la barra n-1-K recien se confirma ahora: no mira futuro.
				int c = n - 1 - K;
				if (c >= K)
				{
					bool esHi = true, esLo = true;
					for (int d = 1; d <= K && (esHi || esLo); d++)
					{
						if (!(_hi[c] > _hi[c - d] && _hi[c] > _hi[c + d])) esHi = false;
						if (!(_lo[c] < _lo[c - d] && _lo[c] < _lo[c + d])) esLo = false;
					}
					int gB = CurrentBar - K;
					if (esHi) AgregarPivote(new Pivot { Bar = gB, Idx = c, IsHigh = true, Tick = _hi[c] });
					if (esLo) AgregarPivote(new Pivot { Bar = gB, Idx = c, IsHigh = false, Tick = _lo[c] });
				}
			}
			else
			{
				// UN PUNTO POR VELA: la mecha. Disponible al cerrar la barra, sin lag.
				int c = n - 1;
				AgregarPivote(new Pivot { Bar = CurrentBar, Idx = c, IsHigh = true, Tick = _hi[c] });
				AgregarPivote(new Pivot { Bar = CurrentBar, Idx = c, IsHigh = false, Tick = _lo[c] });
			}

			ActualizarZonas();
		}

		// CADENA SOBRE UN NIVEL. Un punto cuenta como TOQUE si esta a
		// TouchToleranceTicks del nivel. Rompe -- y cierra la cadena -- solo el punto
		// que atraviesa el nivel en el sentido que lo invalida. Alejarse no rompe.
		private void AgregarPivote(Pivot p)
		{
			List<Pivot> cad = p.IsHigh ? _cadHi : _cadLo;
			if (cad.Count == 0) { cad.Add(p); return; }

			long nivel = cad[cad.Count - 1].Tick;
			long v0 = cad[0].Tick;
			int b0 = cad[0].Bar;

			if (p.Bar - cad[cad.Count - 1].Bar > MaxStepBars) { Reiniciar(cad, p); return; }

			bool rompe = p.IsHigh ? (p.Tick > nivel + TouchToleranceTicks)
								  : (p.Tick < nivel - TouchToleranceTicks);
			if (rompe) { Reiniciar(cad, p); return; }

			if (Math.Abs(p.Tick - nivel) > TouchToleranceTicks) return;   // lejos: se ignora

			long dTotal = p.Tick - v0;
			int dSpan = p.Bar - b0;
			bool empinada = Math.Abs(dTotal) * SlopePerBars > (long)MaxSlopeTicks * Math.Max(dSpan, 1)
				&& Math.Abs(dTotal) > MaxSlopeTicks;
			if (Math.Abs(dTotal) > MaxTotalDriftTicks || empinada) { Reiniciar(cad, p); return; }

			int sig = p.IsHigh ? -1 : 1;      // direccion que comprime
			if (OnlyCompressingChains && dTotal != 0 && ((dTotal > 0) != (sig > 0)))
			{ Reiniciar(cad, p); return; }

			cad.Add(p);
			if (cad.Count >= MinPivots) CrearOActualizarZona(cad, p.IsHigh);
		}

		private void Reiniciar(List<Pivot> cad, Pivot p)
		{
			cad.Clear();
			cad.Add(p);
		}

		private void CrearOActualizarZona(List<Pivot> grupo, bool isHigh)
		{
			int a = grupo[0].Bar, b = grupo[grupo.Count - 1].Bar;          // globales
			int ia = grupo[0].Idx, ib = grupo[grupo.Count - 1].Idx;        // locales
			// El nivel operativo es el ULTIMO escalon: los previos ya fueron
			// superados por la propia escalera.
			long nivel = grupo[grupo.Count - 1].Tick;

			long exc = 0;
			if (ia >= 0 && ib > ia && ib < _hi.Count)
			{
				long mx = _hi[ia], mn = _lo[ia];
				for (int i = ia; i <= ib; i++) { if (_hi[i] > mx) mx = _hi[i]; if (_lo[i] < mn) mn = _lo[i]; }
				exc = mx - mn;
			}

			// si el ultimo pivote extiende una zona ya creada, se actualiza en vez
			// de duplicarla: la zona es el grupo, no cada par consecutivo
			Zone z = null;
			for (int i = _zones.Count - 1; i >= 0; i--)
				if (_zones[i].IsHigh == isHigh && _zones[i].FirstBar == a) { z = _zones[i]; break; }
			bool nueva = z == null;
			if (nueva) { z = new Zone(); _zoneSeq++; }

			z.IsHigh = isHigh; z.Level = nivel;
			z.LevelLo = isHigh ? nivel - ZoneHeightTicks : nivel;
			z.LevelHi = isHigh ? nivel : nivel + ZoneHeightTicks;
			z.BandLo = isHigh ? nivel + 1 : nivel - LiquidityBandTicks;
			z.BandHi = isHigh ? nivel + LiquidityBandTicks : nivel - 1;
			z.NPivots = grupo.Count; z.FirstBar = a; z.CreatedBar = b;
			z.PivotBars.Clear(); z.PivotLevels.Clear(); z.FlatSteps = 0;
			for (int i = 0; i < grupo.Count; i++)
			{
				z.PivotBars.Add(grupo[i].Bar); z.PivotLevels.Add(grupo[i].Tick);
				if (i > 0 && grupo[i].Tick == grupo[i - 1].Tick) z.FlatSteps++;
			}
			z.Direction = isHigh ? _dirHi : _dirLo;
			z.TotalDropTicks = Math.Abs(grupo[grupo.Count - 1].Tick - grupo[0].Tick);
			z.SpanBars = b - a; z.ExcursionTicks = exc;
			long m = RoundTicks > 0 ? ((nivel % RoundTicks) + RoundTicks) % RoundTicks : 0;
			z.RoundConfluence = RoundTicks > 0 ? Math.Min(m, RoundTicks - m) : 0;
			z.State = "ACTIVE"; z.TouchedBar = -1; z.SweptBar = -1;

			if (nueva)
			{
				_zones.Add(z);
				if (MaxZonesRendered > 0 && _zones.Count > MaxZonesRendered)
					_zones.RemoveRange(0, _zones.Count - MaxZonesRendered);
			}
			EscribirZona(z, grupo);
		}

		private void ActualizarZonas()
		{
			int loc = _hi.Count - 1;        // ultima barra, indice local
			int i0 = CurrentBar;            // la misma barra, indice global
			long h = _hi[loc], l = _lo[loc];
			for (int i = 0; i < _zones.Count; i++)
			{
				Zone z = _zones[i];
				if (z.State == "SWEPT" || z.State == "EXPIRED") continue;
				if (i0 <= z.CreatedBar) continue;
				if (MaxAgeBars > 0 && (i0 - z.CreatedBar) > MaxAgeBars)
				{ z.State = "EXPIRED"; z.ExpiredBar = i0; continue; }
				if (z.IsHigh)
				{
					if (z.TouchedBar < 0 && h >= z.LevelLo) { z.TouchedBar = i0; z.State = "TOUCHED"; }
					if (h >= z.Level + InvalidationTicks) { z.SweptBar = i0; z.State = "SWEPT"; }
				}
				else
				{
					if (z.TouchedBar < 0 && l <= z.LevelHi) { z.TouchedBar = i0; z.State = "TOUCHED"; }
					if (l <= z.Level - InvalidationTicks) { z.SweptBar = i0; z.State = "SWEPT"; }
				}
			}
		}

		private void EscribirZona(Zone z, List<Pivot> grupo)
		{
			if (_log == null || _logFailed) return;
			try
			{
				StringBuilder pb = new StringBuilder(), pl = new StringBuilder();
				for (int i = 0; i < grupo.Count; i++)
				{
					if (i > 0) { pb.Append('|'); pl.Append('|'); }
					pb.Append(grupo[i].Bar); pl.Append(grupo[i].Tick);
				}
				_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},"
				+ "{15},{16},{17},{18},{19}",
					_zoneSeq, z.CreatedBar,
					Time[0].ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					_sessionIndex, z.IsHigh ? "H" : "L",
					z.Level, z.LevelLo, z.LevelHi, z.BandLo, z.BandHi,
					z.NPivots, z.FirstBar, z.SpanBars, z.ExcursionTicks, z.RoundConfluence,
					z.Direction, z.TotalDropTicks, z.FlatSteps,
					pb.ToString(), pl.ToString()));
			}
			catch (Exception ex) { _logFailed = true; Print(Name + " ERROR [event_log]: " + ex.Message); }
		}

		#region Render
		private void DisposeDxBrushes()
		{
			if (_dxLevelHi != null) { _dxLevelHi.Dispose(); _dxLevelHi = null; }
			if (_dxLevelLo != null) { _dxLevelLo.Dispose(); _dxLevelLo = null; }
			if (_dxBand != null) { _dxBand.Dispose(); _dxBand = null; }
			if (_dxSwept != null) { _dxSwept.Dispose(); _dxSwept = null; }
		}

		public override void OnRenderTargetChanged()
		{
			DisposeDxBrushes();
			if (RenderTarget == null) return;
			try
			{
				float op = ZoneOpacity / 100f;
				_dxLevelHi = LevelHighColor.ToDxBrush(RenderTarget);
				_dxLevelLo = LevelLowColor.ToDxBrush(RenderTarget);
				_dxBand = BandColor.ToDxBrush(RenderTarget);
				_dxSwept = SweptColor.ToDxBrush(RenderTarget);
				_dxLevelHi.Opacity = op; _dxLevelLo.Opacity = op;
				_dxBand.Opacity = op * 0.7f;      // la banda es secundaria al nivel
				_dxSwept.Opacity = op * 0.5f;     // barrida: visible pero apagada
			}
			catch { DisposeDxBrushes(); }
		}

		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (Bars == null || ChartBars == null || RenderTarget == null) return;
			if (_zones == null || _zones.Count == 0) return;
			if (_dxLevelHi == null) OnRenderTargetChanged();
			if (_dxLevelHi == null) return;

			int from = ChartBars.FromIndex, to = ChartBars.ToIndex;
			float half = (float)chartControl.Properties.BarDistance / 2f;
			SharpDX.Direct2D1.AntialiasMode prev = RenderTarget.AntialiasMode;
			RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.PerPrimitive;
			try
			{
				for (int i = 0; i < _zones.Count; i++)
				{
					Zone z = _zones[i];
					// KeepTouchedZones=false SOLO oculta; el CSV nunca se recorta.
					if (!KeepTouchedZones && z.State != "ACTIVE") continue;
					if (HideSwept && z.State == "SWEPT") continue;
					int end = z.CreatedBar + ExtendBars;
					if (z.SweptBar >= 0) end = Math.Min(end, z.SweptBar);
					if (end < from || z.FirstBar > to) continue;

					int a = Math.Max(z.FirstBar, from), b = Math.Min(end, to);
					float x1 = chartControl.GetXByBarIndex(ChartBars, a);
					float x2 = chartControl.GetXByBarIndex(ChartBars, b);
					float w = Math.Max(1f, x2 - x1);

					SharpDX.Direct2D1.Brush bl = z.State == "SWEPT" ? _dxSwept
						: (z.IsHigh ? _dxLevelHi : _dxLevelLo);

					// POLILINEA de la escalera: un segmento por escalon, tal como se
					// traza a mano. Un rectangulo, o una linea horizontal unica, no
					// muestran el objeto: lo que importa es el camino escalonado.
					for (int k = 0; k < z.PivotBars.Count; k++)
					{
						int pb = z.PivotBars[k];
						float px = chartControl.GetXByBarIndex(ChartBars, pb);
						float py = chartScale.GetYByValue(z.PivotLevels[k] * TickSize);
						if (k > 0)
						{
							float qx = chartControl.GetXByBarIndex(ChartBars, z.PivotBars[k - 1]);
							float qy = chartScale.GetYByValue(z.PivotLevels[k - 1] * TickSize);
							RenderTarget.DrawLine(new SharpDX.Vector2(qx, qy),
								new SharpDX.Vector2(px, py), bl, LineWidthPixels);
						}
						if (pb >= from && pb <= to)
							RenderTarget.FillRectangle(new SharpDX.RectangleF(
								px - half, py - PivotMarkPixels / 2f, half * 2f, PivotMarkPixels), bl);
					}

					// prolongacion del ULTIMO escalon, que es el nivel vigente
					float y = chartScale.GetYByValue(z.Level * TickSize);
					float xLast = chartControl.GetXByBarIndex(ChartBars, Math.Min(z.CreatedBar, to));
					if (x2 > xLast)
						RenderTarget.FillRectangle(new SharpDX.RectangleF(
							xLast, y - LineWidthPixels / 2f, x2 - xLast, LineWidthPixels), bl);

					// banda de liquidez: franja fina MAS ALLA del nivel, opcional
					if (ShowLiquidityBand && LiquidityBandTicks > 0)
					{
						long blo = Math.Min(z.BandLo, z.BandHi), bhi = Math.Max(z.BandLo, z.BandHi);
						float yTop = chartScale.GetYByValue((bhi + 0.5) * TickSize);
						float yBot = chartScale.GetYByValue((blo - 0.5) * TickSize);
						RenderTarget.FillRectangle(
							new SharpDX.RectangleF(x1, yTop, w, Math.Max(1f, yBot - yTop)),
							z.State == "SWEPT" ? _dxSwept : _dxBand);
					}
				}
			}
			finally { RenderTarget.AntialiasMode = prev; }
		}

		#endregion

		#region Properties
		[NinjaScriptProperty]
		[Display(Name = "PointModePivot", Order = 0, GroupName = "1. Deteccion",
			Description = "OFF (default) = un punto por vela, su mecha. ON = solo extremos "
				+ "que dominan PivotStrength barras a cada lado. El modo por vela es el que "
				+ "reproduce las seguidillas y serruchos que se trazan a mano.")]
		public bool PointModePivot { get; set; }

		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "PivotStrength (solo si PointModePivot)", Order = 1, GroupName = "1. Deteccion",
			Description = "Barras a cada lado que el extremo debe dominar ESTRICTAMENTE. "
				+ "Subirlo da menos pivotes y mas significativos.")]
		public int PivotStrength { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "TouchToleranceTicks", Order = 2, GroupName = "1. Deteccion",
			Description = "Cuan cerca del nivel tiene que estar un punto para contar como "
				+ "toque. Un punto que ATRAVIESA el nivel mas alla de esto corta la cadena; "
				+ "uno que se aleja para el otro lado simplemente se ignora.")]
		public int TouchToleranceTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "MaxSlopeTicks", Order = 3, GroupName = "1. Deteccion",
			Description = "Deriva maxima del nivel cada SlopePerBars barras. La escalera no "
				+ "puede ser empinada.")]
		public int MaxSlopeTicks { get; set; }

		[NinjaScriptProperty] [Range(1, 100000)]
		[Display(Name = "SlopePerBars", Order = 4, GroupName = "1. Deteccion")]
		public int SlopePerBars { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MaxTotalDriftTicks", Order = 5, GroupName = "1. Deteccion",
			Description = "Deriva total maxima de la cadena entera, de punta a punta.")]
		public int MaxTotalDriftTicks { get; set; }

		[NinjaScriptProperty] [Range(1, 10000)]
		[Display(Name = "MaxStepTicks (legado)", Order = 9, GroupName = "1. Deteccion",
			Description = "Salto maximo de precio entre dos escalones consecutivos. Es el "
				+ "criterio de que la consecucion sea cercana: mas alla, la cadena se corta.")]
		public int MaxStepTicks { get; set; }

		[NinjaScriptProperty] [Range(1, 100000)]
		[Display(Name = "MaxStepBars", Order = 3, GroupName = "1. Deteccion",
			Description = "Separacion maxima en barras entre dos escalones consecutivos.")]
		public int MaxStepBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "OnlyCompressingChains", Order = 4, GroupName = "1. Deteccion",
			Description = "Solo minimos ASCENDENTES (soporte) y maximos DESCENDENTES "
				+ "(resistencia). Minimos bajando o maximos subiendo son la tendencia "
				+ "misma, no una zona. OFF marca las cuatro combinaciones.")]
		public bool OnlyCompressingChains { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "AllowEqualSteps", Order = 5, GroupName = "1. Deteccion",
			Description = "Un escalon plano, al mismo precio, NO corta la cadena. Los maximos "
				+ "iguales son un caso particular de la escalera, no el objeto entero.")]
		public bool AllowEqualSteps { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "LevelToleranceTicks (legado)", Order = 5, GroupName = "1. Deteccion",
			Description = "Cuanto pueden diferir dos picos y seguir siendo el mismo nivel. "
				+ "Con el tick de ZB, 0 y 1 son universos distintos.")]
		public int LevelToleranceTicks { get; set; }

		[NinjaScriptProperty] [Range(2, 100)]
		[Display(Name = "MinPivots", Order = 3, GroupName = "1. Deteccion",
			Description = "Picos que hacen una zona. 2 = par; 3+ = acumulacion. "
				+ "La literatura mide que mas toques previos implican mas rebote.")]
		public int MinPivots { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "LiquidityBandTicks", Order = 4, GroupName = "2. Zona",
			Description = "Ancho de la banda MAS ALLA del nivel, donde se apoyan los stops. "
				+ "Separada del nivel a proposito: nivel = take-profit (rebote), "
				+ "banda = stops (cascada). Efectos opuestos.")]
		public int LiquidityBandTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "ZoneHeightTicks", Order = 5, GroupName = "2. Zona")]
		public int ZoneHeightTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MaxAgeBars (0 = sin expiracion)", Order = 6, GroupName = "2. Zona",
			Description = "La literatura mide que la probabilidad de rebote DECAE con el tiempo.")]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "ShowLiquidityBand", Order = 17, GroupName = "3. Visual",
			Description = "Dibuja la franja de stops mas alla del nivel. OFF deja solo la "
				+ "linea. No afecta al CSV.")]
		public bool ShowLiquidityBand { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "HideSwept", Order = 18, GroupName = "3. Visual",
			Description = "Oculta en pantalla las zonas barridas. Siguen en el CSV: "
				+ "borrarlas del censo seria sesgo de supervivencia.")]
		public bool HideSwept { get; set; }

		[NinjaScriptProperty] [Range(1, 20)]
		[Display(Name = "LineWidthPixels", Order = 19, GroupName = "3. Visual")]
		public float LineWidthPixels { get; set; }

		[NinjaScriptProperty] [Range(1, 40)]
		[Display(Name = "PivotMarkPixels", Order = 20, GroupName = "3. Visual",
			Description = "Alto de la marca en cada pico que participa de la zona.")]
		public float PivotMarkPixels { get; set; }

		[NinjaScriptProperty] [Range(1, 10000)]
		[Display(Name = "InvalidationTicks", Order = 7, GroupName = "2. Zona",
			Description = "Cuanto debe atravesar el precio para considerar la zona barrida.")]
		public int InvalidationTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "RoundTicks (ZB: 32 = 1 punto)", Order = 8, GroupName = "2. Zona",
			Description = "Cada cuantos ticks hay un numero redondo. Se registra la distancia "
				+ "al mas cercano: ahi es donde Osler documenta concentracion de ordenes.")]
		public int RoundTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "KeepTouchedZones", Order = 9, GroupName = "3. Visual",
			Description = "OFF oculta las tocadas/barridas EN PANTALLA. El CSV nunca se "
				+ "recorta: borrar las mitigadas produce sesgo de supervivencia.")]
		public bool KeepTouchedZones { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "ExtendBars", Order = 10, GroupName = "3. Visual")]
		public int ExtendBars { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MaxZonesRendered", Order = 11, GroupName = "3. Visual")]
		public int MaxZonesRendered { get; set; }

		[XmlIgnore] [Display(Name = "LevelHighColor", Order = 12, GroupName = "3. Visual")]
		public Brush LevelHighColor { get; set; }
		[Browsable(false)]
		public string LevelHighColorSerialize
		{
			get { return Serialize.BrushToString(LevelHighColor); }
			set { LevelHighColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "LevelLowColor", Order = 13, GroupName = "3. Visual")]
		public Brush LevelLowColor { get; set; }
		[Browsable(false)]
		public string LevelLowColorSerialize
		{
			get { return Serialize.BrushToString(LevelLowColor); }
			set { LevelLowColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "BandColor", Order = 14, GroupName = "3. Visual")]
		public Brush BandColor { get; set; }
		[Browsable(false)]
		public string BandColorSerialize
		{
			get { return Serialize.BrushToString(BandColor); }
			set { BandColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "SweptColor", Order = 15, GroupName = "3. Visual")]
		public Brush SweptColor { get; set; }
		[Browsable(false)]
		public string SweptColorSerialize
		{
			get { return Serialize.BrushToString(SweptColor); }
			set { SweptColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "ZoneOpacity", Order = 16, GroupName = "3. Visual")]
		public int ZoneOpacity { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EventLogPath (vacio = off)", Order = 20, GroupName = "4. Auditoria",
			Description = "CSV con una fila por zona, incluidas las que nunca fueron tocadas.")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
