"""Barrido de intake L2 (tools/l2_intake_sweep.py): idempotencia y resumen de continuidad."""
from __future__ import annotations

from tools.l2_intake_sweep import pending_sessions, sweep

TICK = 0.1


def _csv(day: str) -> str:
    return "\n".join([
        f"L2;0;{day}010000;0;0;0;;4300.0;5",
        f"L2;1;{day}010000;0;0;0;;4299.9;3",
        f"L1;2;{day}010000;1;4300.0;1",
    ]) + "\n"


def test_sweep_ingests_pending_and_is_idempotent(tmp_path):
    src, base = tmp_path / "csv", tmp_path / "base"
    src.mkdir()
    (src / "20260915.csv").write_text(_csv("20260915"), encoding="utf-8")
    (src / "20260916.csv").write_text(_csv("20260916"), encoding="utf-8")
    (src / "notes.csv").write_text("x", encoding="utf-8")          # nombre no-sesion: se ignora
    kw = dict(csv_dir=src, base=base, instrument="GC", contract="GC 12-26", tick_size=TICK,
              downloader_id="test", log=tmp_path / "log.jsonl", out=tmp_path / "out")

    first = sweep(**kw)
    assert [r["session"] for r in first["ingested"]] == ["20260915", "20260916"]
    assert first["conversion_failures"] == 0
    assert first["boundaries_checked"] == 1
    assert pending_sessions(src, base) == []

    second = sweep(**kw)
    assert second["ingested"] == []                                 # nada que re-procesar
    assert (tmp_path / "log.jsonl").read_text(encoding="utf-8").count("\n") == 2
    assert (src / "20260915.csv").exists()                          # no borra por default


def test_sweep_reports_conversion_failure(tmp_path):
    src, base = tmp_path / "csv", tmp_path / "base"
    src.mkdir()
    (src / "20260915.csv").write_text("L1;2;20260915010000;1;4300.0;1\n", encoding="utf-8")   # sin L2
    s = sweep(csv_dir=src, base=base, instrument="GC", contract="GC 12-26", tick_size=TICK,
              downloader_id="test", log=tmp_path / "log.jsonl", out=tmp_path / "out")
    assert s["conversion_failures"] == 1
