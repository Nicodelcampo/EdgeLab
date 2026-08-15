#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
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
		private string exportPath = "";

		[NinjaScriptProperty]
		[Display(Name = "CSV Export Path", Description = "Ruta del CSV. Si se deja vacio, se guarda automaticamente como C:\\EdgeLab\\<Instrumento>_1min.csv", Order = 1, GroupName = "Configuracion")]
		public string ExportPath
		{
			get { return exportPath; }
			set { exportPath = value; }
		}

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Exporta automaticamente las barras exactas de 1 minuto del grafico a CSV";
				Name = "ExportM1Bars";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				ExportPath = "";
			}
			else if (State == State.DataLoaded)
			{
				try
				{
					string targetPath = ExportPath;
					if (string.IsNullOrWhiteSpace(targetPath))
					{
						string inst = (Instrument != null) ? Instrument.MasterInstrument.Name : "Data";
						targetPath = string.Format(@"C:\EdgeLab\{0}_1min.csv", inst);
					}

					string dir = Path.GetDirectoryName(targetPath);
					if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
						Directory.CreateDirectory(dir);

					writer = new StreamWriter(targetPath, false);
					// Primera declaracion de version de este .cs (2026-08-15). No tenia
					// ninguna: la regla permanente pide que cada correccion viaje con su
					// version, y sin meta en el CSV un export no se puede trazar al codigo
					// que lo produjo. Arranca en 1.0 porque no hay version previa que
					// continuar. Al tocar este archivo, subirla aca Y en el meta.
					writer.WriteLine(string.Format(
						"# meta indicator=ExportM1Bars,version=1.0,instrument={0},bar_spec=time:1,ts_note=chart_local",
						Instrument.MasterInstrument.Name));
					writer.WriteLine("Time,Open,High,Low,Close,Volume");
				}
				catch { }
			}
			else if (State == State.Terminated)
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
		}

		protected override void OnBarUpdate()
		{
			if (writer == null) return;
			string t = Time[0].ToString("yyyy-MM-dd HH:mm:ss");
			writer.WriteLine(string.Format("{0},{1:F5},{2:F5},{3:F5},{4:F5},{5}", t, Open[0], High[0], Low[0], Close[0], (long)Volume[0]));
		}
	}
}
