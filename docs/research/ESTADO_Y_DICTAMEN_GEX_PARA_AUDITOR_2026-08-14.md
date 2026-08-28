# EdgeLab — Dictamen y Estado del Arte: Investigación y Datasets GEX

- **Destinatario:** Auditor Cuantitativo / Revisión Externa
- **Fecha:** 2026-08-14
- **Estado:** `AUDIT_SUBMISSION_READY`
- **Ámbito:** Gobernanza de Datos, Mecánica de Dealers (CME/CBOE) e Integración con Microestructura
- **Firewall:** `holdout_included=False`, `outcomes_accessed=False`, `pnl_accessed=False`
- **Referente Rector:** `docs/NORTH_STAR.md` (sha256: `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`)

---

## 1. Resumen Ejecutivo y Declaración Epistemológica

El presente documento consolida toda la evidencia empírica, la infraestructura de datos de 17 años y el marco metodológico desarrollado en EdgeLab respecto a la exposición gamma (**GEX - Gamma Exposure**) de los creadores de mercado (Dealers) en futuros y opciones financieras de EE.UU. (S&P 500, Nasdaq 100, Euro FX).

### Reglas de Rigor Metodológico en EdgeLab:
1. **Rechazo a Vendors Opacos:** No se aceptan métricas de proveedores comerciales de caja negra (p. ej. SpotGamma, SqueezeMetrics) como fuente de verdad. Toda inferencia debe derivarse de cadenas de opciones crudas o boletines oficiales auditables.
2. **Paridad de Datos antes de Interpretación:** No se evalúa P&L ni se optimizan parámetros sobre hipótesis GEX hasta que los datos de Open Interest (OI) y volumen superen el gate de paridad contra registros oficiales.
3. **Gobernador de Régimen Diario:** La exposición gamma actúa como una covariable de **régimen estructural ex-ante** que condiciona la probabilidad de reversión a la media intradía, evitando el *data snooping* sobre microestructuras locales.

---

## 2. Inventario Canónico de Datos y Artefactos

### A. Datasets Diarios Procesados (Parquets Canónicos)
Almacenados en `D:\EdgeLab\data\gex\`:

| Archivo Parquet | Activo Subyacente | Rango de Fechas | Días de Trading | Días $+GEX$ | Días $-GEX$ |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `gex_daily_sp500_history.parquet` | S&P 500 (`SPY` $\rightarrow$ `ES`) | 2008-01-02 $\rightarrow$ 2025-12-12 | **4.514 días** | 1.997 ($44.2\%$) | 2.517 ($55.8\%$) |
| `gex_daily_nasdaq_history.parquet` | Nasdaq 100 (`QQQ` $\rightarrow$ `NQ`) | 2011-03-23 $\rightarrow$ 2025-12-15 | **3.700 días** | 1.771 ($47.9\%$) | 1.929 ($52.1\%$) |

### B. Módulos y Código de Producción
1. **Reconstructor Vectorizado:** [`edgelab/gex/reconstruct_daily_gex.py`](file:///d:/EdgeLab/edgelab/gex/reconstruct_daily_gex.py)
   - Procesa contratos de opciones activos ($OI > 0, \gamma > 0$).
   - Infiere precio Spot ATM mediante cotizaciones *mid-quote* $(Bid + Ask) / 2$.
   - Calcula por strike: Net GEX, Call Wall, Put Wall, Absolute Wall y Nivel de Gamma Flip.
2. **ETL de Descarga:** [`tools/download_options_gex_history.py`](file:///d:/EdgeLab/tools/download_options_gex_history.py)
   - Ingesta cadenas históricas públicas verificables.
3. **Módulo de Stress Test Simétrico:** [`edgelab/research/gex_reversal_stress_test.py`](file:///d:/EdgeLab/edgelab/research/gex_reversal_stress_test.py)
   - Batería de primer pasaje estricto ($TP = SL = d$) con inferencia HAC Bartlett IC95%.

---

## 3. Formulación Matemática y Mecánica de Microestructura

### A. Ecuación del Dollar GEX
Para cada contrato $k$ (strike $K$, vencimiento $T$):

$$\text{Dollar GEX}_k = \text{Signo}(k) \times \text{Open Interest}_k \times \Gamma_k \times S^2 \times 0.01 \times 100$$

Donde:
* $\text{Signo}(k) = +1$ si es Call (Dealer largo de gamma al vender la call).
* $\text{Signo}(k) = -1$ si es Put (Dealer corto de gamma al vender la put).
* $S$ es el precio spot subyacente.
* $\Gamma_k = \frac{\partial^2 V_k}{\partial S^2}$ es la gamma del contrato.

### B. Matriz de Dinámica de Cobertura (Dealer Hedging)

```text
               ┌─────────────────────────────────────────────────────────┐
               │              REGÍMENES DE GAMMA EXPOSURE                │
               └────────────────────────────┬────────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
         ┌─────────────────────┐                         ┌─────────────────────┐
         │     +GEX REGIME     │                         │     -GEX REGIME     │
         │  (Dealers Long Gamma)│                         │ (Dealers Short Gamma)│
         └──────────┬──────────┘                         └──────────┬──────────┘
                    │                                               │
    ┌───────────────┴───────────────┐               ┌───────────────┴───────────────┐
    ▼                               ▼               ▼                               ▼
Precio Sube ──> Venden Subyacente   Precio Cae ──> Venden Subyacente
Precio Cae  ──> Compran Subyacente  Precio Sube ──> Compran Subyacente
    │                               │               │                               │
    └───────────────┬───────────────┘               └───────────────┬───────────────┘
                    ▼                                               ▼
         [ AMORTIGUADOR / REVERSIÓN ]                    [ ACELERADOR / MOMENTUM ]
         Quiebres de rango fallan.                       Quiebres de rango explotan.
         Re-entradas: ALTA PROBABILIDAD.                 Re-entradas: PROHIBIDAS.
```

### C. Definición de Niveles Estructurales
* **Call Wall:** $\arg\max_K \left( \sum \text{Call OI}_K \right)$ $\rightarrow$ Techo y resistencia institucional bajo $+GEX$.
* **Put Wall:** $\arg\max_K \left( \sum \text{Put OI}_K \right)$ $\rightarrow$ Piso y soporte institucional bajo $+GEX$.
* **Gamma Flip:** Strike $K^*$ tal que $\sum_{K \le K^*} \text{GEX}_K = 0$ $\rightarrow$ Umbral de transición de régimen.

---

## 4. Gobernanza de Fuentes Oficiales (Gates GEX-M0 / GEX-M1)

Documentado en [`docs/research/GEX_FUENTES_Y_GATES_2026-08-13.md`](file:///d:/EdgeLab/docs/research/GEX_FUENTES_Y_GATES_2026-08-13.md) y [`docs/research/GEX_M0_COLUMN_MAP_2026-08-13.md`](file:///d:/EdgeLab/docs/research/GEX_M0_COLUMN_MAP_2026-08-13.md):

### A. Fuentes Primarias de CME Group
* **Sección 01B:** Daily Bulletin FX Futures & Options (`6E`).
* **Sección 01C:** Daily Bulletin Equity Index Futures & Options (`ES`, `NQ`).
* Publicación: Finales $\approx$ 10:00 a.m. CT del día hábil siguiente.

### B. Identidad Aritmética Demostrada (Gate `GEX-M0`)
Verificada mecánicamente contra el boletín oficial final #154 (2026-08-12):

$$\text{Globex Volume} + \text{Complemento (PNT / Open Outcry)} \equiv \text{Total Volume}$$

* **Euro FX (`EC` / `6E`):** $125.584 + 2.256 = 127.840$ (OI Total: 803.339 contratos).
* **E-mini S&P 500 (`ES`):** $940.765 + 6.867 = 947.632$ (OI Total: 2.103.868 contratos).
* **E-mini Nasdaq 100 (`NQ`):** $410.608 + 2.682 = 413.290$ (OI Total: 291.056 contratos).

---

## 5. Aplicación a Estrategias Cuantitativas (`H-SWEEP-2`)

Registrada en [`docs/research/H-SWEEP-2_REENTRY_FLOW_AND_DENSITY_SHELVES.md`](file:///d:/EdgeLab/docs/research/H-SWEEP-2_REENTRY_FLOW_AND_DENSITY_SHELVES.md):

### Diagnóstico de YM-PRERANGE:
1. La pesca ciega del extremo de barrido en el rango de apertura (08:12–09:12 ET) arrojó un resultado puramente difusivo ($52.1\%$ reversión vs $47.9\%$ continuación, `PRERANGE_NO_EDGE`).
2. **El Mecanismo de Re-entrada Condicionada:**
   * La señal no es el toque del extremo, sino el **re-ingreso del precio al rango** tras absorber el flujo de ruptura.
   * **Filtro GEX:**
     * Si $\text{Net GEX} > 0$ ($+GEX$) $\rightarrow$ La absorción de los dealers respalda la reversión $\rightarrow$ **Se habilita el gatillo de re-entrada**.
     * Si $\text{Net GEX} < 0$ ($-GEX$) $\rightarrow$ La cobertura de dealers empuja el breakout $\rightarrow$ **Se inhabilita el sistema**.

---

## 6. Estado Actual de Ejecución y Próximos Pasos

1. **Infraestructura Completa:** Datasets históricos de GEX de 17 años generados y validados.
2. **Parquets Intradía de ES Disponibles:** Divididos en volúmenes $\le 180\text{ MB}$ en `D:\EdgeLab\data\ES_parquet_notion_split\`.
3. **Próxima Tarea:** Cruce temporal de los parquets intradía de ES (2025–2026) con la tabla de régimen diario de GEX para ejecutar la matriz de primer pasaje F2.7 y cuantificar el delta de expectativa ($\Delta \mathbb{E}$).
