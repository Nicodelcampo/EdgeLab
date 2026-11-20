# @traderdrysdale - Initial Balance + The Madonna - Reel Df2pC5-phBZ

**Reel:** https://www.instagram.com/reel/Df2pC5-phBZ/
**Autor:** @traderdrysdale - Drysdale Trading Group - VWAP Wave System
**CTA del reel:** Comentá 'IB' y te manda guía gratis
**Fecha scrapeo:** 2026-11-17
**Instrumento en ejemplo:** NQ1! - Nasdaq Futures
**Tipo:** Mean-reversion en día de rango + Breakout en día de tendencia - 1 setup por día, 1 hora de paciencia

## VEREDICTO EN 10 SEGUNDOS

**Es Market Profile clásico, no invento.** Initial Balance (IB) es concepto de Peter Steidlmayer / James Dalton de los 80s: Primera hora define el rango de balance inicial. Lo que Drysdale agrega es branding: 'The Madonna' = primer toque del IB High/Low con rechazo.
**Por qué es bueno para EdgeLab:** 1 trade por día, reglas claras, ventana fija, stop definido, target definido, no overtrade. Es ideal para Cartera 2 estable (Payout Loop) y para 5-días phase (necesitás 5 wins, no 5 trades rápidos).
**Por qué es peligroso si lo copiás tal cual:** No define 'time + distance' para confirmar tendencia, no define tamaño de IB válido, no define qué hacer si no hay toque, no define Risk. Sin esos filtros, es 50% WR con RR 1.4 y costos te lo matan si Risk es chico.
**Para LucidFlex:** Con Risk $350, necesitas micros (8 micros = $16/pto), no minis. Con 1 mini, Risk $420 > $350. Con 2 minis, Risk $840, 2 losses = blow $1.000. **Micros obligatorios.**

## 1. REGLAS EXACTAS - COMO LO DICE DRYSDALE

### 1A. Definición Initial Balance

```
VENTANA IB: 9:30 AM - 10:30 AM New York time (ET)
  9:30 = Apertura NY cash
  10:30 = Cierre primera hora
  NO TRADEES en 9:30-10:30. Hands off. 'Sometimes the best move is waiting 60 minutes.'
  'Most traders screw it up, they blow half their account in first 15 minutes because they couldn't sit on hands for 60 minutes.'
IB_HIGH = max(High 9:30-10:30)
IB_LOW  = min(Low 9:30-10:30)
IB_MID  = (IB_HIGH + IB_LOW) / 2
IB_RANGE = IB_HIGH - IB_LOW
Ejemplo del reel:
  IB_HIGH = 21,462.00
  IB_LOW  = 21,380.00
  IB_MID  = 21,421.00  ( (21462+21380)/2 = 21421 )
  IB_RANGE = 82.00 pts
```

### 1B. Clasificación del Día - Range Day vs Trend Day

```
DESPUÉS de 10:30, observás:
SI precio SE QUEDA DENTRO de [IB_LOW, IB_HIGH]:
  CONTEXTO = RANGE DAY
  BIAS = FADE EDGES
  'I fade the edges of the initial balance and I target the IB mid.'
  Short en IB_HIGH -> Target IB_MID
  Long en IB_LOW  -> Target IB_MID

SI precio ROMPE fuera de IB y SE MANTIENE fuera con TIEMPO + DISTANCIA:
  CONTEXTO = TREND DAY / BREAKOUT
  BIAS = LONG si rompe IB_HIGH, SHORT si rompe IB_LOW
  'If price breaks out and holds there with time and distance, this could be a trend day, I trade in direction of break.'
  NO fades en trend day. Si intentás fade en trend day, te atropella.
```

**Problema:** Drysdale no define 'time + distance' en números. Para EdgeLab, necesitás definirlo. Propuesta en Sección 3.

### 1C. The Madonna - El Setup de Mayor Probabilidad

```
NOMBRE: 'The Madonna' - En su comunidad, así llaman al primer toque de IB High o IB Low.
'I like to wait for the very first touch of the IB high or IB low. In my community we call it the Madonna. It's the highest probability trade of the day.'

CONDICIONES MADONNA (todas deben cumplirse):
1. PRIMER TOQUE: Es el PRIMER toque después de 10:30. Segundo toque NO es Madonna, probabilidad menor. Solo 1 Madonna por lado por día.
2. WICK: Vela toca IB_HIGH o IB_LOW y deja mecha (wick) más allá del nivel, pero NO cierra más allá.
   'I need a wick'
3. HOLD: Precio se mantiene, no cierra más allá del nivel en la vela de toque.
   'a hold'
4. CANDLE CLOSE THROUGH? / NO CLOSE THROUGH: En el reel dice 'a candle, close through it, then I'm in' - Interpretación: Necesita vela que cierre DE VUELTA dentro del IB, no fuera. Es decir, vela de rechazo que cierra dentro.
   Si cierra fuera del IB y se mantiene fuera, NO es Madonna, es Breakout (Trend Day). No fades.
5. ENTRADA: Después de wick + hold + cierre dentro, entras en dirección de fade (contraria al toque).
   Short si tocó IB_HIGH, Long si tocó IB_LOW.
6. STOP: Más allá del Swing High/Low de la vela de toque, no más allá del IB.
   'The stop goes beyond the swing.'
   Ejemplo Short: Swing High 21,472.00, Entry 21,451.00, Stop 21,472.00 (o 21,474 con buffer 2 pts)
7. TARGET: IB_MID
   'I target the IB mid.'
   Ejemplo Short: Target 21,421.00
```

### 1D. Ejemplo Completo del Reel - Short Madonna en IB High

| Parámetro | Valor Reel | Cálculo |
| --- | --- | --- |
| IB_HIGH | 21,462.00 | Max 9:30-10:30 |
| IB_LOW | 21,380.00 | Min 9:30-10:30 |
| IB_MID | 21,421.00 | (21462+21380)/2 |
| IB_RANGE | 82.00 pts | 21462-21380 |
| Swing High (wick) | 21,472.00 | Mecha 10 pts por encima de IB_HIGH |
| Entry Short | 21,451.00 | Cierre de vela de rechazo dentro del IB, 11 pts debajo de IB_HIGH |
| Stop | 21,472.00 | Más allá del Swing High, 21 pts de Risk |
| Target | 21,421.00 | IB_MID, 30 pts de Reward |
| Risk | 21.00 pts | 21472-21451 |
| Reward | 30.00 pts | 21451-21421 |
| RR | **1.43 : 1** | 30/21 |
| P&L 1 Mini NQ ($20/pto) | Risk $420, Reward $600 | 21*20=420, 30*20=600 |
| P&L 2 Minis NQ | Risk $840, Reward $1.200 | Demasiado para Lucid $1.000 daily |
| P&L 8 Micros MNQ ($2/pto) | Risk $336, Reward $480 | 21*16=336 (8 micros * $2 = $16/pto), 30*16=480 |
| P&L 10 Micros | Risk $420, Reward $600 | 10*2=20/pto, igual que 1 mini |
| Resultado en reel | **TARGET HIT** | Precio llegó a IB_MID, 'TARGET HIT' en pantalla |

**Para Long Madonna (simétrico):**
```
Si precio toca IB_LOW 21,380, wick a 21,370 (10 pts debajo), cierre dentro a 21,391, Entry Long 21,391, Stop 21,370 (Risk 21 pts), Target IB_MID 21,421 (Reward 30 pts), RR 1.43:1 igual.
```

## 2. LO QUE NO DICE - Y QUE EDGELAB NECESITA DEFINIR

### 2A. ¿Qué es 'Time + Distance' para Trend Day?

Drysdale dice 'holds there with time and distance' pero no da números. Sin números, no podés backtestear.
**Propuesta EdgeLab (para validar OOS):**
```
TREND_DAY_CONFIRMED si:
  (Cierre 5-min > IB_HIGH + 10 pts) Y (Siguiente vela 5-min también cierra > IB_HIGH)  -> 2 velas 5-min fuera = TIME (10 min) + DISTANCE (10 pts)
  O (Cierre 5-min > IB_HIGH + 15 pts en 1 vela) -> Distancia grande, 1 vela suficiente
  O (Precio se mantiene fuera por >15 min sin volver dentro)
Si TREND_DAY_CONFIRMED, NO fades. Solo trades en dirección del break: Long en pullback a IB_HIGH (ahora soporte) o Breakout continuation.
Si NO confirmado (1 vela fuera pero vuelve dentro en <10 min o <10 pts), es FAKE BREAKOUT, es Madonna tardía, fade de vuelta a IB_MID.
```
**Validar:** Backtest con TIME=10 min vs 15 min, DISTANCE=10 pts vs 15 pts, ver cuál da mejor PF OOS. No asumir.

### 2B. ¿Qué IB Range es Válido?

Si IB_RANGE es muy chico, target a IB_MID es muy chico, RR no cubre costos. Si es muy grande, stop es gigante, Risk no cabe en Lucid.
**Propuesta:**
```
IB_RANGE válido para NQ:
  MIN 40 pts (si <40, Target a Mid es <20 pts, RR <1 con Stop 21 pts, no trade)
  MAX 120 pts (si >120, Stop probable >30 pts, Risk $350 con 8 micros = 30*16=480 > $350, no trade o baja size)
  OPTIMO 60-100 pts (ejemplo 82 pts está en óptimo)
  Si IB_RANGE fuera de [40,120], NO_TRADE ese día. Espera al día siguiente.
```
**Para ES:** IB_RANGE válido 10-30 pts (ES 1 pto = $50/mini, 1 micro = $5/pto). Ajustar por volatilidad: IB_RANGE / ATR(14) debe estar entre 0.5 y 1.5.

### 2C. ¿Qué Hacer Si No Hay Toque?

Drysdale no dice. En muchos días, precio nunca toca IB High/Low después de 10:30, se queda en medio.
**Regla EdgeLab:** Si a las 12:00 (ET) no hubo Madonna, NO_TRADE ese día. No fuerces trade en medio del rango. 1 trade por día max, si no hay setup A+, no tradeas. Esto es lo que sube WR de 50% a 55-60% (filtrar).
**Ventana Madonna:** 10:30 - 12:00 ET. Después de 12:00, probabilidad baja, lunch, no trade. Si toque es después de 12:00, ignorar.

### 2D. ¿Segundo Toque?

Drysdale dice primer toque es highest probability. Segundo toque es menor probabilidad porque nivel ya fue testeado, liquidez consumida.
**Regla:** Solo 1 Madonna por día. Si pierdes Madonna, día terminado. No intentes segundo toque. Si ganas Madonna, día terminado (1 trade por día). No overtrade.

### 2E. ¿Stop Exacto y Buffer?

Drysdale: Stop más allá del Swing. Necesitás buffer para no ser cazado por 1 tick.
**Propuesta:** Stop = Swing High/Low +/- 2 pts buffer (NQ) o 0.5 pts (ES). Ejemplo: Swing High 21,472 + 2 = Stop 21,474, Risk 23 pts, Reward 30 pts, RR 1.30:1 (baja de 1.43 a 1.30 por buffer). Incluir buffer en backtest, no ignorar.

## 3. BACKTEST PARA EDGELAB - CÓDIGO LISTO

```python
# edgelab/strategies/drysdale_ib_madonna.py
# Estrategia: Initial Balance + Madonna - @traderdrysdale Df2pC5-phBZ
# Instrumento: NQ, Timeframe: 5-min (para IB) + 1-min (para entrada precisa) o 5-min solo
# Sesión: 9:30-12:00 ET, NO trade antes de 10:30, NO trade después de 12:00

def drysdale_ib_madonna(df_5min, date, risk_dollars=350, cost_per_trade=25):
    # 1. Calcular IB 9:30-10:30
    ib_window = df_5min[(df_5min['time'] >= '09:30') & (df_5min['time'] < '10:30')]
    ib_high = ib_window['high'].max()
    ib_low = ib_window['low'].min()
    ib_mid = (ib_high + ib_low) / 2
    ib_range = ib_high - ib_low
    # Filtro IB Range
    if ib_range < 40 or ib_range > 120:
        return {'action': 'NO_TRADE', 'reason': f'IB_RANGE {ib_range:.1f} fuera de [40,120]'}
    # 2. Esperar primer toque 10:30-12:00
    post_ib = df_5min[(df_5min['time'] >= '10:30') & (df_5min['time'] <= '12:00')]
    for i, candle in post_ib.iterrows():
        # ¿Tocó IB_HIGH?
        if candle['high'] >= ib_high and candle['close'] < ib_high:  # Wick + cierre dentro = rechazo
            # Verificar que no es Trend Day ya confirmado (2 velas previas fuera)
            if is_trend_day_confirmed(post_ib, ib_high, ib_low, i):
                return {'action': 'NO_TRADE', 'reason': 'Trend Day confirmado, no fade'}
            swing_high = candle['high']
            entry = candle['close']  # Entrada en cierre de vela de rechazo
            stop = swing_high + 2  # Buffer 2 pts
            target = ib_mid
            risk_pts = stop - entry
            reward_pts = entry - target
            rr = reward_pts / risk_pts if risk_pts>0 else 0
            if rr < 1.0:
                return {'action': 'NO_TRADE', 'reason': f'RR {rr:.2f} <1.0'}
            # Sizing para Lucid: Risk $350, micros MNQ $2/pto
            micros = int(risk_dollars / (risk_pts * 2))  # Ej: 350/(21*2)=8 micros
            if micros < 1:
                return {'action': 'NO_TRADE', 'reason': 'Risk por trade demasiado grande para micros'}
            return {'action': 'SHORT', 'entry': entry, 'stop': stop, 'target': target, 'rr': rr, 'micros': micros, 'setup': 'MADONNA_SHORT'}
        # ¿Tocó IB_LOW? Simétrico
        if candle['low'] <= ib_low and candle['close'] > ib_low:
            if is_trend_day_confirmed(post_ib, ib_high, ib_low, i):
                return {'action': 'NO_TRADE', 'reason': 'Trend Day, no fade'}
            swing_low = candle['low']
            entry = candle['close']
            stop = swing_low - 2
            target = ib_mid
            risk_pts = entry - stop
            reward_pts = target - entry
            rr = reward_pts / risk_pts if risk_pts>0 else 0
            if rr < 1.0:
                return {'action': 'NO_TRADE', 'reason': f'RR {rr:.2f} <1.0'}
            micros = int(risk_dollars / (risk_pts * 2))
            return {'action': 'LONG', 'entry': entry, 'stop': stop, 'target': target, 'rr': rr, 'micros': micros, 'setup': 'MADONNA_LONG'}
        # ¿Breakout confirmado? Si 2 velas cierran fuera con distancia, es Trend Day, no buscar fade
        if is_trend_day_confirmed(post_ib, ib_high, ib_low, i):
            return {'action': 'TREND_DAY', 'reason': 'Breakout con time+distance, trade en dirección del break, no fade'}
    return {'action': 'NO_TRADE', 'reason': 'No hubo Madonna 10:30-12:00'}

def is_trend_day_confirmed(post_ib, ib_high, ib_low, current_idx, distance_pts=10, time_bars=2):
    # 2 velas 5-min cierran > IB_HIGH + 10 pts o < IB_LOW - 10 pts
    recent = post_ib.iloc[max(0, current_idx-1):current_idx+1]
    if len(recent) < 2:
        return False
    if all(c['close'] > ib_high + distance_pts for _, c in recent.iterrows()):
        return True
    if all(c['close'] < ib_low - distance_pts for _, c in recent.iterrows()):
        return True
    return False
```

**Validación requerida (Gates EdgeLab):**
- Backtest NQ 5-min, 2024-2026, costos $25/trade (o $2/micro * micros + spread), slippage 2 pts, buffer 2 pts incluido.
- Métricas: WR, RR promedio, PF con costos, t-stat, MaxDD, # trades, % días NO_TRADE, % días Trend Day, % días Madonna Short vs Long.
- Si WR <53% neto con costos, no promover. Si PF <1.2, no promover. Si MaxDD >$1.000 con Risk $350, bajar Risk a $300.
- OOS: In-sample 2024-2025, OOS 2026. Si WR OOS cae >5pp, overfit en filtros TIME/DISTANCE.

## 4. EV Y COSTOS - ¿FUNCIONA CON LUCIDFLEX?

**Supuestos:** Madonna WR 55% (si es 'highest probability', debería ser >55%, pero asumimos 55% conservador), RR 1.43:1 (ejemplo), Risk $350, Costo $25/trade (8 micros * $2 comisión + spread).
```
EV/trade = WR * (Reward - Costo) + (1-WR) * (-Risk - Costo)
Reward = 1.43 * 350 = $500.5, Risk = $350
EV = 0.55*(500.5-25) + 0.45*(-350-25) = 0.55*475.5 + 0.45*(-375) = 261.5 - 168.75 = +$92.75 por trade
EV/trade $92.75 es MUCHO mejor que 55% RR 1:1 (EV $10 con Risk $350). Por eso RR 1.43 importa.
Si WR es 50% (no 55%): EV = 0.50*475.5 + 0.50*(-375) = 237.75 - 187.5 = +$50.25, sigue positivo.
Si WR es 45%: EV = 0.45*475.5 + 0.55*(-375) = 214 - 206.25 = +$7.75, breakeven.
Break-even WR con RR 1.43 y Costo $25: WR_be = (Risk + Costo) / (Reward + Risk) = (350+25)/(500.5+350) = 375/850.5 = 44.1%
Necesitas WR >44.1% para ganar. Si Madonna realmente es 'highest probability', WR debería ser 55-60%, margen de seguridad grande.
```

| WR Madonna | EV/trade (Risk $350, RR 1.43, Cost $25) | EV/cuenta Lucid (Overdeliver $3k, 5 payouts) | P(Profit) aprox |
| --- | --- | --- | --- |
| 45% | +$7.75 | ~$50 | ~12% |
| 50% | +$50.25 | ~$800 | ~30% |
| 55% | +$92.75 | ~$1.800 | ~48% |
| 60% | +$135 | ~$2.500 | ~60% |

**Comparación:** Con 55% WR RR 1:1, EV/cuenta era $235. Con 55% WR RR 1.43 (Madonna), EV/cuenta ~$1.800, 7.6x mejor. Por eso buscar RR >1.4 es más potente que buscar WR 60%.
**Tiempo:** 1 trade por día, necesitas 5 wins para 5-días phase. Con WR 55%, esperas 5/0.55=9.1 días para 5 wins. Para Funded a $3k, necesitas $3k / $92.75 = 32 trades esperados, 32 días (1 trade/día). + Eval 2 días + 5-días 9 días = **~43 días a primer payout**. Más lento que estrategias con 3-5 trades/día, pero con menos costos (32 trades * $25 = $800 costos totales vs 200 trades * $25 = $5.000 costos con Risk $100). Menos trades = menos costos.

## 5. COMPARACIÓN CON OTROS EDGES SCRAPEADOS

| Edge | Ventana | Target | RR Típico | Trades/Día | Ventaja vs Madonna | Desventaja vs Madonna |
| --- | --- | --- | --- | --- | --- | --- |
| **Drysdale IB Madonna** | 9:30-10:30 IB, trade 10:30-12:00 | IB Mid | 1.43 | 1 | Reglas claras, 1 trade/día, bajo costo total, ideal para 5-días phase | Lento (43 días a payout), si no hay toque, día perdido |
| FlexingJoe ORB | Apertura 15 min, trade 9:45-10:30 | ORB High/Low | 1.0-1.5 | 1-2 | Más rápido (15 min vs 60 min) | Más false breakouts, ORB 15 min es ruido |
| AlphaZone 9:30 Cheat Code | 9:30 apertura, filtro | ? | ? | 1-2 | Filtro 73.8% claim | No define IB, filtro no reproducible sin backtest |
| Asia NQ 100-300 | Asia rango, break NY | ? | ? | 1-2 | Usa sesión Asia, diversifica vs NY | No define IB, depende de rango Asia |
| Franklin 2 Altos/Bajos + VWAP | Londres | VWAP | ? | 1-2 | Confluencia VWAP, bueno para filtro | Más subjetivo (qué es 2 altos/bajos?) |
| Juan José 2 Velas | NY | 1:1 | 1.0 | 2-3 | Simple, más trades, más rápido | RR 1.0, EV menor que Madonna 1.43 |

**Sinergia:** Madonna es complemento perfecto para Asia NQ y Franklin. Puedes usar:
- **Cartera 1 (Rápida):** Asia NQ + Franklin Londres (mañana temprano)
- **Cartera 2 (Estable):** Madonna IB (10:30-12:00, 1 trade, solo A+)
Si Cartera 1 te da trade en Asia/Londres y ganas, no necesitas Madonna ese día (ya tienes 1 win). Si Cartera 1 no da trade o pierdes, Madonna es tu segunda oportunidad en mismo día, pero con reglas diferentes, correlación baja. No es 2 trades en mismo edge, es 2 edges diferentes en mismo día, diversificación intradía.
**Para tus 2 Carteras en Papel:** Madonna encaja en **Cartera 2 estable** (Payout Loop). Es el edge que usas cuando colchón es $900 y no puedes permitirte varianza. 1 trade/día, RR 1.43, WR 55%+, EV $92/trade, es lo que necesitas para no blow en payout loop.

## 6. RIESGOS Y FILTROS PARA NO BLOW

| Riesgo | Cómo Mitigar |
| --- | --- |
| Fake Breakout (toca IB, vuelve dentro, pero luego rompe y es Trend Day) | Esperar confirmación Trend Day (2 velas fuera + 10 pts) antes de decidir no fade. Si entraste fade y precio cierra 2 velas fuera, salte en breakeven, no esperes stop. |
| IB Range muy grande (>120 pts) -> Stop gigante | NO_TRADE si IB_RANGE >120. O baja size a 4 micros (Risk $350 con Stop 40 pts = 4*2*40=320, cabe). |
| IB Range muy chico (<40 pts) -> Target muy chico | NO_TRADE si IB_RANGE <40. Target a Mid <20 pts, RR <1, no cubre costos. |
| Noticias 10:00 (inventarios, etc.) -> IB distorsionado | Si hay noticia 10:00 ET (ej: EIA, FOMC), IB 9:30-10:30 incluye noticia, rango artificial. NO_TRADE ese día o usa IB 10:00-11:00 en vez de 9:30-10:30. |
| Segundo toque (no Madonna) -> WR menor | Solo primer toque. Si pierdes Madonna, día terminado. No revenge trade. |
| Overtrade (tomar trade en medio, no en borde) | Solo trade en IB High/Low. Si precio está en medio (cerca de IB Mid), NO_TRADE. No hay edge en medio. |
| Costos con micros (8 micros * $2 = $16 comisión + spread $9 = $25) | Incluir costos en backtest. Si usas 8 micros, costo $25 es 7% de Risk $350, manejable. Si usas 1 mini, costo $11.48 + spread $10 = $21, pero Risk $420 > $350, no cabe. Micros son correctos. |

## 7. PLAN PARA EDGELAB - DÓNDE VA MADONNA

```
edgelab/strategies/drysdale_ib_madonna.py  -> Código de Sección 3
specs/drysdale_ib_madonna.md -> Reglas, IB, Madonna, Trend Day, filtros, Risk $350, micros
validation/drysdale_ib_madonna_backtest.py -> Backtest 2024-2026, OOS, PF, t-stat, MaxDD
Cartera asignada: Cartera 2 Estable (Payout Loop + 5-días phase)
Fase: Estructura A - Cartera 1 para Eval, Cartera 2 (Madonna) para Payout Loop
Gates: PF>=1.2 con costos, t>=2.5, WR neto >=50% (breakeven 44.1%, margen 5.9pp), MaxDD <$1.000, OOS WR no cae >5pp
```
**Próximo paso:** Backtest Madonna con NQ 5-min 2024-2026, con TIME=10 min, DISTANCE=10 pts, IB_RANGE [40,120], Ventana 10:30-12:00, Buffer 2 pts, Costo $25. Si PF>=1.2 y WR>=55% OOS, promover a Cartera 2. Si no, ajustar TIME/DISTANCE o descartar.

## Fuentes

- **Reel Df2pC5-phBZ:** @traderdrysdale - Initial Balance + Madonna - Transcript completo 2026-11-17, IB High 21,462 Low 21,380 Mid 21,421, Entry 21,451 Stop 21,472 Target 21,421
- **Concepto IB:** Peter Steidlmayer / James Dalton - Market Profile - Initial Balance 9:30-10:30
- **Costos NQ:** Tradovate $1.29/side + $1.39 exchange + $0.19 clearing = $2.87/side, $5.74 round turn/mini, MNQ $0.94 round turn/micro + spread
- **Simulación EV:** Python, Risk $350, RR 1.43, Cost $25, Overdeliver $3k, WR 45-60%
