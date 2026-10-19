# Pedido mínimo de datos / trabajo local

El auditor buscó los datasets privados accesibles en Kaggle: sólo encontró el paquete rawL2 GC con May31 y Junio15; ES ticks sí, rawL2 ES no. No asumir que las etiquetas de diagnóstico de ES contienen libro.

## Primer envío ES (pequeño, sin resultados)
Elegir la primera sesión cronológica disponible del catálogo ES09-26 ya extraído, no la que tiene mejores operaciones. Enviar para esa sesión:
- `l1_quotes/YYYYMMDD.parquet` (incluye LAST y source_row original).
- `l2_depth/YYYYMMDD.parquet` (MBP-10, side/op/level/precio_ticks/size/ts_us/source_row).
- `manifests/YYYYMMDD.manifest.json`: instrumento, tick0.25, outputs hashes/rows, converter/script/version/provenance, semántica reloj y referencia temporal.
- Ticks de MISMO contrato e intervalo y su hash del inventario canonical; si ya están en Kaggle, basta ref+versión+nombre y hash.
- Identificación del catálogo y enmienda temporal aplicable. El preflight NO autoriza por sí mismo usar Q3/holdout para retornos.

Luego, para QA multis sesión, las primeras3 sesiones cronológicas disponibles del catálogo (incluyendo fallidas/cobertura insuficiente en inventario). Tres sirven para probar el pipeline, no para declarar potencia o confirmación estadística. Preparar selección mayor en manifiesto antes de outcomes.

## GC
Fuentes adicionales: primeras sesiones pre-holdout disponibles del catálogo local, mismo bundle de cuatro insumos y referencias. No elegir por éxito/densidad posterior. Junio15 conserva ABSTAIN: cualquier reexportación/corrección necesita causa documentada y hashes nuevos de AMBAS fuentes, nunca editar cinco timestamps en el auditor.

## Comando de preflight
Requiere Python, numpy y pyarrow. No ejecuta modelos, resultados ni replay de libro.

```bash
python -m unittest discover -s tests/research -p test_l2_pairing_preflight.py -v
python tools/l2_pairing_preflight.py --config preflight_SESSION_private.json --out pairing_SESSION_evidence.json
```

Config privada: `instrument`, `contract`, `session`, `tick_size`, `clock_offset_ns` ENTERO explícito, `clock_resolution_source`, `holdout_boundary_ns` autorizado; `files` con ticks/l1/l2/session_manifest, cada uno con path y sha256 externo comprobado. Sin offset por defecto, ni transporte automático GC→ES. Config se sella antes de labels. No incluirla al repo si contiene rutas/datos privados.

**No tocar:** C0/visores activos, calibraciones, modelos de climas STOP, raworiginales, holdout. Un escritor por carpeta; un solo proceso L2 pesado en la PC de16GB. Al auditor enviar los archivos o evidencia/hash del preflight; no hace falta gastar Claude en analizar resultados.
