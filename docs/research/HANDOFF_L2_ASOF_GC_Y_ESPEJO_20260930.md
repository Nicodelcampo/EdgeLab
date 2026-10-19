# Handoff mínimo — GC sin esperar calibración y espejo L2

Código en la rama foundation/f0b-compatibility-probe. Sin modificar raw, climas,
detectores, índices del visor ni C0–C4.

## Lo que ya se hizo en nube

- Extractor neutral en ticks/contratos `tools/l2_asof_features.py`.
- Registro de TODOS los intentos `tools/mirror_l2_attempts.py`.
- Adapter de `IMP_CONFIRMED` con ledger explícito de publicación raw.
- Replay de QA `tools/gc_l2_asof_smoke.py` sobre los dos ejemplos GC legacy propios,
  reutilizando hash-validator/P0 y `l2_phase0.apply_event`.
- Tests sintéticos, prefijos reales y comprobación independiente de fronteras raw.
- No señales reales de GC/espejo unidas, no destinos futuros, no modelo ni P&L.

## Prueba del código

Desde el root del repo, con el entorno fijado:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/research -p test_l2_asof_and_mirror.py -v
```

El smoke es SÓLO para el schema legacy de esos ejemplos GC (columnas `price`,
`price_tick`, `source_row`, `ts_us`, lados/op originales, manifest local). No
aplicarlo directamente a los parquet nativos MNQ/GC sin `price`; reutilizar su
loader validado para alimentar el extractor. No relajar pins o inventar columnas.

## Enlace de futuros eventos, sin rediseñar la medición

Al publicar un grupo timestamp sobre la primera fila REAL siguiente:

```python
from l2_asof_features import AsOfFeatures

features = AsOfFeatures("GC", window_us=10_000_000)
features.publish(
    bid_levels, ask_levels,
    snapshot_asof_row, snapshot_ts_us,
    available_row, available_ts_us, gate=book_gate_reason,
)
packet = features.sample(
    event_available_row, event_available_ts_us,
    direction=-1,
    target_tick=zone_price_tick, target_side="ask",
    instrument="GC",
)
```

Este ejemplo declara una zona de techo; para piso, dirección +1 y lado bid.
Para espejo que regresa hacia abajo, A se observa en bid (liquidez que podría
oponerse a las ventas); hacia arriba, en ask. No confundir ese lado con “defensa
garantizada”. Target fuera del top-10 = UNKNOWN/null, NO size=0.

Sólo unir si `event_available_row/ts` están verificados. Los eventos exact4
actuales de GC sin publicación raw no se convierten en operables por este código.
No usar bar_B/índice del pico como si fuera instante de confirmación.

Para espejos usar `geometry_from_confirmed_event` con `IMP_CONFIRMED` y su ledger
de publicación. A/B se conocen conservadoramente al registro de confirmación.
No pasar `estado_final`, `bar_final`, S2 final, sólo espejos completos ni eventos
`MIRROR_COMPLETED`. Para cada intento guardar `registry.receipts()`, también
pendientes/invalidados/tardíos. Features al cruzar el landmark, no del grupo que
todavía no estaba publicado. `prospective_event_eligible` es geometría, NO permiso
de trade; `l2_observable` es soporte, NO probabilidad de éxito.

## Qué falta antes de un lote real

1. Tu calibración geométrica GC y congelar perfil(s); publicación raw y reloj.
2. Exportar ledger causal A/B de todos los intentos sobre el período aprobado,
   usando sólo eventos de confirmación conocidos. Confirmar instrumento/marco.
3. Congelar soporte/ventanas y medir densidad por sesión sin destinations.
4. Ratificar `BORRADOR_PROTOCOLO_ESPEJO_L2_PREDICTIBILIDAD_20260930.md` con invalidación,
   horizonte, splits, mínimo útil/potencia y OK antes de labels/modelos.

No repetir masivamente las 52 sesiones MNQ ni iniciar grid/outcomes por haber
pasado este smoke. No necesita que Claude rediseñe el núcleo: la integración
del loader requiere sólo adaptar su callback con el ledger verificado.
Datos, snapshots, eventos y precios quedan privados fuera del repo.

## Aporte al referente

La calibración de picos ya no bloquea el núcleo de medición. El paso pendiente
es enlazar eventos causalmente definidos y luego probar información incremental.