# Inventario de reglas — Topstep

Páginas leídas: 63 · bloqueadas: 0 · oraciones con reglas: 1222

## Cobertura por categoría

| Categoría | Impacto | Oraciones |
|---|---|---|
| objetivo_beneficio | sim | 45 |
| drawdown_maximo | sim | 88 |
| drawdown_bloqueo | sim | 14 |
| perdida_diaria | sim | 120 |
| consistencia | sim | 89 |
| dias_minimos | sim | 3 |
| dias_ganadores | sim | 23 |
| plazo_maximo | sim | 26 |
| inactividad | sim | 7 |
| retiro_colchon | sim | 5 |
| retiro_frecuencia | sim | 9 |
| retiro_minimo | sim | 2 |
| retiro_maximo | sim | 33 |
| retiro_split | sim | 14 |
| retiro_cantidad | sim | 22 |
| cuenta_live | sim | 367 |
| cierre_cuenta | sim | 44 |
| contratos_maximos | sim | 57 |
| escalado | sim | 30 |
| riesgo_por_trade | filtro | 1 |
| relacion_riesgo_beneficio | filtro | 4 |
| ganancia_extraordinaria | filtro | 2 |
| tiempo_minimo_tenencia | filtro | 7 |
| noticias | filtro | 32 |
| horario_y_overnight | filtro | 70 |
| instrumentos | filtro | 9 |
| estrategias_prohibidas | filtro | 145 |
| cobertura_y_copy | filtro | 85 |
| bots_y_automatizacion | filtro | 24 |
| martingala_y_promediar | filtro | 2 |
| cuentas_maximas | filtro | 21 |
| discrecional_firma | filtro | 48 |
| kyc_y_jurisdiccion | filtro | 38 |
| cuota | costo | 90 |
| activacion_y_reset | costo | 65 |
| comisiones_y_datos | costo | 53 |

## objetivo_beneficio (sim)

- Objectives: Reach and maintain the Profit Target Consistency Target: best trading day must stay below 55% of total profits Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit (MLL) Express Funded Account™ — Standard Earn this by passing the Trading Combine®.  
  <sub>55% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- If your account was in profit before the Reset and no trades were placed after, Support may adjust your new profit target.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Rule Do not let your account balance hit or go below the Maximum Loss Limit (MLL) Objectives Reach and maintain your Profit Target Meet the Consistency Target — your best single day should stay below 55% of your Profit Target to avoid increasing your Consistency Target.  
  <sub>55% · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- You can pass in as few as two days, but keep your best day below 55% of your Profit Target.  
  <sub>55% · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Same logic applies to the Daily Loss Limit, Personal Daily Loss Limit, and Personal Daily Profit Target.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Trading Combine — Consistency Target (55%) Your single best day of profit must stay at or below 55% of your Profit Target.  
  <sub>55%, 55% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- If it exceeds that, your Profit Target increases.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- You'll need to earn more to pass. ​ Formula: Best Day Profit ÷ Total Profit = Best Day % ​ Best Day Recommendations (stay below these to avoid a Profit Target increase): Account Size Profit Target Best Day Recommendation $50K $3,000 Less than $1,650 $100K $6,000 Less than $3,300 $150K $9,000 Less than $4,950 Example: $50K account: $1,600 best day ÷ $3,000 total profit = 53% ✅ — Consistency Target met.  
  <sub>$50K, $3,000, $1,650, $100K, $6,000, $3,300 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- You can pass in as few as 2 days, as long as no single day exceeds 55% of your total profit and your Profit Target is met. ⚠️ Losses do not reset your best day.  
  <sub>2 days, 55% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- To find your new Profit Target: Best Day ÷ 0.55 = Total Profit Needed.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Example: On a $50K account, a $1,800 best day ÷ 0.55 = a $3,273 Profit Target.  
  <sub>$50K, $1,800, $3,273 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- If your next day earns $2,200, your best day becomes $2,200 and your new Profit Target becomes $4,000.  
  <sub>$2,200,, $2,200, $4,000 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- If your best day was set during the current trading session (before 3:10 PM CT), any additional profit you earn today adds directly to that best day total — which raises your adjusted Profit Target even further. ​ To resolve a Consistency Target increase, the remaining profit must be earned on a separate trading day, after the market close of the session in which your best day was set. ​ Example : You're in a $50K Trading Combine with a $3,000 Profit Target.  
  <sub>3:10, $50K, $3,000 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Your best day is $2,200 (set today, session still open), so your adjusted Profit Target is $4,000.  
  <sub>$2,200, $4,000 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Yes, but exceeding it increases your Profit Target and makes the Trading Combine harder to pass.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Now the number you see is the number that counts, so there's nothing hidden to account for. 💡 Tip: On TopstepX™, you can set a Personal Daily Profit Target to lock in your gains before exceeding the Consistency Target.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Risk Tools & Orders — What to Expect Personal Daily Loss Limit (PDLL) and Personal Daily Profit Target (PDPT) are not resting orders.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Stops, loss limits, profit targets — together, not interchangeably.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Why didn't my Personal Daily Profit Target trigger at the exact value I set?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Traders use it as a bracket — 1 side for profit target, 1 for stop loss.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Set a realistic profit target before you start.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- TopstepX™ has a Personal Daily Profit Target and lockout feature to make this automatic.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- What You Can Do on the Dashboard Instant Express Funded Account® (XFA) Activation — Hit your Profit Target and activate your XFA in real time.  
  <sub> · [10513413-getting-started-with-the-topstep-dashboard](https://help.topstep.com/en/articles/10513413-getting-started-with-the-topstep-dashboard)</sub>
- Capital Expansion — Unlocking Your Reserve Reserve funds unlock in 25% increments each time you hit the Profit Target for your LFA size.  
  <sub>25% · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- The Profit Target mirrors your Trading Combine® profit target: LFA Size Profit Target to Unlock Reserve Increment $50K $3,000 $100K $6,000 $150K $9,000 Capital Expansion is: Reviewed every Monday morning Funds deposited within 1-2 business days Can be delayed or denied for excessive or reckless risk behavior You cannot unlock multiple tiers with a single large win — each threshold requires net profit since the last expansion .  
  <sub>$50K, $3,000, $100K, $6,000, $150K, $9,000 · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- As you reach each profit target, additional funds are released from your Reserve into your unlocked balance.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Any seed capital still held in reserve by Topstep will be available to unlock as the Trader reaches the designated profit targets based on account size.  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Risk Settings for Follower Accounts Follower accounts support a Personal Daily Loss Limit (PDLL) and/or Personal Daily Profit Target (PDPT).  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Personal Daily Profit Target/Daily Loss Limit Personal Daily Profit Target/Daily Loss Limit The Personal Daily Profit Target (PDPT) and Personal Daily Loss Limit (PDLL) are optional risk settings in TopstepX that allow you to define daily profit and loss thresholds.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Phase 1: Trading Combine® Parameter Value Buying Power $25,000 Profit Target $2,000 Max Loss Limit $1,000 (static, non-trailing 🔥) Max Contracts 2 mini / 20 micro Consistency Target 55% Daily Loss Limit (DLL) Mandatory $500 Funded Activation Fee Free Price $75 one-time — no subscription.  
  <sub>$25,000, $2,000, $1,000, 2 mini, 20 micro, 55% · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Structured like our Standard Trading Combines with Daily Loss Limit (DLL), the $250K Freedom Trading Combine has a Profit Target of $15,000 and Max Loss Limit (MLL) of $10,000.  
  <sub>$250K, $15,000, $10,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Phase 1: Trading Combine® Parameter Value Buying Power $250,000 Profit Target $15,000 Max Loss Limit $10,000 Trailing End of Day Max Contracts 25 mini / 250 micro Consistency Target 55% Daily Loss Limit (DLL) Mandatory $5,000 Price $499 one-time — no subscription.  
  <sub>$250,000, $15,000, $10,000, 25 mini, 250 micro, 55% · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $3,000. $3K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $3,000 $3,000 Max Loss Limit $1,000 (static, non-trailing 🔥) $1,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $3,000, paid one time.  
  <sub>$3,000, $3K, $0, $0, $3,000, $3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $1,500. $1.5K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $1,500 $1,500 Max Loss Limit $500 (static, non-trailing 🔥) $500 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 2 micro (no minis)* 2 micro (no minis)* Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $1,500, paid one time.  
  <sub>$1,500, $1.5K, $0, $0, $1,500, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $6,000. $6K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $6,000 $6,000 Max Loss Limit $2,000 (static, non-trailing 🔥) $2,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $6,000, paid one time.  
  <sub>$6,000, $6K, $0, $0, $6,000, $6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- In the Challenge Round, you trade freely until you hit the $3,000 Profit Target.  
  <sub>$3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Upon hitting the $3,000 Profit Target, the Payout Round account will be locked for trading, and you’ll see an option to request the $3,000 payout in your dashboard.  
  <sub>$3,000, $3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- In the Challenge Round, you trade freely until you hit the $1,500 Profit Target.  
  <sub>$1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Upon hitting the $1,500 Profit Target, the Payout Round account will be locked for trading, and you'll see an option to request the $1,500 Payout in your dashboard.  
  <sub>$1,500, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- In the Challenge Round, you trade freely until you hit the $6,000 Profit Target.  
  <sub>$6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Upon hitting the $6,000 Profit Target, the Payout Round account will be locked for trading, and you'll see an option to request the $6,000 Payout in your dashboard.  
  <sub>$6,000, $6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Protect your account before emotions take over. ​ Personal Daily Profit Target Hit your profit target, and your account locks.  
  <sub> · [topstepx](https://www.topstep.com/topstepx)</sub>
- In order to graduate from the Trading Combine®, a User has to meet all profit targets, following applicable Trading Rules (defined in Section 27) and account parameters applicable to User’s Account for the applicable Trading Combine®, which remain subject to adjustment and change from time to time, without notice, and with a current schedule of Trading Rules and account parameters detailed here .  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- These milestones are the same profit targets achieved in the Trading Combine.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>

## drawdown_maximo (sim)

- Objectives: Reach and maintain the Profit Target Consistency Target: best trading day must stay below 55% of total profits Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit (MLL) Express Funded Account™ — Standard Earn this by passing the Trading Combine®.  
  <sub>55% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: 5 Winning Days of $150 or more (non-consecutive) to request a Payout Net profit greater than $0 since your last Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Express Funded Account™ — Consistency An alternative XFA path with a different Payout structure.  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: Trade at least 3 days at 40% consistency to request a Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Live Funded Account® Topstep’s prop firm capital.  
  <sub>3 days, 40% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- What happens if I break a rule (hit the Maximum Loss Limit)?  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Updated today Table of contents The Basics A Reset returns your Trading Combine® to its original starting balance — Account Balance, Maximum Loss Limit (MLL) , Consistency Target , and trading days all go back to day one.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- When to Reset Hit the Maximum Loss Limit?  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- You can Reset your account in the Topstep Dashboard or the TopstepX platform once your Trading Combine breaches the Maximum Loss Limit.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- TopstepX → Trading Combine breaches Maximum Loss Limit → Pop-up appears that shows option to Reset.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Hit the Maximum Loss Limit (MLL)?  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- Hit the Maximum Loss Limit (MLL) — Account auto-liquidates; orders rejected for the rest of the trading day.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Rule Do not let your account balance hit or go below the Maximum Loss Limit (MLL) Objectives Reach and maintain your Profit Target Meet the Consistency Target — your best single day should stay below 55% of your Profit Target to avoid increasing your Consistency Target.  
  <sub>55% · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Prohibited Conduct Prohibited Trading Strategies Maximum Loss Limit Daily Loss Limit Consistency Target Permitted Products and Trading Hours Related Articles Trading Combine Subscriptions When and What Products Can I Trade?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- What is the Maximum Loss Limit? | Topstep Help Center Copyright 2023.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- All Collections Topstep FAQs What is the Maximum Loss Limit?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- What is the Maximum Loss Limit?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit) +1</sub>
- Topstep's singular rule - the Maximum Loss Limit.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Updated over a week ago Table of contents The Maximum Loss Limit (MLL) is the lowest point your account balance is allowed to reach.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Account Size Maximum Loss Limit $50K $2,000 $100K $3,000 $150K $4,500 ⚠️ The MLL cannot be adjusted or changed.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- How the MLL works The MLL is a trailing limit.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Once it reaches your starting balance, it locks permanently. ​ 📺 Watch: How the Maximum Loss Limit works In the Trading Combine Your account starts at the full account size (e.g., $50,000 for a 50K Trading Combine), and your Maximum Loss Limit starts $2,000 below that. ​ Example: You start a 50K Trading Combine.  
  <sub>$50,000, $2,000 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- You make $500 on day 1, balance rises to $50,500, MLL trails up to $48,500.  
  <sub>$500, $50,500,, $48,500 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- You lose $500 on day 2, balance drops back to $50,000, but MLL stays at $48,500.  
  <sub>$500, $50,000,, $48,500 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- For a 50K XFA, your MLL starts at -$2,000 and trails upward.  
  <sub>$2,000 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Once your balance reaches $2,000, the MLL locks at $0 permanently.  
  <sub>$2,000,, $0 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Day 1: +$500, balance $500, MLL -$1,500.  
  <sub>$500,, $500,, $1,500 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Day 2: +$1,500, balance $2,000, MLL locks at $0. 👉 After your first Payout: Your MLL is set to $0 regardless of where it was before.  
  <sub>$1,500,, $2,000,, $0, $0 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- FAQs When is the MLL calculated?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- The MLL updates at the end of each trading day but is monitored in real time throughout the session.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- If your Net P&L hits the limit at any point during the day, your account is liquidated immediately. ​ What happens if I break the MLL?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- What happens to my MLL when I use Back2Funded?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Your MLL resets to the starting value for your account size: Account Size Starting MLL $50K XFA -$2,000 $100K XFA -$3,000 $150K XFA -$4,500 The MLL trails upward as your balance grows and locks at $0 once reached, same as a brand new XFA.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Can I request that my Maximum Loss Limit be adjusted in my account?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Maximum Loss Limits cannot be adjusted or changed on your account.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Topstep does not make exceptions to the Maximum Loss Limit for any account.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Example Maximum Loss Limit: $48,000 | Balance: $50,000 Open trade moves against you → unrealized P&L drops balance to $47,750 MLL breached → liquidation triggered Price moves favorably during exit → final realized balance: $48,050 Final balance above the limit doesn't matter.  
  <sub>$48,000, $50,000, $47,750, $48,050 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Best Practices Use stop losses before approaching your Maximum Loss Limit Monitor unrealized P&L — not just closed trades Leave a buffer above your limit during volatile markets Avoid trading during high-impact news events ⚠️ Your Maximum Loss Limit is calculated on real-time unrealized P&L.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Express Funded Account Standard Rule Do not hit your Maximum Loss Limit Objectives Follow the Scaling Plan — the max contracts you can hold at one time — based on your current account balance.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Express Funded Account Consistency Rule Do not hit your Maximum Loss Limit Objectives Follow the Scaling Plan — the max contracts you can hold at one time — based on your current account balance.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- What happens if I breach the Maximum Loss Limit?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Related Articles What is the Maximum Loss Limit?  
  <sub> · [8284225-staying-outside-the-2-price-limit-zone](https://help.topstep.com/en/articles/8284225-staying-outside-the-2-price-limit-zone) +4</sub>
- After each Payout: Your Maximum Loss Limit (MLL) resets to $0 permanently, and your 5-day count restarts.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- After each Payout: Your Maximum Loss Limit resets to $0 permanently, your consistency calculation resets, and your 3-day count restarts.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Note: Requesting a full 100% Payout closes your LFA since the balance reaches the Maximum Loss Limit.  
  <sub>100% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- How do Payouts affect my Maximum Loss Limit?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Your MLL is set to $0 after your first Payout.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Will I still get my Payout if I hit the MLL after requesting?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Once the Payout amount has been deducted from your balance, hitting the MLL won't affect it.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- We recommend reaching a balance where your MLL is at $0 first.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- MLL levels by account size: Account Size Maximum Loss Limit $50K $2,000 $100K $3,000 $150K $4,500 Please note: the trading day your Payout is requested will not count toward your winning days for the next Payout cycle.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- When that happens, realized losses may exceed your Maximum Loss Limit or Personal Daily Loss Limit — triggering automatic liquidation.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Orders & Slippage — FAQs How does slippage affect my Maximum Loss Limit?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Slippage can push your account past your Maximum Loss Limit faster than you expect.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Review your stop placement and size for high-volatility conditions to make sure they match your actual risk tolerance. 📺 Click below to watch an informative video from Mick, one of Topstep's Risk Managers, as he explains how slippage works.👇 Topstep Risk Disclosure Related Articles What is the Maximum Loss Limit?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Exploiting platform deficiencies — using instruments or methods that misuse bugs, errors, or deficiencies in the platform Circumventing geographical or technical restrictions Holding a position within 2% of a product’s price lock limit — see How to Ensure I Am Not Trading Within 2% of a Price Limit Trading on behalf of others — including sharing incentives as part of any business arrangement Account stacking — repeatedly hitting the Maximum Loss Limit in one account and switching to another to repeat high-risk attempts Any other conduct that Topstep determines, at its sole discretion, is uncommercial, games the market, is not a viable strategy, or is not responsible trading Do not use a VPN.  
  <sub>2%, 2% · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Account Stacking Repeatedly trading aggressively, hitting the Maximum Loss Limit (MLL) in one account, then switching to another account and repeating.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Do’s and Don’ts of Responsible Trading: Yes No Trade like it's real capital Show up with a plan Define risk before you click Know the news and size accordingly Lock in gains, stack green days Review, refine, repeat Trade without stops Size up after a loss Disrespect your daily limits Go full port, especially on news Trade on tilt, FOMO, or revenge Use MLL as a stop loss 🎯 Knowing when to stop with profit Greed turns winning days into losing ones.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- You might end up here if you: Hit the Maximum Loss Limit on multiple accounts in 1 day Max position the majority of your trades Let losers run bigger than winners Trade without stops Go full port, trade on tilt, FOMO, or revenge Disrespect your daily limits Can't trade small?  
  <sub>1 day · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- It's not a punishment — it's a structured path to rebuild discipline, consistency, and sound risk management. ​ This program gets you back on track — building the discipline and habits needed to trade responsibly in Live markets. 👉 You may need the Responsible Trading Program if: Multiple accounts hit the Maximum Loss Limit in one day You max position a majority of your trades You don’t keep losers smaller than winners You don’t use stops You go full port or trade on tilt, FOMO, or revenge You disrespect your daily limits Can't trade small?  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- Reset Pricing Account Size Standard Path No Activation Fee Path 50K $49 $95 100K $99 $149 150K $199 $229 You may purchase a Reset from your Topstep dashboard, or within the TopstepX platform once your Trading Combine breaches the Maximum Loss Limit .  
  <sub>$49, $95, $99, $149, $199, $229 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- … 28 más en inventario.json

## drawdown_bloqueo (sim)

- Once your balance reaches $2,000, the MLL locks at $0 permanently.  
  <sub>$2,000,, $0 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Day 2: +$1,500, balance $2,000, MLL locks at $0. 👉 After your first Payout: Your MLL is set to $0 regardless of where it was before.  
  <sub>$1,500,, $2,000,, $0, $0 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Your MLL resets to the starting value for your account size: Account Size Starting MLL $50K XFA -$2,000 $100K XFA -$3,000 $150K XFA -$4,500 The MLL trails upward as your balance grows and locks at $0 once reached, same as a brand new XFA.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- A future day becomes your new best day if it exceeds the previous one and locks at 3:10 PM CT on its own day.  
  <sub>3:10 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Optional dashed High/Low lines — a feature you requested — now lock at session close and persist through the day.  
  <sub> · [8524249-topstepx-indicators](https://help.topstep.com/en/articles/8524249-topstepx-indicators)</sub>
- Trend Magic 🧲 👉 An ATR-based trailing stop line that shifts color when momentum flips.  
  <sub> · [8524249-topstepx-indicators](https://help.topstep.com/en/articles/8524249-topstepx-indicators)</sub>
- Trailing Stop Trails the market in set increments.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Trailing Stop Locks in a stop at a set distance, then automatically moves it as price moves in your favor.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Order Management Overview Types of Orders Order Type Description Market Order Filled immediately at the current market price Limit Order Filled at a specific price you set Stop Market Order Pending until conditions are met; used to limit losses or enter after a confirmed directional move OCO (One Cancels the Other) 2 linked orders — when 1 executes, the other cancels automatically Trailing Stop Order A stop that trails the market in set increments as price moves away Filled Order An order that has been executed Open/Pending Order An order waiting to be filled Risk (Stop) Amount (USD) you're willing to lose on a position.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Position closes when reached; updates as size changes Learn more about Order Types here . ​ Order Ticket Select Buy or Sell, pick your order type (Market, Limit, Stop Market, Trailing Stop, or OCO), and access Cancel All, Flatten All, and Reverse Position.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Can't be changed until the next trading day Unlocks at 5 PM CT Support cannot reverse a lock once applied Setup: Settings → Risk Settings → set limits → Save → Lock Risk Settings for Day → Confirm.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- A blue-outlined dot shows it's active to move Order types on mobile charts — Market, Limit, Stop, and Trailing Stop, all accessible from the same " " button 🛜 Important: Because mobile performance depends on your device, Wi-Fi, and data provider, we’re unable to troubleshoot mobile-specific issues that may be related to connectivity.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- You must finish the month net positive to qualify for a bonus, but the leaderboard locks at month end — you still have time to recover and fight your way into the top 100.  
  <sub> · [15764697-the-topstep-octagon](https://help.topstep.com/en/articles/15764697-the-topstep-octagon)</sub>
- If your Max Loss Limit balance increases to $0, your account will lock at $0.  
  <sub>$0,, $0 · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>

## perdida_diaria (sim)

- Objectives: 5 Winning Days of $150 or more Do not hit or exceed the Daily Loss Limit (DLL) — breaching it deactivates your account for that trading day Rule: Do not let your Account Balance reach or go below $0 Key Links Trading Combine® Parameters Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Consistency at Topstep Express Funded Account™ Parameters Topstep Payout Policy What is the Responsible Trading Program?  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Rules: Tied to a specific account size AND type (Standard, No Activation Fee, or DLL) Credits issued before 12/11/2025 — no expiration Credits issued on or after 12/11/2025 — expire 1 year after added Can't transfer between types or sizes Can't combine (two 50K credits can't Reset a 100K) Can't use credits to buy a new Trading Combine — only on an existing active subscription Oldest matching credit will be used first Reset FAQs What does a Reset cost?  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Hit the Personal Daily Loss Limit — Account auto-liquidates; orders rejected for the rest of the trading day.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Prohibited Conduct Prohibited Trading Strategies Maximum Loss Limit Daily Loss Limit Consistency Target Permitted Products and Trading Hours Related Articles Trading Combine Subscriptions When and What Products Can I Trade?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Express Funded Account™ Parameters Topstep Payout Policy Daily Loss Limit in the Trading Combine and Express Funded Account Did this answer your question?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Same logic applies to the Daily Loss Limit, Personal Daily Loss Limit, and Personal Daily Profit Target.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Express Funded Account™ Parameters Topstep Payout Policy Daily Loss Limit in the Trading Combine and Express Funded Account What is a Pro Account?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Hit 5 winning days with at least $150 profit each If you’ve chosen to add a Daily Loss Limit, you must stay within the limits each day.  
  <sub>$150 · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Trade at least 3 days with at least 1 trade per day Keep your consistency at 40% or below: Consistency = Largest Winning Day ÷ Total Net Profit If you’ve chosen to add a Daily Loss Limit, you must stay within the limits each day.  
  <sub>3 days, 40% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- TopstepX™ — Commissions and Fees Daily Loss Limit in the Trading Combine and Express Funded Account Topstep Holiday Trading Hours CME Velocity Logic Did this answer your question?  
  <sub> · [8284225-staying-outside-the-2-price-limit-zone](https://help.topstep.com/en/articles/8284225-staying-outside-the-2-price-limit-zone)</sub>
- Take your Payouts, stay consistent, and position yourself for Live — where there are no caps and no ceiling on what you can earn. ⏰ Limited Time Offering: Add a Daily Loss Limit (DLL) at checkout in the Trading Combine, and increase your Payout Cap once you pass and activate an Express Funded Account.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Available starting at 3:30 PM CT on Tuesday, June 2nd. ​ Traders who voluntarily add a Daily Loss Limit to their account unlock double per-request payout caps.  
  <sub>3:30 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- No DLL added = current caps remain unchanged.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Account Path Current Cap With DLL (new) $50K Standard $2,000 $4,000 $50K Consistency $3,000 $6,000 $100K Standard $3,000 $6,000 $100K Consistency $4,000 $8,000 $150K Standard $5,000 $10,000 $150K Consistency $6,000 $12,000 Limited Time Offering: Payout Cap Increase FAQs Is this available for all Traders?  
  <sub>$50K, $2,000, $4,000, $50K, $3,000, $6,000 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- All Traders who make a new Trading Combine purchase and add a Daily Loss Limit (DLL) at checkout will receive the increased Payout cap, during this limited time offering beginning at 3:30 PM CT on Tuesday, June 2nd. ​ ​ Why is this a limited-time offering, and how long will this last?  
  <sub>3:30 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- If I add a DLL at checkout during Express Funded Account activation or Reactivation, will I still get the increased Payout cap?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Only if you already added the DLL when you purchased your Trading Combine.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- If I already added a Daily Loss Limit before this release, will I see an increased Payout cap?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- That said, the DLL still protects you.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- I hit the Daily Loss Limit, can I still request a Payout?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Hitting the Daily Loss Limit puts your account in a Temporary Violation.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- When that happens, realized losses may exceed your Maximum Loss Limit or Personal Daily Loss Limit — triggering automatic liquidation.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Risk Tools & Orders — What to Expect Personal Daily Loss Limit (PDLL) and Personal Daily Profit Target (PDPT) are not resting orders.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Your Personal Daily Loss Limit is a backstop.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Can I use my Personal Daily Loss Limit as a stop loss?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- The Personal Daily Loss Limit monitors your unrealized P&L and triggers when your threshold is crossed.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Your Personal Daily Loss Limit is a backstop — not a replacement. 🧠 Learn more about the PDLL and PDPT here .  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Daily Loss Limit in the Trading Combine and Express Funded Account What is the Focused Trader Program?  
  <sub> · [10370307-reset-purchase-limits](https://help.topstep.com/en/articles/10370307-reset-purchase-limits)</sub>
- Daily Loss Limit in the Trading Combine and Express Funded Account | Topstep Help Center Copyright 2023.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- All Collections Topstep FAQs Daily Loss Limit in the Trading Combine and Express Funded Account Daily Loss Limit in the Trading Combine and Express Funded Account Bad days happen.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- The Daily Loss Limit (DLL) makes sure one bad day doesn't wipe out your account.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- June 30, 2026 Table of contents Overview The Daily Loss Limit (DLL) is optional in the Trading Combine® and Express Funded Account® (XFA).  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- What Happens When It Triggers Net P&L hits or exceeds the DLL during the trading day (5 PM CT – 3:10 PM CT): Open positions are flattened Pending orders are canceled No new trades until 5 PM CT next session ☝️ Account stays eligible for funding.  
  <sub>3:10 · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Example: $150K Trading Combine® with a $3,000 DLL.  
  <sub>$150K, $3,000 · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Set It at Purchase You now have the option to add a Daily Loss Limit at checkout when purchasing a Trading Combine or activating/Reactivating an Express Funded Account.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- The Daily Loss Limit parameters are: $50K Account: $1,000 $100K Account: $2,000 $150K Account: $3,000 ⚠️ Important: Daily Loss Limit at checkout is fixed (no changes later) Applies to your Express Funded Account after you pass All original account rules and objectives still apply Trader Tip: Over 63% of traders have lost account in a single day.  
  <sub>$50K, $1,000, $100K, $2,000, $150K, $3,000 · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Adding a DLL to your account caps how much you can lose in a single session, so one bad day doesn’t turn into a closed account.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account) +1</sub>
- The traders who last… manage risk first! ​ Adding a Daily Loss Limit helps you: Stay disciplined Protect your account Trade like it’s real capital 💪 Always trade for tomorrow.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account) +1</sub>
- Responsible Trading Discount There's now a Responsible Trading Discount when you add a DLL at purchase for No Activation Fee Trading Combines and Back2Funded Reactivations.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- No Activation Fee Trading Combine Back2Funded Reactivation $10 off → 50K $20 off → 100K $30 off → 150K $50 off Reactivation Fees ⏰ Limited Time Offering: Add a Daily Loss Limit at checkout in the Trading Combine, and increase your Payout Cap once you pass and activate an Express Funded Account.  
  <sub>$10, $20, $30, $50 · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- If you don't set a Daily Loss Limit at purchase After purchasing, you can still add a Daily Loss Limit manually through Risk Settings.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Unlike Daily Loss Limits set at purchase, manual limits can be adjusted or removed at any time — making it easier to rationalize bad habits in the moment.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Set it Manually — Personal Daily Loss Limit (PDLL) Didn't set one at purchase?  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Add a Personal Daily Loss Limit (PDLL) in Risk Settings any time.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- FAQs Can Topstep remove my DLL or PDLL for me?  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Is hitting the DLL a rule violation?  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- How does the Daily Loss Limit work in the Live Funded Account?  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- All Live Funded Account accounts have a Daily Loss Limit.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Credits are tied to a specific account size and path (Standard, Daily Loss Limit, or No Activation Fee) and expire 1 year after issue. 👉 Your Dashboard shows: how many Reset Credits you have, which sizes and paths they apply to, and expiration dates.  
  <sub> · [10513413-getting-started-with-the-topstep-dashboard](https://help.topstep.com/en/articles/10513413-getting-started-with-the-topstep-dashboard)</sub>
- Daily Loss Limit and Maximum Position Size Maximum Position Size: The maximum number of contracts you can hold open at one time, per account.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Learn more here: Dynamic Live Risk Expansion Live Funded Accounts start with a Daily Loss Limit (DLL) based on account size: LFA Size Standard DLL $50K $2,000 $100K $3,000 $150K $4,500 Regardless of account size, if your tradable balance drops to lower thresholds, the DLL and Maximum Position Size automatically adjust: Tradable Balance DLL Max Position Size $10,000 or below $2,000 5 $5,000 or below $1,000 3 ☝️ These limits update on Fridays and return to standard levels once your balance rises back above the thresholds.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Updated this week Table of contents Topstep's Dynamic Live Risk Expansion adjusts your Daily Loss Limit (DLL) and Maximum Position Size (contract limits) as your Live Funded Account® (LFA) profits grow.  
  <sub> · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Starting Daily Loss Limit and Maximum Position Size Account Size Starting Daily Loss Limit Maximum Position Size 50K $2,000 5 100K $3,000 10 150K $4,500 15 How Tiers Work Your net profit determines your Tier.  
  <sub>$2,000, $3,000, $4,500 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Your Daily Loss Limit increases at end of day after 10 Active Trading Days in the new Tier.  
  <sub> · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- If your net profit falls below your Tier at end of day, your Daily Loss Limit scales down that same day.  
  <sub> · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Expansion Table Maximum Position Size Profit Daily Loss Limit Up to 100 lots 1M Up to $100,000 Up to 70 lots 550K Up to $50,000 Up to 50 lots 200K Up to $20,000 Up to 30 lots 100K Up to $10,000 — 50K Up to $6,000 — 20K Up to $5,500 — 15K Up to $5,000 Position Limits remain at the max for each account size (5 lots for $50Ks, 10 lots for $100Ks, 15 lots for $150Ks) until the account reaches Tier 4 with with $100K in profit.  
  <sub>$100,000, $50,000, $20,000, $10,000, $6,000, $5,500 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- For the first three tiers, +$500 is added to your starting Daily Loss Limit for each tier you achieve: $50K Account (Starts at $2,000 DLL): $15k Profit -> $2,500 DLL $20k Profit -> $3,000 DLL $50k Profit -> $3,500 DLL $100K Account (Starts at $3,000 DLL): $15k Profit -> $3,500 DLL $20k Profit -> $4,000 DLL $50k Profit -> $4,500 DLL $150K Account (Starts at $4,500 DLL): $15k Profit -> $5,000 DLL $20k Profit -> $5,500 DLL $50k Profit -> $6,000 DLL Once an account reaches $100k in net profit, Daily Loss Limits and Maximum Position Sizes align across all account types (as shown in Tier 4+).  
  <sub>$500, $50K, $2,000, $15k, $2,500, $20k · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Required Equity Thresholds for Expansion The Risk Team may adjust your Daily Loss Limit and Maximum Position Size based on net equity — even if you haven't moved through the expansion tiers.  
  <sub> · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Adjustments may be considered when a Live Funded Account reaches: $10,000 net equity in a 50K account $15,000 net equity in a 100K account $20,000 net equity in a 150K account Daily Loss Limit Safeguard Regardless of account size, if your tradable balance drops to lower thresholds, the DLL and Maximum Position Size automatically adjust: ☝️ These limits update on Fridays and return to standard levels once your balance rises back above the thresholds.  
  <sub>$10,000, $15,000, $20,000 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- … 60 más en inventario.json

## consistencia (sim)

- Objectives: Reach and maintain the Profit Target Consistency Target: best trading day must stay below 55% of total profits Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit (MLL) Express Funded Account™ — Standard Earn this by passing the Trading Combine®.  
  <sub>55% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: 5 Winning Days of $150 or more (non-consecutive) to request a Payout Net profit greater than $0 since your last Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Express Funded Account™ — Consistency An alternative XFA path with a different Payout structure.  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: Trade at least 3 days at 40% consistency to request a Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Live Funded Account® Topstep’s prop firm capital.  
  <sub>3 days, 40% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: 5 Winning Days of $150 or more Do not hit or exceed the Daily Loss Limit (DLL) — breaching it deactivates your account for that trading day Rule: Do not let your Account Balance reach or go below $0 Key Links Trading Combine® Parameters Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Consistency at Topstep Express Funded Account™ Parameters Topstep Payout Policy What is the Responsible Trading Program?  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Updated today Table of contents The Basics A Reset returns your Trading Combine® to its original starting balance — Account Balance, Maximum Loss Limit (MLL) , Consistency Target , and trading days all go back to day one.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Rule Do not let your account balance hit or go below the Maximum Loss Limit (MLL) Objectives Reach and maintain your Profit Target Meet the Consistency Target — your best single day should stay below 55% of your Profit Target to avoid increasing your Consistency Target.  
  <sub>55% · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Big spike days don't build funded traders, consistency does.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- You can pass in as few as two days, but keep your best day below 55% of your Profit Target.  
  <sub>55% · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- If it still shows Active after 30 minutes, verify your Consistency Target has been met. 👉 A few things to keep in mind: Passed on a Friday?  
  <sub>30 minutes · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Prohibited Conduct Prohibited Trading Strategies Maximum Loss Limit Daily Loss Limit Consistency Target Permitted Products and Trading Hours Related Articles Trading Combine Subscriptions When and What Products Can I Trade?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Consistency at Topstep | Topstep Help Center Copyright 2023.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- All Collections Topstep FAQs Consistency at Topstep Consistency at Topstep Consistency Targets and Consistency Objectives: What Every Topstep Trader Needs to Know Updated over a week ago Table of contents Consistency rules exist because big spike days don't build funded traders.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Here's how the Consistency rules work in the Trading Combine® and the Express Funded Account®.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Trading Combine — Consistency Target (55%) Your single best day of profit must stay at or below 55% of your Profit Target.  
  <sub>55%, 55% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- You'll need to earn more to pass. ​ Formula: Best Day Profit ÷ Total Profit = Best Day % ​ Best Day Recommendations (stay below these to avoid a Profit Target increase): Account Size Profit Target Best Day Recommendation $50K $3,000 Less than $1,650 $100K $6,000 Less than $3,300 $150K $9,000 Less than $4,950 Example: $50K account: $1,600 best day ÷ $3,000 total profit = 53% ✅ — Consistency Target met.  
  <sub>$50K, $3,000, $1,650, $100K, $6,000, $3,300 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- You can pass in as few as 2 days, as long as no single day exceeds 55% of your total profit and your Profit Target is met. ⚠️ Losses do not reset your best day.  
  <sub>2 days, 55% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- The Consistency Target applies regardless of your current account balance.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Can I fix a Consistency increase by trading more on the same day?  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- If your best day was set during the current trading session (before 3:10 PM CT), any additional profit you earn today adds directly to that best day total — which raises your adjusted Profit Target even further. ​ To resolve a Consistency Target increase, the remaining profit must be earned on a separate trading day, after the market close of the session in which your best day was set. ​ Example : You're in a $50K Trading Combine with a $3,000 Profit Target.  
  <sub>3:10, $50K, $3,000 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Now the number you see is the number that counts, so there's nothing hidden to account for. 💡 Tip: On TopstepX™, you can set a Personal Daily Profit Target to lock in your gains before exceeding the Consistency Target.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Express Funded Account Consistency — Consistency Objective (40%) The Consistency path in the Express Funded Account® (XFA) rewards Traders who build profit steadily, not in one big day.  
  <sub>40% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- When you activate your XFA, you choose Standard or Consistency as your Payout path.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- The Consistency path gets you to Payout eligibility faster but adds a 40% threshold.  
  <sub>40% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Formula: Largest Single-Day Net Profit ÷ Total Net Profit = Consistency % Your Consistency % must be 40% or below to be Payout eligible.  
  <sub>40% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- To request a Payout, you must also have: A minimum of 3 trading days with at least 1 trade per day Example: $3,600 largest day ÷ $9,500 total net profit = 37.9% ✅ If your Consistency % exceeds 40%, keep trading.  
  <sub>$3,600, $9,500, 37.9%, 40% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- As you earn more net profit, the percentage will naturally come down. 👉 Your dashboard updates in real time and shows your Consistency %, total net profit, largest single-day profit, and Payout eligibility status. ​ Does Consistency reset after a Payout?  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- After a Payout is requested, your consistency calculation resets to $0 and applies only to profits earned in the new window.  
  <sub>$0 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Trades made on the same day as your Payout request do not count toward your next Consistency Objective, even if made after the request was submitted. 👉 Consistency Examples You request a Payout on Monday.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Your balance drops to $10,000, but your consistency resets to $0.  
  <sub>$10,000,, $0 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- At activation, you choose your Payout path: Standard or Consistency. 🤜 The XFA is the proving ground.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Express Funded Account Consistency Rule Do not hit your Maximum Loss Limit Objectives Follow the Scaling Plan — the max contracts you can hold at one time — based on your current account balance.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Trade at least 3 days with at least 1 trade per day Keep your consistency at 40% or below: Consistency = Largest Winning Day ÷ Total Net Profit If you’ve chosen to add a Daily Loss Limit, you must stay within the limits each day.  
  <sub>3 days, 40% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- XFA Consistency FAQs What is XFA Consistency?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- But no single day can make up more than 40% of your total profits.  
  <sub>40% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Consistency is reset after each Payout. ​ How is consistency calculated? 👉 Consistency = Largest Winning Day ÷ Total Net Profit Consistency tracking only appears on your dashboard once you have positive net profit.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Consistency is calculated for each payout window.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Why does the Consistency Target exist?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Can I have a mix of Standard and Consistency XFA accounts?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- How does a Payout affect my Consistency?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Your consistency calculation resets after each Payout and applies only to profits earned afterward.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Example: You earn $15,000 over 3 days ($5,000 each = 33% consistency ✅) and take a $5,000 Payout.  
  <sub>$15,000, 3 days, $5,000, 33%, $5,000 · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Your remaining balance is $10,000, but your consistency clock resets.  
  <sub>$10,000, · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Once you select XFA Consistency or Standard, that choice cannot be changed either.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Steps to Activate From the Trade Report of your passed Trading Combine®, click "Activate Express Funded Account." If you have multiple passed Trading Combines, confirm the correct account before clicking. ​ Select your XFA type — Standard or Consistency.  
  <sub> · [8284217-express-funded-account-activation](https://help.topstep.com/en/articles/8284217-express-funded-account-activation)</sub>
- Stack 30 winning days in your Live Funded Account® and you unlock daily access to up to 100% of your profits.  
  <sub>100% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Express Funded Account® Consistency.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Standard Path Consistency Path 5 winning days of $150+ 3 days with 40% consistency target Request 50% of the account balance up to $5000* Request 50% of the account balance up to $6,000* 90/10 split 90/10 split ⚠️ Note for traders who joined the new Topstep dashboard before January 12, 2026: You receive 100% of your first $10,000 in lifetime profits.  
  <sub>$150, 3 days, 40%, 50%, $5000, 50% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Account Size XFA Standard XFA Consistency $50K $2,000 $3,000 $100K $3,000 $4,000 $150K $5,000 $6,000 👉 Payout caps apply to XFA accounts only.  
  <sub>$50K, $2,000, $3,000, $100K, $3,000, $4,000 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Account Path Current Cap With DLL (new) $50K Standard $2,000 $4,000 $50K Consistency $3,000 $6,000 $100K Standard $3,000 $6,000 $100K Consistency $4,000 $8,000 $150K Standard $5,000 $10,000 $150K Consistency $6,000 $12,000 Limited Time Offering: Payout Cap Increase FAQs Is this available for all Traders?  
  <sub>$50K, $2,000, $4,000, $50K, $3,000, $6,000 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Yes — Standard and Consistency both qualify.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Payout 1 $6,000 (starting from $0) ✅ No profit requirement on first Payout Take $3,000 Payout New balance: $3,000 — Payout 2 $4,000 (up from $3,000) ✅ Profitable since last Payout Take $1,800 Payout New balance: $2,200 — Payout 3 $4,500 (up from $2,200) ✅ Profitable since last Payout Take $2,000 Payout New balance: $2,500 — Payout 4 $1,800 (down from $2,500) ❌ Not profitable — keep trading Express Funded Account Consistency To request a Payout, you must meet both requirements: 3 trading days with at least 1 trade per day.  
  <sub>$6,000, $0, $3,000, $3,000, $4,000, $3,000 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Stay at or below the 40% consistency target.  
  <sub>40% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Your largest single day cannot exceed 40% of your total net profit.  
  <sub>40% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- After each Payout: Your Maximum Loss Limit resets to $0 permanently, your consistency calculation resets, and your 3-day count restarts.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Reset limits reinforce Responsible Trading by helping you recognize when to step away, build stronger risk management habits, and focus on long-term consistency over short-term emotional decisions.  
  <sub> · [10370307-reset-purchase-limits](https://help.topstep.com/en/articles/10370307-reset-purchase-limits)</sub>
- Consistency first — then size and scale.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading) +1</sub>
- From there, demonstrate consistency in an XFA before being called back up to Live.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Can I use Back2Funded on XFA Standard and XFA Consistency?  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- July 21, 2026 Table of contents The Basics The Responsible Trading Program exists because we're seeing a common theme among struggling Traders: inconsistency, emotional tilt, and lack of discipline.  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- … 29 más en inventario.json

## dias_minimos (sim)

- Objectives: Trade at least 3 days at 40% consistency to request a Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Live Funded Account® Topstep’s prop firm capital.  
  <sub>3 days, 40% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- To request a Payout, you must also have: A minimum of 3 trading days with at least 1 trade per day Example: $3,600 largest day ÷ $9,500 total net profit = 37.9% ✅ If your Consistency % exceeds 40%, keep trading.  
  <sub>$3,600, $9,500, 37.9%, 40% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Trade at least 3 days with at least 1 trade per day Keep your consistency at 40% or below: Consistency = Largest Winning Day ÷ Total Net Profit If you’ve chosen to add a Daily Loss Limit, you must stay within the limits each day.  
  <sub>3 days, 40% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>

## dias_ganadores (sim)

- Objectives: 5 Winning Days of $150 or more (non-consecutive) to request a Payout Net profit greater than $0 since your last Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Express Funded Account™ — Consistency An alternative XFA path with a different Payout structure.  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: 5 Winning Days of $150 or more Do not hit or exceed the Daily Loss Limit (DLL) — breaching it deactivates your account for that trading day Rule: Do not let your Account Balance reach or go below $0 Key Links Trading Combine® Parameters Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Consistency at Topstep Express Funded Account™ Parameters Topstep Payout Policy What is the Responsible Trading Program?  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Hit 5 winning days with at least $150 profit each If you’ve chosen to add a Daily Loss Limit, you must stay within the limits each day.  
  <sub>$150 · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Trade at least 3 days with at least 1 trade per day Keep your consistency at 40% or below: Consistency = Largest Winning Day ÷ Total Net Profit If you’ve chosen to add a Daily Loss Limit, you must stay within the limits each day.  
  <sub>3 days, 40% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Instead of 5 winning days, you need 3 trading days.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Consistency is reset after each Payout. ​ How is consistency calculated? 👉 Consistency = Largest Winning Day ÷ Total Net Profit Consistency tracking only appears on your dashboard once you have positive net profit.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Stack 30 winning days in your Live Funded Account® and you unlock daily access to up to 100% of your profits.  
  <sub>100% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Standard Path Consistency Path 5 winning days of $150+ 3 days with 40% consistency target Request 50% of the account balance up to $5000* Request 50% of the account balance up to $6,000* 90/10 split 90/10 split ⚠️ Note for traders who joined the new Topstep dashboard before January 12, 2026: You receive 100% of your first $10,000 in lifetime profits.  
  <sub>$150, 3 days, 40%, 50%, $5000, 50% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Express Funded Account Standard To request a Payout, you must meet both requirements: 5 winning days of $150+ Net P&L.  
  <sub>$150 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Live Funded Account 5 winning days of $150+ Net P&L per Payout cycle (not consecutive) Request up to 50% of your account balance with no dollar cap After you request a Payout, your winning day count restarts.  
  <sub>$150, 50% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- You'll need 5 new winning days before you're eligible to request your next Payout.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Daily Payouts (after 30 winning days in the LFA): Once you've earned $150+ Net P&L on 30 non-consecutive days in your Live Funded Account, you unlock daily Payouts — request as much of your unlocked balance as you want, once per day (min $125).  
  <sub>$150, $125 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Winning days from the XFA do not count toward this total.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- However, please keep in mind the Payout processing times to determine which trading day will not count toward winning day objectives.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- MLL levels by account size: Account Size Maximum Loss Limit $50K $2,000 $100K $3,000 $150K $4,500 Please note: the trading day your Payout is requested will not count toward your winning days for the next Payout cycle.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Do’s and Don’ts of Responsible Trading: Yes No Trade like it's real capital Show up with a plan Define risk before you click Know the news and size accordingly Lock in gains, stack green days Review, refine, repeat Trade without stops Size up after a loss Disrespect your daily limits Go full port, especially on news Trade on tilt, FOMO, or revenge Use MLL as a stop loss 🎯 Knowing when to stop with profit Greed turns winning days into losing ones.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Once I have 30 winning days, can I take a 100% payout?  
  <sub>100% · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Everything resets to zero: balance, P&L, trade history, and winning days.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- Payouts Payout rules are the same as a standard Express Funded Account: 5 or more winning days of $150 (non-consecutive), Payout up to 50% of the account and up to $5,000, and net positive after your first Payout. ​ Account Size Payout Cap $50K $2,000 $100K $3,000 $150K $5,000 Call Up Process Topstep's Risk team will reach out when you're ready to move to a Pro Account.  
  <sub>$150, 50%, $5,000,, $50K, $2,000, $100K · [14645398-what-is-a-pro-account](https://help.topstep.com/en/articles/14645398-what-is-a-pro-account)</sub>
- They start the next day with $1,000 of room. ​ Static (this Trading Combine): The Max Loss Limit never moves.  
  <sub>$1,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Reactivated Standard XFAs may request a payout after five (5) winning days of $150 or more.  
  <sub>$150 · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- On the Standard Path after every 5 winning days of $150+.  
  <sub>$150 · [instant-payouts](https://www.topstep.com/instant-payouts)</sub>

## plazo_maximo (sim)

- Accounts must have no trading activity Contact us within 28 days of the charge.  
  <sub>28 days · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Each Rebill adds 1 Reset credit to your Reset Bank (same size and account type, expires 1 year from issue).  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- No time limit for passing.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Rules: Tied to a specific account size AND type (Standard, No Activation Fee, or DLL) Credits issued before 12/11/2025 — no expiration Credits issued on or after 12/11/2025 — expire 1 year after added Can't transfer between types or sizes Can't combine (two 50K credits can't Reset a 100K) Can't use credits to buy a new Trading Combine — only on an existing active subscription Oldest matching credit will be used first Reset FAQs What does a Reset cost?  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Keep an eye on our social channels to find out when this offer will expire and what is coming up next.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Order stays in the book until it's filled, canceled, or expired.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Credits are tied to a specific account size and path (Standard, Daily Loss Limit, or No Activation Fee) and expire 1 year after issue. 👉 Your Dashboard shows: how many Reset Credits you have, which sizes and paths they apply to, and expiration dates.  
  <sub> · [10513413-getting-started-with-the-topstep-dashboard](https://help.topstep.com/en/articles/10513413-getting-started-with-the-topstep-dashboard)</sub>
- My requests are being rejected after they worked earlier Session tokens expire.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- An XFA that was eligible for Back2Funded 10 days ago will now have 20 days remaining, even though the original 7-day reactivation window expired.  
  <sub>10 days, 20 days · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- If you do not Reactivate within 30 days, the Back2Funded offer expires for that account.  
  <sub>30 days · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- What You Need A valid, unexpired original physical government-issued ID: Passport, Driver's License, or National ID card A device with a camera (phone or computer) Not accepted: photocopies, images displayed on another screen, or IDs with sticky notes or coverings.  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- How to Complete Identity Verification Prepare your unexpired, physical ID Open the secure link or QR code from your email Take clear photos of your ID (front and back where applicable) Take a selfie Submit Once complete, your account status updates to Verification Complete .  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- Troubleshooting If you're having issues: Try a different browser (Chrome, Safari) or a different device Clear your browser's cache and cookies, then restart your device Make sure camera and microphone access are enabled Confirm your ID is unexpired and a physical document (not a photocopy) Resubmit using the secure link or QR code from your email Avoid using VPNs or VPS — location discrepancies can cause verification issues Ensure your device's time zone and location settings are accurate FAQ Why am I being asked to verify again?  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- Each reward code expires 90 days from the date it's issued.  
  <sub>90 days · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Once your oldest code expires, you're eligible to earn another.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Please note, this Trading Combine expires 90 days after purchase.  
  <sub>90 days · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- The account will expire and close after 90 days.  
  <sub>90 days · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- The account will expire and close after 90 days. $6K Challenge Is this a limited release, and can I buy more than one?  
  <sub>90 days, $6K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Alerts expire at midnight (12:00 AM) in the time zone of the computer you created them on.  
  <sub>12:00 · [16948328-topstepx-price-alerts](https://help.topstep.com/en/articles/16948328-topstepx-price-alerts)</sub>
- Price Alert FAQs Timing, expiration, and conditions ​ What exact time does an alert expire?  
  <sub> · [16948328-topstepx-price-alerts](https://help.topstep.com/en/articles/16948328-topstepx-price-alerts)</sub>
- Example: Pick End of Trading Day or One Week and both expire at midnight, either that day or a week out from the day you created it.  
  <sub> · [16948328-topstepx-price-alerts](https://help.topstep.com/en/articles/16948328-topstepx-price-alerts)</sub>
- If you do not activate the Trading Combine® within 30 calendar days of the date on which it was made available to you, your access to it will be suspended.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Rewards earned under this program expire ninety (90) days after being earned, are tracked and communicated to Code Owners via email, and are otherwise subject to the general terms of this Section 29.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Within 7 days, decide if you want to go Back2Funded.  
  <sub>7 days · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- If you are at the 5 active or pending XFA limit, you cannot activate a new XFA If no action is taken within 7 days, the Back2Funded offer expires and will be automatically declined .  
  <sub>7 days · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- If no action is taken within 7 days, the Back2Funded offer expires and will be automatically declined.  
  <sub>7 days · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>

## inactividad (sim)

- Accounts must have no trading activity Contact us within 28 days of the charge.  
  <sub>28 days · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Inactive subscription — A cancelled or past-due subscription can trigger rejected orders or error messages.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- If your purchase was made within the last 28 days and your account has had no trading activity, contact Trader Support to review your account for a refund so you can purchase the correct size.  
  <sub>28 days · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- What happens if I go inactive?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters) +1</sub>
- XFAs with no trading activity for more than 30 days may be closed.  
  <sub>30 days · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Live Funded Accounts with no trading activity for more than 30 days may be closed.  
  <sub>30 days · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- What are the rules on inactivity?  
  <sub> · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>

## retiro_colchon (sim)

- Best Practices Use stop losses before approaching your Maximum Loss Limit Monitor unrealized P&L — not just closed trades Leave a buffer above your limit during volatile markets Avoid trading during high-impact news events ⚠️ Your Maximum Loss Limit is calculated on real-time unrealized P&L.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- It is not rounded, and there is no buffer.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- What happened to the buffer?  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- The old buffer was quiet padding on top of a 50% target.  
  <sub>50% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Bands frame the gate, giving you a visual buffer zone.  
  <sub> · [8524249-topstepx-indicators](https://help.topstep.com/en/articles/8524249-topstepx-indicators)</sub>

## retiro_frecuencia (sim)

- Consistency is calculated for each payout window.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Payout caps by account size Max Payout per request: 50% of your account balance up to the cap below.  
  <sub>50% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Live Funded Account 5 winning days of $150+ Net P&L per Payout cycle (not consecutive) Request up to 50% of your account balance with no dollar cap After you request a Payout, your winning day count restarts.  
  <sub>$150, 50% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- MLL levels by account size: Account Size Maximum Loss Limit $50K $2,000 $100K $3,000 $150K $4,500 Please note: the trading day your Payout is requested will not count toward your winning days for the next Payout cycle.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- You'll be limited to Express Funded Account ( XFA) Consistency — best day must stay under 40% of total profits per Payout period Standard XFA is unavailable until RTP is completed If you’re placed into the RTP with an active Trading Combine: Any Standard Trading Combine subscription started before RTP placement will remain as a Standard Trading Combine.  
  <sub>40% · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- Under the Responsible Trading Program, Traders may trade up to five Express Funded Accounts while following a consistency requirement during payout periods.  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- Request one payout per business day, provided other rules are followed.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Reactivated Standard XFAs may request a payout after five (5) winning days of $150 or more.  
  <sub>$150 · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Reactivated Consistency XFAs may request a payout after meeting the 40% consistency target.  
  <sub>40% · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>

## retiro_minimo (sim)

- The Basics Request Payouts in the Express Funded Account (XFA) and Live Funded Account (LFA) via your Topstep Dashboard Available during CME market hours: Sunday 5 PM CT – Friday 5 PM CT (excluding holidays) Minimum Payout: $125 90/10 profit split — you keep 90% 2 paths.  
  <sub>$125, 90% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Start trading Start trading Frequently asked questions What is the minimum payout request? $125 How often can I request a payout?  
  <sub>$125 · [instant-payouts](https://www.topstep.com/instant-payouts)</sub>

## retiro_maximo (sim)

- The goal is the Live Funded Account ® — real capital, no Payout caps, and unlimited earning potential. ​ How to Get Started Create your Topstep account at dashboard.topstep.com ​ Choose your account size: 50K , 100K , or 150K Enter your payment info to start your monthly subscription Check your email for your account credentials Single-profile policy: Topstep allows one profile per Trader.  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- From there, take Payouts, build your track record, and earn your call-up to the Live Funded Account ® — where Payouts are uncapped.  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Silver (SI); counts as 2 of any other micro Micro Bitcoin (MBT) Capped at mini-equivalent lot sizes, not standard micro scaling Micro Ether (MET) Capped at mini-equivalent lot sizes, not standard micro scaling Scaling Plan FAQs What if I accidentally exceed my limit but fix it right away?  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Payout caps by account size Max Payout per request: 50% of your account balance up to the cap below.  
  <sub>50% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Account Size XFA Standard XFA Consistency $50K $2,000 $3,000 $100K $3,000 $4,000 $150K $5,000 $6,000 👉 Payout caps apply to XFA accounts only.  
  <sub>$50K, $2,000, $3,000, $100K, $3,000, $4,000 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Live Funded Account Payouts are not capped.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Take your Payouts, stay consistent, and position yourself for Live — where there are no caps and no ceiling on what you can earn. ⏰ Limited Time Offering: Add a Daily Loss Limit (DLL) at checkout in the Trading Combine, and increase your Payout Cap once you pass and activate an Express Funded Account.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Available starting at 3:30 PM CT on Tuesday, June 2nd. ​ Traders who voluntarily add a Daily Loss Limit to their account unlock double per-request payout caps.  
  <sub>3:30 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Account Path Current Cap With DLL (new) $50K Standard $2,000 $4,000 $50K Consistency $3,000 $6,000 $100K Standard $3,000 $6,000 $100K Consistency $4,000 $8,000 $150K Standard $5,000 $10,000 $150K Consistency $6,000 $12,000 Limited Time Offering: Payout Cap Increase FAQs Is this available for all Traders?  
  <sub>$50K, $2,000, $4,000, $50K, $3,000, $6,000 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- All Traders who make a new Trading Combine purchase and add a Daily Loss Limit (DLL) at checkout will receive the increased Payout cap, during this limited time offering beginning at 3:30 PM CT on Tuesday, June 2nd. ​ ​ Why is this a limited-time offering, and how long will this last?  
  <sub>3:30 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- If I add a DLL at checkout during Express Funded Account activation or Reactivation, will I still get the increased Payout cap?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- If I already added a Daily Loss Limit before this release, will I see an increased Payout cap?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- No Activation Fee Trading Combine Back2Funded Reactivation $10 off → 50K $20 off → 100K $30 off → 150K $50 off Reactivation Fees ⏰ Limited Time Offering: Add a Daily Loss Limit at checkout in the Trading Combine, and increase your Payout Cap once you pass and activate an Express Funded Account.  
  <sub>$10, $20, $30, $50 · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- The Live Funded Account® (LFA) is the big leagues — Topstep's money behind you, no Payout caps, and unlimited growth potential.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Remember: what transfers is capped at the account size.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Account Margin Max micros Equity Minis Effect during window 3K Challenge $3,000 0 Blocked No Trading available 25K $20,000 1 Blocked Capped at 1 micro 50K $50,000 3 Blocked Capped at 3 micros 100K $100,000 6 Blocked Capped at 6 micros 150K $150,000 9 Blocked Capped at 9 micros 250K $250,000 15 Blocked Capped at 15 micros Have Questions?  
  <sub>$3,000, $20,000, 1 micro, $50,000, 3 micros, $100,000 · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Your starting balance is 20% of your cumulative XFA balance — but capped at your Account Size, with any excess forfeited (not banked into Reserve).  
  <sub>20% · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- If 20% of the capped amount doesn't reach $10,000, Topstep supplements from that same capped amount to meet the $10,000 minimum.  
  <sub>20%, $10,000,, $10,000 · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Payouts Payout rules are the same as a standard Express Funded Account: 5 or more winning days of $150 (non-consecutive), Payout up to 50% of the account and up to $5,000, and net positive after your first Payout. ​ Account Size Payout Cap $50K $2,000 $100K $3,000 $150K $5,000 Call Up Process Topstep's Risk team will reach out when you're ready to move to a Pro Account.  
  <sub>$150, 50%, $5,000,, $50K, $2,000, $100K · [14645398-what-is-a-pro-account](https://help.topstep.com/en/articles/14645398-what-is-a-pro-account)</sub>
- Resets Not Available Phase 2: Express Funded Account® (XFA) Parameter Value Path Choose Consistency or Standard Payout Cap $4,000 Max Loss Limit $1,000 (static, non-trailing 🔥) After first Payout, MLL sets to $0 Max Contracts: 2 mini / 20 micro (no scaling) Daily Loss Limit (DLL) Mandatory $500 Phase 3: Live Funded Account® (LFA) Parameter Value Tier Size $25,000 Starting Balance $5,000 minimum Daily Loss Limit Mandatory $500 Max Contracts 2 mini / 2 micro $250K Freedom Trading Combine Parameters It's our second Topstep Labs drop, a new evaluation account with $250,000 in buying power - our biggest yet.  
  <sub>$4,000, $1,000, $0, 2 mini, 20 micro, $500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Phase 2: Express Funded Account® (XFA) Parameter Value Path Standard Payout Cap $25,000 Max Loss Limit $10,000 After first Payout, MLL sets to $0 Max Contracts: 25 mini / 250 micro Scaling Plan Balance Lots Below $1,500 3 Lots $1,500 - $2,000 4 Lots $2,000 - $3,000 5 Lots $3,000 - $4,500 10 Lots $4,500 - $6,000 15 Lots $6,000 - $8,000 20 Lots Above $8,000 25 Lots Learn more about how the Scaling Plan works here .  
  <sub>$25,000, $10,000, $0, 25 mini, 250 micro, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- What is the Payout cap on the funded account? $25,000 per Payout - our biggest Payout cap yet!  
  <sub>$25,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Is there a Payout cap on this account?  
  <sub> · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- There is no Payout cap in this experiment, the Challenge is for a fixed $3,000 Payout, no 90/10 split, paid one time.  
  <sub>$3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Is there a Payout cap on the $1.5K Challenge account?  
  <sub>$1.5K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- There is no Payout cap in this experiment, the Challenge is for a fixed $1,500 Payout, no 90/10 split, paid one time.  
  <sub>$1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Is there a Payout cap on the $6K Challenge account?  
  <sub>$6K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- There is no Payout cap in this experiment, the Challenge is for a fixed $6,000 Payout, no 90/10 split, paid one time.  
  <sub>$6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Only accounts with at least one payout are included The average is rounded up to the next tier of $50K, $100K, or $150K Your Live Funded Account maximum starting balance, rules, and limits are based on this capped size 2.  
  <sub>$50K, $100K, $150K · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Traders keep 90% of their profits, and Topstep keeps 10%, up to the maximum payout allowed under the selected payout policy.  
  <sub>90%, 10% · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- If you choose to close your Express Funded Account and are eligible for a payout, you may receive up to 50% of your current Reward Balance, capped at $5,000.  
  <sub>50%, $5,000 · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Double Payout Caps Terms & Conditions Skip to Main Content Funded Trading Prop Firm How It Works Topstep Octagon Instant Payouts Brokerage TopstepX Blog Support Trader Support Help Center Status Page Discord Login Sign Up Sign Up Double Payout Caps Terms & Conditions For a limited time, traders who add a Daily Loss Limit (DLL) to their Topstep account will unlock double the standard payout caps across every account size in which a DLL is active.  
  <sub> · [double-payout-caps-terms-conditions](https://www.topstep.com/double-payout-caps-terms-conditions)</sub>

## retiro_split (sim)

- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- The Basics Request Payouts in the Express Funded Account (XFA) and Live Funded Account (LFA) via your Topstep Dashboard Available during CME market hours: Sunday 5 PM CT – Friday 5 PM CT (excluding holidays) Minimum Payout: $125 90/10 profit split — you keep 90% 2 paths.  
  <sub>$125, 90% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Standard Path Consistency Path 5 winning days of $150+ 3 days with 40% consistency target Request 50% of the account balance up to $5000* Request 50% of the account balance up to $6,000* 90/10 split 90/10 split ⚠️ Note for traders who joined the new Topstep dashboard before January 12, 2026: You receive 100% of your first $10,000 in lifetime profits.  
  <sub>$150, 3 days, 40%, 50%, $5000, 50% · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- After that, the 90/10 split applies.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $3,000. $3K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $3,000 $3,000 Max Loss Limit $1,000 (static, non-trailing 🔥) $1,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $3,000, paid one time.  
  <sub>$3,000, $3K, $0, $0, $3,000, $3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $1,500. $1.5K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $1,500 $1,500 Max Loss Limit $500 (static, non-trailing 🔥) $500 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 2 micro (no minis)* 2 micro (no minis)* Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $1,500, paid one time.  
  <sub>$1,500, $1.5K, $0, $0, $1,500, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $6,000. $6K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $6,000 $6,000 Max Loss Limit $2,000 (static, non-trailing 🔥) $2,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $6,000, paid one time.  
  <sub>$6,000, $6K, $0, $0, $6,000, $6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- There is no Payout cap in this experiment, the Challenge is for a fixed $3,000 Payout, no 90/10 split, paid one time.  
  <sub>$3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- There is no Payout cap in this experiment, the Challenge is for a fixed $1,500 Payout, no 90/10 split, paid one time.  
  <sub>$1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- There is no Payout cap in this experiment, the Challenge is for a fixed $6,000 Payout, no 90/10 split, paid one time.  
  <sub>$6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- How do profit splits work?  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Traders keep 90% of their profits, and Topstep keeps 10%, up to the maximum payout allowed under the selected payout policy.  
  <sub>90%, 10% · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Instant Payouts for Funded Traders | 99% Approval | Topstep Skip to Main Content Funded Trading Prop Firm How It Works Topstep Octagon Instant Payouts Brokerage TopstepX Blog Support Trader Support Help Center Status Page Discord Login Sign Up Sign Up ​ ​ The best payout in the industry Get started today Get started today See how it works See how it works $1.4B+ Paid out to traders 1 9 seconds Average instant payout time* 99.26% Payout approval rate 90% Profit split Aeropay x Topstep We’ve partnered with Aeropay to make payouts instant**.  
  <sub>99%, $1.4, 9 seconds, 99.26%, 90% · [instant-payouts](https://www.topstep.com/instant-payouts)</sub>
- Pass the Trading Combine, get funded, hit the payout path you select, and keep 90% of the profits you take.  
  <sub>90% · [instant-payouts](https://www.topstep.com/instant-payouts)</sub>

## retiro_cantidad (sim)

- Day 2: +$1,500, balance $2,000, MLL locks at $0. 👉 After your first Payout: Your MLL is set to $0 regardless of where it was before.  
  <sub>$1,500,, $2,000,, $0, $0 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- As you earn more net profit, the percentage will naturally come down. 👉 Your dashboard updates in real time and shows your Consistency %, total net profit, largest single-day profit, and Payout eligibility status. ​ Does Consistency reset after a Payout?  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- After a Payout is requested, your consistency calculation resets to $0 and applies only to profits earned in the new window.  
  <sub>$0 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- The new window starts on the trading day after your Payout was requested.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Consistency is reset after each Payout. ​ How is consistency calculated? 👉 Consistency = Largest Winning Day ÷ Total Net Profit Consistency tracking only appears on your dashboard once you have positive net profit.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Your consistency calculation resets after each Payout and applies only to profits earned afterward.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- You now need 3 new qualifying days on profits earned after that Payout.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Your first Payout is exempt.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- After each Payout: Your Maximum Loss Limit (MLL) resets to $0 permanently, and your 5-day count restarts.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Payout 1 $6,000 (starting from $0) ✅ No profit requirement on first Payout Take $3,000 Payout New balance: $3,000 — Payout 2 $4,000 (up from $3,000) ✅ Profitable since last Payout Take $1,800 Payout New balance: $2,200 — Payout 3 $4,500 (up from $2,200) ✅ Profitable since last Payout Take $2,000 Payout New balance: $2,500 — Payout 4 $1,800 (down from $2,500) ❌ Not profitable — keep trading Express Funded Account Consistency To request a Payout, you must meet both requirements: 3 trading days with at least 1 trade per day.  
  <sub>$6,000, $0, $3,000, $3,000, $4,000, $3,000 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- After each Payout: Your Maximum Loss Limit resets to $0 permanently, your consistency calculation resets, and your 3-day count restarts.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Your MLL is set to $0 after your first Payout.  
  <sub>$0 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- All Collections Topstep Program Funded Accounts Express Funded Account® Back2Funded: Rules, Guidelines, and How It Works Back2Funded: Rules, Guidelines, and How It Works Lost it before your first Payout?  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- August 14, 2026 Table of contents The Basics Back2Funded gives you up to 2 Reactivations per account if you lose your Express Funded Account® (XFA) before your first Payout.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- Is returning to Live guaranteed after a certain number of payouts?  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- No Activation Fee Path — $0. 👉 Reactivation Lost your XFA before your first Payout?  
  <sub>$0 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Payouts Payout rules are the same as a standard Express Funded Account: 5 or more winning days of $150 (non-consecutive), Payout up to 50% of the account and up to $5,000, and net positive after your first Payout. ​ Account Size Payout Cap $50K $2,000 $100K $3,000 $150K $5,000 Call Up Process Topstep's Risk team will reach out when you're ready to move to a Pro Account.  
  <sub>$150, 50%, $5,000,, $50K, $2,000, $100K · [14645398-what-is-a-pro-account](https://help.topstep.com/en/articles/14645398-what-is-a-pro-account)</sub>
- Resets Not Available Phase 2: Express Funded Account® (XFA) Parameter Value Path Choose Consistency or Standard Payout Cap $4,000 Max Loss Limit $1,000 (static, non-trailing 🔥) After first Payout, MLL sets to $0 Max Contracts: 2 mini / 20 micro (no scaling) Daily Loss Limit (DLL) Mandatory $500 Phase 3: Live Funded Account® (LFA) Parameter Value Tier Size $25,000 Starting Balance $5,000 minimum Daily Loss Limit Mandatory $500 Max Contracts 2 mini / 2 micro $250K Freedom Trading Combine Parameters It's our second Topstep Labs drop, a new evaluation account with $250,000 in buying power - our biggest yet.  
  <sub>$4,000, $1,000, $0, 2 mini, 20 micro, $500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Phase 2: Express Funded Account® (XFA) Parameter Value Path Standard Payout Cap $25,000 Max Loss Limit $10,000 After first Payout, MLL sets to $0 Max Contracts: 25 mini / 250 micro Scaling Plan Balance Lots Below $1,500 3 Lots $1,500 - $2,000 4 Lots $2,000 - $3,000 5 Lots $3,000 - $4,500 10 Lots $4,500 - $6,000 15 Lots $6,000 - $8,000 20 Lots Above $8,000 25 Lots Learn more about how the Scaling Plan works here .  
  <sub>$25,000, $10,000, $0, 25 mini, 250 micro, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- After the Payout — Account closes out.  
  <sub> · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- How to use Back2Funded Lose your XFA before your first payout.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Back2Funded gives you the opportunity to pay for up to 2 reactivations if you lose your Express Funded Account (XFA) before your first payout.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>

## cuenta_live (sim)

- The Express Funded Account is where you take Payouts and build the track record to get to the Live Funded Account.  
  <sub> · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: Reach and maintain the Profit Target Consistency Target: best trading day must stay below 55% of total profits Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit (MLL) Express Funded Account™ — Standard Earn this by passing the Trading Combine®.  
  <sub>55% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: 5 Winning Days of $150 or more (non-consecutive) to request a Payout Net profit greater than $0 since your last Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Express Funded Account™ — Consistency An alternative XFA path with a different Payout structure.  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: Trade at least 3 days at 40% consistency to request a Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Live Funded Account® Topstep’s prop firm capital.  
  <sub>3 days, 40% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Called up by the Risk Team after consistent XFA performance.  
  <sub> · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: 5 Winning Days of $150 or more Do not hit or exceed the Daily Loss Limit (DLL) — breaching it deactivates your account for that trading day Rule: Do not let your Account Balance reach or go below $0 Key Links Trading Combine® Parameters Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Consistency at Topstep Express Funded Account™ Parameters Topstep Payout Policy What is the Responsible Trading Program?  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Staying Outside the 2% Price Limit Zone What are the costs in the Live Funded Account?  
  <sub>2% · [8284108-how-to-identify-the-futures-front-month-contract](https://help.topstep.com/en/articles/8284108-how-to-identify-the-futures-front-month-contract)</sub>
- Some countries can access Express Funded Accounts® (XFA) but not Live Funded Accounts® (LFA).  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- Requirements No US citizenship required Minimum age: 18 Citizens or residents of OFAC-sanctioned or partner-restricted countries are not eligible to trade, earn funding, or receive payouts Countries Eligible for an XFA — Not LFA These Traders can join Topstep, trade and pass the Trading Combine, earn Express Funded Accounts, and take up to $200,000 in total payouts.  
  <sub>$200,000 · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- No Live Funded Account access: A–E F–K L–O P–Z Albania Germany Laos Papua New Guinea Bolivia Ghana Liberia Serbia Bosnia and Herzegovina Hong Kong Macedonia Trinidad and Tobago British Virgin Islands Iceland Monaco Vietnam Cameroon Kuwait Mongolia Zimbabwe Central African Republic Montenegro Ethiopia Namibia Nepal 👉 Select Traders from these countries may be considered for the Pro Account track rather than the Live Funded Account, based on performance.  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- Why are some countries XFA-only and not eligible for Live?  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- Brokerage restrictions prevent Live Funded Account access in certain countries.  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- Those Traders can still earn payouts and build skills in the XFA and Pro Account.  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- Related Articles Topstep Payout Policy Live Funded Account Parameters Back2Funded: Rules, Guidelines, and How It Works What is a Pro Account?  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- When contacting Trader Support for a refund, provide your Trading Combine or Express Funded Account Number, the last four digits of the charged card, the charge date, and any relevant screenshots or recordings. ⚠️ Filing a chargeback or dispute is strictly prohibited .  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- June 18, 2026 Table of contents The Basics Topstep covers Level 1 market data (Top of Book) for all 4 exchanges on Trading Combine® and Express Funded Account® (XFA) accounts at no cost.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Do I need to pay for data in an Express Funded Account®?  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Level 1 is free for all simulated accounts including the XFA.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Related Articles Quantower Connection Instructions Express Funded Account™ Parameters What are the costs in the Live Funded Account?  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Active until you pass and earn an Express Funded Account® (XFA) — or until you cancel.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- You'll be able to activate your Express Funded Account immediately.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Topstep Pricing and Payment Questions Can I Reset an Express Funded Account (XFA) or Live Funded Account (LFA)?  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- For Express Funded Accounts, use Back2Funded.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Back2Funded reactivates a lost Express Funded Account for a fee.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- If your subscription is canceled or you only have an Express Funded Account, the Practice Account add-on will not work.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- Express Funded Account™ Parameters Getting Started with the Topstep Dashboard Live Funded Account Parameters Did this answer your question?  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- Quantower via TopstepX is available for the Trading Combine® and Express Funded Account® (XFA) only.  
  <sub> · [8284179-quantower-connection-instructions](https://help.topstep.com/en/articles/8284179-quantower-connection-instructions)</sub>
- Meet them, and you've earned your Express Funded Account® .  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Fewer contracts is always allowed. ⚠️ Please note: The Micro to Mini ratio functionality is available for the Trading Combine and Express Funded Account.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- It is not currently available for the Live Funded Account.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters) +1</sub>
- Topstep isn't responsible for trades made on the wrong account. ⚠️ Single Profile Policy: All Trading Combines, Express Funded Accounts, and Live Funded Accounts must be under 1 Topstep profile.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- You'll receive a confirmation email and can activate your Express Funded Account® directly from your Dashboard.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- You can pay the Activation Fee immediately, but your XFA won't be available to trade until markets reopen at 5 PM CT Sunday.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Money made in the Trading Combine does not carry over to your Express Funded Account.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Express Funded Account™ Parameters Topstep Payout Policy Daily Loss Limit in the Trading Combine and Express Funded Account Did this answer your question?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Start in the Trading Combine®, prove your risk management, earn an Express Funded Account® (XFA), take Payouts, and work toward a Live Funded Account® (LFA).  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- Pass, and you earn an Express Funded Account ® where you take Payouts and build your track record.  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- The goal is the Live Funded Account ® — real capital, no Payout caps, and unlimited earning potential. ​ How to Get Started Create your Topstep account at dashboard.topstep.com ​ Choose your account size: 50K , 100K , or 150K Enter your payment info to start your monthly subscription Check your email for your account credentials Single-profile policy: Topstep allows one profile per Trader.  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- Pass the Trading Combine ® and earn an Express Funded Account ®.  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- From there, take Payouts, build your track record, and earn your call-up to the Live Funded Account ® — where Payouts are uncapped.  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- Learn more here: Topstep Community and Topstep Learning Key Links Topstep Program Overview Trading Combine® Parameters Trading Combine Subscription Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Am I Eligible to Trade with Topstep?  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- Express Funded Account™ Parameters Topstep Payout Policy Topstep Labs The Topstep Octagon Did this answer your question?  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- In the Express Funded Account Your Express Funded Account (XFA) balance starts at $0.  
  <sub>$0 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- For a 50K XFA, your MLL starts at -$2,000 and trails upward.  
  <sub>$2,000 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Example: You start a 50K XFA at $0.  
  <sub>$0 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- In the Live Funded Account For the Live Funded Account, refer here .  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Express Funded Account: Your account is permanently closed.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Live Funded Account® (LFA): Learn more .  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Your MLL resets to the starting value for your account size: Account Size Starting MLL $50K XFA -$2,000 $100K XFA -$3,000 $150K XFA -$4,500 The MLL trails upward as your balance grows and locks at $0 once reached, same as a brand new XFA.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Express Funded Account™ Parameters Topstep Payout Policy Daily Loss Limit in the Trading Combine and Express Funded Account What is a Pro Account?  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Trading Combine® Parameters TopstepX™ — Commissions and Fees What are the costs in the Live Funded Account?  
  <sub> · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- Here's how the Consistency rules work in the Trading Combine® and the Express Funded Account®.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Express Funded Account Consistency — Consistency Objective (40%) The Consistency path in the Express Funded Account® (XFA) rewards Traders who build profit steadily, not in one big day.  
  <sub>40% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- When you activate your XFA, you choose Standard or Consistency as your Payout path.  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Related Articles Topstep Program Overview Express Funded Account™ Parameters Topstep Payout Policy Topstep Labs The Topstep Octagon Did this answer your question?  
  <sub> · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Updated this week Table of contents TopstepX™ — Commissions & Fees These fees apply when trading the Trading Combine, Express Funded Account, and Live Funded Account.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- Express Funded Account™ Parameters | Topstep Help Center Copyright 2023.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- All Collections Topstep Program Funded Accounts Express Funded Account® Express Funded Account™ Parameters Express Funded Account™ Parameters Pass the Trading Combine.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- The Express Funded Account® (XFA) is the simulated funded-level account you earn after passing your Trading Combine .  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- At activation, you choose your Payout path: Standard or Consistency. 🤜 The XFA is the proving ground.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- … 307 más en inventario.json

## cierre_cuenta (sim)

- If you add a new card due to a failed renewal, please remember to update the affected subscription with your new card under the Subscriptions section of your Billing tab. ​ During this retry period, account Resets are temporarily disabled for that subscription.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- To avoid unexpected charges or losing the ability to Reset before your next billing cycle, we recommend completing any account Resets the day before your billing date.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- In this case, please contact our Support Team and we'll close the account for you.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- All Practice Account Resets are free, but the limit applies. ​ How long do I have access to the Practice Account?  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- Possible responses to a Prohibited Conduct violation: Warning Deletion of the impacted trading day Account Reset Permanent account closure Delay or denial of a Payout request Ultimately, the action Topstep takes will depend on the infractions severity and your prior history (or lack thereof).  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Breaching those terms will result in immediate account termination.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Cumulative balance was $100K, so $50K is forfeited. → $10K to trade, $40K in Reserve. 👉 Heads up: all Express Funded Accounts are averaged together, so new Topstep Labs accounts may affect your account size.  
  <sub>$100K, $50K, $10K, $40K · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Unlocked reserve is forfeited.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Please note that Payouts can only be taken from your unlocked balance, not from your Live Funded Account Reserve.​ Please note: withdrawing the full balance will close your account.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Warning: Reckless or undisciplined trading in a Live Funded Account may result in forfeiture of live capital.  
  <sub> · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Your starting balance is 20% of your cumulative XFA balance — but capped at your Account Size, with any excess forfeited (not banked into Reserve).  
  <sub>20% · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- If the balance reaches zero, any remaining Live reserve is forfeited.  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- If the Shoulder Tap XFA is traded to $0, the remaining seed capital will be forfeited.  
  <sub>$0, · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Removing all cards will close your account.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- There will not be a remaining account balance, and the account will be closed upon completion.  
  <sub> · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- The Funded Level includes both Express Funded Accounts and Live Funded Accounts, with the aggregate of such accounts used in the percentage determination.  
  <sub> · [topstepx](https://www.topstep.com/topstepx) +5</sub>
- Once accepted, these Terms remain effective until terminated as provided for herein.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We may, in our sole discretion, elect to suspend or terminate access to, or use of, the Topstep Products and Content by anyone who violates these Terms, including but not limited to failure to pay any required Fee.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- You are not entitled to a refund of the fee, for example, if you cancel your Account or request the cancellation by e-mail, if you terminate the use of the Services prematurely (for example, by failing to complete the Trading Combine®), if you fail to meet the conditions of the Trading Combine®, if we suspend your Account or access to Services, or if you otherwise violate the Terms in any manner.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If you do not pay or cause Topstep not to be paid any Fee or portion of a Fee that is due (including by disputing, reversing, or terminating your payment for a Fee), then Topstep may, at its sole discretion, suspend or terminate your access to any Services with or without notice.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- You agree to indemnify and hold Topstep harmless from any claims arising from Topstep’s suspension or termination of your access to any Services for nonpayment.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If we identify that the unusual behavior relates to the User’s involvement in Prohibited Conduct (see Section 27), we reserve the right to determine, at our sole discretion, the nature of the behavior described and reasonable consequences, including, without limitation, the immediate termination of your access to the Sites and Services.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If you become employed by or otherwise engaged by Topstep, or were employed or otherwise engaged by Topstep, you agree to immediately notify Topstep and terminate your Account.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- You may terminate your Account at any time by contacting Support .  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep will confirm the receipt of the request to the User by e-mail, and the contractual relationship between the User and Topstep will be terminated as of the date of the confirmation email.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If you engage in any of Prohibited Conduct, Topstep may (a) consider it as a failure to meet the conditions of the particular Trading Combine®, (b) remove the transactions that violate the prohibition from your trading history and/or not count their results in the profits and/or losses achieved by such Simulated Trading, or (c) immediately cancel all Services provided to you and subsequently terminate your Account.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- You can request the renewal of access via the User Section or by contacting Support within 6 months of the initial suspension, otherwise we will terminate the provision of the Services without any right to a refund of the fee.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If Topstep determines in its sole and absolute discretion you have opened multiple Accounts, Topstep reserves the right to suspend or terminate your Account and subsequently created Accounts.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Termination Users may terminate receipt of any free service publications at any time by sending Topstep a request for removal from the relevant distribution list.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If you wish to terminate receipt of such publications, please use the link on the attached email or see the contact information provided in Section 2.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right to refuse to permit or to terminate your access to any of the Topstep Sites or Services at any time at its sole discretion.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Such termination may result from a violation of the Terms or other referenced agreements, unauthorized use or reproduction of any publication or information, nonpayment of any Fee or portion of a Fee, or any or no reason, all determined in Topstep’s sole discretion.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If such access is refused or terminated, you agree you will not attempt to establish a new Account under any name, real or assumed.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- All provisions of these Terms shall survive termination, including, ownership provisions, warranty disclaimers, indemnities, and limitations of liability.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Any dispute, claim, or controversy arising out of or relating to these Terms or the breach, termination, enforcement, interpretation, or validity thereof, including the determination of the scope or applicability of these Terms to arbitrate, shall be determined by arbitration in Wilmington, Delaware before one arbitrator.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If you are found to have profited from taking advantage of the simulated environment to gain an edge in your Trading Combine® at any time you have graduated past the Trading Combine®, or otherwise deemed to have engaged in other Prohibited Conduct (defined below) you will not be entitled to receive any withdrawals from any other account maintained with Topstep, all of which will be forfeited and closed immediately.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If Topstep, in its sole discretion, determines a User has violated any Trading Rules, failed to supply accurate and complete information requested by Topstep, or engaged in Prohibited Conduct, Topstep may, in its sole determination, remove any Simulated Account profits, delete a trading day, reset an Account, or ban a User from any further use of the Site and Services.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If Topstep identifies trading activity that, in its sole discretion, relates to Prohibited Conduct, Topstep reserves the right to, in its sole discretion, delete the trading day and all profits, or restart or close the Account.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Other prohibited uses You are solely responsible for any and all acts and omissions that occur under your Account, and you agree not to engage in unacceptable use of the Sites or Services or any User Content including: Posting, storing, or disseminating any unsolicited or unauthorized advertising, promotional materials, junk mail, spam, chain letters or other fraudulent schemes, or any other form of solicitation; Using any manual or automated software, devices, or other processes to “crawl” or “spider” any web pages contained in the Sites or Services; Using any VPN or VPS on Accounts is strictly prohibited and may result in account termination and forfeiture of profits.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We may terminate these Terms at any time without notice, and accordingly may deny you access to our Sites and Services, if in our sole judgment you fail to comply with any term or provision of these Terms.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- The obligations and liabilities of the parties incurred prior to the termination date shall survive the termination of these Terms for all purposes.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If the Daily Loss Limit is reached: Positions are flattened Orders are canceled Trading is paused until the next trading session This pause is not a rule violation . *If the account is auto liquidated with a balance less than $1,000 the account will be closed and the remaining account balance will be paid out to the trader.  
  <sub>$1,000 · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Any remaining balance will be forfeited.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Topstep reserves the right to modify or terminate this offer at any time, with or without prior notice, at its sole discretion.  
  <sub> · [double-payout-caps-terms-conditions](https://www.topstep.com/double-payout-caps-terms-conditions)</sub>

## contratos_maximos (sim)

- Contract Sizing at Topstep Account Max Contracts 50K 5 100K 10 150K 15 See the full permitted products list for all available contracts.  
  <sub> · [8284113-can-i-trade-forex-with-you](https://help.topstep.com/en/articles/8284113-can-i-trade-forex-with-you)</sub>
- Practice Account Details Detail Value Account size 150K, regardless of Trading Combine size Maximum Position Size 15 lots Max accounts at once 1 Cost Free with active Trading Combine Resets Always free Label in platform "PRACTICE" in account drop-down How to Activate Log in to the Topstep Dashboard Click Accounts on the left side Click Add-ons on the top left Click Activate on the Practice Account option 👉 To close your Practice Account, follow the same steps and click Unsubscribe instead. 👉 To Reset your Practice Account: click Unsubscribe, then click Activate to create a new one.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- Exceeded Maximum Position Size — Micros and minis count as the same size lots in the program.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- This links your account to ProjectX data — a direct CME feed for faster, cleaner market data with 10:1 Micro to Mini contract conversions.  
  <sub>10:1 · [8284179-quantower-connection-instructions](https://help.topstep.com/en/articles/8284179-quantower-connection-instructions)</sub>
- Maximum Position Size The maximum number of contracts you can hold open at one time, per account.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Account Size Max Contracts Max Micros $50K 5 50 $100K 10 100 $150K 15 150 Hint: You're never required to trade the maximum.  
  <sub>$50K, $100K, $150K · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Express Funded Account Standard Rule Do not hit your Maximum Loss Limit Objectives Follow the Scaling Plan — the max contracts you can hold at one time — based on your current account balance.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Express Funded Account Consistency Rule Do not hit your Maximum Loss Limit Objectives Follow the Scaling Plan — the max contracts you can hold at one time — based on your current account balance.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- It sets your Maximum Position Size — the max contracts you can hold at one time — based on your current account balance. ☝️ The Scaling Plan does not apply to the Live Funded Account®.  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- How It Works Your XFA starts at a $0 balance As your balance grows, so does your buying power — shown below You're never required to trade your maximum contracts → Key rule: Your max contracts do not increase mid-session.  
  <sub>$0 · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Over-leveraging causes the most damage to long-term success Please note: During extreme volatility, we may temporarily tighten position limits on affected products.  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Micros and Minis 10:1 ratio: 1 Mini = 10 Micro contracts Limits are based on mini-contract equivalents Example — $50K XFA, 2-lot Scaling Plan: 2 Minis, OR 20 Micros, OR Any combo equal to 2 Minis ⚠️ Please note: The Micro to Mini ratio functionality is available for the Trading Combine and Express Funded Account.  
  <sub>10:1, 1 Mini, 10 Micro, $50K, 2 Minis, 20 Micros · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Set up your workspace to show open positions and orders Enable Order Confirmation — requires you to reconfirm before an order submits From your Risk Settings page, use Contract Limits to set a per-product max Where do I see my current contract limits?  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- If a Payout reduces your balance to a lower tier, your maximum contract size decreases accordingly.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Trading Maximum Position Size into Major News Events Purposefully trading your full Maximum Position Size directly into a scheduled major news event.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- There's always another day. ⚖️ Keeping position size in check Maximum position size is a tool, not a default setting.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Daily Loss Limit and Maximum Position Size Maximum Position Size: The maximum number of contracts you can hold open at one time, per account.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Your Maximum Position Size is affected by your performance in the Live Funded Account.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Learn more here: Dynamic Live Risk Expansion Live Funded Accounts start with a Daily Loss Limit (DLL) based on account size: LFA Size Standard DLL $50K $2,000 $100K $3,000 $150K $4,500 Regardless of account size, if your tradable balance drops to lower thresholds, the DLL and Maximum Position Size automatically adjust: Tradable Balance DLL Max Position Size $10,000 or below $2,000 5 $5,000 or below $1,000 3 ☝️ These limits update on Fridays and return to standard levels once your balance rises back above the thresholds.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Updated this week Table of contents Topstep's Dynamic Live Risk Expansion adjusts your Daily Loss Limit (DLL) and Maximum Position Size (contract limits) as your Live Funded Account® (LFA) profits grow.  
  <sub> · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Starting Daily Loss Limit and Maximum Position Size Account Size Starting Daily Loss Limit Maximum Position Size 50K $2,000 5 100K $3,000 10 150K $4,500 15 How Tiers Work Your net profit determines your Tier.  
  <sub>$2,000, $3,000, $4,500 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Expansion Table Maximum Position Size Profit Daily Loss Limit Up to 100 lots 1M Up to $100,000 Up to 70 lots 550K Up to $50,000 Up to 50 lots 200K Up to $20,000 Up to 30 lots 100K Up to $10,000 — 50K Up to $6,000 — 20K Up to $5,500 — 15K Up to $5,000 Position Limits remain at the max for each account size (5 lots for $50Ks, 10 lots for $100Ks, 15 lots for $150Ks) until the account reaches Tier 4 with with $100K in profit.  
  <sub>$100,000, $50,000, $20,000, $10,000, $6,000, $5,500 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- For the first three tiers, +$500 is added to your starting Daily Loss Limit for each tier you achieve: $50K Account (Starts at $2,000 DLL): $15k Profit -> $2,500 DLL $20k Profit -> $3,000 DLL $50k Profit -> $3,500 DLL $100K Account (Starts at $3,000 DLL): $15k Profit -> $3,500 DLL $20k Profit -> $4,000 DLL $50k Profit -> $4,500 DLL $150K Account (Starts at $4,500 DLL): $15k Profit -> $5,000 DLL $20k Profit -> $5,500 DLL $50k Profit -> $6,000 DLL Once an account reaches $100k in net profit, Daily Loss Limits and Maximum Position Sizes align across all account types (as shown in Tier 4+).  
  <sub>$500, $50K, $2,000, $15k, $2,500, $20k · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Required Equity Thresholds for Expansion The Risk Team may adjust your Daily Loss Limit and Maximum Position Size based on net equity — even if you haven't moved through the expansion tiers.  
  <sub> · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Adjustments may be considered when a Live Funded Account reaches: $10,000 net equity in a 50K account $15,000 net equity in a 100K account $20,000 net equity in a 150K account Daily Loss Limit Safeguard Regardless of account size, if your tradable balance drops to lower thresholds, the DLL and Maximum Position Size automatically adjust: ☝️ These limits update on Fridays and return to standard levels once your balance rises back above the thresholds.  
  <sub>$10,000, $15,000, $20,000 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Account Daily Loss Limit (DLL) $50K $2,000 $100K $3,000 $150K $4,500 Regardless of account size: Tradable balance at or below $10,000 → DLL drops to $2,000, Max Position Size = 5 Tradable balance at or below $5,000 → DLL drops to $1,000, Max Position Size = 3 Example: If you have a 100K Live Funded Account and your end-of-day balance goes below $10,000, your Daily Loss Limit will be changed from $3,000 to $2,000 before the start of the next trading session.  
  <sub>$50K, $2,000, $100K, $3,000, $150K, $4,500 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- When they do, Topstep may reduce position limits.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Updated this week Table of contents Position Limit Adjustments Markets get wild sometimes.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- During extreme volatility, we may temporarily tighten position limits on affected products.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- How Position Limits Are Adjusted When a product is deemed high-risk due to volatility, we may implement one or both of the following adjustments: Micro Contract Limits Mini Contract Restrictions Trading on mini-sized contracts or larger may be temporarily halted for affected products Current Restrictions 👉 Restrictions below are organized by account size.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- For example, "GC = 3/6/9" means 3 minis for $50K accounts, 6 minis for $100K accounts, and 9 minis for $150K accounts.  
  <sub>3 minis, $50K, 6 minis, $100K, 9 minis, $150K · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- In the $250K Trading Combine , restricted energies are set to a max contract size of 15 minis/150 micros.  
  <sub>$250K, 15 minis, 150 micros · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- For SIL/MHG, 10 minis/100 micros.  
  <sub>10 minis, 100 micros · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Additionally, MGC and MCL is limited to 6 micros.  
  <sub>6 micros · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility) +1</sub>
- Additionally, MGC and MCL is limited to 6 micros. ⚠️ Please note: For Express Funded Accounts, position limits for restricted products have a ceiling of the contracts listed above (CL = 3/6/9, for example). ​ However, a trader's actual limit may be lower depending on their current account balance, as the Scaling Plan applies independently.  
  <sub>6 micros · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Position limit adjustments are: Temporary : Restrictions remain in place only while volatility levels are elevated Product-specific : Only products experiencing extreme volatility are affected Actively monitored : Our Risk Team continuously evaluates market conditions to determine when normal limits can be reinstated What You Can Still Do Continue trading with adjusted position sizes in affected products Trade other products with standard position limits Focus on risk management and strategic opportunities Use this time to refine your trading plan and review your strategy Understanding Market Volatility Historic volatility means historic losses can happen faster than normal.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- How You'll Be Notified When position limits are adjusted, you'll receive notification through: Email communication Dashboard banners Social media updates (@AskTopstep on X) We'll also notify you when restrictions are lifted and normal position limits are reinstated.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Account Margin Max micros Equity Minis Effect during window 3K Challenge $3,000 0 Blocked No Trading available 25K $20,000 1 Blocked Capped at 1 micro 50K $50,000 3 Blocked Capped at 3 micros 100K $100,000 6 Blocked Capped at 6 micros 150K $150,000 9 Blocked Capped at 9 micros 250K $250,000 15 Blocked Capped at 15 micros Have Questions?  
  <sub>$3,000, $20,000, 1 micro, $50,000, 3 micros, $100,000 · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- If you have questions about current position limits or how these adjustments affect your trading, please contact support .  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Lead account — where you place your trades Follower account(s) — where those trades are copied to ✋ Before you connect accounts, please know: The Lead account must have the lowest Maximum Position Size (MPS) of all accounts in the group.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Trade Limits, Symbol Blocks, and Contract Limits are not available on Follower accounts.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Contract Limits Contract Limits Cap the number of contracts you can trade per symbol.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Orders exceeding the limit are automatically rejected Applies to order entry only — won't close open positions Take Profit and Stop Loss bracket orders are ignored Enforced separately for long and short Setup: Settings → Risk Settings → Contract Limits → enter limits → Save. ​ ​ This is also where you can see current contract limits according to your account type/size. ​ Trade Limits Trade Limits Cap total trades per day and/or week.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Phase 1: Trading Combine® Parameter Value Buying Power $25,000 Profit Target $2,000 Max Loss Limit $1,000 (static, non-trailing 🔥) Max Contracts 2 mini / 20 micro Consistency Target 55% Daily Loss Limit (DLL) Mandatory $500 Funded Activation Fee Free Price $75 one-time — no subscription.  
  <sub>$25,000, $2,000, $1,000, 2 mini, 20 micro, 55% · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Resets Not Available Phase 2: Express Funded Account® (XFA) Parameter Value Path Choose Consistency or Standard Payout Cap $4,000 Max Loss Limit $1,000 (static, non-trailing 🔥) After first Payout, MLL sets to $0 Max Contracts: 2 mini / 20 micro (no scaling) Daily Loss Limit (DLL) Mandatory $500 Phase 3: Live Funded Account® (LFA) Parameter Value Tier Size $25,000 Starting Balance $5,000 minimum Daily Loss Limit Mandatory $500 Max Contracts 2 mini / 2 micro $250K Freedom Trading Combine Parameters It's our second Topstep Labs drop, a new evaluation account with $250,000 in buying power - our biggest yet.  
  <sub>$4,000, $1,000, $0, 2 mini, 20 micro, $500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Phase 1: Trading Combine® Parameter Value Buying Power $250,000 Profit Target $15,000 Max Loss Limit $10,000 Trailing End of Day Max Contracts 25 mini / 250 micro Consistency Target 55% Daily Loss Limit (DLL) Mandatory $5,000 Price $499 one-time — no subscription.  
  <sub>$250,000, $15,000, $10,000, 25 mini, 250 micro, 55% · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Phase 2: Express Funded Account® (XFA) Parameter Value Path Standard Payout Cap $25,000 Max Loss Limit $10,000 After first Payout, MLL sets to $0 Max Contracts: 25 mini / 250 micro Scaling Plan Balance Lots Below $1,500 3 Lots $1,500 - $2,000 4 Lots $2,000 - $3,000 5 Lots $3,000 - $4,500 10 Lots $4,500 - $6,000 15 Lots $6,000 - $8,000 20 Lots Above $8,000 25 Lots Learn more about how the Scaling Plan works here .  
  <sub>$25,000, $10,000, $0, 25 mini, 250 micro, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Phase 3: Live Funded Account® (LFA) Parameter Value Tier Size $150,000 Starting Balance $10,000 minimum Daily Loss Limit Mandatory $5,000 Max Contracts 15 mini Please note: once moved to a Live Funded Account, the Live Funded Account will follow our standard Live Funded Account Parameters and be treated as a $150K. $3K Challenge Parameters Our third Labs drop!  
  <sub>$150,000, $10,000, $5,000, 15 mini, $150K, $3K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $3,000. $3K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $3,000 $3,000 Max Loss Limit $1,000 (static, non-trailing 🔥) $1,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $3,000, paid one time.  
  <sub>$3,000, $3K, $0, $0, $3,000, $3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $1,500. $1.5K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $1,500 $1,500 Max Loss Limit $500 (static, non-trailing 🔥) $500 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 2 micro (no minis)* 2 micro (no minis)* Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $1,500, paid one time.  
  <sub>$1,500, $1.5K, $0, $0, $1,500, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- There is no limit on how many Challenges you can have in the Challenge Round. ​ *See more information regarding contract limits here . $6K Challenge Parameters Make $6,000.  
  <sub>$6K, $6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $6,000. $6K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $6,000 $6,000 Max Loss Limit $2,000 (static, non-trailing 🔥) $2,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $6,000, paid one time.  
  <sub>$6,000, $6K, $0, $0, $6,000, $6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- MGC and MCL is limited to 6 micros Learn more here . $1.5K Challenge How much does it cost? $39, one time.  
  <sub>6 micros, $1.5K, $39, · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Regular contract limits are set to 10 micros and 1 mini.  
  <sub>10 micros, 1 mini · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Once you reach $100,000, you can contact the Trade Desk to request higher contract limits.  
  <sub>$100,000, · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Daily Loss Limit Your Daily Loss Limit and starting contract limits are set by your Live account size.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Review the full rules Review the full rules Scaling plan Your contract limit is based on your account balance and follows the Scaling Plan.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>

## escalado (sim)

- Objectives: 5 Winning Days of $150 or more (non-consecutive) to request a Payout Net profit greater than $0 since your last Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Express Funded Account™ — Consistency An alternative XFA path with a different Payout structure.  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Objectives: Trade at least 3 days at 40% consistency to request a Payout Follow the Scaling Plan Rule: Do not let your Account Balance hit or exceed the Maximum Loss Limit Live Funded Account® Topstep’s prop firm capital.  
  <sub>3 days, 40% · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Consistency: at a glance XFA Standard XFA Consistency Payout eligibility 5 winning days of $150+ 3 days traded, 40% consistency target Max Payout 50% of balance, up to $5,000* 50% of balance, up to $6,000* Profit split 90/10 90/10 Scaling Plan ✅ ✅ Maximum Loss Limit (MLL) ✅ ✅ Daily Loss Limit (DLL) Optional Optional Consistency Target ❌ ✅ Profit Target ❌ ❌ *See the Payout Policy for Payout cap details by account size.  
  <sub>$150, 3 days, 40%, 50%, $5,000, 50% · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Express Funded Account Standard Rule Do not hit your Maximum Loss Limit Objectives Follow the Scaling Plan — the max contracts you can hold at one time — based on your current account balance.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Express Funded Account Consistency Rule Do not hit your Maximum Loss Limit Objectives Follow the Scaling Plan — the max contracts you can hold at one time — based on your current account balance.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- What is the Scaling Plan? | Topstep Help Center Copyright 2023.  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- All Collections Topstep Program Funded Accounts Express Funded Account® What is the Scaling Plan?  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- What is the Scaling Plan?  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- July 16, 2026 Table of contents Overview The Scaling Plan is an Express Funded Account® (XFA) objective.  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- It sets your Maximum Position Size — the max contracts you can hold at one time — based on your current account balance. ☝️ The Scaling Plan does not apply to the Live Funded Account®.  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Wait for the next session. ⚠️ Why is the Scaling Plan important?  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- The Scaling Plan acts as a guide on how to responsibly leverage a growing account.  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Micros and Minis 10:1 ratio: 1 Mini = 10 Micro contracts Limits are based on mini-contract equivalents Example — $50K XFA, 2-lot Scaling Plan: 2 Minis, OR 20 Micros, OR Any combo equal to 2 Minis ⚠️ Please note: The Micro to Mini ratio functionality is available for the Trading Combine and Express Funded Account.  
  <sub>10:1, 1 Mini, 10 Micro, $50K, 2 Minis, 20 Micros · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Silver (SI); counts as 2 of any other micro Micro Bitcoin (MBT) Capped at mini-equivalent lot sizes, not standard micro scaling Micro Ether (MET) Capped at mini-equivalent lot sizes, not standard micro scaling Scaling Plan FAQs What if I accidentally exceed my limit but fix it right away?  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- How do I avoid exceeding the Scaling Plan?  
  <sub> · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- How do Payouts affect my Scaling Plan?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Additionally, MGC and MCL is limited to 6 micros. ⚠️ Please note: For Express Funded Accounts, position limits for restricted products have a ceiling of the contracts listed above (CL = 3/6/9, for example). ​ However, a trader's actual limit may be lower depending on their current account balance, as the Scaling Plan applies independently.  
  <sub>6 micros · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- If your Lead and Follower accounts are at different Scaling Plan tiers — meaning their margin requirements differ — the Trade Copier may disconnect automatically at the start of a new trading day.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- If the Scaling plan does not match between the Leader and followers - follower account will be automatically removed at the start of the trading day When a Payout request is submitted, Follower accounts are automatically unlinked.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Pro Accounts are subject to the contract size Scaling Plan .  
  <sub> · [14645398-what-is-a-pro-account](https://help.topstep.com/en/articles/14645398-what-is-a-pro-account)</sub>
- Phase 2: Express Funded Account® (XFA) Parameter Value Path Standard Payout Cap $25,000 Max Loss Limit $10,000 After first Payout, MLL sets to $0 Max Contracts: 25 mini / 250 micro Scaling Plan Balance Lots Below $1,500 3 Lots $1,500 - $2,000 4 Lots $2,000 - $3,000 5 Lots $3,000 - $4,500 10 Lots $4,500 - $6,000 15 Lots $6,000 - $8,000 20 Lots Above $8,000 25 Lots Learn more about how the Scaling Plan works here .  
  <sub>$25,000, $10,000, $0, 25 mini, 250 micro, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $3,000. $3K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $3,000 $3,000 Max Loss Limit $1,000 (static, non-trailing 🔥) $1,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $3,000, paid one time.  
  <sub>$3,000, $3K, $0, $0, $3,000, $3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $1,500. $1.5K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $1,500 $1,500 Max Loss Limit $500 (static, non-trailing 🔥) $500 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 2 micro (no minis)* 2 micro (no minis)* Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $1,500, paid one time.  
  <sub>$1,500, $1.5K, $0, $0, $1,500, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $6,000. $6K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $6,000 $6,000 Max Loss Limit $2,000 (static, non-trailing 🔥) $2,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $6,000, paid one time.  
  <sub>$6,000, $6K, $0, $0, $6,000, $6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Does this change how capital is unlocked in my LFA (Scale In and Scale Up) or DLL expansion?  
  <sub> · [15764697-the-topstep-octagon](https://help.topstep.com/en/articles/15764697-the-topstep-octagon)</sub>
- Scale In and Scale Up and Dynamic Live Risk Expansion are not changing.  
  <sub> · [15764697-the-topstep-octagon](https://help.topstep.com/en/articles/15764697-the-topstep-octagon)</sub>
- At Live activation: 20% of your combined total balance is available for trading The remaining balance unlocks in 25% increments through performance milestones Each unlock releases 25% of your reserve balance , until you reach your Live Account starting balance Topstep may make discretionary exceptions for select traders based on performance and risk evaluation.  
  <sub>20%, 25%, 25% · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Review the full rules Review the full rules Your Daily Loss Limit continues to scale up or down with your available balance.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Your initial and following payouts are limited to 50% of your share of Trading Profits until you reach 30 Benchmark Trading Days in your Live Funded Account.  
  <sub>50% · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Review the full rules Review the full rules Scaling plan Your contract limit is based on your account balance and follows the Scaling Plan.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>

## riesgo_por_trade (filtro)

- The Consistency path gets you to Payout eligibility faster but adds a 40% threshold.  
  <sub>40% · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>

## relacion_riesgo_beneficio (filtro)

- Micros and minis count at a 10:1 ratio.  
  <sub>10:1 · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Micros and Minis 10:1 ratio: 1 Mini = 10 Micro contracts Limits are based on mini-contract equivalents Example — $50K XFA, 2-lot Scaling Plan: 2 Minis, OR 20 Micros, OR Any combo equal to 2 Minis ⚠️ Please note: The Micro to Mini ratio functionality is available for the Trading Combine and Express Funded Account.  
  <sub>10:1, 1 Mini, 10 Micro, $50K, 2 Minis, 20 Micros · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Special Product Weightings Some products are weighted differently and do not follow the standard 10:1 ratio: Product Rule Micro Silver (SIL) 5:1 ratio vs.  
  <sub>10:1, 5:1 · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- Instead, the Risk Team looks for recurring patterns over time, including: Significant drawdown of seeded capital (excluding profits and bonuses) Patterns of YOLO behavior or lack of discipline, including but not limited to: Repeatedly hitting the Daily Loss Limit Activity that resembles gambling rather than disciplined trading Inconsistent performance with a risk/reward imbalance — daily losses far exceeding typical wins.  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>

## ganancia_extraordinaria (filtro)

- Discipline over time beats one lucky session.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- A few lucky fills won’t get your Payout rejected.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>

## tiempo_minimo_tenencia (filtro)

- Errors corrected in under 10 seconds are ignored.  
  <sub>10 seconds · [8284223-what-is-the-scaling-plan](https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan)</sub>
- CME Velocity Logic: Quick Guide What It Is Mechanical safety pause Triggers when Price outruns liquidity Protects market structure (not volatility) What Triggers It Extreme speed + distance Order book can't refill fast enough Pause lasts ~2-10 seconds What Happens Trading pauses Aggressive orders canceled Liquidity refresh → trading resumes What It is NOT Not news, open, or volatility driven Not a trading signal Stops are NOT protected Trader Mindset Liquidity failure = higher risk Expect slippage Don't chase immediately Bottom Line Velocity Logic activates when the market's mechanics break —not when volatility is high.  
  <sub>10 seconds · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- Duration: Typically 2–10 seconds Market State: Reserved / Pre-Open Trading Activity: No trades are matched Aggressive orders that caused the event are canceled Purpose: Stabilize the order book Allow liquidity providers to refresh quotes ☝️ Following the Velocity Logic Event, trading resumes normally, often with a small price gap.  
  <sub>10 seconds · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- It gives you a visual breakdown of buy and sell interest for ES, NQ, CL, and GC — updated every 10 seconds using Express Funded Account data.  
  <sub>10 seconds · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Instant Payouts for Funded Traders | 99% Approval | Topstep Skip to Main Content Funded Trading Prop Firm How It Works Topstep Octagon Instant Payouts Brokerage TopstepX Blog Support Trader Support Help Center Status Page Discord Login Sign Up Sign Up ​ ​ The best payout in the industry Get started today Get started today See how it works See how it works $1.4B+ Paid out to traders 1 9 seconds Average instant payout time* 99.26% Payout approval rate 90% Profit split Aeropay x Topstep We’ve partnered with Aeropay to make payouts instant**.  
  <sub>99%, $1.4, 9 seconds, 99.26%, 90% · [instant-payouts](https://www.topstep.com/instant-payouts)</sub>
- Most approved payouts are delivered in under 9 seconds on average.  
  <sub>9 seconds · [instant-payouts](https://www.topstep.com/instant-payouts)</sub>
- Visit our Help Center Visit our Help Center *Average payout speed of less than 9 seconds applies to auto approved payout requests for US traders using RTP with Aeropay only.  
  <sub>9 seconds · [instant-payouts](https://www.topstep.com/instant-payouts)</sub>

## noticias (filtro)

- FOMC — Federal Open Market Committee.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- Best Practices Use stop losses before approaching your Maximum Loss Limit Monitor unrealized P&L — not just closed trades Leave a buffer above your limit during volatile markets Avoid trading during high-impact news events ⚠️ Your Maximum Loss Limit is calculated on real-time unrealized P&L.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Economic Releases | Topstep Help Center Copyright 2023.  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- All Collections Getting Started Trading Education Economic Releases Economic Releases News drops.  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- Updated over 2 weeks ago Table of contents Economic releases are scheduled government reports that give the market key data on the economy — things like unemployment, interest rate decisions, and supply figures.  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- Common Economic Releases Know what releases affect your products and when they happen.  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- Release Time (CT) Products Affected Unemployment Rate 7:30 AM ES, NKD, NQ, 6A, 6B, 6C, 6E, 6J, 6S, E7, GE, YM, UB, ZT, ZF, ZN, ZB, GC, RTY, SI, HG, TN, 6M, M6A, M6E, 6N, MBT, MET FOMC Statement 1:00 PM All products Crude Oil Inventories (EIA) 9:30 AM / 10:00 AM* CL, QM, MCL, RB Natural Gas Inventories (EIA) 9:30 AM NG, QG Crop Production 11:00 AM ZC, ZS, ZW, ZM, ZL *Pending abbreviated trading hours.  
  <sub>7:30, 1:00, 9:30, 10:00, 9:30, 11:00 · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- Trading During the News Topstep doesn't require you to flatten positions during economic releases — in SIM or Funded Accounts.  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- A few things to know: Trades impacted by economic releases are not eligible for exceptions or Reset credits Results are your responsibility — full stop To reduce slippage risk: cut your position size, use limit orders, or avoid trading the event entirely. ⚠️ You own the outcome.  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- FAQs What causes slippage during economic releases?  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- Monitor economic calendars so you know what's coming.  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- Federal Open Market Committee (FOMC): The Federal Open Market Committee (FOMC) consists of twelve members--the seven members of the Board of Governors of the Federal Reserve System; the president of the Federal Reserve Bank of New York; and four of the remaining eleven Reserve Bank presidents, who serve one-year terms on a rotating basis.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Click here for FOMC info - including News & Events Flipping the Ticket: buying when you meant to sell, or selling when you meant to buy.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- When slippage is most likely Economic releases High volatility periods Illiquid markets Swing highs/lows Market open and close What causes Slippage 3 main drivers: volatility, liquidity, and market gaps.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Economic releases, unexpected events, sharp moves — all of it can push your execution away from your intended price.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- To minimize slippage: Avoid trading during major news events Trade during high-liquidity market hours Does slippage occur in simulated trading and other financial markets?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Slippage can happen anytime, but it's most likely around: Economic Releases High volatility periods Illiquid markets / low market depth Price action around swing highs and lows Market open/close and opening range breakouts Why wasn't my order filled / It blew past my stop ​ Why wasn't my order filled?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- In fast or volatile markets — gaps, major economic releases, sudden imbalances — your stop triggers but fills at the next available price, not the stop price.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Economic Releases Prohibited Trading Strategies at Topstep CME Velocity Logic TopstepX™ Did this answer your question?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Trading Maximum Position Size into Major News Events Purposefully trading your full Maximum Position Size directly into a scheduled major news event.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- During news events like CPI, FOMC, or NFP, or at the market open: Liquidity remains continuous Market makers are active (though with wider spreads) Orders continue filling normally Velocity Logic only triggers when liquidity collapses or the market’s mechanics cannot keep pace with price movement.  
  <sub> · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- Key Takeaways A Velocity Logic Event is a liquidity warning, not a volatility signal Stop orders are not protected and may suffer severe slippage Position sizing must assume worst-case fills, not ideal execution Chasing price immediately after a Velocity Logic Event increases risk Related Articles General Platform Troubleshooting Economic Releases Topstep Trader Lingo Glossary Order Types, Fills, and Slippage Risk Adjustments: High Risk/High Volatility Did this answer your question?  
  <sub> · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- Trading during CPI is also restricted to 0.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility) +1</sub>
- CPI Release Restrictions Ahead of Consumer Price Index (CPI) releases, Topstep temporarily restricts new opening transactions on equity index products (ES, RTY, YM, NQ, NKD) in SIM to protect Traders from extreme volatility.  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Existing Positions: Traders holding existing positions in Metals (GC, SI, HG, PL) prior to 7:25 AM CT may keep them open and manage them through the CPI window.  
  <sub>7:25 · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- A firm reducing exposure before a major news event.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Trader Hub Trader Hub Real-time market news and economic events, powered by Financial Juice.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Economic Events Calendar — A live global schedule shown in your PC's time zone.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Impact Levels: Events are color-coded by market impact: Red (High), Orange (Medium), and Yellow (Low). ⚠️ Important: High-impact news events bring volatility — wider spreads, fast price swings, and slippage.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- News Events TopstepX auto-plots high-impact news events directly on your charts — click a marker to see the event.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Chart Display Settings Chart Value Display Type — show order/position values in Dollar value, Ticks, Percent, or Points Hide Economic Events — hides economic news plots from your charts Hide Chart Plots / Chart Plot Alignment — additional display controls under Settings → Charts & Data NEW: Range Bars Range Bars 👉 Let price — not the clock — decide when a bar prints, so trends, consolidation, and breakouts stand out without the noise of time-based charts.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Closed accounts still count, so if one closes you can't replace it. $3K and $1.5K Challenges don't count toward the 5. 👉 For all Labs offerings, be sure to check the Risk Adjustments article to see how high-risk products and CPI restrictions may affect your account.  
  <sub>$3K, $1.5K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>

## horario_y_overnight (filtro)

- Putting “more-on.” Naked Point of Control (NPOC) — A previous volume point of control that hasn’t been re-tested during regular trading hours.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- Opening Range — Per Hoag: the first minute of regular trading hours.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- Point of Control (POC) — The most visited price during the previous day’s regular trading hours.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- R-Z ​ Regular Trading Hours (RTH) — Old floor pit trading hours.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- For ES: 8:30 AM – 3:15 PM CT.  
  <sub>8:30, 3:15 · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- How to Reach Us Channel Details Chat Click the messenger icon (bottom-right of screen) or "Chat with us" (top-right of website) Phone 888-407-1611 — Mon–Fri, 8:00 AM–5:00 PM CT.  
  <sub>8:00, 5:00 · [8284118-contact-support](https://help.topstep.com/en/articles/8284118-contact-support)</sub>
- Trading outside permitted hours — Orders placed outside Topstep’s permitted trading hours are rejected.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Check the holiday trading hours article.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Trading day hours: The trading day runs from 5:00 PM CT through 3:10 PM CT the next calendar day.  
  <sub>5:00, 3:10 · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Trades placed after 5:00 PM CT (e.g., 6:30 PM CT Tuesday) count toward Wednesday's activity.  
  <sub>5:00, 6:30 · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Prohibited Conduct Prohibited Trading Strategies Maximum Loss Limit Daily Loss Limit Consistency Target Permitted Products and Trading Hours Related Articles Trading Combine Subscriptions When and What Products Can I Trade?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- All positions must be closed by 3:10 PM CT every weekday.  
  <sub>3:10 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- You can resume trading at 5:00 PM CT.  
  <sub>5:00 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- Trading Hours Session Hours Sunday open 5:00 PM CT Weekday close 3:10 PM CT Weekday reopen 5:00 PM CT Friday close 3:10 PM CT (closed till Sunday at 5:00 PM) All open positions and pending orders begin to automatically cancel at 3:10 PM CST.  
  <sub>5:00, 3:10, 5:00, 3:10, 5:00, 3:10 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- Avoid opening new positions after 3:08 PM CT — Risk Managers begin flattening at that time.  
  <sub>3:08 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- It's still your responsibility to be flat by 3:10 PM CT.  
  <sub>3:10 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- If you're trading a product with an earlier daily close than 3:10 PM CT, you must exit before that product's close.  
  <sub>3:10 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- Special Trading Hours CBOT Commodity Products (Corn, Wheat, Soybeans, Soybean Meal, Soybean Oil): Sunday–Monday: 7:00 PM – 7:45 AM CT Monday–Friday: 8:30 AM – 1:20 PM CT CME Agriculture Products (Live Cattle, Lean Hogs): Monday–Friday: 8:30 AM – 1:05 PM CT CBOT Commodity Market Pause (Mon–Fri): 7:45 AM – 8:30 AM CT.  
  <sub>7:00, 7:45, 8:30, 1:20, 8:30, 1:05 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- Color Market State 🔵 Blue Pre-Open 🟠 Orange Paused 🟢 Green Open 🔴 Red Closed FAQ Can I swing trade or hold positions overnight?  
  <sub> · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- All positions must be closed by 3:10 PM CT each weekday.  
  <sub>3:10 · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- At 3:10 PM CT, that day's value locks into your trading history and cannot be changed.  
  <sub>3:10 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- A future day becomes your new best day if it exceeds the previous one and locks at 3:10 PM CT on its own day.  
  <sub>3:10 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- If your best day was set during the current trading session (before 3:10 PM CT), any additional profit you earn today adds directly to that best day total — which raises your adjusted Profit Target even further. ​ To resolve a Consistency Target increase, the remaining profit must be earned on a separate trading day, after the market close of the session in which your best day was set. ​ Example : You're in a $50K Trading Combine with a $3,000 Profit Target.  
  <sub>3:10, $50K, $3,000 · [8284208-consistency-at-topstep](https://help.topstep.com/en/articles/8284208-consistency-at-topstep)</sub>
- Release Time (CT) Products Affected Unemployment Rate 7:30 AM ES, NKD, NQ, 6A, 6B, 6C, 6E, 6J, 6S, E7, GE, YM, UB, ZT, ZF, ZN, ZB, GC, RTY, SI, HG, TN, 6M, M6A, M6E, 6N, MBT, MET FOMC Statement 1:00 PM All products Crude Oil Inventories (EIA) 9:30 AM / 10:00 AM* CL, QM, MCL, RB Natural Gas Inventories (EIA) 9:30 AM NG, QG Crop Production 11:00 AM ZC, ZS, ZW, ZM, ZL *Pending abbreviated trading hours.  
  <sub>7:30, 1:00, 9:30, 10:00, 9:30, 11:00 · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- They update at 4:05 PM CT after each session and vary by product, contract month, and time of day.  
  <sub>4:05 · [8284225-staying-outside-the-2-price-limit-zone](https://help.topstep.com/en/articles/8284225-staying-outside-the-2-price-limit-zone)</sub>
- Overnight limits differ from RTH limits. ➡ Check current CME Price Limits here — they change regularly. 📣 Update: Equity products ES, MES, NQ, MNQ, RTY, M2K, YM, and MYM overnight price limits have expanded from 5% to 7%.  
  <sub>5%, 7% · [8284225-staying-outside-the-2-price-limit-zone](https://help.topstep.com/en/articles/8284225-staying-outside-the-2-price-limit-zone)</sub>
- TopstepX™ — Commissions and Fees Daily Loss Limit in the Trading Combine and Express Funded Account Topstep Holiday Trading Hours CME Velocity Logic Did this answer your question?  
  <sub> · [8284225-staying-outside-the-2-price-limit-zone](https://help.topstep.com/en/articles/8284225-staying-outside-the-2-price-limit-zone)</sub>
- Available starting at 3:30 PM CT on Tuesday, June 2nd. ​ Traders who voluntarily add a Daily Loss Limit to their account unlock double per-request payout caps.  
  <sub>3:30 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- All Traders who make a new Trading Combine purchase and add a Daily Loss Limit (DLL) at checkout will receive the increased Payout cap, during this limited time offering beginning at 3:30 PM CT on Tuesday, June 2nd. ​ ​ Why is this a limited-time offering, and how long will this last?  
  <sub>3:30 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- A day locks in at 4:00 PM CT.  
  <sub>4:00 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Days lock in at 4:00 PM CT.  
  <sub>4:00 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Processing times are estimates and exclude weekends and holidays.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- The trading day runs from 5:00 PM CT to 3:10 PM CT the following day.  
  <sub>5:00, 3:10 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- A request submitted after 5:00 PM CT belongs to the next trading day — that day becomes the Payout request day and is excluded from the new cycle.  
  <sub>5:00 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- This applies to all account types. ​ Example: A Payout request submitted at 5:59 PM CT on Monday belongs to the Tuesday trading session.  
  <sub>5:59 · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- What it shows 3 background-shaded windows: Asia (17:00–02:00 CT), London (02:00–08:30 CT), NY (08:30–16:00 CT).  
  <sub>17:00, 02:00, 02:00, 08:30, 08:30, 16:00 · [8524249-topstepx-indicators](https://help.topstep.com/en/articles/8524249-topstepx-indicators)</sub>
- What it shows High/low of the first 15 minutes from a configurable open time (default 08:30 CT).  
  <sub>15 minutes, 08:30 · [8524249-topstepx-indicators](https://help.topstep.com/en/articles/8524249-topstepx-indicators)</sub>
- Moron Trade: Adding to a losing position - putting "more-on" Naked Point of Control (NPOC): A previous volume point of control that has not been re-tested during regular trading hours.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Opening Range: Hoag considers the first minute of trading during regular trading hours to be the opening range.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Point of Control (POC): Most visited price during the previous day's Regular Trading Hours.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Regular Trading Hours (RTH): Regular trading hours in the futures markets refer to the old trading floor pit trading hours.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Tap in from wherever. 📺 Watch on YouTube 🗯️ Watch on Twitch 🟢 Watch on Kick 📅 TopstepTV Schedule Schedule Sunday: 7:00 PM CT - Slow Markets Monday–Friday: Starting 7:15 AM CT through the evening Feedback Post questions and feedback in the YouTube live chat during the broadcast.  
  <sub>7:00, 7:15 · [8703714-topstep-community](https://help.topstep.com/en/articles/8703714-topstep-community)</sub>
- What Happens When It Triggers Net P&L hits or exceeds the DLL during the trading day (5 PM CT – 3:10 PM CT): Open positions are flattened Pending orders are canceled No new trades until 5 PM CT next session ☝️ Account stays eligible for funding.  
  <sub>3:10 · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- End-of-day qualification: Your net P&L at market close must meet or exceed your current level during a month with no prior bonus.  
  <sub> · [11177768-topstepx-live-performance-bonus](https://help.topstep.com/en/articles/11177768-topstepx-live-performance-bonus)</sub>
- As long as your net profit hits the qualifying level by market close, you're eligible — even if you had a drawdown earlier in the day.  
  <sub> · [11177768-topstepx-live-performance-bonus](https://help.topstep.com/en/articles/11177768-topstepx-live-performance-bonus)</sub>
- The DLL will return to $3,000 after the market closes on Friday if your balance is above $10,000.  
  <sub>$3,000, $10,000 · [11748475-dynamic-live-risk-expansion](https://help.topstep.com/en/articles/11748475-dynamic-live-risk-expansion)</sub>
- Topstep Holiday Trading Hours | Topstep Help Center Copyright 2023.  
  <sub> · [13350348-topstep-holiday-trading-hours](https://help.topstep.com/en/articles/13350348-topstep-holiday-trading-hours)</sub>
- All Collections Getting Started Topstep Holiday Trading Hours Topstep Holiday Trading Hours Holidays bring shortened or closed markets.  
  <sub> · [13350348-topstep-holiday-trading-hours](https://help.topstep.com/en/articles/13350348-topstep-holiday-trading-hours)</sub>
- Position Close Rule Close all positions 15 minutes before early close (e.g., close by 11:45 CT for a 12:00 CT close) Applies to: Trading Combine®, Express Funded Account® (XFA), Live Funded Account® (LFA) Open positions at the cutoff will be auto-liquidated ⚠️ Holiday trading hours are subject to change per the exchange.  
  <sub>15 minutes, 11:45, 12:00 · [13350348-topstep-holiday-trading-hours](https://help.topstep.com/en/articles/13350348-topstep-holiday-trading-hours)</sub>
- Example: If a holiday falls on a Monday with reduced trading hours, the CME may treat the period from Sunday's market open through Tuesday's market close as a single trading day.  
  <sub> · [13350348-topstep-holiday-trading-hours](https://help.topstep.com/en/articles/13350348-topstep-holiday-trading-hours)</sub>
- When Velocity Logic Events Typically Occur Overnight or low-liquidity sessions Algorithmic malfunctions Stop cascades after sudden book thinning Data feed or quote disruptions 👉 Velocity Logic events rarely occur during high-participation periods.  
  <sub> · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- Existing Positions: Traders holding existing positions in Metals (GC, SI, HG, PL) prior to 7:25 AM CT may keep them open and manage them through the CPI window.  
  <sub>7:25 · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Contracts are automatically rolled over during the daily market close window (4:00 PM – 5:00 PM CST) based on an internal algorithm to determine the optimal time to roll active contracts prior to the next trading day based on volume, open interest, and expiration dates.  
  <sub>4:00, 5:00 · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Extended and Regular Trading Hours Toggle Extended and Regular Trading Hours Toggle Switch between ETH and RTH charts for better context.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Extended Trading Hours ( ETH) — near 24-hour coverage.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Regular Trading Hours ( RTH) — higher participation.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Products may be traded during normal electronic trading hours unless otherwise indicated.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If the Net P&L should hit or exceed the Daily Loss Limit during the trading day (5:00 PM CT-3:10 PM CT), the account will hit a soft breach and will be auto-liquidated for the remainder of the then current trading session.  
  <sub>5:00, 3:10 · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- This means any open trading positions will be flattened, any pending orders will be canceled, and your account will be prevented from placing any new trades until the start of the next trading day (5:00 PM CT).  
  <sub>5:00 · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Trading can only occur during normal electronic trading hours unless otherwise indicated by us.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- … 10 más en inventario.json

## instrumentos (filtro)

- Contract Sizing at Topstep Account Max Contracts 50K 5 100K 10 150K 15 See the full permitted products list for all available contracts.  
  <sub> · [8284113-can-i-trade-forex-with-you](https://help.topstep.com/en/articles/8284113-can-i-trade-forex-with-you)</sub>
- Prohibited Conduct Prohibited Trading Strategies Maximum Loss Limit Daily Loss Limit Consistency Target Permitted Products and Trading Hours Related Articles Trading Combine Subscriptions When and What Products Can I Trade?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Default: CME data covered Takes effect at your next billing cycle If you want a different exchange covered: contact the Live Accounts & Funding Team Fees for additional exchanges still apply and are billed on the 26th of each month Data fee: $133 per exchange, per month Exchange Products Covered CME ES, MES, NQ, MNQ, RTY, M2K, NKD, 6A, 6B, 6C, 6E, 6J, 6S, E7, HE, LE, GE NYMEX CL, QM, NG, QG COMEX GC, SI, HG CBOT ZC, ZW, ZS, ZM, ZL, YM, MYM, ZT, ZF, ZN, ZB, UB, TN To trade all permitted products in the LFA, you'd need all 4 exchanges = $540/month total.  
  <sub>$133, $540 · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- Additionally, MGC and MCL is limited to 6 micros. ⚠️ Please note: For Express Funded Accounts, position limits for restricted products have a ceiling of the contracts listed above (CL = 3/6/9, for example). ​ However, a trader's actual limit may be lower depending on their current account balance, as the Scaling Plan applies independently.  
  <sub>6 micros · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Are there restricted products for the $3K Challenge?  
  <sub>$3K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Are there restricted products for the $1.5K Challenge?  
  <sub>$1.5K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Are there restricted products for the $6K Challenge?  
  <sub>$6K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Get started Get started Available products Trade top futures markets on TopstepX, a platform built specifically for futures trading.  
  <sub> · [topstepx](https://www.topstep.com/topstepx)</sub>
- Traders are only permitted to trade permitted products by Topstep.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>

## estrategias_prohibidas (filtro)

- Objectives: 5 Winning Days of $150 or more Do not hit or exceed the Daily Loss Limit (DLL) — breaching it deactivates your account for that trading day Rule: Do not let your Account Balance reach or go below $0 Key Links Trading Combine® Parameters Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Consistency at Topstep Express Funded Account™ Parameters Topstep Payout Policy What is the Responsible Trading Program?  
  <sub>$150, $0 · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Busting a Trade — Voiding a trade due to errors or exchange rule violations.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- Related Articles Topstep Payout Policy Topstep Trader Lingo Glossary Prohibited Conduct Topstep Labs The Topstep Octagon Did this answer your question?  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- What about countries with human rights violations?  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- When contacting Trader Support for a refund, provide your Trading Combine or Express Funded Account Number, the last four digits of the charged card, the charge date, and any relevant screenshots or recordings. ⚠️ Filing a chargeback or dispute is strictly prohibited .  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Chargebacks at Topstep ⚠️ Filing a chargeback or dispute is strictly prohibited .  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Initiating chargebacks is listed as prohibited conduct .  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies) +1</sub>
- Credit or debit card: Visa, Mastercard, American Express, Discover. 👉 Must be in your own name — using someone else's card violates Topstep's Terms of Use.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Prohibited Conduct What is Responsible Trading?  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Multiple profiles are a Terms of Use violation and can result in account closure or suspension.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Test on your Practice Account first and review Prohibited Conduct and Prohibited Trading Strategies before going live.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Prohibited Conduct Prohibited Trading Strategies Maximum Loss Limit Daily Loss Limit Consistency Target Permitted Products and Trading Hours Related Articles Trading Combine Subscriptions When and What Products Can I Trade?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Learn more here: Topstep Community and Topstep Learning Key Links Topstep Program Overview Trading Combine® Parameters Trading Combine Subscription Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Am I Eligible to Trade with Topstep?  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- If your account touches or falls below a limit at any point, it's a violation and liquidation triggers immediately.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Slippage and price movement during execution can push your final realized balance back above the limit — but the violation already happened based on unrealized P&L.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Related Articles Topstep Learning Order Types, Fills, and Slippage Prohibited Trading Strategies at Topstep CME Velocity Logic Risk Adjustments: High Risk/High Volatility Did this answer your question?  
  <sub> · [8284211-economic-releases](https://help.topstep.com/en/articles/8284211-economic-releases)</sub>
- Review Prohibited Conduct and Prohibited Trading Strategies first.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Hedging across accounts and coordinated trading with others is prohibited.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Payout Policy requirements (outlined above) Prohibited Conduct , Terms of Use , and Professional Behavior Prohibited Trading Strategies What tax forms are required?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Hitting the Daily Loss Limit puts your account in a Temporary Violation.  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- However, US-based single-member LLCs may receive Payouts and file taxes under the LLC: Use your personal info on the Funded Account Agreement Use your LLC info on bank and tax forms Not permitted: C-corps, S-corps, or multi-member LLCs.  
  <sub> · [8284238-funded-trader-tax-questions](https://help.topstep.com/en/articles/8284238-funded-trader-tax-questions)</sub>
- Pairs well with: Inverse Fair Value Gap, Balanced Price Range, Sessions, Opening Range Inverse Fair Value Gap 🔄 👉 Track Fair Value Gaps that have been violated and flipped — imbalances that failed become the new draw for the opposite move. ​ What it shows An Inverse Fair Value Gap (IFVG) forms when price closes through an existing Fair Value Gap rather than respecting it.  
  <sub> · [8524249-topstepx-indicators](https://help.topstep.com/en/articles/8524249-topstepx-indicators)</sub>
- A violated bullish FVG flips to a bearish IFVG; a violated bearish FVG flips to a bullish IFVG.  
  <sub> · [8524249-topstepx-indicators](https://help.topstep.com/en/articles/8524249-topstepx-indicators)</sub>
- Busting a trade: Voiding a trade due to errors or CME/exchange rule violations when trades were made on the floor.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- No account selling or sharing — buying, selling, or sharing Topstep accounts violates our TOS.  
  <sub> · [8703714-topstep-community](https://help.topstep.com/en/articles/8703714-topstep-community)</sub>
- Economic Releases Prohibited Trading Strategies at Topstep CME Velocity Logic TopstepX™ Did this answer your question?  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- For more information on Prohibited Trading Strategies, go here .  
  <sub> · [10290170-professional-behavior-at-topstep](https://help.topstep.com/en/articles/10290170-professional-behavior-at-topstep)</sub>
- Prohibited Conduct | Topstep Help Center Copyright 2023.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- All Collections Topstep FAQs Prohibited Conduct Prohibited Conduct Program integrity starts here.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Updated over 2 weeks ago Table of contents Prohibited Conduct applies at every level of the Topstep program.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Violations are reviewed case-by-case based on severity and history.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Possible responses to a Prohibited Conduct violation: Warning Deletion of the impacted trading day Account Reset Permanent account closure Delay or denial of a Payout request Ultimately, the action Topstep takes will depend on the infractions severity and your prior history (or lack thereof).  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- What Is Prohibited Conduct?  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Exploiting platform deficiencies — using instruments or methods that misuse bugs, errors, or deficiencies in the platform Circumventing geographical or technical restrictions Holding a position within 2% of a product’s price lock limit — see How to Ensure I Am Not Trading Within 2% of a Price Limit Trading on behalf of others — including sharing incentives as part of any business arrangement Account stacking — repeatedly hitting the Maximum Loss Limit in one account and switching to another to repeat high-risk attempts Any other conduct that Topstep determines, at its sole discretion, is uncommercial, games the market, is not a viable strategy, or is not responsible trading Do not use a VPN.  
  <sub>2%, 2% · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- VPNs, proxy services, TOR, geo-location obfuscation, and other identity-masking services are not permitted at Topstep.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- If you see an Error 403 Forbidden message, disable your VPN or proxy and try again.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Prohibited Conduct regarding Trader Profiles: Harmful, offensive, illegal, or sexual content Personal Data or misleading claims Unauthorized names, trademarks, or third-party content Advertising, scams, or attempts to evade moderation Notice that Profile Content may undergo automated screening and moderation, which may result in profile suspension or deactivation 🤝 Trading with friends & family is part of the Ultimate Trading Experience.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Trust reviews Terms of Use violations, fraudulent activity, and account manipulation.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Appeals can be denied if the review finds ToU violations, fraudulent activity, or account manipulation.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- An appeal may not be possible depending on the severity of the Terms of Use violation.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- View the full Prohibited Conduct section in the Terms of Use Related Articles Trading Combine® Parameters New to Topstep?  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Prohibited Trading Strategies at Topstep What is Responsible Trading?  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Prohibited Trading Strategies at Topstep | Topstep Help Center Copyright 2023.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- All Collections Topstep FAQs Prohibited Trading Strategies at Topstep Prohibited Trading Strategies at Topstep From account stacking to SIM exploitation: what's not allowed June 10, 2026 Table of contents Topstep prohibits specific trading behaviors that exploit program structure, contradict real-market discipline, or create financial risk for the firm.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- This exploits risk parameters and is not permitted.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Violating Topstep’s Terms of Use Any trades performed in conflict with Topstep’s Terms of Use or the Trading Combine® (TC) terms and conditions.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Using Unfair Technology Using software, AI, ultra-high speed systems, or mass data entry that manipulates, abuses, or provides an unfair advantage on the platform or in the program.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Exploiting the simulator will get you removed from the program.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- We retain the right to reject profit claims if abuse is suspected.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- If you’re here to trade, this isn’t about you. ​ Examples of exploiting or manipulating the Topstep simulator include, but are not limited to: Running scalping algorithms designed to exploit unrealistic SIM fills Making hundreds of rapid trades to take advantage of preferential queue position in SIM Initiating reckless trades in gapped markets to profit from stray fills — these are improbable in live markets Repeatedly exploiting the relative lack of slippage in SIM to achieve impossible stop-loss execution Using tight brackets or auto-breakeven to take advantage of favorable SIM fills 👉 If this doesn't sound like you, it probably isn't.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Topstep shuts this down quickly to keep risk managers and coaches focused on helping Traders — not monitoring abuse. ​ For more information, please refer to our Prohibited Conduct and Professional Behavior policies.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Related Articles Topstep Learning Trading Combine® Parameters Prohibited Conduct What is Responsible Trading?  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Trader Resources Topstep Blog Help Center Status Page Topstep Learning Trader Support Windy (smart assistant, 24/7): https://www.topstep.com/contact-support/ Call: (888) 407-1611 Email: help@topstep.com Text: (866) 448-1642 WhatsApp: (773) 900-6673 All the rules and legal stuff Prohibited Conduct Know the rules before you trade.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Full details: Topstep's Prohibited Conduct .  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Other helpful links: Terms of Use Prohibited Trading Strategies Professional Behavior at Topstep Risk Disclosure 👉 Responsible trading comes down to one simple phrase that you’ll often hear from our Founder & CEO, Michael Patak, “Always Trade for Tomorrow!™” It means making decisions every day that are focused on managing risk and staying consistent, so you can grow your account, take payouts, and find longevity in the Live markets.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Prohibited Trading Strategies at Topstep What is the Responsible Trading Program?  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Triggering it is not a rule violation — it's a forced break for the rest of that session.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Is hitting the DLL a rule violation?  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- It's a temporary break — not a violation.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Multiple profiles violate our Terms of Use and may result in: Profiles or Trading Combines® closed without warning Temporary or permanent account suspension Do not create a new profile when purchasing additional Trading Combines®.  
  <sub> · [10513413-getting-started-with-the-topstep-dashboard](https://help.topstep.com/en/articles/10513413-getting-started-with-the-topstep-dashboard)</sub>
- … 85 más en inventario.json

## cobertura_y_copy (filtro)

- Delta Divergence — Price moving one direction while delta grows in the opposite direction.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- Hedge — Offsetting risk with an opposite position in a different market or contract month.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- If you have multiple accounts, double-check which one you're trading on before you start.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- You can also use a trade copier to duplicate trades across multiple accounts.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- See What is a Trade Copier? 📚 If you're new to Topstep or the Trading Combine, reading the following resources will enhance your experience: Trading Combine Subscriptions What is the Reset?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Yes, up to $750K buying power using a trade copier.  
  <sub>$750K · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- See What is a Trade Copier .  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Hedging across accounts and coordinated trading with others is prohibited.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- See Understanding Hedging and Topstep's Terms of Use .  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- What happens to copy trading during a Payout?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Delta (futures): An order flow measurement that totals the number of contracts that trade on the offer (positive delta) minus the number of contracts that trade on the bid (negative delta) Delta Divergence: Price moving in one direction with Delta growing in the opposite direction.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Hedge: Offset risk with an opposite position in a different market or contract month.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Just keep it by the book — no coordinated group trading, no account-sharing, no single-account rule workarounds.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Understanding Hedging Did this answer your question?  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct) +1</sub>
- You might end up here if you: Hit the Maximum Loss Limit on multiple accounts in 1 day Max position the majority of your trades Let losers run bigger than winners Trade without stops Go full port, trade on tilt, FOMO, or revenge Disrespect your daily limits Can't trade small?  
  <sub>1 day · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Learn more here: Topstep Community Trading with friends & family is part of the Ultimate Trading Experience Just keep it by the book — no coordinated group trading, no account-sharing, no single-account rule workarounds.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- A few things that'll get you flagged: Excessive purchases of Trading Combines® or Resets Trades that conflict with our Terms of Use Single & multi-user hedging Circumventing geographic restrictions Trading on behalf of others Trade with integrity and you've got nothing to worry about.  
  <sub> · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Time requirement 6 months None To request a review from the Risk Team 6 months of consistent trading + $10K net LFA profits, or good trading behavior $10K net LFA profits or good trading behavior 👉 For both paths, Risk Team review does not guarantee approval to rejoin the regular program or purchase multiple accounts.  
  <sub>$10K, $10K · [10551016-what-is-the-focused-trader-program](https://help.topstep.com/en/articles/10551016-what-is-the-focused-trader-program)</sub>
- The Profit Target mirrors your Trading Combine® profit target: LFA Size Profit Target to Unlock Reserve Increment $50K $3,000 $100K $6,000 $150K $9,000 Capital Expansion is: Reviewed every Monday morning Funds deposited within 1-2 business days Can be delayed or denied for excessive or reckless risk behavior You cannot unlock multiple tiers with a single large win — each threshold requires net profit since the last expansion .  
  <sub>$50K, $3,000, $100K, $6,000, $150K, $9,000 · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Tip: You can duplicate trades across multiple accounts using a trade copier.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- API access can affect the potential for hedging — more here . 👥 Getting Help Topstep does not provide technical support for coding or API implementation.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- Can I use 1 subscription across multiple accounts?  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- It's not a punishment — it's a structured path to rebuild discipline, consistency, and sound risk management. ​ This program gets you back on track — building the discipline and habits needed to trade responsibly in Live markets. 👉 You may need the Responsible Trading Program if: Multiple accounts hit the Maximum Loss Limit in one day You max position a majority of your trades You don’t keep losers smaller than winners You don’t use stops You go full port or trade on tilt, FOMO, or revenge You disrespect your daily limits Can't trade small?  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- Understanding Hedging | Topstep Help Center Copyright 2023.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- All Collections Topstep FAQs Understanding Hedging Understanding Hedging Cross-account hedging is prohibited at Topstep.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- This article explains what hedging is, why we prohibit it, and how to ensure your trading stays compliant.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- July 27, 2026 Table of contents What is Cross-Account Hedging?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Cross-account hedging means simultaneously going long and short the same or correlated instrument across multiple accounts — such as MES/ES, MNQ/NQ. ☝️ Simple Example: Express Funded Account (Account A): Long 5 contracts of ES Trading Combine (Account B): Short 5 contracts of ES When positions are hedged across accounts, you're protected from market risk — if the market moves up, Account A profits while Account B loses, and vice versa.  
  <sub>5 contracts, 5 contracts · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Why Institutional Hedging Is Different From Cross-Account Hedging 👉 These two things are not the same.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- What institutional hedging actually is: A market maker balancing inventory.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- A hedge fund protecting a long portfolio.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- What cross-account hedging looks like at a prop firm: Long in 1 account.  
  <sub>1 account · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Cross-account hedging distorts all of it.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- The Simple Version Institutional hedging → managing real market risk.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Cross-account hedging → manipulating prop firm outcomes.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Hedging itself isn't bad, but using it to pass evaluations or take payouts you haven't earned?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Our systems analyze: Position Timing: Are opposite positions opened and closed in coordinated patterns?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Duration: How long are opposite positions held simultaneously?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- First Hedging Attempt — Real-Time Warning If our system detects that you’ve become hedged across accounts: You’ll receive a real-time modal notification You will have a brief window to un-hedge your positions using the options in the modal notification: If you successfully un-hedge within the time window , you may continue trading You will receive a follow-up email notification If You Do Not Un-Hedge Your hedged positions will be automatically liquidated Your account will be flagged for hedging behavior You may continue trading This first instance serves as a warning and educational step .  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Repeat Hedging Attempt(s) on the Same Day If hedging occurs again on the same trading day : You will have a brief window to un-hedge If you do not un-hedge in time : Your hedged positions will be automatically liquidated You may continue trading Please note: There will not be a timer shown on this violation.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Please un-hedge immediately to continue trading.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Next Trading Day — Required Acknowledgement After the first Hedging attempt, you'll be required to sign an acknowledgement upon login on the next trading day.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- A modal notification will appear upon login You must acknowledge the Terms of Use related to hedging by typing "I agree" in the text box The modal will include: Explanation of the hedging policy Details of when the hedging occurred Requirement to acknowledge before trading You will not be able to trade until this acknowledgment is completed.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Future Hedging Attempts — Immediate Liquidation After acknowledgement: Any future hedging attempt will trigger immediate liquidation: After liquidation, you may continue trading You will not be given time to unhedge 5.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Excessive Hedging Attempts — Temporary Violation After excessive hedging attempts: Your positions will be immediately liquidated You will not have the opportunity to unhedge A Temporary Hedging Violation will be issued and you will be prohibited from trading for the remainder of the trading day.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- The violation will apply across the hedged accounts Please note: after numerous warnings, your account may be permanently closed without further notice if you continue to hedge your positions.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- For this reason, it's very important that you review our Hedging Policy and trade responsibly.Additionally, accounts closed for hedging violations are not eligible for payouts, and any associated profits cannot be withdrawn.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Important Notes Monitoring applies in real-time Time windows may be adjusted by Risk & Leadership teams Violations apply across all accounts involved in hedging This policy applies to the Trading Combine, Express, and Live Accounts Copy Trading and Technical Errors Technical glitches and copy trading software can create temporary opposite positions — our system accounts for that.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Manual errors, such as switching directions without closing prior positions, can also result in unintentional hedging. ⚠️ If a hedged position meets our criteria (size, duration, intent), enforcement happens.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- How to Avoid Hedging Violations Best Practices Trade a single account to completely avoid the possibility of hedging Trade each account independently based on your own analysis Don't coordinate positions across accounts (or other traders) to offset risk Monitor copy trading tools to ensure they're not creating opposite positions Close any accidental hedges immediately if they occur Contact Support before implementing any strategy you're unsure about Flatten Positions Before Switching Directions: Ensure all open positions are closed and any working orders are canceled before entering a new trade in the opposite direction.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Frequently Asked Questions Can I trade the same instrument across multiple accounts?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- What's prohibited is holding opposite positions simultaneously in a way that eliminates market risk.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Confirmed hedging violations are final and cannot be appealed.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Are hedging attempts tracked at the account level or trader level?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Hedging attempts are tracked at the Trader level.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- If a Trader received a first-time warning and acknowledged the hedging policy, subsequent hedging activity in any newly purchased account is treated as a post-acknowledgment violation. ​ Are Practice Accounts included in Hedging Alerts?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Practice Accounts are not included in Hedging detection.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- If a hedging violation is not resolved within the warning window, positions will be automatically liquidated, and accounts flagged.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- However, first-time violations are treated as warnings with a brief window to un-hedge, as described in our enforcement policy above.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Will a hedging warning affect my payout request?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- … 25 más en inventario.json

## bots_y_automatizacion (filtro)

- Can I use automated trading strategies?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Topstep won't help set up or troubleshoot automated strategies, and no exceptions are made for errant trades or malfunctions.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Can I use automated strategies?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Authorize access through the Discord role bot.  
  <sub> · [8703714-topstep-community](https://help.topstep.com/en/articles/8703714-topstep-community)</sub>
- Useful for exit strategies and breakeven automation — especially when you don't want to babysit the position.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- Prohibited Conduct regarding Trader Profiles: Harmful, offensive, illegal, or sexual content Personal Data or misleading claims Unauthorized names, trademarks, or third-party content Advertising, scams, or attempts to evade moderation Notice that Profile Content may undergo automated screening and moderation, which may result in profile suspension or deactivation 🤝 Trading with friends & family is part of the Ultimate Trading Experience.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- If you’re here to trade, this isn’t about you. ​ Examples of exploiting or manipulating the Topstep simulator include, but are not limited to: Running scalping algorithms designed to exploit unrealistic SIM fills Making hundreds of rapid trades to take advantage of preferential queue position in SIM Initiating reckless trades in gapped markets to profit from stray fills — these are improbable in live markets Repeatedly exploiting the relative lack of slippage in SIM to achieve impossible stop-loss execution Using tight brackets or auto-breakeven to take advantage of favorable SIM fills 👉 If this doesn't sound like you, it probably isn't.  
  <sub> · [10305426-prohibited-trading-strategies-at-topstep](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep)</sub>
- Can I use automated strategies in my LFA?  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- The API Gateway is built for the simulated environment and isn't available on Live, so automated strategies are not possible at this time in the Live Funded Account.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Updated over a week ago Table of contents TopstepX™ API Access lets advanced Traders and developers build automated strategies, connect third-party tools, and execute trades directly through TopstepX.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- What You Can Do With API Access Build and run automated trading strategies Connect third-party tools and platforms Create custom risk management rules Pull live and historical market data Execute trades directly through your TopstepX account Who It's For Traders and developers comfortable coding in Python, Java, .NET, JavaScript, or similar languages who want to work with REST and WebSocket APIs.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- Running automation on a VPS can result in account suspension or removal from the program.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- You may still use your own private server for supporting work that doesn't touch order flow: Allowed on a private server Not allowed on a private server Historical data storage Placing, modifying, or cancelling orders Research and backtesting Any automated trigger that can reach the order endpoints Logging and analytics Routing or relaying orders on your behalf A read-only dashboard Receiving copies of your own fills, positions, and P&L The line is order transmission: your server can watch and record, but it cannot trade.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- A rule violation is treated the same whether it originates from manual trading or third-party automation.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- Can I build and use my own custom trading bot with the TopstepX / ProjectX API?  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- Custom automated strategies and bots are allowed via the TopstepX / ProjectX API, subject to standard platform rules and our prohibition on highfrequency trading (HFT).  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- You remain the owner of your bot and are solely responsible for its design, performance, and behavior — including making sure it operates within all applicable rules.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- Velocity Logic protects the matching engine and market structure by preventing: Runaway algorithms from clearing the book Liquidity vacuums are causing unrealistic price moves Stop-loss cascades driven by an empty order book Short-term mechanical instability Velocity Logic vs.  
  <sub> · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- When Velocity Logic Events Typically Occur Overnight or low-liquidity sessions Algorithmic malfunctions Stop cascades after sudden book thinning Data feed or quote disruptions 👉 Velocity Logic events rarely occur during high-participation periods.  
  <sub> · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- But you're still fully responsible for all activity across your accounts, including anything created by automated systems or third-party tools.  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Contracts are automatically rolled over during the daily market close window (4:00 PM – 5:00 PM CST) based on an internal algorithm to determine the optimal time to roll active contracts prior to the next trading day based on volume, open interest, and expiration dates.  
  <sub>4:00, 5:00 · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- General Troubleshooting If you’re experiencing latency or slow performance: Lower your Data Speed (Slow or Medium Recommended) Remove indicators and add them back one at a time Reduce the number of active indicators If you’re on mobile, try using another device such as a laptop or desktop Try another browser or incognito mode Clear your Cache and Cookies Use a website to check your connection quality (not speed test) to USA based servers. ⚡️ TopstepX uses real-time exchange data with no artificial delay.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Topstep may apply automated screening, human review, or both to Profile Content, at any time and including after Profile Content has been published.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Other prohibited uses You are solely responsible for any and all acts and omissions that occur under your Account, and you agree not to engage in unacceptable use of the Sites or Services or any User Content including: Posting, storing, or disseminating any unsolicited or unauthorized advertising, promotional materials, junk mail, spam, chain letters or other fraudulent schemes, or any other form of solicitation; Using any manual or automated software, devices, or other processes to “crawl” or “spider” any web pages contained in the Sites or Services; Using any VPN or VPS on Accounts is strictly prohibited and may result in account termination and forfeiture of profits.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>

## martingala_y_promediar (filtro)

- Cannonball — Adding to a losing position as it goes against you.  
  <sub> · [8284101-topstep-learning](https://help.topstep.com/en/articles/8284101-topstep-learning)</sub>
- Moron Trade: Adding to a losing position - putting "more-on" Naked Point of Control (NPOC): A previous volume point of control that has not been re-tested during regular trading hours.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>

## cuentas_maximas (filtro)

- If you have multiple accounts, double-check which one you're trading on before you start.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- You can also use a trade copier to duplicate trades across multiple accounts.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Yes, up to the 5-account limit, unless you're on the Focused Trader Plan (FTP) .  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Never risk more than you're willing to lose. ☝️ Slippage Can Affect Your Account Limits Slippage can push your fill beyond your stop level.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- You might end up here if you: Hit the Maximum Loss Limit on multiple accounts in 1 day Max position the majority of your trades Let losers run bigger than winners Trade without stops Go full port, trade on tilt, FOMO, or revenge Disrespect your daily limits Can't trade small?  
  <sub>1 day · [10406542-what-is-responsible-trading](https://help.topstep.com/en/articles/10406542-what-is-responsible-trading)</sub>
- Details of the Focused Trader Program: Corrective Path Slowdown Path Account limit 1 active $50K account at a time (Trading Combine, XFA, or LFA) Current active accounts can remain open but limited to 1 active $50K account at a time (Trading Combine, XFA, or LFA) once closed.  
  <sub>$50K, $50K · [10551016-what-is-the-focused-trader-program](https://help.topstep.com/en/articles/10551016-what-is-the-focused-trader-program)</sub>
- Time requirement 6 months None To request a review from the Risk Team 6 months of consistent trading + $10K net LFA profits, or good trading behavior $10K net LFA profits or good trading behavior 👉 For both paths, Risk Team review does not guarantee approval to rejoin the regular program or purchase multiple accounts.  
  <sub>$10K, $10K · [10551016-what-is-the-focused-trader-program](https://help.topstep.com/en/articles/10551016-what-is-the-focused-trader-program)</sub>
- Tip: You can duplicate trades across multiple accounts using a trade copier.  
  <sub> · [10657969-live-funded-account-parameters](https://help.topstep.com/en/articles/10657969-live-funded-account-parameters)</sub>
- Can I use 1 subscription across multiple accounts?  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- The eligible XFA does not count toward your 5-account limit during the 30-day window.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- It's not a punishment — it's a structured path to rebuild discipline, consistency, and sound risk management. ​ This program gets you back on track — building the discipline and habits needed to trade responsibly in Live markets. 👉 You may need the Responsible Trading Program if: Multiple accounts hit the Maximum Loss Limit in one day You max position a majority of your trades You don’t keep losers smaller than winners You don’t use stops You go full port or trade on tilt, FOMO, or revenge You disrespect your daily limits Can't trade small?  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- Cross-account hedging means simultaneously going long and short the same or correlated instrument across multiple accounts — such as MES/ES, MNQ/NQ. ☝️ Simple Example: Express Funded Account (Account A): Long 5 contracts of ES Trading Combine (Account B): Short 5 contracts of ES When positions are hedged across accounts, you're protected from market risk — if the market moves up, Account A profits while Account B loses, and vice versa.  
  <sub>5 contracts, 5 contracts · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- Frequently Asked Questions Can I trade the same instrument across multiple accounts?  
  <sub> · [13747047-understanding-hedging](https://help.topstep.com/en/articles/13747047-understanding-hedging)</sub>
- A single Shoulder Tap Express Funded Account Balance reflects your remaining Live capital Follows standard XFA parameters and Payout Policy You are limited to 1 Shoulder Tap XFA — no multiple accounts Can I move back to Live?  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Can I trade multiple accounts while in a Shoulder Tap?  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Trade Copier Trade Copier The Trade Copier lets you mirror trades from a Lead account to 1 or more Follower accounts automatically — so you can run the same strategy across multiple accounts without placing every order manually.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- For the $250K Re-release, you may purchase up to 5 accounts.  
  <sub>$250K, 5 accounts · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- The 5 account limit on $6K Challenges still applies.  
  <sub>5 account, $6K · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- You may purchase up to 5 accounts total.  
  <sub>5 accounts · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Copy promo codes for multiple purposes or for multiple accounts Notwithstanding the foregoing list, a Code Owner (as defined in Section 29) is permitted to share their Referral Code (as defined in Section 29) solely for the purposes of, and in the specific manner contemplated by,Topstep’s Trader Referral Discount Code program described in Section 29.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If Topstep determines in its sole and absolute discretion you have opened multiple Accounts, Topstep reserves the right to suspend or terminate your Account and subsequently created Accounts.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>

## discrecional_firma (filtro)

- Exploiting platform deficiencies — using instruments or methods that misuse bugs, errors, or deficiencies in the platform Circumventing geographical or technical restrictions Holding a position within 2% of a product’s price lock limit — see How to Ensure I Am Not Trading Within 2% of a Price Limit Trading on behalf of others — including sharing incentives as part of any business arrangement Account stacking — repeatedly hitting the Maximum Loss Limit in one account and switching to another to repeat high-risk attempts Any other conduct that Topstep determines, at its sole discretion, is uncommercial, games the market, is not a viable strategy, or is not responsible trading Do not use a VPN.  
  <sub>2%, 2% · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- While warnings will often be sent out first, Topstep reserves the right to send Traders directly to RTP based on the severity of the violation.  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- Instead, the Risk Team looks for recurring patterns over time, including: Significant drawdown of seeded capital (excluding profits and bonuses) Patterns of YOLO behavior or lack of discipline, including but not limited to: Repeatedly hitting the Daily Loss Limit Activity that resembles gambling rather than disciplined trading Inconsistent performance with a risk/reward imbalance — daily losses far exceeding typical wins.  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Our goal is to help traders make the most of the opportunity they've earned, not gamble or take YOLO shots that put it all at risk.  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Please check back periodically to review the Terms of Use and Privacy Policy , as we reserve the right to modify or change these Terms after providing notice to you.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- The form of such notice is at our discretion and may include, without limitation, clear and conspicuous messaging or posting on the Sites or Services indicating the Terms of Use has been changed.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We may, in our sole discretion, elect to suspend or terminate access to, or use of, the Topstep Products and Content by anyone who violates these Terms, including but not limited to failure to pay any required Fee.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- “Topstep Labs” means the Topstep program under which Topstep may offer Services on a limited-release, experimental basis, from time to time and in its sole discretion.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If you do not pay or cause Topstep not to be paid any Fee or portion of a Fee that is due (including by disputing, reversing, or terminating your payment for a Fee), then Topstep may, at its sole discretion, suspend or terminate your access to any Services with or without notice.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- In furtherance of Topstep’s ethos of promoting responsible trading behavior, if you place an unusually large number of orders for the Services within an unreasonably short period of time, as determined in the sole discretion of Topstep, we reserve the right to suspend any further orders of the Services by you.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If we identify that the unusual behavior relates to the User’s involvement in Prohibited Conduct (see Section 27), we reserve the right to determine, at our sole discretion, the nature of the behavior described and reasonable consequences, including, without limitation, the immediate termination of your access to the Sites and Services.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep aims to provide a safe environment for Users to engage in Simulated Trading, as well as other trading or programs offered by Topstep, and reserves the right to take any action it deems prudent to deter any use for engaging in irresponsible behavior or other actions which Topstep, in its sole discretion, deems in conflict with its mission and values.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We reserve the right to limit the availability of the Topstep Products and Content, materials, or other items described or offered thereon to any person, geographic area, or jurisdiction we so desire, at any time and in our sole discretion, and to limit the quantities of any such services, materials, or other item provided.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- The Sites or Services may be inaccessible or inoperable for any reason, including, without limitation: (a) equipment malfunctions, (b) periodic maintenance procedures or repairs which we may undertake from time to time, or (c) causes beyond the control of Topstep or which are not foreseeable by Topstep.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We reserve the right to delete or edit User Content, in whole or in part, in our sole discretion at any time and without notice.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right to determine, at its own discretion, whether certain trades, practices, strategies, or situations are Prohibited Conduct.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- In order to graduate from the Trading Combine®, a User has to meet all profit targets, following applicable Trading Rules (defined in Section 27) and account parameters applicable to User’s Account for the applicable Trading Combine®, which remain subject to adjustment and change from time to time, without notice, and with a current schedule of Trading Rules and account parameters detailed here .  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If you are successful in graduating from the Trading Combine®, you will be offered the opportunity to get funded with the trading capital of TopstepFunded or advance to another product or service offered by Topstep (pursuant to Topstep’s sole discretion), either of which shall be governed pursuant to separate or supplemental written agreement.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- TOPSTEP HAS NO OBLIGATION TO UPDATE ANY CONTENT ON OUR SITES OR SERVICES AND MAY CHANGE OR UPDATE OUR SITES OR SERVICES AT ANY TIME WITHOUT NOTICE.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right to modify, change, replace, add, or remove any elements and functions of the Sites and/or Services at any time without any compensation.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Prices and availability of services are subject to change without notice.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Errors will be corrected where discovered, and Topstep reserves the right to revoke any stated offer and to correct any errors, inaccuracies, or omissions including after an Order has been submitted and whether or not the Order has been confirmed and your payment method accepted and charged.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Promo code usage From time to time, and at Topstep’s sole discretion, Topstep may provide you the ability to access, use, or receive promo codes.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We reserve the right to modify, suspend, impose conditions on or cancel offers for promo codes at any time without notice.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We reserve the right to revoke your permission to link to our Sites or Services at any time and for any reason.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If Topstep determines in its sole and absolute discretion you have opened multiple Accounts, Topstep reserves the right to suspend or terminate your Account and subsequently created Accounts.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right to refuse to grant User Credentials to any individual for any reason, including if such User impersonates someone else, is protected by trademark or other proprietary rights law, or is vulgar or offensive.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We may make User Content available through other Sites and Users, or otherwise publicly available, in our sole discretion.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right, in its sole discretion, to reject, reset, modify, remove, or unpublish any Profile Content, and to suspend or deactivate a Trader Profile, with or without notice and without compensation or refund.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right to refuse to permit or to terminate your access to any of the Topstep Sites or Services at any time at its sole discretion.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Such termination may result from a violation of the Terms or other referenced agreements, unauthorized use or reproduction of any publication or information, nonpayment of any Fee or portion of a Fee, or any or no reason, all determined in Topstep’s sole discretion.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right, at your expense, to assume the exclusive defense and control of any matter for which you are required to indemnify us, and you agree to cooperate with our defense of these claims.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- User acknowledges and agrees that User is solely responsible for staying current on Trading Rules, which remain subject to change at any time and from time to time, with or without notice.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If Topstep, in its sole discretion, determines a User has violated any Trading Rules, failed to supply accurate and complete information requested by Topstep, or engaged in Prohibited Conduct, Topstep may, in its sole determination, remove any Simulated Account profits, delete a trading day, reset an Account, or ban a User from any further use of the Site and Services.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If Topstep identifies trading activity that, in its sole discretion, relates to Prohibited Conduct, Topstep reserves the right to, in its sole discretion, delete the trading day and all profits, or restart or close the Account.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Rewards are personal to a given User and are non-transferrable for any reason.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Any redemption of a Reward is final and nonrefundable for any reason.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep may prohibit any User or potential User from participating in a given Reward, if, at the sole discretion of Topstep, (i) such person shows a disregard for or breaches these Terms, (ii) acts with an intent to annoy, abuse, threaten, or harass any other User, Topstep, or its agents or representatives, (iii) disparages Topstep or its products or services, Topstep’s competitors or their products or services, Topstep Affiliates or any other person or party affiliated with Topstep, or (iv) acts in any other disruptive manner.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep’s decisions, in its sole discretion, as to all matters related to Rewards are final.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep reserves the right to deny, revoke, or claw back any Reward or Referral Code redemption that it determines, in its sole discretion, to be fraudulent, abusive, self-referred, generated using multiple or improperly held Accounts, or not the result of a bona fide first-time Trading Combine purchase.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We reserve the right at any time in our sole discretion to: modify, suspend, or discontinue our Sites or Services or any service, content, feature, or product offered through our Sites or Services, with or without notice; charge fees in connection with the use of our Sites and Services; modify and/or waive any fees charged in connection with our Sites or Services; and/or offer opportunities to some or all users of our Sites or Services.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- We may terminate these Terms at any time without notice, and accordingly may deny you access to our Sites and Services, if in our sole judgment you fail to comply with any term or provision of these Terms.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- If there is ever a conflict between the two, these rules take precedence. ​ Topstep reserves the right to update these rules at any time, with or without notice. ​ You must follow all rules outlined here or in any other communication from Topstep. ​ Payout eligibility and the processing of payouts are governed by these rules and the terms of the Agreement. ​ By trading in your Live Funded Account following any update to these rules, you confirm that you have read, understand and agree to the most current version of these rules.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Topstep reserves the right to update these rules at any time, with or without prior notice.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Topstep reserves the right to close your positions or disable your account at any time, with or without notice.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Topstep reserves the right to modify or discontinue Back2Funded at any time.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Topstep reserves the right to modify or terminate this offer at any time, with or without prior notice, at its sole discretion.  
  <sub> · [double-payout-caps-terms-conditions](https://www.topstep.com/double-payout-caps-terms-conditions)</sub>
- All terms and conditions are subject to change at Topstep’s sole discretion.  
  <sub> · [double-payout-caps-terms-conditions](https://www.topstep.com/double-payout-caps-terms-conditions)</sub>

## kyc_y_jurisdiccion (filtro)

- OFAC sanctions and partner restrictions apply.  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- Requirements No US citizenship required Minimum age: 18 Citizens or residents of OFAC-sanctioned or partner-restricted countries are not eligible to trade, earn funding, or receive payouts Countries Eligible for an XFA — Not LFA These Traders can join Topstep, trade and pass the Trading Combine, earn Express Funded Accounts, and take up to $200,000 in total payouts.  
  <sub>$200,000 · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- A country may be deemed ineligible for several reasons, including, but not limited to, OFAC sanctions and restrictions with our partners.  
  <sub> · [8284116-am-i-eligible-to-trade-with-topstep](https://help.topstep.com/en/articles/8284116-am-i-eligible-to-trade-with-topstep)</sub>
- Clear any pre-populated fields and retype them manually Try completing the agreement on a mobile device — many Traders have better results there How to Purchase Level 2 Data Go to the Accounts tab in your Topstep Dashboard.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Mobile data can cause IP address changes.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Update and restart Restart your device regularly.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Check device specs Component Minimum Recommended RAM 8GB 16GB Processor 4–6 core (i5) i7, i9, or M1 Storage 250GB SSD 250GB+ SSD Switch from tick charts to time-based charts Tick charts are resource-intensive.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Federal Open Market Committee (FOMC): The Federal Open Market Committee (FOMC) consists of twelve members--the seven members of the Board of Governors of the Federal Reserve System; the president of the Federal Reserve Bank of New York; and four of the remaining eleven Reserve Bank presidents, who serve one-year terms on a rotating basis.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- Exploiting platform deficiencies — using instruments or methods that misuse bugs, errors, or deficiencies in the platform Circumventing geographical or technical restrictions Holding a position within 2% of a product’s price lock limit — see How to Ensure I Am Not Trading Within 2% of a Price Limit Trading on behalf of others — including sharing incentives as part of any business arrangement Account stacking — repeatedly hitting the Maximum Loss Limit in one account and switching to another to repeat high-risk attempts Any other conduct that Topstep determines, at its sole discretion, is uncommercial, games the market, is not a viable strategy, or is not responsible trading Do not use a VPN.  
  <sub>2%, 2% · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- VPNs, proxy services, TOR, geo-location obfuscation, and other identity-masking services are not permitted at Topstep.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- If you see an Error 403 Forbidden message, disable your VPN or proxy and try again.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- Topstep conducts IDV (Identity Verification) checks on all Traders.  
  <sub> · [10296582-prohibited-conduct](https://help.topstep.com/en/articles/10296582-prohibited-conduct)</sub>
- VPNs, VPS, and Remote Servers All trading activity must originate from your personal device.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- The use of VPS, VPNs, and remote servers is prohibited by Topstep's Terms of Use.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- How Identity Verification Works | Topstep Help Center Copyright 2023.  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- All Collections Getting Started How Identity Verification Works How Identity Verification Works One-time.  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- When Is Identity Verification Required?  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- What You Need A valid, unexpired original physical government-issued ID: Passport, Driver's License, or National ID card A device with a camera (phone or computer) Not accepted: photocopies, images displayed on another screen, or IDs with sticky notes or coverings.  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- How to Complete Identity Verification Prepare your unexpired, physical ID Open the secure link or QR code from your email Take clear photos of your ID (front and back where applicable) Take a selfie Submit Once complete, your account status updates to Verification Complete .  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- Troubleshooting If you're having issues: Try a different browser (Chrome, Safari) or a different device Clear your browser's cache and cookies, then restart your device Make sure camera and microphone access are enabled Confirm your ID is unexpired and a physical document (not a photocopy) Resubmit using the secure link or QR code from your email Avoid using VPNs or VPS — location discrepancies can cause verification issues Ensure your device's time zone and location settings are accurate FAQ Why am I being asked to verify again?  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- Can I trade while waiting to complete Identity Verification?  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- If, after attempting to complete the identity verification process, you see a banner that says your account is fully locked and to contact Trader Support, please reach out here Related Articles General Platform Troubleshooting New to Topstep?  
  <sub> · [12578731-how-identity-verification-works](https://help.topstep.com/en/articles/12578731-how-identity-verification-works)</sub>
- Browser checks — clear cache and cookies, try a private/incognito window, disable VPNs and ad blockers, or try a different browser/device.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Concurrent Sessions Limit Concurrent Sessions Limit Exchange regulations limit your access to one concurrent user session across all devices (PC, mobile, etc.).  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Logging into a new device will automatically disconnect your previous session.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Note: You can open multiple browser windows or tabs simultaneously, provided they are all running on the same device and using the same browser version.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- There is no limit to the number of windows you can have open at once. 👉 Important: Exchange rules limit you to 1 device/browser at a time — you cannot have it open simultaneously on a PC and a phone, on two different computers, or on two different browsers (like Chrome and Edge) at the same time.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Desktop settings carry over to mobile if audio is enabled on your device.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- General Troubleshooting If you’re experiencing latency or slow performance: Lower your Data Speed (Slow or Medium Recommended) Remove indicators and add them back one at a time Reduce the number of active indicators If you’re on mobile, try using another device such as a laptop or desktop Try another browser or incognito mode Clear your Cache and Cookies Use a website to check your connection quality (not speed test) to USA based servers. ⚡️ TopstepX uses real-time exchange data with no artificial delay.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Mobile Devices TopstepX is mobile-friendly and can be accessed through your phone’s web browser, allowing you to manage trades and monitor the market on the go.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- A blue-outlined dot shows it's active to move Order types on mobile charts — Market, Limit, Stop, and Trailing Stop, all accessible from the same " " button 🛜 Important: Because mobile performance depends on your device, Wi-Fi, and data provider, we’re unable to troubleshoot mobile-specific issues that may be related to connectivity.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Notifications are set up per device These are per computer.  
  <sub> · [16948328-topstepx-price-alerts](https://help.topstep.com/en/articles/16948328-topstepx-price-alerts)</sub>
- Delivery depends on your device, browser, operating system, and connection, and can be delayed or missed.  
  <sub> · [16948328-topstepx-price-alerts](https://help.topstep.com/en/articles/16948328-topstepx-price-alerts)</sub>
- Topstep complies with all applicable economic sanctions laws and regulations administered by U.S.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- By using Topstep Products and Content, you represent and warrant that (a) you are not designated on any U.S. government list of prohibited or restricted persons, including the SDN list, (b) you are not located in, ordinarily resident in, or accessing Topstep Products and Content from any country or region subject to comprehensive U.S. sanctions (including, but not limited to, Cuba, Iran, North Korea, Syria, or the Crimea, Donetsk, or Luhansk regions of Ukraine), and (c) you are not acting on behalf of, employed by, or affiliated with any sanctioned government, entity, or individual.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Other prohibited uses You are solely responsible for any and all acts and omissions that occur under your Account, and you agree not to engage in unacceptable use of the Sites or Services or any User Content including: Posting, storing, or disseminating any unsolicited or unauthorized advertising, promotional materials, junk mail, spam, chain letters or other fraudulent schemes, or any other form of solicitation; Using any manual or automated software, devices, or other processes to “crawl” or “spider” any web pages contained in the Sites or Services; Using any VPN or VPS on Accounts is strictly prohibited and may result in account termination and forfeiture of profits.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- These restrictions apply to all individuals residing in Live Restricted Jurisdictions (each, a “Restricted Participant”).  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- A current list of Live Restricted Jurisdictions is maintained by Topstep and may be updated from time to time.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>

## cuota (costo)

- It requires a monthly subscription.  
  <sub> · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- No monthly subscription required.  
  <sub> · [8284099-topstep-program-overview](https://help.topstep.com/en/articles/8284099-topstep-program-overview)</sub>
- Accidentally Left Subscription On / Forgot to Cancel Your Trading Combine® is a monthly subscription that Rebills approximately every 30 days until you pass or cancel.  
  <sub>30 days · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Managing your subscription is your responsibility.  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Manage your subscription at dashboard.topstep.com .  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Processing a refund will result in the immediate cancellation of your subscription, closure of the associated Trading Combine, and removal of the associated Reset credit. ☝️ Rebill refund requests are handled in chat.  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- The subscription payment was required to keep your account active through to funding.  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Once you earn funding, the subscription and all fees are considered used in full.  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- An unjustified chargeback is filing a dispute without a valid reason — for example: Forgetting to cancel a subscription Misunderstanding a charge Overlooking Topstep’s refund policies Attempting to bypass the standard refund process What Happens If You File a Chargeback?  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies) +1</sub>
- Related Articles Trading Combine Subscriptions What is a Reset?  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies) +1</sub>
- Level 2 (Depth of Market) is available as an upgrade for $38/month.  
  <sub>$38 · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Level 2 Data Level 1 (Top of Book) Level 2 (Depth of Market) What you see Best bid and best ask 5–10 best bids and asks Use case Chart trading DOM / Matrix trading Cost Free (Topstep covers it) $38/month The CME requires payment for all market data on simulated accounts.  
  <sub>$38 · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Level 2 requires an upgrade at $38/month.  
  <sub>$38 · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- An active Level 2 subscription applies to all Trading Combines® under the same username.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Trading Combine Subscriptions | Topstep Help Center Copyright 2023.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- All Collections Topstep Program Trading Combine® Trading Combine Subscriptions Trading Combine Subscriptions Auto-renews monthly and banks a Reset Credit with every Rebill.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Updated over 3 weeks ago Table of contents The Basics The Trading Combine® is a monthly subscription.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Check your Rebill date and manage your subscription from your Topstep Dashboard .  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Trading Combine Subscription FAQs What does the Trading Combine cost?  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Billing page → click " X " next to the subscription → confirm .  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- You also can't purchase a Reset on that subscription after it's canceled.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- The subscription does not cancel — it keeps rebilling, and you can still trade for practice.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- What happens if my subscription renewal payment fails?  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- If a renewal payment fails, your subscription enters a retry period.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- The system will automatically attempt to process the charge two more times before the subscription is canceled.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- If you add a new card due to a failed renewal, please remember to update the affected subscription with your new card under the Subscriptions section of your Billing tab. ​ During this retry period, account Resets are temporarily disabled for that subscription.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Resets will become available again as soon as your subscription payment successfully processes.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Important: Subscription renewals process early on your rebill date.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Subscriptions can't be paused or put on hold.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- What happens to my subscription after I pass?  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- The subscription tied to the passed Trading Combine will auto-cancel, and the account will close.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Check your Billing page for any other active Trading Combine subscriptions that haven't been passed yet.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- When your Trading Combine is marked as Passed, the subscription for that account is automatically canceled.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- However, once a subscription is canceled, you can't Reset that specific account anymore.  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Can I reactivate a canceled subscription?  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Reset it now — or wait for a Reset Credit at your next Rebill. ✌️ Reset your active Trading Combine subscription any time.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Reset Credits stay on your profile, even if you cancel the associated subscription.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Rules: Tied to a specific account size AND type (Standard, No Activation Fee, or DLL) Credits issued before 12/11/2025 — no expiration Credits issued on or after 12/11/2025 — expire 1 year after added Can't transfer between types or sizes Can't combine (two 50K credits can't Reset a 100K) Can't use credits to buy a new Trading Combine — only on an existing active subscription Oldest matching credit will be used first Reset FAQs What does a Reset cost?  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Resets only work on active Trading Combine subscriptions.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Resets are for active Trading Combine subscriptions.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Related Articles Trading Combine Subscriptions New to Topstep?  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- July 28, 2026 Table of contents The Practice Account is a free 150K simulated account available to any Trader with an active Trading Combine subscription.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- In order to have a Practice Account, you must have an active Trading Combine subscription.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- If your subscription is canceled or you only have an Express Funded Account, the Practice Account add-on will not work.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- If your Trading Combine subscription is already canceled and your Practice Account shows as Ineligible, the Unsubscribe button may not be available.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- As long as you have an active Trading Combine subscription.  
  <sub> · [8284134-practice-account](https://help.topstep.com/en/articles/8284134-practice-account)</sub>
- Internet instability is outside Topstep’s control and responsibility. 💻 Login Issues Confirm your subscription is active.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Inactive subscription — A cancelled or past-due subscription can trigger rejected orders or error messages.  
  <sub> · [8284136-general-platform-troubleshooting](https://help.topstep.com/en/articles/8284136-general-platform-troubleshooting)</sub>
- Do I need to purchase a data subscription?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- When a 50K, 100K, or 150K Trading Combine® (account prefix: 50KTC, 100KTC, or 150KTC) passes, the account closes and the subscription is canceled.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- See What is a Trade Copier? 📚 If you're new to Topstep or the Trading Combine, reading the following resources will enhance your experience: Trading Combine Subscriptions What is the Reset?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Prohibited Conduct Prohibited Trading Strategies Maximum Loss Limit Daily Loss Limit Consistency Target Permitted Products and Trading Hours Related Articles Trading Combine Subscriptions When and What Products Can I Trade?  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- The goal is the Live Funded Account ® — real capital, no Payout caps, and unlimited earning potential. ​ How to Get Started Create your Topstep account at dashboard.topstep.com ​ Choose your account size: 50K , 100K , or 150K Enter your payment info to start your monthly subscription Check your email for your account credentials Single-profile policy: Topstep allows one profile per Trader.  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- Learn more here: Topstep Community and Topstep Learning Key Links Topstep Program Overview Trading Combine® Parameters Trading Combine Subscription Express Funded Account® Parameters Live Funded Account® Parameters Payout Policy Prohibited Conduct Related Articles Am I Eligible to Trade with Topstep?  
  <sub> · [8284199-new-to-topstep-start-here](https://help.topstep.com/en/articles/8284199-new-to-topstep-start-here)</sub>
- No monthly subscription fee after passing.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Do I need a data subscription?  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Depending on the subscription path you chose, there may or may not be an activation fee.  
  <sub> · [8284217-express-funded-account-activation](https://help.topstep.com/en/articles/8284217-express-funded-account-activation)</sub>
- Default: CME data covered Takes effect at your next billing cycle If you want a different exchange covered: contact the Live Accounts & Funding Team Fees for additional exchanges still apply and are billed on the 26th of each month Data fee: $133 per exchange, per month Exchange Products Covered CME ES, MES, NQ, MNQ, RTY, M2K, NKD, 6A, 6B, 6C, 6E, 6J, 6S, E7, HE, LE, GE NYMEX CL, QM, NG, QG COMEX GC, SI, HG CBOT ZC, ZW, ZS, ZM, ZL, YM, MYM, ZT, ZF, ZN, ZB, UB, TN To trade all permitted products in the LFA, you'd need all 4 exchanges = $540/month total.  
  <sub>$133, $540 · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- With 1 exchange covered by Topstep, you're at $399/month out of pocket for all 4.  
  <sub>$399 · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- How to reduce data costs: Start with 1 exchange subscription (Topstep covers it — you pay $0 for that exchange) Add more exchanges as your account grows Start your LFA on the 1st of the month — the exchange does not pro-rate data fees (no partial months) ☝️ Important: If you want to start on the 1st, still make your initial data payment during onboarding.  
  <sub>$0 · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- … 30 más en inventario.json

## activacion_y_reset (costo)

- Activation Fee No refunds on Activation Fee purchases, including accidental activations.  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Back2Funded No refunds on Back2Funded purchases, including accidental reactivations.  
  <sub> · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Can I reactivate a canceled subscription?  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- Rules: Tied to a specific account size AND type (Standard, No Activation Fee, or DLL) Credits issued before 12/11/2025 — no expiration Credits issued on or after 12/11/2025 — expire 1 year after added Can't transfer between types or sizes Can't combine (two 50K credits can't Reset a 100K) Can't use credits to buy a new Trading Combine — only on an existing active subscription Oldest matching credit will be used first Reset FAQs What does a Reset cost?  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- You can Reset your account in the Topstep Dashboard or the TopstepX platform once your Trading Combine breaches the Maximum Loss Limit.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- Back2Funded reactivates a lost Express Funded Account for a fee.  
  <sub> · [8284128-what-is-a-reset](https://help.topstep.com/en/articles/8284128-what-is-a-reset)</sub>
- You can pay the Activation Fee immediately, but your XFA won't be available to trade until markets reopen at 5 PM CT Sunday.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- When you Reactivate using Back2Funded , your account restarts completely.  
  <sub> · [8284204-what-is-the-maximum-loss-limit](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit)</sub>
- Back2Funded lets you reactivate up to 2 times at the same size and Payout policy.  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- A one-time Activation Fee applies per XFA (Unless you chose the No Activation Fee Trading Combine).  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Minutes after paying the Activation Fee .  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- Depending on the subscription path you chose, there may or may not be an activation fee.  
  <sub> · [8284217-express-funded-account-activation](https://help.topstep.com/en/articles/8284217-express-funded-account-activation)</sub>
- Activation Fee Path Fee Standard Path $149 one-time activation fee per XFA No Activation Fee Path No activation fee ⚠️ It's your responsibility to confirm you're activating the correct account.  
  <sub>$149 · [8284217-express-funded-account-activation](https://help.topstep.com/en/articles/8284217-express-funded-account-activation)</sub>
- Click "Agree and Continue." ​ Activation Fee: No Activation Fee path: Click Continue — your account is created!  
  <sub> · [8284217-express-funded-account-activation](https://help.topstep.com/en/articles/8284217-express-funded-account-activation)</sub>
- If I add a DLL at checkout during Express Funded Account activation or Reactivation, will I still get the increased Payout cap?  
  <sub> · [8284233-topstep-payout-policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy)</sub>
- Set It at Purchase You now have the option to add a Daily Loss Limit at checkout when purchasing a Trading Combine or activating/Reactivating an Express Funded Account.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Responsible Trading Discount There's now a Responsible Trading Discount when you add a DLL at purchase for No Activation Fee Trading Combines and Back2Funded Reactivations.  
  <sub> · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- No Activation Fee Trading Combine Back2Funded Reactivation $10 off → 50K $20 off → 100K $30 off → 150K $50 off Reactivation Fees ⏰ Limited Time Offering: Add a Daily Loss Limit at checkout in the Trading Combine, and increase your Payout Cap once you pass and activate an Express Funded Account.  
  <sub>$10, $20, $30, $50 · [10490293-daily-loss-limit-in-the-trading-combine-and-express](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account)</sub>
- Credits are tied to a specific account size and path (Standard, Daily Loss Limit, or No Activation Fee) and expire 1 year after issue. 👉 Your Dashboard shows: how many Reset Credits you have, which sizes and paths they apply to, and expiration dates.  
  <sub> · [10513413-getting-started-with-the-topstep-dashboard](https://help.topstep.com/en/articles/10513413-getting-started-with-the-topstep-dashboard)</sub>
- August 14, 2026 Table of contents The Basics Back2Funded gives you up to 2 Reactivations per account if you lose your Express Funded Account® (XFA) before your first Payout.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- Account Size Reactivation Fee $50K XFA $599 $100K XFA $699 $150K XFA $829 New: Responsible Trading Discount for Back2Funded Select a Daily Loss Limit (DLL) at checkout when Reactivating your Express Funded Account, and receive a $50 discount. ✅ $50 off → 50K (DLL: $1,000) ✅ $50 off → 100K (DLL: $2,000) ✅ $50 off → 150K (DLL: $3,000) 👉 Discount is applied at checkout. 💰 Please note: If you added a DLL to your Trading Combine® before the Back2Funded Responsible Trading Discount launched, the $50 discount will still apply automatically when you Reactivate.  
  <sub>$50K, $599, $100K, $699, $150K, $829 · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- The DLL stays with the account for its full lifetime — Trading Combine® → Express Funded Account® → Reactivation.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- This includes accounts where the original 7-day reactivation window have already passed.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- An XFA that was eligible for Back2Funded 10 days ago will now have 20 days remaining, even though the original 7-day reactivation window expired.  
  <sub>10 days, 20 days · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- The Back2Funded option isn't showing on my dashboard If you're eligible but can't see the Back2Funded option: Hard refresh your browser (Ctrl+Shift+R on Windows / Cmd+Shift+R on Mac) Log out and log back in to the Topstep Dashboard If the option still doesn't appear, contact Trader Support — include your account number and the date your XFA was closed I paid but my account hasn't reactivated Your account becomes available at the start of the next trading session after your purchase — not immediately.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- You'll be taken through checkout to pay the Reactivation fee.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- FAQs Does the Payout policy change when I Reactivate?  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- How many times can I Reactivate?  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- Up to 2 Reactivations per Express Funded Account.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- Is a Reactivation the same as a Reset?  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- A Reactivation is Back2Funded — it applies to lost Express Funded Accounts.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- Yes — both types are eligible for Reactivation.  
  <sub> · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- If you do not Reactivate within 30 days, the Back2Funded offer expires for that account.  
  <sub>30 days · [12060405-back2funded-rules-guidelines-and-how-it-works](https://help.topstep.com/en/articles/12060405-back2funded-rules-guidelines-and-how-it-works)</sub>
- Yes, Traders in RTP can Reactivate their Express Funded Account using our Back2Funded option.  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- The Reactivated Express Funded Account account will follow RTP rules and will be created on the Consistency Path with a Daily Loss Limit, regardless of if the original account was purchased before or after RTP placement.  
  <sub> · [13620045-what-is-the-responsible-trading-program](https://help.topstep.com/en/articles/13620045-what-is-the-responsible-trading-program)</sub>
- Back2Funded Reactivation does not apply to Shoulder Tap accounts.  
  <sub> · [13747178-live-funded-account-call-up-and-call-down-process](https://help.topstep.com/en/articles/13747178-live-funded-account-call-up-and-call-down-process)</sub>
- Trading Combine Account Size Standard Path No Activation Fee Path 50K $49/month $95/month 100K $99/month $149/month 150K $199/month $229/month ⚠️ Important: Paths cannot be changed after purchase.  
  <sub>$49, $95, $99, $149, $199, $229 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- The Details: Standard Path: Lower monthly cost. $149 Activation Fee charged once per Express Funded Account (XFA) earned.  
  <sub>$149 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- No Activation Fee Path: Higher monthly cost.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Reset Pricing Account Size Standard Path No Activation Fee Path 50K $49 $95 100K $99 $149 150K $199 $229 You may purchase a Reset from your Topstep dashboard, or within the TopstepX platform once your Trading Combine breaches the Maximum Loss Limit .  
  <sub>$49, $95, $99, $149, $199, $229 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Express Funded Account Activation & Reactivation ☝️ Activation Depends on your path: Standard Path — $149, charged once per XFA earned.  
  <sub>$149, · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- No Activation Fee Path — $0. 👉 Reactivation Lost your XFA before your first Payout?  
  <sub>$0 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Reactivate through our Back2Funded option.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Reactivation fees: $50K XFA — $599 $100K XFA — $699 $150K XFA — $829 ⏳ Reactivation window: 30 calendar days from account closure.  
  <sub>$50K, $599, $100K, $699, $150K, $829 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Responsible Trading Discount 🙌 There's now a Responsible Trading Discount when you add a DLL at purchase for No Activation Fee Trading Combines, Express Funded Account Activations, and Back2Funded Reactivations. 👉 Discount is applied at checkout.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- No Activation Fee Trading Combine Back2Funded Reactivation $10 off → 50K $20 off → 100K $30 off → 150K $50 off Reactivation Fees 🔥 We reward traders who manage risk the right way.  
  <sub>$10, $20, $30, $50 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Phase 1: Trading Combine® Parameter Value Buying Power $25,000 Profit Target $2,000 Max Loss Limit $1,000 (static, non-trailing 🔥) Max Contracts 2 mini / 20 micro Consistency Target 55% Daily Loss Limit (DLL) Mandatory $500 Funded Activation Fee Free Price $75 one-time — no subscription.  
  <sub>$25,000, $2,000, $1,000, 2 mini, 20 micro, 55% · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Resets Not Available Funded Activation Fee Free!  
  <sub> · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $3,000. $3K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $3,000 $3,000 Max Loss Limit $1,000 (static, non-trailing 🔥) $1,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $3,000, paid one time.  
  <sub>$3,000, $3K, $0, $0, $3,000, $3,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $1,500. $1.5K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $1,500 $1,500 Max Loss Limit $500 (static, non-trailing 🔥) $500 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 2 micro (no minis)* 2 micro (no minis)* Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $1,500, paid one time.  
  <sub>$1,500, $1.5K, $0, $0, $1,500, $1,500 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- It isn't tied to your account balance, and there's no 90/10 split — you keep all $6,000. $6K Challenge Parameters Parameter Challenge Round Payout Round Starting Balance $0 $0 Profit Target $6,000 $6,000 Max Loss Limit $2,000 (static, non-trailing 🔥) $2,000 (static, non-trailing 🔥) Daily Loss Limit (DLL) None None Max Contracts 10 micros / 1 mini 10 micros / 1 mini Consistency Target None None Activation Fee — Free Path — Standard only Scaling Plan — None Resets None None Payout None — passing advances you to the Payout Round Fixed $6,000, paid one time.  
  <sub>$6,000, $6K, $0, $0, $6,000, $6,000 · [15520357-topstep-labs](https://help.topstep.com/en/articles/15520357-topstep-labs)</sub>
- Click the alerts icon in the top-right corner, click the settings icon, and check "Show paused alerts on chart." It is off by default. ​ Can I reactivate a paused alert?  
  <sub> · [16948328-topstepx-price-alerts](https://help.topstep.com/en/articles/16948328-topstepx-price-alerts)</sub>
- Pay the reactivation fee for your XFA size (including sales tax).  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Your account will be reactivated and ready to trade at the start of the next trading session.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Once you pay the reactivation fee your account will be pending until the start of the next trading session.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Expectations Each XFA can be reactivated up to 2 times.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Reactivations must be for the same size as the original XFA.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Pricing is based on the original XFA size (plus applicable sales tax): $50K Express Funded Account: $599 $100K Express Funded Account: $699 $150K Express Funded Account: $829 Each reactivation is purchased separately and is final and non-refundable.  
  <sub>$50K, $599, $100K, $699, $150K, $829 · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Reactivation window You have seven calendar days from the time your XFA is closed to decide if you want to go Back2Funded.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- Payout policy Back2Funded XFAs follow the same payout rules as the XFA you reactivated.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
- … 5 más en inventario.json

## comisiones_y_datos (costo)

- TopstepX™ — Commissions and Fees Topstep Trader Lingo Glossary Did this answer your question?  
  <sub> · [8284113-can-i-trade-forex-with-you](https://help.topstep.com/en/articles/8284113-can-i-trade-forex-with-you)</sub>
- Level 2 Depth of Market Data Depth of Market Data activates immediately upon purchase and Rebills monthly on the 28th day of the month for $38.  
  <sub>$38 · [8284117-topstep-refund-policies](https://help.topstep.com/en/articles/8284117-topstep-refund-policies)</sub>
- Level 1 and Level 2 Market Data | Topstep Help Center Copyright 2023.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- All Collections Topstep FAQs Level 1 and Level 2 Market Data Level 1 and Level 2 Market Data Level 1 is free.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- June 18, 2026 Table of contents The Basics Topstep covers Level 1 market data (Top of Book) for all 4 exchanges on Trading Combine® and Express Funded Account® (XFA) accounts at no cost.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Level 2 Data Level 1 (Top of Book) Level 2 (Depth of Market) What you see Best bid and best ask 5–10 best bids and asks Use case Chart trading DOM / Matrix trading Cost Free (Topstep covers it) $38/month The CME requires payment for all market data on simulated accounts.  
  <sub>$38 · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- The CME Market Data Agreement is a legally binding document that lets you access real-time exchange data.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- The CME charges for all market data on simulated accounts.  
  <sub> · [8284120-level-1-and-level-2-market-data](https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data)</sub>
- Related Articles Topstep® Refund Policies Level 1 and Level 2 Market Data What is a Reset?  
  <sub> · [8284121-trading-combine-subscriptions](https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions)</sub>
- This links your account to ProjectX data — a direct CME feed for faster, cleaner market data with 10:1 Micro to Mini contract conversions.  
  <sub>10:1 · [8284179-quantower-connection-instructions](https://help.topstep.com/en/articles/8284179-quantower-connection-instructions)</sub>
- See Level 1 and Level 2 Market Data for details.  
  <sub> · [8284197-trading-combine-parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)</sub>
- Trading Combine® Parameters TopstepX™ — Commissions and Fees What are the costs in the Live Funded Account?  
  <sub> · [8284206-when-and-what-products-can-i-trade](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)</sub>
- TopstepX™ — Commissions and Fees | Topstep Help Center Copyright 2023.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- All Collections TopstepX™ TopstepX™ — Commissions and Fees TopstepX™ — Commissions and Fees Every trade has a cost.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- Updated this week Table of contents TopstepX™ — Commissions & Fees These fees apply when trading the Trading Combine, Express Funded Account, and Live Funded Account.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- Commissions and fees are automatically deducted from each trade, and you'll see a breakdown in the TopstepX platform and from your Dashboard! ​ ​ Round-Turn (RT) cost: charged when you complete both sides of a trade.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- Each side (Buy or Sell) incurs half the total, also called a "per side" fee.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- Round-Turn Cost Breakdown: Exchange Fee NFA Regulatory Fee Commissions Exchange fees are set by the exchange and do not include the regulatory fee.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- Each varies by product. $0.02 round turn ($0.01 per side) Minis $1.00 round turn ($0.50 per side) Micros $.50 round turn ($0.25 per side) Example using ES & MES ES MES NFA & Regulatory Fees $0.02 $0.02 Exchange Fee $2.76 $0.70 Commissions $1.00 $0.50 Total $3.78 $1.22 Example using GC & MGC GC MGC NFA & Regulatory Fees $0.02 $0.02 Exchange Fee $3.30 $1.40 Commissions $1.00 $0.50 Total $4.32 $1.92 ⚠️ Exchange fee increase starting the October 1, 2026 trading day The CME is raising Exchange transaction fees on 2 products.  
  <sub>$0.02, $0.01, $1.00, $0.50, $0.25, $0.02 · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- Fees apply per side, so a round turn counts both entry and exit.  
  <sub> · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- MCL: $0.50 to $0.60 per side ($1.20 round turn) MNG: $0.60 to $0.70 per side ($1.40 round turn) That's $0.10 more per side.  
  <sub>$0.50, $0.60, $1.20, $0.60, $0.70, $1.40 · [8284213-topstepx-commissions-and-fees](https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees)</sub>
- See Level 1 and Level 2 Market Data .  
  <sub> · [8284215-express-funded-account-parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters)</sub>
- TopstepX™ — Commissions and Fees Daily Loss Limit in the Trading Combine and Express Funded Account Topstep Holiday Trading Hours CME Velocity Logic Did this answer your question?  
  <sub> · [8284225-staying-outside-the-2-price-limit-zone](https://help.topstep.com/en/articles/8284225-staying-outside-the-2-price-limit-zone)</sub>
- June 16, 2026 Table of contents Overview In the Live Funded Account® (LFA), you're responsible for 3 costs: Professional Market Data, round-turn commissions, and your platform license.  
  <sub> · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- CME Professional Market Data To trade live, you must subscribe to Professional Market Data from the exchanges.  
  <sub> · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- Default: CME data covered Takes effect at your next billing cycle If you want a different exchange covered: contact the Live Accounts & Funding Team Fees for additional exchanges still apply and are billed on the 26th of each month Data fee: $133 per exchange, per month Exchange Products Covered CME ES, MES, NQ, MNQ, RTY, M2K, NKD, 6A, 6B, 6C, 6E, 6J, 6S, E7, HE, LE, GE NYMEX CL, QM, NG, QG COMEX GC, SI, HG CBOT ZC, ZW, ZS, ZM, ZL, YM, MYM, ZT, ZF, ZN, ZB, UB, TN To trade all permitted products in the LFA, you'd need all 4 exchanges = $540/month total.  
  <sub>$133, $540 · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- How to reduce data costs: Start with 1 exchange subscription (Topstep covers it — you pay $0 for that exchange) Add more exchanges as your account grows Start your LFA on the 1st of the month — the exchange does not pro-rate data fees (no partial months) ☝️ Important: If you want to start on the 1st, still make your initial data payment during onboarding.  
  <sub>$0 · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- Round-Turn Costs Round-turn costs are deducted directly from your brokerage account balance.  
  <sub> · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- Commissions & Fees: $0.72–$2.04 (go to brokerages) Exchange Fees: $2.46–$4.30 (set by exchange, vary by instrument) Examples (round turn): E-mini S&P 500 (ES): $3.80 E-mini NASDAQ 100 (NQ): $3.80 Crude Oil (CL): $1.54 Gold (GC): $4.24 Full breakdown by platform and product: TopstepX™ Commissions and Fees 3.  
  <sub>$0.72, $2.04, $2.46, $4.30, $3.80, $3.80 · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- Platform License or Subscription In the Trading Combine®, Topstep covers platform fees for many supported platforms.  
  <sub> · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- Related Articles Level 1 and Level 2 Market Data Topstep Payout Policy Funded Trader Tax Questions Live Funded Account Parameters Topstep Pricing and Payment Questions Did this answer your question?  
  <sub> · [8284229-what-are-the-costs-in-the-live-funded-account](https://help.topstep.com/en/articles/8284229-what-are-the-costs-in-the-live-funded-account)</sub>
- Brokers: Intermediaries executing orders for commissions.  
  <sub> · [8570400-topstep-trader-lingo-glossary](https://help.topstep.com/en/articles/8570400-topstep-trader-lingo-glossary)</sub>
- How to Tell If Slippage Occurred Open your trade history Find the order in question Compare your intended fill price to your actual fill price Check market data around the time of the fill If the prices differ — that's slippage Slippage Mitigation Strategies Use limit orders — Limits let you set the worst price you'll accept.  
  <sub> · [8765442-order-types-fills-and-slippage](https://help.topstep.com/en/articles/8765442-order-types-fills-and-slippage)</sub>
- What You Can Do With API Access Build and run automated trading strategies Connect third-party tools and platforms Create custom risk management rules Pull live and historical market data Execute trades directly through your TopstepX account Who It's For Traders and developers comfortable coding in Python, Java, .NET, JavaScript, or similar languages who want to work with REST and WebSocket APIs.  
  <sub> · [11187768-topstepx-api-access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)</sub>
- TopstepX™ — Commissions and Fees Staying Outside the 2% Price Limit Zone Topstep Payout Policy Did this answer your question?  
  <sub>2% · [13350348-topstep-holiday-trading-hours](https://help.topstep.com/en/articles/13350348-topstep-holiday-trading-hours)</sub>
- When Velocity Logic Events Typically Occur Overnight or low-liquidity sessions Algorithmic malfunctions Stop cascades after sudden book thinning Data feed or quote disruptions 👉 Velocity Logic events rarely occur during high-participation periods.  
  <sub> · [13545889-cme-velocity-logic](https://help.topstep.com/en/articles/13545889-cme-velocity-logic)</sub>
- TopstepX™ — Commissions and Fees Topstep Labs Did this answer your question?  
  <sub> · [13613539-risk-adjustments-high-risk-high-volatility](https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility)</sub>
- Additional Pricing Information Data Fees Data Type What’s Included Cost Level 1 (Top of Book) Best bid/ask; required for chart trading Included Level 2 (DOM) Multiple bid/ask levels; required for DOM/Matrix trading $38/month Level 2 is billed on the 28th of each month and is not prorated.  
  <sub>$38 · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- To add it: Dashboard → Accounts → Add-Ons → Depth of Market Bundle. ☝ Live Funded Account® (LFA) Traders are subject to Professional Data fees.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Commissions and Fees Commissions and fees are deducted automatically from your balance with each filled trade and show up in your Net P&L.  
  <sub> · [14289835-topstep-pricing-and-payment-questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions)</sub>
- Right-click on the price axis on the right side of the chart Look for " Invert Scale " If it is checked, uncheck the option The chart should return to its normal orientation Data Feed & Connection Data Feed & Connection TopstepX pulls data straight from the exchange(s)— no third-party feed.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Data servers sit in Northern Virginia, and every Trader connects there regardless of location for market data.  
  <sub> · [14434175-topstepx](https://help.topstep.com/en/articles/14434175-topstepx)</sub>
- Commodity Futures Trading Commission.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Commodity Futures Trading Commission, or have an outstanding balance with a trading firm, you are not eligible to use the Sites or Services.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Commodity futures trading commission disclaimer CFTC RULE 4.41 – ALL HYPOTHETICAL OR SIMULATED PERFORMANCE RESULTS HAVE CERTAIN LIMITATIONS.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Securities and Exchange Commission and the U.S.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Commodity Futures Trading Commission or other securities laws and the rules of any securities exchange.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Geographical restrictions Notwithstanding anything to the contrary, if you reside in a jurisdiction where (a) Topstep does not maintain an active relationship with a futures commission merchant partner who accepts live traders resident in your country, and/or (b) Topstep determines that providing access to a live trading account would be inconsistent with internal practices to comply with applicable laws and regulations (a “Live Restricted Jurisdiction”), then the following shall apply: You may still participate in the Topstep program and complete the evaluation process.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Topstep’s decision to restrict access to live trading for Restricted Participants reflects the Company’s internal practices to comply with applicable laws and regulations, as well as the internal practices of the futures commission merchants with which Topstep works.  
  <sub> · [terms-of-use](https://www.topstep.com/terms-of-use)</sub>
- Holiday trading Holiday hours can impact your trading schedule and data fees.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Data Fees and Holidays: Data fees are not prorated for months with holiday trading restrictions.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- If you plan not to trade for the entire month, including holiday hours, and want to avoid being charged a data fee, you must email our team before the 26th of the previous month to request removal.  
  <sub> · [live-funded-account-rules](https://www.topstep.com/live-funded-account-rules)</sub>
- Fees and commissions Your Express account includes simulated fees similar to what you’d pay in a live account.  
  <sub> · [express-funded-account-rules](https://www.topstep.com/express-funded-account-rules)</sub>
