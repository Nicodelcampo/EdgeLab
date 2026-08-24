#!/usr/bin/env python3
"""Entrena o ejecuta el HMM3 GATE sobre features target-free reales.

Uso desde la raíz del repo:
  python -m modules.gate.integration.train_label_hmm3 train \
    --features features.parquet --train-cutoff 2026-07-01T00:00:00Z \
    --checkpoint-out artifacts/gate_hmm3_checkpoint.json

  python -m modules.gate.integration.train_label_hmm3 label \
    --features features.parquet --checkpoint artifacts/gate_hmm3_checkpoint.json \
    --labels-out artifacts/gate_context_labels.parquet
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from modules.gate.core.gate_hmm3_forward import (
    HMM3Checkpoint,
    HMM3Config,
    STATE_NAMES,
    fit_hmm3,
    forward_filter,
)

IDENTITY = ["instrument", "contract", "cme_session"]


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError("features debe ser .parquet/.pq/.csv")


def _write_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".parquet", ".pq"}:
        frame.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        frame.to_csv(path, index=False)
    else:
        raise ValueError("salida debe ser .parquet/.pq/.csv")


def _file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _commit_and_clean() -> str:
    commit = _git(["rev-parse", "HEAD"])
    dirty = _git(["status", "--porcelain"])
    if dirty:
        raise RuntimeError("worktree dirty: no se emite checkpoint ni label formal")
    return commit


def _prepare_features(frame: pd.DataFrame, feature_names: tuple[str, ...]):
    required = [*IDENTITY, "data_window_end", "feature_available_at", *feature_names]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"faltan columnas: {missing}")
    out = frame.copy()
    for key in IDENTITY:
        out[key] = out[key].astype(str)
    out["data_window_end"] = pd.to_datetime(out["data_window_end"], utc=True, errors="raise")
    out["feature_available_at"] = pd.to_datetime(
        out["feature_available_at"], utc=True, errors="raise"
    )
    if (out["data_window_end"] > out["feature_available_at"]).any():
        raise ValueError("hay features publicadas antes del fin de su ventana")
    out = out.sort_values(IDENTITY + ["feature_available_at"], kind="mergesort").reset_index(drop=True)
    gap = out.groupby(IDENTITY, sort=False)["feature_available_at"].diff().gt(pd.Timedelta(minutes=1))
    new_identity = out[IDENTITY].ne(out[IDENTITY].shift()).any(axis=1)
    segment = (new_identity | gap.fillna(False)).cumsum().astype(str)
    sequence_ids = (
        out["instrument"] + "|" + out["contract"] + "|" + out["cme_session"] + "|" + segment
    ).tolist()
    matrix = out.loc[:, feature_names].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    finite = np.isfinite(matrix).all(axis=1)
    return out, matrix, sequence_ids, finite


def train(args: argparse.Namespace) -> None:
    features_path = Path(args.features)
    commit = _commit_and_clean()
    config = HMM3Config()
    frame, matrix, sequence_ids, finite = _prepare_features(_read_frame(features_path), config.feature_names)
    cutoff = pd.Timestamp(args.train_cutoff)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")
    train_mask = (frame["feature_available_at"] < cutoff).to_numpy() & finite
    if not bool(train_mask.any()):
        raise ValueError("cutoff no deja filas finitas de entrenamiento")
    checkpoint = fit_hmm3(
        matrix[train_mask],
        [sid for sid, keep in zip(sequence_ids, train_mask) if keep],
        config=config,
        code_commit=commit,
    )
    checkpoint_path = Path(args.checkpoint_out)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.save(checkpoint_path)
    manifest = {
        "status": "FORMAL_TARGET_FREE_CHECKPOINT",
        "model_id": checkpoint.model_id,
        "checkpoint_sha256": checkpoint.checkpoint_sha256,
        "config_sha256": checkpoint.config_sha256,
        "features_file": str(features_path),
        "features_file_sha256": _file_sha256(features_path),
        "train_cutoff_exclusive": cutoff.isoformat(),
        "training_rows": checkpoint.training_rows,
        "training_sequences": checkpoint.training_sequences,
        "training_matrix_sha256": checkpoint.training_matrix_sha256,
        "code_commit": commit,
        "worktree_clean": True,
        "outcomes_accessed": False,
    }
    manifest_path = checkpoint_path.with_suffix(checkpoint_path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


def label(args: argparse.Namespace) -> None:
    features_path = Path(args.features)
    commit = _commit_and_clean()
    checkpoint = HMM3Checkpoint.load(args.checkpoint)
    frame, matrix, sequence_ids, finite = _prepare_features(
        _read_frame(features_path), checkpoint.feature_names
    )
    if not bool(finite.all()):
        bad = int((~finite).sum())
        raise ValueError(f"{bad} filas no finitas; resolver burn-in, no imputar en inferencia")
    posterior = forward_filter(matrix, sequence_ids, checkpoint)
    hard = posterior.argmax(axis=1)
    sticky = np.zeros(len(hard), dtype=np.int64)
    for i in range(1, len(hard)):
        sticky[i] = sticky[i - 1] + 1 if (
            sequence_ids[i] == sequence_ids[i - 1] and hard[i] == hard[i - 1]
        ) else 0
    run_material = {
        "model_id": checkpoint.model_id,
        "features_file_sha256": _file_sha256(features_path),
        "code_commit": commit,
    }
    run_id = "gate_" + sha256(
        json.dumps(run_material, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    labels = frame[[*IDENTITY, "data_window_end", "feature_available_at"]].copy()
    labels["context_state"] = [STATE_NAMES[int(value)] for value in hard]
    labels["p_calm"] = posterior[:, 0]
    labels["p_normal"] = posterior[:, 1]
    labels["p_volatile"] = posterior[:, 2]
    labels["sticky_age_bars"] = sticky
    labels["context_model_id"] = checkpoint.model_id
    labels["context_run_id"] = run_id
    labels["code_commit"] = commit
    labels["outcomes_accessed"] = False
    output_path = Path(args.labels_out)
    _write_frame(labels, output_path)
    summary = {
        "status": "FORMAL_TARGET_FREE_LABELS",
        "model_id": checkpoint.model_id,
        "run_id": run_id,
        "n_labels": int(len(labels)),
        "features_file_sha256": run_material["features_file_sha256"],
        "labels_file_sha256": _file_sha256(output_path),
        "code_commit": commit,
        "worktree_clean": True,
        "inference": "forward_filter_only",
        "outcomes_accessed": False,
    }
    output_path.with_suffix(output_path.suffix + ".manifest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    sub = out.add_subparsers(dest="command", required=True)
    train_parser = sub.add_parser("train")
    train_parser.add_argument("--features", required=True)
    train_parser.add_argument("--train-cutoff", required=True)
    train_parser.add_argument("--checkpoint-out", required=True)
    train_parser.set_defaults(func=train)
    label_parser = sub.add_parser("label")
    label_parser.add_argument("--features", required=True)
    label_parser.add_argument("--checkpoint", required=True)
    label_parser.add_argument("--labels-out", required=True)
    label_parser.set_defaults(func=label)
    return out


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
