# SUPERCARTERA v3: Pozo Limpio 63m Cero-Iteración (`Carril 2 + MACRO_RISK_PREMIA`) + Frentes No-OHLC + HRP Corregido y CSCV (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de integrar `MACRO_RISK_PREMIA` y `CRIPTO_OFI_PIT`. **`HOLDOUT A5` de todas las familias y sesiones `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **Pedido de Nico (2026-11-27):** revisar la auditoría de Claude y avanzar sumando frentes realmente independientes y limpios de iteración de `REP` para aumentar estabilidad, número de estrategias y potencia conjunta.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `CANASTA_AMPLIA`. **Pruebas:** `4` (`Super_v3_Clean63m_EQ`, `Super_v3_Clean63m_HRP`, `Super_v3_NoCME_EQ`, `Super_v3_Core_TRZV_HRP`).

Cambio respecto a falla previa: en `SUPERCARTERA v2` (`REVISION_CLAUDE.md`) la covarianza `LedoitWolf` aplicó `shrinkage_ = 1.0` colapsando `HRP_Weekly` a exactamente `EQ` (`0.25/0.333`), `Global_VolComp_M1DK` compartió señal de `VIX` con `Carril 2` (`corr = 0.48` vs `US_VZ_EVRP`) y `CRIPTO-PIT v3` usó una `REP` iterada entre `v1–v3`. En `SUPERCARTERA v3`: (1) construimos un **pozo `63m` 100% libre de iteración de `REP` y de sesgo CME** combinando exclusivamente `Carril2_Sell16` + `RP_Canasta_InvVol` (`MACRO_RISK_PREMIA`, `2006–2026-09`); (2) reemplazamos `LedoitWolf` en series ya estandarizadas por covarianza muestral regularizada (`0.85 * S + 0.15 * diag(S)`) para que `HRP` responda realmente a la estructura de correlaciones; (3) evaluamos `OFI_Canasta_InvVol` (`CRIPTO_OFI_PIT`, no-OHLC) condicionada a pasar `DESC > 0` y ortogonalidad `< 0.60` vs `XSMOM`; (4) mantenemos `Global_VolComp_M1DK` separado como transferencia VIX (no como familia independiente en potencia conjunta).

Antecedentes:
- `docs/research/auditoria_claude_20261127/REVISION_CLAUDE.md` y `RESPUESTA_REVISION_CLAUDE.md`
- `docs/research/macro_risk_premia_20261127/PREREGISTRO.md`
- `docs/research/cripto_ofi_20261127/PREREGISTRO.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia antes de abrir holdout, K36 causalidad `DESC`, K51 registro global, cero lectura de `>= 2026-10-01` ni `HOLDOUT A5`).

Potencia previa: no abre ningún `HOLDOUT A5`. Calcula por separado la potencia teórica del **pozo limpio `63m` cero-iteración (`Carril 2 + MACRO_RISK_PREMIA`)** frente al pozo dinámico multi-frente (`21–26` / `06–26`) a igual `10%` de volatilidad.

Diagnóstico de mecanismo: cero búsqueda de parámetros ni selección en `REP`. Estandarización por `SD` mensual de `DESC`, agregación semanal `W-FRI` / mensual `M` libre de spike de lunes, `HRP` ajustado exclusivamente sobre semanas `DESC` (`0.85 * S + 0.15 * diag(S)`), `CSCV (S=16, 12,870 splits)` separado en limpio largo (`06–26`), no-CME (`21–26`) y descriptivo con `CME`, `DSR (N=1..5000)` y `Bootstrap 20k semanal @ 10% vol` en Kaggle.

## Justificación económica
1. Unir primas estructurales globales multi-clase (`MACRO_RISK_PREMIA`, `20+` años limpios sin `=F`) con swing en índices US (`Carril2_Sell16`) crea un núcleo verdaderamente ortogonal de `63` meses sellados sin sesgo de vendedor ni iteración sobre `REP`.
2. Usar regularización acotada en covarianza permite que `HRP` asigne pesos distintos de `1/N` en proporción inversa al agrupamiento de correlación entre frentes.

## Cómo podría refutarse
1. Si `Pool_Clean_63m_ZeroIter` (`Carril 2 + MACRO_RISK_PREMIA`) no supera a `Carril2_Sell16` en `Sharpe`, `Calmar@10%vol` o potencia teórica sobre los `63m` sellados.
2. Si `OFI_Canasta_InvVol` falla en `DESC/REP` o si `CSCV` limpio largo (`06–26`) arroja `1/N OOS Sh <= 0.50` o `PBO >= 0.70`.
