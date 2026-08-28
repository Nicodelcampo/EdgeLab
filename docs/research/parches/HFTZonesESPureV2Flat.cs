// HFTZonesESPureV2Flat.cs - Detector HFT para ES/MES con modo ABSORB + LOGGER ENRIQUECIDO.
//
// === VERSION LOGGER (proyecto C:\LoggerHFT) ===
// Drop-in replacement del HFTZonesESPureV2Flat original. Misma deteccion de zonas, pero
// persiste un set de features completo + un stream continuo de order-flow (delta
// reconstruido por tick-rule) para analisis offline (retorno/MFE/MAE/revisita/HOLD-break).
//
// Tablas (en C:\LoggerHFT\data\hft_logger.sqlite, compartidas con el logger de NQ):
//   hft_zones : una fila por zona (geometria, timing, volumen, DELTA, ABSORCION).
//   hft_flow  : barras de N seg con OHLC + buy/sell/delta (tick-rule). Base del forward.
//
// CONCURRENCIA (FIX): escritura segura con varias instancias (ES+MES+NQ+6E a la vez).
//   - PRAGMA busy_timeout=5000 + WAL.
//   - NO se mantiene una transaccion abierta: se bufferea y se hace flush en
//     transacciones CORTAS (cada N filas / cada 2s / al cerrar). Asi cada instancia
//     toma el lock, escribe y lo libera; las demas no quedan bloqueadas.
//
// Delta tick-rule: side=+1 si close>prevClose, -1 si <, carry si =. buy/sell/delta.
//
// Logica de deteccion original (sin cambios): FIX#1 burst, FIX#2 gap 1er tick, FIX#3 ABSORB.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Data.SQLite;
using System.IO;
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
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class HFTZonesESPureV2Flat : Indicator
    {
        public enum HFTBucket { Predator, Ultra, Fast, Absorb }

        public sealed class Zone
        {
            public int    StartBar, EndBar;
            public DateTime StartTime, EndTime;
            public double Upper, Lower;
            public int    Direction;
            public HFTBucket Bucket;
            public double AvgMs, TotalMs, VolRate;
            public int    Pasos, ValidSteps;
            public double TotalVol;
            public double MaxTickVol;
            public double Cvd, BuyVol, SellVol;
            public double DeltaSlope, DeltaFirst, DeltaSecond;
            public int    NoMoveTicks, MaxLevelTicks;
            public double NoMoveVol;
            public double HeightTicks;
            public string TagRect, TagText;
            public bool   Drawn;
            public Brush  ColorZ;
            public string Reporte;
        }

        // State machine
        private int      streak, validSteps, dir, fails;
        private double   swH, swL;
        private readonly List<double> msList    = new List<double>();
        private readonly List<double> priceList = new List<double>();
        private readonly List<double> volList   = new List<double>();
        private readonly List<double> signList  = new List<double>();
        private double   totalVol;
        private DateTime tStart, tLast;
        private int      idCounter;
        private int      lastSide = 0;

        // Flow stream
        private long   flowBucket = long.MinValue;
        private long   flowStartMs;
        private double fO, fH, fL, fC, fVol, fBuy, fSell;
        private int    fTicks;

        // SQLite (buffered, concurrency-safe)
        private SQLiteConnection dbConn;
        private SQLiteCommand    flowCmd, zoneCmd;
        private bool   dbReady = false;
        private readonly List<object[]> zoneBuf = new List<object[]>();
        private readonly List<object[]> flowBuf = new List<object[]>();
        private long   lastFlushMs = 0;
        private const int BatchSize = 400;
        private const int FlushMs   = 2000;
        private const int MaxBuf    = 200000;

        private readonly List<Zone> zones = new List<Zone>();
        public IReadOnlyList<Zone> PublicZones { get { return zones; } }

        // Tunables NO expuestos como NinjaScriptProperty (no tocar la region autogenerada).
        public bool EnableFlowLog     { get; set; }
        public int  FlowBucketSeconds { get; set; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description              = "[FIX isDown-first] Detector HFT ES/MES con modo ABSORB + logger enriquecido (delta tick-rule, absorcion, flow). Escritura concurrente segura.";
                Name                     = "HFTZonesESPureV2Flat";
                Calculate                = Calculate.OnBarClose;
                IsOverlay                = true;
                DisplayInDataBox         = true;
                DrawOnPricePanel         = true;
                PaintPriceMarkers        = true;
                IsSuspendedWhileInactive = true;

                TickResolution           = 1;
                MinPasos                 = 10;
                MaxRangoTickPorVela      = 1;
                FallosTolerados          = 1;
                FiltroDireccionEstricto  = true;
                MinSweepTicks            = 5;
                MaxAvgMs                 = 15;
                MaxTotalMs               = 300;
                MaxPausaMs               = 50;
                MinVolumeRate            = 500;
                MinTotalVolume           = 200;
                PredatorAvgMs            = 3;
                UltraAvgMs               = 10;
                MostrarAbsorb            = true;
                MinAbsorbPasos           = 8;
                ColorAbsorb              = Brushes.MediumPurple;
                ColorAbsorbBull          = Brushes.OrangeRed;
                ColorAbsorbBear          = Brushes.LimeGreen;
                ExtensionDibujo          = 600;
                Opacidad                 = 30;
                MostrarTexto             = true;
                ColorPredator            = Brushes.Gold;
                ColorUltra               = Brushes.Silver;
                ColorBull                = Brushes.DodgerBlue;
                ColorBear                = Brushes.OrangeRed;
                ColorTexto               = Brushes.Silver;
                EnableDbLogging          = true;
                DbPath                   = @"C:\LoggerHFT\data\oraculo_espurev2flat_ES.sqlite";
                EnableFlowLog            = true;
                FlowBucketSeconds        = 1;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, TickResolution);
            }
            else if (State == State.DataLoaded)
            {
                ResetState();
                zones.Clear();
                idCounter = 0;
                lastSide  = 0;
                flowBucket = long.MinValue;
                fTicks = 0;
                if (EnableDbLogging) SetupDb();
            }
            else if (State == State.Terminated)
            {
                CloseDb();
            }
        }

        private void ResetState()
        {
            streak = 0; validSteps = 0; dir = 0; fails = 0;
            msList.Clear(); priceList.Clear(); volList.Clear(); signList.Clear();
            totalVol = 0;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress == 1)
            {
                if (CurrentBars[1] < 5) return;
                ProcesarSweeps();
                DibujarPendientes();
                return;
            }
            if (BarsInProgress != 0) return;
            if (CurrentBars[0] < 2) return;
            DibujarPendientes();
        }

        // ===================== STATE MACHINE + FLOW =====================
        private void ProcesarSweeps()
        {
            int ds = 1;
            if (CurrentBars[ds] < 1) return;

            double rng = (Highs[ds][0] - Lows[ds][0]) / TickSize;
            bool small = rng <= MaxRangoTickPorVela;
            double ms  = Times[ds][0].Subtract(Times[ds][1]).TotalMilliseconds;
            double vol = Volumes[ds][0];

            double op  = Opens[ds][0];
            double cl  = Closes[ds][0];
            double clP = Closes[ds][1];

            int side = cl > clP ? 1 : (cl < clP ? -1 : lastSide);
            if (side == 0) side = 1;
            lastSide = side;
            double signedVol = side * vol;

            if (EnableFlowLog) AccumFlow(Times[ds][0], cl, vol, side);

            bool isDown, isUp;
            if (FiltroDireccionEstricto)
            {
                isDown = small && cl <= clP && cl <= op;
                isUp   = small && cl >= clP && cl >= op;
            }
            else
            {
                isDown = small && cl <= clP;
                isUp   = small && cl >= clP;
            }

            if (dir != 0 && ms > MaxPausaMs)
            {
                Finalizar();
                dir = 0;
                return;
            }

            if (dir == 0)
            {
                // FIX isDown-first. Con el precio PLANO (cl == clP == op) isDown e
                // isUp son AMBOS true, y al evaluar isDown primero toda racha
                // arrancaba bajista. Medido sobre 23.863 zonas: 92% dir=-1,
                // identico en los tres buckets y los tres contratos.
                //
                // Un tick plano no tiene direccion: no inicia. Es la regla que las
                // notas de HFTZones2 ya piden: no arrancar en plano ni isDown-first.
                //
                // Solo se toca el INICIO. La continuacion queda igual: un tick plano
                // durante una racha no la contradice.
                bool plano = isDown && isUp;
                if (plano) { /* sin direccion: no inicia racha */ }
                else if (isDown) { dir = -1; Iniciar(ms, vol, cl, signedVol); }
                else if (isUp)   { dir =  1; Iniciar(ms, vol, cl, signedVol); }
            }
            else if (dir == -1)
            {
                if (isDown) { Continuar(ms, vol, cl, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    if (fails <= FallosTolerados) Continuar(ms, vol, cl, signedVol, false);
                    else Finalizar();
                }
            }
            else
            {
                if (isUp) { Continuar(ms, vol, cl, signedVol, true); fails = 0; }
                else
                {
                    fails++;
                    if (fails <= FallosTolerados) Continuar(ms, vol, cl, signedVol, false);
                    else Finalizar();
                }
            }
        }

        private void Iniciar(double ms, double vol, double cl, double signedVol)
        {
            int ds = 1;
            streak = 1; validSteps = 1; fails = 0;
            swH = Highs[ds][0]; swL = Lows[ds][0];
            msList.Clear();
            priceList.Clear(); volList.Clear(); signList.Clear();
            priceList.Add(cl); volList.Add(vol); signList.Add(signedVol);
            totalVol = vol;
            tStart = Times[ds][0];
            tLast  = Times[ds][0];
        }

        private void Continuar(double ms, double vol, double cl, double signedVol, bool valid)
        {
            int ds = 1;
            streak++;
            if (valid) validSteps++;
            swH = Math.Max(swH, Highs[ds][0]);
            swL = Math.Min(swL, Lows[ds][0]);
            msList.Add(ms);
            priceList.Add(cl); volList.Add(vol); signList.Add(signedVol);
            totalVol += vol;
            tLast = Times[ds][0];
        }

        private void Finalizar()
        {
            double sweepTicks = (swH - swL) / TickSize;
            bool isSweep  = sweepTicks >= MinSweepTicks;
            bool isAbsorb = !isSweep && MostrarAbsorb;
            int minPasosReq = isSweep ? MinPasos : MinAbsorbPasos;

            if (validSteps >= minPasosReq && (isSweep || isAbsorb))
            {
                double total = msList.Sum();
                int    nIntervals = msList.Count;
                double avgMs = total / Math.Max(1, nIntervals);
                double durationSec = Math.Max(total, 1.0) / 1000.0;
                double volRate = totalVol / durationSec;

                bool veloOk    = avgMs <= MaxAvgMs;
                bool durOk     = total <= MaxTotalMs;
                bool volOk     = volRate >= MinVolumeRate;
                bool volTotOk  = totalVol >= MinTotalVolume;

                if (veloOk && durOk && volOk && volTotOk)
                {
                    HFTBucket bucket; Brush col; string bucketTxt;
                    if (isAbsorb)
                    {
                        bucket = HFTBucket.Absorb;
                        // Placeholder — el color real se asigna abajo, después de calcular el CVD
                        col = ColorAbsorb;
                        bucketTxt = "ABSORB";
                    }
                    else
                    {
                        bucket = avgMs <= PredatorAvgMs ? HFTBucket.Predator
                               : avgMs <= UltraAvgMs    ? HFTBucket.Ultra : HFTBucket.Fast;
                        col = bucket == HFTBucket.Predator ? ColorPredator
                            : bucket == HFTBucket.Ultra    ? ColorUltra
                            : (dir == 1 ? ColorBull : ColorBear);
                        bucketTxt = bucket == HFTBucket.Predator ? "PRED"
                                  : bucket == HFTBucket.Ultra    ? "ULTRA"
                                  : (dir == 1 ? "BULL" : "BEAR");
                    }

                    double cvd = 0, buy = 0, sell = 0, maxTickVol = 0;
                    for (int i = 0; i < signList.Count; i++)
                    {
                        double sv = signList[i];
                        cvd += sv;
                        if (sv >= 0) buy += volList[i]; else sell += volList[i];
                        if (volList[i] > maxTickVol) maxTickVol = volList[i];
                    }

                    // Clasificar ABSORB: ¿las velas fueron para arriba o para abajo?
                    if (isAbsorb)
                    {
                        bool wentDown = priceList[priceList.Count - 1] < priceList[0];
                        col = wentDown ? ColorAbsorbBear : ColorAbsorbBull;
                        bucketTxt = wentDown ? "ABSORB_BEAR" : "ABSORB_BULL";
                    }

                    double slope = 0, dFirst = 0, dSecond = 0;
                    int nS = signList.Count;
                    if (nS >= 2)
                    {
                        double sumX = 0, sumY = 0, sumXY = 0, sumXX = 0, cum = 0;
                        for (int i = 0; i < nS; i++)
                        {
                            cum += signList[i];
                            sumX += i; sumY += cum; sumXY += i * cum; sumXX += (double)i * i;
                        }
                        double den = nS * sumXX - sumX * sumX;
                        if (Math.Abs(den) > 1e-9) slope = (nS * sumXY - sumX * sumY) / den;
                        int half = nS / 2;
                        for (int i = 0; i < nS; i++)
                        {
                            if (i < half) dFirst += signList[i]; else dSecond += signList[i];
                        }
                    }

                    int noMoveTicks = 0; double noMoveVol = 0;
                    var freq = new Dictionary<long, int>();
                    long prevTk = long.MinValue;
                    for (int i = 0; i < priceList.Count; i++)
                    {
                        long tk = (long)Math.Round(priceList[i] / TickSize);
                        if (i > 0 && tk == prevTk) { noMoveTicks++; noMoveVol += volList[i]; }
                        prevTk = tk;
                        int c; freq.TryGetValue(tk, out c); freq[tk] = c + 1;
                    }
                    int maxLevelTicks = 0;
                    foreach (var kv in freq) if (kv.Value > maxLevelTicks) maxLevelTicks = kv.Value;

                    int prim_start = BarsArray[0].GetBar(tStart);
                    int prim_end   = BarsArray[0].GetBar(tLast);
                    if (prim_start < 0) prim_start = Math.Max(0, CurrentBars[0] - streak);
                    if (prim_end < 0)   prim_end   = CurrentBars[0] - 1;
                    if (prim_end < prim_start) prim_end = prim_start;

                    string pasosTxt = (streak == validSteps)
                        ? validSteps.ToString()
                        : string.Format("{0}+{1}f", validSteps, streak - validSteps);

                    string txt = string.Format("[{0}] {1}p {2:F1}ms tot{3:F0}ms vR{4:F0} V{5:F0} h{6:F0}t d{7:F0}",
                        bucketTxt, pasosTxt, avgMs, total, volRate, totalVol, sweepTicks, cvd);

                    idCounter++;
                    string tag = "HFTV2_" + idCounter;

                    var z = new Zone
                    {
                        StartBar = prim_start, EndBar = prim_end,
                        StartTime = tStart, EndTime = tLast,
                        Upper = swH, Lower = swL, Direction = dir, Bucket = bucket,
                        AvgMs = avgMs, TotalMs = total, VolRate = volRate,
                        Pasos = streak, ValidSteps = validSteps, TotalVol = totalVol,
                        MaxTickVol = maxTickVol, Cvd = cvd, BuyVol = buy, SellVol = sell,
                        DeltaSlope = slope, DeltaFirst = dFirst, DeltaSecond = dSecond,
                        NoMoveTicks = noMoveTicks, NoMoveVol = noMoveVol, MaxLevelTicks = maxLevelTicks,
                        HeightTicks = sweepTicks,
                        TagRect = tag + "_R", TagText = tag + "_T", Drawn = false,
                        ColorZ = col, Reporte = txt
                    };
                    zones.Add(z);
                    if (EnableDbLogging) PersistZone(z);
                }
            }
            ResetState();
        }

        // ===================== DIBUJO =====================
        private void DibujarPendientes()
        {
            for (int i = 0; i < zones.Count; i++)
            {
                Zone z = zones[i];
                if (z.Drawn) continue;
                int barsAgoStart = CurrentBars[0] - z.StartBar;
                int barsAgoEnd   = CurrentBars[0] - z.EndBar;
                if (barsAgoStart < 0) continue;
                Draw.Rectangle(this, z.TagRect, false,
                    barsAgoStart, z.Upper, -ExtensionDibujo, z.Lower,
                    Brushes.Transparent, z.ColorZ, Opacidad);
                if (MostrarTexto)
                {
                    double tY = z.Direction == 1 ? z.Lower - (TickSize * 4) : z.Upper + (TickSize * 4);
                    int textBar = Math.Max(0, barsAgoEnd);
                    Draw.Text(this, z.TagText, z.Reporte, textBar, tY, ColorTexto);
                }
                z.Drawn = true;
            }
        }

        // ===================== FLOW STREAM =====================
        private void AccumFlow(DateTime t, double price, double vol, int side)
        {
            long ms = UnixMs(t);
            int  secs = Math.Max(1, FlowBucketSeconds);
            long bucket = (ms / 1000L) / secs;
            if (bucket != flowBucket)
            {
                if (flowBucket != long.MinValue && fTicks > 0) BufferFlow();
                flowBucket  = bucket;
                flowStartMs = bucket * secs * 1000L;
                fO = fH = fL = fC = price;
                fVol = 0; fBuy = 0; fSell = 0; fTicks = 0;
            }
            fC = price;
            if (price > fH) fH = price;
            if (price < fL) fL = price;
            fVol += vol;
            if (side > 0) fBuy += vol; else fSell += vol;
            fTicks++;
        }

        private void BufferFlow()
        {
            if (!dbReady) return;
            flowBuf.Add(new object[] { Instrument.FullName, flowStartMs, fO, fH, fL, fC,
                                       fVol, fBuy, fSell, fBuy - fSell, fTicks });
            if (flowBuf.Count >= BatchSize || (flowStartMs - lastFlushMs) >= FlushMs)
                FlushAll();
        }

        // ===================== SQLITE (buffered) =====================
        private void SetupDb()
        {
            try
            {
                string dir = Path.GetDirectoryName(DbPath);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                    Directory.CreateDirectory(dir);

                dbConn = new SQLiteConnection("Data Source=" + DbPath + ";Version=3;");
                dbConn.Open();
                using (var c = new SQLiteCommand(
                    "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;", dbConn))
                    c.ExecuteNonQuery();

                using (var cmd = new SQLiteCommand(ZonesSchema() + FlowSchema(), dbConn))
                    cmd.ExecuteNonQuery();

                // Migracion suave: si la tabla ya existia sin max_retro (data previa), la agrega.
                try { using (var mig = new SQLiteCommand("ALTER TABLE hft_zones ADD COLUMN max_retro REAL;", dbConn)) mig.ExecuteNonQuery(); }
                catch { /* la columna ya existe */ }

                EnsureUnique("hft_zones", "ux_hz", "instrument, start_ts");
                EnsureUnique("hft_flow",  "ux_hf", "instrument, bar_ts");

                zoneCmd = new SQLiteCommand(ZonesInsert(), dbConn);
                foreach (string p in ZoneParams()) zoneCmd.Parameters.Add(new SQLiteParameter(p));
                zoneCmd.Prepare();

                flowCmd = new SQLiteCommand(FlowInsert(), dbConn);
                foreach (string p in new[]{"@inst","@ts","@o","@h","@l","@c","@v","@bv","@sv","@d","@nt"})
                    flowCmd.Parameters.Add(new SQLiteParameter(p));
                flowCmd.Prepare();

                dbReady = true;
                lastFlushMs = 0;
            }
            catch (Exception ex)
            {
                dbReady = false;
                Print("[HFTLogger-ES] SetupDb: " + ex.Message);
            }
        }

        internal static string ZonesSchema()
        {
            return @"CREATE TABLE IF NOT EXISTS hft_zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT, instrument TEXT, start_ts INTEGER, end_ts INTEGER,
                bucket TEXT, dir INTEGER, price_upper REAL, price_lower REAL, price_mid REAL, height_ticks REAL,
                pasos INTEGER, valid_steps INTEGER, avg_ms REAL, total_ms REAL, vol_rate REAL, total_vol REAL,
                max_tick_vol REAL, cvd_sweep REAL, buy_vol REAL, sell_vol REAL, delta_slope REAL, delta_first REAL,
                delta_second REAL, no_move_ticks INTEGER, no_move_vol REAL, max_level_ticks INTEGER, tick_res INTEGER,
                max_retro REAL);
                CREATE INDEX IF NOT EXISTS idx_hz_ts ON hft_zones(start_ts);
                CREATE INDEX IF NOT EXISTS idx_hz_inst ON hft_zones(instrument);";
        }
        internal static string FlowSchema()
        {
            return @"CREATE TABLE IF NOT EXISTS hft_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT, instrument TEXT, bar_ts INTEGER, open REAL, high REAL,
                low REAL, close REAL, volume REAL, buy_vol REAL, sell_vol REAL, delta REAL, n_ticks INTEGER);
                CREATE INDEX IF NOT EXISTS idx_hf_ts ON hft_flow(instrument, bar_ts);";
        }
        internal static string ZonesInsert()
        {
            return @"INSERT OR IGNORE INTO hft_zones
                (instrument,start_ts,end_ts,bucket,dir,price_upper,price_lower,price_mid,height_ticks,pasos,valid_steps,
                 avg_ms,total_ms,vol_rate,total_vol,max_tick_vol,cvd_sweep,buy_vol,sell_vol,delta_slope,delta_first,
                 delta_second,no_move_ticks,no_move_vol,max_level_ticks,tick_res,max_retro)
                VALUES (@inst,@s,@e,@b,@dir,@pu,@pl,@pm,@ht,@p,@vs,@am,@tm,@vr,@tv,@mtv,@cvd,@buy,@sell,@dsl,@d1,@d2,@nmt,@nmv,@mlt,@tr,@mr)";
        }
        internal static string FlowInsert()
        {
            return @"INSERT OR IGNORE INTO hft_flow
                (instrument,bar_ts,open,high,low,close,volume,buy_vol,sell_vol,delta,n_ticks)
                VALUES (@inst,@ts,@o,@h,@l,@c,@v,@bv,@sv,@d,@nt)";
        }
        internal static string[] ZoneParams()
        {
            return new[]{"@inst","@s","@e","@b","@dir","@pu","@pl","@pm","@ht","@p","@vs","@am","@tm","@vr","@tv",
                         "@mtv","@cvd","@buy","@sell","@dsl","@d1","@d2","@nmt","@nmv","@mlt","@tr","@mr"};
        }

        private void EnsureUnique(string table, string idx, string cols)
        {
            try
            {
                using (var c = new SQLiteCommand("CREATE UNIQUE INDEX IF NOT EXISTS " + idx + " ON " + table + "(" + cols + ");", dbConn))
                    c.ExecuteNonQuery();
            }
            catch
            {
                try
                {
                    using (var c = new SQLiteCommand(
                        "DELETE FROM " + table + " WHERE id NOT IN (SELECT MIN(id) FROM " + table + " GROUP BY " + cols + ");" +
                        "CREATE UNIQUE INDEX IF NOT EXISTS " + idx + " ON " + table + "(" + cols + ");", dbConn))
                        c.ExecuteNonQuery();
                }
                catch (Exception ex) { Print("[HFTLogger] EnsureUnique " + table + ": " + ex.Message); }
            }
        }

        private void PersistZone(Zone z)
        {
            if (!dbReady) return;
            zoneBuf.Add(new object[] {
                Instrument.FullName, UnixMs(z.StartTime), UnixMs(z.EndTime), z.Bucket.ToString(), z.Direction,
                z.Upper, z.Lower, (z.Upper + z.Lower) / 2.0, z.HeightTicks, z.Pasos, z.ValidSteps,
                z.AvgMs, z.TotalMs, z.VolRate, z.TotalVol, z.MaxTickVol, z.Cvd, z.BuyVol, z.SellVol,
                z.DeltaSlope, z.DeltaFirst, z.DeltaSecond, z.NoMoveTicks, z.NoMoveVol, z.MaxLevelTicks,
                TickResolution, 0.0 });
            FlushAll();  // las zonas son raras: las persistimos enseguida
        }

        private void FlushAll()
        {
            if (!dbReady) return;
            if (zoneBuf.Count == 0 && flowBuf.Count == 0) return;
            SQLiteTransaction tx = null;
            try
            {
                tx = dbConn.BeginTransaction();
                if (zoneCmd != null)
                {
                    zoneCmd.Transaction = tx;
                    foreach (var r in zoneBuf)
                    {
                        for (int i = 0; i < r.Length; i++) zoneCmd.Parameters[i].Value = r[i];
                        zoneCmd.ExecuteNonQuery();
                    }
                }
                if (flowCmd != null)
                {
                    flowCmd.Transaction = tx;
                    foreach (var r in flowBuf)
                    {
                        for (int i = 0; i < r.Length; i++) flowCmd.Parameters[i].Value = r[i];
                        flowCmd.ExecuteNonQuery();
                    }
                }
                tx.Commit();
                zoneBuf.Clear(); flowBuf.Clear();
                lastFlushMs = flowStartMs;
            }
            catch (Exception ex)
            {
                try { if (tx != null) tx.Rollback(); } catch { }
                Print("[HFTLogger-ES] flush: " + ex.Message);
                if (zoneBuf.Count + flowBuf.Count > MaxBuf) { zoneBuf.Clear(); flowBuf.Clear(); }
            }
        }

        private void CloseDb()
        {
            try
            {
                if (EnableFlowLog && fTicks > 0) BufferFlow();
                FlushAll();
                if (flowCmd != null) { flowCmd.Dispose(); flowCmd = null; }
                if (zoneCmd != null) { zoneCmd.Dispose(); zoneCmd = null; }
                if (dbConn  != null) { dbConn.Close(); dbConn.Dispose(); dbConn = null; }
            }
            catch (Exception ex) { Print("[HFTLogger-ES] CloseDb: " + ex.Message); }
            dbReady = false;
        }

        private static long UnixMs(DateTime dt)
        {
            return new DateTimeOffset(dt.ToUniversalTime()).ToUnixTimeMilliseconds();
        }

        #region Properties
        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Tick Resolution (sub-serie)", Order=1, GroupName="0. Sub-serie",
            Description="ES: 1 (default, maxima granularidad).")]
        public int TickResolution { get; set; }

        [NinjaScriptProperty][Range(2, 100)]
        [Display(Name="Min pasos del sweep", Order=1, GroupName="A. Estructura", Description="ES: 8-12. Default 10.")]
        public int MinPasos { get; set; }

        [NinjaScriptProperty][Range(1, 20)]
        [Display(Name="Max rango tick por vela", Order=2, GroupName="A. Estructura", Description="ES 1-tick: 1.")]
        public int MaxRangoTickPorVela { get; set; }

        [NinjaScriptProperty][Range(0, 10)]
        [Display(Name="Fallos tolerados", Order=3, GroupName="A. Estructura", Description="ES: 1.")]
        public int FallosTolerados { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Filtro direccion estricto (cuerpo real)", Order=4, GroupName="A. Estructura")]
        public bool FiltroDireccionEstricto { get; set; }

        [NinjaScriptProperty][Range(0, 100)]
        [Display(Name="Min altura del sweep (ticks)", Order=5, GroupName="A. Estructura",
            Description="Por debajo = ABSORB. ES: 4-8.")]
        public int MinSweepTicks { get; set; }

        [NinjaScriptProperty][Range(1, 2000)]
        [Display(Name="Max avgMs (entre ticks)", Order=1, GroupName="B. Filtros temporales", Description="ES: 10-20ms.")]
        public int MaxAvgMs { get; set; }

        [NinjaScriptProperty][Range(50, 10000)]
        [Display(Name="Max totalMs (duracion total)", Order=2, GroupName="B. Filtros temporales", Description="ES: 200-500ms.")]
        public int MaxTotalMs { get; set; }

        [NinjaScriptProperty][Range(10, 5000)]
        [Display(Name="Max pausa entre ticks (ms)", Order=3, GroupName="B. Filtros temporales", Description="ES: 30-100ms.")]
        public int MaxPausaMs { get; set; }

        [NinjaScriptProperty][Range(0, 50000)]
        [Display(Name="Min velocidad volumen (contratos/seg)", Order=1, GroupName="C. Filtros volumen", Description="ES: 300-1000.")]
        public int MinVolumeRate { get; set; }

        [NinjaScriptProperty][Range(0, 100000)]
        [Display(Name="Min volumen total (contratos)", Order=2, GroupName="C. Filtros volumen", Description="ES: 100-500.")]
        public int MinTotalVolume { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Bucket PREDATOR avgMs <=", Order=1, GroupName="D. Buckets")]
        public int PredatorAvgMs { get; set; }

        [NinjaScriptProperty][Range(1, 200)]
        [Display(Name="Bucket ULTRA avgMs <=", Order=2, GroupName="D. Buckets")]
        public int UltraAvgMs { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar zonas ABSORB", Order=1, GroupName="DA. Absorcion")]
        public bool MostrarAbsorb { get; set; }

        [NinjaScriptProperty][Range(2, 100)]
        [Display(Name="Min pasos ABSORB", Order=2, GroupName="DA. Absorcion", Description="Default 8.")]
        public int MinAbsorbPasos { get; set; }

        [NinjaScriptProperty][Range(1, 5000)]
        [Display(Name="Extension dibujo (barras)", Order=1, GroupName="E. Visual")]
        public int ExtensionDibujo { get; set; }

        [NinjaScriptProperty][Range(1, 100)]
        [Display(Name="Opacidad", Order=2, GroupName="E. Visual")]
        public int Opacidad { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Mostrar etiqueta", Order=3, GroupName="E. Visual")]
        public bool MostrarTexto { get; set; }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color PREDATOR", Order=4, GroupName="E. Visual")]
        public Brush ColorPredator { get; set; }
        [Browsable(false)] public string ColorPredatorSerializable
        { get { return Serialize.BrushToString(ColorPredator); } set { ColorPredator = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ULTRA", Order=5, GroupName="E. Visual")]
        public Brush ColorUltra { get; set; }
        [Browsable(false)] public string ColorUltraSerializable
        { get { return Serialize.BrushToString(ColorUltra); } set { ColorUltra = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color bull (Fast)", Order=6, GroupName="E. Visual")]
        public Brush ColorBull { get; set; }
        [Browsable(false)] public string ColorBullSerializable
        { get { return Serialize.BrushToString(ColorBull); } set { ColorBull = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color bear (Fast)", Order=7, GroupName="E. Visual")]
        public Brush ColorBear { get; set; }
        [Browsable(false)] public string ColorBearSerializable
        { get { return Serialize.BrushToString(ColorBear); } set { ColorBear = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ABSORB (legacy)", Order=8, GroupName="E. Visual")]
        public Brush ColorAbsorb { get; set; }
        [Browsable(false)] public string ColorAbsorbSerializable
        { get { return Serialize.BrushToString(ColorAbsorb); } set { ColorAbsorb = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ABSORB Alcista (señal bajista)", Order=9, GroupName="E. Visual",
            Description="Rojo: absorción de compras agresivas = potencial reversión bajista.")]
        public Brush ColorAbsorbBull { get; set; }
        [Browsable(false)] public string ColorAbsorbBullSerializable
        { get { return Serialize.BrushToString(ColorAbsorbBull); } set { ColorAbsorbBull = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color ABSORB Bajista (señal alcista)", Order=10, GroupName="E. Visual",
            Description="Verde: absorción de ventas agresivas = potencial reversión alcista.")]
        public Brush ColorAbsorbBear { get; set; }
        [Browsable(false)] public string ColorAbsorbBearSerializable
        { get { return Serialize.BrushToString(ColorAbsorbBear); } set { ColorAbsorbBear = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty][XmlIgnore]
        [Display(Name="Color texto", Order=9, GroupName="E. Visual")]
        public Brush ColorTexto { get; set; }
        [Browsable(false)] public string ColorTextoSerializable
        { get { return Serialize.BrushToString(ColorTexto); } set { ColorTexto = Serialize.StringToBrush(value); } }

        [NinjaScriptProperty]
        [Display(Name="Enable DB Logging", Order=1, GroupName="F. Database")]
        public bool EnableDbLogging { get; set; }

        [NinjaScriptProperty]
        [Display(Name="DB Path", Order=2, GroupName="F. Database")]
        public string DbPath { get; set; }
        #endregion
    }
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private HFTZonesESPureV2Flat[] cacheHFTZonesESPureV2Flat;
		public HFTZonesESPureV2Flat HFTZonesESPureV2Flat(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorAbsorbBull, Brush colorAbsorbBear, Brush colorTexto, bool enableDbLogging, string dbPath)
		{
			return HFTZonesESPureV2Flat(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorAbsorbBull, colorAbsorbBear, colorTexto, enableDbLogging, dbPath);
		}

		public HFTZonesESPureV2Flat HFTZonesESPureV2Flat(ISeries<double> input, int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorAbsorbBull, Brush colorAbsorbBear, Brush colorTexto, bool enableDbLogging, string dbPath)
		{
			if (cacheHFTZonesESPureV2Flat != null)
				for (int idx = 0; idx < cacheHFTZonesESPureV2Flat.Length; idx++)
					if (cacheHFTZonesESPureV2Flat[idx] != null && cacheHFTZonesESPureV2Flat[idx].TickResolution == tickResolution && cacheHFTZonesESPureV2Flat[idx].MinPasos == minPasos && cacheHFTZonesESPureV2Flat[idx].MaxRangoTickPorVela == maxRangoTickPorVela && cacheHFTZonesESPureV2Flat[idx].FallosTolerados == fallosTolerados && cacheHFTZonesESPureV2Flat[idx].FiltroDireccionEstricto == filtroDireccionEstricto && cacheHFTZonesESPureV2Flat[idx].MinSweepTicks == minSweepTicks && cacheHFTZonesESPureV2Flat[idx].MaxAvgMs == maxAvgMs && cacheHFTZonesESPureV2Flat[idx].MaxTotalMs == maxTotalMs && cacheHFTZonesESPureV2Flat[idx].MaxPausaMs == maxPausaMs && cacheHFTZonesESPureV2Flat[idx].MinVolumeRate == minVolumeRate && cacheHFTZonesESPureV2Flat[idx].MinTotalVolume == minTotalVolume && cacheHFTZonesESPureV2Flat[idx].PredatorAvgMs == predatorAvgMs && cacheHFTZonesESPureV2Flat[idx].UltraAvgMs == ultraAvgMs && cacheHFTZonesESPureV2Flat[idx].MostrarAbsorb == mostrarAbsorb && cacheHFTZonesESPureV2Flat[idx].MinAbsorbPasos == minAbsorbPasos && cacheHFTZonesESPureV2Flat[idx].ExtensionDibujo == extensionDibujo && cacheHFTZonesESPureV2Flat[idx].Opacidad == opacidad && cacheHFTZonesESPureV2Flat[idx].MostrarTexto == mostrarTexto && cacheHFTZonesESPureV2Flat[idx].ColorPredator == colorPredator && cacheHFTZonesESPureV2Flat[idx].ColorUltra == colorUltra && cacheHFTZonesESPureV2Flat[idx].ColorBull == colorBull && cacheHFTZonesESPureV2Flat[idx].ColorBear == colorBear && cacheHFTZonesESPureV2Flat[idx].ColorAbsorb == colorAbsorb && cacheHFTZonesESPureV2Flat[idx].ColorAbsorbBull == colorAbsorbBull && cacheHFTZonesESPureV2Flat[idx].ColorAbsorbBear == colorAbsorbBear && cacheHFTZonesESPureV2Flat[idx].ColorTexto == colorTexto && cacheHFTZonesESPureV2Flat[idx].EnableDbLogging == enableDbLogging && cacheHFTZonesESPureV2Flat[idx].DbPath == dbPath && cacheHFTZonesESPureV2Flat[idx].EqualsInput(input))
						return cacheHFTZonesESPureV2Flat[idx];
			return CacheIndicator<HFTZonesESPureV2Flat>(new HFTZonesESPureV2Flat(){ TickResolution = tickResolution, MinPasos = minPasos, MaxRangoTickPorVela = maxRangoTickPorVela, FallosTolerados = fallosTolerados, FiltroDireccionEstricto = filtroDireccionEstricto, MinSweepTicks = minSweepTicks, MaxAvgMs = maxAvgMs, MaxTotalMs = maxTotalMs, MaxPausaMs = maxPausaMs, MinVolumeRate = minVolumeRate, MinTotalVolume = minTotalVolume, PredatorAvgMs = predatorAvgMs, UltraAvgMs = ultraAvgMs, MostrarAbsorb = mostrarAbsorb, MinAbsorbPasos = minAbsorbPasos, ExtensionDibujo = extensionDibujo, Opacidad = opacidad, MostrarTexto = mostrarTexto, ColorPredator = colorPredator, ColorUltra = colorUltra, ColorBull = colorBull, ColorBear = colorBear, ColorAbsorb = colorAbsorb, ColorAbsorbBull = colorAbsorbBull, ColorAbsorbBear = colorAbsorbBear, ColorTexto = colorTexto, EnableDbLogging = enableDbLogging, DbPath = dbPath }, input, ref cacheHFTZonesESPureV2Flat);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.HFTZonesESPureV2Flat HFTZonesESPureV2Flat(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorAbsorbBull, Brush colorAbsorbBear, Brush colorTexto, bool enableDbLogging, string dbPath)
		{
			return indicator.HFTZonesESPureV2Flat(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorAbsorbBull, colorAbsorbBear, colorTexto, enableDbLogging, dbPath);
		}

		public Indicators.HFTZonesESPureV2Flat HFTZonesESPureV2Flat(ISeries<double> input , int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorAbsorbBull, Brush colorAbsorbBear, Brush colorTexto, bool enableDbLogging, string dbPath)
		{
			return indicator.HFTZonesESPureV2Flat(input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorAbsorbBull, colorAbsorbBear, colorTexto, enableDbLogging, dbPath);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.HFTZonesESPureV2Flat HFTZonesESPureV2Flat(int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorAbsorbBull, Brush colorAbsorbBear, Brush colorTexto, bool enableDbLogging, string dbPath)
		{
			return indicator.HFTZonesESPureV2Flat(Input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorAbsorbBull, colorAbsorbBear, colorTexto, enableDbLogging, dbPath);
		}

		public Indicators.HFTZonesESPureV2Flat HFTZonesESPureV2Flat(ISeries<double> input , int tickResolution, int minPasos, int maxRangoTickPorVela, int fallosTolerados, bool filtroDireccionEstricto, int minSweepTicks, int maxAvgMs, int maxTotalMs, int maxPausaMs, int minVolumeRate, int minTotalVolume, int predatorAvgMs, int ultraAvgMs, bool mostrarAbsorb, int minAbsorbPasos, int extensionDibujo, int opacidad, bool mostrarTexto, Brush colorPredator, Brush colorUltra, Brush colorBull, Brush colorBear, Brush colorAbsorb, Brush colorAbsorbBull, Brush colorAbsorbBear, Brush colorTexto, bool enableDbLogging, string dbPath)
		{
			return indicator.HFTZonesESPureV2Flat(input, tickResolution, minPasos, maxRangoTickPorVela, fallosTolerados, filtroDireccionEstricto, minSweepTicks, maxAvgMs, maxTotalMs, maxPausaMs, minVolumeRate, minTotalVolume, predatorAvgMs, ultraAvgMs, mostrarAbsorb, minAbsorbPasos, extensionDibujo, opacidad, mostrarTexto, colorPredator, colorUltra, colorBull, colorBear, colorAbsorb, colorAbsorbBull, colorAbsorbBear, colorTexto, enableDbLogging, dbPath);
		}
	}
}

#endregion
