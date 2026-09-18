import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/'tools'/'apply_viewer_causal_zone_start.py'
spec=importlib.util.spec_from_file_location('causal_zone_start',MODULE);patcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(patcher)
def test_patch_anchors_zones_to_availability_and_blocks_tf_mismatch(tmp_path):
 source=(ROOT/'viewer'/'nt8_bridge'/'index.html').read_text(encoding='utf-8');path=tmp_path/'index.html';path.write_text(source,encoding='utf-8');assert patcher.apply(path)=='APPLIED';updated=path.read_text(encoding='utf-8');assert 'ABSTAIN_BAR_KEY_MISMATCH' in updated;assert 'var zoneStartTs = zoneAvailableSec(z);' in updated;assert 'var x0 = timeToX(z.t0, i0);' not in updated;assert updated.count('var x0 = timeToX(zoneStartTs, i0);')==2;assert 'candles[z.start_bar_idx].time === zoneStartTs' in updated;assert 'if (candles[mid].time < zoneStartTs)' in updated;assert patcher.apply(path)=='ALREADY_APPLIED'
def test_scientific_zones_have_no_t0_fallback(tmp_path):
 source=(ROOT/'viewer'/'nt8_bridge'/'index.html').read_text(encoding='utf-8');path=tmp_path/'index.html';path.write_text(source,encoding='utf-8');patcher.apply(path);updated=path.read_text(encoding='utf-8');helper=updated[updated.index('function zoneAvailableSec'):updated.index('function drawZones')];assert 'z.source === "luxalgo"' in helper;assert 'return null;' in helper;assert 'z.t0' not in helper.replace('z.source === "luxalgo" && Number.isFinite(Number(z.t0))) return Number(z.t0);','')
