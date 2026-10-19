#!/usr/bin/env python3
r"""Servidor del visor con aVolClusterPOI calculado en vivo por el espejo validado (avolclusterpoi_full.run_full:
paridad NT8 3.408/3.408 eventos en MNQ 12-26 50t). Sirve los archivos del visor y además:

  GET  /api/avcl/meta          → instrumento, ventana, defaults (los de NT8) y sesiones mostradas
  POST /api/avcl/run  {params} → corre run_full sobre TODA la historia cargada (calibración) y devuelve las zonas que
                                 tocan la ventana mostrada, con índices de barra relativos a las velas del bundle

Al arrancar arma ticks → barras 25t → footprints (regla NT8 de subserie 1-tick) UNA vez y escribe el bundle de velas
de las últimas N sesiones. Nada del holdout (sesión CME del 2026-10-01 en adelante) entra.

    E:\EdgeLab\.venv\Scripts\python viewer\nt8_bridge\server_avcl.py 8099 [--sesiones 5] [--ticks 25]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from edgelab.bridge import bars as B  # noqa: E402
from edgelab.bridge import ticks as T  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi_full import FULL_DEFAULTS, run_full  # noqa: E402

PARQUET = Path(r"E:\EdgeLab\data\nt8_reexport_20261005\MNQ\MNQ_12-26_ticks_ext.parquet")
CHART_TZ = "America/Argentina/Buenos_Aires"
START = pd.Timestamp("2026-07-14 19:00", tz=CHART_TZ).value       # sesión CME del 15-jul (como el chart de NT8)
END = pd.Timestamp("2026-09-30 22:00", tz="UTC").value             # apertura de la sesión del 1-oct = holdout
STATE = {}
LOCK = threading.Lock()


def prepare(n_ticks, n_sesiones):
    t0 = time.time()
    tk = T.load_canonical_parquet(str(PARQUET), start_utc_ns=START, end_utc_ns=END)
    ct = pd.to_datetime(tk.ts_ns, utc=True).tz_convert("America/Chicago")
    keep = np.asarray(~(((ct.hour * 60 + ct.minute) >= 960) & ((ct.hour * 60 + ct.minute) < 1020)))   # pausa CME
    tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None)
                                    for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")})
    bars = B.build_tick_bars(tk, n_ticks)
    fps = B.build_footprints(tk, bars, nt8_subseries=True)
    from edgelab.bridge.sessions import session_end_ns
    send = np.array([session_end_ns(int(x)) for x in bars.end_ns])
    starts = np.flatnonzero(np.r_[True, send[1:] != send[:-1]])
    off = int(starts[-n_sesiones]) if len(starts) >= n_sesiones else 0
    tick = float(tk.tick_size)
    candles = [dict(time=int(bars.end_ns[i]) // 1_000_000_000, open=bars.open_t[i] * tick, high=bars.high_t[i] * tick,
                    low=bars.low_t[i] * tick, close=bars.close_t[i] * tick, volume=float(bars.volume[i]))
               for i in range(off, len(bars.close_t))]
    aid = "MNQ_12-26_AVCL_%dT" % n_ticks
    name = "MNQ 12-26 · aVolClusterPOI (%dt, últimas %d sesiones)" % (n_ticks, n_sesiones)
    bundle = dict(meta=dict(id=aid, name=name, instrument="MNQ", contract="MNQ 12-26", tick_size=tick, precision=2,
                            n_zones=0, avcl_live=True),
                  bar_series={"tick_%d" % n_ticks: dict(kind="tick_%d" % n_ticks, name="%d Tick" % n_ticks,
                                                        candles=candles)}, runs=[])
    (HERE / "bundles").mkdir(exist_ok=True)
    (HERE / "bundles" / (aid + ".json")).write_text(json.dumps(bundle), encoding="utf-8")
    man = HERE / "bundles" / "manifest.js"
    txt = man.read_text(encoding="utf-8")
    if '"%s"' % aid not in txt:
        entry = dict(id=aid, name=name, group="MNQ (aVolClusterPOI en vivo)", instrument="MNQ", contract="MNQ 12-26",
                     tick_size=tick, precision=2, candles=len(candles), zones=0, rolls=0, parity_status="PARITY_PASS_50T")
        i = txt.find("window.ASSET_CATALOG = [") + len("window.ASSET_CATALOG = [\n")
        man.write_text(txt[:i] + "  " + json.dumps(entry) + ",\n" + txt[i:], encoding="utf-8")
    STATE.update(tk=tk, bars=bars, fps=fps, off=off, aid=aid, n=len(bars.close_t), tick=tick)
    print("listo: %d ticks, %d barras %dt, mostradas %d (desde barra %d) en %.0f s"
          % (len(tk.ts_ns), len(bars.close_t), n_ticks, len(candles), off, time.time() - t0), flush=True)


def run(params):
    p = {k: params[k] for k in FULL_DEFAULTS if k in params}
    with LOCK:
        t0 = time.time()
        r = run_full(STATE["tk"], STATE["bars"], STATE["fps"], p, chart_tz=CHART_TZ)
    path = (params.get("event_log_path") or "").strip()
    if path:                                                   # Event Log Path: mismos tipos de evento que el CSV de NT8
        pd.DataFrame(r["events"]).to_csv(path, index=False)
    off, n = STATE["off"], STATE["n"]
    ext = int(params.get("visual_extend_bars", 500))
    out = []
    for z in r["zones"]:
        end = z["ended_bar"] if not z["active"] else z["created_bar"] + ext
        if end < off:
            continue
        out.append(dict(id=z["id"], kind=z["kind"], direction=z["direction"], active=z["active"],
                        a=z["created_bar"] - off, b=(min(end, n - 1) - off), extends=bool(z["active"] and end >= n - 1),
                        lower_tick=z["lower_tick"], upper_tick=z["upper_tick"], label=z["label"], outcome=z["outcome"],
                        burst=z["burst_count"], state=z["state"], end_reason=z["end_reason"]))
    return dict(aid=STATE["aid"], seconds=round(time.time() - t0, 1), zones=out, dashboard=r["dashboard"],
                params=r["params"], tick_size=STATE["tick"])


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(HERE), **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, obj, code=200):
        b = json.dumps(obj, default=float).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/api/avcl/meta"):
            return self._json(dict(aid=STATE.get("aid"), defaults=FULL_DEFAULTS, ready="bars" in STATE))
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/avcl/run"):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return self._json(run(json.loads(self.rfile.read(n) or b"{}")))
            except Exception as e:                                   # el error se muestra en el panel
                return self._json(dict(error=str(e)), 400)
        self.send_error(404)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("port", type=int, nargs="?", default=8099)
    ap.add_argument("--sesiones", type=int, default=5); ap.add_argument("--ticks", type=int, default=25)
    a = ap.parse_args()
    prepare(a.ticks, a.sesiones)
    print("Sirviendo en http://127.0.0.1:%d" % a.port, flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
