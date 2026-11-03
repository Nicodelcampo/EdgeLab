# MEDIODIA-SUBASTA: Compresión del Almuerzo de Nueva York (11:30–13:00 ET) y Expansión Vespertina

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Admati y Pfleiderer (1988), «A Theory of Intraday Patterns: Volume and Price Variability», Review of Financial Studies (curva en U de volumen y varianza intradía).
- **Hipótesis económica:** Durante el valle de liquidez del mediodía en Nueva York (11:30–13:00 ET), el flujo institucional disminuye y el precio consolida en una caja de equilibrio. Cuando las mesas institucionales reanudan la ejecución a partir de las 13:00 ET, el primer cierre M1 fuera de la caja del almuerzo (entre 13:00 y 14:45 ET) captura la ola direccional vespertina hasta las 15:55 ET.
- **Módulo:** `edgelab/research/mediodia_subasta.py` (`NOMBRE = "MEDIODIA-SUBASTA"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `MEDIODIA-SUB-NQ-R` (NQ→NQ), `MEDIODIA-SUB-ES-R` (ES→ES), `MEDIODIA-SUB-YM-R` (YM→YM).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Opera el tramo de la tarde (13:00–15:55 ET) en índices (NQ, ES, YM), complementando las reglas matutinas de apertura (09:30–11:00 ET) y el cierre puro de EOD-MOM (15:30–16:00 ET).

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento: primer cierre M1 fuera de la caja [lo_1130_1300, hi_1130_1300] en (13:00, 14:45 ET] por dirección (a lo sumo un disparo por lado y sesión).
- **Alternativas descartadas antes de medir:** Se descartó entrar por simple toque intrabar sin cierre M1 fuera de la caja, y se descartaron objetivos menores a 2R.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `compresion_almuerzo` | `comp_ratio` | `le` | 3 | `(0.75, 1.05)` |
| `cuerpo_quiebre` | `cuerpo` | `ge` | 3 | `(0.45, 0.65)` |
| `sesgo_manana` | `alineado` | `eq_any` | 2 | `2` |

- **Ejecuciones (4):** `('MID', 2.0)`, `('MID', 3.5)`, `('OPUESTO', 2.0)`, `('OPUESTO', 3.0)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Si las cajas comprimidas (comp_ratio <= 0,75) no producen mayor expectativa en R que las cajas anchas, o si ninguna celda sobrevive al tamiz FDR y réplica OOS.
- **Riesgos operativos y estructurales:** Anuncios vespertinos (subastas del Tesoro de EE.UU. a las 13:00 ET o minutas FOMC a las 14:00 ET) que barren ambos bordes de la caja.
