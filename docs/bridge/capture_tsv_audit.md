# Auditor reproducible de CaptureEventProbeV2

`edgelab/data/capture_tsv.py` incorpora al repositorio la auditoría que antes
existía sólo como scripts externos de la captura P1.

## Dos veredictos separados

- **Transporte:** callbacks, filas, secuencias, cola, writer y reloj monotónico.
- **Schema/procedencia:** provider, cuenta, modo, timezone, nulls y sentinelas.

`Simulation` es un entorno de cuenta. No demuestra que falte proveedor. El schema
v2.1 los registra en campos diferentes.

## Uso

```powershell
python tools/audit_capture_event_v2.py `
  C:\ProyectosQuant\EdgeLab\oracles\capture_event_v2__<capture-id>.tsv
```

Código de salida:
- `0`: transporte y schema sin errores;
- `1`: existe deuda o falla;
- `2`: archivo ilegible o argumentos inválidos.

Los warnings —por ejemplo, timestamps fuente que retroceden o ausencia de una
secuencia upstream— no convierten una captura íntegra en pérdida local.

## Interpretación P1

La captura P1 ya auditada externamente debería clasificar como:

```text
transport_ok = true
schema = event_capture_raw_v2
verdict = TRANSPORT_PASS_WITH_SCHEMA_DEBT
```

La deuda esperada es provider/account/timezone no separados y centinelas
`double.MinValue` en campos no aplicables. El auditor no inventa el proveedor a
partir de `Simulation`.

**Tests escritos, no ejecutados:** `tests/foundation/test_capture_tsv.py`.

**Aporte al referente:** la calidad del transporte y la procedencia del dato son
ejes distintos, auditables y reproducibles.
