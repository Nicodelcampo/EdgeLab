import os
import json
import jsonschema

SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "schemas", "edge_factory"))

_SCHEMAS = {}

def get_schema(schema_name: str) -> dict:
    if schema_name not in _SCHEMAS:
        path = os.path.join(SCHEMA_DIR, f"{schema_name}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Schema file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            _SCHEMAS[schema_name] = json.load(f)
    return _SCHEMAS[schema_name]

def validate_zone_event(data: dict) -> None:
    """Validates a causal zone event against zone_events schema.
    Strictly forbids ORIGIN_FALLBACK_UNVERIFIED from causal storage.
    """
    if data.get("availability_quality") == "ORIGIN_FALLBACK_UNVERIFIED":
        raise ValueError("ORIGIN_FALLBACK_UNVERIFIED is forbidden in causal zone_events. Use zone_events_exploratory.")
    schema = get_schema("zone_events")
    jsonschema.validate(instance=data, schema=schema)

def validate_zone_event_exploratory(data: dict) -> None:
    schema = get_schema("zone_events_exploratory")
    jsonschema.validate(instance=data, schema=schema)

def validate_corridor_event(data: dict) -> None:
    schema = get_schema("corridor_events")
    jsonschema.validate(instance=data, schema=schema)

def validate_hypothesis(data: dict) -> None:
    schema = get_schema("hypothesis_registry")
    jsonschema.validate(instance=data, schema=schema)

def validate_experiment(data: dict) -> None:
    schema = get_schema("experiment_registry")
    jsonschema.validate(instance=data, schema=schema)

def validate_negative_result(data: dict) -> None:
    schema = get_schema("negative_results_registry")
    jsonschema.validate(instance=data, schema=schema)

def validate_analysis_dependencies(data: dict) -> None:
    schema = get_schema("analysis_dependencies")
    jsonschema.validate(instance=data, schema=schema)
