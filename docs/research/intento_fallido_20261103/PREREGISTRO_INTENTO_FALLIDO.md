# Pre-registro: INTENTO-FALLIDO (idea de Nico, 03/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr). Referente: `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa del embudo: **EF2
exploratorio**. Código: `edgelab/research/intento_fallido.py` (+ `_lux`, `_avcl`, `_racimos`). Tests: `tests/research/test_intento_fallido.py`.
Mapa de familias con objetivo en zona: `docs/research/MAPA_OBJETIVOS_ZONAS_INTENTO_FALLIDO_20261103.md`.

## Pregunta (Nico)

«Si el precio proviene desde x distancia y se acerca al objetivo a una distancia menor a y, pero en lugar de acceder al objetivo se da
vuelta y avanza z en dirección contraria: (A) ¿qué entradas rentables se pueden hacer habiéndose alejado z?, o (B) habiéndose alejado z,
¿hay alguna distancia a la que, si el precio vuelve a acercarse al objetivo, permite entradas rentables?»

## Población y espacio de eventos (regla del repo)

- **Espacio enumerado**: (1) creación de la zona; (2) aproximación; (3) primer toque; (4) toque n-ésimo; (5) invalidación; (6) expiración;
  (7) confluencia; (8) estado continuo; (9) **aproximación fallida** (acercarse sin tocar y rechazar). U1 mide (2) y opera hacia la zona.
  Ésta mide (9), **el complemento de U1**: los caminos en que U1 no llega a su objetivo. La hipótesis principal es que la zona sigue atrayendo después del intento fallido (entrar hacia ella); a favor del rechazo es el control. Se elige (9) porque es exactamente la pregunta,
  y porque reutiliza zonas, recorridos y disparos causales de U1 ya auditados (paridad, causalidad por disparo, holdout cerrado).
- **x (de dónde viene)** = el recorrido A de U1 (de la zona al extremo E), con A/H ≥ 4 como piso y variable ordinal A/H (4, 8, 16).
  La aproximación se toma en el **primer** disparo de U1 (le falta un tercio del camino), una vez por camino.
- **Evento vela a vela, causal**: distancia al objetivo T (borde cercano de la zona) con el precio más cercano de cada vela. Si T se toca,
  no hay evento. Si lo más cerca que llegó es ≤ y·A y después el cierre se aleja ≥ z·A desde ahí, hay **intento fallido**. Ventana de 240
  velas desde el disparo de U1, dentro de la misma sesión.
- **Grilla**: y ∈ {0,05; 0,10; 0,20}·A; z ∈ {0,10; 0,20; 0,35}·A; N (3 o 5 zonas en el racimo); A/H (piso 4; ≥ 4, ≥ 8, ≥ 16).
  **Reglas** (variable de grupo, 6). **Enmienda de Nico, 03/11, antes de ver resultados: «la idea es entrar hacia la zona, no a favor del
  rechazo; probá las dos, con distintos niveles de TP»**:
  - **A_HACIA** (la idea): al cierre del alejamiento z, entrar HACIA la zona;
  - **A_RECHAZO** (control): en el mismo momento, entrar a favor del rechazo;
  - **B50/B80_HACIA**: cuando el cierre recupera el 50 % / 80 % del rechazo, entrar hacia la zona (segundo intento);
  - **B50/B80_RECHAZO** (control): en el mismo momento, a favor del rechazo.
- **Ejecución** (entrada en el primer tick de la vela siguiente). Stops estructurales, como pide el atlas en R:
  - hacia la zona: un tick más allá del extremo del rechazo;
  - a favor del rechazo: un tick más allá del precio más cercano del intento;
  - en los dos casos, colchón opcional de 0 o 0,5·z.

  **TP**: 1R, 2R, 3R, o niveles de estructura Z1/Z2/Z3. Hacia la zona son el borde cercano, el medio y el borde lejano; a favor del rechazo,
  un tercio, dos tercios y todo el camino de vuelta al origen E. 6 TP × 2 colchones = 12 ejecuciones. 6 × 3 × 3 × 3 × 2 = 324 celdas × 12 =
  **3.888 por canal**. La primera carga (5 reglas, 3 ejecuciones) se detuvo en DESC sin que hubiera resultados: `superadas_v1/`.
- **Noticias**: sin entradas a ±5 min de un dato tier1 y salida forzada antes de cada dato.

## Campañas (fuentes de zonas, por prioridad del mapa)

| Campaña | Zonas | Señal → ejecución |
|---|---|---|
| IF-LUX-CFD-NQ-R2 | racimos LUX-IMB (fuente de U1-CRUZADO) | USATECH CFD → NQ |
| IF-LUX-NQ-R2 | racimos LUX-IMB | NQ → NQ |
| IF-AVCL-NQ-R2 | racimos aVolClusterPOI | NQ → NQ |
| IF-RACIMOS-NQ-R2 | racimos aVolZonePOI2 | NQ → NQ |

Las cuatro comparten mecanismo, pero son familias distintas por fuente de zonas. Linaje: **hijas de U1** (misma población de aproximaciones),
así que heredan la multiplicidad de su padre U1 por fuente (`LINAJES.jsonl`). Abr–sep ya fue mirado por U1: la réplica no es virgen para
el mecanismo padre, pero sí para este evento, que U1 nunca midió. Holdout: frontera única HOLDOUT-A4 y protocolo de apertura en código.

## Justificación económica

**La idea (hacia la zona).** La zona es un imán de liquidez. Si el precio llega cerca y no la toca, la liquidez sigue sin tomar y el
rechazo suele ser una toma de ganancias o una absorción pasajera. Entrar hacia la zona, al rechazo (A_HACIA) o en el reacercamiento
(B_HACIA), apuesta a que el segundo intento la alcance, con un stop chico detrás del extremo del rechazo.

**El control (a favor del rechazo).** El rechazo revela que del otro lado hay absorción, o que el flujo que empujaba se agotó, y deja stops
agrupados detrás del intento. Si gana el control y no la idea, la zona no atrae: repele.

## Cómo podría refutarse

- Ninguna celda nominada por FDR q 0,10 (cola t) en DESC ni pista que replique en abr–sep en R.
- A y B no difieren de sus controles: los rechazos sin zona, que no se miden acá, quedan como NO MEDIDO para una etapa posterior si alguna pasa.
- La ventaja depende de un único y o z aislado, sin meseta.
- Integridad: placebo y latencia de una vela.

**Ids (03/11).** La v2 corre como `-R2`: el contador global de pruebas (append-only) ya tenía registradas 1.620 de la v1 con el id `-R`.
Esas pruebas quedan contadas en la misma familia (conservador). Total de la familia por fuente: 1.620 + 7.776.
