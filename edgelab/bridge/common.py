"""Helpers compartidos NT8-fieles: formato InvariantCulture, tiempo, cuantiles
exactos, ATR de NT8, snap AwayFromZero, merge tick/barra (BIP0 primero).

Portado de la implementación de referencia; semántica idéntica a NT8 (es la base
de la paridad, no se "mejora" sin re-verificar contra el oráculo).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

NS_PER_MS = 1_000_000


def tz_of(name: str):
    return timezone.utc if name in ("UTC", "utc") else ZoneInfo(name)


def ns_to_ms(ts_ns: int) -> int:
    """unix_ms (floor), igual que DateTimeOffset.ToUnixTimeMilliseconds()."""
    return int(ts_ns) // NS_PER_MS


def ts_str(ts_ns: int, tz, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """'yyyy-MM-dd HH:mm:ss.fff' (o fmt custom) en la tz del chart."""
    dt = datetime.fromtimestamp(int(ts_ns) / 1e9, tz=timezone.utc).astimezone(tz)
    ms = (int(ts_ns) // NS_PER_MS) % 1000
    return dt.strftime(fmt) + "." + format(ms, "03d")


def fnum(v: float, dec: int) -> str:
    """Equivalente a v.ToString(\"F{dec}\", InvariantCulture)."""
    return format(float(v), f".{dec}f")


def fnum_or_empty(v, dec: int = 4) -> str:
    return "" if (v is None or (isinstance(v, float) and math.isnan(v))) else fnum(v, dec)


def gnum(v: float, max_dec: int = 6) -> str:
    """Equivalente a ToString(\"0.######\") — sin ceros de cola."""
    s = format(float(v), f".{max_dec}f").rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


def plain(v) -> str:
    """Equivalente al ToString() default de double/int para volúmenes."""
    if isinstance(v, float) and float(v).is_integer():
        return str(int(v))
    return str(v)


def quantile_exact(sorted_vals, q: float) -> float:
    """Cuantil exacto SIN interpolación: idx = ceil(q*n)-1 (contrato NT8 v2)."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    idx = math.ceil(q * n) - 1
    idx = max(0, min(n - 1, idx))
    return float(sorted_vals[idx])


def empirical_pct(sorted_vals, x: float) -> float:
    """count(<= x) / n vía búsqueda binaria (contrato NT8 v2)."""
    lo, hi, idx = 0, len(sorted_vals) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] <= x:
            idx = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return (idx + 1) / float(len(sorted_vals))


def floor_div(a: int, b: int) -> int:
    """FloorDiv de C# replicado (Python // ya es floor; correcto para negativos)."""
    return a // b


def snap_to_tick(price: float, tick_size: float) -> int:
    """round(price/tick, MidpointRounding.AwayFromZero) tras snap oficial."""
    x = price / tick_size
    return int(math.floor(x + 0.5)) if x >= 0 else int(math.ceil(x - 0.5))


def tick_and_bar_events(ts_ns, bar_end_ns):
    """Stream fusionado: cierra la barra primaria ANTES del primer tick con
    ts >= end (regla [inicio, fin); empate: BIP0 primero, igual que NT8)."""
    b, nb = 0, len(bar_end_ns)
    for i in range(len(ts_ns)):
        t = ts_ns[i]
        while b < nb and bar_end_ns[b] <= t:
            yield ("bar", b)
            b += 1
        yield ("tick", i)
    while b < nb:
        yield ("bar", b)
        b += 1


class Nt8Atr:
    """ATR de NT8 (Wilder con ventana expansiva), replicado del ATR.cs."""

    def __init__(self, period: int):
        self.period = period
        self.values = []  # ATR por barra cerrada

    def on_bar(self, high: float, low: float, prev_close):
        if not self.values:
            self.values.append(high - low)
            return
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        n = len(self.values)          # CurrentBar del bar que cierra
        m = min(n, self.period)
        self.values.append(((m - 1) * self.values[-1] + tr) / m)
