# Informe Metodológico y Auditoría A-Priori de BigTrap2Absorption para ES (10 Sesiones Interiores)

**Fecha:** 2026-08-25  
**Instrumento:** E-mini S&P 500 (`ES 09-26`)  
**Motor:** `tools/run_mbt_export.py` (v1.1.1, Python, paridad con `BigTrap2Absorption.cs`)  
**Analizador:** `tools/analyze_all_es_10sessions.py` (orden causal estricto, paridad nativa $q=90$)  
**Artefacto Machine-Readable:** [`docs/research/es_apriori_10sessions_manifest.json`](es_apriori_10sessions_manifest.json)  
**Rama:** `docs/es-apriori-2026-08-25`  

---

## 1. Estado Epistémico Obligatorio y Firewall

```
CAMPAIGN_OUTCOMES_OPENED=false
PREEXISTING_OUTCOME_EXPOSURE=YES
TEMPORAL_HOLDOUT_TOUCHED_TARGET_FREE=YES
EDGE_DECLARED=false
```

> **Registro de Holdout Temporal:**  
> Las 10 sesiones analizadas (`2026-07-14` a `2026-07-27`) se encuentran comprendidas dentro del holdout temporal formal del repositorio (`2026-07-01` a `2026-12-31`). Aunque **no se abrieron ni calcularon outcomes, retornos futuros, P&L, MAE/MFE ni etiquetas direccionales**, no puede afirmarse un estado de "holdout intacto". Se registra formalmente que el holdout fue leído de modo **target-free**, quedando sujeto a decisión explícita de Nico sobre su alcance metodológico futuro.

---

## 2. Inventario de Cinta Madre y Recorte de 10 Sesiones Completas

- **Cinta madre:** `E:\EdgeLab\data\nt8\ES\ES 09-26.Last.txt`
  - Tamaño: 1.463.625.903 bytes (1,46 GB, 30.509.257 líneas).
  - Rango temporal: `2026-06-08 03:00:00 UTC` a `2026-07-28 00:51:47 UTC` (37 sesiones detectadas).
  - Sesiones de borde descartadas por incompletas: `20260608` (8.936 ticks) y `20260728` (18.433 ticks).
- **Cinta de calibración (10 sesiones interiores completas):** `E:\EdgeLab\data\nt8\ES\ES 09-26.10sessions.Last.txt`
  - Líneas: 20.560.762 a 30.490.824 (**9.930.063 ticks**).
  - Bytes: 466.436.658 bytes (466,44 MB).
  - SHA256: `5181ac92e5cbd148b3f0905b742981f1f634c84a6e5a9c8438034cad8a99537c`.
  - Sesiones cubiertas (10): `20260714`, `20260715`, `20260716`, `20260717`, `20260720`, `20260721`, `20260722`, `20260723`, `20260724`, `20260727`.

### Guardrail Completo de Tick Size (Escaneo Streaming de 9.930.063 ticks)
- Mínimo $|\Delta\text{precio}| > 0$: **0.25** exacto (`PASS`).
- Violaciones de grid en Last: **0**
- Violaciones de grid en Bid: **0**
- Violaciones de grid en Ask: **0**
- Líneas malformadas: **0**
- Bids / Asks no positivos ($\le 0$): **0**

---

## 3. Auditoría de Carga: `FAST_LOADER_PARITY_WITH_CANONICAL`

Se auditó el cargador rápido optimizado `load_canonical_ticks_fast` contra el cargador canónico `load_canonical_ticks` sobre los 9.930.063 ticks de la cinta recortada completa:

| Atributo | Loader Rápido | Loader Canónico | Hash SHA-256 (columna) | Estado |
|---|:---:|:---:|:---:|:---:|
| **Ticks Count** | 9.930.063 | 9.930.063 | — | `MATCH` |
| **`ts_ns`** | int64 | int64 | `689e2a92a4faa759...` | `MATCH` |
| **`price_ticks`** | int64 | int64 | `21a6556df9fafbd1...` | `MATCH` |
| **`bid_ticks`** | int64 | int64 | `5f7cb301cb7cbc79...` | `MATCH` |
| **`ask_ticks`** | int64 | int64 | `948e6e19e6324b14...` | `MATCH` |
| **`volume`** | float64 | float64 | `34b740dde4cec4cc...` | `MATCH` |
| **`sequence`** | int64 | int64 | `dac18f5da83f1129...` | `MATCH` |

**Resultado:** `FAST_LOADER_PARITY_WITH_CANONICAL = EXACT`. No se sintetizó BBO en silencio.

---

## 4. Manifiesto de los 8 Exports Nativos ($DATA/es_apriori/)

Todos los archivos generados con `absorption_pct=90.0`, `min_history=200`, `absorption_lookback=500`, `min_trap_frac=0.20`:

| Archivo | SHA-256 | Bytes | TW | Rows | TPR | Cubetas | TRAP bars | Zonas Nativas ($q=90$) | Recomp. Causal $q=90$ |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `es_export__TW10_rows2_tpr1.csv` | `4627c0a7e83d221407cd561f7767381603dcf866c4e3f714f971d57b99fe5c7f` | 391,554,718 | 10 | 2 | 1 | 993,011 | 53,257 | 23 | 23 |
| `es_export__TW15_rows2_tpr1.csv` | `9edb38cc251de0cb55060866e415e97a0f9988278543c836862ebad710ed0c03` | 268,016,186 | 15 | 2 | 1 | 662,010 | 46,471 | 56 | 56 |
| `es_export__TW25_rows2_tpr1.csv` | `9475651a5746041d4e2fe9b3b1e7f15f2d8c8e2ca6e800cf44f0b20a7279191d` | 164,617,649 | 25 | 2 | 1 | 397,208 | 33,237 | 108 | 108 |
| `es_export__TW50_rows2_tpr1.csv` | `cd82d09495b9baf9d6a55fafb405512245982d40e4898292ffa832cd1a8a4b12` | 83,366,807 | 50 | 2 | 1 | 198,606 | 17,270 | 220 | 220 |
| `es_export__TW25_rows1_tpr1.csv` | `4a9c286e984a6692c4c7f83f51b34b73579cf1dd58b935d4867cb48d4396d94c` | 168,746,538 | 25 | 1 | 1 | 397,208 | 33,237 | 6,276 | 6,276 |
| `es_export__TW100_rows2_tpr1.csv` | `33686a90c92d8470b738a10102c1b69df4cc7f0cd95d978c27dd6ceab4f98a42` | 42,808,801 | 100 | 2 | 1 | 99,305 | 9,668 | 277 | 277 |
| `es_export__TW200_rows2_tpr1.csv` | `053fc2140b221925d32b43548dfc0744ea0757cdb4e7eab3c3c497a07092b3e6` | 22,406,897 | 200 | 2 | 1 | 49,655 | 6,465 | 148 | 148 |
| `es_export__TW25_rows2_tpr2.csv` | `cb78cc42018c81dfd23752d98d8ee6ee7741fe432b277b71d9f01a73383c0aeb` | 204,552,950 | 25 | 2 | 2 | 397,208 | 104,915 | 27 | 27 |

*Nota de Paridad:* Todos los 8 archivos cumplen **$100\%$ de paridad nativa $q=90$** bajo orden causal estricto.

---

## 5. Medición de Identidad y Distribución del Colapso ($TW=25, TPR=1, q=95.0$)

Sobre los exports directos `TW25_rows1_tpr1` y `TW25_rows2_tpr1`, evaluados causalmente con clave única `(TradeDate, BarIndex, Side)`:

```
Claves únicas Rows1:        3.736
Claves únicas Rows2:        69
Intersección exacta:        69 (el 100.0% de los eventos Rows2 pertenece a Rows1)
Eventos exclusivos Rows1:   3.667
Eventos exclusivos Rows2:   0
```

### Separación Epistémica de Mediciones:
- **A. Reducción agregada de eventos (`Rows1 → Rows2`):** **$98,15\%$** ($1 - 69 / 3.736$).
- **B. Distribución geométrica de `run_rows` en la población Rows1:**
  - `run_rows == 1`: **$3.667$ eventos ($98,15\%$)**
  - `run_rows == 2`: **$64$ eventos ($1,71\%$)**
  - `run_rows == 3`: **$5$ eventos ($0,13\%$)**
  - `run_rows >= 2`: **$69$ eventos ($1,85\%$)**

### Persistencia Sesión por Sesión del Colapso:
El ratio de eventos `Rows1 / Rows2` por sesión varía en el rango **$22,5\times$ a $234,0\times$** (mediana: **$62,1\times$**). En $4$ de las $10$ sesiones, `Rows=2` produce menos de $5$ eventos.

| Métrica | `TW=25, Rows=1, TPR=1` | `TW=25, Rows=2, TPR=1` | Ratio (1 vs 2) |
|---|:---:|:---:|:---:|
| **Zonas Totales ($q=95.0$)** | **3.736** | **69** | **54,1×** |
| **Tasa sobre Cubetas ($q=95.0$)** | **0,94%** | **0,02%** | **47,0×** |
| **Mediana Zonas / Sesión** | **409,0** | **6,0** | **68,2×** |
| **Rango P25 – P75 / Sesión** | 290,2 – 460,0 | 3,5 – 8,5 | — |
| **Min – Max / Sesión** | 214 – 489 | 2 – 19 | — |
| **Sesiones con $< 5$ zonas** | **0 / 10** | **4 / 10** | — |

---

## 6. Grilla Canónica y Sensibilidad por Cuantiles (Rows=2, TPR=1)

| $TW$ | Cubetas Med/Ses | Zonas $q=90$ (Tot / % / Med) | Zonas $q=95$ (Tot / % / Med) | Zonas $q=97.5$ (Tot / % / Med) | Zonas $q=99$ (Tot / % / Med) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **10** | 98,134.5 | 23 / 0.00% / 2.0 | 9 / 0.00% / 1.0 | 4 / 0.00% / 0.0 | 1 / 0.00% / 0.0 |
| **15** | 65,423.0 | 56 / 0.01% / 4.0 | 29 / 0.00% / 2.0 | 15 / 0.00% / 1.0 | 7 / 0.00% / 0.5 |
| **25** | 39,254.0 | 108 / 0.03% / 9.5 | 69 / 0.02% / 6.0 | 43 / 0.01% / 4.0 | 17 / 0.00% / 1.0 |
| **50** | 19,627.5 | 220 / 0.11% / 19.5 | 155 / 0.08% / 13.5 | 100 / 0.05% / 9.0 | 48 / 0.02% / 5.5 |

---

## 7. Desglose Sesión por Sesión ($q=95.0$) Generado desde JSON

| Sesión | Cubetas ($TW=25$) | `TW25 Rows1 TPR1` | `TW25 Rows2 TPR1` | `TW50 Rows2 TPR1` | `TW100 Rows2 TPR1` | `TW200 Rows2 TPR1` | `TW25 Rows2 TPR2` |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2026-07-14** | 33,715 | 427 | 19 | 32 | 36 | 11 | 8 |
| **2026-07-15** | 37,613 | 275 | 2 | 9 | 15 | 8 | 1 |
| **2026-07-16** | 38,349 | 336 | 10 | 13 | 12 | 7 | 2 |
| **2026-07-17** | 49,690 | 489 | 6 | 14 | 20 | 3 | 1 |
| **2026-07-20** | 40,159 | 391 | 9 | 23 | 16 | 17 | 1 |
| **2026-07-21** | 29,933 | 214 | 7 | 18 | 16 | 12 | 2 |
| **2026-07-22** | 29,996 | 224 | 5 | 10 | 14 | 11 | 3 |
| **2026-07-23** | 49,386 | 476 | 6 | 11 | 18 | 16 | 1 |
| **2026-07-24** | 43,412 | 436 | 3 | 14 | 25 | 23 | 1 |
| **2026-07-27** | 44,955 | 468 | 2 | 11 | 20 | 13 | 0 |
| **Total 10 Sesiones** | **397,208** | **3,736** | **69** | **155** | **192** | **121** | **20** |
| **Mediana / Sesión** | **39,254.0** | **409.0** | **6.0** | **13.5** | **17.0** | **11.5** | **1.0** |

*Invariantes Aritméticos Verificados:*
- $\sum \text{by\_session} = \text{Total}$
- $\text{median}(\text{by\_session}) = \text{Mediana Publicada}$
- $\sum \text{bkt\_by\_session} = \text{Cubetas Totales}$

---

## 8. Discusión de Mecanismos Físicos: L1 vs L2

- **Hecho empírico medido en L1:** En ES, el $98,15\%$ de las absorciones extremas en barras TRAP de $TW \le 25$ transacciones ocurren confinadas en un único tick de precio ($\$0.25$).
- **Estatus Epistémico de la Hipótesis "Thick Book":**  
  `PLAUSIBLE_L2_MECHANISM_NOT_MEASURED_WITH_L1`.  
  La alta liquidez por nivel en ES es una explicación plausible para la absorción en un solo nivel, pero al procesar únicamente cintas L1 (Last/Bid/Ask sin profundidad de libro), no se declara causa raíz L2 confirmada.

---

## 9. Veredicto Final

```
ES_TW25_TPR1_ROWS2_COLLAPSE_OBSERVED_ON_10_SESSIONS
INSUFFICIENT_EVIDENCE_FOR_CANONICAL_PROMOTION_ON_ES
ADAPTATION_CANDIDATES_EXPLORATORY_ONLY_NOT_PREREGISTERED
PLAUSIBLE_L2_MECHANISM_NOT_MEASURED_WITH_L1
CAMPAIGN_OUTCOMES_OPENED=false
```

1. **Colapso Canónico Demostrado:** La configuración canónica ($TW=25, TPR=1, \text{MinStackedRows}=2$) colapsa de forma persistente a lo largo de las 10 sesiones en ES ($69$ eventos totales, mediana $6,0$/sesión, $4/10$ sesiones con $< 5$ eventos).
2. **Candidatos de Adaptación:** Las configuraciones exploratorias ($TW=50, 100, 200$, $\text{MinStackedRows}=1$) fueron examinadas únicamente como mapeo de sensibilidad estructural; **no fueron pre-registradas ni autorizadas para promoción**.
3. **Acción de Código:** No promover ES bajo el contrato canónico actual. No modificar `nt8/BigTrap2Absorption.cs` ni crear un contrato derivado sin un pre-registro explícito aprobado por Nico.
