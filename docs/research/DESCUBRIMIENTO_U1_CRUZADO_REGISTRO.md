# U1-CRUZADO — registro del descubrimiento y del proceso que lo produjo (2026-10-23)

Estado: VIGENTE — candidato más avanzado de EdgeLab al 2026-10-23. **No confirmado:** falta el holdout a N fijo.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Pedido de Nico (2026-10-23): «registralo a fondo, no sólo por su valor como posible edge, sino por todo el proceso hasta
encontrarlo, que fue producto de probar muchísimas variantes y filtrar, y no de probar de a una propuesta humana».

## 1. Qué es
- **Señal, calculada sobre el CFD USATECH (Dukascopy):** un área de ≥ 3 zonas LUX-IMB (OG/VI en M1) en 40 pts. El precio se aleja
  ≥ 8× la altura del área y regresa el 75 % del camino.
- **Operación en el futuro NQ:** HACIA el área, en el tick siguiente. Objetivo en el borde lejano del área. Stop más allá del
  extremo, con tope de 3× la distancia al objetivo.
- **Traslado:** los niveles pasan de un instrumento al otro con la base NQ − USATECH en ese minuto.
- **Riesgo:** gana el 75–80 % de las veces y pierde poco y grande. La peor operación vista es −393 pts, así que el riesgo se
  controla con el tamaño (MNQ) y el límite diario, no con el stop.
- **Mecanismo propuesto:** tras un alejamiento grande, el regreso a una concentración de desequilibrios sigue hasta el área. La
  señal está en las zonas del **CFD**: con las zonas del propio NQ la misma regla da +0,4. El CFD funciona como sensor de la
  estructura y el futuro como instrumento.

## 2. Cómo se llegó: el embudo, no una idea suelta

| paso | qué se hizo | pruebas | resultado |
|---|---|---:|---|
| Pedido de Nico | áreas de zonas × alejamiento × acercamiento × volumen × entradas/SL/TP/BE, NQ y USATECH | — | AREAS-EXP-1 |
| v1.2 | primera corrida | 1.492.992 | **descartada sin mirar**: el código se corrigió después |
| v1.3 DESC | tamiz FDR | 1.990.656 | 0 nominadas en las dos fuentes |
| v1.3b | MDE (faltaba) | (mismas) | t máx 4,6 ≈ máximo por azar; sin falta de potencia |
| Auditoría del filtro | pedido de Nico: «matar todo parece artefacto del filtro» | — | Romano-Wolf por sesiones, canal reciente, regla de régimen, pistas |
| v1.4 DESC | tamiz + Romano-Wolf en 4 canales | 3.981.312 | 0 rechazadas; **80 pistas** distintas a réplica |
| Réplica v1.4 | 80 pistas en abr–sep 2026 | 80 | 0 confirmadas por la regla; **5 celdas de USATECH = una idea: U1** |
| U1-INDAGA | indagar antes del P&L (pedido de Nico): volumen por pierna, esperas, VWAP, velocidad | 11.943.936 | A/H ordena el retorno de forma monótona; U1-B elegida |
| U1-B | seguimiento secuencial en NQ abr–sep | — | **refutada** (−0,18): la selección no sobrevivió |
| U1-CRUZADO | idea de Nico: señal en el CFD, operación en NQ | 4 | **+17 a +28 pts/op netos** en dos períodos |
| Integridad | alineación al segundo, placebo, latencia | — | pasa: pico 0 s, placebo ≈ 0, latencia de 5 min sin degradar |
| OOS 2023–2025 | USATECH nunca usado | 2 | no confirma (≈ 0): funcionaba desde 2025, no antes |
| Topes | 7 topes × T1/T3, regla declarada | 14 | T3 con tope 3×; ningún tope en puntos conserva el edge |
| Holdout exploratorio | 2026-10-01 → 22, acta antes de mirar | — | **8 ops, +29,4 pts/op, 7 de 8**; no concluyente por n |

- **Pruebas registradas en la familia:** 19.409.038, contando cada procedimiento nuevo sobre las mismas celdas como pruebas nuevas.
- **Contador global de EdgeLab:** 19.564.170.
- **Ninguna de las variantes que llevaron a U1 la propuso una persona de a una.** La idea humana fue la del espacio a barrer: áreas,
  alejamiento, volumen, y después usar el CFD como sensor. La celda salió del filtro.

## 3. Qué lo hizo posible (y qué casi lo mata)
- **No descartar sin mirar.** El tamiz FDR mató el 100 % en v1.3. La auditoría del filtro, en las dos direcciones, agregó las
  pistas a réplica, y de ahí salió U1. Lección (ATJ-25): cero sobrevivientes de un millón obliga a auditar el filtro, no a cerrar la familia.
- **Indagar antes de confirmar** (ATJ-26) mostró qué variable ordena el retorno: el tamaño del alejamiento.
- **La selección entre dos fuentes eligió mal** (U1-B), y la confirmación con datos nuevos lo mostró. El sistema descartó una
  falsa candidata antes de gastar el holdout.
- **La idea del sensor** (CFD para la señal, futuro para operar) convirtió algo no operable en algo operable. El conductor genérico
  ya lo trae para cualquier experimento (`grilla_generica.simular_ops(cx_ej=...)`).
- **Controles de integridad antes del holdout.** Sin placebo, latencia y alineación, +20 pts/op podría haber sido look-ahead entre
  feeds. Se verificó que no lo es.
- **Errores:** 26 encontrados en el proceso. Todos corregidos, y la mayoría convertidos en chequeos automáticos (preflight, ATJ-27;
  `u1/REVISION_ERRORES_Y_PLAN_U1_CRUZADO.md`).

## 4. Qué NO está probado
- **No es un edge confirmado.** El holdout exploratorio tiene n = 8; la confirmación necesita ≈ 95–150 operaciones posteriores al
  2026-10-22, con la regla intacta y una sola mirada.
- **Régimen:** neutro en 2023–2024 y positivo desde 2025. Puede ser un régimen actual o un efecto de la selección: sólo el forward
  lo distingue.
- **Feed:** la señal depende de las zonas del CFD de Dukascopy. Operar en vivo exige un feed que reproduzca esas zonas (paridad de
  feeds pendiente).
- **Densidad del feed:** ≈ 5 señales por mes antes de 2025 contra ≈ 20 después. Falta medir si es mercado (volatilidad) o feed
  (ticks por día). Corrida `edgelab-u1x-densidad`, todavía en curso al escribir este registro.
- **Cola:** pérdidas de hasta −393 pts por operación.

## 5. Dónde está todo
| qué | ruta |
|---|---|
| Manifiesto, réplica, revisión de errores, resultados AREAS-EXP-1 | `docs/research/areas_expansion_20261022/` |
| U1-INDAGA, U1-B, U1-CRUZADO, integridad, OOS, topes, holdout | `docs/research/areas_expansion_20261022/u1/` |
| Código | `edgelab/research/{areas_expansion,u1_indaga,u1_cruzado,grilla_generica,grilla_masiva,controles,etapas,embudo}.py` |
| Campaña reproducible en el embudo automático | `config/autopilot/grillas/campanas/U1_CRUZADO.json` (apagada) |
| Registro MEDIDO / NO MEDIDO | `docs/research/areas_expansion_20261022/AREAS_EXP_1_MEDIDO_Y_NO_MEDIDO.md` |
