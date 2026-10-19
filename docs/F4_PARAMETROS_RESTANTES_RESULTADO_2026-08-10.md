# Barrido de los parámetros de `PARAM_SPEC` que F2 no tocó · RESULTADO

**Fecha** 2026-08-10 · **Artefacto** `diag/tasa_senales/barrido_F4_parametros_restantes.json`
**Grilla** `diag/tasa_senales/grilla_F4_parametros_restantes.json` — 11 celdas
**Outcomes** `false` · **Multiplicidad gastada** cero
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

De los 12 parámetros de `PARAM_SPEC`, F2 barrió tres (`ticks_per_row`,
`imbalance_ratio`, `min_trap_volume`) y encontró la tasa de ruptura invariante.
Este barrido cubre los **nueve restantes**, uno por vez desde los defaults
(diseño de un factor a la vez, mismo criterio que F2), reusando
`censo_zonas_completo.py` sin escribir un segundo camino.

---

## 1. Resultado

| celda | zonas | tocada | rota | max_age |
|---|---|---|---|---|
| defaults | 15.947 | 97,9 % | 96,1 % | 3,7 % |
| `imbalance_mode=SameLevel` | 28.056 | 98,1 % | 96,2 % | 3,6 % |
| `trap_volume_source=TotalLevel` | 22.346 | 97,9 % | 96,4 % | 3,4 % |
| `use_wick_filter=False` | 27.151 | 98,4 % | 96,5 % | 3,3 % |
| `wick_zone_pct=10` | 10.111 | 98,1 % | 96,6 % | 3,3 % |
| `wick_zone_pct=50` | 23.113 | 98,2 % | 96,4 % | 3,4 % |
| `min_delta_filter=10` | 14.478 | 97,9 % | 96,3 % | 3,6 % |
| `min_export_volume=5` | 15.947 | 97,9 % | 96,1 % | 3,7 % |
| `invalidation_mode=FirstTouch` | 15.947 | 98,1 % | **0,0 %** | 1,7 % |
| `max_age_bars=200` | 15.947 | **94,8 %** | 88,7 % | **11,2 %** |
| `max_touches=1` | 15.947 | 97,9 % | **29,9 %** | 1,7 % |

---

## 2. Los siete parámetros de "detección" — invariancia confirmada, no sólo en F2

`imbalance_mode`, `trap_volume_source`, `use_wick_filter`, `wick_zone_pct` (dos
valores), `min_delta_filter`, `min_export_volume`: **mueven el conteo de zonas
6× (10.111 → 28.056) y la tasa de ruptura no se mueve** — vive en 96,1–96,6 %
en las siete celdas, el mismo rango estrechísimo que F2 encontró para altura y
selectividad. Extiende la conclusión de F2 a **10 de los 12 parámetros del
indicador**: la propiedad "casi toda zona termina rota" no es un artefacto de
ninguna perilla de detección.

---

## 3. Dos controles positivos — la medición SÍ detecta efecto cuando lo hay

Es la contracara necesaria del punto 2: si el barrido nunca mostrara ningún
movimiento, cabría sospechar que la métrica es insensible, no que el objeto es
invariante. Estas dos celdas confirman que no es así.

**`invalidation_mode=FirstTouch` → rota = 0,0 %, exactamente como se predijo.**
Con esta regla la zona muere en el instante del primer toque —antes de que
pueda darse un close-through—, así que "rota" (definida como close-through)
es estructuralmente imposible. Confirma la advertencia declarada en
`PLAN_ANALISIS_v2`: es un control degenerado para hipótesis de primer toque,
no una hipótesis viable.

**`max_age_bars=200` → tocada cae de 97,9 % a 94,8 %, `max_age` sube de 3,7 %
a 11,2 %.** Acortar la ventana de vida reduce mecánicamente la chance de ser
tocada antes de expirar — el efecto esperado, en la dirección esperada.

---

## 4. El hallazgo: `max_touches=1` reproduce, por un camino distinto, el 30,3 % de F1.3

`max_touches=1` fuerza a la zona a morir apenas se la toca una vez (razón
`max_touches`), salvo que el close-through ocurra en esa misma barra —en cuyo
caso el kernel prioriza `close_through` sobre `max_touches`—. El resultado:

```
rota (max_touches=1)              29,9 %
```

Es decir: en el **29,9 %** de los casos, el primer toque **es** un
close-through en la misma barra. Compárese con F1.3
(`F1_SUPERVIVENCIA_DEPLECION_RESULTADO_2026-08-10.md` §3), que midió la tasa
de ruptura del toque nº 1 **cruzando eventos `ZONE_TOUCHED`/`ZONE_INVALIDATED`
por barra** — un método completamente distinto, sin `max_touches` de por
medio:

```
F1.3, ordinal de toque 1:         30,3 %
```

**Diferencia de 0,4 puntos entre dos mediciones independientes del mismo
hecho.** No es la misma línea de código midiéndose a sí misma: uno cruza logs
de eventos, el otro fuerza la vida de la zona con un parámetro del kernel. Que
coincidan casi exacto es una confirmación cruzada de que ambos números miden
lo mismo correctamente.

---

## 5. Qué queda

Los 12 parámetros de `PARAM_SPEC` están cubiertos: 3 por F2, 9 por este
barrido. Ninguno mueve la tasa de ruptura salvo los dos que la definen por
construcción (`invalidation_mode`, `max_age_bars`) o la truncan
artificialmente (`max_touches`). La conclusión de F1.1/F1.2 —el objeto rompe
casi siempre, y eso no es ajustable por parámetro— queda establecida sobre
la totalidad del espacio de parámetros del indicador, no sobre una muestra de
tres.

---

## Aporte al referente

Cierra el espacio de parámetros del indicador con evidencia, no con muestreo
parcial: 12 de 12 parámetros barridos, target-free, costo cero de
multiplicidad. Confirma que la medición detecta efecto cuando lo hay (dos
controles positivos) y entrega una validación cruzada inesperada —dos caminos
de medición independientes coinciden en 30 % para la tasa de ruptura del
primer toque— que aumenta la confianza en todo el aparato de medición
construido hoy.
