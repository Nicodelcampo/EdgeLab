# Roadmap Operativo Multi-Frente (Arquitectura Paralela de Extraccion y Capitalizacion)

> **Principio rector:** No es una escalera lineal donde una estrategia espera a otra, sino una **mesa multi-frente simultanea** donde cada motor opera en el vehiculo regulatorio/prop que maximiza su payoff asimetrico y minimiza su friccion.

---

## 1. Los 4 Frentes Simultaneos de la Mesa

| Frente | Vehiculo / Plataforma | Cartera / Modulos Asignados | Rol Financiero en el Ecosistema |
|---|---|---|---|
| **Frente 1 — Motor Primario Futuros EOD** | `NinjaTrader 8` (`LucidFlex 150K/50K`, `Tradeify Select Flex 150K/50K`, `Topstep NoAct 50K`, `FundedNext 50K` solo en promo) | **Eval:** `SpeedEval` (`T_Only` en Lucid/Tradeify) o `Core5_R25` (en Topstep mensual)<br>**Funded:** `Core5_AltaConv` con `R_ATR25` (`Netting`, `MaxOpenR=3.0`, flat `16:40 ET`, `16:05 ET` en Topstep) | **Generador masivo de flujo de caja** (`~29 ops/mes`, cero costo de activacion, trailing EOD puro). |
| **Frente 2 — Motor CFD Static-DD Intradia** | `cTrader` / `MetaTrader 5` (`FTMO Swing 100K`, `The5ers HighStakes 100K`) | `Core5_R25` en `US100` (`0.981 pts` spread RTH, `\$0` comm) + Satelite `US500/ES` (`0.35 pts`, `+21.2 R` OOS) + **`HardFlatten = 16:40 ET` (Cero Swap Nocturno)** + `FundedDdBrake` (`-4.5% -> 0.5x`) | **Estabilizador de DD estatico sin arrastre de swaps**: suma diversificacion `US100 + US500` con friccion RTH 36% menor al futuro y cobra ciclos quincenales sin pagar el swap `8%-10%` anual de CFD. |
| **Frente 3 — Manga Ortogonal Multi-Activo** | `NinjaTrader 8` / `MT5` (`cartera_20261116`: `8` reglas `NQ, ES, YM, RTY, CL, MGC`) | `CVGAP-ES-C`, `U1-RACIMOS-GRILLA-NQ`, `CONF-CVR-CFD-NQ-R`, `U1-ZONAS-BT2-ES/NQ`, `PREAPERTURA-NQ` (peso `0.5x`), `U1-ORO-GRILLA` (`1R = \$200` en 50K) | **Descorrelacion estructural (`rho ~= -0.02`)**: `+52 ops/mes` que sostienen pagos cuando el Nasdaq intradia entra en compresion. |
| **Frente 4 — Boveda Personal sin Topes** | Broker regulado propio (`IBKR / AMP` en Futuros Micros `MNQ/MES`, `0` swap) | `30%` de barrido (*sweep*) automatico sobre cada nuevo maximo de caja prop -> `Core5_R25 + ES + O_noWed (0 swap en MNQ) + cartera_20261116` (`1R = 0.75%` compuesto) | **Conversion de opciones fragiles en patrimonio perpetuo**: unico lugar donde `O` Overnight captura alfa real sin swap CFD, inmune a cierres de prop firms. |

---

## 2. Dimensionamiento Simultaneo por Presupuesto de Riesgo (Cifras Reales Respetando Topes Legales por Hogar)

### Nivel E1 — Capital Semilla (`Presupuesto recomendado: \$3,500 - \$4,500`)
- **Composicion simultanea**: `2x LucidFlex 50K` + `2x Tradeify Select Flex 50K` (`SpeedEval -> Core5_R25`, escalonadas cada `3` dias) + `1x The5ers HighStakes 100K` (`US100 + US500` intradia sin swap).
- **Colchon de caja requerido (`p90` / `p95` HOLDOUT)**: `\$3,234` / `\$4,011`
- **Neto 12m esperado**: `\$37,560` (`REP 100%`) | `\$22,556` (`HOLDOUT`, mediana `\$19,629`, `P(>0) = 86.8%`) | `\$18,506` (`REP 60%` estres)
- **Riqueza acumulada 24m (HOLDOUT)**: `\$55,777` (`Ratio Neto12/|p10| = 6.97x`)

### Nivel E2 — Escala Balanceada (`Presupuesto recomendado: \$8,500 - \$11,000`)
- **Composicion simultanea**: `2x LucidFlex 150K` + `2x Tradeify Select Flex 150K` + `1x FTMO Swing 100K` + `1x The5ers HighStakes 100K`.
- **Colchon de caja requerido (`p90` / `p95` HOLDOUT)**: `\$7,807` / `\$9,399`
- **Neto 12m esperado**: `\$72,204` (`REP 100%`) | `\$41,342` (`HOLDOUT`, mediana `\$33,495`, `P(>0) = 82.8%`) | `\$31,158` (`REP 60%` estres)
- **Riqueza acumulada 24m (HOLDOUT)**: `\$105,348` (`Ratio Neto12/|p10| = 5.29x`)

### Nivel E3 — Mesa Institucional Media (`Presupuesto recomendado: \$15,000 - \$19,000`)
- **Composicion simultanea**: `3x LucidFlex 150K` + `3x Tradeify Select Flex 150K` + `2x Topstep NoAct 50K` + `2x FTMO Swing 100K` + `2x The5ers HighStakes 100K`.
- **Colchon de caja requerido (`p90` / `p95` HOLDOUT)**: `\$14,325` / `\$17,244`
- **Neto 12m esperado**: `\$138,260` (`REP 100%`) | `\$77,152` (`HOLDOUT`, mediana `\$62,299`, `P(>0) = 83.4%`) | `\$60,732` (`REP 60%` estres)
- **Riqueza acumulada 24m (HOLDOUT)**: `\$200,510` (`Ratio Neto12/|p10| = 5.39x`)

### Nivel E4 vs E5 — Tope Legal Multi-Prop con Freno Dinamico de Caja + Boveda Personal (`Recomendado para Maximizacion Controlada`)
- **Composicion simultanea al tope legal por hogar (`20` cuentas)**:
  `5x LucidFlex 150K` (tope Lucid) + `5x Tradeify 150K` (tope Tradeify) + `3x Topstep 50K` + `2x FundedNext 50K` + `3x FTMO Swing 100K` (`300K` de `400K` cap FTMO) + `2x The5ers 100K`.
- **Sin freno dinamico (`E4`)**:
- **Colchon de caja requerido (`p90` / `p95` HOLDOUT)**: `\$22,341` / `\$26,720`
- **Neto 12m esperado**: `\$202,174` (`REP 100%`) | `\$114,665` (`HOLDOUT`, mediana `\$93,948`, `P(>0) = 83.2%`) | `\$88,176` (`REP 60%` estres)
- **Riqueza acumulada 24m (HOLDOUT)**: `\$289,519` (`Ratio Neto12/|p10| = 5.13x`)
- **Con Freno Dinamico de Caja (`-\$7,500` pausa compras de expansion / `-\$3,500` reanuda) + `30%` Sweep a Boveda Personal (`E5`)**:
- **Colchon de caja requerido (`p90` / `p95` HOLDOUT)**: `\$10,725` / `\$11,716`
- **Neto 12m esperado**: `\$211,218` (`REP 100%`) | `\$121,457` (`HOLDOUT`, mediana `\$98,958`, `P(>0) = 86.4%`) | `\$97,211` (`REP 60%` estres)
- **Riqueza acumulada 24m (HOLDOUT)**: `\$309,411` (`Ratio Neto12/|p10| = 11.32x`)
- **Capital acumulado dentro de la Boveda Personal propia a los 24m (`E5` HOLDOUT)**: **`\$102,220`** libres de reglas prop.

---

## 3. Reglas Operativas Estrictas de Control de Riesgo y Anti-Ban

1. **Escalonamiento obligatorio (`Stagger = 3 a 5 sesiones`)**: jamas iniciar ni resetear todas las evaluaciones el mismo lunes. Desfasar las compras `3` dias habiles en Futuros y `5` dias en CFD reduce la correlacion de quema en rachas adversas y evita alertas de *copy-trading* sincronizado al milisegundo entre firmas distintas.
2. **Sensibilidad de `T` (`ORB15`) al reloj `09:30:00` en CFD**: sincronizar reloj NTP de la VPS (`< 50 ms` de deriva) y operar siempre con `CheckStopsOnEveryTick = true` en `cTrader`/`MT5`. Si el broker CFD presenta congelamiento de cotizacion en `09:30:00-09:30:10`, reducir el peso de `T` al `50%` (`0.35`) en CFD manteniendo `100%` en `NT8` CME.
3. **Exclusion de `O` Overnight en CFD por Swaps (`8%-10%` anual + `3x` miercoles)**: la auditoria demostro que el financiamiento nocturno CFD (`~6.5 pts/noche` y `~19.5 pts` los miercoles en `US100`) absorbe casi la totalidad de la esperanza matematica de `O` (`REP R/op = +0.006`, `HOLDOUT = -1.41 R`). Por ello, los bots `cTrader`/`MT5` se mantienen **100% intradia (`HardFlatten = 16:40 ET`)**, reservando `O` exclusivamente para futuros `MNQ` en la Boveda Personal (cero swap).
4. **Protocolo de Freno en Tres Capas**:
   - *Nivel Cuenta Funded CFD*: `EnableFundedDdBrake = true` a `-4.5%` desde HWM -> recorta `1R` al `50%` automaticamente en el bot (`cTrader` y `MT5`).
   - *Nivel Caja de Ecosistema*: si el flujo neto de caja cae `-\$7,500` desde su maximo historico (o `-30%` del colchon inicial en niveles `E1/E2`), **congelar nuevas compras de evaluaciones de expansion** y dejar operando unicamente las cuentas ya fondeadas y el nucleo base hasta recuperar `-\$3,500`.
   - *Exclusiones permanentes*: **Cero** cuentas en `Apex` y `AlphaFutures` (prohibicion de bots), **cero** `TakeProfitTrader` intradia trailing con `Core5`, y **cero** compras retail sin codigo promo (`>= 25%-30%` off) en `Lucid`, `Tradeify` y `FundedNext`.
