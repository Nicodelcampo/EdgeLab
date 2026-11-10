# Pre-registro — HFT-CONTEXTO: el rebote según cantidad, cercanía y antigüedad de los otros clusters

Estado: PRE-REGISTRO (commiteado antes de correr y antes de conocer el resultado de HFT-REBOTES). Fecha: 2026-11-10. Pedido de Nico.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `HFT_CLUSTERS_INFO`. Etapa **EF2/EF3 información**. Código: `edgelab/research/hft_contexto.py`, modo `contexto` del kernel,
`tools/hft_clusters_info.py contexto`. Tests: `tests/research/test_hft_contexto.py`.

## 1. Sobre qué eventos
UNA definición de rebote, elegida con regla mecánica (`hft_contexto.elegir_definicion`): entre las nominadas por BH en HFT-REBOTES,
la de más eventos reales; si no hay nominadas, `D0_BASE` (la de más eventos por construcción). Mismos clusters (E0-b, NQ y ES),
misma ventana DESC, misma carrera ±X.

## 2. Variables (en el instante del evento; sólo clusters ya detectados y vivos; distancias en X con signo según el rebote)
| Variable | Estratos | Contraste (A vs B) | Signo esperado | Hipótesis |
|---|---|---|---|---|
| respaldo (clusters en y ∈ [−1, 0]) | 0 · 1 · ≥2 | ≥2 vs 0 | + | defensa en profundidad |
| obstaculo (más cercano con borde en y ∈ (0, 1]) | ninguno · cerca (≤ 0,5) · lejos | cerca vs ninguno | − | un nivel en el camino frena antes de +X |
| densidad (clusters en y ∈ [−2, 2]) | 0 · 1–2 · ≥3 | 0 vs ≥3 | sin dirección | nivel aislado concentra liquidez / niveles juntos se diluyen |
| confluencia (otro cluster solapa el tocado) | no · sí | sí vs no | + | dos niveles independientes en el mismo precio |
| mas_nuevo (el tocado es el más nuevo en ±2X) | no · sí · sin vecinos (fuera) | sí vs no | + | el nivel más reciente pesa más |
| huella (clusters nacidos durante la excursión) | 0 · ≥1 | 0 vs ≥1 | sin dirección | ida limpia (expansión) vs ida con actividad HFT |

Variables correlacionadas a propósito (respaldo, densidad y confluencia comparten clusters): se informan juntas, no se interpretan
como efectos independientes.

## 3. Estadístico y decisión
- **Compuerta de potencia (sólo conteos, sin retornos):** cada estrato del contraste necesita ≥ 150 eventos reales (NQ + ES); si no,
  la variable queda SIN_POTENCIA y no se prueba.
- **Prueba principal:** entre eventos REALES, diferencia del desenlace medio A − B, bootstrap por sesión (activo, fecha); p de una cola
  donde hay signo declarado y de dos colas donde no. **BH q 0,10 entre las variables probadas.** Pruebas: 6 (`hft_clusters_info/contexto`).
- **Diagnóstico (no entra al BH):** el mismo contraste en los pseudo-clusters de control (otra hora de la sesión, lejos en precio de
  clusters reales vivos), con su contexto respecto de los clusters reales. Si el control muestra el mismo efecto, lo que mide la variable
  es la estructura del precio alrededor (hora, volatilidad, tendencia), no el cluster vecino; se informa la diferencia en diferencias.
- **Descriptivo:** distancia al obstáculo (para estudiar un objetivo natural), edad del tocado, conteos por activo.
- Una variable nominada pasa a la réplica abr → sep sólo si su diferencia en diferencias tiene el mismo signo.

## 4. Cómo podría refutarse
Ninguna variable con potencia y efecto; o efectos que el control reproduce (estructura del precio, no clusters); o efectos en un solo activo.

## 5. Riesgos declarados
- En el control no existen «confluencia» ni respaldo pegado al borde (se descartan los pseudo-clusters solapados con reales vivos):
  esas dos variables no tienen diagnóstico completo.
- Con 10–20 clusters por sesión casi todo evento tiene vecinos: «densidad 0» y «obstáculo ninguno» pueden no pasar la compuerta.
- Diseño escrito después de conocer el E0 y el E0-b (sin retornos) y sin conocer ningún resultado con retornos.

## 6. Salida como guía, no como 0/1 (enmienda 2026-11-10, antes de cualquier resultado; pedido de Nico)
Cada resultado de esta familia (`info`, `rebotes`, `contexto`) se traduce automáticamente, al traerlo, en `RECOMENDACIONES_<modo>.md`
con `edgelab/research/recomendador.py`: por ítem, una categoría, una lectura, el próximo análisis sugerido y una prioridad, y la lista
ordenada de «qué hacer después». Reglas fijadas acá, antes de ver nada:
| Categoría | Cuándo | Qué sugiere |
|---|---|---|
| CONFIRMAR | nominada por BH, sin las alertas de abajo | réplica congelada + la indagación específica del ítem |
| INDAGAR | diferencia ≥ MDE/2 o IC90 que excluye 0, sin nominar | la indagación específica (`SUGERENCIAS` de cada módulo) |
| ESTRUCTURA_DE_PRECIO | el control muestra el mismo signo y ≥ la mitad del efecto | medir la variable de precio directamente como familia aparte |
| INCONSISTENTE | signo opuesto entre activos (ambos ≥ 1 error estándar) | indagar por activo antes de combinar |
| SIN_MUESTRA | no pasa la compuerta o MDE > 0,25 | cuánta muestra falta y de dónde sacarla |
| DESCARTAR | MDE ≤ 0,10 y diferencia < MDE/2 | NO_REPETIR con su MDE |
| NO_CONCLUYENTE | el resto | en espera |
Prioridad = peso de la categoría × |z| × 1,5 si el grupo de interés ya supera 0,08 en bruto × 1,3 si la dosis-respuesta es monótona.
Las recomendaciones no cambian las reglas de decisión de los pre-registros: ordenan qué mirar después. Toda indagación sugerida se
pre-registra aparte antes de correr.
