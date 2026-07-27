// AACloseOpenDiffs.cs - v1.2 - Marca diferencias close-to-open entre velas M1 con heatmap.
// v1.2 (2026-07-26): cada fila del logger de research lleva ind_version (Decision B).
// v1.1 (2026-07-26): umbral MinDiffTicks comparado en ENTEROS de tick.
//   v1.0 descartaba el 47.5% de los gaps de 1 tick por el bug de 1 ULP del feed.
// Cuanto MAS zonas se superpongan en precio + tiempo, mas roja se pone el area.
// Usa sub-serie M1 para que funcione en CUALQUIER chart primario, incluido ticks (p.ej. 50t).
//
// FIX visual:
//  - Las zonas se anclan por TIEMPO ABSOLUTO (DateTime), no por barsAgo. Asi inician
//    EXACTAMENTE donde ocurrio el gap, sin importar la resolucion del primario.
//  - El inicio del gap es Times[1][1] (boundary close[prev] -> open[curr]).
//  - La ventana de superposicion se mide en barras M1.
//
// Capa opcional (checkbox "Filtrar por percentil"):
//  - Solo dibuja gaps cuyo tamano supere el percentil PercentilMin de los
//    ultimos VentanaPercentil gaps (default percentil 90 = top 10%).
//  - La persistencia SQLite y la ventana de percentil incluyen TODOS los gaps
//    (>= MinDiffTicks); el filtro afecta solo el dibujo y el heatmap.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.Core.FloatingPoint;
using System.Data.SQLite;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class AACloseOpenDiffs : Indicator
    {
        private sealed class Diff
        {
            public DateTime StartTime;     // instante del gap (boundary close[prev] -> open[curr])
            public DateTime EndTime;       // hasta donde se extiende visualmente la zona
            public double   TopPrice;
            public double   BottomPrice;
            public int      StartM1Bar;    // indice de barra M1 en la que nacio
            public int      ExpiresM1Bar;  // ventana de superposicion temporal (en barras M1)
            public int      OverlapCount;   // cuantas otras zonas se solaparon con esta hasta ahora
            public string   TagRect;
        }

        private readonly List<Diff> diffs = new List<Diff>();
        private int idCounter;

        // === Logger de investigacion: exporta cada zona AL NACER (point-in-time). ===
        // Captura overlap_at_birth = confluencia conocida al nacer (sin lookahead),
        // el analogo de vol_rate/pasos del logger hft_zones del ecosistema quantlab.
        // La persistencia SQLite de mas abajo NO guarda el overlap (la senal real);
        // este CSV si. Requiere FiltrarPorPercentil = false para exportar todas.
        private sealed class ZoneLogRecord
        {
            public long   StartMs, EndMs;
            public double Upper, Lower, DiffTicks;
            public int    Direction, OverlapAtBirth, M1Bar;
        }
        // Version del indicador. UNA sola fuente de verdad: la escriben el meta
        // del canal de paridad y cada fila del logger de research (Decision B).
        private const string IND_VERSION = "1.2";

        private readonly List<ZoneLogRecord> zoneLog = new List<ZoneLogRecord>();
        private string csvLogPath = @"D:\A  Trading\loggers\AACloseOpenDiffs.csv";
        
        // === Export de PARIDAD (separado del logger de research de arriba) ===
        // El logger de research MERGEA con lo previo y tiene ruta fija: sirve para
        // acumular, no para comparar. La paridad necesita UNA corrida limpia y un
        // formato estable, asi que va por su propio canal y no toca al otro.
        private System.IO.StreamWriter parityWriter;
        private string parityResolvedPath = "";
        private int paritySeq;

        // === Expansiones (voids): tramos direccionales con 0 zonas encima ===
        // ZigZag de umbral fijo (ExpansionReversalTicks) sobre la sub-serie M1.
        private bool     expInit;
        private int      expTrend;   // +1 leg alcista en curso, -1 bajista, 0 init
        private int      pivBar;     // barra M1 del inicio del tramo (pivote)
        private double   pivPrice;
        private DateTime pivTime;
        private int      hiBar, loBar;
        private double   hiPrice, loPrice;
        private DateTime hiTime, loTime;
        private readonly List<string> expansionTags = new List<string>();
        private int expCounter;

        private static readonly Brush expArea   = FrozenBrush(Color.FromRgb(80, 140, 235));
        private static readonly Brush expOutline = FrozenBrush(Color.FromRgb(33, 110, 220));
        private static Brush FrozenBrush(Color c) { var b = new SolidColorBrush(c); b.Freeze(); return b; }

        // Ventana rodante con el tamano (en puntos) de los ultimos gaps detectados.
        private readonly List<double> gapWindow = new List<double>();
        private const int MinSamplesPercentil = 10; // minimo de muestras antes de aplicar el filtro

        // Heatmap: gradiente de gris claro a rojo intenso segun overlap count
        private static readonly Color[] heatColors = {
            Color.FromRgb(220, 220, 220), //  1: gris claro
            Color.FromRgb(230, 220, 120), //  2: gris-amarillo
            Color.FromRgb(255, 220,  80), //  3: amarillo
            Color.FromRgb(255, 180,  60), //  4: naranja claro
            Color.FromRgb(255, 130,  40), //  5: naranja
            Color.FromRgb(255,  80,  30), //  6: naranja-rojo
            Color.FromRgb(220,  20,  20), //  7+: rojo
        };

        private static readonly Dictionary<int, Brush> brushCache = new Dictionary<int, Brush>();

        private Brush GetHeatBrush(int overlapCount)
        {
            int idx = Math.Min(Math.Max(0, overlapCount - 1), heatColors.Length - 1);
            if (!brushCache.TryGetValue(idx, out Brush b))
            {
                b = new SolidColorBrush(heatColors[idx]);
                b.Freeze();
                brushCache[idx] = b;
            }
            return b;
        }

        private int GetOpacityScaled(int overlapCount)
        {
            // Opacidad sube con overlap pero limitada
            int op = BaseOpacity + (overlapCount - 1) * 6;
            return Math.Max(1, Math.Min(95, op));
        }

        // Precio -> indice ENTERO de tick. Espejo exacto de snap_to_tick (Python) y
        // de PriceToTick en los otros .cs del puente: redondeo AwayFromZero, NUNCA
        // floor. El floor es lo que rompe cuando el feed entrega el precio 1 ULP por
        // debajo de la grilla. Ver docs/nt8_indicator_parity_contract.md §5.
        private long PriceToTick(double price)
        {
            return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
        }

        // Percentil con interpolacion lineal (pct en 0..100) sobre una copia ordenada.
        private double Percentile(List<double> data, double pct)
        {
            if (data == null || data.Count == 0) return 0.0;
            List<double> sorted = new List<double>(data);
            sorted.Sort();
            if (pct <= 0)   return sorted[0];
            if (pct >= 100) return sorted[sorted.Count - 1];

            double rank = (pct / 100.0) * (sorted.Count - 1);
            int lo = (int)Math.Floor(rank);
            int hi = (int)Math.Ceiling(rank);
            if (lo == hi) return sorted[lo];
            double frac = rank - lo;
            return sorted[lo] + frac * (sorted[hi] - sorted[lo]);
        }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description              = "Diferencias close-open M1 con heatmap (anclaje por tiempo, sirve en charts de ticks). Mas superposiciones = mas rojo. Filtro opcional por percentil de tamano.";
                Name                     = "AACloseOpenDiffs";
                Calculate                = Calculate.OnBarClose;
                IsOverlay                = true;
                DisplayInDataBox         = true;
                DrawOnPricePanel         = true;
                PaintPriceMarkers        = true;
                IsSuspendedWhileInactive = true;

                MinDiffTicks         = 1;
                EventLogPath         = "";
                ExtendBars           = 50;   // en BARRAS M1 (~minutos): define vida + ventana de overlap
                BaseOpacity          = 25;
                MaxRectangles        = 5000;

                FiltrarPorPercentil  = false; // activar tildando la casilla
                PercentilMin         = 90;    // 90 = solo top 10% mas grande. 10 = descarta el 10% mas chico.
                VentanaPercentil     = 100;   // los ultimos N gaps

                DetectarExpansiones    = false; // activar tildando la casilla
                ExpansionMinTicks      = 80;    // alto minimo del tramo (en ticks)
                ExpansionMinBarsM1     = 10;    // ancho minimo del tramo (en barras M1 ~ minutos)
                ExpansionReversalTicks = 40;    // retroceso que cierra/confirma un tramo (ZigZag)
                ExpansionOpacity       = 18;    // opacidad del relleno del rectangulo
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Minute, 1);
            }
            else if (State == State.DataLoaded)
            {
                diffs.Clear();
                gapWindow.Clear();
                idCounter = 0;

                expInit = false;
                expTrend = 0;
                expCounter = 0;
                expansionTags.Clear();

                zoneLog.Clear();
                paritySeq = 0;
                if (!string.IsNullOrEmpty(EventLogPath))
                {
                	try
                	{
                		string d = System.IO.Path.GetDirectoryName(EventLogPath);
                		if (!string.IsNullOrEmpty(d) && !System.IO.Directory.Exists(d))
                			System.IO.Directory.CreateDirectory(d);
                		string bn = System.IO.Path.Combine(d ?? "",
                			System.IO.Path.GetFileNameWithoutExtension(EventLogPath));
                		string ex = System.IO.Path.GetExtension(EventLogPath);
                		if (string.IsNullOrEmpty(ex)) ex = ".csv";
                		parityResolvedPath = bn + ex;
                		for (int k = 2; System.IO.File.Exists(parityResolvedPath) && k < 1000; k++)
                			parityResolvedPath = bn + "_" + k.ToString() + ex;
                		parityWriter = new System.IO.StreamWriter(parityResolvedPath, false,
                			new System.Text.UTF8Encoding(false));
                		parityWriter.AutoFlush = true;
                		parityWriter.WriteLine("# meta indicator=AACloseOpenDiffs,version=" + IND_VERSION + ","
                			+ "subseries=minute_1_always,anchor=boundary_prev_m1_close,"
                			+ "overlap=point_in_time_at_birth,bar_spec_independent=true,instrument="
                			+ Instrument.MasterInstrument.Name + ",tick_size="
                			+ TickSize.ToString(System.Globalization.CultureInfo.InvariantCulture)
                			+ ",min_diff_ticks=" + MinDiffTicks + ",extend_bars=" + ExtendBars);
                		parityWriter.WriteLine("event_seq,event_type,ts,unix_ms,zone_id,start_ms,"
                			+ "end_ms,upper,lower,diff_ticks,direction,overlap_at_birth,m1_bar");
                		Print("[AACloseOpenDiffs] paridad -> " + parityResolvedPath);
                	}
                	catch (Exception ex2) { Print("[AACloseOpenDiffs] no se pudo abrir el CSV de paridad: " + ex2.Message); }
                }
            }
            else if (State == State.Realtime)
            {
                FlushZoneLogCsv();   // primer volcado tras procesar todo el historico
                Print("[AACloseOpenDiffs] logger CSV: " + zoneLog.Count
                    + " zonas escritas -> " + csvLogPath);
            }
            else if (State == State.Terminated)
            {
                FlushZoneLogCsv();   // volcado final al quitar el indicador / cerrar el chart
                if (parityWriter != null) { parityWriter.Flush(); parityWriter.Close(); parityWriter = null; }
                if (zoneLog.Count > 0)
                    Print("[AACloseOpenDiffs] logger CSV (final): " + zoneLog.Count
                        + " zonas -> " + csvLogPath);
            }
        }

        protected override void OnBarUpdate()
        {
            // Solo procesamos la sub-serie M1 (index 1). El primario puede ser 25t, 50t, etc.
            if (BarsInProgress != 1) return;
            if (CurrentBars[1] < 1) return;

            // Capa opcional: deteccion de expansiones (tramos direccionales sin zonas encima).
            if (DetectarExpansiones) DetectarExpansion();

            double closePrev = Closes[1][1];
            double openCurr  = Opens[1][0];

            // v1.1 (barrido ULP 2026-07-26, autorizado por Nico): el umbral de
            // tamano se compara en ENTEROS de tick, nunca en points.
            //
            // El defecto que corrige: `gapPts < MinDiffTicks * TickSize` descartaba
            // el 47.5% de los gaps de EXACTAMENTE 1 tick. NT8 entrega el precio como
            // el double del decimal parseado del feed, que en el 24.3% de los
            // niveles de 6E cae 1 ULP por DEBAJO de la grilla; al restar dos precios
            // consecutivos la diferencia queda apenas por debajo de 1*TickSize y el
            // `<` la mata. Medido contra el oraculo: 43.5% de perdida observada.
            //
            // gapPts sobrevive solo para I/O (dibujo, percentil visual y el logger
            // de research). La DECISION usa gapTicks.
            long gapTicks = Math.Abs(PriceToTick(closePrev) - PriceToTick(openCurr));
            double gapPts = Math.Abs(closePrev - openCurr);
            if (gapTicks < MinDiffTicks) return;

            // --- Capa opcional: filtro por percentil de tamano ---
            // El umbral se calcula sobre los gaps PREVIOS (la ventana antes de
            // agregar el actual). Solo se dibuja si gapPts supera ese percentil.
            bool dibujar = true;
            if (FiltrarPorPercentil && gapWindow.Count >= MinSamplesPercentil)
            {
                double thr = Percentile(gapWindow, PercentilMin);
                if (gapPts <= thr) dibujar = false;
            }

            // La ventana incluye TODOS los gaps (>= MinDiffTicks), se dibujen o no.
            gapWindow.Add(gapPts);
            if (gapWindow.Count > Math.Max(5, VentanaPercentil))
                gapWindow.RemoveAt(0);

            double top = Math.Max(closePrev, openCurr);
            double bot = Math.Min(closePrev, openCurr);

            // El gap se forma en el boundary entre el cierre de la M1 previa y la
            // apertura de la M1 actual => Times[1][1].
            DateTime startTime = Times[1][1];

            // Persistimos SIEMPRE (la data de research no se sesga por el filtro visual).
            long unixMs = new DateTimeOffset(startTime.ToUniversalTime()).ToUnixTimeMilliseconds();
            PersistDiff(Instrument.FullName, unixMs, top, bot, gapPts);

            if (!dibujar) return;

            DateTime endTime = startTime.AddMinutes(ExtendBars);

            idCounter++;
            Diff nueva = new Diff
            {
                StartTime    = startTime,
                EndTime      = endTime,
                TopPrice     = top,
                BottomPrice  = bot,
                StartM1Bar   = CurrentBars[1],
                ExpiresM1Bar = CurrentBars[1] + ExtendBars,
                OverlapCount = 1,
                TagRect      = "AACOD_" + idCounter
            };

            ProcesarSuperposiciones(nueva);
            diffs.Add(nueva);

            DibujarDiff(nueva);

            // Logger de investigacion (point-in-time): overlap AL NACER, sin lookahead.
            // nueva.OverlapCount aca cuenta solo zonas PREVIAS que solapan (las futuras
            // la incrementan despues, pero ese valor futuro no se registra).
            int gapDir = openCurr > closePrev ? 1 : -1;   // +1 gap alcista, -1 bajista
            long endMs = new DateTimeOffset(endTime.ToUniversalTime()).ToUnixTimeMilliseconds();
            zoneLog.Add(new ZoneLogRecord {
                StartMs = unixMs, EndMs = endMs, Upper = top, Lower = bot,
                Direction = gapDir, DiffTicks = gapPts / TickSize,
                OverlapAtBirth = nueva.OverlapCount, M1Bar = CurrentBars[1]
            });

            // Export de PARIDAD: una linea por zona, AL NACER. Mismo orden de campos que
            // el HEADER del kernel Python, para que el matcher compare sin traducir.
            if (parityWriter != null)
            {
            	var pci = System.Globalization.CultureInfo.InvariantCulture;
            	parityWriter.WriteLine(string.Format(pci,
            		"{0},ZONE_CREATED,{1},{2},D{3:000000},{4},{5},{6},{7},{8},{9},{10},{11}",
            		paritySeq, startTime.ToString("yyyy-MM-dd HH:mm:ss.fff", pci), unixMs,
            		paritySeq + 1, unixMs, endMs, top, bot,
            		gapTicks, gapDir,
            		nueva.OverlapCount, CurrentBars[1]));
            	paritySeq++;
            }
            // En realtime volcamos cada zona; en historico cada 500 para no
            // reescribir el archivo entero en cada gap (O(n^2)).
            if (State == State.Realtime) FlushZoneLogCsv();
            else if (zoneLog.Count % 500 == 0) FlushZoneLogCsv();

            // Cap memoria
            if (diffs.Count > Math.Max(10, MaxRectangles))
            {
                int toRemove = diffs.Count - MaxRectangles;
                for (int i = 0; i < toRemove; i++)
                    RemoveDrawObject(diffs[i].TagRect);
                diffs.RemoveRange(0, toRemove);
            }
        }

        private void ProcesarSuperposiciones(Diff nueva)
        {
            // Buscar todas las zonas vivas que se solapan con la nueva en precio
            // y temporalmente (ventana medida en barras M1).
            for (int i = 0; i < diffs.Count; i++)
            {
                Diff existing = diffs[i];

                // Temporal: si la existente ya expiro antes de la nueva, no cuenta
                if (existing.ExpiresM1Bar < nueva.StartM1Bar) continue;

                // Precio: se solapan los rangos?
                if (existing.TopPrice < nueva.BottomPrice) continue;
                if (existing.BottomPrice > nueva.TopPrice) continue;

                // Solapan -> incrementar contadores
                existing.OverlapCount++;
                nueva.OverlapCount++;

                // Re-dibujar la existente con su nuevo color/opacidad
                DibujarDiff(existing);
            }
        }

        private void DibujarDiff(Diff d)
        {
            Brush col = GetHeatBrush(d.OverlapCount);
            int op = GetOpacityScaled(d.OverlapCount);

            // Anclaje por TIEMPO ABSOLUTO: la zona inicia exactamente en el gap (StartTime)
            // y se extiende hacia la derecha hasta EndTime, sin importar si el primario es 25t/50t.
            Draw.Rectangle(this, d.TagRect, false,
                d.StartTime, d.TopPrice,
                d.EndTime,   d.BottomPrice,
                Brushes.Transparent, col, op);
        }

        // === Logger CSV para el ecosistema quantlab/VectorBT ===
        // Reescribe el CSV completo desde zoneLog (dedup natural: una escritura
        // del buffer en memoria). InvariantCulture -> punto decimal aunque el
        // sistema este en locale ES (coma), si no el CSV sale corrupto.
        private void FlushZoneLogCsv()
        {
            try
            {
                string dir = System.IO.Path.GetDirectoryName(csvLogPath);
                if (!string.IsNullOrEmpty(dir) && !System.IO.Directory.Exists(dir))
                    System.IO.Directory.CreateDirectory(dir);

                var ci = System.Globalization.CultureInfo.InvariantCulture;
                // MERGE, no sobreescritura: una instancia fresca (lookback corto)
                // no debe destruir lo acumulado por corridas anteriores.
                var lines = new System.Collections.Generic.Dictionary<string, string>();
                if (System.IO.File.Exists(csvLogPath))
                {
                    foreach (var line in System.IO.File.ReadAllLines(csvLogPath))
                    {
                        if (line.StartsWith("instrument") || line.Trim().Length == 0) continue;
                        var p = line.Split(',');
                        if (p.Length > 4) lines[p[1] + "|" + p[3] + "|" + p[4]] = line;
                    }
                }
                string inst = Instrument.FullName;
                foreach (var z in zoneLog)
                {
                    string key = string.Format(ci, "{0}|{1}|{2}", z.StartMs, z.Upper, z.Lower);
                    // v1.2 (Decision B de Nico, 2026-07-26): cada fila lleva la
                    // VERSION del indicador que la genero. Va por FILA y no en un
                    // header porque este archivo MERGEA corridas distintas: una
                    // version a nivel de archivo seria una afirmacion falsa sobre
                    // el contenido mezclado. Sin este campo el logger de research
                    // no se puede filtrar por version, que es exactamente lo que
                    // dejo pasar el defecto de v1.0 durante todo su historico.
                    lines[key] = string.Format(ci,
                        "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10}",
                        inst, z.StartMs, z.EndMs, z.Upper, z.Lower, (z.Upper + z.Lower) / 2.0,
                        z.Direction, z.DiffTicks, z.OverlapAtBirth, z.M1Bar, IND_VERSION);
                }
                var sb = new System.Text.StringBuilder();
                sb.AppendLine("instrument,start_ms,end_ms,upper,lower,mid,direction,diff_ticks,overlap_at_birth,m1_bar,ind_version");
                foreach (var kv in lines) sb.AppendLine(kv.Value);
                System.IO.File.WriteAllText(csvLogPath, sb.ToString());
            }
            catch { /* research logger: nunca romper el indicador por un fallo de IO */ }
        }

        // === Persistencia SQLite (AlgoNQ) ===
        private string dbPath = @"D:\AlgoProject\data\algo_features.sqlite";

        private void PersistDiff(string inst, long ts, double top, double bot, double diffPts)
        {
            try
            {
                using (var conn = new SQLiteConnection("Data Source=" + dbPath + ";Version=3;Journal Mode=Wal;Synchronous=Off;"))
                {
                    conn.Open();
                    string checkSql = @"SELECT COUNT(*) FROM close_open_diffs WHERE instrument = @inst AND detected_ts = @ts AND top_px = @top";
                    using (var checkCmd = new SQLiteCommand(checkSql, conn))
                    {
                        checkCmd.Parameters.AddWithValue("@inst", inst);
                        checkCmd.Parameters.AddWithValue("@ts", ts);
                        checkCmd.Parameters.AddWithValue("@top", top);
                        long existing = 0;
                        try { existing = (long)checkCmd.ExecuteScalar(); } catch { }
                        if (existing > 0) return;
                    }

                    string sql = @"INSERT INTO close_open_diffs (instrument, detected_ts, top_px, bottom_px, diff_pts)
                                   VALUES (@inst, @ts, @top, @bot, @diff)";
                    using (var cmd = new SQLiteCommand(sql, conn))
                    {
                        cmd.Parameters.AddWithValue("@inst", inst);
                        cmd.Parameters.AddWithValue("@ts", ts);
                        cmd.Parameters.AddWithValue("@top", top);
                        cmd.Parameters.AddWithValue("@bot", bot);
                        cmd.Parameters.AddWithValue("@diff", diffPts);
                        cmd.ExecuteNonQuery();
                    }
                }
            }
            catch (Exception ex)
            {
                // Si la tabla no existe, la creamos
                try
                {
                    using (var conn = new SQLiteConnection("Data Source=" + dbPath + ";Version=3;"))
                    {
                        conn.Open();
                        string createSql = @"CREATE TABLE IF NOT EXISTS close_open_diffs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            instrument TEXT,
                            detected_ts INTEGER,
                            top_px REAL,
                            bottom_px REAL,
                            diff_pts REAL
                        )";
                        using (var cmd = new SQLiteCommand(createSql, conn)) { cmd.ExecuteNonQuery(); }

                        using (var cmd = new SQLiteCommand(@"INSERT INTO close_open_diffs (instrument, detected_ts, top_px, bottom_px, diff_pts)
                                   VALUES (@inst, @ts, @top, @bot, @diff)", conn))
                        {
                            cmd.Parameters.AddWithValue("@inst", inst);
                            cmd.Parameters.AddWithValue("@ts", ts);
                            cmd.Parameters.AddWithValue("@top", top);
                            cmd.Parameters.AddWithValue("@bot", bot);
                            cmd.Parameters.AddWithValue("@diff", diffPts);
                            cmd.ExecuteNonQuery();
                        }
                    }
                }
                catch { }
            }
        }

        // ===================== DETECCION DE EXPANSIONES =====================
        // ZigZag de umbral fijo sobre M1. Cada tramo pivote->extremo se evalua:
        // si su alto (ticks) y ancho (barras M1) superan el minimo y NO hay
        // ninguna zona (diff dibujada) que lo intersecte, se marca como expansion.
        private void DetectarExpansion()
        {
            double rev = Math.Max(1, ExpansionReversalTicks) * TickSize;
            double hi  = Highs[1][0];
            double lo  = Lows[1][0];
            double c   = Closes[1][0];
            DateTime t = Times[1][0];
            int bar    = CurrentBars[1];

            if (!expInit)
            {
                pivBar = bar; pivPrice = c; pivTime = t;
                hiBar  = bar; hiPrice  = hi; hiTime = t;
                loBar  = bar; loPrice  = lo; loTime = t;
                expTrend = 0; expInit = true;
                return;
            }

            if (expTrend >= 0)
            {
                if (hi >= hiPrice) { hiPrice = hi; hiBar = bar; hiTime = t; }
                if (hiPrice - lo >= rev)
                {
                    EvaluarTramo(pivBar, pivPrice, pivTime, hiBar, hiPrice, hiTime);
                    pivBar = hiBar; pivPrice = hiPrice; pivTime = hiTime;
                    loPrice = lo; loBar = bar; loTime = t;
                    expTrend = -1;
                }
            }
            if (expTrend <= 0)
            {
                if (lo <= loPrice) { loPrice = lo; loBar = bar; loTime = t; }
                if (hi - loPrice >= rev)
                {
                    EvaluarTramo(pivBar, pivPrice, pivTime, loBar, loPrice, loTime);
                    pivBar = loBar; pivPrice = loPrice; pivTime = loTime;
                    hiPrice = hi; hiBar = bar; hiTime = t;
                    expTrend = +1;
                }
            }
        }

        private void EvaluarTramo(int startBar, double startPrice, DateTime startTime,
                                  int endBar, double endPrice, DateTime endTime)
        {
            int bars = endBar - startBar;
            if (bars < ExpansionMinBarsM1) return;

            double top = Math.Max(startPrice, endPrice);
            double bot = Math.Min(startPrice, endPrice);
            if (top - bot < ExpansionMinTicks * TickSize) return;

            // Debe tener 0 zonas: ninguna diff dibujada intersecta el rectangulo
            // (overlap en barras M1 y en precio).
            for (int i = 0; i < diffs.Count; i++)
            {
                Diff d = diffs[i];
                if (d.ExpiresM1Bar < startBar || d.StartM1Bar > endBar) continue; // sin overlap temporal
                if (d.TopPrice < bot || d.BottomPrice > top) continue;            // sin overlap de precio
                return; // hay al menos una zona -> no es expansion de 0 zonas
            }

            expCounter++;
            string tag = "AAEXP_" + expCounter;
            DibujarExpansion(tag, startTime, top, endTime, bot);
            expansionTags.Add(tag);

            long ts0 = new DateTimeOffset(startTime.ToUniversalTime()).ToUnixTimeMilliseconds();
            long ts1 = new DateTimeOffset(endTime.ToUniversalTime()).ToUnixTimeMilliseconds();
            PersistExpansion(Instrument.FullName, ts0, ts1, top, bot, top - bot, bars);

            int cap = Math.Max(10, MaxRectangles);
            if (expansionTags.Count > cap)
            {
                int toRemove = expansionTags.Count - cap;
                for (int i = 0; i < toRemove; i++)
                    RemoveDrawObject(expansionTags[i]);
                expansionTags.RemoveRange(0, toRemove);
            }
        }

        private void DibujarExpansion(string tag, DateTime t0, double top, DateTime t1, double bot)
        {
            Draw.Rectangle(this, tag, false, t0, top, t1, bot, expOutline, expArea, ExpansionOpacity);
        }

        private void PersistExpansion(string inst, long ts0, long ts1, double top, double bot, double rangePts, int barsM1)
        {
            try
            {
                using (var conn = new SQLiteConnection("Data Source=" + dbPath + ";Version=3;Journal Mode=Wal;Synchronous=Off;"))
                {
                    conn.Open();
                    string checkSql = @"SELECT COUNT(*) FROM expansion_zones WHERE instrument = @inst AND start_ts = @ts0 AND top_px = @top";
                    using (var checkCmd = new SQLiteCommand(checkSql, conn))
                    {
                        checkCmd.Parameters.AddWithValue("@inst", inst);
                        checkCmd.Parameters.AddWithValue("@ts0", ts0);
                        checkCmd.Parameters.AddWithValue("@top", top);
                        long existing = 0;
                        try { existing = (long)checkCmd.ExecuteScalar(); } catch { }
                        if (existing > 0) return;
                    }

                    string sql = @"INSERT INTO expansion_zones (instrument, start_ts, end_ts, top_px, bottom_px, range_pts, bars_m1)
                                   VALUES (@inst, @ts0, @ts1, @top, @bot, @rng, @bars)";
                    using (var cmd = new SQLiteCommand(sql, conn))
                    {
                        cmd.Parameters.AddWithValue("@inst", inst);
                        cmd.Parameters.AddWithValue("@ts0", ts0);
                        cmd.Parameters.AddWithValue("@ts1", ts1);
                        cmd.Parameters.AddWithValue("@top", top);
                        cmd.Parameters.AddWithValue("@bot", bot);
                        cmd.Parameters.AddWithValue("@rng", rangePts);
                        cmd.Parameters.AddWithValue("@bars", barsM1);
                        cmd.ExecuteNonQuery();
                    }
                }
            }
            catch
            {
                try
                {
                    using (var conn = new SQLiteConnection("Data Source=" + dbPath + ";Version=3;"))
                    {
                        conn.Open();
                        string createSql = @"CREATE TABLE IF NOT EXISTS expansion_zones (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            instrument TEXT,
                            start_ts INTEGER,
                            end_ts INTEGER,
                            top_px REAL,
                            bottom_px REAL,
                            range_pts REAL,
                            bars_m1 INTEGER
                        )";
                        using (var cmd = new SQLiteCommand(createSql, conn)) { cmd.ExecuteNonQuery(); }

                        using (var cmd = new SQLiteCommand(@"INSERT INTO expansion_zones (instrument, start_ts, end_ts, top_px, bottom_px, range_pts, bars_m1)
                                   VALUES (@inst, @ts0, @ts1, @top, @bot, @rng, @bars)", conn))
                        {
                            cmd.Parameters.AddWithValue("@inst", inst);
                            cmd.Parameters.AddWithValue("@ts0", ts0);
                            cmd.Parameters.AddWithValue("@ts1", ts1);
                            cmd.Parameters.AddWithValue("@top", top);
                            cmd.Parameters.AddWithValue("@bot", bot);
                            cmd.Parameters.AddWithValue("@rng", rangePts);
                            cmd.Parameters.AddWithValue("@bars", barsM1);
                            cmd.ExecuteNonQuery();
                        }
                    }
                }
                catch { }
            }
        }

        #region Properties
        [NinjaScriptProperty][Range(1, 50)]
        [Display(Name="Min diferencia (ticks)", Order=1, GroupName="Parametros",
            Description="1 = todas las diferencias close-open. Subir para filtrar gaps mas grandes.")]
        public int MinDiffTicks { get; set; }
        
        [NinjaScriptProperty]
        [Display(Name = "Ruta CSV de paridad (vacio = off)", Order = 99,
            GroupName = "Z. EdgeLab")]
        public string EventLogPath { get; set; }

        [NinjaScriptProperty][Range(1, 5000)]
        [Display(Name="Extend Bars (M1)", Order=2, GroupName="Parametros",
            Description="Vida de cada zona en barras M1 (~minutos). Define extension visual y ventana de superposicion temporal.")]
        public int ExtendBars { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Opacidad base", Order=3, GroupName="Parametros",
            Description="Opacidad inicial. Sube automaticamente con la cantidad de superposiciones.")]
        public int BaseOpacity { get; set; }

        [NinjaScriptProperty][Range(50, 50000)]
        [Display(Name="Max Rectangles", Order=4, GroupName="Parametros")]
        public int MaxRectangles { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Filtrar por percentil", Order=5, GroupName="Filtro percentil",
            Description="Si esta tildado, solo dibuja gaps cuyo tamano supere el percentil de los ultimos N.")]
        public bool FiltrarPorPercentil { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Percentil minimo (%)", Order=6, GroupName="Filtro percentil",
            Description="Umbral de percentil sobre los ultimos N gaps. 90 = solo el top 10% mas grande. 10 = descarta el 10% mas chico.")]
        public double PercentilMin { get; set; }

        [NinjaScriptProperty][Range(5, 5000)]
        [Display(Name="Ventana percentil (gaps)", Order=7, GroupName="Filtro percentil",
            Description="Cantidad de gaps recientes usados para calcular el percentil (los ultimos N).")]
        public int VentanaPercentil { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Detectar expansiones", Order=8, GroupName="Expansiones",
            Description="Si esta tildado, marca tramos direccionales que no tengan ninguna zona encima (voids).")]
        public bool DetectarExpansiones { get; set; }

        [NinjaScriptProperty][Range(1, 100000)]
        [Display(Name="Alto minimo (ticks)", Order=9, GroupName="Expansiones",
            Description="Alto minimo del tramo, en ticks. Calibralo al alto del rectangulo de referencia.")]
        public int ExpansionMinTicks { get; set; }

        [NinjaScriptProperty][Range(1, 100000)]
        [Display(Name="Ancho minimo (barras M1)", Order=10, GroupName="Expansiones",
            Description="Ancho minimo del tramo, en barras M1 (~minutos). Calibralo al ancho del rectangulo de referencia.")]
        public int ExpansionMinBarsM1 { get; set; }

        [NinjaScriptProperty][Range(1, 100000)]
        [Display(Name="Retroceso ZigZag (ticks)", Order=11, GroupName="Expansiones",
            Description="Retroceso (en ticks) que cierra un tramo. Mas alto = tramos mas largos y menos sensibles al ruido.")]
        public int ExpansionReversalTicks { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Opacidad expansion", Order=12, GroupName="Expansiones")]
        public int ExpansionOpacity { get; set; }
        #endregion
    }
}
