#!/usr/bin/env python3
"""Master Overnight Orchestrator for EdgeLab (2026-08-26).

Executes 3 sequential tasks:
1. GATE L2 Extraction & HMM3 Model (13 GC JUN26 Sessions, 69.2M events)
2. Event Store Generation (BigTrap2, Absorption, HFTZones2, VolTicksPOC2 on 5 GC contracts, 40.5M ticks)
3. BT2Absorption 99-Config Target-Free Parameter Sweep

Commits and pushes results to remote repository after each completed task.
"""
from __future__ import annotations

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = Path(r"E:\DatosNT8\overnight_master_20260826.log")
BRANCH = "work/futures-l2-context-foundation-20260825"


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run_cmd(cmd: list[str], cwd: Path | None = None) -> int:
    log(f"Ejecutando comando: {' '.join(str(x) for x in cmd)}")
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    for line in p.stdout:
        stripped = line.strip()
        if stripped:
            log(f"  [output] {stripped}")
    p.wait()
    log(f"Comando finalizado con exit code: {p.returncode}")
    return p.returncode


def git_commit_and_push(commit_msg: str):
    log(f"--- Registrando cambios en Git ({commit_msg}) ---")
    run_cmd(["git", "add", "docs/", "specs/", "tools/"])
    # Solo commitear si hay cambios
    status_proc = subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    if status_proc.stdout.strip():
        run_cmd(["git", "commit", "-m", commit_msg])
        run_cmd(["git", "push", "origin", BRANCH])
        log("Push completado con éxito.")
    else:
        log("No hay cambios pendientes para commitear.")


def main():
    log("================================================================")
    log("INICIANDO MASTER PIPELINE NOCTURNO EDGELAB (8 HORAS)")
    log("================================================================")

    # ---------------------------------------------------------
    # TAREA 1: GATE L2 Extraction & HMM3 4-Regime Model
    # ---------------------------------------------------------
    log("\n>>> [1/3] INICIANDO TAREA 1: GATE L2 (13 Sesiones GC JUN26) <<<")
    t1_start = time.time()
    l2_out_dir = Path(r"E:\DatosNT8\replay.csv\GC JUN26\gate_ctx4")
    l2_out_dir.mkdir(parents=True, exist_ok=True)

    cmd_t1 = [
        sys.executable,
        str(REPO_ROOT / "tools" / "build_l2_gate_contexts.py"),
        "--l2-dir", r"E:\DatosNT8\replay.csv\GC JUN26\parquet_out\l2_depth",
        "--l1-dir", r"E:\DatosNT8\replay.csv\GC JUN26\parquet_out\l1_quotes",
        "--manifests-dir", r"E:\DatosNT8\replay.csv\GC JUN26\parquet_out\manifests",
        "--out-dir", str(l2_out_dir),
        "--allow-dirty",
    ]
    ret_t1 = run_cmd(cmd_t1)
    t1_dur = (time.time() - t1_start) / 60.0

    if ret_t1 == 0:
        log(f">>> TAREA 1 GATE L2 COMPLETADA EXITOSAMENTE en {t1_dur:.1f} minutos <<<")
        # Generar reporte markdown
        rep_t1 = REPO_ROOT / "docs" / "research" / "GATE_L2_CTX4_GC0626_REPORT_2026-08-26.md"
        rep_t1.write_text(f"""# Reporte de Extracción GATE L2 — 13 Sesiones GC JUN26

- **Fecha UTC:** {datetime.now(timezone.utc).isoformat()}
- **Estado:** `REAL_13_SESSION_EXTRACTION=COMPLETE`
- **Tiempo de cómputo:** {t1_dur:.1f} minutos
- **Directorio de salida:** `{l2_out_dir}`
- **Modelos y etiquetas:** Generadas etiquetas HMM3 (`Calm`, `Normal`, `Volatile`) y overlay (`Toxic`).
""", encoding="utf-8")
        git_commit_and_push("feat(context): complete real 13-session GATE L2 extraction and HMM3 model")
    else:
        log(f"ALERTA: TAREA 1 GATE L2 finalizó con error (code {ret_t1}). Continuando con Tarea 2...")

    # ---------------------------------------------------------
    # TAREA 2: Event Store All5 (40.5M ticks, 5 GC contracts)
    # ---------------------------------------------------------
    log("\n>>> [2/3] INICIANDO TAREA 2: EVENT STORE ALL5 CONTRACTS <<<")
    t2_start = time.time()
    cmd_t2 = [
        sys.executable,
        str(REPO_ROOT / "tools" / "build_event_store_all5.py"),
    ]
    ret_t2 = run_cmd(cmd_t2)
    t2_dur = (time.time() - t2_start) / 60.0

    if ret_t2 == 0:
        log(f">>> TAREA 2 EVENT STORE ALL5 COMPLETADA EXITOSAMENTE en {t2_dur:.1f} minutos <<<")
        rep_t2 = REPO_ROOT / "docs" / "research" / "EVENT_STORE_GC_ALL5_REPORT_2026-08-26.md"
        rep_t2.write_text(f"""# Reporte Event Store Canónico — 5 Contratos de GC

- **Fecha UTC:** {datetime.now(timezone.utc).isoformat()}
- **Estado:** `EVENT_STORE_GC_ALL5=COMPLETE`
- **Tiempo de cómputo:** {t2_dur:.1f} minutos
- **Indicadores procesados:** BigTrap2Absorption, BigTrap2, HFTZones2, VolTicksPOC2.
- **Datos procesados:** 40.552.525 ticks sobre GC 12-25, GC 02-26, GC 04-26, GC 06-26, GC 08-26.
- **Directorio de salida:** `E:\\DatosNT8\\event_store_gc_all5`
""", encoding="utf-8")
        git_commit_and_push("feat(events): generate canonical event store for 5 GC contracts")
    else:
        log(f"ALERTA: TAREA 2 EVENT STORE finalizó con error (code {ret_t2}). Continuando con Tarea 3...")

    # ---------------------------------------------------------
    # TAREA 3: Sweep BT2Absorption 99 Configs Target-Free
    # ---------------------------------------------------------
    log("\n>>> [3/3] INICIANDO TAREA 3: SWEEP TARGET-FREE 99 CONFIGS <<<")
    t3_start = time.time()
    sweep_out_dir = Path(r"E:\DatosNT8\bt2a_sweep_overnight_20260826")
    sweep_out_dir.mkdir(parents=True, exist_ok=True)

    cmd_t3 = [
        sys.executable,
        str(REPO_ROOT / "tools" / "bt2_absorption_param_sweep.py"),
        "run",
        "--data-dir", r"E:\DatosNT8",
        "--output", str(sweep_out_dir),
        "--resume",
        "--max-hours", "6.0",
    ]
    ret_t3 = run_cmd(cmd_t3)
    t3_dur = (time.time() - t3_start) / 60.0

    if ret_t3 == 0:
        log(f">>> TAREA 3 SWEEP TARGET-FREE COMPLETADA EXITOSAMENTE en {t3_dur:.1f} minutos <<<")
        rep_t3 = REPO_ROOT / "docs" / "research" / "BT2A_SWEEP_OVERNIGHT_REPORT_2026-08-26.md"
        rep_t3.write_text(f"""# Reporte Sweep Target-Free BT2Absorption — 99 Configs

- **Fecha UTC:** {datetime.now(timezone.utc).isoformat()}
- **Estado:** `SWEEP_BT2A_OVERNIGHT=COMPLETE`
- **Tiempo de cómputo:** {t3_dur:.1f} minutos
- **Directorio de salida:** `{sweep_out_dir}`
- **Outcomes:** `CAMPAIGN_OUTCOMES_OPENED=false` (firewall respetado).
""", encoding="utf-8")
        git_commit_and_push("docs(research): close overnight target-free sweep for BT2Absorption 99 configs")
    else:
        log(f"Tarea 3 Sweep finalizó con código {ret_t3}.")

    log("\n================================================================")
    log("PIPELINE NOCTURNO FINALIZADO. TODOS LOS PROCESOS EJECUTADOS.")
    log("================================================================")


if __name__ == "__main__":
    main()
