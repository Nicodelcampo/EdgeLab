/* Corre los vectores dorados de Python contra el puerto JS y emite un resumen JSON.
 * Lo ejecuta `test_density_field_js_parity.py`; también sirve a mano:
 *     node tests/research/density_field_js_parity_runner.js
 */
"use strict";
const fs = require("fs");
const path = require("path");
const DF = require(process.env.DF_JS || path.resolve(__dirname, "../../viewer/nt8_bridge/density_field.js"));   // DF_JS: para pruebas de mutación
const golden = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../fixtures/density_field_golden_v2.json"), "utf8"));

const TOL_DENSITY = 2e-8;       // ambos redondean a 8 decimales: solo puede diferir un empate de redondeo
const TOL_ROUND6 = 2e-6;
const close = (a, b, tol) => Math.abs(a - b) <= tol;

function cmpInterval(a, b, keys6) {
  if (a.length !== b.length) return "longitud " + a.length + " != " + b.length;
  for (let i = 0; i < a.length; i++) {
    for (const k of Object.keys(b[i])) {
      const x = a[i][k], y = b[i][k];
      if (typeof y === "number" && keys6.includes(k)) { if (!close(x, y, TOL_ROUND6)) return k + "[" + i + "] " + x + " != " + y; }
      else if (typeof y === "number") { if (x !== y && !close(x, y, 1e-9)) return k + "[" + i + "] " + x + " != " + y; }
      else if (JSON.stringify(x) !== JSON.stringify(y)) return k + "[" + i + "] " + JSON.stringify(x) + " != " + JSON.stringify(y);
    }
  }
  return null;
}

const out = { version: DF.VERSION, scenarios: {}, fail_closed: {} };

for (const s of golden.scenarios) {
  const e = s.expected, r = { ok: true, problemas: [] };
  const f = DF.computeField(s.zones, s.t_ref, s.tick_size, s.p_min, s.p_max, s.cfg);
  const inter = DF.detectDensityIntervals(f.density, f.priceTickMin, s.tick_size, s.interval_opts);
  const corr = DF.characterizeCorridors(inter, s.zones, f.activeZoneIds, s.tick_size, DF.toNanoseconds(s.t_ref));

  let maxd = 0, exactos = 0;
  if (f.density.length !== e.density.length) r.problemas.push("largo de densidad");
  else for (let i = 0; i < e.density.length; i++) { const d = Math.abs(f.density[i] - e.density[i]); if (d > maxd) maxd = d; if (d === 0) exactos++; }
  r.max_abs_diff = maxd; r.exactos = exactos; r.n = e.density.length;
  if (maxd > TOL_DENSITY) r.problemas.push("densidad max|diff|=" + maxd);
  if (JSON.stringify(f.activeZoneIds) !== JSON.stringify(e.active_zone_ids)) r.problemas.push("ids activos");

  const m1 = cmpInterval(inter.low_density_intervals, e.intervals.low_density_intervals, ["avg_density"]);
  if (m1) r.problemas.push("corredores: " + m1);
  const m2 = cmpInterval(inter.high_density_regions, e.intervals.high_density_regions, ["max_density"]);
  if (m2) r.problemas.push("murallas: " + m2);
  const m3 = cmpInterval(corr, e.corridors, ["avg_density"]);
  if (m3) r.problemas.push("caracterizacion: " + m3);

  const d = f.diagnostics, x = e.diagnostics;
  if (!close(d.v_ref, x.v_ref, 1e-9)) r.problemas.push("v_ref " + d.v_ref + " != " + x.v_ref);
  for (const k of ["v_ref_source", "n_active_zones", "total_zones_evaluated", "legacy_availability_fallbacks",
                   "legacy_touch_fallbacks", "causal_status", "n_ticks"])
    if (d[k] !== x[k]) r.problemas.push(k + " " + d[k] + " != " + x[k]);
  if (JSON.stringify(d.available_ts_sources) !== JSON.stringify(x.available_ts_sources)) r.problemas.push("available_ts_sources");
  if (!close(d.field_mean, x.field_mean, TOL_ROUND6) || !close(d.field_max, x.field_max, TOL_ROUND6)) r.problemas.push("field_mean/max");

  r.ok = r.problemas.length === 0;
  r.corredores = corr.length; r.murallas = inter.high_density_regions.length; r.activas = f.activeZoneIds.length;
  out.scenarios[s.name] = r;
}

for (const c of golden.must_fail_closed) {
  let lanzo = false, msg = "";
  try { DF.computeField(c.zones, c.t_ref, golden.tick_size, 76000, 76100, c.cfg); } catch (err) { lanzo = true; msg = String(err.message); }
  out.fail_closed[c.name] = { lanzo: lanzo, mensaje: msg };
}

process.stdout.write(JSON.stringify(out));
