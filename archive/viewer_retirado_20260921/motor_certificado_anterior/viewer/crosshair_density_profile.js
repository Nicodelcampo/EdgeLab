(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EdgeLabCrosshairDensity = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function finite(value, fallback) { if (value === null || value === undefined || value === "") return fallback; const n = Number(value); return Number.isFinite(n) ? n : fallback; }
  function build(input) {
    input = input || {};
    const tickSize = finite(input.tickSize, 0);
    const minPrice = finite(input.minPrice, NaN);
    const maxPrice = finite(input.maxPrice, NaN);
    const sigmaTicks = Math.max(0, finite(input.sigmaTicks, 2));
    const maxBins = Math.max(10, Math.floor(finite(input.maxBins, 5000)));
    const ranges = Array.isArray(input.ranges) ? input.ranges : [];
    if (!(tickSize > 0)) throw new Error("tickSize must be positive");
    if (!Number.isFinite(minPrice) || !Number.isFinite(maxPrice) || maxPrice < minPrice) throw new Error("invalid price domain");
    const loTick = Math.ceil(minPrice / tickSize);
    const hiTick = Math.floor(maxPrice / tickSize);
    if (hiTick < loTick) return { loTick, hiTick, tickSize, density: [], maxDensity: 0, contributingRanges: 0 };
    if (hiTick - loTick + 1 > maxBins) throw new Error("density domain exceeds maxBins");
    const density = new Float64Array(hiTick - loTick + 1);
    const halo = Math.ceil(3 * sigmaTicks);
    let contributingRanges = 0;
    for (const raw of ranges) {
      if (!raw) continue;
      let lo = finite(raw.lo, NaN), hi = finite(raw.hi, NaN);
      const weight = Math.max(0, finite(raw.weight, 0));
      if (!Number.isFinite(lo) || !Number.isFinite(hi) || weight <= 0) continue;
      if (hi < lo) { const tmp = lo; lo = hi; hi = tmp; }
      const zLo = Math.round(lo / tickSize), zHi = Math.round(hi / tickSize);
      if (zHi + halo < loTick || zLo - halo > hiTick) continue;
      contributingRanges++;
      for (let k = Math.max(loTick, zLo - halo); k <= Math.min(hiTick, zHi + halo); k++) {
        const distance = k < zLo ? zLo - k : (k > zHi ? k - zHi : 0);
        const kernel = distance === 0 || sigmaTicks === 0 ? (distance === 0 ? 1 : 0) : Math.exp(-(distance * distance) / (2 * sigmaTicks * sigmaTicks));
        density[k - loTick] += weight * kernel;
      }
    }
    let maxDensity = 0;
    for (const value of density) if (value > maxDensity) maxDensity = value;
    return { loTick, hiTick, tickSize, density: Array.from(density), maxDensity, contributingRanges };
  }
  return { build };
});
