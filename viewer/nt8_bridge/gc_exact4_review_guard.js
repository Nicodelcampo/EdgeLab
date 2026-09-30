/* Target-free review copy only. No raw availability or execution claim. */
(function (root) {
  "use strict";
  const asset = "GC_04-26_202602_25T_HFT";
  const cache = new WeakMap();
  function require(ok, message) { if (!ok) throw new Error(message); }
  function validate(d, b, key, aid) {
    require(d && d.schema === "edgelab.gc_exact4.review_layer/1",
      "EXACT4_REVIEW_LAYER_REQUIRED");
    require(d.targetfree_only === true && d.outcomes_computed === false &&
      d.financial_use_certified === false, "TARGETFREE_SCOPE_REQUIRED");
    require(aid === asset && d.asset === aid && key === d.bar_key &&
      key === "tick_25", "ASSET_OR_SERIES_MISMATCH");
    require(b && b.meta && b.meta.tick_size === 0.1, "GC_TICK_REQUIRED");
    const cd = b.bar_series[key].candles, w = d.binding.window;
    require(cd.length === w.bars && cd[0].time === w.first_bar_time &&
      cd[cd.length - 1].time === w.last_bar_time, "WINDOW_MISMATCH");
    if (cache.get(d) === b) return true;
    const ids = new Set();
    d.zonas.forEach(z => {
      require(!ids.has(z.id), "DUPLICATE_ZONE");
      ids.add(z.id);
      require(z.toques === 4 && z.picos.length === 4 && z.det_idx === 3 &&
        z.det_pico === 4 && z.targetfree_only === true &&
        z.outcome_computed === false && z.financial_use_certified === false &&
        z.publication_metadata_pass === false, "EXACT4_OR_SCOPE_MISMATCH");
      require(z.kind === "H" || z.kind === "L", "SIDE_MISMATCH");
      require(Number.isInteger(z.det_i) && cd[z.det_i] &&
        cd[z.det_i].time === z.det_t &&
        cd[z.det_i].close === z.det_precio, "LOGICAL_DETECTION_MISMATCH");
      z.picos.forEach((p, i) => {
        require(Number.isInteger(p[0]) && p[0] < z.det_i &&
          (!i || p[0] > z.picos[i - 1][0]), "PREFIX_ORDER_MISMATCH");
        const c = cd[p[0]];
        require(c && c.time === p[1] &&
          c[z.kind === "H" ? "high" : "low"] === p[2], "PEAK_PARITY_MISMATCH");
        Object.freeze(p);
      });
      Object.freeze(z.picos);
      Object.freeze(z.members_known_at);
      Object.freeze(z);
    });
    Object.freeze(d.zonas);
    Object.freeze(d);
    cache.set(d, b);
    return true;
  }
  function block(message) {
    if (typeof document !== "undefined") {
      const el = document.getElementById("lbl-det-status");
      if (el) el.textContent = "Exact4 bloqueado: " + message;
    }
    return false;
  }
  function canDraw(d, b, key, aid) {
    try { return validate(d, b, key, aid); }
    catch (error) { return block(error.message); }
  }
  const api = {asset, validate, canDraw, block};
  root.GCExact4Review = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") {
    // Remove legacy trade/candidate parameters even if pasted into a review URL.
    const url = new URL(window.location.href);
    ["sl", "tp", "be", "cand", "espejo"].forEach(k => url.searchParams.delete(k));
    url.searchParams.set("asset", asset);
    url.searchParams.set("tf", "tick_25");
    url.searchParams.set("solo", "det");
    if (!/^exact4_c[1-4]$/.test(url.searchParams.get("det") || ""))
      url.searchParams.set("det", "exact4_c1");
    window.history.replaceState(null, "", url.toString());
  }
})(typeof globalThis !== "undefined" ? globalThis : this);