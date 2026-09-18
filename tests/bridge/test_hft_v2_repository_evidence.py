from tools.verify_hft_v2_repository_evidence import verify


def test_committed_hft_v2_certification_evidence_is_self_consistent():
    result = verify()
    assert result["is_pass"], result["errors"]
    assert result["status"] == "PASS_REPOSITORY_EVIDENCE_CONSISTENCY"
    assert result["scope"] == "COMMITTED_EVIDENCE_ONLY_LOCAL_SQLITE_BYTES_NOT_PRESENT_IN_GIT"
