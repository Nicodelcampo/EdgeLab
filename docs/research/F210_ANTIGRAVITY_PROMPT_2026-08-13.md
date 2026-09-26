# Prompt para Google Antigravity — F2.10

Paso 0, obligatorio:

```text
git fetch origin research/bigtrap2-local-displacement-null
git checkout research/bigtrap2-local-displacement-null
git merge --ff-only origin/research/bigtrap2-local-displacement-null
git rev-parse HEAD
```

Si el árbol está sucio, parar. No declares que falta un archivo hasta después del fetch.
HEAD esperado incluye `eecfec4` o posterior.

Sos el implementador local. No reinterpretés F2.9. No abras residual de zona, aVol, cola lejana ni Z2.

## Qué ya está. No lo reescribas

- `specs/bigtrap2_f210_regime_window_v0.json`
- `docs/research/BIGTRAP2_F210_REGIME_WINDOW_PROTOCOL_2026-08-13.md`
- `edgelab/research/f210/{__init__,labels}.py`
- `tests/research/test_f210_labels.py`
- F2.9 runner: `diag/tasa_senales/F2.9_bar_classifier.py`
- F2.7 race/lifecycle/load/firewall

`time:1` = 1 minuto. Wick = 30% extremo del rango High−Low. Sello = `S1`, no el kernel.

## Datos canónicos. NO uses los Parquet de Z1

```text
6E_12-25_ticks.parquet  ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336
6E_03-26_ticks.parquet  b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76
6E_06-26_ticks.parquet  124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1
6E_09-26_ticks.parquet  6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4
```

Si el hash no coincide, ABSTAIN. No sustituyas por `fd2e358…` ni `654e006…`.

## Tarea

Implementá aditivo `diag/tasa_senales/F2.10_regime_window.py`.
Reusá F2.7/F2.9: `P_mode`, `first_passage_race`, `session_mean_map` con ceros, contrastes pareados, carga, firewall.
Reusá F2.10: `is_s1`, `is_t1`, `decide_labels`.

Brazos: `T1_all`, `T1_not_S1`, `T1_and_S1`, `S1_isolated`, `P1`, `T1_after_K0`, `T2`, `T_minus1`.
Contrastes: `T1_not_S1 − P1`, `T1_and_S1 − S1_isolated`, `T1_after_K0 − T1_after_S1`.
201 sesiones. JSON `F2.10_formal_<sha12>.json` y markdown.
No kernel, holdout, P&L, tick:25, Z2, aVol, residual de zona.

```text
./.venv/Scripts/python.exe -m pytest tests/research/test_f210_labels.py -q
./.venv/Scripts/python.exe diag/tasa_senales/F2.10_regime_window.py --formal
```

Devolver: HEAD, tabla de brazos, contrastes pareados, labels, una sola familia siguiente.
