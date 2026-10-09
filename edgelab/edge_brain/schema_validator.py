from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "edge_brain"
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def get_schema(schema_name: str) -> dict[str, Any]:
    if schema_name not in _SCHEMA_CACHE:
        path = SCHEMA_DIR / f"{schema_name}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Schema file not found: {path}")
        _SCHEMA_CACHE[schema_name] = json.loads(path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[schema_name]


def validate_record(schema_name: str, data: dict[str, Any]) -> None:
    """Validate one brain record without mutating or promoting it."""
    jsonschema.validate(instance=data, schema=get_schema(schema_name))
