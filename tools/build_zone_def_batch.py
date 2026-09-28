#!/usr/bin/env python3
r"""Tanda ✓/✗ para validar definiciones de zona de IPC (target-free, a ciegas). Diseño: DISENO_IPC_ABANICO_DE_MECANISMOS_20260927.md §5.

- Cinco definiciones congeladas ACÁ, antes de ver cualquier curva de atracción (DEFS).
- Mes de validación: ES febrero 2026 (el detector se ajustó con enero): fuera de muestra.
- Muestra: `PER_DEF` zonas por definición, sin repetir, mezcladas. El archivo que ve el visor NO dice a qué definición
  pertenece cada zona (ciego); la pertenencia va a artifacts/ipc/zone_defs/ (no lo lee el visor).
- Una zona «pertenece» a una definición si alguna zona de esa definición coincide (mismo tipo, IoU de picos ≥ 0,8):
  así un juicio sirve para todas las definiciones que la contienen.

    .venv\Scripts\python tools\build_zone_def_batch.py            # arma la tanda
    .venv\Scripts\python tools\build_zone_def_batch.py --score    # precisión por definición con los juicios de Nico
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

import peaks_rule as PR  # noqa: E402

ASSET = "ES_03-26_202602_25T_HFT"
PER_DEF = 25
SEED = 20260927
CAP_P90 = None                                   # se toma del ajuste de enero (tope de pendiente de las marcas de Nico)
DEFS = {
    "D1_validada":    dict(w=2, max_gap=60, max_step=2, min_pull=2, nmin=6, minp=8,  cap=True,  rel_vol=None),
    "D2_estricta":    dict(w=2, max_gap=60, max_step=2, min_pull=2, nmin=6, minp=12, cap=True,  rel_vol=None),
    "D3_horizontal":  dict(w=2, max_gap=60, max_step=0, min_pull=2, nmin=5, minp=5,  cap=True,  rel_vol=None),
    "D4_comercio":    dict(w=2, max_gap=60, max_step=2, min_pull=2, nmin=6, minp=8,  cap=True,  rel_vol=1.2),
    "D5_laxa":        dict(w=1, max_gap=30, max_step=4, min_pull=1, nmin=5, minp=5,  cap=False, rel_vol=None),
}
OUT_META = REPO / "artifacts" / "ipc" / "zone_defs"


def iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0)); uni = max(a1, b1) - min(a0, b0)
    return inter / uni if uni > 0 else 0.0


def zones_for(cd, v, cap, p):
    Z = PR.series(cd, 0.25, p["w"], p["max_gap"], p["max_step"], p["min_pull"], p["nmin"],
                  extend_back=True, max_slope=(cap if p["cap"] else None))
    Z = [z for z in Z if len(z["picos"]) >= p["minp"]]
    if p["rel_vol"]:                              # comercio entre picos: volumen por vela entre el 1.º y el minp-ésimo pico
        out = []
        for z in Z:
            a, b = z["picos"][0][0], z["picos"][p["minp"] - 1][0]
            sess0 = int(np.searchsorted(cd["sess"], cd["sess"][a], side="left"))
            ref = np.median(v[sess0:a + 1]) if a > sess0 else np.nan          # sólo lo anterior en la sesión (causal)
            if np.isfinite(ref) and ref > 0 and v[a:b + 1].mean() >= p["rel_vol"] * ref:
                out.append(z)
        Z = out
    return Z


def load():
    b = json.loads((PR.VIEW / "bundles" / f"{ASSET}.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]
    t = np.array([x["time"] for x in c], float)
    cd = dict(t=t, h=np.array([x["high"] for x in c]), l=np.array([x["low"] for x in c]))
    cd["sess"] = np.cumsum(np.r_[0, np.diff(t) > 1800])
    return cd, np.array([x["volume"] for x in c], float)


def build():
    cap = json.loads((PR.VIEW / "bundles" / "peaks_det" / "ES_03-26_202601_25T_HFT.json").read_text(encoding="utf-8")).get("tope_pendiente_p90")
    cd, v = load()
    by = {d: zones_for(cd, v, cap, p) for d, p in DEFS.items()}
    rng = np.random.default_rng(SEED)
    chosen = []
    for d, Z in by.items():
        idx = rng.permutation(len(Z)); k = 0
        for i in idx:
            z = Z[int(i)]
            if any(c["kind"] == z["kind"] and iou(c["i0"], c["i1"], z["i0"], z["i1"]) >= 0.8 for c in chosen):
                continue
            chosen.append(z); k += 1
            if k >= PER_DEF:
                break
    member = []
    for z in chosen:
        member.append([d for d, Z in by.items() if any(y["kind"] == z["kind"] and iou(y["i0"], y["i1"], z["i0"], z["i1"]) >= 0.8 for y in Z)])
    order = rng.permutation(len(chosen))
    chosen = [chosen[int(i)] for i in order]; member = [member[int(i)] for i in order]
    days = len(set((cd["t"] // 86400).astype(int)))
    viewer = dict(schema="EDGELAB_PEAKS_DET_V2_REGLA", asset=ASSET, variante="tanda_definiciones_ciega_20260927", zonas=chosen,
                  zonas_por_dia=round(len(chosen) / max(days, 1), 1), nota="tanda ciega: no indica definición")
    (PR.VIEW / "bundles" / "peaks_det" / f"{ASSET}.json").write_text(json.dumps(viewer, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    OUT_META.mkdir(parents=True, exist_ok=True)
    (OUT_META / "tanda_20260927.json").write_text(json.dumps(dict(asset=ASSET, defs=DEFS, cap_p90=cap, per_def=PER_DEF, seed=SEED,
        zonas_por_definicion_total={d: len(Z) for d, Z in by.items()},
        membresia=[dict(kind=z["kind"], i0=z["i0"], i1=z["i1"], defs=m) for z, m in zip(chosen, member)]), ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(dict(zonas_en_tanda=len(chosen), total_por_def={d: len(Z) for d, Z in by.items()},
                          en_tanda_por_def={d: sum(d in m for m in member) for d in DEFS}), ensure_ascii=False))


def score():
    meta = json.loads((OUT_META / "tanda_20260927.json").read_text(encoding="utf-8"))
    lab = json.loads((PR.VIEW / "labels" / f"{ASSET}.json").read_text(encoding="utf-8"))
    J = {(j["kind"], j["i0"], j["i1"]): j["verdict"] for j in lab.get("judgments", [])}
    res = {}
    for d in meta["defs"]:
        vs = [J.get((m["kind"], m["i0"], m["i1"])) for m in meta["membresia"] if d in m["defs"]]
        vs = [x for x in vs if x]
        si = sum(x == "si" for x in vs)
        res[d] = dict(juzgadas=len(vs), si=si, precision=round(si / len(vs), 3) if vs else None)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    score() if a.score else build()
