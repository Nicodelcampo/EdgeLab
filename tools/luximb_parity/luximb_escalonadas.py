"""Picos escalonados (detector existente `tools/escalonadas_det.py`, familia «IPC estilo NQ», confirmacion por precio)
que suceden sobre un area cargada de zonas LUX-IMB (OG+VI) vivas. Target-free y causal.

- Detector sin cambios: `escalonadas_det.detectar_px` con FAMILIA_NQ sobre las velas 25t del bundle.
- Area de la escalonada al detectar: rango de precio [min low, max high] de las velas 25t desde el primer pico hasta la
  vela de deteccion (solo lo conocido en ese momento; nada de picos posteriores).
- Carga: zonas OG/VI vivas en la vela de deteccion (creadas antes, vida 500 min) que se solapan con ese rango.
- Se marca si la carga >= `--min-zonas` (y opcionalmente densidad cada 10 pts >= `--min-dens`).

Uso: python tools/luximb_parity/luximb_escalonadas.py <bundle.json> <out.json> [--min-zonas N] [--min-dens D]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import escalonadas_det as E  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle"); ap.add_argument("out")
    ap.add_argument("--min-zonas", type=int, default=0)
    ap.add_argument("--min-dens", type=float, default=0.0, help="zonas por cada 10 puntos de rango")
    a = ap.parse_args()
    B = json.load(open(a.bundle, encoding="utf-8"))
    E.TICK = float(B["meta"]["tick_size"])
    f = dict(E.FAMILIA_NQ)
    c = B["bar_series"]["tick_25"]["candles"]
    cd = {k: np.array([x[v] for x in c], float) for k, v in (("t", "time"), ("h", "high"), ("l", "low"), ("c", "close"))}
    Zs = B["runs"][0]["zones"]
    zav = np.array([z["available_ts"] for z in Zs]); zt1 = np.array([z["t1"] for z in Zs])
    ztop = np.array([z["top"] for z in Zs]); zbot = np.array([z["bottom"] for z in Zs])
    det = E.detectar_px(cd, f, f["conf"])
    out = []
    for z in det:
        i0, di = z["picos"][0][0], z["det_i"]
        lo, hi = float(cd["l"][i0:di + 1].min()), float(cd["h"][i0:di + 1].max())
        td = cd["t"][di]
        viva = (zav <= td) & (zt1 > td)
        sel = viva & (zbot <= hi) & (ztop >= lo)
        n = int(sel.sum()); dens = n / max((hi - lo) / 10.0, 1e-9)
        z.update(area_lo=lo, area_hi=hi, zonas_area=n, dens_10pts=round(dens, 3),
                 zona_ids=[Zs[k]["id"] for k in np.flatnonzero(sel)])
        z["marcada"] = n >= a.min_zonas and dens >= a.min_dens
        out.append(z)
    N = np.array([z["zonas_area"] for z in out]); D = np.array([z["dens_10pts"] for z in out])
    days = len(set((cd["t"] // 86400).astype(int)))
    marc = [z for z in out if z["marcada"]]
    res = dict(schema="EDGELAB_PEAKS_DET_V2_REGLA", asset=B["meta"]["id"],
               variante=f"Escalonadas IPC-NQ (precio {f['conf']} ticks) sobre area con >= {a.min_zonas} zonas LUX-IMB vivas",
               parametros=dict(familia=f, min_zonas=a.min_zonas, min_dens=a.min_dens), causal=True,
               total_detectadas=len(out), zonas_area_p10_50_90=np.percentile(N, [10, 50, 90]).tolist() if len(N) else [],
               dens_p10_50_90=np.percentile(D, [10, 50, 90]).round(3).tolist() if len(D) else [],
               zonas=marc, zonas_por_dia=round(len(marc) / max(days, 1), 2))
    json.dump(res, open(a.out, "w", encoding="utf-8"), separators=(",", ":"))
    print(json.dumps({k: v for k, v in res.items() if k != "zonas"}, default=str)[:900], "| marcadas", len(marc))


if __name__ == "__main__":
    main()
