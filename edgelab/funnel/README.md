# Funnel exploratorio: runner CPU con outcomes por etapa

## Responsabilidad y estado

El runner hace E1/E2 y un diagnóstico E3 sobre D0/D1. **No confirma edges ni autoriza promoción.** La integración operativa es CPU-only; `auto`/`gpu` en el runner fallan antes de ejecutar, sin fallback silencioso. El kernel CUDA queda disponible para verificación sintética de bajo nivel, no como route end-to-end acreditada.

## Entrada admitida

```bash
python tools/run_funnel_arrays.py \
  --arrays /ruta/a/arrays-aprobados \
  --registry /ruta/a/registro-preregistrado.json \
  --split /ruta/al/split-original-congelado.json \
  --out /ruta/a/directorio-nuevo \
  --backend cpu
```

No ejecutar este ejemplo sobre datos reales sin manifiesto/aprobación. `--split` exige las fechas y hash originales; cobertura ampliada/truncada falla, no se resplitea automáticamente. Un hash valida identidad de metadata, **no** es un permiso para abrir D2.

La CLI valida etiquetas/split antes de mapear los archivos de precios. Después carga `.npy` con mmap y `allow_pickle=False`. Esto NO es un firewall de archivos/rowgroups ni prueba de que el productor de features nunca vio una reserva. Las rutas legacy que generan señales/features desde todo el histórico siguen fuera de la garantía de este runner.

## Aislamiento y memoria

- Los kernels reciben sólo precios de D0 o D1, en recortes separados.
- Se excluyen señales cuyo horizonte completo cruza el borde de esa etapa; la decisión previa al primer bar puede tener índice local -1.
- Se conserva la convención del kernel: entrada y `entry + hold` inclusive (hold+1 barras).
- Batching limita **una matriz de salida** usando float64 como peor caso; un presupuesto que no admite una columna falla. No limita RAM/VRAM total, inputs, transferencias ni batches retenidos por el llamador.
- Preflight numérico rechaza conversiones truncadas, quotes cruzadas e índices/arithmetic fuera del dominio.

## Salidas y autoridad

`trials.parquet`, `survivors.parquet`, `summary.json` y el ledger local `edge_brain.jsonl` (nombre legacy). Este último **no es el DurableHippocampus canónico ni se ingiere automáticamente**.

Summary v2: `devices` por etapa; `device` es alias deprecated válido sólo para esta route CPU. PBO es diagnóstico sobre survivors, no multiplicidad del universo ni gate de promoción. `promotion_allowed=false`, `asserts_edge=false`.

`runner_d2_outcomes_read=false` describe sólo el runner. `holdout_opened=null` / `upstream_data_access=NOT_AUDITED_BY_RUNNER` evita afirmar una integridad global no probada. No representar null como false.

Debe usarse un directorio nuevo; publicación con mkdir exclusivo no sobrescribe corridas anteriores. Un intento fallido no justifica borrar resultados o reusar silenciosamente la carpeta.

## Verificación sin mercado

```bash
python tools/verify_funnel_cpu_gpu.py --cpu-only --out cpu_oracle.json
python -m pytest tests/test_funnel_stage_integration.py -q
```

El primer comando sólo produce CPU/oracle: **GPU_PENDING**, nunca PASS CUDA. Evidencia histórica específica del kernel en PR 63 no acredita automáticamente esta nueva integración.

[Entrada del repo](../../README.md) · [Contrato del módulo](../../docs/COMPONENT_FUNNEL.md).
