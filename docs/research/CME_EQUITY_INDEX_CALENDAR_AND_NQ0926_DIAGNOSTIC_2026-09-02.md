# Calendario CME Equity Index y diagnóstico NQ 09-26

Fecha: 2026-09-02. Autorizaciones de Nico registradas: diseño separado de
calendario/cobertura y diagnóstico target-free de NQ 09-26.

## Decisión de diseño

`market_session_expected` y `source_capture_complete` son evidencias distintas.
El calendario oficial define apertura/cierre esperados; no demuestra que la
fuente capturó el intervalo. `active_minutes` queda como diagnóstico y nunca
como certificación.

El calendario `cme_equity_index_session_calendar_v1` exige:

- bounds CT explícitos para cada excepción;
- URL oficial `cmegroup.com`, SHA-256 del documento capturado y fecha de acceso;
- fallo si una fecha marcada para revisión no tiene override;
- `CLOSED` con bounds nulos;
- no inferir cobertura de fuente.

La evidencia de captura exige particiones esperadas/presentes, status de
extracción y hash. Un contrato con pocos ticks puede tener captura completa;
una sesión con 1380 minutos activos puede provenir de una fuente incompleta.

## Fuentes primarias

- https://www.cmegroup.com/trading-hours.html
- https://www.cmegroup.com/trading/equity-index/rolldates.html

CME declara que los horarios festivos están sujetos a cambios y normalmente se
finalizan cerca de cada feriado. Por ello no se certifica todavía un calendario
real hasta capturar y hashear cada horario aplicable a Equity Index.

## Diagnóstico autorizado

El runner `nq0926_maintenance_diagnostic_runner.py` lee solo el parquet
NQ 09-26 pre-holdout con SHA-256
`1030715b216210e9443077212fd2e26303966c031243167d097d8465f81fb64f`.
Agrupa los ticks 16:00-17:00 CT por trade date, minuto, `source_file`, rangos de
`source_row` y `sequence`, y registra la distribución `ts_local_ns-ts_utc_ns`.
No asigna causa automáticamente.

Una corrida diagnóstica completada devuelve exit code 0 aunque encuentre una
anomalía; `execution_status` y `scientific_status` quedan separados. Exit no
cero se reserva para error técnico/procedencia.

Comando después de publicar el commit:

```bash
python notebooks/kaggle/nq_contract_regime_manifest/nq0926_maintenance_diagnostic_runner.py \
  --expected-code-commit <FULL_COMMIT_SHA>
```

Prohibido: EF0, indicador, outcomes, P&L y holdout.
