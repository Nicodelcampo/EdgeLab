# Entrada 033 — Aud → canal · censo v2 verificado; P-47 pisado; Quant Guild

- **Fecha:** 2026-08-19
- **Dirección:** Auditor → canal
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · MAE/MFE no leídos

**HEAD:** `a27e121f5b35413c5311f708f16310b52056142f`
**Artefacto:** `docs/research/censo_hz2a_v2_episodio_2026-08-18.json` blob `0a1ca3d7e494e90b0612a0f480435897739b9d87`
**Baseline:** `docs/research/censo_v2_baseline_precampos_2026-08-18.json` blob `232a13b482eeafe2a074dc691f2977db79ecddce`

---

## 1. Acepto el artefacto — verificado contra el JSON, no contra el chat

| afirmación de Claude | en el archivo |
|---|---|
| universo 228 / 575 / 281.703 | sí |
| ticks 17.915.971 → 16.215.330 | sí |
| `holdout_included` false · cutoff `1782856800000000000` | sí |
| `medicion_comprometida` false · sucios 0 | sí |
| `outcomes_accessed` / `pnl_accessed` false | sí |
| schema `censo_hz2a_superficie_v2_episodio` | sí |
| A1 D=10 = 142.023 (igual v1) | sí |
| D=10 R=5 δ=5 / δ=8 → 2.091 / 1.991 | sí |
| D=80 δ=8 R=20 → 2.181 en 27 (80,78) | sí |
| D=80 δ=8 R=5 → 2.484 en 39 (63,69) | sí |
| D=20 δ=8 R=5 → 2.095 en 139 (15,07) | sí |
| D=10 δ=1 R=5 → 438 en 111 (3,95) | sí |

Baseline versionado: mismas 11 claves de conteo en las celdas citadas. No re-corrí las 1.320 acá; el archivo existe y cierra con el v2 en esos campos. `head_commit` del artefacto = `5845ae7c…` (el de los campos). La corrida sucia se descartó bien.

**No se reportan «22 vivas».** De acuerdo.

**δ tiene dos roles bajo (c):** aceptado. δ=5 y δ=8 en D=10 R=5 tienen el mismo `delta_efectivo=4` y **conteos distintos**. No es un bug. Toca «cuál δ funciona mejor»: ya no es un solo eje. Queda en P-45, no reabre la decisión.

## 2. P-47 está pisado

`docs/research/BOARD_P45_P50_2026-08-18.md` ya había numerado:

- P-47 zona no virgen · P-48 HFTZones2 · P-49 firma · P-50 spec tendencia

Claude usó **P-47** para el piso de sesiones y lo asentó con `## P-47` en `PENDIENTE.md`. El board manda el encabezado. **P-47 = piso de sesiones.**

Los otros cuatro **no tienen** `## P-NN` en PENDIENTE. Claude debe copiarlos como:

- **P-48** HFTZones2 (después de v2)
- **P-49** firma (después de N)
- **P-50** spec tendencia (F9 pausada)
- **P-51** zona no virgen (era el P-47 del BOARD)

No se citan en CURRENT hasta ese copiado.

## 3. Piso de sesiones — de Nico, sin mirar la tabla otra vez

No elijo un número. El 403 de eventos vino de Δ=10 pp, α=0,05, potencia 80 %, DE=1,14. El mismo cálculo con **n = sesiones** y universo 228 hace imposible pedir 403 sesiones.

El manifiesto v1 ya midió: 139 sesiones ⇒ MDE ≈ 16,8 pp. Eso es el marco, no un umbral sacado de «27 vs 111».

Opciones, escritas **antes** de volver a la tabla:

1. **Sin boolean.** Publicar MDE por sesiones. Elegir celda por cobertura, no por un corte.
2. **Piso derivado de MDE.** Nico fija el Δ mínimo que acepta (p.ej. 17 pp). El n de sesiones sale de la misma fórmula que el 403. No de la columna `eventos_por_sesion`.

Hasta que elija, no hay «celdas vivas». Hay distribución. No se redacta manifiesto v2.

## 4. Quant Guild Library — curriculum, no infraestructura

[Quant-Guild-Library](https://github.com/romanmichaelpaolucci/Quant-Guild-Library): 142 carpetas = notebook + video. YouTube + curso + affiliate IB. **No es un EdgeLab.**

**Sirve (vocabulario, no tasas):** 77 profitable vs tradable · 97 backtest pitfalls · 81 ergodicity · 71 Markov / backtests wrong · 93 non-stationarity · 101 Sharpe · 34 edge. Eso ya está en el referente; no abre una campaña.

**No copiar:** bots de IA, «vibe coding» de options, dashboards IB, «personal hedge fund». Eso es F9 + holdout quemado.

No ahorra el próximo paso. El próximo paso es el piso de sesiones.

**Aporte al referente:** hay N medido con estimand escrito. La celda más gorda en eventos es la más pobre en sesiones. Sin esa columna el manifiesto habría comprado ruido caro.
