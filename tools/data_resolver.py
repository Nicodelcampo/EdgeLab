#!/usr/bin/env python3
"""Genera docs/data_catalog/RESOLVER.json: UNA respuesta por (instrumento, sesión) — qué dataset/archivo/contrato leer y
si la sesión está aprobada para análisis (con el motivo si no). Sale de sessions.json + las mismas reglas de
tools/data_curate.py (no inventa reglas nuevas). Lo consume edgelab_data.py, que es lo único que un agente debe usar.
  python tools/data_resolver.py"""
import json
from datetime import datetime, timezone
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "docs/data_catalog"
HOLDOUT_FIRST = "2026-10-01"
SPOT_NOTE = ("Spot/CFD Dukascopy (dataset edgelab-dukascopy-*): complemento de POTENCIA para pruebas de información "
             "(dirección, forma) cuando los futuros no alcanzan. Limitaciones: bid/ask de spot/CFD, no libro CME; "
             "volumen = liquidez cotizada, no trades; spread y costos distintos (oro: ~5,8 ticks GC vs 3 en COMEX); "
             "horario distinto. NO sirve para costos ni ejecución del futuro: el neto se confirma siempre en futuros.")


def main():
    sess = json.loads((D / "sessions.json").read_text(encoding="utf-8"))
    cur = json.loads((D / "curated.json").read_text(encoding="utf-8"))
    out = {"schema": "EDGELAB_RESOLVER_V1", "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "holdout_first_trade_date": HOLDOUT_FIRST, "rules": cur.get("rules"),
           "how_to_use": "import edgelab_data as ed; ed.load_ticks('MNQ','2026-01-01','2026-09-30')  # sólo sesiones aprobadas",
           "spot_complement": SPOT_NOTE, "instruments": {}}
    for sym, rows in sess.items():
        conflict = set(cur["instruments"][sym]["caveat_sessions_source_conflict"]["contracts"])
        lst = []
        for r in rows:
            if r["post_holdout"] or r["date"] >= HOLDOUT_FIRST:
                continue                                   # el holdout ni siquiera se lista
            why = ("liquidez_baja" if r["below_25pct_instrument_median"] else
                   "sesion_truncada" if r["thin_minutes"] else None)
            lst.append({"date": r["date"], "contract": r["contract"], "dataset": r["dataset"], "file": r["file"],
                        "approved": why is None, "reason": why, "caveat": "fuente_en_conflicto" if r["contract"] in conflict else None,
                        "trades": r["trades"], "volume": r["volume"], "minutes": r["minutes"]})
        v = cur["instruments"][sym]
        out["instruments"][sym] = {"verdict": v["verdict"], "tick_size": v["tick_size"], "tick_value_usd": v["tick_value_usd"],
                                   "approved_sessions": sum(x["approved"] for x in lst), "sessions": lst}
    (D / "RESOLVER.json").write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf-8")
    print({k: (v["approved_sessions"], len(v["sessions"])) for k, v in out["instruments"].items()})


if __name__ == "__main__":
    main()
