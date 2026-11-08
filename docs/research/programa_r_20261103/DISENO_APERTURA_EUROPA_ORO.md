# APERTURA-EUROPA-ORO: Caja Pre-Mercado de Lingotes Zurich/Londres (02:00–03:30 ET) y Ruptura Europea

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Caminschi y Heaney (2014), «Fixing a Leaky Fix: Short-Term Market Reactions to the London PM Gold Price Fixing», Journal of Futures Markets; Baur et al. (2016), microestructura del mercado físico LBMA.
- **Hipótesis económica:** Entre las 02:00 y las 03:30 ET (07:00–08:30 Londres / 08:00–09:30 Zurich), los bancos de lingotes arbitran el cierre de la SGE (Shanghái) contra la apertura física europea. Esa ventana de 90 minutos forma la caja de referencia del oro europeo; su primer quiebre entre las 03:30 y las 07:30 ET desarrolla el movimiento direccional de la mañana europea hasta antes del London AM Fix (10:25 ET).
- **Módulo:** `edgelab/research/apertura_europa_oro.py` (`NOMBRE = "APERTURA-EUROPA-ORO"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `EUROPA-ORO-GC-R` (GC→GC), `EUROPA-ORO-XAU-R` (DK:XAUUSD→GC).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Focalizada en oro (GC y DK:XAUUSD) durante la mañana europea (03:30–10:25 ET), distinta de ORO-ALMUERZO-RUPTURA (que espera hasta las 14:00 de Madrid) y de las reglas de zonas sobre índices.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento: primer cierre M1 fuera de la caja (02:00, 03:30 ET] durante (03:30, 07:30 ET] por dirección (a lo sumo un disparo por lado y sesión).
- **Alternativas descartadas antes de medir:** Se descartó mantener la posición abierta durante toda la sesión americana para evitar solapar con COMEX-CIERRE-ORO y con anuncios de las 10:00/14:00 ET.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `alineacion_asia` | `alin_asia` | `eq_any` | 2 | `2` |
| `cuerpo_quiebre` | `cuerpo` | `ge` | 3 | `(0.45, 0.65)` |
| `compresion_caja` | `ancho_atr` | `extremos` | 1 | `3` |

- **Ejecuciones (4):** `('MID', 2.0)`, `('MID', 3.5)`, `('OPUESTO', 2.0)`, `('OPUESTO', 3.0)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** 0 celdas nominadas por FDR q <= 0,10 en DESC o falta de confirmación en réplica OOS.
- **Riesgos operativos y estructurales:** Choque de las 08:30 ET en EE.UU. mientras la operación sigue abierta hacia las 10:25 ET (acotado por el stop estructural en la caja europea).
