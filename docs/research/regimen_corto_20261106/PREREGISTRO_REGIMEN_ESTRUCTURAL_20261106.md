# Pre-registro: Diagnóstico Estructural de Regímenes Cortos (`2026-11-06`)

- **Rama objetivo:** `gemini/regimen-corto-20261106`
- **Ventana evaluada:** `2025-08-05 .. 2026-09-30` (el período holdout `>= 2026-10-01` permanece cerrado e intacto).
- **Universos evaluados:**
  1. `U37`: las 37 campañas de futuros (`GC`, `NQ`, `ES`, `YM`) con grilla `<= 6.000` celdas de `docs/research/regimen_corto_20261106/universo.json`.
  2. `VWAP-DUAL-{GC,NQ,ES,YM}-R`: las 4 campañas `vwap_dual_iman` para contrastar entradas `LIM` vs `CONF`.
  3. `U18_SEGUIDAS`: las 18 estrategias nominadas en `DESC <= 2026-03-31` (`Estabilidad mensual en R2`).
- **Controles nulos (`B = 200` réplicas cada uno):**
  - **Nulo A (volteo de signo por sesión sobre `S0` centrado por ejecución):** conserva la correlación transversal entre campañas en cada sesión con deriva nula por celda.
  - **Nulo B (permutación del orden temporal de las sesiones sobre `S` con fricción real):** conserva la correlación entre campañas y la fricción real de cada celda (`-0,2221 R/op`), rompiendo únicamente la estructura temporal mes a mes.
- **Mecanismos evaluados sin lookahead (`P0..P5`):**
  - `P0_MICRO_AF` y `P0_MICRO_RM`: selección rotativa `1M IS -> 1M OOS -> 1M Prueba` sobre todas las celdas.
  - `P1_BAJA_FRICCION_AF` y `P1_BAJA_FRICCION_RM`: restricción ex-ante a ejecuciones de stop/target amplios (`S2/S3, T>=2,5R`).
  - `P2_ARQUETIPO_CAMPANA`: colapso de cada campaña a 1 serie equiponderada de baja fricción (`m = 1`).
  - `P3_PANEL_MULTIACTIVO`: exigencia de coincidencia simultánea en `>= 2` instrumentos de la misma familia en `T-2` y `T-1`.
  - `P4_DESC_CONGELADO_MAS_REGIMEN_OOS`: congelar a lo sumo 1 celda de baja fricción por campaña en `DESC` (`2025-08 .. 2026-03`, `>= 25` ops y media `>= +0,05 R/op`, repitiendo ese mismo paso dentro de cada réplica nula) y evaluar en `OOS` (`2026-04 .. 2026-09`):
    - `P4a_DESC_INCONDICIONAL`: operar todas las celdas congeladas sin filtro mensual.
    - `P4b_DESC_MOMENTUM_1M`: operar en el mes `T` sólo si en `T-1` tuvo `>= 3` ops, `R_{T-1} > 0` y `>= 50%` de sesiones activas positivas.
    - `P4c_DESC_VETO_2M_ROTO`: operar salvo ruptura en dos meses consecutivos (`R_{T-2} < 0`, `R_{T-1} < 0` y suma `<= -2,0 R`).
  - `P5_VWAP_DUAL`: comparación exhaustiva entre entradas `CONF` (a mercado) y `LIM` (orden límite en retroceso) sobre las 4 campañas `VWAP-DUAL-{GC,NQ,ES,YM}-R`.
- **Regla de decisión pre-registrada:** un procedimiento captura régimen corto fuera de muestra sólo si obtiene media `> 0` y supera tanto al Nulo A (`p <= 0,05`) como al Nulo B (`p <= 0,05`).
