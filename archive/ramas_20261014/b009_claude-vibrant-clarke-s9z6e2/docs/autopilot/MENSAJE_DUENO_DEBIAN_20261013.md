# Mensaje para el dueño del Debian

Hola, el autopilot ya está listo del lado del código. Está en la rama `claude/vibrant-clarke-s9z6e2` (PR #64, commit `d82a956b`). Cuando lo instales, fijá esa versión: ya no se actualiza solo en cada ciclo, y para cambiarla se usa `deploy/debian/update.sh <sha>`.

## Qué cambió
Corregimos lo que marcó la revisión de Research Ops.
- Valida los p-values y hace las operaciones de alfa de forma atómica.
- Anota el envío a Kaggle antes de enviarlo, y no reenvía solo un envío incierto.
- Usa un solo controlador por estado y un tope diario común de lanzamientos de la cuenta.
- El manifiesto de protegidos ya está refrescado (`autopilot_protect.py check` da OK).

## Lo que falta de tu lado
Detalle en `deploy/debian/LEEME.md`.
1. Correr `install.sh`.
2. Cargar el token de Kaggle con `setup_kaggle_credentials.sh`.
3. Crear la deploy key de GitHub con permiso de escritura.
4. Copiar a `/etc/edgelab/candidates.json` las candidatas promovidas.
5. Correr `autopilot_doctor.py` y arrancar en modo `propose`, con `PAUSE` puesto, hasta revisar el primer ciclo.

## Avisos
- Todavía no se probó en un Debian real, así que el primer ciclo conviene mirarlo en vivo.
- El autopilot pide Python 3.10 o superior. Research Ops (PR #117) pide 3.12, así que van en venvs separados.
- No pasar a `execute` solo porque el doctor diga "LISTO". Antes hay que verificar el acceso a Kaggle con una operación mínima.
- Las campañas actuales dieron resultados nulos o de información (nivel C). Nada se promueve a estrategia todavía.

Cualquier cosa, el estado y los resultados están en `docs/research/autopilot_runs/`.
