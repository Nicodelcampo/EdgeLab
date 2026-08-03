// ============================================================================
// CaptureEventProbeV2.cs — instrumental de medición para EventIdentity v2.
//
// NO detecta zonas, NO opera y NO modifica indicadores existentes. Registra un
// ledger crudo de OnMarketData para medir qué identidad y precisión expone NT8.
//
// Reglas:
// - un callback -> una fila; nunca deduplica;
// - callback_seq se asigna al entrar al callback;
// - capture_seq se asigna al persistir;
// - source_time se conserva como DateTime.Ticks + Kind + texto, SIN fingir UTC;
// - capture_utc viene de DateTime.UtcNow;
// - monotonic_ticks viene de Stopwatch.GetTimestamp;
// - no llama a callback_seq "exchange sequence": es orden local de NT8;
// - cada instancia crea un archivo nuevo; nunca append ni overwrite.
//
// El archivo es TSV para evitar ambigüedad con decimales/campos de texto.
// Estado: requiere compilación y prueba en la instalación NT8 de Nico.
// ============================================================================
#region Using declarations
using System;
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
        private readonly object writeLock = new object();
        private readonly CultureInfo inv = CultureInfo.InvariantCulture;
        private StreamWriter log;
        private string captureId = "";
        private string processInstanceId = "";
        private string resolvedPath = "";
        private long callbackSeq = -1;
        private long captureSeq = -1;
        private bool writeFailed = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "CaptureEventProbeV2";
                Description = "Captura cruda OnMarketData para EventIdentity v2. No opera.";
                Calculate = Calculate.OnEachTick;
                IsOverlay = true;
                DrawOnPricePanel = false;
                EventLogPath = @"E:\EdgeLab\oracles\capture_event_v2.tsv";
                CaptureModeLabel = "DECLARAR_historical_playback_live";
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
                log.AutoFlush = true;
                log.WriteLine("# schema=event_capture_raw_v2");
                log.WriteLine("# capture_id=" + captureId);
                log.WriteLine("# process_instance_id=" + processInstanceId);
                log.WriteLine("# created_utc=" + DateTime.UtcNow.ToString("o", inv));
                log.WriteLine("# stopwatch_frequency=" + Stopwatch.Frequency.ToString(inv));
                log.WriteLine("# capture_mode_label=" + Safe(CaptureModeLabel));
                log.WriteLine("# source_sequence=NOT_EXPOSED_BY_THIS_NT8_CALLBACK");
                log.WriteLine("capture_id\tprocess_instance_id\tcallback_seq\tcapture_seq\t"
                    + "source_time_ticks\tsource_time_kind\tsource_time_iso\t"
                    + "capture_utc_ticks\tcapture_utc_iso\tmonotonic_ticks\t"
                    + "stopwatch_frequency\tnt8_state\tevent_kind\tinstrument\tcontract\t"
                    + "price\tvolume\tbid\task\taggressor\taggressor_provenance\t"
                    + "timestamp_provenance\tquote_provenance\tcapture_mode_label");
                Print("CaptureEventProbeV2: escribiendo " + resolvedPath);
            }
            catch (Exception ex)
            {
                writeFailed = true;
                Print("CaptureEventProbeV2: NO se pudo abrir el ledger: " + ex.Message);
            }
        }

        private void CloseLedger()
        {
            lock (writeLock)
            {
                if (log == null) return;
                log.Flush();
                log.Close();
                log = null;
            }
        }

        protected override void OnMarketData(MarketDataEventArgs e)
        {
            long cb = Interlocked.Increment(ref callbackSeq);
            long monotonic = Stopwatch.GetTimestamp();
            DateTime captured = DateTime.UtcNow;

            if (log == null || writeFailed)
                return;

            string eventKind = e.MarketDataType.ToString();
            string aggressor = "unknown";
            string aggressorProvenance = "not_applicable";
            if (e.MarketDataType == MarketDataType.Last)
            {
                aggressorProvenance = "quote_rule";
                if (e.Ask > 0 && e.Bid > 0 && e.Ask >= e.Bid)
                {
                    if (e.Price >= e.Ask) aggressor = "buy";
                    else if (e.Price <= e.Bid) aggressor = "sell";
                    else aggressor = "unclassified";
                }
                else
                {
                    aggressor = "unknown";
                    aggressorProvenance = "unknown";
                }
            }

            lock (writeLock)
            {
                if (log == null || writeFailed)
                    return;
                long cap = Interlocked.Increment(ref captureSeq);
                try
                {
                    log.WriteLine(string.Join("\t", new string[] {
                        captureId,
                        processInstanceId,
                        cb.ToString(inv),
                        cap.ToString(inv),
                        e.Time.Ticks.ToString(inv),
                        e.Time.Kind.ToString(),
                        e.Time.ToString("yyyy-MM-ddTHH:mm:ss.fffffff", inv),
                        captured.Ticks.ToString(inv),
                        captured.ToString("o", inv),
                        monotonic.ToString(inv),
                        Stopwatch.Frequency.ToString(inv),
                        State.ToString(),
                        eventKind,
                        Safe(Instrument.MasterInstrument.Name),
                        Safe(Instrument.FullName),
                        e.Price.ToString("R", inv),
                        e.Volume.ToString("R", inv),
                        e.Bid.ToString("R", inv),
                        e.Ask.ToString("R", inv),
                        aggressor,
                        aggressorProvenance,
                        "nt8_event_time",
                        "nt8_snapshot",
                        Safe(CaptureModeLabel)
                    }));
                }
                catch (Exception ex)
                {
                    writeFailed = true;
                    Print("CaptureEventProbeV2: escritura abortada en callback_seq="
                        + cb.ToString(inv) + ": " + ex.Message);
                    try { log.Flush(); } catch { }
                }
            }
        }

        protected override void OnBarUpdate()
        {
            // Deliberadamente vacío. La evidencia sale sólo de OnMarketData.
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
        [System.ComponentModel.DisplayName("Modo declarado: historical/playback/live")]
        public string CaptureModeLabel { get; set; }
        #endregion
    }
}
