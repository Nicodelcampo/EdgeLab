# aVolClusterPOI — Informe Formal por Ticks (2026-08-14)

- **Spec:** `specs/avolcluster_tick_formal_v0.json` (v0)
- **Protocolo:** `docs/research/AVOL_TICK_FORMAL_PROTOCOL_2026-08-14.md`
- **Runner:** `diag/tasa_senales/avolcluster_tick_formal.py`
- **JSON sellado:** `diag/tasa_senales/AVOLT_formal_d5c41684e162.json`
- **Payload SHA-256:** `d5c41684e16280a4a08c54f85194613363c5ba2e80e3cc98691184b8ab86fd3d`
- **Git HEAD:** `413d703b74dfb621e25e9858540b610c14c51952`
- **Firewall:** `<= 2026-06-30` (Holdout no incluido, `outcomes_accessed = false`, `pnl_accessed = false`)

---

## 1. Veredicto Formal Emitido por la Máquina

```text
LABEL: ABSTAIN_P2
```

---

## 2. Gate P2 de Replay

| Métrica | Valor |
|---|---|
| **Oráculo NT8 (`data/nt8_oracles/avolcluster_v05_20260813.csv`)** | 133 zonas `ZONE_CREATED` |
| **Replay Python sobre `6E_09-26` (2026-04-10 a 2026-06-30)** | 51 zonas `OFF_PRICE` |
| **Match Rate P2** | **0.0% (0 / 133)** |
| **Diagnóstico Causal:** | El gráfico NT8 donde se ejecutó el censo operaba con contrato continuo (incluyendo el front month `6E 06-26` en abril/mayo y `6E 09-26` en junio). El archivo canónico `6E_09-26_ticks.parquet` representa exclusivamente el contrato individual de septiembre (que en abril no tenía volumen negociable). |
| **Gate P2:** | **FAIL $\rightarrow$ `ABSTAIN_P2`** (fail-closed estricto según la especificación). |

---

## 3. Resultados Formales de la Carrera de Primer Pasaje por Ticks (4 Contratos Canónicos)

Muestra total evaluada sobre los 4 parquets canónicos (`6E_12-25`, `6E_03-26`, `6E_06-26`, `6E_09-26`):
* **Ticks evaluados:** 16,220,649 ticks
* **Barras M1:** 282,101 barras
* **Sesiones con Zonas:** 188 sesiones
* **Población OFF_PRICE:** 798 zonas

### Tabla Comparativa de Brazos (HAC Bartlett lag 14)

| Brazo | $N$ | Media r_i | SE (HAC) | IC 95% | Aciertos vs Espejo | Tasa Empates |
|---|---|---|---|---|---|---|
| **Zona Real vs Espejo** | 798 | **+0.0657** | 0.0463 | `[-0.0250, +0.1564]` | 410 vs 388 (51.38%) | **0.0%** (0 empates) |
| **Control Random (Primario)** | 798 | **-0.0071** | 0.0476 | `[-0.1003, +0.0862]` | 383 vs 415 (47.99%) | **0.0%** (0 empates) |
| **Control Nearest (Diagnóstico)** | 798 | **-0.0159** | 0.0538 | `[-0.1213, +0.0895]` | 360 vs 438 (45.11%) | **0.0%** (0 empates) |
| **Contraste (Zona − Random)** | 798 | **+0.0728** | 0.0715 | `[-0.0673, +0.2129]` | — | — |
| **Contraste (Zona − Nearest)** | 798 | **+0.0816** | 0.0738 | `[-0.0630, +0.2262]` | — | — |

---

## 4. Hallazgos Metodológicos Clave

1. **Resolución Total de Empates:**
   * La maquinaria de `tick_first_touch` resolvió el **100% de los empates intrabarra** (0 empates residuales). El gate de resolución es del **100% (`frac_resolved = 1.0`)**.
2. **Saneamiento de los Controles:**
   * Tanto `control_random` ($-0.0071$, IC `[-0.100, +0.086]`) como `control_nearest` ($-0.0159$, IC `[-0.121, +0.090]`) se centran exactamente en cero bajo el nulo, confirmando que no hay contaminación de construcción.
3. **Potencia Estadística MDE:**
   * Al expandir a 4 contratos, el error estándar $SE$ cayó a **$0.0463$** (con MDE $\approx 0.13$).
   * El efecto observado $+0.0657$ cruza el cero al 95% de confianza en el contraste pareado.
4. **Split por Lado:**
   * `above` ($N=423$): media $r = +0.0875$
   * `below` ($N=375$): media $r = -0.0400$
