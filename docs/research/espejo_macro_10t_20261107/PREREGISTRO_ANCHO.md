# Pre-registro: ESPEJO-MACRO-10T-ANCHO, ES e YM (07/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2**.
Pedido de Nico: «que sí aparezcan operaciones donde no alcanzan».

## Por qué

Con los topes en tiempo (`PREREGISTRO_TIEMPO.md`), ES siguió con **0 celdas evaluables**: 17,7 M velas y 18 disparos.

El cuello era el **ancho mínimo**: 10 viajes de fricción severa en la mitad que falta, o sea W ≥ 37,75 pts de ES. NQ recorre unas 4
veces más puntos que ES, así que ahí el mismo criterio sí deja pasar eventos.

## Cambio único (`edgelab/research/espejo_macro_ancho.py`)

- Mínimo laxo de **5 viajes** y perilla de ancho en **5, 10 o 20** viajes.
- La celda ≥ 10 es la regla anterior. 5 es el piso: por debajo, la fricción se come lo que falta hasta A.
- **Tamaño:** 31.104 celdas por canal.

## Selección

El cambio se hizo después de ver que ES no tenía eventos. No se miró ningún P&L de ES.

## Campañas

ESPEJO10TA-ES y ESPEJO10TA-YM. Familias hijas con linaje desde la variante en tiempo de cada activo. NQ y GC no se relanzan.

## Cómo podría refutarse

Ninguna celda nominada por FDR q 0,10 y ninguna pista que replique.
