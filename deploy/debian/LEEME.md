# Despliegue del autopilot en Debian: lista de pasos (≈ 20 min)

Estado: probado con ejecutores simulados (15 tests), una corrida de humo real en Kaggle y dos campañas reales lanzadas por el propio autopilot (IDM-1, SLOT-1). Ensayado el 2026-10-16 en Debian 13 (WSL): instalación, doctor (LISTO con credencial Bearer), protegidos OK y un ciclo `propose` pausado. **Falta la prueba en SV1**: los pasos 1–7.

## Lo que ya está hecho
Instalador, servicios systemd endurecidos (ciclo cada 10 min, regeneración diaria de borradores), sincronización de estado a la rama `autopilot/state` (único escritor), doctor de preflight, kill switch, latido, `--status`, guardas (holdout, pre-registro committeado, configuración textual en el pre-registro, archivos protegidos), alpha-investing, selector, generador de candidatas, evidencia viva, puente al Edge Brain.

## Mandato del agente
El agente se rige por [`MANDATO.md`](../../MANDATO.md) (edges útiles para challenges y combinables; no pequeños, inestables ni sin diversificación). Está protegido por hash. **Antes de arrancar en modo `execute`, confirmá en `config/autopilot/mandate.json` las reglas reales del challenge y los umbrales** (hoy son valores de ejemplo).

## Lo que falta de tu lado (los «pocos detalles»)
1. **Máquina:** Debian 12+, 2 vCPU / 4 GB RAM / 20 GB disco, salida HTTPS a `www.kaggle.com`, `github.com`, `storage.googleapis.com`, `squeezemetrics.com` (DIX). No necesita GPU (el cómputo pesado va a Kaggle).
2. **Instalar:** `sudo CODE_REF=<sha o tag revisado> bash deploy/debian/install.sh` (clona el repo, lo FIJA en ese commit, crea el clon de estado, el venv y copia los servicios). Cambiar de versión: `deploy/debian/update.sh <ref>`.
3. **Credencial de Kaggle:** token nuevo de kaggle.com → Settings → API. Con el formato `KGAT_…`: `read -rs KAGGLE_API_TOKEN && export KAGGLE_API_TOKEN && sudo -E bash deploy/debian/setup_kaggle_credentials.sh` (queda como cabecera Bearer 0600, sólo para www.kaggle.com). Con usuario y clave viejos: `sudo KAGGLE_USERNAME=... KAGGLE_KEY=... bash deploy/debian/setup_kaggle_credentials.sh`.
3a. **Segunda cuenta de Kaggle (reparto, 2026-10-26):** con el token de la cuenta de Gonza: `read -rs KAGGLE_API_TOKEN && export KAGGLE_API_TOKEN KAGGLE_CUENTA=nicobuttaro && sudo -E bash deploy/debian/setup_kaggle_credentials.sh` (queda en `/opt/edgelab/.kaggle_auth_header.nicobuttaro`). En `/etc/edgelab/autopilot.env`: `EDGELAB_KAGGLE_CUENTAS=nicolasbuttaro,nicobuttaro` y `EDGELAB_KAGGLE_API=https://www.kaggle.com/api/v1` (en el Debian no hay proxy: un solo host y una cabecera por cuenta). Una campaña con `"cuenta_kaggle": "auto"` lanza cada etapa en la cuenta con menos kernels corriendo; las dos cuentas tienen que ver los datasets privados (compartidos como lector). Probar: `sudo -u edgelab env EDGELAB_KAGGLE_OWNER=nicobuttaro EDGELAB_KAGGLE_API=https://www.kaggle.com/api/v1 /opt/edgelab/venv/bin/python tools/kaggle_kernel.py status --slug nicobuttaro/cualquiera` → un 404 en JSON (no 401) confirma la credencial.
3b. **Claude para los roles:** el instalador deja el CLI en `/opt/edgelab/.local/bin`. Con tu cuenta, en cualquier máquina, `claude setup-token`; pegá el resultado como `CLAUDE_CODE_OAUTH_TOKEN=...` en `/etc/edgelab/autopilot.env` (0600). Nunca `ANTHROPIC_API_KEY`. Los roles y la sala se encienden en `/etc/edgelab/autopilot.json` (`roles_ledger`, `sala`).
4. **Deploy key de GitHub** (solo para publicar el estado): `sudo -u edgelab ssh-keygen -t ed25519 -f /opt/edgelab/.ssh/id_ed25519 -N ''`, agregar la clave pública como *deploy key con escritura* y cambiar a SSH el remoto del clon de estado **y el del clon de código** (`git -C /opt/edgelab/EdgeLab remote set-url origin git@github.com:Nicodelcampo/EdgeLab.git`): la promoción automática publica cada pre-registro en `autopilot/prereg/<run_id>` antes de lanzar y, si no puede, rechaza la candidata. Sin ella el autopilot funciona igual y el estado queda local (`sync_state.sh` avisa y sigue).
5. **Candidatas:** `/var/lib/edgelab-autopilot/state/autopilot_runs/candidates.json` empieza vacío (el instalador migra uno viejo de `/etc/edgelab`). Copiá ahí las promovidas (`python tools/autopilot_generate.py promote ...`) después de revisar el borrador y de que el pre-registro esté committeado en la rama de código.
6. **Protegidos:** `python tools/autopilot_protect.py check` debe dar OK; cada cambio legítimo a gates/guardas exige que un humano refresque el manifiesto y lo committee.
7. **Doctor y primer ciclo (modo propose):** `sudo -u edgelab /opt/edgelab/venv/bin/python tools/autopilot_doctor.py --config /etc/edgelab/autopilot.json` → debe decir LISTO; luego `sudo systemctl start edgelab-autopilot.service` y revisar `--status`. Recién después, en `/etc/edgelab/autopilot.json` poner `"mode": "execute"` y `sudo systemctl enable --now edgelab-autopilot.timer edgelab-autopilot-generate.timer edgelab-propfirm-refresh.timer edgelab-watchdog.timer`.
8. **Regla de decisión `escalera_v1` (2026-10-22, decisión de Nico).** Reemplaza Holm + alpha-investing, cuya riqueza quedó en
   0,0025 y ya no deja descubrir nada (`docs/research/auditoria_embudo_20261022/AUDITORIA_EMBUDO_A_FONDO_20261022.md`). En dos pasos:
   - Actualizar el código (`update.sh <sha>`), parar el timer y probar sobre una COPIA del estado (no toca nada real):
     `sudo -u edgelab /opt/edgelab/venv/bin/python tools/autopilot_activar_escalera.py --config /etc/edgelab/autopilot.json --root /var/lib/edgelab-autopilot/state/autopilot_runs --candidates /var/lib/edgelab-autopilot/state/autopilot_runs/candidates.json`
     → revisar que `status.decision` sea `escalera_v1` y que las corridas cerradas tengan `regla: escalera_v1`.
   - Si se ve bien: el mismo comando con `--aplicar` (agrega `decision` y `escalera` a la configuración, con respaldo
     `autopilot.json.antes_escalera`) y volver a encender el timer. Para volver atrás, restaurar el respaldo.
   La plantilla `autopilot.example.json` ya trae la clave. `fdr.py` y `alpha.json` no cambian; no hace falta refrescar protegidos.

## Operación
- Estado: `sudo -u edgelab /opt/edgelab/venv/bin/python -m edgelab.autopilot --root /var/lib/edgelab-autopilot/state/autopilot_runs --config /etc/edgelab/autopilot.json --candidates /var/lib/edgelab-autopilot/state/autopilot_runs/candidates.json --status`
- Parada de emergencia: `touch /var/lib/edgelab-autopilot/PAUSE` (o `systemctl disable --now edgelab-autopilot.timer`). Para reanudar, borrar el archivo. La sala usa otro interruptor (`PAUSE_SALA`): su `reanudar` nunca levanta una pausa de consola.
- Sala: `sala_inbox.jsonl` debe ser del usuario del agente de Chaski y no escribible por grupo u otros (0644/0600); si no, el autopilot ignora los comandos y lo avisa.
- Vigilante: `edgelab-watchdog.timer` (cada 30 min) y `OnFailure=` en los servicios escriben `alertas.jsonl` y la sala; con `EDGELAB_ALERT_URL=https://ntfy.sh/<tópico>` en `autopilot.env` también avisa al celular.
- Respaldo: `sync_state.sh` copia `runs.sqlite` una vez por día a `/var/lib/edgelab-autopilot/backups` (14 días).
- Conocimiento: el servicio de generación indexa cada día la biblioteca del proyecto (Brain/hipocampo, 400+ papers SSRN normalizados, extracciones y grafo, research propio, MEDIDO/NO MEDIDO, registros de pruebas, resultados del autopilot) en `biblioteca.json`, con sha256 y commit de cada fuente; el manifiesto (sin texto) se sube a `autopilot/state`. Proponente y revisor reciben fichas citables de esa biblioteca y cada propuesta guarda las fuentes exactas que usó (`propuestas.jsonl`).
- Registro de pruebas: el autopilot escribe su propio `trial_registry.jsonl` en el clon de estado; para sumarlo al contador global, copiarlo a `docs/research/autopilot_runs/` del repo de código y correr `python tools/registro_global.py` (idempotente).
- Qué mira el humano: `REPORT.md` de borradores (rama `autopilot/state`), `autopilot.log.jsonl`, la riqueza de alfa y los hallazgos exploratorios.

## Embudo: lo agregado el 2026-10-26 (todo informativo salvo lo que declara la campaña antes de correr)
- **Etapa ATRAS** (después del OOS): con `"atras": [YYYYMMDD, YYYYMMDD]` (años ANTERIORES al DESC que la familia no usó) corre las
  candidatas congeladas ahí y publica A_FAVOR / EN_CONTRA_PASADO / NO_CONCLUYENTE. **Nunca mata**: el pasado no refuta lo que funciona
  en el régimen actual (ATJ-24); el resultado va al acta del holdout. Sin `atras`, la etapa se salta.
- **Potencia**: con `"potencia_previa": {"ops_mes", "sd_op", "efecto_util"}` el PREFLIGHT publica el MDE de DESC/OOS/holdout y los meses
  que harían falta; al final del DESC se publica la potencia prevista de cada candidata en el OOS y en el holdout. No bloquea.
- **Estadístico normalizado**: un experimento declara `NORMALIZAR = "rango_sesion_previa"` en su módulo (P&L neto dividido por el rango
  de la sesión anterior del instrumento de ejecución; causal). Baja la varianza cuando los días son muy distintos.
- **Eventos macro**: `EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=("CPI","NFP","FOMC"))` en el módulo deja fuera las
  entradas en esas ventanas; toda réplica publica además `eventos` (parte de las operaciones y del P&L cerca de un evento). Calendario:
  el de `edgelab/noticias.py` (fuente única); después de regenerar ese CSV, `python tools/eventos_desde_noticias.py --write` y commitear.
- **Meta-análisis entre instrumentos** de una regla congelada: `edgelab.funnel.metaanalisis.combinar` (efecto fijo y aleatorio, I²).
- **Reparto entre cuentas**: `"cuenta_kaggle": "auto"` (paso 3a).

## Grilla masiva y programador (2026-10-22)
- **Usar la modalidad:** plantilla `config/autopilot/grillas/AREAS_EXP_1.json` (RunSpecs E0/DESC/REP, kernel committeado `tools/kaggle_areas/kernel_areas.py`, salida `STUDY_RESULTS.json` con `/disc` y `/rep/` que lee `escalera_v1`). Orden y errores a no repetir: `docs/research/GUIA_GRILLA_MASIVA.md`.
- **Generar variantes sin código:** env `GRILLA` (JSON con NS/WS/XS/A_CORTES). `n_trials` = celdas de la grilla; el pre-registro lleva el bloque JSON exacto (la guarda lo compara).
- **Experimentos nuevos o mejoras:** los escribe el programador. Para encenderlo, `"programador": {"activo": true, ...}` en `/etc/edgelab/autopilot.json` y `systemctl enable --now edgelab-autopilot-programador.timer`. Pedido manual: `python tools/autopilot_generate.py pedir-codigo --state <estado> "qué hacer" --por-que "..."`.
- **Revisión humana:** `programacion.jsonl` (rama `autopilot/state`) lista cada pedido con su estado. Las ramas `autopilot/codigo/*` se mergean a la rama de trabajo; las `autopilot/propuesta/*` se revisan como PR. Sin deploy key el commit queda local y `update.sh` lo protege.

## Embudo automático (2026-10-23)
- **Encender:** `"embudo": {"activo": true, ...}` y `"dukascopy": {...}` en `/etc/edgelab/autopilot.json` (ver `autopilot.example.json`).
  Después `systemctl enable --now edgelab-datos-dukascopy.timer`.
- **Carpeta sellada** (`/var/lib/edgelab-datos/holdout_sellado`): ahí van los datos desde la sesión del 2026-10-01. Nunca se suben a
  Kaggle, y sólo los lee una etapa de holdout con acta.
- **NQ sellado:** si hay ticks de NQ posteriores al 2026-10-01 (exportados de NT8), se copian ahí como `NQ_ticks.parquet`.
- **Lanzar una campaña:** el agente (o una persona) deja el JSON en `config/autopilot/grillas/campanas/` con `"embudo": true` y
  `"conductor": "debian"`. El ciclo sólo conduce las campañas con ese conductor (`embudo.conductor` en `/etc/edgelab/autopilot.json`);
  las de `"conductor": "local"` (hoy EXPZ-NQ y EXPZ-CFD) se siguen corriendo con `tools/embudo_correr.py` y el Debian las informa
  como omitidas. Nunca dos conductores sobre una campaña: relanzarían el mismo slug de Kaggle con estados y libros distintos.
- **Libros del embudo en el estado** (todos los sube `sync_state.sh` a `autopilot/state`): `embudo/<cid>/estado.json`,
  `libro_lord.json` (LORD++ por familia), `HOLDOUT_VENTANAS.jsonl` (ventanas consumidas y aperturas: cada ciclo le agrega las filas
  nuevas del libro del repo), `trial_registry.jsonl` y `launches/*.json` (versiones de datasets de cada kernel). Al cerrar una etapa
  con desenlaces, pasar al repo de código las filas nuevas del registro y del libro de ventanas (`tools/registro_global.py`).
- **Seguir una campaña:** `autopilot_runs/embudo/<cid>/MEDIDO.md` en la rama `autopilot/state`.

## Límites que conviene tener presentes
- El autopilot no opera ni promueve: solo lanza y analiza estudios pre-registrados. Un hallazgo es exploratorio hasta que se replica en datos no usados.
- Con la regla vieja (sin `decision: escalera_v1`), si la riqueza de alfa se agota deja de lanzar campañas nuevas. Con `escalera_v1` eso no pasa: el tamiz FDR nomina y LORD++ confirma en réplica (`confirmaciones_lordpp.json`, que `sync_state.sh` sube).
- `max_per_day` y `max_concurrent` acotan el uso de cómputo de Kaggle (cuota de GPU/CPU de tu cuenta).
- Las claves nunca van al repo ni a la configuración: solo `.netrc` (0600) y la deploy key.
