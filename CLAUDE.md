# EdgeLab — instrucciones permanentes de sesión

> Este archivo se carga en cada sesión de Claude Code. El documento canónico
> versionado es **`docs/NORTH_STAR.md`** — sha256 del cuerpo anterior al
> marcador `SHA256-BODY-ABOVE`: `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
> (no es el hash del archivo completo; el archivo se autocita a su propio pie,
> ver `tests/test_north_star_hash.py`). Si hay conflicto, manda ese doc. Punto
> de entrada operativo del día: `docs/ESTADO_2026-08-10_EMPEZAR_ACA.md`.

## NORTH STAR — referente rector (gobierna todo)

**EL OBJETIVO FINAL DEL PROYECTO ES ENCONTRAR EDGES VÁLIDOS Y APLICABLES EN EL
MERCADO A TRAVÉS DE ALGORITMOS QUE, A TRAVÉS DE LA RENTABILIDAD, PERMITAN
OBTENER GANANCIAS EN LAS CUENTAS DE TRADING DONDE SE APLICAN.**

Jerarquía de objetivos (para priorizar cualquier tarea o trade-off):
1. Expectativa económica NETA (después de comisiones, spread y slippage).
2. Validez fuera de muestra (holdout sellado, sin data snooping).
3. Robustez estadística (MCPT, PBO, DSR/SPA, walk-forward, sensibilidad).
4. Ejecutabilidad real (feed en vivo, fills realistas, latencia, reglas
   completas de entrada/salida/sizing/kill switch).
5. Control de riesgo (drawdown tolerable, despliegue con riesgo mínimo).
6. Paridad, determinismo, trazabilidad y visor COMO MEDIOS para 1–5.

Recordatorios:
- Un indicador con paridad exacta no es un edge. Una zona bien almacenada no
  es un edge. Un backtest positivo no es un edge si no sobrevive selección,
  costos, OOS y ejecución.
- Target-free aplica a la construcción técnica de indicadores; el research de
  estrategias SÍ usa retornos y P&L, pero bajo pre-registro, presupuesto de
  investigación, corrección por múltiples pruebas y holdout sellado.
- El progreso NO se mide por infraestructura terminada sino por cuánto reduce
  la distancia hacia un edge neto, robusto y operable.
- No prometer rentabilidad futura: el objetivo metodológico es maximizar la
  probabilidad de detectar edges reales y rechazar falsos antes de arriesgar
  capital.

## Estado vigente (2026-08-15)

> Punto de entrada operativo: `docs/research/HANDOFF_AUDITORIA_2026-08-14.md`
> + `PENDIENTE.md` (P-01…P-27) + `docs/research/PRECHECK_HOLDOUT_2026-08-15.md`.
> Rama viva: `research/bigtrap2-local-displacement-null`.

- H1 está muerta; el veredicto fue sobre **6E**, no se transporta a otros instrumentos.
- BigTrap2 como función de soporte/resistencia: refutado (~96% de ruptura, invariante a los 12 parámetros del indicador).
- **BigTrap2 como imán de zona: CERRADO (2026-08-13)** — estado `BIGTRAP2_MAGNET_LINE_CLOSED`,
  acta en `docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md`. La hipótesis
  de atracción/revisita que este archivo declaraba "provisional con evidencia fuerte"
  **no sobrevivió**. Cadena de refutación sobre 6E, 201 sesiones, 15.947 zonas:
  - **F2.7**: la carrera contra el espejo es real (Δ≈+0,048, IC [+0,031, +0,066]).
    Real y espejo equidistantes del close, así que "gana porque está más cerca" queda descartado.
  - **F2.8**: **no es imán**. El efecto no muere en `d≥6` (Δ≈+0,077) y un control
    *sin zona* con la misma geometría da casi lo mismo: el contraste cruza cero.
  - **F2.9**: el kernel no es el mejor sello. Vela extrema genérica `S1` = +0,038;
    creadora BigTrap2 `K0` = +0,021, y `K0 ≈ N0` (no-creadora emparejada).
    Residual de zona +0,026 con MDE 0,034 → no se promueve.
  - **F2.10**: no hay ventana temporal exclusiva; el contraste `t+1` cruza cero.
  - Lo que **sí** queda: una vela extrema marca una carrera asimétrica. No es de zona,
    no es exclusiva de BigTrap2, no es un sistema. Es un sello barato de contexto.
  - Cerrados por este acta: imán de zona, cola lejana / 17 frames / Z2, ventana
    `t+1`/`t+2` como producto, cruce BigTrap2 × aVol, PIT / Kaplan-Meier / Cox sobre
    este objeto, y Kaggle de ticks reales (`NO_UPLOAD`).
- **Segunda familia viva: `aVolClusterPOI`** — paridad medida (6E: 72/72 creaciones,
  Δscore = 0 exacto; ES 09-26: 100% pre-11-jun). Sin nulo propio todavía: es el
  siguiente candidato si hay campaña nueva, **sola y target-free**, sin cruce.
- **Paridad de kernels cerrada punta a punta** (P-12/P-13/P-16): BigTrap2 junio
  3.628/3.638 EXACT (99,73%), abril+mayo 171/171 EXACT. Causa raíz del silencio de
  TRAPs: `sesionNoConfiable` nunca reseteaba porque el bloque de frontera quedaba
  detrás del `return` del camino de tiempo (fix `f77a3be`).
- F4 constitucional (información condicional) NO ejecutada — bloqueada por el STOP de abajo.
- Holdout intacto en análisis. Frente de datos/legal, al 2026-08-15 (P-07, P-18, P-25):
  - El leak del corte UTC está **medido y cerrado en código**: la sesión CME del 1-jul
    abre 17:00 CT del 30-jun, así que un corte en `2026-07-01T00:00Z` dejaba pasar
    7.200 s de holdout (871 filas en el parquet ancla; 101.364 ticks sobre los 11
    archivos en cuarentena).
  - **El re-corte físico SÍ se ejecutó** (2026-08-15, máquina local gobernada):
    `[PASS] 11/11`, 48.510.023 filas conservadas, 62.827.237 descartadas. Las fuentes
    se verificaron **intactas después de escribir** (sha256 11/11) — el árbol de origen
    sigue siendo inmutable. `research-v2` existe: 56 contratos, 1.015.587.419 ticks,
    15,895 GiB. Acta: `docs/research/RECUT_EXECUTION_2026-08-15.md`.
  - **`research-v2` NO es publicable.** Sigue bloqueado por licencia (`ABSTAIN_LICENSE`)
    y ahora por capacidad con tres compuertas en rojo. Y ojo con el orden:
    **aprobar la licencia no desbloquea nada por sí solo** — `VERDICT_PRECEDENCE` es un
    `if/elif` y `ABSTAIN_LICENSE` tapaba otros dos gates que también fallan.
  - La V1 del dataset de Kaggle sigue con ticks crudos y holdout físicamente presente,
    subidos antes de cerrar M0 (P-18, abierta y bloqueante).
  - Dos hallazgos que tocan research, no sólo publicación (P-28): `ts_local_ns` es un
    duplicado exacto de `ts_utc_ns`, y **`sequence` no es secuencia del exchange** sino
    índice de fila del origen — 22 igualdades de sha256 sobre 11/11 archivos. Cualquier
    análisis de microestructura que asuma secuenciación de mercado **no está soportado
    por estos datos**.
- Incidente de procedencia Git del 2026-08-10 (`docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md`) **cerrado** — ver `docs/incidents/RESOLUCION_INCIDENTE_PROCEDENCIA_2026-08-10.md`. Las reglas 15–18 de abajo son la práctica permanente que deja como saldo.
- **Dos familias nuevas registradas** (observación de Nico, no ejecutadas): `docs/research/H-COND-1_LUX-IMB_PROTOCOLO.md` (indicador LuxAlgo Imbalance Detector sobre ES; **bloqueada** — faltan parámetros reales del chart exportados, ledger as-of, auditoría antirepintado y paridad Pine→NT8. **Corrección de fuente ya mergeada** [2026-08-15, rama `docs/lux-imb-source-correction`]: las dos premisas viejas —que las zonas mitigadas desaparecían solas y que existía un input `Mitigation Method`— están **retiradas**; en el indicador que usa Nico las zonas NO desaparecen por mitigación. Los parámetros a exportar son: selector `Imbalance` con **OG y VI activos y FVG apagado**, `Min Width`, `Extend`, timeframe e instrumento/contrato con plantilla de sesión. No volver a pedir un método de mitigación. Ver `docs/research/LUX_IMBALANCE_DETECTOR_SOURCE_VERIFICATION.md`) y `docs/research/H-SWEEP-1_YM_PRERANGE.md` (ventana 08:12–09:12 ET sobre YM; 5-de-6 no rechaza ni una moneda — el nulo correcto no es 50% sino 54–76% vía reflexión browniana, y la versión operable compite contra la ruina del jugador `s/(R+s)`. El constructor de sesión parametrizable que faltaba **ya existe y está testeado** (`edgelab/sessions.py::build_session_matrices`, generalizado 2026-08-10) — **sigue bloqueada**, pero ahora por lo que el gate §15 pide de verdad: resolver huso horario [EST/EDT, la etiqueta "Tokyo" del chart no está explicada] y construir calendario de research propio para YM, que todavía no existe. **OJO**: hay una versión más avanzada sin mergear en la rama remota `research/ym-prerange-session-window` — `minute_window_matrices` con calendario explícito obligatorio y soporte de cruce de medianoche — antes de tocar `edgelab/sessions.py` de nuevo, revisar si esa rama ya resuelve esto).
- **Gate G2 corregido acá** (enmienda `G2-A1`, commit `62ac28c`, con OK explícito de Nico en sus 3 preguntas abiertas — ver `docs/incidents/AMENDMENT_G2-A1_2026-08-10.md`): el MCPT original medía concentración temporal pese a lo que decía su contrato, y estructuralmente favorecía al edge que decae y penalizaba al estable (contradecía a G1). Ahora `temporal_concentration_test` quedó como diagnóstico, `PrimaryCI` (bootstrap estacionario, `lower>0`, clusterizado por sesión) es la inferencia primaria, y `AUTHORIZED_DSR_METHOD_SHA256S` ya no está vacío. Sigue sin ejercitarse contra una campaña real. **OJO — descubierto 2026-08-10 22:3x vía `git fetch`**: existe una línea de trabajo paralela y más avanzada, sin mergear, en las ramas remotas `fix/g2-a1-statistical-semantics` + `fix/g2-a1-calibration-hardening` (autor `Nicodelcampo`, validada contra CI, fusiona el `g2.py` de este repo pero reescribe `g2_decision.py`/`promotion.py` con calendario de sesiones elegibles obligatorio, `MIN_DSR_SESSIONS` y dos métodos DSR versionados V1/V2. **No mergear sin decisión explícita de Nico** — son cambios de semántica de validación, regla permanente de este archivo.

## Decisión de prioridad vigente (sellada por Nico)

**F9 (nuevos indicadores) PAUSADA** hasta ejecutar al menos una campaña formal
de descubrimiento sobre los 5 indicadores existentes. Agregar indicadores hoy
amplía el espacio de búsqueda y el data snooping sin evidencia de que haga falta.

## Rituales permanentes

- Todo **checkpoint de turno termina con "Aporte al referente: …"** (1–2 líneas:
  qué distancia se redujo hacia un edge neto y operable). Obligatorio.
- Todo **manifiesto de campaña cita el hash de `docs/NORTH_STAR.md`**.
- Toda **plantilla generadora** (scaffold, spec LLM, reportes) incluye los
  campos obligatorios **"justificación económica"** y **"cómo podría refutarse"**.
- Toda **población** declara, en el mismo documento que la congela, el
  event-space del que fue extraída (ver regla de población abajo).
- **Registro MEDIDO/NO MEDIDO actualizado en el mismo commit** que cualquier
  resultado nuevo — no en un commit aparte, no "después".

## Firewall del holdout (2026-07-01 → 2026-12-31)

- **Prohibido** usar el holdout para elegir dirección, entradas/salidas,
  thresholds, bar_spec, costos o candidatos.
- **Permitido** solo para validaciones target-free (paridad, determinismo,
  geometría, integridad, visor). Una sola apertura por candidato, por protocolo.

## Reglas permanentes

- **Referente rector primero**: toda tarea se justifica por su aporte al edge
  neto, robusto y operable.
- No tocar F0–F2 ni el schema canónico; no modificar parquets reales; no editar
  particiones publicadas (son inmutables).
- **Causa raíz obligatoria** para todo WARN/FAIL; prohibido ampliar tolerancias
  o relajar gates después de ver resultados; cambios de semántica de validación
  se **consultan con Nico**.
- **Ninguna población se congela sin enumerar antes, por escrito, el espacio de
  eventos y estados del que se la extrae**, con su justificación y su condición
  de refutación. Una población elegida sin alternativas escritas no es una
  elección: es una herencia. Extiende el campo obligatorio «cómo podría
  refutarse» de la hipótesis **a la población sobre la que se define**.
  El 2026-08-10 se descubrió que TODO el corpus sobre BigTrap2 medía una sola
  familia de entradas —el toque— porque una premisa dentro de un condicional de
  la enmienda del 2026-08-04 pasó a axioma, y el marco alternativo (zona como
  estado, `features.py`) llevaba trece días construido sin que research lo
  usara. Ningún gate podía cazarlo: **lo único que nadie auditó es lo que nadie
  escribió como decisión.** Ver
  `docs/SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md`. En la
  práctica, esto exige enumerar por separado: creación, aproximación, primer
  toque, toque n-ésimo, invalidación, expiración, confluencia y estado
  continuo — antes de congelar cuál de esas familias se mide.
- **Separar evento de estado.** Un evento (un toque, una creación) da una
  población de N observaciones; un estado (zonas activas, distancia al precio)
  vale en cada barra y suele tener mucha más potencia estadística. Elegir uno
  sin considerar el otro es la misma clase de herencia sin decisión que la
  regla anterior prohíbe.
- **La cadena de un candidato es geometría/lifecycle → información → P&L bruto
  → edge neto/replicado**, en ese orden. No saltar directo a P&L porque el
  lifecycle target-free "se ve bien".
- **No transportar costos de ejecución entre instrumentos.** La fricción de
  6E no es la de ES/NQ/YM; cada instrumento estima la suya.
- **`ticks_per_row` y `bar_spec` son ejes distintos** — no confundir un
  parámetro del indicador con la resolución de barra sobre la que corre.
- **Fuente antes que recuerdo.** Toda afirmación que sostenga una decisión de
  diseño se verifica contra código, artefacto o fuente primaria en el momento.
  Recordar una conclusión de un turno anterior no es verificarla.
- **Integridad precede a interpretación.** Drift de versiones, nulos
  defectuosos, calendarios no habilitados o artefactos no publicados bloquean
  la promoción de un resultado. Un resultado así se conserva como provisional;
  nunca se eleva por urgencia.
- **Toda muerte tiene alcance preciso.** Una hipótesis muerta invalida
  exactamente su mecanismo, población, estimand y ejecución declarados.
  Ampliar la muerte a toda una familia requiere evidencia adicional propia;
  reducirla para rescatarla, también.
- **Cada familia de indicador/zona se registra antes de estudiarse**: declara
  indicador, subfamilias habilitadas, parámetros congelados y ledger propio.
  No se transportan resultados, poblaciones, costos, oráculos ni presupuesto
  de multiplicidad entre familias (BigTrap2, LUX-IMB, YM-PRERANGE y las que
  sigan son independientes). **Si el render de un indicador elimina zonas al
  ser mitigadas/atravesadas, el estado dibujado en pantalla NO es evidencia
  admisible** — lo que se ve reaccionar puede ser el sesgo de supervivencia de
  la regla de dibujo, no el mercado. Exige censo as-of que incluya las zonas
  muertas y una auditoría antirepintado antes de interpretar cualquier
  observación visual sobre ese indicador.
- **Todo nulo publica su MDE, y todo efecto se mide en dos canales**: el
  direccional Y el no direccional, más la distribución completa. Un resultado
  nulo sin MDE mínimo detectable no distingue ausencia de efecto de falta de
  poder; un efecto real bidireccional puede promediar exactamente cero si sólo
  se mira el canal direccional.
- No mirar el holdout para diseñar o elegir. No seleccionar por P&L máximo
  aislado. No ocultar resultados negativos. No ejecutar fills imposibles.
- Tests con fixtures chicos y deterministas; sin dependencias pesadas nuevas
  (duckdb/polars/pyarrow ya están); sin CUDA.
- Commits chicos por fase, push al cierre. Si git pide credenciales: frenar y
  pedir a Nico. Al pushear, usar el token que Nico provea sin persistirlo en
  `.git/config` y redactarlo de los logs.
- **Verificar todo commit con `git show --stat` inmediatamente después de
  crearlo** — `git status` antes de commitear no basta como evidencia de qué
  quedó adentro, sobre todo si un `git add`/`git mv` previo falló en la misma
  sesión de comandos sin dejar rastro obvio. Ver
  `docs/incidents/RESOLUCION_INCIDENTE_PROCEDENCIA_2026-08-10.md`.
- **Una worktree por sesión/campaña que escribe código; un solo escritor por
  directorio de trabajo.** Dos procesos con acceso de escritura al mismo árbol
  (aunque uno sea una tarea delegada) es el escenario que produjo el incidente
  de procedencia del 2026-08-10.
- **Procedencia dirty-aware en todo artefacto de medición**: además de
  `code_commit`, publicar si el árbol estaba limpio al momento de correr
  (`head_start`/`head_end`, dirty/clean). Un `code_commit` sobre árbol dirty no
  garantiza que ese commit contenga el código que realmente corrió.
- **No confundir un barrido target-free llamado "F4" con la F4 constitucional**
  (información condicional, bajo STOP). `F4_PARAMETROS_RESTANTES` del
  2026-08-10 es un barrido de parámetros del indicador, target-free — un
  nombre de conveniencia, no la fase F4 del plan.
- **`/data/` es dato local (gitignorado); `edgelab/data/` es código fuente
  trackeado.** El patrón de `.gitignore` está anclado a la raíz para no
  confundir los dos.

## Interrupción por oráculos (prioridad máxima permanente)

Si aparecen CSVs en `oracles\`: interrumpir en punto seguro → validar
versión/hash del `.cs` y ventana/params → correr gates → **causa raíz de todo
WARN/FAIL** → promover particiones → regenerar visor → registrar cobertura →
retomar la tarea anterior.

## STOP antes de correr búsqueda sobre retornos

Antes de ejecutar CUALQUIER búsqueda sobre P&L/retornos: presentar a Nico el
**manifiesto de campaña + número efectivo de hipótesis + riesgos + datos
faltantes**, y esperar aprobación. No correr la búsqueda sin ese OK. Target-free
publica el landscape completo (todas las celdas, semillas y nulos) — nunca
selecciona por P&L máximo aislado.

## Punteros

- `docs/NORTH_STAR.md` — referente canónico (fuente de verdad).
- `docs/research/HANDOFF_AUDITORIA_2026-08-14.md` — **punto de entrada operativo vigente**.
- `PENDIENTE.md` — board de decisiones abiertas, P-01…P-27. Se lee siempre junto al handoff.
- `docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md` — acta del cierre de
  BigTrap2 como imán, y las herramientas que quedan reutilizables.
- `docs/research/PRECHECK_HOLDOUT_2026-08-15.md` — estado del re-corte del holdout.
- `docs/ESTADO_2026-08-10_EMPEZAR_ACA.md` — histórico; **superado** por el handoff.
- `docs/edge_validation_contract.md` — gates G0–G5 de "edge válido y aplicable".
- `docs/kernel_contract.md` — construcción técnica target-free de kernels.
- `docs/nt8_indicator_parity_contract.md` — protocolo de paridad NT8↔Python.
- `docs/nt8_bridge.md` — store, gate P3, campañas, visor, API de features.
- `docs/incidents/` — incidentes de procedencia/integridad, abiertos y cerrados.
- `docs/audits/CANAL_AUDITOR.md` — **índice del canal Opus 5 ↔ Auditor**: reglas,
  entradas 001-005 con sus URLs de Notion y el estado de la cadena que gobierna
  el capítulo 6. El canal vivía sólo en Notion, contra su propia regla 1.

## Entorno

`.venv` (Python 3.12) desde `requirements/core-bridge-dev.lock`. Suite:
`.venv\Scripts\python -m pytest tests -m "not vectorbt" -q`.

**Ramas (reordenado 2026-08-15).** Branch de trabajo:
`research/bigtrap2-local-displacement-null`.

`foundation/f0b-compatibility-probe` queda como **rama de integración, mantenida por
fast-forward** sobre la rama de trabajo — no se le commitea directo, se la avanza.
`main` = baseline original, no mergear.

> La frase «Branch de trabajo:» de arriba **la parsea `tools/estado.py`**
> (`rama_declarada()`, regex `Branch de trabajo:\s*\n?` + backticks). Si se
> reformula esa línea, `estado.py` devuelve `None` y el primer comando de cada
> sesión miente en silencio. Cambiar las dos cosas juntas o ninguna.

Hasta el 2026-08-15 este archivo declaraba `foundation` como branch de trabajo
mientras el trabajo real vivía cinco días adelante en otra rama, y el propio
`CLAUDE.md` seguía afirmando viva una hipótesis que `F2.8` había cerrado. Es la
misma familia de falla que `docs/AVISO_DIVERGENCIA_DE_RAMAS_2026-08-06.md`
describe: **cuando el documento rector y el árbol discrepan, cada lado lee el suyo
y las dos lecturas son internamente coherentes.**

## PRIMER COMANDO DE CADA SESIÓN

```
.venv\Scripts\python tools\estado.py
```

Dice en qué rama estás, si coincide con la declarada arriba, si estás
sincronizado con el remoto, **y si otra rama tiene trabajo que la tuya no
tiene**. Sale 1 si algo requiere atención. Correlo ANTES de medir cualquier cosa.

**Después, y antes de research**: verificar raíz (`git rev-parse
--show-toplevel`), HEAD, worktree (`git worktree list`) y árbol limpio — el
mismo chequeo que el incidente de procedencia del 2026-08-10 dejó como
protocolo forense, ahora preventivo.

**Regla de una sola rama.** Todo el trabajo va a `foundation/f0b-compatibility-probe`.
Si hace falta una rama auxiliar, se mergea de vuelta **el mismo día**. El
2026-08-05 dos máquinas midieron cosas distintas creyendo mirar lo mismo: 70
commits vivían en una rama que este archivo no mencionaba, y cada lado leyó la
suya. Las dos lecturas eran internamente coherentes. Ver `docs/AVISO_DIVERGENCIA_DE_RAMAS_2026-08-06.md`.
El 2026-08-10 se repitió la misma familia de falla en otra forma: no ramas
distintas, sino **procesos concurrentes sobre el mismo árbol** — ver
`docs/incidents/RESOLUCION_INCIDENTE_PROCEDENCIA_2026-08-10.md`.

Excepciones que divergen a propósito y `estado.py` no marca: `main`, `backup/*`,
`preserve/*`.

**Dos clones en esta máquina** — `E:\EdgeLab` y `E:\ProyectosQuant\EdgeLab-sync-desktop`.
Los dos apuntan al mismo remoto. Correr `estado.py` en el que vayas a usar.
