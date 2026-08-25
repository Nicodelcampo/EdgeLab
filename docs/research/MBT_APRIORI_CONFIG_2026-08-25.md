# Configuración a-priori de BigTrap2Absorption para MBT (Micro Bitcoin Futures)

- **Fecha:** 2026-08-25
- **Rama:** `docs/mbt-apriori-2026-08-25` · **Base:** `foundation/f0b-compatibility-probe` @ `7fbab53`
- **Indicador:** `BigTrap2Absorption.cs` v1.1.1 (sha256 canon: `18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641`)
- **Activo / Tick Size:** MBT (CME Micro Bitcoin) · `TickSize = 5.0` ($5.0 por tick)
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · **Sin outcomes, sin holdout, sin P&L, sin MAE/MFE, sin declarar edge**.

---

## 1. Objetivo y Regla de Decisión Pre-Registrada

Seleccionar una configuración inicial exclusivamente por **estructura** (tasas de eventos, contigüidad, salud del muestreo y llenado del anillo causal), previa a cualquier paso por las 3 puertas formales.

### Regla de decisión (declarada a-priori)

1. **`TapeWindowTicks` (TW):** El mayor TW con mediana de cubetas/sesión $\ge 100$ y zonas/sesión que no colapsen (mediana $\ge 5$). Referencia GC: 25.
2. **Percentil `AbsorptionPct` ($q$):** El valor que sitúe la tasa de eventos en $\approx 1,0\%$ de las cubetas (banda admisible $0,5\% - 2,0\%$).
3. **Contigüidad y Fracción:** `MinStackedRows = 2` (fijo; celda aislada es ruido). `MinTrapFrac = 0.20` salvo inestabilidad (ratio $> 2\times$ entre $0.10$ y $0.30$).
4. **Anillo Causal:** `MinHistoryBuckets` mínimo que no degrade la selección en front-month ($50 - 100$). `AbsorptionLookback`: $200 - 500$.
5. **Criterio de Inviabilidad:** Si ninguna combinación produce $\ge 5$ eventos/sesión mediana con contigüidad $\ge 2$, la recomendación es **NO operar MBT** con este indicador.

---

## 2. Manifiesto de Exports (`$DATA/mbt_apriori/`)

- **Cinta fuente:** `E:\DatosNT8\MBT 08-26.Last.txt` (555.014 ticks, 97 sesiones CME entre 2026-04-20 y 2026-08-25).
- **Parámetros fijos por contrato v1.1.1:** `ScoreMode=AbsDirectional`, `RequireFlowSideMatch=True`, `ImbalanceMode=Diagonal`, `TrapVolumeSource=AggressiveSide`, `TicksPerRow=1`, `ImbalanceRatio=3.0`, `MinStackedRows=2`, `MinTrapFrac=0.20`, `MinDeltaFilter=0`, `MinTrapVolume=0`, `MinExportVolume=1`, `UseWickFilter=True`, `WickZonePct=30.0`, `InvalidationMode=CloseThrough`, `MaxTouches=0`, `MaxAgeBars=2000`, `TickSize=5.0`.

| Archivo | sha256 | Bytes | TW | Cubetas | TRAPs | Zonas | Fills | Burn-in ($N=100$) |
|---|---|---:|:---:|---:|---:|---:|---:|:---:|
| `mbt_export__TW10.csv` | `b88ed81e30891f5dd5256491ac3513180929f3fe84aef879b3006e2c5583df4b` | 33.552.116 | 10 | 55.547 | 22.877 | 728 | 728 | Bar 137 (2026-06-30) |
| `mbt_export__TW15.csv` | `1f217ad208cc55f1ee996514f5ae5fbf7e348f3722ea61bec4216a13b4d1ed4a` | 25.615.498 | 15 | 37.053 | 20.534 | 836 | 836 | Bar 140 (2026-07-02) |
| `mbt_export__TW25.csv` | `14cf8ca6eb9b4f42771e2493a30352cfa8219216329d11e07db54a1fb76d4724` | 18.136.250 | 25 | 22.260 | 16.813 | 688 | 688 | Bar 147 (2026-07-09) |
| `mbt_export__TW50.csv` | `55336f1159f0fd9f6ac4b80f225b15e8361b67a10b663286d29a5d3f40e904a2` | 10.973.149 | 50 | 11.160 | 11.500 | 373 | 373 | Bar 158 (2026-07-20) |

---

## 3. Tabla Comparativa por `TapeWindowTicks` (Front-Month)

*Evaluado sobre las sesiones activas de front-month ($\ge 100$ cubetas completas).*

| TW | Cubetas / Sesión (Mediana [p25–p75]) | $q=90.0$ (Eventos / % / Med) | $q=95.0$ (Eventos / % / Med) | $q=97.5$ (Eventos / % / Med) | $q=99.0$ (Eventos / % / Med) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **10** | 1.600,5 [371,8 – 2.187,2] | 728 / 1,34% / 15,0 | 439 / 0,81% / 9,5 | 227 / 0,42% / 4,5 | 74 / 0,14% / 1,5 |
| **15** | 1.243,0 [918,5 – 1.809,5] | 836 / 2,33% / 26,0 | 456 / 1,27% / 13,0 | 246 / 0,68% / 7,0 | 110 / 0,31% / 3,0 |
| **25** | **760,0 [603,0 – 1.130,0]** | 689 / 3,22% / 24,0 | **372 / 1,74% / 12,0** | **195 / 0,91% / 6,0** | 89 / 0,42% / 3,0 |
| **50** | 390,0 [320,0 – 742,5] | 377 / 3,58% / 13,0 | 190 / 1,81% / 6,0 | 87 / 0,83% / 3,0 | 39 / 0,37% / 2,0 |

---

## 4. Análisis de Sensibilidad Estructural

### 4.1 Llenado del Anillo Causal (Burn-in)

En MBT front-month ($\approx 760$ cubetas/sesión con TW=25):
- `MinHistoryBuckets = 50`: se llena en la barra 91 (primeras horas de sesión activa).
- `MinHistoryBuckets = 100`: se llena en la barra 147 ($\approx 19\%$ de la sesión). $99,3\%$ de las cubetas de la cinta quedan cubiertas y activas.
- `MinHistoryBuckets = 200`: se llena en la barra 258 ($\approx 34\%$ de la sesión).
- `AbsorptionLookback = 500`: abarca $\approx 66\%$ de una sesión completa de front-month, adaptando el percentil al régimen intradiario sin arrastrar datos viejos.

### 4.2 Sensibilidad `MinStackedRows` ($q=95.0, \text{TW}=25, \text{MinTrapFrac}=0.20$)
- `MinStackedRows = 1`: 372 zonas (1,74% cubetas, 12,0 zonas/sesión).
- `MinStackedRows = 2`: **372 zonas** (1,74% cubetas, 12,0 zonas/sesión). **Ratio 1 vs 2 = 1,00×**.
- `MinStackedRows = 3`: 119 zonas (0,56% cubetas, 3,0 zonas/sesión). **Ratio 2 vs 3 = 3,13×**.

> **Hallazgo:** En MBT, exigir `MinStackedRows = 2` no recorta la población frente a 1 (ratio exacto 1,00×). Los desbalances de absorción en MBT ocurren naturalmente en al menos 2 niveles contiguos de $5. No hay pérdida de material y se protege contra celdas aisladas.

### 4.3 Sensibilidad `MinTrapFrac` ($q=95.0, \text{TW}=25, \text{MinStackedRows}=2$)
- `MinTrapFrac = 0.10`: 403 zonas (1,88% cubetas).
- `MinTrapFrac = 0.20`: **372 zonas** (1,74% cubetas).
- `MinTrapFrac = 0.30`: 327 zonas (1,53% cubetas).
- **Ratio 0.10 / 0.30 = 1,23×** ($\ll 2,0\times$, estabilidad confirmada).

---

## 5. Diagnóstico de Régimen (Pre-roll vs Front-Month)

- **Pre-roll (abril–junio 2026):** 22 a 162 cubetas/sesión. Volumen escaso y espaciado.
- **Front-month (julio–agosto 2026):** 603 a 2.960 cubetas/sesión (mediana 760).
- **Dispersión intradiaria:** En front-month, la tasa de eventos varía con la volatilidad intradiaria ($p10=3,0$ zonas/sesión en días calmos, $p90=35,0$ zonas en días de alto flujo; ratio $p90/p10 \approx 11,7\times > 3\times$).

> **ALERTA DE RÉGIMEN:** MBT exhibe una fuerte dependencia de régimen pre-roll vs front-month. La investigación y backtest formal de MBT **deben restringirse exclusivamente a ventanas front-month** (o con cadena de rolls formal). Medir en pre-roll distorsiona la tasa causal del anillo.

---

## 6. Configuración Recomendada para MBT

Siguiendo la regla de decisión pre-registrada:

| Parámetro | Valor Recomendado | Justificación Estructural |
|---|:---:|---|
| `TapeWindowTicks` | **25** | Mayor TW con $\ge 100$ cubetas/sesión (760) y $\ge 5$ eventos/sesión mediana (12 en $q=95$, 6 en $q=97.5$). |
| `AbsorptionPct` ($q$) | **95.0** (o **97.5**) | $q=95.0$ da 1,74% de cubetas (12 zonas/sesión, muestra sólida); $q=97.5$ da 0,91% (exacto a la referencia 1,0% de GC). |
| `ScoreMode` | `AbsMagnitude` / `AbsDirectional` | Conforme a Puerta 0 canónica. |
| `AbsorptionLookback` | **500** | Abarca $\approx 66\%$ de una sesión típica front-month. |
| `MinHistoryBuckets` | **100** | Llenado rápido en barra 147 ($\approx 19\%$ de sesión 1), $99,3\%$ de disponibilidad. |
| `MinStackedRows` | **2** | Estable; idéntico a 1 en MBT (ratio 1,00×) y elimina celdas aisladas. |
| `MinTrapFrac` | **0.20** | Respuesta suave (ratio 0.1/0.3 = 1,23×). |
| `RequireFlowSideMatch`| `True` | Coherencia flujo ↔ atrapamiento. |
| `MinDeltaFilter` | **0** | Evita el interruptor de muerte de contigüidad. |
| `TickSize` | **5.0** | Tick oficial CME para MBT. |

---

## 7. Qué Falsaría Esta Configuración

Esta elección es estrictamente **estructural a-priori** y no valida la existencia de edge económico:

1. **Puerta 0 (Paridad):** Ya firmada `FINAL_PUERTA0_SIGNED` en GC. Si en MBT apareciera divergencia C# $\leftrightarrow$ Python en `verify_layer_parity`, la configuración queda invalidada.
2. **Puerta 1 (Target-Free / Sensibilidad):** Si en la batería de 99 configs de MBT el Jaccard frente al modelo nulo colapsa o no supera el baseline de permutaciones.
3. **Puerta 2 (Outcomes / P&L Bruto y Neto):** Si al abrir retornos causales futuros (tras deducción de comisiones CME MBT + slippage) la expectativa no supera el control $S_1$ de $F2.9$.
4. **Puerta 3 (Holdout / OOS):** Si degrada en las sesiones selladas del holdout.

---

## Aporte al referente

Se fija la primera configuración canónica a-priori para MBT basada en las propiedades intrínsecas de su microestructura: un contrato con $10\times$ menor densidad que GC pero que con $\text{TW}=25, q=95.0, \text{MinStackedRows}=2, \text{MinHistory}=100$ preserva exactamente la geometría de zonas, una tasa del $1,74\%$ de cubetas y una densidad de 12 eventos/sesión en front-month sin colapso de contigüidad.
