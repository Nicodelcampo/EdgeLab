#!/usr/bin/env python3
"""Paridad Python <-> JS del campo de densidad sobre bundles REALES del visor.

**Target-free.** Sin retornos: compara dos implementaciones del mismo campo sobre datos de mercado.

Por qué existe. Los vectores dorados (`tests/fixtures/density_field_golden_v2.json`) son sintéticos y
cubren la lógica; lo que no pueden cubrir es la **suciedad de los datos reales**. La primera corrida de esta
herramienta encontró un defecto que ningún fixture sintético veía: zonas reales con `vol: null`, que Python
rechazaba con `TypeError` y el puerto JS habría tratado en silencio como 0 o NaN (un NaN contamina el
campo entero). Ver `density_field.zone_volume`.

Los bundles son datos locales (ignorados por git), así que esto no corre en CI: se corre a mano, o como parte de
la validación de paridad por activo.

    .venv\\Scripts\\python tools\\verify_density_parity_real_bundle.py ^
        --bundles-dir viewer/nt8_bridge/bundles --bundle 6B_09-25_25T --bundle ZB_06-26_202605_25T_HFT

Sale 0 si TODOS los casos coinciden (densidad ≤ 2e-8, mismos IDs, corredores, murallas y direcciones).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.research.corridor_geometry import characterize_corridors  # noqa: E402
from edgelab.research.density_field import (  # noqa: E402
    compute_field, detect_density_intervals, price_to_tick, to_nanoseconds)

DF_JS = REPO / "viewer" / "nt8_bridge" / "density_field.js"
PRESETS = {
    "HP007_CALIBRATED": {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2,
                         "vol_transform": "TRANS_POWER_025", "use_maturation": True, "use_time_decay": True,
                         "use_wear": True, "saturation": True},
    "FIELD_RAW_STATIC": {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2},
}
JS = r"""
const DF = require(process.argv[1]);
const inp = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = [];
for (const c of inp.casos) {
  const f = DF.computeField(inp.zones, c.t, inp.tick, c.pmin, c.pmax, inp.cfg);
  const i = DF.detectDensityIntervals(f.density, f.priceTickMin, inp.tick, {min_low_ticks: inp.min_low});
  const ch = DF.characterizeCorridors(i, inp.zones, f.activeZoneIds, inp.tick, DF.toNanoseconds(c.t));
  out.push({density: f.density, ids: f.activeZoneIds, low: i.low_density_intervals.map(x => [x.tick_start, x.tick_end]),
            high: i.high_density_regions.map(x => [x.tick_start, x.tick_end]), dirs: ch.map(x => [x.id, x.direction])});
}
process.stdout.write(JSON.stringify(out));
"""


def zonas_del_bundle(path: Path, max_zonas: int):
    d = json.loads(path.read_text(encoding="utf-8"))
    tick = float(d.get("meta", {}).get("tick_size", 0.25))
    run = (d.get("runs") or [None])[0]
    zs = run["zones"] if run else d.get("zones", [])
    out = []
    for i, z in enumerate(zs):
        if z.get("available_ns") is None and z.get("available_ts") is None:
            continue                              # sin disponibilidad explicita: no entra (politica estricta)
        lo, hi = z.get("bottom", z.get("lo")), z.get("top", z.get("hi"))
        if lo is None or hi is None:
            continue
        av = z["available_ns"] / 1e9 if z.get("available_ns") is not None else z["available_ts"]
        out.append({"id": str(z.get("id", i)), "bottom": min(lo, hi), "top": max(lo, hi), "vol": z.get("vol"),
                    "kind": z.get("kind"), "available_ts": av})
    return tick, out[:max_zonas]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles-dir", required=True, type=Path)
    ap.add_argument("--bundle", action="append", required=True, help="nombre sin extension; repetible")
    ap.add_argument("--preset", default="HP007_CALIBRATED", choices=sorted(PRESETS))
    ap.add_argument("--max-zonas", type=int, default=6000)
    ap.add_argument("--min-low-ticks", type=int, default=7)
    ap.add_argument("--instantes", default="0.3,0.55,0.8,0.98", help="cuantiles de disponibilidad")
    a = ap.parse_args(argv)

    cfg = PRESETS[a.preset]
    cuantiles = [float(x) for x in a.instantes.split(",")]
    malos = total = 0
    print(f"{'bundle':30s} {'tRef':14s} {'zonas':>6s} {'activas':>7s} {'ticks':>6s} {'max|diff|':>10s}  ids corr muros dir")
    for nom in a.bundle:
        tick, zonas = zonas_del_bundle(a.bundles_dir / f"{nom}.json", a.max_zonas)
        if len(zonas) < 50:
            print(f"{nom:30s} pocas zonas con disponibilidad explicita ({len(zonas)}): se omite")
            continue
        ts = sorted(z["available_ts"] for z in zonas)
        casos = []
        for q in cuantiles:
            t = ts[int(q * (len(ts) - 1))] + 1.0
            el = [z for z in zonas if z["available_ts"] <= t]
            casos.append({"t": t, "pmin": min(price_to_tick(z["bottom"], tick) for z in el) - 20,
                          "pmax": max(price_to_tick(z["top"], tick) for z in el) + 20})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump({"zones": zonas, "tick": tick, "cfg": cfg, "casos": casos, "min_low": a.min_low_ticks}, fh)
            tmp = fh.name
        r = subprocess.run(["node", "-e", JS, str(DF_JS), tmp], capture_output=True, text=True, encoding="utf-8")
        Path(tmp).unlink(missing_ok=True)
        if r.returncode != 0:
            print(f"{nom}: FALLO EL PUERTO JS: {r.stderr[:300]}")
            return 2
        for c, o in zip(casos, json.loads(r.stdout)):
            res = compute_field(zonas, c["t"], tick, c["pmin"], c["pmax"], cfg)
            inter = detect_density_intervals(res["density"], res["price_ticks"], tick, min_low_ticks=a.min_low_ticks)
            ch = characterize_corridors(inter, zonas, res["active_zone_ids"], tick, to_nanoseconds(c["t"]))
            maxd = max(abs(x - y) for x, y in zip(res["density"], o["density"]))
            ok = (res["active_zone_ids"] == o["ids"],
                  [[x["tick_start"], x["tick_end"]] for x in inter["low_density_intervals"]] == o["low"],
                  [[x["tick_start"], x["tick_end"]] for x in inter["high_density_regions"]] == o["high"],
                  [[x["id"], x["direction"]] for x in ch] == o["dirs"])
            total += 1
            if not (all(ok) and maxd <= 2e-8):
                malos += 1
            print(f"{nom:30s} {c['t']:14.0f} {len(zonas):6d} {len(res['active_zone_ids']):7d} {len(res['density']):6d} "
                  f"{maxd:10.2e}  " + "   ".join("T" if x else "F" for x in ok))
    print(f"\ncasos: {total} | con diferencia: {malos}")
    return 0 if malos == 0 and total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
