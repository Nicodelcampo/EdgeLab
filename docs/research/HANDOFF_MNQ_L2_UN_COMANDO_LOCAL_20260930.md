# MNQ L2 — una ejecución local, diseño y análisis en la nube

> **Actualización 30/09/2026: STOP para seguir las 52 con V1.** Primera sesión recibida: procedencia/geometría PASS, publicación live no certificada y 27/31 máscaras desconocidas. Este handoff se conserva histórico. Para el siguiente diagnóstico con opt-in explícito leer `HANDOFF_MNQ_L2_V2_DIAGNOSTICO_UNA_SESION_20260930.md`; no aplicar el GO del §3 de este documento automáticamente. Nada de outcomes sin manifiesto + OK.

**Preparado, NO MEDIDO en MNQ real.** El L2 MNQ no fue encontrado en Kaggle
conectado (sólo ticks MNQ, GC L2 y contextos NQ). La PC tiene los parquets necesarios.
No hace falta que Claude diseñe filtros ni haga research: sólo ejecutar el exporter.

## 1. Preparar sin pisar a otras sesiones

Leer AGENTS/PROJECT_INDEX/CURRENT y resolver HEAD remoto. Rama de integración
`foundation/f0b-compatibility-probe`. Una worktree propia; no `clean`, reset ni
force-push. Usar lock/venv del repo; no relajar pins. No correr en paralelo otro
proceso pesado en una PC de16GB. No tocar visor, detectores existentes ni climas.

Archivos:
- `tools/mnq_l2_prepare.py`
- `tools/streaming_escalonadas.py`
- `tools/mirror_landmark.py`
- `tools/gc_l2_fixed_price_probe.py` (P0 existente, usado como observable)
- `tests/research/test_mnq_l2_preparation.py`

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests/research -p "test_mnq_l2_preparation.py" -v
```

## 2. Una sola sesión primero (comando sin investigación ni retornos)

Desde el root del repo. Confirmar que `E:\l2_parquet` contiene contratos/parquets
y manifiestos originales; cambiar sólo raíz/output si tu PC usa otras rutas.
ART se declara explícito conforme al protocolo de contextos, no se infiere del reloj
del sistema. El exporter compara hashes y filas y acepta `price` ausente en schema
nativo después de conversión validada. No reconvierte ni edita raw.

```powershell
.venv\Scripts\python.exe tools/mnq_l2_prepare.py --root E:\l2_parquet --catalog docs/research/contract_regimes/L2_sessions_catalog_20260927.json --book-module edgelab/research/l2_phase0.py --out E:\mnq_l2_para_nube_p0 --clock ART --max-sessions 1
```

Salida para pasar a Nico/nube: `E:\mnq_l2_para_nube_p0\MNQ_targetfree_para_nube.zip`.
Incluye sólo QA/hashes, velas150t y eventos/features causales de esa sesión.
Son derivados privados propios; **no subir a repo/public ni agregar Lucid**.

Si falla: pasar traceback y `evidence.json` si existe. No reparar tiempos, ampliar
tolerancias o sustituir un dato por otro. El proceso es autónomo: no requiere
interacción continua ni diseño de Claude. No prometer un tiempo hasta medir esta primera sesión.

## 3. Tras PASS de la primera sesión

La nube revisa paridad, disponibilidad/lag, cobertura de libro y soporte del filtro.
Sólo después, ejecutar el mismo comando con `--max-sessions 0` y un output nuevo
para las52 sesiones; `--sessions YYYYMMDD,YYYYMMDD` permite lote explícito.
Con max-sessions0 se prepara toda la población, **no calcula retornos**. Se conserva
el catálogo y split17/35 sin mirar destinos futuros. Output fuera del worktree.

No ejecutar `mnq_escalonadas_grid.py` para esta propuesta ni abrir marcha/marzo/oct+.
El exporter no tiene un flag de P&L: la fase financiera requiere runner separado y
el borrador/manifiesto ratificado por Nico.

## Disponibilidad y contrato

- Velas150-LAST (prints, no volumen) sobre el L1 propio, sin unir `.Last.txt`.
- Book10 niveles por lado, sin cruce, bootstrap60s; invalidación => features null.
- Reinicio de libro/créditos al cambiar archivo. En solapamiento se corta la cola
  previa al primer timestamp **conjunto** L1/L2 siguiente y se conserva la foto
  inicial. Esto es un loader de preparación nuevo; sus filas recortadas se publican,
  no se da por equivalente al loader por tipo de los climas sin comprobarlo.
- Detector incremental a cierre; `bar_close_row` != necesariamente `available_row`.
  Si una confirmación ocurrió intrabar, no se supone conocimiento/fill allí.
- No llamar absorción o iceberg a recoveries compatibles; MBP no trae cola/IDs.
- Filtro propuesto numérico no validado: >=2 recoveries mismo lado/precio en10s
  y tamaño visible actual positivo. Nada de elegir filtro según resultado neto.

## Espejo (otro objeto)

`mirror_landmark.py` sólo registra un landmark causal de un A/B YA confirmado.
No encuentra A/B retrospectivos ni predice un destino. Default50%; A/B deben
congelarse como conocidos en sus filas disponibles. El caller debe guardar
`snapshot()` de TODOS los intentos, incluidos los invalidados sin espejo completo.
No usar los80 espejos completos como población
de predicción de formación. Esta línea queda en definición, no en backtest.

## Aporte al referente

Claude local queda reducido a ejecutar/verificar inputs; código, diseño y lectura
de evidencia quedan en nube. Aún no hay efecto ni resultado financiero de MNQ-L2.