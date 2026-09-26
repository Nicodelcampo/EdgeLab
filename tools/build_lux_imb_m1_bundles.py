#!/usr/bin/env python3
r"""Barras M1 desde ticks pre-holdout + zonas LUX-IMB (OG + VI) para todos los activos, como bundles del visor.

**Target-free.** Geometria de barras; sin retornos ni senales. Reconstruccion en Python del indicador
`ImbalanceDetectorLuxAlgoMTF` (FVG apagado) validada PARCIALMENTE contra el export de NT8 de 6E
(`tools/verify_lux_imb_vs_6e_oracle.py`, `docs/research/LUX_IMB_VALIDACION_PARCIAL_6E_20260921.md`).
Sin oraculo propio, los demas activos quedan `PARITY_ABSTAIN`.

- Un bundle por CONTRATO (`<ACTIVO>_<contrato>_M1`), con la serie `time_1m` y una corrida LUX-IMB.
- Las barras salen de los ticks de las ventanas de sesion ya auditadas en los manifiestos de los bundles 25t
  (todas pre-holdout; el constructor lo verifica). Minuto UTC real; una barra por minuto con al menos un tick
  (los minutos sin operaciones no generan barra, como en NT8).
- Alineacion: minuto UTC estandar (`--tick-offset-s 0`). HALLAZGO: las barras M1 del export de NT8 de 6E
  (`6E_CONT.json`) solo se reproducen desplazando los ticks +30 s (1.319/1.331 barras OHLC exactas el 2026-06-23,
  contra ~15 % con alineacion estandar). No se sabe si es convencion de NT8 o del generador de ese bundle; los
  bundles del oraculo de LUX-IMB usan ESAS barras. Ver docs/research/LUX_IMB_VALIDACION_PARCIAL_6E_20260921.md.
- `og_geometry="body"` por defecto: es la que reproduce el export de NT8 (decision pendiente de Nico: `wick`).

    .venv\Scripts\python tools\build_lux_imb_m1_bundles.py --workers 3
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.research import lux_imb_series as S  # noqa: E402

HOLDOUT_NS = 1782856800000000000
COLORS = {1: "#2157f3", -1: "#ff1100"}
PRECISION = {"6E": 5, "6B": 4, "6J": 7, "ES": 2, "MES": 2, "NQ": 2, "MNQ": 2, "YM": 0, "GC": 1, "ZB": 5, "MBT": 0}


def build_m1(ts_ns, price_ticks, volume, tick_size):
    """Barras de 1 minuto UTC. Devuelve arrays (t, o, h, l, c, v) con precio en unidades reales."""
    if len(ts_ns) == 0:
        e = np.array([])
        return e.astype(np.int64), e, e, e, e, e
    minute = ts_ns // 60_000_000_000
    starts = np.concatenate(([0], np.flatnonzero(np.diff(minute)) + 1))
    p = price_ticks.astype(np.float64) * tick_size
    ends = np.concatenate((starts[1:], [len(ts_ns)]))
    t = (minute[starts] * 60).astype(np.int64)
    return (t, p[starts], np.maximum.reduceat(p, starts), np.minimum.reduceat(p, starts), p[ends - 1],
            np.add.reduceat(volume.astype(np.float64), starts))


def merge_same_minute(t, o, h, l, c, v):
    """Une barras del mismo minuto (una sesion que termina y otra que empieza dentro del mismo minuto)."""
    if len(t) < 2 or not (np.diff(t) == 0).any():
        return t, o, h, l, c, v
    out = []
    for i in range(len(t)):
        if out and out[-1][0] == t[i]:
            b = out[-1]
            out[-1] = [b[0], b[1], max(b[2], h[i]), min(b[3], l[i]), c[i], b[5] + v[i]]
        else:
            out.append([t[i], o[i], h[i], l[i], c[i], v[i]])
    a = np.array(out, dtype=float)
    return a[:, 0].astype(np.int64), a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]


def contracts_from_manifests(bundles: Path):
    """{(instrumento, contrato): (parquet, {trade_date: (start_ns, end_ns)})} desde los manifiestos 25t."""
    out = {}
    for f in sorted(bundles.glob("*.manifest.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        if "sessions" not in m or "source_sha256" not in m:
            continue
        key = (m["instrument"], m["contract"])
        rec = out.setdefault(key, [m["source_path"], {}])
        for s in m["sessions"]:
            rec[1].setdefault(int(s["trade_date"]), (int(s["start_utc_ns"]), int(s["end_utc_ns"])))
    return out


def build_contract(args):
    inst, contract, path, sessions, out_dir, offset_s = args
    parts = []
    tick_size = None
    for day in sorted(sessions):
        start_ns, end_ns = sessions[day]
        tk = load_canonical_parquet(path, contract=contract, instrument=inst, start_utc_ns=start_ns, end_utc_ns=end_ns)
        if len(tk) == 0:
            continue
        if int(tk.ts_ns[-1]) >= HOLDOUT_NS:
            raise SystemExit(f"HOLDOUT decodificado en {inst} {contract} {day}")
        tick_size = float(tk.tick_size)
        parts.append(build_m1(tk.ts_ns + offset_s * 1_000_000_000, tk.price_ticks, tk.volume, tk.tick_size))
    if not parts:
        return inst, contract, 0, 0
    t, o, h, l, c, v = (np.concatenate([p[i] for p in parts]) for i in range(6))
    order = np.argsort(t, kind="stable")
    t, o, h, l, c, v = merge_same_minute(*(a[order] for a in (t, o, h, l, c, v)))
    z = S.detect_series(o, h, l, c, og_geometry="body")
    lc = S.lifecycle(z, t, h, l)
    zones = []
    counters = {"OG": 0, "VI": 0}
    for k in range(len(z["i_prev"])):
        fam = "OG" if z["family"][k] == S.OG else "VI"
        d = int(z["direction"][k])
        counters[fam] += 1
        i_prev = int(z["i_prev"][k])
        zones.append({"id": f"MTF_{fam}_{counters[fam]}", "source": "luxalgo", "kind": f"{fam} {'BULL' if d > 0 else 'BEAR'}",
                      "top": float(z["top"][k]), "bottom": float(z["bottom"][k]), "t0": int(lc["t0"][k]), "t1": int(lc["t1"][k]),
                      "available_ts": int(t[min(i_prev + 1, len(t) - 1)] + 60), "state": "ACTIVE",
                      "fill_level": float(lc["fill_level"][k]), "color": COLORS[d], "label": fam,
                      "touched": bool(lc["touched"][k]), "touches": int(lc["touched"][k])})
    candles = [{"time": int(t[i]), "open": float(o[i]), "high": float(h[i]), "low": float(l[i]), "close": float(c[i]),
                "volume": float(v[i])} for i in range(len(t))]
    aid = f"{inst}_{contract.split(' ', 1)[1]}_M1"
    prec = PRECISION.get(inst, 2)
    bundle = {
        "meta": dict(id=aid, instrument=inst, contract=f"{contract} M1", tick_size=tick_size, precision=prec,
                     chart_tz="UTC", n_candles=len(candles), n_zones=len(zones), rolls=[], kind="M1_LUX_IMB",
                     outcome_firewall="ENFORCED", holdout_boundary_ns=HOLDOUT_NS, sessions=len(sessions),
                     og_geometry="body", semantics_id=S.SEMANTICS_ID, tick_offset_s=offset_s),
        "bar_series": {"time_1m": {"kind": "time_1m", "name": "1 Minuto (desde ticks)", "param": 1, "candles": candles}},
        "runs": [{"id": "lux_imb_python_body", "name": "Imbalance MTF [LuxAlgo] (OG + VI · Python, cuerpo)",
                  "indicator": "ImbalanceDetectorLuxAlgoMTF", "author": "LuxAlgo / reconstruccion Python",
                  "license": "CC BY-NC-SA 4.0", "bar_key": "time_1m", "zones": zones, "has_oracle": False,
                  "parity": {"status": "PARITY_ABSTAIN", "gate": "PARITY_ABSTAIN"},
                  "parity_reference": "validacion parcial: 6E contra export NT8 (34179/34179)"}],
    }
    p = out_dir / f"{aid}.json"
    p.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    return inst, contract, len(candles), len(zones)


def register(out_dir: Path, rows):
    mf = out_dir / "manifest.js"
    txt = mf.read_text(encoding="utf-8")
    cat = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
    ids = {f"{i}_{c.split(' ', 1)[1]}_M1" for i, c, _, _ in rows}
    cat = [e for e in cat if e.get("id") not in ids]
    for inst, contract, nc, nz in rows:
        aid = f"{inst}_{contract.split(' ', 1)[1]}_M1"
        b = json.loads((out_dir / f"{aid}.json").read_text(encoding="utf-8"))["meta"]
        cat.append(dict(id=aid, name=f"{contract} · M1 · LUX-IMB", group=f"M1 LUX-IMB {inst}", instrument=inst, contract=contract,
                        tick_size=b["tick_size"], precision=b["precision"], candles=nc, zones=nz, rolls=0,
                        parity_status="PARITY_ABSTAIN", kind="M1_LUX_IMB"))
    mf.write_text("window.ASSET_CATALOG = " + json.dumps(cat, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles", type=Path, default=REPO / "viewer/nt8_bridge/bundles")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", help="prefijo de activo (prueba), p.ej. 6E")
    ap.add_argument("--tick-offset-s", type=int, default=0,
                    help="desplaza los ticks antes de agrupar. 0 = minuto UTC estandar. El export de NT8 de 6E se reproduce con 30")
    a = ap.parse_args(argv)
    conts = contracts_from_manifests(a.bundles)
    jobs = [(i, c, p, s, a.bundles, a.tick_offset_s) for (i, c), (p, s) in sorted(conts.items()) if not a.only or i == a.only]
    print(f"{len(jobs)} contratos", flush=True)
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for inst, contract, nc, nz in ex.map(build_contract, jobs):
            print(f"{inst:4s} {contract:10s} barras M1={nc:8d} zonas LUX={nz:7d}", flush=True)
            if nc:
                rows.append((inst, contract, nc, nz))
    register(a.bundles, rows)
    print(json.dumps({"bundles": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
