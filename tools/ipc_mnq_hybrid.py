#!/usr/bin/env python3
"""MNQ IPC hybrid v0.1: geometry only, append-only causal events.

No NQ/MES detector is modified. Bars must be CLOSED and on the tick grid.
Snapshot geometry is visual-only; reconstruct live state from events and
available_i, never from the final zone record or retrospective origin i0.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import hashlib
import json
import math


@dataclass(frozen=True)
class Config:
    w: int = 1
    max_gap_bars: int = 60
    max_step_ticks: int = 7
    min_pull_ticks: int = 7
    visit_exit_ticks: int = 14
    max_width_ticks: int = 21
    evidence_threshold: int = 6
    visit_bonus: int = 2
    min_peaks: int = 3
    max_clock_gap_s: int = 1800

    def validate(self):
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 1
               for v in asdict(self).values()):
            raise ValueError("config values must be positive integers")
        if self.max_gap_bars <= self.w or self.visit_exit_ticks <= self.min_pull_ticks:
            raise ValueError("gap must exceed pivot lag; visit exit must exceed small pull")
        if self.max_width_ticks < self.max_step_ticks:
            raise ValueError("total width cannot be smaller than one allowed step")


def detect(bars, cfg=Config(), tick_size=0.25):
    """bars: session(str), high_ticks(int), low_ticks(int), closed_at(number).

    Confirmation uses w closed bars to the right; extrema on an equal-height
    plateau count once (last plateau maximum with a strictly lower right side).
    No intrabar ordering is inferred. Pull/visit excursion excludes BOTH
    endpoint bars, so a wide peak bar cannot create a fictitious extra visit.
    """
    cfg.validate()
    if not math.isfinite(tick_size) or tick_size <= 0:
        raise ValueError("invalid tick size")
    for i, b in enumerate(bars):
        if not isinstance(b.get("session"), str) or not b["session"]:
            raise ValueError("explicit session ID required")
        for k in ("high_ticks", "low_ticks"):
            if not isinstance(b.get(k), int) or isinstance(b[k], bool):
                raise ValueError("tick prices must be integers")
        if b["high_ticks"] < b["low_ticks"]:
            raise ValueError("inverted bar")
        if not math.isfinite(b.get("closed_at", math.nan)) or not math.isfinite(b.get("chart_time", math.nan)):
            raise ValueError("closed_at required")
        if b["closed_at"] < b["chart_time"]:
            raise ValueError("close precedes candle time")
        if b["low_ticks"] <= 0:
            raise ValueError("nonpositive MNQ price")
        if i and b["closed_at"] < bars[i-1]["closed_at"]:
            raise ValueError("clock inversion: do not sort/deduplicate silently")
        if i and b["chart_time"] < bars[i-1]["chart_time"]:
            raise ValueError("chart clock inversion")
    events, zones = [], {}
    active = {}
    candidates = {"H": None, "L": None}
    ordinal = 0
    previous_session = None

    def emit(kind, j, z, reason=None):
        e = {"event": kind, "available_i": j, "available_at": bars[j]["closed_at"],
             "zone_id": z["id"], "session": z["session"]}
        if reason:
            e["reason"] = reason
        if kind in ("CREATE", "UPDATE"):
            e["state"] = {k: z[k] for k in
                          ("kind", "i0", "lo_ticks", "hi_ticks", "last_peak_i",
                           "peaks_count", "visits", "evidence", "route")}
            e["state"]["peaks"] = [dict(p) for p in z["peaks"]]
        events.append(e)

    def close(z, j, reason):
        z["status"] = reason
        z["closed_i"] = j
        z["closed_at"] = bars[j]["closed_at"]
        active.pop(z["id"], None)
        emit("CLOSE", j, z, reason)

    for j, bar in enumerate(bars):
        data_gap = j > 0 and bar["chart_time"]-bars[j-1]["chart_time"] > cfg.max_clock_gap_s
        if previous_session is not None and (bar["session"] != previous_session or data_gap):
            for zid in list(active):
                close(zones[zid], j, "DATA_GAP" if data_gap and bar["session"] == previous_session else "SESSION_END")
            candidates = {"H": None, "L": None}
        previous_session = bar["session"]
        # Raw wick crossing is known at bar close, independent of pivot detection.
        for zid in list(active):
            z = zones[zid]
            value = bar["high_ticks"] if z["kind"] == "H" else -bar["low_ticks"]
            last = z["peaks"][-1]["signed_ticks"]
            if value > last:
                close(z, j, "BROKEN")
            elif j - z["last_peak_i"] > cfg.max_gap_bars:
                close(z, j, "EXPIRED")
        for kind, sign in (("H", 1), ("L", -1)):
            x = lambda i: bars[i]["high_ticks"] if kind == "H" else -bars[i]["low_ticks"]
            y = lambda i: bars[i]["low_ticks"] if kind == "H" else -bars[i]["high_ticks"]
            c = candidates[kind]
            if c and (x(j) > c["peaks"][-1]["signed_ticks"]
                      or j - c["peaks"][-1]["i"] > cfg.max_gap_bars
                      or (c["zone_id"] and zones[c["zone_id"]]["status"] != "ACTIVE")):
                c = None
                candidates[kind] = None
            q = j - cfg.w
            if q < cfg.w:
                continue
            window = range(q-cfg.w, j+1)
            if any(bars[i]["session"] != bar["session"] for i in window):
                continue
            if any(bars[i]["chart_time"]-bars[i-1]["chart_time"] > cfg.max_clock_gap_s
                   for i in range(q-cfg.w+1,j+1)):
                continue
            px = x(q)
            if not (all(px >= x(i) for i in range(q-cfg.w, q))
                    and all(px > x(i) for i in range(q+1, j+1))):
                continue
            p = {"i": q, "confirmed_i": j, "confirmed_at": bar["closed_at"],
                 "price_ticks": sign*px, "signed_ticks": px}
            if c:
                last = c["peaks"][-1]
                step = last["signed_ticks"] - px
                # Large inwards step/width starts another level; previous zone
                # remains independently active until crossing or expiration.
                width = abs(c["peaks"][0]["signed_ticks"]-px)
                if step < 0 or step > cfg.max_step_ticks or width > cfg.max_width_ticks:
                    c = None
                else:
                    between = range(last["i"]+1, q)
                    if not between:
                        continue
                    pull = last["signed_ticks"] - min(y(i) for i in between)
                    if pull < cfg.min_pull_ticks:
                        continue
                    if pull >= cfg.visit_exit_ticks:
                        c["visits"] += 1
                    c["peaks"].append(p)
            if c is None:
                c = {"peaks": [p], "visits": 1, "zone_id": None}
            candidates[kind] = c
            n = len(c["peaks"])
            evidence = n + cfg.visit_bonus*(c["visits"]-1)
            if n < cfg.min_peaks or evidence < cfg.evidence_threshold:
                continue
            route = ("SPACED" if c["visits"] >= 3 else
                     "MIXED" if c["visits"] == 2 else "DENSE")
            if c["zone_id"] is None:
                ordinal += 1
                zid = f"MNQ-HYB:{bar['session']}:{kind}:{ordinal}"
                c["zone_id"] = zid
                z = {"id": zid, "kind": kind, "session": bar["session"],
                     "created_i": j, "created_at": bar["closed_at"],
                     "status": "ACTIVE", "closed_i": None, "closed_at": None}
                zones[zid] = z
                active[zid] = None
                event = "CREATE"
            else:
                z = zones[c["zone_id"]]
                event = "UPDATE"
            ps = [dict(p) for p in c["peaks"]]
            z.update(i0=ps[0]["i"], last_peak_i=ps[-1]["i"],
                     lo_ticks=min(p["price_ticks"] for p in ps),
                     hi_ticks=max(p["price_ticks"] for p in ps),
                     peaks_count=n, visits=c["visits"], evidence=evidence,
                     route=route, peaks=ps)
            emit(event, j, z)
    # Viewer compatibility: origin geometry is retrospective but explicitly
    # separated from creation. Counts are peaks, visits has its own field.
    visual = []
    for z in zones.values():
        visual.append(dict(
            zone_id=z["id"], kind=z["kind"], i0=z["i0"], i1=z["last_peak_i"],
            t0=bars[z["i0"]]["chart_time"], t1=bars[z["last_peak_i"]]["chart_time"],
            p0=z["lo_ticks"]*tick_size, p1=z["hi_ticks"]*tick_size,
            toques=z["peaks_count"], visitas=z["visits"], evidence=z["evidence"],
            route=z["route"], creation_i=z["created_i"],
            available_at=z["created_at"], status=z["status"],
            closed_i=z["closed_i"], closed_at=z["closed_at"],
            picos=[[p["i"], bars[p["i"]]["chart_time"], p["price_ticks"]*tick_size]
                   for p in z["peaks"]],
            confirmations=[dict(i=p["i"], confirmed_i=p["confirmed_i"],
                                confirmed_at=p["confirmed_at"]) for p in z["peaks"]],
            final_geometry_visual_only=True))
    return dict(schema="EDGELAB_IPC_MNQ_HYBRID_V01",
                variante="MNQ IPC híbrido · BORRADOR NO VALIDADO",
                parametros=asdict(cfg), tick_size=tick_size,
                outcomes_computed=False, calibration="DRAFT_NO_MNQ_HUMAN_LABELS",
                causal_contract="closed bars; append-only events; pivot available at i+w",
                zonas=visual, events=events)


def to_ticks(value, tick):
    x = float(value)/tick
    if not math.isfinite(x) or abs(x-round(x)) > 1e-6:
        raise ValueError("off-grid price: refusing silent rounding")
    return int(round(x))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="canonical MNQ bundle JSON")
    ap.add_argument("--output", required=True, help="separate IPC layer, never overwrite source bundle")
    ap.add_argument("--series", default="tick_25")
    ap.add_argument("--session-id", help="one known session only; span <=24h")
    ap.add_argument("--sessions-json", help="JSON array of explicit session IDs per source candle")
    ap.add_argument("--config", help="draft config JSON; no automatic fitting")
    a = ap.parse_args()
    source, out = Path(a.input), Path(a.output)
    if source.resolve() == out.resolve():
        raise ValueError("cannot overwrite source")
    raw = source.read_bytes()
    bundle = json.loads(raw)
    meta = bundle.get("meta", {})
    asset = str(bundle.get("asset") or meta.get("asset") or meta.get("instrument") or source.stem)
    if not asset.upper().startswith("MNQ"):
        raise ValueError("MNQ only: do not use NQ data as MNQ")
    tick = float(meta.get("tick_size", 0))
    if abs(tick-0.25) > 1e-12:
        raise ValueError("MNQ tick grid must be explicitly declared as 0.25")
    candles = bundle["bar_series"][a.series]["candles"]
    if len(candles) < 3:
        raise ValueError("insufficient bars")
    times = [float(c["time"]) for c in candles]
    if any(not math.isfinite(t) for t in times) or any(b < a for a,b in zip(times,times[1:])):
        raise ValueError("invalid chart timestamps; preserve duplicate ordering")
    if a.sessions_json:
        sessions = json.loads(Path(a.sessions_json).read_text())
        if len(sessions) != len(candles) or not all(isinstance(s,str) and s for s in sessions):
            raise ValueError("sessions array must match every source candle")
    elif a.session_id:
        if times[-1]-times[0] > 86400:
            raise ValueError("monthly bundle needs explicit --sessions-json, not one session ID")
        sessions = [a.session_id]*len(candles)
    elif all(isinstance(c.get("session"),str) and c["session"] for c in candles):
        sessions = [c["session"] for c in candles]
    else:
        raise ValueError("need --sessions-json, --session-id or per-candle session; do not infer CME dates")
    cfg = Config(**json.loads(Path(a.config).read_text())) if a.config else Config()
    bars = []
    for i, c in enumerate(candles):
        # Explicit close wins. Otherwise next candle's opening is a conservative
        # availability boundary; the final unconfirmed candle is omitted.
        if c.get("closed_at") is not None:
            closed_at = float(c["closed_at"])
        elif i+1 < len(candles) and sessions[i+1] == sessions[i]:
            closed_at = times[i+1]
        else:
            # Keep a boundary sentinel with no geometry? No: omit the last bar
            # of each session and retain source_i mapping for displayed peaks.
            continue
        if closed_at < times[i]:
            raise ValueError("closed_at precedes candle time")
        bars.append(dict(session=sessions[i], high_ticks=to_ticks(c["high"],tick),
                         low_ticks=to_ticks(c["low"],tick), chart_time=times[i],
                         closed_at=closed_at, source_i=i))
    result = detect(bars,cfg,tick)
    # Remap compact indices to the immutable source candle indices.
    index = lambda n: None if n is None else bars[n]["source_i"]
    for e in result["events"]:
        e["available_i"] = index(e["available_i"])
        if "state" in e:
            st=e["state"]; st["i0"]=index(st["i0"]);st["last_peak_i"]=index(st["last_peak_i"])
            for p in st["peaks"]:
                p["i"]=index(p["i"]);p["confirmed_i"]=index(p["confirmed_i"])
    for z in result["zonas"]:
        for k in ("i0","i1","creation_i","closed_i"):
            z[k]=index(z[k])
        for p in z["picos"]:
            p[0]=index(p[0])
        for p in z["confirmations"]:
            p["i"]=index(p["i"]);p["confirmed_i"]=index(p["confirmed_i"])
    result.update(asset=asset, bar_series=a.series, input_sha256=hashlib.sha256(raw).hexdigest(),
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  source_bars=len(candles), closed_bars=len(bars),
                  availability_policy="explicit closed_at else next same-session candle opening",
                  config_sha256=hashlib.sha256(json.dumps(asdict(cfg),sort_keys=True).encode()).hexdigest(),
                  review_only=True)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({"asset":asset,"zones":len(result["zonas"]),"closed_bars":len(bars),
                      "outcomes_computed":False,"output":str(out)}))


if __name__ == "__main__":
    main()