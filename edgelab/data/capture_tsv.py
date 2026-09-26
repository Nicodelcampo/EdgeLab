"""Parser y auditor reproducible del ledger TSV de CaptureEventProbeV2.

Separa dos preguntas que antes se mezclaron:

- ``transport_ok``: ¿todos los callbacks observados llegaron a disco, en orden?
- ``schema_ok``: ¿la captura declara procedencia suficiente y no usa sentinelas?

Una cuenta simulada no implica ausencia de proveedor. Por eso provider,
account_environment y capture_mode son dimensiones distintas.
"""
from __future__ import annotations

import csv
import io
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA_V2 = "event_capture_raw_v2"
SCHEMA_V21 = "event_capture_raw_v2_1"
SUPPORTED_SCHEMAS = (SCHEMA_V2, SCHEMA_V21)

V2_COLUMNS = (
    "capture_id", "process_instance_id", "callback_seq", "capture_seq",
    "source_time_ticks", "source_time_kind", "source_time_iso",
    "capture_utc_ticks", "capture_utc_iso", "monotonic_ticks",
    "stopwatch_frequency", "nt8_state", "event_kind", "instrument",
    "contract", "price", "volume", "bid", "ask", "aggressor",
    "aggressor_provenance", "timestamp_provenance", "quote_provenance",
    "capture_mode_label",
)
V21_COLUMNS = V2_COLUMNS + (
    "provider_label", "account_environment_label", "source_timezone_label",
)


class CaptureTsvError(ValueError):
    """El archivo no puede interpretarse como un ledger TSV."""


@dataclass(frozen=True)
class CaptureTsv:
    metadata: dict[str, str]
    columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    summary: dict[str, int]


@dataclass(frozen=True)
class CaptureAudit:
    path: str
    schema: str | None
    n_rows: int
    callbacks_seen: int | None
    rows_written: int | None
    dropped_at_queue: int | None
    writer_errors: int | None
    event_kind_counts: dict[str, int]
    source_time_regressions: int
    max_source_time_regression_ns: int
    capture_utc_regressions: int
    sentinel_values: int
    blank_last_quotes: int
    upstream_loss_observable: bool
    transport_errors: tuple[str, ...]
    schema_errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def transport_ok(self) -> bool:
        return not self.transport_errors

    @property
    def schema_ok(self) -> bool:
        return not self.schema_errors

    @property
    def verdict(self) -> str:
        if not self.transport_ok:
            return "TRANSPORT_FAIL"
        if not self.schema_ok or self.warnings:
            return "TRANSPORT_PASS_WITH_SCHEMA_DEBT"
        return "PASS"

    def to_dict(self) -> dict:
        return dict(asdict(self), transport_ok=self.transport_ok,
                    schema_ok=self.schema_ok, verdict=self.verdict)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False,
                          sort_keys=True)


def _parse_summary(text: str) -> dict[str, int]:
    out = {}
    for part in text.split(","):
        if "=" not in part:
            raise CaptureTsvError("summary malformado: %r" % text)
        key, value = part.strip().split("=", 1)
        try:
            out[key] = int(value)
        except ValueError as exc:
            raise CaptureTsvError("summary no entero: %s=%r" % (key, value)) from exc
    return out


def parse_capture_tsv(path) -> CaptureTsv:
    """Parsea comentarios, header, filas y trailer sin reinterpretar valores."""
    metadata: dict[str, str] = {}
    summary = None
    data_lines = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for line_no, line in enumerate(fh, 1):
            clean = line.rstrip("\r\n")
            if clean.startswith("# summary "):
                if summary is not None:
                    raise CaptureTsvError("summary duplicado")
                summary = _parse_summary(clean[len("# summary "):])
            elif clean.startswith("# "):
                body = clean[2:]
                if "=" not in body:
                    raise CaptureTsvError("metadata malformada en linea %d" % line_no)
                key, value = body.split("=", 1)
                if key in metadata:
                    raise CaptureTsvError("metadata duplicada: %s" % key)
                metadata[key] = value
            elif clean:
                data_lines.append(clean)

    if not data_lines:
        raise CaptureTsvError("falta header TSV")
    reader = csv.DictReader(io.StringIO("\n".join(data_lines)), delimiter="\t",
                            strict=True)
    columns = tuple(reader.fieldnames or ())
    rows = []
    for number, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise CaptureTsvError("cantidad de columnas invalida en fila de datos %d" % number)
        rows.append(dict(row))
    if summary is None:
        raise CaptureTsvError("falta trailer summary")
    return CaptureTsv(metadata, columns, tuple(rows), summary)


def _ints(rows, field, errors):
    out = []
    for i, row in enumerate(rows, 1):
        try:
            out.append(int(row[field]))
        except (KeyError, ValueError):
            errors.append("%s no entero en fila %d" % (field, i))
            return []
    return out


def _float_or_none(value, field, row_no, errors):
    if value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        errors.append("%s no numerico en fila %d" % (field, row_no))
        return None
    if not math.isfinite(number):
        errors.append("%s no finito en fila %d" % (field, row_no))
        return None
    return number


def _placeholder(value):
    return not value or value.upper().startswith("DECLARAR") or value.upper() in {
        "UNKNOWN", "UNSPECIFIED", "N/A",
    }


def audit_capture_tsv(path) -> CaptureAudit:
    """Audita estructura, transporte, procedencia y deuda de representación."""
    cap = parse_capture_tsv(path)
    rows = cap.rows
    meta = cap.metadata
    summary = cap.summary
    transport, schema_errors, warnings = [], [], []
    schema = meta.get("schema")

    expected_columns = V21_COLUMNS if schema == SCHEMA_V21 else V2_COLUMNS
    if schema not in SUPPORTED_SCHEMAS:
        schema_errors.append("schema no soportado: %r" % schema)
    if cap.columns != expected_columns:
        schema_errors.append("columnas no coinciden exactamente con %s" %
                             (schema or "schema ausente"))

    n = len(rows)
    callbacks = summary.get("callbacks_seen")
    written = summary.get("rows_written")
    drops = summary.get("dropped_at_queue")
    writer_errors = summary.get("writer_errors")
    for field in ("callbacks_seen", "rows_written", "dropped_at_queue", "writer_errors"):
        if field not in summary:
            transport.append("summary sin %s" % field)
    if written is not None and written != n:
        transport.append("rows_written=%s pero TSV contiene %d filas" % (written, n))
    if callbacks is not None and callbacks != n:
        transport.append("callbacks_seen=%s pero TSV contiene %d filas" % (callbacks, n))
    if drops not in (None, 0):
        transport.append("dropped_at_queue=%s" % drops)
    if writer_errors not in (None, 0):
        transport.append("writer_errors=%s" % writer_errors)
    if n == 0:
        transport.append("captura vacia")

    cb = _ints(rows, "callback_seq", transport)
    persisted = _ints(rows, "capture_seq", transport)
    monotonic = _ints(rows, "monotonic_ticks", transport)
    source_ticks = _ints(rows, "source_time_ticks", transport)
    capture_ticks = _ints(rows, "capture_utc_ticks", transport)
    frequencies = _ints(rows, "stopwatch_frequency", transport)
    expected = list(range(n))
    if cb and cb != expected:
        transport.append("callback_seq no es exactamente 0..n-1")
    if persisted and persisted != expected:
        transport.append("capture_seq no es exactamente 0..n-1")
    if cb and persisted and cb != persisted:
        transport.append("callback_seq y capture_seq divergen")
    if monotonic and any(b <= a for a, b in zip(monotonic, monotonic[1:])):
        transport.append("monotonic_ticks no es estrictamente creciente")
    if frequencies and len(set(frequencies)) != 1:
        transport.append("stopwatch_frequency cambia dentro de la captura")
    if frequencies and meta.get("stopwatch_frequency"):
        try:
            if frequencies[0] != int(meta["stopwatch_frequency"]):
                transport.append("stopwatch_frequency metadata/fila no coincide")
        except ValueError:
            transport.append("stopwatch_frequency de metadata no es entero")

    capture_ids = {row.get("capture_id") for row in rows}
    process_ids = {row.get("process_instance_id") for row in rows}
    if len(capture_ids) != 1 or (capture_ids and next(iter(capture_ids)) != meta.get("capture_id")):
        transport.append("capture_id mezclado o distinto de metadata")
    if len(process_ids) != 1 or (process_ids and next(iter(process_ids)) != meta.get("process_instance_id")):
        transport.append("process_instance_id mezclado o distinto de metadata")

    source_regressions, max_source_regression_ns = 0, 0
    for a, b in zip(source_ticks, source_ticks[1:]):
        if b < a:
            source_regressions += 1
            max_source_regression_ns = max(max_source_regression_ns, (a - b) * 100)
    capture_regressions = sum(b < a for a, b in zip(capture_ticks, capture_ticks[1:]))
    if source_regressions:
        warnings.append("source_time retrocede %d veces (max=%d ns)" %
                        (source_regressions, max_source_regression_ns))
    if capture_regressions:
        warnings.append("capture_utc retrocede %d veces; monotonic es la autoridad local" %
                        capture_regressions)

    sentinel_values = 0
    blank_last_quotes = 0
    for i, row in enumerate(rows, 1):
        numeric_errors = []
        values = {field: _float_or_none(row.get(field, ""), field, i, numeric_errors)
                  for field in ("price", "volume", "bid", "ask")}
        schema_errors.extend(numeric_errors)
        sentinel_values += sum(v is not None and v <= -1e300 for v in values.values())
        if row.get("event_kind", "").lower() == "last" and (
                values["bid"] is None or values["ask"] is None):
            blank_last_quotes += 1
    if sentinel_values:
        schema_errors.append("%d valores centinela extremos; usar campo vacio/null" %
                             sentinel_values)
    if blank_last_quotes:
        warnings.append("%d eventos Last sin bid/ask completos" % blank_last_quotes)

    if schema == SCHEMA_V2:
        warnings.append("schema v2 legado: provider/account/timezone no separados")
    if schema == SCHEMA_V21:
        for field in ("provider_label", "account_environment_label",
                      "source_timezone_label"):
            values = {row.get(field, "") for row in rows}
            if len(values) != 1 or any(_placeholder(v) for v in values):
                schema_errors.append("%s ausente, placeholder o inconsistente" % field)
        if any(row.get("source_time_kind") == "Unspecified" for row in rows) and any(
                _placeholder(row.get("source_timezone_label", "")) for row in rows):
            schema_errors.append("source_time Unspecified sin timezone declarada")

    mode_values = {row.get("capture_mode_label", "") for row in rows}
    if len(mode_values) != 1 or any(_placeholder(v) for v in mode_values):
        schema_errors.append("capture_mode_label ausente, placeholder o inconsistente")

    source_sequence = meta.get("source_sequence", "")
    upstream_observable = bool(source_sequence and
                               source_sequence != "NOT_EXPOSED_BY_THIS_NT8_CALLBACK")
    if not upstream_observable:
        warnings.append("perdida upstream no observable: callback sin source_sequence")

    return CaptureAudit(
        path=str(Path(path)), schema=schema, n_rows=n, callbacks_seen=callbacks,
        rows_written=written, dropped_at_queue=drops, writer_errors=writer_errors,
        event_kind_counts=dict(Counter(r.get("event_kind", "") for r in rows)),
        source_time_regressions=source_regressions,
        max_source_time_regression_ns=max_source_regression_ns,
        capture_utc_regressions=capture_regressions,
        sentinel_values=sentinel_values, blank_last_quotes=blank_last_quotes,
        upstream_loss_observable=upstream_observable,
        transport_errors=tuple(transport), schema_errors=tuple(schema_errors),
        warnings=tuple(warnings),
    )
