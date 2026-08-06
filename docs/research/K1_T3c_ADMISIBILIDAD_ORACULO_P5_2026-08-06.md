# K1 / T3c — Admisibilidad del oráculo de P5 frente a INC-005

**Fecha:** 2026-08-06
**Autoría:** auditor (sesión Notion AI / Opus)
**Tip auditado:** `80c7b5f6165e9f21ff82a92c3e5678d5b0ba580a`
**Rama:** `foundation/f0b-compatibility-probe`
**Naturaleza:** adjudicación de procedencia; **no implementación**
**NT8:** no · **Holdout abierto por este documento:** no · **Outcomes:** no
**CSV del oráculo abierto:** no (no está en git; ver §3)

> Cierra el ítem K1 que la iteración 3 dejó abierto y que el implementador
> devolvió sin tocar. No se cierra por coincidencia de lecturas preliminares.
> Se cierra por cláusula escrita con alcance, condiciones y lo que un PASS
> **no** significa.

---

## 1. Pregunta

¿Es admisible usar `oracles/BigTrap2_time1_6E_0926_v2.csv` como patrón de oro
de P5, dado que el comentario de cuarentena INC-005 en
`edgelab/research/universo_estudio.py` nombra `BigTrap2_time1_v2` entre las
extracciones que quemaron `2026-07-01 → 2026-07-24`?

---

## 2. Hechos verificados en el tip (con cita)

### 2.1 La cuarentena nombra el artefacto

`edgelab/research/universo_estudio.py` (comentario de cuarentena permanente):

- quema `2026-07-01` a `2026-07-24` por contaminación cruzada manual;
- cita techo `2026-07-24T17:59:20`;
- nombra tres extracciones: `BigTrap2_diag_tick25`, **`BigTrap2_time1_v2`**,
  `Gaps2`;
- declara que cuarentena y frontera del holdout son mecanismos **distintos**;
- declara que ni una apertura sancionada entrega días quemados
  (`holdout_servible` los excluye): la cuarentena es de **procedencia**, no de
  metodología.

### 2.2 El instrumento espera ese archivo por nombre largo

`tools/correr_gates.py`:

```text
nombre="BigTrap2_time1"
oraculo="oracles/BigTrap2_time1_6E_0926_v2.csv"
```

### 2.3 El preflight inventarió el archivo fuera de git

`docs/PREFLIGHT_PRED-004_NT8_2026-08-04.md` §A:

| campo | valor documentado |
|---|---|
| ubicación al 2026-08-04 | `E:\EdgeLab\oracles\` (copia histórica) |
| **en el clon de trabajo / en git** | **ausente** |
| sha256 | `7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27` |
| tamaño · líneas | 1.110.200 B · 6.577 |
| `# meta` | 1 (una sola corrida) |
| reinicios de `seq` | 1 (sin append) |
| `version` en meta | **2.1** |
| parámetros de captura | defaults alineados al `.cs` actual |

### 2.4 N1 confirma el productor del oráculo

`docs/N1_INVENTARIO_SEQ.md` compara `nt8/BigTrap2.cs` v2.4 contra
`archive/nt8_cs_backup/BigTrap2_v2.1_20260727_102239.cs` y declara que **v2.1
es la que produjo el oráculo de referencia de P5**. No abre el CSV.

### 2.5 Qué es P5 hoy (contrato v5, no el JSON preregistrado)

`docs/CONTRATO_ANALIZADOR_PRED-004.md` v5 (`23981e56…`):

- P5 compara la **subsecuencia económica ordenada**
  (`P5_TIPOS_ECONOMICOS`: tipo · timestamp · payload);
- el `seq` absoluto **ya no es condición de FAIL**; se reporta
  (`seq_corrido`, deltas, conteos);
- un PASS **no** es igualdad bit a bit del EventLog completo.

`docs/predictions/PRED-004_tickbar_attribution_v23.json` **todavía dice**:

```text
P5 esperado: "bit-identico al oracle previo"
P5 refuta_si: "cualquier diferencia"
```

Eso es una **inconsistencia material** entre el preregistro y el instrumento.
Se registra en §6; no se “arregla” acá reescribiendo historia.

### 2.6 El oráculo **no está en el tip de git**

Listado de `oracles/` en `80c7b5f`:

- `README.md`
- `split/` (directorio)

**No hay** `BigTrap2_time1_6E_0926_v2.csv` ni ningún CSV de BigTrap2 time1.
Cualquier corrida de P5 depende de un archivo **local no versionado** cuyo
hash sólo está narrado en el preflight.

---

## 3. Identidad del artefacto (T3a parcial)

| afirmación | estado |
|---|---|
| `BigTrap2_time1_v2` (cuarentena) y `BigTrap2_time1_6E_0926_v2.csv` (gates/preflight) son el **mismo artefacto de familia** | **Acreditada por nomenclatura convergente** en tres fuentes independientes del chat: comentario de cuarentena, `correr_gates.py`, preflight |
| El archivo en `E:\EdgeLab\oracles\` tiene sha `7d0f464f…` | **Documentado** en preflight; **no re-hasheado en esta sesión** (no hay bytes en git) |
| Ventana exacta del CSV = techo `17:59:20` del comentario | **No re-verificada aquí** sin abrir el archivo. La iteración 3 la afirmó; este documento **no la eleva a hecho de esta pasada** |

**Consecuencia:** K1 (¿es legítimo el *uso*?) se puede adjudicar. T3a (¿tengo
en mano los bytes correctos el día de la corrida?) **sigue siendo precondición
operativa** y se cierra en la máquina con:

```text
sha256sum oracles/BigTrap2_time1_6E_0926_v2.csv
# debe ser 7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27
```

Sin ese match → P5 = `ABSTAIN` por procedencia de archivo, no se interpreta.

---

## 4. Adjudicación

### Veredicto: **ADMISIBLE como referencia de regresión, con alcance acotado**

### Cláusula (forma canónica)

```text
P5 usa el oráculo histórico BigTrap2_time1_6E_0926_v2.csv
(sha256 7d0f464f… cuando esté presente) como REFERENCIA DE REGRESIÓN del
camino de tiempo del .cs, no como muestra inferencial.

La cuarentena INC-005 NO lo inhabilita para ese uso porque:
  - la cuarentena quema DÍAS como material de estudio / procedencia de
    mercado (ticks, zonas, excursiones, N del universo);
  - P5 no estima nada sobre el mercado ni sobre esos días: compara la
    subsecuencia económica de dos EventLogs (contrato v5);
  - el productor declarado del oráculo es BigTrap2.cs v2.1; el objeto bajo
    prueba es si el camino de tiempo de v2.4 reproduce esa referencia bajo
    el predicado vigente.

Un PASS de P5 significa ÚNICAMENTE:
  la subsecuencia económica ordenada del camino de tiempo bajo v2.4
  coincide con la del EventLog de referencia v2.1, según CONTRATO v5
  (seq reportado, no juzgado como FAIL).

Un PASS de P5 NO significa:
  - que la captura histórica fuera correcta;
  - que el tick input de julio esté limpio;
  - que los días 2026-07-01..24 dejen de estar quemados;
  - que el EventLog completo sea bit-idéntico;
  - que seq no haya corrido (seq_corrido puede ser true con PASS);
  - que P1/P2/P3 estén aprobados;
  - permiso para abrir outcomes ni para mover el pin.

Un FAIL de P5, con T3a satisfecho, se interpreta como regresión (o cambio
deliberado) del camino de tiempo respecto de la referencia v2.1 — no como
propiedad del mercado en días quemados.

Si T3a falla (archivo ausente, hash distinto, meta≠1 corrida, version meta
inesperada): P5 = ABSTAIN por procedencia. No se reinterpreta el FAIL/PASS.
```

### Por qué no es circular en el sentido que bloqueaba

La lectura “circular” temía: *bit-idéntico a una captura defectuosa certifica
el defecto*. Bajo el contrato v5 la pregunta correcta es otra:

> ¿El camino de tiempo de v2.4 reproduce el EventLog económico que v2.1 emitió
> sobre la misma clase de corrida?

Si la referencia es “defectuosa” como **muestra de mercado**, sigue siendo el
**único ancla histórica disponible** del comportamiento del camino de tiempo.
Reproducirla es exactamente el estimando de regresión. Confundir eso con
validar julio como muestra es el error que la cláusula prohíbe.

### Por qué no es permiso en silencio

Hasta este documento, la admisibilidad era una lectura preliminar repetida.
Ahora es una **decisión escrita** con no-significados. La ausencia dejó de
tratarse como permiso.

---

## 5. Condiciones operativas antes de correr P5 (checklist)

| # | condición | dueño |
|---|---|---|
| 1 | Archivo presente en el clon de trabajo con sha `7d0f464f…` (T3a) | Nico / Claude en máquina |
| 2 | `# meta` = 1 corrida, `version=2.1`, un solo reinicio de `seq` (ya documentado; re-chequear) | operador |
| 3 | Analizador y contrato **v5** (`23981e56…`); no interpretar con el texto viejo del JSON PRED-004 | operador |
| 4 | Registrar apertura `check_holdout(purpose="target_free_validation", caller="pred004_analyze:p5-time")` **antes** de abrir el histórico (K3; requiere OK de proceso si escribe log versionado en la corrida) | Nico + Claude |
| 5 | Decisión de Nico sobre `seq_corrido=true` + económicos idénticos → ¿PASS / ABSTAIN / FAIL de política? (abierto; no lo cierra K1) | Nico |
| 6 | No usar `run_nt8_bridge` como analizador de PRED-004 (preflight §8 sigue obsoleto en tip) | operador |
| 7 | `.cs` bajo prueba = v2.4 compilado (`d5cf05b` / sha `9b63959a…`); salto declarado **2.1 → 2.4** | operador |

K1 **desbloquea la legitimidad del uso**. No desbloquea la captura completa de
PRED-004: siguen T3a en máquina, preflight G4, política de `seq_corrido`, y el
resto de la cola.

---

## 6. Hallazgos delicados del mismo pase (casi siempre salta algo)

Estos no son K1. Aparecieron al no tomar el reporte del implementador como
veredicto.

### D1 — El preregistro PRED-004 **mentiría** si se leyera solo

El JSON preregistrado sigue exigiendo bit-identidad y “cualquier diferencia =
FAIL”. El contrato v5 y la batería (52 tests, enmienda N1 aprobada por Nico)
ya no hacen eso. **Hay dos verdades publicadas.**

Hasta que el JSON se enmiende con traza explícita (o se congele un puntero al
contrato v5 como única fuente del predicado), un lector externo adjudicaría P5
con la regla **vieja** y podría declarar FAIL donde v5 dice PASS con
`seq_corrido`.

**Familia:** misma que el overclaim del docstring que Grok cazó — el nombre del
gate promete más (o otra cosa) que el predicado.

**Acción:** enmienda documental del JSON PRED-004 o capa que lo deje
`superseded_by: contrato v5` en el campo P5. No lo hago yo en este commit para
no mezclar adjudicación con reescritura del preregistro sin OK de Nico.

### D2 — El oráculo de P5 **no está en git**

El tip `80c7b5f` no contiene el CSV. El handoff y la actualización hablan de P5
como si el bloqueante fuera sólo K1. **Falso en la práctica:** sin copiar desde
`E:\EdgeLab\oracles\` (o equivalente) con hash verificado, P5 es imposible en
un clon limpio. Eso es T3a + deuda de empaquetado, no sólo admisibilidad.

### D3 — La ventana canónica de paridad cae **dentro** de INC-005

`tools/correr_gates.py` fija:

```text
W0, W1 = 2026-07-13T22:00:00, 2026-07-16T21:00:00
```

Eso está **entero** en `2026-07-01 ≤ fecha ≤ 2026-07-24`.

A la vez, `cargar_dias_de_estudio(..., incluir_holdout=True)` **excluye**
días quemados de `holdout_servible`. Resultado:

- la comparación de paridad **sí** se corre sobre material de días quemados
  (oráculo + parquet de esa ventana);
- el conjunto `aptos` que devuelve la puerta **no** incluye esos días;
- `clasificar()` puede etiquetar FAILs como `DATA_INTEGRITY_FAIL` porque
  “la ventana toca días fuera del universo”, aunque el FAIL sea de kernel.

No invalida K1 (P5 sigue siendo target-free). **Sí** significa que el censo de
paridad y la cuarentena están en tensión estructural: se mide paridad sobre
días que el propio repo declara inadmisibles como muestra. Debe quedar escrito
que esos PASS de paridad **no rehabilitan** julio para EXPLORE.

### D4 — “201 y pasa” no cierra el linaje

El manifiesto versionado (`runs/censo/manifiesto_universo.json`,
`generado_utc=2026-08-04`, `n_dias_aptos=256`, `config_hash=b92831e4cb3d59d3`)
está en git. Eso corrige el modo de falla del manifiesto fantasma.

Sigue **sin** estar escrita la tabla `256 → N_elegible` con una fila por
transición. El retiro de `200 → 197 por roll` es correcto como retractación;
no sustituye a K6. Cualquier texto que aún cite 197 como hecho queda
invalidado; cualquier texto que cite 201 sin mostrar la puerta + el gate sobre
el tip queda igual de frágil que antes.

### D5 — G1 sigue sin adjudicación independiente

El propio implementador lo dejó anotado (`2ad0a0c` y la actualización): la
regla “quien repara no audita” está **incumplida** para el parche G1. Grok
auditó la relajación N1/P5, no el parche mecánico G1 completo. K1 no lo cubre.

### D6 — Preflight §8 sigue mandando a `run_nt8_bridge` para P5

Confirmado en tip: el preflight de captura todavía prescribe
`tools/run_nt8_bridge.py` para P5. Eso mide **otro** contrato (paridad de
zonas), no `pred004_analyze p5-time`. G4 no está cerrado. Correr P5 “como dice
el preflight” sería el error que las tres capas ya marcaron.

### D7 — Conteo de modos de falla

El implementador contó seis y pidió asumir una séptima. En este pase aparecen
al menos:

| # | instancia |
|---|---|
| (previas del día) | B3, H2, H-GPT-1, cero silencioso AACloseOpenDiffs, fricción duplicada, truncamiento `delta_seq` |
| **7** | JSON PRED-004 vs contrato v5 (D1) — predicado publicado distinto del predicado que corre |
| **8** | oráculo de P5 ausente del artefacto versionado mientras el plan lo trata como listo (D2) |
| **9** | ventana de paridad dentro de cuarentena con clasificador que usa otro universo (D3) |

No es pedantería: es la misma familia — **la etiqueta del proceso no coincide con
la población o el predicado real**.

---

## 7. Efecto sobre la cola

| ítem | estado tras K1 |
|---|---|
| K1 / T3c admisibilidad | **CERRADO** por este documento |
| T3a hash en máquina | **ABIERTO** — precondición de corrida |
| T3b bytes del tick input | abierto; no bloquea la cláusula; puede informar un FAIL ambiguo |
| Captura PRED-004 | **sigue bloqueada** por T3a + G4/preflight + política `seq_corrido` + resto |
| D1 enmienda JSON PRED-004 | abierto, dueño Nico |
| D3 tensión paridad/cuarentena | abierto, no bloquea P5 bajo la cláusula |
| Adjudicación independiente G1 | abierta, sin dueño |

---

## 8. Lo que este documento no hace

- No copia el oráculo al repo.
- No enmienda el JSON PRED-004.
- No implementa K3 (`check_holdout` desde `p5-time`).
- No cierra T6-en-NT8 ni mueve el pin.
- No aprueba P1–P4 ni la captura.
- No reabre julio como muestra de EXPLORE.

---

## 9. Resultado

**K1/T3c: ADMISIBLE con alcance acotado.** La cuarentena INC-005 no prohíbe usar
el EventLog histórico de `BigTrap2_time1_*v2` como referencia de regresión del
camino de tiempo. Un PASS de P5 queda definido por el contrato v5 y por la
cláusula de §4; no por el texto bit-idéntico del JSON preregistrado.

**Aporte al referente:** impide que PRED-004 se adjudique contra un patrón de
oro cuya legitimidad era sólo una lectura preliminar, y deja visibles tres
desalineaciones (preregistro vs instrumento, oráculo vs git, paridad vs
cuarentena) que el reporte de avance no había elevado a bloqueo explícito.
