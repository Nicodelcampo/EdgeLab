# P2 — adjudicación de los seis `payload_sha256` no reproducibles

**Fecha** 2026-08-11 · **Worktree** `audit/p0-bigtrap2-drift`
**Herramientas** `tools/verificar_artefactos.py` (corregido acá), `tools/auditar_procedencia.py`
**Fuente de la lista** `docs/REGISTRO_NO_MEDIDO_2026-08-10.md` §1, corrida 2026-08-10 (turno anterior)
**Revisado por el auditor** el 2026-08-11 sobre `ffe523d` — correcciones de lenguaje/clasificación incorporadas.

---

## Veredicto por artefacto

| artefacto | veredicto | mecanismo |
|---|---|---|
| `f_ambos_filtros.json` | **OK_LEGACY** (`serialization=json_sort_keys_ensure_ascii_true`) | serialización de una era anterior — resuelto abajo |
| `F1_nulo_zonas_aleatorias__260757be9e71.json` | **WARN** | árbol dirty al generarse — el script ganó el fix de redondeo en un commit posterior al declarado |
| `censo_zonas_completo__21b7f3512158.json` | **WARN** | árbol dirty al generarse — el script no existía committeado en el commit declarado |
| `F1_superv_depletion__b107bf368c08.json` | **WARN** | mismo mecanismo, mismo commit declarado |
| `barrido_F2_altura.json` | **WARN** | mismo mecanismo; el script que lo generó ya no existe en el repo con ese nombre |
| `INCIDENTE_altura_de_zona_con_ruido_de_redondeo__ac9d001dc815.json` | **WARN** | mismo mecanismo, mismo commit declarado (es el artefacto pre-fix, archivado) |

**Ninguno es FAIL.** Para los cinco WARN, el árbol de trabajo actual coincide
con HEAD para ese archivo (`git diff HEAD` vacío) y cada uno tiene un único
commit en su historia (`git log --follow`). Eso demuestra que el archivo no
cambió *después* de commitearse — **no demuestra que ese commit nunca se haya
reescrito** (amend/rebase/force-push; este repo no lo hace como práctica,
pero el comando no lo descarta por sí solo). La formulación defendible es:
**no se detectó mutación posterior al commit; la procedencia exacta
pre-commit no es reconstruible desde acá.** No "no hubo tampereo" —
corrección del auditor sobre la primera versión de este documento, que usaba
esa frase más fuerte de lo que la evidencia sostiene.

---

## 1. `f_ambos_filtros.json` — resuelto, era de mi propia herramienta

`tools/verificar_artefactos.py` (y su predecesor de esta mañana,
`auditar_procedencia.py`... no, ese es otro barrido — el predecesor real es
la primera versión de `verificar_artefactos.py`, escrita ayer) recalculaba
el hash con `ensure_ascii=False` fijo. Probando variantes:

```
sort_keys=True, ensure_ascii=True,  default=str  ->  860cc551ff3f4da2  <- MATCH
sort_keys=True, ensure_ascii=False, default=str  ->  5b8982ec340881e2
```

Este artefacto es del linaje E-R1 (commits `06a22ec`/`90ab6cf`, anteriores a
todo el trabajo de hoy) y su campo `entorno` está **vacío** (`{}`) — a
diferencia de los otros cinco, que declaran `python: 3.12.7` igual que mi
entorno actual. Es consistente con un script de una convención más vieja,
de antes de que `ensure_ascii=False` fuera el default del proyecto. No hay
generador de este archivo en el repo actual para confirmar línea por línea
(otro síntoma de la misma era), pero el MATCH exacto con una variante
razonable de `json.dumps` es evidencia suficientemente fuerte: **no es
corrupción, es una convención de serialización distinta.**

**Corregido en `tools/verificar_artefactos.py`**: ahora prueba
`ensure_ascii` en {False, True} antes de declarar `MISMATCH`. Es un defecto
determinista de mi propia herramienta, demostrado, y lo permite la
instrucción de la tarea — corregido con el cambio mínimo (probar ambas
variantes, no elegir una).

---

## 2. Los otros cinco — mecanismo real: generación sobre árbol dirty, antes de la regla de procedencia dirty-aware

Ningún ajuste de `json.dumps` (`sort_keys`, `ensure_ascii`, con/sin
`default=str`, `allow_nan`) reproduce ninguno de estos cinco hashes. Tampoco
hay tokens `NaN`/`Infinity` en el texto crudo, ni objetos no nativos de
JSON (`Counter`, `set`, `numpy`) filtrados como string vía `default=str`
—se buscaron los tres explícitamente y no aparecen—. El campo `entorno` de
los cinco coincide exactamente con el entorno de esta corrida
(`python=3.12.7`, `Windows-10-10.0.19045-SP0`), así que tampoco es una
diferencia de versión de Python o de plataforma.

**Lo que sí explica los cinco, de forma consistente:**

Cada artefacto declara su propio `code_commit` (el resultado de `git_head()`
al momento de correr). Comparé ESE commit contra el estado actual del
script que lo generó:

| artefacto | `code_commit` declarado | qué muestra `git diff <commit> HEAD -- <script>` |
|---|---|---|
| `F1_nulo_zonas_aleatorias__260757be9e71.json` | `6a2c08a` | el script gana el fix de redondeo (`altura_ticks_exacta`, el `-1` de rango inclusivo) **en un commit posterior** a `6a2c08a` |
| `censo_zonas_completo__21b7f3512158.json` | `06f343a` | el script aparece como **archivo nuevo** (`new file mode`) — no existía committeado en `06f343a` |
| `F1_superv_depletion__b107bf368c08.json` | `f3d5c7b` | `F1_supervivencia_y_depletion.py` aparece como **archivo nuevo** en `f3d5c7b` |
| `barrido_F2_altura.json` | `f3d5c7b` | ningún `.py` del repo actual contiene el string `"barrido_F2_altura"` — el generador ya no existe con ese nombre (`censo_zonas_completo.py` documenta en su propio docstring que F2 "es este mismo módulo con otra lista de celdas": la fusión probablemente reemplazó a un script F2 standalone) |
| `INCIDENTE_altura_de_zona_con_ruido_de_redondeo__ac9d001dc815.json` | `f3d5c7b` | mismo caso que censo — es el artefacto ARCHIVADO pre-fix de F1.1, generado en la misma sesión |

**La lectura correcta**: `code_commit=git_head()` registra qué commit era
HEAD en el momento de correr, pero **no dice si el árbol estaba limpio**. En
los cinco casos, el script que produjo el artefacto **todavía no estaba
committeado** en ese HEAD (o llevaba un fix que se committeó recién
después) — es decir, corrió sobre un árbol dirty. El código que efectivamente
ejecutó nunca quedó capturado en git en su forma exacta de esa corrida:
puede haber tenido un campo de más, un campo de menos, o simplemente una
versión intermedia entre dos commits reales. Ningún parámetro de `json.dumps`
puede reproducir el hash de un payload cuyo contenido exacto no está en
ningún punto del historial.

**Esto es exactamente el hueco que la regla "procedencia dirty-aware" de
`CLAUDE.md` existe para cerrar** — publicar si el árbol estaba limpio al
momento de correr, además de `code_commit`. Esa regla se agregó el
2026-08-10, **después** de que estos cinco artefactos se generaran. No es
una regla que se violó: es una regla que todavía no existía cuando corrieron.
Los módulos escritos después de esa fecha (`F1.1_grilla_parametros.py`,
`F1.1_regimen_dow_vol.py`, y en general todo lo de hoy) publican
`head_start`/`head_end`/`dirty_start`/`dirty_end`, y verifican limpio.

---

## 3. Por qué esto no es evidencia de mutación posterior, y por qué tampoco es descartable sin más

`git diff HEAD -- <artefacto>` da vacío en los cinco, y cada uno tiene un
único commit en su historia — confirmado en el turno anterior y reconfirmado
acá con `unico_commit_en_su_historia()`. Eso es todo lo que se puede afirmar
con estas herramientas: **no hay evidencia de que el archivo haya cambiado
después de commitearse.** El self-hash nunca coincidió, ni siquiera el día
que se generó — no es que se haya corrompido después; es que el código que
lo produjo nunca quedó capturado en git en su forma exacta (§2).

**No se puede clasificar como PASS** porque el mecanismo de integridad que el
propio campo `payload_sha256` promete (recomputable desde el código
versionado) está roto para estos cinco, aunque el CONTENIDO sea confiable
por otras vías (git-diff-vacío + los propios resultados ya fueron
verificados independientemente por corridas posteriores — F1.1 corregido
replica 47pp contra el headline ya publicado, F1.2/F1.3 fueron la base de
`SESGO_DE_DISENO`, F2 fue confirmado por F4_PARAMETROS_RESTANTES el mismo
día). Por eso **WARN**, no PASS ni FAIL: la evidencia externa sostiene el
contenido, pero el mecanismo de auto-verificación interno de estos cinco
artefactos específicamente no es una prueba criptográfica válida.

---

## 4. Cambios aplicados

- `tools/verificar_artefactos.py`: reporta `OK` (canónico,
  `ensure_ascii=False`) vs `OK_LEGACY` (`ensure_ascii=True`) por separado, con
  el campo `serialization` explícito — ya no un `OK` indiferenciado. Renombra
  `estable_desde_commit` → `working_tree_clean` y agrega
  `commits_en_su_historia`, con el lenguaje corregido (§3). Lógica de
  clasificación extraída a `clasificar_hash()`, función pura.
- `tests/test_verificar_artefactos.py` (nuevo): 5 tests —
  canónico/legacy/mismatch real/sin-hash/caso-ASCII-puro.
- `docs/REGISTRO_NO_MEDIDO_2026-08-10.md` M1: re-etiquetado de "Paridad
  NT8↔Python" a lo que realmente mide (ver P0.1 §1.3 y el commit de M1).
- Este documento.
- **No se tocó ningún artefacto histórico.** No se re-generó ningún JSON, no
  se movió ningún hash de archivo, no se re-corrió F1.1 ni ninguna medición
  con outcomes.

## Aporte al referente

Cierra P2 con una explicación causal real, no con "probé varios parámetros y
ninguno anduvo": los cinco WARN restantes comparten un mecanismo único y
verificable (generación sobre árbol dirty, antes de que la regla que lo
previene existiera) en vez de ser cinco anomalías sueltas. Corrige además un
falso positivo determinista en la propia herramienta de auditoría de
procedencia de la sesión anterior — una herramienta de verificación que
reporta mal es peor que no tener herramienta, porque genera alarmas que
entrenan a ignorarlas.
