"""Bandas de concentración OG+VI sobre un bundle LUX-IMB M1 del visor: lista de bandas y calibración del umbral.

  python tools/luximb_parity/bandas_concentracion.py --bundle viewer/nt8_bridge/bundles/EURUSD_DUKAS_M1_LUXIMB.json \
      --alto-pips 8 --umbral 22 --out bandas.json [--calibrar 18,20,22,25]

Target-free: sólo zonas y horas, no lee precios de cierre ni desenlaces. Regla: `edgelab/bridge/indicators/bandas_concentracion.py`.
"""
from __future__ import annotations

import argparse, json, sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from edgelab.bridge.indicators.bandas_concentracion import detectar  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True, type=Path)
    ap.add_argument("--alto-pips", type=float, default=8.0)
    ap.add_argument("--umbral", type=int, default=22)
    ap.add_argument("--calibrar", default="")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    d = json.loads(a.bundle.read_text(encoding="utf-8"))
    tk = d["meta"]["tick_size"]; pip = tk * 10 if tk < 0.001 else tk
    zonas = [z for z in d["runs"][0]["zones"] if z.get("source") == "luxalgo"]
    T = [c["time"] for c in d["bar_series"]["time_1m"]["candles"]]
    dias = (T[-1] - T[0]) / 86400 * 5 / 7
    for k in [int(x) for x in a.calibrar.split(",") if x]:
        b = detectar(zonas, T, a.alto_pips * pip, k)
        print(json.dumps({"umbral": k, "bandas": len(b), "por_2_dias": round(len(b) / dias * 2, 2),
                          "horas_media": round(sum(x.t1 - x.t0 for x in b) / max(len(b), 1) / 3600, 1)}))
    b = detectar(zonas, T, a.alto_pips * pip, a.umbral)
    res = {"bundle": d["meta"]["id"], "alto_pips": a.alto_pips, "umbral": a.umbral, "vida_min": 500,
           "dias_habiles": round(dias, 1), "n_bandas": len(b), "bandas": [asdict(x) for x in b]}
    if a.out: a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "bandas"}))


if __name__ == "__main__":
    main()
