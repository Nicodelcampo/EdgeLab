#!/usr/bin/env bash
# Instala el autopilot en un Debian 12+ (como root). No toca credenciales: las pone el humano en /etc/edgelab/autopilot.env (0600).
set -euo pipefail
apt-get update -qq && apt-get install -y -qq git python3-venv python3-pip curl
id edgelab >/dev/null 2>&1 || useradd --system --create-home --home-dir /opt/edgelab --shell /usr/sbin/nologin edgelab
install -d -o edgelab -g edgelab /var/lib/edgelab-autopilot /etc/edgelab
[ -d /opt/edgelab/EdgeLab ] || sudo -u edgelab git clone https://github.com/Nicodelcampo/EdgeLab.git /opt/edgelab/EdgeLab
sudo -u edgelab python3 -m venv /opt/edgelab/venv
sudo -u edgelab /opt/edgelab/venv/bin/pip install -q numpy pandas pyarrow scipy jsonschema
[ -f /etc/edgelab/autopilot.json ] || install -o edgelab -g edgelab -m 0644 /opt/edgelab/EdgeLab/deploy/debian/autopilot.example.json /etc/edgelab/autopilot.json
[ -f /etc/edgelab/candidates.json ] || echo '[]' | install -o edgelab -g edgelab -m 0644 /dev/stdin /etc/edgelab/candidates.json
[ -f /etc/edgelab/autopilot.env ] || install -o edgelab -g edgelab -m 0600 /dev/null /etc/edgelab/autopilot.env
cp /opt/edgelab/EdgeLab/deploy/debian/edgelab-autopilot.{service,timer} /etc/systemd/system/
systemctl daemon-reload
echo "Listo. Modo por defecto: 'propose' (no lanza nada). Para activar: editar /etc/edgelab/autopilot.json (mode=execute) y luego: systemctl enable --now edgelab-autopilot.timer"
echo "Detener todo: touch /var/lib/edgelab-autopilot/PAUSE (o systemctl disable --now edgelab-autopilot.timer)"
