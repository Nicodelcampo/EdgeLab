# Resultado del Diagnóstico Estructural de Regímenes Cortos (`2026-11-06`)

Estado: VIGENTE (diagnóstico del régimen corto, 06/11; ver H-REG-1 y la canasta estática en esta carpeta).

- **Pre-registro:** `docs/research/regimen_corto_20261106/PREREGISTRO_REGIMEN_ESTRUCTURAL_20261106.md`
- **Artefactos crudos:** `docs/research/regimen_corto_20261106/resultado_estructural.json` y `docs/research/regimen_corto_20261106/series_diarias_regimen_20261106.json`
- **Tableros diarios interactivos:** `docs/research/regimen_corto_20261106/estabilidad_diaria_en_r.html` y `docs/research/regimen_corto_20261106/top3_estabilidad_diaria_q3.html`
- **Kernels verificados en Kaggle:** `nicolasbuttaro/edgelab-regimen-estructural-20261106` (v4 `COMPLETE` para diagnóstico + 200 réplicas Nulo A/B; v5 `COMPLETE` para series diarias exactas).
- **Rango evaluado:** `2025-08-05 .. 2026-09-30` (sin tocar el holdout `>= 2026-10-01`).

## 1. Tabla Comparativa en `U37` (`2025-10 .. 2026-09`, `B = 200` réplicas Nulo A y Nulo B)

| Procedimiento | Ventanas | Ops | R Total | Media (`R/op`) | Nulo A `q05 / q50 / q95` | $p$ (Nulo A) | Nulo B `q05 / q50 / q95` | $p$ (Nulo B) | Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`P0_MICRO_AF`** (`1M IS -> 1M OOS`, todas las celdas) | 15 | 627 | -14,65 R | -0,0234 R | -0,035 / +0,001 / +0,031 | 0,846 | -0,182 / -0,092 / +0,014 | 0,149 | Rechazado |
| **`P0_MICRO_RM`** (`1M IS -> 1M OOS`, rescate medio) | 36 | 802 | +13,32 R | +0,0166 R | -0,036 / +0,001 / +0,031 | 0,209 | -0,176 / -0,097 / +0,005 | **0,035** | Poda fricción ($p_B=0,035$), no supera Nulo A |
| **`P1_BAJA_FRICCION_AF`** (sólo celdas `S2/S3, T>=2,5R`) | 5 | 302 | -13,16 R | -0,0436 R | -0,047 / -0,002 / +0,040 | 0,930 | -0,250 / -0,079 / +0,103 | 0,333 | Rechazado |
| **`P1_BAJA_FRICCION_RM`** (sólo celdas `S2/S3, T>=2,5R`) | 12 | 349 | -6,83 R | -0,0196 R | -0,043 / -0,001 / +0,037 | 0,756 | -0,207 / -0,080 / +0,071 | 0,229 | Rechazado |
| **`P2_ARQUETIPO_CAMPANA`** (1 serie colapsada por campaña) | 0 | 0 | 0,00 R | 0,0000 R | -0,123 / -0,005 / +0,087 | 0,458 | -0,017 / 0,000 / 0,000 | 0,905 | Sin activaciones |
| **`P3_PANEL_MULTIACTIVO`** ($\ge 2$ activos misma familia/mes) | 0 | 0 | 0,00 R | 0,0000 R | -0,057 / -0,004 / +0,037 | 0,463 | -0,485 / 0,000 / +0,283 | 0,542 | Sin coincidencias |
| **`P4a_DESC_INCONDICIONAL`** (1 celda `DESC` por campaña, sin filtro) | 123 | 639 | -62,07 R | -0,0971 R | -0,063 / +0,001 / +0,057 | 0,995 | -0,149 / -0,060 / +0,022 | 0,711 | Rechazado (falsos positivos de `DESC`) |
| **`P4b_DESC_MOMENTUM_1M`** (1 celda `DESC` + `T-1 > 0` y $\ge 50\%$ días +) | **23** | **103** | **+11,86 R** | **+0,1151 R** | -0,106 / -0,005 / +0,086 | **0,0149** | -0,222 / -0,072 / +0,096 | **0,0398** | **Único aprobado ($p_A < 0,02$ y $p_B < 0,05$)** |
| **`P4c_DESC_VETO_2M_ROTO`** (1 celda `DESC` salvo 2M $\le -2\text{R}$) | 91 | 476 | -37,29 R | -0,0783 R | -0,071 / +0,003 / +0,062 | 0,965 | -0,164 / -0,058 / +0,024 | 0,612 | Rechazado |

## 2. Evaluación sobre las 18 Estrategias Nominadas (`U18_SEGUIDAS`, `OOS 2026-04 .. 2026-09`)

| Variante en `OOS` (`2026-04 .. 2026-09`) | Regla-Meses | Ops | R Total OOS | Media (`R/op`) | % Ventanas + | Nulo A `q05 / q50 / q95` | $p$ (Nulo A) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`P4a_INCONDICIONAL_18`** (operar las 18 sin rotar) | 103 | **900** | **+32,61 R** | **+0,0362 R** | **56,3 %** | -0,040 / +0,004 / +0,054 | 0,164 |
| **`P4b_SOLO_1M_ESTABLE`** ($R_{T-1} > 0$, $\ge 4$ ops, $\ge 50\%$ días +) | 55 | 469 | +11,25 R | +0,0240 R | 56,4 % | -0,083 / -0,000 / +0,075 | 0,328 |
| **`P4b_SOLO_2M_ESTABLE`** ($R_{T-2}, R_{T-1} > 0$ y $\ge 50\%$ días +) | 36 | 275 | +6,38 R | +0,0232 R | 55,6 % | -0,116 / +0,009 / +0,114 | 0,423 |
| **`P4c_VETO_2M_ROTO`** (apaga sólo si $R_{T-2}<0, R_{T-1}<0$ y suma $\le -2\text{R}$) | 96 | 812 | +13,66 R | +0,0168 R | 54,2 % | -0,045 / +0,004 / +0,059 | 0,328 |

- Autocorrelación mensual lag-1 en `OOS`: `r = -0,0611`.

## 3. Comparación `CONF` (Mercado) vs `LIM` (Orden Límite) en `VWAP-DUAL-*-R` (`P5`)

| Campaña | Instrumento | Ops `CONF` | Media `CONF` (`R/op`) | Ops `LIM` | Media `LIM` (`R/op`) | Diferencia `LIM - CONF` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`VWAP-DUAL-GC-R`** | `GC` | 29.396 | -0,2322 R | 30.321 | -0,3089 R | -0,0767 R |
| **`VWAP-DUAL-NQ-R`** | `NQ` | 9.968 | -0,2333 R | 11.476 | -0,1724 R | **+0,0610 R** |
| **`VWAP-DUAL-ES-R`** | `ES` | 7.081 | -0,3809 R | 8.928 | -0,4679 R | -0,0870 R |
| **`VWAP-DUAL-YM-R`** | `YM` | 10.821 | -0,0642 R | 12.303 | -0,1375 R | -0,0734 R |
| **Total 4 Futuros** | **Todos** | **57.266** | **-0,2190 R** | **63.028** | **-0,2731 R** | **-0,0541 R** |
