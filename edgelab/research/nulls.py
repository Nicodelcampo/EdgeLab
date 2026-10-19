"""Generadores nulos explícitos para decisiones G2.

No existe un MCPT universal. Cada campaña declara qué relación rompe y qué
estructura preserva. Este módulo define la interfaz y el primer generador
concreto para EXPLORE: anclas placebo dentro de sesión y estrato, preservando el
conteo real y recomputando expectativa neta por trade.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Mapping, Sequence

from edgelab.stats.cluster_estimand import (
    SessionAggregate,
    trade_weighted_expectancy,
)


class NullGeneratorError(ValueError):
    """El nulo no está suficientemente definido para generar evidencia."""


def _text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise NullGeneratorError("%s debe ser texto no vacio" % name)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class NullManifest:
    null_id: str
    generator_version: str
    null_hypothesis: str
    exchangeability_assumption: str
    seed: int
    n_replicates: int
    test_statistic: str = "trade_weighted_expectancy"
    cluster_unit: str = "session"

    def __post_init__(self):
        for name in ("null_id", "generator_version", "null_hypothesis",
                     "exchangeability_assumption", "test_statistic",
                     "cluster_unit"):
            _text(name, getattr(self, name))
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise NullGeneratorError("seed debe ser entero")
        if (not isinstance(self.n_replicates, int)
                or isinstance(self.n_replicates, bool)
                or self.n_replicates < 1):
            raise NullGeneratorError("n_replicates debe ser entero >= 1")
        if self.test_statistic != "trade_weighted_expectancy":
            raise NullGeneratorError("test_statistic no autorizado: %s" %
                                     self.test_statistic)
        if self.cluster_unit != "session":
            raise NullGeneratorError("cluster_unit debe ser session")


@dataclass(frozen=True, order=True)
class CellKey:
    session_id: str
    stratum_id: str

    def __post_init__(self):
        _text("session_id", self.session_id)
        _text("stratum_id", self.stratum_id)


@dataclass(frozen=True)
class CellDraw:
    key: CellKey
    values: tuple[float, ...]


@dataclass(frozen=True)
class NullReplicate:
    replicate_index: int
    theta_trade: float
    cells: tuple[CellDraw, ...]
    clusters: tuple[SessionAggregate, ...]
    generator_digest: str


class NullGenerator(ABC):
    """Contrato mínimo. Un generador concreto debe declarar y persistir su nulo."""

    @property
    @abstractmethod
    def manifest(self) -> NullManifest:
        raise NotImplementedError

    @property
    @abstractmethod
    def generator_digest(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, replicate_index: int) -> NullReplicate:
        raise NotImplementedError

    def run(self) -> tuple[NullReplicate, ...]:
        return tuple(self.generate(i) for i in range(self.manifest.n_replicates))


def _cell_key(value) -> CellKey:
    if isinstance(value, CellKey):
        return value
    if isinstance(value, tuple) and len(value) == 2:
        return CellKey(value[0], value[1])
    raise NullGeneratorError("clave de celda debe ser (session_id, stratum_id)")


def _uniform_index(size: int, *, domain: str) -> int:
    """Índice determinista con rejection sampling; evita sesgo de módulo."""
    space = 1 << 256
    limit = space - (space % size)
    nonce = 0
    while True:
        raw = hashlib.sha256((domain + "|" + str(nonce)).encode("utf-8")).digest()
        value = int.from_bytes(raw, "big")
        if value < limit:
            return value % size
        nonce += 1


class PlaceboResampleWithinSession(NullGenerator):
    """Nulo de EXPLORE: samplea anclas placebo dentro de sesión y estrato.

    ``real_counts`` fija cuántas señales reales hubo en cada celda.
    ``candidate_pools`` contiene outcomes netos completos de anclas elegibles.
    Se muestrea con reemplazo; por eso no se denomina permutación.
    """

    def __init__(
        self,
        manifest: NullManifest,
        *,
        session_ids: Sequence[str],
        real_counts: Mapping[tuple[str, str] | CellKey, int],
        candidate_pools: Mapping[tuple[str, str] | CellKey, Sequence[float]],
    ):
        if not isinstance(manifest, NullManifest):
            raise NullGeneratorError("manifest debe ser NullManifest")
        if isinstance(session_ids, (str, bytes)) or not session_ids:
            raise NullGeneratorError("session_ids debe ser una secuencia no vacia")
        if len(set(session_ids)) != len(session_ids):
            raise NullGeneratorError("session_ids contiene duplicados")
        if any(not isinstance(s, str) or not s for s in session_ids):
            raise NullGeneratorError("session_id invalido")

        counts = {}
        for raw_key, value in real_counts.items():
            key = _cell_key(raw_key)
            if key in counts:
                raise NullGeneratorError("celda duplicada al normalizar counts: %s" % (key,))
            counts[key] = value
        pools = {}
        for raw_key, value in candidate_pools.items():
            key = _cell_key(raw_key)
            if key in pools:
                raise NullGeneratorError("celda duplicada al normalizar pools: %s" % (key,))
            pools[key] = tuple(value)
        if set(counts) != set(pools):
            missing = sorted(set(counts) - set(pools))
            extra = sorted(set(pools) - set(counts))
            raise NullGeneratorError("celdas counts/pools no coinciden: missing=%s extra=%s"
                                     % (missing, extra))
        calendar = set(session_ids)
        for key, count in counts.items():
            if key.session_id not in calendar:
                raise NullGeneratorError("celda fuera del calendario: %s" %
                                         (key.session_id,))
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise NullGeneratorError("conteo invalido para %s" % (key,))
            pool = pools[key]
            if any(not isinstance(x, (int, float)) or isinstance(x, bool)
                   or not isfinite(x) for x in pool):
                raise NullGeneratorError("pool no numerico finito para %s" % (key,))
            if count > 0 and not pool:
                raise NullGeneratorError("pool vacio con conteo positivo para %s" % (key,))
        if sum(counts.values()) == 0:
            raise NullGeneratorError("el nulo no tiene señales reales que preservar")

        self._manifest = manifest
        self._session_ids = tuple(session_ids)
        self._counts = counts
        self._pools = pools
        payload = dict(
            manifest=asdict(manifest),
            session_ids=self._session_ids,
            cells=[dict(session_id=k.session_id, stratum_id=k.stratum_id,
                        real_count=counts[k], candidate_pool=list(pools[k]))
                   for k in sorted(counts)],
        )
        self._generator_digest = hashlib.sha256(
            _canonical(payload).encode("utf-8")).hexdigest()

    @property
    def manifest(self) -> NullManifest:
        return self._manifest

    @property
    def generator_digest(self) -> str:
        return self._generator_digest

    def generate(self, replicate_index: int) -> NullReplicate:
        if (not isinstance(replicate_index, int) or isinstance(replicate_index, bool)
                or not 0 <= replicate_index < self.manifest.n_replicates):
            raise NullGeneratorError("replicate_index fuera de rango")

        cells = []
        totals = {session_id: [0.0, 0] for session_id in self._session_ids}
        for key in sorted(self._counts):
            count = self._counts[key]
            pool = self._pools[key]
            values = []
            for draw_index in range(count):
                domain = _canonical(dict(
                    null_id=self.manifest.null_id,
                    generator_version=self.manifest.generator_version,
                    seed=self.manifest.seed,
                    replicate_index=replicate_index,
                    session_id=key.session_id,
                    stratum_id=key.stratum_id,
                    draw_index=draw_index,
                ))
                values.append(float(pool[_uniform_index(len(pool), domain=domain)]))
            cells.append(CellDraw(key, tuple(values)))
            totals[key.session_id][0] += sum(values)
            totals[key.session_id][1] += len(values)

        clusters = tuple(
            SessionAggregate(session_id, totals[session_id][0], totals[session_id][1])
            for session_id in self._session_ids
        )
        return NullReplicate(
            replicate_index=replicate_index,
            theta_trade=trade_weighted_expectancy(clusters),
            cells=tuple(cells),
            clusters=clusters,
            generator_digest=self.generator_digest,
        )
