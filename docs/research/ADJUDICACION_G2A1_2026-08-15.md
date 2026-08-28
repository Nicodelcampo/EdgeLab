# Adjudicación de `fix/g2-a1-*` — ~~gana B~~ **NO CERRADA**

> ## ⛔ CORREGIDO EL 2026-08-16 — el diferencial SE CORRIÓ y **no los distingue**
> Siete escenarios sintéticos, **idénticos al dígito**. Y B tiene **17 tests
> menos** que A en la superficie G2. **B es candidato preferido, no ganador.**
> El §4 de este documento —«P-31 ítem 1 bloquea el diferencial»— **era falso**.
> → [`docs/research/g2a1_diferencial/RESULTADO_2026-08-16.md`](g2a1_diferencial/RESULTADO_2026-08-16.md)


**Fecha:** 2026-08-15 · Sin outcomes · Holdout intacto · Sin datos de mercado
**Autoriza:** Nico — *«avanzá con el capítulo 0 y la adjudicación de g2-a1»*.
**Cierra:** el criterio que dejé escrito en `DECISIONES_P35_P37_P10_2026-08-15.md`
para P-10.3. **Bloquea la ejecución de** P-38 hasta que se mergee.

```
A = fix/g2-a1-statistical-semantics   f3b826395336425b698842a481b2ee67f5877940  (2026-08-10)
B = fix/g2-a1-calibration-hardening   3c06e9c0ebebf0f37125c306e8bda02ff2f07e4a  (2026-08-11)
```

---

## 1. Veredicto

**Gana B.** No por ser más nueva ni más grande: **A conserva, a sabiendas, una
etiqueta que su propio código declara falsa.**

`A::g2_decision.py`, `G2_REQUIRED_GATES`:

```python
G2_REQUIRED_GATES = (
    "mcpt",  # nombre estructural histórico; ahora significa nulo de campaña
    ...
```

El comentario **admite que el nombre miente**. B lo renombra a `campaign_null` y
trae el umbral desde `g2_protocol.CAMPAIGN_NULL_MAX_P`.

Eso es **exactamente P-34**, la familia de defectos que este proyecto ya nombró:
*«las etiquetas de versión no se derivan del contenido»*. Acá es peor que en P-34,
donde el desajuste era accidental: **acá está documentado en el mismo commit que lo
introduce**. Un gate llamado `mcpt` que no mide un MCPT sobrevive a cualquier
lectura rápida, y la enmienda G2-A1 ya había degradado el MCPT a diagnóstico
justamente porque medía otra cosa que la que decía.

## 2. Lo que B agrega y A no tiene

| | A | B |
|---|---|---|
| nombre del gate | `mcpt` (comentado como falso) | **`campaign_null`** |
| implementación DSR | sin fijar | **`AUTHORIZED_DSR_IMPLEMENTATION_SHA256S`** — anclada por contenido |
| módulos | todo en `g2` | **`g2_dsr`, `g2_protocol`** nuevos + `g2_ratio` |
| operador del gate | implícito en la función | **explícito por gate** (`le`/`ge`/`gt`) |

El docstring de B declara las tres propiedades que la deep research exige:

> el nulo es específico de campaña; **DSR consume el calendario completo de
> sesiones** mediante `session_hac_bartlett_v2`; **DSR e IC primario comparten
> población**; ningún booleano recibido decide por sí solo.

Traducido a la investigación: calendario completo = **MinTRL** (Bailey/LdP 2012);
población compartida = el problema de **no-IID** (424 eventos en 201 sesiones no
son 424 observaciones); *«ningún booleano decide por sí solo»* = anti-gaming.

## 3. Dos hipótesis mías que la fuente refutó

Las registro porque el método importa más que el resultado.

1. **«A no valida el umbral declarado, B sí.»** **Falso.** A lo valida en
   `GateResult.__post_init__:121` (`if threshold != _GATE_THRESHOLDS[self.name]`).
   B lo hace en `_gate_passes`. **Ubicación distinta, misma garantía.**
2. **«A deja pasar un gate con valor exactamente 0.0.»** **Falso.** Los operadores
   son **idénticos** en las dos: `le` para nulo/pbo, `ge` para dsr, `gt` para
   walk-forward y sensibilidad.

Cuarta y quinta vez hoy que una lectura plausible no sobrevive al archivo.

## 4. ⛔ Lo que NO pude hacer, y por qué importa

El plan era **adjudicar midiendo**, con la validación diferencial que la propia
rama A trae (`.github/workflows/g2-a1-validation.yml`) contra casos de verdad
conocida — los 7 configs que fabrican Sharpe 1 con Sharpe verdadero 0, MinTRL,
no-IID.

**No corrí ninguno.** B importa `g2_dsr` y `g2_protocol`, que **sólo existen en su
rama**, así que ejecutar las dos exige dos árboles de trabajo simultáneos.

Y ahí aparece el bloqueo real: **`git worktree` está inutilizable para esto por
P-31 ítem 1.** `data_root()` resuelve el `data/` de la worktree, que desde que se
commitearon los 11 CSV de `data/nt8_oracles/` **existe siempre y no tiene `nt8/`**.
Cualquier corrida desde una worktree resuelve a un árbol sin parquets.

> **El procedimiento de adjudicación que el canal propuso está bloqueado por una
> pendiente abierta del propio board.** No es una limitación de esta máquina: es
> P-31 ítem 1 impidiendo la validación diferencial de P-10.3.

Por eso este veredicto es **estructural, no numérico**. Es suficiente para decidir
—el defecto de A está en su propio comentario y no requiere ejecutar nada— pero
**no sustituye** la corrida diferencial, que sigue debiéndose.

## 5. Qué recomiendo, en orden

1. **Cerrar P-31 ítem 1** (`data_root()` fail-closed validando que el directorio
   tenga `nt8/`). Desbloquea worktrees y, con ellas, toda adjudicación diferencial
   futura. Es chico y no toca gates.
2. **Correr la validación diferencial** A vs B con los casos de §2. Si contradice
   este veredicto, **manda la medición**.
3. **Mergear B**, retirar A con motivo escrito.
4. **Recién ahí P-38**: hashear el `edge_validation_contract.md` ganador y cargarlo
   en `APPROVED_G2_CONTRACT_SHA256S`. Antes de eso no se puede — el paso 9 de la
   enmienda del 03-ago pide *«el SHA-256 del archivo aprobado»*, y hasta el merge
   hay dos archivos rivales.

**No mergeo B hoy.** El paso 1 no está hecho, el paso 2 no se corrió, y mergear
sobre un veredicto puramente estructural sería exactamente lo que critico de A:
decidir por lectura cuando la medición era posible con un arreglo chico.

## 6. Identidades (regla 2 del canal)

| | SHA de 40 |
|---|---|
| A · `fix/g2-a1-statistical-semantics` | `f3b826395336425b698842a481b2ee67f5877940` |
| B · `fix/g2-a1-calibration-hardening` | `3c06e9c0ebebf0f37125c306e8bda02ff2f07e4a` |
| árbol de esta adjudicación | `f8e89666661d7dcc132ead50062dd48a09cd6d1c` |
