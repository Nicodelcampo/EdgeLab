"""HMM Gaussiano diagonal de tres estados con inferencia causal forward-only.

No usa outcomes. El entrenamiento normaliza sólo con el train y cada checkpoint
incluye pesos, normalizador, hash de matriz, config, commit y un model_id derivado
del contenido. No existe default formal sin checkpoint.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Sequence

import numpy as np

STATE_NAMES = ("calm", "normal", "volatile")
MODEL_FAMILY = "gate_gc_l1_hmm3_forward_v0"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _logsumexp(a: np.ndarray, axis=None) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    m = np.max(a, axis=axis, keepdims=True)
    out = m + np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True))
    return np.squeeze(out, axis=axis) if axis is not None else out


def _row_normalize(a: np.ndarray) -> np.ndarray:
    total = a.sum(axis=1, keepdims=True)
    if np.any(total <= 0):
        raise ValueError("fila probabilística sin masa")
    return a / total


def _validate_matrix(x: np.ndarray, n_features: int) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != n_features:
        raise ValueError(f"X debe tener shape (n,{n_features}); tiene {x.shape}")
    if len(x) < 30:
        raise ValueError("se requieren al menos 30 filas target-free")
    if not np.isfinite(x).all():
        raise ValueError("X contiene NaN/inf; resolver burn-in antes de entrenar")
    return x


def _sequence_slices(sequence_ids: Sequence[object]) -> list[slice]:
    ids = np.asarray([str(v) for v in sequence_ids], dtype=object)
    if len(ids) == 0:
        return []
    starts = np.r_[0, np.flatnonzero(ids[1:] != ids[:-1]) + 1]
    stops = np.r_[starts[1:], len(ids)]
    seen: set[str] = set()
    out: list[slice] = []
    for lo, hi in zip(starts, stops):
        key = str(ids[lo])
        if key in seen:
            raise ValueError(f"sequence_id no contiguo: {key}")
        seen.add(key)
        out.append(slice(int(lo), int(hi)))
    return out


@dataclass(frozen=True)
class HMM3Config:
    feature_names: tuple[str, ...] = (
        "rv_ticks_15m",
        "tick_rate_per_second",
        "spread_ticks_mean",
        "tape_imbalance",
        "efficiency_ratio_10m",
    )
    rv_feature: str = "rv_ticks_15m"
    max_iter: int = 100
    tol: float = 1e-6
    min_variance: float = 1e-4
    pseudocount: float = 1e-3
    seed: int = 20260824
    n_states: int = 3
    inference: str = "forward_filter_only"
    normalization: str = "train_only_mean_std"

    def __post_init__(self) -> None:
        if self.n_states != 3:
            raise ValueError("v0 congela exactamente tres estados")
        if self.rv_feature not in self.feature_names:
            raise ValueError("rv_feature falta de feature_names")
        if self.max_iter < 1 or self.tol <= 0 or self.min_variance <= 0:
            raise ValueError("hiperparámetros inválidos")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("feature_names duplicados")

    def payload(self) -> dict[str, object]:
        out = asdict(self)
        out["feature_names"] = list(self.feature_names)
        out["model_family"] = MODEL_FAMILY
        out["state_names"] = list(STATE_NAMES)
        return out

    @property
    def config_sha256(self) -> str:
        return _digest(self.payload())


@dataclass(frozen=True)
class HMM3Checkpoint:
    schema: str
    model_family: str
    model_id: str
    checkpoint_sha256: str
    config: dict[str, object]
    config_sha256: str
    feature_names: tuple[str, ...]
    state_names: tuple[str, ...]
    normalizer_mean: tuple[float, ...]
    normalizer_scale: tuple[float, ...]
    start_probability: tuple[float, ...]
    transition: tuple[tuple[float, ...], ...]
    means: tuple[tuple[float, ...], ...]
    variances: tuple[tuple[float, ...], ...]
    training_matrix_sha256: str
    training_rows: int
    training_sequences: int
    code_commit: str
    iterations: int
    final_log_likelihood: float

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "model_family": self.model_family,
            "config": self.config,
            "config_sha256": self.config_sha256,
            "feature_names": list(self.feature_names),
            "state_names": list(self.state_names),
            "normalizer_mean": list(self.normalizer_mean),
            "normalizer_scale": list(self.normalizer_scale),
            "start_probability": list(self.start_probability),
            "transition": [list(row) for row in self.transition],
            "means": [list(row) for row in self.means],
            "variances": [list(row) for row in self.variances],
            "training_matrix_sha256": self.training_matrix_sha256,
            "training_rows": self.training_rows,
            "training_sequences": self.training_sequences,
            "code_commit": self.code_commit,
            "iterations": self.iterations,
            "final_log_likelihood": self.final_log_likelihood,
        }

    def validate(self) -> None:
        if self.model_family != MODEL_FAMILY or self.state_names != STATE_NAMES:
            raise ValueError("familia/estados incompatibles")
        if _digest(self.config) != self.config_sha256:
            raise ValueError("config_sha256 no reproduce config")
        digest = _digest(self.unsigned_payload())
        if digest != self.checkpoint_sha256:
            raise ValueError("checkpoint_sha256 no reproduce pesos/normalizador/procedencia")
        if self.model_id != f"{MODEL_FAMILY}:{digest[:16]}":
            raise ValueError("model_id no identifica el checkpoint")
        start = np.asarray(self.start_probability)
        trans = np.asarray(self.transition)
        means = np.asarray(self.means)
        variances = np.asarray(self.variances)
        if start.shape != (3,) or trans.shape != (3, 3):
            raise ValueError("shape probabilística inválida")
        if means.shape != variances.shape or means.shape[0] != 3:
            raise ValueError("shape de emisiones inválida")
        if not np.allclose(start.sum(), 1.0, atol=1e-10):
            raise ValueError("start_probability no suma uno")
        if not np.allclose(trans.sum(axis=1), 1.0, atol=1e-10):
            raise ValueError("transition no es estocástica")
        if np.any(variances <= 0):
            raise ValueError("varianzas no positivas")

    def to_dict(self) -> dict[str, object]:
        out = self.unsigned_payload()
        out["model_id"] = self.model_id
        out["checkpoint_sha256"] = self.checkpoint_sha256
        return out

    def save(self, path: str | Path) -> None:
        self.validate()
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "HMM3Checkpoint":
        out = cls(
            schema=str(raw["schema"]), model_family=str(raw["model_family"]),
            model_id=str(raw["model_id"]), checkpoint_sha256=str(raw["checkpoint_sha256"]),
            config=dict(raw["config"]), config_sha256=str(raw["config_sha256"]),
            feature_names=tuple(raw["feature_names"]), state_names=tuple(raw["state_names"]),
            normalizer_mean=tuple(float(v) for v in raw["normalizer_mean"]),
            normalizer_scale=tuple(float(v) for v in raw["normalizer_scale"]),
            start_probability=tuple(float(v) for v in raw["start_probability"]),
            transition=tuple(tuple(float(v) for v in row) for row in raw["transition"]),
            means=tuple(tuple(float(v) for v in row) for row in raw["means"]),
            variances=tuple(tuple(float(v) for v in row) for row in raw["variances"]),
            training_matrix_sha256=str(raw["training_matrix_sha256"]),
            training_rows=int(raw["training_rows"]), training_sequences=int(raw["training_sequences"]),
            code_commit=str(raw["code_commit"]), iterations=int(raw["iterations"]),
            final_log_likelihood=float(raw["final_log_likelihood"]),
        )
        out.validate()
        return out

    @classmethod
    def load(cls, path: str | Path) -> "HMM3Checkpoint":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def training_matrix_sha256(x: np.ndarray, sequence_ids: Sequence[object],
                           feature_names: Sequence[str]) -> str:
    x = np.ascontiguousarray(np.asarray(x, dtype="<f8"))
    if len(x) != len(sequence_ids):
        raise ValueError("X y sequence_ids difieren")
    h = sha256()
    h.update(_canonical_bytes({"feature_names": list(feature_names), "shape": list(x.shape)}))
    h.update(x.tobytes(order="C"))
    for value in sequence_ids:
        encoded = str(value).encode("utf-8")
        h.update(len(encoded).to_bytes(4, "little"))
        h.update(encoded)
    return h.hexdigest()


def _log_emission(x: np.ndarray, means: np.ndarray, variances: np.ndarray) -> np.ndarray:
    delta = x[:, None, :] - means[None, :, :]
    return -0.5 * np.sum(
        np.log(2.0 * np.pi * variances)[None, :, :] + delta * delta / variances[None, :, :],
        axis=2,
    )


def _forward_backward(log_emit: np.ndarray, start: np.ndarray, trans: np.ndarray):
    n, k = log_emit.shape
    log_trans = np.log(trans)
    alpha = np.empty((n, k))
    beta = np.zeros((n, k))
    alpha[0] = np.log(start) + log_emit[0]
    for t in range(1, n):
        alpha[t] = log_emit[t] + _logsumexp(alpha[t - 1][:, None] + log_trans, axis=0)
    log_likelihood = float(_logsumexp(alpha[-1], axis=0))
    for t in range(n - 2, -1, -1):
        beta[t] = _logsumexp(
            log_trans + log_emit[t + 1][None, :] + beta[t + 1][None, :], axis=1
        )
    gamma = np.exp(alpha + beta - log_likelihood)
    xi = np.zeros((k, k))
    for t in range(n - 1):
        xi += np.exp(
            alpha[t][:, None] + log_trans + log_emit[t + 1][None, :]
            + beta[t + 1][None, :] - log_likelihood
        )
    return log_likelihood, gamma, xi


def _initial_parameters(z: np.ndarray, rv_index: int, slices: Sequence[slice],
                        config: HMM3Config):
    q1, q2 = np.quantile(z[:, rv_index], [1 / 3, 2 / 3])
    labels = np.where(z[:, rv_index] <= q1, 0, np.where(z[:, rv_index] <= q2, 1, 2))
    means = np.vstack([z[labels == k].mean(axis=0) for k in range(3)])
    variances = np.vstack([
        z[labels == k].var(axis=0) + config.min_variance for k in range(3)
    ])
    start = np.full(3, config.pseudocount)
    counts = np.full((3, 3), config.pseudocount)
    for sl in slices:
        y = labels[sl]
        start[y[0]] += 1
        for a, b in zip(y[:-1], y[1:]):
            counts[a, b] += 1
    return start / start.sum(), _row_normalize(counts), means, variances


def fit_hmm3(x: np.ndarray, sequence_ids: Sequence[object], *,
             config: HMM3Config | None = None, code_commit: str) -> HMM3Checkpoint:
    config = config or HMM3Config()
    if not code_commit or code_commit in {"local", "UNKNOWN"}:
        raise ValueError("code_commit real es obligatorio para checkpoint formal")
    x = _validate_matrix(x, len(config.feature_names))
    if len(x) != len(sequence_ids):
        raise ValueError("X y sequence_ids difieren")
    slices = _sequence_slices(sequence_ids)
    mean = x.mean(axis=0)
    scale = np.where(x.std(axis=0) > 1e-12, x.std(axis=0), 1.0)
    z = (x - mean) / scale
    rv_index = config.feature_names.index(config.rv_feature)
    start, trans, means, variances = _initial_parameters(z, rv_index, slices, config)
    previous = -np.inf
    final_ll = -np.inf
    for iteration in range(1, config.max_iter + 1):
        log_emit = _log_emission(z, means, variances)
        start_sum = np.full(3, config.pseudocount)
        xi_sum = np.full((3, 3), config.pseudocount)
        gamma_sum = np.zeros(3)
        gamma_x = np.zeros_like(means)
        gamma_x2 = np.zeros_like(means)
        total_ll = 0.0
        for sl in slices:
            ll, gamma, xi = _forward_backward(log_emit[sl], start, trans)
            zz = z[sl]
            total_ll += ll
            start_sum += gamma[0]
            xi_sum += xi
            gamma_sum += gamma.sum(axis=0)
            gamma_x += gamma.T @ zz
            gamma_x2 += gamma.T @ (zz * zz)
        start = start_sum / start_sum.sum()
        trans = _row_normalize(xi_sum)
        means = gamma_x / gamma_sum[:, None]
        variances = np.maximum(
            gamma_x2 / gamma_sum[:, None] - means * means, config.min_variance
        )
        final_ll = float(total_ll)
        if np.isfinite(previous) and total_ll + 1e-7 < previous:
            raise ArithmeticError("EM redujo log-likelihood")
        if np.isfinite(previous) and abs(total_ll - previous) <= config.tol * (1 + abs(previous)):
            break
        previous = total_ll

    # Identifica los estados por RV ascendente: calm, normal, volatile.
    order = np.argsort(means[:, rv_index])
    start = start[order]
    trans = trans[np.ix_(order, order)]
    means = means[order]
    variances = variances[order]
    config_payload = config.payload()
    unsigned = {
        "schema": "edgelab.context.hmm3_checkpoint/1.0.0",
        "model_family": MODEL_FAMILY,
        "config": config_payload,
        "config_sha256": _digest(config_payload),
        "feature_names": list(config.feature_names),
        "state_names": list(STATE_NAMES),
        "normalizer_mean": mean.tolist(),
        "normalizer_scale": scale.tolist(),
        "start_probability": start.tolist(),
        "transition": trans.tolist(),
        "means": means.tolist(),
        "variances": variances.tolist(),
        "training_matrix_sha256": training_matrix_sha256(x, sequence_ids, config.feature_names),
        "training_rows": int(len(x)),
        "training_sequences": int(len(slices)),
        "code_commit": code_commit,
        "iterations": int(iteration),
        "final_log_likelihood": final_ll,
    }
    checkpoint_hash = _digest(unsigned)
    return HMM3Checkpoint.from_dict({
        **unsigned,
        "checkpoint_sha256": checkpoint_hash,
        "model_id": f"{MODEL_FAMILY}:{checkpoint_hash[:16]}",
    })


def forward_filter(x: np.ndarray, sequence_ids: Sequence[object],
                   checkpoint: HMM3Checkpoint) -> np.ndarray:
    """Posteriores filtrados p(S_t | X_0:t); nunca usa X futuro."""
    checkpoint.validate()
    x = _validate_matrix(x, len(checkpoint.feature_names))
    if len(x) != len(sequence_ids):
        raise ValueError("X y sequence_ids difieren")
    slices = _sequence_slices(sequence_ids)
    z = (x - np.asarray(checkpoint.normalizer_mean)) / np.asarray(checkpoint.normalizer_scale)
    emissions = _log_emission(z, np.asarray(checkpoint.means), np.asarray(checkpoint.variances))
    log_start = np.log(np.asarray(checkpoint.start_probability))
    log_transition = np.log(np.asarray(checkpoint.transition))
    posterior = np.empty((len(x), 3))
    for sl in slices:
        lo, hi = sl.start, sl.stop
        alpha = log_start + emissions[lo]
        alpha -= _logsumexp(alpha, axis=0)
        posterior[lo] = np.exp(alpha)
        for t in range(lo + 1, hi):
            alpha = emissions[t] + _logsumexp(alpha[:, None] + log_transition, axis=0)
            alpha -= _logsumexp(alpha, axis=0)
            posterior[t] = np.exp(alpha)
    if not np.allclose(posterior.sum(axis=1), 1.0, atol=1e-10):
        raise AssertionError("posteriores no suman uno")
    return posterior
