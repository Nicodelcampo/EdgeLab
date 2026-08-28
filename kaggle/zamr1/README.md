# ZAMR-1 — runbook vigente

## Estado

- Z0 sintético: PASS con hardening.
- Z1 builder v2: implementado y todavía no ejecutado formalmente.
- Licencia: `NO_UPLOAD`.
- Z2: no autorizado.

## Regla legal fail-closed

`NO_UPLOAD` significa que los ticks reales no se cargan a Kaggle ni a otro tercero. Un `operational_override` o aceptación de riesgo no equivale a permiso contractual. Notebook 01 contiene un gate que falla antes de buscar o leer Parquet mientras la decisión no sea `RAW_ALLOWED`.

No crear un Dataset Kaggle con `6E_06-26_ticks.parquet` ni `6E_09-26_ticks.parquet`.

## Z1 local

El ejecutable permitido es `zamr1_z1_bigtrap2_defaults_v2` en `edgelab/research/zamr1/z1_builder.py`, usando:

- `specs/zamr1_z1_pilot_plan_2026-08-12.json`;
- los dos Parquet cuyos hashes están congelados en el plan;
- árbol Git limpio;
- únicamente BigTrap2 default;
- frames `5, 10, 25, 50, 100, 200`;
- sin outcomes, retornos, P&L ni holdout.

Ejemplo desde un checkout gobernado:

```bash
python -m edgelab.research.zamr1.z1_builder \
  --plan specs/zamr1_z1_pilot_plan_2026-08-12.json \
  --data-root data/nt8/6E \
  --out-dir artifacts/zamr1-z1
```

La corrida debe producir Parquet derivados, manifests, validación estructural y reporte de recursos. Ningún PASS local autoriza por sí solo subir esos derivados; M0 debe especificar expresamente el tratamiento permitido.

## Kaggle futuro

Notebook 01 queda preparado pero bloqueado. Sólo podrá despertarse si una decisión contractual documentada cambia a `RAW_ALLOWED`, mantiene el holdout físicamente ausente y conserva Internet Off, privacidad y hashes congelados.
