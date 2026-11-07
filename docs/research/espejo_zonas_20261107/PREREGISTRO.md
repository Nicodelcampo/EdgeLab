# Pre-registro: ESPEJO-ZONAS — el espejo clasificado por las zonas de otros indicadores que encontró la ida (07/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar; pedido de Nico: «en lugar de picos use zonas de otros indicadores… en qué parte del
impulso están, la cantidad, la antigüedad, y si hay o no más zonas más allá cercanamente del impulso inicial»). Referente
`docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2**.
Hermana de ESPEJO-PICOS (`docs/research/espejo_picos_20261107/PREREGISTRO.md`): misma base de eventos y mismas ejecuciones; cambia
qué se mira en la ida (zonas de indicadores en lugar de pivotes).

## Hipótesis

Si el impulso fue a buscar la liquidez que marcan las zonas de los indicadores, una vez que las alcanzó el motivo desaparece. Entonces
la vuelta completa el espejo (llega a A) o va más allá. Inversa, mismo mecanismo: si quedan zonas vivas justo más allá del extremo,
el precio tiene un motivo para seguir y el espejo debería fallar más.

**Justificación económica:** las zonas de estos indicadores (volumen agresivo, clusters, trampas, absorciones) son niveles donde hubo
órdenes. Si el impulso las consume, se agota la razón del movimiento, y la vuelta queda sin contraparte que la frene hasta el origen.

**Cómo podría refutarse:**
- los espejos con zonas tomadas no llegan a A ni lo pasan más seguido que los que no tomaron ninguna, a igual ancho, duración y
  horario;
- la presencia de zonas cercanas más allá del extremo no cambia el resultado; o
- la diferencia no se ve en R neto (ninguna celda nominada por FDR q 0,10 ni pista que replique).

## Espacio de eventos y estados (regla de población)

El evento es el del padre: el cierre que deshace la fracción f de la ida (sólo eso se opera). Sobre ese evento se enumeraron estas
formas de relacionar zona e impulso:
- zona creada antes de A, viva, y alcanzada por la ida (**medida**);
- zona creada antes de A, viva, más allá del extremo y cerca (**medida**: «más allá cercana»);
- zona nacida durante la ida: la huella del propio impulso (**medida** como banda de antigüedad);
- zona nacida durante la vuelta (no medida: es posterior al extremo y mezcla la vuelta con la clasificación de la ida);
- zona ya cruzada antes de A (excluida: es liquidez ya consumida, como el pico roto);
- zonas detrás de A, en la otra dirección (no medidas: el objetivo está del lado de A; quedan para una fase con objetivos más allá de A
  mirando esas zonas como destino);
- estado continuo (densidad de zonas por vela) en lugar de evento (no medido acá).

## Definición (`edgelab/research/espejo_zonas.py`, tests en `tests/research/test_espejo_zonas.py`)

- **Base:** el detector de ESPEJO-MACRO-10T-TIEMPO (causal, topes 60 / 120 min), ancho mínimo laxo de 5 viajes, retrocesos fijos en el
  laxo (0,40), velas de 10 ticks. Los módulos padre no se tocan.
- **Zonas** (almacenes `nicolasbuttaro/edgelab-zonas-u1` y `nicolasbuttaro/edgelab-zonas-hft`, vía `prerange_zonas.cargar_zonas`):
  - NQ y ES: AVZP2 (en `t_decidida_ns`), AVCL, BT2, HFT2, HFTNQ;
  - YM: AVZG (zona base 17, como U1-ZONAS-GRILLA), BT2, HFT2, HFTNQ;
  - GC: sin almacén, no se corre;
  - LUX-IMB queda afuera: se calcula sobre velas M1 y acá las velas son de 10 ticks (sería otro indicador).
  - Disponibilidad: primera vela que cierra en o después del instante de la zona; se usa desde esa vela. Sólo zonas de la misma
    sesión que A (las de otra sesión pueden ser de otro contrato tras un roll).
- **Espacio «techo»:** si la ida baja, se niegan los precios. A = mecha de la vela de inicio; techo = extremo de la ida por mechas;
  W = techo − A. Una zona cuenta si su punto medio está más allá de A.
- **Viva:** desde que existe hasta A, ningún cierre pasó su borde lejano en la dirección del impulso. Los almacenes no traen el fin de
  la zona (salvo BT2), así que se calcula igual para todos.
- **Perillas:**
  - indicador (5 niveles; en YM el quinto queda vacío);
  - antigüedad: recientes (≤ 30 min antes de A) · viejas (> 30 min, misma sesión) · nacidas en la ida · todas;
  - zonas tomadas (la ida alcanzó su borde cercano): 0 · 1–2 · 3+ · cualquiera;
  - posición media de las tomadas en el impulso: inicio (< 1/3 W) · medio · final (≥ 2/3 W) · cualquiera;
  - más allá cercana: hay o no una zona viva no alcanzada con borde cercano a ≤ 0,25·W del extremo · cualquiera;
  - del padre: fracción de entrada (25 / 50 / 75 %), ancho en viajes (≥ 5 / 10 / 20) y RTH.
- **Ejecuciones (8):** las de ESPEJO-PICOS: stop en B (1 tick o 10 % de W) × objetivo A, 1,25 W, 1,5 W o 2R.
- **Tamaño:** 259.200 celdas por canal.

Cortes elegidos sin ver datos: 30 min (igual que ESPEJO-PICOS) y 0,25·W (cerca = un cuarto del impulso, la mitad de lo que el objetivo
1,5 W pide más allá de A).

## Linaje y multiplicidad

ESPEJO_ZONAS_{NQ,ES,YM} son hijas de la variante en tiempo de cada activo (y de la de ancho en ES e YM) y **también de ESPEJO-PICOS**
del mismo activo: comparten eventos y desenlaces, así que heredan su multiplicidad bruta (conservador).

## Orden de medición

1. **Información, sin P&L:** probabilidad de llegar a A y de pasarlo por clase (tomadas, posición, antigüedad, más allá) contra el
   control emparejado (los espejos sin zonas tomadas, mismo ancho, duración y horario).
2. **Embudo en R:** ESPEJOZONAS-{NQ,ES,YM}, conductor local, DESC 05/08/2025 → 31/03/2026, réplica abr–sep 2026, holdout desde el
   01/10/2026 a N fijo 150. Cuenta `nicolasbuttaro` (la otra no tiene acceso al almacén HFT2/NQ).
