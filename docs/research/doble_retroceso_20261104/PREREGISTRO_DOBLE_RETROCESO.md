# Pre-registro: DOBLE-RETROCESO (04/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2 exploratorio**
(grilla masiva, `GUIA_GRILLA_MASIVA.md`). Código `edgelab/research/doble_retroceso.py`; tests `tests/research/test_doble_retroceso.py`.

## La idea (Nico, charla con Gemini)

Hay cinco piernas:
1. Un impulso.
2. Un retroceso, que fija el pico P2.
3. Un segundo impulso que **toma P1** sin pasarse mucho.
4. Un segundo retroceso que vuelve **cerca de P2 sin tomarlo**.
5. La continuación.

Se opera la continuación con el stop corto detrás de P2. Se mide en distintas resoluciones de tick y con muchísimas combinaciones de
distancias y de velas por pierna.

## Diseño (optimizado para muchas combinaciones)

- **Una sola pasada del detector por resolución.** Los umbrales son mínimos: impulso 1 ≥ 1 ATR, retroceso 1 ≥ 0,3 ATR, P3 más allá de
  P1 por ≥ 1 tick, retroceso 2 ≥ 0,3 ATR, P4 al menos a 1 tick de P2 sin tomarlo, ≤ 60 velas por pierna.
- **Cada pierna medida pasa a ser variable de la grilla masiva** (tensor acumulado). No hay umbrales elegidos a ojo: los cortes son
  cuantiles del DESC.
- **Variables** (en ATR de la resolución y velas de la resolución):

  | Variable | Qué mide | Tipo |
  |---|---|---|
  | modo | 0 giro temprano desde P4 (≥ 0,25 ATR, vela a favor) · 1 impulso 3 confirmado (≥ 1 ATR) | grupo |
  | resolución | 50, 100, 250 ticks | grupo |
  | imp1 | tamaño del impulso 1 | ≥ cuartiles |
  | ret1 | retroceso 1 / impulso 1 | ≤ cuartiles |
  | pasa_p1 | cuánto P3 se pasó de P1 («no mucho más profundo») | ≤ cuartiles |
  | cerca_p2 | qué tan cerca de P2 quedó P4 sin tomarlo | ≤ cuartiles |
  | velas de cada pierna | impulso 1, retroceso 1, impulso 2, retroceso 2 | ≤ terciles |

- **Ejecuciones:** stop detrás de P2 (+1 tick) o P2 + 0,25 ATR × TP {2R, 3R, MM = impulso 1 medido desde P4}.
- **Tamaño:** 2 × 3 × 4⁴ × 3⁴ × 6 = **746.496 celdas por canal**.
- **Barras de ticks:** se arman con los mismos ticks del simulador (`tpx`), cortadas por sesión. La última barra abierta nunca cuenta
  como cerrada; lo verificó el preflight de causalidad por disparo.
- **Entrada:** el disparo se ubica en la vela M1 del último tick de su barra, y se entra en el primer tick de la vela M1 siguiente. Puede
  ser hasta un minuto tarde, nunca antes.
- **Duplicados:** si varios candidatos disparan en la misma vela con la misma dirección y modo, queda el de mayor impulso 1. La regla es
  declarada, no se elige mirando.
- **Noticias:** sin entradas a ±5 min de un dato tier1 y salida forzada antes de cada dato.

## Campañas

| Campaña | Datos | Señal → ejecución | DESC |
|---|---|---|---|
| DRC-NQ-R, DRC-ES-R, DRC-YM-R, DRC-GC-R | trades del futuro | futuro → futuro | 2025-08 → 2026-03 |
| DRC-USATECH-R, DRC-USA500-R, DRC-USA30-R, DRC-XAU-R, DRC-EURUSD-R, DRC-GBPUSD-R | cotizaciones Dukascopy | CFD/spot → mismo (costo del futuro) | 2024-01 → 2026-03 |

La réplica es abr–sep 2026 en todas. En CFD y spot los «ticks» son cotizaciones, no trades: una barra de 100 ticks es otra resolución que
en el futuro, y se declara así. Holdout: frontera única HOLDOUT-A4. Linaje: familia nueva, sin padres.

## Justificación económica y cómo podría refutarse

- **Justificación:** el impulso 2 barre la liquidez de P1 (stops y entradas de ruptura). El retroceso 2 que no toma P2 muestra que el
  lado contrario no tiene fuerza para recuperar la estructura, y el stop detrás de P2 es corto y estructural, como el atlas en R prefiere.
- **Refutación:**
  - ninguna celda nominada por FDR q 0,10 (cola t) ni pista que replique en ningún activo;
  - las variables de piernas no separan (la celda «cualquiera» rinde igual);
  - falla de integridad;
  - la paridad con el indicador de NT8 falla. Se mide aparte, con señales exportadas del C#.
