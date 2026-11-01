// EdgeLab Live Tick Logger (2026-11-01): graba EN VIVO cada trade con el bid/ask vigente, para que la cartera viva del Debian siga
// las estrategias en papel con datos nuevos (docs/CARTERA_VIVA.md, docs/infra/LOGGER_NT8_DIARIO.md). Es un INDICADOR que no dibuja:
// se agrega a un gráfico de cada instrumento (NQ, ES, YM, GC, contrato del frente) y queda corriendo con la conexión de datos abierta.
//
// Salida: <Root>\<CONTRATO>\<yyyyMMdd>.Last.utc.txt (día UTC), el MISMO formato que EdgeLabTickHistory y EdgeLabTickLogger:
//      yyyyMMdd HHmmss fffffff;last;bid;ask;volume   (hora UTC; bid/ask = último quote conocido, 0 si todavía no hubo)
//   + <Root>\<CONTRATO>\manifest_live.jsonl: una línea por archivo cerrado (ticks, primer/último tick UTC, zona de NT8).
// El archivo del día se escribe con AutoFlush y FileShare.Read: tools/nt8_sellado_diario.py lo puede leer mientras sigue abierto.
// Si NT8 se reinicia en el mismo día, el archivo se ABRE EN MODO AGREGAR: nunca se pisa lo ya grabado.
// Sólo tiempo real (State.Realtime): los ticks históricos que NT8 carga al abrir el gráfico NO se graban (esos se bajan con
// EdgeLabTickHistory). Un hueco de conexión queda como hueco; el conversor lo detecta por la cobertura de la sesión.
#region Using declarations
using System;
using System.Globalization;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class EdgeLabLiveTickLogger : Indicator
	{
		private StreamWriter w; private string dia = null, archivo = null, carpeta = null;
		private double bid = 0, ask = 0; private long n = 0; private DateTime primero, ultimo;
		private readonly object candado = new object();

		[NinjaScriptProperty]
		public string Root { get; set; }

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "EdgeLab Live Tick Logger"; Description = "Graba trades en vivo con bid/ask vigente (no dibuja, no opera).";
				Calculate = Calculate.OnEachTick; IsOverlay = true; DisplayInDataBox = false; PaintPriceMarkers = false;
				Root = @"C:\EdgeLab\tick_live";
			}
			else if (State == State.DataLoaded)
			{
				carpeta = Path.Combine(Root, Instrument.FullName.Replace(" ", "_")); Directory.CreateDirectory(carpeta);
			}
			else if (State == State.Terminated) lock (candado) Cerrar();
		}

		protected override void OnBarUpdate() { }

		protected override void OnMarketData(MarketDataEventArgs e)
		{
			if (State != State.Realtime) return;
			lock (candado)
			{
				if (e.MarketDataType == MarketDataType.Bid) { bid = e.Price; return; }
				if (e.MarketDataType == MarketDataType.Ask) { ask = e.Price; return; }
				if (e.MarketDataType != MarketDataType.Last) return;
				DateTime utc = TimeZoneInfo.ConvertTimeToUtc(DateTime.SpecifyKind(e.Time, DateTimeKind.Unspecified), Core.Globals.GeneralOptions.TimeZoneInfo);
				string d = utc.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
				if (d != dia) { Cerrar(); Abrir(d, utc); }
				w.WriteLine(utc.ToString("yyyyMMdd HHmmss fffffff", CultureInfo.InvariantCulture) + ";" + e.Price.ToString("R", CultureInfo.InvariantCulture) + ";"
					+ bid.ToString("R", CultureInfo.InvariantCulture) + ";" + ask.ToString("R", CultureInfo.InvariantCulture) + ";"
					+ e.Volume.ToString(CultureInfo.InvariantCulture));
				n++; ultimo = utc;
			}
		}

		private void Abrir(string d, DateTime utc)
		{
			dia = d; archivo = Path.Combine(carpeta, d + ".Last.utc.txt");
			var fs = new FileStream(archivo, FileMode.Append, FileAccess.Write, FileShare.Read);
			w = new StreamWriter(fs, new UTF8Encoding(false)); w.AutoFlush = true; n = 0; primero = utc; ultimo = utc;
		}

		private void Cerrar()
		{
			if (w == null) return;
			w.Flush(); w.Close(); w = null;
			File.AppendAllText(Path.Combine(carpeta, "manifest_live.jsonl"),
				"{\"dia\":\"" + dia + "\",\"ticks\":" + n + ",\"primero_utc\":\"" + primero.ToString("o") + "\",\"ultimo_utc\":\"" + ultimo.ToString("o")
				+ "\",\"tz_nt8\":\"" + Core.Globals.GeneralOptions.TimeZoneInfo.Id + "\",\"fuente\":\"EdgeLabLiveTickLogger\"}\n");
		}
	}
}
