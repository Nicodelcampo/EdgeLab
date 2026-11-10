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
  activo. Es descriptiva: no decide nada por sí sola. Pruebas contadas: 15 × 3 = **45** (`hft_ruptura/indaga`).
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
