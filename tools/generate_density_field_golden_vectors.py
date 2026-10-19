#!/usr/bin/env python3
"""Genera los vectores dorados que atan `density_field.js` a `density_field.py`.

**Target-free.** Sin retornos ni P&L: solo entradas sintéticas y las salidas de la referencia.

Por qué existe. Había cinco implementaciones de «corredor» y ninguna validada contra otra: el motor
JS certificado (`corridor_engine.js`, archivado) nunca se comparó con el módulo Python con el que
se midió HP-007, y el único test cruzado existente comparaba a Python con una **tercera** implementación
que vivía dentro del propio test. La regla del repo (`visor_server.py`: no puede haber un segundo
implementador del mismo objeto) exige que el que se mira sea el que se midió; como el visor no puede
llamar a Python, la garantía es este fixture: la referencia genera, el puerto JS reproduce.

Las entradas usan nanosegundos **múltiplos de 4096** (exactamente representables como `number` de JS a
escala 1e18) y segundos/milisegundos enteros: así el fixture no depende del límite de 256 ns de JS.

    .venv\\Scripts\\python tools\\generate_density_field_golden_vectors.py          # regenera
    .venv\\Scripts\\python tools\\generate_density_field_golden_vectors.py --check  # verifica que esté al día
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.research.corridor_geometry import characterize_corridors  # noqa: E402
from edgelab.research.density_field import (  # noqa: E402
    HOLDOUT_NS, compute_field, detect_density_intervals, price_to_tick, to_nanoseconds,
)

OUT = REPO / "tests" / "fixtures" / "density_field_golden_v2.json"
TICK = 0.25
BASE_NS = 1_780_000_000_000_000_000          # 2026-05-28, pre-holdout; múltiplo de 4096
UNIT = 4096 * 1000                            # 4,096 ms


def _ns(rng: random.Random, span_units: int = 6_000_000) -> int:
    return BASE_NS + rng.randrange(0, span_units) * UNIT


def _zones(rng: random.Random, n: int, *, session=None, contract=None, ended=False,
           touch_events=False, touches=False, only_t0=False) -> list[dict]:
    zs = []
    for i in range(n):
        lo = round(19000.0 + rng.randrange(0, 200) * TICK, 2)
        hi = round(lo + rng.randrange(0, 12) * TICK, 2)
        av = _ns(rng, 2_000_000)
        z = {"id": f"Z{i:03d}", "bottom": lo, "top": hi, "vol": float(rng.randrange(1, 120)),
             "kind": rng.choice(["HFT BUY", "HFT SELL", "ABSORB BULL", "ABSORB BEAR"])}
        if only_t0:
            z["t0"] = av // 1_000_000_000
        else:
            z["available_ns"] = av
        if ended and rng.random() < 0.35:
            z["t1"] = (av + rng.randrange(1, 2_000_000) * UNIT) // 1_000_000_000 * 1  # segundos
        if touch_events:
            z["touch_events"] = [av + rng.randrange(1, 3_000_000) * UNIT for _ in range(rng.randrange(0, 4))]
        if touches:
            z["touches"] = rng.randrange(0, 5)
        if session is not None:
            z["session_id"] = rng.choice(session)
        if contract is not None:
            z["contract"] = rng.choice(contract)
        zs.append(z)
    return zs


CAL = {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2, "vol_transform": "TRANS_POWER_025",
       "use_maturation": True, "use_time_decay": True, "use_wear": True, "saturation": True}


def build_scenarios() -> list[dict]:
    rng = random.Random(20260921)
    p0, p1 = price_to_tick(18990.0, TICK), price_to_tick(19070.0, TICK)
    t_ref = BASE_NS + 4_000_000 * UNIT
    sc: list[dict] = []

    def add(name, zones, cfg, t=t_ref, interval_opts=None, lo=p0, hi=p1):
        sc.append({"name": name, "zones": zones, "t_ref": t, "tick_size": TICK, "p_min": lo, "p_max": hi,
                   "cfg": cfg, "interval_opts": interval_opts or {}})

    z = _zones(rng, 60)
    add("raw_gauss", z, {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2},
        interval_opts={"low_thresh": 0.5, "high_thresh": 2.5, "min_low_ticks": 3, "min_high_ticks": 1})
    add("raw_box", z, {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX"},
        interval_opts={"low_thresh": 0.5, "high_thresh": 2.0, "min_low_ticks": 3, "min_high_ticks": 1})
    add("trans_power025", z, {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2, "vol_transform": "TRANS_POWER_025"})
    add("trans_log", z, {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 2.0, "vol_transform": "TRANS_LOG"})
    add("trans_winsorized", z, {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "vol_transform": "TRANS_WINSORIZED"})
    add("trans_count", z, {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "vol_transform": "TRANS_COUNT"})
    zt = _zones(rng, 80, touch_events=True)
    add("calibrated_full_touch_events", zt, dict(CAL))
    zl = _zones(rng, 80, touches=True)
    add("calibrated_legacy_touches", zl, dict(CAL))
    ze = _zones(rng, 80, ended=True)
    add("ended_exclude", ze, dict(CAL))
    add("ended_penalize", ze, dict(CAL, ended_zone_policy="penalize_ended", invalidation_penalty=0.5))
    add("ended_include_all", ze, dict(CAL, ended_zone_policy="include_all"))
    zs = _zones(rng, 90, session=["20260601", "20260602"], contract=["NQ 06-26", "NQ 03-26"])
    add("session_contract_filter", zs, dict(CAL, session_id="20260601", contract="NQ 06-26"))
    add("legacy_availability_t0_only", _zones(rng, 50, only_t0=True), {"model": "FIELD_RAW_STATIC"})
    add("empty_zones", [], dict(CAL))
    add("small_sigma_clamped", z, {"model": "FIELD_RAW_STATIC", "sigma_ticks": 0.01})
    add("early_tref_few_causal", z, dict(CAL), t=BASE_NS + 300_000 * UNIT)

    # --- escalas de tiempo mezcladas (s / ms / us / ns / cadena entera): todas exactamente representables
    ts = 1_780_000_000                          # 2026-05-28 en segundos
    escalas = [
        {"id": "S", "bottom": 19010.0, "top": 19011.0, "vol": 30.0, "available_ts": ts + 100},
        {"id": "MS", "bottom": 19010.5, "top": 19011.5, "vol": 20.0, "available_ts": (ts + 200) * 1000},
        {"id": "US", "bottom": 19020.0, "top": 19021.0, "vol": 40.0, "available_ts": (ts + 300) * 1_000_000},
        {"id": "NS", "bottom": 19020.5, "top": 19022.0, "vol": 10.0, "available_ns": (ts + 400) * 1_000_000_000},
        {"id": "STR", "bottom": 19030.0, "top": 19031.0, "vol": 25.0, "available_ns": str((ts + 500) * 1_000_000_000)},
        {"id": "AVT", "bottom": 19040.0, "top": 19041.0, "vol": 15.0, "availableTime": ts + 600},
    ]
    add("time_scale_detection", escalas, dict(CAL), t=(ts + 1000) * 1_000_000_000)

    # --- precios fuera de grilla (medio tick): round-half-even del pasaje a ticks
    add("off_grid_half_tick", [
        {"id": "H1", "bottom": 19010.125, "top": 19010.375, "vol": 10.0, "available_ns": BASE_NS + 10 * UNIT},
        {"id": "H2", "bottom": 19010.625, "top": 19011.125, "vol": 10.0, "available_ns": BASE_NS + 20 * UNIT},
        {"id": "H3", "bottom": 19011.375, "top": 19011.375, "vol": 10.0, "available_ns": BASE_NS + 30 * UNIT},
    ], {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX"}, t=BASE_NS + 100 * UNIT)

    # --- empates de disponibilidad: el orden lo decide el id, no el orden de entrada
    emp = [{"id": k, "bottom": 19020.0 + i * 0.25, "top": 19021.0 + i * 0.25, "vol": float(10 + i), "available_ns": BASE_NS + 500 * UNIT}
           for i, k in enumerate(["b", "a", "c", "B", "A"])]
    add("availability_ties", emp, dict(CAL), t=BASE_NS + 900 * UNIT)

    # --- mismo conjunto, otro orden: tiene que dar EXACTAMENTE lo mismo
    barajado = list(z)
    random.Random(7).shuffle(barajado)
    add("shuffled_input_order", barajado, {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2},
        interval_opts={"low_thresh": 0.5, "high_thresh": 2.5, "min_low_ticks": 3, "min_high_ticks": 1})

    # --- FRONTERAS: lo que una prueba de mutacion detecto que faltaba. Un `<=` que pasa a `<` no debe sobrevivir.
    tb = BASE_NS + 1000 * UNIT
    add("boundary_causal_equal_tref", [
        {"id": "IGUAL", "bottom": 19010.0, "top": 19010.5, "vol": 10.0, "available_ns": tb},
        {"id": "ANTES", "bottom": 19011.0, "top": 19011.5, "vol": 10.0, "available_ns": tb - UNIT},
        {"id": "DESPUES", "bottom": 19012.0, "top": 19012.5, "vol": 10.0, "available_ns": tb + 4096},
    ], {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX"}, t=tb)
    add("boundary_ended_equal_tref", [
        {"id": "FIN_IGUAL", "bottom": 19010.0, "top": 19010.5, "vol": 10.0, "available_ns": tb - 10 * UNIT, "ended_ns": tb},
        {"id": "FIN_DESPUES", "bottom": 19011.0, "top": 19011.5, "vol": 10.0, "available_ns": tb - 10 * UNIT, "ended_ns": tb + 4096},
        {"id": "FIN_ANTES", "bottom": 19012.0, "top": 19012.5, "vol": 10.0, "available_ns": tb - 10 * UNIT, "ended_ns": tb - UNIT},
    ], {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX"}, t=tb)
    # cajas de peso entero: la densidad cae EXACTAMENTE en los umbrales (1.0 y 2.0) y los tramos miden EXACTAMENTE el minimo
    b0 = price_to_tick(19000.0, TICK)
    def caja(i, a, b):   # ticks [b0+a, b0+b]
        return {"id": i, "bottom": (b0 + a) * TICK, "top": (b0 + b) * TICK, "vol": 10.0, "available_ns": BASE_NS + 10 * UNIT}
    add("boundary_thresholds_exact", [caja("A", 10, 19), caja("B", 15, 19), caja("C", 30, 33)],
        {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX"}, t=tb, lo=b0, hi=b0 + 60,
        interval_opts={"low_thresh": 1.0, "high_thresh": 2.0, "min_low_ticks": 5, "min_high_ticks": 5})

    # --- volumenes nulos / ausentes / cero / negativos (lo encontro la paridad sobre bundles REALES)
    vols = [
        {"id": "V_NULL", "bottom": 19010.0, "top": 19011.0, "vol": None, "available_ns": BASE_NS + 10 * UNIT},
        {"id": "V_AUSENTE", "bottom": 19012.0, "top": 19013.0, "available_ns": BASE_NS + 20 * UNIT},
        {"id": "V_VOLUME", "bottom": 19014.0, "top": 19015.0, "volume": 50.0, "available_ns": BASE_NS + 30 * UNIT},
        {"id": "V_NULL_CON_VOLUME", "bottom": 19016.0, "top": 19017.0, "vol": None, "volume": 80.0, "available_ns": BASE_NS + 40 * UNIT},
        {"id": "V_CERO", "bottom": 19018.0, "top": 19019.0, "vol": 0.0, "available_ns": BASE_NS + 50 * UNIT},
        {"id": "V_NEG", "bottom": 19020.0, "top": 19021.0, "vol": -5.0, "available_ns": BASE_NS + 60 * UNIT},
        {"id": "V_NORMAL", "bottom": 19022.0, "top": 19023.0, "vol": 40.0, "available_ns": BASE_NS + 70 * UNIT},
    ]
    add("volume_null_absent_zero_negative", vols, dict(CAL), t=BASE_NS + 1000 * UNIT)
    add("volume_null_raw_static", vols, {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS"}, t=BASE_NS + 1000 * UNIT)

    # --- campo saturado con una muralla y un corredor claros (caracterización direccional)
    muros = [
        {"id": "W_FLOOR_BUY", "bottom": 19005.0, "top": 19006.0, "vol": 90.0, "kind": "HFT BUY", "available_ns": BASE_NS + 10 * UNIT},
        {"id": "W_FLOOR_2", "bottom": 19005.25, "top": 19006.25, "vol": 90.0, "kind": "HFT BUY", "available_ns": BASE_NS + 20 * UNIT},
        {"id": "W_CEIL_SELL", "bottom": 19030.0, "top": 19031.0, "vol": 90.0, "kind": "HFT SELL", "available_ns": BASE_NS + 40 * UNIT},
        {"id": "W_CEIL_2", "bottom": 19030.25, "top": 19031.25, "vol": 90.0, "kind": "HFT SELL", "available_ns": BASE_NS + 50 * UNIT},
    ]
    add("characterize_dual", muros, dict(CAL, use_time_decay=False, use_maturation=False),
        t=BASE_NS + 1000 * UNIT, interval_opts={"low_thresh": 0.32, "high_thresh": 0.5, "min_low_ticks": 7, "min_high_ticks": 2})
    solo_buy = [dict(m) for m in muros[:2]] + [dict(m, kind="HFT BUY") for m in muros[2:]]
    add("characterize_bull_only", solo_buy, dict(CAL, use_time_decay=False, use_maturation=False),
        t=BASE_NS + 1000 * UNIT, interval_opts={"low_thresh": 0.32, "high_thresh": 0.5, "min_low_ticks": 7, "min_high_ticks": 2})
    por_direccion = [dict(m, kind=None, direction=(1 if "BUY" in m["id"] or m["id"] == "W_FLOOR_2" else -1)) for m in muros]
    for m in por_direccion:
        m.pop("kind")
    add("characterize_by_direction_field", por_direccion, dict(CAL, use_time_decay=False, use_maturation=False),
        t=BASE_NS + 1000 * UNIT, interval_opts={"low_thresh": 0.32, "high_thresh": 0.5, "min_low_ticks": 7, "min_high_ticks": 2})
    return sc


def evaluar(s: dict) -> dict:
    res = compute_field(s["zones"], s["t_ref"], s["tick_size"], s["p_min"], s["p_max"], s["cfg"])
    inter = detect_density_intervals(res["density"], res["price_ticks"], s["tick_size"], **s["interval_opts"])
    corr = characterize_corridors(inter, s["zones"], res["active_zone_ids"], s["tick_size"], to_nanoseconds(s["t_ref"]))
    d = res["diagnostics"]
    return {
        "density": res["density"], "active_zone_ids": res["active_zone_ids"],
        "intervals": inter, "corridors": corr,
        "diagnostics": {k: d[k] for k in ("v_ref", "v_ref_source", "n_active_zones", "total_zones_evaluated",
                                          "legacy_availability_fallbacks", "legacy_touch_fallbacks",
                                          "available_ts_sources", "causal_status", "n_ticks", "field_mean", "field_max")},
    }


def build() -> dict:
    sc = build_scenarios()
    out = []
    for s in sc:
        out.append({**s, "expected": evaluar(s)})
    # casos que DEBEN fallar cerrado (holdout): no llevan salida, llevan el motivo
    fail = [
        {"name": "holdout_zone", "zones": [{"id": "H", "bottom": 19000.0, "top": 19001.0, "vol": 5.0, "available_ns": HOLDOUT_NS}],
         "t_ref": BASE_NS, "cfg": {}},
        {"name": "holdout_tref", "zones": [], "t_ref": HOLDOUT_NS, "cfg": {}},
    ]
    return {"schema": "edgelab_density_field_golden_v2", "holdout_ns": HOLDOUT_NS, "tick_size": TICK,
            "generator": "tools/generate_density_field_golden_vectors.py", "scenarios": out, "must_fail_closed": fail}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    doc = json.dumps(build(), sort_keys=True, separators=(",", ":"))
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == doc
        print("fixture al dia" if ok else "FIXTURE DESACTUALIZADO: regenerar")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"escrito {OUT} ({len(doc)/1024:.0f} KB, {len(json.loads(doc)['scenarios'])} escenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
