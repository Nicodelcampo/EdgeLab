# COMPRESION-NR: Compresión de Volatilidad Intradía (NR4 de 30 Minutos) y Ruptura de Expansión

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Crabel (1990), «Day Trading with Short Term Price Patterns and Opening Range Breakout» (principio de contracción de rango NR4/NR7); Andersen y Bollerslev (1997), clustering de volatilidad intradía.
- **Hipótesis económica:** La volatilidad intradía alterna entre regímenes de compresión (equilibrio temporal de órdenes) y expansión (desequilibrio de flujo). Cuando el rango de 30 minutos [k−29, k] es más estrecho que los tres bloques previos de 30 minutos de la sesión (NR4 de 2 horas) y la vela k cierra fuera del canal de las 15 velas previas, el stop ubicado detrás de la caja comprimida es pequeño en puntos pero estructural, permitiendo capturar múltiplos de 2,5R a 4,0R.
- **Módulo:** `edgelab/research/compresion_nr.py` (`NOMBRE = "COMPRESION-NR"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `COMPRESION-NR-GC-R` (GC→GC), `COMPRESION-NR-NQ-R` (NQ→NQ), `COMPRESION-NR-ES-R` (ES→ES), `COMPRESION-NR-YM-R` (YM→YM).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
No depende de una hora fija ni de zonas de volumen HFT: detecta compresiones de volatilidad de 2 horas tanto en Londres como en NY sobre GC, NQ, ES y YM.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento con enfriamiento: primera vela k (entre 03:00 y 14:30 ET, a partir de la vela 120 de la sesión) donde R_30(k) <= 1,05 * min(R_30(k-30), R_30(k-60), R_30(k-90)) y c[k] rompe el canal de 15 barras, con enfriamiento de 45 minutos entre eventos.
- **Alternativas descartadas antes de medir:** Se descartó medir compresiones de sólo 5 o 10 minutos porque el rango resultante es comparable a la fricción canónica (violando ratio_mov_friccion >= 3,0).

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `grado_compresion` | `ratio_nr` | `le` | 3 | `(0.68, 0.88)` |
| `empuje_vela` | `empuje` | `ge` | 3 | `(0.45, 0.65)` |
| `franja_horaria` | `franja` | `grupo` | 3 | `3` |

- **Ejecuciones (4):** `('CAJA', 1.0, 2.5)`, `('CAJA', 1.0, 4.0)`, `('CAJA', 1.5, 2.5)`, `('CAJA', 1.5, 4.0)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Si las compresiones más severas (ratio_nr <= 0,68) no superan al resto o ninguna celda pasa FDR q <= 0,10 y réplica OOS.
- **Riesgos operativos y estructurales:** Compresiones previas a anuncios macro programados donde el primer movimiento es un barrido bilateral.
