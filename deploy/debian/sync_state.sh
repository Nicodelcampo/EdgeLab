#!/usr/bin/env bash
# Sube el estado del autopilot (registro de pruebas, evidencia viva, riqueza de alfa, bitácora, borradores) a la rama `autopilot/state` del repo.
# Es el ÚNICO escritor de esa rama: así el código (rama de trabajo) se actualiza solo con fast-forward y el estado nunca se bifurca.
# Requiere una deploy key con permiso de escritura (ver LEEME.md). Si falta, no hace nada y sale con 0.
set -euo pipefail
STATE=/var/lib/edgelab-autopilot/state
cd "$STATE"
# respaldo diario de la base SQLite (no va a git): copia consistente con la API de backup, se conservan 14 días
B=/var/lib/edgelab-autopilot/backups; mkdir -p "$B"
[ -f autopilot_runs/runs.sqlite ] && [ ! -f "$B/runs-$(date -u +%F).sqlite" ] && /opt/edgelab/venv/bin/python -c "import sqlite3,sys;s=sqlite3.connect(sys.argv[1]);d=sqlite3.connect(sys.argv[2]);s.backup(d);d.close()" autopilot_runs/runs.sqlite "$B/runs-$(date -u +%F).sqlite" || true
ls -1t "$B"/runs-*.sqlite 2>/dev/null | tail -n +15 | xargs -r rm -f
# manifiestos de lanzamiento (versiones de datasets por kernel): kaggle_launch.py los escribe en el clon de CÓDIGO, que está fijado y
# no se publica; se copian al estado para que la custodia de cada corrida quede en `autopilot/state` (auditoría 2026-10-24)
L=/opt/edgelab/EdgeLab/docs/data_catalog/launches
if [ -d "$L" ]; then mkdir -p autopilot_runs/launches; cp -u "$L"/*.json autopilot_runs/launches/ 2>/dev/null || true; fi
# el libro de LORD++ canónico también vive en el clon de código (decisión 2026-10-24): su copia va al estado
LL=/opt/edgelab/EdgeLab/docs/research/LIBRO_LORD.json; [ -f "$LL" ] && cp "$LL" autopilot_runs/libro_lord.json
[ -n "$(git status --porcelain)" ] || exit 0
# lista blanca: solo los archivos de estado conocidos (no logs arbitrarios ni la base SQLite, que se respalda aparte)
for f in alpha.json evidence_runtime.jsonl trial_registry.jsonl autopilot.log.jsonl heartbeat.json promociones.jsonl sala_outbox.jsonl sala_aprobaciones.jsonl mejoras.jsonl candidates.json propuestas.jsonl alertas.jsonl biblioteca_manifiesto.json edge_brain_ledger.jsonl auditorias.jsonl pedidos_humano.jsonl holdout_aperturas.jsonl confirmaciones_lordpp.json programacion.jsonl pedidos_codigo.jsonl libro_lord.json HOLDOUT_VENTANAS.jsonl; do [ -f autopilot_runs/$f ] && git add autopilot_runs/$f; done
for f in autopilot_runs/embudo/*/estado.json autopilot_runs/embudo/*/MEDIDO.md autopilot_runs/embudo/*/ACTA_HOLDOUT.json autopilot_runs/launches/*.json; do [ -f "$f" ] && git add "$f"; done
git -c user.name=edgelab-autopilot -c user.email=autopilot@localhost commit -qm "autopilot: estado $(date -u +%FT%TZ)" || exit 0
git push -q origin HEAD:autopilot/state || echo "sync_state: no se pudo hacer push (¿deploy key?); el estado queda local" >&2
