// ============================================================================
// VolTicksPOC2.cs — POC de barras con volumen anómalo (footprint reconstruido)
// v2 de VolTicksVolumetric. NO requiere barras Volumetric: reconstruye el
// footprint desde una subserie de 1 tick agregada con AddDataSeries.
// ============================================================================
//
// NOTA DE DISEÑO (LEER ANTES DE MODIFICAR O TRADUCIR)
// ----------------------------------------------------------------------------
// HIPÓTESIS
//   Cuando una barra tiene volumen anómalo respecto de su baseline reciente,
//   el nivel de precio donde se concentró ese volumen (POC del footprint)
//   puede actuar como punto de interés. La anomalía NO tiene dirección
//   inherente: el indicador no etiqueta soporte/resistencia; eso lo decide
//   EdgeLab con event studies.
//
// CONTRATO (invariantes para la paridad NT8 <-> Python)
//   1. Calculate = OnBarClose, fijo. Clase de repintado: non_repainting.
//      available_at = cierre de la barra creadora; esa barra nunca toca ni
//      invalida su propia zona (anti look-ahead).
//   2. FOOTPRINT RECONSTRUIDO: subserie de 1 tick (BarsInProgress == 1).
//      Cada tick suma su volumen a la celda snap(Close_tick) del footprint
//      pendiente; al cerrar la barra primaria (BarsInProgress == 0) ese
//      pendiente ES el footprint de la barra y se resetea.
//      ADVERTENCIA DECLARADA: un tick con timestamp exactamente igual al
//      cierre de la barra primaria puede procesarse después del cierre y
//      asignarse a la barra siguiente (posible divergencia vs Volumetric
//      nativo). Auto-auditoría: si |suma(footprint) - Volume[0]| > 0.5 se
//      emite FOOTPRINT_MISMATCH (se omite en la primera barra, que puede
//      arrancar con footprint parcial). El footprint definitivo lo arbitra
//      EdgeLab desde el parquet de ticks con la regla [inicio, fin).
//   3. Precios en ticks ENTEROS: snap oficial de NT8 y luego
//      Math.Round(precio/TickSize, MidpointRounding.AwayFromZero).
//   4. BASELINE: promedio simple de Volume[1..AvgPeriod] — EXCLUYE la barra
//      actual (una barra gigante no debe amortiguar su propio ratio).
//      ratio = Volume[0] / baseline. Sin baseline completo => sin detección.
//   5. UMBRAL: cuantil EXACTO sin interpolación (menor valor v de la ventana
//      con count(<= v) >= p*n) sobre los últimos RatioWindowBars ratios.
//      El ratio actual se compara ANTES de incorporarse a la ventana.
//      percentil_empírico(x) = count(<= x)/n. Sin P²: los estimadores
//      streaming aproximados dependen del orden de llegada y son imprecisos
//      en colas extremas; quedan prohibidos para indicadores con paridad.
//   6. POC: celda del footprint con mayor volumen; en empate gana el TICK MÁS
//      BAJO (regla determinista, independiente del orden de iteración).
//      Si el footprint está vacío NO hay zona ni fallback al midpoint:
//      se emite ERROR y la barra queda sin detección.
//   7. LIMITACIÓN DECLARADA: el ratio contra baseline móvil NO elimina la
//      estacionalidad intradiaria (esperar sesgo de detecciones en aperturas).
//      Upgrade de research: perfil por franja horaria estilo aVolCellPOI2.
//   8. Ciclo de vida (aprox. a nivel barra; resolución definitiva con ticks
//      en EdgeLab): TOUCH = [Low,High] interseca la zona. FirstTouch invalida
//      al primer toque. CloseThrough: lado de referencia = lado del close al
//      crearse (si cierra dentro, lo fija el primer close externo); invalida
//      el primer close del lado opuesto. MaxTouches>0 invalida al enésimo
//      toque. MaxAgeBars expira. Identidad analítica de una zona =
//      (created_at, poc_tick), nunca el tag de dibujo.
//
// PARAMETRIZACIÓN PARA FUERZA BRUTA EN VECTORBT
//   Grupo 1 - SEMÁNTICOS (run_id; cambiarlos = recomputar): AvgPeriod,
//     RatioWindowBars. (La política de asignación de ticks y el desempate de
//     POC son contrato fijo, no parámetros.)
//   Grupo 2 - SELECCIÓN (barrible OFFLINE vía OBS): DetectionPercentile,
//     MinRatioSamples, ExportFloorPercentile. Cada barra con percentil >=
//     ExportFloorPercentile emite OBS con ratio, percentil, poc_tick,
//     poc_share continuos => cambiar el corte en vectorbt = filtrar filas.
//   Grupo 3 - GEOMETRÍA: PriceMarkTicks (alto de zona alrededor del POC).
//   Grupo 4 - CICLO DE VIDA: InvalidationMode, MaxAgeBars, MaxTouches.
//   Grupo 5 - VISUALES (fuera del run_id): Opacity, VisualExtendBars,
//     MaxRenderedZones (limita SOLO el dibujo, nunca el estado ni el export).
//   Grillas iniciales sugeridas: AvgPeriod {100,200,400};
//     DetectionPercentile {99.0,99.5,99.75,99.9}; resto fijo en la 1ª pasada.
//
// REQUISITOS
//   - Datos históricos de TICK descargados en NT8 para el rango analizado
//     (la subserie de 1 tick no requiere Tick Replay, pero sin tick data no
//     hay footprint y el indicador emite ERROR en vez de inventar niveles).
//   - IsSuspendedWhileInactive = false (reproducibilidad).
//   - No usar series continuas con saltos de rollover.
//   - La región "NinjaScript generated code" se omite: NT8 la regenera.
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
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// Enums a scope GLOBAL (NT8 genera wrappers en MarketAnalyzerColumns/
// Strategies que los referencian por nombre simple; en el namespace Indicators daban CS0246).
public enum VTP2InvalidationMode { None = 0, FirstTouch = 1, CloseThrough = 2 }

namespace NinjaTrader.NinjaScript.Indicators
{
	public class VolTicksPOC2 : Indicator
	{
		private const int HeatSteps = 9;

		// ---------- footprint reconstruido ----------
		private Dictionary<long, double> pendingFootprint;
		private double pendingTickVolume;
		private bool tickSeriesWarned;

		// ---------- baseline y ventana de ratios ----------
		private Queue<double> baselineWindow;  // volúmenes de barras ANTERIORES
		private double baselineSum;
		private Queue<double> ratioWindow;     // ratios de barras anteriores

		// ---------- zonas ----------
		private readonly List<ActiveZone> activeZones = new List<ActiveZone>();
		private readonly Queue<string> renderedTags = new Queue<string>();
		private long zoneCounter;

		// ---------- infra ----------
		private StreamWriter writer;
		private bool writerFailed;
		private bool configImposible;
		private bool sinDatosTick;
		private long eventSeq;
		private Brush[] heatBrushes;

		private class ActiveZone
		{
			public long Id;
			public int CreatedBar;
			public DateTime CreatedTime;
			public long PocTick;
			public double LowerPrice, UpperPrice;
			public double Pct, Ratio, PocShare;
			public int TouchCount, RefSide;
			public string Tag;
		}

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "POC del footprint (reconstruido desde ticks) en barras con volumen anómalo. v2, contrato EdgeLab.";
				Name = "VolTicksPOC2";
				Calculate = Calculate.OnBarClose;      // CONTRATO: no cambiar
				IsOverlay = true;
				DisplayInDataBox = false;
				DrawOnPricePanel = true;
				IsSuspendedWhileInactive = false;      // CONTRATO: reproducibilidad

				// Grupo 1: semánticos
				AvgPeriod        = 200;
				RatioWindowBars  = 2000;
				// Grupo 2: selección
				DetectionPercentile   = 99.5;
				MinRatioSamples       = 500;
				ExportFloorPercentile = 95.0;
				// Grupo 3: geometría
				PriceMarkTicks   = 1;
				// Grupo 4: ciclo de vida
				InvalidationMode = VTP2InvalidationMode.CloseThrough;
				MaxAgeBars       = 2000;
				MaxTouches       = 0;
				// Grupo 5: export y visual
				EventLogPath     = "";
				Opacity          = 20;
				VisualExtendBars = 500;
				MaxRenderedZones = 250;
			}
			else if (State == State.Configure)
			{
				AddDataSeries(BarsPeriodType.Tick, 1); // subserie para reconstruir el footprint
			}
			else if (State == State.DataLoaded)
			{
				pendingFootprint = new Dictionary<long, double>();
				pendingTickVolume = 0;
				tickSeriesWarned = false;
				baselineWindow = new Queue<double>();
				baselineSum = 0;
				ratioWindow = new Queue<double>();
				zoneCounter = 0;
				eventSeq = 0;
				writerFailed = false;
				heatBrushes = BuildHeatBrushes();

				// `ratioWindow` es una ventana RODANTE acotada a RatioWindowBars: su
				// Count nunca supera ese tope. Si MinRatioSamples es mayor, el gate de
				// deteccion (ratioWindow.Count >= MinRatioSamples) NO PUEDE abrir nunca
				// y el indicador no marca NADA, sin error y sin aviso, para siempre.
				// Se detecta y se GRITA en vez de resolverlo en silencio: ni clamp ni
				// fallback. Un config imposible tiene que ser visible, no producir un
				// 'no hay senales' indistinguible de un resultado real.
				// (Incidente 2026-07-26: un chart con RatioWindowBars=200 y
				//  MinRatioSamples=500 no marcaba nada y no habia forma de saber por que.)
				configImposible = MinRatioSamples > RatioWindowBars;
				if (configImposible)
				{
					string msg = string.Format(CultureInfo.InvariantCulture,
						"VolTicksPOC2: CONFIG IMPOSIBLE. MinRatioSamples={0} > RatioWindowBars={1}. "
						+ "La ventana de ratios se acota en {1}, asi que el gate de deteccion nunca "
						+ "abre y NO se marcara ninguna zona. Subir RatioWindowBars a >= {0}, o bajar "
						+ "MinRatioSamples a <= {1}.", MinRatioSamples, RatioWindowBars);
					Print(msg);
					Draw.TextFixed(this, "VTP2_CONFIG", msg, TextPosition.TopLeft);
				}
			}
			else if (State == State.Terminated)
			{
				try { if (writer != null) { writer.Flush(); writer.Close(); writer = null; } }
				catch { }
			}
		}

		protected override void OnBarUpdate()
		{
			// ---------- subserie de 1 tick: acumular footprint pendiente ----------
			if (BarsInProgress == 1)
			{
				long t = SnapToTick(Close[0]);
				double v = Volume[0];
				double cur;
				if (pendingFootprint.TryGetValue(t, out cur)) pendingFootprint[t] = cur + v;
				else pendingFootprint[t] = v;
				pendingTickVolume += v;
				return;
			}
			if (BarsInProgress != 0) return;

			// ESTADO VISIBLE. Mientras no se puede detectar, el indicador lo DICE y
			// muestra cuanto falta. Un grafico vacio es indistinguible de 'no hubo
			// senales', y esa ambiguedad ya costo una sesion de diagnostico
			// (incidente 2026-07-26). El warmup es avg_period + min_ratio_samples
			// barras: hasta ahi, cero detecciones garantizadas.
			if (sinDatosTick)
				Draw.TextFixed(this, "VTP2_CONFIG",
					"VolTicksPOC2: SIN TICK DATA HISTORICA para este instrumento.\n"
					+ "El footprint se reconstruye desde una subserie de 1 tick; sin ella no\n"
					+ "hay POC y NO se puede detectar nada. Descargar tick data historica\n"
					+ "(Tools > Historical Data > Load) para el instrumento y el rango.",
					TextPosition.TopLeft);
			else if (!configImposible)
			{
				int faltanBase  = Math.Max(0, AvgPeriod - baselineWindow.Count);
				int faltanRatio = Math.Max(0, MinRatioSamples - ratioWindow.Count);
				if (faltanBase > 0 || faltanRatio > 0)
					Draw.TextFixed(this, "VTP2_CONFIG", string.Format(CultureInfo.InvariantCulture,
						"VolTicksPOC2: EN WARMUP, todavia no puede detectar.\nbaseline {0}/{1}"
						+ " | ratios {2}/{3}\nfaltan ~{4} barras de {5} ticks. Cargar mas dias.",
						baselineWindow.Count, AvgPeriod, ratioWindow.Count, MinRatioSamples,
						Math.Max(faltanBase, faltanRatio), BarsPeriod.Value),
						TextPosition.TopLeft);
				else if (zoneCounter == 0)
					Draw.TextFixed(this, "VTP2_CONFIG", string.Format(CultureInfo.InvariantCulture,
						"VolTicksPOC2: warmup COMPLETO, buscando. Percentil {0} => ~{1} de cada"
						+ " 1000 barras califica; puede tardar cientos de barras en aparecer la primera.",
						DetectionPercentile, (int)Math.Round((100.0 - DetectionPercentile) * 10)),
						TextPosition.TopLeft);
				else
					RemoveDrawObject("VTP2_CONFIG");
			}

			// ---------- barra primaria: tomar y resetear el footprint SIEMPRE ----------
			Dictionary<long, double> fp = pendingFootprint;
			double fpVol = pendingTickVolume;
			pendingFootprint = new Dictionary<long, double>();
			pendingTickVolume = 0;

			if (CurrentBars.Length < 2 || CurrentBars[1] < 0)
			{
				if (!tickSeriesWarned)
				{
					tickSeriesWarned = true;
					sinDatosTick = true;
					EmitError("tick_series", "Sin datos históricos de tick: no se puede reconstruir el footprint. Sin detecciones.");
				}
				UpdateBaselineWindows(); // mantener ventanas coherentes igualmente
				return;
			}

			// auto-auditoría del footprint (se omite en la primera barra: puede ser parcial)
			if (CurrentBar > 0 && fp.Count > 0 && Math.Abs(fpVol - Volume[0]) > 0.5)
				EmitEvent("FOOTPRINT_MISMATCH", 0, fpVol, 0, Volume[0], fpVol, 0, 0, 0,
					ratioWindow.Count, 0, 0, "reconstructed_vs_bar_volume");

			// 1) ciclo de vida ANTES de crear zonas nuevas (anti look-ahead)
			UpdateZoneLifecycle();

			// 2) ratio contra baseline que EXCLUYE la barra actual
			double ratio = double.NaN, baseline = 0;
			if (baselineWindow.Count >= AvgPeriod)
			{
				baseline = baselineSum / AvgPeriod;
				if (baseline > 0) ratio = Volume[0] / baseline;
			}

			// 3) detección: comparar ANTES de incorporar el ratio a la ventana
			if (!double.IsNaN(ratio) && ratioWindow.Count >= MinRatioSamples)
			{
				double[] sorted = ratioWindow.ToArray();
				Array.Sort(sorted);
				double threshold = QuantileNoInterp(sorted, DetectionPercentile / 100.0);
				double pct = EmpiricalPct(sorted, ratio);

				// POC del footprint reconstruido (empate => tick más bajo)
				long pocTick = long.MaxValue;
				double pocVol = -1.0;
				foreach (KeyValuePair<long, double> kv in fp)
				{
					if (kv.Value > pocVol || (kv.Value == pocVol && kv.Key < pocTick))
					{
						pocVol = kv.Value;
						pocTick = kv.Key;
					}
				}
				bool pocFound = pocVol > 0;
				double pocShare = (pocFound && fpVol > 0) ? pocVol / fpVol : 0;

				if (pct * 100.0 >= ExportFloorPercentile)
				{
					if (pocFound)
						EmitEvent("OBS", pocTick, ratio, baseline, Volume[0], fpVol, pocVol,
							pocShare, threshold, ratioWindow.Count, 0, 0,
							pct.ToString("0.######", CultureInfo.InvariantCulture));
					else
						EmitError("empty_footprint", "Barra sin footprint reconstruido (¿hueco de tick data?). Sin POC ni zona.");
				}

				if (pct >= DetectionPercentile / 100.0 && pocFound)
					CreateZone(pocTick, ratio, pct, pocShare, threshold);
			}

			// 4) actualizar ventanas DESPUÉS de comparar
			if (!double.IsNaN(ratio))
			{
				ratioWindow.Enqueue(ratio);
				while (ratioWindow.Count > RatioWindowBars) ratioWindow.Dequeue();
			}
			UpdateBaselineWindows();
		}

		private void UpdateBaselineWindows()
		{
			baselineWindow.Enqueue(Volume[0]);
			baselineSum += Volume[0];
			while (baselineWindow.Count > AvgPeriod)
				baselineSum -= baselineWindow.Dequeue();
		}

		// ---------------- estadística (exacta, sin interpolación) ----------------

		// menor valor v con count(<= v) >= p * n
		private static double QuantileNoInterp(double[] sorted, double p)
		{
			int n = sorted.Length;
			int idx = (int)Math.Ceiling(p * n) - 1;
			if (idx < 0) idx = 0;
			if (idx > n - 1) idx = n - 1;
			return sorted[idx];
		}

		// count(<= x) / n
		private static double EmpiricalPct(double[] sorted, double x)
		{
			int lo = 0, hi = sorted.Length - 1, idx = -1;
			while (lo <= hi)
			{
				int mid = (lo + hi) / 2;
				if (sorted[mid] <= x) { idx = mid; lo = mid + 1; } else hi = mid - 1;
			}
			return (idx + 1) / (double)sorted.Length;
		}

		// ---------------- zonas ----------------

		private void CreateZone(long pocTick, double ratio, double pct, double pocShare, double threshold)
		{
			double pocPrice = Instrument.MasterInstrument.RoundToTickSize(pocTick * TickSize);
			double half = Math.Max(1, PriceMarkTicks) * TickSize / 2.0;

			ActiveZone z = new ActiveZone
			{
				Id = ++zoneCounter,
				CreatedBar = CurrentBar,
				CreatedTime = Time[0],
				PocTick = pocTick,
				LowerPrice = pocPrice - half,
				UpperPrice = pocPrice + half,
				Pct = pct, Ratio = ratio, PocShare = pocShare,
				TouchCount = 0
			};
			z.RefSide = Close[0] > z.UpperPrice ? 1 : (Close[0] < z.LowerPrice ? -1 : 0);
			z.Tag = "VTP2_" + z.Id;

			activeZones.Add(z);
			EmitEvent("ZONE_CREATED", pocTick, ratio, 0, Volume[0], 0, 0, pocShare, threshold,
				ratioWindow.Count, z.Id, 0, pct.ToString("0.######", CultureInfo.InvariantCulture));
			DrawZone(z);
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
					EmitEvent("ZONE_TOUCHED", z.PocTick, 0, 0, 0, 0, 0, 0, 0, 0, z.Id, z.TouchCount, "");
				}

				string reason = null;
				if (InvalidationMode == VTP2InvalidationMode.FirstTouch && touched)
					reason = "first_touch";
				else if (InvalidationMode == VTP2InvalidationMode.CloseThrough)
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
					EmitEvent("ZONE_INVALIDATED", z.PocTick, 0, 0, 0, 0, 0, 0, 0, 0, z.Id, z.TouchCount, reason);
					// NO se borra el dibujo. Antes se borraba al invalidar/expirar, asi
					// que sobre datos historicos -donde para el final ya murieron casi
					// todas- el grafico quedaba con las zonas VIVAS en la ultima barra:
					// tipicamente una, o ninguna. Parecia que el indicador no detectaba
					// (incidente 2026-07-26: MNQ mostro 1 zona, MES 0, mientras el mismo
					// kernel sobre 6E detectaba 454). El dibujo es SOLO dibujo: el estado
					// y los eventos exportados no cambian, y MaxRenderedZones sigue
					// acotando cuantos rectangulos viven en el chart.
					activeZones.RemoveAt(i);
				}
				else if (CurrentBar - z.CreatedBar >= MaxAgeBars)
				{
					EmitEvent("ZONE_EXPIRED", z.PocTick, 0, 0, 0, 0, 0, 0, 0, 0, z.Id, z.TouchCount, "max_age");
					// NO se borra el dibujo. Antes se borraba al invalidar/expirar, asi
					// que sobre datos historicos -donde para el final ya murieron casi
					// todas- el grafico quedaba con las zonas VIVAS en la ultima barra:
					// tipicamente una, o ninguna. Parecia que el indicador no detectaba
					// (incidente 2026-07-26: MNQ mostro 1 zona, MES 0, mientras el mismo
					// kernel sobre 6E detectaba 454). El dibujo es SOLO dibujo: el estado
					// y los eventos exportados no cambian, y MaxRenderedZones sigue
					// acotando cuantos rectangulos viven en el chart.
					activeZones.RemoveAt(i);
				}
			}
		}

		// ---------------- salida analítica de solo lectura ----------------

		public int ActiveZoneCount { get { return activeZones.Count; } }

		// ---------------- render (nunca fuente de verdad) ----------------

		private void DrawZone(ActiveZone z)
		{
			double cut = DetectionPercentile / 100.0;
			double t = (z.Pct - cut) / Math.Max(1e-9, 1.0 - cut);
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

		private long SnapToTick(double price)
		{
			double snapped = Instrument.MasterInstrument.RoundToTickSize(price);
			return (long)Math.Round(snapped / TickSize, MidpointRounding.AwayFromZero);
		}

		private void EmitError(string code, string message)
		{
			Print(Name + " ERROR [" + code + "] bar=" + CurrentBar + ": " + message);
			EmitEvent("ERROR", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, code);
		}

		private void EmitEvent(string type, long pocTick, double ratio, double baseline,
			double barVolume, double tickVolume, double pocVolume, double pocShare,
			double threshold, int windowCount, long zoneId, int touchCount, string reason)
		{
			if (EventLogPath == null || EventLogPath.Length == 0 || writerFailed) return;
			try
			{
				if (writer == null)
				{
					writer = new StreamWriter(EventLogPath, false);
					writer.WriteLine("# meta,indicator=VolTicksPOC2,version=2.1,instrument="
						+ Instrument.FullName + ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
						+ ",avg_period=" + AvgPeriod + ",ratio_window=" + RatioWindowBars
						+ ",percentile=" + DetectionPercentile.ToString(CultureInfo.InvariantCulture)
						+ ",min_samples=" + MinRatioSamples
						+ ",export_floor=" + ExportFloorPercentile.ToString(CultureInfo.InvariantCulture)
						+ ",poc_tiebreak=lowest_tick,footprint=reconstructed_1tick_subseries");
					writer.WriteLine("event_seq,event_type,bar_index,bar_close_time,poc_tick,ratio,"
						+ "baseline,bar_volume,tick_volume,poc_volume,poc_share,threshold,"
						+ "window_count,zone_id,touch_count,reason");
				}
				eventSeq++;
				writer.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}",
					eventSeq, type, CurrentBar,
					Time[0].ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					pocTick,
					ratio.ToString("0.######", CultureInfo.InvariantCulture),
					baseline.ToString("0.####", CultureInfo.InvariantCulture),
					barVolume, tickVolume, pocVolume,
					pocShare.ToString("0.######", CultureInfo.InvariantCulture),
					threshold.ToString("0.######", CultureInfo.InvariantCulture),
					windowCount, zoneId, touchCount, reason));
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
		[Range(20, 2000)]
		[Display(Name = "Avg Period (baseline)", Order = 1, GroupName = "1. Semántica (run_id)",
			Description = "Promedio de volumen de las N barras ANTERIORES (excluye la actual).")]
		public int AvgPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(100, 20000)]
		[Display(Name = "Ratio Window (barras)", Order = 2, GroupName = "1. Semántica (run_id)",
			Description = "Ventana del cuantil exacto sobre los ratios (reemplaza al estimador P² de la v1).")]
		public int RatioWindowBars { get; set; }

		// -------- Grupo 2: selección (barrible offline vía OBS) --------
		[NinjaScriptProperty]
		[Range(90.0, 99.99)]
		[Display(Name = "Detection Percentile", Order = 10, GroupName = "2. Selección (barrible offline)")]
		public double DetectionPercentile { get; set; }

		[NinjaScriptProperty]
		[Range(50, 20000)]
		[Display(Name = "Min Ratio Samples", Order = 11, GroupName = "2. Selección (barrible offline)",
			Description = "Ratios mínimos en la ventana antes de detectar (recordar ~10/(1-p)).")]
		public int MinRatioSamples { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 99.99)]
		[Display(Name = "Export Floor Percentile", Order = 12, GroupName = "2. Selección (barrible offline)",
			Description = "Exporta OBS para toda barra con percentil >= piso. Clave para barrer el corte en vectorbt sin recomputar.")]
		public double ExportFloorPercentile { get; set; }

		// -------- Grupo 3: geometría --------
		[NinjaScriptProperty]
		[Range(1, 50)]
		[Display(Name = "Price Mark Ticks (alto)", Order = 20, GroupName = "3. Geometría",
			Description = "Alto de la zona en ticks alrededor del POC.")]
		public int PriceMarkTicks { get; set; }

		// -------- Grupo 4: ciclo de vida --------
		[NinjaScriptProperty]
		[Display(Name = "Invalidation Mode", Order = 30, GroupName = "4. Ciclo de vida")]
		public VTP2InvalidationMode InvalidationMode { get; set; }

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
			Description = "Vacío = sin export. Ej: C:\\ProyectosQuant\\EdgeLab\\exports\\vtp2_NQ.csv")]
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
