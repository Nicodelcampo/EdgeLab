#!/usr/bin/env python3
"""CAMP-001 A1 — PREFLIGHT. Resuelve la configuración EFECTIVA y la contrasta
contra lo sellado. **No calcula, carga ni muestra P&L.**

No cita el manifiesto: resuelve en código lo que el runner va a ejecutar y
verifica que coincida. Si algo no coincide ⇒ FRENA sin ejecutar.

Uso:  python tools/camp001_preflight.py [--out runs/nt8_bridge/camp001/preflight.json]
Salida: 0 = PREFLIGHT PASS (autorizado a correr) · 1 = FRENAR.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import store                      # noqa: E402
from edgelab.bridge.identity import kernel_id         # noqa: E402
from edgelab.research import camp001 as C             # noqa: E402
from edgelab.research.holdout_guard import HOLDOUT_START_ISO  # noqa: E402

STORE = os.path.join(REPO, "runs", "nt8_bridge", "campaign_store")
MANIFEST = os.path.join(REPO, "docs", "campaigns", "CAMP-001_gaps2_discovery.md")
HOLDOUT_END_ISO = "2026-12-31T23:59:59"


def _sh(*a):
    return subprocess.run(a, cwd=REPO, capture_output=True, text=True).stdout.strip()


def _manifest_body_sha():
    s = open(MANIFEST, encoding="utf-8").read()
    return hashlib.sha256(s.split("<!-- SHA256-BODY-ABOVE -->")[0]
                          .encode("utf-8")).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Preflight CAMP-001 (sin P&L)")
    ap.add_argument("--out", default=os.path.join(
        REPO, "runs", "nt8_bridge", "camp001", "preflight.json"))
    a = ap.parse_args(argv)

    checks, res = [], {}

    def ck(name, ok, got, want):
        checks.append(dict(check=name, ok=bool(ok), obtenido=got, esperado=want))
        return ok

    print("=" * 78)
    print("CAMP-001 — PREFLIGHT (A1).  Sin acceso a retornos ni P&L.")
    print("=" * 78)

    # ---- 1. manifiesto sellado -------------------------------------------- #
    body = _manifest_body_sha()
    ck("manifiesto: sha256 del cuerpo", body == C.MANIFEST_SHA256,
       body, C.MANIFEST_SHA256)
    res["manifest_sha256"] = body

    # ---- 2. grilla EFECTIVA (resuelta, no citada) -------------------------- #
    grid = C.expand_grid()
    fams = sorted({g["family"] for g in grid})
    zmin = sorted({g["zone_min_size"] for g in grid})
    pads = sorted({g["stop_pad"] for g in grid})
    tR = sorted({g["target_R"] for g in grid})
    tst = sorted({g["time_stop_bars"] for g in grid})
    ids = [g["config_id"] for g in grid]
    ck("grilla: N_eff", len(grid) == C.N_EFF, len(grid), C.N_EFF)
    ck("grilla: sin duplicados", len(set(ids)) == len(ids), len(set(ids)), len(ids))
    ck("grilla: familias", fams == ["F1", "F2", "F3", "F4"], fams, ["F1", "F2", "F3", "F4"])
    ck("grilla: zone_min_size", zmin == [2, 3, 5], zmin, [2, 3, 5])
    ck("grilla: stop_pad", pads == [2, 4], pads, [2, 4])
    ck("grilla: target_R", tR == [1, 2], tR, [1, 2])
    ck("grilla: time_stop (barras m1)", tst == [240], tst, [240])
    ck("grilla: producto cartesiano completo",
       len(grid) == len(fams) * len(zmin) * len(pads) * len(tR) * len(tst),
       len(grid), len(fams) * len(zmin) * len(pads) * len(tR) * len(tst))
    res["grid"] = grid
    print("\n[1] GRILLA EFECTIVA: %d configs = %d familias x %s zmin x %s pad x %s R x %s time_stop"
          % (len(grid), len(fams), zmin, pads, tR, tst))

    # ---- 3. folds y firewall del holdout ----------------------------------- #
    h0 = dt.datetime.fromisoformat(HOLDOUT_START_ISO)
    print("\n[2] FOLDS DE DESARROLLO (rangos UTC semiabiertos de E3)")
    folds_ok = True
    for key, contract, s, e in C.FOLDS:
        fin = dt.datetime.fromisoformat(e)
        antes = fin < h0
        folds_ok &= antes
        print("    %-10s %s -> %s   %s" % (
            contract, s, e, "OK (pre-holdout)" if antes else "TOCA EL HOLDOUT"))
    ck("folds: 4 de desarrollo", len(C.FOLDS) == 4, len(C.FOLDS), 4)
    ck("folds: todos terminan antes del holdout", folds_ok, folds_ok, True)
    ck("holdout excluido", True, "%s -> %s" % (HOLDOUT_START_ISO, HOLDOUT_END_ISO),
       "sin solape")
    res["folds"] = [dict(contract=c, start=s, end=e) for _, c, s, e in C.FOLDS]

    # ---- 4. particiones: identidad, kernel y paridad ----------------------- #
    print("\n[3] PARTICIONES (identidad unica %s)" % C.CAMPAIGN_CONFIG_ID)
    parts = {p["contract"]: p for p in store.get_partitions(
        STORE, indicator="Gaps2", config_id=C.CAMPAIGN_CONFIG_ID)}
    kid_now = kernel_id("Gaps2")
    ck("kernel_id de Gaps2 vigente", kid_now == C.GAPS2_KERNEL_ID,
       kid_now, C.GAPS2_KERNEL_ID)
    pinfo = []
    all_ok = True
    for _, contract, _, _ in C.FOLDS:
        p = parts.get(contract)
        if p is None:
            print("    %-10s FALTA" % contract)
            all_ok = False
            continue
        elig = p["parity_state"] in ("parity_covered", "parity_exact")
        kok = p["kernel_id"] == C.GAPS2_KERNEL_ID
        nz = len(store.read_zone_rows(p["dir"]))
        all_ok &= elig and kok
        cov = (json.loads(p["manifest_json"]).get("coverage") or {})
        print("    %-10s %-16s kernel_id=%s  zonas=%-7d %s" % (
            contract, p["parity_state"], p["kernel_id"], nz,
            "ELEGIBLE" if elig and kok else "NO ELEGIBLE"))
        pinfo.append(dict(contract=contract, parity_state=p["parity_state"],
                          kernel_id=p["kernel_id"], n_zones=nz,
                          integrity_state=p["integrity_state"],
                          coverage_source=cov.get("source_contract"),
                          oracle_sha256=cov.get("oracle_sha256")))
    ck("particiones: 4 elegibles con kernel_id sellado", all_ok, all_ok, True)
    res["partitions"] = pinfo

    # ---- 5. simulador y costo EXACTO --------------------------------------- #
    print("\n[4] SIMULADOR Y FRICCION")
    def _pytest(target):
        r = subprocess.run([sys.executable, "-m", "pytest", target, "-q"],
                           cwd=REPO, capture_output=True, text=True)
        tail = [l for l in r.stdout.strip().splitlines()
                if "passed" in l or "failed" in l or "error" in l]
        return r.returncode, (tail[-1] if tail else "(sin salida)")

    # Los 7 golden de `docs/execution_simulator_spec.md` §9 son CONTRATO: se
    # verifica ese número sellado, no un total de directorio (que crece al
    # agregar tests y haría el check frágil).
    g_rc, g_line = _pytest("tests/research/test_sim_golden.py")
    ck("simulador: 7 golden de la spec §9", g_rc == 0 and "7 passed" in g_line,
       g_line, "7 passed")
    r_rc, sim_line = _pytest("tests/research")
    ck("simulador: tests/research todos verdes",
       r_rc == 0 and "failed" not in sim_line and "error" not in sim_line,
       sim_line, "0 failed")
    cost = C.cost_round_turn("base")
    print("    golden spec §9: %s   ·   tests/research: %s" % (g_line, sim_line))
    print("    close_at_session_end = True (E4) · una posicion simultanea (§5)")
    print("    FRICCION round-turn escenario 'base', RESUELTA:")
    print("       slippage      = %.0f ticks (2 patas x %.0f)" % (
        cost["slippage_ticks"], cost["slippage_ticks"] / 2))
    print("       comision      = USD %.2f (2 patas x %.2f)" % (
        cost["commission_usd"], cost["commission_usd"] / 2))
    print("       tick 6E       = USD %.2f" % cost["tick_value_usd"])
    print("       TOTAL         = USD %.2f  =  %.4f ticks" % (
        cost["total_usd"], cost["total_ticks"]))
    res["cost_round_turn_base"] = cost
    res["close_at_session_end"] = True
    res["max_concurrent_positions"] = 1

    # ---- 6. estado del repo ------------------------------------------------ #
    head = _sh("git", "rev-parse", "HEAD")
    dirty = _sh("git", "status", "--porcelain")
    ck("working tree limpio", dirty == "", dirty[:120] or "(limpio)", "(limpio)")
    res["git_head"] = head
    res["git_clean"] = dirty == ""
    print("\n[5] REPO   HEAD=%s   working tree=%s" % (
        head[:12], "limpio" if not dirty else "SUCIO"))

    # ---- veredicto --------------------------------------------------------- #
    res["checks"] = checks
    res["verdict"] = "PASS" if all(c["ok"] for c in checks) else "FRENAR"
    res["generated_utc"] = dt.datetime.now(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    payload = json.dumps({k: v for k, v in res.items() if k != "_sha"},
                         indent=2, sort_keys=True, ensure_ascii=False)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    open(a.out, "w", encoding="utf-8").write(payload)

    print("\n[6] VERIFICACIONES")
    for c in checks:
        print("    [%s] %-42s %s" % ("x" if c["ok"] else " ", c["check"],
                                     "" if c["ok"] else "obtenido=%r esperado=%r"
                                     % (c["obtenido"], c["esperado"])))
    bad = [c for c in checks if not c["ok"]]
    print("\n%s  (%d/%d checks)" % (
        "PREFLIGHT PASS — autorizado a correr" if not bad else "FRENAR — no ejecutar",
        len(checks) - len(bad), len(checks)))
    print("preflight: %s\nsha256:    %s" % (a.out, sha))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
