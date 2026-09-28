"""Vista previa ciega de specs: ningún precio posterior a la entrada puede quedar en el archivo."""
import json

import pyarrow as pa
import pyarrow.parquet as pq

from tools import build_spec_preview as B

US = 1_000_000


def _session(tmp_path, s="20260101"):
    rows, r = [], 0
    t0 = 3600 * US
    for k in range(400):                                     # fondo: quotes + trades chicos (historia del umbral)
        t = t0 + k * 10 * US
        rows += [(0, 1002, 5, t, r), (1, 1000, 5, t + 1, r + 1), (2, 1002, 1, t + 2, r + 2)]; r += 3
    tb = t0 + 400 * 10 * US                                  # absorción: compras grandes en el ask 1002, sin romperlo
    rows += [(0, 1002, 50, tb, r), (1, 1001, 5, tb + 1, r + 1)]; r += 2
    for k in range(5):
        rows.append((2, 1002, 40, tb + 2 + k * 1000, r)); r += 1
    for k in range(50):                                      # FUTURO: subida enorme que nunca debe aparecer
        t = tb + 11 * US + k * US
        rows += [(0, 1500 + k, 5, t, r), (1, 1499 + k, 5, t + 1, r + 1), (2, 1500 + k, 3, t + 2, r + 2)]; r += 3
    cols = list(zip(*rows))
    base = tmp_path / "base"
    (base / "l1_quotes").mkdir(parents=True)
    pq.write_table(pa.table(dict(side=pa.array(cols[0], pa.int8()), price_tick=pa.array(cols[1], pa.int64()),
                                 size=pa.array(cols[2], pa.int64()), ts_us=pa.array(cols[3], pa.int64()),
                                 source_row=pa.array(cols[4], pa.int64()))), base / "l1_quotes" / f"{s}.parquet")
    return base, tb


def test_preview_contains_no_price_after_entry(tmp_path):
    base, tb = _session(tmp_path)
    spec = dict(spec_id="SPEC-T", data=dict(base=str(base), preview_sessions=["20260101"]),
                grid=dict(max_hold_s=[60]), sample=dict(examples=500, seed=1))
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(spec), encoding="utf-8")
    B._TR_CACHE.clear()
    assert B.main(["--spec", str(sp), "--out", str(tmp_path / "out")]) == 0
    d = json.loads((tmp_path / "out" / "spec_SPEC-T.json").read_text(encoding="utf-8"))
    assert d["blind"] is True and d["examples"], "debe haber al menos un ejemplo"
    target = [e for e in d["examples"] if e["level_tick"] == 1002]
    assert target, "la absorcion en 1002 debe estar en la muestra"
    for e in target:
        assert e["side"] == "SHORT"                          # compras absorbidas en el ask -> fade corto
        assert all(c["time"] * US < e["entry_ts_us"] for c in e["candles"])
        assert max(c["high"] for c in e["candles"]) < 1500   # la subida posterior no está en los datos
    assert len(d["spec_sha256"]) == 64 and len(d["preview_sha256"]) == 64
