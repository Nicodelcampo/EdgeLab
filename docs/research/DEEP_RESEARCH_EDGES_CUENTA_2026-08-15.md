# Deep research — qué hacen quienes validan edges en una cuenta

**Fecha:** 2026-08-15
**Estado:** `RESEARCH_NOTES` — no autoriza F4, holdout ni P&L.
**Mapa:** `docs/research/INVESTIGACION_QUIENES_VALIDAN_EDGES_2026-08-15.md`
**Firewall:** `holdout_included=False`, `outcomes_accessed=False`.

Nadie publica el alpha. Lo copiable es el proceso de rechazo y los números con los que deciden.

## El hecho

Pipeline público (Two Sigma / D.E. Shaw / Citadel GQS / WorldQuant):
hipótesis → features → IC/ICIR + costo neto → OOS → capacidad/decay/corr → paper → 1 contrato.
Un Sharpe 0,3 aislado es inoperable. Un detector no es un portafolio.

## Diez errores (López de Prado, JPM 2018)

1. Sísifo (un quant arma el auto) → laboratorio por estaciones.
2. Investigar *a través* del backtest → importancia de features **antes** (F4).
3. Barras de reloj → volume/dollar/tick clock.
4. Diferenciar a orden 1 → FracDiff; 87 futuros líquidos, ninguno necesita d=1. ES: d=0,4 estacionario, corr 0,995; d=1 deja 0,05.
5. Horizonte fijo → triple barrera (TP/SL en vol + expiración por barras).
6. Lado y tamaño juntos → meta-labeling (primario = setup; secundario = ¿actúo?).
7. No-IID → uniqueness + sequential bootstrap. 424 eventos H1 ≠ n=424 IID.
8. CV con leakage → purge + embargo ~1 %.
9. Un solo walk-forward → CPCV (distribución de Sharpes).
10. Elegir el max Sharpe → DSR con N_eff.

ASA: ~20 iteraciones al 5 % = un falso positivo esperado.

## Números que cambian una decisión

### 7 configs fabrican Sharpe 1

Bailey/López de Prado: tras **7** configuraciones se espera un backtest de 2 años con SR anualizado > 1 cuando el SR verdadero es 0.

ADIA 2024: SR reportado 1,0 / 5 años / T=1260. Un trial: p=0,02. Diez trials, se reportó el mejor: E[max]≈0,69, corte 95 %≈1,12, p≈0,88. **No significativo.**

Harvey 2017: mejor long-short por 3 letras del ticker → t=3,23. t>3 no basta.

Aplicación: 7 indicadores × contratos × bar_spec es ese experimento. Cada celda no cobrada es un trial oculto.

### Grinold: IR ≈ IC × √Breadth

Breadth = apuestas **independientes**/año, no filas.

| Breadth honesta | IC mín. para IR=1 |
|---|---|
| 250 (1 inst., 1 forecast/día) | 0,063 |
| 50 (1 evento/sesión) | 0,14 |
| 4 instrumentos × 1/día, poco corr. | 0,032 |

F4 = Spearman(estado, retorno) por horizonte. Si IC ≈ 0, no hay cap. 6.
F3 (ES/NQ/YM) es potencia, no turismo.

### Costos CME (no-miembro, por lado) + NFA $0,01

| Contrato | Exchange | Tick $ | Exchange ticks/lado | RT exch+NFA |
|---|---|---|---|---|
| ES | $1,38 | 12,50 | 0,110 | $2,78 ≈ 0,22 t |
| NQ | $1,38 | 5,00 | 0,276 | $2,78 ≈ 0,56 t |
| YM | $1,38 | 5,00 | 0,276 | $2,78 ≈ 0,56 t |
| 6E | $1,60 | 6,25 | 0,256 | $3,22 ≈ 0,52 t |
| MES | $0,35 | 1,25 | 0,28 | micro más caro en ticks |
| MNQ/MYM | $0,35 | 0,50 | **0,70** | ídem |
| M6E | $0,24 | 1,25 | 0,19 | más barato en ticks que 6E |

H1: 2,768 ticks de 6E ≈ $17,30 RT. Exchange+NFA = $3,22. El resto es spread/slip/broker. Copiar 2,768 a ES = **$34,60** RT vs $2,78 de exchange. Suicida.

Escenario base EdgeLab (slip 1 tick/pata) en ES: ~$28+ RT. Un bruto de 0,3 ticks muere en cualquier índice.

AQR 2018: costos vivos institucionales << papers. Lección: medir con el broker propio, no bajar el slip a ojo.

## Triple barrera y meta-label

TP/SL en **vol**, expiración por barras de actividad, etiqueta = primera barrera. H1 fue close-through o fin de sesión, sin TP/SL. El 96 % rompe: el neto −2,47 era previsible.

Meta-label: (1) hay setup, alto recall; (2) ¿este se toma? El 2 no busca trades. Eso es F4 → filtro, no F4 → grid de SL/TP.

## Tres backtests (ADIA 2024)

WF (lo que G2 pide) / CPCV / Monte Carlo con proceso generador.
Antes de cualquier backtest: **grafo causal**. Si no se dibuja por qué el mercado pagaría, no se corre.
Finanzas prefiere FWER a FDR: mejor matar verdaderos que promover un mentiroso.

## Paper → contrato

Shadow con spread real. 1 contrato. Si live ≠ research, se mata, no se tunnea.
Carver: limitar el trading al mínimo. Bruto SR 0,31 puede ser −0,46 neto. Enemigo = turnover.

## No copiar

4 millones de alphas. Costos AQR de equity institucional. FracDiff/ML como cap. 1. t>3 o SR>1 como sello.

## Fuentes

- López de Prado 2018, [10 reasons](https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf)
- Bailey et al. 2014, [Pseudo-mathematics](http://ssrn.com/abstract=2308659)
- Bailey & López de Prado 2014 DSR; 2021 False Strategy Theorem
- Joubert et al. 2024, [Three types of backtests](https://www.hillsdaleinv.com/uploads/The_Three_Types_of_Backtests.pdf)
- Harvey 2017, [Presidential address](https://people.duke.edu/~charvey/Media/2018/SSRN-id2893930.pdf)
- Frazzini/Israel/Moskowitz 2018 Trading Costs
- Grinold/Kahn cap. 6
- [IBKR CME](https://www.interactivebrokers.com/en/accounts/fees/CME.php), [TradeStation](https://www.tradestation.com/pricing/exchange-execution-and-clearing-fees/)

Aporte al referente: números robables (7 trials → SR 1 falso; IC 0,06–0,14 en futuros; 2,768 ticks ≠ tabla CME) traducidos a F4/DSR/triple barrera.
