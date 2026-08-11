"""Infraestructura de research multiframe (BigTrap2 tickframes + ML).

Este paquete contiene sólo validación fail-closed del contrato de datos.
No entrena modelos, no lee outcomes y no abre el holdout.
"""

from .dataset_contract import (  # noqa: F401
    CONTRACT_SCHEMA_VERSION,
    ValidationReport,
    check_causality,
    check_firewall,
    check_fold_roles,
    check_null_window_fraction,
    check_primary_key_unique,
    check_required_columns,
    check_target_leakage_columns,
    validate_all,
)
