# LONDRES-IMPULSO: Ruptura del Balance Inicial de Apertura de Londres (02:00–03:00 ET)

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Breedon y Ranaldo (2013), «Intraday Patterns in FX Returns and Order Flow», Journal of Money, Credit and Banking; Andersen y Bollerslev (1998), patrones intradía de liquidez institucional en la transición Asia → Londres.
- **Hipótesis económica:** En la primera hora de caja interbancaria de Londres (07:00–08:00 UK / 02:00–03:00 ET) los dealers europeos acumulan órdenes institucionales en una caja de equilibrio. El primer cierre M1 fuera de esa caja entre las 03:00 y las 05:30 ET libera flujo direccional antes de los anuncios macro de EE.UU. (salida forzada a las 08:25 ET).
- **Módulo:** `edgelab/research/londres_impulso.py` (`NOMBRE = "LONDRES-IMPULSO"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `LONDRES-IMP-6E-R` (6E→6E), `LONDRES-IMP-6B-R` (6B→6B), `LONDRES-IMP-GC-R` (GC→GC), `LONDRES-IMP-NQ-R` (NQ→NQ).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Opera exclusivamente la sesión europea temprana (03:00–08:25 ET) en divisas (6E, 6B), oro (GC) y NQ, sin solapamiento horario con la apertura RTH de EE.UU. (09:30 ET) donde se concentra la canasta v5.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento: primer cierre M1 fuera del rango (02:00–03:00 ET] en (03:00, 05:30 ET] por dirección (a lo sumo un disparo largo y uno corto por sesión). Se descartó evaluar el estado continuo (todas las velas fuera del rango) por autocorrelación intrasesión.
- **Alternativas descartadas antes de medir:** Se descartaron stops de 1–2 ticks en el borde de ruptura, cierres por break-even a +1R y objetivos cortos (< 2R) porque el programa R demostró que cortar ganancias destruye la esperanza matemática en R.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `cuerpo_ruptura` | `cuerpo` | `ge` | 3 | `(0.45, 0.65)` |
| `ancho_caja` | `ancho_atr` | `extremos` | 1 | `3` |
| `eficiencia_previa` | `er60` | `ge` | 3 | `(0.2, 0.35)` |

- **Ejecuciones (4):** `('MID', 2.0)`, `('MID', 3.0)`, `('OPUESTO', 2.0)`, `('OPUESTO', 3.5)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** 0 celdas nominadas por FDR q <= 0,10 en DESC sin pistas que confirmen en réplica OOS, fallo en INTEGRIDAD (latencia de 1 vela o placebo), o media <= 0R en réplica.
- **Riesgos operativos y estructurales:** Falsos quiebres en días festivos europeos (Bank Holidays del Reino Unido) o anuncios del BCE/BoE a las 07:00–08:15 UK.
