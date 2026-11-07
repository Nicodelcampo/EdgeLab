# Pre-registro: ESPEJO-PICOS2 — cuatro definiciones nuevas de pico, distintas entre sí (07/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar; pedido de Nico: «creá definiciones nuevas de picos que sean distintas entre sí, y
lanzá nuevas corridas con esas definiciones»). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2**. Hermana de ESPEJO-PICOS (pivote de w velas,
`docs/research/espejo_picos_20261107/PREREGISTRO.md`) y de ESPEJO-ZONAS: misma base de eventos, mismas ejecuciones, mismas preguntas.

**Escrito antes de conocer las pistas de ESPEJO-PICOS** (su DESC terminó sin nominadas; la réplica de pistas no se había corrido).
Las definiciones nuevas no se eligieron mirando sus celdas: responden a qué otra cosa puede ser «liquidez del lado del impulso».

## Hipótesis

La de ESPEJO-PICOS: si la ida fue a tomar liquidez y la tomó, la vuelta completa el espejo o pasa A. Lo que cambia es qué se llama
liquidez. Cada definición mide un mecanismo distinto:
- **ZIGZAG** (amplitud): el extremo de un movimiento que revirtió al menos R (2 o 5 viajes de fricción severa). Un pico que «costó»
  una reversión grande es un nivel que el mercado recuerda.
- **IGUALES** (stops acumulados): dos pivotes de 3 velas a ≤ 0,1 o 0,4 viajes de fricción (1 y 4 ticks en NQ) sin que el precio pase
  a los dos en el medio. Encima de un techo doble se juntan stops.
- **MECHA** (rechazo): pivote de 3 velas con mecha del lado del pico ≥ 40 % o 60 % del rango de la vela: hubo órdenes que rechazaron.
- **HORARIO** (reloj): extremo de cada ventana de 15 o 60 minutos de reloj. No depende de la forma: es el nivel que cualquiera ve en
  un gráfico de 15 o 60 minutos.

**Justificación económica:** la liquidez en reposo (stops, órdenes de ruptura) se concentra en lugares identificables. Si cada
definición captura un lugar distinto, la que realmente ordena el espejo debería separar mejor a los que llegan a A.

**Cómo podría refutarse:**
- ninguna definición separa a los espejos que tomaron picos de los que no, en llegada a A o más allá, a igual ancho y horario;
- las cuatro dan lo mismo que el pivote simple de ESPEJO-PICOS (no agregan información); o
- ninguna celda nominada por FDR q 0,10 ni pista que replique en R neto.

**Distintas entre sí (medido sin desenlaces, sobre el sintético):** el índice de Jaccard entre los conjuntos de picos de tipos
distintos queda entre 0,04 y 0,31. Con la tolerancia original de IGUALES (1 viaje) se parecía al pivote simple (0,71), y por eso se
achicó a 0,1 y 0,4 viajes antes de lanzar.

## Espacio de eventos y estados (regla de población)

El evento es el del padre (cierre que deshace la fracción f de la ida). Formas de «pico» enumeradas:
- pivote de w velas: **ya medida** (ESPEJO-PICOS);
- reversión por amplitud (ZIGZAG), niveles iguales (IGUALES), rechazo por mecha (MECHA), extremo de ventana de reloj (HORARIO):
  **medidas acá**;
- extremos de sesión (día previo, overnight, OR30, VWAP) y gaps: **fase 2 declarada** en ESPEJO-PICOS, no acá;
- picos con volumen (clímax): no medidos (el volumen de velas de 10 ticks no está validado para eso);
- zonas de indicadores: ESPEJO-ZONAS.

## Definición (`edgelab/research/espejo_picos2.py`, tests en `tests/research/test_espejo_picos2.py`)

- **Base:** detector de ESPEJO-MACRO-10T-TIEMPO (causal, topes 60 / 120 min), ancho laxo de 5 viajes, retrocesos fijos en el laxo,
  velas de 10 ticks. Los módulos padre no se tocan.
- **Pico válido:** confirmado hasta A (cada definición tiene su confirmación: la vela de la reversión, la de confirmación del pivote o
  el cierre de la ventana), de la misma sesión que A, más allá de A y sin romper hasta A (ninguna mecha lo pasó).
- **Perillas:** tipo (4) × escala (2) × antigüedad (≤ 30 min · 30–120 min · > 120 min · todos, cortes de Nico) × picos tomados
  (0 · 1–2 · 3+ · cualquiera) × posición media (inicio / medio / final) × sobrepaso del último tomado (≤ 0,10 W · ≤ 0,25 W · más) ×
  si quedan picos más allá; más fracción, ancho en viajes y RTH del padre.
- **Ejecuciones (8):** las de ESPEJO-PICOS (stop en B a 1 tick o 10 % de W × objetivo A, 1,25 W, 1,5 W o 2R).
- **Tamaño:** 2.073.600 celdas por canal. Es grande a propósito: las cuatro definiciones van en un solo barrido para que la
  corrección por multiplicidad las cobre juntas, en lugar de cuatro familias que se cobran por separado.

## Linaje y multiplicidad

ESPEJO_PICOS2_{NQ,ES,YM,GC}: hijas de la variante en tiempo (y de ancho en ES e YM), de ESPEJO-PICOS y de ESPEJO-ZONAS del mismo
activo (GC no tiene zonas). Comparten eventos y desenlaces: heredan la multiplicidad bruta.

## Orden de medición

1. **Información, sin P&L:** llegada a A y más allá por tipo de pico y clase, contra el control emparejado.
2. **Embudo en R:** ESPEJOPICOS2-{NQ,ES,YM,GC}, conductor local, DESC 05/08/2025 → 31/03/2026, réplica abr–sep 2026, holdout desde el
   01/10/2026 a N fijo 150.
