#!/usr/bin/env bash
# Instala el autopilot en un Debian 12+ (como root). No instala credenciales: ver LEEME.md (setup_kaggle_credentials.sh y deploy key).
# Obligatoria: CODE_REF = sha o tag REVISADO que va a correr el servicio (queda fijado; cambiarlo es `update.sh <ref>`).
# Opcional: REPO_URL.
set -euo pipefail
REPO_URL=${REPO_URL:-https://github.com/Nicodelcampo/EdgeLab.git}
: "${CODE_REF:?definí CODE_REF=<sha o tag revisado> (el servicio nunca corre la punta de una rama)}"
H=/opt/edgelab; S=/var/lib/edgelab-autopilot
apt-get update -qq && apt-get install -y -qq git python3-venv python3-pip curl ca-certificates
id edgelab >/dev/null 2>&1 || useradd --system --create-home --home-dir $H --shell /usr/sbin/nologin edgelab
install -d -o edgelab -g edgelab $S /etc/edgelab
# 1) código (solo fast-forward)
[ -d $H/EdgeLab ] || sudo -u edgelab git clone "$REPO_URL" $H/EdgeLab
(cd $H/EdgeLab && sudo -u edgelab git fetch -q origin && sudo -u edgelab git checkout -q --detach "$CODE_REF" && git rev-parse HEAD)
# 2) estado (otro clon, rama autopilot/state; único escritor)
if [ ! -d $S/state ]; then
  sudo -u edgelab git clone "$REPO_URL" $S/state
  (cd $S/state && (sudo -u edgelab git checkout -q autopilot/state 2>/dev/null || sudo -u edgelab git checkout -q --orphan autopilot/state) && sudo -u edgelab git rm -rqf . 2>/dev/null || true)
  sudo -u edgelab mkdir -p $S/state/autopilot_runs $S/state/autopilot_drafts
  printf 'runs.sqlite\nruns.sqlite-journal\nheartbeat.json\n' | sudo -u edgelab tee $S/state/autopilot_runs/.gitignore >/dev/null
fi
# 3) entorno Python
sudo -u edgelab python3 -m venv $H/venv
sudo -u edgelab $H/venv/bin/pip install -q numpy pandas pyarrow scipy numba jsonschema
# 3b) CLI de Claude para los roles (suscripción por CLAUDE_CODE_OAUTH_TOKEN en /etc/edgelab/autopilot.env; nunca API key)
if [ ! -x $H/.local/bin/claude ]; then sudo -u edgelab env HOME=$H bash -c 'curl -fsSL https://claude.ai/install.sh | bash' || echo "AVISO: no se pudo instalar el CLI de Claude; los roles quedan apagados"; fi
install -d -o edgelab -g edgelab -m 0700 $H/.claude
# 4) configuración (no pisa lo existente)
[ -f /etc/edgelab/autopilot.json ] || install -o edgelab -g edgelab -m 0644 $H/EdgeLab/deploy/debian/autopilot.example.json /etc/edgelab/autopilot.json
# candidatas y promociones viven en el estado (escribibles por el servicio endurecido y sincronizadas a autopilot/state)
C=$S/state/autopilot_runs/candidates.json
if [ ! -f $C ]; then
  if [ -f /etc/edgelab/candidates.json ]; then install -o edgelab -g edgelab -m 0644 /etc/edgelab/candidates.json $C && mv /etc/edgelab/candidates.json /etc/edgelab/candidates.json.migrado
  else echo '[]' | install -o edgelab -g edgelab -m 0644 /dev/stdin $C; fi
fi
install -d -o edgelab -g edgelab $S/backups
[ -f /etc/edgelab/autopilot.env ] || install -o edgelab -g edgelab -m 0600 /dev/null /etc/edgelab/autopilot.env
# 5) systemd
for u in edgelab-autopilot.service edgelab-autopilot.timer edgelab-autopilot-generate.service edgelab-autopilot-generate.timer \
         edgelab-autopilot-programador.service edgelab-autopilot-programador.timer edgelab-datos-dukascopy.service edgelab-datos-dukascopy.timer \
         edgelab-propfirm-refresh.service edgelab-propfirm-refresh.timer edgelab-watchdog.service edgelab-watchdog.timer edgelab-alerta@.service; do
  cp $H/EdgeLab/deploy/debian/$u /etc/systemd/system/
done
systemctl daemon-reload
echo "Instalado. Siguiente: LEEME.md (credencial de Kaggle, deploy key, doctor, primer ciclo en modo propose)."
