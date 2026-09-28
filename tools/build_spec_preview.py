#!/usr/bin/env python3
r"""Vista previa CIEGA de una especificación de entradas, para revisión visual antes de correr (Nico confirma).

    .venv\Scripts\python tools\build_spec_preview.py --spec docs\specs\SPEC_6E_L2_ABSORPTION_20260924.json

Qué hace:
- Detecta los eventos de la población declarada en la spec (hoy: absorciones L2 causales) en las sesiones de
  `data.preview_sessions`.
- Toma una muestra estratificada por sesión (semilla fija, sin elegir "lindos").
- Por cada ejemplo guarda SOLO el pasado: velas de 15 s de los 15 min previos, el nivel absorbido, la entrada
  (precio al bid/ask vigente tras la latencia) y el rango previo. **Ningún precio posterior a la entrada entra al
  archivo**: la ceguera es de datos, no de CSS. La geometría de stop/target/BE/tiempo la dibuja el visor desde la
  grilla de la spec.
- Resumen target-free: eventos por sesión y por hora, superposición entre eventos por tiempo máximo.
- Publica el sha256 de la spec (lo que se confirma) y de la vista previa.

Salida: `viewer/nt8_bridge/bundles/spec_<spec_id>.json`. Se abre en `spec_review.html?spec=<spec_id>`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.research.l2_manipulation_heuristics import ASK, AbsorptionTracker  # noqa: E402

US = 1_000_000
LATENCY_US = 250_000
LOOKBACK_S = 15 * 60
CANDLE_S = 15


def spec_sha256(path: Path) -> str:
    """Hash de la spec canónica (JSON re-serializado ordenado): lo que Nico confirma."""
    obj = json.loads(path.read_text(encoding="utf-8"))
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def session_events(base: Path, s: str):
    """Absorciones causales de una sesión + series de cotización y trades (solo para mirar hacia atrás)."""
    t = pq.read_table(base / "l1_quotes" / f"{s}.parquet", columns=["side", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
    t = t.sort_values("source_row", kind="stable")
    side, px, sz, ts = (t[c].to_numpy() for c in ("side", "price_tick", "size", "ts_us"))
    ab = AbsorptionTracker()                      # causal por defecto
    bid = ask = None
    q_ts, q_bid, q_ask, tr_ts, tr_px, tr_sz = [], [], [], [], [], []
    for sd, p, z, tt in zip(side, px, sz, ts):
        if sd == 0:
            ask = int(p); q_ts.append(int(tt)); q_bid.append(bid); q_ask.append(ask)
        elif sd == 1:
            bid = int(p); q_ts.append(int(tt)); q_bid.append(bid); q_ask.append(ask)
        elif sd == 2:
            agg = 1 if (ask is not None and p >= ask) else (-1 if (bid is not None and p <= bid) else 0)
            ab.on_trade(int(p), int(tt), float(z), agg)
            tr_ts.append(int(tt)); tr_px.append(int(p)); tr_sz.append(int(z))
    q = dict(ts=np.array(q_ts, dtype=np.int64),
             bid=np.array([np.nan if v is None else v for v in q_bid], dtype=float),
             ask=np.array([np.nan if v is None else v for v in q_ask], dtype=float))
    tr = dict(ts=np.array(tr_ts, dtype=np.int64), px=np.array(tr_px, dtype=np.int64), sz=np.array(tr_sz))
    return ab.candidates(), q, tr


def past_candles(tr, t_end_us: int):
    """Velas de 15 s con trades ESTRICTAMENTE anteriores a la entrada (ceguera de datos)."""
    lo = np.searchsorted(tr["ts"], t_end_us - LOOKBACK_S * US, side="left")
    hi = np.searchsorted(tr["ts"], t_end_us, side="left")
    ts, px = tr["ts"][lo:hi], tr["px"][lo:hi]
    out = []
    if not len(ts):
        return out
    b = ts // (CANDLE_S * US)
    for k in np.unique(b):
        m = b == k
        p = px[m]
        out.append(dict(time=int(k * CANDLE_S), open=int(p[0]), high=int(p.max()), low=int(p.min()), close=int(p[-1])))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=REPO / "viewer" / "nt8_bridge" / "bundles")
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    base = Path(spec["data"]["base"])
    rng = np.random.default_rng(spec["sample"]["seed"])
    per_session, pools = {}, {}
    holds = spec["grid"]["max_hold_s"]
    overlap = {h: [0, 0] for h in holds}
    hours = {}
    for s in spec["data"]["preview_sessions"]:
        cands, q, tr = session_events(base, s)
        cands = sorted(cands, key=lambda c: c["available_ts_us"])
        per_session[s] = len(cands)
        ev = []
        for c in cands:
            t_in = c["available_ts_us"] + LATENCY_US
            j = np.searchsorted(q["ts"], t_in, side="right") - 1
            if j < 0 or np.isnan(q["bid"][j]) or np.isnan(q["ask"][j]):
                continue
            short = c["side"] == ASK                               # compras absorbidas en el ask -> SHORT
            entry = q["bid"][j] if short else q["ask"][j]
            lo = np.searchsorted(tr["ts"], t_in - 60 * US, side="left"); hi = np.searchsorted(tr["ts"], t_in, side="left")
            rng60 = int(tr["px"][lo:hi].max() - tr["px"][lo:hi].min()) if hi > lo else 0
            ev.append(dict(session=s, entry_ts_us=int(t_in), side="SHORT" if short else "LONG", level_tick=int(c["tick"]),
                           entry_tick=int(entry), absorbed_volume=float(c["attributed_volume"]),
                           trades_in_window=int(c["trade_count"]), window_start_ts_us=int(c["window_start_ts_us"]),
                           threshold=float(c["volume_threshold"]), range60_ticks=rng60,
                           spread_ticks=float(q["ask"][j] - q["bid"][j])))
            hours[str((t_in // US // 3600) % 24)] = hours.get(str((t_in // US // 3600) % 24), 0) + 1
        for h in holds:                                            # eventos que caerian adentro de una posicion previa
            last = -10 ** 18
            for e in ev:
                overlap[h][1] += 1
                if e["entry_ts_us"] < last + h * US:
                    overlap[h][0] += 1
                else:
                    last = e["entry_ts_us"]
        pools[s] = ev
        print(json.dumps(dict(session=s, events=len(ev))), flush=True)
    # muestra estratificada: ronda por sesiones en orden aleatorio, un evento al azar por sesión y vuelta
    examples, order = [], list(pools)
    rng.shuffle(order)
    remaining = {s: list(rng.permutation(len(pools[s]))) for s in order}
    while len(examples) < spec["sample"]["examples"] and any(remaining.values()):
        for s in order:
            if remaining[s] and len(examples) < spec["sample"]["examples"]:
                e = dict(pools[s][remaining[s].pop()])
                e["candles"] = past_candles_cache(base, s, e["entry_ts_us"])
                e["id"] = len(examples) + 1
                examples.append(e)
    body = dict(schema="EDGELAB_SPEC_PREVIEW_V1", spec=spec, spec_sha256=spec_sha256(a.spec),
                spec_path=str(a.spec).replace("\\", "/"), blind=True,
                blind_note="Ningún precio posterior a la entrada está en este archivo.",
                latency_ms=LATENCY_US // 1000, candle_s=CANDLE_S, lookback_s=LOOKBACK_S,
                summary=dict(sessions=len(per_session), events_total=int(sum(per_session.values())),
                             events_per_session=per_session, events_by_hour_art=hours,
                             overlap_fraction_by_hold={str(h): (v[0] / v[1] if v[1] else 0.0) for h, v in overlap.items()},
                             median_range60_ticks=float(np.median([e["range60_ticks"] for p in pools.values() for e in p])) if any(pools.values()) else None,
                             median_spread_ticks=float(np.median([e["spread_ticks"] for p in pools.values() for e in p])) if any(pools.values()) else None),
                examples=examples)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["preview_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    a.out.mkdir(parents=True, exist_ok=True)
    out = a.out / f"spec_{spec['spec_id']}.json"
    out.write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(dict(out=str(out), examples=len(examples), events=body["summary"]["events_total"],
                          spec_sha256=body["spec_sha256"][:12], preview_sha256=body["preview_sha256"][:12])))
    return 0


_TR_CACHE: dict = {}


def past_candles_cache(base: Path, s: str, t_end_us: int):
    if s not in _TR_CACHE:
        _TR_CACHE.clear()
        t = pq.read_table(base / "l1_quotes" / f"{s}.parquet", columns=["side", "price_tick", "ts_us", "source_row"]).to_pandas()
        t = t[t.side == 2].sort_values("source_row", kind="stable")
        _TR_CACHE[s] = dict(ts=t.ts_us.to_numpy(np.int64), px=t.price_tick.to_numpy(np.int64))
    return past_candles(_TR_CACHE[s], t_end_us)


if __name__ == "__main__":
    raise SystemExit(main())
