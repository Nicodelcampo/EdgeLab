#!/usr/bin/env bash
# Instala el autopilot en un Debian 12+ (como root). No instala credenciales: ver LEEME.md (setup_kaggle_credentials.sh y deploy key).
# Variables opcionales: REPO_URL, CODE_BRANCH (rama de código a seguir; por defecto la rama de trabajo actual del proyecto).
set -euo pipefail
REPO_URL=${REPO_URL:-https://github.com/Nicodelcampo/EdgeLab.git}
CODE_BRANCH=${CODE_BRANCH:-claude/vibrant-clarke-s9z6e2}
H=/opt/edgelab; S=/var/lib/edgelab-autopilot
apt-get update -qq && apt-get install -y -qq git python3-venv python3-pip curl ca-certificates
id edgelab >/dev/null 2>&1 || useradd --system --create-home --home-dir $H --shell /usr/sbin/nologin edgelab
install -d -o edgelab -g edgelab $S /etc/edgelab
# 1) código (solo fast-forward)
[ -d $H/EdgeLab ] || sudo -u edgelab git clone --branch "$CODE_BRANCH" "$REPO_URL" $H/EdgeLab
# 2) estado (otro clon, rama autopilot/state; único escritor)
if [ ! -d $S/state ]; then
  sudo -u edgelab git clone "$REPO_URL" $S/state
  (cd $S/state && (sudo -u edgelab git checkout -q autopilot/state 2>/dev/null || sudo -u edgelab git checkout -q --orphan autopilot/state) && sudo -u edgelab git rm -rqf . 2>/dev/null || true)
  sudo -u edgelab mkdir -p $S/state/autopilot_runs $S/state/autopilot_drafts
  printf 'runs.sqlite\nruns.sqlite-journal\nheartbeat.json\n' | sudo -u edgelab tee $S/state/autopilot_runs/.gitignore >/dev/null
fi
# 3) entorno Python
sudo -u edgelab python3 -m venv $H/venv
sudo -u edgelab $H/venv/bin/pip install -q numpy pandas pyarrow scipy jsonschema
# 4) configuración (no pisa lo existente)
[ -f /etc/edgelab/autopilot.json ] || install -o edgelab -g edgelab -m 0644 $H/EdgeLab/deploy/debian/autopilot.example.json /etc/edgelab/autopilot.json
[ -f /etc/edgelab/candidates.json ] || echo '[]' | install -o edgelab -g edgelab -m 0644 /dev/stdin /etc/edgelab/candidates.json
[ -f /etc/edgelab/autopilot.env ] || install -o edgelab -g edgelab -m 0600 /dev/null /etc/edgelab/autopilot.env
# 5) systemd
cp $H/EdgeLab/deploy/debian/edgelab-autopilot{,-generate}.{service,timer} /etc/systemd/system/ 2>/dev/null || true
cp $H/EdgeLab/deploy/debian/edgelab-autopilot.service $H/EdgeLab/deploy/debian/edgelab-autopilot.timer $H/EdgeLab/deploy/debian/edgelab-autopilot-generate.service $H/EdgeLab/deploy/debian/edgelab-autopilot-generate.timer /etc/systemd/system/
systemctl daemon-reload
echo "Instalado. Siguiente: LEEME.md (credencial de Kaggle, deploy key, doctor, primer ciclo en modo propose)."
