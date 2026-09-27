/* EspejoImpulsos (ESPEJO-IND) — port JS de edgelab/bridge/indicators/espejo_impulsos.py.
 * Misma lógica, mismos eventos; la paridad la verifica tests/research/test_espejo_impulsos_js.py.
 * Target-free y causal: cada evento se conoce al cierre de su `bar`. Precios en ticks. */
(function (root) {
  "use strict";
  var DEF = { max_bars: 20, min_w: 17, atr_k: null, atr_n: 14, e_min: 0.3, e_max: 0.6, retr: 0.3, xs: [0.25, 0.5, 0.75],
              horizon_mult: 3, gap_reset_s: 1800, i2_pct: 33.3, ref_min: 30, thin_frac: 0.25, accept_band: 0.25, npts: 20 };
  var FINAL = { MIRROR_COMPLETED: 1, MIRROR_FAILED: 1, MIRROR_EXPIRED: 1, IMP_NO_MIRROR: 1, IMP_UNCONFIRMED: 1 };
  var COMP = ["vel", "efi", "forma", "ondas"];

  function params(o) { var p = {}, k; for (k in DEF) p[k] = DEF[k]; if (o) for (k in o) if (o[k] !== null && o[k] !== undefined) p[k] = o[k]; return p; }
  function percentile(a, q) {                     // numpy.percentile, interpolación lineal
    var s = a.slice().sort(function (x, y) { return x - y; }), pos = (s.length - 1) * q / 100, lo = Math.floor(pos), hi = Math.ceil(pos);
    return s[lo] + (s[hi] - s[lo]) * (pos - lo);
  }
  function atrPrev(H, L, C, n) {
    var N = C.length, cs = new Float64Array(N + 1), out = new Float64Array(N).fill(Infinity);
    for (var i = 0; i < N; i++) { var pc = i ? C[i - 1] : C[0]; cs[i + 1] = cs[i] + Math.max(H[i] - L[i], Math.abs(H[i] - pc), Math.abs(L[i] - pc)); }
    for (var j = n + 1; j < N; j++) out[j] = (cs[j] - cs[j - n]) / n;
    return out;
  }
  function detect(t, H, L, C, V, thr, p, a0, b0) {
    var W = p.max_bars | 0, e0 = p.e_min, r = p.retr, out = [], n = b0 - a0, path = new Float64Array(n);
    for (var i = 1; i < n; i++) path[i] = path[i - 1] + Math.abs(C[a0 + i] - C[a0 + i - 1]);
    var active = false, floorI = 0, d = 0, i0 = 0, a = 0, ext = 0, iext = 0, thrT = 0;
    for (var j = W; j < n; j++) {
      var J = a0 + j;
      if (t[J] - t[J - 1] > p.gap_reset_s) active = false;
      if (!active) {
        var w0 = Math.max(j - W, floorI); if (w0 >= j) continue;
        var th = Math.max(thr[J], 2); if (!(th < 1e17)) continue;
        var ia = w0, ib = w0;
        for (var q = w0; q <= j; q++) { if (L[a0 + q] < L[a0 + ia]) ia = q; if (H[a0 + q] > H[a0 + ib]) ib = q; }
        var found = false, bnet = 0;
        if (ia < j) { var net = C[J] - L[a0 + ia], pp = path[j] - path[ia];
          if (net >= th && pp > 0 && (C[J] - C[a0 + ia]) / pp >= e0) { found = true; bnet = net; d = 1; i0 = ia; a = L[a0 + ia]; ext = H[J]; } }
        if (ib < j) { var net2 = H[a0 + ib] - C[J], pp2 = path[j] - path[ib];
          if (net2 >= th && pp2 > 0 && (C[a0 + ib] - C[J]) / pp2 >= e0 && (!found || net2 > bnet)) { found = true; d = -1; i0 = ib; a = H[a0 + ib]; ext = L[J]; } }
        if (found) { active = true; iext = j; thrT = th; }
        continue;
      }
      if (d === 1 && H[J] > ext) { ext = H[J]; iext = j; } else if (d === -1 && L[J] < ext) { ext = L[J]; iext = j; }
      var tot = Math.abs(ext - a), retr = d === 1 ? ext - L[J] : H[J] - ext;
      var why = retr >= Math.max(2, r * tot) ? 1 : (j - i0 >= W ? 2 : 0);
      if (!why) continue;
      if (tot >= thrT) {
        var ppi = path[iext] - path[i0], vol = 0;
        for (q = i0; q <= iext; q++) vol += V[a0 + q];
        out.push({ d: d, a: a, ext: ext, i0: i0, iext: iext, jconf: j, why: why, eff: ppi > 0 ? Math.abs(C[a0 + iext] - C[a0 + i0]) / ppi : 1, vol: vol });
      }
      floorI = iext; active = false;
    }
    return out;
  }
  function perfil(H, L, V, i0, iext, a, ext, p) {
    var lo = Math.min(a, ext), hi = Math.max(a, ext), nb = Math.max(1, Math.round(hi - lo)), dens = new Float64Array(nb), q, k;
    var edges = new Float64Array(nb + 1); for (k = 0; k <= nb; k++) edges[k] = lo + (hi - lo) * k / nb;
    for (q = i0; q <= iext; q++) {
      var l = Math.max(L[q], lo), h = Math.min(H[q], hi); if (h < l) continue;
      if (h === l) { k = hi > lo ? Math.min(Math.floor((l - lo) / (hi - lo) * nb), nb - 1) : 0; dens[k] += V[q]; continue; }
      for (k = 0; k < nb; k++) { var ov = Math.min(edges[k + 1], h) - Math.max(edges[k], l); if (ov > 0) dens[k] += V[q] * ov / (h - l); }
    }
    var med = percentile(Array.prototype.slice.call(dens), 50), bs = 0, be = -1;
    k = 0;
    while (k < nb) {
      if (med > 0 && dens[k] < p.thin_frac * med) { var s = k; while (k < nb && dens[k] < p.thin_frac * med) k++; if (k - s > be - bs + 1) { bs = s; be = k - 1; } }
      else k++;
    }
    if (be < bs) return [null, null, 0];
    return [edges[bs], edges[be + 1], hi > lo ? (edges[be + 1] - edges[bs]) / (hi - lo) : 0];
  }
  function aceptacion(H, L, V, iext, k, ext, W, d, p) {
    var blo = d === 1 ? ext - p.accept_band * W : ext, bhi = d === 1 ? ext : ext + p.accept_band * W, tot = 0, n = 0;
    for (var q = iext; q <= k; q++) { var ov = Math.min(H[q], bhi) - Math.max(L[q], blo); if (ov < 0) continue; n++; tot += V[q] * (H[q] > L[q] ? ov / (H[q] - L[q]) : 1); }
    return [tot, n];
  }
  function zigzag(y, thr) {
    if (y.length < 2) return 0;
    var n = 0, dirn = 0, ext = y[0];
    for (var i = 1; i < y.length; i++) { var v = y[i];
      if (dirn >= 0) { if (v > ext) ext = v; else if (ext - v >= thr) { if (dirn === 1) n++; dirn = -1; ext = v; } if (dirn === 0 && v - y[0] >= thr) dirn = 1; }
      else { if (v < ext) ext = v; else if (v - ext >= thr) { n++; dirn = 1; ext = v; } } }
    return n;
  }
  function interp(y, npts) {
    var out = [], m = y.length;
    for (var i = 0; i < npts; i++) { var u = npts > 1 ? i / (npts - 1) * (m - 1) : 0, lo = Math.floor(u), hi = Math.min(m - 1, lo + 1); out.push(y[lo] + (y[hi] - y[lo]) * (u - lo)); }
    return out;
  }
  function efiSeg(s) { var pp = 0; for (var i = 1; i < s.length; i++) pp += Math.abs(s[i] - s[i - 1]); return pp > 0 ? Math.abs(s[s.length - 1] - s[0]) / pp : 1; }
  function semejanza(t, C, d, a, ext, i0, iext, k, f, p) {
    var W = Math.abs(ext - a), m = i0;
    for (var q = i0; q <= iext; q++) if (d * (C[q] - a) / W <= 1 - f) m = q;
    var segM = [], segV = [];
    for (q = iext; q >= m; q--) segM.push(C[q]);
    for (q = iext; q <= k; q++) segV.push(C[q]);
    var dtm = Math.max(t[iext] - t[m], 1), dtv = Math.max(t[k] - t[iext], 1);
    var vel = -Math.abs(Math.log(Math.max(f * W / dtv, 1e-12) / (Math.max(Math.abs(ext - C[m]), 1) / dtm)));
    var ym = segM.map(function (v) { return d * (ext - v) / (f * W); }), yv = segV.map(function (v) { return d * (ext - v) / (f * W); });
    var forma = NaN;
    if (ym.length > 1 && yv.length > 1) { var A = interp(ym, p.npts), B = interp(yv, p.npts), s2 = 0; for (q = 0; q < p.npts; q++) s2 += (A[q] - B[q]) * (A[q] - B[q]); forma = -Math.sqrt(s2 / p.npts); }
    return { vel: vel, efi: -Math.abs(efiSeg(segV) - efiSeg(segM)), forma: forma, ondas: -Math.abs(zigzag(yv, 0.1 / f) / f - zigzag(ym, 0.1 / f) / f) };
  }
  function pct(v, ref) { if (v !== v || !ref.length) return NaN; var lt = 0, eq = 0; for (var i = 0; i < ref.length; i++) { if (Math.abs(ref[i] - v) <= 1e-9) eq++; else if (ref[i] < v) lt++; } return (lt + 0.5 * eq) / ref.length; }

  function run(t, O, H, L, C, V, session, last, prm) {
    var p = params(prm), n = C.length, i;
    if (!last) { last = new Uint8Array(n); for (i = 0; i < n - 1; i++) last[i] = session[i + 1] !== session[i] ? 1 : 0; }
    var thr = p.atr_k ? atrPrev(H, L, C, p.atr_n).map(function (v) { return p.atr_k * v; }) : new Float64Array(n).fill(p.min_w);
    var cuts = [0]; for (i = 1; i < n; i++) if (session[i] !== session[i - 1]) cuts.push(i); cuts.push(n);
    var refVpt = [], refComp = {}, impulses = [], events = [];
    p.xs.forEach(function (x) { refComp[x] = { vel: [], efi: [], forma: [], ondas: [] }; });
    for (var s = 0; s + 1 < cuts.length; s++) {
      var a0 = cuts[s], b0 = cuts[s + 1], imps = detect(t, H, L, C, V, thr, p, a0, b0), sesVpt = [], sesComp = {};
      p.xs.forEach(function (x) { sesComp[x] = { vel: [], efi: [], forma: [], ondas: [] }; });
      var corte = refVpt.length >= p.ref_min ? percentile(refVpt, p.i2_pct) : null;
      imps.forEach(function (im) {
        procesar(im, a0, b0, t, H, L, C, V, last, p, corte, refComp, sesComp, impulses, events);
        if (im.why === 1) sesVpt.push(im.vol / Math.abs(im.ext - im.a));
      });
      refVpt = refVpt.concat(sesVpt);
      p.xs.forEach(function (x) { COMP.forEach(function (c) { refComp[x][c] = refComp[x][c].concat(sesComp[x][c]); }); });
    }
    events.sort(function (x, y) { return x.bar - y.bar || x.imp_id - y.imp_id || x.seq - y.seq; });
    return { params: p, impulses: impulses, events: events };
  }
  function procesar(im, a0, b0, t, H, L, C, V, last, p, corte, refComp, sesComp, impulses, events) {
    var d = im.d, a = im.a, ext = im.ext, i0 = a0 + im.i0, iext = a0 + im.iext, jc = a0 + im.jconf, W = Math.abs(ext - a), iid = impulses.length;
    var vpt = im.vol / W, I1 = p.e_min <= im.eff && im.eff < p.e_max, I2 = corte === null ? null : vpt < corte, nl = perfil(H, L, V, i0, iext, a, ext, p);
    var rec = { imp_id: iid, dir: d, A: a, B: ext, W: W, bar_A: i0, bar_B: iext, bar_conf: jc, eff: im.eff, vol: im.vol, vol_por_tick: vpt,
                I1: I1, I2: I2, ineficiente: I1 || !!I2, no_lista_lo: nl[0], no_lista_hi: nl[1], no_lista_frac: nl[2], estado_final: null, bar_final: null, S2: null };
    impulses.push(rec);
    var seq = 0;
    function emit(kind, bar, kw) { var e = { imp_id: iid, kind: kind, bar: bar, t: t[bar], seq: seq++ }, k; for (k in (kw || {})) e[k] = kw[k]; events.push(e);
      if (FINAL[kind]) { rec.estado_final = kind; rec.bar_final = bar; } return e; }
    if (im.why !== 1) { emit("IMP_UNCONFIRMED", jc); return; }
    emit("IMP_CONFIRMED", jc, { dir: d, A: a, B: ext, W: W, ineficiente: rec.ineficiente, no_lista_lo: nl[0], no_lista_hi: nl[1] });
    var horizon = iext + Math.ceil(p.horizon_mult * (iext - i0 + 1)), done = {}, cand = false;
    for (var k = iext + 1; k < b0; k++) {
      var newext = (d === 1 && H[k] > ext) || (d === -1 && L[k] < ext), retr = d === 1 ? ext - L[k] : H[k] - ext;
      var f = Math.min(Math.max(retr, 0) / W, 1), kk = Math.max(k, jc);
      if (!newext) p.xs.forEach(function (x) {
        if (done[x] || f < x) return; done[x] = 1;
        var comp = semejanza(t, C, d, a, ext, i0, iext, k, f, p), pc = {}, all = true, sum = 0;
        COMP.forEach(function (c) { pc[c] = refComp[x][c].length >= p.ref_min ? pct(comp[c], refComp[x][c]) : NaN; if (pc[c] !== pc[c]) all = false; else sum += pc[c]; });
        var s2 = (pc.vel === pc.vel && pc.forma === pc.forma) ? (pc.vel >= 0.5 && pc.forma >= 0.5) : null, acc = aceptacion(H, L, V, iext, k, ext, W, d, p);
        COMP.forEach(function (c) { sesComp[x][c].push(comp[c]); });
        var kw = { x: x, f: f, S: all ? sum / 4 : NaN, S2: s2, aceptacion_B: im.vol > 0 ? acc[0] / im.vol : NaN, velas_en_B: acc[1] };
        COMP.forEach(function (c) { kw[c] = comp[c]; kw["p_" + c] = pc[c]; });
        emit(cand ? "MIRROR_PROGRESS" : "MIRROR_CANDIDATE", kk, kw);
        if (s2 !== null) rec.S2 = s2;
        cand = true;
      });
      if (newext) { emit(cand ? "MIRROR_FAILED" : "IMP_NO_MIRROR", kk, { reason: "new_extreme" }); return; }
      if (cand && f >= 1) { var far = d === 1 ? a - L[k] : H[k] - a; emit("MIRROR_COMPLETED", kk, { sobrepaso_W: Math.max(far, 0) / W, velas: k - iext }); return; }
      if (k >= horizon || last[k]) { emit(cand ? "MIRROR_EXPIRED" : "IMP_NO_MIRROR", kk, { reason: k >= horizon ? "horizon" : "session_end" }); return; }
    }
    if (iext + 1 >= b0 && last[b0 - 1]) emit("IMP_NO_MIRROR", Math.max(b0 - 1, jc), { reason: "session_end" });
  }
  var api = { run: run, params: params, DEFAULTS: DEF, FINAL: FINAL };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.EspejoImpulsos = api;
})(this);
