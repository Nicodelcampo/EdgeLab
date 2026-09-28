#!/usr/bin/env bash
# Cola nocturna 2026-09-24/25 (Nico duerme, PC disponible ~8 h). Aprobaciones vigentes:
# "OK censo TBZ y OK manifiestos TBZ-E2 y TREND-MICRO". Nada de esto toca el holdout ni reservas.
#
# Principio (visión bola de nieve): el tiempo tiene que rendir, no correr por correr.
#  - orden por valor: primero lo que decide (ES primario), después el apoyo (MES);
#  - guardia de memoria: antes de cada paso pesado espera >= 4 GB libres (hubo dos cuelgues de la PC);
#  - si un paso falla, no se corren los que dependen de él (no se queman horas sobre un error);
#  - cada paso deja un marcador en el log, para retomar sin repetir.
set -u
cd /e/EdgeLab-unified-viewer || exit 1
PY=/e/EdgeLab/.venv/Scripts/python
LOG=artifacts/overnight_20260924.log
export PYTHONIOENCODING=utf-8

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }
free_mb() { powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)" | tr -d '\r'; }
wait_ram() {
  while true; do
    f=$(free_mb)
    if [ -n "$f" ] && [ "$f" -ge 4000 ]; then return 0; fi
    log "esperando RAM (libre ${f} MB < 4000)"; sleep 120
  done
}
run() {  # run <nombre> <comando...>
  local name=$1; shift
  if grep -q "^OK $name\$" "$LOG.done" 2>/dev/null; then log "ya hecho: $name"; return 0; fi
  wait_ram
  log "INICIO $name (libre $(free_mb) MB)"
  "$@" >> "artifacts/overnight_${name}.txt" 2>&1
  local rc=$?
  if [ $rc -eq 0 ]; then echo "OK $name" >> "$LOG.done"; log "FIN $name OK"; else log "FIN $name FALLA rc=$rc"; fi
  return $rc
}

log "=== cola nocturna arranca ==="

# 1) esperar el censo de ES que ya está corriendo (marcador 'exit' en su propio log)
while ! grep -q "^exit" artifacts/tbz_e2/census_run_ES.txt 2>/dev/null; do sleep 120; done
if ! grep -q "^exit 0" artifacts/tbz_e2/census_run_ES.txt; then
  log "el censo ES terminó con error: no se corre E2b ES"; ES_OK=0
else
  ES_OK=1
  # por si alguna sesión quedó sin escribir (reintento idempotente: salta las que existen)
  run census_ES_retry "$PY" tools/tbz_e2.py census --inst ES --workers 2 || ES_OK=0
fi

# 2) TBZ-E2 en ES: resumen del censo, simulación, nulo N3 y reporte (decide)
if [ "$ES_OK" = 1 ]; then
  run summary_ES "$PY" tools/tbz_e2.py summary --inst ES
  run explore_ES "$PY" tools/tbz_e2.py explore --inst ES --workers 2 && \
  run report_ES  "$PY" tools/tbz_e2.py report --inst ES
fi

# 3) TREND-MICRO: esperar su corrida (NQ y ES) y reportar
while ! grep -q "^exit" artifacts/trend_micro_run.txt 2>/dev/null; do sleep 120; done
if grep -q "^exit 0" artifacts/trend_micro_run.txt; then
  run report_TMIC "$PY" tools/trend_micro.py report
else
  log "TREND-MICRO terminó con error: no se reporta"
fi

# 4) TBZ-E2 en MES (apoyo, mismo subyacente; no decide)
run census_MES "$PY" tools/tbz_e2.py census --inst MES --workers 2 && \
run summary_MES "$PY" tools/tbz_e2.py summary --inst MES && \
run explore_MES "$PY" tools/tbz_e2.py explore --inst MES --workers 2 && \
run report_MES "$PY" tools/tbz_e2.py report --inst MES

log "=== cola nocturna termina ==="
