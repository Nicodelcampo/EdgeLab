# Cierre F2.7–F2.10 y herramientas reutilizables (2026-08-13)

Estado: `BIGTRAP2_MAGNET_LINE_CLOSED`
Rama: `research/bigtrap2-local-displacement-null`
HEAD al cerrar: `00dc750d7f2bf8ff5ffc764972aaecb4e2dfcc56`
Audiencia: cualquier persona o LLM que continúe EdgeLab.

Este archivo es el acta. Los informes de Antigravity son evidencia, no veredicto.

## 0. En una frase

Había una marca geométrica real. No era un imán de zona, no era una ventana de 1–2 minutos y no era exclusiva de BigTrap2. Era, como mucho, el comportamiento asimétrico después de velas extremas. El indicador original sigue en el repo; esa tesis no.

## 1. Qué se midió

Universo congelado: 6E, 201 sesiones, `time:1` = M1, Parquet canónicos F2.7.

```text
6E_12-25  ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336
6E_03-26  b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76
6E_06-26  124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1
6E_09-26  6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4
```

No usar los exports Z1 (`fd2e358…` / `654e006…`).

Corte: `2026-06-30`. Holdout y P&L no se abrieron.

## 2. Cadena de hechos (leer juntos)

### F2.7 — la carrera es real

- Δ ≈ +0.048, IC [+0.031, +0.066], 15.947 zonas, 201 sesiones.
- Real y espejo están a la **misma** distancia del close. “Gana porque está más cerca” es imposible.
- Artefacto: `diag/tasa_senales/F2.7_formal_93c2e3f3ac44.json`.

### F2.8 — no es imán

- El efecto no muere en `d ≥ 6` (Δ ≈ +0.077).
- Un control sin zona, misma geometría, da casi lo mismo. El contraste cruza cero.
- Ocupación visitada ≈ 29% ≈ azar. `isolated_rate` bajo ≠ rango tapado.
- Tras el primer toque, ~72% atraviesa / ~27% rebota: no es freno típico.
- `OPEN_FAR_ZONE_FAMILY` no debió encenderse. Etiqueta válida: clasificador de barra.
- Defectos del runner F2.8 (no reabrir para “corregir el corte lindo”): tiraba `r_i=0` del promedio; mezclaba empates con doble censura; contraste no pareado.

### F2.9 — el kernel no es el mejor sello

Probe `P_mode`: d=2, ancho=1, lado = banda extrema del **rango** (no mecha japonesa).

```text
S1   +0.038   [+0.028, +0.049]   vela extrema + vol ≥ mediana
F0   +0.042   [+0.031, +0.054]   TRAP / footprint
K0   +0.021   [+0.003, +0.040]   creadora BigTrap2
N0   +0.018   [+0.002, +0.034]   no-creadora emparejada
```

`K0 − S1` es negativo. `F0 ≈ S1`. `K0 ≈ N0`.
Residual de zona: +0.026, IC arranca en +0.0015, MDE 0.034. No se promueve.
`t+1` se vio fuerte **antes** de controlar clustering y placebo.

Wick del kernel = 30% extremo de High−Low, no (High − max(Open,Close)).

### F2.10 — no hay ventana exclusiva

```text
T1_not_S1     +0.023   minuto después de S1, y esa barra no es extrema
P1            +0.043   minuto después de una no-S1 parecida
diferencia    −0.020   cruza cero
```

Racimo `T1_and_S1` ≈ `S1_isolated`. Kernel no gana a S1 en la ventana.

`OPEN_PRE_STAMP_REVERSAL` **enciende por letra y no se promociona**:
`T_minus1` es sólo −0.009. El contraste −0.12 lo carga `P_minus1` = +0.112
en 14k barras vs 82k del tratamiento. El placebo se construye con la no-S1
más cercana en quintiles; el vecino suele ser la propia S1 o el racimo.
HEAD real del formal: `00dc750d7f2bf8…` (no el SHA truncado del informe).

## 3. Qué queda cerrado

- BigTrap2 como imán de zona.
- Campaña de cola lejana / 17 frames / Z2.
- Ventana de timing `t+1`/`t+2` como producto.
- Cruce BigTrap2 × aVol.
- PIT / Kaplan–Meier / Cox sobre este objeto.
- Kaggle de ticks reales (`NO_UPLOAD`).
- Perseguir `t−1` o relajar hashes.

## 4. Qué sigue siendo útil

Una vela extrema (`S1`: rango ≥3, banda ≥30% del rango, vol ≥ mediana) marca
una carrera `P_mode`. No es exclusiva del kernel. No es un sistema. Es un
**sello barato de contexto**, reutilizable si otra familia (aVol, gap, POC)
pregunta “¿esta barra es extrema?”.

Indicadores del registry, intactos:

| Indicador | Estado |
|---|---|
| BigTrap2 | Kernel vivo. Tesis de imán cerrada. Puede quedar como disparo visual. |
| aVolCellPOI2 | Segunda familia. Portado v2.1. Sin nulo propio. Siguiente candidato. |
| VolTicksPOC2, Gaps2, HFTZones2, AACloseOpenDiffs | En registry. Sin campaña. No abrir en pack. |

## 5. Herramientas a reutilizar (no reescribir)

### Datos y firewall

- Carga canónica + hashes: `data_root()`, `parquet_file_sha256`, tabla de arriba.
- Reloj: sesión CME 17:00 CT (`session_date_cme` en ZAMR; no fecha civil).
- Firewall de corte: `corte_del_sello()`, `outcomes_accessed=false`.
- `time:1` = `build_time_bars(ticks, minutes=1)`. Ticks sólo para footprint y desempate.

### Carrera y ciclo de vida

- `construir_reflejo`, `first_passage_race`, `zone_lifecycle` (F2.7).
- `r_i ∈ {+1,−1,0}`. Los ceros **entran** al promedio por sesión.
- Empates ≠ doble censura. No volcar residuales a `double_censor`.
- Contrastes **pareados por sesión**, no `sqrt(se1²+se2²)`.
- HAC Bartlett: `hac_bartlett_ic`.

### Sello y probe

- `wick_fracs`, `probe_side`, `probe_interval`, `is_s1` (`edgelab/research/f29`, `f210`).
- `P_mode` es un probe nuestro, no el span del kernel.

### Gobernanza de corridas

- Fetch antes de ABSTAIN. Verificar `git cat-file` **después** del fetch.
- No fiarse de SHA truncados de informes (pasó en F2.8, F2.9, F2.10).
- Spec sellada + labels + tests **antes** de la formal.
- Una etiqueta `OPEN_*` ≠ campaña. Auditar letra vs espíritu vs placebo.
- Un `OPEN_*` abre **una** spec. No 17 frames.

### ZAMR / Kaggle

- Builder Z1 v2 y hardening se conservan. Z1 formal del repo: no ejecutado.
- Notebook 01: fail-closed si licencia `NO_UPLOAD`.
- Kaggle: métodos (folds, ledger, anti-leakage), no ticks de 6E.
- Panorama: página Notion del contrato + addendum 2026-08-13.

## 6. Cómo seguir, si se sigue

1. No otro prompt de BigTrap2-timing.
2. Si hay campaña nueva: **aVolCellPOI2 solo**, target-free, nulo propio, mismas 201 sesiones si aplica, sin cruce.
3. Gaps / HFT / POC / AA: sólo si una pregunta única los necesita, no como pack.
4. 2.ª visita / ruptura condicional: no medida. Sólo si hay objeto; población y control fijos; sin “signos” a posteriori.
5. Réplica ES: después de saber qué objeto se replica. Hoy no hay objeto de zona.

## 7. Archivos ancla

```text
specs/bigtrap2_local_reflection_null_v2.json
specs/bigtrap2_f28_distance_coverage_v0.json
specs/bigtrap2_f29_bar_classifier_v0.json
specs/bigtrap2_f210_regime_window_v0.json
diag/tasa_senales/F2.7_nulo_reflexion_local.py
diag/tasa_senales/F2.8_atlas_residuales.py
diag/tasa_senales/F2.9_bar_classifier.py
diag/tasa_senales/F2.10_regime_window.py
diag/tasa_senales/F2.7_formal_93c2e3f3ac44.json
diag/tasa_senales/F2.9_formal_5d5a58b06174.json
diag/tasa_senales/F2.10_formal_b366597f20ee.json
edgelab/bridge/indicators/{bigtrap2,avolcellpoi2,gaps2,hftzones2,voltickspoc2,aacloseopendiffs}.py
```
