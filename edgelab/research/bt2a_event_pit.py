"""Store point-in-time v2 para eventos de BigTrap2Absorption.

Corrige dos fuentes de look-ahead del prototipo v1: ABS_SCORE se fecha por su
publicación al cierre de cubeta y la cinta se corta por ``sig_idx`` (equivalente
a identidad ``(ts_ns, sequence)``), no por timestamp solamente. La ventana no
puede cruzar sesión y no contiene variables de respuesta.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from hashlib import sha256
import json
from typing import Any, Iterable

import numpy as np

from edgelab.bridge.ticks import TickSeries

PIT_SCHEMA = "bt2a_event_pit_v2"
PIT_SPEC_SCHEMA = "bt2a_event_pit_v2_spec"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: object) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _payload(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in text.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            out[key] = value
    return out


def _parse_iso_ns(text: str) -> int:
    normalized = text.strip().replace("Z", "")
    return int(np.datetime64(normalized, "ns").astype(np.int64))


def _number(data: dict[str, str], key: str) -> float | None:
    value = data.get(key, "")
    if value in {"", "NaN", "nan", "None"}:
        return None
    return float(value)


def _half_ticks(price: Any, tick_size: Any, name: str) -> int:
    raw = Decimal(str(price)) * Decimal("2") / Decimal(str(tick_size))
    nearest = raw.to_integral_value(rounding=ROUND_HALF_EVEN)
    if abs(raw - nearest) > Decimal("0.00000001"):
        raise ValueError(f"{name} no alinea a medio tick: {price!r}")
    return int(nearest)


def _session_labels(ts_ns: np.ndarray) -> np.ndarray:
    from edgelab.bridge.bars import session_ids

    days = session_ids(ts_ns)
    unique = np.unique(days)
    mapping = {
        int(day): datetime.fromtimestamp(int(day) * 86400, tz=timezone.utc).strftime("%Y%m%d")
        for day in unique
    }
    return np.asarray([mapping[int(day)] for day in days], dtype="U32")


def score_index(events: Iterable[str]) -> dict[int, dict[str, Any]]:
    """Indexa ABS_SCORE por bar usando el timestamp real del log como disponibilidad."""
    out: dict[int, dict[str, Any]] = {}
    for line in events:
        parts = line.split("|", 3)
        if len(parts) != 4 or parts[2] != "ABS_SCORE":
            continue
        log_sequence, logged_at, _, payload = parts
        data = _payload(payload)
        bar = int(data["bar"])
        if bar in out:
            raise ValueError(f"ABS_SCORE duplicado para bar={bar}")
        out[bar] = {
            "log_sequence": int(log_sequence),
            "available_at_ns": _parse_iso_ns(logged_at),
            "data": data,
        }
    return out


def _validate_tick_order(ticks: TickSeries) -> tuple[dict[str, np.ndarray], np.ndarray]:
    n = len(ticks)
    if n == 0:
        raise ValueError("TickSeries vacío")
    if ticks.bid_ticks is None or ticks.ask_ticks is None:
        raise ValueError("bid_ticks y ask_ticks son obligatorios")
    arrays = {
        "ts": np.asarray(ticks.ts_ns, dtype=np.int64),
        "sequence": np.asarray(ticks.sequence, dtype=np.int64),
        "bid": np.asarray(ticks.bid_ticks, dtype=np.int64),
        "ask": np.asarray(ticks.ask_ticks, dtype=np.int64),
    }
    if any(len(values) != n for values in arrays.values()):
        raise ValueError("longitudes de TickSeries inconsistentes")
    order = np.lexsort((arrays["sequence"], arrays["ts"]))
    if not np.array_equal(order, np.arange(n, dtype=np.int64)):
        raise ValueError("ticks deben estar ordenados por (ts_ns, sequence)")
    identity = np.rec.fromarrays([arrays["ts"], arrays["sequence"]], names="ts,sequence")
    if len(np.unique(identity)) != n:
        raise ValueError("identidad (ts_ns, sequence) duplicada")
    spread = arrays["ask"] - arrays["bid"]
    if np.any(spread < 0):
        raise ValueError("book cruzado: ask_ticks < bid_ticks")
    return arrays, spread


def build_event_pit_store(
    result: dict[str, Any],
    ticks: TickSeries,
    *,
    contract: str,
    report_sessions: set[str],
    assignment: dict[str, str],
    tick_size: float,
    tape_window_ticks: int,
    session_labels: np.ndarray | None = None,
) -> dict[str, Any]:
    """Construye filas y manifiesto v2; falla cerrado ante identidad ambigua."""
    if tape_window_ticks < 2:
        raise ValueError("tape_window_ticks debe ser >= 2")
    if not np.isfinite(tick_size) or tick_size <= 0:
        raise ValueError("tick_size debe ser finito y > 0")

    arrays, spread = _validate_tick_order(ticks)
    sessions = (
        _session_labels(arrays["ts"])
        if session_labels is None
        else np.asarray(session_labels).astype(str)
    )
    if len(sessions) != len(ticks):
        raise ValueError("session_labels tiene longitud incorrecta")
    scores = score_index(result.get("events", []))

    rows: list[dict[str, Any]] = []
    event_keys: list[str] = []
    for zone in result.get("zones", []):
        sig_idx = int(zone["sig_idx"])
        if sig_idx < 0 or sig_idx >= len(ticks):
            raise ValueError(f"sig_idx fuera de rango: {sig_idx}")
        event_time_ns = int(zone["sig_ts"])
        if int(arrays["ts"][sig_idx]) != event_time_ns:
            raise ValueError("sig_idx y sig_ts no identifican el mismo tick")
        session = str(sessions[sig_idx])
        if session not in report_sessions or assignment.get(session) != contract:
            continue

        bar = int(zone["created_bar"])
        score = scores.get(bar)
        indicator_ok = score is not None
        if score is not None and int(score["available_at_ns"]) != event_time_ns:
            raise ValueError("ABS_SCORE no fue publicado al cierre causal de la cubeta")

        direction = str(zone["dir"])
        lo2 = _half_ticks(zone["lo"], tick_size, "zone.lo")
        hi2 = _half_ticks(zone["hi"], tick_size, "zone.hi")
        if hi2 < lo2:
            raise ValueError("geometría invertida")
        event_key = f"{contract}|{session}|{direction}|{event_time_ns}|{lo2}|{hi2}"
        if event_key in event_keys:
            raise ValueError(f"event_key duplicada: {event_key}")
        event_keys.append(event_key)

        tape_ok = False
        tape_reason = None
        start = sig_idx - tape_window_ticks + 1
        tape: dict[str, Any]
        if start < 0:
            tape_reason = "INSUFFICIENT_HISTORY"
            tape = {}
        elif not np.all(sessions[start : sig_idx + 1] == session):
            tape_reason = "SESSION_BOUNDARY"
            tape = {}
        else:
            span_ns = int(arrays["ts"][sig_idx] - arrays["ts"][start])
            interval_count = tape_window_ticks - 1
            if span_ns <= 0:
                tape_reason = "ZERO_TIME_SPAN"
                tape = {}
            else:
                selected_spread = spread[start : sig_idx + 1]
                tape_ok = True
                tape = {
                    "tape_window_ticks": tape_window_ticks,
                    "tape_interval_count": interval_count,
                    "tape_span_ns": span_ns,
                    "tape_rate_per_s": float(interval_count * 1_000_000_000 / span_ns),
                    "spread_p50_ticks": float(np.quantile(selected_spread, 0.5)),
                    "spread_p90_ticks": float(np.quantile(selected_spread, 0.9)),
                    "locked_spread_count": int(np.sum(selected_spread == 0)),
                }

        data = score["data"] if score is not None else {}
        rec: dict[str, Any] = {
            "schema": PIT_SCHEMA,
            "event_key": event_key,
            "instrument": str(ticks.instrument),
            "contract": contract,
            "cme_session_id": session,
            "event_time_ns": event_time_ns,
            "event_sequence": int(arrays["sequence"][sig_idx]),
            "sig_idx": sig_idx,
            "side": direction,
            "zone_lo_half_ticks": lo2,
            "zone_hi_half_ticks": hi2,
            "zone_width_half_ticks": hi2 - lo2,
            "zone_rows": int(zone["nrows"]),
            "trap_frac": float(zone["frac"]),
            "trap_volume": float(zone["vol"]),
            "indicator_bar": bar,
            "indicator_available_at_ns": (int(score["available_at_ns"]) if score else None),
            "indicator_log_sequence": (int(score["log_sequence"]) if score else None),
            "a_score": _number(data, "a_score"),
            "a_thr": _number(data, "a_thr"),
            "a_pass": (data.get("a_pass") == "True" if score else None),
            "n_hist": (int(data.get("n_hist", 0)) if score else None),
            "signed_flow": _number(data, "signed_flow"),
            "d_ticks": _number(data, "d_ticks"),
            "bucket_n_ticks": (int(data.get("n_ticks", 0)) if score else None),
            "bucket_residual": (data.get("residual") == "True" if score else None),
            "tape_window_start_idx": (start if tape_ok else None),
            "tape_window_end_idx": (sig_idx if tape_ok else None),
            "tape_unavailable_reason": tape_reason,
            **(tape or {
                "tape_window_ticks": None,
                "tape_interval_count": None,
                "tape_span_ns": None,
                "tape_rate_per_s": None,
                "spread_p50_ticks": None,
                "spread_p90_ticks": None,
                "locked_spread_count": None,
            }),
            "as_of_ok": bool(indicator_ok and tape_ok),
            "feature_available_at_ns": (
                event_time_ns if indicator_ok and tape_ok else None
            ),
        }
        rec["record_sha256"] = digest(rec)
        rows.append(rec)

    rows.sort(key=lambda row: (row["event_time_ns"], row["event_sequence"], row["event_key"]))
    session_total = Counter(row["cme_session_id"] for row in rows)
    session_ok = Counter(row["cme_session_id"] for row in rows if row["as_of_ok"])
    manifest = {
        "schema": PIT_SCHEMA,
        "target_free": True,
        "outcomes_opened": False,
        "contract": contract,
        "tape_window_ticks": tape_window_ticks,
        "tape_rate_definition": "(N-1) intervals / span between first and last of N ticks",
        "n_rows": len(rows),
        "n_event_keys": len(event_keys),
        "n_as_of_ok": int(sum(row["as_of_ok"] for row in rows)),
        "as_of_coverage": (float(np.mean([row["as_of_ok"] for row in rows])) if rows else None),
        "event_keys_sha256": digest(sorted(event_keys)),
        "rows_sha256": digest(rows),
        "per_session": {
            session: {
                "n_rows": session_total[session],
                "n_as_of_ok": session_ok[session],
            }
            for session in sorted(session_total)
        },
        "recompute_required_from": ["bt2a_event_pit_v1"],
    }
    store = {"manifest": manifest, "rows": rows}
    validate_event_pit_store(store)
    return store


def validate_event_pit_store(store: dict[str, Any]) -> None:
    manifest = store.get("manifest") or {}
    rows = store.get("rows") or []
    if manifest.get("schema") != PIT_SCHEMA:
        raise ValueError("schema PIT inesperado")
    keys = [row.get("event_key") for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("event_keys no son uno-a-uno")
    if manifest.get("n_rows") != len(rows) or manifest.get("n_event_keys") != len(keys):
        raise ValueError("conteos PIT inconsistentes")
    for row in rows:
        expected = dict(row)
        recorded = expected.pop("record_sha256", None)
        if recorded != digest(expected):
            raise ValueError(f"record_sha256 inválido: {row.get('event_key')}")
        if row.get("feature_available_at_ns") is not None and row["feature_available_at_ns"] > row["event_time_ns"]:
            raise ValueError("look-ahead detectado")
    if manifest.get("event_keys_sha256") != digest(sorted(keys)):
        raise ValueError("event_keys_sha256 inválido")
    if manifest.get("rows_sha256") != digest(rows):
        raise ValueError("rows_sha256 inválido")
