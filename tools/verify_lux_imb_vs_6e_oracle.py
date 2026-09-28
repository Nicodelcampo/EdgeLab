#!/usr/bin/env python3
r"""Validacion PARCIAL de LUX-IMB (OG + VI) en Python contra las zonas que NT8 exporto para 6E Continuo.

Oraculo: las zonas `ImbalanceDetectorLuxAlgoMTF` del bundle `6E_CONT.json` (export de NT8, FVG apagado) y sus
barras M1 (`time_1m`). Compara, por clave (familia, direccion, t0): bordes, vencimiento (t1), nivel de relleno y
bandera de toque, y ademas que la serie vectorizada coincida con la referencia escalar `lux_imb.detect_og_vi`.

Que valida: la logica de deteccion y el ciclo de vida, DADAS esas barras. Que NO valida (por eso es parcial):
  - que las barras M1 sean las correctas (vienen del mismo bundle; no se contrastaron con los ticks);
  - otros activos, otros timeframes, otro `Extend`, filtro de ancho (el export usa el defecto: sin filtro), FVG;
  - la disponibilidad causal (`available_at`): el export no la trae, se toma el cierre de la barra actual.

    .venv\Scripts\python tools\verify_lux_imb_vs_6e_oracle.py --bundle viewer\nt8_bridge\bundles\6E_CONT.json
Sale 0 solo si TODO coincide en las dos geometrias esperadas (body = 100 %; wick = documenta la diferencia).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.research import lux_imb as L  # noqa: E402
from edgelab.research import lux_imb_series as S  # noqa: E402

FAM = {"OG": S.OG, "VI": S.VI}


def load(bundle: Path):
    d = json.loads(bundle.read_text(encoding="utf-8"))
    c = d["bar_series"]["time_1m"]["candles"]
    run = next(r for r in d["runs"] if r["indicator"] == "ImbalanceDetectorLuxAlgoMTF")
    a = lambda k: np.array([x[k] for x in c], dtype=float)  # noqa: E731
    bars = dict(t=np.array([x["time"] for x in c], dtype=np.int64), o=a("open"), h=a("high"), l=a("low"), c=a("close"))
    oracle = {}
    for z in run["zones"]:
        fam, dr = z["kind"].split()
        if fam not in FAM:
            continue
        oracle[(FAM[fam], 1 if dr == "BULL" else -1, int(z["t0"]))] = z
    return bars, oracle


def compare(bars, oracle, geometry):
    z = S.detect_series(bars["o"], bars["h"], bars["l"], bars["c"], og_geometry=geometry)
    lc = S.lifecycle(z, bars["t"], bars["h"], bars["l"])
    py = {}
    for k in range(len(z["i_prev"])):
        py[(int(z["family"][k]), int(z["direction"][k]), int(lc["t0"][k]))] = k
    keys_o, keys_p = set(oracle), set(py)
    res = dict(geometry=geometry, oracle=len(keys_o), python=len(keys_p), only_oracle=len(keys_o - keys_p),
               only_python=len(keys_p - keys_o), fields={})
    common = keys_o & keys_p
    for name, fn in (("bordes", lambda o, k: abs(o["top"] - z["top"][k]) < 1e-9 and abs(o["bottom"] - z["bottom"][k]) < 1e-9),
                     ("t1", lambda o, k: int(o["t1"]) == int(lc["t1"][k])),
                     ("fill_level", lambda o, k: abs(o["fill_level"] - lc["fill_level"][k]) < 1e-9),
                     ("touched", lambda o, k: bool(o.get("touches")) == bool(lc["touched"][k]))):
        res["fields"][name] = sum(1 for key in common if fn(oracle[key], py[key]))
    res["common"] = len(common)
    res["exact_zones"] = sum(1 for key in common if all(f(oracle[key], py[key]) for f in (
        lambda o, k: abs(o["top"] - z["top"][k]) < 1e-9 and abs(o["bottom"] - z["bottom"][k]) < 1e-9,
        lambda o, k: int(o["t1"]) == int(lc["t1"][k]),
        lambda o, k: abs(o["fill_level"] - lc["fill_level"][k]) < 1e-9,
        lambda o, k: bool(o.get("touches")) == bool(lc["touched"][k]))))
    return res, z


def vs_scalar(bars, z, geometry, sample=60000):
    """La serie vectorizada debe dar lo mismo que la referencia escalar de `lux_imb` (mismo orden de sucesos)."""
    n = min(sample, len(bars["t"]))
    B = [L.OhlcBar(datetime.fromtimestamp(int(bars["t"][i]), timezone.utc), *(float(bars[k][i]) for k in "ohlc")) for i in range(n)]
    ref = []
    for i in range(1, n):
        for zz in L.detect_og_vi(B[i - 1], B[i], og_geometry=geometry):
            ref.append((i - 1, 0 if zz.family == "OG" else 1, 1 if zz.direction == "bullish" else -1,
                        round(zz.top, 9), round(zz.bottom, 9)))
    m = z["i_prev"] < n - 1
    vec = [(int(a), int(b), int(c), round(float(d), 9), round(float(e), 9)) for a, b, c, d, e in
           zip(z["i_prev"][m], z["family"][m], z["direction"][m], z["top"][m], z["bottom"][m])]
    return sorted(ref) == sorted(vec), len(ref)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, default=REPO / "viewer/nt8_bridge/bundles/6E_CONT.json")
    a = ap.parse_args(argv)
    bars, oracle = load(a.bundle)
    print(f"barras M1: {len(bars['t']):,} | zonas OG+VI del export de NT8: {len(oracle):,}")
    out = {}
    for g in ("body", "wick"):
        r, z = compare(bars, oracle, g)
        same, nref = vs_scalar(bars, z, g)
        r["serie_vs_referencia_escalar"] = same
        out[g] = r
        print(f"\n[{g}] python={r['python']:,} coinciden en clave={r['common']:,} solo_oraculo={r['only_oracle']} solo_python={r['only_python']}")
        print("   campos:", {k: f"{v:,}/{r['common']:,}" for k, v in r["fields"].items()},
              f"| zonas exactas: {r['exact_zones']:,} | serie==escalar ({nref:,} zonas): {same}")
    b = out["body"]
    ok = (b["only_oracle"] == 0 and b["only_python"] == 0 and b["exact_zones"] == b["oracle"] and b["serie_vs_referencia_escalar"]
          and out["wick"]["serie_vs_referencia_escalar"])
    print("\nRESULTADO:", "PARCIAL_PASS (6E, M1, defecto de NT8): geometria cuerpo-a-cuerpo reproduce el export al 100 %" if ok else "FALLA")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
