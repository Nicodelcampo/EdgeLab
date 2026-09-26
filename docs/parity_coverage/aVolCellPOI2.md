# Cobertura de paridad — aVolCellPOI2

Oráculos pre-registrados: **O1 SessionRelative/TotalVolume/Quantile** (default),
**O2 WallClock/AbsDelta** (`bucket_anchor=WallClock`, `detection_source=AbsDelta`).
Especificación en `../nt8_indicator_parity_contract.md` §6.

**Requisito de historia** (contrato §5): con `min_sessions=15` y
`lookback_sessions=20` el chart NT8 necesita **≥ 35 sesiones ≈ 7 semanas**
cargadas antes del rango a comparar. Los `.cs` deben ser rev **190ed59+**
(footprint reconstruido 1-tick; los generados con Volumetric nativo NO valen).

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `bucket_anchor` | bucket_anchor | O1 (SessionRelative), O2 (WallClock) | pendiente |
| `bucket_size` | time_bucket_minutes | O1 | pendiente |
| `lookback` | lookback_sessions | O1 | pendiente |
| `weighting` | profile_weighting | O1 | pendiente |
| `detection_source` | detection_source | O1 (TotalVolume), O2 (AbsDelta) | pendiente |
| `detection_method` | detection_method | O1 (Quantile) | pendiente |
| `export_floor` | export_floor_percentile | O1 | pendiente |
| `quantile_cut` | detection_percentile | O1 | pendiente |
| `robustz_cut` | robust_z_threshold | (RobustLogZ, sin oráculo mínimo — variante futura) | pendiente |
| `min_vol` | min_absolute_volume | O1 | pendiente |
| `profile_gate` | min_sessions, min_cell_samples | O1 | pendiente |
| `geometry_merge` | merge_gap_ticks | O1 | pendiente |
| `geometry_min_cells` | min_zone_cells | O1 | pendiente |
| `lifecycle_invalidation` | invalidation_mode | O1 | pendiente |
| `lifecycle_max_touches` | max_touches | O1 | pendiente |
| `expiration` | max_age_bars | O1 | pendiente |

`detection_method=RobustLogZ` (rama `detection_method` camino alterno) y
`robustz_cut` no están en la campaña mínima: una config que los use queda
`parity_pending` hasta pre-registrar un tercer oráculo RobustLogZ.

## Resultado del primer oráculo (2026-07-26) — FAIL por CALENDARIO DE SESIONES

Oráculo `aVolCellPOI2_6E_0926.csv`, rango largo correcto (chart desde 08/06),
params idénticos (`lookback_sessions=20`, `min_sessions=15`, percentil 99,5).

```
Python: 31 zonas · primera 29/06 sesion 16 · ultima 16/07 sesion 28
NT8   :  5 zonas · primera 14/07 sesion 22 · ultima 17/07 sesion 25
gate FAIL: MATCHED 2 · MISSING_IN_NT8 29
```

### Causa raíz: los dos lados NUMERAN las sesiones distinto

Sobre el mismo tramo calendario Python cuenta **28** sesiones y NT8 **25**. Con
`min_sessions=15`, Python empieza a detectar en la sesión **16** —lo que manda la
regla— y NT8 recién en la **22**.

No es aritmética ni configuración: es el caveat **ya declarado** en el contrato
para los kernels con sesiones — calendario **CME ETH** de `sessions.py` contra el
**`SessionIterator`** de NT8. En el tramo 08/06 → 17/07 de 2026 cae el feriado
del **3 de julio** (Independence Day observado), exactamente el tipo de evento
que produce este desfase.

**No es un desacuerdo del kernel sobre qué es una celda anómala**: las 2 zonas
que ambos ven, coinciden. El desacuerdo es sobre **cuándo empieza a haber
suficiente historia**.

### Qué NO es

- **No** es "pocas zonas". Con percentil 99,5 y `min_cell_samples=500`, pocas
  zonas es el diseño. 31 en seis semanas es lo esperable.
- **No** es el rango: el export ya se hizo con el rango largo correcto.

### Pendiente

Resolver el desfase exige decidir cuál calendario es la referencia, y eso es
**cambio de semántica**: se eleva a Nico. Las opciones son alinear `sessions.py`
al `SessionIterator` de NT8 (incluyendo feriados), o declarar el desfase como
tolerancia medida y comparar sólo desde la sesión donde ambos ya detectan.
