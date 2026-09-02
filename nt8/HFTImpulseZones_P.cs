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
using NinjaTrader.NinjaScript.DrawingTools;
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
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (_log != null) { _log.Flush(); _log.Dispose(); _log = null; }
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
					+ ",uses_tick_clock=false,uses_tick_subseries=false");
				_log.WriteLine("window_index,bar_close_time_utc,session_index,start_close_tick,"
					+ "end_close_tick,displacement_ticks,path_ticks,efficiency_bps,window_volume,"
					+ "decision,direction,zone_lower_tick,zone_upper_tick,closes");
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
				Draw.Rectangle(this, "hiz" + _zoneSeq, false, _times[s], (zLower - 0.5) * TickSize,
					Time[0], (zUpper + 0.5) * TickSize, Brushes.Transparent,
					direction == 1 ? SupportColor : ResistanceColor, ZoneOpacity);
			}

			WriteRow(startTick, endTick, displacement, path, effBps, windowVolume,
				decision, direction, zLower, zUpper, s, e);
			_windowIndex++;
		}

		private void WriteRow(long startTick, long endTick, long displacement, long path,
			long effBps, long windowVolume, string decision, int direction,
			long zLower, long zUpper, int s, int e)
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
				"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13}",
				_windowIndex,
				Time[0].ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture),
				_sessionIndex, startTick, endTick, displacement, path, effBps, windowVolume,
				decision, direction,
				decision == "CREATE" ? zLower.ToString(CultureInfo.InvariantCulture) : "",
				decision == "CREATE" ? zUpper.ToString(CultureInfo.InvariantCulture) : "",
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

		[NinjaScriptProperty]
		[Display(Name = "EventLogPath", Description = "CSV de ventanas para el cruce de paridad",
			Order = 9, GroupName = "Auditoria")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
