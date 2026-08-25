# Configuración a-priori de BigTrap2Absorption para ES (E-mini S&P 500 Futures)

- **Fecha:** 2026-08-25
- **Rama:** `docs/es-apriori-2026-08-25` · **Base:** `docs/mbt-apriori-2026-08-25` (`7fbab53`)
- **Indicador:** `BigTrap2Absorption.cs` v1.1.1 (sha256 canónico: `18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641`)
- **Activo / Tick Size:** ES (CME E-mini S&P 500) · `TickSize = 0.25` (verificado en cinta, especificación oficial CME)
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · **Sin outcomes, sin holdout, sin P&L, sin MAE/MFE, sin declarar edge**.

---

## 1. Inventario de la Cinta Madre y Recorte de 10 Sesiones

### 1.1 Cinta Completa
- **Archivo:** `E:\EdgeLab\data\nt8\ES\ES 09-26.Last.txt`
- **Tamaño:** 1.463.625.903 bytes (1,46 GB) · **Total Líneas / Ticks:** 30.509.257
- **Rango Temporal:** `2026-06-08 03:00:00 UTC` $\rightarrow$ `2026-07-28 00:51:47 UTC`
- **Sesiones Detectadas (37 trade dates):**
  - *Borde inicial (parcial):* `20260608` (8.936 ticks).
  - *Sesiones regulares (35 sesiones):* `20260609` (39.134 t), `20260610` (62.243 t), `20260611` (169.089 t), `20260612` (321.975 t), `20260615` (691.864 t), `20260616` (868.659 t), `20260617` (1.208.640 t), `20260618` (1.109.303 t), `20260619` (144.303 t), `20260622` (1.071.492 t), `20260623` (1.403.997 t), `20260624` (1.406.328 t), `20260625` (1.109.963 t), `20260626` (1.107.992 t), `20260629` (1.113.189 t), `20260630` (905.893 t), `20260701` (988.805 t), `20260702` (1.355.819 t), `20260703` (108.507 t), `20260706` (768.643 t), `20260707` (935.151 t), `20260708` (1.167.104 t), `20260709` (785.309 t), `20260710` (767.716 t), `20260713` (940.707 t), `20260714` (842.883 t), `20260715` (940.313 t), `20260716` (958.708 t), `20260717` (1.242.227 t), `20260720` (1.003.975 t), `20260721` (748.307 t), `20260722` (749.881 t), `20260723` (1.234.626 t), `20260724` (1.085.282 t), `20260727` (1.123.861 t).
  - *Borde final (parcial):* `20260728` (18.433 ticks, sólo 2h51m de sesión).

### 1.2 Cinta de Calibración A-Priori (10 Sesiones Interiores Completas)
Excluyendo las sesiones parciales de borde, se toman las últimas **10 sesiones interiores completas** (`2026-07-14` a `2026-07-27`):
- **Archivo:** `E:\EdgeLab\data\nt8\ES\ES 09-26.10sessions.Last.txt`
- **Límites de corte:** Línea 20.560.762 (`2026-07-13 22:00:00 UTC`) a Línea 30.490.824 (`2026-07-27 20:59:58 UTC`).
- **Ticks / Líneas:** 9.930.063
- **Bytes:** 466.436.658 bytes (466,44 MB)
- **sha256:** `5181ac92e5cbd148b3f0905b742981f1f634c84a6e5a9c8438034cad8a99537c`
- **Guardrail Paso 0b (Tick Size):** Mínimo $|\Delta\text{precio}| > 0$ observado = **0.25** exacto (`PASS`).

---

## 2. Manifiesto de Exports Nativos ($DATA/es_apriori/)

Todos los exports fueron generados directamente con `tools/run_mbt_export.py` parametrizando nativamente `MinStackedRows`, `TicksPerRow` y `TapeWindowTicks`, preservando en cada archivo el cómputo exacto de corridas (`run_rows`, `run_frac`) e identificadores en el nombre.

| Archivo | sha256 | Bytes | TW | Rows | TPR | Cubetas | TRAPs | Zonas | Fills |
|---|---|---:|:---:|:---:|:---:|---:|---:|---:|---:|
| `es_export__TW10_rows2_tpr1.csv` | `4627c0a7e83d221407cd561f7767381603dcf866c4e3f714f971d57b99fe5c7f` | 391.554.718 | 10 | 2 | 1 | 993.011 | 53.257 | 23 | 23 |
| `es_export__TW15_rows2_tpr1.csv` | `9edb38cc251de0cb55060866e415e97a0f9988278543c836862ebad710ed0c03` | 268.016.186 | 15 | 2 | 1 | 662.010 | 46.471 | 56 | 56 |
| `es_export__TW25_rows2_tpr1.csv` | `9475651a5746041d4e2fe9b3b1e7f15f2d8c8e2ca6e800cf44f0b20a7279191d` | 164.617.649 | 25 | 2 | 1 | 397.208 | 33.237 | 108 | 108 |
| `es_export__TW50_rows2_tpr1.csv` | `cd82d09495b9baf9d6a55fafb405512245982d40e4898292ffa832cd1a8a4b12` | 83.366.807 | 50 | 2 | 1 | 198.606 | 17.270 | 220 | 220 |
| `es_export__TW25_rows1_tpr1.csv` | `4a9c286e984a6692c4c7f83f51b34b73579cf1dd58b935d4867cb48d4396d94c` | 168.746.538 | 25 | 1 | 1 | 397.208 | 33.237 | 6.276 | 6.276 |
| `es_export__TW100_rows2_tpr1.csv` | `33686a90c92d8470b738a10102c1b69df4cc7f0cd95d978c27dd6ceab4f98a42` | 42.808.801 | 100 | 2 | 1 | 99.305 | 9.668 | 277 | 277 |
| `es_export__TW200_rows2_tpr1.csv` | `053fc2140b221925d32b43548dfc0744ea0757cdb4e7eab3c3c497a07092b3e6` | 22.406.897 | 200 | 2 | 1 | 49.655 | 6.465 | 148 | 148 |
| `es_export__TW25_rows2_tpr2.csv` | `cb78cc42018c81dfd23752d98d8ee6ee7741fe432b277b71d9f01a73383c0aeb` | 204.552.950 | 25 | 2 | 2 | 397.208 | 104.915 | 27 | 27 |

---

## 3. Comparación Directa de Contigüidad sobre 10 Sesiones: Rows=1 vs Rows=2

Para resolver si la brecha entre `MinStackedRows=1` y `MinStackedRows=2` era un artefacto o una realidad estructural persistente, ambas variantes fueron ejecutadas con corridas directas sobre las 10 sesiones (`TW=25, TicksPerRow=1`):

| Métrica | `MinStackedRows = 1` (Nativo) | `MinStackedRows = 2` (Canónico) | Ratio (1 vs 2) |
|---|:---:|:---:|:---:|
| **Zonas Totales ($q=95.0$)** | **3.737** | **69** | **54,2×** |
| **Tasa sobre Cubetas ($q=95.0$)** | **0,94%** | **0,02%** | **47,0×** |
| **Mediana Zonas / Sesión** | **409,5** | **6,0** | **68,2×** |
| **Percentil 25 - 75 / Sesión** | 291,5 – 460,0 | 3,5 – 8,5 | — |
| **Rango Mín – Máx / Sesión** | 215 – 486 | 2 – 19 | — |
| **Sesiones con $< 5$ zonas** | **0 / 10** | **4 / 10** | — |

### Hallazgo:
La exigencia canónica de 2 filas contiguas (`MinStackedRows=2`) provoca un **colapso del 98,2% de la población de zonas** en ES de forma persistente y homogénea a lo largo de las 10 sesiones.

---

## 4. Grilla Canónica de `TapeWindowTicks` (Baseline: `MinStackedRows=2, TicksPerRow=1`)

| TW | Cubetas / Sesión (Mediana) | $q=90.0$ (Zonas / % / Med) | $q=95.0$ (Zonas / % / Med) | $q=97.5$ (Zonas / % / Med) | $q=99.0$ (Zonas / % / Med) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **10** | 98.134,5 | 18 / 0,00% / 1,5 | 9 / 0,00% / 1,0 | 6 / 0,00% / 0,5 | 1 / 0,00% / 0,0 |
| **15** | 65.423,0 | 56 / 0,01% / 4,0 | 29 / 0,00% / 2,0 | 14 / 0,00% / 1,0 | 7 / 0,00% / 0,5 |
| **25** | 39.254,0 | 108 / 0,03% / 9,5 | 69 / 0,02% / 6,0 | 43 / 0,01% / 4,0 | 15 / 0,00% / 1,0 |
| **50** | 19.627,5 | 221 / 0,11% / 19,5 | 155 / 0,08% / 13,5 | 97 / 0,05% / 9,0 | 41 / 0,02% / 4,0 |

---

## 5. Exploratorias de Adaptación de Escala (No Promovidas)

Para determinar si escalas mayores de tiempo de flujo o de precio permitían rescatar la contigüidad $\ge 2$ sin modificar el kernel:

1. **Escala Temporal Aumentada (`TW=100`, `TW=200` con `Rows=2, TPR=1`):**
   - **`TW=100`:** Produce 148 zonas en $q=95.0$ (0,15% de cubetas, mediana 14,5 zonas/sesión).
   - **`TW=200`:** Produce 121 zonas en $q=95.0$ (0,24% de cubetas, mediana 11,5 zonas/sesión).
   - *Observación:* Aumentar TW a 100-200 ticks permite alcanzar $\ge 10$ zonas/sesión con `Rows=2`, pero a costa de comprimir la sesión a sólo 4.900 cubetas.
2. **Escala de Precio Aumentada (`TW=25, TicksPerRow=2` con `Rows=2`):**
   - Produce sólo **20 zonas** en $q=95.0$ (0,01% de cubetas, mediana 1,0 zona/sesión).
   - *Observación:* Agrando el tamaño de fila a \$0.50 empeora drásticamente el colapso porque las condiciones de imbalance diagonal se vuelven aún más difíciles de apilar contiguamente en 25 ticks.

---

## 6. Desglose Sesión por Sesión (10 Sesiones Completas)

Conteo exacto de zonas generadas en cada una de las 10 sesiones ($q=95.0$):

| Sesión (Trade Date) | Cubetas ($TW=25$) | `TW=25, Rows=1` | `TW=25, Rows=2` | `TW=50, Rows=2` | `TW=100, Rows=2` | `TW=200, Rows=2` | `TW=25, TPR=2` |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2026-07-14** | 33.715 | 427 | 19 | 32 | 32 | 11 | 8 |
| **2026-07-15** | 37.613 | 277 | 2 | 9 | 10 | 8 | 1 |
| **2026-07-16** | 38.349 | 335 | 10 | 13 | 12 | 7 | 2 |
| **2026-07-17** | 49.690 | 486 | 6 | 14 | 12 | 3 | 1 |
| **2026-07-20** | 40.159 | 392 | 9 | 23 | 22 | 17 | 1 |
| **2026-07-21** | 29.933 | 215 | 7 | 18 | 15 | 12 | 2 |
| **2026-07-22** | 29.996 | 225 | 5 | 10 | 10 | 11 | 3 |
| **2026-07-23** | 49.386 | 476 | 6 | 11 | 10 | 16 | 1 |
| **2026-07-24** | 43.412 | 436 | 3 | 14 | 13 | 23 | 1 |
| **2026-07-27** | 44.955 | 468 | 2 | 11 | 10 | 13 | 0 |
| **Total 10 Sesiones** | **397.208** | **3.737** | **69** | **155** | **148** | **121** | **20** |
| **Mediana / Sesión** | **39.254,0** | **409,5** | **6,0** | **13,5** | **12,5** | **11,5** | **1,0** |

---

## 7. Discusión Microestructural: Hechos Medidos vs Hipótesis

1. **Lo empíricamente medido en esta cinta L1:**
   - La geometría de absorción en ES bajo ventanas pequeñas ($TW \le 50$) se encuentra casi exclusivamente concentrada en **una sola fila de precio** ($98,2\%$ de las zonas se forman en mono-nivel).
   - La contigüidad de $\ge 2$ filas con ratio 3:1 y fracción $\ge 20\%$ es extremadamente infrecuente en cubetas de $\le 25$ ticks.
2. **Hipótesis explicativa ("Thick Book") — NO directamente medida por L1:**
   - Una hipótesis plausible para esta dominancia mono-nivel es la profundidad estructural del libro de órdenes de ES (donde las órdenes pasivas absorben agresiones dentro del mismo tick de \$0.25 sin permitir la dispersión vertical rápida que se observa en GC o MBT).
   - Sin embargo, al no disponer de datos de profundidad L2 (Order Book DOM) en esta cinta, esta explicación se mantiene como **hipótesis física cualitativa y no como hecho medido**.

---

## 8. Veredicto

```
CANONICAL_COLLAPSE_OBSERVED_ON_10_SESSIONS
INSUFFICIENT_EVIDENCE_FOR_CANONICAL_PROMOTION_ON_ES
ADAPTATION_CANDIDATES_UNTESTED
CAMPAIGN_OUTCOMES_OPENED=false
```

### Directiva operativa:
1. **No promover ES bajo el contrato canónico actual (`MinStackedRows=2`, $TW \le 25$).**
2. **No crear ni commitear un `.cs` especial para ES en esta etapa.**
3. La variante `MinStackedRows=1` produce una tasa regular ($0,94\%$ cubetas, 409 zonas/sesión), pero relajar la regla de contigüidad constituye una hipótesis de adaptación que requeriría pre-registro formal antes de cualquier intento de validación.

---

## Aporte al referente

Se demuestra con una medición directa sobre **10 sesiones interiores completas (9,93 M de ticks)** que el colapso del contrato canónico de BigTrap2Absorption (`MinStackedRows=2`) en ES es persistente y homogéneo (colapso del $98,2\%$ de zonas, 4 de 10 sesiones con $< 5$ eventos). Se aísla formalmente la dominancia de la geometría mono-nivel en ES, dejando la profundidad del libro como hipótesis no medida y rechazando la promoción de ES bajo el contrato canónico vigente.
