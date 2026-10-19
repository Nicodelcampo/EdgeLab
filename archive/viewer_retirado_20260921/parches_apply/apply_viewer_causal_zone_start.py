#!/usr/bin/env python3
"""Make zone rendering start at causal availability and enforce bar identity."""
from __future__ import annotations
import argparse
from pathlib import Path
HELPER='''
  function zoneAvailableSec(z) {
    var raw = (z.available_ts !== undefined && z.available_ts !== null)
      ? z.available_ts
      : ((z.available_ns !== undefined && z.available_ns !== null)
        ? z.available_ns
        : ((z.availableTime !== undefined && z.availableTime !== null) ? z.availableTime : null));
    // Sólo los overlays legacy LuxAlgo pueden conservar t0. Las zonas
    // científicas sin timestamp de disponibilidad se ocultan fail-closed.
    if (raw === null || raw === undefined) {
      if (z.source === "luxalgo" && Number.isFinite(Number(z.t0))) return Number(z.t0);
      return null;
    }
    raw = Number(raw);
    if (!Number.isFinite(raw)) return null;
    if (raw > 1e16) raw = raw / 1e9;
    else if (raw > 1e11) raw = raw / 1e3;
    return raw;
  }
'''
def replace_once(text:str,old:str,new:str,label:str)->str:
 count=text.count(old)
 if count!=1:raise RuntimeError(f'{label}: expected exactly one match, found {count}')
 return text.replace(old,new,1)
def apply(path:Path)->str:
 text=path.read_text(encoding='utf-8')
 if 'ABSTAIN_BAR_KEY_MISMATCH' in text and 'zoneAvailableSec' in text:return 'ALREADY_APPLIED'
 text=replace_once(text,'  function drawZones() {',HELPER+'\n  function drawZones() {','availability helper')
 start=text.index('  function drawZones() {');end=text.index('\n  function drawCorredoresDemo',start);before,body,after=text[:start],text[start:end],text[end:]
 body=replace_once(body,'''    var nCandles = candles ? candles.length : 0;
    var avgSecPerBar = (nCandles > 1) ? (candles[nCandles - 1].time - candles[0].time) / (nCandles - 1) : 60;
''','''    var nCandles = candles ? candles.length : 0;
    var avgSecPerBar = (nCandles > 1) ? (candles[nCandles - 1].time - candles[0].time) / (nCandles - 1) : 60;

    // Una corrida sólo puede dibujarse sobre su serie primaria.
    var runBarKey = state.run && state.run.bar_key;
    if (runBarKey && runBarKey !== activeKey) {
      window.__EDGELAB_ZONE_RENDER_STATUS__ = {status: "ABSTAIN_BAR_KEY_MISMATCH", runBarKey: runBarKey, activeBarKey: activeKey};
      ctx.save();
      ctx.fillStyle = "rgba(220,38,38,0.95)";
      ctx.font = "bold 12px 'Segoe UI', -apple-system, sans-serif";
      ctx.fillText("ZONAS OCULTAS: run " + runBarKey + " ≠ gráfico " + activeKey, 12, 22);
      ctx.restore();
      return;
    }
    window.__EDGELAB_ZONE_RENDER_STATUS__ = {status: "PASS", runBarKey: runBarKey || null, activeBarKey: activeKey};
''','bar-key guard')
 body=replace_once(body,'''      if (!visible(z)) return;

      var zBot''','''      if (!visible(z)) return;

      // Inicio causal: disponibilidad efectiva, nunca origen retrospectivo.
      var zoneStartTs = zoneAvailableSec(z);
      if (zoneStartTs === null) return;

      var zBot''','causal start')
 for old,new,label in [
  ('if (z.t0 > vr.to) return;','if (zoneStartTs > vr.to) return;','early culling'),
  ('var t1_eff = z.t1 || (z.t0 + 5400);','var t1_eff = Math.max(zoneStartTs, z.t1 || (zoneStartTs + 5400));','effective end'),
  ('candles[z.start_bar_idx].time === z.t0','candles[z.start_bar_idx].time === zoneStartTs','cached start'),
  ('if (candles[mid].time < z.t0) low = mid + 1;','if (candles[mid].time < zoneStartTs) low = mid + 1;','binary start'),
  ('maxT1 = z.t0 + 600;','maxT1 = zoneStartTs + 600;','fallback end'),
  ('if (t1_eff < vr.from || z.t0 > vr.to) return;','if (t1_eff < vr.from || zoneStartTs > vr.to) return;','fixed culling')]:
  body=replace_once(body,old,new,label)
 count=body.count('var x0 = timeToX(z.t0, i0);')
 if count!=2:raise RuntimeError(f'zone x0 anchors: expected exactly two matches, found {count}')
 body=body.replace('var x0 = timeToX(z.t0, i0);','var x0 = timeToX(zoneStartTs, i0);')
 path.write_text(before+body+after,encoding='utf-8');return 'APPLIED'
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--viewer',type=Path,default=Path('viewer/nt8_bridge/index.html'));a=p.parse_args();print(apply(a.viewer));return 0
if __name__=='__main__':raise SystemExit(main())
