#!/usr/bin/env python3
r"""Catálogo canónico de sesiones L2 (E:\l2_parquet): contrato líder por sesión CME y exclusión de sesiones ilíquidas.

Pedido de Nico (27/09): usar los días de mayor liquidez y dejar fuera los contratos con liquidez baja o ya migrada
al siguiente. Target-free: sólo volumen negociado, continuidad y horario; no mira retornos.

- `ts_us` es hora de pared ART (UTC-3): se suman 3 h antes de todo. Los archivos del Market Replay no están alineados a
  la sesión CME, así que se
  re-cortan por trade date CME (17:00 CT → 16:00 CT) con `edgelab.kaggle.sessions_cme.trade_date_ymd`.
- Liquidez de una sesión = volumen negociado (L1, side == 2 = LAST) del contrato en esa sesión.
- Contrato por sesión: regla canónica de los ticks (líder por volumen de la sesión COMPLETA anterior, sólo hacia
  adelante; el vencimiento más lejano reemplaza al vigente sólo si lo supera y su sesión anterior fue completa).
- Sesión incluida si: contrato elegido con span ≥ 22,5 h, sin huecos > 30 min fuera de la pausa 16-17 CT, y volumen
  ≥ 50 % de la mediana de sesiones del instrumento. Si no, queda en `excluidas` con el motivo.
- Para ES y NQ se compara la elección con el catálogo de ticks (research-v2 + extensión jul–sep).

    .venv\Scripts\python tools\build_l2_catalog.py            # escanea (lento, por bloques) y escribe el catálogo
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd  # noqa: E402

BASE = Path(r"E:\l2_parquet")
# TAG por variable de entorno: el catálogo 20260927 está congelado en el protocolo NQ (su sha entra al preflight);
# los reescaneos con datos nuevos se escriben en un archivo con otra fecha, nunca encima.
TAG = os.environ.get("L2_CATALOG_TAG", "20260927")
OUT = REPO / "docs" / "research" / "contract_regimes" / f"L2_sessions_catalog_{TAG}.json"
CACHE = BASE / f"_catalog_scan_{TAG}_utc.json"
MIN_SPAN_H, MAX_GAP_S, MIN_VOL_FRAC = 22.5, 1800, 0.5
LAST = 2
ART_TO_UTC_NS = 3 * 3600 * 1_000_000_000   # docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md: ts_us = hora de pared ART (UTC-3)


def expiry_key(contract_dir):
    mm, yy = contract_dir.split("_")[1].split("-")
    return int(yy) * 100 + int(mm)


def scan():
    """Por archivo diario de L1: volumen, trades, primer/último ts y hueco máximo, por trade date CME."""
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    res = {}
    for cdir in sorted(p for p in BASE.iterdir() if p.is_dir() and (p / "l1_quotes").exists()):
        per = defaultdict(lambda: dict(vol=0, trades=0, first=None, last=None, max_gap_s=0.0, files=[]))
        for f in sorted((cdir / "l1_quotes").glob("*.parquet")):
            pf = pq.ParquetFile(f); prev = None
            for rg in range(pf.metadata.num_row_groups):
                t = pf.read_row_group(rg, columns=["ts_us", "side", "size"])
                ts = t.column("ts_us").to_numpy().astype(np.int64) * 1000 + ART_TO_UTC_NS   # ts_us es hora de pared ART, no UTC
                if not len(ts):
                    continue                                    # archivo/row group vacío (28/09: rompía el reescaneo)
                side = t.column("side").to_numpy(); size = t.column("size").to_numpy()
                td = trade_date_ymd(ts); mb = is_maintenance_break(ts)
                gaps = np.diff(np.r_[prev if prev is not None else ts[0], ts]) / 1e9
                for d in np.unique(td):
                    m = td == d; s = per[str(int(d))]
                    tr = m & (side == LAST)
                    s["vol"] += int(size[tr].sum()); s["trades"] += int(tr.sum())
                    s["first"] = int(ts[m][0]) if s["first"] is None else min(s["first"], int(ts[m][0]))
                    s["last"] = int(ts[m][-1]) if s["last"] is None else max(s["last"], int(ts[m][-1]))
                    g = gaps[m & ~mb]
                    if len(g):
                        s["max_gap_s"] = max(s["max_gap_s"], float(g.max()))
                    if f.stem not in s["files"]:
                        s["files"].append(f.stem)
                prev = int(ts[-1])
        res[cdir.name] = dict(per)
        print(cdir.name, "sesiones", len(per), flush=True)
    CACHE.write_text(json.dumps(res), encoding="utf-8")
    return res


def main():
    raw = scan()
    by_inst = defaultdict(dict)
    for cdir, per in raw.items():
        by_inst[cdir.split("_")[0]][cdir] = per
    cat = dict(schema="EDGELAB_L2_SESSIONS_V1", fuente=str(BASE), criterio=dict(min_span_h=MIN_SPAN_H, max_gap_s=MAX_GAP_S,
               min_vol_frac_mediana_previa_20=MIN_VOL_FRAC, calidad="control de fin de día, no elegibilidad al abrir (048)", contrato="líder por volumen de la sesión completa anterior, sólo hacia adelante",
               liquidez="volumen negociado L1 (LAST)"), instrumentos={})
    for inst, cs in sorted(by_inst.items()):
        days = sorted({d for per in cs.values() for d in per if datetime.strptime(d, "%Y%m%d").weekday() < 5})
        # auditoría 046 §6: la mediana de liquidez usa SÓLO el pasado (las 20 sesiones incluidas anteriores; con < 5, sin
        # criterio de volumen). Es un control de calidad de fin de día (048), no una condición conocida al abrir.
        def med_prev(ses):
            v = [x["vol"] for x in ses[-20:]]
            return float(np.median(v)) if len(v) >= 5 else 0.0

        def complete(c, d, med):
            s = cs[c].get(d)
            return bool(s and (s["last"] - s["first"]) / 3.6e12 >= MIN_SPAN_H and s["max_gap_s"] <= MAX_GAP_S and s["vol"] >= MIN_VOL_FRAC * med)
        cur, ses, exc = None, [], []
        for i, d in enumerate(days):
            if cur is None:
                cur = max(cs, key=lambda c: cs[c].get(d, {}).get("vol", 0))
            elif i > 0:
                p = days[i - 1]
                lead = max(cs, key=lambda c: cs[c].get(p, {}).get("vol", 0))
                if expiry_key(lead) > expiry_key(cur) and cs[lead].get(p, {}).get("vol", 0) > cs[cur].get(p, {}).get("vol", 0) and complete(lead, p, med_prev(ses)):
                    cur = lead
            s = cs[cur].get(d)
            row = dict(trade_date=d, contract=cur, vol=(s or {}).get("vol", 0), files=(s or {}).get("files", []),
                       start_ns=(s or {}).get("first"), end_ns=((s or {}).get("last") or 0) + 1,
                       span_h=round(((s["last"] - s["first"]) / 3.6e12) if s else 0.0, 2), max_gap_s=round((s or {}).get("max_gap_s", 0.0), 1))
            med = med_prev(ses)
            if complete(cur, d, med):
                ses.append(row)
            else:
                motivo = ("sin datos del contrato vigente" if s is None else "volumen < 50 % de la mediana" if s["vol"] < MIN_VOL_FRAC * med
                          else "hueco > 30 min" if s["max_gap_s"] > MAX_GAP_S else "sesión corta (feriado o datos truncos)")
                exc.append(dict(row, motivo=motivo))
        rolls = [s["trade_date"] for i, s in enumerate(ses) if i and s["contract"] != ses[i - 1]["contract"]]
        cat["instrumentos"][inst] = dict(mediana_vol_final=med_prev(ses), sesiones=ses, excluidas=exc, rolls=rolls)
        print(f"{inst:4s} incluidas {len(ses):3d}  excluidas {len(exc):3d}  rolls {rolls}  rango {ses[0]['trade_date'] if ses else '-'}..{ses[-1]['trade_date'] if ses else '-'}")
    for inst in ("ES", "NQ"):                          # cruce con el catálogo de ticks
        f = REPO / "docs" / "research" / "contract_regimes" / f"{inst}_ext_2026q3_sessions_catalog.json"
        if f.exists() and inst in cat["instrumentos"]:
            tk = {s["trade_date"]: s["contract"].replace(" ", "_") for s in json.loads(f.read_text(encoding="utf-8"))["sessions"]}
            l2 = {s["trade_date"]: s["contract"] for s in cat["instrumentos"][inst]["sesiones"]}
            comun = sorted(set(tk) & set(l2)); dif = [d for d in comun if tk[d] != l2[d]]
            cat["instrumentos"][inst]["cruce_ticks"] = dict(sesiones_comunes=len(comun), contrato_distinto=dif)
            print(inst, "cruce con ticks:", len(comun), "comunes,", len(dif), "con contrato distinto", dif)
    OUT.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
