package jforex;

import com.dukascopy.api.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * EdgeLab U1-CRUZADO, señal CAUSAL sobre USATECH (2026-11-02).
 *
 * Port 1:1 de `edgelab/research/u1_cruzado.py::senales` con `areas_expansion.disparos_causales`:
 *   - velas M1 armadas con los ticks: mid = rint(((bid+ask)/2)/0,01)·0,01, marca de cierre = (minuto + 1)·60 s, sólo minutos con ticks;
 *   - zonas LUX-IMB (VI y OG, alcista y bajista) con 500 min de vida;
 *   - áreas: N >= 3 zonas vivas enteras en una banda de 40 pts, G = 1, sin repetir en 500 min;
 *   - ciclo causal: cierre afuera, alejamiento A >= H y regreso; dispara la primera vela con D <= 0,25·A, si A/H >= 8.
 * NO OPERA. Escribe cada señal y todos los ticks usados (también los del calentamiento) en la carpeta de archivos de JForex:
 *   ticks_USATECHIDXUSD_YYYYMMDD.csv   time_ms,bid,ask,bid_vol,ask_vol        (día UTC)
 *   senales_U1_USATECH.csv             t_cierre_s,lado,lo,hi,H,E,A,D,c,t_area_s,fase
 * La paridad con Python se mide con `tools/paridad_jforex_u1.py` sobre esos mismos ticks.
 * En NQ (NT8): base = cierre NQ − cierre USATECH en ese minuto; objetivo T3 = borde lejano + base; stop = E + base más allá de 1 tick
 * (hacia afuera), con tope de 3 × la distancia al objetivo; entrada en el primer tick de la vela NQ siguiente.
 */
public class EdgeLabU1Cruzado implements IStrategy {
    @Configurable("Instrumento (sensor)") public Instrument instrument = Instrument.USATECHIDXUSD;
    @Configurable("Calentamiento (horas de ticks históricos)") public int warmupHoras = 48;
    @Configurable("Carpeta de salida (vacío = carpeta de archivos de JForex)") public String outDir = "";

    private IContext context;
    private IConsole console;
    private IHistory history;
    private File dir;
    private U1Nucleo nucleo;
    private long ultimoTickMs = Long.MIN_VALUE;
    private String diaLog = null;
    private PrintWriter logTicks = null;
    private PrintWriter logSenales = null;
    private final SimpleDateFormat fdia = new SimpleDateFormat("yyyyMMdd");

    @Override
    public void onStart(IContext ctx) throws JFException {
        context = ctx; console = ctx.getConsole(); history = ctx.getHistory();
        fdia.setTimeZone(TimeZone.getTimeZone("UTC"));
        ctx.setSubscribedInstruments(Collections.singleton(instrument), true);
        dir = outDir == null || outDir.isEmpty() ? ctx.getFilesDir() : new File(outDir);
        dir.mkdirs();
        try {
            logSenales = new PrintWriter(new FileWriter(new File(dir, "senales_U1_" + instrument.name() + ".csv"), true), true);
        } catch (IOException e) { throw new JFException("no se pudo abrir el archivo de señales: " + e); }
        nucleo = new U1Nucleo(U1Nucleo.AH_MIN_U1);
        // Calentamiento: ticks históricos de las últimas `warmupHoras` horas, en tramos de 1 h, por el mismo camino que los vivos.
        long fin = history.getTimeOfLastTick(instrument);
        long ini = fin - warmupHoras * 3600_000L;
        int n = 0;
        for (long a = ini; a <= fin; a += 3600_000L) {
            long b = Math.min(a + 3600_000L - 1, fin);
            List<ITick> ts = history.getTicks(instrument, a, b);
            for (ITick t : ts) { alimentar(t, "calentamiento"); n++; }
        }
        console.getOut().println("U1-CRUZADO: calentamiento con " + n + " ticks, " + nucleo.velas() + " velas M1. Salida en " + dir);
    }

    private void alimentar(ITick t, String fase) {
        long ms = t.getTime();
        if (ms < ultimoTickMs) return;                       // nunca hacia atrás (el ensamble de velas exige orden)
        if (ms == ultimoTickMs && "vivo".equals(fase) && nucleo.vistoEnBorde(t.getBid(), t.getAsk())) return;   // empalme calentamiento/vivo
        ultimoTickMs = ms;
        logTick(ms, t.getBid(), t.getAsk(), t.getBidVolume(), t.getAskVolume());
        for (U1Nucleo.Senal s : nucleo.tick(ms, t.getBid(), t.getAsk())) emitir(s, fase);
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

    private void emitir(U1Nucleo.Senal s, String fase) {
        String linea = s.csv() + "," + fase;
        logSenales.println(linea);
        console.getOut().println("SEÑAL U1 " + (s.lado == 1 ? "VENTA (vuelve desde arriba)" : "COMPRA (vuelve desde abajo)") + " " + linea);
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

    @Override public void onMessage(IMessage message) throws JFException { }
    @Override public void onAccount(IAccount account) throws JFException { }

    @Override
    public void onStop() throws JFException {
        if (logTicks != null) logTicks.close();
        if (logSenales != null) logSenales.close();
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
