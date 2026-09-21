import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VIEWER=ROOT/"viewer"/"nt8_bridge"
def test_single_canonical_entrypoint_and_feature_states():
    manifest=json.loads((VIEWER/"viewer_manifest.json").read_text(encoding="utf-8")); assert manifest["canonical_entrypoint"]=="viewer/nt8_bridge/index.html"; assert manifest["feature_status"]["hft_liquidity_corridors"]=="UNIFIED_HP007_DENSITY_FIELD"; assert manifest["feature_status"]["crosshair_density_profile_kernel"]=="UNIFIED_SAME_FIELD_AS_CORRIDORS"; assert manifest["feature_status"]["local_volume_profile_ui"]=="INTEGRATED_FROM_WORKTREE_2026-09-21"; assert manifest["production_rule"].startswith("Do not create another")
def test_canonical_shell_contains_corridors_25t_and_causal_availability():
    html=(VIEWER/"index.html").read_text(encoding="utf-8"); assert "Corredores de Vacío HFT" in html; assert 'value="tick_25"' in html; assert "available_ts" in html
def test_required_feature_files_exist():
    for relative in ["density_field.js","index.html","viewer_manifest.json"]: assert (VIEWER/relative).is_file(),relative
    assert (ROOT/"tools"/"build_multiasset_25t_hft_bundles.py").is_file()


def test_corridor_definition_is_decided_and_points_at_the_reference():
    """Una sola definición de corredor; el manifiesto no puede afirmar unificación sin decir cuál."""
    manifest=json.loads((VIEWER/"viewer_manifest.json").read_text(encoding="utf-8"))
    cd=manifest["corridor_definition"]
    assert cd["status"]=="DECIDED_2026-09-21"
    assert "edgelab/research/density_field.py" in cd["decision"]
    assert "density_field.js" in cd["decision"]
    assert "directional characterization BULL/BEAR/DUAL (corridor_geometry.py)" in cd["not_certified"]
    for muerto in ["corridor_engine.js", "crosshair_density_profile.js", "hft_corridor_preview.html"]:
        assert muerto in cd["superseded"]
        assert not (VIEWER/muerto).exists(), muerto     # y efectivamente ya no están en el visor


def test_no_hay_paginas_competidoras_en_el_visor():
    html = sorted(p.name for p in VIEWER.glob("*.html"))
    assert html == ["index.html", "index_invariant.html", "store_viewer.html"], html
