# -*- coding: utf-8 -*-
import pytest

from edgelab.research.zamr1.upload_gate import (
    UploadNotAuthorized,
    require_raw_third_party_upload,
)


def test_no_upload_rechaza_ticks_a_terceros():
    with pytest.raises(UploadNotAuthorized, match="RAW_UPLOAD_NOT_AUTHORIZED"):
        require_raw_third_party_upload({
            "license_decision": "NO_UPLOAD",
            "operational_override": "USER_RISK_ACCEPTANCE_NOT_LICENSE_PERMISSION",
            "holdout_included": False,
        })


def test_derived_only_tampoco_autoriza_ticks_crudos():
    with pytest.raises(UploadNotAuthorized):
        require_raw_third_party_upload({
            "license_decision": "DERIVED_ONLY",
            "holdout_included": False,
        })


def test_raw_allowed_requiere_holdout_ausente():
    with pytest.raises(UploadNotAuthorized, match="holdout"):
        require_raw_third_party_upload({"license_decision": "RAW_ALLOWED"})
    require_raw_third_party_upload({
        "license_decision": "RAW_ALLOWED",
        "holdout_included": False,
    })
