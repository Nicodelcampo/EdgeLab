# Resolución de la revisión del agente en Debian, 2026-10-19

Responde a `REVISION_ESTRUCTURA_DEBIAN_20261019.md`. Antes de corregir, integré `main` en esta rama: ahí está la versión
más nueva del agente (roles, sala, promoción). En los conflictos del agente y del despliegue tomé la versión de `main`.
En los del funnel conservé la de esta rama, que tiene EF0 con custodia, multiplicidad y huella del kernel.
El manifiesto de protegidos da `OK`: no toqué `guard.py`, `fdr.py`, `spec.py` ni `kaggle_launch.py`.

## Resuelto
| # | Problema | Qué cambió | Dónde |
|---|---|---|---|
| 1 | `auto-promote` no podía escribir (`/etc` en solo lectura) y `promociones.jsonl` no se subía | `candidates.json` y `promociones.jsonl` pasan a `/var/lib/edgelab-autopilot/state/autopilot_runs/`. El instalador migra el archivo viejo de `/etc`. `sync_state.sh` sube los dos. | servicios, `install.sh`, `sync_state.sh`, `LEEME.md` |
| 2 | Los pre-registros automáticos quedaban como commits locales | Cada pre-registro se publica en la rama `autopilot/prereg/<run_id>` **antes** de entrar a la lista. Si el push falla, la candidata se rechaza (`RECHAZADA_NO_PUBLICADA`). La rama queda en `promociones.jsonl`. `update.sh` ya no se traba porque esos commits están en el remoto. | `promocion.py` (`publicar_prereg`, por defecto `true`) |
| 3 | `reanudar` desde la sala levantaba una pausa de consola | Hay dos interruptores. `PAUSE` es de consola; `PAUSE_SALA` es lo único que la sala crea o borra. El ciclo para con cualquiera de los dos y `--status` muestra cuáles están activos. | `daemon.py`, `__main__.py`, `sala.py` |
| 4 | El autor del inbox de la sala no está autenticado | Si `sala_inbox.jsonl` es escribible por grupo u otros, se ignora entero y se avisa en la sala. La firma HMAC queda pendiente. | `sala.py` |
| 5 | El latido no detectaba su propia muerte | Nuevo vigilante externo: `edgelab-watchdog.timer` (cada 30 min) y `OnFailure=edgelab-alerta@` en los servicios. Revisa latido viejo, envíos inciertos, unidades fallidas y pausas de más de 24 h. Escribe `alertas.jsonl` y la sala, y opcionalmente manda un POST a `EDGELAB_ALERT_URL` (ntfy). No repite una alerta antes de 6 h. | `tools/autopilot_watchdog.py`, unidades nuevas |
| 6 | El instalador corría la punta de una rama | `install.sh` exige `CODE_REF` (sha o tag) y deja el código fijado en ese commit. | `install.sh`, `LEEME.md` |
| 7 | Detalles menores | El servicio de generación tiene el mismo endurecimiento que el principal. Las unidades se copian una sola vez. La auto-promoción toma el `.lock` del estado. `candidates.json` se escribe de forma atómica. | servicios, `promocion.py`, `autopilot_generate.py` |
| 8 | `runs.sqlite` sin respaldo | Copia diaria consistente (API de backup de SQLite) a `/var/lib/edgelab-autopilot/backups`; se conservan 14 días. | `sync_state.sh` |

## Acceso del agente a todo lo que sabe el proyecto, con trazabilidad
Antes, el proponente recibía solo lo que se armaba a mano. Además, `contexto.proponer` no se llamaba desde ningún lado.

Ahora existe `edgelab/autopilot/conocimiento.py`, la **biblioteca del agente**. Es determinista y no usa LLM.

**Qué indexa** (hoy son 1.495 fuentes y 41.267 pasajes, en unos 45 s):
- el Cerebro / hipocampo (`edge_brain` ledgers);
- más de 400 papers SSRN normalizados, sus extracciones, el grafo y el cerebro SSRN;
- `literature_leads.json`;
- todo `docs/research` (RESULTADO, MEDIDO / NO MEDIDO, pre-registros);
- los incidentes;
- los resultados y documentos del autopilot;
- los registros de pruebas y `evidence_seed`;
- `MANDATO.md` y `EDGES_DISCOVERED.md`;
- del estado vivo: el registro de pruebas, la evidencia, las promociones, las propuestas y las mejoras.

**Trazabilidad:** cada fuente lleva tipo, `sha256` y el último commit que la tocó. La biblioteca completa tiene una huella. El manifiesto (sin el texto) se sube a `autopilot/state`.

**Cómo la usa el agente:**
- **Búsqueda:** BM25 sobre los pasajes. Devuelve citas `ruta#Llínea` junto con el sha del archivo.
- **Proponente** (`autopilot_generate.py propose`, encendido con `proponente: true`): recibe el tablero (familias retiradas, edges, corridas) y fichas citables, separadas entre literatura y research propio. Los vacíos salen de las marcas «NO MEDIDO / pendiente». La consigna le pide citar las fichas que usa y no reproponer lo que ya se midió. Cada propuesta queda en `propuestas.jsonl` con la lente, la huella de la biblioteca, el commit del repo, el sha del paquete y la lista exacta de fuentes entregadas. Con eso se puede reconstruir con qué información se decidió.
- **Revisor:** recibe antecedentes del proyecto sobre el tema de la candidata. Si la candidata repite algo ya medido o muerto, o contradice un resultado propio sin explicarlo, la consigna es KILL. Las referencias usadas quedan en `promociones.jsonl`.
- Lo recuperado es contexto, no evidencia. Los pasajes pasan por `sanitize`, así que no viajan rutas locales ni secretos.
- El servicio diario de generación corre en este orden: `index`, `draft`, `propose` (si está encendido) y `auto-promote` (si la enmienda está firmada).

## Pruebas
- Nuevas: `tests/test_autopilot_conocimiento.py`, más la publicación del pre-registro con remoto y sin remoto en `test_autopilot_promocion.py`.
- Las pruebas del autopilot dan **72 passed**.
- Suite completa: ver el commit. Las únicas fallas son por `duckdb`, que no está instalado en este contenedor, y son ajenas a este cambio.

## Pendiente (fuera de mi alcance desde acá)
- **Prueba de punta a punta en SV1** con una corrida barata. Necesita la máquina.
- **Calendario de holdout** que avance con el tiempo. Lo decide Nico: va en `MANDATO.md`, que está protegido.
- **Topes de multiplicidad** de la auto-promoción (`MAX_TRIALS_AUTO`, un tope diario). Toca el control de errores: lo decide un humano.
- **Firma HMAC** de los comandos de la sala. Necesita un cambio coordinado con el agente de Chaski.
- **Versión fija de Python** en el venv. El CI usa 3.12; conviene instalar 3.12 en SV1.
- **Configurar en SV1:** la deploy key también en el clon de código (`LEEME` paso 4), `EDGELAB_ALERT_URL` si se quiere aviso al celular, y `systemctl enable --now edgelab-watchdog.timer`.
