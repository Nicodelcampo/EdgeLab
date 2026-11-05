# PRIMERA-HORA-CONT: Continuación del Initial Balance de Primera Hora RTH (09:30–10:30 ET)

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Steidlmayer y Koy (1986), «Markets & Market Logic» (Initial Balance de 60 minutos del Market Profile); Bogousslavsky (2016), JF; Gao, Han, Li y Zhou (2018), JFE.
- **Hipótesis económica:** La primera hora regular (09:30–10:30 ET) establece los extremos del Initial Balance (IB) donde se concentra el descubrimiento inicial de precios. Cuando la primera hora presenta convicción direccional (asimetría cuerpo/rango) y el precio cierra fuera del IB entre las 10:30 y las 12:30 ET con participación de volumen, los algoritmos institucionales TWAP/VWAP sostienen la extensión hacia el cierre (15:55 ET).
- **Módulo:** `edgelab/research/primera_hora_cont.py` (`NOMBRE = "PRIMERA-HORA-CONT"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `PRIMERA-HORA-NQ-R` (NQ→NQ), `PRIMERA-HORA-ES-R` (ES→ES), `PRIMERA-HORA-YM-R` (YM→YM).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
A diferencia de OTR930 y RANGO-PREAPERTURA (que operan los primeros minutos de las 09:30 ET), PRIMERA-HORA-CONT espera a que cierre la primera hora completa (10:30 ET) y mantiene la posición con objetivos amplios (2R a 4R) hasta las 15:55 ET.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento: primer cierre M1 fuera del rango (09:30, 10:30 ET] durante (10:30, 12:30 ET] por lado (máximo un intento por dirección y sesión).
- **Alternativas descartadas antes de medir:** Se descartó colocar el stop en el extremo opuesto completo del IB de 60 minutos (demasiado lejano, reduce el múltiplo R alcanzable en el resto del día); se usan stops a 1/3 y 1/2 del ancho del IB.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `asim_ib` | `asim` | `ge` | 3 | `(0.3, 0.55)` |
| `ancho_ib` | `ib_atr` | `extremos` | 1 | `3` |
| `volumen_quiebre` | `rvol` | `ge` | 3 | `(1.0, 1.25)` |

- **Ejecuciones (4):** `('TERCIO', 2.5)`, `('TERCIO', 4.0)`, `('MITAD', 2.0)`, `('MITAD', 3.5)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Si la asimetría de la primera hora (asim_ib) y el volumen de ruptura no aportan ventaja positiva en R en DESC y réplica OOS.
- **Riesgos operativos y estructurales:** Días en que el dato de las 10:00 ET (ISM / JOLTS / Confianza del Consumidor) estira artificialmente el IB 09:30–10:30 ET y agota el rango diario antes de las 10:30 ET.
