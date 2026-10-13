#!/usr/bin/env bash
# Sube el estado del autopilot (registro de pruebas, evidencia viva, riqueza de alfa, bitácora, borradores) a la rama `autopilot/state` del repo.
# Es el ÚNICO escritor de esa rama: así el código (rama de trabajo) se actualiza solo con fast-forward y el estado nunca se bifurca.
# Requiere una deploy key con permiso de escritura (ver LEEME.md). Si falta, no hace nada y sale con 0.
set -euo pipefail
STATE=/var/lib/edgelab-autopilot/state
cd "$STATE"
[ -n "$(git status --porcelain)" ] || exit 0
# lista blanca: solo los archivos de estado conocidos (no logs arbitrarios ni la base SQLite, que se respalda aparte)
for f in alpha.json evidence_runtime.jsonl trial_registry.jsonl autopilot.log.jsonl heartbeat.json; do [ -f autopilot_runs/$f ] && git add autopilot_runs/$f; done
git -c user.name=edgelab-autopilot -c user.email=autopilot@localhost commit -qm "autopilot: estado $(date -u +%FT%TZ)" || exit 0
git push -q origin HEAD:autopilot/state || echo "sync_state: no se pudo hacer push (¿deploy key?); el estado queda local" >&2
