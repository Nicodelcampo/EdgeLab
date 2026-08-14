#region Using declarations
using System;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using NinjaTrader.Data;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class ExportM1Bars : Indicator
	{
		private StreamWriter writer;
		private string exportPath = @"C:\EdgeLab\6E_1min_2026.csv";

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Export exact 1-minute bars seen by chart to CSV";
				Name = "ExportM1Bars";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
			}
			else if (State == State.DataLoaded)
			{
				try
				{
					writer = new StreamWriter(exportPath, false);
					writer.WriteLine("Time,Open,High,Low,Close,Volume");
				}
				catch { }
			}
			else if (State == State.Terminated)
			{
				if (writer != null)
				{
					writer.Flush();
					writer.Close();
					writer = null;
				}
			}
		}

		protected override void OnBarUpdate()
		{
			if (writer == null) return;
			string t = Time[0].ToString("yyyy-MM-dd HH:mm:ss");
			writer.WriteLine(string.Format("{0},{1:F5},{2:F5},{3:F5},{4:F5},{5}", t, Open[0], High[0], Low[0], Close[0], (long)Volume[0]));
		}
	}
}
