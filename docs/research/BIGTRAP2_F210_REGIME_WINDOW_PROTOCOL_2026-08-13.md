# F2.10 — Ventana de régimen después de una vela extrema (2026-08-13)

Estado: `PREREGISTERED_NOT_RUN`
Spec: `specs/bigtrap2_f210_regime_window_v0.json`
Hereda: F2.9 auditada. Mismas 201 sesiones. Mismos Parquet canónicos. Mismo `P_mode`. Mismo `r_i`.

## 0. Por qué esta y no el residual de zona

F2.9 dejó tres hechos que hay que leer juntos:

1. En `P_mode`, `S1` le gana a `K0`. La regla OHLC es el sello, no el kernel.
2. `t+1` / `t+2` después de una creadora tienen la carrera más limpia de toda la corrida.
3. El residual de zona enciende por `ci95_lower = +0.0015`. El MDE es `0.034`. No se promueve. No abre aVol × BigTrap2.

La pregunta no es “¿la zona todavía suma un poquito?”. Es: **¿el minuto siguiente es especial, o sólo estamos midiendo otra vela extrema pegada a la anterior?**

## 1. Pregunta

> Después de una barra `S1`, ¿`P_mode` en `t+1` sigue vivo aunque esa barra **no** sea `S1`? Si el efecto vive sólo cuando `t+1` también es `S1`, era racimo, no ventana.

## 2. Sello y probe

Sello, por defecto: `S1`

```text
range_ticks >= 3
max(upper_frac, lower_frac) >= 0.30 del rango High−Low
volume >= mediana de la sesión
```

No hace falta BigTrap2 para disparar. `K0` entra sólo en el contraste “¿el kernel hace falta para la ventana?”.

Probe: el mismo `P_mode` de F2.9, computado **en la barra evaluada**, no en la del sello.
`r_i = 0` entra. Contrastes pareados por sesión.

## 3. Familias. No hay producto cartesiano

### A — Partir `t+1`

| Brazo | Quién entra |
|---|---|
| `T1_all` | `b` tal que `b-1` es `S1`, misma sesión |
| `T1_not_S1` | eso, y `b` **no** es `S1` |
| `T1_and_S1` | eso, y `b` también es `S1` |
| `S1_isolated` | `S1` cuyo `b-1` no es `S1` |

`T1_not_S1` es el objeto de timing. `T1_and_S1` es el racimo.

### B — Placebo del minuto siguiente

`P1`: `b` cuyo `b-1` es una no-`S1` emparejada a una `S1` por sesión, quintil de rango, `close_loc` y volumen, más cercana en tiempo.

Si cualquier minuto siguiente ya da `+0.05`, no hay ventana.

### C — ¿Hace falta el kernel?

`T1_after_K0 − T1_after_S1`, pareado. Si cruza cero, BigTrap2 no es el disparo.

### D — `t+2` y `t−1`

`t+2` se reporta. `t−1` salió negativo en F2.9: se informa, no se promociona, salvo que pierda contra su propio placebo (`ci95_upper < 0`).

## 4. Etiquetas

```text
OPEN_POST_STAMP_WINDOW     T1_not_S1 vive y le gana al placebo
OPEN_CLUSTER_ONLY          sólo vive cuando t+1 también es S1
KEEP_KERNEL_FOR_WINDOW     la ventana después de K0 le gana a la de S1
OPEN_PRE_STAMP_REVERSAL    t−1 pierde contra su placebo
CLOSE_WINDOW
CONTINUE_AMBIGUOUS
```

Si hay varias, la primaria es `OPEN_POST_STAMP_WINDOW`. Una sola spec después. No Z2. No aVol. No residual de zona.

## 5. Cerrado

Kernel, holdout, P&L, `tick:25`, cola lejana, Kaggle conjunto, tirar ceros, IC de SE independientes como primario.
