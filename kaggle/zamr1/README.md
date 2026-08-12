# ZAMR-1 en Kaggle — runbook del operador

## Modelo por fase

- Implementación, empaquetado y corrección de tests: **GPT/Codex**.
- Auditoría del contrato antes del piloto real: **Opus**.
- Optimización de sharding si falla el presupuesto: **Kimi**.
- Red-team de leakage/claims antes de promover: **Grok**.

No se cambia de modelo por una opinión distinta sobre el resultado. Cada modelo tiene un rol y los desacuerdos se resuelven con tests o abstención.

## Regla de hoy

El primer viaje a Kaggle es **sintético**. No subir ticks, outcomes, retornos, P&L ni holdout. El objetivo es demostrar que Kaggle reproduce el contrato y los hashes.

## Prerrequisitos locales

1. Checkout de `research/zamr1-zone-atlas`.
2. Árbol limpio.
3. Ejecutar:

```bash
python -m pytest tests/research/test_zamr1_contracts.py -q
```

4. Si hay un FAIL, detenerse y conservar el log completo.
5. Construir un directorio de bundle sintético con exactamente estos archivos:

```text
contract.json
parameter_registry.json
instrument_manifest.json
dataset_manifest.json
hashes.sha256
events_long.parquet
zones_long.parquet
structural_contract.py
```

`contract.json` debe ser copia byte-idéntica de `specs/zamr1_structural_contract_v0.json`; `parameter_registry.json`, de `specs/zamr1_parameter_registry_v0.json`; y `structural_contract.py`, de `edgelab/research/zamr1/structural_contract.py`.

El bundle sintético debe contener 20 sesiones truth-known, únicamente BigTrap2 default y los seis frames permitidos. No debe simular un edge: sólo filas válidas y casos de contrato.

## Crear el Dataset Kaggle

1. Ir a **Datasets → New Dataset**.
2. Nombre sugerido: `edgelab-zamr1-z0-synthetic`.
3. Visibilidad: **Private**.
4. Subir los ocho archivos del bundle sin renombrarlos.
5. No agregar colaboradores ni hacerlo público.
6. Crear versión `v1` con nota: `Z0 synthetic contract test; no market data`.

## Crear el Notebook

1. Ir a **Code → New Notebook**.
2. Nombre sugerido: `edgelab-zamr1-00-contract`.
3. Visibilidad: **Private**.
4. Agregar como input únicamente `edgelab-zamr1-z0-synthetic`.
5. Accelerator: **None/CPU**.
6. Internet: **Off**.
7. Copiar o subir `notebooks/00_validate_contract.py` y ejecutarlo completo.
8. No agregar otro dataset, modelo ni celda exploratoria.

El script encuentra automáticamente el único Dataset cuyo `contract.json` declara `zamr1_structural_contract_v0`. Si hay cero o más de uno, falla de forma cerrada.

## Resultado esperado

La última salida debe decir:

```text
PASS — contrato ZAMR-1 verificado
```

Y debe existir:

```text
/kaggle/working/contract_validation_report.json
```

Guardar una versión del Notebook y descargar ese JSON. El reporte, la URL/versión del Notebook y el log completo son el artefacto de Z0-Kaggle.

## Si aparece FAIL

- no corregir archivos a mano dentro de Kaggle;
- no quitar checks;
- no continuar a EDA;
- descargar `contract_validation_report.json` y el log;
- volver a GPT/Codex con ambos artefactos;
- corregir en Git, generar un bundle nuevo y crear una nueva versión del Dataset.

## Después del PASS sintético

Todavía no se ejecuta el barrido formal. El orden es:

1. auditoría Opus del contrato y Notebook 00;
2. decisión de licencia `RAW_ALLOWED`, `DERIVED_ONLY` o `NO_UPLOAD`;
3. construcción local del piloto real derivado de 20–30 sesiones;
4. Dataset privado nuevo `edgelab-zamr1-z1-6e-derived`;
5. Notebook 00 sobre ese dataset;
6. sólo si vuelve a dar PASS, habilitar el builder/benchmark Z1.

El holdout permanece físicamente ausente en todas estas etapas.
