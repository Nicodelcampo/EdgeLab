#!/usr/bin/env python3
"""CAMP-001 A3 — INTEGRIDAD ANTES DE ABRIR.

Verifica los artefactos crudos **sin interpretarlos**: no imprime P&L, no
rankea, no ordena por resultado. Sólo responde: ¿este intento es técnicamente
válido? Si algo falla ⇒ `INVALID_TECHNICAL`, se conserva todo, no se interpreta
nada y se frena.

Sólo con `INTEGRITY_PASS` se autoriza abrir el reporte (A4).

Uso:  python tools/camp001_integrity.py --attempt 1
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.research import camp001 as C                      # noqa: E402
from edgelab.research.holdout_guard import HOLDOUT_START_ISO   # noqa: E402

OUTDIR = os.path.join(REPO, "runs", "nt8_bridge", "camp001")

# Archivos que DETERMINAN el resultado. Ninguno puede haber cambiado entre el
# preflight y la corrida. (Los artefactos de otras tareas del turno pueden
# existir en el árbol, pero si tocan estos paths el intento es inválido.)
RUN_PATHS = (
    "edgelab/research/camp001.py",
    "edgelab/research/sim.py",
    "edgelab/research/costs.py",
    "edgelab/research/holdout_guard.py",
    "edgelab/bridge/bars.py",
    "edgelab/bridge/ticks.py",
    "edgelab/bridge/store.py",
    "edgelab/bridge/sessions.py",
    "tools/camp001_run.py",
)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Integridad de la corrida CAMP-001")
    ap.add_argument("--attempt", type=int, required=True)
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args(argv)

    d = os.path.join(a.outdir, "attempt_%02d" % a.attempt)
    raw_p = os.path.join(d, "raw_results.jsonl")
    meta_p = os.path.join(d, "run_meta.json")
    if not (os.path.exists(raw_p) and os.path.exists(meta_p)):
        print("INVALID_TECHNICAL: faltan artefactos del intento %d" % a.attempt)
        return 1
    meta = json.load(open(meta_p, encoding="utf-8"))
    rows = [json.loads(l) for l in open(raw_p, encoding="utf-8")]
    pre = json.load(open(os.path.join(a.outdir, "preflight.json"), encoding="utf-8"))

    checks = []

    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    print("=" * 78)
    print("CAMP-001 — A3 INTEGRIDAD (intento %d).  No se interpreta ningun resultado."
          % a.attempt)
    print("=" * 78)

    # 1. cobertura completa de la grilla
    grid = {g["config_id"] for g in C.expand_grid()}
    folds = {f[0] for f in C.FOLDS}
    seen = {(r["config_id"], r["fold"]) for r in rows}
    faltan = {(c, f) for c in grid for f in folds} - seen
    sobran = seen - {(c, f) for c in grid for f in folds}
    ck("48 configs x 4 folds presentes (%d filas)" % len(rows),
       len(rows) == 192 and not faltan and not sobran,
       "faltan=%d sobran=%d" % (len(faltan), len(sobran)))
    ck("sin filas duplicadas", len(seen) == len(rows),
       "%d unicas de %d" % (len(seen), len(rows)))

    # 2. ninguna fecha del holdout
    h0 = dt.datetime.fromisoformat(HOLDOUT_START_ISO)
    fin_max = max(dt.datetime.fromisoformat(f["end_utc"]) for f in meta["folds"])
    ck("ninguna fecha del holdout", fin_max < h0,
       "fin maximo de fold = %s < %s" % (fin_max, h0))

    # 3. costos idénticos al preflight
    ck("costos identicos al preflight",
       meta["cost_round_turn"] == pre["cost_round_turn_base"],
       "USD %.2f = %.4f ticks" % (meta["cost_round_turn"]["total_usd"],
                                  meta["cost_round_turn"]["total_ticks"]))
    ck("close_at_session_end y 1 posicion simultanea",
       meta["close_at_session_end"] is True and meta["max_concurrent_positions"] == 1)

    # 4. conteos = trades EJECUTADOS, no triggers
    mal = [r for r in rows if r["n_trades"] > r["n_signals"]]
    ck("n_trades <= n_signales en todas las filas", not mal,
       "%d filas violan la cota" % len(mal))
    inc = [r for r in rows
           if r["n_trades"] + r["n_rejected"] != r["n_signals"]]
    ck("n_trades + n_rechazadas == n_senales", not inc,
       "%d filas descuadran" % len(inc))

    # 5. sin NaN / nulos inexplicados
    def bad(v):
        return v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))
    nan_rows = [r for r in rows
                for k in ("gross_ticks", "net_ticks", "net_usd", "spread_ticks",
                          "slippage_ticks", "commission_usd")
                if bad(r[k])]
    ck("sin NaN/inf en las magnitudes economicas", not nan_rows,
       "%d violaciones" % len(nan_rows))
    # expectancy None es legítimo SOLO si n_trades == 0
    exp_bad = [r for r in rows
               if (r["expectancy_net_usd"] is None) != (r["n_trades"] == 0)]
    ck("expectancy nula solo cuando n_trades==0", not exp_bad,
       "%d filas inconsistentes" % len(exp_bad))

    # 6. folds vacíos sin explicar
    vacios = [(r["config_id"], r["fold"]) for r in rows if r["n_trades"] == 0]
    sin_expl = [x for x in vacios
                if not any(r["n_signals"] == 0 or r["n_rejected"] > 0
                           for r in rows
                           if (r["config_id"], r["fold"]) == x)]
    ck("folds sin trades, todos explicados", not sin_expl,
       "%d celdas con 0 trades (%d sin explicacion)" % (len(vacios), len(sin_expl)))

    # 7. identidad aditiva de costos, fila a fila
    tv = meta["tick_value_usd"]
    ident = [r for r in rows
             if abs(r["net_ticks"] - (r["gross_ticks"] - r["spread_ticks"]
                                      - r["slippage_ticks"])) > 1e-6
             or abs(r["net_usd"] - (r["net_ticks"] * tv - r["commission_usd"])) > 1e-6]
    ck("identidad aditiva neto = bruto - spread - slippage", not ident,
       "%d filas rotas" % len(ident))

    # 8. digest reproducible
    dg = hashlib.sha256("".join(r["digest"] for r in sorted(
        rows, key=lambda r: (r["config_id"], r["fold"]))).encode("utf-8")).hexdigest()[:16]
    ck("digest reproducible desde los crudos", dg == meta["run_digest"],
       "%s vs %s" % (dg, meta["run_digest"]))
    sha = hashlib.sha256(open(raw_p, "rb").read()).hexdigest()
    ck("sha256 de los crudos coincide con el meta", sha == meta["raw_results_sha256"],
       sha[:16])

    # 9. cero cambios de código en el camino de la corrida
    diff = subprocess.run(["git", "diff", "--name-only", meta["git_head"], "--"]
                          + list(RUN_PATHS), cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    ck("cero cambios en el codigo que determina el resultado", diff == "",
       diff.replace("\n", ", ") or "(sin cambios en %d paths)" % len(RUN_PATHS))
    ck("preflight PASS y HEAD coincidente",
       pre["verdict"] == "PASS" and pre["git_head"] == meta["git_head"],
       meta["git_head"][:12])
    ck("intento marcado COMPLETE", meta.get("status") == "COMPLETE",
       str(meta.get("status")))

    for name, ok, detail in checks:
        print("    [%s] %-52s %s" % ("x" if ok else " ", name, detail))
    bad_n = sum(1 for _, ok, _ in checks if not ok)
    verdict = "INTEGRITY_PASS" if not bad_n else "INVALID_TECHNICAL"
    print("\n%s  (%d/%d)" % (verdict, len(checks) - bad_n, len(checks)))
    if bad_n:
        print("Se conserva todo. NO se interpreta ningun resultado. Frenar.")
    else:
        print("Autorizado a abrir el reporte A4.")
    with open(os.path.join(d, "integrity.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(attempt=a.attempt, verdict=verdict,
                       checks=[dict(check=n, ok=o, detail=dd) for n, o, dd in checks],
                       raw_results_sha256=sha, run_digest=dg),
                  fh, indent=2, ensure_ascii=False)
    return 0 if not bad_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
