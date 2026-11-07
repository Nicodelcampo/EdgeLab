package jforex;

import com.dukascopy.api.*;
import java.util.Calendar;
import java.util.TimeZone;

/**
 * Misma regla de reloj que nt8/strategies/RangoPreapertura.cs, sobre el CFD de índice
 * (USA500IDXUSD para el caso ES, USATECHIDXUSD para el caso NQ). No es el futuro CME
 * y no es un edge promovido. El tercil de ancho no se aplica.
 *
 * Gráfico o suscripción de 1 minuto. Intento 0 = primer quiebre. Intento 1 = reentrada.
 * Stop un tick de instrumento más allá del borde opuesto. Cierre forzado 15:55 ET.
 */
public class RangoPreapertura implements IStrategy {
    @Configurable("Instrumento") public Instrument instrument = Instrument.USA500IDXUSD;
    @Configurable("Cantidad") public double cantidad = 0.01;
    @Configurable("Intento (0 ES, 1 NQ)") public int intento = 0;
    @Configurable("Slippage") public double slippage = 2.0;

    private IEngine engine;
    private IConsole console;
    private IOrder orden;
    private final TimeZone ny = TimeZone.getTimeZone("America/New_York");
    private int dia = -1;
    private int fase, lado1, velas;
    private double rHi, rLo, rMid;
    private boolean enRango;

    @Override
    public void onStart(IContext ctx) throws JFException {
        engine = ctx.getEngine();
        console = ctx.getConsole();
        ctx.setSubscribedInstruments(java.util.Collections.singleton(instrument), true);
        console.getOut().println("RangoPreapertura paper. No es un edge promovido. Intento " + intento);
    }

    @Override
    public void onTick(Instrument inst, ITick tick) {}

    @Override
    public void onBar(Instrument inst, Period period, IBar ask, IBar bid) throws JFException {
        if (!inst.equals(instrument) || period != Period.ONE_MIN || bid == null) return;
        Calendar c = Calendar.getInstance(ny);
        c.setTimeInMillis(bid.getTime());
        int dow = c.get(Calendar.DAY_OF_WEEK);
        if (dow == Calendar.SATURDAY || dow == Calendar.SUNDAY) return;
        int ymd = c.get(Calendar.YEAR) * 10000 + (c.get(Calendar.MONTH) + 1) * 100 + c.get(Calendar.DAY_OF_MONTH);
        if (ymd != dia) reset(ymd);
        int hm = c.get(Calendar.HOUR_OF_DAY) * 100 + c.get(Calendar.MINUTE);
        // Dukascopy etiqueta la vela M1 por su inicio. El cierre es un minuto después.
        hm = hm + 1;
        if (hm % 100 == 60) hm = (hm / 100 + 1) * 100;

        if (hm >= 1555) {
            cerrar();
            fase = 3;
            return;
        }
        if (fase == 3 || hm <= 915) return;
        if (hm <= 930) {
            if (!enRango) { rHi = bid.getHigh(); rLo = bid.getLow(); enRango = true; }
            else { rHi = Math.max(rHi, bid.getHigh()); rLo = Math.min(rLo, bid.getLow()); }
            velas++;
            if (hm == 930) {
                rMid = (rHi + rLo) / 2.0;
                if (velas < 12 || !(rHi > rLo)) fase = 3;
            }
            return;
        }
        if (!enRango || hm > 1130) return;
        if (fase == 1) {
            if ((lado1 == 1 && bid.getLow() <= rMid) || (lado1 == -1 && bid.getHigh() >= rMid)) fase = 2;
            return;
        }
        if (fase != 0 && fase != 2) return;
        int lado = bid.getClose() > rHi ? 1 : (bid.getClose() < rLo ? -1 : 0);
        if (lado == 0) return;
        if ((fase == 0 && intento == 0) || (fase == 2 && intento == 1)) entrar(lado);
        if (fase == 0) { fase = 1; lado1 = lado; }
        else fase = 3;
    }

    private void entrar(int lado) throws JFException {
        if (orden != null && orden.getState() != IOrder.State.CLOSED && orden.getState() != IOrder.State.CANCELED) return;
        double tick = instrument.getPipValue();
        double stop = lado == 1 ? Math.floor(rLo / tick) * tick - tick : Math.ceil(rHi / tick) * tick + tick;
        orden = engine.submitOrder("rp" + dia + fase, instrument,
                lado == 1 ? IEngine.OrderCommand.BUY : IEngine.OrderCommand.SELL,
                cantidad, 0, slippage, stop, 0, 0, System.currentTimeMillis() + 86400000L, "preapertura");
    }

    private void cerrar() throws JFException {
        if (orden != null && orden.getState() == IOrder.State.FILLED) orden.close();
    }

    private void reset(int ymd) {
        dia = ymd; fase = 0; lado1 = 0; velas = 0; enRango = false; rHi = rLo = rMid = 0;
    }

    @Override public void onMessage(IMessage message) {}
    @Override public void onAccount(IAccount account) {}
    @Override public void onStop() {}
}
