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
		#region Variables
		private int startH = 9;
		private int startM = 12;
		private int endH = 10;
		private int endM = 12;
		private string logPath = @"C:\EdgeLab\ym_prerange_events.csv";
		private bool drawEnabled = true;

		private DateTime currentDay = DateTime.MinValue;
		private bool windowOpen = false;
		private bool windowDone = false;

		private double rangeHigh = double.MinValue;
		private double rangeLow = double.MaxValue;
		private DateTime winStartTime = DateTime.MinValue;
		private DateTime winEndTime = DateTime.MinValue;
		private int winStartBar = -1;
		private int winEndBar = -1;

		private bool highSwept = false;
		private bool lowSwept = false;
		private string firstSweepSide = "NONE";
		private DateTime firstSweepTime = DateTime.MinValue;
		private int firstSweepLag = 0;
		private double firstSweepMaxExt = 0;

		private bool secondSweep = false;
		private DateTime secondSweepTime = DateTime.MinValue;
		private int secondSweepLag = 0;

		private string sessionOutcome = "NONE";
		private HashSet<string> loggedDays = new HashSet<string>();

		private StreamWriter writer;
		private bool writerFailed = false;
		#endregion

		#region Properties
		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name = "1. Start Hour", Description = "Hora de inicio en tu gráfico (ej: 9 para 09:12 Arg)", Order = 1, GroupName = "1. Ventana Horaria")]
		public int StartHour
		{
			get { return startH; }
			set { startH = value; }
		}

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name = "2. Start Minute", Description = "Minuto de inicio en tu gráfico (ej: 12)", Order = 2, GroupName = "1. Ventana Horaria")]
		public int StartMinute
		{
			get { return startM; }
			set { startM = value; }
		}

		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name = "3. End Hour", Description = "Hora de fin en tu gráfico (ej: 10 para 10:12 Arg)", Order = 3, GroupName = "1. Ventana Horaria")]
		public int EndHour
		{
			get { return endH; }
			set { endH = value; }
		}

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name = "4. End Minute", Description = "Minuto de fin en tu gráfico (ej: 12)", Order = 4, GroupName = "1. Ventana Horaria")]
		public int EndMinute
		{
			get { return endM; }
			set { endM = value; }
		}

		[NinjaScriptProperty]
		[Display(Name = "5. CSV Export Path", Description = "Ruta completa del archivo CSV para exportar datos", Order = 5, GroupName = "2. Registro y Datos")]
		public string EventLogPath
		{
			get { return logPath; }
			set { logPath = value; }
		}

		[NinjaScriptProperty]
		[Display(Name = "6. Draw Visuals", Description = "Dibujar cajas del rango y flechas de barrido en el gráfico", Order = 6, GroupName = "3. Visual")]
		public bool DrawVisuals
		{
			get { return drawEnabled; }
			set { drawEnabled = value; }
		}
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

				StartHour = 9;
				StartMinute = 12;
				EndHour = 10;
				EndMinute = 12;
				EventLogPath = @"C:\EdgeLab\ym_prerange_events.csv";
				DrawVisuals = true;
			}
			else if (State == State.DataLoaded)
			{
				currentDay = DateTime.MinValue;
				loggedDays.Clear();
				ResetState();
				InitWriter();
			}
			else if (State == State.Terminated)
			{
				if (windowDone)
				{
					FlushDayRecord();
				}
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

				writer = new StreamWriter(EventLogPath, false);
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

		private void ResetState()
		{
			windowOpen = false;
			windowDone = false;
			rangeHigh = double.MinValue;
			rangeLow = double.MaxValue;
			winStartTime = DateTime.MinValue;
			winEndTime = DateTime.MinValue;
			winStartBar = -1;
			winEndBar = -1;

			highSwept = false;
			lowSwept = false;
			firstSweepSide = "NONE";
			firstSweepTime = DateTime.MinValue;
			firstSweepLag = 0;
			firstSweepMaxExt = 0;

			secondSweep = false;
			secondSweepTime = DateTime.MinValue;
			secondSweepLag = 0;
			sessionOutcome = "NONE";
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 1) return;

			DateTime t = Time[0];

			// Cambio de día calendario
			if (t.Date != currentDay)
			{
				if (windowDone)
				{
					FlushDayRecord();
				}
				currentDay = t.Date;
				ResetState();
			}

			int barMin = t.Hour * 60 + t.Minute;
			int startMin = StartHour * 60 + StartMinute;
			int endMin = EndHour * 60 + EndMinute;

			// 1. Acumulación de rango dentro de la ventana
			if (barMin >= startMin && barMin <= endMin)
			{
				if (!windowOpen)
				{
					windowOpen = true;
					winStartTime = t;
					winStartBar = CurrentBar;
					rangeHigh = High[0];
					rangeLow = Low[0];
				}
				else
				{
					rangeHigh = Math.Max(rangeHigh, High[0]);
					rangeLow = Math.Min(rangeLow, Low[0]);
				}
				winEndTime = t;
				winEndBar = CurrentBar;
			}
			else if (windowOpen && !windowDone && barMin > endMin)
			{
				// La ventana acaba de terminar
				windowOpen = false;
				windowDone = true;

				if (DrawVisuals && rangeHigh > rangeLow && winStartBar > 0)
				{
					string boxTag = "YMBox_" + winStartTime.ToString("yyyyMMdd");
					int barsBack = CurrentBar - winStartBar;

					// Dibujar rectángulo del rango
					Draw.Rectangle(this, boxTag, false, barsBack, rangeHigh, 0, rangeLow, Brushes.RoyalBlue, Brushes.LightSteelBlue, 40);

					// Dibujar líneas horizontales de los niveles proyectadas
					Draw.Line(this, boxTag + "_H", false, 0, rangeHigh, -150, rangeHigh, Brushes.Crimson, DashStyleHelper.Dash, 2);
					Draw.Line(this, boxTag + "_L", false, 0, rangeLow, -150, rangeLow, Brushes.ForestGreen, DashStyleHelper.Dash, 2);

					// Texto informativo con tamaño del rango
					double pts = rangeHigh - rangeLow;
					Draw.Text(this, boxTag + "_Txt", string.Format("Rango: {0:F0} pts", pts), 0, rangeHigh + 4 * TickSize, Brushes.DodgerBlue);
				}
			}

			// 2. Detección de barridos post-ventana
			if (windowDone && rangeHigh > rangeLow)
			{
				int lag = CurrentBar - winEndBar;
				bool hitH = (High[0] >= rangeHigh);
				bool hitL = (Low[0] <= rangeLow);

				if (firstSweepSide == "NONE")
				{
					if (hitH && hitL)
					{
						firstSweepSide = "BOTH_SAME_BAR";
						firstSweepTime = t;
						firstSweepLag = lag;
						sessionOutcome = "SameBarBoth";

						if (DrawVisuals)
							Draw.Text(this, "SweepBoth_" + t.ToString("yyyyMMdd_HHmm"), "1er Sweep Ambos (SameBar)", 0, High[0] + 6 * TickSize, Brushes.Orange);
					}
					else if (hitH)
					{
						firstSweepSide = "HIGH";
						firstSweepTime = t;
						firstSweepLag = lag;
						highSwept = true;
						firstSweepMaxExt = High[0] - rangeHigh;
						sessionOutcome = "OnlyHighSwept";

						if (DrawVisuals)
							Draw.ArrowDown(this, "SweepH_" + t.ToString("yyyyMMdd_HHmm"), false, 0, High[0] + 4 * TickSize, Brushes.Red);
					}
					else if (hitL)
					{
						firstSweepSide = "LOW";
						firstSweepTime = t;
						firstSweepLag = lag;
						lowSwept = true;
						firstSweepMaxExt = rangeLow - Low[0];
						sessionOutcome = "OnlyLowSwept";

						if (DrawVisuals)
							Draw.ArrowUp(this, "SweepL_" + t.ToString("yyyyMMdd_HHmm"), false, 0, Low[0] - 4 * TickSize, Brushes.LimeGreen);
					}
				}
				else if (!secondSweep)
				{
					if (firstSweepSide == "HIGH")
					{
						firstSweepMaxExt = Math.Max(firstSweepMaxExt, High[0] - rangeHigh);
						if (hitL)
						{
							secondSweep = true;
							secondSweepTime = t;
							secondSweepLag = lag;
							lowSwept = true;
							sessionOutcome = "BothSweptHighFirst";

							if (DrawVisuals)
								Draw.Text(this, "BothSwept_" + t.ToString("yyyyMMdd_HHmm"), "★ 2do Sweep (L)", 0, Low[0] - 8 * TickSize, Brushes.Gold);
						}
					}
					else if (firstSweepSide == "LOW")
					{
						firstSweepMaxExt = Math.Max(firstSweepMaxExt, rangeLow - Low[0]);
						if (hitH)
						{
							secondSweep = true;
							secondSweepTime = t;
							secondSweepLag = lag;
							highSwept = true;
							sessionOutcome = "BothSweptLowFirst";

							if (DrawVisuals)
								Draw.Text(this, "BothSwept_" + t.ToString("yyyyMMdd_HHmm"), "★ 2do Sweep (H)", 0, High[0] + 8 * TickSize, Brushes.Gold);
						}
					}
				}
			}
		}

		private void FlushDayRecord()
		{
			if (writer == null || writerFailed || !windowDone || rangeHigh <= rangeLow) return;

			string dayKey = winStartTime.ToString("yyyyMMdd");
			if (loggedDays.Contains(dayKey)) return;
			loggedDays.Add(dayKey);

			try
			{
				double rangePts = rangeHigh - rangeLow;
				string sDate = winStartTime.ToString("yyyy-MM-dd");
				string sStart = winStartTime.ToString("HH:mm:ss");
				string sEnd = winEndTime.ToString("HH:mm:ss");

				string sFirstTime = (firstSweepTime == DateTime.MinValue) ? "" : firstSweepTime.ToString("yyyy-MM-dd HH:mm:ss");
				string sSecondTime = (secondSweepTime == DateTime.MinValue) ? "" : secondSweepTime.ToString("yyyy-MM-dd HH:mm:ss");

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
					sessionOutcome
				);

				writer.WriteLine(line);
				writer.Flush();
			}
			catch { }
		}
	}
}
