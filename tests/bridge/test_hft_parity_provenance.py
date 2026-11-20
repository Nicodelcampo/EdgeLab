from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_historical_oracle_discloses_python_backfill() -> None:
    evidence = json.loads((REPO / "data/nt8_oracles/paridad_hftzones_nq_v2_exact.json").read_text())
    assert evidence["formal_classification"] == "NOT_FULLY_CERTIFIED_PYTHON_BACKFILLED_TERMINATION_REASON"
    assert evidence["python_backfilled_fields"] == ["termination_reason"]
    assert evidence["independently_compared_fields_total"] == 5438 * 37
    assert evidence["fields_compared_total"] == 5438 * 38


def test_python_backfill_requires_diagnostic_acknowledgement() -> None:
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools/patch_hft_v2_oracle_termination.py")],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0
    assert "--diagnostic-only" in proc.stderr
    assert "never NT8 parity evidence" in proc.stderr
