#region Using declarations
using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.Tools;
#endregion

// CleanImpulses v1.0 -- los impulsos mas largos SIN zonas creadas adentro.
// Espejo de edgelab/bridge/indicators/cleanimpulse.py
//
// QUE MARCA, en tres pasos y nada mas:
//   1. Parte la serie en TRAMOS: de un pivote a su pivote OPUESTO. Alcista va de
//      un minimo a un maximo, bajista al reves. Largo = |ticks|.
//   2. Se queda con el TopPct % mas largo (3 % por defecto).
//   3. De esos, marca solo los que NO tienen NINGUNA zona CREADA adentro. Una sola
//      zona creada durante el impulso lo descalifica, EN CUALQUIER NIVEL DE
//      PRECIO: la regla es temporal, no espacial.
//
// DE DONDE SALEN LAS ZONAS
//   De HFTZonesNQPureV4, que ya expone PublicZones. Este indicador lo BUSCA EN EL
//   CHART en vez de instanciarlo: instanciarlo obligaria a repetir sus ~37
//   parametros aca, y cualquier cambio en ese indicador romperia este en silencio.
//   Hay que tener los dos puestos en el chart. Si falta, se avisa en pantalla en
//   vez de dibujar cero y parecer que no hay impulsos limpios.
//
// EL PERCENTIL ES CAUSAL
//   El corte se calcula sobre los ultimos WindowLegs tramos YA CERRADOS, no sobre
//   el chart entero. Con el percentil global, un tramo de hoy quedaria clasificado
//   con informacion de manana, y eso invalida cualquier medicion posterior sin
//   que se note.
//
// QUE SIGNIFICA "CONTENER" UNA ZONA -- y las dos correcciones que costo
//   La primera version terminaba el tramo en el pivote EXACTO. La zona que el
//   impulso genera se registra al cerrarse el movimiento, una o dos barras DESPUES
//   del pivote, asi que caia fuera de la ventana y el impulso quedaba marcado como
//   limpio teniendo zonas propias adentro.
//   La regla es TEMPORAL: cualquier zona creada durante el impulso lo descalifica,
//   en cualquier nivel. RequirePriceOverlap existe para contrastar contra la
//   variante espacial, y viene apagado.
//   La gracia por defecto es PivotRight, que es EXACTAMENTE el retardo con el que
//   se confirma el pivote: no introduce mirada al futuro, porque cuando el tramo
//   queda cerrado esa zona ya se conocia.
//
// Este indicador NO dice si un impulso limpio es bueno. Enumera la poblacion.

namespace NinjaTrader.NinjaScript.Indicators
{
	public class CleanImpulses : Indicator
	{
		private class Swing { public int Bar; public bool IsHigh; public long Tick; }
		private class Leg
		{
			public int StartBar, EndBar;
			public long StartTick, EndTick;
			public int Direction;
			public long LengthTicks;
			public long CutTicks;
			public bool IsLong, IsClean;
			public int ZonesInside;
		}

		private List<long> _hi, _lo;
		private List<Swing> _swings;
		private List<Leg> _legs;
		private List<long> _largos;            // historial de largos, para el corte
		private object _zonesSrc;              // instancia de HFTZonesNQPureV4
		private bool _buscado;
		private int _sessionIndex = -1;
		private StreamWriter _log;
		private bool _logFailed;
		private SharpDX.Direct2D1.Brush _dxUp, _dxDown;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "CleanImpulses";
				Description = "Impulsos del top % mas largo sin zonas creadas adentro";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				PivotLeft = 3;
				PivotRight = 3;
				TopPct = 3.0;
				WindowLegs = 200;
				MinLegTicks = 0;
				GraceBars = -1;              // -1 = usar PivotRight
				RequirePriceOverlap = false;   // NINGUNA zona creada dentro, en cualquier nivel

				UpColor = Brushes.LimeGreen;
				DownColor = Brushes.OrangeRed;
				LineWidthPixels = 3f;
				ShowLabel = true;
				EventLogPath = "";
			}
			else if (State == State.DataLoaded)
			{
				_hi = new List<long>(); _lo = new List<long>();
				_swings = new List<Swing>(); _legs = new List<Leg>();
				_largos = new List<long>();
				_buscado = false; _zonesSrc = null;
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (_log != null) { try { _log.Flush(); _log.Close(); } catch { } _log = null; }
				if (_dxUp != null) { _dxUp.Dispose(); _dxUp = null; }
				if (_dxDown != null) { _dxDown.Dispose(); _dxDown = null; }
			}
		}

		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				string dir = Path.GetDirectoryName(EventLogPath);
				if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
				_log = new StreamWriter(EventLogPath, false, new UTF8Encoding(false));
				_log.AutoFlush = true;
				_log.WriteLine("# meta,indicator=CleanImpulses,version=1.0"
					+ ",instrument=" + Instrument.FullName
					+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
					+ ",pivot_left=" + PivotLeft + ",pivot_right=" + PivotRight
					+ ",top_pct=" + TopPct.ToString(CultureInfo.InvariantCulture)
					+ ",window_legs=" + WindowLegs + ",min_leg_ticks=" + MinLegTicks
					+ ",zone_source=HFTZonesNQPureV4.PublicZones"
					+ ",grace_bars=" + GraceBars
					+ ",require_price_overlap=" + RequirePriceOverlap
					+ ",percentile=causal,write_mode=overwrite");
				_log.WriteLine("leg_seq,start_bar,end_bar,bar_close_time_utc,session_index,"
					+ "direction,start_tick,end_tick,length_ticks,cut_ticks,bars,"
					+ "zones_inside,is_long,is_clean");
			}
			catch { _log = null; _logFailed = true; }
		}

		private long PriceToTick(double p)
		{
			return (long)Math.Round(p / TickSize, MidpointRounding.AwayFromZero);
		}

		// Busca HFTZonesNQPureV4 entre los indicadores del chart y lo cachea.
		// Por reflexion: asi este archivo compila aunque ese indicador no exista.
		private void BuscarFuente()
		{
			_buscado = true;
			try
			{
				if (ChartControl == null || ChartControl.Indicators == null) return;
				foreach (object ind in ChartControl.Indicators)
				{
					if (ind == null) continue;
					if (ind.GetType().Name == "HFTZonesNQPureV4") { _zonesSrc = ind; return; }
				}
			}
			catch { }
		}

		private IEnumerable ZonasFuente()
		{
			if (!_buscado) BuscarFuente();
			if (_zonesSrc == null) return null;
			try
			{
				PropertyInfo pi = _zonesSrc.GetType().GetProperty("PublicZones");
				return pi == null ? null : pi.GetValue(_zonesSrc, null) as IEnumerable;
			}
			catch { return null; }
		}

		// zonas CREADAS dentro del rango de barras del tramo. Creadas, no presentes:
		// una zona previa que sigue viva no cuenta -- lo que interesa es si el
		// impulso GENERO zonas mientras corria.
		private int ZonasAdentro(int startBar, int endBar, long loLeg, long hiLeg)
		{
			IEnumerable zs = ZonasFuente();
			if (zs == null) return -1;              // -1 = fuente ausente, no "cero"
			int gracia = GraceBars >= 0 ? GraceBars : PivotRight;
			int b1 = endBar + gracia;
			int n = 0;
			foreach (object z in zs)
			{
				if (z == null) continue;
				Type t = z.GetType();
				FieldInfo fSb = t.GetField("StartBar");
				if (fSb == null) continue;
				int sb = (int)fSb.GetValue(z);
				if (sb < startBar || sb > b1) continue;

				if (RequirePriceOverlap)
				{
					FieldInfo fU = t.GetField("Upper");
					FieldInfo fL = t.GetField("Lower");
					if (fU != null && fL != null)
					{
						long zHi = PriceToTick((double)fU.GetValue(z));
						long zLo = PriceToTick((double)fL.GetValue(z));
						if (zLo > zHi) { long tmp = zLo; zLo = zHi; zHi = tmp; }
						// la zona tiene que caer DENTRO del recorrido del impulso
						if (zHi < loLeg || zLo > hiLeg) continue;
					}
				}
				n++;
			}
			return n;
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 0) return;
			if (Bars.IsFirstBarOfSession) _sessionIndex++;

			_hi.Add(PriceToTick(High[0]));
			_lo.Add(PriceToTick(Low[0]));
			int n = _hi.Count;

			int c = n - 1 - PivotRight;
			if (c < PivotLeft) return;

			bool esH = true, esL = true;
			for (int d = 1; d <= PivotLeft; d++)
			{
				if (!(_hi[c] >= _hi[c - d])) esH = false;
				if (!(_lo[c] <= _lo[c - d])) esL = false;
			}
			for (int d = 1; d <= PivotRight; d++)
			{
				if (!(_hi[c] > _hi[c + d])) esH = false;
				if (!(_lo[c] < _lo[c + d])) esL = false;
			}
			int gb = CurrentBar - PivotRight;
			if (esH) AgregarSwing(new Swing { Bar = gb, IsHigh = true, Tick = _hi[c] });
			if (esL) AgregarSwing(new Swing { Bar = gb, IsHigh = false, Tick = _lo[c] });
		}

		private void AgregarSwing(Swing s)
		{
			// los swings ALTERNAN: dos maximos seguidos no delimitan un tramo.
			// Si llega un segundo maximo sin minimo en medio, reemplaza al anterior
			// solo si es mas extremo.
			if (_swings.Count > 0 && _swings[_swings.Count - 1].IsHigh == s.IsHigh)
			{
				Swing prev = _swings[_swings.Count - 1];
				bool mejor = s.IsHigh ? s.Tick > prev.Tick : s.Tick < prev.Tick;
				if (mejor) _swings[_swings.Count - 1] = s;
				return;
			}
			_swings.Add(s);
			if (_swings.Count < 2) return;
			CerrarTramo(_swings[_swings.Count - 2], s);
		}

		private void CerrarTramo(Swing a, Swing b)
		{
			Leg leg = new Leg();
			leg.StartBar = a.Bar; leg.EndBar = b.Bar;
			leg.StartTick = a.Tick; leg.EndTick = b.Tick;
			leg.Direction = b.Tick > a.Tick ? 1 : -1;
			leg.LengthTicks = Math.Abs(b.Tick - a.Tick);

			// corte CAUSAL: solo con los tramos ya cerrados antes de este
			leg.CutTicks = Corte();
			leg.IsLong = leg.CutTicks > 0 && leg.LengthTicks >= leg.CutTicks
				&& leg.LengthTicks >= MinLegTicks;

			long loLeg = Math.Min(leg.StartTick, leg.EndTick);
			long hiLeg = Math.Max(leg.StartTick, leg.EndTick);
			leg.ZonesInside = ZonasAdentro(leg.StartBar, leg.EndBar, loLeg, hiLeg);
			leg.IsClean = leg.IsLong && leg.ZonesInside == 0;

			_legs.Add(leg);
			_largos.Add(leg.LengthTicks);
			if (_largos.Count > WindowLegs) _largos.RemoveRange(0, _largos.Count - WindowLegs);
			if (_legs.Count > 5000) _legs.RemoveRange(0, _legs.Count - 5000);
			Escribir(leg);
		}

		private long Corte()
		{
			if (_largos.Count < 5) return 0;
			List<long> v = new List<long>(_largos);
			v.Sort();
			int idx = (int)(v.Count * (1.0 - TopPct / 100.0));
			if (idx >= v.Count) idx = v.Count - 1;
			if (idx < 0) idx = 0;
			return v[idx];
		}

		private void Escribir(Leg leg)
		{
			if (_log == null || _logFailed) return;
			try
			{
				_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13}",
					_legs.Count, leg.StartBar, leg.EndBar,
					Time[0].ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					_sessionIndex, leg.Direction, leg.StartTick, leg.EndTick,
					leg.LengthTicks, leg.CutTicks, leg.EndBar - leg.StartBar,
					leg.ZonesInside, leg.IsLong ? 1 : 0, leg.IsClean ? 1 : 0));
			}
			catch (Exception ex) { _logFailed = true; Print(Name + " ERROR [event_log]: " + ex.Message); }
		}

		public override void OnRenderTargetChanged()
		{
			if (_dxUp != null) { _dxUp.Dispose(); _dxUp = null; }
			if (_dxDown != null) { _dxDown.Dispose(); _dxDown = null; }
			if (RenderTarget == null) return;
			try { _dxUp = UpColor.ToDxBrush(RenderTarget); _dxDown = DownColor.ToDxBrush(RenderTarget); }
			catch { _dxUp = null; _dxDown = null; }
		}

		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (ChartBars == null || RenderTarget == null || _legs == null) return;
			if (_dxUp == null) OnRenderTargetChanged();
			if (_dxUp == null) return;

			// Si la fuente de zonas no esta en el chart hay que DECIRLO: dibujar
			// cero impulsos limpios y quedarse callado se lee como "no hay", que es
			// una conclusion, no un estado de falta de datos.
			if (ZonasFuente() == null && ShowLabel)
			{
				using (SharpDX.DirectWrite.TextFormat tf = new SharpDX.DirectWrite.TextFormat(
					Core.Globals.DirectWriteFactory, "Arial", 13))
				using (SharpDX.DirectWrite.TextLayout tl = new SharpDX.DirectWrite.TextLayout(
					Core.Globals.DirectWriteFactory,
					"CleanImpulses: falta HFTZonesNQPureV4 en el chart", tf, 600, 20))
				{
					RenderTarget.DrawTextLayout(
						new SharpDX.Vector2(ChartPanel.X + 8, ChartPanel.Y + 8), tl, _dxDown);
				}
				return;
			}

			int from = ChartBars.FromIndex, to = ChartBars.ToIndex;
			SharpDX.Direct2D1.AntialiasMode prev = RenderTarget.AntialiasMode;
			RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.PerPrimitive;
			try
			{
				for (int i = 0; i < _legs.Count; i++)
				{
					Leg L = _legs[i];
					if (!L.IsClean) continue;                 // SOLO los limpios
					if (L.EndBar < from || L.StartBar > to) continue;
					float x1 = chartControl.GetXByBarIndex(ChartBars, Math.Max(L.StartBar, from));
					float x2 = chartControl.GetXByBarIndex(ChartBars, Math.Min(L.EndBar, to));
					float y1 = chartScale.GetYByValue(L.StartTick * TickSize);
					float y2 = chartScale.GetYByValue(L.EndTick * TickSize);
					RenderTarget.DrawLine(new SharpDX.Vector2(x1, y1), new SharpDX.Vector2(x2, y2),
						L.Direction == 1 ? _dxUp : _dxDown, LineWidthPixels);
				}
			}
			finally { RenderTarget.AntialiasMode = prev; }
		}

		#region Properties
		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "PivotLeft", Order = 1, GroupName = "1. Tramos")]
		public int PivotLeft { get; set; }

		[NinjaScriptProperty] [Range(1, 200)]
		[Display(Name = "PivotRight", Order = 2, GroupName = "1. Tramos")]
		public int PivotRight { get; set; }

		[NinjaScriptProperty] [Range(0.1, 100.0)]
		[Display(Name = "TopPct", Order = 3, GroupName = "1. Tramos",
			Description = "Que porcentaje de los tramos mas largos se considera. 5 = el 5 % "
				+ "mas largo.")]
		public double TopPct { get; set; }

		[NinjaScriptProperty] [Range(5, 100000)]
		[Display(Name = "WindowLegs", Order = 4, GroupName = "1. Tramos",
			Description = "Sobre cuantos tramos YA CERRADOS se calcula el corte. El "
				+ "percentil es causal: usar el chart entero clasificaria con informacion "
				+ "del futuro.")]
		public int WindowLegs { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "MinLegTicks", Order = 5, GroupName = "1. Tramos",
			Description = "Piso absoluto opcional, ademas del percentil.")]
		public int MinLegTicks { get; set; }

		[NinjaScriptProperty] [Range(-1, 10000)]
		[Display(Name = "GraceBars (-1 = PivotRight)", Order = 6, GroupName = "1. Tramos",
			Description = "Barras de gracia despues del pivote para contar una zona como "
				+ "creada por el impulso. La zona se registra al cerrarse el movimiento, "
				+ "no en el pivote exacto. Con PivotRight no hay mirada al futuro.")]
		public int GraceBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "RequirePriceOverlap", Order = 7, GroupName = "1. Tramos",
			Description = "OFF (default) = cualquier zona creada dentro del impulso lo "
				+ "descalifica, en cualquier nivel. ON exige ademas que la zona caiga dentro "
				+ "del recorrido de precio; existe solo para contrastar.")]
		public bool RequirePriceOverlap { get; set; }

		[XmlIgnore] [Display(Name = "UpColor", Order = 10, GroupName = "2. Visual")]
		public Brush UpColor { get; set; }
		[Browsable(false)]
		public string UpColorSerialize
		{
			get { return Serialize.BrushToString(UpColor); }
			set { UpColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "DownColor", Order = 11, GroupName = "2. Visual")]
		public Brush DownColor { get; set; }
		[Browsable(false)]
		public string DownColorSerialize
		{
			get { return Serialize.BrushToString(DownColor); }
			set { DownColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty] [Range(1, 20)]
		[Display(Name = "LineWidthPixels", Order = 12, GroupName = "2. Visual")]
		public float LineWidthPixels { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "ShowLabel", Order = 13, GroupName = "2. Visual",
			Description = "Avisa en pantalla si falta HFTZonesNQPureV4. Sin ese aviso, "
				+ "cero impulsos limpios se lee como una conclusion en vez de como falta "
				+ "de datos.")]
		public bool ShowLabel { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EventLogPath (vacio = off)", Order = 20, GroupName = "3. Auditoria",
			Description = "CSV con TODOS los tramos, no solo los marcados.")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
