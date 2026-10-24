# Resultados M7 — "un area cargada de OG/VI frena el precio": escalonadas en ES, descubrimiento

Estado: MEDIDO. Manifiesto `MANIFIESTO_M7_ES_AREA_CARGADA_FRENA_20261020.md` (OK + K=350 en `2596686a`, antes de mirar).
Codigo `luximb_m7_es.py`, eventos `RESULTADOS_M7_ES_eventos.csv`. ES 09-25..06-26 (hasta 31-mar-2026), 7.699 escalonadas.

| grupo | n | dias | P(ruptura) | recorrido 60 min (pts) p50 / media | area p50 | P&L rechazo neto 1 tick |
|---|---|---|---|---|---|---|
| T area con >= 3 zonas | 1.144 | 167 | 0,643 | 16,0 / 19,7 | 7,5 | -0,55 |
| C 0-2 zonas | 6.555 | 186 | 0,635 | 19,0 / 23,0 | 6,25 | -0,49 |

| hipotesis (direccion fijada) | estimacion | IC 95 % (por dia) | p unilateral | Holm |
|---|---|---|---|---|
| H1 P(ruptura) T - C < 0 | +0,9 pp | [-2,0, +3,7] | 0,72 | 1,0 |
| **H2 recorrido 60 min T - C < 0** | **-3,3 pts (-14 %)** | **[-4,9, -1,6]** | **0,0002** | **0,0008** |
| H3 H1 emparejado (tamano de area x franja) | +3,5 pp | [+0,7, +6,4] | 0,99 | 1,0 |
| H4 P&L rechazo T > 0 | -0,55 pts | [-0,64, -0,47] | 1,0 | 1,0 |

MDE80: H1 4,1 pp; H2 2,3 pts. Por contrato, el recorrido es menor con zonas en los 4 (09-25 -1,7; 12-25 -2,9; 03-26 -2,1;
06-26 -2,1 pts, este con n = 15). Sensibilidad de umbral (dif. P(ruptura)): >= 2: 0,0; >= 3: +0,9; >= 5: +0,8 pp.

## Lectura
1. **Se replica en ES el canal no direccional de la pista de NQ:** con el area cargada el precio recorre ~14 % menos en la
   hora siguiente (sobrevive Holm; consistente en los 4 contratos). Es la primera regularidad de la familia LUX-IMB que
   pasa una prueba pre-registrada fuera de la muestra donde aparecio.
2. **El canal direccional NO se replica:** en ES la escalonada no rompe menos (H1 nula); emparejando por tamano y franja
   rompe incluso algo mas (H3). "Mas rechazo" queda muerto; lo que queda es "menos recorrido".
3. **No es operable tal cual:** el rechazo pierde neto (H4) y la ruptura tambien. Un efecto de magnitud sin direccion sirve,
   en todo caso, como **filtro de volatilidad** (stops/objetivos, evitar entradas de ruptura sobre areas cargadas), no como senal.
4. **Riesgo de confusion no cubierto por el preregistro:** H2 no se emparejo por la volatilidad previa. Las areas cargadas
   podrian concentrarse en momentos de menor volatilidad (las zonas OG/VI son finas y abundan en mercado lento). Antes de
   promover: medir H2 controlando por la volatilidad realizada ANTES de la deteccion (p. ej. recorrido de los 60 min previos).

## Estado
- H2: PROVISIONAL, candidata a replicacion ES (abr-sep, una sola vez) **despues** del control por volatilidad previa en
  descubrimiento. H1/H3/H4: muertos para esta configuracion en ES.
- Paridad LUX-IMB y barras en ES contra NT8: no medida (riesgo declarado).

Aporte al referente: primera regularidad de la familia que sobrevive una prueba pre-registrada fuera de muestra (menos
recorrido sobre areas cargadas, -14 %), con el control pendiente que decide si es de las zonas o del regimen de volatilidad.
