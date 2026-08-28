# -*- coding: utf-8 -*-
"""Gate legal fail-closed para transferencias ZAMR-1 a terceros."""
from __future__ import annotations


class UploadNotAuthorized(RuntimeError):
    pass


def require_raw_third_party_upload(plan: dict) -> None:
    """Autoriza ticks crudos sólo con decisión contractual RAW_ALLOWED.

    Un override operativo o aceptación de riesgo no reemplaza el permiso de
    licencia. NO_UPLOAD y DERIVED_ONLY rechazan siempre la carga de ticks.
    """
    decision = plan.get("license_decision")
    if decision != "RAW_ALLOWED":
        raise UploadNotAuthorized(
            "RAW_UPLOAD_NOT_AUTHORIZED: license_decision=%r; "
            "un operational_override no constituye permiso contractual" % decision
        )
    if plan.get("holdout_included") is not False:
        raise UploadNotAuthorized("RAW_UPLOAD_NOT_AUTHORIZED: holdout no está explícitamente ausente")
