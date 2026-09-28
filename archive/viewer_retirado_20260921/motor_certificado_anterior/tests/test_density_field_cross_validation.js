/**
 * Cross-validation golden test: Python <-> JS density field equivalence.
 *
 * Verifies that the client-side JavaScript implementation calculates
 * identically the discrete density field and active zones from the golden fixture.
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const fixturePath = path.resolve(__dirname, '../fixtures/density_field_golden.json');
const golden = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));

function toNanoseconds(t) {
  if (typeof t === 'number') {
    if (t < 1e11) return t * 1e9;
    if (t < 1e14) return t * 1e6;
    if (t < 1e17) return t * 1e3;
    return t;
  }
  return Number(t);
}

function computeFieldJS(zones, tRefNs, tickSize, p0, p1, cfg) {
  const endedPolicy = cfg.ended_zone_policy || 'exclude_ended';
  const activeZones = zones.filter(z => {
    const avail = z.available_ts || z.available_ts_ns || z.available_ns || z.end_ts || z.end_ts_ns || z.t0;
    if (toNanoseconds(avail) > tRefNs) return false;
    const ended = z.ended_ts || z.ended_ts_ns || z.ended_ns || z.t1;
    if (ended && toNanoseconds(ended) <= tRefNs && endedPolicy === 'exclude_ended') return false;
    return true;
  }).sort((a, b) => {
    const at = toNanoseconds(a.available_ts || a.available_ts_ns || a.available_ns || a.end_ts || a.t0);
    const bt = toNanoseconds(b.available_ts || b.available_ts_ns || b.available_ns || b.end_ts || b.t0);
    return (at - bt) || String(a.id).localeCompare(String(b.id));
  });

  const d = new Float64Array(p1 - p0 + 1);
  const s = Math.max(0.1, +(cfg.sigma_ticks || 1.2));
  const cut = Math.ceil(3 * s);

  for (const z of activeZones) {
    const w = 1.0;
    const lo = Math.round(+z.lo / tickSize);
    const hi = Math.round(+z.hi / tickSize);

    if (cfg.kernel === 'KERNEL_BOX') {
      for (let k = Math.max(p0, lo); k <= Math.min(p1, hi); k++) {
        d[k - p0] += w;
      }
    } else {
      for (let k = Math.max(p0, lo - cut); k <= Math.min(p1, hi + cut); k++) {
        const q = k < lo ? lo - k : k > hi ? k - hi : 0;
        if (q <= 3 * s) {
          d[k - p0] += w * (q === 0 ? 1 : Math.exp(-(q * q) / (2 * s * s)));
        }
      }
    }
  }

  const rounded = Array.from(d, v => +v.toFixed(8));
  const mean = rounded.reduce((a, b) => a + b, 0) / rounded.length;
  const max = Math.max(...rounded);

  return {
    active_zone_ids: activeZones.map(z => z.id),
    density: rounded,
    field_mean: +mean.toFixed(6),
    field_max: +max.toFixed(6)
  };
}

console.log('Running JS Golden Cross-Validation...');
const jsRes = computeFieldJS(
  golden.input_zones,
  golden.t_ref_ns,
  golden.tick_size,
  golden.price_tick_min,
  golden.price_tick_max,
  {
    model: golden.model,
    kernel: golden.kernel,
    sigma_ticks: golden.sigma_ticks
  }
);

// 1. Verify active zones match exactly
assert.deepStrictEqual(jsRes.active_zone_ids, golden.active_zone_ids, 'Active zone IDs mismatch');
console.log('✓ Active zones match exactly:', jsRes.active_zone_ids);

// 2. Verify field mean and max match to within 1e-4
const meanDiff = Math.abs(jsRes.field_mean - golden.field_mean);
const maxDiff = Math.abs(jsRes.field_max - golden.field_max);
assert(meanDiff < 1e-4, `Field mean mismatch: JS ${jsRes.field_mean} vs Py ${golden.field_mean} (diff: ${meanDiff})`);
assert(maxDiff < 1e-4, `Field max mismatch: JS ${jsRes.field_max} vs Py ${golden.field_max} (diff: ${maxDiff})`);
console.log(`✓ Field mean match: JS ${jsRes.field_mean} == Py ${golden.field_mean}`);
console.log(`✓ Field max match: JS ${jsRes.field_max} == Py ${golden.field_max}`);

// 3. Verify point-by-point density array matches
assert.strictEqual(jsRes.density.length, golden.full_density.length, 'Density array length mismatch');
let maxPointDiff = 0;
for (let i = 0; i < jsRes.density.length; i++) {
  const diff = Math.abs(jsRes.density[i] - golden.full_density[i]);
  if (diff > maxPointDiff) maxPointDiff = diff;
  assert(diff < 1e-4, `Point discrepancy at index ${i}: JS ${jsRes.density[i]} vs Py ${golden.full_density[i]}`);
}
console.log(`✓ Point-by-point density matches across ${jsRes.density.length} ticks (max diff: ${maxPointDiff.toExponential(2)})`);

console.log('ALL JS GOLDEN CROSS-VALIDATION CHECKS PASSED!');

