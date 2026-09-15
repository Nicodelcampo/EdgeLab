from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

from edgelab.data.contract_regime import build_contract_regime
from edgelab.data.continuous_contract import (
    ContinuousContractError,
    LINEAGE_COLUMNS,
    build_continuous_series,
)


class ContinuousContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

        # Build dummy regime manifest with 2 contracts and 4 dates
        self.calendar = [20260309, 20260310, 20260311, 20260312]
        self.contracts = [
            {
                "root": "NQ",
                "contract": "NQ_03-26",
                "expiry_ordinal": 202603,
                "first_trade_date": 20260309,
                "last_trade_date": 20260312,
            },
            {
                "root": "NQ",
                "contract": "NQ_06-26",
                "expiry_ordinal": 202606,
                "first_trade_date": 20260309,
                "last_trade_date": 20260312,
            },
        ]
        # Roll on 20260311 because 06-26 volume on 20260310 (150) > 03-26 volume (100)
        self.volumes = [
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260309, "volume": 120, "complete_session": True},
            {"root": "NQ", "contract": "NQ_06-26", "trade_date": 20260309, "volume": 50, "complete_session": True},
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260310, "volume": 100, "complete_session": True},
            {"root": "NQ", "contract": "NQ_06-26", "trade_date": 20260310, "volume": 150, "complete_session": True},
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260311, "volume": 80, "complete_session": True},
            {"root": "NQ", "contract": "NQ_06-26", "trade_date": 20260311, "volume": 200, "complete_session": True},
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260312, "volume": 60, "complete_session": True},
            {"root": "NQ", "contract": "NQ_06-26", "trade_date": 20260312, "volume": 220, "complete_session": True},
        ]
        self.manifest = build_contract_regime(
            contracts=self.contracts,
            daily_volumes=self.volumes,
            calendar_trade_dates=self.calendar,
            source_identity={"mock": True},
        )

        # Create mock source parquets for NQ_03-26 and NQ_06-26
        self.p_0326 = self.tmp_path / "NQ_03-26_ticks.parquet"
        self.p_0626 = self.tmp_path / "NQ_06-26_ticks.parquet"

        # Contract 03-26 ticks on 20260310 (Day 2, active)
        t_03 = pa.table({
            "ts_utc_ns": [1773100000000000000, 1773100001000000000],
            "sequence": [1, 2],
            "price_ticks": [18000, 18001],
            "bid_ticks": [18000, 18000],
            "ask_ticks": [18001, 18001],
            "volume": [5, 10],
            "instrument": ["NQ", "NQ"],
            "contract": ["03-26", "03-26"],
            "trade_date": [20260310, 20260310],
            "source_file": ["NQ_03-26_ticks.parquet", "NQ_03-26_ticks.parquet"],
            "source_row": [0, 1],
        })
        pq.write_table(t_03, self.p_0326)

        # Contract 06-26 ticks on 20260311 and 20260312 (Day 3 & 4, active)
        t_06 = pa.table({
            "ts_utc_ns": [1773200000000000000, 1773300000000000000],
            "sequence": [1, 1],
            "price_ticks": [18100, 18150],
            "bid_ticks": [18099, 18149],
            "ask_ticks": [18100, 18150],
            "volume": [12, 15],
            "instrument": ["NQ", "NQ"],
            "contract": ["06-26", "06-26"],
            "trade_date": [20260311, 20260312],
            "source_file": ["NQ_06-26_ticks.parquet", "NQ_06-26_ticks.parquet"],
            "source_row": [0, 1],
        })
        pq.write_table(t_06, self.p_0626)

        self.source_paths = {
            "NQ_03-26": self.p_0326,
            "NQ_06-26": self.p_0626,
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_continuous_series_preserves_actual_prices(self) -> None:
        table = build_continuous_series(
            root="NQ",
            regime_manifest=self.manifest,
            contract_source_paths=self.source_paths,
        )
        # Check prices: 18000, 18001 from 03-26, and 18100, 18150 from 06-26
        prices = table["price_ticks"].to_pylist()
        self.assertEqual(prices, [18000, 18001, 18100, 18150])

    def test_causal_contract_selection(self) -> None:
        table = build_continuous_series(
            root="NQ",
            regime_manifest=self.manifest,
            contract_source_paths=self.source_paths,
        )
        contracts = table["contract"].to_pylist()
        trade_dates = table["trade_date"].to_pylist()
        self.assertEqual(contracts[:2], ["NQ_03-26", "NQ_03-26"])
        self.assertEqual(trade_dates[:2], [20260310, 20260310])
        self.assertEqual(contracts[2:], ["NQ_06-26", "NQ_06-26"])
        self.assertEqual(trade_dates[2:], [20260311, 20260312])

    def test_state_reset_flag_at_rolls_post_sort(self) -> None:
        table = build_continuous_series(
            root="NQ",
            regime_manifest=self.manifest,
            contract_source_paths=self.source_paths,
        )
        flags = table["state_reset_flag"].to_pylist()
        # Row 0 is first row of series -> True
        self.assertTrue(flags[0])
        self.assertFalse(flags[1])
        # Row 2 is first row of NQ_06-26 (new regime_id) -> True
        self.assertTrue(flags[2])
        self.assertFalse(flags[3])

    def test_state_reset_flag_with_disordered_source_rows(self) -> None:
        # Construct source table with inverted timestamp order
        p_disordered = self.tmp_path / "NQ_03-26_disordered.parquet"
        t_disordered = pa.table({
            "ts_utc_ns": [1773100005000000000, 1773100000000000000],  # later first, earlier second
            "sequence": [2, 1],
            "price_ticks": [18005, 18000],
            "bid_ticks": [18005, 18000],
            "ask_ticks": [18006, 18001],
            "volume": [1, 1],
            "instrument": ["NQ", "NQ"],
            "contract": ["03-26", "03-26"],
            "trade_date": [20260310, 20260310],
            "source_file": ["NQ_03-26_disordered.parquet", "NQ_03-26_disordered.parquet"],
            "source_row": [0, 1],
        })
        pq.write_table(t_disordered, p_disordered)

        paths = dict(self.source_paths)
        paths["NQ_03-26"] = p_disordered

        table = build_continuous_series(
            root="NQ",
            regime_manifest=self.manifest,
            contract_source_paths=paths,
        )
        # Verify timestamps are monotonically sorted post-sort
        ts = table["ts_utc_ns"].to_pylist()
        self.assertEqual(ts[0], 1773100000000000000)
        self.assertEqual(ts[1], 1773100005000000000)
        # Reset flag must be True on earliest row post-sort
        flags = table["state_reset_flag"].to_pylist()
        self.assertTrue(flags[0])
        self.assertFalse(flags[1])

    def test_lineage_columns_presence_and_validity(self) -> None:
        table = build_continuous_series(
            root="NQ",
            regime_manifest=self.manifest,
            contract_source_paths=self.source_paths,
        )
        self.assertEqual(len(LINEAGE_COLUMNS), 10)
        for col in LINEAGE_COLUMNS:
            self.assertIn(col, table.column_names)

        sha = self.manifest["manifest_sha256"]
        self.assertTrue(all(s == sha for s in table["roll_manifest_sha256"].to_pylist()))
        self.assertTrue(all(r == "NQ" for r in table["root"].to_pylist()))

    def test_rejects_duplicate_ts_and_sequence(self) -> None:
        p_dup = self.tmp_path / "NQ_03-26_dup.parquet"
        t_dup = pa.table({
            "ts_utc_ns": [1773100000000000000, 1773100000000000000],  # Identical ts
            "sequence": [1, 1],                                        # Identical seq
            "price_ticks": [18000, 18000],
            "bid_ticks": [18000, 18000],
            "ask_ticks": [18001, 18001],
            "volume": [1, 1],
            "instrument": ["NQ", "NQ"],
            "contract": ["03-26", "03-26"],
            "trade_date": [20260310, 20260310],
            "source_file": ["NQ_03-26_dup.parquet", "NQ_03-26_dup.parquet"],
            "source_row": [0, 1],
        })
        pq.write_table(t_dup, p_dup)

        paths = dict(self.source_paths)
        paths["NQ_03-26"] = p_dup

        with self.assertRaisesRegex(ContinuousContractError, "Duplicate .* detected"):
            build_continuous_series(
                root="NQ",
                regime_manifest=self.manifest,
                contract_source_paths=paths,
            )

    def test_rejects_content_level_micro_standard_mixing(self) -> None:
        p_mnq_disguised = self.tmp_path / "NQ_03-26_disguised.parquet"
        t_bad = pa.table({
            "ts_utc_ns": [1773100000000000000],
            "sequence": [1],
            "price_ticks": [18000],
            "bid_ticks": [18000],
            "ask_ticks": [18001],
            "volume": [1],
            "instrument": ["MNQ"],  # Internal content is MNQ, but file was mapped to NQ!
            "contract": ["03-26"],
            "trade_date": [20260310],
            "source_file": ["NQ_03-26_disguised.parquet"],
            "source_row": [0],
        })
        pq.write_table(t_bad, p_mnq_disguised)

        paths = dict(self.source_paths)
        paths["NQ_03-26"] = p_mnq_disguised

        with self.assertRaisesRegex(ContinuousContractError, "Content mismatch.*MNQ"):
            build_continuous_series(
                root="NQ",
                regime_manifest=self.manifest,
                contract_source_paths=paths,
            )

    def test_rejects_manifest_micro_standard_mixing(self) -> None:
        mixed_contracts = [
            {
                "root": "NQ",
                "contract": "NQ_03-26",
                "expiry_ordinal": 202603,
                "first_trade_date": 20260309,
                "last_trade_date": 20260312,
            },
            {
                "root": "NQ",
                "contract": "MNQ_06-26",
                "expiry_ordinal": 202606,
                "first_trade_date": 20260309,
                "last_trade_date": 20260312,
            },
        ]
        mixed_vols = [
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260309, "volume": 100, "complete_session": True},
            {"root": "NQ", "contract": "MNQ_06-26", "trade_date": 20260309, "volume": 50, "complete_session": True},
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260310, "volume": 100, "complete_session": True},
            {"root": "NQ", "contract": "MNQ_06-26", "trade_date": 20260310, "volume": 50, "complete_session": True},
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260311, "volume": 100, "complete_session": True},
            {"root": "NQ", "contract": "MNQ_06-26", "trade_date": 20260311, "volume": 50, "complete_session": True},
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": 20260312, "volume": 100, "complete_session": True},
            {"root": "NQ", "contract": "MNQ_06-26", "trade_date": 20260312, "volume": 50, "complete_session": True},
        ]
        mixed_manifest = build_contract_regime(
            contracts=mixed_contracts,
            daily_volumes=mixed_vols,
            calendar_trade_dates=self.calendar,
            source_identity={"mock": True},
        )
        with self.assertRaises(ContinuousContractError):
            build_continuous_series(
                root="NQ",
                regime_manifest=mixed_manifest,
                contract_source_paths=self.source_paths,
            )

    def test_writes_to_disk_with_exact_output_name(self) -> None:
        out_file = self.tmp_path / "NQ_CONT_CAUSAL_D1.parquet"
        build_continuous_series(
            root="NQ",
            regime_manifest=self.manifest,
            contract_source_paths=self.source_paths,
            output_parquet_path=out_file,
        )
        self.assertTrue(out_file.exists())
        read_back = pq.read_table(out_file)
        self.assertEqual(len(read_back), 4)


if __name__ == "__main__":
    unittest.main()
