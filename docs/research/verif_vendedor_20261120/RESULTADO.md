# Verificación de las curvas del vendedor de FundedSync con los datos de EdgeLab (2026-11-20)

Estado: RESULTADO — descriptivo sobre operaciones ya medidas (`m1_largo_20261117/FS_OPS_NQ.csv.gz`: los 15 módulos, M1 de NQ de NT8,
fricción canónica de 1,5455 puntos por viaje). No cuenta pruebas ni elige reglas.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `MODULOS_2022_2026.csv` y `CURVAS_EDGELAB.png`.

Episodios: cada módulo, por ventana, en la tabla de abajo.

## La forma de las curvas del vendedor se reproduce en 2022–2026
En puntos netos, 14 de los 15 módulos suben en 2022-01 → 2026-09, igual que en el gráfico del vendedor. La única que no sube es W.

| Módulo | Ops/mes | Neto (pts) | t mensual 2022–26 | t mensual 2010–21 | Bruto → neto (pts) |
|---|---|---|---|---|---|
| T | 19 | +18.990 | **5,81** | 1,51 | 20.667 → 18.990 |
| R | 2,8 | +9.985 | **4,54** | 2,35 | 10.229 → 9.985 |
| Z | 2,5 | +4.564 | **2,79** | 1,76 | 4.780 → 4.564 |
| A20 | 19,7 | +10.757 | **2,57** | −2,96 | 12.491 → 10.757 |
| N | 10 | +3.723 | 1,80 | 0,89 | |
| S | 38 | +9.449 | 1,76 | −3,66 | 12.824 → 9.449 |
| F | 7,7 | +2.045 | 1,62 | −0,35 | |
| Q | 24 | +1.464 | 1,52 | −6,66 | 3.558 → 1.464 |
| C | 5,4 | +2.144 | 1,49 | −0,62 | |
| A1 | 76 | +2.884 | 1,35 | −16,0 | 9.607 → 2.884 |
| V | 18 | +1.894 | 1,09 | 1,41 | |
| P | 11 | +2.115 | 1,08 | −2,19 | |
| O | 6,4 | +1.317 | 0,78 | 3,15 | |
| E | 19 | +395 | 0,34 | −2,58 | 2.060 → 395 |
| W | 103 | −626 | −0,18 | −7,07 | 8.420 → −626 |

## Por qué una curva que sube no alcanza
1. **Ventana elegida.** El gráfico empieza en 2022, cuando NQ cuadruplicó su precio y la fricción relativa ya era baja.
   - En 2010–2021, S, Q, A1, W, P, E y A20 eran negativas y con t significativo.
   - Sólo T, R, Z, O y V eran positivas antes.
2. **Ruido.** Con 57 meses, una curva que sube con t mensual < 2 no se distingue del azar. Tienen t ≥ 2,5 sólo T, R, Z y A20, que son
   justamente las que EdgeLab marcó como candidatas.
3. **Fricción.**
   - A1 pierde el 70 % de su bruto en costos.
   - W y E pierden casi todo.
   - Si el vendedor grafica sin costos o con comisiones de broker barato, sus curvas salen más empinadas que las de una cuenta prop.
4. **Puntos y no R.** En puntos, las operaciones con stop lejano pesan más. Medidas en R, A1 (+0,015), Q (−0,005) y V (+0,018) son ≈ 0
   por operación.
5. **Selección.** El vendedor muestra 15 módulos ya elegidos de su propio desarrollo. Eso no es fuera de muestra.

## Lectura
- **No hay estrategias validadas que nos estemos perdiendo.** Las del gráfico con curva fuerte en 2022–26 (T, A20, R y Z) son las mismas
  que tenemos como candidatas. Q, O y P se ven bien en el gráfico, pero en nuestros datos dan t < 2 y eran negativas o neutras antes de 2022.
- **Las que quedan como pista, no candidatas:** N, S, F, Q y C (t 1,5–1,8 desde 2022). Su única confirmación posible es el forward,
  porque esos meses ya están todos vistos.
- **Lo que no se puede verificar:** el eje del vendedor no tiene unidad ni costos declarados, y sus curvas A/B no dicen tamaño. No podemos
  saber si son con o sin fricción.

## Adenda: desde el 1-sep-2025, fecha en que el vendedor empezó a vender (fuera de su muestra)
Dato de Nico. Asumimos 2025, porque el gráfico del vendedor llega a 2026. Ventana: 2025-09-01 → 2026-09-30, todavía antes del holdout
terminal. En EdgeLab estos meses ya estaban vistos.

| Módulo | Ops | Neto (pts) | t mensual | % meses + |
|---|---|---|---|---|
| R | 31 | +3.494 | 3,57 | 100 % |
| T | 238 | +4.163 | 1,90 | 54 % |
| N | 116 | +2.590 | 1,79 | 64 % |
| A1 | 989 | +2.325 | 1,71 | 69 % |
| C | 62 | +922 | 1,48 | 77 % |
| P | 131 | +1.362 | 1,32 | 77 % |
| Z | 31 | +1.630 | 1,23 | 73 % |
| A20 | 240 | +2.858 | 1,11 | 62 % |
| Q | 306 | +735 | 1,09 | 62 % |
| S | 423 | +2.795 | 0,98 | 62 % |
| F | 45 | +543 | 0,91 | 64 % |
| V | 264 | +751 | 0,86 | 69 % |
| O | 15 | +230 | 0,29 | 50 % |
| E | 254 | −204 | −0,45 | 38 % |
| W | 1.317 | −1.024 | −0,54 | 31 % |

Lectura: en los 13 meses de producto, 13 de 15 módulos son positivos. Sólo R tiene t > 2, y con 13 meses el MDE es grande: un nulo no mata.
Gráfico por módulo: `MODULOS_POR_SEPARADO.png`.

## Adenda 2: comparación visual con la foto del vendedor (ventana 2022-01 → 2026-03, bruto y neto)
Gráfico: `BRUTO_NETO_VENTANA_VENDEDOR.png`. La foto del vendedor no tiene unidades, así que se comparan formas y orden, no niveles.

| Módulo | Vendedor | EdgeLab bruto | EdgeLab neto | Lectura |
|---|---|---|---|---|
| T | sube parejo, de las más altas | sube parejo | igual | coincide |
| A20 | volátil, salto en 2022, sube en 2024–26 | igual | igual | coincide |
| R | sube moderado | sube | igual | coincide (cambia el tamaño) |
| **W** | **de las mejores, sube fuerte** | **sube fuerte (+16k)** | **≈ 0** | **el vendedor coincide con el bruto: la fricción de 5.236 operaciones se come todo** |
| **Q** | sube parejo | sube parejo (+5,8k) | plano hasta 2025 | coincide con el bruto |
| A1 | casi plano, sube al final | sube (+14,5k) | plano/negativo hasta 2025 | entre el bruto y el neto |
| **S** | **negativa 2022–24, vuelve a ≈ 0** | positiva, salto en 2025 | igual | **NO coincide** |
| **O** | **positiva desde 2022, de las más altas** | negativa hasta 2024 | igual | **NO coincide** |
| P | sube fuerte | sube moderado | igual | parcial |
| Z, E, F | ≈ planas | Z y F suben, E con joroba | igual | escala o tamaño distintos |
| N | no está en la foto | — | — | — |

**Conclusión:**
- En W, Q y A1 la curva del vendedor se parece a nuestro **bruto**, es decir sin fricción o con costos de broker barato. Netas de la
  fricción canónica de una cuenta prop, esas tres no tienen ventaja.
- S y O difieren en la forma, no sólo en los costos: o nuestra traducción de esos módulos no calca el original, o el vendedor usa otros
  parámetros o datos.
- Para resolverlo hace falta la lista de operaciones del producto original de esos módulos.
