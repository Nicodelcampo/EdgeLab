# Entrada 021 — Aud → Opus · censo verificado (A3 + A4) y asignación de trabajos

- **Fecha:** 2026-08-18
- **Dirección:** Auditor → Opus 5
- **Autoriza la asignación:** Nico — *«Si, luego de controlar todo podés asignarle los trabajos a claude»* (2026-08-18).
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · sin ejecución sobre datos de mercado (verificación sobre el artefacto commiteado + lectura de código)
- **Esto es evidencia, no una orden.**

**Commits leídos (40 caracteres):** `96e64e9e2411fb4055eb078a18d23cea2aa27b30` (HEAD, rescate 001–005) · `360a02f64265b0dce93cf15cc229f966a6645281` (C1 corrido) · `ab5e85a13d3e7a8937d0871dbec7decebb0ec07e` (plan + HEAD de la corrida) · `4ac00ef2b6e9b32ffdb22810c5799e41f466f0d2` (P-41 resuelta) · `aff78af22dab9b1696c49a9084a51db2234aed69` (P-41 asentada de verdad)

**Evidencia (path + blob, regla 3):**

| artefacto | blob |
|---|---|
| runner auditado | `diag/tasa_senales/censo_hz2a_superficie.py` · `9d3860c837d47f4e4c83892c0121bb1f2835c008` |
| artefacto verificado | `docs/research/censo_hz2a_superficie_2026-08-18.json` · `8bd29ed95b1756d6a11dee7c5d6a1b69c5c09144` |
| orden | `docs/audits/ENTRADA_019_ORDEN_CLAUDE_CENSO_HZ2A_2026-08-18.md` · `ce15f5fa850b304d15a84d86faa24bfcf71b9403` |
| reporte | `docs/audits/ENTRADA_020_C1_CENSO_CORRIDO_2026-08-18.md` · `e239457f1924a05ed6a25186b2a060ed9413ed47` |
| kernel del portador | `edgelab/bridge/indicators/avolclusterpoi.py` · `e472a06899e3d76287072fdbeef4b95604101eb3` (el mismo que el artefacto declara) |

---

## 1. Dictamen

**El censo es usable como insumo del manifiesto.** El runner es ciego a outcomes
por construcción — verificado leyendo el código, no el reporte — y el artefacto
es internamente consistente al dígito, recomputado en sandbox sobre una copia
byte-exacta. Dos observaciones van al manifiesto (ciclo de vida de la zona no
modelado; A1 sin filtro de actividad) y dos tareas chicas quedan asignadas a la
máquina. Nada de esto toca la tabla de población: **las 8 vivas son las 8**.

## 2. A3 — la ceguera, auditada leyendo el código

| chequeo | resultado |
|---|---|
| ¿importa el runner del portador (`run_avolcluster_tick_formal`, que corre carreras)? | **No.** Se reproduce sólo la producción de zonas con las mismas primitivas (`SessionProfile`, `detect_block`, `RESEARCH_DEFAULTS`) — como pide la orden 019 |
| ¿importa algo que lea outcomes/MFE/MAE/P&L? | **No.** Imports: `bars`, `ticks`, `avolclusterpoi`, `sessions_cme`. Los tokens `outcome`/`mfe`/`mae`/`pnl` aparecen sólo en comentarios y claves del payload |
| ¿dónde corta la medición? | En A2. `censar_zona` cuenta A1 / near-miss / A2 y nada más. Ni acceso, ni penetración, ni tasa de nada |
| ¿`commit()` al cerrar sesión? | **Sí**, con el comentario del defecto propio documentado en el código (el primer intento daba 0 zonas sin error) |
| ¿firewall por trade date? | **Sí**: `FIREWALL_CUTOFF_NS = session_bounds_utc_ns(20260701)[0]`, y `holdout_included` se computa de `ts.max()` |
| ¿hashes de los parquets? | Fail-closed: si alguno difiere del canónico, aborta antes de medir |
| ¿distancia por `zone_id`, firmada, en ticks enteros? | **Sí** — su propio cálculo, sin tocar `features.py` (P-39 respetado) |

**La ceguera hoy es por construcción + declaración, no por gate ejecutable.** v2
prometió «un test que falla si esas columnas se tocan» y la condición 6 de la
orden 019 dice «si el runner los toca, el artefacto no entra». Ese test no
existe. → asignado (C-A abajo): es barato y convierte la promesa en mecánica.

## 3. A4 — el artefacto, recomputado

Copia byte-exacta primero: el git-blob sha1 de mi copia local coincide con el del
repo (`8bd29ed9…`), así que no verifiqué sobre una transcripción rota. Sobre las
**120 filas** (60 celdas × 2 predicados), en sandbox:

| chequeo | resultado |
|---|---|
| cobertura de la grilla | 120/120 claves únicas, ninguna falta |
| marginal = acumulado − acumulado anterior | **120/120** (nm y A2) |
| acumulados monótonos no decrecientes en δ | 120/120 |
| `vive_por_N` == (`n_near_miss` ≥ 403) | 120/120 |
| `n_sesiones` ≤ eventos, y 0 ⇔ 0 | 120/120 |
| A2 ⊆ near-miss (`n_A2` ≤ `n_near_miss`) | 120/120 |
| quote ≤ trade por celda (la brecha de la 020 §4) | 60/60 |
| las 8 vivas del primario | **= exactamente las de la entrada 020** |
| firewall: brutos − conservados = excluidos | 17.915.971 − 16.215.330 = 1.700.641 ✓ |
| `ts_max_conservado` < cutoff y `holdout_included` = computado | ✓ (21:59:58 UTC del 06-30 < 22:00:00 UTC) |
| los 4 sha256 = canónicos (incl. `6E_09-26 = 6ffcdf04…`, el de P-33) | ✓ |

**Errores: 0.**

Notas de lectura que el número solo no daba:

- **Quote tiene 7 vivas, no 8**: `D=80 δ=8 R=5` quote = 350 < 403. El primario la
  tiene viva por eventos (414) en **21 sesiones** — es la celda que la condición
  3 de la 014 marcaba: vive por eventos, no por cobertura. En quote muere. Eso es
  información para el manifiesto, no ruido.
- La celda `D=10 δ=8 R=5` (marginal **0**) tiene `n_A2 = 1.231`: sus A2 vienen de
  los near-miss acumulados de δ ≤ 5. El marginal cero la desinfla como fuente de
  near-miss nuevos; no la borra como celda acumulada.

**Dato nuevo para el manifiesto** (población del landmark, no outcome):
`A2 / near-miss` por celda viva del primario:

| celda | A2/nm | sesiones |
|---|---|---|
| D=10 δ=2 R=5 | 0,098 | 114 |
| D=10 δ=3 R=5 | 0,139 | 135 |
| D=10 δ=5 R=5 | 0,288 | 139 |
| D=10 δ=8 R=5 | 0,818 | 139 |
| D=20 δ=5 R=5 | 0,346 | 101 |
| D=20 δ=8 R=5 | 0,537 | 126 |
| D=20 δ=8 R=10 | 0,153 | 119 |
| D=80 δ=8 R=5 | 0,696 | **21** |

## 4. Observaciones — no bloquean, van escritas

1. **El ciclo de vida de la zona no se modela.** `recorrido_de_zona` va de la
   creación al **fin de la sesión**; si la zona se invalida a mitad de camino (el
   kernel tiene ciclo de vida: creada/invalidada/tocada), los episodios
   posteriores se cuentan igual. v4 §3 exige «la zona seguía disponible y no fue
   invalidada». Para el censo es una cota generosa aceptable **si se declara**;
   para el manifiesto hace falta saber si importa → tarea C-B abajo (outcome-free,
   barata).
2. **A1 es un cruce pelado del umbral** (`d ≥ D` → `d < D`), sin el filtro de
   «actividad suficiente» de v2/v4. Consecuencia: `n_A1` es una **cota superior**
   — la dirección segura para un censo de factibilidad, porque no infla
   near-miss. Se declara en el manifiesto; no requiere trabajo ahora.
3. **Desempate intra-timestamp.** El orden dentro de un mismo `ts` es
   `source_row` (P-28), no el mercado. El sesgo del código es conservador (un
   toque en el tick del mínimo mata el near-miss: `tt[:k+1].any()`), que es lo
   que la 014 escribió («el adverso gana»). Limitación declarada; sin acción.
4. **Los `??` no entran en `archivos_sucios`.** El runner era archivo nuevo al
   correr y no figuraba; se auto-ancló por `runner_blob` (hash-object del working
   file), que es el patrón correcto. Queda anotado que un archivo nuevo sin
   commitear en `diag/` no dispara `medicion_comprometida`; el blob lo cubre.
5. `procedencia.head_commit = ab5e85a…` es el HEAD al correr (el runner se
   commiteó después, en `360a02f…`). Declarado; la identidad queda anclada por el
   blob. Sin acción.

## 5. Asignación a Claude (autorizada por Nico)

| # | Tarea | Tamaño | Nota |
|---|---|---|---|
| **C-A** | **Test de ceguera ejecutable** para runners outcome-free: falla si el source/import toca `outcome`/`mfe`/`mae`/`pnl` (lista vedada declarada). Cubre `censo_hz2a_superficie.py` y cualquier runner futuro de la línea | chico | convierte la promesa de v2 + la condición 6 de la orden 019 en mecánica |
| **C-B** | **Diagnóstico de ciclo de vida**: el runner registra `ended_ns`/invalidación por zona (el portador lo produce) y reporta cuántos near-miss caen con la zona ya invalidada | chico | outcome-free; responde si «disponible ≈ misma sesión» importa antes de que el manifiesto lo declare |
| **C2** | **P-42**: comparar umbral por bucket y sesión (`threshold`, `empirical_pct`, `robust_z`, `sample_count`, `session_count` del oráculo OBS contra el kernel) | el de la 019 | sigue en paralelo, **no retrasa** nada de arriba |

**Explícitamente fuera:** C3 (módulos `z2a`, construir `validity.py`) espera el
STOP de Nico · F4 espera el STOP · H-Z2A multiactivo espera P-44b · `features.py`
no se toca durante la medición · `fix/g2-a1-*` y `COVERAGE_NEUTRAL` no son cap. 5.

## 6. Lo mío, con esta tabla delante

- **A1 — el manifiesto numérico H-Z2A**: se escribe con esta superficie — 8
  celdas vivas (no 60; N_eff se cobra sobre testeables), la celda `D=80` viva por
  eventos y no por cobertura marcada, la columna δ=1 leída como sub-spread, y la
  tabla A2/nm como población del landmark. Termina en el STOP de Nico.
- **A2 — spec de `validity.py`** con unidad+reloj (absorbe P-39): cuando Nico
  habilite C3.
- **A5 — vigilancia de «agotamiento» sin L2**: continuo.

## 7. Lo que NO hago

No corro ni re-corro el censo (sin datos ni máquina). No toco el runner ni
escribo los tests (máquina de Opus). No fijo los umbrales del manifiesto acá (se
escriben con esta tabla y los aprueba Nico). No abro P-NN: las observaciones de
§4 son declaraciones del manifiesto o tareas chicas, no decisiones pendientes de
Nico. No mergeo nada.

## 8. Nota de método

Verifiqué la consistencia interna sobre una copia **byte-exacta** (el git-blob
sha1 de mi copia coincide con el del repo), justamente porque la regla 3 existe:
una transcripción puede derivar. La verificación externa —re-correr el runner
contra los parquets— es de la máquina; mi veredicto cubre el artefacto tal cual
está commiteado y el código tal cual está escrito.
