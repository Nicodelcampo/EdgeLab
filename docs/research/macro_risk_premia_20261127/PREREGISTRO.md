# MACRO-RISK-PREMIA: 5 Primas de Riesgo y Momentum Multi-Clase sobre ETFs Ajustados (`2006–2026-09`) (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de descargar las series de Yahoo `adjclose` y antes de medir resultados. **`HOLDOUT A5` (`63` meses en `2006–2026-09`) y sesiones `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **Pedido de Nico (2026-11-27):** sumar frentes genuinamente ortogonales, limpios de iteración en `REP` y libres del sesgo de selección CME, con horizonte de `20+` años y `63m` de holdout sellado para potenciar una cartera multi-estrategia estable.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `MACRO_RISK_PREMIA`. **Pruebas:** `6` (`5` mecanismos institucionales fijos sin grilla + `1` canasta causal `RP_Canasta_InvVol`).

Cambio respecto a campañas previas (`TENDENCIA-NO-EQUITY`, `FUTUROS-NO-EQUITY v2`, `GLOBAL-VOLCOMP`): (1) a diferencia de `FUTUROS-NO-EQUITY v2` (invalidada por empalmes Yahoo `=F`), usamos **exclusivamente ETFs líquidos ajustados por dividendos y splits (`adjclose`, cero empalmes)** junto con índices de rendimiento `^TNX` / `^IRX`; (2) a diferencia de `TENDENCIA-NO-EQUITY` (un solo factor direccional `TSMOM` en `14` ETFs), construimos **5 primas estructurales con exposición cross-sectional, beta-neutralidad frente a `SPY`, pendiente de tasas y crédito**: sectores US `XSMOM` beta-neutral, sectores US `BAB` (Betting-Against-Beta), países globales `XSMOM` beta-neutral, régimen curva-crédito de tasas y tendencia multi-velocidad `no-equity` escalonada; (3) no usa señales del `VIX` ni vela intradía CME, por lo que no duplica `Carril 2` ni `CME_TRZV`.

Antecedentes:
- `docs/research/tendencia_no_equity_20261127/RESULTADO.md`
- `docs/research/auditoria_claude_20261127/REVISION_CLAUDE.md`
- `docs/research/HANDOFF_ANTIGRAVITY_2026-11-27.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia antes de abrir holdout, K36 causalidad estricta `shift(1)`, K51 registro global, cero lectura de `>= 2026-10-01` ni `HOLDOUT A5`).

Potencia previa: no abre `HOLDOUT A5` (`63m` sellados en `2006–2026-09`). Mide en `DESC (143m)` -> `REP (42m)` si la canasta causal multi-prima aporta un nuevo frente limpio independiente (`corr vs Carril2_Sell16 < 0.35`, `|corr vs SPY| < 0.35`) para complementar a `Carril 2` hacia el umbral conjunto `>= 0.70–0.80` en `63m` sin depender de la `REP` iterada de cripto.

Diagnóstico de mecanismo: cero grilla paramétrica (`5` reglas con ventanas estándar fijas `21d / 63d / 126d / 252d`, rebalanceo escalonado `5` cohortes semanales, exposición bruta `1.0`, señales desplazadas `shift(1)`). Fricción base: `10 bps RT` de transacción + costo realista de financiamiento/préstamo de patas cortas (`100 bps/año` en ETFs sectoriales/países y `50 bps/año` en ETFs de bonos/FX/commodities); estrés `2x` (`20 bps RT` + `200/100 bps/año`). **Regla fija causal en `DESC` (`143m`)**: entran exclusivamente mecanismos con `DESC Sharpe > 0.25` y `|corr_DESC vs SPY| < 0.35` (fallback `DESC Sharpe > 0` si ninguno supera `0.25`), ponderados `1/sd` ajustado sólo en `DESC`. `REP (42m)` se evalúa una única vez con pesos congelados.

## Justificación económica
1. Las primas cross-section de momentum sectorial (`XL*`) y nacional (`EW*`) neutralizadas causalmente en `beta_SPY`, junto con `BAB` (aprovechamiento del apalancamiento restringido entre sectores de bajo y alto beta), capturan dispersión relativa e ineficiencias de mandato institucional con exposición direccional de mercado cercana a cero.
2. El diferencial de pendiente de la curva (`^TNX - ^IRX`), la salud del crédito (`HYG/LQD`) y la tendencia multi-velocidad exclusiva en bonos, metales, energía y divisas proveen retornos defensivos y de asignación de riesgo descorrelacionados de la renta variable intradía y swing US.

## Cómo podría refutarse
1. Si ningún mecanismo individual pasa `DESC > 0` o si la canasta `RP_Canasta_InvVol` cae en `REP (42m)` (`Sharpe <= 0` o `DR Sharpe < 0.35`).
2. Si la canasta resultante presenta correlación `> 0.45` con `SPY` o con `Carril2_Sell16` / `CME_TRZV`, demostrando que no agrega diversificación real ni supera el estrés `2x` de costos.
