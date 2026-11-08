# COMEX-CIERRE-ORO: Flujo de Liquidación del Pit de Oro en COMEX (12:30–13:30 ET → 13:30 ET)

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Microestructura de tasación diaria (Settlement) de futuros y opciones de metales en CME/COMEX (13:28–13:30 ET); Bessembinder y Seguin (1992), JF; Baur et al. (2016).
- **Hipótesis económica:** El precio de liquidación diaria (Daily Settlement) de futuros y opciones de oro en COMEX se fija a las 13:30 ET. Entre las 12:30 y las 13:30 ET, productores, bullion banks y operadores de opciones ejecutan coberturas de delta y margen. Al cerrarse la subasta de tasación a las 13:30 ET, el flujo forzado cesa y el precio revierte la presión de liquidación (regla 0) o continúa hacia el cierre electrónico de las 15:55 ET (regla 1).
- **Módulo:** `edgelab/research/comex_cierre_oro.py` (`NOMBRE = "COMEX-CIERRE-ORO"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `COMEX-CIERRE-GC-R` (GC→GC), `COMEX-CIERRE-XAU-R` (DK:XAUUSD→GC).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Específico del mercado de oro (GC y XAUUSD) en la ventana vespertina 13:30–15:55 ET, donde ninguna estrategia de la canasta v5 opera.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento puntual de calendario: el cierre de la vela de las 13:30 ET (m == 810 NY) en cada sesión con subasta 12:30–13:30 ET completa.
- **Alternativas descartadas antes de medir:** Se descartaron stops fijos en dólares o ticks (vulnerables al cambio de régimen del oro entre 2023 y 2026); el riesgo se escala por el rango efectivo de la subasta 12:30–13:30 ET.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `regla` | `regla` | `grupo` | 2 | `2` |
| `desplazamiento_pit` | `desp_rango` | `ge` | 3 | `(0.35, 0.6)` |
| `tamano_subasta` | `rango_atr` | `extremos` | 1 | `3` |
| `eficiencia_sesion` | `er120` | `ge` | 3 | `(0.18, 0.32)` |

- **Ejecuciones (2):** `('PIT', 0.75, 2.5)`, `('PIT', 1.25, 3.5)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Ausencia de celdas nominadas en R o fallo en réplica OOS; si las velas con desplazamiento fuerte en el pit (desp_rango >= 0,60) rinden igual o peor que las de desplazamiento débil.
- **Riesgos operativos y estructurales:** Días de comunicado FOMC (14:00 ET), donde la subasta de las 13:30 ET queda subordinada al anuncio de tasas 30 minutos después.
