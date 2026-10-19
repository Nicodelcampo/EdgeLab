"""Identidad causal de eventos capturados (EventIdentity v2).

Este módulo separa hechos que antes quedaban mezclados:

- ``source_time_ns``: timestamp informado por NT8/proveedor; puede repetirse.
- ``capture_utc_ns``: reloj UTC de la máquina que captura.
- ``monotonic_ns``: reloj monotónico local, útil para ordenar sin depender de NTP.
- ``callback_seq``: orden local de entrada a callbacks NT8.
- ``capture_seq``: orden local de persistencia en una captura.
- ``source_sequence``: secuencia externa opcional, con alcance explícito.

Ninguna secuencia local demuestra continuidad upstream. En particular,
``callback_seq`` no es una secuencia del exchange y no puede usarse para afirmar
que no hubo pérdidas antes de NT8.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

SCHEMA_VERSION = "event_identity_v2"

AGGRESSORS = ("buy", "sell", "unclassified", "unknown")
AGGRESSOR_PROVENANCE = (
    "native_provider",
    "quote_rule",
    "tick_rule",
    "first_tick_default",
    "not_applicable",
    "unknown",
)
TIMESTAMP_PROVENANCE = (
    "nt8_event_time",
    "nt8_bar_time",
    "provider_time",
    "capture_clock_only",
    "unknown",
)
QUOTE_PROVENANCE = (
    "native_event",
    "nt8_snapshot",
    "historical_series",
    "missing",
    "unknown",
)
SOURCE_SEQUENCE_SCOPES = ("exchange", "provider", "platform", "unknown")


class EventIdentityError(ValueError):
    """El registro no satisface el contrato EventIdentity v2."""


def _canonical_json(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EventIdentityError(f"{name} debe ser texto no vacío")


@dataclass(frozen=True)
class EventIdentityV2:
    """Identidad inmutable de un evento observado por el capturador.

    La unicidad operacional está anclada en ``capture_id + capture_seq``. El
    contenido también entra al digest para que una fila alterada cambie su ID.
    Dos eventos materialmente idénticos conservan identidades distintas si
    entraron como callbacks distintos: deduplicarlos sería pérdida de evidencia.
    """

    capture_id: str
    process_instance_id: str
    instrument: str
    contract: str
    event_kind: str
    callback_seq: int
    capture_seq: int
    capture_utc_ns: int
    monotonic_ns: int
    source_time_ns: int | None = None
    source_sequence: str | None = None
    source_sequence_scope: str | None = None
    timestamp_provenance: str = "unknown"
    quote_provenance: str = "unknown"
    aggressor: str = "unknown"
    aggressor_provenance: str = "unknown"
    price_ticks: int | None = None
    volume: float | None = None
    bid_ticks: int | None = None
    ask_ticks: int | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "capture_id",
            "process_instance_id",
            "instrument",
            "contract",
            "event_kind",
        ):
            _require_text(name, getattr(self, name))
        if self.schema_version != SCHEMA_VERSION:
            raise EventIdentityError(
                f"schema_version debe ser {SCHEMA_VERSION!r}, vino {self.schema_version!r}"
            )
        for name in ("callback_seq", "capture_seq", "capture_utc_ns", "monotonic_ns"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise EventIdentityError(f"{name} debe ser entero >= 0")
        if self.source_time_ns is not None and (
            not isinstance(self.source_time_ns, int)
            or isinstance(self.source_time_ns, bool)
            or self.source_time_ns < 0
        ):
            raise EventIdentityError("source_time_ns debe ser entero >= 0 o None")
        if self.aggressor not in AGGRESSORS:
            raise EventIdentityError(f"aggressor inválido: {self.aggressor!r}")
        if self.aggressor_provenance not in AGGRESSOR_PROVENANCE:
            raise EventIdentityError(
                f"aggressor_provenance inválida: {self.aggressor_provenance!r}"
            )
        if self.timestamp_provenance not in TIMESTAMP_PROVENANCE:
            raise EventIdentityError(
                f"timestamp_provenance inválida: {self.timestamp_provenance!r}"
            )
        if self.quote_provenance not in QUOTE_PROVENANCE:
            raise EventIdentityError(
                f"quote_provenance inválida: {self.quote_provenance!r}"
            )
        if (self.source_sequence is None) != (self.source_sequence_scope is None):
            raise EventIdentityError(
                "source_sequence y source_sequence_scope deben aparecer juntos"
            )
        if (
            self.source_sequence_scope is not None
            and self.source_sequence_scope not in SOURCE_SEQUENCE_SCOPES
        ):
            raise EventIdentityError(
                f"source_sequence_scope inválido: {self.source_sequence_scope!r}"
            )
        if self.volume is not None and self.volume <= 0:
            raise EventIdentityError("volume debe ser > 0 o None")
        if (
            self.bid_ticks is not None
            and self.ask_ticks is not None
            and self.bid_ticks > self.ask_ticks
        ):
            raise EventIdentityError("quote cruzada: bid_ticks > ask_ticks")

    def identity_payload(self) -> dict:
        return asdict(self)

    @property
    def event_id(self) -> str:
        raw = _canonical_json(self.identity_payload()).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_record(self) -> dict:
        return dict(event_id=self.event_id, **self.identity_payload())


@dataclass(frozen=True)
class CaptureAuditReport:
    n_events: int
    capture_id: str | None
    source_timestamp_duplicates: int
    millisecond_aliases: int
    missing_source_time: int
    missing_external_sequence: int
    upstream_loss_observable: bool
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def audit_capture(events, *, require_zero_origin: bool = True) -> CaptureAuditReport:
    """Audita una captura completa sin reinterpretar ni deduplicar eventos.

    ``millisecond_aliases`` cuenta pares adyacentes que tienen tiempos fuente
    distintos en ns pero colapsarían al mismo milisegundo. Es evidencia directa
    de que convertir a ``unix_ms`` pierde identidad temporal.

    ``upstream_loss_observable`` sólo puede ser verdadero si *todos* los eventos
    traen una secuencia declarada de alcance ``exchange`` o ``provider``. Aun así
    el reporte no afirma ausencia de pérdida: sólo que existe un campo externo
    con el cual auditarla.
    """
    rows = list(events)
    if not rows:
        return CaptureAuditReport(0, None, 0, 0, 0, 0, False, ())

    errors: list[str] = []
    capture_ids = {e.capture_id for e in rows}
    if len(capture_ids) != 1:
        errors.append(f"captura mezclada: capture_id={sorted(capture_ids)!r}")

    cap_seq = [e.capture_seq for e in rows]
    cb_seq = [e.callback_seq for e in rows]
    if require_zero_origin and cap_seq[0] != 0:
        errors.append(f"capture_seq no empieza en 0 (empieza en {cap_seq[0]})")
    expected = list(range(cap_seq[0], cap_seq[0] + len(cap_seq)))
    if cap_seq != expected:
        errors.append("capture_seq no es contiguo y estrictamente creciente")
    if any(b <= a for a, b in zip(cb_seq, cb_seq[1:])):
        errors.append("callback_seq no es estrictamente creciente")
    if any(b < a for a, b in zip(
        (e.monotonic_ns for e in rows),
        (e.monotonic_ns for e in rows[1:]),
    )):
        errors.append("monotonic_ns retrocede")
    if any(b < a for a, b in zip(
        (e.capture_utc_ns for e in rows),
        (e.capture_utc_ns for e in rows[1:]),
    )):
        errors.append("capture_utc_ns retrocede")

    source_times = [e.source_time_ns for e in rows if e.source_time_ns is not None]
    source_dups = len(source_times) - len(set(source_times))
    ms_aliases = sum(
        1
        for a, b in zip(source_times, source_times[1:])
        if a != b and a // 1_000_000 == b // 1_000_000
    )
    missing_time = sum(e.source_time_ns is None for e in rows)
    missing_seq = sum(e.source_sequence is None for e in rows)
    upstream_observable = all(
        e.source_sequence is not None
        and e.source_sequence_scope in ("exchange", "provider")
        for e in rows
    )

    return CaptureAuditReport(
        n_events=len(rows),
        capture_id=next(iter(capture_ids)) if len(capture_ids) == 1 else None,
        source_timestamp_duplicates=source_dups,
        millisecond_aliases=ms_aliases,
        missing_source_time=missing_time,
        missing_external_sequence=missing_seq,
        upstream_loss_observable=upstream_observable,
        errors=tuple(errors),
    )
