# Resultado — U1-CRUZADO congelada trasladada al oro (señal XAU, operación GC)

Estado: VIGENTE. Etapa EF3. Pre-registro: `PREREGISTRO_U1_ORO.md` (commit `1f7cffeb`). Salida: `U1_ORO.json`, `U1_ORO_operaciones.csv`.
Kernel `nicolasbuttaro/u1-oro-transferencia` v1. Escala: rango M1 mediano de USATECH en el descubrimiento de U1 = **6,25 pts**; el factor
del oro fue 0,06–0,43 según el trimestre (W de 2,5 a 17,3 USD). 440 señales en XAU 2023-04 → 2026-09.

| período | ejecución | operaciones | media neta (USD/oz) | IC90 sesiones | p | MDE | acierto | peor |
|---|---|---:|---:|---|---:|---:|---:|---:|
| proxy XAU 2023-04 → 2025-08 | T1 | 275 | **−0,67** | [−1,34, −0,04] | 0,95 | 0,99 | 68 % | −48,7 |
| proxy XAU 2023-04 → 2025-08 | T3 | 282 | −0,33 | [−1,05, +0,36] | 0,78 | 1,07 | 66 % | −48,7 |
| cruzado GC 2025-08 → 2026-09 | T1 | 112 | +0,60 | [−1,62, +2,79] | 0,32 | 3,33 | 80 % | −43,9 |
| cruzado GC 2025-08 → 2026-09 | T3 | 115 | +1,05 | [−1,37, +3,53] | 0,23 | 3,71 | 75 % | −43,9 |

- Las mismas señales del período cruzado operadas en el propio XAU dan −0,47 (T1) y −2,06 (T3): la diferencia con GC es ruido o
  ejecución, no se interpreta.
- **Filtro de noticias** (declarado en el pre-registro; sin hora de salida en el CSV, se excluye toda operación cuya tenencia máxima
  de 241 min toca una ventana tier 1 de ±1 min): GC T1 +0,32 [−2,15, +2,81] (13 excluidas), T3 +0,76 [−1,95, +3,54] (14); proxy T1
  −0,59, T3 −0,33. Vale el más conservador.

## Decisión (regla del pre-registro)
**INCONCLUSO.** En GC la media es positiva pero sin acercarse a Holm ≤ 0,05 (p 0,23–0,41) y con MDE de 3,3–3,7 USD; no es
NO_TRANSFIERE porque las dos medias en GC son > 0. En el proxy largo de XAU la regla pierde (T1 con IC90 por debajo de cero).

## Lectura
- U1 no se traslada al oro con la fuerza que tenía en NQ: allí la media era ~11 a 18 veces la fricción; acá es del orden de la
  fricción (0,605 USD) y con colas de −44 a −49 USD por operación.
- **Alcance de la muerte**: ninguna; INCONCLUSO no refuta. Tampoco toca a U1 en NQ.
- La grilla `U1-ORO-GRILLA` (escala 0,5/1/2 y todas las perillas de U1-INDAGA) explora el vecindario; parte de este resultado como
  información (linaje `U1_ORO`), no como ancla favorable.
