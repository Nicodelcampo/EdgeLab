#!/usr/bin/env python3
"""store_audit.py — gate P3 sobre el store del bridge (F6.3).

EL gate previo a toda campaña de fuerza bruta: recorre el store completo,
corre P3.2 (round-trip) + P3.4 (API) + identidad al 100%, P3.3 (recomputación)
por muestreo, P3.5 (integridad entre configs) y, si se da, P3.0 (completitud de
campaña). Sale con código != 0 ante CUALQUIER falla.

Uso:
  python tools/store_audit.py --store runs/nt8_bridge/store --all
  python tools/store_audit.py --store <root> --all --recompute-sample 1.0
  python tools/store_audit.py --store <root> --campaign campaign_manifest.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import audit  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gate P3 del store del bridge")
    ap.add_argument("--store", required=True, help="raíz del store")
    ap.add_argument("--all", action="store_true", help="auditar todas las particiones")
    ap.add_argument("--run-id", default=None, help="auditar una sola partición")
    ap.add_argument("--recompute-sample", type=float, default=0.0,
                    help="fracción de particiones a recomputar (P3.3); 1.0 = 100%%")
    ap.add_argument("--campaign", default=None, help="campaign_manifest.json (P3.0)")
    ap.add_argument("--promote", action="store_true",
                    help="elevar integrity_state a api_verified en las particiones que pasan todo")
    args = ap.parse_args(argv)

    from edgelab.bridge import store
    campaign = None
    if args.campaign:
        with open(args.campaign, encoding="utf-8") as fh:
            campaign = json.load(fh)

    if args.run_id:
        parts = [p for p in store.get_partitions(args.store, run_id=args.run_id)]
        if not parts:
            print("run_id no está en el catálogo:", args.run_id)
            return 2
        rep = audit.audit_partition(args.store, parts[0],
                                    recompute=args.recompute_sample > 0)
        _print_partition(rep)
        return 0 if rep["ok"] else 1

    rep = audit.audit_all(args.store, recompute_sample=args.recompute_sample,
                          campaign=campaign)
    print("== store_audit P3 == particiones=%d" % rep["n_partitions"])
    n_fail = 0
    for r in rep["partitions"]:
        if not r["ok"]:
            n_fail += 1
        elif args.promote:
            store.set_state(args.store, r["run_id"], integrity_state="api_verified")
        _print_partition(r)
    cc = rep["cross_config"]
    print("P3.5 integridad-entre-configs:", "OK" if cc["ok"] else "FALLA")
    for d in cc["diagnostics"]:
        print("   ", d["code"], d.get("detail", ""))
    if rep["campaign"] is not None:
        c = rep["campaign"]
        print("P3.0 campaña: expected=%d present=%d failed=%d missing=%d dup=%d %s"
              % (c["expected"], c["present"], c["failed"], len(c["missing"]),
                 len(c["duplicated"]), "OK" if c["ok"] else "FALLA"))
        if c["missing"]:
            print("    faltan:", c["missing"])
    print("RESULTADO:", "VERDE" if rep["ok"] else "ROJO (%d particiones con falla)" % n_fail)
    return 0 if rep["ok"] else 1


def _print_partition(r):
    flag = "OK " if r["ok"] else "FAIL"
    print("[%s] %s %s cfg=%s" % (flag, r["indicator"], r["run_id"], r["config_id"]))
    for name, c in r["checks"].items():
        if c.get("ok") is False:
            print("      %-10s %s %s" % (name, c["code"], c.get("detail", "")))


if __name__ == "__main__":
    raise SystemExit(main())
