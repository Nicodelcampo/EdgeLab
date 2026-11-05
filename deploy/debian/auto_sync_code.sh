#!/usr/bin/env bash
# auto_sync_code.sh — Sincronización automática pre-ciclo para el agente Debian (SV1)
# Resuelve:
#   1) El bloqueo por árbol sucio cuando Embudo o lanzadores escriben estado vivo en CODE_DIR.
#   2) El estancamiento por detached HEAD en update.sh al hacer fast-forward seguro hacia
#      origin/foundation/f0b-compatibility-probe antes de cada ciclo.
#   3) El auto-reset de unidades systemd (como edgelab-autopilot-generate.service) caídas en failed.
set -euo pipefail

CODE_DIR="${EDGELAB_CODE_DIR:-/opt/edgelab/EdgeLab}"
STATE_DIR="${EDGELAB_STATE_DIR:-/var/lib/edgelab-autopilot/state}"
TARGET_BRANCH="${EDGELAB_TARGET_BRANCH:-foundation/f0b-compatibility-probe}"

mkdir -p "$STATE_DIR/autopilot_runs" "$STATE_DIR/launches"

cd "$CODE_DIR"

# 1. Evacuar archivos de estado vivo que hayan quedado sucios en CODE_DIR hacia STATE_DIR
LIVE_FILES=(
  "docs/research/EVALUABLES.jsonl"
  "docs/research/LIBRO_LORD.json"
  "docs/research/LINAJES.jsonl"
  "docs/research/autopilot_runs/account_launches.jsonl"
)

for rel in "${LIVE_FILES[@]}"; do
  if [ -f "$CODE_DIR/$rel" ] && ! git diff --quiet -- "$rel" 2>/dev/null; then
    cp -f "$CODE_DIR/$rel" "$STATE_DIR/autopilot_runs/$(basename "$rel").bak"
    git checkout -q -- "$rel" || true
  fi
done

# Evacuar launches/*.json no rastreados o modificados hacia STATE_DIR/launches
if [ -d "$CODE_DIR/docs/data_catalog/launches" ]; then
  cp -f "$CODE_DIR/docs/data_catalog/launches/"*.json "$STATE_DIR/launches/" 2>/dev/null || true
  git checkout -q -- "docs/data_catalog/launches" 2>/dev/null || true
  git clean -fdq "docs/data_catalog/launches" 2>/dev/null || true
fi

# Limpiar locks efímeros (*.lock)
find "$CODE_DIR/docs/research" -name "*.lock" -delete 2>/dev/null || true

# 2. Fetch y fast-forward seguro hacia origin/$TARGET_BRANCH
git fetch -q origin "$TARGET_BRANCH"

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "origin/$TARGET_BRANCH")"

if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  if git merge-base --is-ancestor "$LOCAL_SHA" "$REMOTE_SHA"; then
    if [ -z "$(git status --porcelain)" ]; then
      git checkout -q --detach "$REMOTE_SHA"
      echo "[auto_sync_code] Fast-forward limpio: $LOCAL_SHA -> $REMOTE_SHA"
    else
      echo "[auto_sync_code] AVISO: árbol aún con cambios locales; se omite checkout a $REMOTE_SHA" >&2
    fi
  else
    echo "[auto_sync_code] AVISO: HEAD ($LOCAL_SHA) diverge de origin/$TARGET_BRANCH ($REMOTE_SHA)" >&2
  fi
fi

# 3. Auto-reset de servicios systemd que hayan quedado en estado 'failed'
for svc in edgelab-autopilot-generate.service edgelab-autopilot-programador.service; do
  if systemctl is-failed --quiet "$svc" 2>/dev/null; then
    systemctl reset-failed "$svc" 2>/dev/null || true
    echo "[auto_sync_code] Servicio recuperado de estado failed: $svc"
  fi
done
