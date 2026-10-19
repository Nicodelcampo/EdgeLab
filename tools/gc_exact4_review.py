"""Audit private exact4 census; bind layers to the original chart bundle.

Never reads returns or simulates positions. Private inputs/outputs stay local.
The reviewed viewer is a NEW COPY; index.html and the C0 layer stay untouched.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from gc_exact4_variants import resolve

PROFILES = ("C1_EXACT4", "C2_EXACT4_DENSAS",
            "C3_EXACT4_SEPARADAS", "C4_EXACT4_PLANAS")
SCHEMA = "edgelab.gc_exact4.review_layer/1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def audit(folder):
    folder = Path(folder)
    evidence = read(folder / "evidence.json")
    base = read(folder / "gc_exact4_baseline_local.json")
    resolved = read(folder / "resolved_configs.json")
    require(sha(folder / "gc_exact4_baseline_local.json") ==
            evidence["baseline_file_sha256"], "BASELINE_BYTES_HASH_FAIL")
    require(resolve(base) == resolved, "RESOLVED_CONFIGS_OR_HASH_FAIL")
    require(base["window"]["bars"] == evidence["bars"], "BAR_COUNT_FAIL")
    require(evidence.get("outcomes_computed") is False and
            evidence.get("current_detector_C0_not_replaced") is True,
            "TARGETFREE_SCOPE_FAIL")
    require([r["id"] for r in evidence["results"]] ==
            ["C0_ACTUAL", *PROFILES], "PROFILE_SET_FAIL")
    require(evidence["results"][0]["status"] ==
            "ABSTAIN_USE_CURRENT_DETECTOR_FOR_C0", "C0_NOT_ABSTAINED")
    report = dict(
        scope="GC_EXACT4_PRIVATE_PACKET_AUDIT_NOT_RAW_REPLAY",
        bars=evidence["bars"], baseline_verified=True, configs_verified=True,
        chart_bundle_present=False, bars_jsonl_present=False,
        publication_verdict="ABSTAIN_MISSING_RAW_PUBLICATION_METADATA",
        raw_code_hash_match={}, input_hashes={}, profiles=[],
        outcomes_computed=False, financial_use_certified=False)
    code_map = {"gc_exact4_prepare.py": "code_sha256",
                "escalonadas_exact4.py": "core_sha256",
                "gc_exact4_variants.py": "resolver_sha256"}
    for name, field in code_map.items():
        data = Path(__file__).with_name(name).read_bytes()
        lf = data.replace(b"\r\n", b"\n")
        variants = {"exact_bytes": data, "LF": lf,
                    "CRLF": lf.replace(b"\n", b"\r\n")}
        matches = [k for k, b in variants.items()
                   if hashlib.sha256(b).hexdigest() == evidence[field]]
        require(bool(matches), "CODE_HASH_FAIL:" + name)
        report["raw_code_hash_match"][name] = matches
    all_events = {}
    for row in evidence["results"][1:]:
        ident = row["id"]
        path = folder / (ident + "_events_private.jsonl")
        with path.open(encoding="utf-8-sig") as f:
            events = [json.loads(line) for line in f if line.strip()]
        cfg = next(p for p in resolved["profiles"] if p["id"] == ident)
        used = {"H": set(), "L": set()}
        ids, sessions, kinds = set(), Counter(), Counter()
        for e in events:
            require(e["kind"] in used and e["id"] not in ids, "ID_KIND_FAIL")
            ids.add(e["id"])
            members, known = e["members"], e["members_known_at"]
            require(len(members) == len(known) == e["n_peaks"] ==
                    e["det_pico"] == 4, "EXACT_FOUR_FAIL")
            require(all(type(v) is int for v in members + known),
                    "INTEGER_INDEX_FAIL")
            require(members == sorted(set(members)), "PEAK_ORDER_FAIL")
            require(known == sorted(known), "KNOWLEDGE_ORDER_FAIL")
            require(all(0 <= q < j <= e["det_i"] < evidence["bars"]
                        for q, j in zip(members, known)), "PREFIX_ORDER_FAIL")
            require(e["pico4_i"] == members[-1] and
                    e["pico4_known_bar_i"] == known[-1] == e["det_i"] ==
                    e["logical_available_bar_i"], "FOURTH_CONFIRMATION_FAIL")
            require(not used[e["kind"]].intersection(members),
                    "REUSED_MEMBER_FAIL")
            used[e["kind"]].update(members)
            sign = 1 if e["kind"] == "H" else -1
            require(e["confirmation_mode"] == "precio" and
                    e["trigger_tick"] ==
                    e["level_tick"] - sign * cfg["params"]["confirm_ticks"],
                    "TRIGGER_FAIL")
            require(e["lower_tick"] <= e["level_tick"] <= e["upper_tick"],
                    "BOUNDS_FAIL")
            require(e["raw_publication_row"] is None and
                    e["raw_publication_ts_us"] is None and
                    e["publication_metadata_pass"] is False,
                    "PACKET_PUBLICATION_SCOPE_CHANGED_REAUDIT_REQUIRED")
            require(e["outcome_computed"] is False and
                    e["financial_use_certified"] is False, "FINANCIAL_FLAG_FAIL")
            sessions[e["session_id"]] += 1
            kinds[e["kind"]] += 1
        stats = row["counts"]
        require(len(events) == stats.get("zones", 0), "EVENT_COUNT_FAIL")
        require(all(kinds[k] == stats.get("zones_" + k, 0) for k in used),
                "SIDE_COUNT_FAIL")
        require(all(sessions[k] == v for k, v in row["per_session"].items())
                and set(sessions).issubset(row["per_session"]),
                "SESSION_COUNT_FAIL")
        incomplete = sum(v for k, v in stats.items()
                         if k.startswith("incomplete_peaks_"))
        require(stats.get("rejected_four_blocks", 0) == 0 and
                stats["eligible_peaks"] == 4 * len(events) + incomplete,
                "PEAK_ACCOUNTING_FAIL")
        require(row["publications_metadata_pass"] == 0 and
                row["outcomes_computed"] is False, "RESULT_SCOPE_FAIL")
        counts = list(sessions.values())
        report["profiles"].append(dict(
            id=ident, zones=len(events), H=kinds["H"], L=kinds["L"],
            nonempty_sessions=len(sessions), listed_sessions=len(row["per_session"]),
            zero_event_sessions=[k for k, v in row["per_session"].items() if not v],
            min_per_nonempty_session=min(counts) if counts else None,
            max_per_session=max(counts) if counts else None,
            per_session=row["per_session"], exact4_members_pass=True,
            unique_members_per_side_pass=True, missing_publication=len(events),
            event_file_sha256=sha(path)))
        all_events[ident] = events
    for path in sorted(folder.glob("*")):
        if path.is_file() and path.suffix in (".json", ".jsonl"):
            report["input_hashes"][path.name] = sha(path)
    return report, base, resolved, all_events


def layer(base, profile, events, bundle):
    require(bundle.get("meta", {}).get("tick_size") == base["tick_size"],
            "BUNDLE_TICK_SIZE_FAIL")
    candles = bundle.get("bar_series", {}).get(base["bar_series"], {}).get("candles")
    require(candles and len(candles) == base["window"]["bars"], "BUNDLE_SERIES_FAIL")
    require(candles[0]["time"] == base["window"]["first_bar_time"] and
            candles[-1]["time"] == base["window"]["last_bar_time"],
            "BUNDLE_WINDOW_FAIL")
    tick = base["tick_size"]
    zones = []
    for e in events:
        q = e["members"]
        field = "high" if e["kind"] == "H" else "low"
        px = [candles[i][field] for i in q]
        ticks = [round(v / tick) for v in px]
        require(all(abs(v / tick - t) < 1e-6 for v, t in zip(px, ticks)),
                "BUNDLE_PRICE_OFF_TICK")
        require(ticks[-1] == e["level_tick"] and
                min(ticks) == e["lower_tick"] and max(ticks) == e["upper_tick"],
                "EVENT_BUNDLE_PEAK_PARITY_FAIL")
        det = candles[e["det_i"]]
        require(det["time"] == e["logical_available_time"], "DETECTION_TIME_FAIL")
        for i in q + [e["det_i"]]:
            c = candles[i]
            require(c["time"] <= det["time"] and c["low"] <= c["close"] <= c["high"],
                    "BUNDLE_OHLC_OR_PREFIX_FAIL")
        # det_precio is the observed bar close, NEVER an inferred trigger fill.
        zones.append(dict(
            id=e["id"], kind=e["kind"], session_id=e["session_id"],
            i0=q[0], i1=q[-1], t0=candles[q[0]]["time"], t1=candles[q[-1]]["time"],
            p0=min(px), p1=max(px), toques=4,
            picos=[[i, candles[i]["time"], candles[i][field]] for i in q],
            det_idx=3, det_pico=4, det_i=e["det_i"], det_t=det["time"],
            det_precio=det["close"], det_nivel=px[-1],
            members_known_at=e["members_known_at"],
            trigger_reference_price=e["trigger_tick"] * tick,
            publication_scope=e["publication_scope"],
            targetfree_only=True, financial_use_certified=False,
            publication_metadata_pass=False, outcome_computed=False))
    return dict(schema=SCHEMA, asset=base["asset"], bar_key=base["bar_series"],
                tick_size=tick, targetfree_only=True, financial_use_certified=False,
                variante=profile["id"] + " · cuatro congelados · DET lógico; raw pendiente",
                parametros=profile["params"], profile_sha256=profile["profile_sha256"],
                binding=dict(chart_bundle_sha256=base["chart_bundle_sha256"],
                             window=base["window"]),
                zonas=zones, candidatas=[], outcomes_computed=False)


def safe_viewer_copy(text):
    """Small exact-match edits; unrelated local modifications are preserved."""
    require("GC_EXACT4_REVIEW_COPY_V1" not in text, "USE_ORIGINAL_INDEX_NOT_COPY")
    replacements = [
        ('<script src="vendor/lightweight-charts.standalone.production.js"></script>',
         '<script src="vendor/lightweight-charts.standalone.production.js"></script>\n'
         '<script src="gc_exact4_review_guard.js"></script>'),
        ('.then(function (d) { peaksDet.data = d; var el = document.getElementById("lbl-det-status");',
         '.then(function (d) { if (state.currentAssetId !== aid) return; '
         'GCExact4Review.validate(d, state.data, state.activeBarKey, aid); '
         'peaksDet.data = d; var el = document.getElementById("lbl-det-status");'),
        ('.catch(function () { var el = document.getElementById("lbl-det-status"); if (el) el.textContent = "Sin detecciones para este activo (tools/peaks_learn.py)."; });',
         '.catch(function (error) { peaksDet.data = null; GCExact4Review.block(error && error.message || "No se pudo cargar la capa exact4"); });'),
        ('function posCompute(z, cd, slT, tpR, beR, tkz) {',
         'function posCompute(z, cd, slT, tpR, beR, tkz) {\n'
         '    throw new Error("GC_EXACT4_TARGETFREE_NO_POSITION_COMPUTATION");'),
        ('function posDashboard(cd) {', 'function posDashboard(cd) {\n    return;'),
        ('function drawPeaksDet(ctx, cd, vr, X, Y) {',
         'function drawPeaksDet(ctx, cd, vr, X, Y) {\n'
         '    if (peaksDet.data && !GCExact4Review.canDraw(peaksDet.data, '
         'state.data, state.activeBarKey, state.currentAssetId)) return;'),
        ('if (isFinite(slT) && isFinite(tpR) && slT > 0 && tpR > 0) {',
         'if (false && isFinite(slT) && isFinite(tpR) && slT > 0 && tpR > 0) {'),
        ('ctx.fillText("DET p" + z.det_pico,',
         'ctx.fillText("DET lógico p" + z.det_pico,'),
        ('function indApplyAll() {', 'function indApplyAll() {\n'
         '    INDICATORS.forEach(function (ind) { if (ind.isOn()) ind.set(false); });\n'
         '    peaksDet.on = true;\n'
         '    var check = document.getElementById("chk-det"); if (check) check.checked = true;\n'
         '    requestDraw(); return;'),
        ('function switchTimeframe(key) {', 'function switchTimeframe(key) {\n'
         '    if (key !== "tick_25") { GCExact4Review.block("Sólo tick_25 para esta revisión"); return; }'),
        ('function loadAsset(aid, options) {', 'function loadAsset(aid, options) {\n'
         '    if (aid !== GCExact4Review.asset) { GCExact4Review.block("Sólo el activo GC capturado"); return; }'),
        ('function tbzxCompute() {', 'function tbzxCompute() { return;'),
        ('function evxCompute() {', 'function evxCompute() { return;'),
        ('function axfCompute() {', 'function axfCompute() { return;'),
        ('function espejoCompute() {', 'function espejoCompute() { return;'),
        ('function renderParity() {',
         'function renderParity() {\n'
         '    var pill = document.getElementById("parity-pill");\n'
         '    if (pill) { pill.textContent = "RAW PENDIENTE"; pill.style.background = "#92400e"; }\n'
         '    var body = document.getElementById("paritybody");\n'
         '    if (body) body.textContent = "Revisión geométrica exact4. Disponibilidad raw y ejecución no certificadas. Sin retornos ni posiciones.";\n'
         '    return;'),
    ]
    for old, new in replacements:
        require(text.count(old) == 1, "VIEWER_HOOK_CHANGED:" + old)
        text = text.replace(old, new, 1)
    curtain = ('var lp = z.picos && z.picos.length ? z.picos[z.picos.length - 1] : '
               '[z.i1, z.t1], cx = XI(lp[0] + 2, cd[lp[0] + 2] ? cd[lp[0] + 2].time : lp[1]);')
    require(text.count(curtain) == 1, "REVIEW_CURTAIN_HOOK_CHANGED")
    text = text.replace(curtain,
        'var cut = z.det_i + 1, cx = cut < cd.length ? XI(cut, cd[cut].time) : w;')
    require(text.count("</head>") == 1, "VIEWER_HEAD_HOOK_CHANGED")
    text = text.replace("</head>", """
<style id="gc-exact4-review-css">
#lbl-det-status,#lbl-rev-status{font-size:14px!important;line-height:1.45}
#pop-bt2a-params .pop-body>div:not(#lab-panel):not(#lab-anchor){display:none}
@media(max-width:600px){
 #pop-bt2a-params{left:16px!important;width:calc(100vw - 32px)!important;max-height:75vh}
 #pop-bt2a-params .pop-body{padding:8px!important}
 #lab-panel button{min-height:44px}
}
</style>
</head>""", 1)
    return '<!-- GC_EXACT4_REVIEW_COPY_V1: geometry only; index.html unchanged -->\n' + text


def export(folder, bundle_path, viewer_dir, install=False):
    report, base, resolved, events = audit(folder)
    require(sha(bundle_path) == base["chart_bundle_sha256"], "CHART_BUNDLE_BYTES_HASH_FAIL")
    bundle = read(bundle_path)
    viewer = Path(viewer_dir)
    require((viewer / "bundles" / (base["asset"] + ".json")).resolve() ==
            Path(bundle_path).resolve(), "USE_BUNDLE_SERVED_BY_THIS_VIEWER")
    out = viewer / "bundles" / "peaks_det"
    planned = []
    for p in resolved["profiles"][1:]:
        require(p["id"] in PROFILES, "PROFILE_FAIL")
        suffix = "exact4_" + p["id"].split("_")[0].lower()
        dest = out / (base["asset"] + "__" + suffix + ".json")
        require(not dest.exists(), "DO_NOT_OVERWRITE_LAYER:" + str(dest))
        planned.append((dest, layer(base, p, events[p["id"]], bundle)))
    copy_path = viewer / "index_gc_exact4.html"
    copy_text = None
    if install:
        require(not copy_path.exists(), "DO_NOT_OVERWRITE_REVIEW_COPY")
        guard = viewer / "gc_exact4_review_guard.js"
        require(guard.exists(), "COPY_REVIEW_GUARD_FROM_DELIVERY_FIRST")
        copy_text = safe_viewer_copy((viewer / "index.html").read_text(encoding="utf-8-sig"))
    out.mkdir(parents=True, exist_ok=True)
    for dest, payload in planned:
        with dest.open("x", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    if copy_text is not None:
        with copy_path.open("x", encoding="utf-8") as f:
            f.write(copy_text)
    report["chart_bundle_present"] = True
    report["chart_bundle_hash_verified"] = True
    report["event_peak_geometry_bound"] = True
    report["layers"] = [{"path": str(p), "sha256": sha(p)} for p, _ in planned]
    report["source_viewer_sha256"] = sha(viewer / "index.html")
    report["source_viewer_unchanged"] = True
    report["review_links"] = [
        "index_gc_exact4.html?asset=" + base["asset"] +
        "&tf=tick_25&solo=det&det=exact4_" + p["id"].split("_")[0].lower()
        for p in resolved["profiles"][1:]]
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--census-dir", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--chart-bundle")
    ap.add_argument("--viewer-dir")
    ap.add_argument("--install-safe-copy", action="store_true")
    a = ap.parse_args()
    require(not Path(a.report).exists(), "DO_NOT_OVERWRITE_REPORT")
    if a.chart_bundle:
        require(bool(a.viewer_dir), "VIEWER_DIR_REQUIRED")
        result = export(a.census_dir, a.chart_bundle, a.viewer_dir, a.install_safe_copy)
    else:
        require(not a.install_safe_copy, "BUNDLE_REQUIRED_FOR_INSTALL")
        result = audit(a.census_dir)[0]
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    with Path(a.report).open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"scope": result["scope"], "profiles": len(result["profiles"]),
                      "publication_verdict": result["publication_verdict"],
                      "outcomes_computed": False}))


if __name__ == "__main__":
    main()