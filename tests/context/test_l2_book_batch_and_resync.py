"""28/09: cruce transitorio dentro de un lote del mismo timestamp, y resync al comenzar archivo nuevo."""
import pandas as pd

from edgelab.context.l2_gate import L2Book, extract_minute_features


def _snap(book, bid, ask):
    for i in range(3):
        book.apply(0, 0, i, ask + i, 1)
        book.apply(1, 0, i, bid - i, 1)


def test_transient_cross_inside_batch_is_not_invalid():
    b = L2Book(); _snap(b, 100, 101)
    b.apply(0, 0, 0, 100, 2, check_cross=False)      # ask nuevo en 100 antes de borrar el bid en 100
    b.apply(1, 2, 0, 100, 0, check_cross=True)
    assert b.ready and b.asks.levels[0][0] == 100 and b.bids.levels[0][0] == 99 and b.crossed_events == 0


def test_cross_at_batch_end_is_counted_but_book_survives():
    b = L2Book(); _snap(b, 100, 101)
    b.apply(1, 0, 0, 102, 1)                  # cruce real (preapertura): se cuenta, no se vacía
    assert b.crossed_events == 1 and b.ready
    b.apply(1, 2, 0, 102, 0)                  # sale el bid cruzado: el libro vuelve a estar sano
    assert b.bids.levels[0][0] == 100 and b.crossed_events == 1


def _rows(ts0, bid, ask, start_row, resync):
    rows = []
    for i in range(3):
        rows.append(dict(side=0, operation=0, level=i, price_tick=ask + i, size=1, ts_us=ts0))
        rows.append(dict(side=1, operation=0, level=i, price_tick=bid - i, size=1, ts_us=ts0))
    df = pd.DataFrame(rows); df["source_row"] = range(start_row, start_row + len(df))
    df["resync"] = False; df.loc[0, "resync"] = resync
    return df


def test_resync_rebuilds_book_after_reset():
    a = _rows(0, 100, 101, 0, True)
    cross = pd.DataFrame([dict(side=1, operation=2, level=7, price_tick=105, size=1, ts_us=1, source_row=100, resync=False)])
    b = _rows(120_000_000, 200, 201, 200, True)
    l2 = pd.concat([a, cross, b], ignore_index=True)
    l1 = pd.DataFrame(dict(side=pd.Series([], dtype="int64"), price_tick=pd.Series([], dtype="int64"),
                           size=pd.Series([], dtype="int64"), source_row=pd.Series([], dtype="int64"),
                           ts_us=pd.Series([], dtype="int64")))
    feats, diag = extract_minute_features(l2, l1, session="x")
    assert diag["book_resyncs"] == 2
    last = feats.sort_values("minute_id").iloc[-1]
    assert bool(last["book_ready"])


def test_tail_gap_keeps_indices_aligned_and_deep_gaps_still_fail():
    b = L2Book()
    for i in range(9):                         # foto de 9 niveles en un libro de 10
        b.apply(0, 0, i, 101 + i, 1); b.apply(1, 0, i, 100 - i, 1)
    b.apply(0, 2, 0, 101, 0)                   # sale el mejor ask (quedan 8)...
    b.apply(0, 0, 9, 115, 1)                   # ...y NT8 inserta su 10.º nivel: hueco de 1 en la cola
    assert b.asks.invalid_events == 0 and b.asks.levels[8] == (None, 0) and b.asks.levels[9] == (115, 1)
    b.apply(0, 1, 8, 111, 2)                   # llega el nivel desconocido: se completa
    assert b.asks.levels[8] == (111, 2) and b.ready
    bad = b.apply(1, 1, 7 + 20, 50, 1)         # salto grande fuera de la regla: sigue fallando cerrado
    assert bad["valid"] is False
