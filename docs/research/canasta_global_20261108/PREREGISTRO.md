# Pre-registro: CANASTA-GLOBAL — reglas estables y diversificadas entre todas las familias medidas (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr; regla global de Nico en `docs/DECISIONES_20261108.md`, pedido «arrancá por el
punto 2»). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa EF4. Familia CANASTA_GLOBAL, hija de todas las familias de los cubos (hereda su multiplicidad vía el nulo de la selección).

**Pregunta:** entre todas las celdas de las 106 grillas ya corridas en R, ¿existe una canasta de reglas estables en sub-bloques
independientes, poco correlacionadas y de varios activos, cuya probabilidad de ser azar (contando la selección) sea < 0,10?

**Justificación económica:** una regla con edge real se repite en períodos independientes; varias reglas así, poco correlacionadas,
suman su esperanza y diluyen su ruido. **Cómo podría refutarse:** p de la selección ≥ 0,10, o la canasta no es positiva en el holdout.

**Datos:** los cubos de `docs/research/regimen_cubos/handles.json` (dataset `nicolasbuttaro/edgelab-cubos-regimen`), R neto por
operación con costos canónicos. Ventana común 05/08/2025 → 30/09/2026 (nunca el holdout), 5 sub-bloques de igual número de sesiones.

**Selección (`edgelab/research/canasta_global.py`, fija):**
1. Celda evaluable: ≥ 30 operaciones en la ventana.
2. Estable: R diario medio > 0 en al menos 4 de 5 sub-bloques y t diario > 1 (días sin operar = 0).
3. Por cubo, las 20 estables de mayor t.
4. Global, en orden de t: se agrega si su correlación diaria con cada elegida es < 0,3, máximo 3 por cubo, hasta 10 reglas; al menos
   3 instrumentos o la canasta queda vacía.
5. Estadístico: t diario de la canasta igual ponderada.

**Probabilidad de azar:** inversión de signo por sesión (el mismo signo para todos los cubos ese día), B = 200, repitiendo 1–5.
p = (1 + #réplicas con t ≥ observado) / 201. **Meta de Nico: p < 0,10.**

**Después:** si p < 0,10, apertura exploratoria del holdout (modo de `edgelab/autopilot/holdout_apertura.py`) con la canasta
congelada y combinación Fisher con p_selección, pre-registrada aparte antes de abrir. Si p ≥ 0,10, no se abre.

**Limitaciones:** las celdas de los cubos ya se miraron en DESC y réplica; el nulo repite la selección completa, así que la búsqueda
queda corregida, pero la elección del universo (qué familias existen) no lo está. Los cubos de distintas familias sobre el mismo
instrumento y horario están correlacionados; el nulo por sesión lo conserva.
