"""HFTZones2 v2.1 — traduccion 1:1 del kernel NT8 (HFTZones2.cs).

Motor de rachas tick-driven con calibracion adaptativa por sesion (congelada
intra-sesion), muestreo determinista con stride, cuantil exacto sin
interpolacion y ciclo de vida tick-exacto. FIX#1 (durSec>=1ms), FIX#2 (solo
intervalos internos en msList), FIX#3 (isSweep por altura) replicados.

Sesiones: calendario CME ETH (sessions.py) en lugar del SessionIterator de
NT8. Feriados no modelados: cualquier discrepancia aparece en paridad como
CALIBRATION_DIFF y se resuelve alli (declarado).

Fidelidad 1:1 verificada contra Hftzones2.txt (AMejorasIndicadoresVectorbt/):
- FIX#1 dur_sec = max(total_ms, 1.0)/1000 (ráfagas sub-ms).
- FIX#2 ms_list solo intervalos INTERNOS de la racha (append en continue_streak).
- FIX#3 is_sweep = height_ticks >= min_sweep_ticks.
- Recalibración solo si len(ms)>=100 y len(vol)>=100 y seen>=MinCalibSamples;
  si no alcanza se mantiene la calibración previa (o sigue pending).
- CALIBRATION_PENDING una vez, en la primera sesión sin calibración (sin
  fallback silencioso). En modo manual calib_ready=True, calib_id=0 de arranque.
- Sampler: decimación determinista por stride con duplicación al llegar al cap
  (jamás muestreo aleatorio); cuantiles exactos sin interpolación.

Requisito de paridad real (ver docs/nt8_indicator_parity_contract.md §5): el
rango debe arrancar en borde de sesión con AL MENOS una sesión completa previa,
para que exista una calibración congelada antes de las detecciones que se
comparan; si no, la primera sesión emite CALIBRATION_PENDING y no crea zonas.
"""
from __future__ import annotations

import math

from .. import sessions
from ..common import fnum, ns_to_ms, quantile_exact, tick_and_bar_events, ts_str, tz_of

NAME = "HFTZones2"

DEFAULTS = dict(
    adaptive_mode=True,
    # A. Estructura
    min_pasos=8, min_absorb_pasos=6, detect_absorb=True, fallos_tolerados=1,
    min_sweep_ticks=4, use_relative_retro=True, retro_floor_ticks=2, retro_pct_height=50.0,
    # B. Calibracion adaptativa
    q_predator=0.02, q_ultra=0.05, q_max_avg=0.15, pause_mult=5.0,
    total_ms_mult=2.0, vol_mult_median_tick=3.0, pause_exclude_ms=1000.0,
    min_calib_samples=5000, calib_sample_cap=262144,
    # C. Manual (solo adaptive_mode=False)
    manual_predator_ms=5.0, manual_ultra_ms=15.0, manual_max_avg_ms=25.0,
    manual_max_pausa_ms=100.0, manual_max_total_ms=500.0,
    manual_min_vol_rate=100.0, manual_min_total_vol=50.0,
    # D. Ciclo de vida
    invalidation_mode="CloseThrough", penetration_ticks=1, max_touches=0,
    max_age_bars=2000, zone_height_ticks=1, max_logged_touches=20,
    min_export_valid_steps=5,
)

HEADER = ("event_seq,event_type,ts,unix_ms,zone_id,calib_id,dir,bucket,upper,lower,"
          "height_ticks,pasos,valid_steps,avg_ms,total_ms,vol_rate,total_vol,"
          "max_retro_ticks,touches,reason,extra")


class _Sampler:
    """AddSample de NT8: decimacion determinista por stride, cap con mitades."""

    def __init__(self, cap):
        self.cap = cap
        self.stride = 1
        self.seen = 0
        self.vals = []

    def add(self, v):
        self.seen += 1
        if self.seen % self.stride != 0:
            return
        if len(self.vals) >= self.cap:
            self.vals = self.vals[1::2]
            self.stride *= 2
        self.vals.append(v)

    def clear(self):
        self.vals = []
        self.stride = 1
        self.seen = 0


def run(ticks, bars, params=None, chart_tz="UTC"):
    p = {**DEFAULTS, **(params or {})}
    tz = tz_of(chart_tz)
    tick_size = ticks.tick_size

    rows, lines, zones, obs_events = [], [], [], []
    seq = 0
    next_zone_id = 0
    closed_bar = -1

    # Estado de sesion / calibracion
    sess_end = None
    ms_s = _Sampler(int(p["calib_sample_cap"]))
    vol_s = _Sampler(int(p["calib_sample_cap"]))
    calib_id = 0
    calib_ready = False
    res_limited = False
    pending_logged = False
    eff = dict(pred=0.0, ultra=0.0, max_avg=0.0, max_pausa=0.0, max_total=0.0,
               min_vol_rate=0.0, min_total_vol=0.0)
    if not p["adaptive_mode"]:
        eff = dict(pred=p["manual_predator_ms"], ultra=p["manual_ultra_ms"],
                   max_avg=p["manual_max_avg_ms"], max_pausa=p["manual_max_pausa_ms"],
                   max_total=p["manual_max_total_ms"], min_vol_rate=p["manual_min_vol_rate"],
                   min_total_vol=p["manual_min_total_vol"])
        calib_ready = True

    # Estado de racha
    st = dict(dir=0, streak=0, valid=0, fails=0, swh=0.0, swl=0.0,
              total_vol=0.0, max_retro=0.0, ms_list=[], t_start=0, t_last=0)

    tns, pticks, vols = ticks.ts_ns, ticks.price_ticks, ticks.volume

    def log(etype, t_ns, z, reason="", extra=""):
        nonlocal seq
        seq += 1
        if z is not None:
            zid = "Z" + format(z["id"], "06d") if z["id"] > 0 else ""
            zone_fields = [zid, str(z["calib_id"]), str(z["dir"]), z["bucket"],
                           fnum(z["upper"], 6), fnum(z["lower"], 6), str(z["height_ticks"]),
                           str(z["pasos"]), str(z["valid_steps"]), fnum(z["avg_ms"], 3),
                           fnum(z["total_ms"], 1), fnum(z["vol_rate"], 2), fnum(z["total_vol"], 2),
                           fnum(z["max_retro"], 1), str(z["touches"])]
        else:
            zid = None
            zone_fields = [""] * 15
        lines.append(",".join([str(seq), etype, ts_str(t_ns, tz), str(ns_to_ms(t_ns))]
                              + zone_fields + [reason or "", extra or ""]))
        rows.append(dict(seq=seq, type=etype, ts_ns=int(t_ns), unix_ms=ns_to_ms(t_ns),
                         zone_id=zid if (z is not None and z["id"] > 0) else None,
                         reason=reason, extra=extra))
        if z is not None and z["id"] > 0:
            z["timeline"].append(dict(ms=ns_to_ms(t_ns), type=etype, extra=extra or reason))

    def recalibrate(t_ns):
        nonlocal calib_id, calib_ready, res_limited, eff
        ms = sorted(ms_s.vals)
        vv = sorted(vol_s.vals)
        q_pred = quantile_exact(ms, p["q_predator"])
        q_ult = quantile_exact(ms, p["q_ultra"])
        q_max = quantile_exact(ms, p["q_max_avg"])
        p50 = quantile_exact(ms, 0.50)
        med_v = quantile_exact(vv, 0.50)
        zero_count = 0
        for v in ms:
            if v <= 0:
                zero_count += 1
            else:
                break
        frac_zero = zero_count / len(ms) if ms else 1.0
        eff["pred"] = max(1.0, q_pred)
        eff["ultra"] = max(eff["pred"], q_ult)
        eff["max_avg"] = max(eff["ultra"], q_max)
        eff["max_pausa"] = min(5000.0, max(eff["max_avg"], p["pause_mult"] * max(1.0, p50)))
        eff["max_total"] = eff["max_avg"] * p["min_pasos"] * p["total_ms_mult"]
        eff["min_total_vol"] = p["vol_mult_median_tick"] * med_v * p["min_pasos"]
        eff["min_vol_rate"] = eff["min_total_vol"] / (eff["max_total"] / 1000.0)
        res_limited = p50 <= 0.0
        calib_id += 1
        calib_ready = True
        extra = ("n_ms={0};n_vol={1};stride_ms={2};frac_zero_ms={3};p50_ms={4};"
                 "median_tick_vol={5};eff_predator_ms={6};eff_ultra_ms={7};eff_max_avg_ms={8};"
                 "eff_max_pausa_ms={9};eff_max_total_ms={10};eff_min_total_vol={11};"
                 "eff_min_vol_rate={12};resolution_limited={13}").format(
            len(ms), len(vv), ms_s.stride, fnum(frac_zero, 4), fnum(p50, 2), fnum(med_v, 2),
            fnum(eff["pred"], 2), fnum(eff["ultra"], 2), fnum(eff["max_avg"], 2),
            fnum(eff["max_pausa"], 2), fnum(eff["max_total"], 2), fnum(eff["min_total_vol"], 2),
            fnum(eff["min_vol_rate"], 2), 1 if res_limited else 0)
        log("CALIBRATION", t_ns, None, "", extra)

    def check_session(t_ns):
        nonlocal sess_end
        if sess_end is not None and t_ns < sess_end:
            return
        sess_end = sessions.session_end_ns(t_ns)
        finalize_streak(t_ns)
        if not p["adaptive_mode"]:
            return
        if len(ms_s.vals) >= 100 and len(vol_s.vals) >= 100 and ms_s.seen >= p["min_calib_samples"]:
            recalibrate(t_ns)
        ms_s.clear()
        vol_s.clear()

    def reset_streak():
        st.update(dir=0, streak=0, valid=0, fails=0, swh=0.0, swl=0.0,
                  total_vol=0.0, max_retro=0.0, ms_list=[])

    def start_streak(direction, price, vol, t_ns):
        st.update(dir=direction, streak=1, valid=1, fails=0, swh=price, swl=price,
                  total_vol=vol, max_retro=0.0, ms_list=[], t_start=t_ns, t_last=t_ns)

    def continue_streak(price, vol, ms, t_ns, valid):
        st["streak"] += 1
        if valid:
            st["valid"] += 1
        st["swh"] = max(st["swh"], price)
        st["swl"] = min(st["swl"], price)
        st["ms_list"].append(ms)      # FIX#2: solo intervalos internos
        st["total_vol"] += vol
        st["t_last"] = t_ns

    def build_zone(height_ticks, is_sweep, avg_ms, total_ms, vol_rate, assign_id):
        nonlocal next_zone_id
        bucket = ("ABSORB" if not is_sweep else
                  "PREDATOR" if avg_ms <= eff["pred"] else
                  "ULTRA" if avg_ms <= eff["ultra"] else "FAST")
        if assign_id:
            next_zone_id += 1
        zid = next_zone_id if assign_id else 0
        if st["dir"] == 1:
            upper, lower = st["swl"], st["swl"] - p["zone_height_ticks"] * tick_size
        else:
            upper, lower = st["swh"] + p["zone_height_ticks"] * tick_size, st["swh"]
        return dict(id=zid, calib_id=calib_id, created_bar=closed_bar,
                    created_ms=ns_to_ms(st["t_last"]), dir=st["dir"], bucket=bucket,
                    avg_ms=avg_ms, total_ms=total_ms, vol_rate=vol_rate,
                    total_vol=st["total_vol"], max_retro=st["max_retro"],
                    pasos=st["streak"], valid_steps=st["valid"], height_ticks=height_ticks,
                    upper=upper, lower=lower, touches=0, inside_epoch=False,
                    archived=False, ended_ms=None, end_reason=None, timeline=[])

    def finalize_streak(t_ns):
        if st["dir"] == 0:
            reset_streak()
            return
        height_ticks = int(round((st["swh"] - st["swl"]) / tick_size))
        is_sweep = height_ticks >= p["min_sweep_ticks"]           # FIX#3
        total_ms = float(sum(st["ms_list"]))
        avg_ms = total_ms / len(st["ms_list"]) if st["ms_list"] else 0.0
        dur_sec = max(total_ms, 1.0) / 1000.0                      # FIX#1
        vol_rate = st["total_vol"] / dur_sec
        min_req = p["min_pasos"] if is_sweep else p["min_absorb_pasos"]
        structural = st["valid"] >= min_req and (is_sweep or p["detect_absorb"])
        ok = (structural and avg_ms <= eff["max_avg"] and total_ms <= eff["max_total"]
              and vol_rate >= eff["min_vol_rate"] and st["total_vol"] >= eff["min_total_vol"])
        if st["valid"] >= p["min_export_valid_steps"]:
            obs = build_zone(height_ticks, is_sweep, avg_ms, total_ms, vol_rate, assign_id=False)
            log("OBS", st["t_last"], obs, "pass=1" if ok else "pass=0", "")
            obs_events.append(obs)
        if ok:
            z = build_zone(height_ticks, is_sweep, avg_ms, total_ms, vol_rate, assign_id=True)
            zones.append(z)
            log("ZONE_CREATED", st["t_last"], z, "", "")
        reset_streak()

    def invalidate_zone(z, t_ns, reason):
        z["archived"] = True
        z["ended_ms"] = ns_to_ms(t_ns)
        z["end_reason"] = reason
        log("ZONE_INVALIDATED", t_ns, z, reason, "")

    def update_zones(price, t_ns):
        for z in reversed(zones):
            if z["archived"]:
                continue
            inside = z["lower"] <= price <= z["upper"]
            if inside and not z["inside_epoch"]:
                z["touches"] += 1
                z["inside_epoch"] = True
                if z["touches"] <= p["max_logged_touches"]:
                    log("ZONE_TOUCHED", t_ns, z, "epoch=" + str(z["touches"]), "")
                if p["invalidation_mode"] == "FirstTouch":
                    invalidate_zone(z, t_ns, "first_touch")
                    continue
                if p["max_touches"] > 0 and z["touches"] >= p["max_touches"]:
                    invalidate_zone(z, t_ns, "max_touches")
                    continue
            elif not inside:
                z["inside_epoch"] = False
            if p["invalidation_mode"] == "CloseThrough":
                through = (price <= z["lower"] - p["penetration_ticks"] * tick_size
                           if z["dir"] == 1 else
                           price >= z["upper"] + p["penetration_ticks"] * tick_size)
                if through:
                    invalidate_zone(z, t_ns, "close_through")

    def step_engine(price, vol, ms, t_ns, prev):
        if st["dir"] != 0 and ms > eff["max_pausa"]:
            finalize_streak(t_ns)
            return
        if st["dir"] == 0:
            if price < prev:
                start_streak(-1, price, vol, t_ns)
            elif price > prev:
                start_streak(1, price, vol, t_ns)
            return
        valid = price >= prev if st["dir"] == 1 else price <= prev
        if valid:
            continue_streak(price, vol, ms, t_ns, True)
            st["fails"] = 0
        else:
            st["fails"] += 1
            if st["fails"] <= p["fallos_tolerados"]:
                continue_streak(price, vol, ms, t_ns, False)
            else:
                finalize_streak(t_ns)
                if price < prev:
                    start_streak(-1, price, vol, t_ns)
                elif price > prev:
                    start_streak(1, price, vol, t_ns)
                return
        if p["use_relative_retro"] and st["dir"] != 0:
            height_ticks = (st["swh"] - st["swl"]) / tick_size
            retro = (st["swh"] - price) / tick_size if st["dir"] == 1 else (price - st["swl"]) / tick_size
            if retro > st["max_retro"]:
                st["max_retro"] = retro
            allowed = max(p["retro_floor_ticks"], p["retro_pct_height"] / 100.0 * height_ticks)
            if retro > allowed:
                finalize_streak(t_ns)   # el tick que viola queda incluido (declarado)

    for kind, idx in tick_and_bar_events(tns, bars.end_ns):
        if kind == "bar":
            closed_bar = idx
            if closed_bar < 1:
                continue
            t_bar = int(bars.end_ns[idx])
            for z in reversed(zones):
                if z["archived"] or closed_bar - z["created_bar"] <= p["max_age_bars"]:
                    continue
                z["archived"] = True
                z["ended_ms"] = ns_to_ms(t_bar)
                z["end_reason"] = "expired"
                log("ZONE_EXPIRED", t_bar, z, "", "")
            continue

        i = idx
        if i < 1:
            continue
        t_ns = int(tns[i])
        check_session(t_ns)
        price = float(pticks[i]) * tick_size
        vol = float(vols[i])
        ms = (int(tns[i]) - int(tns[i - 1])) / 1e6
        if p["adaptive_mode"]:
            if 0 <= ms <= p["pause_exclude_ms"]:
                ms_s.add(ms)
            vol_s.add(vol)
        update_zones(price, t_ns)
        if calib_ready:
            step_engine(price, vol, ms, t_ns, float(pticks[i - 1]) * tick_size)
        elif not pending_logged:
            log("CALIBRATION_PENDING", t_ns, None, "first_session_no_calibration", "")
            pending_logged = True

    if len(bars) > 0:
        t_end = int(bars.end_ns[-1])
        for z in zones:
            if not z["archived"]:
                log("SESSION_END", t_end, z, "snapshot", "")

    viewer_zones = [dict(id="Z" + format(z["id"], "06d"), indicator=NAME,
                         top=z["upper"], bottom=z["lower"], created_ms=z["created_ms"],
                         ended_ms=z["ended_ms"],
                         state=("ACTIVE" if not z["archived"] else
                                "EXPIRED" if z["end_reason"] == "expired" else "INVALIDATED"),
                         kind=("support" if z["dir"] == 1 else "resistance") + "_" + z["bucket"].lower(),
                         dir=z["dir"], bucket=z["bucket"], calib_id=z["calib_id"],
                         touches=z["touches"], end_reason=z["end_reason"], timeline=z["timeline"])
                    for z in zones]

    return dict(indicator=NAME, params=p, header=HEADER, csv_lines=lines,
                events=rows, zones=viewer_zones, obs_count=len(obs_events),
                params_line="# params " + ",".join("%s=%s" % kv for kv in sorted(p.items())))
