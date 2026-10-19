# `nq_contract_regime_manifest_v1.json` (2026-09-01) — INVALIDADO

**Estado: `PROVISIONAL_INVALID_CALENDAR_DO_NOT_USE_FOR_EF0`.**

Ver `docs/research/NQ_CONTRACT_REGIME_C3D575F_AUDIT_2026-09-01.md` para la auditoría
completa (verificada de forma independiente, ver `PENDIENTE.md` P-64). Resumen: el
calendario de este manifiesto contiene 28 fechas de fin de semana, `complete_session=True`
se infería con solo ver 1 tick, y no distinguía cero explícito de fila ausente ni
mantenimiento.

Los 5 archivos de este directorio quedan como evidencia histórica del primer intento, no
como insumo válido para ningún análisis posterior. El constructor/runner corregidos están
en `edgelab/research/nq_contract_regime_manifest_build.py` (v2, fail-closed) y
`notebooks/kaggle/nq_contract_regime_manifest/nq_contract_regime_manifest_runner.py`. La
corrida real v2 sobre los 5 parquets todavía no se ejecutó (STOP, pendiente autorización).
