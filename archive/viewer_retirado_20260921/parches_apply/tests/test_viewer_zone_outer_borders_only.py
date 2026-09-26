import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/'tools'/'apply_viewer_zone_outer_borders_only.py'
spec=importlib.util.spec_from_file_location('outer_borders',MODULE);patcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(patcher)
def test_patch_removes_slice_stroke_rect_and_is_idempotent(tmp_path):
    path = tmp_path / 'index.html'
    path.write_text(patcher.OLD, encoding='utf-8')
    assert patcher.apply(path) == 'APPLIED'
    updated = path.read_text(encoding='utf-8')
    assert 'ctx.strokeRect(drawX0 + 0.5, yMin_s + 0.5, rw_s, h_s);' not in updated
    assert 'isBottomOuterSlice' in updated
    assert 'isTopOuterSlice' in updated
    assert patcher.apply(path) == 'ALREADY_APPLIED'
    live_path = tmp_path / 'live.html'
    live_path.write_text((ROOT / 'viewer' / 'nt8_bridge' / 'index.html').read_text(encoding='utf-8'), encoding='utf-8')
    assert patcher.apply(live_path) in ('APPLIED', 'ALREADY_APPLIED')
