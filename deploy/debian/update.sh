#!/usr/bin/env bash
# Cambia el código del autopilot a una release EXACTA (sha o tag) tras revisarla. Con el timer parado o entre ciclos; nunca durante una corrida del controlador.
set -euo pipefail
[ $# -eq 1 ] || { echo "uso: update.sh <sha|tag>" >&2; exit 2; }
cd /opt/edgelab/EdgeLab
# git siempre como edgelab, dueño del clon: como root falla por "dubious ownership" y dejaría archivos de root en .git.
if [ "$(id -un)" = edgelab ]; then G=(git); else G=(sudo -u edgelab git); fi
systemctl is-active --quiet edgelab-autopilot.service && { echo "el controlador está en ejecución; reintentá luego" >&2; exit 1; }
"${G[@]}" fetch -q origin
# Los pre-registros que commitea la promoción automática no pueden quedar huérfanos al cambiar de versión.
if [ -z "$("${G[@]}" branch -r --contains HEAD)" ] && [ "${FORCE:-0}" != 1 ]; then
  echo "HEAD tiene commits que no están en ningún remoto (pre-registros de la promoción automática)." >&2
  echo "Subilos antes:  git push origin HEAD:refs/heads/autopilot/prereg   (o repetí con FORCE=1 si sabés lo que perdés)" >&2
  exit 1
fi
"${G[@]}" checkout -q --detach "$1" && "${G[@]}" rev-parse HEAD
