# Prompt para Google Antigravity — F2.9

Paso 0, obligatorio:

```text
git fetch origin research/bigtrap2-local-displacement-null
git checkout research/bigtrap2-local-displacement-null
git merge --ff-only origin/research/bigtrap2-local-displacement-null
git rev-parse HEAD
```

Si el árbol está sucio, parar. No declares que falta un archivo hasta después del fetch.
HEAD esperado incluye `2d68a2d` o posterior.

Sos el implementador local. No reinterpretés F2.8. No abras cola lejana ni Z2.

## Qué ya está. No lo reescribas

- `specs/bigtrap2_f29_bar_classifier_v0.json`
- `docs/research/BIGTRAP2_F29_BAR_CLASSIFIER_PROTOCOL_2026-08-13.md`
- `docs/research/F29_KERNEL_MECHANICS_CHECKED_2026-08-13.md`
- `edgelab/research/f29/{__init__,labels}.py`
- `tests/research/test_f29_labels.py`
- `tests/research/test_f29_runner_metrics.py`
- `diag/tasa_senales/F2.9_bar_classifier.py` si existe tras el fetch
- F2.7 runner y formal

Si `F2.9_bar_classifier.py` no está después del fetch, implementalo aditivo. Si está, no lo reescribas: corregí solo FAIL reales.

`time:1` = 1 minuto. Wick = 30% extremo del rango High−Low, no mecha japonesa.

## Datos canónicos. NO uses los Parquet de Z1

```text
6E_12-25_ticks.parquet  ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336
6E_03-26_ticks.parquet  b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76
6E_06-26_ticks.parquet  124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1
6E_09-26_ticks.parquet  6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4
```

Si el hash no coincide, ABSTAIN. No sustituyas por `fd2e358…` ni `654e006…`.

## Reglas que F2.8 rompió y F2.9 no puede romper

- `r_i = 0` entra al promedio por sesión
- no volcar empates a double_censor
- contrastes pareados por sesión, no `sqrt(se1²+se2²)`

## Tarea

1. Pasar tests:
```text
./.venv/Scripts/python.exe -m pytest tests/research/test_f29_labels.py tests/research/test_f29_runner_metrics.py -q
```
2. Correr formal:
```text
./.venv/Scripts/python.exe diag/tasa_senales/F2.9_bar_classifier.py --formal
```
3. Commitear el JSON `F2.9_formal_<sha12>.json` y un markdown de reporte. Árbol limpio. Push a la misma rama.

No kernel, holdout, P&L, tick:25, Z2, cola lejana, Kaggle.

Devolver: HEAD, tabla K0/S0/S1/S2/N0/F0, contrastes pareados, residual C, persistencia D, labels, una sola familia siguiente.
