# FRENTES-ORTOGONALES-20261127: FundedSync O (1 micro fijo) y Compresión de Volatilidad Global en M1DK (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de ejecutar `run_o(qty=1)` en 2018–2026 y antes de evaluar `C2_VZ` y `C2_EVRP` sobre los activos M1 continuos de Dukascopy (`data/m1dk/`). **HOLDOUT A5 (`63m`) de `CANASTA_AMPLIA` y sesiones `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **Pedido de Nico (2026-11-27):** sumar estrategias decorrelacionadas con ventaja esperada neta mayor que su fricción sin repetir barridos fallidos.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `CANASTA_AMPLIA` (mide `PISTA_VIVA` existentes `F-FS-O-N-A5` y `F-COMPRESION-VOL-CRECE`). **Pruebas:** `11` (`1` de `FundedSync O qty=1` fijo + `2` reglas de compresión `VZ` y `EVRP` × `5` activos `M1DK` = `10`).

Cambio respecto a falla previa: respecto a `F-LIT-MACRO-CFD` y `F-MULTIACTIVO-MECANISMOS-PERSISTENCIA-SIN-POTENCIA` (que probaron TSMOM semanal, Donchian, ORB, fade y H1 en CFD), aquí NO se repite ningún barrido técnico sobre OHLC ni se usan futuros `=F` de Yahoo con saltos de roll (`F-YAHOO-FUTUROS-ROLL-NO-AJUSTADO`). En cambio: (A) se fija `qty=1` MNQ constante en `FundedSync O` (`F-FS-O-N-A5`) para eliminar el techo de margen que lo apagó con `NQ > 25,000` en 2025-10; y (B) se evalúa únicamente el mecanismo ya vivo de compresión de volatilidad implícita (`F-COMPRESION-VOL-CRECE`: `C2_VZ` y `C2_EVRP` con IV CBOE causal) sobre los `5` M1 continuos limpios de `data/m1dk/` (`DAX`, `EuroStoxx`, `FTSE`, `Nikkei`, `Oro`), sin ninguna grilla de parámetros.

Antecedentes:
- `docs/research/fs_nfco_a5_20261126/RESULTADO.md` (`O` `CONFIRMA_REP` `p = 0.025`, apagado por margen)
- `docs/research/canasta_amplia_20261127/RESULTADO.md` (`C2_VZ` `27%` y `C2_EVRP` `21%` del aporte en `REP`)
- `docs/research/auditoria_claude_20261127/RESULTADO.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27, K36 causalidad estricta de cierre CBOE `16:15 NY < 17:00 NY`, K51 registro global, cero lectura de `>= 2026-10-01` ni `HOLDOUT A5`).

Potencia previa: exploratorio EF2 en `DESC + REP` exclusivamente (no abre `HOLDOUT A5`); en `M1DK` (`2014–2026`, `~110m DESC+REP`), se requiere `DESC > 0` y `DESC+REP` con fricción `< 0.08 R` antes de considerar inclusión en cartera.

Diagnóstico de mecanismo: sin grilla ni optimización paramétrica. Parámetros congelados de `carril2.py`: `VZ` (`zscore6(IV)` + `zscore6(VIX9D) < -2`, stop `1.25 * ATR20`, tope `10d`, usando `VIX/VIX9D` en índices globales y `GVZ` en `XAUUSD`); `EVRP` (`(IV - RV10) > 0` y `VIX9D/VIX < 1` con `IV = VIX` en índices y `GVZ` en `XAUUSD`, stop `2.0 * ATR20`, tope `20d`). Costo base `8 bps RT` (adverso `16 bps RT`). `FundedSync O`: `run_o(ms, qty=1)` con fricción `1.9775` pts RT MNQ (`\$3.955`/contrato). Canasta causal `Global_VolComp_M1DK`: pesos `1/sd` fit exclusivamente en `DESC` sobre pares con `DESC usd/R > 0`.

## Justificación económica
1. `FundedSync O` explota el drift overnight de índices ligados a prima de liquidez fuera de RTH; fijar `qty=1` MNQ elimina el artefacto de margen `50% * 100k / (25k*20*10%) < 1` ocurrido desde octubre 2025.
2. En índices globales (`DAX, EuroStoxx, FTSE, Nikkei`) y oro (`XAUUSD`), regímenes donde la volatilidad implícita comprimida (`VIX/GVZ` z-score `< -1`) o `eVRP > 0` en contango (`VIX9D/VIX < 1`) reflejan apetito de riesgo calmo antes de expansiones alcistas globales; evaluado sobre M1 continuo de Dukascopy se evita todo salto de roll ficticio.

## Cómo podría refutarse
1. Si `FundedSync O` con `qty=1` pierde en `2025-10..2026-09` (`DESC`/`REP`) o muestra correlación `> 0.35` con `CME_TRZV` o `Carril2_Sell16`.
2. Si `C2_VZ` / `C2_EVRP` en `M1DK` dan media `<= 0` neta a `8 bps` en `REP` o en `2019–2026 DESC+REP`, confirmando que `F-COMPRESION-VOL-CRECE` no transfiere fuera de índices US.
