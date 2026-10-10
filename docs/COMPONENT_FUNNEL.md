# Funnel: contrato de integración CPU por etapas

## Posición en EdgeLab

Datos/custodia aprueba fuentes y particiones; el productor de features prepara señales; este runner hace screening exploratorio sobre D0/D1; el motor tick-exact y validación confirmatoria son otra etapa. El hipocampo canónico recibe evidencia sólo mediante un adaptador aprobado, no por existir un archivo llamado edge_brain.jsonl.

## Interfaces

- `stage_window`: calcula límites/horizontes con etiquetas e índices, sin precios.
- `iter_screen_batches` / alias `bounded_batches`: valida y limita una matriz; no relee los mismos precios por cada batch de configs.
- `cheap_screen`: primitiva de screening, no simulador tick-exact; CPU/GPU de bajo nivel para pruebas.
- `FunnelRunner`: orquestación CPU, salidas y diagnóstico; D2 cerrado incluso con el hash público del split.
- `load_frozen_split` / `validate_split`: identidad, orden, no solapamiento y cobertura exacta; no autorización.
- `tools/run_funnel_arrays.py`: entrada soportada con `--split` explícito y output nuevo.

## Compatibilidad

Se conserva `normal`, se acepta `inverse` y `reverse` como alias legacy -1. Configs no se modifican en sitio. CPU devuelve float64: el test antiguo que usaba 8 bytes para dos señales era insuficiente y se corrige a 16 con assert de nbytes.

`devices` es canónico; `device` queda como alias CPU-only deprecated. `holdout_opened` puede ser null por falta de prueba upstream y no se debe coercer a false. Summary v2 queda marcado no confirmatorio/no promocionable.

La CLI no permite backend auto/gpu de orquestación. Los callers legacy como run_mgc_nonema_funnel.py requieren revisión de generación de features y configuración antes de cualquier uso nuevo; no se rerunean familias negativas para adaptar resultados al nuevo código.

## Split y aprobación

Para un rerun, suministrar el split original de la campaña. No recalcularlo sobre historia ampliada, truncada o corregida para obtener otros resultados. La API programática sin frozen_split está rotulada GENERATED_DIAGNOSTIC_ONLY; no constituye aprobación. El hash no es una credencial.

## Garantía y límites

Los tests ejecutan CPU/Numba/Parquet reales sobre arrays inventados: alteran D2 a NaN, verifican invariancia de artefactos, recortes, límites, ledger, CPU/oracle y CLI. No inspeccionan mercado ni prueban generación de features, saneamiento/liquidez, reserva global, ejecución CUDA end-to-end o multiplicidad completa.

Los antiguos artefactos se preservan, sin declararlos revalidados. Antes de nuevas campañas siguen pendientes el gate de fuente/custodia, wiring upstream y los criterios estadísticos específicos.

[Detalles y comandos](../edgelab/funnel/README.md) · [Mapa](COMPONENTS.md).
