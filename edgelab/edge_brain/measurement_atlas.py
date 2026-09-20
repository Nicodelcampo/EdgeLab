from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema_validator import validate_record


class AtlasValidationError(ValueError):
    """Raised when an indicator, composition contract or atlas catalog violates constraints."""


ALLOWED_ROLES = frozenset({
    "FILTER",
    "TRIGGER",
    "REGIME_GATE",
    "BASELINE",
    "NORMALIZER",
    "MEASUREMENT_CONCEPT",
})


def validate_indicator(indicator: dict[str, Any]) -> None:
    validate_record("indicator_definition", indicator)
    role = indicator.get("role")
    if role not in ALLOWED_ROLES:
        raise AtlasValidationError(f"Invalid indicator role: {role}")
    if indicator.get("status") in {"DRAFT", "PROPOSED"} and indicator.get("asserts_edge") is True:
        raise AtlasValidationError(
            f"Indicator {indicator.get('indicator_id')} asserts edge while in DRAFT/PROPOSED state"
        )
    if not indicator.get("ablations"):
        raise AtlasValidationError(f"Indicator {indicator.get('indicator_id')} must declare ablations")
    if not indicator.get("failure_modes"):
        raise AtlasValidationError(f"Indicator {indicator.get('indicator_id')} must declare failure modes")


def validate_composition(
    composition: dict[str, Any],
    known_indicators: set[str] | None = None,
) -> None:
    validate_record("composition_contract", composition)
    components = composition.get("components", [])
    if len(components) < 2:
        raise AtlasValidationError("Composition contract requires at least two distinct components")
    if known_indicators is not None:
        for comp in components:
            if comp not in known_indicators:
                raise AtlasValidationError(
                    f"Composition {composition.get('composition_id')} references undefined component: {comp}"
                )
    if composition.get("status") in {"DRAFT", "PROPOSED"} and composition.get("asserts_edge") is True:
        raise AtlasValidationError(
            f"Composition {composition.get('composition_id')} asserts edge while in DRAFT/PROPOSED state"
        )
    if not composition.get("ablations"):
        raise AtlasValidationError(
            f"Composition {composition.get('composition_id')} must declare ablations"
        )


def validate_atlas(atlas_data_or_path: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Validate a complete measurement atlas seed or catalog against all structural gates."""
    if isinstance(atlas_data_or_path, (str, Path)):
        path = Path(atlas_data_or_path)
        if not path.is_file():
            raise FileNotFoundError(f"Atlas file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = atlas_data_or_path

    catalog = data.get("catalog")
    if not catalog:
        raise AtlasValidationError("Missing top-level 'catalog' object in atlas")
    validate_record("measurement_atlas_catalog", catalog)

    if catalog.get("status") in {"DRAFT", "PROPOSED"} and catalog.get("asserts_edge") is True:
        raise AtlasValidationError("Atlas catalog asserts edge while in DRAFT/PROPOSED state")

    indicators = data.get("indicators", [])
    compositions = data.get("compositions", [])
    concepts = data.get("concepts", [])

    known_indicators: set[str] = set()
    for ind in indicators:
        validate_indicator(ind)
        ind_id = ind["indicator_id"]
        if ind_id in known_indicators:
            raise AtlasValidationError(f"Duplicate indicator_id in atlas: {ind_id}")
        known_indicators.add(ind_id)

    known_concepts: set[str] = set()
    for conc in concepts:
        concept_id = conc.get("concept_id") or conc.get("indicator_id")
        if not concept_id:
            raise AtlasValidationError("Concept must have concept_id or indicator_id")
        conc_dict = dict(conc)
        if "indicator_id" not in conc_dict:
            conc_dict["indicator_id"] = f"IND-{concept_id}"
        validate_indicator(conc_dict)
        known_concepts.add(concept_id)

    all_components = known_indicators | known_concepts

    for comp in compositions:
        validate_composition(comp, known_indicators=all_components)

    # Cross-reference catalog listings
    for ind_id in catalog.get("indicator_ids", []):
        if ind_id not in known_indicators:
            raise AtlasValidationError(f"Catalog references undeclared indicator: {ind_id}")

    for comp_id in catalog.get("composition_ids", []):
        comp_ids_in_doc = {c["composition_id"] for c in compositions}
        if comp_id not in comp_ids_in_doc:
            raise AtlasValidationError(f"Catalog references undeclared composition: {comp_id}")

    return {
        "valid": True,
        "catalog_id": catalog["catalog_id"],
        "indicators_count": len(indicators),
        "compositions_count": len(compositions),
        "concepts_count": len(concepts),
    }
