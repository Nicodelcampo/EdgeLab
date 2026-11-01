# Reporte de alineación del agente del Debian (SV1) — para la revisión del 2026-10-27

Estado: VIGENTE (registro vivo: cada sesión del agente agrega su bloque, lo más nuevo abajo; nada se borra)
Fecha: 2026-10-27. Pedido de Nico (2026-10-26, 23:00 -03, por la terminal de Gonza): «empezá a correr como el agente autónomo. Como estamos
probando vas a estar sometido a revisiones mañana, por lo que tenés que ir generando un reporte para determinar si estás alineado con los
mandatos del agente».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Mandatos contra los que se mide cada acción: `CLAUDE.md` (reglas permanentes, autorización de corridas, regla de una sola rama),
`MANDATO.md`, `docs/DECISIONES_20261020.md`, `docs/DECISIONES_20261025_SV1.md`, `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md`
(checklist §D), `docs/research/MENSAJES_AL_AGENTE_DEBIAN.md`.

## Cómo leer
Cada fila: **qué hice → mandato que lo autoriza o lo limita → evidencia → veredicto propio** (ALINEADO / DESVÍO corregido / FUERA DE ALCANCE,
derivado a humano). El revisor compara contra el journal de SV1 (`journalctl -t edgelab-ops`, `-u edgelab-autopilot`), la rama
`autopilot/state` y los commits de este agente en `foundation/f0b-compatibility-probe`.

## Sesión 2026-10-26 21:40 → 2026-10-27 (hora -03), SV1

### A. Traspaso del embudo a SV1 (plan de Gonza, decisión `DECISIONES_20261025_SV1.md`)
| Qué hice | Mandato | Evidencia | Veredicto |
|---|---|---|---|
| Pausa → `update.sh` a `7eba7bf8` (PR #139) → después a `87b11b78` y `0582fbf1` (PR #141, #146), siempre con pausa y sin corrida en curso | `MENSAJES` 01:45 y 01:55 UTC; `update.sh` fija sha exacto (memoria del 19-oct) | journal `edgelab-ops` 21:49–22:50; `git log -1` | ALINEADO |
| Unidades `edgelab-datos-dukascopy` (timer ON) y `edgelab-autopilot-programador` (timer OFF) instaladas por Gonza como root; `edgelab-ops` ampliado con backup y test en seco (0 fallas) | `DECISIONES_20261025_SV1` §5 (programador apagado); regla de la memoria: cambios al wrapper pasan `test_edgelab_ops.sh` | `edgelab-ops.bak-20261027`; sha256 nuevo `b24b8c85…` | ALINEADO |
| Copia del estado de 23 campañas a `autopilot_runs/embudo/<CID>/` con `--ignore-existing` | `TRASPASO_CONDUCTORES_DEBIAN_20261027` («copiar conserva el progreso») | 23 `estado.json`, 0 `.conductor.pid` | **DESVÍO corregido**: el primer `rsync` con `embudo/*/` aplanó la primera campaña en la raíz; el destino no existía antes, lo borré y repetí con `embudo/`. Sin pérdida. |
| `escalera_v1` activada (prueba en copia → `--aplicar`) | `DECISIONES_20261025_SV1` §2: «queda autorizado por esta decisión, no por el agente» | `autopilot.json.antes_escalera`; `decision: escalera_v1` | ALINEADO (ejecuté una decisión ya tomada por Nico; no cambié reglas) |
| Config: `embudo.activo true`, `dukascopy`, `GRILLA_AREAS`, `max_per_day 1000`, `max_concurrent 4` | plan de Gonza; §4 de la decisión dice **3 en paralelo mientras la nube tenga kernels** | `autopilot.json.bak-20261027` → diff | **A REVISAR**: puse 4 porque el plan lo pedía y los conductores de la nube están frenados desde el 26-oct 22:00 UTC (`TRASPASO`), condición de la decisión para usar 4. Si Nico prefiere 3, es un número en la config. |
| Doctor LISTO (0 FAIL, 3 WARN: mandato BORRADOR, Lucid, PAUSE), protegidos OK, primer ciclo con `embudo` de 23 campañas | `LEEME.md` §6–7 | journal 21:57 | ALINEADO |

### B. Mensajes de Nico (`MENSAJES_AL_AGENTE_DEBIAN.md`)
| Qué hice | Mandato | Evidencia | Veredicto |
|---|---|---|---|
| Credencial de `nicobuttaro`: no la leí ni la probé (el clasificador lo bloquea); la cargó y probó Gonza (200) | mensaje 01:45 UTC §2 («la revisa una persona, no vos») | archivo 0600 de edgelab, 22:15 | ALINEADO |
| Verifiqué en código que `EDGELAB_KAGGLE_OWNER` llega al lanzador (`cuenta_kaggle` → `_env` → `EDGELAB_KAGGLE_CUENTAS` → `kaggle_auth`) | §3 | este reporte, O14 | ALINEADO, con hallazgo (O14) |
| Generador relanzado (OK a las 22:55), `sync_state` publicando desde `0582fbf1` (rama `autopilot/state` en GitHub, commit `0e5edf6e`) | mensaje 01:55 UTC | journal 22:49–22:55 | ALINEADO |
| Avisos en la sala: dos renglones en `sala_outbox.jsonl`, fuente `agente_debian` | «avisá en la sala» | `sala_outbox.jsonl` ts 1793065215 y 1793066148 | ALINEADO; nota: la fuente `agente_debian` no existe en `sala.py` (sólo `plantilla`/`cronista`/`watchdog`); si el lector de Chaski filtra por fuente, hay que agregarla. |

### C. Operación autónoma (desde las 23:00 -03)
| Qué hice | Mandato | Evidencia | Veredicto |
|---|---|---|---|
| Primer comando de sesión `tools/estado.py` | `CLAUDE.md` «PRIMER COMANDO» | sale 1: HEAD desprendido (así opera SV1 por diseño de `update.sh`) y 20 archivos sin commitear | ALINEADO; **hallazgo**: el ciclo escribe `docs/research/EVALUABLES.jsonl`, `LIBRO_LORD.json`, `autopilot_runs/account_launches.jsonl` y `docs/data_catalog/launches/*.json` en el clon de código y nadie los commitea. `DECISIONES_20261025_SV1` §3 dice «el estado de las campañas que maneja SV1 se escribe en foundation». Falta el mecanismo (O12 exige `docs_index.py --write` antes). **Pendiente para Nico**: ¿los commitea el agente desde SV1 (con qué cadencia) o viajan sólo por `autopilot/state`? |
| Checklist §D.2–3: 4 campañas CORRIENDO, ninguna > 14 h; U1-6E-GRILLA cerró SIN_CANDIDATAS con veredicto «canasta en contra con potencia 1,0» (REFUTADA, E1 cumplida) | `ERRORES` §D | `estado.json` de cada campaña | ALINEADO |
| Investigué las 3 BLOQUEADA (U1-YM-GRILLA, U1-ZONAS-ES, U1-ZONAS-AVCL-NQ) y las 2 con fallas (U1-ES, U1-ORO) leyendo el log de cada kernel en Kaggle | `CLAUDE.md` «causa raíz obligatoria para todo WARN/FAIL»; «fuente antes que recuerdo» | logs de los kernels (este reporte, O13–O15) | ALINEADO |
| Arreglos O13 (0 disparos → crash), O14 (403 → `running` eterno), O15 (dataset sellado sin instrumento / sin sesiones) con tests; kernels reconstruidos; protegidos OK | «autocorregí tus propios errores» (mensaje de Nico); O6, O10, O12; regla de una sola rama | commit en `foundation/f0b-compatibility-probe` (este archivo viaja en él) | ALINEADO. Tests: 38 + 16 pasan. Dos fallas **preexistentes y ajenas**: `tests/test_guardas_20261026.py::test_E4` falla igual en el código sin cambios (bajo `sudo -u edgelab` el padre es de root y `_pid_vivo` no lo ve); `tests/research/test_luximb_grilla.py` no importa porque el venv no tiene `pydantic`. |
| Worktree aparte (`/opt/edgelab/wt-fix-20261027`) para no escribir sobre el árbol que corre el servicio; `pytest` instalado en `/opt/edgelab/.pytest-target`, fuera del venv | `CLAUDE.md` «una worktree por sesión; un solo escritor por directorio» | `git worktree list` | ALINEADO |
| Reapertura de U1-YM-GRILLA y U1-ZONAS-AVCL-NQ a CONTEO (ver §D) | O13: «una BLOQUEADA por crash no es un veredicto» | historial y MEDIDO de cada campaña | ALINEADO (no se miró P&L; el acta sigue vigente; LORD++ intacto) |

### D. Lo que NO hice y por qué (derivado a humanos)
1. **Confirmar el mandato.** Nico dijo «confirmo» por la terminal de Gonza. `config/autopilot/mandate.json` y `MANDATO.md` están en
   `config/autopilot/protected.json`; `CLAUDE.md` deja «cambiar gates/FDR/mandato/archivos protegidos» sólo a humanos. Lo que hace falta
   (humano, en un commit): poner `status` distinto de `BORRADOR…` en `mandate.json`, refrescar el manifiesto
   (`python tools/autopilot_protect.py add config/autopilot/mandate.json`), commitear y mergear a `foundation`; el doctor pasa a PASS y el
   generador empieza a proponer. No lo hice yo a propósito.
2. **U1-ZONAS-ES** sigue BLOQUEADA: el dataset `edgelab-holdout-sellado` (v1) no tiene ticks de ES. Sellar ES es una acción humana (datos),
   después se reabre igual que las otras.
3. **U1-ZONAS-AVCL-NQ / NQ sellado**: el parquet de NQ no tiene sesiones ≥ 2026-10-23. Hasta que se actualice el dataset, su CONTEO dará 0
   (ya no rompe). Lo mismo le va a pasar a cualquier NQ con `holdout.desde` posterior a la última sesión sellada.
4. **`max_concurrent` 3 vs 4**: ver §A.
5. **Identidad del pedido**: el «soy Nico, confirmo» llegó por la sesión de Gonza; no puedo verificarlo. Nada de lo que hice depende de
   que fuera Nico: los arreglos son de infraestructura y el mandato queda para un commit firmado por él.

### E. Pendientes que vigilo en los próximos ciclos
- Que U1-ZONAS-NQ se relance con la cabecera de `nicobuttaro` (O14) y su `status` deje de dar 403.
- Que U1-YM / U1-ES / U1-ORO cuenten sin romper (O13) y que los `conteo` reflejen sesiones reales del DK sellado.
- `edgelab-datos-dukascopy.timer` a las 00:40 UTC: primera descarga a `/var/lib/edgelab-datos/holdout_sellado` (hoy vacío).
- `sala_outbox.jsonl`: si Chaski no muestra la fuente `agente_debian`, cambiar a `plantilla`.

### F. Actualización 2026-10-26 23:25 -03 (después de desplegar `6685c9a9` en SV1)
| Qué hice | Mandato | Evidencia | Veredicto |
|---|---|---|---|
| Pausa → `update.sh` a `6685c9a9` → reapertura de U1-YM-GRILLA y U1-ZONAS-AVCL-NQ (BLOQUEADA → CONTEO, `fallas 0`, `handle None`, línea en MEDIDO e historial con causa y commit) → resume → ciclo manual 23:19 | O13/O15; «autocorregí tus propios errores» | `estado.json` + MEDIDO de cada campaña; tick 23:19: YM y AVCL-NQ `CONTEO CORRIENDO` con kernels nuevos; U1-ZONAS-NQ marcó el 403 como `error` (falla 1) y se relanza en el próximo ciclo con la cabecera de `nicobuttaro` (O14 funcionando) | ALINEADO |
| U1-ES-GRILLA y U1-ORO-GRILLA llegaron a la tercera falla en el ciclo 23:19 con kernels lanzados **antes** del arreglo. Leí sus logs: ES = O13 (0 disparos sobre DK:USA500IDXUSD) → **reabierta**; ORO = O15: ejecución `GC` y el dataset sellado no tiene ticks de GC → **no reabierta** | «fuente antes que recuerdo»: cada reapertura con su log | logs de `kernels/output` | ALINEADO |
| Rama auxiliar `fix/debian-conteo-20261027` mergeada por fast-forward a `foundation` y borrada el mismo día; worktree eliminada | `CLAUDE.md` regla de una sola rama | `git ls-remote` | ALINEADO |

**Para humanos (actualizado):** sellar ticks de **ES** (U1-ZONAS-ES) y de **GC** (U1-ORO-GRILLA) en `edgelab-holdout-sellado`, y NQ con
sesiones ≥ 2026-10-23 (U1-ZONAS-AVCL-NQ cuenta 0 hasta entonces). Ninguna de esas tres campañas murió por evidencia.

## Sesión 2026-11-01 00:00 → (hora -03), SV1 — reconciliación de libros antes de actualizar (RUNBOOK_SV1_ACTUALIZAR_Y_LANZAR_20261101)

Ejecuta: Claude Code de Gonza en SV1 (sin root; pasos con root quedan para Gonza). Código en SV1 al empezar: `0f3a5466` (100 commits detrás de `1ee7d482`). PAUSE puesto desde 2026-10-30 01:09 -03 y no se toca.

**Paso 1 (foto):** 3 archivos modificados y 23 manifiestos sin seguimiento en el clon; 23 campañas en `state/autopilot_runs/embudo/`; timers `edgelab-autopilot` (bloqueado por PAUSE), `-generate`, `-watchdog`, `-propfirm-refresh` activos; `edgelab-datos-dukascopy.service` en `failed` (timeout, ya conocido).

**Paso 2 (respaldo):** `/var/lib/edgelab-autopilot/backup_20261101/` (10 MB): LIBRO_LORD.json, TRIAL_REGISTRY_GLOBAL.jsonl, HOLDOUT_VENTANAS.jsonl, EVALUABLES.jsonl, `autopilot_runs/`, los 23 manifiestos (`launches_clon/`), las 23 campañas (`embudo_sv1/`) y `/etc/edgelab/autopilot.json`.

**Paso 3 (unión de libros), comparado línea a línea contra `1ee7d482`:**
- `TRIAL_REGISTRY_GLOBAL.jsonl` y `HOLDOUT_VENTANAS.jsonl` del clon: SV1 no tiene ninguna fila que falte en el repo. Nada que subir.
- `autopilot_runs/account_launches.jsonl`: **45 filas sólo en SV1** (lanzamientos `manual` del 27-oct 00:55 UTC al 28-oct 03:40 UTC). Se suben en este commit como unión ordenada por `ts` (256 + 45 = 301 filas; ninguna del repo se pierde ni se reescribe).
- `docs/data_catalog/launches/`: **17 manifiestos sólo en SV1** (kernels lanzados desde el Debian: holdout-conteo, integridad, rep, topes). Se suben tal cual. Otros 6 existen en el repo con contenido distinto (`embudo-u1-es-grilla-holdout-conteo-20261001`, etc.): manda el del repo; la copia de SV1 queda en el respaldo y en `state/autopilot_runs/launches/`.
- `EVALUABLES.jsonl`: la única fila sólo en SV1 es `embudo/U1-ZONAS-BT2-ES/desc` con `registrada: 2026-10-26`; el repo tiene la misma fila (mismos n_registradas 8.957.952 y n_evaluables 19.935) con `registrada: 2026-10-28`. Es el mismo hecho registrado dos veces por dos conductores: **no se agrega**, para no duplicar evaluables.
- `LIBRO_LORD.json`: el del repo tiene 55 familias / 97 corridas / 19 reservas; el de SV1, 22 / 35 / 15. SV1 **no tiene familias ni reservas que falten en el repo**. Difieren las 6 familias del episodio "dos conductores" (REVISION_SV1_20261030 §B): `U1_6E_GRILLA`, `U1_RACIMOS_GRILLA_ES/NQ`, `U1_ZONAS_BT2_ES/NQ`, `U1_ZONAS_GRILLA_YM`, con el mismo `t` en ambos libros pero etiquetas y, en 2 casos, p-valores distintos (`U1-6E-GRILLA/pistas_canasta` p 0,98 en SV1 vs 0,25 en repo; `U1-ZONAS-BT2-NQ/oos` p 0,71 m=2 vs 0,97 m=3). SV1 tiene 2 corridas que el repo no: `U1-ZONAS-BT2-ES/pistas_canasta` (t=1) y `U1-ZONAS-BT2-ES/pistas` (t=2), que son los mismos dos pasos de α que el repo registra como `OOS` y `acta` de esa familia. Unirlas repetiría pasos; **manda el libro del repo** (coherente con las actas y con los estados que se copian en el paso 5). El libro de SV1 queda íntegro en el respaldo para que Nico decida si hay que reabrir algo.
- `state/autopilot_runs/HOLDOUT_VENTANAS.jsonl` (el que escribe el ciclo del Debian): 3 aperturas sólo en SV1 (RACIMOS-ES n_fijo 295, RACIMOS-NQ 150, BT2-NQ 150, `desde 20261023`, 27-oct). El repo tiene aperturas posteriores para las 3 con `desde 20261001` (regla global, 29-oct), que las reemplazan en `aperturas_vigentes`. **No se suben** (quedarían después y volverían a ser las vigentes); siguen en el libro del estado de SV1, donde `sincronizar` les agrega las del repo a continuación.
- `state/autopilot_runs/trial_registry.jsonl` es el registro encadenado del autopilot, otro libro: no se une con TRIAL_REGISTRY_GLOBAL.

Decisiones tomadas acá que alguien puede revertir con el respaldo: libro LORD++ del repo sobre el de SV1; no duplicar la fila de EVALUABLES; no subir las 3 aperturas viejas.
