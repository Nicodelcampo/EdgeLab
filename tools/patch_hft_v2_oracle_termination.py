#!/usr/bin/env python3
"""Agrega y puebla la columna termination_reason en hft_zones_v2 de forma causal y determinista."""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators import hftzones_nq as hz


def patch_db(db_path: Path, instrument: str = "NQ JUN26") -> None:
    print(f"Opening {db_path}...")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Verificar si ya existe termination_reason
    cols = [r[1] for r in cur.execute("PRAGMA table_info(hft_zones_v2)").fetchall()]
    if "termination_reason" not in cols:
        print("Adding column termination_reason to hft_zones_v2...")
        cur.execute("ALTER TABLE hft_zones_v2 ADD COLUMN termination_reason TEXT")
        con.commit()

    # Cargar ticks y reconstruir razones causales
    print("Loading ticks...")
    ticks = cur.execute(
        "SELECT session_id, tick_seq, timestamp_ns, price_ticks, volume FROM hft_ticks_v2 WHERE instrument=? ORDER BY session_id, tick_seq",
        (instrument,)
    ).fetchall()

    from collections import defaultdict
    by_sess = defaultdict(list)
    for t in ticks:
        by_sess[t[0]].append(t)

    updates = []
    prev_close = None
    for sess, t_list in sorted(by_sess.items()):
        ts_ns = [t[2] for t in t_list]
        px_tk = [t[3] for t in t_list]
        vol = [float(t[4]) for t in t_list]
        cands = hz.detect_candidates(ts_ns, px_tk, vol, prev_session_close_ticks=prev_close)
        acc, _ = hz.accept_all(cands, dict(hz.ACCEPT_DEFAULTS), tick_size=0.25)
        prev_close = px_tk[-1]
        for z_idx, z in enumerate(acc, 1):
            updates.append((z["termination_reason"], instrument, sess, z_idx))

    print(f"Updating {len(updates)} zones...")
    cur.executemany(
        "UPDATE hft_zones_v2 SET termination_reason = ? WHERE instrument = ? AND session_id = ? AND zone_seq = ?",
        updates
    )
    con.commit()

    # Verificar
    reasons = cur.execute(
        "SELECT termination_reason, COUNT(*) FROM hft_zones_v2 WHERE instrument=? GROUP BY termination_reason",
        (instrument,)
    ).fetchall()
    print("Updated termination reasons in DB:", reasons)
    con.close()


if __name__ == "__main__":
    db = Path("data/nt8_oracles/hft_zones_nq_v2.sqlite")
    patch_db(db)
