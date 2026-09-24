/* EdgeLab — campo de densidad HP-007 D(p,t): PUERTO JS de `edgelab/research/density_field.py`.
 *
 * ÚNICA implementación de densidad/corredores del visor. `index.html` no calcula densidad por su
 * cuenta: llama acá. La referencia es el módulo Python; este archivo se verifica contra vectores
 * dorados generados desde él (`tools/generate_density_field_golden_vectors.py`,
 * `tests/research/test_density_field_js_parity.py`).
 *
 * Contrato heredado del motor certificado anterior (`corridor_engine.js`, archivado):
 *   - causalidad: una zona contribuye en t sii available_ts <= t;
 *   - invariancia de viewport: el resultado NO depende de zoom, pan ni tamaño de canvas;
 *   - firewall del holdout: falla cerrado si una zona, o el instante de evaluación, cae en o después
 *     de HOLDOUT_NS;
 *   - determinismo: mismas entradas => misma salida, independiente del orden de las zonas.
 *
 * LÍMITE DE PRECISIÓN (declarado, no oculto): los timestamps en nanosegundos de época (~1.78e18)
 * exceden 2^53, así que como `number` de JS tienen una resolución efectiva de 256 ns. Alcanza para el
 * corte causal a escala de segundos; NO garantiza el desempate exacto de dos eventos a < 256 ns. Los
 * vectores dorados usan nanosegundos múltiplos de 4096, exactamente representables.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EdgeLabDensityField = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const HOLDOUT_NS = 1782856800000000000;
  const VERSION = "1.0.0";

  // ------------------------------------------------------------------ utilidades numéricas

  /** round-half-even, como `round()` de Python para el redondeo a entero. */
  function roundHalfEven(x) {
    const f = Math.floor(x), d = x - f;
    if (d < 0.5) return f;
    if (d > 0.5) return f + 1;
    return (f % 2 === 0) ? f : f + 1;
  }
  function round6(x) { return Number(x.toFixed(6)); }
  function round8(x) { return Number(x.toFixed(8)); }

  function cmpStr(a, b) { return a < b ? -1 : (a > b ? 1 : 0); }

  function toNanoseconds(t) {
    if (t === null || t === undefined) return 0;
    let val;
    if (typeof t === "number") {
      val = Number.isInteger(t) ? t : roundHalfEven(t);
    } else if (typeof t === "string") {
      const s = t.trim();
      if (/^-?\d+$/.test(s)) return Number(s);       // Python: int(t) sin detección de escala
      const ms = Date.parse(s);
      return Number.isFinite(ms) ? ms * 1e6 : 0;
    } else {
      return 0;
    }
    if (val < 100000000000) return val * 1e9;               // segundos
    if (val < 100000000000000) return val * 1e6;            // milisegundos
    if (val < 100000000000000000) return val * 1e3;         // microsegundos
    return val;                                             // nanosegundos
  }

  function priceToTick(price, tickSize) { return roundHalfEven(round6(price / tickSize)); }
  function tickToPrice(tick, tickSize) { return round6(tick * tickSize); }

  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const notNull = (v) => v !== undefined && v !== null;

  // ------------------------------------------------------------------ extracción de campos

  const AVAIL_KEYS = ["available_ns", "available_ts", "availableTime"];
  const AVAIL_FALLBACK_KEYS = ["origin_ts", "created_ms", "sig_ts", "t0", "time"];

  /** -> [available_ns, esFallbackLegacy] */
  function extractZoneAvailableNs(z) {
    for (const k of AVAIL_KEYS) if (has(z, k) && notNull(z[k])) return [toNanoseconds(z[k]), false];
    for (const k of AVAIL_FALLBACK_KEYS) if (has(z, k) && notNull(z[k])) return [toNanoseconds(z[k]), true];
    return [0, true];
  }

  function extractZoneAvailableSource(z) {
    if (has(z, "available_ts_source") && z.available_ts_source) return String(z.available_ts_source);
    const src = String(z.source === undefined ? "" : z.source).toLowerCase();
    if (src.indexOf("hft") !== -1) {
      if (has(z, "end_ms") || has(z, "created_ms") ||
          (!has(z, "end_ts_ns") && !has(z, "available_ts_ns") && !has(z, "end_ns"))) return "V1_END_MS_DERIVED";
      return "V2_END_NS";
    }
    if (src.indexOf("bigtrap") !== -1 || src.indexOf("bt2a") !== -1) {
      if (has(z, "sig_ts") || has(z, "sig_ts_confirmed") || has(z, "available_ts")) return "SIG_TS_CONFIRMED";
      return "LEGACY_CREATED_MS_FALLBACK";
    }
    return extractZoneAvailableNs(z)[1] ? "LEGACY_FALLBACK" : "EXPLICIT_AVAILABLE_TS";
  }

  const ENDED_KEYS = ["ended_ns", "ended_ts", "ended_ms", "t1"];
  function extractZoneEndedNs(z) {
    for (const k of ENDED_KEYS) if (has(z, k) && notNull(z[k])) return toNanoseconds(z[k]);
    return null;
  }

  /** -> [toquesAsOf, esFallbackLegacy] */
  function reconstructZoneTouchesAsof(z, tRefNs) {
    if (Array.isArray(z.touch_events)) {
      let count = 0;
      for (const ev of z.touch_events) {
        let ts = ev;
        if (ev !== null && typeof ev === "object") ts = has(ev, "touch_ts") ? ev.touch_ts : (has(ev, "ts") ? ev.ts : ev);
        if (toNanoseconds(ts) <= tRefNs) count++;
      }
      return [count, false];
    }
    return [Math.trunc(Number(notNull(z.touches) ? z.touches : 0)), true];
  }

  /** Volumen de una zona. Un volumen NULO equivale a AUSENTE (usa `def`), igual que density_field.zone_volume. */
  function zoneVolume(z, def) {
    const v = notNull(z.vol) ? z.vol : (notNull(z.volume) ? z.volume : null);
    return v === null ? def : Number(v);
  }

  const zoneId = (z) => String(has(z, "id") ? z.id : (has(z, "zone_id") ? z.zone_id : ""));
  const zoneLoPx = (z) => Number(has(z, "lo") ? z.lo : (has(z, "bottom") ? z.bottom : 0.0));
  const zoneHiPx = (z) => Number(has(z, "hi") ? z.hi : (has(z, "top") ? z.top : 0.0));

  function median(sortedVals) {
    const n = sortedVals.length;
    return n % 2 ? sortedVals[(n - 1) / 2] : (sortedVals[n / 2 - 1] + sortedVals[n / 2]) / 2;
  }

  /** -> [vRef, fuente] */
  function computeCausalVRef(zones, tRefNs, maxWindow, coldStartDefault) {
    maxWindow = maxWindow === undefined ? 500 : maxWindow;
    coldStartDefault = coldStartDefault === undefined ? 100.0 : coldStartDefault;
    const items = [];
    for (const z of zones) {
      const avail = extractZoneAvailableNs(z)[0];
      if (avail <= tRefNs) {
        const vol = zoneVolume(z, 0.0);
        if (vol > 0.0) items.push([avail, zoneId(z), vol]);
      }
    }
    if (!items.length) return [coldStartDefault, "COLD_START_DEFAULT"];
    items.sort((a, b) => (a[0] - b[0]) || cmpStr(a[1], b[1]));
    const win = items.slice(-maxWindow).map((x) => x[2]).sort((a, b) => a - b);
    return [Math.max(1.0, median(win)), "CAUSAL_ROLLING_MEDIAN_N_" + win.length];
  }

  // ------------------------------------------------------------------ campo de densidad

  /**
   * Campo discreto sobre la grilla de ticks [pMin, pMax]. Puro, determinista, sin canvas.
   * Devuelve {density, priceTickMin, priceTickMax, activeZoneIds, diagnostics}.
   */
  function computeField(zones, tRef, tickSize, pMin, pMax, fieldConfig) {
    if (pMax < pMin) throw new Error("price_tick_max (" + pMax + ") must be >= price_tick_min (" + pMin + ")");
    const cfg = fieldConfig || {};
    const modelName = cfg.model === undefined ? "FIELD_RAW_STATIC" : cfg.model;
    const kernelType = cfg.kernel === undefined ? "KERNEL_GAUSS" : cfg.kernel;
    const sigmaTicks = Number(cfg.sigma_ticks === undefined ? 1.2 : cfg.sigma_ticks);
    const endedPolicy = cfg.ended_zone_policy === undefined ? "exclude_ended" : cfg.ended_zone_policy;
    const tRefNs = toNanoseconds(tRef);
    const guard = cfg.holdout_guard === undefined ? true : !!cfg.holdout_guard;
    if (guard && tRefNs >= HOLDOUT_NS) throw new Error("t_ref is at or after the sealed holdout boundary");

    const active = [];
    let legacyAvail = 0, legacyTouch = 0;
    for (const z of zones) {
      const av = extractZoneAvailableNs(z);
      if (guard && av[0] >= HOLDOUT_NS) throw new Error("zone " + zoneId(z) + " is available at or after the sealed holdout boundary");
      if (av[1]) legacyAvail++;
      if (av[0] > tRefNs) continue;
      if (notNull(cfg.session_id) && notNull(z.session_id) && String(z.session_id) !== String(cfg.session_id)) continue;
      if (notNull(cfg.contract) && notNull(z.contract) && String(z.contract) !== String(cfg.contract)) continue;
      const ended = extractZoneEndedNs(z);
      const isEnded = ended !== null && ended <= tRefNs;
      if (isEnded && endedPolicy === "exclude_ended") continue;
      active.push(z);
    }
    const key = (z) => [extractZoneAvailableNs(z)[0], zoneId(z), zoneLoPx(z), zoneHiPx(z)];
    active.sort((a, b) => {
      const ka = key(a), kb = key(b);
      return (ka[0] - kb[0]) || cmpStr(ka[1], kb[1]) || (ka[2] - kb[2]) || (ka[3] - kb[3]);
    });
    const activeIds = active.map(zoneId);

    const vr = computeCausalVRef(zones, tRefNs,
      cfg.v_ref_window === undefined ? 500 : Number(cfg.v_ref_window),
      cfg.cold_start_v_ref === undefined ? 100.0 : Number(cfg.cold_start_v_ref));
    const vRef = vr[0];

    const nTicks = (pMax - pMin) + 1;
    const dens = new Float64Array(nTicks);

    for (const z of active) {
      const zAvail = extractZoneAvailableNs(z)[0];
      const ended = extractZoneEndedNs(z);
      const isEnded = ended !== null && ended <= tRefNs;
      let loTick = priceToTick(zoneLoPx(z), tickSize), hiTick = priceToTick(zoneHiPx(z), tickSize);
      if (loTick > hiTick) { const t = loTick; loTick = hiTick; hiTick = t; }

      let wZone;
      if (modelName === "FIELD_RAW_STATIC") {
        wZone = 1.0;
      } else {
        const zVol = zoneVolume(z, 1.0);
        const volTrans = cfg.vol_transform === undefined ? "TRANS_POWER_025" : cfg.vol_transform;
        const ratio = Math.max(1.0, zVol) / Math.max(1.0, vRef);
        let wVol;
        if (volTrans === "TRANS_COUNT") wVol = 1.0;
        else if (volTrans === "TRANS_LOG") wVol = Math.log2(1.0 + ratio);
        else if (volTrans === "TRANS_WINSORIZED") wVol = Math.pow(Math.min(ratio, 3.0), 0.25);
        else wVol = Math.pow(ratio, 0.25);

        let fMat = 1.0;
        if (cfg.use_maturation) {
          const ageS = Math.max(0.0, (tRefNs - zAvail) / 1e9);
          fMat = 1.0 / (1.0 + Math.exp(-Math.max(-20.0, Math.min(20.0, (ageS - 1800.0) / 600.0))));
        }
        let fDecay = 1.0;
        if (cfg.use_time_decay) {
          const ageS = Math.max(0.0, (tRefNs - zAvail) / 1e9);
          const decayAge = Math.max(0.0, ageS - 14400.0);
          fDecay = Math.exp(-Math.log(2.0) * decayAge / 43200.0);
        }
        let fWear = 1.0;
        if (cfg.use_wear) {
          const tw = reconstructZoneTouchesAsof(z, tRefNs);
          if (tw[1]) legacyTouch++;
          // (1 + a·toques)^-b; por defecto a=0.5, b=0.60 (igual que density_field.py)
          fWear = Math.pow(1.0 + (cfg.wear_alpha !== undefined ? Number(cfg.wear_alpha) : 0.5) * tw[0],
                           -(cfg.wear_exp !== undefined ? Number(cfg.wear_exp) : 0.60));
        }
        const penalty = (isEnded && endedPolicy === "penalize_ended")
          ? Number(cfg.invalidation_penalty === undefined ? 0.35 : cfg.invalidation_penalty) : 1.0;
        wZone = wVol * fMat * fDecay * fWear * penalty;
      }
      if (wZone <= 0.0) continue;

      if (kernelType === "KERNEL_BOX") {
        const kLo = Math.max(pMin, loTick), kHi = Math.min(pMax, hiTick);
        for (let k = kLo; k <= kHi; k++) dens[k - pMin] += wZone;
      } else if (kernelType.indexOf("KERNEL_GAUSS") === 0) {
        const sigma = Math.max(0.1, sigmaTicks);
        const cutoff = Math.ceil(3.0 * sigma);
        const kLo = Math.max(pMin, loTick - cutoff), kHi = Math.min(pMax, hiTick + cutoff);
        for (let k = kLo; k <= kHi; k++) {
          const d = k < loTick ? loTick - k : (k > hiTick ? k - hiTick : 0.0);
          if (d <= 3.0 * sigma) dens[k - pMin] += wZone * (d === 0.0 ? 1.0 : Math.exp(-(d * d) / (2.0 * sigma * sigma)));
        }
      }
    }

    if (cfg.saturation) for (let i = 0; i < nTicks; i++) dens[i] = 1.0 - Math.exp(-Math.max(0.0, dens[i]));

    const density = new Array(nTicks);
    let sum = 0.0, max = -Infinity;
    for (let i = 0; i < nTicks; i++) { sum += dens[i]; if (dens[i] > max) max = dens[i]; density[i] = round8(dens[i]); }

    const sources = {};
    for (const z of active) { const s = extractZoneAvailableSource(z); sources[s] = (sources[s] || 0) + 1; }

    return {
      density: density, priceTickMin: pMin, priceTickMax: pMax, activeZoneIds: activeIds,
      diagnostics: {
        model: modelName, kernel: kernelType, sigma_ticks: sigmaTicks, v_ref: vRef, v_ref_source: vr[1],
        n_active_zones: active.length, total_zones_evaluated: zones.length,
        legacy_availability_fallbacks: legacyAvail, legacy_touch_fallbacks: legacyTouch,
        available_ts_sources: sources,
        causal_status: legacyAvail > 0 ? "LEGACY_NON_CAUSAL" : "PASS_CAUSAL",
        n_ticks: nTicks, field_mean: round6(sum / nTicks), field_max: round6(max),
      },
    };
  }

  // ------------------------------------------------------------------ intervalos

  function detectDensityIntervals(density, priceTickMin, tickSize, opts) {
    opts = opts || {};
    const lowT = opts.low_thresh === undefined ? 0.32 : opts.low_thresh;
    const highT = opts.high_thresh === undefined ? 0.70 : opts.high_thresh;
    const minLow = opts.min_low_ticks === undefined ? 7 : opts.min_low_ticks;
    const minHigh = opts.min_high_ticks === undefined ? 2 : opts.min_high_ticks;
    const n = density.length;
    if (n === 0) return { low_density_intervals: [], high_density_regions: [] };
    const tk = (i) => priceTickMin + i;
    const meanOf = (a, b) => { let s = 0.0; for (let i = a; i < b; i++) s += density[i]; return s / (b - a); };
    const maxOf = (a, b) => { let m = -Infinity; for (let i = a; i < b; i++) if (density[i] > m) m = density[i]; return m; };

    const low = [];
    const pushLow = (s, e) => {
      const span = e - s;
      if (span >= minLow) low.push({ tick_start: tk(s), tick_end: tk(e - 1), price_min: tickToPrice(tk(s), tickSize),
        price_max: tickToPrice(tk(e - 1), tickSize), tick_count: span, avg_density: round6(meanOf(s, e)) });
    };
    let inLow = false, lowStart = 0;
    for (let i = 0; i < n; i++) {
      if (density[i] <= lowT) { if (!inLow) { inLow = true; lowStart = i; } }
      else if (inLow) { pushLow(lowStart, i); inLow = false; }
    }
    if (inLow) pushLow(lowStart, n);

    const high = [];
    const pushHigh = (s, e) => {
      const span = e - s;
      if (span >= minHigh) high.push({ tick_start: tk(s), tick_end: tk(e - 1), price_min: tickToPrice(tk(s), tickSize),
        price_max: tickToPrice(tk(e - 1), tickSize), tick_count: span, max_density: round6(maxOf(s, e)) });
    };
    let inHigh = false, highStart = 0;
    for (let i = 0; i < n; i++) {
      if (density[i] >= highT) { if (!inHigh) { inHigh = true; highStart = i; } }
      else if (inHigh) { pushHigh(highStart, i); inHigh = false; }
    }
    if (inHigh) pushHigh(highStart, n);
    return { low_density_intervals: low, high_density_regions: high };
  }

  // ------------------------------------------------------------------ caracterización (capa explícita)

  const WALL_TOLERANCE_TICKS = 3;
  const CHARACTERIZATION_STATUS = "CHARACTERIZATION_UNCERTIFIED";

  function zoneSide(z) {
    const kind = String(notNull(z.kind) ? z.kind : "").toUpperCase();
    if (kind.indexOf("BUY") !== -1 || kind.indexOf("BULL") !== -1) return "BUY";
    if (kind.indexOf("SELL") !== -1 || kind.indexOf("BEAR") !== -1) return "SELL";
    if (notNull(z.direction)) {
      const d = Number(z.direction);
      if (Number.isFinite(d)) { if (d > 0) return "BUY"; if (d < 0) return "SELL"; }
    }
    return null;
  }

  function characterizeCorridors(intervals, zones, activeZoneIds, tickSize, tRefNs, wallTol) {
    wallTol = wallTol === undefined ? WALL_TOLERANCE_TICKS : wallTol;
    const activos = new Set(activeZoneIds);
    const zs = [];
    for (const z of zones) {
      const id = zoneId(z);
      if (!activos.has(id)) continue;
      let a = priceToTick(zoneLoPx(z), tickSize), b = priceToTick(zoneHiPx(z), tickSize);
      if (a > b) { const t = a; a = b; b = t; }
      zs.push({ id: id, lo: a, hi: b, side: zoneSide(z), avail_ns: extractZoneAvailableNs(z)[0] });
    }
    const members = (w) => zs.filter((z) => z.hi >= w.tick_start - wallTol && z.lo <= w.tick_end + wallTol);
    const walls = intervals.high_density_regions.slice().sort((a, b) => a.tick_start - b.tick_start);
    const lows = intervals.low_density_intervals.slice().sort((a, b) => a.tick_start - b.tick_start);
    const out = [];
    for (const c of lows) {
      let floor = null;
      for (const w of walls) if (w.tick_end < c.tick_start) floor = w;
      let ceil = null;
      for (const w of walls) if (w.tick_start > c.tick_end) { ceil = w; break; }
      const mf = floor ? members(floor) : [], mc = ceil ? members(ceil) : [];
      const buyFloor = mf.some((m) => m.side === "BUY"), sellCeil = mc.some((m) => m.side === "SELL");
      const direction = (buyFloor && sellCeil) ? "DUAL" : (buyFloor ? "BULL" : (sellCeil ? "BEAR" : "STRUCTURAL"));
      const avails = mf.concat(mc).map((m) => m.avail_ns);
      out.push({
        id: "CORR_" + c.tick_start + "_" + c.tick_end, tick_start: c.tick_start, tick_end: c.tick_end,
        gap_ticks: c.tick_count, price_min: c.price_min, price_max: c.price_max, avg_density: c.avg_density,
        direction: direction, bounded_below: floor !== null, bounded_above: ceil !== null,
        floor_wall: floor ? [floor.tick_start, floor.tick_end] : null,
        ceil_wall: ceil ? [ceil.tick_start, ceil.tick_end] : null,
        t_birth_ns: avails.length ? Math.max.apply(null, avails) : Math.trunc(tRefNs),
      });
    }
    return out;
  }

  // ------------------------------------------------------------------ presets y estado canónico

  /** Presets de `tools/run_visual_configurations.py` + el modelo calibrado por defecto del visor. */
  const PRESETS = {
    FIELD_RAW_STATIC: { model: "FIELD_RAW_STATIC", kernel: "KERNEL_GAUSS", sigma_ticks: 1.2 },
    FIELD_BOX: { model: "FIELD_RAW_STATIC", kernel: "KERNEL_BOX" },
    FIELD_TRANS_POWER025: { model: "FIELD_TRANS", kernel: "KERNEL_GAUSS", sigma_ticks: 1.2, vol_transform: "TRANS_POWER_025" },
    FIELD_TRANS_LOG: { model: "FIELD_TRANS", kernel: "KERNEL_GAUSS", sigma_ticks: 1.2, vol_transform: "TRANS_LOG" },
    // Por defecto del visor: modelo completo (volumen^0,25, maduración, decaimiento a 12 h tras 4 h,
    // desgaste) + saturación 1-exp(-D), que es lo que hace significativos los umbrales normalizados.
    HP007_CALIBRATED: { model: "FIELD_TRANS", kernel: "KERNEL_GAUSS", sigma_ticks: 1.2, vol_transform: "TRANS_POWER_025",
      use_maturation: true, use_time_decay: true, use_wear: true, saturation: true },
    // Igual pero sin decaimiento temporal: la variante «Sólo Comercio» del visor.
    HP007_NO_TIME_DECAY: { model: "FIELD_TRANS", kernel: "KERNEL_GAUSS", sigma_ticks: 1.2, vol_transform: "TRANS_POWER_025",
      use_maturation: true, use_time_decay: false, use_wear: true, saturation: true },
  };

  function fnv1a(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return (h >>> 0).toString(16).padStart(8, "0");
  }

  /** Cadena canónica del estado ECONÓMICO (sin nada de viewport) y su huella. No es el SHA-256 de Python. */
  function canonicalState(field, intervals, corridors, tRefNs) {
    const s = JSON.stringify({
      asOf: tRefNs, domain: [field.priceTickMin, field.priceTickMax], model: field.diagnostics.model,
      kernel: field.diagnostics.kernel, sigma: field.diagnostics.sigma_ticks, ids: field.activeZoneIds,
      density: field.density,
      low: intervals.low_density_intervals.map((c) => [c.tick_start, c.tick_end]),
      high: intervals.high_density_regions.map((c) => [c.tick_start, c.tick_end]),
      corridors: (corridors || []).map((c) => [c.id, c.direction, c.t_birth_ns]),
    });
    return { canonical: s, fingerprint: fnv1a(s) };
  }

  return {
    VERSION: VERSION, HOLDOUT_NS: HOLDOUT_NS, WALL_TOLERANCE_TICKS: WALL_TOLERANCE_TICKS,
    CHARACTERIZATION_STATUS: CHARACTERIZATION_STATUS, PRESETS: PRESETS,
    toNanoseconds: toNanoseconds, priceToTick: priceToTick, tickToPrice: tickToPrice,
    extractZoneAvailableNs: extractZoneAvailableNs, extractZoneAvailableSource: extractZoneAvailableSource,
    extractZoneEndedNs: extractZoneEndedNs, reconstructZoneTouchesAsof: reconstructZoneTouchesAsof,
    computeCausalVRef: computeCausalVRef, computeField: computeField, detectDensityIntervals: detectDensityIntervals,
    zoneSide: zoneSide, characterizeCorridors: characterizeCorridors, canonicalState: canonicalState,
  };
});
