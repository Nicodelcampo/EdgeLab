# ESTRUCTURA-HHLL: Continuación en Retroceso a EMA60 sobre Estructura Causal de Pivotes (HH+HL / LL+LH)

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Lo, Mamaysky y Wang (2000), «Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation», Journal of Finance; evidencia del Atlas en R (2026-11-03: stop estructural y objetivo lejano).
- **Hipótesis económica:** Cuando una sesión desarrolla una secuencia confirmada de pivotes de orden P=5 alcista (Higher-High h2 > h1 y Higher-Low l2 > l1) o bajista (Lower-Low l2 < l1 y Lower-High h2 < h1), los algoritmos seguidores de tendencia compran los retrocesos hacia el valor medio (EMA60 de la sesión) mientras el último pivote de soporte/resistencia (l2 o h2) permanezca intacto. El stop se ubica estructuralmente detrás del pivote confirmado l2/h2 y el objetivo busca 2,0R a 4,0R.
- **Módulo:** `edgelab/research/estructura_hhll.py` (`NOMBRE = "ESTRUCTURA-HHLL"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `ESTRUCTURA-HHLL-NQ-R` (NQ→NQ), `ESTRUCTURA-HHLL-ES-R` (ES→ES), `ESTRUCTURA-HHLL-YM-R` (YM→YM), `ESTRUCTURA-HHLL-GC-R` (GC→GC).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
A diferencia de TAU-TENDENCIA (que entra en la ruptura del extremo h2/l2 y sale por cruce de recta τ), ESTRUCTURA-HHLL entra en el retroceso hacia la EMA60 (mejor precio de entrada y menor distancia al pivote de stop l2/h2, mejorando el R por operación).

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento con enfriamiento: vela k (03:00–14:30 ET) con estructura HH+HL (o LL+LH) en pivotes confirmados P=5 velas después, precio a <= 1,2 ATR14 de la EMA60 sin violar l2/h2, y cierre a favor de la tendencia (enfriamiento de 35 velas).
- **Alternativas descartadas antes de medir:** Se descartó usar pivotes sin confirmar (look-ahead bias) y se descartó cerrar por línea de tendencia τ (para no cortar ganancias temprano).

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `pendiente_estructura` | `pend_atr` | `ge` | 3 | `(0.5, 1.1)` |
| `profundidad_pullback` | `prof_ret` | `extremos` | 1 | `3` |
| `vela_retoma` | `cuerpo` | `ge` | 3 | `(0.45, 0.65)` |

- **Ejecuciones (4):** `('PIVOTE', 1.0, 2.0)`, `('PIVOTE', 1.0, 3.5)`, `('PIVOTE', 1.4, 2.5)`, `('PIVOTE', 1.4, 4.0)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Si la pendiente estructural entre pivotes (pend_atr) no discrimina el retorno en R o ninguna celda supera FDR q <= 0,10 y réplica OOS.
- **Riesgos operativos y estructurales:** Cambios bruscos de régimen intradía donde el primer retroceso tras dos pivotes coincide con el techo/piso de la sesión.
