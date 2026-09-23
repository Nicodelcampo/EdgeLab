"""Ingesta retroactiva de hipótesis cerradas al Hipocampo durable (tools/build_research_history_ledger.py)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edgelab.edge_brain.hippocampus_store import DurableHippocampus  # noqa: E402
from tools import build_research_history_ledger as B  # noqa: E402

EXPECTED_TIP = "29ef1a3e353eba01c4ba1e6c00fb613873742c468b81b0457b8d49f2c3e7407a"


@pytest.fixture(scope="module")
def store():
    return DurableHippocampus(B.LEDGER)


def test_committed_ledger_tip_is_pinned(store):
    assert store.tip_hash == EXPECTED_TIP
    assert store.verify() == EXPECTED_TIP


def test_rebuild_is_byte_identical(tmp_path):
    assert B.build(tmp_path / "rebuilt.jsonl") == EXPECTED_TIP
    assert (tmp_path / "rebuilt.jsonl").read_bytes() == B.LEDGER.read_bytes()


def test_nothing_is_promoted_and_outcomes_stay_closed(store):
    rec = store.memory.reconstruct_episode(B.EPISODE_ID)
    assert rec["episode"].outcomes_inspected is False
    assert len(rec["lessons"]) == len(B.ENTRIES)
    for lesson in rec["lessons"]:
        assert (lesson.status, lesson.confidence, lesson.evidence_record_ids) == ("PROPOSED", "LOW", [])
        assert "Reopen only with:" in lesson.statement


@pytest.mark.parametrize("entry", B.ENTRIES, ids=[e[0] for e in B.ENTRIES])
def test_every_evidence_ref_resolves_to_a_real_file_at_its_commit(entry):
    ref = entry[5]
    if "@" not in ref:
        return                                   # anchor en CLAUDE.md, sin commit pineado
    path, commit = ref.split(":", 1)[1].rsplit("@", 1)
    out = subprocess.run(["git", "cat-file", "-e", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
    if out.returncode != 0 and any(
        marker in out.stderr + out.stdout
        for marker in (b"Not a valid object name", b"invalid object name")
    ):
        pytest.skip(f"commit {commit} no disponible en este clon (shallow/CI)")
    assert out.returncode == 0, f"{path} no existe en {commit}"
