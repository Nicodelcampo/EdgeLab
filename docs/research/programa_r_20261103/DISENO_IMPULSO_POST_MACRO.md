# IMPULSO-POST-MACRO: Caja de Digestión Post-Macro (08:35–09:00 ET) tras la Ventana de las 08:30 ET

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Andersen, Bollerslev, Diebold y Vega (2003), «Micro Effects of Macro Announcements: Real-Time Price Discovery in Foreign Exchange», American Economic Review; Ederington y Lee (1993), JF.
- **Hipótesis económica:** La literatura de microestructura sobre anuncios macroeconómicos de las 08:30 ET demuestra que el ajuste ocurre en dos fases: un salto instantáneo en los primeros minutos (08:30–08:35 ET) con liquidez vacía, seguido de una fase de digestión de 25 minutos (08:35–09:00 ET) donde las carteras institucionales evalúan el dato y fijan los bordes de equilibrio. El primer quiebre de la caja 08:35–09:00 ET entre las 09:00 y las 10:30 ET captura la tendencia informada de media mañana (hasta las 12:00 ET).
- **Módulo:** `edgelab/research/impulso_post_macro.py` (`NOMBRE = "IMPULSO-POST-MACRO"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `POST-MACRO-6E-R` (6E→6E), `POST-MACRO-GC-R` (GC→GC), `POST-MACRO-ES-R` (ES→ES), `POST-MACRO-NQ-R` (NQ→NQ).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Opera el descubrimiento post-08:30 ET en divisas (6E), oro (GC) e índices (ES, NQ) sobre una caja de digestión (08:35–09:00 ET) que empieza después del spike de las 08:30 ET y antes de la apertura de acciones de las 09:30 ET.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento: primer cierre M1 fuera de la caja (08:35, 09:00 ET] durante (09:00, 10:30 ET] por lado (máximo uno por dirección y sesión).
- **Alternativas descartadas antes de medir:** Se descartó incluir los minutos 08:30–08:35 ET dentro de la caja porque las mechas del segundo exacto del anuncio distorsionan el stop y destruyen el múltiplo R.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `choque_0830` | `choque_atr` | `extremos` | 1 | `3` |
| `cuerpo_ruptura` | `cuerpo` | `ge` | 3 | `(0.45, 0.65)` |
| `eficiencia_digestion` | `er25` | `ge` | 3 | `(0.2, 0.38)` |

- **Ejecuciones (4):** `('MID', 2.0)`, `('MID', 3.5)`, `('OPUESTO', 2.0)`, `('OPUESTO', 3.0)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Si las sesiones con choque fuerte a las 08:30 ET (tercil alto de choque_atr) no muestran mayor continuación en R que las sesiones sin choque, o si ninguna celda confirma en réplica OOS.
- **Riesgos operativos y estructurales:** En índices (ES, NQ), la apertura del contado a las 09:30 ET puede generar un barrido transitorio del punto medio de la caja 08:35–09:00 ET (por eso se prueban stops tanto en MID como en el borde OPUESTO).
