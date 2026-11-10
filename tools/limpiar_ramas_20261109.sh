#!/usr/bin/env bash
# Limpieza de ramas remotas (docs/RAMAS_20261109.md, aprobada por Nico el 2026-11-10). La sesión en la nube sólo puede escribir en su
# propia rama, así que esto se corre desde un clon con permiso de escritura:  bash tools/limpiar_ramas_20261109.sh
set -u
F=origin/foundation/f0b-compatibility-probe
git fetch -q origin
# 1) Integradas: se borran sólo si siguen sin commits que foundation no tenga
INTEGRADAS="chore/conductores-debian claude/noticias-calendario claude/project-thread-dfg222 claude/project-thread-dn74yx claude/project-thread-dzozxn claude/project-thread-idwi7k claude/project-thread-l4tr0z claude/project-thread-umwqbt debian/libros-sv1-20261101 docs/handoff-debian feat/agente-sv1-consolidacion feat/control-barajado feat/kalman-fade feat/simular-cierre fix/canasta-regimen-evidencia fix/ci-verde-20261030 fix/embudo-estado-transitorio fix/fdr-dependencia fix/generate-lente-duplicada fix/holdout-local-sellado fix/indice-docs fix/sync-state-heartbeat research/prerange-hft-20261030 research/prereg-canasta-12 research/prereg-canasta-12b research/prereg-v2"
for r in $INTEGRADAS; do
  if [ "$(git rev-list --count "$F..origin/$r" 2>/dev/null)" = "0" ]; then git push origin --delete "$r"; else echo "NO se borra $r (cambió o ya no existe)"; fi
done
# 2) Viejas con archivos propios: etiqueta de archivo y después se borra la rama (no se pierde nada)
for r in feat/kit-herramientas-tres-franjas research/k37-prereg-corredor-hft-20261017; do
  git tag "archive/$r" "origin/$r" && git push origin "archive/$r" && git push origin --delete "$r"
done
