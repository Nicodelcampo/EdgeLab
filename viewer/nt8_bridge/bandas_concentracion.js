/* BandasConcentracion — port JS de edgelab/bridge/indicators/bandas_concentracion.py (capa &cz=1 del visor).
 * Misma iteración, mismo orden y mismos desempates; la paridad la verifica tests/research/test_bandas_concentracion.py.
 * Causal y target-free: zonas OG+VI ya nacidas y vivas en cada vela M1; t1 de cada banda depende del futuro. */
(function (root) {
  "use strict";
  var VIDA_S = 500 * 60;
  // zonas: [{t0, t1, top, bottom}]; tiempos: aperturas M1 ordenadas; alto en precio; umbral en zonas
  function detectar(zonas, tiempos, alto, umbral, vida) {
    var L = vida || VIDA_S, Z = zonas.slice().sort(function (a, b) { return a.t0 - b.t0; }), act = [], j = 0, out = [];
    for (var ti = 0; ti < tiempos.length; ti++) {
      var t = tiempos[ti];
      while (j < Z.length && Z[j].t0 <= t) act.push(Z[j++]);
      act = act.filter(function (z) { return (z.t1 || z.t0 + L) > t; });
      if (act.length < umbral) continue;
      var srt = act.slice().sort(function (a, b) { return a.bottom - b.bottom; });
      for (;;) {                                           // todas las bandas >= umbral del corte, sin compartir zonas
        var bn = 0, bb = 0, bi = null;
        for (var i = 0; i < srt.length; i++) {
          var b = srt[i].bottom, idx = [];
          for (var k = i; k < srt.length; k++) if (srt[k].top <= b + alto) idx.push(k);
          if (idx.length > bn) { bn = idx.length; bb = b; bi = idx; }
        }
        if (bn < umbral) break;
        var del = {}; bi.forEach(function (k) { del[k] = 1; }); srt = srt.filter(function (z, k) { return !del[k]; });
        var hit = false;
        for (var m = 0; m < out.length; m++) if (t <= out[m].t1 && bb < out[m].piso + alto && bb + alto > out[m].piso) {
          out[m].t1 = t + L; out[m].n = Math.max(out[m].n, bn); hit = true; break;    // misma banda: se alarga
        }
        if (!hit) out.push({ t0: t, t1: t + L, piso: bb, techo: bb + alto, n: bn, n0: bn });
      }
    }
    return out;
  }
  var api = { detectar: detectar, VIDA_S: VIDA_S };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.BandasConcentracion = api;
})(this);
