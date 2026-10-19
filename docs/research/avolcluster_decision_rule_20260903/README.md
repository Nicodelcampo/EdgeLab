# Regla de decisión robusta en aVolClusterPOI — qué se midió y qué se eligió

Fecha: 2026-09-03 · autorizado por Nico ("mantener aVolClusterPOI tal cual y
cambiar sólo la regla de decisión") · población: **22.507 bloques** de
`avolcluster_v05_NQ0626_120t_DIAG_20260901.csv` (NQ 06-26, 120t), celdas crudas.

## El defecto, cuantificado

La regla v0.5 marca hot a la celda con `vol >= mediana × 2`. Sobre los 22.507
bloques reales:

| | |
|---|---|
| celdas por bloque (mediana / media) | 84 / 93,2 |
| celdas hot por bloque (mediana / media) | 14 / 16,6 |
| fracción `hot/n` (mediana / media) | 0,1687 / 0,1708 |
| **bloques con ≥1 celda a un contrato del umbral** | **20.167 (89,60 %)** |

Ese último número es el defecto: en nueve de cada diez bloques, **un contrato de
diferencia entre NT8 y el parquet cambia el conjunto hot**. No hace falta que el
dato esté mal; alcanza con la ambigüedad de ±1 que ya está medida entre las dos
fuentes.

## Qué se probó, todo sobre los mismos bloques y con ruido de ±1 contrato

Turnover = la geometría de la zona elegida (`lower`, `upper`) cambia.

| variante | turnover | altura mediana |
|---|---:|---:|
| `median × 2` (v0.5) | **30,87 %** | 9 t |
| **`top-K`, K = 0,17·n** | **24,47 %** | 8 t |
| `top-K` + recorte de bordes al 25 / 40 / 55 % del pico | 24,03 / 23,29 / 22,34 % | 8 / 8 / 7 t |
| `top-K` con volúmenes cuantizados a 3 / 5 / 10 | 29,15 / 30,18 / 31,65 % | — |
| `median` + recorte al 40 % | 27,86 % | 8 t |
| área de valor 20 % (intervalo mínimo con 20 % del volumen) | **15,82 %** | 8 t |
| área de valor 30 / 40 / 50 % | 19,43 / 23,32 / 26,50 % | 13 / 19 / 26 t |

Tres cosas que enseña la tabla y no eran obvias:

- **La cuantización empeora.** Redondear los volúmenes crea empates masivos, y un
  contrato que cruza un cuanto salta por encima de todas las celdas empatadas.
- **Recortar los bordes casi no ayuda.** La inestabilidad no está en el borde de
  la zona sino en la **membresía** del conjunto hot, que después el clustering por
  gap amplifica al fusionar o partir clusters.
- **El jaccard mediano es 1,000 en todas las variantes**, y en `top-K` el 85,5 %
  de las zonas conserva jaccard ≥ 0,8 y el 86,9 % mueve el centro ≤ 1 tick. El
  turnover por igualdad exacta **sobreestima** la inestabilidad: cuenta como
  cambio total un corrimiento de un tick en el borde.

## Qué se implementó

`UseTopKHotCells` (NT8) / `hot_selection="topk"` (Python). **Por defecto apagado**:
sin tocarlo, el indicador se comporta exactamente como la v0.5, así que los
oráculos y las campañas existentes no cambian.

Con el switch encendido cambia **sólo** la selección de celdas hot: las K de mayor
volumen, `K = round(0,17 × n_celdas)`, empates por tick ascendente. `HotFraction`
0,17 sale de la mediana empírica de `hot/n` (0,1687), así que el tamaño del
conjunto se preserva. **El clustering por gap, el umbral histórico por percentil,
el score y la geometría son idénticos.**

## Lo que NO se logró, dicho sin vueltas

El contrato `PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md` pide turnover < 5 %.
**Ninguna variante llega**: la mejor por igualdad exacta es el área de valor con
15,82 %, y la elegida da 24,47 %.

La razón es estructural: la zona se define con resolución de **un tick**, y los
volúmenes por celda son enteros chicos con muchos empates. Cualquier regla que
elija celdas individuales tiene un borde poblado. Alcanzar < 5 % exige cambiar la
definición de la geometría —no la regla de decisión— y eso es lo que hace
`AVolZonePOI_P.cs`, que se dejó de lado por ser demasiado distinto del original.

**El área de valor al 20 % es la alternativa intermedia**: casi la mitad del
turnover (15,82 %), misma altura mediana (8 t) y sigue siendo "dónde se concentró
el volumen". No se implementó porque cambia la definición de la zona y eso excede
lo autorizado. Queda registrado como la próxima opción si 24,47 % no alcanza.

## Advertencia sobre el comportamiento en el chart

Con `top-K` **siempre** hay K celdas hot, así que se forma cluster en el 100 % de
los bloques contra el 93,5 % de la regla original. Eso **no** significa más zonas
dibujadas: el umbral histórico por percentil sigue siendo el que crea la zona.
Pero la distribución de `best_score` cambia, y ese umbral se calibra sobre
`best_score`. **Antes de usarlo en producción hay que comparar las dos versiones
sobre el mismo chart**, no asumir equivalencia.

## Cómo podría refutarse

Si al correr las dos versiones sobre el mismo chart la cantidad o la ubicación de
las zonas cambia de forma material, la premisa "misma funcionalidad, sólo más
estable" es falsa y el switch debe quedar apagado. La medición es directa: dos
corridas con `DiagBlockExportPath` distinto y comparación de `decision` y
geometría bloque a bloque.
