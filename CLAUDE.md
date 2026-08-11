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

## Estado vigente (2026-08-10)

- H1 está muerta; el veredicto fue sobre **6E**, no se transporta a otros instrumentos.
- BigTrap2 como función de soporte/resistencia: refutado (~96% de ruptura, invariante a los 12 parámetros del indicador).
- BigTrap2 como marcador de atracción/revisita: hipótesis provisional con evidencia fuerte y convergente (6E `time:1`, 6E `tick:25`, ES `time:1` — las tres ~47pp de brecha pareada, 201/201 sesiones), pero **no es edge todavía**.
- F4 constitucional (información condicional) NO ejecutada — bloqueada por el STOP de abajo.
- Holdout intacto.
- Incidente de procedencia Git del 2026-08-10 (`docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md`) **cerrado** — ver `docs/incidents/RESOLUCION_INCIDENTE_PROCEDENCIA_2026-08-10.md`. Las reglas 15–18 de abajo son la práctica permanente que deja como saldo.
- **Dos familias nuevas registradas** (observación de Nico, no ejecutadas): `docs/research/H-COND-1_LUX-IMB_PROTOCOLO.md` (indicador LuxAlgo Imbalance Detector sobre ES; **bloqueada** — faltan parámetros reales del chart exportados, ledger as-of, auditoría antirepintado y paridad Pine→NT8. **OJO**: la versión de este archivo en este repo todavía describe el bloqueo como "el render borra zonas mitigadas" — esa premisa fue **retractada por Nico** en la rama remota sin mergear `docs/lux-imb-source-correction` [2026-08-11]: en el indicador que él usa las zonas NO desaparecen por mitigación y no existe un input "Mitigation Method"; no confiar en la razón vieja hasta mergear esa corrección) y `docs/research/H-SWEEP-1_YM_PRERANGE.md` (ventana 08:12–09:12 ET sobre YM; 5-de-6 no rechaza ni una moneda — el nulo correcto no es 50% sino 54–76% vía reflexión browniana, y la versión operable compite contra la ruina del jugador `s/(R+s)`. El constructor de sesión parametrizable que faltaba **ya existe y está testeado** (`edgelab/sessions.py::build_session_matrices`, generalizado 2026-08-10) — **sigue bloqueada**, pero ahora por lo que el gate §15 pide de verdad: resolver huso horario [EST/EDT, la etiqueta "Tokyo" del chart no está explicada] y construir calendario de research propio para YM, que todavía no existe. **OJO**: hay una versión más avanzada sin mergear en la rama remota `research/ym-prerange-session-window` — `minute_window_matrices` con calendario explícito obligatorio y soporte de cruce de medianoche — antes de tocar `edgelab/sessions.py` de nuevo, revisar si esa rama ya resuelve esto).
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
- `docs/ESTADO_2026-08-10_EMPEZAR_ACA.md` — punto de entrada operativo vigente.
- `docs/edge_validation_contract.md` — gates G0–G5 de "edge válido y aplicable".
- `docs/kernel_contract.md` — construcción técnica target-free de kernels.
- `docs/nt8_indicator_parity_contract.md` — protocolo de paridad NT8↔Python.
- `docs/nt8_bridge.md` — store, gate P3, campañas, visor, API de features.
- `docs/incidents/` — incidentes de procedencia/integridad, abiertos y cerrados.

## Entorno

`.venv` (Python 3.12) desde `requirements/core-bridge-dev.lock`. Suite:
`.venv\Scripts\python -m pytest tests -m "not vectorbt" -q`. Branch de trabajo:
`foundation/f0b-compatibility-probe` (main = baseline original, no mergear).

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
