package jforex;

import com.dukascopy.api.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * HDAUTO_SPOT_NOV (EdgeLab, 2026-11-24): descarga en 1 clic los ticks faltantes de
 * USATECHIDXUSD, USA500IDXUSD y XAUUSD desde 2026-11-16 hasta ayer (UTC)
 * directo en E:\dukascopy_HOLDOUT_SELLADO\<INST>\ticks\YYYY-MM-DD.bin
 */
public class HDAUTO_SPOT_NOV implements IStrategy {
    @Configurable("Desde (UTC, yyyy-MM-dd)") public String desdeDia = "2026-11-16";
    @Configurable("Hasta inclusive (vacio = ayer UTC)") public String hastaDia = "";
    @Configurable("Carpeta de salida base") public String outDir = "E:\\dukascopy";

    private static final Instrument[] INSTS = new Instrument[]{
        Instrument.USATECHIDXUSD,
        Instrument.USA500IDXUSD,
        Instrument.XAUUSD
    };

    private IHistory history;
    private IConsole console;
    private IContext context;

    @Override
    public void onStart(IContext ctx) throws JFException {
        context = ctx;
        history = ctx.getHistory();
        console = ctx.getConsole();
        ctx.setSubscribedInstruments(new HashSet<Instrument>(Arrays.asList(INSTS)), true);

        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd");
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        try {
            long hoy = f.parse(f.format(new Date())).getTime();
            long d0 = f.parse(desdeDia.trim()).getTime();
            long d1 = (hastaDia != null && hastaDia.trim().length() > 0)
                ? f.parse(hastaDia.trim()).getTime()
                : (hoy - 86400000L);

            console.getOut().println("HDAUTO_SPOT_NOV: descargando ticks " + f.format(new Date(d0))
                + " -> " + f.format(new Date(d1)) + " para USATECH, USA500 y XAUUSD");

            for (Instrument instObj : INSTS) {
                if (context.isStopped()) break;
                String inst = instObj.name().replace("/", "");
                File base = new File(outDir + "_HOLDOUT_SELLADO", inst);
                new File(base, "ticks").mkdirs();
                int ok = 0, sinDatos = 0, err = 0;

                for (long day = d0; day <= d1; day += 86400000L) {
                    if (context.isStopped()) { console.getOut().println("DETENIDA por usuario"); break; }
                    Calendar c = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
                    c.setTimeInMillis(day);
                    if (c.get(Calendar.DAY_OF_WEEK) == Calendar.SATURDAY) continue;
                    String ds = f.format(new Date(day));
                    int r = bajarDia(instObj, base, ds, day);
                    if (r == 1) ok++; else if (r == 0) sinDatos++; else err++;
                    console.getOut().println(inst + " " + ds + " -> " + (r == 1 ? "OK" : r == 0 ? "SIN_DATOS" : "ERROR"));
                }
                console.getOut().println("RESUMEN " + inst + " | ok=" + ok + " | sin_datos=" + sinDatos + " | err=" + err);
            }
            console.getOut().println("HDAUTO_SPOT_NOV FINALIZADA.");
        } catch (Exception e) {
            console.getErr().println("ERROR HDAUTO_SPOT_NOV: " + e);
        }
        ctx.stop();
    }

    private int bajarDia(Instrument instObj, File base, String ds, long day) {
        File fin = new File(base, "ticks\\" + ds + ".bin");
        if (fin.exists() && fin.length() > 0) return 1;
        File part = new File(base, "ticks\\" + ds + ".bin.part");
        for (int intento = 0; intento < 3; intento++) {
            if (context.isStopped()) return -1;
            long n = 0;
            try {
                DataOutputStream out = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(part), 1 << 20));
                try {
                    for (int h = 0; h < 24; h++) {
                        if (context.isStopped()) throw new Exception("detenida");
                        long a = day + h * 3600000L;
                        List<ITick> ticks = history.getTicks(instObj, a, a + 3600000L - 1);
                        for (ITick k : ticks) {
                            out.writeLong(k.getTime());
                            out.writeDouble(k.getBid());
                            out.writeDouble(k.getAsk());
                            out.writeFloat((float) k.getBidVolume());
                            out.writeFloat((float) k.getAskVolume());
                            n++;
                        }
                    }
                } finally {
                    out.close();
                }
                if (n > 0) {
                    if (fin.exists()) fin.delete();
                    if (!part.renameTo(fin)) throw new IOException("rename fallo: " + part);
                    return 1;
                }
                part.delete();
                return 0;
            } catch (Exception e) {
                console.getErr().println(instObj + " " + ds + " intento " + (intento + 1) + "/3: " + e);
                try { Thread.sleep(intento == 0 ? 5000 : 15000); } catch (InterruptedException ie) { return -1; }
            }
        }
        return -1;
    }

    public void onTick(Instrument i, ITick t) {}
    public void onBar(Instrument i, Period p, IBar a, IBar b) {}
    public void onMessage(IMessage m) {}
    public void onAccount(IAccount a) {}
    public void onStop() {}
}
