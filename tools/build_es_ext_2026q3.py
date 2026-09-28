#!/usr/bin/env python3
r"""Canoniza la extensión jul-sep 2026 de ES o NQ (enmienda HOLDOUT-A1, 26/09) desde la historia del AddOn de NT8.

- Fuente: E:\DatosNT8\tick_history\ES_09-26 y ES_12-26 (*.Last.utc.txt, días locales de NT8 en hora argentina,
  timestamps en UTC) + manifest.jsonl de procedencia del AddOn.
- Ventana: desde la frontera vieja (sesión CME del 1-jul, 2026-06-30 17:00 CT) hasta ANTES del holdout nuevo
  (sesión CME del 1-oct, 2026-09-30 17:00 CT). Lo anterior ya vive en research-v2 (inmutable, no se toca).
- Salida: E:\EdgeLab\data\nt8_ext_2026q3\ES_parquet\ES_<cc>_ticks_ext.parquet (esquema canonical_tick_v1, igual a
  research-v2: price_ticks = precio / 0,25) + manifiesto por contrato + catálogo de sesiones con completitud.
- Sesión completa: ≥ 200.000 ticks, ningún hueco > 30 min fuera de la pausa 16-17 CT y ≥ 22,5 h entre el primer y el último tick. Las incompletas se listan y
  quedan fuera del catálogo canónico.
- Contrato por sesión: regla canónica (líder de la sesión completa anterior, sólo hacia adelante).

    .venv\Scripts\python tools\build_es_ext_2026q3.py [ES|NQ]
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd  # noqa: E402
from build_mym_canonical import file_sha256, parse_line_batch  # noqa: E402

SRC = Path(r"E:\DatosNT8\tick_history")
OUT = Path(r"E:\EdgeLab\data\nt8_ext_2026q3\ES_parquet")
CAT = REPO / "docs" / "research" / "contract_regimes" / "ES_ext_2026q3_sessions_catalog.json"
START_NS = 1_782_856_800 * 1_000_000_000      # 2026-06-30 17:00 CT = apertura de la sesión CME del 1-jul (frontera vieja)
END_NS = 1_790_805_600 * 1_000_000_000        # 2026-09-30 17:00 CT = apertura de la sesión del 1-oct (holdout nuevo)
TICK = 0.25
CATS = ["buy", "sell", "unclassified"]
CONTRACTS = {"ES 09-26": "ES_09-26", "ES 12-26": "ES_12-26"}
INST = "ES"


def set_inst(inst):
    """ES o NQ (tick 0,25 los dos): rutas, contratos y catálogo del instrumento."""
    global INST, OUT, CAT, CONTRACTS
    INST = inst
    OUT = Path(r"E:\EdgeLab\data\nt8_ext_2026q3") / f"{inst}_parquet"
    CAT = REPO / "docs" / "research" / "contract_regimes" / f"{inst}_ext_2026q3_sessions_catalog.json"
    CONTRACTS = {f"{inst} 09-26": f"{inst}_09-26", f"{inst} 12-26": f"{inst}_12-26"}


MIN_TICKS, MAX_GAP_S, MIN_SPAN_H = 200_000, 1800, 22.5   # sesión CME 17:00-16:00 CT = 23 h


def build(contract, folder):
    pq_path = OUT / f"{folder}_ticks_ext.parquet"
    cache = OUT / f"{folder}_sessions_ext.json"
    if pq_path.exists() and cache.exists():
        return pq_path, {int(k): v for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
    files = sorted((SRC / folder).glob("*.Last.utc.txt"))
    OUT.mkdir(parents=True, exist_ok=True)
    pq_path = OUT / f"{folder}_ticks_ext.parquet"
    writer, n, last_ts, nonmono, bad, dropped = None, 0, None, 0, 0, 0
    per = defaultdict(lambda: dict(ticks=0, first=None, last=None, max_gap_s=0.0))
    src_sha = {}
    for f in files:
        src_sha[f.name] = file_sha256(f)
        for chunk in pd.read_csv(f, sep=";", header=None, dtype={0: str}, chunksize=500_000, names=[0, 1, 2, 3, 4], on_bad_lines="skip"):
            ts, last, bid, ask, vol, malas = parse_line_batch(chunk)
            bad += malas
            keep = (ts >= START_NS) & (ts < END_NS)
            dropped += int((~keep).sum())
            ts, last, bid, ask, vol = ts[keep], last[keep], bid[keep], ask[keep], vol[keep]
            k = len(ts)
            if not k:
                continue
            if last_ts is not None and ts[0] < last_ts:
                nonmono += 1
            nonmono += int((np.diff(ts) < 0).sum())
            px, bd, ak = (np.round(x / TICK).astype(np.int64) for x in (last, bid, ask))
            if max(float(np.abs(last / TICK - px).max()), float(np.abs(bid / TICK - bd).max()), float(np.abs(ask / TICK - ak).max())) > 1e-6:
                raise ValueError(f"grilla de precios rota en {contract} {f.name}")
            cod = np.where(px >= ak, 0, np.where(px <= bd, 1, 2)).astype(np.int8)
            # completitud por sesión CME (huecos fuera de la pausa diaria)
            td = trade_date_ymd(ts); mb = is_maintenance_break(ts)
            prev = np.r_[last_ts if last_ts is not None else ts[0], ts[:-1]]
            gap = (ts - prev) / 1e9
            for d in np.unique(td):
                m = td == d; s = per[int(d)]
                s["ticks"] += int(m.sum())
                s["first"] = int(ts[m][0]) if s["first"] is None else s["first"]
                s["last"] = int(ts[m][-1])
                g = gap[m & ~mb]
                if s["first"] != int(ts[m][0]):          # el hueco con el trozo anterior cuenta sólo dentro de la sesión
                    s["max_gap_s"] = max(s["max_gap_s"], float(g.max()) if len(g) else 0.0)
                elif len(g) > 1:
                    s["max_gap_s"] = max(s["max_gap_s"], float(g[1:].max()))
            last_ts = int(ts[-1])
            seq = np.arange(n, n + k, dtype=np.int64)
            t = pa.table({"ts_utc_ns": ts, "ts_local_ns": ts, "sequence": seq, "price_ticks": px, "bid_ticks": bd, "ask_ticks": ak,
                          "volume": vol.astype(np.int32),
                          "aggressor": pa.DictionaryArray.from_arrays(pa.array(cod, pa.int8()), pa.array(CATS)).cast(pa.string()),
                          "tick_type": pa.array(["trade"] * k), "instrument": pa.array([INST] * k), "contract": pa.array([contract] * k),
                          "source_file": pa.array([str(f)] * k), "source_row": seq})
            if writer is None:
                writer = pq.ParquetWriter(pq_path, t.schema, compression="snappy")
            writer.write_table(t); n += k
    writer.close()
    if nonmono:
        raise ValueError(f"{contract}: {nonmono} timestamps no monótonos")
    man = dict(schema_version="canonical_tick_v1", tool="tools/build_es_ext_2026q3.py", amendment="HOLDOUT-A1 (2026-09-26)",
               generated_utc=datetime.now(timezone.utc).isoformat(), instrument=INST, contract=contract, rows=n, tick_size=TICK,
               window_utc_ns=[START_NS, END_NS], rows_outside_window_dropped=dropped, lineas_no_parseadas=bad,
               parquet_sha256=file_sha256(pq_path), source_files_sha256=src_sha,
               nota="ts_local_ns duplica ts_utc_ns y sequence es índice de fila (igual que research-v2, P-28)")
    (OUT / f"{folder}_manifest_ext.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    cache.write_text(json.dumps({str(k): v for k, v in per.items()}), encoding="utf-8")
    print(contract, "filas", n, "fuera de ventana", dropped, flush=True)
    return pq_path, per


def session_complete(s):
    """Sesión completa: mismos criterios que el catálogo (ticks, span y hueco máximo). Lo usa también la regla de roll."""
    return bool(s and s["ticks"] >= MIN_TICKS and (s["last"] - s["first"]) / 3.6e12 >= MIN_SPAN_H and s["max_gap_s"] <= MAX_GAP_S)


def main():
    set_inst(sys.argv[1] if len(sys.argv) > 1 else "ES")
    per_c, paths = {}, {}
    for c, f in CONTRACTS.items():
        paths[c], per_c[c] = build(c, f)
    days = sorted(set().union(*[set(p) for p in per_c.values()]))
    cur, out, bad = None, [], []
    for i, d in enumerate(days):
        cands = {c: per_c[c][d] for c in CONTRACTS if d in per_c[c]}
        if cur is None:
            cur = f"{INST} 09-26"                                   # continuidad con research-v2 (ES 09-26 al 30-jun)
        elif i > 0:
            prev = {c: per_c[c].get(days[i - 1], {}).get("ticks", 0) for c in CONTRACTS}
            lead = max(prev, key=prev.get)
            if lead > cur and prev[lead] > prev[cur] and session_complete(per_c[lead].get(days[i - 1])):   # auditoría 046 §5: el líder tiene que tener la sesión anterior COMPLETA (ticks, span y huecos), no sólo ticks
                cur = lead
        s = cands.get(cur)
        row = dict(trade_date=str(d), contract=cur, path=str(paths[cur]), ticks=(s or {}).get("ticks", 0),
                   start=(s or {}).get("first"), end=((s or {}).get("last") or 0) + 1, max_gap_s=round((s or {}).get("max_gap_s", 0.0), 1))
        dow = datetime.strptime(str(d), "%Y%m%d").weekday()
        if dow >= 5:
            continue                                             # sábado/domingo no son trade dates CME
        span_h = ((s["last"] - s["first"]) / 3.6e12) if s else 0.0
        if s is None or s["ticks"] < MIN_TICKS or s["max_gap_s"] > MAX_GAP_S or span_h < MIN_SPAN_H:
            bad.append(dict(row, span_h=round(span_h, 2), motivo="sin datos" if s is None else ("pocos ticks" if s["ticks"] < MIN_TICKS else
                            ("hueco > 30 min" if s["max_gap_s"] > MAX_GAP_S else "sesión corta (feriado o datos truncos)"))))
        elif len(out) >= 5 and s["ticks"] < 0.5 * float(np.median([o["ticks"] for o in out[-20:]])):
            bad.append(dict(row, span_h=round(span_h, 2), motivo="ilíquida: < 50 % de la mediana de las 20 sesiones previas (contrato migrado o día flojo)"))
        else:
            out.append(row)
    cat = dict(schema="ES_EXT_SESSIONS_V1", amendment="HOLDOUT-A1 (2026-09-26)", window_utc_ns=[START_NS, END_NS],
               criterio=dict(min_ticks=MIN_TICKS, max_gap_s=MAX_GAP_S, min_span_h=MIN_SPAN_H, liquidez="≥ 50 % de la mediana de las 20 sesiones previas incluidas", contrato="líder de la sesión anterior COMPLETA, sólo hacia adelante (auditoría 046 §5)"),
               sessions=out, excluidas=bad)
    CAT.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(completas=len(out), excluidas=[(b["trade_date"], b["contract"], b["motivo"]) for b in bad],
                          roll=[r["trade_date"] for i, r in enumerate(out) if i and r["contract"] != out[i - 1]["contract"]]), ensure_ascii=False))


if __name__ == "__main__":
    main()
