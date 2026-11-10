# Pre-registro: Filtro y Capa Transversal de Barreras HFT en $R$ (`BARRERAS-HFT-R`)

- **Fecha:** `2026-11-05`
- **Antecedente inmediato (`HFT-GC-P10-R`):**
  - Almacén completo en `GC` (`273` sesiones `2025-08-05..2026-09-30`): `39.583` zonas HFT (`alto_mediano = 7 ticks`) y `4.034` eventos `Cluster P10` (`alto_mediano = 12 ticks`).
  - Corrida base sin filtro de barreras ([`MEDIDO.md`](file:///e:/EdgeLab-port/docs/research/hft_gc_p10_20261105/embudo/HFT-GC-P10-R/MEDIDO.md)): en `DESC` (`2025-08-05..2026-03-31`) las 8 mejores pistas fueron 100% de continuación en la vela de la flecha (`B1_FLECHA_CONT`, hasta `+0,78R`, $p = 0{,}0015$), pero `0` superaron `FDR q <= 0,10` sobre `6.936` celdas evaluables y en `PISTAS` (`2026-04-01..2026-09-30`) quedaron en **`PISTAS_VIVAS`** (`0/8` confirmadas, canasta `-0,177R`, potencia `0,608 < 0,80`) al operar continuación sin verificar si existen zonas HFT frenando el recorrido delante.

---

## 1. Hipótesis Económica y Geometría de «Camino Despejado»

Sea una operación candidata decidida al cierre de la vela M1 $k$ (instante $t_k$) con dirección $s \in \{+1, -1\}$, precio de entrada $e$, riesgo unitario $R = |e - \text{SL}| > 0$ y objetivo original $\text{TP}$ ($D_{\text{TP}} = |\text{TP} - e|$).

Una zona o cluster HFT $z = [\text{lo}_z, \text{hi}_z]$ constituye un **posible freno causal en $k$** únicamente si:
1. **Causalidad estricta:** su confirmación ocurrió en $t_{\text{disp}}(z) \le t_k$ (para zonas individuales: tick de quiebre `t_ns`; para Borde Gris: `t_away_ns <= t_k`; para `Cluster P10`: `t_conf_ns <= t_k`).
2. **Antigüedad vigente:** la edad en tiempo de mercado activo cumple $\Delta \tau_{\text{mkt}}(t_k, z) \le \tau_{\max}$.
3. **No consumida antes de $k$:** cumple el criterio de mitigación exigido (`VIRGEN` o `NO_ATRAVESADA`) evaluado estrictamente en barras $\le k$.
4. **Ubicada de cara a la dirección de la entrada (excluyendo la propia zona gatillo):**
   - Si $s = +1$ (Long): su borde cercano frontal $\text{borde}_z = \max(\text{lo}_z, e)$ está por encima de $e + \delta_{\min}$ ($\delta_{\min} = 0{,}15R$, para no confundir la zona que origina la entrada con una barrera delantera), con $\text{hi}_z > e + \delta_{\min}$.
   - Si $s = -1$ (Short): su borde cercano frontal $\text{borde}_z = \min(\text{hi}_z, e)$ está por debajo de $e - \delta_{\min}$, con $\text{lo}_z < e - \delta_{\min}$.

Definimos la **distancia libre frontal** en unidades de $R$:
$$d_{\text{libre}}(k) = \min_{z \in \mathcal{B}(k)} \frac{|\text{borde}_z - e|}{R} \quad (\text{con } d_{\text{libre}}(k) = +\infty \text{ si } \mathcal{B}(k) = \emptyset)$$

---

## 2. Los 5 Parámetros del Filtro

| Eje | Niveles a evaluar | Significado |
| :--- | :--- | :--- |
| **1. `tipo_barrera`** | `0: TODAS_HFT`<br>`1: FUERTE_VOL_ABS`<br>`2: BORDE_GRIS_OPUESTO`<br>`3: SOLO_CLUSTER_P10` | `0`: cualquier zona HFT vigente (*rango limpio total*).<br>`1`: zonas `Absorb`/`Predator` o volumen HFT en tercil superior causal (`> P67`).<br>`2`: zonas con Borde Gris confirmado de signo opuesto a $s$.<br>`3`: sólo `Clusters P10` ($\ge 4$ zonas comprimidas). |
| **2. `antiguedad_max`** | `5m`, `15m`, `60m`, `180m`, `sesion` | Tiempo máximo de mercado activo tras el cual una zona HFT deja de contar como posible freno (arrancando en `5 min` para capturar liquidez HFT fresca en libro). |
| **3. `mitigacion`** | `0: VIRGEN`<br>`1: NO_ATRAVESADA` | `0`: se descarta apenas recibe el primer toque posterior.<br>`1`: sigue frenando mientras el precio no comercie ambos bordes (`lo` y `hi`). |
| **4. `rango_libre_min`** | `1.0R`, `2.0R`, `1.0_TP`, `1.5_TP` | Exigencia de despeje frontal: desde espacio mínimo de `1R–2R` hasta camino 100% libre al `TP` o `1,5× TP` (*cielo abierto*). |
| **5. `modo_accion`** *(pre-registros paralelos)* | **A: `VETO_PURO`**<br>**B: `CAP_TP_DELANTE`** | **A (`VETO_PURO`):** veta la operación si $d_{\text{libre}} < \text{rango\_libre\_min}$.<br>**B (`CAP_TP_DELANTE`):** si $d_{\text{libre}} < 1{,}5R$ (o el TP recortado queda bajo `3× fricción`, `18,15t` en `GC`), veta la entrada; si $1{,}5R \le d_{\text{libre}}\cdot R < D_{\text{TP}}$, mantiene la entrada y adelanta el `TP` `2 ticks` delante del borde de la primera barrera. |

---

## 3. Dos Vías de Evaluación y Blindaje Anti-Sobreajuste

### Vía 1 — Embudo sobre `HFT-GC-P10` (`HFT-GC-P10-VETO-R` y `HFT-GC-P10-CAPTP-R`)
- Se evalúan en paralelo las dos variantes de acción (**A: Veto puro** y **B: Cap de TP $\ge 1{,}5R$ + veto $< 1{,}5R$**) sobre `GC`.
- **Higiene de ventanas (`AP-001`):** dado que `HFT-GC-P10-R` ya ejecutó `PISTAS` en `[20260401, 20260930]`, ambas campañas declaran linaje hijo de `HFT_GC_P10` en [`LINAJES.jsonl`](file:///e:/EdgeLab-port/docs/research/LINAJES.jsonl), `"periodos_consumidos": {"oos": "COMPROMETIDO"}` y `"pistas_replica": {"activa": false}`:
  - Sólo nominan celdas que pasen **`FDR q <= 0,10`** por mérito propio en `DESC [20250805, 20260331]`.
  - `OOS [20260401, 20260930]` actúa únicamente como filtro de refutación (`INDAGA -> INTEGRIDAD -> OOS -> TOPES`).
  - La confirmación definitiva queda reservada al `HOLDOUT` sellado (`>= 2026-10-01`).

### Vía 2 — Capa Transversal Multi-Familia y Multi-Activo (`ATLAS-BARRERAS-HFT-R`)
- Siguiendo el protocolo DerSimonian-Laird de [`tools/atlas_contexto_r.py`](file:///e:/EdgeLab-port/tools/atlas_contexto_r.py):
  - **Activos y almacenes target-free:** `GC` (`ZONAS_HFTGCP10_GC` + `ZONAS_HFTGCP10_CLUST_GC`) y `NQ`, `ES`, `YM` (`edgelab-zonas-hft`: `ZONAS_HFTNQ_*` y `ZONAS_HFT2_*`).
  - **Separación a priori por mecanismo:** `CONTINUACION` vs `REVERSION` + `GLOBAL`, colapsando pares `Futuro + CFD` en clusters independientes `(familia_base, activo)`.
  - **Criterio de confirmación transversal:** `BH q <= 0,10` en `DESC` (`2025-08-05..2026-03-31`) **y** mismo signo con $p_{\text{uni}} < 0{,}05$ en `REP` (`2026-04-01..2026-09-25`), sin tocar jamás octubre 2026 (`202610`).

