# ZAMR-1 en Kaggle — runbook del operador

## Responsabilidad

Notion AI/GPT implementa, prueba, empaqueta y audita los artefactos. La intervención humana se limita a acciones de cuenta que no pueden delegarse: crear el Dataset/Notebook privado en Kaggle y cargar el bundle entregado.

## Etapa actual: Z0 sintético

- No contiene mercado real, outcomes, retornos, P&L ni holdout.
- Usa `transport_format=csv_truth_known` porque es un chequeo de contrato y entorno.
- CSV queda prohibido fuera de `pilot_stage=Z0_SYNTHETIC_ENVIRONMENT`.
- El piloto real Z1 seguirá exigiendo Parquet.

## Dataset Kaggle

1. Datasets → New Dataset.
2. Nombre: `edgelab-zamr1-z0-synthetic`.
3. Visibilidad: Private.
4. Descomprimir y subir todos los archivos del ZIP entregado.
5. No añadir colaboradores ni otras fuentes.
6. Versión `v1`: `Z0 synthetic contract test; no market data`.

## Notebook Kaggle

1. Code → New Notebook.
2. Nombre: `edgelab-zamr1-00-contract`.
3. Private; accelerator None/CPU; Internet Off.
4. Adjuntar únicamente el Dataset Z0.
5. Ejecutar `00_validate_contract.py` incluido en el Dataset.
6. No agregar EDA ni celdas experimentales.

Resultado obligatorio:

```text
PASS — contrato ZAMR-1 verificado
```

Artefacto obligatorio:

```text
/kaggle/working/contract_validation_report.json
```

Si falla, no corregir en Kaggle ni continuar. Guardar log/reporte y devolverlos al agente para corregir en Git.

## Después del PASS

Opus audita contrato y Notebook 00. Luego se resuelve M0 de licencia y se construye Z1 con 20–30 sesiones derivadas en Parquet. El holdout permanece físicamente ausente.
