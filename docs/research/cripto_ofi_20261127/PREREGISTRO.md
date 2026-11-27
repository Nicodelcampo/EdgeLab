# CRIPTO-OFI-PIT: Flujo de Órdenes Taker Buy/Sell (`agg/klines`, No-OHLC) en `226` Perpetuos PIT (`2021–2026-09`) (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de descargar campos de flujo de órdenes (`count`, `quote_volume`, `taker_buy_quote_volume`) y antes de medir resultados. **`HOLDOUT A5` (`18` meses) y sesiones `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **Pedido de Nico (2026-11-27):** sumar información verdaderamente nueva (no-OHLC) y mecanismos ortogonales al `XSMOM` de precios para aumentar `N`, estabilidad y expectativa neta sin iterar más la `REP` de `v1–v3`.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `CRIPTO_ORDERFLOW_PIT`. **Pruebas:** `4` (`3` mecanismos de flujo de órdenes escalonados a `5d` + `1` canasta causal `OFI_Canasta_InvVol`).

Cambio respecto a falla previa: en `CRIPTO-PIT v1` (`w.sub(mean)` derramaba pesos en monedas planas y `EMA 4H` sufría alta rotación, fallando `REP`) y en `v2/v3` la señal dependía exclusivamente de velas OHLC (`close`), `funding` y `premiumIndex`, iterándose sobre los mismos `51` meses de `DESC+REP`. Esta campaña cambia estructuralmente de fuente de información al usar datos **no-OHLC de microestructura de flujo de órdenes agresivas (`taker_buy_quote_volume`, `quote_volume`, `count`)** en Binance USDT-M, abriendo la familia nueva `CRIPTO_ORDERFLOW_PIT` con `HOLDOUT A5` (`18m`) intacto.

Antecedentes:
- `docs/research/cripto_pit_v3_20261127/RESULTADO.md`
- `docs/research/auditoria_claude_20261127/REVISION_CLAUDE.md`
- `docs/research/cripto_pit_20261127/UNIVERSO_PIT.csv`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia antes de abrir holdout, K36 causalidad `shift(1)`, K51 registro global, cero lectura de `>= 2026-10-01` ni `HOLDOUT A5`).

Potencia previa: no abre `HOLDOUT A5` (`18m` sellados). Sobre `51m` (`DESC 39m + REP 12m`), mide si la presión neta de compradores agresores (`OFI`) aporta señal neta positiva a `20 bps RT + funding` y baja correlación frente a `CR3_XSMOM_21d_Stag5d` (`< 0.60`) y `BTCUSDT`.

Diagnóstico de mecanismo: cero grilla paramétrica (`3` reglas fijas escalonadas a `5d`, universo PIT ex-TradFi `226` monedas con `vol60 >= 25%`, histéresis `<=20/>25`, patas `top-4 / bot-4`, `inv_vol`, `gross=1.0`, señales `shift(1)`, costos `10, 20 (base), 30, 40 bps RT + funding real`):
1. `OFI1_TakerFlow_21d_Stag5d`: flujo neto normalizado `OFI = (2 * taker_buy_qvol - qvol) / qvol` acumulado en `21d` sobre su `std(21d)`.
2. `OFI2_FlowReturn_Div_14d_Stag5d`: divergencia cross-sectional `z_cs(OFI_14d) - z_cs(Ret_14d)` (acumulación agresiva no reflejada aún en precio, o euforia con rechazo).
3. `OFI3_WhaleFlow_14d_Stag5d`: flujo `14d` ponderado por rango cross-sectional del tamaño medio por trade `log(quote_volume / count)` (presión institucional/de tickets grandes).
**Regla fija causal en `DESC`**: entran mecanismos con `DESC usd_mes > 0` y `top5_days_share_DESC < 0.65`, ponderados `1/sd_DESC`. Se requiere medir su correlación mensual frente a `CR3_XSMOM_21d_Stag5d`.

## Justificación económica
1. En perpetuos cripto dominados por flujo minorista y liquidaciones, el desequilibrio neto de órdenes agresivas a mercado (`taker_buy - taker_sell`) contiene información de flujo y posicionamiento distinta del simple retorno de cierre (`close`).
2. Ponderar por tamaño medio de operación (`quote_volume / count`) y contrastar flujo contra retorno (`OFI - Ret`) separa flujo informado de ruido o persecución tardía de precio.

## Cómo podría refutarse
1. Si los `3` mecanismos de flujo no superan `20 bps RT + funding` en `DESC`/`REP` (`Sh <= 0.40` o `REP <= 0`) o concentran `> 65%` en `5` días.
2. Si la correlación mensual con `CR3_XSMOM_21d_Stag5d` supera `0.60`, probando que `OFI` diario apenas re-etiqueta el momentum de precios ya medido.
