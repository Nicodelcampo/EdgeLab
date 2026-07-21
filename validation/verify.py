"""Capa ANTI-BUGS (regla 8 + lecciones EXP-041/043): defensas contra falsos
edges por errores de implementacion — lo que NINGUN test estadistico puede ver
(el bug corre igual sobre datos reales y permutados).

Cuatro defensas, todas obligatorias en el preflight de una estrategia:

1. SCENARIOS SINTETICOS (synthetic_check): datos artificiales con resultado
   conocido a mano — long-TP, long-SL, short-TP, short-SL, salida por tiempo,
   en ambas direcciones. Un motor con el signo invertido (bug EXP-043) o con
   TP/SL cruzados FALLA aca al instante. El motor se pasa como adaptador
   `engine(prices_o_ticks) -> trades`.

2. VERIFICADOR DE LEDGER (verify_ledger): re-deriva cada trade con un CODIGO
   INDEPENDIENTE (loop plano, sin numba, escrito aparte): aritmetica del PnL
   (dir*(exit-entry)/tick - costo), coherencia de la razon de salida, y
   NO-ANTICIPACION del stop/tp (ningun precio anterior al exit registrado
   debio disparar antes la salida). Cualquier discrepancia > tolerancia = FAIL.

3. MIRROR TEST (mirror_series): invierte los precios (p -> 2m - p, con bid/ask
   INTERCAMBIADOS). Una estrategia simetrica long/short debe dar el espejo:
   longs<->shorts y |PnL| igual (a menos del redondeo de tick). Un bug de
   signo o una asimetria accidental explotan aca.

4. PREFIX TEST (prefix_check): corre el pipeline sobre un PREFIJO de los datos
   y exige que los trades con entrada dentro del prefijo sean IDENTICOS a los
   del run completo — cualquier lookahead (features del futuro, cuantiles con
   fuga, normalizaciones globales) rompe la estabilidad del prefijo.
"""
import numpy as np
import pandas as pd


# ------------------------------------------------------------------ 1. sintetico
def synthetic_check(run_trades, tick=0.25, cost=0.0, verbose=True):
    """run_trades(times_ms, last, bid, ask) -> DataFrame con columnas
    [dir, entry_px, exit_px, pnl_ticks, reason]. Se le inyectan escenarios
    de UNA señal artificial con desenlace conocido; el chequeo es de SIGNO y
    coherencia, agnostico del motor: pnl == dir*(exit-entry)/tick - costo y
    perdida<0 en stops / ganancia>0 en tps."""
    fails = []
    trades_seen = 0
    base = 5000.0
    spread = tick
    # epoch base en horario RTH (15:00 UTC) para motores con filtro horario;
    # 30ms entre ticks para disparar señales de micro-ventana (sweep 500ms)
    t0 = int(pd.Timestamp("2026-03-05 15:00:00").value // 10**6)

    def mk(path_ticks):
        n = len(path_ticks)
        t = t0 + np.arange(n, dtype=np.int64) * 30
        last = base + np.asarray(path_ticks, dtype=np.float64) * tick
        bid = last - spread / 2
        ask = last + spread / 2
        return t, last, bid, ask

    # escenarios: (nombre, path en ticks relativos)
    up = list(range(0, 30))          # subida fuerte sostenida
    dn = [-x for x in up]
    rev_up_then_dump = up + [29 - x for x in range(1, 60)]       # sube y se derrumba
    rev_dn_then_pump = dn + [-29 + x for x in range(1, 60)]      # baja y despega
    scenarios = [("tras subida, derrumbe", rev_up_then_dump),
                 ("tras bajada, despegue", rev_dn_then_pump),
                 ("tras subida, sigue", up + [30 + x for x in range(60)]),
                 ("tras bajada, sigue", dn + [-30 - x for x in range(60)])]

    for name, path in scenarios:
        t, last, bid, ask = mk(path)
        try:
            tr = run_trades(t, last, bid, ask)
        except Exception as e:
            fails.append(f"{name}: EXCEPTION {e}")
            continue
        for r in tr.itertuples():
            trades_seen += 1
            expected = r.dir * (r.exit_px - r.entry_px) / tick - cost
            if abs(r.pnl_ticks - expected) > 0.51:
                fails.append(f"{name}: pnl={r.pnl_ticks:+.2f} pero dir*(exit-entry)-costo"
                             f"={expected:+.2f} (dir={r.dir} in={r.entry_px} out={r.exit_px})")
            if r.reason == "sl" and r.pnl_ticks >= 0:
                fails.append(f"{name}: STOP con pnl >= 0 ({r.pnl_ticks:+.2f}) — bug de signo")
            if r.reason == "tp" and r.pnl_ticks <= 0:
                fails.append(f"{name}: TP con pnl <= 0 ({r.pnl_ticks:+.2f})")
    ok = not fails
    if verbose:
        print(f"  [synthetic_check] {'OK' if ok else 'FAIL'} — {trades_seen} trades sinteticos"
              + ("" if ok else "\n    " + "\n    ".join(fails[:8])))
    return ok, fails


# ------------------------------------------------------------------ 2. ledger
def verify_ledger(trades, times_ms, last, tick=0.25, cost=0.0, tol=1.1, verbose=True):
    """Re-deriva cada trade con codigo independiente. trades: DataFrame con
    [dir, entry_i, entry_px, exit_i, exit_px, pnl_ticks, tp_px, sl_px]
    (indices de tick). Chequea aritmetica + primera-pasada del sl/tp."""
    fails = []
    for r in trades.itertuples():
        expected = r.dir * (r.exit_px - r.entry_px) / tick - cost
        if abs(r.pnl_ticks - expected) > 0.01:   # formula exacta: tolerancia ~0
            fails.append(f"trade@{r.entry_i}: pnl {r.pnl_ticks:+.2f} != {expected:+.2f}")
            continue
        if r.exit_i <= r.entry_i:
            fails.append(f"trade@{r.entry_i}: exit_i <= entry_i")
            continue
        # no-anticipacion: entre entry_i+1 y exit_i-1 el last no debio disparar
        # ni el sl (last toca el nivel) ni el tp (last opera A TRAVES: +/-1 tick)
        # — mismas convenciones del motor compartido (edgelab/engine.py)
        seg = last[r.entry_i + 1: r.exit_i]
        if len(seg):
            if r.dir == 1:
                if np.any(seg <= r.sl_px + 1e-9) or np.any(seg >= r.tp_px + tick - 1e-9):
                    fails.append(f"trade@{r.entry_i}: sl/tp cruzado ANTES del exit registrado")
            else:
                if np.any(seg >= r.sl_px - 1e-9) or np.any(seg <= r.tp_px - tick + 1e-9):
                    fails.append(f"trade@{r.entry_i}: sl/tp cruzado ANTES del exit registrado")
    ok = not fails
    if verbose:
        print(f"  [verify_ledger] {'OK' if ok else 'FAIL'} — {len(trades)} trades re-derivados"
              + ("" if ok else f" | {len(fails)} fallas\n    " + "\n    ".join(fails[:6])))
    return ok, fails


# ------------------------------------------------------------------ 3. espejo
def mirror_series(last, bid, ask):
    """Espejo de precios: p -> 2m - p. OJO: bid y ask se INTERCAMBIAN."""
    m = float(np.nanmean(last))
    return 2 * m - last, 2 * m - ask, 2 * m - bid


def mirror_check(run_trades, times_ms, last, bid, ask, verbose=True, tol_frac=0.02):
    """Corre el pipeline sobre los datos reales y sobre el espejo. Exige:
    n_long<->n_short intercambiados (±2%) y expectancy igual (±2% o ±0.1t)."""
    tr = run_trades(times_ms, last, bid, ask)
    ml, mb, ma = mirror_series(last, bid, ask)
    tm = run_trades(times_ms, ml, mb, ma)
    nl, ns = (tr.dir == 1).sum(), (tr.dir == -1).sum()
    nlm, nsm = (tm.dir == 1).sum(), (tm.dir == -1).sum()
    e, em = tr.pnl_ticks.mean(), tm.pnl_ticks.mean()
    ok_n = abs(nl - nsm) <= max(2, tol_frac * max(nl, 1)) and \
           abs(ns - nlm) <= max(2, tol_frac * max(ns, 1))
    ok_e = abs(e - em) <= max(0.1, tol_frac * abs(e))
    ok = ok_n and ok_e
    if verbose:
        print(f"  [mirror_check] {'OK' if ok else 'FAIL'} — real: {nl}L/{ns}S exp={e:+.3f}t | "
              f"espejo: {nlm}L/{nsm}S exp={em:+.3f}t")
    return ok, (nl, ns, e, nlm, nsm, em)


# ------------------------------------------------------------------ 4. prefijo
def prefix_check(run_trades, times_ms, last, bid, ask, fracs=(0.5, 0.8), verbose=True):
    """Los trades cuya entrada cae dentro del prefijo deben ser IDENTICOS
    corriendo el pipeline solo con el prefijo (anti-lookahead)."""
    full = run_trades(times_ms, last, bid, ask)
    fails = []
    for f in fracs:
        cut = int(len(times_ms) * f)
        pre = run_trades(times_ms[:cut], last[:cut], bid[:cut], ask[:cut])
        # margen: descartar trades del final del prefijo (hold cortado)
        margin_ms = 600000
        t_lim = times_ms[cut - 1] - margin_ms
        fe = full[full.entry_t < t_lim]
        pe = pre[pre.entry_t < t_lim]
        if len(fe) != len(pe):
            fails.append(f"frac {f}: {len(fe)} trades full vs {len(pe)} prefijo")
            continue
        if len(fe) and not np.allclose(fe.pnl_ticks.to_numpy(), pe.pnl_ticks.to_numpy(), atol=0.01):
            bad = int(np.sum(~np.isclose(fe.pnl_ticks.to_numpy(), pe.pnl_ticks.to_numpy(), atol=0.01)))
            fails.append(f"frac {f}: {bad} trades con PnL distinto (lookahead)")
    ok = not fails
    if verbose:
        print(f"  [prefix_check] {'OK' if ok else 'FAIL'}"
              + ("" if ok else "\n    " + "\n    ".join(fails)))
    return ok, fails


def preflight(name, run_trades, times_ms, last, bid, ask, tick=0.25, cost=0.0):
    """Bateria completa. Devuelve True solo si TODO pasa. Sin esto, el
    gauntlet estadistico no debe correrse (GIGO)."""
    print(f"\nPREFLIGHT anti-bugs — {name}")
    ok1, _ = synthetic_check(run_trades, tick=tick, cost=cost)
    ok3, _ = mirror_check(run_trades, times_ms, last, bid, ask)
    ok4, _ = prefix_check(run_trades, times_ms, last, bid, ask)
    ok = ok1 and ok3 and ok4
    print(f"  => PREFLIGHT {'APROBADO' if ok else 'RECHAZADO — NO correr gauntlet'}")
    return ok
