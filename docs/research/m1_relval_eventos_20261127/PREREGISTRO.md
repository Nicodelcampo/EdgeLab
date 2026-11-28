# M1-RELVAL-EVENTOS-20Y: Dispersión Cross-Índice, Overnight vs RTH, Pre-FOMC y Varianza Realizada M1 (`2006–2026-09`) (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de calcular retornos. Usa exclusivamente barras locales `M1` de futuros CME (`2006-01 → 2026-09`) con costos canónicos medidos (`edgelab/costos.py`), calendario FOMC y series CBOE. **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `M1_RELVAL_EVENTOS_20Y`. **Pruebas:** `5` (`4` mecanismos fijos sin grilla + `1` canasta causal `MRV_Canasta_InvVol`).

Cambio respecto a falla previa: en `F-FILTROS-CONTEXTO-SIN-FILTRO` (`NO_REPETIR`) fallaron filtros por terciles de VIX sobre intradía direccional NQ; en `F-MULTIACTIVO-MECANISMOS-PERSISTENCIA-SIN-POTENCIA` (`NO_REPETIR`) falló la grilla de 6 breakouts genéricos direccionales; y en `F-TR-NO-TRANSFIERE-EUROPA-B` (`NO_REPETIR`) falló transferir T+R a CFDs europeos. Aquí no buscamos breakouts ni filtros sobre T/R/Z: medimos sobre 20 años mecanismos **mercado-neutrales de valor relativo cross-índice (`ES, NQ, YM, RTY`)**, **calendario pre-FOMC (`14:00 → 13:55 NY`)** y **prima de varianza usando volatilidad realizada exacta de 5 minutos extraída del M1 (`IV − RV_5m`)** con costos canónicos de futuros CME (sin `EMD`, por K33).

Antecedentes:
- `docs/research/holdout_a5_nocme_20261127/RESULTADO.md`
- `docs/research/confianza_sin_forward_20261127/RESULTADO.md`
- `docs/research/canasta_amplia_20261127/RESULTADO.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia, K33 costos canónicos sin estimados ad-hoc, K36 causalidad `shift(1)`, K51 registro global, cero lectura de `HOLDOUT A5` ni `>= 2026-10-01`).

Potencia previa: no abre `HOLDOUT A5` (`63m` sellados). Evalúa sobre `DESC (144m)` y `REP (42m)` si al menos `2` mecanismos logran Sharpe positivo en ambos bloques con estrés `2x` y baja correlación frente a `Carril2_Sell16` (`< 0,40`), para acercar la potencia conjunta de un eventual pool nuevo de `20` años hacia `>= 0,80` (K27).

Diagnóstico de mecanismo: cero grilla paramétrica (`4` reglas estándar sin búsqueda):
1. `MRV1_CrossIdx_Dispersion_5d`: sobre `[ES, NQ, YM, RTY]`, reversión cross-sectional de 5 días neutralizada por volatilidad (`long` rezagado / `short` líder, escalonado 5 cohortes).
2. `MRV2_Overnight_vs_RTH_RelVal`: sobre `[ES, NQ, YM, RTY]`, diferencial móvil `10d` entre retorno nocturno (`ovn`) y sesión contado (`rth`), largo top-1 / corto bottom-1 vol-neutral escalonado `5d`.
3. `MRV3_PreFOMC_Drift_M1`: deriva pre-FOMC estándar (Lucca & Moench 2015), entrando `14:00 NY` de la víspera (`market_days_to_next_fomc == 1`) y saliendo `13:55 NY` del día del comunicado (`is_fomc_statement_day == True`), ponderado `1/vol_20d` en `[ES, NQ, YM]`.
4. `MRV4_True_M1_VRP_ES_NQ_GC`: diferencia causal `(IV − RV_5m)` sobre `[ES/VIX, NQ/VXN, GC/GVZ]` usando volatilidad realizada intradía `5m` de RTH; exposición escalonada `0..1,5` cuando `IV > RV_5m` y `0` cuando `RV_5m >= IV` (se mide neto y en exceso sobre Buy&Hold de igual exposición media).
Costos: fricción ida y vuelta canónica (`edgelab.costos.friccion_rt_puntos`: `ES 0,8877`, `NQ 1,5455`, `YM 5,052`, `RTY 0,4436`, `GC 0,605` pts), escenarios `1x` y `2x`. **Regla fija causal en `DESC`:** entran a `MRV_Canasta_InvVol` mecanismos con `DESC Sh > 0,25` (o `> 0` si <2 superan `0,25`), ponderados `1/sd_DESC`.

## Justificación económica
1. Los flujos institucionales generan distorsiones de corto plazo entre índices estadounidenses de distinto perfil (`NQ` crecimiento, `RTY` small caps, `YM` valor) y entre cierre nocturno versus rueda contado, cuya reversión tiene beta agregada cercana a cero.
2. El anuncio de política monetaria (FOMC) concentra incertidumbre sistemática resuelta justo antes de las 14:00 NY, y el spread `IV − RV_5m` permite dimensionar prima de volatilidad con precisión intradía real de `M1`.

## Cómo podría refutarse
1. Si las patas mercado-neutrales (`MRV1/MRV2`) no cubren costos canónicos de futuros `1x`/`2x` en `DESC+REP` (`Sh <= 0,20` o `REP <= 0`).
2. Si `MRV3` resulta un artefacto extinguido en `REP`/`2019+` o si `MRV4` no supera a su exposición pasiva equivalente (`Sh <= 0` vs Buy&Hold) o presenta correlación `> 0,55` con `Carril2_Sell16`.
