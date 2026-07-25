# CAMP-001 — Primera campaña de descubrimiento: Gaps2

> Este documento sirve al referente rector: ver [`../NORTH_STAR.md`](../NORTH_STAR.md).
> **ESTADO: SEALED v1.0 (2026-07-24).** Aprobado por Nico con las enmiendas
> E1–E5 aplicadas. El manifiesto es **inmutable**: cualquier cambio exige una
> enmienda versionada aprobada ANTES de correr, o una campaña nueva.
>
> **SELLADO ≠ AUTORIZACIÓN DE CORRIDA.** Antes de la primera corrida faltan
> (§10): simulador implementado y reproduciendo sus golden tests, particiones
> de 12-25/03-26/06-26 materializadas en `parity_covered`, y OK final de Nico.

- `campaign_id`: **CAMP-001-gaps2-discovery**
- Fecha de draft: 2026-07-24 · **Sellado: 2026-07-24 (v1.0, enmiendas E1–E5)**
- Hash de `NORTH_STAR.md`: `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`
- Contrato de gates: `docs/edge_validation_contract.md` (G0–G5)
- Hash del manifiesto: al pie (sha256 del cuerpo hasta el marcador)

## 1. Justificación económica (obligatoria)

Gaps2 detecta discontinuidades tick-a-tick (micro-gaps) con ciclo de vida
(touch/fill/invalidate). Hipótesis económica: los micro-gaps señalan
desequilibrios transitorios de liquidez; el precio interactúa con esas zonas de
forma no aleatoria (rechazo o continuación) en horizontes de minutos. Si existe,
el efecto debe superar ~2.7 ticks de costo round-turn estimado (§7) para ser
edge NETO. Gaps2 es el único candidato con circuito completo `parity_exact`
(G0 alcanzable hoy sin trabajo extra de paridad).

## 2. Cómo podría refutarse (obligatoria)

- G1: expectancy neta base ≤ 0, o P&L dependiente de <5 trades, o de un solo
  contrato/fold → el efecto no existe o no es estable.
- G2: MCPT p > 0.05 / PBO > 0.5 / WF-OOS ≤ 0 → el "efecto" es selección.
- G3: neto base > 0 pero colapso en adverso → el efecto existe pero no paga
  costos reales → se registra `failed (uneconomic)`.
- Refutación estructural: si las 4 familias fallan G1 en el agregado, la
  hipótesis "los micro-gaps de 6E llevan información accionable en m1" queda
  registrada como negativa; NO se amplía la grilla dentro de esta campaña.

## 3. Datos

| Rol | Contratos (individuales, sin empalme) | Regla |
|---|---|---|
| Desarrollo | 6E 09-25 · 6E 12-25 · 6E 03-26 · 6E 06-26 | rangos exactos F2 registrados abajo, **recortados a front month** |
| Holdout (PROHIBIDO) | todo dato ≥ **2026-07-01** | firewall G4 |
| Excluido íntegro | **6E 09-26** | su rango cruza el inicio del holdout; se excluye completo por margen. Su uso previo (paridad 07-13→16) fue target-free permitido |

### 3.1 Rangos F2 exactos y regla de recorte (E3, verificado al sellar)

Rangos crudos medidos sobre los parquets F2 (UTC):

| Contrato | Inicio F2 | Fin F2 | Ticks |
|---|---|---|---|
| 6E 09-25 | 2025-07-25 20:00 | 2025-09-15 14:13 | 2.540.174 |
| 6E 12-25 | 2025-09-08 03:03 | 2025-12-15 15:11 | 4.512.321 |
| 6E 03-26 | 2025-12-08 03:01 | 2026-03-16 14:16 | 5.063.517 |
| 6E 06-26 | 2026-03-09 03:00 | 2026-06-15 14:13 | 5.559.262 |

**Los rangos crudos NO son disjuntos**: cada contrato empieza a cotizar ~7 días
antes de que expire el anterior (verificado: 09-25/12-25, 12-25/03-26 y
03-26/06-26 solapan 7 días cada par). Usarlos sin recortar contaría dos veces el
mismo tiempo calendario, inflando `n_trades` y correlacionando folds que el
walk-forward supone independientes.

**Regla de recorte pre-declarada (front month):** cada instante calendario se
asigna al contrato de **vencimiento más cercano** que tenga datos, es decir, el
inicio de cada contrato se recorta al fin del anterior. Rangos efectivos de
desarrollo (disjuntos por construcción):

| Fold | Contrato | Rango efectivo (UTC, semiabierto `[inicio, fin)`) |
|---|---|---|
| 1 | 6E 09-25 | 2025-07-25 20:00 → 2025-09-15 14:13 |
| 2 | 6E 12-25 | **2025-09-15 14:13** → 2025-12-15 15:11 |
| 3 | 6E 03-26 | **2025-12-15 15:11** → 2026-03-16 14:16 |
| 4 | 6E 06-26 | **2026-03-16 14:16** → 2026-06-15 14:13 |

El desarrollo termina el **2026-06-15**, 16 días antes del inicio del holdout
(2026-07-01): sin riesgo de contaminación (el `holdout_guard` lo verifica
igualmente con `purpose="development"`).

Folds naturales (orden temporal): 09-25 → 12-25 → 03-26 → 06-26. WF de G2:
test = {12-25, 03-26, 06-26}, entrenando solo con contratos anteriores.

## 4. Identidad de zonas (config pineada)

- Indicador: **Gaps2**, kernel_id vigente al sellar (se registra).
- Params de zona: **los de la config validada** `a6c32c0e9dbeb79a`
  (defaults + `min_gap_ticks=2`), `bar_spec = time:1`,
  `chart_tz = America/Argentina/Buenos_Aires`.
  **Nota de identidad (decisión):** `config_id` incluye `chart_tz`; para
  heredar `parity_exact` las materializaciones de la campaña usan EXACTAMENTE
  esta identidad. Un run con otra tz sería otra config SIN paridad propia.
- `bar_spec` es dimensión EXTERNA de identidad (sellado). Esta campaña usa
  **solo `time:1`**: cada resolución extra consume presupuesto estadístico y
  exige su propio oráculo (el de 25t queda para una campaña futura).
- Las zonas se consumen del store (`api_verified` mínimo). **Prohibido importar
  kernels en el research.**
- Detección de interacción (touch/ruptura) en research: derivada de **barras
  OHLC vs geometría as-of** de la zona (determinista e independiente del
  kernel); ventana de actividad de zona = `[created_ms, ended_ms)`.

**Precisión de estado (corregida tras F7c).** `parity_exact` es un estado **por
partición**, no por `config_id`. La partición que tiene el oráculo propio es la
de **6E 09-26**, excluida del desarrollo (§3).

Las particiones de esta misma config sobre los contratos de **desarrollo** no
tienen oráculo propio: quedarán **`parity_covered`**, otorgado automáticamente
al publicarse (mismo `config_id`, `kernel_id`, `bar_key` e instrumento; solo
cambia el contrato, que la regla permite). Ver §4.1.

### 4.1 Elegibilidad de configs (regla dura)

Solo se corren configuraciones cuyas particiones estén en estado
**`parity_covered` o `parity_exact`**, bajo la semántica pre-declarada en
`docs/nt8_indicator_parity_contract.md` **§8** (definición §8.2, lista blanca
fail-closed §8.3, anti-autootorgamiento §8.4).

- `parity_pending`, `parity_failed` y `parity_under_review` **NO son elegibles**
  (una cobertura degradada a `under_review` **saca** a esa config de la campaña
  hasta que se revise, §8.5).
- La cobertura la otorga solo el proceso de propagación
  (`coverage.propagate_coverage`); ninguna corrida se declara cubierta a sí misma.
- Verificación al sellar y antes de cada corrida: listar el estado de paridad de
  cada partición usada; si alguna no es `covered|exact`, la campaña **no corre**
  sobre esa config.
- Consecuencia práctica ya verificada (§8.7 del contrato): sobre el store
  vigente, la config de esta campaña es elegible en 6E 09-25; para 12-25, 03-26
  y 06-26 hay que **materializar** la partición (se cubrirá automáticamente al
  publicarse, por identidad idéntica salvo el contrato).

## 5. Familias de estrategia (4, simétricas, interpretables)

Comunes a todas (pre-declarado): dirección mecánica derivada del tipo de zona
(`bull_gap` → soporte → lado long; `bear_gap` → resistencia → lado short; ambos
lados son la MISMA regla, no se cuentan como hipótesis separadas). Señal con
`available_at` = cierre de barra; ejecución al open siguiente (G0). Solo
market/stop-market. **1 contrato fijo** (sizing de descubrimiento). Máximo una
posición simultánea; señal con posición abierta se ignora. Zonas solapadas: se
opera contra la de `created_ms` más reciente. Salidas: stop, target R, o time
stop — lo primero que ocurra.

| Familia | Disparo (en barra t, zona activa as-of) | Entrada |
|---|---|---|
| **F1 fade primer touch** | primer touch (rango de barra entra a la zona) de zona virgen | open t+1 |
| **F2 ruptura-continuación** | close de t atraviesa un borde de la zona (cierre más allá) | open t+1 |
| **F3 fade confirmado** | touch + la barra siguiente cierra fuera de la zona del lado del rebote | open t+1 (tras confirmación) |
| **F4 fade segundo touch** | 2º touch (la zona ya fue tocada y el precio volvió a entrar) | open t+1 |

### 5.1 Dirección y stop — fórmulas exactas (E2, sin ambigüedad)

Notación: `top`/`bottom` = bordes de la zona en **precio**; `tick` = 0.00005;
`pad` = `stop_pad` en ticks; `dir` = `+1` long / `−1` short.

**Definiciones (fijas):**
- **distal** = el borde que el precio debe cruzar para invalidar la tesis del
  trade, es decir el borde del lado **adverso** a `dir`.
- **proximal** = el borde recién atravesado en una ruptura (el más cercano a la
  entrada, que queda del lado adverso una vez posicionados).
- El `stop_pad` se aplica **SIEMPRE en dirección adversa** a `dir`.

**Fórmula única para las 4 familias:**

```
stop  = borde_ref − dir * pad * tick
riesgo = |entrada_fill − stop|
target = entrada_fill + dir * target_R * riesgo
```

donde `borde_ref` es **distal** en las familias de fade (F1/F3/F4) y
**proximal** en la de ruptura (F2). Tabla explícita:

| Familia | Tipo de zona / condición | `dir` | `borde_ref` | Stop desarrollado |
|---|---|---|---|---|
| F1 · F3 · F4 (fade) | `bull_gap` (soporte) | **+1** long | distal = `bottom` | `stop = bottom − pad*tick` |
| F1 · F3 · F4 (fade) | `bear_gap` (resistencia) | **−1** short | distal = `top` | `stop = top + pad*tick` |
| F2 (ruptura) | `close(t) > top` (rompe hacia arriba) | **+1** long | proximal = `top` | `stop = top − pad*tick` |
| F2 (ruptura) | `close(t) < bottom` (rompe hacia abajo) | **−1** short | proximal = `bottom` | `stop = bottom + pad*tick` |

**Nota de dirección (desambiguación explícita):** en las familias de fade la
dirección la fija el **tipo de zona** (soporte→long, resistencia→short); en F2
la fija la **dirección de la ruptura**, no el tipo de zona — un `bull_gap` que
se rompe hacia abajo genera un **short**. Es mecánico desde el precio, sin
hindsight, y trata ambos lados de forma simétrica. Si en la barra `t` el cierre
rompiera ambos bordes (imposible con un solo `close`), no hay caso.

Time stop: cierre a mercado tras `time_stop` barras m1 en posición.

**Cierre forzado de sesión (E4, decisión de Nico): `close_at_session_end = TRUE`.**
Toda posición abierta se cierra a mercado en el último step de su sesión CME,
con `exit_reason="session_close"` y la regla de fill de salida market de
`docs/execution_simulator_spec.md` §6.1/§6.4. Este parámetro queda fijado acá y
se pasa igual a la configuración del simulador.

## 6. Grilla (gruesa y chica) y presupuesto de hipótesis

| Parámetro | Valores | Clase |
|---|---|---|
| familia | F1, F2, F3, F4 | estructural |
| `zone_min_size` (filtro offline sobre `size_ticks` del store) | 2, 3, 5 | selección offline |
| `stop_pad` (ticks) | 2, 4 | ejecución |
| `target_R` | 1, 2 | ejecución |
| `time_stop` (barras m1) | 240 | fijo |

**N_eff = 4 × 3 × 2 × 2 × 1 = 48 hipótesis**, todas cobradas al presupuesto
(abandonadas incluidas). Selección: **una métrica primaria única** = expectancy
NETA (USD/trade, escenario base); se elige 1 ganador por familia (4) y cada uno
enfrenta G2 con N_eff = 48. Métricas secundarias (informativas, jamás de
selección): PF neto, expectancy en ticks, DD, trades/día, MAE/MFE.

### 6.1 Elegibilidad del ganador de familia (E1, pre-declarado)

**`min_trades_winner = 50`.** Una configuración con **menos de 50 trades** en el
conjunto de desarrollo **no puede ser seleccionada ganadora de su familia**,
cualquiera sea su expectancy. Si TODAS las configs de una familia quedan por
debajo, la familia se registra `insufficient_n` y no avanza a G2.

**Calibración (target-free, solo frecuencia de zonas — sin mirar retornos).**
Medido sobre la partición `parity_covered` de la config de campaña
(`d1289a36`, 6E 09-25, 2025-08-01, 1 día completo, 2.130 zonas):

| Filtro | Zonas/día | Extrapolado a ~232 días hábiles de desarrollo |
|---|---|---|
| `zone_min_size ≥ 2` | 2.130 | ~494.000 |
| `zone_min_size ≥ 3` | 370 | ~86.000 |
| `zone_min_size ≥ 5` (celda **más rala**) | 87 | ~20.000 |

En esa celda más rala, las señales por familia siguen siendo abundantes
(F1 `touches≥1`: 70/día ≈ 16.200; F4 `touches≥2`: 47/día ≈ 10.900).

**La restricción binding NO es la escasez de señales sino la regla de una sola
posición simultánea**: con `time_stop = 240` barras m1 (4 h) y ~23 h de sesión
CME, el piso teórico es ~6 trades/día aun si TODOS llegaran al time stop, o sea
**≥ ~1.160 trades en desarrollo** para cualquier celda (y más si stops/targets
pegan antes, que es lo normal). Por lo tanto **50 no cuesta poder estadístico**:
es un guard contra celdas degeneradas (una combinación de filtros que por error
casi no dispare), no un filtro real. Se elige el extremo **superior** del rango
de referencia (30–50) por ser el más conservador sin costo.

**Relación con G1:** `edge_validation_contract.md` §G1 exige `n_trades ≥ 100`
para el candidato que avanza. Son controles de alcance distinto y deliberadamente
separados: 50 es umbral de **selección** dentro de la familia; 100 es gate de
**promoción**. Una config con 50–99 trades puede ganar su familia y luego fallar
G1 — ese resultado es informativo (dice que la familia es demasiado rala) y se
registra. No se toca G1.

Prohibido en esta campaña: refinamiento local de grilla, ML, combinación de
indicadores, resoluciones extra, tocar el holdout. Cualquiera de esas cosas =
campaña nueva con presupuesto acumulado.

(Nota BigTrap2, para campañas futuras: campañas R —`MaxAgeBars` fijo, horizonte
físico variable— y H —horizonte normalizado por regla target-free— son
experimentos DISTINTOS; se elige uno por pre-registro, jamás se mezclan.)

## 7. Modelo de costos (pre-registrado; confirmar antes de G3)

6E: tick = 0.00005 = **$6.25**. Por pata ejecutada, estimación a confirmar con
estados de cuenta reales del broker de Nico (**dato faltante #1**):

| Componente | Estimación/lado |
|---|---|
| comisión broker + exchange/clearing + NFA | **$2.20** |
| slippage base | 1 tick ($6.25) en market/stop |
| slippage adverso / severo | 2 / 3 ticks (stops 2/3) |

Round turn base ≈ $4.40 + 2 ticks slippage = **$16.90 ≈ 2.7 ticks**: es la
vara mínima honesta que el efecto debe superar. Escenario ideal: solo
diagnóstico, jamás para decidir.

## 8. Gates y reglas de abandono

- Gates: los de `edge_validation_contract.md` (G0–G5), sin modificaciones.
- Abandono (duro): si ninguna familia pasa G1 → la campaña cierra y se registra
  negativa (valor informativo real: los micro-gaps m1 de 6E no pagan costos).
- Los 4 ganadores de familia que pasen G1 avanzan a G2; los FAIL se registran.
- Promoción a `EDGES_DISCOVERED.md`: exige G2 + `parity_exact` propio de la
  config ganadora **sobre una ventana del período de desarrollo**. Detalle y
  oráculo de promoción pre-registrado en **§11** (el oráculo 09-26 NO sirve:
  cae dentro del holdout).

## 9. Riesgos declarados

1. **Costos dominantes**: zonas de 2-3 ticks con stops cortos → el costo RT
   (~2.7 ticks) puede superar el movimiento capturable. Riesgo alto y asumido:
   G3 existe exactamente para esto. Mitigación parcial: `zone_min_size=5` y
   `target_R=2` están en la grilla.
2. **Régimen**: ~11 meses / 4 contratos de desarrollo; un solo instrumento.
3. **Múltiples pruebas**: 48 hipótesis; mitigado por N_eff en DSR/MCPT/PBO.
4. **Dependencia de la ventana del oráculo**: `parity_exact` se validó en una
   ventana de 3 días de 09-26; la cobertura por ramas (F7b) sigue pendiente de
   más oráculos — riesgo residual técnico declarado, no bloqueante para G0.
5. **Simulador sin implementar todavía**: la política de fills/costos de G0/G3
   ya tiene **semántica cerrada y golden tests** en
   `docs/execution_simulator_spec.md` (decisión de Nico: simulador propio
   mínimo; `edgelab/engine.py` legacy NO se usa para evidencia formal), pero la
   implementación es un turno mecánico pendiente. Riesgo: que la
   implementación no reproduzca los golden ⇒ se bloquea la campaña hasta que lo
   haga.
6. **Cobertura de paridad más débil que paridad propia**: las particiones de
   desarrollo corren con `parity_covered` (§4.1). El riesgo residual está
   declarado en el contrato de paridad §8.2 (un tramo de datos distinto puede
   ejercitar ramas que la ventana del oráculo no tocó). Mitigación: la promoción
   exige `parity_exact` propio (§11).

## 10. Datos faltantes antes de sellar

1. Costos reales por lado del broker (estados de cuenta) → §7.
2. ~~Decisión simulador~~ → **RESUELTO**: simulador propio mínimo
   (`docs/execution_simulator_spec.md`). Queda pendiente su **implementación**
   (turno mecánico) y que reproduzca los golden tests de esa spec.
3. ~~Política `close_at_session_end`~~ → **RESUELTO por Nico (E4): `TRUE`**
   (cierre forzado de toda posición al fin de sesión CME). Registrado en §5.1 y
   se pasa a la config del simulador.
4. ~~Confirmación de Nico~~ → **RESUELTO: APROBADO CONDICIONAL** (2026-07-24)
   sujeto a las enmiendas E1–E5, aplicadas en esta versión. Familias (§5),
   grilla y N_eff=48 (§6), abandono (§8), elegibilidad y promoción (§4.1/§11)
   quedan confirmados.

**Bloqueos vigentes que NO impiden el sellado pero SÍ la primera corrida:**
(i) simulador implementado y reproduciendo los golden tests de
`docs/execution_simulator_spec.md`; (ii) particiones de 12-25, 03-26 y 06-26
materializadas y en `parity_covered`; (iii) OK final de Nico al resultado del
sellado. Los costos reales del broker (dato faltante #1) bloquean **G3**, no el
sellado.

## 11. Requisito de promoción y oráculo de promoción pre-registrado

Promover un resultado de esta campaña a `EDGES_DISCOVERED.md` exige (regla dura
de `edge_validation_contract.md`) **≥ `statistically_supported` (G2)** **y
`parity_exact` PROPIO de la config ganadora**.

**El oráculo actual (6E 09-26) NO sirve para promover.** Su ventana
(2026-07-13→16) cae **dentro del holdout sellado** y se usó bajo la excepción
*target-free* (paridad geométrica) registrada en `docs/holdout_access_log.md`.
Un edge no puede apoyar su promoción en evidencia tomada del holdout, ni
siquiera técnica: la config ganadora debe demostrar paridad exacta **sobre una
ventana del período de desarrollo (pre-holdout)**.

**Oráculo de promoción pre-registrado** (a exportar cuando haya un ganador; no
antes, para no gastar esfuerzo en configs que no lleguen a G2):

| Ítem | Valor |
|---|---|
| Indicador · barras | **Gaps2** · **1 minuto** (`time:1`) |
| Contrato | **6E 06-26** (contrato de desarrollo, pre-holdout) |
| Ventana UTC | **2026-05-05T22:00:00 → 2026-05-07T21:00:00** (2 sesiones CME completas; la ventana ya pre-registrada en el contrato de paridad §1) |
| Params NT8 | los de la config **ganadora** (se fijan al cerrar G2, no antes) |
| `EventLogPath` | `oracles\Gaps2_6E_0626_may_promo.csv` |
| Rev `.cs` | 190ed59 o posterior |
| Gate exigido | **P2 PASS** sobre esa ventana ⇒ la partición de desarrollo pasa a `parity_exact` propio |

Si ese oráculo diera WARN/FAIL, la promoción **se bloquea** y se analiza causa
raíz (prohibido promover con `parity_covered` ni ampliar tolerancias).

## STOP

Este manifiesto NO autoriza ninguna corrida. Ejecución solo tras aprobación
explícita de Nico y sellado (hash + estado SEALED + entrada en el índice de
campañas).

<!-- SHA256-BODY-ABOVE -->

**sha256 del manifiesto (cuerpo hasta el marcador):** `124b33cdc39629f6d5112a872aacc5e7d32e4ac3df8055305a1d9dd2d9a6cfa3`

**Estado:** SEALED v1.0 — 2026-07-24.
