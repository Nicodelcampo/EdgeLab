# Espejo de las entradas 001–005 del canal (origen Notion) — 2026-08-18

> **Por qué existe este archivo.** Las entradas 001–005 del canal nacieron **en Notion**
> y `docs/audits/CANAL_AUDITOR.md` lo dice explícito: *«el contenido de las entradas
> 001-005 sigue en Notion y no sobrevive a Notion»*. Nico cambia de auditor, así que la
> cuenta que las aloja puede dejar de ser accesible. Esto las rescata.
>
> **Procedencia, declarada y honesta.** Estas páginas **no tienen blob de referencia en
> el repo**: no nacieron de un archivo, así que la regla 3 del canal (path + blob, nunca
> re-transcribir) **no se puede cumplir** para ellas. Se marcan como **origen Notion, sin
> blob verificable**. No se presentan como reproducibles: se presentan como rescatadas.

---

## Qué de esas cinco entradas YA está en el repo (y no se duplica acá)

Antes de espejar se verificó qué contenido sobrevive por otra vía. Estos archivos
existen y son la fuente canónica:

| Contenido | Archivo canónico en el repo |
| --- | --- |
| Decisiones P-35 / P-37 / P-10 (entrada 004 §2) | `docs/research/DECISIONES_P35_P37_P10_2026-08-15.md` |
| Adjudicación `g2-a1`, gana B (entrada 005 §4) | `docs/research/ADJUDICACION_G2A1_2026-08-15.md` |
| P-38, allowlist vacía (entrada 005 §3) | `PENDIENTE.md` P-38 |
| Cierre del capítulo 0, los 7 cuerpos (entrada 005 §1) | `PENDIENTE.md` + `docs/DECISIONES_2026-08-15.md` |

**Lo que sigue es sólo lo que NO tiene otra copia.**

---

## 1. La cadena de dependencias (entrada 005 §4) — cero menciones en el repo

Es el hallazgo operativo más importante de las cinco entradas y **no estaba escrito en
ningún lado**. El orden real en que las cosas se desbloquean:

```
P-31 item 1  ->  diferencial A vs B  ->  merge de B  ->  P-38 (hashear)  ->  G2 puede promover
(data_root)      (la medicion)          (un contrato)    (allowlist)
```

**Por qué importa:** el capítulo 6 (robustez) no podía cerrar *ni pasando G2*, y el
primer eslabón de la cadena —`data_root()` fail-closed— era **lo más barato del
proyecto** y se estaba trabajando último.

**Estado al 2026-08-18:** el primer eslabón **ya está cerrado**. `data_root()` valida por
contenido y falla cerrado (commit del 15-ago, verificado por
`test_data_root_resuelve_data_gitignoreado_desde_una_worktree`). Por lo tanto:

- el **diferencial A vs B** ya es ejecutable — y de hecho se corrió (entrada 008: los dos
  contratos dan resultados estadísticamente idénticos, A trae 17 tests más, adjudicación
  **NO cerrada**);
- **P-38 sigue bloqueada** por lo que la 005 nombró: el paso 9 pide el sha256 «del
  archivo aprobado», y **no se puede hashear un contrato mientras existan dos versiones
  rivales de él**.

## 2. «El verde de la suite no es transportable» (entradas 004 §4 y 005 §5)

El auditor reportó **2 failed / 952 passed**; en su máquina, sobre
`tests/ --ignore=tests/research`: **539 passed, 26 failed, 13 errors, 11 skipped**.

No es contradicción: es que **las 39 rojas dependen del store**, que esa máquina no
tiene. Por archivo, del caché de pytest:

| archivo | fallas |
| --- | --- |
| `test_audit_p3.py` | 13 |
| `test_coverage_propagation.py` | 12 |
| `test_store_v2.py` | 7 |
| resto de `tests/bridge/` · `test_verify_tree` | 7 |

> **«La suite está en 2 failed» es una afirmación sobre una máquina, no sobre el repo.**

Misma familia que el venv global del 09-ago: **un veredicto que depende del entorno y no
lo declara.** Y misma familia que P-34/P-35/P-39/P-41 — una etiqueta que no se deriva de
su contexto.

## 3. Por qué P-35 quedó decidida pero NO implementada (entrada 004)

La decisión fue **`WARN` no es `parity_exact`**. La razón de no implementarla es
metodológica y merece sobrevivir:

> `test_coverage_propagation.py` está en 12 fallas por falta de store, y es la suite que
> validaría un estado nuevo de paridad. **No se cambia semántica de gates sin poder
> correr su test.**

Especificación que dejó para cuando se implemente: **estado propio**, y **no** reusar
`parity_under_review` —ése ya significa degradación §8.5 y confundiría dos hechos—, con
la corrida `WARN` de HFTZones2 como caso de prueba.

## 4. Por qué gana B: su propio comentario delata a A (entrada 005 §4)

`A::g2_decision.py`:

```python
G2_REQUIRED_GATES = (
    "mcpt",  # nombre estructural histórico; ahora significa nulo de campaña
```

**El comentario admite que el nombre miente.** Es P-34 otra vez y peor: ahí el desajuste
era accidental, acá está **documentado en el mismo commit que lo introduce**. Y G2-A1 ya
había degradado el MCPT a diagnóstico precisamente porque medía otra cosa que la que
decía. B lo renombra a `campaign_null`.

## 5. La lección de proceso de la 004, en sus propias palabras

La entrada 004 se publicó **sin haber leído las 001 y 002**, y produjo una «corrección»
que ya estaba resuelta en el propio canal. La retractación quedó dentro de la misma
entrada, sin borrar nada:

> **La regla 1 dice que el repo es el sistema de registro y esa página el timbre — pero
> el timbre también hay que escucharlo antes de tocarlo.**

Eso ya está resumido en `CANAL_AUDITOR.md` §Lección de proceso. Se conserva la frase
porque es la formulación original.

## 6. Errores registrados y no borrados (entrada 005 §9)

Dos lecturas del auditor sobre `g2-a1` que no sobrevivieron al archivo, conservadas
porque el registro no se limpia:

1. *«A no valida el umbral declarado, B sí»* — **falso**: A lo valida en
   `GateResult.__post_init__:121`.
2. *«A deja pasar un gate con valor exactamente 0.0»* — **falso**: los operadores son
   idénticos.

---

## Cómo leer este archivo

Es un **rescate**, no una fuente. Si algo de acá contradice un archivo canónico del
repo, **manda el canónico**. Si contradice la página original de Notion y la página
todavía existe, mandaba la página — pero el punto de este archivo es que puede dejar de
existir.

**Lo que no se rescató y se perdería si la cuenta se cierra**: el formato original, las
tablas de Notion, los enlaces internos entre páginas, y las páginas de auditoría de
Kaggle/holdout del 14 y 15 de agosto cuyo contenido sí está en `docs/research/` pero
cuya redacción original no.
