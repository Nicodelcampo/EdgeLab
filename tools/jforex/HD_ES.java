package jforex;

import com.dukascopy.api.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * Descarga histórica rápida (EdgeLab, 2026-10-04). Pide a la API de historial de JForex rangos de UN DÍA completo
 * (no hora por hora) y escribe archivos binarios por día en E:. Reanuda: los días ya completos no se vuelven a pedir.
 *
 * Ticks:  <out>\<INST>\ticks\YYYY-MM-DD.bin   registros big-endian 32 bytes: long time_ms, double bid, double ask,
 *         float bid_vol, float ask_vol
 * M1:     <out>\<INST>\m1_bid\YYYY-MM-DD.bin y m1_ask\...  registros 44 bytes: long time_ms, double open, high, low,
 *         close, float volume   (las velas M1 de Dukascopy se etiquetan en UTC, inicio de la vela)
 * Tiempos: <out>\<INST>\timings.csv  (día, tipo, registros, ms) para la tabla de rendimiento.
 * Los archivos se escriben como .part y se renombran al terminar: un .bin existente = día completo.
 */
public class HD_ES implements IStrategy {
    @Configurable("Instrumento") public Instrument instrument = Instrument.USA500IDXUSD;
    @Configurable("Desde (UTC, yyyy-MM-dd)") public String fromDay = "2023-01-01";
    @Configurable("Hasta inclusive (UTC, yyyy-MM-dd)") public String toDay = "2026-09-30";
    @Configurable("Carpeta de salida") public String outDir = "E:\\dukascopy";
    @Configurable("Bajar ticks") public boolean doTicks = true;
    @Configurable("Bajar M1 bid/ask") public boolean doM1 = true;

    private IHistory history;
    private IConsole console;
    private IContext context;

    @Override
    public void onStart(IContext ctx) throws JFException {
        context = ctx; history = ctx.getHistory(); console = ctx.getConsole();
        console.getOut().println("HistDownloader v3 (se puede detener) " + fromDay + " -> " + toDay);
        ctx.setSubscribedInstruments(java.util.Collections.singleton(instrument), true);   // el historial exige suscripción
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd");
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        String inst = instrument.name().replace("/", "");
        File base = new File(outDir, inst);
        new File(base, "ticks").mkdirs(); new File(base, "m1_bid").mkdirs(); new File(base, "m1_ask").mkdirs();
        try {
            long d0 = f.parse(fromDay).getTime(), d1 = f.parse(toDay).getTime();
            long t0 = System.currentTimeMillis(); int dias = 0;
            for (long day = d0; day <= d1; day += 86400000L) {
                if (context.isStopped()) { console.getOut().println("DETENIDA por el usuario en " + f.format(new Date(day))); break; }
                String ds = f.format(new Date(day));
                Calendar c = Calendar.getInstance(TimeZone.getTimeZone("UTC")); c.setTimeInMillis(day);
                if (c.get(Calendar.DAY_OF_WEEK) == Calendar.SATURDAY) continue;      // sábado UTC: mercado cerrado
                if (doTicks) bajarTicks(base, ds, day);
                if (doM1) { bajarM1(base, ds, day, OfferSide.BID, "m1_bid"); bajarM1(base, ds, day, OfferSide.ASK, "m1_ask"); }
                dias++;
                console.getOut().println(inst + " " + ds + " listo (" + dias + " días, " + (System.currentTimeMillis() - t0) / 1000 + " s)");
            }
            console.getOut().println("FIN " + inst + ": " + dias + " días en " + (System.currentTimeMillis() - t0) / 1000 + " s");
        } catch (Exception e) {
            console.getErr().println("ERROR: " + e);
        }
        ctx.stop();
    }

    private void bajarTicks(File base, String ds, long day) throws Exception {
        File fin = new File(base, "ticks\\" + ds + ".bin");
        if (fin.exists() && fin.length() > 0) return;
        File part = new File(base, "ticks\\" + ds + ".bin.part");
        long t = System.currentTimeMillis(); long n = 0; boolean ok = true;
        DataOutputStream out = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(part), 1 << 20));
        try {
            for (int h = 0; h < 24; h++) {                       // de a una hora: getTicks es sincrónico y no satura la memoria
                if (context.isStopped()) { ok = false; break; }   // se frena enseguida; el día queda .part y se rehace
                long a = day + h * 3600000L;
                List<ITick> ticks = history.getTicks(instrument, a, a + 3600000L - 1);
                for (ITick k : ticks) {
                    out.writeLong(k.getTime()); out.writeDouble(k.getBid()); out.writeDouble(k.getAsk());
                    out.writeFloat((float) k.getBidVolume()); out.writeFloat((float) k.getAskVolume()); n++;
                }
            }
        } catch (Exception e) { ok = false; console.getErr().println("ticks " + ds + ": " + e); }
        out.close();
        cerrar(part, fin, ok && n > 0, base, ds, "ticks", n, System.currentTimeMillis() - t);
    }

    private void bajarM1(File base, String ds, long day, OfferSide side, String dir) throws Exception {
        File fin = new File(base, dir + "\\" + ds + ".bin");
        if (fin.exists() && fin.length() > 0) return;
        File part = new File(base, dir + "\\" + ds + ".bin.part");
        long t = System.currentTimeMillis(); long n = 0; boolean ok = true;
        DataOutputStream out = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(part), 1 << 16));
        try {
            List<IBar> bars = history.getBars(instrument, Period.ONE_MIN, side, Filter.NO_FILTER, day, day + 86400000L - 60000L);
            for (IBar x : bars) {
                out.writeLong(x.getTime()); out.writeDouble(x.getOpen()); out.writeDouble(x.getHigh()); out.writeDouble(x.getLow());
                out.writeDouble(x.getClose()); out.writeFloat((float) x.getVolume()); n++;
            }
        } catch (Exception e) { ok = false; console.getErr().println(dir + " " + ds + ": " + e); }
        out.close();
        cerrar(part, fin, ok && n > 0, base, ds, dir, n, System.currentTimeMillis() - t);
    }

    private LoadingProgressListener progreso(final boolean[] ok) {
        return new LoadingProgressListener() {
            public void dataLoaded(long start, long end, long current, String info) {}
            public void loadingFinished(boolean all, long start, long end, long current) { if (!all) ok[0] = false; }
            public boolean stopJob() { return false; }
        };
    }

    private void cerrar(File part, File fin, boolean ok, File base, String ds, String tipo, long n, long ms) throws IOException {
        try (FileWriter w = new FileWriter(new File(base, "timings.csv"), true)) {
            w.write(ds + "," + tipo + "," + n + "," + ms + "," + (ok ? "ok" : "incompleto") + "\n");
        }
        if (ok) { if (fin.exists()) fin.delete(); if (!part.renameTo(fin)) console.getErr().println("no se pudo renombrar " + part); }
        else console.getErr().println(tipo + " " + ds + " INCOMPLETO o vacío: queda .part y se reintenta en la próxima corrida");
    }

    public void onTick(Instrument i, ITick t) {}
    public void onBar(Instrument i, Period p, IBar a, IBar b) {}
    public void onMessage(IMessage m) {}
    public void onAccount(IAccount a) {}
    public void onStop() {}
}
