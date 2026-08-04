"""Plan puro y manifiesto para el censo outcome-free de tasas de señales."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


class CensusPlanError(ValueError):
    """El universo no permite construir un censo inequívoco."""


def build_full_plan(days):
    """Agrupa todas las sesiones elegibles por archivo, sin muestreo.

    Falla cerrado ante sesiones repetidas: una fecha no puede contarse dos
    veces por aparecer en más de un contrato o repetida dentro del manifiesto.
    """
    if not isinstance(days, list) or not days:
        raise CensusPlanError("days debe ser una lista no vacia")
    grouped = defaultdict(list)
    owner_by_date = {}
    seen_pairs = set()
    for index, day in enumerate(days):
        if not isinstance(day, dict):
            raise CensusPlanError("days[%d] debe ser objeto" % index)
        date = day.get("fecha")
        archive = day.get("archivo")
        if not isinstance(date, str) or not date:
            raise CensusPlanError("days[%d].fecha debe ser texto no vacio" % index)
        if not isinstance(archive, str) or not archive:
            raise CensusPlanError("days[%d].archivo debe ser texto no vacio" % index)
        pair = (archive, date)
        if pair in seen_pairs:
            raise CensusPlanError("sesion duplicada en manifiesto: %s/%s" % pair)
        seen_pairs.add(pair)
        previous = owner_by_date.setdefault(date, archive)
        if previous != archive:
            raise CensusPlanError(
                "sesion %s aparece en contratos %s y %s" % (date, previous, archive))
        grouped[archive].append(date)
    return [(archive, sorted(dates)) for archive, dates in sorted(grouped.items())]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_run_manifest(*, plan, universe_sha256, output_sha256, code_commit,
                       universe_info, indicators, sep_min_minutes=120,
                       lead_days=20, generated_utc=None):
    """Construye el sidecar auditable de una corrida ya materializada."""
    if generated_utc is None:
        generated_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sessions = sum(len(dates) for _, dates in plan)
    return {
        "schema_version": "signal_rate_census_run_v1",
        "generated_utc": generated_utc,
        "purpose": "EXPLORE-001 outcome-free signal-rate census",
        "code_commit": code_commit,
        "universe_manifest_sha256": universe_sha256,
        "output_sha256": output_sha256,
        "session_count": sessions,
        "contracts": [
            {"archivo": archive, "n_sessions": len(dates),
             "first_session": dates[0], "last_session": dates[-1]}
            for archive, dates in plan
        ],
        "indicators": sorted(indicators),
        "configuration": {
            "sep_min_minutes": sep_min_minutes,
            "lead_days": lead_days,
            "session_timezone": "America/Chicago",
            "chart_timezone": "America/Argentina/Buenos_Aires",
            "day_types": ["COMPLETO", "CIERRE_SEMANAL"],
            "outcomes_accessed": False,
        },
        "universe_filter_report": dict(universe_info),
    }
