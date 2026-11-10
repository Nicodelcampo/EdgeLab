# Pre-registro — HFT-RUPTURA: ¿en qué toques el precio atraviesa de forma distintiva un cluster HFT grande?

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-11-10. Pedido de Nico.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
**Familia nueva `HFT_RUPTURA`**, linaje ← `HFT_CLUSTERS_INFO` (hereda su multiplicidad; nace de una pista vista en sus datos).
Código: `edgelab/research/hft_ruptura.py`, modos `ruptura` y `ruptura_rep` del kernel, `tools/hft_clusters_info.py ruptura|ruptura_rep`.
Tests: `tests/research/test_hft_ruptura.py`.

## 0. Qué se sabe antes de empezar (lo leído en el repo)
- **HFT-REBOTES:** en NQ el cluster grande no se defiende. Pero la «ruptura» es RELATIVA: el real da 49,7 % de rupturas contra
  48,7 % de rebotes (≈ moneda); la diferencia viene de que el control (nivel negociado 20–40 min antes) rebota (+0,07). Además está
  toda en ago–dic 2025 y desaparece en ene–mar 2026, y es igual como soporte que como resistencia. **No hay ruptura operable en
  promedio**: lo que se busca es si un subconjunto de toques rompe lo suficiente para pagar la fricción.
- **BigTrap2 como soporte/resistencia (ago 2026):** ~96 % de ruptura, invariante a los parámetros: las zonas como S/R no se sostienen.
- **`F-HUIDA-CONTINUACION`:** entrar a favor justo después de una huida fuerte en contra resta (única variable de contexto que
  sobrevivió en bruto) → la velocidad y la historia de la aproximación importan.
- **`F-ATLAS-CONTEXTO-ES-FRICCION`:** hora y volatilidad relativa «confirmadas» en neto eran fricción. Acá todo se mide en bruto con
  carrera simétrica ±X (stop y objetivo iguales), así que la fricción no sesga entre celdas.
- **`F-SELECCION-EN-GRILLAS-GRANDES`:** lo elegido entre muchas celdas cae a ≈ 0 en la réplica → la indagación es exploratoria, la
  selección es mecánica y escrita, y la confirmación usa datos no usados y a lo sumo 3 reglas.

## 1. Población
Toque D0 (primer regreso al borde tras alejarse X/2) de los clusters del E0-b (NQ 8 zonas, ES 12 zonas), reales y de control.
Otras poblaciones posibles (toque n-ésimo, penetración, estado continuo) quedan NO MEDIDAS en esta familia.

## 2. Paso 1 — indagación exploratoria (DESC 2025-07 → 2026-03, datos ya usados)
- **Rasgos (15, todos causales):** aproximación (segundos de los últimos X/2, excursión, segundos afuera), cluster (edad, ancho en X,
  zonas, packing, alineación del flujo de sus zonas con la llegada, nº de visita), sesión (minuto ET, tendencia de la sesión respecto
  de la llegada, distancia al extremo de la sesión, rango de los últimos 30 min), toque (volumen de los 30 s previos relativo a la
  sesión, desequilibrio por tick rule en la dirección de llegada).
- **Desenlaces:** carrera ±X (principal), ±X/2, ±2X, tiempo hasta resolver, avance máximo a favor de la ruptura en 15 min.
- **Salida:** por rasgo y tercil (cortes en los reales de cada activo): ruptura real, diferencia contra control, meses positivos, por
  activo. Es descriptiva: no decide nada por sí sola. Pruebas contadas: 15 × 3 = **45** (`hft_ruptura/indaga`; con §7 y §8, 69).
- **Regla de selección (mecánica, `hft_ruptura.seleccionar`):** celdas con ruptura real media ≥ 0,08 (paga la fricción con stop = X),
  mejor que el control, ≥ 5 de 8 meses positivos y mismo signo en NQ y ES (o sólo NQ si ES tiene < 100 eventos); se ordenan por
  ruptura media y se toman hasta 3 de rasgos distintos. Si ninguna cumple: la familia se cierra como SIN_RUPTURA_DISTINTIVA.

## 3. Paso 2 — confirmación (réplica 2026-04-01 → 2026-09-30, no usada por esta familia; una sola vez)
- Las reglas seleccionadas se congelan con sus cortes numéricos (`ruptura_rep`, cortes escritos en el kernel antes de lanzar).
- **Prueba:** por regla, H1: ruptura real media > 0,08 (bootstrap por sesión), y real > control como diagnóstico. LORD++ / BH entre
  ≤ 3 reglas. Pruebas: **3** (`hft_ruptura/rep`).
- Confirmada = rechaza con ruptura > 0,08. Una confirmada no es edge: sigue P&L con ejecución fija y holdout por protocolo.

## 4. Justificación económica
Un cluster HFT grande es un lugar donde se ejecutó tamaño. Si al volver el precio la liquidez ya no está (el ejecutor terminó), el
nivel no frena y el precio sigue; si llega con flujo a favor (desequilibrio, tendencia de sesión, aproximación rápida), puede romperlo
con impulso. Los rasgos buscan cuándo pasa una cosa y no la otra.

## 5. Cómo podría refutarse
Ninguna celda cumple la regla de selección; o ninguna regla supera 0,08 en la réplica; o las que pasan lo hacen sólo en un activo.

## 6. Riesgos declarados
- La pista nació mirando DESC: la indagación sobre DESC es exploratoria y no cuenta como evidencia; sólo la réplica confirma.
- 45 celdas exploratorias: con el umbral económico, la estabilidad mensual y la consistencia entre activos se espera muy poca selección
  por azar, pero no cero; por eso hay réplica.
- Si la familia usa la réplica abr–sep, `HFT_CLUSTERS_INFO` conserva la suya para D4 u otra hipótesis (familias distintas).

## 7. Enmienda A1 (2026-11-10, pedido de Nico, ANTES de ver resultado alguno de la indagación)
La corrida v1 de la indagación (15 rasgos, kernel `hft-clusters-info-ruptura-20261110`) se lanzó y **se descarta sin mirar**: se
relanza con el mismo código más 6 rasgos. Ningún resultado de la v1 se leyó antes de esta enmienda.

Rasgos agregados (todos causales: sólo velas de 1 min completas antes del toque y ticks ≤ toque):
- `picos_dentro`: picos de liquidez vivos (pivote de 3 velas de 1 min por lado, la misma definición que `espejo_picos`, confirmado y
  sin romper hasta el toque) cuyo precio cae dentro del rango del cluster.
- `picos_sin_tomar`: picos que la aproximación dejó atrás sin tomar (llega bajando → máximos vivos arriba; subiendo → mínimos), desde
  la última salida del rango.
- `salida_s`: «expansión limpia» de la última pasada: segundos desde que el precio dejó el rango hasta estar a X/2 de él (chico =
  salida limpia; sin dato si nunca se alejó X/2).
- `vol_banda_rel`: volumen del cluster, proxy declarado: volumen negociado dentro del rango en los 30 min previos a la detección,
  contra el volumen medio por 30 min de la sesión.
- `ema9_pend`, `ema21_pend`: pendiente de la EMA 9 y la EMA 21 de cierres de 1 min en las últimas 5 velas completas, en unidades de X
  y con signo hacia el cluster (> 0 = el precio llega con las EMAs inclinadas hacia el cluster).

Pruebas exploratorias extra: 6 × 3 terciles = **18** (`hft_ruptura/indaga_b`). La regla de selección (§2) y la réplica (§3, ≤ 3
reglas) no cambian. Total de la indagación: 63 celdas, todas exploratorias.

## 8. Revisión R1 (2026-11-10, pedido de Nico de iterar las definiciones, ANTES de ver resultados)
La versión 2 del kernel (enmienda A1) **se descarta sin mirar** y se relanza como versión 3. Errores corregidos:
1. **Estratos con empates (afectaba a la v1 y la v2):** con terciles por `searchsorted(side="right")`, un rasgo discreto con mayoría
   de ceros (picos, tendencia ±1, flujo, nº de visita) mandaba TODO al tercil superior y dejaba vacíos los otros. Ahora estrato =
   (v > corte_1) + (v > corte_2) y los rasgos discretos tienen cortes fijos: picos 0 | 1 | ≥ 2; tendencia y flujo en contra | neutro
   | a favor; visita 2 | 3 | ≥ 4. El resto, terciles de los reales de cada activo.
2. **La réplica no reproducía la celda:** congelaba el promedio de los cortes de NQ y ES y usaba otra regla de borde. Ahora congela
   los cortes de cada activo y usa la misma función (`hft_ruptura.estrato`) que la indagación.
3. **Regla de activos:** el código exigía signo positivo en ES aunque tuviera pocos eventos; ahora cumple lo escrito en §2 (ES sólo
   cuenta con ≥ 100 eventos reales en la celda).
4. **Minuto del día:** era la hora del reloj ET, que parte la sesión CME en dos (cruza medianoche); ahora son minutos desde la
   apertura (18:00 ET).
5. **Flujo de zonas en el control:** valía 0 (neutro) y caía en el estrato del medio; el control no tiene zonas → sin dato.
6. **`salida_s` medía otra cosa:** arrancaba en la salida a X/4 (no cuando el precio deja el rango). Ahora va desde el último tick
   dentro del rango hasta estar a X/2.
7. **EMAs:** sin dato hasta que la EMA se asienta (9 + 5 y 21 + 5 velas de la sesión).

Mejoras de medición («expansión limpia» en tres partes, todas causales):
- `salida_s` (corregida, arriba); `salida_eficiencia`: desplazamiento / camino recorrido en ese tramo (1 = línea recta);
  `pasada_s`: segundos dentro del rango en la visita anterior (la última pasada del precio por el cluster; chico = la cruzó rápido).
- Picos: misma definición, pivotes calculados una vez por sesión (antes O(velas²) por evento). Aclaración: los picos «dentro» que
  sobreviven al toque son en la práctica los del lado de llegada (los del otro lado ya los tomó el precio al llegar).

Pruebas: 23 rasgos × 3 = **69** celdas exploratorias (+6, `hft_ruptura/indaga_c`). Selección (§2) y réplica (§3) sin cambios.
`n_zonas`, `packing` y `flujo_alineado` no existen en el control: su comparación contra control queda vacía y la regla de selección
los evalúa sólo por umbral, meses y activos.
