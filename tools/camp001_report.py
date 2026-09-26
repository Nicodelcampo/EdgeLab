#!/usr/bin/env python3
"""CAMP-001 A4 — REPORTE EN UNIDADES DE EDGE.

La pregunta no es "¿qué config rankea mejor?" sino **"¿existe efecto bruto que
supere la fricción, con muestra suficiente para afirmarlo?"**.

Exige `INTEGRITY_PASS` de A3. Aplica los veredictos mecánicos de E6.6 sin
excepción y separa: hechos observados / veredictos / limitaciones / anomalías.
**No recomienda promociones, no abre el holdout, no cambia reglas post-resultado.**

Uso:  python tools/camp001_report.py --attempt 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.research import camp001 as C      # noqa: E402

OUTDIR = os.path.join(REPO, "runs", "nt8_bridge", "camp001")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reporte CAMP-001 en unidades de edge")
    ap.add_argument("--attempt", type=int, required=True)
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args(argv)

    d = os.path.join(a.outdir, "attempt_%02d" % a.attempt)
    integ_p = os.path.join(d, "integrity.json")
    if not os.path.exists(integ_p):
        print("FRENAR: no hay A3. Correr tools/camp001_integrity.py primero.")
        return 1
    integ = json.load(open(integ_p, encoding="utf-8"))
    if integ["verdict"] != "INTEGRITY_PASS":
        print("FRENAR: A3 dio %s. No se interpreta ningun resultado." % integ["verdict"])
        return 1

    meta = json.load(open(os.path.join(d, "run_meta.json"), encoding="utf-8"))
    rows = [json.loads(l) for l in open(os.path.join(d, "raw_results.jsonl"),
                                        encoding="utf-8")]
    cost = meta["cost_round_turn"]
    tv = meta["tick_value_usd"]
    folds = [f[0] for f in C.FOLDS]

    # agregación por config (los folds son disjuntos por E3)
    by = {}
    for r in rows:
        c = by.setdefault(r["config_id"], dict(
            config_id=r["config_id"], family=r["family"],
            zone_min_size=r["zone_min_size"], stop_pad=r["stop_pad"],
            target_R=r["target_R"], n_trades=0, per_fold={},
            gross_ticks=0.0, net_ticks=0.0, net_usd=0.0,
            spread_ticks=0.0, slippage_ticks=0.0, commission_usd=0.0,
            exit_reasons={}, n_signals=0))
        c["n_trades"] += r["n_trades"]
        c["n_signals"] += r["n_signals"]
        c["per_fold"][r["fold"]] = r["n_trades"]
        for k in ("gross_ticks", "net_ticks", "net_usd", "spread_ticks",
                  "slippage_ticks", "commission_usd"):
            c[k] += r[k]
        for k, v in (r["exit_reasons"] or {}).items():
            c["exit_reasons"][k] = c["exit_reasons"].get(k, 0) + v

    for c in by.values():
        n = c["n_trades"]
        c["exp_gross_ticks"] = (c["gross_ticks"] / n) if n else None
        c["exp_net_ticks"] = (c["net_ticks"] / n) if n else None
        c["exp_net_usd"] = (c["net_usd"] / n) if n else None
        # fricción por trade EFECTIVA (spread + slippage + comisión)
        c["friccion_ticks"] = ((c["spread_ticks"] + c["slippage_ticks"]
                                + c["commission_usd"] / tv) / n) if n else None
        # E6.6, literal
        if n < C.MIN_TRADES_WINNER:
            c["veredicto"] = "no_elegible (<%d trades)" % C.MIN_TRADES_WINNER
        elif n < C.MIN_TRADES_G1:
            c["veredicto"] = "ganador_exploratorio (50-99, NO pasa G1, NO es evidencia)"
        else:
            c["veredicto"] = "elegible_para_G1"

    cfgs = [by[g["config_id"]] for g in C.expand_grid()]   # orden de la grilla

    L = []
    P = L.append
    P("=" * 100)
    P("CAMP-001 — REPORTE A4 (intento %d).  Escenario '%s'." % (a.attempt, meta["scenario"]))
    P("=" * 100)
    P("manifiesto SEALED v1.1 sha256 %s" % meta["manifest_sha256"])
    P("commit %s · digest %s · crudos sha256 %s"
      % (meta["git_head"][:12], meta["run_digest"], meta["raw_results_sha256"][:16]))
    P("")
    P("PREGUNTA: existe efecto BRUTO que supere la friccion, con muestra suficiente")
    P("para afirmarlo? La friccion round-turn es %.4f ticks (USD %.2f): esa es la vara."
      % (cost["total_ticks"], cost["total_usd"]))
    P("")

    # -------------------- 1. HECHOS OBSERVADOS --------------------------------
    P("-" * 100)
    P("1. HECHOS OBSERVADOS — las 48 hipotesis, en orden de la grilla sellada")
    P("-" * 100)
    P("%-18s %-4s %4s %4s %3s %7s  %-22s %9s %9s %10s %11s"
      % ("config", "fam", "zmin", "pad", "R", "trades", "por fold (9-25/12-25/3-26/6-26)",
         "E[bruto]t", "friccion", "E[neto]t", "E[neto]USD"))
    for c in cfgs:
        pf = "/".join(str(c["per_fold"].get(f, 0)) for f in folds)
        fmt = lambda v, d=4: ("%*.*f" % (9, d, v)) if v is not None else "%9s" % "-"
        P("%-18s %-4s %4d %4d %3d %7d  %-22s %s %s %s %s"
          % (c["config_id"], c["family"], c["zone_min_size"], c["stop_pad"],
             c["target_R"], c["n_trades"], pf,
             fmt(c["exp_gross_ticks"]), fmt(c["friccion_ticks"]),
             fmt(c["exp_net_ticks"]),
             ("%11.2f" % c["exp_net_usd"]) if c["exp_net_usd"] is not None else "%11s" % "-"))

    # -------------------- 2. VEREDICTOS MECANICOS -----------------------------
    P("")
    P("-" * 100)
    P("2. VEREDICTOS MECANICOS (E6.6, aplicados sin excepcion)")
    P("-" * 100)
    for fam in C.FAMILIES:
        fc = [c for c in cfgs if c["family"] == fam]
        elig = [c for c in fc if c["n_trades"] >= C.MIN_TRADES_WINNER]
        if not elig:
            P("  %s: insufficient_n — TODAS las configs por debajo de %d trades. "
              "No avanza a G2." % (fam, C.MIN_TRADES_WINNER))
            P("       (E6.4/E6.6: 'no hay muestra para decidir', NUNCA 'no hay edge')")
            continue
        # selección pre-declarada: expectativa NETA por trade (§6)
        win = max(elig, key=lambda c: c["exp_net_usd"])
        P("  %s: %d/%d configs elegibles (>=%d trades). Ganador por E[neto]/trade:"
          % (fam, len(elig), len(fc), C.MIN_TRADES_WINNER))
        P("       %s  n=%d  E[neto]=%.4f ticks (USD %.2f)  -> %s"
          % (win["config_id"], win["n_trades"], win["exp_net_ticks"],
             win["exp_net_usd"], win["veredicto"]))
    P("")
    P("  Recuento de veredictos sobre las 48:")
    for v in sorted({c["veredicto"] for c in cfgs}):
        P("     %-58s %d" % (v, sum(1 for c in cfgs if c["veredicto"] == v)))

    # -------------------- 3. LIMITACIONES -------------------------------------
    P("")
    P("-" * 100)
    P("3. LIMITACIONES ESTADISTICAS")
    P("-" * 100)
    z5 = [c for c in cfgs if c["zone_min_size"] == 5]
    P("  - zone_min_size=5 (%d celdas): estrato de BAJA POTENCIA declarado de antemano"
      % len(z5))
    P("    en E6.4. Trades: min=%d max=%d. Su escasez NO es evidencia contra la"
      % (min(c["n_trades"] for c in z5), max(c["n_trades"] for c in z5)))
    P("    hipotesis; un insufficient_n significa 'no hay muestra para decidir'.")
    P("  - Los folds son heterogeneos (E6.3): 03-26 tiene ~50%% mas zonas que 12-25.")
    P("    Por eso los conteos se reportan por fold y no solo agregados.")
    P("  - La comision (USD %.2f/pata) es ESTIMACION pre-registrada, no dato real del"
      % (cost["commission_usd"] / 2))
    P("    broker (dato faltante #1 del manifiesto). Bloquea G3, no este reporte.")
    P("  - Este reporte NO ejecuta G2 (MCPT, PBO, walk-forward): son gates aparte.")
    P("  - N_eff=48: cualquier lectura de significancia debe corregir por multiples")
    P("    pruebas. Este reporte no la aplica: la aplica G2.")

    # -------------------- 4. ANOMALIAS ----------------------------------------
    P("")
    P("-" * 100)
    P("4. ANOMALIAS Y DESCARTES")
    P("-" * 100)
    inv = sum(r["skipped_signals"]["invalid_stop"] for r in rows)
    nes = sum(r["skipped_signals"]["no_entry_step"] for r in rows)
    rej = {}
    for r in rows:
        for k, v in (r["reject_reasons"] or {}).items():
            rej[k] = rej.get(k, 0) + v
    P("  senales descartadas antes de ejecutar (sumadas sobre las 192 celdas):")
    P("     invalid_stop   %8d   el open ya estaba mas alla del stop: el trade no" % inv)
    P("                             existe (no es una decision discrecional)")
    P("     no_entry_step  %8d   sin barra posterior al disparo (borde de datos)" % nes)
    P("  rechazos del simulador:")
    for k, v in sorted(rej.items()):
        P("     %-14s %8d" % (k, v))
    ex = {}
    for c in cfgs:
        for k, v in c["exit_reasons"].items():
            ex[k] = ex.get(k, 0) + v
    P("  motivos de salida (sumados):")
    for k, v in sorted(ex.items(), key=lambda x: -x[1]):
        P("     %-16s %8d" % (k, v))
    degr = sum(f["n_quotes_degraded"] for f in meta["folds"])
    P("  quotes degradados sustituidos por libro de 1 tick: %d de %d barras (%.3f%%)"
      % (degr, sum(f["n_bars"] for f in meta["folds"]),
         100.0 * degr / max(1, sum(f["n_bars"] for f in meta["folds"]))))

    P("")
    P("-" * 100)
    P("NO se recomienda ninguna promocion. NO se abre el holdout. NO se cambia")
    P("ninguna regla despues del resultado. La decision es de Nico.")
    P("-" * 100)

    txt = "\n".join(L) + "\n"
    out = os.path.join(d, "report_A4.txt")
    open(out, "w", encoding="utf-8", newline="\n").write(txt)
    json.dump(cfgs, open(os.path.join(d, "report_A4.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(txt)
    print("reporte: %s" % out)
    print("sha256:  %s" % hashlib.sha256(txt.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
