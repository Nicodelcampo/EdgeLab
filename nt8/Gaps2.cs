// ============================================================================
// Gaps2.cs — v2.0 — Detector canónico de gaps 1-tick + ciclo de vida tick-exacto
// Consolida: GapsNq (detección) + GapsClassifier (clasificación / lifecycle / CSV)
// Piloto del puente NT8 → EdgeLab/vectorbt. Sigue la Guía reutilizable §1–14.
//
// ============================== CONTRATO ====================================
// DEFINICIÓN DEL EVENTO
//   gap = |P(t) − P(t−1)| >= umbral, entre dos TRADES consecutivos de la
//   subserie 1-tick. top = max(P(t−1),P(t)); bottom = min(P(t−1),P(t));
//   is_bullish = P(t) > P(t−1). Volumen del gap = volumen del tick posterior.
//   Umbrales SIEMPRE en ticks (MinGapTicks), nunca en puntos → portable
//   entre instrumentos sin recalibrar.
//
// MOTOR ÚNICO
//   Detección Y ciclo de vida corren sobre la subserie 1-tick (timestamps
//   exactos). La serie primaria solo se usa para: expiración por barras
//   (MaxAgeBars — depende del tipo de barra del chart: DECLARADO, usar el
//   chart canónico del contrato de datos), render, y ATR de referencia
//   (solo exportado, NUNCA usado para decidir).
//
// CICLO DE VIDA (tick-exacto, monótono)
//   VIRGIN → TOUCHED   : primer trade estrictamente dentro (bottom<P<top).
//          → PARTIAL   : max_pen >= PartialFillPct% desde el borde proximal.
//          → FULLFILLED (interno): max_pen = 100% (P alcanzó el borde distal).
//            Se resuelve como:
//              INVALIDATED reason=inverse  si P avanza ReversalConfirmTicks
//                                          más allá del borde distal;
//              INVALIDATED reason=full_fill si P recruza el borde proximal
//                                          de vuelta, o al expirar
//                                          (extra=resolved_by_expiry).
//            ReversalConfirmTicks=0 ⇒ full_fill inmediato al 100%.
//   ZONE_EXPIRED si (CurrentBar − created_bar) > MaxAgeBars.
//   Penetración: alcista se rellena desde arriba: pen=(top−P)/size;
//   bajista desde abajo: pen=(P−bottom)/size. Clampeada [0,1], máx. acumulado.
//   El tick de creación NO cuenta como toque (sus precios son los bordes).
//   Toque por ÉPOCAS: entrar estando afuera = 1 época; se loguean hasta
//   MaxLoggedTouches épocas; el contador sigue completo en cada evento.
//
// SIN LOOK-AHEAD
//   - Prohibido usar Count. Expiración por CurrentBar − created_bar.
//   - Baseline de volumen = media EXACTA de los últimos VolBaselineTicks
//     volúmenes de tick EXCLUYENDO el tick actual (ring buffer, sin
//     estimadores streaming). vol_ratio vacío hasta MinVolBaselineSamples.
//   - atr_at_creation = ATR(AtrPeriod) de la última barra primaria CERRADA.
//
// LO QUE NO HACE (a propósito — se deriva offline en EdgeLab desde el Store)
//   - Sesiones / killzones / ventanas de noticias: clasificar por ts contra
//     calendario versionado (en v1: offset fijo a ET frágil ante DST).
//   - Clusters y anidamiento entre gaps: query offline (en v1 mutaba
//     IsClustered/ClusterSize de gaps YA creados = repaint de features).
//   - Bins de magnitud (Micro/Small/…): binning offline; acá solo continuo
//     (size_ticks, atr_at_creation, vol_ratio).
//   - Heatmaps de densidad (GapsHeatmap): query offline sobre eventos.
//
// REAPERTURA
//   Pausa > ReopenPauseMinutes entre ticks ⇒ warmup de ReopenWarmupMinutes
//   sin detección (el salto de reapertura no es microestructura). Se emite
//   SESSION_GAP_SKIPPED con pausa y salto, para auditoría.
//
// EXPORT CSV (stream de EVENTOS — nunca dump de estado final)
//   Línea '# meta ...' con indicador/versión/semántica + '# params ...'.
//   event_seq monótono. ts local del chart ISO-8601 con ms + unix_ms
//   (ToUniversalTime de la máquina: VERIFICAR timezone en gate P0).
//   Piso de export: ExportFloorTicks (default 2) <= MinGapTicks (display).
//   Todos los gaps >= piso llevan ciclo de vida completo; MinGapTicks solo
//   filtra el dibujo. Eventos: ZONE_CREATED, ZONE_TOUCHED, ZONE_PARTIAL,
//   ZONE_INVALIDATED(reason), ZONE_EXPIRED, SESSION_GAP_SKIPPED,
//   SESSION_END (snapshot al cerrar, no es lifecycle), ERROR.
//
// RENDER (solo visual, nunca decide)
//   Rectángulos por gap activo, borde por estado, redibujo solo al cierre de
//   barra primaria y ante cambio de estado. Draw.* JAMÁS desde el hilo tick.
//
// PARIDAD (gates): P0 ticks → P2A creación → P2B ciclo de vida contra la
//   réplica vectorbt. P1B no aplica (no usa bid/ask).
//
// A/B contra v1: MinGapTicks=5 con tick 0.25 ≈ MinGapPoints=1.25 de GapsNq.
// ============================================================================

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
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class Gaps2 : Indicator
	{
		#region Tipos internos
		private enum GapState { Virgin, Touched, Partial, FullFilled, Invalidated, Expired }

		private sealed class GapZone
		{
			public int      Id;
			public DateTime CreatedTime;
			public long     CreatedUnixMs;
			public int      CreatedPrimaryBar;
			public double   Top, Bottom;
			public bool     IsBullish;
			public int      SizeTicks;
			public double   AtrAtCreation;   // NaN si aún no hay ATR cerrado
			public double   VolAtCreation;
			public double   VolBaseline;     // NaN si muestras insuficientes
			public GapState State;
			public double   MaxPenPct;
			public int      Touches;
			public bool     InsideEpoch;
			public bool     Display;
			public bool     Archived;
			public bool     NeedsRedraw;
			public string   Tag;
			public double   Size { get { return Top - Bottom; } }
		}
		#endregion

		#region Estado
		private readonly List<GapZone> _gaps = new List<GapZone>(256);
		private int _nextId;
		private ATR _atr;

		// baseline exacto de volumen por tick (excluye tick actual)
		private double[] _volRing;
		private int _volCount, _volHead;
		private double _volSum;

		// reapertura
		private DateTime _lastTickTime = DateTime.MinValue;
		private DateTime _warmupUntil  = DateTime.MinValue;

		// logger
		private StreamWriter _log;
		private long _seq;
		private int _sinceFlush;
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name                     = "Gaps2";
				Description              = "v2 canónica de gaps 1-tick: detección + ciclo de vida tick-exacto + export de eventos. Contrato completo en el header del .cs.";
				Calculate                = Calculate.OnBarClose;   // la subserie 1-tick cierra en cada tick
				IsOverlay                = true;
				DisplayInDataBox         = false;
				PaintPriceMarkers        = false;
				IsSuspendedWhileInactive = false;                  // logger: nunca suspender

				// 1. Detección
				MinGapTicks           = 5;
				ExportFloorTicks      = 2;
				ReopenPauseMinutes    = 60;
				ReopenWarmupMinutes   = 30;
				AtrPeriod             = 14;
				VolBaselineTicks      = 2000;
				MinVolBaselineSamples = 500;

				// 2. Ciclo de vida
				PartialFillPct        = 50;
				ReversalConfirmTicks  = 2;
				MaxAgeBars            = 2000;
				MaxLoggedTouches      = 20;

				// 3. Export
				EventLogPath          = "";

				// 4. Visual
				ShowZones             = true;
				MaxZonesDrawn         = 300;
				RectOpacity           = 25;
				ColorBullGap          = Brushes.LightSkyBlue;
				ColorBearGap          = Brushes.LightSalmon;
			}
			else if (State == State.Configure)
			{
				// Subserie fija de 1 tick: motor único (guía §11/§13).
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				// Validación de combinaciones (guía §5): el piso de export nunca
				// puede superar el umbral de display.
				if (ExportFloorTicks > MinGapTicks)
				{
					Print("[Gaps2] ExportFloorTicks > MinGapTicks; se ajusta ExportFloorTicks=" + MinGapTicks);
					ExportFloorTicks = MinGapTicks;
				}

				_atr     = ATR(AtrPeriod);
				_volRing = new double[Math.Max(2, VolBaselineTicks)];
				_volCount = 0; _volHead = 0; _volSum = 0;
				_gaps.Clear(); _nextId = 0; _seq = 0;

				OpenLog();
			}
			else if (State == State.Terminated)
			{
				CloseLog();
			}
		}

		protected override void OnBarUpdate()
		{
			// ── Subserie 1-tick: motor de detección + ciclo de vida ──
			if (BarsInProgress == 1)
			{
				if (CurrentBars[1] < 1) return;   // necesita tick previo

				double   price = Closes[1][0];
				double   vol   = Volumes[1][0];
				DateTime t     = Times[1][0];

				// Reapertura / warmup
				bool skipDetection = false;
				if (_lastTickTime != DateTime.MinValue)
				{
					double pauseMin = (t - _lastTickTime).TotalMinutes;
					if (pauseMin >= ReopenPauseMinutes)
					{
						_warmupUntil = t.AddMinutes(ReopenWarmupMinutes);
						double jump = Math.Abs(price - Closes[1][1]);
						LogEvent("SESSION_GAP_SKIPPED", null, t, price,
							string.Format(CultureInfo.InvariantCulture, "pause_min={0:F1};jump_pts={1:F4}", pauseMin, jump));
					}
				}
				if (t < _warmupUntil) skipDetection = true;
				_lastTickTime = t;

				// 1) Ciclo de vida ANTES de crear (el tick de creación no toca su propio gap)
				UpdateZonesWithTick(price, t);

				// 2) Detección
				if (!skipDetection)
				{
					double prev     = Closes[1][1];
					int    gapTicks = (int)Math.Round(Math.Abs(price - prev) / TickSize);
					if (gapTicks >= ExportFloorTicks)
						CreateGap(prev, price, vol, t, gapTicks);
				}

				// 3) Baseline: el tick actual entra al ring DESPUÉS de usarse el baseline
				PushVol(vol);
				return;
			}

			// ── Serie primaria: expiración + render ──
			if (BarsInProgress != 0) return;
			if (CurrentBars[0] < 1) return;

			ExpireOldZones();
			DrawZones();
		}

		#region Motor
		private void CreateGap(double prevPrice, double curPrice, double vol, DateTime t, int gapTicks)
		{
			GapZone g = new GapZone();
			g.Id                = ++_nextId;
			g.CreatedTime       = t;
			g.CreatedUnixMs     = ToUnixMs(t);
			g.CreatedPrimaryBar = CurrentBars[0];
			g.Top               = Math.Max(prevPrice, curPrice);
			g.Bottom            = Math.Min(prevPrice, curPrice);
			g.IsBullish         = curPrice > prevPrice;
			g.SizeTicks         = gapTicks;
			g.AtrAtCreation     = (CurrentBars[0] >= AtrPeriod + 1) ? _atr[1] : double.NaN;
			g.VolAtCreation     = vol;
			g.VolBaseline       = (_volCount >= MinVolBaselineSamples) ? _volSum / _volCount : double.NaN;
			g.State             = GapState.Virgin;
			g.MaxPenPct         = 0;
			g.Display           = gapTicks >= MinGapTicks;
			g.Tag               = "G2_" + g.Id;
			g.NeedsRedraw       = true;

			_gaps.Add(g);
			LogEvent("ZONE_CREATED", g, t, curPrice, "");
		}

		private void UpdateZonesWithTick(double price, DateTime t)
		{
			for (int i = _gaps.Count - 1; i >= 0; i--)
			{
				GapZone g = _gaps[i];
				if (g.Archived) continue;

				// Penetración monótona desde el borde proximal
				double pen = g.IsBullish ? (g.Top - price) / g.Size : (price - g.Bottom) / g.Size;
				if (pen < 0) pen = 0;
				if (pen > 1) pen = 1;
				if (pen > g.MaxPenPct) g.MaxPenPct = pen;

				// Épocas de toque (estrictamente dentro)
				bool inside = price > g.Bottom && price < g.Top;
				if (inside && !g.InsideEpoch)
				{
					g.Touches++;
					g.InsideEpoch = true;
					if (g.Touches <= MaxLoggedTouches)
						LogEvent("ZONE_TOUCHED", g, t, price, "epoch=" + g.Touches);
					if (g.State == GapState.Virgin) { g.State = GapState.Touched; g.NeedsRedraw = true; }
				}
				else if (!inside)
					g.InsideEpoch = false;

				// Transiciones
				if (g.State == GapState.Touched && g.MaxPenPct >= PartialFillPct / 100.0)
				{
					g.State = GapState.Partial; g.NeedsRedraw = true;
					LogEvent("ZONE_PARTIAL", g, t, price, "");
				}

				if (g.MaxPenPct >= 1.0 && g.State != GapState.FullFilled && !g.Archived)
				{
					if (ReversalConfirmTicks == 0)
					{
						Invalidate(g, t, price, "full_fill", "");
						continue;
					}
					g.State = GapState.FullFilled; g.NeedsRedraw = true;
				}

				if (g.State == GapState.FullFilled)
				{
					bool inverse = g.IsBullish
						? price <= g.Bottom - ReversalConfirmTicks * TickSize
						: price >= g.Top + ReversalConfirmTicks * TickSize;
					bool backThroughProximal = g.IsBullish ? price >= g.Top : price <= g.Bottom;

					if (inverse)               Invalidate(g, t, price, "inverse", "");
					else if (backThroughProximal) Invalidate(g, t, price, "full_fill", "");
				}
			}
		}

		private void Invalidate(GapZone g, DateTime t, double price, string reason, string extra)
		{
			g.State = GapState.Invalidated;
			g.Archived = true;
			g.NeedsRedraw = true;
			LogEvent("ZONE_INVALIDATED", g, t, price, string.IsNullOrEmpty(extra) ? reason : reason + ";" + extra);
		}

		private void ExpireOldZones()
		{
			for (int i = _gaps.Count - 1; i >= 0; i--)
			{
				GapZone g = _gaps[i];
				if (g.Archived) continue;
				if (CurrentBar - g.CreatedPrimaryBar <= MaxAgeBars) continue;

				if (g.State == GapState.FullFilled)
					Invalidate(g, Time[0], Close[0], "full_fill", "resolved_by_expiry");
				else
				{
					g.State = GapState.Expired; g.Archived = true; g.NeedsRedraw = true;
					LogEvent("ZONE_EXPIRED", g, Time[0], Close[0], "");
				}
			}
		}

		private void PushVol(double v)
		{
			if (_volRing == null) return;
			if (_volCount < _volRing.Length) { _volRing[_volHead] = v; _volSum += v; _volCount++; }
			else { _volSum += v - _volRing[_volHead]; _volRing[_volHead] = v; }
			_volHead = (_volHead + 1) % _volRing.Length;
		}
		#endregion

		#region Render (solo visual)
		private void DrawZones()
		{
			if (!ShowZones) { PruneArchived(); return; }

			int drawn = 0;
			for (int i = _gaps.Count - 1; i >= 0; i--)
			{
				GapZone g = _gaps[i];
				if (!g.Display) continue;
				if (g.Archived && !g.NeedsRedraw) continue;
				if (!g.Archived && drawn >= MaxZonesDrawn) continue;

				int startBA = CurrentBar - g.CreatedPrimaryBar;
				if (startBA < 0 || startBA > CurrentBar) { g.NeedsRedraw = false; continue; }

				Brush fill = g.IsBullish ? ColorBullGap : ColorBearGap;
				Brush border = Brushes.Transparent;
				switch (g.State)
				{
					case GapState.Touched:     border = Brushes.Khaki;     break;
					case GapState.Partial:     border = Brushes.Gold;      break;
					case GapState.FullFilled:  border = Brushes.Orange;    break;
					case GapState.Invalidated: border = Brushes.DimGray;   break;
					case GapState.Expired:     border = Brushes.Gray;      break;
				}

				Draw.Rectangle(this, g.Tag, false, startBA, g.Top, 0, g.Bottom, border, fill, RectOpacity);
				g.NeedsRedraw = false;
				if (!g.Archived) drawn++;
			}
			PruneArchived();
		}

		private void PruneArchived()
		{
			for (int i = _gaps.Count - 1; i >= 0; i--)
				if (_gaps[i].Archived && !_gaps[i].NeedsRedraw)
					_gaps.RemoveAt(i);   // el dibujo final queda en el chart
		}
		#endregion

		#region Logger CSV (stream de eventos)
		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) { _log = null; return; }
			try
			{
				string dir = Path.GetDirectoryName(EventLogPath);
				if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
				_log = new StreamWriter(EventLogPath, false, new UTF8Encoding(false));
				_log.WriteLine("# meta indicator=Gaps2,version=2.0,detector=tick_jump,lifecycle=tick_exact,penetration=proximal_edge_monotonic,invalidation=full_fill_then_inverse,touch=strict_inside_epochs,units=ticks,ts_note=chart_local_plus_unix_ms_verify_tz_in_P0");
				_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"# params instrument={0},tick_size={1},min_gap_ticks={2},export_floor_ticks={3},partial_fill_pct={4},reversal_confirm_ticks={5},max_age_bars={6},vol_baseline_ticks={7},min_vol_baseline_samples={8},atr_period={9},reopen_pause_min={10},reopen_warmup_min={11},max_logged_touches={12},chart_period={13}",
					Instrument.MasterInstrument.Name, TickSize, MinGapTicks, ExportFloorTicks, PartialFillPct,
					ReversalConfirmTicks, MaxAgeBars, VolBaselineTicks, MinVolBaselineSamples, AtrPeriod,
					ReopenPauseMinutes, ReopenWarmupMinutes, MaxLoggedTouches, BarsPeriod.ToString()));
				_log.WriteLine("event_seq,event_type,ts,unix_ms,gap_id,created_unix_ms,top,bottom,size_ticks,is_bullish,atr_at_creation,vol_at_creation,vol_baseline,vol_ratio,state,max_pen_pct,touches,bars_since,price_at_event,extra");
				_log.Flush();
				Print("[Gaps2] Log de eventos: " + EventLogPath);
			}
			catch (Exception ex) { Print("[Gaps2] Error abriendo log: " + ex.Message); _log = null; }
		}

		private void CloseLog()
		{
			try
			{
				if (_log == null) return;
				double px = (CurrentBars != null && CurrentBars.Length > 0 && CurrentBars[0] >= 0) ? Close[0] : 0;
				foreach (GapZone g in _gaps)
					if (!g.Archived) LogEvent("SESSION_END", g, Time[0], px, "snapshot");
				_log.Flush();
				_log.Close();
				_log.Dispose();
				_log = null;
				Print("[Gaps2] Log cerrado.");
			}
			catch (Exception ex) { Print("[Gaps2] Error cerrando log: " + ex.Message); }
		}

		private void LogEvent(string type, GapZone g, DateTime t, double price, string extra)
		{
			if (_log == null) return;
			try
			{
				CultureInfo inv = CultureInfo.InvariantCulture;
				StringBuilder sb = new StringBuilder(256);
				sb.Append(++_seq).Append(',');
				sb.Append(type).Append(',');
				sb.Append(t.ToString("yyyy-MM-dd HH:mm:ss.fff", inv)).Append(',');
				sb.Append(ToUnixMs(t)).Append(',');
				if (g != null)
				{
					double volRatio = (!double.IsNaN(g.VolBaseline) && g.VolBaseline > 0) ? g.VolAtCreation / g.VolBaseline : double.NaN;
					int barsSince = (CurrentBars != null && CurrentBars.Length > 0 && CurrentBars[0] >= 0)
						? CurrentBars[0] - g.CreatedPrimaryBar : -1;
					sb.Append("G").Append(g.Id.ToString("D6", inv)).Append(',');
					sb.Append(g.CreatedUnixMs).Append(',');
					sb.Append(g.Top.ToString("F6", inv)).Append(',');
					sb.Append(g.Bottom.ToString("F6", inv)).Append(',');
					sb.Append(g.SizeTicks.ToString(inv)).Append(',');
					sb.Append(g.IsBullish ? "1" : "0").Append(',');
					sb.Append(Fmt(g.AtrAtCreation)).Append(',');
					sb.Append(g.VolAtCreation.ToString("F2", inv)).Append(',');
					sb.Append(Fmt(g.VolBaseline)).Append(',');
					sb.Append(Fmt(volRatio)).Append(',');
					sb.Append(g.State.ToString().ToUpperInvariant()).Append(',');
					sb.Append(g.MaxPenPct.ToString("F4", inv)).Append(',');
					sb.Append(g.Touches.ToString(inv)).Append(',');
					sb.Append(barsSince.ToString(inv)).Append(',');
				}
				else
					sb.Append(",,,,,,,,,,,,,");
				sb.Append(price.ToString("F6", inv)).Append(',');
				sb.Append(extra ?? "");
				_log.WriteLine(sb.ToString());

				// Flush: transiciones importantes siempre; el resto cada 500 filas
				if (type == "ZONE_INVALIDATED" || type == "ZONE_EXPIRED" || type == "SESSION_END" || ++_sinceFlush >= 500)
				{ _log.Flush(); _sinceFlush = 0; }
			}
			catch (Exception ex) { Print("[Gaps2] Error escribiendo log: " + ex.Message); }
		}

		private static string Fmt(double v)
		{
			return double.IsNaN(v) ? "" : v.ToString("F4", CultureInfo.InvariantCulture);
		}

		private static long ToUnixMs(DateTime t)
		{
			// Nota de contrato: usa la TZ de la máquina para convertir a UTC.
			// Verificar en gate P0 contra el export de ticks.
			return new DateTimeOffset(t.ToUniversalTime()).ToUnixTimeMilliseconds();
		}
		#endregion

		#region Propiedades
		// ── 1. Detección (investigación) ──
		[NinjaScriptProperty]
		[Range(1, 500)]
		[Display(Name = "Min gap (ticks) — display", Order = 1, GroupName = "1. Detección",
			Description = "Tamaño mínimo del gap en ticks para dibujarlo. El export usa ExportFloorTicks.")]
		public int MinGapTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 500)]
		[Display(Name = "Piso de export (ticks)", Order = 2, GroupName = "1. Detección",
			Description = "Todo gap >= este piso se exporta con ciclo de vida completo (patrón OBS). Debe ser <= MinGapTicks.")]
		public int ExportFloorTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 600)]
		[Display(Name = "Pausa de reapertura (min)", Order = 3, GroupName = "1. Detección",
			Description = "Pausa entre ticks >= este valor se trata como cierre/reapertura de mercado.")]
		public int ReopenPauseMinutes { get; set; }

		[NinjaScriptProperty]
		[Range(0, 120)]
		[Display(Name = "Warmup post-reapertura (min)", Order = 4, GroupName = "1. Detección",
			Description = "Minutos sin detección tras una reapertura.")]
		public int ReopenWarmupMinutes { get; set; }

		[NinjaScriptProperty]
		[Range(2, 200)]
		[Display(Name = "Período ATR (solo export)", Order = 5, GroupName = "1. Detección",
			Description = "ATR de la última barra primaria CERRADA. Se exporta como feature; nunca decide.")]
		public int AtrPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(100, 50000)]
		[Display(Name = "Ventana baseline volumen (ticks)", Order = 6, GroupName = "1. Detección",
			Description = "Media exacta de los últimos N volúmenes de tick, excluyendo el tick actual.")]
		public int VolBaselineTicks { get; set; }

		[NinjaScriptProperty]
		[Range(50, 50000)]
		[Display(Name = "Min muestras baseline", Order = 7, GroupName = "1. Detección",
			Description = "vol_ratio vacío hasta juntar estas muestras.")]
		public int MinVolBaselineSamples { get; set; }

		// ── 2. Ciclo de vida ──
		[NinjaScriptProperty]
		[Range(1, 99)]
		[Display(Name = "Umbral PARTIAL (%)", Order = 1, GroupName = "2. Ciclo de vida",
			Description = "Penetración mínima desde el borde proximal para PARTIAL.")]
		public int PartialFillPct { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Confirmación INVERSE (ticks)", Order = 2, GroupName = "2. Ciclo de vida",
			Description = "Ticks más allá del borde distal para reclasificar full_fill como inverse. 0 = full_fill inmediato.")]
		public int ReversalConfirmTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 50000)]
		[Display(Name = "Expiración (barras primarias)", Order = 3, GroupName = "2. Ciclo de vida",
			Description = "Depende del tipo de barra del chart: usar el chart canónico del contrato de datos.")]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty]
		[Range(1, 1000)]
		[Display(Name = "Max épocas de toque logueadas", Order = 4, GroupName = "2. Ciclo de vida")]
		public int MaxLoggedTouches { get; set; }

		// ── 3. Export ──
		[NinjaScriptProperty]
		[Display(Name = "Ruta CSV de eventos (vacío = off)", Order = 1, GroupName = "3. Export")]
		public string EventLogPath { get; set; }

		// ── 4. Visual (nunca decide) ──
		[Display(Name = "Mostrar zonas", Order = 1, GroupName = "4. Visual")]
		public bool ShowZones { get; set; }

		[Range(10, 5000)]
		[Display(Name = "Max zonas dibujadas", Order = 2, GroupName = "4. Visual")]
		public int MaxZonesDrawn { get; set; }

		[Range(0, 100)]
		[Display(Name = "Opacidad (%)", Order = 3, GroupName = "4. Visual")]
		public int RectOpacity { get; set; }

		[XmlIgnore]
		[Display(Name = "Color gap alcista", Order = 4, GroupName = "4. Visual")]
		public Brush ColorBullGap { get; set; }
		[Browsable(false)]
		public string ColorBullGapSerializable
		{ get { return Serialize.BrushToString(ColorBullGap); } set { ColorBullGap = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Color gap bajista", Order = 5, GroupName = "4. Visual")]
		public Brush ColorBearGap { get; set; }
		[Browsable(false)]
		public string ColorBearGapSerializable
		{ get { return Serialize.BrushToString(ColorBearGap); } set { ColorBearGap = Serialize.StringToBrush(value); } }
		#endregion
	}
}
