# Pre-registro: barrido ESPEJO-MACRO-10T, sin lógica condicional (07/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2 exploratorio**.
Pedido de Nico: «medí si hay alguna ventaja en esta lógica así como está, pasando por todo el embudo, con un barrido de varios
parámetros y grillas de entradas; primero lo observamos sin ningún agregado».

## La lógica

Es la de `REGLA.md` de esta carpeta (detector `espejo_macro_10t.py` de foundation), portada a numba en
`edgelab/research/espejo_macro_grilla.py`, con tests en `tests/research/test_espejo_macro_grilla.py`:

- Velas de **10 ticks** dentro de la sesión. La campaña declara `ticks_por_barra: 10` y el embudo entero corre en esa resolución.
- **Impulso de A a B**, ancho y limpio: ningún cierre devuelve más de `retro` de lo recorrido (se mide en el cierre).
- **Vuelta**, igual de limpia. El **evento es el primer cierre que deshace la fracción f de W**.
- **Orden en el sentido de la vuelta (hacia A)**, entrada a mercado en el primer tick de la vela siguiente.

## Dos correcciones del detector original, hechas antes de lanzar

1. **Causalidad.** El original probaba inicios en orden y saltaba al cierre del primer candidato. Un inicio temprano que se completaba
   tarde tapaba candidatos posteriores ya confirmados, así que **el futuro decidía qué disparos existían**. El certificado de causalidad
   lo atrapó. Ahora cada inicio tiene su vela de confirmación y se recorren en orden de tiempo.
2. **A es el origen real:** el cierre de A es el extremo de las 8 velas previas. Si no, un inicio a mitad de la subida se confirmaba
   antes y medía un W menor.

## Grilla (23.328 celdas por canal)

Un solo pase de detección con los umbrales más laxos; los umbrales de la regla son perillas medidas.

- **fracción de entrada:** 25 / 50 / 75 %.
- **retroceso de la ida:** ≤ 0,20 / 0,30 / 0,40.
- **retroceso de la vuelta:** ≤ 0,20 / 0,30 / 0,40.
- **ancho** en viajes de fricción severa sobre la mitad que falta: ≥ 10 / 20 / 40. En NQ, W ≥ 51 / 102 / 204 pts.
- **duración de la ida:** tercil bajo / alto / cualquiera.
- **ritmo de la vuelta** relativo a la ida: tercil bajo / alto / cualquiera.
- **RTH** (9:30–16:00 NY): sí / no / cualquiera.

**Ejecuciones (6):**
- stop un tick más allá de B, o 10 % de W más allá de B;
- objetivo en A, en el 75 % del ancho deshecho, o 2R.

**Salidas comunes:** tope de 2000 velas de 10 ticks (horas), cierre a fin de sesión y salida forzada por noticias tier1, sin entradas a
±5 min de un dato. P&L en R con costos canónicos del futuro.

## Campañas

| Campaña | Señal y ejecución | Familia (linaje: hereda de ESPEJO_REGLA, bruto) |
|---|---|---|
| ESPEJO10T-NQ | NQ | ESPEJO_MACRO_10T_NQ |
| ESPEJO10T-ES | ES | ESPEJO_MACRO_10T_ES |
| ESPEJO10T-YM | YM | ESPEJO_MACRO_10T_YM |
| ESPEJO10T-GC | GC | ESPEJO_MACRO_10T_GC |

DESC del 2025-08-05 al 2026-03-31; réplica abr–sep 2026; holdout sellado desde 2026-10-01 con N fijo 150. Cada familia hereda la
multiplicidad bruta de ESPEJO_REGLA. Las pruebas se cuentan en el contador global al lanzar.

## Cómo podría refutarse

Ninguna celda nominada por FDR q 0,10 en DESC y ninguna pista que replique; o un R neto que sólo aparece con el objetivo más corto.
Un nulo sin potencia no cierra la familia (`ESPEJO_MEDIDO_Y_NO_MEDIDO.md`).

## Justificación económica

Un impulso que recorre precio sin aceptación tiende a deshacerse cuando el empuje afloja. Si la vuelta ya deshizo una fracción limpia,
lo que falta hasta A es largo frente a la fricción (el ancho mínimo lo garantiza en viajes de fricción severa).

## Después

Con este resultado se agrega la lógica condicional que pida Nico, como familia hija con linaje.
