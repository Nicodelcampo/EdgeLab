// ============================================================================
// CaptureEventProbeV2.cs — instrumental de medición EventIdentity v2.1.
//
// NO detecta zonas, NO opera y NO modifica indicadores existentes.
// Un callback -> un registro; nunca deduplica. OnMarketData sólo toma un
// snapshot y lo encola: el writer dedicado realiza todo el I/O.
//
// v2.1 separa provider, entorno de cuenta y modo de captura; declara la zona
// horaria de e.Time sin fingir UTC; y escribe vacío para quotes no aplicables
// en vez de double.MinValue.
// ============================================================================
#region Using declarations
using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class CaptureEventProbeV2 : Indicator
    {
        // Version del instrumental. UNA sola fuente de verdad: la escribe el
        // encabezado de metadata de la captura. Acompana a `schema=`, que versiona
        // el CONTRATO DE COLUMNAS: los dos se mueven por separado (una correccion
        // de captura sin cambio de columnas sube version y deja schema quieto).
        private const string IND_VERSION = "2.1";

        private sealed class RawEvent
        {
            public long CallbackSeq;
            public long SourceTimeTicks;
            public string SourceTimeKind;
            public string SourceTimeIso;
            public long CaptureUtcTicks;
            public string CaptureUtcIso;
            public long MonotonicTicks;
            public string Nt8State;
            public string EventKind;
            public string Instrument;
            public string Contract;
            public double Price;
            public double Volume;
            public double? Bid;
            public double? Ask;
            public string Aggressor;
            public string AggressorProvenance;
            public string QuoteProvenance;
        }

        private readonly CultureInfo inv = CultureInfo.InvariantCulture;
        private StreamWriter log;
        private BlockingCollection<RawEvent> queue;
        private Thread writerThread;
        private string captureId = "";
        private string processInstanceId = "";
        private string resolvedPath = "";
        private long callbackSeq = -1;
        private long captureSeq = -1;
        private long droppedAtQueue;
        private long writerErrors;
        private long rowsWritten;
        private volatile bool closing;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "CaptureEventProbeV2";
                Description = "Captura cruda OnMarketData para EventIdentity v2.1. No opera.";
                Calculate = Calculate.OnEachTick;
                IsOverlay = true;
                DrawOnPricePanel = false;
                EventLogPath = @"C:\ProyectosQuant\EdgeLab\oracles\capture_event_v2.tsv";
                CaptureModeLabel = "DECLARAR_historical_playback_live";
                ProviderLabel = "DECLARAR_provider";
                AccountEnvironmentLabel = "DECLARAR_simulation_or_live";
                SourceTimezoneLabel = "DECLARAR_NT8_Tools_Options_General_TimeZone";
                QueueCapacity = 250000;
            }
            else if (State == State.DataLoaded)
            {
                OpenLedger();
            }
            else if (State == State.Terminated)
            {
                CloseLedger();
            }
        }

        private void OpenLedger()
        {
            try
            {
                Process p = Process.GetCurrentProcess();
                processInstanceId = string.Format(inv, "pid-{0}-start-{1}",
                    p.Id, p.StartTime.ToUniversalTime().Ticks);
                captureId = string.Format(inv, "{0}-{1}",
                    DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffffffZ", inv),
                    Guid.NewGuid().ToString("N"));

                string dir = Path.GetDirectoryName(EventLogPath);
                if (string.IsNullOrEmpty(dir))
                    dir = NinjaTrader.Core.Globals.UserDataDir;
                if (!Directory.Exists(dir))
                    Directory.CreateDirectory(dir);

                string stem = Path.GetFileNameWithoutExtension(EventLogPath);
                string ext = Path.GetExtension(EventLogPath);
                if (string.IsNullOrEmpty(ext)) ext = ".tsv";
                resolvedPath = Path.Combine(dir, stem + "__" + captureId + ext);
                if (File.Exists(resolvedPath))
                    throw new IOException("la ruta exclusiva ya existe: " + resolvedPath);

                log = new StreamWriter(resolvedPath, false, new UTF8Encoding(false));
                log.WriteLine("# meta indicator=CaptureEventProbeV2,version=" + IND_VERSION);
                log.WriteLine("# schema=event_capture_raw_v2_1");
                log.WriteLine("# capture_id=" + captureId);
                log.WriteLine("# process_instance_id=" + processInstanceId);
                log.WriteLine("# created_utc=" + DateTime.UtcNow.ToString("o", inv));
                log.WriteLine("# stopwatch_frequency=" + Stopwatch.Frequency.ToString(inv));
                log.WriteLine("# capture_mode_label=" + Safe(CaptureModeLabel));
                log.WriteLine("# provider_label=" + Safe(ProviderLabel));
                log.WriteLine("# account_environment_label=" + Safe(AccountEnvironmentLabel));
                log.WriteLine("# source_timezone_label=" + Safe(SourceTimezoneLabel));
                log.WriteLine("# queue_capacity=" + QueueCapacity.ToString(inv));
                log.WriteLine("# source_sequence=NOT_EXPOSED_BY_THIS_NT8_CALLBACK");
                log.WriteLine("capture_id\tprocess_instance_id\tcallback_seq\tcapture_seq\t"
                    + "source_time_ticks\tsource_time_kind\tsource_time_iso\t"
                    + "capture_utc_ticks\tcapture_utc_iso\tmonotonic_ticks\t"
                    + "stopwatch_frequency\tnt8_state\tevent_kind\tinstrument\tcontract\t"
                    + "price\tvolume\tbid\task\taggressor\taggressor_provenance\t"
                    + "timestamp_provenance\tquote_provenance\tcapture_mode_label\t"
                    + "provider_label\taccount_environment_label\tsource_timezone_label");
                log.Flush();

                queue = new BlockingCollection<RawEvent>(QueueCapacity);
                writerThread = new Thread(WriterLoop) {
                    IsBackground = true,
                    Name = "EdgeLab-CaptureEventProbeV2-writer"
                };
                writerThread.Start();
                Print("CaptureEventProbeV2: escribiendo " + resolvedPath);
            }
            catch (Exception ex)
            {
                Interlocked.Increment(ref writerErrors);
                Print("CaptureEventProbeV2: NO se pudo abrir el ledger: " + ex.Message);
                try { if (log != null) log.Close(); } catch { }
                log = null;
            }
        }

        private void WriterLoop()
        {
            int sinceFlush = 0;
            try
            {
                foreach (RawEvent r in queue.GetConsumingEnumerable())
                {
                    long cap = Interlocked.Increment(ref captureSeq);
                    log.WriteLine(FormatRow(r, cap));
                    Interlocked.Increment(ref rowsWritten);
                    if (++sinceFlush >= 256)
                    {
                        log.Flush();
                        sinceFlush = 0;
                    }
                }
                log.Flush();
            }
            catch (Exception ex)
            {
                Interlocked.Increment(ref writerErrors);
                Print("CaptureEventProbeV2: writer abortado: " + ex.Message);
            }
        }

        private void CloseLedger()
        {
            closing = true;
            try
            {
                if (queue != null && !queue.IsAddingCompleted)
                    queue.CompleteAdding();
            }
            catch { }

            if (writerThread != null && writerThread.IsAlive && !writerThread.Join(30000))
            {
                Interlocked.Increment(ref writerErrors);
                Print("CaptureEventProbeV2: writer no terminó dentro de 30 segundos");
            }

            if (log != null)
            {
                try
                {
                    log.WriteLine(string.Format(inv,
                        "# summary callbacks_seen={0},rows_written={1},dropped_at_queue={2},writer_errors={3}",
                        Interlocked.Read(ref callbackSeq) + 1,
                        Interlocked.Read(ref rowsWritten),
                        Interlocked.Read(ref droppedAtQueue),
                        Interlocked.Read(ref writerErrors)));
                    log.Flush();
                    log.Close();
                }
                catch (Exception ex)
                {
                    Interlocked.Increment(ref writerErrors);
                    Print("CaptureEventProbeV2: error cerrando ledger: " + ex.Message);
                }
                log = null;
            }
            if (queue != null)
            {
                queue.Dispose();
                queue = null;
            }
            Print(string.Format(inv,
                "CaptureEventProbeV2: cierre callbacks={0} rows={1} drops={2} writer_errors={3} path={4}",
                Interlocked.Read(ref callbackSeq) + 1,
                Interlocked.Read(ref rowsWritten),
                Interlocked.Read(ref droppedAtQueue),
                Interlocked.Read(ref writerErrors), resolvedPath));
        }

        protected override void OnMarketData(MarketDataEventArgs e)
        {
            long cb = Interlocked.Increment(ref callbackSeq);
            long monotonic = Stopwatch.GetTimestamp();
            DateTime captured = DateTime.UtcNow;

            bool quoteRelevant = e.MarketDataType == MarketDataType.Last
                || e.MarketDataType == MarketDataType.Bid
                || e.MarketDataType == MarketDataType.Ask;
            double? bid = quoteRelevant && IsUsableQuote(e.Bid) ? (double?)e.Bid : null;
            double? ask = quoteRelevant && IsUsableQuote(e.Ask) ? (double?)e.Ask : null;
            string quoteProvenance = bid.HasValue || ask.HasValue
                ? "nt8_snapshot" : "missing";

            string aggressor = "unknown";
            string aggressorProvenance = "not_applicable";
            if (e.MarketDataType == MarketDataType.Last)
            {
                aggressorProvenance = "unknown";
                if (bid.HasValue && ask.HasValue && ask.Value >= bid.Value)
                {
                    aggressorProvenance = "quote_rule";
                    if (e.Price >= ask.Value) aggressor = "buy";
                    else if (e.Price <= bid.Value) aggressor = "sell";
                    else aggressor = "unclassified";
                }
            }

            RawEvent record = new RawEvent {
                CallbackSeq = cb,
                SourceTimeTicks = e.Time.Ticks,
                SourceTimeKind = e.Time.Kind.ToString(),
                SourceTimeIso = e.Time.ToString("yyyy-MM-ddTHH:mm:ss.fffffff", inv),
                CaptureUtcTicks = captured.Ticks,
                CaptureUtcIso = captured.ToString("o", inv),
                MonotonicTicks = monotonic,
                Nt8State = State.ToString(),
                EventKind = e.MarketDataType.ToString(),
                Instrument = Safe(Instrument.MasterInstrument.Name),
                Contract = Safe(Instrument.FullName),
                Price = e.Price,
                Volume = Convert.ToDouble(e.Volume, inv),
                Bid = bid,
                Ask = ask,
                Aggressor = aggressor,
                AggressorProvenance = aggressorProvenance,
                QuoteProvenance = quoteProvenance
            };

            if (closing || queue == null || queue.IsAddingCompleted)
            {
                Interlocked.Increment(ref droppedAtQueue);
                return;
            }
            try
            {
                if (!queue.TryAdd(record))
                    Interlocked.Increment(ref droppedAtQueue);
            }
            catch (InvalidOperationException)
            {
                Interlocked.Increment(ref droppedAtQueue);
            }
        }

        protected override void OnBarUpdate()
        {
            // Deliberadamente vacío. La evidencia sale sólo de OnMarketData.
        }

        private bool IsUsableQuote(double value)
        {
            return value > 0.0 && value != double.MinValue && value != double.MaxValue
                && !double.IsNaN(value) && !double.IsInfinity(value);
        }

        private string FormatNullable(double? value)
        {
            return value.HasValue ? value.Value.ToString("R", inv) : "";
        }

        private string FormatRow(RawEvent r, long cap)
        {
            return string.Join("\t", new string[] {
                captureId, processInstanceId, r.CallbackSeq.ToString(inv), cap.ToString(inv),
                r.SourceTimeTicks.ToString(inv), r.SourceTimeKind, r.SourceTimeIso,
                r.CaptureUtcTicks.ToString(inv), r.CaptureUtcIso,
                r.MonotonicTicks.ToString(inv), Stopwatch.Frequency.ToString(inv),
                r.Nt8State, r.EventKind, r.Instrument, r.Contract,
                r.Price.ToString("R", inv), r.Volume.ToString("R", inv),
                FormatNullable(r.Bid), FormatNullable(r.Ask), r.Aggressor,
                r.AggressorProvenance, "nt8_event_time", r.QuoteProvenance,
                Safe(CaptureModeLabel), Safe(ProviderLabel),
                Safe(AccountEnvironmentLabel), Safe(SourceTimezoneLabel)
            });
        }

        private string Safe(string value)
        {
            if (value == null) return "";
            return value.Replace("\t", " ").Replace("\r", " ").Replace("\n", " ");
        }

        #region Properties
        [NinjaScriptProperty]
        [System.ComponentModel.DisplayName("Ruta base del TSV")]
        public string EventLogPath { get; set; }

        [NinjaScriptProperty]
        [System.ComponentModel.DisplayName("Modo: historical/playback/live")]
        public string CaptureModeLabel { get; set; }

        [NinjaScriptProperty]
        [System.ComponentModel.DisplayName("Proveedor de datos declarado")]
        public string ProviderLabel { get; set; }

        [NinjaScriptProperty]
        [System.ComponentModel.DisplayName("Entorno de cuenta: simulation/live")]
        public string AccountEnvironmentLabel { get; set; }

        [NinjaScriptProperty]
        [System.ComponentModel.DisplayName("Zona horaria configurada en NT8")]
        public string SourceTimezoneLabel { get; set; }

        [NinjaScriptProperty]
        [System.ComponentModel.DisplayName("Capacidad de cola")]
        public int QueueCapacity { get; set; }
        #endregion
    }
}
