#!/usr/bin/env bash
# Cambia el código del autopilot a una release EXACTA (sha o tag) tras revisarla. Con el timer parado o entre ciclos; nunca durante una corrida del controlador.
set -euo pipefail
[ $# -eq 1 ] || { echo "uso: update.sh <sha|tag>" >&2; exit 2; }
cd /opt/edgelab/EdgeLab
systemctl is-active --quiet edgelab-autopilot.service && { echo "el controlador está en ejecución; reintentá luego" >&2; exit 1; }
git fetch -q origin && git checkout -q --detach "$1" && git rev-parse HEAD
