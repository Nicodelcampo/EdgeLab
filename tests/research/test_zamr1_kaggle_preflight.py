# -*- coding: utf-8 -*-
"""Tests del transporte y descubrimiento de Notebook 00."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "kaggle/zamr1/notebooks/00_validate_contract.py"
SPEC = importlib.util.spec_from_file_location("zamr1_notebook_00", SCRIPT)
assert SPEC and SPEC.loader
NB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NB)


def _write_csv_tables(root: Path):
    pd.DataFrame([{"session_key": "s"}]).to_csv(root / "events_long.csv", index=False)
    pd.DataFrame([{"session_key": "s"}]).to_csv(root / "zones_long.csv", index=False)


def test_descubre_layout_anidado_de_kaggle(tmp_path, monkeypatch):
    monkeypatch.delenv("EDGELAB_KAGGLE_INPUT", raising=False)
    root = tmp_path / "datasets/user/edgelab-zamr1"
    root.mkdir(parents=True)
    (root / "contract.json").write_text(
        json.dumps({"schema_version": NB.EXPECTED_SCHEMA}), encoding="utf-8"
    )
    assert NB.find_input_root(tmp_path) == root.resolve()


def test_descubrimiento_ambiguo_falla(tmp_path, monkeypatch):
    monkeypatch.delenv("EDGELAB_KAGGLE_INPUT", raising=False)
    for name in ("a", "b"):
        root = tmp_path / name
        root.mkdir()
        (root / "contract.json").write_text(
            json.dumps({"schema_version": NB.EXPECTED_SCHEMA}), encoding="utf-8"
        )
    with pytest.raises(RuntimeError, match="exactamente un input"):
        NB.find_input_root(tmp_path)


def test_csv_truth_known_solo_pasa_en_z0(tmp_path):
    _write_csv_tables(tmp_path)
    events, zones, transport = NB.load_tables(
        tmp_path,
        {"pilot_stage": "Z0_SYNTHETIC_ENVIRONMENT", "transport_format": "csv_truth_known"},
    )
    assert transport == "csv_truth_known"
    assert len(events) == len(zones) == 1


def test_csv_en_z1_falla_cerrado(tmp_path):
    _write_csv_tables(tmp_path)
    with pytest.raises(RuntimeError, match="sólo para Z0"):
        NB.load_tables(
            tmp_path,
            {"pilot_stage": "Z1_BIGTRAP2_DEFAULTS", "transport_format": "csv_truth_known"},
        )


def test_path_de_hash_no_puede_escapar(tmp_path):
    with pytest.raises(RuntimeError, match="fuera del dataset"):
        NB.safe_child(tmp_path, "../secret.txt")
