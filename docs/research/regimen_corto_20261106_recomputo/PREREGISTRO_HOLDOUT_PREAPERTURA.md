# Pre-registro: apertura del holdout de PREAPERTURA-ES y PREAPERTURA-NQ (07/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Pedido de Nico (07/11):
«abrí el holdout de las dos PREAPERTURA».

## Reglas congeladas

Recalculadas contra ticks con resultado idéntico a la serie publicada (`RESULTADO.md` de esta carpeta):

| Regla | Campaña (cortes) | Celda | Familia LORD++ |
|---|---|---|---|
| PREAPERTURA-ES | PREAPERTURA-ES-R | [2, 0, 1, 0, 0, 5] | RANGO_PREAPERTURA_ES |
| PREAPERTURA-NQ | PREAPERTURA-NQ-R | [2, 0, 0, 0, 1, 5] | RANGO_PREAPERTURA_NQ |

Sin tope.

## Cómo se eligieron (para leer el resultado con justicia)

**No** salieron del embudo, que no las nominó: en la réplica las pistas no confirmaron. Salieron de la canasta estática del régimen corto
(Gemini, `regimen_corto_20261106/RESULTADO_CANASTA_ESTATICA_20261107.md`), es decir, de mirar el desarrollo completo, réplica
incluida. Es una **nominación forzada** (excepción humana, como la del 02/11). Se espera la maldición del ganador.

## Decisión, por regla, fijada antes de mirar

- Muestra: las **primeras 150 operaciones desde 2026-10-01**, en el dataset sellado y sólo en sesiones válidas.
- Prueba: el paso de LORD++ **reservado ahora** para la familia.
- Veredicto:
  - **CONFIRMADA** si rechaza y la media en R es > 0;
  - **REFUTADA** si la media es ≤ 0;
  - **SIN_POTENCIA** en cualquier otro caso.
- Con menos de 150 operaciones disponibles el veredicto es **EN CURSO**: se suman las de noviembre en papel con el e-proceso.
- El resultado no se usa para elegir, ajustar ni reintentar. Una apertura por familia.

## Cómo podría refutarse

La media en R del holdout es ≤ 0 en alguna de las dos.
