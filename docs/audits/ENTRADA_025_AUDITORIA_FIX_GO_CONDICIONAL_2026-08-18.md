# Entrada 025 — Aud → canal · auditoría del fix: GO condicional para censo v2

- **Fecha:** 2026-08-18
- **Dirección:** Auditor → canal (copia a Opus y a Nico)
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · sin ejecución sobre datos de mercado
- **Esto es evidencia, no una orden.**

**Commits leídos (40 caracteres):** `2d8533c33eb107d002461ab1d9ab76d5cc8cd53a` (HEAD origin al auditar) · `d7ae64205620adf5a1adffa2423769c386079082` (el fix: gate C-A + escaneo por ciclos + par de neutralidad) · `f8a0904b78bbef883ebe0146ca59c5d5c425bcf0` (ledger v1, traído en el merge)

**Evidencia (path + blob, regla 3 — origin, no el zip):**

| artefacto | blob |
|---|---|
| runner corregido | `diag/tasa_senales/censo_hz2a_superficie.py` · `91b6024aa2f549f78ea217445959625e61c86f18` |
| gate C-A | `tests/research/test_censo_hz2a_ceguera.py` · `fd0e1cf3e32fe5adfb0c5f7c71c6e819e68114ea` |
| neutralidad antes | `docs/research/censo_neutralidad_memoria_antes_2026-08-18.json` · `06ba40c00a7e04f4b2b0505c88f856eb30ec092b` |
| neutralidad después | `docs/research/censo_neutralidad_memoria_despues_2026-08-18.json` · `c69ad716f6a3f9c4bd93baa66a325e065ee45d8f` |

El zip `paquete_auditor_censo_2026-08-18.zip` es la misma prosa con CRLF. Tras `CRLF→LF` los cuatro blobs coinciden con origin. **Manda origin.**

---

## 1. El push está en origin — verificado

HEAD de `foundation/f0b-compatibility-probe` = `2d8533c…`. El fix `d7ae642…` es ancestro. El matiz de Claude es cierto y no limpia el registro de la 024: el primer `push` corrió y GitHub lo rechazó (`non-fast-forward`, porque `d2a37f3` había entrado en el medio); el commit no se perdió; faltó el segundo intento. Ahora está.

## 2. El bug queda cerrado, contra el código

Re-derivado, no aceptado de palabra. Caso asesino (baja a d=2, rechazo, **después toca**):

| instrumento | near-miss en `(D=10, δ=2, R=5, trade)` |
|---|---|
| `argmin` sobre todo el tramo (v1) | **0** |
| escaneo por ciclos (este blob) | **1** |

`BASE + acceso_profundo`: viejo 0, nuevo 1. El toque posterior ya no mata el near-miss anterior. Dirección: **subcuenta**, como la 023.

`BASE` produce (1, 1, 1). `BASE + nunca_vuelve` produce 2 near-miss: dos ciclos dentro del mismo corredor. Queda fijado en el test.

## 3. C-A — 8/8 PASS, recomputado en sandbox

El sandbox no tiene `edgelab` ni `pytest`. Se extrajo `censar_zona` + constantes (sin ejecutar imports del runner) y se rejugaron los 8 casos del test commiteado:

| # | chequeo | resultado |
|---|---|---|
| 1 | no nombra símbolos de outcome en código | PASS |
| 2 | no importa `avolcluster_tick_formal` | PASS |
| 3 | declara `outcomes_accessed=False` y `pnl_accessed=False` | PASS |
| 4 | apendear **nunca baja** un conteo (monotonía) | PASS |
| 5 | truncar **nunca sube** un conteo | PASS |
| 6 | control negativo: un censo retrospectivo **sí** es atrapado | PASS |
| 7 | geometría BASE informativa (1,1,1) y 2º ciclo = 2 | PASS |
| 8 | toque antes del giro mata el near-miss | PASS |

La parte fuerte es la monotonía, no los imports. Las dos expectativas que Claude corrigió (invarianza total; 1 donde van 2) están bien corregidas: pedir invarianza total habría obligado a romper el censo.

El «1.008 passed» sigue siendo evidencia de **máquina**, no del repo (P-31). Lo que sí se sostiene acá son estos 8.

## 4. Neutralidad de memoria — 120/120, con un asterisco honesto

Mismo recorte (`--dias`, 2.261.293 ticks, 39 sesiones, 63 zonas). Celdas: **0 diferencias** en A1 / near-miss / A2 / marginales / sesiones / `vive_por_N`. Firewall y universo idénticos. `holdout_included` false computado.

Lo único que cambia: `runner_blob` `bf65a0f2…` → `91b6024a…` (el cambio de memoria) y `segundos` 35,3 → 34,9. `medicion_comprometida: true` en **las dos** — el runner estaba sucio; el campo se autodela. Esperable, no es un PASS de procedencia limpia.

Esto prueba que liberar `partes` y reordenar columna a columna **no cambia conteos**. No es el censo v2 (cero celdas vivas; N de 45 días).

**205 → 345 no es la misma celda.** En esta ventana el máximo del primario pasa de `D=10 δ=3 R=5` (205) a `D=20 δ=8 R=5` (345). Es el máximo entre celdas, no un +68 % sobre un único punto. La subcuenta está establecida; la magnitud «~40 %» no se transporta a la superficie de 228 sesiones.

## 5. Condiciones para autorizar el censo v2

El fix de lógica **pasa**. El GO al re-run es **condicional**:

1. **`SCHEMA_VERSION` sigue en `censo_hz2a_superficie_v1`.** La definición del evento cambió (un corredor ya no es un solo `argmin`). Nueva definición = nueva etiqueta (manifiesto §6.1). Antes de correr: `censo_hz2a_superficie_v2` y `supersedes: 8bd29ed95b1756d6a11dee7c5d6a1b69c5c09144`.
2. **Las celdas ya no anidan en δ.** En `D=10 R=5` trade el acumulado es 67 → 121 → 205 → **134** → **28**. Hay marginales negativos. El anillo de la 014 («marginal = eventos nuevos de este δ») **deja de valer**. El artefacto v2 debe tratar cada celda como independiente, o dejar de publicar «marginal» como anillo. No es un blocker de lógica; es un blocker de *lectura*.
3. **Nico confirma máquina estable.** El censo pica ~1,5–3,4 GB; no es la matriz.
4. **La matriz de kernels no se re-corre como está.**

## 6. Observación al manifiesto — no bloquea

Después de contar NM, A2 es `(dd[r:] <= δ).any()` y el cursor sigue en `r+1` (el rechazo), **sin consumir el retorno**. El mismo tramo que satisface A2 del ciclo 1 puede ser el `d_min` del ciclo 2. El censo cuenta **geometrías**, no episodios `NM → reject → A2`. Se declara en el manifiesto v2. Si se quiere población de episodios, el cursor tiene que saltar al primer retorno.

Siguen en pie, del censo v1: ciclo de vida no modelado (C-B, **después** de v2) · A1 sin filtro de actividad · P-28.

## 7. Qué sigue

| Quién | Qué |
|---|---|
| **Opus** | Bump de schema a v2 + nota de celdas independientes / marginales. **No corre v2** hasta el OK de Nico. C2 (P-42): estimar `filas × 48 B` y avisar si > 2 GB. C-B después de v2. |
| **Nico** | Confirmar máquina estable. |
| **Auditor** | Con v2 corrido y schema nuevo: verificar el artefacto y escribir el manifiesto v2. El STOP vuelve entonces. |

## 8. Lo que NO hago

No autorizo el censo v2 con el schema todavía en v1. No edito el runner (máquina). No abro P-NN. No doy por cierta la suite 1.008 más allá de estos 8. No mergeo nada.
