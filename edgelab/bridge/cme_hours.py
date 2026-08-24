"""Filtro de horario CME para cintas de ticks crudas.

La base de ticks de NT8 exporta `.Last.txt` **sin** aplicar plantilla de sesión, así
que trae prints aislados fuera del horario del exchange (domingo antes de la apertura,
sábado). El chart de NT8 sí los excluye, con lo cual filtrarlos **acerca** la cinta al
oráculo en vez de alejarla.

Medido sobre los 5 contratos GC del universo: **53 ticks** en total, todos en domingo
antes de 17:00 CT o en sábado. Ver `docs/research/FILTRO_HORARIO_CME_2026-08-24.md`.

Qué NO filtra este módulo, a propósito:

- **Cierres anticipados de feriado.** En Thanksgiving 2025 la cinta llega hasta las
  13:29:56 CT, que es el cierre oficial de metales, y el chart de NT8 corta a las 12:00
  CT por un defecto de su plantilla. Esos 408 ticks son operativa real y **se conservan**
  (`docs/research/NT8_PLANTILLA_SESION_CIERRE_FERIADO_2026-08-23.md`).
- Cualquier cosa dentro de la ventana semanal regular.

El único criterio es el marco semanal: **domingo 17:00 CT → viernes 16:00 CT**.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

# Transiciones de horario de verano de EEUU que caen dentro del universo GC.
# Fuera de este rango el módulo falla cerrado en vez de adivinar el huso.
_DST_OUT_2025 = int(datetime(2025, 11, 2, 7, 0, tzinfo=timezone.utc).timestamp())
_DST_IN_2026 = int(datetime(2026, 3, 8, 8, 0, tzinfo=timezone.utc).timestamp())
_DST_OUT_2026 = int(datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc).timestamp())

_VALID_FROM = int(datetime(2025, 3, 9, 8, 0, tzinfo=timezone.utc).timestamp())
_VALID_TO = int(datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc).timestamp())

_NS = 1_000_000_000


def _ct_offset_seconds(ts_s: np.ndarray) -> np.ndarray:
    """Offset de Chicago en segundos: -5 h en CDT, -6 h en CST."""
    cdt = ((ts_s >= _DST_IN_2026) & (ts_s < _DST_OUT_2026)) | (ts_s < _DST_OUT_2025)
    return np.where(cdt, -5 * 3600, -6 * 3600)


def in_cme_week(ts_ns: np.ndarray) -> np.ndarray:
    """Máscara booleana: `True` si el tick cae dentro de dom 17:00 CT → vie 16:00 CT.

    Falla cerrado si algún timestamp queda fuera del rango donde las transiciones de
    horario de verano están declaradas — antes que devolver una máscara con el huso mal.
    """
    ts_ns = np.asarray(ts_ns, dtype=np.int64)
    if ts_ns.size == 0:
        return np.zeros(0, dtype=bool)

    ts_s = ts_ns // _NS
    lo, hi = int(ts_s.min()), int(ts_s.max())
    if lo < _VALID_FROM or hi > _VALID_TO:
        raise ValueError(
            "cme_hours: timestamps fuera del rango con DST declarado "
            f"({datetime.fromtimestamp(lo, tz=timezone.utc)} → "
            f"{datetime.fromtimestamp(hi, tz=timezone.utc)}). "
            "Agregar las transiciones que falten antes de usar el filtro."
        )

    local = ts_s + _ct_offset_seconds(ts_s)
    # weekday(): lunes=0 … domingo=6, calculado desde el 1970-01-01 (jueves=3).
    wd = ((local // 86400) + 3) % 7
    hh = (local % 86400) // 3600

    fuera_sabado = wd == 5
    fuera_viernes = (wd == 4) & (hh >= 16)
    fuera_domingo = (wd == 6) & (hh < 17)
    return ~(fuera_sabado | fuera_viernes | fuera_domingo)


def filter_cme_week(ticks, *, report: bool = False):
    """Devuelve la `TickSeries` sin los ticks fuera del marco semanal de CME.

    Con `report=True` devuelve `(serie, detalle)`, donde `detalle` trae el conteo y las
    fechas afectadas — para poder declarar en el acta qué se descartó.
    """
    from .ticks import TickSeries

    keep = in_cme_week(ticks.ts_ns)
    n_out = int((~keep).sum())

    out = TickSeries(
        ts_ns=ticks.ts_ns[keep],
        price_ticks=ticks.price_ticks[keep],
        bid_ticks=ticks.bid_ticks[keep],
        ask_ticks=ticks.ask_ticks[keep],
        volume=ticks.volume[keep],
        sequence=np.arange(int(keep.sum()), dtype=np.int64),
        tick_size=ticks.tick_size,
    )
    if not report:
        return out

    fechas: dict[str, int] = {}
    for t in ticks.ts_ns[~keep]:
        d = datetime.fromtimestamp(int(t) / 1e9, tz=timezone.utc).strftime("%Y-%m-%d")
        fechas[d] = fechas.get(d, 0) + 1
    return out, {"descartados": n_out, "conservados": int(keep.sum()), "por_fecha": fechas}
