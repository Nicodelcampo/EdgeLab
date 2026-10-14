#!/usr/bin/env python3
"""Chequeo diario de datos (R0: captura continua). Detecta que la captura se haya cortado y que el respaldo de L2 este al dia.

Que mira:
  1. L2: por contrato en <l2_root>/<CONTRATO>/l2_depth/YYYYMMDD.parquet -> ultima fecha, dias habiles sin dato y huecos dentro del rango.
  2. Respaldo: archivos de <l2_root> que faltan o difieren de tamano en <backup_root>; con --backup copia (robocopy) lo nuevo.
  3. Ticks: export de NT8 mas reciente en <ticks_root> (mtime) y su antiguedad.
Escribe un JSON (--out) y sale 1 si algo requiere atencion (captura cortada > --max-stale dias habiles, o respaldo atrasado).
NT8 debe seguir exportando: este script NO exporta nada, avisa cuando deja de llegar. Ver docs/infra/CAPTURA_CONTINUA_RUNBOOK.md.
Uso: python tools/daily_data_health.py --l2-root E:/l2_parquet --backup-root D:/_BACKUP_L2_20261014/l2_parquet --ticks-root E:/EdgeLab/data/nt8 --out runs/daily_data_health.json [--backup]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RE_DATE = re.compile(r"^(\d{8})\.parquet$")


def weekdays_between(a: dt.date, b: dt.date):
    d = a + dt.timedelta(days=1)
    while d < b:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


def business_days_since(last: dt.date, today: dt.date) -> int:
    n, d = 0, last
    while d < today:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def l2_status(l2_root: Path, today: dt.date) -> dict:
    out = {}
    if not l2_root.is_dir():
        return out
    for c in sorted(p for p in l2_root.iterdir() if p.is_dir() and (p / "l2_depth").is_dir()):
        dates = []
        for f in (c / "l2_depth").iterdir():
            m = RE_DATE.match(f.name)
            if m:
                dates.append(dt.datetime.strptime(m.group(1), "%Y%m%d").date())
        dates.sort()
        if not dates:
            continue
        gaps = [d.isoformat() for a, b in zip(dates, dates[1:]) for d in weekdays_between(a, b)]
        out[c.name] = {"sessions": len(dates), "first": dates[0].isoformat(), "last": dates[-1].isoformat(),
                       "business_days_since_last": business_days_since(dates[-1], today), "missing_weekdays_in_range": gaps}
    return out


def stale_alerts(l2: dict, max_stale: int) -> list:
    """Alerta sólo sobre el contrato más reciente de cada producto: un contrato vencido deja de recibir datos y no es una falla."""
    best = {}
    for c, s in l2.items():
        prod = c.split("_")[0]
        if prod not in best or s["last"] > l2[best[prod]]["last"]:
            best[prod] = c
    return [f"L2 {c}: {l2[c]['business_days_since_last']} dias habiles sin dato nuevo (ultimo {l2[c]['last']})"
            for c in sorted(best.values()) if l2[c]["business_days_since_last"] > max_stale]


def backup_status(src: Path, dst: Path) -> dict:
    missing, differ, n = [], [], 0
    if not src.is_dir():
        return {"checked": 0}
    for dp, _, fns in os.walk(src):
        for f in fns:
            n += 1
            s = Path(dp) / f
            t = dst / s.relative_to(src)
            if not t.is_file():
                missing.append(str(s.relative_to(src)))
            elif t.stat().st_size != s.stat().st_size:
                differ.append(str(s.relative_to(src)))
    return {"checked": n, "missing_in_backup": len(missing), "size_differs": len(differ), "examples_missing": missing[:10]}


def ticks_status(root: Path, today: dt.date) -> dict:
    if not root.is_dir():
        return {}
    newest = None
    for dp, _, fns in os.walk(root):
        for f in fns:
            m = os.path.getmtime(os.path.join(dp, f))
            if newest is None or m > newest[0]:
                newest = (m, os.path.join(dp, f))
    if not newest:
        return {}
    d = dt.datetime.fromtimestamp(newest[0]).date()
    return {"newest_file": newest[1], "newest_date": d.isoformat(), "days_old": (today - d).days}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--l2-root", required=True)
    ap.add_argument("--backup-root")
    ap.add_argument("--ticks-root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-stale", type=int, default=3, help="dias habiles sin dato nuevo antes de alertar")
    ap.add_argument("--backup", action="store_true", help="copia con robocopy lo que falte en el respaldo")
    ap.add_argument("--today", default=None)
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    res = {"today": today.isoformat(), "l2": l2_status(Path(a.l2_root), today)}
    alerts = []
    alerts = stale_alerts(res["l2"], a.max_stale)
    if a.backup_root:
        if a.backup:
            subprocess.run(["robocopy", a.l2_root, a.backup_root, "/E", "/R:1", "/W:1", "/NFL", "/NDL", "/NP", "/MT:4"], check=False)
        res["backup"] = backup_status(Path(a.l2_root), Path(a.backup_root))
        if res["backup"].get("missing_in_backup") or res["backup"].get("size_differs"):
            alerts.append(f"respaldo atrasado: {res['backup'].get('missing_in_backup')} faltan, {res['backup'].get('size_differs')} difieren")
    if a.ticks_root:
        res["ticks"] = ticks_status(Path(a.ticks_root), today)
        if res["ticks"].get("days_old", 0) > a.max_stale + 2:
            alerts.append(f"ticks: ultimo export hace {res['ticks']['days_old']} dias")
    res["alerts"] = alerts
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    for x in alerts:
        print("ALERTA:", x)
    print(f"{len(res['l2'])} contratos L2, {len(alerts)} alertas")
    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
