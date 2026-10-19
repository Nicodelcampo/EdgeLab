# DISENO P-44 — Normalización de parámetros por escala de cada activo (v1, 2026-08-31)

**Estado:** DIRECCION ELEGIDA, NADA CORRIDO. Documento de diseño; no se midió ningún
outcome, no se tocó ningún dato de señal, ninguna campaña congelada cambia.

**Decisión de dirección (Nico, chat Notion AI, 2026-08-31 ~13:30 ART):** ante la
disjuntiva planteada para P-44, se elige **normalizar los parámetros según la escala
de cada activo** (camino (a): una familia multi-instrumento comparable), por encima
del fallback (b) de pre-registrar cada instrumento por separado. El fallback queda
documentado como plan B si la normalización no colapsa las distribuciones.

## 1. El problema (evidencia ya medida, no nueva)

P-44: los parámetros no transportan entre instrumentos. El ejemplo medido del board:
`gaps2` produce **10 zonas** en un activo y **113.298** en otro con los mismos
parámetros nominales. Sin normalización, 56 contratos son 56 universos incomparables
y el N efectivo se queda en ~228 sesiones por campaña.

La aritmética del premio (estimada, no medida): ~2.600 contrato-sesiones potenciales
contra las 228 actuales → MDE de ~13 pp a ~3,8 pp (√(2600/228) ≈ 3,4×). Es el rango
donde vive un edge real (2–5 pp). **Sin N nuevo, un edge verdadero es invisible con
cualquier modelo.**

## 2. Censo medido del material disponible (fuente: `docs/research/bundle_index.json`, 2026-08-15)

11 activos, 56 contratos, 1.015.587.419 ticks (45 limpios + 11 re-cortados).
Filas por activo (árbol research-v2 completo, limpio + re-corte):

| Activo | Clase | Micro | Tick size | Tick value | Contratos | Filas |
| --- | --- | --- | --- | --- | --- | --- |
| ES | Equity index | no | 0,25 | 12,50 | 4 | 262.806.610 |
| MES | Equity index | sí | 0,25 | 1,25 | 4 | 167.065.860 |
| NQ | Equity index | no | 0,25 | 5,00 | 4 | 119.153.201 |
| MNQ | Equity index | sí | 0,25 | 0,50 | 4 | 334.506.728 |
| YM | Equity index | no | 1,00 | 5,00 | 4 | 21.051.454 |
| GC | Metals | no | 0,10 | 10,00 | 4 | 38.154.926 |
| ZB | Rates | no | 0,03125 | 31,25 | 4 | 27.204.693 |
| 6E | FX | no | 0,00005 | 6,25 | 4 | 18.755.187 |
| 6B | FX | no | 0,0001 | 6,25 | 4 | 7.791.752 |
| 6J | FX | no | 0,0000005 | 6,25 | 4 | 14.627.578 |
| MBT | Crypto | sí | 5,00 | 0,50 | 5 | 4.469.430 |

Rangos de trade date por contrato: medidos en el mismo manifest (cada contrato cubre
~3 meses de su tenor). **Sesiones por contrato: NO MEDIDAS todavía** — se computan
target-free con `edgelab/kaggle/sessions_cme.py` (la herramienta ya existe y está
sellada); no se estiman acá porque la cobertura intra-rango varía por activo.

## 3. Las dimensiones de escala que separan a los activos

Un parámetro nominal (ticks de barrera, volumen umbral, ancho de gap) mezcla cuatro
escalas distintas. La normalización consiste en declarar para cada parámetro **a cuál
escala pertenece** y expresarlo en esa unidad:

1. **Escala de precio**: tick_size y nivel de precio (un "gap de 5 puntos" no es lo
   mismo en ZB que en MBT). Unidad candidata: ticks, no puntos.
2. **Escala de volatilidad**: cuánto se mueve el activo por sesión/ventana. Unidad
   candidata: percentil o desvío de la distribución propia del activo (ej. múltiplos
   de la mediana del |Δtick| o del rango diario propio).
3. **Escala de actividad/densidad**: ticks por sesión (de ~0,6M en ZB 09-25 a ~100M
   en MNQ 03-26 — dos órdenes de magnitud). Unidad candidata: fracción de la sesión
   o percentil del flujo propio, no conteo absoluto.
4. **Escala económica**: tick_value/multiplier (ZB vale 62,5× más por tick que MBT).
   Solo entra cuando el estimando es económico; en campañas target-free no aplica.

**Prueba de existencia dentro del proyecto:** la campaña congelada Gate 1 NQ ya
normaliza así — `local_volatility_bin` es el quintil de la volatilidad pre-anchor
**de cada contrato** (`n_rand_matching_definitions`, spec `b9e75c25`). Es el mismo
truco, aplicado a los parámetros de los indicadores en vez de al matching.

## 4. Espacio de diseño (a medir antes de elegir)

Para cada indicador del conjunto nombrado (P-32: BigTrap2, aVolClusterPOI, Gaps2,
AACloseOpenDiffs, VolTicksPOC2) y cada parámetro suyo:

- **A. Unidades de volatilidad propia** (múltiplos de σ o de mediana |Δ| del activo).
- **B. Percentil de la distribución propia** (parámetro = "el p90 del rango propio").
- **C. Geometría relativa al rango de sesión/semana propio**.
- **D (fallback, plan B):** pre-registro por instrumento, combinación a nivel decisión.

Criterio de éxito medible y pre-escrito: tras normalizar, la distribución por activo
de **conteos de zonas/eventos por sesión** debe colapsar a un rango comparable
(se propone como umbral de trabajo: coeficiente de variación inter-activo < 0,5;
es un umbral de diseño, no un resultado), sin colapsar a degeneración (ni 10 ni
113.298 zonas: ni inanición ni diluvio por activo).

## 5. Qué se mide primero (todo target-free)

1. Sesiones por contrato × 56 (sessions_cme.py — target-free).
2. Distribución por activo de las magnitudes que los parámetros gobiernan (rangos,
   gaps, volúmenes, |Δ| ticks): solo features del pasado/presente, cero ventanas
   futuras, cero outcomes.
3. Curva de respuesta conteo-de-eventos vs parámetro normalizado, por activo.

Prohibido en esta fase: cualquier etiqueta forward, MFE/MAE, PnL, o mirar holdout.
Esto es medición de features, no de resultados — misma clase que el censo de Asia
(P-54) y los conteos de cobertura de Gate 1.

## 6. Gobernanza

- **No toca la campaña congelada** (Gate 1 NQ queda con sus 234/228 y sus parámetros;
  esto es para F4 y lo que sigue).
- Cada indicador × activo × parametrización candidata es una hipótesis de diseño que
  paga multiplicidad cuando se use para inferencia; la fase de medición target-free
  no, pero la elección final de normalización **se pre-registra antes de cualquier
  outcome** (la lección de P-47 y del addendum 007: con búsqueda flexible, la
  multiplicidad deja de ser contable — DSR/SPA o pre-registro, no las dos a medias).
- Rama sugerida para el trabajo: `research/p44-scale-normalization-v1-20260831`.
- Cuando haya números medidos, la decisión final (A/B/C o fallback D) vuelve a Nico.
