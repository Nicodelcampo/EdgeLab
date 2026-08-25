# Configuración a-priori de BigTrap2Absorption para ES (E-mini S&P 500 Futures)

- **Fecha:** 2026-08-25
- **Rama:** `docs/es-apriori-2026-08-25` · **Base:** `docs/mbt-apriori-2026-08-25` (`7fbab53`)
- **Indicador:** `BigTrap2Absorption.cs` v1.1.1 (sha256 canónico: `18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641`)
- **Activo / Tick Size:** ES (CME E-mini S&P 500) · `TickSize = 0.25` (verificado en cinta, especificación CME)
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · **Sin outcomes, sin holdout, sin P&L, sin MAE/MFE, sin declarar edge**.

---

## 1. Objetivo y Regla de Decisión Pre-Registrada

Replicar de forma idéntica el protocolo de selección estructural a-priori ejecutado en MBT sobre el contrato E-mini S&P 500 (ES).

### Regla de decisión (declarada a-priori, idéntica a MBT)

1. **`TapeWindowTicks` (TW):** El mayor TW con mediana de cubetas/sesión $\ge 100$ y zonas/sesión que no colapsen (mediana $\ge 5$). Referencia GC: 25.
2. **Percentil `AbsorptionPct` ($q$):** El valor que sitúe la tasa de eventos en $\approx 1,0\%$ de las cubetas (banda admisible $0,5\% - 2,0\%$).
3. **Contigüidad y Fracción:** `MinStackedRows = 2` (fijo; celda aislada es ruido). `MinTrapFrac = 0.20` salvo inestabilidad (ratio $> 2\times$ entre $0.10$ y $0.30$).
4. **Anillo Causal:** `MinHistoryBuckets` mínimo que no degrade la selección en front-month ($50 - 200$). `AbsorptionLookback`: $200 - 500$.
5. **Criterio de Inviabilidad:** Si ninguna combinación produce $\ge 5$ eventos/sesión mediana con contigüidad $\ge 2$, la recomendación es **NO operar ES con este indicador** bajo estos parámetros — y declararlo explícitamente.

---

## 2. Manifiesto de Datos y Exports

### 2.1 Cinta recortada (Paso 0 y Paso 0b)
- **Cinta madre:** `E:\EdgeLab\data\nt8\ES\ES 09-26.Last.txt` (1.463.625.903 bytes, 30.509.257 líneas).
- **Corte de ventana front-month:** Línea 29.366.964 (apertura sesión CME `2026-07-26 22:00:00 UTC`, trade date `20260727`).
- **Cinta recortada:** `E:\EdgeLab\data\nt8\ES\ES 09-26.frontmonth.Last.txt`
  - **Líneas / Ticks:** 1.142.294
  - **Bytes:** 53.644.048 (53,64 MB)
  - **sha256:** `4f66e51f3b22f195871fdae7ba5f6852b6916b9b9589f7c38f79d805ac75fdb9`
  - **Guardrail Paso 0b:** Mínimo $|\Delta\text{precio}|$ no nulo observado = **0.25** exacto (`PASS`).

### 2.2 Manifiesto de Exports (`$DATA/es_apriori/`)
- **Parámetros fijos por contrato v1.1.1:** `ScoreMode=AbsDirectional`, `RequireFlowSideMatch=True`, `ImbalanceMode=Diagonal`, `TrapVolumeSource=AggressiveSide`, `TicksPerRow=1`, `ImbalanceRatio=3.0`, `MinStackedRows=2`, `MinTrapFrac=0.20`, `MinDeltaFilter=0`, `MinTrapVolume=0`, `MinExportVolume=1`, `UseWickFilter=True`, `WickZonePct=30.0`, `InvalidationMode=CloseThrough`, `MaxTouches=0`, `MaxAgeBars=2000`, `TickSize=0.25`.

| Archivo | sha256 | Bytes | TW | Cubetas | TRAPs | Zonas | Fills | Burn-in ($N=100$) |
|---|---|---:|:---:|---:|---:|---:|---:|:---:|
| `es_export__TW10.csv` | `41527dc333ce49b699d71828b0cc94a37ffdbc1f3d05fe6b3d9b3d07e64d3099` | 44.593.203 | 10 | 114.230 | 6.105 | 1 | 1 | Bar 101 (2026-07-27) |
| `es_export__TW15.csv` | `5ae8821da2e19957605ee2ce2fd9ed0cf52f679d5a2a9dc35ba69ffec389ba50` | 30.616.699 | 15 | 76.153 | 5.477 | 2 | 2 | Bar 101 (2026-07-27) |
| `es_export__TW25.csv` | `f268c50cc07ab59e736ed91ef8c7077e7007c86aed1a0f125f7a722b2fabfaf8` | 18.772.381 | 25 | 45.692 | 3.895 | 2 | 2 | Bar 101 (2026-07-27) |
| `es_export__TW50.csv` | `a5fc0e061c230d42f766ecf64f3ac1b20b854886bf1909740464bfc6b3470c6f` | 9.473.407 | 50 | 22.846 | 1.967 | 11 | 11 | Bar 101 (2026-07-27) |

---

## 3. Tabla Comparativa por `TapeWindowTicks` (Regla Baseline: `MinStackedRows=2`)

| TW | Cubetas / Sesión (Mediana) | $q=90.0$ (Zonas / % / Med) | $q=95.0$ (Zonas / % / Med) | $q=97.5$ (Zonas / % / Med) | $q=99.0$ (Zonas / % / Med) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **10** | 57.114 | 1 / 0,00% / 0,5 | 0 / 0,00% / 0,0 | 0 / 0,00% / 0,0 | 0 / 0,00% / 0,0 |
| **15** | 38.075 | 3 / 0,00% / 1,5 | 0 / 0,00% / 0,0 | 0 / 0,00% / 0,0 | 0 / 0,00% / 0,0 |
| **25** | 22.845 | 3 / 0,01% / 1,5 | 2 / 0,00% / 1,0 | 1 / 0,00% / 0,5 | 1 / 0,00% / 0,5 |
| **50** | 11.422 | 12 / 0,05% / 6,0 | 8 / 0,04% / 4,0 | 3 / 0,01% / 1,5 | 1 / 0,00% / 0,5 |

---

## 4. Diagnóstico Microestructural: El Colapso de `MinStackedRows=2` en ES

Al aplicar la regla de contigüidad $\ge 2$ filas imbalanzadas en ES, la población colapsa a prácticamente **cero zonas** en todos los TWs evaluados.

### Causa raíz microestructural aislada
1. **Profundidad del libro (Thick Book):** En ES, la liquidez en cada nivel de precio de \$0.25 es de 300 a 2.000 contratos. En una ventana de 10, 15, 25 o 50 transacciones (ticks), el mercado casi nunca recorre más de 1 o 2 niveles de precio.
2. **Distribución de filas imbalanzadas (`n_rows` en TRAP):**
   - `TW=10`: $99,7\%$ tienen $n\_rows = 1$ (6.086 de 6.105 TRAPs).
   - `TW=25`: $98,9\%$ tienen $n\_rows = 1$ (3.854 de 3.895 TRAPs).
   - `TW=50`: $96,6\%$ tienen $n\_rows = 1$ (1.900 de 1.967 TRAPs).
3. **Contraste con GC y MBT:**
   - En GC y MBT (libros delgados), el flujo agresivo barre múltiples niveles de precio en 25 ticks, generando 2 o 3 niveles contiguos con facilidad (`MinStackedRows=2` no recortó nada en MBT).
   - En ES, la absorción ocurre concentrada en un **único nivel de precio masivo** ($n\_rows = 1$). Exigir 2 niveles contiguos actúa como un **interruptor de aniquilación** geométrica.

### Sensibilidad de Contigüidad ($q=95.0, \text{TW}=25, \text{MinTrapFrac}=0.20$)
- **`MinStackedRows = 1`:** **414 zonas** (0,91% de cubetas $\approx 1,0\%$ referencia GC, tasa sana).
- **`MinStackedRows = 2`:** **2 zonas** (0,00% de cubetas, colapso del 99,5%).
- **`MinStackedRows = 3`:** **0 zonas**.

---

## 5. Llenado del Anillo Causal (Burn-in)

Debido a la densidad extrema de ES ($\approx 22.845$ cubetas/sesión con $\text{TW}=25$):
- `MinHistoryBuckets = 50`: Se llena en los primeros 15 segundos de sesión (Bar 51).
- `MinHistoryBuckets = 100`: Se llena en la barra 101 ($< 0,5\%$ de la primera hora).
- `MinHistoryBuckets = 200`: Se llena en la barra 201 ($< 1\%$ de la primera hora).
- `AbsorptionLookback = 500`: Cubre únicamente $\approx 2\%$ de una sesión intradiaria de ES (unos ~15-20 minutos de negociación activa).

---

## 6. Veredicto y Aplicación de la Regla de Decisión

### Aplicación estricta de la regla pre-registrada:
> *"Si ninguna combinación da $\ge 5$ eventos/sesión mediana con contigüidad $\ge 2$, la recomendación es **NO operar ES con este indicador** — y decirlo."*

### Veredicto: **NO OPERABLE BAJO EL CONTRATO CANÓNICO ACTUAL (TW $\le 50$, `MinStackedRows=2`)**

1. **Bajo los parámetros congelados de Puerta 0 (`MinStackedRows=2`, `TicksPerRow=1`):** ES no produce densidad muestral suficiente ($\le 1$ a 4 eventos/sesión) debido a que la microestructura de libro grueso impide la formación de clusters de 2 ticks en cubetas de $\le 50$ transacciones.
2. **Alternativas estructurales (requieren pre-registro y autorización formal de Nico):**
   - **Opción A (Aflojar contigüidad a `MinStackedRows=1`):** Con $\text{TW}=25, q=95.0, \text{MinStackedRows}=1$, ES produce exactamente $414$ eventos ($0,91\%$ de cubetas, en perfecta concordancia con el $1,0\%$ de GC). Sin embargo, esto viola la regla de rechazo de celda aislada de Puerta 0.
   - **Opción B (Aumentar agregación temporal o de precio):** Usar $\text{TW} \ge 200$ o $\text{TicksPerRow} \ge 2$ (\$0.50 por fila) para que las cubetas abarquen la dispersión necesaria de precios.

---

## 7. Qué Falsaría Esta Conclusión

1. **Puerta 0:** Si un análisis sobre la cinta completa de 30M ticks mostrase que en sesiones de alta volatilidad (e.g. CPI/FOMC) `MinStackedRows=2` alcanza $\ge 10$ eventos/sesión de forma sostenida.
2. **Puerta 1:** Si una prueba de permutación de `MinStackedRows=1` sobre ES demostrase que las celdas individuales en ES NO son ruido sino verdaderos soportes/resistencias de absorción de libro profundo (a diferencia de GC donde $p50=1$ era ruido).

---

## Aporte al referente

Queda demostrado que **BigTrap2Absorption no es universalmente transferible de forma directa entre activos de libro delgado (GC, MBT) y activos de libro grueso (ES)** sin adaptar el eje de granularidad espacial o temporal: la exigencia de contigüidad de 2 ticks (`MinStackedRows=2`) que preserva el 100% de las zonas en MBT destruye el 99,5% de las zonas en ES, aislando un límite microestructural estricto del indicador.
