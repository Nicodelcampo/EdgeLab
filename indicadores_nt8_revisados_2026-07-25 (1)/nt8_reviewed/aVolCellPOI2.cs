// ============================================================================
// aVolCellPOI2.cs — Anomaly Volume Cell POI v2 (perfil horario por sesiones)
// ============================================================================
//
// NOTA DE DISEÑO (LEER ANTES DE MODIFICAR O TRADUCIR)
// ----------------------------------------------------------------------------
// Este indicador está escrito para ser TRADUCIDO a Python/vectorbt (EdgeLab).
// Cada decisión ambigua está resuelta y declarada acá. Si cambiás algo de la
// sección "CONTRATO", la versión Python deja de ser comparable y la paridad
// (GATE P2) va a fallar. Cambios de contrato = nueva versión del indicador.
//
// HIPÓTESIS
//   El volumen por celda de precio tiene estacionalidad intradiaria fuerte.
//   Una celda es "anómala" si su volumen está en la cola extrema del perfil
//   HISTÓRICO de celdas del mismo bucket horario, construido con sesiones
//   completas anteriores (nunca con la sesión actual).
//   La anomalía NO tiene dirección inherente: el indicador NO etiqueta la zona
//   como soporte o resistencia. Eso lo decide EdgeLab con event studies.
//
// CONTRATO (invariantes para la paridad NT8 <-> Python)
//   1. Calculate = OnBarClose, fijo. Clase de repintado: non_repainting.
//      Una zona creada al cierre de la barra B está disponible (available_at)
//      recién a partir de la barra B+1. La barra creadora NUNCA toca ni
//      invalida su propia zona (anti look-ahead).
//   2. Precios en ticks ENTEROS: tick = round(precio_snapeado / TickSize),
//      MidpointRounding.AwayFromZero, después del snap oficial de NT8.
//      Límites físicos de una celda P: [P - TickSize/2, P + TickSize/2].
//   3. Bucket horario: se ancla en (Time[0] - 1 segundo), es decir "cierre
//      menos epsilon", para que una barra que cierra exactamente en 09:35:00
//      pertenezca a la ventana 09:30-09:35 y no a la siguiente.
//      BucketAnchor = SessionRelative (default): minutos desde el inicio REAL
//      de sesión (SessionIterator.ActualSessionBegin) / TimeBucketMinutes.
//      WallClock: (hora*60+minuto)/TimeBucketMinutes (modo legacy).
//      ATENCIÓN: Time[0] está en la timezone del chart. Registrar la timezone
//      en el data contract; la versión Python debe usar la misma.
//   4. Perfil histórico: SOLO sesiones completas anteriores. La sesión actual
//      se acumula aparte y se incorpora al historial al inicio de la sesión
//      siguiente. La primera sesión (potencialmente parcial) se DESCARTA.
//      Lookback: LookbackSessions sesiones por bucket (FIFO por sesión, no por
//      celda). Solo entran celdas con volumen > 0 (distribución condicionada).
//   5. Ponderación: EqualSessionWeight => cada sesión pesa 1 en total (peso
//      por celda = 1/celdas_de_esa_sesión_en_ese_bucket). PooledCells => cada
//      celda pesa 1 (equivalente a la v1, sesgada hacia días de rango grande).
//   6. Cuantil ponderado SIN interpolación: threshold = menor valor v tal que
//      peso_acumulado(<= v) >= p * peso_total. Percentil empírico de x =
//      peso_acumulado(<= x) / peso_total. (Distinto de la v1, que interpolaba
//      linealmente; declarado a propósito por ser trivialmente ponderable y
//      exacto de reproducir.)
//   7. RobustLogZ: y = ln(1+v); mediana ponderada m y MAD ponderada de y;
//      z = (y - m) / (1.4826 * MAD). Si MAD = 0, z = 999 si y > m, si no 0.
//   8. Ciclo de vida (aproximación a nivel barra; la resolución definitiva
//      intrabar la hará EdgeLab con ticks):
//        TOUCH: [Low, High] de una barra posterior intersecta la zona.
//        FirstTouch: el primer touch invalida.
//        CloseThrough: lado de referencia = lado del Close al crearse la zona
//          (arriba/abajo; si cierra dentro, queda indefinido y lo fija el
//          primer close externo posterior). Invalida el primer close en el
//          lado OPUESTO al de referencia.
//        MaxTouches > 0: invalida al alcanzar N touches. MaxAgeBars: expira.
//   9. Fusión: celdas anómalas con separación <= MergeGapTicks se fusionan en
//      una zona (default 0 = solo contiguas). Score de zona = máximo percentil
//      de sus celdas + suma de valores + cantidad de celdas.
//  10. La identidad analítica de una zona es (created_at, geometría inicial en
//      ticks), NUNCA el tag de dibujo ni el id local.
//
// PARAMETRIZACIÓN PARA FUERZA BRUTA EN VECTORBT
//   Grupo 1 - SEMÁNTICOS (entran en el run_id; cambiarlos = recomputar todo):
//     BucketAnchor, TimeBucketMinutes, LookbackSessions, ProfileWeighting,
//     DetectionSource, DetectionMethod.
//     Barrerlos como POCAS variantes discretas y declaradas (son "otros
//     indicadores"), no como grilla densa.
//   Grupo 2 - SELECCIÓN (baratos: se barren OFFLINE sobre el export OBS sin
//     recomputar): DetectionPercentile, RobustZThreshold, MinAbsoluteVolume,
//     MinSessions, MinCellSamples.
//     El indicador exporta TODAS las celdas con percentil empírico >=
//     ExportFloorPercentile (evento OBS), con su percentil y robust-z
//     continuos. En vectorbt, "cambiar el percentil de corte" = filtrar filas.
//   Grupo 3 - GEOMETRÍA (baratos offline si hay OBS): MergeGapTicks,
//     MinZoneCells. La fusión es re-derivable desde las OBS por barra.
//   Grupo 4 - CICLO DE VIDA (baratos offline con barras/ticks): 
//     InvalidationMode, MaxAgeBars, MaxTouches.
//   Grupo 5 - VISUALES (NO entran en el run_id ni en la optimización):
//     Opacity, VisualExtendBars, MaxRenderedZones. MaxRenderedZones limita
//     SOLO el dibujo; nunca borra zonas del estado interno.
//   Grillas sugeridas para investigación (no optimizadas, solo punto de
//   partida): TimeBucketMinutes {5,15,30}; DetectionPercentile
//   {99.0,99.5,99.75,99.9}; LookbackSessions {10,20,40}; resto fijo primero.
//
// EXPORT / ORÁCULO
//   EventLogPath != "" => CSV append-safe con eventos:
//     OBS, ZONE_CREATED, ZONE_TOUCHED, ZONE_INVALIDATED, ZONE_EXPIRED, ERROR.
//   Primera línea: metadatos (# meta,...) con instrumento, tick size y todos
//   los parámetros semánticos. Este CSV es la fuente para GATE P2A/P2B y para
//   los barridos offline. El dibujo es una representación del estado, nunca
//   la fuente de verdad.
//
// REQUISITOS Y ADVERTENCIAS
//   - Requiere barras Volumetric (OrderFlow). DetectionSource=TotalVolume es
//     reconstruible desde ticks Last puros; AbsDelta y MaxSide requieren
//     histórico bid/ask real (verificar en el data contract antes de usarlos
//     para investigación).
//   - Cargar como mínimo LookbackSessions + MinSessions sesiones de data.
//   - NO usar en series de contrato continuo con saltos de rollover: el perfil
//     y las zonas son por contrato individual. Feriados y medias ruedas
//     contaminan el perfil (pendiente: session_quality_flag en EdgeLab).
//   - IsSuspendedWhileInactive = false: el resultado no puede depender de si
//     el chart estuvo visible.
//   - Errores NUNCA silenciosos: emiten evento ERROR y marcan el run inválido.
//   - La región "NinjaScript generated code" se omite a propósito: NT8 la
//     regenera automáticamente al compilar.
// ============================================================================

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Windows.Media;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.BarsTypes;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// Enums a scope GLOBAL (no dentro del namespace Indicators): NT8 genera
// wrappers en MarketAnalyzerColumns/Strategies que los referencian por
// nombre simple; en scope global se resuelven desde cualquier namespace
// (mismo patron que BigTrap2). En el namespace daban CS0246.
public enum AVCP2BucketAnchor { SessionRelative = 0, WallClock = 1 }
public enum AVCP2ProfileWeighting { EqualSessionWeight = 0, PooledCells = 1 }
public enum AVCP2DetectionSource { TotalVolume = 0, AbsDelta = 1, MaxSide = 2 }
public enum AVCP2DetectionMethod { Quantile = 0, RobustLogZ = 1 }
public enum AVCP2InvalidationMode { None = 0, FirstTouch = 1, CloseThrough = 2 }

namespace NinjaTrader.NinjaScript.Indicators
{
	public class aVolCellPOI2 : Indicator
	{
		private const int HeatSteps = 9;

		// ---------- estado del perfil ----------
		// history[bucket] = cola FIFO de sesiones; cada sesión = lista de valores por celda
		private Dictionary<int, Queue<List<double>>> history;
		private Dictionary<int, List<double>> pendingByBucket; // sesión actual (excluida del perfil)
		private Dictionary<int, BucketCache> cacheByBucket;    // caché congelada por sesión
		private bool firstRollDone;                            // descarta la primera sesión parcial
		private int sessionIndex;

		// ---------- zonas ----------
		private readonly List<ActiveZone> activeZones = new List<ActiveZone>();
		private readonly Queue<string> renderedTags = new Queue<string>();
		private long zoneCounter;

		// ---------- infra ----------
		// Footprint reconstruido desde la subserie de 1 tick (guia SS11/SS13):
		// motor unico, sin dependencia de OrderFlow/Volumetric. Identico al port Python.
		private Dictionary<long, double> pendingAsk = new Dictionary<long, double>(64);
		private Dictionary<long, double> pendingBid = new Dictionary<long, double>(64);
		private Dictionary<long, double> curAsk;   // footprint de la barra que cierra
		private Dictionary<long, double> curBid;
		private double lastTickPrice = double.NaN;
		private int    lastTickDir;
		private SessionIterator sessionIterator;
		private StreamWriter writer;
		private bool writerFailed;
		private long eventSeq;
		private bool runInvalid;
		private Brush[] heatBrushes;

		private class BucketCache
		{
			public double[] Values;   // ordenados ascendente
			public double[] CumW;     // pesos acumulados alineados
			public double TotalW;
			public int SampleCount;
			public int SessionCount;
			public double QuantileThreshold;
			public double LogMedian;
			public double MadScaled;  // 1.4826 * MAD ponderada de ln(1+v)
		}

		private class ActiveZone
		{
			public long Id;
			public int CreatedBar;
			public DateTime CreatedTime;
			public long LowerTick, UpperTick;
			public double LowerPrice, UpperPrice;
			public double MaxPct, MaxZ, SumValue;
			public int CellCount, TouchCount, RefSide;
			public string Tag;
		}

		private class Cell
		{
			public long Tick;
			public double Value, Total, Pct, Z;
		}

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Celdas de volumen anómalo vs perfil horario por sesiones. v2, contrato para EdgeLab/vectorbt.";
				Name = "aVolCellPOI2";
				Calculate = Calculate.OnBarClose;      // CONTRATO: no cambiar
				IsOverlay = true;
				DisplayInDataBox = false;
				DrawOnPricePanel = true;
				IsSuspendedWhileInactive = false;      // CONTRATO: reproducibilidad

				// Grupo 1: semánticos
				BucketAnchor        = AVCP2BucketAnchor.SessionRelative;
				TimeBucketMinutes   = 5;
				LookbackSessions    = 20;
				ProfileWeighting    = AVCP2ProfileWeighting.EqualSessionWeight;
				DetectionSource     = AVCP2DetectionSource.TotalVolume;
				DetectionMethod     = AVCP2DetectionMethod.Quantile;
				// Grupo 2: selección
				DetectionPercentile = 99.5;
				RobustZThreshold    = 4.0;
				MinAbsoluteVolume   = 10;
				MinSessions         = 15;
				MinCellSamples      = 500;
				ExportFloorPercentile = 95.0;
				// Grupo 3: geometría
				MergeGapTicks       = 0;
				MinZoneCells        = 1;
				// Grupo 4: ciclo de vida
				InvalidationMode    = AVCP2InvalidationMode.CloseThrough;
				MaxAgeBars          = 2000;
				MaxTouches          = 0;
				// Grupo 5: export y visual
				EventLogPath        = "";
				Opacity             = 20;
				VisualExtendBars    = 500;
				MaxRenderedZones    = 250;
			}
			else if (State == State.Configure)
			{
				// Motor unico: SIEMPRE la subserie de 1 tick (guia SS11/SS13).
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				history         = new Dictionary<int, Queue<List<double>>>();
				pendingByBucket = new Dictionary<int, List<double>>();
				cacheByBucket   = new Dictionary<int, BucketCache>();
				sessionIterator = new SessionIterator(Bars);
				firstRollDone   = false;
				sessionIndex    = 0;
				zoneCounter     = 0;
				eventSeq        = 0;
				runInvalid      = false;
				writerFailed    = false;
				heatBrushes     = BuildHeatBrushes();
			}
			else if (State == State.Terminated)
			{
				try { if (writer != null) { writer.Flush(); writer.Close(); writer = null; } }
				catch { }
			}
		}

		protected override void OnBarUpdate()
		{
			if (BarsInProgress == 1) { AccumulateTick(); return; }
			if (BarsInProgress != 0) return;

			// take + reset del footprint reconstruido (tambien en warm-up: sin fuga)
			curAsk = pendingAsk; curBid = pendingBid;
			pendingAsk = new Dictionary<long, double>(64);
			pendingBid = new Dictionary<long, double>(64);

			if (CurrentBars.Length < 2 || CurrentBars[1] < 0)
			{
				EmitError("tick_series", "subserie de 1 tick sin datos; descargar tick data historico. Cero detecciones, nunca fallback.");
				return;
			}

			// mantener la sesión actualizada (cubre inicio a mitad de sesión)
			if (Bars.IsFirstBarOfSession || sessionIterator.ActualSessionEnd < Time[0])
			{
				sessionIterator.GetNextSession(Time[0], true);
				if (Bars.IsFirstBarOfSession)
					RollSessionIntoHistory();
			}

			// 1) ciclo de vida ANTES de crear zonas nuevas (anti look-ahead)
			UpdateZoneLifecycle();

			// 2) celdas de la barra actual
			List<Cell> cells = CollectCells();
			if (cells == null) return; // error ya emitido

			int bucket = GetBucket();

			// 3) detección contra perfil congelado (sin la sesión actual)
			BucketCache cache = GetCache(bucket);
			if (cache != null)
			{
				List<Cell> anomalous = null;
				double detCut = DetectionPercentile / 100.0;

				foreach (Cell c in cells)
				{
					c.Pct = EmpiricalPercentile(cache, c.Value);
					c.Z   = RobustZ(cache, c.Value);

					if (c.Pct * 100.0 >= ExportFloorPercentile)
						EmitEvent("OBS", bucket, c.Tick, c.Tick, c.Value, c.Total,
							cache.QuantileThreshold, c.Pct, c.Z,
							cache.SampleCount, cache.SessionCount, 0, 0, "");

					bool isAnomaly =
						c.Total >= MinAbsoluteVolume &&
						(DetectionMethod == AVCP2DetectionMethod.Quantile
							? c.Value >= cache.QuantileThreshold && c.Pct >= detCut
							: c.Z >= RobustZThreshold);

					if (isAnomaly)
					{
						if (anomalous == null) anomalous = new List<Cell>();
						anomalous.Add(c);
					}
				}

				if (anomalous != null)
					CreateZones(anomalous, cache, bucket);
			}

			// 4) acumular la barra en la sesión pendiente (DESPUÉS de comparar)
			List<double> pend;
			if (!pendingByBucket.TryGetValue(bucket, out pend))
			{
				pend = new List<double>();
				pendingByBucket[bucket] = pend;
			}
			foreach (Cell c in cells) pend.Add(c.Value);
		}

		// ---------------- perfil ----------------

		private void RollSessionIntoHistory()
		{
			if (!firstRollDone)
			{
				// la primera sesión observada puede estar incompleta: se descarta
				pendingByBucket.Clear();
				firstRollDone = true;
			}
			else
			{
				foreach (KeyValuePair<int, List<double>> kv in pendingByBucket)
				{
					if (kv.Value.Count == 0) continue;
					Queue<List<double>> q;
					if (!history.TryGetValue(kv.Key, out q))
					{
						q = new Queue<List<double>>();
						history[kv.Key] = q;
					}
					q.Enqueue(kv.Value);
					while (q.Count > LookbackSessions) q.Dequeue();
				}
				pendingByBucket = new Dictionary<int, List<double>>();
				sessionIndex++;
			}
			cacheByBucket.Clear(); // el perfil solo cambia acá => cachés válidas toda la sesión
		}

		private BucketCache GetCache(int bucket)
		{
			BucketCache c;
			if (cacheByBucket.TryGetValue(bucket, out c)) return c;
			c = BuildCache(bucket);
			cacheByBucket[bucket] = c;
			return c;
		}

		private BucketCache BuildCache(int bucket)
		{
			Queue<List<double>> sessions;
			if (!history.TryGetValue(bucket, out sessions)) return null;
			if (sessions.Count < MinSessions) return null;

			int n = 0;
			foreach (List<double> s in sessions) n += s.Count;
			if (n < MinCellSamples) return null;

			double[] vals = new double[n];
			double[] wts  = new double[n];
			int i = 0;
			foreach (List<double> s in sessions)
			{
				double w = ProfileWeighting == AVCP2ProfileWeighting.EqualSessionWeight
					? 1.0 / s.Count : 1.0;
				foreach (double v in s) { vals[i] = v; wts[i] = w; i++; }
			}
			Array.Sort(vals, wts);

			double[] cum = new double[n];
			double tot = 0;
			for (i = 0; i < n; i++) { tot += wts[i]; cum[i] = tot; }

			BucketCache c = new BucketCache
			{
				Values = vals, CumW = cum, TotalW = tot,
				SampleCount = n, SessionCount = sessions.Count
			};
			c.QuantileThreshold = WeightedQuantile(c, DetectionPercentile / 100.0);

			// stats robustas (una vez por bucket por sesión)
			double medY = Math.Log(1.0 + WeightedQuantile(c, 0.5));
			double[] dev = new double[n];
			double[] w2  = new double[n];
			for (i = 0; i < n; i++)
			{
				dev[i] = Math.Abs(Math.Log(1.0 + vals[i]) - medY);
				w2[i]  = i == 0 ? cum[0] : cum[i] - cum[i - 1];
			}
			Array.Sort(dev, w2);
			double target = 0.5 * tot, acc = 0; double mad = dev[n - 1];
			for (i = 0; i < n; i++) { acc += w2[i]; if (acc >= target) { mad = dev[i]; break; } }
			c.LogMedian = medY;
			c.MadScaled = 1.4826 * mad;
			return c;
		}

		// menor valor con peso acumulado >= p * total (cuantil ponderado sin interpolación)
		private static double WeightedQuantile(BucketCache c, double p)
		{
			double target = p * c.TotalW;
			int lo = 0, hi = c.Values.Length - 1;
			while (lo < hi)
			{
				int mid = (lo + hi) / 2;
				if (c.CumW[mid] >= target) hi = mid; else lo = mid + 1;
			}
			return c.Values[lo];
		}

		// peso acumulado de valores <= x, dividido por el peso total
		private static double EmpiricalPercentile(BucketCache c, double x)
		{
			int lo = 0, hi = c.Values.Length - 1, idx = -1;
			while (lo <= hi)
			{
				int mid = (lo + hi) / 2;
				if (c.Values[mid] <= x) { idx = mid; lo = mid + 1; } else hi = mid - 1;
			}
			return idx < 0 ? 0.0 : c.CumW[idx] / c.TotalW;
		}

		private static double RobustZ(BucketCache c, double v)
		{
			double y = Math.Log(1.0 + v);
			if (c.MadScaled <= 0) return y > c.LogMedian ? 999.0 : 0.0;
			return (y - c.LogMedian) / c.MadScaled;
		}

		// ---------------- footprint reconstruido (subserie 1 tick) ----------------
		private void AccumulateTick()
		{
			double price = Closes[1][0];
			double vol   = Volumes[1][0];
			int    idx   = CurrentBars[1];
			double askQ  = BarsArray[1].GetAsk(idx);
			double bidQ  = BarsArray[1].GetBid(idx);
			int side = 0;
			if (askQ > 0 && bidQ > 0 && askQ >= bidQ)
			{
				if      (price >= askQ) side =  1;
				else if (price <= bidQ) side = -1;
			}
			if (side == 0) // dentro del spread o sin quotes -> tick rule (fallback declarado)
			{
				if (!double.IsNaN(lastTickPrice))
				{
					if      (price > lastTickPrice) side =  1;
					else if (price < lastTickPrice) side = -1;
					else                            side = lastTickDir;
				}
				if (side == 0) side = 1; // primer tick sin informacion (contrato)
			}
			lastTickPrice = price;
			lastTickDir   = side;
			long tick = (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
			Dictionary<long, double> map = side > 0 ? pendingAsk : pendingBid;
			double cur;
			map[tick] = map.TryGetValue(tick, out cur) ? cur + vol : vol;
		}

		// ---------------- celdas ----------------

		private List<Cell> CollectCells()
		{
			if (curAsk == null || curBid == null) return new List<Cell>();

			long loTick = SnapToTick(Low[0]);
			long hiTick = SnapToTick(High[0]);
			List<Cell> cells = new List<Cell>();

			for (long t = loTick; t <= hiTick; t++)
			{
				double a, b;
				double ask = curAsk.TryGetValue(t, out a) ? a : 0.0;
				double bid = curBid.TryGetValue(t, out b) ? b : 0.0;
				double total = ask + bid;
				if (total <= 0) continue; // CONTRATO: distribución condicionada a volumen > 0

				double value;
				switch (DetectionSource)
				{
					case AVCP2DetectionSource.AbsDelta:
						value = Math.Abs(ask - bid);
						break;
					case AVCP2DetectionSource.MaxSide:
						value = Math.Max(ask, bid);
						break;
					default:
						value = total;
						break;
				}
				cells.Add(new Cell { Tick = t, Value = value, Total = total });
			}
			return cells;
		}

		private long SnapToTick(double price)
		{
			double snapped = Instrument.MasterInstrument.RoundToTickSize(price);
			return (long)Math.Round(snapped / TickSize, MidpointRounding.AwayFromZero);
		}

		private int GetBucket()
		{
			DateTime anchor = Time[0].AddSeconds(-1); // CONTRATO: cierre menos epsilon
			if (BucketAnchor == AVCP2BucketAnchor.SessionRelative)
			{
				double mins = (anchor - sessionIterator.ActualSessionBegin).TotalMinutes;
				if (mins < 0) mins = 0;
				return (int)(mins / Math.Max(1, TimeBucketMinutes));
			}
			return (anchor.Hour * 60 + anchor.Minute) / Math.Max(1, TimeBucketMinutes);
		}

		// ---------------- zonas ----------------

		private void CreateZones(List<Cell> anomalous, BucketCache cache, int bucket)
		{
			anomalous.Sort((a, b) => a.Tick.CompareTo(b.Tick));

			int start = 0;
			for (int i = 1; i <= anomalous.Count; i++)
			{
				bool split = i == anomalous.Count ||
					anomalous[i].Tick - anomalous[i - 1].Tick > MergeGapTicks + 1;
				if (!split) continue;

				int count = i - start;
				if (count >= MinZoneCells)
				{
					double maxPct = 0, maxZ = 0, sum = 0;
					for (int k = start; k < i; k++)
					{
						if (anomalous[k].Pct > maxPct) maxPct = anomalous[k].Pct;
						if (anomalous[k].Z > maxZ) maxZ = anomalous[k].Z;
						sum += anomalous[k].Value;
					}

					ActiveZone z = new ActiveZone
					{
						Id = ++zoneCounter,
						CreatedBar = CurrentBar,
						CreatedTime = Time[0],
						LowerTick = anomalous[start].Tick,
						UpperTick = anomalous[i - 1].Tick,
						MaxPct = maxPct, MaxZ = maxZ, SumValue = sum,
						CellCount = count, TouchCount = 0
					};
					z.LowerPrice = (z.LowerTick - 0.5) * TickSize;
					z.UpperPrice = (z.UpperTick + 0.5) * TickSize;
					z.RefSide = Close[0] > z.UpperPrice ? 1 : (Close[0] < z.LowerPrice ? -1 : 0);
					z.Tag = "aVCP2_" + z.Id;

					activeZones.Add(z);
					EmitEvent("ZONE_CREATED", bucket, z.LowerTick, z.UpperTick, z.SumValue, 0,
						cache.QuantileThreshold, z.MaxPct, z.MaxZ,
						cache.SampleCount, cache.SessionCount, z.Id, 0, "cells=" + z.CellCount);
					DrawZone(z);
				}
				start = i;
			}
		}

		private void UpdateZoneLifecycle()
		{
			for (int i = activeZones.Count - 1; i >= 0; i--)
			{
				ActiveZone z = activeZones[i];
				if (z.CreatedBar >= CurrentBar) continue; // la barra creadora no interactúa

				bool touched = High[0] >= z.LowerPrice && Low[0] <= z.UpperPrice;
				if (touched)
				{
					z.TouchCount++;
					EmitEvent("ZONE_TOUCHED", 0, z.LowerTick, z.UpperTick, 0, 0, 0, 0, 0, 0, 0,
						z.Id, z.TouchCount, "");
				}

				string reason = null;
				if (InvalidationMode == AVCP2InvalidationMode.FirstTouch && touched)
					reason = "first_touch";
				else if (InvalidationMode == AVCP2InvalidationMode.CloseThrough)
				{
					int s = Close[0] > z.UpperPrice ? 1 : (Close[0] < z.LowerPrice ? -1 : 0);
					if (s != 0)
					{
						if (z.RefSide == 0) z.RefSide = s;
						else if (s == -z.RefSide) reason = "close_through";
					}
				}
				if (reason == null && MaxTouches > 0 && z.TouchCount >= MaxTouches)
					reason = "max_touches";

				if (reason != null)
				{
					EmitEvent("ZONE_INVALIDATED", 0, z.LowerTick, z.UpperTick, 0, 0, 0, 0, 0, 0, 0,
						z.Id, z.TouchCount, reason);
					RemoveDrawObject(z.Tag);
					activeZones.RemoveAt(i);
				}
				else if (CurrentBar - z.CreatedBar >= MaxAgeBars)
				{
					EmitEvent("ZONE_EXPIRED", 0, z.LowerTick, z.UpperTick, 0, 0, 0, 0, 0, 0, 0,
						z.Id, z.TouchCount, "max_age");
					RemoveDrawObject(z.Tag);
					activeZones.RemoveAt(i);
				}
			}
		}

		// ---------------- salida analítica de solo lectura ----------------

		public int ActiveZoneCount { get { return activeZones.Count; } }

		// ---------------- render (nunca fuente de verdad) ----------------

		private void DrawZone(ActiveZone z)
		{
			double t;
			if (DetectionMethod == AVCP2DetectionMethod.Quantile)
			{
				double cut = DetectionPercentile / 100.0;
				t = (z.MaxPct - cut) / Math.Max(1e-9, 1.0 - cut);
			}
			else
				t = (z.MaxZ - RobustZThreshold) / Math.Max(1e-9, RobustZThreshold);
			t = Math.Max(0, Math.Min(1, t));

			int maxOp = Math.Max(1, Math.Min(100, Opacity));
			int minOp = Math.Max(1, (int)Math.Round(maxOp * 0.25));
			int op = (int)Math.Round(minOp + (maxOp - minOp) * t);
			int idx = Math.Max(0, Math.Min(HeatSteps - 1, (int)Math.Floor(t * HeatSteps)));

			Draw.Rectangle(this, z.Tag, false,
				0, z.UpperPrice, -Math.Abs(VisualExtendBars), z.LowerPrice,
				Brushes.Transparent, heatBrushes[idx], op);

			renderedTags.Enqueue(z.Tag);
			while (renderedTags.Count > MaxRenderedZones)
				RemoveDrawObject(renderedTags.Dequeue()); // solo dibujo; el estado no se toca
		}

		private static Brush[] BuildHeatBrushes()
		{
			Color[] colors = new Color[]
			{
				Color.FromArgb(255,   0, 200, 0), Color.FromArgb(255,  80, 220, 0),
				Color.FromArgb(255, 150, 240, 0), Color.FromArgb(255, 230, 230, 0),
				Color.FromArgb(255, 255, 200, 0), Color.FromArgb(255, 255, 150, 0),
				Color.FromArgb(255, 255,  90, 0), Color.FromArgb(255, 255,  40, 0),
				Color.FromArgb(255, 220,   0, 0)
			};
			Brush[] brushes = new Brush[HeatSteps];
			for (int i = 0; i < HeatSteps; i++)
			{
				SolidColorBrush b = new SolidColorBrush(colors[i]);
				b.Freeze();
				brushes[i] = b;
			}
			return brushes;
		}

		// ---------------- infra ----------------

		private void EmitError(string code, string message)
		{
			runInvalid = true;
			Print(Name + " ERROR [" + code + "] bar=" + CurrentBar + ": " + message);
			EmitEvent("ERROR", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, code);
		}

		private void EmitEvent(string type, int bucket, long lowerTick, long upperTick,
			double value, double totalVolume, double threshold, double pct, double z,
			int sampleCount, int sessionCount, long zoneId, int touchCount, string reason)
		{
			if (EventLogPath == null || EventLogPath.Length == 0 || writerFailed) return;
			try
			{
				if (writer == null)
				{
					writer = new StreamWriter(EventLogPath, false);
					writer.WriteLine("# meta,indicator=aVolCellPOI2,version=2.0,instrument="
						+ Instrument.FullName + ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
						+ ",bucket_anchor=" + BucketAnchor + ",bucket_minutes=" + TimeBucketMinutes
						+ ",lookback_sessions=" + LookbackSessions + ",weighting=" + ProfileWeighting
						+ ",source=" + DetectionSource + ",method=" + DetectionMethod
						+ ",percentile=" + DetectionPercentile.ToString(CultureInfo.InvariantCulture)
						+ ",robust_z=" + RobustZThreshold.ToString(CultureInfo.InvariantCulture)
						+ ",export_floor=" + ExportFloorPercentile.ToString(CultureInfo.InvariantCulture));
					writer.WriteLine("event_seq,event_type,bar_index,bar_close_time,session_index,"
						+ "bucket,lower_tick,upper_tick,value,total_volume,threshold,empirical_pct,"
						+ "robust_z,sample_count,session_count,zone_id,touch_count,reason");
				}
				eventSeq++;
				writer.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17}",
					eventSeq, type, CurrentBar,
					Time[0].ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					sessionIndex, bucket, lowerTick, upperTick,
					value, totalVolume, threshold,
					pct.ToString("0.######", CultureInfo.InvariantCulture),
					z.ToString("0.####", CultureInfo.InvariantCulture),
					sampleCount, sessionCount, zoneId, touchCount, reason));
			}
			catch (Exception ex)
			{
				writerFailed = true;
				Print(Name + " ERROR [event_log]: " + ex.Message);
			}
		}

		#region Properties

		// -------- Grupo 1: semánticos (run_id) --------
		[NinjaScriptProperty]
		[Display(Name = "Bucket Anchor", Order = 1, GroupName = "1. Semántica (run_id)",
			Description = "SessionRelative: minutos desde el inicio real de sesión (recomendado). WallClock: hora civil (legacy).")]
		public AVCP2BucketAnchor BucketAnchor { get; set; }

		[NinjaScriptProperty]
		[Range(1, 120)]
		[Display(Name = "Time Bucket (minutos)", Order = 2, GroupName = "1. Semántica (run_id)")]
		public int TimeBucketMinutes { get; set; }

		[NinjaScriptProperty]
		[Range(2, 200)]
		[Display(Name = "Lookback Sessions", Order = 3, GroupName = "1. Semántica (run_id)",
			Description = "FIFO por sesión completa, no por celda. La sesión actual nunca entra al perfil.")]
		public int LookbackSessions { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Profile Weighting", Order = 4, GroupName = "1. Semántica (run_id)",
			Description = "EqualSessionWeight: cada sesión pesa igual. PooledCells: cada celda pesa igual (sesgo a días de rango grande).")]
		public AVCP2ProfileWeighting ProfileWeighting { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Detection Source", Order = 5, GroupName = "1. Semántica (run_id)",
			Description = "TotalVolume es reconstruible desde ticks Last. AbsDelta/MaxSide requieren bid/ask histórico real.")]
		public AVCP2DetectionSource DetectionSource { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Detection Method", Order = 6, GroupName = "1. Semántica (run_id)")]
		public AVCP2DetectionMethod DetectionMethod { get; set; }

		// -------- Grupo 2: selección (barrible offline vía OBS) --------
		[NinjaScriptProperty]
		[Range(90.0, 99.99)]
		[Display(Name = "Detection Percentile", Order = 10, GroupName = "2. Selección (barrible offline)")]
		public double DetectionPercentile { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 20.0)]
		[Display(Name = "Robust Z Threshold", Order = 11, GroupName = "2. Selección (barrible offline)")]
		public double RobustZThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100000)]
		[Display(Name = "Min Absolute Volume", Order = 12, GroupName = "2. Selección (barrible offline)",
			Description = "Filtro anti-ruido sobre el volumen TOTAL de la celda, sea cual sea el Detection Source.")]
		public int MinAbsoluteVolume { get; set; }

		[NinjaScriptProperty]
		[Range(2, 200)]
		[Display(Name = "Min Sessions", Order = 13, GroupName = "2. Selección (barrible offline)",
			Description = "Sesiones independientes mínimas en el bucket antes de detectar.")]
		public int MinSessions { get; set; }

		[NinjaScriptProperty]
		[Range(10, 100000)]
		[Display(Name = "Min Cell Samples", Order = 14, GroupName = "2. Selección (barrible offline)",
			Description = "Celdas históricas mínimas en el bucket. Ambos mínimos deben cumplirse.")]
		public int MinCellSamples { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 99.99)]
		[Display(Name = "Export Floor Percentile", Order = 15, GroupName = "2. Selección (barrible offline)",
			Description = "Exporta como OBS toda celda con percentil >= este piso, aunque no supere el corte. Clave para barrer umbrales en vectorbt sin recomputar.")]
		public double ExportFloorPercentile { get; set; }

		// -------- Grupo 3: geometría --------
		[NinjaScriptProperty]
		[Range(0, 5)]
		[Display(Name = "Merge Gap Ticks", Order = 20, GroupName = "3. Geometría",
			Description = "0 = fusiona solo celdas contiguas (recomendado para paridad).")]
		public int MergeGapTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 50)]
		[Display(Name = "Min Zone Cells", Order = 21, GroupName = "3. Geometría")]
		public int MinZoneCells { get; set; }

		// -------- Grupo 4: ciclo de vida --------
		[NinjaScriptProperty]
		[Display(Name = "Invalidation Mode", Order = 30, GroupName = "4. Ciclo de vida")]
		public AVCP2InvalidationMode InvalidationMode { get; set; }

		[NinjaScriptProperty]
		[Range(10, 50000)]
		[Display(Name = "Max Age (barras)", Order = 31, GroupName = "4. Ciclo de vida")]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Max Touches (0 = ilimitado)", Order = 32, GroupName = "4. Ciclo de vida")]
		public int MaxTouches { get; set; }

		// -------- Grupo 5: export y visual (fuera del run_id) --------
		[NinjaScriptProperty]
		[Display(Name = "Event Log Path (CSV)", Order = 40, GroupName = "5. Export y visual (no run_id)",
			Description = "Vacío = sin export. Ej: C:\\ProyectosQuant\\EdgeLab\\exports\\avcp2_NQ.csv")]
		public string EventLogPath { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Opacity", Order = 41, GroupName = "5. Export y visual (no run_id)")]
		public int Opacity { get; set; }

		[NinjaScriptProperty]
		[Range(5, 5000)]
		[Display(Name = "Visual Extend Bars", Order = 42, GroupName = "5. Export y visual (no run_id)")]
		public int VisualExtendBars { get; set; }

		[NinjaScriptProperty]
		[Range(10, 2000)]
		[Display(Name = "Max Rendered Zones", Order = 43, GroupName = "5. Export y visual (no run_id)",
			Description = "Limita SOLO el dibujo. Nunca elimina zonas del estado interno ni del export.")]
		public int MaxRenderedZones { get; set; }

		#endregion
	}
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private aVolCellPOI2[] cacheaVolCellPOI2;
		public aVolCellPOI2 aVolCellPOI2(AVCP2BucketAnchor bucketAnchor, int timeBucketMinutes, int lookbackSessions, AVCP2ProfileWeighting profileWeighting, AVCP2DetectionSource detectionSource, AVCP2DetectionMethod detectionMethod, double detectionPercentile, double robustZThreshold, int minAbsoluteVolume, int minSessions, int minCellSamples, double exportFloorPercentile, int mergeGapTicks, int minZoneCells, AVCP2InvalidationMode invalidationMode, int maxAgeBars, int maxTouches, string eventLogPath, int opacity, int visualExtendBars, int maxRenderedZones)
		{
			return aVolCellPOI2(Input, bucketAnchor, timeBucketMinutes, lookbackSessions, profileWeighting, detectionSource, detectionMethod, detectionPercentile, robustZThreshold, minAbsoluteVolume, minSessions, minCellSamples, exportFloorPercentile, mergeGapTicks, minZoneCells, invalidationMode, maxAgeBars, maxTouches, eventLogPath, opacity, visualExtendBars, maxRenderedZones);
		}

		public aVolCellPOI2 aVolCellPOI2(ISeries<double> input, AVCP2BucketAnchor bucketAnchor, int timeBucketMinutes, int lookbackSessions, AVCP2ProfileWeighting profileWeighting, AVCP2DetectionSource detectionSource, AVCP2DetectionMethod detectionMethod, double detectionPercentile, double robustZThreshold, int minAbsoluteVolume, int minSessions, int minCellSamples, double exportFloorPercentile, int mergeGapTicks, int minZoneCells, AVCP2InvalidationMode invalidationMode, int maxAgeBars, int maxTouches, string eventLogPath, int opacity, int visualExtendBars, int maxRenderedZones)
		{
			if (cacheaVolCellPOI2 != null)
				for (int idx = 0; idx < cacheaVolCellPOI2.Length; idx++)
					if (cacheaVolCellPOI2[idx] != null && cacheaVolCellPOI2[idx].BucketAnchor == bucketAnchor && cacheaVolCellPOI2[idx].TimeBucketMinutes == timeBucketMinutes && cacheaVolCellPOI2[idx].LookbackSessions == lookbackSessions && cacheaVolCellPOI2[idx].ProfileWeighting == profileWeighting && cacheaVolCellPOI2[idx].DetectionSource == detectionSource && cacheaVolCellPOI2[idx].DetectionMethod == detectionMethod && cacheaVolCellPOI2[idx].DetectionPercentile == detectionPercentile && cacheaVolCellPOI2[idx].RobustZThreshold == robustZThreshold && cacheaVolCellPOI2[idx].MinAbsoluteVolume == minAbsoluteVolume && cacheaVolCellPOI2[idx].MinSessions == minSessions && cacheaVolCellPOI2[idx].MinCellSamples == minCellSamples && cacheaVolCellPOI2[idx].ExportFloorPercentile == exportFloorPercentile && cacheaVolCellPOI2[idx].MergeGapTicks == mergeGapTicks && cacheaVolCellPOI2[idx].MinZoneCells == minZoneCells && cacheaVolCellPOI2[idx].InvalidationMode == invalidationMode && cacheaVolCellPOI2[idx].MaxAgeBars == maxAgeBars && cacheaVolCellPOI2[idx].MaxTouches == maxTouches && cacheaVolCellPOI2[idx].EventLogPath == eventLogPath && cacheaVolCellPOI2[idx].Opacity == opacity && cacheaVolCellPOI2[idx].VisualExtendBars == visualExtendBars && cacheaVolCellPOI2[idx].MaxRenderedZones == maxRenderedZones && cacheaVolCellPOI2[idx].EqualsInput(input))
						return cacheaVolCellPOI2[idx];
			return CacheIndicator<aVolCellPOI2>(new aVolCellPOI2(){ BucketAnchor = bucketAnchor, TimeBucketMinutes = timeBucketMinutes, LookbackSessions = lookbackSessions, ProfileWeighting = profileWeighting, DetectionSource = detectionSource, DetectionMethod = detectionMethod, DetectionPercentile = detectionPercentile, RobustZThreshold = robustZThreshold, MinAbsoluteVolume = minAbsoluteVolume, MinSessions = minSessions, MinCellSamples = minCellSamples, ExportFloorPercentile = exportFloorPercentile, MergeGapTicks = mergeGapTicks, MinZoneCells = minZoneCells, InvalidationMode = invalidationMode, MaxAgeBars = maxAgeBars, MaxTouches = maxTouches, EventLogPath = eventLogPath, Opacity = opacity, VisualExtendBars = visualExtendBars, MaxRenderedZones = maxRenderedZones }, input, ref cacheaVolCellPOI2);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.aVolCellPOI2 aVolCellPOI2(AVCP2BucketAnchor bucketAnchor, int timeBucketMinutes, int lookbackSessions, AVCP2ProfileWeighting profileWeighting, AVCP2DetectionSource detectionSource, AVCP2DetectionMethod detectionMethod, double detectionPercentile, double robustZThreshold, int minAbsoluteVolume, int minSessions, int minCellSamples, double exportFloorPercentile, int mergeGapTicks, int minZoneCells, AVCP2InvalidationMode invalidationMode, int maxAgeBars, int maxTouches, string eventLogPath, int opacity, int visualExtendBars, int maxRenderedZones)
		{
			return indicator.aVolCellPOI2(Input, bucketAnchor, timeBucketMinutes, lookbackSessions, profileWeighting, detectionSource, detectionMethod, detectionPercentile, robustZThreshold, minAbsoluteVolume, minSessions, minCellSamples, exportFloorPercentile, mergeGapTicks, minZoneCells, invalidationMode, maxAgeBars, maxTouches, eventLogPath, opacity, visualExtendBars, maxRenderedZones);
		}

		public Indicators.aVolCellPOI2 aVolCellPOI2(ISeries<double> input , AVCP2BucketAnchor bucketAnchor, int timeBucketMinutes, int lookbackSessions, AVCP2ProfileWeighting profileWeighting, AVCP2DetectionSource detectionSource, AVCP2DetectionMethod detectionMethod, double detectionPercentile, double robustZThreshold, int minAbsoluteVolume, int minSessions, int minCellSamples, double exportFloorPercentile, int mergeGapTicks, int minZoneCells, AVCP2InvalidationMode invalidationMode, int maxAgeBars, int maxTouches, string eventLogPath, int opacity, int visualExtendBars, int maxRenderedZones)
		{
			return indicator.aVolCellPOI2(input, bucketAnchor, timeBucketMinutes, lookbackSessions, profileWeighting, detectionSource, detectionMethod, detectionPercentile, robustZThreshold, minAbsoluteVolume, minSessions, minCellSamples, exportFloorPercentile, mergeGapTicks, minZoneCells, invalidationMode, maxAgeBars, maxTouches, eventLogPath, opacity, visualExtendBars, maxRenderedZones);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.aVolCellPOI2 aVolCellPOI2(AVCP2BucketAnchor bucketAnchor, int timeBucketMinutes, int lookbackSessions, AVCP2ProfileWeighting profileWeighting, AVCP2DetectionSource detectionSource, AVCP2DetectionMethod detectionMethod, double detectionPercentile, double robustZThreshold, int minAbsoluteVolume, int minSessions, int minCellSamples, double exportFloorPercentile, int mergeGapTicks, int minZoneCells, AVCP2InvalidationMode invalidationMode, int maxAgeBars, int maxTouches, string eventLogPath, int opacity, int visualExtendBars, int maxRenderedZones)
		{
			return indicator.aVolCellPOI2(Input, bucketAnchor, timeBucketMinutes, lookbackSessions, profileWeighting, detectionSource, detectionMethod, detectionPercentile, robustZThreshold, minAbsoluteVolume, minSessions, minCellSamples, exportFloorPercentile, mergeGapTicks, minZoneCells, invalidationMode, maxAgeBars, maxTouches, eventLogPath, opacity, visualExtendBars, maxRenderedZones);
		}

		public Indicators.aVolCellPOI2 aVolCellPOI2(ISeries<double> input , AVCP2BucketAnchor bucketAnchor, int timeBucketMinutes, int lookbackSessions, AVCP2ProfileWeighting profileWeighting, AVCP2DetectionSource detectionSource, AVCP2DetectionMethod detectionMethod, double detectionPercentile, double robustZThreshold, int minAbsoluteVolume, int minSessions, int minCellSamples, double exportFloorPercentile, int mergeGapTicks, int minZoneCells, AVCP2InvalidationMode invalidationMode, int maxAgeBars, int maxTouches, string eventLogPath, int opacity, int visualExtendBars, int maxRenderedZones)
		{
			return indicator.aVolCellPOI2(input, bucketAnchor, timeBucketMinutes, lookbackSessions, profileWeighting, detectionSource, detectionMethod, detectionPercentile, robustZThreshold, minAbsoluteVolume, minSessions, minCellSamples, exportFloorPercentile, mergeGapTicks, minZoneCells, invalidationMode, maxAgeBars, maxTouches, eventLogPath, opacity, visualExtendBars, maxRenderedZones);
		}
	}
}

#endregion
