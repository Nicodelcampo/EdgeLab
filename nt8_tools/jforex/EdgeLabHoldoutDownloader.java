package jforex;

import com.dukascopy.api.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * EdgeLabHoldoutDownloader (2026-11-15)
 * -------------------------------------
 * Descarga en una sola corrida los ticks faltantes del holdout de Dukascopy
 * para todos los simbolos de la canasta spot de EdgeLab:
 *   USATECHIDXUSD, USA500IDXUSD, USA30IDXUSD, XAUUSD, EURUSD, GBPUSD, USDJPY
 *
 * Formato de salida compatible 1:1 con `tools/dukascopy_descarga.py::leer_jforex_bin`
 * y `edgelab/research/fuentes_ticks.py::bloques_spot_sellado`:
 *   - Binario big-endian de 32 bytes por tick en:
 *       <outDir>\<SIMBOLO>\ticks\YYYY-MM-DD.bin
 *     (long time_ms, double bid, double ask, float bid_vol, float ask_vol)
 *   - Opcionalmente CSV por dia en:
 *       <outDir>\<SIMBOLO>\csv\YYYY-MM-DD.csv
 *     (time_utc_ns,bid,ask,bid_vol,ask_vol)
 *
 * Escribe cada dia como `.part` y lo renombra al terminar: si un `.bin` ya existe y
 * tiene > 0 bytes, lo salta automaticamente (reanudacion segura).
 * Salta sabados UTC (mercado cerrado en Dukascopy).
 */
public class EdgeLabHoldoutDownloader implements IStrategy {

    @Configurable("Simbolos separados por coma (vacio = los 7 de EdgeLab)")
    public String symbolsCsv = "USATECHIDXUSD,USA500IDXUSD,USA30IDXUSD,XAUUSD,EURUSD,GBPUSD,USDJPY";

    @Configurable("Desde UTC inclusive (yyyy-MM-dd)")
    public String fromDay = "2026-10-29";

    @Configurable("Hasta UTC inclusive (yyyy-MM-dd)")
    public String toDay = "2026-11-15";

    @Configurable("Carpeta de salida")
    public String outDir = "C:\\EdgeLab\\jforex_holdout";

    @Configurable("Escribir .bin de 32B (formato nativo EdgeLab)")
    public boolean writeBin = true;

    @Configurable("Escribir .csv (time_utc_ns,bid,ask,bid_vol,ask_vol)")
    public boolean writeCsv = false;

    private IContext context;
    private IHistory history;
    private IConsole console;

    @Override
    public void onStart(IContext ctx) throws JFException {
        this.context = ctx;
        this.history = ctx.getHistory();
        this.console = ctx.getConsole();

        List<Instrument> instruments = resolveInstruments(symbolsCsv);
        if (instruments.isEmpty()) {
            console.getErr().println("EdgeLabHoldoutDownloader: ningun instrumento valido en '" + symbolsCsv + "'");
            ctx.stop();
            return;
        }

        Set<Instrument> subSet = new LinkedHashSet<Instrument>(instruments);
        console.getOut().println("EdgeLabHoldoutDownloader: suscribiendo " + subSet.size() + " instrumentos...");
        ctx.setSubscribedInstruments(subSet, true);

        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd");
        f.setTimeZone(TimeZone.getTimeZone("UTC"));

        long d0;
        long d1;
        try {
            d0 = f.parse(fromDay.trim()).getTime();
            d1 = f.parse(toDay.trim()).getTime();
        } catch (Exception e) {
            console.getErr().println("EdgeLabHoldoutDownloader: fechas invalidas (" + fromDay + " -> " + toDay + "): " + e);
            ctx.stop();
            return;
        }

        long tGlobal = System.currentTimeMillis();
        console.getOut().println("EdgeLabHoldoutDownloader: iniciando descarga UTC [" + fromDay + " .. " + toDay + "] hacia " + outDir);

        for (Instrument inst : instruments) {
            if (context.isStopped()) break;
            String instName = inst.name().replace("/", "");
            File base = new File(outDir, instName);
            if (writeBin) new File(base, "ticks").mkdirs();
            if (writeCsv) new File(base, "csv").mkdirs();

            long tInst = System.currentTimeMillis();
            int diasOk = 0;
            long totalTicksInst = 0;

            for (long day = d0; day <= d1; day += 86400_000L) {
                if (context.isStopped()) {
                    console.getOut().println("DETENIDA por usuario en " + instName + " " + f.format(new Date(day)));
                    break;
                }
                Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
                cal.setTimeInMillis(day);
                if (cal.get(Calendar.DAY_OF_WEEK) == Calendar.SATURDAY) {
                    continue; // Sabado UTC: mercado cerrado
                }
                String ds = f.format(new Date(day));
                long nTicks = bajarDia(inst, instName, base, ds, day);
                if (nTicks >= 0) {
                    diasOk++;
                    totalTicksInst += nTicks;
                }
            }
            long elapsedSec = (System.currentTimeMillis() - tInst) / 1000L;
            console.getOut().println("== FIN " + instName + ": " + diasOk + " dias procesados, "
                    + totalTicksInst + " ticks nuevos en " + elapsedSec + " s ==");
        }

        long totalSec = (System.currentTimeMillis() - tGlobal) / 1000L;
        console.getOut().println("EdgeLabHoldoutDownloader COMPLETADO en " + totalSec + " s. Carpeta: " + outDir);
        ctx.stop();
    }

    private List<Instrument> resolveInstruments(String csv) {
        List<Instrument> list = new ArrayList<Instrument>();
        String raw = (csv == null || csv.trim().isEmpty())
                ? "USATECHIDXUSD,USA500IDXUSD,USA30IDXUSD,XAUUSD,EURUSD,GBPUSD,USDJPY"
                : csv;
        for (String tok : raw.split(",")) {
            String s = tok.trim().toUpperCase(Locale.ROOT).replace("/", "").replace(".", "");
            if (s.isEmpty()) continue;
            if ("USATECH".equals(s) || "NQ".equals(s)) s = "USATECHIDXUSD";
            else if ("USA500".equals(s) || "ES".equals(s)) s = "USA500IDXUSD";
            else if ("USA30".equals(s) || "YM".equals(s)) s = "USA30IDXUSD";
            else if ("XAU".equals(s) || "GOLD".equals(s)) s = "XAUUSD";
            try {
                Instrument inst = Instrument.valueOf(s);
                if (!list.contains(inst)) list.add(inst);
            } catch (IllegalArgumentException e) {
                Instrument inst = Instrument.fromString(tok.trim());
                if (inst != null && !list.contains(inst)) list.add(inst);
                else console.getErr().println("Simbolo desconocido ignorado: " + tok);
            }
        }
        return list;
    }

    private long bajarDia(Instrument inst, String instName, File base, String ds, long dayStartMs) {
        File finBin = new File(new File(base, "ticks"), ds + ".bin");
        File finCsv = new File(new File(base, "csv"), ds + ".csv");

        boolean needBin = writeBin && (!finBin.exists() || finBin.length() == 0);
        boolean needCsv = writeCsv && (!finCsv.exists() || finCsv.length() == 0);
        if (!needBin && !needCsv) {
            console.getOut().println("[SKIP] " + instName + " " + ds + " ya existe.");
            return 0L;
        }

        File partBin = new File(new File(base, "ticks"), ds + ".bin.part");
        File partCsv = new File(new File(base, "csv"), ds + ".csv.part");

        long t0 = System.currentTimeMillis();
        long count = 0L;
        boolean ok = true;

        DataOutputStream outBin = null;
        BufferedWriter outCsv = null;
        try {
            if (needBin) {
                outBin = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(partBin), 1 << 20));
            }
            if (needCsv) {
                outCsv = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(partCsv), "UTF-8"), 1 << 20);
                outCsv.write("time_utc_ns,bid,ask,bid_vol,ask_vol\n");
            }

            for (int h = 0; h < 24; h++) {
                if (context.isStopped()) {
                    ok = false;
                    break;
                }
                long a = dayStartMs + h * 3600_000L;
                long b = a + 3600_000L - 1L;
                List<ITick> ticks = history.getTicks(inst, a, b);
                if (ticks == null || ticks.isEmpty()) continue;

                for (ITick k : ticks) {
                    long ms = k.getTime();
                    double bid = k.getBid();
                    double ask = k.getAsk();
                    float bv = (float) k.getBidVolume();
                    float av = (float) k.getAskVolume();
                    if (outBin != null) {
                        outBin.writeLong(ms);
                        outBin.writeDouble(bid);
                        outBin.writeDouble(ask);
                        outBin.writeFloat(bv);
                        outBin.writeFloat(av);
                    }
                    if (outCsv != null) {
                        long ns = ms * 1_000_000L;
                        outCsv.write(Long.toString(ns));
                        outCsv.write(',');
                        outCsv.write(Double.toString(bid));
                        outCsv.write(',');
                        outCsv.write(Double.toString(ask));
                        outCsv.write(',');
                        outCsv.write(Float.toString(bv));
                        outCsv.write(',');
                        outCsv.write(Float.toString(av));
                        outCsv.write('\n');
                    }
                    count++;
                }
            }
        } catch (Exception e) {
            ok = false;
            console.getErr().println("Error en " + instName + " " + ds + ": " + e);
        } finally {
            try { if (outBin != null) outBin.close(); } catch (IOException ignore) {}
            try { if (outCsv != null) outCsv.close(); } catch (IOException ignore) {}
        }

        long elapsedMs = System.currentTimeMillis() - t0;
        try (FileWriter w = new FileWriter(new File(base, "timings.csv"), true)) {
            w.write(ds + ",ticks," + count + "," + elapsedMs + "," + (ok ? "ok" : "error") + "\n");
        } catch (IOException ignore) {}

        if (ok && count > 0) {
            if (needBin) {
                if (finBin.exists()) finBin.delete();
                if (!partBin.renameTo(finBin)) console.getErr().println("No se pudo renombrar " + partBin);
            }
            if (needCsv) {
                if (finCsv.exists()) finCsv.delete();
                if (!partCsv.renameTo(finCsv)) console.getErr().println("No se pudo renombrar " + partCsv);
            }
            console.getOut().println("[OK] " + instName + " " + ds + " -> " + count + " ticks (" + (elapsedMs / 1000.0) + " s)");
            return count;
        } else {
            if (partBin.exists()) partBin.delete();
            if (partCsv.exists()) partCsv.delete();
            if (ok && count == 0) {
                console.getOut().println("[VACIO] " + instName + " " + ds + " (0 ticks)");
                return 0L;
            }
            return -1L;
        }
    }

    @Override public void onTick(Instrument instrument, ITick tick) throws JFException {}
    @Override public void onBar(Instrument instrument, Period period, IBar askBar, IBar bidBar) throws JFException {}
    @Override public void onMessage(IMessage message) throws JFException {}
    @Override public void onAccount(IAccount account) throws JFException {}
    @Override public void onStop() throws JFException {}
}

