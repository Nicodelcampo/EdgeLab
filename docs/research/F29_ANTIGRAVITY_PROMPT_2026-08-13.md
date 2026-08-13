# Prompt para Google Antigravity — F2.9

Paso 0: `git fetch origin research/bigtrap2-local-displacement-null` y ff-only.
HEAD esperado incluye `ecf2b16` o posterior. Si el árbol está sucio, parar.

Sos el implementador de F2.9. No reinterpretés F2.8. No abras cola lejana ni Z2.

## Qué ya está. No lo reescribas

- `specs/bigtrap2_f29_bar_classifier_v0.json`
- `docs/research/BIGTRAP2_F29_BAR_CLASSIFIER_PROTOCOL_2026-08-13.md`
- `docs/research/F29_KERNEL_MECHANICS_CHECKED_2026-08-13.md`
- `edgelab/research/f29/labels.py`
- `tests/research/test_f29_labels.py`
- F2.7 runner y formal

`time:1` = **1 minuto** (`build_time_bars(..., minutes=1)`). El footprint y el desempate de la carrera usan ticks. El lifecycle OHLC es M1. No cambies eso en F2.9. No pases a tick:25.

Wick del kernel = banda extrema del 30% del **rango High−Low**, no mecha japonesa.

## Datos canónicos F2.7

```text
6E_12-25_ticks.parquet  ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336
6E_03-26_ticks.parquet  b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76
6E_06-26_ticks.parquet  124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1
6E_09-26_ticks.parquet  6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4
```

## Tarea

Implementá aditivo `diag/tasa_senales/F2.9_bar_classifier.py`.

Reusá F2.7: `construir_reflejo`, `first_passage_race`, `zone_lifecycle`, `agregar_por_sesion`, `hac_bartlett_ic`, carga, firewall.
Reusá F2.9: `probe_side`, `probe_interval`, `decide_labels`.

Reglas que F2.8 rompió y F2.9 no puede romper:
- `r_i = 0` entra al promedio por sesión;
- no volcar empates a double_censor;
- contrastes **pareados por sesión**, no `sqrt(se1²+se2²)`.

Familias, en este orden:
A retrato de barra (sin carrera);
B escalera P_mode: K0, S0, S1, S2, N0;
C residual zona vs P_mode en la misma creadora;
D persistencia t−2…t+2;
E F0 = barras con TRAP aunque vol < 30.

S0/S1/S2 son OHLC+volumen. No les pongas imbalance de footprint.
P_mode: d=2, width=1, lado = banda extrema dominante.
S0: range_ticks>=3 y max(upper_frac, lower_frac)>=0.30 del **rango**, no de la mecha japonesa.

201 sesiones. Labels con `decide_labels`. Un JSON `F2.9_formal_<sha12>.json` y un markdown.
No kernel, holdout, P&L, tick:25, Z2, cola lejana, Kaggle.

Tests: probe, S0, ceros incluidos, contraste pareado, labels.

```text
./.venv/Scripts/python.exe -m pytest tests/research/test_f29_labels.py -q
./.venv/Scripts/python.exe diag/tasa_senales/F2.9_bar_classifier.py --formal
```

Devolver: HEAD, tabla de peldaños, contrastes pareados, labels, una sola familia siguiente.
