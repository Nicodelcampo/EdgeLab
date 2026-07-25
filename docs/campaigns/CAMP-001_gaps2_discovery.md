# CAMP-001 — Primera campaña de descubrimiento: Gaps2

> Este documento sirve al referente rector: ver [`../NORTH_STAR.md`](../NORTH_STAR.md).
> **ESTADO: DRAFT v0.1 — PROHIBIDO CORRER.** STOP obligatorio: este manifiesto,
> su número de hipótesis, riesgos y datos faltantes deben ser aprobados por
> Nico ANTES de ejecutar cualquier búsqueda sobre retornos. Al aprobarse se
> sella: se fija el hash del manifiesto y pasa a inmutable (cambios = enmienda
> nueva ANTES de correr, o campaña nueva).

- `campaign_id`: **CAMP-001-gaps2-discovery**
- Fecha de draft: 2026-07-24
- Hash de `NORTH_STAR.md`: `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`
- Contrato de gates: `docs/edge_validation_contract.md` (G0–G5)
- Hash del manifiesto: **(se registra al sellar, mecanismo del marcador sha256)**

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
| Desarrollo | 6E 09-25 · 6E 12-25 · 6E 03-26 · 6E 06-26 | rangos exactos = los del parquet F2 (se registran al sellar) |
| Holdout (PROHIBIDO) | todo dato ≥ **2026-07-01** | firewall G4 |
| Excluido íntegro | **6E 09-26** | su rango cruza el inicio del holdout; se excluye completo por margen. Su uso previo (paridad 07-13→16) fue target-free permitido |

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
  **Precisión de estado (corregida tras F7c):** `parity_exact` es un estado
  **por partición**, no por `config_id`. La partición que tiene el oráculo
  propio es la de **6E 09-26** (excluida del desarrollo, §3). Las particiones
  de esta misma config sobre los contratos de **desarrollo** no tienen oráculo
  propio: quedarán **`parity_covered`**, otorgado automáticamente al publicarse
  (mismo `config_id`, `kernel_id`, `bar_key` e instrumento; solo cambia el
  contrato, que la regla permite). Ver §4.1.
- Detección de interacción (touch/ruptura) en research: derivada de **barras
  OHLC vs geometría as-of** de la zona (determinista e independiente del
  kernel); ventana de actividad de zona = `[created_ms, ended_ms)`.

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

| Familia | Disparo (en barra t, zona activa as-of) | Entrada | Stop | Dirección |
|---|---|---|---|---|
| **F1 fade primer touch** | primer touch (rango de barra entra a la zona) de zona virgen | open t+1 | borde distal + `stop_pad` | rebote (bull→long) |
| **F2 ruptura-continuación** | close de t atraviesa el borde distal (cierre más allá de la zona) | open t+1 | borde proximal − `stop_pad` | continuación de la ruptura |
| **F3 fade confirmado** | touch + la barra siguiente cierra fuera de la zona del lado del rebote | open t+1 (tras confirmación) | borde distal + `stop_pad` | rebote |
| **F4 fade segundo touch** | 2º touch (la zona ya fue tocada y el precio volvió a entrar) | open t+1 | borde distal + `stop_pad` | rebote |

Target: `R × riesgo` (riesgo = |entrada − stop|). Time stop: cierre a mercado
tras `time_stop` barras m1 en posición.

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
3. **Política `close_at_session_end`** (cerrar o no toda posición al cierre de
   sesión): la spec del simulador lo expone como parámetro y **no asume un
   default**; afecta el horizonte real de las 4 familias. Debe fijarlo Nico al
   sellar.
4. Confirmación de Nico de: familias (§5), grilla y N_eff=48 (§6), regla de
   abandono (§8), elegibilidad y promoción (§4.1 y §11), y esta redacción de
   riesgos.

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

<!-- SHA256-BODY-ABOVE (se completa al sellar) -->
