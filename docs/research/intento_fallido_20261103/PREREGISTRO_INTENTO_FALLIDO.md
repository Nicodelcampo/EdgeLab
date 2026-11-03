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
  Ésta mide (9), **el complemento de U1**: los caminos en que U1 no llega a su objetivo. Se elige (9) porque es exactamente la pregunta,
  y porque reutiliza zonas, recorridos y disparos causales de U1 ya auditados (paridad, causalidad por disparo, holdout cerrado).
- **x (de dónde viene)** = el recorrido A de U1 (de la zona al extremo E), con A/H ≥ 4 como piso y variable ordinal A/H (4, 8, 16).
  La aproximación se toma en el **primer** disparo de U1 (le falta un tercio del camino), una vez por camino.
- **Evento vela a vela, causal**: distancia al objetivo T (borde cercano de la zona) con el precio más cercano de cada vela. Si T se toca,
  no hay evento. Si lo más cerca que llegó es ≤ y·A y después el cierre se aleja ≥ z·A desde ahí, hay **intento fallido**. Ventana de 240
  velas desde el disparo de U1, dentro de la misma sesión.
- **Grilla**: y ∈ {0,05; 0,10; 0,20}·A; z ∈ {0,10; 0,20; 0,35}·A; N (3 o 5 zonas en el racimo); A/H. **Reglas** (variable de grupo):
  - **A**: entrar al cierre del alejamiento z, a favor del rechazo;
  - **B-HACIA (r = 0,5 / 0,8)**: después de A, cuando el cierre recupera la fracción r del rechazo hacia T, entrar hacia T (segundo intento);
  - **B-CONTRA (r = 0,5 / 0,8)**: en el mismo momento, entrar en contra (segundo rechazo).
- **Ejecución** (entrada en el primer tick de la vela siguiente; stops estructurales, como pide el atlas en R): a favor del rechazo, el stop va un
  tick más allá del precio más cercano del intento; hacia T, un tick más allá del extremo del rechazo. Objetivos: 2R, 3R, o LEJOS
  (origen E para el rechazo y borde lejano de la zona para el segundo intento). 5 × 3 × 3 × 4 × 2 = 360 celdas × 3 ejecuciones = **1.080 por canal**.
- **Noticias**: sin entradas a ±5 min de un dato tier1 y salida forzada antes de cada dato.

## Campañas (fuentes de zonas, por prioridad del mapa)

| Campaña | Zonas | Señal → ejecución |
|---|---|---|
| IF-LUX-CFD-NQ-R | racimos LUX-IMB (fuente de U1-CRUZADO) | USATECH CFD → NQ |
| IF-LUX-NQ-R | racimos LUX-IMB | NQ → NQ |
| IF-AVCL-NQ-R | racimos aVolClusterPOI | NQ → NQ |
| IF-RACIMOS-NQ-R | racimos aVolZonePOI2 | NQ → NQ |

Las cuatro comparten mecanismo, pero son familias distintas por fuente de zonas. Linaje: **hijas de U1** (misma población de aproximaciones),
así que heredan la multiplicidad de su padre U1 por fuente (`LINAJES.jsonl`). Abr–sep ya fue mirado por U1: la réplica no es virgen para
el mecanismo padre, pero sí para este evento, que U1 nunca midió. Holdout: frontera única HOLDOUT-A4 y protocolo de apertura en código.

## Justificación económica

Una zona con liquidez que el precio no alcanza revela que del otro lado hay absorción, o que el flujo que empujaba se agotó. El rechazo
cerca del objetivo deja stops agrupados detrás del intento. Por eso **A** apuesta a la continuación del rechazo. **B-HACIA** apuesta a que
el segundo intento llegue, cuando la absorción se agotó. **B-CONTRA** apuesta al doble techo o piso.

## Cómo podría refutarse

- Ninguna celda nominada por FDR q 0,10 (cola t) en DESC ni pista que replique en abr–sep en R.
- A y B no difieren de sus controles: los rechazos sin zona, que no se miden acá, quedan como NO MEDIDO para una etapa posterior si alguna pasa.
- La ventaja depende de un único y o z aislado, sin meseta.
- Integridad: placebo y latencia de una vela.
