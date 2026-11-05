# TOKIO-APERTURA-FX: Balance de Apertura de Tokio y Nakane Fix (19:00–20:00 ET)

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Ito y Yamada (2017), «Was the Tokyo Foreign Exchange Fix Manipulated?», Journal of Futures Markets; microestructura del Nakane Fix japonés (09:55 JST).
- **Hipótesis económica:** En la primera hora activa de Tokio (09:00–10:00 JST / 19:00–20:00 ET en horario estándar), los bancos comerciales japoneses y las mesas de metales asiáticas fijan el precio de referencia corporativo (Nakane Fix a las 09:55 JST). El rango 19:00–20:00 ET concentra esas órdenes comerciales; su primera ruptura entre las 20:00 y las 23:30 ET captura la tendencia asiática hasta antes de la apertura europea (01:55 ET).
- **Módulo:** `edgelab/research/tokio_apertura_fx.py` (`NOMBRE = "TOKIO-APERTURA-FX"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `TOKIO-FX-USDJPY-R` (DK:USDJPY→DK:USDJPY), `TOKIO-FX-GC-R` (GC→GC), `TOKIO-FX-6E-R` (6E→6E).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Opera activos guiados por el flujo asiático (DK:USDJPY, GC, 6E) en la ventana nocturna 20:00–01:55 ET, completamente desconectada de las sesiones europeas y americanas de NQ/ES.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento: primer cierre M1 fuera de la caja (19:00, 20:00 ET] durante (20:00, 23:30 ET] por dirección (a lo sumo un disparo por lado y sesión).
- **Alternativas descartadas antes de medir:** Se descartó mantener la operación hasta Nueva York (como hace MODELO-ASIA en NQ) para aislar puramente el flujo de la sesión asiática antes de que Londres abra a las 02:00 ET.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `cuerpo_ruptura` | `cuerpo` | `ge` | 3 | `(0.45, 0.65)` |
| `volumen_rel` | `rvol` | `ge` | 3 | `(1.0, 1.25)` |
| `ancho_tokio` | `ancho_atr` | `extremos` | 1 | `3` |

- **Ejecuciones (4):** `('MID', 2.0)`, `('MID', 3.5)`, `('OPUESTO', 2.0)`, `('OPUESTO', 3.0)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** 0 celdas nominadas por FDR q <= 0,10 en DESC o media <= 0R en réplica OOS; fallo en INTEGRIDAD.
- **Riesgos operativos y estructurales:** Menor volatilidad absoluta en 6E durante el horario asiático en comparación con USDJPY y GC (controlado por el filtro ratio_mov_friccion >= 3,0 del embudo).
