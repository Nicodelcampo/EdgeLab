#!/usr/bin/env python3
"""Idempotently add a causal crosshair density profile to the EdgeLab viewer."""
from __future__ import annotations
import argparse
from pathlib import Path
MARKER = "EDGELAB_CROSSHAIR_DENSITY_PROFILE_V1"

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def apply(path):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return "ALREADY_APPLIED"
    text = replace_once(text, '<script src="data.js"></script>\n<script>', '<script src="data.js"></script>\n<script src="crosshair_density_profile.js"></script>\n<script>', "density module script")
    old = '''        <div style="font-size: 9.5px; color: #666; line-height: 1.3;">
          ✓ Delimitación estricta entre murallas vivas. Sin franjas infinitas ni micro-ruido.
        </div>'''
    new = '''        <!-- EDGELAB_CROSSHAIR_DENSITY_PROFILE_V1 -->
        <label style="display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:11px;cursor:pointer;border-top:1px solid var(--tb-border);padding-top:7px;">
          <span><b>Perfil de densidad</b><br><span style="font-size:9.5px;color:#666;">As-of causal de la crosshair</span></span>
          <input type="checkbox" id="chk-corridors-density-profile">
        </label>
        <div style="display:flex;align-items:center;gap:8px;">
          <label style="font-size:10px;color:#666;">Ancho</label>
          <input type="range" id="range-corridors-density-width" min="60" max="180" step="10" value="110" style="flex:1;accent-color:#0891b2;">
          <span id="lbl-corridors-density-width" style="font-size:10px;font-weight:700;color:#0891b2;min-width:38px;text-align:right;">110 px</span>
        </div>
        <div style="font-size: 9.5px; color: #666; line-height: 1.3;">
          ✓ Delimitación estricta entre murallas vivas. Sin franjas infinitas ni micro-ruido.
        </div>'''
    text = replace_once(text, old, new, "corridor controls")
    text = replace_once(text, '    corridors_dir_filter: "all", // "all", "bull", "bear"\n', '    corridors_dir_filter: "all", // "all", "bull", "bear"\n    corridors_density_profile: false,\n    corridors_density_width: 110,\n    corridors_density_sigma_ticks: 2,\n', "activeProps")
    anchor = '  function drawCorredoresDemo(ctx, w, hCanvas) {'
    renderer = r'''  function densityTsSec(raw) {
    if (raw === undefined || raw === null) return null;
    var value = Number(raw);
    if (!Number.isFinite(value)) return null;
    if (value > 1e16) value /= 1e9;
    else if (value > 1e11) value /= 1e3;
    return value;
  }
  function buildCrosshairDensityRanges(candles, tRef, tick, extBars, activeKey) {
    var ranges = [], zones = (state.run && state.run.zones) || [], nCandles = candles.length;
    var avgSecPerBar = nCandles > 1 ? (candles[nCandles-1].time-candles[0].time)/(nCandles-1) : 60;
    var isVolMode = activeProps.consumption_mode === "volume";
    for (var i=0;i<zones.length;i++) {
      var z=zones[i]; if (!visible(z)) continue;
      var available=densityTsSec(z.available_ts!==undefined?z.available_ts:(z.available_ns!==undefined?z.available_ns:z.availableTime));
      if (available===null || available>tRef) continue;
      var bottom=Math.min(Number(z.bottom),Number(z.top)), top=Math.max(Number(z.bottom),Number(z.top));
      if (!Number.isFinite(bottom)||!Number.isFinite(top)) continue;
      var weight=Math.max(1,Number(z.vol)||1);
      if (state.decayMode==="calibrated_time") { var age=Math.max(0,(tRef-available)/3600); if(age>48)continue; weight*=Math.pow(.5,age/12); }
      var cache=z._consCache;
      if(isVolMode&&cache&&cache.barKey===activeKey&&cache.slices){
        for(var si=0;si<cache.slices.length;si++){var s=cache.slices[si];var death=s.deathBar>=0&&s.deathBar<nCandles?candles[s.deathBar].time:null;if(death!==null&&death<=tRef)continue;ranges.push({lo:bottom+s.startK*tick-(s.startK===0?0:tick*.5),hi:bottom+s.endK*tick+(s.endK===cache.nTicks-1?0:tick*.5),weight:weight});}
        continue;
      }
      var ended=densityTsSec(z.t1); if(ended===null)ended=available+Math.max(1,extBars)*avgSecPerBar;if(ended<tRef)continue;
      ranges.push({lo:bottom,hi:top,weight:weight});
    }
    return ranges;
  }
  function drawCrosshairDensityProfile(ctx,w,hCanvas,candles,tick,extBars,activeKey){
    if(activeProps.corridors_density_profile!==true){window.__EDGELAB_DENSITY_PROFILE_STATUS__={status:"DISABLED"};return;}
    if(!state.hoverTime){window.__EDGELAB_DENSITY_PROFILE_STATUS__={status:"ABSTAIN_NO_CROSSHAIR"};return;}
    if(!window.EdgeLabCrosshairDensity){window.__EDGELAB_DENSITY_PROFILE_STATUS__={status:"ABSTAIN_ENGINE_UNAVAILABLE"};return;}
    var tRef=densityTsSec(state.hoverTime),pTop=series.coordinateToPrice(0),pBottom=series.coordinateToPrice(hCanvas);
    if(tRef===null||pTop===null||pBottom===null){window.__EDGELAB_DENSITY_PROFILE_STATUS__={status:"ABSTAIN_INVALID_DOMAIN"};return;}
    var profile;
    try{profile=window.EdgeLabCrosshairDensity.build({ranges:buildCrosshairDensityRanges(candles,tRef,tick,extBars,activeKey),tickSize:tick,minPrice:Math.min(pTop,pBottom),maxPrice:Math.max(pTop,pBottom),sigmaTicks:activeProps.corridors_density_sigma_ticks||2,maxBins:5000});}
    catch(error){window.__EDGELAB_DENSITY_PROFILE_STATUS__={status:"ABSTAIN_PROFILE_ERROR",message:String(error&&error.message?error.message:error)};return;}
    var tsc=chart.timeScale(),chartW=tsc&&typeof tsc.width==="function"&&tsc.width()>0?tsc.width():w-65,width=Math.max(60,Math.min(180,Number(activeProps.corridors_density_width)||110)),rightX=chartW-2,leftX=rightX-width;
    ctx.save();ctx.fillStyle=state.isDark?"rgba(15,23,42,.76)":"rgba(248,250,252,.80)";ctx.fillRect(leftX,0,width,hCanvas);ctx.strokeStyle=state.isDark?"rgba(34,211,238,.45)":"rgba(8,145,178,.45)";ctx.beginPath();ctx.moveTo(leftX+.5,0);ctx.lineTo(leftX+.5,hCanvas);ctx.stroke();
    if(profile.maxDensity>0)for(var bi=0;bi<profile.density.length;bi++){var value=profile.density[bi];if(!(value>0))continue;var price=(profile.loTick+bi)*tick,y=series.priceToCoordinate(price);if(y===null||y< -2||y>hCanvas+2)continue;var ratio=value/profile.maxDensity,barW=Math.max(1,ratio*(width-8)),nextY=series.priceToCoordinate(price+tick),barH=nextY===null?2:Math.max(1,Math.abs(nextY-y));ctx.fillStyle="rgba(8,145,178,"+(0.18+ratio*.62).toFixed(3)+")";ctx.fillRect(rightX-barW,y-barH/2,barW,barH);}
    var label=new Date(tRef*1000).toISOString().slice(11,19);ctx.font="bold 9px 'Segoe UI',sans-serif";ctx.fillStyle=state.isDark?"#67e8f9":"#0e7490";ctx.fillText("DENSIDAD @ "+label+" UTC",leftX+5,13);ctx.restore();
    window.__EDGELAB_DENSITY_PROFILE_STATUS__={status:"PASS",asOf:tRef,source:"crosshair",contributingRanges:profile.contributingRanges,bins:profile.density.length,maxDensity:profile.maxDensity,decayMode:state.decayMode,activeBarKey:activeKey};
  }

  function drawCorredoresDemo(ctx, w, hCanvas) {'''
    text = replace_once(text, anchor, renderer, "renderer")
    text = replace_once(text, '    if (livingWalls.length < 2) return;\n', '    if (livingWalls.length < 2) { drawCrosshairDensityProfile(ctx,w,hCanvas,candles,tick,extBars,activeKey); return; }\n', "walls return")
    text = replace_once(text, '    if (clusters.length < 2) return;\n', '    if (clusters.length < 2) { drawCrosshairDensityProfile(ctx,w,hCanvas,candles,tick,extBars,activeKey); return; }\n', "clusters return")
    text = replace_once(text, '    // Actualizar botón de la barra de herramientas con el número de corredores activos\n', '    drawCrosshairDensityProfile(ctx,w,hCanvas,candles,tick,extBars,activeKey);\n\n    // Actualizar botón de la barra de herramientas con el número de corredores activos\n', "final draw")
    sync='    if (wrapCorr) wrapCorr.style.opacity = corrEnabled ? "1" : "0.45";\n\n    var hMinVal'
    repl='    if (wrapCorr) wrapCorr.style.opacity = corrEnabled ? "1" : "0.45";\n    var chkDensity=document.getElementById("chk-corridors-density-profile"),rangeDensityWidth=document.getElementById("range-corridors-density-width"),lblDensityWidth=document.getElementById("lbl-corridors-density-width");\n    if(chkDensity)chkDensity.checked=activeProps.corridors_density_profile===true;\n    if(rangeDensityWidth)rangeDensityWidth.value=activeProps.corridors_density_width||110;\n    if(lblDensityWidth)lblDensityWidth.textContent=(activeProps.corridors_density_width||110)+" px";\n\n    var hMinVal'
    text=replace_once(text,sync,repl,"sync")
    listeners='''  var chkCorrDensity=document.getElementById("chk-corridors-density-profile");
  if(chkCorrDensity)chkCorrDensity.addEventListener("change",function(){activeProps.corridors_density_profile=this.checked;requestDraw();});
  var rangeCorrDensityWidth=document.getElementById("range-corridors-density-width");
  if(rangeCorrDensityWidth)rangeCorrDensityWidth.addEventListener("input",function(){activeProps.corridors_density_width=parseInt(this.value,10)||110;var l=document.getElementById("lbl-corridors-density-width");if(l)l.textContent=activeProps.corridors_density_width+" px";requestDraw();});

  function buildStateFilters() {'''
    text=replace_once(text,'  function buildStateFilters() {',listeners,"listeners")
    path.write_text(text,encoding="utf-8")
    return "APPLIED"

def main():
    p=argparse.ArgumentParser();p.add_argument("path",nargs="?",default="viewer/nt8_bridge/index.html");a=p.parse_args();print(apply(Path(a.path)))
if __name__=="__main__":main()
