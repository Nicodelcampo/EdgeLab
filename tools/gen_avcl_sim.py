"""Genera nt8/aVolClusterPOISim.cs a partir de aVolClusterPOI.cs (que NO se modifica: tiene paridad validada).
Agrega un simulador de trades visual (exploración, NO evidencia): al crearse una zona OFF, long en las verdes (soporte)
y short en las rojas (resistencia), al close de la barra de creación. Las AT (azules) no operan."""
import re
import sys

SRC = r"C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\aVolClusterPOI.cs"
DST = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\aVolClusterPOISim.cs"

raw = open(SRC, "rb").read()
crlf = b"\r\n" in raw
s = raw.decode("utf-8-sig").replace("\r\n", "\n")


def rep(a, b, count=1):
    global s
    assert a in s, a[:80]
    s = s.replace(a, b, count)


# 1) sin región generada (NT8 la regenera) ni enums duplicados (ya existen en aVolClusterPOI.cs)
s = s[:s.index("#region NinjaScript generated code")]
rep("public enum AVCLPInvalidationMode { None = 0, FirstTouch = 1, CloseThrough = 2 }\n", "")
rep("public enum AVCLPDashboardCorner { TopRight = 0, TopLeft = 1, BottomRight = 2, BottomLeft = 3 }\n",
    "public enum AVCLPSimSlMode { ZonePercent = 0, FixedTicks = 1 }\npublic enum AVCLPSimTpMode { RMultiple = 0, FixedTicks = 1 }\n")
# 2) clase y nombre
rep("public class aVolClusterPOI : Indicator", "public class aVolClusterPOISim : Indicator")
rep('Name = "aVolClusterPOI";', 'Name = "aVolClusterPOISim";')
rep('Description = "Cluster-mass POI v0.5', 'Description = "[SIM visual, exploracion] Cluster-mass POI v0.5')
# 3) no publicar en el registro compartido (evita duplicar zonas con el indicador original)
s = s.replace("SharedVolClusterZones.", "SimSharedNoop.")
# 4) tags propios
s = s.replace('"AVCLP_', '"AVCLPS_')

# 4b) defaults de ciclo de vida para la copia: invalidación None, MaxAge 500 (configuración usada en la paridad)
rep("InvalidationMode = AVCLPInvalidationMode.CloseThrough;\n\t\t\t\tMaxAgeBars = 0;",
    "InvalidationMode = AVCLPInvalidationMode.None;\n\t\t\t\tMaxAgeBars = 500;")

# 5) campos del simulador
rep("		private List<Zone> zones;\n", '''		private List<Zone> zones;

		// ---- simulador de trades (exploración visual; NO evidencia) ----
		private class SimTrade
		{
			public long ZoneId; public int Dir; public int EntryBar; public double Entry; public double Sl; public double Tp;
			public double Risk; public double SlInit; public bool BeDone; public bool Open; public int ExitBar; public double Exit; public string Reason;
			public double R;
		}
		private List<SimTrade> simTrades;
		private Queue<string> simTags;
		private double simEquityR, simPeakR, simMaxDdR, simSumWinR, simSumLossR;
		private int simWins, simLosses, simBe, simTimeouts, simConsLoss, simMaxConsLoss, simLongN, simShortN;
		private double simLongR, simShortR, simUsd;
''')
# 6) valores por defecto
rep("				AtPriceColor = Brushes.SteelBlue;\n			}", '''				AtPriceColor = Brushes.SteelBlue;

				SimEnabled = true;
				SimSlMode = AVCLPSimSlMode.ZonePercent;
				SimSlZonePercent = 50.0;
				SimSlTicks = 8;
				SimTpMode = AVCLPSimTpMode.RMultiple;
				SimTpR = 30.0;
				SimTpTicks = 80;
				SimUseBreakEven = false;
				SimBeTriggerR = 1.0;
				SimBeOffsetTicks = 0;
				SimMaxBarsInTrade = 0;
				SimExitAtSessionEnd = true;
				SimCommissionTicks = 0.0;
				SimOneTradeAtATime = false;
				SimDrawTrades = true;
				SimMaxDrawnTrades = 300;
				SimRectOpacity = 15;
			}''')
# 7) init
rep("				dashFont = new SimpleFont(\"Consolas\", 12);\n", '''				dashFont = new SimpleFont("Consolas", 12);
				simTrades = new List<SimTrade>();
				simTags = new Queue<string>();
				simEquityR = 0; simPeakR = 0; simMaxDdR = 0; simSumWinR = 0; simSumLossR = 0;
				simWins = 0; simLosses = 0; simBe = 0; simTimeouts = 0; simConsLoss = 0; simMaxConsLoss = 0;
				simLongN = 0; simShortN = 0; simLongR = 0; simShortR = 0; simUsd = 0;
''')
# 8) cierre por fin de sesión al comenzar la sesión nueva
rep("			if (Bars.IsFirstBarOfSession)\n			{\n				CommitSession();",
    "			if (Bars.IsFirstBarOfSession)\n			{\n				if (SimEnabled && SimExitAtSessionEnd && CurrentBar > 0) SimCloseAll(Close[1], CurrentBar - 1, \"SESION\");\n				CommitSession();")
# 9) actualizar trades abiertos con la barra actual (antes de crear zonas nuevas en este bloque)
rep("			ProcessLifecycle(lowTick, highTick, PriceToTick(Close[0]));\n",
    "			ProcessLifecycle(lowTick, highTick, PriceToTick(Close[0]));\n			if (SimEnabled) SimUpdate();\n")
# 10) abrir trade al crear zona OFF
rep("			zones.Add(z);\n			EmitEvent(", "			zones.Add(z);\n			if (SimEnabled && kind != \"AT_PRICE\" && direction != 0) SimOpen(z);\n			EmitEvent(")
# 11) dashboard: anexar estadísticas
rep('			Draw.TextFixed(this, "AVCLPS_DASH", sb.ToString()', '			if (SimEnabled) sb.Append(SimDashboard());\n			Draw.TextFixed(this, "AVCLPS_DASH", sb.ToString()')

SIM_METHODS = '''
		// ------------------------------------------------------------------
		// Simulador de trades (exploración visual)
		// ------------------------------------------------------------------
		private static class SimSharedNoop
		{
			public static void Clear(string a) { }
			public static void PublishZone(string a, object b) { }
			public static void InvalidateZone(string a, long b, int c) { }
		}

		private void SimOpen(Zone z)
		{
			if (SimOneTradeAtATime)
				foreach (SimTrade o in simTrades) if (o.Open) return;
			double lower = (z.LowerTick - 0.5) * TickSize, upper = (z.UpperTick + 0.5) * TickSize;
			int dir = z.Direction;                       // +1 soporte (verde) = long, -1 resistencia (roja) = short
			double entry = Close[0];
			double sl;
			if (SimSlMode == AVCLPSimSlMode.FixedTicks)
				sl = entry - dir * SimSlTicks * TickSize;
			else
			{
				// porcentaje medido desde el borde de la zona más cercano al precio (0 % = borde cercano, 100 % = lejano)
				double near = dir > 0 ? upper : lower, far = dir > 0 ? lower : upper;
				sl = near + (far - near) * SimSlZonePercent / 100.0;
			}
			double risk = (entry - sl) * dir;
			if (risk <= TickSize * 0.5) return;          // SL del lado equivocado o nulo: no se opera
			double tp = SimTpMode == AVCLPSimTpMode.FixedTicks ? entry + dir * SimTpTicks * TickSize : entry + dir * SimTpR * risk;
			simTrades.Add(new SimTrade { ZoneId = z.Id, Dir = dir, EntryBar = CurrentBar, Entry = entry, Sl = sl, Tp = tp,
				Risk = risk, SlInit = sl, Open = true, Reason = "" });
		}

		private void SimUpdate()
		{
			for (int i = simTrades.Count - 1; i >= 0; i--)
			{
				SimTrade t = simTrades[i];
				if (!t.Open || t.EntryBar >= CurrentBar) continue;
				double hi = High[0], lo = Low[0];
				// conservador: si en la misma barra se tocan SL y TP, cuenta el SL
				bool hitSl = t.Dir > 0 ? lo <= t.Sl : hi >= t.Sl;
				bool hitTp = t.Dir > 0 ? hi >= t.Tp : lo <= t.Tp;
				if (hitSl) { SimClose(t, t.Sl, CurrentBar, t.BeDone ? "BE" : "SL"); continue; }
				if (hitTp) { SimClose(t, t.Tp, CurrentBar, "TP"); continue; }
				if (SimMaxBarsInTrade > 0 && CurrentBar - t.EntryBar >= SimMaxBarsInTrade) { SimClose(t, Close[0], CurrentBar, "TIEMPO"); continue; }
				// break even al cierre de la barra (no mueve el stop dentro de la misma barra que lo dispara)
				if (SimUseBreakEven && !t.BeDone)
				{
					double fav = t.Dir > 0 ? hi - t.Entry : t.Entry - lo;
					if (fav >= SimBeTriggerR * t.Risk) { t.Sl = t.Entry + t.Dir * SimBeOffsetTicks * TickSize; t.BeDone = true; }
				}
			}
		}

		private void SimCloseAll(double price, int bar, string reason)
		{
			for (int i = simTrades.Count - 1; i >= 0; i--) if (simTrades[i].Open) SimClose(simTrades[i], price, bar, reason);
		}

		private void SimClose(SimTrade t, double price, int bar, string reason)
		{
			t.Open = false; t.Exit = price; t.ExitBar = bar; t.Reason = reason;
			simTrades.Remove(t);                         // la lista guarda sólo los abiertos
			if (Instrument != null) simUsd += ((price - t.Entry) * t.Dir - SimCommissionTicks * TickSize) * Instrument.MasterInstrument.PointValue;
			t.R = ((price - t.Entry) * t.Dir - SimCommissionTicks * TickSize) / t.Risk;
			simEquityR += t.R;
			if (simEquityR > simPeakR) simPeakR = simEquityR;
			if (simPeakR - simEquityR > simMaxDdR) simMaxDdR = simPeakR - simEquityR;
			if (t.Dir > 0) { simLongN++; simLongR += t.R; } else { simShortN++; simShortR += t.R; }
			if (reason == "BE" && Math.Abs(t.R) < 0.05) simBe++;
			else if (t.R > 0) { simWins++; simSumWinR += t.R; simConsLoss = 0; }
			else { simLosses++; simSumLossR += -t.R; simConsLoss++; if (simConsLoss > simMaxConsLoss) simMaxConsLoss = simConsLoss; }
			if (reason == "TIEMPO" || reason == "SESION") simTimeouts++;
			if (SimDrawTrades) SimDraw(t);
		}

		private void SimDraw(SimTrade t)
		{
			int a = CurrentBar - t.EntryBar, b = Math.Max(0, CurrentBar - t.ExitBar);
			string p = "AVCLPS_T" + t.ZoneId + "_";
			// zona de TP (verde) y de SL (roja) como rectángulos de baja opacidad, desde la entrada hasta la salida
			Draw.Rectangle(this, p + "t", false, a, t.Entry, b, t.Tp, Brushes.Transparent, Brushes.LimeGreen, SimRectOpacity);
			Draw.Rectangle(this, p + "s", false, a, t.Entry, b, t.SlInit, Brushes.Transparent, Brushes.OrangeRed, SimRectOpacity);
			Draw.Line(this, p + "e", false, a, t.Entry, b, t.Entry, Brushes.Gray, DashStyleHelper.Solid, 1);
			Draw.Text(this, p + "r", false, t.R.ToString("+0.0;-0.0", CultureInfo.InvariantCulture) + "R " + t.Reason, b, t.Exit,
				0, t.R > 0 ? Brushes.LimeGreen : Brushes.OrangeRed, dashFont, System.Windows.TextAlignment.Left,
				Brushes.Transparent, Brushes.Transparent, 0);
			foreach (string k in new[] { "e", "s", "t", "r" }) simTags.Enqueue(p + k);
			while (simTags.Count > 4 * Math.Max(10, SimMaxDrawnTrades)) RemoveDrawObject(simTags.Dequeue());
		}

		private string SimDashboard()
		{
			int closed = simWins + simLosses + simBe, open = 0;
			foreach (SimTrade t in simTrades) if (t.Open) open++;
			StringBuilder sb = new StringBuilder(600);
			sb.Append("\\n=== SIMULADOR (exploracion visual, NO evidencia) ===\\n");
			sb.Append("SL: " + (SimSlMode == AVCLPSimSlMode.FixedTicks ? SimSlTicks + " ticks" : SimSlZonePercent.ToString("0", CultureInfo.InvariantCulture) + "% de la zona")
				+ " | TP: " + (SimTpMode == AVCLPSimTpMode.FixedTicks ? SimTpTicks + " ticks" : SimTpR.ToString("0.#", CultureInfo.InvariantCulture) + "R")
				+ " | BE: " + (SimUseBreakEven ? "a " + SimBeTriggerR.ToString("0.##", CultureInfo.InvariantCulture) + "R (+" + SimBeOffsetTicks + "t)" : "off") + "\\n");
			sb.Append("Trades: " + closed + " cerrados, " + open + " abiertos (long " + simLongN + " / short " + simShortN + ")\\n");
			if (closed > 0)
			{
				double wr = 100.0 * simWins / closed;
				double exp = simEquityR / closed;
				double pf = simSumLossR > 0 ? simSumWinR / simSumLossR : double.PositiveInfinity;
				double pointValue = Instrument != null ? Instrument.MasterInstrument.PointValue : 0;
				sb.Append("Ganadores " + simWins + " | Perdedores " + simLosses + " | BE " + simBe + " | por tiempo/sesion " + simTimeouts + "\\n");
				sb.Append("Win rate: " + wr.ToString("0.0", CultureInfo.InvariantCulture) + "% | Expectativa: "
					+ exp.ToString("+0.00;-0.00", CultureInfo.InvariantCulture) + "R/trade\\n");
				sb.Append("Total: " + simEquityR.ToString("+0.0;-0.0", CultureInfo.InvariantCulture) + "R | PF: "
					+ (double.IsInfinity(pf) ? "inf" : pf.ToString("0.00", CultureInfo.InvariantCulture))
					+ " | Max DD: " + simMaxDdR.ToString("0.0", CultureInfo.InvariantCulture) + "R | Racha perd.: " + simMaxConsLoss + "\\n");
				sb.Append("Long: " + simLongR.ToString("+0.0;-0.0", CultureInfo.InvariantCulture) + "R | Short: "
					+ simShortR.ToString("+0.0;-0.0", CultureInfo.InvariantCulture) + "R");
				if (pointValue > 0)
					sb.Append(" | Neto 1 contrato: " + simUsd.ToString("0", CultureInfo.InvariantCulture) + " USD");
				sb.Append("\\n(SL+TP en la misma barra = SL; sin slippage salvo comision en ticks)");
			}
			return sb.ToString();
		}
'''
rep("		#region SharpDX Direct2D Rendering", SIM_METHODS + "\n		#region SharpDX Direct2D Rendering")

PROPS = '''
		[Display(Name = "Activar simulador", Order = 1, GroupName = "10. Simulador (exploracion)")]
		public bool SimEnabled { get; set; }
		[Display(Name = "Modo SL", Order = 2, GroupName = "10. Simulador (exploracion)")]
		public AVCLPSimSlMode SimSlMode { get; set; }
		[Range(0.0, 1000.0)]
		[Display(Name = "SL: % de la zona (0 = borde cercano, 100 = lejano)", Order = 3, GroupName = "10. Simulador (exploracion)")]
		public double SimSlZonePercent { get; set; }
		[Range(1, 100000)]
		[Display(Name = "SL: ticks fijos", Order = 4, GroupName = "10. Simulador (exploracion)")]
		public int SimSlTicks { get; set; }
		[Display(Name = "Modo TP", Order = 5, GroupName = "10. Simulador (exploracion)")]
		public AVCLPSimTpMode SimTpMode { get; set; }
		[Range(0.1, 1000.0)]
		[Display(Name = "TP: multiplo de R", Order = 6, GroupName = "10. Simulador (exploracion)")]
		public double SimTpR { get; set; }
		[Range(1, 100000)]
		[Display(Name = "TP: ticks fijos", Order = 7, GroupName = "10. Simulador (exploracion)")]
		public int SimTpTicks { get; set; }
		[Display(Name = "Break even", Order = 8, GroupName = "10. Simulador (exploracion)")]
		public bool SimUseBreakEven { get; set; }
		[Range(0.1, 1000.0)]
		[Display(Name = "BE: activar a (R)", Order = 9, GroupName = "10. Simulador (exploracion)")]
		public double SimBeTriggerR { get; set; }
		[Range(-1000, 1000)]
		[Display(Name = "BE: offset (ticks a favor)", Order = 10, GroupName = "10. Simulador (exploracion)")]
		public int SimBeOffsetTicks { get; set; }
		[Range(0, 100000)]
		[Display(Name = "Salida por tiempo (barras, 0 = off)", Order = 11, GroupName = "10. Simulador (exploracion)")]
		public int SimMaxBarsInTrade { get; set; }
		[Display(Name = "Cerrar al fin de sesion", Order = 12, GroupName = "10. Simulador (exploracion)")]
		public bool SimExitAtSessionEnd { get; set; }
		[Range(0.0, 1000.0)]
		[Display(Name = "Comision + slippage (ticks por trade)", Order = 13, GroupName = "10. Simulador (exploracion)")]
		public double SimCommissionTicks { get; set; }
		[Display(Name = "Un trade a la vez", Order = 14, GroupName = "10. Simulador (exploracion)")]
		public bool SimOneTradeAtATime { get; set; }
		[Display(Name = "Dibujar trades", Order = 15, GroupName = "10. Simulador (exploracion)")]
		public bool SimDrawTrades { get; set; }
		[Range(10, 100000)]
		[Display(Name = "Max trades dibujados", Order = 16, GroupName = "10. Simulador (exploracion)")]
		public int SimMaxDrawnTrades { get; set; }
		[Range(1, 100)]
		[Display(Name = "Opacidad rectangulos TP/SL (%)", Order = 17, GroupName = "10. Simulador (exploracion)")]
		public int SimRectOpacity { get; set; }
'''
# insertar las propiedades antes del #endregion de Properties (el último #endregion antes del cierre de clase)
i = s.rindex("		#endregion")
s = s[:i] + PROPS + "\n" + s[i:]
out = s.replace("\n", "\r\n") if crlf else s
open(DST, "w", encoding="utf-8").write(out)
print("ok ->", DST)
