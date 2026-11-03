# ABSORCION-CLIMAX: Clímax de Volumen y Mecha de Absorción tras Extensión de 60 Minutos

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Grossman y Miller (1988), «Liquidity and Market Structure», Journal of Finance; Campbell, Grossman y Wang (1993), «Trading Volume and Serial Correlation in Stock Returns», QJE.
- **Hipótesis económica:** Según el modelo de provisión de liquidez de Grossman-Miller y Campbell-Grossman-Wang, los movimientos de precio acompañados de picos anormales de volumen fuera de noticias públicas son impulsados por demanda de inmediatez no informada (liquidaciones o stops). Cuando tras una extensión >= 1,2 ATR14 en 60 minutos aparece una vela con volumen >= 1,35x su media y mecha de rechazo >= 38 % del rango, los creadores de mercado han absorbido el flujo final y el precio revierte.
- **Módulo:** `edgelab/research/absorcion_climax.py` (`NOMBRE = "ABSORCION-CLIMAX"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `ABSORCION-CLIMAX-GC-R` (GC→GC), `ABSORCION-CLIMAX-NQ-R` (NQ→NQ), `ABSORCION-CLIMAX-ES-R` (ES→ES), `ABSORCION-CLIMAX-6E-R` (6E→6E).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
Mecanismo de reversión por agotamiento precio-volumen M1 con exclusión explícita de eventos macro (CPI, NFP, FOMC), aplicable a GC, NQ, ES y 6E en horario europeo y americano (03:00–14:30 ET).

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento con enfriamiento: vela k que cumple extensión previa de 60 min + pico de volumen + mecha de rechazo contraria, con enfriamiento de 35 minutos y filtro EXCLUIR_EVENTOS.
- **Alternativas descartadas antes de medir:** Se descartó entrar sin mecha de rechazo (fadear una vela de clímax que cierra en su extremo suele ser continuación informada) y se descartaron stops pegados a la mecha sin colchón de ATR (0,8x y 1,3x ATR14).

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `mecha_rechazo` | `mecha` | `ge` | 3 | `(0.45, 0.58)` |
| `climax_volumen` | `rvol` | `ge` | 3 | `(1.55, 2.0)` |
| `extension_previa` | `ext_atr` | `extremos` | 1 | `3` |

- **Ejecuciones (4):** `('ATR', 0.8, 2.0)`, `('ATR', 0.8, 3.0)`, `('ATR', 1.3, 2.0)`, `('ATR', 1.3, 3.5)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** 0 nominadas por FDR q <= 0,10 en DESC, fallo de integridad con 1 vela de latencia, o ausencia de confirmación en réplica OOS.
- **Riesgos operativos y estructurales:** Tendencias intradía impulsadas por noticias no catalogadas en el calendario fijo (declaraciones geopolíticas o subastas).
