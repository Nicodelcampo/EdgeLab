# BT2A NQ Gate 1 — resultado, 2026-08-31

**Kernel:** `nicolasbuttaro/bt2a-nq-gate1-16cell-run`, versión 9. Corrió de punta a punta
en ~15,5 minutos reales (arrancó 19:22:01 UTC, agregación terminó 19:37:12 UTC).
**Commit congelado (checkout verificado):** `37aecc65c913ca42104e1b88b4c41a9124f7e29a`.
**Spec:** `specs/bt2a_nq_gate1_v1.draft.json`, hash `b9e75c2533091c3dc8a3a2c8b8b8efde6eb6dfe1313efae48a4b4885366695c3` (rebindeado esta misma noche — ver `DECISION_NICO_REBIND_EVENT_STORE_MANIFEST_2026-08-31.md`).
**Token 4 gastado:** `AUTHORIZE_RUN_BT2A_NQ_GATE1_V1`.

## Verificación (no confío en el JSON solo porque dice lo que dice)

- `bt2a_nq_gate1_manifest.json.result_payload_sha256` (`6935729f...`) recalculado a
  mano contra el `result.json` real (`json.dumps(sort_keys=True, separators=(',',':')...`)
  → **coincide exacto**.
- `manifest.spec_sha256` (`b9e75c25...`) → coincide con el spec rebindeado esta noche.
- `attestation`: `GATE1_RUN=true`, `OUTCOMES_ACCESSED=true` (esperado — Gate 1 existe para
  esto), `HOLDOUT_TOUCHED=false`, `PNL_ACCESSED=false`, `EDGE_DECLARED=false`,
  `PROMOTION_ELIGIBLE=false`, `WINNER_SELECTED=false` — exactamente lo que autorizamos
  (`future_price_path_authorized=true`, el resto `false`). **Sin breach.**
- `coverage.sufficient_power=true` (234 sesiones disponibles ≥ 228 requeridas, en las
  16 celdas).

## Decisión

```
decision: BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM
positive_supported_cells: []
EDGE_DECLARED: false
PROMOTION_ELIGIBLE: false
WINNER_SELECTED: false
reason: "No cell achieved Holm-adjusted two-sided significance at alpha=0.05 with required effect size"
```

**Ninguna de las 16 celdas cumple la regla de decisión** (`p_holm ≤ 0,05` **y**
`point ≥ 1,0 ticks` **y** `IC_lower > 0`). Con potencia suficiente, esto es un nulo real,
no un nulo por falta de datos.

## El matiz que hay que dejar escrito: significativo no es lo mismo que relevante

Contra lo que podría sugerir "ninguna celda significativa", **muchas celdas SÍ son
estadísticamente significativas** (`p_holm < 0,05`) en la familia primaria K_ABS−N_RAND:

```
B18_H25:  point=0.103 ticks   p_holm=0.016
B18_H50:  point=0.122 ticks   p_holm=0.018
B30_H25:  point=0.153 ticks   p_holm=0.016
B30_H50:  point=0.240 ticks   p_holm=0.016
B30_H100: point=0.261 ticks   p_holm=0.016
B30_H250: point=0.187 ticks   p_holm=0.048
B5_H25:   point=-0.053 ticks  p_holm=0.016
B5_H50:   point=-0.040 ticks  p_holm=0.016
B5_H100:  point=-0.034 ticks  p_holm=0.016
```

Lo que las tumba es la puerta de **tamaño mínimo de efecto** (1,0 tick), pre-registrada
antes de ver el resultado: el efecto máximo medido es 0,261 ticks — una fracción de tick,
sin relevancia económica, aunque estadísticamente distinguible del cero con esta cantidad
de datos (234 sesiones, ~750K eventos entre las 4 familias). Esto es exactamente el
escenario para el que existe esa puerta: con suficiente N, casi cualquier desvío no-cero
se vuelve "significativo" sin ser accionable.

**Detalle adicional, no una conclusión**: el signo se invierte entre barreras chicas
(B5, B9 → negativo) y grandes (B18, B30 → positivo). No se interpreta como señal — es
solo una descripción de la forma del nulo, útil como contexto si esta familia se retoma
alguna vez, no como hallazgo.

Los comparadores secundarios (K_ABS−K_BT2, K_ABS−K_ABS_SHUFFLE) muestran el mismo patrón
de celdas nominalmente significativas de magnitud chica — reportados, nunca disparan la
decisión, consistente con el diseño.

## El techo que ya estaba escrito antes de correr esto

La configuración de K_ABS (`bt2a_nq_7e84981882b0b380`, BigTrap2Absorption) se seleccionó
de forma informal sobre solo 2 de 5 contratos (`specs/bt2a_nq_informal_all5_provenance_amendment_v1.draft.json`,
`classification: EXPLORATORY_NON_CONFIRMATORY_NON_PROMOTABLE`). Este resultado hereda ese
techo — no es que el nulo lo cause, es una limitación de la población sobre la que se
midió, declarada antes de saber el resultado. Un nulo exploratorio no necesita ese sello
para ser un nulo válido; lo que no podría hacer, incluso si hubiera salido `SUPPORTED`, es
promoverse sin la campaña formal de 5 contratos.

## Qué queda pendiente de esta rama, del lado de gobernanza

- Un gap de autorización self-serve real en el CLI (P-58, `PENDIENTE.md`) — riesgo
  aceptado explícitamente por Nico para esta corrida puntual, fix diferido.
- Un bug encontrado y corregido esta noche por dos vías independientes al mismo tiempo
  (`sample_nrand_strata_indices`, O(n²) → vectorizado) — verificado por mí con medición
  propia (140,2s → <5s en un estrato de 50k/500) antes de confiar en el reporte ajeno.
- El resultado vive en `edgelab-stats/*.json` (por contrato) + `edgelab-output/*.json`
  (agregado) dentro del output del kernel — pendiente decidir si se commitea al repo como
  se hizo con el resultado V2 de BigTrap2, o se deja como artefacto Kaggle-only.

## Aporte al referente

BigTrap2Absorption sobre NQ, con potencia suficiente y sin breach de firewall, **no
muestra mecanismo direccional económicamente relevante contra un control aleatorio
emparejado** — hay estructura estadística detectable pero del orden de una fracción de
tick, exactamente lo que la puerta de tamaño mínimo de efecto está diseñada para filtrar.
Reduce la distancia hacia un edge real al cerrar formalmente esta rama de la cadena
(geometría/lifecycle → información → P&L bruto) para esta configuración específica de
K_ABS, sin necesidad de gastar presupuesto de holdout ni de campaña formal para llegar a
esa conclusión target-free-adyacente.
