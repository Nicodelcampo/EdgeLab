"""Gate P1A: barras (tiempo y tick), footprint e invariantes NT8-fieles.
Fixtures sintéticos deterministas; sin datos reales."""
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge import common as C
from edgelab.bridge.ticks import TickSeries, load_canonical_parquet


def mk(ts, px, vol, bid=None, ask=None, tick_size=0.25):
    n = len(ts)
    return TickSeries(
        np.asarray(ts, np.int64), np.asarray(px, np.int64), np.asarray(vol, np.float64),
        np.asarray(bid, np.int64) if bid is not None else None,
        np.asarray(ask, np.int64) if ask is not None else None,
        np.arange(n, dtype=np.int64), tick_size, "SYN", "SYN 06-26", "test")


# ---------- helpers NT8-fieles ----------
def test_snap_away_from_zero():
    assert C.snap_to_tick(1.17835, 0.00005) == 23567
    assert C.snap_to_tick(-0.000025, 0.00005) == -1   # 0.5 -> aleja del cero


def test_floor_div_negatives():
    assert C.floor_div(-1, 4) == -1
    assert C.floor_div(-5, 4) == -2
    assert C.floor_div(7, 5) == 1


def test_atr_nt8_expansive_wilder():
    atr = C.Nt8Atr(period=3)
    atr.on_bar(10, 8, None)      # -> 2.0
    atr.on_bar(14, 10, 8)        # tr=6, m=1 -> 6.0
    atr.on_bar(13, 12, 12)       # tr=1, m=2 -> (6+1)/2 = 3.5
    atr.on_bar(20, 10, 13)       # tr=10, m=3 -> (2*3.5+10)/3 = 17/3
    assert atr.values[:3] == [2.0, 6.0, 3.5]
    assert abs(atr.values[3] - 17 / 3) < 1e-12


# ---------- barras ----------
def test_time_bar_boundaries_start_end():
    P = 60 * B.NS
    Bs = 1000 * P
    ts = [Bs, Bs + 30 * B.NS, Bs + 59 * B.NS, Bs + 60 * B.NS, Bs + 90 * B.NS]
    px = [100, 102, 101, 103, 104]
    bars = B.build_time_bars(mk(ts, px, [1] * 5), minutes=1)
    assert len(bars) == 2
    # tick exactamente en fin (Bs+60s) pertenece a la barra siguiente
    assert bars.tick_bar_idx.tolist() == [0, 0, 0, 1, 1]
    assert bars.end_ns[0] == Bs + 60 * B.NS
    assert bars.open_t[0] == 100 and bars.close_t[0] == 101
    assert bars.high_t[0] == 102 and bars.low_t[0] == 100


def test_tick_bars_count():
    ts = [i * B.NS for i in range(5)]
    bars = B.build_tick_bars(mk(ts, [100 + i for i in range(5)], [1] * 5), ticks_per_bar=2)
    assert len(bars) == 3
    assert bars.tick_bar_idx.tolist() == [0, 0, 1, 1, 2]
    assert bars.end_ns[0] == ts[1]          # cierre = ts del último tick de la barra


def test_sequence_tiebreak_equal_ts():
    Bs = 1000 * 60 * B.NS
    ts = [Bs, Bs, Bs + 10 * B.NS]           # dos ticks con ts idéntico
    px = [100, 105, 101]
    bars = B.build_time_bars(mk(ts, px, [1] * 3), minutes=1)
    assert len(bars) == 1
    # open/close respetan el orden del archivo (sequence), no el valor
    assert bars.open_t[0] == 100 and bars.close_t[0] == 101 and bars.high_t[0] == 105


# ---------- footprint / gate P1A ----------
def _quoted_ticks():
    # bid=99, ask=101; price>=ask -> buy(quote), <=bid -> sell(quote), 100 -> tick-rule
    ts = [i * B.NS for i in range(6)]
    px = [101, 99, 100, 101, 99, 100]
    return mk(ts, px, [2, 3, 1, 4, 2, 1], bid=[99] * 6, ask=[101] * 6)


def test_footprint_volume_invariant_and_gate_pass():
    tk = _quoted_ticks()
    bars = B.build_tick_bars(tk, ticks_per_bar=3)
    fps = B.build_footprints(tk, bars)
    assert not B.footprint_volume_mismatches(bars, fps)  # Σ(ask+bid) == vol
    g = B.p1a_gate(tk, bars, fps)
    assert g["status"] == "PASS" and g["quote_fraction"] > 0


def test_footprint_mismatch_detected():
    tk = _quoted_ticks()
    bars = B.build_tick_bars(tk, ticks_per_bar=3)
    fps = B.build_footprints(tk, bars)
    fps.ask[0].clear()                       # rompemos el footprint a propósito
    mism = B.footprint_volume_mismatches(bars, fps)
    assert mism and B.p1a_gate(tk, bars, fps)["status"] == "FAIL"


def test_quote_vs_tickrule_counts():
    tk = _quoted_ticks()
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    assert int(fps.n_quote.sum()) == 4 and int(fps.n_rule.sum()) == 2  # 2 ticks a 100


def test_no_quotes_flagged_not_silent():
    ts = [i * B.NS for i in range(4)]
    tk = mk(ts, [100, 101, 100, 102], [1] * 4, bid=None, ask=None)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    g = B.p1a_gate(tk, bars, fps)
    assert fps.has_quotes is False and g["status"] == "FAIL"
    assert any(d["code"] == "NO_QUOTES" for d in g["diagnostics"])


# ---------- reader F2 (contract + rango + tick_size del catálogo) ----------
def test_load_canonical_parquet_filters_and_ticksize(tmp_path):
    n = 20
    ts = [1_700_000_000_000_000_000 + i * B.NS for i in range(n)]
    tbl = pa.table({
        "ts_utc_ns": pa.array(ts, pa.int64()),
        "price_ticks": pa.array([23566 + (i % 3) for i in range(n)], pa.int64()),
        "bid_ticks": pa.array([23565] * n, pa.int64()),
        "ask_ticks": pa.array([23567] * n, pa.int64()),
        "volume": pa.array([1] * n, pa.int32()),
        "sequence": pa.array(list(range(n)), pa.int64()),
        "instrument": pa.array(["6E"] * n, pa.string()),
        "contract": pa.array(["6E 09-25"] * 10 + ["6E 12-25"] * 10, pa.string()),
    })
    p = tmp_path / "all.parquet"
    pq.write_table(tbl, str(p))
    tk = load_canonical_parquet(str(p), contract="6E 09-25",
                                start_utc_ns=ts[2], end_utc_ns=ts[8])
    assert tk.tick_size == 0.00005          # del catálogo (SIX_E), no float suelto
    assert tk.contract == "6E 09-25"
    assert len(tk) == 6                      # [ts2, ts8): filas 2..7
    with pytest.raises(KeyError):
        load_canonical_parquet(str(p), instrument="ZZ")   # instrument fuera del catálogo
