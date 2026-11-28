# CRIPTO-PIT v3: Microestructura Basis (premiumIndex) + Beta-Neutralización + 5 Mecanismos Escalonados (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de descargar `premiumIndexKlines` y antes de medir resultados. **HOLDOUT A5 de `CRIPTO_BINANCE` (`18m`) y sesiones `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **Pedido de Nico (2026-11-27):** avanzar en frentes de alta expectativa neta, estabilidad, decorrelación y mínimo drawdown sin esperar forward.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `CRIPTO_BINANCE`. **Pruebas:** `6` (`5` mecanismos ortogonales escalonados a `5d` + `1` canasta causal `CR3_Canasta_InvVol`).

Cambio respecto a falla previa: en `cripto_pit.py` (línea 177) la neutralización `.sub(mean)` derramaba pesos hacia monedas planas y `EMA 4H` introducía rotación extrema; en `cripto_pit_v2.py` `FundingCarry` concentraba `73%` en `5` días y sufría pérdidas fuertes en 2025, mientras `TSMOM` dependía de días extremos (`83%` en 5 días). En `CRIPTO-PIT v3`: (1) incorporamos **prima perpetuo-spot real (`premiumIndexKlines/1d`)** combinada con `funding` (`CR3_Basis_Carry_Stag5d`), (2) implementamos **beta-neutralización causal rolling 30d frente a BTC** (`CR3_XSMOM_BetaNeut_Stag5d`), (3) **Betting-Against-Beta / Low-Vol defensivo** (`CR3_BAB_LowVol_Stag5d`), y (4) **momentum residual 21d contra 2 factores (`BTCUSDT` + `ETHUSDT`)** (`CR3_ResidMom_21d_2F_Stag5d`), todos sobre `226` monedas crypto PIT ex-TradFi (`vol60 >= 25%`, histéresis `<=20/>25`, `5` tranches escalonadas).

Antecedentes:
- `docs/research/cripto_pit_20261127/UNIVERSO_PIT.csv` y `RESULTADO.md`
- `docs/research/auditoria_claude_20261127/RESULTADO.md` y `CRIPTO_PIT_V2.json`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia antes de abrir holdout, K36 causalidad por prefijo, K51 registro global, cero lectura de `>= 2026-10-01` ni `HOLDOUT A5`).

Potencia previa: no abre `HOLDOUT A5` (`18m` sellados). Sobre `DESC (39m) + REP (12m) = 51m`, un `Sharpe` observado de `0.85–1.05` aporta potencia teórica conjunta con `Carril 2 (63m)` de `~0.30 / ~0.46 / ~0.72`.

Diagnóstico de mecanismo: sin grilla de optimización. Los 5 mecanismos se fijan de antemano con ventana `21d`/`30d`/`5d`, rebalanceo escalonado `5d`, patas activas `top-4 / bot-4` (`gross = 1.0`), fricción evaluada en `10, 20 (base), 30, 40 bps RT + funding real`, y **regla fija causal de canasta**: entran exclusivamente mecanismos con `DESC usd_mes > 0` y `top5_days_share_DESC < 0.65`, ponderados por `1/sd` mensual ajustado sólo en `DESC`.

## Justificación económica
1. La dispersión cross-sectional de momentum 21d en perpetuos crypto limpia de beta (`BetaNeut` y `ResidMom 2F`) captura flujo tendencial relativo con `beta_BTC ~ 0` y baja concentración.
2. El diferencial `premiumIndex` (basis perp-spot) junto con `funding` refleja exceso de apalancamiento minorista; vender los extremos caros (vetando rupturas de 10d para evitar short squeezes) y comprar activos defensivos de menor beta/volatilidad (`BAB`) aporta retornos estructuralmente ortogonales al momentum.

## Cómo podría refutarse
1. Si a `20 bps RT + funding` la canasta `CR3_Canasta_InvVol` falla en `REP (12m)` o cae por debajo de `Sh = 0.50` en `DESC+REP`.
2. Si los nuevos mecanismos (`Basis_Carry`, `BAB_LowVol`, `ResidMom_2F`) tienen correlación `> 0.70` con `XSMOM` o concentración `top5_days_share > 0.65`, demostrando que no agregan ortogonalidad real.
