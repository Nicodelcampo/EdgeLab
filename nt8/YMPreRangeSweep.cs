#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class YMPreRangeSweep : Indicator
	{
		#region Enums
		public enum PreRangeOutcome
		{
			None,
			OnlyHighSwept,
			OnlyLowSwept,
			BothSweptHighFirst,
			BothSweptLowFirst,
			SameBarBoth
		}
		#endregion

		#region Variables
		private int currentSession = -1;
		private SessionIterator sessionIterator;
		private bool inWindow = false;
		private bool windowCompleted = false;

		private double rangeHigh = double.MinValue;
		private double rangeLow = double.MaxValue;
		private DateTime rangeStartTime = DateTime.MinValue;
		private DateTime rangeEndTime = DateTime.MinValue;
		private int rangeStartBar = -1;
		private int rangeEndBar = -1;
		private long rangeVolume = 0;

		// Post-window sweep tracking
		private bool highSwept = false;
		private bool lowSwept = false;
		private string firstSweepSide = "NONE";
		private DateTime firstSweepTime = DateTime.MinValue;
		private int firstSweepLag = 0;
		private double firstSweepMaxExt = 0; // Max extension beyond first level

		private bool secondSweep = false;
		private DateTime secondSweepTime = DateTime.MinValue;
		private int secondSweepLag = 0;

		private PreRangeOutcome sessionOutcome = PreRangeOutcome.None;

		private StreamWriter writer;
		private bool writerFailed = false;
		#endregion

		#region Properties
		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name = "Start Hour (Local Chart Time)", Description = "Hora de inicio de la ventana en hora de tu gráfico", Order = 1, GroupName = "1. Configuración de Ventana")]
		public int StartHour { get; set; }

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name = "Start Minute", Description = "Minuto de inicio de la ventana", Order = 2, GroupName = "1. Configuración de Ventana")]
		public int StartMinute { get; set; }

		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name = "End Hour (Local Chart Time)", Description = "Hora de fin de la ventana en hora de tu gráfico", Order = 3, GroupName = "1. Configuración de Ventana")]
		public int EndHour { get; set; }

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name = "End Minute", Description = "Minuto de fin de la ventana", Order = 4, GroupName = "1. Configuración de Ventana")]
		public int EndMinute { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "CSV Export Path", Description = "Ruta completa del archivo CSV para exportar datos", Order = 5, GroupName = "2. Registro y Datos")]
		public string EventLogPath { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Draw Visual Boxes", Description = "Dibujar cajas del rango y etiquetas de barrido en el gráfico", Order = 6, GroupName = "3. Visual")]
		public bool DrawVisuals { get; set; }
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Detector y registrador de eventos de la ventana YM-PRERANGE para análisis estadístico.";
				Name = "YMPreRangeSweep";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = true;
				DrawOnPricePanel = true;

				// Por defecto: 08:12 a 09:12 (modificable al horario de tu gráfico)
				StartHour = 8;
				StartMinute = 12;
				EndHour = 9;
				EndMinute = 12;

				EventLogPath = @"C:\EdgeLab\ym_prerange_events.csv";
				DrawVisuals = true;
			}
			else if (State == State.DataLoaded)
			{
				sessionIterator = new SessionIterator(Bars);
				currentSession = -1;
				ResetSession();

				InitWriter();
			}
			else if (State == State.Terminated)
			{
				CloseWriter();
			}
		}

		private void InitWriter()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				string dir = Path.GetDirectoryName(EventLogPath);
				if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
					Directory.CreateDirectory(dir);

				bool exists = File.Exists(EventLogPath);
				writer = new StreamWriter(EventLogPath, false); // Sobrescribir para nueva corrida limpia
				
				// Header formal
				writer.WriteLine("session_date,window_start,window_end,window_high,window_low,range_pts,first_sweep_side,first_sweep_time,first_sweep_lag_bars,second_sweep_occurred,second_sweep_time,second_sweep_lag_bars,max_ext_first_pts,outcome");
				writer.Flush();
			}
			catch
			{
				writerFailed = true;
			}
		}

		private void CloseWriter()
		{
			if (writer != null)
			{
				try
				{
					writer.Flush();
					writer.Close();
				}
				catch { }
				finally
				{
					writer = null;
				}
			}
		}

		private void ResetSession()
		{
			inWindow = false;
			windowCompleted = false;
			rangeHigh = double.MinValue;
			rangeLow = double.MaxValue;
			rangeStartTime = DateTime.MinValue;
			rangeEndTime = DateTime.MinValue;
			rangeStartBar = -1;
			rangeEndBar = -1;
			rangeVolume = 0;

			highSwept = false;
			lowSwept = false;
			firstSweepSide = "NONE";
			firstSweepTime = DateTime.MinValue;
			firstSweepLag = 0;
			firstSweepMaxExt = 0;

			secondSweep = false;
			secondSweepTime = DateTime.MinValue;
			secondSweepLag = 0;
			sessionOutcome = PreRangeOutcome.None;
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 1) return;

			DateTime barTime = Time[0];
			bool isNewSession = sessionIterator.IsNewSession(barTime, false);
			if (isNewSession)
			{
				if (windowCompleted)
				{
					RecordSessionOutcome();
				}
				currentSession++;
				ResetSession();
			}

			// Verificación de ventana horaria (en la hora del gráfico)
			TimeSpan startTs = new TimeSpan(StartHour, StartMinute, 0);
			TimeSpan endTs = new TimeSpan(EndHour, EndMinute, 0);
			TimeSpan curTs = barTime.TimeOfDay;

			bool isInsideWindow = (curTs >= startTs && curTs <= endTs);

			// Fase 1: Dentro de la ventana (construcción del rango)
			if (isInsideWindow)
			{
				if (!inWindow)
				{
					inWindow = true;
					rangeStartTime = barTime;
					rangeStartBar = CurrentBar;
					rangeHigh = High[0];
					rangeLow = Low[0];
					rangeVolume = (long)Volume[0];
				}
				else
				{
					rangeHigh = Math.Max(rangeHigh, High[0]);
					rangeLow = Math.Min(rangeLow, Low[0]);
					rangeVolume += (long)Volume[0];
				}
				rangeEndTime = barTime;
				rangeEndBar = CurrentBar;
			}
			else if (inWindow && !windowCompleted && curTs > endTs)
			{
				// Cierre de la ventana
				inWindow = false;
				windowCompleted = true;

				if (DrawVisuals && rangeStartBar > 0)
				{
					string tag = "PreRangeBox_" + barTime.ToString("yyyyMMdd");
					Draw.Rectangle(this, tag, false, CurrentBar - rangeStartBar, rangeHigh, 0, rangeLow, Brushes.Transparent, Brushes.RoyalBlue, 2);
				}
			}

			// Fase 2: Seguimiento de barridos posteriores
			if (windowCompleted)
			{
				int lagFromEnd = CurrentBar - rangeEndBar;
				bool barHitHigh = (High[0] >= rangeHigh);
				bool barHitLow = (Low[0] <= rangeLow);

				if (firstSweepSide == "NONE")
				{
					if (barHitHigh && barHitLow)
					{
						firstSweepSide = "BOTH_SAME_BAR";
						firstSweepTime = barTime;
						firstSweepLag = lagFromEnd;
						sessionOutcome = PreRangeOutcome.SameBarBoth;
					}
					else if (barHitHigh)
					{
						firstSweepSide = "HIGH";
						firstSweepTime = barTime;
						firstSweepLag = lagFromEnd;
						highSwept = true;
						firstSweepMaxExt = High[0] - rangeHigh;
						sessionOutcome = PreRangeOutcome.OnlyHighSwept;

						if (DrawVisuals)
							Draw.ArrowDown(this, "SweepH_" + barTime.ToString("yyyyMMdd_HHmm"), false, 0, High[0] + 2 * TickSize, Brushes.Red);
					}
					else if (barHitLow)
					{
						firstSweepSide = "LOW";
						firstSweepTime = barTime;
						firstSweepLag = lagFromEnd;
						lowSwept = true;
						firstSweepMaxExt = rangeLow - Low[0];
						sessionOutcome = PreRangeOutcome.OnlyLowSwept;

						if (DrawVisuals)
							Draw.ArrowUp(this, "SweepL_" + barTime.ToString("yyyyMMdd_HHmm"), false, 0, Low[0] - 2 * TickSize, Brushes.LimeGreen);
					}
				}
				else if (!secondSweep)
				{
					if (firstSweepSide == "HIGH")
					{
						firstSweepMaxExt = Math.Max(firstSweepMaxExt, High[0] - rangeHigh);
						if (barHitLow)
						{
							secondSweep = true;
							secondSweepTime = barTime;
							secondSweepLag = lagFromEnd;
							lowSwept = true;
							sessionOutcome = PreRangeOutcome.BothSweptHighFirst;

							if (DrawVisuals)
								Draw.Text(this, "BothSwept_" + barTime.ToString("yyyyMMdd_HHmm"), "2do Sweep (L)", 0, Low[0] - 4 * TickSize, Brushes.Gold);
						}
					}
					else if (firstSweepSide == "LOW")
					{
						firstSweepMaxExt = Math.Max(firstSweepMaxExt, rangeLow - Low[0]);
						if (barHitHigh)
						{
							secondSweep = true;
							secondSweepTime = barTime;
							secondSweepLag = lagFromEnd;
							highSwept = true;
							sessionOutcome = PreRangeOutcome.BothSweptLowFirst;

							if (DrawVisuals)
								Draw.Text(this, "BothSwept_" + barTime.ToString("yyyyMMdd_HHmm"), "2do Sweep (H)", 0, High[0] + 4 * TickSize, Brushes.Gold);
						}
					}
				}
			}
		}

		private void RecordSessionOutcome()
		{
			if (writer == null || writerFailed || !windowCompleted || rangeHigh <= rangeLow) return;

			try
			{
				double rangePts = rangeHigh - rangeLow;
				string sDate = rangeStartTime.ToString("yyyy-MM-dd");
				string sStart = rangeStartTime.ToString("HH:mm:ss");
				string sEnd = rangeEndTime.ToString("HH:mm:ss");

				string sFirstTime = firstSweepTime == DateTime.MinValue ? "" : firstSweepTime.ToString("yyyy-MM-dd HH:mm:ss");
				string sSecondTime = secondSweepTime == DateTime.MinValue ? "" : secondSweepTime.ToString("yyyy-MM-dd HH:mm:ss");

				string line = string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3:F2},{4:F2},{5:F2},{6},{7},{8},{9},{10},{11},{12:F2},{13}",
					sDate,
					sStart,
					sEnd,
					rangeHigh,
					rangeLow,
					rangePts,
					firstSweepSide,
					sFirstTime,
					firstSweepLag,
					secondSweep ? "TRUE" : "FALSE",
					sSecondTime,
					secondSweepLag,
					firstSweepMaxExt,
					sessionOutcome.ToString()
				);

				writer.WriteLine(line);
				writer.Flush();
			}
			catch { }
		}
	}
}
