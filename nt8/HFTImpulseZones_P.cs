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

// HFTImpulseZones_P v1.0 -- zonas de impulso, disenado para PARIDAD.
//
// Reemplaza a HFTZonesNQImpulseV2_5, cuyo problema medido es que decide con
// `_timingZeroFraction >= MaxZeroIntervalFraction` (umbral 0,50) mientras el dato
// real en NQ es 0,51: la sesion entera cambia de clasificacion por un margen de
// 0,01, y por eso aparecen bloques enteros de zonas sin clasificar.
//
// Cumple docs/research/PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md:
//   1. Aritmetica ENTERA: desplazamiento en ticks, eficiencia en basis points.
//   2. SIN reloj entre ticks -- no lee timestamps ni milisegundos. El 51% de los
//      ticks de NQ comparte timestamp, asi que cualquier medida de velocidad es
//      irreproducible por construccion.
//   3. Sin mediana ni cuantil: umbrales fijos declarados sobre cantidades enteras.
//   4. Empates rotos por precio ascendente.
//   5. Sin estado ni calibracion entre sesiones: cada ventana se decide sola.
//   6. Un solo origen: OHLC + volumen de la serie primaria. NO usa subserie de
//      1 tick, que es la capa que no se reproduce desde el parquet.
//   7. Log completo por ventana evaluada.
//
// Definicion de impulso, entera y sin reloj:
//   sobre una ventana deslizante de W barras primarias,
//     desplazamiento = |closeTick(fin) - closeTick(inicio)|
//     recorrido      = suma de |closeTick(i) - closeTick(i-1)|
//     eficiencia_bps = desplazamiento * 10000 / recorrido
//   hay impulso si desplazamiento >= MinDisplacementTicks
//                y eficiencia_bps >= MinEfficiencyBps.
// La zona se ancla al extremo desde el que arranco el impulso.
//
// SENALES POR RACHA DE RAFAGAS
// Una sola ventana con impulso es un evento chico y frecuente. Lo que se busca
// como senal es la ACUMULACION: varias rafagas seguidas en la misma direccion.
//
// Definicion, entera y sin reloj:
//   - solo cuentan rafagas NO SOLAPADAS. La ventana es deslizante, asi que
//     durante un mismo movimiento disparan muchas barras consecutivas; contarlas
//     todas inflaria la racha sin que haya mas mercado. Una rafaga nueva cuenta
//     solo si empieza despues de que termino la anterior (>= WindowBars).
//   - la racha se corta si cambia la direccion o si pasan mas de
//     MaxBarsBetweenBursts barras sin una rafaga nueva. Tambien se corta en la
//     frontera de sesion: la racha no cruza sesiones.
//   - hay SENAL cuando la racha llega a MinBurstsForSignal rafagas Y el
//     desplazamiento acumulado llega a MinBurstDisplacementTicks.
//   - se emite UNA senal por racha, la primera vez que cruza el umbral. Si la
//     racha sigue creciendo, eso queda en las filas siguientes pero no genera
//     una senal nueva: una racha es un evento, no varios.
//
// La senal es una POBLACION DE EVENTOS, no una prediccion. Que tenga o no valor
// economico se mide aparte, con manifiesto y bajo el STOP del proyecto. Este
// indicador no mira retornos.

namespace NinjaTrader.NinjaScript.Indicators
{
	public class HFTImpulseZones_P : Indicator
	{
		private List<long> _closeTicks;      // cierres en ticks enteros, de la sesion en curso
		private List<long> _highTicks;
		private List<long> _lowTicks;
		private List<long> _volumes;
		private List<DateTime> _times;
		private int _sessionIndex = -1;
		private int _windowIndex;
		private int _zoneSeq;
		private StreamWriter _log;

		// --- racha de rafagas ---
		private int _burstDir;              // 1 alcista, -1 bajista, 0 sin racha
		private int _burstCount;
		private long _burstDisplacement;
		private int _burstFirstBar;
		private int _lastBurstBar = int.MinValue;
		private bool _signalEmitted;
		private int _signalSeq;

		// --- render por SharpDX ---
		// Draw.Rectangle crea un objeto de dibujo por zona y NT8 los mantiene vivos;
		// con miles de ventanas eso degrada el chart. Aca son datos y OnRender
		// recorre solo lo visible.
		private class Zone
		{
			public int StartBar;
			public int EndBar;
			public long LowerTick;
			public long UpperTick;
			public int Direction;
			public bool IsSignal;      // rafaga que disparo la senal de racha
		}
		private List<Zone> _zones;
		private SharpDX.Direct2D1.Brush _dxSupport;
		private SharpDX.Direct2D1.Brush _dxResistance;
		private SharpDX.Direct2D1.Brush _dxSignal;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "HFTImpulseZones_P";
				Description = "Zonas de impulso con definicion entera y sin reloj (paridad primero)";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				WindowBars = 12;
				MinDisplacementTicks = 16;
				MinEfficiencyBps = 6000;   // 60,00 %
				MinWindowVolume = 0;
				ZoneHeightTicks = 8;
				MinBurstsForSignal = 3;
				MaxBarsBetweenBursts = 40;
				MinBurstDisplacementTicks = 48;
				ExtendBars = 20;
				MaxZonesRendered = 2000;
				SignalColor = Brushes.Gold;
				SupportColor = Brushes.MediumSeaGreen;
				ResistanceColor = Brushes.IndianRed;
				ZoneOpacity = 30;
				EventLogPath = "";
			}
			else if (State == State.DataLoaded)
			{
				_closeTicks = new List<long>();
				_highTicks = new List<long>();
				_lowTicks = new List<long>();
				_volumes = new List<long>();
				_times = new List<DateTime>();
				_zones = new List<Zone>();
				_zoneSeq = 0;
				_signalSeq = 0;
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (_log != null) { _log.Flush(); _log.Dispose(); _log = null; }
				DisposeDxBrushes();
			}
		}

		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				_log = new StreamWriter(EventLogPath, false, Encoding.UTF8);
				_log.WriteLine("# meta,indicator=HFTImpulseZones_P,version=1.0,contract=parity_first_v1"
					+ ",window_bars=" + WindowBars
					+ ",min_displacement_ticks=" + MinDisplacementTicks
					+ ",min_efficiency_bps=" + MinEfficiencyBps
					+ ",min_window_volume=" + MinWindowVolume
					+ ",zone_height_ticks=" + ZoneHeightTicks
					+ ",min_bursts_for_signal=" + MinBurstsForSignal
					+ ",max_bars_between_bursts=" + MaxBarsBetweenBursts
					+ ",min_burst_displacement_ticks=" + MinBurstDisplacementTicks
					+ ",bursts_counted=non_overlapping,signal_scope=one_per_streak"
					+ ",uses_tick_clock=false,uses_tick_subseries=false");
				_log.WriteLine("window_index,bar_close_time_utc,session_index,start_close_tick,"
					+ "end_close_tick,displacement_ticks,path_ticks,efficiency_bps,window_volume,"
					+ "decision,direction,zone_lower_tick,zone_upper_tick,"
					+ "burst_dir,burst_count,burst_displacement_ticks,burst_first_bar,"
					+ "is_signal,signal_seq,closes");
			}
			catch { _log = null; }
		}

		private long PriceToTick(double price)
		{
			return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 0) return;

			// REGLA 5: reset explicito en el limite de sesion, sin calibracion arrastrada
			if (Bars.IsFirstBarOfSession)
			{
				_sessionIndex++;
				_closeTicks.Clear(); _highTicks.Clear(); _lowTicks.Clear();
				_volumes.Clear(); _times.Clear();
				_windowIndex = 0;
				_burstDir = 0; _burstCount = 0; _burstDisplacement = 0;
				_lastBurstBar = int.MinValue; _signalEmitted = false;
			}

			// REGLA 6: unico origen -- OHLC y volumen de la serie primaria
			_closeTicks.Add(PriceToTick(Close[0]));
			_highTicks.Add(PriceToTick(High[0]));
			_lowTicks.Add(PriceToTick(Low[0]));
			_volumes.Add((long)Volume[0]);
			_times.Add(Time[0]);

			if (_closeTicks.Count < WindowBars) return;

			int n = _closeTicks.Count;
			int s = n - WindowBars;          // inicio de la ventana
			int e = n - 1;                   // fin de la ventana

			long startTick = _closeTicks[s];
			long endTick = _closeTicks[e];
			long displacement = Math.Abs(endTick - startTick);

			long path = 0;                   // recorrido total, entero
			long windowVolume = 0;
			for (int i = s + 1; i <= e; i++) path += Math.Abs(_closeTicks[i] - _closeTicks[i - 1]);
			for (int i = s; i <= e; i++) windowVolume += _volumes[i];

			// REGLA 1: eficiencia en basis points ENTEROS, sin floats
			long effBps = path > 0 ? (displacement * 10000L) / path : 0L;

			string decision;
			int direction = 0;
			long zLower = 0, zUpper = 0;
			bool isSignal = false;

			if (windowVolume < MinWindowVolume) decision = "ABSTAIN_LOW_VOLUME";
			else if (displacement < MinDisplacementTicks) decision = "ABSTAIN_SHORT_DISPLACEMENT";
			else if (effBps < MinEfficiencyBps) decision = "ABSTAIN_LOW_EFFICIENCY";
			else
			{
				decision = "CREATE";
				direction = endTick > startTick ? 1 : -1;
				if (direction == 1)
				{
					// impulso alcista: la zona queda en el piso desde donde arranco
					long baseTick = _lowTicks[s];
					for (int i = s; i <= e; i++) if (_lowTicks[i] < baseTick) baseTick = _lowTicks[i];
					zLower = baseTick;
					zUpper = baseTick + ZoneHeightTicks;
				}
				else
				{
					long baseTick = _highTicks[s];
					for (int i = s; i <= e; i++) if (_highTicks[i] > baseTick) baseTick = _highTicks[i];
					zUpper = baseTick;
					zLower = baseTick - ZoneHeightTicks;
				}
				_zoneSeq++;

				// --- racha de rafagas NO SOLAPADAS ---
				// Una ventana deslizante dispara en muchas barras consecutivas durante
				// el mismo movimiento. Contarlas todas inflaria la racha sin que haya
				// mas mercado, asi que una rafaga nueva solo cuenta si empieza despues
				// de que termino la anterior.
				bool cuenta = _lastBurstBar == int.MinValue
					|| CurrentBar - _lastBurstBar >= WindowBars;
				if (cuenta)
				{
					bool sigue = _burstDir == direction
						&& _lastBurstBar != int.MinValue
						&& CurrentBar - _lastBurstBar <= MaxBarsBetweenBursts;
					if (sigue)
					{
						_burstCount++;
						_burstDisplacement += displacement;
					}
					else
					{
						_burstDir = direction;
						_burstCount = 1;
						_burstDisplacement = displacement;
						_burstFirstBar = CurrentBar - (WindowBars - 1);
						_signalEmitted = false;
					}
					_lastBurstBar = CurrentBar;

					if (!_signalEmitted
						&& _burstCount >= MinBurstsForSignal
						&& _burstDisplacement >= MinBurstDisplacementTicks)
					{
						_signalEmitted = true;
						_signalSeq++;
						isSignal = true;
					}
				}

				Zone z = new Zone();
				z.StartBar = CurrentBar - (WindowBars - 1);
				if (z.StartBar < 0) z.StartBar = 0;
				z.EndBar = CurrentBar + (ExtendBars < 0 ? 0 : ExtendBars);
				z.LowerTick = zLower;
				z.UpperTick = zUpper;
				z.Direction = direction;
				z.IsSignal = isSignal;
				_zones.Add(z);
				if (MaxZonesRendered > 0 && _zones.Count > MaxZonesRendered)
					_zones.RemoveRange(0, _zones.Count - MaxZonesRendered);
			}

			WriteRow(startTick, endTick, displacement, path, effBps, windowVolume,
				decision, direction, zLower, zUpper, s, e, isSignal);
			_windowIndex++;
		}

		private void DisposeDxBrushes()
		{
			if (_dxSupport != null) { _dxSupport.Dispose(); _dxSupport = null; }
			if (_dxResistance != null) { _dxResistance.Dispose(); _dxResistance = null; }
			if (_dxSignal != null) { _dxSignal.Dispose(); _dxSignal = null; }
		}

		public override void OnRenderTargetChanged()
		{
			// El RenderTarget se recrea al redimensionar o cambiar de pantalla: los
			// brushes viejos quedan invalidos y hay que soltarlos SIEMPRE.
			DisposeDxBrushes();
			if (RenderTarget == null) return;
			try
			{
				float op = ZoneOpacity / 100f;
				_dxSupport = SupportColor.ToDxBrush(RenderTarget);
				_dxResistance = ResistanceColor.ToDxBrush(RenderTarget);
				_dxSignal = SignalColor.ToDxBrush(RenderTarget);
				_dxSupport.Opacity = op;
				_dxResistance.Opacity = op;
				_dxSignal.Opacity = 1f;      // la senal se ve entera, no es una zona mas
			}
			catch { DisposeDxBrushes(); }
		}

		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (Bars == null || ChartBars == null || RenderTarget == null) return;
			if (_zones == null || _zones.Count == 0) return;
			if (_dxSupport == null) OnRenderTargetChanged();
			if (_dxSupport == null) return;

			int from = ChartBars.FromIndex;
			int to = ChartBars.ToIndex;
			float half = (float)chartControl.Properties.BarDistance / 2f;

			// Aliased da el borde nitido; en PerPrimitive un rectangulo alineado a
			// pixel sale borroso. Se restaura en finally.
			SharpDX.Direct2D1.AntialiasMode prev = RenderTarget.AntialiasMode;
			RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.Aliased;
			try
			{
				for (int i = 0; i < _zones.Count; i++)
				{
					Zone z = _zones[i];
					if (z.EndBar < from || z.StartBar > to) continue;

					int a = z.StartBar < from ? from : z.StartBar;
					int b = z.EndBar > to ? to : z.EndBar;
					float x1 = chartControl.GetXByBarIndex(ChartBars, a) - half;
					float x2 = chartControl.GetXByBarIndex(ChartBars, b) + half;
					float yTop = chartScale.GetYByValue((z.UpperTick + 0.5) * TickSize);
					float yBot = chartScale.GetYByValue((z.LowerTick - 0.5) * TickSize);
					float w = x2 - x1; if (w < 1f) w = 1f;
					float h = yBot - yTop; if (h < 1f) h = 1f;

					RenderTarget.FillRectangle(new SharpDX.RectangleF(x1, yTop, w, h),
						z.Direction == 1 ? _dxSupport : _dxResistance);

					// La senal se marca EN LA BARRA DONDE DISPARO, que es la del
					// cierre de la ventana -- no en el borde izquierdo de la zona, que
					// esta WindowBars-1 barras antes y haria parecer que disparo antes.
					// La zona se dibuja hacia atras porque describe de donde arranco el
					// impulso; la decision, en cambio, ocurre al final.
					if (z.IsSignal)
					{
						int barSenal = z.StartBar + WindowBars - 1;
						if (barSenal >= from && barSenal <= to)
						{
							float xs = chartControl.GetXByBarIndex(ChartBars, barSenal);
							float top = chartScale.GetYByValue(chartScale.MaxValue);
							float bot = chartScale.GetYByValue(chartScale.MinValue);
							// linea vertical de panel completo: se ve donde disparo aunque
							// la zona quede fuera de la vista vertical
							RenderTarget.FillRectangle(
								new SharpDX.RectangleF(xs - 1f, top, 2f, bot - top), _dxSignal);
							// y un bloque solido sobre la zona, para el lado
							RenderTarget.FillRectangle(
								new SharpDX.RectangleF(xs - half, yTop, half * 2f, h), _dxSignal);
						}
					}
				}
			}
			finally
			{
				RenderTarget.AntialiasMode = prev;
			}
		}

		private void WriteRow(long startTick, long endTick, long displacement, long path,
			long effBps, long windowVolume, string decision, int direction,
			long zLower, long zUpper, int s, int e, bool isSignal)
		{
			if (_log == null) return;
			// REGLA 7: la serie de cierres que decidio, para cruce barra a barra
			StringBuilder sb = new StringBuilder();
			for (int i = s; i <= e; i++)
			{
				if (i > s) sb.Append('|');
				sb.Append(_closeTicks[i]);
			}
			_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
				"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},"
				+ "{13},{14},{15},{16},{17},{18},{19}",
				_windowIndex,
				Time[0].ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture),
				_sessionIndex, startTick, endTick, displacement, path, effBps, windowVolume,
				decision, direction,
				decision == "CREATE" ? zLower.ToString(CultureInfo.InvariantCulture) : "",
				decision == "CREATE" ? zUpper.ToString(CultureInfo.InvariantCulture) : "",
				_burstDir, _burstCount, _burstDisplacement, _burstFirstBar,
				isSignal ? 1 : 0, isSignal ? _signalSeq : 0,
				sb.ToString()));
			_log.Flush();
		}

		#region Properties
		[NinjaScriptProperty] [Range(2, 500)]
		[Display(Name = "WindowBars", Order = 1, GroupName = "Impulso")]
		public int WindowBars { get; set; }

		[NinjaScriptProperty] [Range(1, 10000)]
		[Display(Name = "MinDisplacementTicks", Order = 2, GroupName = "Impulso")]
		public int MinDisplacementTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 10000)]
		[Display(Name = "MinEfficiencyBps", Description = "Desplazamiento sobre recorrido, en basis points enteros",
			Order = 3, GroupName = "Impulso")]
		public int MinEfficiencyBps { get; set; }

		[NinjaScriptProperty] [Range(0, 100000000)]
		[Display(Name = "MinWindowVolume", Order = 4, GroupName = "Impulso")]
		public long MinWindowVolume { get; set; }

		[NinjaScriptProperty] [Range(1, 1000)]
		[Display(Name = "ZoneHeightTicks", Order = 5, GroupName = "Zona")]
		public int ZoneHeightTicks { get; set; }

		[XmlIgnore] [Display(Name = "SupportColor", Order = 6, GroupName = "Visual")]
		public Brush SupportColor { get; set; }
		[Browsable(false)]
		public string SupportColorSerialize
		{
			get { return Serialize.BrushToString(SupportColor); }
			set { SupportColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "ResistanceColor", Order = 7, GroupName = "Visual")]
		public Brush ResistanceColor { get; set; }
		[Browsable(false)]
		public string ResistanceColorSerialize
		{
			get { return Serialize.BrushToString(ResistanceColor); }
			set { ResistanceColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "ZoneOpacity", Order = 8, GroupName = "Visual")]
		public int ZoneOpacity { get; set; }

		[NinjaScriptProperty] [Range(1, 100)]
		[Display(Name = "MinBurstsForSignal", Order = 10, GroupName = "Racha",
			Description = "Rafagas NO SOLAPADAS en la misma direccion que hacen falta para "
				+ "que haya senal. 1 convierte cada rafaga en senal.")]
		public int MinBurstsForSignal { get; set; }

		[NinjaScriptProperty] [Range(1, 100000)]
		[Display(Name = "MaxBarsBetweenBursts", Order = 11, GroupName = "Racha",
			Description = "Barras maximas entre dos rafagas para que sigan siendo la misma "
				+ "racha. Mas alla, la racha se corta y arranca una nueva.")]
		public int MaxBarsBetweenBursts { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MinBurstDisplacementTicks", Order = 12, GroupName = "Racha",
			Description = "Desplazamiento ACUMULADO de la racha, en ticks, que hace falta "
				+ "para la senal. Filtra rachas de muchas rafagas chicas.")]
		public int MinBurstDisplacementTicks { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "ExtendBars", Order = 13, GroupName = "Zona",
			Description = "Barras que la zona se extiende a la derecha. Visual.")]
		public int ExtendBars { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MaxZonesRendered", Order = 14, GroupName = "Zona",
			Description = "Cota de memoria del render. El CSV no se recorta nunca.")]
		public int MaxZonesRendered { get; set; }

		[XmlIgnore] [Display(Name = "SignalColor", Order = 15, GroupName = "Visual")]
		public Brush SignalColor { get; set; }
		[Browsable(false)]
		public string SignalColorSerialize
		{
			get { return Serialize.BrushToString(SignalColor); }
			set { SignalColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty]
		[Display(Name = "EventLogPath", Description = "CSV de ventanas para el cruce de paridad",
			Order = 9, GroupName = "Auditoria")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
