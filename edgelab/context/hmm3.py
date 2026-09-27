"""Deterministic Gaussian HMM3 with causal forward-only inference.

This module is target-free. Training is separated by complete session sequences;
labels use p(S_t | X_0:t) and never the forward-backward smoothed posterior.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Sequence

import numpy as np

STATE_NAMES = ("calm", "normal", "volatile")
MODEL_FAMILY = "gate_gc_l2_hmm3_toxic_forward_v1"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _logsumexp(values: np.ndarray, axis: int | None = None) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    maximum = np.max(values, axis=axis, keepdims=True)
    result = maximum + np.log(np.sum(np.exp(values - maximum), axis=axis, keepdims=True))
    return np.squeeze(result, axis=axis) if axis is not None else result


def _row_normalize(values: np.ndarray) -> np.ndarray:
    totals = values.sum(axis=1, keepdims=True)
    if np.any(totals <= 0):
        raise ValueError("probability row has no mass")
    return values / totals


def _sequence_slices(sequence_ids: Sequence[object]) -> list[slice]:
    ids = np.asarray([str(value) for value in sequence_ids], dtype=object)
    if len(ids) == 0:
        return []
    starts = np.r_[0, np.flatnonzero(ids[1:] != ids[:-1]) + 1]
    stops = np.r_[starts[1:], len(ids)]
    seen: set[str] = set()
    slices: list[slice] = []
    for low, high in zip(starts, stops):
        key = str(ids[low])
        if key in seen:
            raise ValueError(f"non-contiguous sequence_id: {key}")
        seen.add(key)
        slices.append(slice(int(low), int(high)))
    return slices


@dataclass(frozen=True)
class HMM3Config:
    feature_names: tuple[str, ...] = (
        "rv_ticks_15m",
        "event_rate_per_second",
        "spread_ticks_close",
        "abs_ofi_normalized",
        "efficiency_ratio_10m",
        "log_depth_top5",
    )
    rv_feature: str = "rv_ticks_15m"
    max_iter: int = 80
    tolerance: float = 1e-6
    min_variance: float = 1e-4
    pseudocount: float = 1e-3
    seed: int = 20260825

    def __post_init__(self) -> None:
        if self.rv_feature not in self.feature_names:
            raise ValueError("rv_feature absent from feature_names")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("duplicate feature_names")
        if self.max_iter < 1 or self.tolerance <= 0 or self.min_variance <= 0:
            raise ValueError("invalid HMM configuration")

    def payload(self) -> dict[str, object]:
        value = asdict(self)
        value["feature_names"] = list(self.feature_names)
        value["model_family"] = MODEL_FAMILY
        value["state_names"] = list(STATE_NAMES)
        value["inference"] = "forward_filter_only"
        value["normalization"] = "train_only_mean_std"
        return value


def _validate_matrix(matrix: np.ndarray, features: int, minimum_rows: int = 30) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != features:
        raise ValueError(f"X must have shape (n,{features}); got {matrix.shape}")
    if len(matrix) < minimum_rows:
        raise ValueError(f"at least {minimum_rows} finite rows are required")
    if not np.isfinite(matrix).all():
        raise ValueError("X contains NaN/inf")
    return matrix


def _log_emission(matrix: np.ndarray, means: np.ndarray,
                  variances: np.ndarray) -> np.ndarray:
    delta = matrix[:, None, :] - means[None, :, :]
    return -0.5 * np.sum(
        np.log(2.0 * np.pi * variances)[None, :, :]
        + delta * delta / variances[None, :, :], axis=2)


def _forward_backward(log_emission: np.ndarray, start: np.ndarray,
                      transition: np.ndarray):
    rows, states = log_emission.shape
    log_transition = np.log(transition)
    alpha = np.empty((rows, states), dtype=np.float64)
    beta = np.zeros((rows, states), dtype=np.float64)
    alpha[0] = np.log(start) + log_emission[0]
    for row in range(1, rows):
        alpha[row] = log_emission[row] + _logsumexp(
            alpha[row - 1][:, None] + log_transition, axis=0)
    likelihood = float(_logsumexp(alpha[-1], axis=0))
    for row in range(rows - 2, -1, -1):
        beta[row] = _logsumexp(
            log_transition + log_emission[row + 1][None, :]
            + beta[row + 1][None, :], axis=1)
    gamma = np.exp(alpha + beta - likelihood)
    xi = np.zeros((states, states), dtype=np.float64)
    for row in range(rows - 1):
        xi += np.exp(alpha[row][:, None] + log_transition
                     + log_emission[row + 1][None, :] + beta[row + 1][None, :]
                     - likelihood)
    return likelihood, gamma, xi


def _initial_parameters(matrix: np.ndarray, rv_index: int,
                        sequences: Sequence[slice], config: HMM3Config):
    q1, q2 = np.quantile(matrix[:, rv_index], [1.0 / 3.0, 2.0 / 3.0])
    labels = np.where(matrix[:, rv_index] <= q1, 0,
                      np.where(matrix[:, rv_index] <= q2, 1, 2))
    means = np.vstack([matrix[labels == state].mean(axis=0) for state in range(3)])
    variances = np.vstack([
        matrix[labels == state].var(axis=0) + config.min_variance
        for state in range(3)
    ])
    start = np.full(3, config.pseudocount, dtype=np.float64)
    transition = np.full((3, 3), config.pseudocount, dtype=np.float64)
    for sequence in sequences:
        y = labels[sequence]
        start[y[0]] += 1.0
        for previous, current in zip(y[:-1], y[1:]):
            transition[previous, current] += 1.0
    return start / start.sum(), _row_normalize(transition), means, variances


def training_matrix_sha256(matrix: np.ndarray, sequence_ids: Sequence[object],
                           feature_names: Sequence[str]) -> str:
    matrix = np.ascontiguousarray(np.asarray(matrix, dtype="<f8"))
    hasher = sha256()
    hasher.update(canonical_bytes({"feature_names": list(feature_names),
                                   "shape": list(matrix.shape)}))
    hasher.update(matrix.tobytes(order="C"))
    for value in sequence_ids:
        encoded = str(value).encode("utf-8")
        hasher.update(len(encoded).to_bytes(4, "little"))
        hasher.update(encoded)
    return hasher.hexdigest()


def fit_hmm3(matrix: np.ndarray, sequence_ids: Sequence[object], *,
             code_identity: str, config: HMM3Config | None = None) -> dict[str, object]:
    config = config or HMM3Config()
    if not code_identity or code_identity in {"UNKNOWN", "local"}:
        raise ValueError("real code_identity is required")
    matrix = _validate_matrix(matrix, len(config.feature_names))
    if len(matrix) != len(sequence_ids):
        raise ValueError("X and sequence_ids length differ")
    sequences = _sequence_slices(sequence_ids)
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale = np.where(scale > 1e-12, scale, 1.0)
    standardized = (matrix - mean) / scale
    rv_index = config.feature_names.index(config.rv_feature)
    start, transition, means, variances = _initial_parameters(
        standardized, rv_index, sequences, config)
    previous = -np.inf
    final_likelihood = -np.inf
    for iteration in range(1, config.max_iter + 1):
        emission = _log_emission(standardized, means, variances)
        start_sum = np.full(3, config.pseudocount, dtype=np.float64)
        transition_sum = np.full((3, 3), config.pseudocount, dtype=np.float64)
        gamma_sum = np.zeros(3, dtype=np.float64)
        gamma_x = np.zeros_like(means)
        gamma_x2 = np.zeros_like(means)
        likelihood = 0.0
        for sequence in sequences:
            ll, gamma, xi = _forward_backward(emission[sequence], start, transition)
            values = standardized[sequence]
            likelihood += ll
            start_sum += gamma[0]
            transition_sum += xi
            gamma_sum += gamma.sum(axis=0)
            gamma_x += gamma.T @ values
            gamma_x2 += gamma.T @ (values * values)
        start = start_sum / start_sum.sum()
        transition = _row_normalize(transition_sum)
        means = gamma_x / gamma_sum[:, None]
        variances = np.maximum(gamma_x2 / gamma_sum[:, None] - means * means,
                               config.min_variance)
        final_likelihood = float(likelihood)
        if np.isfinite(previous) and likelihood + 1e-7 < previous:
            raise ArithmeticError("EM reduced log-likelihood")
        if np.isfinite(previous) and abs(likelihood - previous) <= (
                config.tolerance * (1.0 + abs(previous))):
            break
        previous = likelihood

    order = np.argsort(means[:, rv_index])
    start = start[order]
    transition = transition[np.ix_(order, order)]
    means = means[order]
    variances = variances[order]
    unsigned = {
        "schema": "edgelab.context.hmm3_checkpoint/1.0.0",
        "model_family": MODEL_FAMILY,
        "config": config.payload(),
        "config_sha256": digest(config.payload()),
        "feature_names": list(config.feature_names),
        "state_names": list(STATE_NAMES),
        "normalizer_mean": mean.tolist(),
        "normalizer_scale": scale.tolist(),
        "start_probability": start.tolist(),
        "transition": transition.tolist(),
        "means": means.tolist(),
        "variances": variances.tolist(),
        "training_matrix_sha256": training_matrix_sha256(
            matrix, sequence_ids, config.feature_names),
        "training_rows": int(len(matrix)),
        "training_sequences": int(len(sequences)),
        "code_identity": code_identity,
        "iterations": int(iteration),
        "final_log_likelihood": final_likelihood,
    }
    checkpoint_hash = digest(unsigned)
    return {**unsigned, "checkpoint_sha256": checkpoint_hash,
            "model_id": f"{MODEL_FAMILY}:{checkpoint_hash[:16]}"}


def validate_checkpoint(checkpoint: dict[str, object]) -> None:
    model_id = str(checkpoint.get("model_id", ""))
    checkpoint_hash = str(checkpoint.get("checkpoint_sha256", ""))
    unsigned = {key: value for key, value in checkpoint.items()
                if key not in {"model_id", "checkpoint_sha256"}}
    if digest(unsigned) != checkpoint_hash:
        raise ValueError("checkpoint_sha256 mismatch")
    if model_id != f"{MODEL_FAMILY}:{checkpoint_hash[:16]}":
        raise ValueError("model_id does not identify checkpoint bytes")
    if tuple(checkpoint["state_names"]) != STATE_NAMES:
        raise ValueError("incompatible state_names")


def forward_filter(matrix: np.ndarray, sequence_ids: Sequence[object],
                   checkpoint: dict[str, object]) -> np.ndarray:
    validate_checkpoint(checkpoint)
    features = tuple(checkpoint["feature_names"])
    matrix = _validate_matrix(matrix, len(features))
    if len(matrix) != len(sequence_ids):
        raise ValueError("X and sequence_ids length differ")
    sequences = _sequence_slices(sequence_ids)
    mean = np.asarray(checkpoint["normalizer_mean"], dtype=np.float64)
    scale = np.asarray(checkpoint["normalizer_scale"], dtype=np.float64)
    standardized = (matrix - mean) / scale
    means = np.asarray(checkpoint["means"], dtype=np.float64)
    variances = np.asarray(checkpoint["variances"], dtype=np.float64)
    emission = _log_emission(standardized, means, variances)
    log_start = np.log(np.asarray(checkpoint["start_probability"], dtype=np.float64))
    log_transition = np.log(np.asarray(checkpoint["transition"], dtype=np.float64))
    posterior = np.empty((len(matrix), 3), dtype=np.float64)
    for sequence in sequences:
        low, high = sequence.start, sequence.stop
        alpha = log_start + emission[low]
        alpha -= _logsumexp(alpha, axis=0)
        posterior[low] = np.exp(alpha)
        for row in range(low + 1, high):
            alpha = emission[row] + _logsumexp(
                alpha[:, None] + log_transition, axis=0)
            alpha -= _logsumexp(alpha, axis=0)
            posterior[row] = np.exp(alpha)
    if not np.allclose(posterior.sum(axis=1), 1.0, rtol=0, atol=1e-10):
        raise AssertionError("posterior rows do not sum to one")
    return posterior
