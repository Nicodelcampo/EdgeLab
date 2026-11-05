# Runbook: actualizar SV1 y volver a lanzar el agente del Debian (2026-11-01)

Estado: VIGENTE. Lo ejecuta una persona con acceso root a SV1 (Gonza) o el Claude Code de SV1 con este documento como pedido.
Contexto: `docs/research/HANDOFF_DEBIAN_20261030.md`, `docs/research/REVISION_SV1_20261030.md`, `docs/CARTERA_VIVA.md`.

## Diagnóstico (desde `autopilot/state`, 2026-11-01)
- **Pausado desde el 2026-10-30 01:09 (-03)** (archivo `PAUSE`): el último ciclo registrado es del 2026-10-30 04:03 UTC y desde ahí
  sólo publica el estado una vez por día (último 2026-10-31 09:22 UTC). No lanza nada.
- **Código viejo:** SV1 corre `0f3a5466` (26-oct); `foundation` va ~80 commits adelante (cartera viva, criba maxT con alfa por canal,
  salida τ, arreglos de CONTEO/404/lectura sellada, PRERANGE, familias del 31-oct).
- **Estados divergentes:** 23 campañas viejas en SV1; en el repo hay ~60 con actas y estados más nuevos (las corrió la nube).

## Pasos (en este orden; cada uno se verifica antes del siguiente)
1. **Foto del estado actual, sin tocar nada:**
   `cd /opt/edgelab/EdgeLab && git log -1 --oneline && git status --short | head -50 && ls -la /var/lib/edgelab-autopilot/PAUSE && systemctl list-timers 'edgelab*'`
2. **Respaldo de todo lo que escribe el ciclo en el clon de código** (libros append-only y manifiestos):
   `B=/var/lib/edgelab-autopilot/backup_20261101 && install -d -o edgelab $B && cp -a docs/research/{LIBRO_LORD.json,TRIAL_REGISTRY_GLOBAL.jsonl,HOLDOUT_VENTANAS.jsonl,EVALUABLES.jsonl} docs/research/autopilot_runs $B/ 2>/dev/null; cp -a /var/lib/edgelab-autopilot/state/autopilot_runs/embudo $B/embudo_sv1`
3. **Unir los libros append-only** de SV1 con los de `foundation` (unión de líneas sin duplicados; el LORD++ con `edgelab.funnel.libro_lord`
   cuidando no repetir pasos). Si SV1 tiene filas que el repo no tiene, se suben en un PR antes de seguir.
4. **Actualizar el código** al último commit de `foundation` revisado: `sudo -u edgelab deploy/debian/update.sh <sha>` (protege el libro
   de LORD++ y los manifiestos de lanzamiento).
5. **Reconciliar las campañas (una sola fuente de verdad):** para cada campaña con estado en el repo
   (`docs/research/*/embudo/<CID>/estado.json`), copiar esa carpeta sobre `/var/lib/edgelab-autopilot/state/autopilot_runs/embudo/<CID>/`.
   El estado del repo manda (tiene las actas). Las campañas que la nube conduce hoy (`"conductor": "local"`: paquete del 31-oct,
   PRERANGE-ZONAS, PRERANGE-BASE) se pasan a `"conductor": "debian"` en un commit **y** la sesión en la nube deja de conducirlas en el
   mismo momento: nunca dos conductores sobre la misma campaña.
6. **Instalar las unidades nuevas** (cartera viva): `sudo cp deploy/debian/edgelab-cartera.{service,timer} /etc/systemd/system/ &&
   sudo install -o edgelab -m 0644 config/cartera/cartera.json /etc/edgelab/cartera.json && sudo systemctl daemon-reload`
   (el timer de la cartera queda APAGADO hasta congelar los cortes de régimen: `tools/cartera_diaria.py cortes`).
7. **Doctor y tests rápidos:** `sudo -u edgelab /opt/edgelab/venv/bin/python tools/autopilot_doctor.py` y
   `sudo -u edgelab /opt/edgelab/venv/bin/python -m pytest -q tests/research/test_embudo*.py tests/research/test_cartera_viva.py`.
   Si algo falla: causa raíz, no se sigue.
8. **Quitar la pausa** (decisión de Nico o Gonza, regla del handoff): `rm /var/lib/edgelab-autopilot/PAUSE` y
   `sudo systemctl enable --now edgelab-autopilot.timer edgelab-autopilot-generate.timer`.
9. **Verificar el primer ciclo:** `journalctl -u edgelab-autopilot -n 100`, y en GitHub que `autopilot/state` publique un estado nuevo
   con las campañas reconciliadas (ninguna relanzada desde cero).

## Lo que NO se hace
No abrir el holdout de la canasta de 7 (falta lo de su handoff), no cambiar gates ni mandato, no habilitar cuentas reales.
