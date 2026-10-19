# Revisión de la estructura del agente autónomo (Debian), 2026-10-19

Revisé el código de `origin/main`: `edgelab/autopilot/*`, `tools/autopilot_generate.py` y `deploy/debian/*`.
Es una revisión de lectura: no corrí nada en SV1.

## Qué está bien (conservar)
- El ciclo es idempotente: un `oneshot` cada 10 minutos, con bloqueo por directorio de estado, latido, conciliación de apuestas de alfa huérfanas y `SEND_UNCERTAIN`.
- Las guardas viven en el código y no en los prompts: holdout, pre-registro committeado, protegidos por hash, alpha-investing y la tabla `mejora.NUNCA`.
- Los roles LLM tienen el perímetro correcto:
  - no orquestan;
  - salida con esquema;
  - `sanitize` falla cerrado;
  - caché por hash, tope diario y gobernador de rate limit.
- El estado vive en otro clon (`autopilot/state`) con un único escritor y una lista blanca de archivos.
- Por defecto todo arranca apagado: `mode: propose`, `auto_promocion: false` y cronista apagado.

## Defectos concretos (corregir antes de encender la promoción automática)
1. **`auto-promote` no puede escribir.**
   - Causa: `edgelab-autopilot-generate.service` usa `ProtectSystem=strict`, que deja `/etc` en solo lectura, y su `ReadWritePaths` no incluye `/etc/edgelab`. Aun así, `promover_auto` escribe `/etc/edgelab/candidates.json` y `promociones.jsonl`, que por defecto va al lado de `candidates.json`.
   - Efecto: con `auto_promocion=true` falla en el primer intento.
   - Además, `sync_state.sh` busca `promociones.jsonl` en `autopilot_runs/`, así que nunca lo sube.
   - Arreglo: mover `candidates.json` y `promociones.jsonl` a `/var/lib/edgelab-autopilot/state/autopilot_runs/`. La configuración (`autopilot.json`) queda en `/etc`, en solo lectura, que es lo correcto.
2. **Los pre-registros automáticos se commitean en el clon de código.**
   - El clon queda en HEAD desacoplado (`update.sh` hace `checkout --detach`) y no tiene deploy key de escritura: la deploy key es del clon de estado.
   - Consecuencias:
     - quedan commits locales que no ve nadie;
     - `update.sh` se niega a actualizar hasta que alguien los suba a mano;
     - cada promoción ensucia el árbol del que corre el código fijado.
   - Arreglo: commitear los pre-registros en el clon de estado (en una rama `autopilot/prereg` o dentro de `autopilot/state`) y empujarlos antes de lanzar. La guarda «pre-registro committeado» tiene que verificar contra ese repo, por ruta y SHA, y además exigir que el push haya salido. Así el pre-registro queda público antes de la corrida, que es lo que le da valor.
3. **«reanudar» desde la sala puede levantar una pausa puesta por un humano en la consola.** Hoy `PAUSE` es un solo archivo. Recomiendo dos:
   - `PAUSE` (consola): solo la consola la crea y la borra;
   - `PAUSE_SALA`: la sala solo puede crear y borrar esta.

   El ciclo se detiene si existe cualquiera de las dos.
4. **El campo `autor` de `sala_inbox.jsonl` no está autenticado.** Es texto que escribe cualquier proceso con acceso al archivo.
   - Mitigación mínima: archivo 0600, propiedad de un usuario distinto de `edgelab` (el del agente Chaski), y ese usuario sin permiso de escritura sobre el estado.
   - Ideal: firmar cada comando con HMAC, con la clave en `autopilot.env`.
5. **El latido no puede detectar su propia muerte.** `diagnosticar` mira `heartbeat_age_s` dentro del mismo ciclo que debería estar corriendo. Hace falta un vigilante externo:
   - un timer aparte, cada 30 minutos, que alerte si el latido tiene más de 1 hora o si `systemctl is-failed`;
   - `OnFailure=edgelab-alerta@%n.service` en las tres unidades;
   - la alerta va a la sala por archivo, más un mail o ntfy opcional.
6. **El instalador no deja el código fijado.** Clona `CODE_BRANCH` (que por defecto es `feat/agente-sv1-consolidacion`, una rama de trabajo) en su punta, y el código recién queda fijado con el primer `update.sh <sha>`. Recomiendo que `install.sh` exija un SHA o tag y haga `checkout --detach` de entrada. El servicio tiene que correr siempre una release revisada.
7. **Detalles menores.**
   - `install.sh` copia las unidades dos veces.
   - El servicio de generación no tiene el mismo endurecimiento que el principal: le faltan `PrivateTmp`, `ProtectHome`, `CapabilityBoundingSet=` y `MemoryMax`.
   - `MemoryMax=3G` en una máquina de 4 GB deja poco margen si coinciden los dos servicios.
   - La generación no toma el `.lock` del estado mientras escribe candidatas. Hay que tomarlo, o escribir con `os.replace` para que el ciclo nunca lea un JSON a medias.

## Recomendaciones de funcionamiento
1. **Encendido por etapas.** Cada etapa dura 1 o 2 semanas y pasa a la siguiente solo con cero incidentes.
   | Etapa | Configuración |
   |---|---|
   | 1 | `propose`, sin roles |
   | 2 | `execute` con `max_per_day=1`, solo candidatas promovidas a mano |
   | 3 | Cronista encendido |
   | 4 | Proponente y revisor generando borradores, sin promoción automática |
   | 5 | Recién ahí `auto_promocion`, con la enmienda AUTONOMIA-A1 firmada y con `max_por_ciclo=1` |
2. **Un hito de punta a punta antes de la etapa 2.** El autopilot lanza en SV1 una corrida barata y conocida, trae el resultado, liquida alfa, escribe el Brain y sube el estado. Hoy eso solo se probó en WSL y desde este contenedor.
3. **Holdout que avance con el tiempo.** `HOLDOUT_FIRST_TRADE_DATE` está fijo en 2026-10-01 y desde entonces se acumulan datos nuevos. Si nadie decide cuándo se abre y cuál es el siguiente corte, el agente se queda sin datos frescos o alguien abre el holdout sin protocolo. Conviene pre-registrar un calendario: por ejemplo, un nuevo bloque de holdout por trimestre, con la regla de apertura escrita en `MANDATO.md`, que es un archivo protegido.
4. **Revisor más independiente.**
   - Hoy el revisor es el mismo modelo que el proponente y se le pide independencia solo por prompt.
   - Que reciba únicamente el pre-registro y las métricas públicas, nunca el texto del proponente con su argumentación. Hoy recibe `borrador`, que es el texto completo.
   - Que tenga una tasa de PROMOTE esperada: si promueve más del 30 %, alarma.
5. **Topes de multiplicidad.**
   - `MAX_TRIALS_AUTO=500` por candidata es mucho frente a una riqueza de alfa inicial de 0,05.
   - Recomiendo un tope diario de pruebas nuevas por toda la promoción automática (por ejemplo 200) y que cada pre-registro declare su `N_eff`.
6. **Novedad por título.** El Jaccard sobre el título deja pasar la misma familia con otro nombre. Hay que sumar el `spec_hash` del estudio y la tupla `(script, instrumento, ventana)` contra las familias retiradas.
7. **Telemetría de costo.**
   - Ya existe `llm_calls`. Hay que agregar los minutos de Kaggle por día, la riqueza de alfa a lo largo del tiempo y la tasa de hallazgos por lente.
   - El cronista debería publicar eso una vez por semana, no en cada ciclo, para no gastar suscripción ni llenar la sala.
8. **Respaldo de `runs.sqlite`.** Queda afuera del estado sincronizado y no hay respaldo automático. Recomiendo un `sqlite3 .backup` diario a otro disco, o subirlo cifrado.
9. **Pendientes ya conocidos.**
   - Python 3.12 en Debian contra 3.11 en el venv: fijar la versión.
   - El FDR global asume independencia entre campañas: si los datos se reusan, exigir una réplica en datos nuevos.

## Prioridad
Si hay que elegir, lo mínimo antes de pasar a `execute`:
- los defectos 1, 2 y 5;
- el hito de punta a punta;
- la decisión sobre el calendario de holdout.

Lo demás puede ir en paralelo con la etapa 1.
