# EdgeLab — plan maestro (2026-07-17)

Proyecto **aislado** del ecosistema principal (`$AVectorBTecosistema`), creado
tras EXP-041/042: el edge de momentum M1 murió por lookahead intrabar de la
decisión, y la cinta NQ vieja quedó inutilizable. EdgeLab arranca en limpio
para que ningún resultado nuevo herede contaminación del estado previo.

Fuente del diseño: `compass_artifact_wf-3d072c3c...markdown.md` (informe de
estrategias gratis + stack de validación), filtrado por lo que ES implementable
con nuestros datos y disciplina.

## Reglas de aislamiento

1. **Cero imports del árbol viejo.** Los primitivos compartidos (contratos de
   instrumento, Deflated Sharpe, kernels de first-passage tick) se COPIAN a
   `edgelab/` — si el ecosistema viejo tiene un bug, no se propaga.
2. **Datos**: solo lectura de fuentes ya re-validadas (`ES_ticks.parquet` está
   verificado: continuo, bid/ask, sin huecos falsos). Todo dato NUEVO (NQ)
   pasa por `databuild/` con reporte de validación ANTES de usarse.
3. **El registro científico sigue siendo central**: cada experimento se asienta
   en `C:\$ACerebroSSRN\cerebro\LEDGER_EXPERIMENTOS.md` (ids EXP-0xx). El
   aislamiento es de CÓDIGO y DATOS, no del historial de evidencia.
4. **Regla 7 (causalidad intrabar) es constitucional**: toda feature de una
   señal con ejecución dentro de la barra i se computa con datos hasta i-1;
   señal que necesita el cierre de i paga la confirmación (market i+1 o limit
   con fill conservador). Checklist obligatorio en el diseño de CADA estrategia.

## Qué del informe SE IMPLEMENTA (por orden)

### Tier 1 — el "gauntlet" de validación (valor más alto, independiente de datos)
El informe aporta 3 tests que NO tenemos y son complementarios reales a
nuestro stack (DSR + BH + null temporal + IS/OOS + corte mensual + tick fills):

- **MCPT (Monte Carlo Permutation Test, Timothy Masters)** — `validation/mcpt.py`
  (in-house, ~100 líneas numba; el repo neurotrader888 es la referencia del
  método, no hace falta como dependencia). Baraja los log-returns intradía
  preservando distribución/vol y destruyendo el orden temporal; re-corre el
  PIPELINE COMPLETO (generación de señal incluida) sobre 1000 permutaciones →
  p-value del proceso entero, no de un combo. Cubre el sesgo de selección que
  el DSR solo aproxima.
- **PBO/CSCV (Probability of Backtest Overfitting)** — `validation/pbo.py`
  (in-house, ~60 líneas; pypbo como referencia). Sobre la matriz trades×combos:
  ¿con qué probabilidad el mejor combo IS queda bajo la mediana OOS?
- **SPA / Reality Check de Hansen** — wrapper sobre `arch` (pip, mantenida,
  de Kevin Sheppard) en `validation/spa.py`. Para comparar variantes de
  estrategia contra benchmark corrigiendo data-snooping.

`validation/gauntlet.py` = runner único con el ORDEN del informe fusionado con
el nuestro: costos reales desde el minuto cero → walk-forward/OOS → MCPT →
DSR+BH → PBO → SPA (si hay familia de variantes) → corte mensual/régimen →
checklist de causalidad. **Umbrales pre-registrados** (del informe, adoptados):
MCPT p>0.05 = muerto; PBO>50% = muerto; edge que desaparece con costos
realistas = muerto.

### Tier 2 — estrategia candidata #1: Intraday Momentum "Noise Area" (Zarattini/Aziz/Barbon, SSRN 4824172)
La única estrategia del informe con reglas completas, evidencia publicada
(Sharpe 1.33 neto, 17 años SPY; réplica independiente en NQ Sharpe ~1.67) y
**causal por construcción**:
- Noise Area: apertura_diaria × (1 ± |move| intradía promedio hasta ese
  minuto-del-día, últimos 14 días), ajustada por gap — todo con datos previos.
- Entrada SOLO en HH:00/HH:30 al romper la banda (decisión al cierre del
  minuto previo → sin lookahead intrabar si se entra market al minuto
  siguiente: pagamos esa fricción explícitamente, motor tick bid/ask).
- Trailing = banda opuesta o VWAP de sesión (con valores del minuto CERRADO).
- Flat a las 16:00 ET. Sin overnight.
- `strategies/noise_area.py`. Primero ES (datos listos), después NQ limpio.
- Costos pre-registrados: 0.5t fee + fill real bid/ask (mucho más duro que el
  paper, que admitió costos 3-5x optimistas).
- **Expectativa honesta pre-registrada**: con 6.5 meses (~135 sesiones,
  entradas solo en 14 slots/día) el poder estadístico es limitado; el test
  responde "¿expectancy causal positiva tras costos + gauntlet?" — NO
  "replica el Sharpe 1.33". Un resultado plano NO refuta el paper; un
  resultado negativo claro mata el port a nuestros instrumentos.

### Tier 3 — segunda tanda (solo si Tier 2 da señal de vida)
- **ORB 5-min simple en NQ/ES**: prior BAJA pre-registrada (el propio paper
  dice Sharpe 0.48 sin el filtro "Stocks in Play", que no es portable a un
  futuro único). Se corre solo como comparación barata dentro del mismo
  harness (mismas sesiones, mismo gauntlet).
- **Cruce ES×NQ causal** (la pregunta intermercado original): con NQ limpio,
  re-test de confluencia/lead-lag con TODAS las features en i-1 — cierra
  honestamente lo que EXP-042 refutó.

## Qué del informe SE DESCARTA (y por qué)

- **RSI-2 de Connors**: necesita SMA(200) DIARIA → ~1 año de historia; tenemos
  6.5 meses y ~3 trades/mes esperables. Sin poder estadístico. Si algún día
  hay años de daily continuo, se revisa.
- **ORB "Stocks in Play"**: requiere universo de 7000 acciones con volumen
  relativo. No portable a futuros únicos (el propio informe lo dice).
- **QQQ/TQQQ ORB (SSRN 4416622)**: asume slippage CERO explícito. Números no
  transferibles.
- **Estrategias comerciales** (The Takeover, automated-trading.ch): marketing
  sin auditoría. Solo cantera de ideas, jamás benchmark.
- **Repos NinjaScript de GitHub**: sin evidencia auditada; se archivan como
  PLANTILLAS C# para el DÍA que algo sobreviva el gauntlet y haya que portarlo
  a NT8 (MicroTrends ATSQuadroStrategyBase para infra de órdenes).
- **mlfinlab**: ya no es gratis. **timeseriescv**: abandonada con bugs
  conocidos. **backtesting.py/backtrader/bt**: nuestro motor tick bid/ask ya
  hace fills path-dependent mejor que un event-driven genérico.
- **Optuna**: en tensión con nuestra disciplina (más búsqueda = más haircut
  BH/DSR). Solo entraría con espacios continuos genuinos y SIEMPRE dentro del
  gauntlet con PBO. No en la primera tanda: grids chicos pre-registrados.
- **Polars/DuckDB**: pyarrow por batches ya maneja 148M ticks sin problema.
  Calidad de vida, no necesidad. Se pospone.
- **quantstats/pyfolio**: tearsheets cosméticos; nuestras métricas por-trade
  en ticks son más honestas para futuros. Se pospone.

## Datos — reconstrucción limpia del NQ (`databuild/`)

Fuente nueva: exports POR CONTRATO desde NT8 en `D:\A  Trading\`
(`NQ 12-25.Last.txt`, `NQ 03-26.Last.txt`, `NQ 06-26.Last.txt`,
`NQ 09-26.Last.txt` — formato `yyyyMMdd HHmmss ffffff;last;bid;ask;vol`).

Pipeline `databuild/build_nq_clean.py` (TODO lo contrario del merge viejo):
1. Parse por contrato → parquet por contrato (timestamp datetime64[ns] UTC
   naive, float64, NUNCA float32).
2. **Validación por contrato**: span, spread p50/p99 en su periodo front,
   saltos tick-a-tick, monotonicidad, duplicados.
3. **Empalme por VOLUMEN**: fecha de switch = primer día en que el contrato
   siguiente supera el volumen diario del anterior (regla mecánica, sin mirar
   precios). NADA de solapamiento: cada timestamp pertenece a UN contrato.
4. **Back-adjustment aditivo** en cada switch (offset = mediana de
   mid_next - mid_prev en la última hora común líquida), acumulado hacia atrás
   — misma convención que la cinta continua del ES.
5. **Reporte de validación FINAL** (gate de uso): 0 saltos >20pt fuera de
   noticias, spread p50 ≈ 1-2t en RTH, sin huecos no-calendario, comparación
   de retornos diarios vs ES (correlación ~0.9 esperada). Si no pasa, la cinta
   NO se usa.
6. Derivados: `nq_m1_candles` (índice ns), `nq_vap_m1`, features de volumen —
   recién DESPUÉS del gate.

## Fases

- **F0** — esqueleto + este plan. ✅ (2026-07-17)
- **F1** — `edgelab/` primitivos copiados (Instrument, deflated_sharpe/BH,
  kernels tick first-passage con entrada stop/market/limit) + tests mínimos.
- **F2** — `validation/`: mcpt.py, pbo.py, spa.py (arch), gauntlet.py.
  Smoke test del gauntlet sobre una estrategia random (debe MORIR en todo).
- **F3** — `databuild/build_nq_clean.py` (bloqueado hasta que termine el
  export del 12-25; 03/06/09-26 ya están).
- **F4** — `strategies/noise_area.py` sobre ES → gauntlet completo → ledger.
- **F5** — Noise Area sobre NQ limpio + ORB comparativo + cruce ES×NQ causal
  → ledger. Si algo sobrevive TODO el gauntlet: port a NT8 (plantilla
  MicroTrends) y validación sim.

## Estado

| Fase | Estado |
|---|---|
| F0 esqueleto+plan | HECHO |
| F1 primitivos (`edgelab/`) | HECHO (instruments, audit, sessions RTH con DST) |
| F2 gauntlet (`validation/`) | HECHO + smoke test PASADO (estrategia random muere: MCPT p=0.37, OOS invertido; PBO familia random 0.44) |
| F3 NQ limpio | HECHO sin 12-25 (decision del usuario). Spans reales: 03-26 dic11→mar20, 06-26 abr19→jun18, 09-26 jun14→jul15. **Hueco de export mar-20→abr-19 (sin solapamiento 03/06): frontera de nivel con offset 0 documentada — PROHIBIDO cruzarla con lookbacks de nivel.** Roll jun con solapamiento real → offset medido. |
| F4 Noise Area ES | HECHO — **MUERTA por expectancy** (-2.90t/trade neto con costo 2.5t RT, n=146, win 34%). Dato clave: MCPT p=0.002 — la ESTRUCTURA de momentum intradia es real (permutaciones pierden 26× mas), pero no paga los costos en esta ventana. |
| F4b ORB 5-min ES | HECHO — **MUERTA por MCPT** (p=0.15): +36.96t/trade, 7/8 meses+, OOS +64.8 — pero las permutaciones (que preservan el retorno open→close del dia) tambien ganan +2979t: el PnL es la DERIVA del semestre, no el patron ORB. Falso positivo que ningun test previo del ecosistema hubiera detectado. |
| F5 NQ + cruce ES×NQ | HECHO — Noise Area NQ **MUERTA** (-20.2t, MCPT p=0.13). Cruce ES→NQ causal: p=0.75 → **SIN informacion condicional** (pregunta intermercado cerrada: sin evidencia). |
| F6.1 tick-fills ORB | HECHO — **cazo un BUG DE SIGNO nuestro en el stop del short del kernel M1** (perdidas de shorts booked como ganancias). Con el fix, M1 y tick COINCIDEN: **ORB NQ -18.7t (MCPT p=0.58) y ORB ES -13.1t → MUERTAS. El "sobreviviente" queda RETRACTADO.** Tanda compass: 0/5 vivas. |

**Cinta NQ extendida (2 exports nuevos)**: 95.3M ticks, ago-28 2025 → jul-15
2026 (~10.5 meses), 5 contratos, 3 rolls medidos (+232.50/+247.12/+311.38 pts),
gate OK (corr diaria vs ES 0.951). Frontera sin datos mar-20→abr-19 documentada.

**Regla 8 nueva (de la correccion EXP-043)**: el MCPT no detecta bugs de
implementacion (GIGO — el mismo codigo corre sobre real y permutado). Ningun
sobreviviente se asienta sin ACUERDO DE DOS SIMULADORES INDEPENDIENTES
(motor distinto + resolucion de datos distinta). Ya es regla 8 en
CEREBRO_SSRN.md.

**Estado final de la primera tanda**: infraestructura completa y calibrada
(gauntlet + cinta NQ limpia + doble simulador); 5/5 estrategias muertas con
causa identificada. Proximo trabajo candidato: pasar los edges tick-nativos
EXP-029/030 del ecosistema viejo por este gauntlet (siguen siendo lo unico
potencialmente vivo), o nueva tanda de candidatos con hipotesis economica.

**Leccion de datos (2026-07-17)**: el spread p50=3t del NQ es REAL (aparece en
el archivo por-contrato limpio), no era solo la contaminacion del merge viejo
— el NQ es estructuralmente mas fino que el ES (~1t). Los costos NQ deben
presupuestar ~3t de spread + slippage.
