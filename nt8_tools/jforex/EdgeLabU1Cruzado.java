package jforex;

import com.dukascopy.api.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * EdgeLab U1-CRUZADO, señal CAUSAL sobre USATECH y EJECUCIÓN REAL (2026-11-03).
 *
 * Señal: port 1:1 de `edgelab/research/u1_cruzado.py::senales` (núcleo `U1Nucleo` abajo, sin cambios; paridad con
 * `tools/paridad_jforex_u1.py`).
 *
 * Ejecución, la misma regla que el papel (`u1_cruzado_papel.py`, E1A/T3/S3 con tope 3×):
 *   - la señal sale al CIERRE de la vela M1; la orden es A MERCADO en ese momento (llena en el primer tick siguiente, con el spread y el
 *     slippage reales del motor de JForex: no se simula ningún precio);
 *   - lado: lado = 1 (precio arriba del área) -> VENTA; lado = -1 -> COMPRA;
 *   - TP: borde lejano del área (T3) o cercano (T1), configurable; SL: 1 pip más allá del extremo E, con tope de 3 × la distancia al TP;
 *     el SL y el TP se calculan con el precio de LLENADO real (si el llenado deja el TP detrás, la orden se cierra y se registra);
 *   - SL y TP quedan en el servidor (se disparan con bid/ask como en una cuenta real);
 *   - una posición a la vez (configurable), sin señales del calentamiento, sólo dentro del rango [Desde, Hasta) configurado;
 *   - opcional: cierre forzado a una hora fija (hora de Nueva York) y no entrar en los últimos minutos antes.
 * Archivos (carpeta de JForex): ticks_*.csv y senales_U1_*.csv (como antes) y operaciones_U1_*.csv (una fila por operación cerrada:
 * entrada y salida reales, R neto = resultado / riesgo inicial en precio).
 */
public class EdgeLabU1Cruzado implements IStrategy {
    @Configurable("Instrumento (sensor y ejecución)") public Instrument instrument = Instrument.USATECHIDXUSD;
    @Configurable("Calentamiento (horas de ticks antes del inicio)") public int warmupHoras = 48;
    @Configurable("Desde (yyyy-MM-dd HH:mm, UTC; vacío = sin límite)") public String desde = "";
    @Configurable("Hasta (yyyy-MM-dd HH:mm, UTC; vacío = sin límite)") public String hasta = "";
    @Configurable("Operar (false = sólo registrar señales)") public boolean operar = true;
    @Configurable("Cantidad (millones de unidades; CFD índice: 0.001 = 1 contrato)") public double cantidad = 0.001;
    @Configurable("Objetivo: true = borde lejano (T3), false = cercano (T1)") public boolean objetivoLejano = true;
    @Configurable("Tope del stop (múltiplos de la distancia al TP; 0 = sin tope)") public double topeMult = 3.0;
    @Configurable("Slippage máximo (pips; 0 = cualquiera)") public double slippagePips = 0;
    @Configurable("Máximo de posiciones abiertas") public int maxPosiciones = 1;
    @Configurable("Cierre forzado (HH:mm hora de Nueva York; vacío = no)") public String cierreNY = "";
    @Configurable("No entrar en los últimos minutos antes del cierre forzado") public int sinEntradaMin = 15;
    @Configurable("Carpeta de salida (vacío = carpeta de archivos de JForex)") public String outDir = "";

    private IContext context;
    private IConsole console;
    private IHistory history;
    private IEngine engine;
    private File dir;
    private U1Nucleo nucleo;
    private long ultimoTickMs = Long.MIN_VALUE;
    private long desdeMs = Long.MIN_VALUE, hastaMs = Long.MAX_VALUE;
    private int cierreMin = -1;
    private String diaLog = null;
    private PrintWriter logTicks = null;
    private PrintWriter logSenales = null;
    private PrintWriter logOps = null;
    private int nOrden = 0;
    private final Map<String, double[]> riesgo = new HashMap<>();       // label -> {riesgo, tp, sl, t_señal, lado, lo, hi, E}
    private final SimpleDateFormat fdia = new SimpleDateFormat("yyyyMMdd");
    private final TimeZone ny = TimeZone.getTimeZone("America/New_York");

    private static long fecha(String s, long def) throws JFException {
        if (s == null || s.trim().isEmpty()) return def;
        try {
            SimpleDateFormat f = new SimpleDateFormat(s.trim().length() > 10 ? "yyyy-MM-dd HH:mm" : "yyyy-MM-dd");
            f.setTimeZone(TimeZone.getTimeZone("UTC"));
            return f.parse(s.trim()).getTime();
        } catch (Exception e) { throw new JFException("fecha inválida: " + s); }
    }

    @Override
    public void onStart(IContext ctx) throws JFException {
        context = ctx; console = ctx.getConsole(); history = ctx.getHistory(); engine = ctx.getEngine();
        fdia.setTimeZone(TimeZone.getTimeZone("UTC"));
        desdeMs = fecha(desde, Long.MIN_VALUE); hastaMs = fecha(hasta, Long.MAX_VALUE);
        if (cierreNY != null && !cierreNY.trim().isEmpty()) {
            String[] p = cierreNY.trim().split(":"); cierreMin = Integer.parseInt(p[0]) * 60 + Integer.parseInt(p[1]);
        }
        ctx.setSubscribedInstruments(Collections.singleton(instrument), true);
        dir = outDir == null || outDir.isEmpty() ? ctx.getFilesDir() : new File(outDir);
        dir.mkdirs();
        try {
            logSenales = new PrintWriter(new FileWriter(new File(dir, "senales_U1_" + instrument.name() + ".csv"), true), true);
            File fo = new File(dir, "operaciones_U1_" + instrument.name() + ".csv"); boolean nuevo = !fo.exists();
            logOps = new PrintWriter(new FileWriter(fo, true), true);
            if (nuevo) logOps.println("label,t_senal_s,lado,t_entrada_ms,entrada,sl,tp,t_salida_ms,salida,motivo,pnl_precio,riesgo_precio,R,comision_usd");
        } catch (IOException e) { throw new JFException("no se pudieron abrir los archivos: " + e); }
        nucleo = new U1Nucleo(U1Nucleo.AH_MIN_U1);
        // Calentamiento: ticks históricos de las `warmupHoras` horas previas al inicio (el primer tick del tester o el último en vivo),
        // por el mismo camino que los vivos. Sus señales se registran pero NUNCA se operan.
        long fin = history.getTimeOfLastTick(instrument);
        long ini = fin - warmupHoras * 3600_000L;
        int n = 0;
        for (long a = ini; a <= fin; a += 3600_000L) {
            long b = Math.min(a + 3600_000L - 1, fin);
            List<ITick> ts = history.getTicks(instrument, a, b);
            for (ITick t : ts) { alimentar(t, "calentamiento"); n++; }
        }
        console.getOut().println("U1-CRUZADO: calentamiento con " + n + " ticks, " + nucleo.velas() + " velas M1. Rango ["
                + (desde.isEmpty() ? "-" : desde) + ", " + (hasta.isEmpty() ? "-" : hasta) + "). Operar = " + operar + ". Salida en " + dir);
    }

    private void alimentar(ITick t, String fase) throws JFException {
        long ms = t.getTime();
        if (ms < ultimoTickMs) return;                       // nunca hacia atrás (el ensamble de velas exige orden)
        if (ms == ultimoTickMs && "vivo".equals(fase) && nucleo.vistoEnBorde(t.getBid(), t.getAsk())) return;   // empalme calentamiento/vivo
        ultimoTickMs = ms;
        if (ms < hastaMs) logTick(ms, t.getBid(), t.getAsk(), t.getBidVolume(), t.getAskVolume());
        for (U1Nucleo.Senal s : nucleo.tick(ms, t.getBid(), t.getAsk())) emitir(s, fase);
        if ("vivo".equals(fase)) cierreForzado(ms);
    }

    private void logTick(long ms, double bid, double ask, double bv, double av) {
        String d = fdia.format(new Date(ms));
        if (!d.equals(diaLog)) {
            if (logTicks != null) logTicks.close();
            try {
                File f = new File(dir, "ticks_" + instrument.name() + "_" + d + ".csv");
                boolean nuevo = !f.exists();
                logTicks = new PrintWriter(new BufferedWriter(new FileWriter(f, true)));
                if (nuevo) logTicks.println("time_ms,bid,ask,bid_vol,ask_vol");
            } catch (IOException e) { console.getErr().println("log de ticks: " + e); logTicks = null; }
            diaLog = d;
        }
        if (logTicks != null) logTicks.println(ms + "," + bid + "," + ask + "," + bv + "," + av);
    }

    private int minutoNY(long ms) {
        Calendar c = Calendar.getInstance(ny); c.setTimeInMillis(ms);
        return c.get(Calendar.HOUR_OF_DAY) * 60 + c.get(Calendar.MINUTE);
    }

    private void emitir(U1Nucleo.Senal s, String fase) throws JFException {
        long tMs = s.t * 1000L;
        boolean enRango = tMs >= desdeMs && tMs < hastaMs;
        String linea = s.csv() + "," + fase + (enRango ? "" : "_fuera_de_rango");
        logSenales.println(linea);
        console.getOut().println("SEÑAL U1 " + (s.lado == 1 ? "VENTA (vuelve desde arriba)" : "COMPRA (vuelve desde abajo)") + " " + linea);
        if (operar && enRango && "vivo".equals(fase)) entrar(s);
    }

    private void entrar(U1Nucleo.Senal s) throws JFException {
        if (cierreMin >= 0) {
            int m = minutoNY(s.t * 1000L), falta = ((cierreMin - m) % 1440 + 1440) % 1440;
            if (falta < sinEntradaMin) { console.getOut().println("  no se opera: a " + falta + " min del cierre forzado"); return; }
        }
        int abiertas = 0;
        for (IOrder o : engine.getOrders(instrument)) if (o.getLabel().startsWith("U1_") && o.getState() == IOrder.State.FILLED) abiertas++;
        if (abiertas >= maxPosiciones) { console.getOut().println("  no se opera: ya hay " + abiertas + " posición(es) abierta(s)"); return; }
        IEngine.OrderCommand cmd = s.lado == 1 ? IEngine.OrderCommand.SELL : IEngine.OrderCommand.BUY;
        String label = "U1_" + s.t + "_" + (++nOrden);
        riesgo.put(label, new double[]{Double.NaN, Double.NaN, Double.NaN, s.t, s.lado, s.lo, s.hi, s.E});
        // A mercado, sin SL/TP: se ponen con el precio de llenado real (onMessage ORDER_FILL_OK).
        engine.submitOrder(label, instrument, cmd, cantidad, 0, slippagePips > 0 ? slippagePips : -1);
    }

    private void ponerNiveles(IOrder o) throws JFException {
        double[] r = riesgo.get(o.getLabel()); if (r == null) return;
        int lado = (int) r[4]; double lo = r[5], hi = r[6], E = r[7], e = o.getOpenPrice(), pip = instrument.getPipValue();
        int s = -lado;                                                         // lado de la operación: +1 compra, -1 venta
        double tp = objetivoLejano ? (lado == 1 ? lo : hi) : (lado == 1 ? hi : lo);
        double dist = (tp - e) * s;
        if (dist <= 0) { console.getOut().println("  " + o.getLabel() + ": el llenado ya pasó el TP, se cierra"); o.close(); return; }
        double sl = E + lado * pip;                                            // más allá del extremo
        if (topeMult > 0 && (e - sl) * s > topeMult * dist) sl = e - s * topeMult * dist;
        double esc = Math.pow(10, instrument.getPipScale() + 1);
        tp = Math.round(tp * esc) / esc; sl = (s == 1 ? Math.floor(sl * esc) : Math.ceil(sl * esc)) / esc;   // el stop, nunca más favorable
        r[0] = (e - sl) * s; r[1] = tp; r[2] = sl;
        o.setStopLossPrice(sl); o.setTakeProfitPrice(tp);
        console.getOut().println("  " + o.getLabel() + " llenada a " + e + "  SL " + sl + "  TP " + tp + "  riesgo " + r[0]);
    }

    private void cierreForzado(long ms) throws JFException {
        if (cierreMin < 0 || minutoNY(ms) != cierreMin) return;
        for (IOrder o : engine.getOrders(instrument))
            if (o.getLabel().startsWith("U1_") && o.getState() == IOrder.State.FILLED) o.close();
    }

    @Override
    public void onTick(Instrument inst, ITick tick) throws JFException {
        if (inst == instrument) alimentar(tick, "vivo");
    }

    @Override
    public void onBar(Instrument inst, Period period, IBar askBar, IBar bidBar) throws JFException {
        // Cierra la vela en curso apenas termina su minuto (sin esperar al próximo tick). Mismo contenido: los ticks llegan en orden.
        if (inst != instrument || period != Period.ONE_MIN) return;
        for (U1Nucleo.Senal s : nucleo.cerrarSiVencida(bidBar.getTime() + 60_000L)) emitir(s, "vivo");
        if (logTicks != null) logTicks.flush();
    }

    @Override
    public void onMessage(IMessage m) throws JFException {
        IOrder o = m.getOrder();
        if (o == null || !o.getLabel().startsWith("U1_")) return;
        if (m.getType() == IMessage.Type.ORDER_FILL_OK) ponerNiveles(o);
        else if (m.getType() == IMessage.Type.ORDER_SUBMIT_REJECTED || m.getType() == IMessage.Type.ORDER_FILL_REJECTED)
            console.getErr().println("  " + o.getLabel() + " rechazada: " + m.getContent());
        else if (m.getType() == IMessage.Type.ORDER_CLOSE_OK) {
            double[] r = riesgo.remove(o.getLabel());
            if (r == null || o.getClosePrice() == 0) return;
            int s = o.isLong() ? 1 : -1; double pnl = (o.getClosePrice() - o.getOpenPrice()) * s;
            String motivo = m.getReasons().contains(IMessage.Reason.ORDER_CLOSED_BY_SL) ? "SL"
                    : m.getReasons().contains(IMessage.Reason.ORDER_CLOSED_BY_TP) ? "TP" : "CIERRE";
            double Rr = r[0] > 0 ? pnl / r[0] : Double.NaN;
            logOps.println(o.getLabel() + "," + (long) r[3] + "," + s + "," + o.getFillTime() + "," + o.getOpenPrice() + "," + r[2] + "," + r[1] + ","
                    + o.getCloseTime() + "," + o.getClosePrice() + "," + motivo + "," + pnl + "," + r[0] + "," + Rr + "," + o.getCommissionInUSD());
            console.getOut().println("  " + o.getLabel() + " cerrada por " + motivo + ": " + pnl + " (" + Rr + " R, antes de comisión)");
        }
    }

    @Override public void onAccount(IAccount account) throws JFException { }

    @Override
    public void onStop() throws JFException {
        if (logTicks != null) logTicks.close();
        if (logSenales != null) logSenales.close();
        if (logOps != null) logOps.close();
        console.getOut().println("U1-CRUZADO detenida. " + nucleo.velas() + " velas.");
    }
}

// === NUCLEO INICIO === (puro Java, sin API de JForex: tools/paridad_jforex_u1.py lo extrae y lo compila para la paridad)
final class U1Nucleo {
    static final double W = 40.0, G = 1.0, X = 0.25, AH_MIN_U1 = 8.0, PASO = 0.01;
    static final long VIDA_S = 500 * 60;
    static final int N_MIN = 3, MAX_CICLOS = 10;
    final double ahMin;

    static final class Senal {
        long t; int lado; double lo, hi, H, E, A, D, c; long tArea;
        String csv() { return t + "," + lado + "," + lo + "," + hi + "," + H + "," + E + "," + A + "," + D + "," + c + "," + tArea; }
    }

    private static final class Zona { final int zi; final long tz; final double lo, hi;
        Zona(int zi, long tz, double lo, double hi) { this.zi = zi; this.tz = tz; this.lo = lo; this.hi = hi; } }

    private static final class Area {
        final long tm, finT; final double lo, hi, H;
        int ciclo = 0, lado = 0; boolean buscando = true, alej = false, hecho = false; double E = 0;
        Area(long tm, double lo, double hi, long finT) { this.tm = tm; this.lo = lo; this.hi = hi; this.H = hi - lo; this.finT = finT; }
    }

    private final ArrayList<double[]> ohlc = new ArrayList<>();   // o, h, l, c
    private final ArrayList<Long> tc = new ArrayList<>();           // cierre del minuto (s)
    private final ArrayList<Zona> vivos = new ArrayList<>();        // orden de creación (vela, luego orden del detector)
    private final ArrayDeque<double[]> marcas = new ArrayDeque<>(); // t, lo, hi de áreas marcadas (N=3, W=40)
    private final ArrayList<Area> areas = new ArrayList<>();
    private boolean hay = false; private long tcAct; private double bo, bh, bl, bc;
    private double ultBid = Double.NaN, ultAsk = Double.NaN;

    U1Nucleo(double ahMin) { this.ahMin = ahMin; }

    int velas() { return tc.size(); }
    boolean vistoEnBorde(double bid, double ask) { return bid == ultBid && ask == ultAsk; }

    /** Un tick. Devuelve las señales de la vela que este tick cerró (si cambió de minuto). */
    List<Senal> tick(long ms, double bid, double ask) {
        ultBid = bid; ultAsk = ask;
        double mid = Math.rint(((bid + ask) / 2) / PASO) * PASO;
        long t = (Math.floorDiv(ms, 60_000L) + 1) * 60;
        List<Senal> out = Collections.emptyList();
        if (hay && t != tcAct) out = cerrar();
        if (!hay) { hay = true; tcAct = t; bo = bh = bl = bc = mid; }
        else { bh = Math.max(bh, mid); bl = Math.min(bl, mid); bc = mid; }
        return out;
    }

    /** Cierra la vela en curso si su minuto ya terminó (`ahoraMs` >= cierre). */
    List<Senal> cerrarSiVencida(long ahoraMs) {
        if (hay && ahoraMs >= tcAct * 1000) return cerrar();
        return Collections.emptyList();
    }

    private List<Senal> cerrar() {
        hay = false;
        ohlc.add(new double[]{bo, bh, bl, bc}); tc.add(tcAct);
        return procesar(tc.size() - 1);
    }

    private List<Senal> procesar(int m) {
        ArrayList<Senal> out = new ArrayList<>();
        long tm = tc.get(m); double[] b = ohlc.get(m);
        // 1) áreas existentes (nacidas antes de m): un paso de disparos_causales
        for (Iterator<Area> it = areas.iterator(); it.hasNext(); ) {
            Area a = it.next();
            if (tm > a.finT || a.ciclo >= MAX_CICLOS) { it.remove(); continue; }
            Senal s = paso(a, b, tm);
            if (s != null) out.add(s);
        }
        // 2) zonas nuevas en m (detect) y, si nació alguna, marca de áreas
        if (m < 3) return out;
        int antes = vivos.size();
        detectar(m);
        if (vivos.size() == antes) return out;
        vivos.removeIf(z -> tm > z.tz + VIDA_S);
        int nv = vivos.size();
        if (nv < N_MIN) return out;
        Integer[] ord = new Integer[nv];
        for (int i = 0; i < nv; i++) ord[i] = i;
        Arrays.sort(ord, (p, q) -> Double.compare(vivos.get(p).lo, vivos.get(q).lo));      // estable (mergesort)
        Zona[] o = new Zona[nv]; double[] lov = new double[nv], hiv = new double[nv];
        for (int i = 0; i < nv; i++) { o[i] = vivos.get(ord[i]); lov[i] = o[i].lo; hiv[i] = o[i].hi; }
        int[] cnt = new int[nv]; double[] alto = new double[nv]; boolean[] nueva = new boolean[nv];
        for (int i = 0; i < nv; i++) {
            alto[i] = -1e300; double lim = lov[i] + W; int j0 = i;
            while (j0 > 0 && lov[j0 - 1] == lov[i]) j0--;
            for (int j = j0; j < nv; j++) {
                if (lov[j] > lim) break;
                if (hiv[j] <= lim) { cnt[i]++; if (hiv[j] > alto[i]) alto[i] = hiv[j]; if (o[j].zi == m) nueva[i] = true; }
            }
        }
        ArrayList<Integer> cand = new ArrayList<>();
        for (int i = 0; i < nv; i++) if (cnt[i] >= N_MIN && nueva[i]) cand.add(i);
        if (cand.isEmpty()) return out;
        cand.sort((p, q) -> Double.compare(alto[p] - lov[p], alto[q] - lov[q]));             // estable: ancho
        cand.sort((p, q) -> Integer.compare(-cnt[p], -cnt[q]));                              // estable: más zonas primero
        while (!marcas.isEmpty() && tm - marcas.peekFirst()[0] > VIDA_S) marcas.pollFirst();
        ArrayList<double[]> usadas = new ArrayList<>();
        for (int i : cand) {
            double lo = lov[i], hi = alto[i]; boolean choca = false;
            for (double[] u : usadas) if (lo <= u[1] && hi >= u[0]) { choca = true; break; }
            if (choca) continue;
            usadas.add(new double[]{lo, hi});
            boolean dup = false;
            for (double[] mk : marcas) if (lo <= mk[2] + G && hi >= mk[1] - G) { dup = true; break; }
            if (dup) continue;
            marcas.addLast(new double[]{tm, lo, hi});
            double lim = lo + W; int j0 = i; long maxTz = Long.MIN_VALUE;
            while (j0 > 0 && lov[j0 - 1] == lov[i]) j0--;
            for (int j = j0; j < nv; j++) { if (lov[j] > lim) break; if (hiv[j] <= lim) maxTz = Math.max(maxTz, o[j].tz); }
            if (hi - lo > 0) areas.add(new Area(tm, lo, hi, maxTz + VIDA_S));
        }
        return out;
    }

    private Senal paso(Area a, double[] b, long tm) {
        double h = b[1], l = b[2], c = b[3];
        if (a.buscando) {
            if (!(c > a.hi || c < a.lo)) return null;
            a.lado = c > a.hi ? 1 : -1; a.E = a.lado == 1 ? h : l; a.alej = false; a.hecho = false; a.buscando = false;
        } else a.E = a.lado == 1 ? Math.max(a.E, h) : Math.min(a.E, l);
        double A = a.lado == 1 ? a.E - a.hi : a.lo - a.E, D = a.lado == 1 ? c - a.hi : a.lo - c;
        boolean adentro = D <= 0;
        if (!a.alej) {
            if (A >= a.H) a.alej = true; else if (adentro) a.buscando = true;
            return null;
        }
        Senal s = null;
        if (!a.hecho && D <= X * A) {
            a.hecho = true;
            if (A / a.H >= ahMin) {
                s = new Senal(); s.t = tm; s.lado = a.lado; s.lo = a.lo; s.hi = a.hi; s.H = a.H; s.E = a.E; s.A = A; s.D = D; s.c = c; s.tArea = a.tm;
            }
        }
        if (adentro) { a.ciclo++; a.buscando = true; }
        return s;
    }

    private void detectar(int i) {
        double[] b0 = ohlc.get(i), b1 = ohlc.get(i - 1);
        double O0 = b0[0], H0 = b0[1], L0 = b0[2], C0 = b0[3], O1 = b1[0], H1 = b1[1], L1 = b1[2], C1 = b1[3];
        double bullTop = Math.min(C0, O0), bullBtm = Math.max(C1, O1), bearTop = Math.min(C1, O1), bearBtm = Math.max(C0, O0);
        long t = tc.get(i);
        if (O0 > C1 && H1 > L0 && C0 > C1 && O0 > O1 && H1 < bullTop) vivos.add(zona(i, t, bullTop, bullBtm));
        if (O0 < C1 && L1 < H0 && C0 < C1 && O0 < O1 && L1 > bearBtm) vivos.add(zona(i, t, bearTop, bearBtm));
        if (L0 > H1) vivos.add(zona(i, t, bullTop, bullBtm));
        if (H0 < L1) vivos.add(zona(i, t, bearTop, bearBtm));
    }

    private static Zona zona(int i, long t, double a, double b) { return new Zona(i, t, Math.min(a, b), Math.max(a, b)); }

    /** Línea de comandos para la paridad: java U1Nucleo ticks.csv [ah_min] > senales.csv (ticks: time_ms,bid,ask,...). */
    public static void main(String[] args) throws IOException {
        U1Nucleo n = new U1Nucleo(args.length > 1 ? Double.parseDouble(args[1]) : AH_MIN_U1);
        PrintWriter w = new PrintWriter(new BufferedWriter(new OutputStreamWriter(System.out)));
        w.println("t_cierre_s,lado,lo,hi,H,E,A,D,c,t_area_s");
        try (BufferedReader r = new BufferedReader(new FileReader(args[0]))) {
            String s = r.readLine();
            while ((s = r.readLine()) != null) {
                String[] p = s.split(",");
                for (Senal x : n.tick(Long.parseLong(p[0]), Double.parseDouble(p[1]), Double.parseDouble(p[2]))) w.println(x.csv());
            }
        }
        for (Senal x : n.cerrarSiVencida(Long.MAX_VALUE / 2)) w.println(x.csv());
        w.flush();
    }
}
// === NUCLEO FIN ===
