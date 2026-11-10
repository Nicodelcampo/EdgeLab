# Resultado E0-b (sin retornos) — clusters más grandes, equilibrio entre potencia y fricción

Estado: RESULTADO (2026-11-10). Pre-registro `PREREGISTRO_E0_E_INFORMACION.md` §8, §8.1 y §8.2. Datos: `HFTC_e0b.json` (tabla
completa de 40 definiciones por activo), `HFTC_e0b.csv`. Ventana 2025-07-01 → 2026-03-31. Ningún retorno mirado.

Criterio: menor `borde detectable = 2,49/√N + fricción / ancho mediano`, entre las definiciones con CV mensual ≤ 0,5.

| Activo | Elegida | Eventos | Por sesión | Ancho mediano (pts) | X (pts) | MDE | Fricción en R | Borde detectable | CV |
|---|---|---|---|---|---|---|---|---|---|
| NQ | K8, ancho ≥ X/2, vida 1.800 s | 3.334 | 20,1 | 19,75 | 19,5 | 0,043 | 0,078 | **0,121** | 0,19 |
| ES | K12, ancho ≥ X, vida 1.800 s | 1.821 | 10,2 | 17,0 | 11,25 | 0,058 | 0,052 | **0,111** | 0,49 |
| YM | K4, ancho ≥ X/4, vida 1.800 s | 275 | 1,8 | 36,0 | 64 | 0,150 | 0,140 | 0,290 | 0,29 |
| GC | ninguna elegible (CV 0,78–1,04) | — | — | — | 7,6 | — | — | (mejor no elegible 0,177) | — |

Contra la definición de 4 zonas del E0: NQ pasa de 0,165 a 0,121 y ES de 0,261 a 0,111.

## Lectura
1. **El equilibrio no está en «pocos»: está en «anchos».** En NQ, exigir 8 zonas y 1.800 s de vida lleva el ancho mediano de 9,5 a
   19,75 puntos (igual al stop mínimo) y todavía deja 20 clusters por sesión. En ES, 12 zonas con ancho ≥ X dan 10 por sesión y 17
   puntos de ancho (fricción 0,05 R). Más zonas y más vida ensanchan el cluster sin volverlo raro.
2. **Las tres primeras de NQ son casi la misma población** (K8 con ancho mínimo 0, X/4 o X/2: 3.334 a 3.477 eventos): el filtro de
   ancho casi no corta porque con 8 zonas el cluster ya nace ancho. El eje que manda es la cantidad de zonas y la vida.
3. **YM y GC no sirven con estos umbrales.** YM: 1,8 por sesión y borde 0,29 (ni potencia ni fricción). GC: ninguna definición es
   estable mes a mes (la frecuencia se cae en feb–mar 2026). Confirma que los umbrales en ticks y contratos calibrados para NQ no se
   transportan: para esos dos haría falta reescalar el detector de zonas, que es otra familia de trabajo.
4. **Límite ya declarado (§8.2):** el ancho mínimo se aplica después de detectar; en ES la elegida es justo la de ancho ≥ X y la
   de 16 zonas queda afuera por CV 0,52 contra el tope de 0,5: está en el borde de la regla.

## Qué sigue (sin lanzar)
Paso INFO (rebote e imán) con K8/X½/1.800 s en NQ y K12/X/1.800 s en ES: 2 activos × 2 hipótesis + 2 combinadas = 6 pruebas, a contar
en el registro global al lanzar. YM entra sólo como descriptivo; GC no entra.
