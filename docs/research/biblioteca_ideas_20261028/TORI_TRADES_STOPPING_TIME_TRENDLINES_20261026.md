# The Trend Is Your Friend Until the End: A Stopping-Time Theory of Swing Trading with Trendlines and Market Structure (Tori Trades, 2026-10-26)

Estado: REFERENCIA (fuente de ideas sin validar; no es evidencia).

The Trend Is Your Friend Until the End:
A Stopping-Time Theory of Swing Trading
with Trendlines and Market Structure

Tori Trades
Independent Research in Quantitative Finance
Working Paper · IG @tori.trades

October 26, 2026

Abstract

Swing traders follow price through its structure: higher highs and higher lows in an uptrend, lower highs and lower lows in a downtrend. They connect the swing points with trendlines, stay with the trend while the line holds, and act on a potential reversal when it breaks. This paper assembles the scientific case for that process. (i) We formalise swing pivots, structure states and pivot trendlines. We show that a close above a line through swing points is equivalent to a time-series momentum signal with an adaptive look-back, which links the method to one of the best-documented return regularities in finance. (ii) We review evidence that the building blocks of the method have measurable effects: Dow-theory market structure, support/resistance and range breakouts, order clustering that accelerates moves through broken levels, and the value of trailing exits when returns trend. (iii) We collect the probability content of trading with the trend: variance ratios, the Hurst exponent, a closed-form continuation probability 1/2 + π⁻¹ arcsin(2^{2H-1} - 1), regime probabilities, expectancy E = pW - (1-p)L, the breakeven win rate 1/(1+b), and the Kelly fraction. (iv) In an illustrative test on 91 years of U.S. market data, a mechanical swing-structure trendline rule (long while the swing trendline holds, cash after a break) won on 61% of its 97 trades with an average win about four times the average loss. It cut the maximum drawdown from 84% to 38%, and lost 3% in the 2007–2009 bear market against 50% for buy-and-hold. Across the trend-filtered rules tested, long-run returns ranged from somewhat below to roughly equal to buy-and-hold, with substantially smaller drawdowns.

1 Introduction and Background

"Cut short your losses" and "let your profits run" are two of the oldest rules in speculation, and both are statements about trends [36]. Dow theory defines a trend by its structure: successively higher highs and higher lows [51]. William Peter Hamilton applied that definition in The Wall Street Journal from 1902 to 1929 [8]. Edwards and Magee [21] and Murphy [51] made it geometric: connect the swing lows of an uptrend (or the swing highs of a downtrend) with a line, stay with the trend while price respects the line, and treat a decisive break as the signal that the trend may be reversing. Academic finance began from the opposite presumption, that prices follow a random walk and past prices carry no information [24, 25].

Six decades of evidence have moved the debate. Persistence in returns over horizons of weeks to months, known as time-series momentum, is among the best-documented regularities in asset pricing [50, 36, 42]. It is the core of the managed-futures industry. A Dow-theory re-examination found that Hamilton's structure-based calls earned positive risk-adjusted returns [8]. Support and resistance levels predict where trends pause, and the orders resting beyond them help explain why breaks are often followed by fast moves [55, 56, 39]. Trailing exits add value precisely when returns trend [38].

The traders' maxim "the trend is your friend until the end" can be stated precisely. A swing trader enters at t₀ when the structure turns up and holds while price stays above the swing trendline y(t). The "end" is the first close through that line, a stopping time

τ = inf{ t > t₀ : ln Cₜ < y(t) - δ },      position held on [t₀, τ),      (1)

at which the trader exits or reverses. The friendship is the persistence of returns before τ; the end is the evidence, at τ, that persistence has broken.

This paper connects these results to the swing trader's workflow. Section 2 reviews the evidence; Section 3 formalises swing structure and trendlines; Section 4 develops continuation probabilities, regime probabilities, expectancy and sizing; Sections 5–6 report an illustration on public data and a synthesis; Section 7 discusses practical considerations.

2 Literature Review

Efficient markets and technical rules. Early filter rules [1] did not beat buy-and-hold after costs [25], and Fama [24] set the efficient-markets benchmark. Brock, Lakonishok and LeBaron [7] then found that moving-average and trading-range-break rules (buy above a recent high, sell below a recent low) on the Dow from 1897 to 1986 produced buy-minus-sell return spreads that random-walk, AR(1), GARCH-M and EGARCH null models could not reproduce. Data-snooping corrections [61] and the survey of Park and Irwin [58] (56 positive, 20 negative and 19 mixed results in 95 studies) temper but do not erase these results. Technical indicators also forecast the U.S. equity premium out of sample as well as macroeconomic variables [52], and objective kernel-based pattern recognition finds incremental information in chart patterns [48].

Market structure, support and resistance. Hamilton's 1902–1929 Dow-theory calls earned high Sharpe ratios and positive alphas [8]. Published support and resistance levels predict intraday trend interruptions [55]. Stop-loss orders cluster just beyond them, so a break can trigger "price cascades" that explain follow-through [56, 57]. These levels coincide with peaks in order-book depth [39], levels with more prior bounces are more likely to hold [12], and stocks near their 52-week high outperform [29].

Momentum. Momentum appears across stocks [37] and across asset classes [3]. Time-series momentum, an asset's own past return predicting its future return, holds in 58 futures markets for 1–12 months and pays most in extreme markets [50]. It was consistently profitable in 67 markets back to 1880 [36], carries a drift-adjusted t-statistic near 10 since 1800 [42], and worked in both bond bull and bear markets [31]. Moving-average crossovers and time-series momentum are the same weighted sum of past returns [43]. Volatility estimation and scaling matter [5, 41], and trend returns resemble lookback straddles that profit from large moves either way [28].

Exits and stop-and-reverse. Wilder's Parabolic SAR [64] formalised the stop-and-reverse system. Stop-loss rules always lower expected return under a random walk but can raise it under momentum, and in equity data certain stop policies raised return while cutting volatility [38]. Simple trend rules dominated passive S&P 500 holding [13], and under regime switching the optimal rule is to hold while the bull-market probability is high and exit when it falls below a threshold [17].

Why trends persist. Underreaction and delayed overreaction arise from conservatism [6], overconfidence [18], slow information diffusion [34] and the disposition effect, the tendency to sell winners early and hold losers [60, 54, 26]. A rule that holds while the line holds and exits on the break is its mechanical opposite. Hedging pressure [50] and adaptive markets [45, 46] explain why trend profits persist yet vary over time.

Practitioners. The chartist canon [21, 51] and Bulkowski's statistics [9, 10, 11] sit alongside systematic trend following: the Turtles' breakout rules [23, 16, 15], Faber's 10-month model [22], multi-asset studies [14, 65], research from AQR, Man AHL and CFM [36, 31, 42], and the "crisis alpha" view [30].

3 Methodology: Swing Structure and Trendlines

Let Pₜ denote a price observed at bars t = 1, …, T, with high Hₜ, low Lₜ and log price pₜ = ln Pₜ. One-bar log returns are rₜ = pₜ - pₜ₋₁, with mean μ and standard deviation σ.

3.1 Swing pivots, structure, and the trendline rule

Definition 3.1 (Swing Pivots and Structure). A bar t is a swing high of order k if Hₜ ≥ Hₜ₊ⱼ for j = 1,…,k, and a swing low if Lₜ ≤ Lₜ₊ⱼ. A pivot is confirmed at bar t+k. Let (ℓ₁, ℓ₂) be the last two confirmed swing lows and (h₁, h₂) the last two swing highs. The structure is an uptrend if Hₕ₂ > Hₕ₁ and Lℓ₂ > Lℓ₁ (higher high, higher low). It is a downtrend if Hₕ₂ < Hₕ₁ and Lℓ₂ < Lℓ₁ (lower high, lower low).

Definition 3.2 (Swing Trendline and Stop-and-Reverse Rule). In an uptrend the support trendline passes through the last two rising swing lows, in log-price coordinates as Bulkowski recommends [10]:

y(t) = m t + b,      m = (ln Lℓ₂ - ln Lℓ₁) / (ℓ₂ - ℓ₁),      b = ln Lℓ₁ - m ℓ₁.      (2)

In a downtrend the resistance trendline passes through the last two falling swing highs. If the last two pivots do not slope in the trend's direction, the line is horizontal at the last pivot. The position sₜ ∈ {+1, -1} is held until the opposing line breaks:

sₜ = { -1   if sₜ₋₁ = +1 and ln Cₜ < y^sup(t) - δ,
       +1   if sₜ₋₁ = -1 and ln Cₜ > y^res(t) + δ,
       sₜ₋₁ otherwise,      (3) }

where δ ≥ 0 is an optional penetration filter of the kind discussed by Murphy [51]. A long/flat variant replaces -1 with 0 (cash).

Remark 3.3. A support line that no price crosses between its two pivots is an edge of the lower convex hull of {(t, ln Lₜ)}. This gives a deterministic, reproducible way to draw the lines, which we use in Section 5. Because pivots are confirmed only k bars later, the rule uses no future information.

The key observation is that the trendline rule is a momentum rule.

Proposition 3.4 (A Trendline Is an Adaptive Momentum Signal). For a trendline (2) with last pivot ℓ₂ and t > ℓ₂,

pₜ ≥ y(t)  ⇔  (pₜ - ln Lℓ₂) / (t - ℓ₂)  ≥  m.      (4)

Price holds above the line exactly when the average return since the most recent swing low is at least the trend's own slope. For a horizontal line at a swing high h (m = 0), a breakout pₜ > ln Hₕ is equivalent to a positive return rₕ,ₜ > 0 since the pivot. This is the time-series momentum sign signal of [50] with look-back t - h set by the market's own swing rhythm rather than a fixed calendar window.

Proof. Since y(ℓ₂) = ln Lℓ₂, we have y(t) = ln Lℓ₂ + m(t - ℓ₂), so pₜ ≥ y(t) is equivalent to pₜ - ln Lℓ₂ ≥ m(t - ℓ₂). Dividing by t - ℓ₂ > 0 gives (4). The horizontal case sets m = 0.

By Levine and Pedersen [43], moving averages and time-series momentum are both weighted sums of past returns. Proposition 3.4 places the swing trendline in the same family. The evidence for trend following therefore bears directly on trading with swing trendlines.

3.2 Measuring the trend: angle, slope and significance

Practitioners judge a trendline partly by its angle, and Bulkowski finds that shallow lines outperform steep ones [10]. The displayed angle, however, depends on chart scaling.

Proposition 3.5 (Angle Depends on Scaling). If a chart displays n bars across width W and a vertical range Δy over height H, a line with slope m is drawn at

θ = arctan(m · s),      s = (H/Δy) / (W/n),      (5)

which can take any value in (0°, 90°) for a fixed m > 0 by choice of s. The normalised angle

θ̃ = arctan(β̂ / σ̂),      (6)

with β̂ the slope of log price per bar and σ̂ the standard deviation of one-bar log returns, is invariant to price level, units and aspect ratio.

Proof. One bar moves the line W/n units horizontally and m H/Δy units vertically on the page, which gives (5). In (6), rescaling prices shifts pₜ by a constant and leaves β̂ and σ̂ unchanged.

The normalised slope β̂/σ̂ is a per-bar Sharpe ratio, and the drift t-statistic is approximately √n tan θ̃. A "strong" trend in invariant terms is therefore a statistically significant one. For a least-squares trend pₜ = a + βt + uₜ over n bars,

β̂ = Σₜ(t - t̄)(pₜ - p̄) / Σₜ(t - t̄)²,      R² = 1 - Σₜ ûₜ² / Σₜ(pₜ - p̄)²,      t_β̂ = β̂ / √(ŝ² / Σₜ(t - t̄)²).      (7)

Proposition 3.6 (Significance Must Be Measured on Returns; Durlauf and Phillips [20]). If pₜ is a driftless random walk, t_β̂ in (7) diverges at rate √n and R² does not converge to zero. The appropriate test of trend strength uses returns:

t_NW = r̄ / √(Ω̂ / n),      TRENDₜ = max{-1, min{1, t_NW}},      (8)

with Ω̂ the Newey–West long-run variance [53]. TREND is the capped trend-strength signal of Baltas and Kosowski [5].

3.3 Benchmark trend rules

Following Moskowitz, Ooi and Pedersen [50], a time-series momentum position with a 12-month look-back earns

r_{t,t+1}^{TSMOM,s} = sign(r_{t-12,t}^s) * (40% / σₜ^s) r_{t,t+1}^s,      (σₜ^s)² = 261 Σ_{i≥0} (1-δ)δ^i (r_{t-1-i}^s - r̄ₜ^s)²,      (9)

with an exponentially weighted ex ante variance (centre of mass δ/(1-δ) = 60 days) scaling each asset to 40% volatility. The moving-average rule of Brock et al. [7], with MAₙ(t) = (1/n) Σ_{i=0}^{n-1} P_{t-i} and band κ, is

sₜ = +1 if MA_S(t) > (1+κ) MA_L(t),      sₜ = -1 if MA_S(t) < (1-κ) MA_L(t).      (10)

Their trading-range break is the horizontal-line case of (3): buy when Pₜ > max_{1≤i≤n} P_{t-i}, sell when Pₜ < min_{1≤i≤n} P_{t-i}. Faber's model [22] holds the asset when the month-end price is above its 10-month average. The Turtle rules [23] enter on a break of the 20- or 55-day high or low and size positions so that one unit risks 1% of equity per N, where N is a 20-day average true range. Lo, Mamaysky and Wang [48] locate pivots objectively with a kernel smoother m̂_h(τ) = Σ_s K_h(τ - s)P_s / Σ_s K_h(τ - s); the pivots of Definition 3.1 can be drawn from m̂_h in the same way.

4 The Probability of Riding a Trend

Persistence tests. The Lo–MacKinlay variance ratio [47] tests whether returns trend:

VR(q) = Var(rₜ + … + r_{t-q+1}) / (q Var(rₜ)) ≈ 1 + 2 Σ_{k=1}^{q-1} (1 - k/q) ρ_k,      z*(q) = (VR(q)-1) / √(ϑ̂(q)/T),      (11)

with VR > 1 indicating trending. Hurst's rescaled range [35] satisfies E[(R/S)_n] ∝ n^H, where H > 1/2 indicates persistence; we compare with the Anis–Lloyd small-sample benchmark [2] (see also [44]).

Proposition 4.1 (Continuation Probability). If consecutive non-overlapping returns (X, Y) are jointly Gaussian with mean zero and correlation ρ, then

P(sign Y = sign X) = 1/2 + arcsin ρ / π.      (12)

For fractional Gaussian noise, ρ = 2^{2H-1} - 1 at every horizon [49], so the continuation probability is 1/2 + π⁻¹ arcsin(2^{2H-1} - 1).

Proof. Write Y = ρX + √(1-ρ²) Z with Z independent of X. By rotational symmetry, {XY > 0} is a pair of opposite sectors of total angle π + 2 arcsin ρ, giving (12). For fractional Gaussian noise, adjacent block sums of length n have covariance 1/2[(2n)^{2H} - 2n^{2H}] and variance n^{2H}.

At H = 0.55 this is 0.523; at H = 0.60, 0.548. A small per-period edge compounds over a trend lasting many periods.

Why exiting on the break helps. If r_{t+1} = μ + ρ(r_t - μ) + ε_{t+1}, then for any threshold c,

E[r_{t+1} | r_t ≤ c] = μ + ρ(E[r_t | r_t ≤ c] - μ) < μ   whenever ρ > 0.      (13)

When returns trend, a sharp move against the position, such as a close through the trendline, predicts below-average returns ahead. This is a simple version of the Kaminski–Lo result that stop rules add value under momentum [38].

Regime probabilities. With bull (B) and bear (R) regimes, return densities φ_B, φ_R and switching probabilities P_ij, the bull probability updates by Bayes' rule [32]:

π_{t|t-1} = P_BB π_{t-1} + P_RB (1 - π_{t-1}),      π_t = π_{t|t-1} φ_B(r_t) / (π_{t|t-1} φ_B(r_t) + (1 - π_{t|t-1}) φ_R(r_t)).      (14)

The optimal policy holds while π_t stays above a threshold and exits below it [17]. Higher lows keep π_t high; a close through the swing trendline pushes it down sharply, making the trendline a visual proxy for the optimal rule.

Expectancy and sizing. Let a rule win with probability p, gaining W on average, and otherwise lose L, with payoff ratio b = W/L.

Lemma 4.2 (Expectancy and Breakeven). The expected profit per trade is E = pW - (1-p)L = L[p(1+b)-1], which is positive if and only if p > p* = 1/(1+b).

Proposition 4.3 (Kelly Fraction). For a binary trade returning +W or -L, the growth-optimal fraction of wealth deployed [40, 62] is

f* = p/L - (1-p)/W = E / (W L),      so the fraction risked is f* L = p - (1-p)/b.      (15)

Proof. Maximise g(f) = p ln(1+fW) + (1-p) ln(1-fL); the first-order condition gives (15), and g" < 0.

Corollary 4.4 (Riding the Trend Is a Payoff-Ratio Business). A trader who stays in while the trendline holds and exits on the break does not need a high win rate. With p = 0.35 and b = 3, E = 0.40L per trade and the Kelly risk fraction is about 0.133. Professional trend followers size well below Kelly; the Turtles risked 1% of equity per unit [23].

5 Results: An Illustrative Test on Public Data

Data and method. These results are illustrative. We use Kenneth French's monthly U.S. market and T-bill returns, 1926–2018 [27], plus daily and weekly S&P 500 and NASDAQ (1999–2018) and WTI crude oil (1986–2019), all public datasets distributed with the arch Python package [59]. Signals use only information available at the close of bar t and apply to bar t+1. The swing rule is Definition 3.2 with pivot order k, δ = 0, and costs of 10 bp per switch. Benchmarks are a 10-month moving-average filter [22] and a 12-month time-series momentum filter [50], holding T-bills when out. Sharpe ratios use excess returns over T-bills.

Table 1: Illustrative backtest. The swing rule (k = pivot order in months) is long while the swing support line holds and in T-bills after a break.

Riding the trend, avoiding the collapse. Every trend rule kept most of the market's long-run return with about two-thirds of its volatility and roughly half its maximum drawdown (Table 1, Figure 2). In 1929–1932 buy-and-hold lost 83.7% against 22.1% for the swing rule; in 2000–2002, 45.1% against 10.2%; in 2007–2009, 50.4% against 2.7%. In the sudden 1987 crash all approaches lost about 24%: no trend rule can exit before the first break.

Figure 2: Growth of $1 (log scale), U.S. market, 1927–2018. [Gráfico logarítmico ascendente con 4 líneas]

Trade statistics. The swing rule (k=3) made 97 long trades and won 60.8% of them, with an average win of +17.2% against an average loss of -4.3% (b = 3.96) and an expectancy of E = +8.8% per trade (Lemma 4.2; Figure 1). Small losses on breaks and large gains while the line holds are the signature of "let profits run, cut losses short."

Continuation by structure state. In up-structures the next month was positive 64.7% of the time and the next three months 71.1%, against 58.3% and 60.3% in down-structures (Table 2). Volatility was 15.4% against 22.4%, and up-structures lasted 7.0 months on average against 3.9. Within this single market the differences are directionally consistent but not individually significant (Welch t = 1.39 at one month); the broad-sample evidence comes from diversified studies [50, 36, 42]. Monthly variance ratios exceed one (VR(2)=1.10, z*=1.97; VR(12)=1.22, z*=1.20), and the autocorrelation of 0.10 implies a continuation probability of 0.532 (Proposition 4.1). The R/S Hurst estimate is 0.63 against a small-sample benchmark of 0.57.

Table 2: Forward U.S. market returns by swing-structure state (k=3), 1927–2018. HH/HL: higher highs and higher lows; LH/LL: lower highs and lower lows.

Timeframe and direction. Sensitivity runs gave two practical lessons. First, timeframe matters: on weekly S&P 500 bars (1999–2018) the long/flat rule cut maximum drawdown from 56% to 23–50% depending on pivot order, and at k = 4 weeks improved return per unit of risk. On daily bars with short pivots it had lower return per unit of risk than buy-and-hold, consistent with evidence that higher-frequency trend signals add little after costs [13]. Second, the reversal side depends on the market: in upward-drifting U.S. equities, going short after an up-trendline break lowered returns (stop-and-reverse CAGR 5.5% vs. 8.5% long/flat), whereas in diversified futures both long and short trends pay [50, 36]. These exploratory runs are reported for transparency, not as optimised results.

A trendline case study. In Figure 3, the S&P 500 swing support line from the 11 March 2003 low through the 15 August 2007 low (12.7% a year) broke on 21 November 2007 at 1,416.77, 9.5% below the October peak. The index then fell a further 52% to its March 2009 low; the 200-day average exited on 7 November. The line is drawn at 19.4°, 35.2° or 12.0° depending on chart dimensions, but its normalised angle (6) is 2.9° (Proposition 3.5). The OLS t_β̂ = 118.9 is inflated, while the return-based t_NW = 2.84 is still significant (Proposition 3.6).

Figure 3: S&P 500 (log scale), 2002–2009: swing support trendline with its touches (circles) and break, OLS trend, and 200-day moving average.

A trendline through swing points is a running estimate of the trend. While price holds the line, the trend is intact; when price closes through it, the evidence has changed, and so should the position.

6 Main Result

Main Result 6.1 (Evidence Synthesis). Combining the literature in Section 2 with Sections 3–5:

(a) Trends persist. Time-series momentum is documented across asset classes over more than a century [50, 36, 42]. Per-period continuation probabilities above 1/2 compound over the life of a trend (Proposition 4.1; Table 2).

(b) Swing trendlines are momentum signals. Holding above a line through swing points is equivalent to positive momentum since the last pivot, measured against the trend's own slope (Proposition 3.4). Trading-range breaks of prior highs and lows have independent historical support [7, 8, 23].

(c) Swing levels matter to the market. Support and resistance coincide with order-book depth, predict trend interruptions, and attract stop orders whose triggering can accelerate moves after a break [55, 56, 57, 39, 12].

(d) Exiting on the break is rational when trends persist. Stop rules add value under momentum (13) [38], and threshold exits on falling bull-regime probability are optimal under regime switching (14) [17].

(e) The payoff is asymmetric. Riding the trend and exiting on the break produce b >> 1 (Lemma 4.2): in our illustration, a 61% win rate with wins about four times losses, and a halved maximum drawdown (Table 1).

(f) Line quality matters. In Bulkowski's samples, trendlines with more touches, longer duration and shallower slope performed better, and exiting at the first close beyond the line beat waiting [10, 11].

Support. (a) Section 2, Proposition 4.1; (b) Proposition 3.4 and Section 2; (c) Section 2; (d) equations (13)–(14); (e) Lemma 4.2, Section 5; (f) Section 2. This is a synthesis of existing evidence and of the illustration above.

7 Discussion and Practical Considerations

What the swing structure adds. Fixed-window rules such as the 10-month average treat every market alike. The swing trendline adapts its look-back to the market's own rhythm (Proposition 3.4) and anchors exits at levels where orders actually cluster [56, 39]. Bulkowski's data offer practical refinements. Among 3,274 down-sloping trendlines broken upward in bull markets, the average subsequent rise to the ultimate high was 51% (median 30%), and a throwback to the line followed 59% of breakouts [11]. For up-sloping lines, four or more touches, lengths beyond about 44 days and shallow slopes were associated with better outcomes [10].

Testing discipline. With many possible rules, the best backtest is biased upward [61, 63, 33, 4]. Defining pivots and breaks precisely (Definitions 3.1–3.2) is what makes a swing method testable and repeatable.

Costs, timeframe and regime. Transaction costs and slippage weigh more on frequent signals [25, 58, 13]. Trend methods give back profits in sideways, choppy markets and cannot pre-empt overnight shocks. Their performance varies over time [46, 5], and sharp rebounds from panic lows can hurt short positions [19]. Volatility-based sizing [50, 23] and trading several uncorrelated markets [36] are the standard defences.

8 Conclusion

Trading with the trend rests on a well-documented fact: returns persist over weeks to months. A trendline drawn through swing highs and lows is a direct, adaptive way to measure that persistence. It is mathematically a momentum signal, it is anchored at price levels with real order-flow significance, and its break is the kind of exit that theory shows to be valuable when trends persist. The method's edge comes from the shape of its payoffs (small losses when the line breaks, large gains while it holds) and from avoiding the deepest declines. In our illustration that meant most of the market's long-run growth with less than half of its maximum drawdown.

Acknowledgements. The author thanks Kenneth R. French and the maintainers of the arch package for the public data; all computations are the author's own and reproducible. Disclaimer: for research and education only; not investment advice.

References

[1] S. S. Alexander, Price movements in speculative markets: Trends or random walks, Industrial Management Review 2(2), 1961.
[2] A. A. Anis and E. H. Lloyd, The expected value of the adjusted rescaled Hurst range of independent normal summands, Biometrika 63(1), 1976.
... [65 references from original paper, including Bulkowski, Brock et al., Moskowitz Ooi Pedersen, Faber, etc.]

Documento recreado a partir del carrusel de Instagram @tori.trades — 26 Oct 2026. Para referencia completa ver las 10 imágenes originales.

### Table 1
| Strategy, U.S. market (Jul 1927–Nov 2018) | CAGR | Vol. | Sharpe | Max DD | Worst month |
|---|---|---|---|---|---|
| Buy and hold | 9.84% | 18.5% | 0.42 | -83.7% | -29.1% |
| Swing-structure trendline rule, long/flat (k=3) | 8.48% | 12.3% | 0.46 | -37.9% | -22.6% |
| Swing-structure trendline rule, long/flat (k=2) | 8.35% | 12.3% | 0.45 | -51.7% | -22.6% |
| 10-month SMA filter (72.7% invested) | 9.80% | 12.5% | 0.55 | -43.0% | -22.6% |
| 12-month TSMOM filter (70.1% invested) | 9.98% | 12.4% | 0.56 | -44.0% | -22.6% |

### Table 2
| Swing structure at month-end | n | P(r_t+1>0) | P(r_t+3>0) | P(r_t+6>0) | Mean 1-month | Ann. vol. |
|---|---|---|---|---|---|---|
| Uptrend (HH / HL) | 680 | 64.7% | 71.1% | 75.6% | +0.97% | 15.4% |
| Downtrend (LH / LL) | 381 | 58.3% | 60.3% | 64.1% | +0.45% | 22.4% |
