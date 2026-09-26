# Enmienda G2-A1 — corrección del gate de robustez estadística

**Fecha** 2026-08-10 · **Aprobada por** Nico, explícita: "elijo la respuesta
que más nos acerque al objetivo y referente del proyecto" sobre las 3
preguntas de la auditoría.
**Origen** auditoría adversarial (Opus), ronda dedicada a refutar hallazgos
previos, no a confirmarlos por consenso. Verificado línea por línea contra
`edgelab/research/g2.py`, `edgelab/research/g2_decision.py`,
`tests/research/test_g2.py` y `docs/edge_validation_contract.md` en el tip
`2fcea58` — y re-verificado contra el código real (no el resumen de la
auditoría) antes de implementar, siguiendo la regla «fuente antes que
recuerdo».
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

---

## 1. El defecto — verificado, no conjeturado

`mcpt()` decía en su docstring "el estadístico es la suma neta". Es falso: el
código, dos líneas más abajo, calculaba la suma de los primeros k bloques
(la mitad temporal) — porque bajo permutación de bloques de sesión, **la suma
total no cambia**, así que la única cantidad que la permutación puede volver
improbable es DÓNDE se acumuló el resultado, no CUÁNTO.

**Consecuencia aritmética, no interpretativa:** G1 exige que ningún subperiodo
aporte más del 80% del P&L (estabilidad). Un candidato que satisface G1 tiene,
por definición, `obs ≈ total/2 ≈ media de la distribución de permutación`. Eso
da `p ≈ 0,5` — **FAIL** de un gate que se presentaba como prueba de robustez.

**El gate premiaba al edge que decae y bloqueaba al que se sostiene.** Es lo
opuesto exacto de la prioridad 3 del NORTH_STAR (robustez estadística) y de la
prioridad 1 (expectativa económica neta: un candidato genuinamente bueno
podía rechazarse sin que nadie entendiera por qué).

### El segundo defecto, independiente

`g2.py` tenía `DSR_MIN = 0.0`: `deflated_sharpe()` devuelve una probabilidad
en `(0,1)`; comparar contra `> 0` no filtra nada — ruido puro pasa con
DSR≈0,5. `g2_decision.py` tenía el umbral correcto (`0.95`) pero
`AUTHORIZED_DSR_METHOD_SHA256S = frozenset()` — un allowlist vacío nunca
autoriza ningún método, así que esa ruta **nunca aprueba, con ninguna
evidencia**. Dos definiciones de "G2 aprobado" en el mismo repo, contradictorias
entre sí y ninguna correcta.

## 2. Por qué ahora y no después

`docs/edge_validation_contract.md` §0: cambiar un gate exige enmienda
aprobada **antes** de correr la campaña afectada — nunca después de ver
resultados, para no relajar en función de lo que convenga. **Hoy ningún
candidato pasó G2**: ES está en cuarentena (incidente de procedencia, ya
cerrado), 6E (H1) dio neto negativo, YM no tiene ni calendario de research
todavía. Ésta es la única ventana en la que corregir el gate no está
contaminado por haber visto un resultado que dependía de él.

## 3. Qué cambia

1. **`mcpt()` → `temporal_concentration_test()`**, sacada de los gates duros.
   Sigue existiendo como diagnóstico —"¿dónde se concentró el resultado?"— sin
   pretender decidir aprobación.
2. **El gate que cumple el rol que `mcpt` prometía y no daba** es
   `g2_decision.PrimaryCI`: bootstrap estacionario-t por sesión, `lower > 0`.
   Ya existía, sin usarse como tal — es la misma máquina de inferencia que
   usó H1 (`edgelab.stats.cluster_estimand.studentized_stationary_interval`).
   No se escribió estadística nueva.
3. **Umbral DSR unificado en 0,95** en ambos módulos.
4. **`AUTHORIZED_DSR_METHOD_SHA256S` poblado** con el hash real del método
   (`g2.dsr_method_sha256()`, hashea las fuentes de `deflated_sharpe` +
   `expected_max_sharpe` — cambiar esa fórmula sin pasar por acá invalida
   automáticamente cualquier autorización vieja, mismo principio que
   `huella_del_codigo` en `curva_excursion_ticks.py`).
5. **`g2.py::evaluar()` eliminada**, junto con `G2Result` (quedaba huérfana).
   Queda **una sola** definición ejecutable de "G2 aprobado":
   `g2_decision.G2ValidationDecision.passed`.

## 4. Qué NO cambia

- `pbo_cscv`, `walk_forward`, `parameter_sensitivity` — no tenían defecto
  encontrado, sin tocar.
- Los umbrales de PBO (≤0,50) y walk-forward (>0) — sin tocar.
- Ningún candidato existente se re-evalúa retroactivamente: no hay ninguno
  que haya pasado G2 todavía.

## 5. Fixture de regresión — el hallazgo, verificado empíricamente

`tests/research/test_g2.py::test_edge_estable_lo_rechazaria_la_concentracion_pero_PrimaryCI_lo_aprueba`
construye un edge sintético con verdad conocida: 200 sesiones, expectativa
positiva pareja en el tiempo (sin concentración en ninguna mitad — el perfil
que G1 exige). Sobre esa misma serie:

```
temporal_concentration_test(...)   ->  p > 0,30   (el viejo gate: FAIL)
studentized_stationary_interval(...)  ->  lower > 0   (el gate real: PASS)
```

La contradicción que la auditoría encontró por álgebra queda demostrada con
datos, y protegida contra que alguien la reintroduzca sin que un test lo note.

## 6. Verificación

`tests/research/test_g2.py` (28 tests) y `tests/research/test_g2_decision.py`
(6 tests): **34/34 en verde**. Suite completa del repo: 799→794 (neto de
tests removidos/agregados), mismas 2 fallas preexistentes no relacionadas
(drift de versión del `.cs` de BigTrap2, incidente aparte).

## 7. Respuestas de Nico a las 3 preguntas de la auditoría

1. **Enmienda completa**, no sólo la parte de DSR — el defecto de MCPT es más
   peligroso (rechaza en silencio al candidato deseable) que el de DSR
   (rechaza siempre o nunca discrimina, más fácil de notar), y el reemplazo
   correcto ya existe, así que el costo de corregir completo es bajo.
2. **PR con código y tests**, no sólo documentación — un cambio documental no
   corrige nada en la práctica; es el mismo patrón que costó el incidente de
   procedencia de hoy: un texto que describe una corrección que el código no
   tiene.
3. **Eliminar `g2.py::evaluar()`**, no dejarla como capa exploratoria — dos
   definiciones de lo mismo es el modo de falla que ya mordió al proyecto dos
   veces en un día (ramas divergentes, geometría del nulo construida dos
   veces distinto); una capa "no vinculante" con el mismo nombre que el gate
   real es una trampa para quien no tenga el contexto completo.

---

## Aporte al referente

Corrige, antes de que exista un solo candidato que dependa de él, un gate que
habría rechazado sistemáticamente al tipo de edge que el proyecto busca
(estable, sostenido) y aprobado al que no sirve (concentrado, decayendo). Es
la misma familia de defecto que esta sesión viene cazando todo el día — una
afirmación en un docstring que el código no cumple — encontrada esta vez en la
pieza que decide si un descubrimiento futuro cuenta como válido.
