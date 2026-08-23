# Cobertura y Paridad — BigTrap2Absorption v1.1.1 (.cs ↔ Python)

Documento autoritativo de paridad por capa para el indicador **BigTrap2Absorption** sobre el contrato de futuros de Oro (**GC DEC26**), ventana del 17 al 21 de agosto de 2026.

## 1. Identidad de Implementaciones y Hashes

| Componente | Ruta | SHA256 |
|---|---|---|
| **.cs Repo** | `nt8/BigTrap2Absorption.cs` (892 líneas CRLF) | `18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641` |
| **.cs Instalado NT8** | `OneDrive/Documentos/NinjaTrader 8/bin/Custom/Indicators/BigTrap2Absorption.cs` (892L kernel + 57L autogen = 949L) | `0af1f759aacea2913e2e2c8f46fe5579453fb37738359c44cdf499eaebae57a3` (Kernel 892L sha: `18d16312...`) |
| **Kernel Python** | `edgelab/bridge/indicators/bigtrap2absorption.py` | `0d162a6092c31228ec0f4f9539b4afc0cb5031737263db4369dea2ad03697ab2` |
| **Export NT8 (AbsDirectional)** | `C:\Users\nicoc\Documents\NinjaTrader 8\exports\bt2_absorption__TW25_2.csv` | `c6eaeb210eeb029930f8157ac76380954700eed80dd5bf5b05df18a5ee9c19d7` |
| **Export NT8 (AbsMagnitude)** | `C:\Users\nicoc\Documents\NinjaTrader 8\exports\bt2_absorption__AbsMagnitude__TW25.csv` | `c521ef990fdce5c495de89f359d19e53dc7416a3701f902aa791f6ff9eb88755` |
| **Cinta de Ticks** | `C:\Users\nicoc\OneDrive\Documentos\DataNT8\GC 12-26.Last.txt` (683.188 ticks) | |

---

## 2. Parámetros del Headline Confirmado (AbsMagnitude)

- **ScoreMode**: `AbsMagnitude` ($A = |\text{signed\_flow}| / (1 + |d\_ticks|)$)
- **TapeWindowTicks**: `25`
- **AbsorptionPct**: `90.0`
- **AbsorptionLookback**: `500`
- **MinHistoryBuckets**: `200`
- **MinStackedRows**: `2`
- **MinTrapFrac**: `0.20`
- **RequireFlowSideMatch**: `true`
- **ImbalanceMode**: `Diagonal` (ratio 3.0)
- **UseWickFilter**: `true` (30.0%)

---

## 3. Cobertura de la Cinta y Limitaciones

- **Cinta canónica**: `GC 12-26.Last.txt` comienza el lunes 17 de agosto de 2026 a las `03:00:00.160 UTC` (`00:00:00.160 ART`).
- **Export NT8**: Comienza en la apertura del domingo 16 de agosto a las `19:00:01.212 ART`.
- **Exclusión pre-ancla**: 714 cubetas iniciales (17.814 ticks) no están contenidas en `GC 12-26.Last.txt`.
- **Ancla temporal dinámica**: Bar NT8 `715` en `t_start = 2026-08-17T00:00:09.788 ART` (`03:00:09.788 UTC`), coincidente exactamente con el índice `12` de la cinta.
- **Cobertura comparable**: 27.328 de 28.042 cubetas (**97,45%**).

---

## 4. Resultados Medidos de Paridad por Capa

### 4.1 Rama Headline: `AbsMagnitude`

| Capa / Métrica | Dimensión Medida | Cobertura | Coincidencia Exacta | Veredicto |
|---|---|---|---|:---:|
| **Cobertura de Cubetas** | `parsed_nt8 = 28.042`, `parsed_py = 27.329` | 27.328 comparables | `only_nt8 = 0`, `only_py = 0` | **EXACT** |
| **Flujo (`signed_flow`)** | Suma de volumen según reglas bid/ask/tickrule | 27.328 cubetas | 27.328 / 27.328 (100,00%) | **EXACT** |
| **Desplazamiento (`d_ticks`)** | `close - open` en ticks | 27.328 cubetas | 27.328 / 27.328 (100,00%) | **EXACT** |
| **Score (`a_score`)** | $|\text{flow}| / (1 + |\text{d\_ticks}|)$ | 27.328 cubetas | 27.328 / 27.328 (100,00%) | **EXACT** |
| **Conteo de ticks (`n_ticks`)** | Largo de cubeta | 27.328 cubetas | 27.328 / 27.328 (100,00%) | **EXACT** |
| **Flags Residuales** | Cortes CME | 27.328 cubetas | 27.328 / 27.328 (100,00%) | **EXACT** |
| **Umbral Causal (`a_pass`)** | Percentil 90 rodante (500 lookback, warmup 200) | 26.824 cubetas post burn-in | 26.824 / 26.824 (100,00%) | **EXACT** |
| **Historial Causal (`n_hist`)** | Tamaño del ring buffer causal | 26.824 cubetas post burn-in | 26.824 / 26.824 (100,00%) | **EXACT** |
| **Valor Umbral (`a_thr`)** | Percentil p90 rodante | 26.824 cubetas post burn-in | 26.824 / 26.824 (100,00%) | **EXACT** |
| **Cortes Residuales (D-2)** | 4 cortes de sesión CME | 4 cortes de sesión | `residual=True` (4/4), `a_pass=False` (4/4), `n_hist` (4/4), `a_thr` (4/4) | **EXACT** |
| **Zonas Creadas** | Geometría (`lo, hi, vol, rows, frac, a_score, a_thr`) | 365 zonas post burn-in | 365 / 365 (100,00%) (`only_nt8 = 0`, `only_py = 0`) | **EXACT** |
| **Fills** | Precio y timestamp (`fill_px, fill_at`) | 365 fills post burn-in | 365 / 365 (100,00%) (`only_nt8 = 0`, `only_py = 0`) | **EXACT** |

*Zonas excluidas de la ventana comparable:* 7 pre-ancla (domingo) y 5 pre-burnin en NT8 (2 en Python).

---

### 4.2 Rama Regresión: `AbsDirectional`

| Capa / Métrica | Dimensión Medida | Cobertura | Coincidencia Exacta | Veredicto |
|---|---|---|---|:---:|
| **Aritmética de Cubeta** | `signed_flow`, `d_ticks`, `a_score`, `n_ticks`, `residual` | 27.328 cubetas | 27.328 / 27.328 (100,00%) c/u | **EXACT** |
| **Umbral Causal** | `a_pass`, `n_hist`, `a_thr` | 26.824 cubetas post burn-in | 26.824 / 26.824 (100,00%) c/u | **EXACT** |
| **Capa Residual D-2** | 4 cortes de sesión | 4 cortes | 4 / 4 (100,00%) | **EXACT** |
| **Zonas Post Burn-in** | Geometría completa | 626 zonas post burn-in | 626 / 626 (100,00%) | **EXACT** |
| **Fills Post Burn-in** | `fill_px, fill_at` | 626 fills post burn-in | 626 / 626 (100,00%) | **EXACT** |

---

## 5. Veredicto Final de Puerta 0

- **Veredicto:** **`PASSED_PUERTA_0`**
- **Headline Validated:** **`true`**
- **Discrepancias Abiertas:** **0**
