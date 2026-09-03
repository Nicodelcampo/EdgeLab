"""Bar builder canónico (tiempo y TICK) + footprint bid/ask con gate P1A.

Barras de TIEMPO: `[inicio, fin)`; un tick con ts == fin pertenece a la barra
SIGUIENTE; timestamp de barra = cierre (semántica Time[0] de NT8).
Barras de TICK: N ticks por barra (BigTrap corre sobre charts de 5t/25t/...);
membresía por `sequence` (orden del archivo); cierre = ts del último tick.
Sin barras vacías (igual que NT8 con datos históricos).

Clasificación buy/sell (idéntica a BigTrap2.AccumulateTick):
  1) quote: ask>0, bid>0, ask>=bid -> price>=ask: buy; price<=bid: sell
  2) tick-rule (fallback CONTADO en n_rule): >last buy; <last sell; ==last dir previa
  3) primer tick sin info -> buy (declarado, cuenta como rule)
NO hay fallback silencioso: si el feed no trae bid/ask, `has_quotes=False` y el
gate P1A lo marca (no se reconstruye footprint fiel sin quotes).

Gate P1A footprint: |Σ(ask_vol + bid_vol) - volumen_barra| <= 0.5 por barra,
si no -> FOOTPRINT_MISMATCH (diagnóstico, nunca silenciado).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .ticks import TickSeries

NS = 1_000_000_000


@dataclass
class BarSeries:
    start_ns: np.ndarray
    end_ns: np.ndarray          # cierre (timestamp NT8 de la barra)
    open_t: np.ndarray          # ticks enteros
    high_t: np.ndarray
    low_t: np.ndarray
    close_t: np.ndarray
    volume: np.ndarray          # float64
    tick_size: float
    kind: str                   # "time" | "tick"
    param: int                  # minutos (time) o ticks_por_barra (tick)
    tick_bar_idx: np.ndarray    # índice de barra de cada tick
    session_idx: Optional[np.ndarray] = None

    def __len__(self):
        return len(self.end_ns)


def _ohlc(ticks: TickSeries, starts, ends):
    n = len(starts)
    o = np.empty(n, np.int64); h = np.empty(n, np.int64)
    lo = np.empty(n, np.int64); c = np.empty(n, np.int64)
    v = np.empty(n, np.float64)
    tbi = np.empty(len(ticks), np.int64)
    for b in range(n):
        i0, i1 = int(starts[b]), int(ends[b])
        p = ticks.price_ticks[i0:i1]
        o[b] = p[0]; c[b] = p[-1]; h[b] = p.max(); lo[b] = p.min()
        v[b] = ticks.volume[i0:i1].sum()
        tbi[i0:i1] = b
    return o, h, lo, c, v, tbi


def build_time_bars(ticks: TickSeries, minutes: int) -> BarSeries:
    period = int(minutes) * 60 * NS
    bucket = ticks.ts_ns // period
    change = np.flatnonzero(np.diff(bucket)) + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [len(bucket)]))
    o, h, lo, c, v, tbi = _ohlc(ticks, starts, ends)
    s_ns = (bucket[starts] * period).astype(np.int64)
    e_ns = ((bucket[starts] + 1) * period).astype(np.int64)
    return BarSeries(s_ns, e_ns, o, h, lo, c, v, ticks.tick_size, "time", int(minutes), tbi)


def session_ids(ts_ns) -> np.ndarray:
    """Índice de sesión CME ETH por tick, vectorizado y con DST.

    Convención `[inicio, fin)`: un tick exactamente en la apertura (17:00 CT)
    pertenece a la sesión que abre. Misma convención que `sessions.py`, que ya
    está validada 7/7 contra el oráculo real — acá se replica vectorizada porque
    llamar `session_key` por tick sobre millones de ticks es inviable.
    """
    import pandas as pd
    idx = pd.to_datetime(np.asarray(ts_ns, dtype="int64"), unit="ns", utc=True)\
            .tz_convert("America/Chicago")
    # trade-date: el día del CIERRE. Un tick a las >= 17:00 pertenece a la sesión
    # que cierra al día siguiente.
    # normalize() vuelve a medianoche LOCAL; el entero de dia sale de ahi.
    dias = np.asarray(idx.normalize().view("int64")) // 86_400_000_000_000
    return dias + (np.asarray(idx.hour) >= 17).astype(np.int64)


def build_tick_bars(ticks: TickSeries, ticks_per_bar: int,
                    reiniciar_por_sesion: bool = True) -> BarSeries:
    """Barras de N ticks, con el contador REINICIADO en cada frontera de sesión.

    ## Por qué el reinicio (TICKBAR-001, defecto 2 de PRED-003)

    La versión previa hacía `bucket = arange(n) // N`: un conteo **global** sobre
    todo el rango, sin noción de sesión. **NT8 reinicia el conteo en cada
    frontera** — está demostrado sobre la captura `tickbar_frontera2_25t`: la
    última barra de la sesión cierra CORTA (bar 3770 = 19 eventos, volumen 2700
    idéntico al que reporta NT8) y la siguiente arranca en el primer evento
    posterior al hueco.

    Sin reinicio, las dos particiones se separan **en la primera frontera** y no
    vuelven a coincidir nunca:

    | K  | tras 1 frontera | tras 33 sesiones |
    |----|----------------:|-----------------:|
    | 10 |        8 ticks  |       132 ticks  |
    | 25 |       23 ticks  |       392 ticks  |

    Este defecto es **independiente** del del `.cs` y no lo mide
    `FOOTPRINT_MISMATCH` (que compara NT8 contra sí mismo). Estaban superpuestos
    y sólo uno estaba diagnosticado.

    `reiniciar_por_sesion=False` reproduce la semántica vieja; existe sólo para
    los tests de regresión que documentan el defecto.
    """
    n = len(ticks)
    N = int(ticks_per_bar)
    if N < 1:
        raise ValueError("ticks_per_bar debe ser >= 1")
    if n == 0:
        raise ValueError("serie de ticks vacía")

    if not reiniciar_por_sesion:
        bucket = np.arange(n) // N
    else:
        ses = session_ids(ticks.ts_ns)
        # inicio de cada sesión dentro del array
        ini_ses = np.concatenate(([0], np.flatnonzero(np.diff(ses)) + 1))
        # posición del tick DENTRO de su sesión: ahí el conteo arranca de cero
        base = np.repeat(ini_ses, np.diff(np.concatenate((ini_ses, [n]))))
        local = (np.arange(n) - base) // N
        # id global de barra: se desplaza para que no se mezclen entre sesiones
        offs = np.concatenate(([0], np.cumsum(
            (np.diff(np.concatenate((ini_ses, [n]))) + N - 1) // N)[:-1]))
        bucket = local + np.repeat(offs, np.diff(np.concatenate((ini_ses, [n]))))

    change = np.flatnonzero(np.diff(bucket)) + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [n]))
    o, h, lo, c, v, tbi = _ohlc(ticks, starts, ends)
    s_ns = ticks.ts_ns[starts].astype(np.int64)
    e_ns = ticks.ts_ns[ends - 1].astype(np.int64)   # cierre = ts del último tick
    return BarSeries(s_ns, e_ns, o, h, lo, c, v, ticks.tick_size, "tick", N, tbi)


def build_resolved_tick_bars(ticks: TickSeries, bar_profile_path: str | Path,
                             ticks_per_bar: int = 120,
                             chart_tz: str = "America/Argentina/Buenos_Aires") -> BarSeries:
    """Reconstruye barras de ticks resolviendo la frontera EXACTA de cada barra
    contra el perfil de volumen reportado por NT8 (P-70 BARPROFILE).

    Garantiza que la partición de barras coincida con la subserie 1-tick de NT8,
    eliminando la deriva por fluctuaciones de tick-count entre barras.
    """
    import pandas as pd
    df_bp = pd.read_csv(bar_profile_path, skiprows=1)
    target_vols = df_bp["profile_volume"].values.astype(np.int64)
    n_bars = len(target_vols)
    n_ticks = len(ticks)

    vols = ticks.volume.astype(np.int64)
    starts = []
    ends = []
    if "bar_close_time" in df_bp.columns and len(df_bp) > 0:
        first_bar_utc = pd.to_datetime(df_bp["bar_close_time"].iloc[0]).tz_localize(chart_tz).tz_convert("UTC")
        t0_ns = int(first_bar_utc.timestamp() * 1e9)
        from .sessions import session_begin_ns
        s_begin = session_begin_ns(t0_ns)
        curr = int(np.searchsorted(ticks.ts_ns, s_begin))
    else:
        curr = 0

    for b in range(n_bars):
        if curr >= n_ticks:
            break
        tv = target_vols[b]
        s = curr
        cum = 0
        e = s
        while e < n_ticks and cum < tv:
            cum += vols[e]
            e += 1
        starts.append(s)
        ends.append(e)
        curr = e

    starts = np.asarray(starts, dtype=np.int64)
    ends = np.asarray(ends, dtype=np.int64)
    o, h, lo, c, v, tbi = _ohlc(ticks, starts, ends)
    s_ns = ticks.ts_ns[starts].astype(np.int64)
    if "bar_close_time" in df_bp.columns:
        t_utc = pd.to_datetime(df_bp["bar_close_time"].values[:len(starts)]).tz_localize(chart_tz).tz_convert("UTC")
        e_ns = t_utc.astype(np.int64).values
    else:
        e_ns = ticks.ts_ns[ends - 1].astype(np.int64)
    sess_idx = df_bp["session_index"].values[:len(starts)].astype(np.int64) if "session_index" in df_bp.columns else None
    return BarSeries(s_ns, e_ns, o, h, lo, c, v, ticks.tick_size, "tick", int(ticks_per_bar), tbi, sess_idx)



@dataclass
class Footprints:
    ask: list       # list[dict[int, float]] volumen agresor comprador por tick de precio
    bid: list       # list[dict[int, float]] volumen agresor vendedor
    total: list
    n_quote: np.ndarray
    n_rule: np.ndarray
    has_quotes: bool


def build_footprints(ticks: TickSeries, bars: BarSeries) -> Footprints:
    nb = len(bars)
    ask = [dict() for _ in range(nb)]
    bid = [dict() for _ in range(nb)]
    total = [dict() for _ in range(nb)]
    n_quote = np.zeros(nb, np.int64)
    n_rule = np.zeros(nb, np.int64)
    has_ba = ticks.bid_ticks is not None and ticks.ask_ticks is not None
    last_price = None
    last_dir = 0
    for i in range(len(ticks)):
        b = int(bars.tick_bar_idx[i])
        p = int(ticks.price_ticks[i])
        vol = float(ticks.volume[i])
        side, by_quote = 0, False
        if has_ba:
            aq, bq = int(ticks.ask_ticks[i]), int(ticks.bid_ticks[i])
            if aq > 0 and bq > 0 and aq >= bq:
                if p >= aq:
                    side, by_quote = 1, True
                elif p <= bq:
                    side, by_quote = -1, True
        if side == 0:
            if last_price is not None:
                side = 1 if p > last_price else (-1 if p < last_price else last_dir)
            if side == 0:
                side = 1  # primer tick sin información (contrato BigTrap2)
        last_price, last_dir = p, side
        if by_quote:
            n_quote[b] += 1
        else:
            n_rule[b] += 1
        m = ask[b] if side > 0 else bid[b]
        m[p] = m.get(p, 0.0) + vol
        total[b][p] = total[b].get(p, 0.0) + vol
    return Footprints(ask, bid, total, n_quote, n_rule, has_quotes=bool(has_ba))


def footprint_volume_mismatches(bars: BarSeries, fps: Footprints, tol: float = 0.5):
    """Lista de (bar_idx, sum_ask_bid, bar_volume, diff) con |diff| > tol.
    Vacío = footprint consistente con el volumen de barra (P1A OK)."""
    out = []
    for b in range(len(bars)):
        s = sum(fps.ask[b].values()) + sum(fps.bid[b].values())
        diff = s - float(bars.volume[b])
        if abs(diff) > tol:
            out.append((b, s, float(bars.volume[b]), diff))
    return out


def p1a_gate(ticks: TickSeries, bars: BarSeries, fps: Footprints) -> dict:
    """Gate P1A de barras/footprint. status PASS/FAIL + diagnósticos (nunca
    silenciados). FAIL si faltan quotes o si hay FOOTPRINT_MISMATCH."""
    diags = []
    if not fps.has_quotes:
        diags.append(dict(code="NO_QUOTES",
                          detail="feed sin bid/ask: footprint no reconstruible fielmente"))
    mism = footprint_volume_mismatches(bars, fps)
    for b, s, v, diff in mism[:20]:
        diags.append(dict(code="FOOTPRINT_MISMATCH", bar=b,
                          detail=f"Σ(ask+bid)={s} vs vol={v} (diff={diff:+.4f})"))
    nq = int(fps.n_quote.sum()); nr = int(fps.n_rule.sum())
    quote_fraction = nq / max(nq + nr, 1)
    status = "FAIL" if diags else "PASS"
    return dict(status=status, n_bars=len(bars), n_ticks=len(ticks),
                n_quote=nq, n_rule=nr, quote_fraction=round(quote_fraction, 4),
                footprint_mismatches=len(mism), diagnostics=diags)
