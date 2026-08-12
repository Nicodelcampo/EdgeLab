"""ZAMR-1: infraestructura target-free para el atlas multiresolución.

Este paquete valida contratos y espacios paramétricos. No calcula outcomes,
no lee retornos, no abre P&L y no toca el holdout.
"""

from .parameter_dag import (  # noqa: F401
    ParamIssue,
    canonical_param_set,
    param_set_id,
    validate_param_set,
    validate_single_family,
)
from .structural_contract import (  # noqa: F401
    CheckResult,
    ValidationReport,
    validate_structural_dataset,
)
