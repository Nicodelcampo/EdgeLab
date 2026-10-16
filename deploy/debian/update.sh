#!/usr/bin/env bash
# Cambia el código del autopilot a una release EXACTA (sha o tag) tras revisarla. Con el timer parado o entre ciclos; nunca durante una corrida del controlador.
set -euo pipefail
[ $# -eq 1 ] || { echo "uso: update.sh <sha|tag>" >&2; exit 2; }
cd /opt/edgelab/EdgeLab
systemctl is-active --quiet edgelab-autopilot.service && { echo "el controlador está en ejecución; reintentá luego" >&2; exit 1; }
git fetch -q origin
# Los pre-registros que commitea la promoción automática no pueden quedar huérfanos al cambiar de versión.
if [ -z "$(git branch -r --contains HEAD)" ] && [ "${FORCE:-0}" != 1 ]; then
  echo "HEAD tiene commits que no están en ningún remoto (pre-registros de la promoción automática)." >&2
  echo "Subilos antes:  git push origin HEAD:refs/heads/autopilot/prereg   (o repetí con FORCE=1 si sabés lo que perdés)" >&2
  exit 1
fi
git checkout -q --detach "$1" && git rev-parse HEAD
