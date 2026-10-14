import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

P = Path(__file__).resolve().parents[2] / "tools/research_ops/audits/audit_liquid_release.py"
spec = importlib.util.spec_from_file_location("independent_liquid_audit", P)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def table(td=20260930, timestamp=audit.CUTOFF_NS-1, rows=2):
    data = {n: pa.array(np.zeros(rows), type=t) for n, t in audit.EXPECTED_TYPES.items()}
    for k, vals in {
        "ts_utc_ns": [timestamp]*rows, "trade_date": [td]*rows, "price_ticks": [100]*rows,
        "bid_ticks": [99]*rows, "ask_ticks": [100]*rows, "volume": [1]*rows,
        "aggressor": [1]*rows, "regime_id": [1]*rows, "outside_regular": [False]*rows,
        "release_row": list(range(rows)), "source_row": list(range(rows)),
    }.items():
        data[k] = pa.array(vals, type=audit.EXPECTED_TYPES[k])
    data["root"] = pa.array(["ES"]*rows).dictionary_encode()
    data["contract"] = pa.array(["ES 12-26"]*rows).dictionary_encode()
    return pa.table(data)


class LiquidAudit(unittest.TestCase):
    def fixture(self, tables, statistics=True):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        path = root / "data/ES_ticks.parquet"
        path.parent.mkdir()
        with pq.ParquetWriter(path, tables[0].schema, write_statistics=statistics) as w:
            for t in tables:
                w.write_table(t)
        m = dict(schema="edgelab_liquid_release_v1", release_id="synthetic",
                 status="CANDIDATE_NOT_RESEARCH_APPROVED", research_allowed=False,
                 assets={"ES": dict(file="data/ES_ticks.parquet", bytes=path.stat().st_size,
                                    sha256=audit.sha(path), rows=sum(t.num_rows for t in tables))},
                 metadata_files={})
        mp = root / "release_manifest.json"
        mp.write_text(json.dumps(m))
        return root, path, audit.sha(mp)

    def stop_without_payload(self, tables, statistics=True):
        _, path, _ = self.fixture(tables, statistics)
        with mock.patch.object(pq.ParquetFile, "read_row_group", side_effect=AssertionError("payload")), \
             mock.patch.object(pq.ParquetFile, "read_row_groups", side_effect=AssertionError("payload")), \
             mock.patch.object(pq.ParquetFile, "iter_batches", side_effect=AssertionError("payload")):
            with self.assertRaises(audit.AuditStop):
                audit.footer_gate(path)

    def test_allowed_footer_no_payload(self):
        _, path, _ = self.fixture([table()])
        with mock.patch.object(pq.ParquetFile, "iter_batches", side_effect=AssertionError("payload")):
            _, groups = audit.footer_gate(path)
        self.assertEqual(sum(g["rows"] for g in groups), 2)

    def test_timestamp_reserved_mislabeled_date(self):
        self.stop_without_payload([table(timestamp=audit.CUTOFF_NS)])

    def test_trading_date_reserved_even_timestamp_allowed(self):
        self.stop_without_payload([table(td=20261001)])

    def test_mixed_group(self):
        t = table().set_column(9, table().schema.field(9), table().column(9))
        # Locate by name, not by assumed column order.
        i = t.schema.get_field_index("trade_date")
        t = t.set_column(i, "trade_date", pa.array([20260929, 20260930], pa.int32()))
        self.stop_without_payload([t])

    def test_statistics_absent(self):
        self.stop_without_payload([table()], statistics=False)

    def test_clock_label_disagreement(self):
        self.stop_without_payload([table(td=20260929)])

    def test_schema_missing_clock(self):
        self.stop_without_payload([table().drop(["ts_utc_ns"])])

    def test_null_clock(self):
        t = table()
        i = t.schema.get_field_index("ts_utc_ns")
        self.stop_without_payload([t.set_column(i, "ts_utc_ns", pa.array([None, audit.CUTOFF_NS-1], pa.int64()))])

    def test_hash_mismatch(self):
        root, _, _ = self.fixture([table()])
        with self.assertRaises(audit.AuditStop):
            audit.verify_files(root, "0"*64)

    def test_tampered_asset(self):
        root, path, pin = self.fixture([table()])
        b = bytearray(path.read_bytes())
        b[10] ^= 1
        path.write_bytes(b)
        with self.assertRaises(audit.AuditStop):
            audit.verify_files(root, pin)

    def test_unexpected_file(self):
        root, _, pin = self.fixture([table()])
        (root / "unlisted.txt").write_text("synthetic")
        with self.assertRaises(audit.AuditStop):
            audit.verify_files(root, pin)

    def test_global_gate_stops_before_metadata_or_any_asset(self):
        root, _, pin = self.fixture([table(timestamp=audit.CUTOFF_NS)])
        with tempfile.TemporaryDirectory() as out, \
             mock.patch.object(audit, "metadata_audit", side_effect=AssertionError("metadata")), \
             mock.patch.object(audit, "audit_asset", side_effect=AssertionError("payload")):
            r = audit.run_audit(root, pin, out)
        self.assertEqual(r["status"], "STOP")
        self.assertFalse(r["market_payload_batches_started"])

    def test_metadata_hash_required(self):
        root, _, _ = self.fixture([table()])
        mp = root / "release_manifest.json"
        m = json.loads(mp.read_text())
        m["metadata_files"]["metadata/missing.json"] = dict(bytes=2, sha256="0"*64)
        mp.write_text(json.dumps(m))
        with self.assertRaises(audit.AuditStop):
            audit.verify_files(root, audit.sha(mp))

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(audit.AuditStop):
                audit.checked_path(root, "../escaped")

    def test_real_download_forbidden_on_host(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(audit.AuditStop):
                audit.download_inputs(root, {}, {})

    def test_safe_synthetic_stream_reconciles(self):
        import pandas as pd
        root, path, _ = self.fixture([table()])
        pf, groups = audit.footer_gate(path)
        frames = {"session_index": pd.DataFrame([dict(instrument="ES", trade_date=20260930,
                    status="SELECTED", contract="ES 12-26", regime_id=1, rows_written=2)]),
                  "source_manifest": pd.DataFrame([dict(instrument="ES", source_id=0, contract="ES 12-26")])}
        r = audit.audit_asset("ES", pf, groups, dict(rows=2, sessions=1,
                              first_trade_date=20260930, last_trade_date=20260930), frames)
        self.assertTrue(r["technical_checks_passed"])
        self.assertEqual(r["rows"], 2)


if __name__ == "__main__":
    unittest.main()