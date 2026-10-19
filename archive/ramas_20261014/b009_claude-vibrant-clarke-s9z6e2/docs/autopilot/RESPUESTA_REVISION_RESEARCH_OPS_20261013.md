# Respuesta a la revisión de Research Ops (PR117/118) sobre el autopilot

Fuente: `docs/research/ops/EXTERNAL_AGENT_ADVANCES_RECONCILIATION.md` y `DEBIAN_AGENT_HANDOFF.md` (rama `feat/research-ops-supervisor-mvp`). Son observaciones sobre un snapshot anterior; esto es lo que se corrigió en esta rama, con tests en `tests/test_autopilot.py`.

| # | Hallazgo | Estado |
|---|---|---|
| 1 | `decide` aceptaba p negativo; p NaN entraba en `n_evaluable` | **Corregido.** `valid_p` (finito, [0,1]); los inválidos quedan en `invalid_p_tests`, no cuentan y el denominador planeado se mantiene (también en `holm_rejections`). |
| 2 | `AlphaInvesting`: dos objetos con estado obsoleto gastan de más y pierden reservas; guardado no atómico | **Corregido.** Cada operación toma `flock`, recarga el estado vigente y escribe con `os.replace`. Test con dos instancias obsoletas. |
| 3 | `launch` antes de `ledger.add`; una caída deja un envío sin registro | **Corregido.** Escribe-antes-de-enviar (`SEND_UNCERTAIN`); un envío incierto no se reenvía ni libera la apuesta; solo un rechazo explícito (`LaunchRejected`) borra la intención y devuelve la apuesta. |
| 3b | `settle` antes de `finish`; ERROR no resolvía la reserva | **Corregido.** Primero el libro, luego la riqueza; un ERROR devuelve la apuesta (`release`, sin gasto ni recarga); `_reconcile` liquida/devuelve apuestas huérfanas tras una caída. |
| 4 | Guarda de env por substring | **Corregido.** Si el valor es JSON debe coincidir estructuralmente con un bloque JSON del pre-registro committeado (claves y valores); si no, texto. Los 8 candidatos vigentes pasan. |
| 5 | `propose` no es de solo lectura (cierra y escribe) | **Documentado, no cambiado:** el ciclo siempre cierra corridas; no usarlo contra estado productivo sin backup. `--status` instancia el libro. |
| 6 | Un solo controlador por estado | **Corregido.** `.lock` exclusivo no bloqueante por directorio de estado (`locked_by_other_controller`). |
| 7 | `git pull --ff-only` en cada ciclo | **Corregido.** Quitado de la unit; el cambio de código es explícito: `deploy/debian/update.sh <sha>`. |
| 8 | `git add -A` en `sync_state.sh` | **Corregido.** Lista blanca de archivos de estado. |
| 0 | Manifiesto de protegidos | **Refrescado por el usuario (autorización explícita 2026-10-13)** para `guard.py` y `fdr.py` tras revisar este diff. |
| 9 | Python 3.12 vs Debian 3.11 | **Abierto.** El autopilot corre en 3.10+; PR117 pide 3.12. Venv separado por componente, aprobado por el administrador. |
| 10 | Doctor/endpoint no prueba acceso privado | **Abierto.** Verificar con una operación mínima autorizada en el host real. |

## Lo que sigue abierto (y no se aparenta resolver)
- **Presupuesto global de cuenta — parcialmente resuelto.** `tools/kaggle_launch.py` (autopilot, humano o cualquier agente que lo use) registra cada lanzamiento en `docs/research/autopilot_runs/account_launches.jsonl` y el autopilot aplica `account_max_per_day` (12) sobre TODO lo registrado (`tick_account_cap`). No ve lanzamientos por la UI/API directa de Kaggle: es un tope de prudencia, no cuota real. Ejemplo real: el 2026-10-13 un tick con `--root .` (estado nuevo, vacío) lanzó una corrida duplicada de `slot-1`; el lock por directorio no lo habría evitado. Falta un registro común de lanzamientos por cuenta (interfaz con `DispatchIntent` de PR117).
- **Alpha-investing no certifica FDR global** con pruebas dependientes/superpuestas (las campañas comparten muestras). Se usa como presupuesto de prioridad, no como garantía. OU-2 mostró un caso: se contó como acierto una re-medición de la misma muestra; ya corregido con `correction_of`.
- **Integración con `DispatchIntent`, adquisición de agregados y semántica de PR117/118**: una responsabilidad por capa, un solo escritor; no se construyó un segundo daemon ni se mergearon ramas.
- Sin prueba en Debian real (LEEME).
