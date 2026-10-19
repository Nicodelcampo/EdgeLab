# Autopilot de EdgeLab: arquitectura (Debian, mejora recursiva acotada)

Estado: **implementado y probado con ejecutores simulados** (11 pruebas). No está desplegado, no se corrió contra Kaggle real y por defecto no lanza nada (`mode: propose`). Complementa —no reemplaza— el prototipo Research Ops (#117/#118: cola durable, presupuesto, recuperación, planificador knowledge-first); ver §7.

## 0. Mandato
Lo que el agente busca está en [`MANDATO.md`](../../MANDATO.md): edges **útiles para pasar challenges y combinables entre varias estrategias**; chicos, inestables o sin margen de diversificación no sirven. El mandato pesa la selección de candidatas (`utility_class`), exige un nivel (A/B/C/D) en cada informe y está protegido por hash (`config/autopilot/mandate.json`, `edgelab/autopilot/mandate.py`, `MANDATO.md`).

## 1. Objetivo y qué significa «mejorar las chances de edge»
El sistema debe (a) crear y seleccionar corridas, (b) lanzarlas y analizarlas, (c) aprender a optimizarlas y (d) aumentar de forma sostenida la probabilidad de hallar edge real. Con muchas pruebas la multiplicidad crece: **no se mejora bajando el listón sino gastando mejor un presupuesto de alfa fijo**. Por eso hay tres mecanismos separados:
1. **Control en línea de falsos descubrimientos (`fdr.py`, alpha-investing):** cada campaña apuesta un nivel familiar `a = f·W/(1+W)`; un hallazgo recarga la riqueza `W`, un fracaso la gasta. Sin réplicas la riqueza decae y el sistema deja de lanzar campañas nuevas. Dentro de cada campaña rige Holm sobre las pruebas planeadas.
2. **Selección por rendimiento histórico (`selector.py`):** Thompson sampling Beta-Bernoulli por (familia, grupo), penalizado por costo, con piso de exploración y sin repetir `spec_hash`. Prioriza donde hubo hallazgos pre-registrados; no cambia el costo de multiplicidad de la corrida elegida.
3. **Optimización de cómputo (`optimizer.py`):** menos tiempo por prueba = más pruebas dentro del mismo presupuesto de cómputo, no de alfa.

## 2. Ciclo (`daemon.Autopilot.tick`)
kill switch → manifiesto de archivos protegidos → cerrar corridas terminadas (traer resultado, **Holm propio al nivel apostado**, liquidar alfa, registrar en Edge Brain y libro) → si hay cupo y presupuesto: ordenar candidatas, pasar **todas** las guardas, contar en el registro global **antes** de lanzar, apostar alfa y lanzar vía `tools/kaggle_launch.py` (preflight en vivo + manifiesto de versiones/bytes verificado dentro del kernel).

## 3. Guardas duras (`guard.py`; un `RunSpec` no puede desactivarlas)
- Holdout: ningún `needs` puede llegar a 2026-10-01.
- Pre-registro y script **committeados y sin cambios locales** antes de lanzar (el código lanzado queda atado a un commit).
- `internet` solo con lista blanca por script.
- Archivos protegidos por hash (`config/autopilot/protected.json`): `edgelab_data.py`, las guardas y el FDR del propio autopilot, `kaggle_launch.py`, pre-registros ya usados. Si cambian, el ciclo se **detiene** hasta que un humano refresque el manifiesto (`tools/autopilot_protect.py`): el sistema no puede aflojar sus propias reglas.
- Presupuestos: `max_concurrent`, `max_per_day`, riqueza de alfa. Modo `execute` solo si un humano lo escribe en la configuración.
- Solo análisis: no hay P&L, promoción ni operación de mercado en ningún camino.

## 4. Mejora recursiva, con límites
| Qué mejora | Cómo se acepta | Quién aprueba |
|---|---|---|
| Scripts de corrida (más rápidos) | `optimizer.compare`: salida canónica idéntica en todas las repeticiones **y** ganancia ≥ 1,2×; si no, se rechaza y se conserva la línea base | Cambio de código por PR; CI + revisión humana |
| Configuración de corrida (workers, nperm, equipo) | `optimizer.advise` propone sobre telemetría del libro; no se aplica sola | Humano |
| Selección de hipótesis | Se actualiza sola con el historial (§1.2); semilla y razón quedan registradas | — (acotada por FDR) |
| Reglas de decisión, gates, holdout, FDR | **No son mutables por el sistema** | Solo humano |

Los hallazgos del sistema son «exploratorios»: pasar a un candidato requiere réplica pre-registrada (fuera del autopilot).

## 5. Aprendizaje
`brain.py` escribe cada corrida analizada como episodio append-only en el hipocampo (éxitos y fracasos por igual; lecciones solo PROPOSED/LOW). El libro SQLite (`ledger.py`) guarda telemetría (segundos, fallos, spec) para `advise`.

## 6. Despliegue en Debian (`deploy/debian/`)
`install.sh` crea el usuario `edgelab`, el venv y el repo; `edgelab-autopilot.timer` dispara un ciclo `oneshot` cada 10 min (`systemd` reinicia solo ante caídas del host y cada ciclo es idempotente). Servicio endurecido (`ProtectSystem=strict`, sin capacidades, 2 GB de memoria). Credenciales de Kaggle solo en `/etc/edgelab/autopilot.env` (0600), nunca en el repo. Parada de emergencia: `touch /var/lib/edgelab-autopilot/PAUSE`.

## 7. Relación con Research Ops (#117/#118) y pendientes
- Research Ops ya aporta: cola SQLite con presupuesto reservado, recibos exclusivos, recuperación/snapshots, planificador knowledge-first, importer de cierres. Este módulo aporta: guardas de holdout/pre-registro/protegidos, FDR en línea, selector, aceptación de optimizaciones por salida idéntica y puente al Brain. **Unirlos** (un solo ledger/cola, usando `Store` para presupuesto y recuperación) es el siguiente paso; hoy son independientes porque viven en ramas con bases distintas.
- **Falta:** generador de candidatas (hoy `candidates.json` lo escribe un humano o un agente con revisión); pre-registro automático de las candidatas generadas (debe ser redactado y committeado antes de entrar a la lista); adaptadores de resultado para más familias; telemetría de recursos del kernel; despliegue real y prueba de punta a punta contra Kaggle con una corrida barata.
- **Límite honesto:** el FDR en línea asume pruebas aproximadamente independientes entre campañas; si hay dependencia fuerte (mismos datos reutilizados) el control es aproximado y conviene reservar una réplica en datos nuevos antes de creer un hallazgo.
