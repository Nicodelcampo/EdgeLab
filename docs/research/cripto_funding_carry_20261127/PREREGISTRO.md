# CRIPTO-FUNDING-CARRY-PIT: Carry de Funding, Choques y Crowding en 226 Perpetuos PIT (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de ejecutar cálculos sobre los parquets locales de funding 8h (`data/crypto_binance_pit_1d/`). **`HOLDOUT A5` (`18m`) y sesiones `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `CRIPTO_FUNDING_CARRY_PIT`. **Pruebas:** `4` (`3` mecanismos causales escalonados a `5d` + `1` canasta causal `CFC_Canasta_InvVol`).

Cambio respecto a falla previa: en `CRIPTO-PIT v1` (`EMA 4H`, pesos no neutralizados) falló la réplica, en `v3` (`CR3_BAB_LowVol`) la pata de baja volatilidad perdió en `2020` (`t = −0,26`) y dio `Sh = 0,00` en `HOLDOUT A5`, y en `F-ATRAS-M1-V2V4-REFUTADA` se repitieron velas con overfitting de ventanas. Esta familia nueva cambia de fuente de señal sin agregar datos: explota el **diferencial estructural de tasa de fondeo (funding 8h)** ya descargado en el universo PIT ex-TradFi de `226` perpetuos (carry puro neutral frente a BTC, choque de tasa de fondeo y momentum filtrado por exceso de apalancamiento), con parámetros fijos y `HOLDOUT A5` (`18m`) completamente virgen.

Antecedentes:
- `docs/research/cripto_pit_v3_20261127/RESULTADO.md`
- `docs/research/cripto_ofi_20261127/RESULTADO.md`
- `docs/research/cripto_v3_2019_20261127/RESULTADO.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia previa, K36 causalidad estricta `shift(1)`, K51 registro global, cero lectura de `HOLDOUT A5` ni `>= 2026-10-01`).

Potencia previa: no abre `HOLDOUT A5` (`18m` sellados). Sobre `51m` (`DESC 39m + REP 12m`), mide si el carry y los choques de funding entre perpetuos aportan señal neta positiva a `20 bps RT + funding real` y baja correlación frente a `CR3_XSMOM` y `OFI1` (`< 0,55`), aumentando la densidad y estabilidad del frente cripto.

Diagnóstico de mecanismo: cero grilla paramétrica (`3` reglas fijas escalonadas en `5` cohortes, universo PIT ex-TradFi `226` monedas con `vol60 >= 25%`, histéresis `<=20/>25`, patas `top-4 / bot-4`, ponderación `inv_vol`, `gross=1.0`, señales desplazadas `shift(1)`, costos `10, 20 (base), 30, 40 bps RT + funding real`):
1. `CFC1_FundingCarry_14d_Stag5d`: ranking por carry negativo acumulado `−sum_14d(funding)` (cobrando funding positivo en cortos / negativo en largos) con neutralización rolling beta frente a BTC (`60d`).
2. `CFC2_FundingShock_Reversal_Stag5d`: exceso de tasa de fondeo de corto plazo (`5d − 30d` estandarizado por `std 30d`), apostando contra congestión aguda.
3. `CFC3_CarryFiltered_XSMOM_Stag5d`: `z_cs(ret_21d) − 0,5 · z_cs(funding_14d)` (momentum transversal evitando posiciones con crowding caro de funding).
**Regla fija causal en `DESC`**: entran mecanismos con `DESC usd_mes > 0` y `top5_days_share_DESC < 0,65`, ponderados `1/sd_DESC`.

## Justificación económica
1. En perpetuos sin vencimiento, la tasa de fondeo transfiere flujo real cada 8 horas entre largos apalancados y cortos; capturar ese diferencial cobrando tasas altas contra monedas con tasa baja o negativa genera carry distinto al retorno de precios.
2. Filtrar el momentum de precios por exceso de fondeo evita comprar activos saturados de apalancamiento largo antes de liquidaciones.

## Cómo podría refutarse
1. Si tras pagar `20 bps RT` de rotación más el flujo real de `funding` (en sentido de la posición) ningún mecanismo logra expectativa positiva sostenida en `DESC` y `REP`, o si >65 % se concentra en 5 días.
2. Si la correlación mensual con `Cripto_v3_Canasta` y `Cripto_OFI_Canasta` supera `0,65`, mostrando redundancia sin diversificación real.
