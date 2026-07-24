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
- Las zonas se consumen del store (`api_verified` mínimo; la config es
  `parity_exact`). **Prohibido importar kernels en el research.**
- Detección de interacción (touch/ruptura) en research: derivada de **barras
  OHLC vs geometría as-of** de la zona (determinista e independiente del
  kernel); ventana de actividad de zona = `[created_ms, ended_ms)`.

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
- Promoción a `EDGES_DISCOVERED.md`: exige G2 + `parity_exact` propio (la
  config de zonas ya lo es; la config GANADORA de estrategia hereda si no
  altera la identidad de zonas).

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
5. **Simulador pendiente** (FASE 3): la política de fills/costos de G0/G3 aún
   no tiene implementación probada (**dato faltante #2**: decidir vectorbt
   instalado vs simulador propio mínimo).

## 10. Datos faltantes antes de sellar

1. Costos reales por lado del broker (estados de cuenta) → §7.
2. Decisión simulador: instalar extra `research-vectorbt` o simulador propio
   determinista mínimo (recomendación: propio mínimo, testeable, sin deps).
3. Confirmación de Nico de: familias (§5), grilla y N_eff=48 (§6), regla de
   abandono (§8), y esta redacción de riesgos.

## STOP

Este manifiesto NO autoriza ninguna corrida. Ejecución solo tras aprobación
explícita de Nico y sellado (hash + estado SEALED + entrada en el índice de
campañas).

<!-- SHA256-BODY-ABOVE (se completa al sellar) -->
