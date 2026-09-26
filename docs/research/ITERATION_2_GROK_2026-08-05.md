# Iteración 2 — Grok — reencuadre y descomposición independiente

**Fecha:** 2026-08-05  
**Rama auditada:** `fix/capture-probe-v2-contract`  
**Tip de entrada de esta iteración:** `b591d1316616f0871c44df00823cd86a6b64f6a1`  
**Tip de código productivo bajo análisis:** `a0087b9429eb2ec741a5d4a1c3d4ba6d3b783a58`  
**Iteración previa leída:** `docs/research/ITERATION_1_GPT_2026-08-05.md`  
**Naturaleza:** análisis estático, reencuadre y diseño de pruebas; **no implementación**  
**Outcomes consultados:** no  
**Holdout abierto:** no  
**NT8 ejecutado:** no

> Protocolo de independencia: no se asume que la Iteración 1 sea correcta.
> Cada ítem se clasifica como `confirmación`, `refutación parcial`,
> `extensión` o `hallazgo independiente`. Claude debe reproducir contra el tip
> que reciba, no copiar veredictos.

## 0. Lente de esta iteración

La Iteración 1 fue excelente en **microdefectos alcanzables del analizador**.
Esta iteración pregunta otra cosa:

1. ¿El fixture propuesto alcanza un estado que el **emisor real** puede producir?
2. ¿Estamos reparando el instrumento preregistrado o un doble de laboratorio?
3. ¿Qué parte de PRED-004 se puede medir **sin** seguir inflando el `.cs`?
4. ¿Qué infraestructura ya existe y sólo hay que endurecer, en vez de inventar?

## 1. Veredicto ejecutivo

```text
PRED-004 sigue sin una medición válida.
a0087b9 mejoró el emisor y el analizador, pero no cerró el instrumento.

La Iteración 1 acertó en varios fallos fail-open del analizador/preflight.
Pero al menos un plan de reproducción (denom==0 vía amb∩procesadas) choca
con la semántica del emisor fiel: ese cruce es, hoy, un estado adversario,
no un camino normal de BigTrap2 v2.4.

Prioridad reordenada:
  1) no crashear / no PASS silencioso  (mecánico, chico)
  2) alinear contrato ↔ emisor ↔ tests con emisor FIEL
  3) gate de compilación real reutilizando check_nt8_cs.py como PRECHECK
  4) T3 en dos capas (CSV oráculo ≠ input de ticks)
  5) T0' como impugnación del estimando, en paralelo, sin borrar PRED-004
```

No capturar. No mover pin. No abrir holdout para diseñar tests.

## 2. Evidencia adicional inspeccionada

Además de lo ya citado por la Iteración 1:

| Artefacto | Para qué |
|---|---|
| `docs/predictions/PRED-004_tickbar_attribution_v23.json` | estimando preregistrado y orden de ejecución |
| `tools/check_nt8_cs.py` | precheck estructural ya existente (no es compilador) |
| `edgelab/research/holdout_guard.py` | firewall por `purpose`, no por capacidad |
| `nt8/BigTrap2.cs` v2.4 | orden real de `Abstener` / `ReportarMismatch` / `BARRA_PROCESADA` |
| `tools/pred004_analyze.py` | ramas, warmup, P3/P5 |

## 3. Matriz sobre la Iteración 1

| ID GPT | Clasificación | Lectura Grok |
|---|---|---|
| H-GPT-1 `verif` / `denom==0` | **confirmación del bug** + **refutación parcial del fixture** | El `NameError` por `verif` es real si se alcanza la rama. Pero con emisor fiel, `ANCLAJE_AMBIGUO` y `BARRA_PROCESADA` no cohabitan la misma barra: `Abstener` retorna sin emitir `BARRA_PROCESADA`. El fixture “todas las procesadas también ambiguas” es **adversarial**, no un camino normal. Sigue haciendo falta cubrir la rama (el analizador no debe crashear), pero Claude debe etiquetar el test como `emisor_adversarial` y agregar por separado la prueba de **inalcanzabilidad bajo emisor fiel**. |
| H-GPT-2 `--resolucion` opcional | **confirmación** | Correcto y de alto valor. El JSON preregistrado exige P5 sobre `time:1`; permitir omitir resolución es fail-open procedimental. Preferencia Grok: **obligatoria en CLI** para `p5-time` (más simple que un ABSTAIN opcional con dos semánticas). |
| H-GPT-3 test H1 ≠ compila | **confirmación + extensión** | Ya existe `tools/check_nt8_cs.py` (CRLF, región duplicada, llaves, meta). T6 no parte de cero: **PRECHECK = check_nt8_cs** y **GATE = compilación real**. El regex anti-`ok` es un control negativo histórico, no el gate. |
| H-GPT-4 preflight obsoleto | **confirmación** | Además: el preflight manda a `run_nt8_bridge.py`, que mide **otro** `FOOTPRINT_MISMATCH` (Python↔Python / matcher). Es el modo de falla más caro del proyecto: etiqueta correcta, estimando equivocado. Actualizar preflight es bloqueante de captura, no cosmética. |
| H-GPT-5 N1 `seq` | **confirmación con reorden** | N1 no debe mezclarse en el mismo microparche que el crash de `verif`. Es decisión de **estimando P5**. Antes de elegir arreglo: inventario de `LogEvent` en camino de **tiempo** v2.1 vs v2.4. Si el camino de tiempo no introduce diagnósticos nuevos entre eventos económicos, N1 puede ser **ruido residual** para esta captura y **deuda explícita** post-PRED-004. Si sí los introduce, P5 bit-idéntico por `seq` está roto por construcción. |
| H-GPT-6 completitud OHLCV en P3 | **confirmación débil / extensión** | De acuerdo en espíritu: P3 del JSON dice “OHLCV del bloque atribuido”, no “OHLC si aparecen dos campos”. Pero en el emisor tick actual, `ReportarMismatch` ya emite los cinco pares. Prioridad menor que H-GPT-1/2/4. Implementar como precondición de esquema, con test adversarial. |

## 4. Hallazgos independientes

### H-GROK-1 — Bajo emisor fiel, `denom == 0` parece inalcanzable

**Hecho (código):**

- `Abstener(...)` emite `ANCLAJE_AMBIGUO` y `return` — no hay `BARRA_PROCESADA`.
- `BARRA_PROCESADA` se emite sólo en el camino que ya decidió consumir/reportar la barra en `DrenarPorOHLCV`.
- Warmup del analizador v3: `lo_int = primera BARRA_PROCESADA`.
- `TAIL_BARRAS = 0` ⇒ no hay cola que vacíe el interior.

**Inferencia:**

Con reglas actuales y emisor fiel:

```text
primera_ok existe
⇒ hay ≥1 BARRA_PROCESADA
⇒ esas barras caen en el interior
⇒ amb ∩ procesadas debería ser vacío
⇒ denom = |procesadas| ≥ 1
```

La rama `if denom == 0` queda como:

- defensa ante logs adversariales/corruptos, o
- resto de una semántica anterior (`verif` / anclajes), o
- red de seguridad si mañana cambia warmup/tail.

**Qué debe hacer Claude:**

1. Reproducir el `NameError` con log **adversarial** (permitido).
2. Añadir test documentado:
   `test_bajo_emisor_fiel_denom_cero_es_inalcanzable` que recorra el `.cs` y/o un emisor-helper fiel y demuestre que no se emite el cruce amb+procesada.
3. Arreglar la rama para fail-closed sin excepción.
4. No vender ese test adversarial como “control del defecto real de v2.2”.

### H-GROK-2 — `BARRA_PROCESADA` también se emite tras mismatch

**Hecho:** si `anclado` y `!CoincideOHLCV`, el `.cs` hace `ReportarMismatch`, marca `sesionNoConfiable`, y **sigue** con `nPares++`, `BARRA_PROCESADA` y `EmitirBarra`.

**Consecuencia para el estimando:**

- Una barra con `FOOTPRINT_MISMATCH` **cuenta en el denominador**.
- Eso es lo correcto para “tasa de mismatch sobre barras que el motor trató”.
- No es lo mismo que “barras con anclaje verificado exitoso”.

**Riesgo:** el nombre del evento sugiere éxito. El contrato debe decir explícitamente:

```text
BARRA_PROCESADA = el secuenciador tomó una decisión de consumo/reporte para esta barra
≠ atribución OHLCV exitosa
≠ sesión confiable
≠ zona emitida
```

**Test mínimo:** log fiel con mismatch en barra B ⇒ B ∈ procesadas ∧ B ∈ mism ∧ entra al denominador.

### H-GROK-3 — Mensajes y comentarios del analizador todavía hablan de anclaje

**Hecho:** el warmup real usa `EVENTO_BARRA_PROCESADA`, pero al menos un mensaje de ABSTAIN aún dice “primer ANCLAJE_VERIFICADO…”. Docstrings mezclan la semántica vieja y la nueva.

**Consecuencia:** el próximo modelo (o humano) reintroducirá el bug de denominador-por-anclaje por lectura del mensaje. Limpieza de strings/docs es parte del parche, no nitpick.

### H-GROK-4 — El meta de tests sigue en `version=2.3` mientras el `.cs` declara `2.4`

**Hecho:** `META_23` en la batería y varios fixtures no exigen `version=2.4`. El analizador no valida que el conjunto de eventos sea coherente con la versión declarada.

**Riesgo de procedencia:** un log `version=2.3` fabricado con `BARRA_PROCESADA` se mide igual. Para laboratorio está bien; para captura real, P6/`# meta` debería exigir `version=2.4` cuando el paquete congelado es v2.4.

**Propuesta:** en modo captura (o con flag `--exigir-version 2.4`), meta incorrecta ⇒ `ABSTAIN`/`FAIL` de procedencia, no medición silenciosa.

### H-GROK-5 — T6 tiene cimiento: no reinventar `check_nt8_cs.py`

`tools/check_nt8_cs.py` ya bloquea la clase de incidente del 2026-07-25:

- LF sueltos / región NinjaScript duplicada
- más de una clase `Indicator`
- llaves/paréntesis desbalanceados
- meta/versión

Eso **no** detecta `CS0103` por identificador inexistente. Por eso v2.3 no compilable pasó hash + pudo pasar checks estructurales.

**Arquitectura T6 recomendada:**

```text
capa A — PRECHECK (ya existe): tools/check_nt8_cs.py
capa B — GATE NUEVO: compilación real NinjaScript / csc con refs NT8
capa C — PIN: sha256 del .cs que compiló en B
capa D — PROHIBICIÓN: preflight no ofrece instalar si A o B ≠ PASS
```

Control negativo de B: copiar a temp, insertar `if (!ok){}`, compilar, esperar fail; no tocar el canónico.

Si B sólo puede correrse dentro de NT8 en la desktop, el entregable de Claude es:

1. script + contrato de artefacto, y
2. parada limpia pidiendo a Nico la ejecución autorizada,

no un comentario “compila por inspección”.

### H-GROK-6 — T3 son DOS preguntas, no una

P5 del JSON: `time:1` bit-idéntico al oracle previo.

Pero el handoff ya mostró que la ventana del oracle histórico cae **entera** en holdout **y** en cuarentena INC-005.

Separar:

| Capa | Pregunta | Si falla |
|---|---|---|
| T3a | ¿El CSV oracle `BigTrap2_time1_…` tiene el sha esperado y una sola corrida (P6)? | No hay referencia ⇒ P5 = `ABSTAIN` o no se corre |
| T3b | ¿Los ticks/parquets que alimentaron esa captura siguen siendo los mismos bytes? | Un FAIL de P5 no distingue regresión de código vs material contaminado |

**Regla:** sin T3a, no se ejecuta P5. Sin T3b, un FAIL de P5 no adjudica culpa al `.cs`.

No se lee el holdout en esta iteración; Claude tampoco debe “inspeccionar de paso” días quemados para calibrar.

### H-GROK-7 — T0' (reencuadre): ¿hace falta instrumentar el `.cs` para medir la afirmación?

El JSON preregistrado dice qué se afirma:

- P1/P2: tasa de `FOOTPRINT_MISMATCH` **del EventLog NT8** bajo K25/K10
- P3: OHLCV del bloque atribuido en barras procesadas
- P4: no procesar cuando candidatos ≠ 1
- P5: time:1 bit-idéntico
- P6: higiene de archivos

**Tres familias de medición alternativa** (para otro agente; Claude no las implementa ahora):

1. **Equivalencia operativa offline**  
   Reimplementar en Python la regla `OHLCV unique match` sobre ticks ya capturados + snapshots de barra primaria exportados por NT8 (sin footprint interno).  
   - Sirve si se prueba paridad del algoritmo de atribución.  
   - **No** es automáticamente la misma afirmación que “BigTrap2.cs en NT8 atribuye bien”.

2. **Export lateral NT8**  
   Otro indicador/probe mínimo que sólo dumpée pares (barId, tickIndex0, tickIndex1, ohlcv) sin el detector económico.  
   - Reduce superficie del `.cs` bajo prueba.  
   - Sigue requiriendo compilación/captura.

3. **Reformulación del estimando**  
   Medir sólo P5+P6+eventos económicos, y mover P1/P2 a una PRED nueva si el denominador instrumentado se vuelve eterno juego del gato y el ratón.  
   - Exige aprobación de Nico.  
   - No borra PRED-004: la deja adjudicada o re-etiquetada.

**Veredicto T0' de esta iteración:**  
No hay todavía una alternativa que preserve el estimando preregistrado **y** elimine BL-1/BL-2 sin alguna forma de observar la atribución dentro de NT8. Por eso T1/v2.4 no fue un error de dirección. T0' sigue viva como impugnación, no como freno a cerrar el analizador.

### H-GROK-8 — El firewall sigue siendo un semáforo de strings

`check_holdout(..., purpose="target_free_validation")` **siempre** permite y sólo loguea. No hay capability: cualquier caller que pase el string entra. Eso confirma BL-5.  
Fuera del microparche de PRED-004, pero Claude no debe usar `purpose=` como si fuera prueba de target-free.

### H-GROK-9 — Orden de ejecución preregistrado ya exige compilación antes de capturar

El JSON dice:

```text
orden_de_ejecucion: tests sinteticos → compilacion NT8 → time:1 → K25 → K10
```

Por lo tanto T6 no es “nice to have de infraestructura”: **viola el preregistro** seguir sin gate de compilación. La Iteración 1 lo dijo; esta iteración lo ancla al artefacto de predicción, no sólo al handoff.

## 5. Qué le pediría a Claude, masticado y en orden distinto

### Principio de corte

Separar **mecánico** (no requiere juicio de Nico) de **semántico** (sí).

### Paquete G0 — Reproducción obligatoria (sin editar productivo)

Entregar un mini-reporte `docs/AUDITORIA_PRED004_REPRO_YYYYMMDD.md` o salida de sesión con:

| ID | Comando/test nuevo que FALLA o expone el hecho | Resultado |
|---|---|---|
| R1 | adversarial `denom==0` alcanza `verif` | excepción u otro |
| R2 | CLI `p5-time` sin `--resolucion` | PASS indebido u otro |
| R3 | `check_nt8_cs.py nt8/BigTrap2.cs --version 2.4` | OK/FAIL/WARN |
| R4 | grep/ast: mensajes que aún dicen ANCLAJE_VERIFICADO como warmup | lista |
| R5 | del `.cs`: `Abstener` no llama `BARRA_PROCESADA` | confirmado/no |

Si R1 no se reproduce, no “arreglar de oídas”.

### Paquete G1 — Microparche mecánico del analizador (un commit o dos)

Alcance cerrado:

1. Eliminar `verif`; rama `denom==0` ⇒ `ABSTAIN` estable, exit 2.
2. Tests: adversarial + nota de emisor fiel.
3. `--resolucion` **required=True** en `p5-time` (preferido) o ABSTAIN sin default silencioso.
4. Tests CLI.
5. Limpiar mensajes warmup (H-GROK-3).
6. No tocar N1 todavía salvo inventario en el reporte.

**Fuera de G1:** refactor amplio, holdout, NT8, pin, umbral 1%.

### Paquete G2 — Inventario N1 (reporte, sin redefinir P5 a ciegas)

Tabla:

| version | path | tipo LogEvent | ¿económico? | ¿incrementa seq? |
|---|---|---|---|---|
| 2.1 | tiempo | … | | |
| 2.4 | tiempo | … | | |
| 2.4 | tick | … | | |

Luego **propuesta** a Nico con una sola recomendación preferida y el costo sobre el preregistro.

Preferencia Grok si el camino tiempo no agrega diagnósticos entre económicos:

```text
P5 compara identidad económica (tipo, ts, payload) + reporta delta_seq
seq absoluto deja de ser condición de FAIL si el inventario lo justifica
```

Eso **es** cambio de contrato: requiere OK explícito. Si no hay OK, dejar N1 abierto y documentar riesgo; no silenciar con `P5_PAYLOAD_IGNORABLE` post hoc.

### Paquete G3 — T6 en dos capas

1. Cablear preflight/tests a `check_nt8_cs.py --version 2.4` como precheck obligatorio.
2. Añadir `tools/compile_nt8_cs.py` (nombre tentativo) o documentar comando NT8 reproducible.
3. Control negativo en temp.
4. Artefacto JSON content-addressed de compilación.
5. Actualizar preflight: sin compilación PASS no hay copia a `Indicators\`.

### Paquete G4 — Preflight único alineado al JSON PRED-004

Reescribir o reemplazar `PREFLIGHT_PRED-004_NT8_2026-08-04.md` para que:

- cite tip, `contrato_sha` v3, sha del `.cs` v2.4;
- prohíba `run_nt8_bridge` como medidor de P1/P2/P5;
- mande a `pred004_analyze.py` con flags obligatorios;
- incorpore T3a como puerta de P5;
- liste inventario de `oracles\` antes/después (N2/P6 procedimental);
- deje el pin intocado hasta adjudicación.

### Paquete G5 — No hacer aún

- captura NT8
- revisión ciega del paquete incompleto
- censo pesado T10 durante capturas
- unificar holdout capability (T5) en el mismo branch rush, salvo commit separado si sobra oxígeno
- fábrica de indicadores / Nautilus

## 6. Grafo revisado (más simple que C0–C5 + T0…)

```text
G0 repro
├─ G1 analizador mecánico (verif, resolución, strings)
├─ G2 inventario N1 → decisión Nico si cambia P5
└─ G3 precheck+compile
         │
         ▼
      G4 preflight congelado
         │
T3a/T3b ─┴─→ freeze → T7 ciego → T8 veto → T9 captura

T0' ∥  impugnación, no bloquea G1
T5  ∥  commit separado
T4/T11 ∥ antes de outcomes EXPLORE, no antes de G1
```

## 7. Fixtures mínimos listos para copiar (intención, no código final)

### F1 — Adversarial denom 0 (endurecimiento)

```text
meta v2.4
barra 0..N:
  BARRA_PROCESADA
  ANCLAJE_AMBIGUO   # el emisor fiel NO hace esto; el analizador debe sobrevivir
esperado hoy: excepción NameError o fallo
esperado post: ABSTAIN, exit 2, sin traceback
```

### F2 — Fiel mismatch cuenta en denominador

```text
meta v2.4
ANCLAJE_VERIFICADO una vez por sesión (opcional para el analizador v3)
BARRA_PROCESADA en todas las barras
FOOTPRINT_MISMATCH en un subconjunto interior con open_blk ≠ open_bar
esperado: esas barras ∈ denominador y numerador; FAIL si tasa > 1%
```

### F3 — Fiel abstención no procesa

```text
sólo ANCLAJE_AMBIGUO en un tramo, sin BARRA_PROCESADA en esas barras
esperado: no inflan denominador; si no hay ninguna BARRA_PROCESADA → ABSTAIN temprano
```

### F4 — P5 sin resolución

```text
p5-time --historico h__Minute1 --nuevo n__Minute1   # sin --resolucion
esperado: no PASS
```

## 8. Desacuerdos explícitos con la Iteración 1 (no resueltos por mayoría)

1. **Fixture denom==0 “realista”:** GPT lo presentó como reproducción del bug de rama; Grok lo marca como adversarial respecto del emisor fiel. Ambos pueden ser útiles si se etiquetan.
2. **N1 dentro de T2/C1:** GPT lo mete en el mismo paquete de reparación del analizador; Grok lo saca a G2 con posible decisión de Nico.
3. **T0' antes que reparación:** el handoff original ponía T0 primero; tras `a0087b9`, Grok coincide con GPT en que la reparación mecánica ya no espera a T0, pero insiste en mantener T0' vivo como impugnación del estimando.
4. **Obligatoriedad de `--resolucion`:** GPT admite ABSTAIN o required; Grok recomienda `required=True` en CLI para reducir estados.

## 9. Prompt corto para Claude (después de la 3ª iteración)

```text
Tip y rama los indica Nico. Leé CLAUDE.md, NORTH_STAR, PRED-004 JSON,
CONTRATO_ANALIZADOR v3, check_nt8_cs.py y docs/research/ITERATION_{1,2,3}_*.

Construí matriz confirmado/refutado/pendiente. Reproducí G0 antes de editar.
Priorizá G1 mecánico; N1 sólo con inventario (G2). T6 = precheck existente +
gate de compilación real. No uses run_nt8_bridge para PRED-004. No abras
NT8/holdout/outcomes ni muevas el pin. Todo test sintético declara si es
emisor_fiel o emisor_adversarial y cita línea del .cs cuando fabrique eventos.
Commits chicos. No te autoapruebes.
```

## 10. Resultado de esta iteración

Esta capa no implementa parches. Confirma los fallos fail-open centrales de la
Iteración 1, corrige el marco de un fixture, ancla T6 al preregistro y a
`check_nt8_cs.py`, parte T3 en dos capas, y reordena el trabajo de Claude para
que el camino crítico sea más corto y menos narrativo.

**Aporte al referente:** evita otra ronda de tests verdes sobre estados que el
motor real no produce, y obliga a que la medición de PRED-004 vuelva al
estimando preregistrado (EventLog NT8 + compilación real), no a un laboratorio
autorreferente.
