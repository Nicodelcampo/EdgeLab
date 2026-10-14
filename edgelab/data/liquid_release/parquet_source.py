"""Lector de parquets derivados canonical_tick_v1 con la misma salida que `nt8_text.iter_decoded` (fuente de respaldo 'P').

Holdout: sólo se leen row groups con ts máximo < cutoff (por estadísticas). Un row group sin estadísticas o que cruce el cutoff
no se lee (se cuenta). Se usan los precios/quotes del parquet y el agresor se RECALCULA con la regla de quotes v1 para que todo
el producto sea homogéneo.
"""
from __future__ import annotations

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq

CUTOFF_UTC_NS = 1_790_805_600_000_000_000      # 2026-09-30T22:00:00Z


def iter_parquet(path, tick_size: float, cutoff_ns: int = CUTOFF_UTC_NS):
    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    cols = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "volume"] + (["tick_type"] if "tick_type" in names else [])
    ci = names.index("ts_utc_ns")
    stats = dict(row_groups_read=0, row_groups_skipped_reserved=0, row_groups_mixed_not_read=0, row_groups_without_stats=0)

    def gen():
        base = 0
        for g in range(pf.metadata.num_row_groups):
            nrows = pf.metadata.row_group(g).num_rows
            st = pf.metadata.row_group(g).column(ci).statistics
            if st is None or not st.has_min_max:
                stats["row_groups_without_stats"] += 1
                base += nrows
                continue
            if int(st.min) >= cutoff_ns:
                stats["row_groups_skipped_reserved"] += 1
                base += nrows
                continue
            if int(st.max) >= cutoff_ns:
                stats["row_groups_mixed_not_read"] += 1
                base += nrows
                continue
            t = pf.read_row_group(g, columns=cols)
            rowidx = np.arange(base, base + nrows, dtype=np.int64)
            base += nrows
            if "tick_type" in t.schema.names:
                keep = pc.equal(pc.cast(t["tick_type"], "string"), "trade").to_numpy(zero_copy_only=False)
                t = t.filter(keep)
                rowidx = rowidx[keep]
            stats["row_groups_read"] += 1
            ts = t["ts_utc_ns"].to_numpy()
            day = ts.astype("datetime64[ns]").astype("datetime64[D]")
            y = day.astype("datetime64[Y]").astype(int) + 1970
            mo = day.astype("datetime64[M]").astype(int) % 12 + 1
            d = (day - day.astype("datetime64[M]")).astype(int) + 1
            hour = ((ts.astype("datetime64[ns]") - day).astype("timedelta64[h]")).astype(int)
            bidt, askt = t["bid_ticks"].to_numpy(), t["ask_ticks"].to_numpy()
            yield dict(ts_raw_ns=ts, date=(y * 10000 + mo * 100 + d).astype(np.int64), hour=hour.astype(np.int64),
                       last=t["price_ticks"].to_numpy() * tick_size, bid=np.where(bidt > 0, bidt * tick_size, 0.0),
                       ask=np.where(askt > 0, askt * tick_size, 0.0), vol=t["volume"].to_numpy().astype(np.int64),
                       row_index=rowidx)
    return gen(), stats
