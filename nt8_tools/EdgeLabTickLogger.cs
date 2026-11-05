// EdgeLab Tick Logger (2026-10-26): exporta la historia de TICKS que el Strategy Analyzer carga para un backtest, para cuando el
// servidor de datos no la entrega por BarsRequest (EdgeLabTickHistory dio "no hay más"). Es una ESTRATEGIA que no opera: sólo escribe.
//
// Uso: Strategy Analyzer -> esta estrategia, instrumento (NQ 03-24, ES 06-24, ...), tipo de datos "Tick" 1, rango de fechas,
//      "Order fill resolution: Standard" (no importa: no hay órdenes). Una corrida por contrato/rango.
// Salida: <Root>\<CONTRATO>\<yyyyMMdd>.Last.utc.txt con el MISMO formato que EdgeLabTickHistory (lo lee el constructor de la release):
//      yyyyMMdd HHmmss fffffff;last;bid;ask;volume   (hora UTC declarada; bid/ask = último quote conocido as-of, 0 si todavía no hubo)
//      más <Root>\<CONTRATO>\manifest_logger.jsonl con una línea por día (ticks, primer/último tick UTC).
// Reglas: sólo días ANTERIORES a la frontera del holdout (sesión CME del 2026-10-01, apertura 2026-09-30 22:00 UTC; fail-closed: un
//      tick en o después de esa hora corta la corrida). Escritura atómica por día (.partial -> rename al cambiar de día y al terminar).
// Nota: bid/ask históricos sólo existen si el proveedor los tiene; si las series Bid/Ask llegan vacías, bid=ask=0 y el manifiesto lo dice.
#region Using declarations
using System;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
	public class EdgeLabTickLogger : Strategy
	{
		private static readonly DateTime HoldoutUtc = new DateTime(2026, 9, 30, 22, 0, 0, DateTimeKind.Utc);
		private StreamWriter w; private string dia = null, partial = null, final = null, carpeta = null;
		private double bid = 0, ask = 0; private long n = 0, nQuote = 0; private DateTime primero, ultimo;

		[NinjaScriptProperty]
		public string Root { get; set; }

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "EdgeLab Tick Logger"; Description = "Exporta ticks del backtest (no opera).";
				Calculate = Calculate.OnEachTick; IsInstantiatedOnEachOptimizationIteration = false; Root = @"C:\EdgeLab\tick_logger";
			}
			else if (State == State.Configure)
			{
				AddDataSeries(Instrument.FullName, new BarsPeriod { BarsPeriodType = BarsPeriodType.Tick, Value = 1, MarketDataType = MarketDataType.Bid });
				AddDataSeries(Instrument.FullName, new BarsPeriod { BarsPeriodType = BarsPeriodType.Tick, Value = 1, MarketDataType = MarketDataType.Ask });
			}
			else if (State == State.DataLoaded)
			{
				carpeta = Path.Combine(Root, Instrument.FullName.Replace(" ", "_")); Directory.CreateDirectory(carpeta);
			}
			else if (State == State.Terminated) Cerrar();
		}

		protected override void OnBarUpdate()
		{
			if (BarsInProgress == 1) { bid = Closes[1][0]; nQuote++; return; }
			if (BarsInProgress == 2) { ask = Closes[2][0]; nQuote++; return; }
			if (BarsPeriod.BarsPeriodType != BarsPeriodType.Tick || BarsPeriod.Value != 1)
				throw new Exception("EdgeLabTickLogger: la serie primaria tiene que ser Tick 1");
			DateTime utc = TimeZoneInfo.ConvertTimeToUtc(Time[0], Core.Globals.GeneralOptions.TimeZoneInfo);
			if (utc >= HoldoutUtc) { Cerrar(); throw new Exception("EdgeLabTickLogger: tick en el holdout (" + utc.ToString("o") + "): corrida cortada"); }
			string d = utc.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
			if (d != dia) { Cerrar(); Abrir(d, utc); }
			w.WriteLine(utc.ToString("yyyyMMdd HHmmss fffffff", CultureInfo.InvariantCulture) + ";" + Close[0].ToString("R", CultureInfo.InvariantCulture) + ";"
				+ bid.ToString("R", CultureInfo.InvariantCulture) + ";" + ask.ToString("R", CultureInfo.InvariantCulture) + ";" + ((long)Volume[0]).ToString(CultureInfo.InvariantCulture));
			n++; ultimo = utc;
		}

		private void Abrir(string d, DateTime utc)
		{
			dia = d; final = Path.Combine(carpeta, d + ".Last.utc.txt"); partial = final + ".partial";
			w = new StreamWriter(partial, false); n = 0; nQuote = 0; primero = utc; ultimo = utc;
		}

		private void Cerrar()
		{
			if (w == null) return;
			w.Flush(); w.Close(); w = null;
			if (File.Exists(final)) File.Delete(final);
			File.Move(partial, final);
			File.AppendAllText(Path.Combine(carpeta, "manifest_logger.jsonl"),
				"{\"dia\":\"" + dia + "\",\"ticks\":" + n + ",\"quotes\":" + nQuote + ",\"primero_utc\":\"" + primero.ToString("o") + "\",\"ultimo_utc\":\""
				+ ultimo.ToString("o") + "\",\"tz_nt8\":\"" + Core.Globals.GeneralOptions.TimeZoneInfo.Id + "\",\"fuente\":\"StrategyAnalyzer\"}\n");
		}
	}
}
