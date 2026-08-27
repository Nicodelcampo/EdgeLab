from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / "docs" / "research" / "bt2a_p2a_v1_r1_20260827"
EXPECTED_RESULT_PAYLOAD = (
    "296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_transport(directory: Path, prefix: str) -> tuple[dict, list[dict[str, str]]]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    listed_names = [entry["file"] for entry in manifest["parts"]]
    actual_names = sorted(path.name for path in directory.glob(f"{prefix}.part*"))
    assert actual_names == listed_names

    chunks: list[bytes] = []
    for entry in manifest["parts"]:
        payload = (directory / entry["file"]).read_bytes()
        assert len(payload) == entry["bytes"]
        assert _sha256(payload) == entry["sha256"]
        chunks.append(payload)

    compressed = base64.b64decode(b"".join(chunks), validate=True)
    assert _sha256(compressed) == manifest["decoded_sha256"]
    raw_csv = gzip.decompress(compressed)
    assert _sha256(raw_csv) == manifest["uncompressed_sha256"]
    rows = list(csv.DictReader(io.StringIO(raw_csv.decode("utf-8"), newline="")))
    assert len(rows) == manifest["record_count"]
    return manifest, rows


def test_aggregate_result_reconstructs_frozen_payload() -> None:
    result_dir = PUBLICATION / "result"
    aggregate = json.loads((result_dir / "result_header.json").read_text(encoding="utf-8"))
    expected = aggregate.pop("source_result_payload_sha256")
    assert expected == EXPECTED_RESULT_PAYLOAD

    primary: list[dict] = []
    secondary: list[dict] = []
    for barrier in (5, 9, 18, 30):
        primary.extend(
            json.loads((result_dir / f"primary_B{barrier}.json").read_text(encoding="utf-8"))[
                "primary_family"
            ]
        )
        secondary.extend(
            json.loads((result_dir / f"secondary_B{barrier}.json").read_text(encoding="utf-8"))[
                "secondary_clock_family"
            ]
        )

    aggregate["primary_family"] = primary
    aggregate["secondary_clock_family"] = secondary
    canonical = json.dumps(aggregate, sort_keys=True, separators=(",", ":")).encode()
    assert _sha256(canonical) == expected
    assert len(primary) == 16
    assert len(secondary) == 12
    assert aggregate["n_sessions"] == 234
    assert aggregate["status"] == "COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC"
    assert aggregate["decision"]["label"] == "P2_DIAGNOSTIC_MECHANISM_SUPPORTED"
    assert aggregate["decision"]["negative_cells"] == []
    assert aggregate["decision"]["winner_selected"] is False
    assert aggregate["decision"]["edge_declared"] is False


def test_complete_checkpoint_inventory_reconstructs() -> None:
    _, rows = _load_transport(
        PUBLICATION / "checkpoints" / "complete",
        "checkpoint_inventory_all.csv.gz.b64",
    )
    assert [int(row["session_index"]) for row in rows] == list(range(234))
    assert max(row["cme_session"] for row in rows) == "20260630"
    assert sum(int(row["n_K_ABS"]) for row in rows) == 16940
    assert sum(int(row["n_K_BT2"]) for row in rows) == 5262


def test_complete_source_package_inventory_reconstructs() -> None:
    manifest, rows = _load_transport(
        PUBLICATION / "source-package" / "complete",
        "file_inventory_all.csv.gz.b64",
    )
    assert manifest["record_count"] == 251
    assert len(rows) == 251


def test_publication_firewall_is_fail_closed() -> None:
    status = json.loads((PUBLICATION / "STATUS.json").read_text(encoding="utf-8"))
    assert status["status"] == "COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC"
    assert status["identities"]["result_payload_sha256"] == EXPECTED_RESULT_PAYLOAD
    assert status["firewall"] == {
        "P2A_OUTCOMES_OPENED": True,
        "P2B_RUN": False,
        "L2_OUTCOMES_OPENED": False,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
        "CONFIRMATORY_ELIGIBLE": False,
        "PROMOTION_ELIGIBLE": False,
    }


if __name__ == "__main__":
    test_aggregate_result_reconstructs_frozen_payload()
    test_complete_checkpoint_inventory_reconstructs()
    test_complete_source_package_inventory_reconstructs()
    test_publication_firewall_is_fail_closed()
    print("PASS_BT2A_P2A_REPOSITORY_PUBLICATION")
