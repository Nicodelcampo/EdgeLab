#!/usr/bin/env python3
"""Perfiles escalados de HFTZones (motor NQ congelado) para todos los activos. **Target-free**: solo ticks.

Decision de Nico 2026-09-21: «mismo indicador» en todos los activos = mismo motor y misma logica, con los
umbrales expresados por el propio activo en vez de en unidades de NQ. Con los umbrales de NQ literales la
densidad de zonas por tick varia ~30x entre activos (ver docs/research/HFTZONES_ESTANDARIZACION_MULTIACTIVO_20260921.md).

Metodo (embudo de cuantiles, sin mirar precios futuros ni retornos):
  1. Se corre `detect_candidates` (censo de rachas, independiente de los umbrales de aceptacion) sobre una
     muestra fija de sesiones pre-holdout de un contrato de referencia por activo.
  2. En NQ se mide el embudo del perfil literal: que fraccion sobrevive cada compuerta, en orden y condicionada a
     las anteriores (pasos -> altura de sweep -> avg_ms -> total_ms -> tasa de volumen -> volumen total).
  3. En cada activo se elige, compuerta a compuerta, el umbral que reproduce la fraccion de NQ elevada a un unico factor
     de rigor alfa (forma del embudo de NQ, intensidad ajustable). alfa se busca por biseccion para que la densidad de
     zonas por 1.000 ticks del activo iguale la de NQ en la muestra de calibracion. Un solo grado de libertad.
     (Igualar las fracciones sin alfa se probo primero y empeoro la dispersion: los activos tienen distinta cantidad
     de rachas candidatas por tick, ver el reporte.)
  4. Quedan FIJOS los parametros estructurales (max_pausa_ms, retroceso, tick_resolution): cambiarlos cambia
     que rachas existen, no solo cuales se aceptan.
  5. Validacion fuera de muestra: se mide la densidad de zonas en OTRO contrato del mismo activo.

Sale 0 si el propio NQ recupera su perfil literal (idempotencia) y el holdout no se toco.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators import hftzones_nq as frozen  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402

HOLDOUT_NS = 1782856800000000000
NAME = "SCALED_FUNNEL_V1"
LIT = dict(frozen.ACCEPT_DEFAULTS)
# contrato de calibracion / contrato de validacion (fuera de muestra) por activo
REFERENCE = {"NQ": ("03-26", "06-26"), "GC": ("04-26", "06-26"), "MBT": ("03-26", "05-26")}   # MBT no tiene 06-26
DEFAULT_REFERENCE = ("03-26", "06-26")
INSTRUMENTS = ["NQ", "ES", "MES", "MNQ", "YM", "6E", "6B", "6J", "GC", "MBT", "ZB"]


def _sessions(bundles: Path, inst: str, suffix: str, n: int):
    """Sesiones de los manifiestos del contrato `<inst> <suffix>`; n equiespaciadas, deterministas."""
    found = {}
    contract = f"{inst} {suffix}"
    for f in sorted(bundles.glob("*.manifest.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        if m.get("instrument") != inst or m.get("contract") != contract or "sessions" not in m:
            continue
        for s in m["sessions"]:
            found.setdefault(int(s["trade_date"]), (m["source_path"], s))
    days = sorted(found)
    if not days:
        return contract, []
    idx = sorted({int(round(i)) for i in np.linspace(0, len(days) - 1, min(n, len(days)))})
    return contract, [(d, *found[d]) for d in (days[i] for i in idx)]


def _candidates(data_root: Path, inst: str, contract: str, sess):
    cands, ticks, tick_size = [], 0, None
    for day, src, s in sess:
        rel = src.replace("\\", "/").split("/data/", 1)[1]
        tk = load_canonical_parquet(data_root / rel, contract=contract, instrument=inst,
                                    start_utc_ns=int(s["start_utc_ns"]), end_utc_ns=int(s["end_utc_ns"]))
        if int(tk.ts_ns[-1]) >= HOLDOUT_NS:
            raise SystemExit(f"HOLDOUT decodificado en {inst} {day}")
        tick_size = float(tk.tick_size)
        ticks += len(tk)
        cands.extend(frozen.detect_candidates(tk.ts_ns, tk.price_ticks, tk.volume, params={},
                                              prev_session_close_ticks=s.get("prev_session_close_ticks")))
    return cands, ticks, tick_size


def _cols(c):
    g = lambda k: np.array([x[k] for x in c], dtype=float)  # noqa: E731
    return dict(steps=g("valid_steps"), height=g("height_ticks"), avg=g("avg_ms"), tot=g("total_ms"),
                rate=g("vol_rate"), vol=g("total_vol"))


def funnel(cols, prof):
    """Fracciones condicionadas del perfil `prof` sobre las columnas (orden fijo del embudo)."""
    m = np.ones(len(cols["steps"]), bool)
    out = []
    for key, thr, ge in (("steps", prof["min_pasos"], True), ("height", prof["min_sweep_ticks"], True),
                         ("avg", prof["max_avg_ms"], False), ("tot", prof["max_total_ms"], False),
                         ("rate", prof["min_volume_rate"], True), ("vol", prof["min_total_volume"], True)):
        ok = (cols[key] >= thr) if ge else (cols[key] <= thr)
        out.append(float(ok[m].sum()) / max(1, int(m.sum())))
        m = m & ok
    return out, int(m.sum())


def match(cols, targets):
    """Umbrales que reproducen las fracciones `targets`, compuerta a compuerta."""
    m = np.ones(len(cols["steps"]), bool)
    prof = dict(LIT)
    spec = (("steps", "min_pasos", True, True), ("height", "min_sweep_ticks", True, True),
            ("avg", "max_avg_ms", False, False), ("tot", "max_total_ms", False, False),
            ("rate", "min_volume_rate", True, False), ("vol", "min_total_volume", True, False))
    for (key, name, ge, integer), q in zip(spec, targets):
        v = cols[key][m]
        if len(v) == 0:
            break
        if integer:
            cand = np.unique(np.floor(v)).astype(int)
            frac = lambda t: float((v >= t).mean())  # noqa: E731
            best = min(cand, key=lambda t: (abs(frac(t) - q), -t))
            thr = float(max(1, best))
        else:
            thr = float(np.quantile(v, (1 - q) if ge else q, method="nearest"))
            thr = round(thr, 1) if key in ("avg", "tot") else float(max(1.0, round(thr)))
        prof[name] = thr
        ok = (cols[key] >= thr) if ge else (cols[key] <= thr)
        m = m & ok
    prof["min_absorb_pasos"] = max(2, int(prof["min_pasos"]) - (LIT["min_pasos"] - LIT["min_absorb_pasos"]))
    prof["min_pasos"] = int(prof["min_pasos"])
    prof["min_sweep_ticks"] = int(prof["min_sweep_ticks"])
    return prof


def fit_alpha(cols, cands, ticks, tick_size, targets, target_density):
    """alfa tal que la densidad de zonas por 1k ticks del activo iguale `target_density` (biseccion, ~monotona)."""
    lo, hi = 0.05, 8.0
    best = None
    for _ in range(28):
        mid = (lo * hi) ** 0.5
        prof = match(cols, [t ** mid for t in targets])
        d, _ = zones_per_1k(cands, ticks, prof, tick_size)
        if best is None or abs(d - target_density) < abs(best[1] - target_density):
            best = (mid, d, prof)
        if d > target_density:
            lo = mid      # demasiadas zonas -> mas rigor (fracciones mas chicas = alfa mayor)
        else:
            hi = mid
    return best


def zones_per_1k(cands, ticks, prof, tick_size):
    z, _ = frozen.accept_all(cands, prof, tick_size)
    return 1000.0 * len(z) / max(1, ticks), len(z)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles", type=Path, default=REPO / "viewer/nt8_bridge/bundles")
    ap.add_argument("--data-root", type=Path, default=Path("E:/EdgeLab/data"))
    ap.add_argument("--sessions", type=int, default=16)
    ap.add_argument("--out", type=Path, default=REPO / "artifacts/research/hftzones_universal_scaled_v1.json")
    ap.add_argument("--instrument", action="append")
    ap.add_argument("--merge", action="store_true", help="actualiza solo los activos dados sobre el resultado previo")
    a = ap.parse_args(argv)

    insts = a.instrument or INSTRUMENTS
    if "NQ" not in insts:
        insts = ["NQ"] + insts
    data = {}
    for inst in insts:
        cal, val = REFERENCE.get(inst, DEFAULT_REFERENCE)
        rec = {}
        for role, suf in (("cal", cal), ("val", val)):
            contract, sess = _sessions(a.bundles, inst, suf, a.sessions)
            t0 = time.time()
            cands, ticks, ts = _candidates(a.data_root, inst, contract, sess)
            rec[role] = dict(contract=contract, sessions=[d for d, _, _ in sess], cands=cands, ticks=ticks, tick_size=ts)
            print(f"{inst:4s} {role} {contract:10s} sesiones={len(sess):2d} ticks={ticks:>12,} cand={len(cands):>8,} "
                  f"{time.time() - t0:5.0f}s", flush=True)
        data[inst] = rec

    ref = _cols(data["NQ"]["cal"]["cands"])
    targets, n_ref = funnel(ref, LIT)
    idem = match(ref, targets)
    idem_ok = all(abs(idem[k] - LIT[k]) <= max(0.51, 0.06 * abs(LIT[k])) for k in
                  ("min_pasos", "min_sweep_ticks", "max_avg_ms", "max_total_ms", "min_volume_rate", "min_total_volume"))
    print("\nembudo NQ literal:", [round(x, 4) for x in targets], "| idempotencia NQ:", idem_ok, idem)

    nq_density, _ = zones_per_1k(data["NQ"]["cal"]["cands"], data["NQ"]["cal"]["ticks"], LIT, data["NQ"]["cal"]["tick_size"])
    profiles, rows = {}, []
    for inst in insts:
        d = data[inst]
        alpha = 1.0
        if inst == "NQ":
            prof = dict(LIT)
        else:
            alpha, _, prof = fit_alpha(_cols(d["cal"]["cands"]), d["cal"]["cands"], d["cal"]["ticks"],
                                       d["cal"]["tick_size"], targets, nq_density)
        prof["alpha"] = round(alpha, 4)
        profiles[inst] = prof
        ts = d["cal"]["tick_size"]
        lit_c, _ = zones_per_1k(d["cal"]["cands"], d["cal"]["ticks"], LIT, ts)
        sc_c, n_c = zones_per_1k(d["cal"]["cands"], d["cal"]["ticks"], prof, ts)
        lit_v, _ = zones_per_1k(d["val"]["cands"], d["val"]["ticks"], LIT, ts)
        sc_v, n_v = zones_per_1k(d["val"]["cands"], d["val"]["ticks"], prof, ts)
        rows.append(dict(instrument=inst, calibration_contract=d["cal"]["contract"], validation_contract=d["val"]["contract"],
                         calibration_sessions=d["cal"]["sessions"], validation_sessions=d["val"]["sessions"],
                         ticks_cal=d["cal"]["ticks"], ticks_val=d["val"]["ticks"], tick_size=ts,
                         zones_per_1k_literal_cal=lit_c, zones_per_1k_scaled_cal=sc_c,
                         zones_per_1k_literal_val=lit_v, zones_per_1k_scaled_val=sc_v, zones_scaled_val=n_v,
                         thresholds=prof))
        print(f"{inst:4s} lit {lit_c:6.2f}->{lit_v:6.2f} | escalado {sc_c:6.2f}->{sc_v:6.2f}  {prof}")

    if a.merge and a.out.exists():
        prev = json.loads(a.out.read_text(encoding="utf-8"))
        keep = [r for r in prev["instruments"] if r["instrument"] not in {r2["instrument"] for r2 in rows}]
        rows = keep + rows
        rows.sort(key=lambda r: INSTRUMENTS.index(r["instrument"]) if r["instrument"] in INSTRUMENTS else 99)
        profiles = {r["instrument"]: r["thresholds"] for r in rows}

    def spread(k):
        v = [r[k] for r in rows if r[k] > 0]
        return max(v) / min(v)
    summary = dict(spread_literal_cal=spread("zones_per_1k_literal_cal"), spread_scaled_cal=spread("zones_per_1k_scaled_cal"),
                   spread_literal_val=spread("zones_per_1k_literal_val"), spread_scaled_val=spread("zones_per_1k_scaled_val"))
    print("\nrango max/min de densidad:", {k: round(v, 1) for k, v in summary.items()})

    out = dict(schema="hftzones_universal_scaled_profiles_v1", name=NAME, holdout_boundary_ns=HOLDOUT_NS,
               target_free=True, outcomes_opened=False, method="funnel_quantile_matching_to_NQ_literal",
               nq_funnel_fractions=targets, nq_idempotent=idem_ok, structural_fixed=["max_pausa_ms", "max_retroceso_ticks",
               "retroceso_pct_height", "tick_resolution", "detect_absorb"], summary=summary, instruments=rows,
               parity_status="PARITY_ABSTAIN")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    prof_json = {"name": NAME, "profiles": profiles, "evidence": str(a.out.relative_to(REPO)).replace("\\", "/"),
                 "evidence_sha256": hashlib.sha256(a.out.read_bytes()).hexdigest()}
    (REPO / "edgelab/bridge/indicators/hftzones_universal_profiles.json").write_text(json.dumps(prof_json, indent=1), encoding="utf-8")
    return 0 if idem_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
