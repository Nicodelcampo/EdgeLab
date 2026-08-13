# ZAMR-1 en Kaggle — runbook del operador

## Responsabilidad

El agente implementa, prueba, empaqueta y audita. La intervención humana se limita a acciones de cuenta: crear Dataset/Notebook privados y cargar archivos.

## Licencia

La decisión contractual es `NO_UPLOAD`. Subir ticks reales a Kaggle es un override de riesgo del usuario, no `RAW_ALLOWED`. No agregar colaboradores. Internet Off. Holdout ausente.

## Z0 sintético — ya cerrado

Dataset `edgelab-zamr1-z0-synthetic`, Notebook `edgelab-zamr1-00-contract`. PASS sintético no autoriza Z1 ni Z2.

## Z1 real — sólo después del builder v2

No usar el builder v1. El ejecutable vigente es `zamr1_z1_bigtrap2_defaults_v2`.

### Dataset de código, sin ticks

1. Datasets → New Dataset.
2. Nombre: `edgelab-zamr1-z1-code`.
3. Private; Link Sharing Off; sin colaboradores.
4. Subir un snapshot del checkout de `research/zamr1-zone-atlas`, incluyendo `edgelab/`, `specs/` y `kaggle/`.
5. Incluir un archivo `CODE_COMMIT` con el SHA de 40 caracteres del HEAD usado.
6. No subir Parquet de mercado en este Dataset.

### Dataset de ticks, separado

1. Nombre: `edgelab-zamr1-z1-raw-6e`.
2. Private; sin colaboradores.
3. Subir exactamente:
   - `6E_06-26_ticks.parquet` (`fd2e358d...`)
   - `6E_09-26_ticks.parquet` (`654e006e...`)
4. No recortar fechas a mano. El builder aplica el firewall.

### Notebook

1. Code → New Notebook: `edgelab-zamr1-01-z1-build`.
2. Private; Accelerator None; Internet Off.
3. Inputs: únicamente los dos Datasets anteriores.
4. Pegar y ejecutar `kaggle/zamr1/notebooks/01_build_z1.py`.
5. No agregar EDA, modelos ni celdas de P&L.

Resultado obligatorio:

```text
PASS — Z1 estructural construido; no interpreta alpha ni P&L
```

Artefactos en `/kaggle/working/z1/`:
`events_long.parquet`, `zones_long.parquet`, `dataset_manifest.json`, `source_data_manifest.json`, `instrument_manifest.json`, `contract_validation_report.json`, `resource_report.json`.

Si FAIL: no parchear en Kaggle. Devolver log y JSON al agente.
