#!/usr/bin/env python3
"""CAMP-001 A2 — EJECUCIÓN INMUTABLE.

Escribe **primero** los artefactos crudos por `config × fold` y su digest. No
rankea, no ordena por resultado, no interpreta: eso es A4, sobre artefactos ya
congelados.

Reglas de A2 (decisión de Nico):
- Un intento = desde que se calculan resultados económicos.
- Fallo técnico ANTES de producir resultados: se registra y se repite el MISMO
  comando exacto.
- Si ya se produjo cualquier resultado parcial: NO se corrige ni se relanza —
  se congela, se marca intento incompleto y decide Nico.
- Nada se ajusta a mitad de camino: ni umbrales, ni grilla, ni costos, ni folds.

Uso:
    python tools/camp001_run.py --attempt 1
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod, store, ticks as ticks_mod  # noqa: E402
from edgelab.research import camp001 as C                              # noqa: E402
from edgelab.research.holdout_guard import check_holdout               # noqa: E402
from edgelab.research.sim import simulate                              # noqa: E402

STORE = os.path.join(REPO, "runs", "nt8_bridge", "campaign_store")
OUTDIR = os.path.join(REPO, "runs", "nt8_bridge", "camp001")
TICK_VALUE_USD = 6.25
SCENARIO = "base"          # G1 se decide en 'base' (§8); los otros son G3


def _iso_ns(s):
    return int(dt.datetime.fromisoformat(s).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1e9)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Corrida inmutable de CAMP-001")
    ap.add_argument("--attempt", type=int, required=True,
                    help="numero de intento (1 = primero)")
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args(argv)

    pre_path = os.path.join(a.outdir, "preflight.json")
    if not os.path.exists(pre_path):
        print("FRENAR: no existe el preflight. Correr tools/camp001_preflight.py")
        return 1
    pre = json.load(open(pre_path, encoding="utf-8"))
    if pre.get("verdict") != "PASS":
        print("FRENAR: el preflight no dio PASS (%s)" % pre.get("verdict"))
        return 1

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                           capture_output=True, text=True).stdout.strip()
    if head != pre["git_head"] or dirty:
        print("FRENAR: el repo cambio desde el preflight (HEAD %s -> %s, %s)"
              % (pre["git_head"][:12], head[:12], "sucio" if dirty else "limpio"))
        return 1

    raw_dir = os.path.join(a.outdir, "attempt_%02d" % a.attempt)
    if os.path.exists(os.path.join(raw_dir, "raw_results.jsonl")):
        print("FRENAR: el intento %d YA tiene resultados. Los artefactos son "
              "inmutables: no se relanza sobre un intento existente." % a.attempt)
        return 1
    os.makedirs(raw_dir, exist_ok=True)

    grid = C.expand_grid()
    cost = C.cost_round_turn(SCENARIO, TICK_VALUE_USD)
    t_ini = time.time()
    print("CAMP-001 — intento %d · escenario '%s' · %d configs x %d folds"
          % (a.attempt, SCENARIO, len(grid), len(C.FOLDS)))
    print("friccion round-turn: USD %.2f = %.4f ticks" % (
        cost["total_usd"], cost["total_ticks"]))

    parts = {p["contract"]: p for p in store.get_partitions(
        STORE, indicator="Gaps2", config_id=C.CAMPAIGN_CONFIG_ID)}

    rows = []
    fold_meta = []
    for key, contract, s, e in C.FOLDS:
        t0 = time.time()
        check_holdout(s, e, purpose="development", caller="camp001_run")
        tk = ticks_mod.load_canonical_parquet(
            os.path.join(REPO, "data", "nt8", "6E", key + "_ticks.parquet"),
            contract=contract, start_utc_ns=_iso_ns(s), end_utc_ns=_iso_ns(e))
        bars = bars_mod.build_time_bars(tk, 1)
        steps, sinfo = C.build_steps(tk, bars)
        zones = store.read_zone_rows(parts[contract]["dir"])
        cache = C.precompute_triggers(zones, bars)
        print("  [%s] %d ticks · %d barras m1 · %d zonas · %d con disparo · quotes degradados=%d"
              % (contract, len(tk), len(bars), len(zones), len(cache),
                 sinfo["n_quotes_degraded"]))
        fold_meta.append(dict(contract=contract, start_utc=s, end_utc=e,
                              n_ticks=len(tk), n_bars=len(bars),
                              n_zones=len(zones), n_zones_con_disparo=len(cache),
                              **sinfo))
        for g in grid:
            sigs, skipped = C.signals_from_cache(
                cache, bars, steps, g["family"], g["zone_min_size"],
                g["stop_pad"], g["target_R"], g["time_stop_bars"],
                tk.tick_size, SCENARIO)
            r = simulate(sigs, steps, scenario=SCENARIO, tick_size=tk.tick_size,
                         tick_value=TICK_VALUE_USD, close_at_session_end=True,
                         check_guard=False)
            sm = r.summary
            n = sm["n_trades"]
            rows.append(dict(
                config_id=g["config_id"], family=g["family"],
                zone_min_size=g["zone_min_size"], stop_pad=g["stop_pad"],
                target_R=g["target_R"], time_stop_bars=g["time_stop_bars"],
                contract=contract, fold=key,
                n_signals=len(sigs), n_trades=n,
                n_rejected=sm["n_rejected"], reject_reasons=sm["reject_reasons"],
                skipped_signals=skipped,
                exit_reasons=sm["exit_reasons"],
                gross_ticks=sm["gross_ticks"], spread_ticks=sm["spread_ticks"],
                slippage_ticks=sm["slippage_ticks"],
                commission_usd=sm["commission_usd"],
                net_ticks=sm["net_ticks"], net_usd=sm["net_usd"],
                # brutos "sin friccion" para poder separar efecto vs friccion
                gross_usd=sm["gross_ticks"] * TICK_VALUE_USD,
                expectancy_gross_ticks=(sm["gross_ticks"] / n) if n else None,
                expectancy_net_ticks=sm["expectancy_net_ticks"],
                expectancy_net_usd=sm["expectancy_net_usd"],
                digest=r.digest))
        print("     ... %d celdas en %.1f s" % (len(grid), time.time() - t0))

    # ---- artefactos crudos INMUTABLES -------------------------------------- #
    rows.sort(key=lambda r: (r["config_id"], r["fold"]))
    raw_path = os.path.join(raw_dir, "raw_results.jsonl")
    with open(raw_path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    raw_sha = hashlib.sha256(open(raw_path, "rb").read()).hexdigest()
    digest = hashlib.sha256("".join(r["digest"] for r in rows)
                            .encode("utf-8")).hexdigest()[:16]

    meta = dict(
        campaign_id="CAMP-001-gaps2-discovery", attempt=a.attempt,
        manifest_sha256=C.MANIFEST_SHA256, preflight_sha256=hashlib.sha256(
            open(pre_path, "rb").read()).hexdigest(),
        git_head=head, scenario=SCENARIO, tick_value_usd=TICK_VALUE_USD,
        cost_round_turn=cost, close_at_session_end=True,
        max_concurrent_positions=1, n_configs=len(grid), n_folds=len(C.FOLDS),
        n_rows=len(rows), folds=fold_meta,
        raw_results_sha256=raw_sha, run_digest=digest,
        elapsed_sec=round(time.time() - t_ini, 1),
        finished_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        status="COMPLETE")
    with open(os.path.join(raw_dir, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True, ensure_ascii=False)

    print("\ncrudos:  %s" % raw_path)
    print("sha256:  %s" % raw_sha)
    print("digest:  %s" % digest)
    print("filas:   %d  (%d configs x %d folds)" % (len(rows), len(grid), len(C.FOLDS)))
    print("\nA2 COMPLETO. NO se miran resultados hasta que A3 de INTEGRITY_PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
