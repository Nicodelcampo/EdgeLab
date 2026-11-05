# WM-FIXING: Flujo Institucional del WMR 4:00 PM London Fix (10:30–11:00 ET → 11:00 ET)

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Melvin y Prins (2015), «Equity Hedging and Exchange Rates at the London 4 p.m. Fix», Journal of Financial Markets; Evans (2018), «FX Fixings», Journal of Finance; Ito y Yamada (2017).
- **Hipótesis económica:** Los fondos pasivos y gestores globales de renta fija/variable ejecutan sus coberturas cambiarias al tipo de referencia WMR de las 16:00 de Londres (11:00 ET). El flujo acumulado entre 10:30 y 11:00 ET produce presión de inventario que o bien revierte tras las 11:00 ET por alivio de liquidez (regla 0) o bien continúa hasta las 12:30 ET cuando refleja rebalanceo macro real (regla 1).
- **Módulo:** `edgelab/research/wm_fixing.py` (`NOMBRE = "WM-FIXING"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `WM-FIXING-6E-R` (6E→6E), `WM-FIXING-6B-R` (6B→6B), `WM-FIXING-GC-R` (GC→GC), `WM-FIXING-EURUSD-R` (DK:EURUSD→6E).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Anclado al evento institucional de las 11:00 ET en FX spot/futuros (6E, 6B, DK:EURUSD) y oro (GC), ortogonal a las zonas de volumen HFT/AVZP2 de índices de EE.UU.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento puntual de calendario: el cierre de la vela de las 11:00 ET (m == 660 NY) en cada sesión hábil con ventana pre-Fix completa (10:30–11:00 ET). No es un estado continuo.
- **Alternativas descartadas antes de medir:** Se descartó operar dentro de la ventana 10:55–11:00 ET con stops cortos por el ensanchamiento transitorio de spreads del propio Fixing; el stop se ancla al rango realizado de toda la media hora 10:30–11:00 ET (1,0x o 1,5x).

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `regla` | `regla` | `grupo` | 2 | `2` |
| `impulso_fix` | `imp_atr` | `ge` | 3 | `(0.75, 1.35)` |
| `volumen_fix` | `v_ratio` | `ge` | 3 | `(0.95, 1.15)` |
| `regimen_vol` | `rv_rel` | `extremos` | 1 | `3` |

- **Ejecuciones (2):** `('RANGO', 1.0, 2.5)`, `('RANGO', 1.5, 3.5)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Si ni la rama de reversión (regla 0) ni la de continuación (regla 1) superan el tamiz FDR q <= 0,10 en DESC o no replican en OOS, o si la ventaja no crece con el impulso y volumen relativo del Fix.
- **Riesgos operativos y estructurales:** Desfase de 1 hora durante las dos semanas anuales en que EE.UU. y Reino Unido cambian el horario de verano (DST) en fechas distintas.
