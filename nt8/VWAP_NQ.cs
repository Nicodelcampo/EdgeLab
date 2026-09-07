// # meta indicator=VWAP_NQ,version=1.0.0
//
// VWAP_NQ — Institutional Anchored VWAP con Bandas de Desviación Estándar para Nasdaq (NQ / MNQ).
//
// Diseñado con Rigurosidad Cuantitativa EdgeLab:
// - Puntos de Anclaje Óptimos para Nasdaq:
//   * RTH Wall Street Open (08:30 CT / 09:30 ET / 10:30 Argentina): El anclaje REINA para NQ. Más del 70% del volumen y los algoritmos institucionales ejecutan contra esta campana.
//   * Session Globex (17:00 CT / 19:00 Argentina): Sesión completa overnight + RTH (23h).
//   * European Open (02:00 CT / 04:00 Argentina): Flujo de apertura DAX / Londres.
//   * Chart Session: Reinicio automático según la plantilla de sesión del gráfico.
// - Bandas de Desviación Estándar (Gaussian Value Area):
//   * Banda 1 (±1.0σ): Value Area institucional (68.2% del volumen negociado).
//   * Banda 2 (±2.0σ): Frontera de tendencia o sobrecompra/sobreventa extrema (95.4% del volumen).
//   * Banda 3 (±3.0σ): Agotamiento o capitulación intradía (99.7% del volumen).
// - HUD Contextual en Tiempo Real con métricas en pts, ticks y estado de equilibrio/sobreextensión.
//
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript
{
	public enum VWAPAnchorNQ
	{
		RTH_WallStreet_0830_CT, // 08:30 CT / 09:30 ET / 10:30 Argentina — Campana de Wall Street (Recomendado NQ)
		Session_CME_1700_CT,    // 17:00 CT / 19:00 Argentina — Apertura de sesión electrónica Globex (23h)
		European_Open_0200_CT,  // 02:00 CT / 04:00 Argentina — Apertura europea (DAX / FTSE)
		Chart_Session,          // Reinicio automático según la plantilla de sesión configurada en el gráfico
		Custom_Time             // Hora y minuto personalizados
	}

	public enum VWAPTimezoneNQ
	{
		CME_Central_Time,       // Horarios oficiales de Chicago (CME)
		Local_Chart_Time        // Hora local del ordenador/gráfico
	}
}

namespace NinjaTrader.NinjaScript.Indicators
{
	public class VWAP_NQ : Indicator
	{
		private const string IND_VERSION = "1.0.0";

		// Acumuladores VWAP
		private double _cumVol;
		private double _cumPv;
		private double _cumP2v;
		private DateTime _lastAnchorDt;
		private TimeZoneInfo _cmeTz;

		#region Properties
		[NinjaScriptProperty]
		[Display(Name = "Punto de Anclaje", GroupName = "1. Anclaje Institucional", Order = 1)]
		public VWAPAnchorNQ AnchorMode { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Zona Horaria de Referencia", GroupName = "1. Anclaje Institucional", Order = 2)]
		public VWAPTimezoneNQ TimezoneMode { get; set; }

		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name = "Hora Personalizada (0-23)", GroupName = "1. Anclaje Institucional", Order = 3)]
		public int CustomAnchorHour { get; set; }

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name = "Minuto Personalizado (0-59)", GroupName = "1. Anclaje Institucional", Order = 4)]
		public int CustomAnchorMinute { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 10.0)]
		[Display(Name = "Multiplicador Banda 1 (σ)", GroupName = "2. Bandas de Desviación", Order = 1)]
		public double Band1Multiplier { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 10.0)]
		[Display(Name = "Multiplicador Banda 2 (σ)", GroupName = "2. Bandas de Desviación", Order = 2)]
		public double Band2Multiplier { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 10.0)]
		[Display(Name = "Multiplicador Banda 3 (σ)", GroupName = "2. Bandas de Desviación", Order = 3)]
		public double Band3Multiplier { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Mostrar Banda 1 (±1σ)", GroupName = "2. Bandas de Desviación", Order = 4)]
		public bool ShowBand1 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Mostrar Banda 2 (±2σ)", GroupName = "2. Bandas de Desviación", Order = 5)]
		public bool ShowBand2 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Mostrar Banda 3 (±3σ)", GroupName = "2. Bandas de Desviación", Order = 6)]
		public bool ShowBand3 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Mostrar HUD de Estado", GroupName = "3. Panel Informativo", Order = 1)]
		public bool ShowHud { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Posición del HUD", GroupName = "3. Panel Informativo", Order = 2)]
		public TextPosition HudPosition { get; set; }
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "VWAP_NQ — Institutional Anchored VWAP con Bandas de Desviación Estándar para Nasdaq (NQ / MNQ)";
				Name						= "VWAP_NQ";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= true;
				PaintPriceMarkers			= true;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				// Anclaje recomendado para Nasdaq: 08:30 CT (09:30 ET Wall Street Open)
				AnchorMode					= VWAPAnchorNQ.RTH_WallStreet_0830_CT;
				TimezoneMode				= VWAPTimezoneNQ.CME_Central_Time;
				CustomAnchorHour			= 8;
				CustomAnchorMinute			= 30;

				// Bandas canónicas de volatilidad gaussiana
				Band1Multiplier				= 1.0;
				Band2Multiplier				= 2.0;
				Band3Multiplier				= 3.0;
				ShowBand1					= true;
				ShowBand2					= true;
				ShowBand3					= true;

				ShowHud						= true;
				HudPosition					= TextPosition.BottomLeft;

				// Configuración estética de Plots para NinjaTrader 8
				AddPlot(new Stroke(Brushes.Cyan, 2), PlotStyle.Line, "VWAP");
				AddPlot(new Stroke(Brushes.DodgerBlue, DashStyleHelper.Dash, 1), PlotStyle.Line, "Upper Band 1 (+1σ)");
				AddPlot(new Stroke(Brushes.DodgerBlue, DashStyleHelper.Dash, 1), PlotStyle.Line, "Lower Band 1 (-1σ)");
				AddPlot(new Stroke(Brushes.Magenta, DashStyleHelper.Solid, 1), PlotStyle.Line, "Upper Band 2 (+2σ)");
				AddPlot(new Stroke(Brushes.Magenta, DashStyleHelper.Solid, 1), PlotStyle.Line, "Lower Band 2 (-2σ)");
				AddPlot(new Stroke(Brushes.Red, DashStyleHelper.Dot, 1), PlotStyle.Line, "Upper Band 3 (+3σ)");
				AddPlot(new Stroke(Brushes.Red, DashStyleHelper.Dot, 1), PlotStyle.Line, "Lower Band 3 (-3σ)");
			}
			else if (State == State.DataLoaded)
			{
				try
				{
					_cmeTz = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
				}
				catch
				{
					_cmeTz = null;
				}

				_cumVol = 0.0;
				_cumPv = 0.0;
				_cumP2v = 0.0;
				_lastAnchorDt = DateTime.MinValue;
			}
		}

		private DateTime GetAnchorDt(DateTime t, TimeSpan anchor)
		{
			if (t.TimeOfDay >= anchor)
				return t.Date.Add(anchor);
			else
				return t.Date.AddDays(-1).Add(anchor);
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 0) return;

			DateTime barDt = Time[0];
			DateTime refDt = barDt;

			if (TimezoneMode == VWAPTimezoneNQ.CME_Central_Time && _cmeTz != null)
			{
				if (barDt.Kind == DateTimeKind.Utc)
					refDt = TimeZoneInfo.ConvertTimeFromUtc(barDt, _cmeTz);
				else
				{
					DateTime localDt = DateTime.SpecifyKind(barDt, DateTimeKind.Local);
					refDt = TimeZoneInfo.ConvertTime(localDt, _cmeTz);
				}
			}

			bool shouldReset = false;

			if (AnchorMode == VWAPAnchorNQ.Chart_Session)
			{
				shouldReset = Bars.IsFirstBarOfSession;
			}
			else
			{
				TimeSpan targetAnchor;
				switch (AnchorMode)
				{
					case VWAPAnchorNQ.RTH_WallStreet_0830_CT:
						targetAnchor = new TimeSpan(8, 30, 0);
						break;
					case VWAPAnchorNQ.Session_CME_1700_CT:
						targetAnchor = new TimeSpan(17, 0, 0);
						break;
					case VWAPAnchorNQ.European_Open_0200_CT:
						targetAnchor = new TimeSpan(2, 0, 0);
						break;
					case VWAPAnchorNQ.Custom_Time:
					default:
						targetAnchor = new TimeSpan(CustomAnchorHour, CustomAnchorMinute, 0);
						break;
				}

				DateTime anchorDt = GetAnchorDt(refDt, targetAnchor);
				if (anchorDt != _lastAnchorDt)
				{
					_lastAnchorDt = anchorDt;
					shouldReset = true;
				}
			}

			if (CurrentBar == 0)
				shouldReset = true;

			// Cálculo estándar institucional con Precio Típico (H+L+C)/3
			double price = (Highs[0][0] + Lows[0][0] + Closes[0][0]) / 3.0;
			double vol = Volumes[0][0];
			if (vol <= 0.0) vol = 1.0;

			if (shouldReset)
			{
				_cumVol = vol;
				_cumPv = price * vol;
				_cumP2v = (price * price) * vol;
			}
			else
			{
				_cumVol += vol;
				_cumPv += price * vol;
				_cumP2v += (price * price) * vol;
			}

			double vwap = _cumPv / _cumVol;
			double variance = Math.Max(0.0, (_cumP2v / _cumVol) - (vwap * vwap));
			double stdDev = Math.Sqrt(variance);

			double upper1 = vwap + (Band1Multiplier * stdDev);
			double lower1 = vwap - (Band1Multiplier * stdDev);
			double upper2 = vwap + (Band2Multiplier * stdDev);
			double lower2 = vwap - (Band2Multiplier * stdDev);
			double upper3 = vwap + (Band3Multiplier * stdDev);
			double lower3 = vwap - (Band3Multiplier * stdDev);

			// Asignar Plots
			Values[0][0] = vwap;

			if (ShowBand1)
			{
				Values[1][0] = upper1;
				Values[2][0] = lower1;
			}
			else
			{
				Values[1].Reset();
				Values[2].Reset();
			}

			if (ShowBand2)
			{
				Values[3][0] = upper2;
				Values[4][0] = lower2;
			}
			else
			{
				Values[3].Reset();
				Values[4].Reset();
			}

			if (ShowBand3)
			{
				Values[5][0] = upper3;
				Values[6][0] = lower3;
			}
			else
			{
				Values[5].Reset();
				Values[6].Reset();
			}

			// Renderizar HUD informativo
			if (ShowHud && CurrentBar >= 1)
			{
				double curPrice = Closes[0][0];
				double distPts = curPrice - vwap;
				double distTicks = distPts / TickSize;
				double numSigmas = stdDev > 0.0001 ? (distPts / stdDev) : 0.0;

				string zoneState;
				if (Math.Abs(numSigmas) <= Band1Multiplier)
					zoneState = "VALUE AREA (Equilibrio / Balance)";
				else if (numSigmas > Band2Multiplier)
					zoneState = "SOBRECOMPRA (+2σ Ruptura Tendencial o Agotamiento)";
				else if (numSigmas < -Band2Multiplier)
					zoneState = "SOBREVENTA (-2σ Ruptura Tendencial o Agotamiento)";
				else if (numSigmas > 0)
					zoneState = "EXTENSIÓN ALCISTA (+1σ)";
				else
					zoneState = "EXTENSIÓN BAJISTA (-1σ)";

				string anchorDesc = AnchorMode == VWAPAnchorNQ.RTH_WallStreet_0830_CT ? "Wall Street RTH (08:30 CT / 10:30 ARG)" :
									(AnchorMode == VWAPAnchorNQ.Session_CME_1700_CT ? "CME Globex (17:00 CT / 19:00 ARG)" :
									(AnchorMode == VWAPAnchorNQ.European_Open_0200_CT ? "Europa Open (02:00 CT / 04:00 ARG)" :
									(AnchorMode == VWAPAnchorNQ.Chart_Session ? "Sesión Chart NT8" : string.Format("Custom {0:D2}:{1:D2}", CustomAnchorHour, CustomAnchorMinute))));

				string hudText = string.Format(
					"=== VWAP INSTITUCIONAL (NQ) ===\n" +
					"Anclaje      : {0}\n" +
					"VWAP         : {1:F2}\n" +
					"Desv. Est (σ): {2:F2} pts (${3:N0})\n" +
					"Distancia    : {4:+0.00;-0.00} pts ({5:+0;-0} tk) [{6:+0.0;-0.0}σ]\n" +
					"Estado       : {7}\n" +
					"-------------------------------\n" +
					"Banda +1σ    : {8:F2} | -1σ: {9:F2}\n" +
					"Banda +2σ    : {10:F2} | -2σ: {11:F2}",
					anchorDesc,
					vwap,
					stdDev,
					stdDev * 20.0,
					distPts,
					distTicks,
					numSigmas,
					zoneState,
					upper1,
					lower1,
					upper2,
					lower2
				);

				Draw.TextFixed(this, "VWAP_NQ_HUD", hudText, HudPosition,
					Brushes.White, new NinjaTrader.Gui.Tools.SimpleFont("Consolas", 10),
					Brushes.Cyan, Brushes.Black, 80);
			}
		}
	}
}
