# k36 — auditoria de resultados y revision del informe de Gemini (2026-10-17)

Fuente: salida cruda del kernel (`k36_summary.json`, sha256 `86bc2416ac02c3b77e80bf3f4798add34435ad56e16ce0c73e9ccdae9cfd27ca`) y codigo del kernel
(`tools/k36_audit/kernel_k36_v1_source.py`, sha256 `eff8bdf6ead2f3f4da1b1456fb24554bfc4fd32bc6d6eca678ef1739e3e3d198`). No se leyo el informe de Canvas.
Tabla lado a lado: `K36_WF178_VS_OOS32_TABLA.md` (generada por `tools/k36_audit/wf_vs_oos_table.py`).

## Veredicto
Sin evidencia de edge. En el walk-forward de 178 sesiones (2 trades/dia) las 7 variantes pierden despues de costos: neto limite inmediato entre -0.61 y -1.53 ticks
(U1), neto pasivo entre -1.26 y -2.25. El nulo de desplazamiento circular no se rechaza (p 0.58 / 0.45 / 0.18).

## Verificado contra el codigo
| afirmacion | resultado |
|---|---|
| Los numeros de C2/U1 (113 trades, +1.38 neto, PF 1.21) | **Ciertos**, pero son las ultimas 32 sesiones; en el walk-forward C2 da **-0.61** (z -0.82) |
| El ranking divide por sqrt(stop) y empuja a stops chicos/objetivos lejos | **Cierto** (`_compute_ev_score`, `ev_ticks / sqrt(max(stop, 6))`); ademas `p_w = 0.65*p_tp1 + 0.35*p_e1` es una mezcla ad hoc, no una probabilidad calibrada |
| `target_mirage_flag` tuvo 0 activaciones porque exigia cuerpo/rango >= 0.72 y |delta| >= 0.42 | **Falso respecto del codigo**: la regla real es `m_grav<0.85 & imbalance>0.50 & toque_fija600<=0` (o `m_grav<0.65 & imbalance>0.60`). La causa de los 0 casos **no esta explicada** |
| Barrer sube el win rate +9.67 pp | Cierto **contra escalera** (36.1 % vs 26.5 %); contra el promedio del universo (38.05 %) el barrido **no mejora** |
| "Se verifica de forma contundente" | No: dos cortes post hoc, sin SE ni test, dentro de un barrido con 44 pruebas |
| La "zona dulce" R in [1.35,1.85] | C1A vs C0 en el walk-forward: neto -0.65 vs -0.79 (0.14 ticks, ruido) |

## Defecto tecnico corregido (parche, no ejecutado)
`verify_causal_outcome_and_prefix_tests` verificaba la disponibilidad de zonas HFT en `cls_b` de la primera zona del corredor, temprano en la sesion:
resultado `n_hft_zones_verified_at_prefix = 0`, el `assert len(a) == len(b)` pasaba como `0 == 0`. El parche (`prefix_test_nontrivial.patch`) corta tarde en varias
sesiones, exige >= 200 zonas verificadas en >= 5 sesiones y compara la identidad (start_ts, end_ts, bucket, dir) de cada zona. **No se ejecuto**: requiere el kernel y los datos en Kaggle.
Si el parche encuentra una discrepancia real, el resultado de k36 pasa a cuestion de causalidad, no solo de potencia.

## Lo que queda abierto
- Origen de los 0 casos de `target_mirage_flag`.
- Eleccion de trades por ML (regresion logistica con `C=0.15`) sin calibracion verificada.
- Inconsistencia entre universos solapados (C1B: -0.20 en U1, -0.59 en U3, +0.88 en U2).
