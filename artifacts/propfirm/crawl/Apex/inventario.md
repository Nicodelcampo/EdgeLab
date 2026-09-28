# Inventario de reglas — Apex

Páginas leídas: 16 · bloqueadas: 0 · oraciones con reglas: 142

## Cobertura por categoría

| Categoría | Impacto | Oraciones |
|---|---|---|
| objetivo_beneficio | sim | 6 |
| drawdown_maximo | sim | 16 |
| drawdown_bloqueo | sim | 6 |
| perdida_diaria | sim | 23 |
| consistencia | sim | 10 |
| dias_minimos | sim | 8 |
| dias_ganadores | sim | 1 |
| plazo_maximo | sim | 6 |
| inactividad | sim | 5 |
| retiro_colchon | sim | 5 |
| retiro_frecuencia | sim | 3 |
| retiro_minimo | sim | 2 |
| retiro_maximo | sim | 3 |
| retiro_split | sim | 5 |
| retiro_cantidad | sim | 2 |
| cuenta_live | sim | 15 |
| cierre_cuenta | sim | 6 |
| contratos_maximos | sim | 9 |
| escalado | sim | 1 |
| riesgo_por_trade | filtro | 4 |
| relacion_riesgo_beneficio | filtro | 2 |
| ganancia_extraordinaria | filtro | 1 |
| tiempo_minimo_tenencia | filtro | **0 — sin evidencia, buscar a mano** |
| noticias | filtro | 2 |
| horario_y_overnight | filtro | 12 |
| instrumentos | filtro | 1 |
| estrategias_prohibidas | filtro | 21 |
| cobertura_y_copy | filtro | 5 |
| bots_y_automatizacion | filtro | 3 |
| martingala_y_promediar | filtro | **0 — sin evidencia, buscar a mano** |
| cuentas_maximas | filtro | 4 |
| discrecional_firma | filtro | 1 |
| kyc_y_jurisdiccion | filtro | 1 |
| cuota | costo | 2 |
| activacion_y_reset | costo | 6 |
| comisiones_y_datos | costo | 6 |

## objetivo_beneficio (sim)

- Profit Target $1,500 / $3,000 / $6,000 / $9,000.  
  <sub>$1,500, $3,000, $6,000, $9,000 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- To pass an evaluation, you must reach the profit target and not reach EOD Drawdown level at any point.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Is there a time limit to reach the profit target?  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Yes, the time limit to reach the profit target is set to 30 calendar days from the date of account purchase.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- High-Risk Strategies: Strategies that involve small profit targets while risking disproportionately large amounts are not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- For example, setting a five-tick profit target with a 150-tick stop loss demonstrates unacceptable risk management.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## drawdown_maximo (sim)

- There is no DLL for Intraday Drawdown Evaluations.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- When EOD Drawdown Stops Trailing.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- Evaluations Tradovate: EOD Drawdown trails indefinitely with the peak EOD account balance.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- The account may experience intraday drawdown, but it may never touch or cross the EOD Threshold level at any time.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- No intraday trailing drawdown.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/) +1</sub>
- EOD Drawdown calculated once per day at market close and enforced following trading session.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Max Drawdown (EOD) $1,000 / $2,000 / $3,000 / $4,000.  
  <sub>$1,000, $2,000, $3,000, $4,000 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/) +1</sub>
- To pass an evaluation, you must reach the profit target and not reach EOD Drawdown level at any point.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- EOD Drawdown calculated once per day at market close and enforced intraday.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- This cap applies across all PA accounts combined, whether different size, EOD, or Intraday Trailing Drawdown.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- If max drawdown is reached it is permanently failed; there are no reset fees and no reset options; purchase a new Evaluation.  
  <sub> · [https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/)</sub>
- Intraday Trailing Drawdown.  
  <sub> · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/)</sub>
- Max intraday drawdown 25K $1,000, 50K $2,000, 100K $3,000, 150K $4,000.  
  <sub>$1,000,, $2,000,, $3,000,, $4,000 · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/)</sub>
- Live account: $0 starting balance, $3,000 end-of-day drawdown, 3 mini / 30 micro contracts, no DLL at Level 1.  
  <sub>$0, $3,000, 3 mini, 30 micro · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Requalification Eval-to-Live: $199, minimum 5 days, 40% consistency, $250 minimum daily profit, $4,000 target, $2,000 intraday trailing drawdown, $1,000 flatten loss limit, 3 mini.  
  <sub>$199,, 5 days, 40%, $250, $4,000, $2,000 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Using the Trailing Threshold as a Stop Loss: Traders are prohibited from using the account's full threshold as a stop-loss mechanism to absorb large losses, leading to account liquidation.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## drawdown_bloqueo (sim)

- When EOD Drawdown Stops Trailing.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- Evaluations Rithmic and Wealthcharts: EOD Threshold stops trailing and becomes fixed when it reaches an amount equal to the Target Profit balance.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- PA: trailing stops at Starting Balance + $100.  
  <sub>$100 · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/)</sub>
- Evaluations Rithmic and Wealthcharts: threshold stops trailing at the Target Profit balance.  
  <sub> · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/)</sub>
- Safety net: once profit reaches $3,100 the drawdown locks at +$100; payouts only from profits above $3,100.  
  <sub>$3,100, $100, $3,100 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- A passed Evaluation is locked to prevent additional trading.  
  <sub> · [https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/](https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/)</sub>

## perdida_diaria (sim)

- Daily Loss Limit Explained.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- DLL resets daily at 6PM ET.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- DLL applies to total account equity including realized and unrealized losses.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- Liquidation at market price; final balance may be slightly above or below the DLL threshold.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- EOD Evaluations daily loss limit: 25K $500, 50K $1,000, 100K $1,500, 150K $2,000; does not increase with profits.  
  <sub>$500,, $1,000,, $1,500,, $2,000 · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- There is no DLL for Intraday Drawdown Evaluations.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- In PA the DLL scales by tier (see scaling).  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- DLL can decrease if balance declines but never below Level 1.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- Hitting the DLL does not change the EOD Threshold.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)</sub>
- The DLL limits how much an account can lose within a single trading day; if it is reached, all open positions are automatically liquidated and trading is paused for the remainder of the day, but the account remains active.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- Daily Loss Limit (DLL) fixed during the trading session.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Daily Loss Limit $500 / $1,000 / $1,500 / $2,000.  
  <sub>$500, $1,000, $1,500, $2,000 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Does hitting the Daily Loss Limit fail my evaluation?  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Reaching DLL pauses trading for the remainder of the session.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- DLL and the EOD Threshold are separate rules.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Daily Loss Limit (DLL) enforced intraday.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- Hitting the DLL pauses trading for the remainder of the session.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- Live account: $0 starting balance, $3,000 end-of-day drawdown, 3 mini / 30 micro contracts, no DLL at Level 1.  
  <sub>$0, $3,000, 3 mini, 30 micro · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Level 2 ($10,000-$50,000): 10 mini, $5,000 DLL.  
  <sub>$10,000, $50,000, 10 mini, $5,000 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Maximum contracts and daily loss limit by profit range: 25K PA: $0-$999 max contracts 1, DLL $500 (L1); $1,000-$1,999 max contracts 2, DLL $500 (L2); $2,000+ max contracts 2, DLL $1,250 (L3).  
  <sub>$0, $999, $500, $1,000, $1,999, $500 · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>
- 50K PA: $0-$1,499 max contracts 2, DLL $1,000 (L1); $1,500-$2,999 max contracts 3, DLL $1,000 (L2); $3,000-$5,999 max contracts 4, DLL $2,000 (L3); $6,000+ max contracts 4, DLL $3,000 (L4).  
  <sub>$0, $1,499, $1,000, $1,500, $2,999, $1,000 · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>
- 100K PA: $0-$1,999 3 contracts DLL $1,750; $2,000-$2,999 4 contracts DLL $1,750; $3,000-$4,999 5 contracts DLL $1,750; $5,000-$9,999 6 contracts DLL $2,500; $10,000+ 6 contracts DLL $3,500.  
  <sub>$0, $1,999, 3 contracts, $1,750, $2,000, $2,999 · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>
- 150K PA: $0-$1,999 4 contracts DLL $2,500; $2,000-$2,999 5 contracts DLL $2,500; $3,000-$4,999 7 contracts DLL $2,500; $5,000-$9,999 10 contracts DLL $3,000; $10,000+ 10 contracts DLL $4,000.  
  <sub>$0, $1,999, 4 contracts, $2,500, $2,000, $2,999 · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>

## consistencia (sim)

- 50% Consistency Requirement.  
  <sub>50% · [https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/](https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/)</sub>
- Reset after payout: the consistency calculation resets.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/](https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/)</sub>
- Being above 50% consistency does not fail your account.  
  <sub>50% · [https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/](https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/)</sub>
- Losing days reduce net profit and affect consistency.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/](https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/)</sub>
- There is no time limit to satisfy the consistency percentage.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/](https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/)</sub>
- If no profit or at a loss since last payout, consistency cannot be calculated and you won't qualify.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/](https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/)</sub>
- 50% consistency rule applies.  
  <sub>50% · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- 50% Consistency Requirement: No single profitable trading day may account for 50% or more of total profit earned since your last approved payout.  
  <sub>50%, 50% · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- If this requirement is not satisfied, the payout request option will not be available until you reach 50% consistency.  
  <sub>50% · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Requalification Eval-to-Live: $199, minimum 5 days, 40% consistency, $250 minimum daily profit, $4,000 target, $2,000 intraday trailing drawdown, $1,000 flatten loss limit, 3 mini.  
  <sub>$199,, 5 days, 40%, $250, $4,000, $2,000 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>

## dias_minimos (sim)

- No minimum trading days required, may pass in one trading day.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- There is no minimum number of trading days required.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Minimum 5 trading days that meet the required minimum daily profit.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Each account must complete at least 5 trading days before a payout can be requested.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- For example, on a 50K EOD PA, you need to have a minimum of 5 trading days with a minimum of $250 profit for each of the days.  
  <sub>$250 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- To remain active you must record at least 2 trading days with $50 or more in net profit within every rolling 30-day period (calendar days).  
  <sub>$50 · [https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/](https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/)</sub>
- Minimum 5 trading days meeting minimum daily profit (not consecutive, no deadline).  
  <sub> · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>
- Requalification Eval-to-Live: $199, minimum 5 days, 40% consistency, $250 minimum daily profit, $4,000 target, $2,000 intraday trailing drawdown, $1,000 flatten loss limit, 3 mini.  
  <sub>$199,, 5 days, 40%, $250, $4,000, $2,000 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>

## dias_ganadores (sim)

- To remain active you must record at least 2 trading days with $50 or more in net profit within every rolling 30-day period (calendar days).  
  <sub>$50 · [https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/](https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/)</sub>

## plazo_maximo (sim)

- There is no time limit to satisfy the consistency percentage.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/](https://apextraderfunding.com/help-center/additional-helpful-items/50-consistency-requirement/)</sub>
- Is there a time limit to reach the profit target?  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Yes, the time limit to reach the profit target is set to 30 calendar days from the date of account purchase.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- 30 consecutive calendar days of access including weekends and holidays; expires at 6:00 PM ET on Day 30; no extensions.  
  <sub>6:00 · [https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/)</sub>
- Level 1 data included; DOM data is extra (Rithmic expires end of month; Tradovate/Wealthcharts billed until cancelled).  
  <sub> · [https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/)</sub>
- 7 calendar days from Passed to pay the PA Activation Fee; cannot be extended; if missed the opportunity expires and a new Evaluation must be passed.  
  <sub> · [https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/](https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/)</sub>

## inactividad (sim)

- Inactivity Policy on PA (modified 2026-09-11).  
  <sub> · [https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/](https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/)</sub>
- After 15 days of inactivity the account moves to dormant.  
  <sub>15 days · [https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/](https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/)</sub>
- If 30 consecutive calendar days pass without meeting this threshold the account will be closed due to inactivity; accumulated rewards and payout eligibility are forfeited; cannot be reinstated.  
  <sub> · [https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/](https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/)</sub>
- Inactivity: no trades for 30 days may close the account.  
  <sub>30 days · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- If a PA is disqualified, liquidated, or closed for inactivity it is permanently closed; a new Evaluation and a new activation fee are required.  
  <sub> · [https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/](https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/)</sub>

## retiro_colchon (sim)

- EOD Performance Account Payouts: Account Size / Min Trade Days / Min Daily Profit / Safety Net / Min Balance to Request / Max Payouts.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Safety Net Requirement: The Safety Net is calculated as your account's drawdown limit plus $100.  
  <sub>$100 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Only profit above the safety net is eligible to be requested for a payout.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Safety net (drawdown limit + $100) maintained for the lifetime of the PA; only profit above the safety net can be requested.  
  <sub>$100 · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>
- Safety net: once profit reaches $3,100 the drawdown locks at +$100; payouts only from profits above $3,100.  
  <sub>$3,100, $100, $3,100 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>

## retiro_frecuencia (sim)

- Maximum 6 payouts per Performance Account.  
  <sub>6 payouts · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Maximum 6 payouts per Performance Account; after 6 payouts the PA is closed.  
  <sub>6 payouts, 6 payouts · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>
- Max payout per request by payout number 1-6: 25K $1,000 each; 50K $1,500, $2,000, $2,500, $2,500, $3,000, $3,000; 100K $2,000, $2,500, $3,000, $3,000, $4,000, $4,000; 150K $2,500, $3,000, $3,000, $4,000, $4,000, $5,000.  
  <sub>$1,000, $1,500,, $2,000,, $2,500,, $2,500,, $3,000, · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>

## retiro_minimo (sim)

- Minimum payout amount: $500.  
  <sub>$500 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- The minimum payout amount is $500 per request, regardless of account size.  
  <sub>$500 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>

## retiro_maximo (sim)

- EOD Performance Account Payouts: Account Size / Min Trade Days / Min Daily Profit / Safety Net / Min Balance to Request / Max Payouts.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- EOD Performance Account Max Payouts, Payout # / $25,000 / $50,000 / $100,000 / $150,000: 1 / $1,000 / $1,500 / $2,000 / $2,500.  
  <sub>$25,000, $50,000, $100,000, $150,000, $1,000, $1,500 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Max payout per request by payout number 1-6: 25K $1,000 each; 50K $1,500, $2,000, $2,500, $2,500, $3,000, $3,000; 100K $2,000, $2,500, $3,000, $3,000, $4,000, $4,000; 150K $2,500, $3,000, $3,000, $4,000, $4,000, $5,000.  
  <sub>$1,000, $1,500,, $2,000,, $2,500,, $2,500,, $3,000, · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>

## retiro_split (sim)

- 100% Payout Split (upon meeting payout eligibility requirements).  
  <sub>100% · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- Approved payouts are issued at a 100% payout split once payout eligibility requirements are met.  
  <sub>100% · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- Up to weekly payouts with 100% payout split.  
  <sub>100% · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Up to weekly, 100% payout split.  
  <sub>100% · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>
- Profit split 90% to the trader.  
  <sub>90% · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>

## retiro_cantidad (sim)

- After 6 payouts, the PA is closed.  
  <sub>6 payouts · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Maximum 6 payouts per Performance Account; after 6 payouts the PA is closed.  
  <sub>6 payouts, 6 payouts · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>

## cuenta_live (sim)

- Performance Accounts: Once the EOD Threshold reaches Starting Balance + $100, it stops increasing.  
  <sub>$100, · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- Once passed, you will have 7 calendar days to activate your corresponding EOD Performance Account (PA).  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- EOD Performance Accounts (PA).  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- The EOD Performance Account is a Simulated Funded (Sim Funded) account awarded after you pass the EOD Evaluation.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- This cap applies across all PA accounts combined, whether different size, EOD, or Intraday Trailing Drawdown.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- The Performance Account is a Simulated Funded (Sim Funded) account.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- Maximum 6 payouts per Performance Account.  
  <sub>6 payouts · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- EOD Performance Account Payouts: Account Size / Min Trade Days / Min Daily Profit / Safety Net / Min Balance to Request / Max Payouts.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- This threshold must be maintained for the lifetime of the Performance Account.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Each Performance Account may receive a maximum of six payouts.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- EOD Performance Account Max Payouts, Payout # / $25,000 / $50,000 / $100,000 / $150,000: 1 / $1,000 / $1,500 / $2,000 / $2,500.  
  <sub>$25,000, $50,000, $100,000, $150,000, $1,000, $1,500 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>
- Maximum 6 payouts per Performance Account; after 6 payouts the PA is closed.  
  <sub>6 payouts, 6 payouts · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)</sub>
- Once selected, all Evaluation Accounts are closed and Performance Accounts deactivated; simulated profits go to a Bonus Vault that is not real money.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Live account: $0 starting balance, $3,000 end-of-day drawdown, 3 mini / 30 micro contracts, no DLL at Level 1.  
  <sub>$0, $3,000, 3 mini, 30 micro · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Up to 5 live accounts, each added after $4,500 profit, max based on PA count at graduation.  
  <sub>$4,500 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>

## cierre_cuenta (sim)

- If 30 consecutive calendar days pass without meeting this threshold the account will be closed due to inactivity; accumulated rewards and payout eligibility are forfeited; cannot be reinstated.  
  <sub> · [https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/](https://apextraderfunding.com/help-center/billing/inactivity-policy-on-performance-accounts-pa/)</sub>
- Declining the invitation: account fully deactivated, final reward payment of $3,000 total, Bonus Vault forfeited.  
  <sub>$3,000 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Inactivity: no trades for 30 days may close the account.  
  <sub>30 days · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Violations result in account closure and forfeiture of funds.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Traders will forfeit their accounts and all associated balances.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Repeat violations lead to account enforcement, closures and forfeits.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>

## contratos_maximos (sim)

- Max Contracts 4 / 6 / 8 / 12.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Max Contracts 2 / 4 / 6 / 10.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- Live account: $0 starting balance, $3,000 end-of-day drawdown, 3 mini / 30 micro contracts, no DLL at Level 1.  
  <sub>$0, $3,000, 3 mini, 30 micro · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Level 2 ($10,000-$50,000): 10 mini, $5,000 DLL.  
  <sub>$10,000, $50,000, 10 mini, $5,000 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Requalification Eval-to-Live: $199, minimum 5 days, 40% consistency, $250 minimum daily profit, $4,000 target, $2,000 intraday trailing drawdown, $1,000 flatten loss limit, 3 mini.  
  <sub>$199,, 5 days, 40%, $250, $4,000, $2,000 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Max contracts 6 mini / 60 micro.  
  <sub>6 mini, 60 micro · [apex-trader-funding](https://propfirmapp.com/prop-firms/apex-trader-funding)</sub>
- Maximum contracts and daily loss limit by profit range: 25K PA: $0-$999 max contracts 1, DLL $500 (L1); $1,000-$1,999 max contracts 2, DLL $500 (L2); $2,000+ max contracts 2, DLL $1,250 (L3).  
  <sub>$0, $999, $500, $1,000, $1,999, $500 · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>
- 50K PA: $0-$1,499 max contracts 2, DLL $1,000 (L1); $1,500-$2,999 max contracts 3, DLL $1,000 (L2); $3,000-$5,999 max contracts 4, DLL $2,000 (L3); $6,000+ max contracts 4, DLL $3,000 (L4).  
  <sub>$0, $1,499, $1,000, $1,500, $2,999, $1,000 · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>
- Orders exceeding max position size are rejected, no penalty.  
  <sub> · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>

## escalado (sim)

- If this requirement is not satisfied, the payout request option will not be available until you reach 50% consistency.  
  <sub>50% · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)</sub>

## riesgo_por_trade (filtro)

- Trading Without Stop Losses or Risk Management: All trades must have either pending or mental stop losses and a well-defined risk management strategy.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Using the Trailing Threshold as a Stop Loss: Traders are prohibited from using the account's full threshold as a stop-loss mechanism to absorb large losses, leading to account liquidation.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- The Violations report accounts for Scaling, Hedging, and MAE.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>
- A trade held past the MAE threshold is flagged (one violation per Trade ID).  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>

## relacion_riesgo_beneficio (filtro)

- High-Risk Strategies: Strategies that involve small profit targets while risking disproportionately large amounts are not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- For example, setting a five-tick profit target with a 150-tick stop loss demonstrates unacceptable risk management.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## ganancia_extraordinaria (filtro)

- Stockpiling Evaluation Accounts: Purchasing multiple discounted evaluation accounts to cycle through and intentionally blow up accounts in pursuit of windfall profits is not permitted.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## noticias (filtro)

- NEWS TRADING: Trading during news is allowed for your normal trading strategy.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- News trading strategies that chase the market or place orders on both sides to gamble the outcome of news is not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## horario_y_overnight (filtro)

- Calculated once daily at market close.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- The EOD Threshold is recalculated once per trading day at 4:59:59 PM ET, based on the account's closing balance.  
  <sub>4:59 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- EOD Drawdown calculated once per day at market close and enforced following trading session.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Drawdown is calculated once per trading day at market close based on your EOD balance.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- The trading day resets at 6:00 PM ET.  
  <sub>6:00 · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- EOD Drawdown calculated once per day at market close and enforced intraday.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- 30 consecutive calendar days of access including weekends and holidays; expires at 6:00 PM ET on Day 30; no extensions.  
  <sub>6:00 · [https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/)</sub>
- All trades must be closed by 4:50 PM ET.  
  <sub>4:50 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Evaluation reviewed at market close 4:59:59 PM ET, marked Passed after 6 PM ET.  
  <sub>4:59 · [https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/](https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/)</sub>
- Holding open trade positions through the market close is prohibited.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- All open trade positions must be closed prior to the market close.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Tier set from ending balance at market close 4:59:59 PM ET; applies to the next session; never changes intraday.  
  <sub>4:59 · [https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/](https://apextraderfunding.com/help-center/additional-helpful-items/scaling-levels-pa-explained/)</sub>

## instrumentos (filtro)

- Manipulation of the simulated trading environment: prohibited, including High Frequency Trading (HFT) or any other exploitative strategies, trying to manipulate the system for erroneous fills or breaching the maximum allowed contracts.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## estrategias_prohibidas (filtro)

- Engaging in prohibited activities, including hedging violations or any form of rule circumvention, will result in immediate account closure.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/) +1</sub>
- Automation and algorithm usage are not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Prohibited Activities (modified 2026-07-31).  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- You may not use the Company Services abusively or to exploit or game the purpose or spirit of the Program.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Trading without these measures is strictly prohibited.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- High-Risk Strategies: Strategies that involve small profit targets while risking disproportionately large amounts are not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Using the Trailing Threshold as a Stop Loss: Traders are prohibited from using the account's full threshold as a stop-loss mechanism to absorb large losses, leading to account liquidation.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Stockpiling Evaluation Accounts: Purchasing multiple discounted evaluation accounts to cycle through and intentionally blow up accounts in pursuit of windfall profits is not permitted.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Unsustainable Strategies: Any trading that fails to demonstrate consistent growth and sustainability is prohibited.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Manipulation of the simulated trading environment: prohibited, including High Frequency Trading (HFT) or any other exploitative strategies, trying to manipulate the system for erroneous fills or breaching the maximum allowed contracts.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Account and Resource Sharing: Sharing MAC addresses, computers, IPs, credit cards, or trade copying with other traders is strictly forbidden.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Violations result in account closure and forfeiture of funds.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Multiple Account Creation: Creating multiple user accounts is prohibited and is a bannable offense.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Holding open trade positions through the market close is prohibited.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- News trading strategies that chase the market or place orders on both sides to gamble the outcome of news is not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Holding both long and short positions simultaneously on the same or correlated instrument is strictly prohibited.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- User Summary and Trade Violations.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>
- The Violations report accounts for Scaling, Hedging, and MAE.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>
- A trade held past the MAE threshold is flagged (one violation per Trade ID).  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>
- Repeat violations lead to account enforcement, closures and forfeits.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>
- Account churning of simulated accounts is considered abuse.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>

## cobertura_y_copy (filtro)

- You may not pass Evaluation Accounts by hedging them against each other.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)</sub>
- Engaging in prohibited activities, including hedging violations or any form of rule circumvention, will result in immediate account closure.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/) +1</sub>
- No hedging, no group trading, avoid limit-up and limit-down.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Multiple Account Creation: Creating multiple user accounts is prohibited and is a bannable offense.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- The Violations report accounts for Scaling, Hedging, and MAE.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/](https://apextraderfunding.com/help-center/getting-started/user-summary-and-trade-violations/)</sub>

## bots_y_automatizacion (filtro)

- Automation and algorithm usage are not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Manipulation of the simulated trading environment: prohibited, including High Frequency Trading (HFT) or any other exploitative strategies, trying to manipulate the system for erroneous fills or breaching the maximum allowed contracts.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- No Automation or Algorithm Usage allowed: Rewards are intended to recognize human traders, not automated systems executing preprogrammed logic.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## cuentas_maximas (filtro)

- You may hold up to 20 PAs active at the same time.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)</sub>
- Up to 5 live accounts, each added after $4,500 profit, max based on PA count at graduation.  
  <sub>$4,500 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
- Stockpiling Evaluation Accounts: Purchasing multiple discounted evaluation accounts to cycle through and intentionally blow up accounts in pursuit of windfall profits is not permitted.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>
- Multiple Account Creation: Creating multiple user accounts is prohibited and is a bannable offense.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## discrecional_firma (filtro)

- News trading strategies that chase the market or place orders on both sides to gamble the outcome of news is not allowed.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## kyc_y_jurisdiccion (filtro)

- You may not use VPNs, proxy servers, cloud servers, anonymizing tools to conceal identity, device or location to evade rules or geographic restrictions.  
  <sub> · [https://apextraderfunding.com/help-center/getting-started/prohibited-activities/](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/)</sub>

## cuota (costo)

- One-time fee, not a subscription, not refundable, not transferable.  
  <sub> · [https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/)</sub>
- Professional data about $150/month covered by Apex; commissions set by the broker.  
  <sub>$150 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>

## activacion_y_reset (costo)

- If max drawdown is reached it is permanently failed; there are no reset fees and no reset options; purchase a new Evaluation.  
  <sub> · [https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/)</sub>
- 7 calendar days from Passed to pay the PA Activation Fee; cannot be extended; if missed the opportunity expires and a new Evaluation must be passed.  
  <sub> · [https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/](https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/)</sub>
- Activation fee is one-time, not refundable, not transferable.  
  <sub> · [https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/](https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/)</sub>
- If a PA is disqualified, liquidated, or closed for inactivity it is permanently closed; a new Evaluation and a new activation fee are required.  
  <sub> · [https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/](https://apextraderfunding.com/help-center/billing/pa-activation-process-deadline-explained/)</sub>
- Apex EOD 50K: price $349 list, activation fee $119.  
  <sub>$349, $119 · [apex-trader-funding](https://propfirmapp.com/prop-firms/apex-trader-funding)</sub>
- Activation fee $89-$139 for Intraday and $109-$159 for EOD accounts.  
  <sub>$89, $139, $109, $159 · [apex-trader-funding](https://propfirmapp.com/prop-firms/apex-trader-funding)</sub>

## comisiones_y_datos (costo)

- Evaluations Rithmic and Wealthcharts: EOD Threshold stops trailing and becomes fixed when it reaches an amount equal to the Target Profit balance.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- Evaluations Tradovate: EOD Drawdown trails indefinitely with the peak EOD account balance.  
  <sub> · [https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)</sub>
- Level 1 data included; DOM data is extra (Rithmic expires end of month; Tradovate/Wealthcharts billed until cancelled).  
  <sub> · [https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/)</sub>
- Evaluations Rithmic and Wealthcharts: threshold stops trailing at the Target Profit balance.  
  <sub> · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/)</sub>
- Evaluations Tradovate: trails indefinitely with the peak balance.  
  <sub> · [https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/)</sub>
- Professional data about $150/month covered by Apex; commissions set by the broker.  
  <sub>$150 · [https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/](https://apextraderfunding.com/help-center/getting-started/apex-live-prop-trading-program-faq/)</sub>
