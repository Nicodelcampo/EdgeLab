# Resultado Gate 1 GC all5 — replicación expandida post-outcome

Fecha: 2026-08-26

## Veredicto ejecutable

```json
{
  "status": "COMPLETE_GATE1_ALL5_POST_OUTCOME_REPLICATION",
  "decision": "EXPANDED_PRIMARY_POSITIVE_NOT_NONINFERIOR_TO_BT2",
  "n_sessions": 234,
  "CAMPAIGN_OUTCOMES_OPENED": true,
  "confirmatory_eligible": false,
  "promotion_eligible": false,
  "EDGE_DECLARED": false
}
```

La muestra contiene los cinco contratos y 234 fechas CME no solapadas. El tamaño supera el objetivo nominal de 133, pero no restaura el firewall confirmatorio ya abierto.

## Contrastes Wild Cluster Bootstrap 95%

| Contraste | Punto | IC 95% | Gate |
|---|---:|---:|---|
| K_ABS − N_RAND | +4.84 ticks | [+3.36, +6.32] | Positivo y supera 2,5 ticks |
| K_ABS − K_ABS_SHUFFLE | +1.74 ticks | [+0.17, +3.31] | Positivo al 95% |
| K_ABS − K_BT2 | +0.10 ticks | [-3.93, +4.16] | No demuestra no-inferioridad/superioridad |

Decisión: `EXPANDED_PRIMARY_POSITIVE_NOT_NONINFERIOR_TO_BT2`. K_ABS supera los dos nulls declarados en esta muestra, pero no supera ni demuestra no-inferioridad frente a BigTrap2.

## Conteos

- Eventos K_ABS elegibles: 16,940.
- Eventos K_BT2 elegibles: 5,262.
- Exclusiones de fill/horizonte registradas: 0.
- Checkpoints completos y validados contra runtime: 234/234.

## Descriptivo por contrato

| Contrato | Sesiones | Media vs N_RAND | Media vs BT2 | Media vs shuffle | Fracción vs N_RAND > 0 |
|---|---:|---:|---:|---:|---:|
| GC 12-25 | 82 | +3.30 | +3.42 | +0.55 | 65.9% |
| GC 02-26 | 44 | +4.33 | +0.14 | +1.15 | 68.2% |
| GC 04-26 | 42 | +7.23 | -4.65 | +5.44 | 64.3% |
| GC 06-26 | 42 | +6.44 | +2.86 | +1.99 | 69.0% |
| GC 08-26 | 24 | +4.04 | -7.81 | -0.04 | 75.0% |

Los renglones por contrato son descriptivos, no gates contract-by-contract. No corresponde seleccionar o eliminar un tramo después de observarlo.

## Interpretación corregida

`d_hat = median(MFE) - median(MAE)` mide excursiones de trayectoria. No es una estrategia de salida ni P&L realizado, no descuenta comisiones y no contiene slippage. Por eso el resultado no se describe como “ticks netos”, “alfa científicamente probado” ni prueba general de ausencia de suerte o ruido.

La afirmación permitida es más estrecha: en la muestra expandida post-outcome, K_ABS tiene un contraste positivo frente a los nulls especificados bajo el horizonte y la ponderación congelados. La comparación con BT2 continúa inconclusa.

## Reproducibilidad

Cada sesión se ejecutó en un proceso fresco, con checkpoint atómico, hash del runtime y warm-up causal de la sesión válida previa. Los buckets de 25 ticks se reinician en cada frontera CME; los 234 checkpoints se invalidan si cambia el runtime, el registro de muestra o el registro de inputs.

Resultado completo SHA-256 de payload: `a307a12c441d82877590a20c59aa1079d590de2cdbb6d55180caaec21622ca53`.

Resumen JSON SHA-256: `38fd7267ae8f7cd7503a28bff8ab32fcec60a8c027d7b263bcbd3b9e674638cc`. Los 234 renglones por sesión se publican en cinco CSV, uno por contrato.
