# MACRO-CTA-VRP-20Y: Tendencia Multi-Horizonte No-Equity, Term Structure VIX/VIX3M, Tasas Reales y Vol-Managed (`2006–2026-09`) (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de descargar `^VIX3M` y medir retornos. Reutiliza los ETFs `adjclose` limpios de `data/macro_risk_premia/` (cero empalmes `=F`) + índices CBOE locales. **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `MACRO_CTA_VRP_20Y`. **Pruebas:** `5` (`4` reglas institucionales sin grilla + `1` canasta causal `MVC_Canasta_InvVol`).

Cambio respecto a falla previa: en `F-YAHOO-FUTUROS-ROLL-NO-AJUSTADO` (`NO_REPETIR`) se invalidó usar `=F` sin ajuste de roll, en `F-CRASH-VIX-INVERTIDA-REFUTADO` (`NO_REPETIR`) falló aplicar `VIX9D/VIX >= 1` como filtro de reversión corta en `Carril 2`, y en `MACRO_RISK_PREMIA` (`RP1` sectorial XSMOM) falló el momentum puro de sectores de acciones en `HOLDOUT`. Esta campaña usa **únicamente ETFs ajustados `adjclose` (cero `=F`)** y explora mecanismos macro no incluidos en `RP4`: (1) tendencia multi-horizonte `21/63/126/252d` en `15` ETFs **no-equity**, (2) rotación `Risk-On vs Flight-to-Quality` por estructura temporal `VIX / VIX3M`, (3) carry de curva y tasas reales (`TIP/IEF`, `GLD/UUP`) y (4) paridad de riesgo *vol-managed* (`1/var`) sin renta variable.

Antecedentes:
- `docs/research/macro_risk_premia_20261127/RESULTADO.md`
- `docs/research/holdout_a5_nocme_20261127/RESULTADO.md`
- `docs/research/supercartera_v3_20261127/RESULTADO.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia, K36 causalidad `shift(1)`, K51 registro global, cero lectura de `HOLDOUT A5` ni `>= 2026-10-01`).

Potencia previa: no abre `HOLDOUT A5` (`63m` sellados). Busca sobre `DESC (144m)` y `REP (42m)` reglas de `20` años con correlación baja frente a `Carril2_Sell16` (`< 0,30`) y frente a `RP4` (`< 0,55`) para complementar un eventual pozo conjunto capaz de superar potencia `>= 0,80` (K27).

Diagnóstico de mecanismo: cero grilla paramétrica (`4` reglas estándar escalonadas en `5` cohortes, señales `shift(1)`, costo `5 bps RT` base / `10 bps RT` estrés sobre rotación + `50 bps/año` en patas cortas):
1. `MVC1_CTA_NonEq_MultiHorizon`: promedio de `tanh(ret_h / (vol_21d * sqrt(h)))` en `h = (21, 63, 126, 252)` sobre `15` ETFs no-equity (`SHY, IEI, IEF, TLT, TIP, LQD, HYG, GLD, SLV, USO, DBC, UUP, FXE, FXY, FXB, FXA`), vol-parity `10%` anual.
2. `MVC2_VIX_TermStruct_FTQ`: razón `ts = (VIX / VIX3M).rolling(3).mean()`; contango sano favorece `Risk-On (SPY+HYG) − Safe-Haven (TLT+GLD)`, backwardation invierte a refugio (`TLT+GLD − SPY`).
3. `MVC3_Rates_RealYield_Carry`: duración por pendiente (`^TNX − ^IRX`) combinada con cobertura real (`GLD` vs `UUP` cuando `TIP/IEF` sube en `63d`).
4. `MVC4_MoreiraMuir_VolManaged_ExEq`: paridad por inversa de varianza (`1/var_21d` acotada `[0,25x; 2,0x]` respecto a su media móvil `252d`) en `5` activos no-equity (`TLT, IEF, GLD, DBC, HYG`) comparada contra `1/vol` estático.
**Regla fija causal en `DESC`:** entran a `MVC_Canasta_InvVol` mecanismos con `DESC Sh > 0,25` (fallback `> 0`), ponderados `1/sd_DESC`.

## Justificación económica
1. La tendencia multi-velocidad en bonos, divisas y materias primas captura shocks macroeconómicos persistentes de tasas e inflación justamente cuando la renta variable (`Carril 2`) sufre caídas prolongadas.
2. La estructura temporal `VIX / VIX3M` refleja cobertura institucional aguda; rotar entre crédito/equity y refugios (`TLT+GLD`) en backwardation protege la cartera y monetiza la prima de riesgo de volatilidad en contango.

## Cómo podría refutarse
1. Si en `DESC+REP` los mecanismos no superan costos (`Sh <= 0,30` o `REP <= 0`).
2. Si la canasta queda altamente correlacionada (`> 0,55`) con `Macro_RP_Canasta` (`RP4`) o con `Carril2_Sell16`, sin aportar nueva ortogonalidad.
