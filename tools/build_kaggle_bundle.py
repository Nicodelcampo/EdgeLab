#!/usr/bin/env python3
"""Indice, sello y staging del bundle de Kaggle - v2 fail-closed.

Reemplaza al builder de `56184a3` (blob df383c06), cuya auditoria del 2026-08-14
(`docs/research/KAGGLE_BUNDLE_BUILDER_AUDITORIA_2026-08-14.md`) encontro cinco
defectos: (1) declaraba licencia CC0-1.0 sobre datos de CME que el proyecto no
puede redistribuir, (2) el docstring prometia sha256 y rangos de fechas que el
codigo nunca calculaba, (3) el `id` del dataset y el `OUT_DIR` no correspondian
al upload real y ninguna copia de los parquets llegaba al directorio de salida,
(4) carpetas ausentes y archivos ilegibles se saltaban en silencio (fail-open) y
(5) tick_size/multiplier estaban duplicados a mano frente a `edgelab.instruments`.

Doctrina de esta version:

* FAIL-CLOSED. Toda anomalia produce un registro en `quarantine` y un veredicto
  distinto de PASS. No hay `continue` silencioso: lo que se excluye se excluye
  nombrando la regla que lo excluyo.
* IDENTIDAD ANTES DE PUBLICAR. sha256 y tamanio por archivo, filas y rango
  temporal reales leidos del footer, y sha256 canonico del indice completo.
* SELLO DEL HOLDOUT POR TRADE DATE (P-17). Un archivo cuyo `ts_max` cae en o
  despues de la apertura de la sesion 2026-07-01 (= 2026-06-30T22:00:00Z) no es
  elegible: requiere re-corte fisico. El corte UTC ingenuo se calcula solo para
  MEDIR el leak que produciria (2 h de ticks del trade date del holdout).
* LICENCIA COMO GATE DE CODIGO (P-07 / M0). Sin una decision aprobada y legible
  por maquina en `docs/research/DATA_LICENSE_DECISION.md` no se emite
  `dataset-metadata.json` ni se stagea un solo byte.
* CANTIDADES DE UNA SOLA FUENTE. tick_size/tick_value/multiplicador vienen de
  `edgelab/instruments.py`; aca solo vive el layout de carpetas de la maquina
  local. Si el layout y el universo de instrumentos divergen, el tool aborta.

Uso:
    python tools/build_kaggle_bundle.py --selftest
    python tools/build_kaggle_bundle.py                       # plan, sin escribir nada publicable
    python tools/build_kaggle_bundle.py --dataset-id user/slug --emit-metadata --stage

Codigos de salida: 0 PASS, 2 ABSTAIN_*, 1 FAIL_*.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SCHEMA_VERSION = 2
TOOL_ID = "tools/build_kaggle_bundle.py@v2"
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE = Path("E:/EdgeLab/data/nt8")
DEFAULT_OUT = Path("E:/EdgeLab/kaggle_dataset")
DEFAULT_LICENSE_DOC = REPO_ROOT / "docs" / "research" / "DATA_LICENSE_DECISION.md"

TS_COLUMN = "ts_utc_ns"
NS_PER_SEC = 1_000_000_000
FILENAME_RE = re.compile(
    r"^(?P<asset>[A-Z0-9]+)_(?P<contract>\d{2}-\d{2})_ticks\.parquet$"
)

# --- Sello del holdout (Contrato Kaggle v2 + enmienda v2.1) -----------------
HOLDOUT_FIRST_TRADE_DATE = 20260701
RESEARCH_MAX_TRADE_DATE = 20260630
NAIVE_UTC_CUT_NS = (
    int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()) * NS_PER_SEC
)

# --- Layout LOCAL de carpetas (unico dato de maquina que vive aca) ----------
ASSET_FOLDERS = {
    "6B": "6B_parquet",
    "6E": "6E",
    "6J": "6J_parquet",
    "ES": "ES_parquet",
    "GC": "GC_parquet",
    "MBT": "MBT_parquet",
    "MES": "MES_parquet",
    "MNQ": "MNQ_parquet",
    "NQ": "NQ_parquet",
    "YM": "YM_parquet",
    "ZB": "ZB",
}

# Etiquetas de presentacion (no son cantidades: no pueden driftear contra nada).
ASSET_LABELS = {
    "6B": ("British Pound futures", "FX", False),
    "6E": ("Euro FX futures", "FX", False),
    "6J": ("Japanese Yen futures", "FX", False),
    "ES": ("E-mini S&P 500", "Equity index", False),
    "GC": ("Gold futures", "Metals", False),
    "MBT": ("Micro Bitcoin futures", "Crypto", True),
    "MES": ("Micro E-mini S&P 500", "Equity index", True),
    "MNQ": ("Micro E-mini Nasdaq-100", "Equity index", True),
    "NQ": ("E-mini Nasdaq-100", "Equity index", False),
    "YM": ("E-mini Dow ($5)", "Equity index", False),
    "ZB": ("30-Year U.S. Treasury Bond futures", "Rates", False),
}

# Multiplicadores declarados a mano por el builder v1. Se conservan como
# fixture de regresion: el self-test exige que las cantidades de
# `edgelab.instruments` los reproduzcan. Si alguna vez divergen, el que esta
# mal es el que no tiene contrato de CME atras.
V1_MULTIPLIERS = {
    "6B": 62500.0,
    "6E": 125000.0,
    "6J": 12500000.0,
    "ES": 50.0,
    "GC": 100.0,
    "MBT": 0.1,
    "MES": 5.0,
    "MNQ": 2.0,
    "NQ": 20.0,
    "YM": 5.0,
    "ZB": 1000.0,
}

# Archivos auxiliares que el builder v1 filtraba en silencio con
# `"all" not in f.name and "prev" not in f.name`. Ahora se excluyen igual, pero
# nombrando la regla y contandolos en el indice.
AUX_PATTERNS = (("_all", "agregado multi-contrato"), ("prev", "contrato anterior"))

# --- Licencia ---------------------------------------------------------------
LICENSE_GATE_OPEN = "<!-- EDGELAB-LICENSE-GATE"
LICENSE_GATE_CLOSE = "-->"
LICENSE_REQUIRED_KEYS = (
    "schema",
    "status",
    "provider",
    "redistribution_allowed",
    "kaggle_visibility",
    "kaggle_license_name",
    "approved_by",
    "approved_at_utc",
    "terms_source_sha256",
)
# Nombres de licencia de Kaggle que AFIRMAN derechos de redistribucion o de
# dominio publico que EdgeLab no posee sobre datos de mercado de CME.
FORBIDDEN_LICENSE_NAMES = {
    "cc0-1.0",
    "pddl",
    "odbl-1.0",
    "dbcl-1.0",
    "cc-by-4.0",
    "cc-by-sa-4.0",
    "cc-by-sa-3.0",
    "cc-by-nc-sa-4.0",
    "gpl-2.0",
    "mit",
    "apache-2.0",
    "unlicense",
}
ALLOWED_LICENSE_NAMES = {"copyright-authors", "other", "unknown"}
PLACEHOLDER_RE = re.compile(r"^\s*(<.*>|tbd|todo|pendiente|n/?a|)\s*$", re.I)

VERDICT_PRECEDENCE = (
    "FAIL_INSTRUMENTS",
    "FAIL_LAYOUT",
    "FAIL_INTEGRITY",
    "ABSTAIN_LICENSE",
    "ABSTAIN_HOLDOUT",
    "ABSTAIN_CAPACITY",
    "PASS",
)
VERDICT_EXIT = {"PASS": 0}


def verdict_exit_code(verdict: str) -> int:
    if verdict == "PASS":
        return 0
    return 2 if verdict.startswith("ABSTAIN") else 1


# ---------------------------------------------------------------------------
# Carga de modulos del repo por path, con identidad registrada
# ---------------------------------------------------------------------------
def load_module_by_path(alias: str, path: Path):
    """Carga un modulo del repo por path (fail-closed si falta).

    Se carga por path y no por `import edgelab...` para que el tool corra desde
    cualquier cwd sin PYTHONPATH y para poder registrar el blob sha1 exacto del
    archivo que efectivamente se ejecuto.
    """
    if not path.is_file():
        raise SystemExit(f"ABORT: falta el modulo requerido {path}")
    spec = importlib.util.spec_from_file_location(alias, str(path))
    if spec is None or spec.loader is None:  # pragma: no cover
        raise SystemExit(f"ABORT: no se pudo preparar el modulo {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


def load_repo_modules(repo_root: Path) -> SimpleNamespace:
    paths = {
        "instruments": repo_root / "edgelab" / "instruments.py",
        "sessions_cme": repo_root / "edgelab" / "kaggle" / "sessions_cme.py",
        "identity": repo_root / "edgelab" / "kaggle" / "identity.py",
        "inventory": repo_root / "edgelab" / "kaggle" / "inventory.py",
    }
    mods = {
        name: load_module_by_path(f"_kbundle_{name}", p) for name, p in paths.items()
    }
    identity = mods["identity"]
    code_identity = identity.code_identity({k: str(v) for k, v in paths.items()})
    return SimpleNamespace(
        instruments=mods["instruments"],
        sessions=mods["sessions_cme"],
        identity=identity,
        inventory=mods["inventory"],
        code_identity=code_identity,
    )


# ---------------------------------------------------------------------------
# Gate de licencia
# ---------------------------------------------------------------------------
def parse_license_gate(path: Path) -> dict:
    """Lee el bloque legible por maquina de la decision de licencia."""
    out: dict = {
        "path": str(path),
        "found": False,
        "values": {},
        "missing": list(LICENSE_REQUIRED_KEYS),
        "reasons": [],
    }
    if not path.is_file():
        out["reasons"].append(f"no existe {path}")
        return out
    text = path.read_text(encoding="utf-8", errors="replace")
    if LICENSE_GATE_OPEN not in text:
        out["reasons"].append(
            f"el documento no contiene el bloque {LICENSE_GATE_OPEN} ... {LICENSE_GATE_CLOSE}"
        )
        return out
    block = text.split(LICENSE_GATE_OPEN, 1)[1]
    if LICENSE_GATE_CLOSE not in block:
        out["reasons"].append("bloque de licencia sin cierre '-->'")
        return out
    block = block.split(LICENSE_GATE_CLOSE, 1)[0]
    values: dict = {}
    for line in block.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        values[key.strip().lower()] = val.strip()
    out["found"] = True
    out["values"] = values
    out["missing"] = [
        k
        for k in LICENSE_REQUIRED_KEYS
        if k not in values or PLACEHOLDER_RE.match(values.get(k, ""))
    ]
    return out


def evaluate_license(gate: dict) -> dict:
    """Decide si se puede publicar y con que nombre de licencia."""
    reasons = list(gate.get("reasons", []))
    values = gate.get("values", {})
    status = (values.get("status") or "").strip().upper()
    lic_name = (values.get("kaggle_license_name") or "").strip()
    redistribution = (values.get("redistribution_allowed") or "").strip().lower()
    visibility = (values.get("kaggle_visibility") or "").strip().lower()

    # Un nombre de licencia prohibido es un error de codigo/documento, no una
    # abstencion: aborta antes de cualquier escritura.
    if lic_name and lic_name.lower() in FORBIDDEN_LICENSE_NAMES:
        raise SystemExit(
            "ABORT: kaggle_license_name='%s' afirma derechos de redistribucion "
            "que EdgeLab no tiene sobre datos de CME. El builder v1 declaraba "
            "CC0-1.0; esta prohibido por codigo." % lic_name
        )

    if gate.get("missing"):
        reasons.append("campos sin completar: " + ", ".join(gate["missing"]))
    if status != "APPROVED":
        reasons.append(f"status={status or 'AUSENTE'} (se requiere APPROVED)")
    if lic_name and lic_name.lower() not in ALLOWED_LICENSE_NAMES:
        reasons.append(
            f"kaggle_license_name='{lic_name}' no esta en la lista permitida "
            + str(sorted(ALLOWED_LICENSE_NAMES))
        )
    if redistribution not in {"true", "false"}:
        reasons.append("redistribution_allowed debe ser true|false")
    private_required = redistribution != "true"
    if private_required and visibility != "private_only":
        reasons.append(
            "sin derecho de redistribucion la visibilidad debe ser private_only "
            f"(dice '{visibility or 'AUSENTE'}')"
        )
    return {
        "path": gate.get("path"),
        "gate_found": gate.get("found", False),
        "status": status or None,
        "provider": values.get("provider"),
        "kaggle_license_name": lic_name or None,
        "redistribution_allowed": redistribution or None,
        "kaggle_visibility": visibility or None,
        "approved_by": values.get("approved_by"),
        "approved_at_utc": values.get("approved_at_utc"),
        "terms_source_sha256": values.get("terms_source_sha256"),
        "force_private": private_required,
        "ok": not reasons,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Descubrimiento de archivos
# ---------------------------------------------------------------------------
def discover_files(base: Path) -> dict:
    """Recorre el layout declarado. Nada se salta en silencio."""
    candidates: list[dict] = []
    excluded: list[dict] = []
    quarantine: list[dict] = []

    for asset in sorted(ASSET_FOLDERS):
        folder = base / ASSET_FOLDERS[asset]
        if not folder.is_dir():
            quarantine.append(
                {
                    "kind": "MISSING_FOLDER",
                    "asset": asset,
                    "path": str(folder),
                    "detail": "carpeta declarada en ASSET_FOLDERS que no existe",
                }
            )
            continue
        try:
            entries = sorted(folder.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            quarantine.append(
                {
                    "kind": "UNREADABLE_FOLDER",
                    "asset": asset,
                    "path": str(folder),
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        for entry in entries:
            if not entry.is_file():
                excluded.append(
                    {
                        "asset": asset,
                        "path": str(entry),
                        "rule": "no es archivo regular",
                    }
                )
                continue
            if entry.suffix.lower() != ".parquet":
                excluded.append(
                    {"asset": asset, "path": str(entry), "rule": "extension != .parquet"}
                )
                continue
            aux = next(
                (why for pat, why in AUX_PATTERNS if pat in entry.name.lower()), None
            )
            if aux:
                excluded.append(
                    {
                        "asset": asset,
                        "path": str(entry),
                        "bytes": entry.stat().st_size,
                        "rule": f"auxiliar: {aux} (patron {AUX_PATTERNS})",
                    }
                )
                continue
            match = FILENAME_RE.match(entry.name)
            if not match:
                quarantine.append(
                    {
                        "kind": "FILENAME_UNPARSEABLE",
                        "asset": asset,
                        "path": str(entry),
                        "detail": f"no matchea {FILENAME_RE.pattern}",
                    }
                )
                continue
            if match.group("asset") != asset:
                quarantine.append(
                    {
                        "kind": "ASSET_FOLDER_MISMATCH",
                        "asset": asset,
                        "path": str(entry),
                        "detail": f"nombre declara {match.group('asset')}",
                    }
                )
                continue
            candidates.append(
                {
                    "asset": asset,
                    "contract": match.group("contract"),
                    "folder": ASSET_FOLDERS[asset],
                    "path": str(entry),
                    "file": entry.name,
                }
            )
    return {
        "candidates": candidates,
        "excluded": excluded,
        "quarantine": quarantine,
    }


# ---------------------------------------------------------------------------
# Indice + gates
# ---------------------------------------------------------------------------
def build_index(
    *,
    base: Path,
    out_dir: Path,
    dataset_id: str | None,
    license_doc: Path,
    mods: SimpleNamespace,
    census_fn=None,
    hash_files: bool = True,
) -> dict:
    identity = mods.identity
    sessions = mods.sessions
    inventory = mods.inventory
    instruments = mods.instruments
    census_fn = census_fn or (lambda p: inventory.footer_census(str(p), ts_column=TS_COLUMN))

    gates: list[dict] = []

    def add_gate(name: str, passed: bool, rule: str, detail) -> None:
        gates.append(
            {"gate": name, "pass": bool(passed), "rule": rule, "detail": detail}
        )

    # --- G-INSTRUMENT: cantidades de una sola fuente ------------------------
    universe = getattr(instruments, "CME_UNIVERSE", {})
    layout_syms = set(ASSET_FOLDERS)
    inst_syms = set(universe)
    inst_table = {}
    drift = []
    for sym in sorted(inst_syms & layout_syms):
        inst = universe[sym]
        label, klass, micro = ASSET_LABELS.get(sym, (sym, "unknown", False))
        mult = inst.multiplier
        inst_table[sym] = {
            "folder": ASSET_FOLDERS[sym],
            "name": label,
            "asset_class": klass,
            "is_micro": micro,
            "tick_size": inst.tick_size,
            "tick_value": inst.tick_value,
            "multiplier": mult,
            "source": "edgelab/instruments.py::CME_UNIVERSE",
        }
        expected = V1_MULTIPLIERS.get(sym)
        if expected is not None and not math.isclose(mult, expected, rel_tol=1e-9):
            drift.append(f"{sym}: instruments={mult!r} vs fixture v1={expected!r}")
    add_gate(
        "G-INSTRUMENT",
        not drift and layout_syms == inst_syms,
        "el layout local y CME_UNIVERSE deben coincidir; multiplicadores sin drift",
        {
            "layout_only": sorted(layout_syms - inst_syms),
            "universe_only": sorted(inst_syms - layout_syms),
            "multiplier_drift": drift,
            "assets": len(inst_table),
        },
    )

    # --- Sello del holdout --------------------------------------------------
    holdout_open_ns = int(sessions.session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0])
    seal = {
        "first_holdout_trade_date": HOLDOUT_FIRST_TRADE_DATE,
        "research_max_trade_date": RESEARCH_MAX_TRADE_DATE,
        "holdout_open_ns": holdout_open_ns,
        "holdout_open_utc": datetime.fromtimestamp(
            holdout_open_ns / NS_PER_SEC, tz=timezone.utc
        ).isoformat(),
        "naive_utc_cut_ns": NAIVE_UTC_CUT_NS,
        "naive_cut_gap_seconds": (NAIVE_UTC_CUT_NS - holdout_open_ns) // NS_PER_SEC,
        "rule": (
            "elegible <=> ts_max_ns < apertura de la sesion CME del 2026-07-01 "
            "(17:00 CT del 2026-06-30). Un corte en 2026-07-01T00:00:00Z deja "
            "pasar las 2 h finales del trade date del holdout."
        ),
    }

    # --- Descubrimiento -----------------------------------------------------
    disc = discover_files(base)
    quarantine = list(disc["quarantine"])
    add_gate(
        "G-LAYOUT",
        not any(q["kind"] in {"MISSING_FOLDER", "UNREADABLE_FOLDER"} for q in quarantine)
        and bool(disc["candidates"]),
        "todas las carpetas declaradas existen y son legibles; hay candidatos",
        {
            "folders": len(ASSET_FOLDERS),
            "candidates": len(disc["candidates"]),
            "excluded_by_rule": len(disc["excluded"]),
            "quarantine": [q for q in quarantine],
        },
    )

    # --- Censo + identidad + holdout por archivo ---------------------------
    records: list[dict] = []
    for cand in disc["candidates"]:
        path = Path(cand["path"])
        rec = dict(cand)
        try:
            census = census_fn(path)
        except Exception as exc:  # fail-closed: el v1 hacia print y seguia
            quarantine.append(
                {
                    "kind": "CENSUS_ERROR",
                    "asset": cand["asset"],
                    "path": cand["path"],
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        rec.update(
            {
                k: census.get(k)
                for k in (
                    "bytes",
                    "rows",
                    "row_groups",
                    "columns",
                    "column_names",
                    "created_by",
                    "format_version",
                    "stats_available",
                    "ts_min_ns",
                    "ts_max_ns",
                    "row_groups_time_ordered",
                )
            }
        )
        if hash_files:
            rec["sha256"] = identity.sha256_file(str(path))
            rec["git_blob_sha1"] = identity.git_blob_sha1(str(path))
        problems = []
        if not rec.get("rows"):
            problems.append("rows=0 o ausente")
        if not rec.get("stats_available"):
            problems.append(
                "sin estadisticas min/max de ts_utc_ns: no se puede certificar "
                "ausencia de holdout"
            )
        ts_min, ts_max = rec.get("ts_min_ns"), rec.get("ts_max_ns")
        if ts_min is None or ts_max is None:
            problems.append("rango temporal ausente")
        elif ts_min > ts_max:
            problems.append("ts_min > ts_max")
        if problems:
            quarantine.append(
                {
                    "kind": "UNCERTIFIABLE",
                    "asset": cand["asset"],
                    "path": cand["path"],
                    "detail": "; ".join(problems),
                }
            )
            rec["eligible"] = False
            rec["exclusion"] = "UNCERTIFIABLE"
            records.append(rec)
            continue

        ts = np.asarray([ts_min, ts_max], dtype=np.int64)
        td = sessions.trade_date_ymd(ts)
        rec["trade_date_min"] = int(td[0])
        rec["trade_date_max"] = int(td[1])
        rec["ts_min_utc"] = datetime.fromtimestamp(
            ts_min / NS_PER_SEC, tz=timezone.utc
        ).isoformat()
        rec["ts_max_utc"] = datetime.fromtimestamp(
            ts_max / NS_PER_SEC, tz=timezone.utc
        ).isoformat()
        rec["holdout_overlap"] = bool(ts_max >= holdout_open_ns)
        rec["naive_utc_overlap"] = bool(ts_max >= NAIVE_UTC_CUT_NS)
        rec["holdout_overlap_seconds"] = (
            int((ts_max - holdout_open_ns) // NS_PER_SEC) if rec["holdout_overlap"] else 0
        )
        rec["eligible"] = not rec["holdout_overlap"]
        if rec["holdout_overlap"]:
            rec["exclusion"] = "RECUT_REQUIRED"
            quarantine.append(
                {
                    "kind": "HOLDOUT_OVERLAP",
                    "asset": cand["asset"],
                    "path": cand["path"],
                    "detail": (
                        f"ts_max={rec['ts_max_utc']} (trade date {rec['trade_date_max']}) "
                        f"entra {rec['holdout_overlap_seconds']} s en el holdout; "
                        "requiere re-corte fisico antes de publicar"
                    ),
                }
            )
        records.append(rec)

    eligible = [r for r in records if r.get("eligible")]
    holdout_files = [r for r in records if r.get("exclusion") == "RECUT_REQUIRED"]

    add_gate(
        "G-IDENTITY",
        bool(records)
        and all(r.get("stats_available") for r in records)
        and (not hash_files or all(r.get("sha256") for r in records)),
        "sha256 + filas + rango temporal real por archivo",
        {
            "files": len(records),
            "hashed": sum(1 for r in records if r.get("sha256")),
            "uncertifiable": sum(
                1 for r in records if r.get("exclusion") == "UNCERTIFIABLE"
            ),
        },
    )
    add_gate(
        "G-HOLDOUT",
        not holdout_files,
        "ningun archivo publicable puede contener ticks del trade date 2026-07-01 o posterior",
        {
            "files_with_overlap": len(holdout_files),
            "files_with_naive_overlap": sum(
                1 for r in records if r.get("naive_utc_overlap")
            ),
            "recut_required": [r["file"] for r in holdout_files],
            "max_overlap_seconds": max(
                [r["holdout_overlap_seconds"] for r in holdout_files] or [0]
            ),
        },
    )

    # --- Presupuesto --------------------------------------------------------
    summary = inventory.summarize_census(
        [
            {
                k: v
                for k, v in r.items()
                if k
                in (
                    "asset",
                    "file",
                    "rows",
                    "bytes",
                    "columns",
                    "column_names",
                    "stats_available",
                )
            }
            for r in eligible
        ]
    )
    metadata_files = 4  # bundle_index.json, dataset-metadata.json, README.md, files.sha256
    budget = inventory.budget_gates(
        summary, top_level_files=len(eligible) + metadata_files
    )
    add_gate(
        "G-BUDGET",
        budget["verdict"] == "PASS",
        "presupuesto tecnico del contrato + limites de plataforma",
        budget,
    )

    # --- Licencia -----------------------------------------------------------
    lic = evaluate_license(parse_license_gate(license_doc))
    add_gate(
        "G-LIC",
        lic["ok"],
        "decision de licencia aprobada y legible por maquina (P-07/M0)",
        lic,
    )

    failed = {g["gate"] for g in gates if not g["pass"]}
    verdict = "PASS"
    if "G-INSTRUMENT" in failed:
        verdict = "FAIL_INSTRUMENTS"
    elif "G-LAYOUT" in failed:
        verdict = "FAIL_LAYOUT"
    elif "G-IDENTITY" in failed or any(
        q["kind"] in {"CENSUS_ERROR", "UNCERTIFIABLE", "FILENAME_UNPARSEABLE", "ASSET_FOLDER_MISMATCH"}
        for q in quarantine
    ):
        verdict = "FAIL_INTEGRITY"
    elif "G-LIC" in failed:
        verdict = "ABSTAIN_LICENSE"
    elif "G-HOLDOUT" in failed:
        verdict = "ABSTAIN_HOLDOUT"
    elif "G-BUDGET" in failed:
        verdict = "ABSTAIN_CAPACITY"

    index = {
        "tool": TOOL_ID,
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": str(base),
        "out_dir": str(out_dir),
        "dataset_id": dataset_id,
        "ts_column": TS_COLUMN,
        "code_identity": mods.code_identity,
        "instruments": inst_table,
        "holdout_seal": seal,
        "license": lic,
        "files": records,
        "eligible_files": [r["file"] for r in eligible],
        "excluded_by_rule": disc["excluded"],
        "quarantine": quarantine,
        "summary": summary,
        "budget": budget,
        "gates": gates,
        "verdict": verdict,
        "publishable": verdict == "PASS",
    }
    index["index_sha256"] = identity.sha256_json(index)
    return index


# ---------------------------------------------------------------------------
# Artefactos
# ---------------------------------------------------------------------------
def stage_bundle(index: dict, out_dir: Path, identity, prefer_hardlink: bool = True) -> dict:
    """Copia (o enlaza) los archivos elegibles al directorio de salida."""
    out_dir.mkdir(parents=True, exist_ok=True)
    staged, lines = [], []
    for rec in index["files"]:
        if not rec.get("eligible"):
            continue
        src, dst = Path(rec["path"]), out_dir / rec["file"]
        method = "hardlink"
        if dst.exists():
            dst.unlink()
        try:
            if not prefer_hardlink:
                raise OSError("hardlink deshabilitado")
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
            method = "copy"
        got = identity.sha256_file(str(dst))
        if rec.get("sha256") and got != rec["sha256"]:
            raise SystemExit(
                f"ABORT: staging corrupto en {dst}: sha256 {got} != {rec['sha256']}"
            )
        staged.append({"file": rec["file"], "method": method, "sha256": got})
        lines.append(f"{got}  {rec['file']}")
    sheet = out_dir / "files.sha256"
    sheet.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "staged": staged,
        "checksum_sheet": str(sheet),
        "checksum_sheet_sha256": identity.sha256_file(str(sheet)),
    }


def build_metadata(index: dict, dataset_id: str) -> dict:
    lic = index["license"]
    total_rows = index["summary"].get("total_rows", 0)
    assets = sorted({r["asset"] for r in index["files"] if r.get("eligible")})
    tdmin = min(r["trade_date_min"] for r in index["files"] if r.get("eligible"))
    tdmax = max(r["trade_date_max"] for r in index["files"] if r.get("eligible"))
    desc = (
        "Tick data de futuros de CME normalizado por EdgeLab para investigacion "
        "interna.\n\n"
        f"Activos: {', '.join(assets)}. Filas: {total_rows:,}. "
        f"Trade dates (CME, America/Chicago): {tdmin} a {tdmax}.\n"
        f"Holdout sellado: el bundle termina antes de la apertura de la sesion "
        f"{index['holdout_seal']['first_holdout_trade_date']} "
        f"({index['holdout_seal']['holdout_open_utc']}).\n\n"
        "RESTRICCION DE USO: dataset privado. La informacion de mercado subyacente "
        "esta sujeta a los terminos del proveedor y NO puede redistribuirse ni "
        "hacerse publica. No cambiar la visibilidad a publico.\n\n"
        f"Identidad: index_sha256={index['index_sha256']}; "
        f"schema_version={index['schema_version']}; tool={index['tool']}."
    )
    return {
        "title": "EdgeLab CME futures tick universe (privado)",
        "id": dataset_id,
        "isPrivate": True,
        "licenses": [{"name": lic["kaggle_license_name"]}],
        "description": desc,
        "keywords": ["finance", "futures", "market microstructure"],
        "resources": [
            {
                "path": r["file"],
                "description": (
                    f"{r['asset']} {r['contract']} | rows={r['rows']} | "
                    f"trade_dates={r['trade_date_min']}..{r['trade_date_max']} | "
                    f"sha256={r.get('sha256', 'NA')}"
                ),
            }
            for r in index["files"]
            if r.get("eligible")
        ],
    }


def build_readme(index: dict) -> str:
    seal = index["holdout_seal"]
    rows = index["summary"].get("total_rows", 0)
    gib = index["summary"].get("total_gib", 0.0)
    lines = [
        "# EdgeLab - CME futures tick universe (dataset privado)",
        "",
        "> **RESTRICCION DE USO.** Dataset privado. La informacion de mercado ",
        "> subyacente esta sujeta a los terminos del proveedor y no puede ",
        "> redistribuirse, republicarse ni hacerse publica. La visibilidad publica ",
        "> requiere una decision de licencia aprobada ",
        "> (`docs/research/DATA_LICENSE_DECISION.md`).",
        "",
        "## Identidad",
        "",
        f"- `index_sha256`: `{index['index_sha256']}`",
        f"- generado por: `{index['tool']}` (schema {index['schema_version']})",
        f"- veredicto de gates: **{index['verdict']}**",
        f"- archivos elegibles: {len(index['eligible_files'])} | filas: {rows:,} | {gib} GiB",
        "",
        "## Sello del holdout",
        "",
        f"- primer trade date del holdout: {seal['first_holdout_trade_date']}",
        f"- apertura de esa sesion: {seal['holdout_open_utc']} (17:00 CT del dia anterior)",
        f"- un corte UTC ingenuo dejaria pasar {seal['naive_cut_gap_seconds']} s de holdout",
        "",
        "## Esquema",
        "",
        f"- columna temporal: `{index['ts_column']}` (int64, nanosegundos UTC)",
        f"- columnas: {', '.join(index['summary'].get('schema', []) or [])}",
        "",
        "## Contenido",
        "",
        "| activo | nombre | clase | contratos | filas | GiB | tick_size | multiplicador |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    by_asset = index["summary"].get("by_asset", {})
    for sym, meta in sorted(index["instruments"].items()):
        acc = by_asset.get(sym, {})
        lines.append(
            "| {sym} | {name} | {klass} | {c} | {rows} | {gib} | {ts} | {mult} |".format(
                sym=sym,
                name=meta["name"],
                klass=meta["asset_class"],
                c=acc.get("contracts", 0),
                rows=f"{acc.get('rows', 0):,}",
                gib=round(acc.get("bytes", 0) / (1 << 30), 3),
                ts=meta["tick_size"],
                mult=meta["multiplier"],
            )
        )
    lines += [
        "",
        "Cantidades por instrumento: `edgelab/instruments.py::CME_UNIVERSE` ",
        "(fuente unica; el multiplicador es derivado = tick_value / tick_size).",
        "",
        "## Verificacion",
        "",
        "```bash",
        "sha256sum -c files.sha256",
        "```",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def _fake_census(specs: dict):
    def fn(path):
        name = os.path.basename(str(path))
        spec = specs[name]
        if spec.get("raise"):
            raise RuntimeError("footer ilegible (simulado)")
        asset, contract = name.split("_")[0], name.split("_")[1]
        rec = {
            "path": str(path),
            "file": name,
            "bytes": spec.get("bytes", os.path.getsize(path)),
            "asset": asset,
            "contract": contract,
            "filename_ok": True,
            "rows": spec.get("rows", 1000),
            "row_groups": 2,
            "columns": 8,
            "created_by": "selftest",
            "format_version": "2.6",
            "column_names": [
                "ts_utc_ns",
                "price",
                "volume",
                "bid_ticks",
                "ask_ticks",
                "aggressor",
                "sequence",
                "contract",
            ],
            "column_types": ["int64"] * 8,
            "ts_column": TS_COLUMN,
            "stats_available": spec.get("stats", True),
            "row_groups_time_ordered": True,
        }
        if spec.get("stats", True):
            rec["ts_min_ns"] = spec["ts_min"]
            rec["ts_max_ns"] = spec["ts_max"]
        return rec

    return fn


def _write_license_doc(path: Path, **over) -> Path:
    vals = {
        "schema": "1",
        "status": "PENDING",
        "provider": "CME Group via NinjaTrader Continuum",
        "redistribution_allowed": "false",
        "kaggle_visibility": "private_only",
        "kaggle_license_name": "copyright-authors",
        "approved_by": "<por completar>",
        "approved_at_utc": "<por completar>",
        "terms_source_sha256": "<por completar>",
    }
    vals.update({k: str(v) for k, v in over.items()})
    body = "\n".join(f"{k}: {v}" for k, v in vals.items())
    path.write_text(
        f"# decision de licencia (selftest)\n\n{LICENSE_GATE_OPEN}\n{body}\n{LICENSE_GATE_CLOSE}\n",
        encoding="utf-8",
    )
    return path


def selftest() -> int:
    fails: list[str] = []

    def check(name: str, cond: bool, extra: str = "") -> None:
        print(f"{'OK   ' if cond else 'FALLA'} {name}" + (f"  [{extra}]" if extra else ""))
        if not cond:
            fails.append(name)

    mods = load_repo_modules(REPO_ROOT)
    sessions, identity = mods.sessions, mods.identity

    # T1 - aritmetica del sello
    open_ns = int(sessions.session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0])
    iso = datetime.fromtimestamp(open_ns / NS_PER_SEC, tz=timezone.utc).isoformat()
    check("T1 apertura del holdout = 2026-06-30T22:00:00+00:00", iso == "2026-06-30T22:00:00+00:00", iso)
    gap = (NAIVE_UTC_CUT_NS - open_ns) // NS_PER_SEC
    check("T1b el corte UTC ingenuo deja pasar 7200 s", gap == 7200, f"gap={gap}")
    td = sessions.trade_date_ymd(np.asarray([open_ns - 1, open_ns], dtype=np.int64))
    check(
        "T1c trade date cambia exactamente en ese ns",
        [int(td[0]), int(td[1])] == [RESEARCH_MAX_TRADE_DATE, HOLDOUT_FIRST_TRADE_DATE],
        f"{int(td[0])}->{int(td[1])}",
    )

    # T2 - multiplicadores contra el fixture del builder v1
    uni = mods.instruments.CME_UNIVERSE
    bad = [
        f"{s}:{uni[s].multiplier}!={V1_MULTIPLIERS[s]}"
        for s in sorted(V1_MULTIPLIERS)
        if s not in uni or not math.isclose(uni[s].multiplier, V1_MULTIPLIERS[s], rel_tol=1e-9)
    ]
    check("T2 los 11 multiplicadores reproducen la tabla del builder v1", not bad, "; ".join(bad))
    check("T2b layout == CME_UNIVERSE", set(ASSET_FOLDERS) == set(uni))

    # T3 - hashing real contra hashlib
    import hashlib

    with tempfile.TemporaryDirectory() as td_str:
        tmp = Path(td_str)
        blob = tmp / "x.bin"
        blob.write_bytes(b"edgelab" * 1000)
        check(
            "T3 sha256_file == hashlib sobre los bytes",
            identity.sha256_file(str(blob)) == hashlib.sha256(blob.read_bytes()).hexdigest(),
        )

    # Escenario base: 2 activos limpios + 1 con holdout
    day = 86_400 * NS_PER_SEC
    clean_min = open_ns - 60 * day
    specs = {
        "ES_06-26_ticks.parquet": {"rows": 5_000_000, "ts_min": clean_min, "ts_max": open_ns - 1, "bytes": 200 << 20},
        "6E_06-26_ticks.parquet": {"rows": 1_131_047, "ts_min": clean_min, "ts_max": open_ns - 3600 * NS_PER_SEC, "bytes": 40 << 20},
        "ES_09-26_ticks.parquet": {"rows": 9_000_000, "ts_min": clean_min, "ts_max": NAIVE_UTC_CUT_NS + 10 * day, "bytes": 300 << 20},
    }

    def make_tree(root: Path, names) -> None:
        for name in names:
            asset = name.split("_")[0]
            folder = root / ASSET_FOLDERS[asset]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(b"PAR1" + name.encode())
        for sym in ASSET_FOLDERS:  # el resto del layout debe existir
            (root / ASSET_FOLDERS[sym]).mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td_str:
        tmp = Path(td_str)
        base = tmp / "nt8"
        make_tree(base, specs)
        lic_pending = _write_license_doc(tmp / "lic_pending.md")
        lic_ok = _write_license_doc(
            tmp / "lic_ok.md",
            status="APPROVED",
            approved_by="Nico",
            approved_at_utc="2026-08-14T23:00:00Z",
            terms_source_sha256="a" * 64,
        )

        # T4 - licencia PENDING -> ABSTAIN_LICENSE
        idx = build_index(
            base=base, out_dir=tmp / "out", dataset_id="u/s",
            license_doc=lic_pending, mods=mods, census_fn=_fake_census(specs),
        )
        check("T4 status PENDING -> ABSTAIN_LICENSE", idx["verdict"] == "ABSTAIN_LICENSE", idx["verdict"])
        check("T4b exit code 2", verdict_exit_code(idx["verdict"]) == 2)

        # T5 - CC0 en el documento -> abort duro
        lic_cc0 = _write_license_doc(
            tmp / "lic_cc0.md", status="APPROVED", kaggle_license_name="CC0-1.0",
            approved_by="x", approved_at_utc="2026-08-14T00:00:00Z", terms_source_sha256="b" * 64,
        )
        try:
            build_index(base=base, out_dir=tmp / "out", dataset_id="u/s",
                        license_doc=lic_cc0, mods=mods, census_fn=_fake_census(specs))
            check("T5 CC0-1.0 aborta", False, "no aborto")
        except SystemExit as exc:
            check("T5 CC0-1.0 aborta", "CC0-1.0" in str(exc), str(exc)[:60])

        # T6 - licencia aprobada, pero el 09-26 tiene holdout -> ABSTAIN_HOLDOUT
        idx = build_index(base=base, out_dir=tmp / "out", dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(specs))
        holdout = [r for r in idx["files"] if r.get("exclusion") == "RECUT_REQUIRED"]
        check("T6 ABSTAIN_HOLDOUT con el 09-26 sin cortar", idx["verdict"] == "ABSTAIN_HOLDOUT", idx["verdict"])
        check("T6b el archivo con holdout no es elegible", [r["file"] for r in holdout] == ["ES_09-26_ticks.parquet"])
        check("T6c se mide el leak del corte UTC ingenuo", holdout[0]["naive_utc_overlap"] is True)
        check("T6d el limpio de ts_max = apertura-1ns SI es elegible",
              any(r["file"] == "ES_06-26_ticks.parquet" and r["eligible"] for r in idx["files"]))

        # T7 - sin el archivo con holdout -> PASS y artefactos
        specs_clean = {k: v for k, v in specs.items() if k != "ES_09-26_ticks.parquet"}
        base2 = tmp / "nt8_clean"
        make_tree(base2, specs_clean)
        out2 = tmp / "out2"
        idx = build_index(base=base2, out_dir=out2, dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(specs_clean))
        check("T7 PASS con bundle limpio", idx["verdict"] == "PASS", idx["verdict"])
        check("T7b index_sha256 cierra contra su propio contenido",
              idx["index_sha256"] == identity.sha256_json({k: v for k, v in idx.items() if k != "index_sha256"}))
        meta = build_metadata(idx, "u/s")
        check("T7c metadata privada y sin licencia prohibida",
              meta["isPrivate"] is True
              and meta["licenses"][0]["name"].lower() not in FORBIDDEN_LICENSE_NAMES)
        stage = stage_bundle(idx, out2, identity)
        check("T7d staging copia los 2 elegibles con sha256 identico", len(stage["staged"]) == 2)
        sheet = (out2 / "files.sha256").read_text().strip().splitlines()
        check("T7e files.sha256 lista los 2 archivos", len(sheet) == 2, sheet[0][:20] + "...")
        check("T7f README trae la restriccion de uso", "RESTRICCION DE USO" in build_readme(idx))

        # T8 - carpeta faltante -> FAIL_LAYOUT (el v1 hacia continue)
        base3 = tmp / "nt8_missing"
        make_tree(base3, specs_clean)
        shutil.rmtree(base3 / ASSET_FOLDERS["GC"])
        idx = build_index(base=base3, out_dir=tmp / "o3", dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(specs_clean))
        check("T8 carpeta ausente -> FAIL_LAYOUT + cuarentena",
              idx["verdict"] == "FAIL_LAYOUT"
              and any(q["kind"] == "MISSING_FOLDER" for q in idx["quarantine"]), idx["verdict"])

        # T9 - footer ilegible y stats ausentes -> FAIL_INTEGRITY
        broken = dict(specs_clean)
        broken["6E_06-26_ticks.parquet"] = dict(broken["6E_06-26_ticks.parquet"], raise_=True)
        broken["6E_06-26_ticks.parquet"]["raise"] = True
        idx = build_index(base=base2, out_dir=tmp / "o4", dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(broken))
        check("T9 footer ilegible -> FAIL_INTEGRITY",
              idx["verdict"] == "FAIL_INTEGRITY"
              and any(q["kind"] == "CENSUS_ERROR" for q in idx["quarantine"]), idx["verdict"])
        nostats = dict(specs_clean)
        nostats["6E_06-26_ticks.parquet"] = dict(nostats["6E_06-26_ticks.parquet"], stats=False)
        idx = build_index(base=base2, out_dir=tmp / "o5", dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(nostats))
        check("T9b sin min/max no se puede certificar -> FAIL_INTEGRITY",
              idx["verdict"] == "FAIL_INTEGRITY"
              and any(q["kind"] == "UNCERTIFIABLE" for q in idx["quarantine"]), idx["verdict"])

        # T10 - presupuesto: 12 GiB -> ABSTAIN_CAPACITY
        heavy = {k: dict(v, bytes=6 << 30) for k, v in specs_clean.items()}
        idx = build_index(base=base2, out_dir=tmp / "o6", dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(heavy))
        check("T10 12 GiB de input -> ABSTAIN_CAPACITY", idx["verdict"] == "ABSTAIN_CAPACITY", idx["verdict"])

        # T11 - auxiliares excluidos por regla, no en silencio
        (base2 / ASSET_FOLDERS["ES"] / "ES_all_ticks.parquet").write_bytes(b"PAR1aux")
        (base2 / ASSET_FOLDERS["ES"] / "ES_prev_ticks.parquet").write_bytes(b"PAR1aux")
        idx = build_index(base=base2, out_dir=tmp / "o7", dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(specs_clean))
        check("T11 los auxiliares quedan listados con su regla",
              len(idx["excluded_by_rule"]) == 2
              and all("auxiliar" in e["rule"] for e in idx["excluded_by_rule"]),
              str(len(idx["excluded_by_rule"])))
        check("T11b y no rompen el PASS", idx["verdict"] == "PASS", idx["verdict"])

        # T12 - nombre no parseable -> cuarentena (nunca ignorado)
        (base2 / ASSET_FOLDERS["ES"] / "ES-06-26.parquet").write_bytes(b"PAR1")
        idx = build_index(base=base2, out_dir=tmp / "o8", dataset_id="u/s",
                          license_doc=lic_ok, mods=mods, census_fn=_fake_census(specs_clean))
        check("T12 nombre invalido -> FAIL_INTEGRITY",
              idx["verdict"] == "FAIL_INTEGRITY"
              and any(q["kind"] == "FILENAME_UNPARSEABLE" for q in idx["quarantine"]), idx["verdict"])

    print()
    print(f"self-test: {len(fails)} fallas")
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--license-doc", type=Path, default=DEFAULT_LICENSE_DOC)
    ap.add_argument("--dataset-id", default=None, help="slug user/dataset (sin default)")
    ap.add_argument("--stage", action="store_true", help="copiar/enlazar los elegibles a --out")
    ap.add_argument("--emit-metadata", action="store_true")
    ap.add_argument("--no-hardlink", action="store_true")
    ap.add_argument("--no-hash", action="store_true", help="solo para diagnostico; nunca para publicar")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    mods = load_repo_modules(REPO_ROOT)
    index = build_index(
        base=args.base,
        out_dir=args.out,
        dataset_id=args.dataset_id,
        license_doc=args.license_doc,
        mods=mods,
        hash_files=not args.no_hash,
    )

    args.out.mkdir(parents=True, exist_ok=True)
    idx_path = args.out / "bundle_index.json"
    mods.identity.write_json(str(idx_path), index)  # auditoria: siempre

    print(f"[{index['verdict']}] {index['summary'].get('files_ok', 0)} archivos elegibles, "
          f"{index['summary'].get('total_rows', 0):,} filas, {index['summary'].get('total_gib', 0)} GiB")
    for g in index["gates"]:
        print(f"  {'PASS' if g['pass'] else 'FAIL'}  {g['gate']}: {g['rule']}")
    for q in index["quarantine"]:
        print(f"  CUARENTENA {q['kind']}: {q['path']} :: {q['detail']}")
    for e in index["excluded_by_rule"]:
        print(f"  EXCLUIDO {e['path']} :: {e['rule']}")
    print(f"  indice: {idx_path} (index_sha256={index['index_sha256'][:16]}...)")

    if index["verdict"] != "PASS":
        if args.stage or args.emit_metadata:
            print("  staging y metadata NO emitidos: el veredicto no es PASS")
        return verdict_exit_code(index["verdict"])

    if args.stage:
        st = stage_bundle(index, args.out, mods.identity, prefer_hardlink=not args.no_hardlink)
        print(f"  staged {len(st['staged'])} archivos + files.sha256")
    if args.emit_metadata:
        if not args.dataset_id:
            raise SystemExit("ABORT: --emit-metadata requiere --dataset-id explicito")
        meta = build_metadata(index, args.dataset_id)
        mods.identity.write_json(str(args.out / "dataset-metadata.json"), meta)
        (args.out / "README.md").write_text(build_readme(index), encoding="utf-8")
        print(f"  dataset-metadata.json emitido (isPrivate=True, licencia "
              f"{meta['licenses'][0]['name']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
