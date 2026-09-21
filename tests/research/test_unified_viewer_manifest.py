import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VIEWER=ROOT/"viewer"/"nt8_bridge"
def test_single_canonical_entrypoint_and_feature_states():
    manifest=json.loads((VIEWER/"viewer_manifest.json").read_text(encoding="utf-8")); assert manifest["canonical_entrypoint"]=="viewer/nt8_bridge/index.html"; assert manifest["feature_status"]["hft_liquidity_corridors"]=="NOT_UNIFIED_MULTIPLE_IMPLEMENTATIONS"; assert manifest["feature_status"]["crosshair_density_profile_kernel"]=="INTEGRATED_DUPLICATES_ENGINE_MATH"; assert manifest["feature_status"]["local_volume_profile_ui"]=="INTEGRATED_FROM_WORKTREE_2026-09-21"; assert manifest["production_rule"].startswith("Do not create another")
def test_canonical_shell_contains_corridors_25t_and_causal_availability():
    html=(VIEWER/"index.html").read_text(encoding="utf-8"); assert "Corredores de Vacío HFT" in html; assert 'value="tick_25"' in html; assert "available_ts" in html
def test_required_feature_files_exist():
    for relative in ["corridor_engine.js","crosshair_density_profile.js","index.html","viewer_manifest.json"]: assert (VIEWER/relative).is_file(),relative
    assert (ROOT/"tools"/"build_multiasset_25t_hft_bundles.py").is_file()


def test_corridor_definition_is_declared_pending_not_silently_integrated():
    """El manifiesto no puede afirmar INTEGRATED mientras haya mas de una implementacion."""
    manifest=json.loads((VIEWER/"viewer_manifest.json").read_text(encoding="utf-8"))
    cd=manifest["corridor_definition"]
    assert cd["status"]=="DECISION_PENDING"
    assert len(cd["implementations_found"])>=3
    assert "corridor_engine.js" in cd["implementations_found"]
    assert "edgelab/research/density_field.py" in cd["implementations_found"]
